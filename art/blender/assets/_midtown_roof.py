"""Midtown kit, part 1: materials, helpers and the roofs (midtown.md 2.1, 5.3, 9.1, 10 and 14.2).

Built with the Block's facade helpers (assets/facade.py: B, bx, rod, sheet, weather), imported, never changed, so the
Block's outputs stay byte for byte. Surfaces are catalogued tiling scans (tinted where the slot name says so, SLOT_META)
and a few flat slots; no unique bakes, so a roof prop costs no texture memory of its own.

Thin geometry: every member within reach of the path is at least 6 cm across (midtown.md 15, READY.md R3 flicker at
render scale 0.50): stand braces, rails, ladder rungs and conduits included. Tie rods appear nowhere.

Pivots. Props and rooms: centre of the footprint on the roof surface, forward (the door) +X unless the docstring says
otherwise. Parapets: the wall-module convention (bottom-left corner of the outer face, running +X, outer face toward -Y,
z = 0 on the roof surface). Stairs and bridges: see each docstring. The art has no collision: the level data decides.
"""
import math

import numpy as np

from assets import facade as fc
from assets.facade import B, bx, rod, sheet
from mi import geo, mat, paths, steel

X, Y, Z = np.eye(3)
SOOT = (0.030, 0.028, 0.026)
SLOT_META = {}
MEMBER_MIN = 0.06                      # metres: the thinnest member near the path


def _tile_of(set_name):
    try:
        return mat.scan_tile(set_name)
    except Exception:
        return (2.0, 2.0)


def S(ctx, set_name, slot=None, tint=None, note=None, **kw):
    """Material on a catalogued tiling scan."""
    slot = slot or "MI_" + set_name[3:]
    try:
        m = ctx.scan_set(set_name, slot=slot, tint=tint, **kw)
    except KeyError:                                   # a baked set on disk (set.json), not a catalogued scan
        kw.pop("blend", None)
        m = mat.from_texture_set(paths.texture_set(set_name), name=slot, tile_m=_tile_of(set_name), tint=tint, **kw)
        m["mi_tile_m"] = _tile_of(set_name)
        if set_name not in ctx.sets:
            ctx.sets.append(set_name)
    if slot != "MI_" + set_name[3:] or tint is not None:
        SLOT_META[slot] = {"set": set_name, "workflow": "tiling"}
        if tint is not None:
            SLOT_META[slot]["tint"] = [round(float(c), 3) for c in tint]
        if note:
            SLOT_META[slot]["note"] = note
    return m


def F(name, col, rough=0.6, metal=0.0, emit=None, strength=0.0, note=None):
    """A flat slot (constant parameters in the Unreal master material, no texture)."""
    m = mat.flat(name, col, rough, metal)
    if emit is not None:
        p = mat.principled(m)
        p.inputs["Emission Color"].default_value = (*emit, 1.0)
        p.inputs["Emission Strength"].default_value = strength
    SLOT_META[name] = {"workflow": "flat" if emit is None else "emissive", "color": [round(float(c), 3) for c in col],
                       "roughness": rough, "metallic": metal}
    if emit is not None:
        SLOT_META[name]["emissive"] = [round(float(c), 3) for c in emit]
    if note:
        SLOT_META[name]["note"] = note
    return m


def materials(ctx):
    rust = dict(blend="TS_Steel_ScanRust", leak_color=(0.24, 0.10, 0.035), leak_rough=0.1, dirt_color=SOOT, alpha="splash")
    M = {}
    M["black"] = S(ctx, "TS_Steel_ScanPaintGrey", "MI_Steel_PaintBlack", tint=(0.07, 0.07, 0.075), blend_start=0.40, **rust)
    M["grey"] = S(ctx, "TS_Steel_ScanPaintGrey", blend_start=0.45, macro=0.12, **rust)
    M["hvac"] = S(ctx, "TS_Steel_ScanPaintWhite", "MI_Steel_PaintBeige", tint=(0.74, 0.71, 0.63), blend_start=0.6, **rust,
                  note="factory beige of rooftop units: the white paint scan tinted")
    M["galv"] = S(ctx, "TS_Galvanised_Aged", alpha="splash", dirt_color=SOOT)
    M["plate"] = S(ctx, "TS_Plate_ScanDiamond", alpha="splash", dirt_color=SOOT)
    M["grate"] = S(ctx, "TS_Plate_ScanDurbar", alpha="splash", dirt_color=SOOT,
                   note="the gantry and catwalk decks: grating read as a texture on plates, never open mesh (midtown.md 14.2)")
    M["brickBuff"] = S(ctx, "TS_Brick_ScanBuff", alpha="splash", dirt_color=SOOT)
    M["brickRed"] = S(ctx, "TS_Brick_ScanRed", alpha="splash", dirt_color=SOOT)
    M["stone"] = S(ctx, "TS_Concrete_ScanWeathered", alpha="splash", dirt_color=SOOT, macro=0.12)
    M["conc"] = S(ctx, "TS_Concrete_ScanStained", alpha="splash", dirt_color=SOOT, macro=0.12)
    M["roof"] = S(ctx, "TS_Roof_ScanBitumen", alpha="splash", dirt_color=(0.10, 0.09, 0.08), macro=0.2)
    M["roofGravel"] = S(ctx, "TS_Roof_ScanGravel", alpha="splash", dirt_color=(0.10, 0.09, 0.08), macro=0.2)
    M["timber"] = S(ctx, "TS_Wood_ScanPlankDark", "MI_Timber_TankStave", tint=(0.80, 0.72, 0.62), alpha="splash", dirt_color=SOOT,
                    macro=0.15, note="water tank staves: the dark plank scan, warmer (the design's TS_Timber_TankStave, as a tint: no new set)")
    M["boards"] = S(ctx, "TS_Wood_ScanPlankNew", alpha="splash", dirt_color=SOOT, macro=0.15)
    M["fabricNet"] = S(ctx, "TS_Fabric_ScanCanvas", "MI_Fabric_ScaffoldNet", tint=(0.05, 0.16, 0.22), alpha="splash", dirt_color=SOOT,
                       note="scaffold netting, OPAQUE woven (the design's TS_Scaffold_Netting as a tint of the canvas scan: no alpha, "
                            "no new set)")
    M["rubber"] = S(ctx, "TS_Rubber_Aged", alpha="splash")
    M["glass"] = mat.make("MI_Glass_Wired", "glass", Film=0.25)
    SLOT_META["MI_Glass_Wired"] = {"workflow": "glass", "note": "M_MI_Glass, opaque (midtown.md 15: no translucency); skylights"}
    M["grille"] = F("MI_Grille_Dark", (0.035, 0.035, 0.038), 0.55, 0.6, note="fan guards and louvre gaps: dark, slightly metallic")
    M["interior"] = F("MI_Interior_Dark", (0.022, 0.021, 0.02), 0.9, note="the stairwell's dark below the first steps")
    M["sodium"] = F("MI_Lamp_Sodium", (0.9, 0.8, 0.6), 0.2, emit=(1.0, 0.55, 0.18), strength=0.0,
                    note="roof work light lens: 2200 K; emissive 1 lit at night (the light itself is a placed spot, midtown.md 11.1)")
    M["led"] = F("MI_Lamp_LED", (0.9, 0.9, 0.9), 0.2, emit=(0.85, 0.9, 1.0), strength=0.0, note="LED flood lens, 4000 K")
    M["signFace"] = F("M_Sign_MT_Face", (0.35, 0.35, 0.35), 0.4,
                      note="printed face on 0..1 UVs: the MI of a placed carrier reads Sign_MT_Atlas1 (BC, ORM, E) and maps 0..1 to "
                           "its cell (art/out/midtown/signs_midtown.json)")
    SLOT_META["M_Sign_MT_Face"] = {"workflow": "sign_atlas", "sets": ["Sign_MT_Atlas1"], "uv": "0..1 over the face",
                                   "note": SLOT_META["M_Sign_MT_Face"]["note"]}
    M["signScreen"] = F("M_MI_Screen", (0.012, 0.012, 0.014), 0.6,
                        note="the one screen master (midtown.md 12.3): opaque, black base, roughness 0.6, emissive = a cell of "
                             "MT_Screens_A/B x nits, crossfade of two cells, LED mask 8 to 20 m; UV 0..1 over the screen")
    SLOT_META["M_MI_Screen"] = {"workflow": "screen_atlas", "sets": ["MT_Screens_A", "MT_Screens_B", "MT_LEDMask"],
                                "uv": "0..1 over the screen", "note": SLOT_META["M_MI_Screen"]["note"]}
    M["signTicker"] = F("M_MT_Ticker", (0.012, 0.012, 0.014), 0.6,
                        note="ticker band: M_MI_Screen's ticker variant reading MT_Ticker (u pans 0.35 m/s, wraps); UV 0..1 over the band")
    SLOT_META["M_MT_Ticker"] = {"workflow": "screen_strip", "sets": ["MT_Ticker"], "uv": "0..1 over the 4 m module, u continues",
                                "note": SLOT_META["M_MT_Ticker"]["note"]}
    return M


# ================================================================================================= helpers

