"""Midtown placements: the west block's roofs (A, B, C, D, E), the stairs and bridges between them, the gantry and G1, the
roof billboard C1, the scaffold stair tower, and the art-only screens around the square, assembled from the `midtown` kit
in level coordinates (midtown.md 2, 3, 5.3, 9.1, 12.2).

    venv/bin/python art/blender/assets/_midtown_place.py     -> art/out/placements/placements_midtown.json

Pure arithmetic: no mesh is built. Coordinates: the web level's (x, y, z) are Blender (x, -z, y); Unreal cm = (x, -y, z) x 100 of
Blender; yaw = -rotation about Z (degrees). Every roof surface is the top of its mass collider (2.1), so decks sit at the roof
height and parapets on the roof edge with their outer face on it. Positions the design leaves open (WT-A to WT-C, the HVAC
rows, the art-only screens past the bounds) are this lane's choice and listed as such ("chosen": true); lane D's colliders
decide where they differ.

Tiled screens: every SM_Sign_LEDWall_Tile_2m entry carries {screen, tile: [column, row], tiles: [columns, rows]}; in
Unreal one MI per screen, the tile's offset in PerInstanceCustomData (u0 = column / columns, v0 = row / rows, size 1 / columns
by 1 / rows), so the whole screen shows one slide.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

R1, R2, R3 = 14.0, 17.6, 21.2

# building: web rect x0, x1, z0, z1, roof height, brick, deck kind
ROOFS = {
    "A": dict(x=(-50.0, -30.0), z=(-38.0, -12.0), h=R3, brick="Buff", deck="Gravel"),
    "B": dict(x=(-50.0, -30.0), z=(-12.0, 8.0), h=R2, brick="Buff", deck="Gravel"),
    "E": dict(x=(-50.0, -30.0), z=(8.0, 22.0), h=R1, brick="Red", deck="Gravel"),
    "C": dict(x=(-28.0, -8.0), z=(-38.0, -4.0), h=R2, brick="Red", deck="Gravel"),
    "D": dict(x=(-28.0, -8.0), z=(-4.0, 22.0), h=R1, brick="Red", deck="Pavers"),
}
# parapet edges: (building, side, [openings as (from, to) along the edge's web coordinate]). Sides n/s/e/w in web terms
# (north = -z). An edge against a taller neighbour has no parapet (B and E north, D north).
EDGES = [
    ("A", "n", []), ("A", "w", []), ("A", "e", [(-22.0, -20.0)]), ("A", "s", [(-44.0, -42.0)]),
    ("B", "w", []), ("B", "e", [(-10.0, -8.0)]), ("B", "s", [(-48.0, -46.0), (-36.0, -34.0)]),
    ("E", "w", []), ("E", "e", [(16.0, 18.0)]), ("E", "s", []),
    ("C", "n", []), ("C", "w", [(-22.0, -20.0), (-10.0, -8.0)]), ("C", "e", []), ("C", "s", [(-24.0, -22.0), (-16.0, -14.0)]),
    ("D", "w", [(16.0, 18.0)]), ("D", "e", [(0.5, 2.5), (4.0, 10.0), (11.0, 13.0)]), ("D", "s", []),
]
SCAF_LEVELS = [14.0, 12.27, 10.54, 8.81, 7.08, 5.35, 3.62, 1.88, 0.15]


def entry(mesh, group, role, wx, wy, wz, rot=0.0, scale=None, chosen=False, **extra):
    """One instance at the web point (wx, wy, wz), turned rot degrees about Blender Z."""
    bx_, by_, bz_ = wx, -wz, wy
    e = {"mesh": mesh, "group": group, "role": role, "web": [round(wx, 4), round(wy, 4), round(wz, 4)],
         "blender_m": [round(bx_, 4), round(by_, 4), round(bz_, 4)], "rot_z_deg": round(rot % 360.0, 4),
         "location_cm": [round(bx_ * 100, 2), round(-by_ * 100, 2), round(bz_ * 100, 2)], "yaw": round(-rot % 360.0, 4)}
    if scale is not None:
        e["scale"] = [round(float(s), 5) for s in scale]
    if chosen:
        e["chosen"] = True
    e.update(extra)
    return e


# ------------------------------------------------------------------------------------------------- roofs

def decks(out):
    for k, r in ROOFS.items():
        x0, x1 = r["x"]
        z0, z1 = r["z"]
        mesh = "SM_Roof_Deck_%s_4m" % r["deck"]
        nx, nz = int(math.ceil((x1 - x0) / 4.0 - 1e-6)), int(math.ceil((z1 - z0) / 4.0 - 1e-6))
        for i in range(nx):
            for j in range(nz):
                sx = min(4.0, x1 - x0 - 4.0 * i) / 4.0
                sz = min(4.0, z1 - z0 - 4.0 * j) / 4.0
                # deck pivot: a corner, x and Blender y from 0 to 4 -> the corner at (x, -z) runs toward -z
                wx, wz = x0 + 4.0 * i, z0 + 4.0 * j + 4.0 * sz
                if k == "D" and -13.0 < wx + 2 < -8.0 and 4.0 < wz - 2 < 10.0:
                    continue                                                            # the service shaft
                out.append(entry(mesh, k, "deck", wx, r["h"], wz, 0.0, scale=(sx, sz, 1.0) if (sx < 1 or sz < 1) else None))


def edge_line(k, side):
    """The edge's run in web coordinates: (fixed axis, value, run axis, start, end, outward normal in Blender, rot)."""
    r = ROOFS[k]
    x0, x1 = r["x"]
    z0, z1 = r["z"]
    T = 0.30
    if side == "n":                         # outward = -z (web) = +y Blender; run toward -x (Blender t = (-1, 0)): rot 180
        return ("z", z0, "x", x1, x0, 180.0)
    if side == "s":                         # outward +z = -y Blender: rot 0, run +x
        return ("z", z1, "x", x0, x1, 0.0)
    if side == "e":                         # outward +x: rot 90, run toward +y Blender = -z web
        return ("x", x1, "z", z1 - T, z0 + T, 90.0)
    return ("x", x0, "z", z0 + T, z1 - T, 270.0)   # west: outward -x: rot 270, run toward -y Blender = +z web


