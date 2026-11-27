"""Canal Street round 3, part 3 (fixer pass): the street pieces that had a collider but no mesh, and the Canal dumpster.

Each is built at its collider's size (tools/levels/data/level_chinatown.json `propPlacements`), pivot at the centre of the footprint
on the ground, forward +X, so the placements stay pure arithmetic (_chinatown_streets.PROPS) and no instance is scaled.

    newsstand (1.9 x 1.4 x 2.6)             SM_Prop_CT_Newsstand
    phone kiosk (0.35 x 0.95 x 2.5)         SM_Prop_CT_PhoneKiosk
    shop display (1.2 x 1.45 x 1.9)         SM_Prop_CT_ShopDisplay
    laundry cart (0.9 x 0.6 x 1.05)         SM_Prop_CT_LaundryCart
    steam chimney (0.5 x 0.5 x 2.5)         SM_Prop_CT_SteamChimney
    shed post (0.2 x 0.2 x 3.4)             SM_Prop_CT_ShedPost
    scale stand (0.45 x 0.6 x 1.4)          SM_Prop_CT_ScaleStand
    alarm pedestal (0.4 x 0.4 x 1.4)        SM_Prop_CT_AlarmPedestal
    arcade pillar (0.6 x 0.6 x 4.05)        SM_Prop_CT_ArcadePillar
    the dumpster (1.9 x 1.17 x 1.37)        SM_Prop_CT_Dumpster, _LOD1, _LOD2  (the Block's is a clean toy-green box with a blank label)
"""
import math

import numpy as np

from assets._chinatown_kit import ball, bx, done, lathe, rod
from assets._chinatown_props3 import blob, cyl, ring
from assets.facade import B
from mi import geo


def tilted(b, lo, hi, slot, rot=(0, 0, 0), pivot=None):
    """A box turned by Euler degrees about `pivot` (default its centre): lids, flaps, a bent plate."""
    lo, hi = np.minimum(lo, hi).astype(float), np.maximum(lo, hi).astype(float)
    ob = geo.box(tuple(hi - lo), bevel=0.0, name="t")
    c = (lo + hi) / 2
    pv = c if pivot is None else np.asarray(pivot, float)
    geo.transform(ob, loc=tuple(c - pv), rot=(0, 0, 0))
    geo.transform(ob, loc=(0, 0, 0), rot=rot)
    geo.transform(ob, loc=tuple(pv))
    return b.absorb(ob, slot)


def fin(ctx, b, name, M, notes, size=None, cover=None, collision="box", **kw):
    return done(ctx, b, name, M, collision=collision, cover_height=cover, expect_size=size, notes=notes, **kw)


# ------------------------------------------------------------------------------------------------------ newsstand

