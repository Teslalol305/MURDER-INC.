"""Round 4, lane 2: surfaces of the parts kit, per texel from the geometry maps (mi.texpaint), like the guns'.

Two unique 2K sets:
  Weapon_Parts      BC N ORM E  the optics, muzzle devices, grips and the laser: black hard-anodised aluminium (dielectric
                                 oxide, bare bright metal where the edges are rubbed), parkerised and blued steel, brushed
                                 stainless with heat-darkened ends, stippled black polymer, laminated wood, black rubber,
                                 carbon in the compensator's ports, the red emitter (E)
  Weapon_PartsMags  BC N ORM    the three extended magazines: stamped steel (dark parkerised for the rifle, light phosphated
                                 for the SMG, brushed for the NINE), polymer floor plates and sleeve, the NINE's polished gold
                                 pad, brass cases and copper-jacketed bullets, the dark inside
The painters get the geometry maps of the atlas object (parts laid out in a row, `offsets` undo that) and return the
channels for bake.write_set."""
import math

import numpy as np

from mi import texpaint as tp
from assets import weapons as W
from assets import _weapons_tex as TX
from assets import _weapons_parts_geo as G

L = W.L
lin = W.hexlin
gauss = W.gauss


class PartSurf(TX.Surf2):
    """Surf2 with positions in each part's own frame (the atlas lays the parts out in a row)."""

    def __init__(self, Gm, seed, offsets):
        super().__init__(Gm, seed)
        self.pid = np.rint(self.part).astype(np.int32)
        off = np.zeros((int(self.pid.max()) + 1 if len(self.pid) else 1, 3), np.float32)
        for k, v in offsets.items():
            if k < len(off):
                off[k] = v
        self.p = (self.p - off[np.clip(self.pid, 0, len(off) - 1)]).astype(np.float32)

    def of(self, k, *ids):
        m = self.pid == k
        return m & np.isin(self.id, ids) if ids else m

    def anodised(self, sel, handling, base="212225", rough=0.44, bare="a3a7ad", edge_gain=0.85, octave=0):
        """Hard-anodised aluminium: a dark dielectric oxide layer, bare bright aluminium (metallic 1) where the convex
        edges are rubbed; fine bead-blast grain in the normal map."""
        if not sel.any():
            return np.zeros(0, np.float32)
        p, N = self.p[sel], self.N
        w, rub = self.wear(sel, handling, edge_gain, 0.95, octave=octave)
        mac = N.fbm(p, 40.0, 3, octave0=120 + octave)
        mic = N.fbm(p, 600.0, 2, octave0=123 + octave)
        col = np.asarray(lin(base), np.float32)[None, :] * (1.0 + 0.10 * mac[:, None] + 0.05 * mic[:, None])
        col = col * (1.0 + 0.30 * rub[:, None])
        wb = tp.smooth(w, 0.62, 0.80)                          # binary: oxide or bare metal (a worn edge, not a bare face)
        bc = np.asarray(lin(bare), np.float32)[None, :] * (1.0 + 0.06 * mic[:, None])
        self.bc[sel] = col + (bc - col) * wb[:, None]
        r = rough + 0.04 * mac + 0.03 * mic - 0.10 * rub
        self.rough[sel] = r + (0.30 - r) * wb
        self.metal[sel] = wb
        self.h[sel] += 2.4e-6 * N.fbm(p, 3500.0, 2, octave0=126 + octave) - 3e-6 * w
        return w

    def engrave_on(self, k, img, axes, centre, size, facing, depth=5e-5):
        """Engraved marking on part k only: img (texpaint.text_image) laid on a plane, `centre` and `size` in metres (part
        frame), on the faces that look along `facing` ('+Y' ...)."""
        ax = "XYZ".index(facing[-1])
        sg = -1.0 if facing[0] == "-" else 1.0
        origin = (centre[0] - size[0] / 2, centre[1] - size[1] / 2)
        v = tp.raster_plane(img, self.p, axes, origin, size) * (self.n[:, ax] * sg > 0.7) * (self.pid == k)
        self.h -= depth * v
        self.bc *= (1 - 0.45 * v)[:, None]
        self.rough += 0.15 * v
        return v

    def rubber(self, sel, base="101010", rough=0.86):
        if not sel.any():
            return
        p = self.p[sel]
        v = self.N.fbm(p, 120.0, 3, octave0=130)
        self.bc[sel] = np.asarray(lin(base), np.float32)[None, :] * (1 + 0.12 * v[:, None])
        self.rough[sel] = rough + 0.05 * v
        self.metal[sel] = 0.0
        self.h[sel] += 4e-6 * self.N.fbm(p, 2500.0, 1, octave0=131)


