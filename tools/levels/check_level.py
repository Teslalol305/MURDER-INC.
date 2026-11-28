#!/usr/bin/env python3
"""Checks a new level file before any engine or art work (MAPS.md lane D acceptance; chinatown.md 17 checks 2 to 7
and 13; midtown.md 19 Loads, Reach, ReelRooms, Edges, Budgets; the guidance in any reel order).

    python3 tools/levels/check_level.py --level chinatown|midtown|all [--file PATH] [--quick]

Writes tools/levels/reports/check_<id>.json (the numbers, the guide paths the plan picture draws) and prints a
summary. Exit status 1 when any check fails. The nav, reach and fall checks use tools/levels/navgrid.py, a mirror of
FMIBoxWorld's rule (design numbers): the engine's Levels.<Id>.Nav / .Reach / .Edges tests stay the authority.
"""

import argparse
import itertools
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import navgrid  # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "names"))
import check_names  # noqa: E402  (tools/names: the approved and retired names, names.json)

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(HERE, "data")
REPORTS = os.path.join(HERE, "reports")

EXPECT = {
    "chinatown": {"objectives": 3, "ground": 38, "air": 0, "explosives": 18, "titleKeys": 14, "colliderCap": 800,
                  "reels": ["reel4", "reel5", "reel6"]},
    "midtown": {"objectives": 3, "ground": 30, "air": 0, "explosives": 17, "titleKeys": 14, "colliderCap": 820,
                "reels": ["reel7", "reel8", "reel9"]},
}
CJK = re.compile("[⺀-⿿　-〿぀-ヿ㄀-ㇿ㈀-鿿가-힯豈-﫿︰-﹏＀-￯]")
# Names the designs already rejected as real (chinatown.md 13.3) and real marks the art bible forbids; a hit is a failure.
REAL_NAMES = ["PEARL RIVER", "KOWLOON", "GOLDEN PHOENIX", "TKTS", "I ♥ NY", "I LOVE NY", "MTA", "NYPD", "COCA", "PEPSI",
              "SAMSUNG", "PANASONIC", "TOSHIBA", "SONY", "M&M", "HERSHEY", "DISNEY", "NASDAQ", "REUTERS"]
GOON_RUN = 4.5  # config.json enemies.goon.runSpeed
SAFE_DROP = 13.0 ** 2 / (2 * 21.0)  # 4.024 m: config.json player.fall (damage above a 13 m/s landing, gravity 21)
JUMP_APEX = 1.0                     # a jump lifts the feet 1.0 m, and MIPlayerRules takes the peak fall speed: a drop jumped is 1.0 m longer


class Report:
    def __init__(self, lid):
        self.lid = lid
        self.checks = []
        self.data = {}

    def add(self, name, ok, detail, warn=False, waivers=None):
        """warn=True only for advisory checks (listed as such in the README). A gate that fails is FAIL unless the level
        records a waiver for it (guide.waivers or checks.waivers: {check, reason, owner}); then WAIVED, with the reason."""
        res = "PASS" if ok else ("WARN" if warn else "FAIL")
        if res == "FAIL" and waivers:
            w = [x for x in waivers if x.get("check") == name]
            if w:
                res = "WAIVED"
                detail = {"detail": detail, "waiver": w[0]}
        self.checks.append({"check": name, "result": res, "detail": detail})

    @property
    def failed(self):
        return [c for c in self.checks if c["result"] == "FAIL"]


def W(p):
    return (p["x"], p["y"], p["z"])


def boxes_of(doc):
    out = []
    for b in doc["colliders"]["boxes"]:
        out.append({"tag": b["tag"], "flags": b["flags"], "min": W(b["web"]["min"]), "max": W(b["web"]["max"]),
                    "owner": b["owner"], "index": b["index"]})
    return out


