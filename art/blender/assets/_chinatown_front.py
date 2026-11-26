"""Canal Street kit, part 2: shop fronts, grilles, the stacked-sign rail, box awnings, the sign carriers, the exposed
neon and the market's rooftop letters.

Wall modules (shop fronts, grille, awnings): pivot at the bottom-left corner of the outer face, running +X, outer face
toward -Y (README conventions, the Block's facade kit). Shop fronts stand between the Block's piers
(SM_Facade_Pier_<Brick>, 0.32 m) under a sign band: the module is the clear width between piers, 2.77 m high.

Sign carriers carry no words: the face is slot M_Sign_CT_Face on 0..1 UVs (u left to right as read, v up), and the
placed sign's material instance picks its cell of Sign_CT_Atlas1 (assets/_chinatown_atlas.py, signs_chinatown.json).
Bands, kiosks, boards, posters: pivot at the bottom-left of the face, face toward -Y, the body behind (+Y), as the
Block's signs. Blades: pivot at the wall fixing on the wall plane at the blade's bottom, the blade running out along -Y,
faces looking +-X (each face reads correctly from its side). Street blades: pivot at the clamp, faces +-Y.
"""
import math

import numpy as np

from assets import facade as fc
from assets import signs as sg
from assets._chinatown_kit import SLOT_META, absorb, done, lathe, rod
from assets.facade import BAND0, BULK, DOOR_W, HEAD, B, bar, bx, sheet
from mi import geo

X, Y, Z = np.eye(3)


def face_uv(b, ob, key="face"):
    """Map every face part of slot `key` to 0..1 over its own extent (the carriers share one material)."""
    o = b._out
    if key not in o["order"]:
        return 0
    si = o["order"].index(key)
    uvl = ob.data.uv_layers[0].data
    uv = np.empty(len(uvl) * 2, np.float32)
    uvl.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    sel = o["slot"] == si
    n = 0
    for p in np.unique(o["part"][sel]):
        m = sel & (o["part"] == p)
        lo, hi = uv[m].min(0), uv[m].max(0)
        uv[m] = (uv[m] - lo) / np.maximum(hi - lo, 1e-9)
        n += 1
    uvl.foreach_set("uv", uv.ravel())
    return n


def done_sign(ctx, b, name, M, **asset):
    ob = b.finish(name, M, ctx.kit)
    face_uv(b, ob)
    fc.weather(ctx, b, ob, name, ledges=[], ground=False)
    asset.setdefault("collision", "none")
    ctx.asset(ob, slots=SLOT_META, **asset)
    ctx.K[name] = ob
    return ob


# ================================================================================================= shop fronts

def gate_up(b, x0, x1, z1, hood=0.30):
    """A roll gate rolled up: the hood box over the opening and the two guide rails."""
    for px in (x0, x1 - 0.10):
        bx(b, (px, -0.115, 0), (px + 0.10, 0, z1 - hood + 0.03), "trim", ch=0.004, axis="z", pin=False)
    bx(b, (x0, -0.27, z1 - hood), (x1, 0, z1), "grey", ch=0.006, axis="x", pin=False)
    b.rivets([(xx, -0.27, z1 - hood + 0.03) for xx in np.arange(x0 + 0.08, x1 - 0.05, 0.32)], -Y, "grey", d=0.02, h=0.008, leak=0.15)
    bx(b, (x0 + 0.12, -0.10, z1 - hood - 0.02), (x1 - 0.12, -0.06, z1 - hood + 0.01), "grey", pin=False)      # the curtain's bottom bar
    b.leaks += [(x0 + 0.04, -0.27, z1 - hood), (x1 - 0.04, -0.27, z1 - hood)]