def m_newsstand(ctx, M):
    """Newsstand 1.4 deep (X) x 1.9 wide (Y) x 2.6: a steel kiosk, three open bays of magazines and papers across its +X face, a counter with a till and a
    lottery sign board (no words), a sloped roof with a gutter, a rolled-up shutter above the bays."""
    b = B(380)
    L, W = 1.4, 1.9
    bx(b, (-L / 2, -W / 2, 0.0), (L / 2, W / 2, 0.14), "black", ch=0.0)                                   # plinth
    bx(b, (-L / 2, -W / 2, 0.14), (-L / 2 + 0.05, W / 2, 2.30), "grey", ch=0.0)                           # back wall
    for s in (-1, 1):                                                                                      # the two sides
        bx(b, (-L / 2, s * W / 2 - (0.04 if s > 0 else 0.0), 0.14), (L / 2, s * W / 2 + (0.0 if s > 0 else 0.04), 2.30), "grey", ch=0.0)
    bx(b, (L / 2 - 0.08, -W / 2, 0.14), (L / 2, W / 2, 1.00), "grey", ch=0.0)                             # the counter's front panel
    bx(b, (L / 2 - 0.55, -W / 2, 1.00), (L / 2, W / 2, 1.05), "stainless", ch=0.0)                  # counter top and lip
    bx(b, (L / 2 - 0.08, -W / 2, 1.90), (L / 2, W / 2, 2.30), "grey", ch=0.0)                             # the shutter box above the bays
    for i in range(4):                                                                                     # shutter slats
        bx(b, (L / 2 - 0.02, -W / 2 + 0.03, 1.93 + i * 0.09), (L / 2 + 0.012, W / 2 - 0.03, 1.93 + i * 0.09 + 0.07), "galv", pin=False)
    for s in (-0.31, 0.31):                                                                                # two uprights make three bays
        bx(b, (L / 2 - 0.12, s - 0.02, 1.05), (L / 2 - 0.04, s + 0.02, 1.90), "black", ch=0.003)
    for k, tilt in enumerate((18, 14, 20)):                                                                # the sloped magazine shelves, three bays
        yc = (k - 1) * 0.62
        for r in range(3):
            z = 1.10 + r * 0.25
            tilted(b, (L / 2 - 0.44, yc - 0.28, z), (L / 2 - 0.10, yc + 0.28, z + 0.015), "ply", rot=(0, tilt, 0))
            for j in range(2):                                                                             # a pair of magazine rows per shelf
                col = ("paper", "clothLight", "fabricRed", "fabricBlue", "fabricYellow")[(k * 7 + r * 3 + j) % 5]
                tilted(b, (L / 2 - 0.42, yc - 0.27 + j * 0.28, z + 0.015), (L / 2 - 0.12, yc - 0.27 + j * 0.28 + 0.25, z + 0.026), col,
                       rot=(0, tilt, 0))
    for r in range(3):                                                                                     # papers stacked on the counter
        bx(b, (L / 2 - 0.50, -0.62 + r * 0.05, 1.05 + r * 0.045), (L / 2 - 0.22, -0.34 + r * 0.05, 1.095 + r * 0.045), "clothLight", pin=False)
    bx(b, (L / 2 - 0.30, 0.30, 1.05), (L / 2 - 0.12, 0.52, 1.20), "black", ch=0.0)                         # till
    bx(b, (L / 2 - 0.26, 0.33, 1.20), (L / 2 - 0.14, 0.49, 1.26), "glasswin", pin=False)
    bx(b, (L / 2 - 0.08, -0.80, 2.36), (L / 2 - 0.01, 0.80, 2.52), "redlac", ch=0.0)                      # sign board above (words come from a decal)
    tilted(b, (-L / 2, -W / 2, 2.30), (L / 2, W / 2, 2.35), "galv", rot=(0, -5, 0))   # the roof, sloped to the front
    bx(b, (L / 2 - 0.04, -W / 2, 2.20), (L / 2, W / 2, 2.30), "black", ch=0.0)        # gutter lip
    for s in (-1, 1):
        rod(b, (L / 2 - 0.03, s * (W / 2 - 0.03), 2.20), (L / 2 - 0.03, s * (W / 2 - 0.03), 1.92), 0.02, "black", n=6)   # downspout
    return fin(ctx, b, "SM_Prop_CT_Newsstand", M, "Newsstand 1.4 x 1.9 x 2.6 m (two on Canal's north sidewalk, chinatown.md 4.1; placed turned -90 so the counter faces the street): steel kiosk, three sloped racks of magazines "
               "and papers across its +X face, a stainless counter with a till, a shutter box, a sloped roof with gutter. The sign board is blank for a decal. "
               "Pivot at the centre of the footprint; the counter faces +X.", cover=1.0)


# ------------------------------------------------------------------------------------------------------ phone kiosk

