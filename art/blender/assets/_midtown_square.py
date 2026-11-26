"""Midtown kit, part 4: the square (midtown.md 2.2, 2.3, 9.1, 11.2, 12.4, 14.2): the Stand and the Booth as the level
data has them, the plaza's planters, kiosks, food carts, cafe furniture, light poles, barriers, the generator, road
cases, cable ramps and the cable drum.

The Stand follows tools/levels/data/level_midtown.json, not the first drawing: tiers 1 to 5 are two wings (x 10..13 and
19..22) round a front court at plaza level (x 13..19), tiers 6 to 8 run the full 12 m over the Booth, and the Booth's front
wall carries the 1.0 m shoot-through slot (sill 1.0, head 2.0) looking into the court. Every tier is 1.5 m deep and 0.40
higher than the last (tops 0.55 to 3.35 over the plaza), slabs 0.30 thick. The guard on the top tier is a dark scrim on a
truss (the data's playerOnly box, 2.2 to 6.35).

Surfaces: the catalogued scans and the sets already baked (no new tiling set: TS_Granite_Pavers became a tint of the
aggregate concrete scan). Emissive: the amber riser glass (40 nits), the light poles' LED heads, the kiosks' and carts'
lightbox faces (200 nits, Sign_MT_Atlas1), the booth monitors (small, M_MI_Screen on a slide), rack indicators; none is a
large screen, none is translucent.

Pivots. Props: centre of the footprint on the ground (z = 0 is the plaza top, 0.15 in the level, or the roadway at 0),
front (the side people use) toward -Y, which is web +z (south) at rotation 0. Stand pieces: see each docstring. Members
near the path are 6 cm across or more (chair legs and backs are short parts, under 0.6 m: the thin rule's length floor).
The art has no collision: the level data decides.
"""
import math

import numpy as np

from assets import _midtown_roof as R
from assets.facade import B, bx, rod, sheet
from mi import geo, steel

X, Y, Z = np.eye(3)
T_TIER, D_TIER, RISE = 0.30, 1.5, 0.40


def materials(ctx, M):
    S, F = R.S, R.F
    M["granite"] = S(ctx, "TS_Concrete_ScanAggregate", "MI_Stone_Granite", tint=(0.60, 0.58, 0.58), alpha="splash",
                     dirt_color=R.SOOT, macro=0.10,
                     note="the plaza's granite planters: the exposed-aggregate scan, cooled grey (the design's TS_Granite_Pavers as a "
                          "tint: no new set)")
    M["soil"] = S(ctx, "TS_Ground_ScanSoil", alpha="splash", macro=0.1)
    M["hedge"] = S(ctx, "TS_Leaf_Privet", "MI_Leaf_PrivetClipped", tint=(0.55, 0.62, 0.50),
                   note="clipped box hedge in the granite planters: the privet leaf set on a closed lumpy mesh, opaque (no masked "
                        "foliage), darkened for the night square")
    M["stainless"] = S(ctx, "TS_Steel_Stainless", dirt_color=R.SOOT)
    M["plasticBlack"] = S(ctx, "TS_Plastic_Black", dirt_color=R.SOOT)
    M["orange"] = S(ctx, "TS_Plastic_Orange", dirt_color=R.SOOT)
    M["white"] = S(ctx, "TS_Plastic_White", dirt_color=R.SOOT)
    M["yellow"] = S(ctx, "TS_Steel_ScanPaintYellow", alpha="splash", dirt_color=R.SOOT)
    clean = "TS_Steel_PaintWhiteClean"
    M["standGrey"] = S(ctx, clean, "MI_Steel_PaintStand", tint=(0.40, 0.42, 0.45), dirt_color=R.SOOT,
                       note="THE STAND's grey steel, new for the premiere (an invented viewing stand, no real copy): the clean "
                            "white paint set tinted, no rust")
    M["standBlack"] = S(ctx, clean, "MI_Steel_PaintStandBlack", tint=(0.045, 0.045, 0.05), dirt_color=R.SOOT,
                        note="the Stand's and the crew gear's black steel: the clean paint set tinted")
    M["kiosk"] = S(ctx, clean, "MI_Steel_PaintKiosk", tint=(0.06, 0.12, 0.22), dirt_color=R.SOOT,
                   note="the souvenir kiosks' navy enamel")
    M["genWhite"] = S(ctx, clean, "MI_Steel_PaintGenerator", tint=(0.78, 0.77, 0.72), dirt_color=R.SOOT,
                      note="the hired generator's off-white enclosure")
    M["scrim"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_Scrim", tint=(0.07, 0.07, 0.08), alpha="splash", dirt_color=R.SOOT,
                   note="the dark scrim on the top tier's guard truss: opaque woven, no alpha")
    M["umbrella"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_UmbrellaNavy", tint=(0.12, 0.20, 0.36), alpha="splash",
                      dirt_color=R.SOOT, note="food cart umbrellas: navy canvas (no red field near the Goons)")
    M["shutter"] = S(ctx, "TS_Shutter_ScanGrey", alpha="splash", dirt_color=R.SOOT)
    M["drum"] = S(ctx, "TS_Wood_ScanPlankDark", "MI_Wood_CableDrum", tint=(0.85, 0.75, 0.62), alpha="splash", dirt_color=R.SOOT)
    M["riser"] = F("MI_Stand_RiserGlass", (0.30, 0.16, 0.05), 0.12, emit=(1.0, 0.48, 0.12), strength=0.0,
                   note="THE STAND's amber riser glass, opaque, lit from inside: emissive 40 nits at night (midtown.md 2.3, 11.2: "
                        "about 26 m2 of risers in all; not a screen)")
    M["warm"] = F("MI_Lamp_KioskInterior", (0.55, 0.50, 0.42), 0.5, emit=(1.0, 0.80, 0.55), strength=0.0,
                  note="the kiosks' and carts' interior strip lights: emissive 120 nits at night, small")
    M["indicator"] = F("MI_Lamp_Indicator", (0.04, 0.10, 0.06), 0.3, emit=(0.35, 1.0, 0.55), strength=0.0,
                       note="rack and console indicator dots: emissive 60 nits, a few cm each")
    return M


# ================================================================================================= helpers

def quad(b, o, u, v, w, h, slot):
    """One flat face (two triangles) at o spanned by u * w and v * h, looking along u x v. Returns its frame."""
    o, u, v = (np.asarray(a, float) for a in (o, u, v))
    b._add(np.array([o, o + u * w, o + u * w + v * h, o + v * h]), [0, 1, 2, 3], [4], slot, kind=b.OTHER, uv_off=(0.0, 0.0))
    return (tuple(o), u, v, (w, h))


def fix_faces(ob, slot_name, frames):
    """0..1 UVs on every face of a slot from the frame whose rectangle holds the face's centre (several faces of one slot,
    each with its own frame). frames: [(origin, u, v, (w, h))]."""
    me = ob.data
    idx = [i for i, m in enumerate(me.materials) if m and m.name == slot_name]
    if not idx:
        return 0
    uvl = me.uv_layers[0].data
    co = np.array([v.co for v in me.vertices])
    n = 0
    for poly in me.polygons:
        if poly.material_index not in idx:
            continue
        c = np.array(poly.center)
        best = None
        for (o, ua, va, (w, h)) in frames:
            o, ua, va = (np.asarray(a, float) for a in (o, ua, va))
            p = c - o
            nrm = np.cross(ua, va)
            s, t, d = float(np.dot(p, ua)) / w, float(np.dot(p, va)) / h, abs(float(np.dot(p, nrm)))
            if -0.01 <= s <= 1.01 and -0.01 <= t <= 1.01 and d < 0.02 and float(np.dot(np.array(poly.normal), nrm)) > 0.5:
                best = (o, ua, va, w, h)
                break
        if best is None:
            continue
        o, ua, va, w, h = best
        for li in poly.loop_indices:
            p = co[me.loops[li].vertex_index] - o
            uvl[li].uv = (float(np.dot(p, ua) / w), float(np.dot(p, va) / h))
        n += 1
    return n


def done(ctx, b, name, M, faces=None, screens=None, labels=None, **asset):
    """roof.done plus per-face frames for the printed faces (M_Sign_MT_Face) and the monitor screens (M_MI_Screen).
    labels: roof.label() results (one face each)."""
    ob = R.done(ctx, b, name, M, faces=labels, **asset)
    if faces:
        fix_faces(ob, "M_Sign_MT_Face", faces)
    if screens:
        fix_faces(ob, "M_MI_Screen", screens)
    return ob


def tube(b, p0, p1, slot, r=0.03, n=10):
    return R.tube(b, p0, p1, slot, r, n)


