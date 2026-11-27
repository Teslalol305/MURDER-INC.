"""Canal Street (Level 2, Chinatown at night, wet after rain): the `chinatown` art family, MAPS.md lane A-CT.

    venv/bin/python art/blender/build.py build chinatown --export                 # meshes, atlas, manifests, placements
    venv/bin/python art/blender/build.py build chinatown --export --preview --samples 16
    venv/bin/python art/blender/assets/_chinatown_check.py                        # the lane's checks (reads the outputs)

What it makes (design: docs/unreal/maps/chinatown.md 13; the owner's answer of 2026-11-26: signs in ENGLISH ONLY):
    shop fronts       SM_Facade_Shopfront_CT_{Wide, Narrow, Restaurant, Jewelry, Grocery, Shut}, SM_Facade_CT_Fascia_1m,
                      SM_Facade_CT_WindowGrille, SM_Facade_CT_StackedSignRail, SM_Facade_CT_Awning_Box_{3,4,6}m
    sign carriers     SM_Sign_CT_Band_{6,8,10}m, _Blade_{4,6,12}m, _Kiosk_{1m,3m}, _Board, _StallBoard, _Poster_{A,B},
                      _Placard, _StreetBlade, _Arch (faces from the atlas Sign_CT_Atlas1), exposed neon
                      SM_Sign_CT_Neon_{MoonGate, Mahjong, SilverWave, BigLight}, SM_Sign_CT_RooftopFrame (pan letters)
    market            SM_Prop_CT_{StallCounter_2m, FishCounter, Produce_{Citrus,Greens,Mixed}, DryGoods, StyrofoamBoxes,
                      Tarp, PendantBulb, FishTank, HangingScale, HandTruck}
    vendors           SM_Prop_CT_{VendorTable, Goods_{Bags,Caps,TShirts,Shades,Discs}, MarketUmbrella, ClothingRail}
    lanterns          SM_Prop_CT_Lantern, SM_Prop_CT_LanternString_14m (one string, over the banquet doors only)
    street, Square    SM_Prop_CT_{EBike, CardboardBale, Stanchions, CardTable, Stool, ParkBench, BasketballHoop,
                      ChainLinkEdging_3m, FruitStand}
    roofs             SM_Prop_CT_{Condenser, Skylight, RoofHatch}
Reused unchanged from the Block (chinatown.md 13.1): the facade kit's piers, bays, cornice, parapet and fire escapes,
furniture, gaps, street kit and vehicles; the placements reference them by name.

Outputs (art/out, git-ignored): glb/SM_*_CT_*.glb, the shared manifest.json (merged under its lock), textures/Sign_CT_Atlas1,
chinatown/manifest_chinatown.json (this lane's assets, budgets, sets), chinatown/signs_chinatown.json (every name, its
cell, carrier, colour), placements/placements_chinatown.json (the Canal north row N1..N6 assembled from the kits).
"""
import json
import os
import time

from assets import _chinatown_front as front
from assets import _chinatown_kit as kit
from assets import _chinatown_names as names
from mi import export, geo, paths, scene

FAMILY = {"name": "chinatown",
          "description": "Canal Street (Level 2): CT shop fronts, awnings, sign carriers and English sign atlas, neon, market, vendors, lanterns, street and roof props"}

OUT = os.path.join(paths.out, "chinatown")

# Triangle budgets per asset: chinatown.md 13.2, the upper end of each range (SM5 draws LOD0 / the Nanite fallback). The
# awnings and the far facade proxies have their rows in 13.2 since revision 4.
BUDGET = {
    "SM_Facade_Shopfront_CT_": 15000, "SM_Facade_CT_WindowGrille": 3000, "SM_Facade_CT_StackedSignRail": 3000,
    "SM_Facade_CT_Fascia": 3000, "SM_Facade_CT_Awning": 6000, "SM_Sign_CT_Neon_": 12000, "SM_Sign_CT_RooftopFrame": 12000,
    "SM_Sign_CT_": 12000, "SM_Prop_CT_StallCounter": 6000, "SM_Prop_CT_FishCounter": 6000, "SM_Prop_CT_Produce": 6000,
    "SM_Prop_CT_FruitStand": 6000, "SM_Prop_CT_Lantern": 600, "SM_Prop_CT_LanternString": 600, "SM_Prop_CT_Goods": 6000,
    "SM_Prop_CT_EBike": 6000, "SM_Prop_CT_": 6000, "SM_Facade_CT_Far_": 12000, "SM_Struct_CT_MarketHall": 40000, "SM_Struct_CT_ColdRoom": 6000,
    "SM_Struct_CT_RoofBulkhead": 4000, "SM_Struct_CT_YardStair": 12000, "SM_Struct_CT_SidewalkShed": 10000,
    "SM_Struct_CT_BakeryKitchen": 12000, "SM_Struct_CT_Arcade": 8000, "SM_Struct_CT_BanquetFacade": 40000,
    "SM_Prop_CT_Hydrant": 6000, "SM_Prop_TrashCan_Metal_LOD1": 2000,
    "SM_Furn_": 4000, "SM_Prop_": 4000, "SM_Decal_CT_": 100,
    "SM_Prop_CT_BanquetStage": 6000, "SM_Prop_CT_Standpipe": 1500, "SM_Prop_CT_BikeRack": 3000,
    "SM_Facade_CT_Alcove_": 9000, "SM_Facade_CT_Ground": 4000, "SM_Facade_CT_": 6000,
}


