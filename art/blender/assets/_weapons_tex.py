"""Surface pass of the weapons rebuild (round 1): material definition per part with binary metalness, wear that
follows use, fine detail sized for a 4K display at 30 cm.

Rules every painter here keeps:
  * steel, gold, brass, stainless: metallic 1.0 everywhere, also where worn; only oil, carbon, dirt, wood, polymer
    and paint are 0, and the dirt/carbon masks switch metallic off with a narrow step (no grey 0.3 .. 0.9 band);
  * wear = convex edge x exposure x handling: bright only where something rubs (holster, hand, bolt handle, slide
    stop, magazine insertion), dull everywhere else; no uniform noise scratches, no fingerprint stamps;
  * roughness 0.15 .. 0.6 with breakup; brushed and machined parts carry their direction in the height (normal map)
    and in streaked roughness;
  * carbon and oil collect in recesses, at the muzzle, round the port and the rivets.

The painters take the geometry maps of mi.texpaint (G) and return channels for bake.write_set, like the first-pass
painters in assets/weapons.py, which stay as they were.
"""
import math

import numpy as np

from mi import texpaint as tp
from assets import weapons as W

L = W.L
gauss = W.gauss


def lin(h):
    return W.hexlin(h)


class Surf2(W.Surf):
    """Surf with the round-1 finishes (binary metalness, use-driven wear)."""

    def wear(self, sel, handling, edge_gain=1.0, base_thr=0.95, breakup=0.30, soft=0.16, octave=0):
        """0..1 wear on the texels of sel: convex edges, pushed by handling (0..1 per texel of the whole set)."""
        p = self.p[sel]
        hz = np.clip(handling[sel], 0, 1)
        e = self.convex[sel] * edge_gain
        brk = self.N.fbm(p, 480.0, 3, octave0=70 + octave)
        brk2 = self.N.fbm(p, 70.0, 2, octave0=74 + octave)
        w = tp.smooth(e * (0.25 + 1.35 * hz) + breakup * brk + 0.15 * brk2 - base_thr + 0.55 * hz * hz, 0.0, soft)
        # flats rubbed by the hand or holster go satin-bright without reaching bare steel
        rub = np.clip(hz * (0.55 + 0.45 * self.N.fbm(p, 140.0, 2, octave0=78 + octave)), 0, 1)
        return w, rub

    def steel(self, sel, base, rough, handling, worn_col, worn_rough=0.20, edge_gain=1.0, base_thr=0.95,
              rvar=0.05, cvar=0.04, brushed=None, thin_shift=None, scratch=0.0, octave=0, rub_polish=0.10):
        """Metallic 1.0 steel finish. brushed: None or axis 'X'/'Y'/'Z' (direction of the brushing / machining);
        thin_shift: (colour, amount) where the finish is thin (blued plum-brown, oxide brown)."""
        if not sel.any():
            return np.zeros(0, np.float32)
        p, N = self.p[sel], self.N
        mac = N.fbm(p, 24.0, 3, octave0=80 + octave)
        mic = N.fbm(p, 420.0, 2, octave0=83 + octave)
        col = np.asarray(base, np.float32)[None, :] * (1.0 + cvar * mac[:, None] + 0.5 * cvar * mic[:, None])
        if thin_shift is not None:
            tcol, amt = thin_shift
            thin = tp.smooth(N.fbm(p, 16.0, 3, octave0=86 + octave), 0.15, 0.75) * amt
            col = col + (np.asarray(tcol, np.float32)[None, :] - col) * thin[:, None]
        r = rough + rvar * mac + 0.5 * rvar * mic
        if brushed:
            ax = "XYZ".index(brushed)
            f_line = [26000.0] * 3
            f_line[ax] = 9.0
            f_band = [2400.0] * 3
            f_band[ax] = 14.0
            lines = N.fbm(p, tuple(f_line), 2, octave0=88 + octave)
            bands = N.fbm(p, tuple(f_band), 2, octave0=90 + octave)
            r = r + 0.035 * bands + 0.02 * lines
            col = col * (1.0 + 0.025 * bands[:, None])
            self.h[sel] += 9.0e-7 * lines + 6.0e-7 * bands
        w, rub = self.wear(sel, handling, edge_gain, base_thr, octave=octave)
        wc = np.asarray(worn_col, np.float32)[None, :]
        col = col * (1.0 + 0.22 * rub[:, None])
        col = col + (wc - col) * w[:, None]
        r = r - rub_polish * rub
        r = r + (worn_rough - r) * w
        if scratch > 0:
            hz = handling[sel]
            sc = self.scratches(scratch, sel=sel) * tp.smooth(hz, 0.25, 0.7)
            col = col + (wc - col) * (0.5 * sc)[:, None]
            r = r - 0.06 * sc
            self.h[sel] += -6.0e-6 * sc
        self.bc[sel] = col
        self.rough[sel] = r
        self.metal[sel] = 1.0
        # orange-peel of the finish and fine pitting, a little rounding off where it is worn
        self.h[sel] += 1.6e-6 * N.fbm(p, 2200.0, 2, octave0=92 + octave) - 3.0e-6 * w * (0.5 + 0.5 * mic)
        return w

    def polymer(self, sel, base, rough, handling, var=0.035):
        if not sel.any():
            return
        p, N = self.p[sel], self.N
        v = N.fbm(p, 60.0, 3, octave0=95)
        hz = np.clip(handling[sel], 0, 1)
        self.bc[sel] = np.asarray(base, np.float32)[None, :] * (1 + var * v[:, None]) * (1 + 0.10 * hz[:, None])
        self.rough[sel] = rough + 0.03 * v - 0.13 * hz * (0.6 + 0.4 * N.fbm(p, 200.0, 2, octave0=96))
        self.metal[sel] = 0.0
        self.h[sel] += 2.0e-6 * N.fbm(p, 5000.0, 1, octave0=97)       # moulded micro texture

    def dirt(self, amount=1.0, carbon=None, oil=None, dust_col=None):
        """Dust and dried oil in the recesses, carbon where given; metallic drops to 0 with a narrow step where the
        deposit is thick (no grey half-metal)."""
        p, N = self.p, self.N
        g = tp.smooth(1.0 - self.cav, 0.12, 0.50) * 0.85 + tp.smooth(1.0 - self.ao, 0.35, 0.90) * 0.35
        g = np.clip(g * (0.45 + 0.75 * N.fbm(p, 260.0, 3, octave0=60)) * amount, 0, 1)
        dc = np.asarray(dust_col if dust_col is not None else lin("2a2723"), np.float32)
        self.bc = self.bc + (dc[None, :] - self.bc) * (g * 0.85)[:, None]
        self.rough = self.rough + (0.78 - self.rough) * g
        thick = tp.smooth(g, 0.42, 0.52)
        if carbon is not None:
            c = np.clip(carbon * (0.6 + 0.55 * N.fbm(p, 380.0, 3, octave0=63)), 0, 1)
            self.bc = self.bc + (lin("0c0b0a")[None, :] - self.bc) * c[:, None]
            self.rough = self.rough + (0.62 - self.rough) * c
            thick = np.maximum(thick, tp.smooth(c, 0.45, 0.55))
        if oil is not None:
            o = np.clip(oil * (0.5 + 0.6 * N.fbm(p, 90.0, 2, octave0=66)), 0, 1)
            self.rough = self.rough - 0.12 * o
            self.bc = self.bc * (1 - 0.12 * o)[:, None]
        self.metal = self.metal * (1.0 - thick)

    def checker(self, sel, pitch, depth, angle_deg, border, tip_polish=None):
        """Pyramid checkering on the texels of sel (they must already exclude the border): height and lit tips.
        Returns the tips mask."""
        p = self.p
        a = math.radians(angle_deg)
        u = p[:, 0] * math.cos(a) + p[:, 2] * math.sin(a)
        v = -p[:, 0] * math.sin(a) + p[:, 2] * math.cos(a)
        a1, a2 = (u + v) / pitch, (u - v) / pitch
        f1, f2 = a1 - np.floor(a1) - 0.5, a2 - np.floor(a2) - 0.5
        tri = np.maximum(np.abs(f1), np.abs(f2)) * 2.0                     # 0 at the apex .. 1 at the groove
        fade = tp.smooth(border, 0.0, 0.0006)
        self.h += sel * fade * (-tri * depth)
        tips = sel * fade * tp.smooth(0.35 - tri, 0.0, 0.3)
        groove = sel * fade * tp.smooth(tri, 0.8, 1.0)
        self.bc *= (1.0 + 0.25 * tips - 0.35 * groove)[:, None]
        self.rough += 0.08 * groove
        if tip_polish is not None:
            self.rough -= 0.15 * tips * tip_polish
        return tips

    def checker_uv(self, sel, u, v, pitch, depth, field, fade_w=0.0004, flat=0.15, top_rough=0.70, val_rough=0.85):
        """Diamond checkering on the texels of sel in surface coordinates u, v (metres, arrays over sel): `pitch` is
        the true spacing between neighbouring groove lines (20 LPI = 1.27 mm), `depth` the groove depth, small flat
        tops. field: distance (m) into the checkered field (<= 0: the smooth border). Tops `top_rough`, valleys
        `val_rough`. Returns the top mask (0..1) over sel."""
        if not sel.any():
            return np.zeros(0, np.float32)
        q = pitch * math.sqrt(2.0)
        a1, a2 = (u + v) / q, (u - v) / q
        f1, f2 = a1 - np.floor(a1) - 0.5, a2 - np.floor(a2) - 0.5
        tri = np.maximum(np.abs(f1), np.abs(f2)) * 2.0                  # 0 at the apex .. 1 on the groove line
        hgt = np.clip((1.0 - tri) / (1.0 - flat), 0, 1)                 # flat tops
        fade = tp.smooth(field, 0.0, fade_w)
        self.h[sel] += fade * (hgt - 1.0) * depth
        rr = top_rough + (val_rough - top_rough) * (1.0 - hgt)
        self.rough[sel] = self.rough[sel] * (1 - fade) + rr * fade
        self.bc[sel] *= (1.0 + fade * (0.10 * tp.smooth(hgt, 0.85, 1.0) - 0.30 * tp.smooth(1.0 - hgt, 0.5, 1.0)))[:, None]
        return (tp.smooth(hgt, 0.85, 1.0) * fade).astype(np.float32)

    def brushed_stainless(self, sel, base, handling, polish, octave=0):
        """Brushed stainless along X: colour within about 1.5 % (no clouds), roughness 0.30-0.38 carried by a fine
        longitudinal grain, edges polished by wear (polish 0..1 -> roughness 0.17, brighter), holster scuffs."""
        if not sel.any():
            return
        p, N = self.p[sel], self.N
        streak = N.fbm(p, (5.0, 700.0, 700.0), 3, octave0=200 + octave)
        grain = N.fbm(p, (10.0, 12000.0, 12000.0), 2, octave0=203 + octave)
        col = np.asarray(base, np.float32)[None, :] * (1.0 + 0.010 * streak[:, None] + 0.005 * grain[:, None])
        r = 0.34 + 0.022 * streak + 0.016 * grain
        self.h[sel] += 2.5e-7 * grain + 2.5e-7 * streak
        hz = np.clip(handling[sel], 0, 1)
        pe = np.clip(polish[sel], 0, 1)
        sc = self.scratches(0.55, sel=sel, freq_across=2400.0) * tp.smooth(hz, 0.30, 0.85)
        col = col * (1.0 + 0.09 * pe[:, None] + 0.03 * hz[:, None] + 0.07 * sc[:, None])
        r = r + (0.17 - r) * pe - 0.05 * hz - 0.05 * sc
        self.h[sel] -= 2.5e-6 * sc
        self.bc[sel] = col
        self.rough[sel] = np.clip(r, 0.12, 0.5)
        self.metal[sel] = 1.0

    def stipple(self, sel, size, depth):
        if not sel.any():
            return
        p = self.p[sel]
        _id, d = self.N.cells(p, size, 0.85, octave=40)
        pit = tp.smooth(0.55 - d, 0.0, 0.35)
        self.h[sel] += -depth * pit + 0.25 * depth * self.N.fbm(p, 1.0 / size * 1.7, 1, octave0=41)
        self.rough[sel] += 0.05 * pit
        self.bc[sel] *= (1.0 - 0.12 * pit)[:, None]


