"""STRETCH surfaces: the darkest gun. Near-black oiled walnut (solid straight grain, no laminate), deep blue-black steel,
black rubber, black hard-anodised bipod and irons, a bright bolt carrier.

Every mask is a function of the gun-space position, so the 4K set has no visible seams; wear sits where hands, slings,
the bolt handle and the bipod reach. The painters take the geometry maps of mi.texpaint (G) and return channels for
bake.write_set, like the CHOPPER's and NINE's (assets/_weapons_tex.py, whose Surf2 and blued_sheet are reused).

    walnut      base #2b1c14 +-8 % per growth ring, rings from tilted planes warped into arches along the X grain, pale-brown
                pores as slits along X, satin oil roughness 0.38-0.48 (0.28 where hands rub), dents and crushed corners
    steel       #1d2128 (slightly violet), metallic 1, roughness 0.26-0.42, bare steel only on edges and rubbed flats
    rubber      #141414, roughness 0.85, diamond stipple in the normal map (butt pad, cheek riser, bipod feet)
    anodised    black hard anodise, non-metal base, bare aluminium at the edges (bipod legs, flip-up irons)
    carrier     bright ground steel with surface-grinding marks along X
"""
import math

import numpy as np

from mi import texpaint as tp
from assets import weapons as W
from assets import _weapons_tex as TX

lin = TX.lin
gauss = W.gauss
BLUED, DARK, BRIGHT, WOOD, COVER, BORE, BRASS, POLYMER, COPPER, PRIMER = (W.BLUED, W.DARK, W.BRIGHT, W.WOOD, W.COVER, W.BORE,
                                                                          W.BRASS, W.POLYMER, W.COPPER, W.PRIMER)
RUBBER = 19


class SS(TX.Surf2):
    """Surf2 with the STRETCH's finishes."""

    def diamond(self, sel, u, v, pitch, depth, flat=0.2, top_rough=0.80, val_rough=0.9):
        """Diamond / pyramid stipple on the texels of sel in surface coordinates u, v (m): true groove spacing `pitch`."""
        if not sel.any():
            return
        u, v = u[sel], v[sel]
        q = pitch * math.sqrt(2.0)
        a1, a2 = (u + v) / q, (u - v) / q
        f1, f2 = a1 - np.floor(a1) - 0.5, a2 - np.floor(a2) - 0.5
        tri = np.maximum(np.abs(f1), np.abs(f2)) * 2.0
        hgt = np.clip((1.0 - tri) / (1.0 - flat), 0, 1)
        self.h[sel] += (hgt - 1.0) * depth
        self.rough[sel] = top_rough + (val_rough - top_rough) * (1.0 - hgt)
        self.bc[sel] *= (1.0 + 0.18 * tp.smooth(hgt, 0.85, 1.0) - 0.30 * tp.smooth(1.0 - hgt, 0.5, 1.0))[:, None]


# ================================================================================================= handling

