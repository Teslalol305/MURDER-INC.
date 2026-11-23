"""Level structures that were still collider boxes in Unreal (docs/unreal/PROGRESS.md, spec 05-level 2.5-2.10), built
as the things those boxes stand for and fitted to them: every piece sits inside or flush with its collider boxes in
unreal/MurderInc/Content/Data/level.json, so the tuned cover and openings do not change. What may not fit by nature
(roofs, canopies, lamps and rails overhead, a skylight kerb on an unreachable roof) is listed per asset in `allow`
and measured: done() counts every vertex outside the union of its colliders and its allowed regions.

    SM_Struct_ElMezzanine          fare-control box hung under the tracks (station, collider 65): riveted sheet-steel
                                   walls on angle posts, window band (2nd / 5th east panes and 3rd side panes lit),
                                   enamel name board 188 ST, gooseneck lamps, riveted floor with lap seams.
    SM_Struct_ElBridge_S / _N      covered bridge from the mezzanine to each stair head (66 / 77) with the posts under
                                   the stair head (67, 68 / 78, 79); under the El's footprint the deck is its roof.
    SM_Struct_ElStair              the stair from the sidewalk (70-74 / 81-85, gate 69 / 80): riveted plate stringers,
                                   20 risers of 0.1955, diamond-plate treads with worn nosings, lattice balustrades with
                                   pipe handrails, a corrugated roof on rafters, the trestle, portal posts with green
                                   globes, a scissor gate and its STATION CLOSED plate. Symmetric: placed on both sides.
    SM_Struct_ElPlatformEnd_S / _N the platforms over the bounds (75, 76 / 86, 87): slab on cantilevers and knee braces,
                                   windscreen with six lit panes, canopy on posts, fluorescent tubes, end plate.
    SM_Struct_ElPlatform_10m       the same platform, plain, for the run west of the bounds (x -96 .. -46).
    SM_Struct_Kiosk_News / _Candy  sheet-steel kiosks (559 / 490): shutters, folded counters, fascia, posters, door.
    SM_Struct_ProduceStand         (561) plywood ends, three tiers of slatted crates with heaps of modelled fruit,
                                   canvas canopy on a pipe frame, spring scale, price cards, two bare bulbs.
    SM_Struct_Hoarding_*           plywood hoardings (west closure 467-469, vacant lot 370-371): sheets, nailers,
                                   posts, cap rail, fly-posters, POST NO BILLS, ROAD CLOSED boards. The shed parapet
                                   (534-536) is SM_Furn_SidewalkShed's.
    SM_Struct_DigPen               the orange pen round the utility dig (562-566) and its steam stack (567).
    SM_Struct_LoadingDock          (396-400) concrete platform, steel edge, bumpers, steps, roll shutter, stencil.
    SM_Struct_Garages              (188) eight roll doors under concrete lintels, numbers, caged lamps, coping, roof.
    SM_Struct_ShopFloor / _ShopRoof / _ShopColumn / _ShopMezzanine / _ShopStair / _ShopSafe / _ShopExtractorFan
    (+ _Blades) / _ShopExitSign    the inside of V&R Auto Body (189-237): sealed floor in cast panels with oil, paint
                                   and a drain; ribbed roof deck on purlins and open-web joists with four skylights and
                                   high-bay lamps; columns with yellow sleeves; mezzanine, office and stair.

Placement: art/out/placements/structures.json, the form of buildings.json (Unreal cm, yaw), plus the collider
indices each instance draws. Materials are tiling scan sets with world-scale UVs (mi.steel Builder: 1 UV unit = one
tile) and the Wear mask; painted graphics are Sign_<Key> faces drawn in assets/_structures_art.py.

    build.py build structures --export            (about 2 min; --force redraws the faces)
    build.py build structures --preview --only structures_station,structures_street ...
"""
import json
import math
import os

import bpy
import numpy as np
from mathutils import Matrix

from assets import el as EL
from assets import _structures_art as ART
from assets.facade import bar, rod, sheet
from assets.furniture import B, board, box, card, lathe, pipe
from assets.street import Waves, sstep
from mi import geo, mat, paths, render, scene, steel

FAMILY = {"name": "structures", "description": "El station, kiosks, produce stand, hoardings, dock, garages, chop-shop interior"}

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
LEVEL = os.path.join(ROOT, "unreal", "MurderInc", "Content", "Data", "level.json")
OUT = os.path.join(paths.out if hasattr(paths, "out") else os.path.join(ROOT, "art", "out"), "placements", "structures.json")
X, Y, Z = np.eye(3)
TOL = 0.012                                       # fit tolerance in metres (rivet heads, paint, posters)

# -------------------------------------------------------------------------------------------------- level data
_LV = {}


def level():
    if not _LV:
        with open(LEVEL) as f:
            _LV.update(json.load(f))
    return _LV


def col(i):
    """Collider i in Blender metres: (lo, hi)."""
    w = level()["colliders"]["boxes"][i]["web"]
    a, b_ = w["min"], w["max"]
    return np.array([a["x"], -b_["z"], a["y"]]), np.array([b_["x"], -a["z"], b_["y"]])


def cells(u0, u1, v0, v1, holes):
    """Rectangle minus rectangular holes -> list of (u0, u1, v0, v1), merged along u per row."""
    us = sorted({u0, u1} | {min(max(h[0], u0), u1) for h in holes} | {min(max(h[1], u0), u1) for h in holes})
    vs = sorted({v0, v1} | {min(max(h[2], v0), v1) for h in holes} | {min(max(h[3], v0), v1) for h in holes})
    out = []
    for j in range(len(vs) - 1):
        a, b_ = vs[j], vs[j + 1]
        if b_ - a < 1e-6:
            continue
        run = None
        for i in range(len(us) - 1):
            c, d = us[i], us[i + 1]
            if d - c < 1e-6:
                continue
            mc, mv = (c + d) / 2, (a + b_) / 2
            hole = any(h[0] <= mc <= h[1] and h[2] <= mv <= h[3] for h in holes)
            if hole:
                if run:
                    out.append(run)
                run = None
            elif run and abs(run[1] - c) < 1e-9:
                run = (run[0], d, a, b_)
            else:
                if run:
                    out.append(run)
                run = (c, d, a, b_)
        if run:
            out.append(run)
    return out


def hexlin(h):
    h = h.lstrip("#")
    c = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def tint_to(set_name, hexcol, gain=1.0):
    """Tint that takes a scan's mean albedo to the colour `hexcol` (sRGB)."""
    rec = mat.scan_info(set_name) or {}
    alb = np.array(((rec.get("measured") or {}).get("albedo") or {}).get("linear_rgb") or [0.18, 0.18, 0.18])
    return tuple(float(v) for v in np.round(hexlin(hexcol) / np.maximum(alb, 0.02) * gain, 3))


# ----------------------------------------------------------------------------------------------------- materials

SLOT_META = {}


def lamp(name, base, emit, strength):
    m = mat.flat(name, base, 0.25)
    bs = mat.principled(m)
    bs.inputs["Emission Color"].default_value = (*emit, 1.0)
    bs.inputs["Emission Strength"].default_value = strength
    m["mi_emit"] = list(emit)
    SLOT_META[name] = {"workflow": "flat", "note": "emissive %s at night (x %.1f); the level drives it" % (str(tuple(round(v, 2) for v in emit)), strength)}
    return m


def materials(ctx):
    M = dict(EL.materials(ctx))                 # steel (El green), rail, tie, concrete, tread, white, glow
    sc, ts = ctx.scan_set, ctx.tiling_set
    soot = (0.03, 0.028, 0.026)
    rust = dict(blend="TS_Steel_ScanRust", leak_color=(0.24, 0.10, 0.035), leak_rough=0.1, dirt_color=soot, alpha="splash")

    def tinted(key, set_name, slot, hexcol, gain=1.0, **kw):
        t = tint_to(set_name, hexcol, gain)
        M[key] = sc(set_name, slot=slot, tint=t, **kw)
        SLOT_META[slot] = {"set": set_name, "workflow": "tiling", "tint": list(t), "note": hexcol}

    # station sheet steel #2f4038 (fine-rib panels), roofing #1c2224
    tinted("sheet", "TS_Corrugated_ScanBlue", "MI_Corrugated_StationGreen", "#2f4038", 1.15, blend_start=0.55, **rust)
    tinted("roofing", "TS_Corrugated_ScanWeathered", "MI_Corrugated_Roofing", "#1c2224", 1.1, alpha="splash", dirt_color=soot)
    # furniture's painted slots, same names and parameters
    M["yellow"] = sc("TS_Steel_ScanPaintWhite", slot="MI_Steel_PaintYellow", tint=(2.1, 1.85, 0.075), blend_start=0.5, **rust)
    M["dark"] = sc("TS_Steel_ScanPaintGrey", slot="MI_Steel_IronDark", tint=(0.10, 0.12, 0.22), blend_start=0.5, **rust)
    M["black"] = sc("TS_Steel_ScanPaintGrey", slot="MI_Steel_PaintBlack", tint=(0.07, 0.07, 0.075), blend_start=0.45, **rust)
    SLOT_META.update({"MI_Steel_PaintYellow": {"set": "TS_Steel_ScanPaintWhite", "workflow": "tiling", "tint": [2.1, 1.85, 0.075], "note": "#f2c21a"},
                      "MI_Steel_IronDark": {"set": "TS_Steel_ScanPaintGrey", "workflow": "tiling", "tint": [0.10, 0.12, 0.22], "note": "#23262a"},
                      "MI_Steel_PaintBlack": {"set": "TS_Steel_ScanPaintGrey", "workflow": "tiling", "tint": [0.07, 0.07, 0.075]}})
    M["grey"] = sc("TS_Steel_ScanPaintGrey", alpha="splash", dirt_color=soot, leak_color=(0.22, 0.10, 0.04))
    tinted("kiosk", "TS_Steel_ScanPaintGrey", "MI_Steel_KioskGreen", "#24463a", 1.0, blend_start=0.5, **rust)
    M["shutter"] = sc("TS_Shutter_ScanGrey", alpha="splash", dirt_color=soot, leak_color=(0.22, 0.10, 0.04))
    M["garage"] = sc("TS_GarageDoor_ScanRust", alpha="splash", dirt_color=soot)
    M["galv"] = ts("TS_Galvanised_Aged", "galvanised", tile_m=2.0, res=2048, Age=0.55, Rust=0.15)
    M["rubber"] = ts("TS_Rubber_Aged", "rubber", tile_m=1.0, res=1024, Age=0.5)
    M["pOrange"] = ts("TS_Plastic_Orange", "plastic", tile_m=1.0, res=1024, Color=(0.80, 0.13, 0.012), Roughness=0.45,
                      **{"Sun Fade": 0.35, "Scratches": 0.5})
    M["pWhite"] = ts("TS_Plastic_White", "plastic", tile_m=1.0, res=1024, Color=(0.72, 0.72, 0.70), Roughness=0.5,
                     **{"Sun Fade": 0.2, "Scratches": 0.45})
    # timber and boards
    M["ply"] = sc("TS_Plywood_ScanLauan", alpha="splash", dirt_color=soot, macro=0.1)
    M["plyGreen"] = sc("TS_Plywood_ScanLauan", slot="MI_Plywood_HunterGreen", tint=(0.17, 0.93, 0.83), alpha="splash", dirt_color=soot)
    SLOT_META["MI_Plywood_HunterGreen"] = {"set": "TS_Plywood_ScanLauan", "workflow": "tiling", "tint": [0.17, 0.93, 0.83]}
    tinted("plyOrange", "TS_Plywood_ScanLauan", "MI_Plywood_DigOrange", "#c4571a", 1.0, alpha="splash", dirt_color=soot)
    tinted("plyProduce", "TS_Plywood_ScanLauan", "MI_Plywood_ProduceGreen", "#2d5a3a", 1.0, alpha="splash", dirt_color=soot)
    tinted("officePanel", "TS_Plywood_ScanLauan", "MI_Plywood_OfficeBrown", "#6b5a43", 1.0, alpha="splash", dirt_color=soot)
    M["plank"] = sc("TS_Wood_ScanPlankNew", alpha="splash", dirt_color=soot, macro=0.12)
    M["pallet"] = sc("TS_Wood_ScanPallet", alpha="splash", dirt_color=soot, macro=0.12)
    tinted("canvas", "TS_Fabric_ScanCanvas", "MI_Fabric_ScanCanvas_Produce", "#2d5a3a", 1.0, alpha="splash",
           dirt_color=(0.10, 0.09, 0.07))
    # masonry, concrete, floors, roofs
    tinted("brickGarage", "TS_BrickPainted_ScanWhitewash", "MI_BrickPainted_Garages", "#b9b4a6", 1.0, alpha="splash",
           dirt_color=soot, leak_color=(0.12, 0.09, 0.06))
    M["concRough"] = sc("TS_Concrete_ScanRough", alpha="splash", dirt_color=(0.06, 0.055, 0.048), macro=0.12)
    M["concFormed"] = sc("TS_Concrete_ScanFormed", alpha="splash", dirt_color=(0.07, 0.064, 0.056), macro=0.14)
    M["concTop"] = sc("TS_Sidewalk_ScanWorn", alpha="splash", dirt_color=(0.06, 0.055, 0.048), macro=0.12)
    M["coping"] = sc("TS_Concrete_ScanWeathered", alpha="splash", dirt_color=soot, macro=0.12)
    M["roof"] = sc("TS_Roof_ScanBitumen", alpha="wet", dirt_color=soot)
    M["floor"] = sc("TS_Floor_ScanGarage", alpha="wet", dirt_color=(0.05, 0.045, 0.04), leak_color=(0.018, 0.016, 0.013),
                    leak_rough=-0.35, macro=0.18)
    SLOT_META["MI_Floor_ScanGarage"] = {"set": "TS_Floor_ScanGarage", "workflow": "tiling",
                                        "note": "B = oil (dark, glossier), A = wet sheen of fresh spills, R = tyre grime"}
    tinted("floorPaint", "TS_Floor_ScanPaintWorn", "MI_FloorPaint_Yellow", "#e0b21a", 1.0, alpha="wet", dirt_color=soot)
    M["lino"] = sc("TS_Floor_ScanLino", alpha="splash", dirt_color=soot)
    M["deck"] = sc("TS_Corrugated_ScanGalv", alpha="splash", dirt_color=soot, leak_color=(0.20, 0.10, 0.04))
    # glass, lamps, flat bits
    M["glass"] = mat.make("MI_Glass_Store", "glass", Film=0.10)
    M["glassWired"] = mat.make("MI_Glass_Wired", "glass", Film=0.45)
    M["glassSky"] = mat.make("MI_Glass_Skylight", "glass", Film=0.6)
    SLOT_META["MI_Glass_Wired"] = {"workflow": "procedural", "note": "wired glass, dirty film; dark room behind"}
    SLOT_META["MI_Glass_Skylight"] = {"workflow": "procedural", "note": "skylight glazing: translucent, lets daylight in"}
    M["glassLit"] = lamp("MI_Glass_StationLit", (0.55, 0.45, 0.30), (1.0, 0.79, 0.54), 2.5)
    M["glassCool"] = lamp("MI_Glass_PlatformLit", (0.45, 0.50, 0.52), (0.81, 0.89, 1.0), 1.6)
    M["lensGreen"] = lamp("MI_Lamp_GlobeGreen", (0.10, 0.45, 0.22), (0.33, 1.0, 0.54), 6.0)
    M["lensWarm"] = lamp("MI_Lamp_BulbWarm", (0.85, 0.80, 0.70), (1.0, 0.79, 0.54), 8.0)
    M["tube"] = lamp("MI_Lamp_Fluorescent", (0.85, 0.87, 0.88), (0.81, 0.89, 1.0), 6.0)
    M["lampWork"] = lamp("MI_Lamp_HighBay", (0.85, 0.82, 0.75), (1.0, 0.85, 0.66), 10.0)
    M["interior"] = mat.flat("MI_Interior_Dark", (0.022, 0.021, 0.02), 0.9)
    M["chrome"] = mat.flat("MI_Metal_Chrome", (0.77, 0.77, 0.77), 0.10, 1.0)
    M["alu"] = mat.flat("MI_Metal_SpunAluminium", (0.62, 0.62, 0.62), 0.32, 1.0)
    M["brass"] = mat.flat("MI_Metal_Brass", (0.62, 0.46, 0.20), 0.3, 1.0)
    M["cord"] = mat.flat("MI_Rubber_Cord", (0.02, 0.02, 0.02), 0.6)
    for k, v in (("MI_Interior_Dark", "dark room behind glass"), ("MI_Metal_Chrome", "chrome"), ("MI_Metal_SpunAluminium", "spun aluminium shade"),
                 ("MI_Metal_Brass", "brass"), ("MI_Rubber_Cord", "lamp cord")):
        SLOT_META[k] = {"workflow": "flat", "note": v}
    # fruit (flat: colour and sheen; the heaps are geometry)
    for key, col_, r in (("fOrange", (0.62, 0.20, 0.012), 0.42), ("fRed", (0.38, 0.018, 0.02), 0.30), ("fRedDark", (0.20, 0.01, 0.015), 0.32),
                         ("fYellow", (0.70, 0.52, 0.04), 0.40), ("fGreen", (0.07, 0.25, 0.03), 0.35), ("fLime", (0.16, 0.38, 0.04), 0.38),
                         ("fPurple", (0.05, 0.012, 0.035), 0.22), ("fStem", (0.12, 0.10, 0.04), 0.8)):
        nm = "MI_Fruit_" + key[1:]
        M[key] = mat.flat(nm, col_, r)
        SLOT_META[nm] = {"workflow": "flat", "note": "produce stand fruit"}
    # printed faces
    for k in ART.KEYS:
        M["sign" + k] = mat.sign_face(k, (0.5, 0.5, 0.5), 0.45)
    return M


def sign_tile(M, key, w, h):
    M["sign" + key]["mi_tile_m"] = (float(w), float(h))


# ------------------------------------------------------------------------------------------------------- helpers

def poly(b, pts, thick, slot, normal, **kw):
    """Flat plate from a planar outline, its front looking along `normal` (winding fixed here)."""
    P = np.asarray(pts, dtype=np.float64)
    n = np.sum(np.cross(P, np.roll(P, -1, axis=0)), axis=0)
    if np.dot(n, normal) < 0:
        P = P[::-1]
    return b.poly_plate([tuple(p) for p in P], thick, slot, **kw)