# ================================================================================================= NINE

def nine_handling(p, n):
    """Holster and hand contact on the NINE (0..1), round 2 geometry."""
    W_ = np.zeros(len(p), np.float32)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    slide = (z > -0.0136) & (x > -0.001)
    # holster: slide nose and its front corners, the top radii, the dust-cover nose, guard front, tang tip
    W_ += slide * tp.smooth(x, 0.165, 0.196) * 0.9
    W_ += slide * tp.smooth(z, 0.0080, 0.0118) * 0.35
    W_ += (z < -0.0136) * (z > -0.027) * tp.smooth(x, 0.176, 0.196) * 0.9
    W_ += (x > 0.119) * (z < -0.026) * (z > -0.073) * tp.smooth(x, 0.122, 0.130) * 0.85
    W_ += gauss(p, (0.112, 0.0, -0.0715), 0.012, 0.55) * (z < -0.068)                  # guard bottom on the holster
    W_ += gauss(p, (-0.031, 0.0, -0.0133), 0.0065, 0.95)                                # beavertail tip
    W_ += gauss(p, (0.186, 0.0, 0.016), 0.006, 0.7) + gauss(p, (0.012, 0.0, 0.016), 0.007, 0.5)   # sights
    # hands: racking at the serrations, slide stop and safety pads, magazine button, takedown lever
    W_ += (np.abs(y) > 0.0115) * (x > 0.004) * (x < 0.032) * (z > -0.0125) * (z < 0.0095) * 0.75
    W_ += gauss(p, (0.0645, 0.016, -0.0185), 0.006, 0.95) + gauss(p, (0.026, 0.016, -0.0150), 0.006, 0.95)
    W_ += gauss(p, (0.0625, 0.013, -0.0405), 0.005, 0.85) + gauss(p, (0.108, 0.013, -0.023), 0.004, 0.6)
    W_ += gauss(p, (-0.023, 0.0, 0.0095), 0.0045, 0.9)                                  # hammer thumb face
    # the grip: palm on the right panel, support fingers on the left, web of the hand in the tang's cup,
    # fingers on the front strap; magazine insertion at the butt
    W_ += gauss(p, (0.014, -0.015, -0.078), 0.022, 0.70) * (y < 0)
    W_ += gauss(p, (0.030, 0.015, -0.090), 0.020, 0.50) * (y > 0)
    W_ += gauss(p, (-0.022, 0.0, -0.021), 0.010, 0.75)
    W_ += gauss(p, (-0.025, 0.0, -0.075), 0.030, 0.45) * (x < -0.012)
    W_ += (x > 0.035) * (z < -0.078) * (z > -0.126) * tp.smooth(n[:, 0], 0.3, 0.8) * 0.55
    W_ += (z < -0.1245) * 0.75
    # the slide stop sweeps an arc on the frame under its pad
    r = np.hypot(x - 0.0955, z + 0.0165)
    W_ += (y > 0.0110) * tp.smooth(0.0035 - np.abs(r - 0.033), 0.0, 0.003) * (x < 0.072) * (z < -0.0138) * 0.7
    return np.clip(W_, 0, 1)


