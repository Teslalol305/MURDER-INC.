"""Midtown kit, part 5 (round 3): the rooftop bar THE LOFTLARK, the roof boxes that had no art, and the plaza's small dressing.

Everything here is fitted to a collider of tools/levels/data/level_midtown.json (assets/_midtown_place.py): the mesh is
authored at the size of the data's box (its "core"), so the fit stretches by a few percent at most, and every member within
reach of the path is 6 cm across or more (the thin check of _midtown_check.py).

    roof (THE LOFTLARK, midtown.md 9.1 and 10)  SM_Roof_Lounge_Bar, SM_Roof_Lounger, SM_Roof_Lounger_Stack,
        SM_Roof_Umbrella_Folded, SM_Roof_PlanterBox, SM_Roof_Loftlark_Neon_4m (the neon, unlit: the lounge is closed),
        SM_Roof_LoungeDeck_9x7 (the raised timber deck of D, 0.6 m, a 0.3 m step on its open sides)
    roof boxes with no art  SM_Roof_DuctBox_1p6, SM_Roof_VentBox_1x1, SM_Roof_ConduitBox_1p4, SM_Roof_ConduitRun_4m,
        SM_Roof_PipeSleepers_1p6, SM_Roof_FanHousing_1p6, SM_Roof_DunnageDeck_6x6 (E's steel dunnage platform)
    plaza small dressing  SM_Sq_BollardPlanter, SM_Sq_Newsstand, SM_Sq_PhoneKiosk, SM_Sq_WayfindingPylon, SM_Sq_ATM_Kiosk,
        SM_Sq_Standpipe, SM_Sq_ValetStand, SM_Sq_LuggageCart, SM_Sq_Crates_Stack, SM_Sq_Hoarding_6m, SM_Sq_Sawhorse,
        SM_Sq_FanSign, SM_Sq_TrashCan (replaces the Block's wire basket on the Midtown placements)
Reused from the Block's kits (placed, not rebuilt): SM_Prop_CT_Hydrant, SM_Furn_SignPost, SM_Furn_NewspaperBox,
SM_Furn_TrashBags_A / _B, SM_Furn_BusShelter.

Pivots: centre of the footprint on the ground (or on the roof / deck it stands on), the front (the side people use) toward -Y.
The art has no collision: the level data decides.
"""
import math

import numpy as np

from assets import _midtown_roof as R
from assets import _midtown_square as SQ
from assets import signs as sg
from assets.facade import B, bx, rod, sheet
from mi import geo, mat, steel

X, Y, Z = np.eye(3)
done, quad, tube, short_rod = SQ.done, SQ.quad, SQ.tube, SQ.short_rod


