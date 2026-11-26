"""Canal Street placements, round 2 (MAPS.md lane A-CT): every building face the player sees besides the north row, the
signs lane D placed (tools/levels/data/level_chinatown.json `signage`), the props on lane D's prop colliders
(`propPlacements`) and the fitted structures (_chinatown_struct). Pure arithmetic, no Blender: _chinatown_place.assemble()
adds these instances to the north row's.

Faces. A face is a wall plane of a building with its outward normal (web '+x', '-x', '+z', '-z'), the point along the
plane where it starts and its length; modules run along it the way the north row's run east (a module's +X is the face's
run, its outer face looks out). Where two faces meet at a corner the later one starts (or ends) 0.30 m in, so the first
one's end cap is the corner and no two faces overlap. Ground storeys are explicit segments (piers at their own widths,
shop fronts with their fascia, the alcoves, back-wall bays, openings with a head panel over them), so a front lines up
with lane D's doors and with its sign; upper storeys are bays on a 3.1 m grid with fills at the ends, built at their
widths: no instance is scaled anywhere (the review's rule).

Signs. Every word comes from lane D's signage list (each id names its face key in _chinatown_names). A sign over a shop
front sits on the front's fascia as the north row's do (bands 2.76 m, kiosks 3.05 m over the sidewalk); elsewhere at lane
D's height. Where the art had to move one, the instance says so (`deviation`) and the list is in DEVIATIONS. A front with
no sign of lane D's gets a generic lightbox or a stall board (words that need no name search), so every front has one.

Coordinates as _chinatown_place: Blender metres (web x, -z, y), Unreal cm = (x, -y, z) x 100 of Blender, yaw = -rot_z.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from assets import _chinatown_level as lv  # noqa: E402
from assets import _chinatown_names as names  # noqa: E402

BAY, STOREY, GROUND, PIER_W, WIN_SILL = 3.1, 3.1, 3.65, 0.32, 0.60
ESC_L = 2.99
BLOCK_BRICKS = ("Red", "Brown", "Buff", "Painted")          # the Block's kit has window bays, piers and parapets in these
OUT = {"+x": (1.0, 0.0), "-x": (-1.0, 0.0), "+z": (0.0, -1.0), "-z": (0.0, 1.0)}     # web outward -> Blender normal
GROUND_KINDS = ("GroundWall", "GroundDoor", "GroundWindow")


def cm(w):
    return "%03d" % int(round(w * 100))


class Face:
    def __init__(self, building, key, plane, outward, start, length, base):
        self.building, self.key, self.plane, self.outward, self.start, self.L, self.base = \
            building, key, plane, outward, start, length, base
        self.n = OUT[outward]
        self.u = (-self.n[1], self.n[0])
        if outward in ("+z", "-z"):
            self.o = (start, -plane)
        else:
            self.o = (plane, -start)
        self.rot = math.degrees(math.atan2(self.u[1], self.u[0]))

    def at(self, s, d=0.0):
        """Blender (x, y) s metres along the run, d metres behind the wall plane (negative: in front)."""
        return (self.o[0] + self.u[0] * s - self.n[0] * d, self.o[1] + self.u[1] * s - self.n[1] * d)

    def along(self, bx_, by_):
        """s and the distance in front of the plane of a Blender point."""
        dx, dy = bx_ - self.o[0], by_ - self.o[1]
        return dx * self.u[0] + dy * self.u[1], dx * self.n[0] + dy * self.n[1]


def mk(mesh, x, y, z, rot, building, role, face=None, **extra):
    from assets import _chinatown_place as place
    e = {"mesh": mesh, "building": building, "role": role, "blender_m": [round(x, 4), round(y, 4), round(z, 4)],
         "rot_z_deg": round(rot % 360.0, 4),
         "location_cm": [round(x * 100, 2), round(-y * 100, 2), round(z * 100, 2)], "yaw": round(-rot % 360.0, 3)}
    if face:
        e["face"] = face
        c = place.cells().get(face)
        if c:
            e["atlas"], e["atlas_uv"] = c["atlas"], c["uv"]
    e.update(extra)
    return e


def fe(F, mesh, s, z, d, role, face=None, rot=0.0, **extra):
    x, y = F.at(s, d)
    return mk(mesh, x, y, F.base + z, F.rot + rot, F.building, role, face, faceKey=F.key, **extra)


# ================================================================================================= the faces

# (building, key, plane, outward, start, length, base, storeys, brick, kind, ground segments, options)
# Ground segments: ("pier", w), ("front", kind, generic sign or None [, "awning"]), ("alcove",), ("res",), (GroundWall |
# GroundDoor | GroundWindow,), ("gap", w [, z0, h]): an opening with an optional head panel w x h at z0.
# Options: escapes (bay indices), rows_from (first upper row drawn), blank_rows, top ("front": cornice and parapet; "back":
# a party-wall cap), ground (False: no ground storey, the structure or the market owns it).
FACES = [
    # W1, the six-storey tenement west of Lantern Alley: the shut hardware store on Canal, the alley wall with three escapes
    ("W1", "W1.canal", -14.0, "-z", -30.0, 14.0, 0.15, 6, "Red", "front",
     [("pier", 0.30), ("res",), ("pier", 0.90), ("front", "Shut", None), ("pier", 0.32), ("front", "Narrow", "KioskPhones"),
      ("pier", 1.28)], {}),
    ("W1", "W1.alleyA", -30.0, "+x", 14.0, 27.7, 0.0, 6, "Common", "back",
     [("pier", 1.45), ("GroundDoor",), ("GroundWall",), ("GroundWindow",), ("GroundDoor",), ("GroundWall",), ("GroundDoor",),
      ("GroundWindow",), ("GroundWall",), ("pier", 1.45)], {"escapes": (1, 4, 6), "top": "back"}),
    # W3, MOON GATE BAKERY: the Canal front, the Mott side of the front shop, the walls over the kitchen roof and the market roof
    ("W3", "W3.canal", -14.0, "-z", 8.0, 8.0, 0.15, 5, "Buff", "front",
     [("pier", 0.40), ("front", "Bakery", None), ("pier", 0.40)], {}),
    ("W3", "W3.mott", 8.0, "+x", -3.0, 10.7, 0.15, 5, "Buff", "front",
     [("pier", 0.70), ("GroundWindow",), ("GroundWall",), ("GroundWindow",), ("pier", 0.70)], {}),
    ("W3", "W3.rear", -3.0, "+z", 0.0, 8.0, 0.15, 5, "Buff", "back", [], {"ground": False, "blank_rows": (0,), "top": "back"}),
    ("W3", "W3.west", 0.0, "-x", -13.7, 10.4, 0.15, 5, "Common", "back", [], {"ground": False, "blank_rows": (0,), "top": "back"}),
    # the backs on Lantern Alley B
    ("S1", "S1.alleyB", 14.0, "-z", -14.0, 16.0, 0.0, 5, "Common", "back",
     [("pier", 0.25), ("GroundWall",), ("GroundDoor",), ("GroundWindow",), ("GroundDoor",), ("GroundWall",), ("pier", 0.25)],
     {"escapes": (1, 3), "top": "back"}),
    ("S2", "S2.alleyB", 14.0, "-z", 0.0, 14.0, 0.0, 5, "Painted", "back",
     [("pier", 0.80), ("GroundWindow",), ("GroundDoor",), ("GroundWall",), ("GroundDoor",), ("pier", 0.80)],
     {"escapes": (2,), "top": "back"}),
    ("S3", "S3.alleyB", 14.0, "-z", 7.7, 7.7, 0.0, 6, "Brown", "back",
     [("pier", 0.75), ("GroundWall",), ("GroundWindow",), ("pier", 0.75)], {"top": "back"}),
    # S3 on Mott: QUICK WIRE, the coach office's door (its band on the second storey), GOOD WISHES GROCERY
    ("S3", "S3.mott", 8.0, "+x", 32.0, 18.0, 0.15, 6, "Brown", "front",
     [("pier", 1.50), ("front", "Jewelry", None), ("pier", 1.30), ("front", "Narrow", None), ("pier", 1.80),
      ("front", "Grocery", None), ("pier", 1.00)], {"escapes": (4,)}),
    # E1a over the arcade, E1b east of it
    ("E1a", "E1a.canalArcade", -14.0, "-z", 33.6, 4.2, 0.15, 5, "Red", "front", [("gap", 4.2, 4.05, 2.70)], {"rows_from": 1}),
    ("E1a", "E1a.canal", -14.0, "-z", 29.4, 11.4, 0.15, 5, "Red", "front",
     [("pier", 0.40), ("front", "Wide", None), ("pier", 0.32), ("front", "Jewelry", None), ("pier", 0.68)], {}),
    ("E1a", "E1a.mott", 18.0, "-x", -13.7, 15.7, 0.15, 5, "Red", "front",
     [("pier", 3.20), ("front", "Restaurant", None, "awning"), ("pier", 0.32), ("front", "Grocery", "StallFruit"), ("pier", 1.18)],
     {"escapes": (0,), "n": 4}),
    ("E1a", "E1a.square", 2.0, "+z", 18.3, 11.1, 0.15, 5, "Red", "front",
     [("pier", 3.20), ("front", "Jewelry", None), ("pier", 0.32), ("front", "Narrow", "KioskKeys"), ("pier", 1.18)], {}),
    ("E1a", "E1a.squareArcade", 2.0, "+z", 29.4, 4.2, 0.15, 5, "Red", "front", [("gap", 4.2, 4.05, 2.70)], {"rows_from": 1}),
    ("E1b", "E1b.canal", -14.0, "-z", 44.0, 10.4, 0.15, 6, "Buff", "front",
     [("pier", 2.00), ("front", "Wide", None), ("pier", 2.40)], {}),
    ("E1b", "E1b.square", 2.0, "+z", 33.6, 10.4, 0.15, 6, "Buff", "front",
     [("pier", 0.60), ("front", "Restaurant", "StallRoast"), ("pier", 0.32), ("front", "Narrow", "KioskWatch"), ("pier", 2.08)], {}),
    # the arcade's side walls: kiosks behind glass, the workshop door (BIG LIGHT SIGNS) with a head over it
    ("Arcade", "Arcade.west", 29.4, "+x", 2.0, 16.0, 0.15, 1, "Red", "front",
     [("pier", 3.80), ("front", "Narrow", None), ("pier", 0.60), ("front", "Narrow", None), ("pier", 2.60), ("front", "Narrow", None),
      ("pier", 1.80)], {"ground_only": True}),
    ("Arcade", "Arcade.east", 33.6, "-x", -14.0, 16.0, 0.15, 1, "Buff", "front",
     [("pier", 0.30), ("front", "Narrow", None), ("pier", 3.30), ("gap", 2.0, 2.25, 1.40), ("pier", 8.00)], {"ground_only": True}),
]

# where the art places a sign of lane D's differently (the reason is in the instance and in chinatown.md 13.6)
DEVIATIONS = {
    "s3.coach": dict(y=6.90, why="SEVEN STARS COACH's 8 m band overlaps both its neighbours' bands along S3's 18 m Mott face "
                                 "(lane D's centres 18, 24, 28.5): it is mounted between the second- and third-storey windows "
                                 "over the coach office's door, the ticket office upstairs"),
    "poster.opera": dict(x=-29.99, why="lane D's point (x -27.95, facing +x) is in the middle of Lantern Alley A: pasted on W1's "
                                       "alley wall at the same z and height"),
    "m.letters": dict(why="the frame stands on lane D's four legs (x -22 .. -2): the 12 m letters centre on the legs (x -12), "
                          "1 m east of lane D's point"),
    "arcade.kiosk.3": dict(x=33.58, why="lane D's point (x 32.55) is 1.05 m out in the arcade's aisle: the board is mounted on the "
                                         "east wall (x 33.6) at the same z and height, over the narrow front that has no other sign"),
    "lanterns": dict(y=6.25, why="lane D's point (y 4.3) is in front of the banquet band (3.95 .. 4.85): the cable is fixed at "
                                 "6.25 so the lanterns hang clear above the band, over the doors"),
}
NORTH_ROW = ("N1", "N2", "N3", "N4", "N5", "N6")
SKIP_IDS = ("vacant.0", "vacant.2")          # papers on north-row windows: the north row has its own one vacancy paper


def faces():
    out = []
    for (bld, key, plane, ow, start, L, base, storeys, brick, kind, segs, opt) in FACES:
        out.append((Face(bld, key, plane, ow, start, L, base), storeys, brick, kind, segs, opt))
    return out


FRONTS = {"Wide": 6.0, "Narrow": 2.4, "Restaurant": 5.0, "Jewelry": 4.0, "Grocery": 6.0, "Shut": 6.0, "Bakery": 7.2}


def pier_mesh(brick, w):
    if abs(w - PIER_W) < 1e-6 and brick in BLOCK_BRICKS:
        return "SM_Facade_Pier_" + brick
    return "SM_Facade_CT_Pier_%s_%s" % (brick, cm(w))


def ground(F, brick, segs, out):
    s, shops = 0.0, []
    for seg in segs:
        k = seg[0]
        if k == "pier":
            parts = max(1, int(math.ceil(seg[1] / 4.2 - 1e-9)))              # a wide wall is made of piers of at most 4.2 m
            for _i in range(parts):
                out.append(fe(F, pier_mesh(brick, seg[1] / parts), s, 0.0, 0.0, "pier"))
                s += seg[1] / parts
        elif k == "front":
            f, sign = seg[1], seg[2]
            c = FRONTS[f]
            out.append(fe(F, "SM_Facade_Shopfront_CT_" + f, s, 0.0, 0.0, "shop front", front=f, span=[round(s, 3), round(s + c, 3)]))
            out.append(fe(F, "SM_Facade_CT_Fascia_" + cm(c), s, 2.77, 0.0, "fascia"))
            if len(seg) > 3 and seg[3] == "awning" and c >= 3.0:
                Lw = max(v for v in (3, 4, 6) if v <= c)
                out.append(fe(F, "SM_Facade_CT_Awning_Box_%dm" % Lw, s + c / 2 - Lw / 2, 2.35, 0.0, "awning"))
            shops.append((f, s, c, sign))
            s += c
        elif k == "alcove":
            out.append(fe(F, "SM_Facade_CT_Alcove_" + brick, s, 0.0, 0.0, "alcove"))
            s += 2.8
        elif k == "res":
            out.append(fe(F, "SM_Facade_ResEntry_Red", s, 0.0, 0.0, "residents' entrance"))
            s += 2.8
        elif k in GROUND_KINDS:
            out.append(fe(F, "SM_Facade_CT_%s_%s" % (k, brick), s, 0.0, 0.0, "ground bay"))
            s += BAY
        elif k == "gap":
            if len(seg) > 2:
                out.append(fe(F, "SM_Facade_CT_Head_%s_%sx%s" % (brick, cm(seg[1]), cm(seg[3])), s, seg[2], 0.0, "head"))
            s += seg[1]
        else:
            raise ValueError(seg)
    assert abs(s - F.L) < 1e-6, (F.key, s, F.L)
    for f, s0, c, sign in shops:                          # generic signs where lane D has none
        if sign:
            Fc = names.FACES[sign]
            z = 3.05 if Fc["kind"] == "kiosk" else 3.10
            out.append(fe(F, Fc["carrier"], s0 + c / 2 - Fc["w"] / 2, z, -0.12, "shop sign", face=sign, generic=True))
    return shops


def uppers(F, storeys, brick, kind, opt, out):
    from assets import _chinatown_place as place
    n = opt.get("n", int(F.L // BAY + 1e-6))                  # "n": fewer bays than fit, when the end fills would be under 0.30 m
    p = (F.L - n * BAY) / 2
    rnd = place.rng_seq(F.key)
    ups = storeys - 1
    rows_from, blank_rows = opt.get("rows_from", 0), opt.get("blank_rows", ())
    escs = [p + e * BAY + BAY / 2 - ESC_L / 2 for e in opt.get("escapes", ())]
    win = ("SM_Facade_BayWindow_" if brick in BLOCK_BRICKS else "SM_Facade_CT_BayWindow_") + brick
    blank = "SM_Facade_BayBlank_" + brick
    for i in range(rows_from, ups):
        z = GROUND + i * STOREY
        if p > 0.005:
            out.append(fe(F, "SM_Facade_CT_Fill_%s_%s" % (brick, cm(p)), 0.0, z, 0.0, "fill"))
            out.append(fe(F, "SM_Facade_CT_Fill_%s_%s" % (brick, cm(p)), F.L - p, z, 0.0, "fill"))
        for j in range(n):
            u = rnd()
            xw = p + j * BAY + BAY / 2
            behind = any(e - 0.3 < xw < e + ESC_L + 0.3 for e in escs)
            window = i not in blank_rows and (kind == "front" or u < 0.80)
            out.append(fe(F, win if window else blank, p + j * BAY, z, 0.0, "bay"))
            if not window:
                continue
            v = rnd()
            if i == 0 and kind == "front" and not behind and v < 0.40:
                out.append(fe(F, "SM_Facade_CT_WindowGrille", xw, z + WIN_SILL, 0.0, "grille"))
            elif 0.40 <= v < 0.58 and not behind:
                out.append(fe(F, "SM_Facade_AirConditioner", xw, z + WIN_SILL, 0.0, "air conditioner"))
            elif v < 0.92:
                out.append(fe(F, "SM_Facade_WindowBlind", xw, z + WIN_SILL, 0.0, "blind"))
    zr = GROUND + ups * STOREY
    if opt.get("top", "front") == "front" and brick in BLOCK_BRICKS:
        if p > 0.005:
            out.append(fe(F, "SM_Facade_CT_CorniceEnd_L_" + cm(p), 0.0, zr, 0.0, "cornice"))
            out.append(fe(F, "SM_Facade_CT_CorniceEnd_R_" + cm(p), F.L - p, zr, 0.0, "cornice"))
        for j in range(n):
            out.append(fe(F, "SM_Facade_Cornice_310", p + j * BAY, zr, 0.0, "cornice"))
            out.append(fe(F, "SM_Facade_Parapet_310_" + brick, p + j * BAY, zr, 0.0, "parapet"))
    else:
        for j in range(n):
            out.append(fe(F, "SM_Facade_PartyWallCap_310", p + j * BAY, zr, 0.0, "parapet"))
    if p > 0.005:
        out.append(fe(F, "SM_Facade_CT_ParapetFill_%s_%s" % (brick, cm(p)), 0.0, zr, 0.0, "parapet"))
        out.append(fe(F, "SM_Facade_CT_ParapetFill_%s_%s" % (brick, cm(p)), F.L - p, zr, 0.0, "parapet"))
    for e in escs:
        for i in range(max(rows_from, 0), ups):
            z = GROUND + i * STOREY + 0.25
            out.append(fe(F, "SM_Facade_FireEscape_Balcony", e, z, 0.0, "fire escape"))
            for bxs in (0.10, ESC_L / 2, ESC_L - 0.10):
                out.append(fe(F, "SM_Facade_FireEscape_Bracket", e + bxs, z, 0.0, "fire escape"))
            if i == 0:
                out.append(fe(F, "SM_Facade_FireEscape_Ladder", e, z, 0.0, "fire escape"))
            if i < ups - 1:
                out.append(fe(F, "SM_Facade_FireEscape_Stair", e, z, 0.0, "fire escape"))
    return n


def assemble_faces(out):
    shops = {}
    for F, storeys, brick, kind, segs, opt in faces():
        if opt.get("ground", True):
            shops[F.key] = (F, ground(F, brick, segs, out))
        if not opt.get("ground_only"):
            uppers(F, storeys, brick, kind, opt, out)
    return shops


# ================================================================================================= lane D's signs

def _flat_rot(nb):
    return math.degrees(math.atan2(nb[0], -nb[1]))


def _planes(shops):
    """Wall planes signs can sit on: every face above, plus the structures' faces (market fascia, E2, cold room, workshop)."""
    P = [(F.outward, F.plane, F, 0.0) for F, _s in shops.values()]
    P += [(F.outward, F.plane, F, 0.0) for F, _st, _b, _k, _sg, opt in faces() if not opt.get("ground", True)]
    extra = [("M", "-z", -14.0, -30.0, 0.05), ("E2", "-z", 18.0, 44.0, 0.0), ("E2", "-x", 18.0, 18.0, 0.0),
             ("M", "-z", 1.5, -18.0, 0.0), ("E1b", "-x", 37.6, -14.0, 0.0), ("W1", "+x", -30.0, 14.0, 0.0),
             ("S3", "-z", 14.0, 7.7, 0.0), ("M", "-x", -26.0, -14.0, 0.0)]
    for bld, ow, plane, start, off in extra:
        P.append((ow, plane, Face(bld, bld + ".plane", plane, ow, start, 60.0, 0.0), off))
    return P