def nine_panel_border(S, pol):
    """Distance (m) of each polymer texel from the edge of the side-facing flat of its panel, measured in the side
    projection (per side and per 0.5 mm height band), and from the screw bushings; -1 off the flat."""
    from assets import _weapons_nine as N9
    p, n = S.p, S.n
    d = np.zeros(len(p), np.float32)
    flat = pol & (np.abs(n[:, 1]) > 0.80)
    for side in (-1, 1):
        s = flat & (np.sign(p[:, 1]) == side)
        if not s.any():
            continue
        zb = np.floor(p[:, 2] / 0.0005).astype(np.int64)
        zs = zb[s]
        xs = p[s, 0]
        lo_, hi_ = zs.min(), zs.max()
        k = hi_ - lo_ + 1
        xmin = np.full(k, np.inf)
        xmax = np.full(k, -np.inf)
        np.minimum.at(xmin, zs - lo_, xs)
        np.maximum.at(xmax, zs - lo_, xs)
        ok = np.isfinite(xmin)
        idx = np.arange(k)
        xmin = np.interp(idx, idx[ok], xmin[ok])
        xmax = np.interp(idx, idx[ok], xmax[ok])
        ker = np.ones(5) / 5
        xmin = np.convolve(np.pad(xmin, 2, mode="edge"), ker, "valid")
        xmax = np.convolve(np.pad(xmax, 2, mode="edge"), ker, "valid")
        j = np.clip(zb - lo_, 0, k - 1)
        zt, zbot = (lo_ + k) * 0.0005, lo_ * 0.0005
        dd = np.minimum.reduce([p[:, 0] - xmin[j], xmax[j] - p[:, 0], zt - p[:, 2], p[:, 2] - zbot])
        d = np.where(s, dd, d)
    for x, z in N9.SCREWS:
        d = np.minimum(d, np.hypot(p[:, 0] - x, p[:, 2] - z) - 0.0040)
    return np.where(flat, d, -1.0)


