"""Canal Street round 3, part 1: the street and alley props the placements could not place before (chinatown_art.md 6).

Each one is built at its collider's size (lane D's `propPlacements`, tools/levels/data/level_chinatown.json), pivot at the centre of
the footprint on the ground (a wall piece: at the foot of the wall, its back on the wall plane's side), forward +X, so the
placements are pure arithmetic (_chinatown_streets.PROPS) and no instance is scaled.

    dumpling cart, hotpot cart, roasted-nut cart       SM_Prop_CT_{DumplingCart, HotpotCart, NutCart}
    stone lions (left and right)                       SM_Prop_CT_StoneLion_{L, R}
    trash bags (a heap and a small heap)               SM_Prop_CT_TrashBags_{L, S}
    fruit stand at the Mott collider (0.8 x 1.0 m)     SM_Prop_CT_FruitStand_Small
    standpipe (siamese connection), bike rack, chair stack, grease bin, light planters, bucket stack, sandwich board,
    CD rack, road plates, dig fence                    SM_Prop_CT_{Standpipe, BikeRack, ChairStack, GreaseBin, Planter_{S,L},
                                                       BucketStack, SandwichBoard, CDRack, RoadPlates, DigFence}
    roof and wall: vent turbine, exhaust fan, exhaust stack, antenna mast
                                                       SM_Prop_CT_{RoofVent, ExhaustFan, ExhaustStack, AntennaMast}
and the hand-built LODs the collapse cannot make (a pallet stack is boards that collapse to slivers):
SM_Furn_PalletStack_A_LOD1 / _LOD2, same slot, size and pivot as the Block's.
"""
import math

import numpy as np

from assets import _chinatown_kit as kit
from assets.facade import B, sheet
from assets._chinatown_kit import SLOT_META, X, Y, Z, ball, bar, bx, crate, done, fill_fruit, frame_box, greens, lathe, rod
from mi import geo


# ------------------------------------------------------------------------------------------------------ small helpers

def cyl(b, c, r, h, slot, seg=12, axis="Z"):
    """Capped cylinder, its base centre at c, standing along `axis`."""
    ob = geo.cylinder(r, h, seg, name="c", axis=axis)
    geo.transform(ob, loc=c)
    return b.absorb(ob, slot)


def ring(b, c, major, minor, slot, axis="Y", seg=20, sm=6):
    """Torus about the point c with its axis along X, Y or Z."""
    ob = geo.torus(major, minor, seg, sm, name="t")
    geo.transform(ob, loc=c, rot={"Z": (0, 0, 0), "Y": (90, 0, 0), "X": (0, 90, 0)}[axis])
    return b.absorb(ob, slot)


def blob(b, c, r, slot, seg=8, rings=5, squash=(1, 1, 1), rot=0.0):
    ob = geo.sphere(1.0, seg, rings)
    geo.transform(ob, loc=c, rot=(0, 0, rot), scale=(r * squash[0], r * squash[1], r * squash[2]))
    return b.absorb(ob, slot)


def fin(ctx, b, name, M, notes, size=None, cover=None, collision="box", **kw):
    return done(ctx, b, name, M, collision=collision, cover_height=cover, expect_size=size, notes=notes, **kw)


# ------------------------------------------------------------------------------------------------------ carts

def cart_wheels(b, x, y, z0, r, M_slot="rubber"):
    for s in (-1, 1):
        ring(b, (x, y + s * 0.30, z0 + r), r - 0.03, 0.03, M_slot, "Y", seg=16, sm=6)
        cyl(b, (x, y + s * 0.30 - 0.015, z0 + r), r - 0.03, 0.03, "chrome", seg=14, axis="Y")
    rod(b, (x, y - 0.30, z0 + r), (x, y + 0.30, z0 + r), 0.018, "chrome", n=6)


def m_dumpling_cart(ctx, M):
    """Dumpling cart 1.4 x 1.0 x 1.25: a stainless cart on two wheels, a gas ring under a stack of three bamboo steamers."""
    b = B(310)
    L, W = 1.4, 0.9
    cart_wheels(b, -0.15, 0.0, 0.0, 0.26)
    bx(b, (-L / 2, -W / 2 + 0.05, 0.28), (L / 2 - 0.30, W / 2 - 0.05, 0.84), "stainless", ch=0.006)           # cabinet
    for s in (-1, 1):
        bx(b, (-L / 2 + 0.06, s * (W / 2 - 0.05) - 0.006, 0.34), (L / 2 - 0.36, s * (W / 2 - 0.05) + 0.006, 0.78), "black", pin=False)  # doors
    bx(b, (-L / 2 - 0.02, -W / 2, 0.84), (L / 2 - 0.28, W / 2, 0.88), "stainless", ch=0.004)               # top
    bx(b, (-L / 2 - 0.02, -W / 2, 0.88), (-L / 2, W / 2, 0.93), "stainless", pin=False)                    # splash lip
    for s in (-1, 1):
        bx(b, (-L / 2 - 0.02, s * W / 2 - 0.01, 0.88), (L / 2 - 0.28, s * W / 2 + 0.01, 0.92), "stainless", pin=False)
    for i in range(3):                                                                                     # the steamer stack
        z = 0.88 + i * 0.12
        lathe(b, [(0.19, z), (0.215, z), (0.215, z + 0.11), (0.19, z + 0.11)], "timber", loc=(-0.28, 0.0, 0.0), seg=14)
        ring(b, (-0.28, 0.0, z + 0.055), 0.215, 0.011, "stem", "Z", seg=14, sm=4)
    lathe(b, [(0.0, 1.22), (0.21, 1.22), (0.235, 1.10), (0.20, 1.10), (0.0, 1.10)], "timber", loc=(-0.28, 0.0, 0.0), seg=14)
    ball(b, 0.035, (-0.28, 0.0, 1.255), "timber", seg=8, rings=4)
    lathe(b, [(0.0, 0.88), (0.10, 0.88), (0.12, 0.92), (0.0, 0.92)], "black", loc=(0.28, 0.0, 0.0), seg=12)  # a wok ring beside it
    lathe(b, [(0.0, 0.92), (0.15, 0.96), (0.19, 1.04), (0.17, 1.04), (0.12, 0.98), (0.0, 0.97)], "alu", loc=(0.28, 0.0, 0.0), seg=14)
    cyl(b, (L / 2 - 0.50, -0.25, 0.28), 0.14, 0.55, "plasticGreen", seg=12)                                # gas bottle under the lip
    for s in (-1, 1):                                                                                      # handle bars
        rod(b, (L / 2 - 0.30, s * 0.34, 0.80), (L / 2 + 0.0, s * 0.36, 0.95), 0.019, "chrome", n=6)
    rod(b, (L / 2, -0.36, 0.95), (L / 2, 0.36, 0.95), 0.019, "chrome", n=6)
    bx(b, (-0.60, -0.12, 0.93), (-0.40, 0.12, 0.945), "ply", ch=0.002, pin=False)                          # tray of dumplings
    for i in range(3):
        blob(b, (0.0 + i * 0.1, 0.0, 0.95), 0.04, "fabricWhite", seg=6, rings=4, squash=(1.2, 1.0, 0.8))
    return fin(ctx, b, "SM_Prop_CT_DumplingCart", M, "Dumpling cart 1.4 x 0.9 x 1.25 m (three on Canal and the market's corner pier: chinatown.md 4.3 and "
               "4.8): a stainless cabinet on two pneumatic wheels, a stack of three bamboo steamers on the gas, a wok ring, a gas bottle, handle bars. "
               "Pivot at the cart's centre, handle toward +X.", cover=1.0)