# ---------------------------------------------------------------------------------------------------------- schema
def check_schema(doc, rep, exp, raw):
    errs = []

    def need(cond, msg):
        if not cond:
            errs.append(msg)

    for k in ("meta", "bounds", "zones", "places", "playerStart", "objectives", "extraction", "enemySpawns", "coverPoints",
              "explosives", "interior", "cinematicPath", "colliders", "nav", "tuning"):
        need(k in doc, "missing section " + k)
    if errs:
        rep.add("schema.sections", False, errs)
        return False
    b = doc["bounds"]["web"]
    need(all(isinstance(b.get(k), (int, float)) for k in ("minX", "maxX", "minZ", "maxZ")), "bounds.web")
    for i, c in enumerate(doc["colliders"]["boxes"]):
        need(c.get("index") == i, "collider index %d" % i)
        for k in ("tag", "surface"):
            need(isinstance(c.get(k), str), "collider %d %s" % (i, k))
        f = c.get("flags", {})
        need(all(isinstance(f.get(k), bool) for k in ("bulletOnly", "playerOnly", "noNav")), "collider %d flags" % i)
        mn, mx = c["web"]["min"], c["web"]["max"]
        need(all(mx[a] > mn[a] for a in "xyz"), "collider %d has min >= max" % i)
        need(c["owner"].get("kind") in ("level", "prop", "explosive", "truck"), "collider %d owner kind" % i)
        ue = c["ue"]["min"]
        need(abs(ue["X"] - mn["x"] * 100) < 0.05 and abs(ue["Y"] - mn["z"] * 100) < 0.05 and abs(ue["Z"] - mn["y"] * 100) < 0.05,
             "collider %d ue mirror" % i)
    for i, p in enumerate(doc["enemySpawns"]["points"]):
        need(p.get("index") == i and p.get("type") in ("ground", "air") and isinstance(p.get("zone"), str) and p["zone"],
             "spawn %d index/type/zone" % i)
        need("pos" in p["web"] and "facing" in p["web"], "spawn %d web.pos/facing" % i)
        if p["type"] == "ground":
            need(p.get("layer") in [ly["id"] for ly in doc["nav"]["layers"]], "spawn %d layer" % i)
    for i, p in enumerate(doc["coverPoints"]["points"]):
        need(p.get("index") == i and p.get("zone") and "pos" in p["web"] and p.get("layer"), "cover %d" % i)
    for i, o in enumerate(doc["objectives"]):
        need(o.get("index") == i and all(isinstance(o.get(k), str) for k in ("id", "code", "label", "zone", "place")), "objective %d" % i)
        need("pos" in o["web"] and isinstance(o["web"].get("rotationY"), (int, float)), "objective %d pos/rotationY" % i)
    x = doc["extraction"]
    need(x.get("zone") and "pos" in x["web"] and isinstance(x["web"].get("radius"), (int, float)), "extraction zone/pos/radius")
    need("pos" in x["truck"]["web"] and isinstance(x["truck"]["web"].get("rotationY"), (int, float)), "extraction.truck pos/rotationY (loader line 128)")
    ps = doc["playerStart"]["web"]
    need("pos" in ps and isinstance(ps.get("yaw"), (int, float)), "playerStart")
    for i, z in enumerate(doc["zones"]):
        need(z.get("id") and z.get("name") and all(k in z["web"] for k in ("minX", "maxX", "minZ", "maxZ")), "zone %d" % i)
    for i, e in enumerate(doc["explosives"]["items"]):
        need(e.get("index") == i and e.get("type") in ("propane", "rack") and "pos" in e["web"] and isinstance(e.get("collider"), int),
             "explosive %d" % i)
    for i, ib in enumerate(doc["interior"]["boxes"]):
        need("min" in ib["web"] and "max" in ib["web"], "interior box %d" % i)
    for i, d in enumerate(doc["interior"]["doorways"]):
        need("outside" in d["web"] and "inside" in d["web"], "doorway %d" % i)
    for i, c in enumerate(doc["cinematicPath"]["points"]):
        need("pos" in c["web"] and "look" in c["web"], "title key %d" % i)
    if "el" in doc:
        need("deck" in doc["el"] and "underside" in doc["el"]["deck"]["web"], "el present without a deck")
    rep.add("schema.loaderSections", not errs, errs[:20] or "every section FMILevelData::Load reads is present with the field "
            "names and types it reads; ue mirrors match web x 100; `el` %s" % ("absent (E2: optional)" if "el" not in doc else "present (fallback deck)"))

    cnt = doc["meta"]["counts"]
    sp = doc["enemySpawns"]["points"]
    got = {"objectives": len(doc["objectives"]), "ground": sum(1 for p in sp if p["type"] == "ground"),
           "air": sum(1 for p in sp if p["type"] == "air"), "explosives": len(doc["explosives"]["items"]),
           "titleKeys": len(doc["cinematicPath"]["points"])}
    bad = {k: (got[k], exp[k]) for k in got if got[k] != exp[k]}
    meta_ok = (cnt["colliders"] == len(doc["colliders"]["boxes"]) and cnt["enemySpawns"]["ground"] == got["ground"]
               and cnt["enemySpawns"]["air"] == got["air"] and cnt["explosives"] == got["explosives"])
    rep.add("schema.counts", not bad and meta_ok, {"got": got, "levelsJsonProvides": {k: exp[k] for k in got}, "mismatch": bad,
                                                   "metaCountsMatch": meta_ok})

    ids = [o["id"] for o in doc["objectives"]]
    rep.add("schema.reelIds", ids == exp["reels"], ids)

    # zones tile the bounds (sampled every 0.5 m)
    holes = 0
    zs = [z["web"] for z in doc["zones"]]
    xs = [b["minX"] + 0.25 + 0.5 * i for i in range(int((b["maxX"] - b["minX"]) / 0.5))]
    zz = [b["minZ"] + 0.25 + 0.5 * j for j in range(int((b["maxZ"] - b["minZ"]) / 0.5))]
    for X in xs:
        for Z in zz:
            if not any(r["minX"] <= X <= r["maxX"] and r["minZ"] <= Z <= r["maxZ"] for r in zs):
                holes += 1
    rep.add("schema.zonesTileBounds", holes == 0, "%d sample points without a zone" % holes)

    # no Chinese (or any CJK) characters anywhere; no rejected real names
    hits = sorted(set(CJK.findall(raw)))
    rep.add("content.englishOnly", not hits, "no CJK characters in the file" if not hits else "CJK characters: " + "".join(hits[:40]))
    texts = " ".join(s.get("text", "") for s in doc.get("signage", {}).get("placements", [])).upper()
    real = [n for n in REAL_NAMES if re.search(r"(?<![A-Z])" + re.escape(n) + r"(?![A-Z])", raw.upper())]
    rep.add("content.noRejectedRealNames", not real, real or "none of the names the designs rejected and no real mark the art "
            "bible forbids appears anywhere in the file")
    check_name_lists(doc, raw, rep)
    return True


def check_name_lists(doc, raw, rep):
    """The approved list (tools/names/names.json, MAPS.md C1): no retired name anywhere in the file (ids built from one
    included), and every sign, screen slide and shop list names an approved name, a generic word, a real place or a story
    mark of this level."""
    data = check_names.load()
    lid = doc["meta"]["level"]["id"] if isinstance(doc["meta"].get("level"), dict) else doc["meta"].get("level")
    hits = []
    for name, toks in check_names.RETIRED_TOKENS.items():
        for t in toks:
            n = len(check_names.token_re(t).findall(raw))
            if n:
                hits.append("%s x%d (retired: %s)" % (t, n, name))
    rep.add("content.noRetiredNames", not hits, hits or "no retired name (%d) appears anywhere in the file" % len(check_names.RETIRED_TOKENS))
    strip = lambda t: re.sub(r"\s*\(.*?\)", "", t).strip().upper()
    allowed = [strip(n["text"]) for n in data["names"] if n["status"] == "approved" and n.get("level") == lid]
    allowed += [strip(g) for g in data["generic"].get(lid, []) if not g.startswith("the ")]
    allowed += [strip(g) for g in data["realPlaces"] + data["storyMarks"]]
    allowed = [a for a in allowed if len(a) >= 2]

    def listed(text):
        t = re.sub(r"\s+", " ", text.replace(" / ", " ").upper()).strip()
        # the text names an allowed name, or is two or more words of one (the half-finished BIG LIGHT neon)
        return not t or any(a in t for a in allowed) or (" " in t and any(t in a for a in allowed))

    bad = []
    for s in doc.get("signage", {}).get("placements", []):
        if s.get("kind") in ("exitbox", "lanterns"):
            continue  # a plain EXIT box; the lantern string carries no words
        for t in [s.get("text") or ""] + list(s.get("slides") or []):
            if not listed(t):
                bad.append((s["id"], t))
    for b in (doc.get("buildings") or {}).get("list", []):
        for raw_part in (b.get("shops") or "").split(";"):
            if raw_part.strip()[:1].islower():
                continue  # prose about the building, not a sign
            part = re.sub(r"^\d+F\s+", "", strip(raw_part))
            if part and not any(w in part.lower() for w in ("storeroom", "backs", "shut")) and not listed(part):
                bad.append((b["id"], part))
    rep.add("content.namesOnApprovedList", not bad, bad[:20] or "every sign face, screen slide and shop list names an approved "
            "name (names.md), a generic word, a real place or a story mark; %d faces" % len(doc.get("signage", {}).get("placements", [])))


