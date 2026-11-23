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
    """Holster and hand contact on the NINE (0..1), round 3 geometry. No flat rectangles: every term is a contact
    spot or an edge band."""
    W_ = np.zeros(len(p), np.float32)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    slide = (z > -0.0136) & (x > -0.001)
    # holster: slide nose and its front corners, the shoulders, the dust-cover nose, guard front, tang tip
    W_ += slide * tp.smooth(x, 0.168, 0.196) * 0.9
    W_ += slide * tp.smooth(z, 0.0060, 0.0100) * tp.smooth(np.abs(y), 0.0085, 0.0120) * 0.45
    W_ += (z < -0.0136) * (z > -0.027) * tp.smooth(x, 0.176, 0.196) * 0.9
    W_ += (x > 0.119) * (z < -0.026) * (z > -0.073) * tp.smooth(x, 0.124, 0.131) * 0.85
    W_ += gauss(p, (0.112, 0.0, -0.0715), 0.012, 0.55) * (z < -0.068)                  # guard bottom on the holster
    W_ += gauss(p, (-0.031, 0.0, -0.0133), 0.0065, 0.95)                                # beavertail tip
    W_ += gauss(p, (0.186, 0.0, 0.016), 0.006, 0.7) + gauss(p, (0.012, 0.0, 0.016), 0.007, 0.5)   # sights
    # hands: racking grip on the serration crests, slide stop and safety pads, magazine button, takedown lever
    W_ += slide * (x > 0.0045) * (x < 0.0255) * (np.abs(y) > 0.0118) * gauss(p, (0.015, 0.0, -0.001), 0.012, 0.8)
    W_ += gauss(p, (0.0645, 0.016, -0.0185), 0.006, 0.95) + gauss(p, (0.026, 0.016, -0.0150), 0.006, 0.95)
    W_ += gauss(p, (0.0625, 0.013, -0.0405), 0.005, 0.85) + gauss(p, (0.108, 0.013, -0.023), 0.004, 0.6)
    W_ += gauss(p, (-0.023, 0.0, 0.0095), 0.0045, 0.9)                                  # hammer thumb face
    # the grip: palm on the right panel, support fingers on the left, web of the hand in the tang's cup,
    # fingers on the front strap; magazine insertion at the butt
    W_ += gauss(p, (0.014, -0.015, -0.078), 0.020, 0.70) * (y < 0)
    W_ += gauss(p, (0.030, 0.015, -0.090), 0.018, 0.50) * (y > 0)
    W_ += gauss(p, (-0.010, 0.0, -0.028), 0.011, 0.75)
    W_ += gauss(p, (-0.020, 0.0, -0.085), 0.026, 0.45) * (x < -0.006)
    W_ += (x > 0.018) * (z < -0.076) * (z > -0.126) * tp.smooth(n[:, 0], 0.3, 0.8) * 0.55
    W_ += (z < -0.1245) * 0.75
    # the slide stop sweeps an arc on the frame under its pad
    r = np.hypot(x - 0.0955, z + 0.0165)
    W_ += (y > 0.0110) * tp.smooth(0.0035 - np.abs(r - 0.033), 0.0, 0.003) * (x < 0.072) * (z < -0.0138) * 0.7
    return np.clip(W_, 0, 1)


def nine_panel_field(S, pol):
    """Distance (m) of each polymer texel from the panel's edge, read back from the panel grids the build stored
    (_weapons_nine.PANEL_FIELD: the same distances that recess the checkered field), minus the smooth ring round
    each screw; -1 where no panel is."""
    from assets import _weapons_nine as N9
    p = S.p
    d = np.full(len(p), -1.0, np.float32)
    for side, (zs, X, D) in N9.PANEL_FIELD.items():
        s = pol & (np.sign(p[:, 1]) == side)
        if not s.any():
            continue
        idx = np.nonzero(s)[0]
        zq, xq = p[idx, 2], p[idx, 0]
        order = np.argsort(-zs)                      # rows top -> bottom; interpolate between neighbouring rows
        zr = zs[order]
        k = np.clip(np.searchsorted(-zr, -zq), 1, len(zr) - 1)
        out = np.zeros(len(idx), np.float32)
        for kk in np.unique(k):
            m = k == kk
            r0, r1 = order[kk - 1], order[kk]
            d0 = np.interp(xq[m], X[r0], D[r0], left=-1.0, right=-1.0)
            d1 = np.interp(xq[m], X[r1], D[r1], left=-1.0, right=-1.0)
            t = np.clip((zr[kk - 1] - zq[m]) / max(zr[kk - 1] - zr[kk], 1e-9), 0, 1)
            out[m] = d0 + (d1 - d0) * t
        d[idx] = out
    for x, z in N9.SCREWS:
        d = np.where(d >= 0, np.minimum(d, np.hypot(p[:, 0] - x, p[:, 2] - z) - 0.0048), d)
    return d


def stainless_aniso(G, sel_img):
    """Anisotropy map for Unreal (0..1 = anisotropy 0..0.75 along the mesh tangent): on where the UV's U runs along
    +X (the slide's straightened shell: the brushing direction), off elsewhere."""
    P = G["pos"]
    du = np.roll(P, -1, axis=1) - np.roll(P, 1, axis=1)
    ln = np.linalg.norm(du, axis=-1)
    along = np.abs(du[..., 0]) / np.maximum(ln, 1e-12)
    a = tp.smooth(along, 0.93, 0.99) * sel_img
    return np.clip(tp.dilate(a.astype(np.float32), G["mask"], 8), 0, 1).astype(np.float32)


