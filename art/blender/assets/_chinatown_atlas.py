"""Canal Street sign atlases: every face of _chinatown_names.FACES drawn with PIL into 4096 x 4096 atlases.

    venv/bin/python art/blender/assets/_chinatown_atlas.py            # draws art/out/textures/Sign_CT_Atlas<N>/

Each atlas is a texture set `Sign_CT_Atlas<N>` (T_Sign_CT_Atlas<N>_BC sRGB, _ORM linear at half size, _E sRGB = the
night emissive at strength 1) with its cells in set.json: `cells.<key>` = {"atlas", "px": [x, y, w, h] from the top-left,
"uv": [u0, v0, u1, v1] with v up (Blender / glTF-before-flip), "face_m": [w, h]}. A carrier mesh (SM_Sign_CT_*) has its
face on 0..1 UVs in slot M_Sign_CT_Face; the material instance of a placed sign picks its atlas and maps 0..1 to the
cell: uv' = uv * (u1 - u0, v1 - v0) + (u0, v0). Lit faces: the emissive map is the clean print lit from behind
(lightbox) at the face's night value; unlit faces (boards, paper) have black emissive.

Density: lit faces 256 px/m (a 10 m band is 2560 x 230 px), paper, boards and street blades 512 px/m (seen close).
Cells are padded by 8 px and aligned to 4 px (block compression). The packer is a skyline packer, tallest first.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from assets import _chinatown_names as names  # noqa: E402
from assets import signs as sg  # noqa: E402
from mi import paths  # noqa: E402

ATLAS = 4096
PAD = 8
DENS = {"band": 256, "blade": 256, "kiosk": 256, "arch": 256, "board": 512, "poster": 512, "placard": 512, "street": 512}
FONT_FILES = {
    "ct_heavy": "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
    "ct_bold": "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "ct_street": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
    "ct_marker": "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
    "ct_serif": os.path.join(os.path.dirname(HERE), "fonts", "OldStandard-Bold.ttf"),
}
FONT_KEY = {"heavy": "ct_heavy", "bold": "ct_bold", "street": "ct_street", "marker": "ct_marker", "serif": "ct_serif"}
sg.FONTS.update(FONT_FILES)          # in-memory only: signs.Canvas.text looks fonts up by key


def set_name(i):
    return "Sign_CT_Atlas%d" % i


# ================================================================================================= packing

def pack(sizes):
    """Skyline bottom-left packing of {key: (w, h)} px into as many ATLAS x ATLAS pages as needed.
    Returns {key: (page, x, y)} with y from the top."""
    order = sorted(sizes, key=lambda k: (-sizes[k][1], -sizes[k][0], k))
    pages, out = [], {}

    def place(sky, w, h):
        best = None
        for i in range(len(sky)):
            x = sky[i][0]
            if x + w > ATLAS:
                break
            y, j, span = 0, i, 0
            while span < w and j < len(sky):
                y = max(y, sky[j][1])
                span += sky[j][2]
                j += 1
            if span < w or y + h > ATLAS:
                continue
            if best is None or (y, x) < (best[1], best[0]):
                best = (x, y)
        return best

    def add(sky, x, y, w, h):
        new = []
        for (sx, sy, sw) in sky:
            a, b = max(sx, x), min(sx + sw, x + w)
            if b <= a:
                new.append((sx, sy, sw))
                continue
            if sx < a:
                new.append((sx, sy, a - sx))
            if b < sx + sw:
                new.append((b, sy, sx + sw - b))
        new.append((x, y + h, w))
        new.sort()
        merged = []
        for s in new:
            if merged and merged[-1][1] == s[1] and merged[-1][0] + merged[-1][2] == s[0]:
                merged[-1] = (merged[-1][0], s[1], merged[-1][2] + s[2])
            else:
                merged.append(s)
        return merged

    for k in order:
        w, h = sizes[k]
        w4, h4 = w + 2 * PAD, h + 2 * PAD
        for p, sky in enumerate(pages):
            pos = place(sky, w4, h4)
            if pos:
                pages[p] = add(sky, pos[0], pos[1], w4, h4)
                out[k] = (p, pos[0] + PAD, pos[1] + PAD)
                break
        else:
            sky = [(0, 0, ATLAS)]
            pos = place(sky, w4, h4)
            if pos is None:
                raise ValueError("%s (%d x %d px) does not fit a %d atlas" % (k, w, h, ATLAS))
            pages.append(add(sky, pos[0], pos[1], w4, h4))
            out[k] = (len(pages) - 1, pos[0] + PAD, pos[1] + PAD)
    return out, len(pages)


def cell_px(F):
    k = DENS[F["kind"]]
    a4 = lambda v: int(4 * round(v * k / 4.0))
    return a4(F["w"]), a4(F["h"])


# ================================================================================================= drawing

def stacked(cv, F, ink):
    """Blade letters stacked top to bottom, one word group per line, a dot between groups."""
    letters = []
    for gi, (text, _c, _y, font) in enumerate(F["lines"]):
        if gi:
            letters.append(("·", font))
        letters += [(ch, font) for ch in text if ch != " "]
    n = len(letters)
    rim = 0.11 * F["w"]
    usable = F["h"] - 2 * rim - 0.06
    step = usable / n
    cap = min(step * 0.74, (F["w"] - 2 * rim) * 0.70)
    mask = cv.blank()
    for i, (ch, font) in enumerate(letters):
        cy = rim + 0.03 + step * (i + 0.5)
        m, _w, _s = cv.text(ch, FONT_KEY[font], cap if ch != "·" else cap * 0.5, F["w"] / 2, cy,
                            max_w=(F["w"] - 2 * rim) * 0.86)
        mask = np.maximum(mask, m)
    cv.put(mask, ink)
    return mask


def lines(cv, F, ink, sub_ink=None, wobble=0.0, rng=None):
    mask = cv.blank()
    inner = F["w"] - 2 * max(0.10 * F["h"], 0.03) - 0.06
    for i, (text, cap, cy, font) in enumerate(F["lines"]):
        cond = 0.86 if font == "heavy" else 0.94
        m, _w, _s = cv.text(text, FONT_KEY[font], cap * F["h"], F["w"] / 2, cy * F["h"], cond, 0.02 if font == "heavy" else 0.05,
                            max_w=inner)
        if wobble and rng is not None:                                    # marker on card: a hand-drawn wobble
            im = Image.fromarray((m * 255).astype(np.uint8)).rotate(float(rng.uniform(-2.5, 2.5)), Image.BICUBIC)
            m = np.asarray(im, np.float32) / 255.0
            m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255.0
        cv.put(m, sub_ink if (i and sub_ink is not None) else ink)
        mask = np.maximum(mask, m)
    return mask


def frame_mask(cv, t):
    return ((cv.x < t) | (cv.x > cv.wm - t) | (cv.y < t) | (cv.y > cv.hm - t)).astype(np.float32)


def draw(key, F, rng):
    """(BC (H, W, 3) sRGB, roughness (H, W), E (H, W, 3) linear or None) of one face."""
    k = DENS[F["kind"]]
    field, ink = sg.paint(F["field"]), sg.paint(F["ink"])
    sub = sg.paint(F["sub"]) if F.get("sub") else None
    cv = sg.Canvas(F["w"], F["h"], k, field)
    kind = F["kind"]
    letters = cv.blank()
    if kind in ("band", "kiosk", "arch"):
        fw = 0.045 * F["h"]
        ki = fw + 0.03
        cv.put(cv.rect(ki, ki, F["w"] - ki, F["h"] - ki, r=0.02, outline=0.010), ink)            # printed keyline
        cv.put(cv.rect(ki + 0.025, ki + 0.025, F["w"] - ki - 0.025, F["h"] - ki - 0.025, r=0.015, outline=0.005), ink, 0.7)
        letters = lines(cv, F, ink, sub)
        if kind == "band":                                                                       # end ornaments: coin and lattice
            for xs in (ki + 0.22, F["w"] - ki - 0.22):
                cy, r = F["h"] * 0.40, F["h"] * 0.17
                ring = cv.draw(lambda d, kk: d.ellipse([(xs - r) * kk, (cy - r) * kk, (xs + r) * kk, (cy + r) * kk], outline=255,
                                                       width=max(1, int(0.022 * kk))))
                sq = cv.draw(lambda d, kk: d.rectangle([(xs - r * 0.36) * kk, (cy - r * 0.36) * kk, (xs + r * 0.36) * kk,
                                                        (cy + r * 0.36) * kk], outline=255, width=max(1, int(0.016 * kk))))
                cv.put(np.maximum(ring, sq), ink)
                letters = np.maximum(letters, np.maximum(ring, sq))
        clean = cv.c.copy()
        rough = 0.28 + sg.weather_face(cv, rng, 0.9, bugs=int(60 * F["w"]), crack=False)
        frame = frame_mask(cv, fw)
        cv.put(frame, sg.paint("#1b1c20"))
        rough = np.where(frame > 0.5, 0.55, rough)
    elif kind == "blade":
        rim = 0.11 * F["w"]
        cv.put(frame_mask(cv, rim * 0.55), sg.paint(F.get("rim", F["ink"])))
        cv.put(cv.rect(rim * 0.8, rim * 0.8, F["w"] - rim * 0.8, F["h"] - rim * 0.8, r=0.03, outline=0.012), ink, 0.8)
        letters = stacked(cv, F, ink)
        clean = cv.c.copy()
        rough = 0.30 + sg.weather_face(cv, rng, 0.8, top_fade=0.15, bugs=int(40 * F["h"]))
    elif kind == "board":
        n = sg.vnoise(rng, cv.H, cv.W, cv.k * 0.05)
        cv.c = cv.c * (0.90 + 0.10 * n[..., None])                                              # brush strokes along the board
        cv.put(cv.rect(0.03, 0.03, F["w"] - 0.03, F["h"] - 0.03, r=0.01, outline=0.012), ink, 0.85)
        letters = lines(cv, F, ink, sub)
        clean = cv.c.copy()
        rough = 0.55 + sg.weather_face(cv, rng, 1.2, top_fade=0.1, grime=0.4)
    elif kind in ("poster", "placard"):
        letters = lines(cv, F, ink, sub, wobble=0.02 if kind == "placard" else 0.0, rng=rng)
        clean = cv.c.copy()
        rough = 0.75 + sg.weather_face(cv, rng, 1.0, top_fade=0.1, grime=0.3)
        if kind == "poster":                                                                    # paste wrinkles and a fold
            wr = sg.vnoise(rng, cv.H, cv.W, cv.k * 0.03)
            cv.c = cv.c * (0.92 + 0.08 * wr[..., None])
            fold = sg.sstep(0.004, 0.0, np.abs(cv.y - cv.hm * 0.5))
            cv.put(fold, cv.c.mean(axis=(0, 1)) * 0.7, 0.4)
    else:                                                                                       # street blade
        cv.put(cv.rect(0.012, 0.012, F["w"] - 0.012, F["h"] - 0.012, r=0.01, outline=0.008), ink)
        letters = lines(cv, F, ink)
        clean = cv.c.copy()
        rough = 0.35 + 0.5 * sg.weather_face(cv, rng, 0.6, top_fade=0.1, grime=0.15)
    E = None
    if F.get("lit"):
        v = cv.y / F["h"]
        if kind == "blade":
            prof = 0.75 + 0.25 * np.exp(-((cv.x / F["w"] - 0.5) / 0.35) ** 2)
        else:
            prof = 0.62 + 0.38 * np.maximum(np.exp(-((v - 0.28) / 0.17) ** 2), np.exp(-((v - 0.72) / 0.17) ** 2))
        dirt = np.clip(sg.lum(cv.c) / np.maximum(sg.lum(clean), 1e-3), 0, 1.2)
        fr = frame_mask(cv, 0.045 * F["h"]) if kind != "blade" else np.zeros_like(prof)
        E = sg.to_lin(clean) * (prof * dirt * (1 - fr))[..., None]
        E = E * (0.30 + 0.70 * np.clip(letters[..., None] + 0.6 * sg.lum(clean)[..., None], 0, 1))
    return np.clip(cv.c, 0, 1), np.clip(rough, 0.02, 1), E


# ================================================================================================= atlas

def build_atlases(seed=0, log=print):
    names.check_english()
    sizes = {k: cell_px(F) for k, F in names.FACES.items()}
    where, npages = pack(sizes)
    BC = [np.zeros((ATLAS, ATLAS, 3), np.float32) for _ in range(npages)]
    RO = [np.full((ATLAS, ATLAS), 0.6, np.float32) for _ in range(npages)]
    EM = [np.zeros((ATLAS, ATLAS, 3), np.float32) for _ in range(npages)]
    for p in range(npages):
        BC[p][:] = sg.paint("#2a2a2c")
    cells = {}
    for key, F in names.FACES.items():
        rng = np.random.default_rng(sum(map(ord, key)) * 7919 + seed)
        c, r, e = draw(key, F, rng)
        p, x, y = where[key]
        w, h = sizes[key]
        im = lambda a: np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS), np.float32) / 255.0
        cc = im(c)
        BC[p][y:y + h, x:x + w] = cc
        rr = np.asarray(Image.fromarray((r * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR), np.float32) / 255.0
        RO[p][y:y + h, x:x + w] = rr
        if e is not None:
            EM[p][y:y + h, x:x + w] = im(sg.to_srgb(e))
        # bleed the edge pixels into the padding (mip and filtering safety)
        for arr in (BC[p], RO[p], EM[p]):
            arr[y - PAD:y, x:x + w] = arr[y:y + 1, x:x + w]
            arr[y + h:y + h + PAD, x:x + w] = arr[y + h - 1:y + h, x:x + w]
            arr[y - PAD:y + h + PAD, x - PAD:x] = arr[y - PAD:y + h + PAD, x:x + 1]
            arr[y - PAD:y + h + PAD, x + w:x + w + PAD] = arr[y - PAD:y + h + PAD, x + w - 1:x + w]
        cells[key] = {"atlas": set_name(p + 1), "px": [x, y, w, h],
                      "uv": [round(x / ATLAS, 6), round(1 - (y + h) / ATLAS, 6), round((x + w) / ATLAS, 6), round(1 - y / ATLAS, 6)],
                      "face_m": [F["w"], F["h"]], "px_per_m": DENS[F["kind"]], "kind": F["kind"], "lit": bool(F.get("lit")),
                      "glow": F.get("glow"), "carrier": F["carrier"], "text": [t[0] for t in F["lines"]], "where": F["where"]}
    out = []
    for p in range(npages):
        sname = set_name(p + 1)
        d = paths.ensure(paths.texture_set(sname))
        Image.fromarray((BC[p] * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, "T_%s_BC.png" % sname), optimize=True)
        orm = np.stack([np.ones_like(RO[p]), RO[p], np.zeros_like(RO[p])], -1)
        Image.fromarray((orm * 255).astype(np.uint8), "RGB").resize((ATLAS // 2, ATLAS // 2), Image.BILINEAR) \
            .save(os.path.join(d, "T_%s_ORM.png" % sname), optimize=True)
        Image.fromarray((EM[p] * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, "T_%s_E.png" % sname), optimize=True)
        mine = {k: v for k, v in cells.items() if v["atlas"] == sname}
        used = sum(v["px"][2] * v["px"][3] for v in mine.values()) / float(ATLAS * ATLAS)
        lin = sg.to_lin(BC[p])
        info = dict(kind="sign_atlas", resolution=[ATLAS, ATLAS],
                    files={"BC": "T_%s_BC.png" % sname, "ORM": "T_%s_ORM.png" % sname, "E": "T_%s_E.png" % sname},
                    convention={"BC": "sRGB", "ORM": "linear AO, roughness, metallic (half size)",
                                "E": "sRGB, night value at strength 1; black where the face is unlit"},
                    emissive_day=0.3, cells=mine, fill=round(used, 3),
                    albedo_mean=[round(float(v), 4) for v in lin.reshape(-1, 3).mean(0)],
                    roughness_mean=round(float(RO[p].mean()), 3), metallic_mean=0.0,
                    fonts=sorted({os.path.basename(FONT_FILES[FONT_KEY[t[3]]]) for F in names.FACES.values() for t in F["lines"]}),
                    note="Canal Street sign faces, English only, invented names (assets/_chinatown_names.py). The MI of a placed "
                         "sign maps the carrier's 0..1 face UVs to its cell (uv, v up).")
        with open(os.path.join(d, "set.json"), "w") as f:
            json.dump(info, f, indent=1, sort_keys=True)
        log("atlas %s: %d faces, %.0f %% of the page used" % (sname, len(mine), used * 100))
        out.append(sname)
    return out, cells


def preview_sheet(path, cells, max_px=1280):
    """A small JPEG of the atlas pages side by side (for review)."""
    pages = sorted({c["atlas"] for c in cells.values()})
    ims = [Image.open(os.path.join(paths.texture_set(p), "T_%s_BC.png" % p)).convert("RGB") for p in pages]
    W = max_px // len(ims)
    row = Image.new("RGB", (W * len(ims), W), (16, 16, 16))
    for i, im in enumerate(ims):
        row.paste(im.resize((W, W), Image.LANCZOS), (i * W, 0))
    from mi import render
    return render.save_jpeg(row, path, 300)


if __name__ == "__main__":
    sets, cells = build_atlases()
    print(sets, len(cells))
