"""Midtown kit, part 6 (round 3): the premiere's set and the city bus.

The unit base the level data blocks out (midtown.md 1, 2.2, 9.1, 12.4): the production, broadcast, satellite, catering, cable,
staging and generator trucks, the production and screen trailers, light towers and truss towers, press walls, the VIP tent, the
merch, coat check, security, info and photo booths, the portable toilets, a camera riser, the speaker stack and the sound tower;
and the stalled city bus (SM_Vehicle_CityBus, an invented operator, no real livery).

Vehicles: local +X is the nose, Y across, the centre of the footprint on the ground; a mesh is authored at the size of its
collider (the fit stretches by a few percent at most). Wheels are 18-sided; the thin check (members over 0.6 m at least 5.5 cm
across) holds for every mesh, and the bus and the trucks have a _LOD1 (mi collapse, about a quarter of the triangles) for the
views past 12 m (build.py -> midtown.lods). The trucks carry generic words or the approved names only (BRIGHTWIRE EVENTS,
BROADCAST UNIT, CATERING, CITY CROSSTOWN): no real operator, network or livery.

Pivots for the booths and tents: centre of the footprint on the ground, the front (the side people use) toward -Y.
The art has no collision: the level data decides.
"""
import math

import numpy as np

from assets import _midtown_dress as D
from assets import _midtown_roof as R
from assets import _midtown_square as SQ
from assets.facade import B, bx, rod, sheet
from mi import geo, steel

X, Y, Z = np.eye(3)
done, quad, tube, lbl, dome = SQ.done, SQ.quad, SQ.tube, D.lbl, D.dome


def wheel(b, c, r=0.50, w=0.30):
    SQ.wheel(b, c, r, w, Y, "rubber", "galv")
    rod(b, np.asarray(c, float) + (0, -w / 2 - 0.02, 0), np.asarray(c, float) + (0, w / 2 + 0.02, 0), r * 0.30, "black", n=10)


def side(b, x0, z0, w, h, yh, name="signFace"):
    """A printed face on each side of a vehicle: -Y reads along +X, +Y along -X. Returns the two frames."""
    return [quad(b, (x0, -yh - 0.001, z0), X, Z, w, h, name), quad(b, (x0 + w, yh + 0.001, z0), -X, Z, w, h, name)]


def lights(b, x, W, z, slot="led", w=0.22, h=0.12):
    for s in (-1, 1):
        bx(b, (x - 0.01, s * (W / 2 - 0.32) - w / 2, z), (x + 0.03, s * (W / 2 - 0.32) + w / 2, z + h), slot, ch=0.006, pin=False)


def tail(b, x, W, z):
    for s in (-1, 1):
        bx(b, (x - 0.03, s * (W / 2 - 0.20) - 0.09, z), (x + 0.01, s * (W / 2 - 0.20) + 0.09, z + 0.34), "tail", ch=0.006, pin=False)
    bx(b, (x - 0.05, -W / 2 + 0.10, 0.62), (x, W / 2 - 0.10, 0.78), "grey", ch=0.01, pin=False)                  # bumper bar


def chassis(b, x0, x1, W, axles, z=0.48):
    """Two rails, cross members, a fuel tank and the wheels (axles: [(x, dual)])."""
    for s in (-1, 1):
        bx(b, (x0, s * 0.45 - 0.07, z), (x1, s * 0.45 + 0.07, z + 0.22), "standBlack", ch=0.006, pin=False, axis="x")
    for x in np.linspace(x0 + 0.4, x1 - 0.4, 4):
        bx(b, (x - 0.06, -0.45, z + 0.04), (x + 0.06, 0.45, z + 0.20), "standBlack", pin=False, axis="y")
    for ax, dual in axles:
        for s in (-1, 1):
            wheel(b, (ax, s * (W / 2 - 0.20), 0.50))
            if dual:
                wheel(b, (ax, s * (W / 2 - 0.55), 0.50))
        bx(b, (ax - 0.06, -W / 2 + 0.3, 0.42), (ax + 0.06, W / 2 - 0.3, 0.54), "standBlack", pin=False, axis="y")
    ax0 = axles[-1][0]
    for s in (-1, 1):                                                                                      # mud guard over the rear wheels
        bx(b, (ax0 - 0.62, s * (W / 2 - 0.02) - (0.0 if s > 0 else 0.2), 0.96), (ax0 + 0.62, s * (W / 2 - 0.02) + (0.2 if s > 0 else 0.0), 1.02), "standBlack", ch=0.01, pin=False, axis="x")
    bx(b, (x0 + 1.0, -W / 2 + 0.05, 0.50), (x0 + 1.9, -W / 2 + 0.35, 0.80), "standBlack", ch=0.02, pin=False)  # fuel tank


def cab(b, xf, length, W, paint, hcab=2.62):
    """A cab-over cab from xf - length to xf: windscreen, side glass, grille, lamps, bumper, mirrors, a step and a roof deflector."""
    x0 = xf - length
    bx(b, (x0, -W / 2 + 0.03, 0.62), (xf, W / 2 - 0.03, hcab), paint, ch=0.07, axis="x", pin=False)
    bx(b, (xf - 0.05, -W / 2 + 0.26, 1.36), (xf + 0.015, W / 2 - 0.26, 2.40), "glassTint", ch=0.02, pin=False)       # windscreen
    for s in (-1, 1):
        y = s * (W / 2 - 0.03)
        bx(b, (xf - 1.30, y - (0.012 if s < 0 else 0.0), 1.38), (xf - 0.30, y + (0.012 if s > 0 else 0.0), 2.30), "glassTint", ch=0.01, pin=False)
        bx(b, (xf - 1.34, y - (0.01 if s < 0 else 0.0), 0.94), (xf - 0.26, y + (0.01 if s > 0 else 0.0), 1.00), "grey", pin=False)   # door shut line
        bx(b, (xf - 0.58, y - (0.03 if s < 0 else 0.0), 1.10), (xf - 0.38, y + (0.03 if s > 0 else 0.0), 1.20), "black", pin=False)  # handle
        tube(b, (xf - 0.50, s * (W / 2 + 0.02), 2.00), (xf - 0.50, s * (W / 2 + 0.24), 2.00), "black", 0.03)
        bx(b, (xf - 0.56, s * (W / 2 + 0.20) - 0.06, 1.62), (xf - 0.44, s * (W / 2 + 0.28) + 0.06, 2.12), "black", ch=0.01, pin=False)  # mirror
        bx(b, (xf - 0.90, y - (0.20 if s < 0 else 0.0), 0.40), (xf - 0.30, y + (0.20 if s > 0 else 0.0), 0.46), "grey", pin=False)      # step
    bx(b, (xf - 0.02, -W / 2 + 0.20, 0.62), (xf + 0.02, W / 2 - 0.20, 1.20), "black", pin=False, axis="y")                          # grille
    for z in (0.74, 0.90, 1.06):
        bx(b, (xf + 0.02, -W / 2 + 0.28, z), (xf + 0.035, W / 2 - 0.28, z + 0.06), "grille", pin=False, axis="y")
    lights(b, xf, W, 0.78)
    bx(b, (xf - 0.06, -W / 2 + 0.02, 0.50), (xf + 0.14, W / 2 - 0.02, 0.66), "grey", ch=0.02, pin=False)           # bumper
    bx(b, (x0 + 0.1, -W / 2 + 0.15, hcab), (xf - 0.25, W / 2 - 0.15, hcab + 0.12), paint, ch=0.04, pin=False)      # roof deflector


