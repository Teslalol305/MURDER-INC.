"""Round 4, lane 2: the parts kit, geometry (optics, muzzle devices, grips, laser). Our own shapes, no maker's marks.

Every part is built once, in the frame of its mount: the origin is the mount (the centre of an MI-R clamp footprint on the
lug tops, the gun's muzzle mount on the bore, the underside plane of an underbarrel rail ...), X forward along the bore,
Y left, Z up, metres. Builders return (objects, sockets): objects whose faces carry `mid` (the surface recipe of
`_weapons_parts_tex.py`) and `part` (the part's index in the atlas); `weapons_parts.py` joins, unwraps, textures and
exports them.

MI-R rail (the CHOPPER's measured top rail; the SHORTY, STRETCH and RATTLER cut the same): 21.2 mm across the dovetail's
widest point, a 45 deg top chamfer, a neck 15.6 mm wide 6 mm under the lug top, lugs 5.3 mm every 10.6 mm, slot floors
5.4 mm under the lug tops. A clamp is a base plate on the lug face (the reference plane) with two jaws hooked under the
dovetail's shoulders and a clamp screw on the right: a 0.15 mm gap to the flanks and no key in a slot, so the part seats on
any MI-R rail whatever X it is placed at.
"""
import math

import numpy as np

from mi import geo
from assets import weapons as W

MM = 0.001

# surface recipes (face attribute `mid`); lens and reticle faces become their own slots (flat materials in Unreal)
(AL, STEELD, HEAT, STAIN, POLY, RUBBER, WOODG, BRASSM, RED, CARBON, LENS, RET, GOLDM, MAGST, MAGPOLY, COPPERM, BORED,
 STEELB) = range(18)
LENS_SLOT, RET_SLOT = "M_Part_Lens", "M_Part_Reticle"


def mm(*v):
    return tuple(float(x) * MM for x in v)


# --------------------------------------------------------------------------------------------------- finishing
def fin(ob, mid, part=0, smooth=50.0):
    """Finish a piece: clean, shade smooth with sharp edges over `smooth` degrees, area-weighted normals, `mid` and `part`
    face attributes. No bone: the parts are static meshes."""
    W.clean(ob)
    geo.smooth_by_angle(ob, smooth)
    geo.weighted_normals(ob)
    me = ob.data
    for nm, v in (("mid", float(mid)), ("part", float(part))):
        a = me.attributes.get(nm) or me.attributes.new(nm, "FLOAT", "FACE")
        a.data.foreach_set("value", np.full(len(me.polygons), v, np.float32))
    return ob


def retag(ob, mid, where):
    """Give the faces whose centre satisfies where(cx, cy, cz) (arrays, metres) the recipe `mid`."""
    me = ob.data
    n = len(me.polygons)
    c = np.empty(n * 3, np.float32)
    me.polygons.foreach_get("center", c)
    c = c.reshape(-1, 3)
    cur = np.empty(n, np.float32)
    me.attributes["mid"].data.foreach_get("value", cur)
    sel = where(c[:, 0], c[:, 1], c[:, 2])
    cur[sel] = float(mid)
    me.attributes["mid"].data.foreach_set("value", cur)
    return ob


def lathe_x(prof_mm, seg=64, at=(0, 0, 0), closed=False, fillet=0.0, fseg=2, name="Lathe"):
    """Surface of revolution about the X axis through `at` (mm) from a profile [(x, r)] in mm."""
    return W.lathe([(x * MM, r * MM) for x, r in prof_mm], seg, axis="X", at=mm(*at), closed=closed,
                   fillet=fillet * MM, fseg=fseg, name=name)


def lathe_y(prof_mm, seg=48, at=(0, 0, 0), closed=False, fillet=0.0, fseg=2, name="LatheY"):
    """About a horizontal axis along +Y through `at` (mm); the profile is [(y, r)]."""
    return W.lathe([(y * MM, r * MM) for y, r in prof_mm], seg, axis="Y", at=mm(*at), closed=closed,
                   fillet=fillet * MM, fseg=fseg, name=name)


def lathe_z(prof_mm, seg=48, at=(0, 0, 0), closed=False, fillet=0.0, fseg=2, name="LatheZ"):
    """About a vertical axis through `at` (mm); the profile is [(z, r)]."""
    return W.lathe([(z * MM, r * MM) for z, r in prof_mm], seg, axis="Z", at=mm(*at), closed=closed,
                   fillet=fillet * MM, fseg=fseg, name=name)