def paint_nine(G):
    S = Surf2(G, 202)
    p, n, N = S.p, S.n, S.N
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    hz = nine_handling(p, n)
    # ---- brushed stainless slide: #aeb1b6, grain along X, edges polished by wear
    st = S.sel(W.STAINLESS)
    crest = np.zeros(len(p), np.float32)
    for sgn in (1, -1):
        c45 = (n[:, 1] * sgn * 0.7071 + n[:, 2] * 0.7071)
        crest = np.maximum(crest, tp.smooth(c45, 0.9935, 0.9985))           # crest line of the 3 mm top radii
    nose = tp.smooth(x, 0.1832, 0.1845) * (np.abs(n[:, 0]) > 0.2) * tp.smooth(S.convex, 0.25, 0.7)
    polish = np.clip(tp.smooth(S.convex, 0.55, 0.95) + crest * (z > 0.006) + nose, 0, 1)
    S.brushed_stainless(st, lin("aeb1b6"), hz, polish, octave=0)
    # ---- black oxide frame: rough 0.45 +- 0.08 in 20-40 mm blotches, fine sanding marks along X, bare steel
    # only where hand and holster rub
    frame = S.sel(W.BLACKOX)
    S.steel(frame, lin("34363b"), 0.45, hz, lin("8a9098"), worn_rough=0.24, thin_shift=(lin("3a3532"), 0.25),
            rvar=0.08, cvar=0.03, octave=3, base_thr=0.90, rub_polish=0.12)
    if frame.any():
        q = p[frame]
        sand = N.fbm(q, (60.0, 9000.0, 9000.0), 2, octave0=210)
        S.h[frame] += 5e-7 * sand * (np.abs(n[frame, 1]) > 0.6)
        S.rough[frame] += 0.025 * sand
    # small parts: dark steel, wear on the pads
    S.steel(S.sel(W.DARK), lin("3c3e43"), 0.40, hz, lin("8a9098"), worn_rough=0.22, octave=6, base_thr=0.92)
    # polished barrel, hood and guide rod: #bbbec4 at 0.12, lathe rings
    pol_s = S.sel(W.POLISHED)
    S.steel(pol_s, lin("bbbec4"), 0.12, hz * 0.3, lin("d6d9de"), worn_rough=0.10, rvar=0.012, cvar=0.008, octave=9,
            base_thr=1.2)
    if pol_s.any():
        q = p[pol_s]
        S.h[pol_s] += 4.0e-7 * N.fbm(q, (30000.0, 10.0, 10.0), 2, octave0=100)
        S.rough[pol_s] += 0.015 * N.fbm(q, (3000.0, 12.0, 12.0), 2, octave0=102)
    # gold trigger
    gold = S.sel(W.GOLD)
    if gold.any():
        S.bc[gold] = lin("e7b53a")[None, :] * (1 + 0.012 * N.fbm(p[gold], 40.0, 2, octave0=104)[:, None])
        S.rough[gold] = 0.18 + 0.02 * N.fbm(p[gold], 300.0, 2, octave0=105) - 0.03 * S.convex[gold]
        S.metal[gold] = 1.0
        S.h[gold] += 3e-5 * (n[gold, 0] > 0.5) * np.sin(p[gold, 2] / 0.0009 * 2 * math.pi)
    # ---- grip panels: polymer #1c1c1f, 2.5 mm smooth border at 0.5, 20 LPI checkering 0.45 mm deep (tops 0.7,
    # valleys 0.85), screws in bushings excluded; polished where the palm and the web sit
    pol = S.sel(W.POLYMER)
    S.polymer(pol, lin("1c1c1f"), 0.50, hz * 0.6)
    bd = nine_panel_border(S, pol)
    chk = pol & (bd > 0.0)
    if chk.any():
        tops = S.checker_uv(chk, p[chk, 0], p[chk, 2], 0.00127, 4.5e-4, bd[chk] - 0.0025)
        S.rough[chk] -= 0.14 * hz[chk] * tops
        S.bc[chk] *= (1.0 + 0.10 * hz[chk] * tops)[:, None]
    # ---- front strap: a 30 mm band of 20 LPI checkering (0.4 mm) with a 2 mm smooth border
    fs = frame & (n[:, 0] > 0.45) & (x > 0.035) & (z < -0.080) & (z > -0.1185)
    if fs.any():
        zf = z[fs]
        field = np.minimum.reduce([zf + 0.1170, -0.0850 - zf, 0.0088 - np.abs(y[fs])]) - 0.0020
        S.checker_uv(fs, y[fs], zf, 0.00127, 4.0e-4, field, top_rough=0.55, val_rough=0.75)
    # back strap: fine stipple
    bs = frame & (n[:, 0] < -0.45) & (z < -0.035) & (z > -0.124)
    S.stipple(bs, 0.00055, 5.0e-5)
    # ---- hammer thumb face (30 LPI), rear sight's rear face (40 LPI anti-glare lines)
    dk = S.sel(W.DARK)
    th = dk & (x > -0.0265) & (x < -0.0195) & (z > 0.0078) & (n[:, 2] > 0.35)
    if th.any():
        field = np.minimum.reduce([x[th] + 0.0262, -0.0201 - x[th], 0.0040 - np.abs(y[th])]) - 0.0004
        S.checker_uv(th, x[th], y[th], 0.00085, 1.5e-4, field, top_rough=0.30, val_rough=0.55)
    rsf = dk & (x < 0.0070) & (x > 0.0050) & (z > 0.0128) & (z < 0.0186) & (n[:, 0] < -0.6)
    S.h[rsf] += -6e-5 * np.abs(((z[rsf] / 0.000635) % 1.0) - 0.5) * 2.0
    S.rough[rsf] = 0.55
    # ---- carbon, oil and dust
    rr = np.hypot(y, z)
    carbon = (tp.smooth(x, 0.198, 0.2010) * pol_s * tp.smooth(0.0068 - rr, 0.0, 0.0022) * 0.95          # crown
              + (x > 0.193) * (n[:, 0] > 0.6) * tp.smooth(0.0100 - rr, 0.0, 0.0030) * 0.45                 # slide nose
              + st * gauss(p, (0.106, -0.012, 0.009), 0.013, 0.40) * ((y < -0.006) | (z > 0.009))          # round the port
              + st * (x > 0.084) * (x < 0.128) * (y < 0.005) * tp.smooth(S.convex, 0.2, 0.6) * 0.35 * (z > -0.004)
              + st * (x < 0.006) * (n[:, 0] > 0.5) * 0.6                                                    # breech face
              + pol_s * (x < 0.0650) * (n[:, 0] < -0.5) * tp.smooth(rr, 0.0040, 0.0052) * 0.45)            # chamber edge
    oil = (gauss(p, (0.10, 0.0, -0.0125), 0.05, 0.5) * (np.abs(n[:, 2]) > 0.6)
           + st * (np.abs(y) > 0.0115) * (x > 0.004) * (x < 0.032) * 0.35)                                 # serrations
    keep = {k: getattr(S, k)[pol_s].copy() for k in ("bc", "rough", "metal")}
    S.dirt(0.55, carbon=np.clip(carbon, 0, 1), oil=oil)
    # the polished hood and barrel stay clean except the chamber ring and the crown
    cpol = np.clip(carbon[pol_s], 0, 1)
    for k, v in keep.items():
        cur = getattr(S, k)
        cur[pol_s] = v * (1 - cpol[:, None] if v.ndim == 2 else 1 - cpol) + cur[pol_s] * (cpol[:, None] if v.ndim == 2 else cpol)
    # sights and markings
    S.dots([(0.0060, 0.0045, 0.0160), (0.0060, -0.0045, 0.0160)], 0.00085, "-X")
    S.dots([(0.1832, 0.0, 0.0158)], 0.00080, "-X")
    hood = tp.text_image([("9×19", 256, 256, 120)], 512)
    S.engrave(hood, (0, 1), (0.0985, -0.0054), (0.0108, 0.0108), "+Z", 2.5e-5)
    return S.channels(height_blur=0.35)