def paint_nine(G):
    S = Surf2(G, 202)
    p, n, N = S.p, S.n, S.N
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    hz = nine_handling(p, n)
    # ---- brushed stainless slide: #aeb1b6, brushed along X (30-80 um streaks, roughness 0.22-0.34 in long bands),
    # the top flat bead-blasted (0.45), edge breaks polished (0.12), holster bands at the nose and serration crests,
    # faint finger oil on the rear flats
    st = S.sel(W.STAINLESS)
    slide = st & (z > -0.0140) & (x > -0.0005) & (x < 0.1965) & (np.abs(y) < 0.0140)
    if st.any():
        q = p[st]
        bands = N.fbm(q * np.array([3.0, 1.0, 1.0], np.float32), (2.0, 900.0, 900.0), 3, octave0=200)
        streak = N.fbm(q, (8.0, 15000.0, 15000.0), 2, octave0=203)
        hair = tp.smooth(N.ridged(q, (25.0, 24000.0, 24000.0), 1, octave0=205), 0.90, 0.99)
        col = lin("aeb1b6")[None, :] * (1.0 + 0.012 * bands[:, None] + 0.008 * streak[:, None] + 0.03 * hair[:, None])
        r = 0.28 + 0.06 * bands + 0.02 * streak - 0.04 * hair
        S.h[st] += 3.0e-7 * streak + 2.5e-7 * hair
        nn = n[st]
        flat_top = tp.smooth(nn[:, 2], 0.985, 0.998) * (q[:, 2] > 0.0118) * (np.abs(q[:, 1]) < 0.0036)
        bead = N.fbm(q, 9000.0, 1, octave0=207)
        r = r + (0.45 + 0.03 * bead - r) * flat_top
        col = col * (1 - 0.06 * flat_top)[:, None]
        S.h[st] += 4e-7 * bead * flat_top
        pe = tp.smooth(S.convex[st], 0.50, 0.92)
        hzs = np.clip(hz[st], 0, 1)
        holster = tp.smooth(S.convex[st] * (0.5 + 1.0 * hzs) + 0.10 * N.fbm(q, 300.0, 2, octave0=208), 0.58, 0.86)
        r = r + (0.12 - r) * np.maximum(pe, holster * 0.8)
        col = col * (1.0 + 0.10 * pe[:, None] + 0.08 * holster[:, None])
        sc = S.scratches(0.5, sel=st, freq_across=2600.0) * tp.smooth(hzs, 0.25, 0.8)
        col = col * (1.0 + 0.06 * sc[:, None])
        r = r - 0.05 * sc
        S.h[st] -= 2.0e-6 * sc
        prints = S.fingerprints([((0.040, -0.0136, -0.002), "Y"), ((0.052, 0.0136, -0.004), "Y")], 0.0085)[st]
        prints *= np.abs(nn[:, 1]) > 0.8
        r = r - 0.06 * prints
        col = col * (1 - 0.025 * prints)[:, None]
        S.bc[st], S.rough[st], S.metal[st] = col, np.clip(r, 0.10, 0.55), 1.0
    # ---- black oxide frame: even #34363b (+-1.5 %), roughness 0.42 +- 0.025, bright only on convex edges and where
    # hands and holster rub, a fine machining grain along X on the flats
    frame = S.sel(W.BLACKOX)
    S.steel(frame, lin("34363b"), 0.42, hz, lin("8a9098"), worn_rough=0.24, thin_shift=(lin("3a3532"), 0.08),
            rvar=0.025, cvar=0.015, octave=3, base_thr=0.90, rub_polish=0.12)
    edge_wear(S, frame, lin("8a9098"), 1.05, octave=50, rough=0.22)
    if frame.any():
        q = p[frame]
        sand = N.fbm(q, (60.0, 9000.0, 9000.0), 2, octave0=210)
        S.h[frame] += 5e-7 * sand * (np.abs(n[frame, 1]) > 0.6)
        S.rough[frame] += 0.02 * sand
    # small parts: dark steel, wear on the pads and edges
    dk = S.sel(W.DARK)
    S.steel(dk, lin("3c3e43"), 0.40, hz, lin("8a9098"), worn_rough=0.22, octave=6, base_thr=0.92, rvar=0.03, cvar=0.02)
    edge_wear(S, dk, lin("8a9098"), 0.95, octave=53, rough=0.22)
    # screw slots worn bright at their edges (0.25 mm)
    for sx, sz in __import__("assets._weapons_nine", fromlist=["SCREWS"]).SCREWS:
        ring = dk & (np.hypot(x - sx, z - sz) < 0.0036) & (np.abs(y) > 0.0135)
        S.bc[ring] += (lin("8a9098") - S.bc[ring]) * (0.8 * tp.smooth(S.convex[ring], 0.3, 0.7))[:, None]
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
    # ---- grip panels: moulded polymer #1c1c1f; the 2.5 mm border smooth (0.5), 20 LPI checkering 0.45 mm deep in
    # the recessed field (tops 0.7, valleys 0.85); tops polished where the palm and fingers sit
    pol = S.sel(W.POLYMER)
    S.polymer(pol, lin("1c1c1f"), 0.50, hz * 0.6)
    bd = nine_panel_field(S, pol)
    chk = pol & (bd > 0.0)
    if chk.any():
        tops = S.checker_uv(chk, p[chk, 0], p[chk, 2], 0.00127, 4.5e-4, bd[chk] - BORDER_N9 - 0.0006, fade_w=0.0003)
        S.rough[chk] -= 0.14 * hz[chk] * tops
        S.bc[chk] *= (1.0 + 0.10 * hz[chk] * tops)[:, None]
    # ---- front strap: 20 LPI checkering (0.4 mm) with a 2 mm smooth border; back strap: 20 LPI checkering too
    fs = frame & (n[:, 0] > 0.45) & (x > 0.018) & (z < -0.080) & (z > -0.1215)
    if fs.any():
        zf = z[fs]
        field = np.minimum.reduce([zf + 0.1195, -0.0820 - zf, 0.0072 - np.abs(y[fs])]) - 0.0015
        S.checker_uv(fs, y[fs], zf, 0.00127, 4.0e-4, field, top_rough=0.55, val_rough=0.75)
    bs = frame & (n[:, 0] < -0.45) & (z < -0.046) & (z > -0.1225) & (x < 0.0)
    if bs.any():
        zb_ = z[bs]
        field = np.minimum.reduce([zb_ + 0.1205, -0.0480 - zb_, 0.0078 - np.abs(y[bs])]) - 0.0015
        S.checker_uv(bs, y[bs], zb_, 0.00127, 4.0e-4, field, top_rough=0.55, val_rough=0.75)
    # guard front: 1.5 mm-pitch horizontal serrations
    gf = frame & (n[:, 0] > 0.6) & (x > 0.1270) & (z < -0.028) & (z > -0.0600)
    if gf.any():
        f = np.minimum(z[gf] + 0.0595, -0.0285 - z[gf])
        S.h[gf] += -1.6e-4 * tp.smooth(np.abs(((z[gf] / 0.0015) % 1.0) - 0.5), 0.10, 0.22) * tp.smooth(f, 0.0, 0.0008)
    # ---- rear sight's sloped rear face and the slide's rear face: 40 LPI anti-glare lines; firing-pin stop plate seam
    rsf = dk & (x < 0.0084) & (x > 0.0062) & (z > 0.0120) & (z < 0.0186) & (n[:, 0] < -0.6)
    S.h[rsf] += -7e-5 * np.abs(((z[rsf] / 0.000635) % 1.0) - 0.5) * 2.0
    S.rough[rsf] = 0.62
    srf = st & (x < 0.0009) & (n[:, 0] < -0.7)
    if srf.any():
        S.h[srf] += -6e-5 * np.abs(((z[srf] / 0.000635) % 1.0) - 0.5) * 2.0
        S.rough[srf] = 0.55
        yy, zz = np.abs(y[srf]), z[srf]
        seam = (np.minimum(np.abs(yy - 0.0052), np.abs(zz + 0.0105)) < 0.00006) & (yy < 0.0053) & (zz > -0.0106) & (zz < 0.0090)
        seam |= (np.abs(zz - 0.0090) < 0.00006) & (yy < 0.0053)
        S.h[srf] -= 1.2e-4 * seam
        S.bc[srf] *= (1 - 0.6 * seam)[:, None]
    # ---- carbon, oil and dust
    rr = np.hypot(y, z)
    carbon = (tp.smooth(x, 0.198, 0.2010) * pol_s * tp.smooth(0.0068 - rr, 0.0, 0.0022) * 0.95          # crown
              + (x > 0.193) * (n[:, 0] > 0.6) * tp.smooth(0.0100 - rr, 0.0, 0.0030) * 0.45                 # slide nose
              + st * gauss(p, (0.106, -0.012, 0.009), 0.013, 0.40) * ((y < -0.006) | (z > 0.009))          # round the port
              + st * (x > 0.084) * (x < 0.128) * (y < 0.005) * tp.smooth(S.convex, 0.2, 0.6) * 0.35 * (z > -0.004)
              + st * (x > 0.0044) * (x < 0.0062) * (n[:, 0] > 0.5) * 0.6                                   # breech face
              + pol_s * (x < 0.0650) * (n[:, 0] < -0.5) * tp.smooth(rr, 0.0040, 0.0052) * 0.45)            # chamber edge
    grime = np.zeros(len(p), np.float32)                                     # pins and controls
    for c in ((0.091, 0.0125, -0.031), (0.091, -0.0125, -0.031), (-0.0135, 0.0095, -0.0105), (-0.0135, -0.0095, -0.0105),
              (0.0955, 0.0130, -0.0165), (0.118, 0.0130, -0.0215), (0.008, 0.0130, -0.018), (0.0625, 0.0110, -0.0405)):
        d = np.linalg.norm(p - np.asarray(c, np.float32), axis=1)
        grime = np.maximum(grime, tp.smooth(0.0045 - d, 0.0, 0.0025) * tp.smooth(1.0 - S.cav, 0.02, 0.15))
    oil = gauss(p, (0.10, 0.0, -0.0125), 0.05, 0.5) * (np.abs(n[:, 2]) > 0.6)
    keep = {k: getattr(S, k)[pol_s].copy() for k in ("bc", "rough", "metal")}
    S.dirt(0.60, carbon=np.clip(carbon + 0.6 * grime, 0, 1), oil=oil)
    # the polished hood and barrel stay clean except the chamber ring and the crown
    cpol = np.clip(carbon[pol_s], 0, 1)
    for k, v in keep.items():
        cur = getattr(S, k)
        cur[pol_s] = v * (1 - cpol[:, None] if v.ndim == 2 else 1 - cpol) + cur[pol_s] * (cpol[:, None] if v.ndim == 2 else cpol)
    # sights and markings
    S.dots([(0.0068, 0.0045, 0.0160), (0.0068, -0.0045, 0.0160)], 0.00085, "-X")
    S.dots([(0.1832, 0.0, 0.0158)], 0.00080, "-X")
    hood = tp.text_image([("9×19", 256, 256, 120)], 512)
    S.engrave(hood, (0, 1), (0.0985, -0.0054), (0.0108, 0.0108), "+Z", 2.5e-5)
    ch = S.channels(height_blur=0.35)
    ch["aniso"] = stainless_aniso(G, tp.scatter(S.m, (slide & (np.abs(n[:, 0]) < 0.5)).astype(np.float32)))
    return ch