def bar(b, p0, p1, w, t, slot, up=Z, **kw):
    """Rectangular bar from p0 to p1 (facade.bar), `up` swapped when the bar runs along it."""
    d = np.asarray(p1, float) - np.asarray(p0, float)
    if abs(float(np.dot(d / np.linalg.norm(d), up))) > 0.98:
        up = Y if abs(d[1]) < abs(d[0]) or abs(d[2]) > 0 else X
    return fc.bar(b, p0, p1, w, t, slot, up=up, **kw)


def tube(b, p0, p1, slot, r=0.03, n=10):
    """Round tube or pipe, r at least MEMBER_MIN / 2."""
    return rod(b, p0, p1, max(r, MEMBER_MIN / 2), slot, n=n)


def col_ibeam(b, x, y, z0, z1, slot="black", d=0.20, bf=0.18, turn=False):
    """Vertical I-section column centred on (x, y)."""
    u, v = (X, Y) if not turn else (Y, X)
    o = np.array((x, y, z0)) - v * d / 2
    return b.prism(steel.ibeam(d, bf, 0.012, 0.008), o, u, v, (0, 0, z1 - z0), slot, pstep=9.0)


def beam_x(b, x0, x1, y, z, slot="black", d=0.20, bf=0.14):
    """I beam along X, its bottom at z, centred on y."""
    return b.prism(steel.ibeam(d, bf, 0.011, 0.007), (x0, y, z), Y, Z, (x1 - x0, 0, 0), slot, pstep=9.0)


def beam_y(b, y0, y1, x, z, slot="black", d=0.20, bf=0.14):
    return b.prism(steel.ibeam(d, bf, 0.011, 0.007), (x, y0, z), -X, Z, (0, y1 - y0, 0), slot, pstep=9.0)


def angle_brace(b, p0, p1, slot="black", w=0.075):
    """Angle-section diagonal brace (legs w, 8 mm), the heel along the line p0 -> p1."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax = steel.unit(p1 - p0)
    u = steel.unit(np.cross(Z if abs(ax[2]) < 0.9 else X, ax))
    v = np.cross(ax, u)
    return b.prism(steel.angle(w, w, 0.008), p0 - (u + v) * w * 0.3, u, v, p1 - p0, slot, pstep=9.0)


def rail_run(b, p0, p1, slot="galv", h=1.10, post=1.5, mid=True, toe=True, r=0.03):
    """A guard rail along p0 -> p1 on its floor: posts every `post` m, top rail at h, mid rail, toe board."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = float(np.linalg.norm(p1 - p0))
    n = max(1, int(math.ceil(L / post)))
    for i in range(n + 1):
        q = p0 + (p1 - p0) * i / n
        tube(b, q, q + (0, 0, h), slot, r)
    tube(b, p0 + (0, 0, h), p1 + (0, 0, h), slot, r)
    if mid:
        tube(b, p0 + (0, 0, h * 0.5), p1 + (0, 0, h * 0.5), slot, r)
    if toe:
        d = steel.unit(p1 - p0)
        nrm = steel.unit(np.cross(Z, d))
        a, c = p0 + nrm * 0.0, p1 + nrm * 0.0
        bar(b, a + (0, 0, 0.075), c + (0, 0, 0.075), 0.15, 0.025, slot, up=nrm)


def plates(b, x0, x1, y0, y1, z, t, slot, n=1, axis="x"):
    """A deck of n plates side by side across x0..x1 (slight gaps), top at z."""
    xs = np.linspace(x0, x1, n + 1)
    for i in range(n):
        bx(b, (xs[i] + 0.003, y0, z - t), (xs[i + 1] - 0.003, y1, z), slot, ch=0.003, pin=False, axis=axis)


def face_quad(b, x0, x1, z0, z1, y, slot, facing=-1):
    """A single flat face (two triangles) on 0..1 UVs, in the plane y, looking toward facing * Y. Returns the part."""
    v = np.array([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], float)
    loops = [0, 1, 2, 3] if facing < 0 else [3, 2, 1, 0]
    p = b._add(v, loops, [4], slot, kind=b.OTHER, uv_off=(0.0, 0.0))
    p["uv01"] = (x0, x1, z0, z1, facing)
    return p


def fix_face_uvs(ob, slot_name, frame, zrange=None):
    """Set 0..1 UVs on the faces of one slot from a frame (origin, u axis, v axis, (w, h)); zrange: only the faces whose
    centre lies between these heights (several faces of one slot, each with its own frame)."""
    o, ua, va, (w, h) = frame
    me = ob.data
    idx = [i for i, m in enumerate(me.materials) if m and m.name == slot_name]
    if not idx:
        return 0
    uvl = me.uv_layers[0].data
    co = np.array([v.co for v in me.vertices])
    n = 0
    for poly in me.polygons:
        if poly.material_index in idx:
            if zrange is not None and not (zrange[0] <= poly.center[2] <= zrange[1]):
                continue
            for li in poly.loop_indices:
                p = co[me.loops[li].vertex_index] - np.asarray(o)
                uvl[li].uv = (float(np.dot(p, ua) / w), float(np.dot(p, va) / h))
            n += 1
    return n


def label(b, o, u, v, w=0.40, h=0.28, back="grey"):
    """A printed label: a thin backing plate and its face (M_Sign_MT_Face, 0..1) on the plane through o spanned by u
    and v (the face looks along u x v). Returns the face's frame for done(faces=...)."""
    o, u, v = (np.asarray(a, float) for a in (o, u, v))
    n = np.cross(u, v)
    b.prism(steel.rect(w, h), o - n * 0.008, u, v, n * 0.008, back, pstep=9.0)
    f = o + n * 0.001
    b._add(np.array([f, f + u * w, f + u * w + v * h, f + v * h]), [0, 1, 2, 3], [4], "signFace", kind=b.OTHER, uv_off=(0.0, 0.0))
    return ("M_Sign_MT_Face", (tuple(f), u, v, (w, h)))


def done(ctx, b, name, M, ground=True, ledges=(), faces=None, **asset):
    """Finish, weather, set face UVs, declare. faces: [(slot name, frame)] for 0..1 face slots."""
    ob = b.finish(name, M, ctx.kit)
    fc.weather(ctx, b, ob, name, ledges=list(ledges), ground=ground)
    for f_ in (faces or []):
        fix_face_uvs(ob, *f_)
    asset.setdefault("collision", "none")
    ctx.asset(ob, slots=SLOT_META, **asset)
    ctx.K[name] = ob
    return ob


# ================================================================================================= decks and parapets

def m_deck(ctx, M, kind):
    """Roof deck panel 4 x 4 m, top at z = 0: gravel ballast on the membrane, or concrete pavers on pedestals (THE LOFTLARK,
    walkways). Pivot: a corner (x, y from 0 to 4)."""
    b = B(301 if kind == "Gravel" else 302, step=0.5)
    if kind == "Gravel":
        bx(b, (0, 0, -0.10), (4.0, 4.0, 0.0), "roofGravel", axis="x")
    else:
        bx(b, (0, 0, -0.12), (4.0, 4.0, -0.07), "roof", axis="x")
        for i in range(6):
            for j in range(6):
                x0, y0 = i * 0.6667, j * 0.6667
                bx(b, (x0 + 0.006, y0 + 0.006, -0.05), (x0 + 0.6607, y0 + 0.6607, 0.0), "conc", pin=False, axis="x")
    name = "SM_Roof_Deck_%s_4m" % kind
    return done(ctx, b, name, M, ground=False, expect_size=(4.0, 4.0, None),
                notes=("Roof deck panel 4 x 4 m, top at z = 0 (the roof surface of the level data): %s. Pivot at a corner. "
                       "Tile it over each roof between the parapets.") % ("ballast gravel on the membrane" if kind == "Gravel" else
                                                                        "2 ft concrete pavers on rubber pedestals (THE LOFTLARK, walkways)"))


def m_parapet(ctx, M, brick, L):
    """Parapet 1.10 m over the roof, 0.30 thick: brick, cast-stone coping overhanging both sides, membrane flashing up
    the inner face under a steel counterflashing strip. Wall-module pivot (outer face toward -Y, roof surface z = 0)."""
    b = B(311 + L, step=0.3)
    k = "brick" + brick
    T, H = 0.30, 1.10
    bx(b, (0, 0, -0.40), (L, T, H - 0.08), k, axis="x")                                       # brick, down past the roof line
    bx(b, (0, -0.04, H - 0.08), (L, T + 0.04, H), "stone", ch=0.012, axis="x")                 # coping
    for xx in np.arange(1.0, L - 0.01, 1.0):                                                   # coping joints
        bx(b, (xx - 0.004, -0.045, H - 0.082), (xx + 0.004, T + 0.045, H + 0.002), "conc", pin=False, axis="y")
    bx(b, (0, T, 0.0), (L, T + 0.012, 0.38), "roof", axis="x")                                 # base flashing up the inner face
    bx(b, (0, T, 0.0), (L, T + 0.10, 0.012), "roof", axis="x")
    bx(b, (0, T + 0.012, 0.34), (L, T + 0.022, 0.42), "galv", ch=0.002, pin=False, axis="x")   # counterflashing strip
    for xx in np.arange(0.4, L, 0.8):
        rod(b, (xx, T + 0.022, 0.40), (xx, T + 0.032, 0.40), 0.008, "galv", n=6)
        b.leaks.append((xx, T + 0.024, 0.34))
    name = "SM_Roof_Parapet_%dm_%s" % (L, brick)
    return done(ctx, b, name, M, ground=False, ledges=[(0, L, H - 0.08, 0.8)], expect_size=(L, None, None),
                notes=("Roof parapet %d m (%s brick), 1.10 m over the roof, 0.30 thick (midtown.md 2.1): overhanging coping, inner "
                       "flashing and counterflashing. Wall-module pivot: bottom-left of the outer face, running +X, outer face -Y, "
                       "z = 0 on the roof surface; the brick runs 0.40 below it. The edge guard is data (playerOnly), not art.")
                % (L, brick))