def m_phone_kiosk(ctx, M):
    """Wall phone kiosk 0.35 x 0.95 x 2.5: a steel hood over a payphone shelf with the handset on its cord, coin box and a lit number panel."""
    b = B(381)
    D, W = 0.35, 0.95
    bx(b, (-D / 2, -W / 2, 0.0), (-D / 2 + 0.05, W / 2, 2.30), "trim", ch=0.004)                           # back panel against the wall
    tilted(b, (-D / 2, -W / 2 - 0.03, 2.28), (D / 2, W / 2 + 0.03, 2.34), "trim", rot=(0, -6, 0))          # the hood
    for s in (-1, 1):
        bx(b, (-D / 2, s * W / 2 - (0.04 if s > 0 else 0.0), 1.05), (D / 2 - 0.04, s * W / 2 + (0.0 if s > 0 else 0.04), 2.28), "trim", ch=0.004)  # side wings
    bx(b, (-D / 2 + 0.05, -0.18, 1.18), (-D / 2 + 0.17, 0.18, 1.62), "black", ch=0.008)                      # the phone's case
    bx(b, (-D / 2 + 0.17, -0.12, 1.45), (-D / 2 + 0.185, 0.12, 1.58), "neonWhite", pin=False)               # lit panel
    for r in range(4):
        for c in range(3):
            bx(b, (-D / 2 + 0.17, -0.07 + c * 0.05, 1.22 + r * 0.045), (-D / 2 + 0.19, -0.04 + c * 0.05, 1.24 + r * 0.045), "chrome", pin=False)
    bx(b, (-D / 2 + 0.05, -0.09, 1.62), (-D / 2 + 0.20, 0.09, 1.70), "black", ch=0.01)                       # the cradle
    rod(b, (-D / 2 + 0.17, -0.10, 1.64), (-D / 2 + 0.17, -0.10, 1.34), 0.02, "black", n=6)                    # the handset hangs
    bx(b, (-D / 2 + 0.17, -0.14, 1.30), (-D / 2 + 0.22, -0.06, 1.52), "black", ch=0.01)
    bx(b, (-D / 2, -W / 2, 1.00), (D / 2, W / 2, 1.05), "stainless", ch=0.004)                              # the shelf
    for s in (-1, 1):
        rod(b, (D / 2 - 0.04, s * (W / 2 - 0.04), 1.0), (-D / 2 + 0.05, s * (W / 2 - 0.04), 0.70), 0.02, "trim", n=6)  # shelf brackets
    return fin(ctx, b, "SM_Prop_CT_PhoneKiosk", M, "Public phone kiosk 0.35 x 0.95 x 2.5 m (Mott's east sidewalk): a steel back panel, side wings and sloped hood, a payphone case with a lit "
               "number panel, keypad and handset on its cord over a stainless shelf. Pivot at the foot of the wall, front toward +X.", cover=0.0)


# ------------------------------------------------------------------------------------------------------ shop display

def m_shop_display(ctx, M):
    """Sidewalk display 1.2 x 1.45 x 1.9: a three-tier wire stand of boxed goods, plastic baskets and a hanging bar, an awning-pole on top."""
    b = B(382)
    L, W = 1.2, 1.45
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx(b, (sx * (L / 2 - 0.03) - 0.02, sy * (W / 2 - 0.03) - 0.02, 0.0), (sx * (L / 2 - 0.03) + 0.02, sy * (W / 2 - 0.03) + 0.02, 1.78), "black", pin=False)
    for z, d in ((0.16, 1.0), (0.66, 0.9), (1.14, 0.8)):
        bx(b, (-L / 2 + 0.02, -W / 2 + 0.02, z), (L / 2 - 0.02, W / 2 - 0.02, z + 0.04), "galv", pin=False)   # the tiers
    for k, (z, slot) in enumerate(((0.20, "plasticBlue"), (0.70, "plasticOrange"), (1.18, "plasticGreen"))):
        for j in range(3):                                                                                 # three baskets per tier, goods in them
            y0 = -W / 2 + 0.10 + j * 0.45
            bx(b, (-L / 2 + 0.12, y0, z), (L / 2 - 0.12, y0 + 0.40, z + 0.22), slot, pin=False)
            bx(b, (-L / 2 + 0.16, y0 + 0.03, z + 0.20), (L / 2 - 0.16, y0 + 0.37, z + 0.24),
               ("cloth", "card", "fabricRed")[(j + k) % 3], pin=False)
    rod(b, (-L / 2 + 0.03, -W / 2 + 0.03, 1.78), (-L / 2 + 0.03, W / 2 - 0.03, 1.78), 0.016, "black", n=6)    # the hanging bar
    for j in range(5):                                                                                     # five shirts or bags hung from it
        blob(b, (-L / 2 + 0.06, -0.55 + j * 0.27, 1.55), 0.12, ("fabricRed", "fabricBlue", "clothLight", "fabricGreen", "fabricYellow")[j], seg=6, rings=4, squash=(0.35, 1.0, 1.7))
    return fin(ctx, b, "SM_Prop_CT_ShopDisplay", M, "Sidewalk display stand 1.2 x 1.45 x 1.9 m (five in front of shop fronts on Canal's south side): a black wire frame, three tiers of "
               "colour baskets with boxed goods, a hanging bar of five garments. No logos. Pivot at the centre of the footprint.", cover=0.8)


