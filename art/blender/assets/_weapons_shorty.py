"""SHORTY: a compact bullpup carbine (5.6 mm class, short-stroke gas piston, semi / auto), our own design.

Gun space = Blender space as the CHOPPER and the NINE: X forward along the bore, Y left, Z up, metres. The ORIGIN is on
the bore axis at the rear face of the butt pad (in a bullpup the receiver ends at the butt). Muzzle +X (0.700).
This module holds the contract (bones, sockets, pivots, travel), small mm-unit wrappers over the weapons kit, and the
big solids: moulded body, butt pad, carry handle with the exact MI-R rail, ventilated forend with its underside rail,
barrel, gas system, birdcage flash hider and front sight. _weapons_shorty_b.py has the grip, trigger group, moving
parts, details, magazine and the rig; weapons_shorty.py is the family (build, textures, export, previews).

Layout (mm from the butt face, Z from the bore):
    butt pad    X 0..30, Z -78..+52, R 120 in side view, 38 wide, rubber, 6 mm heel chamfer, lanyard hole in the toe
    body        X 30..395, Z -62..+50 (cheek rise +56 over X 34..110), 56 wide, 4 mm top chamfers, 3.5 mm bottom radii
    handle      legs X 118..150 / 300..330, bar Z 76..88, window 150 x 24 (Z 52..76), rail MI-R X 160..282 (12 lugs,
                11 slots, lug tops Z 100), rear aperture (9 mm at X 134, Z 60) in a 20 mm ring, sight port in the front leg
    forend      X 392..590, Z -40..+34, 62 wide, hollow, 3 x 4 slots of 5 x 14 per side, rail MI-R underneath
    barrel      X 396..664 (R 9.5 to the shoulder X 652, then the R 8.5 threaded stub), bore R 2.8, hider X 652..700
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
OLIVE = W.POLYMER        # olive-drab injection-moulded polymer
PARK = W.DARK            # parkerised steel
BRIGHT = W.BRIGHT        # bright steel: bolt face, extractor, worn carrier
RUBBER = W.TAPE          # black rubber butt pad
BORE = W.BORE            # dark interior surfaces (cavities, bores)
TRIT = W.LENS            # tritium insert (the only emissive texels)
WHITE = W.PAINT          # white paint (selector marks)
BRASS, COPPER, PRIMER = W.BRASS, W.COPPER, W.PRIMER
MAGSTEEL = W.BLUED       # the magazine's stamped steel body

BONE_ID = {"body": 0, "bolt": 1, "trigger": 2, "selector": 3, "magazine": 4, "MuzzleDevice": 5, "IronsFront": 6}

SH = {   # brief numbers, metres (gun space)
    "length": 0.700, "height": 0.280,
    "bolt_head": (0.380, 0.0, 0.012), "bolt_travel": 0.075,
    "trigger_pivot": (0.362, 0.0, -0.050), "trigger_deg": 17.0,
    "selector_pivot": (0.300, 0.0285, -0.022), "selector_deg": (0.0, 14.0, 28.0),
    "mag_hinge": (0.206, 0.0, -0.020), "mag_drop": 0.13,
    "muzzle_head": (0.652, 0.0, 0.0), "irons_front_head": (0.575, 0.0, 0.034),
    "sockets": {"Muzzle": (0.700, 0.0, 0.0), "Eject": (0.372, -0.0285, 0.016), "SightRear": (0.134, 0.0, 0.060),
                "SightFront": (0.575, 0.0, 0.060), "RecoilPivot": (0.015, 0.0, -0.012),
                "MagHinge": (0.206, 0.0, -0.020), "Palm_R": (0.295, -0.0165, -0.095),
                "Palm_L": (0.505, 0.0, -0.052), "Optic": (0.221, 0.0, 0.100), "MuzzleMount": (0.652, 0.0, 0.0),
                "Underbarrel": (0.488, 0.0, -0.052), "Laser": (0.536, 0.0, -0.052)},
}

# the exact numbers the other modules and the proof read (mm)
BODY_X0, BODY_X1 = 30.0, 395.0
BODY_W, BODY_ZB, BODY_ZT = 28.0, -62.0, 50.0
FORE_X0, FORE_X1 = 392.0, 590.0
FORE_W, FORE_ZB, FORE_ZT = 31.0, -40.0, 34.0
CAV = (215.0, 398.0, -16.0, 16.0, -10.0, 33.0)          # bolt carrier cavity X0, X1, Y0, Y1, Z0, Z1
WELL = (180.0, 232.0, -13.0, 13.0, -64.0, -18.0)       # magazine well
PORT = (340.0, 400.0, 0.0, 32.0)                       # ejection port (x0, x1, z0, z1), right flank
SLOT = (298.0, 386.0, 6.0, 18.0)                       # bolt slot (x0, x1, z0, z1), left flank
RAIL_TOP = dict(x0=160.0, lugs=12, zref=100.0)         # MI-R on the carry handle
RAIL_UNDER = dict(x0=459.95, lugs=10, zref=-52.0)      # MI-R under the forend
LUG, PITCH = 5.3, 10.6
VENT_COLS = (480.0, 495.0, 510.0, 525.0)               # slot centres (X), five mm wide
VENT_ROWS = (-24.0, -3.0, 18.0)                        # slot centres (Z), fourteen mm tall


# ----------------------------------------------------------------------------------------------- mm wrappers

def bx(x0, x1, y0, y1, z0, z1, bevel=0.0, seg=2, name="Box"):
    return W.box(x0 * MM, x1 * MM, y0 * MM, y1 * MM, z0 * MM, z1 * MM, bevel * MM, seg, name)


def pr(outline, a0, a1, axis="Y", bevel=0.4, seg=2, fillet=0.0, name="Prism", corner=30.0, fseg=3):
    """Prism from an outline in mm: axis 'Y' (x, z), 'Z' (x, y), 'X' (y, z), extruded between a0 and a1 (mm)."""
    pts = [(p[0] * MM, p[1] * MM) for p in outline]
    return W.prism(pts, a0 * MM, a1 * MM, axis, bevel * MM, seg, name, corner, fillet * MM, fseg)


def lt(prof, seg=48, axis="X", at=(0.0, 0.0, 0.0), name="Lathe", fillet=0.0, fseg=2):
    """Lathe from a profile [(t, r)] in mm along an axis through `at` (mm)."""
    return W.lathe([(t * MM, r * MM) for t, r in prof], seg, axis, tuple(a * MM for a in at), name, False,
                   fillet * MM, fseg)


def tr(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    geo.transform(ob, loc=tuple(a * MM for a in loc), rot=rot, scale=scale)
    return ob


def smooth01(t):
    return CH9.smoothstep(t)


def finish(ob, mid, bone, smooth=50.0):
    """Finish a part like weapons.P but safe after booleans and bevels: weld coincident vertices first (a bevel clamped to
    zero width leaves doubled vertices; deleting those faces, as P does, would open the shell), drop degenerate faces,
    smooth by angle, area-weighted normals, the material id and the rigid bone."""
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
            v = float(BONE_ID.get(bone, 0))
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


# ----------------------------------------------------------------------------------------------- MI-R rail

def mi_profile(flip=False):
    """MI-R cross section (y, z) relative to the lug-top plane (reference plane, z = 0, lugs reach down to -12):
    21.2 mm across the 45 degree flanks, 15.6 mm base, 12 mm lugs, slots cut down to -5.4 (the standard shared
    with the parts kit and copied from the CHOPPER's rail). flip: the lugs hang down (rail under the gun)."""
    p = [(-7.8, -12.0), (7.8, -12.0), (7.8, -6.4), (10.6, -3.7), (10.6, -2.7), (7.8, 0.0), (-7.8, 0.0), (-10.6, -2.7),
         (-10.6, -3.7), (-7.8, -6.4)]
    if flip:
        p = [(y, -z) for y, z in p][::-1]
    return p


def mi_rail(x0, lugs, zref, flip=False, name="Rail", bevel=0.25):
    """MI-R rail: `lugs` lugs of 5.3 mm with 5.3 mm slots between them from x0 (mm), the lug tops (or, flipped, the lug
    undersides) on the plane zref. Returns the object (a prism with the slots cut, edges broken 0.25 mm)."""
    n_slots = lugs - 1
    length = lugs * LUG + n_slots * LUG
    pts = [(y, z + zref) for y, z in mi_profile(flip)]
    rail = pr(pts, x0, x0 + length, axis="X", bevel=bevel, seg=1, name=name)
    floor = -5.4
    for k in range(n_slots):
        a = x0 + LUG + k * PITCH
        if not flip:
            c = bx(a, a + LUG, -14, 14, zref + floor, zref + 5)
        else:
            c = bx(a, a + LUG, -14, 14, zref - 5, zref - floor)
        W.cut(rail, c)
    W.round_edges(rail, bevel * MM, 1, 50)
    return rail


# ----------------------------------------------------------------------------------------------- body

def cheek(x):
    """Cheek rise over the rear top: +6 mm between X 34 and 110 (smooth ramps)."""
    return 6.0 * float(smooth01((x - 34.0) / 20.0) * (1.0 - smooth01((x - 90.0) / 20.0)))


def body_ring(w, zb, zt, c=4.0, rb=3.5):
    """(y, z) ring in mm, counter-clockwise: flat bottom with R 3.5 corners, vertical flanks, 4 mm top chamfers."""
    corners = [(-w, zb), (w, zb), (w, zt - c), (w - c, zt), (-(w - c), zt), (-w, zt - c)]
    return CH9.rpoly(corners, [rb, rb, 2.6, 2.6, 2.6, 2.6], [4, 4, 3, 3, 3, 3], [4, 3, 1, 4, 1, 3])


def body_stations():
    extra = [34, 40, 46, 52, 60, 70, 80, 92, 100, 110, 118, 150, 180, 232, 300, 330, 400]
    return CH9.stations(BODY_X0, BODY_X1, 22.0, 2.2, 4, extra=extra)


def body_solid():
    xs = body_stations()
    polys = []
    for x in xs:
        d = CH9.end_inset(x, BODY_X0, BODY_X1, 2.2)
        ring = body_ring(BODY_W, BODY_ZB, BODY_ZT + cheek(x))
        polys.append(CH9.offset(ring, -d) * MM)
    return CH9.loft_polys(polys, np.asarray(xs) * MM, "Body")


def port_cutter(y1=-8.0):
    """The ejection port through the right flank (60 x 32 mm, R 4). y1: how far in the cutter reaches (-25 for the forend,
    whose 4 mm wall is all it must go through)."""
    x0, x1, z0, z1 = PORT
    return pr([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], -44.0, y1, "Y", bevel=0.0, fillet=4.0, name="Port")


def slot_cutter():
    x0, x1, z0, z1 = SLOT
    return pr([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], 8.0, 44.0, "Y", bevel=0.0, fillet=5.8, name="Slot")


def cavity_cutter():
    x0, x1, y0, y1, z0, z1 = CAV
    return bx(x0, x1, y0, y1, z0, z1, bevel=1.2, name="Cavity")


def well_cutter():
    x0, x1, y0, y1, z0, z1 = WELL
    return bx(x0, x1, y0, y1, z0, z1, bevel=0.8, name="Well")


def build_body():
    """The moulded clamshell body with the ejection port, the bolt slot, the magazine well and the trigger slot cut,
    the carrier cavity inside; interior faces get the dark interior id."""
    b = body_solid()
    W.cut(b, port_cutter(), slot_cutter(), cavity_cutter())
    W.cut(b, well_cutter())
    W.cut(b, bx(351.0, 381.0, -5.5, 5.5, -64.0, -41.0, bevel=0.6, name="TrigSlot"))
    W.round_edges(b, 0.5 * MM, 2, 50)
    # shallow moulded recesses: a marking panel (right), the serial panel (left) and the hold-open thumb recess (left)
    W.cut(b, pr([(188, -38), (322, -38), (322, -14), (188, -14)], -29.0, -27.5, "Y", bevel=0, fillet=4.0, name="PanelR"))
    W.cut(b, pr([(44, -34), (112, -34), (112, -24), (44, -24)], 27.5, 29.0, "Y", bevel=0, fillet=3.0, name="PanelL"))
    W.cut(b, pr([(326, -15), (358, -15), (358, -7), (326, -7)], 27.1, 29.0, "Y", bevel=0, fillet=3.4, name="HoldOpen"))
    W.round_edges(b, 0.16 * MM, 1, 50)
    return b


# ----------------------------------------------------------------------------------------------- butt pad

def pad_x0(z):
    """Rear face of the pad: R 120 in side view with its apex at the middle (Z -13), 6 mm chamfer at the heel."""
    zz = np.asarray(z, dtype=np.float64)
    arc = 120.0 - np.sqrt(120.0 ** 2 - (zz + 13.0) ** 2)
    x_c = 120.0 - math.sqrt(120.0 ** 2 - 59.0 ** 2)                 # arc at Z 46
    x_t = 120.0 - math.sqrt(120.0 ** 2 - 65.0 ** 2) + 6.0           # 6 mm forward of the top corner
    ch = x_c + (zz - 46.0) * (x_t - x_c) / 6.0
    return np.where(zz > 46.0, np.maximum(arc, ch), arc)


def build_pad():
    """Rubber butt pad: horizontal sections lofted from the toe to the heel, rear face R 120 (side view), 38 wide with
    R 6 rear corners and a slight crown across, edges rounded 2.5 mm, 4 mm lanyard hole through the toe."""
    zs = list(np.linspace(-78.0, 52.0, 27))
    for k in range(1, 5):                                   # round the toe and the heel
        f = 1.0 - math.cos(k / 4.0 * math.pi / 2.0)
        zs += [-78.0 + 2.5 * f, 52.0 - 2.5 * f]
    zs += [46.0, 47.5, 49.0, 50.5]
    zs = np.array(sorted(set(np.round(zs, 4))))
    secs, zz = [], []
    for z in zs:
        d = 0.0
        e = min(z + 78.0, 52.0 - z)
        if e < 2.5:
            d = 2.5 - math.sqrt(max(0.0, 2.5 ** 2 - (2.5 - e) ** 2))
        x0 = float(pad_x0(z)) + d + 1.4                    # the crown across the width brings the middle back to the arc
        secs.append(K.rrect(x0 * MM, 31.0 * MM, (19.0 - d) * MM, 6.0 * MM, 2.0 * MM, bulge_b=1.4 * MM))
        zz.append(z * MM)
    pad = K.loft_z(secs, zz, 72, name="Pad")
    hole = lt([(-30, 0), (-30, 2.0), (30, 2.0), (30, 0)], 20, axis="Y", at=(25.5, 0.0, -68.0), name="Lanyard")
    W.cut(pad, hole)
    return pad


# ----------------------------------------------------------------------------------------------- handle

HANDLE_OUT = [(118, 46), (118, 70), (121, 79), (128, 85.5), (136, 88), (319, 88), (326.5, 84), (330, 76), (330, 46)]
WINDOW = (150.0, 300.0, 52.0, 76.0)


def build_handle():
    """The integral carry handle: an arch moulded with the body (34 wide), a 150 x 24 window under the bar, the 20 mm
    ring and the 9 mm rear aperture at X 134, Z 60 (the sight line), the sight port through the front leg, the MI-R rail
    on the bar."""
    h = pr(HANDLE_OUT, -17.0, 17.0, "Y", bevel=1.6, seg=3, fillet=5.0, name="Handle")
    x0, x1, z0, z1 = WINDOW
    win = pr([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], -30.0, 30.0, "Y", bevel=0.0, fillet=6.0, name="Window")
    W.cut(h, win)
    ring = lt([(114.0, 0), (114.0, 9.0), (115.0, 10.0), (118.5, 10.0), (118.5, 0)], 40, "X", at=(0, 0, 60.0), name="Ring",
              fillet=0.4)
    port = bx(294.0, 336.0, -9.0, 9.0, 53.0, 67.0, bevel=0.0, name="SightPort")
    W.cut(h, port)
    for tgt in (h, ring):
        ap = lt([(108.0, 0), (108.0, 7.2), (118.0, 6.4), (126.0, 5.0), (131.0, 4.5), (137.0, 4.5), (146.0, 7.0), (152.0, 9.5),
                 (152.0, 0)], 48, "X", at=(0, 0, 60.0), name="Aperture")
        W.cut(tgt, ap)
    W.round_edges(ring, 0.3 * MM, 1, 50)
    W.round_edges(h, 0.5 * MM, 2, 50)
    return h, ring


def build_gussets():
    """Moulded blends where the handle legs meet the body top (the legs are moulded with the body)."""
    out = []
    for tri in ([(109, 50), (118, 50), (118, 59)], [(330, 50), (339, 50), (330, 59)]):
        out.append(pr(tri, -17.0, 17.0, "Y", bevel=0.6, seg=2, name="Gusset"))
    return out


def build_rail_top():
    return mi_rail(RAIL_TOP["x0"], RAIL_TOP["lugs"], RAIL_TOP["zref"], False, "RailTop")


# ----------------------------------------------------------------------------------------------- forend

def fore_ring(w, zb, zt, r=2.5):
    corners = [(-w, zb), (w, zb), (w, zt), (-w, zt)]
    return CH9.rpoly(corners, [r] * 4, [3] * 4, [3, 3, 3, 3])


def build_forend():
    """Blocky ventilated forend (hollow): 62 x 74 mm, 2 mm edge radii, twelve 5 x 14 slots per side, the carrier cavity
    continuing into it, MI-R rail under it, the barrel passing through a 22 mm hole in its front wall."""
    xs = CH9.stations(FORE_X0, FORE_X1, 25.0, 2.0, 4, extra=[396.0, 440.0, 560.0, 584.0])
    polys = []
    for x in xs:
        d = CH9.end_inset(x, FORE_X0, FORE_X1, 2.0)
        polys.append(CH9.offset(fore_ring(FORE_W, FORE_ZB, FORE_ZT), -d) * MM)
    f = CH9.loft_polys(polys, np.asarray(xs) * MM, "Forend")
    cav = pr([(-27, -36), (27, -36), (27, 30), (-27, 30)], 395.0, 584.0, "X", bevel=0.0, fillet=2.0, name="ForeCavity")
    W.cut(f, cav)
    W.cut(f, cavity_cutter(), port_cutter(-25.0))
    W.cut(f, lt([(578, 0), (578, 11.2), (592, 11.2), (592, 0)], 48, "X", name="BarrelHole"))
    for xc in VENT_COLS:
        for zc in VENT_ROWS:
            s = pr([(xc - 2.5, zc - 7.0), (xc + 2.5, zc - 7.0), (xc + 2.5, zc + 7.0), (xc - 2.5, zc + 7.0)], -40.0, 40.0,
                   "Y", bevel=0.0, fillet=2.3, fseg=3, name="Vent")
            W.cut(f, s)
    W.round_edges(f, 0.45 * MM, 2, 50)
    return f


def build_nose_ring():
    """Steel bushing round the barrel where it leaves the forend."""
    return W.lathe([(589.0 * MM, 10.0 * MM), (589.0 * MM, 14.4 * MM), (591.8 * MM, 14.4 * MM), (593.4 * MM, 12.8 * MM),
                    (593.4 * MM, 10.0 * MM)], 56, "X", (0, 0, 0), "NoseRing", True, 0.3 * MM, 2)


def build_rail_under():
    return mi_rail(RAIL_UNDER["x0"], RAIL_UNDER["lugs"], RAIL_UNDER["zref"], True, "RailUnder")


# ----------------------------------------------------------------------------------------------- barrel, gas, hider

def build_barrel():
    """Barrel: chamber ring at the breech, R 9.5 to the thread shoulder at X 652, the R 8.5 threaded stub to X 664
    (six turns modelled as ridges), crowned and bored R 2.8 from the muzzle end."""
    prof = [(397.0, 0.0), (397.0, 11.0), (400.0, 11.5), (412.0, 11.5), (414.0, 9.5), (651.0, 9.5), (652.0, 8.9),
            (652.0, 8.5)]
    pitch, r_valley, r_peak = 2.0, 8.05, 8.5
    x = 652.0
    for k in range(6):
        prof += [(x + 0.2 + k * pitch, r_valley), (x + 0.5 + k * pitch, r_peak), (x + 1.3 + k * pitch, r_peak),
                 (x + 1.6 + k * pitch, r_valley)]
    prof += [(664.0, 8.05), (664.0, 7.2), (664.0 - 0.4, 6.8), (664.0 - 0.4, 2.8), (600.0, 2.8), (600.0, 0.0)]
    b = lt(prof, 64, name="Barrel")
    return b


def build_gas(piston=True):
    """Short-stroke gas system seen through the forend's slots: gas block on the barrel, gas tube above it running
    back into the receiver, the piston rod and a handguard retaining ring at the front."""
    parts = []
    blk = lt([(512.0, 0.0), (512.0, 13.5), (514.0, 15.0), (538.0, 15.0), (540.0, 13.5), (540.0, 0.0)], 56, name="GasBlock",
             fillet=0.8)
    parts.append(blk)
    saddle = pr([(520.0, 8.0), (534.0, 8.0), (534.0, 22.0), (520.0, 22.0)], -7.5, 7.5, "Y", bevel=0.8, name="GasSaddle")
    parts.append(saddle)
    tube = lt([(399.0, 0.0), (399.0, 4.3), (400.0, 4.8), (524.0, 4.8), (524.0, 0.0)], 32, at=(0.0, 0.0, 17.0),
              name="GasTube")
    parts.append(tube)
    return parts


def build_hider():
    """Squat six-slot birdcage flash hider, X 652..700, R 12.5, bore R 2.8, one closed shell on its own bone."""
    h = lt([(652.0, 0.0), (652.0, 11.5), (653.0, 12.5), (656.0, 12.5), (656.0, 11.6), (657.8, 11.6), (657.8, 12.5), (698.5, 12.5),
            (700.0, 11.0), (700.0, 0.0)], 64, name="Hider", fillet=0.3)
    W.cut(h, lt([(651.0, 0.0), (651.0, 8.9), (655.0, 8.9), (655.0, 9.3), (693.0, 9.3), (694.0, 7.0), (694.0, 0.0)], 56,
                name="HiderCavity"))
    W.cut(h, lt([(690.0, 0.0), (690.0, 2.8), (701.0, 2.8), (701.0, 0.0)], 24, name="HiderBore"))
    for k in range(6):
        c = bx(662.0, 690.0, -1.8, 1.8, 6.0, 16.0, bevel=0.0, name="HiderSlot")
        W.cut(h, tr(c, rot=(k * 60.0, 0, 0)))
    # crown chamfer at the front, collar groove at the rear
    W.round_edges(h, 0.4 * MM, 2, 50)
    return h


# ----------------------------------------------------------------------------------------------- front sight

def build_front_sight():
    """The front sight tower on the forend nose: dovetail base, post (tip X 575, Z 60 = SightFront), two 3 mm guard
    ears, a 2 mm tritium insert in the post's rear face; all on bone IronsFront."""
    parts = []
    base = pr([(561.0, 33.0), (589.0, 33.0), (589.0, 41.0), (584.0, 46.0), (566.0, 46.0), (561.0, 41.0)], -10.0, 10.0, "Y",
              bevel=0.8, seg=2, fillet=1.0, name="TowerBase")
    parts.append(base)
    post = pr([(573.0, 45.0), (577.0, 45.0), (577.0, 59.0), (576.4, 60.0), (573.6, 60.0), (573.0, 59.0)], -1.2, 1.2, "Y",
              bevel=0.25, seg=1, name="Post")
    parts.append(post)
    for s in (1, -1):
        ear = pr([(566.0, 44.0), (584.0, 44.0), (583.0, 60.0), (581.0, 64.5), (569.0, 64.5), (567.0, 60.0)],
                 s * 5.2, s * 8.2, "Y", bevel=0.4, seg=2, fillet=1.2, name="Ear")
        parts.append(ear)
    return parts
