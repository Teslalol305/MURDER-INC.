"""Canal Street structures fitted to lane D's colliders (MAPS.md lane A-CT round 2; chinatown.md 13.2, 13.4: "every structure
that the player stands on or fights around is fitted to its colliders with structures.py's measure-every-vertex step").

Every mesh here is built in the level's own frame from tools/levels/data/level_chinatown.json (web metres (x, y, z) are
Blender (x, -z, y)) and measured the way assets/structures.py measures the Block's: every vertex must lie inside or within
TOL of the union of its collider boxes, or inside an allowed region named here (overhead art, gate hoods, door leaves
folded against a wall, coping). The report is written to art/out/chinatown/fit_chinatown.json and checked by
_chinatown_check.py (fit). The pivot of each mesh is the Blender min corner of its colliders' union (pure arithmetic:
struct_places() gives the same numbers without Blender, for the placements).

    SM_Struct_CT_MarketHall        GOLDEN TIDE MARKET's shell (walls with the three Canal gates, the side door and the rear
                                   roll-up, roof slab, parapets with coping, the corrugated Canal fascia, steel beams,
                                   fluorescent rows, the green EXIT box) and B0, the storeroom behind it
    SM_Struct_CT_ColdRoom          insulated panel room with its strip curtain parted at the 2.0 m door, evaporator on the lid
    SM_Struct_CT_RoofBulkhead_B0   the roof Goons' door: brick stair house, steel door on its east face, caged lamp, vent
    SM_Struct_CT_YardStair         the climbable switchback: diamond-plate treads on the 26 step boxes, stringers, landings,
                                   48 mm rails inside the playerOnly guards, the solid space under it closed with sheeting
    SM_Struct_CT_SidewalkShed_Mott the bakery's Mott shed: plywood deck and parapet with the missing panel, pipe posts in their
                                   boxes, joists and lamps under the deck
    SM_Struct_CT_BakeryKitchen     MOON GATE BAKERY's one-storey rear: walls with the Mott and alley doors, the walkable roof,
                                   its parapets (the Mott gap of drop R1), the 0.30 m curb to the market roof
    SM_Struct_CT_Arcade            PLUM BLOSSOM ARCADE's soffit at 4.2 m with its lights, the frieze over the kiosks, the
                                   terrazzo, the kiosk pillar
    SM_Struct_CT_BanquetFacade     E2's stucco fronts on the Square and Mott: the banquet doors (red lacquer surround, gold
                                   lattice leaves folded inside), the dub room's raised roll-up, two rows of upper windows,
                                   the gold trim cornice and the parapet
"""
import json
import math
import os

import numpy as np

from assets import facade as fc
from assets import _chinatown_kit as kit
from assets._chinatown_kit import bar, bx, rod
from mi import scene

from assets._chinatown_level import (LEVEL, ROOT, STRUCTS, W, boxes, cbox, level, parts, prop_colliders,  # noqa: F401
                                     struct_pivot, struct_places)

TOL = 0.015                                         # fit tolerance (paint, tile skins, plates laid on a collider face)
X, Y, Z = np.eye(3)


# ================================================================================================= fitting

def inside(P, bxs, tol=TOL):
    ok = np.zeros(len(P), bool)
    for lo, hi in bxs:
        ok |= np.all((P >= np.asarray(lo) - tol) & (P <= np.asarray(hi) + tol), axis=1)
    return ok


def fit_report(co, cols, allow):
    bxs = [cbox(i) for i in cols]
    ok = inside(co, bxs)
    regs = [r for _n, r in allow]
    ok2 = ok | inside(co, regs, tol=0.0)
    bad = ~ok2
    rep = {"vertices": int(len(co)), "outside_colliders": int((~ok).sum()), "allowed": int((~ok & ok2).sum()),
           "outside_unexplained": int(bad.sum()), "allow": [n for n, _r in allow], "colliders": len(cols)}
    if bad.any():
        P = co[bad]
        d = np.full(len(P), 1e9)
        for lo, hi in bxs:
            e = np.maximum(np.maximum(np.asarray(lo) - P, P - np.asarray(hi)), 0)
            d = np.minimum(d, np.linalg.norm(e, axis=1))
        rep["max_outside_m"] = round(float(d.max()), 3)
        k = int(np.argmax(d))
        rep["worst_at_web"] = [round(float(P[k, 0]), 2), round(float(P[k, 2]), 2), round(float(-P[k, 1]), 2)]
    return rep


def done(ctx, b, name, M, notes, allow=(), ground=True, cover=None):
    """Finish (kit materials and wear), measure the fit in the level frame, set the pivot, record the report."""
    ob = kit.done(ctx, b, name, M, ground=ground, collision="none", cover_height=cover,
                  notes=notes + " Fitted to lane D's colliders (tools/levels/data/level_chinatown.json, parts %s); the art "
                                "carries no collision. Pivot = the colliders' min corner, Blender %s; place at that point, "
                                "yaw 0." % (name, tuple(struct_pivot(name))))
    co = np.array([v.co[:] for v in ob.data.vertices])
    rep = fit_report(co, STRUCTS[name](), allow)
    scene.set_pivot(ob, struct_pivot(name))
    ob["mi_placed"] = True
    if not hasattr(ctx, "ct_fit"):
        ctx.ct_fit = {}
    ctx.ct_fit[name] = rep
    ctx.log("  fit %-32s %s" % (name, rep))
    return ob


def wb(b, x0, x1, y0, y1, z0, z1, slot, **kw):
    """A box given in web coordinates."""
    lo, hi = W(x0, x1, y0, y1, z0, z1)
    return bx(b, lo, hi, slot, **kw)


