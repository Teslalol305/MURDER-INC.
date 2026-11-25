"""Round 4, lane 2: the parts kit, geometry II: the 4x scope, the muzzle devices, the grips and the laser module.
Same conventions as _weapons_parts_geo.py (mount at the origin, X forward, Z up, metres; mm in the code)."""
import math

import numpy as np

from mi import geo
from assets import weapons as W
from assets import _weapons_parts_geo as G
from assets._weapons_parts_geo import (AL, STEELD, HEAT, STAIN, POLY, RUBBER, WOODG, BRASSM, RED, CARBON, LENS, RET, BORED,
                                       MM, fin, retag, mm, box_mm, lathe_x, lathe_y, lathe_z, prism_yz, prism_xz, prism_xy,
                                       ring_x, knurled, axis_to_z, axis_to_ny, move, clamp, screw_head_y, screw_head_z)


# ---------------------------------------------------------------------------------------------------- SCOPE 4x
def scope_4x(pi=0):
    """Compact fixed 4x tube scope: monolithic 52 mm clamp with two cross-bolts, 30 mm main tube on axis Z +27.5, objective
    bell R 21 x 38, ocular bell R 19 x 28, X -65..+85, elevation turret on top (tallest Z 53.5), windage turret on the
    right only, knurled lens rings. Hollow: the ocular bore R 14, a dark matte interior, glass in a flat translucent slot,
    the reticle a 20 mm plane at X 0. SightEye (-67, 0, 27.5)."""
    AX = 27.5
    objs = clamp(52.0, part=pi, name="SC", screws=2)
    # one closed-profile body: eyepiece bell, tube, objective bell (outer and inner wall in one lathe)
    prof = [(-65.0, 14.0), (-65.0, 17.6), (-64.0, 18.2), (-58.0, 18.2), (-56.8, 19.0), (-40.0, 19.0), (-36.0, 15.6), (-35.0, 15.0),
            (46.0, 15.0), (47.5, 16.0), (52.0, 21.0), (82.0, 21.0), (82.8, 21.0), (85.0, 21.0), (85.0, 19.4), (80.0, 19.4),
            (52.0, 17.0), (46.0, 14.0), (-35.0, 14.0), (-37.0, 14.0), (-45.0, 14.0)]
    body = lathe_x(prof, 56, at=(0, 0, AX), closed=True, fillet=0.4, fseg=1, name="SCBody")
    fin(body, AL, pi)
    retag(body, BORED, lambda x, y, z: (np.hypot(y, z - AX * MM) < 19.5 * MM) & (x > -64.5 * MM) & (x < 84.5 * MM)
          & ((np.hypot(y, z - AX * MM) < 14.6 * MM) | (x > 46.5 * MM)))
    objs.append(body)
    # lens rings: knurled collars at the eyepiece end and at the objective's mouth (1.5 mm pitch)
    objs.append(fin(rings_x(-65.0, -57.4, 18.8, 30, AX, "SCEye"), STEELD, pi))
    objs.append(fin(rings_x(76.0, 85.0, 22.0, 40, AX, "SCObj", bore=19.5), STEELD, pi))
    # mount rings round the tube and the riser block that joins them to the plate
    objs.append(fin(box_mm(-25.0, 25.0, -9.5, 9.5, 5.0, 15.0, bevel=1.2, name="SCRiser"), AL, pi))
    for x0 in (-24.0, 10.0):
        r = lathe_x([(x0, 15.0), (x0, 18.4), (x0 + 14.0, 18.4), (x0 + 14.0, 15.0)], 48, at=(0, 0, AX), closed=True, fillet=0.5,
                    fseg=1, name="SCRing")
        objs.append(fin(r, AL, pi))
    # elevation turret on top (R 11 base, knurled R 9.6 cap, tallest Z 53.5) and windage turret on the right only
    for axis_fn, at, nm in ((axis_to_z, (6.0, 0.0, AX + 14.0), "SCElev"), (axis_to_ny, (6.0, -14.0, AX), "SCWind")):
        base = knurled(11.0, 5.0, 20, 0.35, 0.8, name=nm + "Base")
        cap = knurled(9.6, 7.0, 24, 0.40, 0.7, name=nm + "Cap")
        move(cap, 5.0, 0, 0)
        for o, m_ in ((base, AL), (cap, STEELD)):
            axis_fn(o, at)
            objs.append(fin(o, m_, pi))
    # glass: a flat slot at the eyepiece and at the objective; the reticle plane at X 0 facing the eye
    for x, r_, nm in ((-63.2, 13.9, "SCLensE"), (80.8, 19.3, "SCLensO")):
        d = lathe_x([(x - 0.7, 0.0), (x - 0.7, r_), (x + 0.7, r_), (x + 0.7, 0.0)], 48, at=(0, 0, AX), fillet=0.2, fseg=1, name=nm)
        objs.append(fin(d, LENS, pi))
    objs.append(fin(box_mm(-0.1, 0.1, -10.0, 10.0, AX - 10.0, AX + 10.0, bevel=0.0, name="SCRet"), RET, pi))
    return objs, {"SightEye": mm(-67.0, 0, AX)}


