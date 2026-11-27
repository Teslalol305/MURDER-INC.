"""Canal Street round 3, part 2: the interior props (chinatown_art.md 6): the Moon Gate bakery and its kitchen, the dub room, the neon
workshop and the banquet hall with its stage. Each is a module at its collider's size or an exact divisor of it (the placements tile
a module along the collider's long side), pivot at the footprint's centre on the floor, forward +X, so nothing is scaled.

    bakery        SM_Prop_CT_BakeryCounter (2.3 m, two tile a 4.6 m run), BakeryOven (1.6 m deck oven), TrayRack (0.8 m trolley), FlourSacks
    kitchen       SM_Prop_CT_KitchenTable (1.9 m), KitchenRange (1.5 m wok range), KitchenCounter (2.0 m), KitchenRack (0.8 m wire shelf)
    dub room      SM_Prop_CT_TapeRack (1.7 m), CuttingTable (the record-cutting lathe), DiscBurners (the duplicator tower)
    neon workshop SM_Prop_CT_KioskCounter, TubeBundles, BendingBench
    banquet hall  SM_Prop_CT_BanquetTable (a round table of 1.7 m with a cloth, a turntable and ten settings), BanquetStage (2.8 x 7.8 x 0.5 m)
"""
import math

import numpy as np

from assets._chinatown_kit import bar, bx, crate, rod
from assets._chinatown_props3 import blob, cyl, fin, ring
from assets._chinatown_kit import ball, lathe
from assets.facade import B, sheet, sub as fsub


def m_bakery_counter(ctx, M):
    """Bakery display counter 2.3 x 1.0 x 1.0: a tiled carcass, a glass case with three shelves of buns and loaves, a till plate."""
    b = B(400, step=0.5)
    rng = ctx.rng("bakerycounter")
    L, W = 2.3, 0.9
    bx(b, (-L / 2, -W / 2, 0.0), (L / 2, W / 2, 0.14), "black", ch=0.004)
    bx(b, (-L / 2, -W / 2, 0.14), (L / 2, W / 2, 0.88), "tile", ch=0.004)
    bx(b, (-L / 2 - 0.02, -W / 2 - 0.02, 0.88), (L / 2 + 0.02, W / 2 + 0.02, 0.92), "stainless", ch=0.004)
    for x in (-L / 2 + 0.04, 0.0, L / 2 - 0.04):
        for y in (-W / 2 + 0.05, W / 2 - 0.05):
            rod(b, (x, y, 0.92), (x, y, 1.20), 0.018, "chrome", n=6)
    bx(b, (-L / 2 + 0.03, -W / 2 + 0.03, 1.20), (L / 2 - 0.03, W / 2 - 0.03, 1.23), "glasswin", pin=False)
    for s in (-1, 1):
        bx(b, (-L / 2 + 0.03, s * (W / 2 - 0.04) - 0.006, 0.96), (L / 2 - 0.03, s * (W / 2 - 0.04) + 0.006, 1.19), "glasswin", pin=False)
    for z in (0.92, 1.06):
        bx(b, (-L / 2 + 0.05, -W / 2 + 0.10, z), (L / 2 - 0.05, W / 2 - 0.10, z + 0.012), "stainless", pin=False)
        for i in range(8):
            x = -L / 2 + 0.16 + i * 0.28
            kind = int(rng.integers(0, 3))
            if kind == 0:                                                                                   # a tray of buns
                for k in range(3):
                    for j in range(2):
                        blob(b, (x - 0.08 + k * 0.08, -0.12 + j * 0.22 + 0.0, z + 0.04), 0.04, "grain", seg=8, rings=5, squash=(1, 1, 0.85))
            elif kind == 1:                                                                                 # loaves
                for j in range(2):
                    blob(b, (x, -0.18 + j * 0.36, z + 0.05), 0.07, "ply", seg=8, rings=5, squash=(1.5, 0.8, 0.8))
            else:                                                                                           # egg tarts: yellow discs in a tray
                for k in range(3):
                    cyl(b, (x - 0.08 + k * 0.08, 0.0, z + 0.012), 0.035, 0.03, "yellow", seg=8)
    bx(b, (L / 2 - 0.32, -0.06, 0.92), (L / 2 - 0.04, 0.22, 0.99), "black", ch=0.008)                      # a till, blank
    return fin(ctx, b, "SM_Prop_CT_BakeryCounter", M, "Moon Gate Bakery display counter 2.3 x 0.9 x 1.23 m (two make the 4.6 m run, x 0.4..5.0): a white-tile carcass, a "
               "stainless top, a glass case on chrome posts with two shelves of buns, loaves and egg tarts, a till. Customer side toward -Y.", cover=1.0)


