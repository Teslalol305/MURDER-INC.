"""Texel patterns of SK_RuleArms (used by characters.py): skin and glove, computed per texel from the baked rest
position of the RIGHT arm (the left arm is its mirror and shares the sets). Units: metres; colours linear."""
import numpy as np

from mi import texel as T
from mi import sdf

from . import characters as C


def _lin(h):
    return np.array(C.srgb(h), dtype=np.float32)


SKIN = _lin("#684029")
GLOVE = _lin("#1e1f22")
SUEDE = _lin("#2a2724")
THREAD = _lin("#3c3e43")
RUBBER = _lin("#18181b")


def _angdiff(a, b):
    return (a - b + np.pi) % (2 * np.pi) - np.pi


# ------------------------------------------------------------------------------------------------ skin


VEINS = [  # (base angle in the forearm section (x ulnar, y dorsal), wander, phase, s from, s to, width m)
    (np.radians(150), 0.22, 0.4, 0.035, 0.27, 0.0016),   # cephalic, radial border
    (np.radians(-35), 0.20, 1.7, 0.035, 0.25, 0.0017),   # basilic, ulnar-volar
    (np.radians(-95), 0.16, 2.9, 0.050, 0.22, 0.0013),   # median antebrachial, volar
    (np.radians(70), 0.30, 4.1, 0.040, 0.17, 0.0012),    # dorsal branch
    (np.radians(115), 0.25, 5.3, 0.090, 0.21, 0.0011),   # radial dorsal branch
]


def skin_texels(R, P, N):
    """(bc (n, 3) linear, roughness (n,), height (n,) metres) for skin texels at rest positions P."""
    n = len(P)
    s, x, y = R.fore_coords(P)
    su, xu, yu = R.upper_coords(P)
    rr = np.sqrt(x * x + y * y)
    th = np.arctan2(y, x)
    up = s > R.L + 0.004
    dorsal = np.where(up, xu / np.maximum(np.hypot(xu, yu), 1e-6), y / np.maximum(rr, 1e-6))   # -1..1
    h = np.zeros(n, dtype=np.float32)
    rough = np.full(n, 0.47, dtype=np.float32)
    # colour: mottling, a lighter inner forearm, sparse darker spots
    m1 = T.fbm(P, 1 / 0.030, 3, seed=1)
    m2 = T.fbm(P, 1 / 0.006, 3, seed=2)
    val = 1.0 + 0.10 * m1 + 0.05 * m2 + 0.11 * (0.5 - 0.5 * dorsal)
    bc = SKIN[None] * val[:, None]
    red = 0.05 * T.fbm(P, 1 / 0.018, 2, seed=3)
    bc[:, 0] *= 1 + red
    bc[:, 2] *= 1 - red * 0.5
    spots = T.smoothstep(0.50, 0.72, T.noise(P, 1 / 0.0022, 5)) * T.smoothstep(0.1, 0.5, T.noise(P, 1 / 0.02, 6))
    bc *= (1 - 0.16 * spots)[:, None]
    # elbow: darker, rougher, folded skin over the olecranon
    O = R.E - R.ant * 0.030 + R.bu * 0.004
    dO = np.linalg.norm(P - O, axis=1)
    elbow = T.smoothstep(0.040, 0.012, dO)
    bc *= (1 - 0.18 * elbow)[:, None]
    rough += 0.12 * elbow
    fold = np.sin(dO / 0.0021 * 2 * np.pi + 3 * T.fbm(P, 1 / 0.008, 2, seed=7))
    h += 0.00012 * elbow * fold
    # inner elbow crease
    cr = np.abs((P - R.E) @ R.bu - 0.004 + 0.002 * T.noise(P, 1 / 0.01, 8)) < 0.0012
    ant = ((P - R.E) @ R.ant) > 0.02
    h -= 0.00018 * (cr & ant)
    # veins and wrist tendons (forearm only)
    fore = (~up) & (s > 0.03)
    for i, (a0, wander, ph, s0, s1, w) in enumerate(VEINS):
        path = a0 + wander * np.sin(s * 17 + ph) + 0.10 * T.noise(np.stack([s * 30, s * 0 + i, s * 0], 1), 1.0, 9)
        d = np.abs(_angdiff(th, path)) * rr
        vis = T.smoothstep(s0, s0 + 0.025, s) * T.smoothstep(s1, s1 - 0.03, s) * fore
        v = np.exp(-(d / w) ** 2) * vis * (0.75 + 0.25 * T.noise(P, 1 / 0.015, 10 + i))
        h += 0.00032 * v
        bc *= (1 - 0.10 * v)[:, None]
        bc[:, 2] *= 1 + 0.06 * v
        rough -= 0.04 * v
    for a0 in (np.radians(-80), np.radians(-105)):
        d = np.abs(_angdiff(th, a0)) * rr
        vis = T.smoothstep(0.035, 0.05, s) * T.smoothstep(0.13, 0.08, s) * (~up)
        h += 0.00028 * np.exp(-(d / 0.0018) ** 2) * vis
    # skin microrelief (polygonal grooves), pores, faint circumferential creases
    f1, f2 = T.cells(P, 1 / 0.0011, 11)
    groove = T.smoothstep(0.12, 0.0, f2 - f1)
    h -= 0.000018 * groove
    pores = T.smoothstep(0.42, 0.78, T.noise(P, 1 / 0.00055, 12))
    pores2 = T.smoothstep(0.55, 0.85, T.noise(P, 1 / 0.0011, 13))
    h -= 0.000030 * pores + 0.000035 * pores2
    rough += 0.04 * pores
    ax = np.where(up[:, None], R.bu[None], R.af[None])
    Q = P + 3.0 * (np.einsum("ij,ij->i", P, ax))[:, None] * ax
    h -= 0.000022 * T.ridged(Q, 1 / 0.004, 14)
    # forearm hair: short dark streaks lying toward the elbow, leaning to the ulnar side
    dens = T.smoothstep(-0.3, 0.7, dorsal) * T.smoothstep(0.03, 0.06, s) * np.where(up, 0.25, 1.0)
    dens *= 0.55 + 0.45 * T.fbm(P, 1 / 0.03, 2, seed=15)
    _, u, _v = R.fore_frame(0.15)
    flow = np.where(up[:, None], R.bu[None], (-R.af + 0.45 * u)[None])
    t = flow - np.einsum("ij,ij->i", flow, N)[:, None] * N
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    b = np.cross(N, t)
    Hq = np.stack([np.einsum("ij,ij->i", P, t) / 0.0045, np.einsum("ij,ij->i", P, b) / 0.00016,
                   np.einsum("ij,ij->i", P, N) / 0.0045], axis=1)
    hair = T.smoothstep(0.50, 0.80, T.noise(Hq, 1.0, 16)) * dens
    bc = bc * (1 - 0.55 * hair)[:, None] + np.array([0.012, 0.008, 0.006], dtype=np.float32) * (0.55 * hair)[:, None]
    rough += 0.16 * hair
    h += 0.00002 * hair
    rough += 0.05 * T.fbm(P, 1 / 0.012, 2, seed=17)
    return bc.astype(np.float32), np.clip(rough, 0.25, 0.9).astype(np.float32), h


