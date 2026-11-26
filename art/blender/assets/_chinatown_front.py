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
from assets._chinatown_kit import SLOT_META, absorb, bar, bx, done, lathe, rod
from assets.facade import BAND0, BULK, DOOR_W, HEAD, B, sheet
from mi import geo


class thick_members:
    """While the Block's own door and glazing helpers draw a CT shop front, their rods and boxes go through the Canal
    kit's flicker floor (members over 0.6 m at least 36 mm across). facade.py itself is not changed, so the Block's
    outputs stay byte for byte."""

    def __enter__(self):
        from assets import _chinatown_kit as kit
        self.saved = (fc.rod, fc.bx)
        fc.rod, fc.bx = kit.rod_floor, kit.bx_floor
        return self

    def __exit__(self, *a):
        fc.rod, fc.bx = self.saved

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

def gate_down(b, x0, x1, z1, hood=0.30):
    """A roll gate shut, light enough for a whole street of them: a corrugated curtain (three points a slat, flat along the run),
    guide rails, the hood box, a bottom bar with two padlocked hasps."""
    zc = z1 - hood + 0.03
    n = int(round(zc / 0.075))
    pitch = zc / n
    prof = [(0.045, 0.0)]
    for i in range(n):
        prof += [(0.058, (i + 0.0) * pitch), (0.078, (i + 0.5) * pitch)]
    prof += [(0.058, zc), (0.045, zc)]
    for px in (x0, x1 - 0.10):
        bx(b, (px, -0.115, 0), (px + 0.10, 0, zc), "trim", ch=0.004, axis="z", pin=False)
    b.prism(prof, (x0 + 0.06, 0, 0), -Y, Z, (x1 - x0 - 0.12, 0, 0), "grey", step=2.0, pstep=9.0)
    bx(b, (x0 + 0.10, -0.125, 0.004), (x1 - 0.10, -0.045, 0.016), "grey", ch=0.003, axis="x", pin=False)
    for hx in (x0 + 0.42, x1 - 0.42):
        bx(b, (hx - 0.06, -0.090, 0.087), (hx + 0.06, -0.078, 0.143), "trim", ch=0.002, axis="x", pin=False)
        bx(b, (hx - 0.024, -0.124, 0.053), (hx + 0.024, -0.100, 0.101), "chrome", ch=0.004, axis="x", pin=False)
        b.leaks.append((hx, -0.09, 0.115))
    bx(b, (x0, -0.27, z1 - hood), (x1, 0, z1), "grey", ch=0.006, axis="x", pin=False)
    b.leaks += [(x0 + 0.04, -0.27, z1 - hood), (x1 - 0.04, -0.27, z1 - hood)]


def gate_up(b, x0, x1, z1, hood=0.30):
    """A roll gate rolled up: the hood box over the opening and the two guide rails."""
    for px in (x0, x1 - 0.10):
        bx(b, (px, -0.115, 0), (px + 0.10, 0, z1 - hood + 0.03), "trim", ch=0.004, axis="z", pin=False)
    bx(b, (x0, -0.27, z1 - hood), (x1, 0, z1), "grey", ch=0.006, axis="x", pin=False)
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
    # MOON GATE BAKERY's Canal front (W3, x 0.4..7.6): display windows both sides of the 2.0 m doorway at x 2..4 of the level
    # (lane D's opening), the glazed leaves folded open inside so the Goon door stays clear
    "Bakery": (7.2, 3.6, "tile", "the bakery's front: display windows either side of a 2.0 m doorway held open"),
}


