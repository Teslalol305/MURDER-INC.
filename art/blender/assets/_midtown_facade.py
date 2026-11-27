"""Midtown kit, part 7 (round 3): the facade tables, the storefront carriers and the east podium modules.

The Block's facade kit is not changed (facade.py, signs.py and place_buildings.py stay byte for byte, midtown.md 17.13's per-level
table is done here instead): this module draws Midtown's own, much lighter modules and holds the tables that put them on the
level's facade colliders (the placements are assembled in _midtown_place.facades).

    SM_Facade_MT_Bay_{Red,Buff,Stone}_3p1   one storey of one bay, 3.10 x 3.30: the wall in the brick or stone slot, a recessed
                                            window (frame, mullion, transom, stone sill, 4 cm storey ledge) whose pane is the
                                            window-grid slot M_MT_WindowGrid (a lit or dark window per pane from its world
                                            position: the master material of midtown_art.md 8). About 150 triangles
    SM_Facade_MT_Cornice_3p1                a cast-stone cornice with dentils and a flashing, 0.55 high
    SM_Facade_MT_Ground_Blank_3p1           4.70 m of base: a stone plinth, pilasters, a steel louvre, a service door bay
    SM_Facade_MT_Shop_{Souvenir,Slice,Camera,Bank,Chop,Pharmacy}  the six shopfronts (3.6 high), the glazing, the door, the bulkhead
                                            and the interior glow (midtown.md 12.4); the bank is shuttered and closed
    SM_Sign_MT_Band_{6,7,8,10}m             the storefront carriers: a steel fascia box 1.10 high with a lit face 0.9 high (the bands
                                            of Sign_MT_Atlas1); each placement says its face
    SM_Facade_MT_TheatreFront_8m, SM_Facade_MT_HotelFront_8m   the east podium modules (4.70 high): the theatre's doors, posters and
                                            brass; the hotel's revolving door and glass
    SM_Facade_Marquee_A, SM_Facade_Marquee_B  THE MERIDALE THEATRE's marquee (8.0 x 2.0, bulbs, name and show boards) and HOTEL
                                            CASTELLANE's canopy (6.0 x 2.4)
Module frame: the Block's (pivot at the bottom-left of the outer face, running +X, outer face toward -Y, the wall plane y = 0, the
wall 0.30 behind it; everything proud has y < 0). Brick UVs are real metres from the module pivot (the placed instance's offset or
world-aligned UVs make the bond run through). The art has no collision: the facade colliders of the level data decide.
"""
import math

import numpy as np

from assets import _midtown_dress as D
from assets import _midtown_roof as R
from assets import _midtown_square as SQ
from assets import facade as fc
from assets.facade import B, bx, rod, sheet
from mi import geo, steel

X, Y, Z = np.eye(3)
done, quad, tube = SQ.done, SQ.quad, SQ.tube
BAY, STOREY, GROUND, T = 3.10, 3.30, 4.70, 0.30


def wall_slot(kind):
    return {"Red": "brickRed", "Buff": "brickBuff", "Stone": "stone"}[kind]