SHOPFRONTS = {
    # name: clear width, door left edge (None: open front or gate down), bulkhead, what
    "Wide": (6.0, 3.6, "tile", "glazed front, door right of centre, gate rolled up"),
    "Narrow": (2.4, 0.55, "metal", "a narrow glazed door shop (one bay), gate rolled up"),
    "Restaurant": (5.0, 0.4, "tile", "a restaurant front: door at the left, a wide window with a hanging rail for roast meats"),
    "Jewelry": (4.0, 1.375, "metal", "a jewellery front: two small display windows with security bars inside, door in the middle"),
    "Grocery": (6.0, None, "tile", "an open front (gate up, no glass): a stepped display shelf across the opening"),
    "Shut": (6.0, None, "metal", "a shuttered front, gate down and padlocked"),
}


def m_shopfront(ctx, M, name):
    c, d0, bulk, what = SHOPFRONTS[name]
    b = B(300 + len(name))
    rng = ctx.rng("ctshop", name)
    lit = dict(M, interior=M["interiorLit"])
    if name == "Shut":
        fc.gate(b, 0.0, c, BAND0, rng)
        coll = "box"
    elif name == "Grocery":
        gate_up(b, 0.0, c, BAND0)
        bx(b, (0.10, -0.06, 0.0), (c - 0.10, 0.02, 0.06), "conc", ch=0.004, axis="x")                       # threshold
        for i, (yy, z) in enumerate(((-0.55, 0.45), (-0.25, 0.70), (0.05, 0.95))):                          # stepped shelf
            bx(b, (0.25, yy, 0.0), (c - 1.6, yy + 0.30, z), "wood", ch=0.006, pin=False)
        bx(b, (c - 1.45, 0.05, 0.0), (c - 0.15, 1.20, 2.30), "interior", pin=False)                          # the way in, lit inside
        bx(b, (0.10, 1.20, 0.0), (c - 0.10, 1.24, HEAD), "interior", pin=False)
        bx(b, (0.10, 0.0, HEAD), (c - 0.10, 1.24, HEAD + 0.04), "interior", pin=False)
        coll = "complex"
    else:
        gate_up(b, 0.0, c, BAND0)
        if d0 > 0.05:
            fc.glazing(b, 0.0, d0, HEAD - 0.32, bulk)
        if c - d0 - DOOR_W > 0.05:
            fc.glazing(b, d0 + DOOR_W, c, HEAD - 0.32, bulk)
        fc.shop_door(b, d0, HEAD - 0.32)
        bx(b, (0, -0.12, HEAD - 0.32), (c, 0.02, BAND0 - 0.30), "trim", ch=0.004, axis="x", pin=False)
        if name == "Restaurant":                                                                             # roast-meat rail
            rod(b, (d0 + DOOR_W + 0.15, 0.25, 1.95), (c - 0.15, 0.25, 1.95), 0.012, "chrome", n=6)
            for xx in np.arange(d0 + DOOR_W + 0.30, c - 0.2, 0.32):
                rod(b, (xx, 0.25, 1.95), (xx, 0.25, 1.80), 0.003, "chrome", n=4)
        if name == "Jewelry":                                                                                # bars inside the glass
            for a, e in ((0.0, d0), (d0 + DOOR_W, c)):
                for xx in np.arange(a + 0.10, e - 0.05, 0.11):
                    rod(b, (xx, 0.05, BULK + 0.02), (xx, 0.05, HEAD - 0.34), 0.006, "chrome", n=5)
        coll = "complex"
    return done(ctx, b, "SM_Facade_Shopfront_CT_" + name, lit, ground=True, collision=coll, expect_size=(c, None, BAND0),
                notes="Canal Street shop front %.2f m between the piers, 2.77 m high: %s. Generic module: the shop's sign is a separate "
                      "carrier with its face from the atlas, so 14 shops need these six fronts (chinatown.md 13.2). Interior slot "
                      "MI_Interior_Lit (warm, lit at night)." % (c, what))


