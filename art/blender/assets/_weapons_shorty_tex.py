"""SHORTY surfaces: olive injection-moulded polymer, parkerised steel, black rubber, bright bolt steel, tritium.

Every channel is a function of the 3D position on the baked geometry maps (mi.texpaint), like the CHOPPER's and the
NINE's: wear sits where hands, slings and the bolt really rub, grime where the short-range occlusion finds a recess,
markings are laid on the flanks in metres. The heavy per-texel painters run in pieces of 1.5 M texels (a 4K set is
~13 M covered texels; three guns share this machine's memory).

  polymer  #4b5232, roughness 0.58 +- 0.06 mottled, metallic 0; chalky light olive on every convex edge a hand or the
           sling rubs, a faint sheen on rubbed flats, grey-brown grime in slots and stipple; moulded micro texture
           (0.4 mm orange peel, 0.1 mm grain), a 0.4 mm parting line along the top and bottom centre, moulded markings
  steel    parkerised #3b3e39, metallic 1, roughness 0.62 +- 0.08, fine crystalline grain; bright where it is touched
           (trigger, hider mouth, bolt path, rail edges), carbon round the port, the hider and the bolt face
  rubber   black #161616, roughness 0.88, diamond stipple 1.8 mm on the pad
  bolt     bright steel (#b1b6bd, roughness 0.25): the carrier's wear, bolt face and extractor
  tritium  three emissive inserts' worth of E: the front post's rear face (the other two sit on parts of the kit)
"""
import math

import numpy as np

from mi import texpaint as tp
from assets import weapons as W
from assets import _weapons_tex as TX
from assets import _weapons_shorty as S0

lin = W.hexlin
gauss = W.gauss
OLIVE, PARK, BRIGHT, RUBBER, BORE, TRIT, WHITE = S0.OLIVE, S0.PARK, S0.BRIGHT, S0.RUBBER, S0.BORE, S0.TRIT, S0.WHITE
CHUNK = 1_500_000
DETAIL_POLY = "TS_GunDetail_Polymer"
DETAIL_POLY_TILE_M = 0.012


def release(G):
    """Free the geometry maps the flat per-texel arrays already hold (position, normal, ids, edge masks): at 4K that is
    ~0.7 GB of the ~5 GB this painter peaks at. The AO, cavity, mask and texel-size maps stay (channels() reads them)."""
    for k in ("pos", "nrm", "id", "part", "edge", "convex"):
        G.pop(k, None)


def pieces(sel, size=CHUNK):
    yield from TX.chunks(sel, size)


# ----------------------------------------------------------------------------------------------- handling