def short_rod(b, p0, p1, r, slot, n=8):
    """A rod thinner than the 6 cm floor, allowed only for parts under 0.6 m long (chair legs and backs)."""
    assert np.linalg.norm(np.asarray(p1, float) - np.asarray(p0, float)) < 0.6
    return rod(b, p0, p1, r, slot, n=n)


def lump(b, size, centre, slot, bevel=0.08, edge=0.16, amount=0.035, seed=0):
    """A closed lumpy block (clipped hedge): a bevelled box, densified and displaced along its normals."""
    ob = geo.box(size, bevel=bevel, segments=2)
    geo.densify(ob, max_edge=edge, passes=4)
    geo.displace(ob, amount=amount, scale=5.0, seed=seed)
    geo.displace(ob, amount=amount * 0.4, scale=15.0, seed=seed + 7)
    geo.transform(ob, loc=centre)
    return b.absorb(ob, slot)


def wheel(b, c, r, w, axis=Y, slot="rubber", hub="galv"):
    c, axis = np.asarray(c, float), np.asarray(axis, float)
    rod(b, c - axis * w / 2, c + axis * w / 2, r, slot, n=18)
    rod(b, c - axis * (w / 2 + 0.01), c + axis * (w / 2 + 0.01), r * 0.55, hub, n=12)


# ================================================================================================= THE STAND and THE BOOTH

def m_tier(ctx, M, W):
    """One tier of THE STAND, W wide (12 m for tiers 6 to 8 over the Booth, 3 m for each wing's tiers 1 to 5), 1.5 deep:
    checker-plate tread on a steel deck, nosing with an amber strip, and the riser glass below the nosing (0.40 high, lit
    from inside, a steel light box behind it). The 12 m tier has its deck beams and soffit inside the 0.30 slab (the Booth's
    ceiling) and end plates. Pivot: centre of the tread top; the front (the riser) toward -Y."""
    b = B(601 + int(W), step=0.75)
    x0, x1, y0, y1 = -W / 2, W / 2, -D_TIER / 2, D_TIER / 2
    bx(b, (x0, y0 + 0.02, -0.012), (x1, y1, 0.0), "plate", axis="x")                              # checker tread
    bx(b, (x0, y0 + 0.02, -0.06), (x1, y1, -0.012), "standGrey", axis="x")                         # deck
    bx(b, (x0, y0 - 0.04, -0.06), (x1, y0 + 0.04, 0.004), "galv", ch=0.004, pin=False, axis="x")   # nosing
    bx(b, (x0, y0 - 0.046, -0.059), (x1, y0 - 0.040, 0.001), "riser", pin=False, axis="x")        # amber nosing strip (6 cm)
    bx(b, (x0, y0 - 0.01, -RISE), (x1, y0 + 0.01, -0.06), "riser", pin=False, axis="x")          # riser glass
    bx(b, (x0, y0 + 0.01, -RISE), (x1, y0 + 0.04, -0.06), "standGrey", pin=False, axis="x")      # its light box
    nm = max(2, int(round(W / 1.5)))
    for xx in np.linspace(x0, x1, nm + 1):                                                       # riser mullions
        xa, xb_ = max(x0, xx - 0.04), min(x1, xx + 0.04)
        bx(b, (xa, y0 - 0.025, -RISE), (xb_, y0 + 0.015, -0.06), "standGrey", ch=0.003, pin=False, axis="z")
    if W > 4:
        bx(b, (x0, y1 - 0.02, -T_TIER), (x1, y1, -0.06), "standGrey", pin=False, axis="x")           # back fascia
        bx(b, (x0, y0 + 0.04, -T_TIER), (x1, y0 + 0.06, -0.06), "standGrey", pin=False, axis="x")  # front fascia (behind the glass)
        bx(b, (x0, y0 + 0.06, -0.075), (x1, y1 - 0.02, -0.06), "standGrey", pin=False, axis="x")   # soffit plate
        for yy in (-0.35, 0.35):                                                                 # deck beams in the slab
            b.prism(steel.ibeam(0.22, 0.12, 0.010, 0.007), (x0 + 0.01, yy, -T_TIER), Y, Z, (W - 0.02, 0, 0), "standBlack", pstep=9.0)
        for xx in np.arange(x0 + 1.0, x1 - 0.5, 2.0):                                            # cross ribs
            bx(b, (xx - 0.04, y0 + 0.06, -0.20), (xx + 0.04, y1 - 0.02, -0.075), "standBlack", pin=False, axis="y")
        for s in (-1, 1):                                                                        # end plates
            xe = x0 if s < 0 else x1
            bx(b, (xe - 0.012 * (s < 0), y0 - 0.04, -T_TIER), (xe + 0.012 * (s > 0), y1, 0.004), "standGrey", ch=0.003, pin=False, axis="y")
            b.rivets([(xe + s * 0.012, yy, -0.15) for yy in np.linspace(y0 + 0.2, y1 - 0.2, 4)], s * X, "standGrey", leak=0.0)
    name = "SM_Sq_Stand_Tier_%dm" % int(W)
    return done(ctx, b, name, M, ground=False, expect_size=(W, None, None),
                notes=("THE STAND tier, %d m wide x 1.5 deep: checker tread, galvanised nosing with an amber strip, amber riser glass "
                       "0.40 high (MI_Stand_RiserGlass, emissive 40 nits, opaque) in a steel light box%s. Pivot: centre of the tread "
                       "top, the riser toward -Y. Placed on the level's stand colliders: %s.")
                % (W, ", deck beams and soffit inside the 0.30 slab (the Booth's ceiling), end plates" if W > 4 else "",
                   "tiers 6 to 8 at x 16" if W > 4 else "tiers 1 to 5 of both wings (x 11.5 and 20.5)"))


def m_wingside(ctx, M):
    """The stepped side cladding of one wing of tiers 1 to 5: a steel panel 4 cm thick, clad on both faces (so one mesh
    serves the outer and the inner face of both wings), its top stepping 0.40 every 1.5 m, cover strips at each step, a
    galvanised cap and a kick plate. Pivot: the south (front) end on the ground in the panel's mid-plane; it runs toward +Y
    (north) for 7.5 m, steps rising."""
    b = B(611, step=0.75)
    t = 0.02
    for k in range(1, 6):
        ya, yb, zt = D_TIER * (k - 1), D_TIER * k, RISE * k
        bx(b, (-t, ya, 0.0), (t, yb, zt - 0.03), "standGrey", axis="y")
        bx(b, (-t - 0.02, ya, zt - 0.03), (t + 0.02, yb + (0.02 if k < 5 else 0.0), zt), "galv", ch=0.003, pin=False, axis="y")
        for s in (-1, 1):
            bx(b, (s * t, yb - 0.04, 0.0), (s * (t + 0.015), yb + 0.04, zt), "standBlack", pin=False, axis="z")
    for s in (-1, 1):
        bx(b, (s * t, 0.0, 0.0), (s * (t + 0.006), 7.5, 0.18), "galv", pin=False, axis="y")
        bx(b, (s * t, 0.0, 0.0), (s * (t + 0.015), 0.06, RISE - 0.03), "standBlack", pin=False, axis="z")
    return done(ctx, b, "SM_Sq_Stand_WingSide", M, ground=True, expect_size=(None, 7.5, 2.0),
                notes="Side cladding of a wing of THE STAND (tiers 1 to 5): 4 cm steel panel clad on both faces, top stepping 0.40 "
                      "every 1.5 m (2.0 at the back), cover strips, cap, kick plate. Pivot: south end on the ground, mid-plane; runs +Y "
                      "(north). Four placements: x 10, 13, 19, 22 (the wings' outer and court faces).")


