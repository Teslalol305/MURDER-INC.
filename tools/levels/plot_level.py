#!/usr/bin/env python3
"""Top-down plan pictures of a level file (and its check report), for looking at the data against the design.

    python3 tools/levels/plot_level.py --level chinatown|midtown|all [--scale 10]

Writes art/previews/maps/plan_<id>.jpg (north up, x east, 10 m grid). Run check_level.py first: the guide paths, the
falls and the thin fallback-ring spots are read from tools/levels/reports/check_<id>.json.
Drawn: ground and floors; solids filled by height (cut away above 3 m over interiors: roof slabs, ceilings and upper
storeys over walk-in rooms are outlines); roof-layer walkable cells tinted per layer; edge guards (playerOnly) in
magenta; ground spawns (circles; squares for upper layers, hollow when switched off), air spawns (triangles), cover
(dots), explosives (orange), reels (gold, numbered), the extraction ring and truck, the player start (arrow), interior
boxes (dashed), Buzzard doorways (yellow ticks), links (cyan), authored drops (yellow arrows), the guide path of the
intended reel order (green) and of the other five orders (thin olive).
"""

import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import navgrid  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(ROOT, "art", "previews", "maps")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

LAYER_TINT = {"roof": (150, 110, 200), "r1": (90, 150, 210), "r2": (150, 110, 200), "r3": (210, 120, 150)}


def W(p):
    return (p["x"], p["y"], p["z"])


def font(sz, bold=False):
    try:
        return ImageFont.truetype(FONTB if bold else FONT, sz)
    except OSError:
        return ImageFont.load_default()


def height_col(h, kind):
    if kind == "vehicle":
        return (58, 86, 120)
    if kind == "prop":
        t = min(1.0, h / 3.0)
        return (int(70 + 40 * t), int(110 + 30 * t), int(125 + 30 * t))
    t = min(1.0, max(0.0, (h - 1.0) / 22.0))
    return (int(105 + 60 * t), int(95 + 40 * t), int(90 + 30 * t))


