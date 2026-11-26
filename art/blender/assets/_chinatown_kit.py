"""Canal Street kit, part 1: materials, helpers and the props (market, vendors, lanterns, street, roof).

Built with the Block's facade helpers (assets/facade.py: B, bx, rod, bar, sheet, weather), imported, never changed, so
the Block's own outputs stay byte for byte. Props: pivot at the centre of the footprint on the ground, forward +X.
Surfaces are the catalogued tiling scans (tinted where the slot name says so, SLOT_META) and a few flat slots for small
things (produce, ice, fish, bulbs); no unique bakes, so a prop costs no texture memory of its own.
"""
import math
import os

import numpy as np

from assets import _chinatown_matlas as matlas
from assets import facade as fc
from assets import signs as sg
from assets.facade import B, sheet
from mi import geo, mat, paths, scene

X, Y, Z = np.eye(3)
SOOT = (0.030, 0.028, 0.026)
SLOT_META = {}


def _tile_of(set_name):
    try:
        return mat.scan_tile(set_name)
    except Exception:
        return (2.0, 2.0)


def S(ctx, set_name, slot=None, tint=None, note=None, **kw):
    """Material on a tiling set: a catalogued scan, or a baked set on disk (set.json)."""
    slot = slot or "MI_" + set_name[3:]
    try:
        m = ctx.scan_set(set_name, slot=slot, tint=tint, **kw)
    except KeyError:
        d = paths.texture_set(set_name)
        kw.pop("blend", None)
        m = mat.from_texture_set(d, name=slot, tile_m=_tile_of(set_name), tint=tint, **kw)
        m["mi_tile_m"] = _tile_of(set_name)
        if set_name not in ctx.sets:
            ctx.sets.append(set_name)
    if slot != "MI_" + set_name[3:] or tint is not None:
        SLOT_META[slot] = {"set": set_name, "workflow": "tiling"}
        if tint is not None:
            SLOT_META[slot]["tint"] = [round(float(c), 3) for c in tint]
        if note:
            SLOT_META[slot]["note"] = note
    return m


def F(name, col, rough=0.6, metal=0.0, emit=None, strength=0.0, note=None):
    """A flat slot (constant parameters in the Unreal master material, no texture)."""
    m = mat.flat(name, col, rough, metal)
    if emit is not None:
        p = mat.principled(m)
        p.inputs["Emission Color"].default_value = (*emit, 1.0)
        p.inputs["Emission Strength"].default_value = strength
    SLOT_META[name] = {"workflow": "flat" if emit is None else "emissive", "color": [round(float(c), 3) for c in col],
                       "roughness": rough, "metallic": metal}
    if emit is not None:
        SLOT_META[name]["emissive"] = [round(float(c), 3) for c in emit]
    if note:
        SLOT_META[name]["note"] = note
    return m