def m_namepanel(ctx, M):
    """Cast-stone name panel 6.0 x 0.6 m on the parapet's street face, the face (M_Sign_MT_Face) incised: HALVORSEN
    BUILDING (A) and CORVIN HALL (C) from the sign atlas. Pivot: bottom-left of its back, running +X, face toward -Y."""
    b = B(321, step=1.0)
    W, H = 6.0, 0.6
    bx(b, (-0.08, -0.10, -0.08), (W + 0.08, 0.0, H + 0.08), "stone", ch=0.015, axis="x")       # surround
    bx(b, (-0.12, -0.14, H + 0.08), (W + 0.12, 0.0, H + 0.14), "stone", ch=0.012, axis="x")    # hood moulding
    face_quad(b, 0.0, W, 0.0, H, -0.1005, "signFace")
    return done(ctx, b, "SM_Roof_NamePanel_6m", M, ground=False, expect_size=(W + 0.24, None, None),
                faces=[("M_Sign_MT_Face", ((0.0, -0.1005, 0.0), X, Z, (W, H)))],
                notes="Cast-stone name panel 6 x 0.6 m (face 0..1 in M_Sign_MT_Face: Plaque_Halvorsen on A's parapet, Plaque_Corvin "
                      "on C's cornice). Pivot: bottom-left of the back, face toward -Y, set on the outer face of the parapet.")


# ================================================================================================= water towers

def m_tankstand(ctx, M, h, span):
    """Steel stand under a water tank: four I-section legs on concrete piers, a ring of girts at mid height, angle
    braces (no tie rods: flicker), two main beams and cross beams on top with timber dunnage. Pivot: centre, on the roof.
    The tank sits at z = h + 0.30 (the dunnage top)."""
    b = B(331 + int(h), step=0.6)
    L = span / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * L, sy * L
            bx(b, (x - 0.30, y - 0.30, 0.0), (x + 0.30, y + 0.30, 0.35), "conc", ch=0.02, pin=False, axis="x")     # pier
            bx(b, (x - 0.20, y - 0.20, 0.35), (x + 0.20, y + 0.20, 0.375), "black", ch=0.003, pin=False, axis="x")   # base plate
            b.rivets([(x + dx, y + dy, 0.375) for dx in (-0.14, 0.14) for dy in (-0.14, 0.14)], Z, "black", d=0.04, h=0.02, leak=0.5)
            col_ibeam(b, x, y, 0.375, h, turn=(sx * sy > 0))
    zs = [0.375 + (h - 0.375) * f for f in ((0.5,) if h < 3 else (0.35, 0.70))]
    corners = [(-L, -L), (L, -L), (L, L), (-L, L)]
    for z in zs:                                                                               # girts (channels)
        for i in range(4):
            p, q = corners[i], corners[(i + 1) % 4]
            bar(b, (p[0], p[1], z), (q[0], q[1], z), 0.08, 0.16, "black", ch=0.003)
    levels = [0.375] + zs + [h - 0.05]
    for a_, c_ in zip(levels[:-1], levels[1:]):                                                # X braces per panel
        for i in range(4):
            p, q = corners[i], corners[(i + 1) % 4]
            angle_brace(b, (p[0], p[1], a_ + 0.08), (q[0], q[1], c_ - 0.08))
            angle_brace(b, (q[0], q[1], a_ + 0.08), (p[0], p[1], c_ - 0.08))
    for sy in (-1, 1):                                                                         # main beams, cross beams
        beam_x(b, -L - 0.35, L + 0.35, sy * L, h, d=0.30, bf=0.16)
    for xx in np.linspace(-L + 0.1, L - 0.1, 6):                                               # dunnage timbers
        bx(b, (xx - 0.075, -L - 0.30, h + 0.30 - 0.15), (xx + 0.075, L + 0.30, h + 0.30), "timber", ch=0.006, axis="y")
    for (cx, cy) in corners:                                                                   # cap plates and bolts
        b.rivets([(cx + dx, cy + dy, h + 0.30) for dx in (-0.05, 0.05) for dy in (-0.05, 0.05)], Z, "black", d=0.035, h=0.02, leak=0.3)
    name = "SM_Roof_TankStand_%dm" % int(round(h))
    return done(ctx, b, name, M, ground=True, expect_size=(None, None, h + 0.30),
                notes=("Water tank stand, %.0f m (legs %.1f m apart): I-section legs on concrete piers, girts, angle X braces (no "
                       "tie rods: members 6 cm and up), main beams, timber dunnage. Pivot: centre on the roof; the tank goes on at "
                       "z = %.2f. WT-A uses the 4 m stand, WT-B and WT-C the 2 m.") % (h, span, h + 0.30))


def m_watertank(ctx, M, D, H, cone):
    """Timber water tank: staves (V joints) of diameter D and height H, steel hoops with lugs, a conical roof with a
    hatch and finial, an outlet pipe and a caged access ladder (rails and rungs 6 cm). Pivot: centre of the floor."""
    b = B(341 + int(D * 10), step=0.6)
    r, ns = D / 2, 40
    for yy in np.linspace(-r + 0.2, r - 0.2, int(D / 0.30)):                                  # floor joists
        hx = math.sqrt(max(r * r - yy * yy, 0.01)) - 0.02
        bx(b, (-hx, yy - 0.10, 0.0), (hx, yy + 0.10, 0.10), "timber", axis="x")
    prof = []
    for i in range(ns):
        a0, a1 = 2 * math.pi * i / ns, 2 * math.pi * (i + 1) / ns
        e = 0.005 / r
        prof += [(r * math.cos(a0 + e), r * math.sin(a0 + e)), (r * math.cos(a1 - e), r * math.sin(a1 - e)),
                 ((r - 0.010) * math.cos(a1), (r - 0.010) * math.sin(a1))]
    b.prism(prof, (0, 0, 0.10), X, Y, (0, 0, H), "timber", step=H / 3, pstep=9.0, fdir=X)
    nh = int(H / 0.7) + 1
    for i, zh in enumerate(np.linspace(0.35, H - 0.10, nh)):                                   # hoops and lugs
        hoop = geo.tube(r + 0.012, r - 0.002, 0.06, 40)
        geo.transform(hoop, loc=(0, 0, zh))
        b.absorb(hoop, "black")
        a = 0.4 + i * 1.7
        ca, sa = math.cos(a), math.sin(a)
        lug = geo.box((0.16, 0.07, 0.10), bevel=0.006)
        geo.transform(lug, loc=((r + 0.03) * ca, (r + 0.03) * sa, zh - 0.02), rot=(0, 0, math.degrees(a) + 90))
        b.absorb(lug, "black")
        b.leaks.append(((r + 0.02) * ca, (r + 0.02) * sa, zh - 0.02))
    z_top = 0.10 + H
    rc = geo.revolve([(0.0, z_top - 0.04), (r + 0.18, z_top - 0.04), (r + 0.18, z_top + 0.02), (0.20, z_top + cone - 0.08),
                      (0.0, z_top + cone)], 40)
    b.absorb(rc, "timber")
    rod(b, (0, 0, z_top + cone - 0.05), (0, 0, z_top + cone + 0.35), 0.04, "black", n=10)    # finial
    ball = geo.sphere(0.08, 12, 8)
    geo.transform(ball, loc=(0, 0, z_top + cone + 0.40))
    b.absorb(ball, "black")
    ha = math.radians(20)                                                                       # roof hatch on the ladder side
    hx_, hz = (r * 0.55) * math.cos(ha), z_top + cone * (1 - 0.55 * r / (r + 0.18))
    hatch = geo.box((0.70, 0.60, 0.20), bevel=0.01)
    geo.transform(hatch, loc=(hx_, (r * 0.55) * math.sin(ha), hz - 0.06), rot=(0, -math.degrees(math.atan2(cone, r)), 20))
    b.absorb(hatch, "timber")
    rod(b, (0.6, -0.3, -0.6), (0.6, -0.3, 0.05), 0.11, "black", n=14)                         # outlet riser and flange
    rod(b, (0.6, -0.3, 0.0), (0.6, -0.3, 0.04), 0.16, "black", n=14)
    xl = r + 0.25                                                                               # ladder up the +X side
    for sy in (-0.24, 0.24):
        bar(b, (xl, sy, -0.2), (xl, sy, z_top + 0.9), MEMBER_MIN, MEMBER_MIN, "black", up=X, ch=0.004)
        for zz in (0.8, z_top - 0.3):
            bar(b, (r + 0.01, sy, zz), (xl, sy, zz), MEMBER_MIN, MEMBER_MIN, "black", ch=0.004)
    for zz in np.arange(0.10, z_top + 0.8, 0.35):
        tube(b, (xl, -0.24, zz), (xl, 0.24, zz), "black", 0.03, n=8)
    for zz in np.arange(2.2, z_top + 0.9, 1.0):                                                 # cage hoops (flat bar on edge)
        pts = [(xl + 0.36 * math.cos(t), 0.36 * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, 9)]
        for p, q in zip(pts[:-1], pts[1:]):
            bar(b, (p[0], p[1], zz), (q[0], q[1], zz), MEMBER_MIN, 0.012 * 5, "black", ch=0.003)
    for t in np.linspace(-math.pi / 2, math.pi / 2, 5)[1:-1]:                                   # cage verticals
        bar(b, (xl + 0.36 * math.cos(t), 0.36 * math.sin(t), 2.2), (xl + 0.36 * math.cos(t), 0.36 * math.sin(t), z_top + 0.9),
            MEMBER_MIN, MEMBER_MIN * 0.5 + 0.03, "black", up=X, ch=0.003)
    name = "SM_Roof_WaterTank_%s" % ("%.1f" % D).replace(".", "p")
    return done(ctx, b, name, M, ground=False, expect_size=(None, None, None),
                notes=("Timber water tank %.1f m across, staves %.1f m, cone roof %.1f m, hoops, hatch, outlet, caged ladder (+X). "
                       "Pivot: centre of the floor; set on a SM_Roof_TankStand at its dunnage top. WT-A: 4.6 m on the 4 m stand "
                       "(tank 25.2 to 30.8, roof to 32.4, midtown.md 4); WT-B and WT-C: 3.6 m on the 2 m stand.") % (D, H, cone))


