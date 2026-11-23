"""Texel patterns of the bare SK_RuleArms (used by rule.py): one 4K set for both arms (the forearm tattoos differ,
so the left arm has its own islands), computed per texel from the baked rest position. Positions of the left arm
are mirrored onto the right arm's rig for the anatomy, the noise uses the true position so the two arms differ.

Regions (face attribute mi_region): 0 arm, 1 back of the hand and fingers, 2 palm and inside of the fingers, 3 nail.
Units: metres; colours linear. Tattoo lettering: art/out/ref/tattoos.json (git-ignored), else the game's name.
"""
import json
import os

import numpy as np

from mi import paths
from mi import texel as T

from . import characters as C
from . import _characters_tex as X

# his skin, measured on the reference sheet under even light (sRGB): back of the forearm, palm, nail bed
SKIN = np.array(C.srgb("#6f4a39"), dtype=np.float32)
PALM = np.array(C.srgb("#a07060"), dtype=np.float32)
KNUCKLE = np.array(C.srgb("#432717"), dtype=np.float32)
# review round 1: one skin albedo for the arms, the head and the body, warmed and deepened toward the photo
# (cheeks #ba633b-#c26d41 and forearms #b66136 under its flash; albedo kept at the photo's hue, r/g 2.1 linear).
# Linear median of the forearm, back of the hand, face; every skin map is graded to it (grade_skin).
# review round 3: deeper and less saturated (was 0.165 / 0.079 / 0.038, R/B 4.3 read orange): R/B 3.0, the
# albedo of deep brown skin under neutral light (the photo's print is graded warm, R/B 6-9 on the forearms)
SKIN_TARGET = np.array([0.115, 0.062, 0.038], dtype=np.float32)
# natural short nails: a pink-brown bed matched to the skin, a faint lunula, a thin off-white free edge
NAIL = SKIN_TARGET * np.array([1.50, 1.42, 1.80], dtype=np.float32)
LUNULA = SKIN_TARGET * np.array([1.85, 1.85, 2.30], dtype=np.float32)
FREE_EDGE = np.array([0.40, 0.33, 0.27], dtype=np.float32)
INK = np.array([0.020, 0.026, 0.030], dtype=np.float32)          # healed black ink under brown skin: blue-green black


def grade_skin(bc, sel, target=SKIN_TARGET, keep_spread=True):
    """Per-channel gain in linear space taking the median of bc[sel] to `target` (n, 3) -> (n, 3); returns the
    gains too. Applied to every skin texel so relative structure (palm, knuckles, mottling) is kept."""
    m = np.median(bc[sel], axis=0)
    k = target / np.maximum(m, 1e-5)
    return bc * k[None], k

TATTOO_FILE = os.path.join(paths.out, "ref", "tattoos.json")
DEFAULT_TATTOOS = {"right": [{"text": "RULE", "style": "roman"}, {"text": "Inc.", "style": "script"}],
                   "left": [{"text": "XVII", "style": "roman"}, {"text": "XXIII", "style": "roman"}]}


def _side_frame(R, P, N, side):
    """Positions and normals in the right arm's frame (the left arm is the mirror image)."""
    if side is None:
        return P, N
    Q, M = P.copy(), N.copy()
    m = side > 0.5
    Q[m, 0] *= -1
    M[m, 0] *= -1
    return Q, M


def hand_coords(R, P):
    """u along the hand from the wrist (m), v across toward the little finger (m), w toward the back (m)."""
    q = P - R.W
    return q @ R.fwd, q @ R.lat, q @ R.dors