def _ow_of(n):
    for k, v in OUT.items():
        if abs(v[0] - n[0]) < 1e-6 and abs(v[1] - n[1]) < 1e-6:
            return k
    return None


def _coord(ow, x, z):
    return x if ow in ("+x", "-x") else z


def data_signs(shops, out, report):
    from assets import _chinatown_front_pure as fp
    planes = _planes(shops)
    for sg in lv.level()["signage"]["placements"]:
        sid, kind, fk = sg["id"], sg["kind"], sg.get("face")
        if sg.get("building") in NORTH_ROW or sid in SKIP_IDS:
            continue
        w = sg["web"]
        p = dict(w["pos"])
        dev = DEVIATIONS.get(sid)
        if dev:
            p.update({k: v for k, v in dev.items() if k in ("x", "y", "z")})
        nb = (w["normal"]["x"], -w["normal"]["z"])
        ww, hh = w["width"], w["height"]
        extra = {"dataSign": sid}
        if dev:
            extra["deviation"] = dev["why"]
        bld = sg.get("building") or "street"
        if kind in ("decal", "graffiti", "exitbox"):
            report["notPlaced"].append((sid, kind, "decals are not built yet" if kind != "exitbox" else
                                        "drawn in SM_Struct_CT_MarketHall (the green exit box)"))
            continue
        carrier = sg.get("carrier")
        if kind == "letters":
            x_e, _xs, yc = fp.rooftop_legs()
            out.append(mk("SM_Sign_CT_RooftopFrame", x_e, yc + 0.21, 5.70, 180.0, "M", "rooftop letters", face=None, **extra))
            continue
        if kind == "lanterns":
            L0 = 14.0
            x0, y0, z0 = p["x"] - L0 / 2, -p["z"], p["y"]
            out.append(mk("SM_Prop_CT_LanternString_14m", x0, y0, z0, 0.0, bld, "lantern string", **extra))
            for hx, _hy, hz in fp.lantern_hooks():
                out.append(mk("SM_Prop_CT_Lantern", x0 + hx, y0, z0 + hz, 0.0, bld, "lantern", dataSign=sid))
            continue
        if kind == "street":
            out.append(mk(carrier, p["x"], -p["z"], p["y"], _flat_rot(nb), bld, "street sign", face=fk, **extra))
            continue
        if kind == "placard":
            rot = _flat_rot(nb)
            u = (math.cos(math.radians(rot)), math.sin(math.radians(rot)))
            out.append(mk(carrier, p["x"] - u[0] * ww / 2, -p["z"] - u[1] * ww / 2, p["y"] - 0.17, rot, bld, "placard", face=fk, **extra))
            continue
        if kind == "blade":
            best = None
            for ow, plane, F, off in planes:
                if ow in ("+x", "-x") == (abs(nb[0]) > 0.5):          # the wall runs along the blade's faces' normal
                    continue
                d = abs(_coord(ow, p["x"], p["z"]) - plane)
                if d < 1.2 and (best is None or d < best[0]):
                    best = (d, ow, plane, F, off)
            if best is None:
                report["notPlaced"].append((sid, kind, "no wall within 1.2 m"))
                continue
            _d, ow, plane, F, off = best
            o = OUT[ow]
            bxp = (p["x"], -plane) if ow in ("+z", "-z") else (plane, -p["z"])
            bxp = (bxp[0] + o[0] * off, bxp[1] + o[1] * off)
            out.append(mk(carrier, bxp[0], bxp[1], p["y"] - hh / 2, math.degrees(math.atan2(o[0], -o[1])), bld, "blade", face=fk,
                          **extra))
            continue
        ow = _ow_of(nb)
        hang = kind == "board" and bld == "M" and carrier == "SM_Sign_CT_StallBoard"
        rot = _flat_rot(nb)
        u = (math.cos(math.radians(rot)), math.sin(math.radians(rot)))
        if hang:
            out.append(mk(carrier, p["x"] - u[0] * ww / 2, -p["z"] - u[1] * ww / 2, p["y"] - hh / 2, rot, bld, "stall board",
                          face=fk, **extra))
            continue
        best = None
        for ow2, plane, F, off in planes:
            if ow2 != ow:
                continue
            d = abs(_coord(ow, p["x"], p["z"]) - plane)
            if d < 0.7 and (best is None or d < best[0]):
                best = (d, plane, F, off)
        if best is None:
            report["notPlaced"].append((sid, kind, "no wall plane within 0.7 m facing %s" % ow))
            continue
        _d, plane, F, off = best
        s_c, _out = F.along(p["x"], -p["z"])
        over = None
        if F.key in shops:
            for f, s0, c, _sign in shops[F.key][1]:
                if s0 - 0.6 <= s_c <= s0 + c + 0.6 and p["y"] - F.base < 5.5:
                    over = (f, s0, c)
        depth = {"band": 0.20, "kiosk": 0.12, "board": 0.02, "poster": 0.002, "neon": 0.02, "arch": 0.22}[kind]
        if over and kind in ("band", "kiosk", "board") and sid not in DEVIATIONS:
            zb = F.base + {"band": 2.76, "kiosk": 3.05, "board": 3.10}[kind]
            d = {"band": 0.275, "kiosk": 0.12, "board": 0.12}[kind]
            if abs(zb - (p["y"] - hh / 2)) > 0.25:
                extra["heightFromData_m"] = round(zb - (p["y"] - hh / 2), 2)
        else:
            zb = p["y"] - hh / 2
            d = depth + (0.0 if kind in ("poster", "neon") else 0.01) + off
        x, y = F.at(s_c - ww / 2, -d)
        role = {"band": "sign band", "kiosk": "shop sign", "board": "board", "poster": "poster", "neon": "neon",
                "arch": "arch sign"}[kind]
        if kind == "neon":                                   # exposed neon is its own mesh: no atlas cell
            extra["neon"] = fk
            fk = None
        out.append(mk(carrier, x, y, zb, rot, bld, role, face=fk, faceKey=F.key, **extra))