BORDER_N9 = 0.0025


def paint_nine_mag(G):
    """Nine magazine: brushed steel body (along the magazine axis), bright insertion scuffs on the body, one moulded
    gold base pad: polished #e7b53a (0.20) on the sides, the bottom flats scuffed to 0.25-0.5, brass showing through
    at the corners and on the front lip."""
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
        ng = n[gold]
        S.bc[gold] = lin("e7b53a")[None, :] * (1 + 0.012 * N.fbm(q, 40.0, 2, octave0=104)[:, None])
        S.rough[gold] = 0.20 + 0.02 * N.fbm(q, 300.0, 2, octave0=105)
        S.metal[gold] = 1.0
        bot = tp.smooth(-ng[:, 2], 0.55, 0.85)
        sc = np.maximum(S.scratches(1.0, along="X", sel=gold, freq_across=1800.0),
                        S.scratches(0.8, along="Y", sel=gold, freq_across=1800.0, octave=20)) * bot
        scuff = bot * (0.6 + 0.4 * tp.smooth(N.fbm(q, 70.0, 3, octave0=109), -0.3, 0.5))
        S.rough[gold] += (0.42 - S.rough[gold]) * scuff * 0.8 + 0.08 * sc
        S.bc[gold] *= (1 - 0.10 * scuff)[:, None]
        lipf = tp.smooth(q[:, 0], 0.0255, 0.0290) * tp.smooth(ng[:, 0], 0.2, 0.7)
        corner = tp.smooth(S.convex[gold] * (0.6 + 0.6 * N.fbm(q, 500.0, 2, octave0=106)) + 0.5 * lipf, 0.45, 0.8)
        wear = np.clip(corner + 0.6 * sc * tp.smooth(N.fbm(q, 90.0, 2, octave0=107), -0.2, 0.3), 0, 1)
        S.bc[gold] += (lin("b38b3c") - S.bc[gold]) * wear[:, None]
        S.rough[gold] += 0.10 * wear
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
    H += gauss(p, (0.104, 0.021, 0.003), 0.006, 0.9)                                 # selector tab
    H += gauss(p, (0.166, 0.0, -0.064), 0.008, 0.9)                                  # magazine catch paddle
    H += (x > 0.036) * (x < 0.060) * (z > 0.031) * 0.35                               # cover rib crowns
    H += gauss(p, (0.4092, 0.0, 0.062), 0.006, 0.8)                                  # front sight ear tops
    H += (x > 0.455) * (x < 0.4975) * tp.smooth(np.hypot(y, z), 0.0120, 0.0130) * 0.4  # booster body and ring
    H += gauss(p, (0.0, 0.0, 0.010), 0.012, 0.5) + gauss(p, (0.022, 0.0, -0.028), 0.012, 0.6)   # trunnion, hinge
    return np.clip(H, 0, 1)