def m_booth_side(ctx, M):
    """A side wall of THE BOOTH (the data's booth.wall.west / .east): 0.60 thick, 4.5 m from the front (y 0, web z -29.5)
    to the back (y 4.5), its top under the tier soffits (2.10, 2.50, 2.90 over the plaza), and the 2.0 m Goon door (y 1.5
    to 3.5, 2.0 high) with a steel frame on both faces. Symmetric about its mid-plane: one mesh for both sides. Pivot: front
    end, mid-plane, on the ground; runs +Y."""
    b = B(621, step=0.6)
    w = 0.30
    tops = [(0.0, 1.5, 2.10), (1.5, 3.0, 2.50), (3.0, 4.5, 2.90)]
    door = (1.5, 3.5, 2.0)
    for ya, yb, zt in tops:
        segs = [(ya, yb)]
        if yb > door[0] and ya < door[1]:
            segs = [(ya, max(ya, door[0])), (min(yb, door[1]), yb)]
            bx(b, (-w, max(ya, door[0]), door[2]), (w, min(yb, door[1]), zt), "standGrey", axis="y")          # lintel part
        for a_, c_ in segs:
            if c_ - a_ > 1e-3:
                bx(b, (-w, a_, 0.0), (w, c_, zt), "standGrey", axis="y")
    for s in (-1, 1):                                                                               # panel seams and frame
        for yy in (0.75, 3.95):
            bx(b, (s * w, yy - 0.03, 0.0), (s * (w + 0.008), yy + 0.03, 2.05), "standBlack", pin=False, axis="z")
        for yy in (door[0], door[1]):
            bx(b, (s * w, yy - 0.04, 0.0), (s * (w + 0.02), yy + 0.04, door[2] + 0.08), "standBlack", ch=0.004, pin=False, axis="z")
        bx(b, (s * w, door[0] - 0.04, door[2]), (s * (w + 0.02), door[1] + 0.04, door[2] + 0.08), "standBlack", ch=0.004, pin=False, axis="y")
        bx(b, (s * w, 0.0, 0.0), (s * (w + 0.006), door[0], 0.15), "galv", pin=False, axis="y")
        bx(b, (s * w, door[1], 0.0), (s * (w + 0.006), 4.5, 0.15), "galv", pin=False, axis="y")
    bx(b, (-w, door[0], -0.005), (w, door[1], 0.012), "plate", pin=False, axis="y")                 # threshold plate
    faces = []
    for s in (-1, 1):                                                                               # a label over the door, both faces
        o = np.array((s * (w + 0.010), 2.5 - s * 0.20, door[2] + 0.12))
        u = s * Y
        b.prism(steel.rect(0.40, 0.28), o - s * X * 0.008, u, Z, s * X * 0.008, "standGrey", pstep=9.0)
        faces.append(quad(b, o + s * X * 0.001, u, Z, 0.40, 0.28, "signFace"))
    return done(ctx, b, "SM_Sq_Booth_WallSide", M, ground=True, faces=faces, expect_size=(None, 4.5, 2.9),
                notes="A side wall of THE BOOTH, 0.60 thick, 4.5 long, top under the tier soffits (2.10, 2.50, 2.90 over the plaza), "
                      "the 2.0 m Goon door (y 1.5 to 3.5, 2.0 high, midtown.md 2.3 and 9.1) framed on both faces, a label "
                      "(Label_CrewOnly) over it on both faces. Symmetric: the same mesh at x 10.3 and 21.7. Pivot: front end, mid-plane, "
                      "ground; runs +Y (north).")


def m_booth_front(ctx, M):
    """THE BOOTH's front wall (x 10.6..21.4, 0.30 thick, its outer face toward the front court, -Y): solid ends to 2.10
    over the plaza, and between them the broken window: a sill to 0.85, a head from 1.85, a steel frame round the 6 m x
    1.0 m opening and a few glass shards left at its corners (the shoot-through slot: nothing in the opening).
    Pivot: centre of the wall on the ground."""
    b = B(631, step=0.6)
    W, t, H = 10.8, 0.15, 2.10
    s0, s1, z0, z1 = -3.0, 3.0, 0.85, 1.85
    for xa, xb_ in ((-W / 2, s0), (s1, W / 2)):
        bx(b, (xa, -t, 0.0), (xb_, t, H), "standGrey", axis="x")
    bx(b, (s0, -t, 0.0), (s1, t, z0), "standGrey", axis="x")
    bx(b, (s0, -t, z1), (s1, t, H), "standGrey", axis="x")
    bx(b, (s0 - 0.04, -t - 0.05, z0 - 0.04), (s1 + 0.04, t + 0.02, z0), "galv", ch=0.004, pin=False, axis="x")       # sill cap
    for (xa, xb_, za, zb) in ((s0, s1, z0, z0 + 0.06), (s0, s1, z1 - 0.06, z1), (s0, s0 + 0.06, z0, z1), (s1 - 0.06, s1, z0, z1)):
        bx(b, (xa, -0.05, za), (xb_, 0.05, zb), "standBlack", ch=0.004, pin=False)                       # the window frame
    rng = ctx.rng("booth-shards")
    for (cx, cz, sx, sz) in ((s0 + 0.06, z0 + 0.06, 1, 1), (s1 - 0.06, z0 + 0.06, -1, 1), (s0 + 0.06, z1 - 0.06, 1, -1),
                             (s1 - 0.06, z1 - 0.06, -1, -1), (0.4, z1 - 0.06, -1, -1), (-1.6, z0 + 0.06, 1, 1)):
        a, c = rng.uniform(0.10, 0.26), rng.uniform(0.08, 0.20)
        pts = [(cx, cz), (cx + sx * a, cz), (cx + sx * a * 0.35, cz + sz * c * 0.5), (cx, cz + sz * c)]
        if sx * sz < 0:
            pts = pts[::-1]
        b.poly_plate([(p[0], 0.004, p[1]) for p in pts], 0.008, "glass", kind=b.OTHER)
    for s in (-1, 1):                                                                                 # panel seams on the ends
        for xx in (s * 4.2,):
            bx(b, (xx - 0.03, -t - 0.008, 0.0), (xx + 0.03, -t, H), "standBlack", pin=False, axis="z")
    bx(b, (-W / 2, -t - 0.006, 0.0), (W / 2, -t, 0.15), "galv", pin=False, axis="x")                 # kick plate (outside)
    return done(ctx, b, "SM_Sq_Booth_FrontWall", M, ground=True, expect_size=(W, None, H),
                notes="THE BOOTH's front wall, 10.8 x 0.30 x 2.10: solid ends, sill to 0.85 and head from 1.85 over the plaza (the "
                      "level's 1.0 and 2.0), the 6 x 1.0 m broken window framed in steel with glass shards only at its corners (the "
                      "shoot-through slot: a playerOnly box in the data, nothing in the opening). Pivot: centre, ground; the court "
                      "side toward -Y.")


def m_stand_back(ctx, M):
    """The back of THE STAND: the Booth's back wall (12 x 0.30, to 3.20 over the plaza) and the top tier's guard (the data's
    playerOnly box to 6.35): a dark scrim from the top tier to 6.20 on a box-section truss, returning 1.8 m down both sides
    of tier 8. Pivot: the inner face of the back wall at its centre, on the ground; the wall runs along X, the Stand lies
    toward -Y (south)."""
    b = B(641, step=0.75)
    W = 12.0
    zt8 = 3.20                                                                                     # tier 8 top over the plaza
    bx(b, (-W / 2, 0.0, 0.0), (W / 2, 0.30, zt8), "standGrey", axis="x")
    for xx in np.arange(-W / 2 + 1.5, W / 2 - 0.1, 1.5):                                          # seams, outside
        bx(b, (xx - 0.03, 0.30, 0.0), (xx + 0.03, 0.308, zt8), "standBlack", pin=False, axis="z")
    for xx in np.arange(-W / 2, W / 2 + 0.01, 2.0):                                               # truss posts behind the wall
        xc = float(np.clip(xx, -W / 2 + 0.05, W / 2 - 0.05))
        bx(b, (xc - 0.05, 0.30, 0.0), (xc + 0.05, 0.40, 6.30), "standBlack", ch=0.005, pin=False, axis="z")
    for zz in (zt8 + 0.05, 4.7, 6.20):                                                            # girts
        bx(b, (-W / 2 - 0.05, 0.40, zz - 0.05), (W / 2 + 0.05, 0.48, zz + 0.05), "standBlack", ch=0.005, pin=False, axis="x")
    F = np.array([[(-W / 2 - 0.05 + (W + 0.1) * i / 8, 0.32, zt8 + (6.20 - zt8) * j / 3) for i in range(9)] for j in range(4)])
    sheet(b, F, 0.006, "scrim")
    for s in (-1, 1):                                                                              # returns down tier 8's sides
        xs = s * (W / 2 + 0.05)
        Fr = np.array([[(xs, 0.30 - 1.8 * i / 3, (zt8 - 0.0) + (6.20 - zt8) * j / 3) for i in range(4)] for j in range(4)])
        if s > 0:
            Fr = Fr[:, ::-1]
        sheet(b, Fr, 0.006, "scrim")
        for yy in (0.30, -0.6, -1.5):
            bx(b, (xs - 0.05, yy - 0.05, zt8 - 0.10), (xs + 0.05, yy + 0.05, 6.30), "standBlack", ch=0.005, pin=False, axis="z")
        for zz in (zt8 + 0.05, 4.7, 6.20):
            bx(b, (xs - 0.04, -1.55, zz - 0.04), (xs + 0.04, 0.30, zz + 0.04), "standBlack", ch=0.004, pin=False, axis="y")
        R.rail_run(b, np.array((xs - s * 0.10, -1.45, zt8)), np.array((xs - s * 0.10, 0.20, zt8)), "galv", h=1.10, post=0.85, toe=False)
    return done(ctx, b, "SM_Sq_Stand_Back", M, ground=True, expect_size=(None, None, None),
                notes="Back of THE STAND: the Booth's back wall (12 x 0.30 to 3.20 over the plaza) and the top tier's guard, a dark "
                      "opaque scrim (MI_Fabric_Scrim) to 6.20 on a box-section truss with girts, returning 1.8 m along tier 8's sides "
                      "with a hand rail (the data's playerOnly guard boxes). Pivot: inner face of the back wall at its centre, ground.")


