"""Midtown kit, part 2: the gantry behind the big LED wall, the backs of the giant screens, the roof billboard (C1), the
LED tile the art-only screens are built from, the ticker band and the north tower's stack (midtown.md 4 S2, 10, 12, 14.2).

The playable side of every screen is plate and truss, never lattice: cabinet backs (1 x 1 m plates with handles and
power boxes), box-section posts, channel girts and angle braces, all 6 cm and up. The screen surface is ONE face per
screen in the slot M_MI_Screen on 0..1 UVs (the master of midtown.md 12.3); the C1 face is M_Sign_MT_Face (a lightbox).
"""
import math

import numpy as np

from assets import _midtown_roof as R
from assets.facade import B, bx, rod
from mi import steel

X, Y, Z = np.eye(3)
SCREEN = "M_MI_Screen"


def screen_face(b, x0, x1, z0, z1, y=0.0, slot="signScreen"):
    """A screen surface in the plane y looking toward -Y; returns its UV frame."""
    R.face_quad(b, x0, x1, z0, z1, y, slot)
    return ((x0, y, z0), X, Z, (x1 - x0, z1 - z0))


def bezel(b, x0, x1, z0, z1, y=0.0, w=0.12, d=0.10, slot="black"):
    bx(b, (x0 - w, y - 0.02, z0 - w), (x1 + w, y + d, z0), slot, ch=0.006, pin=False, axis="x")
    bx(b, (x0 - w, y - 0.02, z1), (x1 + w, y + d, z1 + w), slot, ch=0.006, pin=False, axis="x")
    bx(b, (x0 - w, y - 0.02, z0), (x0, y + d, z1), slot, ch=0.006, pin=False, axis="z")
    bx(b, (x1, y - 0.02, z0), (x1 + w, y + d, z1), slot, ch=0.006, pin=False, axis="z")


def cabinet_backs(b, x0, x1, z0, z1, y, cell=1.0, depth=0.12, rng=None, boxes=True):
    """The backs of the LED cabinets: one plate per cell with a recessed seam, two handles and a power box on some."""
    nx, nz = int(round((x1 - x0) / cell)), int(round((z1 - z0) / cell))
    bx(b, (x0, y, z0), (x1, y + depth - 0.02, z1), "black", axis="x")                           # the cabinet body
    for i in range(nx):
        for j in range(nz):
            cx0, cz0 = x0 + i * cell, z0 + j * cell
            bx(b, (cx0 + 0.02, y + depth - 0.02, cz0 + 0.02), (cx0 + cell - 0.02, y + depth, cz0 + cell - 0.02), "grey",
               pin=False, axis="x")
            if boxes and (i + j) % 2 == 0:
                bx(b, (cx0 + 0.30, y + depth, cz0 + 0.55), (cx0 + 0.70, y + depth + 0.07, cz0 + 0.80), "grey", ch=0.006, pin=False)
            if boxes and (i * 7 + j * 3) % 5 == 0:
                for hx in (0.12, cell - 0.18):
                    bx(b, (cx0 + hx, y + depth, cz0 + 0.20), (cx0 + hx + 0.06, y + depth + 0.04, cz0 + 0.40), "galv", pin=False)


def truss_back(b, x0, x1, z0, z1, y, post_every=2.0, girt_every=1.5, depth=0.30, brace=True, slot="black"):
    """Box-section posts, channel girts and angle braces behind a screen, from y (the cabinet backs) to y + depth."""
    xs = np.arange(x0, x1 + 1e-6, post_every)
    for xx in xs:
        bx(b, (xx - 0.075, y + depth - 0.15, z0 - 0.3), (xx + 0.075, y + depth, z1 + 0.15), slot, ch=0.006, pin=False, axis="z")
    zs = np.arange(z0, z1 + 1e-6, girt_every)
    for zz in zs:
        b.prism(steel.channel(0.15, 0.065, 0.009, 0.007), (x0 - 0.1, y + 0.02, zz - 0.075), Y, Z, (x1 - x0 + 0.2, 0, 0), slot, pstep=9.0)
    if brace:
        for k, (xa, xb) in enumerate(zip(xs[:-1], xs[1:])):
            if k % 2:
                continue
            for za, zb in zip(zs[:-1], zs[1:]):
                R.angle_brace(b, (xa + 0.08, y + depth - 0.08, za + 0.08), (xb - 0.08, y + depth - 0.08, zb - 0.08), slot)


# ================================================================================================= the gantry and G1