def box_mm(x0, x1, y0, y1, z0, z1, bevel=0.5, seg=2, name="Box"):
    return W.box(x0 * MM, x1 * MM, y0 * MM, y1 * MM, z0 * MM, z1 * MM, bevel=bevel * MM, seg=seg, name=name)


def prism_yz(poly_mm, x0, x1, bevel=0.3, seg=2, name="PrismX", fillet=0.0):
    """Outline in (y, z) mm extruded along X from x0 to x1 (mm)."""
    return W.prism([(y * MM, z * MM) for y, z in poly_mm], x0 * MM, x1 * MM, axis="X", bevel=bevel * MM, seg=seg,
                   name=name, fillet=fillet * MM)


def prism_xz(poly_mm, y0, y1, bevel=0.3, seg=2, name="PrismY", fillet=0.0):
    """Side-view outline in (x, z) mm extruded along Y from y0 to y1 (mm)."""
    return W.prism([(x * MM, z * MM) for x, z in poly_mm], y0 * MM, y1 * MM, axis="Y", bevel=bevel * MM, seg=seg,
                   name=name, fillet=fillet * MM)


def prism_xy(poly_mm, z0, z1, bevel=0.3, seg=2, name="PrismZ", fillet=0.0):
    """Top-view outline in (x, y) mm extruded along Z from z0 to z1 (mm)."""
    return W.prism([(x * MM, y * MM) for x, y in poly_mm], z0 * MM, z1 * MM, axis="Z", bevel=bevel * MM, seg=seg,
                   name=name, fillet=fillet * MM)


def move(ob, dx=0.0, dy=0.0, dz=0.0):
    geo.transform(ob, loc=(dx * MM, dy * MM, dz * MM))
    return ob


def ring_x(radius_fn, xs_mm, m=96, at=(0, 0, 0), cap0=True, cap1=True, name="RingLoft"):
    """Loft of rings about the X axis: radius_fn(x_mm, theta) -> radius in mm; cross-sections at xs_mm (m points each)."""
    th = np.linspace(0.0, 2 * math.pi, m, endpoint=False)
    secs = []
    for x in xs_mm:
        r = np.array([radius_fn(x, t) for t in th]) * MM
        secs.append(np.stack([np.full(m, (x + at[0]) * MM), at[1] * MM + r * np.cos(th), at[2] * MM + r * np.sin(th)], 1))
    return W.loft(np.array(secs), closed=True, cap0=cap0, cap1=cap1, name=name)


def axis_to_z(ob, at):
    """An X-axis object (base at X = 0) turned to stand on +Z at `at` (mm)."""
    geo.transform(ob, rot=(0, -90, 0))
    return move(ob, *at)


def axis_to_ny(ob, at):
    """An X-axis object turned to point along -Y (the right side) from `at` (mm)."""
    geo.transform(ob, rot=(0, 0, 90))
    geo.transform(ob, scale=(1, -1, 1))
    return move(ob, *at)


def axis_to_py(ob, at):
    geo.transform(ob, rot=(0, 0, 90))
    return move(ob, *at)


def knurled(r, h, teeth, depth, chamfer=0.5, name="Knurl", dome=0.0):
    """A knurled cylinder along +X from 0 to h (mm): `teeth` shallow scallops of `depth`, chamfered ends (the radius
    function of one ring: smooth cosine teeth between the chamfers)."""
    def rad(t, th):
        k = 0.5 + 0.5 * math.cos(teeth * th)
        e = min(1.0, max(0.0, min(t, h - t) / max(chamfer, 1e-6)))
        base = r - chamfer * (1.0 - e)
        return base - depth * k * e + (dome * (1 - ((2 * t - h) / h) ** 2) if dome else 0.0)
    xs = sorted(set([0.0, chamfer, h - chamfer, h]))
    return ring_x(rad, xs, m=teeth * 3, name=name)


def flutes(depth, n, width_frac=0.55):
    """Radius offset (mm, <= 0) of n shallow flutes around a tube: smooth scallops `width_frac` of the pitch wide."""
    def f(theta):
        u = (theta * n / (2 * math.pi)) % 1.0 - 0.5            # -0.5 .. 0.5 across one pitch
        a = abs(u) / (width_frac / 2.0)
        return -depth * (0.5 + 0.5 * math.cos(math.pi * min(a, 1.0))) if a < 1.0 else 0.0
    return f