def m_shopfront(ctx, M, name):
    c, d0, bulk, what = SHOPFRONTS[name]
    b = B(300 + len(name), step=0.25)
    rng = ctx.rng("ctshop", name)
    lit = dict(M, interior=M["interiorLit"])
    if name == "Shut":
        gate_down(b, 0.0, c, BAND0)
        coll = "box"
    elif name == "Bakery":
        gate_up(b, 0.0, c, BAND0)
        dw, hd = 2.0, HEAD - 0.32
        with thick_members():
            fc.glazing(b, 0.0, d0, hd, bulk)
            fc.glazing(b, d0 + dw, c, hd, bulk)
        bx(b, (d0, -0.09, 0.0), (d0 + dw, 0.40, 0.02), "conc", ch=0.004, axis="x")                         # threshold
        for xa in (d0, d0 + dw - 0.05):                                                                    # jambs and head
            bx(b, (xa, -0.075, 0.02), (xa + 0.05, 0.40, hd), "trim", axis="z", pin=False)
        bx(b, (d0, -0.075, hd), (d0 + dw, 0.40, hd + 0.08), "trim", axis="x", pin=False)
        bx(b, (d0 + 0.05, -0.04, hd + 0.08), (d0 + dw - 0.05, -0.03, BAND0 - 0.30), "glass", axis="x")         # transom
        bx(b, (0, -0.12, hd), (d0, 0.02, BAND0 - 0.30), "trim", ch=0.004, axis="x", pin=False)
        bx(b, (d0 + dw, -0.12, hd), (c, 0.02, BAND0 - 0.30), "trim", ch=0.004, axis="x", pin=False)
        for xa, sgn in ((d0 + 0.05, 1), (d0 + dw - 0.05, -1)):                                            # leaves folded in
            x0_, x1_ = (xa, xa + 0.05) if sgn > 0 else (xa - 0.05, xa)
            bx(b, (x0_, 0.40, 0.03), (x1_, 1.40, hd - 0.02), "alu", axis="y", pin=False)
            bx(b, (x0_ + 0.01 * sgn, 0.46, 0.30), (x1_ + 0.01 * sgn, 1.34, hd - 0.10), "glass", axis="y")
        bx(b, (0.40, 1.40, 0.0), (c - 0.40, 1.44, hd), "interior", pin=False)                               # the lit shop
        coll = "complex"
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
            with thick_members():
                fc.glazing(b, 0.0, d0, HEAD - 0.32, bulk)
        if c - d0 - DOOR_W > 0.05:
            with thick_members():
                fc.glazing(b, d0 + DOOR_W, c, HEAD - 0.32, bulk)
        with thick_members():
            fc.shop_door(b, d0, HEAD - 0.32)
        bx(b, (0, -0.12, HEAD - 0.32), (c, 0.02, BAND0 - 0.30), "trim", ch=0.004, axis="x", pin=False)
        if name == "Restaurant":                                                                             # roast-meat rail
            rod(b, (d0 + DOOR_W + 0.15, 0.25, 1.95), (c - 0.15, 0.25, 1.95), 0.012, "chrome", n=6)
            for xx in np.arange(d0 + DOOR_W + 0.30, c - 0.2, 0.32):
                rod(b, (xx, 0.25, 1.95), (xx, 0.25, 1.80), 0.003, "chrome", n=4)
        if name == "Jewelry":                                                                                # bars inside the glass
            for a, e in ((0.0, d0), (d0 + DOOR_W, c)):
                for xx in np.arange(a + 0.10, e - 0.05, 0.14):
                    rod(b, (xx, 0.05, BULK + 0.02), (xx, 0.05, HEAD - 0.34), 0.008, "chrome", n=4)
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
    b = B(321, step=0.4)
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
                      "name is on its sign), closed ends, welded frame. Pivot at the left end of the fixing line on the wall; on Canal it "
                      "is fixed at 2.35 m so its top clears the sign band (placements). Slot %s; the cloth tint is per shop in its MI." % (length, M[slot].name))


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

NEON_HEX = {"#ff3d9a": "Pink", "#55ff8a": "Green", "#35e0ff": "Cyan", "#f6c21a": "Gold", "#ff3030": "Red", "#f4f8ff": "White"}