def stretch_handling(p, n):
    """Where the STRETCH is rubbed (0..1): shoulder, cheek, firing hand, support hand, the bolt handle's path, the rail's rear
    half (optics clamp there), muzzle, bipod, controls."""
    H = np.zeros(len(p), np.float32)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    r = np.hypot(y, z)
    H += gauss(p, (-0.248, 0.0, -0.050), 0.050, 0.55)                                  # butt pad: shoulder
    H += gauss(p, (-0.150, 0.0, 0.060), 0.040, 0.80) + gauss(p, (-0.115, 0.0, 0.056), 0.030, 0.6)   # cheek riser
    H += gauss(p, (-0.205, 0.0, -0.098), 0.020, 0.80)                                  # toe, set down on the ground
    H += gauss(p, (-0.060, 0.026, -0.004), 0.050, 0.35) + gauss(p, (-0.060, -0.026, -0.004), 0.050, 0.35)   # wrist: both hands
    H += gauss(p, (0.046, -0.0165, -0.085), 0.026, 0.80) + gauss(p, (0.040, 0.0, -0.045), 0.020, 0.75)     # grip: palm, web
    H += gauss(p, (0.082, 0.0, -0.085), 0.020, 0.55) * (n[:, 0] > 0.3)                # finger grooves
    H += gauss(p, (0.300, 0.0, -0.030), 0.050, 0.70) * (z < -0.015)                    # support hand under the handguard
    H += gauss(p, (0.195, 0.040, 0.015), 0.012, 1.0) + gauss(p, (0.195, 0.030, 0.015), 0.012, 0.9)        # charging knob
    H += (x > 0.085) * (x < 0.208) * (y > 0.018) * (z > 0.008) * (z < 0.022) * 0.9     # its slot: the stem's path
    H += gauss(p, (0.056, 0.0245, -0.010), 0.014, 0.9) + gauss(p, (0.140, 0.0245, -0.014), 0.014, 0.8)    # selector, bolt catch
    H += gauss(p, (0.108, 0.0, -0.062), 0.012, 0.9) * (n[:, 0] > -0.3)                 # trigger face
    H += (x > 0.0) * (x < 0.22) * (z > 0.0455) * 0.75                                  # rail's rear half: optics clamp and slide
    H += (x > 0.22) * (x < 0.546) * (z > 0.0455) * 0.30
    H += (x > 0.2845) * (x < 0.4815) * (z < -0.0325) * (z > -0.0385) * 0.55            # bottom rail
    H += tp.smooth(x, 0.775, 0.790) * 0.95                                            # brake mouth
    H += (x > 0.7149) * tp.smooth(0.0158 - np.abs(r - 0.0155), 0.0, 0.002) * 0.35
    H += gauss(p, (0.505, 0.0, 0.062), 0.012, 0.8) + gauss(p, (0.028, 0.0, 0.066), 0.014, 0.8)             # irons
    H += (x > 0.31) * (x < 0.48) * (z < -0.044) * 0.55                                 # bipod legs
    H += (x > 0.128) * (x < 0.188) * (z < -0.042) * (z > -0.052) * 0.8                 # mag well lips
    H += gauss(p, (0.171, -0.0195, -0.040), 0.008, 0.9)                                # release button
    H += (x > 0.136) * (x < 0.184) * (z < -0.120) * 0.9                                # magazine floor plate
    H += gauss(p, (0.088, 0.0, -0.100), 0.025, 0.6) * (z < -0.092)                     # guard bottom on the ground
    return np.clip(H, 0, 1)


# ================================================================================================= materials

