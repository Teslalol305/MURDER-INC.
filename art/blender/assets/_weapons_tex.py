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
    """Holster and hand contact on the NINE (0..1)."""
    W_ = np.zeros(len(p), np.float32)
    slide = (p[:, 2] > -0.0135) & (p[:, 0] > -0.002)
    # holster: nose of slide and dust cover, top edges of the slide, sights, guard front, beavertail, rail edges
    W_ += slide * tp.smooth(p[:, 0], 0.160, 0.196) * 0.9
    W_ += slide * tp.smooth(p[:, 2], 0.0075, 0.0115) * 0.55
    W_ += (p[:, 2] < -0.0120) * (p[:, 2] > -0.026) * tp.smooth(p[:, 0], 0.172, 0.196) * 0.9
    W_ += (p[:, 0] > 0.118) * (p[:, 2] < -0.026) * (p[:, 2] > -0.072) * 0.75
    W_ += gauss(p, (-0.031, 0.0, -0.011), 0.008, 0.95)
    W_ += (p[:, 0] > 0.130) * (p[:, 0] < 0.197) * (p[:, 2] < -0.019) * (p[:, 2] > -0.027) * 0.55
    W_ += gauss(p, (0.186, 0.0, 0.016), 0.006, 0.8) + gauss(p, (0.012, 0.0, 0.016), 0.007, 0.6)
    # hands: slide serrations (racking), slide stop and safety pads, magazine button, grip panels at the palm
    W_ += (np.abs(p[:, 1]) > 0.011) * (p[:, 0] > 0.006) * (p[:, 0] < 0.026) * (p[:, 2] > -0.012) * 0.8
    W_ += gauss(p, (0.064, 0.015, -0.0155), 0.007, 0.9) + gauss(p, (0.025, 0.015, -0.011), 0.007, 0.9)
    W_ += gauss(p, (0.0625, 0.012, -0.0405), 0.005, 0.8)
    W_ += gauss(p, (0.014, -0.015, -0.078), 0.022, 0.75) * (p[:, 1] < 0)
    W_ += gauss(p, (0.030, 0.015, -0.090), 0.020, 0.55) * (p[:, 1] > 0)
    W_ += gauss(p, (-0.026, 0.0, -0.070), 0.030, 0.55) * (p[:, 0] < -0.012)          # back strap in the palm
    W_ += gauss(p, (0.026, 0.0, -0.095), 0.030, 0.45) * (p[:, 0] > 0.012) * (p[:, 2] < -0.075)   # fingers on the front strap
    # slide stop's sweep on the frame under its pad (arc about the pivot)
    r = np.hypot(p[:, 0] - 0.0955, p[:, 2] + 0.0165)
    W_ += (p[:, 1] > 0.0110) * tp.smooth(0.004 - np.abs(r - 0.033), 0.0, 0.003) * (p[:, 0] < 0.072) * 0.8
    return np.clip(W_, 0, 1)


def nine_panel_border(S, pol):
    """Distance (m) of each polymer texel from the edge of the side-facing flat of its panel, measured in the side
    projection: per side and per 0.5 mm height band, the x extent of the texels that face sideways."""
    from assets import _weapons_nine as N9
    p, n = S.p, S.n
    d = np.zeros(len(p), np.float32)
    flat = pol & (np.abs(n[:, 1]) > 0.82)
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
        # carry neighbours over empty bands and smooth the extents
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
        d = np.minimum(d, np.hypot(p[:, 0] - x, p[:, 2] - z) - 0.0043)
    bx, bz = N9.BUTTON
    return np.where(flat, d, -1.0)