def neon_text(b, text, font, cap, w, h, cy, slot, r, y, max_w, step=None, seg=6, stand=0.5, back=0.0, inset=0.0):
    """Glass tube along the letter outlines of one line (lighter than signs.neon_line: a coarser resample, 6-sided tube,
    a standoff every `stand` metres). Returns (loops, fill, ink_left)."""
    loops, fillm, ink_left, sc = sg.layout_line(text, font, cap, 0.88, 0.04, w, h, cy, max_w, step=step or max(0.02, cap * 0.12))
    for P in loops:
        Q = P + sg.ink_normals(P, ink_left) * inset if inset else P
        sg.tube(b, sg.to3(Q, y), r, slot, seg=seg)
        L = np.sum(np.linalg.norm(np.diff(np.vstack([Q, Q[:1]]), axis=0), axis=1))
        for i in np.linspace(0, len(Q), max(2, int(L / stand)), endpoint=False).astype(int):
            sg.cyl(b, (Q[i, 0], y + r * 0.8, Q[i, 1]), (Q[i, 0], back, Q[i, 1]), 0.0045, "standoff", seg=4)
        i0 = int(np.argmin(Q[:, 1] + 0.001 * Q[:, 0]))
        q = Q[(i0 + 2) % len(Q)]
        sg.cyl(b, (q[0], y, q[1]), (q[0], back, q[1]), r * 1.55, "rubber", seg=6)
    return loops, fillm, ink_left


def m_neon(ctx, M, key, N):
    """Exposed neon on a painted pan: tube letters, a border tube, transformer box on top."""
    w, h = N["w"], N["h"]
    b = B(400 + len(key), step=0.5)
    col = "neon" + NEON_HEX[N["colour"]]
    bx(b, (0, 0.003, 0), (w, 0.07, h), "black", ch=0.004, axis="x")
    r, yt = 0.0065, -0.0415
    mx = w - 0.32 * h
    if N.get("sub"):
        neon_text(b, N["text"], "heavy", 0.36 * h, w, h, 0.34, col, r, yt, mx)
        neon_text(b, N["sub"], "medium", 0.20 * h, w, h, 0.76, col, 0.0045, yt + 0.002, mx)
    else:
        neon_text(b, N["text"], "heavy", 0.52 * h, w, h, 0.50, col, r, yt, mx)
    bt = sg.rounded_rect(0.09 * h, 0.09 * h, w - 0.09 * h, h - 0.09 * h, 0.14 * h, 0.05)
    sg.tube(b, sg.to3(bt, yt), r, col, seg=6)
    for i in np.linspace(0, len(bt), 10, endpoint=False).astype(int):
        sg.cyl(b, (bt[i, 0], yt + r * 0.8, bt[i, 1]), (bt[i, 0], 0.0, bt[i, 1]), 0.0045, "standoff", seg=4)
    bx(b, (w - 0.62, 0.01, h + 0.002), (w - 0.30, 0.13, h + 0.11), "grey", ch=0.004)
    sg.whip(b, [(w - 0.46, 0.07, h + 0.11), (w - 0.46, 0.08, h + 0.20), (w - 0.40, 0.09, h + 0.24), (w - 0.36, 0.12, h + 0.20)],
            "rubber", 0.008)
    ob = b.finish(N["mesh"], M, ctx.kit)
    fc.weather(ctx, b, ob, N["mesh"], ledges=[], ground=False)
    ctx.asset(ob, collision="none", slots=SLOT_META,
              notes="Exposed glass neon \"%s%s\" (MI_Neon_%s: 13 mm tube on glass standoffs, electrode boots, a border tube) on a "
                    "painted steel pan %.1f x %.2f m, transformer on top. %s. Pivot bottom-left of the pan's face, face -Y. English "
                    "only." % (N["text"], (" / " + N["sub"]) if N.get("sub") else "", NEON_HEX[N["colour"]], w, h, N["where"]))
    ctx.K[N["mesh"]] = ob
    return ob


def rooftop_legs():
    from assets._chinatown_front_pure import rooftop_legs as f
    return f()