def m_booth_desk(ctx, M):
    """The broadcast desk (3.2 x 0.6 x 0.8): a steel desk, a sloped console with faders, knobs and indicator dots, a cable
    tray. Its operator side toward -Y (the slot); its back against the Booth's back wall. Pivot: centre, ground."""
    b = B(651, step=0.6)
    L, W, H = 3.2, 0.6, 0.80
    bx(b, (-L / 2, -W / 2, 0.74), (L / 2, W / 2, 0.78), "plasticBlack", ch=0.006, axis="x")       # top
    for s in (-1, 1):
        bx(b, (s * L / 2 - (0.05 if s > 0 else 0.0), -W / 2 + 0.03, 0.0), (s * L / 2 + (0.05 if s < 0 else 0.0), W / 2, 0.74),
           "standGrey", ch=0.004, pin=False, axis="z")
    bx(b, (-L / 2 + 0.05, W / 2 - 0.04, 0.10), (L / 2 - 0.05, W / 2, 0.74), "standGrey", pin=False, axis="x")   # modesty panel
    bx(b, (-L / 2 + 0.05, -W / 2 + 0.05, 0.62), (L / 2 - 0.05, W / 2 - 0.05, 0.74), "standGrey", pin=False, axis="x")   # drawers
    rows = [((-1.20, -0.24, 0.78), (0.30, -0.24, 0.78)), ((-1.20, 0.14, 0.92), (0.30, 0.14, 0.92))]
    b.plate_rows(rows, 0.05, "grille")
    for i in range(10):                                                                            # fader caps
        xx = -1.12 + i * 0.14
        bx(b, (xx - 0.02, -0.19, 0.80), (xx + 0.02, -0.15, 0.825), "galv", pin=False)
        bx(b, (xx - 0.012, 0.02, 0.86), (xx + 0.012, 0.045, 0.885), "indicator" if i % 3 == 0 else "galv", pin=False)
    bx(b, (0.55, -0.22, 0.78), (1.05, -0.05, 0.80), "plasticBlack", ch=0.003, pin=False)
    bx(b, (1.15, -0.20, 0.78), (1.40, 0.00, 0.787), "white", pin=False)
    bx(b, (-L / 2 + 0.1, W / 2 - 0.10, 0.20), (L / 2 - 0.1, W / 2 - 0.04, 0.26), "galv", pin=False, axis="x")   # cable tray
    return done(ctx, b, "SM_Sq_Booth_Desk", M, ground=True, cover_height=0.8, expect_size=(None, None, None),
                notes="THE BOOTH's broadcast desk 3.2 x 0.6 x 0.8 (the data's booth_desk): steel frame, black top, sloped console "
                      "with faders and indicator dots (MI_Lamp_Indicator), keyboard, cable tray. Pivot: centre, ground; the operator "
                      "side -Y. Three SM_Sq_Booth_Monitor stand on it.")


def m_booth_rack(ctx, M):
    """Two equipment racks side by side (1.4 x 0.8 x 1.75): frames, vented doors open, rack units with handles, indicator
    dots, cable looms out of the top. Front toward -Y. Pivot: centre, ground."""
    b = B(661, step=0.6)
    for cx in (-0.35, 0.35):
        bx(b, (cx - 0.34, -0.40, 0.0), (cx + 0.34, 0.40, 0.08), "standBlack", pin=False, axis="x")         # plinth
        bx(b, (cx - 0.34, -0.40, 1.68), (cx + 0.34, 0.40, 1.75), "standBlack", pin=False, axis="x")
        for sx in (-1, 1):
            bx(b, (cx + sx * 0.34 - (0.06 if sx > 0 else 0.0), -0.40, 0.08), (cx + sx * 0.34 + (0.06 if sx < 0 else 0.0), 0.40, 1.68),
               "standBlack", pin=False, axis="z")
        bx(b, (cx - 0.28, 0.36, 0.08), (cx + 0.28, 0.40, 1.68), "grille", pin=False, axis="z")
        z = 0.12
        rng = ctx.rng("rack", cx)
        while z < 1.6:
            h = float(rng.choice([0.044, 0.089, 0.133]))
            bx(b, (cx - 0.27, -0.36, z), (cx + 0.27, 0.30, z + h - 0.004), "plasticBlack" if rng.random() < 0.6 else "standGrey", ch=0.002,
               pin=False, axis="x")
            bx(b, (cx - 0.25, -0.375, z + h * 0.3), (cx - 0.21, -0.36, z + h * 0.7), "indicator", pin=False)
            z += h
    for cx in (-0.35, 0.35):                                                                         # looms out of the top
        rod(b, (cx + 0.15, 0.25, 1.75), (cx + 0.15, 0.25, 1.85), 0.035, "rubber", n=8)
    return done(ctx, b, "SM_Sq_Booth_Rack", M, ground=True, cover_height=1.75, expect_size=(None, None, None),
                notes="Two 19-inch equipment racks 1.4 x 0.8 x 1.75 (the data's booth_rack): frames, rear vents, rack units with "
                      "indicator dots, looms. Pivot: centre, ground; front -Y.")


def monitor(b, c, w=0.56, h=0.34, slot_face="signScreen"):
    """A flat monitor on a foot at c (its foot's centre), the screen facing -Y; returns the screen frame."""
    c = np.asarray(c, float)
    bx(b, c + (-0.12, -0.08, 0.0), c + (0.12, 0.08, 0.015), "plasticBlack", ch=0.004, pin=False)
    bx(b, c + (-0.025, 0.0, 0.015), c + (0.025, 0.05, 0.12), "plasticBlack", pin=False)
    bx(b, c + (-w / 2 - 0.015, -0.02, 0.10), c + (w / 2 + 0.015, 0.02, 0.10 + h + 0.03), "plasticBlack", ch=0.004, pin=False)
    o = c + (-w / 2, -0.0205, 0.115)
    return quad(b, o, X, Z, w, h, slot_face)


def m_booth_monitor(ctx, M):
    b = B(671, step=0.5)
    fr = monitor(b, (0, 0, 0))
    return done(ctx, b, "SM_Sq_Booth_Monitor", M, ground=False, screens=[fr], expect_size=(None, None, None),
                notes="Booth monitor 0.56 x 0.34 on a foot: the screen is M_MI_Screen on 0..1 (a slide from MT_Screens_A/B, named by "
                      "the placement's `slide`; small, not a large screen; LED mask off). Pivot: foot centre; screen toward -Y.")


def m_monitor_cart(ctx, M):
    """A monitor cart (1.2 x 0.5 x 1.0): steel frame on four casters, two shelves, two monitors on top. Pivot: centre."""
    b = B(681, step=0.5)
    L, W = 1.2, 0.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (L / 2 - 0.04), sy * (W / 2 - 0.04)
            bx(b, (x - 0.03, y - 0.03, 0.10), (x + 0.03, y + 0.03, 0.62), "galv", pin=False, axis="z")
            wheel(b, (x, y, 0.05), 0.05, 0.04, X, "rubber", "galv")
    for z in (0.20, 0.60):
        bx(b, (-L / 2, -W / 2, z), (L / 2, W / 2, z + 0.03), "standGrey", ch=0.003, pin=False, axis="x")
    bx(b, (-0.45, -0.18, 0.23), (0.10, 0.18, 0.45), "plasticBlack", ch=0.004, pin=False)
    frames = [monitor(b, (xx, 0.02, 0.63)) for xx in (-0.29, 0.29)]
    return done(ctx, b, "SM_Sq_Booth_MonitorCart", M, ground=True, screens=frames, expect_size=(None, None, None),
                notes="Monitor cart 1.2 x 0.5 x 1.0 (the data's monitor_cart): frame, casters, two shelves, a recorder, two monitors "
                      "(M_MI_Screen, the placement's `slide`). Pivot: centre, ground; screens toward -Y.")


# ================================================================================================= the plaza

