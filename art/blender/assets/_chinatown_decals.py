"""Canal Street decals: the graffiti tags, the alley stencil and the near-ground wear pass (chinatown_art.md 6).

    venv/bin/python art/blender/assets/_chinatown_decals.py      # draws art/out/textures/CT_Decals/ (no Blender)
    (the meshes are built by `build.py build chinatown`, chinatown.build -> build_decals)

One 2K page, T_CT_Decals (BC with the paint's alpha, N, ORM), 256 to 640 px per metre, and a quad per cell, SM_Decal_CT_<Name>, its
UVs on its own cell, so one material (M_CT_Decals) serves all of them. In Unreal the same page is a decal-domain material (DBuffer,
normal and roughness blended) on a decal actor of the quad's size; the quads are the preview's stand-in and the placement list.

    SM_Decal_CT_Graffiti_{Vultures, Vltr, Rule, Inc}   1.6 x 0.6 m: invented tags only (the names are the level's `graffiti` rows and
                                                       are on the approved list: tools/names, DECAL_TEXT). Spray paint with a dark
                                                       outline, overspray, drips and flaking.
    SM_Decal_CT_Stencil_Mott                           1.4 x 0.4 m: white spray stencil "MOTT ST" and an arrow, with the stencil bridges.
    SM_Decal_CT_Wear_Grime_{A, B}                      3.0 x 1.0 m: the dirt band at a wall's foot (kerb splash, damp, hands, bins).
    SM_Decal_CT_Wear_Scuffs                            1.2 x 0.9 m: kicks, bin scrapes and trolley marks at door height.
    SM_Decal_CT_Wear_Streaks                           0.9 x 2.4 m: rain and rust runs from a sill or a bracket.
Coordinates and offsets: a quad lies in the XZ plane, facing -Y like the wall modules, pivot at its bottom-left corner; placed 4 mm
in front of its wall.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from mi import paths  # noqa: E402

SET = "CT_Decals"
SLOT = "M_CT_Decals"
FONTS = os.path.join(HERE, "..", "fonts")
PAGE = 2048
# name: (width m, height m, px per metre)
CELLS = {
    "Graffiti_Vultures": (1.6, 0.6, 640), "Graffiti_Vltr": (1.6, 0.6, 640), "Graffiti_Rule": (1.6, 0.6, 640), "Graffiti_Inc": (1.6, 0.6, 640),
    "Stencil_Mott": (1.4, 0.4, 640), "Wear_Grime_A": (3.0, 1.0, 320), "Wear_Grime_B": (3.0, 1.0, 320),
    "Wear_Scuffs": (1.2, 0.9, 400), "Wear_Streaks": (0.9, 2.4, 300),
}
TEXT = {"Graffiti_Vultures": "VULTURES", "Graffiti_Vltr": "VLTR", "Graffiti_Rule": "RULE", "Graffiti_Inc": "INC", "Stencil_Mott": "MOTT ST"}
OXBLOOD, GOLD, WHITE = (0.42, 0.045, 0.06), (0.78, 0.55, 0.13), (0.80, 0.80, 0.76)
INK = {"Graffiti_Vultures": (OXBLOOD, (0.03, 0.02, 0.02), "Anton-Regular.ttf"), "Graffiti_Vltr": (OXBLOOD, (0.03, 0.02, 0.02), "PassionOne-Bold.ttf"),
       "Graffiti_Rule": (GOLD, (0.05, 0.03, 0.02), "Anton-Regular.ttf"), "Graffiti_Inc": (GOLD, (0.05, 0.03, 0.02), "PassionOne-Bold.ttf")}


def layout():
    """Shelf-pack the cells on the page: {name: (x, y, w_px, h_px)}."""
    out, x, y, row = {}, 0, 0, 0
    for k, (w, h, ppm) in CELLS.items():
        pw, ph = int(round(w * ppm)), int(round(h * ppm))
        if x + pw > PAGE:
            x, y, row = 0, y + row, 0
        out[k] = (x, y, pw, ph)
        x += pw
        row = max(row, ph)
    assert y + row <= PAGE, "decal page overflow"
    return out


def _noise(rng, shape, scale):
    h, w = shape
    g = (max(2, h // scale + 2), max(2, w // scale + 2))
    a = rng.random(g).astype(np.float32)
    im = Image.fromarray((a * 255).astype(np.uint8)).resize((w + 2 * scale, h + 2 * scale), Image.BICUBIC)
    return np.asarray(im, np.float32)[scale:scale + h, scale:scale + w] / 255.0


def _text_mask(text, font_file, size, w, h, rng, jitter=True, bold=0):
    """L mask (0..1) of the text fitted to the cell, one rotated character at a time."""
    f = ImageFont.truetype(os.path.join(FONTS, font_file), size)
    ims = []
    for ch in text:
        if ch == " ":
            ims.append(Image.new("L", (size // 3, size), 0))
            continue
        im = Image.new("L", (size * 2, size * 2), 0)
        ImageDraw.Draw(im).text((size // 2, size // 4), ch, font=f, fill=255)
        bb = im.getbbox()
        im = im.crop(bb)
        if jitter:
            im = im.rotate(rng.uniform(-7, 7), expand=True, resample=Image.BICUBIC)
        ims.append(im)
    gap = max(2, size // 22)
    tw = sum(i.width for i in ims) + gap * (len(ims) - 1)
    th = max(i.height for i in ims)
    canvas = Image.new("L", (tw, th), 0)
    x = 0
    for im in ims:
        y = (th - im.height) // 2 + (int(rng.integers(-size // 14, size // 14 + 1)) if jitter else 0)
        canvas.paste(im, (x, max(0, y)), im)
        x += im.width + gap
    sc = min((w * 0.88) / tw, (h * 0.80) / th)
    canvas = canvas.resize((max(1, int(tw * sc)), max(1, int(th * sc))), Image.LANCZOS)
    out = Image.new("L", (w, h), 0)
    out.paste(canvas, ((w - canvas.width) // 2, (h - canvas.height) // 2 + int(h * 0.03)))
    return out


def _warp(img, rng, amp, scale):
    """The image sampled through a smooth random displacement field: ragged, hand-sprayed edges instead of font outlines."""
    h, w = img.shape
    dx = (_noise(rng, (h, w), scale) - 0.5) * 2 * amp
    dy = (_noise(rng, (h, w), scale) - 0.5) * 2 * amp
    yy, xx = np.mgrid[0:h, 0:w]
    sx = np.clip((xx + dx).round().astype(int), 0, w - 1)
    sy = np.clip((yy + dy).round().astype(int), 0, h - 1)
    return img[sy, sx]


def _blur(a, r):
    return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def _brick(h, w, ppm, rng):
    """(relief 0..1, mortar mask 0..1) of a running-bond wall at the cell's scale: 215 x 65 mm bricks, 10 mm joints."""
    bh, bw, mj = int(round(0.075 * ppm)), int(round(0.225 * ppm)), max(2, int(round(0.010 * ppm)))
    yy, xx = np.mgrid[0:h, 0:w]
    row = yy // bh
    xo = xx + (row % 2) * (bw // 2)
    ly, lx = yy % bh, xo % bw
    mortar = ((ly < mj) | (lx < mj)).astype(np.float32)
    edge = np.minimum.reduce([ly, bh - 1 - ly, lx, bw - 1 - lx]).astype(np.float32)
    relief = np.clip(edge / (mj * 2.5), 0, 1) * (1 - mortar)
    brick_id = (row * 97 + xo // bw * 31) % 251
    per = 0.88 + 0.12 * (brick_id / 251.0)
    return relief, mortar, per.astype(np.float32)


def graffiti(name, rng):
    """A spray tag that reads as paint on brick: ragged hand edges, a lighter core with a softer rim, a thin dark shadow outline and a bright
    highlight, a fine overspray mist, drips with beads, a faded and flaked top coat, a roller-buffed patch of an older cover-up behind it and a
    ghost of another tag, and the brick relief breaking the paint at the joints (the normal carries the bricks)."""
    ppm = CELLS[name][2]
    w, h = [int(round(v * CELLS[name][2])) for v in CELLS[name][:2]]
    ink, edge, font = INK[name]
    m = _text_mask(TEXT[name], font, 300, int(w * 0.80), int(h * 0.84), rng)             # the tag's mask at 80 % of the cell
    full = Image.new("L", (w, h), 0)
    full.paste(m, ((w - m.width) // 2, (h - m.height) // 2))
    base = np.asarray(full, np.float32) / 255.0
    base = _warp(base, rng, 3.2, 14)                                                    # hand-wobbled edges
    base = _warp(base, rng, 1.1, 4)
    core = _blur(base, 2.4)
    mask = np.clip((core - 0.30) * 2.6, 0, 1)                                           # a hard-ish spray edge
    rim = np.clip(_blur(base, 5.0) - mask * 0.9, 0, 1)                                    # the softer spray at the stroke's rim
    # the stroke's density: heavier in the middle of a line (distance from the edge ~ a heavier blur), lighter at the rim
    dens = np.clip(_blur(base, 7.0) * 1.35, 0.55, 1.0)
    # overspray mist: random fine dots, thinning with distance from the letters
    halo = _blur(base, 22.0)
    mist = (rng.random((h, w)) < (halo * 0.20)).astype(np.float32)
    mist = _blur(mist, 0.8) * 1.6 * (1 - mask)
    # drop shadow outline: the dark second pass, offset down-right and a little heavier
    sh = np.roll(np.roll(base, int(0.012 * ppm), axis=0), int(0.010 * ppm), axis=1)
    shadow = np.clip(_blur(_warp(sh, rng, 2.4, 12), 2.0) * 1.5 - 0.3, 0, 1) * (1 - mask)
    # the highlight: a thin pale stroke along the upper left edge of the letters
    up = np.roll(np.roll(base, -int(0.006 * ppm), axis=0), -int(0.005 * ppm), axis=1)
    hl = np.clip(mask - np.clip(_blur(up, 1.6) * 1.4 - 0.2, 0, 1), 0, 1) * (rng.random() * 0 + 1.0)
    hl *= (_noise(rng, (h, w), 40) > 0.38)
    # drips: from the lowest filled pixel of a good share of the columns, uneven length and width, with a bead at the end
    drips = np.zeros((h, w), np.float32)
    cols = np.where(mask.max(axis=0) > 0.6)[0]
    for x in rng.choice(cols, size=min(26, len(cols)), replace=False):
        ys = np.where(mask[:, x] > 0.6)[0]
        y0 = int(ys.max())
        ln = int(rng.integers(int(0.015 * ppm), int(0.22 * ppm)))
        wd = int(rng.integers(2, 6))
        wob = (_noise(rng, (1, max(ln, 2)), 18)[0] - 0.5) * 3.0
        for k in range(ln):
            yy = y0 + k
            if yy >= h - 3:
                break
            xx = int(x + wob[k])
            wk = max(1, int(round(wd * (1.0 - 0.45 * k / ln))))
            drips[yy, max(0, xx - wk // 2):xx + wk // 2 + 1] = max(0.25, 1.0 - 0.6 * k / ln)
        yb = min(h - 4, y0 + ln)
        drips[yb:yb + 6, max(0, x - 2):x + 3] = 0.9                                      # the bead
    drips = _blur(drips, 0.7)
    paint = np.clip(mask * dens + drips * 0.85, 0, 1)
    # fading and flaking of the top coat: patches of the sun and rain, then flakes of paint gone to the brick
    fade = 0.80 + 0.20 * np.clip(_noise(rng, (h, w), 70) * 1.6, 0, 1)
    flake = _noise(rng, (h, w), 5) * 0.55 + _noise(rng, (h, w), 20) * 0.45
    paint *= fade * (1.0 - 0.70 * (flake > 0.93))
    # brick: the paint is thinner on the joints and varies per brick; the relief goes into the normal map
    relief, mortar, per = _brick(h, w, ppm, rng)
    paint *= (1.0 - 0.22 * mortar) * per
    shadow *= (1.0 - 0.3 * mortar)
    # the older layers behind: a roller-buffed patch (grey-brown, ragged) and the ghost of an earlier tag in another colour
    buff = np.zeros((h, w), np.float32)
    bx0, bx1 = int(w * rng.uniform(0.03, 0.14)), int(w * rng.uniform(0.52, 0.70))
    by0, by1 = int(h * rng.uniform(0.40, 0.60)), int(h * rng.uniform(0.92, 1.0))
    buff[by0:by1, bx0:bx1] = 1.0
    buff = np.clip(_blur(_warp(buff, rng, 5.0, 20), 3.0) * 1.8 - 0.4, 0, 1) * (0.55 + 0.45 * _noise(rng, (h, w), 30)) * (1.0 - 0.25 * mortar) * 0.9
    other = "Graffiti_Rule" if name != "Graffiti_Rule" else "Graffiti_Inc"
    gm = _text_mask(TEXT[other], INK[other][2], 300, int(w * 0.42), int(h * 0.50), rng)
    gfull = Image.new("L", (w, h), 0)
    gfull.paste(gm, (int(w * 0.52), int(h * 0.06)))
    ghost = _blur(_warp(np.asarray(gfull, np.float32) / 255.0, rng, 3.0, 14), 2.2)
    ghost = np.clip((ghost - 0.3) * 2.0, 0, 1) * (0.25 + 0.30 * _noise(rng, (h, w), 40)) * (1.0 - 0.4 * mortar)
    # compose: ghost, buff patch, then shadow, tag, highlight, mist
    ghost_col, buff_col = np.array((0.16, 0.18, 0.20)), np.array((0.20, 0.17, 0.14))
    tint = 0.80 + 0.30 * _noise(rng, (h, w), 26)[..., None] + 0.10 * (rim[..., None] * 0.0)
    ink_col = np.array(ink)[None, None] * tint * (0.78 + 0.30 * dens[..., None])
    ink_col = np.where(drips[..., None] > 0.2, ink_col * 0.85, ink_col)
    edge_col = np.array(edge)[None, None] * (0.8 + 0.4 * _noise(rng, (h, w), 10)[..., None])
    hl_col = np.clip(np.array(ink) * 2.4 + 0.12, 0, 1)[None, None]
    layers = [(ghost, ghost_col[None, None]), (buff * 0.8, buff_col[None, None]), (shadow * 0.92, edge_col), (paint, ink_col),
              (hl * 0.55 * paint, hl_col), (mist * 0.38, np.array(ink)[None, None] * 0.85)]
    col = np.zeros((h, w, 3), np.float32)
    a = np.zeros((h, w), np.float32)
    for al, c in layers:
        al = np.clip(al, 0, 1)
        col = col * (1 - al[..., None]) + c * al[..., None]
        a = a + al * (1 - a)
    height = np.clip(0.55 * paint + 0.30 * shadow + 0.2 * buff + 0.45 * relief, 0, 1)
    return col, np.clip(a, 0, 1), height


def stencil(name, rng):
    w, h = [int(round(v * CELLS[name][2])) for v in CELLS[name][:2]]
    tm = _text_mask("MOTT ST", "BebasNeue-Regular.ttf", 260, int(w * 0.68), h, rng, jitter=False)
    im = Image.new("L", (w, h), 0)
    im.paste(tm, (0, 0))
    d = ImageDraw.Draw(im)
    ax0, ax1, cy = int(w * 0.72), int(w * 0.97), h // 2
    d.polygon([(ax0, cy - h // 8), (ax1 - h // 3, cy - h // 8), (ax1 - h // 3, cy - h // 3), (ax1, cy), (ax1 - h // 3, cy + h // 3),
               (ax1 - h // 3, cy + h // 8), (ax0, cy + h // 8)], fill=255)
    a = np.asarray(im, np.float32) / 255.0
    for yy in (int(h * 0.36), int(h * 0.62)):                                                           # stencil bridges
        a[yy:yy + 5, :] = 0.0
    for xx in (ax0 + (ax1 - ax0) // 3, ax0 + 2 * (ax1 - ax0) // 3):
        a[:, xx:xx + 5] = 0.0
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.4)), np.float32) / 255.0
    over = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(5)), np.float32) / 255.0
    flake = _noise(rng, (h, w), 4) * 0.6 + _noise(rng, (h, w), 18) * 0.4
    alpha = np.clip(a * (1.1 - 0.5 * (flake > 0.7)) * 0.9 + over * 0.12, 0, 1)
    col = np.array(WHITE)[None, None] * (0.85 + 0.25 * _noise(rng, (h, w), 14)[..., None])
    return col, alpha, a


def grime(name, rng):
    w, h = [int(round(v * CELLS[name][2])) for v in CELLS[name][:2]]
    v = (h - 1 - np.arange(h, dtype=np.float32))[:, None] / (CELLS[name][2])           # metres above the foot
    n1, n2 = _noise(rng, (h, w), 30), _noise(rng, (h, w), 7)
    top = 0.55 + 0.35 * _noise(rng, (1, w), 60)[0][None, :]                              # the band's height varies along the wall
    band = np.clip(1.0 - v / top, 0, 1) ** 1.7
    sp = (rng.random((h, w)) < 0.0035 * np.clip(1.4 - v, 0, 1)).astype(np.float32)       # splash speckle higher up
    sp = np.asarray(Image.fromarray((sp * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255.0 * 4.0
    alpha = np.clip((band * (0.45 + 0.4 * n1 + 0.25 * n2) + sp * 0.5) * 0.85, 0, 0.82)
    alpha *= np.clip((np.arange(w) / 40.0), 0, 1)[None, :] * np.clip(((w - 1 - np.arange(w)) / 40.0), 0, 1)[None, :]   # the ends fade
    col = np.array((0.045, 0.040, 0.034))[None, None] * (0.7 + 0.6 * n2[..., None]) + np.array((0.04, 0.025, 0.012))[None, None] * band[..., None]
    return col, alpha, alpha


def scuffs(name, rng):
    w, h = [int(round(v * CELLS[name][2])) for v in CELLS[name][:2]]
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for _ in range(46):
        x, y = rng.uniform(0.05, 0.95) * w, rng.uniform(0.18, 0.95) * h
        ln, ang = rng.uniform(0.04, 0.22) * w, rng.uniform(-0.6, 0.35)
        d.line([(x, y), (x + ln * np.cos(ang), y + ln * np.sin(ang))], fill=int(rng.integers(90, 255)), width=int(rng.integers(1, 4)))
    a = np.asarray(im.filter(ImageFilter.GaussianBlur(1.1)), np.float32) / 255.0
    mask = np.clip(_noise(rng, (h, w), 50) * 1.6 - 0.35, 0, 1)
    alpha = np.clip(a * (0.35 + 0.6 * mask), 0, 0.7)
    light = _noise(rng, (h, w), 10)[..., None]
    col = np.where(light > 0.45, np.array((0.50, 0.48, 0.44))[None, None], np.array((0.02, 0.02, 0.02))[None, None])
    return col, alpha, alpha


def streaks(name, rng):
    w, h = [int(round(v * CELLS[name][2])) for v in CELLS[name][:2]]
    a = np.zeros((h, w), np.float32)
    for _ in range(11):
        x = int(rng.integers(8, w - 8))
        ln = int(rng.integers(h // 4, h - 20))
        wd = int(rng.integers(3, 12))
        prof = np.clip(1.0 - np.arange(ln) / ln, 0, 1) ** 0.8 * rng.uniform(0.35, 0.9)
        wob = _noise(rng, (1, ln), 40)[0] * 6 - 3
        for yy in range(ln):
            xx = int(x + wob[yy])
            a[yy, max(0, xx - wd // 2):xx + wd // 2 + 1] = np.maximum(a[yy, max(0, xx - wd // 2):xx + wd // 2 + 1], prof[yy])
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.2)), np.float32) / 255.0
    a *= 0.35 + 0.65 * _noise(rng, (h, w), 14)
    rust = _noise(rng, (h, w), 60)[..., None]
    col = np.array((0.30, 0.13, 0.05))[None, None] * rust + np.array((0.05, 0.045, 0.04))[None, None] * (1 - rust)
    return col, np.clip(a * 0.8, 0, 0.75), a


def _normal(h_img, k=2.0):
    gy, gx = np.gradient(h_img.astype(np.float32))
    n = np.stack([-gx * k, gy * k, np.ones_like(h_img)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def make_textures(seed=0, log=print):
    d = paths.texture_set(SET)
    os.makedirs(d, exist_ok=True)
    rects = layout()
    bc = np.zeros((PAGE, PAGE, 4), np.float32)
    nm = np.zeros((PAGE, PAGE, 3), np.float32) + np.array((0.5, 0.5, 1.0), np.float32)
    orm = np.zeros((PAGE, PAGE, 3), np.float32) + np.array((1.0, 0.7, 0.0), np.float32)
    cells = {}
    for i, k in enumerate(CELLS):
        rng = np.random.default_rng(seed * 100 + 17 + i)
        fn = graffiti if k.startswith("Graffiti") else stencil if k.startswith("Stencil") else grime if "Grime" in k else scuffs if "Scuffs" in k else streaks
        col, alpha, height = fn(k, rng)
        x, y, w, h = rects[k]
        bc[y:y + h, x:x + w, :3] = np.clip(col, 0, 1)
        bc[y:y + h, x:x + w, 3] = alpha
        nm[y:y + h, x:x + w] = _normal(height, 2.0 if k.startswith(("Graffiti", "Stencil")) else 0.6)
        rough = 0.62 if k.startswith(("Graffiti", "Stencil")) else 0.92
        orm[y:y + h, x:x + w] = np.array((1.0, rough, 0.0), np.float32)
        cells[k] = {"px": [x, y, w, h], "uv": [x / PAGE, 1 - (y + h) / PAGE, (x + w) / PAGE, 1 - y / PAGE], "size_m": list(CELLS[k][:2]),
                    "text": [TEXT[k]] if k in TEXT else []}

    def save(arr, role, mode):
        Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), mode).save(os.path.join(d, "T_%s_%s.png" % (SET, role)), optimize=True)
    save(bc, "BC", "RGBA")
    save(nm, "N", "RGB")
    save(orm, "ORM", "RGB")
    info = {"kind": "decal_atlas", "albedo_mean": [0.35, 0.30, 0.25], "roughness_mean": 0.8, "metallic_mean": 0.0, "alpha": "BC alpha = paint coverage",
            "about": "Canal Street decals (assets/_chinatown_decals.py): BC rgb = paint colour, alpha = coverage; v up in the uv rects",
            "resolution": PAGE, "files": {"BC": "T_%s_BC.png" % SET, "N": "T_%s_N.png" % SET, "ORM": "T_%s_ORM.png" % SET}, "cells": cells,
            "fill": round(sum(c["px"][2] * c["px"][3] for c in cells.values()) / float(PAGE * PAGE), 3)}
    with open(os.path.join(d, "set.json"), "w") as f:
        json.dump(info, f, indent=1)
    log("decal page %d px, %d cells, fill %.0f %%" % (PAGE, len(cells), info["fill"] * 100))
    return info


def cells_info():
    with open(os.path.join(paths.texture_set(SET), "set.json")) as f:
        return json.load(f)["cells"]


def build_decals(ctx):
    """One quad per cell (SM_Decal_CT_<Name>) with the shared material M_CT_Decals; registers them as assets."""
    import bmesh
    import bpy
    from mi import mat, scene, geo
    from assets._chinatown_kit import SLOT_META
    if ctx.args.bake or not os.path.exists(os.path.join(paths.texture_set(SET), "set.json")):
        make_textures(ctx.args.seed, ctx.log)
    ctx.sets.append(SET)
    m = mat.from_texture_set(paths.texture_set(SET), name=SLOT, masks=False, alpha="splash", macro=0.0)
    p = mat.principled(m)
    img = next(n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeTexImage" and n.image and "_BC" in n.image.name)
    m.node_tree.links.new(img.outputs["Alpha"], p.inputs["Alpha"])
    try:
        m.surface_render_method = "DITHERED"
    except Exception:
        pass
    SLOT_META[SLOT] = {"workflow": "decal", "set": SET, "uv": "each quad's UVs are on its own cell of the page",
                       "note": "decal-domain MI in Unreal: BC rgb with alpha as the paint's opacity, N blended, roughness from ORM; "
                               "on the quad as a masked / dithered surface for the preview"}
    cells = cells_info()
    made = []
    for k, c in cells.items():
        w, h = c["size_m"]
        u0, v0, u1, v1 = c["uv"]
        bm = bmesh.new()
        vs = [bm.verts.new(p_) for p_ in ((0, 0, 0), (w, 0, 0), (w, 0, h), (0, 0, h))]
        f = bm.faces.new(vs)
        uv = bm.loops.layers.uv.new(geo.UV)
        for lo, (uu, vv) in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
            lo[uv].uv = (uu, vv)
        ob = geo.new("SM_Decal_CT_" + k, bm, ctx.kit, smooth=None, uv=False)
        ob.data.materials.append(m)
        ctx.asset(ob, collision="none", slots=SLOT_META, expect_size=(w, None, h),
                  notes="Decal quad %.1f x %.1f m (a %s), facing -Y with its pivot at the bottom-left corner; placed 4 mm in front of the wall. In "
                        "Unreal a decal actor of this size with the cell's UV rect." % (w, h, "graffiti tag" if k.startswith("Graffiti") else
                        "spray stencil" if k.startswith("Stencil") else "near-ground wear pass piece"))
        ctx.K[ob.name] = ob
        made.append(ob)
    return made


if __name__ == "__main__":
    make_textures()