def m_rooftop_letters(ctx, M):
    """GOLDEN TIDE MARKET in open-face pan letters with gold neon inside, on a steel frame standing on the four legs lane D
    placed on the market's north parapet (market.letters.leg colliders): the frame runs the legs' full span, the letters
    are centred on it, every leg of the art inside its collider, no kicker on the roof (the legs clamp to the parapet)."""
    w, h, Dl, t = 12.0, 1.5, 0.11, 0.004
    z0 = 1.6
    x_e, xs, _yc = rooftop_legs()
    Lf = x_e - (min(xs) - 0.15)                                  # the frame's length, east end to west end
    legs = sorted(x_e - x for x in xs)                           # local x of each leg (the frame faces north: local x runs west)
    x_l = Lf / 2 - w / 2
    b = B(395, step=0.6)      # coarse wear grid on the long rails and the letter backs
    # outlines resampled every 0.10 m and a 4-sided tube: 12k triangles at most (chinatown.md 13.2, sign carriers 2-12k)
    loops, (FV, FF), ink_left, sc = sg.layout_line("GOLDEN TIDE MARKET", "heavy", 1.0, 0.84, 0.06, w, h, 0.5, w - 0.4, step=0.10)
    lift = lambda P: P + np.array([x_l, z0])
    for P in loops:
        Ni = sg.ink_normals(P, ink_left)
        Nout = np.column_stack([-Ni[:, 0], np.zeros(len(P)), -Ni[:, 1]])
        sg.strip(b, sg.to3(lift(P), 0.0), sg.to3(lift(P), Dl), "trim", Nout)
        # (the return's 4 mm inner wall and lip are never seen from the street: not modelled)
        Q = lift(P + Ni * 0.03)
        sg.tube(b, sg.to3(Q, 0.05), 0.0065, "neonGold", seg=4)
    FV2 = np.asarray(FV) + np.array([x_l, z0])
    sg.fill(b, FV2, FF, Dl - t, "black", front=True)
    sg.fill(b, FV2, FF, Dl, "trim", front=False)
    D = Dl
    for x in legs:
        bar(b, (x, D + 0.10, 0.0), (x, D + 0.10, z0 + h), 0.10, 0.10, "black", ch=0.004)
        bx(b, (x - 0.14, D - 0.04, -0.012), (x + 0.14, D + 0.24, 0.0), "black", pin=False)                  # base plate
        bx(b, (x - 0.08, D + 0.04, 0.70), (x + 0.08, D + 0.16, 1.10), "black", pin=False)                   # parapet clamp
    for z in (z0 - 0.05, z0 + h * 0.5, z0 + h - 0.05):
        bar(b, (0.05, D + 0.10, z), (Lf - 0.05, D + 0.10, z), 0.06, 0.06, "black", ch=0.004)
    for x in np.arange(x_l + 1.0, x_l + w, 2.0):                                                            # letter hangers
        bar(b, (x, D + 0.02, z0 - 0.05), (x, D + 0.02, z0 + h - 0.05), 0.04, 0.04, "black", ch=0.003)
    ob = b.finish("SM_Sign_CT_RooftopFrame", M, ctx.kit)
    fc.weather(ctx, b, ob, "SM_Sign_CT_RooftopFrame", ledges=[], ground=False)
    ctx.asset(ob, collision="none", slots=SLOT_META, cover_height=None,
              notes="The market's rooftop letters GOLDEN TIDE MARKET: open-face pan letters (1.0 m caps, 110 mm returns) with gold "
                    "neon inside, 12 m long, centred on a %.2f m steel frame of three rails on the four 100 mm legs lane D placed "
                    "(market.letters.leg: local x %s), each with a base plate and a clamp to the parapet, no kicker on the roof; "
                    "letters from 1.6 to 3.1 m above the roof. The landmark seen from Canal. Pivot at the frame's east end on the "
                    "letters' face line on the roof (web y 5.7); placed at yaw 180 the letters face north. One stroke may flicker "
                    "(chinatown.md 11.3)." % (Lf, [round(v, 2) for v in legs]))
    ctx.K["SM_Sign_CT_RooftopFrame"] = ob
    return ob


