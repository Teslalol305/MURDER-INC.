"""RATTLER surfaces: mid-grey phosphated stamped sheet, darker blackened steel, black stippled polymer, dull zinc wire, tan woven
nylon strap, bright bolt steel.

Every channel is a function of the 3D position on the baked geometry maps (mi.texpaint), like the CHOPPER's and the NINE's: wear
sits where hands, slings and the bolt really rub, grime where the short-range occlusion finds a recess, markings are laid on the
flanks in metres. The heavy per-texel painters run in pieces of 1.5 M texels (a 4K set is ~13 M covered texels).

  sheet    phosphated #6a6e73, metallic 1, roughness 0.52 +- 0.08, orange peel in the height, a fine crystalline grain; bright bare
           steel along the receiver's lower edges, the well's mouth, the selector and the handle's stem; the spot welds and the
           seam bead darker and rougher (heat tint); carbon streaks round the ejection port
  steel    blackened #34373c (shroud, barrel, muzzle device, sights, handle), roughness 0.45; carbon on the vents and at the muzzle
  polymer  black #1b1b1d, roughness 0.70, 1.15 mm stipple on the grip, chalky dark grey where the hand rubs
  zinc     dull zinc #8b9096, roughness 0.50, metallic 1, a faint white bloom
  strap    tan nylon webbing #a58f66, roughness 0.9, a 1.15 mm twill weave in the height, darker stitching, frayed edge, the palm's
           grime
"""
import math

import numpy as np

from mi import texpaint as tp
from assets import weapons as W
from assets import _weapons_tex as TX
from assets import _weapons_rattler as S0

lin = W.hexlin
gauss = W.gauss
SHEET, BLACK, BRIGHT, POLY, ZINC, STRAP, BORE, WHITE = S0.SHEET, S0.BLACK, S0.BRIGHT, S0.POLY, S0.ZINC, S0.STRAP, S0.BORE, S0.WHITE
CHUNK = 1_500_000


def release(G):
    """Free the geometry maps the flat per-texel arrays already hold (position, normal, ids, edge masks); the AO, cavity, mask and
    texel-size maps stay (channels() reads them)."""
    for k in ("pos", "nrm", "id", "part", "edge", "convex"):
        G.pop(k, None)


def pieces(sel, size=CHUNK):
    yield from TX.chunks(sel, size)


# ----------------------------------------------------------------------------------------------- handling

def handling(p, n):
    """Where the RATTLER is rubbed (0..1): the firing hand on the grip, the support palm on the strap, the thumb on the selector and
    the T-handle, the trigger finger, the rail lugs, the magazine well's mouth, the lower edges that rub a holster or a bag."""
    H = np.zeros(len(p), np.float32)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    H += gauss(p, (0.062, -0.015, -0.082), 0.030, 0.85)                              # palm on the grip's right face
    H += gauss(p, (0.062, 0.016, -0.082), 0.030, 0.55)                               # the left side of the grip
    H += gauss(p, (0.082, 0.0, -0.100), 0.030, 0.70) * (n[:, 0] > 0.2)               # fingers on the front strap
    H += gauss(p, (0.034, 0.0, -0.050), 0.020, 0.60)                                 # web of the hand
    H += gauss(p, (0.040, 0.0, -0.140), 0.020, 0.60)                                 # grip heel
    H += gauss(p, (0.133, 0.0, -0.065), 0.012, 0.95)                                 # trigger blade
    H += gauss(p, (0.115, 0.0, -0.088), 0.020, 0.45)                                 # guard bottom
    H += gauss(p, (0.065, 0.025, -0.017), 0.014, 0.95)                               # selector thumb pad
    H += gauss(p, (0.092, 0.0, 0.048), 0.018, 0.95)                                  # the T-handle's head
    H += gauss(p, (0.098, 0.0, 0.032), 0.010, 0.85)                                  # its stem
    H += gauss(p, (0.012, 0.0, 0.060), 0.012, 0.70)                                  # rear sight leaf
    H += gauss(p, (0.412, 0.0, 0.058), 0.010, 0.70)                                  # front sight post
    H += gauss(p, (0.405, 0.0, 0.040), 0.020, 0.45)                                  # its tower
    H += gauss(p, (0.315, 0.0, -0.0275), 0.045, 0.95)                                # support palm on the strap's underside
    H += gauss(p, (0.330, 0.026, -0.010), 0.040, 0.55) + gauss(p, (0.330, -0.026, -0.010), 0.040, 0.55)   # fingers round the shroud
    H += (z < -0.032) * (x > 0.004) * (x < 0.268) * tp.smooth(-z, 0.032, 0.040) * 0.50   # the lower edges (holster, bag, bench)
    H += gauss(p, (0.166, 0.0, -0.042), 0.030, 0.85)                                 # the magazine well's mouth
    H += gauss(p, (0.148, -0.020, -0.058), 0.008, 0.90)                              # magazine catch
    H += (x > 0.111) * (x < 0.233) * (z > 0.036) * (np.abs(y) < 0.012) * 0.55        # rail lugs
    H += tp.smooth(x, 0.452, 0.465) * 0.85                                           # muzzle device mouth
    H += (x > 0.410) * (x < 0.466) * (z > 0.006) * 0.35                              # its top (over the slots)
    H += (x < 0.006) * 0.40                                                          # the rear cap
    H += gauss(p, (0.170, -0.022, 0.012), 0.035, 0.55)                               # the ejection port's lips
    H += gauss(p, (0.021, 0.023, 0.022), 0.015, 0.65)                                # sling plate
    H += (np.abs(y) > 0.024) * (x > 0.0) * (x < 0.255) * (z > -0.036) * 0.25         # the stock frame
    H += (x > 0.240) * (np.abs(y) > 0.024) * 0.55                                    # the butt plate
    H += gauss(p, (0.0, 0.0285, 0.0), 0.020, 0.45)                                   # hinge
    return np.clip(H, 0, 1)