def screw_head_y(x, z, y, r=2.1, h=1.0, sign=-1, seg=20, name="Screw"):
    """A socket-head cap screw on a side face (axis Y), base at y, head standing `h` toward sign (-1: toward -Y); mm."""
    prof = [(0.0, 0.0), (0.0, r), (h * 0.75, r), (h, r * 0.84), (h, r * 0.48), (h * 0.45, r * 0.48), (h * 0.45, 0.0)]
    ob = lathe_y(prof, seg, at=(x, 0.0, z), fillet=0.1 if seg > 16 else 0.0, fseg=1, name=name)
    if sign < 0:
        geo.transform(ob, scale=(1, -1, 1))
    return move(ob, 0, y, 0)


def screw_head_z(x, y, z, r=2.1, h=1.0, sign=1, seg=24, name="ScrewZ"):
    """A socket-head screw on a horizontal face (axis Z), base at z, head toward sign (+1 up); mm."""
    prof = [(0.0, 0.0), (0.0, r), (h * 0.75, r), (h, r * 0.84), (h, r * 0.48), (h * 0.45, r * 0.48), (h * 0.45, 0.0)]
    ob = lathe_z(prof, seg, at=(x, y, 0.0), fillet=0.1, fseg=1, name=name)
    if sign < 0:
        geo.transform(ob, scale=(1, 1, -1))
    return move(ob, 0, 0, z)


def reticle_plane(size_mm, axis_z, pi, name="Reticle"):
    """The reticle: a 2-triangle plane at X 0, size x size mm on the optical axis, its face toward the eye (-X)."""
    h = size_mm / 2.0 * MM
    v = np.array([(0.0, -h, axis_z * MM - h), (0.0, h, axis_z * MM - h), (0.0, h, axis_z * MM + h), (0.0, -h, axis_z * MM + h)])
    ob = geo.from_arrays(name, v, [(0, 3, 2, 1)], smooth=None)
    ob.data.polygons[0].flip() if ob.data.polygons[0].normal.x > 0 else None
    return fin(ob, RET, pi)


# ------------------------------------------------------------------------------------------------------ MI-R clamp
RAIL_HW = 10.6                  # half width of the widest point of the guns' MI-R dovetail (3 mm under the lug face)
JAW_GAP = 0.15
FACE_GAP = 0.03                 # the plate rides 0.03 mm over the lug face (no coplanar contact)


def jaw_poly():
    """Half cross-section (y >= 0, z) of one clamp jaw for a rail whose lug face is the z = 0 plane and whose body is at
    z < 0 (a top rail: the part grows to +z); mirror z for an underside rail. Measured on the five guns: the CHOPPER's, the
    SHORTY's and the RATTLER's dovetail has a 45 deg top chamfer (half width 7.6 at the lug face to 10.6 at 3 mm) and an
    undercut to 7.8 below 6.5 mm; the STRETCH's rail has the same chamfer (7.86 to 10.6) and straight flanks at 10.6 below
    it. No jaw can hook under the shoulder of one without crossing the other, so the jaws are side walls that follow the
    chamfer (0.15 mm gap) and hold the rail's flanks down to 7.5 mm; the clamp screw does the clamping."""
    g = JAW_GAP
    env = [(7.86, 0.0), (8.36, -0.5), (8.86, -1.0), (9.37, -1.5), (9.88, -2.0), (10.40, -2.5), (RAIL_HW, -3.0)]   # the envelope of the guns' profiles
    return [(y + g, z) for y, z in env] + [(RAIL_HW + g, -7.5), (13.4, -7.5), (13.4, 1.5), (env[0][0] + g, 1.5)]