def laminate(S, sel, base, ply_axis, grain_axis, handling, palm=None, web=None, octave=0, polish=None, grime=None):
    """Laminated wood under clear varnish: plies 1.0-1.5 mm thick alternating #55301c and the darker #3d2214 (the
    shape's curves cut through them, so they show as contour bands on curved faces and as straight stripes on every
    chamfer, vent wall and end face), grain along grain_axis with open pores, varnish at 0.25-0.3 over wood at 0.5,
    worn back to matte on the edges and under the support hand (palm), handling polish where given (polish), small
    dents, grime (0..1) darkening toward the ferrule."""
    if not sel.any():
        return
    p, N = S.p[sel], S.N
    n = S.n[sel]
    warp = 0.00030 * N.fbm(p, 45.0, 3, octave0=130 + octave) + 0.00010 * N.fbm(p, 260.0, 2, octave0=133 + octave)
    q = p[:, ply_axis] + warp
    s_ = q / 0.00125 + 0.18 * np.sin(q / 0.0071 * 2 * math.pi)                    # 1.0 .. 1.5 mm plies
    k = np.floor(s_).astype(np.int64)
    f = s_ - np.floor(s_)
    dark = lin("3d2214")
    light = np.asarray(base, np.float32)
    jit = N.vals[(k * 37 + 11) & 255] * 0.08 - 0.04
    tone = np.where((k % 2 == 0)[:, None], light[None, :], dark[None, :]) * (1 + jit)[:, None]
    soft = tp.smooth(np.minimum(f, 1 - f), 0.0, 0.10)                              # soft ply boundaries
    mixc = (light[None, :] + dark[None, :]) * 0.5
    col = mixc + (tone - mixc) * soft[:, None]
    glue = tp.smooth(0.05 - np.minimum(f, 1 - f), 0.0, 0.04)
    fr = [1800.0, 1800.0, 1800.0]
    fr[grain_axis] = 22.0
    grain = N.fbm(p + warp[:, None] * 4, tuple(fr), 3, octave0=136 + octave)
    fr2 = [v * 2.2 for v in fr]
    pores = tp.smooth(N.ridged(p, tuple(fr2), 1, octave0=139 + octave), 0.90, 0.985)
    col = col * (1 + 0.12 * grain[:, None]) * (1 - 0.30 * glue[:, None]) * (1 - 0.18 * pores[:, None])
    end = tp.smooth(np.abs(n[:, grain_axis]), 0.55, 0.85)                         # end grain reads darker, drier
    col = col * (1 - 0.30 * end[:, None])
    hz = np.clip(handling[sel], 0, 1)
    brk = N.fbm(p, 360.0, 3, octave0=142 + octave)
    e = S.convex[sel]
    edge = tp.smooth(e * (0.55 + 1.0 * hz) + 0.30 * brk - 0.55, 0.0, 0.18)         # varnish worn off the edges
    chip = tp.smooth(e * (0.3 + 1.3 * hz) + 0.40 * brk - 0.95, 0.0, 0.08)          # through to pale raw wood
    raw = lin("a77a50")
    col = col * (1 + 0.10 * edge[:, None])
    col = col + (raw[None, :] * (0.9 + 0.2 * grain[:, None]) - col) * chip[:, None]
    r = 0.27 + 0.03 * N.fbm(p, 120.0, 2, octave0=145 + octave) + 0.10 * pores + 0.10 * end
    r = r + (0.50 - r) * np.clip(edge + chip, 0, 1)
    if palm is not None:                             # under the support hand: varnish worn back to matte
        pm = np.clip(palm[sel], 0, 1) * (0.6 + 0.4 * tp.smooth(N.fbm(p, 150.0, 2, octave0=146 + octave), -0.3, 0.4))
        r = r + (0.48 - r) * pm
        col = col * (1 + 0.06 * pm)[:, None]
    if polish is not None:                           # handling polish (grip swell and back)
        po = np.clip(polish[sel], 0, 1)
        r = r - 0.10 * po * (1 - pores * 0.6)
        col = col * (1 - 0.06 * po)[:, None]
    if web is not None:
        wb = np.clip(web[sel], 0, 1)
        col = col * (1 - 0.30 * wb)[:, None]
        r = r + 0.08 * wb
    if grime is not None:
        gm = np.clip(grime[sel], 0, 1) * (0.6 + 0.4 * N.fbm(p, 200.0, 2, octave0=147 + octave))
        col = col * (1 - 0.35 * gm)[:, None]
        r = r + 0.12 * gm
    # small dents: sparse round pits 0.6-1.5 mm across, the varnish rougher in them
    _id, dd = N.cells(p, 0.004, 0.9, octave=148 + octave)
    keep = _id > 0.80
    dent = tp.smooth(0.30 - dd, 0.0, 0.18) * keep
    r = r + 0.10 * dent
    S.bc[sel] = col
    S.rough[sel] = np.clip(r, 0.18, 0.75)
    S.metal[sel] = 0.0
    S.h[sel] += (-2.0e-5 * pores + 3e-6 * grain - 5e-5 * chip * (0.5 + 0.5 * brk) - 8e-5 * dent
                 + 1.2e-6 * N.fbm(p, 4500.0, 1, octave0=149 + octave))


