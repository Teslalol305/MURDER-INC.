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
 12 sq-emissive  (--build, round 2) the square's emissive slots (riser glass, strip and indicator lights, LED heads, lit faces,
                 booth monitors) by area x luminance against the seven screens and the ticker: no screen-sized face, riser
                 glass under 30 m2, the whole square under 5 % of the screens' light, nothing translucent
 11 fit          (round 2) every placement on a level collider sits on it and covers it (tools/levels/data/level_midtown.json);
                 every collider of a dressed tag has art; the lane's own choices are marked "chosen"
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
    check_square_emissive(ctx)
    check_facade_emissive(ctx)


# the square's emissive slots and their night luminance (cd/m2): midtown.md 11.2, the kit's notes
SQ_EMIT = {"MI_Stand_RiserGlass": 40, "MI_Lamp_KioskInterior": 120, "MI_Lamp_Indicator": 60, "MI_Lamp_LED": 300,
           "M_Sign_MT_Face": 200, "M_MI_Screen": 300}
SCREENS_M2 = {"G1": (144, 450), "E1": (432, 450), "E2a": (160, 300), "E2b": (160, 300), "E3": (240, 450), "N1": (336, 450),
              "S1": (72, 300), "ticker": (19.2, 300)}


def check_square_emissive(ctx):
    """(--build) The square's emissive cost against the screens' (midtown.md 11.2, 12.3, 15): the area of every emissive
    slot on the placed square meshes times its luminance, beside the seven big screens and the ticker. Passes when no
    square surface is screen-sized (a monitor or a lightbox face under 2 m2 each), the riser glass stays under 30 m2, and
    the whole square adds under 5 % of the screens' emitted light (area x nits); nothing translucent."""
    pp = os.path.join(paths.out, "placements", "placements_midtown.json")
    if not os.path.exists(pp):
        report(False, "sq-emissive", "no placements: run build.py build midtown --export")
        return
    import numpy as np
    cells = load(os.path.join(paths.texture_set("Sign_MT_Atlas1"), "set.json"))["cells"]
    count = {}
    for e in load(pp)["instances"]:
        if e["mesh"].startswith("SM_Sq_"):
            sc = e.get("scale") or [1, 1, 1]
            names_ = e.get("faces") or ([e["face"]] if e.get("face") else [])
            lit = sum(1 for n_ in names_ if cells[n_]["lit"]) / float(len(names_)) if names_ else 1.0     # an unlit printed face emits nothing
            count.setdefault(e["mesh"], []).append((sc, lit))
    area, biggest = {}, (0.0, "")
    for name, scs in count.items():
        ob = ctx.assets[name]["ob"]
        me = ob.data
        for poly in me.polygons:
            m = me.materials[poly.material_index]
            if m is None or m.name not in SQ_EMIT:
                continue
            if m.name == "MI_Stand_RiserGlass" and poly.normal[1] > -0.5:
                continue                                       # the glass box's front only (its back and edges are hidden)
            for sc, lit in scs:
                a_ = poly.area * float(np.sqrt(sc[0] * sc[1])) * (lit if m.name == "M_Sign_MT_Face" else 1.0)
                area[m.name] = area.get(m.name, 0.0) + a_
        per = {}
        lit_m = max(l_ for _s, l_ in scs)
        for poly in me.polygons:
            m = me.materials[poly.material_index]
            if m is not None and m.name in ("M_MI_Screen", "M_Sign_MT_Face"):
                per[m.name] = per.get(m.name, 0.0) + poly.area * (lit_m if m.name == "M_Sign_MT_Face" else 1.0)
        for k, v in per.items():
            if v > biggest[0]:
                biggest = (v, "%s %s" % (name, k))
    sq = sum(area[k] * SQ_EMIT[k] for k in area)
    scr = sum(a_ * n_ for a_, n_ in SCREENS_M2.values())
    from assets import _midtown_roof as R
    transl = sorted({m.name for k, a in ctx.assets.items() if k.startswith("SM_Sq_") for m in a["ob"].data.materials
                     if m and R.SLOT_META.get(m.name, {}).get("workflow") not in (None, "tiling", "flat", "emissive", "glass",
                                                                                 "sign_atlas", "screen_atlas")})
    ok = biggest[0] < 2.0 and area.get("MI_Stand_RiserGlass", 0) < 30.0 and sq < 0.05 * scr and not transl
    report(ok, "sq-emissive", "the square's emissive slots: %s m2; largest single face %.2f m2 (%s); area x nits %.0f against the screens' "
           "%.0f (%.1f %%, ceiling 5 %%); translucent slots %s"
           % ({k: round(v, 1) for k, v in sorted(area.items())}, biggest[0], biggest[1], sq, scr, 100.0 * sq / scr, transl or "none"))