def rings_x(x0, x1, r, teeth, axis_z, name, bore=14.1):
    """A knurled collar along X from x0 to x1 around the axis (0, 0, axis_z) (mm), bored through (R `bore`): the optical path."""
    ob = knurled(r, x1 - x0, teeth, 0.30, 0.6, name=name)
    W.cut(ob, lathe_x([(-1.0, 0.0), (-1.0, bore), (x1 - x0 + 1.0, bore), (x1 - x0 + 1.0, 0.0)], 48, name="Bore"))
    return move(ob, x0, 0, axis_z)


# --------------------------------------------------------------------------------------------- muzzle devices
def suppressor(pi=0, length=210.0, r=19.5, collar_r=12.5, collar_l=16.0, rec_r=9.0, rec_d=12.0, bore_r=5.5, flutes_n=12,
               mid=STEELD, name="SU", front_mid=None, plug_relief=False, seg=48):
    """Long rifle / SMG suppressor, 210 mm, body R 19.5: a rear mount collar R 12.5 x 16 with an internal recess R 9.0 x 12
    deep (swallows the barrel stub R 8.5), 12 shallow 0.6 mm flutes, a 2 mm end cap with an 11 mm bore. Origin = the rear
    face on the bore axis; Muzzle at X +210."""
    objs = []
    L = length
    # rear collar with the recess, the shoulder into the body
    rear = lathe_x([(rec_d, 0.0), (rec_d, rec_r), (0.0, rec_r), (0.0, collar_r), (collar_l, collar_r), (collar_l + 1.5, r - 1.2),
                    (collar_l + 3.0, r), (collar_l + 3.0, 0.0)], seg, closed=False, fillet=0.5, fseg=1, name=name + "Rear")
    if plug_relief:                      # the NINE's recoil-spring plug stands 1.0 mm proud of the slide's front face at Z -9.2..-11.8
        W.cut(rear, box_mm(-1.0, 1.65, -3.4, 3.4, -12.6, -7.0, bevel=0.0, name="PlugRelief"))
    objs.append(fin(rear, mid, pi))
    # fluted body (rings straight along the tube, the flutes fade in and out)
    fl = G.flutes(0.6, flutes_n)
    ramp = lambda x: min(1.0, max(0.0, (x - (collar_l + 8.0)) / 6.0)) * min(1.0, max(0.0, (L - 8.0 - 4.0 - x) / 6.0))
    xs = [collar_l + 3.0, collar_l + 8.0, collar_l + 14.0, L - 18.0, L - 12.0, L - 8.0]
    body = ring_x(lambda x, th: r + fl(th) * ramp(x), xs, m=flutes_n * 6, name=name + "Body")
    objs.append(fin(body, mid, pi))
    # a thread-relief band and the end cap
    cap = lathe_x([(L - 8.0, 0.0), (L - 8.0, r - 0.2), (L - 6.5, r + 0.3), (L - 2.0, r + 0.3), (L - 0.6, r - 0.9), (L, r - 1.6),
                   (L, bore_r + 1.2), (L - 1.0, bore_r), (L - 7.0, bore_r), (L - 7.0, 0.0)], seg, closed=False, fillet=0.35, fseg=1,
                  name=name + "Cap")
    objs.append(fin(cap, front_mid if front_mid is not None else mid, pi))
    # raised bands along the tube (clamshell rings) and six screws on the end cap's face
    for xb in ((60.0, 120.0, 172.0) if L > 180 else (50.0, 100.0)):
        band = lathe_x([(xb - 1.6, r - 0.3), (xb - 1.6, r + 0.55), (xb + 1.6, r + 0.55), (xb + 1.6, r - 0.3)], max(24, seg - 12), closed=True, fillet=0.3,
                       fseg=1, name=name + "Ring")
        objs.append(fin(band, mid, pi))
    rf = (r + bore_r) / 2.0
    for k in range(6):
        a = k * math.pi / 3.0 + 0.26
        sc = lathe_x([(L - 0.3, 0.0), (L - 0.3, 1.5), (L + 0.55, 1.5), (L + 0.55, 0.0)], 8, at=(0, rf * math.cos(a), rf * math.sin(a)), name=name + "FaceScrew")
        objs.append(fin(sc, STEELD if mid != STAIN else STAIN, pi))
    # three wipe grooves on the collar
    for x in ((5.0, 10.0) if L > 180 else (5.0,)):
        objs.append(fin(lathe_x([(x - 0.4, collar_r - 0.05), (x - 0.4, collar_r + 0.12), (x + 0.4, collar_r + 0.12), (x + 0.4, collar_r - 0.05)],
                                24, closed=True, name=name + "Band"), mid, pi))
    for o in objs:
        geo.transform(o, loc=(0.05 * MM, 0, 0))                  # a 0.05 mm relief off the gun's mount face
    return objs, {"Muzzle": mm(L, 0, 0)}


