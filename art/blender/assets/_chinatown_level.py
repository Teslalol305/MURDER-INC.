"""Canal Street level data for the art lane (pure Python, no Blender): lane D's level file read as the art needs it.
Web metres (x, y up, z) are Blender (x, -z, y). Used by the placements (_chinatown_place, _chinatown_streets) and the
fitted structures (_chinatown_struct).
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
LEVEL = os.path.join(ROOT, "tools", "levels", "data", "level_chinatown.json")
_LV = {}


# ================================================================================================= level data (no Blender)

def level():
    if not _LV:
        with open(LEVEL) as f:
            _LV.update(json.load(f))
    return _LV


def boxes():
    return level()["colliders"]["boxes"]


def W(x0, x1, y0, y1, z0, z1):
    """A web box (x, y up, z) as Blender (lo, hi)."""
    return (np.array([min(x0, x1), -max(z0, z1), min(y0, y1)]), np.array([max(x0, x1), -min(z0, z1), max(y0, y1)]))


def cbox(i):
    w = boxes()[i]["web"]
    a, b_ = w["min"], w["max"]
    return W(a["x"], b_["x"], a["y"], b_["y"], a["z"], b_["z"])


def parts(*prefixes, exclude=()):
    """Collider indices whose `part` starts with one of the prefixes."""
    out = []
    for c in boxes():
        p = c.get("part") or ""
        if any(p.startswith(q) for q in prefixes) and not any(p.startswith(e) for e in exclude):
            out.append(c["index"])
    return out


def prop_colliders(name):
    return [i for p in level()["propPlacements"]["items"] if p["name"] == name for i in p.get("colliders", [])]


# the colliders each structure is fitted to (by lane D's part names, so a moved wall moves the art with it)
STRUCTS = {
    "SM_Struct_CT_MarketHall": lambda: parts("market.wall", "market.roof", "market.parapet", "B0.mass", "B0.parapet"),
    "SM_Struct_CT_ColdRoom": lambda: parts("coldroom."),
    "SM_Struct_CT_RoofBulkhead_B0": lambda: parts("B0.bulkhead"),
    "SM_Struct_CT_YardStair": lambda: parts("stair."),
    "SM_Struct_CT_SidewalkShed_Mott": lambda: parts("mottshed."),
    "SM_Struct_CT_BakeryKitchen": lambda: parts("bakery.wall.mott.kitchen", "bakery.wall.alley", "bakery.wall.yard",
                                                 "kitchen.", "bakery.floor"),
    "SM_Struct_CT_Arcade": lambda: parts("arcade.", "E1a.mass", "E1b.mass") + prop_colliders("arcade_pillar"),
    "SM_Struct_CT_BanquetFacade": lambda: parts("banquet.wall.square", "dub.wall.mott", "E2.upper", "e2.floor"),
}


def struct_pivot(name):
    """Blender min corner of the structure's colliders' union (the mesh's pivot and its placement)."""
    lo = np.min([cbox(i)[0] for i in STRUCTS[name]()], axis=0)
    return [round(float(v), 4) for v in lo]


def struct_places():
    """[(mesh, Blender pivot, collider indices)] for the placements (pure arithmetic)."""
    return [(n, struct_pivot(n), STRUCTS[n]()) for n in STRUCTS]
