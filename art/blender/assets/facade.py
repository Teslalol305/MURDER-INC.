"""Facade kit: every street-facing walk-up of the block, as modules (docs/unreal/spec/05-level.md 2.5).

A street front is assembled by `assemble_front(ctx, "s1")` (or by a level script reading the same tables):

    ground floor   SM_Facade_Pier_<Brick> | SM_Facade_Shopfront_<Shop> | SM_Facade_Pier_<Brick>      (0 .. 2.77 m)
                   SM_Facade_SignBand_<Shop> on top (2.77 .. 3.69), SM_Facade_Awning_<cm> where the shop has one,
                   SM_Facade_ResEntry_Red (tenement door on its stoop), SM_Facade_Vestibule_Red (S2's gated pocket)
    upper floors   SM_Facade_Fill_<cm>_<Brick> | n x SM_Facade_BayWindow_<Brick> (3.1 x 3.1) | Fill
                   props on the windows: SM_Facade_AirConditioner, SM_Facade_WindowBlind
    top            SM_Facade_CorniceEnd_L_<cm> | n x SM_Facade_Cornice_310 | CorniceEnd_R, the same split for
                   SM_Facade_Parapet_310_<Brick> / ParapetFill; sides: SM_Facade_CornerReturn_<Brick>,
                   SM_Facade_BayBlank_Common, SM_Facade_PartyWallCap_310; SM_Facade_RoofPanel_4m, water tank, bulkhead
    fire escape    SM_Facade_FireEscape_Balcony / _Stair / _Ladder / _Bracket

Module frame (README): pivot at the bottom-left corner of the outer face, running +X, outer face toward -Y, so the
wall plane y = 0 is the building line = the collision face; everything proud of it (piers, rails, cornice) has no
collision, and the only pocket is the shop door recess. Heights are measured from the sidewalk top.

Brick: the UVs are real metres from the module's pivot (u along the run, v up), so the bond would jump from one
module to the next. Each placed instance therefore carries its position along the run and its height in metres
(custom property `mi_uv`, read by the brick materials; in Unreal the same two numbers are per-instance custom data,
or the master material uses world-aligned UVs for the brick slots).

Wear (vertex colour): R soot (under sills, copings and belt courses, in reveals), G chipped arrises and paint worn
to rust, B rain and rust runs from the ends of every ledge and from anchors, A splash-back at the sidewalk.
"""
import math
import os

import bpy
import numpy as np

from assets.street import KERB_H, Waves, sstep
from mi import geo, mat, paths, render, scene, steel

FAMILY = {"name": "facade",
          "description": "Street-front kit: storefronts, roll gates, awnings, brick bays, cornice, parapet, fire escape, roof items"}

X, Y, Z = np.eye(3)
BAY, STOREY, GROUND, T = 3.1, 3.1, 3.65, 0.30          # bay width, upper storey, ground storey, wall thickness
WIN_W, WIN_H, WIN_SILL = 1.24, 1.736, 0.60
PIER_W, PIER_OUT = 0.32, 0.10
BULK, HEAD, BAND0, BAND_H = 0.63, 2.69, 2.77, 0.74     # bulkhead top, glass head, sign band bottom and height
DOOR_W, RECESS = 1.25, 0.36
AWN_Z = 2.75                                           # awning fixing line above the sidewalk
LINE = 11.0                                            # building lines at y = +-11
ESC_L, ESC_D, ESC_RAIL = 2.99, 1.07, 0.95

BRICKS = {"Red": "TS_Brick_ScanRedDark", "Brown": "TS_Brick_ScanBrown", "Buff": "TS_Brick_ScanBuff",
          "Painted": "TS_BrickPainted_ScanWhitewash", "Common": "TS_Brick_ScanRedCommon"}
FACE = ("Red", "Brown", "Buff", "Painted")
ENDS = {"Red": (0.60, 0.80), "Brown": (0.25,), "Buff": (0.60, 0.85), "Painted": (0.60,)}   # end pier widths in use
AWNINGS = (7.50, 10.26)

# sign, web x0, x1, sign w, h, door centre x (None: gate down), bulkhead, awning, preview colour of the sign face
SHOPS = {
    "Laundromat": ("n1", -46.0, -37.2, 7.50, 0.62, -39.65, "tile", False, (0.004, 0.036, 0.08)),
    "Barber": ("n1", -34.4, -26.2, 7.06, 0.62, -32.37, "tile", True, (0.01, 0.01, 0.012)),
    "Deli": ("n2", 11.0, 22.0, 8.40, 0.74, 16.50, "metal", True, (0.88, 0.54, 0.01)),
    "ChecksCashed": ("s1", -46.0, -38.3, 6.56, 0.74, -43.23, "metal", False, (0.01, 0.012, 0.01)),
    "Pizza": ("s1", -38.3, -30.0, 7.16, 0.74, -32.65, "tile", True, (0.45, 0.02, 0.013)),
    "Pawn": ("s2", -30.0, -24.0, 4.86, 0.74, -25.52, "metal", False, (0.012, 0.011, 0.008)),
    "Records": ("s2", -21.8, -16.0, 4.66, 0.62, -20.30, "wood", False, (0.008, 0.012, 0.014)),
    "Chicken": ("s3", -4.0, 5.0, 7.50, 0.74, -1.18, "tile", False, (0.88, 0.54, 0.01)),
    "Liquor": ("s3", 5.0, 13.5, 7.36, 0.62, 9.25, "metal", False, (0.014, 0.008, 0.008)),
    "Nails": ("s3", 13.5, 22.0, 7.36, 0.74, None, "metal", False, (0.014, 0.008, 0.012)),
}
# face: the way the front looks (N: the building stands on the south side). ground: ("entry" | "vestibule", x0, x1)
# besides the shops. escape: (centre x, balconies). free: ends whose side wall shows, as (left, right) seen from
# the street, each None or the first upper storey (0-based) from which it is free.
BUILDINGS = {
    "n1": dict(x=(-46.0, -26.2), face="S", storeys=5, brick="Red", extra=(("entry", -37.2, -34.4),), escape=(-30.6, 4), depth=23.0),
    "n2": dict(x=(11.0, 22.0), face="S", storeys=3, brick="Buff", extra=(), escape=None, depth=23.0),
    "s1": dict(x=(-46.0, -30.0), face="N", storeys=3, brick="Brown", extra=(), escape=(-42.5, 2), depth=23.0),
    "s2": dict(x=(-30.0, -16.0), face="N", storeys=4, brick="Red", extra=(("vestibule", -24.0, -21.8),), escape=(-27.0, 3), depth=23.0),
    "s3": dict(x=(-4.0, 22.0), face="N", storeys=2, brick="Buff", extra=(), escape=None, depth=15.0),
}

SLOT_META = {
    "MI_Steel_PaintDark": {"set": "TS_Steel_ScanPaintGrey", "workflow": "tiling", "tint": [0.16, 0.16, 0.17],
                           "note": "dark shop-front enamel: the grey paint scan multiplied by the tint"},
    "MI_Steel_PaintBlack": {"set": "TS_Steel_ScanPaintGrey", "workflow": "tiling", "tint": [0.07, 0.07, 0.075],
                            "note": "black fire-escape enamel: the grey paint scan multiplied by the tint"},
    "MI_Steel_PaintWhite": {"set": "TS_Steel_ScanPaintWhite", "workflow": "tiling", "note": "window frames and sashes"},
    "MI_Wood_DoorPaint": {"set": "TS_Wood_ScanPlankPainted", "workflow": "tiling", "tint": [0.30, 0.12, 0.09]},
    "MI_Fabric_ScanCanvas": {"note": "awning cloth: tint per shop (pizza #b3261e, barber #1c2f5a, deli #1f5a3a)"},
    "MI_Glass_Store": {"workflow": "glass", "note": "storefront plate glass: translucent, not Nanite"},
    "MI_Glass_Window": {"workflow": "glass", "note": "upper windows: opaque with a parallax room, or translucent"},
    "MI_Interior_Dark": {"workflow": "flat", "note": "shallow dark room behind the glass (stand-in for a parallax interior)"},
    "MI_Metal_Aluminium": {"workflow": "flat"}, "MI_Metal_Chrome": {"workflow": "flat"}, "MI_Fabric_Blind": {"workflow": "flat"},
}
for _k in BRICKS:
    SLOT_META["MI_" + BRICKS[_k][3:]] = {"uv": "metres from the module pivot / tile_m; add the instance's (run, height) "
                                               "offset or use world-aligned UVs so the bond runs through"}


def shop_local(name):
    """A shop in its own frame: left end as seen from the street = 0."""
    bld, xa, xb, sw, sh, door, bulk, awn, col = SHOPS[name]
    north = BUILDINGS[bld]["face"] == "N"
    w = xb - xa
    dc = None if door is None else (xb - door if north else door - xa)
    return dict(name=name, building=bld, W=w, C=w - 2 * PIER_W, door=dc, d0=None if dc is None else dc - DOOR_W / 2 - PIER_W,
                sign=(sw, sh), bulk=bulk, awning=awn, colour=col, x=(xa, xb))


def cm(v):
    return "%03d" % int(round(v * 100))


# ------------------------------------------------------------------------------------------------------ materials

def instance_uv(m):
    """Add the placed instance's `mi_uv` (metres along the run, metres up) to the UVs of a tiling material."""
    nt = m.node_tree
    uvn = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeUVMap"), None)
    if uvn is None or nt.nodes.get("mi_uv"):
        return m
    tu, tv = m["mi_tile_m"]
    att = nt.nodes.new("ShaderNodeAttribute")
    att.name, att.attribute_type, att.attribute_name = "mi_uv", "OBJECT", "mi_uv"
    div = nt.nodes.new("ShaderNodeVectorMath")
    div.operation = "DIVIDE"
    div.inputs[1].default_value = (tu, tv, 1.0)
    add = nt.nodes.new("ShaderNodeVectorMath")
    targets = [l.to_socket for l in uvn.outputs[0].links]
    nt.links.new(att.outputs["Vector"], div.inputs[0])
    nt.links.new(uvn.outputs[0], add.inputs[0])
    nt.links.new(div.outputs[0], add.inputs[1])
    for s in targets:
        nt.links.new(add.outputs[0], s)
    return m