def edge_wear(S, sel, worn_col, width_gain=1.0, octave=0, rough=0.24):
    """Thin bare-steel line on every convex edge (curvature-driven, ~0.2-0.6 mm), broken up; returns the mask."""
    if not sel.any():
        return np.zeros(0, np.float32)
    p = S.p[sel]
    brk = S.N.fbm(p, 900.0, 2, octave0=220 + octave)
    w = tp.smooth(S.convex[sel] * width_gain + 0.25 * brk, 0.78, 0.98)
    S.bc[sel] += (np.asarray(worn_col, np.float32)[None, :] - S.bc[sel]) * w[:, None]
    S.rough[sel] += (rough - S.rough[sel]) * w
    S.h[sel] -= 1.5e-6 * w
    return w


def chunks(sel, size=1_500_000):
    """Split a texel mask into masks of at most `size` texels (per-texel painters run in pieces to bound memory)."""
    idx = np.nonzero(sel)[0]
    for k in range(0, len(idx), size):
        m = np.zeros(len(sel), bool)
        m[idx[k:k + size]] = True
        yield m


def laminate3(S, sel, grain_axis, handling, rub=None, palm=None, web=None, octave=0, grime=None, ply_normal=(0.0, 1.0, 0.0)):
    """Laminated wood driven by a 3D ply field (round 3): ply = floor(dot(P, ply_normal) / 1.6-2.0 mm) with the plies
    stacked across the gun, so a flat side face lies in one ply and shows its long grain, while round-overs, slot
    walls and ends cut through the stack and show the plies as contour lines that follow the shape. Stain alternates
    dark red-brown #4a2515 / lighter #6b3a22 with +-8 % per ply, each ply its own grain streaks and fine pores; varnish
    at 0.28 worn to 0.5 where hands rub (rub), dents and a few crushed corners, pale bare wood on worn edges."""
    if not sel.any():
        return
    p, N = S.p[sel], S.N
    n = S.n[sel]
    pn = np.asarray(ply_normal, np.float32)
    warp = 0.00022 * N.fbm(p, 30.0, 3, octave0=130 + octave) + 0.00006 * N.fbm(p, 210.0, 2, octave0=133 + octave)
    f = p @ pn + warp
    s_ = f / 0.0018 + 0.11 * np.sin(f / 0.0093 * 2 * math.pi) + 0.06 * np.sin(f / 0.0047 * 2 * math.pi + 1.3)
    k = np.floor(s_).astype(np.int64)
    fr = s_ - np.floor(s_)
    dark, light = lin("4a2515"), lin("6b3a22")
    jit = N.vals[(k * 37 + 11 + octave) & 255] * 0.16 - 0.08
    tone = np.where((k % 2 == 0)[:, None], light[None, :], dark[None, :]) * (1 + jit)[:, None]
    edge_d = np.minimum(fr, 1 - fr)
    soft = tp.smooth(edge_d, 0.0, 0.07)
    mixc = (light[None, :] + dark[None, :]) * 0.5
    col = mixc + (tone - mixc) * soft[:, None]
    glue = tp.smooth(0.035 - edge_d, 0.0, 0.03)                     # the thin glue line between plies
    # per-ply grain: streaks along the grain axis, shifted per ply so neighbouring plies differ
    shift = (N.vals[(k * 53 + 7) & 255] * 0.37)[:, None].astype(np.float32)
    q = p + shift
    frq = [1500.0, 1500.0, 1500.0]
    frq[grain_axis] = 18.0
    grain = N.fbm(q, tuple(frq), 3, octave0=136 + octave)
    frq2 = [3800.0, 3800.0, 3800.0]
    frq2[grain_axis] = 60.0
    streak = tp.smooth(N.ridged(q, tuple(frq2), 2, octave0=138 + octave), 0.80, 0.97)
    frq3 = [9000.0, 9000.0, 9000.0]
    frq3[grain_axis] = 900.0
    pores = tp.smooth(N.ridged(q, tuple(frq3), 1, octave0=139 + octave), 0.93, 0.99)
    face_on = np.abs(n @ pn)                                        # 1 on a face lying in a ply
    col = col * (1 + (0.10 + 0.06 * face_on)[:, None] * grain[:, None]) * (1 - 0.16 * streak[:, None]) \
        * (1 - 0.35 * glue[:, None] * (1 - face_on)[:, None]) * (1 - 0.12 * pores[:, None])
    end = tp.smooth(np.abs(n[:, grain_axis]), 0.60, 0.90)           # end grain: darker, drier, the stain pooled
    col = col * (1 - 0.28 * end[:, None])
    hz = np.clip(handling[sel], 0, 1)
    brk = N.fbm(p, 240.0, 3, octave0=142 + octave)
    e = S.convex[sel]
    worn = tp.smooth(e * (0.55 + 0.9 * hz) + 0.22 * brk - 0.55, 0.0, 0.18)       # varnish worn off the edges
    bare = tp.smooth(e * (0.45 + 1.0 * hz) + 0.25 * brk - 0.92, 0.0, 0.10)       # through to pale bare wood
    raw = lin("9a6a42")
    col = col * (1 + 0.08 * worn[:, None])
    col = col + (raw[None, :] * (0.92 + 0.12 * grain[:, None]) - col) * bare[:, None]
    r = 0.28 + 0.02 * N.fbm(p, 90.0, 2, octave0=145 + octave) + 0.08 * pores + 0.06 * end
    r = r + (0.50 - r) * np.clip(worn * 0.8 + bare, 0, 1)
    if rub is not None:                               # handling: the varnish worn satin (0.5) where hands rub
        rb = np.clip(rub[sel], 0, 1) * (0.7 + 0.3 * tp.smooth(N.fbm(p, 120.0, 2, octave0=146 + octave), -0.3, 0.4))
        r = r + (0.50 - r) * rb
        col = col * (1 - 0.05 * rb)[:, None]
    if palm is not None:
        pm = np.clip(palm[sel], 0, 1)
        r = r + (0.46 - r) * pm * 0.7
    if web is not None:
        wb = np.clip(web[sel], 0, 1)
        col = col * (1 - 0.25 * wb)[:, None]
        r = r + 0.06 * wb
    if grime is not None:
        gm = np.clip(grime[sel], 0, 1) * (0.6 + 0.4 * N.fbm(p, 200.0, 2, octave0=147 + octave))
        col = col * (1 - 0.30 * gm)[:, None]
        r = r + 0.10 * gm
    # dents (sparse, 1-3 mm) and a few crushed corners on the most exposed edges
    _id, dd = N.cells(p, 0.009, 0.9, octave=148 + octave)
    dent = tp.smooth(0.28 - dd, 0.0, 0.20) * (_id > 0.86)
    crush = tp.smooth(e * (0.5 + hz) - 0.75, 0.0, 0.1) * tp.smooth(N.fbm(p, 60.0, 2, octave0=150 + octave), 0.35, 0.6)
    col = col * (1 - 0.10 * dent - 0.12 * crush)[:, None]
    r = r + 0.08 * dent + 0.10 * crush
    S.bc[sel] = col
    S.rough[sel] = np.clip(r, 0.2, 0.7)
    S.metal[sel] = 0.0
    S.h[sel] += (-1.4e-5 * pores - 1.0e-5 * streak * (1 - face_on) + 2.5e-6 * grain - 4.0e-5 * bare * (0.5 + 0.5 * brk)
                 - 9e-5 * dent - 1.2e-4 * crush + 0.8e-6 * N.fbm(p, 3000.0, 1, octave0=149 + octave))