def truck(ctx, M, name, L, W, Hb, cab_len, paint, kind, face, notes, axles=None, cover=None):
    """A box truck, flatbed or generator truck, nose to +X: chassis, cab, then the body. kind: 'box' | 'flat' | 'gen' | 'sat' |
    'cater'. face: (key, w, h, z0) of the printed side panel or None."""
    b = B(abs(hash(name)) % 997 + 1000, step=0.6)
    x0, xf = -L / 2, L / 2
    ax = axles or [(xf - 0.95, False), (x0 + 1.4, True), (x0 + 2.9, True)]
    chassis(b, x0, xf, W, ax)
    cab(b, xf, cab_len, W, paint)
    xb = xf - cab_len - 0.06
    faces = []
    if kind in ("box", "sat", "cater"):
        bx(b, (x0, -W / 2, 0.80), (xb, W / 2, 0.80 + Hb), paint, ch=0.05, axis="x", pin=False)
        for s in (-1, 1):                                                                                  # rib lines (6 cm flat strips)
            for xr in np.arange(x0 + 1.0, xb - 0.5, 1.3):
                bx(b, (xr - 0.03, s * W / 2 - (0.012 if s > 0 else 0.0), 0.90), (xr + 0.03, s * W / 2 + (0.012 if s < 0 else 0.0), 0.80 + Hb - 0.10), "grey", pin=False, axis="z")
        bx(b, (x0 - 0.03, -W / 2 + 0.05, 0.84), (x0, W / 2 - 0.05, 0.80 + Hb - 0.05), "grey", pin=False, axis="y")          # rear door panel
        for z in (1.4, 2.2):                                                                                # rear door locking bars
            tube(b, (x0 - 0.05, -W / 2 + 0.2, z), (x0 - 0.05, W / 2 - 0.2, z), "galv", 0.03)
        tail(b, x0, W, 0.95)
        bx(b, (x0 - 0.18, -W / 2 + 0.10, 0.80 - 0.18), (x0, W / 2 - 0.10, 0.80 - 0.10), "black", ch=0.01, pin=False)       # tail lift in its stowed fold... plate
        if face:
            faces += side(b, x0 + 0.4, face[3], face[1], face[2], W / 2)
    if kind == "sat":
        bx(b, (x0 + 0.7, -0.5, 0.80 + Hb), (x0 + 1.9, 0.5, 0.80 + Hb + 0.16), "grey", ch=0.02, pin=False)
        s_ = geo.sphere(0.85, 24, 10)                                                                       # the dish: a shallow bowl, tilted
        co, _ = geo.arrays(s_)
        co[:, 2] = np.where(co[:, 2] < 0.0, co[:, 2] * 0.0, co[:, 2] * 0.22)
        geo.set_verts(s_, co)
        geo.transform(s_, loc=(x0 + 1.3, 0.0, 0.80 + Hb + 0.50), rot=(0, 30, 0))
        b.absorb(s_, "truckWhite")
        tube(b, (x0 + 1.3, 0.0, 0.80 + Hb + 0.16), (x0 + 1.3, 0.0, 0.80 + Hb + 0.50), "grey", 0.04)
        for s in (-1, 1):                                                                                   # stabiliser jacks
            bx(b, (xb - 1.6, s * (W / 2 + 0.02) - 0.10, 0.60), (xb - 1.35, s * (W / 2 + 0.02) + 0.10, 1.20), "black", pin=False)
            bx(b, (xb - 1.7, s * (W / 2 + 0.02) - 0.20, 0.0), (xb - 1.25, s * (W / 2 + 0.02) + 0.20, 0.06), "black", pin=False)
    if kind == "cater":
        yh = W / 2
        bx(b, (-2.8, yh, 1.35), (-0.4, yh + 0.02, 2.30), "interior", pin=False)                           # the serving hatch, open
        bx(b, (-2.9, yh + 0.02, 1.25), (-0.3, yh + 0.40, 1.30), "stainless", ch=0.005, pin=False)       # counter
        b.poly_plate([(-2.95, yh, 2.34), (-0.25, yh, 2.34), (-0.25, yh + 0.55, 2.10), (-2.95, yh + 0.55, 2.10)][::-1], 0.04, "cream", kind=b.OTHER)   # awning, up
        for xx in (-2.9, -0.3):
            tube(b, (xx, yh + 0.52, 2.10), (xx, yh + 0.38, 1.30), "galv", 0.03)
    if kind == "flat":
        bx(b, (x0, -W / 2, 0.80), (xb, W / 2, 0.92), "boards", ch=0.01, axis="x", pin=False)
        for s in (-1, 1):
            bx(b, (x0, s * W / 2 - (0.08 if s > 0 else 0.0), 0.70), (xb, s * W / 2 + (0.08 if s < 0 else 0.0), 0.80), "standBlack", pin=False, axis="x")
        bx(b, (xb - 0.12, -W / 2, 0.92), (xb, W / 2, 2.40), "standBlack", ch=0.01, pin=False, axis="y")          # headboard
        tail(b, x0, W, 0.60)
    if kind == "gen":
        bx(b, (x0, -W / 2, 0.80), (xb, W / 2, 0.92), "boards", ch=0.01, axis="x", pin=False)
        tail(b, x0, W, 0.60)
    return b, faces, (x0, xf, xb)


def finish(ctx, M, b, name, faces, W, L, H, notes, cover=None):
    return done(ctx, b, name, M, ground=True, faces=faces, cover_height=cover, expect_size=(None, None, None), notes=notes)


# ================================================================================================= trucks

def m_prod(ctx, M):
    L, W = 8.0, 2.5
    b, faces, (x0, xf, xb) = truck(ctx, M, "prod", L, W, 2.50, 2.85, "truckWhite", "box", ("Panel_Brightwire", 5.0, 1.0, 1.55), "")
    faces = faces[:2]
    bx(b, (x0 - 0.20, -W / 2 + 0.2, 0.86), (x0 - 0.04, W / 2 - 0.2, 2.45), "black", ch=0.01, pin=False)           # tail lift, stowed folded up
    for s in (-1, 1):
        bx(b, (x0 - 0.20, s * (W / 2 - 0.20) - 0.04, 0.86), (x0 - 0.04, s * (W / 2 - 0.20) + 0.04, 2.45), "galv", pin=False, axis="z")
    return finish(ctx, M, b, "SM_Sq_Truck_Production", faces, W, L, 3.3,
                  "The production company's box truck, 8.0 x 2.5 x 3.3 (the data's box_truck: cargo 5.15 + cab 2.85), nose to +X: "
                  "white 4-axle-less cab-over, ribbed box with a tail lift stowed behind (x13's rack stands at its tail), Panel_Brightwire "
                  "on both sides (BRIGHTWIRE EVENTS, STAGING · LIGHTING · SCREENS; the VLTR spray over it is a decal). LOD1 for the views "
                  "past 12 m. Pivot: centre, ground.", 3.3)


def m_broadcast(ctx, M):
    """A broadcast van 2.2 x 6.8 x 3.4: a long panel van (the silhouette extruded across), roof mast and two domes, a light bar,
    side glass, Panel_Broadcast."""
    L, W = 6.8, 2.2
    b = B(1101, step=0.6)
    x0, xf = -L / 2, L / 2
    prof = [(x0, 0.62), (x0, 2.78), (xf - 1.7, 2.82), (xf - 0.75, 1.72), (xf - 0.15, 1.30), (xf, 1.05), (xf, 0.62)]
    b.prism(prof[::-1], (0, -W / 2, 0), X, Z, (0, W, 0), "truckWhite", pstep=0.5)
    chassis(b, x0 + 0.1, xf - 0.1, W, [(xf - 1.2, False), (x0 + 1.3, False)], z=0.42)
    for s in (-1, 1):
        y = s * W / 2
        bx(b, (xf - 2.4, y - (0.014 if s < 0 else 0.0), 1.55), (xf - 1.15, y + (0.014 if s > 0 else 0.0), 2.40), "glassTint", ch=0.01, pin=False)   # cab side glass
        bx(b, (xf - 1.62, y - (0.012 if s < 0 else 0.0), 0.78), (xf - 1.55, y + (0.012 if s > 0 else 0.0), 2.70), "grey", pin=False, axis="z")    # sliding door seam
        tube(b, (xf - 1.30, s * (W / 2 + 0.02), 1.90), (xf - 1.30, s * (W / 2 + 0.22), 1.90), "black", 0.03)
        bx(b, (xf - 1.36, s * (W / 2 + 0.18) - 0.06, 1.55), (xf - 1.24, s * (W / 2 + 0.28) + 0.06, 2.05), "black", ch=0.01, pin=False)
    b.poly_plate([(xf - 0.75, -W / 2 + 0.20, 1.74), (xf - 0.75, W / 2 - 0.20, 1.74), (xf - 1.65, W / 2 - 0.20, 2.76), (xf - 1.65, -W / 2 + 0.20, 2.76)],
                 0.02, "glassTint", kind=b.OTHER)                                                          # windscreen on the rake
    lights(b, xf, W, 0.78)
    bx(b, (xf - 0.04, -W / 2 + 0.10, 0.52), (xf + 0.12, W / 2 - 0.10, 0.66), "grey", ch=0.02, pin=False)
    tail(b, x0, W, 0.95)
    for x in (-1.0, 0.3, 1.6):                                                                              # roof gear
        dome(b, (x, -0.55, 2.80), 0.36, "grey", squash=0.5)
    rod(b, (-2.0, 0.55, 2.80), (-2.0, 0.55, 3.40), 0.045, "galv", n=10)
    rod(b, (-2.0, 0.55, 2.80), (-2.0, 0.55, 2.90), 0.18, "black", n=14)
    bx(b, (xf - 1.9, -0.6, 2.82), (xf - 1.7, 0.6, 2.90), "led", ch=0.01, pin=False)                       # light bar at the windscreen header
    bx(b, (-2.8, -0.5, 2.80), (-2.0, 0.0, 2.92), "grey", ch=0.01, pin=False)
    faces = side(b, x0 + 0.35, 1.35, 3.0, 0.70, W / 2)
    return finish(ctx, M, b, "SM_Sq_Van_Broadcast_6p8", faces, W, L, 3.4,
                  "Broadcast van 2.2 x 6.8 x 3.4 (the data's broadcast_van, two; the second stretches to 6.5): a long panel van "
                  "silhouette, side glass, roof domes and a 6 cm mast to 3.4, a light bar, Panel_Broadcast (BROADCAST UNIT, "
                  "SATELLITE UPLINK: generic, no network name) on both sides. Nose to +X. LOD1. Pivot: centre, ground.", 3.4)


def m_satellite(ctx, M):
    L, W = 7.0, 2.2
    b, faces, (x0, xf, xb) = truck(ctx, M, "sat", L, W, 2.40, 2.2, "truckWhite", "sat", ("Panel_Broadcast", 3.0, 0.70, 1.55), "")
    return finish(ctx, M, b, "SM_Sq_Truck_Satellite", faces, W, L, 3.4,
                  "Satellite uplink truck 2.2 x 7.0 x 3.4 (the data's satellite_truck): white cab and box, a 1.7 m dish stowed at the "
                  "rear of the roof on a pedestal, stabiliser jacks, Panel_Broadcast on both sides. Nose to +X. LOD1. Pivot: centre, ground.", 3.4)