def materials(ctx):
    sc = ctx.scan_set
    soot = (0.030, 0.028, 0.026)
    rust = dict(blend="TS_Steel_ScanRust", leak_color=(0.24, 0.10, 0.035), leak_rough=0.1, dirt_color=soot, alpha="splash")
    M = {}
    for k, s in BRICKS.items():
        lime = k == "Brown"                                   # ART_BIBLE: white lime runs on the brown brick
        M["brick" + k] = instance_uv(sc(s, alpha="splash", dirt_color=soot, macro=0.16, wear_tint=(1.14, 1.12, 1.10),
                                        leak_color=(0.46, 0.44, 0.40) if lime else (0.045, 0.04, 0.036)))
    M["common"] = M["brickCommon"]
    M["stone"] = sc("TS_Concrete_ScanWeathered", alpha="splash", dirt_color=soot, leak_color=(0.06, 0.052, 0.045), macro=0.12)
    M["conc"] = sc("TS_Sidewalk_ScanWorn", alpha="splash", dirt_color=(0.06, 0.055, 0.048), macro=0.12)
    M["tile"] = sc("TS_Tile_ScanWhite", alpha="splash", dirt_color=(0.07, 0.06, 0.05), macro=0.06)
    M["wood"] = sc("TS_Wood_ScanPlankPainted", alpha="splash", dirt_color=soot, macro=0.1)
    M["door"] = sc("TS_Wood_ScanPlankPainted", slot="MI_Wood_DoorPaint", alpha="splash", tint=(0.30, 0.12, 0.09), dirt_color=soot)
    M["timber"] = sc("TS_Wood_ScanPlankDark", alpha="splash", dirt_color=soot, macro=0.15)
    M["grey"] = sc("TS_Steel_ScanPaintGrey", blend_start=0.40, macro=0.12, **rust)
    M["trim"] = sc("TS_Steel_ScanPaintGrey", slot="MI_Steel_PaintDark", tint=(0.16, 0.16, 0.17), blend_start=0.55, macro=0.10, **rust)
    M["black"] = sc("TS_Steel_ScanPaintGrey", slot="MI_Steel_PaintBlack", tint=(0.07, 0.07, 0.075), blend_start=0.45,
                    wear_rough=-0.1, **rust)
    M["white"] = sc("TS_Steel_ScanPaintWhite", slot="MI_Steel_PaintWhite", alpha="splash", dirt_color=(0.06, 0.05, 0.04), macro=0.08)
    M["fabric"] = sc("TS_Fabric_ScanCanvas", alpha="splash", tint=(0.62, 0.075, 0.06), dirt_color=(0.07, 0.06, 0.05),
                     wear_tint=(1.5, 1.6, 1.6), macro=0.2)
    M["roof"] = sc("TS_Roof_ScanBitumen", alpha="splash", dirt_color=(0.10, 0.09, 0.08), macro=0.2)
    M["alu"] = mat.flat("MI_Metal_Aluminium", (0.60, 0.60, 0.61), 0.38, 1.0)
    M["chrome"] = mat.flat("MI_Metal_Chrome", (0.77, 0.77, 0.77), 0.10, 1.0)
    M["interior"] = mat.flat("MI_Interior_Dark", (0.022, 0.021, 0.02), 0.9)
    M["blind"] = mat.flat("MI_Fabric_Blind", (0.56, 0.53, 0.45), 0.85)
    M["glass"] = mat.make("MI_Glass_Store", "glass", Film=0.08)
    M["glasswin"] = mat.make("MI_Glass_Window", "glass", Film=0.18)
    for name in SHOPS:
        s = shop_local(name)
        m = mat.flat("M_Sign_" + name, s["colour"], 0.45)
        m["mi_tile_m"] = (float(s["sign"][0]), float(s["sign"][1]))       # the face is one 0..1 square
        M["sign" + name] = m
    return M


# ------------------------------------------------------------------------------------------------------- geometry

def B(seed=0, step=0.15):
    return steel.Builder(step=step, seed=seed)


def bx(b, lo, hi, slot, ch=0.0, pin=True, axis=None, **kw):
    """Box between two corners. pin: UVs measured from the module pivot (masonry that must run through);
    otherwise every part takes a random piece of its tile."""
    lo, hi = np.minimum(lo, hi).astype(float), np.maximum(lo, hi).astype(float)
    if np.any(hi - lo < 1e-5):
        return None
    if pin:
        kw.setdefault("uv_off", (0.0, 0.0))
    return b.box(lo, hi, slot, axis=axis, chamfer=ch, **kw)


def run(b, prof, x0, x1, slot, pin=True, **kw):
    """Profile [(out, z)] (counter-clockwise, out = distance in front of the wall plane) extruded from x0 to x1."""
    if pin:
        kw.setdefault("uv_off", (0.0, 0.0))
    kw.setdefault("pstep", 0.25)
    return b.prism(prof, (x0, 0.0, 0.0), -Y, Z, (x1 - x0, 0.0, 0.0), slot, **kw)


def rod(b, p0, p1, r, slot, n=8, **kw):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax = steel.unit(p1 - p0)
    u = steel.unit(np.cross(Z if abs(ax[2]) < 0.9 else X, ax))
    v = np.cross(ax, u)
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    kw.setdefault("pstep", 9.0)
    return b.prism(np.stack([r * np.cos(a), r * np.sin(a)], 1), p0, u, v, p1 - p0, slot, **kw)


def bar(b, p0, p1, w, t, slot, up=Z, ch=0.0, **kw):
    """Rectangular bar from p0 to p1: t along `up`, w across."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax = steel.unit(p1 - p0)
    u = steel.unit(np.cross(up, ax))
    v = np.cross(ax, u)
    kw.setdefault("pstep", 9.0)
    return b.prism(steel.rect(w, t, -w / 2, -t / 2, ch), p0, u, v, p1 - p0, slot, **kw)


def sheet(b, F, thick, slot, **kw):
    """Cloth or sheet metal from a grid of points F (rows, columns, 3): the front looks along
    (column direction) x (row direction), the back lies `thick` behind it."""
    F = np.asarray(F, dtype=np.float64)
    nr, nc = F.shape[:2]
    n = np.cross(np.gradient(F, axis=1), np.gradient(F, axis=0))
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-12)
    nvf = nr * nc
    verts = np.concatenate([F.reshape(-1, 3), (F - n * thick).reshape(-1, 3)])
    idx = lambda r, c: r * nc + c
    r_, c_ = np.meshgrid(np.arange(nr - 1), np.arange(nc - 1), indexing="ij")
    r_, c_ = r_.ravel(), c_.ravel()
    front = np.stack([idx(r_, c_), idx(r_, c_ + 1), idx(r_ + 1, c_ + 1), idx(r_ + 1, c_)], axis=-1)
    back = front[:, ::-1] + nvf
    c, r = np.arange(nc - 1), np.arange(nr - 1)
    bottom = np.stack([idx(0, c + 1), idx(0, c), idx(0, c) + nvf, idx(0, c + 1) + nvf], axis=-1)
    top = np.stack([idx(nr - 1, c), idx(nr - 1, c + 1), idx(nr - 1, c + 1) + nvf, idx(nr - 1, c) + nvf], axis=-1)
    left = np.stack([idx(r, 0), idx(r + 1, 0), idx(r + 1, 0) + nvf, idx(r, 0) + nvf], axis=-1)
    right = np.stack([idx(r + 1, nc - 1), idx(r, nc - 1), idx(r, nc - 1) + nvf, idx(r + 1, nc - 1) + nvf], axis=-1)
    quads = np.concatenate([front, back, bottom, top, left, right])
    edge = np.zeros((nr, nc))
    edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = 1.0
    tags = np.zeros((2 * nvf, 2))
    tags[:, 0] = np.concatenate([edge.ravel(), edge.ravel()])
    kw.setdefault("kind", b.OTHER)
    return b._add(verts, quads.ravel(), np.full(len(quads), 4), slot, tags, **kw)


def sub(b, other, rot_deg=0.0, loc=(0, 0, 0)):
    """Merge another builder, turned about Z and moved."""
    r = math.radians(rot_deg)
    Mx = np.eye(4)
    Mx[:2, :2] = [[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]]
    Mx[:3, 3] = loc
    return b.merge(other, Mx)


# ------------------------------------------------------------------------------------------------------- weather

MASONRY = ("brick", "common", "stone", "conc", "tile", "roof")


def weather(ctx, b, ob, key, ledges=(), ground=False, fade=None):
    """Paint the Wear mask. ledges: (x0, x1, z, strength) of every sill, coping or band that sheds water: soot
    collects under it and runs start at its ends. ground: the module stands on the sidewalk (splash-back).
    fade: (width, height) of a wall module; the random part of the mask dies out at its edges so that
    neighbouring modules meet without a step."""
    W = b.loops(ob, ao=None)
    rng = ctx.rng("wear", key)
    P, N = W.P, W.N
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    wa, wb, wc = Waves(rng, 0.7), Waves(rng, 2.6), Waves(rng, 0.22)
    a = wa.u(x + 0.6 * y, z)
    bb = wb.u(x - 0.4 * y, z)
    c = wc.u(x + y, z * 0.12)                                  # stretched down the wall: streaks
    up = np.clip(N[:, 2], 0, 1)
    names = W.names
    of = lambda pre: np.isin(W.slot, [i for i, k in enumerate(names) if k.startswith(pre)])
    mas, gls = of(MASONRY), of("glass")
    soft = of(("fabric", "interior", "sign", "blind"))
    met = ~(mas | gls | soft)
    e = 1.0
    if fade:
        e = sstep(0.0, 0.35, x) * sstep(fade[0], fade[0] - 0.35, x) * sstep(0.0, 0.35, z) * sstep(fade[1], fade[1] - 0.35, z)
    R = 0.10 + e * (0.16 * (a - 0.5) + 0.10 * (bb - 0.5)) + 0.28 * W.concave + 0.22 * up * (0.5 + 0.5 * bb)
    R = R + 0.14 * (np.abs(N[:, 0]) > 0.7) * mas                               # reveals stay dirty
    Bk = mas * e * 0.30 * sstep(0.60, 0.86, c) * (0.4 + 0.6 * bb)              # faint rain streaking everywhere
    for (x0, x1, zl, s) in ledges:
        inx = sstep(x0 - 0.10, x0 + 0.04, x) * sstep(x1 + 0.10, x1 - 0.04, x)
        dz = zl - z
        below = (dz > -0.01) * (up < 0.5)
        R = R + s * 0.50 * inx * below * sstep(0.75 + 0.5 * bb, 0.0, dz) * (0.45 + 0.55 * c)
        for xe in (x0, x1):
            Bk = np.maximum(Bk, s * below * np.exp(-((x - xe) / 0.075) ** 2) * sstep(1.3 + 0.9 * bb, 0.03, dz) * (0.5 + 0.5 * c))
    G = W.convex * sstep(0.45, 0.80, 0.6 * a + 0.4 * c)
    Gm = np.maximum(0.8 * W.convex * sstep(0.30, 0.72, 0.5 * a + 0.5 * bb), 0.75 * up * sstep(0.45, 0.80, a))
    G = np.where(met, Gm, G)
    if b.leaks:
        Bk = np.maximum(Bk, steel.streaks(P, N, b.leaks, 0.75, 0.045, seed=len(P)) * (0.6 + 0.4 * a))
    A = np.zeros(len(P))
    if ground:
        A = np.clip(np.exp(-np.clip(z, 0, None) / 0.22) * (0.55 + 0.5 * c), 0, 1) * (1 - 0.5 * up)
        R = R + 0.30 * sstep(1.3, 0.0, z) * (0.3 + 0.7 * bb)                   # hands, dogs, road spray
        G = np.where(met, np.maximum(G, 0.7 * sstep(0.45, 0.0, z) * sstep(0.4, 0.75, a)), G)   # kicked and scraped
    R = np.where(gls, 0.03 + 0.10 * a + (0.22 * sstep(BULK + 0.45, BULK, z) if ground else 0.0), R)
    G = np.where(gls | soft, 0.0, G)
    if "fabric" in names:
        fab = of("fabric")
        R = np.where(fab, 0.15 + 0.5 * up * sstep(0.4, 0.8, bb) + 0.3 * W.convex, R)       # pooled dirt on the top
        G = np.where(fab, up * (0.35 + 0.4 * a), G)                                        # sun-chalked
        Bk = np.where(fab, (1 - up) * 0.6 * sstep(0.55, 0.85, c), Bk)                      # dirt runs down the valance
    geo.set_wear(ob, np.clip(np.stack([R, G, Bk, A], axis=1), 0, 1), per="corner")


def done(ctx, b, name, M, brick=None, wear=None, **asset):
    mats = dict(M)
    if brick:
        mats["brick"] = M["brick" + brick]
    ob = b.finish(name, mats, ctx.kit)
    weather(ctx, b, ob, name, **(wear or {}))
    asset.setdefault("collision", "none")
    ctx.asset(ob, slots=SLOT_META, **asset)
    ctx.K[name] = ob
    return ob


# ------------------------------------------------------------------------------------------------ parts of a wall

def wall_opening(b, w, h, x0, x1, z0, z1, slot="brick", y0=0.0, y1=T):
    """Wall w x h between the planes y0 and y1 with an opening: two piers, a panel below, a panel above.
    The piers' side faces are the reveals."""
    bx(b, (0, y0, 0), (x0, y1, h), slot, axis="z")
    bx(b, (x1, y0, 0), (w, y1, h), slot, axis="z")
    bx(b, (x0, y0, 0), (x1, y1, z0), slot, axis="x")
    bx(b, (x0, y0, z1), (x1, y1, h), slot, axis="x")