# ================================================================================================= rooms on the roof

def room(b, W, Dp, Hi, brick, door, door_w=2.0, door_h=2.3, slab=0.25, wall=0.25, vents=()):
    """A brick room W (x) by Dp (y), clear height Hi, walls `wall` thick, a door opening `door_w` wide on the face
    `door` = (side, centre along it) with side in '+x', '-x', '+y', '-y'. Centre of the footprint at the origin."""
    x0, x1, y0, y1 = -W / 2, W / 2, -Dp / 2, Dp / 2
    side, c = door
    k = "brick" + brick
    H = Hi

    def wall_x(y_lo, y_hi, xa, xb, cut=None):          # wall along x from xa to xb, between y_lo..y_hi
        if cut is None:
            bx(b, (xa, y_lo, 0), (xb, y_hi, H), k, axis="x")
            return
        ca, cb = cut
        bx(b, (xa, y_lo, 0), (ca, y_hi, H), k, axis="x")
        bx(b, (cb, y_lo, 0), (xb, y_hi, H), k, axis="x")
        bx(b, (ca, y_lo, door_h), (cb, y_hi, H), k, axis="x")
        bx(b, (ca - 0.06, y_lo - 0.02, door_h), (cb + 0.06, y_hi + 0.02, door_h + 0.20), "grey", ch=0.004, pin=False, axis="x")   # steel lintel

    def wall_y(x_lo, x_hi, ya, yb, cut=None):
        if cut is None:
            bx(b, (x_lo, ya, 0), (x_hi, yb, H), k, axis="y")
            return
        ca, cb = cut
        bx(b, (x_lo, ya, 0), (x_hi, ca, H), k, axis="y")
        bx(b, (x_lo, cb, 0), (x_hi, yb, H), k, axis="y")
        bx(b, (x_lo, ca, door_h), (x_hi, cb, H), k, axis="y")
        bx(b, (x_lo - 0.02, ca - 0.06, door_h), (x_hi + 0.02, cb + 0.06, door_h + 0.20), "grey", ch=0.004, pin=False, axis="y")

    cut = (c - door_w / 2, c + door_w / 2)
    wall_x(y0, y0 + wall, x0, x1, cut if side == "-y" else None)
    wall_x(y1 - wall, y1, x0, x1, cut if side == "+y" else None)
    wall_y(x0, x0 + wall, y0 + wall, y1 - wall, cut if side == "-x" else None)
    wall_y(x1 - wall, x1, y0 + wall, y1 - wall, cut if side == "+x" else None)
    bx(b, (x0 - 0.08, y0 - 0.08, H), (x1 + 0.08, y1 + 0.08, H + slab), "stone", ch=0.015, axis="x")     # slab, drip edge
    bx(b, (x0 + 0.05, y0 + 0.05, H + slab), (x1 - 0.05, y1 - 0.05, H + slab + 0.01), "roof", axis="x")
    for (vx, vy) in vents:
        rod(b, (vx, vy, H + slab), (vx, vy, H + slab + 0.5), 0.06, "grey", n=12)
        rod(b, (vx, vy, H + slab + 0.5), (vx, vy, H + slab + 0.56), 0.10, "grey", n=12)
    return x0, x1, y0, y1, H


def open_door(b, side, c, door_w, wall, x0, x1, y0, y1, door_h=2.3, slot="grey"):
    """A steel door frame in the opening and the leaf swung open 100 degrees against the wall outside."""
    t = 0.05
    if side in ("+x", "-x"):
        xw = x1 if side == "+x" else x0
        s = 1 if side == "+x" else -1
        for yy in (c - door_w / 2, c + door_w / 2 - 0.06):
            bx(b, (xw - s * wall - 0.01, yy, 0), (xw + s * 0.01, yy + 0.06, door_h), slot, ch=0.003, pin=False, axis="z")
        leaf = (xw + s * 0.03, xw + s * (0.03 + 0.95), c - door_w / 2 - 0.10, c - door_w / 2 - 0.10 + t)
        bx(b, (min(leaf[0], leaf[1]), leaf[2], 0.02), (max(leaf[0], leaf[1]), leaf[3], door_h - 0.03), slot, ch=0.004, pin=False, axis="z")
        bx(b, (min(leaf[0], leaf[1]) + 0.10, leaf[2] - 0.012, 1.0), (min(leaf[0], leaf[1]) + 0.32, leaf[2], 1.10), "galv", ch=0.003, pin=False)
    else:
        yw = y1 if side == "+y" else y0
        s = 1 if side == "+y" else -1
        for xx in (c - door_w / 2, c + door_w / 2 - 0.06):
            bx(b, (xx, yw - s * wall - 0.01, 0), (xx + 0.06, yw + s * 0.01, door_h), slot, ch=0.003, pin=False, axis="z")
        leaf = (yw + s * 0.03, yw + s * (0.03 + 0.95), c - door_w / 2 - 0.10, c - door_w / 2 - 0.10 + t)
        bx(b, (leaf[2], min(leaf[0], leaf[1]), 0.02), (leaf[3], max(leaf[0], leaf[1]), door_h - 0.03), slot, ch=0.004, pin=False, axis="z")
        bx(b, (leaf[2] - 0.012, min(leaf[0], leaf[1]) + 0.10, 1.0), (leaf[2], min(leaf[0], leaf[1]) + 0.32, 1.10), "galv", ch=0.003, pin=False)


def m_bulkhead(ctx, M):
    """Stair bulkhead (stair hut) 4 x 4 m: I1 on A, bulkhead B. Clear 2.8 m, a 2.0 m door on +X with the steel leaf
    open against the wall, the stair's first flight going down at the back (dark below), a vent and a label plate."""
    b = B(351, step=0.35)
    W = Dp = 4.0
    door = ("+x", 0.0)
    x0, x1, y0, y1, H = room(b, W, Dp, 2.8, "Buff", door, vents=[(-1.2, 1.2)])
    open_door(b, "+x", 0.0, 2.0, 0.25, x0, x1, y0, y1)
    bx(b, (x0 + 0.25, -1.75, -0.02), (x1 - 0.25, 1.75, 0.0), "conc", axis="x")                 # landing slab
    for i in range(6):                                                                         # the flight going down, west
        zt = -0.18 * (i + 1)
        bx(b, (x0 + 0.30 + i * 0.26, -1.70, zt - 0.04), (x0 + 0.56 + i * 0.26, -0.45, zt), "conc", pin=False, axis="y")
    bx(b, (x0 + 0.30, -1.72, -1.6), (x0 + 2.0, -0.43, -1.15), "interior", pin=False)
    rail_run(b, np.array((x0 + 0.30, -0.40, 0.0)), np.array((x0 + 2.0, -0.40, 0.0)), "grey", h=1.0, post=0.85, mid=True, toe=False)
    lab = label(b, (x1 + 0.008, 1.12, 1.45), Y, Z)                                              # Label_RoofDoor
    return done(ctx, b, "SM_Roof_Bulkhead_4x4", M, ground=True, faces=[lab], ledges=[(-9, 9, 2.8, 0.8)], expect_size=(None, None, None),
                notes="Stair bulkhead 4 x 4 m, clear 2.8 m (I1 on A at (-46, 21.2, -35), bulkhead B on B): buff brick, slab roof, "
                      "vent, 2.0 m door on +X (Goon door, midtown.md 9.1) with the leaf open, the stair going down inside (dark). "
                      "Turn it so +X faces the door side: I1's door is on its east face. Label plate face: Label_RoofDoor.")