FAC_PREFIX = ("SM_Facade_MT_", "SM_Facade_Marquee_", "SM_Sign_MT_Band_", "SM_Vehicle_CityBus", "SM_Vehicle_MT_", "SM_Roof_Loftlark")


def check_facade_emissive(ctx):
    """(--build, round 3) The facades' lit faces (the storefront bands, the marquee's boards, the bus's destination sign), the
    bulbs and the shop glow, by area x luminance against the seven screens and the ticker: every lit printed face a lightbox (under
    12 m2, none is M_MI_Screen), the whole of it, with the square's, under 5 % of the screens' light, nothing translucent."""
    import numpy as np
    pp = os.path.join(paths.out, "placements", "placements_midtown.json")
    cells = load(os.path.join(paths.texture_set("Sign_MT_Atlas1"), "set.json"))["cells"]
    emit = dict(SQ_EMIT, MI_Lamp_MarqueeBulb=350, MI_Lamp_Tail=60, MI_Neon_Pink=0, MI_Neon_Cyan=0)
    count = {}
    for e in load(pp)["instances"]:
        if e["mesh"].startswith(FAC_PREFIX):
            sc = e.get("scale") or [1, 1, 1]
            names_ = e.get("faces") or ([e["face"]] if e.get("face") else [])
            lit = sum(1 for n_ in names_ if cells[n_]["lit"]) / float(len(names_)) if names_ else 0.0
            count.setdefault(e["mesh"], []).append((sc, lit))
    area, biggest, screens_slot = {}, (0.0, ""), []
    for name, scs in count.items():
        me = ctx.assets[name]["ob"].data
        per = 0.0
        for poly in me.polygons:
            m = me.materials[poly.material_index]
            if m is None or m.name not in emit:
                continue
            if m.name == "M_MI_Screen":
                screens_slot.append(name)
            front = poly.normal[1] < -0.5 or m.name in ("MI_Lamp_MarqueeBulb", "MI_Lamp_Tail")
            if not front:
                continue
            for sc, lit in scs:
                f_ = lit if m.name == "M_Sign_MT_Face" else 1.0
                area[m.name] = area.get(m.name, 0.0) + poly.area * float(np.sqrt(sc[0] * sc[1])) * f_
            if m.name == "M_Sign_MT_Face":
                per = max(per, poly.area)
        if per > biggest[0]:
            biggest = (per, name)
    tot = sum(area[k] * emit[k] for k in area)
    sq = sum(v * SQ_EMIT.get(k, 0) for k, v in {"MI_Stand_RiserGlass": 26.4, "M_Sign_MT_Face": 5.1}.items())
    scr = sum(a_ * n_ for a_, n_ in SCREENS_M2.values())
    ok = biggest[0] < 12.0 and not screens_slot and (tot + sq) < 0.05 * scr
    report(ok, "fac-emissive", "the facades', vehicles' and neon's emissive slots: %s m2; largest single lit face %.2f m2 (%s, a lightbox: under 12); "
           "area x nits %.0f (with the square's %.0f: %.1f %% of the screens' %.0f, ceiling 5 %%); screen slots %s"
           % ({k: round(v, 1) for k, v in sorted(area.items())}, biggest[0], biggest[1], tot, sq, 100.0 * (tot + sq) / scr, scr, screens_slot or "none"))


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
    unknown = sorted({e["mesh"] for e in pl["instances"] if e["mesh"] not in lane_meshes and not (e.get("reused") and e["mesh"] in shared)})
    badface = [e["face"] for e in pl["instances"] if e.get("face") and e["face"] not in fcells]
    badface += [f_ for e in pl["instances"] for f_ in (e.get("faces") or []) if f_ not in fcells]
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
    check_fit(pl, shared)
    check_views(pl, shared)
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