def sill(b, x0, x1, zt, slot="stone", horn=0.10):
    """Cast-stone sill 100 mm thick, projecting 45 mm, with a weathered top and horns."""
    zb = zt - 0.10
    run(b, [(-0.22, zb), (0.033, zb), (0.045, zb + 0.012), (0.045, zt - 0.025), (-0.10, zt), (-0.22, zt)], x0 - horn, x1 + horn, slot)


def sash(b, x0, x1, z0, z1, y, slot, glass, st=0.045, bottom=None):
    d = 0.035
    bt = bottom or st
    kw = dict(ch=0.003, pin=False)
    bx(b, (x0, y, z0), (x0 + st, y + d, z1), slot, axis="z", **kw)
    bx(b, (x1 - st, y, z0), (x1, y + d, z1), slot, axis="z", **kw)
    bx(b, (x0 + st, y, z0), (x1 - st, y + d, z0 + bt), slot, axis="x", **kw)
    bx(b, (x0 + st, y, z1 - st), (x1 - st, y + d, z1), slot, axis="x", **kw)
    bx(b, (x0 + st - 0.008, y + d / 2 - 0.003, z0 + bt - 0.008), (x1 - st + 0.008, y + d / 2 + 0.003, z1 - st + 0.008), glass, axis="x")


def sash_window(b, x0, x1, z0, z1, y=0.10, frame="white", glass="glasswin"):
    """Double-hung window set 100 mm back in its opening: box frame, upper sash outside, lower sash inside."""
    fw, fd = 0.05, 0.11
    kw = dict(ch=0.003, pin=False)
    bx(b, (x0, y, z0), (x0 + fw, y + fd, z1), frame, axis="z", **kw)
    bx(b, (x1 - fw, y, z0), (x1, y + fd, z1), frame, axis="z", **kw)
    bx(b, (x0 + fw, y, z1 - fw), (x1 - fw, y + fd, z1), frame, axis="x", **kw)
    bx(b, (x0 + fw, y, z0), (x1 - fw, y + fd, z0 + 0.03), frame, axis="x", **kw)
    zm = (z0 + z1) / 2
    sash(b, x0 + fw, x1 - fw, zm - 0.02, z1 - fw, y + 0.015, frame, glass)
    sash(b, x0 + fw, x1 - fw, z0 + 0.03, zm + 0.02, y + 0.052, frame, glass, bottom=0.065)


BELT = [(0.0, 0.0), (0.13, 0.0), (0.13, 0.035), (0.16, 0.06), (0.18, 0.08), (0.18, 0.16), (0.0, 0.18)]


def belt(b, x0, x1, z, slot="stone"):
    """Belt course over the sign band: 180 mm high, 180 mm proud, with a wash on top."""
    run(b, [(p, z + q) for p, q in BELT], x0, x1, slot)


def gate(b, x0, x1, z1, rng, hood=0.30, slot="grey"):
    """Roll-down security gate, shut: curved slats at 75 mm pitch (dented low down), guide rails 100 mm wide, a
    hood box, a bottom bar with slide bolts, hasps and padlocks. Wider than 5.5 m it is two curtains and a post."""
    zc = z1 - hood + 0.03
    n = int(round(zc / 0.075))
    pitch = zc / n
    prof = [(0.045, 0.0)]
    for i in range(n):
        prof += [(0.058 + 0.022 * math.sin(math.pi * t) ** 0.6, (i + t) * pitch) for t in (0.0, 0.06, 0.16, 0.32, 0.5, 0.68, 0.84, 0.94)]
    prof += [(0.058, zc), (0.045, zc)]
    xm = (x0 + x1) / 2
    spans = [(x0, x1)] if x1 - x0 <= 5.5 else [(x0, xm + 0.05), (xm - 0.05, x1)]
    posts = sorted({x0, x1 - 0.10} | ({xm - 0.05} if len(spans) > 1 else set()))
    for px in posts:
        bx(b, (px, -0.115, 0), (px + 0.10, 0, zc), "trim", ch=0.004, axis="z", pin=False)
        b.rivets([(px + 0.05, -0.115, zz) for zz in np.arange(0.22, zc - 0.1, 0.48)], -Y, "trim", d=0.022, h=0.009, leak=0.5)
    for a, c in spans:
        p = b.prism(prof, (a + 0.06, 0, 0), -Y, Z, (c - a - 0.12, 0, 0), slot, step=0.10, pstep=9.0)
        v = p["v"]
        front = v[:, 1] < -0.05
        for _ in range(int(3 + (c - a) * 1.5)):                       # kicks and hand trucks
            cx, cz = rng.uniform(a + 0.25, c - 0.25), rng.uniform(0.12, zc * 0.42)
            amp, rad = rng.uniform(0.006, 0.026), rng.uniform(0.10, 0.32)
            v[:, 1] += front * amp * np.exp(-((v[:, 0] - cx) ** 2 + (v[:, 2] - cz) ** 2) / rad ** 2)
        tilt = rng.uniform(-0.010, 0.010)                             # the bottom bar is never level
        for part in (bx(b, (a + 0.10, -0.125, 0.004), (c - 0.10, -0.045, 0.016), slot, ch=0.003, axis="x", pin=False),
                     bx(b, (a + 0.10, -0.092, 0.016), (c - 0.10, -0.082, 0.075), slot, axis="x", pin=False)):
            part["v"][:, 2] += tilt * (part["v"][:, 0] - a) / (c - a) + abs(tilt)
        for hx, sgn in ((a + 0.42, -1), (c - 0.42, 1)):               # slide bolt into the guide, hasp, padlock
            zb = 0.115
            bx(b, (hx - 0.06, -0.090, zb - 0.028), (hx + 0.06, -0.078, zb + 0.028), "trim", ch=0.002, axis="x", pin=False)
            rod(b, (hx, -0.098, zb + 0.012), ((a + 0.07) if sgn < 0 else (c - 0.07), -0.098, zb + 0.012), 0.008, "chrome")
            for dz in (-0.012, 0.004):
                rod(b, (hx + 0.03 * sgn, -0.090, zb + dz), (hx + 0.03 * sgn, -0.112, zb + dz), 0.004, "chrome", n=6)
            rod(b, (hx + 0.03 * sgn, -0.110, zb - 0.014), (hx + 0.03 * sgn, -0.110, zb + 0.006), 0.004, "chrome", n=6)
            bx(b, (hx + 0.03 * sgn - 0.024, -0.124, zb - 0.062), (hx + 0.03 * sgn + 0.024, -0.100, zb - 0.014), "chrome", ch=0.004, axis="x", pin=False)
            b.leaks.append((hx, -0.09, zb))
        for hx in (a + (c - a) * 0.3, a + (c - a) * 0.7):             # lifting handles
            for dx in (-0.07, 0.07):
                rod(b, (hx + dx, -0.078, 0.30), (hx + dx, -0.115, 0.30), 0.006, "chrome", n=6)
            rod(b, (hx - 0.07, -0.115, 0.30), (hx + 0.07, -0.115, 0.30), 0.006, "chrome", n=6)
    bx(b, (x0, -0.27, z1 - hood), (x1, 0, z1), slot, ch=0.006, axis="x", pin=False)
    for zz in (z1 - hood + 0.03, z1 - 0.03):
        b.rivets([(xx, -0.27, zz) for xx in np.arange(x0 + 0.08, x1 - 0.05, 0.32)], -Y, slot, d=0.02, h=0.008, leak=0.15)
    b.leaks += [(x0 + 0.04, -0.27, z1 - hood), (x1 - 0.04, -0.27, z1 - hood)]


def glazing(b, a, c, head, bulk, depth=0.60):
    """Display window from a to c: bulkhead to 0.63, sill rail, mullions (no pane wider than 1.9 m), plate glass,
    and a shallow dark display space behind."""
    slot = {"tile": "tile", "metal": "trim", "wood": "wood"}[bulk]
    pin = bulk != "metal"
    bx(b, (a, -0.08, 0.0), (c, 0.0, BULK - 0.05), slot, axis="x", pin=pin)
    bx(b, (a, -0.095, 0.0), (c, -0.08, 0.10), "stone" if bulk == "tile" else "trim", ch=0.004, axis="x", pin=pin)
    if bulk != "tile":                                                # framed panels
        n = max(1, int(round((c - a) / 0.85)))
        pw = (c - a) / n
        for i in range(n + 1):
            xs = min(max(a + i * pw - 0.035, a), c - 0.07)
            bx(b, (xs, -0.094, 0.10), (xs + 0.07, -0.08, BULK - 0.05), slot, ch=0.003, axis="z", pin=False)
        bx(b, (a, -0.094, BULK - 0.13), (c, -0.08, BULK - 0.05), slot, ch=0.003, axis="x", pin=False)
    bx(b, (a, -0.12, BULK - 0.05), (c, 0.02, BULK), "trim", ch=0.004, axis="x", pin=False)
    n = max(1, int(math.ceil((c - a - 0.06) / 1.96 - 1e-6)))
    pw = (c - a - 0.06 * (n + 1)) / n
    for i in range(n + 1):
        xm = a + i * (pw + 0.06)
        bx(b, (xm, -0.075, BULK), (xm + 0.06, 0.005, head), "trim", ch=0.003, axis="z", pin=False)
    for i in range(n):
        xg = a + 0.06 + i * (pw + 0.06)
        bx(b, (xg - 0.012, -0.039, BULK - 0.01), (xg + pw + 0.012, -0.031, head + 0.01), "glass", axis="x")
    bx(b, (a, 0.0, BULK - 0.03), (c, depth, BULK), "interior", axis="x")
    bx(b, (a, depth - 0.02, BULK), (c, depth, head), "interior", axis="x")
    bx(b, (a, 0.02, head), (c, depth, head + 0.02), "interior", axis="x")
    bx(b, (a, 0.005, BULK), (a + 0.01, depth, head), "interior", axis="z")
    bx(b, (c - 0.01, 0.005, BULK), (c, depth, head), "interior", axis="z")


def shop_door(b, d0, head):
    """Shop door 1.25 m wide in a recess 0.36 m deep: metal-clad reveals, threshold, aluminium frame, glazed
    leaf with a kick plate and a push bar, solid transom."""
    d1, yr = d0 + DOOR_W, RECESS
    for xa in (d0, d1 - 0.02):
        bx(b, (xa, -0.075, 0.02), (xa + 0.02, yr + 0.06, head), "trim", axis="z", pin=False)
    bx(b, (d0, -0.09, 0.0), (d1, yr + 0.12, 0.02), "conc", ch=0.004, axis="x")
    bx(b, (d0, 0.02, head), (d1, yr + 0.06, BAND0), "trim", axis="x", pin=False)
    x0, x1, zt = d0 + 0.02, d1 - 0.02, 2.27
    kw = dict(ch=0.003, pin=False)
    for xa in (x0, x1 - 0.05):
        bx(b, (xa, yr, 0.02), (xa + 0.05, yr + 0.06, head), "alu", axis="z", **kw)
    bx(b, (x0 + 0.05, yr, zt), (x1 - 0.05, yr + 0.06, zt + 0.05), "alu", axis="x", **kw)
    bx(b, (x0 + 0.05, yr + 0.02, zt + 0.05), (x1 - 0.05, yr + 0.04, head), "trim", axis="x", pin=False)
    l0, l1, ya, yb = x0 + 0.055, x1 - 0.055, yr + 0.008, yr + 0.052
    bx(b, (l0, ya, 0.03), (l0 + 0.08, yb, zt - 0.005), "alu", axis="z", **kw)
    bx(b, (l1 - 0.08, ya, 0.03), (l1, yb, zt - 0.005), "alu", axis="z", **kw)
    bx(b, (l0 + 0.08, ya, 0.03), (l1 - 0.08, yb, 0.30), "alu", axis="x", **kw)
    bx(b, (l0 + 0.08, ya, zt - 0.085), (l1 - 0.08, yb, zt - 0.005), "alu", axis="x", **kw)
    bx(b, (l0 + 0.07, ya + 0.018, 0.29), (l1 - 0.07, ya + 0.026, zt - 0.075), "glass", axis="z")
    yp = ya - 0.055
    rod(b, (l0 + 0.10, yp, 1.045), (l1 - 0.10, yp, 1.045), 0.0125, "chrome", n=10)
    for xs in (l0 + 0.14, l1 - 0.14):
        rod(b, (xs, yp, 1.045), (xs, ya, 1.045), 0.008, "chrome", n=6)
    bx(b, (l1 - 0.065, ya - 0.006, 0.98), (l1 - 0.015, ya, 1.10), "chrome", ch=0.002, axis="z", pin=False)     # lock plate
    bx(b, (x0, yr + 0.10, 0.02), (x1, yr + 0.11, head), "interior", axis="z")