def m_tankhouse(ctx, M):
    """The tank house (I2, Reel 7): brick room 6 x 6, clear 2.8, its 2.0 m door on the south face (-Y), a heavier slab
    that carries WT-C's stand, a pump and pipe manifold inside (the reel hold corner), a work-light bracket over the door."""
    b = B(361, step=0.35)
    x0, x1, y0, y1, H = room(b, 6.0, 6.0, 2.8, "Red", ("-y", 0.0), slab=0.35)
    open_door(b, "-y", 0.0, 2.0, 0.25, x0, x1, y0, y1)
    bx(b, (x0 + 0.25, y0 + 0.25, -0.02), (x1 - 0.25, y1 - 0.25, 0.0), "conc", axis="x")
    bx(b, (x1 - 1.8, y1 - 1.5, 0.0), (x1 - 0.4, y1 - 0.6, 0.25), "conc", ch=0.02, pin=False)  # pump plinth
    for k_, xx in enumerate((x1 - 1.5, x1 - 0.8)):                                              # two pumps
        rod(b, (xx, y1 - 1.05, 0.25), (xx, y1 - 1.05, 0.75), 0.18, "grey", n=16)
        rod(b, (xx, y1 - 1.05, 0.75), (xx, y1 - 1.05, 0.85), 0.12, "grey", n=16)
        tube(b, (xx, y1 - 1.05, 0.55), (xx, y1 - 0.30, 0.55), "grey", 0.05)
    tube(b, (x1 - 1.9, y1 - 0.30, 0.55), (x1 - 0.30, y1 - 0.30, 0.55), "grey", 0.08)           # header along the back wall
    tube(b, (x1 - 0.30, y1 - 0.30, 0.55), (x1 - 0.30, y1 - 0.30, H + 0.35), "grey", 0.08)       # riser up through the slab
    tube(b, (x0 + 0.40, y1 - 0.30, 2.40), (x1 - 0.30, y1 - 0.30, 2.40), "grey", 0.05)
    for xx in np.arange(x0 + 0.8, x1 - 0.3, 1.2):
        bar(b, (xx, y1 - 0.25, 2.30), (xx, y1 - 0.40, 2.30), 0.06, 0.06, "black")
    bx(b, (x0 + 0.40, y1 - 0.45, 1.20), (x0 + 1.20, y1 - 0.25, 1.90), "grey", ch=0.01, pin=False)  # control box
    lab = label(b, (x0 + 0.62, y1 - 0.45, 1.30), X, Z, 0.36, 0.24)                               # Label_HighVoltage
    bx(b, (-0.2, y0 - 0.25, 2.55), (0.2, y0, 2.65), "black", ch=0.004, pin=False)               # work-light bracket
    return done(ctx, b, "SM_Roof_TankHouse_6x6", M, ground=True, faces=[lab], ledges=[(-9, 9, 2.8, 0.8)], expect_size=(None, None, None),
                notes="The tank house (I2, Reel 7) on C: 6 x 6 m, clear 2.8 m, red brick, a 0.35 m slab that carries WT-C (the 2 m "
                      "stand stands on it), the 2.0 m door on the south face (-Y), pumps and a manifold inside, a bracket over the "
                      "door for SM_Roof_WorkLight (the shadowed sodium flood). Pivot: centre on the roof.")


def m_machineroom(ctx, M):
    """The machine room (I3) on B: 6 x 6, clear 3.0, door on -Y, louvred intake on +X, an exhaust fan on the slab."""
    b = B(371, step=0.35)
    x0, x1, y0, y1, H = room(b, 6.0, 6.0, 3.0, "Buff", ("-y", 0.0), vents=[(1.5, 1.5)])
    open_door(b, "-y", 0.0, 2.0, 0.25, x0, x1, y0, y1)
    bx(b, (x0 + 0.25, y0 + 0.25, -0.02), (x1 - 0.25, y1 - 0.25, 0.0), "conc", axis="x")
    bx(b, (x1, -1.0, 1.0), (x1 + 0.06, 1.0, 2.2), "grey", ch=0.006, pin=False, axis="y")          # louvre frame
    for zz in np.arange(1.08, 2.15, 0.12):
        bx(b, (x1 + 0.06, -0.95, zz), (x1 + 0.13, 0.95, zz + 0.065), "grey", pin=False, axis="y")
        bx(b, (x1 + 0.055, -0.95, zz + 0.065), (x1 + 0.06, 0.95, zz + 0.12), "grille", pin=False, axis="y")
    for i in range(2):                                                                          # motors and a cabinet inside
        cx = x0 + 1.3 + i * 2.0
        bx(b, (cx - 0.6, y1 - 1.8, 0.0), (cx + 0.6, y1 - 0.6, 0.15), "conc", ch=0.01, pin=False)
        rod(b, (cx - 0.45, y1 - 1.2, 0.55), (cx + 0.45, y1 - 1.2, 0.55), 0.30, "grey", n=18)
        bx(b, (cx - 0.5, y1 - 1.5, 0.15), (cx + 0.5, y1 - 0.9, 0.30), "grey", ch=0.01, pin=False)
    bx(b, (x1 - 1.2, y0 + 0.35, 0.0), (x1 - 0.35, y0 + 0.95, 2.0), "grey", ch=0.01, pin=False)
    lab = label(b, (1.25, y0 - 0.008, 1.45), X, Z)                                              # Label_MachineRoom
    fx, fy = -1.2, 1.2                                                                          # exhaust fan on the slab
    bx(b, (fx - 0.6, fy - 0.6, H + 0.25), (fx + 0.6, fy + 0.6, H + 0.55), "grey", ch=0.01, pin=False)
    rod(b, (fx, fy, H + 0.55), (fx, fy, H + 0.95), 0.45, "grey", n=24)
    rod(b, (fx, fy, H + 0.95), (fx, fy, H + 0.97), 0.40, "grille", n=24)
    return done(ctx, b, "SM_Roof_MachineRoom_6x6", M, ground=True, faces=[lab], ledges=[(-9, 9, 3.0, 0.8)], expect_size=(None, None, None),
                notes="Machine room (I3) on B: 6 x 6 m, clear 3.0 m, buff brick, a 2.0 m door on -Y at x 0 (the room's south face "
                      "x -38..-36), a louvred intake on +X, motors and a cabinet inside, an exhaust fan on the slab. Pivot: centre.")


def m_servicebulkhead(ctx, M):
    """The bulkhead over the service stair shaft (I4) on D: 5 (x) by 6 (y), its top at 2.8 over the roof, the 2.0 m
    door on the -X face near the north end, the shaft open below (the stair is the level's L6 flights)."""
    b = B(381, step=0.35)
    W, Dp, H = 5.0, 6.0, 2.8
    x0, x1, y0, y1 = -W / 2, W / 2, -Dp / 2, Dp / 2
    k = "brickRed"
    c = y1 - 1.2                                                                                 # door z 4.2..6.2: local y 0.8..2.8
    bx(b, (x0, y0, 0), (x0 + 0.25, c - 1.0, H), k, axis="y")
    bx(b, (x0, c + 1.0, 0), (x0 + 0.25, y1, H), k, axis="y")
    bx(b, (x0, c - 1.0, 2.3), (x0 + 0.25, c + 1.0, H), k, axis="y")
    bx(b, (x0 - 0.02, c - 1.06, 2.3), (x0 + 0.27, c + 1.06, 2.5), "grey", ch=0.004, pin=False, axis="y")
    bx(b, (x1 - 0.25, y0, 0), (x1, y1, H), k, axis="y")
    bx(b, (x0 + 0.25, y0, 0), (x1 - 0.25, y0 + 0.25, H), k, axis="x")
    bx(b, (x0 + 0.25, y1 - 0.25, 0), (x1 - 0.25, y1, H), k, axis="x")
    bx(b, (x0 - 0.08, y0 - 0.08, H), (x1 + 0.08, y1 + 0.08, H + 0.25), "stone", ch=0.015, axis="x")
    bx(b, (x0 + 0.05, y0 + 0.05, H + 0.25), (x1 - 0.05, y1 - 0.05, H + 0.26), "roof", axis="x")
    open_door(b, "-x", c, 2.0, 0.25, x0, x1, y0, y1)
    rod(b, (1.5, -2.2, H + 0.25), (1.5, -2.2, H + 0.75), 0.07, "grey", n=12)
    lab = label(b, (x0 - 0.008, c + 1.55, 1.45), -Y, Z)                                          # Label_RoofDoor
    return done(ctx, b, "SM_Roof_Bulkhead_5x6", M, ground=True, faces=[lab], ledges=[(-9, 9, H, 0.8)], expect_size=(None, Dp + 0.16, None),
                notes="Service-stair bulkhead (I4) on D: 5 x 6 m over the shaft x -13..-8, z 4..10, top at 16.8 (2.8 over R1), red "
                      "brick, the 2.0 m door in the -X (west) face at z 4.2..6.2, the shaft open below (L6 is level geometry).")


# ================================================================================================= roof dressing