# ================================================================================================= props on lane D's colliders

# catalogue name -> [(mesh, length along its X, width along its Y)] (tiled along the collider's long side), options
PROPS = {
    "stall_counter": ([("SM_Prop_CT_StallCounter_2m", 2.04, 1.876)], {}),
    "fish_counter": ([("SM_Prop_CT_FishCounter", 2.0, 1.03)], {}),
    "pallet_stack": ([("SM_Furn_PalletStack_A", 1.23, 1.03)], {}),
    "pallet_single": ([("SM_Furn_Pallet", 1.2, 1.0)], {}),
    "skylight": ([("SM_Prop_CT_Skylight", 3.0, 2.0)], {}),
    "condenser": ([("SM_Prop_CT_Condenser", 1.1, 0.9)], {}),
    "roof_ac": ([("SM_Prop_CT_Condenser", 1.1, 0.9)], {}),
    "dumpster": ([("SM_Furn_Dumpster", 1.9, 1.17)], {}),
    "crate_stack": ([("SM_Prop_CardboardBoxes", 0.96, 0.81)], {}),
    "produce_crates": ([("SM_Prop_CardboardBoxes", 0.96, 0.81)], {}),
    "trash_can": ([("SM_Prop_TrashCan_Metal", 0.78, 0.56)], {}),
    "traffic_cone": ([("SM_Furn_TrafficCone", 0.36, 0.36)], {}),
    "traffic_drum": ([("SM_Furn_TrafficBarrel", 0.6, 0.6)], {}),
    "newspaper_box": ([("SM_Furn_NewspaperBox", 0.48, 0.46)], {}),
    "mailbox": ([("SM_Furn_Mailbox", 0.53, 0.52)], {}),
    "street_lamp": ([("SM_Furn_StreetLamp", 0.34, 0.34)], {"lamp": True}),
    "vendor_table": ([("SM_Prop_CT_VendorTable", 1.84, 0.81)], {"goods": True}),
    "garment_rail": ([("SM_Prop_CT_ClothingRail", 1.54, 0.5)], {}),
    "cardboard_bale": ([("SM_Prop_CT_CardboardBale", 1.1, 0.81)], {}),
    "fish_boxes": ([("SM_Prop_CT_StyrofoamBoxes", 0.68, 0.48)], {}),
    "styrofoam_stack": ([("SM_Prop_CT_StyrofoamBoxes", 0.68, 0.48)], {}),
    "hand_truck": ([("SM_Prop_CT_HandTruck", 0.63, 0.55)], {}),
    "drygoods_bins": ([("SM_Prop_CT_DryGoods", 1.83, 0.52)], {}),
    "fruit_crates": ([("SM_Prop_CT_Produce_Citrus", 1.4, 1.02)], {}),
    "ebike": ([("SM_Prop_CT_EBike", 1.7, 0.6)], {}),
    "card_table": ([("SM_Prop_CT_CardTable", 0.86, 0.86)], {"stools": True}),
    "park_bench": ([("SM_Prop_CT_ParkBench", 1.8, 0.54)], {}),
    "basketball_hoop": ([("SM_Prop_CT_BasketballHoop", 0.3, 0.3)], {"overhead": True, "rot": 180.0}),
    "jersey_barrier": ([("SM_Furn_JerseyBarrier", 3.0, 0.61)], {}),
    "milk_crates": ([("SM_Furn_MilkCrate", 0.33, 0.33)], {"crates": True}),
    "sign_pole": ([("SM_Furn_SignPost", 0.08, 0.08)], {"overhead": True}),
    "muni_meter": ([("SM_Furn_ParkingMeter", 0.19, 0.16)], {}),
}
# no mesh yet, or the only mesh is far from the collider's size, or too heavy without a LOD (listed in the report)
UNMAPPED_WHY = {
    "trash_bags": "the Block's bag piles are 1.28 x 0.97 m against 0.6 x 0.8 colliders: a smaller pile is needed",
    "hydrant": "SM_Prop_Hydrant is 46k triangles: needs its LOD before it is placed 4 times in a worst view",
    "fire_hydrant": "as hydrant", "planter": "SM_Street_Planter is 42k triangles: needs a LOD",
    "food_cart": "SM_Street_FoodCart is 2.4 x 1.3 m against 1.4 x 0.9: the dumpling cart is not built",
    "hotpot_cart": "not built", "fruit_stand": "SM_Prop_CT_FruitStand is 2.4 x 1.2 m against a 0.8 x 1.0 collider",
    "barricade": "SM_Furn_Barricade is 2.4 m against a 1.2 m collider",
}
GOODS = ["SM_Prop_CT_Goods_Caps", "SM_Prop_CT_Goods_TShirts", "SM_Prop_CT_Goods_Shades", "SM_Prop_CT_Goods_Discs"]
# market dressing on the stall rows (rows R1..R4 from lane D's stall_counter items): goods on the counters, a tarp and two
# bulbs over each front run
ROW_GOODS = {"R1": "SM_Prop_CT_Produce_Citrus", "R2": "SM_Prop_CT_Produce_Greens", "R3": "SM_Prop_CT_DryGoods",
             "R4": "SM_Prop_CT_StyrofoamBoxes"}