def m_fascia(ctx, M):
    """The strip over a shop front, 2.77 to 3.65 m, between the piers: a steel fascia the sign band hangs on and the belt
    course over it. 1 m long, meant to be scaled along its run (X) to the clear width."""
    b = B(319)
    bx(b, (0.0, -0.06, 0.0), (1.0, 0.30, 0.88), "trim", axis="x", pin=False)
    bx(b, (0.0, -0.075, 0.02), (1.0, -0.06, 0.86), "trim", ch=0.002, axis="x", pin=False)
    fc.belt(b, 0.0, 1.0, 0.70)
    return done(ctx, b, "SM_Facade_CT_Fascia_1m", M, ground=False, collision="box", expect_size=(1.0, None, None),
                ledges=[(0.0, 1.0, 0.70, 0.6)],
                notes="Fascia strip over a Canal shop front: steel panel 2.77 to 3.65 m with the belt course on top. 1.0 m long: "
                      "scale it along X to the clear width between the piers (placements_chinatown.json does). The shop's "
                      "SM_Sign_CT_Band_* hangs on it.")


def m_grille(ctx, M):
    """Security grille over a low upper window of the Block's bay (opening 1.24 x 1.736): pivot = the window's bottom centre
    on the wall plane, like SM_Facade_AirConditioner."""
    b = B(320)
    w, h = fc.WIN_W + 0.10, fc.WIN_H + 0.10
    x0, y = -w / 2, -0.05
    for xx in (x0, -x0 - 0.03):
        bx(b, (xx, y - 0.03, -0.05), (xx + 0.03, y, h - 0.05), "black", ch=0.003, pin=False)
    for zz in (-0.05, h / 2 - 0.05, h - 0.08):
        bx(b, (x0, y - 0.03, zz), (-x0, y, zz + 0.03), "black", ch=0.003, pin=False)
    for xx in np.arange(x0 + 0.12, -x0 - 0.05, 0.12):
        rod(b, (xx, y - 0.015, -0.03), (xx, y - 0.015, h - 0.06), 0.008, "black", n=6)
    for xx in (x0 + 0.015, -x0 - 0.015):
        for zz in (0.10, h - 0.25):
            bx(b, (xx - 0.03, y, zz), (xx + 0.03, 0.0, zz + 0.06), "black", pin=False)
    return done(ctx, b, "SM_Facade_CT_WindowGrille", M, ground=False, collision="none", expect_size=(w, None, h),
                notes="Steel security grille over a low upper window (BayWindow opening): 16 mm bars (no thin steel, chinatown.md 13.4), "
                      "frame 30 mm, fixed to the reveals. Pivot = window bottom centre on the wall plane (as the air conditioner).")


def m_sign_rail(ctx, M):
    """Steel rail projecting off the wall that carries signs stacked one over another."""
    b = B(321)
    out, H = 1.30, 3.2
    for x in (0.0, 0.9):
        bx(b, (x, -0.02, 0.0), (x + 0.10, 0.0, H), "black", ch=0.004, pin=False)                       # wall plates
        for z in (0.2, 1.25, 2.30, H - 0.10):
            bar(b, (x + 0.05, 0.0, z), (x + 0.05, -out, z), 0.05, 0.05, "black", ch=0.003)
        bar(b, (x + 0.05, -out, 0.2), (x + 0.05, -out, H - 0.10), 0.05, 0.05, "black", ch=0.003)
        bar(b, (x + 0.05, -0.05, 0.25), (x + 0.05, -out + 0.05, 1.20), 0.04, 0.04, "black", ch=0.003)  # diagonal
    for z in (0.2, 1.25, 2.30, H - 0.10):
        bar(b, (0.05, -out, z), (0.95, -out, z), 0.05, 0.05, "black", ch=0.003)
    return done(ctx, b, "SM_Facade_CT_StackedSignRail", M, ground=False, collision="none", expect_size=(1.0, None, H),
                notes="Stacked-sign rail: two wall plates 0.9 m apart, four arms 1.3 m out at 0.2 / 1.25 / 2.30 / 3.1 m and a front "
                      "post; hang kiosk faces (SM_Sign_CT_Kiosk_*) on its arms one over another. Pivot at the left plate's bottom on the "
                      "wall plane, arms along -Y. Mount its bottom at 3.2 m or more over the sidewalk.")