def handling(p, n):
    """Where the SHORTY is rubbed (0..1): the firing hand on the grip, the support hand and the forend's flanks, the face
    on the cheek rise, the carry handle's bar, the rails' edges, the controls and the muzzle."""
    H = np.zeros(len(p), np.float32)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    H += gauss(p, (0.295, -0.0165, -0.095), 0.030, 0.85)                            # palm on the grip's right face
    H += gauss(p, (0.300, 0.0165, -0.100), 0.030, 0.55)                             # the left side of the grip
    H += gauss(p, (0.318, 0.0, -0.108), 0.032, 0.70) * (n[:, 0] > 0.2)              # fingers on the front strap
    H += gauss(p, (0.286, 0.0, -0.060), 0.020, 0.60)                                # web of the hand
    H += gauss(p, (0.256, 0.0, -0.168), 0.016, 0.70)                                # heel of the grip
    H += (z < -0.150) * (x > 0.245) * (x < 0.30) * 0.35                             # grip base
    H += gauss(p, (0.505, 0.0, -0.052), 0.050, 0.85)                                # support palm on the rail
    H += gauss(p, (0.500, 0.031, -0.012), 0.045, 0.60) + gauss(p, (0.500, -0.031, -0.012), 0.045, 0.60)   # forend flanks
    H += gauss(p, (0.470, 0.0, -0.040), 0.050, 0.40)                                # forend underside
    H += (x > 0.130) * (x < 0.325) * (z > 0.074) * 0.70                             # the handle's bar
    H += (x > 0.118) * (x < 0.150) * (z > 0.045) * (z < 0.080) * 0.45               # the rear leg
    H += gauss(p, (0.070, 0.0, 0.056), 0.035, 0.80)                                 # the cheek rise (cheek weld)
    H += gauss(p, (0.016, 0.0, 0.040), 0.022, 0.60)                                 # heel of the butt
    H += (x < 0.034) * 0.45                                                         # the butt pad
    H += (x > 0.160) * (x < 0.282) * (z > 0.092) * 0.55                             # rail lugs
    H += (x > 0.46) * (x < 0.562) * (z < -0.046) * 0.60                             # underside rail lugs
    H += gauss(p, (0.380, 0.037, 0.012), 0.010, 0.95)                               # charging knob
    H += (x > 0.296) * (x < 0.388) * (y > 0.026) * (z > 0.004) * (z < 0.020) * 0.80  # the knob's path along the slot
    H += gauss(p, (0.275, 0.032, -0.022), 0.014, 0.95)                              # selector thumb pad
    H += gauss(p, (0.368, 0.0, -0.075), 0.012, 0.95)                                # trigger blade
    H += gauss(p, (0.244, -0.029, -0.043), 0.008, 0.80)                             # magazine release
    H += (x > 0.178) * (x < 0.234) * (z < -0.056) * 0.60                            # magazine well lips
    H += tp.smooth(x, 0.680, 0.700) * 0.90                                          # hider mouth
    H += (x > 0.560) * (x < 0.592) * (z > 0.040) * 0.60                             # front sight
    H += gauss(p, (0.575, 0.0, 0.058), 0.010, 0.80)                                 # front post
    H += (x > 0.340) * (x < 0.402) * (y < -0.024) * (z > -0.002) * (z < 0.034) * 0.65   # the ejection port's lips
    H += (x > 0.400) * (x < 0.472) * (y < -0.030) * 0.55                            # the deflector
    H += gauss(p, (0.405, -0.030, -0.052), 0.020, 0.30)
    return np.clip(H, 0, 1)


# ----------------------------------------------------------------------------------------------- text and marks

FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PPM = 20000.0                                              # marking images: 0.05 mm per pixel


def text_plate(w_mm, h_mm, items):
    """White-on-black marking image (float 0..1) of a w x h mm plate. items: (kind, text, x_mm, z_mm, cap_mm) with kind
    'mono' | 'sans' | 'star'; x, z are the plate's centre of the item (mm from the plate's lower left), cap = capital height."""
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
            f = ImageFont.truetype(FONT_MONO if kind == "mono" else FONT_SANS, int(px / 0.73))
            d.text((cx, cy), text, fill=255, font=f, anchor="mm")
    return np.asarray(im, np.float32) / 255.0


def lay(S, img, axes, origin, size, facing, depth, colour=None, flip=False, gate=None):
    """Lay a marking on the flank: height -= depth where the text is; colour (a linear rgb) painted over it when given."""
    a = img[:, ::-1] if flip else img
    ax = "XYZ".index(facing[-1])
    sg = -1.0 if facing[0] == "-" else 1.0
    v = tp.raster_plane(a, S.p, axes, origin, size) * (S.n[:, ax] * sg > 0.7)
    if gate is not None:
        v = v * gate
    S.h -= depth * v
    if colour is None:
        S.bc *= (1.0 - 0.34 * v)[:, None]
        S.rough += 0.10 * v
    else:
        S.bc += (np.asarray(colour, np.float32)[None, :] - S.bc) * (0.92 * v)[:, None]
        S.rough += (0.62 - S.rough) * v * 0.8
    return v


# ----------------------------------------------------------------------------------------------- surfaces