def m_bay(ctx, M, kind):
    """One storey of one bay: the wall with a 1.94 x 1.77 opening, the recessed pane (M_MT_WindowGrid), a steel frame with a
    mullion and a transom, a stone sill on horns, the storey ledge."""
    b = B(1401 + len(kind), step=0.8)
    s = wall_slot(kind)
    x0, x1, z0, z1 = 0.58, 2.52, 0.78, 2.55
    fc.wall_opening(b, BAY, STOREY, x0, x1, z0, z1, slot=s)
    bx(b, (x0, 0.17, z0), (x1, 0.19, z1), "windowGrid", pin=False, axis="x")                              # the pane, 17 cm behind the wall plane
    for (a, c, e, f) in ((x0, x1, z0, z0 + 0.06), (x0, x1, z1 - 0.06, z1), (x0, x0 + 0.06, z0, z1), (x1 - 0.06, x1, z0, z1)):
        bx(b, (a, 0.10, e), (c, 0.20, f), "grey", ch=0.004, pin=False)                                     # the frame
    bx(b, (BAY / 2 - 0.03, 0.12, z0), (BAY / 2 + 0.03, 0.20, z1), "grey", pin=False, axis="z")            # mullion
    bx(b, (x0, 0.12, z0 + 0.62 * (z1 - z0) - 0.03), (x1, 0.20, z0 + 0.62 * (z1 - z0) + 0.03), "grey", pin=False, axis="x")   # transom
    bx(b, (x0 - 0.10, -0.09, z0 - 0.09), (x1 + 0.10, 0.10, z0), "stone", ch=0.008, axis="x")              # sill with horns
    bx(b, (x0 - 0.06, -0.03, z1), (x1 + 0.06, 0.06, z1 + 0.10), "stone", ch=0.006, pin=False, axis="x")   # lintel course
    bx(b, (0.0, -0.04, 0.0), (BAY, 0.0, 0.14), "stone", ch=0.004, pin=False, axis="x")                     # the storey ledge (4 cm proud)
    return done(ctx, b, "SM_Facade_MT_Bay_%s_3p1" % kind, M, ground=False, expect_size=(BAY, None, STOREY),
                notes=("Midtown facade bay, one storey, 3.10 x 3.30 (stretched to 3.225 / 3.10 / 3.16 / 3.06 by the building tables): %s wall, "
                       "a 1.94 x 1.77 recessed window with a steel frame, mullion, transom and stone sill, the 4 cm storey ledge; the pane "
                       "is the window-grid slot M_MT_WindowGrid (lit or dark per window from its world position: 24 percent of the masses, "
                       "34 percent of the towers). Pivot: bottom-left of the outer face, face -Y.") % kind)


def m_cornice(ctx, M):
    b = B(1411, step=0.8)
    bx(b, (0.0, -0.10, 0.0), (BAY, 0.0, 0.14), "stone", ch=0.006, axis="x")
    bx(b, (0.0, -0.20, 0.14), (BAY, 0.0, 0.34), "stone", ch=0.01, axis="x")
    for i in range(14):                                                                                   # dentils
        x = 0.06 + i * (BAY - 0.12) / 13
        bx(b, (x - 0.06, -0.24, 0.14), (x + 0.06, -0.20, 0.30), "stone", pin=False, axis="x")
    bx(b, (0.0, -0.36, 0.34), (BAY, 0.0, 0.50), "stone", ch=0.012, axis="x")
    bx(b, (0.0, -0.40, 0.50), (BAY, 0.04, 0.55), "galv", ch=0.004, pin=False, axis="x")
    return done(ctx, b, "SM_Facade_MT_Cornice_3p1", M, ground=False, expect_size=(BAY, None, 0.55),
                notes="Cast-stone cornice 3.10 x 0.55 (0.40 proud) with dentils and a galvanised flashing: it overlaps the top 0.55 of the "
                      "last storey under the roof's parapet (the west blocks) or closes the tall facades (the east and south). Pivot: "
                      "bottom-left of the outer face, face -Y.")


def m_ground_blank(ctx, M):
    b = B(1421, step=0.8)
    H = GROUND
    bx(b, (0.0, -0.06, 0.0), (BAY, T, 0.55), "conc", ch=0.006, axis="x")                                 # plinth
    bx(b, (0.0, 0.0, 0.55), (BAY, T, H), "stone", axis="x")
    for x in (0.0, BAY - 0.20):
        bx(b, (x, -0.10, 0.55), (x + 0.20, 0.0, H - 0.55), "stone", ch=0.008, axis="z")                   # pilasters
    bx(b, (0.0, -0.08, 3.96), (BAY, 0.0, 4.10), "stone", ch=0.006, axis="x")                              # belt course
    bx(b, (0.0, -0.12, H - 0.30), (BAY, 0.0, H), "stone", ch=0.008, axis="x")
    bx(b, (0.60, -0.02, 0.85), (2.50, 0.02, 2.55), "black", ch=0.006, axis="x", pin=False)                 # a steel service panel
    for k in range(7):                                                                                    # louvre slats
        bx(b, (0.72, -0.05, 1.00 + k * 0.20), (2.38, 0.02, 1.08 + k * 0.20), "grille", pin=False, axis="x")
    for k in range(2):
        bx(b, (0.58, -0.04, 0.83 + k * 1.72), (2.52, 0.00, 0.89 + k * 1.72), "galv", pin=False, axis="x")
    return done(ctx, b, "SM_Facade_MT_Ground_Blank_3p1", M, ground=True, expect_size=(BAY, None, H),
                notes="Midtown blank ground storey 3.10 x 4.70: concrete plinth, stone wall with pilasters and a belt course, a steel "
                      "service louvre panel in a frame. Used between the shopfronts and for the tower bases. Pivot: bottom-left of the "
                      "outer face, face -Y.")


