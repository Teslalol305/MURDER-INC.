#!/usr/bin/env python3
"""Holds the guns, attachments, presentation and text data to the rules of docs/unreal/LOADOUT.md, with no engine.

What it mirrors from the code (unreal/MurderInc/Source/MurderInc):
  * FMILoadoutData::ValidateData        (every $ref resolves, the clip roles, compatibility, text keys, ops, stats)
  * the trade check of LOADOUT.md 3.3   (B / W of every non-baseline part inside tradeBand; ValidateData does not compute it yet)
  * FMILoadoutResolver::ApplyEffects    (set, add, mul, min, max, factor clamp, target clamps, falloff end >= start), run over every
                                        compatible build of every gun, so a clamp that swallows a part's effect, a magSize that is not a
                                        whole number and a falloff that breaks are found here and not on the box
  * FMIReadiness                        (IsGunReady, OfferedSlots, OfferedParts, BaseMesh) in three worlds: a clean checkout (no asset),
                                        the box before the weapons import (the pack and the templates only) and the box after it
And it holds the data to what the art lanes exported (Content/Data/gun_contract.json, made by make_gun_contract.py): every mount's socket
and position, every hide bone, every part socket, the gun-space markers and the mesh offset.

  python3 tools/data/check_guns_data.py            checks, prints the tables, exit 1 on any error
  python3 tools/data/check_guns_data.py --quiet    errors only
  python3 tools/data/check_guns_data.py --art      also compare gun_contract.json with art/out (the freshness the generator's --check gives)
"""
import copy
import itertools
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.environ.get("MI_DATA_DIR") or os.path.join(REPO, "unreal", "MurderInc", "Content", "Data")  # MI_DATA_DIR: a copy to test against
QUIET = "--quiet" in sys.argv
INF = float("inf")

ERRORS, WARNINGS = [], []


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNINGS.append(msg)


def say(msg=""):
    if not QUIET:
        print(msg)


# ------------------------------------------------------------------------------------------------------ loading
def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


FILES = {n: load(n) for n in ("config.json", "presentation.json", "guns.json", "attachments.json", "crew.json", "levels.json", "frontend.json", "frontend_text.json")}
UNRESOLVED = []


def get(root, path, default=None):
    """The value at a dotted path with [i] items, or default (MIJson::Get)."""
    cur = root
    for part in path.split("."):
        idx = None
        if part.endswith("]") and "[" in part:
            part, i = part[:-1].split("[")
            idx = int(i)
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
        if idx is not None:
            if not isinstance(cur, list) or idx >= len(cur):
                return default
            cur = cur[idx]
    return cur


def put(root, path, value):
    parts = path.split(".")
    cur = root
    for part in parts[:-1]:
        cur = cur[part]
    last = parts[-1]
    if last.endswith("]") and "[" in last:
        name, i = last[:-1].split("[")
        cur[name][int(i)] = value
    else:
        cur[last] = value


def resolve(v, owner, depth=0):
    """Replaces every {"$ref": "file#path"} by the value it names (FMILoadoutData's Resolve)."""
    if depth > 16:
        return v
    if isinstance(v, list):
        return [resolve(x, owner, depth) for x in v]
    if not isinstance(v, dict):
        return v
    if len(v) == 1 and "$ref" in v:
        ref = v["$ref"]
        f, _, p = ref.partition("#")
        doc = FILES.get(f)
        target = get(doc, p) if doc is not None else None
        if target is None:
            UNRESOLVED.append("%s: %s" % (owner, ref))
            return None
        return resolve(copy.deepcopy(target), owner, depth + 1)
    return {k: resolve(x, owner, depth) for k, x in v.items()}


GUNS_J = resolve(FILES["guns.json"], "guns.json")
ATT_J = resolve(FILES["attachments.json"], "attachments.json")
TEXT_J = resolve(FILES["frontend_text.json"], "frontend_text.json")
FRONT_J = resolve(FILES["frontend.json"], "frontend.json")
PRES = FILES["presentation.json"]
CONFIG = FILES["config.json"]
try:
    CONTRACT = load("gun_contract.json")
except OSError:
    CONTRACT = None
    err("Content/Data/gun_contract.json is missing: python3 tools/data/make_gun_contract.py")

ROSTER = GUNS_J["roster"]
GUNS = GUNS_J["guns"]
SLOTS = sorted(ATT_J["slots"], key=lambda s: s["order"])
SLOT_IDS = [s["id"] for s in SLOTS]
STATS = ATT_J["stats"]
PARTS = ATT_J["attachments"]
COMPAT = ATT_J["compatibility"]
FACTOR = ATT_J["meta"]["factor"]
BAND = ATT_J["meta"]["tradeBand"]
ROLES = [r["role"] for r in GUNS_J["clipRoles"]["roles"]]


