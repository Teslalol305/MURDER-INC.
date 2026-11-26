#!/usr/bin/env python3
"""The shared layout tool (MAPS.md lane D, item D1): layout table -> level_<id>.json in level.json's schema.

    python3 tools/levels/build_level.py --level chinatown|midtown|all [--out DIR] [--el-fallback]

Writes unreal/MurderInc/Content/Data/levels/level_<id>.json (a folder the game does not read: levels.json is not
touched until the split screens and map travel ship, MAPS.md section 5). Deterministic: the same table gives the same
bytes. Derived values (cover points, spawn facings) use tools/levels/navgrid.py, the checker's mirror of the nav rule;
the nav grids themselves are left to the engine bake.
"""

import argparse
import importlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "layouts"))

import navgrid  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "unreal", "MurderInc", "Content", "Data", "levels")
LEVELS = ("chinatown", "midtown")


def layer_list(L):
    if L.nav and L.nav.get("layers"):
        return L.nav["layers"]
    return [{"id": "street", "y": 0.0, "rect": L.bounds, "floor": "plane"}]


def grids_for(L):
    return {ly["id"]: navgrid.layer_grid(L.boxes, ly) for ly in layer_list(L)}


def spawn_facings(L, grids):
    cx = (L.bounds["minX"] + L.bounds["maxX"]) / 2
    cz = (L.bounds["minZ"] + L.bounds["maxZ"]) / 2
    out = []
    for s in L.spawns:
        x, y, z = s["pos"]
        if s.get("face"):
            fx, fz = s["face"]
        elif s["type"] == "air":
            dx, dz = cx - x, cz - z
            d = math.hypot(dx, dz) or 1.0
            fx, fz = dx / d, dz / d
        else:
            g = grids[s["layer"]]
            best, bl = (0.0, 1.0), -1.0
            for k in range(32):
                a = 2 * math.pi * k / 32
                dx, dz = math.sin(a), math.cos(a)
                run = 0.0
                while run < 6.0:
                    if not g.free(x + dx * (run + 0.25), z + dz * (run + 0.25)):
                        break
                    run += 0.25
                if run > bl + 1e-9:
                    bl, best = run, (dx, dz)
            fx, fz = best
        out.append((fx, fz))
    return out


def gen_covers(L, grids):
    rule = L.extra.pop("_coverRule", {"minHeight": 1.0, "maxSide": 10.0, "out": 0.6, "spacing": 1.2})
    layers = layer_list(L)
    pts = []

    def near(x, z, y):
        return any((p["pos"][0] - x) ** 2 + (p["pos"][2] - z) ** 2 < rule["spacing"] ** 2 and abs(p["pos"][1] - y) < 1.0 for p in pts)

    def floor_at(x, z, base):
        f = 0.0
        for b in L.boxes:
            if b["flags"]["bulletOnly"]:
                continue
            (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
            if x0 <= x <= x1 and z0 <= z <= z1 and y1 <= base + 0.3 and y1 > f:
                f = y1
        return f

    skip_tags = set(rule.get("skipTags", ["explosive"]))
    cover_tags = set(rule.get("tags", []))
    parapet_tags = set(rule.get("parapetTags", []))
    sources = []
    for b in L.boxes:
        f = b["flags"]
        if f["playerOnly"] or f["bulletOnly"] or b["tag"] in skip_tags:
            continue
        is_parapet = b["tag"] in parapet_tags
        if not is_parapet and b["owner"]["kind"] != "prop" and b["tag"] not in cover_tags:
            continue
        (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
        if not is_parapet and max(x1 - x0, z1 - z0) > rule["maxSide"]:
            continue
        lay = None
        for ly in layers:
            if ly["floor"] == "plane":
                if y0 <= 0.3:
                    lay = ly
            elif abs(y0 - ly["y"]) <= 0.3:
                lay = ly
        if lay is None:
            continue
        h = y1 - max(y0, lay["y"] if lay["floor"] != "plane" else 0.0)
        if h < rule["minHeight"] or h > rule.get("maxHeight", 99.0):
            continue
        sources.append((b, lay, is_parapet))
    for b, lay, is_parapet in sources:
        (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
        g = grids[lay["id"]]
        every = rule.get("parapetEvery", 4.0) if is_parapet else rule.get("every", 3.0)
        faces = []
        short_min = rule.get("shortSideMin", 0.0)
        for side in ("n", "s", "e", "w"):
            if side in ("n", "s"):
                length, a0, other = x1 - x0, x0, z1 - z0
            else:
                length, a0, other = z1 - z0, z0, x1 - x0
            if not is_parapet and length < short_min and (length < other or (length == other and side in ("n", "s"))):
                continue
            n = max(1, int(round(length / every)))
            for k in range(n):
                t = a0 + length * (k + 0.5) / n
                faces.append((side, t))
        for side, t in faces:
            for out in (rule["out"], rule["out"] + 0.25, rule["out"] + 0.5):
                if side == "n":
                    x, z = t, z0 - out
                elif side == "s":
                    x, z = t, z1 + out
                elif side == "e":
                    x, z = x1 + out, t
                else:
                    x, z = x0 - out, t
                if not (L.bounds["minX"] < x < L.bounds["maxX"] and L.bounds["minZ"] < z < L.bounds["maxZ"]):
                    break
                if g.free(x, z):
                    y = floor_at(x, z, y0)
                    if lay["floor"] != "plane" and abs(y - lay["y"]) > 0.45:
                        break
                    if not near(x, z, y):
                        pts.append({"pos": (round(x, 2), round(y, 2), round(z, 2)), "layer": lay["id"], "source": b["tag"]})
                    break
    return pts


def build(level_id, out_dir, el_fallback=False):
    mod = importlib.import_module(level_id)
    L = mod.build()
    grids = grids_for(L)
    facings = spawn_facings(L, grids)
    covers = gen_covers(L, grids)
    doc = L.to_json(facings, covers, "tools/levels/build_level.py (layout table tools/levels/layouts/%s.py)" % level_id,
                    el_fallback=el_fallback)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "level_%s.json" % level_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return path, doc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--level", default="all", choices=LEVELS + ("all",))
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--el-fallback", action="store_true", help="write the degenerate deck of MAPS.md E2's fallback")
    a = ap.parse_args()
    for lid in (LEVELS if a.level == "all" else (a.level,)):
        path, doc = build(lid, a.out, a.el_fallback)
        c = doc["meta"]["counts"]
        print("%s: %s colliders, %s ground + %s air spawns, %s cover, %s explosives, %d bytes -> %s" % (
            lid, c["colliders"], c["enemySpawns"]["ground"], c["enemySpawns"]["air"], c["coverPoints"], c["explosives"],
            os.path.getsize(path), os.path.relpath(path, ROOT)))


if __name__ == "__main__":
    main()
