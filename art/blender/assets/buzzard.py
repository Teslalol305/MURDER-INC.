"""The Buzzard: the Vultures' armed heavy-lift quadcopter (skinned SK_Buzzard), its rotor blur disc and tracer
bolt (effects meshes) and the broken-up wreck (static pieces).

Briefs: docs/unreal/spec/assets/characters.json (buzzard, buzzard_rotor_blur, buzzard_bolt, buzzard_wreck),
behaviour in docs/unreal/spec/03-enemies.md 3.8 and 5.4; web mesh src/enemies/buzzard-model.js.

Drone space = Blender space: nose +X, up +Z, the drone's left +Y (the brief's 'right' values change sign on Y:
the gun hangs on -Y, the red port light sits at +Y). Origin at the centre of the airframe. Every position below
is a brief number (or the web mesh's, converted with (x, y, z)_blender = (-z, -x, y)_web).

    build.py build buzzard --bake --export --preview         # everything (4K bake: geometry maps + numpy layers)
    build.py build buzzard --res 512 --bake --export         # draft sets (every set at 1/8 size)
    MI_PREVIEWS=buzzard_hero,buzzard_wire build.py build buzzard --preview

Textures are authored like the weapons' (assets/weapons.py, mi/texpaint.py): geometry maps baked once through
the unique UVs, every layer computed in numpy from the 3D position (carbon twill along each arm, chipped
oxblood paint, anodising with machined edges, oil thrown back from the motors, dust in the recesses).
"""
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import bake, export, geo, mat, paths, render, rig, scene
from mi import texpaint as tp
from assets import weapons as W

FAMILY = {"name": "buzzard", "description": "The Buzzard quadcopter (skinned SK_Buzzard), rotor blur, bolt, wreck pieces"}
GROUPS = ("drone", "fx", "wreck")

# material ids (face attribute 'mid'): one unique set, the id picks the surface recipe
(HULL, DECK, OXBLOOD, CARBON, PROPC, ANOD, ALU, GUN, BARREL, STEEL, COPPER, RUBBER, SKID, WIRE_R, WIRE_K, NYLON,
 XT90, BATTERY, STRAP, LENS, LED_R, LED_G, LED_W, MAGNET, STATOR, BALL, GLASS_K, BORE, SLEEVE, BRASS, TAPE) = range(31)
EMISSIVE = {LENS: "M_Buzzard_Eye", LED_R: "M_Buzzard_Strobe", LED_G: "M_Buzzard_Strobe", LED_W: "M_Buzzard_Strobe"}

prism, lathe, box, cut, union, round_edges, clean, loft, fix_normals = (
    W.prism, W.lathe, W.box, W.cut, W.union, W.round_edges, W.clean, W.loft, W.fix_normals)

# ---------------------------------------------------------------------------------------------- brief numbers
BZ = {
    "hubs": {"fl": (0.27, 0.33, 0.075), "fr": (0.27, -0.33, 0.075), "rl": (-0.30, 0.35, 0.075), "rr": (-0.30, -0.35, 0.075)},
    "ccw": {"fl": True, "rr": True, "fr": False, "rl": False},      # diagonal pairs turn the same way (web rotors 0, 3)
    "prop_r": 0.185, "chord": 0.034, "blade_z": 0.092, "blur_lift": 0.022,
    "gimbal": (0.17, 0.0, -0.085), "ball": (0.19, 0.0, -0.10), "ball_r": 0.062,
    "eye": (0.255, 0.0, -0.10), "lens_r": 0.036, "ring_r": 0.045,
    "muzzle": (0.37, -0.062, -0.13), "gun_c": (0.26, -0.062, -0.13), "ammo_c": (0.19, -0.055, -0.17),
    "strobe_port": (0.33, 0.36, 0.02), "strobe_star": (0.33, -0.36, 0.02), "strobe_tail": (-0.47, 0.0, 0.09),
    "skid_y": 0.13, "skid_z": -0.16, "skid_x": (-0.23, 0.17), "strut_x": (0.10, -0.16),
}
PROP_BONES = {"fl": "prop_fl", "fr": "prop_fr", "rl": "prop_rl", "rr": "prop_rr"}


def lin(h):
    return W.hexlin(h)


# ------------------------------------------------------------------------------------------------ modelling kit

def xform(ob, M):
    ob.data.transform(M)
    if M.determinant() < 0:
        ob.data.flip_normals()
    ob.data.update()
    return ob


def rot_z(deg):
    return Matrix.Rotation(math.radians(deg), 4, "Z")


def T(x, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def P(ob, mid, bone="body", grp=0, smooth=48.0):
    """weapons.P (clean, smooth by angle, weighted normals, 'mid' and 'part', rigid bone) plus 'grp' (wreck piece)."""
    W.P(ob, mid, bone, smooth)
    me = ob.data
    a = me.attributes.get("grp") or me.attributes.new("grp", "FLOAT", "FACE")
    a.data.foreach_set("value", np.full(len(me.polygons), float(grp), np.float32))
    return ob


def rrect(w, h, r, seg=4, cx=0.0, cy=0.0):
    pts = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]
    return [tuple(p[:2]) for p in geo.fillet(pts, min(r, 0.49 * min(w, h)), seg, closed=True)]


def ring_pts(n, rx, ry, cx=0.0, cy=0.0, phase=0.0):
    a = np.linspace(0, 2 * math.pi, n, endpoint=False) + phase
    return [(cx + rx * math.cos(t), cy + ry * math.sin(t)) for t in a]


def cyl(r, z0, z1, seg=24, at=(0, 0), fillet=0.0008, axis="Z", name="Cyl"):
    """Closed cylinder along an axis through `at` (the two other coordinates), rims rounded."""
    prof = [(0.0, z0), (r, z0), (r, z1), (0.0, z1)]
    ob = geo.revolve(geo.fillet(prof, min(fillet, 0.45 * r, 0.45 * abs(z1 - z0)), 2), seg, name=name)
    if axis == "X":
        geo.transform(ob, rot=(0, 90, 0))
        geo.transform(ob, loc=(0, at[0], at[1]))
    elif axis == "Y":
        geo.transform(ob, rot=(-90, 0, 0))
        geo.transform(ob, loc=(at[0], 0, at[1]))
    else:
        geo.transform(ob, loc=(at[0], at[1], 0))
    return fix_normals(ob)


def rev(prof, seg=32, at=(0, 0, 0), closed=False, fillet=0.0, fseg=2, name="Rev"):
    """Revolve an (r, z) profile around the vertical axis through `at`."""
    if fillet > 0:
        prof = geo.fillet(prof, fillet, fseg, closed=closed)
    ob = geo.revolve(prof, seg, closed=closed, name=name)
    geo.transform(ob, loc=at)
    return fix_normals(ob)


def tube_path(path, r, seg=10, name="Wire", bend=0.0, cap=True):
    pts = geo.fillet(path, bend, 4) if bend > 0 else path
    return fix_normals(geo.sweep(geo.circle_profile(r, seg), pts, cap=cap, name=name))


def band(path, w, t, name="Band"):
    """Thin flat band (strap, hose clamp, zip tie) swept round a closed path, its width across the path plane."""
    prof = rrect(t, w, t * 0.45, 2)
    return fix_normals(geo.sweep(prof, path, closed_path=True, closed_profile=True, cap=False, name=name))


def loop_path(w, h, r, seg=5):
    """Closed rounded-rectangle path in the (y, z) plane (x = 0), counter-clockwise."""
    return [(0.0, p[0], p[1]) for p in rrect(w, h, r, seg)]


def screw(head_r=0.0024, head_h=0.0016, button=True, seg=10):
    """Hex-socket screw head facing +Z, its seat at z = 0 (button or cap head)."""
    if button:
        prof = [(0.0, -0.0004), (head_r, -0.0004), (head_r, 0.0003), (head_r * 0.82, head_h * 0.75), (head_r * 0.45, head_h),
                (head_r * 0.42, head_h)]
    else:
        prof = [(0.0, -0.0004), (head_r, -0.0004), (head_r, head_h * 0.85), (head_r * 0.9, head_h), (head_r * 0.42, head_h)]
    sock = head_r * 0.40
    prof += [(sock, head_h), (sock, head_h * 0.35), (0.0, head_h * 0.35)]
    ob = geo.revolve(prof, seg, name="Screw")
    # hex socket: pull the socket ring onto a hexagon
    co = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    r = np.hypot(co[:, 0], co[:, 1])
    s = (np.abs(r - sock) < 1e-6) & (co[:, 2] < head_h * 1.01)
    a = np.arctan2(co[:, 1], co[:, 0])
    hexr = sock * math.cos(math.pi / 6) / np.cos(((a + math.pi / 6) % (math.pi / 3)) - math.pi / 6)
    co[s, 0] = hexr[s] * np.cos(a[s])
    co[s, 1] = hexr[s] * np.sin(a[s])
    ob.data.vertices.foreach_set("co", co.ravel())
    return fix_normals(ob)


def frame_to(point, normal, spin=0.0):
    """Matrix putting +Z on `normal` at `point`."""
    n = Vector(normal).normalized()
    q = Vector((0, 0, 1)).rotation_difference(n)
    return Matrix.Translation(point) @ q.to_matrix().to_4x4() @ Matrix.Rotation(spin, 4, "Z")


def screws(points, normals, mid=STEEL, bone="body", grp=0, **kw):
    proto = screw(**kw)
    Ms = [frame_to(p, n, 0.4 * i) for i, (p, n) in enumerate(zip(points, normals))]
    ob = geo.instances(proto, Ms, name="Screws")
    return P(ob, mid, bone, grp)


def zip_tie(w, h, at, axis_deg, mid=NYLON, grp=0, bone="body", tail=0.01):
    """Zip tie round a w x h (y, z) section, rotated about Z by axis_deg (its loop plane normal = the run direction),
    centred at `at`; the lock head sits at the top-left corner with a cut tail."""
    p = loop_path(w + 0.0016, h + 0.0016, 0.0025, 3)
    ob = band(p, 0.0026, 0.0009, "Zip")
    head = box(-0.0018, 0.0018, w / 2 - 0.0005, w / 2 + 0.0035, h / 2 - 0.0005, h / 2 + 0.003, bevel=0.0004)
    tl = box(-0.0007, 0.0007, w / 2 + 0.0035, w / 2 + 0.0035 + tail, h / 2 + 0.0004, h / 2 + 0.0016, bevel=0.0002)
    ob = geo.join([ob, head, tl])
    xform(ob, T(*at) @ rot_z(axis_deg))
    return P(ob, mid, bone, grp)


# ================================================================================================== AIRFRAME