def shopfront(ctx, M, name, w, door, bulk, notes, closed=False, wall="stone", awning=False, display="plain", glow=True):
    """A shop front w wide, 3.6 high: stone piers 0.55 each side, a bulkhead, plate glass in 1.5 m bays on a steel frame with a
    dark interior and a strip of light behind it, a recessed door pair at `door` (centre) 1.8 wide, a head with the roll shutter
    hood. closed: the roll grille is down over the glass."""
    b = B(abs(hash(name)) % 997 + 1500, step=0.8)
    H = 3.6
    for x in (0.0, w - 0.55):
        bx(b, (x, -0.10, 0.0), (x + 0.55, T, H), wall if wall in ("stone", "conc") else "stone", ch=0.008, axis="z")
    bx(b, (0.55, 0.0, H - 0.20), (w - 0.55, T, H), "stone", axis="x")
    bx(b, (0.55, -0.02, 0.0), (w - 0.55, 0.20, bulk), "standBlack" if not closed else "stone", ch=0.006, axis="x")      # bulkhead
    d0, d1 = door - 0.9, door + 0.9
    spans = [(0.55, d0), (d1, w - 0.55)] if door else [(0.55, w - 0.55)]
    for (a, c) in spans:
        n = max(1, int(round((c - a) / 1.5)))
        bx(b, (a, 0.18, bulk), (c, 0.22, H - 0.20), "glassTint", pin=False, axis="x")                      # the glass
        bx(b, (a, 0.24, bulk), (c, 0.90, H - 0.20), "interior", pin=False, axis="x")
        if glow:
            bx(b, (a + 0.1, 0.30, H - 0.30), (c - 0.1, 0.40, H - 0.24), "warm", pin=False, axis="x")       # light strip inside
        for i in range(n + 1):
            xx = a + (c - a) * i / n
            bx(b, (xx - 0.04, 0.10, bulk), (xx + 0.04, 0.24, H - 0.20), "black", pin=False, axis="z")
        bx(b, (a, 0.10, bulk), (c, 0.24, bulk + 0.07), "black", pin=False, axis="x")
        bx(b, (a, 0.10, H - 0.27), (c, 0.24, H - 0.20), "black", pin=False, axis="x")
        if display == "shelves" and not closed:
            for k in range(3):
                bx(b, (a + 0.2, 0.30, bulk + 0.35 + k * 0.55), (c - 0.2, 0.62, bulk + 0.39 + k * 0.55), "stainless", pin=False, axis="x")
                for j in range(int((c - a - 0.5) / 0.35)):
                    bx(b, (a + 0.3 + j * 0.35, 0.34, bulk + 0.39 + k * 0.55), (a + 0.55 + j * 0.35, 0.58, bulk + 0.62 + k * 0.55 + 0.05 * (j % 3)),
                       ["white", "plasticBlack", "umbrella", "yellow"][(j + k) % 4], pin=False)
    if door:
        bx(b, (d0, 0.30, 0.0), (d1, T, H - 0.20), "interior", pin=False, axis="z")                        # the recess
        for side in (-1, 1):
            xs = door + side * 0.45
            bx(b, (xs - 0.43, 0.24, 0.06), (xs + 0.43, 0.27, 2.45), "glassTint", pin=False)
            for xr in (xs - 0.45, xs + 0.45):
                bx(b, (xr - 0.04, 0.22, 0.0), (xr + 0.04, 0.30, 2.50), "brass", pin=False, axis="z")
            bx(b, (xs - 0.43, 0.22, 2.42), (xs + 0.43, 0.30, 2.50), "brass", pin=False, axis="x")
            bx(b, (xs - 0.43, 0.22, 0.0), (xs + 0.43, 0.30, 0.20), "brass", pin=False, axis="x")
            tube(b, (xs - side * 0.30, 0.19, 0.95), (xs - side * 0.30, 0.19, 1.30), "brass", 0.03)
        bx(b, (d0, 0.0, 2.50), (d1, 0.30, H - 0.20), "black", pin=False, axis="x")
    hood = (0.55, w - 0.55)
    bx(b, (hood[0], -0.12, H - 0.50), (hood[1], 0.10, H - 0.20), "black", ch=0.01, pin=False, axis="x")      # the shutter hood
    if closed:
        for (a, c) in spans:                                                                                # grille down over the glass
            for xx in np.arange(a + 0.12, c, 0.18):
                bx(b, (xx - 0.03, 0.06, bulk), (xx + 0.03, 0.12, H - 0.50), "shutter", pin=False, axis="z")
            for z in np.arange(bulk + 0.2, H - 0.50, 0.36):
                bx(b, (a, 0.06, z - 0.03), (c, 0.12, z + 0.03), "shutter", pin=False, axis="x")
    if awning:
        b.poly_plate([(0.7, -1.20, H - 0.35), (w - 0.7, -1.20, H - 0.35), (w - 0.7, 0.0, H - 0.05), (0.7, 0.0, H - 0.05)][::-1], 0.02, "umbrella", kind=b.OTHER)
        bx(b, (0.7, -1.22, H - 0.60), (w - 0.7, -1.18, H - 0.35), "umbrella", pin=False, axis="x")
    return done(ctx, b, name, M, ground=True, expect_size=(w, None, H), notes=notes)