def parapets(out):
    for k, side, gaps in EDGES:
        r = ROOFS[k]
        fixed, val, run, a, b, rot = edge_line(k, side)
        sgn = 1.0 if b > a else -1.0
        lo, hi = min(a, b), max(a, b)
        pieces, cur = [], lo
        for g0, g1 in sorted(gaps):
            if g0 > cur:
                pieces.append((cur, g0))
            cur = max(cur, g1)
        if cur < hi:
            pieces.append((cur, hi))
        for (p0, p1) in pieces:
            start, end = (p0, p1) if sgn > 0 else (p1, p0)
            L = p1 - p0
            s = 0.0
            while L - s > 1e-6:
                left = L - s
                if left >= 4.0 - 1e-6:
                    mesh, ln, sc = "SM_Roof_Parapet_4m_%s" % r["brick"], 4.0, None
                elif left >= 1.0 - 1e-6:
                    mesh, ln, sc = "SM_Roof_Parapet_1m_%s" % r["brick"], 1.0, None
                else:
                    mesh, ln, sc = "SM_Roof_Parapet_1m_%s" % r["brick"], left, (left, 1.0, 1.0)
                pos = start + sgn * s
                wx, wz = (pos, val) if run == "x" else (val, pos)
                out.append(entry(mesh, k, "parapet_" + side, wx, r["h"], wz, rot, scale=sc))
                s += ln


def P(out, mesh, group, role, wx, wy, wz, rot=0.0, **kw):
    out.append(entry(mesh, group, role, wx, wy, wz, rot, **kw))