def wcol(b, i, slot, **kw):
    lo, hi = cbox(i)
    return bx(b, lo, hi, slot, **kw)


def wrod(b, p0, p1, r, slot, n=8):
    """A rod between two web points."""
    return rod(b, (p0[0], -p0[2], p0[1]), (p1[0], -p1[2], p1[1]), r, slot, n=n)


def frame(origin_web, outward):
    """4x4 matrix from a local wall frame (run +X, outer face at y = 0 looking -Y, wall behind +Y, z up) to the level:
    origin_web (x, y, z) is the frame's origin, outward one of '+x', '-x', '+z', '-z' (web)."""
    n = {"+x": (1.0, 0.0), "-x": (-1.0, 0.0), "+z": (0.0, -1.0), "-z": (0.0, 1.0)}[outward]
    u = (-n[1], n[0])
    M = np.eye(4)
    M[:3, 0] = (u[0], u[1], 0.0)
    M[:3, 1] = (-n[0], -n[1], 0.0)
    M[:3, 2] = (0.0, 0.0, 1.0)
    M[:3, 3] = (origin_web[0], -origin_web[2], origin_web[1])
    return M


def merge(b, sub, M):
    b.merge(sub, M)


def B(seed, step=1.0):
    return fc.B(seed, step=step)


# ================================================================================================= materials

def materials(ctx, M):
    """The kit's materials plus the structures' surfaces (catalogued scans, tinted; no new tiling set). Slot keys starting
    with a masonry word (brick, stone, conc, tile, roof) get the facade wear rules."""
    S = kit.S
    soot = kit.SOOT
    Mb = fc.materials(ctx)
    Ms = dict(M)
    for k in ("brickRed", "brickBuff", "brickBrown", "brickPainted", "brickCommon"):
        Ms[k] = Mb[k]
    Ms["white"] = Mb["white"]
    Ms["brickBlock"] = S(ctx, "TS_Block_ScanPainted", alpha="splash", dirt_color=soot, macro=0.14,
                         note="the market hall's painted block (a former garage)")
    Ms["corr"] = S(ctx, "TS_Corrugated_ScanWeathered", alpha="splash", dirt_color=soot,
                   note="the market's corrugated Canal fascia, the shut storeroom gate, the sheeting under the yard stair")
    Ms["roofGravel"] = S(ctx, "TS_Roof_ScanGravel", alpha="splash", dirt_color=(0.10, 0.09, 0.08), macro=0.2)
    Ms["concFloor"] = S(ctx, "TS_Floor_ScanPaintWorn", alpha="splash", dirt_color=(0.06, 0.055, 0.05), macro=0.12,
                        note="the market floor, painted concrete worn by carts")
    Ms["stoneStucco"] = S(ctx, "TS_Stucco_ScanPainted", "MI_Stucco_PaintCream", tint=(0.86, 0.78, 0.60), alpha="splash",
                          dirt_color=soot, macro=0.12, note="E2's painted stucco, cream")
    Ms["plate"] = S(ctx, "TS_Plate_ScanDiamond", alpha="splash", dirt_color=soot, note="stair treads and landings")
    Ms["panel"] = S(ctx, "TS_Steel_ScanPaintWhite", "MI_Steel_PanelWhite", tint=(0.86, 0.87, 0.85), alpha="splash",
                    dirt_color=(0.07, 0.065, 0.06), note="cold-room insulated panels")
    Ms["plyGreen"] = S(ctx, "TS_Plywood_ScanLauan", "MI_Plywood_PaintGreen", tint=(0.11, 0.24, 0.15), alpha="splash",
                       dirt_color=soot, note="sidewalk shed plywood, painted green")
    Ms["tileTerrazzo"] = S(ctx, "TS_Tile_ScanChecker", "MI_Tile_Terrazzo", tint=(0.62, 0.58, 0.52), alpha="splash",
                           dirt_color=(0.07, 0.06, 0.05), note="the arcade's floor and pillar base (the design's TS_Terrazzo as a tint)")
    Ms["strip"] = kit.F("MI_PVC_StripCurtain", (0.42, 0.50, 0.48), 0.25, note="PVC strip curtain, opaque in this level (no translucency)")
    Ms["tube"] = kit.F("MI_Lamp_Fluorescent", (0.9, 0.92, 0.95), 0.3, emit=(0.92, 0.96, 1.0), strength=0.0,
                       note="fluorescent tube, 5000 K, lit at night")
    Ms["exitGreen"] = kit.F("MI_Lamp_ExitGreen", (0.05, 0.35, 0.12), 0.4, emit=(0.15, 1.0, 0.35), strength=0.0,
                            note="the plain green exit box over the rear roll-up (no word on it)")
    return Ms


# ================================================================================================= the market hall

def gate_hood(b, x0, x1, y0, z_face, out):
    """A roll gate's coil box on a wall face: x0..x1 (web x), bottom y0, 0.30 high, `out` m in front of the face at
    web z = z_face (out < 0 toward -z)."""
    za, zb = sorted((z_face, z_face + out))
    wb(b, x0, x1, y0, y0 + 0.32, za, zb, "grey", ch=0.006)
    wb(b, x0 + 0.06, x1 - 0.06, y0 - 0.03, y0, za + 0.03, zb - 0.03, "trim")