def m_band(ctx, M, w):
    """A storefront band carrier w x 1.10: a steel fascia box with its lit face 0.9 high (M_Sign_MT_Face on 0..1 UVs; the placement
    names the face), a belt course above. Pivot: bottom-left of the face's outer plane, face -Y."""
    b = B(1431 + w, step=0.8)
    bx(b, (0.0, -0.01, 0.0), (w, T, 1.10), "black", ch=0.006, axis="x", pin=False)
    bx(b, (0.0, -0.14, 0.96), (w, 0.0, 1.10), "stone", ch=0.006, axis="x", pin=False)
    bx(b, (0.0, -0.10, 0.0), (w, 0.0, 0.05), "black", pin=False, axis="x")
    for x in (0.0, w - 0.06):
        bx(b, (x, -0.10, 0.0), (x + 0.06, 0.0, 1.0), "black", pin=False, axis="z")
    faces = [quad(b, (0.06, -0.0905, 0.05), X, Z, w - 0.12, 0.90, "signFace")]
    bx(b, (0.06, -0.09, 0.05), (w - 0.06, -0.0895, 0.95), "black", pin=False, axis="x")
    return done(ctx, b, "SM_Sign_MT_Band_%dm" % w, M, ground=False, faces=faces, expect_size=(w, None, 1.10),
                notes="Storefront band carrier %d x 1.10: a black steel fascia box, a belt course over it, the lit face %.2f x 0.90 (200 nits; "
                      "the faces of Sign_MT_Atlas1 of the shops: SEVENTH AV SOUVENIRS 8, SLICE OF SEVENTH 6, SHUTTERBOX 10, BELLHAVEN "
                      "SAVINGS 8 unlit, BRANNIGAN'S 8, ASHBY & CROSS 7). Pivot: bottom-left of the face, face -Y." % (w, w - 0.12))


