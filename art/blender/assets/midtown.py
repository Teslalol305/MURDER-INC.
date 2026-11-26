"""Midtown rooftops above the square (Level 3, night): the `midtown` art family, MAPS.md lane A-MT.

    venv/bin/python art/blender/build.py build midtown --export                  # meshes, faces, manifests, placements
    venv/bin/python art/blender/build.py build midtown --bake --export           # the same, redrawing the screen and sign atlases
    venv/bin/python art/blender/build.py build midtown --preview --samples 12    # the night look-dev pictures (art/previews/maps/mt_*)
    venv/bin/python art/blender/assets/_midtown_check.py                         # the lane's checks (reads the outputs)

What it makes (design: docs/unreal/maps/midtown.md 12 and 14.2; English only, every name invented, IPX the only real mark):
    roofs        SM_Roof_Deck_{Gravel,Pavers}_4m, SM_Roof_Parapet_{4,1}m_{Buff,Red}, SM_Roof_NamePanel_6m,
                 SM_Roof_TankStand_{4,2}m, SM_Roof_WaterTank_{4p6,3p6}, SM_Roof_Bulkhead_4x4, SM_Roof_Bulkhead_5x6,
                 SM_Roof_TankHouse_6x6, SM_Roof_MachineRoom_6x6, SM_Roof_HVAC_RTU_{L,M}, SM_Roof_Skylight_2x3,
                 SM_Roof_Vent_Mushroom, SM_Roof_ChimneyStack, SM_Roof_TarKettle, SM_Roof_Dish, SM_Roof_Antenna, SM_Roof_WorkLight,
                 SM_Roof_SteelStair_3p6, SM_Roof_StairHead_2p4, SM_Roof_PlankBridge_2p6x2, SM_Roof_PipeBridge_2p6x2
    screens      SM_Roof_Gantry_16m, SM_Sign_LEDWall_16x9 (G1, its truss back is the playable side), SM_Roof_BillboardFrame_16x8
                 (C1), SM_Sign_LEDWall_Tile_2m (the art-only screens are tiled from it), SM_Sign_Ticker_4m, SM_Sign_TowerStack (N1)
    scaffold     SM_Scaf_Flight_2p4, SM_Scaf_Landing_2p4, SM_Scaf_Bay_Frame, SM_Scaf_Netting_Panel, SM_Scaf_Sign
    faces        MT_Screens_A/_B (16 slides), MT_Ticker, MT_Digits, MT_LEDMask, Sign_MT_Atlas1 (18 printed faces)
Reused from the Block unchanged (midtown.md 14.1): facade kit, furniture, gaps, street, vehicles, props; not built here: the
square's furniture, the Stand and the Booth, the bus, the facade tables (lane A-MT's other families, still open).

Outputs (art/out, git-ignored): glb/SM_Roof_*, SM_Scaf_*, SM_Sign_LEDWall_*, SM_Sign_Ticker_4m, SM_Sign_TowerStack; the shared
manifest.json (merged under its lock); textures/MT_* and Sign_MT_Atlas1; midtown/manifest_midtown.json (this lane's assets,
budgets, sets, emissive plan), midtown/signs_midtown.json (every name, its cell and carrier), placements/placements_midtown.json
(the west block's roofs, the gantry and the scaffold tower assembled from the kits, in level coordinates).
"""
import json
import os
import time

from assets import _midtown_names as names
from assets import _midtown_roof as roof
from mi import export, geo, paths, scene

FAMILY = {"name": "midtown",
          "description": "Midtown rooftops (Level 3): roofs, parapets, water towers, bulkheads, HVAC, stairs and bridges, the gantry and "
                         "LED wall backs, the roof billboard, the scaffold stair; the screen and sign atlases"}

OUT = os.path.join(paths.out, "midtown")