def paint_nine_mag(G):
    """Nine magazine: brushed steel body (along the magazine axis), bright insertion scuffs on the body, polished
    gold base pad (#e7b53a at 0.18) worn through to brass at its corners and scuffed on the bottom."""
    S = Surf2(G, 9)
    p, n, N = S.p, S.n, S.N
    a = np.array([0.250, 0.0, 0.968]) / np.linalg.norm([0.250, 0.0, 0.968])
    t = p @ a.astype(np.float32)
    hz = np.clip(tp.smooth(t, -0.045, -0.020) * 0.7 + gauss(p, (0.008, 0.0, -0.135), 0.03, 0.4), 0, 1)
    body = S.sel(W.BLUED)
    S.steel(body, lin("9da1a7"), 0.27, hz, lin("c9cdd2"), worn_rough=0.16, rvar=0.03, cvar=0.02, octave=0)
    if body.any():
        q = p[body]
        al = q @ a.astype(np.float32)
        perp = q[:, 0] * a[2] - q[:, 2] * a[0]
        lines = N.fbm(np.stack([al * 8.0, q[:, 1] * 26000.0, perp * 26000.0], 1), 1.0, 2, octave0=120)
        S.h[body] += 8e-7 * lines
        sc = tp.smooth(N.ridged(np.stack([al * 30.0, q[:, 1] * 1800.0, perp * 1800.0], 1), 1.0, 2, octave0=122), 0.93, 0.99)
        sc *= tp.smooth(np.abs(q[:, 1]), 0.0085, 0.0097) * tp.smooth(N.fbm(q, 60.0, 2, octave0=124), -0.1, 0.4)
        S.bc[body] += (lin("d4d7db") - S.bc[body]) * (0.7 * sc)[:, None]
        S.rough[body] -= 0.08 * sc
    S.steel(S.sel(W.DARK), lin("3c3e43"), 0.42, hz, lin("8a9098"), octave=3)
    gold = S.sel(W.GOLD)
    if gold.any():
        q = p[gold]
        S.bc[gold] = lin("e7b53a")[None, :] * (1 + 0.012 * N.fbm(q, 40.0, 2, octave0=104)[:, None])
        S.rough[gold] = 0.18 + 0.02 * N.fbm(q, 300.0, 2, octave0=105)
        S.metal[gold] = 1.0
        # floor scuffs on the domed bottom (random directions) and wear through at the corners and edges
        bot = tp.smooth(-n[gold, 2], 0.4, 0.8)
        sc = np.maximum(S.scratches(1.0, along="X", sel=gold, freq_across=1800.0),
                        S.scratches(0.8, along="Y", sel=gold, freq_across=1800.0, octave=20)) * bot
        corner = tp.smooth(S.convex[gold] * (0.6 + 0.6 * N.fbm(q, 500.0, 2, octave0=106)), 0.45, 0.8)
        corner = np.maximum(corner, tp.smooth(np.abs(q[:, 0] - 0.008), 0.033, 0.038) * tp.smooth(S.convex[gold], 0.2, 0.5))
        wear = np.clip(corner + 0.6 * sc * tp.smooth(N.fbm(q, 90.0, 2, octave0=107), -0.2, 0.3), 0, 1)
        S.bc[gold] += (lin("b38b3c") - S.bc[gold]) * wear[:, None]
        S.rough[gold] += 0.10 * wear + 0.06 * sc
        S.h[gold] -= 4e-6 * sc
    S.plain(S.sel(W.BORE), lin("040405"), 0.7, 0.0)
    S.steel(S.sel(W.BRASS), lin("caa23d"), 0.26, hz * 0, lin("e2c46a"), worn_rough=0.2, cvar=0.03, octave=6)
    S.steel(S.sel(W.COPPER), lin("b5683a"), 0.28, hz * 0, lin("d08a5a"), worn_rough=0.2, cvar=0.03, octave=8)
    S.steel(S.sel(W.PRIMER), lin("caa23d") * np.array([0.95, 0.9, 0.85], np.float32), 0.32, hz * 0, lin("caa23d"),
            octave=10)
    S.dirt(0.5)
    return S.channels(height_blur=0.4)


