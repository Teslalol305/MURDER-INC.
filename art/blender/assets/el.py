"""The El: the elevated line over Jamaica Avenue as a modular kit of early twentieth-century riveted steelwork.

The game's overall dimensions are kept (src/level/el.js, layout.js; docs/unreal/spec/05-level.md 2.7): column pairs
every 10 m, rows 9.2 m apart (y = +-4.6), cap at 5.30 m, cross girder 5.30..6.50, deck underside 6.50, rail top
6.83, deck 10.8 m wide, tracks at y = +-2.1, gauge 1.435. What the game draws as boxes is built as the structure
those boxes stand for:

    SM_El_Column          built-up H column: web plate, four web angles, two flange plates, four tip angles tied by
                          batten plates on the open sides, riveted; a flared base of wing plates, stiffeners and base
                          angles on a base plate with eight anchor bolts, on a chamfered concrete pedestal.
                          Pivot: centre of the footprint on the ground. Flanges face east and west.
    SM_El_Bent            transverse plate girder (web, four flange angles, cover plates, stiffener angles on
                          fillers every metre, web splices) and the two knee braces down to the columns (double
                          angles on gusset plates with connection angles). Pivot: centre line, ground, girder along Y.
    SM_El_GirderSpan_10m  two longitudinal plate girders over the column rows, four rolled stringers under the
                          rails, end connections to the cross girders, longitudinal knee braces, fascia girders on
                          brackets, the mid-span cross frame and the lateral bracing. Pivot: west bent, centre
                          line, ground; runs +X.
    SM_El_Deck_10m        open deck: 36 timber ties with daylight between them, four running rails on tie plates
                          with spikes, guard timbers, third rails on insulators under cover boards, steel walkways
                          on bearers with pipe railing and toe board, a plank walkway between the tracks, a cable
                          trough and conduits. Same pivot as the span.
    SM_El_Lamp            the sodium fixture hung under the deck. Pivot: its mounting point (it hangs down -Z).

Placement (Blender, metres): bents at x = k * 10; columns at (x, +-4.6, 0); bent, span and deck at (x, 0, 0);
lamps at (x + 5, +-2.1, 6.02), alternating sides.

Slots are scanned tiling sets (art/scans/sets.json), UVs are in real metres divided by each set's tile size, and
the Wear masks are painted from the geometry: R dirt in roots and pockets and soot on undersides, G rust creeping
in from plate edges, rivet heads and wherever water sits, B rust runs below rivets and connections, A pale dust on
upward faces and splash-back at the column foot.
"""
import math
import os

import bpy
import numpy as np

from mi import geo, mat, paths, render, scene, steel
from assets.street import STEEL_RUST, Waves, sstep

FAMILY = {"name": "el", "description": "The El: riveted column, bent, 10 m girder span, open deck with tracks, lamp"}

SPACING = 10.0
ROW_Y = 4.6
COL_TOP = 5.30
DECK = 6.50
TIE_TOP = 6.68
RAIL_TOP = 6.83
HALF = 5.40
TRACKS = (-2.1, 2.1)
GAUGE = 1.435
RAIL_Y = [c + s * GAUGE / 2 for c in TRACKS for s in (-1, 1)]
N_TIES = 18                                   # per track per module: pitch 0.556 m (the game's 0.56), gaps 0.336
LAMP_Z = 6.02

X = np.array([1.0, 0.0, 0.0])
Y = np.array([0.0, 1.0, 0.0])
Z = np.array([0.0, 0.0, 1.0])


def V(*a):
    return np.array(a, dtype=np.float64)


def line(p0, p1, pitch=0.15):
    """Points from p0 to p1 at about `pitch`, inset half a pitch at both ends (rows continue across modules)."""
    p0, p1 = np.asarray(p0, dtype=np.float64), np.asarray(p1, dtype=np.float64)
    n = max(1, int(round(np.linalg.norm(p1 - p0) / pitch)))
    t = (np.arange(n) + 0.5) / n
    return p0[None, :] + (p1 - p0)[None, :] * t[:, None]


def keep(points, axis, ranges):
    """Drop the points whose coordinate on `axis` falls inside any (lo, hi) range."""
    if len(points) == 0 or not ranges:
        return points
    c = points[:, axis]
    ok = np.ones(len(points), dtype=bool)
    for lo, hi in ranges:
        ok &= ~((c > lo) & (c < hi))
    return points[ok]


# ------------------------------------------------------------------------------------------------------ materials

def materials(ctx):
    sc = ctx.scan_set
    M = {}
    # El green: the scan is a yellower green than the art bible's #354C40..#3F5A4C, so it is tinted toward blue.
    # G: chalking first, then the paint gives way to the rust scan. A: pale dust on tops.
    M["steel"] = sc("TS_Steel_ScanPaintGreen", blend="TS_Steel_ScanRust", alpha="splash", tint=(0.84, 1.0, 1.30),
                    blend_start=0.35, wear_tint=(1.18, 1.16, 1.12), wear_rough=0.12, dirt_color=(0.030, 0.029, 0.027),
                    leak_color=(0.24, 0.10, 0.035), leak_rough=0.12, macro=0.16, blend_tint=(0.85, 0.85, 0.85))
    # rails, tie plates, spikes, third rail: rust; G polishes the running surface to bare steel. The slot is shared
    # with the street's kerb steel, so the parameters are the street's (A is wetness there: the deck paints 0)
    M["rail"] = sc("TS_Steel_ScanRust", **STEEL_RUST)
    # creosoted timber: the grey scan tinted dark and warm; G bleaches it where the sun and feet work on it
    M["tie"] = sc("TS_Wood_ScanTie", alpha="splash", tint=(0.66, 0.58, 0.52), wear_tint=(1.75, 1.75, 1.75), wear_rough=0.05,
                  dirt_color=(0.022, 0.020, 0.018), leak_color=(0.20, 0.09, 0.035), macro=0.2)
    M["concrete"] = sc("TS_Concrete_ScanFormed", alpha="splash", dirt_color=(0.07, 0.064, 0.056), wear_tint=(1.12, 1.11, 1.09),
                       leak_color=(0.26, 0.12, 0.05), macro=0.14)
    M["trough"] = sc("TS_Concrete_ScanRough", alpha="splash", dirt_color=(0.05, 0.046, 0.042), macro=0.14)
    M["tread"] = sc("TS_Plate_ScanDiamond", alpha="splash", wear_metal=0.75, wear_tint=(1.3, 1.3, 1.3), wear_rough=-0.3,
                    dirt_color=(0.03, 0.028, 0.026))
    M["white"] = sc("TS_Steel_ScanPaintWhite", alpha="splash", dirt_color=(0.06, 0.05, 0.035), macro=0.1)
    glow = mat.flat("MI_Glass_SodiumLens", (0.9, 0.75, 0.5), 0.25)
    bs = mat.principled(glow)
    bs.inputs["Emission Color"].default_value = (1.0, 0.46, 0.11, 1.0)       # high-pressure sodium, #FFB45E
    bs.inputs["Emission Strength"].default_value = 12.0
    M["glow"] = glow
    return M


# ------------------------------------------------------------------------------------------------------- weather