def m_nut_cart(ctx, M):
    """Roasted-nut cart 1.5 x 0.9 x 1.25: a glass cabinet with a rotating roasting drum, brass trim, two wheels."""
    b = B(311)
    L, W = 1.5, 0.9
    cart_wheels(b, 0.0, 0.0, 0.0, 0.27)
    bx(b, (-L / 2, -W / 2 + 0.05, 0.30), (L / 2 - 0.35, W / 2 - 0.05, 0.80), "redlac", ch=0.006)           # red cabinet
    bx(b, (-L / 2 - 0.02, -W / 2, 0.80), (L / 2 - 0.33, W / 2, 0.84), "stainless", ch=0.004)
    for s in (-1, 1):                                                                                      # glass case on top, brass posts
        bx(b, (-L / 2 + 0.02, s * (W / 2 - 0.06) - 0.01, 0.84), (L / 2 - 0.38, s * (W / 2 - 0.06) + 0.01, 1.18), "glasswin", pin=False)
    bx(b, (-L / 2 + 0.02, -W / 2 + 0.05, 1.18), (L / 2 - 0.36, W / 2 - 0.05, 1.22), "redlac", ch=0.004)
    for x in (-L / 2 + 0.03, L / 2 - 0.40):
        for s in (-1, 1):
            rod(b, (x, s * (W / 2 - 0.06), 0.84), (x, s * (W / 2 - 0.06), 1.18), 0.018, "gold", n=6)
    drum = geo.cylinder(0.20, 0.55, 14, name="drum", axis="Y")
    geo.transform(drum, loc=(-0.20, -0.275, 1.02))
    b.absorb(drum, "alu")
    for a in range(6):
        t = a * math.pi / 3
        rod(b, (-0.20, -0.30, 1.02), (-0.20 + 0.19 * math.cos(t), -0.30, 1.02 + 0.19 * math.sin(t)), 0.018, "gold", n=5)
    for i in range(14):                                                                                    # nuts lying on the floor of the case
        blob(b, (-0.62 + 0.09 * (i % 7) + 0.03 * (i // 7), -0.2 + 0.16 * (i // 7), 0.875), 0.035, "timber", seg=6, rings=4, squash=(1.3, 1.0, 0.8), rot=i * 40)
    for s in (-1, 1):
        rod(b, (L / 2 - 0.35, s * 0.34, 0.78), (L / 2, s * 0.36, 0.95), 0.019, "chrome", n=6)
    rod(b, (L / 2, -0.36, 0.95), (L / 2, 0.36, 0.95), 0.019, "chrome", n=6)
    return fin(ctx, b, "SM_Prop_CT_NutCart", M, "Roasted-nut cart 1.5 x 0.9 x 1.25 m (Canal's south sidewalk, x 4.8): red cabinet, a glass case with a roasting drum "
               "and nuts, brass posts, two wheels and a handle toward +X.", cover=1.0)


def m_hotpot_cart(ctx, M):
    """Hotpot cart 0.9 x 1.2 x 0.95: a small rolling table with a divided pot on a burner, stacked bowls and a bottle crate under."""
    b = B(312)
    L, W = 1.2, 0.9
    cart_wheels(b, -0.35, 0.0, 0.0, 0.14)
    for x in (-0.55, 0.45):
        for s in (-1, 1):
            rod(b, (x, s * 0.36, 0.14), (x, s * 0.36, 0.78), 0.02, "stainless", n=6)
    bx(b, (-L / 2, -W / 2, 0.78), (L / 2, W / 2, 0.82), "stainless", ch=0.004)
    bx(b, (-L / 2 + 0.04, -W / 2 + 0.04, 0.30), (L / 2 - 0.04, W / 2 - 0.04, 0.33), "stainless", pin=False)   # lower shelf
    for i in range(3):                                                                                     # a crate of bottles on the shelf
        cyl(b, (-0.25 + i * 0.12, -0.18, 0.33), 0.04, 0.26, "plasticGreen", seg=8)
    crate(b, -0.38, -0.30, 0.33, 0.40, 0.22, 0.12, "plasticBlue")
    lathe(b, [(0.0, 0.82), (0.20, 0.82), (0.20, 0.86), (0.0, 0.86)], "black", loc=(0.12, 0.0, 0.0), seg=14)  # burner
    lathe(b, [(0.0, 0.86), (0.30, 0.88), (0.31, 0.93), (0.285, 0.93), (0.28, 0.90), (0.0, 0.89)], "alu", loc=(0.12, 0.0, 0.0), seg=20)   # pot
    bx(b, (0.12 - 0.28, -0.012, 0.90), (0.12 + 0.28, 0.012, 0.93), "alu", pin=False)                        # the divider
    bx(b, (0.12 - 0.012, -0.28, 0.90), (0.12 + 0.012, 0.28, 0.93), "alu", pin=False)
    for s in (-1, 1):
        for k in range(2):
            lathe(b, [(0.0, 0.0), (0.05, 0.0), (0.085, 0.07), (0.0, 0.07)], "fabricWhite", loc=(-0.38 + k * 0.0, s * 0.24 + 0.0, 0.82 + k * 0.07), seg=10)
    for i in range(5):                                                                                     # chillies and mushrooms floating
        blob(b, (0.12 + 0.12 * math.cos(i * 1.26), 0.12 * math.sin(i * 1.26), 0.925), 0.03, "apple" if i % 2 else "grain", seg=6, rings=4, squash=(1.3, 1, 0.6))
    for s in (-1, 1):
        rod(b, (L / 2, s * 0.36, 0.78), (L / 2 + 0.10, s * 0.38, 0.92), 0.019, "chrome", n=6)
    return fin(ctx, b, "SM_Prop_CT_HotpotCart", M, "Hotpot cart 1.2 x 0.9 x 0.95 m (x 20.6, Square side): a stainless trolley with a divided pot on a burner, "
               "stacked bowls, a crate of bottles on the lower shelf, handle toward +X.", cover=0.9)


# ------------------------------------------------------------------------------------------------------ stone lions

def m_stone_lion(ctx, M, side):
    """Guardian lion 0.8 x 0.8 x 1.1 on a stepped plinth, facing +X: a seated body, a broad head with a muzzle and a mane of curls round its
    back half, the ball under the left paw (L) or the right (R)."""
    s = 1.0 if side == "L" else -1.0
    b = B(320 + (side == "R"))
    bx(b, (-0.40, -0.40, 0.0), (0.40, 0.40, 0.28), "stone", ch=0.012)                                      # plinth
    bx(b, (-0.36, -0.36, 0.28), (0.36, 0.36, 0.34), "stone", ch=0.010)
    blob(b, (-0.04, 0.0, 0.54), 0.27, "stone", seg=12, rings=8, squash=(1.05, 0.72, 0.82))                  # haunch and body
    blob(b, (0.10, 0.0, 0.68), 0.23, "stone", seg=12, rings=8, squash=(0.85, 0.80, 1.05))                   # chest
    for sy in (-1, 1):                                                                                     # forelegs and paws
        rod(b, (0.20, sy * 0.12, 0.36), (0.18, sy * 0.12, 0.62), 0.05, "stone", n=8)
        blob(b, (0.25, sy * 0.12, 0.37), 0.065, "stone", seg=8, rings=5, squash=(1.4, 0.9, 0.5))
    ball(b, 0.09, (0.27, -s * 0.12, 0.45), "stone", seg=10, rings=7)                                       # the ball under one paw
    blob(b, (0.14, 0.0, 0.97), 0.17, "stone", seg=12, rings=8, squash=(1.0, 1.05, 0.95))                    # head
    blob(b, (0.29, 0.0, 0.92), 0.09, "stone", seg=10, rings=6, squash=(1.2, 1.1, 0.8))                      # muzzle
    bx(b, (0.34, -0.07, 0.875), (0.38, 0.07, 0.895), "black", pin=False)                                   # the mouth
    blob(b, (0.375, 0.0, 0.955), 0.03, "black", seg=6, rings=4, squash=(1, 1.3, 0.8))                        # nose
    for sy in (-1, 1):
        blob(b, (0.255, sy * 0.09, 1.045), 0.05, "stone", seg=8, rings=5, squash=(1.4, 1.0, 0.6))          # brows
        blob(b, (0.295, sy * 0.085, 1.00), 0.02, "black", seg=5, rings=4)                                  # eyes
        blob(b, (0.10, sy * 0.15, 1.10), 0.045, "stone", seg=6, rings=4, squash=(0.8, 1.0, 1.0))           # ears
    for k in range(13):                                                                                    # the mane: curls round the head's back half
        t = math.radians(60 + k * 20)                                                                      # 60 .. 300 degrees, 0 = facing +X
        blob(b, (0.14 + 0.19 * math.cos(t) * 0.9, 0.2 * math.sin(t), 0.97 + 0.025 * (k % 3 - 1)), 0.075, "stone", seg=7, rings=5, squash=(0.9, 0.9, 1.25))
    for k in range(5):
        blob(b, (0.06 + 0.02 * (k % 2), (k - 2) * 0.08, 0.78 - 0.03 * abs(k - 2)), 0.07, "stone", seg=6, rings=4, squash=(0.9, 0.9, 1.1))
    rod(b, (-0.28, 0.0, 0.46), (-0.38, s * 0.10, 0.74), 0.035, "stone", n=6)                                # tail curling up
    blob(b, (-0.38, s * 0.10, 0.80), 0.06, "stone", seg=7, rings=5)
    return fin(ctx, b, "SM_Prop_CT_StoneLion_" + side, M, "Stone guardian lion 0.8 x 0.8 x 1.1 m on a stepped plinth, facing +X (the banquet hall's door, x 29.1 and 36.1, "
               "chinatown.md 4.7): a seated body, a broad head with brows, muzzle and mouth, curls round its back half, a ball under one paw; _L has the ball under "
               "the left paw (+Y), _R mirrored. Generic, no real hall's lion.", cover=0.7)


# ------------------------------------------------------------------------------------------------------ trash

def m_trash_bags(ctx, M, name, L, W, count):
    b = B(330 + count)
    rng = ctx.rng(name)
    cols, rows = max(2, int(round(L / 0.30))), max(1, int(round(W / 0.30)))
    cells = [(i, j) for j in range(rows) for i in range(cols)]
    for k, (i, j) in enumerate(cells[:count]):
        x = -L / 2 + (i + 0.5) * L / cols + rng.uniform(-0.03, 0.03)
        y = -W / 2 + (j + 0.5) * W / rows + rng.uniform(-0.03, 0.03)
        r = min(L / cols, W / rows) * 0.62
        sl = "plastic" if k != 2 else "clothLight"
        rz = rng.uniform(0, 180)
        blob(b, (x, y, r * 0.55), r, sl, seg=8, rings=6, squash=(1.12, 0.95, 0.62), rot=rz)               # a slumped bag
        blob(b, (x + 0.05, y - 0.04, r * 0.45), r * 0.8, sl, seg=7, rings=5, squash=(1.0, 0.9, 0.5), rot=rz + 40)   # a fold at its side
        ob = geo.cylinder(0.03, 0.12, 6, name="knot")                                                      # the gathered neck, leaning
        geo.transform(ob, loc=(x + rng.uniform(-0.03, 0.03), y, r * 0.95), rot=(rng.uniform(-30, 30), rng.uniform(-30, 30), 0))
        b.absorb(ob, sl)
        blob(b, (x, y, r * 1.12), 0.04, sl, seg=6, rings=4, squash=(1.5, 1.0, 0.5), rot=rz)                 # the flopped tail of the tie
    for k in range(max(1, count // 3)):                                                                    # a second layer, lower and flatter
        x = rng.uniform(-L / 2 + 0.2, L / 2 - 0.2)
        y = rng.uniform(-W / 2 + 0.15, W / 2 - 0.15)
        blob(b, (x, y, 0.30), 0.17, "plastic", seg=8, rings=6, squash=(1.2, 0.9, 0.6), rot=rng.uniform(0, 90))
        ob = geo.cylinder(0.026, 0.10, 6, name="knot")
        geo.transform(ob, loc=(x, y, 0.38), rot=(rng.uniform(-25, 25), rng.uniform(-25, 25), 0))
        b.absorb(ob, "plastic")
    return fin(ctx, b, "SM_Prop_CT_TrashBags_" + name, M, "A heap of %d black trash bags %.2f x %.2f x 0.6 m, slumped, folded and tied (twelve on Canal, the alley and "
               "the Square's edge; chinatown.md 4.1). Pivot at the heap's centre." % (count, L, W), collision="none", cover=0.5)


# ------------------------------------------------------------------------------------------------------ fruit stand

def m_fruit_stand_small(ctx, M):
    """Fruit stand at the Mott collider (0.8 x 1.0 x 0.85): two steps of trays, a scale and a price-card stand with no words."""
    b = B(340, step=0.6)
    rng = ctx.rng("fruitstand_small")
    L, W = 1.0, 0.8
    for x in (-L / 2 + 0.03, L / 2 - 0.03):
        for y in (-W / 2 + 0.04, W / 2 - 0.04):
            rod(b, (x, y, 0.0), (x, y, 0.55), 0.02, "timber", n=6)
    for i, (y0, z) in enumerate(((-W / 2, 0.40), (-0.02, 0.62))):
        bx(b, (-L / 2, y0, z - 0.03), (L / 2, y0 + (W / 2 + 0.02 if i else W / 2 - 0.02), z), "wood", pin=False)
    for i, (y0, z) in enumerate(((-W / 2 + 0.05, 0.40), (0.05, 0.62))):
        for j in range(2):
            x0 = -L / 2 + 0.05 + j * 0.46
            bx(b, (x0, y0, z), (x0 + 0.42, y0 + 0.30, z + 0.012), "card", pin=False)
            for s in (0, 1):
                bx(b, (x0, y0 + s * 0.29, z), (x0 + 0.42, y0 + 0.01 + s * 0.29, z + 0.09), "card", pin=False)
            fr = ("orange", "apple", "yellow", "leaf")[(i * 2 + j) % 4]
            if fr == "leaf":
                greens(b, rng, x0, y0 + 0.02, z + 0.012, 0.42, 0.26, n=3)
            else:
                fill_fruit(b, rng, x0 + 0.01, y0 + 0.02, z + 0.012, 0.40, 0.27, 0.045, fr, layers=1, seg=5)
    bx(b, (-L / 2 + 0.05, W / 2 - 0.10, 0.62), (-L / 2 + 0.25, W / 2 - 0.02, 0.85), "black", pin=False)     # the price board, blank
    return fin(ctx, b, "SM_Prop_CT_FruitStand_Small", M, "Fruit stand 1.0 x 0.8 x 0.85 m, the Mott sidewalk collider's size (x 8.2, z 8.6): two steps of card trays "
               "with fruit and greens and a blank price board. Placed turned 90 degrees on 0.8 x 1.0.", cover=0.85)


# ------------------------------------------------------------------------------------------------------ wall and street fittings

def m_standpipe(ctx, M):
    """Siamese standpipe connection 0.25 deep x 0.30 wide x 0.9: a brass plate, a body, two capped inlets at 45 degrees."""
    b = B(350, step=0.3)
    bx(b, (-0.125, -0.15, 0.20), (-0.105, 0.15, 0.80), "gold", ch=0.004, pin=False)                          # the plate
    rod(b, (-0.12, 0.0, 0.52), (0.02, 0.0, 0.52), 0.05, "gold", n=8)
    for s in (-1, 1):
        rod(b, (0.02, 0.0, 0.52), (0.12, s * 0.10, 0.40), 0.04, "gold", n=8)
        cyl(b, (0.12, s * 0.10, 0.37), 0.058, 0.08, "gold", seg=8)
        rod(b, (0.12, s * 0.10, 0.33), (0.12, s * 0.10, 0.37), 0.06, "black", n=8)
        rod(b, (0.06, s * 0.05, 0.43), (0.09, s * 0.12, 0.24), 0.008, "chrome", n=4)                         # the cap chain
    rod(b, (-0.11, 0.0, 0.52), (-0.11, 0.0, 0.84), 0.035, "gold", n=8)                                    # a riser into the wall
    bx(b, (-0.125, -0.15, 0.20), (-0.10, 0.15, 0.22), "black", pin=False)
    return fin(ctx, b, "SM_Prop_CT_Standpipe", M, "Siamese standpipe connection 0.25 x 0.30 x 0.9 m on a facade (eleven on Canal's two sidewalks): a plate, two "
               "capped brass inlets at 45 degrees with a chain, a riser. Pivot at the foot of the wall's footprint, outward +X.",
               collision="none", cover=None)


def m_bike_rack(ctx, M):
    """Hoop bike rack 2.0 x 0.1 x 0.85 with a locked bicycle (the side view: it is only 0.1 m deep at the collider)."""
    b = B(351, step=0.4)
    for x in (-0.85, 0.85):                                                                                # two inverted-U hoops in the XZ plane
        hw = 0.15
        pts = [(x - hw, 0.0), (x - hw, 0.62)] + [(x + hw * math.cos(math.pi - t), 0.62 + 0.22 * math.sin(t)) for t in np.linspace(0.0, math.pi, 7)[1:-1]] + [(x + hw, 0.62), (x + hw, 0.0)]
        for (xa, za), (xb, zb) in zip(pts[:-1], pts[1:]):
            rod(b, (xa, 0, za), (xb, 0, zb), 0.02, "galv", n=6)
        for xx in (x - hw, x + hw):
            bx(b, (xx - 0.04, -0.04, 0.0), (xx + 0.04, 0.04, 0.012), "galv", pin=False)
    # the bicycle, between the hoops
    wr = 0.28
    for x in (-0.40, 0.40):
        ring(b, (x, 0.0, wr), wr - 0.02, 0.02, "rubber", "Y", seg=24, sm=6)
        cyl(b, (x, -0.015, wr), 0.045, 0.03, "chrome", seg=8, axis="Y")
        for a in range(8):
            t = a * math.pi / 4
            rod(b, (x, 0, wr), (x + (wr - 0.04) * math.cos(t), 0, wr + (wr - 0.04) * math.sin(t)), 0.004, "chrome", n=3)
    fr = {"bb": (0.0, 0.0, 0.27), "seat": (-0.22, 0.0, 0.70), "head": (0.30, 0.0, 0.70), "rear": (-0.40, 0.0, wr), "front": (0.40, 0.0, wr)}
    for a, c in (("bb", "seat"), ("bb", "head"), ("seat", "head"), ("rear", "bb"), ("rear", "seat"), ("front", "head")):
        rod(b, fr[a], fr[c], 0.017, "jade", n=6)
    bx(b, (-0.34, -0.06, 0.72), (-0.10, 0.06, 0.76), "black", ch=0.01, pin=False)
    bx(b, (0.26, -0.18, 0.76), (0.30, 0.18, 0.79), "black", pin=False)
    ring(b, (0.0, 0.0, 0.27), 0.06, 0.012, "chrome", "Y", seg=12, sm=4)
    ring(b, (0.56, 0.0, 0.50), 0.09, 0.008, "black", "Y", seg=12, sm=4)                                      # the lock round hoop and frame
    return fin(ctx, b, "SM_Prop_CT_BikeRack", M, "Hoop bike rack 2.0 x 0.1 x 0.85 m with a bicycle locked between its two hoops (side on: the level's collider is "
               "0.1 m deep). Pivot at the rack's centre; the bicycle's handlebars reach 0.2 m either side of the collider.", cover=0.85)


def m_chair_stack(ctx, M):
    """Six banquet chairs stacked: 0.5 x 0.5 x 1.2, black frames, red seats."""
    b = B(352, step=0.4)
    for k in range(6):
        z = k * 0.075
        for sx in (-1, 1):
            for sy in (-1, 1):
                rod(b, (sx * 0.20, sy * 0.20, z), (sx * 0.20, sy * 0.20, z + 0.46), 0.016, "black", n=6)
        bx(b, (-0.22, -0.22, z + 0.44), (0.22, 0.22, z + 0.50), "fabricRed", ch=0.008, pin=False)
        for sy in (-1, 1):
            rod(b, (-0.20, sy * 0.20, z + 0.46), (-0.22, sy * 0.20, z + 0.88), 0.016, "black", n=6)
        bx(b, (-0.235, -0.22, z + 0.62), (-0.205, 0.22, z + 0.82), "fabricRed", ch=0.006, pin=False)
        rod(b, (-0.20, -0.20, z + 0.16), (-0.20, 0.20, z + 0.16), 0.012, "black", n=5)
    return fin(ctx, b, "SM_Prop_CT_ChairStack", M, "Stack of six banquet chairs 0.5 x 0.5 x 1.2 m (black tube frames, red padded seats and backs): the banquet hall's spare "
               "chairs, the noodle house's stools (chinatown.md 4.7). Backs toward -X.", cover=1.0)


def m_grease_bin(ctx, M):
    """Wheeled grease bin 0.9 x 0.58 x 1.0: a green tote with a sloped lid, handle bar, two wheels, a greasy lip."""
    b = B(353, step=0.3)
    L, W = 0.9, 0.58
    bx(b, (-L / 2, -W / 2, 0.10), (L / 2, W / 2, 0.80), "plasticGreen", ch=0.02)
    bx(b, (-L / 2 - 0.01, -W / 2 - 0.01, 0.80), (L / 2 + 0.01, W / 2 + 0.01, 0.86), "plasticGreen", ch=0.02)
    bx(b, (-L / 2 + 0.01, -W / 2 + 0.03, 0.86), (L / 2 - 0.01, W / 2 - 0.03, 0.92), "plasticGreen", ch=0.02)
    bx(b, (L / 2 - 0.15, -0.12, 0.92), (L / 2 - 0.02, 0.12, 0.98), "black", ch=0.01)                        # the lid's handle
    for s in (-1, 1):
        cyl(b, (-L / 2 + 0.08, s * (W / 2 + 0.01) - 0.02, 0.09), 0.09, 0.04, "rubber", seg=12, axis="Y")
        bx(b, (-L / 2 + 0.02, s * W / 2 - 0.02, 0.10), (-L / 2 + 0.14, s * W / 2 + 0.02, 0.22), "black", pin=False)
    bx(b, (-L / 2 - 0.05, -0.20, 0.55), (-L / 2, 0.20, 0.60), "black", ch=0.006)                            # the back handle
    for s in (-1, 1):
        bx(b, (-L / 2 - 0.05, s * 0.18 - 0.015, 0.40), (-L / 2, s * 0.18 + 0.015, 0.58), "black", pin=False)
    bx(b, (-0.2, -W / 2 - 0.003, 0.45), (0.2, -W / 2 + 0.003, 0.70), "clothLight", pin=False)               # a plain blank label
    return fin(ctx, b, "SM_Prop_CT_GreaseBin", M, "Wheeled grease bin 0.9 x 0.58 x 1.0 m (three in the alleys): green plastic tote, a stepped lid with a handle, two wheels, "
               "a back handle, a blank label.", cover=0.9)


def m_planter(ctx, M, tag, L, W, H):
    b = B(354 + int(L * 10), step=0.4)
    rng = ctx.rng("planter" + tag)
    bx(b, (-L / 2, -W / 2, 0.0), (L / 2, W / 2, H - 0.12), "stone", ch=0.012)
    bx(b, (-L / 2 - 0.02, -W / 2 - 0.02, H - 0.14), (L / 2 + 0.02, W / 2 + 0.02, H - 0.10), "stone", ch=0.008)
    bx(b, (-L / 2 + 0.05, -W / 2 + 0.05, H - 0.12), (L / 2 - 0.05, W / 2 - 0.05, H - 0.04), "timber", pin=False)
    for i in range(int(8 * L * W / 0.5) + 6):                                                                # shrub: leaf lobes
        blob(b, (rng.uniform(-L / 2 + 0.1, L / 2 - 0.1), rng.uniform(-W / 2 + 0.1, W / 2 - 0.1), rng.uniform(H - 0.02, H + 0.10)), rng.uniform(0.08, 0.13), "leaf",
             seg=7, rings=5, squash=(1.0, 1.0, 0.8))
    return fin(ctx, b, "SM_Prop_CT_Planter_" + tag, M, "Light planter %.1f x %.1f x %.1f m (the 42k-triangle Block planter was too heavy to place): a stone box, soil, a lump of shrub."
               % (L, W, H + 0.1), cover=0.7)


def m_bucket_stack(ctx, M):
    """Two nested mop buckets and a wringer 0.6 x 0.53 x 0.7."""
    b = B(356, step=0.3)
    for (x, y, z, c) in ((-0.12, 0.0, 0.0, "plasticOrange"), (-0.12, 0.0, 0.18, "plasticOrange")):
        lathe(b, [(0.0, z), (0.16, z), (0.21, z + 0.30), (0.0, z + 0.30)], c, loc=(x, y, 0.0), seg=14)
        ring(b, (x, y, z + 0.30), 0.21, 0.012, c, "Z", seg=14, sm=4)
    bx(b, (0.08, -0.22, 0.0), (0.30, 0.22, 0.30), "plasticBlue", ch=0.012)                                  # the wringer bucket on wheels
    bx(b, (0.10, -0.20, 0.30), (0.28, 0.20, 0.34), "plasticBlue", ch=0.006)
    rod(b, (0.28, 0.0, 0.14), (0.30, 0.0, 0.60), 0.022, "alu", n=6)
    rod(b, (-0.28, 0.12, 0.0), (-0.10, 0.20, 0.64), 0.011, "timber", n=6)                                   # a mop leaning
    for a in range(7):
        blob(b, (-0.28 + 0.02 * math.cos(a), 0.12 + 0.02 * math.sin(a), 0.03), 0.03, "clothLight", seg=5, rings=3, squash=(1, 1, 1.4))
    return fin(ctx, b, "SM_Prop_CT_BucketStack", M, "Two nested orange buckets and a blue mop wringer 0.6 x 0.53 x 0.7 m with a mop leaning (five in the alleys).", cover=0.6)


def m_sandwich_board(ctx, M):
    """A-frame sandwich board 0.68 x 0.80 x 1.1: two black panels in a timber frame, hinged at the top; no writing here."""
    b = B(357, step=0.3)
    for s in (-1, 1):
        a = s * 0.28
        for sx in (-1, 1):
            rod(b, (a * 0.08, sx * 0.30, 1.05), (a * 1.0, sx * 0.30, 0.0), 0.017, "timber", n=6)
        pts = np.array([[a * 0.12, -0.27, 0.95], [a * 0.12, 0.27, 0.95], [a * 0.88, 0.27, 0.10], [a * 0.88, -0.27, 0.10]])
        Fv = np.zeros((2, 2, 3))
        Fv[0, 0], Fv[0, 1], Fv[1, 0], Fv[1, 1] = pts[3], pts[2], pts[0], pts[1]
        sheet(b, Fv if s > 0 else Fv[:, ::-1], 0.016, "black", vdir=Z, fdir=Y)
    rod(b, (0.0, -0.30, 1.05), (0.0, 0.30, 1.05), 0.018, "timber", n=6)
    return fin(ctx, b, "SM_Prop_CT_SandwichBoard", M, "A-frame sandwich board 0.56 x 0.6 x 1.05 m: two black panels in timber legs (the writing is a chalk decal on the "
               "level, not geometry).", cover=None)


def m_cd_rack(ctx, M):
    """Record shop CD rack 1.0 x 0.6 x 1.5: a black steel rack of six shelves of CDs on edge, backed against the wall."""
    b = B(358, step=0.4)
    rng = ctx.rng("cdrack")
    bx(b, (-0.30, -0.50, 0.0), (-0.26, 0.50, 1.50), "black", ch=0.004)
    for z in np.linspace(0.12, 1.30, 6):
        bx(b, (-0.30, -0.50, z), (0.26, 0.50, z + 0.02), "black", ch=0.003)
        bx(b, (0.24, -0.50, z), (0.28, 0.50, z + 0.10), "black", pin=False)
        for j in range(26):
            y = -0.46 + j * 0.036
            c = ("cloth", "clothLight", "fabricRed", "fabricBlue", "fabricGreen", "fabricYellow")[int(rng.integers(0, 6))]
            lean = rng.uniform(-0.02, 0.05)
            bx(b, (-0.10 + lean, y, z + 0.02), (0.22 + lean * 0.3, y + 0.012, z + 0.30), c, pin=False)
    for y in (-0.50, 0.49):
        bx(b, (-0.30, y, 0.0), (0.28, y + 0.01, 1.50), "black", pin=False)
    return fin(ctx, b, "SM_Prop_CT_CDRack", M, "Record shop CD rack 0.6 x 1.0 x 1.5 m: six shelves of plain-sleeved discs standing on edge (no sleeve art, no names), "
               "back toward -X (two, N1's window).", cover=None)


def m_road_plates(ctx, M):
    """Four steel road plates stacked on edge against the corner: 0.7 x 1.4 x 1.9."""
    b = B(359, step=0.5)
    for i in range(4):
        bx(b, (-0.25 + i * 0.12, -0.60, 0.0), (-0.25 + i * 0.12 + 0.025, 0.60 + 0.0, 1.88), "trim", ch=0.003)
        bx(b, (-0.25 + i * 0.12 - 0.02, -0.60, 0.0), (-0.25 + i * 0.12 + 0.045, -0.50, 0.04), "black", pin=False)
    for z in (0.5, 1.4):
        rod(b, (-0.30, -0.66, z), (0.30, -0.66, z), 0.018, "galv", n=6)
    return fin(ctx, b, "SM_Prop_CT_RoadPlates", M, "Steel road plates stacked on edge 0.7 x 1.4 x 1.9 m against the dig's corner (diamond trim, two lifting bars).", cover=1.9)


def m_dig_fence(ctx, M):
    """2.55 m run of the dig's plywood fence 0.25 x 2.55 x 2.4: plywood sheets on 4x4 posts with a rail, a sawhorse foot."""
    b = B(360, step=0.5)
    L = 2.55
    for y in (-L / 2 + 0.06, 0.0, L / 2 - 0.06):
        bx(b, (-0.10, y - 0.05, 0.0), (0.0, y + 0.05, 2.30), "timber", ch=0.004)
    for k in range(2):
        y0 = -L / 2 + 0.02 + k * 1.245
        bx(b, (0.0, y0, 0.10), (0.018, y0 + 1.22, 2.30), "ply", ch=0.002)
    bx(b, (-0.10, -L / 2, 2.22), (0.02, L / 2, 2.34), "timber", ch=0.004)
    bx(b, (-0.10, -L / 2, 0.80), (-0.01, L / 2, 0.92), "timber", ch=0.004)
    for y in (-0.55, 0.55):                                                                                # sawhorse feet
        bx(b, (-0.12, y - 0.04, 0.0), (0.12, y + 0.04, 0.10), "timber", ch=0.003)
    return fin(ctx, b, "SM_Prop_CT_DigFence", M, "A 2.55 m run of the dig's plywood fence, 2.4 m high (tiles along its collider): two sheets on three posts with a top and "
               "a mid rail and sawhorse feet; the plywood face toward +X.", cover=2.3)


# ------------------------------------------------------------------------------------------------------ roofs and walls

def m_roof_vent(ctx, M):
    """Turbine roof vent 0.6 x 0.6 x 0.9: a galvanised base, a neck and a finned ball."""
    b = B(370, step=0.4)
    lathe(b, [(0.0, 0.0), (0.30, 0.0), (0.30, 0.06), (0.14, 0.12), (0.14, 0.34), (0.0, 0.34)], "galv", seg=16)
    lathe(b, [(0.0, 0.34), (0.20, 0.36), (0.26, 0.56), (0.20, 0.82), (0.05, 0.88), (0.0, 0.90)], "galv", seg=16)
    for a in range(14):
        t = a * 2 * math.pi / 14
        bx_ = geo.box((0.012, 0.15, 0.46), bevel=0.0, base=False)
        geo.transform(bx_, loc=(0.26 * math.cos(t) * 0.92, 0.26 * math.sin(t) * 0.92, 0.58), rot=(0, 0, math.degrees(t) + 90 + 28))
        b.absorb(bx_, "galv")
    ring(b, (0, 0, 0.36), 0.20, 0.012, "alu", "Z", seg=16, sm=4)
    return fin(ctx, b, "SM_Prop_CT_RoofVent", M, "Turbine roof vent 0.6 x 0.6 x 0.9 m (six on the market and bakery roofs, chinatown.md 4.3): a galvanised base, a neck and a "
               "domed turbine with 14 curved vanes.", cover=0.9)


def m_exhaust_fan(ctx, M):
    """Wall exhaust fan 0.6 deep x 0.8 wide x 0.8: a box housing with a round guard and fan, a drip pan, a greasy stain below."""
    b = B(371, step=0.3)
    bx(b, (-0.30, -0.40, 0.0), (0.18, 0.40, 0.80), "galv", ch=0.012)
    bx(b, (-0.30, -0.40, 0.0), (0.18, 0.40, 0.06), "black", ch=0.004)
    bx(b, (0.18, -0.30, 0.10), (0.30, 0.30, 0.70), "galv", ch=0.01)                                         # the louvre face
    for z in np.linspace(0.14, 0.66, 7):
        bx(b, (0.30, -0.27, z), (0.325, 0.27, z + 0.012), "black", pin=False)
    ring(b, (0.31, 0.0, 0.40), 0.26, 0.014, "alu", "X", seg=20, sm=5)
    for a in range(5):
        t = a * 2 * math.pi / 5
        rod(b, (0.30, 0.0, 0.40), (0.30, 0.22 * math.cos(t), 0.40 + 0.22 * math.sin(t)), 0.014, "alu", n=5)
    cyl(b, (0.30, 0.0, 0.40), 0.05, 0.03, "black", seg=10, axis="X")
    bx(b, (-0.32, -0.34, 0.80), (0.20, 0.34, 0.84), "galv", ch=0.006)                                       # rain hood
    return fin(ctx, b, "SM_Prop_CT_ExhaustFan", M, "Kitchen exhaust fan box on a wall 0.6 deep x 0.8 wide x 0.8 m (six, 2.6 m above the alley floor): a galvanised housing, a "
               "louvred face with a guard ring, five blades and a hood. Back toward -X.", collision="none")


def m_exhaust_stack(ctx, M):
    """Roof exhaust stack 0.6 x 0.6 x 1.6: a base box, a flue pipe and a rain cap on three stays."""
    b = B(372, step=0.4)
    bx(b, (-0.30, -0.30, 0.0), (0.30, 0.30, 0.30), "roof", ch=0.01)
    lathe(b, [(0.0, 0.30), (0.19, 0.30), (0.19, 0.34), (0.15, 0.34), (0.15, 1.30), (0.0, 1.30)], "galv", seg=14)
    lathe(b, [(0.0, 1.46), (0.30, 1.40), (0.30, 1.37), (0.0, 1.55)], "galv", seg=14)
    for a in range(3):
        t = a * 2 * math.pi / 3
        rod(b, (0.13 * math.cos(t), 0.13 * math.sin(t), 1.30), (0.16 * math.cos(t), 0.16 * math.sin(t), 1.40), 0.012, "galv", n=4)
    return fin(ctx, b, "SM_Prop_CT_ExhaustStack", M, "Roof exhaust stack 0.6 x 0.6 x 1.6 m on a roofing base: a flue and a cap on stays (the bakery's chimney run).", cover=None)


def m_antenna_mast(ctx, M):
    """TV and radio mast 0.6 x 1.4 x 2.2: a tripod base on the roof, a mast, two cross arms of dipoles, a small dish."""
    b = B(373, step=0.4)
    for a in range(3):
        t = a * 2 * math.pi / 3
        rod(b, (0.22 * math.cos(t), 0.55 * math.sin(t), 0.0), (0.0, 0.0, 0.9), 0.02, "galv", n=6)
    bx(b, (-0.25, -0.60, 0.0), (0.25, 0.60, 0.05), "roof", ch=0.005)
    rod(b, (0.0, 0.0, 0.0), (0.0, 0.0, 2.2), 0.025, "galv", n=8)
    for z, w in ((1.4, 0.55), (1.8, 0.40), (2.1, 0.28)):
        rod(b, (0.0, -w, z), (0.0, w, z), 0.017, "alu", n=6)
        for yy in (-w, -w * 0.5, w * 0.5, w):
            rod(b, (-0.12, yy, z), (0.12, yy, z), 0.012, "alu", n=4)
    cyl(b, (0.07, 0.0, 1.08), 0.30, 0.04, "galv", seg=16, axis="X")
    rod(b, (0.07, 0.0, 1.08), (0.30, 0.0, 1.08), 0.015, "galv", n=5)
    return fin(ctx, b, "SM_Prop_CT_AntennaMast", M, "Roof mast 0.6 x 1.4 x 2.2 m (W1's roof): a tripod base, a mast with three cross arms of dipoles and a small dish.", cover=None)


# ------------------------------------------------------------------------------------------------------ hand-built LODs

def _pallet(b, z, L, W, slot, boards=5, detail=True):
    """One pallet (1.2 x 1.0 x 0.144): five top boards, three stringer rows of blocks, three bottom boards."""
    for i in range(boards):
        y = -W / 2 + i * (W - 0.10) / (boards - 1)
        bx(b, (-L / 2, y, z + 0.122), (L / 2, y + 0.10, z + 0.144), slot, pin=False)
    for j in range(3):
        x = -L / 2 + j * (L - 0.10) / 2
        bx(b, (x, -W / 2, z + 0.022), (x + 0.10, W / 2, z + 0.122), slot, pin=False)
    for j in range(3):
        x = -L / 2 + j * (L - 0.10) / 2
        bx(b, (x - 0.0, -W / 2, z), (x + 0.10, W / 2, z + 0.022), slot, pin=False)


def m_pallet_stack_lods(ctx, M):
    """SM_Furn_PalletStack_A_LOD1 (about 1.2k triangles: every pallet's boards as boxes) and _LOD2 (about 150: the stack as eight slabs and four posts),
    1.23 x 1.03 x 1.15, the Block's slot MI_Wood_ScanPallet."""
    out = []
    for lod, (boards, n) in (("LOD1", (5, 8)), ("LOD2", (0, 8))):
        b = B(380 + len(lod) + boards, step=4.0)
        L, W = 1.23, 1.03
        for k in range(n):
            z = k * 0.1438
            if boards:
                _pallet(b, z, 1.2, 1.0, "pallet")
            else:
                bx(b, (-0.60, -0.50, z + 0.10), (0.60, 0.50, z + 0.1438), "pallet", pin=False)
                for j in (-0.55, 0.0, 0.50):
                    bx(b, (j - 0.05, -0.50, z), (j + 0.05, 0.50, z + 0.10), "pallet", pin=False)
        ob = done(ctx, b, "SM_Furn_PalletStack_A_" + lod, M, collision="none", cover_height=None, expect_size=None,
                  notes="%s of the Block's SM_Furn_PalletStack_A (13k triangles): eight pallets built as boxes, same slot, size and pivot. The collapse left slivers; "
                        "drawn past %d m." % (lod, 12 if lod == "LOD1" else 30))
        out.append(ob)
    return out


def _pole_mats(M):
    """The slots of the Block's sign post and street lamp that the Canal kit did not have yet (the same names)."""
    from mi import mat
    if "lens" not in M:
        M["lens"] = kit.F("MI_Lamp_Lens", (0.80, 0.78, 0.72), 0.15)
    if "signSignPost" not in M:
        M["signSignPost"] = mat.sign_face("SignPost", (0.3, 0.3, 0.3), 0.45)
        M["signSignPost"]["mi_tile_m"] = (0.32, 0.44)


def m_pole_lods(ctx, M):
    """Hand-built LODs of the Block's SM_Furn_SignPost (562 triangles: LOD1 about 30) and SM_Furn_StreetLamp (1128: LOD1 about 330,
    LOD2 about 110): their poles are 40 to 120 mm across and collapse to slivers, so the pole is rebuilt as a few solid members. Same slots
    in the same order, size and pivot as the Block's."""
    from assets.furniture import card
    _pole_mats(M)
    out = []
    b = B(390, step=4.0)
    bx(b, (-0.025, -0.0255, 0.0), (0.025, 0.0065, 2.8), "galv", pin=False)
    bx(b, (-0.16, -0.019, 2.18), (0.16, -0.016, 2.62), "galv", pin=False)
    card(b, (-0.16, -0.0195, 2.18), (0.32, 0, 0), (0, 0, 0.44), "signSignPost", sign=True)
    out.append(done(ctx, b, "SM_Furn_SignPost_LOD1", M, collision="none", cover_height=None, expect_size=None,
                    notes="LOD1 of the Block's SM_Furn_SignPost (562 triangles): the channel post as a solid box, the plate and its face; same slots, size and "
                          "pivot. Drawn past 12 m."))
    for lod, (seg, hseg, hr) in (("LOD1", (8, 10, 5)), ("LOD2", (4, 6, 3))):
        b = B(391 + len(lod) + seg, step=4.0)
        bx(b, (-0.17, -0.17, 0.0), (0.17, 0.17, 0.04), "galv", pin=False)                                  # the base: a 45-degree 4-sided lathe in the Block's
        bx(b, (-0.15, -0.15, 0.04), (0.15, 0.15, 0.60), "galv", pin=False)
        lathe(b, [(0.13, 0.60), (0.10, 2.5), (0.07, 5.5), (0.06, 7.2), (0.0, 7.2)], "galv", seg=seg)
        for p0, p1 in (((0, 0, 7.0), (0, 0, 7.40)), ((0, 0, 7.40), (0, -0.70, 7.76)), ((0, -0.70, 7.76), (0, -1.86, 7.80))):
            rod(b, p0, p1, 0.04, "galv", n=6 if lod == "LOD1" else 4)
        rod(b, (0, -0.02, 6.60), (0, -1.15, 7.70), 0.022, "galv", n=4)
        head = geo.sphere(0.5, hseg, hr)
        co, _ = geo.arrays(head)
        co *= (0.30, 0.74, 0.16)
        co[:, 2] = np.maximum(co[:, 2], -0.035)
        geo.set_verts(head, co)
        geo.transform(head, loc=(0, -2.16, 7.80))
        b.absorb(head, "galv")
        bx(b, (-0.10, -2.42, 7.755), (0.10, -1.98, 7.766), "lens", pin=False)
        bx(b, (-0.06, 0.205, 0.15), (0.06, 0.212, 0.40), "galv", pin=False)
        out.append(done(ctx, b, "SM_Furn_StreetLamp_" + lod, M, collision="none", cover_height=None, expect_size=None,
                        notes="%s of the Block's SM_Furn_StreetLamp (1128 triangles): the tapered pole, the transformer base, the davit arm and the cobra head "
                              "with fewer sides; same slots, size and pivot. Drawn past %d m." % (lod, 12 if lod == "LOD1" else 30)))
    return out


PROPS3 = [m_dumpling_cart, m_nut_cart, m_hotpot_cart, lambda c, M: m_stone_lion(c, M, "L"), lambda c, M: m_stone_lion(c, M, "R"),
          lambda c, M: m_trash_bags(c, M, "L", 0.90, 0.60, 6), lambda c, M: m_trash_bags(c, M, "S", 0.58, 0.60, 3),
          m_fruit_stand_small, m_standpipe, m_bike_rack, m_chair_stack, m_grease_bin,
          lambda c, M: m_planter(c, M, "S", 0.8, 0.6, 0.8), lambda c, M: m_planter(c, M, "L", 1.0, 1.0, 0.9),
          m_bucket_stack, m_sandwich_board, m_cd_rack, m_road_plates, m_dig_fence,
          m_roof_vent, m_exhaust_fan, m_exhaust_stack, m_antenna_mast, m_pallet_stack_lods, m_pole_lods]
