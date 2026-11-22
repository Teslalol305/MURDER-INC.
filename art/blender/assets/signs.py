"""Signage: the ten storefront signs as built objects, their printed and painted faces, and the IPX pieces
(billboard face, bus-shelter one-sheet, the mural on the pawn shop's side wall).

Sources: docs/unreal/spec/06-look-fx.md 2.3 (IPX mark), 2.8 (sign styles), 2.9 (every sign, verbatim text), 2.12
(mural, billboard face), 2.13 (ipx_ad one-sheet); docs/unreal/ART_BIBLE.md 5 (sign types as built objects, IPX, type,
hygiene); briefs sign_* in docs/unreal/spec/assets/signs-fx.json (names SM_Sign_<Brief>, sizes, letter heights).

Construction (ART_BIBLE 5.2 / 5.3):
    lightbox        Laundromat, Deli, Pizza, Chicken (raised face): extruded cabinet 200 mm deep, retainer frame
                    4.5 % of the height, printed flex face (slot M_Sign_<Shop>, BC + E), hinge, latches, whip
    neon on a pan   Barber, Pawn: 13 mm glass tube along the letter outlines, 35 mm glass standoffs, electrode
                    boots, a border tube, transformer box, on a painted steel pan (M_Sign_<Shop>)
    neon on wood    Records: the same tubes over a hand-painted plywood fascia with a moulding (M_Sign_Records)
    LED flex        Nails: pink flex along the outlines on a black backer, clear acrylic cover, aluminium edge
    pan letters     ChecksCashed, Liquor: open-face channel letters 110 mm deep (returns, lip, floor) with the tube
                    inside on standoffs, on a raceway; the band face behind (M_Sign_<Shop>) carries the sub line
                    in white cut vinyl (Checks) and the ghost and drill holes of an older sign

Mesh frame (brief): pivot at the bottom-left corner of the face, running +X, face toward -Y, the body behind it
(+Y). Mounting on SM_Facade_SignBand_<Shop>: band-local (x0, -0.150 - depth, z0) with x0 = (W - w) / 2,
z0 = (0.74 - h) / 2 (`mount`), i.e. the back of the sign on the band's sign plate.

Faces are drawn here with PIL into art/out/textures/Sign_<Key>/T_Sign_<Key>_BC.png (+ _ORM, + _E for lit faces),
the material is mat.sign_face(key). Fonts (all free licences, installed on the build machine):
    heavy grotesque   Inter Display Black (OFL), headlines; set at 70 .. 82 % width it is the condensed face
                      (no true condensed face is installed: Anton, Oswald, League Gothic are not on the machine)
    bold grotesque    Inter Bold / Medium (sub lines, Archivo 700 stand-in), DejaVu Sans Bold and FreeSans Bold
                      for the shops lettered by other sign shops
    IPX mark          Inter ExtraBold Italic in the stadium lozenge (spec 2.3), one master image (ipx_master)
"""
import json
import math
import os

import bpy
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from assets import facade
from mi import geo, mat, paths, render, scene, steel

FAMILY = {"name": "signs",
          "description": "Storefront signs as built objects (lightbox, neon, LED flex, pan letters), their faces, IPX billboard, one-sheet and mural"}

X, Y, Z = np.eye(3)
FD = "/usr/share/fonts"
FONTS = {
    "heavy": FD + "/opentype/inter/InterDisplay-Black.otf",
    "heavyIt": FD + "/opentype/inter/InterDisplay-BlackItalic.otf",
    "xbIt": FD + "/opentype/inter/Inter-ExtraBoldItalic.otf",
    "bold": FD + "/opentype/inter/Inter-Bold.otf",
    "semi": FD + "/opentype/inter/Inter-SemiBold.otf",
    "medium": FD + "/opentype/inter/Inter-Medium.otf",
    "dejavu": FD + "/truetype/dejavu/DejaVuSans-Bold.ttf",
    "free": FD + "/truetype/freefont/FreeSansBold.ttf",
}
PAN_Y = 0.150                         # the band's sign plate is 0.150 in front of the wall

# key = facade shop / slot key; brief mesh name; type; w, h; headline (cap m, centre from top as a fraction);
# sub line; colours (field, type, sub); font, width factor; phone number (fictional, 555-01xx)
SIGNS = {
    "Laundromat": dict(mesh="SM_Sign_Laundromat", kind="lightbox", w=7.50, h=0.62, text="24 HR LAUNDROMAT", cap=0.335, cy=0.50,
                       field="#0d3550", ink="#f4f2ec", font="dejavu", cond=0.80, phone="(718) 555-0142", age=1.0, glow="#cfe4ff"),
    "Barber": dict(mesh="SM_Sign_CrownFadeBarber", kind="neon", w=7.06, h=0.62, text="CROWN & FADE BARBER", cap=0.285, cy=0.50,
                   tube="#ff3030", font="heavy", cond=0.74, age=1.2),
    "Deli": dict(mesh="SM_Sign_HollisDeli", kind="lightbox", w=8.40, h=0.74, text="HOLLIS DELI & GROCERY", cap=0.296, cy=0.40,
                 sub="OPEN 24 HRS  ·  COLD CUTS  ·  COFFEE  ·  LOTTO", subcap=0.104, subcy=0.78,
                 field="#f2c21a", ink="#8a1410", font="heavy", cond=0.70, phone="(718) 555-0119", age=1.35, glow="#ffd24a"),
    "ChecksCashed": dict(mesh="SM_Sign_ChecksCashed", kind="letters", w=6.56, h=0.74, text="CHECKS CASHED", cap=0.266, cy=0.40,
                         sub="MONEY ORDERS  ·  BILLS PAID", subcap=0.096, subcy=0.76, tube="#55ff8a", font="heavy", cond=0.86,
                         phone="(718) 555-0181", age=1.0),
    "Pizza": dict(mesh="SM_Sign_99cPizza", kind="lightbox", w=7.16, h=0.74, text="99¢ PIZZA", cap=0.296, cy=0.40,
                  sub="SLICES ALL NIGHT", subcap=0.104, subcy=0.78, field="#b3261e", ink="#fff1d0", font="free", cond=0.82,
                  phone="(718) 555-0199", age=0.85, glow="#ff5a3a", dim=(2.3, 4.6)),
    "Pawn": dict(mesh="SM_Sign_PawnGold", kind="neon", w=4.86, h=0.74, text="PAWN & GOLD", cap=0.266, cy=0.40,
                 sub="WE BUY GOLD  ·  LOANS", subcap=0.096, subcy=0.76, tube="#f6c21a", font="heavy", cond=0.80, age=1.1),
    "Records": dict(mesh="SM_Sign_TapesRecords", kind="wood", w=4.66, h=0.62, text="TAPES · RECORDS · CDs", cap=0.285, cy=0.50,
                    tube="#35e0ff", font="heavy", cond=0.72, board="#1d2b45", stripe="#e2d6b4", phone="(718) 555-0167", age=1.3),
    "Chicken": dict(mesh="SM_Sign_GoldenBird", kind="lightbox", w=7.50, h=0.74, text="GOLDEN BIRD CHICKEN", cap=0.296, cy=0.40,
                    sub="FRIED  ·  WINGS  ·  BISCUITS", subcap=0.104, subcy=0.78, field="#f2c21a", ink="#b3261e",
                    font="heavy", cond=0.76, phone="(718) 555-0177", age=0.9, glow="#ffc84a", raised=0.035),
    "Liquor": dict(mesh="SM_Sign_WinesLiquors", kind="letters", w=7.36, h=0.62, text="WINES & LIQUORS", cap=0.285, cy=0.50,
                   tube="#ff3030", font="heavy", cond=0.90, age=1.25),
    "Nails": dict(mesh="SM_Sign_LuckyNails", kind="flex", w=7.36, h=0.74, text="LUCKY NAILS", cap=0.266, cy=0.40,
                  sub="MANICURE  ·  PEDICURE", subcap=0.096, subcy=0.76, tube="#ff3d9a", font="heavy", cond=0.84, age=0.8),
}
DEPTH = {"lightbox": 0.20, "neon": 0.07, "wood": 0.06, "flex": 0.05, "letters": 0.20}

SLOT_META = dict(facade.SLOT_META)
for _c, _h in (("Red", "#ff3030"), ("Green", "#55ff8a"), ("Gold", "#f6c21a"), ("Cyan", "#35e0ff"), ("Pink", "#ff3d9a")):
    SLOT_META["MI_Neon_" + _c] = {"workflow": "emissive", "emissive": _h,
                                  "note": "glass tube: base colour = tube colour greyed 55 % toward #9a9aa2 (milky by day); emissive in the "
                                          "tube colour, 400 .. 2,000 nits at night, x 0.55 by day (spec 2.8); flicker group per sign"}
SLOT_META["MI_Glass_Standoff"] = {"workflow": "flat", "note": "clear glass standoffs and tube supports"}
SLOT_META["MI_Glass_Acrylic"] = {"workflow": "glass", "note": "clear acrylic cover of the LED flex box"}
SLOT_META["MI_Rubber_Aged"] = {"set": "TS_Rubber_Aged", "workflow": "tiling", "note": "electrode boots, cable, flexible conduit"}
for _k, _s in SIGNS.items():
    SLOT_META["M_Sign_" + _k] = {"workflow": "sign", "uv": "0..1 over the %.2f x %.2f m face" % (_s["w"], _s["h"]),
                                 "note": "T_Sign_%s_BC/_ORM%s; shared with SM_Facade_SignBand_%s" % (_k, "/_E (lit face)" if _s["kind"] == "lightbox" else "", _k)}
SLOT_META["M_Sign_Mural"] = {"workflow": "decal", "uv": "0..1 over 12 x 7.6 m",
                             "note": "BC with opacity in alpha (holes show the wall's brick); a DBuffer decal keeping the wall's normal at ~70 % "
                                     "and its roughness (spec 4.4, ART_BIBLE 5.5)"}


# ================================================================================================= colour helpers

def rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def lum(c):
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


L_MIN, L_MAX = float(lum(to_lin(rgb("#2a2a2c")))), float(lum(to_lin(rgb("#e6e4dc"))))


def paint(h):
    """A screen colour as paint or print (ART_BIBLE 5.4 / 3.1): luminance kept between #2A2A2C and #E6E4DC, hue kept."""
    c = to_lin(rgb(h) if isinstance(h, str) else h)
    L = float(lum(c))
    if L < L_MIN:
        c = c * (L_MIN / max(L, 1e-5))
    elif L > L_MAX:
        c = c * (L_MAX / L)
    return to_srgb(np.clip(c, 0, 1))