def materials(ctx):
    rust = dict(blend="TS_Steel_ScanRust", leak_color=(0.24, 0.10, 0.035), leak_rough=0.1, dirt_color=SOOT, alpha="splash")
    M = {}
    M["trim"] = S(ctx, "TS_Steel_ScanPaintGrey", "MI_Steel_PaintDark", tint=(0.16, 0.16, 0.17), blend_start=0.55, macro=0.10, **rust)
    M["black"] = S(ctx, "TS_Steel_ScanPaintGrey", "MI_Steel_PaintBlack", tint=(0.07, 0.07, 0.075), blend_start=0.45, **rust)
    M["grey"] = S(ctx, "TS_Steel_ScanPaintGrey", blend_start=0.40, macro=0.12, **rust)
    M["jade"] = S(ctx, "TS_Steel_ScanPaintGreen", blend_start=0.45, **rust)
    M["redlac"] = S(ctx, "TS_Steel_ScanPaintWhite", "MI_Paint_RedLacquer", tint=(0.42, 0.035, 0.03), alpha="splash", dirt_color=SOOT,
                    note="red lacquer (banquet doors, lantern caps' rods): the white paint scan multiplied by the tint")
    M["stainless"] = S(ctx, "TS_Steel_Stainless", alpha="splash", dirt_color=(0.08, 0.07, 0.06))
    M["galv"] = S(ctx, "TS_Galvanised_Aged", alpha="splash", dirt_color=SOOT)
    M["tile"] = S(ctx, "TS_Tile_ScanWhite", alpha="splash", dirt_color=(0.07, 0.06, 0.05), macro=0.06)
    M["stone"] = S(ctx, "TS_Concrete_ScanWeathered", alpha="splash", dirt_color=SOOT, macro=0.12)
    M["conc"] = S(ctx, "TS_Sidewalk_ScanWorn", alpha="splash", dirt_color=(0.06, 0.055, 0.048), macro=0.12)
    M["wood"] = S(ctx, "TS_Wood_ScanPlankPainted", alpha="splash", dirt_color=SOOT, macro=0.1)
    M["timber"] = S(ctx, "TS_Wood_ScanPlankDark", alpha="splash", dirt_color=SOOT, macro=0.15)
    M["pallet"] = S(ctx, "TS_Wood_ScanPallet", alpha="splash", dirt_color=SOOT)
    M["ply"] = S(ctx, "TS_Plywood_ScanLauan", alpha="splash", dirt_color=SOOT)
    canvas = dict(alpha="splash", dirt_color=(0.07, 0.06, 0.05), wear_tint=(1.5, 1.6, 1.6), macro=0.2)
    M["fabricRed"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_CanvasRed", tint=(0.55, 0.07, 0.05), **canvas)
    M["fabricGreen"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_CanvasGreen", tint=(0.07, 0.30, 0.17), **canvas)
    M["fabricYellow"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_CanvasYellow", tint=(0.85, 0.58, 0.08), **canvas)
    M["fabricBlue"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_TarpBlue", tint=(0.07, 0.20, 0.55), **canvas,
                        note="market tarp blue (the design's TS_Tarp_Blue, as a tint of the canvas scan: no new set)")
    M["fabricWhite"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_CanvasWhite", tint=(0.86, 0.85, 0.80), **canvas)
    M["fabricPink"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_CanvasPink", tint=(0.85, 0.30, 0.45), **canvas)
    M["burlap"] = S(ctx, "TS_Fabric_ScanBurlap", alpha="splash", dirt_color=SOOT)
    M["card"] = S(ctx, "TS_Cardboard_Kraft", alpha="splash", dirt_color=SOOT)
    M["styro"] = S(ctx, "TS_Plastic_White", alpha="splash", dirt_color=(0.12, 0.11, 0.09))
    M["plastic"] = S(ctx, "TS_Plastic_Black", alpha="splash", dirt_color=SOOT)
    M["plasticOrange"] = S(ctx, "TS_Plastic_Orange", alpha="splash", dirt_color=SOOT)
    M["plasticBlue"] = S(ctx, "TS_Plastic_White", "MI_Plastic_Blue", tint=(0.10, 0.28, 0.62), alpha="splash", dirt_color=SOOT)
    M["plasticGreen"] = S(ctx, "TS_Plastic_White", "MI_Plastic_Green", tint=(0.12, 0.45, 0.22), alpha="splash", dirt_color=SOOT)
    M["rubber"] = S(ctx, "TS_Rubber_Aged", alpha="splash")
    M["roof"] = S(ctx, "TS_Roof_ScanBitumen", alpha="splash", dirt_color=(0.10, 0.09, 0.08), macro=0.2)
    M["chain"] = S(ctx, "TS_ChainLink_Galv", alpha="splash", note="masked chain-link: opacity from the set's BC alpha")
    M["alu"] = F("MI_Metal_Aluminium", (0.60, 0.60, 0.61), 0.38, 1.0)
    M["chrome"] = F("MI_Metal_Chrome", (0.77, 0.77, 0.77), 0.10, 1.0)
    M["gold"] = F("MI_Metal_Gold", (0.80, 0.58, 0.22), 0.35, 1.0)
    M["glass"] = mat.make("MI_Glass_Store", "glass", Film=0.08)
    M["glasswin"] = mat.make("MI_Glass_Window", "glass", Film=0.18)
    SLOT_META["MI_Glass_Store"] = {"workflow": "glass", "note": "M_MI_Glass, opaque in this level (chinatown.md 14: no translucency)"}
    SLOT_META["MI_Glass_Window"] = {"workflow": "glass", "note": "M_MI_Glass, opaque with a parallax room"}
    M["interior"] = F("MI_Interior_Dark", (0.022, 0.021, 0.02), 0.9, note="shallow dark room behind the glass (the TC_* cube maps in Unreal)")
    M["interiorLit"] = F("MI_Interior_Lit", (0.10, 0.095, 0.085), 0.8, emit=(1.0, 0.86, 0.66), strength=0.6,
                         note="a lit shop interior seen through glass at night (warm); 8 to 15 nits")
    M["face"] = F("M_Sign_CT_Face", (0.35, 0.35, 0.35), 0.4,
                  note="sign face on 0..1 UVs: the MI of a placed sign reads Sign_CT_Atlas<N> (BC, ORM, E) and maps 0..1 to "
                       "its cell (art/out/chinatown/signs_chinatown.json)")
    SLOT_META["M_Sign_CT_Face"] = {"workflow": "sign_atlas", "sets": ["Sign_CT_Atlas1"], "uv": "0..1 over the face",
                                   "note": SLOT_META["M_Sign_CT_Face"]["note"]}
    M["paper"] = F("MI_Paper_LanternRed", (0.55, 0.06, 0.035), 0.75, emit=(1.0, 0.16, 0.06), strength=0.0,
                   note="lantern paper: two-sided, a lamp inside at night (40 to 80 nits); 0 by day")
    M["bulb"] = F("MI_Lamp_Bulb", (0.9, 0.88, 0.8), 0.2, emit=(1.0, 0.82, 0.58), strength=0.0, note="bare bulb, lit at night")
    M["ice"] = F("MI_Ice_Crushed", (0.80, 0.86, 0.90), 0.12, note="crushed ice: wet, bright speculars")
    M["fish"] = F("MI_Fish_Silver", (0.50, 0.53, 0.55), 0.28, 0.35, note="whole fish on ice")
    M["orange"] = F("MI_Produce_Orange", (0.78, 0.30, 0.03), 0.45)
    M["yellow"] = F("MI_Produce_Yellow", (0.78, 0.62, 0.10), 0.45)
    M["apple"] = F("MI_Produce_Red", (0.42, 0.05, 0.04), 0.35)
    M["leaf"] = F("MI_Produce_Leaf", (0.16, 0.36, 0.08), 0.55)
    M["stem"] = F("MI_Produce_Stem", (0.72, 0.78, 0.60), 0.5)
    M["grain"] = F("MI_Produce_Dried", (0.52, 0.36, 0.20), 0.85, note="dried goods in bins: mushrooms, beans, dates")
    M["water"] = F("MI_Water_Tank", (0.10, 0.18, 0.16), 0.05)
    M["cloth"] = F("MI_Fabric_Goods", (0.18, 0.19, 0.22), 0.8, note="vendor goods: T-shirts, caps, bags (no logos, no patterns)")
    M["clothLight"] = F("MI_Fabric_GoodsLight", (0.70, 0.68, 0.64), 0.8)
    M["standoff"] = F("MI_Glass_Standoff", (0.80, 0.82, 0.80), 0.08)
    for h_, n_ in sg.NEON.items():
        M["neon" + n_] = sg.neon_mat(n_, h_)
        SLOT_META["MI_Neon_" + n_] = {"workflow": "emissive", "emissive": h_,
                                      "note": "glass tube, 400 .. 2,000 nits at night, x 0.55 by day (ART_BIBLE 5.2)"}
    M["_atlas"] = matlas.material(ctx)
    SLOT_META[matlas.SLOT] = {"workflow": "atlas", "set": matlas.SET, "uv": "each face inside one 256 px cell of the 2K page",
                              "note": "the market and vendor goods atlas (assets/_chinatown_matlas.py): produce, crate plastics, "
                                      "card, pallet, ice, fish, the vendor fabrics and plastics"}
    M["neonWhite"] = sg.neon_mat("White", "#f4f8ff")
    SLOT_META["MI_Neon_White"] = {"workflow": "emissive", "emissive": "#f4f8ff", "note": "white neon, about 1,200 nits"}
    return M


# ================================================================================================= helpers

# The flicker floor (chinatown.md 13.4: railings 40 mm or more; READY.md R3 at render scale 0.50): any member longer than
# MIN_LEN is drawn at least MIN_W across (with the polygon's flat-to-flat allowance). The kit's rods, boxes and bars go
# through these wrappers, so a detail can never be modelled thinner; _chinatown_check.py tests the result.
MIN_LEN, MIN_W = 0.6, 0.036


def rod(b, p0, p1, r, slot, n=8, **kw):
    if float(np.linalg.norm(np.asarray(p1, float) - np.asarray(p0, float))) > MIN_LEN - 0.02:
        r = max(r, (MIN_W / 2) / math.cos(math.pi / max(n, 3)) * 1.02)
    return _FC_ROD(b, p0, p1, r, slot, n=n, **kw)


def bx(b, lo, hi, slot, ch=0.0, pin=True, axis=None, **kw):
    lo, hi = np.minimum(lo, hi).astype(float), np.maximum(lo, hi).astype(float)
    d = hi - lo
    if d.max() > MIN_LEN - 0.02:
        order = np.argsort(d)
        if d[order[1]] < MIN_W:                       # long and thin in two directions: a member, not a panel
            for k in order[:2]:
                if d[k] < MIN_W:
                    c = (lo[k] + hi[k]) / 2
                    lo[k], hi[k] = c - MIN_W / 2, c + MIN_W / 2
    return _FC_BX(b, lo, hi, slot, ch=ch, pin=pin, axis=axis, **kw)

_FC_ROD, _FC_BX = fc.rod, fc.bx


def rod_floor(b, p0, p1, r, slot, n=8, **kw):
    """rod() for code that calls facade.rod by name (see _chinatown_front.thick_members): the floor, then the original."""
    if float(np.linalg.norm(np.asarray(p1, float) - np.asarray(p0, float))) > MIN_LEN - 0.02:
        r = max(r, (MIN_W / 2) / math.cos(math.pi / max(n, 3)) * 1.02)
    return _FC_ROD(b, p0, p1, r, slot, n=n, **kw)


def bx_floor(b, lo, hi, slot, ch=0.0, pin=True, axis=None, **kw):
    lo, hi = np.minimum(lo, hi).astype(float), np.maximum(lo, hi).astype(float)
    d = hi - lo
    if d.max() > MIN_LEN - 0.02:
        order = np.argsort(d)
        if d[order[1]] < MIN_W:
            for k in order[:2]:
                if d[k] < MIN_W:
                    c = (lo[k] + hi[k]) / 2
                    lo[k], hi[k] = c - MIN_W / 2, c + MIN_W / 2
    return _FC_BX(b, lo, hi, slot, ch=ch, pin=pin, axis=axis, **kw)


def bar(b, p0, p1, w, t, slot, up=Z, **kw):
    """facade.bar, with the `up` vector swapped when the bar runs along it (a vertical bar would be degenerate)."""
    d = np.asarray(p1, float) - np.asarray(p0, float)
    if float(np.linalg.norm(d)) > MIN_LEN and max(w, t) < MIN_W:
        w = max(w, MIN_W)
    if abs(float(np.dot(d / np.linalg.norm(d), up))) > 0.98:
        up = Y if abs(d[1]) < abs(d[0]) or abs(d[2]) > 0 else X
    return fc.bar(b, p0, p1, w, t, slot, up=up, **kw)


def absorb(b, ob, slot, loc=(0, 0, 0), rot=0.0, scale=(1, 1, 1)):
    geo.transform(ob, loc=loc, rot=(0, 0, rot), scale=scale)
    return b.absorb(ob, slot)


def ball(b, r, c, slot, seg=10, rings=7, squash=(1.0, 1.0, 1.0)):
    return absorb(b, geo.sphere(r, seg, rings), slot, loc=c, scale=squash)


def lathe(b, prof, slot, loc=(0, 0, 0), seg=12):
    return absorb(b, geo.revolve(prof, seg), slot, loc=loc)


def frame_box(b, x0, x1, y0, y1, z0, z1, t, slot):
    """Square-tube frame: four legs and two rings of rails."""
    for xx in (x0, x1 - t):
        for yy in (y0, y1 - t):
            bx(b, (xx, yy, z0), (xx + t, yy + t, z1), slot, ch=0.002, pin=False)
    for zz in (z0 + 0.10, z1 - t):
        bx(b, (x0 + t, y0, zz), (x1 - t, y0 + t, zz + t), slot, ch=0.002, pin=False)
        bx(b, (x0 + t, y1 - t, zz), (x1 - t, y1, zz + t), slot, ch=0.002, pin=False)
        bx(b, (x0, y0 + t, zz), (x0 + t, y1 - t, zz + t), slot, ch=0.002, pin=False)
        bx(b, (x1 - t, y0 + t, zz), (x1, y1 - t, zz + t), slot, ch=0.002, pin=False)


def crate(b, x0, y0, z0, L, W, H, slot, t=0.008):
    """Open plastic produce crate: floor, slotted walls (two rails per side), corner posts."""
    bx(b, (x0, y0, z0), (x0 + L, y0 + W, z0 + 0.012), slot, pin=False)
    for zz in (z0 + 0.012, z0 + H - 0.04):
        bx(b, (x0, y0, zz), (x0 + L, y0 + t, zz + 0.04), slot, pin=False)
        bx(b, (x0, y0 + W - t, zz), (x0 + L, y0 + W, zz + 0.04), slot, pin=False)
        bx(b, (x0, y0 + t, zz), (x0 + t, y0 + W - t, zz + 0.04), slot, pin=False)
        bx(b, (x0 + L - t, y0 + t, zz), (x0 + L, y0 + W - t, zz + 0.04), slot, pin=False)
    for xx in (x0, x0 + L - 0.03):
        for yy in (y0, y0 + W - 0.03):
            bx(b, (xx, yy, z0), (xx + 0.03, yy + 0.03, z0 + H), slot, pin=False)


def fill_fruit(b, rng, x0, y0, z0, L, W, r, slot, layers=1, jit=0.15, seg=5):
    """slot: one material, or a tuple to choose from per fruit (a crate of one colour reads as a flat slab)."""
    n = 0
    for k in range(layers):
        nx, ny = int(L / (2 * r)), int(W / (2 * r))
        off = (k % 2) * r * 0.5
        for i in range(nx):
            for j in range(ny):
                if k and rng.random() < 0.35:
                    continue
                rr = r * rng.uniform(0.88, 1.08)
                c = (x0 + r + off + i * 2 * r + rng.uniform(-jit, jit) * r, y0 + r + off * 0.6 + j * 2 * r + rng.uniform(-jit, jit) * r,
                     z0 + rr + k * r * 1.55)
                if c[0] + rr > x0 + L + 0.01 or c[1] + rr > y0 + W + 0.01:
                    continue
                sl = slot if isinstance(slot, str) else slot[int(rng.integers(0, len(slot)))]
                ball(b, rr, c, sl, seg=seg, rings=4, squash=(1.0, 1.0, rng.uniform(0.88, 0.98)))
                n += 1
    return n


def greens(b, rng, x0, y0, z0, L, W, slot_leaf="leaf", slot_stem="stem", n=10):
    """Bundles of leafy greens lying in a crate: a pale stem cone and a leafy flattened lobe each."""
    for i in range(n):
        cx, cy = x0 + rng.uniform(0.12, L - 0.12), y0 + rng.uniform(0.05, W - 0.05)
        a = rng.uniform(0, 2 * math.pi)
        ln = rng.uniform(0.20, 0.28)
        st = geo.cylinder(0.025, ln * 0.45, 6, name="st", axis="X")
        geo.transform(st, loc=(cx, cy, z0 + 0.03), rot=(0, 0, math.degrees(a)))
        b.absorb(st, slot_stem)
        lf = geo.sphere(0.06, 8, 5)
        geo.transform(lf, loc=(cx + math.cos(a) * ln * 0.45, cy + math.sin(a) * ln * 0.45, z0 + 0.045), rot=(0, 0, math.degrees(a)),
                      scale=(1.8, 1.0, 0.55))
        b.absorb(lf, slot_leaf)


def done(ctx, b, name, M, ground=True, ledges=(), collision="box", **asset):
    ob = b.finish(name, M, ctx.kit)
    if name.startswith("SM_Prop_CT_"):
        # the small surfaces of the market and vendor props go onto the one 2K atlas (chinatown.md 13.5): one slot
        # for a produce display, two or three for the rest, instead of up to seven flat slots
        matlas.remap(ob, M, M["_atlas"])
    fc.weather(ctx, b, ob, name, ledges=list(ledges), ground=ground)
    ctx.asset(ob, collision=collision, slots=SLOT_META, **asset)
    ctx.K[name] = ob
    return ob


# ================================================================================================= the market

def m_stall_counter(ctx, M):
    """Double-sided stall counter 2.0 x 1.8 x 0.95: plywood carcass on a steel kick, stainless top with a lip,
    a raised back shelf down the middle (goods on both faces)."""
    b = B(201)
    L, W, H = 2.0, 1.8, 0.95
    bx(b, (-L / 2, -W / 2 + 0.04, 0), (L / 2, W / 2 - 0.04, 0.12), "black", ch=0.004)                   # kick
    bx(b, (-L / 2, -W / 2, 0.12), (L / 2, W / 2, H - 0.04), "ply", ch=0.004)                              # carcass
    for s in (-1, 1):
        for xx in np.linspace(-L / 2 + 0.02, L / 2 - 0.06, 4):                                            # panel battens
            bx(b, (xx, s * W / 2 + (0.0 if s > 0 else -0.018), 0.14), (xx + 0.04, s * W / 2 + (0.018 if s > 0 else 0.0), H - 0.06), "ply", pin=False)
    bx(b, (-L / 2 - 0.02, -W / 2 - 0.02, H - 0.04), (L / 2 + 0.02, W / 2 + 0.02, H), "stainless", ch=0.004)   # top
    for s in (-1, 1):
        bx(b, (-L / 2 - 0.02, s * (W / 2 + 0.02) - 0.008, H), (L / 2 + 0.02, s * (W / 2 + 0.02) + 0.008, H + 0.035), "stainless", pin=False)
    bx(b, (-L / 2 + 0.05, -0.10, H), (L / 2 - 0.05, 0.10, H + 0.28), "ply", ch=0.004)                    # centre riser
    bx(b, (-L / 2 + 0.03, -0.16, H + 0.28), (L / 2 - 0.03, 0.16, H + 0.30), "stainless", ch=0.003)
    return done(ctx, b, "SM_Prop_CT_StallCounter_2m", M, expect_size=(L + 0.04, W + 0.056, H + 0.30), cover_height=H,
                notes="Market stall counter module 2.0 m (rows R1..R4 are runs of these, chinatown.md 4.3): plywood carcass, steel "
                      "kick, stainless top with lips, a raised middle shelf. Chest-high cover; the level's collider is the run's box.")


def m_fish_counter(ctx, M):
    """Fish counter 2.0 x 1.0 x 0.9: stainless tub on legs, an ice bed sloping to the customer, fish in rows."""
    b = B(202)
    rng = ctx.rng("fish")
    L, W, H = 2.0, 1.0, 0.90
    frame_box(b, -L / 2, L / 2, -W / 2, W / 2, 0.0, 0.72, 0.04, "stainless")
    bx(b, (-L / 2, -W / 2, 0.72), (L / 2, W / 2, 0.76), "stainless", ch=0.003)
    for s in (-1, 1):                                                                                      # tub walls
        bx(b, (-L / 2, s * W / 2 - (0.02 if s > 0 else 0), 0.76), (L / 2, s * W / 2 + (0 if s > 0 else 0.02), 0.84 if s < 0 else H + 0.10), "stainless", pin=False)
        bx(b, (s * L / 2 - (0.02 if s > 0 else 0), -W / 2 + 0.02, 0.76), (s * L / 2 + (0 if s > 0 else 0.02), W / 2 - 0.02, H + 0.10), "stainless", pin=False)
    xs = np.linspace(-L / 2 + 0.02, L / 2 - 0.02, 25)
    ys = np.linspace(-W / 2 + 0.02, W / 2 - 0.02, 13)
    n = sg.vnoise(rng, len(ys), len(xs), 3, 2)
    Fv = np.zeros((len(ys), len(xs), 3))
    Fv[..., 0], Fv[..., 1] = xs[None, :], ys[:, None]
    Fv[..., 2] = 0.80 + 0.12 * (ys[:, None] + W / 2) / W + 0.025 * n
    sheet(b, Fv, 0.04, "ice", vdir=Y, fdir=X)
    for row in range(3):
        y = -W / 2 + 0.18 + row * 0.28
        for i in range(7):
            x = -L / 2 + 0.16 + i * 0.26 + rng.uniform(-0.03, 0.03)
            z = 0.80 + 0.12 * (y + W / 2) / W + 0.04
            ln = rng.uniform(0.30, 0.40)
            body = geo.sphere(1.0, 8, 5)
            geo.transform(body, loc=(x, y, z), rot=(0, 0, 90 + rng.uniform(-12, 12)), scale=(ln / 2, 0.055, 0.035))
            b.absorb(body, "fish")
            tail = geo.cylinder(0.04, 0.01, 4, name="tail", axis="Y")
            geo.transform(tail, loc=(x, y - ln / 2 - 0.02, z), scale=(1.0, 1.0, 0.6))
            b.absorb(tail, "fish")
    return done(ctx, b, "SM_Prop_CT_FishCounter", M, expect_size=(L, W, None), cover_height=H,
                notes="Fish counter on the market's east wall (x -1.4..-0.4, chinatown.md 4.3): stainless tub on legs, crushed ice "
                      "sloping to the customer, three rows of whole fish. Flat slots MI_Ice_Crushed, MI_Fish_Silver.")


def m_produce(ctx, M, kind):
    """Sloped produce display: four plastic crates on a timber stand, filled with fruit or greens."""
    b = B(203 + len(kind), step=0.6)
    rng = ctx.rng("produce", kind)
    L, W = 1.4, 1.0
    bx(b, (-L / 2, -W / 2, 0), (L / 2, W / 2, 0.06), "pallet", pin=False)
    for xx in (-L / 2, L / 2 - 0.06):
        bx(b, (xx, -W / 2, 0.06), (xx + 0.06, W / 2, 0.50), "timber", pin=False)
    plat = B(204, step=0.6)
    for j, yy in enumerate((-W / 2, 0.0)):                                                     # two rows, the front one lower
        for i, xx in enumerate((-L / 2 + 0.06, 0.02)):
            z0 = 0.50 + j * 0.16
            slot = ("plasticBlue", "plasticGreen")[(i + j) % 2]
            crate(plat, xx, yy, z0, 0.62, 0.48, 0.20, slot)
            # the crate reads full from one visible layer on a false bottom (the layers under it are never seen)
            if kind == "Greens" and (i + j) % 2 == 0:
                bx(plat, (xx + 0.02, yy + 0.02, z0 + 0.012), (xx + 0.60, yy + 0.46, z0 + 0.10), "leaf", pin=False)
                greens(plat, rng, xx + 0.02, yy + 0.02, z0 + 0.10, 0.58, 0.44, n=8)
            else:
                fr = {"Citrus": ("orange", "orange", "yellow"), "Greens": ("apple",), "Mixed": ("orange", "apple", "yellow", "orange")[i + 2 * j]}[kind]
                fr = fr if isinstance(fr, tuple) and len(fr) > 1 else (fr if isinstance(fr, str) else fr[0])
                # the false bottom is a dark liner (crate paper), never the fruit colour: one flat orange layer read as a slab
                bx(plat, (xx + 0.02, yy + 0.02, z0 + 0.012), (xx + 0.60, yy + 0.46, z0 + 0.09), "black", pin=False)
                fill_fruit(plat, rng, xx + 0.02, yy + 0.02, z0 + 0.09, 0.58, 0.44, 0.045 if fr != "yellow" else 0.042, fr, layers=1, seg=6)
    bx(b, (-L / 2, -W / 2 - 0.02, 0.06), (L / 2, -W / 2 + 0.02, 0.50), "timber", pin=False)
    fc.sub(b, plat, 0.0, (0, 0, 0))
    return done(ctx, b, "SM_Prop_CT_Produce_" + kind, M, expect_size=(L, None, None), cover_height=0.7,
                notes="Produce display %s: four plastic crates on a timber stand, the front row lower; fruit as low spheres "
                      "on a false bottom, one slot: the market and vendor goods atlas M_CT_MarketGoods. Market aisles, the fruit "
                      "stand on Mott, the grocery's sidewalk." % kind)


def m_dry_goods(ctx, M):
    """Dry goods: three open burlap sacks with rolled tops and a rack of three plastic bins."""
    b = B(207)
    rng = ctx.rng("dry")
    for i, x in enumerate((-0.55, -0.12, 0.31)):
        r, h = rng.uniform(0.19, 0.22), rng.uniform(0.48, 0.58)
        prof = [(0.0, 0.0), (r * 0.92, 0.0), (r, 0.06), (r * 1.04, h * 0.5), (r * 0.98, h - 0.05), (r * 1.12, h - 0.02),
                (r * 1.10, h + 0.05), (r * 0.96, h + 0.05), (r * 0.94, h - 0.06), (0.0, h - 0.06)]
        lathe(b, prof, "burlap", loc=(x, 0.0, 0.0), seg=14)
        for k in range(14):                                                                     # the contents heaped
            a, rr = rng.uniform(0, 2 * math.pi), rng.uniform(0, r * 0.7)
            ball(b, rng.uniform(0.03, 0.05), (x + rr * math.cos(a), rr * math.sin(a), h - 0.06), "grain", seg=6, rings=4, squash=(1, 1, 0.5))
    bx(b, (0.55, -0.25, 0.0), (1.05, 0.25, 0.04), "black", pin=False)
    for j, z in enumerate((0.04, 0.36, 0.68)):
        bx(b, (0.57, -0.23, z), (1.03, 0.23, z + 0.26), ("plasticOrange", "plastic", "plasticBlue")[j], ch=0.006, pin=False)
        bx(b, (0.58, -0.22, z + 0.20), (1.02, 0.22, z + 0.255), "grain", pin=False)
    for xx in (0.55, 1.03):
        bx(b, (xx, -0.25, 0.0), (xx + 0.02, -0.23, 0.98), "black", pin=False)
        bx(b, (xx, 0.23, 0.0), (xx + 0.02, 0.25, 0.98), "black", pin=False)
    return done(ctx, b, "SM_Prop_CT_DryGoods", M, cover_height=0.6,
                notes="Dry goods stall dressing: three open burlap sacks (rolled tops, heaped contents) and a steel rack of three bins.")


def m_styro(ctx, M):
    b = B(208)
    rng = ctx.rng("styro")
    z = 0.0
    for i in range(4):
        dx, dy = rng.uniform(-0.03, 0.03), rng.uniform(-0.02, 0.02)
        bx(b, (-0.31 + dx, -0.21 + dy, z), (0.31 + dx, 0.21 + dy, z + 0.20), "styro", ch=0.012, pin=False)
        bx(b, (-0.32 + dx, -0.22 + dy, z + 0.20), (0.32 + dx, 0.22 + dy, z + 0.235), "styro", ch=0.008, pin=False)
        z += 0.235
    return done(ctx, b, "SM_Prop_CT_StyrofoamBoxes", M, cover_height=None,
                notes="Stack of four styrofoam fish boxes with lids (market, alley A, yard).")


def m_tarp(ctx, M):
    b = B(209)
    L, W = 3.0, 2.0
    xs, ys = np.linspace(-L / 2, L / 2, 25), np.linspace(-W / 2, W / 2, 17)
    Fv = np.zeros((len(ys), len(xs), 3))
    Fv[..., 0], Fv[..., 1] = xs[None, :], ys[:, None]
    u, v = (xs[None, :] / (L / 2)), (ys[:, None] / (W / 2))
    Fv[..., 2] = -0.22 * (1 - u ** 2) * (1 - v ** 2) - 0.03 * np.sin(u * 7.0) * (1 - v ** 2)
    sheet(b, Fv[:, ::-1], 0.003, "fabricBlue", vdir=Y, fdir=X)
    for cx in (-L / 2, L / 2):
        for cy in (-W / 2, W / 2):
            rod(b, (cx, cy, 0.0), (cx * 1.03, cy * 1.06, 0.35), 0.005, "rubber", n=5)
    return done(ctx, b, "SM_Prop_CT_Tarp", M, ground=False, collision="none", expect_size=(None, None, None),
                notes="Blue tarp 3 x 2 m sagging 0.22 m, tied at the corners (ropes up 0.35 m). Pivot at the corner plane's centre: "
                      "hang it over a stall at 2.4 m or more (art only, above the nav band).")


def m_pendant(ctx, M):
    b = B(210)
    rod(b, (0, 0, 0.55), (0, 0, 0.16), 0.006, "rubber", n=6)          # a short drop from the stall's frame (under 0.6 m)
    lathe(b, [(0.0, 0.08), (0.03, 0.08), (0.035, 0.12), (0.022, 0.16), (0.0, 0.16)], "black", seg=10)
    ball(b, 0.045, (0, 0, 0.05), "bulb", seg=10, rings=7, squash=(1, 1, 1.2))
    for a in range(6):                                                                         # wire cage
        t = a * math.pi / 3
        rod(b, (0.03 * math.cos(t), 0.03 * math.sin(t), 0.10), (0.06 * math.cos(t), 0.06 * math.sin(t), 0.02), 0.0025, "black", n=4)
    return done(ctx, b, "SM_Prop_CT_PendantBulb", M, ground=False, collision="none",
                notes="Bare-bulb pendant with a wire cage on 1 m of cord (pivot = the bulb's bottom; hang from the market roof at 2.4 m+). "
                      "MI_Lamp_Bulb is emissive at night; the market's real lights are the four rects and two spots of chinatown.md 11.2.")


def m_fish_tank(ctx, M):
    b = B(211)
    L, W = 1.2, 0.5
    frame_box(b, -L / 2, L / 2, -W / 2, W / 2, 0.0, 0.80, 0.035, "black")
    bx(b, (-L / 2, -W / 2, 0.80), (L / 2, W / 2, 0.83), "black", pin=False)
    bx(b, (-L / 2 + 0.02, -W / 2 + 0.02, 0.83), (L / 2 - 0.02, W / 2 - 0.02, 1.30), "water", pin=False)
    for lo, hi in (((-L / 2, -W / 2, 0.83), (L / 2, -W / 2 + 0.012, 1.42)), ((-L / 2, W / 2 - 0.012, 0.83), (L / 2, W / 2, 1.42)),
                   ((-L / 2, -W / 2, 0.83), (-L / 2 + 0.012, W / 2, 1.42)), ((L / 2 - 0.012, -W / 2, 0.83), (L / 2, W / 2, 1.42))):
        bx(b, lo, hi, "glass", pin=False)
    bx(b, (-L / 2 - 0.01, -W / 2 - 0.01, 1.42), (L / 2 + 0.01, W / 2 + 0.01, 1.45), "black", pin=False)
    bx(b, (0.30, -0.08, 1.45), (0.48, 0.08, 1.55), "plastic", ch=0.01, pin=False)              # pump
    rod(b, (0.39, 0.0, 1.50), (0.39, 0.0, 0.88), 0.004, "rubber", n=5)
    return done(ctx, b, "SM_Prop_CT_FishTank", M, cover_height=0.8,
                notes="Live tank on a steel stand: opaque glass (MI_Glass_Store), dark water, an air pump and hose (the bubbles are "
                      "in the Unreal material). Market east wall.")


def m_scale(ctx, M):
    b = B(212)
    rod(b, (0, 0, 0.95), (0, 0, 0.78), 0.006, "chrome", n=6)
    lathe(b, [(0.0, 0.58), (0.11, 0.58), (0.12, 0.62), (0.12, 0.74), (0.11, 0.78), (0.0, 0.78)], "plasticOrange", seg=16)
    lathe(b, [(0.0, 0.751), (0.095, 0.751), (0.095, 0.755), (0.0, 0.755)], "clothLight", seg=16)
    for a in range(3):
        t = a * 2 * math.pi / 3
        rod(b, (0, 0, 0.58), (0.16 * math.cos(t), 0.16 * math.sin(t), 0.30), 0.0025, "chrome", n=4)
    lathe(b, [(0.0, 0.28), (0.18, 0.28), (0.19, 0.31), (0.0, 0.30)], "stainless", seg=16)
    return done(ctx, b, "SM_Prop_CT_HangingScale", M, ground=False, collision="none",
                notes="Hanging dial scale with a pan on three chains (pivot on the ground line: hang at 1.0 m above the counter top).")


def m_hand_truck(ctx, M):
    b = B(213)
    for s in (-0.18, 0.18):
        rod(b, (0.0, s, 0.12), (-0.18, s, 1.20), 0.014, "black", n=8)
    for z in (0.40, 0.75, 1.05):
        rod(b, (-0.04 - z * 0.15, -0.18, z), (-0.04 - z * 0.15, 0.18, z), 0.010, "black", n=6)
    bx(b, (0.0, -0.20, 0.0), (0.24, 0.20, 0.012), "black", pin=False)
    for s in (-0.24, 0.24):
        r = geo.cylinder(0.12, 0.07, 14, name="w", axis="Y")
        geo.transform(r, loc=(-0.06, s, 0.12))
        b.absorb(r, "rubber")
    rod(b, (-0.06, -0.24, 0.12), (-0.06, 0.24, 0.12), 0.01, "chrome", n=6)
    for i in range(3):                                                                          # a load of cartons
        bx(b, (0.02, -0.19, 0.012 + i * 0.30), (0.42, 0.19, 0.30 + i * 0.30), "card", ch=0.006, pin=False)
    return done(ctx, b, "SM_Prop_CT_HandTruck", M, cover_height=None,
                notes="Hand truck with three cartons on it (the party-goods wholesaler's, alley A).")


# ================================================================================================= vendors on Canal

def m_vendor_table(ctx, M):
    b = B(220)
    L, W, H = 1.8, 0.76, 0.75
    for x in (-L / 2 + 0.06, L / 2 - 0.06):
        rod(b, (x, -W / 2 + 0.05, 0.0), (x, W / 2 - 0.05, H - 0.04), 0.02, "grey", n=6)
        rod(b, (x, W / 2 - 0.05, 0.0), (x, -W / 2 + 0.05, H - 0.04), 0.02, "grey", n=6)
    bx(b, (-L / 2, -W / 2, H - 0.04), (L / 2, W / 2, H), "plastic", ch=0.008)
    xs, zs = np.linspace(-L / 2 - 0.02, L / 2 + 0.02, 37), np.linspace(0.0, 1.0, 9)
    for s in (-1, 1):                                                                           # the cloth's skirt, front and back
        Fv = np.zeros((len(zs), len(xs), 3))
        Fv[..., 0] = xs[None, :]
        Fv[..., 1] = s * (W / 2 + 0.012 + 0.015 * np.sin(xs[None, :] * 9.0) * (1 - zs[:, None]))
        Fv[..., 2] = H + 0.002 - (1 - zs[:, None]) * 0.40
        sheet(b, Fv if s < 0 else Fv[:, ::-1], 0.003, "fabricWhite", vdir=Z, fdir=X)
    top = np.zeros((2, 2, 3))
    top[..., 0] = [[-L / 2 - 0.02, L / 2 + 0.02]] * 2
    top[..., 1] = [[-W / 2 - 0.012] * 2, [W / 2 + 0.012] * 2]
    top[..., 2] = H + 0.003
    sheet(b, top, 0.002, "fabricWhite", vdir=Y, fdir=X)
    return done(ctx, b, "SM_Prop_CT_VendorTable", M, expect_size=(None, None, None), cover_height=H,
                notes="Folding vendor table 1.8 x 0.76 x 0.75 with a white cloth hanging 0.40 m at the front and back (the Canal "
                      "table strip, chinatown.md 4.1: 1.8 m tables at a 4 m pitch). Goods clusters sit on top.")


def m_goods(ctx, M, kind):
    b = B(221 + len(kind))
    rng = ctx.rng("goods", kind)
    if kind == "Bags":                                                                          # unbranded handbags in rows
        for i in range(10):
            x, y = -0.75 + (i % 5) * 0.32, -0.16 + (i // 5) * 0.30
            w, d, h = rng.uniform(0.24, 0.30), rng.uniform(0.10, 0.14), rng.uniform(0.18, 0.26)
            bx(b, (x - w / 2, y - d / 2, 0.0), (x + w / 2, y + d / 2, h), ("cloth", "clothLight", "plastic")[i % 3], ch=0.02, pin=False)
            for dx in (-w * 0.25, w * 0.25):
                rod(b, (x + dx, y, h), (x + dx * 0.6, y, h + 0.08), 0.006, "plastic", n=5)
            rod(b, (x - w * 0.15, y, h + 0.08), (x + w * 0.15, y, h + 0.08), 0.006, "plastic", n=5)
        what = "ten unbranded handbags in two rows (no logo, monogram or pattern)"
    elif kind == "Caps":                                                                        # a pegboard of caps
        bx(b, (-0.45, -0.03, 0.0), (0.45, 0.03, 0.90), "ply", ch=0.004)
        for i in range(12):
            x, z = -0.33 + (i % 4) * 0.22, 0.18 + (i // 4) * 0.26
            cap = geo.sphere(0.085, 10, 5)
            geo.transform(cap, loc=(x, -0.06, z), rot=(90, 0, 0), scale=(1.0, 1.0, 0.75))
            b.absorb(cap, ("cloth", "clothLight", "fabricGreen", "fabricYellow")[i % 4])
            bx(b, (x - 0.07, -0.17, z - 0.07), (x + 0.07, -0.05, z - 0.06), ("cloth", "clothLight", "fabricGreen", "fabricYellow")[i % 4], pin=False)
        what = "a pegboard of twelve plain caps (their CANAL ST lettering, if wanted, is a decal; no logos)"
    elif kind == "TShirts":                                                                     # folded stacks
        for i in range(6):
            x, y = -0.6 + (i % 3) * 0.42, -0.14 + (i // 3) * 0.32
            n = rng.integers(4, 8)
            for k in range(n):
                bx(b, (x - 0.17 + rng.uniform(-0.01, 0.01), y - 0.13, k * 0.03), (x + 0.17, y + 0.13, k * 0.03 + 0.028),
                   ("clothLight", "cloth", "fabricRed", "fabricBlue")[(i + k) % 4], ch=0.008, pin=False)
        what = "six stacks of folded T-shirts (plain; the NEW YORK print is a decal if wanted, no brand)"
    elif kind == "Shades":                                                                      # spinner rack of sunglasses
        rod(b, (0, 0, 0.0), (0, 0, 0.95), 0.012, "chrome", n=8)
        lathe(b, [(0.0, 0.0), (0.20, 0.0), (0.20, 0.02), (0.0, 0.02)], "black", seg=12)
        for k in range(4):
            z = 0.32 + k * 0.17
            for a in range(8):
                t = a * math.pi / 4
                cx, cy = 0.13 * math.cos(t), 0.13 * math.sin(t)
                bx(b, (cx - 0.07, cy - 0.006, z), (cx + 0.07, cy + 0.006, z + 0.045), "plastic", pin=False)
                bx(b, (cx - 0.075, cy - 0.003, z + 0.008), (cx + 0.075, cy + 0.003, z + 0.040), "glasswin", pin=False)
        what = "a spinner rack of sunglasses (unbranded)"
    else:                                                                                       # Discs: disc cases and USB tray
        for i in range(18):
            x, y = -0.75 + (i % 6) * 0.27, -0.25 + (i // 6) * 0.20
            for k in range(rng.integers(3, 7)):
                bx(b, (x - 0.07, y - 0.062, k * 0.011), (x + 0.07, y + 0.062, k * 0.011 + 0.010), ("plastic", "clothLight")[k % 2], pin=False)
        bx(b, (0.82, -0.25, 0.0), (1.10, 0.25, 0.03), "plastic", pin=False)
        for i in range(20):
            bx(b, (0.84 + (i % 4) * 0.065, -0.23 + (i // 4) * 0.095, 0.03), (0.88 + (i % 4) * 0.065, -0.21 + (i // 4) * 0.095, 0.042), "alu", pin=False)
        what = "stacks of disc cases (no real titles) and a tray of USB sticks"
    return done(ctx, b, "SM_Prop_CT_Goods_" + kind, M, ground=False, collision="none",
                notes="Vendor goods cluster: %s. Sits on SM_Prop_CT_VendorTable (top 0.753 m)." % what)


def m_umbrella(ctx, M):
    b = B(230)
    R, zr = 1.1, 2.15
    rod(b, (0, 0, 0.08), (0, 0, zr + 0.12), 0.024, "alu", n=10)
    lathe(b, [(0.0, 0.0), (0.24, 0.0), (0.24, 0.08), (0.06, 0.10), (0.0, 0.10)], "plastic", seg=14)
    n = 8
    for i in range(n):
        a0, a1 = i * 2 * math.pi / n, (i + 1) * 2 * math.pi / n
        us = np.linspace(0, 1, 5)
        rs = np.linspace(0.04, R, 7)
        Fv = np.zeros((len(rs), len(us), 3))
        aa = a0 + (a1 - a0) * us
        Fv[..., 0] = rs[:, None] * np.cos(aa)[None, :]
        Fv[..., 1] = rs[:, None] * np.sin(aa)[None, :]
        Fv[..., 2] = zr - 0.42 * (rs[:, None] / R) ** 1.3 + 0.03 * np.sin(np.pi * us)[None, :] * (rs[:, None] / R)
        sheet(b, Fv, 0.003, ("fabricGreen", "fabricWhite")[i % 2], vdir=Z, fdir=X)
        rod(b, (0, 0, zr - 0.02), (R * math.cos(a0), R * math.sin(a0), zr - 0.425), 0.018, "alu", n=5)
    return done(ctx, b, "SM_Prop_CT_MarketUmbrella", M, collision="none", cover_height=None,
                notes="Vendor umbrella 2.2 m across in green and white panels, aluminium pole in a weighted base (red is kept off the "
                      "street's fight backgrounds, chinatown.md 1). Canopy above the nav band; only the base blocks.")


def m_clothing_rail(ctx, M):
    b = B(231)
    rng = ctx.rng("rail")
    L = 1.5
    for x in (-L / 2, L / 2):
        rod(b, (x, 0, 0.05), (x, 0, 1.55), 0.02, "chrome", n=8)
        rod(b, (x, -0.25, 0.04), (x, 0.25, 0.04), 0.02, "chrome", n=8)
    rod(b, (-L / 2, 0, 1.55), (L / 2, 0, 1.55), 0.02, "chrome", n=8)
    for i in range(14):
        x = -L / 2 + 0.10 + i * (L - 0.2) / 13 + rng.uniform(-0.02, 0.02)
        rod(b, (x, 0, 1.55), (x, 0, 1.47), 0.003, "chrome", n=4)
        bx(b, (x - 0.012, -0.24, 0.85 + rng.uniform(-0.05, 0.05)), (x + 0.012, 0.24, 1.47),
           ("cloth", "clothLight", "fabricBlue", "fabricGreen", "fabricPink")[i % 5], ch=0.006, pin=False)
    return done(ctx, b, "SM_Prop_CT_ClothingRail", M, cover_height=None,
                notes="Clothing rail 1.5 m with fourteen plain garments (no prints).")


# ================================================================================================= lanterns

def lantern_parts(b, z0=0.0):
    """Red paper lantern 0.42 m: ribbed paper body, gold rings top and bottom, a red tassel."""
    prof = [(0.0, z0 + 0.06), (0.07, z0 + 0.06)]
    for t in np.linspace(0.05, 0.95, 7):
        prof.append((0.07 + 0.15 * math.sin(math.pi * t), z0 + 0.06 + 0.32 * t))
    prof += [(0.07, z0 + 0.38), (0.0, z0 + 0.38)]
    lathe(b, prof, "paper", seg=12)
    for zz in (z0 + 0.045, z0 + 0.38):
        lathe(b, [(0.0, zz), (0.075, zz), (0.075, zz + 0.018), (0.0, zz + 0.018)], "gold", seg=10)
    rod(b, (0, 0, z0 + 0.045), (0, 0, z0 - 0.02), 0.005, "gold", n=5)
    lathe(b, [(0.0, z0 - 0.20), (0.022, z0 - 0.19), (0.016, z0 - 0.02), (0.0, z0 - 0.015)], "paper", seg=6)
    rod(b, (0, 0, z0 + 0.398), (0, 0, z0 + 0.45), 0.003, "black", n=4)


def m_lantern(ctx, M):
    b = B(240)
    lantern_parts(b, 0.20)
    return done(ctx, b, "SM_Prop_CT_Lantern", M, ground=False, collision="none",
                notes="Red paper lantern (0.44 m body, tassel to the pivot): pivot at the tassel tip, hook at z 0.65. No characters "
                      "on it (English-only level). One string of 16 over the banquet doors only (chinatown.md 4.8, 4.9); MI_Paper_LanternRed "
                      "glows 40 to 80 nits at night.")


def m_lantern_string(ctx, M):
    """The cable for 16 lanterns across the banquet doors: a catenary 14 m long with 16 drop hooks. The lanterns are
    instances of SM_Prop_CT_Lantern at the hook points (listed in the notes and in signs_chinatown.json)."""
    b = B(241)
    L, sag = 14.0, 0.55
    xs = np.linspace(0, L, 21)
    zs = -sag * (1 - ((xs - L / 2) / (L / 2)) ** 2)
    # a 40 mm sleeved messenger cable, not an 8 mm wire: thin lines crawl at render scale 0.50 (chinatown.md 13.4)
    sg.tube(b, np.stack([xs, np.zeros_like(xs), zs], 1), 0.026, "black", seg=4, closed=False, plane=Y)
    hooks = []
    for i in range(16):
        x = L * (i + 0.5) / 16
        z = -sag * (1 - ((x - L / 2) / (L / 2)) ** 2)
        rod(b, (x, 0, z), (x, 0, z - 0.12), 0.006, "black", n=3)
        hooks.append((round(x, 3), 0.0, round(z - 0.12 - 0.65, 3)))
    for x in (0.0, L):
        bx(b, (x - 0.04, -0.04, -0.05), (x + 0.04, 0.04, 0.05), "black", pin=False)
    ctx.lantern_hooks = hooks
    return done(ctx, b, "SM_Prop_CT_LanternString_14m", M, ground=False, collision="none", expect_size=(L + 0.08, None, None),
                notes="Lantern cable 14 m with 16 hooks, sagging 0.55 m; pivot at the west fixing (wall bracket), running +X. Lantern "
                      "instances (SM_Prop_CT_Lantern pivots) at local %s m." % (hooks,))


# ================================================================================================= street and the Square

def m_ebike(ctx, M):
    b = B(250)
    for x in (-0.55, 0.55):
        w = geo.torus(0.27, 0.03, 20, 8)
        geo.transform(w, loc=(x, 0, 0.30), rot=(90, 0, 0))
        b.absorb(w, "rubber")
        hub = geo.cylinder(0.06, 0.07, 10, name="hub", axis="Y")
        geo.transform(hub, loc=(x, 0, 0.30))
        b.absorb(hub, "alu")
        for a in range(6):
            t = a * math.pi / 3
            rod(b, (x, 0, 0.30), (x + 0.25 * math.cos(t), 0, 0.30 + 0.25 * math.sin(t)), 0.004, "alu", n=4)
    pts = [(-0.55, 0, 0.30), (-0.10, 0, 0.36), (0.40, 0, 0.62), (-0.18, 0, 0.82), (-0.10, 0, 0.36)]
    for p, q in zip(pts[:-1], pts[1:]):
        rod(b, p, q, 0.022, "black", n=8)
    rod(b, (0.55, 0, 0.30), (0.40, 0, 0.62), 0.016, "black", n=8)
    rod(b, (0.40, 0, 0.62), (0.34, 0, 1.05), 0.016, "black", n=8)
    rod(b, (0.34, -0.30, 1.05), (0.34, 0.30, 1.05), 0.012, "black", n=6)
    bx(b, (-0.06, -0.08, 0.40), (0.26, 0.08, 0.58), "plastic", ch=0.02, pin=False)                       # battery
    bx(b, (-0.30, -0.08, 0.86), (-0.06, 0.08, 0.92), "plastic", ch=0.02, pin=False)                       # saddle
    bx(b, (-0.85, -0.18, 0.62), (-0.35, 0.18, 0.66), "black", pin=False)                                  # rack
    bx(b, (-0.84, -0.20, 0.66), (-0.36, 0.20, 1.10), "fabricYellow", ch=0.025, pin=False)                 # insulated delivery box
    return done(ctx, b, "SM_Prop_CT_EBike", M, cover_height=None, expect_size=(None, None, None),
                notes="Delivery e-bike with an insulated box (plain yellow, no brand), chained to the Mott shed posts (2).")


def m_bale(ctx, M):
    b = B(251)
    bx(b, (-0.55, -0.40, 0.0), (0.55, 0.40, 0.80), "card", ch=0.03)
    for x in (-0.30, 0.0, 0.30):
        bx(b, (x - 0.012, -0.405, -0.005), (x + 0.012, 0.405, 0.805), "plastic", pin=False)
    return done(ctx, b, "SM_Prop_CT_CardboardBale", M, cover_height=0.8,
                notes="Baled cardboard 1.1 x 0.8 x 0.8 with three straps (kerbside on Mott, alley B).")


def m_stanchion(ctx, M):
    b = B(252)
    for x in (-0.6, 0.6):
        lathe(b, [(0.0, 0.0), (0.17, 0.0), (0.17, 0.02), (0.03, 0.05), (0.03, 0.0)], "chrome", loc=(x, 0, 0), seg=14)
        rod(b, (x, 0, 0.05), (x, 0, 0.95), 0.03, "chrome", n=10)
        lathe(b, [(0.0, 0.95), (0.04, 0.95), (0.04, 1.0), (0.0, 1.0)], "chrome", loc=(x, 0, 0), seg=10)
    bx(b, (-0.58, -0.006, 0.86), (0.58, 0.006, 0.91), "cloth", pin=False)
    return done(ctx, b, "SM_Prop_CT_Stanchions", M, collision="none", cover_height=None,
                notes="Two queue stanchions with a belt (the coach office's waiting line on Mott, chinatown.md 4.6).")


def m_card_table(ctx, M):
    b = B(253)
    s, H = 0.86, 0.71
    for cx in (-s / 2 + 0.03, s / 2 - 0.03):
        for cy in (-s / 2 + 0.03, s / 2 - 0.03):
            rod(b, (cx, cy, 0), (cx, cy, H - 0.03), 0.011, "black", n=6)
    bx(b, (-s / 2, -s / 2, H - 0.03), (s / 2, s / 2, H), "black", ch=0.006)
    bx(b, (-s / 2 + 0.02, -s / 2 + 0.02, H), (s / 2 - 0.02, s / 2 - 0.02, H + 0.003), "fabricGreen", pin=False)
    rng = ctx.rng("cards")
    for i in range(8):                                                                          # cards and a game board's pieces
        x, y = rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3)
        bx(b, (x - 0.03, y - 0.045, H + 0.003), (x + 0.03, y + 0.045, H + 0.005), "clothLight", pin=False)
    for i in range(10):
        lathe(b, [(0.0, H + 0.003), (0.016, H + 0.003), (0.016, H + 0.013), (0.0, H + 0.013)], ("timber", "fabricRed")[i % 2],
              loc=(rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0), seg=8)
    return done(ctx, b, "SM_Prop_CT_CardTable", M, cover_height=H,
                notes="Folding card table 0.86 m square with cards and game pieces (the Square, where old men play in the evening).")


def m_stool(ctx, M):
    b = B(254)
    for s in (-1, 1):
        rod(b, (s * 0.15, -0.15, 0.0), (s * 0.15, 0.15, 0.44), 0.010, "black", n=6)
        rod(b, (s * 0.15, 0.15, 0.0), (s * 0.15, -0.15, 0.44), 0.010, "black", n=6)
    bx(b, (-0.17, -0.17, 0.44), (0.17, 0.17, 0.47), "plasticBlue", ch=0.01)
    return done(ctx, b, "SM_Prop_CT_Stool", M, collision="none", notes="Folding stool (card tables, vendors).")


def m_bench(ctx, M):
    b = B(255)
    L = 1.8
    for x in (-L / 2 + 0.12, 0.0, L / 2 - 0.12):
        bar(b, (x, -0.25, 0.0), (x, -0.22, 0.45), 0.05, 0.03, "black")
        bar(b, (x, 0.22, 0.0), (x, 0.14, 0.45), 0.05, 0.03, "black")
        bar(b, (x, -0.25, 0.42), (x, 0.22, 0.42), 0.05, 0.03, "black")
        bar(b, (x, 0.18, 0.45), (x, 0.26, 0.85), 0.05, 0.03, "black")
    for i in range(4):
        y = -0.22 + i * 0.12
        bx(b, (-L / 2, y, 0.45), (L / 2, y + 0.09, 0.48), "timber", ch=0.006)
    for i in range(2):
        z = 0.58 + i * 0.16
        bx(b, (-L / 2, 0.20 + i * 0.03, z), (L / 2, 0.23 + i * 0.03, z + 0.10), "timber", ch=0.006)
    for x in (-L / 2 + 0.12, L / 2 - 0.12, 0.0):                                                 # armrests split the seat
        bar(b, (x, -0.24, 0.48), (x, -0.24, 0.66), 0.04, 0.03, "black")
        bar(b, (x, -0.26, 0.66), (x, 0.18, 0.66), 0.05, 0.03, "black")
    return done(ctx, b, "SM_Prop_CT_ParkBench", M, cover_height=0.85,
                notes="Park bench 1.8 m with cast armrests that split the seat, timber slats (the Square, chinatown.md 4.8).")


def m_hoop(ctx, M):
    b = B(256)
    rod(b, (0, 0, 0), (0, 0, 3.40), 0.06, "grey", n=12)
    bar(b, (0, 0, 3.30), (0.95, 0, 3.30), 0.06, 0.06, "grey")
    bx(b, (0.95, -0.90, 2.90), (0.98, 0.90, 3.95), "stainless", ch=0.01)
    bx(b, (0.98, -0.30, 3.05), (0.985, 0.30, 3.50), "black", pin=False)
    ring = geo.torus(0.23, 0.009, 20, 6)
    geo.transform(ring, loc=(1.21, 0, 3.05))
    b.absorb(ring, "fabricRed")
    for a in range(12):
        t = a * math.pi / 6
        rod(b, (1.21 + 0.23 * math.cos(t), 0.23 * math.sin(t), 3.05), (1.21 + 0.15 * math.cos(t + 0.3), 0.15 * math.sin(t + 0.3), 2.65),
            0.003, "clothLight", n=3)
    lathe(b, [(0.0, 0.0), (0.16, 0.0), (0.16, 0.02), (0.0, 0.02)], "grey", seg=12)
    return done(ctx, b, "SM_Prop_CT_BasketballHoop", M, cover_height=None,
                notes="Basketball hoop on a pole (the Square's south-east corner, x 40.6..40.9, z 16.0..16.3): steel backboard, a worn "
                      "net. Only the pole blocks (its collider box).")


def m_edging(ctx, M):
    b = B(257)
    L, H = 3.0, 0.9
    for x in (0.0, 1.5, 3.0):
        rod(b, (x, 0, 0), (x, 0, H), 0.024, "galv", n=8)
    rod(b, (0, 0, H - 0.02), (L, 0, H - 0.02), 0.016, "galv", n=8)
    sg.card(b, (0.0, 0.0, 0.02), (L, 0, 0), (0, 0, H - 0.06), "chain", 1, 1, sign=False)
    sg.card(b, (L, 0.002, 0.02), (-L, 0, 0), (0, 0, H - 0.06), "chain", 1, 1, sign=False)
    return done(ctx, b, "SM_Prop_CT_ChainLinkEdging_3m", M, collision="box", cover_height=None, expect_size=(None, None, H),
                notes="Low chain-link edging 3 m x 0.9 m round the Square's dirt beds: posts, top rail, masked chain-link panel "
                      "(MI_ChainLink_Galv, two-sided card). Pivot at the west post, running +X.")


def m_fruit_stand(ctx, M):
    """Mott Street fruit stand: a three-step timber display with fruit in boxes, a scale and a price card stand."""
    b = B(258, step=0.6)      # coarse wear grid: the stand is small and its trays carry the detail
    rng = ctx.rng("fruitstand")
    L, W = 2.4, 1.2
    for i, (yy, z) in enumerate(((-W / 2, 0.55), (-W / 2 + 0.40, 0.80), (-W / 2 + 0.80, 1.05))):
        bx(b, (-L / 2, yy, 0.0), (L / 2, yy + 0.40, z), "wood", pin=False)
        for j in range(4):
            x0 = -L / 2 + 0.04 + j * 0.59
            bx(b, (x0, yy + 0.03, z), (x0 + 0.55, yy + 0.37, z + 0.012), "card", pin=False)
            for s in (0, 1):
                bx(b, (x0, yy + 0.03 + s * 0.33, z), (x0 + 0.55, yy + 0.04 + s * 0.33, z + 0.10), "card", pin=False)
            fr = ("orange", "apple", "yellow", "orange", "apple", "leaf")[(i * 4 + j) % 6]
            if fr == "leaf":
                greens(b, rng, x0, yy + 0.04, z + 0.012, 0.55, 0.32, n=3)
            else:
                fill_fruit(b, rng, x0 + 0.01, yy + 0.045, z + 0.012, 0.53, 0.31, 0.052, fr, layers=1, seg=5)
    return done(ctx, b, "SM_Prop_CT_FruitStand", M, cover_height=1.0,
                notes="Sidewalk fruit stand 2.4 x 1.2 m, three steps of cardboard trays with fruit and greens (under the Mott shed's "
                      "south end, chinatown.md 4.6; S3's grocery front).")


# ================================================================================================= roofs

def m_condenser(ctx, M):
    b = B(260)
    bx(b, (-0.55, -0.45, 0.0), (0.55, 0.45, 0.12), "black", pin=False)
    bx(b, (-0.50, -0.40, 0.12), (0.50, 0.40, 1.20), "galv", ch=0.01)
    for z in np.arange(0.20, 1.10, 0.09):                                                       # coil guard bars on the long faces
        fc.bx(b, (-0.46, -0.43, z), (0.46, -0.40, z + 0.04), "alu", pin=False)
        fc.bx(b, (-0.46, 0.40, z), (0.46, 0.43, z + 0.04), "alu", pin=False)
    lathe(b, [(0.0, 1.20), (0.36, 1.20), (0.36, 1.26), (0.0, 1.26)], "black", seg=16)
    for a in range(5):
        t = a * 2 * math.pi / 5
        rod(b, (0, 0, 1.24), (0.34 * math.cos(t), 0.34 * math.sin(t), 1.24), 0.012, "black", n=4)
    rod(b, (0.50, 0.2, 0.40), (0.85, 0.2, 0.40), 0.02, "rubber", n=6)
    return done(ctx, b, "SM_Prop_CT_Condenser", M, cover_height=1.2,
                notes="Rooftop condenser 1.1 x 0.9 x 1.26 m (three on the market roof: cover from Buzzards and roof Goons).")


def m_skylight(ctx, M):
    b = B(261)
    L, W, H = 3.0, 2.0, 0.8
    bx(b, (-L / 2, -W / 2, 0.0), (L / 2, W / 2, 0.45), "roof", ch=0.02)                          # upstand
    for s in (-1, 1):                                                                           # hipped glass faces
        Fv = np.zeros((2, 2, 3))
        Fv[..., 0] = [[-L / 2 + 0.05, L / 2 - 0.05]] * 2
        Fv[0, :, 1], Fv[1, :, 1] = s * (W / 2 - 0.05), 0.0
        Fv[0, :, 2], Fv[1, :, 2] = 0.47, H
        sheet(b, Fv if s > 0 else Fv[:, ::-1], 0.01, "glasswin", vdir=Y, fdir=X)
    rod(b, (-L / 2 + 0.05, 0, H), (L / 2 - 0.05, 0, H), 0.03, "alu", n=6)
    for x in np.linspace(-L / 2 + 0.05, L / 2 - 0.05, 5):
        for s in (-1, 1):
            rod(b, (x, s * (W / 2 - 0.05), 0.47), (x, 0, H), 0.012, "alu", n=4)
    return done(ctx, b, "SM_Prop_CT_Skylight", M, cover_height=0.8, expect_size=(L, W, None),
                notes="Hipped skylight 3 x 2 x 0.8 m on a roofing upstand (four on the market roof; light from the hall below at night "
                      "is a level light, not this mesh).")


def m_hatch(ctx, M):
    b = B(262)
    bx(b, (-0.5, -0.5, 0.0), (0.5, 0.5, 0.40), "roof", ch=0.02)
    bx(b, (-0.52, -0.52, 0.40), (0.52, 0.52, 0.48), "galv", ch=0.008)
    rod(b, (-0.2, 0.52, 0.44), (0.2, 0.52, 0.44), 0.012, "galv", n=6)
    return done(ctx, b, "SM_Prop_CT_RoofHatch", M, cover_height=0.48, notes="Roof hatch 1.04 m square on an upstand.")


PROPS = [m_stall_counter, m_fish_counter, lambda c, M: m_produce(c, M, "Citrus"), lambda c, M: m_produce(c, M, "Greens"),
         lambda c, M: m_produce(c, M, "Mixed"), m_dry_goods, m_styro, m_tarp, m_pendant, m_fish_tank, m_scale, m_hand_truck,
         m_vendor_table] + [(lambda k: (lambda c, M: m_goods(c, M, k)))(k) for k in ("Bags", "Caps", "TShirts", "Shades", "Discs")] + \
        [m_umbrella, m_clothing_rail, m_lantern, m_lantern_string, m_ebike, m_bale, m_stanchion, m_card_table, m_stool, m_bench,
         m_hoop, m_edging, m_fruit_stand, m_condenser, m_skylight, m_hatch]