def clamp(length, part=0, x0=None, under=False, plate_t=6.0, knob=True, name="Clamp", mid=AL, jaw_mid=STEELD, width=26.8,
          screws=0):
    """MI-R clamp footprint `length` mm long centred on X = 0 (or starting at x0): plate on the lug face (z 0.03..plate_t, or
    mirrored for an underside rail), two jaws along the dovetail's flanks, a clamp screw knob on the right, optional extra
    hex screws (`screws`) along the right jaw. Returns finished objects."""
    s = -1.0 if under else 1.0
    xa = (-length / 2.0) if x0 is None else x0
    xb = xa + length
    out = []
    z0, z1 = (FACE_GAP, plate_t) if not under else (-plate_t, -FACE_GAP)
    out.append(fin(box_mm(xa, xb, -width / 2, width / 2, z0, z1, bevel=0.9, name=name + "Plate"), mid, part))
    for side in (1, -1):
        pts = [(side * y, s * z) for y, z in jaw_poly()]
        out.append(fin(prism_yz(pts, xa + 1.2, xb - 1.2, bevel=0.35, name=name + "Jaw"), jaw_mid, part))
    if knob:
        kx = 0.5 * (xa + xb) if screws == 0 else xa + 0.30 * (xb - xa)
        out.append(fin(axis_to_ny(knurled(4.5, 5.2, 20, 0.35, 0.6, name=name + "Knob"), (kx, -width / 2, s * -4.0)), jaw_mid, part))
    for k in range(screws):
        sx = xa + (0.62 + 0.26 * k) * (xb - xa)
        out.append(fin(screw_head_y(sx, s * -4.0, -width / 2, r=2.3, h=1.4, sign=-1, seg=16, name=name + "Bolt"), STEELD, part))
    return out


# --------------------------------------------------------------------------------------------------- RED DOT
def red_dot(pi=0):
    """Compact enclosed red dot (tube sight): clamp 52 x 21.2 mm, body tube R 16.5 on axis Z +24.5, X -32..+32 (rear hood,
    front window), elevation cap (top Z 47), windage cap on the right, battery cap on the front top.
    SightEye (-32.5, 0, 24.5) on the optical axis."""
    AX = 24.5
    objs = clamp(52.0, part=pi, name="RD")
    prof = [(-32.0, 14.3), (-32.0, 17.6), (-31.2, 18.3), (-26.0, 18.3), (-23.5, 16.5), (31.2, 16.5), (32.0, 15.7), (32.0, 14.3)]
    body = lathe_x(prof, 72, at=(0, 0, AX), closed=True, fillet=0.35, fseg=1, name="RDBody")
    fin(body, AL, pi)
    retag(body, BORED, lambda x, y, z: (np.hypot(y, z - AX * MM) < 14.4 * MM) & (np.abs(x) < 31.5 * MM))
    objs.append(body)
    objs.append(fin(box_mm(-23.0, 21.0, -9.0, 9.0, 5.0, 11.0, bevel=1.0, name="RDNeck"), AL, pi))
    objs.append(fin(box_mm(-9.5, 16.5, -8.5, 8.5, 38.5, 43.0, bevel=1.4, name="RDTop"), AL, pi))
    # elevation turret (X +4): knurled cap R 5, top at Z 47
    objs.append(fin(axis_to_z(knurled(5.2, 4.0, 24, 0.3, 0.45, name="RDElev"), (4.0, 0.0, 43.0)), STEELD, pi))
    objs.append(fin(axis_to_ny(knurled(4.8, 4.0, 24, 0.3, 0.45, name="RDWind"), (4.0, -16.3, AX)), STEELD, pi))
    objs.append(fin(screw_head_y(4.0, AX, 16.3, r=3.0, h=1.0, sign=+1, name="RDPlug"), STEELD, pi))
    # battery cap on the front top (X +24), knurled with a coin slot
    bat = axis_to_z(knurled(6.8, 2.6, 28, 0.3, 0.5, name="RDBat"), (24.0, 0.0, 40.6))
    W.cut(bat, box_mm(21.0, 27.0, -0.8, 0.8, 42.0, 44.0, bevel=0.0, name="RDSlot"))
    objs.append(fin(bat, STEELD, pi))
    for sx in (-4.0, 12.0):                                    # two screws on the top housing
        for sy in (-5.2, 5.2):
            objs.append(fin(screw_head_z(sx, sy, 43.0, r=1.5, h=0.8, sign=1, seg=12, name="RDTopScrew"), STEELD, pi))
    # lenses in both windows and the reticle plane at X 0
    for x, nm in ((-30.4, "RDLensR"), (30.2, "RDLensF")):
        d = lathe_x([(x - 0.8, 0.0), (x - 0.8, 14.15), (x + 0.8, 14.15), (x + 0.8, 0.0)], 64, at=(0, 0, AX), fillet=0.2, fseg=1, name=nm)
        objs.append(fin(d, LENS, pi))
    objs.append(reticle_plane(10.0, AX, pi, "RDRet"))
    return objs, {"SightEye": mm(-32.5, 0, AX)}