def m_bakery_oven(ctx, M):
    """Three-deck bakery oven 1.6 x 1.2 x 1.75 on a steel stand with a flue hood."""
    b = B(401, step=0.5)
    L, W = 1.6, 1.2
    for x in (-L / 2 + 0.05, L / 2 - 0.05):
        for y in (-W / 2 + 0.06, W / 2 - 0.06):
            rod(b, (x, y, 0.0), (x, y, 0.45), 0.025, "black", n=6)
    bx(b, (-L / 2, -W / 2, 0.45), (L / 2, W / 2, 0.50), "black", ch=0.004)
    for k in range(3):
        z0 = 0.50 + k * 0.40
        bx(b, (-L / 2, -W / 2, z0), (L / 2, W / 2, z0 + 0.38), "stainless", ch=0.008)
        bx(b, (-L / 2 + 0.08, -W / 2 - 0.02, z0 + 0.05), (L / 2 - 0.08, -W / 2, z0 + 0.32), "black", ch=0.006)     # the door
        bx(b, (-L / 2 + 0.16, -W / 2 - 0.025, z0 + 0.10), (L / 2 - 0.16, -W / 2 - 0.018, z0 + 0.27), "glasswin", pin=False)
        rod(b, (-L / 2 + 0.16, -W / 2 - 0.07, z0 + 0.33), (L / 2 - 0.16, -W / 2 - 0.07, z0 + 0.33), 0.016, "chrome", n=6)
        for s in (-1, 1):
            bx(b, (s * (L / 2 - 0.08) - 0.02, -W / 2 - 0.05, z0 + 0.30), (s * (L / 2 - 0.08) + 0.02, -W / 2 - 0.0, z0 + 0.33), "chrome", pin=False)
    bx(b, (-L / 2 + 0.05, -W / 2 + 0.10, 1.70), (L / 2 - 0.05, W / 2 - 0.10, 1.75), "stainless", ch=0.006)
    bx(b, (-0.12, -W / 2 + 0.08, 1.74), (0.12, -W / 2 + 0.32, 1.75), "black", pin=False)
    for i in range(4):                                                                                      # dial knobs
        cyl(b, (-0.45 + i * 0.30, -W / 2 - 0.05, 0.62 - 0.06), 0.028, 0.045, "black", seg=8, axis="Y")
    return fin(ctx, b, "SM_Prop_CT_BakeryOven", M, "Three-deck bakery oven 1.6 x 1.2 x 1.75 m (two make the 3.2 m run along the kitchen's east side, x 6.4): a stainless "
               "body on a black stand, black doors with glass and chrome handles, dials. Doors toward -Y.", cover=1.2)