def polymer_olive(S, sel, hz):
    """The olive moulded polymer on the texels of sel (one piece of the chunking): mottled #4b5232, chalky light olive on
    the edges a hand or the sling rubs, handled flats darker and glossier, sun-faded tops, scuffs, vertical grime runs on the
    flanks, scratches along the way the gun is handled."""
    if not sel.any():
        return np.zeros(0, np.float32)
    p, n, N = S.p[sel], S.n[sel], S.N
    pv = S.part[sel]
    mott = N.fbm(p, 55.0, 3, octave0=400)
    fine = N.fbm(p, 900.0, 2, octave0=403)
    drift = N.fbm(p, 5.0, 2, octave0=405)                                           # slow colour drift over the gun
    blot = N.fbm(p, 22.0, 2, octave0=406)                                           # 4-5 cm blotches
    col = lin("4b5232")[None, :] * (1.0 + 0.135 * mott[:, None] + 0.03 * fine[:, None] + 0.08 * drift[:, None]
                                    + 0.075 * blot[:, None]) * (1.0 + 0.05 * (pv - 0.5))[:, None]
    r = 0.58 + 0.07 * mott + 0.02 * fine + 0.03 * blot
    h = np.clip(hz[sel], 0, 1)
    e = S.convex[sel]
    brk = N.fbm(p, 420.0, 3, octave0=407)
    brk2 = N.fbm(p, 80.0, 2, octave0=410)
    w = tp.smooth(e * (0.60 + 1.35 * h) + 0.34 * brk + 0.14 * brk2 - 0.54 + 0.30 * h * h, 0.0, 0.24)
    chalk = lin("8f9674")
    col = col + (chalk[None, :] - col) * (0.90 * w)[:, None]                         # chalky light olive on the edges
    r = r + (0.85 - r) * w
    sun = tp.smooth(n[:, 2], 0.35, 0.95) * (0.55 + 0.45 * N.fbm(p, 14.0, 2, octave0=412))   # top faces fade in the sun
    col = col + (chalk[None, :] - col) * (0.11 * sun)[:, None]
    r = r + 0.05 * sun
    rub = np.clip(h * (0.5 + 0.5 * N.fbm(p, 130.0, 2, octave0=413)), 0, 1)
    r = r - 0.17 * rub * (1.0 - w)                                                    # handled flats: darker, glossier
    col = col * (1.0 - 0.10 * rub * (1.0 - w))[:, None]
    scuff_n = N.fbm(p, (45.0, 420.0, 420.0), 3, octave0=425)                        # thin scuffs along X: dragged, drawn, set down
    scuff = tp.smooth(scuff_n - 0.22, 0.0, 0.30) * tp.smooth(0.7 * h + 0.7 * e + 0.10, 0.30, 0.8)
    col = col + (chalk[None, :] - col) * (0.20 * scuff)[:, None]
    r = r + 0.05 * scuff
    low = tp.smooth(-p[:, 2], 0.0, 0.07)                                            # grime runs down the flanks
    streak = tp.smooth(N.fbm(p, (45.0, 45.0, 3.5), 2, octave0=428), 0.05, 0.55)
    gr = streak * tp.smooth(np.abs(n[:, 1]), 0.6, 0.95) * (0.25 + 0.75 * low) * 0.80
    col = col * (1.0 - 0.30 * gr)[:, None]
    r = r + 0.10 * gr
    sc = S.scratches(0.7, along="X", sel=sel, freq_across=1800.0, octave=420) * tp.smooth(h + 0.25 * e, 0.12, 0.6)
    col = col + (chalk[None, :] - col) * (0.42 * sc)[:, None]
    r = r + 0.06 * sc
    S.bc[sel] = col
    S.rough[sel] = np.clip(r, 0.25, 0.9)
    S.metal[sel] = 0.0
    S.h[sel] += (1.2e-5 * N.fbm(p, 2400.0, 2, octave0=416) + 4.0e-6 * N.fbm(p, 9000.0, 1, octave0=418)
                 - 3.0e-5 * w * (0.5 + 0.5 * brk) - 5.0e-6 * sc - 6.0e-6 * scuff)
    return w