def m_hvac(ctx, M, size):
    """Packaged rooftop unit on its curb: cabinet with access panels and handles, a condenser coil face behind a
    louvred guard, condenser fans with guards on top, an economiser hood, conduit and a disconnect box."""
    L, W, H = (3.6, 1.8, 1.3) if size == "L" else (2.2, 1.3, 1.05)
    b = B(391 if size == "L" else 392, step=0.5)
    bx(b, (-L / 2 - 0.05, -W / 2 - 0.05, 0.0), (L / 2 + 0.05, W / 2 + 0.05, 0.35), "galv", ch=0.005, axis="x")   # curb
    bx(b, (-L / 2, -W / 2, 0.35), (L / 2, W / 2, 0.35 + H), "hvac", ch=0.012, axis="x")
    zt = 0.35 + H
    for i in range(int(L / 0.6)):                                                                # access panels on -Y
        xa = -L / 2 + 0.06 + i * 0.6
        if xa + 0.54 > L / 2 - 0.9:
            break
        bx(b, (xa, -W / 2 - 0.008, 0.45), (xa + 0.54, -W / 2, zt - 0.12), "hvac", ch=0.003, pin=False, axis="z")
        bx(b, (xa + 0.40, -W / 2 - 0.045, 0.9), (xa + 0.46, -W / 2 - 0.008, 1.05), "galv", ch=0.004, pin=False)
    cx0 = L / 2 - 0.85                                                                           # condenser coil end
    for s in (-1, 1):
        bx(b, (cx0, s * W / 2 - (0.01 if s > 0 else 0.0), 0.45), (L / 2 - 0.05, s * W / 2 + (0.0 if s > 0 else 0.0) + 0.01 * s, zt - 0.10),
           "grille", pin=False, axis="x")
        for zz in np.arange(0.48, zt - 0.12, 0.10):
            bx(b, (cx0, s * (W / 2 + 0.01) - 0.03, zz), (L / 2 - 0.05, s * (W / 2 + 0.01) + 0.03, zz + 0.06), "hvac", pin=False, axis="x")
    nf = 2 if size == "L" else 1
    for i in range(nf):                                                                          # fans on top
        fx = L / 2 - 0.55 - i * 1.0 if size == "L" else L / 2 - 0.55
        rod(b, (fx, 0, zt), (fx, 0, zt + 0.10), 0.40, "hvac", n=24)
        rod(b, (fx, 0, zt + 0.10), (fx, 0, zt + 0.105), 0.36, "grille", n=24)
        for a in range(0, 180, 30):                                                              # guard: radial and a ring
            t = math.radians(a)
            bar(b, (fx - 0.38 * math.cos(t), -0.38 * math.sin(t), zt + 0.13), (fx + 0.38 * math.cos(t), 0.38 * math.sin(t), zt + 0.13),
                0.06, 0.02, "galv", ch=0.003)
        ring = geo.torus(0.25, 0.03, 32, 8)
        geo.transform(ring, loc=(fx, 0, zt + 0.13))
        b.absorb(ring, "galv")
    hx = -L / 2                                                                                  # economiser hood on -X
    for i, zz in enumerate(np.arange(0.55, zt - 0.2, 0.16)):
        bx(b, (hx - 0.28, -W / 2 + 0.15, zz), (hx, W / 2 - 0.15, zz + 0.012), "hvac", pin=False, axis="y")
    bx(b, (hx - 0.30, -W / 2 + 0.12, 0.50), (hx, -W / 2 + 0.15, zt - 0.15), "hvac", pin=False)
    bx(b, (hx - 0.30, W / 2 - 0.15, 0.50), (hx, W / 2 - 0.12, zt - 0.15), "hvac", pin=False)
    bx(b, (hx - 0.31, -W / 2 + 0.12, zt - 0.17), (hx, W / 2 - 0.12, zt - 0.14), "hvac", pin=False)
    bx(b, (-L / 2 + 0.3, W / 2, 0.6), (-L / 2 + 0.7, W / 2 + 0.18, 1.1), "grey", ch=0.008, pin=False)   # disconnect box
    lab = label(b, (-L / 2 + 0.68, W / 2 + 0.188, 0.80), -X, Z, 0.36, 0.24)                       # Label_HighVoltage
    tube(b, (-L / 2 + 0.5, W / 2 + 0.09, 0.6), (-L / 2 + 0.5, W / 2 + 0.09, 0.12), "galv", 0.03)        # conduit to the roof
    tube(b, (-L / 2 + 0.5, W / 2 + 0.09, 0.12), (-L / 2 + 0.5, W / 2 + 1.2, 0.12), "galv", 0.03)
    for (xx, yy) in ((-L / 2 + 0.5, W / 2 + 0.7),):
        bx(b, (xx - 0.15, yy - 0.08, 0.0), (xx + 0.15, yy + 0.08, 0.10), "rubber", ch=0.01, pin=False)
    b.leaks += [(L / 2 - 0.05, -W / 2, 0.45), (-L / 2, W / 2 - 0.2, 0.40)]
    return done(ctx, b, "SM_Roof_HVAC_RTU_%s" % size, M, ground=True, faces=[lab], cover_height=round(0.35 + H, 2), expect_size=(None, None, None),
                notes=("Rooftop unit %s: %.1f x %.1f m cabinet on a 0.35 m curb, top at %.2f (cover: the level's collider is its box), "
                       "access panels on -Y, the coil end on +X, %d fan(s) with guards (6 cm), economiser hood on -X, disconnect box "
                       "(label face Label_HighVoltage), conduit. Pivot: centre on the roof; HVAC hum point source per unit.")
                % (size, L, W, 0.35 + H, nf))


def m_skylight(ctx, M):
    """Hipped skylight 2 x 3 m on a brick curb: wired glass panes in a galvanised frame, a ridge cap."""
    b = B(401, step=0.6)
    L, W = 3.0, 2.0
    bx(b, (-L / 2, -W / 2, 0), (L / 2, W / 2, 0.45), "brickBuff", axis="x")
    bx(b, (-L / 2 - 0.05, -W / 2 - 0.05, 0.45), (L / 2 + 0.05, W / 2 + 0.05, 0.50), "galv", ch=0.004, axis="x")
    zr = 0.50 + 0.55
    for s in (-1, 1):                                                                            # two long slopes
        p0, p1 = np.array((-L / 2 + 0.5, s * W / 2, 0.50)), np.array((-L / 2 + 0.5, 0.0, zr))
        F = np.array([[(-L / 2 + 0.5 + i * (L - 1.0) / 4, s * W / 2 * (1 - j), 0.50 + (zr - 0.50) * j) for i in range(5)] for j in (0.0, 1.0)])
        if s < 0:
            F = F[:, ::-1]
        sheet(b, F, 0.012, "glass")
        for i in range(5):
            x = -L / 2 + 0.5 + i * (L - 1.0) / 4
            bar(b, (x, s * W / 2, 0.52), (x, 0.0, zr + 0.01), 0.06, 0.04, "galv", up=Z, ch=0.004)
    for s in (-1, 1):                                                                            # two hipped ends
        F = np.array([[(s * L / 2, -W / 2, 0.50), (s * L / 2, W / 2, 0.50)], [(s * (L / 2 - 0.5), -0.001, zr), (s * (L / 2 - 0.5), 0.001, zr)]])
        if s > 0:
            F = F[:, ::-1]
        sheet(b, F, 0.012, "glass")
        for yy in (-W / 2, W / 2):
            bar(b, (s * L / 2, yy, 0.52), (s * (L / 2 - 0.5), 0.0, zr), 0.06, 0.04, "galv", up=Z, ch=0.004)
    bar(b, (-L / 2 + 0.45, 0, zr + 0.02), (L / 2 - 0.45, 0, zr + 0.02), 0.10, 0.05, "galv", ch=0.004)
    return done(ctx, b, "SM_Roof_Skylight_2x3", M, ground=True, expect_size=(L + 0.1, W + 0.1, None),
                notes="Hipped skylight 3 x 2 m on a 0.45 m brick curb, wired glass (opaque M_MI_Glass) in galvanised bars. Pivot: centre.")


def m_vent(ctx, M):
    b = B(411, step=0.5)
    bx(b, (-0.35, -0.35, 0), (0.35, 0.35, 0.30), "galv", ch=0.006, axis="x")
    rod(b, (0, 0, 0.30), (0, 0, 0.75), 0.18, "galv", n=20)
    cap = geo.revolve([(0.0, 0.78), (0.42, 0.78), (0.44, 0.80), (0.30, 0.98), (0.0, 1.02)], 24)
    b.absorb(cap, "galv")
    for a in range(0, 360, 90):
        t = math.radians(a)
        bar(b, (0.16 * math.cos(t), 0.16 * math.sin(t), 0.72), (0.34 * math.cos(t), 0.34 * math.sin(t), 0.80), 0.06, 0.012 * 5, "galv")
    rod(b, (0, 0, 0.74), (0, 0, 0.78), 0.30, "grille", n=20)
    return done(ctx, b, "SM_Roof_Vent_Mushroom", M, ground=True, expect_size=(None, None, None),
                notes="Mushroom exhaust vent on a curb, 1.0 m tall (4 of them carry the small steam plumes). Pivot: centre.")


