"""weapons_r4.json: the socket and slot contract of the round-4 guns and parts, written from the exported files and PROVED
against them.

    python art/blender/assets/_weapons_r4_contract.py          # writes art/out/weapons_r4.json and checks it (exit 1 on a miss)

For each of the five own guns (SK_Chopper, SK_Nine, SK_Shorty, SK_Stretch, SK_Rattler): every deform bone and every socket head
in gun space (Blender metres: X bore, Y left, Z up) and in Unreal centimetres ((x, -y, z) x 100), the material slots, the
triangle count, the eject direction; for each part: the file, the mount (the gun socket it sits on), its own sockets (metres and
Unreal cm), the slots and the hide bones its slot's fitted part asks for. The file travels in the parts archive
(tools/box/fp/fp-art.sh packr4 copies art/out/weapons_r4.json), and the import's socket pass compares what the project holds
against it.

The check re-imports every GLB in a fresh scene and measures every bone head against the contract to 1e-5 m, and every part's
.sockets.json against the part contract; so the contract cannot drift from the files. No number here is typed twice: the guns'
come from art/out/manifest.json (written by each family's export), the parts' from weapons_parts_contract.json, and the
eject directions and hide bones below are the specification's.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
if BL not in sys.path:
    sys.path.insert(0, BL)

from mi import paths  # noqa: E402

OUT = os.path.join(paths.out, "weapons_r4.json")
PARTS = os.path.join(HERE, "weapons_parts_contract.json")
GUNS = {"chopper": "SK_Chopper", "nine": "SK_Nine", "shorty": "SK_Shorty", "stretch": "SK_Stretch", "rattler": "SK_Rattler"}
# casing direction in gun space (X bore, Y left, Z up): the specification's
EJECT = {"shorty": (0.55, -0.80, 0.25), "stretch": (-0.15, -0.95, 0.30), "rattler": (0.0, -0.95, 0.31),
         "chopper": (0.0, -0.95, 0.30), "nine": (0.0, -0.95, 0.30)}
HIDE = {   # what a fitted part of the slot hides (HideBoneByName: the bone and its children)
    "chopper": {"optic": ["FrontSight"], "muzzle": ["Booster"]},
    "nine": {},
    "shorty": {"optic": ["IronsFront"], "muzzle": ["MuzzleDevice"]},
    "stretch": {"optic": ["IronsRear", "IronsFront"], "muzzle": ["MuzzleDevice"]},
    "rattler": {"optic": ["IronsFront", "IronsRear"], "muzzle": ["MuzzleDevice"]},
}
SLOTS = {"chopper": ["optic", "muzzle", "underbarrel"], "nine": ["muzzle", "laser", "magazine"],
         "shorty": ["optic", "muzzle", "underbarrel", "laser", "magazine"],
         "stretch": ["optic", "muzzle", "underbarrel", "magazine"], "rattler": ["optic", "muzzle", "magazine"]}


def ue(v):
    return [round(v[0] * 100.0, 4), round(-v[1] * 100.0, 4), round(v[2] * 100.0, 4)]


def build():
    man = json.load(open(os.path.join(paths.out, "manifest.json")))["assets"]
    parts = json.load(open(PARTS))
    out = {"about": "Round-4 weapons contract. Gun space = Blender: X forward along the bore, Y left, Z up, metres; Unreal = "
                    "(x, -y, z) x 100. Written by art/blender/assets/_weapons_r4_contract.py from the exported files and "
                    "proved against them (same script, --check is implied).",
           "guns": {}, "parts": {}, "sets": parts.get("sets", {})}
    for gid, sk in GUNS.items():
        e = man[sk]
        sk_ = e["skeleton"]
        out["guns"][gid] = {
            "mesh": sk, "triangles": e.get("triangles"), "slots": e.get("material_slots"),
            "bounds_m": e.get("bounds_m"),
            "bones": {n: {"head_m": b["head_m"], "head_unreal_cm": b["head_unreal_cm"], "parent": b["parent"]}
                      for n, b in sk_.items() if b.get("deform")},
            "sockets": {n: {"m": b["head_m"], "unreal_cm": b["head_unreal_cm"]} for n, b in sk_.items() if not b.get("deform")},
            "eject_dir_gun": list(EJECT[gid]), "eject_dir_unreal": [EJECT[gid][0], -EJECT[gid][1], EJECT[gid][2]],
            "workbench_slots": SLOTS[gid], "hide_bones_when_fitted": HIDE[gid]}
    for pid, rec in parts["parts"].items():
        out["parts"][pid] = rec
    return out


def check(out):
    """Re-import each GLB in a fresh scene and compare every joint head with the contract; compare each part's
    .sockets.json with the part contract. Returns the list of misses."""
    import bpy
    from mi import rig
    miss = []
    for gid, g in out["guns"].items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        arm, meshes, _c = rig.import_glb(os.path.join(paths.glb, g["mesh"] + ".glb"), "Imp_" + gid)
        heads = {b.name: [float(v) for v in (arm.matrix_world @ b.head_local)] for b in arm.data.bones}
        want = {n: b["head_m"] for n, b in g["bones"].items()}
        want.update({n: b["m"] for n, b in g["sockets"].items()})
        for n, h in want.items():
            if n not in heads:
                miss.append("%s: joint %s missing in the GLB" % (gid, n))
            elif max(abs(a - b) for a, b in zip(heads[n], h)) > 1e-5:
                miss.append("%s: joint %s at %s in the GLB, contract %s" % (gid, n, [round(v, 6) for v in heads[n]], h))
        extra = sorted(set(heads) - set(want) - {"body"})
        if extra:
            miss.append("%s: joints in the GLB that the contract does not list: %s" % (gid, extra))
        tris = sum(len(m.data.polygons) for m in meshes)          # polygons: the files are triangulated on export
        if g.get("triangles") and abs(tris - g["triangles"]) > max(8, 0.002 * g["triangles"]):
            miss.append("%s: %d triangles in the GLB, manifest says %d" % (gid, tris, g["triangles"]))
        print("%-8s %2d joints  %6d tris  %s" % (gid, len(heads), tris, "ok" if not [m for m in miss if m.startswith(gid)] else "MISS"))
    for pid, rec in out["parts"].items():
        f = os.path.join(paths.glb, rec["mesh"] + ".sockets.json")
        if not os.path.exists(f):
            miss.append("part %s: no %s.sockets.json" % (pid, rec["mesh"]))
            continue
        sj = json.load(open(f))
        sj = sj.get("sockets", sj)
        for n, m_ in (rec.get("sockets_m") or {}).items():
            got = sj.get(n)
            got = got.get("m") if isinstance(got, dict) else got
            if got is None or max(abs(a - b) for a, b in zip(got, m_)) > 1e-5:
                miss.append("part %s: socket %s %s in the file, contract %s" % (pid, n, got, m_))
    return miss


if __name__ == "__main__":
    c = build()
    with open(OUT, "w") as fh:
        json.dump(c, fh, indent=1, sort_keys=True)
    print("wrote", OUT, "(%d guns, %d parts)" % (len(c["guns"]), len(c["parts"])))
    miss = check(c)
    for m in miss:
        print("MISS", m)
    print("CONTRACT KEPT" if not miss else "CONTRACT HAS %d MISSES" % len(miss))
    sys.exit(1 if miss else 0)