# Triangle caps (midtown.md 14.2, read as the cap of each named asset; the unnamed ones get the cap of their kind).
BUDGET = {
    "SM_Roof_Deck_": 2000, "SM_Roof_Parapet_": 3000, "SM_Roof_NamePanel": 1000,
    "SM_Roof_TankStand_": 12000, "SM_Roof_WaterTank_": 12000, "SM_Roof_TankHouse_6x6": 10000, "SM_Roof_MachineRoom_6x6": 10000,
    "SM_Roof_Bulkhead_": 8000, "SM_Roof_SteelStair_3p6": 15000, "SM_Roof_StairHead_2p4": 6000, "SM_Roof_PlankBridge": 6000,
    "SM_Roof_PipeBridge": 6000, "SM_Roof_HVAC_RTU_L": 10000, "SM_Roof_HVAC_RTU_M": 6000, "SM_Roof_Skylight": 3000,
    "SM_Roof_Vent_Mushroom": 4000, "SM_Roof_ChimneyStack": 4000, "SM_Roof_TarKettle": 3000, "SM_Roof_Dish": 3000,
    "SM_Roof_Antenna": 2000, "SM_Roof_WorkLight": 2000,
    "SM_Roof_Gantry_16m": 25000, "SM_Sign_LEDWall_16x9": 30000, "SM_Roof_BillboardFrame_16x8": 25000,
    "SM_Sign_LEDWall_Tile_2m": 2000, "SM_Sign_Ticker_4m": 2000, "SM_Sign_TowerStack": 40000,
    "SM_Scaf_Flight_2p4": 8000, "SM_Scaf_Landing_2p4": 4000, "SM_Scaf_Bay_Frame": 6000, "SM_Scaf_Netting_Panel": 500,
    "SM_Scaf_Sign": 1000,
}

# How the screens stay within the design's emissive budget (midtown.md 11.2, 12.3, 15): recorded with the art.
EMISSIVE_PLAN = {
    "large_screens": {"G1": "SM_Sign_LEDWall_16x9 (16 x 9, hero, 450 nits)", "E1": "12 x 9 tiles of SM_Sign_LEDWall_Tile_2m (24 x 18, hero)",
                      "E2a": "4 x 10 tiles (8 x 20, 300 nits)", "E2b": "4 x 10 tiles (8 x 20, 300 nits)",
                      "E3": "10 x 6 tiles (20 x 12, hero; the curve as tiles turned 6 degrees apart)",
                      "N1": "SM_Sign_TowerStack (3 x 14 x 8, hero)", "S1": "6 x 3 tiles (12 x 6, 300 nits)"},
    "count": "7 large screen surfaces + the ticker (ceiling 9). C1 is a lightbox (200 nits), not a screen",
    "material": "one opaque master M_MI_Screen (slot M_MI_Screen on 0..1 UVs per screen, or per tile with the tile's sub-rect "
                "in the MI): black base, emissive = atlas cell x nits, crossfade of two cells, LED mask faded 8..20 m. No "
                "translucency, no world position offset, no video, no render targets",
    "tiles": "a tiled screen is ONE material instance per screen; each tile's MI parameter (its row and column) offsets "
             "its 0..1 UVs into the screen's cell, so the whole screen still shows one slide (placements carry the offsets)",
    "change_rate": "the director changes at most one hero screen in any 2 s, each at most every 8 s, 0.6 s crossfade, nothing "
                   "faster than 3 Hz",
    "light": "Lumen from the emissive plus 4 unshadowed rect lights (G1, E1, E3, N1) sized to the screens; if Lumen blotches at "
             "0.5 render scale the screen meshes' Affect Dynamic Indirect Lighting goes off",
    "palette": "no red field on any slide (the Goons are oxblood); VLTR is a small corner mark",
}


def budget(name):
    best = max((k for k in BUDGET if name.startswith(k)), key=len)
    return BUDGET[best]


def build(ctx):
    names.check_english()
    ctx.K = {}
    ctx.kit = scene.collection("MidtownKit", ctx.col)
    from assets import _midtown_atlas as atlas
    have = all(os.path.exists(os.path.join(paths.texture_set(s), "set.json"))
               for s in ("MT_Screens_A", "MT_Screens_B", "MT_Ticker", "MT_Digits", "MT_LEDMask", "Sign_MT_Atlas1"))
    if ctx.args.bake or not have:
        atlas.build_all(ctx.args.seed, log=ctx.log)
    for s in ("MT_Screens_A", "MT_Screens_B", "MT_Ticker", "MT_Digits", "MT_LEDMask", "Sign_MT_Atlas1"):
        if s not in ctx.sets:
            ctx.sets.append(s)
    M = roof.materials(ctx)
    ctx.M = M
    kits = list(roof.PROPS)
    try:
        from assets import _midtown_screens as screens
        kits += screens.PROPS
    except ImportError:
        pass
    try:
        from assets import _midtown_scaffold as scaffold
        kits += scaffold.PROPS
    except ImportError:
        pass
    for f in kits:
        f(ctx, M)
    tris = {n: geo.stats(o)["triangles"] for n, o in ctx.K.items()}
    ctx.log("%d assets, %d triangles in all, largest %s (%d)" % (len(tris), sum(tris.values()), max(tris, key=tris.get), max(tris.values())))
    for n_, t_ in sorted(tris.items()):
        ctx.log("  %-34s %7d / %6d%s" % (n_, t_, budget(n_), "" if t_ <= budget(n_) else "   OVER"))
    return [a["ob"] for a in ctx.assets.values()]