def _union(cols):
    bxs = [lv.cbox(i) for i in cols]
    lo = [min(b[0][k] for b in bxs) for k in range(3)]
    hi = [max(b[1][k] for b in bxs) for k in range(3)]
    return lo, hi


def _tile(L, cands):
    """The candidate and count that cover length L best (least uncovered plus overhang)."""
    best = None
    for mesh, ln, wd in cands:
        for n in range(1, 8):
            err = abs(L - n * ln)
            if best is None or err < best[0] - 1e-9:
                best = (err, mesh, ln, wd, n)
    return best[1:]


def props(out, report):
    for p in lv.level()["propPlacements"]["items"]:
        name = p["name"]
        if name not in PROPS:
            report["unmapped"][name] = report["unmapped"].get(name, 0) + 1
            continue
        cands, opt = PROPS[name]
        cols = p.get("colliders") or []
        if not cols:
            continue
        lo, hi = _union(cols)
        ex, ey = hi[0] - lo[0], hi[1] - lo[1]
        cx, cy, z0 = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]
        along_x = ex >= ey
        L, Wd = (ex, ey) if along_x else (ey, ex)
        mesh, ln, wd, n = _tile(L, cands) if not opt.get("lamp") and not opt.get("overhead") else (cands[0][0], cands[0][1], cands[0][2], 1)
        rot = 0.0 if along_x else 90.0
        if opt.get("rot") is not None:
            rot = opt["rot"]
        if opt.get("lamp"):
            rot = _lamp_rot(cx, cy)
        over_l = max(0.0, (n * ln - L) / 2)
        over_w = max(0.0, (wd - Wd) / 2)
        unc = max(0.0, (L - n * ln) / 2)
        if not opt.get("overhead") and not opt.get("lamp"):
            report["fit"].append({"prop": name, "index": p["index"], "mesh": mesh, "n": n, "overhang_m": round(max(over_l, over_w), 3),
                                  "uncovered_end_m": round(unc, 3)})
        group = p.get("group") or "level"
        for i in range(n):
            t = (i - (n - 1) / 2) * ln
            x, y = (cx + t, cy) if along_x else (cx, cy + t)
            if opt.get("crates"):
                for dx, dy, dz in ((-0.17, 0.0, 0.0), (0.17, 0.0, 0.0), (-0.17, 0.0, 0.28), (0.17, 0.0, 0.28)):
                    out.append(mk(mesh, x + dx, y + dy, z0 + dz, rot, group, "prop", prop=name, propIndex=p["index"]))
                continue
            out.append(mk(mesh, x, y, z0, rot, group, "prop", prop=name, propIndex=p["index"]))
            if opt.get("goods"):
                g = "SM_Prop_CT_Goods_Bags" if p.get("goods") == "rack" else GOODS[p["index"] % len(GOODS)]
                out.append(mk(g, x, y, z0 + 0.753, rot, group, "vendor goods", prop=name, propIndex=p["index"]))
            if opt.get("stools"):
                for dx, dy in ((0.75, 0.0), (-0.75, 0.0), (0.0, 0.75)):
                    out.append(mk("SM_Prop_CT_Stool", x + dx, y + dy, z0, 0.0, group, "stool", prop=name, propIndex=p["index"]))
        if name == "stall_counter" and p.get("row") in ROW_GOODS:
            g = ROW_GOODS[p["row"]]
            k = 2 if p.get("run") == "front" else 1
            for j in range(k):
                t = (j - (k - 1) / 2) * 2.4
                out.append(mk(g, cx, cy + t, z0 + 0.95, 90.0, "M", "stall goods", prop=name, propIndex=p["index"]))
            if p.get("run") == "front":
                out.append(mk("SM_Prop_CT_Tarp", cx, cy, 3.25, 90.0, "M", "stall tarp", prop=name, propIndex=p["index"]))
                for t in (-1.6, 1.6):
                    out.append(mk("SM_Prop_CT_PendantBulb", cx, cy + t, 4.85, 0.0, "M", "pendant", prop=name, propIndex=p["index"]))
        if name == "fish_counter":
            out.append(mk("SM_Prop_CT_FishTank", cx - 0.1, lo[1] + 0.35, z0, 90.0, "M", "fish tank", prop=name, propIndex=p["index"]))
            out.append(mk("SM_Prop_CT_HangingScale", cx - 0.1, cy, 1.25, 0.0, "M", "scale", prop=name, propIndex=p["index"]))


