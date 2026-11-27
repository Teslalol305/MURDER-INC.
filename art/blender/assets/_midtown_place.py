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


# ------------------------------------------------------------------------------------------------- the level data (round 2)

LEVEL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "tools", "levels", "data", "level_midtown.json")
_DATA = {}


def data():
    if not _DATA:
        with open(LEVEL) as f:
            _DATA["d"] = json.load(f)
    return _DATA["d"]


def boxes(tag=None, part=None):
    """The level's colliders with this tag (or part, or part prefix ending in '*'), in index order."""
    out = []
    for c in data()["colliders"]["boxes"]:
        if tag is not None and c["tag"] != tag:
            continue
        if part is not None:
            q = c.get("part") or ""
            if not (q == part or (part.endswith("*") and q.startswith(part[:-1]))):
                continue
        out.append(c)
    return out


def rect(c):
    mn, mx = c["web"]["min"], c["web"]["max"]
    return mn["x"], mx["x"], mn["y"], mx["y"], mn["z"], mx["z"]


def fit_parts(parts, mode):
    """A fit record naming the colliders (by part) an instance dresses."""
    idx = [c["index"] for p in parts for c in boxes(part=p)]
    assert idx, parts
    return {"colliders": idx, "mode": mode}


def fitted(out, mesh, group, role, c, core, mode="scale", rots=(0.0, 90.0), prefer=None, y=None, chosen_facing=False, above=None, **kw):
    """Place `mesh` on the collider c: its centre on the box's centre, its base on the box's bottom (or y), turned so the
    mesh's core footprint (local X, local Y, height) lies along the box, scaled to the box in mode "scale" (mode "centre":
    no scale, the residual recorded). prefer: the rotation to use among the equivalent ones (0 or 180, 90 or 270)."""
    x0, x1, y0, y1, z0, z1 = rect(c)
    ex, ey, ez = x1 - x0, y1 - y0, z1 - z0
    best = None
    for r in rots:
        a, b_ = (ex, ez) if r % 180 == 0 else (ez, ex)
        sc = (a / core[0], b_ / core[1], ey / core[2])
        an = max(abs(math.log(v)) for v in sc[:2])
        if best is None or an < best[0] - 1e-9:
            best = (an, r, sc)
    _an, r, sc = best
    if prefer is not None and (prefer - r) % 180 == 0:
        r = prefer
    f = {"colliders": [c["index"]], "tag": c["tag"], "mode": mode}
    if above:
        f["above"] = above
    if mode == "scale":
        sc = tuple(round(v, 4) for v in sc)
        kw["scale"] = sc if any(abs(v - 1.0) > 0.005 for v in sc) else None
        f["scale"] = list(sc)
    else:
        f["residual_m"] = [round(core[0] * 1.0 - (ex if r % 180 == 0 else ez), 3), round(core[1] - (ez if r % 180 == 0 else ex), 3),
                           round(core[2] - ey, 3)]
    if chosen_facing:
        kw["chosen"] = True
        f["chosen"] = "the facing (the box is symmetric)"
    P(out, mesh, group, role, (x0 + x1) / 2, y0 if y is None else y, (z0 + z1) / 2, r, fit=f, **kw)


def along(out, mesh, group, role, c, L, core_w, core_h, y=None, **kw):
    """A run of n modules L long along the box's long axis, stretched to fill it (jersey barriers, chimney rows)."""
    x0, x1, y0, y1, z0, z1 = rect(c)
    ex, ez = x1 - x0, z1 - z0
    run, wid = (ex, ez) if ex >= ez else (ez, ex)
    n = max(1, int(round(run / L)))
    s = run / (n * L)
    sc = (round(s, 4), round(wid / core_w, 4), round((y1 - y0) / core_h, 4))
    for i in range(n):
        t = -run / 2 + (i + 0.5) * run / n
        wx, wz = ((x0 + x1) / 2 + t, (z0 + z1) / 2) if ex >= ez else ((x0 + x1) / 2, (z0 + z1) / 2 + t)
        P(out, mesh, group, role + (" %d/%d" % (i + 1, n) if n > 1 else ""), wx, y0 if y is None else y, wz, 0.0 if ex >= ez else 90.0,
          scale=sc if any(abs(v - 1.0) > 0.005 for v in sc) else None,
          fit={"colliders": [c["index"]], "tag": c["tag"], "mode": "scale", "modules": n, "scale": list(sc)}, **kw)


# ------------------------------------------------------------------------------------------------- roofs, fitted (round 2)

def towers(out):
    """WT-A, WT-B, WT-C: each stand and tank sized to its colliders (legs 0.45 square; the tank's box)."""
    for t, grp, base in (("A", "A", R3), ("B", "B", R2), ("C", "C", 20.7)):
        legs = boxes(part="WT%s.leg" % t)
        tank = boxes(part="WT%s.tank" % t)[0]
        x0, x1, y0, y1, z0, z1 = rect(tank)
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        lc = [((rect(c)[0] + rect(c)[1]) / 2, (rect(c)[4] + rect(c)[5]) / 2) for c in legs]
        assert abs(sum(p[0] for p in lc) / 4 - cx) < 0.01 and abs(sum(p[1] for p in lc) / 4 - cz) < 0.01
        P(out, "SM_Roof_TankStand_%s" % t, grp, "WT-%s stand%s" % (t, " (on the tank house)" if t == "C" else ""), cx, base, cz,
          fit={"colliders": [c["index"] for c in legs], "mode": "part", "legs_m": round(max(p[0] for p in lc) - min(p[0] for p in lc), 3)})
        P(out, "SM_Roof_WaterTank_%s" % t, grp, "WT-%s" % t, cx, y0, cz, 0.0, chosen=True,
          fit={"colliders": [tank["index"]], "mode": "part", "chosen": "the ladder's side (+X)"})


# core footprints (local X, local Y, height) of the roof dressing: the part the level's box stands for
CORE = {"SM_Roof_HVAC_RTU_L": (3.7, 1.9, 1.65), "SM_Roof_HVAC_RTU_M": (2.3, 1.4, 1.40), "SM_Roof_HVAC_RTU_S": (1.9, 1.9, 1.40),
        "SM_Roof_Skylight_2x3": (3.1, 2.1, 1.095), "SM_Roof_Vent_Mushroom": (0.88, 0.88, 1.02), "SM_Roof_TarKettle": (1.0, 1.0, 1.14),
        "SM_Roof_Dish": (1.5, 1.5, 2.02), "SM_Roof_Antenna": (2.12, 2.12, 4.3)}


def roof_group(c):
    x, z = (rect(c)[0] + rect(c)[1]) / 2, (rect(c)[4] + rect(c)[5]) / 2
    for k, r in ROOFS.items():
        if r["x"][0] <= x <= r["x"][1] and r["z"][0] <= z <= r["z"][1]:
            return k
    return "roof"