def m_catering(ctx, M):
    L, W = 6.8, 2.2
    b, faces, (x0, xf, xb) = truck(ctx, M, "cater", L, W, 2.20, 2.2, "cream", "cater", ("Panel_Catering", 4.0, 0.9, 1.65), "")
    return finish(ctx, M, b, "SM_Sq_Truck_Catering", faces, W, L, 3.0,
                  "Catering truck 2.2 x 6.8 x 3.0 (the data's catering_truck): a cream box with a serving hatch open on +Y, a stainless "
                  "counter, a raised awning, Panel_Catering (CATERING, CREW AND GUESTS) on both sides. Nose to +X. LOD1. Pivot: centre, ground.", 3.0)


def m_generator_truck(ctx, M):
    L, W = 4.2, 2.2
    b, faces, (x0, xf, xb) = truck(ctx, M, "gentruck", L, W, 0.0, 1.5, "truckWhite", "gen", None, "", axles=[(1.15, False), (-0.9, True)])
    x0, xb = -L / 2, L / 2 - 1.5 - 0.06
    bx(b, (x0 + 0.1, -W / 2 + 0.1, 0.92), (xb - 0.1, W / 2 - 0.1, 2.50), "genWhite", ch=0.03, axis="x", pin=False)         # enclosure
    for s in (-1, 1):
        for i in range(3):
            bx(b, (x0 + 0.25 + i * 0.85, s * (W / 2 - 0.1) - (0.012 if s < 0 else 0.0), 1.05), (x0 + 0.95 + i * 0.85, s * (W / 2 - 0.1) + (0.012 if s > 0 else 0.0), 1.55), "grille", pin=False)
            bx(b, (x0 + 0.25 + i * 0.85, s * (W / 2 - 0.1) - (0.012 if s < 0 else 0.0), 1.65), (x0 + 0.95 + i * 0.85, s * (W / 2 - 0.1) + (0.012 if s > 0 else 0.0), 2.4), "genWhite", pin=False)
    bx(b, (x0 + 0.1, -W / 2 + 0.2, 2.50), (xb - 0.1, W / 2 - 0.2, 2.58), "grey", ch=0.01, pin=False)
    for y in (-0.5, 0.5):
        rod(b, (x0 + 0.6, y, 2.58), (x0 + 0.6, y, 3.20), 0.07, "black", n=12)
        rod(b, (x0 + 0.6, y, 3.20), (x0 + 0.6, y, 3.24), 0.10, "black", n=12)
    bx(b, (x0 - 0.02, -0.5, 1.2), (x0 + 0.02, 0.5, 1.9), "interior", pin=False)
    for i, y in enumerate((-0.25, 0.0, 0.25)):
        tube(b, (x0 - 0.02, y, 0.95), (x0 - 0.32, y, 0.30), "rubber", 0.03)                                  # cable tails
    return finish(ctx, M, b, "SM_Sq_Truck_Generator", [], W, L, 3.2,
                  "Generator truck 2.2 x 4.2 x 3.2 (the data's generator_truck): a short cab-over with a sound-proofed generator "
                  "enclosure on the bed (louvres, two exhaust stacks to 3.2), cable tails at the rear. Nose to +X. Pivot: centre, ground.", 3.2)


def m_cable_truck(ctx, M):
    L, W = 7.0, 2.6
    b, faces, (x0, xf, xb) = truck(ctx, M, "cable", L, W, 0.0, 2.2, "truckGrey", "flat", None, "")
    for i, x in enumerate(np.linspace(x0 + 1.0, xb - 1.3, 3)):                                              # three cable reels on edge
        for z in (1.92,):
            for s in (-1, 1):
                rod(b, (x, s * 0.45, z), (x, s * 0.49, z), 0.85, "drum", n=26)
            rod(b, (x, -0.45, z), (x, 0.45, z), 0.70, "rubber", n=26)
            rod(b, (x, -0.62, z), (x, 0.62, z), 0.08, "galv", n=10)
            bx(b, (x - 0.10, -0.62, 0.92), (x + 0.10, 0.62, 1.00), "standBlack", pin=False)                  # cradle under each reel
    for xx in np.linspace(x0 + 0.6, xb - 0.6, 4):
        for s in (-1, 1):
            tube(b, (xx, s * (W / 2 - 0.05), 0.92), (xx, s * (W / 2 - 0.05), 1.30), "galv", 0.03)             # stakes
    return finish(ctx, M, b, "SM_Sq_Truck_Cable", [], W, L, 3.3,
                  "Cable truck 2.6 x 7.0 x 3.3 (the data's cable_truck): a grey flatbed with three large cable reels on edge (timber "
                  "flanges, black cable wound), stakes and a headboard. Nose to +X. LOD1. Pivot: centre, ground.", 3.3)


def m_staging_truck(ctx, M):
    L, W = 8.0, 2.4
    b, faces, (x0, xf, xb) = truck(ctx, M, "staging", L, W, 0.0, 2.2, "truckWhite", "flat", None, "")
    for k in range(3):                                                                                       # deck panels stacked, strapped
        for j in range(2):
            x = x0 + 0.5 + j * 1.9
            bx(b, (x, -1.0, 0.92 + k * 0.22), (x + 1.8, 1.0, 1.12 + k * 0.22), "plate", ch=0.01, pin=False, axis="x")
            bx(b, (x, -1.0, 0.92 + k * 0.22), (x + 1.8, 1.0, 0.95 + k * 0.22), "black", pin=False, axis="x")
    for x in (x0 + 1.4, x0 + 3.2):
        for s in (-1, 1):
            bx(b, (x - 0.03, s * 1.05 - 0.03, 0.80), (x + 0.03, s * 1.05 + 0.03, 1.62), "rubber", pin=False, axis="z")
        bx(b, (x - 0.03, -1.05, 1.58), (x + 0.03, 1.05, 1.64), "rubber", pin=False, axis="y")
    for i in range(3):                                                                                       # truss lengths lying on top (box section)
        y = -0.8 + i * 0.8
        for yo in (-0.18, 0.18):
            tube(b, (x0 + 0.4, y + yo * 0.5, 1.72), (xb - 0.4, y + yo * 0.5, 1.72), "galv", 0.03)
        for xx in np.arange(x0 + 0.4, xb - 0.5, 0.55):
            tube(b, (xx, y - 0.09, 1.72), (xx + 0.28, y + 0.09, 1.72), "galv", 0.03)
    return finish(ctx, M, b, "SM_Sq_Truck_Staging", [], W, L, 3.3,
                  "Staging truck 2.4 x 8.0 x 3.3 (the data's staging_truck): a white flatbed loaded with deck panels in three layers, "
                  "strapped, and aluminium truss lengths lying on top. Nose to +X. LOD1. Pivot: centre, ground.", 3.3)


# ================================================================================================= trailers, light and truss towers

def m_trailer(ctx, M, L, W, name):
    """A site office trailer: a steel box on a frame, a door with a landing and steps and rails, windows with sills, a roof
    air conditioner, skirting, jacks and a tongue toward +X (the hitch)."""
    b = B(1111 + int(L * 10), step=0.6)
    tongue = 0.8
    xa, xb = -L / 2, L / 2 - tongue
    bx(b, (xa, -W / 2, 0.55), (xb, W / 2, 2.85), "cream", ch=0.04, axis="x", pin=False)
    bx(b, (xa, -W / 2 + 0.03, 0.30), (xb, W / 2 - 0.03, 0.55), "standBlack", ch=0.01, pin=False, axis="x")
    for s in (-1, 1):
        bx(b, (xa, s * 0.40 - 0.06, 0.40), (L / 2 - 0.1, s * 0.40 + 0.06, 0.50), "standBlack", pin=False, axis="x")    # frame rails to the tongue
    tube(b, (xb, 0, 0.45), (L / 2 - 0.05, 0, 0.45), "black", 0.04)
    bx(b, (L / 2 - 0.15, -0.08, 0.40), (L / 2, 0.08, 0.52), "black", ch=0.01, pin=False)
    tube(b, (L / 2 - 0.50, 0.0, 0.45), (L / 2 - 0.50, 0.0, 0.0), "galv", 0.04)                              # jack
    for x in (xa + 0.6, xb - 0.6):
        for s in (-1, 1):
            tube(b, (x, s * (W / 2 - 0.1), 0.30), (x, s * (W / 2 - 0.1), 0.0), "galv", 0.03)
    wx = (xa + 1.4, xa + 3.3, xb - 1.4)
    for x in wx[:L > 5.5 and 3 or 2]:                                                                        # windows on both sides
        for s in (-1, 1):
            y = s * W / 2
            bx(b, (x - 0.5, y - (0.012 if s < 0 else 0.0), 1.45), (x + 0.5, y + (0.012 if s > 0 else 0.0), 2.30), "glassTint", ch=0.008, pin=False)
            bx(b, (x - 0.56, y - (0.03 if s < 0 else 0.0), 1.38), (x + 0.56, y + (0.03 if s > 0 else 0.0), 1.45), "white", pin=False)
    for s in (-1,):                                                                                          # door and landing on -Y
        xd = xb - 0.7
        bx(b, (xd - 0.45, -W / 2 - 0.02, 0.60), (xd + 0.45, -W / 2 + 0.01, 2.40), "standGrey", ch=0.01, pin=False, axis="z")
        bx(b, (xd - 0.9, -W / 2 - 1.0, 0.50), (xd + 0.9, -W / 2, 0.58), "plate", ch=0.01, pin=False)        # landing
        bx(b, (xd - 0.7, -W / 2 - 1.5, 0.26), (xd + 0.7, -W / 2 - 1.0, 0.32), "plate", ch=0.01, pin=False)  # step
        for sx in (-1, 1):
            tube(b, (xd + sx * 0.88, -W / 2 - 0.98, 0.58), (xd + sx * 0.88, -W / 2 - 0.98, 1.50), "galv", 0.03)
            tube(b, (xd + sx * 0.88, -W / 2 - 0.98, 1.50), (xd + sx * 0.88, -W / 2 - 0.05, 1.50), "galv", 0.03)
        tube(b, (xd - 0.88, -W / 2 - 0.98, 1.50), (xd + 0.88, -W / 2 - 0.98, 1.50), "galv", 0.03)
    bx(b, (xa + 0.8, -0.55, 2.85), (xa + 1.8, 0.55, 3.00), "hvac", ch=0.02, pin=False)                        # roof A/C
    rod(b, (xa + 1.3, 0.0, 3.0), (xa + 1.3, 0.0, 3.04), 0.40, "grille", n=16)
    tail(b, xa, W, 0.70)
    return done(ctx, b, name, M, ground=True, cover_height=3.0, expect_size=(None, None, None),
                notes=("Site office trailer %.1f x %.1f x 3.0 (the data's production_trailer, two): cream steel box on a frame, windows "
                       "with sills, a door with a landing, a step and rails on -Y, a roof A/C, jacks, a hitch tongue toward +X. Pivot: "
                       "centre, ground.") % (L, W))