# ================================================================================================= CHOPPER

def chopper_handling(p, n):
    """Where the CHOPPER is rubbed (0..1): hands, sling, the bolt handle's path, holster-like contacts on the
    muzzle, sights, cover ribs, hinge and the magazine well."""
    H = np.zeros(len(p), np.float32)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    H += tp.smooth(x, 0.488, 0.4975) * 0.9                                           # muzzle crown and mouth
    H += (x > 0.426) * (x < 0.476) * tp.smooth(np.hypot(y, z), 0.0118, 0.0129) * 0.5  # booster body
    H += (x > 0.035) * (x < 0.061) * (z > 0.026) * 0.75                               # cover ribs
    H += (x > 0.104) * (x < 0.176) * (y < -0.013) * (z > -0.003) * (z < 0.033) * 0.7  # ejection port edges
    H += (x > 0.080) * (x < 0.196) * (y > 0.013) * (z > 0.005) * (z < 0.014) * 0.85   # charging slot: handle path
    H += gauss(p, (0.180, 0.036, 0.0145), 0.010, 0.9)                                # knob
    H += gauss(p, (0.100, 0.020, 0.002), 0.012, 0.9) + gauss(p, (0.055, 0.017, -0.004), 0.030, 0.35)  # selector
    H += gauss(p, (0.022, 0.0, -0.028), 0.016, 0.75)                                 # hinge
    H += (x > 0.150) * (x < 0.232) * (z < -0.033) * (z > -0.046) * 0.7                 # magazine well lips
    H += gauss(p, (0.409, 0.0, 0.060), 0.010, 0.8) + gauss(p, (0.0235, 0.0, 0.052), 0.012, 0.7)  # sight ears
    H += gauss(p, (0.0, 0.0, -0.010), 0.020, 0.55)                                   # rear end
    H += gauss(p, (0.315, 0.0, -0.040), 0.030, 0.6) * (z < -0.030) * (z > -0.050)   # left palm on the handguard
    H += gauss(p, (0.040, -0.016, -0.085), 0.030, 0.7) + gauss(p, (0.110, 0.0, -0.065), 0.018, 0.6)  # grip, trigger
    H += gauss(p, (0.386, -0.025, -0.012), 0.008, 0.8)                               # band lever
    H += (x > 0.234) * (x < 0.338) * (z < -0.050) * 0.20                              # shoulder piece edges
    H += (x > 0.060) * (x < 0.170) * (z > 0.036) * 0.45                               # rail lugs
    H += gauss(p, (0.258, -0.014, 0.019), 0.006, 0.8)                                # retainer lever pad
    return np.clip(H, 0, 1)


def laminate(S, sel, base, ply_axis, grain_axis, handling, palm=None, web=None, octave=0):
    """Laminated wood under varnish: plies 1.2-1.8 mm thick in three alternating red-brown tones (the shape's
    curves cut through them, so the ply lines swirl as contours), grain along grain_axis with open pores, varnish
    0.35-0.5 broken by the pores, polished where a hand rubs, chips to pale raw wood on worn edges."""
    if not sel.any():
        return
    p, N = S.p[sel], S.N
    n = S.n[sel]
    warp = 0.00030 * N.fbm(p, 45.0, 3, octave0=130 + octave) + 0.00012 * N.fbm(p, 260.0, 2, octave0=133 + octave)
    q = p[:, ply_axis] + warp
    s = q / 0.0015 + 0.22 * np.sin(q / 0.0061 * 2 * math.pi)                         # 1.2 .. 1.8 mm plies
    k = np.floor(s).astype(np.int64)
    f = s - np.floor(s)
    tones = np.array([[0.86, 0.80, 0.78], [1.00, 1.00, 1.00], [1.17, 1.08, 0.98]], np.float32)
    jit = N.vals[(k * 37 + 11) & 255] * 0.10 - 0.05
    col = np.asarray(base, np.float32)[None, :] * tones[np.mod(k, 3)] * (1 + jit)[:, None]
    glue = tp.smooth(0.10 - np.minimum(f, 1 - f), 0.0, 0.06)
    fr = [1800.0, 1800.0, 1800.0]
    fr[grain_axis] = 22.0
    grain = N.fbm(p + warp[:, None] * 4, tuple(fr), 3, octave0=136 + octave)
    fr2 = [v * 2.2 for v in fr]
    pores = tp.smooth(N.ridged(p, tuple(fr2), 1, octave0=139 + octave), 0.90, 0.985)
    col = col * (1 + 0.16 * grain[:, None]) * (1 - 0.35 * glue[:, None]) * (1 - 0.22 * pores[:, None])
    # end grain (faces across the grain) and vent walls read darker and drier
    end = tp.smooth(np.abs(n[:, grain_axis]), 0.55, 0.85)
    col = col * (1 - 0.45 * end[:, None])
    hz = np.clip(handling[sel], 0, 1)
    brk = N.fbm(p, 360.0, 3, octave0=142 + octave)
    e = S.convex[sel]
    chip = tp.smooth(e * (0.3 + 1.3 * hz) + 0.40 * brk - 0.92, 0.0, 0.10)
    raw = lin("b08458")
    col = col + (raw[None, :] * (0.9 + 0.2 * grain[:, None]) - col) * chip[:, None]
    r = 0.42 + 0.05 * N.fbm(p, 120.0, 2, octave0=145 + octave) + 0.12 * pores + 0.15 * end
    if palm is not None:
        pm = np.clip(palm[sel], 0, 1)
        r = r + (0.20 - r) * pm * (1 - pores * 0.6)
        col = col * (1 - 0.10 * pm)[:, None]
    if web is not None:
        wb = np.clip(web[sel], 0, 1)
        col = col * (1 - 0.35 * wb)[:, None]
        r = r + 0.08 * wb
    r = r + (0.72 - r) * chip
    S.bc[sel] = col
    S.rough[sel] = r
    S.metal[sel] = 0.0
    S.h[sel] += -2.5e-5 * pores + 4e-6 * grain - 5e-5 * chip * (0.5 + 0.5 * brk) + 1.5e-6 * N.fbm(p, 4500.0, 1, octave0=148 + octave)