# ------------------------------------------------------------------------------------------------ glove


def _stitch_rows(sd, param, offsets, pitch=0.0034, duty=0.62, width=0.00034):
    """Raised stitches along a seam: rows at signed distances `offsets` from the seam, dashes of `duty` along
    `param` (metres). Returns (height, thread mask)."""
    hh = np.zeros_like(sd)
    m = np.zeros_like(sd)
    ph = (param / pitch) % 1.0
    dash = T.smoothstep(0.0, 0.08, ph) * T.smoothstep(duty, duty - 0.08, ph)
    hole = np.exp(-(((ph - duty - 0.5 * (1 - duty)) * pitch) / 0.00035) ** 2)
    for o in offsets:
        prof = np.exp(-((sd - o) / width) ** 2)
        hh += 0.00024 * prof * dash - 0.00010 * prof * hole
        m = np.maximum(m, prof * dash)
    return hh, m


def _welt(sd, half=0.0014, height=0.00038):
    t = np.clip(1 - (sd / half) ** 2, 0, 1)
    return height * t ** 0.7 - 0.00030 * np.exp(-(sd / 0.00022) ** 2)


def glove_texels(R, P, N, slot, label, dors, piece):
    """(bc, roughness, height) for glove texels. slot 0 leather, 1 suede, 2 rubber; label 0 hand / 1..5 finger;
    dors 1 on the back; piece 0 glove, 1 knuckle bar, 2 strap, 3 fingertip pads."""
    n = len(P)
    h = np.zeros(n, dtype=np.float32)
    rough = np.zeros(n, dtype=np.float32)
    bc = np.zeros((n, 3), dtype=np.float32)
    thread = np.zeros(n, dtype=np.float32)
    s, x, y = R.fore_coords(P)
    glove = piece == 0
    leather = glove & ((slot == 0))
    suede = glove & (slot == 1)
    # leather: pebbled grain, crevices darker and rougher, broad soft wrinkles
    f1, f2 = T.cells(P, 1 / 0.00075, 21)
    grain = T.smoothstep(0.0, 0.16, f2 - f1)
    lv = 1.0 + 0.05 * T.fbm(P, 1 / 0.02, 2, seed=22)
    bc_l = GLOVE[None] * (lv * (0.82 + 0.18 * grain))[:, None]
    r_l = 0.40 + 0.14 * (1 - grain) + 0.04 * T.fbm(P, 1 / 0.01, 2, seed=23)
    h_l = 0.000030 * grain + 0.000045 * T.fbm(P, 1 / 0.005, 3, seed=24)
    # suede: short nap, fuzzy and matte
    nap = T.fbm(P, 1 / 0.00035, 3, seed=25)
    bc_s = SUEDE[None] * (1.0 + 0.10 * nap + 0.06 * T.fbm(P, 1 / 0.015, 2, seed=26))[:, None]
    r_s = 0.86 + 0.06 * nap
    h_s = 0.000015 * nap
    # rubber: fine mould stipple
    st = T.noise(P, 1 / 0.00028, 27)
    bc_r = RUBBER[None] * (1.0 + 0.06 * T.fbm(P, 1 / 0.01, 2, seed=28))[:, None]
    r_r = 0.62 + 0.06 * st
    h_r = 0.000012 * st
    bc[:] = np.where(leather[:, None], bc_l, np.where(suede[:, None], bc_s, bc_r))
    rough[:] = np.where(leather, r_l, np.where(suede, r_s, r_r))
    h[:] = np.where(leather, h_l, np.where(suede, h_s, h_r))

    # seams between the back (leather) and the palm (suede): signed distance (+ on the back) and a running length
    sd = np.full(n, 1.0, dtype=np.float32)
    par = np.zeros(n, dtype=np.float32)
    for i, name in enumerate(C.FINGERS):
        m = glove & (label == i + 1)
        if not m.any():
            continue
        r, cosd, t = C.finger_frame_coords(R, name, P[m])
        sd[m] = r * cosd
        par[m] = t
        # compression wrinkles over the joints (back), a crease under each joint (palm)
        Pc = R.chain[name]["P"]
        tj = [0.0, np.linalg.norm(Pc[1] - Pc[0]), np.linalg.norm(Pc[1] - Pc[0]) + np.linalg.norm(Pc[2] - Pc[1])]
        wr = np.zeros(m.sum(), dtype=np.float32)
        warp = 0.0018 * T.fbm(P[m], 1 / 0.004, 2, seed=30 + i) + 0.0012 * cosd
        for j, tjv in enumerate(tj):
            env = np.exp(-((t - tjv) / (0.0050 if j else 0.0035)) ** 2) * T.smoothstep(-0.35, 0.25, cosd)
            wv = np.sin((t - tjv + warp) / 0.0022 * 2 * np.pi)
            wr += env * (np.maximum(wv, 0) ** 1.5 - 0.3)
            crease = np.exp(-((t - tjv - 0.0015) / 0.0007) ** 2) * T.smoothstep(0.1, -0.4, cosd)
            wr -= 0.9 * crease
        h[m] += 0.00030 * wr
        rough[m] += 0.05 * np.clip(-wr, 0, 1)
    hand = glove & (label == 0) & (s <= 0.004)
    q = P[hand] - R.W
    sd[hand] = q @ R.dors + 0.0035
    par[hand] = q @ R.fwd
    cuff = glove & (s > 0.004)
    sd[cuff] = y[cuff]
    par[cuff] = s[cuff]
    h += np.where(glove, _welt(sd), 0)
    sh, sm = _stitch_rows(sd, par, (0.0023, -0.0023))
    h += np.where(glove, sh, 0)
    thread = np.maximum(thread, np.where(glove, sm, 0))

    # raised back panel: stitched round its edge
    hf = np.array([R.fwd, R.lat, R.dors])
    qb = sdf.local(P, R.W + R.fwd * 0.034, hf)
    foot = sdf.rect2(qb[:, 0], qb[:, 1] - 0.003, 0.033, 0.0235, 0.012)
    onback = glove & (label == 0) & (dors > 0.5) & (s <= 0.004)
    perim = np.arctan2(qb[:, 1] - 0.003, qb[:, 0]) * 0.028
    sh, sm = _stitch_rows(foot, perim, (-0.0021,))
    h += np.where(onback, sh, 0)
    thread = np.maximum(thread, np.where(onback, sm, 0))

    # cuff: stitch rows at the bottom, middle and under the rolled edge; padded pillows between them
    ang = np.arctan2(y, x) * 0.030
    for s0 in (0.0075, 0.0225, 0.0365):
        sh, sm = _stitch_rows(s - s0, ang, (0.0,), pitch=0.0032)
        groove = -0.00022 * np.exp(-((s - s0) / 0.0006) ** 2)
        h += np.where(cuff, sh + groove, 0)
        thread = np.maximum(thread, np.where(cuff, sm, 0))
    pillow = np.clip(np.sin(np.clip((s - 0.0075) / 0.015, 0, 2) * np.pi), 0, 1)
    h += np.where(cuff & (s < 0.0365), 0.00035 * pillow, 0)

    # palm creases (suede side): distal, proximal and the thenar arc, plus wrist folds
    if suede.any():
        q = P[suede] - R.W
        a, b = q @ R.fwd, q @ R.lat
        span = float(np.linalg.norm(np.mean(list(R.mcp.values()), axis=0) - R.W))
        lines = [a - (span * 0.80 + 0.006 * b / 0.04), a - (span * 0.62 - 0.004 * b / 0.04),
                 np.hypot(a - 0.020, b + 0.030) - 0.034]
        cr = np.zeros(len(q), dtype=np.float32)
        for L in lines:
            cr += np.exp(-(L / 0.0008) ** 2)
        cr += np.exp(-((a + 0.004) / 0.0010) ** 2) * 0.6
        h[suede] -= 0.00032 * np.clip(cr, 0, 1.3) * (0.7 + 0.3 * T.noise(P[suede], 1 / 0.006, 40))
        bc[suede] *= (1 - 0.18 * np.clip(cr, 0, 1))[:, None]

    # rubber pieces
    kb = piece == 1
    if kb.any():
        mcp = R.mcp
        kl = C._n(mcp["pinky"] - mcp["index"])
        kf = np.array([C._n(np.cross(kl, R.dors)), kl, R.dors])
        qk = sdf.local(P[kb], np.mean(list(mcp.values()), axis=0), kf)
        ft = sdf.rect2(qk[:, 0] + 0.002, qk[:, 1], 0.010, 0.043, 0.008)
        sh, sm = _stitch_rows(ft, qk[:, 1], (-0.0017,), pitch=0.003)
        h[kb] += sh
        thread[kb] = np.maximum(thread[kb], sm)
        dome = np.zeros(kb.sum(), dtype=np.float32)
        for nme in C.FINGERS[:4]:
            c = mcp[nme] + R.dors * (R.chain[nme]["r"][0] + C.GLOVE_T + 0.004)
            dome = np.maximum(dome, T.smoothstep(0.006, 0.0, np.linalg.norm(P[kb] - c, axis=1)))
        bc[kb] *= (1 + 0.35 * dome)[:, None]                     # scuffed, lighter tops
        rough[kb] += 0.08 * dome
    stp = piece == 2
    if stp.any():
        c0, u, v = R.fore_frame(0.020)
        qs = sdf.local(P[stp], c0, np.array([-R.af, u, v]))
        ft = sdf.rect2(qs[:, 0], qs[:, 1] + 0.004, 0.012, 0.020, 0.0045)
        rim = np.exp(-((ft + 0.0018) / 0.0007) ** 2)
        rib = np.sin((qs[:, 0] + qs[:, 1]) / 0.0016 * 2 * np.pi) * (ft < -0.003)
        h[stp] += 0.00025 * rim + 0.00012 * rib
        tab = qs[:, 1] < -0.021
        h[stp] += 0.00015 * np.sin(qs[:, 1] / 0.0012 * 2 * np.pi) * tab
    pad = piece == 3
    if pad.any():
        for i, name in enumerate(C.FINGERS):
            m = pad & (label == i + 1)
            if not m.any():
                continue
            r, cosd, t = C.finger_frame_coords(R, name, P[m])
            ang2 = np.arctan2(np.sqrt(np.maximum(1 - cosd ** 2, 0)), cosd) * r
            h[m] += 0.00013 * np.sin(t / 0.0009 * 2 * np.pi + 0.3 * np.sin(ang2 / 0.003))
            rough[m] += 0.05

    bc = bc * (1 - thread[:, None]) + THREAD[None] * thread[:, None]
    rough = rough * (1 - thread) + 0.74 * thread
    return bc.astype(np.float32), np.clip(rough, 0.2, 0.95).astype(np.float32), h
