#!/usr/bin/env python3
"""Writes unreal/MurderInc/Content/Data/gun_contract.json from what the art lanes exported (weapons round 4).

The contract is our own data: for each of the five own guns the sockets and the deform bones (metres, the mesh's own frame),
for each part its mount socket, its own sockets and the guns it fits. A test can hold guns.json, attachments.json and
presentation.json to it in a clean checkout, where art/out does not exist (art/out is never committed).

  python3 tools/data/make_gun_contract.py            write the file
  python3 tools/data/make_gun_contract.py --check    exit 1 when the file is not what art/out says now (stale)
  python3 tools/data/make_gun_contract.py --anchors  print the gun-space anchors worked out for presentation.json

Sources: art/out/manifest.json (the guns: skeleton block), art/blender/assets/weapons_parts_contract.json (the parts), and
art/out/weapons_r4.json when it exists (the hand-off of the weapons lanes; its part sockets must agree, else this stops).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "art", "out")
DATA = os.path.join(REPO, "unreal", "MurderInc", "Content", "Data")
TARGET = os.path.join(DATA, "gun_contract.json")

GUNS = [  # (gun id, art asset, asset folder under /Game/Weapons, magazine mesh, brass mesh)
    ("chopper", "SK_Chopper", "Chopper", "SM_Weapon_ChopperMagazine", "SM_Weapon_CasingRifle"),
    ("nine", "SK_Nine", "Nine", "SM_Weapon_NineMagazine", None),
    ("shorty", "SK_Shorty", "Shorty", "SM_Weapon_ShortyMagazine", "SM_Weapon_CasingRifle"),
    ("stretch", "SK_Stretch", "Stretch", "SM_Weapon_StretchMagazine", "SM_Weapon_CasingRifle"),
    ("rattler", "SK_Rattler", "Rattler", "SM_Weapon_RattlerMagazine", "SM_Weapon_CasingPistol"),
]
PARTS_FOLDER = "/Game/Weapons/Parts/"
BRASS_FOLDER = "/Game/Weapons/Casings/"


def clean(v):
    out = []
    for x in v:
        x = round(float(x) + 0.0, 6)
        out.append(int(x) if x == int(x) else x)
    return out


def web(b):
    """Blender metres (x forward, y left, z up) -> the viewmodel data's gun space (x right, y up, z toward the viewer)."""
    return [-b[1], b[2], -b[0]]


def compact(v, level=0, width=118):
    """JSON in the data files' style: numbers inline, one key a line."""
    ind = "  " * level
    if isinstance(v, dict):
        if not v:
            return "{}"
        one = "{" + ", ".join(json.dumps(k) + ": " + compact(x, 0, 10 ** 6) for k, x in v.items()) + "}"
        if len(one) + len(ind) <= 100 and all(not isinstance(x, (dict, list)) or (isinstance(x, list) and all(not isinstance(y, (dict, list)) for y in x)) for x in v.values()):
            return one
        return "{\n" + ",\n".join(ind + "  " + json.dumps(k) + ": " + compact(x, level + 1, width) for k, x in v.items()) + "\n" + ind + "}"
    if isinstance(v, list):
        one = "[" + ", ".join(compact(x, 0, 10 ** 6) for x in v) + "]"
        if all(not isinstance(x, (dict, list)) for x in v) and len(one) + len(ind) <= width:
            return one
        return "[\n" + ",\n".join(ind + "  " + compact(x, level + 1, width) for x in v) + "\n" + ind + "]"
    return json.dumps(v, ensure_ascii=False)