def paint_chopper(G):
    """One painter for the three CHOPPER sets (receiver and rear, furniture, front end): every mask is a function
    of the gun-space position, so the sets meet without seams."""
    S = Surf2(G, 101)
    p, n, N = S.p, S.n, S.N
    hz = chopper_handling(p, n)
    blued, bright_edge = lin("5a5e65"), lin("9aa0a8")
    S.steel(S.sel(W.BLUED), blued, 0.42, hz, bright_edge, worn_rough=0.22, thin_shift=(lin("5e5052"), 0.45), rvar=0.06,
            octave=0)
    S.steel(S.sel(W.COVER), lin("53565c"), 0.44, hz, bright_edge, worn_rough=0.22, thin_shift=(lin("5a4f50"), 0.40),
            rvar=0.06, octave=3)
    S.steel(S.sel(W.DARK), lin("3c3e43"), 0.47, hz, bright_edge, worn_rough=0.24, rvar=0.05, octave=6)
    car = S.sel(W.BRIGHT)
    S.steel(car, lin("b1b6bd"), 0.27, np.clip(hz + 0.3, 0, 1), lin("c8ccd2"), worn_rough=0.16, brushed="X", rvar=0.03,
            cvar=0.02, octave=9, rub_polish=0.05)
    if car.any():                                    # machining: fine tool marks across the milled faces
        q = p[car]
        S.h[car] += 1.2e-6 * np.sin(q[:, 0] / 0.00018 * 2 * math.pi) * (np.abs(n[car, 1]) > 0.7)
    wood = S.sel(W.WOOD)
    grip = wood & (p[:, 2] < -0.035) & (p[:, 0] < 0.09)
    hg = wood & ~grip
    palm_l = tp.smooth(0.006 - np.abs(p[:, 0] - 0.315), 0.0, 0.020) * (p[:, 2] < -0.018) * 0.9
    laminate(S, hg, lin("55301c"), 2, 0, hz, palm=palm_l, octave=0)
    palm_r = gauss(p, (0.035, -0.016, -0.090), 0.028, 1.0) * (p[:, 1] < 0.002)
    web = gauss(p, (0.026, 0.0, -0.045), 0.014, 0.8) * (p[:, 0] < 0.034)
    laminate(S, grip, lin("55301c"), 1, 2, hz, palm=palm_r * 0.85, web=web, octave=10)
    # rubber pad of the shoulder piece: moulded ribs across
    pad = S.sel(W.POLYMER)
    if pad.any():
        q = p[pad]
        rib = np.abs(np.sin(q[:, 0] / 0.0024 * math.pi))
        S.bc[pad] = lin("1b1a1a")[None, :] * (1 + 0.05 * N.fbm(q, 90.0, 2, octave0=150)[:, None])
        S.rough[pad] = 0.72 - 0.08 * hz[pad]
        S.metal[pad] = 0.0
        S.h[pad] += -1.6e-4 * tp.smooth(rib, 0.0, 0.35) * (n[pad, 2] < -0.5)
    S.plain(S.sel(W.BORE), lin("050506"), 0.62, 0.0)
    # carbon: inside the booster (black at the throat, fading out to the mouth), gas block front, round the port
    # and on the bolt face; oil on the carrier and in the port
    r = np.hypot(p[:, 1], p[:, 2])
    inside = ((S.n[:, 1] * p[:, 1] + S.n[:, 2] * p[:, 2]) < 0) & (p[:, 0] > 0.43)
    carbon = (inside * (r < 0.0165) * (0.55 + 0.45 * tp.smooth(0.494 - p[:, 0], 0.0, 0.02))
              + tp.smooth(p[:, 0], 0.4955, 0.4975) * tp.smooth(0.0150 - r, 0.0, 0.0012) * 0.6
              + (p[:, 0] > 0.4250) * (p[:, 0] < 0.428) * (S.n[:, 0] > 0.6) * 0.35
              + gauss(p, (0.150, -0.017, 0.012), 0.022, 0.55) * (p[:, 1] < -0.010)
              + (p[:, 0] > 0.2025) * car * (S.n[:, 0] > 0.6) * 0.7)
    oil = gauss(p, (0.150, -0.010, 0.014), 0.035, 0.8) * car + gauss(p, (0.30, 0.0, 0.008), 0.05, 0.3)
    S.dirt(0.9, carbon=np.clip(carbon, 0, 1), oil=oil)
    # sight paint (faintly self-lit): two dots on the rear leaf, a strip on the front post's rear face
    S.dots([(0.0215, 0.0046, 0.0498), (0.0215, -0.0046, 0.0498)], 0.00095, "-X")
    S.dots([(0.4080, 0.0, 0.0527)], (0.00072, 0.0027), "-X")
    # stamped markings: selector positions, a fictional proof mark, a short fictional number
    img = tp.text_image([("S", 128, 70, 120), ("A", 128, 250, 120), ("1", 128, 430, 120)], 512)
    S.engrave(img, (0, 2), (0.1075, -0.0215), (0.0105, 0.0315), "+Y", 6e-5)
    pm = tp.text_image([("✶", 256, 256, 330)], 512)
    S.engrave(pm, (0, 2), (0.2195, -0.0125), (0.0085, 0.0085), "+Y", 5e-5)
    sn = tp.text_image([("MI-87", 256, 256, 140)], 512)
    S.engrave(sn, (0, 2), (0.236, -0.0040), (0.022, 0.022), "+Y", 4e-5)
    kn = S.sel(W.DARK) & (p[:, 1] > 0.031) & (np.abs(p[:, 0] - 0.180) < 0.008) & (np.abs(p[:, 2] - 0.0145) < 0.008)
    ang = np.arctan2(p[:, 2] - 0.0145, p[:, 0] - 0.180)
    knurl = np.sin(ang * 36 + p[:, 1] / 0.0007 * 2 * math.pi) * np.sin(ang * 36 - p[:, 1] / 0.0007 * 2 * math.pi)
    S.h += kn * 2.5e-5 * knurl
    # trigger face serrations
    trg = S.sel(W.DARK) & (np.abs(p[:, 0] - 0.105) < 0.009) & (p[:, 2] < -0.040) & (p[:, 2] > -0.070) & (n[:, 0] < -0.4)
    S.h += trg * 3e-5 * np.sin(p[:, 2] / 0.0010 * 2 * math.pi)
    return S.channels(height_blur=0.4)