def market_hall(ctx, M):
    b = B(501, step=1.2)
    col = {boxes()[i]["part"] + "#%d" % i: i for i in STRUCTS["SM_Struct_CT_MarketHall"]()}
    for key, i in col.items():
        part = key.split("#")[0]
        lo, hi = cbox(i)
        if part == "market.wall.party":                      # the market's half of the party wall (the bakery owns the rest)
            hi = hi.copy()
            hi[0] = 0.0
        slot = "brickCommon" if part.startswith("B0.") else "concFloor" if part == "market.roof.slab" else "brickBlock"
        if part.startswith(("market.parapet", "B0.parapet")):
            slot = "brickBlock" if part.startswith("market") else "brickCommon"
        bx(b, lo, hi, slot)
    A = []
    # interior: floor, tile wainscot on the inner faces, beams, light rows, skylight wells, the exit box
    ix0, ix1, iz0, iz1 = -25.6, -0.4, -13.6, 5.6
    wb(b, ix0, ix1, -0.03, 0.0, iz0, iz1, "concFloor")
    A.append(("floor slab under the hall (y -0.03..0)", W(ix0, ix1, -0.04, 0.001, iz0, iz1)))
    for (x0, x1, z0, z1) in ((ix0, ix0 + 0.012, iz0, -2.7), (ix0, ix0 + 0.012, -1.7, iz1), (ix0, -22.0, iz0, iz0 + 0.012),
                             (-18.0, -15.0, iz0, iz0 + 0.012), (-11.0, -8.0, iz0, iz0 + 0.012), (-4.0, ix1, iz0, iz0 + 0.012),
                             (ix0, -7.0, iz1 - 0.012, iz1), (-3.0, ix1, iz1 - 0.012, iz1), (ix1 - 0.012, ix1, iz0, iz1)):
        wb(b, x0, x1, 0.0, 1.20, z0, z1, "tile")
    A.append(("overhead inside the hall, 2.4 m and up (beams, light rows, skylight wells, the exit box, gate coils)",
              W(ix0, ix1, 2.4, 5.4, iz0, iz1)))
    for x in (-23.0, -16.1, -9.3, -2.6):                     # steel beams across the short span, under the slab
        prof = [(-0.09, 0.0), (0.09, 0.0), (0.09, -0.016), (0.007, -0.016), (0.007, -0.384), (0.09, -0.384), (0.09, -0.40),
                (-0.09, -0.40), (-0.09, -0.384), (-0.007, -0.384), (-0.007, -0.016), (-0.09, -0.016)][::-1]     # counter-clockwise
        b.prism(prof, (x, -iz0, 5.40), X, Z, (0.0, -(iz1 - iz0), 0.0), "black", step=2.0, pstep=1.0)
    for x in (-23.7, -18.0, -12.8, -7.6, -2.0):              # fluorescent rows over the aisles, on drop rods
        for z in np.arange(-12.4, 4.6, 2.6):
            wb(b, x - 0.08, x + 0.08, 4.30, 4.40, z - 0.62, z + 0.62, "trim")
            wb(b, x - 0.05, x + 0.05, 4.285, 4.30, z - 0.58, z + 0.58, "tube")
            for dz in (-0.5, 0.5):
                wrod(b, (x, 4.40, z + dz), (x, 5.0, z + dz), 0.006, "black", n=4)
    for p in level()["propPlacements"]["items"]:             # skylight wells: lit panels under each roof skylight
        if p["name"] == "skylight":
            c = cbox(p["colliders"][0])
            x0, x1 = c[0][0] + 0.15, c[1][0] - 0.15
            z0, z1 = -c[1][1] + 0.15, -c[0][1] - 0.15
            wb(b, x0, x1, 5.39, 5.40, z0, z1, "tube")
            for (a0, a1, c0, c1) in ((x0 - 0.06, x0, z0, z1), (x1, x1 + 0.06, z0, z1), (x0, x1, z0 - 0.06, z0), (x0, x1, z1, z1 + 0.06)):
                wb(b, a0, a1, 5.10, 5.40, c0, c1, "grey")
    ex = next((s for s in level()["signage"]["items"] if s["id"] == "m.exit"), None)
    if ex:
        p = ex["web"]["pos"]
        wb(b, p["x"] - 0.25, p["x"] + 0.25, p["y"] - 0.10, p["y"] + 0.10, p["z"] - 0.08, p["z"], "trim")
        wb(b, p["x"] - 0.22, p["x"] + 0.22, p["y"] - 0.08, p["y"] + 0.08, p["z"] - 0.09, p["z"] - 0.08, "exitGreen")
    # the Canal face: gates up (coil boxes, guide rails), the corrugated fascia from over the gates to the coping
    gates = [(-22.0, -18.0), (-15.0, -11.0), (-8.0, -4.0)]
    for x0, x1 in gates:
        gate_hood(b, x0 - 0.1, x1 + 0.1, 3.42, -14.0, -0.30)
        for xa in (x0 - 0.12, x1 + 0.02):
            wb(b, xa, xa + 0.10, 0.0, 3.42, -14.11, -14.0, "trim")
    A.append(("gate rails and coil boxes on the Canal face (0.30 m out)", W(-26.0, 0.0, 0.0, 3.80, -14.32, -14.0)))
    wb(b, -26.0, 0.0, 3.76, 6.80, -14.05, -14.0, "corr")
    A.append(("corrugated fascia and coping on the Canal face", W(-26.05, 0.05, 3.70, 6.86, -14.10, -14.0)))
    for x0, x1 in gates:                                       # the steel lintel angles
        wb(b, x0 - 0.15, x1 + 0.15, 3.40, 3.52, -14.04, -14.0, "black")
    # parapet coping (galvanised cap), tar and gravel on the roof
    for part, (lo, hi) in ((boxes()[i]["part"], cbox(i)) for i in STRUCTS["SM_Struct_CT_MarketHall"]()):
        if part.startswith(("market.parapet", "B0.parapet")):
            bx(b, lo - np.array([0.03, 0.03, 0.0]) + np.array([0, 0, hi[2] - lo[2]]), hi + np.array([0.03, 0.03, 0.03]), "galv")
    A.append(("parapet coping, 30 mm round the parapets", W(-26.05, 0.05, 5.70, 6.86, -14.05, 10.05)))
    wb(b, -25.7, -0.15, 5.70, 5.712, -13.7, 5.7, "roofGravel")
    wb(b, -25.7, -16.3, 5.70, 5.712, 6.0, 9.7, "roofGravel")
    # the side door (1.0 m, player only): a steel leaf folded open against the inner face, the frame on the reveals
    wb(b, -25.62, -25.60, 0.0, 2.10, -1.68 + 0.02, -0.72, "trim")
    for za, zb in ((-2.70, -2.695), (-1.705, -1.70)):                 # frame plates on the reveals
        wb(b, -26.0, -25.6, 0.0, 2.20, za, zb, "black")
    A.append(("the side door's leaf folded against the inner face", W(-25.64, -25.58, 0.0, 2.12, -1.70, -0.70)))
    # the rear roll-up to the yard: coil box inside, rails on the inner face
    wb(b, -7.1, -2.9, 3.40, 3.72, 5.30, 5.60, "grey")
    for xa in (-7.12, -3.0):
        wb(b, xa, xa + 0.12, 0.0, 3.40, 5.50, 5.60, "trim")
    A.append(("the rear roll-up's rails on the inner face", W(-7.13, -2.87, 0.0, 3.41, 5.49, 5.61)))
    # B0, the storeroom: a steel door on alley A and a shut gate on alley B, a caged lamp over the door
    wb(b, -26.01, -26.0, 0.0, 2.20, 7.0, 8.1, "trim")
    wb(b, -24.4, -20.8, 0.0, 2.60, 10.0, 10.01, "corr")
    wb(b, -26.18, -26.0, 2.45, 2.70, 7.4, 7.7, "black")
    A.append(("B0's lamp over the alley door", W(-26.2, -26.0, 2.4, 2.75, 7.35, 7.75)))
    notes = ("GOLDEN TIDE MARKET (chinatown.md 4.3): one tall storey in painted block, clear 5.4 m, the walkable roof at 5.7 "
             "(tar and gravel), Canal parapet 1.1 m, the others 1.0 m with galvanised coping; three 4 m Canal gates rolled up "
             "under a corrugated fascia that carries the band, the blades and the rooftop letters; the 1.0 m side door (leaf "
             "folded inside), the 4 m rear roll-up to the yard; inside: worn painted floor, white tile to 1.2 m, four steel "
             "beams, fluorescent rows over the aisles, lit skylight wells, the green exit box over the rear roll-up; B0 the "
             "storeroom (common brick, shut).")
    return done(ctx, b, "SM_Struct_CT_MarketHall", M, notes, allow=A)


