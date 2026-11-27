"""Lane A-CT checks for the Canal Street art (run after `build.py build chinatown --export`).

    venv/bin/python art/blender/assets/_chinatown_check.py            # check the outputs in art/out
    venv/bin/python art/blender/assets/_chinatown_check.py --build    # build in memory and validate every asset (no files)

Checks (each prints PASS or FAIL with the evidence; the script exits 1 on any FAIL):
  1 english      every string on a sign, board, poster, neon or decal is printable ASCII (plus the middle dot and arrow):
                 no Chinese characters; the atlas set.json cells carry only those strings
  2 names        every business name is in the invented list (_chinatown_names), IPX appears on no Canal sign
  3 validation   every SM_*_CT_* asset passes mi.export.validate (names, scale, faces, winding, slots, UVs, Wear)
  4 budgets      triangles per asset within chinatown.md 13.2 (chinatown.BUDGET), none over 300k
  5 files        every manifest_chinatown.json asset has its GLB in art/out/glb and its record in the shared manifest with
                 the same triangle count and bounds
  6 atlas        Sign_CT_Atlas1 is 4096 x 4096 with BC, ORM, E; every face of the names table has a cell inside the page,
                 no two cells overlap, every carrier named by a face exists
  7 placements   every mesh placed in placements_chinatown.json is a Canal asset of this lane or a module of the Block's
                 facade kit in the shared manifest; every sign placed with a face has its cell
  8 block        facade.py, signs.py and place_buildings.py are unchanged against the branch head (the A0 rule: the Block's
                 outputs byte for byte)
  9 thin         (--build) no loose member longer than 0.6 m is thinner than 34 mm across (chinatown.md 13.4's 40 mm
                 railings with the hexagon's flat-to-flat allowance): flicker at render scale 0.50
 10 views        the north row's triangles in worst view 1 with the far proxies (chinatown.md 14: at most 1.5 M, aim 1.1 M)
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER_DIR = os.path.dirname(HERE)
if BLENDER_DIR not in sys.path:
    sys.path.insert(0, BLENDER_DIR)

from assets import _chinatown_names as names  # noqa: E402
from mi import paths  # noqa: E402

FAILS = []


def report(ok, what, detail=""):
    print("%s  %-11s %s" % ("PASS" if ok else "FAIL", what, detail), flush=True)
    if not ok:
        FAILS.append(what)


def load(p):
    with open(p) as f:
        return json.load(f)


def check_english():
    try:
        n = names.check_english()
        report(True, "english", "%d strings, all English (ASCII and the middle dot)" % n)
    except ValueError as e:
        report(False, "english", str(e))
    p = os.path.join(paths.texture_set("Sign_CT_Atlas1"), "set.json")
    if os.path.exists(p):
        cells = load(p)["cells"]
        bad = [(k, t) for k, c in cells.items() for t in c["text"] if any(ch not in names.ALLOWED for ch in t)]
        report(not bad, "english", "atlas cells: %d faces, %s" % (len(cells), bad or "no other script"))
    biz = names.business_names()
    ipx = [k for k, v in biz.items() if "IPX" in v.upper()]
    report(not ipx, "names", "%d invented business names, IPX on none (%s)" % (len(biz), ipx or "ok"))


def check_build():
    import argparse
    import bpy  # noqa: F401  (bmesh needs bpy loaded first)
    from mi import export, scene
    import build as B
    args = argparse.Namespace(bake=False, export=False, preview=False, res=2048, samples=16, tile_samples=4, seed=0, only=None,
                              force=False, fbx=False, rebake_unique=False)
    from assets import chinatown
    scene.reset(samples=16)
    ctx = B.Ctx("chinatown", args)
    chinatown.build(ctx)
    errs, over = 0, 0
    from mi import geo
    for name, a in ctx.assets.items():
        e, w = export.validate(a["ob"], a["expect_size"])
        t = geo.stats(a["ob"])["triangles"]
        cap = chinatown.budget(name)
        if e:
            errs += 1
            print("    %s: %s" % (name, "; ".join(e)))
        if t > cap:
            over += 1
            print("    %s: %d triangles, budget %d" % (name, t, cap))
    report(errs == 0, "validation", "%d assets, %d failing" % (len(ctx.assets), errs))
    report(over == 0, "budgets", "%d over budget" % over)
    # thin members: chinatown.md 13.4 (railings 40 mm or more; no thin steel on the critical-path sight lines). A loose part
    # longer than 0.6 m must be 34 mm or more across (a 40 mm tube with the hexagon's flat-to-flat allowance): thinner
    # lines crawl at render scale 0.50 (READY.md R3)
    from assets._midtown_check import thin_members
    thin = {}
    for name, a in ctx.assets.items():
        tm = thin_members(a["ob"], min_w=0.034, min_len=0.6)
        if tm:
            thin[name] = tm[:3]
    for k, v in thin.items():
        print("    %s: %s" % (k, v))
    report(not thin, "thin", "no loose member longer than 0.6 m is thinner than 34 mm across (%d assets)" % len(ctx.assets)
           if not thin else "%d assets with thin members" % len(thin))


def check_outputs():
    from assets import chinatown
    lane = os.path.join(paths.out, "chinatown", "manifest_chinatown.json")
    if not os.path.exists(lane):
        report(False, "files", "no %s: run build.py build chinatown --export" % lane)
        return
    man = load(lane)
    shared = load(paths.manifest)["assets"]
    missing, mism, over = [], [], []
    for r in man["assets"]:
        g = os.path.join(paths.out, r["glb"])
        if not os.path.exists(g):
            missing.append(r["name"])
        s = shared.get(r["name"])
        if not s or s["triangles"] != r["triangles"] or s["bounds_m"]["size"] != r["size_m"]:
            mism.append(r["name"])
        if r["triangles"] > chinatown.budget(r["name"]) or r["triangles"] > 300000:
            over.append((r["name"], r["triangles"]))
    report(not missing and not mism, "files", "%d assets, %d GLBs missing, %d differ from the shared manifest %s"
           % (len(man["assets"]), len(missing), len(mism), (missing + mism)[:5]))
    tot = sum(r["triangles"] for r in man["assets"])
    report(not over, "budgets", "%d assets within chinatown.md 13.2, %d triangles in all, largest %s %s"
           % (len(man["assets"]) - len(over), tot, max(man["assets"], key=lambda r: r["triangles"])["name"], over or ""))
    # atlas
    d = paths.texture_set("Sign_CT_Atlas1")
    info = load(os.path.join(d, "set.json"))
    from PIL import Image
    sizes = {r: Image.open(os.path.join(d, f)).size for r, f in info["files"].items()}
    cells = info["cells"]
    rects = [(k, c["px"]) for k, c in cells.items()]
    overlap = [(a[0], b[0]) for i, a in enumerate(rects) for b in rects[i + 1:]
               if a[1][0] < b[1][0] + b[1][2] and b[1][0] < a[1][0] + a[1][2] and a[1][1] < b[1][1] + b[1][3] and b[1][1] < a[1][1] + a[1][3]]
    outside = [k for k, (x, y, w, h) in rects if x < 0 or y < 0 or x + w > 4096 or y + h > 4096]
    nocell = [k for k in names.FACES if k not in cells]
    carriers = {f["carrier"] for f in names.FACES.values()}
    nocarrier = sorted(c for c in carriers if c not in shared)
    report(sizes.get("BC") == (4096, 4096) and "E" in sizes and not overlap and not outside and not nocell and not nocarrier, "atlas",
           "BC %s ORM %s E %s, %d cells, fill %.0f %%, overlaps %s, outside %s, faces without a cell %s, carriers missing %s"
           % (sizes.get("BC"), sizes.get("ORM"), sizes.get("E"), len(cells), info["fill"] * 100, overlap or 0, outside or 0, nocell or 0,
              nocarrier or 0))
    # placements
    pl = load(os.path.join(paths.out, "placements", "placements_chinatown.json"))
    unknown = sorted({e["mesh"] for e in pl["instances"] if e["mesh"] not in shared})
    noface = [e["mesh"] for e in pl["instances"] if e.get("face") and "atlas_uv" not in e]
    check_fit(pl, shared)
    check_round3(pl, shared)
    report(not unknown and not noface, "placements", "%d instances of %d meshes, unknown %s, faces without a cell %s"
           % (pl["count"], len({e["mesh"] for e in pl["instances"]}), unknown or 0, noface or 0))


def check_fit(pl, shared):
    """11 fit      every structure's vertices inside its lane D colliders (or a named allowed region), 0 unexplained; every
                 structure placed at its colliders' min corner; every north-row alcove is the real recess
       12 stretch  no instance anywhere is scaled (the review's rule)
       13 signs    every shop front of every face has a sign on its face within 8 m (assets/_chinatown_streets.sign_coverage)
       14 props    every prop of lane D that has a mesh stands on its colliders: the worst overhang"""
    from assets import _chinatown_level as lv
    fit = os.path.join(paths.out, "chinatown", "fit_chinatown.json")
    if not os.path.exists(fit):
        report(False, "fit", "no %s" % fit)
        return
    rep = load(fit)
    bad = {k: v["outside_unexplained"] for k, v in rep["structures"].items() if v["outside_unexplained"]}
    placed = {e["mesh"]: e for e in pl["instances"] if e["role"] == "structure"}
    off = []
    for name, piv, _cols in lv.struct_places():
        e = placed.get(name)
        if not e or max(abs(a - b) for a, b in zip(e["blender_m"], piv)) > 1e-3:
            off.append(name)
    report(not bad and not off and len(rep["structures"]) == len(lv.STRUCTS), "fit",
           "%d structures fitted to %d colliders of %s: %d vertices outside, unexplained %s, misplaced %s"
           % (len(rep["structures"]), sum(v["colliders"] for v in rep["structures"].values()), rep["level"],
              sum(v["outside_colliders"] for v in rep["structures"].values()), bad or 0, off or 0))
    scaled = [e["mesh"] for e in pl["instances"] if e.get("scale")]
    report(not scaled, "stretch", "%d instances, %d scaled %s" % (pl["count"], len(scaled), sorted(set(scaled))[:5] or ""))
    from assets import _chinatown_streets as st
    nfr, miss = st.sign_coverage(pl["instances"])
    report(not miss, "signs", "%d shop fronts, every one with a sign over it; without: %s" % (nfr, miss or 0))
    worst = max((r["overhang_m"] for r in pl.get("propFit", [])), default=0.0)
    report(worst <= 1.1, "props", "%d prop groups on their colliders, worst overhang %.2f m (jersey barriers 3 m on shorter boxes)"
           % (len(pl.get("propFit", [])), worst))


PLANNED = ("food_cart", "hotpot_cart", "stone_lion", "trash_bags", "fruit_stand", "standpipe", "bike_rack", "chair_stack", "grease_bin",
           "roof_vent", "exhaust_fan", "exhaust_stack", "bakery_counter", "bakery_ovens", "tray_racks", "flour_sacks", "kitchen_table",
           "kitchen_range", "kitchen_counter", "kitchen_rack", "tape_racks", "cutting_table", "disc_burners", "kiosk_counter", "tube_bundles",
           "bending_bench", "banquet_table", "banquet_stage", "planter", "bucket_stack", "sandwich_board", "cd_rack", "road_plates", "dig_fence")


def check_round3(pl, shared):
    from assets import _chinatown_lod as lod
    from assets import _chinatown_level as lv
    from assets import _chinatown_names as nm
    # 14 lods
    inst = pl["instances"]
    seen = {}
    for e in inst:
        if e["mesh"] in shared and lod.in_view(lod.instance_box(e, shared[e["mesh"]]), lod.VIEW1):
            seen[e["mesh"]] = seen.get(e["mesh"], 0) + 1
    need = sorted(m for m, n in seen.items() if n >= 3 and shared[m]["triangles"] > 1500 and m.startswith(("SM_Prop", "SM_Furn")) and "Pallet" not in m
                  and not m.endswith("_Hydrant"))
    nolod = [m for m in need if m + "_LOD1" not in shared]
    bad = []
    for m in sorted(shared):
        for k in ("_LOD1", "_LOD2"):
            if m.endswith(k) and m[:-len(k)] in shared:
                a, b = shared[m[:-len(k)]], shared[m]
                if [x["slot"] for x in a["material_slots"]] != [x["slot"] for x in b["material_slots"]] and "Decal" not in m:
                    bad.append((m, "slots"))
                if max(abs(x - y) for x, y in zip(a["bounds_m"]["size"], b["bounds_m"]["size"])) > 0.05 * max(a["bounds_m"]["size"]) + 0.02:
                    bad.append((m, "size"))
                if b["triangles"] >= a["triangles"] and a["triangles"] > 500:
                    bad.append((m, "not lighter"))
    order = [m for m in shared if m.endswith("_LOD2") and m[:-5] + "_LOD1" in shared and shared[m]["triangles"] >= shared[m[:-5] + "_LOD1"]["triangles"]]
    n1 = sum(1 for m in shared if m.endswith("_LOD1") and "_CT_" in m or m.endswith("_LOD1") and m[:-5] in shared)
    n2 = sum(1 for m in shared if m.endswith("_LOD2"))
    report(not nolod and not bad and not order, "lods", "%d LOD1 and %d LOD2 meshes; heavy props placed 3 times or more in the worst view without a LOD1: %s; mismatches %s; LOD2 not lighter %s"
           % (n1, n2, nolod or 0, bad[:4] or 0, order or 0))
    # 15 decals
    decals = [e for e in inst if e["role"] == "decal"]
    approved = {t.replace("\u2192", "").strip() for ws in nm.DECAL_TEXT.values() for t in ws}
    cells = load(os.path.join(paths.texture_set("CT_Decals"), "set.json"))["cells"]
    texts = {t for c in cells.values() for t in c["text"]}
    ids = sorted(e.get("dataSign") for e in decals)
    wear = [e for e in inst if e["role"] == "wear decal"]
    grounds = {F.key for F, _s, _b, _k, _g, o in __import__("assets._chinatown_streets", fromlist=["x"]).faces() if o.get("ground", True)}
    covered = {e.get("faceKey") for e in wear}
    scaled = [e["mesh"] for e in decals + wear if e.get("scale")]
    ok = (ids == ["alley.stencil", "graffiti.0", "graffiti.1", "graffiti.2", "graffiti.3"] and texts <= approved and not scaled
          and covered == grounds and all(e["mesh"] in shared for e in decals + wear))
    report(ok, "decals", "%d decal rows placed %s (texts %s, all on the approved list); the wear pass: %d pieces on %d of %d ground walls; scaled %d"
           % (len(decals), ids, sorted(texts), len(wear), len(covered & grounds), len(grounds), len(scaled)))
    # 16 props3
    placed = {e.get("prop") for e in inst if e["role"] == "prop"}
    unmapped = pl.get("unmappedProps", {})
    missing = [n for n in PLANNED if n not in placed or n in unmapped]
    report(not missing, "props3", "%d planned prop kinds, all placed from the colliders (not placed: %s); still unmapped: %s"
           % (len(PLANNED), missing or 0, sorted(unmapped)))


def check_views():
    """chinatown.md 14: worst view 1 (Canal St from the start, looking east) at most 1.5 M triangles drawn, aim 1.1 M. The
    north row is the only part placed so far, so its share must leave room for the south row, the vehicles and the
    road: it passes at 0.55 M or less with the far proxies (half the aim)."""
    from assets import _chinatown_lod as lod
    try:
        full, prox, rows = lod.view_triangles()
    except (OSError, KeyError) as e:
        report(False, "views", "cannot measure: %s" % e)
        return
    for b, r in rows.items():
        print("    %s: %s" % (b, r))
    north = sum(r["trianglesDrawn"] for b, r in rows.items() if b in ("N1", "N2", "N3", "N4", "N5", "N6"))
    report(prox <= 1500000 and north <= 550000, "views",
           "worst view 1, every placed piece in the frustum: %d triangles with every module at LOD0, %d with the far proxies past "
           "%.0f m (budget 1.5 M; aim 1.1 M: %s); the north row's share %d (at most 0.55 M)"
           % (full, prox, lod.LOD_SWITCH, "met" if prox <= 1100000 else "over by %d, the props' LODs are the lever" % (prox - 1100000), north))


def check_block():
    repo = os.path.dirname(os.path.dirname(BLENDER_DIR))
    files = ["art/blender/assets/facade.py", "art/blender/assets/signs.py", "art/blender/place_buildings.py",
             "unreal/MurderInc/Content/Data/levels.json", "unreal/MurderInc/Content/Data/level.json",
             "unreal/MurderInc/Content/Data/art_catalogue.json"]
    r = subprocess.run(["git", "-C", repo, "diff", "--stat", "HEAD", "--"] + files, capture_output=True, text=True)
    r2 = subprocess.run(["git", "-C", repo, "log", "--oneline", "-1", "--"] + files, capture_output=True, text=True)
    report(r.returncode == 0 and not r.stdout.strip(), "block", "no working change to %d Block files (last commit touching them: %s)"
           % (len(files), r2.stdout.strip()[:60]))


if __name__ == "__main__":
    check_english()
    if "--build" in sys.argv:
        check_build()
    else:
        check_outputs()
        check_views()
    check_block()
    print("ALL CHECKS PASS" if not FAILS else "FAILED: %s" % ", ".join(FAILS))
    sys.exit(1 if FAILS else 0)