def parkerised(S, sel, hz, octave=0, base="3b3e39", worn="8a9098", edge_gain=1.0, rough=0.62):
    """Manganese phosphate: dark grey-green, rough, a fine crystalline grain in the height, bright steel where touched."""
    if not sel.any():
        return
    for part in pieces(sel):
        S.steel(part, lin(base), rough, hz, lin(worn), worn_rough=0.26, edge_gain=edge_gain * 1.35, rvar=0.08, cvar=0.035,
                octave=octave, base_thr=0.82, rub_polish=0.16, scratch=0.65)
        p = S.p[part]
        S.h[part] += 4.5e-6 * S.N.fbm(p, 7000.0, 2, octave0=430) + 2.0e-6 * S.N.fbm(p, 21000.0, 1, octave0=433)


def dirt_chunked(S, amount, carbon=None, oil=None):
    """Surf2.dirt in pieces: dust and dried oil in the recesses (short-range occlusion), carbon where given; metallic drops
    with a narrow step where the deposit is thick."""
    allsel = np.ones(len(S.p), bool)
    dust = lin("3a362f")
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

RIGHT_PANEL = (0.188, -0.038, 0.134, 0.024)         # x0, z0, width, height of the marking recess (right flank)
LEFT_PANEL = (0.044, -0.034, 0.068, 0.010)          # the serial recess (left flank)