# ---------------------------------------------------------------------------------------------------------- colliders
def check_colliders(doc, boxes, rep, exp):
    n = len(boxes)
    rep.add("colliders.count", n <= exp["colliderCap"], "%d colliders (cap %d), all axis-aligned, %d oriented" % (
        n, exp["colliderCap"], len(doc.get("orientedBoxes", {}).get("boxes", []))))
    bad = []
    for i, e in enumerate(doc["explosives"]["items"]):
        c = doc["colliders"]["boxes"][e["collider"]]
        if c["owner"].get("kind") != "explosive" or c["owner"].get("explosive") != i:
            bad.append(i)
        p = W(e["web"]["pos"])
        mn, mx = W(c["web"]["min"]), W(c["web"]["max"])
        if not (mn[0] <= p[0] <= mx[0] and mn[2] <= p[2] <= mx[2] and abs(mn[1] - p[1]) < 0.01):
            bad.append(("pos", i))
    rep.add("colliders.explosiveIndices", not bad, bad or "every explosives.items[i].collider is owner {explosive: i} and sits under the item")
    thin = [b["index"] for b in boxes if not b["flags"]["bulletOnly"] and min(b["max"][k] - b["min"][k] for k in range(3)) < 0.05]
    try:
        akeys = set(json.load(open(os.path.join(ROOT, "unreal", "MurderInc", "Content", "Data", "audio.json")))["surfaces"]) - {"about"}
        used = {b["surface"] for b in doc["colliders"]["boxes"]} | {s["surface"] for s in doc["ground"]["surfaces"]}
        rep.add("colliders.surfacesKnown", used <= akeys, sorted(used - akeys) or "every collider and ground surface is a key of audio.json surfaces (%s)" % ", ".join(sorted(used)))
    except OSError:
        pass
    rep.add("colliders.noThinMovementBoxes", not thin, thin or "no movement-blocking collider thinner than 0.05 m")
    # explosives keep 4 m from reels, the extraction and doorway centres (chinatown.md 9)
    reels = [W(o["web"]["pos"]) for o in doc["objectives"]]
    ex = W(doc["extraction"]["web"]["pos"])
    close = []
    for i, e in enumerate(doc["explosives"]["items"]):
        p = W(e["web"]["pos"])
        for q in reels + [ex]:
            d = math.hypot(p[0] - q[0], p[2] - q[2])
            if d < 4.0 and abs(p[1] - q[1]) < 3:
                close.append((i, round(d, 2)))
    rep.add("explosives.clearOfReelsAndTruck", not close, close or "no explosive within 4 m of a reel case or the extraction zone")
    # ... and 4 m from every doorway centre (interior.doorways: the middle of outside and inside) and Goon door
    # (checks.goonDoors), chinatown.md 9; an exception the design wants is listed in checks.explosiveDoorExceptions
    chk = doc.get("checks") or {}
    doors = [(d.get("name"), ((d["web"]["outside"]["x"] + d["web"]["inside"]["x"]) / 2, (d["web"]["outside"]["y"] + d["web"]["inside"]["y"]) / 2,
                              (d["web"]["outside"]["z"] + d["web"]["inside"]["z"]) / 2)) for d in doc["interior"]["doorways"]]
    lay_y = {ly["id"]: ly["y"] for ly in doc["nav"]["layers"]}
    doors += [(d["what"], (d["x"], lay_y.get(d.get("layer", "street"), 0.0), d["z"])) for d in chk.get("goonDoors", [])]
    exc = {(e["explosive"], e["door"]): e for e in chk.get("explosiveDoorExceptions", [])}
    near, excused = [], []
    for i, e in enumerate(doc["explosives"]["items"]):
        p = W(e["web"]["pos"])
        for name, q in doors:
            d = math.hypot(p[0] - q[0], p[2] - q[2])
            if d < 4.0 and abs(p[1] - q[1]) < 3.0:
                (excused if (i, name) in exc else near).append({"explosive": i, "type": e["type"], "door": name, "m": round(d, 2)})
    rep.add("explosives.clearOfDoorways", not near, near or "no explosive within 4 m of a doorway centre or a Goon door (%d doors)%s" % (
        len(doors), "; design exceptions: %s" % [(x["explosive"], x["door"], x["m"], exc[(x["explosive"], x["door"])]["why"]) for x in excused]
        if excused else ""))


# ---------------------------------------------------------------------------------------------------------- nav and spawns
def build_grids(doc, boxes):
    grids = {}
    for ly in doc["nav"]["layers"]:
        grids[ly["id"]] = navgrid.layer_grid(boxes, ly)
    return grids