def m_theatre_front(ctx, M):
    """THE MERIDALE THEATRE's front, 8.0 x 4.70: stone surround, a six-leaf brass and glass door in a 6.0 m recess lit by a warm
    ceiling, two poster cases (dark, lit edge), a box-office window at one end, brass kick plates and push bars. The marquee hangs
    over its middle."""
    b = B(1441, step=0.8)
    H, w = GROUND, 8.0
    bx(b, (0.0, -0.06, 0.0), (w, T, 0.45), "conc", ch=0.006, axis="x")
    for x in (0.0, w - 0.9):
        bx(b, (x, -0.12, 0.45), (x + 0.9, T, H), "stone", ch=0.01, axis="z")
    bx(b, (0.9, 0.0, 3.60), (w - 0.9, T, H), "stone", axis="x")                                             # head
    bx(b, (0.9, 0.0, 0.45), (w - 0.9, 0.36, 3.60), "interior", pin=False, axis="x")                         # the lobby, dark
    bx(b, (1.0, 0.18, 3.46), (w - 1.0, 0.34, 3.52), "warm", pin=False, axis="x")                            # ceiling glow in the recess
    for i in range(6):
        x = 1.05 + i * (w - 2.1) / 6
        bx(b, (x + 0.02, 0.34, 0.50), (x + (w - 2.1) / 6 - 0.02, 0.37, 2.55), "glassTint", pin=False)
        for xr in (x, x + (w - 2.1) / 6):
            bx(b, (xr - 0.04, 0.30, 0.45), (xr + 0.04, 0.38, 2.60), "brass", pin=False, axis="z")
        bx(b, (x, 0.30, 2.55), (x + (w - 2.1) / 6, 0.38, 2.62), "brass", pin=False, axis="x")
        bx(b, (x, 0.30, 0.45), (x + (w - 2.1) / 6, 0.38, 0.65), "brass", pin=False, axis="x")
        tube(b, (x + 0.12, 0.28, 0.95), (x + 0.12, 0.28, 1.35), "brass", 0.03)
    bx(b, (1.0, 0.0, 2.62), (w - 1.0, 0.38, 3.46), "standBlack", pin=False, axis="x")                       # transom panel
    for x in (0.12, w - 0.78):                                                                              # poster cases on the piers
        bx(b, (x, -0.16, 1.00), (x + 0.66, -0.06, 2.50), "standBlack", ch=0.008, pin=False, axis="z")
        bx(b, (x + 0.05, -0.17, 1.05), (x + 0.61, -0.155, 2.45), "interior", pin=False)
        bx(b, (x + 0.05, -0.172, 1.05), (x + 0.61, -0.16, 1.11), "warm", pin=False, axis="x")
        bx(b, (x + 0.05, -0.172, 2.39), (x + 0.61, -0.16, 2.45), "warm", pin=False, axis="x")
    return done(ctx, b, "SM_Facade_MT_TheatreFront_8m", M, ground=True, expect_size=(w, None, H),
                notes="THE MERIDALE THEATRE's front 8.0 x 4.70: stone surround, a six-leaf brass and glass door in a 6.0 m recess with a "
                      "warm ceiling glow, two dark poster cases with lit edges, brass kick plates and push bars. Two modules stand side by "
                      "side over z -22..-6; the marquee (SM_Facade_Marquee_A) hangs over the join. Pivot: bottom-left of the outer face, "
                      "face -Y.")