def m_screen_trailer(ctx, M):
    """The mobile screen, parked and dark: 4.0 x 0.6 x 4.0 (the data's screen_trailer): an equipment cabinet on a skid with
    outriggers, two masts and the folded LED wall above it (off: opaque black glass faces, no emissive) with a truss back and
    a Panel_Brightwire face on the cabinet. Pivot: centre, ground; the screen faces -Y."""
    b = B(1121, step=0.6)
    bx(b, (-2.0, -0.30, 0.0), (2.0, 0.30, 0.30), "standBlack", ch=0.01, pin=False, axis="x")
    for s in (-1, 1):
        bx(b, (s * 1.75 - 0.10, -0.30, 0.0), (s * 1.75 + 0.10, 0.30, 0.05), "galv", pin=False)
    bx(b, (-1.9, -0.28, 0.30), (1.9, 0.28, 1.50), "truckGrey", ch=0.02, axis="x", pin=False)
    for i in range(4):
        bx(b, (-1.8 + i * 0.95, -0.292, 0.38), (-0.95 + i * 0.95, -0.28, 1.42), "grey", ch=0.008, pin=False, axis="z")
    for s in (-1, 1):
        bx(b, (s * 1.85 - 0.10, -0.12, 1.50), (s * 1.85 + 0.10, 0.12, 4.0), "standBlack", ch=0.008, axis="z", pin=False)
    bx(b, (-1.85, -0.20, 1.80), (1.85, 0.20, 3.95), "standBlack", ch=0.012, axis="x", pin=False)
    bx(b, (-1.78, -0.205, 1.88), (1.78, -0.20, 3.87), "plasticBlack", pin=False)                            # the wall, off
    for i in range(1, 6):
        bx(b, (-1.78 + i * 0.593 - 0.03, -0.207, 1.88), (-1.78 + i * 0.593 + 0.03, -0.20, 3.87), "standBlack", pin=False, axis="z")
    for z in (2.55, 3.20):
        bx(b, (-1.78, -0.207, z - 0.03), (1.78, -0.20, z + 0.03), "standBlack", pin=False, axis="x")
    for i in range(5):                                                                                      # truss back
        tube(b, (-1.7 + i * 0.85, 0.22, 1.9), (-1.28 + i * 0.85, 0.22, 3.9), "black", 0.03)
    faces = [quad(b, (-1.7, -0.2925, 0.62), X, Z, 3.4, 0.68, "signFace")]
    return done(ctx, b, "SM_Sq_ScreenTrailer", M, ground=True, faces=faces, cover_height=4.0, expect_size=(None, None, None),
                notes="Mobile screen trailer, parked and dark, 4.0 x 0.6 x 4.0 (the data's screen_trailer): an equipment cabinet on a skid "
                      "with outriggers (Panel_Brightwire on its front), two masts and the folded LED wall above it, black and off (no "
                      "emissive: not one of the 7 screens), truss back. Pivot: centre, ground; the screen faces -Y.")


def m_light_tower(ctx, M):
    """A mobile light tower 3.0 x 1.4 x 2.6 (the data's light_tower, seven): a trailer with an enclosure and fuel tank, stabiliser
    legs, and the mast raised to 5.6 m carrying a four-lamp head (LED lenses, small). The collider covers the trailer and the
    lowered mast's height; the raised mast is over the box (shots pass). Pivot: centre, ground; the tongue toward +X."""
    b = B(1131, step=0.6)
    bx(b, (-1.4, -0.70, 0.40), (0.9, 0.70, 0.52), "standBlack", ch=0.01, pin=False, axis="x")
    tube(b, (0.9, 0, 0.46), (1.5, 0, 0.46), "black", 0.04)
    bx(b, (1.40, -0.07, 0.40), (1.5, 0.07, 0.52), "black", pin=False)
    for s in (-1, 1):
        wheel(b, (-0.5, s * 0.72, 0.33), 0.33, 0.20)
        for x in (-1.3, 0.8):
            bx(b, (x - 0.06, s * 0.75 - 0.06, 0.0), (x + 0.06, s * 0.75 + 0.06, 0.50), "black", pin=False, axis="z")
            bx(b, (x - 0.12, s * 0.75 - 0.12, 0.0), (x + 0.12, s * 0.75 + 0.12, 0.04), "black", pin=False)
    bx(b, (-1.3, -0.62, 0.52), (0.1, 0.62, 1.55), "orange", ch=0.03, axis="x", pin=False)
    for i in range(3):
        bx(b, (-1.2 + i * 0.45, -0.632, 0.70), (-0.82 + i * 0.45, -0.62, 1.30), "grille", pin=False)
    bx(b, (0.15, -0.60, 0.52), (0.75, 0.60, 0.95), "black", ch=0.02, pin=False)                              # fuel tank
    rod(b, (-0.60, 0.0, 1.55), (-0.60, 0.0, 3.9), 0.09, "galv", n=12)
    rod(b, (-0.60, 0.0, 3.9), (-0.60, 0.0, 5.6), 0.065, "galv", n=10)
    bx(b, (-0.90, -0.60, 5.60), (-0.30, 0.60, 5.70), "black", ch=0.01, pin=False)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx(b, (-0.60 + sx * 0.25 - 0.14, sy * 0.40 - 0.18, 5.70), (-0.60 + sx * 0.25 + 0.14, sy * 0.40 + 0.18, 5.92), "black", ch=0.01, pin=False)
            bx(b, (-0.60 + sx * 0.25 - 0.12, sy * 0.40 - 0.16, 5.66), (-0.60 + sx * 0.25 + 0.12, sy * 0.40 + 0.16, 5.70), "led", pin=False)
    for s in (-1, 1):
        tube(b, (-0.60, 0.0, 3.3), (-0.60 + s * 0.45, 0.0, 1.55), "black", 0.03)                           # mast stays
    return done(ctx, b, "SM_Sq_LightTower", M, ground=True, cover_height=2.6, expect_size=(None, None, None),
                notes="Mobile light tower, trailer 3.0 x 1.4 (the data's light_tower, seven; the box is the trailer at the lowered "
                      "mast's height 2.6): orange generator enclosure with louvres and a fuel tank, four stabiliser legs, the 6.5 cm mast "
                      "raised to 5.6 with four LED lenses (MI_Lamp_LED, small; the light is lane L's). Pivot: centre, ground; the "
                      "tongue toward +X.")