def blued_sheet(S, sel, base, handling, worn_col, octave=0, rough_lo=0.35, rough_hi=0.55, edge_gain=1.0):
    """Blued sheet and forgings (round 3): even colour with a faint orange-peel variation (+-3 % value), roughness
    0.35-0.55 in fine breakup, bare bright steel only on convex edges 0.3-1.5 mm wide (wider where hands and the
    bolt handle rub), handling polish on the flats, sparse 0.05 mm micro-scratches along the handling motion."""
    if not sel.any():
        return np.zeros(0, np.float32)
    p, N = S.p[sel], S.N
    hz = np.clip(handling[sel], 0, 1)
    peel = N.fbm(p, 650.0, 2, octave0=300 + octave)
    mid = N.fbm(p, 140.0, 2, octave0=303 + octave)
    col = np.asarray(base, np.float32)[None, :] * (1.0 + 0.03 * peel[:, None] + 0.015 * mid[:, None])
    r = rough_lo + (rough_hi - rough_lo) * (0.5 + 0.5 * tp.smooth(mid + 0.4 * peel, -0.7, 0.7))
    S.h[sel] += 1.2e-6 * peel
    e = S.convex[sel] * edge_gain
    brk = N.fbm(p, 700.0, 2, octave0=306 + octave)
    w = tp.smooth(e * (0.65 + 0.9 * hz) + 0.18 * brk - 0.62, 0.0, 0.16)
    rubp = np.clip(hz * (0.5 + 0.5 * N.fbm(p, 110.0, 2, octave0=308 + octave)), 0, 1)
    sc = S.scratches(0.35, sel=sel, freq_across=20000.0, freq_long=60.0, octave=310 + octave) * tp.smooth(hz, 0.15, 0.6)
    wc = np.asarray(worn_col, np.float32)[None, :]
    col = col * (1.0 + 0.16 * rubp[:, None])
    col = col + (wc - col) * np.clip(w + 0.45 * sc, 0, 1)[:, None]
    r = r - 0.10 * rubp
    r = r + (0.22 - r) * w - 0.05 * sc
    S.bc[sel] = col
    S.rough[sel] = r
    S.metal[sel] = 1.0
    S.h[sel] += -2.5e-6 * w * (0.5 + 0.5 * brk) - 2.0e-6 * sc
    return w