def m_gantry(ctx, M):
    """The gantry deck behind the LED wall (R1, 14.0): 16 m along +X, 3.5 m deep from the building face (y = 0) to the
    screen side (y = -3.5), deck top z = 0, 0.4 m deep. Channel edge beams and I cross beams, a grating deck (texture on
    plates), the front rail at 1.10 (the letterbox to the wall's underside at 2.2 is data, playerOnly), the end frames up
    to 3.0, knee braces down to the facade, the control cabinet (Reel 8's), power boxes and a cable tray.
    Pivot: the south end on the building face (local x = 0 is world z = 14, x runs north), deck top."""
    b = B(601, step=0.6)
    L, D = 16.0, 3.5
    for y, u in ((0.0, Y), (-D, -Y)):
        b.prism(steel.channel(0.40, 0.10, 0.014, 0.010), (0, y, -0.40), -u, Z, (L, 0, 0), "black", pstep=9.0)
    for xx in np.arange(1.0, L, 2.0):
        b.prism(steel.ibeam(0.30, 0.15, 0.011, 0.008), (xx, -D + 0.1, -0.33), X, Z, (0, D - 0.2, 0), "black", pstep=9.0)
    R.plates(b, 0.0, L, -D + 0.02, -0.02, 0.0, 0.03, "grate", n=8)
    for xx in np.arange(0.0, L + 0.01, 2.0):                                                     # front rail posts
        R.bar(b, (xx + (0.04 if xx == 0 else -0.04 if xx == L else 0), -D + 0.06, 0.0), (xx + (0.04 if xx == 0 else -0.04 if xx == L else 0), -D + 0.06, 1.10),
              0.06, 0.06, "black", ch=0.004)
    for zz in (1.10, 0.55):
        R.tube(b, (0, -D + 0.06, zz), (L, -D + 0.06, zz), "black", 0.03)
    R.bar(b, (0, -D + 0.06, 0.075), (L, -D + 0.06, 0.075), 0.15, 0.02, "black", up=Y)
    for xe in (0.04, L - 0.04):                                                                  # end frames to 3.0
        for yy in (-D + 0.06, -1.6, -0.06):
            R.bar(b, (xe, yy, 0.0), (xe, yy, 3.0), 0.06, 0.06, "black", ch=0.004)
        for zz in (1.1, 2.0, 3.0):
            R.tube(b, (xe, -D + 0.06, zz), (xe, -0.06, zz), "black", 0.03)
    for xx in np.arange(1.0, L, 4.0):                                                            # knee braces to the facade
        R.bar(b, (xx, -D + 0.25, -0.40), (xx, 0.05, -2.8), 0.10, 0.10, "black", ch=0.004)
        bx(b, (xx - 0.15, 0.0, -3.0), (xx + 0.15, 0.03, -2.6), "black", ch=0.004, pin=False, axis="z")
        b.rivets([(xx + dx, 0.0, zz) for dx in (-0.09, 0.09) for zz in (-2.92, -2.68)], -Y, "black", d=0.04, h=0.02, leak=0.6)
    cx = L - 1.6                                                                                 # control cabinet (Reel 8), north end
    bx(b, (cx - 0.6, -0.75, 0.0), (cx + 0.6, -0.05, 2.0), "grey", ch=0.012, pin=False)
    for s in (-1, 1):
        bx(b, (cx + s * 0.3 - 0.29, -0.765, 0.08), (cx + s * 0.3 + 0.29, -0.75, 1.92), "grey", ch=0.004, pin=False, axis="z")
        bx(b, (cx + s * 0.04 - 0.015, -0.80, 0.9), (cx + s * 0.04 + 0.015, -0.765, 1.15), "galv", pin=False)
    lab = R.label(b, (cx + 0.12, -0.766, 1.45), X, Z, 0.36, 0.24)
    for i, xx in enumerate((4.2, 8.6, 12.4)):                                                   # power boxes on the wall side
        bx(b, (xx - 0.35, -0.35, 0.9), (xx + 0.35, -0.02, 1.7), "grey", ch=0.008, pin=False)
        R.tube(b, (xx, -0.18, 1.7), (xx, -0.18, 2.6), "galv", 0.03)
    for zz in (2.6,):                                                                            # cable tray up to the wall
        bx(b, (0.4, -0.40, zz), (L - 0.4, -0.10, zz + 0.012), "galv", pin=False)
        for yy in (-0.40, -0.10):
            bx(b, (0.4, yy - 0.006, zz), (L - 0.4, yy + 0.006, zz + 0.10), "galv", pin=False)
        for xx in np.arange(1.0, L, 2.0):
            R.bar(b, (xx, -0.25, zz), (xx, -0.25, 3.4), 0.06, 0.06, "black", ch=0.003)
    for i in range(6):                                                                           # cables down to the cabinet
        R.tube(b, (cx - 0.3 + i * 0.12, -0.25, 2.0), (cx - 0.3 + i * 0.12, -0.25, 2.6), "rubber", 0.03, n=8)
    return R.done(ctx, b, "SM_Roof_Gantry_16m", M, ground=False, faces=[lab], expect_size=(None, None, None),
                  notes="The gantry behind G1 (R1 14.0, world x -8..-4.5, z -2..14): grating deck on channels and I beams, front rail "
                        "1.10 (the guard to 2.2 and the end guards to 3.0 are playerOnly data), end frames, knee braces to D's face, "
                        "the control cabinet of Reel 8 at the north end (label Label_HighVoltage), power boxes, cable tray. Pivot: the "
                        "south end on the building face (rot_z 90: +X runs north, the screen side faces east), deck top at 14.0.")