def weather(ctx, b, ob, key, column=False):
    """Paint the Wear mask of a steel module from its geometry (see the module docstring)."""
    W = b.loops(ob, ao=0.10, rays=8)
    rng = ctx.rng("wear", key)
    P, N = W.P, W.N
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    wa, wb, wc = Waves(rng, 0.55), Waves(rng, 2.4), Waves(rng, 0.16)
    a = wa.u(x + 0.61 * z, y + 0.37 * z)
    bb = wb.u(x + 0.5 * z, y - 0.5 * z)
    c = wc.u(x + z, y + 0.7 * z)
    up, down = np.clip(N[:, 2], 0, 1), np.clip(-N[:, 2], 0, 1)
    ao = W.ao
    R = 0.05 + 0.85 * ao * (0.55 + 0.6 * a) + 0.30 * W.concave + 0.22 * down * (0.4 + 0.8 * bb)
    G = W.convex * sstep(0.30, 0.72, 0.6 * a + 0.4 * c) * (0.5 + 0.5 * bb)            # plate edges and member ends
    G = np.maximum(G, 0.95 * up * sstep(0.2, 0.55, ao) * (0.5 + 0.5 * a))             # where water sits
    riv = W.kind == b.RIVET
    G = np.where(riv, np.maximum(G, 0.95 * sstep(0.60, 0.78, c) * (0.6 + 0.4 * a)), G)  # some heads have lost their paint
    G = np.maximum(G, 0.16 * up * (1 - ao) * (0.5 + bb))                              # chalking on sunlit tops
    B = steel.streaks(P, N, b.leaks, 0.6, 0.04, seed=len(P)) * (0.65 + 0.5 * a)
    A = up * (0.25 + 0.55 * bb) * (1 - 0.6 * ao)
    if column:
        foot = sstep(1.5, 0.3, z)
        G = np.maximum(G, 0.9 * foot * sstep(0.35, 0.75, a) * (0.4 + 0.6 * np.maximum(W.convex, ao)))
        R = np.maximum(R, 0.5 * sstep(2.2, 0.4, z) * (0.3 + 0.7 * bb))                # hands, exhaust, road spray
        A = np.maximum(A, np.exp(-np.clip(z - 0.26, 0, None) / 0.22) * (0.6 + 0.4 * c) * (1 - 0.5 * up))
        con = W.is_slot("concrete")
        steepness = 1 - np.abs(N[:, 2])
        Rc = 0.18 + 0.5 * ao + 0.35 * a * steepness + 0.3 * up * bb
        Gc = np.maximum(W.convex * (0.5 + 0.5 * c), 0.55 * steepness * sstep(0.55, 0.8, c))   # chipped arrises, bumper scars
        Bc = steepness * sstep(0.35, 0.7, 0.5 * a + 0.5 * wc.u(x * 3.0 + y * 3.0, z * 0.2)) * 0.9 + 0.5 * up * sstep(0.47, 0.42, np.maximum(np.abs(x), np.abs(y)))
        Ac = np.clip(np.exp(-z / 0.12) * (0.7 + 0.5 * c), 0, 1)
        R, G, B, A = np.where(con, Rc, R), np.where(con, Gc, G), np.where(con, Bc, B), np.where(con, Ac, A)
    geo.set_wear(ob, np.clip(np.stack([R, G, B, A], axis=1), 0, 1), per="corner")
    return W


# ------------------------------------------------------------------------------------------------------- column

def build_column(ctx, M):
    b = steel.Builder(step=0.14, chamfer=0.0025, seed=11)
    S = "steel"
    zb, zc = 0.315, COL_TOP - 0.03              # top of the base plate, underside of the cap plate
    # ---- pedestal, grout, base plate, anchor bolts
    ped = geo.box((1.04, 1.04, 0.26), bevel=0.02, segments=2, name="ped")
    geo.densify(ped, 0.09, 6)
    geo.displace(ped, 0.004, 2.5, seed=3)
    b.absorb(ped, "concrete")
    grout = geo.box((0.95, 0.95, 0.022), bevel=0.008, segments=1, name="grout")
    geo.transform(grout, loc=(0, 0, 0.255))
    b.absorb(grout, "concrete")
    b.box((-0.445, -0.445, 0.275), (0.445, 0.445, zb), S)
    bolts = [(sx * 0.39, sy * 0.39) for sx in (-1, 1) for sy in (-1, 1)] + [(0.405, 0.0), (-0.405, 0.0), (0.0, 0.405), (0.0, -0.405)]
    for (bx, by) in bolts:
        b.box((bx - 0.04, by - 0.04, zb), (bx + 0.04, by + 0.04, zb + 0.010), S, chamfer=0.002)
    rr = ctx.rng("col", "bolts")
    from mathutils import Matrix
    nuts = geo.instances(geo.nut(0.036, "anchor"), [Matrix.Translation((bx, by, zb + 0.010)) @ Matrix.Rotation(rr.uniform(0, 1.0), 4, "Z")
                                                    for bx, by in bolts], "anchors")
    b.absorb(nuts, S)
    b.leaks += [(bx, by, zb) for bx, by in bolts]
    # ---- shaft: flange plates, web, web angles, tip angles
    L = zc - zb
    for sx in (-1, 1):
        b.box((sx * 0.234, -0.24, zb), (sx * 0.25, 0.24, zc), S)
    b.box((-0.234, -0.006, zb), (0.234, 0.006, zc), S)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.prism(steel.angle(0.10, 0.14, 0.012), (sx * 0.234, sy * 0.006, zb), (-sx, 0, 0), (0, sy, 0), (0, 0, L), S)
            b.prism(steel.angle(0.09, 0.09, 0.010), (sx * 0.234, sy * 0.24, zb), (-sx, 0, 0), (0, -sy, 0), (0, 0, L), S)
    # ---- batten plates across the open sides (the top one is tall: the knee-brace gusset lands on it)
    riv, rn = [], []
    battens = [(zb, zb + 0.36), (1.55, 1.85), (2.50, 2.80), (3.45, 3.75), (3.88, 4.73), (5.06, zc)]
    for sy in (-1, 1):
        for z0, z1 in battens:
            b.box((-0.23, sy * 0.24, z0), (0.23, sy * 0.25, z1), S)
            for xx in (-0.185, 0.185):
                p = line((xx, sy * 0.25, z0), (xx, sy * 0.25, z1), 0.105)
                riv.append(p)
                rn.append(np.tile(V(0, sy, 0), (len(p), 1)))
    # ---- flared base: wing plates on the flange faces, stiffeners square to them, base angles
    for sx in (-1, 1):
        rows = []
        for zz, w in ((zb, 0.445), (zb + 0.10, 0.445), (1.20, 0.24)):
            l, r = (sx * 0.262, -sx * w, zz), (sx * 0.262, sx * w, zz)
            rows.append((l, r))
        b.plate_rows(rows, 0.012, S)
        for y0 in (-0.16, 0.16):
            sg = 1.0 if y0 > 0 else -1.0
            rows = []
            for zz, xo in ((zb, 0.445), (zb + 0.08, 0.445), (0.95, 0.30)):
                pa, pc = V(sx * 0.262, y0 + 0.006, zz), V(sx * xo, y0 + 0.006, zz)
                rows.append((pc, pa) if pc[0] > pa[0] else (pa, pc))
            b.plate_rows(rows, 0.012, S)
            yy = y0 + sg * 0.006 if sg > 0 else y0 - 0.006
            b.prism(steel.angle(0.065, 0.075, 0.008), (sx * 0.262, yy, zb + 0.10), (sx, 0, 0), (0, sg, 0), (0, 0, 0.36), S)
            p = line((sx * 0.270, yy + sg * 0.045, zb + 0.10), (sx * 0.270, yy + sg * 0.045, zb + 0.46), 0.12)
            riv.append(p)
            rn.append(np.tile(V(sx, 0, 0), (len(p), 1)))
            p = line((sx * 0.262 + sx * 0.04, yy + sg * 0.008, zb + 0.10), (sx * 0.262 + sx * 0.04, yy + sg * 0.008, zb + 0.46), 0.12)
            riv.append(p)
            rn.append(np.tile(V(0, sg, 0), (len(p), 1)))
        for ya, yb in ((-0.445, -0.25), (-0.15, 0.15), (0.25, 0.445)):
            b.prism(steel.angle(0.10, 0.10, 0.012), (sx * 0.262, ya, zb), (sx, 0, 0), (0, 0, 1), (0, yb - ya, 0), S)
            p = line((sx * 0.274, ya, zb + 0.06), (sx * 0.274, yb, zb + 0.06), 0.10)
            riv.append(p)
            rn.append(np.tile(V(sx, 0, 0), (len(p), 1)))
    for sy in (-1, 1):
        b.prism(steel.angle(0.10, 0.10, 0.012), (-0.23, sy * 0.25, zb), (0, sy, 0), (0, 0, 1), (0.46, 0, 0), S)
        p = line((-0.23, sy * 0.262, zb + 0.06), (0.23, sy * 0.262, zb + 0.06), 0.10)
        riv.append(p)
        rn.append(np.tile(V(0, sy, 0), (len(p), 1)))
    # ---- rivet lines on the flanges (through the web angles and the tip angles), on the web, on the wing plates
    for sx in (-1, 1):
        for k, yy in enumerate((-0.195, -0.085, 0.085, 0.195)):
            stagger = 0.075 if k in (1, 2) else 0.0
            p = line((sx * 0.25, yy, 1.24 + stagger), (sx * 0.25, yy, 5.09 + stagger - 0.15), 0.15)
            if k in (1, 2):
                p = keep(p, 2, [(4.03, 4.89)])             # the knee-brace connection angles of the span land here
            riv.append(p)
            rn.append(np.tile(V(sx, 0, 0), (len(p), 1)))
            p = line((sx * 0.262, yy, zb + 0.14 + stagger), (sx * 0.262, yy, 1.19 + stagger - 0.15), 0.15)
            riv.append(p)
            rn.append(np.tile(V(sx, 0, 0), (len(p), 1)))
        for sy in (-1, 1):
            p = line((sx * 0.179, sy * 0.018, zb + 0.05), (sx * 0.179, sy * 0.018, zc - 0.05), 0.15)
            riv.append(p)
            rn.append(np.tile(V(0, sy, 0), (len(p), 1)))
    # ---- cap: plate, cap angles, bolts up into the cross girder
    b.box((-0.31, -0.31, zc), (0.31, 0.31, COL_TOP), S)
    for sx in (-1, 1):
        b.prism(steel.angle(0.06, 0.15, 0.012), (sx * 0.25, -0.24, zc), (sx, 0, 0), (0, 0, -1), (0, 0.48, 0), S)
        p = line((sx * 0.262, -0.24, zc - 0.09), (sx * 0.262, 0.24, zc - 0.09), 0.12)
        riv.append(p)
        rn.append(np.tile(V(sx, 0, 0), (len(p), 1)))
    for sy in (-1, 1):
        b.prism(steel.angle(0.06, 0.15, 0.012), (-0.23, sy * 0.25, zc), (0, sy, 0), (0, 0, -1), (0.46, 0, 0), S)
        p = line((-0.23, sy * 0.262, zc - 0.09), (0.23, sy * 0.262, zc - 0.09), 0.115)
        riv.append(p)
        rn.append(np.tile(V(0, sy, 0), (len(p), 1)))
    heads = geo.instances(geo.hex_bolt(0.024, name="capbolt"), [Matrix.Translation((sx * 0.275, sy * 0.275, zc)) @ Matrix.Rotation(math.pi, 4, "X")
                                                               for sx in (-1, 1) for sy in (-1, 1)], "capbolts")
    b.absorb(heads, S)
    b.rivets(np.concatenate(riv), np.concatenate(rn), S)
    ob = b.finish("SM_El_Column", M, ctx.col)
    weather(ctx, b, ob, "column", column=True)
    ctx.asset(ob, collision="box", cover_height=COL_TOP, pivot="centre of the footprint on the ground; flanges face +X and -X",
              expect_size=(1.04, 1.04, COL_TOP), notes=(
        "El column, 5.30 m to the cap. Built-up H: 12 mm web, four web angles, two 480 x 16 flange plates, four tip "
        "angles tied by batten plates on the north and south (open) sides; rivets 36 mm at 150 mm pitch. Flared base: "
        "wing plates to 0.89 m, stiffeners, base angles, 0.89 m base plate, eight anchor bolts, concrete pedestal "
        "1.04 x 1.04 x 0.26 with 20 mm chamfers. Gameplay collider: box 0.64 x 0.64 x 5.30 (tag el-column). The cross "
        "girder of SM_El_Bent sits on the cap; knee-brace gussets land on the tall batten at z 3.88..4.73 and on the "
        "flange faces at z 4.07..4.85."))
    return ob