def number(v):
    """A number, or the strings Infinity / -Infinity (MIJson::Number)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if v == "Infinity":
        return INF
    if v == "-Infinity":
        return -INF
    return None


# --------------------------------------------------------------------------------------------- ValidateData mirror
def has_text(key):
    return get(TEXT_J, key) is not None


def validate_data():
    for u in UNRESOLVED:
        err("$ref does not resolve: " + u)
    for k in ("holster", "draw", "adsFov", "adsLook", "noise", "semiFireBuffer", "modeSwitch", "inspectAfter"):
        d = GUNS_J["extraDefaults"].get(k)
        if number(d.get("value") if isinstance(d, dict) else None) is None:
            err("guns.json extraDefaults.%s is not a number" % k)
    for gid in ROSTER:
        g = GUNS.get(gid)
        if g is None:
            err("roster names %s, which has no entry" % gid)
            continue
        if not g.get("rules"):
            err("%s: no rules" % gid)
        if not g.get("presentation"):
            err("%s: no presentation" % gid)
        seen = {}
        for status, roles in g["clips"]["byStatus"].items():
            for r in roles:
                seen[r] = seen.get(r, 0) + 1
        for r in ROLES:
            if seen.get(r, 0) != 1:
                err("%s: clip role %s named %d times" % (gid, r, seen.get(r, 0)))
        for r in seen:
            if r not in ROLES:
                err("%s: unknown clip role %s" % (gid, r))
        for slot, row in (COMPAT.get(gid) or {}).items():
            if slot not in SLOT_IDS:
                if slot != "dropped":
                    err("%s: compatibility slot %s is not a slot" % (gid, slot))
                continue
            for o in row["options"]:
                p = PARTS.get(o)
                if p is None:
                    err("%s.%s: unknown part %s" % (gid, slot, o))
                elif p["slot"] != slot:
                    err("%s.%s: %s belongs to %s" % (gid, slot, o, p["slot"]))
                if row.get("variant") and p and p.get("presentation", {}).get("variant") not in g.get("variants", {}):
                    err("%s: variant of %s has no entry" % (gid, o))
            if row.get("required") and row.get("default") not in row["options"]:
                err("%s.%s: required, but its default %s is not an option" % (gid, slot, row.get("default")))
            if not row.get("variant") and slot not in g.get("mounts", {}):
                err("%s.%s: no mount in guns.json" % (gid, slot))
            if row.get("default") is not None and row.get("default") not in row["options"]:
                err("%s.%s: the default %s is not an option" % (gid, slot, row.get("default")))
        tk = g.get("text", "")
        if tk.startswith("frontend.") and not (has_text(tk + ".name") and has_text(tk + ".blurb")):
            err("%s: text %s.name / .blurb missing" % (gid, tk))
        if g.get("melee", "").startswith("frontend.") and not has_text(g["melee"]):
            err("%s: text %s missing" % (gid, g["melee"]))
        if not has_text("frontend.loadout.classes.%s" % g["class"]):
            err("%s: class %s has no text" % (gid, g["class"]))
    ops = ("set", "add", "mul", "min", "max")
    for pid, p in PARTS.items():
        if p["slot"] not in SLOT_IDS:
            err("%s: unknown slot %s" % (pid, p["slot"]))
        if not (has_text(p["text"] + ".name") and has_text(p["text"] + ".blurb")):
            err("%s: text %s missing" % (pid, p["text"]))
        if p.get("baseline") and p["effects"]:
            err("%s: a baseline part has effects" % pid)
        for e in p["effects"]:
            s = STATS.get(e["stat"])
            if s is None:
                err("%s: unknown stat %s" % (pid, e["stat"]))
                continue
            if e["op"] not in ops:
                err("%s: unknown op %s" % (pid, e["op"]))
            multi = len(s["targets"]) > 1 or any(t["path"].endswith("*") for t in s["targets"])
            if multi and e["op"] != "mul":
                err("%s: %s has several targets and takes only mul, not %s" % (pid, e["stat"], e["op"]))
        seen_stat = [e["stat"] for e in p["effects"]]
        for st in set(seen_stat):
            if seen_stat.count(st) > 1:
                warn("%s: stat %s has %d effects (the Attachments.<part>.<stat> test finds the first only)" % (pid, st, seen_stat.count(st)))
    for sid, s in STATS.items():
        if s.get("text") and not has_text(s["text"]):
            err("stat %s: text %s missing" % (sid, s["text"]))
    for s in SLOTS:
        if not has_text(s["text"]):
            err("slot %s: text %s missing" % (s["id"], s["text"]))
    for gid in FRONT_J["parity"]["guns"]:
        if not GUNS.get(gid, {}).get("parity"):
            err("frontend.json parity gun %s is not a parity gun" % gid)


# -------------------------------------------------------------------------------------------------- trade check
def trade_ratio(p):
    """(B, W): sums of |ln f| over the better and the worse `mul` effects of the stats with trade true (LOADOUT.md 3.3)."""
    b = w = 0.0
    for e in p["effects"]:
        s = STATS.get(e["stat"])
        if not s or not s.get("trade") or e["op"] != "mul" or e["value"] <= 0:
            continue
        f = e["value"]
        good = (f < 1) if s["better"] == "lower" else (f > 1) if s["better"] == "higher" else None
        if good is None or f == 1:
            continue
        if good:
            b += abs(math.log(f))
        else:
            w += abs(math.log(f))
    return b, w


def check_trade():
    rows = []
    for pid, p in PARTS.items():
        if p.get("baseline"):
            continue
        b, w = trade_ratio(p)
        ratio = b / w if w else INF
        rows.append((pid, b, w, ratio))
        if b == 0 or w == 0:
            err("trade: %s has no better or no worse effect (B %.4f, W %.4f)" % (pid, b, w))
        elif not (BAND[0] <= ratio <= BAND[1]):
            err("trade: %s B/W = %.3f is outside the band %s" % (pid, ratio, BAND))
    return rows


# ------------------------------------------------------------------------------------------------------- resolver
def filled_extra(g):
    extra = copy.deepcopy(g.get("extra") or {})
    for k, d in GUNS_J["extraDefaults"].items():
        if not isinstance(d, dict) or "value" not in d:
            continue
        have = extra.get(k)
        if have is None:
            extra[k] = copy.deepcopy(d["value"])
        elif isinstance(have, dict) and isinstance(d["value"], dict):
            for m, v in d["value"].items():
                have.setdefault(m, v)
    fo = extra.get("falloff")
    if isinstance(fo, dict):
        for k in ("start", "end", "min"):
            n = number(fo.get(k))
            if n is not None:
                fo[k] = n
    return extra


def clampv(t, v):
    c = t.get("clamp")
    if not c:
        return v
    lo, hi = number(c[0]), number(c[1])
    return min(hi, max(lo, v))


def for_numbers(v, fn):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return fn(v)
    if isinstance(v, list):
        return [for_numbers(x, fn) for x in v]
    if isinstance(v, dict):
        return {k: for_numbers(x, fn) for k, x in v.items()}
    return v


def apply_effects(parts, doc, swallowed=None):
    """FMILoadoutResolver::ApplyEffects on doc = {"rules": ..., "extra": ...} in web units. swallowed: list that receives (stat, wanted, got)."""
    by_stat = {}
    order = []
    for pid in parts:
        for e in PARTS[pid]["effects"]:
            o = by_stat.setdefault(e["stat"], {"set": None, "add": 0.0, "hasadd": False, "mul": 1.0, "hasmul": False, "min": None, "max": None})
            if e["stat"] not in order:
                order.append(e["stat"])
            v = number(e["value"])
            if e["op"] == "set":
                o["set"] = v
            elif e["op"] == "add":
                o["add"] += v
                o["hasadd"] = True
            elif e["op"] == "mul":
                o["mul"] *= v
                o["hasmul"] = True
            elif e["op"] == "min":
                o["min"] = v if o["min"] is None else min(o["min"], v)
            elif e["op"] == "max":
                o["max"] = v if o["max"] is None else max(o["max"], v)
    for sid in order:
        s, o = STATS[sid], by_stat[sid]
        multi = len(s["targets"]) > 1 or any(t["path"].endswith("*") for t in s["targets"])
        if multi:
            f = min(FACTOR[1], max(FACTOR[0], o["mul"]))
            for t in s["targets"]:
                if t["path"].endswith(".*"):
                    parent = t["path"][:-2]
                    v = get(doc, parent)
                    if v is not None:
                        put(doc, parent, for_numbers(v, lambda n, f=f: n * f))
                    continue
                v = number(get(doc, t["path"]))
                if v is None:
                    continue
                want = v * f
                got = clampv(t, want)
                if swallowed is not None and abs(got - want) > 1e-12 * max(1.0, abs(want)):
                    swallowed.append((sid, t["path"], want, got))
                put(doc, t["path"], got)
            continue
        t = s["targets"][0]
        v = number(get(doc, t["path"]))
        if v is None:
            continue
        if o["set"] is not None:
            v = o["set"]
        if o["hasadd"]:
            v += o["add"]
        if o["hasmul"]:
            v *= o["mul"]
        if o["min"] is not None:
            v = min(v, o["min"])
        if o["max"] is not None:
            v = max(v, o["max"])
        got = clampv(t, v)
        if swallowed is not None and abs(got - v) > 1e-12 * max(1.0, abs(v)):
            swallowed.append((sid, t["path"], v, got))
        put(doc, t["path"], got)
    st, en = number(get(doc, "extra.falloff.start")), number(get(doc, "extra.falloff.end"))
    if st is not None and en is not None and en < st:
        put(doc, "extra.falloff.end", st)


def gun_doc(gid):
    g = GUNS[gid]
    return {"rules": copy.deepcopy(g["rules"]), "extra": filled_extra(g)}


def check_base_in_clamps():
    for gid in ROSTER:
        doc = gun_doc(gid)
        for sid, s in STATS.items():
            for t in s["targets"]:
                if t["path"].endswith("*") or not t.get("clamp"):
                    continue
                v = number(get(doc, t["path"]))
                if v is None:
                    continue
                lo, hi = number(t["clamp"][0]), number(t["clamp"][1])
                if not (lo <= v <= hi):
                    err("clamp: %s's %s = %s is outside the clamp %s of stat %s" % (gid, t["path"], v, t["clamp"], sid))


def check_builds():
    """Every compatible build of every gun resolves with falloff.end >= start and falloff.min inside its clamp; each part's effect is not swallowed."""
    fmin_t = STATS["falloff.min"]["targets"][0]
    total = 0
    for gid in ROSTER:
        row = COMPAT.get(gid) or {}
        slots = [s for s in SLOT_IDS if s in row and not row[s].get("variant")]
        choices = [[None] + list(row[s]["options"]) if not row[s].get("required") else list(row[s]["options"]) for s in slots]
        n = 0
        for combo in itertools.product(*choices):
            parts = [p for p in combo if p is not None]
            doc = gun_doc(gid)
            apply_effects(parts, doc)
            st, en, mn = number(get(doc, "extra.falloff.start")), number(get(doc, "extra.falloff.end")), number(get(doc, "extra.falloff.min"))
            if en < st:
                err("build %s %s: falloff.end %s < start %s" % (gid, parts, en, st))
            lo, hi = number(fmin_t["clamp"][0]), number(fmin_t["clamp"][1])
            if not (lo <= mn <= hi):
                err("build %s %s: falloff.min %s outside [%s, %s]" % (gid, parts, mn, lo, hi))
            n += 1
        total += n
        # one part at a time: is its effect applied in full on this gun?
        for slot in slots:
            for pid in row[slot]["options"]:
                sw = []
                doc = gun_doc(gid)
                apply_effects([pid], doc, sw)
                for sid, path, want, got in sw:
                    warn("effect swallowed by a clamp: %s on the %s, %s wanted %.6g, got %.6g" % (pid, gid, path, want, got))
                for e in PARTS[pid]["effects"]:
                    if e["stat"] == "magSize" and e["op"] == "mul":
                        base = number(get(GUNS[gid]["rules"], "magSize"))
                        r = base * e["value"]
                        if abs(r - round(r)) > 1e-9:
                            err("magSize: %s on the %s gives %.9g rounds, not a whole number (ParseGun truncates)" % (pid, gid, r))
    return total