def paint_shorty(G):
    S = TX.Surf2(G, 301)
    release(G)
    p, n, N = S.p, S.n, S.N
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    hz = handling(p, n)
    ol = S.sel(OLIVE)
    pk = S.sel(PARK)
    rb = S.sel(RUBBER)
    br = S.sel(BRIGHT)
    bo = S.sel(BORE)
    tr_ = S.sel(TRIT)
    # ---- olive polymer
    for part in pieces(ol):
        polymer_olive(S, part, hz)
    # grip: stipple on the whole surface, finger grooves darkened by the occlusion
    grip = ol & (z < -0.060) & (x > 0.246) & (x < 0.346) & (np.abs(y) < 0.0185)
    for part in pieces(grip):
        S.stipple(part, 0.00115, 2.4e-4)
    # the forend and the handle's bar carry a finer moulded grip pattern on their flanks
    grippy = ol & (x > 0.396) & (x < 0.592) & (np.abs(n[:, 1]) > 0.8) & (np.abs(y) > 0.0300) & (np.abs(y) < 0.0316) & (z > -0.036) & (z < 0.030)
    for part in pieces(grippy):
        S.stipple(part, 0.0016, 7e-5)
    # parting line: 0.4 mm wide, 0.15 mm deep along the top and the bottom centre of the shells and down the grip's
    # front and back
    seam = ol & (np.abs(y) < 0.0002) & ((np.abs(n[:, 2]) > 0.92) | ((np.abs(n[:, 0]) > 0.92) & (z < -0.06))) & (x > 0.030)
    S.h -= 1.5e-4 * seam
    S.bc *= (1.0 - 0.28 * seam)[:, None]
    S.rough += 0.10 * seam
    # ---- parkerised steel: barrel, hider, trigger, selector, front tower, carrier, rails, screws, pins, deflector hardware
    parkerised(S, pk, hz, octave=3, edge_gain=1.45)
    # bolt: the carrier is steel too; the bolt head, extractor and the firing-pin hole are bright
    for part in pieces(br):
        S.steel(part, lin("b1b6bd"), 0.25, hz, lin("d4d8dc"), worn_rough=0.2, rvar=0.03, cvar=0.03, octave=9, base_thr=1.2,
                rub_polish=0.10)
        q = S.p[part]
        S.h[part] += 6e-7 * N.fbm(q, (300.0, 16000.0, 16000.0), 2, octave0=330)
    # rubber butt pad: black, rough, a 1.8 mm diamond stipple on the rear face
    for part in pieces(rb):
        pp = S.p[part]
        hh = np.clip(hz[part], 0, 1)
        v = N.fbm(pp, 80.0, 2, octave0=440)
        S.bc[part] = lin("161616")[None, :] * (1.0 + 0.10 * v[:, None]) * (1.0 + 0.25 * hh[:, None])
        S.rough[part] = 0.88 - 0.10 * hh + 0.03 * v
        S.metal[part] = 0.0
        S.h[part] += 8e-6 * N.fbm(pp, 5000.0, 2, octave0=442)
    rear = rb & (n[:, 0] < -0.45)
    if rear.any():
        field = np.minimum.reduce([0.0165 - np.abs(y[rear]), z[rear] + 0.0745, 0.0485 - z[rear]])
        S.checker_uv(rear, y[rear], z[rear], 0.0018, 3.8e-4, field, fade_w=0.0004, flat=0.10, top_rough=0.84, val_rough=0.93)
    # interior: dark, dusty, rough
    for part in pieces(bo):
        pp = S.p[part]
        v = N.fbm(pp, 120.0, 2, octave0=450)
        S.bc[part] = lin("0b0b0a")[None, :] * (1.0 + 0.30 * v[:, None]) + lin("07070a")[None, :] * 0.0
        S.rough[part] = 0.66 + 0.10 * v
        S.metal[part] = 0.0
        S.h[part] += 3e-6 * N.fbm(pp, 3000.0, 1, octave0=452)
    # ---- the tritium insert: pale ring, emissive green
    if tr_.any():
        S.bc[tr_] = lin("9db57a")[None, :]
        S.rough[tr_] = 0.30
        S.metal[tr_] = 0.0
        S.emit[tr_] = lin("66ff7a")[None, :] * 0.95
    # ---- charging knob knurl (diamond 1.4 mm), the selector pad's wear, trigger serration
    kn = pk & (y > 0.032) & (np.abs(x - 0.380) < 0.007) & (np.abs(z - 0.012) < 0.007)
    ang = np.arctan2(z - 0.012, x - 0.380)
    knurl = np.sin(ang * 34 + y / 0.0007 * 2 * math.pi) * np.sin(ang * 34 - y / 0.0007 * 2 * math.pi)
    S.h += kn * 2.0e-5 * knurl
    S.bc += (lin("8a9098") - S.bc) * (kn * np.clip(knurl, 0, 1) * 0.25)[:, None]
    trg = pk & (np.abs(x - 0.369) < 0.007) & (z < -0.056) & (z > -0.084) & (n[:, 0] < -0.35)
    S.h += trg * 3e-5 * np.sin(z / 0.0010 * 2 * math.pi)
    # ---- markings
    x0, z0, w, h_ = RIGHT_PANEL
    plate = text_plate(w * 1000, h_ * 1000, [("mono", "CARBINE S-5.6", 36.0, 12.0, 5.4), ("star", "", 85.0, 12.0, 8.0),
                                           ("mono", "S2-0417", 112.0, 12.0, 3.6)])
    lay(S, plate, (0, 2), (x0, z0), (w, h_), "-Y", 1.8e-4)
    xs0, zs0, ws, hs = LEFT_PANEL
    plate_l = text_plate(ws * 1000, hs * 1000, [("mono", "S2-0417", 18.0, 5.0, 4.4), ("star", "", 49.0, 5.0, 6.0)])
    lay(S, plate_l, (0, 2), (xs0, zs0), (ws, hs), "+Y", 1.8e-4, flip=True)
    # the selector legends: white paint, one line per position (the lever tip passes SAFE, SEMI, AUTO at 0 / 14 / 28 deg)
    leg = text_plate(16.0, 22.0, [("mono", "AUTO", 8.0, 17.5, 3.0), ("mono", "SEMI", 8.0, 11.0, 3.0), ("mono", "SAFE", 8.0, 4.5, 3.0)])
    lay(S, leg, (0, 2), (0.2475, -0.0265), (0.016, 0.022), "+Y", 5e-5, colour=lin("cfcdbd"), flip=True)
    # white paint on the lever's tip
    tip = ((x - 0.2735) ** 2 + (z + 0.022) ** 2 < 0.0016 ** 2) & pk & (y > 0.0335)
    S.bc[tip] = lin("d8d6c8")[None, :]
    S.rough[tip] = 0.6
    # ---- sight ears and the post wear bright, the muzzle shows carbon, the bolt face and the port too
    r = np.hypot(y, z)
    carbon = (tp.smooth(x, 0.6985, 0.7002) * (n[:, 0] > 0.6) * 0.55                                  # hider face
              + (x > 0.693) * pk * tp.smooth(0.0035 - np.abs(r - 0.0028), 0.0, 0.0012) * 0.9          # the bore's lip
              + gauss(p, (0.378, -0.015, 0.012), 0.020, 0.55) * (y < -0.010)                          # round the port
              + (x > 0.394) * (x < 0.397) * (n[:, 0] > 0.6) * (r < 0.0125) * 0.5                       # bolt face and chamber
              + (x > 0.660) * (x < 0.698) * pk * (np.abs(n[:, 0]) < 0.4) * 0.35 * (np.arctan2(z, y) % (math.pi / 3) < 0.4)
              + gauss(p, (0.426, -0.020, 0.018), 0.030, 0.35) * ol * (y < -0.028))                     # soot on the deflector
    oil = (gauss(p, (0.372, -0.012, 0.010), 0.040, 0.9) * (y < -0.004) + gauss(p, (0.345, 0.0, 0.012), 0.060, 0.6) * br
           + gauss(p, (0.500, 0.0, 0.0), 0.080, 0.35) * pk + 0.45 * hz * ol)
    dirt_chunked(S, 1.3, carbon=np.clip(carbon, 0, 1), oil=np.clip(oil, 0, 1))
    S.rough = np.maximum(S.rough, 0.16 * (S.metal > 0.5))
    ch = S.channels(height_blur=0.35)
    return ch