def suppressor_pistol(pi=0):
    """Pistol suppressor, 155 mm, body R 16.0 (top Z +16, 2.5 mm under the NINE's sight line at +18.5), rear collar R 11.5 x
    10 with a recess R 7.2 x 6 deep over the barrel's crown stub (R 6.8), ten 0.5 mm flutes, a 10 mm end bore. Brushed
    stainless, heat-darkened front 60 mm (in the texture). Origin = the slide's front face; Muzzle at X +155."""
    return suppressor(pi, length=155.0, r=16.0, collar_r=11.5, collar_l=10.0, rec_r=7.2, rec_d=6.0, bore_r=5.0, flutes_n=10,
                      mid=STAIN, name="SP", plug_relief=True, seg=32)


def compensator(pi=0):
    """Three-chamber compensator, 62 mm, R 15: rear collar with a recess R 9.0 x 12.6 (the specification says 10, the guns' stub is 12 long), a chamber through the body, three 4 x 14
    mm vertical ports on top and one angled port per side, a solid front face with a 7 mm bore and a scalloped crown, carbon
    in the ports (texture). Origin on the bore at the mount; Muzzle at X +62."""
    prof = [(12.6, 0.0), (12.6, 9.0), (0.0, 9.0), (0.0, 12.5), (14.0, 12.5), (15.5, 15.0), (56.0, 15.0), (58.0, 14.2), (61.2, 12.8),
            (62.0, 11.4), (62.0, 3.5), (55.0, 3.5), (55.0, 5.2), (14.2, 5.2), (14.2, 0.0)]
    body = lathe_x(prof, 40, closed=False, fillet=0.3, fseg=1, name="CPBody")
    # the ports: three vertical slots on top, one angled slot per side, six scallops in the crown
    cut = []
    for x0 in (23.0, 33.0, 43.0):
        cut.append(box_mm(x0 - 2.0, x0 + 2.0, -7.0, 7.0, 2.0, 18.0, bevel=0.0, name="CPPort"))
    for sgn in (1, -1):
        c = box_mm(24.0, 38.0, -2.0, 2.0, 2.0, 18.0, bevel=0.0, name="CPSide")
        geo.transform(c, rot=(sgn * 68.0, 0, 0), loc=(0, 0, 0))
        cut.append(c)
    for k in range(6):
        c = box_mm(59.0, 63.0, -1.4, 1.4, 11.0, 17.0, bevel=0.0, name="CPScallop")
        geo.transform(c, rot=(k * 60.0 + 30.0, 0, 0))
        cut.append(c)
    for c in cut:
        W.cut(body, c)
    fin(body, G.STEELB, pi)
    geo.transform(body, loc=(0.05 * MM, 0, 0))                   # a 0.05 mm relief off the gun's mount face
    return [body], {"Muzzle": mm(62.0, 0, 0)}