def cold_room(ctx, M):
    b = B(502, step=0.8)
    for i in STRUCTS["SM_Struct_CT_ColdRoom"]():
        wcol(b, i, "panel")
    for x in np.arange(-25.0, -18.6, 1.2):                     # panel joints on the hall face (none across the door)
        if not -21.1 < x < -18.9:
            wb(b, x - 0.02, x + 0.02, 0.0, 3.0, 1.49, 1.50, "stainless")
    wb(b, -21.06, -21.0, 0.0, 2.40, 1.49, 1.76, "stainless")
    wb(b, -19.0, -18.94, 0.0, 2.40, 1.49, 1.76, "stainless")
    wb(b, -21.0, -19.0, 2.36, 2.40, 1.49, 1.76, "stainless")
    xs = list(np.arange(-20.98, -20.42, 0.14)) + list(np.arange(-19.58, -19.02, 0.14))
    for k, x in enumerate(xs):                                  # strips parted to the sides, alternate ones staggered
        z0 = 1.600 + 0.006 * (k % 2)
        wb(b, x, x + 0.16, 0.06, 2.36, z0, z0 + 0.003, "strip")
    A = [("strip curtain parted to both sides of the 2.0 m door", W(-21.0, -19.0, 0.05, 2.40, 1.48, 1.77)),
         ("evaporator and pipe on the lid", W(-25.0, -22.6, 3.2, 3.85, 2.4, 5.0))]
    wb(b, -24.6, -23.2, 3.20, 3.75, 2.8, 4.4, "galv", ch=0.01)
    wrod(b, (-23.2, 3.5, 3.6), (-22.7, 3.5, 3.6), 0.02, "black")
    return done(ctx, b, "SM_Struct_CT_ColdRoom", M, "The market's cold room (Reel 5's room, chinatown.md 4.3): white insulated "
                "panels 0.25 m with stainless joints, a stainless door frame with its PVC strip curtain parted to the sides (the "
                "2.0 m opening stays clear to see through), the evaporator on the lid. The COLD ROOM sign is a placed carrier.",
                allow=A, cover=3.0)