def m_box_awning(ctx, M, length, slot):
    """Box awning: a sloped cloth top and a vertical valance on a welded frame, closed ends. Pivot at the left end of the
    fixing line on the wall (2.75 m above the sidewalk, as the Block's awnings)."""
    b = B(330 + int(length))
    out, zt, zf, val = 1.10, 0.55, 0.0, 0.40
    for xx in np.linspace(0.02, length - 0.02, max(2, int(round(length / 1.5)) + 1)):
        bar(b, (xx, -0.01, zt), (xx, -out + 0.02, zf), 0.025, 0.025, "grey", ch=0.003)
        bar(b, (xx, -out + 0.015, zf), (xx, -out + 0.015, zf - val + 0.02), 0.025, 0.025, "grey", up=-Y, ch=0.003)
        bar(b, (xx, -0.01, zf - val + 0.05), (xx, -out + 0.03, zf - val + 0.05), 0.02, 0.02, "grey", ch=0.003)
    nc = int(length / 0.10) + 1
    xs = np.linspace(0, length, nc)
    t = np.linspace(0, 1, 9)[:, None]
    top = np.zeros((9, nc, 3))
    top[..., 0] = xs[None, :]
    top[..., 1] = -(out + 0.004) * (1 - t)
    top[..., 2] = zf + 0.004 + (zt - zf) * t - 0.012 * np.sin(np.pi * t) * (0.6 + 0.4 * np.sin(xs[None, :] * 2.1))
    sheet(b, top, 0.003, slot, vdir=Y, fdir=X)
    zr = np.linspace(0, 1, 4)[:, None]
    v = np.zeros((4, nc, 3))
    v[..., 0] = xs[None, :]
    v[..., 1] = -(out + 0.006)
    v[..., 2] = zf - val + (val + 0.004) * zr
    sheet(b, v, 0.003, slot)
    for xe, sgn in ((0.0, 1.0), (length, -1.0)):
        a = np.linspace(0.0, 1.0, 7)[None, :] if sgn > 0 else np.linspace(1.0, 0.0, 7)[None, :]
        wing = np.zeros((4, 7, 3))
        wing[..., 0] = xe - sgn * 0.004
        wing[..., 1] = -out * a
        ztop = zt + (zf - zt) * a
        wing[..., 2] = (zf - val) + (ztop - (zf - val)) * zr
        sheet(b, wing, 0.003, slot)
    b.leaks += [(0.02, -out, zf - val), (length - 0.02, -out, zf - val)]
    return done(ctx, b, "SM_Facade_CT_Awning_Box_%dm" % int(round(length)) + ("_" + slot[6:] if slot != "fabricGreen" else ""), M,
                ground=False, collision="none", expect_size=(length, None, None),
                notes="Box awning %.1f m: cloth top sloping 0.55 m over 1.10 m, a 0.40 m vertical valance (plain: no words, the shop's "
                      "name is on its sign), closed ends, welded frame. Pivot at the left end of the fixing line, 2.75 m above the "
                      "sidewalk. Slot %s (the cloth tint is per shop in Unreal)." % (length, slot, M[slot].name))


# ================================================================================================= sign carriers

def cabinet(b, w, h, D, slot="trim", f=0.04):
    """Lightbox cabinet: extruded body behind the face (y 0..D), retainer frame round the face, the face card itself."""
    bx(b, (0.0, 0.012, 0.0), (w, D, h), slot, ch=0.006, axis="x")
    for lo, hi in (((-0.004, -0.014, -0.004), (w + 0.004, 0.014, f)), ((-0.004, -0.014, h - f), (w + 0.004, 0.014, h + 0.004)),
                   ((-0.004, -0.014, f), (f, 0.014, h - f)), ((w - f, -0.014, f), (w + 0.004, 0.014, h - f))):
        bx(b, lo, hi, slot, ch=0.003, axis="x")
    sg.card(b, (0, 0.0, 0), (w, 0, 0), (0, 0, h), "face", max(2, int(w / 0.5)), 2)


