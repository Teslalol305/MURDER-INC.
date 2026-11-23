"""Independent review renders and measurements of the exported player guns (critique round 2).

Reuses the round-1 review harness (weapons_review.py: fresh scene, studio HDRI, texture wiring from the sets on disk,
studio and first-person cameras, measurements) and adds what changed since: the CHOPPER's three material slots
(M_Chopper, M_Chopper_Furniture, M_Chopper_Front) and per-bone part extents.

    python art/blender/review/weapons_review_r2.py [--only Chopper|Nine] [--views left,...] [--samples 32]
    python art/blender/review/weapons_review_r2.py --measure-only

Outputs: art/blender/review/sheets/r2/weapons_<Gun>_<view>.jpg (1280 x 720), measure.json beside them.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import weapons_review as wr  # noqa: E402

wr.OUT = os.path.join(HERE, "sheets", "r2")
wr.GUNS["Chopper"]["sets"] = {
    "M_Chopper": "Chopper",
    "M_Chopper_Furniture": "Chopper_Furniture",
    "M_Chopper_Front": "Chopper_Front",
    "M_Weapon_ChopperMagazine": "Weapon_ChopperMagazine",
}

_measure = wr.measure


def measure(name, objs, meshes):
    res = _measure(name, objs, meshes)
    gun = next(o for o in meshes if o.name.startswith("SK_"))
    mw = gun.matrix_world
    co = np.array([tuple(mw @ v.co) for v in gun.data.vertices])
    vg = {g.index: g.name for g in gun.vertex_groups}
    dom = np.full(len(co), -1)
    best = np.zeros(len(co))
    for v in gun.data.vertices:
        for g in v.groups:
            if g.weight > best[v.index]:
                best[v.index], dom[v.index] = g.weight, g.group
    ext = {}
    for gi, gname in vg.items():
        sel = co[dom == gi]
        if len(sel):
            ext[gname] = [sel.min(0).round(4).tolist(), sel.max(0).round(4).tolist()]
    res["part_extents"] = ext
    for o in meshes:
        if o is gun:
            continue
        c = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
        res.setdefault("mag_extents", {})[o.name] = [c.min(0).round(4).tolist(), c.max(0).round(4).tolist()]
    return res


wr.measure = measure

if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--samples" not in argv:
        argv += ["--samples", "32"]
    sys.argv = [sys.argv[0]] + argv
    wr.main()