def m_planter(ctx, M):
    """Granite planter 4.0 x 1.0 x 0.90 (the data's planter_granite): four granite walls with a chamfered coping, a plinth
    reveal, soil and a clipped box hedge to 1.25. Pivot: centre, ground; long along X."""
    b = B(701, step=0.5)
    L, W, H, t = 4.0, 1.0, 0.90, 0.12
    bx(b, (-L / 2 + 0.02, -W / 2 + 0.02, 0.0), (L / 2 - 0.02, W / 2 - 0.02, 0.06), "granite", ch=0.004, axis="x")   # reveal
    for (a, c) in (((-L / 2, -W / 2), (L / 2, -W / 2 + t)), ((-L / 2, W / 2 - t), (L / 2, W / 2)),
                   ((-L / 2, -W / 2 + t), (-L / 2 + t, W / 2 - t)), ((L / 2 - t, -W / 2 + t), (L / 2, W / 2 - t))):
        bx(b, (a[0], a[1], 0.06), (c[0], c[1], H - 0.06), "granite", ch=0.006)
    for (a, c) in (((-L / 2 - 0.02, -W / 2 - 0.02), (L / 2 + 0.02, -W / 2 + t + 0.01)), ((-L / 2 - 0.02, W / 2 - t - 0.01), (L / 2 + 0.02, W / 2 + 0.02)),
                   ((-L / 2 - 0.02, -W / 2 + t + 0.01), (-L / 2 + t + 0.01, W / 2 - t - 0.01)),
                   ((L / 2 - t - 0.01, -W / 2 + t + 0.01), (L / 2 + 0.02, W / 2 - t - 0.01))):
        bx(b, (a[0], a[1], H - 0.06), (c[0], c[1], H), "granite", ch=0.015)                       # coping
    for xx in (-L / 2 + 1.33, -L / 2 + 2.67):                                                      # joints in the coping
        bx(b, (xx - 0.004, -W / 2 - 0.025, H - 0.062), (xx + 0.004, W / 2 + 0.025, H + 0.002), "conc", pin=False, axis="y")
    bx(b, (-L / 2 + t, -W / 2 + t, 0.70), (L / 2 - t, W / 2 - t, 0.76), "soil", axis="x")
    lump(b, (L - 2 * t - 0.10, W - 2 * t - 0.10, 0.50), (0, 0, 0.75), "hedge", bevel=0.10, edge=0.15, amount=0.035, seed=3)
    return done(ctx, b, "SM_Sq_Planter_Granite_4m", M, ground=True, ledges=[(-L / 2, L / 2, H, 0.6)], cover_height=0.9,
                expect_size=(L + 0.04, W + 0.04, None),
                notes="Granite planter 4.0 x 1.0 x 0.90 (14 on the plaza, the data's planter_granite): granite walls (MI_Stone_Granite), "
                      "coping, soil, a clipped box hedge to 1.25 (MI_Leaf_PrivetClipped on a closed mesh: no masked leaves). Pivot: "
                      "centre, ground, long along X.")


def m_kiosk(ctx, M):
    """Souvenir kiosk 3.0 x 2.0 x 2.45 (the data's kiosk_souvenir): a steel cabinet on a plinth, the sales window on -Y with
    its roll shutter half down over a counter and racks of caps and folded shirts lit by a strip light, poster panels on the
    ends, a back door, and an overhanging roof with a lightbox header front and back (Kiosk_SeventhAv). Pivot: centre."""
    b = B(711, step=0.6)
    L, W, H = 3.0, 2.0, 2.45
    x0, x1, y0, y1 = -L / 2, L / 2, -W / 2, W / 2
    bx(b, (x0, y0, 0.0), (x1, y1, 0.12), "stainless", ch=0.004, axis="x")                           # plinth
    wx0, wx1, wz0, wz1 = -1.25, 1.25, 0.95, 2.00
    bx(b, (x0, y0, 0.12), (wx0, y0 + 0.06, wz1), "kiosk", axis="z")                                   # front ends
    bx(b, (wx1, y0, 0.12), (x1, y0 + 0.06, wz1), "kiosk", axis="z")
    bx(b, (wx0, y0, 0.12), (wx1, y0 + 0.06, wz0 - 0.06), "kiosk", axis="x")
    bx(b, (wx0 - 0.02, y0 - 0.30, wz0 - 0.06), (wx1 + 0.02, y0 + 0.06, wz0), "stainless", ch=0.005, axis="x")   # counter
    for (xa, xb_, ya, yb) in ((x0, x0 + 0.06, y0 + 0.06, y1), (x1 - 0.06, x1, y0 + 0.06, y1), (x0, x1, y1 - 0.06, y1)):
        bx(b, (xa, ya, 0.12), (xb_, yb, wz1), "kiosk", axis="y" if yb - ya > xb_ - xa else "x")         # ends, back
    bx(b, (x0, y0, wz1), (x1, y1, 2.10), "kiosk", axis="x")                                           # top band
    bx(b, (wx0, y0 + 0.02, 1.48), (wx1, y0 + 0.07, wz1), "shutter", axis="x")                      # shutter half down
    bx(b, (wx0 - 0.05, y0 - 0.02, wz1 - 0.02), (wx1 + 0.05, y0 + 0.14, 2.10), "kiosk", ch=0.006, pin=False, axis="x")   # its box
    bx(b, (-0.2, y0 + 0.01, 1.44), (0.2, y0 + 0.03, 1.48), "galv", pin=False)                     # shutter handle
    bx(b, (x0 + 0.06, y0 + 0.06, 0.12), (x1 - 0.06, y1 - 0.06, 0.14), "interior", axis="x")        # inside floor
    bx(b, (x0 + 0.06, y1 - 0.10, 0.9), (x1 - 0.06, y1 - 0.06, 2.0), "white", axis="x")             # back wall inside, lit
    bx(b, (wx0, y0 + 0.08, 1.37), (wx1, y0 + 0.14, 1.43), "warm", pin=False, axis="x")             # strip light
    rng = ctx.rng("kiosk")
    for i in range(10):                                                                             # caps on the back wall
        cx, cz = -1.15 + i * 0.255, 1.70 if i % 2 else 1.50
        cap = geo.sphere(0.09, 10, 5)
        co, _ = geo.arrays(cap)
        co[:, 2] = np.maximum(co[:, 2], 0.0) * 0.7
        geo.set_verts(cap, co)
        geo.transform(cap, loc=(cx, y1 - 0.18, cz), rot=(90, 0, 0))
        b.absorb(cap, ["umbrella", "white", "plasticBlack", "kiosk"][i % 4])
    for i in range(6):                                                                              # folded shirts on the counter shelf
        cx = -1.0 + i * 0.4
        bx(b, (cx - 0.15, y1 - 0.55, 0.96 + 0.0), (cx + 0.15, y1 - 0.25, 1.00 + 0.02 * (i % 3)), ["white", "plasticBlack", "umbrella"][i % 3],
           ch=0.006, pin=False)
    bx(b, (x0 + 0.1, y1 - 0.62, 0.12), (x1 - 0.1, y1 - 0.22, 0.96), "kiosk", pin=False, axis="x")   # shelf unit
    for s in (-1, 1):                                                                                # poster panels on the ends
        xe = x0 if s < 0 else x1
        bx(b, (xe + s * 0.0, y0 + 0.25, 0.5), (xe + s * 0.02, y1 - 0.25, 1.85), "standBlack", pin=False, axis="z")
    bx(b, (x1 - 0.005, -0.40, 0.14), (x1 + 0.01, 0.40, 1.95), "kiosk", ch=0.003, pin=False, axis="z")   # end door
    bx(b, (x0 - 0.15, y0 - 0.25, 2.10), (x1 + 0.15, y1 + 0.10, 2.16), "kiosk", ch=0.006, axis="x")      # roof
    bx(b, (x0 - 0.15, y0 - 0.25, 2.16), (x1 + 0.15, y1 + 0.10, 2.45), "standBlack", ch=0.004, axis="x")   # header box
    faces = []
    for s in (-1, 1):                                                                                 # lightbox faces front and back
        yf = (y0 - 0.251) if s < 0 else (y1 + 0.101)
        o = np.array((x0 - 0.10 if s < 0 else x1 + 0.10, yf, 2.19))
        faces.append(quad(b, o, X if s < 0 else -X, Z, L + 0.20, 0.23, "signFace"))
    return done(ctx, b, "SM_Sq_Kiosk_Souvenir", M, ground=True, faces=faces, cover_height=2.45, expect_size=(None, None, 2.45),
                notes="Souvenir kiosk 3.0 x 2.0 x 2.45 (the data's kiosk_souvenir): steel cabinet on a plinth, sales window on -Y with "
                      "the roll shutter half down (MI_Shutter_ScanGrey), counter, caps and folded shirts lit by a strip light "
                      "(MI_Lamp_KioskInterior), poster panels, end door, a roof with a lightbox header front and back (face "
                      "Kiosk_SeventhAv, 200 nits). Pivot: centre, ground.")


