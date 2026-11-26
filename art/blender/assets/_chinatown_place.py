"""Canal Street placements: the north row of Canal Street (N1 .. N6, chinatown.md 4.1 and 4.10) assembled from the Block's
facade kit (piers, bays, fills, cornice, parapet, fire escapes, air conditioners, blinds) and the Canal kit (shop fronts,
fascia, sign carriers with their faces, blades, neon, grilles, box awnings).

    venv/bin/python art/blender/assets/_chinatown_place.py     -> art/out/placements/placements_chinatown.json

Pure arithmetic: no mesh is built. Coordinates: the web level's (x, y, z) are Blender (x, -z, y); Unreal cm = (x, -y, z) x 100
of Blender; yaw = -rotation about Z (degrees). The north facade plane is web z = -33.0 (Blender y = +33.0), facing south,
so every module stands at rotation 0 on a frame running east from the building's west end, on the sidewalk (0.15 m).

Simplifications to settle with lane D's colliders (MAPS.md D3): the six 2.4 x 1.0 m alcoves are a residents' entrance
(SM_Facade_ResEntry_Red, flat, 2.8 m) at the alcove's x, not yet a 1.0 m recess; the ground storey is the Block's 3.65 m
(the design says 3.8: the upper floors sit 0.15 m lower); N4's brown brick and N5's green paint use the Block's Red and
Painted sets (the kit has no Brown fill wider than 0.25 m and no green brick); the N4 sidewalk shed is the Block's
SidewalkShed modules, placed by the level script, not here.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from assets import _chinatown_names as names  # noqa: E402

BAY, STOREY, GROUND, PIER_W, WIN_SILL = 3.1, 3.1, 3.65, 0.32, 0.60
ESC_L = 2.99
KERB_H = 0.15
LINE_Y = 33.0                     # Blender y of the north facade plane (web z = -33.0)
ENDS = {"Red": (0.60, 0.80), "Buff": (0.60, 0.85), "Painted": (0.60,)}
FRONTS = {"Wide": 6.0, "Narrow": 2.4, "Restaurant": 5.0, "Jewelry": 4.0, "Grocery": 6.0, "Shut": 6.0}

# web x range, storeys, brick, main front, face key (band), alcove centre x (web), fire escape bay (index or None),
# extras: blades (face key, s from the west end, z), neon (key, s, z), window sign (face key, s, z), awning (length, shop)
ROW = {
    "N1": dict(x=(-44.0, -29.0), storeys=6, brick="Painted", front="Wide", band="GoldHits", alcove=-35.0, escape=2,
               blade=("JadeTeapot", 1.2, GROUND + 0.9)),
    "N2": dict(x=(-29.0, -15.0), storeys=5, brick="Red", front="Jewelry", band="TwinCarp", alcove=-22.0, escape=None,
               window=("FarShore", GROUND + 2 * STOREY + 0.95)),
    "N3": dict(x=(-15.0, -1.0), storeys=5, brick="Buff", front="Restaurant", band="EightTreasure", alcove=-8.0, escape=1,
               awning=4.0),
    "N4": dict(x=(-1.0, 13.0), storeys=6, brick="Red", front="Grocery", band="SpringPine", alcove=5.0, escape=None),
    "N5": dict(x=(13.0, 26.0), storeys=5, brick="Painted", front="Wide", band="LongLife", alcove=20.0, escape=None,
               neon=("MahjongNeon", 1, GROUND + WIN_SILL + 0.55), awning=6.0),
    "N6": dict(x=(26.0, 44.0), storeys=7, brick="Red", front="Wide", band="SunnyDay", alcove=31.0, escape=None,
               blade=("HarborStar", None, GROUND + 1.6)),
}


def rng_seq(key):
    """A small deterministic sequence per building (no numpy: the placements must not depend on a library version)."""
    s = sum(ord(c) * (i + 1) for i, c in enumerate(key)) or 1

    def nxt():
        nonlocal s
        s = (s * 1103515245 + 12345) % (2 ** 31)
        return s / float(2 ** 31)
    return nxt


def entry(mesh, s, z, d, x0, building, role, scale=1.0, face=None, rot=0.0):
    """One instance at s metres along the row from x0, z above the sidewalk, d behind the wall plane (negative = in front)."""
    bx_, by_, bz_ = x0 + s, LINE_Y + d, KERB_H + z
    e = {"mesh": mesh, "building": building, "role": role,
         "blender_m": [round(bx_, 4), round(by_, 4), round(bz_, 4)], "rot_z_deg": rot,
         "location_cm": [round(bx_ * 100, 2), round(-by_ * 100, 2), round(bz_ * 100, 2)], "yaw": round(-rot % 360.0, 3)}
    if abs(scale - 1.0) > 1e-6:
        e["scale"] = [round(scale, 5), 1.0, 1.0]
    if face:
        e["face"] = face
        c = cells().get(face)
        if c:
            e["atlas"], e["atlas_uv"] = c["atlas"], c["uv"]
    return e


_CELLS = {}


def cells():
    if not _CELLS:
        p = os.path.join(HERE, "..", "..", "out", "textures", "Sign_CT_Atlas1", "set.json")
        if os.path.exists(p):
            with open(p) as f:
                _CELLS.update(json.load(f)["cells"])
    return _CELLS


def fill_name(k, p):
    w = min(ENDS[k], key=lambda v: abs(v - p))
    return "SM_Facade_Fill_%03d_%s" % (round(w * 100), k), w


def ground(key, B, out):
    x0, x1 = B["x"]
    W = x1 - x0
    a0, a1 = B["alcove"] - 1.4 - x0, B["alcove"] + 1.4 - x0
    out.append(entry("SM_Facade_ResEntry_Red", a0, 0.0, 0.0, x0, key, "alcove entrance"))
    segs = [(0.0, a0), (a1, W)]
    main = max(segs, key=lambda sg_: sg_[1] - sg_[0])
    shops = []
    for (s0, s1) in segs:
        span = s1 - s0
        mods = []
        first = B["front"] if (s0, s1) == main else None
        rest = span - PIER_W
        if first and FRONTS[first] + PIER_W <= rest + 1e-6:
            mods.append(first)
            rest -= FRONTS[first] + PIER_W
        while rest >= FRONTS["Narrow"] + PIER_W + 0.6:
            mods.append("Narrow")
            rest -= FRONTS["Narrow"] + PIER_W
        if not mods:
            mods.append("Narrow" if rest >= FRONTS["Narrow"] + 0.2 else None)
            if mods[0]:
                rest -= FRONTS["Narrow"] + PIER_W
        mods = [m for m in mods if m]
        end = PIER_W + max(rest, 0.0) / 2                          # the leftover goes into the two end piers
        s = s0
        out.append(entry("SM_Facade_Pier_" + B["brick"], s, 0.0, 0.0, x0, key, "pier", scale=end / PIER_W))
        s += end
        for i, m in enumerate(mods):
            out.append(entry("SM_Facade_Shopfront_CT_" + m, s, 0.0, 0.0, x0, key, "shop front"))
            out.append(entry("SM_Facade_CT_Fascia_1m", s, 2.77, 0.0, x0, key, "fascia", scale=FRONTS[m]))
            shops.append((m, s, FRONTS[m]))
            s += FRONTS[m]
            if i < len(mods) - 1:
                out.append(entry("SM_Facade_Pier_" + B["brick"], s, 0.0, 0.0, x0, key, "pier"))
                s += PIER_W
        out.append(entry("SM_Facade_Pier_" + B["brick"], s, 0.0, 0.0, x0, key, "pier", scale=(s1 - s) / PIER_W))
    # the band: over the main front, centred, in front of the fascia
    m, s, c = next(sh for sh in shops if sh[0] == B["front"]) if any(sh[0] == B["front"] for sh in shops) else shops[0]
    F = names.FACES[B["band"]]
    out.append(entry(F["carrier"], s + c / 2 - F["w"] / 2, 2.76, -0.075 - 0.20, x0, key, "sign band", face=B["band"]))
    for (m2, s2, c2) in shops:                                       # the other fronts: a shut neighbour's face stays blank
        if (m2, s2) != (m, s) and m2 == "Narrow":
            fk = "ForLease" if int(s2) % 2 else "ForRent"                 # a vacant neighbour: a paper sign in its glass
            out.append(entry(names.FACES[fk]["carrier"], s2 + 0.15, 1.35, -0.09, x0, key, "vacant sign", face=fk))
    if B.get("awning"):
        L = B["awning"]
        out.append(entry("SM_Facade_CT_Awning_Box_%dm" % int(L), s + c / 2 - L / 2, 2.35, 0.0, x0, key, "awning"))
    return shops


def uppers(key, B, out):
    x0, x1 = B["x"]
    W, k = x1 - x0, B["brick"]
    n = int(W // BAY + 1e-6)
    p = (W - n * BAY) / 2
    fname, fw = fill_name(k, p)
    rnd = rng_seq(key)
    esc = None if B["escape"] is None else p + B["escape"] * BAY + BAY / 2 - ESC_L / 2
    ups = B["storeys"] - 1
    for i in range(ups):
        z = GROUND + i * STOREY
        out.append(entry(fname, 0.0, z, 0.0, x0, key, "fill", scale=p / fw))
        out.append(entry(fname, W - p, z, 0.0, x0, key, "fill", scale=p / fw))
        for j in range(n):
            out.append(entry("SM_Facade_BayWindow_" + k, p + j * BAY, z, 0.0, x0, key, "bay"))
            xw = p + j * BAY + BAY / 2
            behind = esc is not None and esc - 0.3 < xw < esc + ESC_L + 0.3
            u = rnd()
            if B.get("neon") and i == 0 and j == B["neon"][1]:
                N = names.NEON[B["neon"][0]]
                out.append(entry(N["mesh"], xw - N["w"] / 2, B["neon"][2] - GROUND + z, -0.02, x0, key, "window neon"))
            elif i == 0 and not behind and u < 0.45:
                out.append(entry("SM_Facade_CT_WindowGrille", xw, z + WIN_SILL, 0.0, x0, key, "grille"))
            elif 0.45 <= u < 0.60 and not behind:
                out.append(entry("SM_Facade_AirConditioner", xw, z + WIN_SILL, 0.0, x0, key, "air conditioner"))
            elif u < 0.95:
                out.append(entry("SM_Facade_WindowBlind", xw, z + WIN_SILL, 0.0, x0, key, "blind"))
    zr = GROUND + ups * STOREY
    cl, cw = min(((v, "SM_Facade_CorniceEnd_L_%03d" % round(v * 100)) for v in (0.25, 0.60, 0.80, 0.85)), key=lambda t: abs(t[0] - p))
    out.append(entry(cw, 0.0, zr, 0.0, x0, key, "cornice", scale=p / cl))
    out.append(entry(cw.replace("_L_", "_R_"), W - p, zr, 0.0, x0, key, "cornice", scale=p / cl))
    pname, pw = fill_name(k, p)
    out.append(entry(pname.replace("Fill_", "ParapetFill_"), 0.0, zr, 0.0, x0, key, "parapet", scale=p / pw))
    out.append(entry(pname.replace("Fill_", "ParapetFill_"), W - p, zr, 0.0, x0, key, "parapet", scale=p / pw))
    for j in range(n):
        out.append(entry("SM_Facade_Cornice_310", p + j * BAY, zr, 0.0, x0, key, "cornice"))
        out.append(entry("SM_Facade_Parapet_310_" + k, p + j * BAY, zr, 0.0, x0, key, "parapet"))
    if esc is not None:
        for i in range(ups):
            z = GROUND + i * STOREY + 0.25
            out.append(entry("SM_Facade_FireEscape_Balcony", esc, z, 0.0, x0, key, "fire escape"))
            for bxs in (0.10, ESC_L / 2, ESC_L - 0.10):
                out.append(entry("SM_Facade_FireEscape_Bracket", esc + bxs, z, 0.0, x0, key, "fire escape"))
            if i == 0:
                out.append(entry("SM_Facade_FireEscape_Ladder", esc, z, 0.0, x0, key, "fire escape"))
            if i < ups - 1:
                out.append(entry("SM_Facade_FireEscape_Stair", esc, z, 0.0, x0, key, "fire escape"))
    if B.get("blade"):
        fk, s, z = B["blade"]
        s = (W - 1.6) if s is None else s
        out.append(entry(names.FACES[fk]["carrier"], s, z, 0.0, x0, key, "blade", face=fk))
    if B.get("window"):
        fk, z = B["window"]
        out.append(entry(names.FACES[fk]["carrier"], p + BAY + BAY / 2 - 1.5, z, -0.12, x0, key, "window sign", face=fk))
    return n


def assemble():
    out = []
    for key, B in ROW.items():
        ground(key, B, out)
        uppers(key, B, out)
    return out


def write_placements(path):
    out = assemble()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = {"about": "Canal Street, north row N1..N6 (chinatown.md 4.10), from assets/_chinatown_place.py: the Block's facade kit and "
                    "the Canal kit. Unreal centimetres (X east, Y south, Z up), yaw degrees about Z (0 = module as imported), "
                    "optional scale along the module's run (X); blender_m / rot_z_deg are the same in Blender metres. Signs carry "
                    "their face key and atlas cell (uv v-up). See the module docstring for what waits on lane D's colliders.",
           "buildings": {k: {"x_web": list(B["x"]), "storeys": B["storeys"], "brick": B["brick"], "front": B["front"], "band": B["band"]}
                         for k, B in ROW.items()},
           "count": len(out), "instances": out}
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    return len(out)


if __name__ == "__main__":
    p = os.path.join(HERE, "..", "..", "out", "placements", "placements_chinatown.json")
    print(write_placements(os.path.normpath(p)), "instances")