# ----------------------------------------------------------------------------------------------- the magazine

def paint_shorty_mag(G):
    """SHORTY magazine: parkerised stamped steel with bright insertion scuffs and pouch scratches, an olive polymer floor
    plate with its drag tab and follower, dark feed lips, the rounds. Spine weld bead on the rear face."""
    S = TX.Surf2(G, 17)
    release(G)
    p, n, N = S.p, S.n, S.N
    top = tp.smooth(p[:, 2], -0.060, -0.026)
    floor = tp.smooth(-p[:, 2], 0.165, 0.178)
    hz = np.clip(top * 0.85 + floor * 0.75 + gauss(p, (0.206, 0.0, -0.150), 0.040, 0.45), 0, 1)
    body = S.sel(W.BLUED)
    parkerised(S, body, hz, octave=11, base="4a4d46", rough=0.52, edge_gain=1.3)
    if body.any():
        q = p[body]
        sc = tp.smooth(N.ridged(np.stack([q[:, 0] * 400.0, q[:, 1] * 30.0, q[:, 2] * 2500.0], 1), 1.0, 2, octave0=160), 0.95, 0.995)
        sc = sc * top[body] * (np.abs(n[body, 1]) > 0.6)
        pouch = S.scratches(0.9, along="Z", sel=body, freq_across=9000.0, freq_long=40.0, octave=170) * tp.smooth(-q[:, 2], 0.10, 0.16) \
            * (np.abs(n[body, 1]) > 0.6)
        S.bc[body] += (lin("9aa0a8") - S.bc[body]) * (0.6 * sc + 0.45 * pouch)[:, None]
        S.rough[body] -= 0.10 * sc + 0.06 * pouch
        S.h[body] -= 2e-6 * pouch
        for zr in (-0.070, -0.108, -0.146):                                   # stamped ribs read as slightly worn on top
            rr = tp.smooth(0.0022 - np.abs(q[:, 2] - zr), 0.0, 0.0008) * (np.abs(q[:, 1]) > 0.0120)
            S.bc[body] += (lin("8a9098") - S.bc[body]) * (0.28 * rr * tp.smooth(N.fbm(q, 90.0, 2, octave0=172), -0.2, 0.5))[:, None]
        spine = (np.abs(q[:, 1]) < 0.0011) & (q[:, 0] < 0.1835) & (n[body, 0] < -0.5)                  # weld bead down the rear
        S.h[body] += 7e-5 * spine * (0.5 + 0.5 * np.sin(q[:, 2] / 0.0011 * 2 * math.pi))
        S.bc[body] += (lin("56524a") - S.bc[body]) * (0.5 * spine)[:, None]
    for sel_, base_ in ((S.sel(OLIVE), "4b5232"),):
        for part in pieces(sel_):
            polymer_olive(S, part, hz)
    parkerised(S, S.sel(PARK), hz, octave=5)
    S.plain(S.sel(BORE), lin("050506"), 0.7, 0.0)
    S.steel(S.sel(W.BRASS), lin("caa23d"), 0.27, hz * 0, lin("e2c46a"), worn_rough=0.2, cvar=0.03, octave=6)
    S.steel(S.sel(W.COPPER), lin("b5683a"), 0.29, hz * 0, lin("d08a5a"), worn_rough=0.2, cvar=0.03, octave=8)
    S.steel(S.sel(W.PRIMER), lin("caa23d") * np.array([0.95, 0.9, 0.85], np.float32), 0.32, hz * 0, lin("caa23d"), octave=10)
    # a stamped capacity numeral on the right face and an invented mark on the rear
    plate = text_plate(30.0, 16.0, [("sans", "30", 15.0, 8.0, 7.0)])
    lay(S, plate, (0, 2), (0.2000, -0.0870), (0.030, 0.016), "-Y", 1.2e-4)
    dirt_chunked(S, 0.9)
    return S.channels(height_blur=0.4)