def paint_nine(G):
    S = Surf2(G, 202)
    p, n, N = S.p, S.n, S.N
    hz = nine_handling(p, n)
    # stainless slide: brushed along X; worn bright and smoother on the nose, the top edges and the serrations
    S.steel(S.sel(W.STAINLESS), lin("aeb1b6"), 0.26, hz, lin("d2d5da"), worn_rough=0.14, brushed="X", cvar=0.02,
            rvar=0.03, scratch=0.5, octave=0, rub_polish=0.06)
    # black oxide frame: bare steel only at the dust-cover nose, guard front, beavertail and rail edges
    frame = S.sel(W.BLACKOX)
    S.steel(frame, lin("34363b"), 0.45, hz, lin("8a9098"), worn_rough=0.24, thin_shift=(lin("3b3530"), 0.35),
            rvar=0.04, octave=3)
    # small parts (hammer, stop, safety, button, sights, pins): dark steel, wear on the pads
    S.steel(S.sel(W.DARK), lin("3c3e43"), 0.40, hz, lin("8a9098"), worn_rough=0.22, octave=6)
    # polished barrel and guide rod: lathe rings, bright
    pol_s = S.sel(W.POLISHED)
    S.steel(pol_s, lin("bbbec4"), 0.15, hz * 0.4, lin("d6d9de"), worn_rough=0.10, rvar=0.02, cvar=0.015, octave=9)
    if pol_s.any():
        q = p[pol_s]
        S.h[pol_s] += 7.0e-7 * N.fbm(q, (30000.0, 10.0, 10.0), 2, octave0=100)
        S.rough[pol_s] += 0.03 * N.fbm(q, (3000.0, 12.0, 12.0), 2, octave0=102)
    # gold: smooth polished plate, no mottling
    gold = S.sel(W.GOLD)
    if gold.any():
        S.bc[gold] = lin("e7b53a")[None, :] * (1 + 0.015 * N.fbm(p[gold], 40.0, 2, octave0=104)[:, None])
        S.rough[gold] = 0.19 + 0.025 * N.fbm(p[gold], 300.0, 2, octave0=105) - 0.04 * S.convex[gold]
        S.metal[gold] = 1.0
        S.h[gold] += 4e-5 * (n[gold, 0] > 0.5) * np.sin(p[gold, 2] / 0.0009 * 2 * math.pi)
    # grip panels: moulded polymer 0.55, polished where the palm sits; checkering 1.3 mm with a 2 mm smooth border
    pol = S.sel(W.POLYMER)
    S.polymer(pol, lin("1c1c1f"), 0.56, hz * 0.9)
    bd = nine_panel_border(S, pol)
    chk = pol & (bd > 0.0020)
    S.checker(chk, 0.0013, 3.2e-4, 15.0, bd - 0.0020, tip_polish=hz)
    # front and back straps stippled (frame texels on the grip that face front or back)
    strap = frame & (p[:, 2] < -0.040) & (p[:, 2] > -0.1255) & (np.abs(n[:, 1]) < 0.55) & (p[:, 0] < 0.034)
    S.stipple(strap, 0.00055, 6.0e-5)
    # serration interiors dark, chamber hood marking 2.5 mm high
    ser = S.sel(W.STAINLESS) & (np.abs(p[:, 1]) > 0.0108) & (np.abs(p[:, 1]) < 0.0128) & (p[:, 0] > 0.0075) \
        & (p[:, 0] < 0.0225) & (np.abs(n[:, 1]) < 0.5)
    S.bc[ser] *= 0.35
    S.rough[ser] += 0.12
    S.plain(S.sel(W.BORE), lin("040405"), 0.6, 0.0)
    # trigger, hammer spur and button textures
    spur = S.sel(W.DARK) & (p[:, 0] < -0.018) & (p[:, 2] > 0.004)
    S.h += spur * 7e-5 * np.abs(np.sin((p[:, 0] * 0.6 - p[:, 2] * 0.8) / 0.0008 * math.pi)) * np.abs(
        np.sin((p[:, 0] * 0.6 + p[:, 2] * 0.8) / 0.0008 * math.pi))
    btn = S.sel(W.DARK) & (p[:, 1] > 0.0125) & (np.hypot(p[:, 0] - 0.0625, p[:, 2] + 0.0405) < 0.0046)
    S.h += btn * 3e-5 * np.sign(np.sin(p[:, 0] / 0.0007 * math.pi) * np.sin(p[:, 2] / 0.0007 * math.pi))
    pads = S.sel(W.DARK) & (p[:, 1] > 0.0140) & (((p[:, 0] > 0.057) & (p[:, 0] < 0.071)) | ((p[:, 0] > 0.019) & (p[:, 0] < 0.031)))
    S.h += pads * 5e-5 * np.abs(np.sin(p[:, 0] / 0.0008 * math.pi))
    # carbon: breech face, barrel crown and slide nose face, round the port and on the hood; oil on the rails
    rr = np.hypot(p[:, 1], p[:, 2])
    carbon = (tp.smooth(p[:, 0], 0.198, 0.2010) * pol_s * tp.smooth(0.0068 - rr, 0.0, 0.0022) * 0.95
              + (p[:, 0] > 0.193) * (n[:, 0] > 0.6) * tp.smooth(0.0105 - rr, 0.0, 0.003) * 0.5
              + (p[:, 0] < 0.007) * (n[:, 0] > 0.6) * tp.smooth(0.006 - rr, 0.0, 0.003) * 0.8
              + gauss(p, (0.112, -0.008, 0.009), 0.012, 0.55) * (p[:, 1] < 0.0)
              + gauss(p, (0.088, 0.0, 0.004), 0.010, 0.45) * pol_s)
    oil = (gauss(p, (0.10, 0.0, -0.0125), 0.05, 0.6) * (np.abs(n[:, 2]) > 0.6) + gauss(p, (0.105, 0.0, 0.002), 0.03, 0.5))
    S.dirt(0.7, carbon=np.clip(carbon, 0, 1), oil=oil)
    # one faint thumb smudge on the left of the slide (roughness only)
    sm = gauss(p, (0.040, 0.0135, 0.002), 0.007, 1.0) * (n[:, 1] > 0.7) * S.sel(W.STAINLESS)
    S.rough += 0.05 * sm * (0.6 + 0.4 * N.fbm(p, 900.0, 2, octave0=110))
    # sights and markings
    S.dots([(0.0060, 0.0045, 0.0160), (0.0060, -0.0045, 0.0160)], 0.00085, "-X")
    S.dots([(0.1832, 0.0, 0.0158)], 0.00080, "-X")
    hood = tp.text_image([("9×19", 256, 256, 120)], 512)
    S.engrave(hood, (0, 1), (0.0985, -0.0054), (0.0108, 0.0108), "+Z", 2.5e-5)
    return S.channels(height_blur=0.4)