def m_ct_widths(ctx, M):
    """The north row's modules at the widths its own buildings need (_chinatown_place.needed_widths()): end piers, upper
    fills, parapet fills, cornice ends and fascias. The Block's kit has a few fixed widths and the first placements
    stretched them up to 5 times along their run, so the brick stretched with them (the tiling UVs are in metres); these
    are built with the Block's own parts and materials at the exact width, so every brick is the scan's size. facade.py
    is not changed (its outputs stay byte for byte)."""
    from assets import _chinatown_place as place
    need = place.needed_widths()
    Mb = fc.materials(ctx)
    Mx = dict(M)
    Mx.update({k: v for k, v in Mb.items() if k.startswith("brick") or k in ("stone", "grey")})
    out = []
    cm = place.cm
    for k, w in need["pier"]:
        b = fc.B(11)
        fc.bx(b, (0, -fc.PIER_OUT, 0), (w, fc.T, fc.GROUND), "brick", ch=0.006, axis="z")
        fc.bx(b, (0, -fc.PIER_OUT - 0.025, 0), (w, 0.0, 0.24), "stone", ch=0.010, axis="x")
        out.append(fc.done(ctx, b, "SM_Facade_CT_Pier_%s_%s" % (k, cm(w)), Mx, k, wear=dict(ground=True), collision="box",
                           expect_size=(w, None, fc.GROUND),
                           notes="Canal shop-front end pier %.2f m wide (the Block's pier at this building's width: no scaling)." % w))
    for k, w in need["fill"]:
        b = fc.B(43)
        fc.bx(b, (0, 0, 0), (w, fc.T, fc.STOREY), "brick", axis="z")
        out.append(fc.done(ctx, b, "SM_Facade_CT_Fill_%s_%s" % (k, cm(w)), Mx, k, collision="box", expect_size=(w, fc.T, fc.STOREY),
                           notes="Plain brick end pier of an upper storey, %.2f m (built at the width, not scaled)." % w))
    for k, w in need["parapet"]:
        b = fc.B(43)
        fc.parapet_parts(b, w)
        out.append(fc.done(ctx, b, "SM_Facade_CT_ParapetFill_%s_%s" % (k, cm(w)), Mx, k,
                           wear=dict(ledges=[(-1.0, w + 1.0, 0.90, 0.9)]), collision="box", expect_size=(w, 0.38, 0.97),
                           notes="Parapet over an end pier, %.2f m (built at the width, not scaled)." % w))
    for w in need["cornice"]:
        for end in ("L", "R"):
            b = fc.B(51)
            fc.cornice_parts(b, w, end)
            out.append(fc.done(ctx, b, "SM_Facade_CT_CorniceEnd_%s_%s" % (end, cm(w)), Mx, expect_size=(w, None, None),
                               notes="Pressed-metal cornice end piece %.2f m (%s) with console, built at the width." % (w, end)))
    for w in need["fascia"]:
        b = B(319, step=0.5)
        bx(b, (0.0, -0.06, 0.0), (w, 0.30, 0.88), "trim", axis="x", pin=False)
        bx(b, (0.0, -0.075, 0.02), (w, -0.06, 0.86), "trim", ch=0.002, axis="x", pin=False)
        fc.belt(b, 0.0, w, 0.70)
        out.append(done(ctx, b, "SM_Facade_CT_Fascia_" + cm(w), M, ground=False, collision="box", expect_size=(w, None, None),
                        ledges=[(0.0, w, 0.70, 0.6)],
                        notes="Fascia strip over a %.1f m Canal shop front (2.77 to 3.65 m), built at the width." % w))
    return out


# ================================================================================================= round 2: the other buildings

ALCOVE_W, ALCOVE_OPEN, ALCOVE_D, ALCOVE_HEAD = 2.8, 2.4, 1.0, 2.85   # module, opening, depth to the back wall, soffit (web 3.0)


