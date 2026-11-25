"""RATTLER: the Goons' compact open-bolt submachine gun in the player's hands (9 mm class, semi / auto, 545 rpm), our own
design in the manner of a class of firearm: a stamped sheet-steel box, a round ventilated shroud with a tan strap wrap, a
slotted muzzle device, a long straight stick magazine ahead of the pistol grip and a folding wire stock.

Gun space = Blender space as the CHOPPER and the NINE: X forward along the bore, Y left, Z up, metres. The ORIGIN is on the
bore axis at the rear face of the receiver (the data already expects it: guns.json art note X_rattler = X_goon + 0.080,
Z_rattler = Z_goon - 0.042). Muzzle +X (0.465, stock folded).

This module holds the contract (bones, sockets, pivots, travel), small mm-unit wrappers over the weapons kit, and the big
solids of the BODY: the stamped receiver (hollow, 1.6 mm sheet, 3 mm bends) with its ejection port, handle slot, magazine
well, ribs, spot welds and top seam; the MI-R rail on the cover; the ventilated shroud, the strap wrap, the barrel and its
threaded stub, the slotted muzzle device, the flip-up rear sight and the front sight tower. _weapons_rattler_b.py has the
grip, trigger group, bolt, selector, wire stock, magazine and the rig; weapons_rattler.py is the family (build, textures,
export, previews).

Layout (mm from the receiver's rear face, Z from the bore):
    receiver   X 0..270, Y +-22, Z -42..+30, 1.6 mm sheet, outer bends R 3, ribs, spot welds, top seam
    rail       MI-R on the cover, lug tops Z +42, 12 lugs from X 111, the red dot's Optic socket at X 172
    shroud     round tube R 25.5, X 270..410, wall 1.6, 35 slots (5 x 9) over the open third, end ring, tan strap X 290..350
    barrel     breech X 198, bore R 4.5, R 8 inside the shroud, R 9.5 collars, threaded stub R 8.5 X 410..422 under the device
    device     slotted nose X 410..465 R 14.5, three 6 mm slots at 12 mm pitch, bore R 4.5
"""
import math

import bpy
import numpy as np

from mi import geo
from assets import weapons as W
from assets import _weapons_kit as K
from assets import _weapons_chopper as CH9

MM = 0.001

# material ids (face attribute 'mid'): one unique 4K set, the id picks the surface recipe (see the painter)
SHEET = W.COVER          # mid-grey phosphated stamped sheet: receiver, cover, rail, magazine well, guard
BLACK = W.BLACKOX        # darker blackened steel: shroud, barrel, muzzle device, sights, handle, small hardware
BRIGHT = W.BRIGHT        # bright steel: bolt face, extractor, worn pins
POLY = W.POLYMER         # black stippled polymer: the pistol grip
ZINC = W.ZINC            # dull zinc: the wire stock
STRAP = W.TAPE           # tan woven nylon strap wrap
BORE = W.BORE            # very dark interior surfaces (bores, cavities that never see light)
INNER = W.DARK           # oiled dark phosphate: the receiver's inside, the bolt body, the breech
WHITE = W.PAINT          # white paint: sight dots
BRASS, COPPER, PRIMER = W.BRASS, W.COPPER, W.PRIMER
MAGSTEEL = W.COVER       # the magazine's stamped steel body (same grey phosphate as the receiver)

BONE_ID = {"body": 0, "bolt": 1, "trigger": 2, "selector": 3, "magazine": 4, "stock": 5, "MuzzleDevice": 6,
           "IronsFront": 7, "IronsRear": 8}

RT = {   # specification numbers, metres (gun space)
    "length": 0.465, "height": 0.2715,
    "bolt_head": (0.215, 0.0, 0.0), "bolt_travel": 0.050,
    "trigger_pivot": (0.127, 0.0, -0.045), "trigger_deg": 17.0,
    "selector_pivot": (0.045, 0.0225, -0.014), "selector_deg": (0.0, 14.0, 28.0),
    "mag_hinge": (0.166, 0.0, -0.032), "mag_drop": 0.14,
    "stock_hinge": (0.0, 0.0285, 0.0), "stock_deg": 180.0,
    "muzzle_head": (0.410, 0.0, 0.0), "irons_front_head": (0.412, 0.0, 0.0255), "irons_rear_head": (0.012, 0.0, 0.030),
    "sockets": {"Muzzle": (0.465, 0.0, 0.0), "Eject": (0.165, -0.0225, 0.008), "SightRear": (0.012, 0.0, 0.0575),
                "SightFront": (0.412, 0.0, 0.0575), "RecoilPivot": (-0.020, 0.0, -0.030),
                "MagHinge": (0.166, 0.0, -0.032), "Palm_R": (0.062, -0.0150, -0.082),
                "Palm_L": (0.315, 0.0, -0.0275), "Optic": (0.172, 0.0, 0.042), "MuzzleMount": (0.410, 0.0, 0.0)},
    "eject_dir": (0.0, -0.95, 0.31),
}