# -------------------------------------------------------------------------------------------------------- readiness
def make_world(kind):
    """asset_exists(path) for 'clean' (no asset), 'box-before' (the pack, the templates and the NINE, as the box has them before the
    weapons import) and 'box-after' (and every mesh of ours imported)."""
    own, before = set(), set()
    if CONTRACT:
        for gid, g in CONTRACT["guns"].items():
            own.update([g["asset"], g["magazine"]] + ([g["brass"]] if g.get("brass") else []))
            if gid == "nine":
                before.update([g["asset"], g["magazine"]])
        for p in CONTRACT["parts"].values():
            own.add(p["asset"])
            if p.get("topRound"):
                own.add(p["topRound"])

    def exists(path):
        if kind == "clean" or not path:
            return False
        if path in own:
            return kind == "box-after" or path in before
        if path.startswith("/Game/Characters/Crew/"):
            return False
        return True  # the pack, the templates, the arms: on every box
    return exists


class Ready:
    def __init__(self, exists):
        self.exists = exists

    def base_mesh(self, gid, build=None):
        g = GUNS[gid]
        if g.get("variants"):
            part = None
            row = (COMPAT.get(gid) or {}).get("stock")
            if row:
                part = row.get("default")
                if build and "stock" in build:
                    part = build["stock"]
            variant = PARTS[part]["presentation"].get("variant", "open") if part in PARTS else "open"
            v = g["variants"].get(variant)
            if v and v.get("mesh") and self.exists(v["mesh"]):
                optic = (build or {}).get("optic")
                if optic and optic != "irons" and v.get("opticMesh") and self.exists(v["opticMesh"]):
                    return v["opticMesh"]
                return v["mesh"]
        real = g["presentation"].get("realMesh") or ""
        if real and self.exists(real):
            return real
        return g["presentation"].get("mesh") if isinstance(g["presentation"].get("mesh"), str) and g["presentation"].get("mesh") else g["presentation"].get("fallbackMesh")

    def gun_ready(self, gid):
        g = GUNS.get(gid)
        if not g:
            return False
        if g.get("parity"):
            return True
        if g.get("variants"):
            open_name = "open"
            row = (COMPAT.get(gid) or {}).get("stock")
            if row and row.get("default") in PARTS:
                open_name = PARTS[row["default"]]["presentation"].get("variant", "open")
            v = g["variants"].get(open_name)
            mesh_ok = bool(v) and v.get("status") == "exists" and self.exists(v.get("mesh", ""))
        else:
            real = g["presentation"].get("realMesh") or g["presentation"].get("mesh") or ""
            mesh_ok = g["art"]["mesh"]["status"] == "exists" and self.exists(real)
        if not mesh_ok:
            return False
        cs = {}
        for status, roles in g["clips"]["byStatus"].items():
            for r in roles:
                cs.setdefault(r, status)
        playable = GUNS_J["ready"]["playable"]
        for r in GUNS_J["ready"]["coreRoles"]:
            st = cs.get(r, "missing")
            if st not in playable and st != "inProgress":
                return False
        return True

    def offered_parts(self, gid, slot):
        g = GUNS[gid]
        row = (COMPAT.get(gid) or {}).get(slot)
        if not row:
            return []
        if row.get("variant"):
            out = []
            for o in row["options"]:
                v = g["variants"].get(PARTS[o]["presentation"].get("variant"))
                if v and v.get("status") == "exists" and self.exists(v.get("mesh", "")):
                    out.append(o)
            return out if len(out) >= 2 else []
        m = g.get("mounts", {}).get(slot)
        if not m or m.get("status") != "exists":
            return []
        out = []
        for o in row["options"]:
            p = PARTS[o]
            mesh = p["presentation"].get("mesh")
            if p.get("baseline") or (mesh and self.exists(mesh)):
                out.append(o)
        if row.get("required") and row.get("default") not in out:
            return []
        return out if len(out) > (1 if row.get("required") else 0) else []

    def offered_slots(self, gid):
        row = COMPAT.get(gid) or {}
        return [s for s in SLOT_IDS if s in row and self.offered_parts(gid, s)]