# ----------------------------------------------------------------------------------------------- text and marks

FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
PPM = 20000.0                                              # marking images: 0.05 mm per pixel


def text_plate(w_mm, h_mm, items):
    """White-on-black marking image (float 0..1) of a w x h mm plate. items: (kind, text, x_mm, z_mm, cap_mm) with kind
    'mono' | 'star'; x, z are the plate's centre of the item (mm from the plate's lower left), cap = capital height."""
    from PIL import Image, ImageDraw, ImageFont
    w, h = int(w_mm * PPM / 1000), int(h_mm * PPM / 1000)
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for kind, text, x, z, cap in items:
        px = cap * PPM / 1000
        cx, cy = x * PPM / 1000, h - z * PPM / 1000
        if kind == "star":
            r = px * 0.5
            pts = []
            for k in range(10):
                a = -math.pi / 2 + k * math.pi / 5
                rr = r if k % 2 == 0 else r * 0.42
                pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
            d.polygon(pts, fill=255)
        else:
            f = ImageFont.truetype(FONT_MONO, int(px / 0.73))
            d.text((cx, cy), text, fill=255, font=f, anchor="mm")
    return np.asarray(im, np.float32) / 255.0


def lay(S, img, axes, origin, size, facing, depth, colour=None, flip=False, gate=None):
    """Lay a marking on a flank: height -= depth where the text is; colour (a linear rgb) painted over it when given."""
    a = img[:, ::-1] if flip else img
    ax = "XYZ".index(facing[-1])
    sg = -1.0 if facing[0] == "-" else 1.0
    v = tp.raster_plane(a, S.p, axes, origin, size) * (S.n[:, ax] * sg > 0.7)
    if gate is not None:
        v = v * gate
    S.h -= depth * v
    if colour is None:
        S.bc *= (1.0 - 0.14 * v)[:, None]
        S.rough += 0.06 * v
    else:
        S.bc += (np.asarray(colour, np.float32)[None, :] - S.bc) * (0.92 * v)[:, None]
        S.rough += (0.62 - S.rough) * v * 0.8
    return v


# ----------------------------------------------------------------------------------------------- surfaces

def sheet(S, sel, hz):
    """Phosphated stamped sheet on the texels of sel (one piece of the chunking)."""
    if not sel.any():
        return
    S.steel(sel, lin("6a6e73"), 0.52, hz, lin("c0c4c9"), worn_rough=0.26, edge_gain=1.15, rvar=0.08, cvar=0.04, octave=2, base_thr=0.90,
            rub_polish=0.16, scratch=0.65)
    p, N = S.p[sel], S.N
    # orange peel of the stamping and the fine crystalline grain of the phosphate
    S.h[sel] += 2.6e-6 * N.fbm(p, 900.0, 2, octave0=330) + 2.0e-6 * N.fbm(p, 6000.0, 2, octave0=333)
    # the sheet's macro mottling (rolled, then phosphated in batches): darker and lighter cloudy patches
    mac = N.fbm(p, 9.0, 2, octave0=336)
    S.bc[sel] *= (1.0 + 0.05 * mac)[:, None]