# ---------------------------------------------------------------------------------------------- shared steelwork

def plate_girder(b, x0, x1, z0, z1, fw, ct, aw, ah, at, stations, S="steel", under_skip=(), top_heads=False, splices=()):
    """A riveted plate girder along +X in the plane y = 0: 12 mm web, four flange angles (aw on the cover plate, ah
    on the web, at thick), cover plates fw wide and ct thick, pairs of stiffener angles on fillers at `stations`
    (x of the angle's heel), web splices at `splices`. under_skip: (lo, hi) x ranges without rivet heads under
    the bottom flange (bearings, connections)."""
    b.box((x0, -0.006, z0 + ct), (x1, 0.006, z1 - ct), S, axis="x")
    b.box((x0, -fw / 2, z0), (x1, fw / 2, z0 + ct), S, axis="x")
    b.box((x0, -fw / 2, z1 - ct), (x1, fw / 2, z1), S, axis="x")
    for sy in (-1, 1):
        b.prism(steel.angle(aw, ah, at), (x0, sy * 0.006, z0 + ct), (0, sy, 0), (0, 0, 1), (x1 - x0, 0, 0), S)
        b.prism(steel.angle(aw, ah, at), (x0, sy * 0.006, z1 - ct), (0, sy, 0), (0, 0, -1), (x1 - x0, 0, 0), S)
    zlo, zhi = z0 + ct + at, z1 - ct - at
    riv, rn = [], []
    covered = []
    for xs in stations:
        covered.append((xs - 0.02, xs + 0.11))
        for sy in (-1, 1):
            b.box((xs, sy * 0.006, z0 + ct + ah), (xs + 0.09, sy * (0.006 + at), z1 - ct - ah), S, axis="z")
            b.prism(steel.angle(0.09, 0.125, 0.010), (xs, sy * (0.006 + at), zlo), (1, 0, 0), (0, sy, 0), (0, 0, zhi - zlo), S)
            p = line((xs + 0.055, sy * (0.016 + at), zlo + 0.02), (xs + 0.055, sy * (0.016 + at), zhi - 0.02), 0.15)
            riv.append(p)
            rn.append(np.tile(V(0, sy, 0), (len(p), 1)))
    for xs in splices:                                     # web splice: a plate each side, two rows of rivets
        covered.append((xs - 0.17, xs + 0.17))
        for sy in (-1, 1):
            b.box((xs - 0.15, sy * 0.006, z0 + ct + ah + 0.02), (xs + 0.15, sy * 0.016, z1 - ct - ah - 0.02), S, axis="z")
            for dx in (-0.09, 0.09):
                p = line((xs + dx, sy * 0.016, z0 + ct + ah + 0.02), (xs + dx, sy * 0.016, z1 - ct - ah - 0.02), 0.13)
                riv.append(p)
                rn.append(np.tile(V(0, sy, 0), (len(p), 1)))
    for sy in (-1, 1):
        for zz in (z0 + ct + 0.57 * ah, z1 - ct - 0.57 * ah):                         # angles to web
            p = keep(line((x0, sy * (0.006 + at), zz), (x1, sy * (0.006 + at), zz), 0.15), 0, covered)
            riv.append(p)
            rn.append(np.tile(V(0, sy, 0), (len(p), 1)))
        yy = sy * (0.006 + 0.6 * aw)
        p = keep(line((x0, yy, z0), (x1, yy, z0), 0.15), 0, under_skip)                # heads under the bottom flange
        riv.append(p)
        rn.append(np.tile(V(0, 0, -1), (len(p), 1)))
        p = keep(line((x0, yy, z0 + ct + at), (x1, yy, z0 + ct + at), 0.15), 0, covered)
        riv.append(p)
        rn.append(np.tile(V(0, 0, 1), (len(p), 1)))
        p = keep(line((x0, yy, z1 - ct - at), (x1, yy, z1 - ct - at), 0.15), 0, covered)
        riv.append(p)
        rn.append(np.tile(V(0, 0, -1), (len(p), 1)))
        if top_heads:
            p = line((x0, yy, z1), (x1, yy, z1), 0.15)
            riv.append(p)
            rn.append(np.tile(V(0, 0, 1), (len(p), 1)))
    b.rivets(np.concatenate(riv), np.concatenate(rn), S)