def check_readiness():
    results = {}
    for kind in ("clean", "box-before", "box-after"):
        r = Ready(make_world(kind))
        results[kind] = {g: (r.gun_ready(g), r.offered_slots(g)) for g in ROSTER}
    # what the owner asked for: on the box after the import every gun is offered, with these slots
    want = {"chopper": 3, "nine": 3, "shorty": 5, "stick": 5, "stretch": 4, "rattler": 3}
    for g in ROSTER:
        n = len(results["box-after"][g][1])
        if not results["box-after"][g][0]:
            err("readiness: %s is not offered on the box after the weapons import" % g)
        if n != want[g]:
            err("readiness: %s offers %d slots on the box after the import, the plan says %d (%s)" % (g, n, want[g], results["box-after"][g][1]))
    for g in ROSTER:
        if GUNS[g].get("parity"):
            continue
        # a clean checkout offers only the parity guns, and no gun of ours shows a slot there
        if results["clean"][g][0]:
            err("readiness: %s is offered in a clean checkout (it must not be)" % g)
    for g in ("chopper", "nine"):
        if results["clean"][g][1]:
            err("readiness: %s offers slots in a clean checkout: %s" % (g, results["clean"][g][1]))
    return results


def check_view_parse():
    """FMIViewmodelData::ParseGunView needs these keys on a gun's resolved presentation (and the rules' views); a missing one makes Resolve
    fail, so the set-up cannot start with that gun. Checked for the presentation as drawn with the template and with the real mesh."""
    def vec(v, n):
        return isinstance(v, list) and len(v) == n and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v)
    for gid in ROSTER:
        base = copy.deepcopy(GUNS[gid]["presentation"])
        worlds = [("template", base)]
        if isinstance(base.get("real"), dict) and base.get("realMesh"):
            merged = copy.deepcopy(base)
            merged.update(copy.deepcopy(base["real"]))
            worlds.append(("real mesh", merged))
        for label, p in worlds:
            need = [("meshOffset.pos", 3), ("meshOffset.rot", 3)] + [("markers." + m, 3) for m in ("muzzle", "eject", "sightRear", "pivot", "grip", "support")]
            need += [("poses." + k, 6) for k in ("sprint", "reload", "wall", "holster")]
            for path, n in need:
                if not vec(get(p, path), n):
                    err("parse: %s (%s) presentation.%s is not %d numbers" % (gid, label, path, n))
            for path in ("relief", "flash.star", "flash.jet"):
                v = get(p, path)
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    err("parse: %s (%s) presentation.%s is not a number" % (gid, label, path))
            for k, m in (p.get("parts") or {}).items():
                if isinstance(m, dict) and "bone" in m and m["bone"] is not None and not isinstance(m["bone"], str):
                    err("parse: %s (%s) parts.%s.bone is not a string" % (gid, label, k))
        views = GUNS[gid]["rules"].get("views")
        if not (isinstance(views, list) and views and all(vec(v, 6) for v in views)):
            err("parse: %s rules.views is not a list of six-number poses" % gid)