def m_alcove(ctx, Mb, k):
    """A north-row shop alcove as lane D cut it (N*.front gaps 2.4 m, 1.0 m deep, lintel at web y 3.0): a real recess with
    brick reveals, a concrete soffit at 2.85 m over the sidewalk, the residents' door in the back wall, a bell panel and
    mailboxes on the reveals, a lamp in the soffit. 2.8 m wide (0.2 m piers each side), pivot at the bottom-left of the outer
    face on the sidewalk, as the Block's ResEntry it replaces."""
    b = fc.B(23 + len(k))
    w, o, d, hd = ALCOVE_W, ALCOVE_OPEN, ALCOVE_D, ALCOVE_HEAD
    x0, x1 = (w - o) / 2, (w + o) / 2
    T = fc.T
    fc.bx(b, (0.0, -fc.PIER_OUT, 0.0), (x0, d + T, fc.GROUND), "brick", axis="z")                       # reveals
    fc.bx(b, (x1, -fc.PIER_OUT, 0.0), (w, d + T, fc.GROUND), "brick", axis="z")
    fc.bx(b, (x0, -fc.PIER_OUT, hd), (x1, T, fc.GROUND), "brick", axis="x")                              # head over the recess
    fc.bx(b, (x0 - 0.10, -fc.PIER_OUT - 0.02, hd), (x1 + 0.10, -fc.PIER_OUT, hd + 0.20), "stone", ch=0.006, axis="x")
    fc.bx(b, (x0, T, hd), (x1, d, hd + 0.10), "conc", axis="x")                                         # soffit
    dx0, dx1, dh = w / 2 - 0.50, w / 2 + 0.50, 2.30                                                     # the back wall and door
    fc.bx(b, (x0, d, 0.0), (dx0, d + T, hd), "brick", axis="z")
    fc.bx(b, (dx1, d, 0.0), (x1, d + T, hd), "brick", axis="z")
    fc.bx(b, (dx0, d, dh + 0.06), (dx1, d + T, hd), "brick", axis="x")
    kw = dict(ch=0.004, pin=False)
    for xa in (dx0, dx1 - 0.06):
        fc.bx(b, (xa, d + 0.02, 0.0), (xa + 0.06, d + 0.12, dh + 0.06), "door", axis="z", **kw)
    fc.bx(b, (dx0 + 0.06, d + 0.02, dh), (dx1 - 0.06, d + 0.12, dh + 0.06), "door", axis="x", **kw)
    fc.bx(b, (dx0 + 0.065, d + 0.08, 0.01), (dx1 - 0.065, d + 0.12, dh - 0.005), "door", axis="z", **kw)
    for pz0, pz1 in ((0.30, 1.00), (1.15, 2.15)):
        fc.bx(b, (dx0 + 0.16, d + 0.066, pz0), (dx1 - 0.16, d + 0.08, pz1), "door", ch=0.008, axis="z", pin=False)
    fc.rod(b, (dx1 - 0.14, d + 0.08, 1.05), (dx1 - 0.14, d + 0.03, 1.05), 0.022, "chrome", n=10)
    fc.bx(b, (dx0 + 0.06, d + 0.10, 2.42), (dx1 - 0.06, d + 0.11, hd - 0.05), "glasswin", axis="x")       # transom light
    fc.bx(b, (x1 - 0.012, 0.42, 1.20), (x1, 0.56, 1.58), "alu", ch=0.002, axis="z", pin=False)          # bell panel
    fc.bx(b, (x0, 0.30, 1.05), (x0 + 0.025, 0.86, 1.55), "chrome", ch=0.002, axis="y", pin=False)       # mailboxes
    fc.bx(b, (x0, 0.0, -0.01), (x1, d, 0.0), "tile", axis="x")                                         # a tiled floor
    fc.bx(b, (w / 2 - 0.12, d / 2 - 0.12, hd - 0.05), (w / 2 + 0.12, d / 2 + 0.12, hd), "alu", ch=0.004, pin=False)
    fc.belt(b, 0.0, w, 3.51)
    name = "SM_Facade_CT_Alcove_" + k
    return fc.done(ctx, b, name, Mb, k, wear=dict(ground=True, ledges=[(0.0, w, 3.51, 0.8), (x0 - 0.1, x1 + 0.1, hd, 0.6)]),
                   collision="complex", expect_size=(w, None, None),
                   notes="Canal north-row shop alcove (chinatown.md 4.1; lane D's N*.front gap and lintel): a real 2.4 x 1.0 m "
                         "recess, brick reveals, soffit at 2.85 m over the sidewalk (web y 3.0), the residents' door 1.0 m in the "
                         "back wall with a transom, bell panel and mailboxes on the reveals, a soffit lamp, belt course. 2.8 m "
                         "wide with 0.2 m piers; pivot bottom-left of the outer face on the sidewalk (replaces SM_Facade_ResEntry_Red).")