def roof_bulkhead(ctx, M):
    b = B(503, step=0.6)
    (lo, hi), = [cbox(i) for i in STRUCTS["SM_Struct_CT_RoofBulkhead_B0"]()]
    bx(b, lo, hi - np.array([0, 0, 0.06]), "brickCommon")
    bx(b, lo + np.array([0, 0, hi[2] - lo[2] - 0.06]), hi, "roof")
    # the steel door on the east face (web x -22.4, z 7.0..9.0), its frame and the caged lamp over it
    wb(b, -22.4, -22.392, 5.70, 7.80, 7.05, 8.95, "trim")
    wb(b, -22.4, -22.388, 5.70, 7.86, 6.98, 7.05, "black")
    wb(b, -22.4, -22.388, 5.70, 7.86, 8.95, 9.02, "black")
    wb(b, -22.4, -22.388, 7.80, 7.86, 7.05, 8.95, "black")
    wb(b, -22.40, -22.20, 7.95, 8.15, 7.90, 8.10, "black")
    wb(b, -22.22, -22.18, 7.96, 8.14, 7.92, 8.08, "bulb")
    wrod(b, (-24.6, 8.30, 8.6), (-24.6, 8.85, 8.6), 0.05, "galv")
    A = [("caged lamp over the door", W(-22.41, -22.15, 7.9, 8.2, 7.85, 8.15)), ("vent pipe on the roof", W(-24.7, -24.5, 8.3, 8.9, 8.5, 8.7))]
    return done(ctx, b, "SM_Struct_CT_RoofBulkhead_B0", M, "B0's roof bulkhead, the roof Goons' door (chinatown.md 4.4): common "
                "brick stair house 3.0 x 2.8 x 2.6 m on the storeroom roof, tar cap, a 2.0 m steel door with its frame on the east "
                "face, a caged lamp over it, a vent pipe. The stair inside is not modelled (as the Block's shop interiors).",
                allow=A, cover=2.6)


def _stair_line(x, flight):
    """The line through a flight's inner tread corners (web y over x): every point of it lies under the treads."""
    if flight == 1:
        return 0.2192 / 0.26 * (-9.8 - x)
    return 2.85 + 0.2192 / 0.26 * (x + 13.18)


def _flat(b, poly, zc, slot, thick=0.012):
    """A sheet in the web plane z = zc (to zc + thick) from a counter-clockwise polygon of web (x, y)."""
    b.prism(poly, (0.0, -zc, 0.0), X, Z, (0.0, -thick, 0.0), slot, step=1.0, pstep=0.8)


def yard_stair(ctx, M):
    b = B(504, step=0.5)
    cols = {boxes()[i]["part"]: cbox(i) for i in STRUCTS["SM_Struct_CT_YardStair"]()}
    for part, (lo, hi) in cols.items():                       # treads and landings: diamond plate on each box's top
        if part.startswith("stair.flight") or part.startswith("stair.landing"):
            t = hi[2]
            bx(b, (lo[0], lo[1], t - 0.035), (hi[0], hi[1], t), "plate")
            if part.startswith("stair.flight"):                # nosing angle on the riser edge
                f1 = part.startswith("stair.flight1")
                xe = hi[0] if f1 else lo[0]
                bx(b, (xe - 0.03 if f1 else xe, lo[1], t - 0.09), (xe if f1 else xe + 0.03, hi[1], t - 0.035), "black")
            else:
                for (a, c) in ((lo[1], lo[1] + 0.05), (hi[1] - 0.05, hi[1])):
                    bx(b, (lo[0], a, t - 0.22), (hi[0], c, t - 0.035), "black")
    # stringers: 20 mm channel plates 0.30 deep under the line of the inner tread corners, both sides of each flight
    k = 0.2192 / 0.26
    for zz in (7.22, 8.16):                                    # flight 1 runs down to the yard at x -9.8
        top = lambda x: _stair_line(x, 1) - 0.04
        xf, xg = -9.8 - 0.04 / k, -9.8 - 0.34 / k
        _flat(b, [(-13.18, top(-13.18) - 0.30), (xg, 0.0), (xf, 0.0), (-13.18, top(-13.18))], zz, "black", 0.02)
    for zz in (6.02, 7.16):
        top = lambda x: _stair_line(x, 2) - 0.04
        _flat(b, [(-13.18, top(-13.18) - 0.30), (-9.8, top(-9.8) - 0.30), (-9.8, top(-9.8)), (-13.18, top(-13.18))], zz, "black", 0.02)
    # posts under the mid landing; brackets of flight 2 into the market's south wall
    for x, z in ((-14.52, 6.08), (-14.52, 8.12), (-13.26, 8.12), (-13.26, 6.08)):
        wrod(b, (x, 0.0, z), (x, 2.82, z), 0.05, "black")
        wb(b, x - 0.07, x + 0.07, 0.0, 0.012, z - 0.06, z + 0.06, "black")
    for x in np.arange(-12.8, -9.8, 1.2):
        y = _stair_line(x, 2) - 0.30
        wb(b, x - 0.05, x + 0.05, y - 0.25, y, 5.80, 6.04, "black")
    # rails, inside the playerOnly guards: south (flight 1 and the mid landing), west of the landing, between, the head
    def rail(pts, zc, posts):
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            for h in (1.0, 0.5):
                wrod(b, (x0, y0 + h, zc), (x1, y1 + h, zc), 0.024, "black")
        for x, y in posts:
            wrod(b, (x, y, zc), (x, y + 1.0, zc), 0.024, "black")
    rail([(-9.8, 0.22), (-13.18, 2.85), (-14.55, 2.85)], 8.25, [(-9.85, 0.22), (-11.0, 1.20), (-12.2, 2.19), (-13.18, 2.85), (-14.55, 2.85)])
    for h in (1.0, 0.5):
        wrod(b, (-14.65, 2.85 + h, 6.05), (-14.65, 2.85 + h, 8.25), 0.024, "black")
    wrod(b, (-14.65, 2.85, 6.05), (-14.65, 3.85, 6.05), 0.024, "black")
    s2 = [(-13.18, 2.85), (-9.8, 5.7), (-8.6, 5.7)]
    rail(s2, 7.20, [(-13.1, 2.85), (-11.9, 3.90), (-10.7, 4.94), (-9.8, 5.70), (-8.65, 5.70)])
    for h in (1.0, 0.5):
        wrod(b, (-8.55, 5.7 + h, 6.05), (-8.55, 5.7 + h, 7.2), 0.024, "black")
    wrod(b, (-8.55, 5.7, 6.05), (-8.55, 6.7, 6.05), 0.024, "black")
    for (x0, y0), (x1, y1) in zip(s2[:-1], s2[1:]):          # the wall rail on flight 2's north side
        wrod(b, (x0, y0 + 0.9, 6.07), (x1, y1 + 0.9, 6.07), 0.024, "black")
    # the solid space under the stair closed with corrugated sheeting (its colliders run to the ground)
    _flat(b, [(-13.18, 0.0), (-9.8 - 0.36 / k, 0.0), (-13.18, _stair_line(-13.18, 1) - 0.36)], 8.188, "corr")
    _flat(b, [(-14.6, 0.0), (-13.18, 0.0), (-13.18, 2.62), (-14.6, 2.62)], 8.188, "corr")
    b.prism([(-8.18, 0.0), (-6.0, 0.0), (-6.0, 2.62), (-8.18, 2.62)], (-14.59, 0.0, 0.0), Y, Z, (-0.012, 0.0, 0.0), "corr",
            step=1.0, pstep=0.8)
    lo_line = [(x, max(_stair_line(x, 1) - 0.36, 0.0)) for x in np.linspace(-13.18, -10.24, 4)]
    hi_line = [(x, _stair_line(x, 2) - 0.36) for x in np.linspace(-9.8, -13.18, 5)][:-1]
    _flat(b, lo_line + [(-8.62, 0.0), (-8.62, 5.40), (-9.8, 5.40)] + hi_line[1:], 7.188, "corr")
    b.prism([(-7.18, 0.0), (-6.0, 0.0), (-6.0, 5.40), (-7.18, 5.40)], (-8.612, 0.0, 0.0), Y, Z, (0.012, 0.0, 0.0), "corr",
            step=1.0, pstep=0.8)
    A = [("flight 2's brackets into the market's south wall", W(-13.2, -9.6, 2.0, 5.7, 5.6, 6.02)),
         ("the wall handrail on flight 2 (7 cm off the wall)", W(-13.2, -8.6, 3.0, 6.7, 6.0, 6.1))]
    return done(ctx, b, "SM_Struct_CT_YardStair", M, "The yard stair (chinatown.md 4.4), the level's one climbable fire escape: "
                "two flights of 13 risers of 0.219 on diamond-plate treads with nosing angles, 20 mm stringers under the line of "
                "the inner tread corners, the mid landing on four 100 mm posts, flight 2 bracketed into the market's south wall, "
                "48 mm rails at 0.5 and 1.0 m inside the playerOnly guards (no thin steel, 13.4), and the space under it (solid "
                "in the colliders) closed with corrugated sheeting, so nothing reads as walkable that is not.", allow=A,
                ground=True)