def heat(S, sel, x0, x1, along=0, strength=1.0):
    """Heat-darkened metal along the axis: from x0 to x1 (metres, part frame) the finish goes through straw, purple and blue
    to a dark brown-grey, with rainbow banding (thin-oxide interference). Applied on top of the metal that is already
    painted on `sel`; the metal stays metal."""
    if not sel.any():
        return
    p = S.p[sel]
    t = np.clip((p[:, along] - x0) / max(x1 - x0, 1e-6), 0, 1)
    t = t + 0.06 * S.N.fbm(p, (40.0, 400.0, 400.0), 2, octave0=140)
    t = np.clip(t, 0, 1)
    stops = [(0.00, lin("8d8579")), (0.18, lin("9b7a45")), (0.34, lin("7a4a3a")), (0.50, lin("4a3d78")), (0.68, lin("26365e")),
             (0.84, lin("2a2b30")), (1.00, lin("1c1b1c"))]
    col = np.zeros((len(t), 3), np.float32)
    for c in range(3):
        col[:, c] = np.interp(t, [s[0] for s in stops], [s[1][c] for s in stops])
    a = tp.smooth(t, 0.02, 0.2)[:, None] * strength
    S.bc[sel] = S.bc[sel] * (1 - a) + col * a
    S.rough[sel] = S.rough[sel] + (0.52 - S.rough[sel]) * a[:, 0] * 0.8


def hand_map(S, spots):
    """0..1 handling per texel: spots = [(part, (x, y, z) mm, radius mm, weight)] in each part's frame."""
    out = np.full(len(S.p), 0.16, np.float32)
    for k, c, r, w in spots:
        m = S.pid == k
        if not m.any():
            continue
        d = np.linalg.norm(S.p[m] - np.asarray(c, np.float32) * 1e-3, axis=1)
        out[m] = np.maximum(out[m], w * np.exp(-(d / (r * 1e-3)) ** 2))
    return np.clip(out, 0, 1)


# part indices of the hardware set
RD, SC, SU, CP, SP, FV, FW, FA, LZ = range(9)