def m_band(ctx, M, w):
    b = B(340 + int(w))
    h, D = 0.9, 0.20
    cabinet(b, w, h, D)
    for xc in (0.45, w - 0.45):                                                                           # Z clips
        bx(b, (xc - 0.04, D - 0.05, -0.035), (xc + 0.04, D, -0.004), "black", ch=0.002)
        bx(b, (xc - 0.04, D - 0.004, -0.035), (xc + 0.04, D, 0.06), "black")
    sg.whip(b, [(w - 0.02, D * 0.5, h * 0.25), (w + 0.07, D * 0.45, h * 0.18), (w + 0.10, D * 0.6, -0.05), (w + 0.02, D + 0.02, -0.10)],
            "rubber", 0.010)
    return done_sign(ctx, b, "SM_Sign_CT_Band_%dm" % int(w), M, expect_size=(None, None, None),
                     notes="Lightbox band %.0f x 0.9 m, 0.20 m deep: extruded cabinet, retainer frame 40 mm, face on 0..1 UVs (slot "
                           "M_Sign_CT_Face: the MI picks the shop's cell of Sign_CT_Atlas1), Z clips, power whip. Pivot bottom-left of "
                           "the face, face -Y. Mount on the facade's sign band (3.2 to 4.2 m on Canal)." % w)


def m_kiosk(ctx, M, w, h, tag):
    b = B(350 + int(w * 10))
    cabinet(b, w, h, 0.12, f=0.025)
    return done_sign(ctx, b, "SM_Sign_CT_Kiosk_" + tag, M,
                     notes="Small lightbox %.2f x %.2f m, 0.12 m deep (kiosks, the cold-room door, window signs, the stacked rail). "
                           "Face M_Sign_CT_Face 0..1. Pivot bottom-left of the face, face -Y." % (w, h))


def m_blade(ctx, M, hgt, w):
    """Double-sided vertical blade sign projecting from the wall: cabinet 0.25 thick, two faces, brackets top and bottom."""
    b = B(360 + int(hgt))
    off, t = 0.35, 0.25                                                                                   # gap to the wall, thickness
    y0, y1 = -off - w, -off
    bx(b, (-t / 2, y0, 0.0), (t / 2, y1, hgt), "trim", ch=0.008, axis="z")
    f = 0.035
    for s in (-1, 1):
        x = s * (t / 2 + 0.006)
        du = np.array([0, w, 0]) * s
        o = np.array([x, y0 if s > 0 else y1, 0.0])
        sg.card(b, o + np.array([0, 0, 0]), du, (0, 0, hgt), "face", 2, max(2, int(hgt / 0.5)))
        for lo, hi in (((x - 0.008, y0 - 0.004, -0.004), (x + 0.008, y1 + 0.004, f)), ((x - 0.008, y0 - 0.004, hgt - f), (x + 0.008, y1 + 0.004, hgt + 0.004)),
                       ((x - 0.008, y0 - 0.004, f), (x + 0.008, y0 + f, hgt - f)), ((x - 0.008, y1 - f, f), (x + 0.008, y1 + 0.004, hgt - f))):
            bx(b, lo, hi, "trim", ch=0.002)
    for z in (0.15, hgt - 0.20) + ((hgt / 2,) if hgt > 7 else ()):
        bx(b, (-0.10, -0.012, z - 0.15), (0.10, 0.0, z + 0.15), "black", ch=0.003)                       # wall plate
        bar(b, (0.0, -0.01, z), (0.0, y1 - 0.02, z), 0.05, 0.08, "black", ch=0.003)
        if z < hgt / 2:
            bar(b, (0.0, -0.01, z + 0.6), (0.0, y1 - 0.02, z + 0.05), 0.04, 0.04, "black", ch=0.003)        # kicker
    sg.whip(b, [(0.0, y1 + 0.02, hgt - 0.3), (0.05, -0.15, hgt - 0.35), (0.06, -0.02, hgt - 0.6)], "rubber", 0.010)
    return done_sign(ctx, b, "SM_Sign_CT_Blade_%dm" % int(hgt), M, expect_size=(None, None, hgt + 0.004),
                     notes="Double-sided blade %.0f x %.2f m, 0.25 m thick, 0.35 m off the wall on %d brackets: two faces on 0..1 UVs "
                           "(slot M_Sign_CT_Face, each reads correctly from its side; letters stacked in the atlas). Pivot at the wall "
                           "plane at the blade's bottom, blade out along -Y, faces +-X." % (hgt, w, 3 if hgt > 7 else 2))