def octa_plan(L, Wd, cx=0.0, fil=0.0, seg=3):
    """Elongated octagon in plan (x, y): vertices at the nose, tail, sides and diagonals (the web hull)."""
    pts = [(cx + L / 2 * math.cos(a), Wd / 2 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    return [tuple(p[:2]) for p in (geo.fillet(pts, fil, seg, closed=True) if fil > 0 else pts)]


def lofted_plan(plan, levels, cx, name):
    """Loft a plan outline through (z, scale) levels, scaled about (cx, 0)."""
    pl = np.array(plan)
    secs = []
    for z, s in levels:
        q = np.empty((len(pl), 3))
        q[:, 0] = cx + (pl[:, 0] - cx) * s
        q[:, 1] = pl[:, 1] * s
        q[:, 2] = z
        secs.append(q)
    return loft(secs, name=name)


def hull_parts():
    parts = []
    # hull: faceted lozenge 0.56 x 0.30 x 0.11, 2 cm aft, z -0.035..0.075, the bottom 84 % of the top
    plan = octa_plan(0.56, 0.30, -0.02, fil=0.016, seg=3)
    lv = [(-0.035, 0.825), (-0.0325, 0.838), (-0.029, 0.846), (0.040, 0.945), (0.070, 0.993), (0.0735, 0.999), (0.075, 0.988)]
    h = lofted_plan(plan, lv, -0.02, "Hull")
    round_edges(h, 0.0025, 2, 25.0)
    parts.append(P(h, HULL, grp=1))
    # parting line flange between the lower tub and the upper shell (a 3 mm lip at z 0.040)
    fl = lofted_plan(octa_plan(0.56, 0.30, -0.02, fil=0.018, seg=3), [(0.0375, 0.952), (0.0405, 0.958), (0.0425, 0.955)], -0.02, "Flange")
    round_edges(fl, 0.0008, 1, 30.0)
    parts.append(P(fl, HULL, grp=1))
    # raised top deck 0.50 x 0.26 tapering to 0.30 x 0.156, z 0.052..0.112, centred 4 cm aft
    dplan = octa_plan(0.50, 0.26, -0.04, fil=0.014, seg=3)
    d = lofted_plan(dplan, [(0.060, 1.0), (0.0745, 0.985), (0.108, 0.62), (0.111, 0.605), (0.112, 0.59)], -0.04, "Deck")
    round_edges(d, 0.002, 2, 20.0)
    parts.append(P(d, DECK, grp=1))
    # oxblood spine panel 0.34 x 0.07, top at +0.13 (z 0.107..0.129), with a centre rib
    sp = prism(rrect(0.34, 0.07, 0.012, 4, cx=-0.05), 0.107, 0.129, axis="Z", bevel=0.0018, seg=2)
    parts.append(P(sp, OXBLOOD, grp=1))
    rib = prism(rrect(0.26, 0.012, 0.005, 3, cx=-0.05), 0.128, 0.1318, axis="Z", bevel=0.0009, seg=2)
    parts.append(P(rib, OXBLOOD, grp=1))
    pts = [(-0.05 + dx, dy, 0.129) for dx in (-0.155, -0.05, 0.05, 0.155) for dy in (-0.026, 0.026)]
    parts.append(screws(pts, [(0, 0, 1)] * len(pts), grp=1, head_r=0.0022))
    # screws round the deck where it meets the hull top
    ring = [(-0.04 + 0.262 * math.cos(a), 0.137 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 14, endpoint=False)]
    parts.append(screws([(x, y, 0.0752) for x, y in ring], [(0, 0, 1)] * len(ring), grp=1, head_r=0.0021))
    # GPS puck on a short mast on the rear of the hull top
    parts.append(P(cyl(0.006, 0.072, 0.118, 12, at=(-0.245, 0.0)), ALU, grp=1))
    parts.append(P(rev([(0.0, 0.115), (0.028, 0.115), (0.030, 0.121), (0.026, 0.130), (0.0, 0.132)], 32, at=(-0.245, 0, 0),
                       fillet=0.002), HULL, grp=1))
    # down-looking sensor module (optical flow camera + range finder) under the rear hull
    sm = box(-0.215, -0.175, -0.022, 0.022, -0.043, -0.033, bevel=0.0015)
    parts.append(P(sm, HULL, grp=1))
    for yy in (-0.010, 0.010):
        parts.append(P(cyl(0.0055, -0.0445, -0.042, 16, at=(-0.195, yy)), GLASS_K, grp=1))
    # two telemetry antennae hanging back and down from the rear underside
    for s in (1, -1):
        base = Vector((-0.235, s * 0.055, -0.030))
        tip = base + Vector((-0.055, s * 0.02, -0.07))
        parts.append(P(tube_path([tuple(base), tuple(base + (tip - base) * 0.18)], 0.0055, 12, "AntBase"), NYLON, grp=1))
        parts.append(P(tube_path([tuple(base + (tip - base) * 0.16), tuple(tip)], 0.0032, 10, "Ant"), RUBBER, grp=1))
    return parts


def beak_parts():
    """Hooked nose fairing: four-sided, 0.20 m wide and 0.10 m tall at its base (x 0.24), tip 0.48 ahead, drooping
    11 degrees with the droop growing toward the tip; it runs back over the hull's nose as a cowling. The oxblood
    brow plate (0.12 x 0.10, tilted 17 degrees, front up) rises out of its ridge like a crest."""
    parts = []
    n = 28
    secs = []
    for i in range(n):
        t = i / (n - 1)
        x = 0.13 + 0.348 * t
        k = max(0.0, (x - 0.242) / 0.236)
        zc = 0.0118 - 0.0468 * k ** 1.35
        wd = 0.200 * (1 - k) ** 0.95 + 0.005
        ht = 0.100 * (1 - k) ** 0.95 + 0.004
        top = ht * (0.5 + 0.08 * k)
        dia = [(0.0, top), (wd / 2, 0.0), (0.0, -(ht - top)), (-wd / 2, 0.0)]
        dia = geo.fillet(dia, 0.009 * (1 - k) + 0.0014, 3, closed=True)
        secs.append([(x, p[0], zc + p[1]) for p in dia])
    b = loft(secs, name="Beak")
    parts.append(P(b, HULL, grp=1))
    br = prism(rrect(0.12, 0.10, 0.018, 4), -0.006, 0.006, axis="Z", bevel=0.0018, seg=2)
    xform(br, T(0.30, 0, 0.052) @ Matrix.Rotation(math.radians(-17.0), 4, "Y"))
    parts.append(P(br, OXBLOOD, grp=1))
    c17, s17 = math.cos(math.radians(17)), math.sin(math.radians(17))
    pts = [(0.30 + dx * c17, dy, 0.058 + dx * s17) for dx in (0.035,) for dy in (-0.03, 0.03)]
    parts.append(screws(pts, [(-s17, 0, c17)] * 2, grp=1, head_r=0.0028))
    return parts


def tail_parts():
    """Boom 0.26 x 0.05 x 0.04 to 0.53 aft; V tail: two oxblood fins 0.15 tall, 0.11 chord, canted 34 degrees,
    at 0.47 aft (the web's fin frame; leading edge kept upright); white strobe on a mast between them."""
    parts = []
    bm = prism(rrect(0.05, 0.04, 0.009, 4), -0.53 + 0.012, -0.26, axis="X", bevel=0.0014, seg=2)
    xform(bm, T(0, 0, 0.01))
    parts.append(P(bm, HULL, grp=3))
    cap = rev([(0.0, 0.0), (0.012, 0.0), (0.0115, 0.006), (0.006, 0.011), (0.0, 0.012)], 24)
    xform(cap, T(-0.518, 0, 0.01) @ Matrix.Rotation(math.radians(-90), 4, "Y") @ Matrix.Diagonal((1.6, 2.0, 1.0, 1.0)))
    parts.append(P(cap, HULL, grp=3))
    for s in (1, -1):                         # s = +1: the fin on the drone's right (-Y)
        out = [(0.055, -0.075), (0.055, -0.060), (0.055 - 0.135 * math.tan(0.3) + 0.006, 0.070), (0.0, 0.075),
               (-0.058, 0.075), (-0.055, -0.075)]
        f = prism(out, -0.006, 0.006, axis="Y", bevel=0.0024, seg=2)
        xform(f, T(-0.47, -s * 0.055, 0.075) @ Matrix.Rotation(0.3, 4, "Y") @ Matrix.Rotation(s * 0.6, 4, "X"))
        parts.append(P(f, OXBLOOD, grp=3))
    parts.append(P(cyl(0.004, 0.028, 0.083, 12, at=(-0.47, 0.0)), ALU, grp=3))
    parts.append(P(cyl(0.0085, 0.078, 0.084, 20, at=(-0.47, 0.0)), HULL, grp=3))
    parts.append(P(rev([(0.0, 0.083), (0.0078, 0.083), (0.0076, 0.090), (0.005, 0.0965), (0.0, 0.0985)], 20, at=(-0.47, 0, 0.0)),
                   LED_W, grp=3))
    return parts


def arm_parts(key):
    """A swept arm (rectangular carbon tube 0.045 x 0.03) from the hull to the hub, a folding joint near the
    hull, the motor phase loom underneath with zip ties."""
    hx, hy, _ = BZ["hubs"][key]
    g = {"fl": 4, "fr": 5, "rl": 6, "rr": 7}[key]
    L = math.hypot(hx, hy)
    ang = math.degrees(math.atan2(hy, hx))
    R = T(0, 0, 0.012) @ rot_z(ang)
    parts = []
    a = prism(rrect(0.045, 0.03, 0.0075, 4), 0.10, L, axis="X", bevel=0.0012, seg=2)
    xform(a, R)
    parts.append(P(a, CARBON, grp=g))
    # folding joint: anodised sleeve, hinge knuckles, locking collar
    j0, j1 = 0.165, 0.215
    s = prism(rrect(0.052, 0.037, 0.008, 4), j0, j1, axis="X", bevel=0.0016, seg=2)
    xform(s, R)
    parts.append(P(s, ANOD, grp=g))
    col = lathe([(0.0, 0.0), (0.0, 0.0300), (0.0025, 0.0315), (0.0135, 0.0315), (0.016, 0.0300), (0.016, 0.0)], 32, axis="X",
                fillet=0.0008)
    xform(col, R @ T(j1 + 0.002) @ Matrix.Diagonal((1.0, 0.92, 0.66, 1.0)))
    parts.append(P(col, ALU, grp=g))
    for zz in (0.0185, -0.0185):
        k = cyl(0.0062, 0.0, 0.006, 20, at=(0.0, 0.0))
        xform(k, R @ T(0.19, -0.022, zz - (0.006 if zz < 0 else 0)))
        parts.append(P(k, ALU, grp=g))
    sp = [Vector((0.180, -0.026, 0.0)), Vector((0.200, -0.026, 0.0)), Vector((0.180, 0.026, 0.0)), Vector((0.200, 0.026, 0.0))]
    parts.append(screws([tuple(R @ (v + Vector((0, 0, 0.0185)))) for v in sp], [(0, 0, 1)] * 4, grp=g, button=False, head_r=0.002))
    # grommet where the arm enters the motor pod
    gr = lathe([(0.0, 0.0), (0.0, 0.0255), (0.002, 0.0275), (0.006, 0.0275), (0.008, 0.0255), (0.008, 0.0)], 28, axis="X",
               fillet=0.0008)
    xform(gr, R @ T(L - 0.054) @ Matrix.Diagonal((1.0, 1.0, 0.75, 1.0)))
    parts.append(P(gr, RUBBER, grp=g))
    # phase loom under the arm: braided sleeve, three leads out of the pod, zip ties
    side = -1.0 if hy > 0 else 1.0
    path = [(L - 0.050, 0.006 * side, -0.0120), (L - 0.075, 0.0085 * side, -0.0196), (0.25, 0.010 * side, -0.0197),
            (0.14, 0.009 * side, -0.0196), (0.105, 0.004 * side, -0.0150)]
    lm = tube_path(path, 0.0046, 10, "Loom", bend=0.02)
    xform(lm, R)
    parts.append(P(lm, SLEEVE, grp=g))
    for t in (0.25, 0.32, L - 0.12):
        zt = zip_tie(0.045, 0.030 + 0.0105, (0, 0, 0), 0.0, grp=g)
        xform(zt, R @ T(t, 0, -0.0052))
        parts.append(zt)
    # nav strobe housing on the front pods
    return parts


def motor_parts(key):
    """Motor pod under the hub: composite cup with the finned ESC heat sink in its floor, the stator (18 teeth,
    copper windings) and the anodised outrunner bell with slanted side vents and a spoked cap that show the
    windings, the prop adapter. Front pods carry the navigation strobes."""
    hx, hy, hz = BZ["hubs"][key]
    g = {"fl": 4, "fr": 5, "rl": 6, "rr": 7}[key]
    ang = math.degrees(math.atan2(hy, hx))
    H = T(hx, hy, 0.0) @ rot_z(ang)
    parts = []
    # cup: z -0.0125 .. 0.031, floor open in the middle for the heat sink
    cup = rev([(0.030, -0.0110), (0.040, -0.0125), (0.0455, -0.008), (0.0465, 0.029), (0.0445, 0.0315), (0.0425, 0.0305),
               (0.0445, 0.0285), (0.0445, -0.006), (0.039, -0.0095), (0.030, -0.0085)], 40, closed=True, fillet=0.0012, fseg=1)
    xform(cup, H)
    parts.append(P(cup, HULL, grp=g))
    hs = rev([(0.0, -0.0105), (0.0315, -0.0105), (0.0315, -0.0080), (0.0, -0.0080)], 32, fillet=0.0005, fseg=1)
    fins = []
    for i in range(-5, 6):
        y = i * 0.0052
        half = math.sqrt(max(0.0294 ** 2 - y * y, 1e-6))
        fins.append(box(-half, half, y - 0.0008, y + 0.0008, -0.0170, -0.0102, bevel=0.0004))
    hs = geo.join([hs] + fins)
    xform(hs, H)
    parts.append(P(hs, ANOD, grp=g))
    # stator mount flange and its screws
    fl = rev([(0.008, 0.0290), (0.031, 0.0290), (0.031, 0.0345), (0.008, 0.0345)], 32, closed=True, fillet=0.0006, fseg=1)
    xform(fl, H)
    parts.append(P(fl, ANOD, grp=g))
    sp = [(0.022 * math.cos(a), 0.022 * math.sin(a), 0.0345) for a in np.radians([45, 135, 225, 315])]
    sc = screws(sp, [(0, 0, 1)] * 4, grp=g, button=False, head_r=0.0019, head_h=0.0014)
    xform(sc, H)
    parts.append(sc)
    # stator: core, 18 teeth with shoes, copper windings
    st = [rev([(0.006, 0.0350), (0.0135, 0.0350), (0.0135, 0.0635), (0.006, 0.0635)], 24, closed=True, fillet=0.0004, fseg=1)]
    wind = []
    for i in range(18):
        a = i * 20.0 + 10.0
        tooth = box(0.013, 0.0345, -0.0017, 0.0017, 0.0365, 0.0620, bevel=0.0)
        shoe = box(0.0335, 0.0362, -0.0031, 0.0031, 0.0362, 0.0623, bevel=0.0004, seg=1)
        w_ = box(0.0150, 0.0318, -0.0038, 0.0038, 0.0375, 0.0610, bevel=0.0022, seg=2)
        for o in (tooth, shoe):
            xform(o, rot_z(a))
            st.append(o)
        xform(w_, rot_z(a))
        wind.append(w_)
    s_ob = geo.join(st)
    xform(s_ob, H)
    parts.append(P(s_ob, STATOR, grp=g))
    w_ob = geo.join(wind)
    xform(w_ob, H)
    parts.append(P(w_ob, COPPER, grp=g, smooth=70.0))
    # bell: lower ring with magnets inside, vent band with slanted ribs, top ring + spoked cap
    low = rev([(0.0385, 0.0348), (0.0420, 0.0348), (0.0422, 0.0460), (0.0385, 0.0460)], 56, closed=True, fillet=0.0006, fseg=1)
    mag = rev([(0.0368, 0.0352), (0.0386, 0.0352), (0.0386, 0.0455), (0.0368, 0.0455)], 40, closed=True)
    top = rev([(0.0385, 0.0578), (0.0422, 0.0578), (0.0420, 0.0650), (0.0395, 0.0675), (0.0300, 0.0680), (0.0300, 0.0655),
               (0.0385, 0.0650)], 56, closed=True, fillet=0.0006, fseg=1)
    ribs = []
    for i in range(16):
        rb = box(-0.0016, 0.0016, -0.0010, 0.0010, -0.0068, 0.0068, bevel=0.0003)
        xform(rb, rot_z(i * 22.5) @ T(0.0, 0.0404, 0.0519) @ Matrix.Rotation(math.radians(28.0), 4, "Y"))
        ribs.append(rb)
    hub = rev([(0.0045, 0.0650), (0.0125, 0.0650), (0.0125, 0.0690), (0.0045, 0.0690)], 24, closed=True, fillet=0.0005, fseg=1)
    spokes = []
    for i in range(6):
        c = []
        for k in range(9):
            t = k / 8
            r = 0.0115 + t * 0.0195
            a = math.radians(i * 60.0 + 24.0 * t)
            c.append((r * math.cos(a), r * math.sin(a)))
        nrm = []
        for k in range(len(c)):
            p0, p1 = np.array(c[max(k - 1, 0)]), np.array(c[min(k + 1, len(c) - 1)])
            d = (p1 - p0) / np.linalg.norm(p1 - p0)
            nrm.append(np.array([-d[1], d[0]]))
        wdt = 0.0034
        outline = [tuple(np.array(p) + n * wdt / 2) for p, n in zip(c, nrm)] + \
                  [tuple(np.array(p) - n * wdt / 2) for p, n in zip(c[::-1], nrm[::-1])]
        spokes.append(prism(outline, 0.0652, 0.0678, axis="Z", bevel=0.0004, seg=1))
    bell = geo.join([low, top] + ribs + [hub] + spokes)
    xform(bell, H)
    parts.append(P(bell, ANOD, grp=g))
    xform(mag, H)
    parts.append(P(mag, MAGNET, grp=g))
    # prop adapter collar (body side of the shaft)
    ad = rev([(0.0, 0.0688), (0.0090, 0.0688), (0.0095, 0.0715), (0.0080, 0.0748), (0.0, 0.0748)], 28, fillet=0.0004)
    xform(ad, H)
    parts.append(P(ad, ALU, grp=g))
    # front pods: the navigation strobe in a streamlined housing toward the brief position
    if key in ("fl", "fr"):
        sp = Vector(BZ["strobe_port"] if key == "fl" else BZ["strobe_star"])
        d = Vector((sp.x - hx, sp.y - hy, 0.0))
        dist = d.length
        a2 = math.degrees(math.atan2(d.y, d.x))
        hsg = lathe([(0.0, 0.0), (0.0, 0.0085), (dist - 0.050, 0.0085), (dist - 0.044, 0.0080), (dist - 0.040, 0.0)],
                    24, axis="X", fillet=0.0015)
        xform(hsg, T(hx, hy, sp.z) @ rot_z(a2) @ T(0.038))
        parts.append(P(hsg, HULL, grp=g))
        dome = lathe([(0.0, 0.0), (0.0, 0.0078), (0.004, 0.0072), (0.0075, 0.0045), (0.0092, 0.0)], 24, axis="X")
        xform(dome, T(hx, hy, sp.z) @ rot_z(a2) @ T(dist - 0.0085))
        parts.append(P(dome, LED_R if key == "fl" else LED_G, grp=g, smooth=80.0))
    return parts


def airfoil(n=14, camber=0.045, pos=0.38):
    """NACA-style section, chord 0 (LE) .. 1 (TE): closed loop of 2n-2 points (x, z), thickness 1 (scaled later)."""
    b = np.linspace(0, math.pi, n)
    x = 0.5 * (1 - np.cos(b))
    yt = 5 * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1036 * x ** 4)
    yc = np.where(x < pos, camber / pos ** 2 * (2 * pos * x - x * x), camber / (1 - pos) ** 2 * ((1 - 2 * pos) + 2 * pos * x - x * x))
    up = [(x[i], yc[i], yt[i]) for i in range(n)]
    lo = [(x[i], yc[i], -yt[i]) for i in range(n - 2, 0, -1)]
    return up + lo


def prop_blade(ccw=True, n_span=22):
    """One blade along +X: twisted (pitch 0.14 m, i.e. about 15 x 5.5 in), tapered chord (0.034 m at its widest),
    thin rounded tip, leading edge toward the direction of travel (+Y for a counter-clockwise prop)."""
    secs = []
    R = BZ["prop_r"]
    sec = airfoil()
    for i in range(n_span):
        t = i / (n_span - 1)
        r = 0.012 + (R - 0.012) * (1 - (1 - t) ** 1.15)
        rn = (r - 0.012) / (R - 0.012)
        c = 0.0175 + 0.0165 * math.exp(-((rn - 0.33) / 0.36) ** 2)
        if rn > 0.82:
            c *= math.sqrt(max(1 - ((rn - 0.82) / 0.18) ** 2, 0.0)) * 0.92 + 0.08
        th = (0.30 - 0.22 * min(rn / 0.25, 1.0)) if rn < 0.25 else (0.08 - 0.02 * (rn - 0.25) / 0.75)
        beta = min(math.atan(0.14 / (2 * math.pi * r)), math.radians(26.0))
        sweep = -0.0045 * rn ** 2
        ring = []
        for xc, yc, yt in sec:
            yy = (0.30 - xc) * c + sweep           # LE at +0.3 chord (direction of travel)
            zz = (yc + yt * th) * c
            ring.append((r, yy * math.cos(beta) - zz * math.sin(beta), yy * math.sin(beta) + zz * math.cos(beta)))
        secs.append(ring)
    bl = loft(secs, name="Blade")
    if not ccw:
        geo.transform(bl, scale=(1, -1, 1))
    return fix_normals(bl)


def prop_parts(key, grp=None):
    """Two-blade prop on its bone: moulded hub, blades, washer and dome nut (z 0.075 .. 0.105)."""
    hx, hy, hz = BZ["hubs"][key]
    bone = PROP_BONES[key]
    g = grp if grp is not None else {"fl": 8, "fr": 9, "rl": 10, "rr": 11}[key]
    ccw = BZ["ccw"][key]
    b1 = prop_blade(ccw)
    b2 = prop_blade(ccw)
    geo.transform(b2, rot=(0, 0, 180))
    blades = geo.join([b1, b2])
    xform(blades, T(0, 0, BZ["blade_z"]))
    hub = rev([(0.0, 0.0750), (0.0172, 0.0750), (0.0178, 0.0790), (0.0170, 0.0915), (0.0130, 0.0935), (0.0, 0.0935)], 36,
              fillet=0.0008)
    wsh = rev([(0.0040, 0.0933), (0.0105, 0.0933), (0.0105, 0.0946), (0.0040, 0.0946)], 28, closed=True, fillet=0.0003)
    nut = rev([(0.0, 0.0945), (0.0088, 0.0945), (0.0088, 0.0990), (0.0075, 0.1010), (0.0055, 0.1040), (0.0, 0.1050)], 6)
    dome = rev([(0.0, 0.0995), (0.0070, 0.0995), (0.0062, 0.1035), (0.0035, 0.1062), (0.0, 0.1068)], 28, fillet=0.0005)
    out = []
    for ob, m in ((blades, PROPC), (hub, PROPC), (wsh, STEEL), (nut, ALU), (dome, ALU)):
        xform(ob, T(hx, hy, 0.0) @ rot_z(90.0))           # parked along Y: the brief's 1.07 m across the discs
        out.append(P(ob, m, bone, g, smooth=60.0 if m == PROPC else 48.0))
    return out


def skid_parts():
    """Two rails 0.40 long, 0.26 apart, 0.16 below the centre, on four splayed struts (web: 0.27 rad), rubber end
    caps and feet, moulded T-fittings, clamp blocks on the hull and a cross tube front and back."""
    parts = []
    x0, x1 = BZ["skid_x"]
    zr = BZ["skid_z"]
    for s in (1, -1):
        y = s * BZ["skid_y"]
        parts.append(P(tube_path([(x0 + 0.012, y, zr), (x1 - 0.012, y, zr)], 0.009, 20, "Rail", cap=True), SKID, grp=12))
        for xe, d in ((x0, 1), (x1, -1)):
            cp = lathe([(0.0, 0.0), (0.0, 0.0098), (0.018, 0.0098), (0.0215, 0.0085), (0.0245, 0.005), (0.025, 0.0)], 24,
                       axis="X", fillet=0.001)
            if d < 0:
                geo.transform(cp, scale=(-1, 1, 1))
                fix_normals(cp)
            xform(cp, T(xe - d * 0.001, y, zr))
            parts.append(P(cp, RUBBER, grp=12))
        for xs in BZ["strut_x"]:
            top = (xs, s * 0.100, -0.036)
            bot = (xs, y, zr + 0.004)
            parts.append(P(tube_path([top, bot], 0.007, 16, "Strut"), SKID, grp=12))
            tf = lathe([(0.0, 0.0), (0.0, 0.0125), (0.024, 0.0125), (0.024, 0.0)], 24, axis="X", fillet=0.002)
            xform(tf, T(xs - 0.012, y, zr))
            parts.append(P(tf, NYLON, grp=12))
            ft = box(xs - 0.022, xs + 0.022, y - 0.009, y + 0.009, zr - 0.0135, zr - 0.006, bevel=0.003, seg=3)
            parts.append(P(ft, RUBBER, grp=12))
            cb = box(xs - 0.016, xs + 0.016, s * 0.100 - 0.012, s * 0.100 + 0.012, -0.046, -0.033, bevel=0.002)
            parts.append(P(cb, ALU, grp=12))
            parts.append(screws([(xs - 0.010, s * 0.100, -0.046), (xs + 0.010, s * 0.100, -0.046)], [(0, 0, -1)] * 2, grp=12,
                                button=False, head_r=0.0018))
    for xs in BZ["strut_x"]:
        parts.append(P(tube_path([(xs, -0.118, -0.128), (xs, 0.118, -0.128)], 0.0045, 12, "Brace"), SKID, grp=12))
    return parts


def battery_parts():
    """Flight pack under the hull between the struts: shrink-wrapped 6S LiPo on a carbon tray, two webbing straps
    with buckles, main leads into a yellow XT90 pair, the balance lead tucked under a strap."""
    parts = []
    x0, x1, y0, y1, z0, z1 = -0.150, 0.060, -0.066, 0.066, -0.092, -0.041
    bt = box(x0, x1, y0, y1, z0, z1, bevel=0.0075, seg=4)
    parts.append(P(bt, BATTERY, grp=2))
    tray = prism(rrect(0.25, 0.15, 0.012, 4, cx=-0.045), -0.0405, -0.0365, axis="Z", bevel=0.0009, seg=1)
    parts.append(P(tray, CARBON, grp=2))
    ts = [(-0.045 + dx, dy, -0.0405) for dx in (-0.115, 0.115) for dy in (-0.062, 0.062)]
    parts.append(screws(ts, [(0, 0, -1)] * 4, grp=2, head_r=0.0022))
    for xs in (-0.105, 0.012):
        pth = [(xs, p[1], p[2] - 0.0665) for p in loop_path(0.1365, 0.0545, 0.008, 4)]
        parts.append(P(band(pth, 0.020, 0.0014, "Strap"), STRAP, grp=2))
        bk = box(xs - 0.013, xs + 0.013, -0.018, 0.012, z0 - 0.0058, z0 - 0.0008, bevel=0.0012)
        parts.append(P(bk, NYLON, grp=2))
        tab = box(xs - 0.0102, xs + 0.0102, 0.012, 0.040, z0 - 0.0036, z0 - 0.0016, bevel=0.0006)
        parts.append(P(tab, STRAP, grp=2))
    # main leads: red and black, out of the front face, into the XT90 pair hanging under the tray
    for yy, m in ((0.012, WIRE_R), (-0.012, WIRE_K)):
        pth = [(x1 - 0.004, yy * 1.4, -0.052), (x1 + 0.016, yy * 1.4, -0.054), (x1 + 0.030, yy * 0.6, -0.068),
               (x1 + 0.030, yy * 0.35, -0.084)]
        parts.append(P(tube_path(pth, 0.0042, 12, "Lead", bend=0.012), m, grp=2, smooth=70.0))
        up = [(x1 + 0.030, yy * 0.35, -0.0365), (x1 + 0.030, yy * 0.35, -0.052)]
        parts.append(P(tube_path(up, 0.0042, 12, "Pig"), m, grp=2, smooth=70.0))
    xt = box(x1 + 0.019, x1 + 0.041, -0.0085, 0.0085, -0.0895, -0.0525, bevel=0.0015)
    parts.append(P(xt, XT90, grp=2))
    seam = box(x1 + 0.0175, x1 + 0.0425, -0.0095, 0.0095, -0.0712, -0.0688, bevel=0.0006)
    parts.append(P(seam, XT90, grp=2))
    # balance lead: six thin wires side by side, out of the rear face and under the rear strap
    bl = []
    for k in range(6):
        yy = -0.006 + k * 0.0024
        bl.append(tube_path([(x0 + 0.002, yy, -0.050), (x0 - 0.010, yy, -0.056), (x0 - 0.011, yy, -0.088), (x0 + 0.030, yy + 0.02, -0.0935)],
                            0.0011, 6, "Bal", bend=0.006))
    parts.append(P(geo.join(bl), WIRE_K, grp=2, smooth=70.0))
    parts.append(P(box(x0 + 0.030, x0 + 0.044, 0.006, 0.024, -0.0985, -0.0925, bevel=0.0007), NYLON, grp=2))
    return parts


def gimbal_parts():
    """Two-axis gimbal under the nose. Body side: carbon damper plate, four rubber dampers, the lower plate and
    the yaw motor housing (the web's neck). Gimbal bone: yaw collar, the ball housing (0.124 m) with pitch motor
    caps, the eye (0.072 m lens in a 0.09 m ring), the slung gun on its improvised mount (bar, L bracket, two
    hose clamps), the solenoid on the trigger, the feed chute from the ammunition box and the wiring loom."""
    gx, gy, gz = BZ["gimbal"]
    bx, by, bz = BZ["ball"]
    br = BZ["ball_r"]
    body, gim = [], []
    plate = prism(rrect(0.078, 0.066, 0.008, 4, cx=gx), -0.0385, -0.0355, axis="Z", bevel=0.0008, seg=1)
    body.append(P(plate, CARBON, grp=1))
    lp = prism(rrect(0.070, 0.058, 0.008, 4, cx=gx), -0.0525, -0.0495, axis="Z", bevel=0.0008, seg=1)
    body.append(P(lp, ANOD, grp=1))
    dmp = []
    for dx in (-0.027, 0.027):
        for dy in (-0.022, 0.022):
            dmp.append(rev([(0.0, -0.0500), (0.0035, -0.0500), (0.0062, -0.0465), (0.0068, -0.0440), (0.0055, -0.0405),
                            (0.0035, -0.0385), (0.0, -0.0385)], 20, at=(gx + dx, dy, 0.0)))
    body.append(P(geo.join(dmp), RUBBER, grp=1, smooth=70.0))
    neck = rev([(0.0, -0.0600), (0.0230, -0.0600), (0.0245, -0.0560), (0.0250, -0.0525), (0.0, -0.0525)], 40, at=(gx, gy, 0),
               fillet=0.001)
    body.append(P(neck, ANOD, grp=1))
    # ---- gimbal bone
    col = rev([(0.0185, -0.0640), (0.0240, -0.0640), (0.0460, -0.0605), (0.0470, -0.0590), (0.0440, -0.0580), (0.0185, -0.0600)],
              48, at=(gx, gy, 0), closed=True, fillet=0.0008)
    gim.append(P(col, ANOD, "gimbal", 13))
    # ball housing: sphere r 0.062 about (0.19, 0, -0.10), open above z -0.058, rolled lip
    zc = -0.058 - bz
    a_cut = math.asin(zc / br)
    prof = [(0.0, -br)]
    for k in range(1, 20):
        a = -math.pi / 2 + (a_cut + math.pi / 2) * k / 19
        prof.append((br * math.cos(a), br * math.sin(a)))
    rc = br * math.cos(a_cut)
    prof += [(rc - 0.0035, zc + 0.0002), (rc - 0.0040, zc - 0.002)]
    ball = rev(prof, 48, at=(bx, by, bz), fillet=0.0012)
    gim.append(P(ball, BALL, "gimbal", 13))
    belt = rev([(br - 0.0006, -0.0035), (br + 0.0012, -0.0030), (br + 0.0014, 0.0030), (br - 0.0006, 0.0035)], 64,
               at=(bx, by, bz), closed=True, fillet=0.0004)
    gim.append(P(belt, ANOD, "gimbal", 13))
    # pitch motor caps on both sides, on the pitch axis through the pivot
    for s in (1, -1):
        cp = lathe([(0.0, 0.0), (0.0, 0.0215), (0.0045, 0.0215), (0.0075, 0.0185), (0.0082, 0.0), ], 40, axis="Y", fillet=0.0008)
        if s < 0:
            geo.transform(cp, scale=(1, -1, 1))
            fix_normals(cp)
        xform(cp, T(gx, s * 0.0545, gz))
        gim.append(P(cp, ANOD, "gimbal", 13))
        sp = [(gx + 0.0145 * math.cos(a), s * 0.0625, gz + 0.0145 * math.sin(a)) for a in np.radians([30, 150, 270])]
        gim.append(screws(sp, [(0, s, 0)] * 3, STEEL, "gimbal", 13, button=False, head_r=0.0018))
    # eye: ring 0.09 across, lens 0.072 across at (0.255, 0, -0.10), looking forward
    ex = BZ["eye"][0]
    ring = lathe([(0.0, BZ["lens_r"] - 0.0008), (0.0, BZ["ring_r"]), (0.020, BZ["ring_r"]), (0.0235, BZ["ring_r"] - 0.0025),
                  (0.0245, BZ["lens_r"] + 0.0035), (0.0245, BZ["lens_r"] + 0.0006), (0.0190, BZ["lens_r"] - 0.0008)],
                 64, axis="X", closed=True, fillet=0.0009)
    geo.transform(ring, loc=(ex - 0.0215, 0, bz))
    gim.append(P(ring, DECK, "gimbal", 13))
    lr = BZ["lens_r"]
    lens = lathe([(0.0, 0.0), (0.0, lr - 0.0002), (0.0016, lr - 0.0006), (0.0040, lr * 0.84), (0.0062, lr * 0.58),
                  (0.0075, lr * 0.30), (0.0079, 0.0)], 64, axis="X")
    geo.transform(lens, loc=(ex - 0.0055, 0, bz))
    gim.append(P(lens, LENS, "gimbal", 13, smooth=80.0))
    # ---- gun: receiver x 0.16..0.36, 0.03 wide (y -0.077..-0.047), 0.034 tall (z -0.147..-0.113)
    gcx, gcy, gcz = BZ["gun_c"]
    y0, y1 = gcy - 0.015, gcy + 0.015
    z0, z1 = gcz - 0.017, gcz + 0.017
    rec = prism([(0.160, z0 + 0.004), (0.166, z0), (0.352, z0), (0.360, z0 + 0.006), (0.360, z1 - 0.004), (0.356, z1),
                 (0.164, z1), (0.160, z1 - 0.006)], y0, y1, axis="Y", bevel=0.0014, seg=2)
    port = box(0.235, 0.285, y0 - 0.002, y0 + 0.0035, gcz - 0.007, gcz + 0.009, bevel=0.0008)
    cut(rec, port)
    for xx in (0.176, 0.192, 0.208, 0.308, 0.324, 0.340):
        hole = cyl(0.0042, 0.0, 0.004, 16, axis="Y", at=(xx, gcz - 0.002))
        geo.transform(hole, loc=(0, y0 - 0.002, 0))
        cut(rec, hole)
    round_edges(rec, 0.0006, 1, 40.0)
    gim.append(P(rec, GUN, "gimbal", 14))
    bolt = box(0.240, 0.272, y0 + 0.0025, y0 + 0.006, gcz - 0.0055, gcz + 0.0075, bevel=0.0010)
    gim.append(P(bolt, STEEL, "gimbal", 14))
    knob = cyl(0.0042, 0.0, 0.010, 16, axis="Y", at=(0.262, gcz + 0.001))
    geo.transform(knob, scale=(1, -1, 1))
    fix_normals(knob)
    geo.transform(knob, loc=(0, y0 - 0.0005, 0))
    gim.append(P(knob, GUN, "gimbal", 14))
    rail = box(0.172, 0.348, gcy - 0.0075, gcy + 0.0075, z1 - 0.0002, z1 + 0.0032, bevel=0.0006)
    for xx in np.arange(0.180, 0.345, 0.0105):
        cut(rail, box(xx - 0.0024, xx + 0.0024, gcy - 0.009, gcy + 0.009, z1 + 0.0018, z1 + 0.004))
    round_edges(rail, 0.0004, 1, 40.0)
    gim.append(P(rail, GUN, "gimbal", 14))
    mx = BZ["muzzle"][0]
    br_ = lathe([(0.0, 0.0), (0.0, 0.010), (mx - 0.024 - 0.300, 0.010), (mx - 0.022 - 0.300, 0.0094), (mx - 0.300 - 0.012, 0.0094),
                 (mx - 0.300 - 0.012, 0.0)], 32, axis="X", fillet=0.0005)
    geo.transform(br_, loc=(0.300, gcy, gcz))
    gim.append(P(br_, BARREL, "gimbal", 14))
    md = lathe([(0.0, 0.0057), (0.0, 0.0112), (0.0185, 0.0112), (0.0200, 0.0098), (0.0200, 0.0057)], 32, axis="X", closed=True,
               fillet=0.0006)
    geo.transform(md, loc=(mx - 0.020, gcy, gcz))
    for k in range(3):
        xa = mx - 0.0165 + k * 0.0050
        for s in (1, -1):
            ya, yb = (gcy + 0.004, gcy + 0.014) if s > 0 else (gcy - 0.014, gcy - 0.004)
            cut(md, box(xa, xa + 0.0026, ya, yb, gcz - 0.0028, gcz + 0.0028))
    gim.append(P(md, BARREL, "gimbal", 14))
    bore = cyl(0.0056, 0.0, 0.004, 20, axis="X", at=(gcy, gcz))
    geo.transform(bore, loc=(mx - 0.0045, 0, 0))
    gim.append(P(bore, BORE, "gimbal", 14))
    # improvised mount: flat bar on the receiver top, an L bracket to the pitch cap, two hose clamps
    bar = box(0.168, 0.325, gcy - 0.012, gcy + 0.012, z1 + 0.0032, z1 + 0.0072, bevel=0.0008)
    gim.append(P(bar, ALU, "gimbal", 14))
    zt = z1 + 0.0072
    lb = prism([(0.152, zt), (0.205, zt), (0.205, gz + 0.012), (0.186, gz + 0.022), (0.152, gz + 0.022)], -0.0667, -0.0629,
               axis="Y", bevel=0.0008, seg=1, fillet=0.004)
    gim.append(P(lb, ALU, "gimbal", 14))
    foot = box(0.168, 0.205, -0.0705, -0.0535, zt, zt + 0.004, bevel=0.0008)
    gim.append(P(foot, ALU, "gimbal", 14))
    lsc = [(gx - 0.010, -0.0667, gz - 0.006), (gx + 0.010, -0.0667, gz - 0.006)]
    gim.append(screws(lsc, [(0, -1, 0)] * 2, STEEL, "gimbal", 14, button=False, head_r=0.0024))
    gim.append(screws([(0.196, -0.062, zt + 0.004)], [(0, 0, 1)], STEEL, "gimbal", 14, button=False, head_r=0.0024))
    bl = []
    for xx in (0.205, 0.300):
        hh = (z1 + 0.0072) - z0
        pth = [(xx, p[1] + gcy, p[2] + z0 + hh / 2) for p in loop_path(0.0315, hh + 0.0012, 0.0035, 3)]
        bl.append(P(band(pth, 0.0085, 0.0007, "Clamp"), STEEL, "gimbal", 14))
        hsn = box(xx - 0.0065, xx + 0.0065, y0 - 0.0075, y0 - 0.0005, z1 - 0.004, z1 + 0.0085, bevel=0.0008)
        bl.append(P(hsn, STEEL, "gimbal", 14))
        sw = cyl(0.0028, 0.0, 0.016, 12, axis="X", at=(y0 - 0.0045, z1 + 0.0024))
        geo.transform(sw, loc=(xx - 0.008, 0, 0))
        bl.append(P(sw, BRASS, "gimbal", 14))
    gim += bl
    # solenoid on the trigger: coil in a steel U frame on the receiver's tail, plunger link, two leads
    sx = 0.150
    coil = cyl(0.0078, 0.0, 0.024, 20, axis="X", at=(gcy, gcz - 0.002))
    geo.transform(coil, loc=(sx - 0.022, 0, 0))
    gim.append(P(coil, TAPE, "gimbal", 14))
    uf = box(sx - 0.025, sx + 0.0015, gcy - 0.0095, gcy + 0.0095, gcz - 0.0115, gcz - 0.0095, bevel=0.0005)
    ue = [box(sx - 0.025, sx - 0.023, gcy - 0.0095, gcy + 0.0095, gcz - 0.0115, gcz + 0.007, bevel=0.0004),
          box(sx - 0.0005, sx + 0.0015, gcy - 0.0095, gcy + 0.0095, gcz - 0.0115, gcz + 0.007, bevel=0.0004)]
    gim.append(P(geo.join([uf] + ue), STEEL, "gimbal", 14))
    pl = cyl(0.0022, 0.0, 0.018, 12, axis="X", at=(gcy, gcz - 0.002))
    geo.transform(pl, loc=(sx - 0.002, 0, 0))
    gim.append(P(pl, STEEL, "gimbal", 14))
    lk = box(sx + 0.012, sx + 0.016, gcy - 0.003, gcy + 0.003, z0 - 0.002, gcz, bevel=0.0006)
    gim.append(P(lk, STEEL, "gimbal", 14))
    for dy, m in ((-0.003, WIRE_R), (0.003, WIRE_K)):
        pth = [(sx - 0.024, gcy + dy, gcz + 0.005), (sx - 0.030, gcy + dy, gcz + 0.011), (0.126, -0.056 + dy, -0.119)]
        gim.append(P(tube_path(pth, 0.0013, 8, "SolLead", bend=0.004), m, "gimbal", 14, smooth=70.0))
    # wiring loom from the yaw collar down the back of the ball to the solenoid: braided sleeve, connector, zip tie
    c = Vector(BZ["ball"])
    dirs = [(-0.30, -0.45, 0.84), (-0.50, -0.55, 0.62), (-0.68, -0.56, 0.38), (-0.80, -0.55, 0.12)]
    lpts = [(gx - 0.007, -0.028, -0.0625)] + [tuple(c + Vector(d).normalized() * (br + 0.0045)) for d in dirs] + \
           [(0.127, -0.054, -0.116)]
    gim.append(P(tube_path(lpts, 0.0034, 10, "GimLoom", bend=0.008), SLEEVE, "gimbal", 13))
    mid_pt = c + Vector(dirs[2]).normalized() * (br + 0.0085)
    nrm = (mid_pt - c).normalized()
    cn = box(-0.0045, 0.0045, -0.0040, 0.0040, -0.006, 0.006, bevel=0.0008)
    xform(cn, frame_to(mid_pt, nrm))
    gim.append(P(cn, NYLON, "gimbal", 13))
    # ammunition box under the gun (0.07 x 0.05 x 0.045) with lid seam, latch and the feed chute
    ax_, ay, az = BZ["ammo_c"]
    ab = box(ax_ - 0.035, ax_ + 0.035, ay - 0.025, ay + 0.025, az - 0.0225, az + 0.0205, bevel=0.0022)
    gim.append(P(ab, DECK, "gimbal", 14))
    lid = box(ax_ - 0.036, ax_ + 0.036, ay - 0.026, ay + 0.026, az + 0.0175, az + 0.0225, bevel=0.0015)
    gim.append(P(lid, DECK, "gimbal", 14))
    lat = box(ax_ + 0.035, ax_ + 0.0385, ay - 0.008, ay + 0.008, az + 0.005, az + 0.020, bevel=0.0008)
    gim.append(P(lat, STEEL, "gimbal", 14))
    for yy in (ay - 0.026, ay + 0.026):
        r_ = box(ax_ - 0.025, ax_ + 0.025, yy - 0.0012, yy + 0.0012, az - 0.012, az - 0.008, bevel=0.0009)
        gim.append(P(r_, DECK, "gimbal", 14))
    ch = []
    for k in range(7):
        t = k / 6
        x = ax_ + 0.030 + 0.012 * math.sin(t * math.pi * 0.5)
        y = ay - 0.026 - 0.006 * math.sin(t * math.pi)
        z = az + 0.012 + 0.030 * t
        ch.append((x, y, z))
    chute = geo.sweep(rrect(0.006, 0.016, 0.002, 2), ch, cap=True, name="Chute")
    gim.append(P(fix_normals(chute), RUBBER, "gimbal", 14))
    return body, gim


# ================================================================================================== ASSEMBLY

BONES = [
    rig.Bone("body", (0, 0, 0)),
    rig.Bone("prop_fl", BZ["hubs"]["fl"], "body"), rig.Bone("prop_fr", BZ["hubs"]["fr"], "body"),
    rig.Bone("prop_rl", BZ["hubs"]["rl"], "body"), rig.Bone("prop_rr", BZ["hubs"]["rr"], "body"),
    rig.Bone("gimbal", BZ["gimbal"], "body"),
    rig.Bone("Eye", BZ["eye"], "gimbal", deform=False), rig.Bone("GunMuzzle", BZ["muzzle"], "gimbal", deform=False),
    rig.Bone("Strobe_Port", BZ["strobe_port"], "body", deform=False),
    rig.Bone("Strobe_Starboard", BZ["strobe_star"], "body", deform=False),
    rig.Bone("Strobe_Tail", BZ["strobe_tail"], "body", deform=False),
    rig.Bone("Hub_FL", BZ["hubs"]["fl"], "body", deform=False), rig.Bone("Hub_FR", BZ["hubs"]["fr"], "body", deform=False),
    rig.Bone("Hub_RL", BZ["hubs"]["rl"], "body", deform=False), rig.Bone("Hub_RR", BZ["hubs"]["rr"], "body", deform=False),
]


def drone_parts():
    parts = hull_parts() + beak_parts() + tail_parts() + skid_parts() + battery_parts()
    for k in ("fl", "fr", "rl", "rr"):
        parts += arm_parts(k) + motor_parts(k) + prop_parts(k)
    b, g = gimbal_parts()
    return parts + b + g


def face_array(ob, name):
    a = np.empty(len(ob.data.polygons), np.float32)
    ob.data.attributes[name].data.foreach_get("value", a)
    return a


def assign_slots(ob):
    """Slot 0 M_Buzzard; the lens faces M_Buzzard_Eye; the strobe lenses M_Buzzard_Strobe (both read the Buzzard set:
    material instances that scale its E map by the game's eye brightness and strobe flash)."""
    me = ob.data
    me.materials.clear()
    names = ["M_Buzzard", "M_Buzzard_Eye", "M_Buzzard_Strobe"]
    for n in names:
        m = bpy.data.materials.get(n) or bpy.data.materials.new(n)
        me.materials.append(m)
    mid = np.rint(face_array(ob, "mid")).astype(int)
    idx = np.zeros(len(mid), np.int32)
    idx[mid == LENS] = 1
    idx[np.isin(mid, [LED_R, LED_G, LED_W])] = 2
    me.polygons.foreach_set("material_index", idx)
    return names


# ================================================================================================== TEXTURES

COL = {"hull": "1c1e24", "deck": "2b2e36", "oxblood": "7c151d", "prop": "30333a", "gun": "17181c", "skid": "22242a",
       "lens": "2a0806", "anod": "2c2f36", "alu": "a9adb3", "steel": "b4b7bb", "copper": "b0582c", "rubber": "141416",
       "wire_r": "a3141a", "wire_k": "141417", "nylon": "1a1a1c", "xt90": "d3a10e", "battery": "23272e",
       "strap": "1d1e20", "magnet": "8a8d92", "stator": "35373b", "ball": "17181c", "glass_k": "060708",
       "bore": "050505", "sleeve": "161719", "brass": "b08d47", "tape": "121214", "primer": "6e6a64",
       "dust": "7a7266", "soot": "0b0a09", "oil": "0e0c0a", "led_r": "ff3f38", "led_g": "3fff61", "led_w": "f3f3ff"}
LC = {k: lin(v) for k, v in COL.items()}


def twill(u, v, tow=0.0021, N=None, p=None):
    """2/2 twill carbon weave on surface coordinates (u, v) in metres. Returns (height 0..1, tone -1..1, warp mask)."""
    a, b = u / tow, v / tow
    i, j = np.floor(a), np.floor(b)
    fa, fb = a - i, b - j
    warp_up = ((i.astype(np.int64) + j.astype(np.int64)) // 2 % 2) == 0
    across = np.where(warp_up, fb, fa)                          # position across the tow on top
    along = np.where(warp_up, fa, fb)
    crown = np.sin(np.clip(across, 0, 1) * math.pi) ** 0.6     # rounded tow cross-section
    dip = 1.0 - 0.55 * np.sin(np.clip(along, 0, 1) * math.pi) ** 6 * 0   # tows pass over two, dip at crossings
    h = crown * dip
    if N is not None:
        fib = N.fbm(p * np.array([1.0, 1.0, 1.0], np.float32), 6000.0, 1, octave0=71)
        h = h + 0.12 * fib
    tone = np.where(warp_up, 1.0, -1.0)
    return h.astype(np.float32), tone.astype(np.float32), warp_up


def surface_uv(S, sel, axis_dir):
    """Coordinates on the surface for a weave whose warp runs along axis_dir (unit 3-vector, in the surface where
    possible): u along it, v around (normal x axis)."""
    p, n = S.p[sel], S.n[sel]
    a = np.asarray(axis_dir, np.float32)
    a = a / np.linalg.norm(a)
    t = a[None, :] - n * (n @ a)[:, None]
    bad = np.linalg.norm(t, axis=1) < 0.3
    t[bad] = np.cross(n[bad], np.array([0, 0, 1.0], np.float32))
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-6)
    bt = np.cross(n, t)
    return (p * t).sum(1), (p * bt).sum(1)


def paint_buzzard(G):
    S = W.Surf(G, 313)
    p, n, N = S.p, S.n, S.N
    up = np.clip(n[:, 2], 0, 1)
    down = np.clip(-n[:, 2], 0, 1)
    # ---------------------------------------------------------------- moulded composite (hull, beak, boom, pods)
    for ids, base, rough in (((HULL,), LC["hull"], 0.46), ((DECK,), LC["deck"], 0.44), ((BALL,), LC["ball"], 0.40)):
        sel = S.sel(*ids)
        if not sel.any():
            continue
        q = p[sel]
        mac = N.fbm(q, 18.0, 3, octave0=1)
        peel = N.fbm(q, 2600.0, 2, octave0=3)
        c = base[None, :] * (1 + 0.07 * mac[:, None])
        e = S.convex[sel]
        brk = N.fbm(q, 300.0, 3, octave0=5)
        scuff = tp.smooth(e * 1.3 + 0.45 * brk - 0.75, 0.0, 0.25)
        sc = S.scratches(0.7, sel=sel)
        light = base * 2.6 + 0.035
        c = c + (light[None, :] - c) * np.clip(scuff * 0.75 + sc * 0.35, 0, 1)[:, None]
        S.bc[sel] = c
        S.rough[sel] = rough + 0.05 * mac + 0.03 * peel + 0.18 * scuff - 0.06 * sc
        S.metal[sel] = 0.0
        S.h[sel] += 3e-6 * peel - 5e-6 * sc - 1.5e-5 * scuff * (brk > 0)
    # panel lines and moulded seams on the hull: offsets of the plan outline, a hatch on the belly
    hs = S.sel(HULL)
    if hs.any():
        q = p[hs]
        dx = (q[:, 0] + 0.02) / 0.28
        dy = q[:, 1] / 0.15
        lozr = np.abs(dx) + np.abs(dy) * 0.72
        lines = (tp.smooth(0.0012, 0.0, 0.0012 - np.abs((lozr - 0.62) * 0.2)) * (q[:, 2] < 0.0)).astype(np.float32)
        hatch = ((np.abs(q[:, 0] + 0.04) < 0.075) & (np.abs(np.abs(q[:, 1]) - 0.052) < 0.0007)) | \
                ((np.abs(q[:, 1]) < 0.052) & (np.abs(np.abs(q[:, 0] + 0.04) - 0.075) < 0.0007))
        hatch &= q[:, 2] < -0.03
        lin_ = np.maximum(lines, hatch.astype(np.float32))
        S.h[hs] -= 6e-5 * lin_
        S.bc[hs] *= (1 - 0.35 * lin_)[:, None]
    # ---------------------------------------------------------------- carbon: arms (warp along each arm), tray, plates
    car = S.sel(CARBON)
    if car.any():
        q = p[car]
        ang = np.arctan2(q[:, 1], q[:, 0])
        hub_a = np.array([math.atan2(h[1], h[0]) for h in BZ["hubs"].values()])
        k = np.argmin(np.abs(((ang[:, None] - hub_a[None, :]) + math.pi) % (2 * math.pi) - math.pi), axis=1)
        dirs = np.stack([np.cos(hub_a), np.sin(hub_a), np.zeros(4)], -1).astype(np.float32)[k]
        rad = np.hypot(q[:, 0], q[:, 1])
        dirs[rad < 0.10] = (1.0, 0.0, 0.0)
        nn = n[car]
        t = dirs - nn * (nn * dirs).sum(1, keepdims=True)
        bad = np.linalg.norm(t, axis=1) < 0.3
        t[bad] = np.array([1.0, 0, 0], np.float32)
        t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-6)
        bt = np.cross(nn, t)
        u, v = (q * t).sum(1), (q * bt).sum(1)
        # the weave at 45 degrees to the arm (bias-laid outer ply)
        uu, vv = (u + v) * 0.7071, (u - v) * 0.7071
        h, tone, wu = twill(uu, vv, 0.0024, N, q)
        mac = N.fbm(q, 25.0, 3, octave0=8)
        c = LC["deck"][None, :] * (0.78 + 0.14 * tone[:, None] + 0.10 * h[:, None] + 0.05 * mac[:, None])
        e = S.convex[car]
        brk = N.fbm(q, 260.0, 3, octave0=9)
        scuff = tp.smooth(e * 1.2 + 0.4 * brk - 0.72, 0.0, 0.25)
        sc = S.scratches(0.8, sel=car)
        c = c + (LC["deck"] * 2.2 - c) * np.clip(scuff * 0.5 + sc * 0.25, 0, 1)[:, None]
        S.bc[car] = c
        S.rough[car] = 0.24 + 0.08 * (1 - h) + 0.05 * mac + 0.30 * scuff + 0.12 * sc * 0 + 0.05 * tone
        S.metal[car] = 0.0
        S.h[car] += 3.5e-5 * h - 6e-6 * sc - 1e-5 * scuff
    # props: carbon twill along the blade, leading-edge wear, printed size marks
    pc = S.sel(PROPC)
    if pc.any():
        q = p[pc]
        hubs = np.array([h for h in BZ["hubs"].values()], np.float32)
        d2 = ((q[:, None, :2] - hubs[None, :, :2]) ** 2).sum(-1)
        k = np.argmin(d2, axis=1)
        rel = q - hubs[k]
        r = np.hypot(rel[:, 0], rel[:, 1])
        ra = np.arctan2(rel[:, 1], rel[:, 0])
        u, v = r, r * ra
        h, tone, wu = twill(u, v, 0.0018, N, q)
        c = LC["prop"][None, :] * (0.80 + 0.12 * tone[:, None] + 0.10 * h[:, None])
        le = tp.smooth(S.edge[pc], 0.3, 0.9) * tp.smooth(r, 0.10, 0.17)
        chips = tp.smooth(le * 1.2 + 0.5 * N.fbm(q, 900.0, 2, octave0=13) - 0.8, 0.0, 0.2)
        c = c + (LC["prop"] * 2.8 - c) * chips[:, None]
        S.bc[pc] = c
        S.rough[pc] = 0.22 + 0.10 * (1 - h) + 0.35 * chips
        S.metal[pc] = 0.0
        S.h[pc] += 2.5e-5 * h - 3e-5 * chips
    # ---------------------------------------------------------------- oxblood paint over composite: chips to black, primer
    ox = S.sel(OXBLOOD)
    if ox.any():
        q = p[ox]
        mac = N.fbm(q, 22.0, 3, octave0=20)
        brush = N.fbm(q * np.array([1, 1, 1], np.float32), (900.0, 70.0, 900.0), 2, octave0=21)
        c = LC["oxblood"][None, :] * (1 + 0.10 * mac[:, None] + 0.04 * brush[:, None])
        e = S.convex[ox]
        brk = N.fbm(q, 420.0, 3, octave0=22)
        brk2 = N.fbm(q, 90.0, 2, octave0=23)
        chip = tp.smooth(e * 1.4 + 0.45 * brk + 0.25 * brk2 - 0.80, 0.0, 0.10)
        primer = tp.smooth(e * 1.4 + 0.45 * brk + 0.25 * brk2 - 0.74, 0.0, 0.08) * (1 - chip)
        flake = tp.smooth(N.fbm(q, 160.0, 3, octave0=24), 0.52, 0.60) * tp.smooth(N.fbm(q, 18.0, 2, octave0=25), 0.1, 0.4)
        chip = np.maximum(chip, flake)
        c = c * (1 - primer[:, None]) + LC["primer"][None, :] * primer[:, None]
        c = c * (1 - chip[:, None]) + (LC["hull"] * 1.4)[None, :] * chip[:, None]
        S.bc[ox] = c
        S.rough[ox] = 0.52 + 0.06 * mac + 0.03 * brush - 0.1 * chip
        S.metal[ox] = 0.0
        S.h[ox] += 2e-6 * brush + 1.2e-5 * (1 - chip) - 0.2e-5 * primer
    # ---------------------------------------------------------------- anodised aluminium, bare aluminium, steel
    hand = np.zeros(len(p), np.float32)
    S.metal_finish(S.sel(ANOD), LC["anod"], LC["alu"], 0.34, 0.85, hand, wear_amount=1.2, scratch=0.6, orange=0.2)
    S.metal_finish(S.sel(ALU), LC["alu"], LC["alu"] * 1.1, 0.30, 1.0, hand, wear_amount=0.3, brushed=1.0, orange=0.1)
    S.metal_finish(S.sel(STEEL), LC["steel"], LC["steel"] * 1.1, 0.28, 1.0, hand, wear_amount=0.3, scratch=0.5, orange=0.1)
    S.metal_finish(S.sel(GUN), LC["gun"] * 1.6, LC["alu"] * 0.75, 0.55, 0.65, hand, wear_amount=1.0, scratch=0.7)
    S.metal_finish(S.sel(BARREL), LC["prop"] * 1.2, LC["alu"] * 0.7, 0.50, 0.7, hand, wear_amount=0.6, scratch=0.4)
    S.metal_finish(S.sel(SKID), LC["skid"] * 1.3, LC["alu"], 0.40, 0.75, hand, wear_amount=1.0, scratch=1.0)
    S.plain(S.sel(BRASS), LC["brass"], 0.35, 1.0)
    S.plain(S.sel(MAGNET), LC["magnet"], 0.32, 1.0)
    st = S.sel(STATOR)
    S.plain(st, LC["stator"], 0.45, 0.6)
    S.h += st * 1.2e-5 * np.sin(p[:, 2] / 0.00035 * math.pi) ** 2
    # machining rings on the motor caps and flanges (concentric about each hub)
    hubs = np.array([h for h in BZ["hubs"].values()], np.float32)
    d2 = ((p[:, None, :2] - hubs[None, :, :2]) ** 2).sum(-1)
    kh = np.argmin(d2, axis=1)
    rr = np.sqrt(d2[np.arange(len(p)), kh])
    an = S.sel(ANOD, ALU) & (up > 0.8) & (rr < 0.045)
    S.h += an * 1.5e-6 * np.sin(rr / 0.00018 * math.pi)
    S.rough -= an * 0.05
    # copper windings: enamelled wire turns stacked radially
    cu = S.sel(COPPER)
    if cu.any():
        q = p[cu]
        turns = np.sin(rr[cu] / 0.00042 * math.pi) ** 2
        c = LC["copper"][None, :] * (0.85 + 0.25 * turns[:, None] + 0.08 * N.fbm(q, 900.0, 2, octave0=30)[:, None])
        S.bc[cu] = c
        S.rough[cu] = 0.22 + 0.10 * (1 - turns)
        S.metal[cu] = 1.0
        S.h[cu] += 4e-5 * turns
    # ---------------------------------------------------------------- rubber, plastics, wires, battery, strap
    S.plain(S.sel(RUBBER), LC["rubber"], 0.80, 0.0, var=0.08, rvar=0.06)
    S.plain(S.sel(NYLON), LC["nylon"], 0.55, 0.0, var=0.05, rvar=0.05)
    S.plain(S.sel(XT90), LC["xt90"], 0.42, 0.0, var=0.05, rvar=0.04)
    S.plain(S.sel(WIRE_R), LC["wire_r"], 0.50, 0.0, var=0.06, rvar=0.05)
    S.plain(S.sel(WIRE_K), LC["wire_k"], 0.52, 0.0, var=0.06, rvar=0.05)
    S.plain(S.sel(TAPE), LC["tape"], 0.38, 0.0, var=0.05, rvar=0.06)
    S.plain(S.sel(GLASS_K), LC["glass_k"], 0.06, 0.0, var=0.02, rvar=0.01)
    S.plain(S.sel(BORE), LC["bore"], 0.7, 0.3)
    sl = S.sel(SLEEVE)
    if sl.any():
        q = p[sl]
        a1 = N.fbm(q, 90.0, 1, octave0=33)
        weave = np.sin((q[:, 0] + q[:, 1] + q[:, 2]) / 0.0016 * math.pi) * np.sin((q[:, 0] - q[:, 1] + q[:, 2] * 0.5) / 0.0016 * math.pi)
        S.bc[sl] = LC["sleeve"][None, :] * (1 + 0.35 * weave[:, None] + 0.1 * a1[:, None])
        S.rough[sl] = 0.55 - 0.12 * weave
        S.metal[sl] = 0.0
        S.h[sl] += 2.5e-5 * weave
    stp = S.sel(STRAP)
    if stp.any():
        q = p[stp]
        weave = np.sin(q[:, 1] / 0.0007 * math.pi) * np.sin(q[:, 0] / 0.0009 * math.pi + q[:, 2] / 0.0009 * math.pi)
        S.bc[stp] = LC["strap"][None, :] * (1 + 0.25 * weave[:, None])
        S.rough[stp] = 0.78 - 0.06 * weave
        S.metal[stp] = 0.0
        S.h[stp] += 2e-5 * weave
    bt = S.sel(BATTERY)
    if bt.any():
        q = p[bt]
        wr = N.ridged(q, (60.0, 220.0, 60.0), 2, octave0=40)
        ed = tp.smooth(S.edge[bt], 0.2, 0.8)
        S.bc[bt] = LC["battery"][None, :] * (1 + 0.06 * N.fbm(q, 40.0, 2, octave0=41)[:, None])
        S.rough[bt] = 0.30 + 0.12 * ed + 0.05 * wr
        S.metal[bt] = 0.0
        S.h[bt] += 1.5e-5 * tp.smooth(wr, 0.85, 1.0) * ed
        lab = tp.text_image([("VLT-6S", 256, 130, 70), ("22000 mAh  22.2 V", 256, 230, 40), ("25C  488 Wh", 256, 300, 40),
                             ("DO NOT PUNCTURE", 256, 400, 26)], 512)
        lbl = tp.raster_plane(lab, q, (0, 1), (-0.140, -0.055), (0.18, 0.11)) * (n[bt, 2] < -0.8)
        frame = tp.raster_plane(np.pad(np.ones((440, 440), np.float32), 36), q, (0, 1), (-0.140, -0.055), (0.18, 0.11)) * (n[bt, 2] < -0.8)
        S.bc[bt] = S.bc[bt] * (1 - 0.6 * frame[:, None]) + LC["xt90"][None, :] * 0.55 * frame[:, None] * 0
        S.bc[bt] = S.bc[bt] + (np.array([0.62, 0.60, 0.55], np.float32) - S.bc[bt]) * lbl[:, None]
    # ---------------------------------------------------------------- lenses and strobes (E)
    le = S.sel(LENS)
    if le.any():
        q = p[le]
        rad = np.hypot(q[:, 1] - BZ["eye"][1], q[:, 2] - BZ["eye"][2]) / BZ["lens_r"]
        rings = 0.5 + 0.5 * np.cos(rad * math.pi * 7)
        S.bc[le] = LC["lens"][None, :] * (0.7 + 0.5 * rings[:, None])
        S.rough[le] = 0.03
        S.metal[le] = 0.0
        glow = np.clip(1.0 - rad, 0, 1) ** 0.6 * (0.55 + 0.45 * rings) + tp.smooth(0.30 - np.abs(rad - 0.62), 0.0, 0.3) * 0.6
        S.emit[le] = np.array([1.0, 0.09, 0.05], np.float32)[None, :] * np.clip(glow, 0, 1)[:, None]
    for mid, key in ((LED_R, "led_r"), (LED_G, "led_g"), (LED_W, "led_w")):
        sel = S.sel(mid)
        if sel.any():
            S.bc[sel] = LC[key][None, :] * 0.55 + 0.25
            S.rough[sel] = 0.08
            S.metal[sel] = 0.0
            S.emit[sel] = LC[key][None, :]
    # ---------------------------------------------------------------- oil thrown back from the motors, dust, grime
    rel = p[:, :2] - hubs[kh, :2]
    behind = tp.smooth(-rel[:, 0], -0.01, 0.03) * tp.smooth(0.16 - rr, 0.0, 0.08)
    streak = tp.smooth(N.fbm(np.stack([p[:, 0] * 0.15, p[:, 1], p[:, 2]], -1), (40.0, 700.0, 700.0), 2, octave0=50), 0.15, 0.6)
    oil = np.clip(behind * streak * (p[:, 2] < 0.075) * (1 - S.sel(PROPC, COPPER, LENS, LED_R, LED_G, LED_W)), 0, 1) * 0.8
    S.bc = S.bc + (LC["oil"][None, :] - S.bc) * (oil * 0.55)[:, None]
    S.rough = S.rough - 0.20 * oil
    dust = np.clip(tp.smooth(up, 0.4, 0.95) * (0.35 + 0.5 * N.fbm(p, 60.0, 3, octave0=60)) * 0.55, 0, 1)
    dust *= 1 - S.sel(LENS, LED_R, LED_G, LED_W, GLASS_K) * 0.85
    S.bc = S.bc + (LC["dust"][None, :] * 0.6 - S.bc) * (dust * 0.45)[:, None]
    S.rough = S.rough + (0.85 - S.rough) * dust * 0.5
    S.grime(0.9, dust_col=LC["dust"])
    # crew unit marks: B-07 in off-white on both fins (stencil), a small warning decal on each arm root
    fin = S.sel(OXBLOOD) & (p[:, 0] < -0.40)
    if fin.any():
        img = tp.text_image([("B-07", 256, 256, 150)], 512)
        for s in (1, -1):
            v = tp.raster_plane(img, p, (0, 2), (-0.515, 0.05), (0.07, 0.07)) * fin * (n[:, 1] * s > 0.3) * (p[:, 1] * s > 0)
            S.bc = S.bc + (np.array([0.62, 0.60, 0.56], np.float32) - S.bc) * (v * 0.85)[:, None]
            S.h += 4e-6 * v
    return S.channels(height_blur=0.5)