# ------------------------------------------------------------------------------------------------------ laundry cart

def m_laundry_cart(ctx, M):
    """Laundry cart 0.9 x 0.6 x 1.05: a wire basket on four casters, a canvas liner heaped with bundles, a push bar."""
    b = B(383)
    L, W = 0.9, 0.6
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(b, (sx * (L / 2 - 0.07), sy * (W / 2 - 0.07), 0.0), 0.035, 0.07, "rubber", seg=8)
            rod(b, (sx * (L / 2 - 0.07), sy * (W / 2 - 0.07), 0.07), (sx * (L / 2 - 0.07), sy * (W / 2 - 0.07), 0.14), 0.014, "chrome", n=6)
    bx(b, (-L / 2, -W / 2, 0.14), (L / 2, W / 2, 0.18), "galv", ch=0.003)                                    # the base
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx(b, (sx * (L / 2 - 0.015) - 0.015, sy * (W / 2 - 0.015) - 0.015, 0.14), (sx * (L / 2 - 0.015) + 0.015, sy * (W / 2 - 0.015) + 0.015, 0.78), "galv", ch=0.002)
    for z in (0.40, 0.76):
        for sy in (-1, 1):
            rod(b, (-L / 2, sy * (W / 2 - 0.015), z), (L / 2, sy * (W / 2 - 0.015), z), 0.012, "galv", n=6)
        for sx in (-1, 1):
            rod(b, (sx * (L / 2 - 0.015), -W / 2, z), (sx * (L / 2 - 0.015), W / 2, z), 0.012, "galv", n=6)
    bx(b, (-L / 2 + 0.03, -W / 2 + 0.03, 0.20), (L / 2 - 0.03, W / 2 - 0.03, 0.62), "fabricWhite", ch=0.01)       # the liner
    for i, (x, y, r, sl) in enumerate(((-0.22, -0.08, 0.20, "fabricWhite"), (0.10, 0.06, 0.22, "clothLight"), (0.28, -0.10, 0.16, "fabricBlue"),
                                       (-0.10, 0.12, 0.17, "fabricYellow"), (0.0, -0.05, 0.19, "fabricWhite"))):
        blob(b, (x, y, 0.70 + 0.04 * (i % 2)), r, sl, seg=8, rings=6, squash=(1.1, 1.0, 0.75), rot=i * 37)       # the heaped laundry
    rod(b, (-L / 2 - 0.03, -W / 2, 0.80), (-L / 2 - 0.03, W / 2, 0.80), 0.018, "chrome", n=6)                 # the push bar
    for sy in (-1, 1):
        rod(b, (-L / 2, sy * (W / 2 - 0.03), 0.70), (-L / 2 - 0.03, sy * (W / 2 - 0.03), 1.04), 0.016, "chrome", n=6)
    rod(b, (-L / 2 - 0.03, -W / 2 + 0.03, 1.04), (-L / 2 - 0.03, W / 2 - 0.03, 1.04), 0.018, "chrome", n=6)
    return fin(ctx, b, "SM_Prop_CT_LaundryCart", M, "Laundry cart 0.9 x 0.6 x 1.05 m (two, at the back of Canal's north row): a galvanised wire basket on four casters, a canvas liner "
               "heaped with bundles, a chrome push bar at -X. Pivot at the centre of the footprint.", cover=0.6)


# ------------------------------------------------------------------------------------------------------ steam chimney