# -------------------------------------------------------------------------------------------------- ground floor

def m_pier(ctx, M, k):
    b = B(11)
    bx(b, (0, -PIER_OUT, 0), (PIER_W, T, GROUND), "brick", ch=0.006, axis="z")
    bx(b, (0, -PIER_OUT - 0.025, 0), (PIER_W, 0.0, 0.24), "stone", ch=0.010, axis="x")         # cast-stone base block
    return done(ctx, b, "SM_Facade_Pier_" + k, M, k, wear=dict(ground=True), collision="box",
                expect_size=(PIER_W, None, GROUND),
                notes="Shop-front end pier 0.32 m wide, 0.10 m proud of the building line, 3.65 m high, with a cast-stone base.")


def m_shopfront(ctx, M, name):
    s = shop_local(name)
    c = s["C"]
    b = B(len(name))
    rng = ctx.rng("shop", name)
    if s["d0"] is None:
        gate(b, 0.0, c, BAND0, rng)
        notes = "Shuttered shop front %.2f m between the piers: roll gate down, hood, guides, padlocked slide bolts." % c
        coll = "box"
    else:
        d0 = s["d0"]
        if d0 > 0.05:
            glazing(b, 0.0, d0, HEAD, s["bulk"])
        if c - d0 - DOOR_W > 0.05:
            glazing(b, d0 + DOOR_W, c, HEAD, s["bulk"])
        shop_door(b, d0, HEAD)
        bx(b, (0, -0.12, HEAD), (c, 0.02, BAND0), "trim", ch=0.004, axis="x", pin=False)
        notes = ("Shop front %.2f m between the piers (place at shop left end + 0.32): %s bulkhead, plate glass, door recess "
                 "0.36 m deep from x %.3f to %.3f (carve it out of the collider), shallow dark display space." % (c, s["bulk"], d0, d0 + DOOR_W))
        coll = "complex"
    return done(ctx, b, "SM_Facade_Shopfront_" + name, M, wear=dict(ground=True), collision=coll,
                expect_size=(c, None, BAND0), notes=notes)


def m_signband(ctx, M, name):
    s = shop_local(name)
    w, c = s["W"], s["C"]
    sw, sh = s["sign"]
    b = B(len(name) + 3)
    bx(b, (PIER_W, -0.11, 0), (w - PIER_W, 0, BAND_H), "trim", axis="x", pin=False)
    n = max(1, int(round(c / 1.22)))
    pw = c / n
    for i in range(n):                                                # sheet-metal fascia panels
        bx(b, (PIER_W + i * pw + 0.003, -0.13, 0.004), (PIER_W + (i + 1) * pw - 0.003, -0.11, BAND_H - 0.004), "trim", ch=0.003, axis="x", pin=False)
    sx0, sz0 = (w - sw) / 2, (BAND_H - sh) / 2
    bx(b, (sx0 - 0.02, -0.146, max(sz0 - 0.02, 0.0)), (sx0 + sw + 0.02, -0.13, min(sz0 + sh + 0.02, BAND_H)), "alu", ch=0.003, axis="x", pin=False)
    bx(b, (sx0, -0.150, sz0), (sx0 + sw, -0.146, sz0 + sh), "sign", axis="x", uv_org=(sx0, 0.0, sz0))
    belt(b, 0.0, w, BAND_H)
    mats = dict(M, sign=M["sign" + name])
    return done(ctx, b, "SM_Facade_SignBand_" + name, mats, wear=dict(ledges=[(0.0, w, BAND_H, 0.7)]),
                expect_size=(w, 0.18, BAND_H + 0.18),
                notes="Sign band of the shop (place at the shop's left end, 2.77 m up): fascia between the piers, belt course "
                      "over the whole front, sign face %.2f x %.2f m in slot M_Sign_%s with 0..1 UVs (u left to right, v up)." % (sw, sh, name))


def m_awning(ctx, M, length):
    """Lean-to awning: welded square-tube frame, cloth top sagging between the rafters, loose valance, end wings.
    Pivot: left end of the fixing line on the wall (2.75 m above the sidewalk)."""
    b = B(int(length * 10))
    rng = ctx.rng("awning", length)
    out, zw, zf, zv, za = 1.35, 0.10, -0.38, -0.60, -0.59
    S = "grey"
    nr = max(2, int(round(length / 1.25)))
    xr = np.linspace(0.0125, length - 0.0125, nr + 1)                 # rafters
    bar(b, (0, -0.0125, zw - 0.02), (length, -0.0125, zw - 0.02), 0.025, 0.025, S, ch=0.003)
    bar(b, (0, -out + 0.0125, zf - 0.015), (length, -out + 0.0125, zf - 0.015), 0.025, 0.025, S, ch=0.003)
    for xx in xr:
        bar(b, (xx, -0.02, zw - 0.022), (xx, -out + 0.02, zf - 0.017), 0.025, 0.025, S, ch=0.003)
    na = max(2, int(round(length / 2.6)) + 1)
    for xx in np.linspace(0.02, length - 0.02, na):                   # arms 3 x 4 cm and their struts
        bar(b, (xx, 0.0, za + 0.02), (xx, -out + 0.02, za + 0.02), 0.03, 0.04, S, ch=0.003)
        bar(b, (xx, -out + 0.035, za + 0.04), (xx, -out + 0.035, zf - 0.02), 0.03, 0.03, S, up=-Y, ch=0.003)
        bx(b, (xx - 0.05, -0.008, za - 0.05), (xx + 0.05, 0.0, za + 0.09), S, ch=0.002, axis="z", pin=False)
        b.rivets([(xx, -0.008, za - 0.03), (xx, -0.008, za + 0.07)], -Y, S, d=0.02, h=0.009, leak=1.0)
    # cloth top: rows from the front edge up to the wall
    nc, nrow = int(length / 0.10) + 1, 13
    xs = np.linspace(0.0, length, nc)
    t = np.linspace(0.0, 1.0, nrow)[:, None]
    pitch = xr[1] - xr[0]
    bay = np.clip(((xs - xr[0]) / pitch).astype(int), 0, nr - 1)
    sag = 0.016 * np.sin(np.pi * ((xs - xr[0]) / pitch % 1.0)) ** 2 * (0.6 + 0.8 * rng.random(nr))[bay]
    pool = 0.02 * np.exp(-((xs - length * rng.uniform(0.3, 0.7)) / 0.5) ** 2)
    top = np.zeros((nrow, nc, 3))
    top[..., 0] = xs[None, :]
    top[..., 1] = -(out + 0.004) * (1 - t)
    top[..., 2] = zf + 0.004 + (zw - zf) * t - (sag + pool)[None, :] * np.sin(np.pi * t) ** 0.8
    sheet(b, top, 0.003, "fabric", vdir=Y, fdir=X)
    # valance: rows from the bottom up, a scalloped hem, hanging a little out of true
    zr = np.linspace(0.0, 1.0, 5)[:, None]
    hem = zv + 0.028 * np.abs(np.sin(np.pi * xs / 0.42))
    val = np.zeros((5, nc, 3))
    val[..., 0] = xs[None, :]
    val[..., 2] = hem[None, :] + (zf + 0.004 - hem[None, :]) * zr
    val[..., 1] = -(out + 0.006) - 0.012 * np.sin(xs[None, :] * 7.0 + 1.0) * (1 - zr)
    sheet(b, val, 0.003, "fabric")
    for xe, sgn in ((0.0, 1.0), (length, -1.0)):                      # end wings
        a = np.linspace(0.0, 1.0, 9)[None, :] if sgn > 0 else np.linspace(1.0, 0.0, 9)[None, :]
        zt_, zb_ = zw + (zf - zw) * a, za + (zv - za) * a
        wing = np.zeros((5, 9, 3))
        wing[..., 0] = xe - sgn * 0.004
        wing[..., 1] = -out * a
        wing[..., 2] = zb_ + (zt_ - zb_) * zr
        sheet(b, wing, 0.003, "fabric")
    b.leaks += [(0.02, -0.01, za), (length - 0.02, -0.01, za)]
    return done(ctx, b, "SM_Facade_Awning_" + cm(length), M, expect_size=(length, None, None),
                notes="Fabric lean-to awning %.2f m long, projecting 1.35 m: fixed 2.75 to 2.85 m above the sidewalk, front edge "
                      "2.37 m, valance to 2.15 m. Pivot at the left end of the fixing line. Tint the cloth per shop; no collision." % length)


def m_resentry(ctx, M, k="Red"):
    """Tenement residents' entrance, 2.8 m wide: brick panel 0.10 proud, two-step stoop, panelled door, transom."""
    b = B(21)
    w, x0, x1 = 2.8, 0.90, 1.90
    wall_opening(b, w, GROUND, x0, x1, 0.0, 2.85 + 0.20, y0=-PIER_OUT)
    bx(b, (x0 - 0.20, -PIER_OUT - 0.02, 2.85), (x1 + 0.20, T, 3.05), "stone", ch=0.008, axis="x")          # lintel
    bx(b, (0.50, -0.75, 0.0), (2.30, -PIER_OUT, 0.16), "conc", ch=0.012, axis="x")                          # stoop
    bx(b, (0.70, -0.45, 0.16), (2.10, 0.12, 0.32), "conc", ch=0.012, axis="x")
    kw = dict(ch=0.004, pin=False)
    for xa in (x0, x1 - 0.06):                                                                             # frame
        bx(b, (xa, 0.0, 0.32), (xa + 0.06, 0.10, 2.85), "door", axis="z", **kw)
    bx(b, (x0 + 0.06, 0.0, 2.35), (x1 - 0.06, 0.10, 2.41), "door", axis="x", **kw)
    bx(b, (x0 + 0.06, 0.0, 2.80), (x1 - 0.06, 0.10, 2.85), "door", axis="x", **kw)
    l0, l1 = x0 + 0.065, x1 - 0.065
    bx(b, (l0, 0.035, 0.325), (l1, 0.080, 2.345), "door", axis="z", **kw)                                   # leaf
    pwid = (l1 - l0 - 0.36) / 2
    for i in range(2):                                                                                      # six raised panels
        for (pz0, pz1) in ((0.62, 1.05), (1.17, 1.75), (1.87, 2.24)):
            px = l0 + 0.12 + i * (pwid + 0.12)
            bx(b, (px, 0.022, pz0), (px + pwid, 0.035, pz1), "door", ch=0.008, axis="z", pin=False)
    bx(b, (l0 + 0.02, 0.031, 0.335), (l1 - 0.02, 0.035, 0.55), "chrome", axis="x", pin=False)               # kick plate
    rod(b, (l1 - 0.07, 0.035, 1.12), (l1 - 0.07, -0.02, 1.12), 0.011, "chrome", n=8)                        # knob
    rod(b, (l1 - 0.07, -0.02, 1.12), (l1 - 0.07, -0.045, 1.12), 0.027, "chrome", n=12)
    bx(b, (l0 + 0.30, 0.031, 1.08), (l1 - 0.30, 0.035, 1.13), "chrome", axis="x", pin=False)                # letter plate
    bx(b, (x0 + 0.075, 0.045, 2.425), (x1 - 0.075, 0.053, 2.785), "glasswin", axis="x")                     # transom light
    bx(b, (x0 + 0.06, 0.04, 2.41), (x0 + 0.08, 0.06, 2.80), "door", axis="z", pin=False)
    bx(b, (x1 - 0.08, 0.04, 2.41), (x1 - 0.06, 0.06, 2.80), "door", axis="z", pin=False)
    bx(b, (x0, T - 0.012, 0.32), (x1, T - 0.002, 2.85), "interior", axis="z")
    bx(b, (x1 + 0.16, -PIER_OUT - 0.022, 1.25), (x1 + 0.30, -PIER_OUT, 1.62), "alu", ch=0.003, axis="z", pin=False)   # bell panel
    belt(b, 0.0, w, 3.51)
    return done(ctx, b, "SM_Facade_ResEntry_" + k, M, k, wear=dict(ground=True, ledges=[(0.0, w, 3.51, 0.8), (x0 - 0.2, x1 + 0.2, 2.85, 0.6)]),
                collision="box", expect_size=(w, None, 3.69),
                notes="Residents' entrance bay 2.8 m wide: brick 0.10 m proud, stoop of two steps (no collision in the game), "
                      "panelled door 1.0 m, transom light, cast-stone lintel, belt course.")