def m_truss_tower(ctx, M):
    """A box-truss tower 0.6 x 0.6 x 4.2 (the data's truss_tower, six): four 6 cm chords, ladder and diagonal bracing every
    0.6 m, a base plate and a top with a lamp bar of four moving heads. Pivot: centre, on the plaza."""
    b = B(1141, step=0.7)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(b, (sx * 0.27, sy * 0.27, 0.04), (sx * 0.27, sy * 0.27, 4.10), "galv", 0.03)
    for i, z in enumerate(np.arange(0.04, 4.11, 0.6)):
        for (p, q) in (((-0.27, -0.27), (0.27, -0.27)), ((0.27, -0.27), (0.27, 0.27)), ((0.27, 0.27), (-0.27, 0.27)), ((-0.27, 0.27), (-0.27, -0.27))):
            tube(b, (p[0], p[1], z), (q[0], q[1], z), "galv", 0.03)
        if z < 4.0:
            for (p, q) in (((-0.27, -0.27), (0.27, -0.27)), ((0.27, -0.27), (0.27, 0.27)), ((0.27, 0.27), (-0.27, 0.27)), ((-0.27, 0.27), (-0.27, -0.27))):
                s = 1 if (i % 2 == 0) else -1
                a, c = (z, z + 0.6) if s > 0 else (z + 0.6, z)
                tube(b, (p[0], p[1], a), (q[0], q[1], c), "galv", 0.03)
    bx(b, (-0.38, -0.38, 0.0), (0.38, 0.38, 0.04), "black", ch=0.004, pin=False)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx(b, (sx * 0.32 - 0.03, sy * 0.32 - 0.03, 0.04), (sx * 0.32 + 0.03, sy * 0.32 + 0.03, 0.30), "black", pin=False, axis="z")
    bx(b, (-0.34, -0.34, 4.10), (0.34, 0.34, 4.16), "black", ch=0.004, pin=False)
    bx(b, (-0.60, -0.08, 4.16), (0.60, 0.08, 4.28), "black", ch=0.01, pin=False)                              # lamp bar
    for x in (-0.45, -0.15, 0.15, 0.45):
        bx(b, (x - 0.08, -0.10, 4.28), (x + 0.08, 0.10, 4.42), "black", ch=0.01, pin=False)
        bx(b, (x - 0.06, -0.08, 4.42), (x + 0.06, 0.08, 4.44), "led", pin=False)
    return done(ctx, b, "SM_Sq_TrussTower", M, ground=True, cover_height=4.2, expect_size=(None, None, None),
                notes="Box-truss tower 0.6 x 0.6 x 4.2 (the data's truss_tower, six): four 6 cm chords, rungs and diagonals every "
                      "0.6 m (all 6 cm), a base plate, a lamp bar with four heads on top (the bar overhangs the box). Pivot: centre, "
                      "ground.")


def m_press_wall(ctx, M):
    """A step-and-repeat press wall 3.4 x 0.3 x 2.4 (the data's press_wall, three; stretched along X to 2.4 or 2.8): a printed
    banner on two truss posts and a header bar with A-frame feet, black fabric back. The face is Press_Wall (WORLD PREMIERE ·
    MIDNIGHT repeated, a small oxblood VLTR). Pivot: centre, ground; the face toward -Y."""
    b = B(1151, step=0.6)
    W = 3.4
    for s in (-1, 1):
        x = s * (W / 2 - 0.06)
        tube(b, (x, 0.0, 0.05), (x, 0.0, 2.40), "black", 0.03)
        tube(b, (x + s * 0.0, -0.12, 0.05), (x, 0.0, 0.05), "black", 0.03)
        bx(b, (x - 0.30, -0.15, 0.0), (x + 0.30, 0.15, 0.05), "black", ch=0.006, pin=False)
    bx(b, (-W / 2 + 0.02, -0.04, 0.12), (W / 2 - 0.02, 0.02, 2.30), "scrim", pin=False, axis="x")
    bx(b, (-W / 2, -0.06, 2.30), (W / 2, 0.04, 2.40), "standBlack", ch=0.006, pin=False, axis="x")
    bx(b, (-W / 2, -0.06, 0.06), (W / 2, 0.04, 0.12), "standBlack", ch=0.006, pin=False, axis="x")
    faces = [quad(b, (-W / 2 + 0.02, -0.0406, 0.12), X, Z, W - 0.04, 2.18, "signFace")]
    return done(ctx, b, "SM_Sq_PressWall_3p4", M, ground=True, faces=faces, cover_height=2.4, expect_size=(None, None, None),
                notes="Press wall 3.4 x 0.3 x 2.4 (the data's press_wall, three): a printed step-and-repeat banner (Press_Wall: WORLD "
                      "PREMIERE, MIDNIGHT, a small oxblood VLTR) on two posts with a header and foot bar, A-frame feet. Pivot: centre, "
                      "ground; the face toward -Y.")


# ================================================================================================= tents and booths