def m_steam_chimney(ctx, M):
    """Steam chimney 0.5 x 0.5 x 2.5: a galvanised flue on a base, a roof flange, a rain cap on three stays, a band and a scorch mark."""
    b = B(384)
    bx(b, (-0.25, -0.25, 0.0), (0.25, 0.25, 0.10), "conc", ch=0.008)                                        # the collar's base plate
    lathe(b, [(0.0, 0.10), (0.20, 0.10), (0.20, 0.22), (0.12, 0.30), (0.12, 2.18), (0.0, 2.18)], "galv", seg=16)   # flue with a flared foot
    for z in (0.9, 1.6):
        lathe(b, [(0.0, z), (0.135, z), (0.135, z + 0.05), (0.0, z + 0.05)], "galv", seg=16)                # joint bands
    lathe(b, [(0.0, 2.18), (0.18, 2.18), (0.18, 2.22), (0.0, 2.22)], "galv", seg=16)                       # the rim under the cap
    for a in range(3):                                                                                     # three stays
        t = a * 2 * math.pi / 3
        rod(b, (0.15 * math.cos(t), 0.15 * math.sin(t), 2.20), (0.10 * math.cos(t), 0.10 * math.sin(t), 2.38), 0.014, "galv", n=6)
    lathe(b, [(0.0, 2.50), (0.12, 2.43), (0.26, 2.38), (0.26, 2.36), (0.0, 2.40)], "galv", seg=16)         # the rain cap, a shallow cone
    lathe(b, [(0.0, 2.50), (0.12, 2.43), (0.0, 2.43)], "black", seg=12)
    bx(b, (0.10, -0.05, 2.05), (0.135, 0.05, 2.18), "black", ch=0.004, pin=False)                            # soot streak at the top
    return fin(ctx, b, "SM_Prop_CT_SteamChimney", M, "Steam chimney 0.5 x 0.5 x 2.5 m (two on the roofs of Canal's north row, steam is an effect): a galvanised flue with a flared "
               "foot on a base plate, two joint bands, a rain cap on three stays, a soot streak. Pivot at the centre of the base.", cover=0.0)


# ------------------------------------------------------------------------------------------------------ shed post

def m_shed_post(ctx, M):
    """Sidewalk-shed post 0.2 x 0.2 x 3.4: a steel tube post on a base plate and a cap plate with a hammer-head, two scaffold clamps."""
    b = B(385)
    bx(b, (-0.10, -0.10, 0.0), (0.10, 0.10, 0.02), "trim", ch=0.003)                                       # base plate
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(b, (sx * 0.075, sy * 0.075, 0.02), 0.012, 0.02, "chrome", seg=6)                            # four bolts
    bx(b, (-0.045, -0.045, 0.02), (0.045, 0.045, 3.30), "trim", ch=0.003)                                   # the tube
    bx(b, (-0.10, -0.07, 3.30), (0.10, 0.07, 3.36), "trim", ch=0.004)                                       # cap plate
    bx(b, (-0.10, -0.05, 3.36), (0.10, 0.05, 3.40), "trim", ch=0.004)                                       # the hammer-head under the beam
    for z in (1.0, 2.1):
        ring(b, (0.0, 0.0, z), 0.052, 0.014, "chrome", "Z", seg=10, sm=5)                                   # scaffold clamps
        bx(b, (0.05, -0.02, z - 0.03), (0.095, 0.02, z + 0.03), "chrome", ch=0.003, pin=False)
    bx(b, (-0.046, -0.046, 0.55), (0.046, 0.046, 0.85), "yellow", ch=0.002, pin=False)                      # the hazard sleeve at kerb height
    return fin(ctx, b, "SM_Prop_CT_ShedPost", M, "Sidewalk-shed post 0.2 x 0.2 x 3.4 m (five under the N4 shed): a dark steel tube on a bolted base plate, a cap plate and hammer-head, "
               "two clamps and a yellow hazard sleeve at kerb height. Pivot at the centre of the base.", cover=0.0)


# ------------------------------------------------------------------------------------------------------ scale stand

