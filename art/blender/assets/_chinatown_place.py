"""Canal Street placements: the north row of Canal Street (N1 .. N6, chinatown.md 4.1 and 4.10) assembled from the Block's
facade kit (piers, bays, fills, cornice, parapet, fire escapes, air conditioners, blinds) and the Canal kit (shop fronts,
fascia, sign carriers with their faces, blades, neon, grilles, box awnings).

    venv/bin/python art/blender/assets/_chinatown_place.py     -> art/out/placements/placements_chinatown.json

Pure arithmetic: no mesh is built. Coordinates: the web level's (x, y, z) are Blender (x, -z, y); Unreal cm = (x, -y, z) x 100
of Blender; yaw = -rotation about Z (degrees). The north facade plane is web z = -33.0 (Blender y = +33.0), facing south,
so every module stands at rotation 0 on a frame running east from the building's west end, on the sidewalk (0.15 m).

No module is scaled (the review's finding: bricks stretched up to 5 times along end piers and fills): the piers, fills,
parapet fills, cornice ends and fascias at a building's own widths are Canal modules built at those widths.

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
PIER_MIN = 0.30                   # a pier at a front's end: at least this wide
ESC_L = 2.99
KERB_H = 0.15
LINE_Y = 33.0                     # Blender y of the north facade plane (web z = -33.0)
FRONTS = {"Wide": 6.0, "Narrow": 2.4, "Restaurant": 5.0, "Jewelry": 4.0, "Grocery": 6.0, "Shut": 6.0}

# web x range, storeys, brick, the fronts west and east of the alcove [(front, sign)], the band's face (it hangs over the
# front marked "band"), alcove centre x, fire-escape bay, and the extras: blades (face, s from the west end, z), window
# neon, window letters, awnings (front index), stacked sign rails [(s, faces from the bottom up)].
# Every front carries a sign: the band, a generic lightbox (WATCH REPAIR, KEYS CUT, PHONES) or a painted stall board
# (ROAST MEAT, FRUIT, VEGETABLES, DRY GOODS, TOFU): the generic words need no name search (tools/names/names.json).
# One vacancy paper on the whole row (it was eight). No module is scaled: piers, fills, parapet fills, cornice ends and
# fascias are built at the widths this table needs (needed_widths(), _chinatown_front.m_ct_widths), so no brick is stretched.
ROW = {
    "N1": dict(x=(-44.0, -29.0), storeys=6, brick="Painted", alcove=-35.0, escape=2, band="GoldHits",
               fronts=[[("Wide", "band")], [("Jewelry", "KioskWatch")]],
               blade=("JadeTeapot", 1.2, GROUND + 0.9), rails=[(12.6, ["KioskKeys", "KioskPhones"])]),
    "N2": dict(x=(-29.0, -15.0), storeys=5, brick="Red", alcove=-22.0, escape=None, band="TwinCarp",
               fronts=[[("Jewelry", "band")], [("Restaurant", "StallRoast")]],
               window=("FarShore", GROUND + 2 * STOREY + 0.95), awnings=[1], rails=[(9.0, ["KioskWatch", "KioskNeon"])]),
    "N3": dict(x=(-15.0, -1.0), storeys=5, brick="Buff", alcove=-8.0, escape=1, band="EightTreasure",
               fronts=[[("Restaurant", "band")], [("Jewelry", "KioskPhones")]], awnings=[0],
               rails=[(12.4, ["StallRoast", "KioskKeys"])]),
    "N4": dict(x=(-1.0, 13.0), storeys=6, brick="Red", alcove=5.0, escape=None, band="SpringPine",
               fronts=[[("Jewelry", "StallDry")], [("Grocery", "band")]], rails=[(1.4, ["StallTofu", "KioskWatch"])]),
    "N5": dict(x=(13.0, 26.0), storeys=5, brick="Painted", alcove=20.0, escape=None, band="LongLife",
               fronts=[[("Restaurant", "band")], [("Jewelry", "StallFruit")]],
               neon=("MahjongNeon", 1, GROUND + WIN_SILL + 0.55), awnings=[0], rails=[(9.6, ["StallVeg", "KioskPhones"])]),
    "N6": dict(x=(26.0, 44.0), storeys=7, brick="Red", alcove=31.0, escape=None, band="SunnyDay",
               fronts=[[("Narrow", "ForLease")], [("Wide", "band"), ("Jewelry", "KioskKeys")]],
               blade=("HarborStar", None, GROUND + 1.6), awnings=[1], rails=[(6.6, ["KioskWatch", "StallFish"])]),
}


def cm(w):
    return "%03d" % int(round(w * 100))


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


def ground(key, B, out):
    x0, x1 = B["x"]
    W = x1 - x0
    a0, a1 = B["alcove"] - 1.4 - x0, B["alcove"] + 1.4 - x0
    out.append(entry("SM_Facade_CT_Alcove_" + B["brick"], a0, 0.0, 0.0, x0, key, "alcove entrance"))
    shops = []
    for (s0, s1), fronts in zip(((0.0, a0), (a1, W)), B["fronts"]):
        widths = [FRONTS[f] for f, _sg in fronts]
        n = len(fronts)
        spare = (s1 - s0) - sum(widths) - (n - 1) * PIER_W
        assert spare >= 2 * PIER_MIN - 1e-6, (key, fronts, s1 - s0)
        end = spare / 2                                              # the two end piers take the rest, each built at its width
        s = s0
        out.append(entry("SM_Facade_CT_Pier_%s_%s" % (B["brick"], cm(end)), s, 0.0, 0.0, x0, key, "pier"))
        s += end
        for i, (f, sign) in enumerate(fronts):
            c = FRONTS[f]
            out.append(entry("SM_Facade_Shopfront_CT_" + f, s, 0.0, 0.0, x0, key, "shop front"))
            out.append(entry("SM_Facade_CT_Fascia_" + cm(c), s, 2.77, 0.0, x0, key, "fascia"))
            shops.append((f, s, c, sign))
            s += c
            if i < n - 1:
                out.append(entry("SM_Facade_Pier_" + B["brick"], s, 0.0, 0.0, x0, key, "pier"))
                s += PIER_W
        out.append(entry("SM_Facade_CT_Pier_%s_%s" % (B["brick"], cm(end)), s, 0.0, 0.0, x0, key, "pier"))
    for idx, (f, s, c, sign) in enumerate(shops):
        if sign == "band":
            F = names.FACES[B["band"]]
            out.append(entry(F["carrier"], s + c / 2 - F["w"] / 2, 2.76, -0.075 - 0.20, x0, key, "sign band", face=B["band"]))
        elif sign in ("ForLease", "ForRent"):
            out.append(entry(names.FACES[sign]["carrier"], s + c / 2 - names.FACES[sign]["w"] / 2, 1.35, -0.09, x0, key, "vacant sign",
                             face=sign))
        else:
            F = names.FACES[sign]
            z = 3.05 if F["kind"] == "kiosk" else 3.10
            out.append(entry(F["carrier"], s + c / 2 - F["w"] / 2, z, -0.12, x0, key, "shop sign", face=sign))
        if idx in B.get("awnings", []) and c >= 3.0:
            L = max(v for v in (3, 4, 6) if v <= c)
            out.append(entry("SM_Facade_CT_Awning_Box_%dm" % L, s + c / 2 - L / 2, 2.35, 0.0, x0, key, "awning"))
    return shops


def uppers(key, B, out):
    x0, x1 = B["x"]
    W, k = x1 - x0, B["brick"]
    n = int(W // BAY + 1e-6)
    p = (W - n * BAY) / 2
    rnd = rng_seq(key)
    esc = None if B["escape"] is None else p + B["escape"] * BAY + BAY / 2 - ESC_L / 2
    ups = B["storeys"] - 1
    for i in range(ups):
        z = GROUND + i * STOREY
        out.append(entry("SM_Facade_CT_Fill_%s_%s" % (k, cm(p)), 0.0, z, 0.0, x0, key, "fill"))
        out.append(entry("SM_Facade_CT_Fill_%s_%s" % (k, cm(p)), W - p, z, 0.0, x0, key, "fill"))
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
    out.append(entry("SM_Facade_CT_CorniceEnd_L_" + cm(p), 0.0, zr, 0.0, x0, key, "cornice"))
    out.append(entry("SM_Facade_CT_CorniceEnd_R_" + cm(p), W - p, zr, 0.0, x0, key, "cornice"))
    out.append(entry("SM_Facade_CT_ParapetFill_%s_%s" % (k, cm(p)), 0.0, zr, 0.0, x0, key, "parapet"))
    out.append(entry("SM_Facade_CT_ParapetFill_%s_%s" % (k, cm(p)), W - p, zr, 0.0, x0, key, "parapet"))
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
    for s, faces in B.get("rails", []):                               # stacked signs: the Chinatown read in English
        zr0 = GROUND + 0.35
        out.append(entry("SM_Facade_CT_StackedSignRail", s, zr0, 0.0, x0, key, "stacked sign rail"))
        for i, fk in enumerate(faces):
            F = names.FACES[fk]
            out.append(entry(F["carrier"], s + 0.45 - F["w"] / 2, zr0 + 0.25 + 1.05 * i, -0.65, x0, key, "stacked sign",
                             face=fk, rot=90.0))
    return n


def needed_widths():
    """The width-specific modules this table places: {"pier": {(brick, w)}, "fill": ..., "parapet": ..., "cornice": {w},
    "fascia": {w}} (built by _chinatown_front.m_ct_widths)."""
    out = assemble()
    need = {"pier": set(), "fill": set(), "parapet": set(), "cornice": set(), "fascia": set()}
    for e in out:
        m = e["mesh"]
        for tag, pre in (("pier", "SM_Facade_CT_Pier_"), ("fill", "SM_Facade_CT_Fill_"), ("parapet", "SM_Facade_CT_ParapetFill_")):
            if m.startswith(pre):
                k, w = m[len(pre):].rsplit("_", 1)
                need[tag].add((k, int(w) / 100.0))
        if m.startswith("SM_Facade_CT_CorniceEnd_"):
            need["cornice"].add(int(m.rsplit("_", 1)[1]) / 100.0)
        if m.startswith("SM_Facade_CT_Fascia_") and not m.endswith("_1m"):
            need["fascia"].add(int(m.rsplit("_", 1)[1]) / 100.0)
    return {k: sorted(v) for k, v in need.items()}


def assemble_north():
    out = []
    for key, B in ROW.items():
        ground(key, B, out)
        uppers(key, B, out)
    return out


_ASM = {}


def assemble_all():
    """The north row, then round 2 (_chinatown_streets): the other buildings, lane D's signs, the props and the structures."""
    if "all" not in _ASM:
        from assets import _chinatown_streets as st
        out = assemble_north()
        more, rep = st.assemble()
        _ASM["all"], _ASM["report"] = out + more, rep
    return list(_ASM["all"])