def _lamp_rot(x, y):
    """The street lamp's arm (local -Y) over the roadway: Canal's south sidewalk lamps reach north, the north sidewalk's
    south, Mott's lamps across Mott."""
    zw = -y
    if 8.0 <= x <= 10.2 and zw > -14.0:
        return 90.0
    if 15.8 <= x <= 18.0 and zw > -14.0:
        return -90.0
    if zw < -29.0:
        return 0.0
    return 180.0


# ================================================================================================= structures

def structures(out):
    for mesh, piv, cols in lv.struct_places():
        out.append(mk(mesh, piv[0], piv[1], piv[2], 0.0, mesh.split("_CT_")[1].split("_")[0], "structure", colliders=cols))


# ================================================================================================= all of it

def assemble():
    out, report = [], {"notPlaced": [], "unmapped": {}, "fit": []}
    shops = assemble_faces(out)
    data_signs(shops, out, report)
    props(out, report)
    structures(out)
    for k, why in UNMAPPED_WHY.items():
        if k in report["unmapped"]:
            report["unmapped"][k] = "%d placement(s): %s" % (report["unmapped"][k], why)
    return out, report


def buildings():
    """The facade buildings of round 2 and the pivot of each one's far proxy (its first face's origin on its base)."""
    out = {}
    for F, storeys, brick, kind, segs, opt in faces():
        if F.building == "Arcade":
            continue
        if F.building not in out:
            out[F.building] = {"pivot_blender_m": [round(F.o[0], 4), round(F.o[1], 4), F.base], "faces": [], "storeys": storeys}
        out[F.building]["faces"].append({"key": F.key, "plane_web": F.plane, "outward": F.outward, "start_web": F.start,
                                          "length_m": F.L, "brick": brick, "kind": kind})
    return out