def plot(lid, scale):
    doc = json.load(open(os.path.join(DATA, "level_%s.json" % lid), encoding="utf-8"))
    rp = os.path.join(HERE, "reports", "check_%s.json" % lid)
    rep = json.load(open(rp)) if os.path.exists(rp) else {"data": {}, "checks": []}
    b = doc["bounds"]["web"]
    M = 60
    legend_h = 150
    Wd = int((b["maxX"] - b["minX"]) * scale) + 2 * M
    Ht = int((b["maxZ"] - b["minZ"]) * scale) + 2 * M + legend_h
    img = Image.new("RGB", (Wd, Ht), (24, 25, 30))
    d = ImageDraw.Draw(img, "RGBA")

    def P(x, z):
        return (M + (x - b["minX"]) * scale, M + (z - b["minZ"]) * scale)

    def R(x0, z0, x1, z1):
        a, c = P(x0, z0), P(x1, z1)
        return [min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1])]

    # ground: roadway, then floors
    d.rectangle(R(b["minX"], b["minZ"], b["maxX"], b["maxZ"]), fill=(52, 55, 62))
    for f in doc["ground"]["floors"]:
        h = f["height"]["web"]
        r = f["web"]
        if h <= 0.001:
            col = (52, 55, 62)
        elif h < 0.3:
            col = (74, 78, 86)
        elif h < 1.0:
            col = (88, 92, 100)
        else:
            continue
        d.rectangle(R(r["minX"], r["minZ"], r["maxX"], r["maxZ"]), fill=col)

    boxes = doc["colliders"]["boxes"]
    interiors = [(W(ib["web"]["min"]), W(ib["web"]["max"])) for ib in doc["interior"]["boxes"]]

    def over_interior(mn, mx):
        for a, c in interiors:
            if mn[0] < c[0] and mx[0] > a[0] and mn[2] < c[2] and mx[2] > a[2]:
                return True
        return False

    # roof-layer walkable tint (the checker's mirror of the layer rule)
    sel = [{"tag": x["tag"], "flags": x["flags"], "min": W(x["web"]["min"]), "max": W(x["web"]["max"])} for x in boxes]
    layers = [ly for ly in doc["nav"]["layers"] if ly["floor"] != "plane"]

    order = sorted(range(len(boxes)), key=lambda i: boxes[i]["web"]["max"]["y"])
    outlines = []
    for i in order:
        bx = boxes[i]
        mn, mx = W(bx["web"]["min"]), W(bx["web"]["max"])
        f = bx["flags"]
        if bx["tag"] in ("sidewalk", "floor", "square") and mx[1] <= 0.2:
            continue
        rr = R(mn[0], mn[2], mx[0], mx[2])
        if f["playerOnly"]:
            outlines.append(("guard", rr))
            continue
        if f["bulletOnly"]:
            outlines.append(("bullet", rr))
            continue
        if bx["owner"]["kind"] == "explosive":
            continue
        if (mn[1] >= 3.0 and over_interior(mn, mx)) or (mn[1] >= 2.4 and mn[1] > 0.3 and not any(abs(mn[1] - ly["y"]) < 0.35 for ly in layers)):
            outlines.append(("cut", rr))
            continue
        kind = "vehicle" if bx["surface"] in ("car", "glass") and bx["owner"]["kind"] in ("prop", "truck") else (
            "prop" if bx["owner"]["kind"] == "prop" else "level")
        h = mx[1]
        col = height_col(h, kind)
        if bx["owner"]["kind"] == "truck":
            col = (60, 140, 90)
        d.rectangle(rr, fill=col + (255,), outline=(20, 20, 24))
    for ly in layers:
        g = navgrid.layer_grid(sel, ly)
        tint = LAYER_TINT.get(ly["id"], (150, 110, 200))
        for j in range(g.rows):
            for i in range(g.cols):
                if not g.blocked[j, i]:
                    cx, cz = g.centre(i, j)
                    d.rectangle(R(cx - 0.25, cz - 0.25, cx + 0.25, cz + 0.25), fill=tint + (70,))
        # re-draw solids standing on this layer so the roof furniture reads over the tint
        for bx in boxes:
            mn, mx = W(bx["web"]["min"]), W(bx["web"]["max"])
            if abs(mn[1] - ly["y"]) < 0.35 and not bx["flags"]["playerOnly"] and bx["owner"]["kind"] != "explosive":
                d.rectangle(R(mn[0], mn[2], mx[0], mx[2]), fill=height_col(mx[1] - mn[1], "prop") + (255,), outline=(20, 20, 24))
    for kind, rr in outlines:
        if kind == "guard":
            d.rectangle(rr, outline=(235, 70, 200, 255), width=max(1, int(scale / 6)))
        elif kind == "bullet":
            d.rectangle(rr, outline=(170, 170, 170, 160), width=1)
        else:
            d.rectangle(rr, outline=(160, 150, 140, 140), width=1)

    # interiors (dashed) and doorways
    for a, c in interiors:
        x0, z0, x1, z1 = a[0], a[2], c[0], c[2]
        for (p0, p1) in (((x0, z0), (x1, z0)), ((x1, z0), (x1, z1)), ((x1, z1), (x0, z1)), ((x0, z1), (x0, z0))):
            L = math.dist(p0, p1)
            n = max(1, int(L / 1.0))
            for k in range(0, n, 2):
                t0, t1 = k / n, min(1, (k + 1) / n)
                d.line([P(p0[0] + (p1[0] - p0[0]) * t0, p0[1] + (p1[1] - p0[1]) * t0),
                        P(p0[0] + (p1[0] - p0[0]) * t1, p0[1] + (p1[1] - p0[1]) * t1)], fill=(230, 230, 120, 170), width=1)
    for dw in doc["interior"]["doorways"]:
        o, i = W(dw["web"]["outside"]), W(dw["web"]["inside"])
        d.line([P(o[0], o[2]), P(i[0], i[2])], fill=(250, 220, 60, 200), width=2)

    # zone labels
    fz = font(int(scale * 1.25), bold=True)
    for rg in doc["places"]["regions"]:
        r = rg["web"]
        cx, cz = (r["minX"] + r["maxX"]) / 2, (r["minZ"] + r["maxZ"]) / 2
        t = rg["name"]
        tw = d.textlength(t, font=fz)
        x, y = P(cx, cz)
        d.text((x - tw / 2, y - scale * 0.7), t, font=fz, fill=(255, 255, 255, 70))

    # guide paths: the other orders thin, the intended order on top
    gd = rep.get("data", {}).get("guide", {})
    intended = "-".join((doc.get("guide") or {}).get("intendedOrder", []))
    for key, legs in gd.items():
        if key == intended:
            continue
        for leg in legs:
            pts = leg.get("points") or []
            if len(pts) > 1:
                d.line([P(p[0], p[2]) for p in pts], fill=(150, 160, 60, 90), width=1)
    for leg in gd.get(intended, []):
        pts = leg.get("points") or []
        if len(pts) > 1:
            d.line([P(p[0], p[2]) for p in pts], fill=(80, 230, 110, 235), width=max(2, int(scale / 4)))

    # links and drops
    for lk in doc["nav"].get("links", []):
        if isinstance(lk["path"], list):
            d.line([P(p[0], p[2]) for p in lk["path"]], fill=(60, 220, 240, 255), width=max(2, int(scale / 4)))
    for dr in (doc.get("drops") or {}).get("items", []):
        a, c = dr["from"], dr["to"]
        pa, pc = P(a[0], a[2]), P(c[0], c[2])
        d.line([pa, pc], fill=(255, 230, 60, 255), width=2)
        ang = math.atan2(pc[1] - pa[1], pc[0] - pa[0])
        for s in (2.6, -2.6):
            d.line([pc, (pc[0] - 7 * math.cos(ang + s), pc[1] - 7 * math.sin(ang + s))], fill=(255, 230, 60, 255), width=2)
        d.text((pc[0] + 4, pc[1] - 6), dr["id"], font=font(int(scale * 0.95)), fill=(255, 230, 60, 255))

    # cover, spawns, explosives
    for c in doc["coverPoints"]["points"]:
        x, y, z = W(c["web"]["pos"])
        p = P(x, z)
        r = max(1.5, scale * 0.14)
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(90, 220, 230, 200))
    fs = font(max(9, int(scale * 0.85)))
    for s in doc["enemySpawns"]["points"]:
        x, y, z = W(s["web"]["pos"])
        p = P(x, z)
        r = max(3, scale * 0.42)
        if s["type"] == "air":
            d.polygon([(p[0], p[1] - r), (p[0] - r, p[1] + r * 0.8), (p[0] + r, p[1] + r * 0.8)], outline=(140, 200, 255, 255), fill=(140, 200, 255, 70))
            continue
        on = s.get("enabled", True)
        fill = (230, 60, 60, 255) if on else None
        if s.get("layer", "street") != "street":
            d.rectangle([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=fill, outline=(255, 120, 120, 255), width=2)
        else:
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=fill, outline=(255, 120, 120, 255))
        fx, fz2 = s["web"]["facing"]["x"], s["web"]["facing"]["z"]
        d.line([p, (p[0] + fx * r * 2, p[1] + fz2 * r * 2)], fill=(255, 150, 150, 255), width=1)
        if s.get("name"):
            d.text((p[0] + r + 1, p[1] - r - 2), s["name"], font=fs, fill=(255, 170, 170, 230))
    for e in doc["explosives"]["items"]:
        x, y, z = W(e["web"]["pos"])
        p = P(x, z)
        r = max(3, scale * 0.38)
        d.rectangle([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(255, 140, 20, 255), outline=(60, 30, 0))

    # extraction, truck, reels, start
    x = doc["extraction"]
    ex = W(x["web"]["pos"])
    rr = x["web"]["radius"] * scale
    pe = P(ex[0], ex[2])
    d.ellipse([pe[0] - rr, pe[1] - rr, pe[0] + rr, pe[1] + rr], outline=(80, 255, 120, 255), width=3)
    d.text((pe[0] - rr, pe[1] + rr + 2), "IPX", font=font(int(scale * 1.1), True), fill=(80, 255, 120, 255))
    tr = W(x["truck"]["web"]["pos"])
    pt = P(tr[0], tr[2])
    d.text((pt[0] - 8, pt[1] - scale * 2.6), "TRUCK" + (" (rolls in)" if x.get("arrival") else ""), font=font(int(scale * 0.9), True), fill=(80, 255, 120, 255))
    fr = font(int(scale * 1.2), True)
    for o in doc["objectives"]:
        ox, oy, oz = W(o["web"]["pos"])
        p = P(ox, oz)
        r = scale * 1.0
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(250, 200, 40, 255), outline=(60, 40, 0), width=2)
        tw = d.textlength(o["code"], font=fr)
        d.text((p[0] - tw / 2, p[1] - scale * 0.75), o["code"], font=fr, fill=(30, 20, 0))
    st = doc["playerStart"]["web"]
    ps = P(st["pos"]["x"], st["pos"]["z"])
    fx, fz2 = st["facing"]["x"], st["facing"]["z"]
    L = scale * 2.2
    tip = (ps[0] + fx * L, ps[1] + fz2 * L)
    side = (-fz2, fx)
    d.polygon([tip, (ps[0] + side[0] * L * 0.45, ps[1] + side[1] * L * 0.45), (ps[0] - side[0] * L * 0.45, ps[1] - side[1] * L * 0.45)],
              fill=(255, 255, 255, 255), outline=(0, 0, 0))
    d.text((ps[0] - 10, ps[1] + L * 0.6), "START", font=font(int(scale * 0.95), True), fill=(255, 255, 255))

    # checker findings: falls, thin fallback spots
    for fl in rep.get("data", {}).get("falls", []):
        p = P(fl["x"], fl["z"])
        d.line([(p[0] - 6, p[1] - 6), (p[0] + 6, p[1] + 6)], fill=(255, 0, 0), width=3)
        d.line([(p[0] - 6, p[1] + 6), (p[0] + 6, p[1] - 6)], fill=(255, 0, 0), width=3)
    for lw in rep.get("data", {}).get("fallbackLow", []):
        p = P(lw["x"], lw["z"])
        d.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], outline=(255, 150, 0), width=2)

    # grid, frame, title, legend
    fg = font(11)
    x0 = math.ceil(b["minX"] / 10) * 10
    while x0 <= b["maxX"]:
        a, c = P(x0, b["minZ"]), P(x0, b["maxZ"])
        d.line([a, c], fill=(255, 255, 255, 28), width=1)
        d.text((a[0] - 8, M - 18), "%d" % x0, font=fg, fill=(200, 200, 200))
        x0 += 10
    z0 = math.ceil(b["minZ"] / 10) * 10
    while z0 <= b["maxZ"]:
        a, c = P(b["minX"], z0), P(b["maxX"], z0)
        d.line([a, c], fill=(255, 255, 255, 28), width=1)
        d.text((8, a[1] - 7), "z %d" % z0, font=fg, fill=(200, 200, 200))
        z0 += 10
    d.rectangle(R(b["minX"], b["minZ"], b["maxX"], b["maxZ"]), outline=(255, 255, 255, 120), width=1)
    summ = rep.get("summary", {})
    title = "%s  (level_%s.json)   %d colliders   checks: %s pass, %s warn, %s fail" % (
        doc["meta"]["name"].upper(), lid, len(boxes), summ.get("pass", "?"), summ.get("warn", "?"), summ.get("fail", "?"))
    d.text((M, 12), title, font=font(16, True), fill=(255, 255, 255))
    d.text((Wd - M - 70, 14), "N ↑   10 m grid", font=font(12), fill=(220, 220, 220))
    ly0 = Ht - legend_h + 14
    items = [((230, 60, 60), "ground spawn (square: upper layer; hollow: off)"),
             ((140, 200, 255), "air spawn"), ((90, 220, 230), "cover point"), ((255, 140, 20), "explosive"),
             ((250, 200, 40), "reel (code)"), ((80, 255, 120), "extraction (IPX)"), ((80, 230, 110), "guide path, intended order"),
             ((150, 160, 60), "guide paths, the 5 other orders"), ((60, 220, 240), "nav link (stair)"), ((255, 230, 60), "authored drop / doorway"),
             ((235, 70, 200), "edge guard (playerOnly)"), ((230, 230, 120), "interior box (dashed)")]
    for ly in layers:
        items.append((LAYER_TINT.get(ly["id"], (150, 110, 200)), "walkable on layer %s (y %.1f)" % (ly["id"], ly["y"])))
    fl_ = font(12)
    colw = (Wd - 2 * M) // 3
    for k, (col, t) in enumerate(items):
        cx = M + (k % 3) * colw
        cy = ly0 + (k // 3) * 22
        d.rectangle([cx, cy + 2, cx + 14, cy + 14], fill=col)
        d.text((cx + 20, cy), t, font=fl_, fill=(225, 225, 225))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "plan_%s.jpg" % lid)
    img.save(path, "JPEG", quality=82, optimize=True, progressive=True)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--level", default="all", choices=("chinatown", "midtown", "all"))
    ap.add_argument("--scale", type=float, default=11.0)
    a = ap.parse_args()
    for lid in (("chinatown", "midtown") if a.level == "all" else (a.level,)):
        p = plot(lid, a.scale)
        print("%s -> %s (%d KB)" % (lid, os.path.relpath(p, ROOT), os.path.getsize(p) // 1024))


if __name__ == "__main__":
    main()