def m_tray_rack(ctx, M):
    """Bakery tray trolley 0.8 x 0.8 x 1.75: eleven slides, six trays of buns, four castors."""
    b = B(402, step=0.5)
    rng = ctx.rng("trayrack")
    for x in (-0.36, 0.36):
        for y in (-0.36, 0.36):
            rod(b, (x, y, 0.10), (x, y, 1.72), 0.018, "alu", n=6)
            cyl(b, (x, y, 0.0), 0.05, 0.10, "rubber", seg=8)
    for z in (0.12, 1.70):
        bx(b, (-0.38, -0.38, z), (0.38, 0.38, z + 0.03), "alu", pin=False)
    for k in range(6):
        z = 0.30 + k * 0.24
        for y in (-0.36, 0.36):
            bx(b, (-0.38, y - 0.012, z), (0.38, y + 0.012, z + 0.03), "alu", pin=False)
        bx(b, (-0.34, -0.31, z + 0.03), (0.34, 0.31, z + 0.045), "black", pin=False)
        for i in range(3):
            for j in range(4):
                blob(b, (-0.24 + i * 0.24, -0.22 + j * 0.147, z + 0.08), 0.05, "grain" if (i + j + k) % 3 else "ply", seg=8, rings=5, squash=(1, 1, 0.8))
    return fin(ctx, b, "SM_Prop_CT_TrayRack", M, "Bakery tray trolley 0.8 x 0.8 x 1.75 m (four make the 3.2 m run, x 0.4): aluminium posts, six trays of buns, castors.", cover=1.0)


def m_flour_sacks(ctx, M):
    """A stack of burlap flour sacks 0.7 x 0.6 x 0.9: two rows of two on a pallet board, a sack on top."""
    b = B(403, step=0.5)
    bx(b, (-0.35, -0.30, 0.0), (0.35, 0.30, 0.10), "pallet", ch=0.004, pin=False)
    for k, (x, y, z, rz) in enumerate(((-0.17, -0.14, 0.10, 0), (0.17, -0.14, 0.10, 8), (-0.17, 0.14, 0.10, -6), (0.17, 0.14, 0.10, 3),
                                       (0.0, 0.0, 0.30, 90), (-0.12, 0.0, 0.50, 20))):
        blob(b, (x, y, z + 0.10), 0.20 if k < 5 else 0.18, "burlap" if k % 2 else "clothLight", seg=8, rings=6, squash=(0.85, 0.65, 0.5), rot=rz)
    return fin(ctx, b, "SM_Prop_CT_FlourSacks", M, "Burlap flour sacks 0.7 x 0.6 x 0.9 m on a board (the bakery's two stacks, x 0.5 and 6.6).", cover=0.8)


def m_kitchen_table(ctx, M):
    """Stainless prep table 1.9 x 1.4 x 0.9 with an under-shelf, a back lip, a rolling pin and a bowl of dough."""
    b = B(404, step=0.5)
    L, W = 1.9, 1.4
    for x in (-L / 2 + 0.05, L / 2 - 0.05):
        for y in (-W / 2 + 0.05, W / 2 - 0.05):
            rod(b, (x, y, 0.0), (x, y, 0.86), 0.022, "stainless", n=6)
    bx(b, (-L / 2, -W / 2, 0.86), (L / 2, W / 2, 0.90), "stainless", ch=0.004)
    bx(b, (-L / 2 + 0.03, -W / 2 + 0.03, 0.20), (L / 2 - 0.03, W / 2 - 0.03, 0.23), "stainless", ch=0.003)
    for s in (-1, 1):
        bx(b, (-L / 2, s * W / 2 - 0.02, 0.86), (L / 2, s * W / 2 + 0.02, 0.94), "stainless", pin=False) if s > 0 else None
    rod(b, (-0.30, 0.20, 0.925), (0.30, 0.20, 0.925), 0.02, "timber", n=8)
    lathe(b, [(0.0, 0.90), (0.12, 0.90), (0.17, 1.00), (0.0, 1.00)], "stainless", loc=(0.55, -0.20, 0.0), seg=12)
    blob(b, (0.55, -0.20, 1.0), 0.15, "clothLight", seg=8, rings=4, squash=(1, 1, 0.5))
    bx(b, (-0.70, -0.40, 0.90), (-0.10, 0.05, 0.915), "clothLight", pin=False)                              # floured board
    return fin(ctx, b, "SM_Prop_CT_KitchenTable", M, "Stainless prep table 1.9 x 1.4 x 0.9 m (two make the 3.8 m run in the bakery kitchen, x 3.6): legs, an under-shelf, a "
               "back lip, a rolling pin, a bowl of dough, a floured board.", cover=0.9)


