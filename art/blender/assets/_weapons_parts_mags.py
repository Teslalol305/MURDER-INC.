"""Round 4, lane 2: the parts kit, geometry III: the three extended magazines and their top rounds.

Frame: origin = the gun's MagHinge socket (the centre of the feed lips' top face for the rifle and SMG wells; the spec's point
for the NINE), the magazine hangs in -Z; the NINE's is modelled pre-canted about that origin (sockets carry no rotation).
Each builder returns (objects, top round object, sockets). Faces carry `mid` (G.MAGST steel body, G.MAGPOLY floor plate and
sleeve, G.GOLDM the NINE's pad, G.BRASSM / G.COPPERM the rounds, G.BORED the dark inside) and `part`."""
import math

import numpy as np

from mi import geo
from assets import weapons as W
from assets import _weapons_kit as K
from assets import _weapons_parts_geo as G
from assets._weapons_parts_geo import MM, fin, retag, mm, box_mm, prism_xy, move

BRASSM, COPPERM, BORED, MAGST, MAGPOLY, GOLDM = G.BRASSM, G.COPPERM, G.BORED, G.MAGST, G.MAGPOLY, G.GOLDM


def round_obj(length_mm, r_mm, rifle, name, pi, at_mm, seg=24):
    """A loaded round along +X from its base at `at_mm` (mm), brass case and copper bullet (W.cartridge), retagged."""
    rd = W.cartridge(length_mm * MM, r_mm * MM, name=name, rifle=rifle, seg=seg)
    mid = np.empty(len(rd.data.polygons), np.float32)
    rd.data.attributes["mid"].data.foreach_get("value", mid)
    out = np.where(np.rint(mid) == W.COPPER, COPPERM, BRASSM).astype(np.float32)
    rd.data.attributes["mid"].data.foreach_set("value", out)
    rd.data.attributes["part"].data.foreach_set("value", np.full(len(rd.data.polygons), float(pi), np.float32))
    geo.transform(rd, loc=mm(*at_mm))
    return rd


def stick_magazine(depth, width, height, rib_zs, rib_len, spine, pi=0, name="MG", corner=3.4, floor_over=1.0, floor_t=8.0,
                   tab=8.0, round_len=44.0, round_r=5.6, rifle=True, second_round=True, lips=0.78):
    """A straight stamped-steel stick magazine, `depth` (X) x `width` (Y) x `height` (Z) mm, lips top at z = 0: a hollow body
    with folded feed lips, stamped ribs across both side walls at the heights `rib_zs`, a vertical spine bead on the rear and
    a weld bead on the front wall, a black polymer floor plate with a drag tab on the front, the second round in the stack;
    the top round is returned separately. Returns (objects, top round)."""
    dx, hy = depth / 2.0, width / 2.0
    objs = []
    body_h = height - floor_t
    outer = prism_xy([(-dx, -hy), (dx, -hy), (dx, hy), (-dx, hy)], -body_h, 0.0, bevel=0.0, name=name + "Body", fillet=corner)
    # cavity: the inside, 0.9 mm walls, and the narrower feed opening through the top (the lips folded in)
    inner = prism_xy([(-dx + 0.9, -hy + 0.9), (dx - 0.9, -hy + 0.9), (dx - 0.9, hy - 0.9), (-dx + 0.9, hy - 0.9)], -body_h + 1.5,
                     -3.2, bevel=0.0, name=name + "Cav", fillet=max(corner - 0.9, 0.6))
    opening = prism_xy([(-dx + 3.2, -hy * lips), (dx - 3.2, -hy * lips), (dx - 3.2, hy * lips), (-dx + 3.2, hy * lips)], -4.0, 1.0,
                       bevel=0.0, name=name + "Open", fillet=1.6)
    W.cut(outer, inner)
    W.cut(outer, opening)
    W.round_edges(outer, 0.0003, 1, 50)
    fin(outer, MAGST, pi)
    retag(outer, BORED, lambda x, y, z: (np.abs(y) < (hy - 0.95) * MM) & (np.abs(x) < (dx - 0.95) * MM) & (z < -0.2 * MM) & (z > -(body_h - 1.2) * MM))
    objs.append(outer)
    # stamped ribs across both side walls: rib_len long, 4.8 mm tall, 0.9 mm proud, rounded
    for z in rib_zs:
        for sy in (1, -1):
            ya, yb = (hy - 0.15, hy + 0.9) if sy > 0 else (-hy - 0.9, -hy + 0.15)
            objs.append(fin(box_mm(-rib_len / 2, rib_len / 2, ya, yb, z - 2.4, z + 2.4, bevel=0.9, seg=2, name=name + "Rib"), MAGST, pi))
    # the spine bead on the rear wall and the weld bead on the front wall
    objs.append(fin(box_mm(-dx - 0.9, -dx + 0.15, -1.6, 1.6, -body_h + 3.0, -spine, bevel=0.4, name=name + "Spine"), MAGST, pi))
    objs.append(fin(box_mm(dx - 0.15, dx + 0.45, -1.3, 1.3, -body_h + 3.0, -spine, bevel=0.3, name=name + "Weld"), MAGST, pi))
    # floor plate: polymer, `floor_over` wider than the body all round, with the drag tab on the front
    fp_ = box_mm(-dx - floor_over, dx + floor_over, -hy - floor_over, hy + floor_over, -height, -body_h, bevel=1.6, seg=2, name=name + "Floor")
    tb = box_mm(dx + 0.5, dx + 0.5 + tab, -hy * 0.45, hy * 0.45, -height, -height + 5.0, bevel=1.1, seg=2, name=name + "Tab")
    W.cut(tb, G.lathe_z([(-4.0, 0.0), (-4.0, 2.3), (4.0, 2.3), (4.0, 0.0)], 14, at=(dx + 0.5 + tab * 0.62, 0.0, -height + 2.5), name="Hole"))
    objs.append(fin(fp_, MAGPOLY, pi))
    objs.append(fin(tb, MAGPOLY, pi))
    # the second round in the stack (right column, 9.5 mm below the top round) and the top round (left column)
    if second_round:
        objs.append(fin_round(round_obj(round_len, round_r, rifle, name + "Round2", pi, (-dx + 2.4, -hy * 0.30, -6.0 - 9.5)), pi))
    top = round_obj(round_len, round_r, rifle, name + "TopRound", pi, (-dx + 2.4, hy * 0.30, -6.0))
    return objs, top