def blackened(S, sel, hz, octave=0):
    if not sel.any():
        return
    S.steel(sel, lin("34373c"), 0.45, hz, lin("8a9098"), worn_rough=0.24, edge_gain=1.05, rvar=0.06, cvar=0.03, octave=octave + 5,
            base_thr=0.90, rub_polish=0.14, scratch=0.5)
    p, N = S.p[sel], S.N
    S.h[sel] += 3.5e-6 * N.fbm(p, 7000.0, 2, octave0=340) + 1.6e-6 * N.fbm(p, 2400.0, 2, octave0=343)


def polymer_black(S, sel, hz):
    """Black moulded polymer: #1b1b1d, roughness 0.70 mottled, moulded grain; chalky dark grey on the convex edges a hand rubs."""
    if not sel.any():
        return
    p, n, N = S.p[sel], S.n[sel], S.N
    mott = N.fbm(p, 55.0, 3, octave0=350)
    fine = N.fbm(p, 900.0, 2, octave0=353)
    col = lin("1b1b1d")[None, :] * (1.0 + 0.10 * mott[:, None] + 0.03 * fine[:, None])
    r = 0.70 + 0.05 * mott + 0.02 * fine
    h = np.clip(hz[sel], 0, 1)
    e = S.convex[sel]
    brk = N.fbm(p, 420.0, 3, octave0=357)
    w = tp.smooth(e * (0.50 + 1.25 * h) + 0.30 * brk - 0.70 + 0.30 * h * h, 0.0, 0.22)
    chalk = lin("55565a")
    col = col + (chalk[None, :] - col) * (0.85 * w)[:, None]
    r = r + (0.55 - r) * w * 0.6
    rub = np.clip(h * (0.5 + 0.5 * N.fbm(p, 130.0, 2, octave0=360)), 0, 1)
    r = r - 0.16 * rub * (1.0 - w)
    col = col * (1.0 + 0.30 * rub * (1.0 - w))[:, None]
    sc = S.scratches(0.5, along="X", sel=sel, freq_across=1800.0, octave=363) * tp.smooth(h + 0.25 * e, 0.12, 0.6)
    col = col + (chalk[None, :] - col) * (0.35 * sc)[:, None]
    S.bc[sel] = col
    S.rough[sel] = np.clip(r, 0.3, 0.9)
    S.metal[sel] = 0.0
    S.h[sel] += 1.4e-5 * N.fbm(p, 2400.0, 2, octave0=366) + 4.0e-6 * N.fbm(p, 9000.0, 1, octave0=368) - 3.0e-5 * w * (0.5 + 0.5 * brk)


def zinc_wire(S, sel, hz):
    if not sel.any():
        return
    p, N = S.p[sel], S.N
    mac = N.fbm(p, 40.0, 3, octave0=370)
    mic = N.fbm(p, 900.0, 2, octave0=373)
    col = lin("8b9096")[None, :] * (1.0 + 0.07 * mac[:, None] + 0.03 * mic[:, None])
    h = np.clip(hz[sel], 0, 1)
    bloom = tp.smooth(N.fbm(p, 120.0, 3, octave0=376), 0.30, 0.80) * (1.0 - 0.6 * h)           # white zinc bloom
    col = col + (lin("b9bcbe")[None, :] - col) * (0.25 * bloom)[:, None]
    e = S.convex[sel]
    w = tp.smooth(e * (0.6 + 1.2 * h) + 0.25 * N.fbm(p, 500.0, 3, octave0=379) - 0.75, 0.0, 0.25)
    col = col + (lin("cdd0d3")[None, :] - col) * (0.7 * w)[:, None]
    r = 0.50 + 0.07 * mac + 0.04 * mic - 0.12 * h * (1.0 - w) + 0.10 * bloom
    sc = S.scratches(0.6, along="X", sel=sel, freq_across=1800.0, octave=382) * tp.smooth(h + 0.2 * e, 0.1, 0.6)
    col = col * (1.0 + 0.15 * sc)[:, None]
    S.bc[sel] = col
    S.rough[sel] = np.clip(r, 0.25, 0.8)
    S.metal[sel] = 1.0
    S.h[sel] += 3.0e-6 * N.fbm(p, 2500.0, 2, octave0=385) - 4.0e-6 * bloom