# the exact numbers the other modules and the proof read (mm)
REC = dict(x0=0.0, x1=270.0, w=22.0, zb=-42.0, zt=30.0, r=3.0, t=1.6)
PORT = (140.0, 200.0, 0.0, 24.0)                       # ejection port (x0, x1, z0, z1), right flank
HSLOT = (38.0, 106.0, -4.0, 4.0)                       # charging-handle slot in the cover (x0, x1, y0, y1)
WELL_IN = (144.5, 187.5, -15.5, 15.5)                  # magazine well opening (x0, x1, y0, y1)
WELL_OUT = (142.9, 189.1, -17.1, 17.1, -72.0, -42.0)   # magazine well housing (x0, x1, y0, y1, z0, z1)
TRIG_SLOT = (117.0, 139.0, -5.5, 5.5)                  # trigger slot in the floor (x0, x1, y0, y1)
RAIL = dict(x0=111.05, lugs=12, zref=42.0)             # MI-R on the cover (lug tops Z 42; X 111.05..232.95)
LUG, PITCH = 5.3, 10.6
SHROUD = dict(x0=270.0, x1=410.0, r=25.5, t=1.6, flange=(270.0, 277.5, 27.0), ring=(398.0, 410.0, 27.0))
WRAP = dict(x0=290.0, x1=350.0, r0=25.5, r1=27.5)
VENT_X = [284.0 + 8.4 * k for k in range(14)]
BREECH_X = 198.0
STUB = (410.0, 422.0, 8.5)                             # threaded stub: x0, x1, radius
DEVICE = (410.0, 465.0, 14.5)                          # muzzle device x0, x1, radius


# ----------------------------------------------------------------------------------------------- mm wrappers

def bx(x0, x1, y0, y1, z0, z1, bevel=0.0, seg=2, name="Box"):
    return W.box(x0 * MM, x1 * MM, y0 * MM, y1 * MM, z0 * MM, z1 * MM, bevel * MM, seg, name)


def pr(outline, a0, a1, axis="Y", bevel=0.4, seg=2, fillet=0.0, name="Prism", corner=30.0, fseg=3):
    """Prism from an outline in mm: axis 'Y' (x, z), 'Z' (x, y), 'X' (y, z), extruded between a0 and a1 (mm)."""
    pts = [(p[0] * MM, p[1] * MM) for p in outline]
    return W.prism(pts, a0 * MM, a1 * MM, axis, bevel * MM, seg, name, corner, fillet * MM, fseg)


def lt(prof, seg=48, axis="X", at=(0.0, 0.0, 0.0), name="Lathe", fillet=0.0, fseg=2, closed=False):
    """Lathe from a profile [(t, r)] in mm along an axis through `at` (mm)."""
    return W.lathe([(t * MM, r * MM) for t, r in prof], seg, axis, tuple(a * MM for a in at), name, closed,
                   fillet * MM, fseg)


def tr(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    geo.transform(ob, loc=tuple(a * MM for a in loc), rot=rot, scale=scale)
    return ob


def smooth01(t):
    return CH9.smoothstep(t)


def finish(ob, mid, bone, smooth=50.0):
    """Finish a part like weapons.P but safe after booleans and bevels: weld coincident vertices first, drop degenerate
    faces, smooth by angle, area-weighted normals, the material id, the bone id and the rigid bone."""
    import bmesh
    bm = geo.bm_of(ob)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-6)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    geo.bm_to(ob, bm)
    geo.smooth_by_angle(ob, smooth)
    geo.weighted_normals(ob)
    me = ob.data
    for nm in ("mid", "part", "bid"):
        a = me.attributes.get(nm) or me.attributes.new(nm, "FLOAT", "FACE")
        if nm == "mid":
            v = float(mid)
        elif nm == "bid":
            v = float(BONE_ID.get(bone or "body", 0))
        else:
            v = float(np.random.default_rng(len(bpy.data.objects) * 7919).random())
        a.data.foreach_set("value", np.full(len(me.polygons), v, np.float32))
    if bone:
        from mi import rig
        rig.tag(ob, bone)
    return ob