def atlas_card(b, o, du, dv, slot, cell, size_m):
    """Card from corner o along du, dv (faces du x dv) showing atlas cell (u0, v0, u1, v1) of a face of size_m."""
    u0, v0, u1, v1 = cell
    du, dv = np.asarray(du, float), np.asarray(dv, float)
    tile = (np.linalg.norm(du) / (u1 - u0), np.linalg.norm(dv) / (v1 - v0))
    q = card(b, o, du, dv, slot, step=1.0, sign=True)
    q["uv_off"] = np.array([u0, v0])
    q["tile"] = tile
    return q


def finish(b, name, M, col_):
    """Builder.finish, honouring per-part tile overrides (atlas cards) by rescaling their UVs afterwards."""
    ob = b.finish(name, M, col_)
    uv = ob.data.uv_layers[0].data
    UV = np.empty(len(uv) * 2, np.float32)
    uv.foreach_get("uv", UV)
    UV = UV.reshape(-1, 2)
    part = b._out["part"]
    changed = False
    for i, p in enumerate(b.parts):
        if "tile" in p:
            m = part == i
            t0 = steel._tile(M[p["slot"]])
            UV[m] = (UV[m] - p["uv_off"]) * np.array(t0) / np.array(p["tile"]) + p["uv_off"]
            changed = True
    if changed:
        uv.foreach_set("uv", UV.ravel())
    return ob


SOFT = ("glass", "sign", "lens", "lamp", "interior", "tube", "f", "chrome", "brass", "alu", "cord", "canvas")


def wear(ctx, b, ob, key, ground=True, ao=0.10, rust=0.0, dirt=1.0, edge=1.0, extra=None):
    """Wear mask: R grime in cavities and on undersides, G knocked edges (and, with `rust`, paint lost where water
    sits and on rivet heads), B runs from leak points, A splash-back at the foot. extra(W, R, G, B, A) may edit."""
    W = b.loops(ob, ao=ao, rays=6) if ao else b.loops(ob, ao=None)
    P, N = W.P, W.N
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    rng = ctx.rng("wear", key)
    a = Waves(rng, 0.45).u(x + 0.7 * y, z + 0.3 * x)
    bb = Waves(rng, 1.6).u(x - 0.5 * y, z)
    c = Waves(rng, 0.15).u(x + y, z * 0.15)
    up, down = np.clip(N[:, 2], 0, 1), np.clip(-N[:, 2], 0, 1)
    names = W.names
    soft = np.isin(W.slot, [i for i, k in enumerate(names) if k.startswith(SOFT) and k not in ("floor", "floorPaint")])
    R = 0.07 + 0.14 * (a - 0.5) + 0.32 * W.concave + 0.55 * W.ao + 0.20 * up * bb + 0.15 * down * (0.4 + 0.8 * bb)
    G = edge * 0.9 * W.convex * sstep(0.30, 0.72, 0.55 * a + 0.45 * c)
    if rust:
        G = np.maximum(G, rust * 0.9 * up * sstep(0.2, 0.55, W.ao) * (0.5 + 0.5 * a))
        G = np.where(W.kind == b.RIVET, np.maximum(G, rust * 0.95 * sstep(0.60, 0.78, c) * (0.6 + 0.4 * a)), G)
        G = np.maximum(G, rust * 0.16 * up * (1 - W.ao) * (0.5 + bb))
    Bk = steel.streaks(P, N, b.leaks, 0.55, 0.035, seed=len(P)) * (0.6 + 0.4 * a) if b.leaks else np.zeros(len(P))
    A = np.zeros(len(P))
    if ground is not False:
        g0 = z.min() if ground is True else float(ground)
        hgt = z - g0
        A = np.clip(np.exp(-np.clip(hgt, 0, None) / 0.20) * (0.5 + 0.5 * c) * (1 - 0.5 * up), 0, 1)
        R = R + 0.20 * sstep(0.8, 0.0, hgt) * (0.3 + 0.7 * bb)
        G = np.maximum(G, 0.6 * edge * sstep(0.35, 0.0, hgt) * sstep(0.4, 0.75, a))
    R = R * dirt
    if extra:
        R, G, Bk, A = extra(W, R, G, Bk, A)
    R = np.where(soft, 0.05 + 0.10 * a, R)
    G = np.where(soft, 0.0, G)
    Bk = np.where(soft, 0.0, Bk)
    A = np.where(soft, 0.0, A)
    geo.set_wear(ob, np.clip(np.stack([R, G, Bk, A], 1), 0, 1), per="corner")


def inside(P, boxes, tol=TOL):
    ok = np.zeros(len(P), bool)
    for lo, hi in boxes:
        ok |= np.all((P >= np.asarray(lo) - tol) & (P <= np.asarray(hi) + tol), axis=1)
    return ok


def done(ctx, b, name, M, notes, pivot, colliders, places, allow=(), size=None, collision="box", cover=None,
         ground=True, ao=0.10, rust=0.0, dirt=1.0, extra=None, fit=True, xf=None):
    """Finish, weather, measure the fit to the colliders, set the pivot, declare the asset and its placements.
    places: [(Blender pivot location, yaw degrees, [collider indices])]."""
    ob = finish(b, name, M, ctx.col)
    wear(ctx, b, ob, name, ground=ground, ao=ao, rust=rust, dirt=dirt, extra=extra)
    co, _ = geo.arrays(ob)
    if xf is not None:                                   # built in its own frame: measure where it will stand
        co = (np.c_[co, np.ones(len(co))] @ np.asarray(xf).T)[:, :3]
    report = None
    if fit and colliders:
        boxes = [col(i) for i in colliders]
        ok = inside(co, boxes)
        out_any = ~ok
        ok2 = ok | inside(co, allow)
        bad = ~ok2
        report = {"vertices": int(len(co)), "outside_colliders": int(out_any.sum()), "allowed_overhead": int((out_any & ~bad).sum()),
                  "outside_unexplained": int(bad.sum())}
        if bad.any():
            P = co[bad]
            d = np.zeros(len(P))
            for lo, hi in boxes:
                e = np.maximum(np.maximum(np.asarray(lo) - P, P - np.asarray(hi)), 0)
                dd = np.linalg.norm(e, axis=1)
                d = np.where(d == 0, dd, np.minimum(d, dd)) if len(boxes) > 1 else dd
            report["max_outside_m"] = round(float(d.max()), 3)
            report["worst_at"] = [round(float(v), 2) for v in P[int(np.argmax(d))]]
        ctx.log("  fit %-30s %s" % (name, report))
    if xf is None:
        scene.set_pivot(ob, pivot)
    ob["mi_placed"] = True
    ctx.asset(ob, collision=collision, cover_height=cover, notes=notes + " Pivot: Blender %s." % (tuple(round(v, 3) for v in pivot),),
              expect_size=size, slots=SLOT_META)
    ctx.built.append(ob)
    ctx.places.append(dict(mesh=name, pivot=[float(v) for v in pivot], places=places, fit=report))
    return ob


# ===================================================================================================== THE STATION

MZ = dict(x0=-46.0, x1=-39.4, y=4.1, z0=3.90, zf=4.06, z1=6.30)
FACE_IN = 0.025                                       # wall planes stand this far inside the collider faces


def sheet_wall(b, o, u, n, L, z0, z1, windows=(), holes=(), band=None, step_post=1.15, lit_slot="glassLit",
               dark_slot="glassWired", liner=0.16, sheet_slot="sheet", trim_slot="steel"):
    """Riveted sheet-steel wall: outer face on the plane through o with outward normal n, running along u for L,
    from z0 to z1. windows: [(u centre, width, lit)] in the band (zb0, zb1); holes: [(u0, u1, z0, z1)] left open
    (steel passing through, doorways). A dark liner stands `liner` behind (what the glass shows)."""
    o, u, n = (np.asarray(v, float) for v in (o, u, n))
    P = lambda s, z, d=0.0: o + u * s + Z * z - n * d

    def bx_(s0, s1, za, zb, d0, d1, slot, **kw):
        a, c = P(s0, za, d0), P(s1, zb, d1)
        return b.box(np.minimum(a, c), np.maximum(a, c), slot, **kw)

    opens = [(c - w / 2, c + w / 2, band[0], band[1]) for c, w, _ in windows] if band else []
    for s0, s1, za, zb in cells(0.0, L, z0, z1, opens + list(holes)):
        bx_(s0, s1, za, zb, 0.0, 0.004, sheet_slot, vdir=Z, fdir=u)
    # posts (angles) at the panel joints, behind the sheet, with cover strips and rivets in front
    k = max(1, int(round(L / step_post)))
    for i in range(k + 1):
        s = min(max(i * L / k, 0.03), L - 0.03)
        if any(h[0] - 0.03 < s < h[1] + 0.03 and h[2] <= z0 + 0.1 for h in holes):
            continue
        spans = cells(s - 0.025, s + 0.025, z0, z1, list(holes))
        for s0, s1, za, zb in spans:
            bx_(s0, s1, za, zb, 0.004, 0.07, trim_slot)
            bx_(s - 0.03, s + 0.03, za, zb, -0.006, 0.0, trim_slot)
            zs = np.arange(za + 0.08, zb - 0.04, 0.15)
            b.rivets([P(s, zz, -0.006) for zz in zs], n, trim_slot, d=0.020, h=0.008, leak=0.08)
    for zt in ([band[0] - 0.05, band[1]] if band else []) + [z0, z1 - 0.06]:
        for s0, s1, za, zb in cells(0.0, L, zt, zt + 0.06, list(holes)):
            bx_(s0, s1, za, zb, -0.012, 0.0, trim_slot)
            b.rivets([P(s, (za + zb) / 2, -0.012) for s in np.arange(s0 + 0.08, s1 - 0.04, 0.2)], n, trim_slot, d=0.020, h=0.008, leak=0.1)
    if band:
        za, zb = band
        for c, w, lit in windows:
            s0, s1 = c - w / 2, c + w / 2
            for (a0, a1, b0, b1) in ((s0, s0 + 0.045, za, zb), (s1 - 0.045, s1, za, zb), (s0, s1, za, za + 0.045), (s0, s1, zb - 0.045, zb),
                                     ((s0 + s1) / 2 - 0.015, (s0 + s1) / 2 + 0.015, za, zb), (s0, s1, (za + zb) / 2 - 0.012, (za + zb) / 2 + 0.012)):
                bx_(a0, a1, b0, b1, 0.0, 0.05, trim_slot)
            bx_(s0, s1, za - 0.02, za, -0.03, 0.05, trim_slot)                          # sill
            bx_(s0 + 0.045, s1 - 0.045, za + 0.045, zb - 0.045, 0.03, 0.036, lit_slot if lit else dark_slot)
    if liner:
        for s0, s1, za, zb in cells(0.0, L, z0, z1, list(holes)):
            bx_(s0, s1, za, zb, liner, liner + 0.01, "interior")


def mezzanine(ctx, M):
    b = B(41, step=0.35)
    x0, x1, yh, zf0, zf, z1 = MZ["x0"] + FACE_IN, MZ["x1"] - FACE_IN, MZ["y"] - FACE_IN, MZ["z0"], MZ["zf"], MZ["z1"]
    # floor: built-up plate floor, lap strips and rivet rows underneath, perimeter channel
    b.box((x0, -yh, zf0 + 0.008), (x1, yh, zf), "steel", chamfer=0.0)
    for xs in np.arange(x0 + 1.1, x1 - 0.5, 1.1):
        b.box((xs - 0.04, -yh, zf0), (xs + 0.04, yh, zf0 + 0.008), "steel")
        for dx in (-0.025, 0.025):
            b.rivets([(xs + dx, yy, zf0) for yy in np.arange(-yh + 0.1, yh, 0.15)], -Z, "steel", d=0.022, h=0.008, leak=0.05)
    for sy in (-1, 1):
        b.box((x0, sy * yh - 0.01, zf0), (x1, sy * yh + 0.01 * 0, zf + 0.06), "steel")
    for xx in (x0, x1):
        b.box((xx - 0.005, -yh, zf0), (xx + 0.005, yh, zf + 0.06), "steel")
    # walls: east (name board, six panes), the two street sides (four panes), west
    girder = (-45.0 - 0.36, -45.0 + 0.36, 5.28, z1)
    brace = (-45.15, -44.85, 4.28, 4.60)
    band = (4.95, 5.75)
    east = [((-2.75 + 1.1 * i) + yh, 1.0, i in (1, 4)) for i in range(6)]
    sheet_wall(b, (x1, -yh, 0), Y, X, 2 * yh, zf, z1, east, band=band)
    L = x1 - x0
    side_s = [(-42.7 + d - x0, 1.1, i == 2) for i, d in enumerate((-1.8, -0.6, 0.6, 1.8))]      # 3rd from the west
    side_n = [(x1 - (-42.7 - d), 1.1, i == 2) for i, d in enumerate((-1.8, -0.6, 0.6, 1.8))]    # 3rd from the east
    hs = [(girder[0] - x0, girder[1] - x0, girder[2], girder[3]), (brace[0] - x0, brace[1] - x0, brace[2], brace[3])]
    sheet_wall(b, (x0, -yh, 0), X, -Y, L, zf, z1, side_s, holes=hs, band=band)
    hn = [(x1 - girder[1], x1 - girder[0], girder[2], girder[3]), (x1 - brace[1], x1 - brace[0], brace[2], brace[3])]
    sheet_wall(b, (x1, yh, 0), -X, Y, L, zf, z1, side_n, holes=hn, band=band)
    sheet_wall(b, (x0, yh, 0), -Y, -X, 2 * yh, zf, z1, [], band=None)
    # collars round the steel that passes through the side walls
    for sy in (-1, 1):
        yy = sy * yh
        for (a0, a1, b0, b1) in (girder, brace):
            for (p0, p1) in (((a0 - 0.03, b0 - 0.03), (a1 + 0.03, b0)), ((a0 - 0.03, b0), (a0, b1)), ((a1, b0), (a1 + 0.03, b1))):
                b.box((p0[0], yy - 0.012 * (1 if sy > 0 else 0) - 0.006, p0[1]), (p1[0], yy + 0.006, p1[1]), "steel")
    # roof (cut where the cross girder passes)
    for xa, xb in ((x0, girder[0]), (girder[1], x1)):
        b.box((xa, -yh, 6.22), (xb, yh, z1), "roofing", vdir=X)
    # name board: enamel plate on standoffs, east face
    bx0 = MZ["x1"] - 0.004
    b.box((bx0 - 0.02, -2.3, 4.06), (bx0, 2.3, 4.88), "steel")
    card(b, (bx0 + 0.0008, -2.3, 4.06), (0, 4.6, 0), (0, 0, 0.82), "signStationName", sign=True)
    sign_tile(M, "StationName", 4.6, 0.82)
    b.rivets([(bx0, yy, zz) for yy in (-2.22, 2.22) for zz in (4.14, 4.80)], X, "steel", d=0.026, h=0.010, leak=0.6)
    # gooseneck lamps over the board (overhead)
    for yy in (-1.4, 1.4):
        pipe(b, [(x1, yy, 5.92), (x1 + 0.25, yy, 5.95), (x1 + 0.45, yy, 5.90), (x1 + 0.50, yy, 5.84)], 0.016, "steel", bend=0.08)
        lathe(b, [(0.0, 5.84), (0.05, 5.84), (0.07, 5.80), (0.17, 5.70), (0.175, 5.69), (0.0, 5.69)], "steel", 24, loc=(x1 + 0.5, yy, 0))
        lathe(b, [(0.0, 5.695), (0.12, 5.695), (0.11, 5.70), (0.0, 5.71)], "lensWarm", 20, loc=(x1 + 0.5, yy, 0))
        b.box((x1 - 0.03, yy - 0.06, 5.86), (x1, yy + 0.06, 5.98), "steel")
    allow = [((x1, -1.7, 5.6), (x1 + 0.7, 1.7, 6.05))]
    return done(ctx, b, "SM_Struct_ElMezzanine", M,
                "188 St fare-control mezzanine hung under the tracks (05-level 2.7.2): riveted plate floor 3.90..4.06 with lap "
                "strips underneath, sheet-steel walls on angle posts to 6.30 (fine-rib panels, cover strips, trims), a window "
                "band 4.95..5.75 (east: six panes, 2nd and 5th lit MI_Glass_StationLit; street sides: four, 3rd lit), dark liner "
                "behind, wall cut and collared where the El's cross girder and knee braces pass (x -45), enamel name board "
                "M_Sign_StationName 4.6 x 0.82 on the east face, two gooseneck lamps over it. Collider 65 (tag station).",
                (-42.7, 0.0, 0.0), [65], [((-42.7, 0.0, 0.0), 0.0, [65])], allow=allow, rust=0.6, ground=False)


