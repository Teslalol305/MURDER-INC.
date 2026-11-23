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
PALM = np.array(C.srgb("#a7796a"), dtype=np.float32)
KNUCKLE = np.array(C.srgb("#4e3022"), dtype=np.float32)
NAIL = np.array(C.srgb("#b88f7f"), dtype=np.float32)
LUNULA = np.array(C.srgb("#d6b8ab"), dtype=np.float32)
INK = np.array([0.020, 0.026, 0.030], dtype=np.float32)          # healed black ink under brown skin: blue-green black

TATTOO_FILE = os.path.join(paths.out, "ref", "tattoos.json")
DEFAULT_TATTOOS = {"right": [{"text": "RULE", "style": "blackletter"}, {"text": "Inc.", "style": "script"}],
                   "left": [{"text": "XVII", "style": "roman"}, {"text": "IIIXX", "style": "roman"}]}


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
        m = d < best
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


# ------------------------------------------------------------------------------------------------ tattoos


def _font(style, size):
    from PIL import ImageFont
    files = {"blackletter": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
             "script": "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
             "roman": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"}
    try:
        return ImageFont.truetype(files.get(style, files["roman"]), size)
    except OSError:
        return ImageFont.load_default()


def tattoo_chart(side, px_per_m=8000):
    """Ink mask on a chart of the forearm: rows = arc length around the forearm (m, -0.12..0.12, 0 = back of the
    forearm, + toward the radius), columns = height above the wrist (0.04..0.27 m). Returns (img, s0, a0, px/m).
    Lettering after the reference photo: right forearm, near the elbow on the back and radial face, a word in
    narrow blackletter capitals with a script line beside it; left forearm, mid forearm, two rows of Roman
    numerals in serif capitals. Both run along the forearm, read from the elbow toward the wrist."""
    from PIL import Image, ImageDraw, ImageFilter
    spec = DEFAULT_TATTOOS
    if os.path.exists(TATTOO_FILE):
        with open(TATTOO_FILE) as f:
            spec = json.load(f)
    s0, s1, a0, a1 = 0.04, 0.27, -0.12, 0.12
    W, H = int((s1 - s0) * px_per_m), int((a1 - a0) * px_per_m)
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)

    def put(text, style, s_centre, a_centre, height_m, squeeze=1.0, rot=0):
        size = int(height_m * px_per_m)
        f = _font(style, size)
        tw = int(d.textlength(text, font=f)) + size
        tile = Image.new("L", (tw, int(size * 1.6)), 0)
        ImageDraw.Draw(tile).text((size // 2, int(size * 0.2)), text, font=f, fill=255)
        tile = tile.resize((max(1, int(tile.width * squeeze)), tile.height), Image.LANCZOS)
        # columns run toward the wrist = decreasing s: the text reads from the elbow to the wrist
        tile = tile.transpose(Image.ROTATE_180) if rot == 180 else tile
        x = int((s_centre - s0) * px_per_m - tile.width / 2)
        y = int((a_centre - a0) * px_per_m - tile.height / 2)
        img.paste(255, (x, y), tile)

    rows = spec.get(side, [])
    if side == "right":
        for i, r in enumerate(rows[:2]):
            if r.get("style") == "script":
                put(r["text"], "script", 0.170, -0.010, 0.020, 1.0, 180)
            else:
                put(r["text"], "blackletter", 0.185, 0.022, 0.026, 0.62, 180)
    else:
        for i, r in enumerate(rows[:3]):
            put(r["text"], "roman", 0.150 + 0.008 * i, 0.030 - 0.030 * i, 0.019, 0.85, 180)
    # healed ink: spread a little under the skin, uneven take-up
    img = img.filter(ImageFilter.GaussianBlur(px_per_m * 0.00022))
    a = np.asarray(img, dtype=np.float32) / 255.0
    return a, s0, a0, px_per_m


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
    """(bc (n, 3) linear, roughness (n,), height (n,) m) for skin and nail texels at rest positions P."""
    Q, M = _side_frame(R, P, N, side)
    n = len(P)
    # the forearm and upper arm: the first version's patterns (mottling, inner forearm, veins, tendons, pores,
    # creases, hair, elbow) recoloured to his skin
    bc, rough, h = X.skin_texels(R, Q, M)
    bc = bc / X.SKIN[None] * SKIN[None]
    bc *= (1.0 + 0.05 * T.fbm(P, 1 / 0.05, 2, seed=31))[:, None]           # left and right differ
    s, x, y = R.fore_coords(Q)
    u, v, w = hand_coords(R, Q)
    lab, tt, cosd, fd = finger_info(R, Q)
    hand = T.smoothstep(0.035, 0.005, s)                                      # 1 on the hand, 0 up the forearm
    reg = np.rint(region).astype(int)
    # back / palm: by region where the faces say so, softened over the border of the hand
    # the palm side by the faces' region (the border of a hand's palm skin is fairly sharp), softened on the
    # fingers by the angle round each finger; the back of the hand keeps the arm's colour (no seam at the wrist)
    pal = np.where(reg == 2, 1.0, 0.0)
    pal = np.where((lab > 0) & (reg > 0), T.smoothstep(0.25, -0.35, cosd), pal) * hand
    mott = 1.0 + 0.07 * T.fbm(P, 1 / 0.012, 3, seed=32) + 0.04 * T.fbm(P, 1 / 0.003, 2, seed=33)
    bc = bc * (1 - pal)[:, None] + (PALM[None] * mott[:, None]) * pal[:, None]
    rough = rough * (1 - hand) + (0.46 + 0.10 * pal) * hand
    # knuckles: darker, folded skin over the joints on the back of the hand
    for i, f in enumerate(C.FINGERS):
        m = (lab == i + 1)
        if not m.any():
            continue
        js = _joint_ts(R, f)
        dors = T.smoothstep(-0.1, 0.5, cosd[m])
        for j, (jt, k) in enumerate(zip(js[:3], (0.55, 0.85, 0.65))):
            if f == "thumb" and j == 0:
                continue
            dj = tt[m] - jt
            ring = np.exp(-(dj / 0.0055) ** 2) * dors
            dark = ring * k * (0.75 + 0.25 * T.noise(P[m], 1 / 0.004, 40 + j))
            bc[m] = bc[m] * (1 - 0.45 * dark)[:, None] + KNUCKLE[None] * (0.45 * dark)[:, None]
            # wrinkles across the joint, curved toward the tip at the sides
            wr = np.sin((dj + 0.0012 * (1 - cosd[m] ** 2)) / 0.00085 * np.pi + 2 * T.noise(P[m], 1 / 0.003, 50 + j))
            h[m] -= 0.000045 * ring * np.clip(wr, 0, 1) * (1.4 if j == 1 else 1.0)
            # palmar flexion creases: one at the base of the finger, two at the middle joint, one at the end joint
            palm_side = T.smoothstep(0.2, -0.5, cosd[m])
            for off in ((0.0045,) if j == 0 else (-0.0011, 0.0011) if j == 1 else (0.0,)):
                cr = np.exp(-((dj - off - 0.0004 * T.noise(P[m], 1 / 0.006, 60 + j)) / 0.00032) ** 2) * palm_side
                h[m] -= 0.00010 * cr
                bc[m] *= (1 - 0.18 * cr)[:, None]
        # fingerprint ridges on the pad of the last segment, a whorl round the pad's centre
        tip = T.smoothstep(js[2] + 0.004, js[2] + 0.010, tt[m]) * T.smoothstep(0.1, -0.6, cosd[m])
        c = R.chain[f]["P"][2] + (R.chain[f]["P"][3] - R.chain[f]["P"][2]) * 0.55
        rr = np.linalg.norm(Q[m] - c, axis=1)
        ridge = 0.5 + 0.5 * np.sin(rr / 0.00048 * 2 * np.pi + 1.5 * T.noise(P[m], 1 / 0.004, 70 + i))
        h[m] -= 0.000018 * ridge * tip
        rough[m] += 0.05 * tip
        # sparse hair on the back of the first segment
        hs = T.smoothstep(0.003, 0.012, tt[m]) * T.smoothstep(js[1] - 0.004, js[1] - 0.012, tt[m]) * T.smoothstep(0.4, 0.8, cosd[m])
        hair = T.smoothstep(0.62, 0.85, T.noise(np.stack([tt[m] / 0.002, cosd[m] / 0.05, P[m, 2] * 0], 1), 1.0, 80 + i)) * hs
        bc[m] *= (1 - 0.5 * hair)[:, None]
    # metacarpal knuckles (back of the hand) and the hand's dorsal veins
    for f in C.FINGERS[:4]:
        dk = np.linalg.norm(Q - (R.mcp[f] + R.dors * R.chain[f]["r"][0] * 0.9), axis=1)
        k = np.exp(-(dk / 0.008) ** 2) * hand
        bc = bc * (1 - 0.35 * k)[:, None] + KNUCKLE[None] * (0.35 * k)[:, None]
    back = hand * (1 - pal) * (lab == 0)
    for a0, a1 in (((0.060, 0.010), (0.018, -0.006)), ((0.058, -0.014), (0.012, 0.010)), ((0.040, 0.026), (0.004, 0.018)),
                   ((0.030, -0.020), (0.030, 0.022))):
        dv = _poly_dist(u, v, [a0, ((a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2 + 0.004), a1])
        vein = np.exp(-(dv / 0.0013) ** 2) * back
        h += 0.00030 * vein
        bc *= (1 - 0.08 * vein)[:, None]
    # palm creases (thenar, proximal and distal transverse) and the creases of the wrist
    palm = hand * pal * (lab == 0)
    for pts, depth in (([(0.010, -0.010), (0.032, -0.020), (0.055, -0.024), (0.070, -0.020)], 0.00016),
                       ([(0.060, -0.030), (0.064, -0.010), (0.066, 0.008), (0.062, 0.022)], 0.00014),
                       ([(0.075, -0.004), (0.073, 0.012), (0.068, 0.030), (0.064, 0.040)], 0.00013)):
        dc = _poly_dist(u + 0.0006 * T.noise(Q, 1 / 0.01, 90), v, pts)
        cr = np.exp(-(dc / 0.0005) ** 2) * palm
        h -= depth * cr
        bc *= (1 - 0.25 * cr)[:, None]
    fine = T.ridged(np.stack([u / 0.003, v / 0.0045, w * 0], 1), 1.0, seed=91) * palm
    h -= 0.000012 * fine
    for off in (0.000, 0.006):
        wc = np.exp(-((s - 0.003 - off + 0.001 * T.noise(Q, 1 / 0.02, 92)) / 0.0006) ** 2) * T.smoothstep(0.0, -0.5, y / np.maximum(np.hypot(x, y), 1e-6))
        h -= 0.00008 * wc
    # tattoos on the forearms, as healed ink in the skin
    fore = (s > 0.04) & (s < 0.27)
    if fore.any():
        theta = np.arctan2(x[fore], y[fore])             # 0 on the back of the forearm, + toward the radius
        rad = np.hypot(x[fore], y[fore])
        arc = -theta * rad
        ink = np.zeros(fore.sum(), dtype=np.float32)
        for sd, key in ((0, "right"), (1, "left")):
            mm = (side[fore] > 0.5) == bool(sd)
            if mm.any():
                ink[mm] = _sample(charts[key], s[fore][mm], arc[mm])
        ink *= 0.72 + 0.28 * T.fbm(P[fore], 1 / 0.002, 2, seed=95)
        b = bc[fore]
        bc[fore] = b * (1 - 0.82 * ink)[:, None] + INK[None] * (0.82 * ink)[:, None] * (b / SKIN[None]).mean(1, keepdims=True)
        rough[fore] += 0.03 * ink
    # nails: plate over the bed, lighter lunula at the root, whiter free edge, fine lengthwise ridges, glossier
    nail = reg == 3
    if nail.any():
        ln, ttn, _cd, _fd = finger_info(R, Q[nail])
        js_end = np.array([_joint_ts(R, C.FINGERS[max(l - 1, 0)])[2] for l in ln])
        along = ttn - js_end
        L3 = np.array([_joint_ts(R, C.FINGERS[max(l - 1, 0)])[3] - _joint_ts(R, C.FINGERS[max(l - 1, 0)])[2] for l in ln])
        f = np.clip(along / np.maximum(L3, 1e-4), 0, 1.4)
        col = NAIL[None] * (1 + 0.06 * T.fbm(P[nail], 1 / 0.002, 2, seed=96))[:, None]
        lun = T.smoothstep(0.42, 0.30, f)
        col = col * (1 - 0.5 * lun)[:, None] + LUNULA[None] * (0.5 * lun)[:, None]
        edge = T.smoothstep(0.95, 1.08, f)
        col = col * (1 - 0.6 * edge)[:, None] + np.array([0.62, 0.55, 0.50], dtype=np.float32)[None] * (0.6 * edge)[:, None]
        bc[nail] = col
        rough[nail] = 0.22 + 0.06 * T.fbm(P[nail], 1 / 0.003, 2, seed=97)
        Qn = Q[nail]
        ridges = T.noise(np.stack([Qn @ R.lat / 0.00025, Qn @ R.fwd / 0.02, Qn[:, 2] * 0], 1), 1.0, 98)
        h[nail] = 0.000006 * ridges
    return bc.astype(np.float32), np.clip(rough, 0.18, 0.9).astype(np.float32), h.astype(np.float32)