def paint_nine_mag(G):
    """Nine magazine: brushed steel body (along the magazine axis), bright insertion scuffs on the body, polished
    gold base pad, brass and copper top round."""
    S = Surf2(G, 9)
    p, n, N = S.p, S.n, S.N
    a = np.array([0.250, 0.0, 0.968]) / np.linalg.norm([0.250, 0.0, 0.968])
    t = p @ a.astype(np.float32)
    hz = np.clip(tp.smooth(t, -0.045, -0.020) * 0.7 + gauss(p, (0.0, 0.0, -0.135), 0.03, 0.4), 0, 1)
    body = S.sel(W.BLUED)
    S.steel(body, lin("9da1a7"), 0.27, hz, lin("c9cdd2"), worn_rough=0.16, rvar=0.03, cvar=0.02, octave=0)
    if body.any():
        q = p[body]
        # brushing along the magazine axis, insertion scuffs: long streaks on the sides near the edges
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
        S.bc[gold] = lin("e7b53a")[None, :] * (1 + 0.015 * N.fbm(p[gold], 40.0, 2, octave0=104)[:, None])
        S.rough[gold] = 0.20 + 0.02 * N.fbm(p[gold], 300.0, 2, octave0=105)
        S.metal[gold] = 1.0
        e = S.convex[gold] * tp.smooth(N.fbm(p[gold], 300.0, 2, octave0=106), -0.2, 0.3)
        S.bc[gold] += (lin("f6d27a") - S.bc[gold]) * (0.5 * e)[:, None]
    S.plain(S.sel(W.BORE), lin("040405"), 0.7, 0.0)
    S.steel(S.sel(W.BRASS), lin("caa23d"), 0.26, hz * 0, lin("e2c46a"), worn_rough=0.2, cvar=0.03, octave=6)
    S.steel(S.sel(W.COPPER), lin("b5683a"), 0.28, hz * 0, lin("d08a5a"), worn_rough=0.2, cvar=0.03, octave=8)
    S.steel(S.sel(W.PRIMER), lin("caa23d") * np.array([0.95, 0.9, 0.85], np.float32), 0.32, hz * 0, lin("caa23d"),
            octave=10)
    S.dirt(0.5)
    return S.channels(height_blur=0.4)