def m_scale_stand(ctx, M):
    """Produce scale stand 0.45 x 0.6 x 1.4: a tripod of tube legs under a hanging spring scale with a steel pan and a bag of fruit."""
    b = B(386)
    for a in range(3):
        t = a * 2 * math.pi / 3 + 0.4
        rod(b, (0.0, 0.0, 1.28), (0.20 * math.cos(t), 0.26 * math.sin(t), 0.0), 0.02, "black", n=6)
    cyl(b, (0.0, 0.0, 1.26), 0.045, 0.08, "black", seg=8)
    rod(b, (0.0, 0.0, 1.34), (0.0, 0.0, 1.40), 0.012, "chrome", n=6)
    lathe(b, [(0.0, 1.00), (0.07, 1.00), (0.075, 1.18), (0.0, 1.18)], "alu", seg=14, loc=(0.0, 0.0, 0.0))     # the scale's body
    bx(b, (-0.02, -0.075, 1.05), (0.075, 0.075, 1.15), "plastic", pin=False)                                 # dial face
    rod(b, (0.0, 0.0, 1.00), (0.0, 0.0, 0.80), 0.01, "chrome", n=6)
    lathe(b, [(0.0, 0.80), (0.17, 0.82), (0.20, 0.86), (0.18, 0.86), (0.0, 0.84)], "stainless", seg=16)      # the pan
    for i, (x, y) in enumerate(((0.0, 0.0), (0.08, 0.04), (-0.07, 0.05), (0.02, -0.08))):
        ball(b, 0.055, (x, y, 0.90), ("orange", "orange", "apple", "yellow")[i], seg=8, rings=5)
    return fin(ctx, b, "SM_Prop_CT_ScaleStand", M, "Produce scale stand 0.45 x 0.6 x 1.4 m (a grocer's, Canal's south sidewalk): a tripod of tube legs, a hanging spring scale with a dial, "
               "a steel pan holding four pieces of fruit. Pivot at the centre of the footprint.", cover=0.0)


# ------------------------------------------------------------------------------------------------------ alarm pedestal

def m_alarm_pedestal(ctx, M):
    """Alarm pedestal 0.4 x 0.4 x 1.4: a steel post box on a plinth with a red call button under a hood, a beacon dome on top and a grille."""
    b = B(387)
    bx(b, (-0.20, -0.20, 0.0), (0.20, 0.20, 0.06), "stone", ch=0.006)
    bx(b, (-0.14, -0.14, 0.06), (0.14, 0.14, 1.12), "trim", ch=0.004)
    bx(b, (0.14, -0.10, 0.80), (0.18, 0.10, 1.02), "black", ch=0.006)                                      # the call plate
    bx(b, (0.18, -0.045, 0.88), (0.205, 0.045, 0.96), "redlac", ch=0.006)                                  # red button
    tilted(b, (0.14, -0.12, 1.02), (0.24, 0.12, 1.05), "black", rot=(0, 25, 0), pivot=(0.14, 0.0, 1.03))    # the hood over it
    for i in range(5):
        bx(b, (0.14, -0.09, 0.30 + i * 0.05), (0.15, 0.09, 0.33 + i * 0.05), "black", pin=False)            # the speaker grille
    bx(b, (-0.16, -0.16, 1.12), (0.16, 0.16, 1.18), "black", ch=0.006)
    lathe(b, [(0.0, 1.18), (0.12, 1.18), (0.13, 1.26), (0.10, 1.36), (0.0, 1.40)], "redlac", seg=14)        # the beacon dome
    return fin(ctx, b, "SM_Prop_CT_AlarmPedestal", M, "Alarm pedestal 0.4 x 0.4 x 1.4 m (two, Canal's north sidewalk): a steel post on a stone plinth, a speaker grille, a red call button "
               "under a hood, a beacon dome. Pivot at the centre of the base, button toward +X.", cover=0.0)


# ------------------------------------------------------------------------------------------------------ arcade pillar