def paint_parts(Gm, offsets=None, **kw):
    S = PartSurf(Gm, 301, offsets or {})
    p, n = S.p, S.n
    hand = hand_map(S, [
        (RD, (0, -18, -4), 8, 0.9), (RD, (4, 0, 47), 8, 0.8), (RD, (4, -21, 24.5), 8, 0.8), (RD, (24, 0, 43), 9, 0.7),
        (RD, (-30, 0, 24.5), 20, 0.5), (RD, (0, 0, 41), 40, 0.4),
        (SC, (6, 0, 53), 12, 0.8), (SC, (6, -26, 27.5), 12, 0.8), (SC, (-60, 0, 27.5), 10, 0.8), (SC, (80, 0, 27.5), 10, 0.7),
        (SC, (0, -14, -4), 10, 0.8), (SC, (80, 0, 27.5), 30, 0.4),
        (SU, (4, 0, 0), 12, 0.7), (SU, (200, 0, 0), 14, 0.6), (SU, (100, 0, 19.5), 60, 0.35),
        (SP, (4, 0, 0), 10, 0.6), (SP, (150, 0, 0), 12, 0.6), (SP, (80, 0, 16), 50, 0.4),
        (CP, (50, 0, 0), 20, 0.5), (CP, (60, 0, 0), 14, 0.6),
        (FV, (0, 0, -52), 40, 0.9), (FW, (0, 0, -48), 40, 0.9), (FA, (-12, 0, -30), 28, 0.9), (FA, (20, 0, -30), 40, 0.6),
        (LZ, (-6, -15, -12), 8, 0.8), (LZ, (0, 0, -16), 24, 0.5)])
    # ------------------------------------------------------------------ black anodised aluminium (the optics' bodies, clamps)
    S.anodised(S.sel(G.AL), hand)
    # ------------------------------------------------------------------ dark steel: screws, knurled caps and knobs
    S.steel(S.sel(G.STEELD), lin("2a2c30"), 0.42, hand, lin("b9bcc2"), worn_rough=0.24, edge_gain=1.0, brushed=None)
    # ------------------------------------------------------------------ blued / nitrided steel: the compensator, saddles
    S.steel(S.sel(G.STEELB), lin("23262b"), 0.46, hand, lin("aeb2b8"), worn_rough=0.24, thin_shift=(lin("3a3f4a"), 0.45))
    # ------------------------------------------------------------------ brushed stainless: the pistol suppressor
    S.brushed_stainless(S.sel(G.STAIN), lin("aeb1b6"), hand, np.clip(S.convex * 1.2 + 0.3 * hand, 0, 1))
    # ------------------------------------------------------------------ heat on the suppressors: front 80 / 60 mm
    su = S.of(SU, G.STEELD)
    S.steel(su, lin("3a3d41"), 0.50, hand, lin("b9bcc2"), worn_rough=0.28, thin_shift=(lin("4a4e55"), 0.3))
    heat(S, su, (210 - 85) * 1e-3, 210 * 1e-3 - 0.003)
    sp = S.of(SP, G.STAIN)
    heat(S, sp, (155 - 65) * 1e-3, 155 * 1e-3 - 0.003, strength=0.95)
    # ------------------------------------------------------------------ polymer: grips and the laser body (stippled)
    pol = S.sel(G.POLY)
    S.polymer(pol, lin("1c1d20"), 0.66, hand, var=0.04)
    grips = pol & np.isin(S.pid, (FV, FA))
    S.stipple(grips & (np.abs(n[:, 2]) < 0.9), 0.0011, 1.6e-4)
    S.stipple(S.of(LZ, G.POLY), 0.0013, 8e-5)
    # the angled grip's two stippled side panels are rougher still
    # ------------------------------------------------------------------ wood: the CHOPPER grip (laminated, the same stain)
    S.wood_laminate(S.sel(G.WOODG), L["wood"], ply_axis=0, grain_axis=2, handling=hand)
    # ------------------------------------------------------------------ rubber, red emitter, the dark inside
    S.rubber(S.sel(G.RUBBER))
    red = S.sel(G.RED)
    S.plain(red, np.array([0.80, 0.015, 0.010], np.float32), 0.16, 0.0, var=0.03)
    S.emit[red] = np.array([1.0, 0.045, 0.03], np.float32)[None, :] * 1.0
    S.plain(S.sel(G.BORED), np.array([0.004, 0.004, 0.0045], np.float32), 0.88, 0.0, var=0.2)
    S.plain(S.sel(G.CARBON), np.array([0.010, 0.010, 0.010], np.float32), 0.8, 0.0)
    # carbon in the compensator's ports and chamber, soot round the suppressors' bores
    cp = S.of(CP)
    r_ = np.hypot(p[:, 1], p[:, 2])
    carbon = cp * (tp.smooth(0.30 - S.cav, 0.0, 0.25) * 0.9 + (r_ < 0.0062) * 0.9 + tp.smooth(p[:, 0] * 1e3, 52.0, 62.0) * (r_ < 0.0125) * 0.7)
    mouth = (S.of(SU) | S.of(SP)) & (r_ < 0.0072) & (p[:, 0] > 0.140)
    S.dirt(0.9, carbon=np.clip(carbon + mouth * 0.9, 0, 1))
    # ------------------------------------------------------------------ markings (invented)
    S.engrave_on(RD, tp.text_image([("RD-1  *", 256, 256, 150)], 512), (0, 2), (0.0, 0.0245), (0.026, 0.026), "+Y", 5e-5)
    S.engrave_on(SC, tp.text_image([("SC 4X  *", 256, 256, 150)], 512), (0, 2), (-0.018, 0.0275), (0.034, 0.034), "+Y", 5e-5)
    S.engrave_on(SU, tp.text_image([("SUP-7  *    FRONT >", 256, 256, 100)], 512), (0, 2), (0.060, 0.0), (0.060, 0.060), "+Y", 5e-5)
    S.engrave_on(SP, tp.text_image([("SUP-9  *", 256, 256, 150)], 512), (0, 2), (0.045, 0.0), (0.045, 0.045), "+Y", 5e-5)
    S.engrave_on(LZ, tp.text_image([("RL-2", 256, 256, 170)], 512), (0, 2), (0.0, -0.016), (0.020, 0.020), "+Y", 4e-5)
    S.grime(0.55)
    return binary_metal(S.channels(height_blur=0.5))