def inside_boxes(ob, boxes_mm, mid):
    """Set the face attribute 'mid' of the faces whose centre lies in any of the boxes (x0, x1, y0, y1, z0, z1 in mm)."""
    me = ob.data
    n = len(me.polygons)
    c = np.empty(n * 3, np.float32)
    me.polygons.foreach_get("center", c)
    c = c.reshape(-1, 3) / MM
    a = me.attributes.get("mid") or me.attributes.new("mid", "FLOAT", "FACE")
    v = np.empty(n, np.float32)
    a.data.foreach_get("value", v)
    for x0, x1, y0, y1, z0, z1 in boxes_mm:
        m = ((c[:, 0] >= x0) & (c[:, 0] <= x1) & (c[:, 1] >= y0) & (c[:, 1] <= y1) & (c[:, 2] >= z0) & (c[:, 2] <= z1))
        v[m] = float(mid)
    a.data.foreach_set("value", v)
    return ob


def joined(objs, name):
    objs = [o for o in objs if o is not None]
    return geo.join(objs, name) if len(objs) > 1 else objs[0]


def cut_many(target, cutters, solver="EXACT"):
    """One boolean pass with every cutter joined into a single object (the cutters must not overlap one another)."""
    cutters = [c for c in cutters if c is not None]
    if not cutters:
        return target
    c = joined(cutters, "Cutters")
    geo.boolean(target, c, "DIFFERENCE", solver)
    return target


def rot_x(ob, deg, at=(0.0, 0.0, 0.0)):
    """Rotate an object's mesh about an X-parallel axis through (y, z) = at[1:], mm."""
    tr(ob, loc=(0, -at[1], -at[2]))
    geo.transform(ob, rot=(deg, 0, 0))
    tr(ob, loc=(0, at[1], at[2]))
    return ob


# ----------------------------------------------------------------------------------------------- MI-R rail

def mi_profile(flip=False):
    """MI-R cross section (y, z) relative to the lug-top plane (reference plane, z = 0, lugs reach down to -12):
    21.2 mm across the 45 degree flanks, 15.6 mm base, 12 mm lugs, slots cut down to -5.4 (the standard shared with the
    parts kit and copied from the CHOPPER's rail). flip: the lugs hang down (rail under the gun)."""
    p = [(-7.8, -12.0), (7.8, -12.0), (7.8, -6.4), (10.6, -3.7), (10.6, -2.7), (7.8, 0.0), (-7.8, 0.0), (-10.6, -2.7),
         (-10.6, -3.7), (-7.8, -6.4)]
    if flip:
        p = [(y, -z) for y, z in p][::-1]
    return p


def mi_rail(x0, lugs, zref, flip=False, name="Rail", bevel=0.25):
    """MI-R rail: `lugs` lugs of 5.3 mm with 5.3 mm slots between them from x0 (mm), the lug tops on the plane zref."""
    n_slots = lugs - 1
    length = lugs * LUG + n_slots * LUG
    pts = [(y, z + zref) for y, z in mi_profile(flip)]
    rail = pr(pts, x0, x0 + length, axis="X", bevel=bevel, seg=1, name=name)
    floor = -5.4
    cutters = []
    for k in range(n_slots):
        a = x0 + LUG + k * PITCH
        cutters.append(bx(a, a + LUG, -14, 14, zref + floor, zref + 5) if not flip else
                       bx(a, a + LUG, -14, 14, zref - 5, zref - floor))
    cut_many(rail, cutters)
    W.round_edges(rail, bevel * MM, 1, 50)
    return rail


# ----------------------------------------------------------------------------------------------- receiver