def m_ledwall(ctx, M):
    """G1: the 16 x 9 m LED wall. Screen face in the plane y = 0 looking -Y (east over the square), bottom at z = 0
    (16.2 in the world, 2.2 over the gantry deck); a bezel; behind it (+Y) the cabinet backs, the truss of posts, girts
    and braces, and two outrigger frames back to the building (3.5 m) at mid height and at the top. Pivot: the bottom
    south corner of the face (local x = 0 is world z = 14), face toward -Y."""
    b = B(611, step=0.8)
    W, H = 16.0, 9.0
    fr = screen_face(b, 0.0, W, 0.0, H, 0.0)
    bezel(b, 0.0, W, 0.0, H, 0.0, w=0.15, d=0.12)
    cabinet_backs(b, 0.0, W, 0.0, H, 0.02, cell=1.0, depth=0.14)
    truss_back(b, 0.0, W, 0.0, H, 0.16, post_every=2.0, girt_every=1.5, depth=0.35)
    for zz in (4.4, H - 0.1):                                                                    # outriggers to the building
        for xx in np.arange(1.0, W, 4.0):
            b.prism(steel.ibeam(0.25, 0.13, 0.011, 0.008), (xx, 0.5, zz - 0.25), X, Z, (0, 3.3, 0), "black", pstep=9.0)
            R.angle_brace(b, (xx, 0.55, zz - 0.25), (xx, 2.2, zz - 1.6))
            bx(b, (xx - 0.2, 3.80, zz - 0.45), (xx + 0.2, 3.83, zz + 0.05), "black", ch=0.004, pin=False, axis="z")
    for xx in np.arange(2.0, W, 4.0):                                                            # catwalk ladder posts (service)
        R.bar(b, (xx, 0.70, 0.0), (xx, 0.70, H), 0.06, 0.06, "black", ch=0.003)
    return R.done(ctx, b, "SM_Sign_LEDWall_16x9", M, ground=False, faces=[(SCREEN, fr)], expect_size=(None, None, None),
                  notes="G1, the gantry LED wall 16 x 9 m (world 16.2 to 25.2 over the west sidewalk, facing east): one screen face "
                        "(M_MI_Screen 0..1, 450 nits, the takeover until reel8), bezel, cabinet backs, posts every 2 m, girts every "
                        "1.5 m, angle braces, outriggers to D (plate and truss: the playable back). Pivot: bottom south corner of the "
                        "face, face -Y (rot_z 90 in the world: +X runs north, the face looks east).")