def m_foodcart(ctx, M):
    """Food cart 1.8 x 1.0 x 1.25 (the data's food_cart): a stainless body on two wheels and a front jack, a steam table with
    lids and a hot plate, a sneeze glass, a lit menu panel on -Y (Cart_Menu), a tow bar, and the umbrella half down on its
    pole (to 2.3). Pivot: centre, ground; the vendor's side +Y, the customers' -Y."""
    b = B(721, step=0.5)
    L, W, H = 1.8, 1.0, 1.25
    x0, x1, y0, y1 = -0.80, 0.80, -0.40, 0.40
    bx(b, (x0, y0, 0.32), (x1, y1, 0.95), "stainless", ch=0.01, axis="x")                            # body
    bx(b, (x0 - 0.03, y0 - 0.03, 0.95), (x1 + 0.03, y1 + 0.03, 0.98), "stainless", ch=0.006, axis="x")   # top rim
    for i, (cx, w_) in enumerate(((-0.45, 0.5), (0.10, 0.5), (0.55, 0.3))):                           # steam table lids
        bx(b, (cx - w_ / 2, -0.25, 0.98), (cx + w_ / 2, 0.25, 1.04 + 0.02 * (i == 1)), "stainless" if i < 2 else "standBlack", ch=0.012, pin=False)
        if i < 2:
            bx(b, (cx - 0.08, -0.03, 1.04), (cx + 0.08, 0.03, 1.07), "standBlack", ch=0.004, pin=False)
    b.poly_plate([(x0 + 0.05, y0 - 0.02, 0.98), (x1 - 0.05, y0 - 0.02, 0.98), (x1 - 0.05, y0 + 0.08, 1.25), (x0 + 0.05, y0 + 0.08, 1.25)][::-1],
                 0.008, "glass", kind=b.OTHER)                                                       # sneeze glass
    for s in (-1, 1):
        bx(b, (s * (x1 - 0.05) - 0.03, y0 - 0.03, 0.98), (s * (x1 - 0.05) + 0.03, y0 + 0.09, 1.25), "stainless", pin=False, axis="z")
    bx(b, (x0, y1 - 0.01, 0.40), (x1, y1 + 0.01, 0.90), "stainless", pin=False, axis="x")            # vendor doors
    bx(b, (-0.02, y1 + 0.01, 0.42), (0.02, y1 + 0.02, 0.88), "standBlack", pin=False, axis="z")
    bx(b, (x0 + 0.1, y0 - 0.05, 0.42), (x1 - 0.1, y0, 0.82), "standBlack", ch=0.006, pin=False, axis="x")  # menu box
    faces = [quad(b, (x0 + 0.13, y0 - 0.051, 0.45), X, Z, 1.34, 0.34, "signFace")]
    bx(b, (x0 + 0.1, y0 - 0.06, 0.84), (x1 - 0.1, y0, 0.86), "warm", pin=False, axis="x")           # light strip
    wheel(b, (0.45, -0.46, 0.28), 0.28, 0.08, Y)
    wheel(b, (0.45, 0.46, 0.28), 0.28, 0.08, Y)
    tube(b, (0.45, -0.42, 0.28), (0.45, 0.42, 0.28), "galv", 0.03)
    tube(b, (-0.65, 0.0, 0.32), (-0.65, 0.0, 0.0), "galv", 0.035)                                     # jack
    bx(b, (-0.72, -0.07, 0.0), (-0.58, 0.07, 0.02), "galv", pin=False)
    tube(b, (x0, 0.0, 0.40), (-0.98, 0.0, 0.40), "galv", 0.035)                                       # tow bar
    bx(b, (-0.99, -0.05, 0.36), (-0.90, 0.05, 0.44), "standBlack", ch=0.006, pin=False)
    bx(b, (x1, -0.30, 0.10), (x1 + 0.06, 0.30, 0.32), "standBlack", pin=False, axis="y")                   # propane box (closed)
    tube(b, (0.62, 0.30, 0.98), (0.62, 0.30, 2.30), "galv", 0.03)                                      # umbrella pole
    ring = []
    for i in range(10):                                                                               # half-down canopy: a narrow cone of panels
        a0, a1 = 2 * math.pi * i / 10, 2 * math.pi * (i + 1) / 10
        F = np.array([[(0.62 + 0.40 * math.cos(a), 0.30 + 0.40 * math.sin(a), 1.55) for a in (a0, a1)],
                      [(0.62 + 0.10 * math.cos(a), 0.30 + 0.10 * math.sin(a), 2.28) for a in (a0, a1)]])
        sheet(b, F, 0.006, "umbrella")
    rod(b, (0.62, 0.30, 2.28), (0.62, 0.30, 2.36), 0.05, "galv", n=10)
    b.leaks += [(0.0, y0, 0.33), (0.5, y1, 0.33)]
    return done(ctx, b, "SM_Sq_FoodCart", M, ground=True, faces=faces, cover_height=1.25, expect_size=(None, None, None),
                notes="Food cart 1.8 x 1.0 x 1.25 (the data's food_cart): stainless body, steam table and lids, sneeze glass (opaque "
                      "M_MI_Glass), lit menu panel on -Y (face Cart_Menu, 200 nits), light strip, two wheels and a jack, tow bar, the "
                      "navy umbrella half down on its pole (6 cm) to 2.36. Steam is a small particle (lane L). Pivot: centre, ground.")


def chair(b, c, rot=0.0):
    """A bistro chair (aluminium frame, slatted seat and back) at c, facing -Y turned rot degrees; every frame part under
    0.6 m (3 cm legs, kept off the hero sightlines)."""
    c = np.asarray(c, float)
    r = math.radians(rot)
    Rm = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
    P = lambda x, y, z: c + Rm @ np.array((x, y, z))
    for sx in (-1, 1):
        short_rod(b, P(sx * 0.19, -0.19, 0.0), P(sx * 0.18, -0.17, 0.44), 0.015, "stainless")
        short_rod(b, P(sx * 0.19, 0.20, 0.0), P(sx * 0.18, 0.18, 0.44), 0.015, "stainless")
        short_rod(b, P(sx * 0.18, 0.18, 0.46), P(sx * 0.18, 0.22, 0.84), 0.015, "stainless")
    for i in range(5):
        yy = -0.18 + i * 0.09
        p0, p1 = P(-0.20, yy, 0.45), P(0.20, yy + 0.06, 0.465)
        bx(b, np.minimum(p0, p1), np.maximum(p0, p1), "stainless", pin=False)
    for i in range(3):
        zz = 0.60 + i * 0.09
        p0, p1 = P(-0.19, 0.19, zz), P(0.19, 0.215, zz + 0.05)
        bx(b, np.minimum(p0, p1), np.maximum(p0, p1), "stainless", pin=False)


def m_cafetable(ctx, M):
    b = B(731, step=0.5)
    bx(b, (-0.40, -0.40, 0.72), (0.40, 0.40, 0.75), "stainless", ch=0.006, axis="x")
    bx(b, (-0.38, -0.38, 0.70), (0.38, 0.38, 0.72), "standBlack", pin=False, axis="x")
    tube(b, (0, 0, 0.04), (0, 0, 0.70), "standBlack", 0.04)
    for a in (45, 135):
        t = math.radians(a)
        R.bar(b, (-0.32 * math.cos(t), -0.32 * math.sin(t), 0.02), (0.32 * math.cos(t), 0.32 * math.sin(t), 0.02), 0.06, 0.04, "standBlack", ch=0.004)
    return done(ctx, b, "SM_Sq_CafeTable", M, ground=True, cover_height=0.75, expect_size=(0.8, 0.8, 0.75),
                notes="Plaza cafe table 0.8 x 0.8 x 0.75 (the data's cafe_table): aluminium top, black pedestal (8 cm) on a cross "
                      "base. Pivot: centre, ground.")


def m_cafechair(ctx, M):
    b = B(741, step=0.5)
    chair(b, (0, 0, 0))
    return done(ctx, b, "SM_Sq_CafeChair", M, ground=True, expect_size=(None, None, None),
                notes="Bistro chair (aluminium, slatted): dressing round the cafe tables, no collider (under the data's 0.5 m clutter "
                      "rule for loose chairs); legs 3 cm, every part under 0.6 m. Pivot: centre, ground; it faces -Y.")