def walnut(S, sel, hz, rub=None, octave=0, grime=None):
    """Near-black oiled walnut from a solid plank: growth-ring planes (tilted 13 deg about X, gently warped), early
    and late wood bands, straight grain streaks along X, pale-brown pores as short slits, satin oil with a hand polish, dents
    and crushed corners. Base about #3a2619 (the brief's #2b1c14 lifted 35 % so the wood still reads as wood in daylight) +-8 % per ring; the figure is carried by ring, streak and pore contrast."""
    if not sel.any():
        return
    p, N = S.p[sel], S.N
    n = S.n[sel]
    warp = 0.0019 * N.fbm(p, (5.0, 16.0, 16.0), 3, octave0=400 + octave) + 0.0006 * N.fbm(p, (28.0, 120.0, 120.0), 2, octave0=403 + octave)
    a = math.radians(13.0)
    f = p[:, 1] * math.cos(a) + p[:, 2] * math.sin(a) + warp
    s_ = f / 0.0032
    k = np.floor(s_).astype(np.int64)
    fr = s_ - np.floor(s_)
    jit = N.vals[(k * 37 + 11 + octave) & 255] * 0.16 - 0.08                      # +-8 % per ring
    ringw = 0.5 + 0.5 * np.sin(2 * math.pi * s_)
    late = tp.smooth(fr, 0.50, 0.92) * tp.smooth(1.0 - fr, 0.0, 0.08)             # the dark latewood line closing each ring
    early = lin("3e291b")
    lateg = lin("24170f")
    gr = N.fbm(p, (6.0, 1300.0, 1300.0), 3, octave0=406 + octave)
    streak = tp.smooth(N.ridged(p, (10.0, 3600.0, 3600.0), 2, octave0=409 + octave), 0.74, 0.94)
    pores = tp.smooth(N.ridged(p, (34.0, 8200.0, 8200.0), 1, octave0=412 + octave), 0.93, 0.992)
    col = early[None, :] * ((1 + jit) * (0.80 + 0.36 * ringw) * (1 + 0.16 * gr))[:, None]
    col = col + (lateg[None, :] - col) * (0.50 * late + 0.34 * streak)[:, None]
    pale = lin("5c4636")
    col = col + (pale[None, :] * (0.85 + 0.3 * gr[:, None]) - col) * (0.30 * pores)[:, None]
    end = tp.smooth(np.abs(n[:, 0]), 0.60, 0.90)                                  # end grain: darker, drier, the oil pooled
    col = col * (1 - 0.28 * end)[:, None]
    hzs = np.clip(hz[sel], 0, 1)
    brk = N.fbm(p, 240.0, 3, octave0=415 + octave)
    e = S.convex[sel]
    worn = tp.smooth(e * (0.45 + 0.9 * hzs) + 0.22 * brk - 0.58, 0.0, 0.18)       # finish rubbed off the edges
    bare = tp.smooth(e * (0.38 + 1.0 * hzs) + 0.25 * brk - 0.95, 0.0, 0.10)       # to pale raw wood
    raw = lin("6a4a31")
    col = col * (1 + 0.14 * worn)[:, None]
    col = col + (raw[None, :] * (0.9 + 0.2 * gr[:, None]) - col) * bare[:, None]
    r = 0.43 + 0.04 * N.fbm(p, 120.0, 2, octave0=418 + octave) + 0.10 * pores + 0.06 * end        # satin oil 0.38 .. 0.48
    r = r + (0.50 - r) * np.clip(worn * 0.7 + bare, 0, 1)
    polish = hzs * (0.55 + 0.45 * tp.smooth(N.fbm(p, 110.0, 2, octave0=419 + octave), -0.3, 0.4))
    r = r + (0.28 - r) * np.clip(polish * (1 - pores) * (1 - bare), 0, 1)                        # hands polish it to 0.28
    col = col * (1 + 0.10 * polish)[:, None]
    if rub is not None:
        rb = np.clip(rub[sel], 0, 1)
        r = r + (0.30 - r) * rb * 0.6
    if grime is not None:
        gm = np.clip(grime[sel], 0, 1) * (0.6 + 0.4 * N.fbm(p, 200.0, 2, octave0=421 + octave))
        col = col * (1 - 0.35 * gm)[:, None]
        r = r + 0.10 * gm
    _id, dd = N.cells(p, 0.011, 0.9, octave=424 + octave)
    dent = tp.smooth(0.26 - dd, 0.0, 0.18) * (_id > 0.88)
    crush = tp.smooth(e * (0.5 + hzs) - 0.75, 0.0, 0.1) * tp.smooth(N.fbm(p, 60.0, 2, octave0=427 + octave), 0.35, 0.6)
    col = col * (1 - 0.14 * dent - 0.16 * crush)[:, None]
    r = r + 0.08 * dent + 0.12 * crush
    S.bc[sel] = col
    S.rough[sel] = np.clip(r, 0.22, 0.62)
    S.metal[sel] = 0.0
    S.h[sel] += (-1.4e-5 * pores - 8e-6 * streak - 5e-6 * late + 3.0e-6 * gr - 4.5e-5 * bare * (0.5 + 0.5 * brk) - 9e-5 * dent
                 - 1.3e-4 * crush + 0.8e-6 * N.fbm(p, 3500.0, 1, octave0=429 + octave))


def rubber(S, sel, hz, octave=0):
    """Black rubber, roughness 0.85, a soft mottle, worn grey and shinier where shoulders and cheek rub."""
    if not sel.any():
        return
    p, N = S.p[sel], S.N
    v = N.fbm(p, 90.0, 3, octave0=440 + octave)
    hzs = np.clip(hz[sel], 0, 1)
    S.bc[sel] = lin("141414")[None, :] * (1 + 0.10 * v[:, None]) * (1 + 0.55 * hzs[:, None] * (0.6 + 0.4 * v[:, None]))
    S.rough[sel] = 0.85 - 0.12 * hzs + 0.03 * v
    S.metal[sel] = 0.0
    S.h[sel] += 2.5e-6 * N.fbm(p, 4200.0, 1, octave0=443 + octave)