def paint_chopper(G):
    """One painter for the three CHOPPER sets (receiver and rear, furniture, front end), round 3: every mask is a
    function of the gun-space position, so the sets meet without seams. Blued steel with use-driven edge wear and
    packed grime, milled trunnions, ground carrier, laminate from a 3D ply field."""
    S = Surf2(G, 101)
    p, n, N = S.p, S.n, S.N
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    hz = chopper_handling(p, n)
    bright_edge = lin("9aa0a8")
    bl = S.sel(W.BLUED)
    # where the edges wear hardest: the magazine-well lip, the charging-handle path, the cover ribs, sight ears, booster
    gain = np.ones(len(p), np.float32)
    gain += 0.6 * ((x > 0.150) & (x < 0.232) & (z < -0.033))
    gain += 0.6 * ((x > 0.080) & (x < 0.196) & (y > 0.010) & (z > 0.004) & (z < 0.016))
    gain += 0.5 * ((x > 0.035) & (x < 0.061) & (z > 0.026))
    gain += 0.5 * (x > 0.426)
    blued_sheet(S, bl, lin("5a5e65"), hz, bright_edge, octave=0, edge_gain=gain[bl])
    cv = S.sel(W.COVER)
    blued_sheet(S, cv, lin("53565c"), hz, bright_edge, octave=3, edge_gain=1.15)
    dk = S.sel(W.DARK)
    blued_sheet(S, dk, lin("3c3e43"), hz, bright_edge, octave=6, rough_lo=0.40, rough_hi=0.58, edge_gain=1.1)
    # forged trunnions and blocks: linear milling marks (rear trunnion faces, the sight block's flanks, gas block)
    mill = bl & (((x < 0.0036) & (np.abs(y) < 0.0158)) | ((x > 0.186) & (x < 0.256) & (z > 0.011)) | ((x > 0.392) & (x < 0.427)))
    if mill.any():
        q = p[mill]
        nm = n[mill]
        across = np.where(np.abs(nm[:, 0]) > 0.6, q[:, 2], q[:, 0])
        lines = np.sin(across / 0.00060 * 2 * math.pi + 3.0 * N.fbm(q, 40.0, 1, octave0=320))
        S.h[mill] += 6e-7 * lines + 4e-7 * N.fbm(q, (9000.0, 30.0, 9000.0), 1, octave0=322)
        S.rough[mill] += 0.03 * lines - 0.05
    # ground carrier: short surface-grinding marks along X, roughness 0.2-0.3, oiled rails, carbon ring at the bolt face
    car = S.sel(W.BRIGHT)
    if car.any():
        q = p[car]
        g1 = N.fbm(q, (300.0, 16000.0, 16000.0), 2, octave0=330)
        g2 = tp.smooth(N.ridged(q, (140.0, 24000.0, 24000.0), 1, octave0=332), 0.86, 0.98)
        S.bc[car] = lin("b1b6bd")[None, :] * (1.0 + 0.025 * g1[:, None] + 0.04 * g2[:, None])
        S.rough[car] = 0.25 + 0.04 * g1 - 0.05 * g2
        S.metal[car] = 1.0
        S.h[car] += 5e-7 * g1 + 4e-7 * g2
        rail = (np.abs(n[car, 2]) > 0.8) & (q[:, 2] < 0.0075)
        S.rough[car] -= 0.07 * rail
        S.bc[car] *= (1 - 0.06 * rail)[:, None]
        w_ = tp.smooth(S.convex[car], 0.5, 0.9)
        S.rough[car] += (0.18 - S.rough[car]) * w_
    # ---- laminate: plies stacked across the gun (ply normal = Y)
    wood = S.sel(W.WOOD)
    grip = wood & (z < -0.040) & (x < 0.09)
    hg = wood & ~grip
    flange = tp.smooth(np.abs(y), 0.019, 0.022) * (z > -0.016) * (z < -0.004) * (x > 0.25)
    palm_l = tp.smooth(0.012 - np.abs(x - 0.315), 0.0, 0.020) * (z < -0.018)
    grime = tp.smooth(x, 0.330, 0.372) * hg
    for part in chunks(hg):                          # in pieces: the 4K furniture set is ~11 M texels
        laminate3(S, part, 0, hz, rub=np.clip(flange * 0.9 + palm_l * 0.6, 0, 1), octave=0, grime=grime)
    front_g = tp.smooth(n[:, 0], 0.2, 0.7) * grip
    palm_r = gauss(p, (0.040, -0.016, -0.090), 0.026, 1.0) * (y < 0.002)
    web = gauss(p, (0.030, 0.0, -0.046), 0.012, 0.8) * (x < 0.036)
    for part in chunks(grip):
        laminate3(S, part, 2, hz, rub=np.clip(front_g * 0.9 + palm_r * 0.5, 0, 1), web=web, octave=10)
    S.plain(S.sel(W.BORE), lin("050506"), 0.62, 0.0)
    # ---- the rear sight leaf's rear face: 0.5 mm anti-glare lines, 0.15 mm deep, dark matte
    lf = dk & (x > 0.0213) & (x < 0.0224) & (z > 0.040) & (z < 0.0552) & (n[:, 0] < -0.6)
    if lf.any():
        S.h[lf] += -1.5e-4 * np.abs(((z[lf] / 0.0005) % 1.0) - 0.5) * 2.0
        S.rough[lf] = 0.68
        S.bc[lf] *= 0.80
    # ---- carbon, grime and oil: concave corners, rivet rings, the cover-to-receiver seam, the port and gas block
    r = np.hypot(y, z)
    inside = ((n[:, 1] * y + n[:, 2] * z) < 0) & (x > 0.43)
    carbon = (inside * (r < 0.0165) * (0.65 + 0.35 * tp.smooth(0.494 - x, 0.0, 0.02))
              + tp.smooth(x, 0.4955, 0.4975) * tp.smooth(0.0150 - r, 0.0, 0.0012) * 0.5
              + (x > 0.4250) * (x < 0.428) * (n[:, 0] > 0.6) * 0.45
              + (x > 0.392) * (x < 0.4265) * (z > 0.004) * (z < 0.028) * (n[:, 0] > 0.5) * 0.4
              + gauss(p, (0.140, -0.017, 0.012), 0.022, 0.55) * (y < -0.010)
              + (x > 0.2025) * car * (n[:, 0] > 0.6) * 0.7
              + car * (x > 0.2040) * (x < 0.2060) * tp.smooth(r, 0.0034, 0.0045) * tp.smooth(0.0084 - r, 0.0, 0.0008) * 0.8)
    seam = tp.smooth(0.0012 - np.abs(z - 0.0045), 0.0, 0.0012) * (np.abs(y) > 0.0155) * (x > 0.002) * (x < 0.186)
    rivring = np.zeros(len(p), np.float32)
    from assets import _weapons_chopper as CHT
    for xr, zr in tuple(CHT.FRONT_RIVETS) + tuple(CHT.REAR_RIVETS):
        d = np.hypot(x - xr, z - zr)
        rivring = np.maximum(rivring, tp.smooth(0.0007 - np.abs(d - 0.0025), 0.0, 0.0006) * (np.abs(y) > 0.0155))
    oil = (gauss(p, (0.140, -0.012, 0.012), 0.040, 0.9) * (y < -0.004) + gauss(p, (0.150, 0.0, 0.014), 0.05, 0.6) * car
           + gauss(p, (0.409, 0.0, 0.012), 0.022, 0.7) * (x > 0.385))
    S.dirt(1.25, carbon=np.clip(carbon + 0.55 * seam + 0.6 * rivring, 0, 1), oil=oil)
    S.rough = S.rough - 0.10 * np.clip(oil, 0, 1) * (S.metal > 0.5)
    S.rough = np.maximum(S.rough, 0.18 * (S.metal > 0.5))
    carb = np.clip(carbon, 0, 1) * inside
    S.rough = S.rough + (0.80 - S.rough) * carb * 0.9
    rim = (x > 0.4940) * tp.smooth(r, 0.0140, 0.0156) * (S.sel(W.BLUED))
    S.bc += (lin("b8bdc4") - S.bc) * (rim * 0.85)[:, None]
    S.rough -= 0.20 * rim
    S.metal = np.maximum(S.metal, rim)
    # sight paint (faintly self-lit): two dots on the rear leaf, a strip on the front post's rear face, chipped
    S.dots([(0.0215, 0.0046, 0.0498), (0.0215, -0.0046, 0.0498)], 0.00095, "-X")
    S.dots([(0.4080, 0.0, 0.0527)], (0.00072, 0.0027), "-X")
    chipm = (x > 0.4075) * (x < 0.4085) * (np.abs(z - 0.0527) < 0.003) * tp.smooth(N.fbm(p, 2600.0, 2, octave0=230), 0.25, 0.45)
    S.bc += (lin("3c3e43") - S.bc) * chipm[:, None]
    S.emit *= (1 - chipm)[:, None]
    # stamped markings on the left (+Y) faces, laid out to read correctly from the left (image x runs along -X):
    # selector positions and one fictional proof symbol 0.15 mm deep; no letters-and-numbers code
    img = tp.text_image([("S", 128, 70, 120), ("A", 128, 250, 120), ("1", 128, 430, 120)], 512)[:, ::-1]
    S.engrave(img, (0, 2), (0.1075, -0.0215), (0.0105, 0.0315), "+Y", 6e-5)
    pm = tp.text_image([("✶", 256, 256, 330)], 512)[:, ::-1]
    S.engrave(pm, (0, 2), (0.2195, -0.0125), (0.0085, 0.0085), "+Y", 1.5e-4)
    kn = S.sel(W.DARK) & (y > 0.031) & (np.abs(x - 0.180) < 0.008) & (np.abs(z - 0.0145) < 0.008)
    ang = np.arctan2(z - 0.0145, x - 0.180)
    knurl = np.sin(ang * 36 + y / 0.0007 * 2 * math.pi) * np.sin(ang * 36 - y / 0.0007 * 2 * math.pi)
    S.h += kn * 2.5e-5 * knurl
    trg = S.sel(W.DARK) & (np.abs(x - 0.105) < 0.009) & (z < -0.040) & (z > -0.070) & (n[:, 0] < -0.4)
    S.h += trg * 3e-5 * np.sin(z / 0.0010 * 2 * math.pi)
    return S.channels(height_blur=0.4)