def m_vestibule(ctx, M, k="Red"):
    """S2's shared vestibule: a pocket 2.2 m wide and 2.4 m deep with display windows on both sides, a small roll
    gate in the brick back wall and a concrete soffit."""
    b = B(31)
    w, d, hd = 2.2, 2.4, 2.55
    rng = ctx.rng("vestibule")
    bx(b, (0, -0.02, -0.10), (w, d, 0.0), "conc", axis="y")                                   # floor at sidewalk height
    for rot, loc in ((90.0, (0.0, 0.0, 0.0)), (-90.0, (w, d, 0.0))):                          # the two glazed sides
        s_ = B(32)
        glazing(s_, 0.0, d, hd, "metal", depth=0.05)
        bx(s_, (0, -0.12, hd), (d, 0.02, hd + 0.08), "trim", ch=0.004, axis="x", pin=False)
        sub(b, s_, rot, loc)
    wall_opening(b, w, hd + 0.08, 0.40, 1.80, 0.0, 2.50, y0=d, y1=d + T)                      # back wall
    g_ = B(33)
    gate(g_, 0.40, 1.80, 2.50, rng, hood=0.25)
    sub(b, g_, 0.0, (0.0, d + 0.10, 0.0))
    bx(b, (0.40, d + 0.10, 0.0), (1.80, d + 0.12, 2.5), "interior", axis="z")
    bx(b, (0, 0.0, hd + 0.08), (w, d + T, GROUND), "conc", axis="y")                          # soffit block
    bx(b, (0, -0.06, hd + 0.08), (w, 0.0, 3.51), "stone", ch=0.008, axis="x")                 # its street face
    rod(b, (w / 2, 1.2, hd + 0.08), (w / 2, 1.2, hd + 0.05), 0.11, "alu", n=16)               # recessed lamp
    belt(b, 0.0, w, 3.51)
    return done(ctx, b, "SM_Facade_Vestibule_" + k, M, k, wear=dict(ground=True, ledges=[(0.0, w, 3.51, 0.8)]),
                collision="complex", expect_size=(w, None, None),
                notes="Vestibule pocket 2.2 x 2.4 m between the pawn shop and the record shop: glazed sides, brick back wall "
                      "with a roll gate 1.4 x 2.25 m, concrete soffit from 2.63 m, floor at sidewalk height.")


# -------------------------------------------------------------------------------------------------- upper floors

def m_bay(ctx, M, k, window=True):
    b = B(41)
    ledges = []
    if window:
        x0, x1, z0, z1, lint = (BAY - WIN_W) / 2, (BAY + WIN_W) / 2, WIN_SILL, WIN_SILL + WIN_H, 0.203
        wall_opening(b, BAY, STOREY, x0, x1, z0 - 0.10, z1 + lint)
        sill(b, x0, x1, z0)
        if k == "Buff":                                               # soldier course: the bond turned on end
            bx(b, (x0 - 0.10, -0.008, z1), (x1 + 0.10, T, z1 + lint), "brick", axis="x", vdir=X, fdir=Z)
        else:
            bx(b, (x0 - 0.15, -0.012, z1), (x1 + 0.15, T, z1 + lint), "stone", ch=0.006, axis="x")
        sash_window(b, x0, x1, z0, z1)
        bx(b, (x0 - 0.02, T - 0.012, z0 - 0.02), (x1 + 0.02, T - 0.002, z1 + 0.02), "interior", axis="z")
        ledges = [(x0 - 0.10, x1 + 0.10, z0 - 0.10, 1.0)]
    else:
        bx(b, (0, 0, 0), (BAY, T, STOREY), "brick", axis="x")
    name = "SM_Facade_Bay%s_%s" % ("Window" if window else "Blank", k)
    notes = ("Upper-storey bay 3.1 x 3.1 m, wall 0.30 m: double-hung window in an opening 1.24 x 1.736 m, sill 0.60 m above the "
             "floor line, cast-stone sill, %s. Window centre for props: x 1.55, z 0.60." % ("soldier-course head" if k == "Buff" else "cast-stone lintel")
             if window else "Blank brick bay 3.1 x 3.1 m, wall 0.30 m.")
    return done(ctx, b, name, M, k, wear=dict(ledges=ledges, fade=(BAY, STOREY)), collision="box",
                expect_size=(BAY, None, STOREY), notes=notes)


def m_fill(ctx, M, k, w, parapet=False):
    b = B(43)
    if parapet:
        parapet_parts(b, w)
        return done(ctx, b, "SM_Facade_ParapetFill_%s_%s" % (cm(w), k), M, k, wear=dict(ledges=[(-1.0, w + 1.0, 0.90, 0.9)]),
                    collision="box", expect_size=(w, 0.38, 0.97), notes="Parapet over an end pier, %.2f m." % w)
    bx(b, (0, 0, 0), (w, T, STOREY), "brick", axis="z")
    return done(ctx, b, "SM_Facade_Fill_%s_%s" % (cm(w), k), M, k, collision="box", expect_size=(w, T, STOREY),
                notes="Plain brick end pier of an upper storey, %.2f m wide (the bay grid is centred on the front)." % w)


def m_corner(ctx, M, k):
    """Corner return: the face brick turning 0.60 m down the side wall, with a chamfered arris at both ends.
    A wall module like the others: stand it against the side plane, behind the front wall."""
    b = B(45)
    bx(b, (0, 0, 0), (0.60, T, STOREY), "brick", ch=0.006, axis="z")
    return done(ctx, b, "SM_Facade_CornerReturn_" + k, M, k, collision="box", expect_size=(0.60, T, STOREY),
                notes="Corner return 0.60 x 3.1 m: the street brick carried round onto the side wall, where common brick takes over.")


# ------------------------------------------------------------------------------------------------ top of the wall

CORNICE = [(0.0, -0.42), (0.025, -0.42), (0.025, -0.18), (0.21, -0.18), (0.21, -0.10), (0.225, -0.075), (0.24, -0.06),
           (0.24, 0.05), (0.33, 0.05), (0.33, 0.075), (0.355, 0.10), (0.375, 0.16), (0.385, 0.23), (0.40, 0.28),
           (0.42, 0.30), (0.42, 0.38), (0.0, 0.38)]
BRACKET = [(0.025, -0.42), (0.07, -0.42), (0.085, -0.40), (0.09, -0.36), (0.11, -0.31), (0.16, -0.27), (0.20, -0.24),
           (0.20, -0.18), (0.025, -0.18)]


def cornice_parts(b, length, end=None, S="grey"):
    """Pressed-metal cornice at the roof line (z = 0): crown 0.42 proud, bed mould, a row of scrolled brackets
    0.22 wide at 0.62 m centres, small dentils. end 'L' or 'R': an end block with a drop console."""
    # with an end block the run stops 2 mm inside it: coplanar end caps would shadow each other in a path tracer
    run(b, CORNICE, 0.002 if end == "L" else 0.0, length - (0.002 if end == "R" else 0.0), S, pin=False, pstep=0.12)
    n = int(round(length / 0.62))
    if n >= 1:
        for i in range(n):
            xc = (i + 0.5) * length / n
            b.prism(BRACKET, (xc - 0.11, 0, 0), -Y, Z, (0.22, 0, 0), S, pstep=9.0)
            b.leaks.append((xc, -0.07, -0.42))
    nd = max(1, int(round(length / 0.1033)))
    for i in range(nd):
        xd = (i + 0.2) * length / nd
        bx(b, (xd, -0.235, -0.17), (xd + 0.6 * length / nd, -0.21, -0.115), S, pin=False)
    for xs in np.arange(0.775, length - 0.1, 1.55):                    # lapped sheet joints
        b.prism([(p + 0.004 if p > 0 else p, q + (0.004 if q > 0.3 else 0.0)) for p, q in CORNICE[3:]] + [(0.0, -0.18)],
                (xs - 0.02, 0, 0), -Y, Z, (0.04, 0, 0), S, pstep=9.0)
    if end:
        xe = 0.0 if end == "L" else length - 0.14
        big = [(p * 1.07 if p > 0 else 0.0, q * 1.05 + 0.005) for p, q in CORNICE[2:]] + [(0.0, -0.18)]
        b.prism(big, (xe, 0, 0), -Y, Z, (0.14, 0, 0), S, pstep=9.0)
        b.prism([(p * 1.25 if p > 0.03 else p, -0.18 + (q + 0.18) * 1.9) for p, q in BRACKET], (xe, 0, 0), -Y, Z, (0.14, 0, 0), S, pstep=9.0)
        b.leaks.append((xe + 0.07, -0.08, -0.62))


def m_cornice(ctx, M, length, end=None):
    b = B(51)
    cornice_parts(b, length, end)
    name = "SM_Facade_Cornice_310" if end is None else "SM_Facade_CorniceEnd_%s_%s" % (end, cm(length))
    return done(ctx, b, name, M, expect_size=(length, None, None),
                notes="Pressed-metal cornice, %s. Pivot on the wall at the roof line; 0.42 m projection, "
                      "brackets at 0.62 m. No collision." % ("3.1 m run" if end is None else "%.2f m end piece (%s) with console" % (length, end)))


def parapet_parts(b, w, slot="brick", h=0.90):
    bx(b, (0, 0, 0), (w, T, h), slot, axis="x" if w > h else "z")
    n = max(1, int(round(w / 0.775)))
    for i in range(n):                                                # coping stones with open joints
        x0, x1 = i * w / n + (0.004 if i else 0.0), (i + 1) * w / n - (0.004 if i < n - 1 else 0.0)
        run(b, [(-T - 0.04, h), (0.04, h), (0.04, h + 0.07), (-T - 0.04, h + 0.055)], x0, x1, "stone")


def m_parapet(ctx, M, k):
    b = B(53)
    parapet_parts(b, BAY, "brick")
    return done(ctx, b, "SM_Facade_Parapet_310_" + k, M, k, wear=dict(ledges=[(-1.0, BAY + 1.0, 0.90, 0.9)], fade=(BAY, 9.0)),
                collision="box", expect_size=(BAY, 0.38, 0.97),
                notes="Roof parapet 3.1 m: brick 0.30 x 0.90 m above the roof line, cast-stone coping 70 mm overhanging 40 mm.")


def m_partycap(ctx, M):
    """Party-wall parapet in common brick with a camelback tile coping."""
    b = B(55)
    bx(b, (0, 0, 0), (BAY, T, 0.90), "common", axis="x")
    for i in range(5):
        x0, x1 = i * 0.62 + (0.004 if i else 0.0), (i + 1) * 0.62 - (0.004 if i < 4 else 0.0)
        run(b, [(-T - 0.035, 0.90), (0.035, 0.90), (0.035, 0.93), (-0.06, 0.975), (-0.15, 0.99), (-0.24, 0.975), (-T - 0.035, 0.93)],
            x0, x1, "stone")
    return done(ctx, b, "SM_Facade_PartyWallCap_310", M, wear=dict(ledges=[(-1.0, BAY + 1.0, 0.90, 1.0)], fade=(BAY, 9.0)),
                collision="box", expect_size=(BAY, None, 0.99),
                notes="Party-wall cap 3.1 m: common-brick parapet 0.90 m with a camelback coping, for side and rear walls.")