def knee_brace(b, O, h, A, Bp, zf, sface, S="steel"):
    """Knee brace in the vertical plane through O along the horizontal unit vector h (pointing away from the
    column): two angles back to back from A to Bp, given as (distance from the column centre, height); a gusset
    on the column face (s = sface) and one under the girder flange at z = zf, each held by two connection angles."""
    O, h = np.asarray(O, dtype=np.float64), np.asarray(h, dtype=np.float64)
    nf = np.cross(h, Z)                                     # front of the plane: outlines are counter-clockwise seen from it
    pt = lambda s, z_: O + h * s + Z * z_
    A, Bp = np.asarray(A, dtype=np.float64), np.asarray(Bp, dtype=np.float64)
    d = (Bp - A) / np.linalg.norm(Bp - A)
    pp = np.array([-d[1], d[0]])
    d3, p3 = h * d[0] + Z * d[1], h * pp[0] + Z * pp[1]
    Q = A + 0.55 * d
    low = [(sface, A[1] - 0.33), (sface + 0.11, A[1] - 0.30), tuple(Q - 0.12 * pp), tuple(Q + 0.12 * pp), (sface, A[1] + 0.45)]
    Pq = Bp - 0.5 * d
    T1, T2 = (Bp[0] - 0.49, zf), (Bp[0] + 0.37, zf)
    upp = [tuple(Pq - 0.12 * pp), (T2[0], zf - 0.10), T2, T1, tuple(Pq + 0.12 * pp)]
    for outline in (low, upp):
        b.poly_plate([pt(s, z_) + nf * 0.006 for s, z_ in outline], 0.012, S, step=0.12)
    riv, rn = [], []
    # the brace: two angles back to back on the gussets
    start, Lm = A + 0.12 * d, float(np.linalg.norm(Bp - A)) - 0.22
    for sg in (-1, 1):
        heel = pt(*start) + p3 * 0.05 + nf * sg * 0.006
        b.prism(steel.angle(0.10, 0.075, 0.010), heel, -p3, nf * sg, d3 * Lm, S)
        for t in (0.07, 0.15, 0.23, Lm - 0.23, Lm - 0.15, Lm - 0.07):
            riv.append((pt(*start) + d3 * t + nf * sg * 0.016)[None, :])
            rn.append((nf * sg)[None, :])
    # connection angles: gusset to column face, gusset to girder flange
    zl0, zl1 = low[0][1] + 0.02, low[-1][1] - 0.02
    for sg in (-1, 1):
        b.prism(steel.angle(0.10, 0.10, 0.010), pt(sface, zl0) + nf * sg * 0.006, h, nf * sg, Z * (zl1 - zl0), S)
        p = line(pt(sface + 0.055, zl0) + nf * sg * 0.016, pt(sface + 0.055, zl1) + nf * sg * 0.016, 0.12)
        riv.append(p)
        rn.append(np.tile(nf * sg, (len(p), 1)))
        p = line(pt(sface + 0.010, zl0) + nf * sg * 0.066, pt(sface + 0.010, zl1) + nf * sg * 0.066, 0.12)
        riv.append(p)
        rn.append(np.tile(h, (len(p), 1)))
        b.prism(steel.angle(0.10, 0.10, 0.010), pt(T1[0], zf) + nf * sg * 0.006, -Z, nf * sg, h * (T2[0] - T1[0]), S)
        p = line(pt(T1[0], zf - 0.055) + nf * sg * 0.016, pt(T2[0], zf - 0.055) + nf * sg * 0.016, 0.12)
        riv.append(p)
        rn.append(np.tile(nf * sg, (len(p), 1)))
        p = line(pt(T1[0], zf - 0.010) + nf * sg * 0.066, pt(T2[0], zf - 0.010) + nf * sg * 0.066, 0.12)
        riv.append(p)
        rn.append(np.tile(-Z, (len(p), 1)))
    b.rivets(np.concatenate(riv), np.concatenate(rn), S)
    b.leaks += [tuple(pt(sface + 0.02, zl0 + 0.05)), tuple(pt(*low[2])), tuple(pt(*upp[0]))]


# ---------------------------------------------------------------------------------------------------------- bent

def build_bent(ctx, M):
    b = steel.Builder(step=0.13, seed=21)
    g = steel.Builder(step=0.13, seed=22)
    Lg = 10.1                                              # the game's cross girder: y -5.05 .. 5.05
    stations = [yy + Lg / 2 - 0.045 for yy in range(-4, 5)] + [0.03, Lg - 0.12]
    caps = [(Lg / 2 + s * ROW_Y - 0.33, Lg / 2 + s * ROW_Y + 0.33) for s in (-1, 1)]             # column caps
    caps += [(Lg / 2 - 3.76, Lg / 2 - 2.86), (Lg / 2 + 2.86, Lg / 2 + 3.76)]                    # knee-brace connections
    plate_girder(g, 0.0, Lg, COL_TOP, DECK, 0.46, 0.016, 0.15, 0.15, 0.016, stations, under_skip=caps,
                 splices=(Lg / 2 - 0.5, Lg / 2 + 0.5))
    b.merge(g, [[0, -1, 0, 0], [1, 0, 0, -Lg / 2], [0, 0, 1, 0], [0, 0, 0, 1]])   # girder along +Y in the plane x = 0
    for ys in (-1, 1):
        knee_brace(b, (0.0, ys * ROW_Y, 0.0), (0.0, -ys, 0.0), (0.30, 4.25), (1.35, 5.25), COL_TOP, 0.25)
    ob = b.finish("SM_El_Bent", M, ctx.col)
    weather(ctx, b, ob, "bent")
    ctx.asset(ob, collision="box", pivot="on the centre line at ground level; the girder runs along Y in the plane x = 0",
              expect_size=(0.46, 10.1, None), notes=(
        "Transverse plate girder z 5.30..6.50, y -5.05..5.05: 12 mm web, four 150 x 150 x 16 flange angles, 460 x 16 "
        "cover plates, stiffener angle pairs on fillers every metre, two web splices, rivets 36 mm at 150 mm. Two knee "
        "braces (double angles) from the column faces at z 4.25 to the bottom flange 1.35 m inboard, with gusset "
        "plates and connection angles. Sits on the caps of two SM_El_Column at (x, +-4.6). Gameplay collider: box "
        "x +-0.3, y +-5.05, z 5.30..6.50 (tag el-girder); the braces do not collide in the web game."))
    return ob


# ---------------------------------------------------------------------------------------------------------- span