def m_hotel_front(ctx, M):
    """HOTEL CASTELLANE's front 8.0 x 4.70: a stone base, dark glazing in brass frames, a revolving door 2.4 across with four
    wings (a drum of glass between brass posts), a swing door each side, brass handrails and a canopy plate over the door."""
    b = B(1451, step=0.8)
    H, w = GROUND, 8.0
    bx(b, (0.0, -0.06, 0.0), (w, T, 0.50), "stone", ch=0.006, axis="x")
    bx(b, (0.0, 0.0, 0.50), (0.7, T, H), "stone", axis="z")
    bx(b, (w - 0.7, 0.0, 0.50), (w, T, H), "stone", axis="z")
    bx(b, (0.7, 0.0, 3.70), (w - 0.7, T, H), "stone", axis="x")
    bx(b, (0.7, 0.20, 0.50), (w - 0.7, 0.30, 3.70), "glassTint", pin=False, axis="x")
    bx(b, (0.7, 0.30, 0.50), (w - 0.7, 0.9, 3.70), "interior", pin=False, axis="x")
    bx(b, (0.8, 0.40, 3.54), (w - 0.8, 0.50, 3.60), "warm", pin=False, axis="x")
    for x in np.linspace(0.7, w - 0.7, 8):
        bx(b, (x - 0.04, 0.12, 0.50), (x + 0.04, 0.30, 3.70), "brass", pin=False, axis="z")
    bx(b, (0.7, 0.12, 3.62), (w - 0.7, 0.30, 3.70), "brass", pin=False, axis="x")
    bx(b, (0.7, 0.12, 0.50), (w - 0.7, 0.30, 0.58), "brass", pin=False, axis="x")
    cx = w / 2
    rod(b, (cx, 0.10, 0.55), (cx, 0.10, 2.65), 1.20, "glassTint", n=24)                                      # the revolving door's drum
    rod(b, (cx, 0.10, 2.62), (cx, 0.10, 2.78), 1.25, "brass", n=24)
    rod(b, (cx, 0.10, 0.50), (cx, 0.10, 0.58), 1.25, "brass", n=24)
    for a in range(4):                                                                                      # the four wings
        t = math.radians(45 + 90 * a)
        tube(b, (cx + 1.0 * math.cos(t), 0.10 + 1.0 * math.sin(t), 0.60), (cx + 1.0 * math.cos(t), 0.10 + 1.0 * math.sin(t), 2.60), "brass", 0.03)
        bx(b, (cx + 0.50 * math.cos(t) - 0.03, 0.10 + 0.50 * math.sin(t) - 0.03, 0.62), (cx + 0.50 * math.cos(t) + 0.03, 0.10 + 0.50 * math.sin(t) + 0.03, 2.58), "brass", pin=False, axis="z")
    for s in (-1, 1):                                                                                       # swing doors either side
        xs = cx + s * 2.0
        bx(b, (xs - 0.50, 0.22, 0.58), (xs + 0.50, 0.26, 2.50), "interior", pin=False)
        for xr in (xs - 0.50, xs + 0.50):
            bx(b, (xr - 0.04, 0.18, 0.50), (xr + 0.04, 0.30, 2.60), "brass", pin=False, axis="z")
        tube(b, (xs - s * 0.36, 0.17, 1.00), (xs - s * 0.36, 0.17, 1.40), "brass", 0.03)
    for s in (-1, 1):
        tube(b, (cx + s * 3.0, -0.30, 0.0), (cx + s * 3.0, -0.30, 0.95), "brass", 0.03)
    tube(b, (cx - 3.0, -0.30, 0.95), (cx + 3.0, -0.30, 0.95), "brass", 0.03)
    return done(ctx, b, "SM_Facade_MT_HotelFront_8m", M, ground=True, expect_size=(w, None, H),
                notes="HOTEL CASTELLANE's front 8.0 x 4.70: stone base and piers, dark glazing in brass frames lit by a warm ceiling, a "
                      "2.4 m revolving door drum with four brass-posted wings, a swing door each side, brass handrails at the kerb. The "
                      "canopy (SM_Facade_Marquee_B) hangs over it. Pivot: bottom-left of the outer face, face -Y.")


def bulbs(b, x0, x1, y, z, n=None):
    n = n or int(round((x1 - x0) / 0.20))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        bx(b, (x - 0.035, y - 0.035, z - 0.035), (x + 0.035, y + 0.035, z + 0.035), "bulb", ch=0.012, pin=False)