def m_roof(ctx, M):
    b = B(57)
    bx(b, (0, 0, -0.20), (4.0, 4.0, 0.0), "roof", axis="x")
    for yy in (1.0, 2.0, 3.0):                                         # laps of the roofing rolls
        bx(b, (0, yy - 0.05, 0.0), (4.0, yy + 0.05, 0.004), "roof", axis="x")
    return done(ctx, b, "SM_Facade_RoofPanel_4m", M, collision="box", expect_size=(4.0, 4.0, None),
                notes="Flat roof panel 4 x 4 m, bitumen felt with lapped rolls; top at z = 0 (the roof line). Pivot at a corner.")


# ---------------------------------------------------------------------------------------------------- roof items

def m_tank(ctx, M):
    """Rooftop water tank: timber staves 2.6 m across from 2.13 to 4.10 m with five hoops and a conical roof to
    4.98 m, on a braced steel stand 1.9 m tall, with a riser pipe and a ladder. Prop pivot: centre, on the roof."""
    b = B(61)
    S, L = "black", 1.05
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.prism(steel.ibeam(0.15, 0.13, 0.010, 0.007), (sx * L, sy * L - 0.075, 0.02), X, Y, (0, 0, 1.73), S, pstep=9.0)
            bx(b, (sx * L - 0.15, sy * L - 0.15, 0.0), (sx * L + 0.15, sy * L + 0.15, 0.02), S, ch=0.003, axis="x", pin=False)
            b.rivets([(sx * L + dx, sy * L + dy, 0.02) for dx in (-0.11, 0.11) for dy in (-0.11, 0.11)], Z, S, d=0.03, h=0.014, leak=0.0)
    for sy in (-1, 1):                                                 # main beams, then cross beams
        b.prism(steel.ibeam(0.18, 0.12, 0.011, 0.007), (-L - 0.2, sy * L, 1.75), Y, Z, (2 * L + 0.4, 0, 0), S, pstep=9.0)
    for xx in np.linspace(-1.0, 1.0, 5):
        bx(b, (xx - 0.05, -1.33, 1.93), (xx + 0.05, 1.33, 2.05), "timber", ch=0.004, axis="y")
    for (p0, p1) in (((-L, -L), (L, -L)), ((L, -L), (L, L)), ((L, L), (-L, L)), ((-L, L), (-L, -L))):   # rod bracing
        rod(b, (p0[0], p0[1], 0.12), (p1[0], p1[1], 1.68), 0.011, S, n=6)
        rod(b, (p1[0], p1[1], 0.12), (p0[0], p0[1], 1.68), 0.011, S, n=6)
        bar(b, (p0[0], p0[1], 0.95), (p1[0], p1[1], 0.95), 0.06, 0.06, S, ch=0.004)
    r, ns = 1.30, 44
    for yy in np.linspace(-1.2, 1.2, 9):                               # floor planks
        hx = math.sqrt(max(r * r - yy * yy, 0.01)) + 0.04
        bx(b, (-hx, yy - 0.14, 2.05), (hx, yy + 0.14, 2.13), "timber", axis="x")
    prof = []
    for i in range(ns):                                                # staves with a V joint
        a0, a1 = 2 * math.pi * i / ns, 2 * math.pi * (i + 1) / ns
        e = 0.004 / r
        prof += [(r * math.cos(a0 + e), r * math.sin(a0 + e)), (r * math.cos(a1 - e), r * math.sin(a1 - e)),
                 ((r - 0.008) * math.cos(a1), (r - 0.008) * math.sin(a1))]
    b.prism(prof, (0, 0, 2.13), X, Y, (0, 0, 1.97), "timber", step=0.25, pstep=9.0, fdir=X)
    for i, zh in enumerate(np.linspace(2.28, 3.95, 5)):                # hoops and their lugs
        hoop = geo.tube(r + 0.008, r - 0.002, 0.05, 64)
        geo.transform(hoop, loc=(0, 0, zh))
        b.absorb(hoop, S)
        a = 0.5 + i * 1.3
        bx(b, (-0.07, -0.02, zh - 0.01), (0.07, 0.03, zh + 0.06), S, ch=0.004, axis="x", pin=False)
        p = b.parts[-1]
        ca, sa = math.cos(a), math.sin(a)
        v = p["v"].copy()
        p["v"][:, 0] = (r + 0.02 + v[:, 1]) * ca + v[:, 0] * sa
        p["v"][:, 1] = (r + 0.02 + v[:, 1]) * sa - v[:, 0] * ca
        b.leaks.append(((r + 0.01) * ca, (r + 0.01) * sa, zh))
    cone = geo.revolve([(0.0, 4.07), (1.40, 4.07), (1.40, 4.11), (0.10, 4.94), (0.0, 4.98)], 44)
    b.absorb(cone, "timber")
    rod(b, (0.5, 0.0, 0.0), (0.5, 0.0, 2.06), 0.075, S, n=14)          # riser
    rod(b, (0.5, 0.0, 0.25), (0.5, 0.0, 0.31), 0.10, S, n=14)
    for sy in (-0.2, 0.2):                                             # ladder up the east side
        bar(b, (r + 0.14, sy, 0.0), (r + 0.14, sy, 4.25), 0.05, 0.01, S, up=X, ch=0.002)
    for zz in np.arange(0.3, 4.2, 0.30):
        rod(b, (r + 0.14, -0.2, zz), (r + 0.14, 0.2, zz), 0.0095, S, n=6)
    for zz in (2.4, 3.9):
        for sy in (-0.2, 0.2):
            rod(b, (r, sy, zz), (r + 0.14, sy, zz), 0.008, S, n=6)
    return done(ctx, b, "SM_Facade_WaterTank", M, expect_size=(2.8, 2.8, 4.98),
                notes="Rooftop water tank (catalogue water_tower, 2.8 x 2.74 x 4.98 m): timber staves, five iron hoops, "
                      "conical roof, braced steel stand, riser, ladder. Prop pivot (centre, on the roof). No collision.")


def m_bulkhead(ctx, M, k):
    """Stair bulkhead: brick box 3.0 x 3.5 m, 2.6 m high, steel door on the +X side, slab roof, vent pipe."""
    s_ = B(63)
    wall_opening(s_, 3.5, 2.42, 1.20, 2.20, 0.0, 2.10)                                       # door wall
    bx(s_, (1.14, -0.012, 2.10), (2.26, T, 2.30), "stone", ch=0.006, axis="x")
    bx(s_, (1.20, 0.05, 0.0), (2.20, 0.10, 2.10), "trim", ch=0.003, axis="z", pin=False)      # steel door in its frame
    for xa in (1.20, 2.16):
        bx(s_, (xa, 0.03, 0.0), (xa + 0.04, 0.12, 2.10), "trim", axis="z", pin=False)
    rod(s_, (2.08, 0.05, 1.05), (2.08, -0.01, 1.05), 0.012, "chrome", n=8)
    rod(s_, (2.08, -0.01, 1.05), (1.96, -0.01, 1.05), 0.010, "chrome", n=8)
    bx(s_, (0, T, 0), (T, 3.0, 2.42), "brick", axis="y")
    bx(s_, (3.5 - T, T, 0), (3.5, 3.0, 2.42), "brick", axis="y")
    bx(s_, (T, 3.0 - T, 0), (3.5 - T, 3.0, 2.42), "brick", axis="x")
    bx(s_, (-0.05, -0.05, 2.42), (3.55, 3.05, 2.60), "stone", ch=0.012, axis="x")             # slab with a drip edge
    bx(s_, (0.0, 0.0, 2.60), (3.5, 3.0, 2.605), "roof", axis="x")
    rod(s_, (0.8, 2.2, 2.60), (0.8, 2.2, 3.0), 0.05, "grey", n=12)
    rod(s_, (0.8, 2.2, 3.0), (0.8, 2.2, 3.04), 0.085, "grey", n=12)
    b = B(64)
    sub(b, s_, 90.0, (1.5, -1.75, 0.0))                                # door wall onto +X, pivot to the centre
    return done(ctx, b, "SM_Facade_StairBulkhead_" + k, M, k, wear=dict(ledges=[(-9, 9, 2.42, 0.8)]), collision="box",
                expect_size=(3.1, 3.6, None),
                notes="Stair bulkhead 3.0 x 3.5 m in plan, 2.6 m high (collider tag bulkhead): steel door on +X, slab roof, vent.")


# --------------------------------------------------------------------------------------------------- fire escape

def m_balcony(ctx, M):
    """One fire-escape balcony 2.99 x 1.07 m: flat-bar slats 38 x 6 mm at 66 mm centres, a hatch at the left end,
    square balusters under a flat top rail 0.95 m above the landing. Pivot: left end, on the wall, landing top."""
    b = B(71)
    S, Lx, D = "black", ESC_L, ESC_D
    fr = dict(ch=0.002)
    bar(b, (0, -D + 0.005, -0.033), (Lx, -D + 0.005, -0.033), 0.01, 0.065, S, **fr)             # frame on edge
    bar(b, (0, -0.03, -0.033), (Lx, -0.03, -0.033), 0.01, 0.065, S, **fr)
    for xx in (0.005, Lx - 0.005):
        bar(b, (xx, 0.0, -0.033), (xx, -D, -0.033), 0.01, 0.065, S, **fr)
    for xx in np.arange(0.6, Lx - 0.3, 0.6):                                                     # bearers
        bar(b, (xx, -0.03, -0.036), (xx, -D, -0.036), 0.01, 0.055, S, **fr)
    hx0, hx1, hy0, hy1 = 0.12, 0.87, -0.70, -0.06                                                # hatch
    bar(b, (hx1, hy1 + 0.03, -0.036), (hx1, hy0 - 0.03, -0.036), 0.01, 0.055, S, **fr)
    bar(b, (hx0, hy0, -0.036), (hx1, hy0, -0.036), 0.01, 0.055, S, **fr)
    for yy in np.arange(-0.065, -D + 0.03, -0.066):                                              # slats
        x0 = hx1 if hy0 - 0.02 < yy < hy1 + 0.02 else 0.01
        bx(b, (x0, yy - 0.019, -0.006), (Lx - 0.01, yy + 0.019, 0.0), S, ch=0.0015, axis="x", pin=False)
    zr = ESC_RAIL
    rails = (((0.0125, 0.0), (0.0125, -D + 0.0125), -X), ((0.0125, -D + 0.0125), (Lx - 0.0125, -D + 0.0125), -Y),
             ((Lx - 0.0125, -D + 0.0125), (Lx - 0.0125, 0.0), X))
    for (p0, p1, nrm) in rails:                                                                  # nrm: outward
        p0, p1 = np.array(p0), np.array(p1)
        ln = float(np.linalg.norm(p1 - p0))
        dr = (p1 - p0) / ln
        bar(b, (*p0, zr - 0.006), (*p1, zr - 0.006), 0.045, 0.012, S, ch=0.003)                  # top rail, flat
        bar(b, (*p0, 0.09), (*p1, 0.09), 0.012, 0.035, S, ch=0.002)                              # bottom rail, on edge
        nb = int(ln / 0.115)
        pts = [p0 + dr * (i + 0.5) * ln / nb for i in range(nb)]
        for q in pts:                                                                            # balusters 13 mm square
            bar(b, (q[0], q[1], 0.0), (q[0], q[1], zr - 0.012), 0.013, 0.013, S, up=X if abs(dr[0]) > 0.5 else Y, ch=0.002)
        b.rivets([(q[0] + nrm[0] * 0.007, q[1] + nrm[1] * 0.007, 0.09) for q in pts], nrm, S, d=0.014, h=0.006, leak=0.2)
    for (cx, cy) in ((0.0125, -D + 0.0125), (Lx - 0.0125, -D + 0.0125)):                         # corner posts
        bar(b, (cx, cy, -0.06), (cx, cy, zr), 0.03, 0.03, S, up=Y, ch=0.003)
    for xx in (0.0125, Lx - 0.0125):                                                             # wall anchors
        for zz in (-0.033, zr - 0.006):
            bx(b, (xx - 0.04, -0.008, zz - 0.05), (xx + 0.04, 0.0, zz + 0.05), S, ch=0.002, axis="z", pin=False)
            b.rivets([(xx, -0.008, zz + 0.03), (xx, -0.008, zz - 0.03)], -Y, S, d=0.022, h=0.01, leak=0.0)
            b.leaks.append((xx, -0.004, zz - 0.05))
    return done(ctx, b, "SM_Facade_FireEscape_Balcony", M, expect_size=(ESC_L, ESC_D, None),
                notes="Fire-escape balcony (catalogue fire_escape 3.0 x 1.1 m): slatted landing, hatch 0.75 x 0.64 m at the left "
                      "end, railing 0.95 m. Pivot: left end on the wall at the landing top (4.05, 7.15 ... above the road). No collision.")


