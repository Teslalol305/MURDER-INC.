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
    report(not unknown and not noface, "placements", "%d instances of %d meshes, unknown %s, faces without a cell %s"
           % (pl["count"], len({e["mesh"] for e in pl["instances"]}), unknown or 0, noface or 0))


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
    check_block()
    print("ALL CHECKS PASS" if not FAILS else "FAILED: %s" % ", ".join(FAILS))
    sys.exit(1 if FAILS else 0)