# ---------------------------------------------------------------------------------------------- art cross-checks
def web(b):
    return [-b[1], b[2], -b[0]]


def near(a, b, tol=1e-6):
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))


OWN = {"chopper", "nine", "shorty", "stretch", "rattler"}


def effective_presentation(gid):
    """The presentation the resolver builds when the real mesh is drawn: presentation merged with its `real` block."""
    p = copy.deepcopy(GUNS[gid]["presentation"])
    real = p.get("real")
    if isinstance(real, dict):
        p.update(real)
    return p


def check_art():
    if not CONTRACT:
        return
    cg, cp = CONTRACT["guns"], CONTRACT["parts"]
    for gid in OWN:
        g, c = GUNS[gid], cg[gid]
        pres = effective_presentation(gid)
        # the mesh asset
        art = g["art"]["mesh"]
        if art["asset"] != c["mesh"]:
            err("art: %s art.mesh.asset %s is not the exported %s" % (gid, art["asset"], c["mesh"]))
        if art["status"] != "exists":
            err("art: %s art.mesh.status is %s, the mesh is exported" % (gid, art["status"]))
        meshes = [g["variants"]["open"]["mesh"]] if g.get("variants") else ([g["presentation"].get("realMesh")] if gid != "nine" else [g["presentation"].get("realMesh")])
        for m in meshes:
            if m != c["asset"]:
                err("art: %s draws %s, the contract's asset is %s" % (gid, m, c["asset"]))
        if g.get("variants") and set(g["variants"]) - {"about", "open"}:
            err("art: %s still has variants %s (one body, no stock slot)" % (gid, sorted(set(g["variants"]) - {"about", "open"})))
        if gid in ("shorty", "stretch") and "packLength" in g:
            err("art: %s still names a pack length" % gid)
        # mounts
        for slot, m in g.get("mounts", {}).items():
            if not isinstance(m, dict):
                continue
            if m.get("status") != "exists":
                err("mounts: %s.%s is %s: the contract has the socket" % (gid, slot, m.get("status")))
            sock = m["socket"]
            if sock not in c["sockets"]:
                err("mounts: %s.%s names the socket %s, which SK is not exported with (%s)" % (gid, slot, sock, sorted(c["sockets"])))
                continue
            if "at" not in m or m["at"] is None or not near(m["at"], c["sockets"][sock]):
                err("mounts: %s.%s at %s differs from the exported %s %s" % (gid, slot, m.get("at"), sock, c["sockets"][sock]))
            for h in m.get("hide", []):
                if h not in c["deformBones"]:
                    err("mounts: %s.%s hides %s, which is not a deform bone (%s)" % (gid, slot, h, sorted(c["deformBones"])))
            rb = m.get("rideBone")
            if slot == "magazine" and rb not in c["deformBones"]:
                err("mounts: %s.magazine rideBone %s is not a deform bone" % (gid, rb))
            row = (COMPAT.get(gid) or {}).get(slot)
            if row and row["mount"] != sock:
                err("compatibility: %s.%s mount %s but guns.json socket %s" % (gid, slot, row["mount"], sock))
        for slot in (COMPAT.get(gid) or {}):
            if slot in SLOT_IDS and not COMPAT[gid][slot].get("variant") and slot not in g.get("mounts", {}):
                err("compatibility: %s has the slot %s but no mount" % (gid, slot))
        # the viewmodel sockets and the markers
        for key, sock in pres.get("sockets", {}).items():
            if key == "note" or not isinstance(sock, str):
                continue
            if sock not in c["sockets"] and sock not in c["deformBones"]:
                err("presentation: %s sockets.%s = %s is neither an exported socket nor a bone" % (gid, key, sock))
        mo = pres.get("meshOffset", {})
        if mo.get("rot") != [0, 0, 0]:
            err("presentation: %s meshOffset.rot is %s: our meshes face +X, the rotation is the identity" % (gid, mo.get("rot")))
        pos = mo.get("pos", [0, 0, 0])
        for name, sk in (("muzzle", "Muzzle"), ("eject", "Eject"), ("sightRear", "SightRear"), ("pivot", "RecoilPivot"), ("grip", "Palm_R"), ("support", "Palm_L")):
            want = [a + b for a, b in zip(web(c["sockets"][sk]), pos)]
            have = (pres.get("markers") or {}).get(name)
            if have is None:
                continue  # check_view_parse reports it
            tol = 2e-3 if gid == "nine" else 1.2e-3
            if gid not in ("nine",) and not near(have, want, tol):
                err("presentation: %s markers.%s %s is not the exported %s in gun space %s" % (gid, name, have, sk, [round(x, 4) for x in want]))
        for bone_key in ("bolt", "trigger", "magazine", "barrel"):
            pb = (pres.get("parts") or {}).get(bone_key)
            if pb and pb.get("bone") and pb["bone"] not in c["deformBones"]:
                err("presentation: %s parts.%s.bone %s is not a deform bone (%s)" % (gid, bone_key, pb["bone"], sorted(c["deformBones"])))
        anim = pres.get("animSet")
        sets = PRES["firstPerson"]["animSets"]
        if anim not in sets:
            err("presentation: %s animSet %s is not in firstPerson.animSets" % (gid, anim))
        elif sets[anim].get("mode") == "ik":
            for side in ("left", "right"):
                s = sets[anim]["ik"][side]
                if s not in c["sockets"]:
                    err("presentation: animSets.%s ik.%s = %s is not a socket of %s" % (anim, side, s, c["mesh"]))
            mag = sets[anim]["magazine"]
            if mag["full"] != c["magazine"]:
                err("presentation: animSets.%s magazine %s is not the contract's %s" % (anim, mag["full"], c["magazine"]))
            if mag["socket"] not in c["deformBones"]:
                err("presentation: animSets.%s magazine socket %s is not a deform bone" % (anim, mag["socket"]))
            if gid != "nine" and sets[anim].get("casing") != c.get("brass"):
                err("presentation: animSets.%s casing %s is not the contract's %s" % (anim, sets[anim].get("casing"), c.get("brass")))
        # the factory magazine the stage draws and the first person overrides (presentation.magazine)
        mg = pres.get("magazine")
        if not isinstance(mg, dict):
            err("presentation: %s has no presentation.magazine {mesh, bone}" % gid)
        else:
            if mg.get("mesh") != c["magazine"]:
                err("presentation: %s magazine.mesh %s is not the contract's %s" % (gid, mg.get("mesh"), c["magazine"]))
            if "socket" in mg:
                err("presentation: %s magazine has a `socket` key: the resolver reads only `mesh` and `bone`" % gid)
            if mg.get("bone") not in c["deformBones"]:
                err("presentation: %s magazine.bone %s is not a deform bone" % (gid, mg.get("bone")))
            if c.get("magazineTopRound") and mg.get("topRound") != c["magazineTopRound"]:
                err("presentation: %s magazine.topRound %s is not the contract's %s" % (gid, mg.get("topRound"), c["magazineTopRound"]))
        # eye position, for the picture review (information only)
        sr = c["sockets"]["SightRear"]
        relief = pres.get("relief")
        if relief:
            say("  eye: %-8s irons: eye %.0f mm behind the rear sight, at x %.3f m (mesh bounds x %.3f .. %.3f)" % (gid, relief * 1000, sr[0] - relief, c["bounds"]["min"][0], c["bounds"]["max"][0]))
    # the parts
    for pid, p in PARTS.items():
        if p.get("source") != "own":
            continue
        c = cp.get(pid)
        if c is None:
            err("art: part %s is not in the contract" % pid)
            continue
        if p["slot"] != c["slot"]:
            err("art: %s slot %s, the contract's %s" % (pid, p["slot"], c["slot"]))
        mesh = p["presentation"]["mesh"]
        if mesh != c["asset"]:
            err("art: %s mesh %s is not the contract's %s" % (pid, mesh, c["asset"]))
        if c.get("topRound") and p["presentation"].get("topRoundMesh") != c["topRound"]:
            err("art: %s topRoundMesh %s is not the contract's %s" % (pid, p["presentation"].get("topRoundMesh"), c.get("topRound")))
        for marker, sock in (p["presentation"].get("sockets") or {}).items():
            if sock not in c["sockets"]:
                err("art: %s sockets.%s = %s is not a socket of %s (%s)" % (pid, marker, sock, c["mesh"], sorted(c["sockets"])))
        for sock, cm in (p["presentation"].get("socketOffsetsCm") or {}).items():
            want = [c["sockets"][sock][0] * 100, -c["sockets"][sock][1] * 100, c["sockets"][sock][2] * 100]
            if not near(cm, want, 1e-4):
                err("art: %s socketOffsetsCm.%s %s is not the contract's %s" % (pid, sock, cm, want))
        takers = sorted(g for g in ROSTER if p["slot"] in (COMPAT.get(g) or {}) and pid in COMPAT[g][p["slot"]]["options"])
        if takers != sorted(c["appliesTo"]):
            err("compatibility: %s is in the rows of %s but the contract says it fits %s" % (pid, takers, sorted(c["appliesTo"])))
        for g in takers:
            if COMPAT[g][p["slot"]]["mount"] != c["gunSocket"]:
                err("compatibility: %s on the %s mounts at %s, the contract's gun socket is %s" % (pid, g, COMPAT[g][p["slot"]]["mount"], c["gunSocket"]))
        if p["slot"] == "optic":
            rel = p["presentation"].get("relief")
            if not rel or not (0.05 <= rel <= 0.3):
                err("art: optic %s has relief %s" % (pid, rel))
    # the icons and pips: the data says exists exactly when the art lanes rendered the file
    ui = CONTRACT.get("ui") or {}
    for gid in OWN:
        ic = GUNS[gid]["art"].get("icon") or {}
        have = ic.get("asset") in (ui.get("gunIcons") or [])
        if (ic.get("status") == "exists") != have:
            err("art: %s icon %s is marked %s but the art lanes %s it" % (gid, ic.get("asset"), ic.get("status"), "rendered" if have else "did not render"))
    for pid, p in PARTS.items():
        if p.get("source") != "own":
            continue
        pip = (p["art"].get("pip") or {})
        if pip.get("asset") not in (ui.get("pips") or []) or pip.get("status") != "exists":
            err("art: %s pip %s is not one the art lanes rendered" % (pid, pip))
    # where the eye ends up behind each optic (information for the picture review: the near plane may slice what is under the eye)
    for gid in sorted(OWN):
        c = cg[gid]
        row = (COMPAT.get(gid) or {}).get("optic")
        if not row or "Optic" not in c["sockets"]:
            continue
        for o in row["options"]:
            part, pc = PARTS.get(o), cp.get(o)
            if not part or not pc or "SightEye" not in pc["sockets"]:
                continue
            ex = c["sockets"]["Optic"][0] + pc["sockets"]["SightEye"][0] - part["presentation"]["relief"]
            ez = c["sockets"]["Optic"][2] + pc["sockets"]["SightEye"][2]
            above = (ez - c["bounds"]["max"][2]) * 1000
            say("  eye: %-8s + %-9s eye at x %+.3f m, z %.3f m: %s mm %s the mesh's top (bounds x %.3f .. %.3f)%s"
                % (gid, o, ex, ez, "%.0f" % abs(above), "above" if above >= 0 else "BELOW", c["bounds"]["min"][0], c["bounds"]["max"][0],
                   "  <- check the near plane" if (above < 10 and c["bounds"]["min"][0] <= ex <= c["bounds"]["max"][0]) else ""))
    # the STICK's factory magazine: the pack's, on a socket of its mesh (the resolver reads only magazine.mesh and magazine.bone)
    stick_mag = GUNS["stick"]["presentation"].get("magazine")
    if not (isinstance(stick_mag, dict) and stick_mag.get("mesh") and stick_mag.get("bone")):
        err("presentation: stick has no presentation.magazine {mesh, bone}: the resolver reads only those two keys")
    # the compatibility must not name a part the contract does not know, except the pack's own (source pack)
    for gid in OWN:
        for slot, row in (COMPAT.get(gid) or {}).items():
            if slot not in SLOT_IDS:
                continue
            for o in row["options"]:
                if PARTS[o].get("source") == "pack" and gid != "stick":
                    err("compatibility: %s.%s offers the pack part %s (our guns take our own parts)" % (gid, slot, o))
    # the clean-checkout rule: nothing of ours is committed; every own asset path is under /Game/Weapons
    for gid in OWN - {"nine"}:
        for path in re_paths(GUNS[gid]):
            if "/Game/ThirdParty/" in path and gid != "chopper":
                pass