GROUND_KINDS = ("GroundWall", "GroundDoor", "GroundWindow")


def m_ground(ctx, Mb, kind, k):
    """A 3.1 m ground-storey bay for a building's back or side wall (no shop): plain brick on a concrete base course, a
    steel back door under a hooded lamp, or a small barred window high in the wall. Flush with the upper bays (wall plane
    at y = 0, 0.30 thick behind)."""
    b = fc.B(60 + GROUND_KINDS.index(kind) * 7 + len(k))
    w, H, T = fc.BAY, fc.GROUND, fc.T
    if kind == "GroundWall":
        fc.bx(b, (0.0, 0.0, 0.30), (w, T, H), "brick", axis="z")
    elif kind == "GroundDoor":
        x0, x1, dh = 1.05, 2.05, 2.15
        fc.wall_opening(b, w, H, x0, x1, 0.30, dh + 0.06)
        fc.bx(b, (x0, 0.0, 0.0), (x1, T, 0.30), "conc", axis="x")
        fc.bx(b, (x0 - 0.06, -0.012, 0.30), (x0, 0.06, dh + 0.06), "black", axis="z", pin=False)
        fc.bx(b, (x1, -0.012, 0.30), (x1 + 0.06, 0.06, dh + 0.06), "black", axis="z", pin=False)
        fc.bx(b, (x0 - 0.06, -0.012, dh + 0.06), (x1 + 0.06, 0.06, dh + 0.14), "black", axis="x", pin=False)
        fc.bx(b, (x0, 0.06, 0.30), (x1, 0.10, dh + 0.06), "trim", axis="z", pin=False)                     # the steel leaf
        fc.rod(b, (x1 - 0.12, 0.06, 1.25), (x1 - 0.12, 0.01, 1.25), 0.018, "chrome", n=8)
        fc.bx(b, (w / 2 - 0.16, -0.20, dh + 0.30), (w / 2 + 0.16, 0.0, dh + 0.42), "black", ch=0.004, pin=False)   # hood lamp
        fc.bx(b, (w / 2 - 0.10, -0.17, dh + 0.27), (w / 2 + 0.10, -0.03, dh + 0.30), "bulb", pin=False)
        fc.bx(b, (2.35, -0.015, 2.45), (2.85, 0.0, 2.85), "galv", ch=0.002, pin=False)                       # vent grille
    else:
        x0, x1, z0, z1 = 1.10, 2.00, 1.95, 2.50
        fc.wall_opening(b, w, H, x0, x1, z0, z1)
        fc.bx(b, (0.0, 0.0, 0.0), (w, T, 0.30), "conc", axis="x")
        fc.bx(b, (x0, T - 0.012, z0), (x1, T, z1), "interior", axis="z")
        fc.bx(b, (x0, 0.10, z0), (x1, 0.11, z1), "glasswin", axis="z")
        for xx in np.arange(x0 + 0.10, x1 - 0.05, 0.11):
            fc.rod(b, (xx, 0.03, z0), (xx, 0.03, z1), 0.008, "black", n=6)
        fc.sill(b, x0, x1, z0)
    if kind == "GroundWall":
        fc.bx(b, (0.0, -0.015, 0.0), (w, T, 0.30), "conc", axis="x")
    name = "SM_Facade_CT_%s_%s" % (kind, k)
    return fc.done(ctx, b, name, Mb, k, wear=dict(ground=True, fade=(w, H)), collision="box", expect_size=(w, None, H),
                   notes="Back or side wall ground bay 3.1 x 3.65 m in %s brick for the alleys and side streets (no shop): %s." % (
                       k, {"GroundWall": "plain brick on a concrete base course",
                           "GroundDoor": "a 1.0 m steel back door in a frame under a hooded lamp, a vent grille",
                           "GroundWindow": "a small barred window high in the wall"}[kind]))