def strap(S, sel, hz):
    """Tan woven nylon webbing wrapped round the shroud (axis X): a twill weave in the height along the strap's own coordinates (axial
    x, arc length round the tube), darker stitching on the tail's raised thread rows, a frayed edge, the palm's grime."""
    if not sel.any():
        return
    p, n, N = S.p[sel], S.n[sel], S.N
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    r = np.hypot(y, z)
    arc = r * np.arctan2(-y, z)                                        # arc length from the top toward the right side
    pitch = 0.00115
    u, v = x / pitch, arc / pitch
    tw = np.sin(2 * math.pi * (u + 0.5 * v))
    warp = np.sin(2 * math.pi * v * 0.5)
    weave = 0.55 * tw + 0.45 * warp * np.sin(2 * math.pi * u * 0.5)
    hz_ = np.clip(hz[sel], 0, 1)
    mott = N.fbm(p, 45.0, 3, octave0=390)
    fine = N.fbm(p, 1400.0, 2, octave0=393)
    col = lin("a58f66")[None, :] * (1.0 + 0.08 * mott[:, None] + 0.04 * fine[:, None] + 0.07 * weave[:, None])
    dark = tp.smooth(hz_, 0.15, 0.95)
    grime = lin("3d3326")
    col = col + (grime[None, :] - col) * (0.60 * dark * (0.6 + 0.4 * N.fbm(p, 200.0, 2, octave0=396)))[:, None]
    # the stitching: the raised bars of the stitched box (r > 29.45) in a darker thread
    thread = (r > 29.42) & (r < 30.2)
    col = np.where(thread[:, None], lin("5b4d33")[None, :] * (1.0 + 0.1 * fine[:, None]), col)
    # frayed edges: the two edges of the band and the tail's free end get paler, hairy
    edge = np.maximum(tp.smooth(np.abs(x - 290.0e-3) * -1.0 + 0.0014, 0.0, 0.0014), tp.smooth(np.abs(x - 350.0e-3) * -1.0 + 0.0014, 0.0, 0.0014))
    hairs = tp.smooth(N.fbm(p, (40.0, 5000.0, 5000.0), 2, octave0=399), 0.1, 0.6)
    col = col + (lin("c7b48c")[None, :] - col) * (0.55 * edge * hairs)[:, None]
    S.bc[sel] = col
    S.rough[sel] = np.clip(0.90 - 0.08 * weave * 0.3 + 0.05 * dark, 0.5, 1.0)
    S.metal[sel] = 0.0
    S.h[sel] += 1.25e-4 * (0.5 + 0.5 * weave) + 1.0e-5 * N.fbm(p, 3500.0, 1, octave0=402) * (0.5 + 0.5 * hairs) - 2.0e-5 * dark
    return None


def dirt_chunked(S, amount, carbon=None, oil=None):
    """Surf2.dirt in pieces: dust and dried oil in the recesses (short-range occlusion), carbon where given; metallic drops with a
    narrow step where the deposit is thick."""
    allsel = np.ones(len(S.p), bool)
    dust = lin("34312c")
    for part in pieces(allsel, 2_000_000):
        idx = np.nonzero(part)[0]
        p, N = S.p[idx], S.N
        g = tp.smooth(1.0 - S.cav[idx], 0.12, 0.50) * 0.85 + tp.smooth(1.0 - S.ao[idx], 0.35, 0.90) * 0.35
        g = np.clip(g * (0.45 + 0.75 * N.fbm(p, 260.0, 3, octave0=60)) * amount, 0, 1)
        S.bc[idx] += (dust[None, :] - S.bc[idx]) * (g * 0.80)[:, None]
        S.rough[idx] += (0.78 - S.rough[idx]) * g
        thick = tp.smooth(g, 0.42, 0.52)
        if carbon is not None:
            c = np.clip(carbon[idx] * (0.6 + 0.55 * N.fbm(p, 380.0, 3, octave0=63)), 0, 1)
            S.bc[idx] += (lin("0c0b0a")[None, :] - S.bc[idx]) * c[:, None]
            S.rough[idx] += (0.66 - S.rough[idx]) * c
            thick = np.maximum(thick, tp.smooth(c, 0.45, 0.55))
        if oil is not None:
            o = np.clip(oil[idx] * (0.5 + 0.6 * N.fbm(p, 90.0, 2, octave0=66)), 0, 1)
            S.rough[idx] -= 0.12 * o
            S.bc[idx] *= (1 - 0.12 * o)[:, None]
        S.metal[idx] *= (1.0 - thick)