def m_board(ctx, M, w, h, tag, hang=False):
    b = B(370 + int(w * 10))
    bx(b, (0.0, 0.002, 0.0), (w, 0.020, h), "wood", ch=0.003, axis="x")
    sg.card(b, (0, 0.0, 0), (w, 0, 0), (0, 0, h), "face", max(2, int(w / 0.5)), 1)
    mw = 0.025
    for lo, hi in (((-0.01, -0.016, -0.01), (w + 0.01, 0.004, mw)), ((-0.01, -0.016, h - mw), (w + 0.01, 0.004, h + 0.01)),
                   ((-0.01, -0.016, mw), (mw, 0.004, h - mw)), ((w - mw, -0.016, mw), (w + 0.01, 0.004, h - mw))):
        bx(b, lo, hi, "timber", ch=0.005, axis="x")
    if hang:
        for xx in (0.12, w - 0.12):
            rod(b, (xx, 0.01, h), (xx, 0.01, h + 0.60), 0.0035, "chrome", n=4)
            bx(b, (xx - 0.02, 0.0, h + 0.58), (xx + 0.02, 0.02, h + 0.62), "black", pin=False)
    nm = "SM_Sign_CT_" + tag
    return done_sign(ctx, b, nm, M,
                     notes="Painted board %.2f x %.2f m (18 mm ply with a moulding), face M_Sign_CT_Face 0..1, unlit (a nearby lamp lights "
                           "it). %s Pivot bottom-left of the face, face -Y." % (w, h, "Hangs on two wires 0.60 m long from its top "
                                                                                       "(market stall boards, above 2.4 m)." if hang else ""))


def m_poster(ctx, M, w, h, tag):
    b = B(380 + int(h * 10))
    sg.card(b, (0, 0.0, 0), (w, 0, 0), (0, 0, h), "face", 4, 4, lift=lambda s, t: 0.002 * np.sin(s * 9.0) * np.sin(t * 7.0))
    sg.card(b, (w, 0.0015, 0), (-w, 0, 0), (0, 0, h), "clothLight", 1, 1, sign=False)
    return done_sign(ctx, b, "SM_Sign_CT_Poster_" + tag, M,
                     notes="Paper poster %.2f x %.2f m pasted on a wall (face M_Sign_CT_Face 0..1, slightly wrinkled, unlit). Pivot "
                           "bottom-left, face -Y; place 2 mm off the wall." % (w, h))


def m_placard(ctx, M):
    b = B(390)
    w, h = 0.36, 0.24
    bx(b, (-0.04, 0.0, 0.0), (w + 0.04, 0.10, 0.012), "plastic", pin=False)                            # foot
    bar(b, (w / 2, 0.05, 0.012), (w / 2, 0.02, 0.06), 0.02, 0.01, "plastic")
    sg.card(b, (0.0, 0.015, 0.05), (w, 0, 0), (0, 0, h), "face", 1, 1)
    sg.card(b, (w, 0.017, 0.05), (-w, 0, 0), (0, 0, h), "clothLight", 1, 1, sign=False)
    return done_sign(ctx, b, "SM_Sign_CT_Placard", M,
                     notes="Price card 0.36 x 0.24 m in a plastic stand (vendor tables; marker on card, unlit). Face 0..1.")