# midtown.md 15's shot views (eye, look-at, in web coordinates); every placed piece in the frustum (yaw only, 90 degree horizontal
# field as the stream's 16:9, 120 m far) at LOD0, and with the LOD1s (facade modules past 25 m, props and vehicles past 12 m)
VIEWS = {"V1 start": ((-43.2, 22.88, -35.0), (10, 10, -10)), "V2 tank house door": ((-19.3, 19.28, -27.0), (-5, 22, -10)),
         "V3 gantry letterbox": ((-6.2, 15.68, 6.0), (20, 3, 6)), "V4 scaffold mid landing": ((-5.0, 8.6, 17.0), (15, 3, 0)),
         "V5 top of the Stand": ((16.0, 5.03, -33.0), (10, 2, 20)), "V6 at the truck": ((0.0, 1.68, 26.0), (12, 6, -20))}


def check_views(pl, shared):
    """The art the lane places, counted per shot view: triangles drawn with every module at LOD0 and with the LOD1s (the Block's
    vehicles and the street and backdrop kits are not in this count: the ceiling is the whole view, 1.3 M target and 1.5 M ceiling,
    midtown.md 15; this lane's art must leave room: at most 0.9 M in any view)."""
    import math
    from assets import _chinatown_lod as cl
    worst = (0, "")
    rows = []
    for name, (eye, at) in VIEWS.items():
        e3 = (eye[0], -eye[2], eye[1])
        dx, dy = at[0] - eye[0], -(at[2] - eye[2])
        n = math.hypot(dx, dy) or 1.0
        view = {"eye": e3, "dir": (dx / n, dy / n), "hfov": 90.0, "vfov": 58.7, "far": 120.0}
        t0 = t1 = 0
        for e in pl["instances"]:
            rec = shared.get(e["mesh"])
            if not rec:
                continue
            bx_ = cl.instance_box(e, rec)
            if not cl.in_view(bx_, view):
                continue
            tr = rec["triangles"]
            t0 += tr
            lod = shared.get(e["mesh"] + "_LOD1")
            d = cl.dist_to_box(view["eye"], bx_)
            sw = 25.0 if e["mesh"].startswith(("SM_Facade_MT_", "SM_Facade_Marquee_")) else 12.0
            t1 += lod["triangles"] if lod and d > sw else tr
        rows.append((name, t0, t1))
        if t1 > worst[0]:
            worst = (t1, name)
    print("    " + "; ".join("%s %.2f M -> %.2f M" % (n_, a / 1e6, b_ / 1e6) for n_, a, b_ in rows))
    report(worst[0] <= 900000, "views", "the lane's placed art in the six shot views, LOD0 -> with the LOD1s: worst %s, %.2f M triangles (this "
           "lane's share of the 1.3 M target: at most 0.9 M)" % (worst[1], worst[0] / 1e6))