def assemble():
    return assemble_all()


def report():
    assemble_all()
    return _ASM["report"]


def needed_round2():
    from assets import _chinatown_streets as st
    return st.needed()


def _round2_buildings():
    from assets import _chinatown_streets as st
    return st.buildings()


def _round2_proxies():
    from assets import _chinatown_streets as st
    return [{"mesh": "SM_Facade_CT_Far_" + k, "building": k, "blender_m": v["pivot_blender_m"],
             "location_cm": [round(v["pivot_blender_m"][0] * 100, 2), round(-v["pivot_blender_m"][1] * 100, 2),
                             round(v["pivot_blender_m"][2] * 100, 2)], "yaw": 0.0, "lodSwitch_m": 30.0,
             "use": "the building's LOD1 / HLOD proxy: its faces' modules merged; drawn instead of them past lodSwitch_m"}
            for k, v in st.buildings().items()]


def write_placements(path):
    out = assemble()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = {"about": "Canal Street, north row N1..N6 (chinatown.md 4.10), from assets/_chinatown_place.py: the Block's facade kit and "
                    "the Canal kit. Unreal centimetres (X east, Y south, Z up), yaw degrees about Z (0 = module as imported), "
                    "optional scale along the module's run (X); blender_m / rot_z_deg are the same in Blender metres. Signs carry "
                    "their face key and atlas cell (uv v-up). See the module docstring for what waits on lane D's colliders.",
           "buildings": dict({k: {"x_web": list(B["x"]), "storeys": B["storeys"], "brick": B["brick"], "fronts": B["fronts"], "band": B["band"]}
                              for k, B in ROW.items()}, **_round2_buildings()),
           "notPlaced": report()["notPlaced"], "unmappedProps": report()["unmapped"],
           "propFit": report()["fit"],
           "count": len(out), "instances": out,
           "farProxies": [{"mesh": "SM_Facade_CT_Far_" + k, "building": k, "blender_m": [B["x"][0], LINE_Y, KERB_H],
                           "location_cm": [round(B["x"][0] * 100, 2), round(-LINE_Y * 100, 2), round(KERB_H * 100, 2)], "yaw": 0.0,
                           "lodSwitch_m": 30.0,
                           "use": "the building's LOD1 / HLOD proxy: drawn instead of its modules past lodSwitch_m from the camera"}
                          for k, B in ROW.items()] + _round2_proxies()}
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    return len(out)


if __name__ == "__main__":
    p = os.path.join(HERE, "..", "..", "out", "placements", "placements_chinatown.json")
    print(write_placements(os.path.normpath(p)), "instances")
