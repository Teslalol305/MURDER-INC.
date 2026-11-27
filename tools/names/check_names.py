"""Check the new levels' sign and screen names against the approved list (tools/names/names.json, MAPS.md lane C).

    python3 tools/names/check_names.py            # report; exit 1 if anything must still change
    python3 tools/names/check_names.py --json     # the same as JSON

Three checks, each re-run whenever an art lane or the layout tool changes a name:

1. RETIRED: no retired name (one that collided with a real business or mark) is left in the art lists, the atlas and
   placement code, the level layouts, the generated level files or the map designs. Ids built from a retired name
   (SeaBreeze, E1_Orbelle, ...) are listed too: they never reach the screen, but renaming them keeps the next search
   honest.
2. UNLISTED: every business name the art lists report (their business_names()) is on the approved list, a generic
   word, a real place or a story mark. A new name is searched and added to tools/names/build_names.py first.
3. ENGLISH: no CJK or other non-English character in the Canal Street and Midtown files (the owner's answer of
   2026-11-26: Canal Street signs in English only).

Pure Python 3 (no Blender, no Unreal). The art lists are loaded with runpy from their files; they import nothing but
the standard library.
"""
import argparse
import json
import os
import re
import runpy
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NAMES = os.path.join(ROOT, "tools", "names", "names.json")

# Files that carry the new levels' words. Missing files are skipped (other lanes create them as they go).
SCAN = [
    "art/blender/assets/_chinatown_names.py", "art/blender/assets/_chinatown_atlas.py", "art/blender/assets/_chinatown_place.py",
    "art/blender/assets/_chinatown_front.py", "art/blender/assets/_chinatown_kit.py", "art/blender/assets/_chinatown_preview.py",
    "art/blender/assets/chinatown.py", "art/blender/assets/signs.py",
    "art/blender/assets/_midtown_names.py", "art/blender/assets/_midtown_atlas.py", "art/blender/assets/_midtown_screens.py",
    "art/blender/assets/_midtown_roof.py", "art/blender/assets/_midtown_scaffold.py", "art/blender/assets/midtown.py",
    "art/blender/assets/_midtown_square.py", "art/blender/assets/_midtown_place.py", "art/blender/assets/_midtown_dress.py",
    "art/blender/assets/_midtown_set.py", "art/blender/assets/_midtown_facade.py", "art/blender/assets/_midtown_preview.py",
    "tools/levels/layouts/chinatown.py", "tools/levels/layouts/midtown.py",
    "tools/levels/data/level_chinatown.json", "tools/levels/data/level_midtown.json",
    "docs/unreal/maps/chinatown.md", "docs/unreal/maps/midtown.md", "docs/unreal/maps/progression.md",
    "docs/unreal/maps/characters.md", "docs/unreal/MAPS.md",
]
ART_LISTS = {"chinatown": "art/blender/assets/_chinatown_names.py", "midtown": "art/blender/assets/_midtown_names.py"}

# The part of each retired name that identifies it, and the ids the art code built from it.
RETIRED_TOKENS = {
    "SEA BREEZE TRAVEL": ["SEA BREEZE", "SeaBreeze"],
    "BRIGHT MOON HOTEL": ["BRIGHT MOON", "BrightMoon"],
    "LILY CAFE": ["LILY CAFE", "LilyCafe"],
    "CLEAR VIEW OPTICAL": ["CLEAR VIEW", "ClearView"],
    "ORBELLE": ["ORBELLE"],
    "THE ALDERWAY THEATRE": ["ALDERWAY"],
    "NIGHT SHIFT": ["NIGHT SHIFT"],
    "QUILLON": ["QUILLON"],
    "TAMSIN GRAY": ["TAMSIN GRAY", "TamsinGray"],
    "HALCYON SODA": ["HALCYON"],
    "MIDTOWN SLICE": ["MIDTOWN SLICE", "MidtownSlice"],
    "46TH ST CAMERA & ELECTRONICS": ["46TH ST CAMERA", "46thStCamera"],
    "LANTERN SAVINGS": ["LANTERN SAVINGS", "LanternSavings"],
    "CORNER CHEMISTS": ["CORNER CHEMISTS", "CornerChemists"],
    "THE PERCH": ["THE PERCH"],
}
CJK = re.compile("[⺀-⿿　-〿぀-ヿ㄀-ㇿ㈀-䶿一-鿿가-힯豈-﫿︰-﹏＀-￯]")