def rec_ring(inset=0.0, r=None):
    """(y, z) ring in mm, counter-clockwise: the stamped box's section, outer bends R 3 (R 1.4 inside)."""
    w, zb, zt = REC["w"] - inset, REC["zb"] + inset, REC["zt"] - inset
    r = max((REC["r"] - inset) if r is None else r, 0.35)
    corners = [(-w, zb), (w, zb), (w, zt), (-w, zt)]
    return CH9.rpoly(corners, [r] * 4, [5] * 4, [6, 4, 6, 4])


def receiver_solid():
    """The outer sheet box as a loft: 44 x 72 mm, 3 mm bends, ends rounded 0.8 mm."""
    xs = CH9.stations(REC["x0"], REC["x1"], 22.0, 0.8, 3, extra=[36, 40, 106, 110, 138, 142, 188, 192, 198, 202, 236, 240])
    polys = []
    for x in xs:
        d = CH9.end_inset(x, REC["x0"], REC["x1"], 0.8)
        polys.append(CH9.offset(rec_ring(), -d) * MM)
    return CH9.loft_polys(polys, np.asarray(xs) * MM, "Receiver")


def cavity_cutter():
    """The hollow of the box: 1.6 mm walls, R 1.4 inner bends, closed by the 1.6 mm end plates."""
    t = REC["t"]
    ring = CH9.offset(rec_ring(), -t) * MM
    return CH9.loft_polys([ring, ring], np.array([t, REC["x1"] - t]) * MM, "Cavity")


def port_cutter():
    """The ejection port through the right flank, 60 x 24 mm, R 4 corners; reaches only through the 1.6 mm wall."""
    x0, x1, z0, z1 = PORT
    return pr([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], -30.0, -16.0, "Y", bevel=0.0, fillet=4.0, name="Port")