def needed():
    """Round-2 modules: alcoves, ground bays, window bays in a brick the Block has only blank, heads."""
    from assets import _chinatown_place as place
    need = {"alcove": set(), "ground": set(), "bay": set(), "head": set()}
    for e in place.assemble():
        m = e["mesh"]
        if m.startswith("SM_Facade_CT_Alcove_"):
            need["alcove"].add(m.rsplit("_", 1)[1])
        for k in GROUND_KINDS:
            if m.startswith("SM_Facade_CT_%s_" % k):
                need["ground"].add((k, m.rsplit("_", 1)[1]))
        if m.startswith("SM_Facade_CT_BayWindow_"):
            need["bay"].add(m.rsplit("_", 1)[1])
        if m.startswith("SM_Facade_CT_Head_"):
            _a, k, wh = m.rsplit("_", 2)
            w, h = wh.split("x")
            need["head"].add((k, int(w) / 100.0, int(h) / 100.0))
    return {k: sorted(v) for k, v in need.items()}


def sign_coverage(instances):
    """Every shop front with a sign over it: a sign instance on the same face whose face spans the front's middle third,
    up to 8 m over the sidewalk (the north row's fronts are matched by building and position)."""
    fronts = [e for e in instances if e["role"] == "shop front"]
    signs = [e for e in instances if e.get("face") and e["role"] not in ("placard",)]
    missing = []
    for f in fronts:
        mesh = f["mesh"].split("_CT_")[1]
        c = FRONTS.get(mesh, 6.0)
        a = math.radians(f["rot_z_deg"])
        u = (math.cos(a), math.sin(a))
        x0, y0 = f["blender_m"][0], f["blender_m"][1]
        mid = (x0 + u[0] * c / 2, y0 + u[1] * c / 2)
        ok = False
        for s in signs:
            if s["building"] != f["building"]:
                continue
            sx, sy, sz = s["blender_m"]
            Fw = names.FACES.get(s["face"], {}).get("w") or names.NEON.get(s["face"], {}).get("w") or 1.0
            a2 = math.radians(s["rot_z_deg"])
            u2 = (math.cos(a2), math.sin(a2))
            if s["role"] == "blade":
                continue
            # the sign's span along the front's run, and its distance from the front's plane
            t0 = (sx - x0) * u[0] + (sy - y0) * u[1]
            t1 = t0 + Fw * (u2[0] * u[0] + u2[1] * u[1])
            lo_, hi_ = min(t0, t1), max(t0, t1)
            dist = abs(-(sx - x0) * u[1] + (sy - y0) * u[0])
            if lo_ <= c * 0.66 and hi_ >= c * 0.33 and dist < 1.5 and sz - f["blender_m"][2] < 8.0:
                ok = True
                break
        if not ok:
            missing.append((f["building"], f.get("faceKey"), f["mesh"], [round(v, 2) for v in mid]))
    return len(fronts), missing


if __name__ == "__main__":
    out, rep = assemble()
    from collections import Counter
    print(len(out), "instances", Counter(e["role"] for e in out).most_common(12))
    print("not placed", rep["notPlaced"])
    print("unmapped", rep["unmapped"])
    print("worst prop fits", sorted(rep["fit"], key=lambda r: -r["overhang_m"])[:6])