def m_arcade_pillar(ctx, M):
    """Arcade pillar 0.6 x 0.6 x 4.05: a square concrete column with a chamfered shaft, a plinth with a bevel, a capital, a rust stain at the foot."""
    b = B(388)
    bx(b, (-0.30, -0.30, 0.0), (0.30, 0.30, 0.30), "conc", ch=0.02)
    bx(b, (-0.26, -0.26, 0.30), (0.26, 0.26, 3.75), "conc", ch=0.03)
    bx(b, (-0.31, -0.31, 3.75), (0.31, 0.31, 4.05), "conc", ch=0.02)
    bx(b, (-0.33, -0.33, 3.68), (0.33, 0.33, 3.78), "conc", ch=0.01)
    for s in (-1, 1):                                                                                      # a pair of steel angle guards at the foot
        bx(b, (s * 0.26 - 0.015, -0.27, 0.30), (s * 0.26 + 0.015, 0.27, 1.10), "black", ch=0.003, pin=False)
    return fin(ctx, b, "SM_Prop_CT_ArcadePillar", M, "Arcade pillar 0.6 x 0.6 x 4.05 m (the Square's arcade edge): a square concrete column on a plinth with a capital and steel angle guards. "
               "Pivot at the centre of the base.", cover=0.0)


# ------------------------------------------------------------------------------------------------------ the dumpster