def on_export(ctx, objs):
    entries = []
    for name, a in ctx.assets.items():
        if ctx.want(name):
            entries.append(export.export_asset(a["ob"], ctx.family, a["collision"], a["cover_height"], a["notes"], a["pivot"],
                                               a["expect_size"], fbx=ctx.args.fbx, slots=a["slots"]))
    write_lane_files(ctx, entries)


def write_lane_files(ctx, entries):
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for e in entries:
        cap = budget(e["name"])
        rows.append({"name": e["name"], "glb": e["glb"], "triangles": e["triangles"], "budget_tris": cap,
                     "within_budget": e["triangles"] <= cap, "size_m": e["bounds_m"]["size"],
                     "slots": [m["slot"] for m in e["material_slots"]], "collision": e["collision"], "notes": e["notes"]})
    sets = {}
    for s in ("MT_Screens_A", "MT_Screens_B", "MT_Ticker", "MT_Digits", "MT_LEDMask", "Sign_MT_Atlas1"):
        with open(os.path.join(paths.texture_set(s), "set.json")) as f:
            info = json.load(f)
        sets[s] = {"resolution": info["resolution"], "files": info["files"], "cells": len(info.get("cells", {}))}
    man = {"about": "MAPS.md lane A-MT, Midtown roof, screen and scaffold art (assets/midtown.py). The GLBs and textures stay in "
                    "art/out (git-ignored); this file lists what the lane made and how it measures against midtown.md 14 and 15.",
           "updated": time.strftime("%Y-%m-%dT%H:%M:%S"), "family": "midtown", "count": len(rows),
           "triangles_total": sum(r["triangles"] for r in rows), "assets": rows,
           "texture_sets_new": sets, "texture_sets_reused": sorted(s for s in ctx.sets if s.startswith("TS_")),
           "new_tiling_sets": 0, "emissive_plan": EMISSIVE_PLAN,
           "rules": {"english_only": True, "strings_checked": names.check_english(), "real_marks": "IPX only (the owner's)",
                     "names_searched": False, "collision": "none on the art: the level data decides (MAPS.md lane B)",
                     "thin_members_min_m": roof.MEMBER_MIN}}
    with open(os.path.join(OUT, "manifest_midtown.json"), "w") as f:
        json.dump(man, f, indent=1, sort_keys=True)
    scr = {}
    for p in ("A", "B"):
        with open(os.path.join(paths.texture_set("MT_Screens_" + p), "set.json")) as f:
            for k, c in json.load(f)["cells"].items():
                scr[k] = dict(c, atlas="MT_Screens_" + p)
    with open(os.path.join(paths.texture_set("Sign_MT_Atlas1"), "set.json")) as f:
        faces = json.load(f)["cells"]
    signs = {"about": "Every word on a Midtown screen, billboard, sign or label (English only, invented names; "
                      "assets/_midtown_names.py) with its atlas cell. A screen = its mesh's M_MI_Screen slot + the slide cells; a "
                      "printed face = its carrier + an MI of M_Sign_MT_Face mapping 0..1 to the cell (v up).",
             "slides": scr, "faces": faces, "ticker": names.TICKER, "digits": names.DIGITS, "marks": names.MARKS,
             "business_names": names.business_names(), "names_status": "invented, not yet searched (MAPS.md C1)"}
    with open(os.path.join(OUT, "signs_midtown.json"), "w") as f:
        json.dump(signs, f, indent=1, sort_keys=True)
    n = 0
    try:
        from assets import _midtown_place as place
        n = place.write_placements(os.path.join(paths.out, "placements", "placements_midtown.json"))
    except ImportError:
        pass
    ctx.log("lane files: %d assets, %d slides, %d faces, %d placements" % (len(rows), len(scr), len(faces), n))


def on_preview(ctx, objs):
    from assets import _midtown_preview as prev
    prev.render_all(ctx)