# -------------------------------------------------------------------------------------------------------- GRIPS
def grip_body(height, radius, grooves, cap_r, cap_h, neck_r=8.5, neck_h=6.0, oval=0.93, name="GB", top=0.0, slot=True):
    """A vertical grip body about the Z axis hanging from z = top (mm) down to top - height: a neck, the body with finger
    grooves [(centre depth below the top, groove depth)], a flared cap with a lanyard slot (through along Y). Profile (z, r)."""
    zb = -(height - cap_h)
    prof = [(0.0, 0.0), (0.0, neck_r), (-neck_h, neck_r), (-neck_h - 1.2, radius - 1.6), (-neck_h - 2.6, radius)]
    for zc, depth in grooves:
        prof += [(-zc + 4.5, radius), (-zc + 2.0, radius - depth), (-zc - 2.0, radius - depth), (-zc - 4.5, radius)]
    prof += [(zb + 1.0, radius), (zb, radius + 0.2), (zb - 2.0, cap_r), (-height + 1.0, cap_r), (-height, cap_r - 1.2), (-height, 0.0)]
    ob = lathe_z(prof, 28, at=(0, 0, top), fillet=0.4, fseg=1, name=name)
    if slot:
        W.cut(ob, box_mm(-1.6, 1.6, -30.0, 30.0, top - height + 3.0, top - height + 7.0, bevel=0.0, name="Slot"))
    geo.transform(ob, scale=(oval, 1.0, 1.0))
    return ob


def foregrip_vertical(pi=0):
    """Vertical foregrip on an underside MI-R rail: clamp 40 x 21.2 mm (two cross-bolts), a 6 mm neck, body O30 x 70 with three
    finger grooves, a stippled polymer shell, a flared O34 cap with a lanyard slot; total height 92. Origin = the lug
    undersides plane, the part hangs in -Z; SupportHand (0, 0, -52)."""
    objs = clamp(40.0, part=pi, under=True, plate_t=5.0, screws=1, name="FV")
    body = grip_body(92.0 - 5.0, 15.0, [(28.0, 1.3), (42.0, 1.3), (56.0, 1.3)], 17.0, 9.0, name="FVBody", top=-5.0)
    objs.append(fin(body, POLY, pi))
    return objs, {"SupportHand": mm(0, 0, -52.0)}


def foregrip_angled(pi=0):
    """Angled foregrip on an underside MI-R rail: clamp plate 55 x 21.2 mm, a wedge body leaning forward and down at 38 deg
    with a thumb shelf on its front, stippled panels left and right, 2 mm radii; about 78 x 30 x 58 mm. The palm rests on the
    rear ramp (SupportHand (-12, 0, -30)). Origin = the lug undersides plane, hanging in -Z."""
    objs = clamp(55.0, part=pi, under=True, plate_t=5.0, screws=1, name="FA")
    side = [(-26.0, -4.5), (-19.0, -16.0), (-12.0, -30.0), (-5.5, -43.0), (0.0, -52.0), (3.0, -58.0), (30.0, -58.0), (34.0, -52.0),
            (31.0, -41.0), (24.0, -28.0), (17.0, -19.0), (14.0, -14.5), (28.0, -14.5), (28.0, -4.5)]
    wedge = prism_xz(side, -13.5, 13.5, bevel=1.8, seg=3, name="FAWedge", fillet=2.0)
    for sy in (1, -1):                                       # the stippled panels: 0.8 mm pockets in both flanks
        W.cut(wedge, box_mm(2.0, 21.0, 12.7 if sy > 0 else -15.0, 15.0 if sy > 0 else -12.7, -50.0, -22.0, bevel=0.0, name="Panel"))
    objs.append(fin(wedge, POLY, pi))
    # the thumb shelf: a ledge on the front ramp, and two retention screws on the right
    shelf = box_mm(12.0, 28.0, -14.5, 14.5, -15.5, -13.5, bevel=0.8, name="FAShelf")
    objs.append(fin(shelf, POLY, pi))
    return objs, {"SupportHand": mm(-12.0, 0, -30.0)}