def m_ct_bay(ctx, Mb, k):
    """The Block's upper bay with a window, in a brick the Block's kit has only as a blank bay (Common): the same parts."""
    b = fc.B(41)
    BAY, ST = fc.BAY, fc.STOREY
    x0, x1, z0, z1, lint = (BAY - fc.WIN_W) / 2, (BAY + fc.WIN_W) / 2, fc.WIN_SILL, fc.WIN_SILL + fc.WIN_H, 0.203
    fc.wall_opening(b, BAY, ST, x0, x1, z0 - 0.10, z1 + lint)
    fc.sill(b, x0, x1, z0)
    fc.bx(b, (x0 - 0.15, -0.012, z1), (x1 + 0.15, fc.T, z1 + lint), "stone", ch=0.006, axis="x")
    fc.sash_window(b, x0, x1, z0, z1)
    fc.bx(b, (x0 - 0.02, fc.T - 0.012, z0 - 0.02), (x1 + 0.02, fc.T - 0.002, z1 + 0.02), "interior", axis="z")
    return fc.done(ctx, b, "SM_Facade_CT_BayWindow_" + k, Mb, k, wear=dict(ledges=[(x0 - 0.10, x1 + 0.10, z0 - 0.10, 1.0)], fade=(BAY, ST)),
                   collision="box", expect_size=(BAY, None, ST),
                   notes="Upper-storey bay 3.1 x 3.1 m in %s brick, the Block's window bay parts (backs and side walls of Canal "
                         "Street's buildings)." % k)


def m_head(ctx, Mb, k, w, h):
    """A brick panel over an opening at its own size (no scaling): the head over the arcade mouths and the workshop door."""
    b = fc.B(81)
    fc.bx(b, (0.0, 0.0, 0.0), (w, fc.T, h), "brick", axis="x")
    fc.bx(b, (-0.02, -0.03, 0.0), (w + 0.02, fc.T, 0.18), "stone", ch=0.006, axis="x")
    from assets import _chinatown_place as place
    name = "SM_Facade_CT_Head_%s_%sx%s" % (k, place.cm(w), place.cm(h))
    return fc.done(ctx, b, name, Mb, k, wear=dict(ledges=[(0.0, w, h, 0.6)], fade=(w, h)), collision="box", expect_size=(w, None, h),
                   notes="Brick head %.2f x %.2f m over an opening (cast-stone soffit band), built at its size." % (w, h))


def build_round2(ctx, M):
    """The modules the round-2 placements need (_chinatown_place.needed_round2())."""
    from assets import _chinatown_place as place
    need = place.needed_round2()
    Mb = dict(fc.materials(ctx))
    for key in ("bulb", "galv"):                       # the Canal kit's lamp and galvanised slots
        Mb[key] = M[key]
    out = []
    for k in need["alcove"]:
        out.append(m_alcove(ctx, Mb, k))
    for kind, k in need["ground"]:
        out.append(m_ground(ctx, Mb, kind, k))
    for k in need["bay"]:
        out.append(m_ct_bay(ctx, Mb, k))
    for k, w, h in need["head"]:
        out.append(m_head(ctx, Mb, k, w, h))
    return out


def build_front(ctx, M):
    from assets import _chinatown_names as names
    out = []
    for n in SHOPFRONTS:
        out.append(m_shopfront(ctx, M, n))
    out.append(m_fascia(ctx, M))
    out += m_ct_widths(ctx, M)
    out += build_round2(ctx, M)
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