def m_stair(ctx, M):
    """Stair flight from one balcony up through the hatch of the next (rise 3.1 m, about 64 degrees)."""
    b = B(73)
    S = "black"
    rise, n = STOREY, 13
    xt, xb_ = 0.20, 0.20 + rise / math.tan(math.radians(64.0))
    y0, y1 = -0.10, -0.66
    dx, dz = (xb_ - xt) / n, rise / n
    up = steel.unit(np.cross((xt - xb_, 0, rise), Y))
    for yy in (y0, y1):
        bar(b, (xb_ + 0.05, yy, -0.11), (xt - 0.06, yy, rise + 0.13), 0.010, 0.13, S, up=up, ch=0.002)
    for i in range(1, n):                                              # treads: two flat bars each
        tx, tz = xb_ - i * dx, i * dz
        for off in (-0.035, 0.035):
            bx(b, (tx + off - 0.028, y1 + 0.005, tz - 0.006), (tx + off + 0.028, y0 - 0.005, tz), S, ch=0.0015, axis="y", pin=False)
        b.rivets([(tx, yy + sg * 0.005, tz - 0.02) for yy, sg in ((y0, 1), (y1, -1))], [(0, 1, 0), (0, -1, 0)], S, d=0.014, h=0.006, leak=0.25)
    for yy in (y0, y1):                                                # handrails on three posts
        hr0, hr1 = np.array((xb_ + 0.02, yy, 0.90)), np.array((xt + 0.02, yy, rise + 0.90))
        rod(b, hr0, hr1, 0.012, S, n=8)
        for f in (0.04, 0.5, 0.96):
            q = hr0 + (hr1 - hr0) * f
            rod(b, (q[0] - 0.02, yy, q[2] - 0.90), q, 0.008, S, n=6)
    return done(ctx, b, "SM_Facade_FireEscape_Stair", M, expect_size=(None, None, None),
                notes="Fire-escape stair between two balconies 3.1 m apart: flat-bar stringers, 12 slatted treads, two handrails. "
                      "Same pivot as the lower balcony; it comes up through the hatch of the balcony above. No collision.")


def m_ladder(ctx, M):
    """Drop ladder, hauled up: hangs in the hatch of the lowest balcony, foot 1.85 m below the landing."""
    b = B(75)
    S = "black"
    xc, ya, yb, z0, z1 = 0.50, -0.20, -0.56, -1.85, 1.15
    for yy in (ya, yb):
        bar(b, (xc, yy, z0), (xc, yy, z1), 0.05, 0.010, S, up=Y, ch=0.002)
    for zz in np.arange(z0 + 0.15, z1 - 0.1, 0.30):
        rod(b, (xc, ya, zz), (xc, yb, zz), 0.0095, S, n=6)
    for yy in (ya, yb):                                                # hooks over the top, guides on the landing
        rod(b, (xc, yy, z1), (xc - 0.10, yy, z1 + 0.06), 0.008, S, n=6)
        rod(b, (xc - 0.10, yy, z1 + 0.06), (xc - 0.16, yy, z1 - 0.04), 0.008, S, n=6)
        bx(b, (xc - 0.045, yy - 0.02, -0.07), (xc + 0.045, yy + 0.02, -0.035), S, ch=0.002, axis="x", pin=False)
    bx(b, (xc - 0.03, yb - 0.01, z0 - 0.01), (xc + 0.03, ya + 0.01, z0 + 0.03), S, ch=0.003, axis="y", pin=False)
    return done(ctx, b, "SM_Facade_FireEscape_Ladder", M, expect_size=(None, None, 3.0),
                notes="Fire-escape drop ladder 3.0 m, raised: same pivot as the lowest balcony, foot 2.2 m above the sidewalk. No collision.")


def m_bracket(ctx, M):
    """Wall bracket under a balcony: angle arm, diagonal brace, wall plate with three bolts. Pivot on the wall at
    the landing top, on the bracket's centre line."""
    b = B(77)
    S = "black"
    b.prism(steel.angle(0.05, 0.05, 0.006), (-0.025, 0.0, -0.116), X, Z, (0, -ESC_D + 0.02, 0), S, pstep=9.0)
    bar(b, (0, -ESC_D + 0.10, -0.116), (0, -0.012, -0.86), 0.025, 0.025, S, up=X, ch=0.003)
    bx(b, (-0.04, -0.012, -0.95), (0.04, 0.0, -0.05), S, ch=0.003, axis="z", pin=False)
    b.rivets([(0, -0.012, zz) for zz in (-0.09, -0.50, -0.91)], -Y, S, d=0.03, h=0.014, leak=0.0)
    bx(b, (-0.03, -ESC_D + 0.06, -0.125), (0.03, -ESC_D + 0.14, -0.116), S, ch=0.002, axis="y", pin=False)
    b.leaks += [(0, -0.006, -0.95), (0.02, -0.006, -0.95)]
    return done(ctx, b, "SM_Facade_FireEscape_Bracket", M, expect_size=(None, ESC_D, None),
                notes="Fire-escape wall bracket: three per balcony (x 0.10, 1.495, 2.89 from the balcony pivot). Rust runs from the plate.")


# -------------------------------------------------------------------------------------------------- window props

def m_ac(ctx, M):
    """Window air conditioner seen from the street: cabinet with a finned back and louvred sides, accordion
    panels to the jambs, the sash rail resting on it. Pivot: centre of the sill, on the wall plane."""
    b = B(81)
    w, h, S = 0.62, 0.40, "grey"
    bx(b, (-w / 2, -0.42, 0.0), (w / 2, 0.13, h), S, ch=0.008, axis="y", pin=False)
    bx(b, (-w / 2 - 0.004, -0.424, -0.004), (w / 2 + 0.004, -0.40, h + 0.004), S, ch=0.004, axis="x", pin=False)   # rear frame
    for i in range(15):                                                # condenser fins behind a guard
        zz = 0.03 + i * 0.023
        bx(b, (-w / 2 + 0.035, -0.432, zz), (w / 2 - 0.035, -0.424, zz + 0.011), "trim", pin=False, axis="x")
    for sx in (-1, 1):
        for i in range(8):                                             # side louvres
            zz = 0.07 + i * 0.034
            bx(b, (sx * w / 2, -0.37, zz), (sx * (w / 2 + 0.006), -0.15, zz + 0.016), S, pin=False, axis="y")
        xs = np.linspace(w / 2, 0.57, 15) * sx                         # accordion panel
        ys = 0.118 + 0.007 * (np.arange(15) % 2)
        zs = np.linspace(0.0, h, 4)[:, None]
        F = np.zeros((4, 15, 3))
        F[..., 0], F[..., 1], F[..., 2] = (xs if sx > 0 else xs[::-1])[None, :], (ys if sx > 0 else ys[::-1])[None, :], zs
        sheet(b, F, 0.004, "blind")
        bar(b, (sx * 0.2, -0.38, -0.012), (sx * 0.2, 0.0, -0.33), 0.025, 0.025, "trim", up=X, ch=0.003)     # brace to the wall
    bx(b, (-0.57, 0.10, h), (0.57, 0.15, h + 0.05), "white", ch=0.003, axis="x", pin=False)                # sash rail on top
    bx(b, (-w / 2, -0.40, -0.012), (w / 2, 0.02, 0.0), "trim", axis="y", pin=False)                        # support tray
    b.leaks += [(-0.2, -0.40, -0.012), (0.22, -0.40, -0.012)]
    return done(ctx, b, "SM_Facade_AirConditioner", M, expect_size=(1.14, None, None),
                notes="Window air conditioner for SM_Facade_BayWindow: pivot at the centre of the sill on the wall plane "
                      "(bay x 1.55, z 0.60). About one upper window in six. A rust streak decal belongs under it.")


def m_blind(ctx, M):
    b = B(83)
    bx(b, (-0.56, 0.215, WIN_H - 0.86), (0.56, 0.219, WIN_H - 0.05), "blind", axis="x")
    bx(b, (-0.565, 0.211, WIN_H - 0.885), (0.565, 0.223, WIN_H - 0.86), "blind", ch=0.003, axis="x")
    rod(b, (-0.565, 0.217, WIN_H - 0.07), (0.565, 0.217, WIN_H - 0.07), 0.018, "blind", n=10)
    return done(ctx, b, "SM_Facade_WindowBlind", M, expect_size=(1.13, None, None),
                notes="Half-drawn roller blind behind the sashes of SM_Facade_BayWindow: same pivot as the air conditioner. "
                      "About 45 % of the upper windows.")


# --------------------------------------------------------------------------------------------------------- build

def build(ctx):
    M = materials(ctx)
    ctx.M, ctx.K = M, {}
    ctx.kit = scene.collection("FacadeKit", ctx.col)
    for k in FACE:
        m_pier(ctx, M, k)
        m_bay(ctx, M, k, True)
        m_bay(ctx, M, k, False)
        m_corner(ctx, M, k)
        m_parapet(ctx, M, k)
        for w in ENDS[k]:
            m_fill(ctx, M, k, w)
            m_fill(ctx, M, k, w, parapet=True)
    m_bay(ctx, M, "Common", False)
    m_partycap(ctx, M)
    for name in SHOPS:
        m_shopfront(ctx, M, name)
        m_signband(ctx, M, name)
    ctx.log("ground floor: %d shop fronts" % len(SHOPS))
    for length in AWNINGS:
        m_awning(ctx, M, length)
    m_resentry(ctx, M)
    m_vestibule(ctx, M)
    m_cornice(ctx, M, BAY)
    for w in sorted({w for ws in ENDS.values() for w in ws}):
        m_cornice(ctx, M, w, "L")
        m_cornice(ctx, M, w, "R")
    m_roof(ctx, M)
    m_tank(ctx, M)
    for k in ("Red", "Buff"):
        m_bulkhead(ctx, M, k)
    m_balcony(ctx, M)
    m_stair(ctx, M)
    m_ladder(ctx, M)
    m_bracket(ctx, M)
    m_ac(ctx, M)
    m_blind(ctx, M)
    tris = {n: geo.stats(o)["triangles"] for n, o in ctx.K.items()}
    ctx.log("%d modules, %d triangles in all, largest %s (%d)" % (len(tris), sum(tris.values()), max(tris, key=tris.get), max(tris.values())))
    return [a["ob"] for a in ctx.assets.values()]


# ------------------------------------------------------------------------------------------------------ assembly

class Frame:
    """A wall line in the level: origin (x, y, z) of its left end, turned rot degrees about Z.
    at(s, d, z): s metres along the run, d metres behind the wall plane, z metres up."""

    def __init__(self, origin, rot):
        self.o, self.rot = np.asarray(origin, float), float(rot)
        r = math.radians(rot)
        self.c, self.s = math.cos(r), math.sin(r)

    def at(self, s=0.0, d=0.0, z=0.0):
        return (self.o[0] + self.c * s - self.s * d, self.o[1] + self.s * s + self.c * d, self.o[2] + z)