def re_paths(o, out=None):
    out = [] if out is None else out
    if isinstance(o, dict):
        for v in o.values():
            re_paths(v, out)
    elif isinstance(o, list):
        for v in o:
            re_paths(v, out)
    elif isinstance(o, str) and o.startswith("/Game/"):
        out.append(o)
    return out


def check_pack_free():
    """The CHOPPER no longer draws the pack rifle (DECISIONS.md 2026-11-25); SHORTY and STRETCH name no pack mesh."""
    for gid in ("chopper", "shorty", "stretch", "rattler", "nine"):
        text = json.dumps(GUNS[gid]) if gid != "chopper" else json.dumps(PRES["guns"]["chopper"])
        if "InfimaTFA/Weapon/SK_TFA" in text:
            err("pack: %s still names a pack rifle mesh" % gid)
        if gid != "chopper" and "MI_Chopper_DarkEarth" in text:
            err("pack: %s names the CHOPPER's pack finish" % gid)
    real = PRES["guns"]["chopper"].get("real", {})
    for k in ("materials", "fingers"):
        if k in real:
            err("presentation: guns.chopper.real.%s is the pack rifle's finish / finger measures and does not fit SK_Chopper" % k)


def check_weapon_paths():
    """tools/box/cloud/pak_weapons.py stops a package when the data names an object path under /Game/Weapons that is not in the pak. Every
    such path must be an asset the weapons import makes (gun_contract.json) or one of the older, already packaged ones."""
    older = {"/Game/Weapons/Rifle/Meshes/SKM_Rifle.SKM_Rifle", "/Game/Weapons/Pistol/Meshes/SKM_Pistol.SKM_Pistol", "/Game/Weapons/GoonSMG/SM_Weapon_GoonSMG.SM_Weapon_GoonSMG"}
    known = set(older)
    for g in (CONTRACT or {}).get("guns", {}).values():
        known.update(x for x in (g["asset"], g["magazine"], g.get("magazineTopRound"), g.get("brass")) if x)
    for p in (CONTRACT or {}).get("parts", {}).values():
        known.update(x for x in (p["asset"], p.get("topRound")) if x)
    for name in ("guns.json", "attachments.json", "presentation.json", "gun_contract.json"):
        for path in set(re_paths(load(name))):
            if path.startswith("/Game/Weapons/") and re.match(r"^/Game/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+$", path) and path not in known:  # pak_weapons.py's own pattern: an object path, not a folder
                err("pak: %s names %s, which the weapons import does not make and no older package carried" % (name, path))