# the CHOPPER's folded stock plate under the handguard: a curved 2.5 mm band, 30 mm wide with 5 mm flanges, bottom
# z(x) = -63.9 + (x - 285)^2 / 240 (mm, gun space); the saddle hangs from it. Socket Underbarrel (305, 0, -62.3).
def plate_z(x_gun_mm):
    return -63.9 + (x_gun_mm - 285.0) ** 2 / 240.0


def foregrip_vertical_wood(pi=0):
    """The CHOPPER's vertical grip: a saddle clamp that hugs the folded stock's curved shoulder plate (the lowest thing under
    the handguard: a 2.5 mm band 30 mm wide, bottom Z -62.3 at the mount, arc R 120), 36 x 46 mm with ears rising 18 mm on
    both sides, a steel strap under the plate and two 5 mm bolts, and a wooden body O30, 82 mm tall in all, hanging to Z
    -145 (gun space). Origin = Underbarrel (305, 0, -62.3); SupportHand (0, 0, -48)."""
    objs = []
    X0 = 305.0
    zs = lambda x: plate_z(X0 + x) - plate_z(X0)               # the plate's underside relative to the mount (mm)
    xs = np.linspace(-18.0, 18.0, 13)
    # saddle floor: a 4 mm band under the plate following its arc, 36 long, 30.6 + 2 x 3 wide
    top = [(float(x), float(zs(x)) - 0.25) for x in xs]
    bot = [(float(x), float(zs(x)) - 4.25) for x in xs[::-1]]
    floor = prism_xz(top + bot, -18.3, 18.3, bevel=0.5, seg=2, name="FWFloor", fillet=0.0)
    objs.append(fin(floor, G.STEELB, pi))
    # ears: 3 mm side plates hugging the plate's flanges, 18 mm tall above the floor
    for s in (1, -1):
        e_top = [(float(x), float(zs(x)) + 17.0) for x in xs]
        e_bot = [(float(x), float(zs(x)) - 4.0) for x in xs[::-1]]
        ear = prism_xz(e_top + e_bot, s * 15.5 if s > 0 else -18.5, s * 18.5 if s > 0 else -15.5, bevel=0.5, seg=2, name="FWEar")
        objs.append(fin(ear, G.STEELB, pi))
        # clamp bolts through the ears: heads on the right, nuts on the left
    for bx in (-9.0, 9.0):
        objs.append(fin(screw_head_y(bx, float(zs(bx)) + 6.0, -18.5, r=3.4, h=2.2, sign=-1, seg=12, name="FWBolt"), STEELD, pi))
        objs.append(fin(screw_head_y(bx, float(zs(bx)) + 6.0, 18.5, r=3.0, h=1.8, sign=+1, seg=12, name="FWNut"), STEELD, pi))
    # strap: a thin band round the floor's middle
    objs.append(fin(box_mm(-4.0, 4.0, -18.6, 18.6, float(zs(0)) - 4.9, float(zs(0)) - 3.6, bevel=0.4, name="FWStrap"), STEELD, pi))
    # the wooden body: neck under the floor, O30 x oval body with three finger grooves, cap with a lanyard slot
    body = grip_body(77.7, 15.0, [(26.0, 1.2), (40.0, 1.2), (54.0, 1.2)], 16.5, 8.0, name="FWBody", top=float(zs(0)) - 5.0)
    objs.append(fin(body, WOODG, pi))
    return objs, {"SupportHand": mm(0, 0, -48.0)}