def m_chimney(ctx, M):
    b = B(421, step=0.5)
    L, W, H = 1.2, 0.7, 2.0
    bx(b, (-L / 2, -W / 2, 0), (L / 2, W / 2, H), "brickRed", axis="x")
    bx(b, (-L / 2 - 0.05, -W / 2 - 0.05, H), (L / 2 + 0.05, W / 2 + 0.05, H + 0.10), "stone", ch=0.012, axis="x")
    for xx in (-0.28, 0.28):                                                                     # flue liners
        bx(b, (xx - 0.14, -0.14, H + 0.10), (xx + 0.14, 0.14, H + 0.42), "brickRed", ch=0.006, pin=False, axis="z")
        bx(b, (xx - 0.10, -0.10, H + 0.30), (xx + 0.10, 0.10, H + 0.425), "interior", pin=False, axis="z")
    b.leaks += [(-L / 2, -W / 2, H), (L / 2, W / 2, H)]
    return done(ctx, b, "SM_Roof_ChimneyStack", M, ground=True, ledges=[(-L / 2, L / 2, H, 1.0)], expect_size=(None, None, None),
                notes="Brick chimney stack 1.2 x 0.7 m, 2.0 m with coping and two clay flue liners (A's north party wall row). Pivot: centre.")


def m_tarkettle(ctx, M):
    b = B(431, step=0.5)
    bx(b, (-0.9, -0.08, 0.30), (0.6, 0.08, 0.38), "black", ch=0.006, pin=False)                  # chassis
    for s in (-1, 1):
        rod(b, (-0.3, s * 0.45, 0.30), (-0.3, s * 0.38, 0.30), 0.30, "rubber", n=18)            # wheels on an axle
    tube(b, (-0.3, -0.42, 0.30), (-0.3, 0.42, 0.30), "black", 0.03)
    rod(b, (0.0, 0, 0.38), (0.0, 0, 1.05), 0.42, "black", n=24)                                   # the kettle
    rod(b, (0.0, 0, 1.05), (0.0, 0, 1.10), 0.45, "black", n=24)
    bx(b, (-0.30, -0.30, 1.10), (0.30, 0.30, 1.14), "black", ch=0.006, pin=False)                # lid
    bx(b, (0.42, -0.18, 0.38), (0.62, 0.18, 0.62), "black", ch=0.006, pin=False)                 # burner box
    tube(b, (0.0, -0.42, 0.70), (0.0, -0.62, 0.62), "black", 0.03)                                # draw-off spout
    tube(b, (-0.9, 0, 0.38), (-1.3, 0, 0.95), "black", 0.03)                                     # tow handle
    tube(b, (-1.3, -0.2, 0.95), (-1.3, 0.2, 0.95), "black", 0.03)
    bx(b, (0.85, -0.25, 0.30), (0.95, 0.25, 0.36), "black", pin=False)
    tube(b, (0.9, 0, 0.0), (0.9, 0, 0.30), "black", 0.04)                                        # jack stand
    b.leaks += [(0.0, -0.42, 0.65), (0.2, 0.40, 0.70)]
    return done(ctx, b, "SM_Roof_TarKettle", M, ground=True, cover_height=1.1, expect_size=(None, None, None),
                notes="Roofer's tar kettle on two wheels with a burner box and tow bar (x0's propane tank stands by it). Pivot: centre.")


def m_dish(ctx, M):
    b = B(441, step=0.5)
    for s in (-1, 1):                                                                            # ballast sled
        bx(b, (-0.7, s * 0.55 - 0.05, 0), (0.7, s * 0.55 + 0.05, 0.10), "galv", ch=0.004, pin=False)
        for xx in (-0.45, 0.0, 0.45):
            bx(b, (xx - 0.2, s * 0.55 - 0.2, 0.10), (xx + 0.2, s * 0.55 + 0.2, 0.18), "conc", ch=0.01, pin=False)
    tube(b, (0, 0, 0.0), (0, 0, 1.3), "galv", 0.05)
    for s in (-1, 1):
        tube(b, (0, s * 0.55, 0.10), (0, 0, 0.9), "galv", 0.03)
    dsh = geo.revolve([(0.0, 0.0), (0.25, 0.012), (0.5, 0.05), (0.62, 0.08), (0.62, 0.10), (0.5, 0.075), (0.25, 0.04), (0.0, 0.03)], 32)
    geo.transform(dsh, loc=(0.10, 0, 1.40), rot=(0, 70, 0))
    b.absorb(dsh, "hvac")
    tube(b, (0.10, 0, 1.40), (0.70, 0, 1.55), "galv", 0.03)
    bx(b, (0.66, -0.06, 1.50), (0.80, 0.06, 1.62), "plate", ch=0.005, pin=False)
    return done(ctx, b, "SM_Roof_Dish", M, ground=True, expect_size=(None, None, None),
                notes="Satellite dish 1.25 m on a ballasted sled (non-penetrating mount). Pivot: centre.")