def m_billboard(ctx, M):
    """C1 on C's roof: a 16 x 8 m lightbox (face M_Sign_MT_Face, MARLOWE & FINCH) at 2.0 to 10.0 over the roof, facing -Y
    (east in the world), on three pairs of I legs 1.5 m apart, braced, a catwalk at the face's foot with a rail and four
    LED floods on goosenecks. Pivot: the face's bottom-left edge projected to the roof (z = 0), face toward -Y."""
    b = B(621, step=0.8)
    W, H, z0 = 16.0, 8.0, 2.0
    bx(b, (-0.1, 0.0, z0 - 0.1), (W + 0.1, 0.35, z0 + H + 0.1), "grey", axis="x")               # the lightbox cabinet
    R.face_quad(b, 0.0, W, z0, z0 + H, -0.002, "signFace")
    fr = ((0.0, -0.002, z0), X, Z, (W, H))
    for (za, zb) in ((z0 - 0.12, z0), (z0 + H, z0 + H + 0.12)):                                   # retainer frame
        bx(b, (-0.12, -0.05, za), (W + 0.12, 0.02, zb), "galv", ch=0.004, pin=False, axis="x")
    for xa in (-0.12, W):
        bx(b, (xa, -0.05, z0), (xa + 0.12, 0.02, z0 + H), "galv", ch=0.004, pin=False, axis="z")
    for xx in (2.0, 8.0, 14.0):                                                                  # legs, braced
        for yy in (0.6, 2.1):
            R.col_ibeam(b, xx, yy, 0.0, z0 + H, d=0.30, bf=0.20)
            bx(b, (xx - 0.25, yy - 0.25, 0.0), (xx + 0.25, yy + 0.25, 0.30), "conc", ch=0.02, pin=False)
        for za, zb in ((0.3, 3.6), (3.6, 6.8), (6.8, z0 + H)):
            R.angle_brace(b, (xx, 0.7, za), (xx, 2.0, zb))
        for zz in (3.6, 6.8):
            R.bar(b, (xx, 0.6, zz), (xx, 2.1, zz), 0.08, 0.16, "grey", ch=0.003)
    truss_back(b, 0.0, W, z0, z0 + H, 0.35, post_every=2.0, girt_every=2.0, depth=0.25, brace=False, slot="grey")
    for (xa, xb) in ((2.0, 8.0), (8.0, 14.0)):                                                   # back bracing between legs
        R.angle_brace(b, (xa, 2.1, 0.4), (xb, 2.1, z0 + H - 0.2))
    yc = -1.0                                                                                    # catwalk at the foot
    R.plates(b, 0.0, W, yc, -0.05, z0 - 0.25, 0.03, "grate", n=8)
    for xx in np.arange(1.0, W, 2.5):
        R.bar(b, (xx, 0.0, z0 - 0.28), (xx, yc, z0 - 0.28), 0.06, 0.10, "grey", ch=0.003)
        R.bar(b, (xx, 0.6, 0.3), (xx, yc + 0.1, z0 - 0.32), 0.07, 0.07, "grey", ch=0.003)
    R.rail_run(b, np.array((0.0, yc + 0.04, z0 - 0.25)), np.array((W, yc + 0.04, z0 - 0.25)), "grey", h=1.0, post=2.0, toe=True)
    for xx in (2.0, 6.0, 10.0, 14.0):                                                            # four LED floods on goosenecks
        R.tube(b, (xx, yc + 0.1, z0 + 0.8), (xx, yc - 0.6, z0 + 0.6), "grey", 0.03)
        hs = R.geo.box((0.40, 0.14, 0.26), bevel=0.01)
        R.geo.transform(hs, loc=(xx, yc - 0.7, z0 + 0.55), rot=(55, 0, 0))
        b.absorb(hs, "grey")
        ln = R.geo.box((0.36, 0.01, 0.22), bevel=0.003)
        R.geo.transform(ln, loc=(xx, yc - 0.62, z0 + 0.66), rot=(55, 0, 0))
        b.absorb(ln, "led")
    return R.done(ctx, b, "SM_Roof_BillboardFrame_16x8", M, ground=False, faces=[("M_Sign_MT_Face", fr)],
                  expect_size=(None, None, None),
                  notes="C1, the roof billboard on C's east edge (world x -11..-8.8, z -36..-20; face 19.6 to 27.6, facing east): a "
                        "lightbox (face C1_MarloweFinch from Sign_MT_Atlas1, 200 nits at night) on six I legs, braces, a catwalk with "
                        "rail and four LED floods. Its legs and catwalk are the cover line (data). Pivot: bottom-left of the face "
                        "projected to the roof, face -Y (rot_z 90 faces it east).")


def m_ledtile(ctx, M):
    """One 2 x 2 m LED cabinet module: the screen face (0..1 over the tile), bezel strips, the cabinet back with handles
    and a power box. The art-only screens (E1, E2a/b, E3, S1) are rows and columns of it. Pivot: bottom-left of the
    face, face toward -Y."""
    b = B(631, step=1.0)
    fr = screen_face(b, 0.0, 2.0, 0.0, 2.0, 0.0)
    for (za, zb) in ((0.0, 0.06), (1.94, 2.0)):                                                  # module rails, 6 cm
        bx(b, (0.0, -0.004, za), (2.0, 0.06, zb), "black", pin=False, axis="x")
    cabinet_backs(b, 0.0, 2.0, 0.0, 2.0, 0.02, cell=1.0, depth=0.14)
    return R.done(ctx, b, "SM_Sign_LEDWall_Tile_2m", M, ground=False, faces=[(SCREEN, fr)], expect_size=(2.0, None, 2.0),
                  notes="LED cabinet module 2 x 2 m: screen face (M_MI_Screen, 0..1 per tile; the MI offsets each tile into its "
                        "screen's slide cell by row and column), back plates, handles, power boxes. E1 12 x 9 tiles, E2a/b 4 x 10, "
                        "E3 10 x 6 (turned 6 degrees apart for the curve), S1 6 x 3. Pivot: bottom-left of the face, face -Y.")