def bridge(ctx, M, s):
    """Covered bridge on side s (-1 south = Blender -y, +1 north)."""
    b = B(42 + s, step=0.35)
    xa, xb = -45.9 + FACE_IN, -44.2 - FACE_IN
    y0, y1 = MZ["y"] - FACE_IN, 9.05 - FACE_IN
    Yv = lambda v: s * v
    z0, zf = 3.90, 4.06
    colm = (-45.0 - 0.34, -45.0 + 0.34, 4.26, 4.94)                 # the El column passes through the floor
    yel = 5.45                                                      # under the El deck up to here
    for c0, c1, d0, d1 in cells(xa, xb, y0, y1, [(colm[0], colm[1], colm[2], colm[3])]):
        b.box((c0, min(Yv(d0), Yv(d1)), z0 + 0.008), (c1, max(Yv(d0), Yv(d1)), zf), "steel")
    for yy in np.arange(y0 + 0.9, y1 - 0.3, 0.9):                   # lap strips underneath
        if colm[2] - 0.05 < yy < colm[3] + 0.05:
            continue
        b.box((xa, Yv(yy) - 0.04, z0), (xb, Yv(yy) + 0.04, z0 + 0.008), "steel")
        b.rivets([(xx, Yv(yy) + dy, z0) for xx in np.arange(xa + 0.1, xb, 0.15) for dy in (-0.025, 0.025)], -Z, "steel", d=0.022, h=0.008, leak=0.05)
    for (a0, a1, d0, d1) in ((colm[0] - 0.04, colm[1] + 0.04, colm[2] - 0.04, colm[2]), (colm[0] - 0.04, colm[1] + 0.04, colm[3], colm[3] + 0.04),
                             (colm[0] - 0.04, colm[0], colm[2], colm[3]), (colm[1], colm[1] + 0.04, colm[2], colm[3])):
        b.box((a0, min(Yv(d0), Yv(d1)), zf), (a1, max(Yv(d0), Yv(d1)), zf + 0.05), "steel")      # collar angle
    for xx in (xa, xb):
        b.box((xx - 0.004 if xx > -45 else xx, min(Yv(y0), Yv(y1)), z0), (xx + (0.0 if xx > -45 else 0.004), max(Yv(y0), Yv(y1)), zf + 0.06), "steel")
    # side walls: low under the El, full with a window band beyond it; the east wall is open where the stair arrives
    band = (5.15, 6.05)
    wins = lambda: [(c - y0, 0.95, False) for c in np.arange(yel + 0.65, 9.0 - 0.4, 1.05)]
    for xw, nx in ((xa, -1), (xb, 1)):
        # walls run along +/-y from the mezzanine end; the frame's u must point along increasing distance
        u = np.array([0, s, 0.0])
        n = np.array([nx, 0, 0.0])
        o = (xw, Yv(y0), 0.0)
        hz = [(-0.1, yel - y0, 5.25, 6.3)]                                  # under the El: wall stops at 5.25
        if nx > 0:
            hz.append((7.25 - y0, y1 - y0 + 0.1, zf - 0.01, 6.3))              # stair opening
        sheet_wall(b, o, u, n, y1 - y0, zf, 6.20, [w for w in wins() if not (nx > 0 and w[0] + y0 > 7.1)], holes=hz, band=band)
    # outer end wall with one window
    sheet_wall(b, (xb, Yv(y1), 0.0), np.array([-1.0, 0, 0]), np.array([0, s, 0.0]), xb - xa, zf, 6.20, [((xb - xa) / 2, 0.9, False)], band=band)
    # roof beyond the El footprint, header plate facing the El
    b.box((xa, min(Yv(yel), Yv(y1)), 6.20), (xb, max(Yv(yel), Yv(y1)), 6.30), "roofing", vdir=Y)
    b.box((xa, min(Yv(yel), Yv(yel + 0.01)), 5.25), (xb, max(Yv(yel), Yv(yel + 0.01)), 6.30), "sheet")
    # stair-head opening frame
    for yy in (7.25, y1 - 0.03):
        b.box((xb - 0.06, Yv(yy) - 0.03, zf), (xb, Yv(yy) + 0.03, 6.20), "steel")
    b.box((xb - 0.06, min(Yv(7.22), Yv(y1)), 6.05), (xb, max(Yv(7.22), Yv(y1)), 6.20), "steel")
    # posts under the stair head
    for xp in (-45.9, -44.2):
        yp = Yv(8.95)
        b.box((xp - 0.07, yp - 0.07, 0.17), (xp + 0.07, yp + 0.07, z0), "steel", chamfer=0.004)
        b.box((xp - 0.098, yp - 0.098, 0.15), (xp + 0.098, yp + 0.098, 0.17), "steel")
        b.box((xp - 0.098, yp - 0.098, z0 - 0.02), (xp + 0.098, yp + 0.098, z0), "steel")
        for dx in (-0.07, 0.07):
            for dy in (-0.07, 0.07):
                b.box((xp + dx - 0.012, yp + dy - 0.012, 0.17), (xp + dx + 0.012, yp + dy + 0.012, 0.19), "steel", chamfer=0.003)
        b.leaks.append((xp, yp, z0 - 0.02))
    cols = [77, 78, 79] if s < 0 else [66, 67, 68]
    name = "SM_Struct_ElBridge_" + ("N" if s > 0 else "S")
    return done(ctx, b, name, M,
                "Covered bridge from the mezzanine to the %s stair head (05-level 2.7.2): riveted plate floor 3.90..4.06, collar "
                "round the El column that passes through it, sheet walls with a wired-glass band 5.15..6.05 and a roof 6.20..6.30 "
                "beyond the El deck's footprint (|y| > 5.45; under it the walls stop at 5.25 and the deck is the roof), the east "
                "wall open over the stair (|y| 7.25..9.05), end wall with one pane, two posts 0.14 under the stair head on base "
                "plates. Colliders %s." % ("north" if s > 0 else "south", cols),
                (-45.05, Yv(6.575), 0.0), cols, [((-45.05, Yv(6.575), 0.0), 0.0, cols)], allow=[col(65)], rust=0.6, ground=0.15)


ST = dict(xf=-38.8, xt=-44.2, g=0.27, n=20, z0=0.15, ztop=4.06, hw=0.95)


def stair(ctx, M):
    """Built on the south side (centre Blender y -8.15); symmetric about its centre line."""
    b = B(45, step=0.3)
    cy = -8.15
    xf, g, n, z0 = ST["xf"], ST["g"], ST["n"], ST["z0"]
    r = (ST["ztop"] - z0) / n
    line = lambda x: z0 + r + (xf - x) * r / g                        # through the nosings
    sl = np.array([-g, 0.0, r]) / math.hypot(g, r)                    # up the flight
    nrm = np.array([r, 0.0, g]) / math.hypot(g, r)                    # square to the slope, upward
    wi, ws = 0.80, 0.012                                              # stringer inner face, web thickness
    xt = ST["xt"]
    # treads and risers
    for k in range(1, n + 1):
        xa, xb = xf - k * g, xf - (k - 1) * g
        zt = z0 + k * r
        b.box((xa, cy - wi, zt - 0.008), (xb - 0.03, cy + wi, zt), "tread", chamfer=0.0)
        b.prism(steel.angle(0.05, 0.05, 0.006), (xb, cy - wi, zt), -X, -Z, (0, 2 * wi, 0), "rail")      # nosing angle
        b.box((xb - 0.006, cy - wi, zt - r), (xb, cy + wi, zt - 0.05), "steel")                        # riser
        b.box((xa, cy - wi, zt - 0.05), (xb, cy - wi + 0.04, zt - 0.008), "steel")                     # carriers
        b.box((xa, cy + wi - 0.04, zt - 0.05), (xb, cy + wi, zt - 0.008), "steel")
    # stringers: plate web from the nosing line down 0.40, flange angles, rivets
    xc = xf - (0.40 - (line(xf) - z0)) * g / r if line(xf) - 0.40 < z0 else xf
    x_last = xf - (n - 1) * g
    for sy in (-1, 1):
        yo = cy + sy * (wi + ws)
        outline = [(xf + 0.02, yo, z0), (xf + 0.02, yo, line(xf)), (x_last, yo, line(x_last)), (xt, yo, line(x_last)),
                   (xt, yo, line(x_last) - 0.40), (xc, yo, z0)]
        poly(b, outline, ws, "steel", np.array([0, sy, 0.0]), vdir=sl, fdir=nrm)
        cosa = g / math.hypot(g, r)
        for pa, vv, L in ((np.array([xf, yo, line(xf)]), -nrm, (xf - x_last) / cosa),
                          (np.array([xc, yo, z0]), nrm, (xc - x_last) / cosa)):
            b.prism(steel.angle(0.075, 0.075, 0.009), pa, np.array([0, sy, 0.0]), vv, sl * L, "steel")
            pts = [pa + sl * t + vv * 0.045 + np.array([0, sy * 0.009, 0]) for t in np.arange(0.12, L - 0.05, 0.13)]
            b.rivets(pts, np.array([0, sy, 0.0]), "steel", d=0.026, h=0.010, leak=0.1)
        # lattice balustrade: posts, top rail, mid rail, diagonal flats between the stringer top and the mid rail
        posts = list(np.linspace(xf - 0.12, x_last + 0.06, 6))
        yr = cy + sy * (wi + ws + 0.03)
        for xp in posts:
            rod(b, (xp, yr, line(xp) - 0.10), (xp, yr, line(xp) + 0.98), 0.022, "steel", n=10)
        top = lambda x: line(x) + 1.0
        rod(b, (xf + 0.05, yr, top(xf + 0.05)), (xt + 0.02, yr, top(x_last)), 0.024, "steel", n=12)
        rod(b, (xf + 0.05, yr, line(xf + 0.05) + 0.52), (x_last, yr, line(x_last) + 0.52), 0.016, "steel", n=8)
        pitch = 0.22
        for xs in np.arange(xf - 0.05, x_last + 0.2, -pitch):
            for dx in (-0.37, 0.37):
                xe = xs + dx
                if not (x_last <= xe <= xf):
                    continue
                bar(b, (xs, yr, line(xs) + 0.03), (xe, yr, line(xe) + 0.50), 0.035, 0.006, "steel", up=np.array([0, 1.0, 0]))
        # roof rafters on posts above the rail (overhead), purlins across, corrugated sheet
    rz = lambda x: 2.65 + (-38.2 - x) * (6.26 - 2.65) / (-38.2 - xt)
    xe0 = -38.95
    for sy in (-1, 1):
        yr = cy + sy * (wi + ws + 0.03)
        for xp in np.linspace(xf - 0.12, x_last + 0.06, 6):
            b.prism(steel.angle(0.05, 0.05, 0.006), (xp - 0.025, yr - 0.025, line(xp) + 0.98), X, Y, (0, 0, rz(xp) - 0.13 - line(xp) - 0.98), "steel")
        b.prism(steel.channel(0.12, 0.05, 0.008, 0.006), (xe0, cy + sy * 0.92, rz(xe0) - 0.13), np.array([0, -sy, 0.0]), nrm,
                np.array([xt - xe0, 0.0, rz(xt) - rz(xe0)]), "steel")
    for xp in np.arange(xe0 - 0.05, xt, -0.9):
        b.prism(steel.angle(0.05, 0.05, 0.006), (xp, cy - 0.93, rz(xp) - 0.012), -X, -Z, (0, 1.86, 0), "steel")
    sheet_pts = [(xe0, cy - ST["hw"], rz(xe0)), (xt, cy - ST["hw"], rz(xt)), (xt, cy + ST["hw"], rz(xt)), (xe0, cy + ST["hw"], rz(xe0))]
    F = np.array([[np.array(sheet_pts[0]) + (np.array(sheet_pts[1]) - np.array(sheet_pts[0])) * t + np.array([0, 2 * ST["hw"] * v, 0])
                   for t in np.linspace(0, 1, 10)] for v in np.linspace(0, 1, 4)])
    sheet(b, F, 0.008, "roofing")
    b.box((xe0 - 0.03, cy - ST["hw"], rz(xe0) - 0.12), (xe0, cy + ST["hw"], rz(xe0) + 0.01), "steel")            # eave fascia
    # trestle at mid flight
    xm = -41.5
    for sy in (-1, 1):
        b.box((xm - 0.06, cy + sy * 0.78 - 0.06, z0), (xm + 0.06, cy + sy * 0.78 + 0.06, line(xm) - 0.55), "steel", chamfer=0.004)
        b.box((xm - 0.09, cy + sy * 0.78 - 0.09, z0), (xm + 0.09, cy + sy * 0.78 + 0.09, z0 + 0.02), "steel")
    b.box((xm - 0.08, cy - wi, line(xm) - 0.55), (xm + 0.08, cy + wi, line(xm) - 0.40), "steel")
    # portal: posts, stems, green globes; scissor gate; plate
    xp = -38.56
    for sy in (-1, 1):
        yp = cy + sy * 0.84
        b.box((xp - 0.06, yp - 0.06, z0), (xp + 0.06, yp + 0.06, 2.50), "steel", chamfer=0.004)
        b.box((xp - 0.075, yp - 0.075, 2.50), (xp + 0.075, yp + 0.075, 2.53), "steel")
        lathe(b, [(0.0, 2.53), (0.03, 2.53), (0.022, 2.60), (0.02, 2.95), (0.045, 2.98), (0.0, 2.99)], "steel", 16, loc=(xp, yp, 0))
        sp = geo.sphere(0.17, 24, 12)
        geo.transform(sp, loc=(xp, yp, 3.15))
        b.absorb(sp, "lensGreen")
        lathe(b, [(0.0, 3.30), (0.06, 3.30), (0.05, 3.34), (0.0, 3.35)], "steel", 16, loc=(xp, yp, 0))
    gx0, gx1 = -38.70, -38.62
    b.box((gx0, cy - 0.78, 2.55), (gx1, cy + 0.78, 2.63), "steel")
    b.box((gx0, cy - 0.78, z0), (gx1, cy + 0.78, z0 + 0.02), "steel")
    pk = np.arange(-0.74, 0.75, 0.124)
    for py in pk:
        b.box((gx0 + 0.02, cy + py - 0.008, z0 + 0.02), (gx1 - 0.02, cy + py + 0.008, 2.55), "steel")
    for i in range(len(pk) - 1):
        for t0, t1 in ((0.25, 0.95), (0.95, 1.65), (1.65, 2.35)):
            for flip in (0, 1):
                ya, yb = (pk[i], pk[i + 1]) if not flip else (pk[i + 1], pk[i])
                bar(b, ((gx0 + gx1) / 2, cy + ya, z0 + t0), ((gx0 + gx1) / 2, cy + yb, z0 + t1), 0.022, 0.004, "steel", up=X)
    b.box((-38.645, cy - 0.06, 1.05), (-38.60, cy + 0.06, 1.20), "steel")                               # hasp
    lathe(b, [(0.0, -0.03), (0.03, -0.03), (0.032, 0.03), (0.0, 0.03)], "brass", 12, loc=(-38.585, cy, 1.0), rot=(0, 90, 0))
    b.box((-38.535, cy - 0.75, 2.18), (-38.51, cy + 0.75, 2.60), "steel")
    card(b, (-38.5095, cy - 0.75, 2.18), (0, 1.5, 0), (0, 0, 0.42), "signStationClosed", sign=True)
    sign_tile(M, "StationClosed", 1.5, 0.42)
    for sy in (-1, 1):
        b.box((-38.62, cy + sy * 0.78 - 0.02, 2.40), (-38.535, cy + sy * 0.78 + 0.02, 2.44), "steel")
    cols = [80, 81, 82, 83, 84, 85]
    hw = ST["hw"]
    allow = [((xt - 0.05, cy - hw - 0.05, 0.0), (xf + 0.1, cy + hw + 0.05, 7.0)),       # rails, roof and posts above the boxes
             ((-38.75, cy - 1.05, 2.5), (-38.3, cy + 1.05, 3.4))]                             # globes over the gate
    return done(ctx, b, "SM_Struct_ElStair", M,
                "188 St station stair (05-level 2.7.2), foot x -38.8 (z 0.15) to head x -44.2 (z 4.06 = bridge floor): 20 risers "
                "of 0.1955 and goings of 0.27, diamond-plate treads with steel nosing angles (bare where feet wear them), sheet "
                "risers, riveted plate stringers with flange angles, lattice balustrades with pipe top and mid rails (thin bars "
                "over the coarse flight boxes), a corrugated roof on channel rafters and angle posts from x -38.95 (z 3.09) to "
                "the head (6.26), the trestle at x -41.5, portal posts with green globes (MI_Lamp_GlobeGreen), a scissor gate "
                "with hasp and padlock, plate M_Sign_StationClosed. Symmetric about its centre line: place the same mesh at both "
                "stairs (pivot on the centre line at the foot, ground).",
                (-38.8, cy, 0.0), cols, [((-38.8, cy, 0.0), 0.0, cols), ((-38.8, -cy, 0.0), 0.0, [69, 70, 71, 72, 73, 74])],
                allow=allow, rust=0.8, ground=0.15)


def platform(ctx, M, s, x0, x1, end=False, name=None, posts=(), windows=(), tubes=(), wind_x1=None, can_x1=None):
    b = B(47 + (s > 0) + 2 * end, step=0.4)
    Yv = lambda v: s * v
    lo = lambda a, c: (min(Yv(a), Yv(c)), max(Yv(a), Yv(c)))
    # slab, edge nosing and paint strip
    ya, yb = lo(3.75, 7.05)
    b.box((x0, ya, 7.55), (x1, yb, 7.75), "concRough", vdir=X)
    y0, y1 = lo(3.75, 4.05)
    b.box((x0, y0, 7.75), (x1, y1, 7.7515), "floorPaint", vdir=X)
    y0, y1 = lo(3.75, 3.80)
    b.box((x0, y0, 7.60), (x1, y1, 7.76), "steel")
    # stringers under the slab, cantilevers and knee braces at the posts, beyond the posts every 5 m
    for yy in (4.4, 6.5):
        b.prism(steel.ibeam(0.15, 0.10, 0.01, 0.007), (x0, Yv(yy), 7.40), Y, Z, (x1 - x0, 0, 0), "steel")
    for xp in sorted(set(list(posts) + list(np.arange(x0 + 2.5, x1 - 0.5, 5.0)))):
        y0_, y1_ = lo(3.8, 7.0)
        b.box((xp - 0.05, y0_, 7.40), (xp + 0.05, y1_, 7.55), "steel")
        bar(b, (xp, Yv(4.8), 6.2), (xp, Yv(6.9), 7.4), 0.10, 0.10, "steel", up=X)
        b.box((xp - 0.008, min(Yv(4.6), Yv(5.1)), 6.0), (xp + 0.008, max(Yv(4.6), Yv(5.1)), 6.45), "steel")
    # windscreen with windows, posts, canopy
    wx1 = wind_x1 if wind_x1 is not None else x1
    wy0, wy1 = 7.0, 7.05
    sheet_wall(b, (x0, Yv(wy1), 0.0), X, np.array([0, s, 0.0]), wx1 - x0, 7.75, 10.15,
               [(c - x0, 1.7, True) for c in windows], band=(8.675, 9.425), lit_slot="glassCool", step_post=1.25, liner=0.0)
    cx1 = can_x1 if can_x1 is not None else x1
    zc = lambda yy: 10.42 + (yy - 3.9) * (10.15 - 10.42) / (7.25 - 3.9)
    for xp in posts:
        yp = Yv(6.75)
        b.box((xp - 0.07, yp - 0.07, 7.75), (xp + 0.07, yp + 0.07, zc(6.75) - 0.12), "steel", chamfer=0.004)
        bar(b, (xp, Yv(3.9), zc(3.9) - 0.10), (xp, Yv(7.25), zc(7.25) - 0.10), 0.08, 0.15, "steel", up=Z)
        bar(b, (xp, yp, zc(6.75) - 0.8), (xp, Yv(5.2), zc(5.2) - 0.16), 0.06, 0.06, "steel", up=X)
    F = np.array([[(xx, Yv(yy), zc(yy)) for xx in np.linspace(x0, cx1, max(2, int((cx1 - x0) / 1.0)))] for yy in np.linspace(3.9, 7.25, 5)])
    if s > 0:
        F = F[:, ::-1]
    sheet(b, F[::-1] if s < 0 else F, 0.008, "roofing")
    for yy in (4.6, 5.8, 6.9):
        b.prism(steel.angle(0.05, 0.05, 0.006), (x0, Yv(yy), zc(yy) - 0.006), np.array([0, 0, -1.0]), np.array([0, 1.0, 0]), (cx1 - x0, 0, 0), "steel")
    y0, y1 = lo(3.86, 3.9)
    b.box((x0, y0, zc(3.9) - 0.18), (cx1, y1, zc(3.9) + 0.02), "steel")                      # fascia on the track edge
    for xt in tubes:
        yt = Yv(5.4)
        b.box((xt - 0.62, yt - 0.06, 10.10), (xt + 0.62, yt + 0.06, zc(5.4) - 0.01), "steel")
        lathe(b, [(0.0, -0.6), (0.014, -0.6), (0.014, 0.6), (0.0, 0.6)], "tube", 10, loc=(xt, yt, 10.085), rot=(0, 90, 0))
        lathe(b, [(0.0, -0.6), (0.014, -0.6), (0.014, 0.6), (0.0, 0.6)], "tube", 10, loc=(xt, yt + 0.04 * s, 10.085), rot=(0, 90, 0))
    if end:
        y0, y1 = lo(3.75, 7.0)
        b.box((x1 - 0.02, y0, 7.75), (x1, y1, 8.85), "steel")
        for yy in np.arange(4.0, 7.0, 0.6):
            b.box((x1 - 0.08, Yv(yy) - 0.03, 7.75), (x1 - 0.02, Yv(yy) + 0.03, 8.85), "steel")
    return b