def finger_info(R, P):
    """Nearest finger per point: (label 1..5 or 0, distance along the chain t (m), dorsal cosine, joint ts)."""
    best = np.full(len(P), 1e9)
    lab = np.zeros(len(P), dtype=np.int64)
    tt = np.zeros(len(P))
    cd = np.zeros(len(P))
    for i, n in enumerate(C.FINGERS):
        d, cosd, t = C.finger_frame_coords(R, n, P)
        d = d - R.chain[n]["r"][0]
        m = (d < best) & (t > 0.0005)                      # behind the knuckle (chain clipped) is the hand
        best[m], lab[m], tt[m], cd[m] = d[m], i + 1, t[m], cosd[m]
    return lab, tt, cd, best


def _joint_ts(R, n):
    P = R.chain[n]["P"]
    L = np.linalg.norm(np.diff(P, axis=0), axis=1)
    return np.array([0.0, L[0], L[0] + L[1], L.sum()])


def _poly_dist(u, v, pts):
    """Distance in the (u, v) plane to a polyline."""
    pts = np.asarray(pts, dtype=np.float64)
    best = np.full(len(u), 1e9)
    for a, b in zip(pts[:-1], pts[1:]):
        ab = b - a
        t = np.clip(((u - a[0]) * ab[0] + (v - a[1]) * ab[1]) / (ab @ ab), 0, 1)
        d = np.hypot(u - a[0] - t * ab[0], v - a[1] - t * ab[1])
        best = np.minimum(best, d)
    return best


def _vein_sum(R, P):
    """The first version's forearm vein masks (_characters_tex.skin_texels, same formula), summed."""
    s, x, y = R.fore_coords(P)
    rr = np.sqrt(x * x + y * y)
    th = np.arctan2(y, x)
    up = s > R.L + 0.004
    fore = (~up) & (s > 0.03)
    out = np.zeros(len(P), dtype=np.float32)
    for i, (a0, wander, ph, s0, s1, w) in enumerate(X.VEINS):
        path = a0 + wander * np.sin(s * 17 + ph) + 0.10 * T.noise(np.stack([s * 30, s * 0 + i, s * 0], 1), 1.0, 9)
        d = np.abs(X._angdiff(th, path)) * rr
        vis = T.smoothstep(s0, s0 + 0.025, s) * T.smoothstep(s1, s1 - 0.03, s) * fore
        out += (np.exp(-(d / w) ** 2) * vis * (0.75 + 0.25 * T.noise(P, 1 / 0.015, 10 + i))).astype(np.float32)
    return out


# ------------------------------------------------------------------------------------------------ tattoos


FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")


def _font(style, size):
    """Review round 3: a real blackletter (UnifrakturMaguntia), a real script (Pinyon Script) and a bold
    high-contrast serif for the numerals (Old Standard Bold), all SIL Open Font License (art/blender/fonts)."""
    from PIL import ImageFont
    files = {"blackletter": "UnifrakturMaguntia-Book.ttf", "script": "PinyonScript-Regular.ttf",
             "roman": "OldStandard-Bold.ttf"}
    try:
        return ImageFont.truetype(os.path.join(FONTS, files.get(style, files["roman"])), size)
    except OSError:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", size)