def m_vip_tent(ctx, M):
    """The VIP tent 3.0 x 3.0 x 2.8 (the data's vip_tent): a pop-up frame tent, a pitched white canopy with a black valance,
    black side drapes on three sides, the front open and tied back, a carpet and a stanchion sign (Label_VIP). Pivot: centre, ground."""
    b = B(1161, step=0.6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(b, (sx * 1.40, sy * 1.40, 0.0), (sx * 1.40, sy * 1.40, 2.10), "galv", 0.03)
    b.poly_plate([(-1.5, -1.5, 2.10), (1.5, -1.5, 2.10), (1.5, 0.0, 2.80), (-1.5, 0.0, 2.80)], 0.03, "tentWhite", kind=b.OTHER)
    b.poly_plate([(-1.5, 0.0, 2.80), (1.5, 0.0, 2.80), (1.5, 1.5, 2.10), (-1.5, 1.5, 2.10)], 0.03, "tentWhite", kind=b.OTHER)
    for (p, q) in (((-1.5, -1.5), (1.5, -1.5)), ((1.5, -1.5), (1.5, 1.5)), ((1.5, 1.5), (-1.5, 1.5)), ((-1.5, 1.5), (-1.5, -1.5))):
        bx(b, (min(p[0], q[0]) - 0.02, min(p[1], q[1]) - 0.02, 1.88), (max(p[0], q[0]) + 0.02, max(p[1], q[1]) + 0.02, 2.12), "tentBlack", pin=False, axis="x" if p[1] == q[1] else "y")
    for (x0, y0, x1, y1) in ((-1.48, 1.40, 1.48, 1.44), (-1.48, -1.40, -1.44, 1.40), (1.44, -1.40, 1.48, 1.40)):
        bx(b, (x0, y0, 0.0), (x1, y1, 1.88), "tentBlack", pin=False, axis="y" if (y1 - y0) > (x1 - x0) else "x")
    bx(b, (-1.40, -1.38, 0.0), (1.40, 1.38, 0.025), "standGrey", pin=False, axis="x")                       # carpet
    bx(b, (-0.30, -1.46, 0.0), (0.30, -1.40, 1.88), "tentBlack", pin=False)                                  # the tied-back flap
    stand = [(-1.9, -1.45, 0.0)]
    tube(b, (-1.90, -1.45, 0.0), (-1.90, -1.45, 1.05), "brass", 0.03)
    bx(b, (-2.10, -1.46, 1.05), (-1.70, -1.42, 1.35), "standBlack", pin=False)
    faces = [quad(b, (-2.10, -1.4605, 1.05), X, Z, 0.40, 0.30, "signFace")]
    for x in (-1.9,):
        rod(b, (x, -1.45, 0.0), (x, -1.45, 0.04), 0.20, "standBlack", n=14)
    return done(ctx, b, "SM_Sq_VipTent_3x3", M, ground=True, faces=faces, cover_height=2.8, expect_size=(None, None, None),
                notes="VIP tent 3.0 x 3.0 x 2.8 (the data's vip_tent): frame tent with a pitched white canopy and black valance, black "
                      "drapes on three sides, the front open, a carpet and a stanchion sign (Label_VIP). Opaque canvas, no alpha. "
                      "Pivot: centre, ground; the front toward -Y.")


def booth(ctx, M, name, key, w, d, h, label, paint, notes, counter=True, glass=True, roof=True):
    b = B(abs(hash(name)) % 997 + 1200, step=0.5)
    x0, x1, y0, y1 = -w / 2, w / 2, -d / 2, d / 2
    bx(b, (x0, y0, 0.0), (x1, y1, 0.10), "standBlack", ch=0.004, pin=False, axis="x")
    bx(b, (x0 + 0.02, y1 - 0.06, 0.10), (x1 - 0.02, y1, h - 0.30), paint, ch=0.008, pin=False, axis="x")       # back wall
    for sx in (-1, 1):
        bx(b, (sx * (w / 2 - 0.03) - 0.03, y0 + 0.04, 0.10), (sx * (w / 2 - 0.03) + 0.03, y1, h - 0.30), paint, ch=0.006, pin=False, axis="y")
    bx(b, (x0, y0 + 0.02, 0.10), (x1, y0 + 0.08, 0.95), paint, ch=0.006, pin=False, axis="x")                 # below the counter
    bx(b, (x0 - 0.03, y0 - 0.06, 0.95), (x1 + 0.03, y0 + 0.30, 1.01), "stainless", ch=0.004, pin=False, axis="x")   # counter
    bx(b, (x0, y0 + 0.02, h - 0.62), (x1, y0 + 0.08, h - 0.30), paint, ch=0.006, pin=False, axis="x")
    if roof:
        bx(b, (x0 - 0.10, y0 - 0.20, h - 0.30), (x1 + 0.10, y1 + 0.06, h - 0.22), paint, ch=0.01, pin=False, axis="x")
    bx(b, (x0 - 0.10, y0 - 0.26, h - 0.22), (x1 + 0.10, y0 - 0.14, h), "standBlack", ch=0.006, pin=False, axis="x")   # header
    wlab = min(w + 0.2, 0.9 if key == "Label_Merch" else 0.6)
    fz = h - 0.21
    faces = [quad(b, (-wlab / 2, y0 - 0.2611, fz), X, Z, wlab, 0.19, "signFace")]
    bx(b, (-wlab / 2 - 0.02, y0 - 0.2606, fz - 0.01), (wlab / 2 + 0.02, y0 - 0.2600, fz + 0.20), "standBlack", pin=False)
    bx(b, (x0 + 0.06, y1 - 0.10, 1.01), (x1 - 0.06, y1 - 0.08, h - 0.40), "interior", pin=False)
    bx(b, (x0 + 0.06, y0 + 0.12, h - 0.36), (x1 - 0.06, y0 + 0.18, h - 0.30), "warm", pin=False, axis="x")
    return b, faces, (x0, x1, y0, y1)


def m_merch(ctx, M):
    b, faces, (x0, x1, y0, y1) = booth(ctx, M, "merch", "Label_Merch", 1.6, 1.2, 2.5, "", "kiosk", "")
    for k in range(3):
        bx(b, (x0 + 0.08, y1 - 0.40, 1.15 + k * 0.30), (x1 - 0.08, y1 - 0.08, 1.18 + k * 0.30), "stainless", pin=False, axis="x")
        for j in range(5):
            xx = x0 + 0.14 + j * 0.28
            bx(b, (xx, y1 - 0.38, 1.18 + k * 0.30), (xx + 0.22, y1 - 0.12, 1.34 + k * 0.30), ["white", "plasticBlack", "umbrella"][(j + k) % 3], pin=False)
    for j in range(5):
        xx = x0 + 0.14 + j * 0.28
        dome(b, (xx + 0.11, y0 + 0.22, 1.01), 0.10, ["white", "plasticBlack", "umbrella", "yellow", "cushion"][j], squash=0.7, seg=10, rings=4)
    return done(ctx, b, "SM_Sq_MerchBooth", M, ground=True, faces=faces, cover_height=2.5, expect_size=(None, None, None),
                notes="Merch booth 1.6 x 1.2 x 2.5 (the data's merch_booth): navy steel stall, a stainless counter with caps on it, racks of "
                      "folded shirts, a lit header (Label_Merch: PREMIERE MERCH, CAPS · SHIRTS · POSTERS). Pivot: centre, ground; the front toward -Y.")


def m_coat(ctx, M):
    b, faces, (x0, x1, y0, y1) = booth(ctx, M, "coat", "Label_CoatCheck", 1.4, 1.0, 2.2, "", "standGrey", "")
    tube(b, (x0 + 0.06, y1 - 0.30, 1.90), (x1 - 0.06, y1 - 0.30, 1.90), "stainless", 0.03)
    for j in range(8):
        xx = x0 + 0.15 + j * 0.15
        bx(b, (xx, y1 - 0.36, 0.90), (xx + 0.10, y1 - 0.24, 1.86), ["plasticBlack", "standGrey", "umbrella", "cushion"][j % 4], ch=0.02, pin=False)
    return done(ctx, b, "SM_Sq_CoatCheck", M, ground=True, faces=faces, cover_height=2.2, expect_size=(None, None, None),
                notes="Coat check 1.4 x 1.0 x 2.2 (the data's coat_check): a grey steel booth with a counter, a rail of coats on hangers, a "
                      "header (Label_CoatCheck). Pivot: centre, ground; the front toward -Y.")


def m_security(ctx, M):
    b, faces, (x0, x1, y0, y1) = booth(ctx, M, "security", "Label_Security", 1.4, 1.4, 2.6, "", "truckGrey", "", roof=True)
    for s in (-1, 1):                                                                                       # side windows and a door on +X
        bx(b, (s * (0.70) - (0.012 if s < 0 else 0.0), -0.45, 1.20), (s * 0.70 + (0.012 if s > 0 else 0.0), 0.45, 2.20), "glassTint", ch=0.006, pin=False)
    bx(b, (-0.45, y0 + 0.03, 1.15), (0.45, y0 + 0.07, 2.20), "glassTint", ch=0.006, pin=False)
    bx(b, (-0.30, y1 - 0.08, 0.12), (0.30, y1, 2.00), "standGrey", ch=0.006, pin=False, axis="z")
    bx(b, (-0.45, -0.20, 2.30), (0.45, 0.20, 2.42), "led", ch=0.01, pin=False)                                # beacon bar (dark)
    return done(ctx, b, "SM_Sq_SecurityBooth", M, ground=True, faces=faces, cover_height=2.6, expect_size=(None, None, None),
                notes="Security booth 1.4 x 1.4 x 2.6 (the data's security_booth): a grey steel guard hut with glazed sides and front, a "
                      "back door, a beacon bar, a header (Label_Security). Pivot: centre, ground; the front toward -Y.")


def m_info(ctx, M):
    b, faces, (x0, x1, y0, y1) = booth(ctx, M, "info", "Label_Info", 2.6, 1.2, 2.4, "", "kiosk", "")
    return done(ctx, b, "SM_Sq_InfoBooth", M, ground=True, faces=faces, cover_height=2.4, expect_size=(None, None, None),
                notes="Information booth 2.6 x 1.2 x 2.4 (the data's info_booth; its 1.2 x 2.6 box): a navy steel desk booth with a long counter, a roof and a "
                      "header (Label_Info). Pivot: centre, ground; the front toward -Y (long side along Y when placed on the box).")


def m_photo(ctx, M):
    b, faces, (x0, x1, y0, y1) = booth(ctx, M, "photo", "Label_PhotoBooth", 1.4, 1.4, 2.3, "", "standBlack", "", roof=True)
    bx(b, (-0.45, y0 + 0.02, 0.10), (0.45, y0 + 0.07, 1.90), "tentBlack", pin=False)                          # curtain
    bx(b, (x0 + 0.1, y1 - 0.14, 1.10), (x0 + 0.5, y1 - 0.06, 1.50), "plasticBlack", ch=0.01, pin=False)       # the camera screen
    bx(b, (0.0, y1 - 0.12, 1.30), (0.30, y1 - 0.06, 1.38), "warm", pin=False)
    return done(ctx, b, "SM_Sq_PhotoBooth", M, ground=True, faces=faces, cover_height=2.3, expect_size=(None, None, None),
                notes="Photo booth 1.4 x 1.4 x 2.3 (the data's photo_booth): a black steel booth with a curtain, a bench and a flash lamp, a "
                      "header (Label_PhotoBooth). Pivot: centre, ground; the front toward -Y.")


def m_toilets(ctx, M):
    """Portable toilets 2.4 x 1.2 x 2.45 (the data's portable_toilets): two blue plastic cabins with doors, vents and roof ribs."""
    b = B(1171, step=0.5)
    for i, cx in enumerate((-0.60, 0.60)):
        bx(b, (cx - 0.58, -0.58, 0.0), (cx + 0.58, 0.58, 0.10), "standBlack", ch=0.006, pin=False, axis="x")
        bx(b, (cx - 0.58, -0.58, 0.10), (cx + 0.58, 0.58, 2.30), "teal", ch=0.03, axis="x", pin=False)
        bx(b, (cx - 0.52, -0.595, 0.18), (cx + 0.52, -0.58, 2.05), "teal", ch=0.008, pin=False, axis="z")
        bx(b, (cx - 0.12, -0.60, 1.05), (cx + 0.12, -0.585, 1.18), "white", pin=False)                           # the latch
        bx(b, (cx + 0.30, -0.604, 1.12), (cx + 0.42, -0.59, 1.36), "stainless", pin=False)
        bx(b, (cx - 0.30, -0.60, 1.55), (cx + 0.30, -0.585, 1.85), "white", pin=False)                          # occupied panel
        bx(b, (cx - 0.64, -0.64, 2.30), (cx + 0.64, 0.64, 2.45), "teal", ch=0.03, pin=False, axis="x")
        for k in range(5):
            bx(b, (cx - 0.50 + k * 0.22, 0.58, 2.10), (cx - 0.40 + k * 0.22, 0.60, 2.24), "grille", pin=False)
        rod(b, (cx + 0.40, 0.40, 2.45), (cx + 0.40, 0.40, 2.62), 0.06, "white", n=10)
        bx(b, (cx - 0.20, -0.66, 0.0), (cx + 0.20, -0.58, 0.14), "standBlack", pin=False)
    return done(ctx, b, "SM_Sq_PortableToilets", M, ground=True, cover_height=2.45, expect_size=(None, None, None),
                notes="Portable toilets 2.4 x 1.2 x 2.45 (the data's portable_toilets): two blue plastic cabins with doors, latches, vent "
                      "ribs and a roof vent stack. Pivot: centre, ground; the doors toward -Y.")


def m_riser(ctx, M):
    """A camera riser 1.6 x 0.8 x 2.6 (the data's camera_riser): a scaffold platform 1.5 x 0.8 at 1.2 on four legs, a ladder, a
    rail, a tripod camera on it with its lens toward -Y."""
    b = B(1181, step=0.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(b, (sx * 0.72, sy * 0.34, 0.0), (sx * 0.72, sy * 0.34, 1.20), "galv", 0.03)
            tube(b, (sx * 0.72, sy * 0.34, 1.20), (sx * 0.72, sy * 0.34, 1.62), "galv", 0.03)
    bx(b, (-0.80, -0.40, 1.16), (0.80, 0.40, 1.24), "plate", ch=0.006, axis="x")
    for z in (0.55,):
        tube(b, (-0.72, -0.34, z), (0.72, -0.34, z), "galv", 0.03)
        tube(b, (-0.72, 0.34, z), (0.72, 0.34, z), "galv", 0.03)
    tube(b, (-0.72, -0.34, 1.62), (0.72, -0.34, 1.62), "galv", 0.03)
    tube(b, (-0.72, 0.34, 1.62), (0.72, 0.34, 1.62), "galv", 0.03)
    tube(b, (-0.72, -0.34, 1.62), (-0.72, 0.34, 1.62), "galv", 0.03)
    tube(b, (0.72, -0.34, 1.62), (0.72, 0.34, 1.62), "galv", 0.03)
    for z in np.arange(0.25, 1.2, 0.25):                                                                    # ladder on the +X end
        tube(b, (0.35, -0.44, z), (0.62, -0.44, z), "galv", 0.03)
    for x in (0.35, 0.62):
        tube(b, (x, -0.44, 0.0), (x, -0.44, 1.22), "galv", 0.03)
    for a in range(3):                                                                                      # tripod
        t = 2 * math.pi * a / 3 + 0.4
        tube(b, (0.0, 0.0, 1.24 + 0.78), (0.42 * math.cos(t), 0.42 * math.sin(t), 1.24), "standBlack", 0.03)
    bx(b, (-0.12, -0.12, 2.02), (0.12, 0.12, 2.08), "black", pin=False)
    bx(b, (-0.14, -0.38, 2.08), (0.14, 0.22, 2.40), "plasticBlack", ch=0.02, pin=False)                     # camera body
    rod(b, (0.0, -0.38, 2.26), (0.0, -0.62, 2.26), 0.09, "black", n=14)
    bx(b, (-0.10, 0.22, 2.20), (0.10, 0.34, 2.42), "plasticBlack", ch=0.01, pin=False)                      # viewfinder
    return done(ctx, b, "SM_Sq_CameraRiser", M, ground=True, cover_height=2.6, expect_size=(None, None, None),
                notes="Camera riser 1.6 x 0.8 x 2.6 (the data's camera_riser): a scaffold platform at 1.2 on four legs with a rail and a "
                      "ladder, a tripod camera on it (lens toward -Y). Pivot: centre, ground.")


def m_speaker(ctx, M):
    """The speaker stack 1.4 x 0.8 x 2.75 (the data's speaker_stack): two subwoofers on a deck, a six-box line array on a stand
    (grilles, handles, rigging bars), cables. Pivot: centre, ground; the grilles toward -Y."""
    b = B(1191, step=0.5)
    bx(b, (-0.70, -0.40, 0.0), (0.70, 0.40, 0.12), "standBlack", ch=0.006, pin=False, axis="x")
    for cx in (-0.35, 0.35):
        bx(b, (cx - 0.34, -0.38, 0.12), (cx + 0.34, 0.38, 0.92), "plasticBlack", ch=0.02, axis="x", pin=False)
        bx(b, (cx - 0.30, -0.395, 0.18), (cx + 0.30, -0.375, 0.86), "grille", pin=False, axis="z")
        rod(b, (cx, -0.395, 0.52), (cx, -0.40, 0.52), 0.24, "standBlack", n=20)
        for z in (0.40, 0.64):
            bx(b, (cx + 0.34, -0.10, z), (cx + 0.36, 0.10, z + 0.08), "black", pin=False)
    for i in range(6):
        z = 0.96 + i * 0.28
        yaw = -0.04 * i
        bx(b, (-0.45, -0.28, z), (0.45, 0.28, z + 0.26), "plasticBlack", ch=0.015, axis="x", pin=False)
        bx(b, (-0.40, -0.295, z + 0.04), (0.40, -0.275, z + 0.22), "grille", pin=False, axis="x")
        for x in (-0.47, 0.47):
            bx(b, (x - 0.01, -0.06, z + 0.08), (x + 0.01, 0.06, z + 0.18), "black", pin=False)
    for x in (-0.38, 0.38):
        bx(b, (x - 0.03, 0.22, 0.12), (x + 0.03, 0.30, 2.66), "galv", pin=False, axis="z")
    bx(b, (-0.46, 0.18, 2.62), (0.46, 0.30, 2.72), "galv", ch=0.006, pin=False, axis="x")
    for y in (-0.15, 0.0, 0.15):
        tube(b, (0.0, 0.30, 0.20), (0.0 + (y * 1.5), 0.55, 0.0), "rubber", 0.03)
    return done(ctx, b, "SM_Sq_SpeakerStack", M, ground=True, cover_height=2.75, expect_size=(None, None, None),
                notes="Speaker stack 1.4 x 0.8 x 2.75 (the data's speaker_stack, the premiere loop's source): two subs on a deck, a "
                      "six-cabinet line array with grilles and rigging bars on a stand, cable tails. Pivot: centre, ground; grilles -Y.")


def m_sound_tower(ctx, M):
    """The sound tower 1.2 x 1.2 x 4.0 (the data's sound_tower): a scaffold tower with a mixing platform at 2.0, guard rails, a
    ladder, a mixing desk with faders and a canopy, two top speakers and a cable loom. Pivot: centre, ground."""
    b = B(1201, step=0.6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(b, (sx * 0.55, sy * 0.55, 0.0), (sx * 0.55, sy * 0.55, 4.0), "galv", 0.03)
    for z in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
        for (p, q) in (((-0.55, -0.55), (0.55, -0.55)), ((0.55, -0.55), (0.55, 0.55)), ((0.55, 0.55), (-0.55, 0.55)), ((-0.55, 0.55), (-0.55, -0.55))):
            if z in (2.5, 4.0) or (z in (0.5, 1.0, 1.5, 2.0)) and (p[0] == q[0] or z in (0.5, 2.0)):
                tube(b, (p[0], p[1], z), (q[0], q[1], z), "galv", 0.03)
    for (p, q) in (((-0.55, -0.55), (0.55, -0.55)), ((0.55, 0.55), (-0.55, 0.55)), ((0.55, -0.55), (0.55, 0.55)), ((-0.55, 0.55), (-0.55, -0.55))):
        tube(b, (p[0], p[1], 0.5), (q[0], q[1], 2.0), "galv", 0.03)
    bx(b, (-0.60, -0.60, 2.0), (0.60, 0.60, 2.06), "plate", ch=0.004, axis="x")
    bx(b, (-0.40, -0.32, 2.06), (0.40, 0.14, 2.12), "standBlack", pin=False)
    bx(b, (-0.45, -0.28, 2.12), (0.45, 0.10, 2.36), "plasticBlack", ch=0.015, pin=False)                    # the desk
    for j in range(6):
        bx(b, (-0.38 + j * 0.15, -0.26, 2.36), (-0.30 + j * 0.15, -0.02, 2.40), "stainless", pin=False)
    for j in range(8):
        bx(b, (-0.38 + j * 0.108, -0.20, 2.38), (-0.35 + j * 0.108, -0.10, 2.395), "indicator", pin=False)
    b.poly_plate([(-0.62, -0.62, 3.30), (0.62, -0.62, 3.30), (0.62, 0.62, 3.40), (-0.62, 0.62, 3.40)], 0.03, "tentBlack", kind=b.OTHER)
    for sx in (-1, 1):
        bx(b, (sx * 0.55 - 0.14, -0.20, 3.45), (sx * 0.55 + 0.14, 0.20, 3.99), "plasticBlack", ch=0.015, pin=False)
        bx(b, (sx * 0.55 - 0.12, -0.215, 3.50), (sx * 0.55 + 0.12, -0.20, 3.94), "grille", pin=False)
    for z in np.arange(0.3, 2.0, 0.3):                                                                       # ladder on +Y
        tube(b, (-0.2, 0.62, z), (0.2, 0.62, z), "galv", 0.03)
    for x in (-0.2, 0.2):
        tube(b, (x, 0.62, 0.0), (x, 0.62, 2.0), "galv", 0.03)
    for i, x in enumerate((-0.1, 0.0, 0.1)):
        tube(b, (x, 0.0, 2.0), (x * 3, 0.9, 0.04), "rubber", 0.03)
    return done(ctx, b, "SM_Sq_SoundTower", M, ground=True, cover_height=4.0, expect_size=(None, None, None),
                notes="Sound tower 1.2 x 1.2 x 4.0 (the data's sound_tower): a scaffold tower with a mix platform at 2.0 (the desk, faders and "
                      "indicators), a ladder, a black canopy and two speakers on top, cables to the ground. Pivot: centre, ground.")


# ================================================================================================= the city bus

def m_bus(ctx, M):
    """The stalled city bus, 12.0 x 2.8 x 3.1 (the data's bus; an invented operator, plain blue and white, no real livery):
    a low-floor 12 m transit bus facing +X: white body with a blue skirt and a blue window band, a lit destination sign
    (Panel_CityCrosstown) over the windscreen, tinted side glass in eleven bays, two doors on the kerb side (+Y), six wheels with
    arch trim, big mirrors, a roof pod and hatches, lamps, a bike-less front, an interior silhouette (seat backs, poles) behind
    the glass. Pivot: centre, ground; the nose toward +X, the doors on +Y."""
    L, W = 12.0, 2.6
    b = B(1301, step=0.6)
    x0, xf = -L / 2, L / 2
    prof = [(x0, 0.45), (x0, 2.75), (x0 + 0.5, 3.00), (xf - 0.9, 3.02), (xf - 0.15, 2.9), (xf, 2.60), (xf, 0.60), (xf - 0.2, 0.40)]
    b.prism(prof[::-1], (0, -W / 2, 0), X, Z, (0, W, 0), "truckWhite", pstep=0.5)
    bx(b, (xf - 0.3, -W / 2, 0.55), (xf + 0.02, W / 2, 0.95), "cityBlue", ch=0.03, pin=False)
    for s in (-1, 1):                                                                                      # blue skirt and window band
        y = s * W / 2
        yy = lambda t: (y - (t if s < 0 else 0.0), y + (t if s > 0 else 0.0))
        a, c = yy(0.03)
        bx(b, (x0, a, 0.40), (xf - 0.2, c, 0.95), "cityBlue", ch=0.01, pin=False, axis="x")
        a, c = yy(0.02)
        bx(b, (x0 + 0.1, a, 2.55), (xf - 1.1, c, 2.78), "cityBlue", ch=0.01, pin=False, axis="x")
        for i in range(11):                                                                                 # glass bays
            xx = x0 + 0.55 + i * 0.93
            if s > 0 and (xx > 3.0 and xx < 4.0 or (xx > -1.4 and xx < -0.3)):
                continue                                                                                   # the two doors on +Y
            a, c = yy(0.025)
            bx(b, (xx, a, 1.12), (xx + 0.82, c, 2.50), "glassTint", ch=0.01, pin=False)
            a, c = yy(0.03)
            bx(b, (xx - 0.05, a, 1.06), (xx + 0.87, c, 1.12), "black", pin=False)
        a, c = yy(0.02)
        bx(b, (xf - 1.45, a, 1.12), (xf - 0.30, c, 2.50), "glassTint", ch=0.01, pin=False)
    for s, xs in ((1, 3.0), (1, -1.4)):                                                                     # doors on the kerb side (+Y): two leaves, glass, a handrail
        y = W / 2
        bx(b, (xs, y - 0.02, 0.55), (xs + 1.1, y + 0.03, 2.62), "black", ch=0.01, pin=False)
        for k in range(2):
            bx(b, (xs + 0.03 + k * 0.52, y + 0.02, 0.75), (xs + 0.55 + k * 0.52 - 0.02, y + 0.05, 2.50), "glassTint", ch=0.01, pin=False)
        tube(b, (xs + 0.02, y + 0.06, 0.60), (xs + 0.02, y + 0.06, 2.30), "stainless", 0.03)
        tube(b, (xs + 1.08, y + 0.06, 0.60), (xs + 1.08, y + 0.06, 2.30), "stainless", 0.03)
        bx(b, (xs - 0.05, y, 0.38), (xs + 1.15, y + 0.55, 0.48), "plate", pin=False)
    b.poly_plate([(xf - 0.12, -W / 2 + 0.12, 1.00), (xf - 0.12, W / 2 - 0.12, 1.00), (xf - 0.02, W / 2 - 0.12, 2.55), (xf - 0.02, -W / 2 + 0.12, 2.55)],
                 0.02, "glassTint", kind=b.OTHER)                                                          # windscreen
    bx(b, (xf - 0.12, -W / 2 + 0.55, 2.62), (xf, W / 2 - 0.55, 2.88), "black", ch=0.01, pin=False)         # destination box
    faces = [quad(b, (xf + 0.001, -1.0, 2.64), Y, Z, 2.0, 0.22, "signFace")]
    faces[0]
    for s in (-1, 1):
        bx(b, (xf - 0.30, s * (W / 2 - 0.22) - 0.10, 0.82), (xf + 0.03, s * (W / 2 - 0.22) + 0.10, 0.96), "led", ch=0.008, pin=False)
        bx(b, (xf - 0.28, s * (W / 2 - 0.22) - 0.10, 0.98), (xf + 0.03, s * (W / 2 - 0.22) + 0.10, 1.04), "black", pin=False)
        tube(b, (xf - 0.90, s * (W / 2 + 0.02), 2.35), (xf - 0.80, s * (W / 2 + 0.42), 2.30), "black", 0.03)
        bx(b, (xf - 0.90, s * (W / 2 + 0.38) - 0.06, 1.60), (xf - 0.74, s * (W / 2 + 0.46) + 0.06, 2.35), "black", ch=0.012, pin=False)   # mirror arm and glass
        bx(b, (x0 - 0.02, s * (W / 2 - 0.30) - 0.12, 0.90), (x0 + 0.02, s * (W / 2 - 0.30) + 0.12, 1.28), "tail", ch=0.006, pin=False)
    bx(b, (x0 - 0.04, -W / 2 + 0.20, 0.48), (x0 + 0.04, W / 2 - 0.20, 0.64), "grey", ch=0.015, pin=False)    # rear bumper
    bx(b, (x0 - 0.01, -0.6, 1.25), (x0, 0.6, 2.35), "glassTint", pin=False, axis="z")                       # rear glass
    # wheels: front axle behind the door, a drive axle at the rear, and arches' trim
    for ax in (xf - 2.5, x0 + 2.3):
        for s in (-1, 1):
            wheel(b, (ax, s * (W / 2 - 0.06), 0.50), 0.52, 0.30)
            bx(b, (ax - 0.64, s * (W / 2 + 0.03) - (0.14 if s < 0 else 0.0), 0.96), (ax + 0.64, s * (W / 2 + 0.03) + (0.14 if s > 0 else 0.0), 1.04), "black", ch=0.01, pin=False, axis="x")
    for s in (-1, 1):                                                                                      # the rear tag axle's single wheel
        wheel(b, (x0 + 0.9, s * (W / 2 - 0.06), 0.46), 0.46, 0.26)
    # roof: a pod with the A/C, hatches
    bx(b, (x0 + 1.0, -0.9, 3.0), (x0 + 3.8, 0.9, 3.32), "truckWhite", ch=0.05, pin=False, axis="x")
    for i in range(2):
        bx(b, (x0 + 4.4 + i * 1.6, -0.5, 3.0), (x0 + 5.6 + i * 1.6, 0.5, 3.07), "grey", ch=0.01, pin=False)
    # interior: a floor, seat backs in two rows, vertical poles, a dark ceiling, a driver cab
    bx(b, (x0 + 0.1, -W / 2 + 0.1, 0.62), (xf - 0.3, W / 2 - 0.1, 0.70), "interior", pin=False, axis="x")
    for i in range(10):
        xx = x0 + 0.7 + i * 0.95
        if (3.0 - 0.5 < xx < 4.1) or (-1.4 - 0.5 < xx < -0.3):
            continue
        for s in (-1, 1):
                bx(b, (xx, s * (W / 2 - 0.30) - 0.40, 0.72), (xx + 0.12, s * (W / 2 - 0.30) + 0.40, 1.45), "plasticBlack", ch=0.03, pin=False)
    for xx in np.linspace(x0 + 1.5, xf - 2.5, 6):
        tube(b, (xx, 0.0, 0.70), (xx, 0.0, 2.55), "stainless", 0.03)
    bx(b, (x0 + 0.1, -W / 2 + 0.1, 2.52), (xf - 1.0, W / 2 - 0.1, 2.58), "interior", pin=False, axis="x")
    bx(b, (xf - 1.45, 0.20, 0.70), (xf - 0.45, 0.95, 1.25), "plasticBlack", ch=0.03, pin=False)           # driver's seat and cab
    faces = faces + [quad(b, (x0 + 1.4, -W / 2 - 0.0305, 0.50), X, Z, 4.0, 0.80, "signFace"),
                     quad(b, (x0 + 5.4, W / 2 + 0.0305, 0.50), -X, Z, 4.0, 0.80, "signFace")]
    return done(ctx, b, "SM_Vehicle_CityBus", M, ground=True, faces=faces, cover_height=3.1, expect_size=(None, None, None),
                notes="The stalled city bus, 12.0 x 2.6 x 3.3 (the data's bus 2.8 x 12 x 3.1; an invented operator, CITY CROSSTOWN, plain "
                      "blue and white, no real livery): white body, blue skirt and window band, tinted glass in eleven bays, two doors on "
                      "+Y, a lit destination sign (face Panel_CityCrosstown) and Bus_Side on each flank, six wheels, mirrors, lamps, a roof "
                      "pod, a lit-dark interior silhouette (seat backs, poles). Nose to +X, the doors on +Y (the kerb side when it faces south). LOD1. Pivot: centre, ground.")


PROPS = [m_prod, m_broadcast, m_satellite, m_catering, m_generator_truck, m_cable_truck, m_staging_truck,
         lambda c, M: m_trailer(c, M, 6.0, 2.1, "SM_Sq_Trailer_Production_6m"), lambda c, M: m_trailer(c, M, 6.4, 2.4, "SM_Sq_Trailer_Production_6p4"),
         m_screen_trailer, m_light_tower, m_truss_tower, m_press_wall, m_vip_tent, m_merch, m_coat, m_security, m_info, m_photo,
         m_toilets, m_riser, m_speaker, m_sound_tower, m_bus]