def m_marquee_a(ctx, M):
    """THE MERIDALE THEATRE's marquee, 8.0 wide, 2.0 out, 2.4 high: a black steel box on two I-beam brackets into the wall, a lit
    name band on the front over the show board (LAMPLIGHT AVENUE, A NEW MUSICAL), the same show board on both ends, three rows of
    marquee bulbs round the front and a soffit with recessed warm lights. Pivot: bottom-left of the front face's wall plane
    at the soffit (the box runs toward -Y); the front face at y = -2.0."""
    b = B(1461, step=0.8)
    w, d, h = 8.0, 2.0, 2.4
    bx(b, (0.0, -d, 0.0), (w, 0.0, 0.12), "standBlack", ch=0.006, axis="x")                                  # soffit plate
    for i in range(6):
        bx(b, (0.6 + i * 1.36, -d + 0.2, -0.02), (0.9 + i * 1.36, -0.3, 0.0), "warm", pin=False, axis="y")  # soffit lights
    bx(b, (0.0, -d, 0.12), (w, -d + 0.14, h), "standBlack", ch=0.006, axis="x")                              # front
    bx(b, (0.0, -d, 0.12), (0.14, 0.0, h), "standBlack", ch=0.006, axis="y")                                # ends
    bx(b, (w - 0.14, -d, 0.12), (w, 0.0, h), "standBlack", ch=0.006, axis="y")
    bx(b, (0.0, -d, h), (w, 0.0, h + 0.12), "standBlack", ch=0.006, axis="x")
    for x in (1.2, w - 1.2):                                                                                 # the I-beam brackets into the wall
        bx(b, (x - 0.08, -d + 0.14, 0.12), (x + 0.08, 0.0, 0.42), "black", ch=0.004, pin=False, axis="y")
    # the front faces: the name band (top, 8.0 x 0.80: Band_MeridaleTheatre's 12 x 1.2 at 10:1) over the show board (8.0 x 1.4)
    f1 = quad(b, (0.0, -d - 0.0005, 1.60 + 0.0), X, Z, w, 0.80, "signFace")
    f2 = quad(b, (0.0, -d - 0.0005, 0.20), X, Z, w, 1.40, "signFace")
    bx(b, (0.0, -d - 0.004, 0.12), (w, -d - 0.001, 0.20), "brass", pin=False, axis="x")
    bx(b, (0.0, -d - 0.004, 1.60 - 0.06), (w, -d - 0.001, 1.60), "brass", pin=False, axis="x")
    bx(b, (0.0, -d - 0.004, 2.40 - 0.06), (w, -d - 0.001, 2.40), "brass", pin=False, axis="x")
    for z in (0.14, 1.62, 2.38):
        bulbs(b, 0.1, w - 0.1, -d - 0.04, z)
    bx(b, (0.0, -d + 0.14, h - 0.10), (w, -0.5, h - 0.04), "interior", pin=False, axis="x")
    faces = [f1, f2]
    return done(ctx, b, "SM_Facade_Marquee_A", M, ground=False, faces=faces, expect_size=(w, None, None),
                notes="THE MERIDALE THEATRE's marquee 8.0 x 2.0 x 2.4 (midtown.md 14.2's SM_Facade_Marquee_A): black steel box on I-beam "
                      "brackets into the wall (no tie rods), a lit name band (Band_MeridaleTheatre, 12 x 1.2 squeezed to 8 x 0.8: the "
                      "same 10:1) over the show board (Marquee_Lamplight: LAMPLIGHT AVENUE, A NEW MUSICAL), brass trim, three rows of "
                      "bulbs (MI_Lamp_MarqueeBulb, 350 nits, a slow chase of 3 s: one bulb texture, no flashing), a soffit with warm "
                      "lights. Hangs at 3.6 over the sidewalk, centred on the theatre's doors (z -14). Pivot: bottom-left at the wall "
                      "plane, the box toward -Y.")


def m_marquee_b(ctx, M):
    """HOTEL CASTELLANE's canopy, 6.0 wide, 2.4 out, 0.9 high: a flat stainless and dark-glass canopy on cantilever beams, a lit
    fascia (Band_HotelCastellane at 8.9:1: 6.2 x 0.70), a brass edge strip, soffit downlights and a drip edge. Pivot as the marquee."""
    b = B(1471, step=0.8)
    w, d, h = 6.0, 2.4, 0.90
    bx(b, (0.0, -d, 0.0), (w, 0.0, 0.12), "standBlack", ch=0.006, axis="x")
    for i in range(5):
        bx(b, (0.5 + i * 1.25, -d + 0.4, -0.02), (0.8 + i * 1.25, -0.4, 0.0), "warm", pin=False, axis="y")
    bx(b, (0.0, -d, 0.12), (w, -d + 0.12, h), "standBlack", ch=0.006, axis="x")
    for x in (0.0, w - 0.12):
        bx(b, (x, -d, 0.12), (x + 0.12, 0.0, h - 0.10), "standBlack", ch=0.006, axis="y")
    bx(b, (0.12, -d + 0.12, h - 0.14), (w - 0.12, 0.0, h - 0.10), "glassTint", pin=False, axis="x")          # the glass roof
    bx(b, (0.0, -d, h - 0.10), (w, 0.0, h), "stainless", ch=0.006, axis="x")
    for x in (1.0, w - 1.0):
        bx(b, (x - 0.08, -d + 0.12, 0.12), (x + 0.08, 0.0, 0.50), "black", ch=0.004, pin=False, axis="y")
    f = quad(b, (-0.1, -d - 0.0005, 0.12), X, Z, w + 0.2, 0.70, "signFace")
    bx(b, (-0.1, -d - 0.004, 0.05), (w + 0.1, -d - 0.001, 0.12), "brass", pin=False, axis="x")
    bx(b, (-0.1, -d - 0.004, 0.80), (w + 0.1, -d - 0.001, 0.86), "brass", pin=False, axis="x")
    return done(ctx, b, "SM_Facade_Marquee_B", M, ground=False, faces=[f], expect_size=(w, None, None),
                notes="HOTEL CASTELLANE's canopy 6.0 x 2.4 x 0.9 (midtown.md 14.2's SM_Facade_Marquee_B): a flat steel canopy with a "
                      "dark-glass roof (opaque) on cantilever beams into the wall (no columns, no tie rods), a lit fascia (Band_Hotel"
                      "Castellane, 8:1 at 6.2 x 0.70), brass edge strips and soffit downlights. Hangs at 3.0 over the sidewalk, centred "
                      "on the hotel's doors (z 6). Pivot: bottom-left at the wall plane, the canopy toward -Y.")