def m_street_blade(ctx, M):
    b = B(391)
    w, h = 0.90, 0.20
    bx(b, (-w / 2, -0.003, -h / 2), (w / 2, 0.003, h / 2), "alu", pin=False)
    sg.card(b, (-w / 2, -0.004, -h / 2), (w, 0, 0), (0, 0, h), "face", 2, 1)
    sg.card(b, (w / 2, 0.004, -h / 2), (-w, 0, 0), (0, 0, h), "face", 2, 1)
    lathe(b, [(0.0, -h / 2 - 0.04), (0.045, -h / 2 - 0.04), (0.045, h / 2 + 0.04), (0.0, h / 2 + 0.04)], "alu", seg=10)
    return done_sign(ctx, b, "SM_Sign_CT_StreetBlade", M,
                     notes="Street name blade 0.90 x 0.20 m, two faces (green, retroreflective, plain: no agency mark), on a post clamp. "
                           "Pivot at the clamp centre, faces +-Y; mount on a SignPost or lamp post at 3.0 m.")


def m_arch(ctx, M):
    b = B(392)
    w, h, D = 4.0, 0.8, 0.22
    cabinet(b, w, h, D, slot="jade")
    for s in (0, 1):                                                                                     # scrolls at the ends
        x = -0.05 if s == 0 else w + 0.05
        geo_ = geo.torus(0.16, 0.035, 16, 6)
        geo.transform(geo_, loc=(x, D / 2, h / 2), rot=(90, 0, 0))
        b.absorb(geo_, "gold")
    lathe(b, [(0.0, h + 0.004), (0.10, h + 0.004), (0.06, h + 0.12), (0.0, h + 0.16)], "gold", seg=10)
    return done_sign(ctx, b, "SM_Sign_CT_Arch", M,
                     notes="The arcade's arch sign: a 4.0 x 0.8 m lightbox in jade-green enamel with gold scrolls and a finial, face 0..1 "
                           "(PLUM BLOSSOM ARCADE). Pivot bottom-left of the face, face -Y; one at each mouth (4.2 m wide).")


# ================================================================================================= neon and rooftop letters

NEON_HEX = {"#ff3d9a": "Pink", "#55ff8a": "Green", "#35e0ff": "Cyan", "#f6c21a": "Gold", "#ff3030": "Red"}


def m_neon(ctx, M, key, N):
    S = dict(w=N["w"], h=N["h"], tube=N["colour"], text=N["text"], font="heavy", cond=0.88, age=1.0)
    if N.get("sub"):
        S.update(cap=0.36 * N["h"], cy=0.34, sub=N["sub"], subcap=0.20 * N["h"], subcy=0.76)
    else:
        S.update(cap=0.52 * N["h"], cy=0.50)
    MM = dict(M)
    MM["sign" + key] = M["black"]
    b, D, _note = sg.neon_on_pan(ctx, MM, key, S, "neon")
    ob = b.finish(N["mesh"], MM, ctx.kit)
    fc.weather(ctx, b, ob, N["mesh"], ledges=[], ground=False)
    ctx.asset(ob, collision="none", slots=SLOT_META,
              notes="Exposed glass neon \"%s%s\" (%s tube MI_Neon_%s, 13 mm on 35 mm glass standoffs, electrode boots, a border tube) "
                    "on a painted steel pan %.1f x %.2f m, transformer on top. %s. Pivot bottom-left of the pan's face, face -Y. English "
                    "only." % (N["text"], (" / " + N["sub"]) if N.get("sub") else "", NEON_HEX[N["colour"]], NEON_HEX[N["colour"]],
                               N["w"], N["h"], N["where"]))
    ctx.K[N["mesh"]] = ob
    return ob