def roof_dressing(out):
    for c in boxes("hvac_rtu"):                     # the unit whose cabinet needs the least stretch
        x0, x1, y0, y1, z0, z1 = rect(c)
        best = None
        for m in ("SM_Roof_HVAC_RTU_S", "SM_Roof_HVAC_RTU_M", "SM_Roof_HVAC_RTU_L"):
            for a, b_ in (((x1 - x0), (z1 - z0)), ((z1 - z0), (x1 - x0))):
                an = max(abs(math.log(a / CORE[m][0])), abs(math.log(b_ / CORE[m][1])))
                if best is None or an < best[0]:
                    best = (an, m)
        fitted(out, best[1], roof_group(c), "HVAC", c, CORE[best[1]])
    for c in boxes("skylight"):
        fitted(out, "SM_Roof_Skylight_2x3", roof_group(c), "skylight", c, CORE["SM_Roof_Skylight_2x3"])
    for c in boxes("chimney_stack"):
        along(out, "SM_Roof_ChimneyStack", roof_group(c), "chimney row", c, 1.3, 0.8, 2.425)
    for c in boxes("roof_vent"):
        fitted(out, "SM_Roof_Vent_Mushroom", roof_group(c), "vent", c, CORE["SM_Roof_Vent_Mushroom"])
    for c in boxes("tar_kettle"):
        fitted(out, "SM_Roof_TarKettle", roof_group(c), "tar kettle (x0 beside it)", c, CORE["SM_Roof_TarKettle"], mode="centre")
    for c in boxes("satellite_dish"):
        fitted(out, "SM_Roof_Dish", roof_group(c), "dish", c, CORE["SM_Roof_Dish"], mode="centre")
    for c in boxes("antenna_mast"):
        fitted(out, "SM_Roof_Antenna", roof_group(c), "antenna", c, CORE["SM_Roof_Antenna"], mode="centre",
               above="the mast and its panels over the cabinet box (shots pass)")


# ------------------------------------------------------------------------------------------------- the square (round 2)

SW = 0.15
REUSED = {"SM_Street_Bench": "gaps", "SM_Furn_StreetLamp": "furniture", "SM_Prop_CT_Hydrant": "canal",
          "SM_Street_SignPost": "gaps", "SM_Furn_NewspaperBox": "furniture", "SM_Furn_TrashBags_A": "furniture", "SM_Furn_TrashBags_B": "furniture",
          "SM_Furn_BusShelter": "gaps"}