def budget(name):
    best = max((k for k in BUDGET if name.startswith(k)), key=len)
    return BUDGET[best]


def build(ctx):
    names.check_english()
    ctx.K = {}
    ctx.kit = scene.collection("ChinatownKit", ctx.col)
    from assets import _chinatown_atlas as atlas
    have = os.path.exists(os.path.join(paths.texture_set("Sign_CT_Atlas1"), "set.json"))
    if ctx.args.bake or not have:
        sets, cells = atlas.build_atlases(ctx.args.seed, log=ctx.log)
    ctx.sets.append("Sign_CT_Atlas1")
    M = kit.materials(ctx)
    ctx.M = M
    for f in kit.PROPS:
        f(ctx, M)
    from assets import _chinatown_props3 as props3
    from assets import _chinatown_props3b as props3b
    for f in props3.PROPS3 + props3b.PROPS3B:                                          # round 3: carts, lions, fittings, interiors
        f(ctx, M)
    front.build_front(ctx, M)
    from assets import _chinatown_decals as decals
    decals.build_decals(ctx)                                                           # round 3: graffiti, stencil, the near-ground wear pass
    from assets import _chinatown_struct as struct
    struct.build_structs(ctx, M)
    from assets import _chinatown_lod as lod
    lod.build_far_proxies(ctx)
    lod.build_prop_lods(ctx)
    tris = {n: geo.stats(o)["triangles"] for n, o in ctx.K.items()}
    ctx.log("%d assets, %d triangles in all, largest %s (%d)" % (len(tris), sum(tris.values()), max(tris, key=tris.get), max(tris.values())))
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
    with open(os.path.join(paths.texture_set("Sign_CT_Atlas1"), "set.json")) as f:
        atlas = json.load(f)
    rows = []
    for e in entries:
        cap = budget(e["name"])
        rows.append({"name": e["name"], "glb": e["glb"], "triangles": e["triangles"], "budget_tris": cap,
                     "within_budget": e["triangles"] <= cap, "size_m": e["bounds_m"]["size"],
                     "slots": [m["slot"] for m in e["material_slots"]], "collision": e["collision"]})
    man = {"about": "MAPS.md lane A-CT, Canal Street art (assets/chinatown.py). The GLBs and textures stay in art/out (git-ignored); "
                    "this file lists what the lane made and how it measures against chinatown.md 13 and 14.",
           "updated": time.strftime("%Y-%m-%dT%H:%M:%S"), "family": "chinatown", "count": len(rows),
           "triangles_total": sum(r["triangles"] for r in rows), "assets": rows,
           "texture_sets_new": ["Sign_CT_Atlas1", "CT_Decals"], "texture_sets_reused": sorted(s for s in ctx.sets if s.startswith("TS_")),
           "atlas": {"name": "Sign_CT_Atlas1", "resolution": atlas["resolution"], "faces": len(atlas["cells"]), "fill": atlas["fill"]},
           "rules": {"english_only": True, "strings_checked": names.check_english(), "real_marks": "none (IPX is not on this level's signs)",
                     "names_searched": "2026-11-26 (docs/unreal/maps/names.md); owner sign-off pending"}}
    with open(os.path.join(OUT, "manifest_chinatown.json"), "w") as f:
        json.dump(man, f, indent=1, sort_keys=True)
    signs = {"about": "Every word on a Canal Street sign (English only, invented names; assets/_chinatown_names.py) with its atlas "
                      "cell. A placed sign = its carrier mesh + an MI of M_Sign_CT_Face with the atlas textures and the cell's uv "
                      "rect (v up: uv' = uv * (u1 - u0, v1 - v0) + (u0, v0)); glow = the colour of its sign-wash light.",
             "faces": atlas["cells"], "neon": names.NEON, "other": names.OTHER_TEXT, "decal_text_not_built": names.DECAL_TEXT,
             "business_names": names.business_names(), "names_status": "invented; searched 2026-11-26 (MAPS.md C1, docs/unreal/maps/names.md), the colliding ones replaced; owner sign-off pending",
             "lantern_hooks_m": getattr(ctx, "lantern_hooks", None)}
    with open(os.path.join(OUT, "signs_chinatown.json"), "w") as f:
        json.dump(signs, f, indent=1, sort_keys=True)
    from assets import _chinatown_struct as struct
    struct.write_fit(ctx, os.path.join(OUT, "fit_chinatown.json"))
    from assets import _chinatown_place as place
    n = place.write_placements(os.path.join(paths.out, "placements", "placements_chinatown.json"))
    ctx.log("lane files: %d assets, %d faces, %d placements" % (len(rows), len(atlas["cells"]), n))


def on_preview(ctx, objs):
    from assets import _chinatown_preview as prev
    prev.render_all(ctx)