def paint_chopper_mag(G):
    """CHOPPER magazine (round 3): #45484e bluing at 0.45, bright along the front and back spines, the base and the
    feed lips; insertion scuffs at the top, pouch scratches over the lower third; seven spot-weld dimples on the spine
    strip, a rippled weld bead on the front seam."""
    S = Surf2(G, 7)
    p, n, N = S.p, S.n, S.N
    top = tp.smooth(p[:, 2], -0.050, -0.028)
    floor = tp.smooth(-p[:, 2], 0.205, 0.226)
    spine = (np.abs(p[:, 1]) < 0.0045) & (np.abs(n[:, 0]) > 0.35)
    lower = tp.smooth(-p[:, 2], 0.150, 0.175)
    hz = np.clip(top * 0.85 + floor * 0.7 + gauss(p, (0.29, 0.0, -0.20), 0.05, 0.35) + spine * 0.8, 0, 1)
    body = S.sel(W.BLUED)
    blued_sheet(S, body, lin("45484e"), hz, lin("9aa0a8"), octave=0, rough_lo=0.40, rough_hi=0.50, edge_gain=1.15)
    if body.any():
        q = p[body]
        sc = tp.smooth(N.ridged(np.stack([q[:, 0] * 400.0, q[:, 1] * 30.0, q[:, 2] * 2500.0], 1), 1.0, 2, octave0=160),
                       0.95, 0.995) * top[body] * (np.abs(n[body, 1]) > 0.6)
        pouch = S.scratches(0.9, along="Z", sel=body, freq_across=9000.0, freq_long=40.0, octave=170) * lower[body] \
            * (np.abs(n[body, 1]) > 0.6)
        S.bc[body] += (lin("9aa0a8") - S.bc[body]) * (0.6 * sc + 0.45 * pouch)[:, None]
        S.rough[body] -= 0.1 * sc + 0.06 * pouch
        S.h[body] -= 2e-6 * pouch
        # spot welds on the spine strip: seven dimples 2.5 mm across, heat-tinted rings
        R, a0, a1, (Pt0, C) = W.chopper_mag_geometry()
        sv = np.linspace(0.12, 0.88, 7)
        for v in sv:
            a = a0 + (a1 - a0) * v
            nn_ = np.array([math.cos(a), math.sin(a)])
            Pc = C - R * nn_
            d = (0.062 + (0.059 - 0.062) * v) / 2
            c = Pc + nn_ * (-d - 0.0012)
            dist = np.sqrt((q[:, 0] - c[0]) ** 2 + q[:, 1] ** 2 + (q[:, 2] - c[1]) ** 2)
            dim = tp.smooth(0.00125 - dist, 0.0, 0.0008)
            tint = tp.smooth(0.0024 - dist, 0.0, 0.0008) * (1 - dim)
            S.h[body] -= 1.2e-4 * dim
            S.bc[body] = S.bc[body] * (1 - 0.15 * dim)[:, None] + (lin("4a3f3a") - S.bc[body]) * (0.25 * tint)[:, None]
        front = (q[:, 0] * n[body, 0] > 0) & (np.abs(q[:, 1]) < 0.0012)
        S.h[body] += 3e-5 * front * np.sin(np.hypot(q[:, 0], q[:, 2]) / 0.0009 * 2 * math.pi)
    S.steel(S.sel(W.DARK), lin("3c3e43"), 0.50, np.clip(hz + floor, 0, 1), lin("9aa0a8"), worn_rough=0.24, octave=3)
    edge_wear(S, S.sel(W.DARK), lin("9aa0a8"), 1.2, octave=44)
    S.plain(S.sel(W.BORE), lin("050506"), 0.7, 0.0)
    S.steel(S.sel(W.BRASS), lin("caa23d"), 0.27, hz * 0, lin("e2c46a"), worn_rough=0.2, cvar=0.03, octave=6)
    S.steel(S.sel(W.COPPER), lin("b5683a"), 0.29, hz * 0, lin("d08a5a"), worn_rough=0.2, cvar=0.03, octave=8)
    S.steel(S.sel(W.PRIMER), lin("caa23d") * np.array([0.95, 0.9, 0.85], np.float32), 0.32, hz * 0, lin("caa23d"),
            octave=10)
    S.dirt(0.9)
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