# ----------------------------------------------------------------------------------------------- the gun

RIGHT_PLATE = (0.022, -0.0245, 0.112, 0.014)        # x0, z0, width, height of the marking band between the ribs (right flank)
LEFT_LEGEND = (0.0765, -0.0325, 0.0055, 0.0240)     # the selector's legends beside the lever's arc (left flank)


def paint_rattler(G):
    S = TX.Surf2(G, 411)
    release(G)
    p, n, N = S.p, S.n, S.N
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    hz = handling(p, n)
    sh, bk, br, pl, zn, st, bo, wh = (S.sel(i) for i in (SHEET, BLACK, BRIGHT, POLY, ZINC, STRAP, BORE, WHITE))
    for part in pieces(sh):
        sheet(S, part, hz)
    for part in pieces(bk):
        blackened(S, part, hz)
    for part in pieces(br):
        S.steel(part, lin("b1b6bd"), 0.25, hz, lin("d4d8dc"), worn_rough=0.2, rvar=0.03, cvar=0.03, octave=9, base_thr=1.2,
                rub_polish=0.10)
        q = S.p[part]
        S.h[part] += 6e-7 * N.fbm(q, (300.0, 16000.0, 16000.0), 2, octave0=330)
    for part in pieces(pl):
        polymer_black(S, part, hz)
    grip = pl & (z < -0.045) & (x > 0.028) & (x < 0.100)
    for part in pieces(grip):
        S.stipple(part, 0.00115, 2.4e-4)
    for part in pieces(zn):
        zinc_wire(S, part, hz)
    for part in pieces(st):
        strap(S, part, hz)
    for part in pieces(bo):
        pp = S.p[part]
        v = N.fbm(pp, 120.0, 2, octave0=450)
        S.bc[part] = lin("0b0b0a")[None, :] * (1.0 + 0.30 * v[:, None])
        S.rough[part] = 0.66 + 0.10 * v
        S.metal[part] = 0.0
        S.h[part] += 3e-6 * N.fbm(pp, 3000.0, 1, octave0=452)
    if wh.any():
        S.bc[wh] = lin("d8d6c8")[None, :]
        S.rough[wh] = 0.6
        S.metal[wh] = 0.0
    # ---- the seam bead on the cover: darker, rougher, a ripple of the weld along X; the spot welds a little lighter
    seam = sh & (np.abs(y) < 0.00095) & (z > 0.0295) & (z < 0.0310) & (n[:, 2] > 0.3)
    ripple = 0.5 + 0.5 * np.sin(x / 0.0019 * 2 * math.pi + 3.0 * N.fbm(p, 200.0, 1, octave0=460))
    S.h += seam * (4.5e-5 * ripple)
    S.bc += (lin("3d3a34") - S.bc) * (seam * 0.55)[:, None]
    S.rough += seam * 0.12
    welds = sh & (np.abs(np.abs(y) - 0.0222) < 0.0007) & (z > -0.0380) & (z < -0.0330)
    S.bc += (lin("8c9094") - S.bc) * (welds * 0.30)[:, None]
    # ---- the selector legends and the stamped markings
    x0, z0, w, h_ = RIGHT_PLATE
    plate = text_plate(w * 1000, h_ * 1000, [("mono", "SMG 9", 15.0, 7.0, 5.4), ("star", "", 37.0, 7.0, 7.0), ("mono", "R-545", 59.0, 7.0, 5.4),
                                           ("mono", "R3-0912", 94.0, 7.0, 4.0)])
    lay(S, plate, (0, 2), (x0, z0), (w, h_), "-Y", 1.8e-4)
    xs0, zs0, ws, hs = LEFT_LEGEND
    leg = text_plate(ws * 1000, hs * 1000, [("mono", "S", 2.75, 20.5, 3.0), ("mono", "1", 2.75, 12.0, 3.0), ("mono", "A", 2.75, 3.5, 3.0)])
    lay(S, leg, (0, 2), (xs0, zs0), (ws, hs), "+Y", 1.2e-4, colour=lin("cfcdbd"), flip=True)
    # ---- the carbon and the oil: round the port, on the vents' bridges, at the muzzle, on the bolt's face and the breech
    r = np.hypot(y, z)
    carbon = (gauss(p, (0.172, -0.022, 0.012), 0.030, 0.55) * (y < -0.010)
              + tp.smooth(x, 0.4585, 0.4652) * (n[:, 0] > 0.6) * 0.65                                   # the muzzle device's face
              + (x > 0.416) * (x < 0.462) * bk * (z > 0.004) * 0.40                                      # over the slots
              + (x > 0.455) * (r < 0.0058) * 0.8                                                          # the bore's lip
              + (x > 0.325) * (x < 0.400) * (r > 0.0250) * (r < 0.0262) * 0.28 * (np.abs(n[:, 0]) < 0.5)   # the shroud's vents
              + (x > 0.196) * (x < 0.202) * (n[:, 0] > 0.6) * (r < 0.0135) * 0.5)                         # chamber and bolt face
    oil = (gauss(p, (0.170, -0.020, 0.010), 0.040, 0.9) * (y < -0.004) + gauss(p, (0.140, 0.0, 0.010), 0.060, 0.6) * (bk | br)
           + 0.45 * hz * sh)
    dirt_chunked(S, 0.85, carbon=np.clip(carbon, 0, 1), oil=np.clip(oil, 0, 1))
    S.rough = np.maximum(S.rough, 0.16 * (S.metal > 0.5))
    return S.channels(height_blur=0.35)