# ----------------------------------------------------------------------------------------------- tiling detail

def detail_polymer(res=1024, tile=DETAIL_POLY_TILE_M, seed=23):
    """Tiling polymer grain for the olive parts (the 4K set stops at ~0.14 mm per texel): periodic band-passed noise at
    0.1 mm and 0.4 mm as a tangent-space normal, and a roughness offset in ORM.G (0.5 = no change; use rough + (G - 0.5)).
    Tile 12 mm. Metallic is 0 (the master material blends this tile with TS_GunDetail_Steel by the gun's metallic)."""
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
    f1, f2 = tile / 0.0004, tile / 0.0001                     # 0.4 mm and 0.1 mm features per tile
    h = 3.0e-6 * band(f1, f1 * 0.35) + 1.6e-6 * band(min(f2, res / 3.0), min(f2, res / 3.0) * 0.30)
    px = tile / res
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px)
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * px)
    nn = np.stack([-dx, -dy, np.ones_like(h)], -1)
    nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
    rough = np.clip(0.5 + 0.06 * band(f1 / 2, f1 / 5) + 0.03 * band(f1, f1 / 4), 0, 1)
    ch = {"bc": np.full((res, res, 3), 0.5, np.float32), "rough": rough.astype(np.float32),
          "metal": np.zeros((res, res), np.float32), "ao": np.ones((res, res), np.float32),
          "normal": (nn * 0.5 + 0.5).astype(np.float32)}
    return _bake.write_set(DETAIL_POLY, ch, meta={
        "kind": "tiling", "tile_m": tile, "authoring": "assets/_weapons_shorty_tex.py detail_polymer (periodic band-passed noise)",
        "use": "detail normal (blend over the unique N) and roughness offset (ORM.G - 0.5) on the olive polymer of SK_Shorty "
               "(where its ORM.B is 0); TS_GunDetail_Steel on the steel (where ORM.B is 1)"})
