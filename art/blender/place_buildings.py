"""Placement data for the street-facing buildings of the block, from the facade kit's own assembly helpers.

    uv run --no-project --with bpy==5.3.0 --with numpy --with pillow python art/blender/place_buildings.py
    (or venv/bin/python art/blender/place_buildings.py, art/blender/README.md "Set-up")

Writes art/out/placements/buildings.json: one entry per module instance, in Unreal coordinates (centimetres, X east,
Y south, Z up; yaw in degrees, yaw 0 = the module as imported). The level script of the Unreal project
(unreal/MurderInc/Content/Python/build_block.py) places these as instanced static meshes; the gameplay collision
stays the collider boxes of level.json.

The modules themselves are not built here: `assets.facade.put` only needs an object to copy per module name, so a
tiny stand-in mesh is made for each name on demand (seconds instead of building the kit). The fronts, side walls,
party-wall caps, roof panels and stair bulkheads come from `assemble_front` / `assemble_shell` exactly as the kit's
own sample uses them; what those helpers leave open (the backs of the buildings, the strip a side wall leaves at the
back corner) is closed here with blank common-brick bays, scaled along their run where a full bay does not fit.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402

from assets import facade  # noqa: E402
from assets.facade import BAY, BUILDINGS, LINE, SHOPS, STOREY, GROUND, T, Frame  # noqa: E402
from assets.street import KERB_H  # noqa: E402
from mi import scene  # noqa: E402

OUT = os.path.join(HERE, "..", "out", "placements", "buildings.json")

# Which ends of each building show (left / right as seen from the street), the stair bulkhead on its roof
# (Blender x, y of its centre: docs/unreal/spec/05-level.md 2.5.4), and whether the back wall is built.
# s1's left end (x -30) stands against the taller s2 and is never seen. Water tanks are catalogue props
# (props.json `water_tower`), placed by the level script, so none here.
SHELLS = {
    "n1": dict(sides=("L", "R"), bulkhead=(-35.5, 18.25)),
    "n2": dict(sides=("L", "R"), bulkhead=None),
    "s1": dict(sides=("R",), bulkhead=None),
    "s2": dict(sides=("L", "R"), bulkhead=(-19.5, -28.75)),
    "s3": dict(sides=("L", "R"), bulkhead=(13.0, -20.75)),
}
# Awning cloth per shop (spec 05-level.md 2.5.3, the web game's catalogue colours).
AWNING_TINT = {"Barber": "#1c2f5a", "Deli": "#1f5a3a", "Pizza": "#b3261e"}


class Stub:
    """What assets.facade.put needs from a build context, without building the kit."""

    def __init__(self, seed=0):
        self.seed = seed
        self.sample = scene.collection("Placements")
        self.K = _Modules()

    def rng(self, *key):
        return scene.rng("facade", self.seed, *key)          # the same stream as build.py's ctx.rng


class _Modules(dict):
    def __missing__(self, name):
        ob = bpy.data.objects.new(name, bpy.data.meshes.new(name))
        self[name] = ob
        return ob


def to_unreal(name, loc, rot, building, role, scale=1.0, extra=None):
    x, y, z = loc
    entry = {"mesh": name, "building": building, "role": role,
             "location": [round(x * 100.0, 2), round(-y * 100.0, 2), round(z * 100.0, 2)],
             "yaw": round(-rot % 360.0, 3)}
    if abs(scale - 1.0) > 1e-6:
        entry["scale"] = [round(scale, 5), 1.0, 1.0]
    if extra:
        entry.update(extra)
    return entry


def shop_at(key, x):
    """The shop of building `key` whose front spans Blender x."""
    for name, sh in SHOPS.items():
        if sh[0] == key and sh[1] - 0.01 <= x <= sh[2] + 0.01:
            return name
    return None


def closing_walls(key, sides):
    """The walls the kit's helpers leave open: the back (blank common bays from the roof down, the last one scaled to
    fit, a party-wall cap row on top) and, for each shown side, the strip between the last side bay and the back.
    Returns [(module, location, rotation, scale)] in Blender metres and degrees."""
    bd = BUILDINGS[key]
    x0, x1 = bd["x"]
    w, depth, north = x1 - x0, bd["depth"], bd["face"] == "N"
    zr = KERB_H + GROUND + (bd["storeys"] - 1) * STOREY
    out = []
    # The back: outer face toward the back of the lot. Front frames run +x facing -y (south fronts) or -x facing +y.
    back = Frame((x0, -LINE - depth, KERB_H), 0.0) if north else Frame((x1, LINE + depth, KERB_H), 180.0)
    runs = []
    s = 0.0
    while s < w - 1e-6:
        piece = min(BAY, w - s)
        runs.append((s, piece / BAY))
        s += piece
    z = zr - STOREY
    while z > -STOREY + KERB_H:
        for s, k in runs:
            out.append(("SM_Facade_BayBlank_Common", back.at(s, 0.0, z - KERB_H), back.rot, k))
        z -= STOREY
    for s, k in runs:
        out.append(("SM_Facade_PartyWallCap_310", back.at(s, 0.0, zr - KERB_H), back.rot, k))
    # Side strips: assemble_shell covers T + 0.6 + nb bays of the depth.
    nb = int((depth - T - 0.6) // BAY)
    rest = depth - T - 0.6 - nb * BAY
    if rest > 0.01:
        front = facade.front_frame(key)
        for side in sides:
            if side == "R":
                sf = Frame(front.at(w, T, 0.0), front.rot + 90.0)
                s0 = 0.6 + nb * BAY
            else:
                total = 0.6 + nb * BAY
                sf = Frame(front.at(0.0, T + total + rest, 0.0), front.rot - 90.0)
                s0 = 0.0
            z = zr - STOREY
            while z > -STOREY + KERB_H:
                out.append(("SM_Facade_BayBlank_Common", sf.at(s0, 0.0, z - KERB_H), sf.rot, rest / BAY))
                z -= STOREY
            out.append(("SM_Facade_PartyWallCap_310", sf.at(s0, 0.0, zr - KERB_H), sf.rot, rest / BAY))
    return out


def main():
    ctx = Stub()
    entries = []
    for key, shell in SHELLS.items():
        front, back = [], []
        facade.assemble_front(ctx, key, front)
        facade.assemble_shell(ctx, key, sides=shell["sides"], bulkhead=shell["bulkhead"], out=back)
        for name, loc, rot in front:
            extra = None
            if name.startswith("SM_Facade_Awning_"):
                # The awning's pivot is its left end as seen from the street, 0.32 m + a margin inside the shop.
                bd = BUILDINGS[key]
                x_mid = loc[0] - 2.0 if bd["face"] == "N" else loc[0] + 2.0
                shop = shop_at(key, x_mid)
                extra = {"shop": shop, "tint": AWNING_TINT.get(shop)}
            entries.append(to_unreal(name, loc, rot, key, "front", extra=extra))
        for name, loc, rot in back:
            entries.append(to_unreal(name, loc, rot, key, "shell"))
        for name, loc, rot, k in closing_walls(key, shell["sides"]):
            entries.append(to_unreal(name, loc, rot, key, "closing", scale=k))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    meshes = sorted({e["mesh"] for e in entries})
    doc = {
        "about": "Facade-kit instances of the street-facing buildings n1, n2, s1, s2, s3 (art/blender/place_buildings.py "
                 "from assets/facade.py assemble_front / assemble_shell). Unreal centimetres: X east, Y south, Z up; "
                 "yaw degrees about Z (0 = module as imported); optional scale along the module's run (X).",
        "buildings": {k: {"x_web": list(BUILDINGS[k]["x"]), "face": BUILDINGS[k]["face"], "storeys": BUILDINGS[k]["storeys"],
                          "depth_m": BUILDINGS[k]["depth"], "sides": list(v["sides"])} for k, v in SHELLS.items()},
        "count": len(entries),
        "meshes": meshes,
        "instances": entries,
    }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, indent=1)
    print("PLACEMENTS OK %s: %d instances of %d modules" % (os.path.normpath(OUT), len(entries), len(meshes)))
    for key in SHELLS:
        print("  %s: %d" % (key, sum(e["building"] == key for e in entries)))


if __name__ == "__main__":
    main()