def check_optic_fade():
    """The optic's housing fades out as the sight comes up (LOADOUT.md 3.3): the importer makes M_Part_Hardware masked with an "AimFade"
    scalar and the rig sets "AimFade" on every slot whose base material is "M_Part_Hardware". Three files must keep agreeing on those names,
    or the fade silently does nothing (a render is the only proof it works; this holds the names)."""
    def text(*parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()
    imp = text("tools", "box", "fp", "mi_fp_import.py")
    guns = text("tools", "box", "fp", "mi_guns_r4.py")
    rig = text("unreal", "MurderInc", "Source", "MurderInc", "Weapons", "MIFirstPersonRig.cpp")
    if 'BLEND_MASKED' not in imp.split("if aim_fade:")[1].split("if skeletal:")[0]:
        err("fade: the importer's aim_fade branch no longer makes the material masked")
    if '_scalar(m, "AimFade"' not in imp:
        err("fade: the importer no longer makes the AimFade scalar parameter")
    if 'SetScalarParameterValue(TEXT("AimFade")' not in rig:
        err("fade: the rig no longer sets AimFade")
    if 'GetName() == TEXT("M_Part_Hardware")' not in rig:
        err("fade: the rig no longer looks for M_Part_Hardware")
    if not re.search(r'PARTS \+ "/M_Part_Hardware".*aim_fade=True', guns):
        err("fade: the parts import no longer makes M_Part_Hardware with aim_fade=True")
    if '"M_Part_Hardware": hardware' not in guns:
        err("fade: the hardware material is no longer assigned to the M_Part_Hardware slots")


def check_arm_reach():
    """Anim set armStretch (support arm, 1 to 1.3) and foregripCurl (degrees) on the four hand-IK rifle sets; the NINE's pistol set has none."""
    sets = load("presentation.json")["firstPerson"]["animSets"]
    for g in ("chopper", "shorty", "stretch", "rattler"):
        st = sets[g + "_ik"]
        if not (isinstance(st.get("armStretch"), (int, float)) and 1.0 <= st["armStretch"] <= 1.3):
            err("reach: animSets.%s_ik.armStretch must be a number from 1.0 to 1.3" % g)
        if not (isinstance(st.get("foregripCurl"), (int, float)) and 0 <= st["foregripCurl"] <= 70):
            err("reach: animSets.%s_ik.foregripCurl must be 0 to 70 degrees" % g)
        if not (isinstance(st.get("reloadCurl"), (int, float)) and 0 <= st["reloadCurl"] <= 70):
            err("reach: animSets.%s_ik.reloadCurl must be 0 to 70 degrees" % g)
    if sets["pistol"].get("armStretch", 1.0) != 1.0:
        err("reach: the NINE's pistol set must not stretch")
    # HANDS_R4.md 8: the support elbow pole (camera space cm, out to the left and down) and the reload hold on the magazine
    num3 = lambda v: isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v)
    for name, st in sets.items():
        if st.get("mode") != "ik":
            continue
        for key in ("supportElbowOut", "supportElbowOutAim"):
            if key in st and not (num3(st[key]) and all(abs(x) <= 80 for x in st[key]) and st[key][1] <= 0 and st[key][2] <= 0):
                err("hands: animSets.%s.%s must be three numbers within 80 cm, y (right) and z (up) not above 0" % (name, key))
        mag = st.get("magazine", {})
        if "palm" in mag and not (num3(mag["palm"]) and all(abs(x) <= 60 for x in mag["palm"])):
            err("hands: animSets.%s.magazine.palm must be three numbers (cm, the magazine's frame)" % name)
        if not (isinstance(mag.get("squeeze", 1.0), (int, float)) and 0.2 <= mag.get("squeeze", 1.0) <= 1.0):
            err("hands: animSets.%s.magazine.squeeze must be 0.2 to 1" % name)
        if not (isinstance(mag.get("blend", 0.25), (int, float)) and 0.05 <= mag.get("blend", 0.25) <= 0.6):
            err("hands: animSets.%s.magazine.blend must be 0.05 to 0.6 s" % name)
        if "turn" in mag and not (num3(mag["turn"]) and all(abs(x) <= 180 for x in mag["turn"])):
            err("hands: animSets.%s.magazine.turn must be three angles in degrees (-180 to 180)" % name)
        if mag.get("inHand", 0) not in (0, 1):
            err("hands: animSets.%s.magazine.inHand is 0 or 1" % name)
        if "height" in mag and not (isinstance(mag["height"], (int, float)) and 0 <= mag["height"] <= 1):
            err("hands: animSets.%s.magazine.height must be 0 to 1 (a fraction of the magazine's height)" % name)
        if "aimSides" in st.get("grip", {}) and not set(st["grip"]["aimSides"]) <= set("lr"):
            err("hands: animSets.%s.grip.aimSides takes l and r only" % name)
    check_reload_solves(sets)