def fin_round(rd, pi):
    return rd


def mag_ext_rifle(pi=0):
    """Extended rifle magazine for the two bullpup / marksman wells: 24 x 48 mm straight box, 235 mm tall (the 45-round
    look), four stamped ribs per side and a spine, feed lips, a black polymer floor plate with a drag tab. Same cross-section
    as the standard SHORTY and STRETCH magazines. Origin = MagHinge (the centre of the feed lips' top face)."""
    objs, top = stick_magazine(48.0, 24.0, 235.0, (-52.0, -98.0, -144.0, -190.0), 30.0, 10.0, pi, name="MR", round_len=44.0,
                               round_r=5.6, rifle=True)
    return objs, top, {}


def mag_ext_smg(pi=0):
    """Extended stick magazine for the RATTLER: 30 x 42 mm, 242 mm from the lips (the 50-round look), grey stamped steel with
    two ribs per side and a spine like the standard stick, a black floor plate with a drag tab. Origin = MagHinge."""
    objs, top = stick_magazine(42.0, 30.0, 242.0, (-98.0, -170.0), 26.0, 10.0, pi, name="MS", corner=3.0, round_len=29.0, round_r=4.9,
                               rifle=False, floor_t=8.0, tab=7.0)
    return objs, top, {}


# ------------------------------------------------------------------------------------------------- NINE (canted)
def mag_ext_pistol(pi=0):
    """Extended pistol magazine for the NINE: the standard magazine's body (19.5 x 34 mm, raked along the grip axis (0.250, 0,
    0.968), three witness holes per side, feed lips, the stack) lengthened by 48 mm, a black polymer sleeve over its last 48
    mm and the NINE's polished gold base pad (43 x 26 x 7 mm) carried down with it (in place X -0.0255..0.030, floor Z -0.181).
    Built in gun space like the standard magazine and moved so that the MagHinge socket (0.0177, 0, -0.0359) is the origin."""
    from assets import _weapons_nine as N9
    A, F = N9.A, N9.F
    b = N9.mag_base()
    top_t = (-0.037 - b[2]) / A[2]
    Wm, D = 0.00975, 0.017
    extra = 0.048
    sec = geo.fillet([(-D, -Wm), (D - 0.004, -Wm), (D, -Wm + 0.004), (D, Wm - 0.004), (D - 0.004, Wm), (-D, Wm)], 0.0018, 3, closed=True)
    inner = [(u * (D - 0.0007) / D, v * (Wm - 0.0007) / Wm) for u, v in sec]
    ring = lambda t, s: [tuple(b + A * t + F * u + np.array([0, 1.0, 0]) * v) for u, v in s]

    def ring_flat(zt, s):
        out = []
        for u, v in s:
            c = b + F * u + np.array([0, 1.0, 0]) * v
            out.append(tuple(c + A * ((zt - c[2]) / A[2])))
        return out
    z_bot = N9.BUTT_Z - 0.0030 - extra * A[2]                  # the body's flat bottom, 48 mm lower along the axis
    objs = []
    body = K_loft([ring_flat(z_bot, sec), ring(top_t - 0.004, sec)], cap0=True, cap1=False, name="MPBody")
    inn = K_loft([ring(top_t - 0.004 - 0.030, inner), ring(top_t - 0.004, inner)], cap0=True, cap1=False, name="MPIn")
    bm = geo.bm_of(inn)
    for fc in bm.faces:
        fc.normal_flip()
    geo.bm_to(inn, bm)
    holes = []
    for t in (0.030, 0.048, 0.066):
        c = b + A * t + F * (-0.008)
        holes.append(W.lathe([(-0.02, 0.0), (-0.02, 0.0015), (0.02, 0.0015), (0.02, 0.0)], 24, axis="Y", at=tuple(c)))
    W.cut(body, *holes)
    W.round_edges(body, 0.0003, 2, 50)
    objs.append(fin(body, MAGST, pi))
    objs.append(fin(inn, BORED, pi))
    o, i = ring(top_t - 0.004, sec), ring(top_t - 0.004, inner)
    m = len(o)
    rim = geo.from_arrays("MPRim", np.concatenate([o, i]), [(j, (j + 1) % m, m + (j + 1) % m, m + j) for j in range(m)], smooth=None)
    objs.append(fin(W.fix_normals(rim), MAGST, pi))
    for s in (1, -1):
        prof = [(s * Wm, 0.0), (s * Wm, 0.0020), (s * (Wm - 0.0012), 0.0034), (s * (Wm - 0.0036), 0.0040), (s * (Wm - 0.0044), 0.0034),
                (s * (Wm - 0.0007), 0.0012), (s * (Wm - 0.0007), 0.0)]
        if s < 0:
            prof = prof[::-1]
        secs = []
        for u in np.linspace(-D + 0.001, D * 0.25, 7):
            c = b + A * (top_t - 0.004) + F * u
            secs.append([tuple(c + np.array([0, y, 0]) + A * h) for y, h in prof])
        objs.append(fin(K_loft(secs, name="MPLip"), MAGST, pi))
    for k in range(1, 10):
        t = top_t - 0.004 - 0.0062 * k
        c = b + A * t + F * (-D + 0.002)
        rd = W.cartridge(0.030, 0.0047, name="Stack", rifle=False, seg=16)
        geo.transform(rd, loc=(c[0], (0.0035 if k % 2 else -0.0035), c[2]))
        retag_round(rd, pi)
        objs.append(rd)
    # the polymer sleeve: 0.6 mm proud over the last 48 mm of the body, closed at the bottom by the pad
    sl_sec = geo.fillet([(u * (D + 0.0006) / D, v * (Wm + 0.0006) / Wm) for u, v in sec], 0.0016, 2, closed=True)
    sleeve = K_loft([ring_flat(z_bot, sl_sec), ring_flat(N9.BUTT_Z - 0.0030 + 0.0, sl_sec)], cap0=True, cap1=True, name="MPSleeve")
    W.round_edges(sleeve, 0.0003, 1, 50)
    objs.append(fin(sleeve, MAGPOLY, pi))
    pad = N9.build_pad()
    geo.transform(pad, loc=tuple(-extra * A))
    objs.append(fin(pad, GOLDM, pi))
    ctop = b + A * top_t
    top = W.cartridge(0.030, 0.0048, name="MPTopRound", rifle=False, seg=24)
    geo.transform(top, loc=(ctop[0] - 0.0175, 0.0, -0.0335))
    retag_round(top, pi)
    # everything into the socket's frame: the origin is MagHinge (0.0177, 0, -0.0359)
    off = np.array([-0.0177, 0.0, 0.0359])
    for ob in objs + [top]:
        geo.transform(ob, loc=tuple(off))
    return objs, top, {}


def K_loft(sections, closed=True, cap0=True, cap1=True, name="Loft"):
    return W.loft(sections, closed=closed, cap0=cap0, cap1=cap1, name=name)


def retag_round(rd, pi):
    mid = np.empty(len(rd.data.polygons), np.float32)
    rd.data.attributes["mid"].data.foreach_get("value", mid)
    rd.data.attributes["mid"].data.foreach_set("value", np.where(np.rint(mid) == W.COPPER, COPPERM, BRASSM).astype(np.float32))
    rd.data.attributes["part"].data.foreach_set("value", np.full(len(rd.data.polygons), float(pi), np.float32))
    return rd