def m_antenna(ctx, M):
    b = B(451, step=0.6)
    for s in (-1, 1):
        bx(b, (-1.0, s * 1.0 - 0.06, 0), (1.0, s * 1.0 + 0.06, 0.12), "galv", ch=0.004, pin=False)
        bx(b, (s * 1.0 - 0.06, -1.0, 0), (s * 1.0 + 0.06, 1.0, 0.12), "galv", ch=0.004, pin=False)
    for (xx, yy) in ((-0.7, -0.7), (0.7, -0.7), (-0.7, 0.7), (0.7, 0.7)):
        bx(b, (xx - 0.2, yy - 0.2, 0.12), (xx + 0.2, yy + 0.2, 0.32), "conc", ch=0.01, pin=False)
    tube(b, (0, 0, 0.12), (0, 0, 4.2), "galv", 0.06)
    for (xx, yy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        tube(b, (xx * 0.95, yy * 0.95, 0.12), (0, 0, 1.6), "galv", 0.03)
    for i, a in enumerate((0, 120, 240)):                                                       # three sector panels
        t = math.radians(a)
        cx, cy = 0.30 * math.cos(t), 0.30 * math.sin(t)
        tube(b, (0, 0, 3.4), (cx, cy, 3.4), "galv", 0.03)
        pan = geo.box((0.10, 0.30, 1.4), bevel=0.01)
        geo.transform(pan, loc=(cx, cy, 2.9), rot=(0, 0, a))
        b.absorb(pan, "hvac")
    bx(b, (0.4, -0.25, 0.12), (0.8, 0.25, 0.9), "grey", ch=0.01, pin=False)                       # radio cabinet
    return done(ctx, b, "SM_Roof_Antenna", M, ground=True, expect_size=(None, None, None),
                notes="Rooftop antenna: a 4.2 m mast on a ballast frame, three sector panels (chunky members, no thin elements), "
                      "a radio cabinet. Pivot: centre.")


def m_worklight(ctx, M):
    """Wall flood: bracket plate, yoke and a lamp housing with its lens (MI_Lamp_Sodium). Pivot: wall plate centre, the
    lamp looks down and out along -Y (the wall is at y = 0, the light goes toward -Y)."""
    b = B(461, step=0.5)
    bx(b, (-0.12, 0.0, -0.15), (0.12, 0.02, 0.15), "black", ch=0.003, pin=False, axis="z")
    bar(b, (0, 0.0, 0), (0, -0.30, 0), 0.06, 0.06, "black", ch=0.004)
    for s in (-1, 1):
        bar(b, (s * 0.20, -0.30, 0.0), (s * 0.20, -0.30, -0.12), 0.06, 0.02 * 3, "black", ch=0.003)
    bar(b, (-0.20, -0.30, 0.0), (0.20, -0.30, 0.0), 0.06, 0.06, "black", ch=0.003)
    hs = geo.box((0.34, 0.16, 0.30), bevel=0.012)
    geo.transform(hs, loc=(0, -0.32, -0.30), rot=(-35, 0, 0))
    b.absorb(hs, "grey")
    ln = geo.box((0.30, 0.012, 0.25), bevel=0.003)
    geo.transform(ln, loc=(0, -0.42, -0.24), rot=(-35, 0, 0))
    b.absorb(ln, "sodium")
    tube(b, (0.10, 0.0, -0.15), (0.10, 0.0, -0.80), "galv", 0.03)
    return done(ctx, b, "SM_Roof_WorkLight", M, ground=False, expect_size=(None, None, None),
                notes="Roof work light (sodium, 2200 K): wall plate, arm, yoke, housing, lens MI_Lamp_Sodium (emissive 1 at night), "
                      "conduit down. The light is a placed spot (midtown.md 11.1). Pivot: wall plate centre, lamp toward -Y.")


# ================================================================================================= stairs and bridges

def m_steelstair(ctx, M):
    """Roof stair L1 to L4: 2.0 m wide, 3.6 m of rise over 4.0 m of run in 18 risers of 0.20 (two per collider step of
    0.40), channel stringers, checker-plate treads with nosings, handrails both sides (6 cm) on posts, the stringers
    standing on the lower roof. Pivot: the head of the flight (upper level, z = 0) on the centre line; it descends along +X."""
    b = B(471, step=0.6)
    n, rise, run, W = 18, 3.6, 4.0, 2.0
    t = run / n
    for s in (-1, 1):                                                                            # solid plate stringers
        y = s * (W / 2 + 0.04)
        p0, p1 = np.array((0.0, y, -0.08)), np.array((run, y, -rise - 0.08))
        d = steel.unit(p1 - p0)
        up = steel.unit(np.cross(d, Y)) * (1 if np.cross(d, Y)[2] > 0 else -1)
        fc.bar(b, p0 - d * 0.12, p1 + d * 0.02, 0.08, 0.28, "galv", up=up, ch=0.004)
        bx(b, (run - 0.02, y - 0.08, -rise), (run + 0.20, y + 0.08, -rise + 0.02), "galv", ch=0.003, pin=False)   # foot plates
        b.rivets([(run + 0.10, y, -rise + 0.02)], Z, "galv", d=0.04, h=0.02, leak=0.0)
    for i in range(n):                                                                           # treads with nosings
        x0, z = i * t, -(i + 1) * rise / n
        bx(b, (x0 - 0.01, -W / 2, z - 0.006), (x0 + t + 0.03, W / 2, z), "plate", ch=0.002, pin=False, axis="y")
        bx(b, (x0 - 0.01, -W / 2, z - 0.06), (x0 + 0.02, W / 2, z), "plate", ch=0.002, pin=False, axis="y")
        bx(b, (x0 + 0.02, -W / 2 + 0.02, z - 0.06), (x0 + t - 0.02, -W / 2 + 0.03, z - 0.006), "galv", pin=False)
    for s in (-1, 1):                                                                            # handrails
        y = s * (W / 2 + 0.06)
        h0, h1 = np.array((-0.2, y, 1.0)), np.array((run + 0.25, y, -rise + 1.0))
        tube(b, h0, h1, "galv", 0.03)
        tube(b, h0 + (0, 0, -0.5), h1 + (0, 0, -0.5), "galv", 0.03)
        for f in np.linspace(0.02, 0.98, 4):
            q = h0 + (h1 - h0) * f
            zf = -rise * min(1.0, max(0.0, (q[0]) / run)) + 0.05
            tube(b, (q[0], y, zf - 0.05), (q[0], y, q[2]), "galv", 0.03)
    name = "SM_Roof_SteelStair_3p6"
    return done(ctx, b, name, M, ground=False, expect_size=(None, None, None),
                notes="Galvanised roof stair (L1 to L4, midtown.md 5.3): 2.0 m wide, 3.6 m rise over 4.0 m run, 18 art risers of "
                      "0.20 over the data's 8 collider steps of 0.40 (one per two), channel stringers, checker treads, rails 6 cm. "
                      "Pivot: the head (upper level) on the centre line, descending +X. L1 turns 0 (east); L2, L3, L4 descend south "
                      "(Blender -Y): rot_z -90.")


def m_stairhead(ctx, M):
    """The steel-stair head bridge over the light court (L1): a 2.4 x 2.0 m checker-plate deck on channels, rails to
    1.2 m both sides with toe boards. Pivot: the west end on the centre line, deck top z = 0, running +X."""
    b = B(481, step=0.6)
    L, W = 2.4, 2.0
    for s in (-1, 1):
        b.prism(steel.channel(0.25, 0.08, 0.011, 0.008), (0, s * W / 2, -0.25), -Y if s > 0 else Y, Z, (L, 0, 0), "galv", pstep=9.0)
    for xx in np.linspace(0.2, L - 0.2, 4):
        b.prism(steel.channel(0.15, 0.06, 0.009, 0.007), (xx, -W / 2, -0.16), X, Z, (0, W, 0), "galv", pstep=9.0)
    plates(b, 0, L, -W / 2, W / 2, 0.0, 0.008, "plate", n=2)
    for s in (-1, 1):
        rail_run(b, np.array((0.0, s * (W / 2 - 0.04), 0.0)), np.array((L, s * (W / 2 - 0.04), 0.0)), "galv", h=1.2, post=1.2)
    return done(ctx, b, "SM_Roof_StairHead_2p4", M, ground=False, expect_size=(L, None, None),
                notes="Head bridge of the steel stair over the light court (L1: x -30..-27.6, z -22..-20, top 21.2): checker deck on "
                      "channels, rails 1.2 m (the playerOnly rails are data). Pivot: west end, centre line, deck top.")


def m_plankbridge(ctx, M):
    """Scaffold-board bridge B to C over the light court (PLANKS): boards on tube ledgers, tube rails 1.2 m and toe
    boards both sides, couplers. Pivot: west end, centre line, deck top z = 0, running +X."""
    b = B(491, step=0.6)
    L, W = 2.6, 2.0
    for s in (-1, 1):
        tube(b, (-0.1, s * (W / 2 - 0.05), -0.08), (L + 0.1, s * (W / 2 - 0.05), -0.08), "galv", 0.03)
    for xx in (0.15, L / 2, L - 0.15):
        tube(b, (xx, -W / 2 - 0.05, -0.13), (xx, W / 2 + 0.05, -0.13), "galv", 0.03)
    nb = 9
    for j in range(nb):                                                                          # boards 0.225 wide, 0.05 thick
        y0 = -W / 2 + j * W / nb
        bx(b, (0.0 + 0.01 * (j % 3), y0 + 0.004, -0.05), (L - 0.01 * ((j + 1) % 3), y0 + W / nb - 0.004, 0.0), "boards", ch=0.004, pin=False, axis="x")
        for xx in (0.03, L - 0.03):
            bx(b, (xx - 0.02, y0 + 0.01, -0.035), (xx + 0.02, y0 + W / nb - 0.01, -0.0), "galv", pin=False)       # end bands
    for s in (-1, 1):
        y = s * (W / 2 + 0.02)
        for xx in (0.05, L - 0.05):
            tube(b, (xx, y, -0.13), (xx, y, 1.2), "galv", 0.03)
        tube(b, (0, y, 1.2), (L, y, 1.2), "galv", 0.03)
        tube(b, (0, y, 0.6), (L, y, 0.6), "galv", 0.03)
        bx(b, (0, y - 0.015, 0.0), (L, y + 0.015, 0.15), "boards", ch=0.003, pin=False, axis="x")
        for xx in (0.05, L - 0.05):                                                              # couplers
            for zz in (0.6, 1.2):
                bx(b, (xx - 0.05, y - 0.05, zz - 0.04), (xx + 0.05, y + 0.05, zz + 0.04), "galv", ch=0.01, pin=False)
    return done(ctx, b, "SM_Roof_PlankBridge_2p6x2", M, ground=False, expect_size=(None, None, None),
                notes="Scaffold-board bridge (PLANKS, B to C over the light court, x -30.3..-27.7, z -10..-8, top 17.6): 9 boards on "
                      "tube ledgers, tube rails 1.2 m, toe boards, couplers. Pivot: west end, centre line, deck top.")


def m_pipebridge(ctx, M):
    """Steel catwalk E to D (PIPE BRIDGE): channel stringers, a grating deck (texture on plates), rails, two pipes
    carried under the deck on hangers. Pivot: west end, centre line, deck top z = 0, running +X."""
    b = B(501, step=0.6)
    L, W = 2.6, 2.0
    for s in (-1, 1):
        b.prism(steel.channel(0.20, 0.075, 0.010, 0.007), (0, s * W / 2, -0.20), -Y if s > 0 else Y, Z, (L, 0, 0), "black", pstep=9.0)
    plates(b, 0, L, -W / 2 + 0.01, W / 2 - 0.01, 0.0, 0.03, "grate", n=3)
    for s in (-1, 1):
        rail_run(b, np.array((0.0, s * (W / 2 - 0.03), 0.0)), np.array((L, s * (W / 2 - 0.03), 0.0)), "black", h=1.2, post=1.3)
    for yy, r in ((-0.45, 0.10), (0.35, 0.075)):
        tube(b, (-0.3, yy, -0.45), (L + 0.3, yy, -0.45), "grey", r, n=16)
        for xx in (0.4, L - 0.4):
            bar(b, (xx, yy, -0.20), (xx, yy, -0.45 + r), 0.06, 0.06, "black", ch=0.003)
    return done(ctx, b, "SM_Roof_PipeBridge_2p6x2", M, ground=False, expect_size=(None, None, None),
                notes="Steel catwalk (PIPE BRIDGE, E to D, x -30.3..-27.7, z 16..18, top 14.0): channels, grating deck (texture on "
                      "plates), rails 1.2 m, two pipes carried under it. Pivot: west end, centre line, deck top.")


PROPS = [
    lambda c, M: m_deck(c, M, "Gravel"), lambda c, M: m_deck(c, M, "Pavers"),
    lambda c, M: m_parapet(c, M, "Buff", 4), lambda c, M: m_parapet(c, M, "Buff", 1),
    lambda c, M: m_parapet(c, M, "Red", 4), lambda c, M: m_parapet(c, M, "Red", 1),
    m_namepanel,
    lambda c, M: m_tankstand(c, M, 4.0, 3.4), lambda c, M: m_tankstand(c, M, 2.0, 2.6),
    lambda c, M: m_watertank(c, M, 4.6, 5.6, 1.6), lambda c, M: m_watertank(c, M, 3.6, 4.2, 1.2),
    m_bulkhead, m_tankhouse, m_machineroom, m_servicebulkhead,
    lambda c, M: m_hvac(c, M, "L"), lambda c, M: m_hvac(c, M, "M"),
    m_skylight, m_vent, m_chimney, m_tarkettle, m_dish, m_antenna, m_worklight,
    m_steelstair, m_stairhead, m_plankbridge, m_pipebridge,
]