# ----------------------------------------------------------------------------------------------- the magazine

def paint_rattler_mag(G):
    """RATTLER magazine: phosphated grey stamped steel with bright insertion scuffs and pouch scratches, ribs worn on their crowns,
    a black polymer floor plate with its drag tab and the follower, dark feed lips, the rounds. Weld seam on the rear face."""
    S = TX.Surf2(G, 17)
    release(G)
    p, n, N = S.p, S.n, S.N
    top = tp.smooth(p[:, 2], -0.060, -0.032)
    floor = tp.smooth(-p[:, 2], 0.200, 0.213)
    hz = np.clip(top * 0.85 + floor * 0.75 + gauss(p, (0.166, 0.0, -0.150), 0.040, 0.45), 0, 1)
    body = S.sel(SHEET)
    for part in pieces(body):
        sheet(S, part, hz)
    if body.any():
        q = p[body]
        pouch = S.scratches(0.9, along="Z", sel=body, freq_across=9000.0, freq_long=40.0, octave=170) * tp.smooth(-q[:, 2], 0.10, 0.16) \
            * (np.abs(n[body, 1]) > 0.6)
        S.bc[body] += (lin("b9bdc2") - S.bc[body]) * (0.5 * pouch)[:, None]
        S.rough[body] -= 0.06 * pouch
        for xr in (0.156, 0.176):                                    # the stamped ribs read slightly worn on their crowns
            rr = tp.smooth(0.0021 - np.abs(q[:, 0] - xr), 0.0, 0.0008) * (np.abs(q[:, 1]) > 0.0150)
            S.bc[body] += (lin("a0a4a9") - S.bc[body]) * (0.30 * rr * tp.smooth(N.fbm(q, 90.0, 2, octave0=172), -0.2, 0.5))[:, None]
        spine = (np.abs(q[:, 1]) < 0.0011) & (q[:, 0] < 0.1465) & (n[body, 0] < -0.5)             # the weld bead down the rear
        S.h[body] += 6e-5 * spine * (0.5 + 0.5 * np.sin(q[:, 2] / 0.0019 * 2 * math.pi))
        S.bc[body] += (lin("3d3a34") - S.bc[body]) * (0.5 * spine)[:, None]
    for part in pieces(S.sel(POLY)):
        polymer_black(S, part, hz)
    S.plain(S.sel(BORE), lin("050506"), 0.7, 0.0)
    S.steel(S.sel(W.BRASS), lin("caa23d"), 0.27, hz * 0, lin("e2c46a"), worn_rough=0.2, cvar=0.03, octave=6)
    S.steel(S.sel(W.COPPER), lin("b5683a"), 0.29, hz * 0, lin("d08a5a"), worn_rough=0.2, cvar=0.03, octave=8)
    S.steel(S.sel(W.PRIMER), lin("caa23d") * np.array([0.95, 0.9, 0.85], np.float32), 0.32, hz * 0, lin("caa23d"), octave=10)
    plate = text_plate(30.0, 14.0, [("mono", "32", 15.0, 7.0, 6.0)])
    lay(S, plate, (0, 2), (0.1500, -0.1050), (0.030, 0.014), "-Y", 1.2e-4)
    dirt_chunked(S, 0.9)
    return S.channels(height_blur=0.4)
