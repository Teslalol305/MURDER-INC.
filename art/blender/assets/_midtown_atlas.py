"""Midtown faces: the LED screen atlases, the ticker strip, the countdown digits, the LED pixel mask and the sign atlas.

    venv/bin/python art/blender/assets/_midtown_atlas.py          # draws every set into art/out/textures/ (about 40 s)

Sets (midtown.md 12.3 and 14.2; all opaque, one master material per kind, English only, invented names):
    MT_Screens_A, MT_Screens_B   4096 x 4096, 8 slides each: T_MT_Screens_<A|B>_E (sRGB). The screens' master
                                 M_MI_Screen is black (roughness 0.6); emissive = the slide x nits (450 hero, 300 others),
                                 a crossfade between two cells, the LED mask faded out between 8 and 20 m.
                                 Cells: horizontal 2048 x 1024, vertical 1024 x 2048. A slide is drawn at its screen's own
                                 aspect and stored squeezed into its cell, so the screen's 0..1 UVs map it back unstretched.
    MT_Ticker                    4096 x 256 strip (T_MT_Ticker_E), the three headlines, panned at 0.35 m/s, wraps in u.
    MT_Digits                    512 x 64 (T_MT_Digits_E): 16 cells of 32 x 64 px, names._DIGITS order (0-9, ':', ' ', '-').
    MT_LEDMask                   64 x 64 tiling (T_MT_LEDMask_M, linear): RGB sub-pixel dots of one LED module pixel.
    Sign_MT_Atlas1               4096 x 4096 (T_Sign_MT_Atlas1_BC sRGB, _ORM half size linear, _E sRGB night value): the
                                 printed faces (billboard C1, storefront bands, plaques, labels), skyline packed like
                                 Sign_CT_Atlas1, cells in set.json (uv with v up).
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from assets import _midtown_names as names  # noqa: E402
from assets import signs as sg  # noqa: E402
from mi import paths  # noqa: E402

ATLAS = 4096
PAD = 8
FD = "/usr/share/fonts"
FONT_FILES = {
    "mt_heavy": FD + "/opentype/inter/InterDisplay-Black.otf",
    "mt_bold": FD + "/opentype/inter/Inter-Bold.otf",
    "mt_semi": FD + "/opentype/inter/Inter-SemiBold.otf",
    "mt_light": FD + "/opentype/inter/Inter-Light.otf",
    "mt_italic": FD + "/opentype/inter/Inter-Italic.otf",
    "mt_serif": os.path.join(os.path.dirname(HERE), "fonts", "OldStandard-Bold.ttf"),
    "mt_script": os.path.join(os.path.dirname(HERE), "fonts", "PinyonScript-Regular.ttf"),
}
sg.FONTS.update(FONT_FILES)           # in-memory only: signs.Canvas.text looks fonts up by key
DENS = {"billboard": 128, "band": 256, "plaque": 384, "label": 1024}

# Screen atlas layout: (atlas, x, y, w, h) in px from the top-left.
H_CELL, V_CELL = (2048, 1024), (1024, 2048)
LAYOUT = {
    "G1_Takeover": ("A", 0, 0), "G1_NoSignal": ("A", 2048, 0), "G1_StandBy": ("A", 0, 1024), "IPX_Presents": ("A", 2048, 1024),
    "E1_Orbelle": ("A", 0, 2048), "E1_Northbound": ("A", 2048, 2048), "E3_Alderway": ("A", 0, 3072), "E3_Vesperline": ("A", 2048, 3072),
    "E2a_Kestrel": ("B", 0, 0), "E2b_BrassBun": ("B", 1024, 0), "IPX_Presents_E1": ("B", 0, 2048), "IPX_Presents_E3": ("B", 0, 3072),
    "N1_Quillon": ("B", 2048, 0), "N1_TamsinGray": ("B", 2048, 1024), "N1_Halcyon": ("B", 2048, 2048), "S1_Duskline": ("B", 2048, 3072),
}


def rgb(h):
    return sg.paint(h)


# ================================================================================================== slides

def _grad(cv, c0, c1, angle=90.0, power=1.0):
    a = math.radians(angle)
    t = (cv.x / cv.wm * math.cos(a) + cv.y / cv.hm * math.sin(a))
    t = (t - t.min()) / max(t.max() - t.min(), 1e-6)
    t = t ** power
    cv.c = rgb(c0) * (1 - t[..., None]) + rgb(c1) * t[..., None]


def _ellipse(cv, cx, cy, rx, ry, outline=None):
    def f(d, k):
        box = [(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k]
        if outline:
            d.ellipse(box, outline=255, width=max(1, int(outline * k)))
        else:
            d.ellipse(box, fill=255)
    return cv.draw(f)


def _poly(cv, pts):
    return cv.draw(lambda d, k: d.polygon([(x * k, y * k) for x, y in pts], fill=255))


def _glow(mask, cv, r_m):
    im = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(1, r_m * cv.k)))
    return np.asarray(im, np.float32) / 255.0


def _motif(cv, S, rng):
    """The picture of an ad, in its palette (bright accents only where the design allows)."""
    bg0, bg1, ink, acc = S["palette"]
    W, H = cv.wm, cv.hm
    art = S.get("art")
    if art == "bottle":                                                    # a perfume bottle with a soft halo, right
        cx, cy = W * 0.74, H * 0.56
        cv.put(_glow(_ellipse(cv, cx, cy, H * 0.22, H * 0.26), cv, H * 0.08), rgb(acc), 0.55)
        body = cv.rect(cx - H * 0.13, cy - H * 0.12, cx + H * 0.13, cy + H * 0.26, r=H * 0.05)
        cv.put(body, rgb("#d8ccff"), 0.85)
        cv.put(cv.rect(cx - H * 0.11, cy - H * 0.10, cx + H * 0.11, cy + H * 0.24, r=H * 0.04), rgb("#7c64c8"), 0.55)
        cv.put(cv.rect(cx - H * 0.035, cy - H * 0.22, cx + H * 0.035, cy - H * 0.12, r=H * 0.01), rgb("#e9e2ff"))
        cv.put(cv.rect(cx - H * 0.07, cy - H * 0.30, cx + H * 0.07, cy - H * 0.21, r=H * 0.02), rgb("#2a1f52"))
        cv.put(cv.rect(cx - H * 0.10, cy - H * 0.06, cx - H * 0.075, cy + H * 0.18, r=H * 0.01), rgb("#ffffff"), 0.6)
    elif art == "contrail":                                                # a contrail rising across a night sky, a plane
        for i in range(60):
            x, y = rng.uniform(0, W), rng.uniform(0, H * 0.7)
            cv.put(_ellipse(cv, x, y, 0.025, 0.025), rgb("#ffffff"), rng.uniform(0.3, 0.9))
        line = cv.draw(lambda d, k: d.line([(W * 0.36 * k, H * 1.02 * k), (W * 0.82 * k, H * 0.30 * k)], fill=255, width=int(0.18 * k)))
        cv.put(_glow(line, cv, 0.35), rgb(acc), 0.8)
        cv.put(line, rgb("#ffffff"), 0.9)
        px, py, s = W * 0.84, H * 0.27, H * 0.06
        cv.put(_poly(cv, [(px + 2.2 * s, py - 0.9 * s), (px - 1.4 * s, py + 0.9 * s), (px - 1.0 * s, py + 0.2 * s), (px - 2.4 * s, py + 0.3 * s),
                          (px - 0.4 * s, py - 0.3 * s), (px - 0.8 * s, py - 1.6 * s), (px + 0.2 * s, py - 0.7 * s)]), rgb("#ffffff"))
    elif art == "bars":                                                    # signal bars climbing
        n = 5
        for i in range(n):
            h_ = H * (0.06 + 0.045 * i)
            x0 = W * 0.18 + i * W * 0.135
            cv.put(cv.rect(x0, H * 0.94 - h_, x0 + W * 0.10, H * 0.94, r=0.08), rgb(acc), 0.95)
    elif art == "bun":                                                     # a burger in three stacked shapes
        cx, cy, r = W * 0.5, H * 0.80, W * 0.34
        cv.put(_glow(_ellipse(cv, cx, cy, r * 1.2, r * 0.9), cv, 0.6), rgb(acc), 0.35)
        cv.put(_ellipse(cv, cx, cy - r * 0.38, r, r * 0.55), rgb("#c98a2e"))
        cv.put(cv.rect(cx - r * 1.02, cy - r * 0.16, cx + r * 1.02, cy + r * 0.10, r=r * 0.08), rgb("#4a2a12"))
        cv.put(cv.rect(cx - r * 1.05, cy - r * 0.22, cx + r * 1.05, cy - r * 0.12, r=r * 0.04), rgb("#e8b21c"))
        cv.put(cv.rect(cx - r * 0.95, cy + r * 0.10, cx + r * 0.95, cy + r * 0.34, r=r * 0.12), rgb("#b8792a"))
        for i in range(14):
            sx, sy = cx + rng.uniform(-0.7, 0.7) * r, cy - r * rng.uniform(0.45, 0.78)
            cv.put(_ellipse(cv, sx, sy, 0.05, 0.03), rgb("#fff1c8"))
    elif art == "spot":                                                    # a spotlight cone onto a stage line, stars
        cone = _poly(cv, [(W * 0.47, 0.0), (W * 0.53, 0.0), (W * 0.70, H), (W * 0.30, H)])
        cv.put(_glow(cone, cv, 0.5), rgb(acc), 0.35)
        for i in range(40):
            x, y = rng.uniform(0, W), rng.uniform(0, H)
            cv.put(_ellipse(cv, x, y, 0.03, 0.03), rgb("#ffffff"), rng.uniform(0.2, 0.7))
    elif art == "horizon":                                                 # sea, a low sun, a ship's silhouette
        cv.put(_glow(_ellipse(cv, W * 0.68, H * 0.62, H * 0.16, H * 0.16), cv, 0.8), rgb(acc), 0.9)
        cv.put(_ellipse(cv, W * 0.68, H * 0.62, H * 0.12, H * 0.12), rgb("#ffe7c0"))
        sea = ((cv.y > H * 0.64)).astype(np.float32)
        cv.put(sea, rgb("#061a33"))
        for i in range(30):
            y = H * 0.66 + i * H * 0.011
            cv.put(cv.rect(W * 0.60 - i * 0.04, y, W * 0.76 + i * 0.04, y + 0.03), rgb(acc), 0.35 * (1 - i / 30))
        cv.put(_poly(cv, [(W * 0.78, H * 0.64), (W * 0.97, H * 0.64), (W * 0.95, H * 0.61), (W * 0.80, H * 0.61)]), rgb("#020608"))
        cv.put(cv.rect(W * 0.83, H * 0.575, W * 0.92, H * 0.61), rgb("#020608"))
        cv.put(cv.rect(W * 0.86, H * 0.55, W * 0.89, H * 0.575), rgb("#020608"))
    elif art == "dial":                                                    # a watch face
        cx, cy, r = W * 0.76, H * 0.5, H * 0.34
        cv.put(_ellipse(cv, cx, cy, r * 1.08, r * 1.08), rgb("#8a9098"))
        cv.put(_ellipse(cv, cx, cy, r, r), rgb("#101216"))
        for i in range(12):
            a = i * math.pi / 6
            x0, y0 = cx + math.sin(a) * r * 0.78, cy - math.cos(a) * r * 0.78
            x1, y1 = cx + math.sin(a) * r * 0.92, cy - math.cos(a) * r * 0.92
            cv.put(cv.draw(lambda d, k, x0=x0, y0=y0, x1=x1, y1=y1: d.line([(x0 * k, y0 * k), (x1 * k, y1 * k)], fill=255,
                                                                          width=int(0.10 * k))), rgb(ink))
        for a, ln, w in ((math.radians(-60), 0.55, 0.12), (math.radians(110), 0.80, 0.07)):
            cv.put(cv.draw(lambda d, k, a=a, ln=ln, w=w: d.line([(cx * k, cy * k), ((cx + math.sin(a) * r * ln) * k,
                                                                                  (cy - math.cos(a) * r * ln) * k)], fill=255,
                                                              width=int(w * k))), rgb(acc))
    elif art == "stripes":                                                 # bold diagonal bands, fashion
        for i in range(7):
            x0 = W * 0.55 + i * 0.9
            cv.put(_poly(cv, [(x0, H), (x0 + 0.45, H), (x0 + 0.45 + H * 0.5, 0), (x0 + H * 0.5, 0)]),
                   rgb(acc if i % 2 else "#8c84a0"), 0.75)
    elif art == "bubbles":
        for i in range(70):
            r = rng.uniform(0.04, 0.32)
            x, y = rng.uniform(W * 0.45, W * 0.98), rng.uniform(0.0, H)
            cv.put(_ellipse(cv, x, y, r, r, outline=max(0.02, r * 0.18)), rgb(acc), rng.uniform(0.5, 1.0))
    elif art == "skyline":                                                 # towers against a dusk band
        x = W * 0.48
        while x < W:
            w = rng.uniform(0.35, 0.9)
            h = rng.uniform(0.18, 0.62) * H
            cv.put(cv.rect(x, H - h, x + w, H), rgb("#07060f"))
            for j in range(int(h / 0.32)):
                for i in range(max(1, int(w / 0.22))):
                    if rng.random() < 0.45:
                        wx, wy = x + 0.07 + i * 0.22, H - h + 0.12 + j * 0.32
                        cv.put(cv.rect(wx, wy, wx + 0.09, wy + 0.13), rgb(acc), rng.uniform(0.4, 0.9))
            x += w + rng.uniform(0.02, 0.12)


def draw_slide(key, S, k=128):
    """A slide at its screen's aspect: (H, W, 3) sRGB emissive colour (the LED's light). k px per metre."""
    W, H = S["size_m"]
    rng = np.random.default_rng(sum(map(ord, key)) * 31)
    cv = sg.Canvas(W, H, k, rgb("#000000"))
    kind = S["kind"]
    if kind == "takeover":
        _grad(cv, "#000000", "#08080a", 90)
        m, _w, _s = cv.text(S["lines"][0], "mt_heavy", H * 0.15, W / 2, H * 0.30, cond=0.92, track=0.03, max_w=W * 0.86)
        cv.put(m, rgb("#ffffff"))
        m, _w, _s = cv.text("·  " + S["lines"][1] + "  ·", "mt_semi", H * 0.075, W / 2, H * 0.50, track=0.25, max_w=W * 0.6)
        cv.put(m, rgb("#d6d6d6"))
        S["clock_rect"] = [round(0.36, 4), round(0.60, 4), round(0.64, 4), round(0.82, 4)]     # u0, v0 (from top), u1, v1 of the clock box
        x0, y0, x1, y1 = W * 0.36, H * 0.60, W * 0.64, H * 0.82
        cv.put(cv.rect(x0, y0, x1, y1, r=0.08, outline=0.05), rgb("#bdbdbd"))
        m, _w, _s = cv.text("VLTR", "mt_heavy", H * 0.045, W * 0.935, H * 0.92, cond=0.9, align="r")
        cv.put(m, rgb("#6e1018"))                                                              # small oxblood mark, a corner
        cv.put(cv.rect(W * 0.94, H * 0.895, W * 0.955, H * 0.945, r=0.01), rgb("#6e1018"))
    elif kind == "state":
        _grad(cv, "#000000", "#050505", 90)
        m, _w, _s = cv.text(S["lines"][0], "mt_semi", H * 0.08, W / 2, H * 0.5, track=0.30, max_w=W * 0.5)
        cv.put(m, rgb("#5a5a5a" if "NO" in S["lines"][0] else "#8a8a8a"))
    elif kind == "ipx":
        _grad(cv, "#000000", "#0a0a0c", 90)
        hh = min(H * 0.30, W * 0.18)
        sg.put_ipx(cv, W / 2, H * 0.43, hh, rgb("#ffffff"))
        m, _w, _s = cv.text(S["lines"][0], "mt_semi", hh * 0.20, W / 2, H * 0.43 + hh * 0.85, track=0.45, max_w=W * 0.6)
        cv.put(m, rgb("#cfcfcf"))
    else:
        bg0, bg1, ink, acc = S["palette"]
        _grad(cv, bg0, bg1, 60 if W >= H else 100, 1.3)
        _motif(cv, S, rng)
        L = S["lines"]
        if W < H:                                                           # vertical: lines stacked at the top
            caps = [W * 0.20, W * 0.20, W * 0.085, W * 0.085]
            ys = [H * 0.10, H * 0.20, H * 0.33, H * 0.38]
            for i, t in enumerate(L):
                f = "mt_heavy" if i < 2 else "mt_semi"
                m, _w, _s = cv.text(t, f, caps[i], W / 2, ys[i], cond=0.9 if i < 2 else 1.0, max_w=W * 0.86)
                cv.put(m, rgb(ink if i < 2 else acc))
        else:
            left = S.get("art") in ("bottle", "dial", "stripes", "bubbles", "skyline", "horizon", "contrail")
            cx, al, mw = (W * 0.07, "l", W * 0.52) if left else (W / 2, "c", W * 0.86)
            if key == "E3_Alderway":
                m, _w, _s = cv.text(L[0], "mt_serif", H * 0.055, W / 2, H * 0.16, track=0.08, max_w=W * 0.8)
                cv.put(m, rgb(acc))
                m, _w, _s = cv.text(L[1], "mt_heavy", H * 0.20, W / 2, H * 0.44, cond=0.88, track=0.04, max_w=W * 0.86)
                cv.put(_glow(m, cv, 0.12), rgb(acc), 0.6)
                cv.put(m, rgb(ink))
                m, _w, _s = cv.text(L[2], "mt_script", H * 0.09, W / 2, H * 0.70, max_w=W * 0.6)
                cv.put(m, rgb(acc))
            else:
                m, _w, _s = cv.text(L[0], "mt_heavy" if key != "E1_Orbelle" else "mt_serif", H * 0.14, cx, H * 0.40, cond=0.92,
                                    track=0.06, max_w=mw, align=al)
                cv.put(m, rgb(ink))
                if len(L) > 1:
                    f = "mt_script" if key in ("E1_Orbelle",) else "mt_italic" if key in ("N1_TamsinGray", "N1_Quillon") else "mt_semi"
                    m, _w, _s = cv.text(L[1], f, H * (0.085 if f == "mt_script" else 0.06), cx, H * 0.58, track=0.02,
                                        max_w=mw, align=al)
                    cv.put(m, rgb(acc))
    return np.clip(cv.c, 0, 1)


def build_screens(log=print):
    names.check_english()
    pages = {p: np.zeros((ATLAS, ATLAS, 3), np.float32) for p in ("A", "B")}
    cells = {"A": {}, "B": {}}
    for key, S in names.SLIDES.items():
        p, x, y = LAYOUT[key]
        W, H = S["size_m"]
        w, h = V_CELL if H > W else H_CELL
        k = 1.25 * max(w / W, h / H)                                     # draw a little over the cell's density, then squeeze
        img = draw_slide(key, S, k)
        im = Image.fromarray((img * 255 + 0.5).astype(np.uint8)).resize((w, h), Image.LANCZOS)
        pages[p][y:y + h, x:x + w] = np.asarray(im, np.float32) / 255.0
        c = {"px": [x, y, w, h], "uv": [round(x / ATLAS, 6), round(1 - (y + h) / ATLAS, 6), round((x + w) / ATLAS, 6), round(1 - y / ATLAS, 6)],
             "screens": S["screen"], "screen_m": list(S["size_m"]), "kind": S["kind"], "text": S["lines"], "note": S.get("note", "")}
        if S.get("clock_rect"):
            c["clock_rect_in_slide"] = S["clock_rect"]
        cells[p][key] = c
    out = []
    for p, arr in pages.items():
        sname = "MT_Screens_" + p
        d = paths.ensure(paths.texture_set(sname))
        Image.fromarray((arr * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, "T_%s_E.png" % sname), optimize=True)
        info = dict(kind="screen_atlas", resolution=[ATLAS, ATLAS], files={"E": "T_%s_E.png" % sname},
                    convention={"E": "sRGB; the slide's light at strength 1 (x 450 nits hero, 300 others in M_MI_Screen)",
                                "compression": "BC1 sRGB with mips"},
                    cells=cells[p], albedo_mean=[0.012, 0.012, 0.014], roughness_mean=0.6, metallic_mean=0.0,
                    master="M_MI_Screen (opaque, black base, roughness 0.6, crossfade of two cells, LED mask 8 to 20 m)",
                    note="Midtown LED screen slides (assets/_midtown_names.py SLIDES), English only, invented names; IPX is the "
                         "owner's mark. Slides are squeezed into their cells: the screen's 0..1 UVs map the cell back unstretched.")
        with open(os.path.join(d, "set.json"), "w") as f:
            json.dump(info, f, indent=1, sort_keys=True)
        log("screen atlas %s: %d slides" % (sname, len(cells[p])))
        out.append(sname)
    return out, cells


def build_ticker(log=print):
    k = 256 / 0.8                                                          # 0.8 m band, 256 px tall
    text = "     ·     ".join(names.TICKER) + "     ·     "
    m, (i0, i1), top, base = sg.text_mask(text, "mt_bold", cap_px=150)
    w = i1 - i0
    strip = np.zeros((256, 4096, 3), np.float32)
    im = Image.fromarray((m[:, i0:i1] * 255).astype(np.uint8)).resize((4096, m.shape[0]), Image.LANCZOS)
    mm = np.asarray(im, np.float32) / 255.0
    oy = int(128 - (top + base) / 2)
    hh = min(mm.shape[0], 256 - max(0, oy))
    strip[max(0, oy):max(0, oy) + hh] = mm[max(0, -oy):max(0, -oy) + hh, :, None] * rgb("#ffd890")
    d = paths.ensure(paths.texture_set("MT_Ticker"))
    Image.fromarray((strip * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, "T_MT_Ticker_E.png"), optimize=True)
    length_m = round(w * 0.8 / 256, 3)                                     # the text at its own shape on a 0.8 m band
    info = dict(kind="ticker", resolution=[4096, 256], files={"E": "T_MT_Ticker_E.png"}, headlines=names.TICKER,
                albedo_mean=[0.012, 0.012, 0.014], roughness_mean=0.6, metallic_mean=0.0,
                strip_length_m=length_m, band_m=[24.0, 0.8], u_per_band=round(24.0 / length_m, 4), pan_m_per_s=0.35, wrap="u",
                note="the three headlines with dots, %d px of text squeezed into 4096 px: the band's material maps u 0..u_per_band "
                     "across the 24 m band (which restores the letters' shape) and pans u by 0.35 / strip_length_m per second" % w)
    with open(os.path.join(d, "set.json"), "w") as f:
        json.dump(info, f, indent=1, sort_keys=True)
    log("ticker: %d px of text squeezed to 4096" % w)
    return "MT_Ticker"


def build_digits(log=print):
    arr = np.zeros((64, 512, 3), np.float32)
    for i, ch in enumerate(names.DIGITS):
        if not ch.strip():
            continue
        m, (i0, i1), top, base = sg.text_mask(ch, "mt_semi", cap_px=38, cond=0.80)
        g = m[:, i0:i1][:, :30]
        oy = int(32 - (top + base) / 2)
        ox = i * 32 + (32 - g.shape[1]) // 2
        h = min(g.shape[0], 64 - max(0, oy))
        w = min(g.shape[1], 32)
        arr[max(0, oy):max(0, oy) + h, ox:ox + w] = np.maximum(arr[max(0, oy):max(0, oy) + h, ox:ox + w], g[max(0, -oy):max(0, -oy) + h, :w, None])
    d = paths.ensure(paths.texture_set("MT_Digits"))
    Image.fromarray((arr * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, "T_MT_Digits_E.png"), optimize=True)
    json.dump(dict(kind="digits", albedo_mean=[0.012, 0.012, 0.014], roughness_mean=0.6, metallic_mean=0.0, resolution=[512, 64], files={"E": "T_MT_Digits_E.png"}, cells=names.DIGITS, cell_px=[32, 64],
                   note="the countdown clock M:SS composited into G1_Takeover's clock_rect_in_slide (white, x 450 nits)"),
              open(os.path.join(d, "set.json"), "w"), indent=1, sort_keys=True)
    log("digits: %d glyphs" % sum(1 for c in names.DIGITS if c.strip()))
    return "MT_Digits"


def build_ledmask(log=print):
    """One LED module pixel: three vertical sub-pixel bars (R, G, B) on black, soft edges; tiles."""
    n = 64
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) + 0.5
    out = np.zeros((n, n, 3), np.float32)
    for c, cx in enumerate((n * 0.22, n * 0.5, n * 0.78)):
        bar = np.clip(1.0 - np.abs(x - cx) / (n * 0.10), 0, 1) * np.clip(1.0 - np.abs(y - n * 0.5) / (n * 0.38), 0, 1)
        out[..., c] = np.clip(bar * 1.6, 0, 1)
    d = paths.ensure(paths.texture_set("MT_LEDMask"))
    Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, "T_MT_LEDMask_M.png"))
    json.dump(dict(kind="mask", albedo_mean=[0.5, 0.5, 0.5], roughness_mean=0.6, metallic_mean=0.0, resolution=[n, n], files={"M": "T_MT_LEDMask_M.png"}, convention={"M": "linear, tiling"},
                   note="multiplies the screen emissive near the camera; faded to its mean between 8 and 20 m (no moire at render "
                        "scale 0.5). Tile: one LED pitch, 16 mm on the hero walls"), open(os.path.join(d, "set.json"), "w"), indent=1,
              sort_keys=True)
    log("LED mask %d px" % n)
    return "MT_LEDMask"


# ================================================================================================== printed faces

def cell_px(F):
    k = DENS[F["kind"]]
    a4 = lambda v: int(4 * round(v * k / 4.0))
    return a4(F["w"]), a4(F["h"])


def pack(sizes):
    """Shelf packing, tallest first, into one ATLAS x ATLAS page. Returns {key: (x, y)} from the top-left."""
    order = sorted(sizes, key=lambda k: (-sizes[k][1], -sizes[k][0], k))
    out, x, y, shelf = {}, 0, 0, 0
    for k in order:
        w, h = sizes[k][0] + 2 * PAD, sizes[k][1] + 2 * PAD
        if x + w > ATLAS:
            x, y, shelf = 0, y + shelf, 0
        if y + h > ATLAS:
            raise ValueError("Sign_MT_Atlas1 is full at %s" % k)
        out[k] = (x + PAD, y + PAD)
        x += w
        shelf = max(shelf, h)
    return out


def draw_face(key, F, rng):
    k = DENS[F["kind"]]
    W, H = F["w"], F["h"]
    cv = sg.Canvas(W, H, k, rgb(F["field"]))
    ink = rgb(F["ink"])
    sub = rgb(F.get("sub", F["ink"]))
    font = "mt_serif" if F.get("font") == "serif" else "mt_heavy"
    L = F["lines"]
    letters = cv.blank()
    kind = F["kind"]
    if kind == "billboard":                                              # C1: a big printed lightbox face
        _grad(cv, "#f6f2ea", "#e2d8c4", 100)
        cv.put(cv.rect(W * 0.03, H * 0.06, W * 0.97, H * 0.94, r=0.05, outline=0.04), rgb("#b89a5a"))
        m, _w, _s = cv.text(L[0], "mt_serif", H * 0.17, W / 2, H * 0.38, track=0.05, max_w=W * 0.86)
        cv.put(m, ink)
        letters = np.maximum(letters, m)
        m, _w, _s = cv.text(L[1], "mt_italic", H * 0.07, W / 2, H * 0.62, track=0.02, max_w=W * 0.8)
        cv.put(m, sub)
        letters = np.maximum(letters, m)
        for i in range(30):                                              # a few gold ornament dots along a rule
            cv.put(_ellipse(cv, W * 0.30 + i * W * 0.4 / 29, H * 0.51, 0.03, 0.03), rgb("#b89a5a"))
        rough = 0.30 + sg.weather_face(cv, rng, 0.8, top_fade=0.12, bugs=int(20 * W))
    elif kind == "band":
        fw = 0.06 * H
        m_ = cv.blank()
        if len(L) == 1:
            m, _w, _s = cv.text(L[0], font, H * 0.42, W / 2, H * 0.50, cond=0.9, track=0.04, max_w=W * 0.9)
            m_ = m
            cv.put(m, ink)
        else:
            m, _w, _s = cv.text(L[0], font, H * 0.34, W / 2, H * 0.36, cond=0.9, track=0.04, max_w=W * 0.9)
            cv.put(m, ink)
            m2, _w, _s = cv.text(L[1], "mt_semi", H * 0.14, W / 2, H * 0.72, track=0.2, max_w=W * 0.8)
            cv.put(m2, sub)
            m_ = np.maximum(m, m2)
        letters = m_
        fr = ((cv.x < fw) | (cv.x > W - fw) | (cv.y < fw) | (cv.y > H - fw)).astype(np.float32)
        cv.put(fr, rgb("#1b1c20"))
        rough = 0.32 + sg.weather_face(cv, rng, 0.9, top_fade=0.15)
    elif kind == "plaque":
        if F.get("carved"):                                              # cast stone: incised letters, shadowed upper edge
            n = sg.vnoise(rng, cv.H, cv.W, cv.k * 0.04)
            cv.c = cv.c * (0.88 + 0.12 * n[..., None])
            m, _w, _s = cv.text(L[0], "mt_serif", H * 0.46, W / 2, H * 0.52, track=0.12, max_w=W * 0.9)
            sh = np.roll(m, int(0.012 * k), axis=0)
            cv.put(np.clip(sh - m * 0.3, 0, 1), rgb("#2a241c"), 0.55)
            cv.put(m, ink, 0.8)
            cv.put(cv.rect(0.05, 0.05, W - 0.05, H - 0.05, outline=0.012), rgb("#7a705e"), 0.8)
            rough = 0.75 + 0.2 * sg.weather_face(cv, rng, 1.2, top_fade=0.1, grime=0.5)
        else:                                                            # a painted board on the scaffold
            cv.put(cv.rect(0.05, 0.05, W - 0.05, H - 0.05, outline=0.03), ink)
            ys, caps, fonts = (H * 0.30, H * 0.56, H * 0.80), (H * 0.20, H * 0.15, H * 0.055), ("mt_heavy", "mt_heavy", "mt_semi")
            for i, t in enumerate(L):
                m, _w, _s = cv.text(t, fonts[i], caps[i], W / 2, ys[i], cond=0.92, track=0.04, max_w=W * 0.86)
                cv.put(m, ink)
                letters = np.maximum(letters, m)
            rough = 0.55 + sg.weather_face(cv, rng, 1.3, top_fade=0.1, grime=0.5)
    else:                                                                # small labels
        cv.put(cv.rect(0.008, 0.008, W - 0.008, H - 0.008, r=0.01, outline=0.006), ink)
        m, _w, _s = cv.text(L[0], "mt_heavy", H * 0.24, W / 2, H * 0.34, cond=0.9, max_w=W * 0.86)
        cv.put(m, ink)
        m2, _w, _s = cv.text(L[1], "mt_bold", H * 0.13, W / 2, H * 0.70, max_w=W * 0.86)
        cv.put(m2, ink)
        letters = np.maximum(m, m2)
        rough = 0.45 + sg.weather_face(cv, rng, 1.0, top_fade=0.1, grime=0.3)
    E = None
    if F.get("lit"):
        v = cv.y / H
        prof = 0.70 + 0.30 * np.exp(-((v - 0.5) / 0.45) ** 2)
        E = sg.to_lin(np.clip(cv.c, 0, 1)) * prof[..., None]
    return np.clip(cv.c, 0, 1), np.clip(rough, 0.02, 1), E


def build_signs(seed=0, log=print):
    names.check_english()
    sizes = {k: cell_px(F) for k, F in names.FACES.items()}
    where = pack(sizes)
    BC = np.ones((ATLAS, ATLAS, 3), np.float32) * rgb("#2a2a2c")
    RO = np.full((ATLAS, ATLAS), 0.6, np.float32)
    EM = np.zeros((ATLAS, ATLAS, 3), np.float32)
    cells = {}
    sname = "Sign_MT_Atlas1"
    for key, F in names.FACES.items():
        rng = np.random.default_rng(sum(map(ord, key)) * 7919 + seed)
        c, r, e = draw_face(key, F, rng)
        x, y = where[key]
        w, h = sizes[key]
        rs = lambda a: np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS), np.float32) / 255.0
        BC[y:y + h, x:x + w] = rs(c)
        RO[y:y + h, x:x + w] = rs(r)
        if e is not None:
            EM[y:y + h, x:x + w] = rs(sg.to_srgb(e))
        for arr in (BC, RO, EM):                                         # bleed the edges into the padding
            arr[y - PAD:y, x:x + w] = arr[y:y + 1, x:x + w]
            arr[y + h:y + h + PAD, x:x + w] = arr[y + h - 1:y + h, x:x + w]
            arr[y - PAD:y + h + PAD, x - PAD:x] = arr[y - PAD:y + h + PAD, x:x + 1]
            arr[y - PAD:y + h + PAD, x + w:x + w + PAD] = arr[y - PAD:y + h + PAD, x + w - 1:x + w]
        cells[key] = {"atlas": sname, "px": [x, y, w, h],
                      "uv": [round(x / ATLAS, 6), round(1 - (y + h) / ATLAS, 6), round((x + w) / ATLAS, 6), round(1 - y / ATLAS, 6)],
                      "face_m": [F["w"], F["h"]], "px_per_m": DENS[F["kind"]], "kind": F["kind"], "lit": bool(F.get("lit")),
                      "carrier": F["carrier"], "text": F["lines"], "where": F["where"]}
    d = paths.ensure(paths.texture_set(sname))
    Image.fromarray((BC * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, "T_%s_BC.png" % sname), optimize=True)
    orm = np.stack([np.ones_like(RO), RO, np.zeros_like(RO)], -1)
    Image.fromarray((orm * 255).astype(np.uint8), "RGB").resize((ATLAS // 2, ATLAS // 2), Image.BILINEAR) \
        .save(os.path.join(d, "T_%s_ORM.png" % sname), optimize=True)
    Image.fromarray((EM * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, "T_%s_E.png" % sname), optimize=True)
    used = sum(v["px"][2] * v["px"][3] for v in cells.values()) / float(ATLAS * ATLAS)
    info = dict(kind="sign_atlas", resolution=[ATLAS, ATLAS],
                files={"BC": "T_%s_BC.png" % sname, "ORM": "T_%s_ORM.png" % sname, "E": "T_%s_E.png" % sname},
                convention={"BC": "sRGB", "ORM": "linear AO, roughness, metallic (half size)",
                            "E": "sRGB, night value at strength 1 (x 200 nits for lightboxes, midtown.md 11.2); black where unlit"},
                cells=cells, fill=round(used, 3), albedo_mean=[round(float(v), 4) for v in sg.to_lin(BC).reshape(-1, 3).mean(0)],
                roughness_mean=round(float(RO.mean()), 3), metallic_mean=0.0,
                note="Midtown printed faces, English only, invented names (assets/_midtown_names.py FACES). A placed carrier's MI "
                     "maps its 0..1 face UVs to the cell: uv' = uv * (u1 - u0, v1 - v0) + (u0, v0).")
    with open(os.path.join(d, "set.json"), "w") as f:
        json.dump(info, f, indent=1, sort_keys=True)
    log("sign atlas %s: %d faces, %.0f %% of the page used" % (sname, len(cells), used * 100))
    return sname, cells


def build_all(seed=0, log=print):
    sets, scells = build_screens(log)
    sets += [build_ticker(log), build_digits(log), build_ledmask(log)]
    s, fcells = build_signs(seed, log)
    sets.append(s)
    return sets, scells, fcells


def preview_sheet(path, max_px=1280):
    """Three atlas pages side by side (screens A, B, signs), downscaled, for review."""
    files = [os.path.join(paths.texture_set("MT_Screens_A"), "T_MT_Screens_A_E.png"),
             os.path.join(paths.texture_set("MT_Screens_B"), "T_MT_Screens_B_E.png"),
             os.path.join(paths.texture_set("Sign_MT_Atlas1"), "T_Sign_MT_Atlas1_BC.png")]
    W = max_px // 3
    row = Image.new("RGB", (W * 3, W + 40), (16, 16, 16))
    for i, f in enumerate(files):
        row.paste(Image.open(f).convert("RGB").resize((W - 4, W - 4), Image.LANCZOS), (i * W + 2, 2))
    tk = Image.open(os.path.join(paths.texture_set("MT_Ticker"), "T_MT_Ticker_E.png")).convert("RGB").resize((W * 3 - 4, 36), Image.LANCZOS)
    row.paste(tk, (2, W + 2))
    from mi import render
    return render.save_jpeg(row, path, 300)


if __name__ == "__main__":
    print(build_all())