def put(ctx, name, fr, s, z=0.0, d=0.0, col=None, out=None, turn=0.0):
    """Place one instance of a module on a frame. Returns the object; `out` collects (name, location, rotation)."""
    ob = scene.duplicate(ctx.K[name], linked=True, col=col or ctx.sample)
    loc = fr.at(s, d, z)
    scene.place(ob, loc, fr.rot + turn)
    ob["mi_placed"] = True
    ob["mi_uv"] = (float(s), float(z), 0.0)
    if out is not None:
        out.append((name, tuple(round(float(v), 4) for v in loc), fr.rot + turn))
    return ob


def front_frame(key):
    bd = BUILDINGS[key]
    x0, x1 = bd["x"]
    return Frame((x1, -LINE, KERB_H), 180.0) if bd["face"] == "N" else Frame((x0, LINE, KERB_H), 0.0)


def assemble_front(ctx, key, out=None):
    """The street front of one building from the kit: shops, upper storeys, cornice, parapet, fire escape,
    air conditioners and blinds. Returns [(module, location, rotation about Z)] (Blender metres and degrees)."""
    bd = BUILDINGS[key]
    x0, x1 = bd["x"]
    w, k, north = x1 - x0, bd["brick"], bd["face"] == "N"
    fr = front_frame(key)
    out = [] if out is None else out
    loc = lambda xa, xb: (x1 - xb) if north else (xa - x0)            # left end of a span in the front's own run
    P = lambda *a, **kw: put(ctx, *a, out=out, **kw)
    for name, sh in SHOPS.items():
        if sh[0] != key:
            continue
        s = shop_local(name)
        s0 = loc(sh[1], sh[2])
        P("SM_Facade_Pier_" + k, fr, s0)
        P("SM_Facade_Pier_" + k, fr, s0 + s["W"] - PIER_W)
        P("SM_Facade_Shopfront_" + name, fr, s0 + PIER_W)
        P("SM_Facade_SignBand_" + name, fr, s0, z=BAND0)
        if s["awning"]:
            length = max(a for a in AWNINGS if a <= s["C"] + 1e-6)
            P("SM_Facade_Awning_" + cm(length), fr, s0 + PIER_W + (s["C"] - length) / 2, z=AWN_Z)
    for kind, xa, xb in bd["extra"]:
        P("SM_Facade_%s_%s" % ("ResEntry" if kind == "entry" else "Vestibule", k), fr, loc(xa, xb))
    n = int(w // BAY + 1e-6)
    p = (w - n * BAY) / 2
    ups = bd["storeys"] - 1
    rng = ctx.rng("dress", key)
    esc = None
    if bd["escape"]:
        xc, nb = bd["escape"]
        esc = ((x1 - xc) if north else (xc - x0)) - ESC_L / 2
    for i in range(ups):
        z = GROUND + i * STOREY
        P("SM_Facade_Fill_%s_%s" % (cm(p), k), fr, 0.0, z)
        P("SM_Facade_Fill_%s_%s" % (cm(p), k), fr, w - p, z)
        for j in range(n):
            P("SM_Facade_BayWindow_" + k, fr, p + j * BAY, z)
            xw = p + j * BAY + BAY / 2
            behind = esc is not None and i < bd["escape"][1] and esc - 0.3 < xw < esc + ESC_L + 0.3
            u = rng.random()
            if u < 0.16 and not behind:
                P("SM_Facade_AirConditioner", fr, xw, z + WIN_SILL)
            elif u < 0.60:
                P("SM_Facade_WindowBlind", fr, xw, z + WIN_SILL)
    zr = GROUND + ups * STOREY                                         # the roof line
    P("SM_Facade_CorniceEnd_L_" + cm(p), fr, 0.0, zr)
    P("SM_Facade_CorniceEnd_R_" + cm(p), fr, w - p, zr)
    P("SM_Facade_ParapetFill_%s_%s" % (cm(p), k), fr, 0.0, zr)
    P("SM_Facade_ParapetFill_%s_%s" % (cm(p), k), fr, w - p, zr)
    for j in range(n):
        P("SM_Facade_Cornice_310", fr, p + j * BAY, zr)
        P("SM_Facade_Parapet_310_" + k, fr, p + j * BAY, zr)
    if esc is not None:
        for i in range(bd["escape"][1]):
            z = GROUND + i * STOREY + 0.25
            P("SM_Facade_FireEscape_Balcony", fr, esc, z)
            for bxs in (0.10, ESC_L / 2, ESC_L - 0.10):
                P("SM_Facade_FireEscape_Bracket", fr, esc + bxs, z)
            if i == 0:
                P("SM_Facade_FireEscape_Ladder", fr, esc, z)
            if i < bd["escape"][1] - 1:
                P("SM_Facade_FireEscape_Stair", fr, esc, z)
    return out


def assemble_shell(ctx, key, sides=("L", "R"), tank=None, bulkhead=None, out=None):
    """What stands behind a front in the sample: side walls in common brick behind a corner return, party-wall
    caps, roof panels, and the roof items. sides: which ends show (left / right as seen from the street)."""
    bd = BUILDINGS[key]
    x0, x1 = bd["x"]
    w, k, north, depth = x1 - x0, bd["brick"], bd["face"] == "N", bd["depth"]
    out = [] if out is None else out
    P = lambda *a, **kw: put(ctx, *a, out=out, **kw)
    fr = front_frame(key)
    zr = GROUND + (bd["storeys"] - 1) * STOREY
    nb = int((depth - T - 0.6) // BAY)
    for side in sides:
        # right end: the side wall runs back from the front; left end: it runs forward to the front
        if side == "R":
            sf = Frame(fr.at(w, T, 0.0), fr.rot + 90.0)
            order = [("SM_Facade_CornerReturn_" + k, 0.0, 0.6)] + [("SM_Facade_BayBlank_Common", 0.6 + i * BAY, BAY) for i in range(nb)]
            caps = [("SM_Facade_ParapetFill_060_" + k if 0.60 in ENDS[k] else "SM_Facade_PartyWallCap_310", 0.0)] + \
                   [("SM_Facade_PartyWallCap_310", 0.6 + i * BAY) for i in range(nb)]
        else:
            total = 0.6 + nb * BAY
            sf = Frame(fr.at(0.0, T + total, 0.0), fr.rot - 90.0)
            order = [("SM_Facade_BayBlank_Common", i * BAY, BAY) for i in range(nb)] + [("SM_Facade_CornerReturn_" + k, nb * BAY, 0.6)]
            caps = [("SM_Facade_PartyWallCap_310", i * BAY) for i in range(nb)] + \
                   [("SM_Facade_ParapetFill_060_" + k if 0.60 in ENDS[k] else "SM_Facade_PartyWallCap_310", nb * BAY)]
        z = zr - STOREY
        while z > -STOREY:                                             # from the roof down; the last row is sunk
            for name, s, _w in order:
                P(name, sf, s, z)
            z -= STOREY
        for name, s in caps:
            P(name, sf, s, zr)
    nx, ny = int(math.ceil((w - 2 * T) / 4.0)), int(math.ceil((depth - T) / 4.0))
    for i in range(nx):
        for j in range(ny):
            sx = min(T + i * 4.0, w - T - 4.0)
            sy = min(T + j * 4.0, depth - 4.0)
            lap = -0.004 * ((sx != T + i * 4.0) + (sy != T + j * 4.0))
            # the panel's own +Y runs to the back of the building
            P("SM_Facade_RoofPanel_4m", fr, sx, zr + lap, d=sy)
    wx = lambda x: (x1 - x) if north else (x - x0)
    wy = lambda y: (-LINE - y) if north else (y - LINE)
    if tank:
        P("SM_Facade_WaterTank", fr, wx(tank[0]), zr, d=wy(tank[1]))
    if bulkhead:
        P("SM_Facade_StairBulkhead_" + ("Buff" if k == "Buff" else "Red"), fr, wx(bulkhead[0]), zr, d=wy(bulkhead[1]))
    return out


# ------------------------------------------------------------------------------------------------------- previews

def on_preview(ctx, objs):
    """The south block face (S1, S2, S3: seven shop fronts) behind the street and the El, in level coordinates."""
    from assets import el, street
    a = ctx.args
    Pv = paths.previews
    only = set(a.only or [])
    want = lambda nm: not only or nm in only
    T0 = type(ctx)
    st = T0("street", a)
    street.build(st)
    dress = scene.collection("Dressing", st.col)
    for kx in (-4, -3, -2, -1, 1, 2, 3):                               # the 20 m section repeated along the avenue
        for ob in st.placed:
            if ob.data is st.A["hydrant"].data:
                continue
            dd = scene.duplicate(ob, linked=True, col=dress)
            dd.location.x += kx * street.L
    render.backdrop(600.0, (0.075, 0.073, 0.07), z=-0.06)
    ec = T0("el", a)
    el.build(ec)
    x_off = -40.0                                                      # three bays in front of S1 and S2
    for ob in ec.placed:
        ob.location.x += x_off
    el.layout(ec, ec.A, range(-3, 1), x_off, skip=(0,))
    el.layout(ec, ec.A, range(3, 11), x_off, skip=(3,))
    mat.principled(ec.M["glow"]).inputs["Emission Strength"].default_value = 0.0
    materials(ctx)                                                     # ours again: shared slots keep our settings
    ctx.kit.hide_render = True
    ctx.sample = scene.collection("FacadeSample", ctx.col)
    placed = []
    for key in ("s1", "s2", "s3"):
        assemble_front(ctx, key, placed)
    assemble_shell(ctx, "s1", sides=(), out=placed)
    assemble_shell(ctx, "s2", sides=("L",), tank=(-23.0, -24.0), bulkhead=(-19.5, -28.75), out=placed)
    assemble_shell(ctx, "s3", sides=("L", "R"), bulkhead=(13.0, -20.75), out=placed)
    ctx.log("sample: %d instances of %d modules" % (len(placed), len({p[0] for p in placed})))
    render.setup(samples=a.samples)
    eye = KERB_H + 1.65
    if want("facade_wire"):
        vl = bpy.context.view_layer
        vl.material_override = mat.flat("Clay", (0.55, 0.55, 0.55), 0.55)
        ec.col.hide_render = True
        render.rig_day(sun_azimuth=330.0, stops=-0.6)
        render.cam_look((-9.0, 4.5, 9.5), (-27.5, -11.0, 5.6), lens=24, name="Cam_Wire")
        _p, sec = render.render_jpeg(os.path.join(Pv, "facade_wire.jpg"), max(24, a.samples // 2))
        vl.material_override = None
        ec.col.hide_render = False
        ctx.log("preview facade_wire.jpg %.0fs" % sec)
    sun = render.DESIGN_SUN_BEARING
    if want("facade_day_hero"):
        render.rig_day(sun_azimuth=sun, stops=1.8)
        render.cam_look((-20.5, 8.6, eye), (-33.0, -11.0, 2.9), lens=24, name="Cam_Hero")
        _p, sec = render.render_jpeg(os.path.join(Pv, "facade_day_hero.jpg"), a.samples)
        ctx.log("preview facade_day_hero.jpg %.0fs" % sec)
    if want("facade_day_street"):
        render.rig_day(sun_azimuth=sun, stops=0.9)
        render.cam_look((-47.5, -6.3, eye), (-10.0, -10.2, 6.2), lens=20, name="Cam_Street")
        _p, sec = render.render_jpeg(os.path.join(Pv, "facade_day_street.jpg"), a.samples)
        ctx.log("preview facade_day_street.jpg %.0fs" % sec)
    if want("facade_storefront"):
        render.rig_day(sun_azimuth=sun, stops=2.4)
        render.cam_look((-36.6, -7.25, eye), (-33.6, -11.0, 1.75), lens=24, name="Cam_Storefront")
        _p, sec = render.render_jpeg(os.path.join(Pv, "facade_storefront.jpg"), a.samples)
        ctx.log("preview facade_storefront.jpg %.0fs" % sec)