def tattoo_chart(side, px_per_m=8000):
    """Ink mask on a chart of the forearm: rows = arc length around the forearm (m, -0.12..0.12, 0 = back of the
    forearm, + toward the radius), columns = height above the wrist (0.04..0.27 m). Returns (img, s0, a0, px/m).

    Hands-and-tattoos pass (after the photo and the r3 review: "both pieces run along the forearm, where the photo's
    lines run across it; the numerals read mirrored; the ink is faded grey"): every line now runs ACROSS the forearm,
    round the back of it from the ulnar to the radial border, the letters' tops toward the elbow (the photo: they
    read for someone facing him). Right forearm, near the elbow: the word in heavy serif capitals 21 mm tall (along
    the arm) and about 7 cm long (round the arm), the script line beside it toward the wrist (16 mm). Left forearm,
    upper third: two rows of bold serif numerals 14 mm tall, 2.6 cm apart along the arm. The left arm is the mirror
    image of the right arm's frame, so its chart is drawn mirrored to read correctly from outside. Healed ink: dense
    blue-black, bled 0.3 mm with a faint halo, slightly ragged edges and uneven take-up (texel noise in skin_texels).
    """
    from PIL import Image, ImageDraw, ImageFilter
    spec = DEFAULT_TATTOOS
    if os.path.exists(TATTOO_FILE):
        with open(TATTOO_FILE) as f:
            spec = json.load(f)
    s0, s1, a0, a1 = 0.04, 0.27, -0.12, 0.12
    W, H = int((s1 - s0) * px_per_m), int((a1 - a0) * px_per_m)
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    mirror = side == "left"

    def put(text, style, s_centre, a_centre, cap_m, squeeze=1.0, max_len=None):
        size = int(cap_m / 0.68 * px_per_m)                  # cap height is about 0.68 of the em
        f = _font(style, size)
        bb = d.textbbox((0, 0), text, font=f)
        tile = Image.new("L", (bb[2] - bb[0] + size // 2, bb[3] - bb[1] + size // 2), 0)
        ImageDraw.Draw(tile).text((size // 4 - bb[0], size // 4 - bb[1]), text, font=f, fill=255)
        tw = int(tile.width * squeeze)
        if max_len and tw > max_len * px_per_m:
            tw = int(max_len * px_per_m)
        tile = tile.resize((max(1, tw), tile.height), Image.LANCZOS)
        # across the arm: the baseline runs round the forearm (+arc, chart rows), the letters' tops toward the
        # elbow (+s, chart columns)
        tile = tile.transpose(Image.ROTATE_270)
        if mirror:
            tile = tile.transpose(Image.FLIP_TOP_BOTTOM)
        x = int((s_centre - s0) * px_per_m - tile.width / 2)
        y = int((a_centre - a0) * px_per_m - tile.height / 2)
        img.paste(255, (x, y), tile)

    rows = spec.get(side, [])
    if side == "right":
        for r in rows[:2]:
            if r.get("style") == "script":
                put(r["text"], "script", 0.168, 0.004, 0.016, 1.0, max_len=0.075)
            else:
                put(r["text"], "roman", 0.203, 0.000, 0.021, 0.96, max_len=0.085)
    else:
        for i, r in enumerate(rows[:3]):
            put(r["text"], "roman", 0.168 + 0.026 * i, 0.004, 0.014, 0.95, max_len=0.065)
    a = np.asarray(img, dtype=np.float32) / 255.0
    # slightly ragged edges (needle work, 0.15 mm), then a 0.3 mm bleed into the dermis and a faint halo
    rng = np.random.default_rng(31 if side == "right" else 32)
    jit = rng.random(a.shape, dtype=np.float32)
    jit = np.asarray(Image.fromarray((jit * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(px_per_m * 0.00025)),
                     dtype=np.float32) / 255.0
    a = np.clip((a - 0.5) * 1.0 + (jit - 0.5) * 0.9 + 0.5, 0, 1)
    base = Image.fromarray((a * 255).astype(np.uint8))
    core = np.asarray(base.filter(ImageFilter.GaussianBlur(px_per_m * 0.00016)), dtype=np.float32) / 255.0
    halo = np.asarray(base.filter(ImageFilter.GaussianBlur(px_per_m * 0.0006)), dtype=np.float32) / 255.0
    a = np.maximum(np.clip((core - 0.5) * 1.6 + 0.5, 0, 1), 0.22 * halo)
    return np.clip(a, 0, 1), s0, a0, px_per_m


def _sample(chart, s, arc):
    img, s0, a0, k = chart
    H, W = img.shape
    x = (s - s0) * k
    y = (arc - a0) * k
    ok = (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1)
    out = np.zeros(len(s), dtype=np.float32)
    xi, yi = np.floor(x[ok]).astype(int), np.floor(y[ok]).astype(int)
    fx, fy = x[ok] - xi, y[ok] - yi
    out[ok] = (img[yi, xi] * (1 - fx) * (1 - fy) + img[yi, xi + 1] * fx * (1 - fy)
               + img[yi + 1, xi] * (1 - fx) * fy + img[yi + 1, xi + 1] * fx * fy)
    return out


# ------------------------------------------------------------------------------------------------ skin


def skin_texels(R, P, N, region, side, charts):
    """(bc (n, 3) linear, roughness (n,), height (n,) m) for skin and nail texels at rest positions P.

    Review round 3 rebuild (the skin read as glossy orange plastic with a stipple normal, dark streaks along the
    forearms, pink palms with a sawtooth edge, ink lines for creases): written here for his skin instead of
    recolouring the first version's patterns.
      colour   one deep brown (graded afterwards to SKIN_TARGET), melanin variation at 4 cm and 8 mm, a lighter
               inner forearm, darker elbows, knuckles and nail folds, a slightly cooler tint over raised veins;
               the palm 15-25 % lighter and warmer, blended over 1-1.5 cm round the palmar border by the
               surface's own direction (no face-region edge)
      relief   skin-line grooves (1.1 mm cells), fine creases across the forearm, soft raised veins on the back of
               the hand and the forearm, knuckle wrinkles, palmar flexion creases and finger pads as forms (not
               lines), fine pores only as a light breakup
      rough    0.55-0.7: drier over knuckles and elbows, cavities rougher, a low-frequency breakup
      hair     short dark hair lying toward the elbow on the back of the forearm, the upper arm, the back of the
               hand and the first finger segments (soft strands at texel scale, not 0.16 mm streaks)
      ink      the tattoos as healed blue-black ink under the skin, bled 0.3-0.5 mm (tattoo_chart)
    """
    Q, M = _side_frame(R, P, N, side)
    n = len(P)
    reg = np.rint(region).astype(int)
    s, x, y = R.fore_coords(Q)
    su, xu, yu = R.upper_coords(Q)
    rr = np.sqrt(x * x + y * y)
    th = np.arctan2(y, x)
    up = s > R.L + 0.004
    dorsal = np.where(up, xu / np.maximum(np.hypot(xu, yu), 1e-6), y / np.maximum(rr, 1e-6))   # -1..1
    u, v, w = hand_coords(R, Q)
    lab, tt, cosd, fd = finger_info(R, Q)
    hand = T.smoothstep(0.035, 0.005, s)                                      # 1 on the hand, 0 up the forearm
    onhand = hand * (reg != 3)
    h = np.zeros(n, dtype=np.float32)

    # ---- colour
    base = SKIN_TARGET / SKIN_TARGET.mean()
    mel = 1.0 + 0.08 * T.fbm(P, 1 / 0.040, 3, seed=201) + 0.035 * T.fbm(P, 1 / 0.008, 2, seed=202)
    bc = base[None] * mel[:, None]
    hue = 0.035 * T.fbm(P, 1 / 0.022, 2, seed=203)                          # a little redder / yellower in places
    bc[:, 0] *= 1 + hue
    bc[:, 2] *= 1 - hue * 0.6
    bc *= (1.0 + 0.09 * (0.5 - 0.5 * dorsal) * (1 - hand))[:, None]          # the inner forearm a little lighter
    O = R.E - R.ant * 0.030 + R.bu * 0.004                                   # elbow: darker, drier, folded
    dO = np.linalg.norm(Q - O, axis=1)
    elbow = T.smoothstep(0.042, 0.012, dO)
    bc *= (1 - 0.20 * elbow)[:, None]
    fold = np.sin(dO / 0.0024 * 2 * np.pi + 3 * T.fbm(P, 1 / 0.008, 2, seed=204))
    h += 0.00014 * elbow * fold
    cr = np.exp(-(((Q - R.E) @ R.bu - 0.004 + 0.002 * T.noise(P, 1 / 0.01, 205)) / 0.0025) ** 2)
    h -= 0.00008 * cr * T.smoothstep(0.01, 0.035, (Q - R.E) @ R.ant)        # inner elbow crease

    # ---- palm: by the surface's own direction against the back of the hand / of the finger
    dv = np.tile(R.dors, (n, 1))
    for i, f in enumerate(C.FINGERS):
        mf = lab == i + 1
        if mf.any():
            # the finger's dorsal direction from the knuckle on (the hand's behind it)
            k = T.smoothstep(0.0, 0.012, tt[mf])[:, None]
            dv[mf] = R.dors[None] * (1 - k) + R.chain[f]["dors"][None] * k
    dv /= np.linalg.norm(dv, axis=1, keepdims=True)
    palmar = -np.einsum("ij,ij->i", M, dv)
    pal = T.smoothstep(-0.50, 0.55, palmar) * T.smoothstep(0.014, -0.004, s) * (reg != 3)
    PALM_K = np.array([1.22, 1.16, 1.07], dtype=np.float32)
    pmott = 1.0 + 0.05 * T.fbm(P, 1 / 0.010, 2, seed=206)
    bc = bc * (1 - pal)[:, None] + (bc * PALM_K[None] * pmott[:, None]) * pal[:, None]

    # ---- knuckles, joints, creases, pads (forms first, colour second)
    KN = np.array([0.64, 0.58, 0.56], dtype=np.float32)                       # darker, a touch redder
    for i, f in enumerate(C.FINGERS):
        m = (lab == i + 1)
        if not m.any():
            continue
        js = _joint_ts(R, f)
        dors_s = T.smoothstep(-0.1, 0.5, cosd[m])
        palm_side = T.smoothstep(0.15, -0.45, cosd[m])
        for j, (jt, k) in enumerate(zip(js[:3], (0.55, 0.85, 0.65))):
            if f == "thumb" and j == 0:
                continue
            dj = tt[m] - jt
            ring = np.exp(-(dj / 0.0060) ** 2) * dors_s
            if j == 0:
                ring *= T.smoothstep(0.0005, 0.006, tt[m])
            dark = ring * k * (0.75 + 0.25 * T.noise(P[m], 1 / 0.004, 240 + j))
            bc[m] = bc[m] * (1 - 0.55 * dark)[:, None] + (bc[m] * KN[None]) * (0.55 * dark)[:, None]
            # knuckle wrinkles: concentric folds across the joint, curved toward the tip at the sides
            wr = np.sin((dj + 0.0013 * (1 - cosd[m] ** 2)) / 0.0011 * np.pi + 2 * T.noise(P[m], 1 / 0.003, 250 + j))
            h[m] -= 0.000075 * ring * np.clip(wr, 0, 1) * (1.3 if j == 1 else 1.0)
            # palmar flexion creases as grooves (one at the base, two at the middle joint, one at the end)
            for off in ((0.0045,) if j == 0 else (-0.0012, 0.0012) if j == 1 else (0.0,)):
                c_ = np.exp(-((dj - off - 0.0004 * T.noise(P[m], 1 / 0.006, 260 + j)) / 0.00055) ** 2) * palm_side
                h[m] -= 0.00018 * c_
                bc[m] *= (1 - 0.08 * c_)[:, None]
        # pads: a soft bulge on the palm side of each segment, the end pad fullest
        for j in range(3):
            if f == "thumb" and j == 0:
                continue
            a_, b_ = js[j], js[j + 1] + (0.004 if j == 2 else 0.0)
            mid, half = (a_ + b_) / 2, (b_ - a_) / 2
            pad = np.clip(1 - ((tt[m] - mid) / max(half, 1e-4)) ** 2, 0, 1) ** 1.5 * palm_side
            h[m] += (0.00045 if j == 2 else 0.00030) * pad
        # fingerprint ridges on the end pad (a whorl), barely there
        tip = T.smoothstep(js[2] + 0.004, js[2] + 0.010, tt[m]) * palm_side
        c0 = R.chain[f]["P"][2] + (R.chain[f]["P"][3] - R.chain[f]["P"][2]) * 0.55
        rr_ = np.linalg.norm(Q[m] - c0, axis=1)
        ridge = 0.5 + 0.5 * np.sin(rr_ / 0.00048 * 2 * np.pi + 1.5 * T.noise(P[m], 1 / 0.004, 270 + i))
        h[m] -= 0.000012 * ridge * tip
    for f in C.FINGERS[:4]:                                                   # metacarpal heads
        dk = np.linalg.norm(Q - (R.mcp[f] + R.dors * R.chain[f]["r"][0] * 0.9), axis=1)
        k = np.exp(-(dk / 0.010) ** 2) * hand * (1 - pal)
        bc = bc * (1 - 0.42 * k)[:, None] + (bc * KN[None]) * (0.42 * k)[:, None]
    # palm creases (thenar, proximal and distal transverse) as soft grooves, and the wrist creases
    palm = hand * pal * (lab == 0)
    for pts, depth in (([(0.010, -0.010), (0.032, -0.020), (0.055, -0.024), (0.070, -0.020)], 0.00026),
                       ([(0.060, -0.030), (0.064, -0.010), (0.066, 0.008), (0.062, 0.022)], 0.00022),
                       ([(0.075, -0.004), (0.073, 0.012), (0.068, 0.030), (0.064, 0.040)], 0.00020)):
        dc = _poly_dist(u + 0.0006 * T.noise(Q, 1 / 0.01, 280), v, pts)
        c_ = np.exp(-(dc / 0.0009) ** 2) * palm
        h -= depth * c_
        bc *= (1 - 0.07 * c_)[:, None]
    # the thenar and hypothenar eminences
    h += 0.0007 * np.exp(-(((u - 0.030) / 0.020) ** 2 + ((v + 0.024) / 0.014) ** 2)) * palm
    h += 0.0005 * np.exp(-(((u - 0.032) / 0.024) ** 2 + ((v - 0.026) / 0.011) ** 2)) * palm
    for off in (0.000, 0.006):
        wc = np.exp(-((s - 0.003 - off + 0.001 * T.noise(Q, 1 / 0.02, 281)) / 0.0008) ** 2) * T.smoothstep(0.0, -0.5, y / np.maximum(np.hypot(x, y), 1e-6))
        h -= 0.00012 * wc

    # ---- veins: soft raised forms with a slight cool shift (no painted lines)
    vein = np.zeros(n, dtype=np.float32)
    back = hand * (1 - pal) * (lab == 0)
    for a0, a1 in (((0.060, 0.010), (0.018, -0.006)), ((0.058, -0.014), (0.012, 0.010)), ((0.040, 0.026), (0.004, 0.018)),
                   ((0.030, -0.020), (0.030, 0.022))):
        dvn = _poly_dist(u + 0.0015 * T.noise(Q, 1 / 0.02, 290), v, [a0, ((a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2 + 0.004), a1])
        vein = np.maximum(vein, np.exp(-(dvn / 0.0032) ** 2) * back * (0.65 + 0.35 * T.noise(Q, 1 / 0.012, 291)))
    fore = (~up) & (s > 0.03)
    for i, (a0, wander, ph, s0, s1, wd) in enumerate(X.VEINS):
        path = a0 + wander * np.sin(s * 17 + ph) + 0.10 * T.noise(np.stack([s * 30, s * 0 + i, s * 0], 1), 1.0, 9)
        d = np.abs(X._angdiff(th, path)) * rr
        vis = T.smoothstep(s0, s0 + 0.025, s) * T.smoothstep(s1, s1 - 0.03, s) * fore
        vein = np.maximum(vein, 0.75 * np.exp(-(d / (wd * 1.5)) ** 2) * vis * (0.6 + 0.4 * T.noise(P, 1 / 0.02, 292 + i)))
    h += 0.00042 * vein
    bc *= (1 - 0.035 * vein)[:, None]
    bc[:, 0] *= 1 - 0.03 * vein
    bc[:, 2] *= 1 + 0.05 * vein

    # ---- microrelief: skin-line grooves, fine creases across the limb, light pores
    f1, f2 = T.cells(P, 1 / 0.0011, 211)
    groove = T.smoothstep(0.14, 0.0, f2 - f1)
    h -= 0.000040 * groove
    ax = np.where(up[:, None], R.bu[None], R.af[None])
    along = np.einsum("ij,ij->i", Q, ax)
    Qc = Q + 2.5 * along[:, None] * ax                                       # creases run round the limb
    crease = T.ridged(Qc, 1 / 0.0045, 212) * (1 - hand * 0.6)
    h -= 0.000035 * crease
    # the forearm's own skin lines: shallow folds across the back of the forearm every 3-4 mm, wandering
    lines = T.ridged(np.stack([along / 0.0035, (th * rr) / 0.03, along * 0], 1), 1.0, 219) * (1 - hand) * (~up)
    h -= 0.000030 * lines * T.smoothstep(-0.3, 0.6, dorsal)
    pores = T.smoothstep(0.50, 0.85, T.noise(P, 1 / 0.00060, 213))
    h -= 0.000012 * pores
    cav = np.clip(0.6 * groove + 0.5 * crease + 0.4 * pores, 0, 1)

    # ---- hair: short strands lying toward the elbow (ulnar lean), soft at texel scale
    dens = T.smoothstep(-0.2, 0.7, dorsal) * T.smoothstep(0.02, 0.06, s) * np.where(up, 0.35, 1.0)
    dens = dens + backh_density(R, Q, lab, tt, cosd, pal, hand)
    dens *= 0.55 + 0.45 * T.fbm(P, 1 / 0.03, 2, seed=215)
    _, uu, _vv = R.fore_frame(0.15)
    flow = np.where(up[:, None], R.bu[None], (-R.af + 0.45 * uu)[None])
    flow = np.where((hand > 0.5)[:, None], -R.fwd[None] * 0.6 + R.lat[None] * 0.4, flow)
    t_ = flow - np.einsum("ij,ij->i", flow, M)[:, None] * M
    t_ /= np.maximum(np.linalg.norm(t_, axis=1, keepdims=True), 1e-9)
    b_ = np.cross(M, t_)
    Hq = np.stack([np.einsum("ij,ij->i", P, t_) / 0.0035, np.einsum("ij,ij->i", P, b_) / 0.00035,
                   np.einsum("ij,ij->i", P, M) / 0.0035], axis=1)
    strand = T.smoothstep(0.46, 0.74, T.noise(Hq, 1.0, 216)) * np.clip(dens, 0, 1)
    HAIR = np.array([0.012, 0.009, 0.007], dtype=np.float32)
    bc = bc * (1 - 0.45 * strand)[:, None] + HAIR[None] * (0.45 * strand)[:, None]
    h += 0.000010 * strand

    # ---- warmth: better-perfused fingertips and knuckles
    warm = onhand * (lab > 0) * T.smoothstep(0.03, 0.06, tt)
    bc[:, 0] *= 1 + 0.07 * warm
    bc[:, 2] *= 1 - 0.04 * warm

    # ---- roughness
    rough = (0.62 + 0.03 * (0.5 - 0.5 * dorsal) * (1 - hand) - 0.03 * hand * (1 - pal) + 0.0 * pal
             + 0.05 * T.fbm(P, 1 / 0.015, 2, seed=217) + 0.08 * elbow + 0.05 * cav - 0.03 * vein + 0.06 * strand)
    tipr = (lab > 0) * T.smoothstep(0.05, 0.07, tt) * pal
    rough -= 0.06 * tipr
    rough = rough.astype(np.float32)

    # ---- tattoos: healed ink under the skin (no extra specular; roughness variation calmed over it)
    fo = (s > 0.04) & (s < 0.27) & (reg != 3)
    if fo.any():
        theta = np.arctan2(x[fo], y[fo])                 # 0 on the back of the forearm, + toward the radius
        rad = np.hypot(x[fo], y[fo])
        arc = -theta * rad
        ink = np.zeros(fo.sum(), dtype=np.float32)
        for sd, key in ((0, "right"), (1, "left")):
            mm = (side[fo] > 0.5) == bool(sd)
            if mm.any():
                ink[mm] = _sample(charts[key], s[fo][mm], arc[mm])
        ink *= 0.88 + 0.12 * T.fbm(P[fo], 1 / 0.003, 2, seed=218)                # uneven take-up
        b = bc[fo]
        lum = (b @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)) / float(base @ np.array([0.2126, 0.7152, 0.0722]))
        inkc = INK_REL[None] * lum[:, None]                                      # ink under this skin's own shade
        bc[fo] = b * (1 - 0.94 * ink)[:, None] + inkc * (0.94 * ink)[:, None]
        rough[fo] = rough[fo] * (1 - 0.5 * ink) + 0.62 * 0.5 * ink

    # ---- nails: a pink-brown bed matched to the skin, faint lunula, thin free edge, fine ridges
    nail = reg == 3
    if nail.any():
        ln, ttn, _cd, _fd = finger_info(R, Q[nail])
        js_end = np.array([_joint_ts(R, C.FINGERS[max(l - 1, 0)])[2] for l in ln])
        alongn = ttn - js_end
        L3 = np.array([_joint_ts(R, C.FINGERS[max(l - 1, 0)])[3] - _joint_ts(R, C.FINGERS[max(l - 1, 0)])[2] for l in ln])
        col = NAIL[None] * (1 + 0.07 * T.fbm(P[nail], 1 / 0.002, 2, seed=96))[:, None]     # nails are not graded
        lun = T.smoothstep(L3 * 0.48, L3 * 0.40, alongn)
        col = col * (1 - 0.35 * lun)[:, None] + LUNULA[None] * (0.35 * lun)[:, None]
        r3 = np.array([R.chain[C.FINGERS[max(l - 1, 0)]]["r"][3] for l in ln])
        tipd = (L3 + 0.78 * r3) - alongn
        edge = T.smoothstep(0.0009, 0.0003, tipd)
        col = col * (1 - 0.8 * edge)[:, None] + FREE_EDGE[None] * (0.8 * edge)[:, None]
        col *= (1 - 0.18 * T.smoothstep(0.35, 0.95, np.abs(_cd)))[:, None]
        bc[nail] = col
        rough[nail] = 0.35 + 0.04 * T.fbm(P[nail], 1 / 0.003, 2, seed=97) + 0.06 * edge
        Qn = Q[nail]
        ridges = T.noise(np.stack([Qn @ R.lat / 0.00025, Qn @ R.fwd / 0.02, Qn[:, 2] * 0], 1), 1.0, 98)
        h[nail] = 0.000006 * ridges
    return bc.astype(np.float32), np.clip(rough, 0.25, 0.85).astype(np.float32), h.astype(np.float32)


# blue-black healed ink relative to the skin's mean, slight green-blue ageing. Hands-and-tattoos pass: the photo's
# ink is about a fifth of the skin's luminance (it read as a faded grey smudge at a third): linear 0.010-0.016
INK_REL = np.array([0.0105, 0.0135, 0.0160], dtype=np.float32) / float(SKIN_TARGET.mean())


def backh_density(R, Q, lab, tt, cosd, pal, hand):
    """Hair density on the back of the hand and the first finger segments."""
    d = hand * (1 - pal) * np.where(lab > 0, T.smoothstep(0.012, 0.004, np.abs(tt - 0.012)) * T.smoothstep(0.3, 0.8, cosd), 0.6)
    return d.astype(np.float32)