def anodised(S, sel, hz, octave=0, edge_gain=1.0):
    """Black hard anodise over aluminium: non-metal base, bare metal only on the worn edges and rubbed flats."""
    if not sel.any():
        return
    p, N = S.p[sel], S.N
    v = N.fbm(p, 200.0, 3, octave0=450 + octave)
    hzs = np.clip(hz[sel], 0, 1)
    brk = N.fbm(p, 800.0, 2, octave0=453 + octave)
    w = tp.smooth(S.convex[sel] * edge_gain * (0.7 + 0.9 * hzs) + 0.18 * brk - 0.62, 0.0, 0.14)
    base = lin("101214")[None, :] * (1 + 0.15 * v[:, None])
    alu = lin("a7acb3")[None, :]
    S.bc[sel] = base + (alu - base) * w[:, None]
    S.rough[sel] = np.where(w > 0.5, 0.32, 0.52 + 0.06 * v - 0.10 * hzs)
    S.metal[sel] = (w > 0.5).astype(np.float32)
    S.h[sel] += 1.5e-6 * N.fbm(p, 2400.0, 2, octave0=456 + octave) - 2.0e-6 * w


def label(text, w_m, h_m, ppm=18000):
    """White-on-black image of a line of text filling a w_m x h_m plane (PIL, DejaVu Sans Bold)."""
    from PIL import Image, ImageDraw, ImageFont
    W_, H_ = int(w_m * ppm), int(h_m * ppm)
    im = Image.new("L", (W_, H_), 0)
    d = ImageDraw.Draw(im)
    size = int(H_ * 0.9)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    while f.getlength(text) > W_ * 0.98 and size > 8:
        size -= 2
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    d.text((W_ / 2, H_ / 2), text, fill=255, font=f, anchor="mm")
    return np.asarray(im, dtype=np.float32) / 255.0


# ================================================================================================= the gun