def load():
    with open(NAMES, encoding="utf-8") as f:
        return json.load(f)


def token_re(tok):
    # ids (no space, mixed case) match case-sensitively inside identifiers; words match case-insensitively on boundaries
    if " " not in tok and tok != tok.upper():
        return re.compile(re.escape(tok))
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(tok) + r"(?![A-Za-z0-9])", re.IGNORECASE)


def check_retired(data):
    retired = {n["text"]: n["replacedBy"] for n in data["names"] if n["status"] == "retired"}
    missing = set(retired) - set(RETIRED_TOKENS)
    assert not missing, "add tokens for %s" % sorted(missing)
    pats = [(name, tok, token_re(tok)) for name, toks in RETIRED_TOKENS.items() for tok in toks]
    hits = []
    for rel in SCAN:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                for name, tok, rx in pats:
                    m = rx.search(line)
                    if m:
                        # an id is a match inside or beside an identifier (E1_Orbelle, "SeaBreeze"); text is the words
                        ident = m.group(0) != m.group(0).upper() or line[max(0, m.start() - 1):m.start()] == "_"
                        hits.append(dict(file=rel, line=i, retired=name, use=retired[name], token=tok,
                                         kind="id" if ident else "text",
                                         excerpt=line.strip()[:140]))
    return hits


def norm(s):
    s = re.sub(r"\s*\(.*?\)\s*", " ", s).strip()
    return s.split("  ·  ")[0].strip().upper()


def check_unlisted(data):
    approved = {n["text"].upper() for n in data["names"] if n["status"] == "approved"}
    retired = {n["text"].upper() for n in data["names"] if n["status"] == "retired"}
    generic = {g.upper() for lst in data["generic"].values() for g in lst}
    places = {p.upper() for p in data["realPlaces"]}
    marks = {m.split(" ")[0].upper() for m in data["storyMarks"]}
    out = []
    for level, rel in ART_LISTS.items():
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            out.append(dict(level=level, file=rel, name=None, verdict="list file not found"))
            continue
        mod = runpy.run_path(path, run_name="names_check")
        names = mod["business_names"]()
        names = list(names.values()) if isinstance(names, dict) else list(names)
        for raw in names:
            n = norm(raw)
            if n in approved or n in generic or n in places or n in marks:
                continue
            if n in retired:
                out.append(dict(level=level, file=rel, name=raw, verdict="retired"))
                continue
            if any(a.startswith(n + " ") or n.startswith(a + " ") for a in approved):
                continue        # a blade or neon that carries part of an approved name (JADE TEAPOT DIM SUM, BIG LIGHT)
            out.append(dict(level=level, file=rel, name=raw, verdict="not on the approved list: search it and add it"))
    return out


def check_english():
    out = []
    for rel in SCAN:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                m = CJK.search(line)
                if m:
                    out.append(dict(file=rel, line=i, char="U+%04X" % ord(m.group(0))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    data = load()
    res = dict(retired=check_retired(data), unlisted=check_unlisted(data), english=check_english())
    if a.json:
        print(json.dumps(res, indent=1, ensure_ascii=False))
    else:
        appr = sum(1 for n in data["names"] if n["status"] == "approved")
        print("approved list: %d names (%d retired), searched %s, signed off: %s"
              % (appr, len(data["names"]) - appr, data["searched"], data["signedOff"] or "not yet"))
        by_file = {}
        for h in res["retired"]:
            by_file.setdefault(h["file"], []).append(h)
        print("\n1. RETIRED names still in use: %d lines in %d files" % (len(res["retired"]), len(by_file)))
        for rel, hs in by_file.items():
            print("  %s" % rel)
            for h in hs:
                print("    %5d  %-4s %-28s -> %-30s | %s" % (h["line"], h["kind"], h["token"], h["use"], h["excerpt"][:70]))
        print("\n2. UNLISTED names in the art lists: %d" % len(res["unlisted"]))
        for u in res["unlisted"]:
            print("  %-10s %-40s %s" % (u["level"], u["name"], u["verdict"]))
        print("\n3. Non-English characters: %d" % len(res["english"]))
        for e in res["english"]:
            print("  %s:%d %s" % (e["file"], e["line"], e["char"]))
    bad = len(res["retired"]) + len(res["unlisted"]) + len(res["english"])
    print("\n%s" % ("PASS" if not bad else "FAIL: %d items to change" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