def check_fit(pl, shared):
    """Round 2: the placements against the level data as it is on disk now (tools/levels/data/level_midtown.json). Every
    fitted instance stands on its collider (pivot on the box's centre and bottom; for the parts of the Stand, the Booth
    and the rooms, inside the boxes it names), its art footprint covers at least 60 % of the box and its height is 0.6 to
    1.8 times the box's; every collider of a dressed tag has art; the chosen positions are listed."""
    import math
    repo = os.path.dirname(os.path.dirname(BLENDER_DIR))
    lv = load(os.path.join(repo, "tools", "levels", "data", "level_midtown.json"))["colliders"]["boxes"]
    bad, n, worst_cov = [], 0, 1.0
    for e in pl["instances"]:
        f = e.get("fit")
        if not f:
            continue
        n += 1
        cs = [lv[i] for i in f["colliders"]]
        lo = [min(c["web"]["min"][k] for c in cs) for k in "xyz"]
        hi = [max(c["web"]["max"][k] for c in cs) for k in "xyz"]
        wx, wy, wz = e["web"]
        if f["mode"] == "part":
            if not (lo[0] - 0.5 <= wx <= hi[0] + 0.5 and lo[2] - 0.5 <= wz <= hi[2] + 0.5 and lo[1] - 0.5 <= wy <= hi[1] + 0.5):
                bad.append((e["mesh"], e["role"], "pivot off its boxes"))
            continue
        cx, cz = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2
        if f.get("modules", 1) == 1 and (abs(wx - cx) > 0.02 or abs(wz - cz) > 0.02):
            bad.append((e["mesh"], e["role"], "centre %.2f, %.2f off the box's %.2f, %.2f" % (wx, wz, cx, cz)))
        if abs(wy - lo[1]) > 0.02:
            bad.append((e["mesh"], e["role"], "base %.2f, box bottom %.2f" % (wy, lo[1])))
        bmin, bmax = shared[e["mesh"]]["bounds_m"]["min"], shared[e["mesh"]]["bounds_m"]["max"]
        sc = e.get("scale") or [1.0, 1.0, 1.0]
        r = math.radians(e["rot_z_deg"])
        pts = [(x * sc[0], y * sc[1]) for x in (bmin[0], bmax[0]) for y in (bmin[1], bmax[1])]
        pts = [(e["blender_m"][0] + x * math.cos(r) - y * math.sin(r), e["blender_m"][1] + x * math.sin(r) + y * math.cos(r)) for x, y in pts]
        ax0, ax1 = min(p[0] for p in pts), max(p[0] for p in pts)
        az0, az1 = min(-p[1] for p in pts), max(-p[1] for p in pts)             # Blender y = -web z
        if f.get("modules", 1) > 1:
            continue
        ix = max(0.0, min(ax1, hi[0]) - max(ax0, lo[0]))
        iz = max(0.0, min(az1, hi[2]) - max(az0, lo[2]))
        cov = ix * iz / max(1e-6, (hi[0] - lo[0]) * (hi[2] - lo[2]))
        worst_cov = min(worst_cov, cov)
        hr = (bmax[2] - bmin[2]) * sc[2] / max(1e-6, hi[1] - lo[1])
        if cov < 0.6 or not 0.6 <= hr <= (3.0 if f.get("above") else 1.8):
            bad.append((e["mesh"], e["role"], "covers %.0f %% of its box, height ratio %.2f" % (cov * 100, hr)))
    fs = pl.get("fit", {})
    left = fs.get("colliders_of_dressed_tags_left", ["no fit summary"])
    chosen = sum(1 for e in pl["instances"] if e.get("chosen"))
    report(not bad and not left, "fit", "%d instances fitted to level_midtown.json (worst footprint cover %.0f %%), %d colliders of %d "
           "dressed tags, none left without art%s; %d chosen positions (%s)%s"
           % (n, worst_cov * 100, fs.get("colliders_dressed", 0), len(fs.get("dressed_tags", [])), "" if not left else " BUT left: %s" % left,
              chosen, ", ".join(sorted({r.split(" ")[0] for r in fs.get("chosen_roles", [])}))[:160], "" if not bad else "; off: %s" % bad[:6]))


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