def mott_shed(ctx, M):
    b = B(505, step=0.8)
    cols = {boxes()[i]["part"] + "#%d" % i: cbox(i) for i in STRUCTS["SM_Struct_CT_SidewalkShed_Mott"]()}
    A = [("joists, beams and lamps under the deck", W(8.0, 10.0, 2.50, 2.80, -3.0, 10.0)),
         ("the parapet's top rail", W(9.86, 10.04, 3.95, 4.06, -3.0, 10.0))]
    for key, (lo, hi) in cols.items():
        part = key.split("#")[0]
        if part == "mottshed.deck":
            bx(b, lo, hi, "plyGreen")
            for zz in np.arange(-2.7, 10.0, 0.61):                     # joists across, a beam along the posts
                wb(b, 8.0, 9.95, 2.555, 2.80, zz - 0.025, zz + 0.025, "timber")
            wb(b, 9.72, 9.88, 2.50, 2.80, -3.0, 10.0, "black")
            for zz in (-1.5, 1.5, 4.5, 7.5):
                wb(b, 8.95, 9.15, 2.72, 2.80, zz - 0.1, zz + 0.1, "black")
                wb(b, 9.0, 9.1, 2.70, 2.72, zz - 0.06, zz + 0.06, "bulb")
        elif part == "mottshed.parapet":
            bx(b, lo, hi, "plyGreen")
            wb(b, 9.86, 10.04, 3.95, 4.05, -hi[1], -lo[1], "timber")
        elif part == "mottshed.post":
            cx, cz = (lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2
            wrod(b, (cx, 0.15, cz), (cx, 2.50, cz), 0.05, "black", n=8)
            wb(b, cx - 0.09, cx + 0.09, 0.15, 0.165, cz - 0.09, cz + 0.09, "black")
            wb(b, cx - 0.09, cx + 0.09, 2.49, 2.50, cz - 0.09, cz + 0.09, "black")
    wb(b, 7.88, 8.0, 2.40, 2.80, -3.0, 10.0, "timber")                       # the ledger on the bakery wall
    A.append(("the ledger on the bakery's Mott wall", W(7.86, 8.0, 2.38, 2.80, -3.0, 10.0)))
    return done(ctx, b, "SM_Struct_CT_SidewalkShed_Mott", M, "The bakery's Mott sidewalk shed (chinatown.md 4.6): green-painted "
                "plywood deck (top 3.0 m, the landing of drop R1) on 2x10 joists and a steel beam over five 100 mm pipe posts on "
                "the kerb line, a ledger on the bakery wall, the 1.0 m plywood parapet with the missing panel at z 2..5 (drop R2) "
                "and its broken edges, four lamps under the deck.", allow=A)


def bakery_kitchen(ctx, M):
    b = B(506, step=0.8)
    cols = {boxes()[i]["part"] + "#%d" % i: cbox(i) for i in STRUCTS["SM_Struct_CT_BakeryKitchen"]()}
    A = [("doors folded open against the inner faces", W(4.0, 7.62, 0.15, 2.45, 2.0, 9.62)),
         ("parapet coping", W(-0.05, 8.05, 5.70, 6.76, -3.05, 10.05)),
         ("exhaust hood over the alley door", W(3.6, 6.4, 2.7, 3.4, 10.0, 10.45)),
         ("lintel angles and the tiled inner faces", W(0.38, 7.62, 0.15, 5.42, -3.0, 9.62))]
    for key, (lo, hi) in cols.items():
        part = key.split("#")[0]
        if part == "bakery.floor":
            bx(b, (0.4, -9.6, 0.135), (7.6, 3.0, 0.15), "tile")
            continue
        if ".guard" in part:
            continue
        slot = "brickBuff"
        if part == "kitchen.roof.slab":
            slot = "conc"
        elif part == "kitchen.curb":
            slot = "stone"
        bx(b, lo, hi, slot)
        if part.startswith("kitchen.parapet"):
            bx(b, lo - np.array([0.03, 0.03, 0.0]) + np.array([0, 0, hi[2] - lo[2]]), hi + np.array([0.03, 0.03, 0.03]), "galv")
    wb(b, 0.0, 8.0, 5.70, 5.712, -3.0, 10.0, "roof")
    for (x0, x1, z0, z1) in ((7.588, 7.6, -3.0, 2.0), (7.588, 7.6, 4.0, 9.6), (0.4, 4.0, 9.588, 9.6), (6.0, 7.6, 9.588, 9.6),
                             (0.4, 0.412, 6.0, 9.6)):
        wb(b, x0, x1, 0.15, 1.8, z0, z1, "tile")
    wb(b, 7.59, 7.60, 0.15, 2.40, 4.02, 5.0, "trim")                       # Mott door leaf folded in
    wb(b, 6.0, 7.0, 0.15, 2.40, 9.59, 9.60, "trim")                        # alley door leaf folded in
    for (x0, x1, z0, z1) in ((7.6, 8.0, 2.0, 4.0), (4.0, 6.0, 9.6, 10.0)):  # steel lintel plates under the lintels
        wb(b, x0, x1, 2.59, 2.61, z0, z1, "black")
    wb(b, 4.1, 5.9, 2.85, 3.25, 10.0, 10.40, "galv", ch=0.01)
    return done(ctx, b, "SM_Struct_CT_BakeryKitchen", M, "MOON GATE BAKERY's one-storey rear (chinatown.md 4.5): buff brick walls "
                "with the 2 m Mott and alley doors (leaves folded inside), white tile inside to 1.8 m, the walkable roof at 5.7 "
                "(tar), its 1.0 m parapets with galvanised coping and the broken 3 m Mott section of drop R1, the 0.30 m curb to "
                "the market roof, an exhaust hood over the alley door.", allow=A)


def arcade(ctx, M):
    b = B(507, step=1.0)
    A = [("frieze and light boxes under the soffit", W(29.4, 33.6, 3.60, 4.20, -14.0, 2.0))]
    wb(b, 29.4, 33.6, 4.20, 4.24, -14.0, 2.0, "stone")                     # soffit (painted concrete)
    for (x0, x1) in ((29.4, 29.7), (33.3, 33.6)):                          # frieze over the kiosks, 3.8..4.2
        wb(b, x0, x1, 3.80, 4.20, -14.0, 2.0, "trim")
    for z in np.arange(-12.6, 1.0, 2.4):                                   # two rows of fluorescent boxes
        for x in (30.6, 32.4):
            wb(b, x - 0.10, x + 0.10, 4.08, 4.20, z - 0.62, z + 0.62, "trim")
            wb(b, x - 0.07, x + 0.07, 4.07, 4.08, z - 0.58, z + 0.58, "tube")
    wb(b, 29.4, 33.6, 0.135, 0.15, -14.0, 2.0, "tileTerrazzo")
    for i in prop_colliders("arcade_pillar"):
        lo, hi = cbox(i)
        bx(b, lo + np.array([0.0, 0.0, 0.0]), (hi[0], hi[1], lo[2] + 0.30), "tileTerrazzo")
        bx(b, lo + np.array([0.03, 0.03, 0.30]), hi - np.array([0.03, 0.03, 0.0]), "redlac")
    return done(ctx, b, "SM_Struct_CT_Arcade", M, "PLUM BLOSSOM ARCADE's covered passage (chinatown.md 4.7): painted soffit at "
                "4.2 m with two rows of fluorescent boxes, a steel frieze over the kiosk fronts on both sides, terrazzo on the "
                "floor, the kiosk pillar in red lacquer on a terrazzo base. The kiosks are Canal shop fronts placed on the side "
                "walls; the arch signs are carriers.", allow=A)


def banquet_facade(ctx, M):
    """E2's Square and Mott fronts, built in each face's wall frame and merged into the level frame."""
    b = B(508, step=1.0)
    A = [("Square face: sills, trim bands and the cornice, 0.16 m proud above 2.4 m", W(17.84, 44.0, 2.4, 10.96, 17.83, 18.0)),
         ("Mott face: sills, trim bands and the cornice", W(17.83, 18.0, 2.4, 10.96, 18.0, 32.0)),
         ("banquet doors folded flat inside the hall", W(28.9, 37.1, 0.15, 3.80, 18.40, 18.52))]
    T = 0.40                                            # the walls' thickness, as their colliders

    def wall(L, H, openings, windows, seed):
        s = B(seed, step=1.0)
        cuts = sorted(openings)
        xs = [0.0]
        for a, c, h in cuts:                            # ground: piers between the openings, a head over each
            fc.bx(s, (xs[-1], 0.0, 0.0), (a, T, 5.0), "stoneStucco", axis="z")
            fc.bx(s, (a, 0.0, h), (c, T, 5.0), "stoneStucco", axis="x")
            xs.append(c)
        fc.bx(s, (xs[-1], 0.0, 0.0), (L, T, 5.0), "stoneStucco", axis="z")
        fc.bx(s, (0.0, -0.012, 0.0), (L, 0.0, 0.45), "stone", axis="x")      # a cast plinth (12 mm proud)
        for zrow in (5.55, 8.05):                       # two upper rows, windows 1.24 x 1.55 at a 3.1 m pitch
            x = 0.0
            wl = sorted(w for w in windows if w is not None)
            prev = 0.0
            for wx in wl:
                x0, x1 = wx - 0.62, wx + 0.62
                fc.bx(s, (prev, 0.0, zrow - 0.55), (x0, T, zrow + 1.95), "stoneStucco", axis="z")
                fc.bx(s, (x0, 0.0, zrow - 0.55), (x1, T, zrow), "stoneStucco", axis="x")
                fc.bx(s, (x0, 0.0, zrow + 1.55), (x1, T, zrow + 1.95), "stoneStucco", axis="x")
                fc.sill(s, x0, x1, zrow)
                fc.sash_window(s, x0, x1, zrow, zrow + 1.55)
                fc.bx(s, (x0, T - 0.012, zrow), (x1, T, zrow + 1.55), "interior", axis="z")
                prev = x1
            fc.bx(s, (prev, 0.0, zrow - 0.55), (L, T, zrow + 1.95), "stoneStucco", axis="z")
        fc.bx(s, (0.0, 0.0, 10.0), (L, T, 10.9), "stoneStucco", axis="x")          # parapet
        fc.bx(s, (0.0, -0.10, 5.0), (L, 0.0, 5.12), "gold", axis="x")              # gold trim bands
        fc.bx(s, (0.0, -0.16, 9.80), (L, 0.0, 10.0), "gold", axis="x")
        fc.bx(s, (0.0, -0.03, 10.9), (L, T, 10.95), "galv", axis="x")
        return s

    # the Square face: plane web z 18, outward -z, from x 44 west; the banquet doors at web x 31..35 (s 9..13), head 3.8
    sq_win = [1.55 + 3.1 * k for k in range(8)]
    s = wall(26.0, 10.9, [(9.0, 13.0, 3.80)], sq_win, 509)
    for (a, c) in ((8.6, 9.0), (13.0, 13.4)):                                      # red lacquer surround, flush
        fc.bx(s, (a, -0.005, 0.0), (c, 0.01, 3.80), "redlac", axis="z")
    fc.bx(s, (8.6, -0.005, 3.80), (13.4, 0.01, 3.95), "redlac", axis="x")
    for (a, c) in ((7.0, 9.0), (13.0, 15.0)):                                       # the leaves folded flat inside
        fc.bx(s, (a, 0.40, 0.15), (c, 0.46, 3.70), "redlac", axis="x")
        for k in range(4):
            fc.bx(s, (a + 0.15 + k * 0.45, 0.46, 1.2), (a + 0.5 + k * 0.45, 0.48, 3.4), "gold", axis="z")
    merge(b, s, frame((44.0, 0.0, 18.0), "-z"))
    # the Mott face: plane web x 18, outward -x, from z 18.3 south; the dub room's roll-up at z 24..27 (s 5.7..8.7), head 3.4
    m = wall(13.7, 10.9, [(5.7, 8.7, 3.40)], [1.55 + 3.1 * k for k in range(4)], 510)
    fc.bx(m, (5.6, -0.30, 3.10), (8.8, 0.0, 3.40), "grey", axis="x")                # the raised roll-up's coil box
    for xa in (5.58, 8.70):
        fc.bx(m, (xa, -0.10, 0.15), (xa + 0.12, 0.0, 3.10), "trim", axis="z")
    merge(b, m, frame((18.0, 0.0, 18.3), "-x"))
    A.append(("the dub room's roll-up hood and rails (0.30 m out)", W(17.68, 18.0, 0.15, 3.45, 23.85, 27.15)))
    return done(ctx, b, "SM_Struct_CT_BanquetFacade", M, "E2, CRANE PAVILION BANQUET HALL and the dub room (chinatown.md 4.9): "
                "cream stucco fronts on the Square and Mott fitted to their walls (ground 0..5.0, uppers to the roof at 10.0, "
                "parapet to 10.9), two rows of sash windows, gold trim bands and cornice, the 4 m banquet doors with a flush red "
                "lacquer surround and their gold-lattice leaves folded flat inside, the dub room's roll-up raised under its hood. "
                "The band, the SILVER WAVE neon and the lantern string are placed separately.", allow=A)


BUILDERS = [market_hall, cold_room, roof_bulkhead, yard_stair, mott_shed, bakery_kitchen, arcade, banquet_facade]


def build_structs(ctx, M):
    Ms = materials(ctx, M)
    ctx.Ms = Ms
    return [f(ctx, Ms) for f in BUILDERS]


def write_fit(ctx, path):
    rep = {"about": "Canal Street structures against lane D's colliders (assets/_chinatown_struct.py): every vertex inside or "
                    "within %.3f m of its colliders' union or inside a named allowed region (overhead, coping, door leaves "
                    "folded against a wall). outside_unexplained must be 0." % TOL,
           "level": os.path.relpath(LEVEL, ROOT), "tolerance_m": TOL, "structures": getattr(ctx, "ct_fit", {}),
           "alcoves": getattr(ctx, "ct_alcove_fit", {})}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(rep, f, indent=1, sort_keys=True)
    return rep