def build_span(ctx, M):
    b = steel.Builder(step=0.16, seed=31)
    S = "steel"
    L = SPACING
    riv, rn = [], []

    def end_connection(yc, z0, z1, tw, n_piece):
        """Web tab and a pair of connection angles to the cross girder web at both ends of a longitudinal member."""
        for xe, hx in ((0.0, 1.0), (L, -1.0)):
            xa, xb = xe + hx * 0.006, xe + hx * 0.24
            b.box((min(xa, xb), yc - tw / 2, z0 - 0.02), (max(xa, xb), yc + tw / 2, z1 + 0.02), S, axis="z")
            for sg in (-1, 1):
                b.prism(steel.angle(0.10, 0.10, 0.010), (xa, yc + sg * tw / 2, z0), (hx, 0, 0), (0, sg, 0), (0, 0, z1 - z0), S)
                p = line((xa + hx * 0.055, yc + sg * (tw / 2 + 0.010), z0), (xa + hx * 0.055, yc + sg * (tw / 2 + 0.010), z1), (z1 - z0) / n_piece)
                riv.append(p)
                rn.append(np.tile(V(0, sg, 0), (len(p), 1)))
                p = line((xa + hx * 0.010, yc + sg * (tw / 2 + 0.06), z0), (xa + hx * 0.010, yc + sg * (tw / 2 + 0.06), z1), (z1 - z0) / n_piece)
                riv.append(p)
                rn.append(np.tile(V(hx, 0, 0), (len(p), 1)))

    # ---- longitudinal plate girders over the column rows
    st = [1.25 * k - 0.045 for k in range(1, 8)]
    for ys in (-1, 1):
        g = steel.Builder(step=0.16, seed=32 + ys)
        plate_girder(g, 0.24, L - 0.24, 5.50, DECK, 0.36, 0.014, 0.10, 0.15, 0.012, st, under_skip=[(0.79, 1.69), (L - 1.69, L - 0.79)])
        b.merge(g, [[1, 0, 0, 0], [0, 1, 0, ys * ROW_Y], [0, 0, 1, 0], [0, 0, 0, 1]])
        end_connection(ys * ROW_Y, 5.55, 6.30, 0.012, 6)
        for xe, hx in ((0.0, 1.0), (L, -1.0)):
            knee_brace(b, (xe, ys * ROW_Y, 0.0), (hx, 0.0, 0.0), (0.30, 4.40), (1.30, 5.45), 5.50, 0.25)
    # ---- a rolled stringer under every rail
    for yc in RAIL_Y:
        b.prism(steel.ibeam(0.58, 0.18, 0.022, 0.013), (0.24, yc, 5.92), Y, Z, X * (L - 0.48), S, pstep=0.2)
        end_connection(yc, 5.98, 6.30, 0.013, 3)
    # ---- fascia girders on brackets
    for ys in (-1, 1):
        b.box((0.0, ys * 5.388, 6.15), (L, ys * HALF, 6.72), S, axis="x")
        b.prism(steel.angle(0.09, 0.09, 0.010), (0.0, ys * 5.388, 6.72), (0, -ys, 0), (0, 0, -1), (L, 0, 0), S)
        b.prism(steel.angle(0.09, 0.09, 0.010), (0.0, ys * 5.388, 6.15), (0, -ys, 0), (0, 0, 1), (L, 0, 0), S)
        for zz in (6.20, 6.67):
            p = line((0.0, ys * HALF, zz), (L, ys * HALF, zz), 0.15)
            riv.append(p)
            rn.append(np.tile(V(0, ys, 0), (len(p), 1)))
        b.box((L / 2 - 0.16, ys * HALF, 6.24), (L / 2 + 0.16, ys * (HALF + 0.010), 6.63), S, axis="z")      # splice plate
        for dx in (-0.10, -0.04, 0.04, 0.10):
            p = line((L / 2 + dx, ys * (HALF + 0.010), 6.26), (L / 2 + dx, ys * (HALF + 0.010), 6.61), 0.115)
            riv.append(p)
            rn.append(np.tile(V(0, ys, 0), (len(p), 1)))
        for k in (1, 3, 5, 7):
            xs = 1.25 * k - 0.045
            ya, yb = ys * 4.70, ys * 5.388
            lo_a, lo_b = (xs, ya, 6.06), (xs, yb, 6.18)
            hi_a, hi_b = (xs, ya, 6.46), (xs, yb, 6.46)
            rows = [(lo_a, lo_b), (hi_a, hi_b)] if ys > 0 else [(lo_b, lo_a), (hi_b, hi_a)]
            b.plate_rows(rows, 0.010, S)
            for zz in (6.16, 6.27, 6.38):
                riv.append(V(xs - 0.010, ys * 4.725, zz)[None, :])
                rn.append(V(-1, 0, 0)[None, :])
                riv.append(V(xs + 0.010, ys * 4.725, zz)[None, :])
                rn.append(V(1, 0, 0)[None, :])
            b.prism(steel.angle(0.075, 0.075, 0.008), (xs, ys * 5.388, 6.25), (0, -ys, 0), (1, 0, 0), (0, 0, 0.21), S)
            p = line((xs + 0.045, ys * HALF, 6.24), (xs + 0.045, ys * HALF, 6.63), 0.13)
            riv.append(p)
            rn.append(np.tile(V(0, ys, 0), (len(p), 1)))
    # ---- mid-span cross frame: struts and a diagonal between each pair of longitudinal members
    xm = L / 2
    lines_y = [-ROW_Y] + RAIL_Y + [ROW_Y]
    for k in range(len(lines_y) - 1):
        ya, yb = lines_y[k] + 0.012, lines_y[k + 1] - 0.012
        for zz in (6.40, 6.04):
            b.prism(steel.angle(0.09, 0.09, 0.010), (xm, ya, zz), (0, 0, -1), (1, 0, 0), (0, yb - ya, 0), S)
        for yy in (ya, yb - 0.20):
            for z0, z1 in ((6.22, 6.42), (5.94, 6.14)):
                b.box((xm - 0.010, yy, z0), (xm, yy + 0.20, z1), S, axis="z")
                for dy, dz in ((0.05, 0.05), (0.15, 0.05), (0.10, 0.14)):
                    riv.append(V(xm - 0.010, yy + dy, z0 + dz)[None, :])
                    rn.append(V(-1, 0, 0)[None, :])
        up = (k % 2 == 0)
        p0 = V(xm - 0.010, ya + 0.08, 6.00 if up else 6.36)
        p1 = V(xm - 0.010, yb - 0.08, 6.36 if up else 6.00)
        dd = (p1 - p0) / np.linalg.norm(p1 - p0)
        b.prism(steel.angle(0.075, 0.075, 0.008), p0, np.cross(dd, X), -X, p1 - p0, S)
    # ---- lateral bracing: six diagonals per span in the plane z = 6.28, zigzagging between the lines
    bays = [-ROW_Y + 0.2, RAIL_Y[0], RAIL_Y[1], RAIL_Y[2], RAIL_Y[3], ROW_Y - 0.2]
    for hi, (xa, xb) in enumerate(((0.38, xm - 0.14), (xm + 0.14, L - 0.38))):
        for k in (0, 2, 4):
            flip = (hi + k // 2) % 2 == 0
            y0, y1 = (bays[k], bays[k + 1]) if flip else (bays[k + 1], bays[k])
            s0 = 0.10 * (1 if y1 > y0 else -1)
            p0, p1 = V(xa, y0 + s0, 6.28), V(xb, y1 - s0, 6.28)
            dd = (p1 - p0) / np.linalg.norm(p1 - p0)
            b.prism(steel.angle(0.09, 0.09, 0.010), p0 + dd * 0.05, np.cross(Z, dd), -Z, p1 - p0 - dd * 0.10, S)
            for pe, sgn in ((p0, 1), (p1, -1)):
                b.box((pe[0] - 0.16, pe[1] - 0.13, 6.28), (pe[0] + 0.16, pe[1] + 0.13, 6.29), S, axis="x")
                for t in (0.10, 0.19):
                    q = pe + dd * sgn * t + np.cross(Z, dd) * 0.045
                    riv.append(V(q[0], q[1], 6.27)[None, :])
                    rn.append(V(0, 0, -1)[None, :])
    b.rivets(np.concatenate(riv), np.concatenate(rn), S)
    ob = b.finish("SM_El_GirderSpan_10m", M, ctx.col)
    weather(ctx, b, ob, "span")
    ctx.asset(ob, collision="complex", pivot="west bent on the centre line at ground level; runs +X to the next bent",
              expect_size=(SPACING, 2 * HALF + 0.02, None), notes=(
        "Longitudinal steel of one 10 m bay, between two SM_El_Bent: plate girders over the column rows (y +-4.6, "
        "z 5.50..6.50) with stiffeners every 1.25 m, a rolled 0.58 m stringer under each rail (y +-1.3825, +-2.8175), "
        "end connection angles to the cross girder webs, four longitudinal knee braces to the column flanges, fascia "
        "girders (y +-5.4, z 6.15..6.72) on four brackets a side, the mid-span cross frame and six lateral bracing "
        "diagonals at z 6.28. Open between the members: the sky shows through. Gameplay colliders: boxes 0.40 wide over "
        "each girder line, z 5.50..6.50 (tag el-girder)."))
    return ob


# ---------------------------------------------------------------------------------------------------------- deck

def build_deck(ctx, M):
    from mathutils import Matrix
    b = steel.Builder(step=0.25, seed=41)
    S, T, RL = "steel", "tie", "rail"
    L = SPACING
    rng = ctx.rng("deck")
    pitch = L / N_TIES
    tie_x = (np.arange(N_TIES) + 0.5) * pitch
    board = lambda k: ((k % 5) + 0.5) / 5.0                 # TS_Wood_ScanTie: five boards across the tile
    nb = 0

    def timber(size, centre, grain, slot=T, bevel=0.007, yaw=0.0, dens=0.3):
        nonlocal nb
        ob = geo.box(size, bevel=bevel, segments=2, name="timber", base=False)
        geo.densify(ob, dens, 5)
        geo.transform(ob, loc=centre, rot=(0, 0, yaw))
        nb += 1
        b.absorb(ob, slot, vdir=grain, fdir=Z, uv_org=centre, uv_off=(board(nb * 2 + int(rng.integers(0, 5))), rng.uniform(0, 1)))

    # ---- ties: 0.22 x 0.18 x 2.70, never quite square or level
    for c in TRACKS:
        for xt in tie_x:
            ln = 2.70 + rng.uniform(-0.03, 0.03)
            timber((0.22, ln, 0.18), (xt + rng.uniform(-0.012, 0.012), c + rng.uniform(-0.02, 0.02), DECK + 0.09), Y,
                   yaw=rng.uniform(-0.5, 0.5), bevel=0.009)
    # ---- running rails on tie plates with spikes
    for yr in RAIL_Y:
        b.prism(steel.rail(0.140), (0.0, yr, TIE_TOP + 0.010), Y, Z, X * L, RL, step=0.5, pstep=0.06, caps=False, uv_off=(rng.uniform(0, 1), 0.3))
        for xt in tie_x:
            b.box((xt - 0.09, yr - 0.125, TIE_TOP), (xt + 0.09, yr + 0.125, TIE_TOP + 0.010), RL, step=0.3)
            for dx, dy in ((-0.05, -0.083), (0.05, 0.083), (0.05, -0.083), (-0.05, 0.083)):
                b.box((xt + dx - 0.016, yr + dy - 0.016, TIE_TOP + 0.010), (xt + dx + 0.016, yr + dy + 0.016, TIE_TOP + 0.036), RL, step=0.3)
    # joint bars on one rail of each track, mid-module
    for yr in (RAIL_Y[0], RAIL_Y[3]):
        for sg in (-1, 1):
            b.box((L / 2 - 0.30, yr + sg * 0.009, TIE_TOP + 0.047), (L / 2 + 0.30, yr + sg * 0.030, TIE_TOP + 0.112), RL, step=0.3)
        heads = geo.instances(geo.hex_bolt(0.022, name="jb"), [Matrix.Translation((L / 2 + dx, yr + 0.030, TIE_TOP + 0.08)) @ Matrix.Rotation(-math.pi / 2, 4, "X")
                                                             for dx in (-0.21, -0.07, 0.07, 0.21)], "jointbolts")
        b.absorb(heads, RL)
    # ---- guard timbers, third rail on insulators, cover board on brackets
    bolt_m = []
    for c in TRACKS:
        so = 1.0 if c > 0 else -1.0                         # the third rail is on the outer side of each track
        for (yc, w, hgt) in ((c - so * 1.20, 0.15, 0.13), (c + so * 0.945, 0.13, 0.10)):
            for xa, xb in ((0.004, 6.108), (6.116, L - 0.004)):
                timber((xb - xa, w, hgt), ((xa + xb) / 2, yc, TIE_TOP + hgt / 2), X, bevel=0.006, dens=0.35)
            bolt_m += [Matrix.Translation((xt, yc, TIE_TOP + hgt)) for xt in tie_x[1::3]]
        y3 = c + so * 1.12
        b.prism(steel.rail(0.090, 0.10, 0.066, 0.022), (0.0, y3, TIE_TOP + 0.035), Y, Z, X * L, RL, step=0.5, pstep=0.06, caps=False)
        ins = geo.instances(geo.cylinder(0.046, 0.035, 14, bevel=0.006, name="ins"), [Matrix.Translation((xt, y3, TIE_TOP)) for xt in tie_x[0::6]], "insulators")
        b.absorb(ins, RL)
        for xa, xb in ((0.003, 4.997), (5.003, L - 0.003)):
            timber((xb - xa, 0.26, 0.03), ((xa + xb) / 2, y3, TIE_TOP + 0.185), X, bevel=0.004, dens=0.35)
        for xt in tie_x[3::6]:
            yo = y3 + so * 0.105
            b.box((xt - 0.025, yo - 0.004, TIE_TOP), (xt + 0.025, yo + 0.004, TIE_TOP + 0.17), S, step=0.3)
            b.box((xt - 0.025, y3 - 0.12, TIE_TOP + 0.162), (xt + 0.025, y3 + 0.12, TIE_TOP + 0.170), S, step=0.3)
    bolts = geo.instances(geo.hex_bolt(0.020, name="gb"), bolt_m, "guardbolts")
    b.absorb(bolts, RL)
    # ---- side walkways: bearers, tread plate, toe board, pipe railing
    for ys in (-1, 1):
        for k in range(8):
            xb = 0.625 + 1.25 * k
            b.prism(steel.channel(0.132, 0.05, 0.008, 0.006), (xb - 0.02, ys * 3.50, DECK), X, Z, (0, ys * 1.885, 0), S)
            x0 = 1.25 * k
            b.box((x0 + 0.003, ys * 3.90, DECK + 0.132), (x0 + 1.247, ys * 5.30, DECK + 0.140), "tread", step=0.2)
        b.box((0.0, ys * 5.31, DECK + 0.14), (L, ys * 5.316, DECK + 0.29), S, axis="x")
        yr = ys * 5.35
        for zz in (7.25, 7.75):
            b.absorb(geo.pipe([(0.0, yr, zz), (L, yr, zz)], 0.0242, 10, cap=False, name="handrail"), S)
        for k in range(4):
            xp = 1.25 + 2.5 * k
            b.absorb(geo.pipe([(xp, yr, DECK + 0.14), (xp, yr, 7.75)], 0.0242, 10, name="post"), S)
            b.box((xp - 0.06, yr - 0.045, DECK + 0.14), (xp + 0.06, yr + 0.045, DECK + 0.150), S, step=0.3)
            for zz in (7.25, 7.75):
                sp = geo.sphere(0.036, 10, 6, "fitting")
                geo.transform(sp, loc=(xp, yr, zz))
                b.absorb(sp, S)
    # ---- walkway between the tracks: channel bearers on the inner stringers, five planks
    for i in (1, 4, 7, 10, 13, 16):
        xb = (i + 1) * pitch
        b.prism(steel.channel(0.08, 0.04, 0.007, 0.005), (xb - 0.02, -1.37, DECK), X, Z, (0, 2.74, 0), S)
    for j in range(5):
        yc = -0.486 + j * 0.243
        xj = (8 if j % 2 == 0 else 11) * pitch
        for xa, xb in ((0.004, xj - 0.004), (xj + 0.004, L - 0.004)):
            timber((xb - xa, 0.225, 0.06), ((xa + xb) / 2, yc, DECK + 0.11), X, bevel=0.005, dens=0.35)
    # ---- cable trough (north) and conduits (south) on the bearers beside the walkway
    zt = DECK + 0.132
    u_prof = [(0, 0), (0.30, 0), (0.30, 0.16), (0.27, 0.16), (0.27, 0.035), (0.03, 0.035), (0.03, 0.16), (0, 0.16)]
    b.prism(u_prof, (0.0, 3.53, zt), Y, Z, X * L, "trough", step=0.5, pstep=0.1, caps=False)
    for k in range(10):
        lid = geo.box((0.985, 0.31, 0.04), bevel=0.006, segments=1, name="lid", base=False)
        geo.densify(lid, 0.2, 4)
        geo.transform(lid, loc=(0.5 + k, 3.68 + rng.uniform(-0.012, 0.012), zt + 0.18 + (0.006 if k == 6 else 0.0)),
                      rot=(0, 0.6 if k == 6 else 0.0, rng.uniform(-0.8, 0.8)))
        b.absorb(lid, "trough")
    for yc in (-3.58, -3.66, -3.74):
        b.absorb(geo.pipe([(0.0, yc, zt + 0.03), (L, yc, zt + 0.03)], 0.03, 10, cap=False, name="conduit"), S)
    ob = b.finish("SM_El_Deck_10m", M, ctx.col)
    # ---- wear
    W = b.loops(ob, ao=0.10, rays=6)
    P, N = W.P, W.N
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    rw = ctx.rng("wear", "deck")
    wa, wb, wc = Waves(rw, 0.5), Waves(rw, 2.2), Waves(rw, 0.15)
    a, bb, c_ = wa.u(x, y + 0.4 * z), wb.u(x, y), wc.u(x + z, y)
    up, down = np.clip(N[:, 2], 0, 1), np.clip(-N[:, 2], 0, 1)
    ao = W.ao
    d_rail = np.min(np.abs(y[:, None] - np.array(RAIL_Y)[None, :]), axis=1)
    R = 0.06 + 0.8 * ao * (0.6 + 0.5 * a) + 0.25 * W.concave + 0.2 * down
    G = W.convex * sstep(0.3, 0.72, 0.6 * a + 0.4 * c_) * (0.5 + 0.5 * bb)
    G = np.maximum(G, 0.9 * up * sstep(0.2, 0.55, ao) * (0.5 + 0.5 * a))
    B = np.zeros(len(P))
    A = up * (0.2 + 0.4 * bb) * (1 - 0.6 * ao)
    tie = W.is_slot(T)
    Rt = 0.22 + 0.55 * np.exp(-d_rail / 0.22) * (0.6 + 0.5 * a) + 0.4 * ao + 0.25 * down     # brake dust and grease by the rails
    Gt = up * (0.25 + 0.6 * bb * c_) * (1 - 0.7 * np.exp(-d_rail / 0.25)) + 0.3 * W.convex * a
    walk = tie & (np.abs(y) < 0.62) & (z > DECK + 0.1)
    Gt = np.where(walk, 0.35 + 0.5 * np.exp(-(y / 0.3) ** 2) * (0.6 + 0.5 * a), Gt)          # boots bleach the planks
    Bt = up * np.exp(-d_rail / 0.10) * (0.5 + 0.5 * c_) * 0.9                                 # rust off the tie plates
    R, G, B, A = np.where(tie, Rt, R), np.where(tie, Gt, G), np.where(tie, Bt, B), np.where(tie, 0.15 * up * bb, A)
    rl = W.is_slot(RL)
    top = (up > 0.7) & (z > RAIL_TOP - 0.004)
    top3 = (up > 0.7) & (np.abs(z - (TIE_TOP + 0.125)) < 0.004)
    R = np.where(rl, 0.35 + 0.4 * ao + 0.2 * a, R)
    G = np.where(rl, np.where(top, 1.0, np.where(top3, 0.85, 0.15 * W.convex)), G)
    A = np.where(rl, 0.0, A)
    tr = W.is_slot("tread")
    G = np.where(tr, 0.2 + 0.7 * np.exp(-((np.abs(y) - 4.6) / 0.28) ** 2) * (0.6 + 0.5 * a), G)
    R = np.where(tr, 0.15 + 0.6 * sstep(0.45, 0.68, np.abs(np.abs(y) - 4.6)) * (0.5 + 0.6 * bb), R)
    cn = W.is_slot("trough")
    R = np.where(cn, 0.2 + 0.5 * ao + 0.3 * a, R)
    G = np.where(cn, W.convex * (0.4 + 0.5 * c_), G)
    geo.set_wear(ob, np.clip(np.stack([R, G, B, A], axis=1), 0, 1), per="corner")
    ctx.asset(ob, collision="box", pivot="west bent on the centre line at ground level; runs +X",
              expect_size=(SPACING, None, None), notes=(
        "Open deck of one 10 m bay, everything above z = 6.50: 18 ties per track (0.22 x 0.18 x 2.70 at 0.556 m, sky "
        "between them), four running rails (140 mm, gauge 1.435, top 6.83) on tie plates with spikes, joint bars, guard "
        "timbers, two third rails on insulators under cover boards (top 6.88), tread-plate walkways y +-3.9..5.3 on "
        "channel bearers with toe board and two-rail pipe railing (rails at 7.25 and 7.75, posts every 2.5 m), a plank "
        "walkway between the tracks, a covered cable trough on the north side and three conduits on the south. Tiles "
        "end to end. Gameplay collider: one box z 6.50..6.90, y +-5.4 (tag el-deck). The ties are separate boxes on "
        "purpose: with ray-traced shadows they stripe the avenue."),
        slots={"MI_Wood_ScanTie": {"note": "creosoted timber: tint the scan (see tint); G bleaches, R is brake dust and grease"},
               "MI_Steel_ScanRust": {"note": "G = 1 is the polished running surface: bare steel, metallic 1, roughness 0.25"}})
    return ob


# ---------------------------------------------------------------------------------------------------------- lamp

def build_lamp(ctx, M):
    """Sodium fixture hung from the stringers: canopy, conduit stem, enamelled reflector, glass bowl."""
    b = steel.Builder(step=0.2, seed=51)
    S = "steel"
    b.absorb(geo.revolve([(0, -0.06), (0.024, -0.06), (0.052, -0.044), (0.052, -0.004), (0.046, 0.0), (0, 0.0)], 20, name="canopy"), S)
    stem = geo.cylinder(0.0135, 0.20, 12, name="stem")
    geo.transform(stem, loc=(0, 0, -0.258))
    b.absorb(stem, S)
    outer = [(0.300, -0.440), (0.272, -0.402), (0.205, -0.333), (0.125, -0.288), (0.090, -0.262), (0.052, -0.250), (0.044, -0.216), (0, -0.216)]
    b.absorb(geo.revolve(outer, 32, name="shade"), S)
    inner = [(0, -0.224), (0.040, -0.256), (0.087, -0.268), (0.122, -0.293), (0.202, -0.338), (0.269, -0.406), (0.297, -0.440)]
    b.absorb(geo.revolve(inner, 32, name="reflector"), "white")
    rim = geo.torus(0.2985, 0.006, 32, 8, "rim")
    geo.transform(rim, loc=(0, 0, -0.440))
    b.absorb(rim, S)
    b.absorb(geo.revolve([(0, -0.476), (0.10, -0.468), (0.17, -0.448), (0.20, -0.424), (0.20, -0.418), (0, -0.418)], 28, name="lens"), "glow")
    ring = geo.torus(0.201, 0.008, 28, 8, "ring")
    geo.transform(ring, loc=(0, 0, -0.420))
    b.absorb(ring, S)
    for k in range(3):                                   # three hangers hold the bowl ring under the reflector
        an = math.radians(120 * k + 20)
        b.absorb(geo.pipe([(0.201 * math.cos(an), 0.201 * math.sin(an), -0.420), (0.10 * math.cos(an), 0.10 * math.sin(an), -0.285)], 0.004, 6, name="hanger"), S)
    ob = b.finish("SM_El_Lamp", M, ctx.col, smooth=50)
    W = b.loops(ob, ao=0.05, rays=6)
    up = np.clip(W.N[:, 2], 0, 1)
    rw = ctx.rng("wear", "lamp")
    n = Waves(rw, 0.2).u(W.P[:, 0] * 3, W.P[:, 1] * 3 + W.P[:, 2])
    R = 0.15 + 0.7 * W.ao + 0.3 * n * (1 - up)
    G = W.convex * (0.3 + 0.6 * n) + 0.3 * up * n
    A = up * (0.5 + 0.4 * n)
    geo.set_wear(ob, np.clip(np.stack([R, G, 0 * R, A], axis=1), 0, 1), per="corner")
    ctx.asset(ob, collision="box", pivot="the mounting point at the top of the canopy; the fixture hangs down -Z",
              expect_size=(0.61, 0.61, 0.476), notes=(
        "El lamp: canopy and conduit stem, enamelled reflector 0.60 m across (green outside, white inside), glass bowl "
        "with a ring on three hangers. Hang at (bay x + 5, y +-2.1 alternating, z 6.02): the bowl is then at z 5.54..5.60, "
        "where the level data puts the lamp hints (kind el, #FFB45E). The slot MI_Glass_SodiumLens is the emitter "
        "(ART_BIBLE 2.7); no textures."),
        slots={"MI_Glass_SodiumLens": {"emissive": "#FFB45E high-pressure sodium, level per ART_BIBLE 2.7", "textures": None}})
    return ob


# --------------------------------------------------------------------------------------------------------- build

def build(ctx):
    M = materials(ctx)
    A = {}
    for name, fn in (("column", build_column), ("bent", build_bent), ("span", build_span), ("deck", build_deck), ("lamp", build_lamp)):
        A[name] = fn(ctx, M)
        ctx.log("%-7s %7d tris" % (name, geo.stats(A[name])["triangles"]))
    ctx.A, ctx.M = A, M
    ctx.placed = layout(ctx, A, range(0, 4), origin=True)
    return [a["ob"] for a in ctx.assets.values()]


def layout(ctx, A, bents, x_off=0.0, origin=False, skip=()):
    """Bents at x_off + k * 10 for k in `bents`, with a bay (span, deck, lamp) after each but the last. The first
    use of each asset is the asset itself (origin=True keeps it at its pivot position when that is where it
    belongs); the rest are linked duplicates."""
    col = scene.collection("ElLayout", ctx.col)
    used = set()
    out = []

    def put(key, loc):
        src = A[key]
        if origin and key not in used:
            used.add(key)
            ob = src
        else:
            ob = scene.duplicate(src, linked=True, col=col)
        scene.place(ob, loc, 0.0)
        ob["mi_placed"] = True
        out.append(ob)
        return ob

    ks = list(bents)
    for i, k in enumerate(ks):
        xb = x_off + k * SPACING
        if k not in skip:                                  # skip: bents that another call already placed
            put("bent", (xb, 0, 0))
            for ys in (-1, 1):
                put("column", (xb, ys * ROW_Y, 0))
        if i < len(ks) - 1:
            put("span", (xb, 0, 0))
            put("deck", (xb, 0, 0))
            put("lamp", (xb + SPACING / 2, 2.1 if k % 2 == 0 else -2.1, LAMP_Z))
    return out


# ------------------------------------------------------------------------------------------------------- previews

def on_preview(ctx, objs):
    """Look-dev: the El over the street family. Three bays stand over 30 m of street in front of the camera (more
    bays and street, all instances, carry the view to the horizon)."""
    from assets import street
    a = ctx.args
    P = paths.previews
    only = set(a.only or [])
    want = lambda n: not only or n in only
    sub = type(ctx)("street", a)
    street.build(sub)
    dress = street._dress(sub)
    x_off = 5.0
    for ob in ctx.placed:
        ob.location.x += x_off
    more = layout(ctx, ctx.A, range(-3, 1), x_off, skip=(0,)) + layout(ctx, ctx.A, range(3, 9), x_off, skip=(3,))
    render.setup(samples=a.samples)
    kerb = street.KERB_H
    if want("el_wire"):
        clay = mat.flat("Clay", (0.55, 0.55, 0.55), 0.55)
        vl = bpy.context.view_layer
        vl.material_override = clay
        render.rig_day(sun_azimuth=215.0, stops=-0.9)
        render.cam_look((x_off + 6.3, -8.3, 4.2), (x_off + 0.6, -4.2, 5.35), lens=40, name="Cam_Wire")
        _p, sec = render.render_jpeg(os.path.join(P, "el_wire.jpg"), max(24, a.samples // 2))
        vl.material_override = None
        ctx.log("preview el_wire.jpg %.0fs" % sec)
    # the design sun: 4:15 PM, bearing 260 (10 degrees south of due west), so the ties stripe the roadway
    if want("el_day_hero"):
        render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING, stops=0.7)
        render.cam_look((-3.0, -8.7, kerb + 1.65), (40.0, -2.2, 3.4), lens=24, name="Cam_ElHero")
        _p, sec = render.render_jpeg(os.path.join(P, "el_day_hero.jpg"), a.samples)
        ctx.log("preview el_day_hero.jpg %.0fs" % sec)
    if want("el_day_column"):
        render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING, stops=0.9)
        render.cam_look((x_off - 2.9, -7.3, 1.62), (x_off + 0.05, -4.6, 1.45), lens=30, name="Cam_ElColumn")
        _p, sec = render.render_jpeg(os.path.join(P, "el_day_column.jpg"), a.samples)
        ctx.log("preview el_day_column.jpg %.0fs" % sec)
    if want("el_day_under"):
        render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING, stops=1.6)
        render.cam_look((x_off + 3.2, -1.6, 1.7), (x_off + 10.6, 1.9, 6.3), lens=20, name="Cam_ElUnder")
        _p, sec = render.render_jpeg(os.path.join(P, "el_day_under.jpg"), a.samples)
        ctx.log("preview el_day_under.jpg %.0fs" % sec)
    del dress, more