def roof_items(out):
    # A (R3): WT-A on the 4 m stand, bulkhead I1, HVAC, skylights, chimney row on the north party wall, tar kettle, antenna
    P(out, "SM_Roof_TankStand_4m", "A", "WT-A stand", -38.0, R3, -25.0, chosen=True)
    P(out, "SM_Roof_WaterTank_4p6", "A", "WT-A", -38.0, R3 + 4.30, -25.0, 0.0, chosen=True)
    P(out, "SM_Roof_Bulkhead_4x4", "A", "I1 bulkhead (door east)", -46.0, R3, -35.0, 0.0)
    P(out, "SM_Roof_HVAC_RTU_L", "A", "HVAC", -36.0, R3, -32.5, 0.0, chosen=True)
    P(out, "SM_Roof_HVAC_RTU_M", "A", "HVAC", -45.5, R3, -19.5, 90.0, chosen=True)
    P(out, "SM_Roof_Skylight_2x3", "A", "skylight", -41.5, R3, -28.0, 0.0, chosen=True)
    P(out, "SM_Roof_Skylight_2x3", "A", "skylight", -34.5, R3, -15.0, 0.0, chosen=True)
    for x in (-46.0, -40.5, -34.0):
        P(out, "SM_Roof_ChimneyStack", "A", "chimney row", x, R3, -37.0, 0.0, chosen=True)
    P(out, "SM_Roof_TarKettle", "A", "tar kettle (x0 beside it)", -35.2, R3, -18.6, 20.0)
    P(out, "SM_Roof_Antenna", "A", "antenna", -47.5, R3, -14.5, 0.0, chosen=True)
    P(out, "SM_Roof_Vent_Mushroom", "A", "vent (steam)", -44.0, R3, -27.0, chosen=True)
    P(out, "SM_Roof_NamePanel_6m", "A", "name panel", -37.0, R3 - 0.75, -38.0, 180.0, face="Plaque_Halvorsen")
    # B (R2): machine room I3, WT-B on the 2 m stand, bulkhead B, HVAC, vents
    P(out, "SM_Roof_MachineRoom_6x6", "B", "I3 machine room (door south)", -37.0, R2, -5.0, 0.0)
    P(out, "SM_Roof_TankStand_2m", "B", "WT-B stand", -45.0, R2, -5.0, chosen=True)
    P(out, "SM_Roof_WaterTank_3p6", "B", "WT-B", -45.0, R2 + 2.30, -5.0, 0.0, chosen=True)
    P(out, "SM_Roof_Bulkhead_4x4", "B", "bulkhead B (the wave door)", -44.0, R2, 3.5, 0.0, chosen=True)
    P(out, "SM_Roof_HVAC_RTU_M", "B", "HVAC", -34.0, R2, 4.0, 0.0, chosen=True)
    P(out, "SM_Roof_Vent_Mushroom", "B", "vent (steam)", -32.5, R2, -1.0, chosen=True)
    # E (R1): HVAC, dish, vent
    P(out, "SM_Roof_HVAC_RTU_M", "E", "HVAC", -44.0, R1, 15.0, 90.0, chosen=True)
    P(out, "SM_Roof_Dish", "E", "dish", -47.0, R1, 19.5, 30.0, chosen=True)
    P(out, "SM_Roof_Vent_Mushroom", "E", "vent", -38.0, R1, 19.0, chosen=True)
    # C (R2): the tank house I2 with WT-C on it, the HVAC row, vents, the roof billboard C1 and its name panel
    th_top = R2 + 2.8 + 0.35
    P(out, "SM_Roof_TankHouse_6x6", "C", "I2 tank house, Reel 7 (door south)", -19.0, R2, -32.0, 0.0)
    P(out, "SM_Roof_TankStand_2m", "C", "WT-C stand (on the tank house)", -19.0, th_top, -32.0)
    P(out, "SM_Roof_WaterTank_3p6", "C", "WT-C", -19.0, th_top + 2.30, -32.0, 0.0)
    P(out, "SM_Roof_WorkLight", "C", "tank house flood (shadowed sodium spot)", -19.0, R2 + 2.65, -28.75, 0.0)
    for x in (-24.5, -19.5, -14.5):
        P(out, "SM_Roof_HVAC_RTU_L", "C", "HVAC row", x, R2, -14.0, 0.0, chosen=True)
    P(out, "SM_Roof_Vent_Mushroom", "C", "vent (steam)", -25.5, R2, -24.0, chosen=True)
    P(out, "SM_Roof_Skylight_2x3", "C", "skylight", -14.0, R2, -8.0, 90.0, chosen=True)
    P(out, "SM_Roof_BillboardFrame_16x8", "C", "C1 roof billboard (faces east)", -8.8, R2, -20.0, 90.0, face="C1_MarloweFinch")
    P(out, "SM_Roof_NamePanel_6m", "C", "name panel (east cornice)", -8.0, R2 - 0.75, -27.0, 90.0, face="Plaque_Corvin")
    # D (R1): the service-stair bulkhead I4, HVAC, vents, the gantry door flood
    P(out, "SM_Roof_Bulkhead_5x6", "D", "I4 service stair bulkhead (door west)", -10.5, R1, 7.0, 0.0)
    P(out, "SM_Roof_HVAC_RTU_M", "D", "HVAC", -25.0, R1, 19.0, 0.0, chosen=True)
    P(out, "SM_Roof_Vent_Mushroom", "D", "vent (steam)", -16.0, R1, 15.0, chosen=True)
    P(out, "SM_Roof_WorkLight", "D", "gantry door flood on I4's north face (shadowed sodium spot)", -9.5, R1 + 2.4, 3.9, 180.0)
    # stairs and bridges (5.3)
    P(out, "SM_Roof_StairHead_2p4", "A-C", "L1 head bridge", -30.0, R3, -21.0, 0.0)
    P(out, "SM_Roof_SteelStair_3p6", "A-C", "L1 steel stair (descends east)", -27.6, R3, -21.0, 0.0)
    P(out, "SM_Roof_SteelStair_3p6", "A-B", "L2 tank stair (descends south)", -43.0, R3, -12.0, -90.0)
    P(out, "SM_Roof_SteelStair_3p6", "B-E", "L3 back stair (descends south)", -35.0, R2, 8.0, -90.0)
    P(out, "SM_Roof_SteelStair_3p6", "C-D", "L4 billboard stair (descends south)", -15.0, R2, -4.0, -90.0)
    P(out, "SM_Roof_PlankBridge_2p6x2", "B-C", "planks", -30.3, R2, -9.0, 0.0)
    P(out, "SM_Roof_PipeBridge_2p6x2", "E-D", "pipe bridge", -30.3, R1, 17.0, 0.0)