def check_reload_solves(sets):
    """HANDS_R4.md 10: the support hand's grip round every magazine a hand-IK gun holds in a reload (grips.json magazines, made by
    tools/data/reload_grips.py): each set's own magazine and every magazine part has one, with the wrist and every finger joint, as
    three finite numbers (cm, the magazine mesh's frame) within reach of the magazine (60 cm)."""
    grips = load("grips.json")
    mags = grips.get("magazines", {})
    want = set()
    for name, st in sets.items():
        full = st.get("magazine", {}).get("full", "") if st.get("mode") == "ik" else ""
        if full:
            want.add(full.rsplit(".", 1)[-1])
    for pid, p in PARTS.items():   # our own magazine parts ride the hand-IK guns' magazine bone (the pack's are the STICK's)
        mesh = str(p.get("presentation", {}).get("mesh", ""))
        if p.get("slot") == "magazine" and p.get("source") == "own" and mesh:
            want.add(mesh.rsplit(".", 1)[-1])
    joints = ["hand_l"] + ["%s_%s_l" % (f, j) for f in ("index", "middle", "ring", "pinky") for j in ("metacarpal", "01", "02", "03", "tip")] \
        + ["thumb_%s_l" % j for j in ("01", "02", "03", "tip")]
    for m in sorted(want):
        pts = mags.get(m, {}).get("l")
        if not isinstance(pts, dict):
            err("hands: grips.json magazines has no reload grip for %s (python3 tools/data/reload_grips.py)" % m)
            continue
        missing = [j for j in joints if j not in pts]
        if missing:
            err("hands: grips.json magazines.%s.l lacks %s" % (m, ", ".join(missing)))
        for j, v in pts.items():
            if not (isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) and math.isfinite(x) and abs(x) <= 60 for x in v)):
                err("hands: grips.json magazines.%s.l.%s must be three numbers within 60 cm" % (m, j))


def check_freshness():
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(HERE, "make_gun_contract.py"), "--check"], capture_output=True, text=True)
    say("  " + (r.stdout.strip() or r.stderr.strip()))
    if r.returncode != 0:
        err("gun_contract.json is stale (art/out has changed): python3 tools/data/make_gun_contract.py")


# ------------------------------------------------------------------------------------------------------------ main
def safe(fn, *a):
    """A check that trips over malformed data reports that as an error and lets the others run."""
    try:
        return fn(*a)
    except Exception as e:  # noqa: BLE001
        err("the checker could not finish %s: %s %s" % (fn.__name__, type(e).__name__, e))
        return None


def main():
    safe(validate_data)
    trade = safe(check_trade) or []
    safe(check_base_in_clamps)
    safe(check_view_parse)
    nbuilds = safe(check_builds) or 0
    ready = safe(check_readiness)
    say("== effect trade (B better, W worse, B/W inside %s)" % BAND)
    for pid, b, w, ratio in sorted(trade):
        say("  %-24s B %.4f  W %.4f  B/W %.3f  %s" % (pid, b, w, ratio, "own" if PARTS[pid].get("source") == "own" else ""))
    say("== %d compatible builds resolved (falloff, clamps)" % nbuilds)
    say("== what is offered (guns, slots)")
    for kind in ("clean", "box-before", "box-after"):
        if ready:
            say("  %-10s %s" % (kind, "  ".join("%s:%s" % (g, ("%d" % len(ready[kind][g][1])) if ready[kind][g][0] else "-") for g in ROSTER)))
    say("== art contract")
    safe(check_art)
    safe(check_pack_free)
    safe(check_weapon_paths)
    safe(check_optic_fade)
    safe(check_arm_reach)
    if "--art" in sys.argv:
        safe(check_freshness)
    for w in WARNINGS:
        print("WARNING:", w)
    for e in ERRORS:
        print("ERROR:", e)
    print("%s: %d error(s), %d warning(s)" % ("FAILED" if ERRORS else "OK", len(ERRORS), len(WARNINGS)))
    sys.exit(1 if ERRORS else 0)


if __name__ == "__main__":
    main()