def build():
    manifest = json.load(open(os.path.join(OUT, "manifest.json")))
    parts_src = json.load(open(os.path.join(REPO, "art", "blender", "assets", "weapons_parts_contract.json")))["parts"]
    contract = {
        "meta": {
            "file": "gun_contract.json",
            "about": "What the art lanes exported for weapons round 4, as data: the own guns' sockets and deform bones and the parts kit's mounts and sockets. "
                     "guns.json mounts (socket, at, hide, rideBone), presentation.json (sockets, markers, parts bones, meshOffset) and attachments.json (part meshes, "
                     "sockets, compatibility) are held to it by tools/data/check_guns_data.py and by MurderInc.Loadout.SocketContract, which runs in a clean checkout "
                     "(art/out is never committed).",
            "game": "MURDER INC.",
            "schema": 1,
            "units": "metres, in the mesh's own frame: x forward along the bore, y left, z up. Unreal cm = (x, -y, z) x 100; the viewmodel data's gun space (web) = (-y, z, -x).",
            "source": "art/out/manifest.json of %s (the guns) and art/blender/assets/weapons_parts_contract.json (the parts)" % manifest.get("updated", "?"),
            "regenerate": "python3 tools/data/make_gun_contract.py   (add --check to see whether this file is stale)",
        },
        "assets": {"folder": "/Game/Weapons/", "parts": PARTS_FOLDER, "brass": BRASS_FOLDER,
                   "note": "an asset path is <folder>/<mesh>.<mesh>; the weapons import (tools/box/fp/import-chars.sh r4) puts each mesh there"},
        "guns": {},
        "parts": {},
    }
    for gid, sk, folder, mag, brass in GUNS:
        a = manifest["assets"][sk]
        sk_b = a["skeleton"]
        contract["guns"][gid] = {
            "mesh": sk,
            "asset": "/Game/Weapons/%s/%s.%s" % (folder, sk, sk),
            "triangles": a["triangles"],
            "bounds": {"min": clean(a["bounds_m"]["min"]), "max": clean(a["bounds_m"]["max"])},
            "deformBones": {k: clean(v["head_m"]) for k, v in sorted(sk_b.items()) if v.get("deform")},
            "sockets": {k: clean(v["head_m"]) for k, v in sorted(sk_b.items()) if not v.get("deform")},
            "materialSlots": [s["slot"] for s in a["material_slots"]],
            "textureSets": [s["set"] for s in a["material_slots"]],
            "magazine": "/Game/Weapons/%s/%s.%s" % (folder, mag, mag),
            "magazineTopRound": ("/Game/Weapons/%s/%s_TopRound.%s_TopRound" % (folder, mag, mag)) if (mag + "_TopRound") in manifest["assets"] else None,
            "brass": (BRASS_FOLDER + brass + "." + brass) if brass else None,
        }
    for pid, p in sorted(parts_src.items()):
        entry = {
            "mesh": p["mesh"],
            "asset": PARTS_FOLDER + p["mesh"] + "." + p["mesh"],
            "slot": p["slot"],
            "gunSocket": p["gun_socket"],
            "appliesTo": p["applies_to"],
            "sockets": {k: clean(v) for k, v in p["sockets_m"].items()},
            "bounds": {"min": clean(p["bounds_m"]["min"]), "max": clean(p["bounds_m"]["max"])},
            "materialSlots": p["material_slots"],
            "triangles": p["triangles"],
        }
        if p.get("top_round_mesh"):
            entry["topRound"] = PARTS_FOLDER + p["top_round_mesh"] + "." + p["top_round_mesh"]
        contract["parts"][pid] = entry
    ui = os.path.join(OUT, "ui")
    names = sorted(os.path.splitext(f)[0] for f in os.listdir(ui)) if os.path.isdir(ui) else []
    contract["ui"] = {
        "folder": "/Game/UI/Icons/",
        "gunIcons": [n for n in names if n.startswith("T_UI_Gun_")],
        "pips": [n for n in names if n.startswith("T_UI_Att_")],
        "note": "rendered by the weapons pipeline (white on transparent: guns 512 x 192, pips 128 x 128), never committed; the weapons import puts them in /Game/UI/Icons",
    }
    r4 = os.path.join(OUT, "weapons_r4.json")
    if os.path.exists(r4):
        check_against_r4(contract, json.load(open(r4)))
    return contract


def check_against_r4(contract, r4):
    """The weapons lanes' own hand-off must say the same as the committed parts contract; any difference stops the run."""
    parts = r4.get("parts") or {}
    bad = []
    for pid, p in contract["parts"].items():
        theirs = parts.get(pid) or parts.get(p["mesh"])
        if not isinstance(theirs, dict):
            continue
        socks = theirs.get("sockets_m") or theirs.get("sockets") or {}
        for k, v in p["sockets"].items():
            if k in socks and max(abs(a - b) for a, b in zip(socks[k], v)) > 1e-5:
                bad.append("%s socket %s: contract %s, weapons_r4.json %s" % (pid, k, v, socks[k]))
    if bad:
        sys.exit("weapons_r4.json disagrees with weapons_parts_contract.json:\n  " + "\n  ".join(bad))


def render(contract):
    return compact(contract) + "\n"


def anchors(contract):
    ch = contract["guns"]["chopper"]["sockets"]["Palm_R"]
    print("CHOPPER Palm_R in gun space (web):", [round(x, 4) for x in web(ch)])
    for gid in ("shorty", "stretch", "rattler"):
        pr = contract["guns"][gid]["sockets"]["Palm_R"]
        off = [a - b for a, b in zip(web(ch), web(pr))]
        print("%-8s Palm_R web %s -> mesh offset that puts it on the CHOPPER's palm: %s" % (gid, [round(x, 4) for x in web(pr)], [round(x, 4) for x in off]))


if __name__ == "__main__":
    c = build()
    if "--anchors" in sys.argv:
        anchors(c)
        sys.exit(0)
    text = render(c)
    if "--check" in sys.argv:
        have = open(TARGET, encoding="utf-8").read() if os.path.exists(TARGET) else ""
        # the 'source' line carries the manifest's timestamp: a re-export that changes nothing must not make the file stale
        strip = lambda s: "\n".join(l for l in s.splitlines() if '"source":' not in l)
        if strip(have) != strip(text):
            print("gun_contract.json is STALE: art/out says something else. Run: python3 tools/data/make_gun_contract.py")
            sys.exit(1)
        print("gun_contract.json is current")
        sys.exit(0)
    open(TARGET, "w", encoding="utf-8").write(text)
    print("wrote", os.path.relpath(TARGET, REPO), "(%d bytes): %d guns, %d parts" % (len(text), len(c["guns"]), len(c["parts"])))