def m_rooftop_letters(ctx, M):
    """GOLDEN TIDE MARKET in open-face pan letters with gold neon, on a steel frame standing on the market's north parapet."""
    w, h = 12.0, 1.5
    S = dict(w=w, h=h, tube="#f6c21a", text="GOLDEN TIDE MARKET", font="heavy", cap=1.0, cy=0.5, cond=0.84, age=1.0)
    lb, D, _n = sg.pan_letters(ctx, M, "RooftopLetters", S)
    b = B(395)
    fc.sub(b, lb, 0.0, (0.0, 0.0, 1.6))
    for x in np.arange(0.4, w, 2.0):
        bar(b, (x, D + 0.10, 0.0), (x, D + 0.10, 1.6 + h), 0.08, 0.08, "black", ch=0.004)
        bar(b, (x, D + 0.10, 1.2), (x, D + 1.30, 0.0), 0.06, 0.06, "black", ch=0.004)
        bx(b, (x - 0.15, D - 0.05, -0.02), (x + 0.15, D + 1.45, 0.0), "black", pin=False)
    for z in (1.55, 1.6 + h * 0.5, 1.6 + h - 0.05):
        bar(b, (0.2, D + 0.10, z), (w - 0.2, D + 0.10, z), 0.06, 0.06, "black", ch=0.004)
    ob = b.finish("SM_Sign_CT_RooftopFrame", M, ctx.kit)
    fc.weather(ctx, b, ob, "SM_Sign_CT_RooftopFrame", ledges=[], ground=False)
    ctx.asset(ob, collision="none", slots=SLOT_META, cover_height=None,
              notes="The market's rooftop letters GOLDEN TIDE MARKET: open-face pan letters 1.0 m caps with gold neon inside, on a "
                    "steel frame (posts every 2 m, kickers, rails) standing on the north parapet, letters from 1.6 m to 3.1 m above "
                    "the roof. The landmark seen from Canal. Pivot at the left end of the frame's front line on the roof (y 5.7 web), "
                    "letters face -Y. The frame legs are cover on the roof (the level's colliders). One stroke may flicker.")
    ctx.K["SM_Sign_CT_RooftopFrame"] = ob
    return ob


def build_front(ctx, M):
    from assets import _chinatown_names as names
    out = []
    for n in SHOPFRONTS:
        out.append(m_shopfront(ctx, M, n))
    out.append(m_fascia(ctx, M))
    out.append(m_grille(ctx, M))
    out.append(m_sign_rail(ctx, M))
    for L, slot in ((3.0, "fabricGreen"), (4.0, "fabricGreen"), (6.0, "fabricGreen")):
        out.append(m_box_awning(ctx, M, L, slot))
    for w in (6, 8, 10):
        out.append(m_band(ctx, M, w))
    out.append(m_kiosk(ctx, M, 1.2, 0.35, "1m"))
    out.append(m_kiosk(ctx, M, 3.0, 0.6, "3m"))
    out.append(m_blade(ctx, M, 4.0, 0.8))
    out.append(m_blade(ctx, M, 6.0, 0.9))
    out.append(m_blade(ctx, M, 12.0, 1.1))
    out.append(m_board(ctx, M, 2.4, 0.5, "Board"))
    out.append(m_board(ctx, M, 1.6, 0.42, "StallBoard", hang=True))
    out.append(m_poster(ctx, M, 0.6, 0.42, "A"))
    out.append(m_poster(ctx, M, 0.6, 0.9, "B"))
    out.append(m_placard(ctx, M))
    out.append(m_street_blade(ctx, M))
    out.append(m_arch(ctx, M))
    for key, N in names.NEON.items():
        out.append(m_neon(ctx, M, key, N))
    out.append(m_rooftop_letters(ctx, M))
    return out