def square(out):
    """THE STAND and THE BOOTH from their colliders, then the plaza and the roadways' furniture, every piece on its box."""
    for k in range(1, 9):
        for side in (("west", "east") if k < 6 else ("",)):
            part = "stand.tier%d%s" % (k, "." + side if side else "")
            c = boxes(part=part)[0]
            x0, x1, y0, y1, z0, z1 = rect(c)
            P(out, "SM_Sq_Stand_Tier_%dm" % (3 if k < 6 else 12), "stand", "tier %d%s" % (k, " " + side if side else ""),
              (x0 + x1) / 2, y1, (z0 + z1) / 2, 0.0, fit={"colliders": [c["index"]], "mode": "part", "tier": k})
    wings = [c["index"] for c in boxes(part="stand.tier*") if c["part"].endswith(("west", "east"))]
    for x, what in ((10.0, "west wing, outer"), (13.0, "west wing, court side"), (19.0, "east wing, court side"), (22.0, "east wing, outer")):
        xi = x + (0.02 if x in (10.0, 19.0) else -0.02)
        P(out, "SM_Sq_Stand_WingSide", "stand", "side cladding, " + what, xi, SW, -22.0, 0.0,
          fit={"colliders": wings, "mode": "part"})
    for side, x in (("west", 10.3), ("east", 21.7)):
        P(out, "SM_Sq_Booth_WallSide", "booth", "booth %s wall (2.0 m Goon door)" % side, x, SW, -29.5, 0.0, face="Label_CrewOnly",
          fit=fit_parts(["booth.wall." + side, "booth.wall.%s.lintel" % side], "part"))
    P(out, "SM_Sq_Booth_FrontWall", "booth", "booth front wall and the shoot-through slot", 16.0, SW, -29.35, 0.0,
      fit=fit_parts(["booth.wall.front", "booth.slot.sill", "booth.slot.head", "booth.slot.frame"], "part"))
    P(out, "SM_Sq_Stand_Back", "stand", "booth back wall and the top tier's guard scrim", 16.0, SW, -34.0, 0.0,
      fit=fit_parts(["booth.wall.back", "stand.guard.north", "stand.guard.west", "stand.guard.east"], "part"))
    fitted(out, "SM_Sq_Booth_Desk", "booth", "broadcast desk", boxes("booth_desk")[0], (3.2, 0.6, 0.8), prefer=0.0)
    fitted(out, "SM_Sq_Booth_Rack", "booth", "equipment racks", boxes("booth_rack")[0], (1.4, 0.8, 1.75), prefer=0.0)
    fitted(out, "SM_Sq_Booth_MonitorCart", "booth", "monitor cart", boxes("monitor_cart")[0], (1.2, 0.5, 1.0), prefer=0.0,
           slide="G1_Takeover")
    d = boxes("booth_desk")[0]
    dx0, dx1, _dy0, dy1, dz0, dz1 = rect(d)
    for i, lx in enumerate((-0.9, -0.3, 0.9)):                                   # on the desk, behind the console
        P(out, "SM_Sq_Booth_Monitor", "booth", "booth monitor %d (the program feed)" % (i + 1), (dx0 + dx1) / 2 + lx, dy1 - 0.02,
          (dz0 + dz1) / 2 - 0.20, 0.0, chosen=True, slide="G1_Takeover" if i != 1 else "G1_StandBy", on=d["index"])
    fitted(out, "SM_Sq_CableDrum", "stand", "cable drum (front court)", boxes("cable_drum")[0], (0.8, 0.8, 0.97))
    # the plaza
    for c in boxes("planter_granite"):
        fitted(out, "SM_Sq_Planter_Granite_4m", "plaza", "granite planter", c, (4.04, 1.04, 0.90))
    for c, facing in zip(boxes("kiosk_souvenir"), (0.0, 180.0)):
        fitted(out, "SM_Sq_Kiosk_Souvenir", "plaza", "souvenir kiosk", c, (3.0, 2.0, 2.45), prefer=facing, chosen_facing=True,
               face="Kiosk_SeventhAv")
    for c, facing in zip(boxes("food_cart"), (180.0, 0.0)):
        fitted(out, "SM_Sq_FoodCart", "plaza", "food cart (lit, steaming, umbrella half down)", c, (1.8, 1.0, 1.25), prefer=facing,
               chosen_facing=True, face="Cart_Menu", above="the umbrella, half down, over the cart's box (shots pass)")
    for c in boxes("cafe_table"):
        fitted(out, "SM_Sq_CafeTable", "plaza", "cafe table", c, (0.8, 0.8, 0.75))
        x0, x1, _y0, _y1, z0, z1 = rect(c)
        for dx, rot in ((-0.62, 90.0), (0.62, 270.0)):
            P(out, "SM_Sq_CafeChair", "plaza", "cafe chair (dressing, no collider)", (x0 + x1) / 2 + dx, SW, (z0 + z1) / 2, rot, chosen=True,
              near=c["index"])
    for c in boxes("cafe_chairs"):
        fitted(out, "SM_Sq_CafeChair_Stack", "plaza", "cafe chairs, stacked two high", c, (0.5, 0.5, 0.9), mode="centre")
    for c in boxes("light_pole"):
        fitted(out, "SM_Sq_LightPole_LED", "plaza", "plaza LED pole (twin head)", c, (0.3, 0.3, 8.0), mode="centre")
    for c in boxes("cable_ramp"):
        fitted(out, "SM_Sq_CableRamp_1p2", "plaza", "cable ramp", c, (1.2, 0.5, 0.08))
    fitted(out, "SM_Sq_Generator", "premiere", "the premiere's generator by the Stand", boxes("generator")[0], (1.6, 1.2, 1.15))
    for c in boxes("road_cases"):
        fitted(out, "SM_Sq_RoadCase_Stack", "premiere", "the crew's road cases", c, (2.0, 1.4, 1.9), face="Stencil_Brightwire")
    # barriers
    for c in boxes("jersey_barrier"):
        along(out, "SM_Sq_Barrier_Jersey_1p8", "barriers", "concrete barrier", c, 1.8, 0.5, 0.81)
    for c in boxes("water_barrier"):
        x0, x1, y0, y1, z0, z1 = rect(c)
        if (x1 - x0) >= (z1 - z0):
            along(out, "SM_Sq_Barrier_Water_1p9", "barriers", "water barrier", c, 1.9, 0.6, 0.9)
        else:                                                                  # a cluster: two side by side along z
            n = max(1, int((x1 - x0) // 0.6))
            for i in range(n):
                wx = x0 + (i + 0.5) * (x1 - x0) / n
                P(out, "SM_Sq_Barrier_Water_1p9", "barriers", "water barrier (pushed together)", wx, y0, (z0 + z1) / 2, 90.0,
                  scale=(round((z1 - z0) / 1.9, 4), 1.0, 1.0), fit={"colliders": [c["index"]], "tag": c["tag"], "mode": "scale",
                                                                     "modules": n})
    for c in boxes("bike_barrier"):
        fitted(out, "SM_Sq_Barrier_Bike_2p4", "barriers", "crowd-control barrier", c, (2.4, 0.5, 1.1))
    # reused from the Block's kits (midtown.md 14.1)
    for c, facing in zip(boxes("bench"), (0.0, 180.0, 180.0, 180.0)):
        fitted(out, "SM_Street_Bench", "plaza", "bench (reused, gaps)", c, (1.76, 0.56, 0.84), mode="centre", prefer=facing,
               chosen_facing=True, reused="gaps")
    for c in boxes("trash_can"):
        fitted(out, "SM_Sq_TrashCan", "street", "litter basket (the lane's light one: the Block's wire basket is 17k triangles)", c, (0.60, 0.60, 0.99), mode="centre")
    for c in boxes("street_lamp"):
        x0, x1 = rect(c)[:2]
        rot = 90.0 if x0 < 10 else 270.0                                        # the davit arm (-Y) over the roadway
        fitted(out, "SM_Furn_StreetLamp", "street", "avenue street lamp (reused, furniture; the arm over the roadway)", c,
               (0.34, 0.34, 7.88), mode="centre", rots=(rot,), reused="furniture")


def roof_items(out):
    """The rooms, water towers and roof dressing, fitted to the level data's colliders (round 2): every position the first
    round chose is now the collider's (lane D's colliders win); the art with no collider under it is gone."""
    # A (R3): bulkhead I1, WT-A on its stand, the tar kettle's roof, the name panel
    P(out, "SM_Roof_Bulkhead_4x4", "A", "I1 bulkhead (door east)", -46.0, R3, -35.0, 0.0,
      fit=fit_parts(["bulkheadA.wall", "bulkheadA.wall.east", "bulkheadA.roof"], "part"))
    towers(out)
    P(out, "SM_Roof_NamePanel_6m", "A", "name panel", -37.0, R3 - 0.75, -38.0, 180.0, face="Plaque_Halvorsen")
    # B (R2): machine room I3, bulkhead B (the wave door)
    P(out, "SM_Roof_MachineRoom_6x6", "B", "I3 machine room (door south)", -37.0, R2, -5.0, 0.0,
      fit=fit_parts(["machineroom.wall", "machineroom.wall.south", "machineroom.wall.south.lintel", "machineroom.roof"], "part"))
    P(out, "SM_Roof_Bulkhead_4x4", "B", "bulkhead B (the wave door, east)", -46.0, R2, 2.0, 0.0, fit=fit_parts(["bulkheadB"], "part"))
    # C (R2): the tank house I2 under WT-C (the tower is in towers()), the roof billboard C1 and its name panel
    P(out, "SM_Roof_TankHouse_6x6", "C", "I2 tank house, Reel 7 (door south)", -19.0, R2, -32.0, 0.0,
      fit=fit_parts(["tankhouse.wall.north", "tankhouse.wall.west", "tankhouse.wall.east", "tankhouse.wall.south", "tankhouse.wall.south.lintel", "tankhouse.roof"], "part"))
    P(out, "SM_Roof_WorkLight", "C", "tank house flood (shadowed sodium spot)", -19.0, R2 + 2.65, -28.75, 0.0)
    P(out, "SM_Roof_BillboardFrame_16x8", "C", "C1 roof billboard (faces east)", -8.8, R2, -20.0, 90.0, face="C1_MarloweFinch")
    P(out, "SM_Roof_NamePanel_6m", "C", "name panel (east cornice)", -8.0, R2 - 0.75, -27.0, 90.0, face="Plaque_Corvin")
    # D (R1): the service-stair bulkhead I4 and the gantry door flood
    P(out, "SM_Roof_Bulkhead_5x6", "D", "I4 service stair bulkhead (door west)", -10.5, R1, 7.0, 0.0,
      fit=fit_parts(["L6.bulkhead.west", "L6.bulkhead.east", "L6.bulkhead.roof"], "part"))
    P(out, "SM_Roof_WorkLight", "D", "gantry door flood on I4's north face (shadowed sodium spot)", -9.5, R1 + 2.4, 3.9, 180.0)
    roof_dressing(out)
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
    def edges(sid, cols, rows, pivot_of, ldir_of, y0, rot_of):
        """The bezel round a tiled screen's outside: H pieces under the bottom row and over the top one, V pieces left of
        the first column and right of the last (the tiles are flush, the bezel is only here)."""
        for i in range(cols):
            (wx, wz), rot = pivot_of(i), rot_of(i)
            P(out, "SM_Sign_LEDWall_Edge_H_2m", "screens", "%s bezel bottom" % sid, wx, y0, wz, rot, chosen=True, screen=sid)
            P(out, "SM_Sign_LEDWall_Edge_H_2m", "screens", "%s bezel top" % sid, wx, y0 + 2.0 * rows + 0.12, wz, rot, chosen=True,
              screen=sid)
        for i, off in ((0, 0.0), (cols - 1, 2.12)):
            (wx, wz), (lx, lz), rot = pivot_of(i), ldir_of(i), rot_of(i)
            for j in range(rows):
                P(out, "SM_Sign_LEDWall_Edge_V_2m", "screens", "%s bezel side" % sid, wx + lx * off, y0 + 2.0 * j, wz + lz * off, rot,
                  chosen=True, screen=sid)

    def tiled(sid, cols, rows, x_of, y0, rot, slide):
        for i in range(cols):
            for j in range(rows):
                wx, wz = x_of(i)
                P(out, "SM_Sign_LEDWall_Tile_2m", "screens", "%s tile" % sid, wx, y0 + 2.0 * j, wz, rot, chosen=True,
                  screen=sid, tile=[i, j], tiles=[cols, rows], first_slide=slide)
        a, b_ = x_of(0), x_of(1)
        ld = ((b_[0] - a[0]) / 2.0, (b_[1] - a[1]) / 2.0)                    # the tile's local +X in web (x, z)
        edges(sid, cols, rows, x_of, lambda i: ld, y0, lambda i: rot)
    tiled("E1", 12, 9, lambda i: (33.0, -30.0 + 2.0 * i), 10.0, -90.0, "E1_Miravesse")       # east tower podium, faces west
    tiled("E2a", 4, 10, lambda i: (33.0, -4.0 + 2.0 * i), 6.0, -90.0, "E2a_Kestrel")       # east hotel verticals
    tiled("E2b", 4, 10, lambda i: (33.0, 6.0 + 2.0 * i), 6.0, -90.0, "E2b_BrassBun")
    # E3: the corner screen at x 30, z 22, ten columns turned 6 degrees apart (54 degrees of arc, radius 19.1 m), the arc's
    # middle facing south-west across the square
    R = 1.0 / math.sin(math.radians(3.0))
    n_mid = math.atan2(-1.0, -1.0)                                          # the middle faces Blender (-1, -1): web south-west
    mx, my = 31.5, -23.5                                                     # the middle tile's centre, Blender
    cx, cy = mx - R * math.cos(n_mid), my - R * math.sin(n_mid)              # the arc's centre, behind the face
    e3 = []
    for i in range(10):
        phi = n_mid + math.radians(-27.0 + 6.0 * i)
        nx, ny = math.cos(phi), math.sin(phi)                               # the tile faces outward from the centre
        px, py = cx + R * nx, cy + R * ny
        th = math.atan2(nx, -ny)                                             # local -Y -> (nx, ny)
        bx_, by_ = px - math.cos(th), py - math.sin(th)                      # pivot: the tile's left end
        e3.append(((bx_, -by_), (math.cos(th), -math.sin(th)), math.degrees(th)))
        for j in range(6):
            P(out, "SM_Sign_LEDWall_Tile_2m", "screens", "E3 tile", bx_, 14.0 + 2.0 * j, -by_, math.degrees(th), chosen=True,
              screen="E3", tile=[i, j], tiles=[10, 6], first_slide="E3_Meridale")
    edges("E3", 10, 6, lambda i: e3[i][0], lambda i: e3[i][1], 14.0, lambda i: e3[i][2])
    tiled("S1", 6, 3, lambda i: (12.0 - 2.0 * i, 36.4), 6.0, 180.0, "S1_Duskline")       # W 46 St south facade, faces north
    P(out, "SM_Sign_TowerStack", "screens", "N1 tower stack (faces south)", 5.0, 22.0, -48.0, 0.0, chosen=True, screen="N1",
      slides=["N1_Horovan", "N1_Northweft", "N1_Fizzwick"],
      slides_note="one ad per face, bottom to top (the mesh's FaceIndex UV: u 0, 1, 2); they rotate together on the 12 s cycle")
    for i in range(6):                                                       # the ticker on the theatre, faces west
        P(out, "SM_Sign_Ticker_4m", "screens", "ticker module %d" % i, 30.0, 8.0, -30.0 + 4.0 * i, -90.0, module=i)


# ------------------------------------------------------------------------------------------------- round 3: dressing, the premiere's set, the facades

CORE3 = {"SM_Roof_Lounge_Bar": (4.0, 1.0, 1.1), "SM_Roof_Lounger": (1.4, 1.0, 0.5), "SM_Roof_Lounger_Stack": (1.5, 2.0, 0.9),
         "SM_Roof_Umbrella_Folded": (0.4, 1.0, 2.2), "SM_Roof_PlanterBox": (1.0, 2.0, 0.9), "SM_Roof_DuctBox_1p6": (1.6, 1.6, 1.1),
         "SM_Roof_VentBox_1x1": (1.0, 1.0, 1.2), "SM_Roof_ConduitBox_1p4": (1.4, 0.8, 0.7), "SM_Roof_ConduitRun_4m": (0.4, 4.0, 0.7),
         "SM_Roof_PipeSleepers_1p6": (1.6, 0.8, 0.35), "SM_Roof_FanHousing_1p6": (1.6, 1.6, 1.0),
         "SM_Sq_BollardPlanter": (0.7, 0.7, 0.9), "SM_Sq_Newsstand": (2.0, 1.4, 2.6), "SM_Sq_PhoneKiosk": (1.2, 0.5, 2.5),
         "SM_Sq_WayfindingPylon": (0.6, 1.0, 2.4), "SM_Sq_ATM_Kiosk": (0.7, 0.8, 1.4), "SM_Sq_Standpipe": (0.3, 0.3, 0.9),
         "SM_Sq_ValetStand": (1.6, 1.0, 1.1), "SM_Sq_LuggageCart": (1.5, 0.6, 1.2), "SM_Sq_Crates_Stack": (1.3, 1.4, 1.0),
         "SM_Sq_Hoarding_6m": (0.35, 6.0, 2.4), "SM_Sq_Van_Broadcast_6p8": (6.8, 2.2, 3.4), "SM_Sq_Truck_Satellite": (7.0, 2.2, 3.4),
         "SM_Sq_Truck_Catering": (6.8, 2.2, 3.0), "SM_Sq_Truck_Generator": (4.2, 2.2, 3.2), "SM_Sq_Truck_Cable": (7.0, 2.6, 3.3),
         "SM_Sq_Truck_Staging": (8.0, 2.4, 3.3), "SM_Sq_Trailer_Production_6m": (6.0, 2.1, 3.0), "SM_Sq_Trailer_Production_6p4": (6.4, 2.4, 3.0),
         "SM_Sq_ScreenTrailer": (4.0, 0.6, 4.0), "SM_Sq_LightTower": (3.0, 1.4, 2.6), "SM_Sq_TrussTower": (0.6, 0.6, 4.2),
         "SM_Sq_PressWall_3p4": (3.4, 0.3, 2.4), "SM_Sq_VipTent_3x3": (3.0, 3.0, 2.8), "SM_Sq_MerchBooth": (1.6, 1.2, 2.5),
         "SM_Sq_CoatCheck": (1.4, 1.0, 2.2), "SM_Sq_SecurityBooth": (1.4, 1.4, 2.6), "SM_Sq_InfoBooth": (2.6, 1.2, 2.4),
         "SM_Sq_PhotoBooth": (1.4, 1.4, 2.3), "SM_Sq_PortableToilets": (2.4, 1.2, 2.45), "SM_Sq_CameraRiser": (1.6, 0.8, 2.6),
         "SM_Sq_SpeakerStack": (1.4, 0.8, 2.75), "SM_Sq_SoundTower": (1.2, 1.2, 4.0), "SM_Vehicle_CityBus": (12.0, 2.6, 3.3),
         "SM_Vehicle_MT_Sedan": (4.61, 1.85, 1.45), "SM_Vehicle_MT_Taxi": (4.61, 1.85, 1.55), "SM_Vehicle_MT_SUV": (4.91, 1.99, 1.82),
         "SM_Vehicle_MT_Van": (5.21, 1.95, 2.19)}
PARKED = {"sedan": "SM_Vehicle_MT_Sedan", "taxi": "SM_Vehicle_MT_Taxi", "suv": "SM_Vehicle_MT_SUV", "van": "SM_Vehicle_MT_Van"}
ROOF_ABOVE = {"SM_Roof_Lounge_Bar": "the back bar's shelves over the island's box (shots pass)",
              "SM_Roof_Lounger": "the back cushion over the seat's box", "SM_Sq_LightTower": "the mast raised to 5.6 over the trailer's box (shots pass)",
              "SM_Sq_TrussTower": "the lamp bar over the tower's box"}
NOSE_SOUTH = 270.0                       # the vehicles' nose (+X) toward +z web (south), as the southbound avenues run
FRONT_FACES = {"newsstand": {460: 270.0, 461: 270.0, 477: 90.0}}


def tag_fit(out, mesh, group, role, tag, prefer=None, **kw):
    for c in boxes(tag):
        fitted(out, mesh, group, role, c, CORE3[mesh], prefer=prefer, **kw)


def dressing(out):
    """Round 3: THE LOFTLARK, the roof boxes, the plaza's small dressing and the premiere's set, each on its collider."""
    # THE LOFTLARK (D): the raised deck, the bar, loungers, folded umbrellas, planter boxes, the neon
    deck = [c["index"] for c in boxes("deck") if c.get("part", "").startswith("D.lounge")]
    d0 = boxes(part="D.lounge.deck")[0]
    x0, x1, y0, y1, z0, z1 = rect(d0)
    P(out, "SM_Roof_LoungeDeck_9x7", "D", "THE LOFTLARK's raised timber deck (0.6 m, a 0.3 m step on its open sides)", (x0 + x1) / 2, y0, (z0 + z1) / 2, 0.0,
      fit={"colliders": deck, "mode": "part"})
    tag_fit(out, "SM_Roof_Lounge_Bar", "D", "THE LOFTLARK's bar (guests' side west)", "lounge_bar", prefer=0.0, above=ROOF_ABOVE["SM_Roof_Lounge_Bar"])
    tag_fit(out, "SM_Roof_Lounger", "D", "lounge sofa", "lounger", above=ROOF_ABOVE["SM_Roof_Lounger"])
    tag_fit(out, "SM_Roof_Lounger_Stack", "D", "folded sun loungers", "lounger_stack")
    tag_fit(out, "SM_Roof_Umbrella_Folded", "D", "folded umbrella", "umbrella_folded")
    tag_fit(out, "SM_Roof_PlanterBox", "D", "planter box", "planter_box")
    P(out, "SM_Roof_Loftlark_Neon_4m", "D", "THE LOFTLARK neon (unlit, on D's east parapet coping, faces the square)", -8.0, R1 + 1.1 + 0.4, 0.4, 90.0, chosen=True,
      neon="THE LOFTLARK")
    # E's dunnage platform and the roof boxes
    e0 = boxes(part="E.dunnage.deck")[0]
    x0, x1, y0, y1, z0, z1 = rect(e0)
    P(out, "SM_Roof_DunnageDeck_6x6", "E", "E's steel dunnage platform (D2's landing; 0.6 m, a 0.3 m step east and south)", (x0 + x1) / 2, y0, (z0 + z1) / 2, 0.0,
      fit={"colliders": [c["index"] for c in boxes("deck") if c.get("part", "").startswith("E.dunnage")], "mode": "part"})
    for c in boxes("duct_box"):
        fitted(out, "SM_Roof_DuctBox_1p6", roof_group(c), "duct plenum", c, CORE3["SM_Roof_DuctBox_1p6"])
    for c in boxes("vent_box"):
        fitted(out, "SM_Roof_VentBox_1x1", roof_group(c), "louvred vent housing", c, CORE3["SM_Roof_VentBox_1x1"])
    for c in boxes("conduit_box"):
        fitted(out, "SM_Roof_ConduitBox_1p4", roof_group(c), "junction cabinet", c, CORE3["SM_Roof_ConduitBox_1p4"], prefer=0.0)
    for c in boxes("conduit_run"):
        fitted(out, "SM_Roof_ConduitRun_4m", roof_group(c), "conduit run", c, CORE3["SM_Roof_ConduitRun_4m"])
    for c in boxes("pipe_sleepers"):
        fitted(out, "SM_Roof_PipeSleepers_1p6", roof_group(c), "pipe sleepers", c, CORE3["SM_Roof_PipeSleepers_1p6"])
    for c in boxes("fan_housing"):
        fitted(out, "SM_Roof_FanHousing_1p6", "E", "roof exhaust fan (on the dunnage deck)", c, CORE3["SM_Roof_FanHousing_1p6"])
    # the plaza's small dressing
    for c in boxes("bollard_planter"):
        fitted(out, "SM_Sq_BollardPlanter", "plaza", "bollard planter", c, CORE3["SM_Sq_BollardPlanter"])
    for c, f in zip(boxes("newsstand"), (270.0, 270.0, 90.0)):
        fitted(out, "SM_Sq_Newsstand", "street", "newsstand (the sales window toward the street)", c, CORE3["SM_Sq_Newsstand"], prefer=f, chosen_facing=True, face="Label_Newsstand")
    for c in boxes("phone_kiosk"):
        fitted(out, "SM_Sq_PhoneKiosk", "street", "phone and charging kiosk", c, CORE3["SM_Sq_PhoneKiosk"], prefer=90.0, chosen_facing=True, face="Label_PhoneKiosk")
    for c in boxes("wayfinding_pylon"):
        fitted(out, "SM_Sq_WayfindingPylon", "plaza", "wayfinding pylon", c, CORE3["SM_Sq_WayfindingPylon"], face="Pylon_Streets")
    for c in boxes("atm_kiosk"):
        fitted(out, "SM_Sq_ATM_Kiosk", "street", "cash machine (the closed bank lobby)", c, CORE3["SM_Sq_ATM_Kiosk"], chosen_facing=True, face="Label_ATM")
    for c, f in zip(boxes("standpipe"), (90.0, 270.0)):
        fitted(out, "SM_Sq_Standpipe", "street", "siamese standpipe (back to the facade)", c, CORE3["SM_Sq_Standpipe"], mode="centre", prefer=f, chosen_facing=True)
    for c in boxes("valet_stand"):
        fitted(out, "SM_Sq_ValetStand", "street", "hotel valet stand", c, CORE3["SM_Sq_ValetStand"], face="Label_Valet")
    for c in boxes("luggage_cart"):
        fitted(out, "SM_Sq_LuggageCart", "street", "luggage cart", c, CORE3["SM_Sq_LuggageCart"])
    for c in boxes("crate_stack"):
        fitted(out, "SM_Sq_Crates_Stack", "street", "stacked crates", c, CORE3["SM_Sq_Crates_Stack"])
    for c in boxes("hoarding"):
        fitted(out, "SM_Sq_Hoarding_6m", "street", "hoarding (the closed shop being fitted out)", c, CORE3["SM_Sq_Hoarding_6m"])
    for c in boxes("hydrant"):
        fitted(out, "SM_Prop_CT_Hydrant", "street", "hydrant (reused, the Canal kit's light one)", c, (0.32, 0.43, 0.84), mode="centre", reused="canal",
               chosen_facing=True)
    for c in boxes("sign_pole"):
        fitted(out, "SM_Street_SignPost", "street", "sign pole (reused, gaps)", c, (0.60, 0.06, 2.80), mode="centre", reused="gaps")
    for c in boxes("newspaper_box"):
        fitted(out, "SM_Furn_NewspaperBox", "street", "newspaper box (reused, furniture)", c, (0.48, 0.46, 1.08), mode="centre", reused="furniture")
    for c, m in zip(boxes("trash_bags"), ("SM_Furn_TrashBags_A", "SM_Furn_TrashBags_B", "SM_Furn_TrashBags_A")):
        fitted(out, m, "street", "trash bags (reused, furniture)", c, (1.28, 0.97, 0.63), mode="centre", reused="furniture")
    for c in boxes("bus_shelter"):
        fitted(out, "SM_Furn_BusShelter", "street", "bus shelter (reused, gaps; stretched to its box)", c, (3.62, 1.52, 2.48), prefer=90.0, reused="gaps",
               chosen_facing=True)
    # what the crowd left (midtown.md 12.4): fan signs on the plaza and the roadways (flat, under the 0.5 m clutter rule: no collider).
    # SM_Sq_Sawhorse is built but not placed: a 1.0 m sawhorse needs a collider from lane D.
    for i, (x, y, z, r) in enumerate(((9.6, SW, -17.4, 20.0), (14.2, SW, -6.6, 200.0), (17.9, SW, 2.2, 80.0), (12.7, SW, 10.4, 310.0),
                                      (19.3, SW, 16.9, 140.0), (4.8, 0.0, -2.2, 250.0), (-1.2, 0.0, 14.5, 30.0), (26.4, 0.0, 10.6, 170.0))):
        P(out, "SM_Sq_FanSign", "plaza", "a fan's cardboard sign, dropped (dressing, no collider)", x, y, z, r, chosen=True)
    # the premiere's set
    box_c = boxes("box_truck")
    x0, x1, y0, y1, z0, z1 = [min(rect(c)[i] for c in box_c) if i % 2 == 0 else max(rect(c)[i] for c in box_c) for i in range(6)]
    P(out, "SM_Sq_Truck_Production", "premiere", "the production company's truck (BRIGHTWIRE EVENTS), nose north, the tail lift stowed", (x0 + x1) / 2, y0,
      (z0 + z1) / 2, 90.0, face="Panel_Brightwire", fit={"colliders": [c["index"] for c in box_c], "mode": "part"})
    for i, c in enumerate(boxes("broadcast_van")):
        fitted(out, "SM_Sq_Van_Broadcast_6p8", "premiere", "broadcast van %d" % (i + 1), c, CORE3["SM_Sq_Van_Broadcast_6p8"], prefer=NOSE_SOUTH,
               chosen_facing=True, face="Panel_Broadcast")
    for c in boxes("satellite_truck"):
        fitted(out, "SM_Sq_Truck_Satellite", "premiere", "satellite truck", c, CORE3["SM_Sq_Truck_Satellite"], prefer=NOSE_SOUTH, chosen_facing=True,
               face="Panel_Broadcast")
    for c in boxes("catering_truck"):
        fitted(out, "SM_Sq_Truck_Catering", "premiere", "catering truck", c, CORE3["SM_Sq_Truck_Catering"], prefer=NOSE_SOUTH, chosen_facing=True,
               face="Panel_Catering")
    for c in boxes("generator_truck"):
        fitted(out, "SM_Sq_Truck_Generator", "premiere", "generator truck", c, CORE3["SM_Sq_Truck_Generator"], prefer=NOSE_SOUTH, chosen_facing=True)
    for c in boxes("cable_truck"):
        fitted(out, "SM_Sq_Truck_Cable", "premiere", "cable truck", c, CORE3["SM_Sq_Truck_Cable"], prefer=NOSE_SOUTH, chosen_facing=True)
    for c in boxes("staging_truck"):
        fitted(out, "SM_Sq_Truck_Staging", "premiere", "staging truck", c, CORE3["SM_Sq_Truck_Staging"], prefer=NOSE_SOUTH, chosen_facing=True)
    for c, m in zip(boxes("production_trailer"), ("SM_Sq_Trailer_Production_6m", "SM_Sq_Trailer_Production_6p4")):
        fitted(out, m, "premiere", "site office trailer (hitch south)", c, CORE3[m], prefer=NOSE_SOUTH, chosen_facing=True)
    for c in boxes("screen_trailer"):
        fitted(out, "SM_Sq_ScreenTrailer", "premiere", "mobile screen trailer (parked, dark)", c, CORE3["SM_Sq_ScreenTrailer"], chosen_facing=True, face="Panel_Brightwire")
    for c in boxes("light_tower"):
        fitted(out, "SM_Sq_LightTower", "premiere", "light tower", c, CORE3["SM_Sq_LightTower"], chosen_facing=True, above=ROOF_ABOVE["SM_Sq_LightTower"])
    for c in boxes("truss_tower"):
        fitted(out, "SM_Sq_TrussTower", "premiere", "truss tower", c, CORE3["SM_Sq_TrussTower"], above=ROOF_ABOVE["SM_Sq_TrussTower"])
    for c in boxes("press_wall"):
        fitted(out, "SM_Sq_PressWall_3p4", "premiere", "press wall (faces south)", c, CORE3["SM_Sq_PressWall_3p4"], face="Press_Wall", chosen_facing=True)
    for c in boxes("vip_tent"):
        fitted(out, "SM_Sq_VipTent_3x3", "premiere", "VIP tent", c, CORE3["SM_Sq_VipTent_3x3"], face="Label_VIP", chosen_facing=True)
    for c in boxes("merch_booth"):
        fitted(out, "SM_Sq_MerchBooth", "premiere", "merch booth", c, CORE3["SM_Sq_MerchBooth"], face="Label_Merch", chosen_facing=True)
    for c in boxes("coat_check"):
        fitted(out, "SM_Sq_CoatCheck", "premiere", "coat check", c, CORE3["SM_Sq_CoatCheck"], face="Label_CoatCheck", chosen_facing=True)
    for c in boxes("security_booth"):
        fitted(out, "SM_Sq_SecurityBooth", "premiere", "security booth", c, CORE3["SM_Sq_SecurityBooth"], face="Label_Security", chosen_facing=True)
    for c in boxes("info_booth"):
        fitted(out, "SM_Sq_InfoBooth", "premiere", "information booth", c, CORE3["SM_Sq_InfoBooth"], prefer=90.0, face="Label_Info", chosen_facing=True)
    for c in boxes("photo_booth"):
        fitted(out, "SM_Sq_PhotoBooth", "premiere", "photo booth", c, CORE3["SM_Sq_PhotoBooth"], face="Label_PhotoBooth", chosen_facing=True)
    for c in boxes("portable_toilets"):
        fitted(out, "SM_Sq_PortableToilets", "premiere", "portable toilets", c, CORE3["SM_Sq_PortableToilets"], chosen_facing=True)
    for c in boxes("camera_riser"):
        fitted(out, "SM_Sq_CameraRiser", "premiere", "camera riser", c, CORE3["SM_Sq_CameraRiser"], chosen_facing=True)
    for c in boxes("speaker_stack"):
        fitted(out, "SM_Sq_SpeakerStack", "premiere", "speaker stack", c, CORE3["SM_Sq_SpeakerStack"], chosen_facing=True)
    for c in boxes("sound_tower"):
        fitted(out, "SM_Sq_SoundTower", "premiere", "sound tower", c, CORE3["SM_Sq_SoundTower"])
    for c in boxes("bus"):
        fitted(out, "SM_Vehicle_CityBus", "street", "the stalled city bus (CITY CROSSTOWN), nose south, doors on the kerb (east) side", c, CORE3["SM_Vehicle_CityBus"],
               prefer=NOSE_SOUTH, chosen_facing=True, faces=["Panel_CityCrosstown", "Bus_Side", "Bus_Side"])
    parked_cars(out)


def parked_cars(out):
    """The 14 parked cars: each on its body box, the glass box above it (the cabin) giving the car its height. The avenues run
    southbound, so a car along z points its nose south; W 46 St's row points west."""
    for tag, mesh in PARKED.items():
        glass = [g for g in boxes(tag) if g.get("surface") == "glass"]
        for c in (b for b in boxes(tag) if b.get("surface") == "car"):
            x0, x1, y0, y1, z0, z1 = rect(c)
            top = y1
            for g in glass:
                gx0, gx1, _gy0, gy1, gz0, gz1 = rect(g)
                if gx0 >= x0 - 0.01 and gx1 <= x1 + 0.01 and gz0 >= z0 - 0.01 and gz1 <= z1 + 0.01 and abs(g["web"]["min"]["y"] - y1) < 0.01:
                    top = max(top, gy1)
            merged = dict(c, web={"min": c["web"]["min"], "max": dict(c["web"]["max"], y=top)})
            along_z = (z1 - z0) >= (x1 - x0)
            fitted(out, mesh, "street", "parked %s (body box plus the cabin's glass box)" % tag, merged, CORE3[mesh],
                   prefer=NOSE_SOUTH if along_z else 180.0, chosen_facing=True)


# The facade tables (midtown.md 2.1, 12.4, 14.2): each frontage is a run along a facade collider's outer plane, the modules
# placed in the Block's module frame (bottom-left of the outer face, running +X, the face toward -Y). rot: turn about Blender Z;
# the run goes along the module's +X = (cos rot, -sin rot) in web (x, z). Heights are from y = 0 (the 0.15 sidewalk slab hides
# the module bases): the ground storey 4.70 m, then the storeys of the building tables (3.30 / 3.225 / 3.10 for the west blocks).
GROUND = 4.70
FRONTAGES = [
    dict(id="East (theatre, hotel)", at=(30.0, -38.0), rot=270.0, length=60.0, storeys=(8, 3.1625), top=30.0, cols=dict(part="east.facade"),
         walls=lambda x, z: "Stone" if z < -4.0 else "Buff",
         ground=[("blank", 16.0), ("theatre", 16.0), ("blank", 8.0), ("hotel", 8.0), ("blank", 12.0)]),
    dict(id="South (W 46 St row)", at=(31.0, 36.0), rot=180.0, length=81.0, storeys=(5, 3.06), top=20.0, cols=dict(part="w46.south.facade"),
         walls=lambda x, z: "Buff" if x > -10.0 else "Stone",
         ground=[("blank", 9.0), ("Chop", 8.0), ("blank", 8.0), ("Pharmacy", 7.0), ("blank", 49.0)]),
    dict(id="West C (Seventh Av, Corvin Hall)", at=(-8.0, -4.0), rot=90.0, length=34.0, storeys=(4, 3.225), top=17.6, cols=dict(tag="C"),
         walls=lambda x, z: "Red", ground=[("blank", 2.0), ("Souvenir", 8.0), ("blank", 6.0), ("Slice", 6.0), ("blank", 12.0)]),
    dict(id="West D (Seventh Av, the gantry side)", at=(-8.0, 22.0), rot=90.0, length=26.0, storeys=(3, 3.10), top=14.0, cols=dict(tag="D"),
         walls=lambda x, z: "Red", ground=[("Bank", 8.0), ("blank", 2.0), ("Camera", 10.0), ("blank", 6.0)]),
    dict(id="W 46 St north row, E", at=(-50.0, 22.0), rot=0.0, length=20.0, storeys=(3, 3.10), top=14.0, cols=dict(tag="E"),
         walls=lambda x, z: "Red", ground=[("blank", 20.0)]),
    dict(id="W 46 St north row, D", at=(-28.0, 22.0), rot=0.0, length=20.0, storeys=(3, 3.10), top=14.0, cols=dict(tag="D"),
         walls=lambda x, z: "Red", ground=[("blank", 20.0)]),
]
SHOP_MESH = {"Souvenir": ("SM_Facade_MT_Shop_Souvenir", 8, "Band_SeventhAvSouvenirs"), "Slice": ("SM_Facade_MT_Shop_Slice", 6, "Band_SliceOfSeventh"),
             "Camera": ("SM_Facade_MT_Shop_Camera", 10, "Band_Shutterbox"), "Bank": ("SM_Facade_MT_Shop_Bank", 8, "Band_Bellhaven"),
             "Chop": ("SM_Facade_MT_Shop_Chop", 8, "Band_BranniganChopHouse"), "Pharmacy": ("SM_Facade_MT_Shop_Pharmacy", 7, "Band_AshbyCross")}


def run_pos(f, s):
    """Web (x, z) of the point s metres along a frontage's run."""
    r = math.radians(f["rot"])
    return f["at"][0] + s * math.cos(r), f["at"][1] - s * math.sin(r)


def facades(out):
    """The facade tables as placements: the ground storey (shopfronts under their bands, blank bases, the east podium's theatre and
    hotel fronts with the marquee and the canopy), the storeys of bays at the buildings' storey heights, and the cornice at the
    roof line (the west blocks' parapets are the roofs' own art)."""
    for f in FRONTAGES:
        rot = f["rot"]
        cols = [c["index"] for c in (boxes(**f["cols"]))]
        fit = {"colliders": cols, "mode": "part", "frontage": f["id"]}
        n_up, sh = f["storeys"]
        group = f["id"].split(" (")[0]
        s = 0.0
        for kind, ln in f["ground"]:
            if kind == "blank":
                n = max(1, int(round(ln / 3.1)))
                for i in range(n):
                    wx, wz = run_pos(f, s + i * ln / n)
                    P(out, "SM_Facade_MT_Ground_Blank_3p1", group, "ground base", wx, 0.0, wz, rot, scale=(round(ln / n / 3.1, 4), 1.0, 1.0), fit=fit)
            elif kind in SHOP_MESH:
                mesh, w, face = SHOP_MESH[kind]
                wx, wz = run_pos(f, s)
                P(out, mesh, group, "shopfront (%s)" % kind, wx, 0.0, wz, rot, fit=fit)
                P(out, "SM_Sign_MT_Band_%dm" % w, group, "storefront band (%s)" % kind, wx, 3.6, wz, rot, face=face, fit=fit)
            else:
                mesh = "SM_Facade_MT_TheatreFront_8m" if kind == "theatre" else "SM_Facade_MT_HotelFront_8m"
                for i in range(int(ln // 8)):
                    wx, wz = run_pos(f, s + i * 8.0)
                    P(out, mesh, group, "%s front" % kind, wx, 0.0, wz, rot, fit=fit)
                if kind == "theatre":
                    wx, wz = run_pos(f, s + 4.0)                                            # centred on the doors at z -14
                    P(out, "SM_Facade_Marquee_A", group, "THE MERIDALE THEATRE marquee (over the doors, 3.6 up)", wx, 3.6, wz, rot, fit=fit,
                      faces=["Band_MeridaleTheatre", "Marquee_Lamplight"])
                else:
                    wx, wz = run_pos(f, s + 1.0)                                            # centred on the doors at z 6
                    P(out, "SM_Facade_Marquee_B", group, "HOTEL CASTELLANE canopy (over the doors, 3.0 up)", wx, 3.0, wz, rot, fit=fit,
                      faces=["Band_HotelCastellane"])
            s += ln
        nb = max(1, int(round(f["length"] / 3.1)))
        bw = f["length"] / nb
        for i in range(nb):
            wx, wz = run_pos(f, i * bw)
            cx, cz = run_pos(f, (i + 0.5) * bw)
            wall = f["walls"](cx, cz)
            for k in range(n_up):
                P(out, "SM_Facade_MT_Bay_%s_3p1" % wall, group, "bay, storey %d" % (k + 1), wx, GROUND + k * sh, wz, rot,
                  scale=(round(bw / 3.1, 4), 1.0, round(sh / 3.3, 4)), fit=fit)
            P(out, "SM_Facade_MT_Cornice_3p1", group, "cornice", wx, f["top"] - 0.55, wz, rot, scale=(round(bw / 3.1, 4), 1.0, 1.0), fit=fit)


def build_all():
    out = []
    decks(out)
    parapets(out)
    roof_items(out)
    gantry(out)
    scaffold(out)
    screens(out)
    square(out)
    dressing(out)
    facades(out)
    return out


def fit_summary(out):
    """What the placements take from the level data (round 2): instances on a collider, the lane's own choices, the
    colliders of the dressed tags left without art."""
    fittedn = sum(1 for e in out if e.get("fit"))
    chosen = sorted({e["role"].split(" %")[0] for e in out if e.get("chosen")})
    dressed = {i for e in out if e.get("fit") for i in e["fit"]["colliders"]}
    tags = ["stand", "stand-guard", "booth", "booth-slot", "booth_desk", "booth_rack", "monitor_cart", "cable_drum", "planter_granite",
            "kiosk_souvenir", "food_cart", "cafe_table", "cafe_chairs", "light_pole", "street_lamp", "cable_ramp", "generator",
            "road_cases", "jersey_barrier", "water_barrier", "bike_barrier", "bench", "trash_can", "water-tower", "hvac_rtu", "skylight",
            "chimney_stack", "roof_vent", "tar_kettle", "satellite_dish", "antenna_mast", "tank-house", "machine-room",
            # round 3
            "lounge_bar", "lounger", "lounger_stack", "umbrella_folded", "planter_box", "duct_box", "vent_box", "conduit_box", "conduit_run",
            "pipe_sleepers", "fan_housing", "deck", "bollard_planter", "newsstand", "phone_kiosk", "wayfinding_pylon", "atm_kiosk", "standpipe",
            "valet_stand", "luggage_cart", "crate_stack", "hoarding", "hydrant", "sign_pole", "newspaper_box", "trash_bags", "bus_shelter",
            "box_truck", "broadcast_van", "satellite_truck", "catering_truck", "generator_truck", "cable_truck", "staging_truck",
            "production_trailer", "screen_trailer", "light_tower", "truss_tower", "press_wall", "vip_tent", "merch_booth", "coat_check",
            "security_booth", "info_booth", "photo_booth", "portable_toilets", "camera_riser", "speaker_stack", "sound_tower", "bus", "facade"]
    left = sorted(c["index"] for c in data()["colliders"]["boxes"] if c["tag"] in tags and c["index"] not in dressed)
    return {"source": "tools/levels/data/level_midtown.json", "fitted_instances": fittedn, "chosen_instances": sum(1 for e in out if e.get("chosen")),
            "chosen_roles": chosen, "dressed_tags": tags, "colliders_dressed": len(dressed), "colliders_of_dressed_tags_left": left,
            "reused_meshes": REUSED, "not_dressed": ["ipx_truck (the existing SM_Vehicle_IPXTruck arrives after the last reel)", "cabinet (G1.cabinet, part of the gantry mesh)"]}


def write_placements(path):
    out = build_all()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    meshes = sorted({e["mesh"] for e in out})
    doc = {"about": "Midtown (Level 3) roofs, gantry, scaffold and screens assembled from the midtown kit (assets/_midtown_place.py). "
                    "Each entry: mesh, group, role, web (x, y, z), blender_m, rot_z_deg, location_cm (Unreal), yaw, optional scale "
                    "(x, y, z), face (Sign_MT_Atlas1 cell) or screen (+ tile, tiles, first_slide). 'chosen': a position the design "
                    "leaves open, chosen by the art lane.",
           "count": len(out), "meshes": meshes, "levels": {"R1": R1, "R2": R2, "R3": R3, "scaffold": SCAF_LEVELS},
           "fit": fit_summary(out), "instances": out}
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    return len(out)


if __name__ == "__main__":
    from mi import paths
    n = write_placements(os.path.join(paths.out, "placements", "placements_midtown.json"))
    print("%d placements" % n)