def hslot_cutter():
    """The charging-handle slot in the cover top (8 mm wide, rounded ends)."""
    x0, x1, y0, y1 = HSLOT
    return pr([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 20.0, 40.0, "Z", bevel=0.0, fillet=3.9, name="HSlot")


def well_cutter():
    x0, x1, y0, y1 = WELL_IN
    return pr([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], -50.0, -30.0, "Z", bevel=0.0, fillet=1.5, name="WellHole")


def trig_cutter():
    x0, x1, y0, y1 = TRIG_SLOT
    return pr([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], -50.0, -30.0, "Z", bevel=0.0, fillet=1.2, name="TrigSlot")


def barrel_hole_cutter():
    return lt([(262.0, 0.0), (262.0, 11.4), (272.0, 11.4), (272.0, 0.0)], 48, name="BarrelHole")


def build_receiver():
    """The stamped box: hollow, with the ejection port, the handle slot, the well opening, the trigger slot and the
    barrel hole cut; interior faces get the dark interior id."""
    b = receiver_solid()
    W.cut(b, cavity_cutter())
    cut_many(b, [port_cutter(), hslot_cutter(), well_cutter(), trig_cutter(), barrel_hole_cutter()])
    W.round_edges(b, 0.4 * MM, 2, 50)
    return b


def rec_interior_boxes():
    t = REC["t"]
    return [(t - 0.2, REC["x1"] - t + 0.2, -REC["w"] + t - 0.3, REC["w"] - t + 0.3, REC["zb"] + t - 0.3, REC["zt"] - t + 0.3)]


def build_ribs():
    """Stamped reinforcement ribs, 1.3 mm proud, 4 mm wide: two long ones per flank (the left ones start behind the
    selector's reach at X 82)."""
    out = []
    for side, x0, x1 in ((-1, 14.0, 256.0), (1, 82.0, 256.0)):
        for z in (-8.0, -27.0):
            y_in, y_out = 21.5, 23.3
            a, b = (y_in, y_out) if side > 0 else (-y_out, -y_in)
            out.append(pr([(x0, z - 2.0), (x1, z - 2.0), (x1, z + 2.0), (x0, z + 2.0)], a, b, "Y", bevel=0.8, seg=3, fillet=1.9,
                          name="Rib"))
    return out


def build_welds():
    """Spot welds every 18 mm along the lower edges of both flanks (Z -36): 15 per side."""
    out = []
    for k in range(15):
        x = 9.0 + 18.0 * k
        for side in (-1, 1):
            w = lt([(-0.4, 0.0), (-0.4, 1.7), (0.0, 1.7), (0.30, 1.35), (0.50, 0.7), (0.56, 0.0)], 12, axis="Y",
                   at=(0.0, 0.0, 0.0), name="Weld")
            if side < 0:
                geo.transform(w, scale=(1, -1, 1))
            tr(w, loc=(x, side * 22.0, -35.5))
            out.append(w)
    return out


def build_seam():
    """The butt-welded seam along the cover's top centre line: a 1.6 mm bead in three runs (the slot and the rail
    interrupt it)."""
    out = []
    for x0, x1 in ((3.0, 36.0), (107.5, 110.0), (234.0, 267.5)):
        out.append(bx(x0, x1, -0.85, 0.85, 29.6, 30.75, bevel=0.45, seg=2, name="Seam"))
    return out


def build_rail():
    return mi_rail(RAIL["x0"], RAIL["lugs"], RAIL["zref"], False, "Rail")


def build_rail_bed():
    """The cover's pressed saddle under the rail: a 1.2 mm base plate wider than the rail's foot, with 4 rivets."""
    out = [bx(RAIL["x0"] - 2.0, RAIL["x0"] + 12 * LUG + 11 * LUG + 2.0, -10.2, 10.2, 29.9, 30.9, bevel=0.45, seg=2, name="RailBed")]
    return out


def build_rear_cap():
    """Rear end: the spring-cap boss (R 9, 2.2 mm proud) with a slotted screw, behind the 1.6 mm end plate."""
    boss = lt([(-2.2, 0.0), (-2.2, 7.6), (-1.6, 8.8), (0.6, 9.0), (0.6, 0.0)], 40, axis="X", at=(0.0, 0.0, 0.0), name="RearBoss",
              fillet=0.5)
    return boss


def rrect_pts(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def build_rear_frame():
    """The rear end plate's pressed border: a 1.4 mm wide frame standing 1 mm proud round the edge of the plate, with four corner
    rivets inside it."""
    outer = pr(rrect_pts(-19.6, 19.6, -39.6, 27.6) if False else [(-19.6, -39.6), (19.6, -39.6), (19.6, 27.6), (-19.6, 27.6)], -1.1, 0.4, "X",
               bevel=0.35, seg=1, fillet=2.6, name="RearFrame")
    inner = pr([(-18.2, -38.2), (18.2, -38.2), (18.2, 26.2), (-18.2, 26.2)], -2.5, 1.5, "X", bevel=0.0, fillet=1.6, name="RearFrameIn")
    W.cut(outer, inner)
    out = [outer]
    for y, z in ((-14.0, -32.0), (14.0, -32.0), (-14.0, 20.0), (14.0, 20.0)):
        out.append(W.rivet((0.2 * MM, y * MM, z * MM), "X", r=0.0023, h=0.0009, sign=-1, seg=14))
    return out


def build_port_frame():
    """The pressed lip round the ejection port: 1.8 mm wide, 0.9 mm proud, flush with the port's edge."""
    x0, x1, z0, z1 = PORT
    outer = pr([(x0 - 1.8, z0 - 1.8), (x1 + 1.8, z0 - 1.8), (x1 + 1.8, z1 + 1.8), (x0 - 1.8, z1 + 1.8)], -22.9, -21.4, "Y", bevel=0.35,
               seg=1, fillet=5.8, name="PortFrame")
    inner = pr([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], -25.0, -18.0, "Y", bevel=0.0, fillet=4.0, name="PortFrameIn")
    W.cut(outer, inner)
    return outer


def build_takedown():
    """The takedown pin's head on the right flank near the rear: a knurled R 4.2 head with a screwdriver slot."""
    return W.pin_head((22.0 * MM, -22.0 * MM, -17.5 * MM), "Y", r=0.0042, h=0.0016, sign=-1, slot=True, seg=24)


# ----------------------------------------------------------------------------------------------- magazine well

def build_well():
    """Stamped well housing under the receiver: 1.6 mm walls, the mouth flared 1 mm."""
    x0, x1, y0, y1, z0, z1 = WELL_OUT
    h = bx(x0, x1, y0, y1, z0, z1, bevel=1.4, seg=2, name="WellHousing")
    xi0, xi1, yi0, yi1 = WELL_IN
    W.cut(h, bx(xi0, xi1, yi0, yi1, z0 - 1.0, z1 + 4.0, bevel=0.6, name="WellBore"))
    W.cut(h, bx(143.5, 145.0, -1.5, 1.5, z0 - 1.0, z1 + 4.0, bevel=0.0, name="SeamRelief"))   # room for the magazine's spine weld
    W.round_edges(h, 0.35 * MM, 1, 50)
    return h


# ----------------------------------------------------------------------------------------------- shroud, barrel, sights

def build_shroud():
    """Round steel tube R 25.5 (wall 1.6) from the receiver's front plate to the nose, a flange at the rear and an end ring
    at the front, with 5 rows of 5 x 9 mm slots (the underside row is left out) in the columns the strap does not cover."""
    x0, x1, r, t = SHROUD["x0"], SHROUD["x1"], SHROUD["r"], SHROUD["t"]
    fx0, fx1, fr = SHROUD["flange"]
    ex0, ex1, er = SHROUD["ring"]
    ri = r - t
    prof = [(x0, ri), (x0, fr - 0.8), (x0 + 0.8, fr), (fx1 - 0.8, fr), (fx1, fr - 0.8), (fx1, r), (ex0, r),
            (ex0, er - 0.8), (ex0 + 0.8, er), (ex1 - 0.8, er), (ex1, er - 0.8), (ex1, 14.2), (ex1 - 3.0, 14.2),
            (ex1 - 3.0, ri), (fx1 + 2.0, ri), (fx1 + 2.0, ri - 0.0)]
    # a closed ring profile: outer wall out, inner wall back
    tube = lt(prof, 72, name="Shroud", closed=True)
    vents = []
    for k, xc in enumerate(VENT_X):
        if 289.0 < xc - 2.5 and xc + 2.5 < 351.0:
            continue                                      # fully under the strap
        for row in range(6):
            ang = row * 60.0
            if row == 3:
                continue
            c = pr([(xc - 2.5, -4.5), (xc + 2.5, -4.5), (xc + 2.5, 4.5), (xc - 2.5, 4.5)], 19.0, 31.0, "Z", bevel=0.0, fillet=2.2,
                   fseg=2, name="Vent")
            rot_x(c, ang)
            vents.append(c)
    cut_many(tube, vents)
    W.round_edges(tube, 0.3 * MM, 1, 50)
    return tube


def build_barrel():
    """Barrel: chamber ring at the breech (X 198, chamber mouth R 4.9 in the breech face), R 11 through the receiver, R 9.5
    collars, R 8 inside the shroud, the R 8.5 threaded stub (six turns) to X 422, crowned, bored R 4.5 through."""
    prof = [(BREECH_X, 4.9), (BREECH_X, 12.5), (BREECH_X + 1.0, 13.0), (BREECH_X + 14.0, 13.0), (BREECH_X + 15.0, 11.0), (270.0, 11.0),
            (272.0, 9.5), (292.0, 9.5), (293.5, 8.0), (396.5, 8.0), (398.0, 9.5), (410.0, 9.5), (410.0, 8.9)]
    pitch, r_valley, r_peak = 2.0, 8.05, 8.5
    x = 410.0
    for k in range(6):
        prof += [(x + 0.2 + k * pitch, r_valley), (x + 0.5 + k * pitch, r_peak), (x + 1.3 + k * pitch, r_peak),
                 (x + 1.6 + k * pitch, r_valley)]
    prof += [(422.0, 8.05), (422.0, 7.0), (421.5, 6.5), (421.5, 4.5), (BREECH_X + 16.0, 4.5), (BREECH_X + 16.0, 4.9)]
    return lt(prof, 40, name="Barrel", closed=True)


def build_device():
    """Slotted muzzle device X 410..465, R 14.5, one closed shell: a rear recess over the stub, a front wall with the bore
    R 4.5, three 6 mm slots at 12 mm pitch cut through the top and the sides."""
    x0, x1, r = DEVICE
    h = lt([(x0, 0.0), (x0, r - 1.0), (x0 + 1.0, r), (x0 + 4.5, r), (x0 + 4.5, r - 0.6), (x0 + 6.0, r - 0.6), (x0 + 6.0, r),
            (x1 - 1.4, r), (x1, r - 1.4), (x1, 0.0)], 56, name="Device", fillet=0.3)
    W.cut(h, lt([(x0 - 1.0, 0.0), (x0 - 1.0, 9.1), (x0 + 13.5, 9.1), (x0 + 13.5, 0.0)], 48, name="DeviceRecess"))
    W.cut(h, lt([(x0 + 12.5, 0.0), (x0 + 12.5, 7.2), (x1 + 1.0, 7.2), (x1 + 1.0, 0.0)], 40, name="DeviceChamber"))
    W.cut(h, lt([(x1 - 4.0, 0.0), (x1 - 4.0, 4.5), (x1 + 1.0, 4.5), (x1 + 1.0, 0.0)], 32, name="DeviceBore"))
    slots = []
    for k in range(3):
        xc = 426.0 + 12.0 * k
        slots.append(bx(xc - 3.0, xc + 3.0, -9.0, 9.0, 0.0, r + 2.0, bevel=0.0, name="DevSlot"))
    cut_many(h, slots)
    W.round_edges(h, 0.4 * MM, 2, 50)
    return h


def build_front_sight():
    """The front-sight tower on the nose ring, X 395..415: a dovetail base, the post (tip X 412, Z 57.5 = SightFront) and two
    3 mm guard ears; every piece closed, all on bone IronsFront."""
    parts = []
    base = pr([(395.0, 24.0), (415.0, 24.0), (415.0, 33.0), (411.0, 36.0), (399.0, 36.0), (395.0, 33.0)], -9.5, 9.5, "Y", bevel=0.7,
              seg=2, fillet=1.0, name="TowerBase")
    parts.append(base)
    post = pr([(410.0, 35.0), (414.0, 35.0), (414.0, 56.7), (413.2, 57.5), (410.8, 57.5), (410.0, 56.7)], -1.5, 1.5, "Y", bevel=0.35,
              seg=1, name="Post")
    parts.append(post)
    for s in (1, -1):
        ear = pr([(400.0, 35.0), (418.0, 35.0), (418.0, 57.0), (415.0, 61.5), (403.0, 61.5), (400.0, 57.0)], s * 6.0, s * 9.0, "Y",
                 bevel=0.45, seg=2, fillet=1.4, name="Ear")
        parts.append(ear)
    return parts


def build_rear_base():
    """The rear sight's fixed base on the cover (bone body): a 20 x 22 mm stamped saddle with two hinge ears."""
    parts = [bx(4.0, 24.0, -11.0, 11.0, 29.8, 34.0, bevel=1.0, seg=2, name="RearBase")]
    for s in (1, -1):
        y0, y1 = (7.4, 10.4) if s > 0 else (-10.4, -7.4)
        parts.append(bx(8.0, 16.0, y0, y1, 33.5, 41.0, bevel=1.0, seg=2, name="RearEar"))
    return parts


def build_rear_leaf():
    """The flip-up rear sight (bone IronsRear): a 3 mm leaf with a 4.8 mm aperture centred on the sight line (Z 57.5, X 12)
    in a 13 mm ring, a countersink toward the eye, two guard wings and a hinge pin through the base ears (Z 37.5)."""
    leaf = pr([(-7.0, 34.6), (7.0, 34.6), (7.0, 46.0), (6.9, 51.0), (6.5, 57.5), (0.0, 64.0), (-6.5, 57.5), (-6.9, 51.0),
              (-7.0, 46.0)], 10.5, 13.5, "X", bevel=0.4, seg=2, fillet=1.4, name="Leaf")
    ap = lt([(9.0, 0.0), (9.0, 3.6), (10.5, 2.5), (14.5, 2.4), (14.5, 0.0)], 32, name="Aperture", at=(0.0, 0.0, 57.5))
    W.cut(leaf, ap)
    parts = [leaf]
    for s in (1, -1):
        e = pr([(12.0, 38.0), (21.0, 38.0), (21.0, 54.0), (19.0, 58.0), (12.0, 58.0)], s * 7.0 if s > 0 else -9.2, 9.2 if s > 0 else -7.0, "Y",
               bevel=0.4, seg=1, fillet=1.0, name="LeafWing")
        parts.append(e)
    parts.append(lt([(-10.2, 0.0), (-10.2, 1.4), (-9.6, 1.9), (9.6, 1.9), (10.2, 1.4), (10.2, 0.0)], 20, axis="Y", at=(12.0, 0.0, 37.5),
                    name="HingePin"))
    return parts