def paint_chopper_mag(G):
    """CHOPPER magazine: dull blued body, bright only on the feed lips, the lug and tab and the floor plate edges,
    insertion scuffs at the top of the body; brass and copper rounds."""
    S = Surf2(G, 7)
    p, n, N = S.p, S.n, S.N
    top = tp.smooth(p[:, 2], -0.050, -0.028)
    floor = tp.smooth(-p[:, 2], 0.205, 0.226)
    hz = np.clip(top * 0.85 + floor * 0.7 + gauss(p, (0.29, 0.0, -0.20), 0.05, 0.35), 0, 1)
    body = S.sel(W.BLUED)
    S.steel(body, lin("45484e"), 0.52, hz, lin("9aa0a8"), worn_rough=0.24, thin_shift=(lin("4d4446"), 0.35), rvar=0.05,
            edge_gain=1.1, octave=0)
    if body.any():
        q = p[body]
        sc = tp.smooth(N.ridged(np.stack([q[:, 0] * 400.0, q[:, 1] * 30.0, q[:, 2] * 2500.0], 1), 1.0, 2, octave0=160),
                       0.95, 0.995) * top[body] * (np.abs(n[body, 1]) > 0.6)
        S.bc[body] += (lin("9aa0a8") - S.bc[body]) * (0.6 * sc)[:, None]
        S.rough[body] -= 0.1 * sc
    S.steel(S.sel(W.DARK), lin("3c3e43"), 0.50, hz, lin("9aa0a8"), worn_rough=0.24, octave=3)
    S.plain(S.sel(W.BORE), lin("050506"), 0.7, 0.0)
    S.steel(S.sel(W.BRASS), lin("caa23d"), 0.27, hz * 0, lin("e2c46a"), worn_rough=0.2, cvar=0.03, octave=6)
    S.steel(S.sel(W.COPPER), lin("b5683a"), 0.29, hz * 0, lin("d08a5a"), worn_rough=0.2, cvar=0.03, octave=8)
    S.steel(S.sel(W.PRIMER), lin("caa23d") * np.array([0.95, 0.9, 0.85], np.float32), 0.32, hz * 0, lin("caa23d"),
            octave=10)
    S.dirt(0.8)
    return S.channels(height_blur=0.4)


# ================================================================================================= detail set

DETAIL_SET = "TS_GunDetail_Steel"
DETAIL_TILE_M = 0.02


def detail_set(res=1024, tile=DETAIL_TILE_M, seed=11):
    """Tiling micro-detail for the gun materials (the 4K unique sets stop at ~0.1 mm per texel): periodic band-passed
    noise at 0.2 mm (main) and 0.6 mm (weak) as a tangent-space normal, and a roughness offset in ORM.G
    (0.5 = no change; use rough + (G - 0.5)). Tile 20 mm; in the guns' UV layouts that is a repeat of
    (4096 / density) / 0.02 per UV unit (see the set's meta)."""
    from mi import bake as _bake
    rng = np.random.default_rng(seed)

    def band(f0, bw):
        wn = rng.standard_normal((res, res)).astype(np.float32)
        F = np.fft.rfft2(wn)
        fy = np.fft.fftfreq(res)[:, None] * res
        fx = np.fft.rfftfreq(res)[None, :] * res
        fr = np.sqrt(fx * fx + fy * fy)
        k = np.exp(-0.5 * ((fr - f0) / bw) ** 2)
        a = np.fft.irfft2(F * k, s=(res, res)).astype(np.float32)
        return a / max(float(a.std()), 1e-9)
    f_main = tile / 0.0002
    h = 1.2e-6 * band(f_main, f_main * 0.35) + 0.8e-6 * band(f_main / 3, f_main / 9)
    px = tile / res
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px)
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * px)
    n = np.stack([-dx, -dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    rough = np.clip(0.5 + 0.05 * band(f_main / 2, f_main / 5) + 0.03 * band(f_main / 12, f_main / 30), 0, 1)
    ch = {"bc": np.full((res, res, 3), 0.5, np.float32), "rough": rough.astype(np.float32),
          "metal": np.ones((res, res), np.float32), "ao": np.ones((res, res), np.float32),
          "normal": (n * 0.5 + 0.5).astype(np.float32)}
    return _bake.write_set(DETAIL_SET, ch, meta={
        "kind": "tiling", "tile_m": tile, "authoring": "assets/_weapons_tex.py detail_set (periodic band-passed noise)",
        "use": "detail normal (blend over the unique N) and roughness offset (ORM.G - 0.5) for SK_Chopper and SK_Nine; "
               "repeat per UV unit = (4096 / slot texel density px/m) / tile_m"})