def m_chairstack(ctx, M):
    b = B(742, step=0.5)
    chair(b, (0, 0, 0))
    chair(b, (0, 0.02, 0.055))
    return done(ctx, b, "SM_Sq_CafeChair_Stack", M, ground=True, expect_size=(None, None, None),
                notes="Two bistro chairs stacked (the data's cafe_chairs, 0.5 x 0.5 x 0.9). Pivot: centre, ground.")


def m_lightpole(ctx, M):
    """Plaza LED light pole, 8.0 m (the data's light_pole, 0.30 at the base): a cast base, a tapered steel pole, a twin
    arm with two flat LED heads (MI_Lamp_LED, 4000 K) and a banner bracket. Pivot: centre, ground; the arms along X."""
    b = B(751, step=0.8)
    rod(b, (0, 0, 0), (0, 0, 0.55), 0.15, "standBlack", n=16)
    rod(b, (0, 0, 0.55), (0, 0, 0.62), 0.13, "standBlack", n=16)
    prof = geo.revolve([(0.0, 0.62), (0.11, 0.62), (0.075, 7.7), (0.0, 7.72)], 12)
    b.absorb(prof, "standBlack")
    for s in (-1, 1):
        R.bar(b, (0, 0, 7.45), (s * 0.90, 0, 7.62), 0.08, 0.06, "standBlack", ch=0.004)
        bx(b, (s * 0.90 - 0.30, -0.12, 7.56), (s * 0.90 + 0.30, 0.12, 7.66), "standBlack", ch=0.01, pin=False, axis="x")
        bx(b, (s * 0.90 - 0.27, -0.10, 7.554), (s * 0.90 + 0.27, 0.10, 7.56), "led", pin=False, axis="x")
    for z in (3.2, 4.6):                                                                                # banner bracket (no banner)
        R.bar(b, (0, 0, z), (0, -0.55, z), 0.06, 0.06, "standBlack", ch=0.004)
    bx(b, (-0.06, 0.08, 1.0), (0.06, 0.16, 1.25), "standBlack", ch=0.004, pin=False)                       # hand hole cover
    return done(ctx, b, "SM_Sq_LightPole_LED", M, ground=True, expect_size=(None, None, None),
                notes="Plaza LED pole 8.0 m: cast base 0.30, tapered pole, twin arm, two flat LED heads (MI_Lamp_LED, emissive; the "
                      "light is one of the 12 placed 4000 K spots, midtown.md 11.1), banner bracket. Pivot: centre, ground; arms along X.")


def m_jersey(ctx, M):
    """Concrete safety-shape barrier, 1.8 m module (the data's jersey_barrier boxes are 1.8 to 3.8 m: one or two modules,
    stretched along X): the safety profile 0.50 at the foot, 0.15 at the top, 0.81 high, lifting slots, end keys.
    Pivot: centre, on the roadway."""
    b = B(761, step=0.6)
    L = 1.8
    prof = [(-0.25, 0.0), (0.25, 0.0), (0.25, 0.075), (0.16, 0.33), (0.075, 0.81), (-0.075, 0.81), (-0.16, 0.33), (-0.25, 0.075)]
    b.prism(prof, (-L / 2 + 0.02, 0, 0), Y, Z, (L - 0.04, 0, 0), "conc", step=0.6, pstep=0.25, uv_off=(0.0, 0.0))
    for s in (-1, 1):
        b.prism([(p[0] * 0.92, p[1] * 0.97) for p in prof], (s * (L / 2 - 0.02), 0, 0), Y, Z, (s * 0.02, 0, 0), "conc", pstep=0.25)
    for xx in (-0.45, 0.45):                                                                            # fork slots at the foot
        bx(b, (xx - 0.10, -0.252, 0.0), (xx + 0.10, 0.252, 0.06), "interior", pin=False, axis="y")
    bx(b, (-0.08, -0.04, 0.80), (0.08, 0.04, 0.815), "galv", pin=False)                                   # lifting loop plate
    return done(ctx, b, "SM_Sq_Barrier_Jersey_1p8", M, ground=True, cover_height=0.81, expect_size=(None, 0.5, 0.81),
                notes="Concrete safety-shape barrier module 1.8 m (0.50 foot, 0.15 top, 0.81 high), fork slots, lifting plate. The "
                      "data's jersey_barrier boxes take one or two modules stretched along X to the box (scale in the placement). "
                      "Pivot: centre, roadway.")


def m_water(ctx, M):
    """Water-filled plastic barrier 1.9 x 0.6 x 0.9: orange body with a white top band, a fill cap, interlock lugs, a
    fork tunnel. Pivot: centre, ground."""
    b = B(771, step=0.5)
    L = 1.9
    prof = [(-0.30, 0.0), (0.30, 0.0), (0.30, 0.12), (0.20, 0.30), (0.15, 0.78), (0.12, 0.90), (-0.12, 0.90), (-0.15, 0.78),
            (-0.20, 0.30), (-0.30, 0.12)]
    b.prism(prof, (-L / 2 + 0.08, 0, 0), Y, Z, (L - 0.16, 0, 0), "orange", step=0.5, pstep=0.2)
    top = [(-0.152, 0.64), (0.152, 0.64), (0.153, 0.785), (0.122, 0.905), (-0.122, 0.905), (-0.153, 0.785)]
    b.prism(top, (-L / 2 + 0.079, 0, 0), Y, Z, (L - 0.158, 0, 0), "white", step=0.5, pstep=0.2)
    for s in (-1, 1):                                                                                    # rounded ends
        b.prism([(p[0] * 0.85, p[1] * 0.97) for p in prof], (s * (L / 2 - 0.08), 0, 0), Y, Z, (s * 0.07, 0, 0), "orange", pstep=0.2)
        xa, xb_ = sorted((s * L / 2, s * (L / 2 - 0.07)))
        for z in (0.25, 0.70):
            bx(b, (xa, -0.06, z), (xb_, 0.06, z + 0.10), "orange", ch=0.01, pin=False)
    rod(b, (0.5, 0, 0.90), (0.5, 0, 0.94), 0.06, "white", n=12)                                          # fill cap
    bx(b, (-0.25, -0.302, 0.02), (0.25, 0.302, 0.11), "interior", pin=False, axis="y")                    # fork tunnel
    return done(ctx, b, "SM_Sq_Barrier_Water_1p9", M, ground=True, cover_height=0.9, expect_size=(None, 0.6, None),
                notes="Water-filled plastic barrier 1.9 x 0.6 x 0.9: orange body (TS_Plastic_Orange), white top band, fill cap, "
                      "interlock lugs, fork tunnel. Pivot: centre, ground.")


def m_bike(ctx, M):
    """Steel crowd-control barrier ('bike rack') 2.4 x 0.5 x 1.1, no agency mark: tube frame (6 cm), flat-bar pickets 6 cm
    wide, bridge feet, the hook and eye at the ends. Pivot: centre, ground; long along X."""
    b = B(781, step=0.6)
    L, H = 2.4, 1.1
    x0, x1 = -1.10, 1.10
    for s in (-1, 1):
        tube(b, (s * 1.10, 0, 0.12), (s * 1.10, 0, H), "galv", 0.03)
        bx(b, (s * 1.10 - 0.04, -0.25, 0.0), (s * 1.10 + 0.04, 0.25, 0.04), "galv", ch=0.004, pin=False, axis="y")   # bridge foot
        R.bar(b, (s * 1.10, 0, 0.04), (s * 1.10, 0, 0.14), 0.06, 0.06, "galv")
        tube(b, (s * 1.10, 0, H - 0.08), (s * 1.18, 0, H - 0.08), "galv", 0.03)                           # hook / eye
    tube(b, (x0, 0, H), (x1, 0, H), "galv", 0.03)
    tube(b, (x0, 0, 0.18), (x1, 0, 0.18), "galv", 0.03)
    for xx in np.linspace(x0 + 0.16, x1 - 0.16, 13):
        R.bar(b, (xx, 0, 0.20), (xx, 0, H - 0.02), 0.06, 0.012, "galv", up=Y)
    return done(ctx, b, "SM_Sq_Barrier_Bike_2p4", M, ground=True, expect_size=(None, 0.5, None),
                notes="Steel crowd-control barrier 2.4 x 0.5 x 1.1 (the data's bike_barrier; no agency mark): 6 cm tube frame, 6 cm "
                      "flat-bar pickets, bridge feet, hook and eye. Pivot: centre, ground; long along X.")