def m_ticker(ctx, M):
    """A 4 m module of the theatre's ticker band (0.8 m tall): the band face (M_MT_Ticker, 0..1 over the module, u
    continues module to module), top and bottom hoods, a steel box behind. Pivot: bottom-left of the face, face -Y."""
    b = B(641, step=1.0)
    L, H = 4.0, 0.8
    R.face_quad(b, 0.0, L, 0.0, H, 0.0, "signTicker")
    fr = ((0.0, 0.0, 0.0), X, Z, (L, H))
    bx(b, (0.0, 0.0, -0.05), (L, 0.40, H + 0.05), "black", axis="x")
    for (za, zb, d) in ((H, H + 0.10, -0.20), (-0.10, 0.0, -0.12)):
        bx(b, (0.0, d, za), (L, 0.02, zb), "black", ch=0.006, pin=False, axis="x")
    for xx in (0.0, L - 0.02):
        bx(b, (xx, -0.12, -0.10), (xx + 0.02, 0.02, H + 0.10), "black", pin=False, axis="z")
    return R.done(ctx, b, "SM_Sign_Ticker_4m", M, ground=False, faces=[("M_MT_Ticker", fr)], expect_size=(None, None, None),
                  notes="Ticker band module 4 x 0.8 m (six of them make the 24 m band on the theatre at y 8.0 to 8.8, x 30, z -30..-6): "
                        "face M_MT_Ticker (0..1 per module, the MI adds the module's index to u), hoods, box. Pivot: bottom-left, face -Y.")


def m_towerstack(ctx, M):
    """N1: three 14 x 8 m screens stacked (1 m apart) on a tower crown north of the square, art only: three faces in
    the screen slot (each 0..1), bezels, a box-girder frame and a back truss, a parapet-like base. Pivot: bottom-left of
    the lowest face, faces toward -Y (south, toward the square)."""
    b = B(651, step=1.5)
    W, H, gap = 14.0, 8.0, 1.0
    faces = []
    for i in range(3):
        z0 = i * (H + gap)
        faces.append((SCREEN, screen_face(b, 0.0, W, z0, z0 + H, 0.0), (z0 - 0.01, z0 + H + 0.01)))
        bezel(b, 0.0, W, z0, z0 + H, 0.0, w=0.20, d=0.15)
        bx(b, (-0.2, 0.02, z0), (W + 0.2, 0.30, z0 + H), "black", axis="x")
    top = 3 * H + 2 * gap
    truss_back(b, 0.0, W, 0.0, top, 0.30, post_every=3.5, girt_every=3.0, depth=0.6)
    for xx in (-0.6, W + 0.2):                                                                   # box-girder side frames
        bx(b, (xx, -0.4, -2.0), (xx + 0.4, 1.2, top + 1.0), "grey", ch=0.01, axis="z")
    bx(b, (-0.6, -0.4, top + 0.4), (W + 0.6, 1.2, top + 1.0), "grey", ch=0.01, axis="x")
    bx(b, (-0.6, -0.6, -2.0), (W + 0.6, 1.4, -0.4), "stone", ch=0.02, axis="x")
    for xx in np.arange(0.5, W, 2.0):                                                            # maintenance light bar
        R.tube(b, (xx, -0.25, -0.3), (xx, -0.25, -0.05), "grey", 0.03)
    return R.done(ctx, b, "SM_Sign_TowerStack", M, ground=False, faces=faces, expect_size=(None, None, None),
                  notes="N1, the north tower's stack of three 14 x 8 m screens (art only, beyond z -38): three faces in M_MI_Screen "
                        "(each 0..1), bezels, side girders, a back truss, a stone base. Pivot: bottom-left of the lowest face, face -Y.")


PROPS = [m_gantry, m_ledwall, m_billboard, m_ledtile, m_ticker, m_towerstack]