def gantry(out):
    P(out, "SM_Roof_Gantry_16m", "gantry", "gantry deck (R1)", -8.0, R1, 14.0, 90.0)
    P(out, "SM_Sign_LEDWall_16x9", "gantry", "G1 LED wall (faces east)", -4.2, R1 + 2.2, 14.0, 90.0, screen="G1")


def scaffold(out):
    L = SCAF_LEVELS
    for k in range(1, 9):                                                    # flight k from L[k-1] down to L[k]
        if k % 2:                                                            # odd: descends N -> S in the west column
            P(out, "SM_Scaf_Flight_2p4", "scaffold", "flight %d" % k, -6.8, L[k], 18.0, 90.0)
        else:                                                                # even: descends S -> N in the east column
            P(out, "SM_Scaf_Flight_2p4", "scaffold", "flight %d" % k, -4.2, L[k], 15.5, -90.0)
    for k in (0, 2, 4, 6):                                                   # N landings (z 14..15.5)
        P(out, "SM_Scaf_Landing_2p4", "scaffold", "N landing %.2f" % L[k], -5.5, L[k], 14.0, -90.0)
    for k in (1, 3, 5, 7):                                                   # S landings (z 18..20)
        P(out, "SM_Scaf_Landing_2p4", "scaffold", "S landing %.2f" % L[k], -5.5, L[k], 18.0, -90.0, scale=(1.3333, 1.0, 1.0))
    lift = 0.346 * 5
    for i in range(9):                                                       # outer frames, a lift above the top as the guard
        z = 0.15 + i * lift
        for zz, sc in ((20.0, None), (17.5, None), (15.0, (0.4, 1.0, 1.0))):     # east face, south to north (rot 90)
            P(out, "SM_Scaf_Bay_Frame", "scaffold", "east frame", -3.0, z, zz, 90.0, scale=sc)
            if zz == 17.5:
                P(out, "SM_Scaf_Netting_Panel", "scaffold", "east netting (flights; the landings stay open)", -3.0, z, zz, 90.0)
        for xx in (-8.0, -5.5):                                              # south face (rot 0)
            P(out, "SM_Scaf_Bay_Frame", "scaffold", "south frame", xx, z, 20.0, 0.0)
            if i != 3:                                                       # the shed-hop opening at the 5.35 landing
                P(out, "SM_Scaf_Netting_Panel", "scaffold", "south netting", xx, z, 20.0, 0.0)
        for zz in (20.0, 17.5):                                              # the spine between the columns (no netting)
            P(out, "SM_Scaf_Bay_Frame", "scaffold", "spine", -5.5, z, zz, 90.0)
    P(out, "SM_Scaf_Sign", "scaffold", "contractor board (south face)", -6.7, 2.6, 20.12, 0.0, face="Board_KesslerRoth")