def m_generator(ctx, M):
    """Towable generator 1.6 x 1.2 x 1.15 (the data's generator by the Stand): an enclosure on a single-axle trailer, doors
    with louvres, a control panel, the exhaust, lifting eye, the DANGER / HIGH VOLTAGE label, and a cable tail to the Stand.
    Pivot: centre, ground; long along X (the tow bar toward -X)."""
    b = B(791, step=0.5)
    ex0, ex1, ey0, ey1, ez0, ez1 = -0.55, 0.78, -0.45, 0.45, 0.34, 1.05
    bx(b, (-0.62, -0.40, 0.26), (0.80, 0.40, 0.34), "standBlack", ch=0.004, pin=False, axis="x")                  # chassis
    bx(b, (ex0, ey0, ez0), (ex1, ey1, ez1), "genWhite", ch=0.015, axis="x")                                     # enclosure
    for s in (-1, 1):
        y = ey0 if s < 0 else ey1
        for i in range(2):                                                                                   # doors with louvres
            xa = ex0 + 0.08 + i * 0.62
            ya, yb = sorted((y, y + s * 0.008))
            bx(b, (xa, ya, ez0 + 0.08), (xa + 0.56, yb, ez1 - 0.08), "genWhite", ch=0.003, pin=False, axis="x")
            ya, yb = sorted((y, y + s * 0.012))
            for zz in np.arange(ez0 + 0.16, ez0 + 0.40, 0.06):
                bx(b, (xa + 0.08, ya, zz), (xa + 0.48, yb, zz + 0.025), "grille", pin=False, axis="x")
        wheel(b, (0.15, s * 0.52, 0.25), 0.25, 0.14, Y)
        bx(b, (-0.20, s * 0.52 - 0.09, 0.50), (0.50, s * 0.52 + 0.09, 0.53), "standBlack", ch=0.004, pin=False, axis="x")   # fender
    tube(b, (ex0, 0.0, 0.30), (-0.80, 0.0, 0.30), "standBlack", 0.035)                                            # tow bar
    bx(b, (-0.80, -0.05, 0.26), (-0.72, 0.05, 0.34), "standBlack", ch=0.004, pin=False)
    tube(b, (-0.66, 0.0, 0.30), (-0.66, 0.0, 0.0), "galv", 0.035)                                            # jack
    bx(b, (ex1, -0.30, 0.55), (ex1 + 0.02, 0.30, 0.95), "standBlack", ch=0.003, pin=False, axis="z")             # control panel
    bx(b, (ex1 + 0.02, -0.25, 0.85), (ex1 + 0.025, -0.05, 0.92), "indicator", pin=False)
    lab = R.label(b, (ex1 + 0.021, 0.06, 0.62), Y, Z, 0.20, 0.14)
    tube(b, (0.45, 0.25, ez1), (0.45, 0.25, 1.15), "standBlack", 0.04)                                            # exhaust
    bx(b, (-0.05, -0.05, ez1), (0.05, 0.05, ez1 + 0.06), "galv", pin=False)                                  # lifting eye
    for i, y in enumerate((-0.15, 0.0, 0.15)):                                                               # cable tail
        tube(b, (ex1 + 0.02, y, 0.60), (ex1 + 0.10, y, 0.05), "rubber", 0.03)
    b.leaks += [(0.45, 0.25, ez1), (ex1, 0.0, 0.55)]
    return done(ctx, b, "SM_Sq_Generator", M, ground=True, labels=[lab], cover_height=1.05, expect_size=(None, None, None),
                notes="Towable generator 1.6 x 1.2 x 1.15 (the data's generator by the Stand; the hum's point source, midtown.md 13): "
                      "enclosure (the beige steel slot), louvred doors, single-axle trailer, tow bar, jack, control panel with a lit "
                      "indicator, label Label_HighVoltage, exhaust, cable tail. Pivot: centre, ground; tow bar -X.")


def m_roadcases(ctx, M):
    """A stack of road cases 2.0 x 1.4 x 1.9 (the data's road_cases): four columns of black laminate cases on casters,
    aluminium edge bands 6 cm wide, ball corners, latches, BRIGHTWIRE stencils on the -Y faces. Pivot: centre, ground."""
    b = B(801, step=0.5)
    rng = ctx.rng("cases")
    faces = []
    for ci, (cx, cy) in enumerate(((-0.5, -0.35), (0.5, -0.35), (-0.5, 0.35), (0.5, 0.35))):
        z = 0.0
        heights = [0.62, 0.58, 0.55] if ci % 2 == 0 else [0.78, 0.92]
        for hi, h in enumerate(heights):
            if z + h > 1.9 + 1e-6:
                break
            w, d = 0.96, 0.66
            if hi == 0:
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        wheel(b, (cx + sx * 0.36, cy + sy * 0.24, 0.05), 0.05, 0.04, X, "rubber", "galv")
                z0 = 0.10
            else:
                z0 = z
            z1 = z0 + h - (0.10 if hi == 0 else 0.0)
            bx(b, (cx - w / 2, cy - d / 2, z0), (cx + w / 2, cy + d / 2, z1), "plasticBlack", ch=0.01, axis="x")
            for zz in (z0, z1 - 0.06, (z0 + z1) / 2 - 0.03):
                bx(b, (cx - w / 2 - 0.004, cy - d / 2 - 0.004, zz), (cx + w / 2 + 0.004, cy + d / 2 + 0.004, zz + 0.06), "galv", pin=False, axis="x")
            for sx in (-1, 1):
                bx(b, (cx + sx * (w / 2 - 0.08) - 0.03, cy - d / 2 - 0.012, (z0 + z1) / 2 - 0.03), (cx + sx * (w / 2 - 0.08) + 0.03,
                   cy - d / 2 - 0.004, (z0 + z1) / 2 + 0.03), "galv", pin=False)
            if cy < 0 and rng.random() < 0.8:
                o = (cx - 0.25, cy - d / 2 - 0.0045, z0 + 0.12)
                faces.append(quad(b, o, X, Z, 0.50, 0.17, "signFace"))
            z = z1
    return done(ctx, b, "SM_Sq_RoadCase_Stack", M, ground=True, faces=faces, cover_height=1.9, expect_size=(None, None, None),
                notes="Road cases stacked 2.0 x 1.4 x 1.9 (the data's road_cases, the crew's): black laminate cases on casters, "
                      "6 cm aluminium bands, latches, Stencil_Brightwire faces on the -Y side. Pivot: centre, ground.")


def m_cableramp(ctx, M):
    b = B(811, step=0.4)
    L = 1.2
    prof = [(-0.25, 0.0), (0.25, 0.0), (0.12, 0.075), (-0.12, 0.075)]
    b.prism(prof, (-L / 2, 0, 0), Y, Z, (L, 0, 0), "rubber", pstep=0.2)
    bx(b, (-L / 2, -0.11, 0.075), (L / 2, 0.11, 0.08), "yellow", pin=False, axis="x")
    for xx in np.linspace(-L / 2 + 0.2, L / 2 - 0.2, 3):
        bx(b, (xx - 0.004, -0.11, 0.076), (xx + 0.004, 0.11, 0.081), "standBlack", pin=False, axis="y")
    return done(ctx, b, "SM_Sq_CableRamp_1p2", M, ground=True, expect_size=(L, 0.5, None),
                notes="Cable protector ramp 1.2 x 0.5 x 0.08 (the data's cable_ramp): rubber body, yellow lid. Pivot: centre, ground.")


def m_cabledrum(ctx, M):
    b = B(821, step=0.4)
    for z in (0.0, 0.89):
        rod(b, (0, 0, z), (0, 0, z + 0.06), 0.40, "drum", n=24)
    rod(b, (0, 0, 0.06), (0, 0, 0.89), 0.34, "rubber", n=24)
    for z in np.arange(0.10, 0.86, 0.075):
        rod(b, (0, 0, z), (0, 0, z + 0.06), 0.345, "rubber", n=24)
    rod(b, (0, 0, 0.95), (0, 0, 0.97), 0.08, "galv", n=12)
    tube(b, (0.34, 0.0, 0.5), (0.55, 0.05, 0.03), "rubber", 0.03)
    return done(ctx, b, "SM_Sq_CableDrum", M, ground=True, expect_size=(None, None, None),
                notes="Cable drum stood on its flange, 0.80 across, 0.97 high (the data's cable_drum in the front court), wound "
                      "with black cable, a tail to the ground. Pivot: centre, ground.")


PROPS = [
    lambda c, M: m_tier(c, M, 12.0), lambda c, M: m_tier(c, M, 3.0), m_wingside, m_booth_side, m_booth_front, m_stand_back,
    m_booth_desk, m_booth_rack, m_booth_monitor, m_monitor_cart,
    m_planter, m_kiosk, m_foodcart, m_cafetable, m_cafechair, m_chairstack, m_lightpole, m_jersey, m_water, m_bike,
    m_generator, m_roadcases, m_cableramp, m_cabledrum,
]


def build(ctx, M):
    materials(ctx, M)
    for f in PROPS:
        f(ctx, M)