def paint_stretch(G):
    S = SS(G, 211)
    p, n, N = S.p, S.n, S.N
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    r = np.hypot(y, z)
    hz = stretch_handling(p, n)
    bright_edge = lin("a9aeb6")
    # ---- steel
    bl = S.sel(BLUED)
    gain = np.ones(len(p), np.float32)
    gain += 0.6 * ((x > 0.0) & (x < 0.22) & (z > 0.045))                          # rail's rear half wears bright
    gain += 0.5 * ((x > 0.085) & (x < 0.208) & (y > 0.018) & (z > 0.008) & (z < 0.022))
    gain += 0.6 * (x > 0.775)                                                      # brake mouth
    TX.blued_sheet(S, bl, lin("384050"), hz, bright_edge, octave=0, rough_lo=0.26, rough_hi=0.42, edge_gain=0.62 * gain[bl])
    # ---- bolt carrier and head: bright ground steel
    car = S.sel(BRIGHT)
    if car.any():
        q = p[car]
        nq = n[car]
        g1 = N.fbm(q, (300.0, 16000.0, 16000.0), 2, octave0=330)
        g2 = tp.smooth(N.ridged(q, (140.0, 24000.0, 24000.0), 1, octave0=332), 0.86, 0.98)
        S.bc[car] = lin("b1b6bd")[None, :] * (1.0 + 0.025 * g1[:, None] + 0.04 * g2[:, None])
        S.rough[car] = 0.25 + 0.04 * g1 - 0.05 * g2
        S.metal[car] = 1.0
        S.h[car] += 5e-7 * g1 + 4e-7 * g2
        w_ = tp.smooth(S.convex[car], 0.5, 0.9)
        S.rough[car] += (0.18 - S.rough[car]) * w_
    # ---- walnut: stock, handguard, grip
    wood = S.sel(WOOD)
    stock = wood & (x < 0.004)
    hg = wood & (x > 0.2)
    grip = wood & (x >= 0.004) & (x <= 0.2)
    rubw = np.clip(gauss(p, (-0.150, 0.0, 0.058), 0.05, 0.4) + gauss(p, (0.300, 0.0, -0.030), 0.045, 0.7) * (z < -0.01), 0, 1)
    grime = tp.smooth(x, 0.50, 0.541) * hg
    for part in TX.chunks(stock):
        walnut(S, part, hz, rub=rubw, octave=0, grime=None)
    for part in TX.chunks(hg):
        walnut(S, part, hz, rub=rubw, octave=7, grime=grime)
    for part in TX.chunks(grip):
        walnut(S, part, hz, rub=rubw, octave=14)
    # stippled panel on the grip: both flanks, a dotted field 0.9 mm pitch
    gp = grip & (np.abs(y) > 0.0095) & (z < -0.062) & (z > -0.128)
    if gp.any():
        S.stipple(gp, 0.0009, 9e-5)
    # ---- rubber, anodised
    rub = S.sel(RUBBER)
    rubber(S, rub, hz, octave=0)
    sel_b = rub & (x < -0.20) & (n[:, 0] < -0.45)                                      # butt pad's rear face: diamond stipple
    S.diamond(sel_b, y, z, 0.0016, 2.6e-4)
    sel_c = rub & (x > -0.19) & (x < -0.11) & (n[:, 2] > 0.5)                          # cheek riser's top
    S.diamond(sel_c, x, y, 0.0014, 2.2e-4)
    sel_f = rub & (x < 0.34) & (z < -0.04)                                             # bipod feet: ribs read as rings
    if sel_f.any():
        S.h[sel_f] += -1.5e-4 * (0.5 + 0.5 * np.sin(x[sel_f] / 0.0026 * 2 * math.pi))
    dk = S.sel(DARK)
    anodised(S, dk, hz, octave=0)
    S.plain(S.sel(BORE), lin("050506"), 0.62, 0.0)
    # ---- interior of the receiver: matte parkerised black
    cav = (np.abs(y) < 0.0194) & (z > -0.0292) & (z < 0.0372) & (x > 0.0038) & (x < 0.2098) & bl
    S.bc[cav] = lin("0b0c0e")[None, :]
    S.rough[cav] = 0.62
    S.metal[cav] = 0.0
    well = bl & (np.abs(y) < 0.0132) & (x > 0.130) & (x < 0.184) & (z < -0.031) & (z > -0.0495)
    S.bc[well] = lin("0b0c0e")[None, :]
    S.rough[well] = 0.62
    S.metal[well] = 0.0
    # ---- carbon, oil, grime
    carbon = (tp.smooth(x, 0.786, 0.790) * tp.smooth(0.0158 - r, 0.0, 0.002) * 0.7
              + (x > 0.715) * (x < 0.79) * (r < 0.0160) * 0.35
              + gauss(p, (0.150, -0.024, 0.017), 0.030, 0.55) * (y < -0.017)         # round the ejection port
              + gauss(p, (0.205, 0.0, 0.0), 0.012, 0.6))
    oil = gauss(p, (0.150, 0.0, 0.010), 0.060, 0.6) + gauss(p, (0.140, -0.021, 0.017), 0.040, 0.7) * (y < -0.01)
    S.dirt(1.1, carbon=np.clip(carbon, 0, 1), oil=np.clip(oil, 0, 1))
    S.rough = np.maximum(S.rough, 0.18 * (S.metal > 0.5))
    # ---- markings: stamped on the flanks, invented: MARKSMAN 7.6 / MOD S1 / SAFE SEMI / proof star / M1-3308
    def engrave_left(text, x0, z0, w_m, h_m, depth=7e-5):
        img = label(text, w_m, h_m)[:, ::-1]
        S.engrave(img, (0, 2), (x0, z0), (w_m, h_m), "+Y", depth)

    def engrave_right(text, x0, z0, w_m, h_m, depth=7e-5):
        img = label(text, w_m, h_m)
        S.engrave(img, (0, 2), (x0, z0), (w_m, h_m), "-Y", depth)
    engrave_left("MARKSMAN 7.6", 0.095, 0.0265, 0.064, 0.0058)
    engrave_left("MOD S1", 0.168, 0.0265, 0.030, 0.0058)
    engrave_left("M1-3308", 0.012, -0.0270, 0.036, 0.0050)
    engrave_left("SAFE", 0.0575, -0.0050, 0.0185, 0.0040)           # marks at the lever tip's two positions (rest, +16 deg)
    engrave_left("SEMI", 0.0575, -0.0215, 0.0185, 0.0040)
    engrave_right("MOD S1", 0.040, 0.0250, 0.028, 0.0058)
    engrave_right("M1-3308", 0.040, -0.0265, 0.036, 0.0050)
    star = tp.text_image([("✶", 256, 256, 330)], 512)
    S.engrave(star[:, ::-1], (0, 2), (0.0095, 0.0225), (0.0085, 0.0085), "+Y", 1.5e-4)
    # trigger blade: fine ridges across its face; charging knob knurl is modelled
    trg = bl & (np.abs(x - 0.110) < 0.009) & (z < -0.056) & (z > -0.074) & (n[:, 0] > 0.4) & (np.abs(y) < 0.0035)
    S.h += trg * 3e-5 * np.sin(z / 0.0009 * 2 * math.pi)
    return S.channels(height_blur=0.4)