def screens(out):
    """The art-only screens beyond the bounds (positions chosen by this lane; midtown.md 12.2 gives sizes and sides)."""
    def tiled(sid, cols, rows, x_of, y0, rot, slide):
        for i in range(cols):
            for j in range(rows):
                wx, wz = x_of(i)
                P(out, "SM_Sign_LEDWall_Tile_2m", "screens", "%s tile" % sid, wx, y0 + 2.0 * j, wz, rot, chosen=True,
                  screen=sid, tile=[i, j], tiles=[cols, rows], first_slide=slide)
    tiled("E1", 12, 9, lambda i: (33.0, -30.0 + 2.0 * i), 10.0, -90.0, "E1_Miravesse")       # east tower podium, faces west
    tiled("E2a", 4, 10, lambda i: (33.0, -4.0 + 2.0 * i), 6.0, -90.0, "E2a_Kestrel")       # east hotel verticals
    tiled("E2b", 4, 10, lambda i: (33.0, 6.0 + 2.0 * i), 6.0, -90.0, "E2b_BrassBun")
    # E3: the corner screen at x 30, z 22, ten columns turned 6 degrees apart (54 degrees of arc, radius 19.1 m), the arc's
    # middle facing south-west across the square
    R = 1.0 / math.sin(math.radians(3.0))
    n_mid = math.atan2(-1.0, -1.0)                                          # the middle faces Blender (-1, -1): web south-west
    mx, my = 31.5, -23.5                                                     # the middle tile's centre, Blender
    cx, cy = mx - R * math.cos(n_mid), my - R * math.sin(n_mid)              # the arc's centre, behind the face
    for i in range(10):
        phi = n_mid + math.radians(-27.0 + 6.0 * i)
        nx, ny = math.cos(phi), math.sin(phi)                               # the tile faces outward from the centre
        px, py = cx + R * nx, cy + R * ny
        th = math.atan2(nx, -ny)                                             # local -Y -> (nx, ny)
        bx_, by_ = px - math.cos(th), py - math.sin(th)                      # pivot: the tile's left end
        for j in range(6):
            P(out, "SM_Sign_LEDWall_Tile_2m", "screens", "E3 tile", bx_, 14.0 + 2.0 * j, -by_, math.degrees(th), chosen=True,
              screen="E3", tile=[i, j], tiles=[10, 6], first_slide="E3_Meridale")
    tiled("S1", 6, 3, lambda i: (12.0 - 2.0 * i, 36.4), 6.0, 180.0, "S1_Duskline")       # W 46 St south facade, faces north
    P(out, "SM_Sign_TowerStack", "screens", "N1 tower stack (faces south)", 5.0, 22.0, -48.0, 0.0, chosen=True, screen="N1",
      first_slide="N1_Horovan")
    for i in range(6):                                                       # the ticker on the theatre, faces west
        P(out, "SM_Sign_Ticker_4m", "screens", "ticker module %d" % i, 30.0, 8.0, -30.0 + 4.0 * i, -90.0, module=i)


def build_all():
    out = []
    decks(out)
    parapets(out)
    roof_items(out)
    gantry(out)
    scaffold(out)
    screens(out)
    return out


def write_placements(path):
    out = build_all()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    meshes = sorted({e["mesh"] for e in out})
    doc = {"about": "Midtown (Level 3) roofs, gantry, scaffold and screens assembled from the midtown kit (assets/_midtown_place.py). "
                    "Each entry: mesh, group, role, web (x, y, z), blender_m, rot_z_deg, location_cm (Unreal), yaw, optional scale "
                    "(x, y, z), face (Sign_MT_Atlas1 cell) or screen (+ tile, tiles, first_slide). 'chosen': a position the design "
                    "leaves open, chosen by the art lane.",
           "count": len(out), "meshes": meshes, "levels": {"R1": R1, "R2": R2, "R3": R3, "scaffold": SCAF_LEVELS},
           "instances": out}
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    return len(out)


if __name__ == "__main__":
    from mi import paths
    n = write_placements(os.path.join(paths.out, "placements", "placements_midtown.json"))
    print("%d placements" % n)