SHOPS = [
    ("SM_Facade_MT_Shop_Souvenir", 8.0, 4.0, 0.55, "Souvenir shop front 8.0 x 3.6 (SEVENTH AV SOUVENIRS; its band is SM_Sign_MT_Band_8m): "
     "a wide glazed front with a door pair, racks of caps and shirts, a warm interior glow, a roll shutter hood. Pivot: bottom-left of "
     "the outer face, face -Y.", dict(display="shelves")),
    ("SM_Facade_MT_Shop_Slice", 6.0, 3.0, 0.60, "Pizza slice shop front 6.0 x 3.6 (SLICE OF SEVENTH; band SM_Sign_MT_Band_6m): glazing "
     "with a door, a green-and-white awning (no red), warm interior glow. Pivot: bottom-left of the outer face.", dict(awning=True)),
    ("SM_Facade_MT_Shop_Camera", 10.0, 5.0, 0.55, "Camera and electronics shop front 10.0 x 3.6 (SHUTTERBOX CAMERA & ELECTRONICS; band "
     "SM_Sign_MT_Band_10m): a wide glazed front with a door, shelves of boxes, cool interior glow. Pivot: bottom-left of the outer face.",
     dict(display="shelves")),
    ("SM_Facade_MT_Shop_Bank", 8.0, 4.0, 0.90, "Closed bank lobby front 8.0 x 3.6 (BELLHAVEN SAVINGS; band SM_Sign_MT_Band_8m, unlit): a "
     "stone portal, dark glass behind a steel roll grille that is down, a brass door pair, no glow. Pivot: bottom-left of the outer face.",
     dict(closed=True, glow=False)),
    ("SM_Facade_MT_Shop_Chop", 8.0, 4.0, 0.60, "Steakhouse front 8.0 x 3.6 (BRANNIGAN'S CHOP HOUSE; band SM_Sign_MT_Band_8m): a dark timber "
     "bulkhead, glazing with a door pair, a warm glow, an awning. Pivot: bottom-left of the outer face.", dict(awning=True)),
    ("SM_Facade_MT_Shop_Pharmacy", 7.0, 3.5, 0.55, "Pharmacy front 7.0 x 3.6 (ASHBY & CROSS PHARMACY; band SM_Sign_MT_Band_7m): wide "
     "glazing, a door, bright cool interior glow. Pivot: bottom-left of the outer face.", dict(display="shelves")),
]

PROPS = [lambda c, M: m_bay(c, M, "Red"), lambda c, M: m_bay(c, M, "Buff"), lambda c, M: m_bay(c, M, "Stone"), m_cornice, m_ground_blank,
         lambda c, M: [shopfront(c, M, n, w, d, bk, notes, **kw) for (n, w, d, bk, notes, kw) in SHOPS],
         lambda c, M: [m_band(c, M, w) for w in (6, 7, 8, 10)],
         m_theatre_front, m_hotel_front, m_marquee_a, m_marquee_b]