def materials(ctx, M):
    """The slots rounds 3 adds: vehicle and tent paints (tints of the clean paint and canvas sets), brass, tinted glass, the
    marquee bulbs, the LOFTLARK's neon, the window-grid facade slot, hoarding plywood. No new tiling set."""
    S, F = R.S, R.F
    clean = "TS_Steel_PaintWhiteClean"
    M["truckWhite"] = S(ctx, clean, "MI_Steel_PaintTruckWhite", tint=(0.80, 0.80, 0.78), dirt_color=R.SOOT,
                        note="vehicle white (the premiere's trucks and the bus): the clean paint set, tinted, no rust")
    M["truckGrey"] = S(ctx, clean, "MI_Steel_PaintTruckGrey", tint=(0.30, 0.31, 0.33), dirt_color=R.SOOT)
    M["cityBlue"] = S(ctx, clean, "MI_Steel_PaintCityBlue", tint=(0.07, 0.19, 0.42), dirt_color=R.SOOT,
                      note="the stalled bus's blue (CITY CROSSTOWN, plain blue and white, no real livery)")
    M["cream"] = S(ctx, clean, "MI_Steel_PaintCream", tint=(0.82, 0.78, 0.62), dirt_color=R.SOOT, note="catering truck and trailers")
    M["teal"] = S(ctx, clean, "MI_Plastic_Portable", tint=(0.10, 0.34, 0.50), dirt_color=R.SOOT, note="portable toilets: blue plastic, no red")
    M["tentWhite"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_TentWhite", tint=(0.80, 0.79, 0.74), alpha="splash", dirt_color=R.SOOT,
                       note="VIP and merch tents: white canvas, opaque (no alpha)")
    M["tentBlack"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_TentBlack", tint=(0.05, 0.05, 0.055), alpha="splash", dirt_color=R.SOOT)
    M["cushion"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_Cushion", tint=(0.55, 0.50, 0.40), alpha="splash", dirt_color=R.SOOT,
                     note="THE LOFTLARK's cushions and umbrellas: sand canvas")
    M["plywood"] = S(ctx, "TS_Wood_ScanPlankNew", "MI_Wood_Hoarding", tint=(0.52, 0.52, 0.48), alpha="splash", dirt_color=R.SOOT,
                     note="hoarding and crates: the new plank scan, greyed")
    M["brass"] = F("MI_Metal_Brass", (0.55, 0.40, 0.16), 0.35, 0.9, note="bar rails, the luggage cart, the standpipe")
    M["glassTint"] = mat.make("MI_Glass_Tinted", "glass", Film=0.5)
    R.SLOT_META["MI_Glass_Tinted"] = {"workflow": "glass", "note": "M_MI_Glass, opaque (midtown.md 15: no translucency): vehicle and booth glass"}
    M["bulb"] = F("MI_Lamp_MarqueeBulb", (0.9, 0.85, 0.7), 0.3, emit=(1.0, 0.78, 0.4), strength=0.0,
                  note="marquee bulb bands: one bulb texture, a slow chase (3 s cycle, no flashing), emissive 350 nits (midtown.md 11.2)")
    M["tail"] = F("MI_Lamp_Tail", (0.30, 0.02, 0.02), 0.3, emit=(1.0, 0.12, 0.08), strength=0.0, note="tail and brake lamps, a few cm2")
    M["windowGrid"] = F("M_MT_WindowGrid", (0.04, 0.045, 0.06), 0.28,
                        note="the Midtown facade's window master (opaque): per window, from the world position of the pane, a lit state "
                             "(24 percent of the masses, 34 percent of the towers), a brightness with a long tail of dim ones, a colour "
                             "from tungsten to TV blue, a ceiling gradient and a covering (38 percent blinds, 22 percent curtains); "
                             "unlit panes are dark reflective glass (roughness 0.28). The specification is "
                             "_midtown_preview.window_grid (midtown_art.md 8)")
    R.SLOT_META["M_MT_WindowGrid"]["workflow"] = "window_grid"
    for col, h in (("Pink", "#ff3d9a"), ("Cyan", "#35e0ff")):
        M["neon" + col] = sg.neon_mat(col, h)
        R.SLOT_META["MI_Neon_" + col] = {"workflow": "emissive", "note": "exposed neon, 13 mm tube; off while THE LOFTLARK is closed (night "
                                         "strength 250 nits when lit, midtown.md 11.2)"}
    M["standoff"] = M["galv"]
    return M


# ================================================================================================= helpers

def dome(b, centre, r, slot, squash=0.6, seg=12, rings=6):
    s = geo.sphere(r, seg, rings)
    co, _ = geo.arrays(s)
    co[:, 2] = np.maximum(co[:, 2], 0.0) * squash
    geo.set_verts(s, co)
    geo.transform(s, loc=centre)
    return b.absorb(s, slot)


def blob(b, size, centre, slot, seed=0, amount=0.03):
    """A closed lumpy mass (a shrub, a hedge) from SQ.lump."""
    return SQ.lump(b, size, centre, slot, bevel=min(size) * 0.3, edge=0.14, amount=amount, seed=seed)


def lbl(b, o, u, v, w, h):
    """A thin backing plate and a printed face (M_Sign_MT_Face) on the plane through o spanned by u, v. Returns the frame."""
    o, u, v = (np.asarray(a, float) for a in (o, u, v))
    n = np.cross(u, v)
    n = n / np.linalg.norm(n)
    b.prism(steel.rect(w, h), o - n * 0.012, u, v, n * 0.012, "standBlack", pstep=9.0)
    return quad(b, o + n * 0.0008, u, v, w, h, "signFace")


# ================================================================================================= THE LOFTLARK

def m_bar(ctx, M):
    """The rooftop bar 4.0 x 1.0 x 1.1 (the data's lounge_bar): a guest counter on the -Y side (timber slats on a dark kick, a slab
    top overhanging the guests with a brass foot rail, a sink and a till) and a back bar behind it on the +Y side (two bays of bottle
    shelves to 1.9 on a mirror, a gap between them), the whole island inside the 1.0 m box; six pedestal stools stand in front on
    the deck. Customers' side -Y. Pivot: centre of the island, on the deck."""
    b = B(901, step=0.5)
    bx(b, (-2.0, -0.50, 0.0), (2.0, 0.05, 0.10), "standBlack", ch=0.004, pin=False, axis="x")                 # kick
    for i in range(20):                                                                                    # slat front
        x0 = -2.0 + i * 0.2
        bx(b, (x0 + 0.01, -0.50, 0.10), (x0 + 0.19, -0.42, 1.00), "boards", ch=0.004, pin=False, axis="z")
    bx(b, (-2.0, -0.42, 0.10), (2.0, 0.05, 1.00), "interior", pin=False, axis="x")                              # the body behind the slats
    bx(b, (-2.0, -0.56, 1.00), (2.0, 0.10, 1.10), "conc", ch=0.01, axis="x")                                    # slab top, overhanging the guests' side
    tube(b, (-1.9, -0.52, 0.22), (1.9, -0.52, 0.22), "brass", 0.03)                                               # foot rail
    for x in np.linspace(-1.9, 1.9, 5):
        tube(b, (x, -0.52, 0.22), (x, -0.44, 0.22), "brass", 0.03)
    bx(b, (0.90, -0.25, 1.10), (1.50, 0.05, 1.16), "stainless", ch=0.004, pin=False)                            # sink
    bx(b, (0.98, -0.21, 1.16), (1.42, 0.01, 1.18), "interior", pin=False)
    tube(b, (1.20, 0.00, 1.16), (1.20, 0.00, 1.40), "stainless", 0.03)
    bx(b, (-1.6, -0.25, 1.10), (-1.2, 0.05, 1.30), "plasticBlack", ch=0.008, pin=False)                         # till
    bx(b, (-1.52, -0.05, 1.30), (-1.28, 0.05, 1.46), "plasticBlack", ch=0.006, pin=False)
    # the back bar: two bays with a gap between them, shelves of bottles
    for xa, xb_ in ((-2.0, -0.45), (0.45, 2.0)):
        bx(b, (xa, 0.10, 0.0), (xb_, 0.50, 0.95), "standBlack", ch=0.005, pin=False, axis="x")               # back counter
        bx(b, (xa, 0.10, 0.95), (xb_, 0.50, 1.00), "conc", ch=0.006, pin=False, axis="x")
        bx(b, (xa, 0.46, 1.00), (xb_, 0.50, 1.90), "stainless", pin=False, axis="x")                              # mirror panel
        for zz in (1.30, 1.62, 1.88):
            bx(b, (xa, 0.24, zz - 0.02), (xb_, 0.46, zz + 0.02), "boards", pin=False, axis="x")
        for sh_z, n in ((1.32, 9), (1.64, 8)):
            for j in range(n):
                bx_ = xa + 0.12 + j * (xb_ - xa - 0.24) / max(n - 1, 1)
                rod(b, (bx_, 0.35, sh_z), (bx_, 0.35, sh_z + 0.24 + 0.04 * (j % 3)), 0.035, ["grille", "glassTint", "brass"][j % 3], n=8)
        for xx in (xa, xb_):
            bx(b, (xx - 0.03 if xx == xb_ else xx, 0.10, 0.0), (xx if xx == xb_ else xx + 0.03, 0.50, 1.90), "standBlack", pin=False, axis="z")
    bx(b, (-0.45, 0.10, 1.86), (0.45, 0.50, 1.92), "standBlack", pin=False, axis="x")                          # the gap's lintel
    for x in np.linspace(-1.6, 1.6, 6):                                                                      # pedestal stools (guests' side)
        rod(b, (x, -1.00, 0.0), (x, -1.00, 0.04), 0.20, "standBlack", n=14)
        rod(b, (x, -1.00, 0.04), (x, -1.00, 0.62), 0.04, "stainless", n=8)
        rod(b, (x, -1.00, 0.62), (x, -1.00, 0.69), 0.19, "cushion", n=16)
    return done(ctx, b, "SM_Roof_Lounge_Bar", M, ground=True, cover_height=1.1, expect_size=(None, None, None),
                notes="THE LOFTLARK's bar 4.0 x 1.0 x 1.1 (the data's lounge_bar): a guest counter (slat front on a kick, slab top with a "
                      "brass foot rail, sink and till) and a back bar behind it (two bays of bottle shelves to 1.9 on a mirror, a gap "
                      "between), the island inside the 1.0 m box; six pedestal stools stand in front on the deck (-Y, outside the "
                      "collider). The back bar is over the box (shots pass). Pivot: centre of the island, on the deck.")


def m_lounger(ctx, M):
    """A low lounge sofa 1.4 x 1.0 x 0.5 (the data's lounger): a timber frame on short legs, a seat and a back cushion,
    two arm bolsters. Front toward -Y. Pivot: centre, on the deck."""
    b = B(911, step=0.4)
    bx(b, (-0.70, -0.50, 0.10), (0.70, 0.50, 0.26), "boards", ch=0.008, pin=False, axis="x")
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx(b, (sx * 0.62 - 0.05, sy * 0.42 - 0.05, 0.0), (sx * 0.62 + 0.05, sy * 0.42 + 0.05, 0.10), "standBlack", pin=False, axis="z")
    bx(b, (-0.66, -0.46, 0.26), (0.66, 0.30, 0.42), "cushion", ch=0.05, pin=False, axis="x")                   # seat
    bx(b, (-0.66, 0.30, 0.26), (0.66, 0.46, 0.78), "cushion", ch=0.05, pin=False, axis="x")                     # back
    for sx in (-1, 1):
        bx(b, (sx * 0.62 - 0.07, -0.44, 0.42), (sx * 0.62 + 0.07, 0.30, 0.56), "cushion", ch=0.04, pin=False, axis="y")
    return done(ctx, b, "SM_Roof_Lounger", M, ground=True, cover_height=0.5, expect_size=(None, None, None),
                notes="THE LOFTLARK's low lounge sofa 1.4 x 1.0 x 0.5 (the data's lounger; the back cushion rises to 0.78 over the "
                      "box). Front toward -Y. Pivot: centre, on the deck.")


def m_lounger_stack(ctx, M):
    """Folded sun loungers stacked 1.5 x 2.0 x 0.9 (the data's lounger_stack): six aluminium-framed loungers, two columns of
    three, with slatted sling beds, strapped. Pivot: centre, on the deck; the long side along Y."""
    b = B(912, step=0.5)
    for cx in (-0.37, 0.37):
        for k in range(3):
            z0 = 0.06 + k * 0.28
            for sx in (-1, 1):
                bx(b, (cx + sx * 0.30 - 0.03, -1.0, z0), (cx + sx * 0.30 + 0.03, 1.0, z0 + 0.06), "galv", pin=False, axis="y")
            for j in range(10):
                y0 = -0.95 + j * 0.19
                bx(b, (cx - 0.30, y0, z0 + 0.06), (cx + 0.30, y0 + 0.14, z0 + 0.10), "cushion", pin=False, axis="x")
            bx(b, (cx - 0.32, -0.45, z0 + 0.10), (cx + 0.32, 0.45, z0 + 0.20), "cushion", ch=0.03, pin=False, axis="x")   # the folded pad
        bx(b, (cx - 0.32, -0.30, 0.06), (cx - 0.28, -0.20, 0.88), "black", pin=False, axis="z")              # strap
        bx(b, (cx + 0.28, -0.30, 0.06), (cx + 0.32, -0.20, 0.88), "black", pin=False, axis="z")
        bx(b, (cx - 0.32, -0.30, 0.86), (cx + 0.32, -0.20, 0.90), "black", pin=False, axis="x")
    return done(ctx, b, "SM_Roof_Lounger_Stack", M, ground=True, cover_height=0.9, expect_size=(None, None, None),
                notes="Folded sun loungers stacked, 1.5 x 2.0 x 0.9 (the data's lounger_stack): two columns of three aluminium "
                      "frames with slatted beds and folded pads, strapped. Pivot: centre, on the deck; long side along Y.")


def m_umbrella(ctx, M):
    """A folded patio umbrella on its timber foot, 0.4 x 1.0 x 2.2 (the data's umbrella_folded): a 1.0 m sleeper foot, a 6 cm
    steel pole, the sand canvas furled and tied along the top 1.6 m. Pivot: centre, on the deck."""
    b = B(913, step=0.5)
    bx(b, (-0.20, -0.50, 0.0), (0.20, 0.50, 0.12), "boards", ch=0.01, pin=False, axis="y")
    tube(b, (0, 0, 0.12), (0, 0, 2.20), "black", 0.03)
    s = geo.sphere(0.5, 14, 8)
    co, _ = geo.arrays(s)
    co[:, 0] *= 0.20 / 0.5
    co[:, 1] *= 0.20 / 0.5
    co[:, 2] *= 0.82 / 0.5
    geo.set_verts(s, co)
    geo.transform(s, loc=(0.0, 0.0, 1.45))
    b.absorb(s, "cushion")
    for z in (1.0, 1.45, 1.9):
        rod(b, (0, 0, z), (0, 0, z + 0.03), 0.105, "black", n=14)
    rod(b, (0, 0, 2.20), (0, 0, 2.24), 0.04, "brass", n=8)
    return done(ctx, b, "SM_Roof_Umbrella_Folded", M, ground=True, cover_height=2.2, expect_size=(None, None, None),
                notes="Folded patio umbrella on its timber foot, 0.4 x 1.0 x 2.2 (the data's umbrella_folded): 6 cm pole, sand canvas "
                      "furled and tied. Pivot: centre, on the deck.")


def m_planterbox(ctx, M):
    """A timber planter box 1.0 x 2.0 x 0.9 (the data's planter_box): board sides on feet, soil and a clipped shrub row
    (a closed lumpy mesh: no masked leaves). Pivot: centre, on the deck."""
    b = B(914, step=0.5)
    for sx in (-1, 1):
        bx(b, (sx * 0.47 - 0.03, -1.0, 0.10), (sx * 0.47 + 0.03, 1.0, 0.56), "boards", pin=False, axis="y")
    for sy in (-1, 1):
        bx(b, (-0.5, sy * 0.97 - 0.03, 0.10), (0.5, sy * 0.97 + 0.03, 0.56), "boards", pin=False, axis="x")
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx(b, (sx * 0.44 - 0.04, sy * 0.94 - 0.04, 0.0), (sx * 0.44 + 0.04, sy * 0.94 + 0.04, 0.12), "standBlack", pin=False, axis="z")
    bx(b, (-0.45, -0.94, 0.12), (0.45, 0.94, 0.50), "soil", pin=False, axis="y")
    blob(b, (0.80, 1.78, 0.42), (0.0, 0.0, 0.70), "hedge", seed=5, amount=0.04)
    return done(ctx, b, "SM_Roof_PlanterBox", M, ground=True, cover_height=0.9, expect_size=(None, None, None),
                notes="Timber planter 1.0 x 2.0 x 0.9 (the data's planter_box; one is stretched to 1.5): board sides on feet, soil, a "
                      "clipped shrub row (closed lumpy mesh, the privet leaf set, opaque). Pivot: centre, on the deck.")


def m_loftlark_neon(ctx, M):
    """THE LOFTLARK in exposed neon, 4.0 x 0.9 (midtown.md 12.4: neon on D, unlit, the lounge is closed): a black steel pan with
    a border tube and the name in 13 mm tubes on standoffs (the Canal kit's neon_text), two clamp brackets and a transformer.
    Pivot: bottom-left of the face, the face toward -Y, the pan behind (+Y)."""
    from assets import _chinatown_front as cf
    b = B(915, step=0.5)
    w, h = 4.0, 0.9
    bx(b, (0, 0.003, 0), (w, 0.08, h), "black", ch=0.004, axis="x", pin=False)
    r, yt = 0.0065, -0.0415
    cf.neon_text(b, "THE LOFTLARK", "heavy", 0.50 * h, w, h, 0.50, "neonPink", r, yt, w - 0.4)
    bt = sg.rounded_rect(0.09 * h, 0.09 * h, w - 0.09 * h, h - 0.09 * h, 0.14 * h, 0.05)
    sg.tube(b, sg.to3(bt, yt), r, "neonCyan", seg=6)
    for i in np.linspace(0, len(bt), 14, endpoint=False).astype(int):
        sg.cyl(b, (bt[i, 0], yt + r * 0.8, bt[i, 1]), (bt[i, 0], 0.0, bt[i, 1]), 0.0045, "standoff", seg=4)
    for x in (0.4, w - 0.4):                                                                                 # clamp brackets to the coping
        bx(b, (x - 0.04, 0.0, -0.40), (x + 0.04, 0.12, 0.0), "black", ch=0.004, pin=False, axis="z")
        bx(b, (x - 0.07, 0.12, -0.40), (x + 0.07, 0.26, -0.30), "black", ch=0.004, pin=False)
    bx(b, (w - 0.9, 0.08, h), (w - 0.5, 0.20, h + 0.12), "grey", ch=0.004, pin=False)
    return done(ctx, b, "SM_Roof_Loftlark_Neon_4m", M, ground=False, expect_size=(w, None, None),
                notes="THE LOFTLARK in exposed neon (an approved name, names.md): a 4.0 x 0.9 black steel pan, the name in 13 mm tubes "
                      "(MI_Neon_Pink) with a cyan border tube (MI_Neon_Cyan) on glass standoffs, clamp brackets to the parapet "
                      "coping, a transformer. The tubes are dark while the lounge is closed; lit they are 250 nits "
                      "(midtown.md 11.2). Pivot: bottom-left of the face, face toward -Y.")


def m_deck(ctx, M, kind):
    """A raised deck on D (THE LOFTLARK, 9.2 x 6.7, timber, 0.6 high) or E (the steel dunnage platform, 6.2 x 6.2): the top
    at +0.6, a 0.3 m step 0.5 m wide along the east and the south sides (the data's .step boxes), joists under, a fascia.
    Pivot: the centre of the deck, on the roof; the south side toward -Y, the east side +X."""
    timber = kind == "lounge"
    W, D = (9.2, 6.7) if timber else (6.2, 6.2)
    b = B(921 if timber else 922, step=0.6)
    H, ST = 0.60, 0.30
    top = "boards" if timber else "plate"
    if timber:
        for j in range(int(W / 0.14)):
            x0 = -W / 2 + j * 0.14
            bx(b, (x0 + 0.004, -D / 2, H - 0.035), (x0 + 0.136, D / 2, H), "boards", pin=False, axis="y")
    else:
        bx(b, (-W / 2, -D / 2, H - 0.012), (W / 2, D / 2, H), "plate", ch=0.003, axis="x")
        for i in range(1, 4):                                                                              # plate seams
            bx(b, (-W / 2 + i * W / 4 - 0.03, -D / 2, H - 0.014), (-W / 2 + i * W / 4 + 0.03, D / 2, H + 0.004), "black", pin=False, axis="y")
    bx(b, (-W / 2, -D / 2, 0.0), (W / 2, D / 2, H - 0.035 if timber else H - 0.012), "black" if not timber else "interior", pin=False, axis="x")
    for sx in (-1, 1):                                                                                      # fascia
        bx(b, (sx * W / 2 - (0.03 if sx > 0 else 0.0), -D / 2, 0.06), (sx * W / 2 + (0.03 if sx < 0 else 0.0), D / 2, H), "boards" if timber else "black", pin=False, axis="y")
    for sy in (-1, 1):
        bx(b, (-W / 2, sy * D / 2 - (0.03 if sy > 0 else 0.0), 0.06), (W / 2, sy * D / 2 + (0.03 if sy < 0 else 0.0), H), "boards" if timber else "black", pin=False, axis="x")
    for x in np.linspace(-W / 2 + 0.5, W / 2 - 0.5, int(W // 1.2)):                                         # joists / dunnage beams (6 cm up)
        R.beam_y(b, -D / 2, D / 2, x, 0.0, "black", d=0.14 if timber else 0.20, bf=0.10 if timber else 0.14)
    # steps: east (+X) and south (-Y) at 0.30
    sw = 0.5
    bx(b, (W / 2, -D / 2 - sw, 0.0), (W / 2 + sw, D / 2, ST), top, ch=0.004, pin=False, axis="y")
    bx(b, (-W / 2, -D / 2 - sw, 0.0), (W / 2, -D / 2, ST), top, ch=0.004, pin=False, axis="x")
    bx(b, (W / 2 + sw - 0.03, -D / 2 - sw, 0.0), (W / 2 + sw, D / 2, ST - 0.01), "black", pin=False, axis="y")
    if not timber:                                                                                          # cleats and a lashed pallet of tiles
        for x in (-2.4, 2.4):
            bx(b, (x - 0.15, -2.6, H), (x + 0.15, -2.2, H + 0.12), "black", ch=0.006, pin=False)
        bx(b, (-1.0, 0.3, H), (1.0, 1.1, H + 0.14), "boards", pin=False)
    name = "SM_Roof_LoungeDeck_9x7" if timber else "SM_Roof_DunnageDeck_6x6"
    return done(ctx, b, name, M, ground=False, expect_size=(None, None, None), cover_height=0.6,
                notes=("THE LOFTLARK's raised timber deck on D" if timber else "E's steel dunnage platform (the drop D2 lands on it)")
                      + ", %.1f x %.1f x 0.6 (the data's deck boxes), %s on joists, a fascia, a 0.30 m step 0.5 wide along the east and the south "
                      "sides. Pivot: the centre of the deck, on the roof; the south side toward -Y, the east side +X." % (W, D, "board decking" if timber else "checker plate"))


# ================================================================================================= the roof boxes with no art

def m_duct(ctx, M):
    """A sheet-metal duct plenum 1.6 x 1.6 x 1.1 (the data's duct_box, six of them): a galvanised box with standing seams and
    flanges, an insulated round duct rising 0.4 and turning over, and a service panel with latches. Pivot: centre, on the roof."""
    b = B(931, step=0.5)
    bx(b, (-0.8, -0.8, 0.0), (0.8, 0.8, 0.80), "galv", ch=0.012, axis="x")
    for i in range(1, 4):                                                                                  # standing seams
        bx(b, (-0.8 + i * 0.4 - 0.03, -0.81, 0.04), (-0.8 + i * 0.4 + 0.03, -0.80, 0.76), "grey", pin=False, axis="z")
        bx(b, (-0.81, -0.8 + i * 0.4 - 0.03, 0.04), (-0.80, -0.8 + i * 0.4 + 0.03, 0.76), "grey", pin=False, axis="z")
    bx(b, (-0.84, -0.84, 0.78), (0.84, 0.84, 0.84), "grey", ch=0.006, pin=False, axis="x")                   # top flange
    bx(b, (-0.6, -0.6, 0.0), (-0.1, -0.5, 0.30), "grey", pin=False)                                          # service panel (-Y), latches
    bx(b, (-0.6, -0.815, 0.12), (-0.1, -0.80, 0.62), "grey", ch=0.006, pin=False, axis="z")
    for x in (-0.55, -0.15):
        bx(b, (x - 0.03, -0.83, 0.32), (x + 0.03, -0.815, 0.38), "black", pin=False)
    rod(b, (0.30, 0.20, 0.84), (0.30, 0.20, 1.02), 0.25, "grey", n=16)                                       # insulated duct, wrapped
    for z in (0.90, 0.99):
        rod(b, (0.30, 0.20, z), (0.30, 0.20, z + 0.025), 0.275, "galv", n=16)
    rod(b, (0.30, 0.20, 1.02), (0.55, 0.20, 1.02), 0.25, "grey", n=16)
    rod(b, (0.55, 0.20, 1.02), (0.55, 0.20, 1.10), 0.25, "grey", n=16)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx(b, (sx * 0.72 - 0.08, sy * 0.72 - 0.08, 0.0), (sx * 0.72 + 0.08, sy * 0.72 + 0.08, 0.04), "black", pin=False, axis="z")
    return done(ctx, b, "SM_Roof_DuctBox_1p6", M, ground=True, cover_height=1.1, expect_size=(None, None, None),
                notes="Duct plenum 1.6 x 1.6 x 1.1 (the data's duct_box, six on the roofs): galvanised box with seams and a flange, a "
                      "service panel with latches on -Y, a wrapped round duct rising and turning over. Pivot: centre, on the roof.")


def m_ventbox(ctx, M):
    """A louvred vent housing 1.0 x 1.0 x 1.2 (the data's vent_box, two): a steel curb, louvres on all four faces over a dark
    gap, a pitched cap, a short flue. Pivot: centre, on the roof."""
    b = B(932, step=0.5)
    bx(b, (-0.5, -0.5, 0.0), (0.5, 0.5, 0.16), "grey", ch=0.008, axis="x")
    for sx, sy, ax in ((0, -1, "x"), (0, 1, "x"), (-1, 0, "y"), (1, 0, "y")):
        for k in range(8):
            z0 = 0.20 + k * 0.095
            if ax == "x":
                y = sy * 0.455
                bx(b, (-0.42, y - 0.045, z0), (0.42, y + 0.045, z0 + 0.04), "grille" if k % 2 else "galv", pin=False, axis="x")
            else:
                x = sx * 0.455
                bx(b, (x - 0.045, -0.42, z0), (x + 0.045, 0.42, z0 + 0.04), "grille" if k % 2 else "galv", pin=False, axis="y")
    bx(b, (-0.44, -0.44, 0.16), (0.44, 0.44, 1.0), "interior", pin=False, axis="z")
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx(b, (sx * 0.46 - 0.04, sy * 0.46 - 0.04, 0.16), (sx * 0.46 + 0.04, sy * 0.46 + 0.04, 1.02), "grey", pin=False, axis="z")
    b.poly_plate([(-0.56, -0.56, 1.02), (0.56, -0.56, 1.02), (0.56, 0.0, 1.16), (-0.56, 0.0, 1.16)], 0.02, "galv", kind=b.OTHER)
    b.poly_plate([(-0.56, 0.0, 1.16), (0.56, 0.0, 1.16), (0.56, 0.56, 1.02), (-0.56, 0.56, 1.02)], 0.02, "galv", kind=b.OTHER)
    rod(b, (0.0, 0.0, 1.14), (0.0, 0.0, 1.20), 0.10, "grey", n=10)
    return done(ctx, b, "SM_Roof_VentBox_1x1", M, ground=True, cover_height=1.2, expect_size=(None, None, None),
                notes="Louvred vent housing 1.0 x 1.0 x 1.2 (the data's vent_box, two): steel curb, louvres on four faces over a dark "
                      "gap, corner posts, a pitched galvanised cap. Pivot: centre, on the roof.")


def m_conduitbox(ctx, M):
    """An electrical junction cabinet 1.4 x 0.8 x 0.7 (the data's conduit_box): a grey steel enclosure on a plinth with hinged
    doors, 6 cm conduits dropping in from the roof side, a DANGER / HIGH VOLTAGE label. Pivot: centre, on the roof; doors -Y."""
    b = B(933, step=0.5)
    bx(b, (-0.70, -0.40, 0.0), (0.70, 0.40, 0.08), "black", ch=0.004, pin=False, axis="x")
    bx(b, (-0.68, -0.38, 0.08), (0.68, 0.38, 0.66), "grey", ch=0.01, axis="x")
    for i in range(2):                                                                                     # two doors
        x0 = -0.64 + i * 0.64
        bx(b, (x0, -0.395, 0.12), (x0 + 0.60, -0.38, 0.62), "grey", ch=0.006, pin=False, axis="x")
        bx(b, (x0 + (0.50 if i == 0 else 0.04), -0.405, 0.30), (x0 + (0.56 if i == 0 else 0.10), -0.395, 0.46), "black", pin=False)
    bx(b, (-0.70, -0.38, 0.66), (0.70, 0.40, 0.70), "black", ch=0.004, pin=False, axis="x")                  # rain hood
    for x in (-0.45, 0.0, 0.45):                                                                          # conduits
        tube(b, (x, 0.30, 0.66), (x, 0.30, 0.62), "galv", 0.03)
        tube(b, (x, 0.40, 0.55), (x, 0.60, 0.55), "galv", 0.03)
    lab = R.label(b, (0.10, -0.396, 0.22), X, Z, 0.36, 0.24)
    return done(ctx, b, "SM_Roof_ConduitBox_1p4", M, ground=True, labels=[lab], cover_height=0.7, expect_size=(None, None, None),
                notes="Junction cabinet 1.4 x 0.8 x 0.7 (the data's conduit_box, two): grey steel on a plinth, two hinged doors with "
                      "latches, a rain hood, 6 cm conduits, Label_HighVoltage. Pivot: centre, on the roof; doors toward -Y.")


def m_conduitrun(ctx, M):
    """A conduit run 0.4 x 4.0 x 0.7 (the data's conduit_run): three 6 cm galvanised conduits and a cable tray on five saddle
    stands, a junction box in the middle. Pivot: centre, on the roof; the run along Y."""
    b = B(934, step=0.6)
    for y in np.linspace(-1.9, 1.9, 5):
        bx(b, (-0.18, y - 0.04, 0.0), (0.18, y + 0.04, 0.06), "black", pin=False, axis="x")
        for x in (-0.16, 0.16):
            bx(b, (x - 0.03, y - 0.03, 0.06), (x + 0.03, y + 0.03, 0.42), "black", pin=False, axis="z")
        bx(b, (-0.20, y - 0.04, 0.42), (0.20, y + 0.04, 0.46), "black", pin=False, axis="x")
    for x in (-0.12, 0.0, 0.12):
        tube(b, (x, -2.0, 0.52), (x, 2.0, 0.52), "galv", 0.03)
    bx(b, (-0.20, -2.0, 0.60), (0.20, 2.0, 0.64), "plate", pin=False, axis="y")
    bx(b, (-0.22, -0.20, 0.42), (0.22, 0.20, 0.70), "grey", ch=0.008, pin=False)
    return done(ctx, b, "SM_Roof_ConduitRun_4m", M, ground=True, cover_height=0.7, expect_size=(None, None, None),
                notes="Conduit run 0.4 x 4.0 x 0.7 (the data's conduit_run): three 6 cm conduits and a tray on five saddle stands, a "
                      "junction box. Pivot: centre, on the roof; along Y.")


def m_sleepers(ctx, M):
    """Pipe sleepers 1.6 x 0.8 x 0.35 (the data's pipe_sleepers, four): two timber sleepers carrying two insulated pipes with
    jacketed sleeves, a steel saddle each. Pivot: centre, on the roof; the pipes along X."""
    b = B(935, step=0.5)
    for x in (-0.55, 0.55):
        bx(b, (x - 0.10, -0.40, 0.0), (x + 0.10, 0.40, 0.14), "boards", ch=0.008, pin=False, axis="y")
    for y in (-0.20, 0.20):
        rod(b, (-0.80, y, 0.245), (0.80, y, 0.245), 0.105, "hvac", n=16)
        for x in (-0.55, 0.55):
            rod(b, (x - 0.06, y, 0.245), (x + 0.06, y, 0.245), 0.115, "galv", n=16)
        rod(b, (-0.80, y, 0.245), (-0.795, y, 0.245), 0.05, "black", n=8)
    return done(ctx, b, "SM_Roof_PipeSleepers_1p6", M, ground=True, cover_height=0.35, expect_size=(None, None, None),
                notes="Pipe sleepers 1.6 x 0.8 x 0.35 (the data's pipe_sleepers, four): two timber sleepers carrying two insulated "
                      "pipes, metal saddles. Pivot: centre, on the roof; the pipes along X.")


def m_fan(ctx, M):
    """A roof exhaust fan 1.6 x 1.6 x 1.0 (the data's fan_housing): a square curb, a round housing, a domed hood on four
    posts over the fan, a guard ring, a belt box, a disconnect on the curb. Pivot: centre, on the roof."""
    b = B(936, step=0.5)
    bx(b, (-0.8, -0.8, 0.0), (0.8, 0.8, 0.30), "grey", ch=0.01, axis="x")
    rod(b, (0, 0, 0.30), (0, 0, 0.55), 0.62, "galv", n=28)
    rod(b, (0, 0, 0.55), (0, 0, 0.60), 0.70, "grey", n=28)
    rod(b, (0, 0, 0.60), (0, 0, 0.66), 0.46, "grille", n=24)
    for a in range(4):
        t = math.radians(45 + 90 * a)
        rod(b, (0.55 * math.cos(t), 0.55 * math.sin(t), 0.60), (0.55 * math.cos(t), 0.55 * math.sin(t), 0.84), 0.04, "galv", n=8)
    dome(b, (0, 0, 0.84), 0.74, "galv", squash=0.30, seg=24, rings=8)
    rod(b, (0, 0, 1.0), (0, 0, 1.04), 0.10, "grey", n=10)
    bx(b, (0.62, -0.20, 0.0), (0.80, 0.20, 0.55), "grey", ch=0.006, pin=False)                               # disconnect
    bx(b, (0.60, -0.14, 0.40), (0.64, 0.14, 0.50), "black", pin=False)
    return done(ctx, b, "SM_Roof_FanHousing_1p6", M, ground=True, cover_height=1.0, expect_size=(None, None, None),
                notes="Roof exhaust fan 1.6 x 1.6 x 1.0 (the data's fan_housing): curb, round housing, guard ring, a domed galvanised "
                      "hood on four posts, a disconnect. Pivot: centre, on the roof.")


# ================================================================================================= the plaza's small dressing

def m_bollard_planter(ctx, M):
    """A heavy bollard planter 0.7 x 0.7 x 0.9 (the data's bollard_planter, two): a precast granite drum, a collar, soil and a
    clipped shrub; the sort that stops a vehicle. Pivot: centre, ground."""
    b = B(941, step=0.4)
    p = geo.revolve([(0.0, 0.0), (0.35, 0.0), (0.355, 0.60), (0.31, 0.64), (0.30, 0.60), (0.0, 0.60)], 28)
    b.absorb(p, "granite")
    rod(b, (0, 0, 0.0), (0, 0, 0.06), 0.345, "black", n=24)
    rod(b, (0, 0, 0.52), (0, 0, 0.58), 0.36, "stone", n=24)
    dome(b, (0, 0, 0.60), 0.29, "soil", squash=0.2, seg=16, rings=4)
    blob(b, (0.52, 0.52, 0.34), (0, 0, 0.74), "hedge", seed=11, amount=0.03)
    return done(ctx, b, "SM_Sq_BollardPlanter", M, ground=True, cover_height=0.9, expect_size=(None, None, None),
                notes="Bollard planter 0.7 x 0.7 x 0.9 (the data's bollard_planter, two): a granite drum with a collar, soil and a "
                      "clipped shrub (opaque lumpy mesh). Pivot: centre, ground.")


def m_newsstand(ctx, M):
    """A newsstand 2.0 wide x 1.4 deep x 2.6 (the data's newsstand, three): a steel kiosk with the sales window and a fold-down shelf on
    -Y, racks of magazines and snacks lit by a strip, a pitched roof with a lightbox header on the front. Pivot: centre, ground; the window toward -Y."""
    b = B(942, step=0.5)
    L, W = 2.0, 1.4
    bx(b, (-L / 2, -W / 2, 0.0), (L / 2, W / 2, 0.14), "black", ch=0.004, axis="x", pin=False)
    for (xa, xb_, ya, yb) in ((-L / 2, -L / 2 + 0.05, -W / 2, W / 2), (L / 2 - 0.05, L / 2, -W / 2, W / 2), (-L / 2, L / 2, W / 2 - 0.05, W / 2)):
        bx(b, (xa, ya, 0.14), (xb_, yb, 2.20), "kiosk", axis="z", pin=False)
    bx(b, (-L / 2, -W / 2, 0.14), (L / 2, -W / 2 + 0.05, 0.95), "kiosk", axis="x", pin=False)                    # below the window
    bx(b, (-L / 2, -W / 2, 1.90), (L / 2, -W / 2 + 0.05, 2.20), "kiosk", axis="x", pin=False)                    # above it
    bx(b, (-L / 2 - 0.04, -W / 2 - 0.34, 0.92), (L / 2 + 0.04, -W / 2 + 0.05, 0.97), "stainless", ch=0.005, axis="x", pin=False)  # the shelf
    for j in range(6):                                                                                    # magazine rows on the shelf
        x0 = -L / 2 + 0.08 + j * 0.32
        bx(b, (x0, -W / 2 - 0.30, 0.97), (x0 + 0.28, -W / 2 - 0.10, 1.16 + 0.04 * (j % 2)), ["white", "yellow", "umbrella", "orange"][j % 4], pin=False)
    for k in range(3):                                                                                    # racks inside, lit
        bx(b, (-L / 2 + 0.06, -W / 2 + 0.10, 1.05 + k * 0.28), (L / 2 - 0.06, -W / 2 + 0.34, 1.07 + k * 0.28), "stainless", pin=False, axis="x")
        for j in range(7):
            x0 = -L / 2 + 0.10 + j * 0.27
            bx(b, (x0, -W / 2 + 0.12, 1.07 + k * 0.28), (x0 + 0.20, -W / 2 + 0.30, 1.24 + k * 0.28), ["white", "yellow", "umbrella", "orange", "plasticBlack"][(j + k) % 5], pin=False)
    bx(b, (-L / 2 + 0.06, -W / 2 + 0.06, 1.88), (L / 2 - 0.06, -W / 2 + 0.12, 1.92), "warm", pin=False, axis="x")   # strip
    b.poly_plate([(-L / 2 - 0.10, -W / 2 - 0.40, 2.20), (L / 2 + 0.10, -W / 2 - 0.40, 2.20), (L / 2 + 0.10, 0.0, 2.38), (-L / 2 - 0.10, 0.0, 2.38)][::-1],
                 0.05, "kiosk", kind=b.OTHER)
    b.poly_plate([(-L / 2 - 0.10, 0.0, 2.38), (L / 2 + 0.10, 0.0, 2.38), (L / 2 + 0.10, W / 2 + 0.10, 2.20), (-L / 2 - 0.10, W / 2 + 0.10, 2.20)][::-1],
                 0.05, "kiosk", kind=b.OTHER)
    bx(b, (-L / 2 - 0.10, -W / 2 - 0.42, 2.22), (L / 2 + 0.10, -W / 2 - 0.30, 2.58), "standBlack", ch=0.006, pin=False, axis="x")     # header
    faces = [quad(b, (-L / 2 - 0.08, -W / 2 - 0.431, 2.26), X, Z, L + 0.16, 0.30, "signFace")]
    for j in range(3):                                                                                    # bundles of papers on the roof
        bx(b, (-0.5 + j * 0.34, -0.3, 2.38), (-0.2 + j * 0.34, 0.3, 2.50), "white", pin=False)
    bx(b, (-0.25, W / 2 - 0.06, 0.14), (0.25, W / 2, 1.95), "kiosk", ch=0.004, pin=False, axis="z")         # back door
    return done(ctx, b, "SM_Sq_Newsstand", M, ground=True, faces=faces, cover_height=2.6, expect_size=(None, None, None),
                notes="Newsstand 2.0 x 1.4 x 2.6 (the data's newsstand, three: 1.4 x 2.0 boxes): navy steel kiosk, sales window with a stainless shelf "
                      "of magazines on -Y, lit racks (MI_Lamp_KioskInterior), pitched roof, a header lightbox (face Label_Newsstand, "
                      "200 nits) and bundles on the roof. Generic words only. Pivot: centre, ground.")


def m_phonekiosk(ctx, M):
    """A street phone and charging kiosk 1.2 x 0.5 x 2.5 (the data's phone_kiosk, two): a slab pylon on a plinth with a
    hood, a handset cradle and a keypad panel at 1.1, a charging shelf, an info panel face (Label_PhoneKiosk). Pivot: centre,
    ground; the front toward -Y."""
    b = B(943, step=0.5)
    bx(b, (-0.60, -0.25, 0.0), (0.60, 0.25, 0.12), "black", ch=0.004, pin=False, axis="x")
    bx(b, (-0.55, -0.20, 0.12), (0.55, 0.20, 2.30), "kiosk", ch=0.01, axis="z", pin=False)
    bx(b, (-0.58, -0.24, 2.30), (0.58, 0.24, 2.50), "standBlack", ch=0.01, pin=False)
    bx(b, (-0.50, -0.26, 1.00), (0.50, -0.20, 1.40), "standBlack", ch=0.004, pin=False)                       # the keypad panel
    for r in range(4):
        for c in range(3):
            bx(b, (-0.14 + c * 0.10, -0.275, 1.06 + r * 0.075), (-0.07 + c * 0.10, -0.26, 1.10 + r * 0.075), "stainless", pin=False)
    bx(b, (0.20, -0.32, 1.10), (0.38, -0.24, 1.34), "black", ch=0.01, pin=False)                              # handset cradle
    bx(b, (0.22, -0.40, 1.18), (0.36, -0.30, 1.30), "plasticBlack", ch=0.01, pin=False)
    bx(b, (-0.45, -0.34, 0.80), (0.0, -0.20, 0.86), "stainless", ch=0.004, pin=False)                       # charging shelf
    bx(b, (-0.40, -0.30, 0.86), (-0.10, -0.24, 0.90), "indicator", pin=False)
    bx(b, (-0.22, -0.204, 1.54), (0.22, -0.20, 1.88), "standBlack", pin=False)
    faces = [quad(b, (-0.20, -0.2048, 1.56), X, Z, 0.40, 0.30, "signFace")]
    return done(ctx, b, "SM_Sq_PhoneKiosk", M, ground=True, faces=faces, cover_height=2.5, expect_size=(None, None, None),
                notes="Phone and charging kiosk 1.2 x 0.5 x 2.5 (the data's phone_kiosk, two): navy slab pylon with a hood, keypad "
                      "panel, handset cradle, charging shelf, an info panel (face Label_PhoneKiosk, generic words). Pivot: centre, "
                      "ground; the front toward -Y.")


def m_pylon(ctx, M):
    """A wayfinding pylon 0.6 x 1.0 x 2.4 (the data's wayfinding_pylon, two): a steel plinth and shaft with directional blades
    on two sides reading the real street names (Pylon_Streets), a cap. Pivot: centre, ground; the blades face -Y and +Y."""
    b = B(944, step=0.5)
    bx(b, (-0.30, -0.50, 0.0), (0.30, 0.50, 0.10), "black", ch=0.004, pin=False, axis="y")
    bx(b, (-0.16, -0.45, 0.10), (0.16, 0.45, 2.30), "standGrey", ch=0.01, axis="z", pin=False)
    bx(b, (-0.20, -0.48, 2.30), (0.20, 0.48, 2.40), "standBlack", ch=0.008, pin=False)
    # two printed faces on the long sides (+-X): the shaft is 0.32 wide x 0.9 long; each face is 0.80 x 0.36 at 1.50
    faces = [quad(b, (-0.1605, -0.40, 1.50), Y, Z, 0.80, 0.36, "signFace"), quad(b, (0.1605, 0.40, 1.50), -Y, Z, 0.80, 0.36, "signFace")]
    return done(ctx, b, "SM_Sq_WayfindingPylon", M, ground=True, faces=faces, cover_height=2.4, expect_size=(None, None, None),
                notes="Wayfinding pylon 0.6 x 1.0 x 2.4 (the data's wayfinding_pylon, two): grey steel shaft on a plinth with a cap, "
                      "a printed street-name face (Pylon_Streets: SEVENTH AV, BROADWAY, W 46 ST) on each long side. Pivot: centre, "
                      "ground; the faces look along -X and +X.")


def m_atm(ctx, M):
    """A freestanding cash machine kiosk 0.7 x 0.8 x 1.4 (the data's atm_kiosk at the closed bank lobby): a steel cabinet, a
    lit screen panel (dark, off), a keypad, a card slot, a canopy hood, Label_ATM. Pivot: centre, ground; the front -Y."""
    b = B(945, step=0.4)
    bx(b, (-0.35, -0.40, 0.0), (0.35, 0.40, 0.08), "black", ch=0.004, pin=False, axis="y")
    bx(b, (-0.33, -0.38, 0.08), (0.33, 0.38, 1.30), "standGrey", ch=0.01, axis="z", pin=False)
    bx(b, (-0.36, -0.42, 1.30), (0.36, 0.40, 1.40), "standBlack", ch=0.008, pin=False)
    bx(b, (-0.22, -0.395, 0.95), (0.22, -0.38, 1.22), "interior", pin=False)                                 # screen (off)
    bx(b, (-0.24, -0.40, 0.93), (0.24, -0.38, 0.95), "black", pin=False, axis="x")
    for r in range(4):
        for c in range(3):
            bx(b, (-0.12 + c * 0.09, -0.40, 0.58 + r * 0.07), (-0.06 + c * 0.09, -0.388, 0.62 + r * 0.07), "stainless", pin=False)
    bx(b, (0.10, -0.40, 0.70), (0.30, -0.385, 0.74), "black", pin=False)
    bx(b, (-0.25, -0.43, 0.30), (0.25, -0.38, 0.40), "stainless", ch=0.005, pin=False)                       # cash tray
    bx(b, (-0.14, -0.395, 0.34), (0.14, -0.38, 0.36), "interior", pin=False)
    faces = [lbl(b, (-0.20, -0.4125, 1.32), X, Z, 0.40, 0.06)]
    return done(ctx, b, "SM_Sq_ATM_Kiosk", M, ground=True, faces=faces, cover_height=1.4, expect_size=(None, None, None),
                notes="Cash machine kiosk 0.7 x 0.8 x 1.4 (the data's atm_kiosk by the closed bank lobby): steel cabinet, a dark screen, "
                      "keypad, cash tray, a hood, Label_ATM. Pivot: centre, ground; the front toward -Y.")


def m_standpipe(ctx, M):
    """A siamese fire standpipe connection 0.3 x 0.3 x 0.9 (the data's standpipe, two): a brass two-way inlet on a wall plate
    at 0.85, caps on chains, a stub pipe. Pivot: centre, ground; the inlets face -Y."""
    b = B(946, step=0.3)
    bx(b, (-0.15, 0.08, 0.0), (0.15, 0.15, 0.90), "black", ch=0.004, pin=False)
    bx(b, (-0.14, 0.02, 0.55), (0.14, 0.08, 0.80), "brass", ch=0.01, pin=False)
    for s in (-1, 1):
        rod(b, (s * 0.07, 0.02, 0.68), (s * 0.07, -0.10, 0.68), 0.05, "brass", n=10)
        rod(b, (s * 0.07, -0.10, 0.68), (s * 0.07, -0.13, 0.68), 0.06, "brass", n=10)
    rod(b, (0.0, 0.05, 0.0), (0.0, 0.05, 0.55), 0.035, "brass", n=8)
    return done(ctx, b, "SM_Sq_Standpipe", M, ground=True, cover_height=0.9, expect_size=(None, None, None),
                notes="Siamese standpipe connection 0.3 x 0.3 x 0.9 (the data's standpipe, two): brass two-way inlet on a wall plate, "
                      "capped. Pivot: centre, ground; the inlets face -Y.")


def m_valet(ctx, M):
    """A hotel valet stand 1.6 x 1.0 x 1.1 (the data's valet_stand): a dark timber lectern on a platform with a brass rail, a
    key cabinet behind it (rows of hooks), a pen light, Label_Valet. Pivot: centre, ground; the attendant's front -Y."""
    b = B(947, step=0.4)
    bx(b, (-0.80, -0.50, 0.0), (0.80, 0.50, 0.06), "standBlack", ch=0.004, pin=False, axis="x")
    bx(b, (-0.40, -0.25, 0.06), (0.40, 0.15, 1.00), "plywood", ch=0.01, pin=False)
    bx(b, (-0.45, -0.30, 1.00), (0.45, 0.20, 1.06), "brass", ch=0.008, pin=False)
    bx(b, (-0.60, 0.20, 0.06), (0.60, 0.46, 1.10), "standBlack", ch=0.008, pin=False)
    for r in range(3):
        for c in range(8):
            bx(b, (-0.52 + c * 0.14, 0.18, 0.40 + r * 0.22), (-0.46 + c * 0.14, 0.20, 0.46 + r * 0.22), "brass", pin=False)
    for sx in (-1, 1):
        tube(b, (sx * 0.74, -0.45, 0.06), (sx * 0.74, -0.45, 1.00), "brass", 0.03)
    tube(b, (-0.74, -0.45, 1.00), (0.74, -0.45, 1.00), "brass", 0.03)
    faces = [lbl(b, (-0.20, -0.2512, 0.60), X, Z, 0.40, 0.20)]
    return done(ctx, b, "SM_Sq_ValetStand", M, ground=True, faces=faces, cover_height=1.1, expect_size=(None, None, None),
                notes="Hotel valet stand 1.6 x 1.0 x 1.1 (the data's valet_stand): a dark lectern on a platform, a key cabinet with "
                      "brass hooks, brass rails, Label_Valet. Pivot: centre, ground; the attendant's front toward -Y.")


def m_luggage(ctx, M):
    """A bellhop luggage cart 1.5 x 0.6 x 1.2 (the data's luggage_cart): a brass frame with two decks and a gantry on four
    casters, three suitcases and a garment bag. Pivot: centre, ground."""
    b = B(948, step=0.4)
    for sx in (-1, 1):
        tube(b, (sx * 0.70, -0.25, 0.10), (sx * 0.70, -0.25, 1.15), "brass", 0.03)
        tube(b, (sx * 0.70, 0.25, 0.10), (sx * 0.70, 0.25, 1.15), "brass", 0.03)
        tube(b, (sx * 0.70, -0.25, 1.15), (sx * 0.70, 0.25, 1.15), "brass", 0.03)
        for sy in (-1, 1):
            wheel = SQ.wheel
            wheel(b, (sx * 0.64, sy * 0.25, 0.07), 0.07, 0.04, Y)
    tube(b, (-0.70, -0.25, 1.15), (0.70, -0.25, 1.15), "brass", 0.03)
    tube(b, (-0.70, 0.25, 1.15), (0.70, 0.25, 1.15), "brass", 0.03)
    for z in (0.14, 0.52):
        bx(b, (-0.72, -0.27, z), (0.72, 0.27, z + 0.03), "brass", pin=False, axis="x")
    for x, w_, h_, c in ((-0.45, 0.45, 0.34, "plasticBlack"), (0.05, 0.50, 0.30, "standGrey"), (0.45, 0.34, 0.26, "plasticBlack")):
        bx(b, (x - w_ / 2, -0.22, 0.17), (x + w_ / 2, 0.22, 0.17 + h_), c, ch=0.02, pin=False)
    bx(b, (-0.40, -0.22, 0.55), (0.20, 0.22, 0.88), "umbrella", ch=0.02, pin=False)
    tube(b, (-0.15, 0.0, 0.88), (-0.15, 0.0, 1.15), "brass", 0.03)
    bx(b, (0.30, -0.22, 0.55), (0.65, 0.22, 0.82), "standGrey", ch=0.02, pin=False)
    return done(ctx, b, "SM_Sq_LuggageCart", M, ground=True, cover_height=1.2, expect_size=(None, None, None),
                notes="Bellhop luggage cart 1.5 x 0.6 x 1.2 (the data's luggage_cart): brass frame, two decks, a rail, four casters, three "
                      "cases and a garment bag. Pivot: centre, ground.")


def m_crates(ctx, M):
    """A stack of timber crates 1.3 x 1.4 x 1.0 (the data's crate_stack, one beside the facade at x -7.9): two rows of crates, a
    pallet under, one lid pried up. Pivot: centre, ground."""
    b = B(949, step=0.4)
    bx(b, (-0.65, -0.70, 0.0), (0.65, 0.70, 0.12), "boards", pin=False, axis="x")
    for (cx, cy, z0, h_) in ((-0.32, -0.33, 0.12, 0.45), (0.32, -0.33, 0.12, 0.45), (-0.32, 0.33, 0.12, 0.45), (0.32, 0.33, 0.12, 0.45),
                            (0.0, -0.33, 0.57, 0.40), (0.0, 0.33, 0.57, 0.40)):
        bx(b, (cx - 0.30, cy - 0.30, z0), (cx + 0.30, cy + 0.30, z0 + h_), "plywood", ch=0.008, pin=False)
        for k in range(3):
            bx(b, (cx - 0.31, cy - 0.31, z0 + 0.07 + k * 0.13), (cx + 0.31, cy + 0.31, z0 + 0.10 + k * 0.13), "boards", pin=False, axis="x")
    bx(b, (-0.30, -0.06, 0.97), (0.30, 0.20, 1.0), "boards", pin=False, axis="x")
    return done(ctx, b, "SM_Sq_Crates_Stack", M, ground=True, cover_height=1.0, expect_size=(None, None, None),
                notes="Timber crates stacked on a pallet, 1.3 x 1.4 x 1.0 (the data's crate_stack): six slatted crates in two layers. "
                      "Pivot: centre, ground.")


def m_hoarding(ctx, M):
    """Construction hoarding 0.35 x 6.0 x 2.4 (the data's hoarding, along the facade at x -7.95): plywood panels on 10 cm posts
    with a rail at the top and a kicker, a pedestrian light bar at 2.2 (dark), a door. Pivot: centre, ground; long along Y."""
    b = B(951, step=0.6)
    for y in np.linspace(-3.0, 3.0, 5):
        bx(b, (-0.175, y - 0.05, 0.0), (0.175, y + 0.05, 2.40), "boards", pin=False, axis="z")
    for i in range(4):
        y0 = -3.0 + i * 1.5
        bx(b, (-0.04, y0 + 0.05, 0.10), (0.04, y0 + 1.45, 2.30), "plywood", ch=0.004, axis="z")
    for z in (0.30, 1.20, 2.30):
        bx(b, (-0.175, -3.0, z - 0.04), (0.175, 3.0, z + 0.04), "boards", pin=False, axis="y")
    bx(b, (-0.19, -3.0, 0.0), (0.19, 3.0, 0.10), "black", pin=False, axis="y")
    bx(b, (-0.19, -3.0, 2.30), (0.19, 3.0, 2.40), "black", pin=False, axis="y")
    return done(ctx, b, "SM_Sq_Hoarding_6m", M, ground=True, cover_height=2.4, expect_size=(None, None, None),
                notes="Hoarding 0.35 x 6.0 x 2.4 (the data's hoarding along the facade at x -7.95, z -20..-14): plywood panels on posts, "
                      "rails, a kicker and a cap. Blank (no bills, no words). Pivot: centre, ground; long along Y.")


def m_trashcan(ctx, M):
    """A street litter basket 0.60 x 0.60 x 0.99 (the data's trash_can, twenty): a steel drum on a base ring with a rolled rim and
    six 6 cm bands, a dark liner and a little litter in the mouth. It replaces the Block's wire basket (17k triangles, 20 placed:
    300k in the start view) with a lighter one of the same size. Pivot: centre, ground."""
    b = B(955, step=0.4)
    rod(b, (0, 0, 0.0), (0, 0, 0.10), 0.26, "standBlack", n=18)
    p = geo.revolve([(0.0, 0.10), (0.25, 0.10), (0.285, 0.16), (0.295, 0.80), (0.0, 0.80)], 20)
    b.absorb(p, "standGrey")
    rod(b, (0, 0, 0.80), (0, 0, 0.86), 0.315, "galv", n=22)
    for a in range(6):
        t = math.radians(30 + 60 * a)
        bx(b, (0.286 * math.cos(t) - 0.03, 0.286 * math.sin(t) - 0.03, 0.18), (0.286 * math.cos(t) + 0.03, 0.286 * math.sin(t) + 0.03, 0.80), "standBlack",
           pin=False, axis="z")
    rod(b, (0, 0, 0.74), (0, 0, 0.82), 0.26, "interior", n=18)
    dome(b, (0.0, 0.0, 0.78), 0.24, "plasticBlack", squash=0.22, seg=14, rings=4)
    for (x, y, z, w_) in ((0.08, -0.06, 0.86, 0.10), (-0.10, 0.05, 0.85, 0.12), (0.02, 0.12, 0.86, 0.09)):
        bx(b, (x - w_ / 2, y - w_ / 2, z), (x + w_ / 2, y + w_ / 2, z + 0.06), ["white", "yellow", "umbrella"][int(abs(x) * 20) % 3], pin=False)
    return done(ctx, b, "SM_Sq_TrashCan", M, ground=True, cover_height=0.99, expect_size=(None, None, None),
                notes="Litter basket 0.60 x 0.60 x 0.99 (the data's trash_can, twenty): a steel drum on a base ring, a rolled rim, six 6 cm "
                      "bands, a dark liner with a little litter. Replaces the Block's 17k-triangle wire basket on the Midtown placements. "
                      "Pivot: centre, ground.")


def m_sawhorse(ctx, M):
    """A crowd-control sawhorse barrier 1.8 x 0.5 x 1.0 (no agency mark): white and orange striped boards on an A-frame; the
    midtown.md 12.4 leftover. Dressing, no collider. Pivot: centre, ground; long along X."""
    b = B(952, step=0.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            R.bar(b, (sx * 0.75 + sy * 0.0, sy * 0.25, 0.0), (sx * 0.75, 0.0, 0.95), 0.06, 0.06, "black", ch=0.004)
    tube(b, (-0.75, 0.0, 0.92), (0.75, 0.0, 0.92), "black", 0.03)
    for z in (0.50, 0.82):
        for k in range(6):
            x0 = -0.90 + k * 0.30
            bx(b, (x0, -0.03, z), (x0 + 0.30, 0.03, z + 0.14), "white" if k % 2 else "orange", pin=False, axis="x")
    return done(ctx, b, "SM_Sq_Sawhorse", M, ground=True, cover_height=1.0, expect_size=(None, None, None),
                notes="Sawhorse barrier 1.8 x 0.5 x 1.0 (no agency mark): striped boards on an A-frame. Leftover dressing (midtown.md "
                      "12.4), no collider. Pivot: centre, ground.")


def m_fansign(ctx, M):
    """A fan's cardboard sign dropped on the plaza, 0.7 x 0.5 (midtown.md 12.4): a blank cardboard sheet on a stick lying
    askew. Dressing, no collider, no words. Pivot: centre, ground."""
    b = B(953, step=0.3)
    bx(b, (-0.35, -0.25, 0.0), (0.35, 0.25, 0.012), "boards", pin=False, axis="x")
    bx(b, (-0.32, -0.05, 0.012), (0.32, 0.05, 0.03), "plywood", pin=False, axis="x")
    bx(b, (0.30, -0.03, 0.0), (1.1, 0.03, 0.06), "boards", pin=False, axis="x")
    return done(ctx, b, "SM_Sq_FanSign", M, ground=True, expect_size=(None, None, None),
                notes="A fan's cardboard sign on a stick, lying on the plaza (blank). Leftover dressing (midtown.md 12.4), no collider. "
                      "Pivot: the sheet's centre, ground.")


PROPS = [m_bar, m_lounger, m_lounger_stack, m_umbrella, m_planterbox, m_loftlark_neon,
         lambda c, M: m_deck(c, M, "lounge"), lambda c, M: m_deck(c, M, "dunnage"),
         m_duct, m_ventbox, m_conduitbox, m_conduitrun, m_sleepers, m_fan,
         m_bollard_planter, m_newsstand, m_phonekiosk, m_pylon, m_atm, m_standpipe, m_valet, m_luggage, m_crates, m_hoarding,
         m_sawhorse, m_fansign, m_trashcan]
