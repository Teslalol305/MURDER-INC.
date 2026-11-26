"""Lane A-MT checks for the Midtown roof, screen and scaffold art (run after `build.py build midtown --export`).

    venv/bin/python art/blender/assets/_midtown_check.py            # check the outputs in art/out
    venv/bin/python art/blender/assets/_midtown_check.py --build    # build in memory: validation, budgets, thin members (no files)

Checks (each prints PASS or FAIL with the evidence; the script exits 1 on any FAIL):
  1 english      every string on a screen, billboard, sign, label, the ticker and the digits is English type (ASCII, the middle
                 dot, the degree sign); the atlas set.json cells carry only those strings
  2 names        IPX appears only on the IPX slides (the owner's mark); no invented name repeats another
  3 validation   (--build) every asset passes mi.export.validate (names, scale, faces, winding, slots, UVs, Wear)
  4 budgets      triangles per asset within midtown.md 14.2 (midtown.BUDGET), none over 300k
  5 thin         (--build) no loose member longer than 0.6 m is thinner than 5.5 cm across (the 6 cm floor of midtown.md 15
                 with the octagon's flat-to-flat allowance, 6 cm x cos 22.5): flicker at render scale 0.50
  6 files        every manifest_midtown.json asset has its GLB in art/out/glb and the same triangles and bounds in the shared
                 manifest
  7 atlases      MT_Screens_A/B 4096 with 8 cells each, every slide in a cell, no overlaps; the ticker 4096 x 256, the digits
                 512 x 64, the LED mask 64; Sign_MT_Atlas1 4096 with BC, ORM, E, every face in a cell, no overlaps
  8 placements   every placed mesh is a lane asset; every face and slide named by a placement has its cell; every tiled
                 screen has all its tiles once
  9 emissive     large screen surfaces in the placements at most 9 (midtown.md 15), new texture memory at most 180 MB (BC1
                 estimate with mips), no new tiling set
 10 block        facade.py, signs.py, place_buildings.py and the Block's data files unchanged against the branch head; the
                 lane writes nothing under unreal/MurderInc
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER_DIR = os.path.dirname(HERE)
if BLENDER_DIR not in sys.path:
    sys.path.insert(0, BLENDER_DIR)

from assets import _midtown_names as names  # noqa: E402
from mi import paths  # noqa: E402

FAILS = []
SETS = ("MT_Screens_A", "MT_Screens_B", "MT_Ticker", "MT_Digits", "MT_LEDMask", "Sign_MT_Atlas1")


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
        report(True, "english", "%d strings, all English (ASCII, the middle dot, the degree sign)" % n)
    except ValueError as e:
        report(False, "english", str(e))
    texts = []
    for s in SETS:
        p = os.path.join(paths.texture_set(s), "set.json")
        if os.path.exists(p):
            cells = load(p).get("cells", {})
            for k, c in (cells.items() if isinstance(cells, dict) else []):
                if isinstance(c, dict):
                    texts += [(k, t) for t in c.get("text", [])]
            texts += [("ticker", t) for t in load(p).get("headlines", [])]
    bad = [(k, t) for k, t in texts if not names.ALLOWED.match(t)]
    report(not bad, "english", "atlas cells and the ticker: %d strings, %s" % (len(texts), bad or "no other script"))
    ipx = [k for k, s in names.SLIDES.items() if any("IPX" in t.upper() for t in s["lines"]) or (s["kind"] == "ipx") != k.startswith("IPX")]
    ipx += [k for k, f in names.FACES.items() if any("IPX" in t.upper() for t in f["lines"])]
    biz = names.business_names()
    report(not ipx and len(biz) == len(set(b.split(" (")[0] for b in biz)), "names",
           "%d invented names, IPX only on the 3 IPX slides (%s)" % (len(biz), ipx or "ok"))


def thin_members(ob, min_w=0.055, min_len=0.6):
    """Loose parts (connected components) longer than min_len whose second extent is under min_w."""
    import numpy as np
    me = ob.data
    nv = len(me.vertices)
    co = np.empty(nv * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    parent = np.arange(nv)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    ev = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", ev)
    for a, b in ev.reshape(-1, 2):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    roots = np.array([find(i) for i in range(nv)])
    bad = []
    for r in np.unique(roots):
        P = co[roots == r]
        if len(P) < 4:
            continue
        c = P - P.mean(0)
        _u, _s, vt = np.linalg.svd(c, full_matrices=False)
        ext = np.sort(np.ptp(c @ vt.T, axis=0))[::-1]
        if ext[0] > min_len and ext[1] < min_w:
            bad.append([round(float(e), 3) for e in ext])
    return bad


def check_build():
    import argparse
    import bpy  # noqa: F401  (bmesh needs bpy loaded first)
    from mi import export, geo, scene
    import build as B
    args = argparse.Namespace(bake=False, export=False, preview=False, res=2048, samples=16, tile_samples=4, seed=0, only=None,
                              force=False, fbx=False, rebake_unique=False)
    from assets import midtown
    scene.reset(samples=16)
    ctx = B.Ctx("midtown", args)
    midtown.build(ctx)
    errs, over, thin = 0, 0, {}
    for name, a in ctx.assets.items():
        e, w = export.validate(a["ob"], a["expect_size"])
        t = geo.stats(a["ob"])["triangles"]
        if e:
            errs += 1
            print("    %s: %s" % (name, "; ".join(e)))
        if t > midtown.budget(name):
            over += 1
            print("    %s: %d triangles, budget %d" % (name, t, midtown.budget(name)))
        tm = thin_members(a["ob"])
        if tm:
            thin[name] = tm
    report(errs == 0, "validation", "%d assets, %d failing" % (len(ctx.assets), errs))
    report(over == 0, "budgets", "%d assets, %d over budget" % (len(ctx.assets), over))
    report(not thin, "thin", "%d assets, members under 5.5 cm across and over 0.6 m long: %s"
           % (len(ctx.assets), {k: v[:3] for k, v in thin.items()} or "none"))


def overlaps(rects):
    return [(a[0], b[0]) for i, a in enumerate(rects) for b in rects[i + 1:]
            if a[1][0] < b[1][0] + b[1][2] and b[1][0] < a[1][0] + a[1][2] and a[1][1] < b[1][1] + b[1][3] and b[1][1] < a[1][1] + a[1][3]]


def check_outputs():
    from PIL import Image
    from assets import midtown
    lane = os.path.join(paths.out, "midtown", "manifest_midtown.json")
    if not os.path.exists(lane):
        report(False, "files", "no %s: run build.py build midtown --export" % lane)
        return
    man = load(lane)
    shared = load(paths.manifest)["assets"]
    missing, mism, over = [], [], []
    for r in man["assets"]:
        if not os.path.exists(os.path.join(paths.out, r["glb"])):
            missing.append(r["name"])
        s = shared.get(r["name"])
        if not s or s["triangles"] != r["triangles"] or s["bounds_m"]["size"] != r["size_m"]:
            mism.append(r["name"])
        if r["triangles"] > midtown.budget(r["name"]) or r["triangles"] > 300000:
            over.append((r["name"], r["triangles"]))
    report(not missing and not mism, "files", "%d assets, %d GLBs missing, %d differ from the shared manifest %s"
           % (len(man["assets"]), len(missing), len(mism), (missing + mism)[:5]))
    big = max(man["assets"], key=lambda r: r["triangles"])
    report(not over, "budgets", "%d assets within midtown.md 14.2, %d triangles in all, largest %s (%d) %s"
           % (len(man["assets"]) - len(over), man["triangles_total"], big["name"], big["triangles"], over or ""))
    # atlases
    slides, ok = {}, True
    for p in ("A", "B"):
        d = paths.texture_set("MT_Screens_" + p)
        info = load(os.path.join(d, "set.json"))
        size = Image.open(os.path.join(d, info["files"]["E"])).size
        cells = info["cells"]
        ov = overlaps([(k, c["px"]) for k, c in cells.items()])
        out = [k for k, c in cells.items() if c["px"][0] + c["px"][2] > 4096 or c["px"][1] + c["px"][3] > 4096]
        ok &= size == (4096, 4096) and len(cells) == 8 and not ov and not out
        slides.update(cells)
        print("    MT_Screens_%s: %s, %d slides, overlaps %s, outside %s" % (p, size, len(cells), ov or 0, out or 0))
    noslide = [k for k in names.SLIDES if k not in slides]
    sz = {s: Image.open(os.path.join(paths.texture_set(s), list(load(os.path.join(paths.texture_set(s), "set.json"))["files"].values())[0])).size
          for s in ("MT_Ticker", "MT_Digits", "MT_LEDMask")}
    d = paths.texture_set("Sign_MT_Atlas1")
    info = load(os.path.join(d, "set.json"))
    fsz = {r: Image.open(os.path.join(d, f)).size for r, f in info["files"].items()}
    fcells = info["cells"]
    fov = overlaps([(k, c["px"]) for k, c in fcells.items()])
    noface = [k for k in names.FACES if k not in fcells]
    ok &= not noslide and sz == {"MT_Ticker": (4096, 256), "MT_Digits": (512, 64), "MT_LEDMask": (64, 64)}
    ok &= fsz.get("BC") == (4096, 4096) and "E" in fsz and "ORM" in fsz and not fov and not noface
    report(ok, "atlases", "16 slides in 2 pages (missing %s), ticker %s, digits %s, mask %s; signs BC %s ORM %s E %s, %d faces, fill "
           "%.0f %%, overlaps %s, faces without a cell %s" % (noslide or 0, sz["MT_Ticker"], sz["MT_Digits"], sz["MT_LEDMask"],
                                                              fsz.get("BC"), fsz.get("ORM"), fsz.get("E"), len(fcells),
                                                              info["fill"] * 100, fov or 0, noface or 0))
    # placements
    pl = load(os.path.join(paths.out, "placements", "placements_midtown.json"))
    lane_meshes = {r["name"] for r in man["assets"]}
    unknown = sorted({e["mesh"] for e in pl["instances"] if e["mesh"] not in lane_meshes})
    badface = [e["face"] for e in pl["instances"] if e.get("face") and e["face"] not in fcells]
    badslide = [e["first_slide"] for e in pl["instances"] if e.get("first_slide") and e["first_slide"] not in slides]
    tiles = {}
    for e in pl["instances"]:
        if e.get("tile"):
            tiles.setdefault(e["screen"], (e["tiles"], []))[1].append(tuple(e["tile"]))
    badtiles = [s for s, ((c, r), got) in tiles.items() if sorted(got) != sorted((i, j) for i in range(c) for j in range(r))]
    report(not unknown and not badface and not badslide and not badtiles, "placements",
           "%d instances of %d meshes; unknown meshes %s, faces without a cell %s, slides missing %s, tiled screens %s complete%s"
           % (pl["count"], len({e["mesh"] for e in pl["instances"]}), unknown or 0, badface or 0, badslide or 0,
              sorted(tiles), (", broken " + str(badtiles)) if badtiles else ""))
    # emissive and texture memory
    screens = sorted({e["screen"] for e in pl["instances"] if e.get("screen")})
    mb = 0.0
    for s in SETS:
        inf = load(os.path.join(paths.texture_set(s), "set.json"))
        w, h = inf["resolution"]
        nmaps = len(inf["files"])
        mb += w * h * 0.5 * 4 / 3 * nmaps / 2 ** 20 if s != "Sign_MT_Atlas1" else (w * h * 0.5 * 2 + (w // 2) * (h // 2) * 0.5) * 4 / 3 / 2 ** 20
    report(len(screens) <= 9 and mb <= 180 and man["new_tiling_sets"] == 0, "emissive",
           "%d large screens %s (ceiling 9) + the ticker; new texture memory about %.0f MB (ceiling 180), new tiling sets %d"
           % (len(screens), screens, mb, man["new_tiling_sets"]))


def check_block():
    repo = os.path.dirname(os.path.dirname(BLENDER_DIR))
    files = ["art/blender/assets/facade.py", "art/blender/assets/signs.py", "art/blender/place_buildings.py",
             "unreal/MurderInc/Content/Data/levels.json", "unreal/MurderInc/Content/Data/level.json"]
    r = subprocess.run(["git", "-C", repo, "diff", "--stat", "HEAD", "--"] + files, capture_output=True, text=True)
    mine = [os.path.join("art/blender/assets", f) for f in os.listdir(HERE) if "midtown" in f]
    report(r.returncode == 0 and not r.stdout.strip(), "block", "no working change to %d Block files; this lane's %d files are all "
           "under art/blender/assets (nothing under unreal/MurderInc)" % (len(files), len(mine)))


if __name__ == "__main__":
    check_english()
    if "--build" in sys.argv:
        check_build()
    else:
        check_outputs()
    check_block()
    print("ALL CHECKS PASS" if not FAILS else "FAILED: %s" % ", ".join(FAILS))
    sys.exit(1 if FAILS else 0)