def check_spawns(doc, boxes, grids, rep):
    solid = [b for b in boxes if not b["flags"]["bulletOnly"]]
    import numpy as np
    mn_all = np.array([b["min"] for b in boxes])
    mx_all = np.array([b["max"] for b in boxes])
    off, inside, comp_bad = [], [], []
    main = {}
    for ly, g in grids.items():
        pts = [p for p in doc["enemySpawns"]["points"] if p["type"] == "ground" and p["layer"] == ly]
        regs = {}
        for p in pts:
            x, y, z = W(p["web"]["pos"])
            c = g.cell_at(x, z)
            if c is None or g.blocked[c[1], c[0]]:
                off.append((p["index"], p.get("name"), ly))
            else:
                regs.setdefault(int(g.region[c[1], c[0]]), []).append(p["index"])
        if regs:
            main[ly] = max(regs, key=lambda r: len(regs[r]))
            if len(regs) > 1:
                comp_bad.append({ly: {k: v for k, v in regs.items()}})
    for p in doc["enemySpawns"]["points"]:
        if p["type"] != "ground":
            continue
        x, y, z = W(p["web"]["pos"])
        for b in solid:
            (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
            if x0 - 0.3 < x < x1 + 0.3 and z0 - 0.3 < z < z1 + 0.3 and y1 > y + 0.43 and y0 < y + 1.8:
                inside.append((p["index"], p.get("name"), b["index"], b["tag"]))
                break
    rep.add("spawns.groundOnFreeCells", not off, off or "every ground point is on a free cell of its own layer")
    rep.add("spawns.groundOneComponentPerLayer", not comp_bad, comp_bad or "each layer's ground points lie in one connected region")
    rep.add("spawns.groundNotInsideColliders", not inside, inside or "no ground point's capsule (r 0.3, 1.8 m) overlaps a solid above its step")
    # air: the drones are removed (owner, 2026-11-28, config.json flow.drones=false): no level has an air point
    n_air = [p["index"] for p in doc["enemySpawns"]["points"] if p["type"] == "air"]
    rep.add("spawns.noAir", not n_air, n_air or "no air points: the drones (Buzzards) are removed from the game, so the level has none")
    return main


# ---------------------------------------------------------------------------------------------------------- route graph
class Router:
    """Shortest walks over the layers: within a layer, A* on its grid; across layers, the link polylines (both ways) and
    the authored drops (down only). Midtown's guide.graph is this; Canal uses its street layer alone."""

    def __init__(self, doc, grids):
        self.doc = doc
        self.grids = grids
        self.cache = {}
        self.edges = []  # (layerA, (x,z), layerB, (x,z), length, kind, id, bias, polyline)
        g = doc.get("guide") or {}
        graph = g.get("graph")
        if graph:
            for e in graph["edges"]:
                a = graph["nodes"][e["from"]]
                b = graph["nodes"][e["to"]]
                poly = e.get("path") or [a["pos"], b["pos"]]
                L = sum(math.dist(poly[i], poly[i + 1]) for i in range(len(poly) - 1))
                self.edges.append((a["layer"], (a["pos"][0], a["pos"][2]), b["layer"], (b["pos"][0], b["pos"][2]), L, e["kind"],
                                   e.get("link") or e.get("drop") or e.get("id"), e.get("bias", 0.0), poly, e.get("oneWay", False)))

    def cell(self, layer, x, z, snap=2.2):
        g = self.grids[layer]
        c, d = g.nearest_free(x, z, max_r=snap)
        return c

    def seg(self, layer, a, b):
        key = (layer, a, b)
        if key not in self.cache:
            g = self.grids[layer]
            r = g.path(a, b)
            self.cache[key] = r
            self.cache[(layer, b, a)] = (r[0], list(reversed(r[1]))) if r else None
        return self.cache[key]

    def route(self, src, dst, use_bias=True, block=None):
        """src/dst: (layer, x, z). Dijkstra over waypoints {src, dst, every edge end}; returns (length, legs)."""
        import heapq
        nodes = [src, dst]
        for e in self.edges:
            nodes.append((e[0], e[1][0], e[1][1]))
            nodes.append((e[2], e[3][0], e[3][1]))
        nodes = list(dict.fromkeys(nodes))
        cells = {}
        for n in nodes:
            c = self.cell(n[0], n[1], n[2], snap=2.2 if n in (src, dst) else 1.5)
            cells[n] = c
        if cells[src] is None or cells[dst] is None:
            return None
        grids_backup = {}
        if block:
            for layer, r in block:
                g = self.grids[layer]
                grids_backup[layer] = g.blocked.copy()
                i0, j0 = int((r[0] - g.ox) / 0.5), int((r[2] - g.oz) / 0.5)
                i1, j1 = int((r[1] - g.ox) / 0.5), int((r[3] - g.oz) / 0.5)
                g.blocked[max(0, j0):j1 + 1, max(0, i0):i1 + 1] = 1
            self.cache = {}
        try:
            adj = {n: [] for n in nodes}
            by_layer = {}
            for n in nodes:
                if cells[n] is not None:
                    by_layer.setdefault(n[0], []).append(n)
            for layer, ns in by_layer.items():
                for a, b in itertools.combinations(ns, 2):
                    r = self.seg(layer, cells[a], cells[b])
                    if r:
                        adj[a].append((b, r[0], ("walk", layer, r[1])))
                        adj[b].append((a, r[0], ("walk", layer, list(reversed(r[1])))))
            for e in self.edges:
                a = (e[0], e[1][0], e[1][1])
                b = (e[2], e[3][0], e[3][1])
                bias = e[7] if use_bias else 0.0
                adj[a].append((b, e[4] + bias, ("edge", e[5], e[6], e[8], e[4])))
                if not e[9]:
                    adj[b].append((a, e[4] + bias, ("edge", e[5], e[6], list(reversed(e[8])), e[4])))
            dist = {src: 0.0}
            prev = {}
            pq = [(0.0, 0, src)]
            k = 0
            while pq:
                d, _, u = heapq.heappop(pq)
                if u == dst:
                    break
                if d > dist.get(u, 1e18):
                    continue
                for v, w, how in adj[u]:
                    nd = d + w
                    if nd < dist.get(v, 1e18):
                        dist[v] = nd
                        prev[v] = (u, how)
                        k += 1
                        heapq.heappush(pq, (nd, k, v))
            if dst not in dist:
                return None
            legs = []
            v = dst
            while v != src:
                u, how = prev[v]
                legs.append(how)
                v = u
            legs.reverse()
            true_len = 0.0
            pts = []
            steps = []
            for h in legs:
                if h[0] == "walk":
                    g = self.grids[h[1]]
                    y = g.y
                    seg = [(g.centre(i, j)[0], y, g.centre(i, j)[1]) for (i, j) in h[2]]
                    pts.extend(seg)
                    true_len += sum(math.dist(seg[i], seg[i + 1]) for i in range(len(seg) - 1))
                else:
                    pts.extend([tuple(p) for p in h[3]])
                    true_len += h[4]
                    steps.append({"kind": h[1], "id": h[2], "height": round(abs(h[3][0][1] - h[3][-1][1]), 2)})
            return {"length": true_len, "cost": dist[dst], "points": pts, "steps": steps}
        finally:
            for layer, arr in grids_backup.items():
                self.grids[layer].blocked[:] = arr
            if block:
                self.cache = {}


def objective_layer(doc, o):
    return o.get("layer", "street")


def check_guidance(doc, grids, rep, exp):
    router = Router(doc, grids)
    st = doc["playerStart"]
    start = (st.get("layer", "street"), st["web"]["pos"]["x"], st["web"]["pos"]["z"])
    reels = {o["id"]: (objective_layer(doc, o), o["web"]["pos"]["x"], o["web"]["pos"]["z"]) for o in doc["objectives"]}
    x = doc["extraction"]
    exl = (x.get("layer", "street"), x["web"]["pos"]["x"], x["web"]["pos"]["z"])
    # every reel has a free cell within 2.2 m on its layer
    far = []
    for rid, r in reels.items():
        c, d = grids[r[0]].nearest_free(r[1], r[2], max_r=2.2)
        if c is None:
            far.append(rid)
    rep.add("reach.navCellNearEveryReel", not far, far or "each reel has a free nav cell of its layer within 2.2 m")
    orders = {}
    fails = []
    for order in itertools.permutations(exp["reels"]):
        seq = [("start", start)] + [(rid, reels[rid]) for rid in order] + [("extraction", exl)]
        legs = []
        for (na, a), (nb, b) in zip(seq, seq[1:]):
            r = router.route(a, b)
            if r is None:
                fails.append("%s: %s -> %s" % ("-".join(order), na, nb))
                legs.append({"from": na, "to": nb, "length": None})
            else:
                legs.append({"from": na, "to": nb, "length": round(r["length"], 1), "steps": r["steps"],
                             "points": [[round(p[0], 2), round(p[1], 2), round(p[2], 2)] for p in r["points"]]})
        orders["-".join(order)] = legs
    rep.data["guide"] = orders
    rep.add("guide.everyReelOrder", not fails, fails or "a guidance path exists for all 6 reel orders, every leg (start -> 3 reels "
            "-> IPX), over %s" % ("the street layer" if not (doc.get("guide") or {}).get("graph") else "the route graph (layers + links + drops)"))
    # the intended order against the design's legs (+-10 %)
    g = doc.get("guide") or {}
    dl = g.get("designLegs")
    if dl:
        key = "-".join(g["intendedOrder"])
        got = [l["length"] for l in orders[key]]
        rows, ok = [], True
        for d, m in zip(dl, got):
            within = m is not None and abs(m - d["m"]) <= 0.10 * d["m"]
            ok &= within
            rows.append({"leg": "%s -> %s" % (d["from"], d["to"]), "design": d["m"], "data": m, "within10pct": within})
        tot = sum(m for m in got if m)
        # a waiver covers only the legs it names: a leg outside the design's 10 % that no waiver names is a FAIL
        failing = {r["leg"] for r in rows if not r["within10pct"]}
        wv = [w for w in (g.get("waivers") or []) if w.get("check") == "guide.intendedLegsVsDesign" and failing <= set(w.get("legs", []))]
        rep.add("guide.intendedLegsVsDesign", ok, {"legs": rows, "total": round(tot, 1), "designTotal": round(sum(d["m"] for d in dl), 1)},
                waivers=wv)
    # intended legs at least 10 % shorter than the best route avoiding them (chinatown.md 7.2)
    alts = g.get("alternatives") or []
    for alt in alts:
        a = reels.get(alt["from"], start if alt["from"] == "start" else exl)
        b = reels.get(alt["to"], exl if alt["to"] == "extraction" else None)
        r0 = router.route(a, b)
        r1 = router.route(a, b, block=[(alt.get("layer", "street"), alt["block"])])
        if r0 and r1:
            margin = (r1["length"] - r0["length"]) / r1["length"]
            rep.add("guide.routeTie.%s-%s" % (alt["from"], alt["to"]), margin >= 0.10,
                    {"intended": round(r0["length"], 1), "bestAvoiding": round(r1["length"], 1), "margin": round(margin, 3),
                     "avoided": alt["what"]}, waivers=g.get("waivers"))
        else:
            rep.add("guide.routeTie.%s-%s" % (alt["from"], alt["to"]), r0 is not None, {"intended": r0 and round(r0["length"], 1),
                    "bestAvoiding": None, "avoided": alt["what"], "note": "no route avoiding it"})
    # drawn points lie on walking surfaces (link polylines sampled against the colliders)
    return router, orders


def check_links_on_surfaces(doc, boxes, rep):
    g = doc.get("guide") or {}
    graph = g.get("graph")
    links = (doc.get("nav") or {}).get("links", [])
    solid = [b for b in boxes if not b["flags"]["bulletOnly"] and not b["flags"]["playerOnly"]]
    bad = []
    for lk in links:
        poly = lk["path"]
        if not isinstance(poly, list):
            bad.append((lk["id"], "no polyline"))
            continue
        for i in range(len(poly) - 1):
            a, b = poly[i], poly[i + 1]
            n = max(1, int(math.dist(a, b) / 0.25))
            for k in range(n + 1):
                t = k / n
                p = [a[j] + (b[j] - a[j]) * t for j in range(3)]
                best = 0.0 if p[1] < 0.6 else None
                for bx in solid:
                    (x0, y0, z0), (x1, y1, z1) = bx["min"], bx["max"]
                    if x0 - 0.05 <= p[0] <= x1 + 0.05 and z0 - 0.05 <= p[2] <= z1 + 0.05 and y1 <= p[1] + 0.6:
                        if best is None or y1 > best:
                            best = y1
                if best is None or p[1] - best > 0.6:
                    bad.append((lk["id"], [round(v, 2) for v in p], best))
                    break
            else:
                continue
            break
    rep.add("guide.linksOnWalkingSurfaces", not bad, bad or "every link polyline (%d) runs within 0.6 m over a walking surface "
            "(stair treads, landings, decks) at every 0.25 m" % len(links))


# ---------------------------------------------------------------------------------------------------------- player reach and falls
def check_player(doc, boxes, rep, quick=False):
    b = doc["bounds"]["web"]
    fl = navgrid.PlayerFlood(boxes, b)
    st = W(doc["playerStart"]["web"]["pos"])
    seen, falls_walk = fl.flood(st, jump=False)
    heights = fl.reach_heights(seen)

    def reached(p, rad=2.2, dy=2.5):
        for c, hs in heights.items():
            x, z = fl.centre(c)
            if (x - p[0]) ** 2 + (z - p[2]) ** 2 <= rad * rad and any(abs(h - p[1]) <= dy for h in hs):
                return True
        return False

    miss = [o["id"] for o in doc["objectives"] if not reached(W(o["web"]["pos"]))]
    ex = W(doc["extraction"]["web"]["pos"])
    if not reached(ex, rad=doc["extraction"]["web"]["radius"], dy=1.0):
        miss.append("extraction")
    rep.add("reach.player", not miss, miss or "walking only (steps of 0.42 m or less, no jumps) from playerStart the player "
            "reaches every reel (2.2 m, 2.5 m vertical) and the extraction disc; %d standing states" % len(seen))
    rep.data["playerStates"] = len(seen)
    # drops: the walk flood and the jump flood (parapets, cars, counters climbed with a 1.0 m jump)
    falls = list(falls_walk)
    if not quick:
        # every edge he can stand at he can also jump off: the jump flood tests take-off + 1.0 m (the apex) against 4.02
        seen_j, falls_j = fl.flood(st, jump=True, safe_drop=SAFE_DROP, apex=JUMP_APEX)
        falls += falls_j
        rep.data["playerStatesWithJumps"] = len(seen_j)
    clusters = []
    for c, h, nb, f in falls:
        x, z = fl.centre(nb)
        for cl in clusters:
            if math.hypot(cl["x"] - x, cl["z"] - z) < 2.0:
                cl["n"] += 1
                cl["drop"] = max(cl["drop"], round(h - f, 2))
                break
        else:
            clusters.append({"x": round(x, 2), "z": round(z, 2), "fromY": h, "toY": f, "drop": round(h - f, 2), "n": 1})
    rep.data["falls"] = clusters
    rep.add("edges.noDamagingDrop", not clusters, clusters[:12] or "no reachable edge drops more than 4.02 m walking off, or more "
            "than 3.02 m where he can jump off (take-off + the 1.0 m apex against the 13 m/s fall-damage landing)%s" % (
                " (quick: walking only)" if quick else ""))
    drops = (doc.get("drops") or {}).get("items", [])
    over = [(d["id"], d["height"]) for d in drops if d["height"] + JUMP_APEX > SAFE_DROP + 1e-6]
    rep.add("drops.authoredFreeWhenJumped", not over, over or ", ".join("%s %.2f m" % (d["id"], d["height"]) for d in drops) +
            ": every authored drop plus the 1.0 m jump apex stays under 4.02 m, so it is free walked or jumped")
    # each authored drop happens in the flood: a state near `from` at its height and one near `to`
    missing = []
    for d in drops:
        fr, to = d["from"], d["to"]
        if not reached(fr, rad=1.2, dy=0.3) or not reached(to, rad=1.6, dy=0.4):
            missing.append(d["id"])
    rep.add("drops.authoredReachable", not missing, missing or "the top and the landing of every authored drop are reached")
    return fl, seen


# ---------------------------------------------------------------------------------------------------------- reel rooms, doorways, player-only gaps
def check_rooms(doc, grids, rep, router):
    ib = doc["interior"]["boxes"]

    def in_box(p, box, pad=0.0):
        mn, mx = W(box["web"]["min"]), W(box["web"]["max"])
        return mn[0] - pad < p[0] < mx[0] + pad and mn[2] - pad < p[2] < mx[2] + pad

    bad = []
    for d in doc["interior"]["doorways"]:
        n = sum(1 for box in ib if in_box(W(d["web"]["inside"]), box))
        if n != 1:
            bad.append((d.get("name"), n))
    rep.add("interior.doorwaysInsideOneBox", not bad, bad or "%d doorways, each inside point in exactly one interior box; %d boxes" % (
        len(doc["interior"]["doorways"]), len(ib)))
    # reel rooms (check 13 / ReelRooms): a Goon path from >= 2 ground spawns on the reel's layer, one within 30 s
    rows, ok = [], True
    for o in doc["objectives"]:
        p = W(o["web"]["pos"])
        layer = objective_layer(doc, o)
        g = grids[layer]
        tc, _ = g.nearest_free(p[0], p[2], max_r=2.2)
        sp = [s for s in doc["enemySpawns"]["points"] if s["type"] == "ground" and s["layer"] == layer]
        room = [box for box in ib if in_box(p, box) and W(box["web"]["min"])[1] - 0.2 <= p[1] <= W(box["web"]["max"])[1]]
        lens = []
        for s in sp:
            q = W(s["web"]["pos"])
            if room and any(in_box(q, box) for box in room):
                continue  # excludePlayerRoom: not a spawn in the reel's own room
            sc = g.cell_at(q[0], q[2])
            if sc is None or g.blocked[sc[1], sc[0]] or tc is None:
                continue
            r = g.path(sc, tc)
            if r:
                lens.append((round(r[0], 1), s.get("name") or s["index"]))
        lens.sort()
        good = len(lens) >= 2 and lens[0][0] <= GOON_RUN * 30
        ok &= good
        rows.append({"reel": o["id"], "layer": layer, "room": [box.get("name") for box in room], "spawnsWithPath": len(lens),
                     "nearest": lens[:3]})
    rep.add("reelRooms.goonPaths", ok, rows)
    # authored player-only gaps must be closed to Goon nav
    gaps = (doc.get("checks") or {}).get("playerOnlyGaps", [])
    open_gaps = []
    for gp in gaps:
        g = grids[gp.get("layer", "street")]
        if g.free(gp["x"], gp["z"]):
            open_gaps.append(gp)
    if gaps:
        rep.add("doors.playerOnlyGapsClosedToNav", not open_gaps, open_gaps or ", ".join(gp["what"] for gp in gaps))
        wide = [gp["what"] for gp in gaps if gp.get("width", 99) > 1.0 + 1e-6]
        rep.add("doors.playerOnlyGapsAtMost1m", not wide, wide or "every player-only gap is 1.0 m or less, so the 0.5 m cells and "
                "0.5 m inflate close it to Goons at every grid alignment (the 0.64 m capsule still passes)")
    # Goon doors stay open on the nav
    doors = (doc.get("checks") or {}).get("goonDoors", [])
    shut = [d["what"] for d in doors if not grids[d.get("layer", "street")].free(d["x"], d["z"])]
    if doors:
        rep.add("doors.goonDoorsOpenOnNav", not shut, shut or "%d Goon doors (2.0 m or wider) have a free nav cell in the opening" % len(doors))


# ---------------------------------------------------------------------------------------------------------- fallback ring (check 6)
def check_fallback(doc, boxes, grids, rep, quick=False):
    import numpy as np
    rays = navgrid.Rays(boxes)
    reach = doc["nav"].get("spawnReach", {})
    pts = [p for p in doc["enemySpawns"]["points"] if p["type"] == "ground" and p.get("enabled", True)]
    rooms = doc["interior"]["boxes"]
    zones = doc["zones"]

    def zone_of(x, z):
        for zn in zones:
            r = zn["web"]
            if r["minX"] <= x <= r["maxX"] and r["minZ"] <= z <= r["maxZ"]:
                return zn["id"]
        return None

    def room_of(x, y, z):
        for i, box in enumerate(rooms):
            mn, mx = W(box["web"]["min"]), W(box["web"]["max"])
            if mn[0] <= x <= mx[0] and mn[2] <= z <= mx[2] and mn[1] - 0.2 <= y <= mx[1]:
                return i
        return None

    step = 4 if quick else 2
    low = []
    n = 0
    for lid, g in grids.items():
        for j in range(1, g.rows - 1, step * 2):
            for i in range(1, g.cols - 1, step * 2):
                if g.blocked[j, i]:
                    continue
                x, z = g.centre(i, j)
                y = g.y
                eye = (x, y + 1.6, z)
                pz = zone_of(x, z)
                proom = room_of(x, y + 0.5, z)
                allowed = set(reach.get(lid, [lid]))
                cnt = 0
                for p in pts:
                    if p.get("layer") not in allowed:
                        continue
                    if p.get("overlooks") and lid != p["layer"] and pz not in p["overlooks"]:
                        continue
                    q = W(p["web"]["pos"])
                    if math.hypot(q[0] - x, q[2] - z) < 9.0:
                        continue
                    if proom is not None and room_of(q[0], q[1] + 0.5, q[2]) == proom:
                        continue
                    if rays.clear(eye, (q[0], q[1] + 1.6, q[2])):
                        continue
                    cnt += 1
                    if cnt >= 3:
                        break
                n += 1
                if cnt < 3:
                    low.append({"layer": lid, "x": round(x, 1), "z": round(z, 1), "hidden": cnt})
    rep.data["fallbackLow"] = low
    rep.add("spawns.fallbackRingNeverNeeded", not low, {"samples": n, "below3": low[:15], "count": len(low)} if low else
            "%d player positions sampled every %d m on every layer: each has 3 or more ground points 9 m away, hidden from "
            "the eye, outside the player's room, on an allowed layer; disabled points not counted" % (n, step))


# ---------------------------------------------------------------------------------------------------------- disabled points
def check_enabled(doc, rep, release=False):
    off = [p.get("name") or p["index"] for p in doc["enemySpawns"]["points"] if p.get("enabled") is False]
    detail = ("%d points still carry enabled:false (%s): the loader must skip them (MAPS.md E8) and the release turns them on "
              "once nav step A exists" % (len(off), ", ".join(map(str, off)))) if off else "every spawn point is enabled"
    rep.add("spawns.allEnabledForRelease", not off, detail, warn=not release)


# ---------------------------------------------------------------------------------------------------------- sight lines
def check_sightlines(doc, boxes, grids, rep):
    """The designs' sight-line rules (chinatown.md 4.1: the longest open line is the roadway from the start to the truck,
    77 m, and the south sidewalk is the protected lane; midtown.md 10: breakers keep every open ground line in the
    square under 45 m, the Goons' sight range). Eye to eye at 1.6 m over the floor, between free street cells sampled
    in each rule's rectangle, through the box ray cast."""
    rules = ((doc.get("checks") or {}).get("sightlines") or {}).get("rules", [])
    if not rules:
        return
    rays = navgrid.Rays(boxes)
    g = grids["street"]
    sup = [b for b in boxes if not b["flags"]["bulletOnly"] and b["max"][1] <= 0.42]

    def floor(x, z):
        f = 0.0
        for b in sup:
            if b["min"][0] <= x <= b["max"][0] and b["min"][2] <= z <= b["max"][2] and b["max"][1] > f:
                f = b["max"][1]
        return f

    for r in rules:
        x0, x1, z0, z1 = r["rect"]
        st = r.get("step", 2.0)
        pts = []
        x = x0 + st / 2
        while x < x1:
            z = z0 + st / 2
            while z < z1:
                if g.free(x, z):
                    pts.append((x, floor(x, z) + 1.6, z))
                z += st
            x += st
        n, clear = 0, []
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                d = math.hypot(pts[i][0] - pts[j][0], pts[i][2] - pts[j][2])
                if d <= r["max"]:
                    continue
                n += 1
                if rays.clear(pts[i], pts[j]):
                    clear.append((round(d, 1), [round(pts[i][0], 1), round(pts[i][2], 1)], [round(pts[j][0], 1), round(pts[j][2], 1)]))
        clear.sort(reverse=True)
        rep.add("sight.%s" % r["id"], not clear, {"open": len(clear), "of": n, "longest": clear[:6], "rule": r.get("why")} if clear else
                "no open line longer than %.0f m between %d street cells sampled every %.1f m (%d pairs tested): %s" % (
                    r["max"], len(pts), st, n, r.get("why", "")))


# ---------------------------------------------------------------------------------------------------------- the planned clutter
def check_clutter(doc, rep, exp):
    b = doc.get("colliderBudget")
    if not b:
        rep.add("colliders.plannedClutter", False, "no colliderBudget: the clutter groups of the design's collider breakdown are not authored")
        return
    plan, placed = b["clutterPlanned"], b["clutterPlaced"]
    tp, tg = sum(plan.values()), sum(placed.values())
    ok = tg >= 0.75 * tp and len(doc["colliders"]["boxes"]) <= exp["colliderCap"]
    rep.add("colliders.plannedClutter", ok, {"planned": plan, "placed": placed, "clutterPlaced": tg, "clutterPlanned": tp,
                                             "share": round(tg / tp, 2), "colliders": len(doc["colliders"]["boxes"]),
                                             "plannedTotal": b.get("plannedTotal"), "skipped": len(b.get("skipped", [])),
                                             "rule": "the clutter groups at 75 % of the design's breakdown or more, under the cap"})


# ---------------------------------------------------------------------------------------------------------- guidance from every layer
def check_guide_layers(doc, grids, rep, router):
    """From every free cell (every 4 m) of every layer but the street, the guidance finds a way to each reel and to the
    extraction (chinatown.md 7.3: players get lost on the roof; the route graph carries the stair and the drops)."""
    tgt = [(o["id"], (objective_layer(doc, o), o["web"]["pos"]["x"], o["web"]["pos"]["z"])) for o in doc["objectives"]]
    x = doc["extraction"]
    tgt.append(("extraction", (x.get("layer", "street"), x["web"]["pos"]["x"], x["web"]["pos"]["z"])))
    bad, n = [], 0
    for lid, g in grids.items():
        if lid == "street":
            continue
        main = None
        for j in range(2, g.rows - 2, 8):
            for i in range(2, g.cols - 2, 8):
                if g.blocked[j, i]:
                    continue
                cx, cz = g.centre(i, j)
                for name, t in tgt:
                    n += 1
                    if router.route((lid, cx, cz), t) is None:
                        bad.append({"layer": lid, "x": round(cx, 1), "z": round(cz, 1), "to": name})
    if n:
        rep.add("guide.fromEveryLayer", not bad, bad[:10] or "%d routes from cells sampled every 4 m on the upper layers reach every "
                "reel and the extraction over the route graph" % n)


# ---------------------------------------------------------------------------------------------------------- level-specific
def check_specific(doc, boxes, rep):
    sp = (doc.get("checks") or {})
    rays = navgrid.Rays(boxes)
    for s in sp.get("shootThrough", []):
        ok = rays.clear(s["a"], s["b"])
        rep.add("slot.%s.shotPasses" % s["id"], ok, s["what"])
        frame = [b for b in boxes if b.get("index") in s.get("frame", [])]
        okf = bool(frame) and all(b["flags"]["playerOnly"] for b in frame)
        rep.add("slot.%s.playerBlocked" % s["id"], okf, "the slot's frame is playerOnly (movement blocked, shots and sight pass)")


def run(lid, path=None, quick=False, release=False):
    path = path or os.path.join(DATA, "level_%s.json" % lid)
    raw = open(path, encoding="utf-8").read()
    doc = json.loads(raw)
    rep = Report(lid)
    exp = EXPECT[lid]
    if not check_schema(doc, rep, exp, raw):
        return rep, doc
    all_boxes = boxes_of(doc)
    # an extraction truck that arrives after the last reel (Midtown, E10) is out of the box world until then: its
    # colliders block the nav from the start (the bake stamps them, noNav false) but not shots, sight or movement
    late = doc["extraction"].get("arrival") == "afterAll"
    boxes = [b for b in all_boxes if not (late and b["owner"].get("kind") == "truck")]
    check_colliders(doc, all_boxes, rep, exp)
    check_clutter(doc, rep, exp)
    grids = build_grids(doc, all_boxes)
    if late:
        tb = [b for b in all_boxes if b["owner"].get("kind") == "truck"]
        g = grids["street"]
        free = [b["index"] for b in tb if b["flags"]["noNav"] or g.free((b["min"][0] + b["max"][0]) / 2, (b["min"][2] + b["max"][2]) / 2)]
        rep.add("extraction.lateTruckBlocksNav", not free, free or "the arriving truck's footprint is blocked on the street nav from "
                "the start (so pursuers never path into it at the extraction), while its colliders stay out of rays and movement "
                "until it arrives")
    rep.data["navCells"] = {k: {"cols": g.cols, "rows": g.rows, "free": int((g.blocked == 0).sum())} for k, g in grids.items()}
    check_spawns(doc, boxes, grids, rep)
    check_enabled(doc, rep, release)
    router, orders = check_guidance(doc, grids, rep, exp)
    check_guide_layers(doc, grids, rep, router)
    check_links_on_surfaces(doc, boxes, rep)
    check_rooms(doc, grids, rep, router)
    check_player(doc, boxes, rep, quick)
    check_fallback(doc, boxes, grids, rep, quick)
    check_sightlines(doc, boxes, grids, rep)
    check_specific(doc, boxes, rep)
    return rep, doc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--level", default="all", choices=("chinatown", "midtown", "all"))
    ap.add_argument("--file")
    ap.add_argument("--quick", action="store_true", help="skip the jump flood and sample the fallback ring every 4 m")
    ap.add_argument("--release", action="store_true", help="release gate: a spawn point still disabled is a FAIL, not a WARN")
    a = ap.parse_args()
    bad = 0
    os.makedirs(REPORTS, exist_ok=True)
    for lid in (("chinatown", "midtown") if a.level == "all" else (a.level,)):
        rep, doc = run(lid, a.file, a.quick, a.release)
        out = {"level": lid, "file": os.path.relpath(a.file or os.path.join(DATA, "level_%s.json" % lid), ROOT),
               "tool": "tools/levels/check_level.py", "summary": {
                   "pass": sum(1 for c in rep.checks if c["result"] == "PASS"),
                   "warn": sum(1 for c in rep.checks if c["result"] == "WARN"),
                   "waived": sum(1 for c in rep.checks if c["result"] == "WAIVED"),
                   "fail": len(rep.failed)}, "checks": rep.checks, "data": rep.data}
        data = out.pop("data")
        text = json.dumps(out, indent=1)
        with open(os.path.join(REPORTS, "check_%s.json" % lid), "w") as f:
            f.write(text[:-2] + ',\n "data": ' + json.dumps(data, separators=(",", ":")) + "\n}\n")
        print("== %s: %d pass, %d warn, %d waived, %d fail" % (lid, out["summary"]["pass"], out["summary"]["warn"], out["summary"]["waived"],
                                                              out["summary"]["fail"]))
        for c in rep.checks:
            d = c["detail"]
            s = d if isinstance(d, str) else json.dumps(d)[:300]
            print("  %-6s %-40s %s" % (c["result"], c["check"], s))
        bad += len(rep.failed)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