def sstep(a, b, x):
    t = np.clip((np.asarray(x, np.float32) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def vnoise(rng, h, w, cell, octaves=3):
    """Smooth value noise 0..1 of shape (h, w); cell = feature size in pixels."""
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for _ in range(octaves):
        gh, gw = max(2, int(h / cell) + 2), max(2, int(w / cell) + 2)
        a = (rng.random((gh, gw)) * 255).astype(np.uint8)
        out += amp * np.asarray(Image.fromarray(a).resize((w, h), Image.BICUBIC), np.float32) / 255.0
        tot += amp
        amp *= 0.5
        cell = max(1.0, cell / 2.0)
    out /= tot
    lo, hi = np.percentile(out, 1), np.percentile(out, 99)
    return np.clip((out - lo) / max(hi - lo, 1e-5), 0, 1)


# ================================================================================================= type

_FC = {}


def font(key, px):
    k = (key, int(round(px)))
    if k not in _FC:
        _FC[k] = ImageFont.truetype(FONTS[key], max(4, int(round(px))))
    return _FC[k]


def cap_ratio(key):
    f = font(key, 1000)
    bb = f.getbbox("H")
    return (bb[3] - bb[1]) / 1000.0


def text_mask(text, key, cap_px=None, cond=1.0, track_em=0.0, size_px=None):
    """Antialiased mask (float32 0..1) of one line. Returns (mask, (x_ink0, x_ink1), cap top row, baseline row)."""
    size = size_px if size_px is not None else cap_px / cap_ratio(key)
    f = font(key, size)
    asc, desc = f.getmetrics()
    pad = int(size * 0.4) + 4
    tr = track_em * size
    if tr:
        adv = [f.getlength(ch) for ch in text]
        wid = sum(adv) + tr * (len(text) - 1)
    else:
        wid = f.getlength(text)
    im = Image.new("L", (int(wid) + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(im)
    if tr:
        x = pad
        for ch, a in zip(text, adv):
            d.text((x, pad), ch, font=f, fill=255)
            x += a + tr
    else:
        d.text((pad, pad), text, font=f, fill=255)
    hb = f.getbbox("H")
    top, base = pad + hb[1], pad + hb[3]
    if cond != 1.0:
        im = im.resize((max(1, int(im.width * cond)), im.height), Image.LANCZOS)
    m = np.asarray(im, np.float32) / 255.0
    cols = np.where(m.max(axis=0) > 0.02)[0]
    return m, (int(cols[0]), int(cols[-1]) + 1), top, base


class Canvas:
    """A face drawn in metres: k px per metre, (x, y) from the top-left corner. c: sRGB colour (H, W, 3)."""

    def __init__(self, w_m, h_m, k, bg):
        self.k, self.wm, self.hm = k, w_m, h_m
        self.W, self.H = int(round(w_m * k)), int(round(h_m * k))
        self.c = np.ones((self.H, self.W, 3), np.float32) * np.asarray(bg, np.float32)
        self.a = np.ones((self.H, self.W), np.float32)
        yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        self.x, self.y = (xx + 0.5) / k, (yy + 0.5) / k                # metres

    def blank(self):
        return np.zeros((self.H, self.W), np.float32)

    def put(self, mask, col, op=1.0):
        a = np.clip(mask * op, 0, 1)[..., None]
        self.c = self.c * (1 - a) + np.asarray(col, np.float32) * a

    def draw(self, fn, width=None):
        """Mask from an ImageDraw callback fn(draw, k) at 4x supersampling."""
        s = 4 if self.W * self.H < 4e6 else 2
        im = Image.new("L", (self.W * s, self.H * s), 0)
        fn(ImageDraw.Draw(im), self.k * s)
        return np.asarray(im.resize((self.W, self.H), Image.BOX), np.float32) / 255.0

    def rect(self, x0, y0, x1, y1, r=0.0, outline=None):
        def f(d, k):
            box = [x0 * k, y0 * k, x1 * k, y1 * k]
            if outline:
                d.rounded_rectangle(box, radius=r * k, outline=255, width=max(1, int(outline * k)))
            else:
                d.rounded_rectangle(box, radius=r * k, fill=255)
        return self.draw(f)

    def text(self, text, key, cap, cx, cy, cond=1.0, track=0.0, max_w=None, align="c", size=None):
        """Mask of a line whose cap height is `cap` metres (or font size `size` m), its caps centred at (cx, cy);
        scaled down as a whole when wider than max_w. align 'c', 'l' (cx = left end) or 'r' (cx = right end)."""
        k = self.k
        if size is not None:
            m, (i0, i1), top, base = text_mask(text, key, cond=cond, track_em=track, size_px=size * k)
        else:
            m, (i0, i1), top, base = text_mask(text, key, cap * k, cond, track)
        wpx = i1 - i0
        sc = 1.0
        if max_w and wpx > max_w * k:
            sc = max_w * k / wpx
            im = Image.fromarray((m * 255).astype(np.uint8))
            im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
            m = np.asarray(im, np.float32) / 255.0
            i0, i1, top, base = int(i0 * sc), int(i1 * sc), top * sc, base * sc
            wpx = i1 - i0
        ox = {"c": cx * k - wpx / 2, "l": cx * k, "r": cx * k - wpx}[align] - i0
        oy = cy * k - (top + base) / 2
        out = self.blank()
        ox, oy = int(round(ox)), int(round(oy))
        ys0, xs0 = max(0, -oy), max(0, -ox)
        ys1, xs1 = min(m.shape[0], self.H - oy), min(m.shape[1], self.W - ox)
        if ys1 > ys0 and xs1 > xs0:
            out[oy + ys0:oy + ys1, ox + xs0:ox + xs1] = m[ys0:ys1, xs0:xs1]
        return out, (i1 - i0) / k, sc

    def save(self, path, size, alpha=False):
        arr = np.clip(self.c, 0, 1)
        if alpha:
            arr = np.concatenate([arr, np.clip(self.a, 0, 1)[..., None]], -1)
        im = Image.fromarray((arr * 255 + 0.5).astype(np.uint8), "RGBA" if alpha else "RGB")
        if size and im.size != tuple(size):
            im = im.resize(size, Image.LANCZOS)
        im.save(path, optimize=True)
        return path


# ================================================================================================= weathering

def weather_face(cv, rng, age=1.0, top_fade=0.22, grime=0.25, bugs=0, crack=False, field_mask=None):
    """Sun fade (stronger toward the top), yellowed whites, dust, grime along the bottom, insects, a corner crack.
    Returns a roughness offset map."""
    H, W = cv.H, cv.W
    n1 = vnoise(rng, H, W, cv.k * 0.9)
    n2 = vnoise(rng, H, W, cv.k * 0.12)
    c = cv.c
    L = lum(c)[..., None]
    faded = c + (1 - c) * 0.16
    faded = faded * 0.7 + np.mean(faded, -1, keepdims=True) * 0.3
    f = age * (0.06 + top_fade * (1 - cv.y / cv.hm) ** 1.4 * (0.6 + 0.6 * n1))[..., None]
    c = c * (1 - f) + faded * f
    yel = np.clip((L - 0.62) / 0.3, 0, 1) * 0.6 * age
    c = c * (1 - yel * np.array([0.0, 0.025, 0.10], np.float32))
    c = c * (0.94 + 0.06 * n2[..., None])
    gb = grime * age * sstep(0.10, 0.0, cv.hm - cv.y) * (0.5 + 0.7 * n1)
    c = c * (1 - 0.55 * gb[..., None]) + np.array([0.16, 0.13, 0.10], np.float32) * 0.55 * gb[..., None]
    rough = 0.10 * n2 + 0.35 * gb
    cv.c = c
    if bugs:
        def f_(d, k):
            for _ in range(bugs):
                x = rng.uniform(0.05, cv.wm - 0.05)
                y = cv.hm - abs(rng.normal(0, 0.035)) - 0.03
                r = rng.uniform(0.0015, 0.004)
                d.ellipse([(x - r) * k, (y - r * 0.7) * k, (x + r) * k, (y + r * 0.7) * k], fill=int(rng.uniform(120, 255)))
        bm = cv.draw(f_)
        cv.put(bm, (0.06, 0.045, 0.03), 0.85)
        rough = rough + 0.4 * bm
    if crack:
        def g(d, k):
            for cx, cy, dx, dy in ((cv.wm - 0.06, 0.06, -1, 1), (0.05, cv.hm - 0.05, 1, -1)):
                x, y = cx, cy
                pts = [(x * k, y * k)]
                for _ in range(rng.integers(8, 16)):
                    x += dx * rng.uniform(0.005, 0.03)
                    y += dy * rng.uniform(-0.004, 0.02)
                    pts.append((x * k, y * k))
                d.line(pts, fill=255, width=max(1, int(0.0015 * k)))
        cm_ = cv.draw(g)
        cv.put(cm_, (0.08, 0.07, 0.06), 0.7)
    return rough


def screws(cv, pts, r=0.005, rust=0.6, rng=None):
    """Fixing screws with a rust halo and a short run."""
    def f(d, k):
        for x, y in pts:
            d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=255)
    m = cv.draw(f)
    halo = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(cv.k * r * 1.2)), np.float32) / 255
    run = np.zeros_like(m)
    step = max(1, int(cv.k * 0.004))
    for i in range(1, int(cv.k * 0.12 / step)):
        run[i * step:, :] = np.maximum(run[i * step:, :], halo[:-i * step, :] * (1 - i * step / (cv.k * 0.12)) * 0.6)
    cv.put(np.clip(halo * 1.8, 0, 1) * rust + run * rust * 0.5, (0.30, 0.13, 0.05), 0.7)
    cv.put(m, (0.12, 0.11, 0.10), 1.0)
    return m


# ================================================================================================= the IPX mark

def ipx_master(h_px=512, col=(1.0, 1.0, 1.0)):
    """THE IPX mark (spec 2.3), white on transparent: 'IPX' Inter ExtraBold Italic at 0.58 h, tracking 0.05 em, centred
    0.02 h left in a stadium outline of outer height h, stroke 0.065 h, width text + 0.86 h. Every IPX mark of the world
    is pasted from this image; when IPX supplies its logo, change this function (or the PNG it writes) only."""
    s = 4
    h = h_px * s
    m, (i0, i1), top, base = text_mask("IPX", "xbIt", size_px=0.58 * h, track_em=0.05)
    tw = i1 - i0
    W = int(tw + 0.86 * h) + 4
    im = Image.new("L", (W, h + 4), 0)
    d = ImageDraw.Draw(im)
    st = max(1, int(round(0.065 * h)))
    d.rounded_rectangle([2, 2, W - 2, h + 2], radius=h / 2, outline=255, width=st)
    tm = Image.fromarray((m * 255).astype(np.uint8))
    ox = int(W / 2 - tw / 2 - i0 - 0.02 * h)
    oy = int((h + 4) / 2 - (top + base) / 2)
    im.paste(255, (ox, oy), tm)
    im = im.resize((max(1, W // s), (h + 4) // s), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255.0
    rgba = np.zeros(a.shape + (4,), np.float32)
    rgba[..., :3] = col
    rgba[..., 3] = a
    return rgba


def put_ipx(cv, cx, cy, h, col):
    """Paste the master mark, height h metres, centred at (cx, cy). Returns its width in metres."""
    hp = max(8, int(round(h * cv.k)))
    m = ipx_master(hp)[..., 3]
    out = cv.blank()
    oy, ox = int(round(cy * cv.k - m.shape[0] / 2)), int(round(cx * cv.k - m.shape[1] / 2))
    ys0, xs0 = max(0, -oy), max(0, -ox)
    ys1, xs1 = min(m.shape[0], cv.H - oy), min(m.shape[1], cv.W - ox)
    out[oy + ys0:oy + ys1, ox + xs0:ox + xs1] = m[ys0:ys1, xs0:xs1]
    cv.put(out, col)
    return m.shape[1] / cv.k, out


# ================================================================================================= faces

def set_dir(key):
    return paths.ensure(paths.texture_set("Sign_" + key))


def write_set(key, cv, size, rough, emis=None, meta=None, alpha=False, orm_size=None, metal=None):
    d = set_dir(key)
    cv.save(os.path.join(d, "T_Sign_%s_BC.png" % key), size, alpha=alpha)
    orm = np.stack([np.ones_like(rough), np.clip(rough, 0.02, 1), np.zeros_like(rough) if metal is None else metal], -1)
    im = Image.fromarray((orm * 255).astype(np.uint8), "RGB")
    osz = orm_size or (max(64, size[0] // 4), max(32, size[1] // 4))
    im.resize(osz, Image.BILINEAR).save(os.path.join(d, "T_Sign_%s_ORM.png" % key))
    files = {"BC": "T_Sign_%s_BC.png" % key, "ORM": "T_Sign_%s_ORM.png" % key}
    ep = os.path.join(d, "T_Sign_%s_E.png" % key)
    if emis is not None:
        Image.fromarray((np.clip(to_srgb(emis), 0, 1) * 255).astype(np.uint8), "RGB").resize(size, Image.LANCZOS).save(ep, optimize=True)
        files["E"] = "T_Sign_%s_E.png" % key
    elif os.path.exists(ep):
        os.remove(ep)
    info = dict(kind="sign", resolution=list(size), files=files, convention={"BC": "sRGB", "ORM": "linear AO, roughness, metallic",
                                                                             "E": "sRGB, night value at strength 1"})
    info.update(meta or {})
    lin = to_lin(np.clip(cv.c, 0, 1))
    info["albedo_mean"] = [round(float(v), 4) for v in lin.reshape(-1, 3).mean(0)]
    info["roughness_mean"] = round(float(np.mean(np.clip(rough, 0.02, 1))), 3)
    info["metallic_mean"] = 0.0
    if alpha:
        info["alpha"] = "BC alpha = paint coverage (opacity)"
    with open(os.path.join(d, "set.json"), "w") as f:
        json.dump(info, f, indent=1, sort_keys=True)
    return d


def face_lightbox(key, S, rng):
    w, h = S["w"], S["h"]
    k = 512 / h
    field, ink = paint(S["field"]), paint(S["ink"])
    cv = Canvas(w, h, k, field)
    fw = 0.045 * h
    # panel seams of the flex face every 1.22 m
    seams = cv.blank()
    for xs in np.arange(1.22, w - 0.1, 1.22):
        seams = np.maximum(seams, sstep(0.004, 0.0, np.abs(cv.x - xs)))
    cv.put(seams, field * 0.62, 0.5)
    ki = fw + 0.024
    key_m = cv.rect(ki, ki, w - ki, h - ki, r=0.018, outline=0.009)
    cv.put(key_m, ink)
    inner = w - 2 * (ki + 0.07)
    hl, hw, _ = cv.text(S["text"], S["font"], S["cap"], w / 2, S["cy"] * h, S["cond"], 0.02, max_w=inner)
    sh = np.roll(np.roll(hl, int(0.006 * k), 0), int(0.004 * k), 1)          # printed drop shadow
    cv.put(sh, field * 0.55, 0.45)
    cv.put(hl, ink)
    letters = hl.copy()
    if S.get("sub"):
        sl, sw_, _ = cv.text(S["sub"], "bold", S["subcap"], w / 2, S["subcy"] * h, 0.92, 0.06, max_w=inner)
        cv.put(sl, ink)                                       # headline colour (the web's pale sub line cannot be read)
        letters = np.maximum(letters, sl)
    # stars each side of the headline and the shop's phone number at the right end, where there is room
    free = (w - hw) / 2 - ki - 0.12
    if free > 0.5:
        ph, pw, _ = cv.text(S["phone"], "bold", 0.055, w - ki - 0.10, S["cy"] * h, 0.9, 0.04, align="r")
        cv.put(ph, ink)
        for xs in (w / 2 - hw / 2 - 0.22, w / 2 + hw / 2 + 0.22):
            st = star_mask(cv, xs, S["cy"] * h, S["cap"] * 0.42)
            cv.put(st, ink)
            letters = np.maximum(letters, st)
    else:
        ph, pw, _ = cv.text(S["phone"], "bold", 0.026, w - ki - 0.05, h - ki - 0.028, 0.9, 0.04, align="r")
        cv.put(ph, ink)
    clean = cv.c.copy()
    rough = 0.28 + weather_face(cv, rng, S["age"], bugs=int(260 * S["age"]), crack=S["age"] > 1.0)
    # retainer frame (also geometry): dark anodised, with screws
    frame = ((cv.x < fw) | (cv.x > w - fw) | (cv.y < fw) | (cv.y > h - fw)).astype(np.float32)
    cv.put(frame, paint("#1b1c20"))
    pts = [(x, h - fw / 2) for x in np.arange(0.3, w - 0.2, 0.6)] + [(x, fw / 2) for x in np.arange(0.3, w - 0.2, 0.6)]
    screws(cv, pts, 0.004, 0.5 * S["age"], rng)
    rough = np.where(frame > 0.5, 0.55, rough)
    # emissive: the clean print lit from behind; two tube bands at 28 % and 72 %, 62 % at the edges, 70 % at the ends
    v = cv.y / h
    prof = 0.62 + 0.38 * np.maximum(np.exp(-((v - 0.28) / 0.17) ** 2), np.exp(-((v - 0.72) / 0.17) ** 2))
    prof = prof * (0.70 + 0.30 * sstep(0.0, 0.55, np.minimum(cv.x, w - cv.x)))
    if S.get("dim"):
        a, b_ = S["dim"]
        prof = prof * (1 - 0.45 * sstep(a - 0.3, a, cv.x) * sstep(b_ + 0.3, b_, cv.x) * np.exp(-((v - 0.72) / 0.2) ** 2))
    dirt = np.clip(lum(cv.c) / np.maximum(lum(clean), 1e-3), 0, 1.2)
    E = to_lin(clean) * (prof * dirt * (1 - frame))[..., None]
    E = E * (0.35 + 0.65 * np.clip(letters[..., None] + lum(clean)[..., None], 0, 1))
    meta = dict(face_m=[w, h], emissive_day=0.3, fonts=[os.path.basename(FONTS[S["font"]]) + " at %d %% width" % round(S["cond"] * 100),
                                                         os.path.basename(FONTS["bold"])],
                note="lightbox flex face: field %s, type %s; E = the face lit from behind (night), x 0.3 by day" % (S["field"], S["ink"]))
    return write_set(key, cv, (4096, 512), rough, E, meta)


def star_mask(cv, cx, cy, r):
    def f(d, k):
        pts = []
        for i in range(10):
            a = math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.42
            pts.append(((cx + rr * math.cos(a)) * k, (cy - rr * math.sin(a)) * k))
        d.polygon(pts, fill=255)
    return cv.draw(f)


def face_pan(key, S, rng, kind):
    """Painted steel pan (neon), black backer (flex) or the band plate behind pan letters."""
    w, h = S["w"], S["h"]
    k = 512 / h
    base = paint("#2c2c2f") if kind != "flex" else paint("#221a20")
    cv = Canvas(w, h, k, base)
    n1, n2 = vnoise(rng, cv.H, cv.W, k * 0.7), vnoise(rng, cv.H, cv.W, k * 0.05)
    cv.c = cv.c * (0.86 + 0.22 * n1[..., None]) * (0.95 + 0.08 * n2[..., None])
    if kind == "flex":
        kl = cv.rect(0.06 * h, 0.06 * h, w - 0.06 * h, h - 0.06 * h, r=0.03, outline=0.006)
        cv.put(kl, paint(S["tube"]) * 0.85)
    if kind == "letters":
        # the older sign: a less faded rectangle where its cabinet hung, its fixing holes, adhesive ghost of its letters
        x0, x1, y0, y1 = 0.25, w - 0.35, 0.06, h - 0.05
        ghost = cv.rect(x0, y0, x1, y1, r=0.01)
        cv.put(ghost, base * 0.82, 0.55)
        gl, _w, _ = cv.text(S["text"], "dejavu", S["cap"] * 0.92, w / 2 + 0.11, S["cy"] * h + 0.03, 0.78, 0.0, max_w=w - 0.8)
        cv.put(gl, base * 1.25, 0.22)
        holes = [(x, y) for x in (x0 + 0.03, x1 - 0.03, (x0 + x1) / 2) for y in (y0 + 0.03, y1 - 0.03)]
        holes += [(x, y) for x in np.arange(0.6, w - 0.5, 0.9) for y in (S["cy"] * h - 0.05, S["cy"] * h + 0.05)]
        screws(cv, holes, 0.0045, 0.8, rng)
    if S.get("sub") and kind == "letters":
        sl, sw_, _ = cv.text(S["sub"], "bold", S["subcap"], w / 2, S["subcy"] * h, 0.95, 0.06, max_w=w - 0.6)
        cv.put(sl, paint("#e6e4dc"))                                         # white cut vinyl
        lift = np.roll(sl, -int(0.0015 * k), 0) * (cv.x > w / 2 + sw_ * 0.3) * (cv.x < w / 2 + sw_ * 0.38)
        cv.put(np.clip(lift - sl, 0, 1), paint("#ffffff"), 0.8)               # one letter edge lifting
        ph, _pw, _ = cv.text(S["phone"], "bold", 0.042, w - 0.22, S["subcy"] * h, 0.95, 0.04, align="r")
        cv.put(ph, paint("#e6e4dc"))
    edge = 0.02
    pts = [(x, edge) for x in np.arange(0.25, w, 0.75)] + [(x, h - edge) for x in np.arange(0.25, w, 0.75)]
    screws(cv, pts, 0.004, 0.7 * S["age"], rng)
    rough = 0.55 + weather_face(cv, rng, S["age"] * 0.8, top_fade=0.30, grime=0.35, bugs=0, crack=False)
    if kind == "flex":
        rough = rough * 0.5
    meta = dict(face_m=[w, h], note={"neon": "painted steel pan behind the exposed neon (tubes are geometry)",
                                     "flex": "black backer of the LED flex box (the flex is geometry)",
                                     "letters": "band plate behind the open-face pan letters: older sign ghost, drill holes, "
                                                "sub line in white cut vinyl"}[kind])
    return write_set(key, cv, (4096, 512), rough, None, meta)


def face_wood(key, S, rng):
    """Hand-painted plywood fascia: sign-writer's enamel, pinstripe border, sheet joints, flaking to primer."""
    w, h = S["w"], S["h"]
    k = 512 / h
    board = paint(S["board"])
    cv = Canvas(w, h, k, board)
    grain = vnoise(rng, cv.H, cv.W // 8, k * 0.05)
    grain = np.asarray(Image.fromarray((grain * 255).astype(np.uint8)).resize((cv.W, cv.H), Image.BICUBIC), np.float32) / 255
    cv.c = cv.c * (0.90 + 0.16 * grain[..., None])
    for xs in np.arange(2.44, w, 2.44):                                       # sheet joints
        cv.put(sstep(0.003, 0.0, np.abs(cv.x - xs)), board * 0.4, 0.9)
    stripe = paint(S["stripe"])
    wob = vnoise(rng, cv.H, cv.W, k * 0.3)
    i0 = 0.08 * h
    for inset, wd in ((i0, 0.010), (i0 + 0.022, 0.004)):
        m = cv.rect(inset, inset, w - inset, h - inset, r=0.035, outline=wd)
        cv.put(m * (0.75 + 0.35 * wob), stripe)                                # brush-edged line
    for cx_ in (i0 + 0.07, w - i0 - 0.07):
        for cy_ in (i0 + 0.07, h - i0 - 0.07):
            dm = cv.draw(lambda d, kk, cx_=cx_, cy_=cy_: d.polygon([((cx_ - 0.025) * kk, cy_ * kk), (cx_ * kk, (cy_ - 0.025) * kk),
                                                                    ((cx_ + 0.025) * kk, cy_ * kk), (cx_ * kk, (cy_ + 0.025) * kk)], fill=255))
            cv.put(dm, stripe)
    ph, _w, _ = cv.text(S["phone"], "bold", 0.030, w - i0 - 0.14, h - i0 - 0.055, 0.9, 0.06, align="r")
    cv.put(ph * (0.8 + 0.3 * wob), stripe)
    flake = vnoise(rng, cv.H, cv.W, k * 0.08)
    flake = flake * (0.70 + 0.35 * (cv.y / h)) * (0.8 + 0.25 * vnoise(rng, cv.H, cv.W, k * 0.5))
    fm = sstep(0.86, 0.90, flake)
    cv.put(fm, paint("#9a958a"))                                              # primer
    fm2 = sstep(0.93, 0.96, flake)
    cv.put(fm2, paint("#6b5236"))                                             # bare wood
    rough = 0.6 + weather_face(cv, rng, S["age"], top_fade=0.35, grime=0.3) + 0.2 * fm
    meta = dict(face_m=[w, h], note="hand-painted plywood fascia under the cyan neon: enamel %s, pinstripe %s" % (S["board"], S["stripe"]))
    return write_set(key, cv, (4096, 512), rough, None, meta)


def face_billboard(rng):
    w, h = 8.84, 3.94
    k = 2048 / h
    cv = Canvas(w, h, k, paint("#0d0e11"))
    n = vnoise(rng, cv.H, cv.W, k * 0.8)
    cv.c = cv.c * (0.94 + 0.10 * n[..., None])
    ink, gold = paint("#f4f2ec"), paint("#f6c21a")
    mw, _m = put_ipx(cv, w / 2, 0.418 * h, 0.527 * h, ink)
    bar = cv.rect(w / 2 - mw / 2, 0.758 * h - 0.006 * h, w / 2 + mw / 2, 0.758 * h + 0.006 * h)
    cv.put(bar, gold)
    ad, _aw, _ = cv.text("IPX.EXCHANGE", "bold", None, w / 2, 0.859 * h, 1.0, 0.3, size=0.09 * h)
    cv.put(ad, ink)
    # panel seams of the face sheet showing through the vinyl, strap wrinkles at the corners, an older poster edge
    for xs in np.arange(w / 6, w - 0.1, w / 6):
        cv.put(sstep(0.006, 0.0, np.abs(cv.x - xs - 0.004)), np.array([0.0, 0.0, 0.0]), 0.35)
        cv.put(sstep(0.004, 0.0, np.abs(cv.x - xs + 0.004)), np.array([1.0, 1.0, 1.0]), 0.06)
    for cx, cy, sx, sy in ((0, 0, 1, 1), (w, 0, -1, 1), (0, h, 1, -1), (w, h, -1, -1)):
        dx, dy = (cv.x - cx) * sx, (cv.y - cy) * sy
        r = np.sqrt(dx * dx + dy * dy)
        ang = np.arctan2(dy, dx)
        wr = np.sin(ang * 22 + r * 3.0) * sstep(0.9, 0.05, r) * sstep(0.0, 0.08, r)
        cv.put(np.clip(wr, 0, 1), np.array([1.0, 1.0, 1.0]), 0.07)
        cv.put(np.clip(-wr, 0, 1), np.array([0.0, 0.0, 0.0]), 0.18)
    edge = 0.05 + 0.04 * vnoise(rng, cv.H, 4, k * 0.3)[:, :1].repeat(cv.W, 1)
    old = (cv.x > w - edge).astype(np.float32)
    stripes = ((np.floor(cv.y / 0.35) % 2) > 0).astype(np.float32)
    cv.put(old, paint("#c9b9a0") * (0.8 + 0.2 * stripes[..., None]))
    cv.put(old * stripes, paint("#a03a2a"), 0.7)
    rough = 0.45 + weather_face(cv, rng, 0.7, top_fade=0.15, grime=0.15) + 0.2 * old
    meta = dict(face_m=[w, h], note="IPX billboard vinyl (spec 2.12): black field, mark 52.7 % of the height at 41.8 %, gold bar at "
                                     "75.8 %, IPX.EXCHANGE at 85.9 %. No painted light: the four lamp arms light it in Unreal")
    return write_set("Billboard", cv, (4096, 2048), rough, None, meta)


def face_onesheet(rng):
    w, h = 1.14, 1.72
    k = 2048 / h
    cv = Canvas(w, h, k, paint("#141519"))
    n = vnoise(rng, cv.H, cv.W, k * 0.5)
    cv.c = cv.c * (0.92 + 0.14 * (1 - cv.y / h)[..., None] + 0.04 * n[..., None])
    ink, gold, grey = paint("#f4f2ec"), paint("#f6c21a"), paint("#a9a7a0")
    m = 0.08 * w
    cv.put(cv.rect(m, 0.062 * h, w - m, 0.062 * h + 0.004), gold)
    t, _tw, _ = cv.text("IPX PRESENTS", "bold", 0.030, w / 2, 0.105 * h, 1.0, 0.32)
    cv.put(t, ink)
    for word, col, cy in (("MURDER", ink, 0.30), ("INC.", gold, 0.475)):
        tm, _w, _ = cv.text(word, "heavy", 0.26, w / 2, cy * h, 0.62, 0.0, max_w=w - 2 * m)
        cv.put(tm, col)
    t, _tw, _ = cv.text("STARRING JA RULE", "bold", 0.040, w / 2, 0.625 * h, 1.0, 0.18, max_w=w - 2 * m)
    cv.put(t, ink)
    cv.put(cv.rect(w * 0.3, 0.680 * h, w * 0.7, 0.680 * h + 0.008), gold)
    put_ipx(cv, w / 2, 0.80 * h, 0.15, ink)
    t, _tw, _ = cv.text("IPX.EXCHANGE", "bold", 0.028, w / 2, 0.905 * h, 1.0, 0.3)
    cv.put(t, grey)
    clean = cv.c.copy()
    rough = 0.25 + weather_face(cv, rng, 0.45, top_fade=0.12, grime=0.2)
    side = 0.75 + 0.25 * sstep(0.0, 0.25, np.minimum(cv.x, w - cv.x))
    E = to_lin(clean) * side[..., None] * 1.2
    meta = dict(face_m=[w, h], emissive_day=0.6,
                note="bus-shelter one-sheet (spec 2.13 ipx_ad, ART_BIBLE 5.4), back-lit behind glass, both faces of the ad box")
    return write_set("BusShelter", cv, (1024, 2048), rough, E, meta)


def face_mural(rng):
    """12 x 7.6 m, layer by layer from spec 2.12, then the wall's life: sun-fade at the top, lime pushing through,
    peeling at the base (holes in the alpha show the brick), chips, the ghost outline of a demolished building."""
    w, h = 12.0, 7.6
    k = 4096 / w
    cv = Canvas(w, h, k, (0, 0, 0))
    v = cv.y / h
    top, mid, bot = paint("#111a33"), paint("#3b1420"), paint("#0b0c12")
    t1 = np.clip(v / 0.62, 0, 1)[..., None]
    t2 = np.clip((v - 0.62) / 0.38, 0, 1)[..., None]
    cv.c = np.where(v[..., None] < 0.62, top * (1 - t1) + mid * t1, mid * (1 - t2) + bot * t2)
    rcx, rcy, R = 0.30 * w, 0.56 * h, 0.40 * h
    ang = np.arctan2(cv.y - rcy, cv.x - rcx)
    wedge = np.floor((ang + math.pi) / (2 * math.pi) * 36).astype(int)
    on = (wedge % 2 == 0)
    gold_ray = on & ((wedge // 2) % 2 == 0)
    red_ray = on & ((wedge // 2) % 2 == 1)
    cv.put(gold_ray.astype(np.float32), paint("#f6c21a"), 0.20)
    cv.put(red_ray.astype(np.float32), paint("#e2222b"), 0.14)
    r = np.sqrt((cv.x - rcx) ** 2 + (cv.y - rcy) ** 2)
    aa = 1.5 / k
    cv.put(sstep(R + aa, R - aa, r), paint("#d9a514"))
    for f in np.arange(0.42, 0.97, 0.045):
        cv.put(sstep(0.012, 0.004, np.abs(r - f * R)), paint("#4a3008"), 0.55)
    cv.put(sstep(0.34 * R + aa, 0.34 * R - aa, r), paint("#8a1a22"))
    cv.put(sstep(0.045 * R + aa, 0.045 * R - aa, r), paint("#0b0c12"))
    # the El in silhouette along the bottom
    el = paint("#07080c")
    sil = ((v > 0.78) & (v < 0.825)) | (v > 0.955)
    sil = sil.astype(np.float32)
    for i, xc in enumerate(np.arange(0.06 * w, w, 0.115 * w)):
        col_ = (np.abs(cv.x - xc) < 0.012 * w) & (v > 0.825)
        hy = (v > 0.825) & (v < 0.87) & (np.abs(cv.x - xc) < 0.012 * w + (0.87 - v) * h * 0.45)
        sil = np.maximum(sil, (col_ | hy).astype(np.float32))
    cv.put(sil, el)
    ink = paint("#f4f2ec")
    put_ipx(cv, 0.77 * w, 0.60 * h, 0.17 * h, ink)
    ad, _aw, _ = cv.text("IPX.EXCHANGE", "semi", None, 0.77 * w, 0.725 * h, 1.0, 0.05, size=0.05 * h)
    cv.put(ad, ink)
    fr = cv.rect(0.02 * h, 0.02 * h, w - 0.02 * h, h - 0.02 * h, outline=0.012 * h)
    cv.put(fr, paint("#f6c21a"))
    # RULE, sprayed big over it: soft edges, overspray, drips (6.4 x 2.3 m, centre at 73 % W, 23 % H)
    rx, ry, rw, rh = 0.733 * w - 0.2, 0.230 * h, 6.4, 2.3
    m, (i0, i1), tp, bs = text_mask("RULE", "heavyIt", cap_px=rh * k * 0.86, cond=1.0, track_em=-0.02)
    rows = np.where(m.max(axis=1) > 0.02)[0]
    m = m[rows[0]:rows[-1] + 1, i0:i1]
    im = Image.fromarray((m * 255).astype(np.uint8)).resize((int(rw * k), int(rh * k)), Image.LANCZOS)
    tm = np.asarray(im, np.float32) / 255.0
    hh, ww = tm.shape
    dy = (vnoise(rng, hh, ww, k * 0.5) - 0.5) * 0.06 * k
    dx = (vnoise(rng, hh, ww, k * 0.5) - 0.5) * 0.06 * k
    yy, xx = np.mgrid[0:hh, 0:ww]
    tm = tm[np.clip((yy + dy).astype(int), 0, hh - 1), np.clip((xx + dx).astype(int), 0, ww - 1)]
    rule = cv.blank()
    oy, ox = int(ry * k - hh / 2), int(rx * k - ww / 2)
    ys1, xs1 = min(hh, cv.H - oy), min(ww, cv.W - ox)
    rule[oy:oy + ys1, ox:ox + xs1] = tm[:ys1, :xs1]
    soft = np.asarray(Image.fromarray((rule * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.012 * k)), np.float32) / 255
    halo = np.asarray(Image.fromarray((rule * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.10 * k)), np.float32) / 255
    drips = cv.blank()
    bottoms = np.where((rule[1:, :] < 0.3) & (rule[:-1, :] > 0.7))
    sel = rng.choice(len(bottoms[0]), size=min(70, len(bottoms[0])), replace=False) if len(bottoms[0]) else []
    for i in sel:
        y0, x0 = bottoms[0][i], bottoms[1][i]
        ln = int(rng.uniform(0.05, 0.45) * k)
        wd = max(1, int(rng.uniform(0.006, 0.014) * k))
        for j in range(ln):
            t_ = 1 - j / ln * 0.6
            ww_ = max(1, int(wd * t_))
            yy_ = y0 + j
            if yy_ >= cv.H:
                break
            drips[yy_, max(0, x0 - ww_ // 2):x0 + ww_ // 2 + 1] = 1.0
    gold = paint("#f6c21a")
    cv.put(halo, gold, 0.18)
    cv.put(np.clip(soft * 1.15, 0, 1), gold)
    cv.put(drips, gold, 0.9)
    shade = soft * sstep(ry - 0.2 * rh, ry + 0.6 * rh, cv.y)
    cv.put(shade, gold * 0.62, 0.35)
    # the wall's life
    n1, n2 = vnoise(rng, cv.H, cv.W, k * 1.2), vnoise(rng, cv.H, cv.W, k * 0.15)
    fade = (0.08 + 0.30 * sstep(0.45, 0.0, v) * (0.6 + 0.6 * n1))[..., None]
    chalk = cv.c * 0.6 + 0.4 * np.mean(cv.c, -1, keepdims=True) + 0.12
    cv.c = cv.c * (1 - fade) + chalk * fade
    gx = np.interp(cv.x, [0, 0.35 * w, 0.62 * w, w], [0.58 * h, 0.30 * h, 0.30 * h, 0.52 * h])  # demolished neighbour's roof line
    below = sstep(-0.05, 0.05, cv.y - gx)
    cv.c = cv.c * (1 - 0.06 * below[..., None])
    cv.put(sstep(0.05, 0.0, np.abs(cv.y - gx)) * (0.5 + 0.5 * n2), paint("#2a2a2c") * 0.8, 0.25)
    lime = cv.blank()
    for (lx, ly, lr) in ((0.12 * w, 0.42 * h, 0.45), (0.52 * w, 0.66 * h, 0.35), (0.88 * w, 0.18 * h, 0.30)):
        d = np.sqrt(((cv.x - lx) / 1.4) ** 2 + (cv.y - ly) ** 2) / lr
        lime = np.maximum(lime, sstep(1.0, 0.3, d + 0.35 * (n2 - 0.5)))
        lime = np.maximum(lime, sstep(1.0, 0.5, np.abs(cv.x - lx) / 0.05 + 0.5 * n2) * sstep(ly - 0.1, ly + 0.2, cv.y) *
                          sstep(ly + lr * 3, ly + 0.2, cv.y))                     # a run below the bloom
    cv.put(lime, paint("#d8d4c8"), 0.75)
    holes = vnoise(rng, cv.H, cv.W, k * 0.06)
    base_peel = sstep(1.3, 0.2, h - cv.y)                                       # peeling over the lowest metre or so
    alpha = 1.0 - sstep(0.62, 0.70, holes * (0.35 + 0.75 * base_peel) + 0.10 * n1)
    chips = sstep(0.975, 0.99, vnoise(rng, cv.H, cv.W, k * 0.03)) * (0.3 + 0.7 * base_peel)
    alpha = np.clip(alpha - chips, 0, 1)
    edge = np.clip(np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)), np.float32) / 255, 0, 1)
    cv.put(alpha - edge, paint("#d8d2c0"), 0.6)                                 # flake edges catch light
    cv.a = alpha
    rough = 0.62 + 0.16 * n2 + 0.1 * lime
    meta = dict(face_m=[w, h], note="mural on the pawn shop's east side wall, centre web (-15.98, 4.5, 18.4): spec 2.12 layers + RULE "
                                     "spray; alpha = paint coverage. Decal: keep the wall's normal at ~70 %, roughness 0.6 .. 0.8")
    return write_set("Mural", cv, (4096, 2048), rough, None, meta, alpha=True)


def draw_faces(ctx):
    for key, S in SIGNS.items():
        rng = ctx.rng("face", key)
        {"lightbox": lambda: face_lightbox(key, S, rng), "neon": lambda: face_pan(key, S, rng, "neon"),
         "flex": lambda: face_pan(key, S, rng, "flex"), "letters": lambda: face_pan(key, S, rng, "letters"),
         "wood": lambda: face_wood(key, S, rng)}[S["kind"]]()
        ctx.log("face Sign_%s" % key)
    face_billboard(ctx.rng("face", "billboard"))
    face_onesheet(ctx.rng("face", "onesheet"))
    face_mural(ctx.rng("face", "mural"))
    m = ipx_master(1024)
    d = set_dir("IPXMark")
    Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8), "RGBA").save(os.path.join(d, "T_Sign_IPXMark_BC.png"))
    with open(os.path.join(d, "set.json"), "w") as f:
        json.dump(dict(kind="sign", resolution=list(m.shape[1::-1]), alpha="mark coverage", face_m=None,
                       note="the IPX master mark (spec 2.3), white on transparent: every IPX mark is pasted from ipx_master()"), f, indent=1)
    ctx.log("faces: billboard, one-sheet, mural, IPX master")


# ================================================================================================= outlines

def outlines(text, key, cap, cond=1.0, track=0.0):
    """Glyph contours of one line as closed polylines [(n, 2)] in metres: caps `cap` tall, baseline at 0,
    ink from x = 0. Also the filled glyphs as a mesh (verts (n, 2), faces). Blender's own font machinery."""
    f = bpy.data.fonts.load(FONTS[key], check_existing=True)
    cu = bpy.data.curves.new("sgn_txt", "FONT")
    cu.body, cu.font, cu.size = text, f, 1.0
    cu.space_character = 1.0 + track
    ob = bpy.data.objects.new("sgn_txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    c2 = oe.to_curve(dg)
    loops = []
    for sp in c2.splines:
        bp = sp.bezier_points
        n = len(bp)
        pts = []
        for i in range(n):
            p0, p1 = np.array(bp[i].co[:2]), np.array(bp[i].handle_right[:2])
            p2, p3 = np.array(bp[(i + 1) % n].handle_left[:2]), np.array(bp[(i + 1) % n].co[:2])
            t = np.linspace(0, 1, 12, endpoint=False)[:, None]
            pts.append((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3)
        loops.append(np.concatenate(pts))
    oe.to_curve_clear()
    me = bpy.data.meshes.new_from_object(oe)
    FV = np.array([v.co[:2] for v in me.vertices])
    FF = [list(p.vertices) for p in me.polygons]
    bpy.data.meshes.remove(me)
    hb = bpy.data.curves.new("sgn_h", "FONT")
    hb.body, hb.font, hb.size = "H", f, 1.0
    oh = bpy.data.objects.new("sgn_h", hb)
    bpy.context.scene.collection.objects.link(oh)
    dg = bpy.context.evaluated_depsgraph_get()
    mh = bpy.data.meshes.new_from_object(oh.evaluated_get(dg))
    caph = max(v.co.y for v in mh.vertices) - min(v.co.y for v in mh.vertices)
    bpy.data.meshes.remove(mh)
    for o, c in ((ob, cu), (oh, hb)):
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.curves.remove(c)
    s = cap / caph
    x0 = min(l[:, 0].min() for l in loops)
    sc = np.array([s * cond, s])
    loops = [(l - [x0, 0]) * sc for l in loops]
    FV = (FV - [x0, 0]) * sc
    return loops, FV, FF


def resample(P, step):
    """Closed polyline resampled by arc length (corners are rounded by less than step / 2)."""
    Q = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    keep = np.concatenate([[True], seg[:-1] > 1e-7])
    P = P[keep]
    Q = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    n = max(8, int(L / step))
    t = np.linspace(0, L, n, endpoint=False)
    return np.stack([np.interp(t, s, Q[:, 0]), np.interp(t, s, Q[:, 1])], 1)


def area2(P):
    Q = np.roll(P, -1, 0)
    return float(np.sum(P[:, 0] * Q[:, 1] - Q[:, 0] * P[:, 1])) / 2


def ink_normals(P, ink_left):
    """Per-vertex unit normals pointing into the ink (mitred, clamped)."""
    T = np.roll(P, -1, 0) - P
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    Nl = np.stack([-T[:, 1], T[:, 0]], 1)
    if not ink_left:
        Nl = -Nl
    Nv = Nl + np.roll(Nl, 1, 0)
    Nv /= np.maximum(np.linalg.norm(Nv, axis=1, keepdims=True), 1e-9)
    c = np.clip(np.einsum("ij,ij->i", Nv, Nl), 0.4, 1.0)
    return Nv / c[:, None]


def layout_line(text, key, cap, cond, track, w, h, cy, max_w, step):
    """Contours of a line centred on the face (caps centred cy from the top): (loops in face metres, fill, ink_left, scale)."""
    loops, FV, FF = outlines(text, key, cap, cond, track)
    wid = max(l[:, 0].max() for l in loops)
    sc = min(1.0, max_w / wid)
    off = np.array([w / 2 - wid * sc / 2, h * (1 - cy) - cap * sc / 2])
    loops = [l * sc + off for l in loops]
    FV = FV * sc + off
    big = max(loops, key=lambda l: abs(area2(l)))
    ink_left = area2(big) > 0
    loops = [resample(l, step) for l in loops]
    return loops, (FV, FF), ink_left, sc


# ================================================================================================= geometry

def B(seed=0, step=0.15):
    return steel.Builder(step=step, seed=seed)


def bx(b, lo, hi, slot, ch=0.0, **kw):
    return facade.bx(b, lo, hi, slot, ch=ch, pin=False, **kw)


def mesh(b, V, faces, slot, **kw):
    faces = [f for f in faces if len(f) >= 3]
    return b._add(np.asarray(V, np.float64), np.concatenate([np.asarray(f) for f in faces]), [len(f) for f in faces], slot,
                  kind=b.OTHER, **kw)


def card(b, o, du, dv, slot, nu=1, nv=1, lift=None, sign=True):
    """Quad grid from o along du, dv facing du x dv; lift(s, t) -> offset along that normal; sign: UVs 0..1."""
    o, du, dv = (np.asarray(v, np.float64) for v in (o, du, dv))
    nrm = np.cross(du, dv)
    nrm /= np.linalg.norm(nrm)
    s, t = np.linspace(0, 1, nu + 1), np.linspace(0, 1, nv + 1)
    S_, T_ = np.meshgrid(s, t)
    V = o + S_[..., None] * du + T_[..., None] * dv
    if lift is not None:
        V = V + lift(S_, T_)[..., None] * nrm
    idx = lambda r, c: r * (nu + 1) + c
    F = [[idx(r, c), idx(r, c + 1), idx(r + 1, c + 1), idx(r + 1, c)] for r in range(nv) for c in range(nu)]
    kw = dict(uv_off=(0.0, 0.0), uv_org=o, vdir=dv, fdir=du) if sign else {}
    return mesh(b, V.reshape(-1, 3), F, slot, **kw)


def to3(P2, y):
    """Face coordinates (x along the sign, z up) at depth y."""
    return np.stack([P2[:, 0], np.full(len(P2), y), P2[:, 1]], 1)


def tube(b, P3, r, slot, seg=8, closed=True, plane=Y):
    """Round tube along a polyline lying in a plane (normal `plane`); rings of `seg` vertices, faces outward."""
    P3 = np.asarray(P3, np.float64)
    n = len(P3)
    if closed:
        T = np.roll(P3, -1, 0) - np.roll(P3, 1, 0)
    else:
        T = np.gradient(P3, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    pn = np.asarray(plane, np.float64)
    N = np.cross(pn, T)
    bad = np.linalg.norm(N, axis=1) < 1e-6
    N[bad] = np.cross(T[bad], X if abs(pn[0]) < 0.9 else Z)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    Bn = np.cross(T, N)
    a = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    V = P3[:, None, :] + r * (np.cos(a)[None, :, None] * N[:, None, :] + np.sin(a)[None, :, None] * Bn[:, None, :])
    m = n if closed else n - 1
    F = []
    for i in range(m):
        j = (i + 1) % n
        for k_ in range(seg):
            k2 = (k_ + 1) % seg
            F.append([i * seg + k_, j * seg + k_, j * seg + k2, i * seg + k2])
    V = V.reshape(-1, 3)
    f0 = F[0]
    fn = np.cross(V[f0[1]] - V[f0[0]], V[f0[3]] - V[f0[0]])
    if np.dot(fn, V[f0[0]] - P3[0]) < 0:
        F = [f[::-1] for f in F]
    return mesh(b, V, F, slot)


def strip(b, A, Bv, slot, want):
    """Closed band of quads between two loops with the same count; `want` (n, 3): wanted normals."""
    n = len(A)
    V = np.vstack([A, Bv])
    F = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    f0 = F[0]
    fn = np.cross(V[f0[1]] - V[f0[0]], V[f0[3]] - V[f0[0]])
    if np.dot(fn, want[0]) < 0:
        F = [f[::-1] for f in F]
    return mesh(b, V, F, slot)


def fill(b, FV, FF, y, slot, front=True):
    V = to3(np.asarray(FV), y)
    F = [list(f) for f in FF]
    if F:
        f0 = F[0]
        fn = np.cross(V[f0[1]] - V[f0[0]], V[f0[2]] - V[f0[0]])
        if (fn[1] < 0) != front:
            F = [f[::-1] for f in F]
    return mesh(b, V, F, slot)


def rounded_rect(x0, z0, x1, z1, r, step):
    pts = []
    for cx, cz, a0 in ((x1 - r, z0 + r, -90), (x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180)):
        for a in np.radians(np.linspace(a0, a0 + 90, 10)):
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return resample(np.array(pts), step)


def cyl(b, p0, p1, r, slot, seg=8):
    return facade.rod(b, p0, p1, r, slot, n=seg)


def neon_line(b, S, text, key, cap, cy, cond, slot, r, y_tube, max_w, standoff=True, boots=True, inset=0.0, track=0.02,
              floor_y=None, pan=None):
    """Tubes along the letter outlines of one line, with standoffs back to the pan (y = 0 or floor_y) and two
    electrode boots per contour. inset > 0: the tube runs inside the stroke (pan letters). Returns the layout."""
    w, h = S["w"], S["h"]
    loops, fillm, ink_left, sc = layout_line(text, key, cap, cond, track, w, h, cy, max_w, step=max(0.006, cap * 0.035))
    back = 0.0 if floor_y is None else floor_y
    for P in loops:
        Q = P
        if inset:
            Q = P + ink_normals(P, ink_left) * inset
        tube(b, to3(Q, y_tube), r, slot)
        if standoff:
            L = np.sum(np.linalg.norm(np.diff(np.vstack([Q, Q[:1]]), axis=0), axis=1))
            ns = max(2, int(L / 0.22))
            for i in np.linspace(0, len(Q), ns, endpoint=False).astype(int):
                cyl(b, (Q[i, 0], y_tube + r * 0.8, Q[i, 1]), (Q[i, 0], back, Q[i, 1]), 0.0045, "standoff", seg=6)
        if boots:
            i0 = int(np.argmin(Q[:, 1] + 0.001 * Q[:, 0]))
            for di in (-2, 2):
                q = Q[(i0 + di) % len(Q)]
                cyl(b, (q[0], y_tube, q[1]), (q[0], back, q[1]), r * 1.55, "rubber", seg=8)
    return loops, fillm, ink_left


def neon_mat(colour_name, hexcol):
    c = rgb(hexcol)
    grey = rgb("#9a9aa2")
    base = to_lin(c * 0.45 + grey * 0.55)
    m = bpy.data.materials.get("MI_Neon_" + colour_name) or bpy.data.materials.new("MI_Neon_" + colour_name)
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*base, 1.0)
    p.inputs["Roughness"].default_value = 0.22
    p.inputs["Coat Weight"].default_value = 0.6
    p.inputs["Emission Color"].default_value = (*to_lin(c), 1.0)
    p.inputs["Emission Strength"].default_value = 6.0
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    m["mi_emit_day"] = 0.55
    return m


NEON = {"#ff3030": "Red", "#55ff8a": "Green", "#f6c21a": "Gold", "#35e0ff": "Cyan", "#ff3d9a": "Pink"}


def materials(ctx):
    M = facade.materials(ctx)
    for h_, n_ in NEON.items():
        M["neon" + n_] = neon_mat(n_, h_)
    M["standoff"] = mat.flat("MI_Glass_Standoff", (0.80, 0.82, 0.80), 0.08)
    M["acrylic"] = mat.make("MI_Glass_Acrylic", "glass", Film=0.04)
    rub = paths.texture_set("TS_Rubber_Aged")
    if mat.find_set_files(rub):
        with open(os.path.join(rub, "set.json")) as f_:
            tile = json.load(f_).get("tile_m", 0.5)
        M["rubber"] = mat.from_texture_set(rub, name="MI_Rubber_Aged", alpha="splash", tile_m=tile)
    else:
        M["rubber"] = mat.flat("MI_Rubber_Aged", (0.03, 0.03, 0.03), 0.7)
        M["rubber"]["mi_tile_m"] = (0.5, 0.5)
    for key in list(SIGNS) + ["Mural"]:
        if "sign" + key not in M:
            M["sign" + key] = mat.sign_face(key, (0.3, 0.3, 0.3))
        S = SIGNS.get(key)
        M["sign" + key]["mi_tile_m"] = (S["w"], S["h"]) if S else (12.0, 7.6)
    return M


def whip(b, pts, slot="rubber", r=0.011):
    P = np.asarray(pts, np.float64)
    t = np.linspace(0, 1, 24)
    # smooth Catmull-Rom through the points
    out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(0, i - 1)], P[i], P[i + 1], P[min(len(P) - 1, i + 2)]
        for s in np.linspace(0, 1, 8, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s + (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3))
    out.append(P[-1])
    return tube(b, np.array(out), r, slot, seg=8, closed=False, plane=Z)


def sign_lightbox(ctx, M, key, S):
    w, h = S["w"], S["h"]
    D = DEPTH["lightbox"]
    b = B(len(key))
    f = 0.045 * h
    bx(b, (0.0, 0.014, 0.0), (w, D, h), "trim", ch=0.006, axis="x")                     # extruded cabinet
    for lo, hi in (((-0.004, -0.016, -0.004), (w + 0.004, 0.016, f)), ((-0.004, -0.016, h - f), (w + 0.004, 0.016, h + 0.004)),
                   ((-0.004, -0.016, f), (f, 0.016, h - f)), ((w - f, -0.016, f), (w + 0.004, 0.016, h - f))):
        bx(b, lo, hi, "trim", ch=0.003, axis="x")                                       # retainer frame
    rise = S.get("raised", 0.006)
    edge = 0.10 if S.get("raised") else 0.5
    lift = lambda s, t: -rise * sstep(0.0, edge / w, np.minimum(s, 1 - s)) * sstep(0.0, edge / h, np.minimum(t, 1 - t)) \
        if S.get("raised") else -rise * np.sin(np.pi * s) * np.sin(np.pi * t)
    nu = max(8, int(w / 0.05)) if S.get("raised") else max(8, int(w / 0.25))
    nv = 16 if S.get("raised") else 4
    card(b, (0, 0.0, 0), (w, 0, 0), (0, 0, h), "sign" + key, nu, nv, lift=lambda s, t: -lift(s, t))
    zz = np.arange(0.3, w - 0.2, 0.6)
    b.rivets(np.stack([zz, np.full_like(zz, -0.016), np.full_like(zz, f / 2)], 1), (0, -1, 0), "alu", d=0.010, h=0.003, seg=6, leak=0.5)
    b.rivets(np.stack([zz, np.full_like(zz, -0.016), np.full_like(zz, h - f / 2)], 1), (0, -1, 0), "alu", d=0.010, h=0.003, seg=6, leak=0.3)
    for xh in np.arange(0.05, w - 0.05, 0.3):                                            # piano hinge of the service edge
        cyl(b, (xh, -0.010, h + 0.006), (xh + 0.25, -0.010, h + 0.006), 0.005, "alu", seg=6)
    for xl in (w * 0.2, w * 0.5, w * 0.8):                                               # latches on the bottom edge
        bx(b, (xl - 0.03, -0.022, -0.012), (xl + 0.03, 0.01, 0.006), "alu", ch=0.002)
    for xc in (0.45, w - 0.45):                                                          # Z clips into the fascia
        bx(b, (xc - 0.04, D - 0.05, -0.035), (xc + 0.04, D, -0.004), "black", ch=0.002)
        bx(b, (xc - 0.04, D - 0.004, -0.035), (xc + 0.04, D, 0.06), "black")
    whip(b, [(w - 0.02, D * 0.5, h * 0.25), (w + 0.07, D * 0.45, h * 0.18), (w + 0.10, D * 0.6, -0.05), (w + 0.06, D * 0.9, -0.12),
             (w + 0.02, D + 0.02, -0.10)], "rubber", 0.010)
    notes = ("Lightbox (ART_BIBLE 5.2): extruded aluminium cabinet %.2f deep, retainer frame %.0f mm, printed flex face in slot "
             "M_Sign_%s (BC + E, 0..1 UVs; E = night, x 0.3 by day)%s, piano hinge on the top edge, three latches, Z clips, power whip "
             "at the right end. Text: \"%s\"%s." % (D, f * 1000, key, ", face raised %.0f mm" % (rise * 1000) if S.get("raised") else
                                                   ", face bowed 6 mm", S["text"], (" / \"%s\"" % S["sub"]) if S.get("sub") else ""))
    return b, D, notes


def neon_on_pan(ctx, M, key, S, kind):
    w, h = S["w"], S["h"]
    D = DEPTH[kind]
    b = B(len(key) + 1)
    col = "neon" + NEON[S["tube"]]
    if kind == "wood":
        bx(b, (0, 0.004, 0), (w, 0.024, h), "wood", ch=0.003, axis="x")                 # 18 mm ply (+ paint)
        for zb in (0.06, h - 0.10):
            bx(b, (0.05, 0.024, zb), (w - 0.05, D, zb + 0.04), "timber", ch=0.003, axis="x")   # battens
        mw = 0.032
        for lo, hi in (((-0.01, -0.022, -0.01), (w + 0.01, 0.006, mw)), ((-0.01, -0.022, h - mw), (w + 0.01, 0.006, h + 0.01)),
                       ((-0.01, -0.022, mw), (mw, 0.006, h - mw)), ((w - mw, -0.022, mw), (w + 0.01, 0.006, h - mw))):
            bx(b, lo, hi, "wood", ch=0.006, axis="x")                                      # moulding
    else:
        bx(b, (0, 0.003, 0), (w, D, h), "black", ch=0.004, axis="x")                     # pan
        for lo, hi in (((-0.006, -0.008, -0.006), (w + 0.006, 0.006, 0.014)), ((-0.006, -0.008, h - 0.014), (w + 0.006, 0.006, h + 0.006)),
                       ((-0.006, -0.008, 0.014), (0.014, 0.006, h - 0.014)), ((w - 0.014, -0.008, 0.014), (w + 0.006, 0.006, h - 0.014))):
            bx(b, lo, hi, "black" if kind == "neon" else "alu", ch=0.003, axis="x")          # rolled lip / extrusion
    card(b, (0, 0.0, 0), (w, 0, 0), (0, 0, h), "sign" + key, max(4, int(w / 0.5)), 2)
    if kind == "flex":
        r, yt, stand = 0.0045, -0.0055, False
        bx(b, (-0.008, -0.064, -0.008), (w + 0.008, -0.004, 0.006), "alu", ch=0.002, axis="x")
        bx(b, (-0.008, -0.064, h - 0.006), (w + 0.008, -0.004, h + 0.008), "alu", ch=0.002, axis="x")
        bx(b, (-0.008, -0.064, 0.006), (0.006, -0.004, h - 0.006), "alu", ch=0.002)
        bx(b, (w - 0.006, -0.064, 0.006), (w + 0.008, -0.004, h - 0.006), "alu", ch=0.002)
        card(b, (0.006, -0.058, 0.006), (w - 0.012, 0, 0), (0, 0, h - 0.012), "acrylic", 4, 1, sign=False)
        rs = 0.0035
    else:
        r, yt, stand, rs = 0.0065, -0.0415, True, 0.0040
    mxw = w - 2 * 0.16 * h
    neon_line(b, S, S["text"], S["font"], S["cap"], S["cy"], S["cond"], col, r, yt, mxw, stand, kind != "flex")
    if S.get("sub"):
        neon_line(b, S, S["sub"], "medium", S["subcap"], S["subcy"], 0.92, col, rs, yt + (r - rs), mxw, stand, False, track=0.06)
    if kind != "flex":
        bt = rounded_rect(0.09 * h, 0.09 * h, w - 0.09 * h, h - 0.09 * h, 0.14 * h, 0.01)
        tube(b, to3(bt, yt), r, col)
        for i in np.linspace(0, len(bt), 12, endpoint=False).astype(int):
            cyl(b, (bt[i, 0], yt + r * 0.8, bt[i, 1]), (bt[i, 0], 0.0, bt[i, 1]), 0.0045, "standoff", seg=6)
        bx(b, (w - 0.62, 0.01, h + 0.002), (w - 0.30, 0.13, h + 0.11), "grey", ch=0.004)  # transformer box on top
        whip(b, [(w - 0.46, 0.07, h + 0.11), (w - 0.46, 0.08, h + 0.20), (w - 0.40, D + 0.02, h + 0.24), (w - 0.36, D + 0.05, h + 0.20)],
             "rubber", 0.008)
    if kind == "flex":
        whip(b, [(w - 0.1, D * 0.5, 0.0), (w - 0.1, D * 0.6, -0.08), (w - 0.05, D + 0.03, -0.12)], "rubber", 0.006)
    what = {"neon": "Exposed glass neon (ART_BIBLE 5.2): 13 mm tube along the letter outlines on 35 mm glass standoffs, two electrode "
                    "boots per loop, border tube inset 9 %%, on a painted steel pan (face slot M_Sign_%s), transformer box on top" % key,
            "wood": "Cyan exposed neon over a hand-painted plywood fascia (ART_BIBLE 5.3): tubes on standoffs, painted board in slot "
                    "M_Sign_%s with a moulding, on battens, transformer box on top" % key,
            "flex": "Pink LED flex (9 mm) along the letter outlines on a black backer (M_Sign_%s), clear acrylic cover "
                    "(MI_Glass_Acrylic) in an aluminium edge extrusion" % key}[kind]
    return b, D, "%s. Tube material %s. Text: \"%s\"%s." % (what, M[col].name, S["text"], (" / \"%s\"" % S["sub"]) if S.get("sub") else "")


def pan_letters(ctx, M, key, S):
    w, h = S["w"], S["h"]
    b = B(len(key) + 2)
    Dl, t = 0.11, 0.003
    col = "neon" + NEON[S["tube"]]
    loops, (FV, FF), ink_left, sc = layout_line(S["text"], S["font"], S["cap"], S["cond"], 0.06, w, h, S["cy"], w - 0.5, step=0.008)
    for P in loops:
        Ni = ink_normals(P, ink_left)
        Pin = P + Ni * t
        Nout = np.column_stack([-Ni[:, 0], np.zeros(len(P)), -Ni[:, 1]])
        strip(b, to3(P, 0.0), to3(P, Dl), "trim", Nout)                                   # returns
        strip(b, to3(Pin, 0.0), to3(Pin, Dl - t), "trim", -Nout)                         # inside of the returns
        strip(b, to3(P, 0.0), to3(Pin, 0.0), "trim", np.tile([0, -1.0, 0], (len(P), 1)))   # lip
    fill(b, FV, FF, Dl - t, "black", front=True)                                         # tray floor
    fill(b, FV, FF, Dl, "trim", front=False)                                             # back
    neon_line(b, S, S["text"], S["font"], S["cap"], S["cy"], S["cond"], col, 0.0065, 0.05, w - 0.5, True, True,
              inset=0.024, track=0.06, floor_y=Dl - t)
    xs = [l[:, 0] for l in loops]
    x0, x1 = min(x.min() for x in xs) - 0.12, max(x.max() for x in xs) + 0.12
    zc = h * (1 - S["cy"])
    bx(b, (x0, Dl, zc - 0.05), (x1, Dl + 0.09, zc + 0.05), "trim", ch=0.004, axis="x")    # raceway
    bx(b, (x1 - 0.45, Dl + 0.005, zc - 0.045), (x1 - 0.20, Dl + 0.085, zc - 0.05 + 0.004), "grey")
    whip(b, [(x1, Dl + 0.045, zc), (x1 + 0.08, Dl + 0.05, zc - 0.05), (x1 + 0.10, Dl + 0.09, zc - 0.15), (x1 + 0.08, Dl + 0.09 + 0.02, zc - 0.20)],
         "rubber", 0.010)
    D = Dl + 0.09
    note = ("Open-face pan letters (ART_BIBLE 5.2): aluminium returns %.0f mm deep with a 3 mm lip, dark floor, %s tube inside on "
            "standoffs with electrode boots, on a raceway %.2f m long; the band face behind (M_Sign_%s) carries%s the ghost of "
            "an older sign. Text: \"%s\"." % (Dl * 1000, S["tube"], x1 - x0, key,
                                              " the sub line \"%s\" in white cut vinyl and" % S["sub"] if S.get("sub") else "", S["text"]))
    return b, D, note


def mount(key):
    """(x0, y, z0) of the sign's pivot in the frame of SM_Facade_SignBand_<key>."""
    S = SIGNS[key]
    s = facade.shop_local(key)
    return ((s["W"] - S["w"]) / 2, -(PAN_Y + DEPTH[S["kind"]]), (facade.BAND_H - S["h"]) / 2)


def mural_card(ctx, M):
    b = B(77)
    card(b, (0, 0, 0), (12.0, 0, 0), (0, 0, 7.6), "signMural", 24, 16)
    ob = b.finish("SM_Sign_Mural", {"signMural": M["signMural"]}, ctx.col)
    ctx.asset(ob, collision="none", expect_size=(12.0, None, 7.6), slots=SLOT_META,
              notes="The IPX / RULE mural as a decal card 12 x 7.6 m (pivot bottom-left, face -Y). Level: on the pawn shop's east side "
                    "wall, centre web (-15.98, 4.5, 18.4) = Blender (-15.98, -18.4, 4.5), facing east; best as a DBuffer decal of "
                    "M_Sign_Mural over the wall's brick (opacity = BC alpha, normal kept ~70 %%).")
    return ob


def build(ctx):
    have = all(os.path.exists(os.path.join(paths.texture_set("Sign_" + k), "T_Sign_%s_BC.png" % k)) for k in list(SIGNS) + ["Mural"])
    if ctx.args.bake or ctx.args.force or not have:
        draw_faces(ctx)
    M = materials(ctx)
    ctx.M, ctx.K = M, {}
    for key, S in SIGNS.items():
        kind = S["kind"]
        if kind == "lightbox":
            b, D, notes = sign_lightbox(ctx, M, key, S)
        elif kind == "letters":
            b, D, notes = pan_letters(ctx, M, key, S)
        else:
            b, D, notes = neon_on_pan(ctx, M, key, S, kind)
        ob = b.finish(S["mesh"], M, ctx.col)
        facade.weather(ctx, b, ob, key, ledges=[(0.0, S["w"], S["h"], 0.5)])
        x0, y0, z0 = mount(key)
        notes += (" Mount: on SM_Facade_SignBand_%s at band-local (%.3f, %.3f, %.3f) (the sign's back on the band's sign plate); "
                  "paired light per spec 2.17." % (key, x0, y0, z0))
        ctx.asset(ob, collision="box", expect_size=(S["w"], None, None) if kind not in ("letters",) else None,
                  notes=notes, slots=SLOT_META)
        ctx.K[key] = ob
        ctx.log("%-26s %7d tris" % (S["mesh"], geo.stats(ob)["triangles"]))
    ctx.K["Mural"] = mural_card(ctx, M)
    if "Sign_IPXMark" not in ctx.sets:
        ctx.sets.append("Sign_IPXMark")
    return [a["ob"] for a in ctx.assets.values()]


# ================================================================================================= previews

def day_glow(on=True):
    """Lit faces and tubes at their day share (spec 2.8: neon x 0.55, other signs x 0.3)."""
    for m in bpy.data.materials:
        if m.name.startswith("MI_Neon_"):
            mat.principled(m).inputs["Emission Strength"].default_value = 6.0 * 0.55 * 0.6 if on else 6.0
        elif m.name.startswith("M_Sign_") and m.get("mi_emit_day") is not None:
            p = mat.principled(m)
            if p.inputs["Emission Color"].is_linked:
                p.inputs["Emission Strength"].default_value = float(m["mi_emit_day"]) if on else 1.0


def on_preview(ctx, objs):
    a = ctx.args
    Pv = paths.previews
    only = set(a.only or [])
    want = lambda nm: not only or nm in only
    day_glow(True)
    render.setup(samples=a.samples)
    sun = render.DESIGN_SUN_BEARING
    if want("signs_sheet"):
        render_sheet(ctx, sun, Pv)
    if want("signs_street") or want("signs_ipx"):
        for ob in ctx.col.all_objects:
            ob.hide_render = True
    if want("signs_street"):
        render_street(ctx, sun, Pv)
    if want("signs_ipx"):
        render_ipx(ctx, sun, Pv)


def relink(ob, col):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    col.objects.link(ob)
    return ob


def render_sheet(ctx, sun, Pv):
    """The ten signs side by side at one scale (orthographic), two columns, on a dark fascia."""
    for ob in ctx.col.all_objects:
        ob.hide_render = True
    col = scene.collection("SignSheet", ctx.col)
    keys = list(SIGNS)
    xs, row_h = (0.0, 9.0), 1.45
    for i, key in enumerate(keys):
        S = SIGNS[key]
        c, r = i % 2, i // 2
        ob = scene.duplicate(ctx.K[key], linked=True, col=col)
        x = xs[c] + (8.4 - S["w"]) / 2
        z = 8.0 - r * row_h
        ob.location = (x, -DEPTH[S["kind"]], z)
        ob.hide_render = False
        fas = geo.box((8.9, 0.02, 1.05), bevel=0.0)
        geo.transform(fas, loc=(xs[c] + 4.2, 0.0, z - 0.15))
        fas.data.materials.append(mat.flat("Fascia", (0.03, 0.03, 0.032), 0.5))
        relink(fas, col)
    wall = geo.box((22, 0.1, 9), bevel=0.0)
    geo.transform(wall, loc=(8.6, 0.12, 1.4))
    wall.data.materials.append(mat.flat("Wall", (0.16, 0.15, 0.14), 0.8))
    render.rig_day(sun_azimuth=200.0, stops=0.3)
    cam = render.cam_look((8.6 - 6.0, -30.0, 2.0), (8.6, 0.0, 5.0), lens=50, name="Cam_Sheet")
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 18.6
    _p, sec = render.render_jpeg(os.path.join(Pv, "signs_sheet.jpg"), ctx.args.samples)
    ctx.log("preview signs_sheet.jpg %.0fs" % sec)
    col.hide_render = True
    wall.hide_render = True


def render_street(ctx, sun, Pv):
    """The south block face of the facade sample (S1, S2, S3) with its signs on, the street in front."""
    from assets import street
    T0 = type(ctx)
    st = T0("street", ctx.args)
    street.build(st)
    dress = scene.collection("Dressing", st.col)
    for kx in (-4, -3, -2, -1, 1, 2, 3):
        for ob in st.placed:
            if ob.data is st.A["hydrant"].data:
                continue
            dd = scene.duplicate(ob, linked=True, col=dress)
            dd.location.x += kx * street.L
    render.backdrop(600.0, (0.075, 0.073, 0.07), z=-0.06)
    fc = T0("facade", ctx.args)
    facade.build(fc)
    fc.kit.hide_render = True
    fc.sample = scene.collection("FacadeSample", fc.col)
    placed = []
    for key in ("s1", "s2", "s3"):
        facade.assemble_front(fc, key, placed)
    facade.assemble_shell(fc, "s1", sides=(), out=placed)
    facade.assemble_shell(fc, "s2", sides=("L",), tank=(-23.0, -24.0), bulkhead=(-19.5, -28.75), out=placed)
    facade.assemble_shell(fc, "s3", sides=("L", "R"), bulkhead=(13.0, -20.75), out=placed)
    sc = scene.collection("SignsPlaced", ctx.col)
    for key in SIGNS:
        bld, xa, xb = facade.SHOPS[key][:3]
        fr = facade.front_frame(bld)
        north = facade.BUILDINGS[bld]["face"] == "N"
        x1 = facade.BUILDINGS[bld]["x"][1]
        x0b = facade.BUILDINGS[bld]["x"][0]
        s0 = (x1 - xb) if north else (xa - x0b)
        mx, my, mz = mount(key)
        ob = scene.duplicate(ctx.K[key], linked=True, col=sc)
        scene.place(ob, fr.at(s0 + mx, my, facade.BAND0 + mz), fr.rot)
        ob.hide_render = False
    mo = scene.duplicate(ctx.K["Mural"], linked=True, col=sc)                 # on S2's east side wall, facing east
    scene.place(mo, (-15.995, -24.4, 0.70), 90.0)
    mo.hide_render = False
    day_glow(True)
    render.rig_day(sun_azimuth=sun, stops=1.0)
    eye = 0.15 + 1.65
    render.cam_look((-6.0, 8.5, eye), (-6.0, -11.0, 3.4), lens=16, name="Cam_SignsStreet")
    _p, sec = render.render_jpeg(os.path.join(Pv, "signs_street.jpg"), ctx.args.samples)
    ctx.log("preview signs_street.jpg %.0fs" % sec)


def render_ipx(ctx, sun, Pv):
    """Billboard and bus shelter from the furniture family with their IPX faces."""
    from assets import furniture
    T0 = type(ctx)
    fc = T0("furniture", ctx.args)
    fc.built = []
    M = furniture.materials(fc)
    bs = furniture.bus_shelter(fc, M)
    bb = furniture.billboard(fc, M)
    scene.place(bs, (-3.0, -3.0, 0.0), 0.0)
    scene.place(bb, (4.0, 6.0, 0.0), 0.0)
    render.backdrop(400.0, (0.09, 0.088, 0.085), z=-0.01)
    brick = "TS_Brick_ScanRedCommon"
    wall = geo.box((12.8, 0.3, 9.5), bevel=0.0)                         # a common-brick side wall with the mural on it
    geo.transform(wall, loc=(-10.0, 10.15, 0.0))
    geo.uv_world_box(wall, mat.scan_tile(brick))
    wall.data.materials.append(ctx.scan_set(brick, alpha="splash"))
    geo.ensure_wear(wall)
    mo = scene.duplicate(ctx.K["Mural"], linked=True, col=ctx.col)
    scene.place(mo, (-16.0, 9.997, 0.70), 0.0)
    mo.hide_render = False
    day_glow(True)
    render.rig_day(sun_azimuth=200.0, stops=0.6)
    render.cam_look((-9.5, -16.0, 1.7), (-3.0, 3.0, 4.5), lens=24, name="Cam_IPX")
    _p, sec = render.render_jpeg(os.path.join(Pv, "signs_ipx.jpg"), ctx.args.samples)
    ctx.log("preview signs_ipx.jpg %.0fs" % sec)