def platforms(ctx, M):
    out = []
    for s in (-1, 1):
        b = platform(ctx, M, s, -46.0, -29.5, end=True, posts=(-45.0, -35.0), windows=(-45.2, -42.8, -40.4, -38.0, -35.6, -33.2),
                     tubes=(-43.5, -38.0, -32.5), wind_x1=-31.0, can_x1=-30.5)
        cols = [86, 87] if s < 0 else [75, 76]
        nm = "SM_Struct_ElPlatformEnd_" + ("N" if s > 0 else "S")
        allow = [((-46.1, -7.3 if s < 0 else 3.7, 5.9), (-29.4, -3.7 if s < 0 else 7.3, 10.6))]
        out.append(done(ctx, b, nm, M,
                        "188 St %s platform over the bounds (05-level 2.7.2), x -46..-29.5: concrete slab 7.55..7.75 with a steel "
                        "nosing and yellow edge paint, on I stringers, cantilevers and knee braces from the El girder line; sheet "
                        "windscreen on the street edge to x -31 with six lit panes (MI_Glass_PlatformLit); canopy posts at x -45 "
                        "and -35 with cantilever beams and braces, corrugated canopy sloping 10.42 -> 10.15 to x -30.5, three "
                        "fluorescent fixtures, end plate at x -29.5. Colliders %s." % ("north" if s > 0 else "south", cols),
                        (-46.0, 0.0, 0.0), cols, [((-46.0, 0.0, 0.0), 0.0, cols)], allow=allow, rust=0.5, ground=False))
    b = platform(ctx, M, -1, 0.0, 10.0, posts=(5.0,), windows=(1.25, 3.75, 6.25, 8.75), tubes=(2.5, 7.5))
    places = [((x, 0.0, 0.0), 0.0, []) for x in (-96.0, -86.0, -76.0, -66.0, -56.0)]
    places += [((x + 10.0, 0.0, 0.0), 180.0, []) for x in (-96.0, -86.0, -76.0, -66.0, -56.0)]
    out.append(done(ctx, b, "SM_Struct_ElPlatform_10m", M,
                    "Plain 10 m platform module of the 188 St station for the run west of the bounds (x -96..-46): the south "
                    "platform's cross-section with one canopy post at its middle, four lit windscreen panes and two tubes. "
                    "Symmetric along x, so the north platform is the same mesh turned 180 degrees about its own middle.",
                    (0.0, 0.0, 0.0), [], places, rust=0.5, ground=False, fit=False))
    return out


# ============================================================================================ KIOSKS AND THE STAND

def kiosk(ctx, M, name, w, d, face, band_key, band_w, door_face, colliders, centre):
    """Sheet-steel kiosk, footprint centre at the origin, z 0 = sidewalk. face: unit vector of the shutter face."""
    b = B(50 + len(name), step=0.3)
    f = np.asarray(face, float)
    H = 2.50
    hx, hy = w / 2 - 0.002, d / 2 - 0.002
    fx, fy = w / 2 - 0.024, d / 2 - 0.024                            # wall planes: trims and rivets stay inside
    b.box((-hx + 0.01, -hy + 0.01, 0.0), (hx - 0.01, hy - 0.01, 0.10), "black")                    # base channel
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.prism(steel.angle(0.05, 0.05, 0.005), (sx * hx, sy * hy, 0.0), np.array([-sx, 0, 0.0]), np.array([0, -sy, 0.0]), (0, 0, H), "kiosk")
    faces = [(np.array([0, -1.0, 0]), X, w, fy), (np.array([0, 1.0, 0]), -X, w, fy), (np.array([1.0, 0, 0]), Y, d, fx), (np.array([-1.0, 0, 0]), -Y, d, fx)]
    for n, u, L, off in faces:
        o = n * off - u * (L / 2 - 0.05)
        Ls = L - 0.10
        holes = []
        if np.dot(n, f) > 0.9:
            holes.append((0.12, Ls - 0.12, 0.80, 2.05))
        sheet_wall(b, o, u, n, Ls, 0.10, H - 0.26, [], holes=holes, band=None, step_post=0.75, sheet_slot="kiosk", trim_slot="kiosk", liner=0.0)
        # fascia band
        P = lambda sv, z, dd=0.0: o + u * sv + Z * z - n * dd
        a, c = P(0, H - 0.26, 0), P(Ls, H, 0.05)
        b.box(np.minimum(a, c), np.maximum(a, c), "kiosk")
        if np.dot(n, f) > 0.9:
            bw = min(band_w, Ls - 0.1)
            card(b, P((Ls - bw) / 2, H - 0.26, -0.001), u * bw, Z * 0.26, "sign" + band_key, sign=True)
            sign_tile(M, band_key, bw, 0.26)
            # shutter: hood, guides, slat curtain, bottom bar, hasp and padlock; folded counter flap below
            sa, sb_ = 0.12, Ls - 0.12
            a, c = P(sa - 0.06, 2.05, 0.0), P(sb_ + 0.06, 2.22, 0.12)
            b.box(np.minimum(a, c), np.maximum(a, c), "kiosk")
            for sv in (sa - 0.02, sb_ + 0.02):
                a, c = P(sv - 0.03, 0.80, 0.0), P(sv + 0.03, 2.05, 0.05)
                b.box(np.minimum(a, c), np.maximum(a, c), "black")
            a, c = P(sa, 0.84, 0.03), P(sb_, 2.05, 0.04)
            b.box(np.minimum(a, c), np.maximum(a, c), "shutter", vdir=Z, fdir=u)
            a, c = P(sa, 0.80, 0.02), P(sb_, 0.86, 0.045)
            b.box(np.minimum(a, c), np.maximum(a, c), "black")
            a, c = P(Ls / 2 - 0.05, 0.70, 0.0), P(Ls / 2 + 0.05, 0.84, 0.02)
            b.box(np.minimum(a, c), np.maximum(a, c), "black")
            lathe(b, [(0.0, -0.035), (0.028, -0.035), (0.03, 0.03), (0.0, 0.03)], "brass", 12, loc=tuple(P(Ls / 2, 0.66, 0.012)))
            a, c = P(0.15, 0.42, 0.0), P(Ls - 0.15, 0.80, 0.025)
            b.box(np.minimum(a, c), np.maximum(a, c), "kiosk")
            for sv in (0.4, Ls - 0.4):
                lathe(b, [(0.0, -0.04), (0.012, -0.04), (0.012, 0.04), (0.0, 0.04)], "black", 8, loc=tuple(P(sv, 0.80, -0.0)), rot=(0, 90, 0))
        elif np.dot(n, np.asarray(door_face, float)) > 0.9:
            a, c = P(Ls / 2 - 0.35, 0.12, -0.004), P(Ls / 2 + 0.35, 2.05, 0.0)
            b.box(np.minimum(a, c), np.maximum(a, c), "kiosk")
            for zz in (0.4, 1.7):
                lathe(b, [(0.0, -0.06), (0.012, -0.06), (0.012, 0.06), (0.0, 0.06)], "black", 8, loc=tuple(P(Ls / 2 - 0.36, zz, -0.004)))
            a, c = P(Ls / 2 + 0.22, 1.0, -0.012), P(Ls / 2 + 0.30, 1.12, -0.004)
            b.box(np.minimum(a, c), np.maximum(a, c), "black")
        else:
            cell = (0.0, 0.0, 0.5, 1.0) if np.dot(n, X) + np.dot(n, Y) * 0.5 > 0 else (0.5, 0.0, 1.0, 1.0)
            if Ls > 1.0:
                atlas_card(b, P(Ls / 2 - 0.3, 1.0, -0.0012), u * 0.6, Z * 0.9, "signKioskPosters", cell, ART.KPOST_M)
    b.box((-hx, -hy, H - 0.04), (hx, hy, H), "roofing", vdir=X)
    b.box((-hx, -hy, H - 0.012), (hx, hy, H), "kiosk")
    b.box((-hx + 0.04, -hy + 0.04, 0.10), (hx - 0.04, hy - 0.04, 0.11), "interior")
    cx, cy, cz = centre
    off = np.array([cx, cy, cz])
    for p in b.parts:
        p["v"] = p["v"] + off
        p["uv_org"] = p["uv_org"] + off
    b.leaks = [tuple(np.asarray(l) + off) for l in b.leaks]
    return done(ctx, b, name, M,
                "Shut sidewalk kiosk (05-level 2.9.4), %.2f x %.2f x 2.50 above the sidewalk: base channel, corner angles, "
                "riveted sheet panels (MI_Steel_KioskGreen #24463a), roll shutter in guides under a hood with bottom bar, "
                "hasp and padlock over a folded counter flap, fascia M_Sign_%s, a padlocked side door, two posters "
                "(M_Sign_KioskPosters), tar-sheet roof. Pivot: footprint centre on the sidewalk." % (w, d, band_key),
                centre, colliders, [(centre, 0.0, colliders)], size=(w, d, 2.5), ground=True, rust=0.3)


FRUIT = {  # kind: (slot, radius, (sx, sy, sz) stretch, heap height)
    "orange": ("fOrange", 0.040, (1, 1, 0.96), 0.10), "apple": ("fRed", 0.037, (1, 1, 0.9), 0.09),
    "appleDark": ("fRedDark", 0.036, (1, 1, 0.9), 0.09), "lemon": ("fYellow", 0.032, (1.35, 1, 1), 0.08),
    "lime": ("fLime", 0.028, (1, 1, 1), 0.07), "pepper": ("fGreen", 0.042, (1, 1, 1.05), 0.08),
    "plum": ("fPurple", 0.027, (1, 1, 1.05), 0.07), "eggplant": ("fPurple", 0.040, (2.4, 1, 1), 0.08),
    "mango": ("fOrange", 0.045, (1.35, 1.0, 0.9), 0.08),
}
ROWS = [["orange", "apple", "lemon", "lime", "plum"], ["appleDark", "mango", "pepper", "lemon", "eggplant"],
        ["lemon", "plum", "orange", "apple", "pepper"]]


def _sphere_tpl(seg=10, rings=7):
    th = np.linspace(0, np.pi, rings + 1)[1:-1]
    ph = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    V = [(0, 0, -1)] + [(math.sin(t) * math.cos(p), math.sin(t) * math.sin(p), -math.cos(t)) for t in th for p in ph] + [(0, 0, 1)]
    F = []
    for j in range(seg):
        F.append([0, 1 + (j + 1) % seg, 1 + j])
    for i in range(rings - 2):
        for j in range(seg):
            a, c = 1 + i * seg + j, 1 + i * seg + (j + 1) % seg
            F.append([a, c, c + seg, a + seg])
    top = len(V) - 1
    base = 1 + (rings - 2) * seg
    for j in range(seg):
        F.append([base + j, base + (j + 1) % seg, top])
    return np.array(V, float), F


_TPL = _sphere_tpl()


def fruit_heap(b, kind, cx, cy, ztop, tilt, rng, w=0.64, d=0.44):
    """One crate's heap: fruit on a domed surface over the crate's opening, tilted toward the front (-y)."""
    slot, r, st, hh = FRUIT[kind]
    V0, F = _TPL
    loops = np.concatenate([np.array(f) for f in F])
    totals = np.array([len(f) for f in F])
    rx = r * st[0] * 2.05
    pts = []
    for j, yy in enumerate(np.arange(-d / 2 + r, d / 2 - r * 0.7, r * st[1] * 1.75)):
        for xx in np.arange(-w / 2 + r * st[0] + (j % 2) * rx / 2, w / 2 - r * st[0] * 0.8, rx):
            pts.append((xx, yy))
    ct, sn = math.cos(tilt), math.sin(tilt)
    for xx, yy in pts:
        u, v = 2 * xx / w, 2 * yy / d
        h = hh * max(0.0, 1 - u * u) ** 0.6 * max(0.0, 1 - v * v) ** 0.6 + rng.uniform(-0.006, 0.006)
        rr = r * rng.uniform(0.88, 1.1)
        Rz = Matrix.Rotation(rng.uniform(0, 6.28), 3, "Z") @ Matrix.Rotation(rng.uniform(-0.4, 0.4), 3, "X")
        R = np.array(Rz)
        Vv = (V0 * np.array(st) * rr) @ R.T
        Vv[:, 2] *= rng.uniform(0.92, 1.02)
        ly, lz = yy, h + rr * st[2] * 0.75
        p = np.array([cx + xx, cy + ly * ct - lz * sn, ztop + ly * sn + lz * ct])
        b._add(Vv + p, loops, totals, slot, None, kind=b.OTHER)
        if kind in ("apple", "appleDark", "orange", "pepper", "mango") and rng.random() < 0.5:
            b.box(p + np.array([-0.003, -0.003, rr * st[2] * 0.95]), p + np.array([0.003, 0.003, rr * st[2] * 0.95 + 0.012]), "fStem", chamfer=0.0)


def crate(b, cx, cy, zb, tilt, rng, W=0.70, D=0.50, Hc=0.22):
    """Slatted produce crate (corner posts, three slats a side, slatted bottom), tilted about x through its base front."""
    sub_ = B(int(rng.integers(1e6)), step=0.3)
    t = 0.012
    for sx in (-1, 1):
        for sy in (-1, 1):
            board(sub_, (sx * W / 2 - (0.04 if sx > 0 else 0), sy * D / 2 - (0.04 if sy > 0 else 0), 0), (sx * W / 2 + (0.0 if sx > 0 else 0.04), sy * D / 2 + (0.0 if sy > 0 else 0.04), Hc), "pallet")
    for k, (z0, z1) in enumerate(((0.01, 0.07), (0.085, 0.145), (0.16, Hc))):
        for sy in (-1, 1):
            y0 = sy * D / 2 - (t if sy > 0 else 0)
            board(sub_, (-W / 2, y0, z0), (W / 2, y0 + t, z1), "pallet")
        for sx in (-1, 1):
            x0 = sx * W / 2 - (t if sx > 0 else 0)
            board(sub_, (x0, -D / 2 + 0.04, z0), (x0 + t, D / 2 - 0.04, z1), "pallet")
    for xx in np.linspace(-W / 2 + 0.06, W / 2 - 0.06, 5):
        board(sub_, (xx - 0.04, -D / 2, 0.0), (xx + 0.04, D / 2, 0.01), "pallet")
    sub_.box((-W / 2 + 0.015, -D / 2 + 0.015, 0.02), (W / 2 - 0.015, D / 2 - 0.015, Hc - 0.03), "interior")
    Mx = np.eye(4)
    ct, sn = math.cos(tilt), math.sin(tilt)
    Mx[1:3, 1:3] = [[ct, -sn], [sn, ct]]
    Mx[:3, 3] = (cx, cy, zb)
    b.merge(sub_, Mx)