def m_kitchen_range(ctx, M):
    """Wok range 1.5 x 0.8 x 0.85: a stainless cabinet with two wok burners, a woks' water tap and a back splash."""
    b = B(405, step=0.5)
    L, W = 1.5, 0.8
    bx(b, (-L / 2, -W / 2, 0.0), (L / 2, W / 2, 0.78), "stainless", ch=0.006)
    bx(b, (-L / 2 + 0.05, -W / 2 - 0.01, 0.08), (L / 2 - 0.05, -W / 2 + 0.01, 0.70), "black", pin=False)
    bx(b, (-L / 2, -W / 2, 0.78), (L / 2, W / 2, 0.82), "black", ch=0.004)
    for x in (-0.38, 0.38):
        lathe(b, [(0.0, 0.82), (0.22, 0.82), (0.24, 0.85), (0.17, 0.85), (0.0, 0.84)], "black", loc=(x, 0.0, 0.0), seg=14)
        lathe(b, [(0.0, 0.84), (0.20, 0.87), (0.25, 0.97), (0.22, 0.97), (0.17, 0.90), (0.0, 0.88)], "alu", loc=(x, 0.0, 0.0), seg=16)
        rod(b, (x - 0.30, -W / 2 + 0.10, 0.90), (x - 0.22, -W / 2 + 0.10, 0.95), 0.016, "black", n=5)
    bx(b, (-L / 2, W / 2 - 0.05, 0.82), (L / 2, W / 2, 1.30), "stainless", ch=0.004)
    rod(b, (-0.02, W / 2 - 0.08, 1.05), (-0.02, 0.10, 1.05), 0.018, "chrome", n=6)
    for i in range(4):
        cyl(b, (-0.60 + i * 0.4, -W / 2 - 0.05, 0.62), 0.03, 0.05, "black", seg=8, axis="Y")
    return fin(ctx, b, "SM_Prop_CT_KitchenRange", M, "Wok range 1.5 x 0.8 x 1.3 m (two make the 3.0 m line at the banquet kitchen's north wall): a stainless cabinet, a black "
               "top with two wok burners and woks, a back splash with a tap, four gas knobs. Knobs toward -Y.", cover=0.9)


def m_kitchen_counter(ctx, M):
    """Stainless counter 2.0 x 0.8 x 0.85 with a sink, an under-shelf and a splashback."""
    b = B(406, step=0.5)
    L, W = 2.0, 0.8
    for x in (-L / 2 + 0.05, L / 2 - 0.05):
        for y in (-W / 2 + 0.05, W / 2 - 0.05):
            rod(b, (x, y, 0.0), (x, y, 0.82), 0.022, "stainless", n=6)
    bx(b, (-L / 2, -W / 2, 0.82), (L / 2, W / 2, 0.85), "stainless", ch=0.004)
    bx(b, (-L / 2 + 0.03, -W / 2 + 0.03, 0.20), (L / 2 - 0.03, W / 2 - 0.03, 0.23), "stainless", pin=False)
    bx(b, (-L / 2, W / 2 - 0.03, 0.85), (L / 2, W / 2, 1.05), "stainless", ch=0.004)
    bx(b, (-0.35, -0.28, 0.78), (0.35, 0.26, 0.82), "black", pin=False)                                      # the sink well (dark)
    rod(b, (0.0, W / 2 - 0.06, 0.85), (0.0, W / 2 - 0.06, 1.15), 0.016, "chrome", n=6)
    rod(b, (0.0, W / 2 - 0.06, 1.15), (0.0, 0.18, 1.15), 0.016, "chrome", n=6)
    return fin(ctx, b, "SM_Prop_CT_KitchenCounter", M, "Stainless counter with a sink 2.0 x 0.8 x 0.85 m (the banquet kitchen's east wall): an under-shelf, a splashback, a gooseneck tap.", cover=0.9)