def binary_metal(ch):
    """Metallic is binary on every gun set (a texel is metal or it is not; the wear and dirt passes grade the colour and
    the roughness, not the metalness): partly metallic texels render as dull blotchy grey next to the guns' crisp metal."""
    ch["metal"] = (np.asarray(ch["metal"]) >= 0.5).astype(np.float32)
    return ch


# ------------------------------------------------------------------------------------------------ magazines
MR, MS, MP = range(3)


def paint_mags(Gm, offsets=None, **kw):
    S = PartSurf(Gm, 302, offsets or {})
    p, n = S.p, S.n
    hand = hand_map(S, [(MR, (0, 0, -230), 30, 0.9), (MR, (0, 0, -120), 60, 0.4), (MS, (0, 0, -235), 30, 0.9), (MS, (0, 0, -130), 60, 0.4),
                        (MP, (0.012, 0, -0.14), 30, 0.9)])
    st = S.sel(G.MAGST)
    rifle, smg, pis = st & (S.pid == MR), st & (S.pid == MS), st & (S.pid == MP)
    S.steel(rifle, lin("34383a"), 0.58, hand, lin("a6aaaf"), worn_rough=0.26, rvar=0.06, thin_shift=(lin("2d3033"), 0.4), edge_gain=1.0)
    S.steel(smg, lin("6a6e73"), 0.52, hand, lin("c3c6cb"), worn_rough=0.26, rvar=0.06, cvar=0.05, edge_gain=1.0)
    S.brushed_stainless(pis, lin("aeb1b6"), hand, np.clip(S.convex * 1.2 + 0.3 * hand, 0, 1))
    S.polymer(S.sel(G.MAGPOLY), lin("151517"), 0.62, hand, var=0.04)
    S.stipple(S.sel(G.MAGPOLY) & (np.abs(n[:, 2]) < 0.8), 0.0012, 8e-5)
    S.plain(S.sel(G.GOLDM), L["gold"], 0.16, 1.0, var=0.03, rvar=0.03, scratch=0.4)
    S.metal_finish(S.sel(G.BRASSM), L["brass"], L["brass"] * 1.25, 0.26, 1.0, hand * 0, wear_amount=0.4, scratch=0.5, orange=0.3)
    S.metal_finish(S.sel(G.COPPERM), L["copper"], L["copper"] * 1.2, 0.28, 1.0, hand * 0, wear_amount=0.3, scratch=0.3)
    S.plain(S.sel(G.BORED), np.array([0.004, 0.004, 0.0045], np.float32), 0.88, 0.0, var=0.2)
    S.grime(0.7)
    return binary_metal(S.channels(height_blur=0.5))