# ------------------------------------------------------------------------------------------------------- LASER
def laser_module(pi=0):
    """Compact red laser module 46 x 22 x 28 mm for an underside rail (the NINE's dust cover, the SHORTY's MI-R forend): a base
    plate with two side walls hugging the rail's flanks (no hooks, no keys: it seats on either dovetail), a moulded polymer
    body, a 9 mm emitter window in a recessed pocket on the front face (a steel lens ring and the red emitter), a knurled side
    wheel, a rubber button, a battery cap, four screws. Origin = the rail's underside plane at the middle of the module; Beam at
    (+23.5, 0, -12.5) along +X."""
    objs = []
    # plate under the rail (z -4..-0.03) and the walls along the dovetail's flanks (inner face 10.75, up to +3.2)
    objs.append(fin(box_mm(-20.0, 20.0, -13.0, 13.0, -4.0, -G.FACE_GAP, bevel=0.8, name="LZPlate"), POLY, pi))
    for s in (1, -1):
        wall = box_mm(-19.0, 19.0, 10.75 if s > 0 else -13.0, 13.0 if s > 0 else -10.75, -4.0, 3.2, bevel=0.5, name="LZWall")
        objs.append(fin(wall, G.STEELB, pi))
    # moulded body: x -23..+23, y +-11, z -4..-28, 2.6 mm radii, a pocket for the emitter in the front face
    body = box_mm(-23.0, 23.0, -11.0, 11.0, -28.0, -3.0, bevel=2.6, seg=3, name="LZBody")
    W.cut(body, lathe_x([(19.6, 0.0), (19.6, 6.4), (24.0, 6.4), (24.0, 0.0)], 40, at=(0, 0, -12.5), name="Pocket"))
    # a shallow recess round the button and the wheel on the sides
    W.cut(body, box_mm(-13.0, -5.0, 10.2, 12.0, -21.0, -14.0, bevel=0.0, name="BtnPocket"))
    objs.append(fin(body, POLY, pi))
    ring = lathe_x([(19.8, 0.0), (19.8, 5.7), (22.4, 5.7), (22.4, 4.6), (21.2, 4.5), (21.2, 0.0)], 40, at=(0, 0, -12.5), fillet=0.15, fseg=1,
                   name="LZRing")
    objs.append(fin(ring, G.STEELB, pi))
    em = lathe_x([(20.0, 0.0), (20.0, 4.5), (21.5, 4.5), (21.5, 0.0)], 32, at=(0, 0, -12.5), name="LZEmit")
    objs.append(fin(em, RED, pi))
    # right side: the knurled windage wheel; left side: the rubber pressure button; rear: the battery cap; four screws
    objs.append(fin(axis_to_ny(knurled(4.8, 3.4, 20, 0.3, 0.45, name="LZWheel"), (-4.0, -10.4, -12.0)), STEELD, pi))
    objs.append(fin(box_mm(-12.0, -6.0, 10.2, 12.2, -20.0, -15.0, bevel=0.9, name="LZButton"), RUBBER, pi))
    cap = knurled(7.0, 2.6, 24, 0.3, 0.5, name="LZCap")
    geo.transform(cap, rot=(0, 0, 180))
    objs.append(fin(move(cap, -22.4, 0.0, -15.0), STEELD, pi))
    for sx, sz in ((-17.0, -8.0), (-17.0, -22.0), (15.0, -8.0), (15.0, -22.0)):
        objs.append(fin(screw_head_y(sx, sz, 11.0, r=1.6, h=0.9, sign=+1, seg=12, name="LZScrew"), STEELD, pi))
    # the NINE's dust cover tapers 1.9 deg (its underside climbs 0.033 mm per mm toward the muzzle) and the SHORTY's rail is
    # flat: the module is tilted 1 deg nose up and sits 0.38 mm low, so it crosses neither (0.03 mm off at one end, under 0.75
    # mm at the other on both rails)
    for o in objs:
        geo.transform(o, rot=(0, -1.0, 0))
        geo.transform(o, loc=(0, 0, -0.38 * MM))
    return objs, {"Beam": mm(23.5, 0, -12.5)}