def m_kitchen_rack(ctx, M):
    """Wire pot rack 0.8 x 0.6 x 1.6: four shelves of pots, a ladle on a hook."""
    b = B(407, step=0.5)
    for x in (-0.36, 0.36):
        for y in (-0.26, 0.26):
            rod(b, (x, y, 0.0), (x, y, 1.60), 0.019, "chrome", n=6)
    for k, z in enumerate((0.20, 0.62, 1.04, 1.46)):
        bx(b, (-0.38, -0.28, z), (0.38, 0.28, z + 0.02), "chrome", pin=False)
        for i in range(2):
            lathe(b, [(0.0, 0.0), (0.12, 0.0), (0.13, 0.16 - 0.03 * k * 0.4), (0.0, 0.16 - 0.03 * k * 0.4)], "alu", loc=(-0.18 + i * 0.36, 0.0, z + 0.02), seg=10)
    return fin(ctx, b, "SM_Prop_CT_KitchenRack", M, "Chrome wire shelf 0.8 x 0.6 x 1.6 m with four shelves of aluminium pots (two in the banquet kitchen).", cover=1.2)


def m_tape_rack(ctx, M):
    """Dub room equipment rack 1.0 x 1.7 x 2.0: a black steel frame with five shelves of reel-to-reel and cassette decks, patch cords."""
    b0 = B(408, step=0.5)
    b = b0
    rng = ctx.rng("taperack")
    L, W = 1.0, 1.7
    for x in (-L / 2 + 0.03, L / 2 - 0.03):
        for y in (-W / 2 + 0.03, W / 2 - 0.03):
            rod(b, (x, y, 0.0), (x, y, 2.0), 0.02, "black", n=6)
    for z in (0.05, 0.50, 0.95, 1.40, 1.85):
        bx(b, (-L / 2, -W / 2, z), (L / 2, W / 2, z + 0.03), "black", ch=0.003)
    for k, z in enumerate((0.08, 0.53, 0.98, 1.43)):
        for j in range(2):
            y0 = -W / 2 + 0.06 + j * 0.80
            bx(b, (-0.40, y0, z), (0.45, y0 + 0.74, z + 0.34), "trim", ch=0.006)
            bx(b, (0.45, y0 + 0.04, z + 0.03), (0.47, y0 + 0.70, z + 0.31), "black", pin=False)
            if k % 2 == 0:                                                                                  # a reel-to-reel: two reels and a head block
                for yy in (y0 + 0.17, y0 + 0.57):
                    cyl(b, (0.47, yy, z + 0.17), 0.11, 0.012, "alu", seg=14, axis="X")
                    cyl(b, (0.47, yy, z + 0.17), 0.03, 0.025, "black", seg=8, axis="X")
            else:
                for yy in (y0 + 0.20, y0 + 0.54):
                    bx(b, (0.45, yy - 0.06, z + 0.12), (0.475, yy + 0.06, z + 0.20), "glasswin", pin=False)
    for j in range(6):                                                                                      # patch cords hanging
        rod(b, (0.50, -0.7 + j * 0.28, 1.76), (0.54, -0.7 + j * 0.28 + 0.05, 1.45 - 0.02 * j), 0.010, "plastic", n=4)
    b = B(408, step=0.5)
    fsub(b, b0, -90.0)                                                                                      # long side along X, fronts toward -Y
    return fin(ctx, b, "SM_Prop_CT_TapeRack", M, "Dub room equipment rack 1.7 x 1.0 x 2.0 m (two make the 3.4 m wall, x 18.4): a black steel frame, five shelves, reel-to-reel and "
               "cassette decks with their reels, patch cords. Long side along X, fronts toward -Y.", cover=None)