def paint_stretch_mag(G):
    """Magazine: deep blue-black stamped steel with bright insertion wear at the lips and along the rib edges, black polymer
    floor plate with a worn drag tab, dark follower, brass round and bullet."""
    S = SS(G, 17)
    p, n, N = S.p, S.n, S.N
    top = tp.smooth(p[:, 2], -0.060, -0.030)
    floor = tp.smooth(-p[:, 2], 0.118, 0.131)
    hz = np.clip(top * 0.85 + floor * 0.8 + gauss(p, (0.157, 0.0, -0.085), 0.04, 0.35), 0, 1)
    body = S.sel(BLUED)
    TX.blued_sheet(S, body, lin("384050"), hz, lin("a9aeb6"), octave=0, rough_lo=0.28, rough_hi=0.44, edge_gain=1.0)
    if body.any():
        q = p[body]
        sc = tp.smooth(N.ridged(np.stack([q[:, 0] * 400.0, q[:, 1] * 30.0, q[:, 2] * 2500.0], 1), 1.0, 2, octave0=160), 0.95, 0.995) \
            * top[body] * (np.abs(n[body, 1]) > 0.6)
        pouch = S.scratches(0.9, along="Z", sel=body, freq_across=9000.0, freq_long=40.0, octave=170) * tp.smooth(-q[:, 2], 0.085, 0.11) \
            * (np.abs(n[body, 1]) > 0.6)
        S.bc[body] += (lin("a9aeb6") - S.bc[body]) * (0.6 * sc + 0.45 * pouch)[:, None]
        S.rough[body] -= 0.1 * sc + 0.06 * pouch
        S.h[body] -= 2e-6 * pouch
    S.steel(S.sel(DARK), lin("26292e"), 0.50, np.clip(hz + floor, 0, 1), lin("a9aeb6"), worn_rough=0.24, octave=3)
    pol = S.sel(POLYMER)
    S.polymer(pol, lin("0d0d0e"), 0.72, np.clip(floor + 0.2 * hz, 0, 1))
    S.h[pol] += 0.0
    S.steel(S.sel(BRASS), lin("caa23d"), 0.27, hz * 0, lin("e2c46a"), worn_rough=0.2, cvar=0.03, octave=6)
    S.steel(S.sel(COPPER), lin("b5683a"), 0.29, hz * 0, lin("d08a5a"), worn_rough=0.2, cvar=0.03, octave=8)
    S.steel(S.sel(PRIMER), lin("caa23d") * np.array([0.95, 0.9, 0.85], np.float32), 0.32, hz * 0, lin("caa23d"), octave=10)
    S.plain(S.sel(BORE), lin("050506"), 0.7, 0.0)
    S.dirt(0.9)
    return S.channels(height_blur=0.4)