def m_dumpster(ctx, M, lod=0):
    """Canal dumpster 1.9 x 1.17 x 1.37 (lod 0 about 3k triangles, 1 about 1.2k, 2 about 0.4k): a front-load steel bin in a dark, sun- and
    salt-faded green with ribbed sides, a dented front, fork pockets, black plastic lids (one propped open), a hauler plate of
    stencil bars (no words), a cardboard flap and a bag over the rim. The three levels keep the same four slots (dumpster, black, plastic, yellow)."""
    b = B(389 + lod)
    L, W, H = 1.9, 1.17, 1.37
    t = 0.035
    c6 = 0.006 if lod == 0 else 0.0
    bx(b, (-L / 2, -W / 2, 0.10), (L / 2, W / 2, 0.14), "black", ch=c6)                                       # the floor
    for s in (-1, 1):                                                                                      # skids
        bx(b, (-L / 2 + 0.05, s * 0.40 - 0.05, 0.0), (L / 2 - 0.05, s * 0.40 + 0.05, 0.10), "black", ch=c6)
    bx(b, (-L / 2, -W / 2, 0.14), (L / 2, -W / 2 + t, 1.20), "dumpster", ch=c6)                              # side walls
    bx(b, (-L / 2, W / 2 - t, 0.14), (L / 2, W / 2, 1.20), "dumpster", ch=c6)
    bx(b, (-L / 2, -W / 2, 0.14), (-L / 2 + t, W / 2, 1.20), "dumpster", ch=c6)                              # back wall
    tilted(b, (L / 2 - t, -W / 2, 0.14), (L / 2, W / 2, 1.22), "dumpster", rot=(0, 3, 0), pivot=(L / 2, 0.0, 0.14))   # front, leaning out a little
    if lod <= 1:
        for s in (-1, 1):                                                                                  # top rim, a box section
            bx(b, (-L / 2 - 0.03, s * (W / 2 - 0.02) - 0.045, 1.20), (L / 2 + 0.03, s * (W / 2 - 0.02) + 0.045, 1.30), "dumpster", ch=c6)
        for x in (-L / 2 + 0.02, L / 2 - 0.02):
            bx(b, (x - 0.045, -W / 2 - 0.01, 1.20), (x + 0.045, W / 2 + 0.01, 1.30), "dumpster", ch=c6)
        for s in (-1, 1):                                                                                  # lift pockets at the sides' lower edge
            bx(b, (-0.40, s * (W / 2 + 0.01) - 0.03, 0.22), (0.40, s * (W / 2 + 0.01) + 0.03, 0.30), "black", ch=c6)
    if lod == 0:
        for s in (-1, 1):                                                                                  # pressed ribs on the sides (5 vertical, 2 horizontal)
            yy = s * (W / 2 + 0.012)
            for x in np.linspace(-L / 2 + 0.22, L / 2 - 0.22, 5):
                bx(b, (x - 0.025, yy - 0.014, 0.18), (x + 0.025, yy + 0.014, 1.18), "dumpster", pin=False)
            for z in (0.46, 0.86):
                bx(b, (-L / 2 + 0.02, yy - 0.014, z - 0.025), (L / 2 - 0.02, yy + 0.014, z + 0.025), "dumpster", pin=False)
        for z in (0.50, 0.90):                                                                             # the back's ribs
            bx(b, (-L / 2 - 0.03, -W / 2 + 0.05, z - 0.03), (-L / 2, W / 2 - 0.05, z + 0.03), "dumpster", pin=False)
        tilted(b, (-0.10, W / 2 + 0.005, 0.50), (0.45, W / 2 + 0.04, 0.92), "dumpster")                    # a dented patch, proud
        tilted(b, (0.40, -W / 2 - 0.04, 0.60), (0.80, -W / 2 - 0.005, 1.02), "dumpster")
        bx(b, (-0.05, -W / 2 - 0.012, 0.58), (0.35, -W / 2 - 0.004, 0.64), "black", pin=False)             # rust-dark seam smear
    for i in range({0: 3, 1: 1, 2: 1}[lod]):                                                               # the hauler plate: faded bars, not words
        x = -0.55 + i * 0.35
        bx(b, (x - 0.14, -W / 2 - 0.008, 0.98), (x + 0.14, -W / 2 + 0.002, 1.12), "yellow", pin=False)
        for j in range(4 if lod == 0 else 0):
            bx(b, (x - 0.12 + j * 0.065, -W / 2 - 0.012, 1.00), (x - 0.12 + j * 0.065 + 0.03, -W / 2 - 0.006, 1.10), "black", pin=False)
    lid_x = -L / 2 + 0.02
    tilted(b, (lid_x, -W / 2 + 0.02, 1.30), (lid_x + 0.92, 0.0, 1.34), "plastic", rot=(0, -2, 0), pivot=(lid_x, -W / 2, 1.30))          # a closed lid, rear left
    tilted(b, (lid_x, 0.0, 1.30), (lid_x + 0.92, W / 2 - 0.02, 1.34), "plastic", rot=(0, 62, 0), pivot=(lid_x, 0.0, 1.31))             # the other, propped open
    if lod == 0:
        bx(b, (lid_x + 0.40, -W / 2 + 0.2, 1.34), (lid_x + 0.50, -W / 2 + 0.5, 1.38), "plastic", ch=c6)       # the lid's pull handle
        tilted(b, (0.10, -0.40, 1.22), (0.78, 0.20, 1.25), "card")                                          # cardboard flat poking out
        tilted(b, (0.55, 0.10, 1.22), (0.85, 0.50, 1.40), "card", rot=(10, 0, 20))
        blob(b, (-0.18, -0.30, 1.28), 0.17, "plastic", seg=7, rings=4, squash=(1.2, 1.0, 0.6), rot=30)
    if lod <= 1:
        blob(b, (0.30, 0.25, 1.30), 0.22, "plastic", seg=8 if lod == 0 else 6, rings=5 if lod == 0 else 3, squash=(1.1, 1.0, 0.7))   # a black bag over the rim
    return fin(ctx, b, "SM_Prop_CT_Dumpster" + ("" if lod == 0 else "_LOD%d" % lod), M,
               "Canal dumpster 1.9 x 1.17 x 1.4 m (four, the alleys and the loading bays) at LOD%d: a dark faded-green front-load bin, ribbed sides, dented panels, fork pockets, "
               "black plastic lids (one propped open), a hauler plate of bars (no words), a cardboard flap, a bag over the rim. Pivot at the centre of the footprint, front toward +X. "
               "Replaces the Block's SM_Furn_Dumpster on Canal (a clean toy-green box with a blank label)." % lod,
               size=None, cover=1.2, collision="box" if lod == 0 else "none")


PROPS4 = [m_newsstand, m_phone_kiosk, m_shop_display, m_laundry_cart, m_steam_chimney, m_shed_post, m_scale_stand, m_alarm_pedestal, m_arcade_pillar,
          lambda c, M: m_dumpster(c, M, 0), lambda c, M: m_dumpster(c, M, 1), lambda c, M: m_dumpster(c, M, 2)]