def m_cutting_table(ctx, M):
    """Record-cutting table 1.6 x 2.0 x 0.9 (the dub room): a heavy bench, a lathe platter with a tonearm and a head, a mixer."""
    b = B(409, step=0.5)
    L, W = 2.0, 1.6
    for x in (-L / 2 + 0.06, L / 2 - 0.06):
        for y in (-W / 2 + 0.06, W / 2 - 0.06):
            rod(b, (x, y, 0.0), (x, y, 0.84), 0.03, "black", n=6)
    bx(b, (-L / 2, -W / 2, 0.84), (L / 2, W / 2, 0.90), "timber", ch=0.006)
    bx(b, (-L / 2 + 0.04, -W / 2 + 0.04, 0.22), (L / 2 - 0.04, W / 2 - 0.04, 0.25), "ply", pin=False)
    cyl(b, (-0.30, 0.0, 0.90), 0.34, 0.10, "trim", seg=24)
    cyl(b, (-0.30, 0.0, 1.00), 0.31, 0.012, "black", seg=24)
    cyl(b, (-0.30, 0.0, 1.012), 0.015, 0.03, "chrome", seg=8)
    bx(b, (0.10, -0.60, 0.90), (0.40, -0.30, 1.04), "trim", ch=0.008)
    rod(b, (0.25, -0.45, 1.04), (-0.05, -0.05, 1.10), 0.02, "chrome", n=6)
    bx(b, (-0.12, -0.08, 1.07), (-0.02, 0.02, 1.12), "black", pin=False)
    bx(b, (0.55, -0.35, 0.90), (0.95, 0.35, 1.02), "black", ch=0.008)                                      # mixer
    for i in range(8):
        cyl(b, (0.65 + (i % 4) * 0.07, -0.15 + (i // 4) * 0.2, 1.02), 0.018, 0.02, "chrome", seg=6)
    return fin(ctx, b, "SM_Prop_CT_CuttingTable", M, "Record-cutting table 2.0 x 1.6 x 1.1 m (the dub room, x 22.2, z 20.4): a timber bench, a lathe platter with a stylus arm, "
               "a mixer with knobs. Long side along +X.", cover=0.9)


def m_disc_burners(ctx, M):
    """Disc duplicator tower 0.8 x 0.8 x 1.65: a stack of ten drive units on a wheeled stand."""
    b = B(410, step=0.5)
    for x in (-0.34, 0.34):
        for y in (-0.34, 0.34):
            rod(b, (x, y, 0.08), (x, y, 1.62), 0.02, "black", n=6)
            cyl(b, (x, y, 0.0), 0.04, 0.08, "rubber", seg=8)
    for k in range(10):
        z = 0.16 + k * 0.145
        bx(b, (-0.36, -0.34, z), (0.36, 0.34, z + 0.13), "trim", ch=0.004)
        bx(b, (0.36, -0.28, z + 0.02), (0.375, 0.28, z + 0.11), "black", pin=False)
        bx(b, (0.375, -0.20, z + 0.05), (0.385, 0.05, z + 0.065), "plastic", pin=False)
        blob(b, (0.38, 0.17, z + 0.09), 0.012, "orange" if k % 3 == 0 else "plasticGreen", seg=4, rings=3)
    return fin(ctx, b, "SM_Prop_CT_DiscBurners", M, "Disc duplicator tower 0.8 x 0.8 x 1.65 m (the dub room, x 24.6, z 18.6): ten drive units with blank trays and status lamps on a "
               "wheeled stand. Fronts toward +X.", cover=None)


def m_kiosk_counter(ctx, M):
    """The sign-repair kiosk counter 1.0 x 1.0 x 0.95: a steel counter with a glass tube rack and a stool."""
    b = B(411, step=0.5)
    bx(b, (-0.50, -0.50, 0.0), (0.50, 0.50, 0.90), "grey", ch=0.008)
    bx(b, (-0.52, -0.52, 0.90), (0.52, 0.52, 0.95), "stainless", ch=0.004)
    for i in range(3):
        rod(b, (-0.38 + i * 0.38, -0.42, 0.95), (-0.38 + i * 0.38, -0.42, 1.18), 0.02, "neonWhite", n=6)
    bx(b, (-0.45, -0.46, 1.18), (0.45, -0.38, 1.21), "black", pin=False)
    bx(b, (0.10, 0.10, 0.95), (0.40, 0.40, 1.05), "black", ch=0.006)
    return fin(ctx, b, "SM_Prop_CT_KioskCounter", M, "Sign-repair kiosk counter 1.0 x 1.0 x 1.2 m (the NEON SIGNS kiosk, x 32.6): a steel carcass, a stainless top, three white "
               "tube samples on a rail, a transformer box.", cover=0.95)


def m_tube_bundles(ctx, M):
    """Glass tube bundles 0.8 x 0.8 x 0.85 on a stand: forty clear tubes in a timber cradle."""
    b = B(412, step=0.5)
    rng = ctx.rng("tubebundles")
    for x in (-0.30, 0.30):
        bx(b, (x - 0.03, -0.38, 0.0), (x + 0.03, 0.38, 0.45), "timber", ch=0.004)
    bx(b, (-0.36, -0.38, 0.0), (0.36, -0.32, 0.45), "timber", pin=False)
    bx(b, (-0.36, 0.32, 0.0), (0.36, 0.38, 0.45), "timber", pin=False)
    for i in range(5):
        for j in range(4):
            if (i + j) % 7 == 6:
                continue
            y = -0.25 + i * 0.125
            z = 0.52 + j * 0.095
            rod(b, (-0.38, y, z), (0.38 + rng.uniform(-0.05, 0.05), y, z), 0.021, "glasswin" if (i + j) % 2 else "neonWhite", n=8)
    return fin(ctx, b, "SM_Prop_CT_TubeBundles", M, "Bundles of glass tubing 0.8 x 0.8 x 0.85 m in a timber cradle (the neon workshop, x 34.2): 18 tubes of 42 mm (the lane's thin-member "
               "floor) alternating clear and phosphor white.", cover=0.8)


def m_bending_bench(ctx, M):
    """Neon bending bench 2.0 x 0.8 x 0.8: a steel bench with a ribbon burner, a gas hose, a transformer, a half-bent tube on a former."""
    b = B(413, step=0.5)
    L, W = 2.0, 0.8
    for x in (-L / 2 + 0.06, L / 2 - 0.06):
        for y in (-W / 2 + 0.05, W / 2 - 0.05):
            rod(b, (x, y, 0.0), (x, y, 0.76), 0.028, "trim", n=6)
    bx(b, (-L / 2, -W / 2, 0.76), (L / 2, W / 2, 0.80), "grey", ch=0.004)
    bx(b, (-L / 2 + 0.05, -W / 2 + 0.05, 0.25), (L / 2 - 0.05, W / 2 - 0.05, 0.28), "grey", pin=False)
    bx(b, (-0.60, -0.08, 0.80), (0.20, 0.08, 0.86), "black", ch=0.004)                                      # the ribbon burner
    rod(b, (-0.60, 0.0, 0.88), (0.20, 0.0, 0.88), 0.022, "apple", n=6)                                      # the flame bar (glowing)
    rod(b, (0.25, -0.20, 0.835), (0.85, -0.20, 0.835), 0.021, "neonWhite", n=8)
    rod(b, (0.85, -0.20, 0.835), (0.85, 0.15, 0.835), 0.021, "neonWhite", n=8)
    rod(b, (0.85, 0.15, 0.835), (0.45, 0.15, 0.835), 0.021, "neonWhite", n=8)
    bx(b, (0.55, 0.05, 0.80), (0.92, 0.35, 0.82), "ply", ch=0.003)                                          # the pattern board
    bx(b, (-0.90, 0.10, 0.80), (-0.60, 0.34, 1.02), "black", ch=0.008)                                      # transformer
    for i in range(3):
        cyl(b, (-0.84 + i * 0.09, 0.22, 1.02), 0.025, 0.04, "chrome", seg=6)
    rod(b, (-0.62, 0.0, 0.87), (-0.95, -0.28, 0.45), 0.02, "plastic", n=6)
    return fin(ctx, b, "SM_Prop_CT_BendingBench", M, "Neon bending bench 2.0 x 0.8 x 1.0 m (BIG LIGHT SIGNS' workshop, x 35.4): a steel bench, a ribbon burner with a gas hose, a "
               "transformer with knobs, a half-bent white tube on its pattern board.", cover=0.8)


def m_banquet_table(ctx, M):
    """Round banquet table 1.7 m across, 0.8 high, with a red cloth, a glass turntable and ten settings (no chairs: they are the stacks)."""
    b = B(414, step=0.5)
    r = 0.85
    lathe(b, [(0.0, 0.0), (0.30, 0.0), (0.34, 0.05), (0.12, 0.10), (0.10, 0.60), (0.0, 0.60)], "black", seg=14)
    lathe(b, [(0.0, 0.60), (r, 0.76), (r + 0.01, 0.79), (r - 0.02, 0.795), (0.0, 0.795)], "fabricRed", seg=28)
    lathe(b, [(0.0, 0.795), (0.44, 0.795), (0.44, 0.81), (0.0, 0.81)], "glasswin", seg=20)
    for a in range(10):
        t = a * 2 * math.pi / 10
        c = (0.58 * math.cos(t), 0.58 * math.sin(t))
        lathe(b, [(0.0, 0.795), (0.09, 0.795), (0.10, 0.805), (0.0, 0.805)], "fabricWhite", loc=(c[0], c[1], 0.0), seg=10)
        ball(b, 0.025, (c[0] * 1.14, c[1] * 1.14, 0.82), "clothLight", seg=6, rings=4)
    for a in range(3):                                                                                     # dishes on the turntable
        t = a * 2 * math.pi / 3
        lathe(b, [(0.0, 0.81), (0.08, 0.81), (0.10, 0.84), (0.0, 0.84)], "fabricWhite", loc=(0.2 * math.cos(t), 0.2 * math.sin(t), 0.0), seg=10)
    return fin(ctx, b, "SM_Prop_CT_BanquetTable", M, "Round banquet table 1.7 m across, 0.84 high (seven in the hall, x 28.6..36.6): a pedestal, a red cloth to the floor's edge, a "
               "glass turntable with three dishes and ten plates with cups.", cover=0.8)


def m_banquet_stage(ctx, M):
    """The banquet hall's stage 2.8 x 7.8 x 0.5: a carpeted deck on a black skirt, a step at the front, a red curtain backdrop on a rail."""
    b = B(415, step=2.0)
    L, W = 2.8, 7.8
    bx(b, (0.0, 0.0, 0.0), (L, W, 0.46), "black", ch=0.004)
    bx(b, (-0.02, -0.02, 0.46), (L + 0.02, W + 0.02, 0.50), "fabricRed", ch=0.004)
    for y in np.linspace(0.30, W - 0.30, 8):                                                                # a gold edge strip and a skirt crease
        bx(b, (-0.025, y - 0.02, 0.05), (0.0, y + 0.02, 0.44), "gold", pin=False)
    bx(b, (-0.03, 0.0, 0.46), (0.0, W, 0.50), "gold", pin=False)
    xb = L - 0.15
    for y in np.linspace(0.05, W - 0.25, 30):                                                              # the curtain: pleats
        z1 = 4.0
        bx(b, (xb, y, 0.5), (xb + 0.06, y + 0.27, z1), "fabricRed", ch=0.004, pin=False)
    rod(b, (xb, 0.0, 4.05), (xb, W, 4.05), 0.025, "gold", n=8)
    for y in (0.05, W / 2, W - 0.05):
        rod(b, (xb, y, 0.5), (xb, y, 4.05), 0.03, "gold", n=8)
    return fin(ctx, b, "SM_Prop_CT_BanquetStage", M, "Banquet stage 2.8 x 7.8 x 0.5 m deck (x 40.8..43.6, z 18.8..26.6; with its 4 m curtain) at its collider's min corner, "
               "placed at that point: a red carpeted deck on a black skirt, a gold edge, a red pleated curtain on a gold rail.", cover=0.5)


PROPS3B = [m_bakery_counter, m_bakery_oven, m_tray_rack, m_flour_sacks, m_kitchen_table, m_kitchen_range, m_kitchen_counter,
           m_kitchen_rack, m_tape_rack, m_cutting_table, m_disc_burners, m_kiosk_counter, m_tube_bundles, m_bending_bench,
           m_banquet_table, m_banquet_stage]