# ================================================================================================== PIPELINE

SKINNED = {}


def tex_res(ctx, full):
    return full if ctx.args.res >= 2048 else max(128, full * ctx.args.res // 4096)


def unwrap(ob, res):
    mid = np.rint(face_array(ob, "mid"))
    w = np.ones(len(mid), np.float32)
    w[np.isin(mid, [STATOR, MAGNET, BORE])] = 0.35
    w[np.isin(mid, [COPPER])] = 0.5
    return geo.uv_unwrap(ob, res=res, angle=52.0, margin_px=5, pack="AABB", weights=w)



def write_unique(ctx, ob, set_name, res, painter, **kw):
    d = paths.texture_set(set_name)
    old = bake.read_set(set_name)
    stale = not old or old.get("uv_hash") != geo.uv_hash(ob) or old.get("resolution", [0])[0] != res
    if ctx.args.bake and (stale or ctx.args.force or ctx.args.rebake_unique) or not old:
        ctx.log("texture %s at %d px" % (set_name, res))
        G = tp.geometry_maps(ob, res=res, samples=8 if res >= 2048 else 16, bevel_radius=0.0015)
        ch = painter(G, **kw)
        dens = geo.uv_texel_density(ob, res)
        bake.write_set(set_name, ch, meta={"kind": "unique", "asset": ob.name, "uv_hash": geo.uv_hash(ob),
                                           "texel_density_px_per_m": round(dens, 1),
                                           "authoring": "mi.texpaint: geometry maps + numpy layers (assets/buzzard.py)"})
        ctx.log("  wrote %s (%.0f px/m)" % (d, dens))
    elif stale:
        ctx.log("WARNING %s: set is stale (mesh changed); run with --bake" % set_name)
    if set_name not in ctx.sets:
        ctx.sets.append(set_name)
    return d


def preview_materials(set_dir, names, eye=0.0, strobe=0.0):
    """Blender stand-ins of the Unreal materials: every slot reads the set; M_Buzzard shows no emission, the eye and
    strobe slots scale E (the game drives them)."""
    out = {}
    for n in names:
        m = bpy.data.materials.get(n)
        if m is not None:
            bpy.data.materials.remove(m)
        m = mat.from_texture_set(set_dir, name=n, masks=False, macro=0.0, ao_strength=0.0, alpha="none")
        b = mat.principled(m)
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = eye if n.endswith("Eye") else (strobe if n.endswith("Strobe") else 0.0)
        out[n] = m
    return out


def build_drone(ctx):
    col = ctx.col
    parts = drone_parts()
    ob = geo.join(parts, "SK_Buzzard", col)
    arm = rig.armature("SKEL_Buzzard", BONES, col)
    names = assign_slots(ob)
    res = tex_res(ctx, 4096)
    dens = unwrap(ob, res)
    ctx.log("SK_Buzzard: %d tris, %.0f px/m" % (geo.stats(ob)["triangles"], dens))
    d = write_unique(ctx, ob, "Buzzard", res, paint_buzzard)
    mats = preview_materials(d, names, eye=6.0, strobe=4.0)
    for i, n in enumerate(names):
        ob.data.materials[i] = mats[n]
    geo.ensure_wear(ob)
    rig.bind(ob, arm)
    SKINNED["SK_Buzzard"] = {"ob": ob, "arm": arm, "expect_size": (1.02, 1.07, 0.35), "poses": drone_poses(),
                             "notes": DRONE_NOTES}
    return [ob, arm]


def drone_poses():
    return [{"name": "props turned (fl, rr +60 deg; fr, rl -45 deg about the hub axis)",
             "bones": {"prop_fl": {"rotate": ((0, 0, 1), 60.0)}, "prop_rr": {"rotate": ((0, 0, 1), 60.0)},
                       "prop_fr": {"rotate": ((0, 0, 1), -45.0)}, "prop_rl": {"rotate": ((0, 0, 1), -45.0)}}},
            {"name": "gimbal pitched 77 deg down", "bones": {"gimbal": {"rotate": ((0, 1, 0), 77.0)}}},
            {"name": "gimbal yawed 86 deg to the right", "bones": {"gimbal": {"rotate": ((0, 0, 1), -86.0)}}},
            {"name": "gimbal pitched 29 deg up", "bones": {"gimbal": {"rotate": ((0, 1, 0), -29.0)}}}]


DRONE_NOTES = (
    "The Buzzard, skinned (rigid). Nose +X, up +Z, the drone's right = -Y (gun on -Y, red port strobe on +Y); origin "
    "at the centre of the airframe (no ground pivot). Bones, rest orientation = drone axes: body (root); prop_fl "
    "(0.27, 0.33, 0.075), prop_fr (0.27, -0.33), prop_rl (-0.30, 0.35), prop_rr (-0.30, -0.35): spin about local +Z, "
    "fl and rr counter-clockwise seen from above (+Z), fr and rl clockwise (41 rad/s x power); hide one when killed. "
    "gimbal (0.17, 0, -0.085): yaw about +Z +-86 deg, pitch about +Y (+77 deg = down, -29 deg = up); carries the eye, "
    "gun, ammunition box and their mount. Sockets: Eye (0.255, 0, -0.10), GunMuzzle (0.37, -0.062, -0.13) on gimbal; "
    "Strobe_Port, Strobe_Starboard, Strobe_Tail, Hub_FL/FR/RL/RR on body (blur discs at hub + 0.022 Z). Slots: "
    "M_Buzzard (unique 4K set Buzzard: BC, N, ORM, E; no emission on this slot), M_Buzzard_Eye (lens: E x eye "
    "brightness, linear (1, 0.09, 0.05)), M_Buzzard_Strobe (three strobe lenses: E x flash).")


# --------------------------------------------------------------------------------------------------- build hooks

def build(ctx):
    only = [o.lower() for o in (ctx.args.only or GROUPS)]
    objs = []
    if "drone" in only or "wreck" in only:
        objs += build_drone(ctx)
    if "fx" in only and "build_fx" in globals():
        objs += build_fx(ctx)
    if "wreck" in only and "build_wreck" in globals():
        objs += build_wreck(ctx)
    return objs


def on_export(ctx, objs):
    for name, a in ctx.assets.items():
        export.export_asset(a["ob"], ctx.family, a["collision"], a["cover_height"], a["notes"], a["pivot"],
                            a["expect_size"], slots=a["slots"])
    only = [o.lower() for o in (ctx.args.only or GROUPS)]
    if "drone" not in only:
        return
    for name, s in SKINNED.items():
        ob, arm = s["ob"], s["arm"]
        err, warn = rig.validate(ob, arm, s["expect_size"])
        for w in warn:
            print("    warning %s: %s" % (name, w))
        if err:
            raise ValueError("%s failed validation:\n  %s" % (name, "\n  ".join(err)))
        path = rig.export_skinned(ob, arm)
        rep = rig.verify(path, s["poses"])
        ok = rep["ok"] and rep["glb"]["all_axes_are_asset_axes"]
        ctx.log("%s: %s, poses %s, joint axes = drone axes: %s" % (
            name, os.path.relpath(path, paths.art), ", ".join("%s %.1e m" % (p["name"][:24], p["max_error_m"]) for p in rep["poses"]),
            rep["glb"]["all_axes_are_asset_axes"]))
        if not ok:
            raise ValueError("%s: re-import proof failed: %s" % (name, json.dumps(rep)[:2000]))
        sockets = {b.name: [round(v, 5) for v in b.head_local] for b in arm.data.bones if not b.use_deform}
        se = export.set_entry("Buzzard") or {}
        extra = {"M_Buzzard": {"emissive_scale": 0.0},
                 "M_Buzzard_Eye": {"set": "Buzzard", "workflow": "unique", "textures": se.get("textures"),
                                   "emissive_scale": "eye brightness (spec 3.8.5), E colour linear (1, 0.09, 0.05)"},
                 "M_Buzzard_Strobe": {"set": "Buzzard", "workflow": "unique", "textures": se.get("textures"),
                                      "emissive_scale": "strobe flash 0..1 (E holds red / green / white)"}}
        entry = rig.manifest_entry(ob, arm, ctx.family, path, s["notes"], sockets=sockets, poses_report=rep, slots=extra)
        export.write_manifest([entry], ["Buzzard"])