def produce_stand(ctx, M):
    b = B(61, step=0.3)
    rng = ctx.rng("produce")
    hw, hd = 1.9, 1.19
    # plywood ends shaped to the tiers, back panel, timber frame
    for sx in (-1, 1):
        xo = sx * (hw - 0.001)
        outline = [(xo, -hd, 0.0), (xo, hd - 0.002, 0.0), (xo, hd - 0.002, 2.30), (xo, 0.45, 2.30), (xo, -0.25, 1.05), (xo, -hd, 0.62)]
        poly(b, outline, 0.018, "plyProduce", np.array([sx, 0, 0.0]), vdir=Z, fdir=Y)
    board(b, (-hw + 0.02, hd - 0.02, 0.0), (hw - 0.02, hd - 0.002, 2.25), "plyProduce", ch=0.002)
    tilt = math.radians(9.0)
    tiers = [(-0.88, 0.28), (-0.31, 0.60), (0.26, 0.92)]
    for ti, (yc, zb) in enumerate(tiers):
        # shelf frame: 2x4 ledgers and legs
        for xx in np.linspace(-hw + 0.06, hw - 0.06, 4):
            for yy in (yc - 0.24, yc + 0.24):
                zz = zb - 0.03 + (yy - (yc - 0.25)) * math.tan(tilt) - 0.02
                board(b, (xx - 0.019, yy - 0.044, 0.0), (xx + 0.019, yy + 0.044, max(0.05, zz)), "plank")
        for yy in (yc - 0.24, yc + 0.24):
            zz = zb - 0.03 + (yy - (yc - 0.25)) * math.tan(tilt)
            board(b, (-hw + 0.02, yy - 0.019, zz - 0.089), (hw - 0.02, yy + 0.019, zz), "plank")
        for ci, kind in enumerate(ROWS[ti]):
            cx = -1.48 + ci * 0.74
            crate(b, cx, yc, zb - 0.03, tilt, rng)
            ct, sn = math.cos(tilt), math.sin(tilt)
            fruit_heap(b, kind, cx, yc - 0.22 * sn, zb - 0.03 + 0.22 * ct - 0.02, tilt, rng)
    # canopy: galvanised pipe frame bracketed to the wall, sagging canvas, valance
    zw, zf = 2.85, 2.25
    for xx in (-hw + 0.05, hw - 0.05):
        pipe(b, [(xx, hd - 0.03, zw), (xx, -hd + 0.03, zf)], 0.021, "galv")
        pipe(b, [(xx, hd - 0.03, zw - 0.55), (xx, hd - 0.55, zw - 0.05)], 0.016, "galv")
        b.box((xx - 0.05, hd - 0.012, zw - 0.62), (xx + 0.05, hd - 0.002, zw + 0.05), "galv")
    rod(b, (-hw + 0.03, -hd + 0.03, zf), (hw - 0.03, -hd + 0.03, zf), 0.021, "galv", n=12)
    rod(b, (-hw + 0.03, hd - 0.03, zw), (hw - 0.03, hd - 0.03, zw), 0.021, "galv", n=12)
    nu, nv = 24, 10
    F = np.zeros((nv, nu, 3))
    for i, v in enumerate(np.linspace(0, 1, nv)):
        for j, u in enumerate(np.linspace(0, 1, nu)):
            xx = -hw + 0.005 + u * (2 * hw - 0.01)
            yy = -hd + 0.01 + v * (2 * hd - 0.03)
            zz = zf + 0.035 + v * (zw - zf) - 0.045 * math.sin(math.pi * u * 2.0 % math.pi) * math.sin(math.pi * v)
            F[i, j] = (xx, yy, zz)
    sheet(b, F, 0.003, "canvas")
    for k in range(13):                                             # scalloped valance
        x0 = -hw + 0.005 + k * (2 * hw - 0.01) / 13
        x1 = x0 + (2 * hw - 0.01) / 13
        Fv = np.array([[(x0 + (x1 - x0) * u, -hd + 0.006, zf + 0.04 - (0.20 + 0.04 * math.sin(math.pi * u)) * vv) for u in np.linspace(0, 1, 5)]
                       for vv in np.linspace(0, 1, 3)])
        sheet(b, Fv, 0.003, "canvas")
    # spring scale with pan on chains
    sx_, sy_ = 0.55, -1.05
    pipe(b, [(sx_, -hd + 0.03, zf - 0.02), (sx_, sy_, zf - 0.10), (sx_, sy_, zf - 0.16)], 0.004, "steel", bend=0.02)
    lathe(b, [(0.0, -0.035), (0.10, -0.035), (0.105, -0.03), (0.105, 0.03), (0.10, 0.035), (0.0, 0.035)], "white", 28,
          loc=(sx_, sy_, zf - 0.27), rot=(90, 0, 0))
    card(b, (sx_ - 0.09, sy_ - 0.0365, zf - 0.36), (0.18, 0, 0), (0, 0, 0.18), "signScaleDial", sign=True)
    sign_tile(M, "ScaleDial", 0.18, 0.18)
    zp = 1.42
    for a in (0, 2.09, 4.19):
        pipe(b, [(sx_, sy_, zf - 0.38), (sx_ + 0.15 * math.cos(a), sy_ + 0.15 * math.sin(a), zp + 0.03)], 0.0025, "steel")
    lathe(b, [(0.0, zp - 0.04), (0.12, zp - 0.035), (0.17, zp + 0.0), (0.18, zp + 0.03), (0.172, zp + 0.03), (0.162, zp + 0.005),
              (0.11, zp - 0.028), (0.0, zp - 0.032)], "chrome", 32, loc=(sx_, sy_, 0))
    # price cards on wire sticks in the heaps
    for i in range(10):
        ti, ci = i % 3, i % 5
        yc, zb = tiers[ti]
        cx = -1.48 + ci * 0.74 + rng.uniform(-0.15, 0.15)
        yy = yc - 0.30
        zz = zb + 0.24 + 0.05
        rod(b, (cx, yy, zz - 0.1), (cx, yy, zz), 0.0018, "steel", n=4)
        cell = ((i % 5) / 5, 1 - (i // 5 + 1) / 2, (i % 5 + 1) / 5, 1 - (i // 5) / 2)
        atlas_card(b, (cx - 0.06, yy - 0.002, zz), (0.12, 0, 0), (0, -0.02, 0.118), "signPriceCards", cell, ART.PRICE_M)
    # two bare bulbs on cords
    for bx_ in (-0.9, 0.9):
        p0 = (bx_, -0.2, zf + 0.33)
        rod(b, p0, (bx_, -0.2, 2.13), 0.004, "cord", n=6)
        lathe(b, [(0.0, 2.13), (0.02, 2.13), (0.021, 2.08), (0.0, 2.08)], "black", 12, loc=(bx_, -0.2, 0))
        lathe(b, [(0.0, 2.08), (0.014, 2.08), (0.03, 2.05), (0.033, 2.02), (0.024, 1.99), (0.0, 1.985)], "lensWarm", 16, loc=(bx_, -0.2, 0))
    centre = (13.3, 9.79, 0.15)
    off = np.array(centre)
    for p in b.parts:
        p["v"] = p["v"] + off
        p["uv_org"] = p["uv_org"] + off
    allow = [((11.4, 8.5, 0.15), (15.2, 10.98, 3.05))]
    return done(ctx, b, "SM_Struct_ProduceStand", M,
                "Produce stand against the deli (05-level 2.9.4), 3.8 x 2.38: green plywood ends shaped to the tiers and a back "
                "panel, three tiers of 2x4 frames carrying 15 slatted crates tilted 9 degrees (tops 0.5, 0.82, 1.14), modelled "
                "heaps of oranges, apples, lemons, limes, plums, mangoes, peppers and eggplants (flat MI_Fruit_* slots), a "
                "green canvas canopy on a galvanised pipe frame sloping 3.0 -> 2.4 with a scalloped valance, a spring scale "
                "with dial (M_Sign_ScaleDial) and chrome pan, ten price cards on wire sticks (M_Sign_PriceCards), two bare bulbs "
                "(MI_Lamp_BulbWarm). Pivot: footprint centre on the sidewalk. The canopy above the 2.5 box is overhead.",
                centre, [561], [(centre, 0.0, [561])], allow=allow, ground=True, ao=0.06)


# ================================================================================================== HOARDINGS

def hoarding_run(b, L, H, slot, rng, posters=(), signs=(), stencil=None):
    """Local frame: x 0..L, collider face at y = 0 looking -Y, back at y = 0.08, base z = 0."""
    yf = 0.012
    xs = list(np.arange(0.0, L, 1.22)) + [L]
    for x0, x1 in zip(xs[:-1], xs[1:]):
        if x1 - x0 < 0.02:
            continue
        b.box((x0 + 0.0015, yf, 0.015), (x1 - 0.0015, yf + 0.018, H - 0.06), slot, vdir=Z, fdir=X, chamfer=0.0015)
    for zz in (0.30, H / 2, H - 0.40):
        board(b, (0.0, yf + 0.018, zz), (L, yf + 0.056, zz + 0.089), "plank")
    for xp in list(np.arange(0.0, L - 0.05, 2.44)) + [L - 0.09]:
        board(b, (xp, yf + 0.018, 0.0), (xp + 0.09, 0.08, H - 0.06), "plank")
    board(b, (0.0, 0.0, H - 0.06), (L, 0.08, H), "plank")
    for xp in np.arange(0.3, L, 0.4):                                      # nail heads in rows on the nailers
        for zz in (0.345, H / 2 + 0.045, H - 0.355):
            if rng.random() < 0.7:
                b.box((xp - 0.004, yf - 0.0012, zz - 0.004), (xp + 0.004, yf, zz + 0.004), "steel", chamfer=0.0)
    for k, (x, z, key, rot) in enumerate(posters):
        cell = ART.FLY[key]
        w, h = 0.6, 0.9
        a = math.radians(rot)
        du = np.array([w * math.cos(a), 0, w * math.sin(a)])
        dv = np.array([-h * math.sin(a), 0, h * math.cos(a)])
        atlas_card(b, (x, yf - 0.0006 - 0.0004 * (k % 3), z), du, dv, "signFlyPosters", cell, ART.FLY_M)
    for x, z, w, h, key in signs:
        b.box((x, 0.002, z), (x + w, yf, z + h), "steel")
        card(b, (x, 0.0015, z), (w, 0, 0), (0, 0, h), "sign" + key, sign=True)
    if stencil:
        x, z = stencil
        card(b, (x, yf - 0.0003, z), (1.5, 0, 0), (0, 0, 0.24), "signPostNoBills", sign=True)


def hoardings(ctx, M):
    rng = ctx.rng("hoardings")
    sign_tile(M, "PostNoBills", 1.5, 0.24)
    sign_tile(M, "RoadClosed", 3.4, 1.05)
    out = []
    kinds = list(ART.FLY)
    # (name, collider, L, H, z base, Blender pivot, yaw, posters?, signs, stencil, note)
    runs = [
        ("SM_Struct_Hoarding_WestS", 467, 4.0, 2.55, 0.15, (-45.26, 7.0, 0.15), 90.0, 3, [], None, "west closure on the south sidewalk"),
        ("SM_Struct_Hoarding_WestRoad", 468, 14.0, 2.70, 0.0, (-45.26, -7.0, 0.0), 90.0, 3,
         [(7.0 - 3.4 - 1.7 - 1.0, 1.225, 3.4, 1.05, "RoadClosed"), (7.0 + 2.6 - 1.7, 1.225, 3.4, 1.05, "RoadClosed")], None,
         "west closure across the road, the two ROAD CLOSED boards at web z 3.4 and -2.6"),
        ("SM_Struct_Hoarding_WestN", 469, 4.0, 2.55, 0.15, (-45.26, -11.0, 0.15), 90.0, 0, [], None, "west closure on the north sidewalk"),
        ("SM_Struct_Hoarding_LotW", 370, 4.1, 2.55, 0.0, (-11.9, -11.1, 0.0), 180.0, 5, [], (1.3, 2.18), "vacant lot, west of the gateway"),
        ("SM_Struct_Hoarding_LotE", 371, 4.7, 2.55, 0.0, (-4.0, -11.1, 0.0), 180.0, 6, [], (1.6, 2.18), "vacant lot, east of the gateway"),
    ]
    for name, ci, L, H, zb, piv, yaw, npost, signs, sten, note in runs:
        b = B(70 + ci, step=0.4)
        posters, x = [], 0.25
        for k in range(npost):
            if x + 0.6 > L - 0.1:
                break
            posters.append((x, rng.uniform(0.75, 1.05), kinds[(ci + k) % len(kinds)], rng.uniform(-2.5, 2.5)))
            if rng.random() < 0.4 and x + 0.9 < L:                          # pasted over half the last one
                posters.append((x + 0.3, rng.uniform(0.85, 1.2), kinds[(ci + 3 * k + 1) % len(kinds)], rng.uniform(-3, 3)))
            x += rng.uniform(0.62, 0.9)
        hoarding_run(b, L, H, "plyGreen", rng, posters, signs, sten)
        Mx = np.array(Matrix.Translation(piv) @ Matrix.Rotation(math.radians(yaw), 4, "Z"))
        out.append(done(ctx, b, name, M,
                        "Plywood hoarding, %s (05-level 2.9.1 / 2.10.4): %.2f m long, %.2f high, 8 cm deep: 18 mm hunter-green "
                        "sheets on 2x4 nailers and 9 cm posts every 2.44 m on the back, a timber cap rail, nail heads, fly-posters "
                        "from the atlas M_Sign_FlyPosters (fictional bills), stencil M_Sign_PostNoBills where the spec has it. "
                        "Wall module: pivot bottom-left of the outer face, running +X, face -Y." % (note, L, H),
                        piv, [ci], [(piv, yaw, [ci])], ground=True, xf=Mx))
    return out


def dig_pen(ctx, M):
    b = B(80, step=0.4)
    rng = ctx.rng("dig")
    H = 2.20
    sign_tile(M, "DigDanger", 0.9, 0.6)
    # four walls, faces outward: kerb side (y 7.0, face -y), wall side (y 9.24, face +y), ends (x 17.76, face -x; 21.24, face +x)
    walls = [((17.8, 7.0, 0.15), 0.0, 3.4, [(1.25, 1.0, 0.9, 0.6, "DigDanger")]),
             ((21.2, 9.24, 0.15), 180.0, 3.4, []),
             ((17.76, 9.2, 0.15), -90.0, 2.16, [(0.63, 1.0, 0.9, 0.6, "DigDanger")]),
             ((21.24, 7.04, 0.15), 90.0, 2.16, [])]
    for piv, yaw, L, signs in walls:
        w = B(int(yaw) + 900, step=0.4)
        hoarding_run(w, L, H, "plyOrange", rng, [], signs, None)
        Mx = np.array(Matrix.Translation(piv) @ Matrix.Rotation(math.radians(yaw), 4, "Z"))
        b.merge(w, Mx)
    # the open vault inside, a plate cover pushed aside
    b.box((17.86, 7.10, 0.15), (21.14, 9.14, 0.16), "interior")
    b.box((18.0, 8.4, 0.16), (19.2, 9.0, 0.18), "steel", chamfer=0.004)
    # steam stack: nine orange and white rings, 0.4 high each
    for k in range(9):
        z0 = 0.15 + k * 0.4
        lathe(b, [(0.17, z0), (0.199, z0 + 0.01), (0.197, z0 + 0.36), (0.19, z0 + 0.39), (0.17, z0 + 0.40), (0.165, z0 + 0.40),
                  (0.165, z0 + 0.002)], "pOrange" if k % 2 == 0 else "pWhite", 36, loc=(19.5, 8.1, 0), closed=True)
    allow = []
    return done(ctx, b, "SM_Struct_DigPen", M,
                "Utility dig (05-level 2.9.4): an orange plywood pen 3.48 x 2.24 x 2.2 (MI_Plywood_DigOrange, the hoarding "
                "construction), two DANGER / STEAM KEEP OUT boards, the open vault inside with a plate pushed aside, and the "
                "steam stack of nine orange and white rings r 0.2 from 0.15 to 3.75 at (19.5, -8.1 web). Pivot: footprint "
                "centre on the sidewalk.", (19.5, 8.12, 0.15), [562, 563, 564, 565, 566, 567],
                [((19.5, 8.12, 0.15), 0.0, [562, 563, 564, 565, 566, 567])], allow=allow, ground=True)


# =============================================================================================== DOCK AND GARAGES

def loading_dock(ctx, M):
    b = B(90, step=0.3)
    yf, yb = -27.41, -26.0
    sign_tile(M, "LoadingZone", 1.6, 0.6)
    b.box((6.4, yf, 0.0), (12.4, yb, 0.98), "concFormed", vdir=Z)
    b.box((6.4, yf, 0.98), (12.4, yb, 1.0), "concTop", vdir=X)
    b.prism(steel.angle(0.10, 0.10, 0.009), (6.4, yf, 1.0), Y, -Z, (6.0, 0, 0), "yellow")                 # edge angle
    b.prism(steel.angle(0.08, 0.08, 0.008), (6.4, yf, 1.0), X, -Z, (0, yb - yf, 0), "yellow")
    for xb in (7.4, 9.4, 11.4):
        b.box((xb - 0.16, yf - 0.01, 0.43), (xb + 0.16, yf, 0.92), "black")
        for k in range(6):
            b.box((xb - 0.15, -27.5, 0.45 + k * 0.075), (xb + 0.15, yf - 0.01, 0.45 + k * 0.075 + 0.07), "rubber", chamfer=0.006)
        for zz in (0.50, 0.85):
            lathe(b, [(0.0, 0.0), (0.016, 0.0), (0.016, 0.008), (0.0, 0.01)], "steel", 6, loc=(xb, -27.5, zz), rot=(90, 0, 0))
    for i in range(4):
        x0 = 5.4 + 0.25 * i
        zt = 0.25 * (i + 1)
        b.box((x0, -27.5, 0.0), (6.4, yb, zt), "concFormed", vdir=Z)
        b.prism(steel.angle(0.05, 0.05, 0.006), (x0, -27.5, zt), X, -Z, (0, 1.5, 0), "rail")
    # roll shutter above the dock on S3's back wall
    yw = yb
    b.box((7.45, yw - 0.36, 3.50), (11.35, yw, 3.88), "grey")
    for xg in (7.55, 11.25):
        b.box((xg - 0.05, yw - 0.09, 1.0), (xg + 0.05, yw, 3.5), "black")
    b.box((7.6, yw - 0.05, 1.03), (11.2, yw - 0.035, 3.5), "shutter", vdir=Z, fdir=X)
    b.box((7.6, yw - 0.07, 1.0), (11.2, yw - 0.03, 1.07), "black")
    for xh in (8.2, 10.6):
        b.box((xh - 0.06, yw - 0.10, 1.10), (xh + 0.06, yw - 0.07, 1.16), "black")
    card(b, (16.8, yw - 0.002, 1.2), (-1.6, 0, 0), (0, 0, 0.6), "signLoadingZone", sign=True)
    allow = [((5.4, -27.5, 0.0), (17.0, -25.95, 3.9))]
    return done(ctx, b, "SM_Struct_LoadingDock", M,
                "Loading dock on the back of S3 (05-level 2.10.5): formed-concrete platform 6 x 1.5 x 1.0 with a worn slab "
                "top, yellow steel edge angles, three laminated rubber bumpers (flush with the collider face), four concrete "
                "steps with steel nosings at its west end; the roll shutter over it on the wall (hood, guides, slat curtain, "
                "bottom bar, handles) and the NO PARKING / LOADING ZONE stencil at x 16 (M_Sign_LoadingZone). Pivot: west end "
                "of the steps' front, ground.", (5.4, -27.5, 0.0), [396, 397, 398, 399, 400],
                [((5.4, -27.5, 0.0), 0.0, [396, 397, 398, 399, 400])], allow=allow, ground=True)


def garages(ctx, M):
    b = B(95, step=0.4)
    rng = ctx.rng("garages")
    yb_, yf = -31.12, -31.42                                   # brick face, back of the front wall
    doors = [-13.6 + 4.4 * k for k in range(8)]
    holes = [(c - 1.7, c + 1.7, 0.0, 2.75) for c in doors]
    for x0, x1, z0, z1 in cells(-16.0, 22.0, 0.0, 3.80, holes):
        b.box((x0, yf, z0), (x1, yb_, z1), "brickGarage", vdir=Z, fdir=X, uv_off=(0.0, 0.0))
    for k, c in enumerate(doors):
        b.box((c - 1.85, yb_, 2.75), (c + 1.85, -31.0, 3.0), "concRough", vdir=Z)                       # lintel
        for sx in (-1, 1):
            b.box((c + sx * 1.7 - 0.04, -31.30, 0.0), (c + sx * 1.7 + 0.04, -31.24, 2.75), "black")      # guides
        slot = "garage" if rng.random() < 0.6 else "shutter"
        b.box((c - 1.66, -31.30, 0.02), (c + 1.66, -31.27, 2.75), slot, vdir=Z, fdir=X)
        b.box((c - 1.66, -31.32, 0.0), (c + 1.66, -31.26, 0.08), "black")
        for sx in (-0.9, 0.9):
            b.box((c + sx - 0.07, -31.25, 0.10), (c + sx + 0.07, -31.23, 0.16), "black")
        b.box((c - 0.05, -31.25, 0.06), (c + 0.05, -31.22, 0.18), "black")
        lathe(b, [(0.0, -0.03), (0.025, -0.03), (0.027, 0.03), (0.0, 0.03)], "brass", 12, loc=(c, -31.20, 0.05))
        cell = ((k % 4) / 4, 1 - (k // 4 + 1) / 2, (k % 4 + 1) / 4, 1 - (k // 4) / 2)
        atlas_card(b, (c - 0.35, yb_ + 0.0012, 3.09), (0.7, 0, 0), (0, 0, 0.42), "signGarageNumbers", cell, ART.GARAGE_M)
    for xl in (-7.1, 6.1, 19.3):                               # caged jelly-jar lamps
        b.box((xl - 0.06, yb_, 2.88), (xl + 0.06, yb_ + 0.02, 3.12), "black")
        lathe(b, [(0.0, 0.0), (0.05, 0.0), (0.055, 0.02), (0.0, 0.02)], "black", 16, loc=(xl, yb_ + 0.02, 3.0), rot=(-90, 0, 0))
        lathe(b, [(0.0, 0.02), (0.045, 0.02), (0.05, 0.06), (0.045, 0.1), (0.0, 0.105)], "lensWarm", 16, loc=(xl, yb_ + 0.0, 3.0), rot=(-90, 0, 0))
        for a in range(4):
            ang = a * math.pi / 2 + 0.785
            rod(b, (xl + 0.055 * math.cos(ang), yb_ + 0.02, 3.0 + 0.055 * math.sin(ang)),
                (xl + 0.055 * math.cos(ang), yb_ + 0.115, 3.0 + 0.055 * math.sin(ang)), 0.003, "black", n=4)
    b.box((-16.0, -31.50, 3.80), (22.0, -31.08, 4.10), "coping", vdir=X)
    for x0, x1 in ((-16.0, -15.7), (21.7, 22.0)):
        b.box((x0, -34.0, 0.0), (x1, yf, 3.80), "brickGarage", vdir=Z, fdir=Y, uv_off=(0.0, 0.0))
        b.box((x0 - (0.0 if x0 < 0 else 0.0), -34.0, 3.80), (x1, -31.50, 4.10), "coping", vdir=Y)
    b.box((-15.7, -34.0, 0.0), (21.7, -33.7, 3.80), "brickGarage", vdir=Z, fdir=X, uv_off=(0.0, 0.0))
    b.box((-15.7, -33.7, 3.55), (21.7, yf, 3.70), "roof", vdir=X)
    pipe(b, [(21.55, -31.07, 3.70), (21.55, -31.07, 0.25), (21.55, -31.045, 0.08)], 0.045, "galv", bend=0.06)
    b.box((21.45, yb_, 3.58), (21.65, -31.02, 3.78), "galv")
    allow = []
    return done(ctx, b, "SM_Struct_Garages", M,
                "The row of garages on the rear lane (05-level 2.5.4), x -16..22: painted brick (MI_BrickPainted_Garages "
                "#b9b4a6, world-aligned UVs) with eight closed roll doors 3.4 x 2.75 (ribbed rust or grey slats, guides, bottom "
                "bar, lift handles, hasp and padlock) under concrete lintels 3.7 wide flush with the collider face, numbers 41-48 "
                "(M_Sign_GarageNumbers), caged lamps right of doors 2, 5 and 8, a concrete coping 3.8..4.1, end walls, a "
                "bitumen roof behind the coping, a downpipe and scupper at the gable. Pivot: the west end of the front, ground.",
                (-16.0, -31.0, 0.0), [188], [((-16.0, -31.0, 0.0), 0.0, [188])], allow=allow, ground=True)


# =========================================================================================== THE CHOP SHOP INSIDE

SKY = [(-18.5, 19.5), (-9.0, 24.5), (-9.0, 15.5), (0.5, 20.5)]
WORK = [(-18.2, 17.2), (-9.2, 22.4), (-9.2, 14.6), (0.6, 21.2)]
OIL = [(-19.2, 17.3), (-12.3, 15.6), (-1.3, 19.6), (-9.0, 24.0), (-4.5, 13.2), (2.8, 24.5), (-15.5, 21.8), (-7.6, 27.8)]


def shop_floor(ctx, M):
    b = B(100, step=0.2)
    rng = ctx.rng("floor")
    xs = np.linspace(-23.6, 5.6, 7)
    ys = np.linspace(11.4, 30.6, 5)
    for i in range(6):
        for j in range(4):
            b.box((xs[i] + 0.003, ys[j] + 0.003, -0.15), (xs[i + 1] - 0.003, ys[j + 1] - 0.003, 0.0), "floor", chamfer=0.002, uv_off=(0.0, 0.0))
    b.box((-23.6, 11.4, -0.16), (5.6, 30.6, -0.004), "interior")                 # joint sealant under the gaps
    for x0, x1, y0, y1 in ((-15.0, -9.0, 11.0, 11.4), (-3.2, 0.6, 11.0, 11.4), (5.6, 6.0, 21.1, 23.1)):
        b.box((x0, y0, -0.15), (x1, y1, 0.0), "floor", chamfer=0.002, uv_off=(0.0, 0.0))
    for x0, x1, y0, y1 in ((-15.0, -9.0, 11.0, 11.05), (-3.2, 0.6, 11.0, 11.05), (5.95, 6.0, 21.1, 23.1)):
        b.box((x0, y0, -0.01), (x1, y1, 0.003), "steel")
    # yellow bay outlines (north edge and both sides, open toward the avenue)
    for (x0, x1, za, zb_) in ((-21.6, -16.8, -20.4, -14.2), (-3.4, 0.8, -22.6, -16.6), (-14.6, -9.4, -18.4, -12.4)):
        y0, y1 = -zb_, -za
        for lo, hi in (((x0, y1 - 0.10), (x1, y1)), ((x0, y0), (x0 + 0.10, y1)), ((x1 - 0.10, y0), (x1, y1))):
            b.box((lo[0], lo[1], 0.0), (hi[0], hi[1], 0.0015), "floorPaint", chamfer=0.0)
    # floor drain: frame, bars over a dark sump
    dx0, dx1, dy0, dy1 = -5.2, -4.5, 16.6, 17.3
    b.box((dx0 + 0.03, dy0 + 0.03, 0.0), (dx1 - 0.03, dy1 - 0.03, 0.0008), "interior")
    for lo, hi in (((dx0, dy0), (dx1, dy0 + 0.03)), ((dx0, dy1 - 0.03), (dx1, dy1)), ((dx0, dy0), (dx0 + 0.03, dy1)), ((dx1 - 0.03, dy0), (dx1, dy1))):
        b.box((lo[0], lo[1], 0.0), (hi[0], hi[1], 0.004), "steel", chamfer=0.0)
    for xx in np.arange(dx0 + 0.06, dx1 - 0.04, 0.035):
        b.box((xx - 0.006, dy0 + 0.03, 0.0), (xx + 0.006, dy1 - 0.03, 0.004), "steel", chamfer=0.0)
    # oil-stain decals over the spec's eight spots
    sign_tile(M, "OilStain", 1.0, 1.0)
    for k, (x, z) in enumerate(OIL):
        s = rng.uniform(1.2, 2.0)
        a = rng.uniform(0, math.pi)
        du = np.array([math.cos(a), math.sin(a), 0]) * s
        dv = np.array([-math.sin(a), math.cos(a), 0]) * s * rng.uniform(0.7, 1.0)
        o = np.array([x, z, 0.002 + 0.0004 * k]) - du / 2 - dv / 2
        card(b, o, du, dv, "signOilStain", sign=True)
    spots = np.array([(x, z) for x, z in OIL])

    def oil(W, R, G, Bk, A):
        P = W.P
        d = np.min(np.linalg.norm(P[:, None, :2] - spots[None], axis=2), axis=1)
        n = Waves(ctx.rng("oil"), 0.6).u(P[:, 0], P[:, 1])
        on = (P[:, 2] > -0.001) & (W.N[:, 2] > 0.9)
        Bk = np.where(on, np.clip(np.exp(-(d / (1.4 + 0.3 * n)) ** 2) * 0.95 + 0.25 * sstep(0.8, 1.6, n), 0, 1), Bk)
        A = np.where(on, np.clip(np.exp(-(d / 0.6) ** 2) * 0.6 + 0.5 * np.exp(-(np.hypot(P[:, 0] + 4.85, P[:, 1] - 16.95) / 1.2) ** 2), 0, 1), A)
        lane = np.exp(-((P[:, 0] + 12) / 3.0) ** 2) * sstep(26.0, 12.0, P[:, 1])
        R = np.where(on, np.clip(0.10 + 0.25 * lane + 0.12 * n + 0.35 * sstep(1.5, 0.2, np.minimum.reduce([P[:, 0] + 23.6, 5.6 - P[:, 0], P[:, 1] - 11.4, 30.6 - P[:, 1]])), 0, 1), R)
        return R, G, Bk, A
    allow = [((-23.6, 11.0, -0.2), (6.0, 30.6, 0.01))]
    return done(ctx, b, "SM_Struct_ShopFloor", M,
                "V&R Auto Body floor (05-level 2.6.1): sealed garage concrete (MI_Floor_ScanGarage) in 24 cast panels with "
                "6 mm saw-cut joints, out through the three door openings to steel threshold angles; yellow bay outlines "
                "(MI_FloorPaint_Yellow); a 0.7 m drain grate over a dark sump; oil: the Wear mask's B (dark, glossy) and A (wet "
                "sheen) round the eight spec spots and tyre grime (R) along the lanes, plus eight alpha decal cards "
                "M_Sign_OilStain. Top at z 0 (the ground); no collider of its own. Pivot: the shop's north-west inside corner.",
                (-23.6, 30.6, 0.0), [], [((-23.6, 30.6, 0.0), 0.0, [])], allow=allow, ground=False, ao=None, extra=oil, fit=False)


def ow_joist(b, x, y0, y1, zb=5.55, zt=5.962, supports=()):
    """Open-web steel joist along y at x: double-angle chords, round-bar web, bearing shoes."""
    L = y1 - y0
    for sx in (-1, 1):
        b.prism(steel.angle(0.05, 0.05, 0.006), (x + sx * 0.006, y0, zt), np.array([sx, 0, 0.0]), -Z, (0, L, 0), "grey")
        b.prism(steel.angle(0.045, 0.045, 0.005), (x + sx * 0.006, y0 + 0.3, zb), np.array([sx, 0, 0.0]), Z, (0, L - 0.6, 0), "grey")
    pts = np.arange(y0 + 0.3, y1 - 0.25, 0.55)
    for i in range(len(pts) - 1):
        za, zb2 = (zb + 0.03, zt - 0.05) if i % 2 == 0 else (zt - 0.05, zb + 0.03)
        rod(b, (x, pts[i], za), (x, pts[i + 1], zb2), 0.011, "grey", n=8)
    for yy in (y0, y1 - 0.30):
        b.box((x - 0.06, yy, zt - 0.11), (x + 0.06, yy + 0.30, zt - 0.05), "grey")
    for yy in supports:
        b.box((x - 0.14, yy - 0.14, zb - 0.02), (x + 0.14, yy + 0.14, zb), "grey")


def shop_roof(ctx, M):
    b = B(110, step=0.5)
    x0, x1, y0, y1 = -23.6, 5.6, 11.4, 30.6
    holes = [(cx - 1.2, cx + 1.2, cy - 1.7, cy + 1.7) for cx, cy in SKY]
    # ribbed deck (1.5 in ribs at 6 in), strips between the skylights, ribs running north-south
    pitch, dep = 0.1524, 0.038
    for c0, c1, d0, d1 in cells(x0, x1, y0, y1, holes):
        n = max(1, int(round((c1 - c0) / pitch)))
        p = (c1 - c0) / n
        prof = []
        for k in range(n):
            a = c0 + k * p
            prof += [(a, 6.0 - 0.004), (a + 0.25 * p, 6.0 - 0.004), (a + 0.35 * p, 6.0 - dep), (a + 0.65 * p, 6.0 - dep), (a + 0.75 * p, 6.0 - 0.004)]
        prof += [(c1, 6.0 - 0.004), (c1, 6.0), (c0, 6.0)]
        b.prism([(px, pz) for px, pz in prof], (0.0, d0, 0.0), X, Z, (0, d1 - d0, 0), "deck", step=1.0, pstep=0.5, vdir=Y)
    for c0, c1, d0, d1 in cells(x0 - 0.38, x1 + 0.38, y0 - 0.38, y1 + 0.38, holes):
        b.box((c0, d0, 6.0), (c1, d1, 6.29), "interior")
        b.box((c0, d0, 6.29), (c1, d1, 6.30), "roof", vdir=X, uv_off=(0.0, 0.0))
    # skylights: light-well linings, galvanised kerbs above the roof, wired glass in a steel grid
    for cx, cy in SKY:
        for (a0, a1, d0, d1) in ((cx - 1.2, cx + 1.2, cy - 1.7, cy - 1.69), (cx - 1.2, cx + 1.2, cy + 1.69, cy + 1.7),
                                 (cx - 1.2, cx - 1.19, cy - 1.7, cy + 1.7), (cx + 1.19, cx + 1.2, cy - 1.7, cy + 1.7)):
            b.box((a0, d0, 5.96), (a1, d1, 6.30), "galv")
        for (a0, a1, d0, d1) in ((cx - 1.35, cx + 1.35, cy - 1.85, cy - 1.7), (cx - 1.35, cx + 1.35, cy + 1.7, cy + 1.85),
                                 (cx - 1.35, cx - 1.2, cy - 1.7, cy + 1.7), (cx + 1.2, cx + 1.35, cy - 1.7, cy + 1.7)):
            b.box((a0, d0, 6.30), (a1, d1, 6.60), "galv")
        b.box((cx - 1.2, cy - 1.7, 6.585), (cx + 1.2, cy + 1.7, 6.592), "glassSky")
        for xx in (cx - 1.2, cx, cx + 1.2):
            b.box((xx - 0.02, cy - 1.7, 6.56), (xx + 0.02, cy + 1.7, 6.61), "grey")
        for yy in (cy - 1.7, cy, cy + 1.7):
            b.box((cx - 1.2, yy - 0.02, 6.56), (cx + 1.2, yy + 0.02, 6.61), "grey")
    # open-web joists bearing on the walls and on the two columns, purlins framed between them
    for xj in (-18.0, -12.0, -6.0, 0.0):
        ow_joist(b, xj, y0, y1, supports=(21.0,) if xj in (-18.0, -6.0) else ())
    for yp in (27.0, 22.6, 18.2, 13.8):
        b.prism(steel.channel(0.16, 0.06, 0.006, 0.005), (x0, yp - 0.03, 5.80), Y, Z, (x1 - x0, 0, 0), "grey")
        b.prism([(0, 0), (0.03, 0), (0.03, 0.03), (0, 0.03)], (x0, yp + 0.05, 5.76), Y, Z, (x1 - x0, 0, 0), "steel", caps=True)  # conduit run
    # high-bay lamps: conduit drop, ballast, spun shade, glowing disc
    for lx, lz in WORK:
        ly = lz
        rod(b, (lx, ly, 5.34), (lx, ly, 5.962), 0.012, "galv", n=8)
        yp = min((27.0, 22.6, 18.2, 13.8), key=lambda v: abs(v - ly))
        rod(b, (lx, ly, 5.77), (lx, yp + 0.065, 5.77), 0.012, "galv", n=8)
        lathe(b, [(0.0, 5.50), (0.09, 5.50), (0.10, 5.46), (0.10, 5.36), (0.08, 5.34), (0.0, 5.34)], "grey", 24, loc=(lx, ly, 0))
        lathe(b, [(0.11, 5.34), (0.16, 5.30), (0.28, 5.17), (0.36, 5.08), (0.365, 5.075), (0.355, 5.075), (0.275, 5.16), (0.155, 5.29),
                  (0.105, 5.33)], "alu", 40, loc=(lx, ly, 0), closed=True)
        lathe(b, [(0.0, 5.06), (0.24, 5.06), (0.24, 5.10), (0.0, 5.10)], "lampWork", 32, loc=(lx, ly, 0))
    # vent stack on the roof
    lathe(b, [(0.21, 5.96), (0.22, 5.96), (0.22, 7.55), (0.21, 7.55)], "galv", 32, loc=(-3.0, 27.5, 0), closed=True)
    lathe(b, [(0.0, 7.62), (0.34, 7.70), (0.33, 7.73), (0.0, 7.88)], "galv", 32, loc=(-3.0, 27.5, 0))
    for a in range(3):
        ang = a * 2.094
        rod(b, (-3.0 + 0.2 * math.cos(ang), 27.5 + 0.2 * math.sin(ang), 7.5), (-3.0 + 0.3 * math.cos(ang), 27.5 + 0.3 * math.sin(ang), 7.71), 0.008, "galv", n=6)
    lathe(b, [(0.22, 6.30), (0.40, 6.30), (0.23, 6.45), (0.22, 6.45)], "galv", 32, loc=(-3.0, 27.5, 0), closed=True)
    allow = [((x0 - 0.1, y0 - 0.1, 5.0), (x1 + 0.1, y1 + 0.1, 6.0)),                      # steel and lamps under the slab
             ((x0, y0, 6.3), (x1, y1, 7.9))]                                               # kerbs and stack on the roof
    return done(ctx, b, "SM_Struct_ShopRoof", M,
                "V&R Auto Body roof (05-level 2.6.2-2.6.3): 1.5 in ribbed galvanised deck (MI_Corrugated_ScanGalv) under a slab "
                "to 6.30 with a bitumen top; four skylights 2.4 x 3.4 (lined light wells, galvanised kerbs 2.7 x 3.7 x 0.3 on the "
                "roof, wired glass MI_Glass_Skylight in a steel grid at x -1.2/0/+1.2, y -1.7/0/+1.7); four open-web joists at "
                "x -18, -12, -6, 0 (double-angle chords, round-bar web, bearing shoes; 5.55..5.96, on the columns at y 21 web "
                "-21), C purlins framed between them at web z -27, -22.6, -18.2, -13.8 with conduit runs, four high-bay lamps "
                "(conduit drop, ballast, spun shade, glowing disc MI_Lamp_HighBay), the galvanised vent stack with a rain cap. "
                "The collider (201) is continuous: nothing passes a skylight. Pivot: the shop's north-west inside corner at 0.",
                (-23.6, 30.6, 0.0), [201], [((-23.6, 30.6, 0.0), 0.0, [201])], allow=allow, ground=False, ao=None)


def shop_column(ctx, M):
    b = B(120, step=0.3)
    h = 0.14
    b.box((-h, -h, 0.0), (h, h, 0.025), "grey")
    for sx in (-1, 1):
        for sy in (-1, 1):
            lathe(b, [(0.0, 0.025), (0.018, 0.025), (0.018, 0.045), (0.0, 0.05)], "grey", 6, loc=(sx * 0.105, sy * 0.105, 0))
    for sx in (-1, 1):
        b.box((sx * 0.13 - 0.008, -0.13, 0.025), (sx * 0.13 + 0.008, 0.13, 5.53), "grey")
    b.box((-0.122, -0.006, 0.025), (0.122, 0.006, 5.53), "grey")
    b.box((-h, -h, 5.53), (h, h, 5.55), "grey")
    for z0, z1 in ((0.025, 1.2),):
        for sx in (-1, 1):
            b.box((sx * h - (0.006 if sx > 0 else 0), -h, z0), (sx * h + (0.0 if sx > 0 else 0.006), h, z1), "yellow")
            b.box((-h, sx * h - (0.006 if sx > 0 else 0), z0), (h, sx * h + (0.0 if sx > 0 else 0.006), z1), "yellow")
        b.box((-h, -h, z1 - 0.006), (h, h, z1), "yellow")
    places = [((x, -z, 0.0), 0.0, [i]) for (x, z), i in (((-18.0, -21.0), 202), ((-6.0, -21.0), 203))]
    b2 = B(0)
    b2.merge(b, np.array(Matrix.Translation((-18.0, 21.0, 0.0))))
    return done(ctx, b2, "SM_Struct_ShopColumn", M,
                "Shop roof column (05-level 2.6.3): wide-flange 0.26 x 0.26 on a 0.28 base plate with four anchor nuts, cap "
                "plate at 5.55 under the joist, a yellow sheet-steel sleeve 0.28 square to 1.2 (the bumper guard). Pivot: centre "
                "of the footprint on the floor.", (-18.0, 21.0, 0.0), [202], places, ground=True)


def shop_mezzanine(ctx, M):
    b = B(130, step=0.3)
    x0, x1, y0, y1 = -23.6, -15.4, 25.0, 30.6
    for (px, py) in ((-15.5, 25.1), (-19.5, 25.1), (-23.5, 25.1), (-15.5, 30.5)):
        b.box((px - 0.075, py - 0.075, 0.02), (px + 0.075, py + 0.075, 2.48), "dark", chamfer=0.004)
        b.box((px - 0.08, py - 0.08, 0.0), (px + 0.08, py + 0.08, 0.02), "dark")
        b.box((px - 0.08, py - 0.08, 2.48), (px + 0.08, py + 0.08, 2.5), "dark")
    b.prism(steel.channel(0.30, 0.09, 0.012, 0.008), (x0, y0, 2.5), Y, Z, (x1 - x0, 0, 0), "yellow")
    b.prism(steel.channel(0.30, 0.09, 0.012, 0.008), (x1, y1, 2.5), -X, Z, (0, y0 - y1 + 0.0, 0), "yellow")
    for xj in np.arange(x0 + 0.3, x1 - 0.1, 0.6):
        b.prism(steel.channel(0.13, 0.05, 0.007, 0.005), (xj, y0 + 0.09, 2.662), X, Z, (0, y1 - y0 - 0.14, 0), "dark")
    b.prism(steel.angle(0.08, 0.08, 0.008), (x0, y1, 2.79), -Y, -Z, (x1 - x0, 0, 0), "dark")
    b.box((x0, y0, 2.792), (x1, y1, 2.80), "tread", vdir=X)
    b.box((x0, 27.1, 2.80), (-17.4, y1, 2.803), "lino", vdir=X, uv_off=(0.0, 0.0))
    # railings: south edge, east edge north of the stair head
    def railing(p0, p1, posts):
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        d = p1 - p0
        for t in np.linspace(0, 1, posts):
            p = p0 + d * t
            rod(b, (p[0], p[1], 2.80), (p[0], p[1], 3.83), 0.021, "yellow", n=10)
        rod(b, (p0[0], p0[1], 3.829), (p1[0], p1[1], 3.829), 0.021, "yellow", n=10)
        rod(b, (p0[0], p0[1], 3.35), (p1[0], p1[1], 3.35), 0.017, "yellow", n=8)
        u = d / np.linalg.norm(d)
        nn = np.cross(Z, u) * 0.003
        a, c = p0 - nn + np.array([0, 0, 2.80]), p1 + nn + np.array([0, 0, 2.90])
        b.box(np.minimum(a, c), np.maximum(a, c), "yellow")
    railing((-23.58, 25.04, 0), (-15.42, 25.04, 0), 7)
    railing((-15.44, 26.28, 0), (-15.44, 30.58, 0), 4)
    # office: timber panel 2.8..3.75, steel sill, glass band 3.80..5.00 in mullions, steel head to 5.30, roof slab
    def office_wall(p0, p1, door=None):
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        d = p1 - p0
        L = np.linalg.norm(d)
        u = d / L
        n = np.cross(u, Z)
        P = lambda s, z, o=0.0: p0 + u * s + Z * z + n * o
        bxx = lambda s0, s1, za, zb, o0, o1, slot, **kw: b.box(np.minimum(P(s0, za, o0), P(s1, zb, o1)), np.maximum(P(s0, za, o0), P(s1, zb, o1)), slot, **kw)
        sL = L if door is None else door
        bxx(0, sL, 2.80, 3.73, -0.05, 0.05, "officePanel", vdir=Z, fdir=u)
        bxx(0, sL, 3.73, 3.75, -0.05, 0.05, "plank")
        bxx(0, sL, 3.75, 3.80, -0.045, 0.045, "dark")
        bxx(0, sL, 5.00, 5.30, -0.05, 0.05, "dark")
        k = max(1, int(round(sL / 1.15)))
        for i in range(k + 1):
            s = min(max(i * sL / k, 0.025), sL - 0.025)
            bxx(s - 0.025, s + 0.025, 3.80, 5.00, -0.025, 0.025, "dark")
        bxx(0, sL, 3.80, 5.00, -0.003, 0.003, "glass")
        for i in range(k):
            s = (i + 0.5) * sL / k
            bxx(s - 0.05, s + 0.05, 3.26, 3.29, 0.05, 0.052, "steel")
    office_wall((-23.6, 27.1, 0), (-17.4, 27.1, 0), door=4.6)
    office_wall((-17.4, 27.1, 0), (-17.4, 30.6, 0))
    for xx, ya in ((-19.05, 27.05), (-17.45, 27.10)):
        b.box((xx, ya, 2.80), (xx + 0.05, 27.15, 4.90), "dark")
    b.box((-19.0, 27.05, 4.90), (-17.4, 27.15, 5.30), "dark")
    b.box((-23.6, 27.05, 5.30), (-17.35, 30.6, 5.40), "dark", vdir=X)
    b.box((-21.4, 28.74, 5.20), (-19.8, 28.86, 5.30), "grey")
    lathe(b, [(0.0, -0.78), (0.016, -0.78), (0.016, 0.78), (0.0, 0.78)], "tube", 10, loc=(-20.6, 28.8, 5.18), rot=(0, 90, 0))
    # wall tube under the deck on the north wall
    b.box((-20.6, 30.52, 2.56), (-19.4, 30.6, 2.64), "grey")
    lathe(b, [(0.0, -0.58), (0.013, -0.58), (0.013, 0.58), (0.0, 0.58)], "tube", 10, loc=(-20.0, 30.50, 2.585), rot=(0, 90, 0))
    # posters in the office
    for i, (o, du) in enumerate((((-22.8, 30.599, 3.9), (0.6, 0, 0)), ((-21.9, 30.599, 3.95), (0.6, 0, 0)), ((-23.599, 29.6, 3.9), (0, -0.6, 0)))):
        cell = (i / 3, 0.0, (i + 1) / 3, 1.0)
        du = np.array(du, float)
        oo = np.array(o, float)
        if i < 2:
            oo, du = oo + du, -du
        atlas_card(b, oo, du, (0, 0, 0.9), "signShopPosters", cell, ART.SHOP_M)
    cols = [208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 222, 223]
    allow = [((x0, y0, 2.48), (x1, y1, 2.67)),                    # beams and joists under the deck
             ((-23.6, 27.1, 2.8), (-17.4, 30.6, 5.3)),             # the office's inside: posters, lamp
             ((-20.7, 30.4, 2.5), (-19.3, 30.6, 2.7))]
    return done(ctx, b, "SM_Struct_ShopMezzanine", M,
                "V&R Auto Body mezzanine (05-level 2.6.4): four 0.16 posts on base plates, yellow channel edge beams 0.30 on the "
                "south and east edges, channel joists at 0.6 and a wall ledger, diamond-plate deck to 2.80, lino in the office; "
                "yellow tube railings (top 3.85, mid 3.35, toe plate) on the south edge and the east edge north of the stair "
                "head; the office: brown plywood panel walls 2.8..3.75 with a timber cap, steel sill, glass band 3.80..5.00 in "
                "steel mullions, steel head to 5.30, door frame and header (x -19..-17.4), roof slab 5.30..5.40, a 1.6 m tube "
                "under it, three posters (M_Sign_ShopPosters); a wall tube under the deck. Pivot: the shop's north-west inside "
                "corner, floor.", (-23.6, 30.6, 0.0), cols, [((-23.6, 30.6, 0.0), 0.0, cols)], allow=allow, ground=True)


def shop_stair(ctx, M):
    b = B(140, step=0.3)
    xf, xt, n, H = -12.04, -15.4, 12, 2.8
    g, r = (xf - xt) / n, H / n
    y0, y1 = 25.04, 26.26
    line = lambda x: r + (xf - x) * r / g
    sl = np.array([-g, 0, r]) / math.hypot(g, r)
    for k in range(1, n + 1):
        xa, xb = xf - k * g, xf - (k - 1) * g
        zt = k * r
        for yy in np.arange(y0 + 0.01, y1 - 0.005, 0.032):                       # bearing bars
            b.box((xa + 0.01, yy, zt - 0.03), (xb, yy + 0.004, zt), "grey", chamfer=0.0)
        for xx in np.linspace(xa + 0.04, xb - 0.03, 3):                          # cross rods
            b.box((xx - 0.003, y0, zt - 0.006), (xx + 0.003, y1, zt), "grey", chamfer=0.0)
        b.prism(steel.angle(0.03, 0.03, 0.004), (xb, y0, zt), -X, -Z, (0, y1 - y0, 0), "yellow")       # nosing
        for yy in (y0, y1 - 0.006):
            b.box((xa, yy, zt - 0.08), (xb, yy + 0.006, zt - 0.005), "grey")
    for ys, sy in ((24.98, -1), (26.26, 1)):
        yo = ys if sy < 0 else ys + 0.06
        outline = [(xf, ys, 0.0), (xf, ys, line(xf) + 0.02), (xt, ys, H), (xt, ys, H - 0.26), (xf - 0.26 * g / r, ys, 0.0)]
        P = np.array(outline)
        for yy in (ys, ys + 0.06):
            pass
        b.box((xt - 0.01, ys, H - 0.26), (xt, ys + 0.06, H), "dark")
        poly(b, [(p[0], ys + (0.06 if sy > 0 else 0.0), p[2]) for p in P], 0.06 if False else 0.008, "dark", np.array([0, sy, 0.0]), vdir=sl)
        poly(b, [(p[0], ys + (0.0 if sy > 0 else 0.06), p[2]) for p in P], 0.008, "dark", np.array([0, -sy, 0.0]), vdir=sl)
        yr = ys + 0.03
        xl = xf - (n - 1) * g
        for xp in np.linspace(xf - 0.12, xl + 0.05, 4):
            rod(b, (xp, yr, line(xp) - 0.02), (xp, yr, min(3.80, line(xp) + 0.98)), 0.019, "yellow", n=10)
        rod(b, (xf - 0.05, yr, line(xf - 0.05) + 1.0), (xl, yr, min(3.828, line(xl) + 1.0)), 0.021, "yellow", n=10)
        rod(b, (xl, yr, min(3.828, line(xl) + 1.0)), (xt + 0.03, yr, 3.828), 0.021, "yellow", n=10)
        rod(b, (xf - 0.05, yr, line(xf - 0.05) + 0.5), (xl, yr, line(xl) + 0.5), 0.017, "yellow", n=8)
        b.box((xf - 0.02, ys, 0.0), (xf + 0.0, ys + 0.06, 0.01), "dark")
    cols = list(range(224, 238))
    allow = [((xt, 24.96, 0.0), (xf + 0.02, 26.34, 3.86 + 0.0))]
    return done(ctx, b, "SM_Struct_ShopStair", M,
                "Mezzanine stair (05-level 2.6.4): 12 open bar-grating treads (bearing bars 4 x 30 mm at 32 mm, cross rods) "
                "with yellow nosings, rise 0.233, going 0.28, on two channel stringers 0.06 x 0.26 with end plates, yellow pipe "
                "handrails 1.0 and 0.5 above the nosings on both sides. Pivot: the foot, south stringer, floor.",
                (xf, 24.98, 0.0), cols, [((xf, 24.98, 0.0), 0.0, cols)], allow=allow, ground=True)


def shop_safe(ctx, M):
    b = B(150, step=0.2)
    x0, x1, y0, y1, z0, z1 = -18.5, -17.7, 29.6, 30.4, 2.8, 3.65
    body = geo.box((0.8, 0.72, 0.82), bevel=0.02, segments=2)
    geo.transform(body, loc=(-18.1, 30.04, 2.83))
    b.absorb(body, "dark")
    b.box((x0 + 0.06, 29.665, z0 + 0.09), (x1 - 0.06, 29.68, z1 - 0.06), "dark")
    for zz in (z0 + 0.2, z1 - 0.2):
        lathe(b, [(0.0, -0.06), (0.018, -0.06), (0.018, 0.06), (0.0, 0.06)], "dark", 12, loc=(x1 - 0.02, 29.672, zz))
    lathe(b, [(0.0, 0.0), (0.055, 0.0), (0.05, 0.02), (0.035, 0.028), (0.0, 0.03)], "chrome", 32, loc=(-18.18, 29.665, 3.32), rot=(90, 0, 0))
    lathe(b, [(0.0, 0.0), (0.014, 0.0), (0.014, 0.05), (0.0, 0.05)], "chrome", 12, loc=(-17.98, 29.665, 3.12), rot=(90, 0, 0))
    bar(b, (-17.98, 29.615, 3.02), (-17.98, 29.615, 3.22), 0.022, 0.022, "chrome", up=Y)
    b.box((-18.34, 29.668, 3.48), (-18.02, 29.672, 3.56), "brass")
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((-18.1 + sx * 0.33 - 0.03, 30.04 + sy * 0.3 - 0.03, z0), (-18.1 + sx * 0.33 + 0.03, 30.04 + sy * 0.3 + 0.03, z0 + 0.03), "black")
    return done(ctx, b, "SM_Struct_ShopSafe", M,
                "Office safe (05-level 2.6.4), 0.8 x 0.8 x 0.85 on four feet: bevelled steel body (MI_Steel_IronDark), door "
                "slab with two hinge barrels, chrome combination dial and T-handle, brass maker's plate (blank). Door faces web "
                "+z (the office front). Pivot: footprint centre on the deck.", (-18.1, 30.0, 2.8), [221],
                [((-18.1, 30.0, 2.8), 0.0, [221])], ground=2.8)


def shop_fan(ctx, M):
    out = []
    b = B(160, step=0.2)
    cy, cz = 22.1, 4.5
    pl = geo.plate((2.0, 1.2), 0.004, holes=[(0.0, 0.0, 0.58)])
    geo.transform(pl, loc=(5.98, cy, cz), rot=(90, 0, 90))
    b.absorb(pl, "galv")
    sh = geo.tube(0.6, 0.585, 0.36, 48, axis="X")
    geo.transform(sh, loc=(5.62, cy, cz))
    b.absorb(sh, "galv")
    lathe(b, [(0.0, -0.1), (0.11, -0.1), (0.12, -0.08), (0.12, 0.08), (0.11, 0.1), (0.0, 0.1)], "dark", 24, loc=(5.86, cy, cz), rot=(0, 90, 0))
    for a in (0.0, 2.094, 4.189):
        rod(b, (5.88, cy + 0.11 * math.cos(a), cz + 0.11 * math.sin(a)), (5.88, cy + 0.58 * math.cos(a), cz + 0.58 * math.sin(a)), 0.01, "dark", n=6)
    for xg in (5.625, 5.975):
        for k in range(5):
            zz = cz - 0.48 + k * 0.24
            h = math.sqrt(max(0.0, 0.58 ** 2 - (zz - cz) ** 2))
            rod(b, (xg, cy - h, zz), (xg, cy + h, zz), 0.0035, "black", n=6)
        b.absorb(geo.torus(0.58, 0.004, 48, 6), "black") if False else None
    for xg in (5.625, 5.975):
        tor = geo.torus(0.575, 0.005, 48, 6)
        geo.transform(tor, loc=(xg, cy, cz), rot=(0, 90, 0))
        b.absorb(tor, "black")
    # caged lamp on the alley face over the side door
    b.box((6.0, cy - 0.06, 2.75), (6.02, cy + 0.06, 2.97), "black")
    lathe(b, [(0.0, 0.02), (0.045, 0.02), (0.05, 0.07), (0.045, 0.12), (0.0, 0.125)], "lensWarm", 16, loc=(6.0, cy, 2.86), rot=(0, 90, 0))
    allow = [((6.0, cy - 0.1, 2.7), (6.2, cy + 0.1, 3.0))]
    out.append(done(ctx, b, "SM_Struct_ShopExtractorFan", M,
                    "Extractor fan in the shop's east wall over the side door (05-level 2.6.2): galvanised mounting plate 2.0 x 1.2 "
                    "with a 1.16 m port, shroud ring, motor on three struts, wire guards (five bars and a ring) on both faces, and the "
                    "caged lamp over the side door on the alley face. The blades are SM_Struct_ShopExtractorFan_Blades. Pivot: the "
                    "fan axis on the wall's outer plane.", (6.0, cy, cz), [200], [((6.0, cy, cz), 0.0, [200])], allow=allow, ground=False))
    b = B(161, step=0.2)
    for k in range(4):
        a = k * math.pi / 2
        bl = geo.box((0.03, 0.5, 0.2), bevel=0.01, segments=2, base=False)
        geo.transform(bl, loc=(0.0, 0.3, 0.0))
        co, _ = geo.arrays(bl)
        tw = 0.5 + 0.25 * (co[:, 1] - 0.3)
        c_, s_ = np.cos(tw), np.sin(tw)
        x_, z_ = co[:, 0] * c_ - co[:, 2] * s_, co[:, 0] * s_ + co[:, 2] * c_
        co[:, 0], co[:, 2] = x_, z_
        geo.set_verts(bl, co)
        geo.transform(bl, rot=(math.degrees(a), 0, 0))
        geo.transform(bl, loc=(5.70, cy, cz))
        b.absorb(bl, "grey")
    lathe(b, [(0.0, -0.05), (0.08, -0.05), (0.08, 0.04), (0.04, 0.05), (0.0, 0.055)], "grey", 24, loc=(5.70, cy, cz), rot=(0, -90, 0))
    out.append(done(ctx, b, "SM_Struct_ShopExtractorFan_Blades", M,
                    "Four pitched blades 0.5 x 0.2 at radius 0.3 on a hub: the turning part of the extractor fan (spins about the "
                    "Unreal X axis at 1.7 rad/s, 05-level 2.6.2). Pivot: on the axis at the hub.", (5.70, cy, cz), [200],
                    [((5.70, cy, cz), 0.0, [200])], ground=False))
    return out


def shop_exit(ctx, M):
    b = B(170, step=0.2)
    sign_tile(M, "ExitBox", 0.7, 0.3)
    b.box((5.52, 21.75, 2.70), (5.60, 22.45, 3.00), "black")
    card(b, (5.5195, 22.45, 2.70), (0, -0.7, 0), (0, 0, 0.3), "signExitBox", sign=True)
    rod(b, (5.58, 22.1, 3.0), (5.58, 22.1, 3.25), 0.012, "galv", n=8)
    allow = [((5.5, 21.7, 2.6), (5.61, 22.5, 3.3))]
    return done(ctx, b, "SM_Struct_ShopExitSign", M,
                "Lit EXIT box 0.7 x 0.3 over the side door inside the shop (05-level 2.6.5, M_Sign_ExitBox with E), on a "
                "conduit stub. Pivot: on the wall's inner plane.", (5.6, 22.1, 2.85), [199], [((5.6, 22.1, 2.85), 0.0, [])],
                allow=allow, ground=False)


# ========================================================================================================= build

def build(ctx):
    ctx.built, ctx.places = [], []
    ART.draw_all(force=ctx.args.force)
    M = materials(ctx)
    ctx.M = M
    want = lambda k: not ctx.args.only or k in ctx.args.only or any(o.startswith("structures_") for o in ctx.args.only)
    if want("station"):
        mezzanine(ctx, M)
        for s in (-1, 1):
            bridge(ctx, M, s)
        stair(ctx, M)
        platforms(ctx, M)
    if want("street"):
        kiosk(ctx, M, "SM_Struct_Kiosk_News", 3.0, 2.46, (0, 1, 0), "KioskNews", 2.4, (1, 0, 0), [559], (-28.7, 8.27, 0.15))
        kiosk(ctx, M, "SM_Struct_Kiosk_Candy", 2.74, 1.65, (1, 0, 0), "KioskCandy", 1.35, (0, 1, 0), [490], (-43.87, -10.075, 0.15))
        produce_stand(ctx, M)
        hoardings(ctx, M)
        dig_pen(ctx, M)
    if want("yard"):
        loading_dock(ctx, M)
        garages(ctx, M)
    if want("shop"):
        shop_floor(ctx, M)
        shop_roof(ctx, M)
        shop_column(ctx, M)
        shop_mezzanine(ctx, M)
        shop_stair(ctx, M)
        shop_safe(ctx, M)
        shop_fan(ctx, M)
        shop_exit(ctx, M)
    return ctx.built


def on_export(ctx, objs):
    from mi import export
    for name, a in ctx.assets.items():
        export.export_asset(a["ob"], ctx.family, a["collision"], a["cover_height"], a["notes"], a["pivot"], a["expect_size"],
                            slots=a["slots"])
    write_placements(ctx)


def write_placements(ctx):
    path = os.path.join(ROOT, "art", "out", "placements", "structures.json")
    old = {}
    if os.path.exists(path):
        with open(path) as f:
            old = {e["mesh"]: e for e in json.load(f).get("instances", [])}
    inst, fits = [], {}
    for p in ctx.places:
        for loc, yaw, cols in p["places"]:
            x, y, z = loc
            inst.append({"mesh": p["mesh"], "structure": p["mesh"].replace("SM_Struct_", ""), "role": "structure",
                         "location": [round(x * 100.0, 2), round(-y * 100.0, 2), round(z * 100.0, 2)],
                         "yaw": round(-yaw % 360.0, 3), "colliders": cols})
        fits[p["mesh"]] = p["fit"]
    names = {e["mesh"] for e in inst}
    for e in old.values():
        if e["mesh"] not in names:
            inst.append(e)
    drawn = sorted({c for e in inst for c in e["colliders"]})
    doc = {"about": "Structure instances of the structures family (art/blender/assets/structures.py), the form of buildings.json: "
                    "Unreal centimetres (X east, Y south, Z up), yaw degrees about Z (0 = mesh as imported). `colliders`: the "
                    "level.json collider indices the instance draws (keep them as invisible blocking boxes: the art sits inside "
                    "or flush with them, overhead parts listed per mesh under `fit`).",
           "count": len(inst), "meshes": sorted(names | {e["mesh"] for e in old.values()}),
           "colliders_drawn": drawn,
           "colliders_drawn_elsewhere": {"534": "SM_Furn_SidewalkShed (parapet)", "535": "SM_Furn_SidewalkShed (parapet)",
                                         "536": "SM_Furn_SidewalkShed (parapet)"},
           "fit": fits, "instances": inst}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    ctx.log("placements: %s (%d instances)" % (path, len(inst)))


# ======================================================================================================= preview

def _append(blend, names):
    path = os.path.join(paths.blend, blend + ".blend")
    with bpy.data.libraries.load(path) as (src, dst):
        dst.objects = [n for n in names if n in src.objects]
    out = {}
    for ob in dst.objects:
        if ob is None:
            continue
        ob.matrix_world = Matrix.Identity(4)
        out[ob.name] = ob
    return out


def _put(proto, loc, yaw=0.0, scale=1.0, col_=None):
    ob = scene.duplicate(proto, linked=True, col=col_)
    ob.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Diagonal((scale, 1, 1, 1))
    return ob


def context_dress(ctx, x_range=(-60, 30)):
    """The block round the structures for the pictures: El, street, the facade kit from buildings.json, shop walls."""
    dcol = scene.collection("Dress")
    el = _append("el", ["SM_El_Column", "SM_El_Bent", "SM_El_GirderSpan_10m", "SM_El_Deck_10m", "SM_El_Lamp"])
    for k in range(int(x_range[0] // 10), int(x_range[1] // 10) + 1):
        x = k * 10.0
        for yy in (-4.6, 4.6):
            _put(el["SM_El_Column"], (x + 5.0, yy, 0), col_=dcol)
        _put(el["SM_El_Bent"], (x + 5.0, 0, 0), col_=dcol)
        _put(el["SM_El_GirderSpan_10m"], (x + 5.0, 0, 0), col_=dcol)
        _put(el["SM_El_Deck_10m"], (x + 5.0, 0, 0), col_=dcol)
    st = _append("street", ["SM_Street_Road_20m", "SM_Street_Sidewalk_4m", "SM_Street_Sidewalk_4m_B", "SM_Street_Kerb_4m"])
    for x in np.arange(x_range[0], x_range[1], 20.0):
        _put(st["SM_Street_Road_20m"], (x, 0, 0), col_=dcol)
    for i, x in enumerate(np.arange(x_range[0], x_range[1], 4.0)):
        sw = st["SM_Street_Sidewalk_4m" if i % 2 else "SM_Street_Sidewalk_4m_B"]
        _put(sw, (x, 7.0, 0), col_=dcol)
        _put(sw, (x + 4.0, -7.0, 0), 180.0, col_=dcol)
        _put(st["SM_Street_Kerb_4m"], (x, 7.0, 0), col_=dcol)
        _put(st["SM_Street_Kerb_4m"], (x + 4.0, -7.0, 0), 180.0, col_=dcol)
    with open(os.path.join(ROOT, "art", "out", "placements", "buildings.json")) as f:
        bj = json.load(f)
    names = sorted({e["mesh"] for e in bj["instances"]})
    fac = _append("facade", names)
    for e in bj["instances"]:
        if e["mesh"] not in fac:
            continue
        X_, Y_, Z_ = e["location"]
        x = X_ / 100.0
        if not (x_range[0] - 6 < x < x_range[1] + 6):
            continue
        _put(fac[e["mesh"]], (x, -Y_ / 100.0, Z_ / 100.0), -e["yaw"], (e.get("scale") or [1.0])[0], col_=dcol)
    return dcol


def shop_walls():
    """The auto body shop's block walls (furniture modules) round the interior, doorways left open."""
    dcol = scene.collection("DressShop")
    if True:
        fw = _append("furniture", ["SM_Furn_BlockWall_200"])
        w = fw.get("SM_Furn_BlockWall_200")
        if w:
            for x in np.arange(-24.0, 6.0, 2.0):
                _put(w, (x + 2.0, 31.0, 0), 180.0, col_=dcol)                        # north wall, outer face +y
            for y in np.arange(11.0, 31.0, 2.0):
                _put(w, (-24.0, y + 2.0, 0), -90.0, col_=dcol)                       # west wall, outer face -x
                if not (20.5 < y + 1.0 < 23.7):
                    _put(w, (6.0, y, 0), 90.0, col_=dcol)                            # east wall, outer face +x
            for x in np.arange(-24.0, 6.0, 2.0):
                if -15.2 < x + 1.0 < -8.8 or -3.4 < x + 1.0 < 0.8:
                    continue
                _put(w, (x, 11.0, 0), 0.0, col_=dcol)
    return dcol


def _clay_wire():
    m = bpy.data.materials.new("ClayWire")
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    clay = nt.nodes.new("ShaderNodeBsdfPrincipled")
    clay.inputs["Base Color"].default_value = (0.55, 0.55, 0.55, 1)
    clay.inputs["Roughness"].default_value = 0.6
    dark = nt.nodes.new("ShaderNodeBsdfDiffuse")
    dark.inputs["Color"].default_value = (0.02, 0.025, 0.03, 1)
    wire = nt.nodes.new("ShaderNodeWireframe")
    wire.use_pixel_size = True
    wire.inputs["Size"].default_value = 0.7
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(wire.outputs[0], mix.inputs[0])
    nt.links.new(clay.outputs[0], mix.inputs[1])
    nt.links.new(dark.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def _place_assets(ctx):
    """Put every built asset where structures.json places it (the build leaves them at their pivots)."""
    pcol = scene.collection("Placed")
    for p in ctx.places:
        ob = bpy.data.objects.get(p["mesh"])
        if ob is None:
            continue
        first = True
        for loc, yaw, _c in p["places"]:
            if first:
                ob.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(yaw), 4, "Z")
                first = False
            else:
                _put(ob, loc, yaw, col_=pcol)


def _shot(ctx, name, samples):
    """One preview. MI_PROBE=<dir>: a 192 x 108 exposure probe into <dir> instead, its luminance logged."""
    probe = os.environ.get("MI_PROBE")
    if probe:
        from PIL import Image
        os.makedirs(probe, exist_ok=True)
        f = os.path.join(probe, name + ".png")
        render.render_png(f, 12, (192, 108))
        bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1280, 720
        g = np.asarray(Image.open(f).convert("L"), float) / 255.0
        ctx.log("probe %s: mean %.3f  p10 %.3f  p50 %.3f  p90 %.3f  clipped %.1f%%"
                % (name, g.mean(), *np.percentile(g, (10, 50, 90)), 100.0 * (g > 0.98).mean()))
        return
    _p, sec = render.render_jpeg(os.path.join(paths.previews, name + ".jpg"), samples)
    ctx.log("preview %s.jpg %.0fs" % (name, sec))


def on_preview(ctx, objs):
    a = ctx.args
    P = paths.previews
    only = set(a.only or [])
    want = lambda n: (not only) or n in only
    _place_assets(ctx)
    render.setup(samples=a.samples)
    sc = bpy.context.scene                          # memory: the agents share one limit; no 8K map is needed at 1280 x 720
    sc.render.use_simplify = True
    sc.cycles.texture_limit_render = "4096"
    for k in ("lensGreen", "glassLit", "glassCool", "lensWarm", "tube", "lampWork"):
        bs = mat.principled(ctx.M[k])
        bs.inputs["Emission Strength"].default_value *= 0.15                # by day
    if want("structures_station") or want("structures_station_up") or want("structures_wire") or want("structures_street"):
        context_dress(ctx, (-60, 30))
    if want("structures_wire"):
        vl = bpy.context.view_layer
        vl.material_override = _clay_wire()
        render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING, stops=2.2)
        render.cam_look((-36.2, -10.6, 1.6), (-40.2, -8.0, 2.4), lens=30, name="Cam_Wire")
        _p, sec = render.render_jpeg(os.path.join(P, "structures_wire.jpg"), max(24, a.samples // 2))
        vl.material_override = None
        ctx.log("preview structures_wire.jpg %.0fs" % sec)
    st_stops = float(os.environ.get("MI_ST_STOPS", "3.0"))
    up_stops = float(os.environ.get("MI_UP_STOPS", "4.2"))
    if want("structures_station"):
        # the stair foot faces east: the design sun (260) stands straight behind it, so for this picture the dome is
        # turned to a mid-morning sun (80) that lights the entrance instead of a silhouette against the sky
        render.rig_day(sun_azimuth=80.0, stops=st_stops)
        render.cam_look((-33.2, -9.6, 1.70), (-41.0, -7.2, 3.3), lens=24, name="Cam_Station")
        _shot(ctx, "structures_station", a.samples)
    if want("structures_station_up"):
        render.rig_day(sun_azimuth=80.0, stops=up_stops)
        render.cam_look((-40.3, -8.15, 1.3 + 1.62), (-44.6, -7.6, 5.3), lens=22, name="Cam_StationUp")
        _shot(ctx, "structures_station_up", a.samples)
    if want("structures_street"):
        # for this one picture the news kiosk (shutter to the road) and a lot hoarding (face west) are moved in
        # beside the produce stand, so the three read in one frame
        kn = bpy.data.objects.get("SM_Struct_Kiosk_News")
        if kn:
            kn.matrix_world = Matrix.Translation((7.6, 9.6, 0.15)) @ Matrix.Rotation(math.pi, 4, "Z")
        hl = bpy.data.objects.get("SM_Struct_Hoarding_LotW")
        if hl:
            hl.matrix_world = Matrix.Translation((17.6, 10.95, 0.15)) @ Matrix.Rotation(math.radians(-90.0), 4, "Z")
        render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING, stops=float(os.environ.get("MI_SR_STOPS", "0.5")))
        render.cam_look((5.5, 5.6, 1.60), (13.0, 9.6, 1.0), lens=24, name="Cam_Street")
        _shot(ctx, "structures_street", a.samples)
    if want("structures_chopshop"):
        if not bpy.data.collections.get("Dress"):
            context_dress(ctx, (-30, 10))
        shop_walls()
        render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING, stops=float(os.environ.get("MI_SH_STOPS", "3.2")))
        for k in ("lampWork", "tube"):
            mat.principled(ctx.M[k]).inputs["Emission Strength"].default_value /= 0.15
        for lx, lz in WORK:
            ld = bpy.data.lights.new("Work", "SPOT")
            ld.energy, ld.spot_size, ld.color = 900.0, math.radians(120), (1.0, 0.86, 0.68)
            lo = bpy.data.objects.new("Work", ld)
            lo.location = (lx, lz, 5.0)
            bpy.context.scene.collection.objects.link(lo)
        render.cam_look((-8.0, 16.0, 1.66), (-18.5, 27.5, 3.0), lens=20, name="Cam_Shop")
        _shot(ctx, "structures_chopshop", a.samples)
