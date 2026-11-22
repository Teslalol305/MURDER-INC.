"""Drawn art for the gap-filling pass (assets/gaps.py, the furniture graphics, the shop-front extras).

1. Tiling sets drawn with numpy (no catalogued scan exists for them; Poly Haven has none of these in the catalogue):
   TS_Bark_Pear (young Callery pear trunk and boughs), TS_Leaf_Pear and TS_Leaf_Privet (one leaf over the whole
   0..1 square: the leaf meshes are cut to the outline, so no alpha), TS_Cardboard_Kraft (corrugated board),
   TS_Steel_Stainless (brushed #4 stainless). Periodic noise (FFT-filtered) so every set tiles.
2. Painted graphics and printed faces Sign_<Key> (T_Sign_<Key>_BC / _ORM / _E), read by mat.sign_face(key): all the
   furniture faces that were flat colours (meter dial, newspaper, mail label, booth PARK and RATES boards, shed
   banners, sign plate, bus-stop flag, street-name blade) and the faces of the new assets (phone head and card,
   pedestrian signal, vending face, generator label, toilet hire plate, food-cart menu, crate and carton stencils,
   barber pole). Drawn with the signs.py canvas, weathered with mi.texpaint noise. Fictional content only.

    build.py build gaps --only art          (redraws everything, about a minute)
"""
import math
import zlib
import os

import numpy as np
from PIL import Image

from assets import signs as S
from mi import bake, paths
from mi import texpaint as tp

paint, sstep = S.paint, S.sstep


# ================================================================================================ periodic noise

def pnoise(rng, h, w, sigma_px, aniso=(1.0, 1.0)):
    """Seamless gaussian-filtered noise, zero mean, unit deviation. aniso = (stretch along x, along y)."""
    fy = np.fft.fftfreq(h)[:, None] * aniso[1]
    fx = np.fft.fftfreq(w)[None, :] * aniso[0]
    k = np.exp(-2 * (np.pi * sigma_px) ** 2 * (fx * fx + fy * fy))
    n = np.real(np.fft.ifft2(np.fft.fft2(rng.normal(size=(h, w))) * k))
    return ((n - n.mean()) / (n.std() + 1e-9)).astype(np.float32)


def fbm(rng, h, w, sigma_px, octaves=4, aniso=(1.0, 1.0)):
    out, amp, tot = np.zeros((h, w), np.float32), 1.0, 0.0
    for _ in range(octaves):
        out += amp * pnoise(rng, h, w, sigma_px, aniso)
        tot += amp
        amp *= 0.5
        sigma_px = max(0.6, sigma_px / 2.0)
    return out / tot


def tiling_set(name, tile_m, ch, meta=None):
    """Write a numpy tiling set (ch: bc linear (H, W, 3), rough, metal, height m [, ao])."""
    h, w = ch["rough"].shape
    px = tile_m[0] / w
    if "normal" not in ch:
        ch["normal"] = bake.normal_from_height(ch["height"], px, wrap=True)
    if "ao" not in ch:
        ch["ao"] = bake.ao_from_height(ch["height"], px, relief=float(np.ptp(ch["height"])) or 1e-3)
    info = dict(kind="tiling", tile_m=list(tile_m), texel_density_px_per_m=round(w / tile_m[0], 1), seamless=True,
                source="drawn with numpy in assets/_gaps_art.py")
    info.update(meta or {})
    return bake.write_set(name, ch, meta=info)


def have(name):
    return os.path.exists(os.path.join(paths.texture_set(name), "set.json"))


def bark_set(force=False, n=1024):
    """Young Callery pear bark, 0.5 m tile, u around the stem, v along it: grey-brown, shallow vertical fissures
    breaking into scaly plates, pale lenticels, a green algae film on the shaded side (wear G drives it in engine)."""
    if have("TS_Bark_Pear") and not force:
        return
    rng = np.random.default_rng(11)
    fis = fbm(rng, n, n, 10, 4, aniso=(1.0, 0.18))                 # long along v (rows)
    plate = fbm(rng, n, n, 28, 3, aniso=(1.0, 0.45))
    fine = pnoise(rng, n, n, 1.2)
    ridges = 1.0 - np.abs(np.tanh(1.6 * fis))
    crack = sstep(0.82, 0.97, ridges) * sstep(-0.3, 0.6, plate)
    height = 0.004 * (1 - crack) + 0.0012 * plate + 0.0003 * fine
    lent = sstep(2.6, 3.4, pnoise(rng, n, n, 1.6, aniso=(1.0, 3.0)))     # short horizontal lenticels
    base = np.array([0.120, 0.100, 0.082], np.float32)
    grey = np.array([0.205, 0.195, 0.180], np.float32)
    t = sstep(-1.0, 1.2, plate)[..., None]
    bc = base * (1 - t) + grey * t
    bc = bc * (0.88 + 0.12 * fine[..., None])
    bc = bc * (1 - 0.72 * crack[..., None]) + np.array([0.045, 0.032, 0.022]) * 0.72 * crack[..., None]
    bc = bc * (1 - 0.6 * lent[..., None]) + np.array([0.33, 0.30, 0.25]) * 0.6 * lent[..., None]
    algae = sstep(0.4, 1.6, fbm(rng, n, n, 40, 3))[..., None] * 0.35
    bc = bc * (1 - algae) + np.array([0.085, 0.11, 0.05]) * algae
    rough = np.clip(0.78 + 0.12 * crack - 0.05 * plate + 0.03 * fine, 0.5, 1.0)
    tiling_set("TS_Bark_Pear", (0.5, 0.5), dict(bc=bc.astype(np.float32), rough=rough.astype(np.float32),
                                                metal=np.zeros((n, n), np.float32), height=height.astype(np.float32)),
               meta=dict(surface="bark", note="u around the stem, v along it; two-sided not needed"))


def leaf_outline(kind, n=24):
    """Leaf outline in the unit square (u across, v from the petiole at v=0 to the tip at v=1), closed polygon."""
    t = np.linspace(0, np.pi, n)
    v = (1 - np.cos(t)) / 2
    if kind == "pear":            # broad ovate, short acuminate tip, widest at 40 %
        half = 0.48 * np.sin(np.pi * v ** 0.82) ** 0.85 * (1 - 0.25 * v ** 6)
    else:                          # privet: narrow elliptic
        half = 0.47 * np.sin(np.pi * v) ** 0.9
    right = np.stack([0.5 + half, v], 1)
    left = np.stack([0.5 - half[::-1], v[::-1]], 1)
    P = np.concatenate([right, left[1:-1]])
    return P


def leaf_set(kind, force=False, n=512):
    """One leaf over the 0..1 square (petiole at v=0, tip at v=1), upper side: midrib, pinnate veins, a glossy
    cuticle, sun-yellowed margin, a few insect bites and spots. Back side shares it (two-sided foliage)."""
    name = "TS_Leaf_Pear" if kind == "pear" else "TS_Leaf_Privet"
    if have(name) and not force:
        return
    rng = np.random.default_rng(21 if kind == "pear" else 22)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    u = (xx + 0.5) / n
    v = 1 - (yy + 0.5) / n
    P = leaf_outline(kind, 64)
    from PIL import ImageDraw
    im = Image.new("L", (n, n), 0)
    ImageDraw.Draw(im).polygon([(x * n, (1 - y) * n) for x, y in P], fill=255)
    inside = np.asarray(im) > 127
    d_mid = np.abs(u - 0.5)
    mid = sstep(0.010, 0.0, d_mid) * (v < 0.97)
    k = 9 if kind == "pear" else 7
    s = (v - 0.04) * k - d_mid * k * 1.4                          # veins running out and up from the midrib
    sec = sstep(0.09, 0.0, np.abs(s - np.round(s))) * sstep(0.02, 0.05, d_mid) * (v > 0.06)
    net = pnoise(rng, n, n, 2.2)
    tert = sstep(0.75, 0.95, 1 - np.abs(np.tanh(2 * net))) * 0.5
    fine = pnoise(rng, n, n, 1.0)
    big = pnoise(rng, n, n, 60)
    base = np.array([0.052, 0.098, 0.028] if kind == "pear" else [0.034, 0.070, 0.022], np.float32)
    bc = base * (0.82 + 0.18 * big[..., None]) * (0.95 + 0.05 * fine[..., None])
    vein_col = np.array([0.075, 0.105, 0.040], np.float32)
    vm = np.clip(mid + 0.65 * sec + 0.25 * tert, 0, 1)[..., None]
    bc = bc * (1 - 0.6 * vm) + vein_col * 0.6 * vm
    edge = np.zeros_like(u)
    if inside.any():
        dist = tp.blur(inside.astype(np.float32), 6)
        edge = sstep(0.75, 0.45, dist) * inside
        bc = bc * (1 - 0.5 * edge[..., None]) + np.array([0.11, 0.10, 0.025]) * 0.5 * edge[..., None]
    spots = sstep(2.9, 3.3, pnoise(rng, n, n, 2.5))
    bc = bc * (1 - 0.7 * spots[..., None]) + np.array([0.07, 0.045, 0.02]) * 0.7 * spots[..., None]
    height = 0.00025 * (1 - mid) * (1 - 0.6 * sec) - 0.00006 * tert + 0.00002 * fine
    rough = np.clip((0.34 if kind == "pear" else 0.42) + 0.08 * vm[..., 0] + 0.05 * big + 0.25 * spots, 0.2, 0.9)
    ao = np.ones((n, n), np.float32)
    bc = np.where(inside[..., None], bc, base * 0.7)
    tiling_set(name, (1.0, 1.0), dict(bc=bc.astype(np.float32), rough=rough.astype(np.float32), metal=np.zeros((n, n), np.float32),
                                      height=height.astype(np.float32), ao=ao),
               meta=dict(surface="leaf", note="one leaf over 0..1 (petiole at v 0); meshes are cut to the outline: "
                         "two-sided foliage, subsurface colour #6f8f2a, opaque (Nanite foliage)"))


def cardboard_set(force=False, n=1024):
    """Single-wall corrugated kraft board, 0.6 m tile: fibre mottle, the flutes showing through every 7 mm as
    faint ridges along u, scuffs, a water tide-mark. Printing is a decal."""
    if have("TS_Cardboard_Kraft") and not force:
        return
    rng = np.random.default_rng(31)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    tile = 0.6
    y_m = yy / n * tile
    flute = 0.5 + 0.5 * np.cos(2 * np.pi * y_m / (tile / round(tile / 0.0072)))
    mott = fbm(rng, n, n, 18, 4)
    fib = pnoise(rng, n, n, 0.8, aniso=(1.0, 3.5))
    scuff = sstep(1.6, 2.6, fbm(rng, n, n, 6, 3, aniso=(1.0, 0.25)))
    tide = sstep(0.05, 0.0, np.abs(fbm(rng, n, n, 70, 2) - 0.9)) * 0.6
    base = np.array([0.255, 0.165, 0.085], np.float32)
    bc = base * (0.9 + 0.08 * mott[..., None] + 0.04 * fib[..., None] + 0.03 * flute[..., None])
    bc = bc * (1 - 0.18 * scuff[..., None]) + np.array([0.42, 0.33, 0.22]) * 0.18 * scuff[..., None]
    bc = bc * (1 - 0.35 * tide[..., None])
    height = 0.00018 * flute + 0.00003 * fib - 0.00008 * scuff
    rough = np.clip(0.86 + 0.04 * mott - 0.06 * scuff, 0.6, 1.0)
    tiling_set("TS_Cardboard_Kraft", (tile, tile), dict(bc=bc.astype(np.float32), rough=rough.astype(np.float32),
                                                        metal=np.zeros((n, n), np.float32), height=height.astype(np.float32)),
               meta=dict(surface="cardboard", note="flutes run along u"))


def stainless_set(force=False, n=1024):
    """Brushed (#4) stainless sheet, 0.5 m tile: fine grain along u, handling smudges, water spots."""
    if have("TS_Steel_Stainless") and not force:
        return
    rng = np.random.default_rng(41)
    grain = pnoise(rng, n, n, 0.7, aniso=(0.02, 1.0))             # long along x (u)
    grain2 = pnoise(rng, n, n, 2.0, aniso=(0.05, 1.0))
    smudge = sstep(0.6, 1.8, fbm(rng, n, n, 40, 3))
    spots = sstep(2.8, 3.4, pnoise(rng, n, n, 3.0))
    lum_ = 0.56 + 0.025 * grain + 0.015 * grain2 - 0.04 * smudge
    bc = np.stack([lum_, lum_ * 0.99, lum_ * 0.97], -1)
    bc = bc * (1 - 0.25 * spots[..., None]) + np.array([0.62, 0.60, 0.55]) * 0.25 * spots[..., None]
    rough = np.clip(0.30 + 0.06 * grain2 + 0.12 * smudge + 0.15 * spots, 0.12, 0.8)
    height = 0.000015 * grain + 0.00001 * grain2
    tiling_set("TS_Steel_Stainless", (0.5, 0.5), dict(bc=bc.astype(np.float32), rough=rough.astype(np.float32),
                                                      metal=np.ones((n, n), np.float32), height=height.astype(np.float32)),
               meta=dict(surface="stainless", note="brushing along u: anisotropy 0.6 along the tangent in engine"))


def draw_sets(force=False):
    bark_set(force)
    leaf_set("pear", force)
    leaf_set("privet", force)
    cardboard_set(force)
    stainless_set(force)


# ================================================================================================ face helpers

def grime(cv, seed, amount=1.0, streaks=0.5, edge=0.6):
    """Weathering in the texpaint style: noise on the face's metres (mi.texpaint.Noise), dirt toward the edges and
    the bottom, rain streaks from the top. Returns a roughness offset."""
    N = tp.Noise(seed)
    p = np.stack([cv.x.ravel(), cv.y.ravel(), np.zeros(cv.x.size)], 1)
    big = N.fbm(p, 6.0, 3).reshape(cv.H, cv.W)
    st = N.fbm(p, (40.0, 1.2, 1.0), 3, octave0=8).reshape(cv.H, cv.W)
    ed = np.minimum(np.minimum(cv.x, cv.wm - cv.x), np.minimum(cv.y, cv.hm - cv.y))
    m = amount * (0.10 + 0.25 * (big + 1) / 2 * edge * sstep(0.08 * max(cv.wm, cv.hm), 0.0, ed)
                  + 0.25 * streaks * sstep(0.55, 0.9, st) * (cv.y / cv.hm))
    m = np.clip(m, 0, 1)
    cv.put(m, (0.17, 0.145, 0.115), 0.55)
    return 0.15 * m


def face(key, w, h, px_w, bg, draw, emis=None, rough=0.45, age=1.0, alpha=False, meta=None, grime_amt=1.0, top_fade=0.22,
         metal=None):
    """Canvas w x h metres at px_w pixels across; draw(cv) paints it (and may return an emission image)."""
    k = px_w / w
    cv = S.Canvas(w, h, k, paint(bg) if isinstance(bg, str) else bg)
    rng = np.random.default_rng(zlib.crc32(key.encode()))
    e = draw(cv, rng)
    r = S.weather_face(cv, rng, age=age, top_fade=top_fade, grime=0.2) if age else np.zeros((cv.H, cv.W), np.float32)
    if grime_amt:
        r = r + grime(cv, zlib.crc32(key.encode()) % 997, grime_amt)
    rough = np.clip(rough + r, 0.03, 1.0)
    size = (cv.W, cv.H)
    m = dict(face_m=[w, h], drawn_by="assets/_gaps_art.py")
    m.update(meta or {})
    if emis is not None or e is not None:
        m.setdefault("emissive_day", 0.3)
    return S.write_set(key, cv, size, rough, emis=e if e is not None else emis, meta=m, alpha=alpha, metal=metal)


def txt(cv, s, cap, cx, cy, col, fk="heavy", cond=1.0, max_w=None, align="c", track=0.0, op=1.0):
    m, wd, _ = cv.text(s, fk, cap, cx, cy, cond=cond, track=track, max_w=max_w, align=align)
    cv.put(m, paint(col) if isinstance(col, str) else col, op)
    return m, wd


def rect(cv, x0, y0, x1, y1, col, r=0.0, outline=None, op=1.0):
    m = cv.rect(x0, y0, x1, y1, r, outline)
    cv.put(m, paint(col) if isinstance(col, str) else col, op)
    return m


def arrow(cv, x0, y, x1, col, head=0.02, w=0.006, both=False):
    def f(d, k):
        d.line([(x0 * k, y * k), (x1 * k, y * k)], fill=255, width=max(1, int(w * k)))
        s = 1 if x1 > x0 else -1
        d.polygon([(x1 * k, y * k), ((x1 - s * head) * k, (y - head * 0.6) * k), ((x1 - s * head) * k, (y + head * 0.6) * k)], fill=255)
        if both:
            d.polygon([(x0 * k, y * k), ((x0 + s * head) * k, (y - head * 0.6) * k), ((x0 + s * head) * k, (y + head * 0.6) * k)], fill=255)
    cv.put(cv.draw(f), paint(col))


def greek(cv, x0, y0, x1, y1, line=0.006, gap=0.004, col="#2a2a2c", seed=0, op=0.85):
    """Lines of small grey 'words' standing for body text."""
    rng = np.random.default_rng(seed)

    def f(d, k):
        y = y0
        while y + line <= y1:
            x = x0
            end = x1 - (rng.uniform(0, (x1 - x0) * 0.5) if rng.random() < 0.15 else 0)
            while x < end:
                wd = rng.uniform(0.008, 0.03) * line / 0.006
                d.rectangle([x * k, y * k, min(x + wd, end) * k, (y + line * 0.75) * k], fill=255)
                x += wd + line * 0.5
            y += line + gap
    cv.put(cv.draw(f), paint(col), op)


def grommets(cv, pts, r=0.012):
    def f(d, k):
        for x, y in pts:
            d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=255)
    ring = cv.draw(f)

    def g(d, k):
        for x, y in pts:
            d.ellipse([(x - r * 0.55) * k, (y - r * 0.55) * k, (x + r * 0.55) * k, (y + r * 0.55) * k], fill=255)
    hole = cv.draw(g)
    cv.put(ring, (0.62, 0.60, 0.55))
    cv.put(hole, (0.03, 0.03, 0.03))


def barcode(cv, x0, y0, x1, y1, seed):
    rng = np.random.default_rng(seed)

    def f(d, k):
        x = x0
        while x < x1:
            bw = rng.choice([1, 1, 2, 3]) * (x1 - x0) / 95
            if rng.random() < 0.55:
                d.rectangle([x * k, y0 * k, (x + bw) * k, y1 * k], fill=255)
            x += bw
    cv.put(cv.draw(f), (0.03, 0.03, 0.035))


# ================================================================================================ the faces

def furniture_faces():
    # parking meter dial window, 0.10 x 0.15: white dial, red violation flag, 1 HR scale, 25 cents
    def meter(cv, rng):
        rect(cv, 0.0, 0.0, 0.10, 0.15, "#1c1d20")
        rect(cv, 0.008, 0.012, 0.092, 0.105, "#e6e4dc", r=0.01)
        def f(d, k):
            cx, cy, r = 0.05 * k, 0.085 * k, 0.034 * k
            d.pieslice([cx - r, cy - r, cx + r, cy + r], 200, 340, fill=255)
        cv.put(cv.draw(f), paint("#c2261e"))
        txt(cv, "EXPIRED", 0.006, 0.05, 0.072, "#e6e4dc", "bold")
        for i, a in enumerate(np.linspace(200, 340, 7)):
            x = 0.05 + 0.04 * math.cos(math.radians(a))
            y = 0.085 + 0.04 * math.sin(math.radians(a))
            rect(cv, x - 0.0008, y - 0.0008, x + 0.0008, y + 0.0008, "#2a2a2c")
        def needle(d, k):
            d.line([(0.05 * k, 0.085 * k), ((0.05 - 0.03) * k, (0.085 - 0.018) * k)], fill=255, width=max(1, int(0.0018 * k)))
        cv.put(cv.draw(needle), paint("#2a2a2c"))
        txt(cv, "1 HR", 0.007, 0.05, 0.097, "#2a2a2c", "bold")
        txt(cv, "25¢", 0.011, 0.05, 0.128, "#e6e4dc", "heavy")
        txt(cv, "NICKELS DIMES QUARTERS", 0.0028, 0.05, 0.142, "#9a9aa2", "medium", max_w=0.085)
    face("MeterDial", 0.10, 0.15, 256, "#1c1d20", meter, rough=0.25, age=0.6)

    # newspaper front page behind the glass, 0.33 x 0.41
    def paper(cv, rng):
        rect(cv, 0.0, 0.0, 0.33, 0.41, "#e6e1d2")
        txt(cv, "QUEENS NIGHT LEDGER", 0.024, 0.165, 0.032, "#16161a", "heavy", cond=0.78, max_w=0.31)
        rect(cv, 0.01, 0.052, 0.32, 0.054, "#2a2a2c")
        txt(cv, "THURSDAY, JULY 20, 2000   ·   50¢   ·   LATE CITY FINAL", 0.0042, 0.165, 0.060, "#2a2a2c", "medium", max_w=0.31)
        rect(cv, 0.01, 0.066, 0.32, 0.0665, "#2a2a2c")
        txt(cv, "THREE REELS", 0.05, 0.165, 0.105, "#111114", "heavy", cond=0.74, max_w=0.31)
        txt(cv, "GONE", 0.07, 0.165, 0.178, "#111114", "heavy", cond=0.74, max_w=0.31)
        txt(cv, "Masters vanish from Hollis studio; label offers reward", 0.0075, 0.165, 0.226, "#2a2a2c", "semi", max_w=0.31)
        ph = rect(cv, 0.012, 0.24, 0.19, 0.37, "#808080")
        n = S.vnoise(rng, cv.H, cv.W, cv.k * 0.03)
        dots = ((np.sin(cv.x * 2600) * np.sin(cv.y * 2600)) * 0.5 + 0.5 < n).astype(np.float32)
        cv.put(ph * dots, (0.07, 0.07, 0.075))
        txt(cv, "Police at the scene on Hollis Av. Wednesday night.", 0.0035, 0.10, 0.378, "#2a2a2c", "medium", max_w=0.18)
        greek(cv, 0.20, 0.243, 0.318, 0.40, seed=3)
        greek(cv, 0.012, 0.386, 0.19, 0.405, seed=4)
    face("Newspaper", 0.33, 0.41, 768, "#e6e1d2", paper, rough=0.8, age=1.4, top_fade=0.35)

    # mail label plate 0.36 x 0.27: navy band, MAIL, collection times
    def mail(cv, rng):
        rect(cv, 0.0, 0.0, 0.36, 0.27, "#f1efe6", r=0.012)
        rect(cv, 0.0, 0.0, 0.36, 0.11, "#16264f", r=0.012)
        rect(cv, 0.0, 0.05, 0.36, 0.11, "#16264f")
        txt(cv, "MAIL", 0.064, 0.18, 0.056, "#f1efe6", "heavy", cond=0.9)
        txt(cv, "LAST COLLECTION", 0.013, 0.18, 0.135, "#16264f", "bold")
        for i, (a, b) in enumerate((("MON – FRI", "5:00 PM"), ("SATURDAY", "1:00 PM"), ("SUN & HOLIDAYS", "NONE"))):
            y = 0.165 + i * 0.027
            txt(cv, a, 0.011, 0.03, y, "#16264f", "semi", align="l")
            txt(cv, b, 0.011, 0.33, y, "#16264f", "bold", align="r")
        rect(cv, 0.02, 0.15, 0.34, 0.1515, "#16264f")
        S.screws(cv, [(0.015, 0.015), (0.345, 0.015), (0.015, 0.255), (0.345, 0.255)], 0.004, 0.5)
    face("Mailbox", 0.36, 0.27, 512, "#f1efe6", mail, rough=0.35, age=1.0)

    # booth board PARK / 24 HOURS, gold on black, 1.6 x 0.56
    def park(cv, rng):
        rect(cv, 0.0, 0.0, 1.6, 0.56, "#0c0c0d")
        rect(cv, 0.025, 0.025, 1.575, 0.535, "#f6c21a", r=0.02, outline=0.008)
        txt(cv, "PARK", 0.26, 0.8, 0.22, "#f6c21a", "heavy", cond=0.86)
        txt(cv, "24 HOURS", 0.085, 0.8, 0.44, "#f6c21a", "heavy", cond=0.9, track=0.08)
        arrow(cv, 1.18, 0.22, 1.48, "#f6c21a", head=0.08, w=0.045)
        S.screws(cv, [(0.04, 0.05), (1.56, 0.05), (0.04, 0.51), (1.56, 0.51)], 0.007, 0.8)
    face("LotBooth", 1.6, 0.56, 1536, "#0c0c0d", park, rough=0.42, age=1.2)

    # tariff board 0.5 x 0.65
    def rates(cv, rng):
        rect(cv, 0.0, 0.0, 0.5, 0.65, "#f1efe6")
        rect(cv, 0.0, 0.0, 0.5, 0.12, "#0c0c0d")
        txt(cv, "RATES", 0.065, 0.25, 0.06, "#f6c21a", "heavy")
        rows = (("FIRST HOUR", "$6"), ("EACH ADD’L HOUR", "$3"), ("ALL NIGHT", "$14"), ("LOST TICKET", "$30"))
        for i, (a, b) in enumerate(rows):
            y = 0.17 + i * 0.075
            txt(cv, a, 0.024, 0.03, y, "#0c0c0d", "bold", align="l", max_w=0.33)
            txt(cv, b, 0.032, 0.47, y, "#0c0c0d", "heavy", align="r")
            rect(cv, 0.03, y + 0.033, 0.47, y + 0.0345, "#9a9aa2")
        rect(cv, 0.03, 0.5, 0.47, 0.57, "#c2261e")
        txt(cv, "NO IN & OUT", 0.032, 0.25, 0.535, "#f1efe6", "heavy")
        txt(cv, "NOT RESPONSIBLE FOR THEFT OR DAMAGE", 0.0105, 0.25, 0.605, "#2a2a2c", "semi", max_w=0.44)
        txt(cv, "RATES PLUS 18.375% PARKING TAX", 0.0105, 0.25, 0.627, "#2a2a2c", "semi", max_w=0.44)
        S.screws(cv, [(0.02, 0.02), (0.48, 0.02), (0.02, 0.63), (0.48, 0.63)], 0.005, 0.8)
    face("LotRates", 0.5, 0.65, 640, "#f1efe6", rates, rough=0.4, age=1.3)

    # vinyl shed banners 4.9 x 0.78 with grommets
    for key, field, ink, line1, line2 in (("ShedBanner_Chicken", "#f2c21a", "#c2261e", "GOLDEN BIRD CHICKEN", "FRIED · BBQ · WINGS · OPEN LATE"),
                                         ("ShedBanner_Liquor", "#0c0c0d", "#d42a24", "WINES & LIQUORS", "COLD BEER · LOTTO · ICE"),
                                         ("ShedBanner_Nails", "#3a0f2a", "#ff6fb4", "LUCKY NAILS", "MANICURE · PEDICURE · WALK-INS WELCOME")):
        def ban(cv, rng, field=field, ink=ink, line1=line1, line2=line2):
            rect(cv, 0.0, 0.0, 4.9, 0.78, field)
            rect(cv, 0.035, 0.035, 4.865, 0.745, ink, outline=0.012)
            txt(cv, line1, 0.34, 2.45, 0.32, ink, "heavy", cond=0.82, max_w=4.5)
            txt(cv, line2, 0.09, 2.45, 0.62, ink if field != "#f2c21a" else "#16161a", "bold", max_w=4.4, track=0.04)
            # creases from the folds in the box
            for xf in (1.22, 2.45, 3.67):
                cr = sstep(0.012, 0.0, np.abs(cv.x - xf - 0.01 * np.sin(cv.y * 9)))
                cv.put(cr, (0.9, 0.9, 0.9) if field == "#0c0c0d" else (0.1, 0.08, 0.06), 0.18)
            grommets(cv, [(x, y) for x in np.linspace(0.06, 4.84, 9) for y in (0.06, 0.72)])
        face(key, 4.9, 0.78, 2048, field, ban, rough=0.5, age=1.5, top_fade=0.35)

    # NO PARKING ANYTIME plate 0.32 x 0.44
    def nopark(cv, rng):
        rect(cv, 0.0, 0.0, 0.32, 0.44, "#f1efe6", r=0.012)
        rect(cv, 0.008, 0.008, 0.312, 0.432, "#c2261e", r=0.008, outline=0.006)
        txt(cv, "NO", 0.06, 0.16, 0.07, "#c2261e", "heavy")
        txt(cv, "PARKING", 0.05, 0.16, 0.16, "#c2261e", "heavy", cond=0.82, max_w=0.28)
        txt(cv, "ANYTIME", 0.04, 0.16, 0.24, "#c2261e", "heavy", cond=0.86, max_w=0.28)
        arrow(cv, 0.05, 0.34, 0.27, "#c2261e", head=0.04, w=0.014, both=True)
        S.screws(cv, [(0.16, 0.03), (0.16, 0.41)], 0.006, 0.9)
    face("SignPost", 0.32, 0.44, 384, "#f1efe6", nopark, rough=0.35, age=1.6)

    # bus-stop flag 0.26 x 0.36
    def flag(cv, rng):
        rect(cv, 0.0, 0.0, 0.26, 0.36, "#f1efe6", r=0.01)
        rect(cv, 0.0, 0.0, 0.26, 0.13, "#1f4f9a", r=0.01)
        rect(cv, 0.0, 0.06, 0.26, 0.13, "#1f4f9a")
        def bus(d, k):
            d.rounded_rectangle([0.06 * k, 0.03 * k, 0.20 * k, 0.095 * k], radius=0.01 * k, fill=255)
        cv.put(cv.draw(bus), paint("#f1efe6"))
        rect(cv, 0.07, 0.04, 0.19, 0.06, "#1f4f9a")
        for xw in (0.085, 0.175):
            def wh(d, k, xw=xw):
                d.ellipse([(xw - 0.011) * k, 0.087 * k, (xw + 0.011) * k, 0.109 * k], fill=255)
            cv.put(cv.draw(wh), paint("#16161a"))
        txt(cv, "BUS STOP", 0.038, 0.13, 0.17, "#1f4f9a", "heavy", cond=0.86, max_w=0.24)
        txt(cv, "NO", 0.026, 0.13, 0.235, "#c2261e", "heavy")
        txt(cv, "STANDING", 0.026, 0.13, 0.275, "#c2261e", "heavy", cond=0.86, max_w=0.24)
        txt(cv, "Q2  Q3  Q110", 0.017, 0.13, 0.33, "#16161a", "bold")
    face("BusFlag", 0.26, 0.36, 384, "#f1efe6", flag, rough=0.35, age=1.4)

    # street-name blade 0.60 x 0.17 (default JAMAICA AV), retroreflective green, white border
    def blade(cv, rng):
        rect(cv, 0.0, 0.0, 0.60, 0.17, "#1f5a3a", r=0.012)
        rect(cv, 0.008, 0.008, 0.592, 0.162, "#f1efe6", r=0.008, outline=0.005)
        txt(cv, "JAMAICA AV", 0.068, 0.315, 0.085, "#f1efe6", "bold", cond=0.88, max_w=0.50)
        txt(cv, "188", 0.018, 0.022, 0.035, "#f1efe6", "bold", align="l")
    face("StreetBlade", 0.60, 0.17, 768, "#1f5a3a", blade, rough=0.3, age=1.2,
         meta=dict(note="both faces; retroreflective sheeting"))


def new_faces():
    # phone head band 0.90 x 0.22: PHONE white on blue, lit
    def head(cv, rng):
        rect(cv, 0.0, 0.0, 0.90, 0.22, "#1f4f9a")
        rect(cv, 0.0, 0.0, 0.90, 0.018, "#0f2245")
        rect(cv, 0.0, 0.202, 0.90, 0.22, "#0f2245")
        m, _ = txt(cv, "PHONE", 0.11, 0.45, 0.112, "#e9f1ff", "heavy", track=0.12)
        e = np.zeros((cv.H, cv.W, 3), np.float32) + S.to_lin(S.rgb("#1f4f9a")) * 0.6
        e = e * (1 - m[..., None]) + S.to_lin(S.rgb("#e9f1ff")) * m[..., None] * 1.6
        e[(cv.y < 0.018) | (cv.y > 0.202)] = 0.0
        return e
    face("PhoneHead", 0.90, 0.22, 1024, "#1f4f9a", head, rough=0.2, age=1.0, meta=dict(emissive_day=0.25))

    # instruction card and coin plate on the phone, 0.30 x 0.20
    def card(cv, rng):
        rect(cv, 0.0, 0.0, 0.30, 0.20, "#e9e7df")
        rect(cv, 0.0, 0.0, 0.30, 0.04, "#1f4f9a")
        txt(cv, "PUBLIC TELEPHONE", 0.017, 0.15, 0.02, "#e9f1ff", "bold", track=0.05)
        rows = (("LOCAL CALL", "25¢"), ("EMERGENCY", "911  NO COIN"), ("OPERATOR", "0"), ("INFORMATION", "411"))
        for i, (a, b) in enumerate(rows):
            y = 0.06 + i * 0.026
            txt(cv, a, 0.0105, 0.015, y, "#16161a", "bold", align="l")
            txt(cv, b, 0.0105, 0.285, y, "#16161a", "heavy", align="r")
        txt(cv, "THIS PHONE: (718) 555-0142", 0.0085, 0.15, 0.17, "#2a2a2c", "semi")
        txt(cv, "REPAIR SERVICE  DIAL 611", 0.0085, 0.15, 0.188, "#2a2a2c", "semi")
    face("PhoneCard", 0.30, 0.20, 512, "#e9e7df", card, rough=0.35, age=1.2)

    # pedestrian signal 0.30 x 0.30 sections: orange raised hand and white walking person on black louvres
    def louvre(cv):
        rect(cv, 0.0, 0.0, cv.wm, cv.hm, "#0a0a0b")
        hon = ((np.sin(cv.x * 620) > 0.85) | (np.sin(cv.y * 620) > 0.85)).astype(np.float32)
        cv.put(hon, (0.05, 0.05, 0.055), 0.6)

    def hand(cv, rng):
        louvre(cv)
        def f(d, k):
            cx, cy = 0.15, 0.17
            d.rounded_rectangle([(cx - 0.055) * k, (cy - 0.02) * k, (cx + 0.05) * k, (cy + 0.085) * k], radius=0.03 * k, fill=255)
            for i, (dx, h) in enumerate(((-0.045, 0.085), (-0.018, 0.105), (0.01, 0.1), (0.037, 0.08))):
                d.rounded_rectangle([(cx + dx - 0.012) * k, (cy - h) * k, (cx + dx + 0.012) * k, cy * k], radius=0.012 * k, fill=255)
            d.rounded_rectangle([(cx + 0.03) * k, (cy - 0.0) * k, (cx + 0.09) * k, (cy + 0.025) * k], radius=0.012 * k, fill=255)
        m = cv.draw(f)
        dots = ((np.sin(cv.x * 900) * np.sin(cv.y * 900)) > -0.2).astype(np.float32)
        cv.put(m * (0.55 + 0.45 * dots), paint("#ff7a1a"))
        return np.ones((cv.H, cv.W, 1), np.float32) * (m * dots)[..., None] * S.to_lin(S.rgb("#ff7a1a")) * 2.0
    face("PedHand", 0.30, 0.30, 512, "#0a0a0b", hand, rough=0.15, age=0.5, grime_amt=0.6, meta=dict(emissive_day=0.4))

    def walk(cv, rng):
        louvre(cv)
        def f(d, k):
            cx = 0.15
            d.ellipse([(cx - 0.018) * k, 0.035 * k, (cx + 0.018) * k, 0.071 * k], fill=255)
            w = max(1, int(0.02 * k))
            d.line([(cx * k, 0.075 * k), (cx * k, 0.165 * k)], fill=255, width=w)
            d.line([(cx * k, 0.09 * k), ((cx - 0.04) * k, 0.14 * k)], fill=255, width=int(w * 0.8))
            d.line([(cx * k, 0.09 * k), ((cx + 0.04) * k, 0.13 * k)], fill=255, width=int(w * 0.8))
            d.line([(cx * k, 0.16 * k), ((cx - 0.045) * k, 0.26 * k)], fill=255, width=w)
            d.line([(cx * k, 0.16 * k), ((cx + 0.04) * k, 0.215 * k), ((cx + 0.055) * k, 0.26 * k)], fill=255, width=w)
        m = cv.draw(f)
        dots = ((np.sin(cv.x * 900) * np.sin(cv.y * 900)) > -0.2).astype(np.float32)
        cv.put(m * (0.5 + 0.5 * dots), paint("#e9f1ff"))
        return np.ones((cv.H, cv.W, 1), np.float32) * (m * dots)[..., None] * S.to_lin(S.rgb("#f4f6ff")) * 2.0
    face("PedWalk", 0.30, 0.30, 512, "#0a0a0b", walk, rough=0.15, age=0.5, grime_amt=0.6, meta=dict(emissive_day=0.4))

    # vending face 0.60 x 1.20: ICE COLD SODA on a blue-to-cyan field with bubbles, $1.00 tag (brandless)
    def vend(cv, rng):
        t = (cv.y / cv.hm)[..., None]
        a, b = paint("#0d3a8c"), paint("#35d0e0")
        cv.c = a * (1 - t) + b * t
        def bub(d, k):
            for _ in range(70):
                x, y, r = rng.uniform(0, 0.6), rng.uniform(0.35, 1.2), rng.uniform(0.006, 0.03)
                d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], outline=255, width=max(1, int(0.003 * k)))
        cv.put(cv.draw(bub), (0.85, 0.95, 1.0), 0.55)
        def swoosh(d, k):
            d.arc([-0.3 * k, 0.55 * k, 0.9 * k, 1.5 * k], 200, 330, fill=255, width=int(0.03 * k))
        cv.put(cv.draw(swoosh), (0.92, 0.97, 1.0), 0.7)
        txt(cv, "ICE", 0.11, 0.3, 0.11, "#e9f1ff", "heavyIt", track=0.04)
        txt(cv, "COLD", 0.11, 0.3, 0.25, "#e9f1ff", "heavyIt", track=0.04)
        txt(cv, "SODA", 0.11, 0.3, 0.39, "#f6c21a", "heavyIt", track=0.04)
        # three cans
        for i, col in enumerate(("#c2261e", "#1f5a3a", "#e9e7df")):
            x0 = 0.08 + i * 0.16
            rect(cv, x0, 0.62, x0 + 0.12, 0.93, col, r=0.02)
            rect(cv, x0, 0.62, x0 + 0.12, 0.64, "#c9ccd0", r=0.01)
            rect(cv, x0 + 0.01, 0.74, x0 + 0.11, 0.80, "#e9f1ff" if col != "#e9e7df" else "#0d3a8c", op=0.85)
            hl = sstep(0.02, 0.0, np.abs(cv.x - x0 - 0.03)) * (cv.y > 0.64) * (cv.y < 0.92)
            cv.put(hl, (1, 1, 1), 0.35)
        rect(cv, 0.36, 1.0, 0.56, 1.12, "#f6c21a", r=0.015)
        txt(cv, "$1.00", 0.05, 0.46, 1.06, "#16161a", "heavy", cond=0.9)
        txt(cv, "EXACT CHANGE", 0.016, 0.18, 1.06, "#e9f1ff", "bold")
        e = S.to_lin(np.clip(cv.c, 0, 1)) * 1.2
        return e
    face("Vending", 0.60, 1.20, 768, "#0d3a8c", vend, rough=0.12, age=1.0, meta=dict(emissive_day=0.35,
         note="back-lit polycarbonate face behind glass"))

    # generator label 0.62 x 0.32 (both flanks)
    def gen(cv, rng):
        rect(cv, 0.0, 0.0, 0.62, 0.32, "#f1efe6")
        rect(cv, 0.0, 0.0, 0.62, 0.10, "#c2261e")
        def oval(d, k):
            d.ellipse([0.14 * k, 0.015 * k, 0.48 * k, 0.085 * k], fill=255)
        cv.put(cv.draw(oval), paint("#f1efe6"))
        txt(cv, "DANGER", 0.045, 0.31, 0.05, "#c2261e", "heavy")
        txt(cv, "HIGH VOLTAGE", 0.05, 0.31, 0.15, "#16161a", "heavy", cond=0.86, max_w=0.58)
        txt(cv, "60 kW · 480 V · 3 PHASE", 0.028, 0.31, 0.215, "#16161a", "bold", max_w=0.58)
        txt(cv, "AUTHORIZED PERSONNEL ONLY  ·  KEEP DOORS CLOSED", 0.012, 0.31, 0.27, "#2a2a2c", "semi", max_w=0.58)
        txt(cv, "HOLLIS EQUIPMENT RENTAL  (718) 555-0188", 0.011, 0.31, 0.298, "#2a2a2c", "semi", max_w=0.58)
    face("GenLabel", 0.62, 0.32, 768, "#f1efe6", gen, rough=0.4, age=1.6)

    # portable toilet hire plate 0.30 x 0.22
    def plate(cv, rng):
        rect(cv, 0.0, 0.0, 0.30, 0.22, "#1f4f9a", r=0.015)
        txt(cv, "HOLLIS", 0.042, 0.15, 0.045, "#f1efe6", "heavy", track=0.04)
        txt(cv, "SITE SERVICES", 0.018, 0.15, 0.095, "#f1efe6", "bold", track=0.06)
        rect(cv, 0.03, 0.12, 0.27, 0.122, "#f1efe6")
        txt(cv, "UNIT 14", 0.026, 0.15, 0.155, "#f6c21a", "heavy")
        txt(cv, "(718) 555-0131", 0.014, 0.15, 0.195, "#f1efe6", "semi")
    face("PortaPlate", 0.30, 0.22, 512, "#1f4f9a", plate, rough=0.35, age=1.6)

    # food-cart menu board 1.5 x 0.52, red ground, yellow lettering
    def menu(cv, rng):
        rect(cv, 0.0, 0.0, 1.5, 0.52, "#c2261e")
        rect(cv, 0.02, 0.02, 1.48, 0.50, "#f2c21a", r=0.02, outline=0.01)
        txt(cv, "HOT DOGS", 0.12, 0.42, 0.12, "#f2c21a", "heavy", cond=0.84)
        txt(cv, "PRETZELS · COLD SODA", 0.045, 0.42, 0.235, "#f1efe6", "bold", max_w=0.75)
        for i, (a, b) in enumerate((("HOT DOG", "1.50"), ("SAUSAGE", "2.50"), ("PRETZEL", "1.25"), ("SODA", "1.00"))):
            y = 0.09 + i * 0.1
            txt(cv, a, 0.04, 0.88, y, "#f1efe6", "heavy", cond=0.9, align="l")
            txt(cv, b, 0.045, 1.44, y, "#f2c21a", "heavy", align="r")
        txt(cv, "KNISHES  ·  ONIONS  ·  KRAUT", 0.03, 0.42, 0.34, "#f2c21a", "bold", max_w=0.75)
        def dog(d, k):
            d.rounded_rectangle([0.18 * k, 0.40 * k, 0.66 * k, 0.47 * k], radius=0.035 * k, fill=255)
        cv.put(cv.draw(dog), paint("#e0a24a"))
        def wurst(d, k):
            d.rounded_rectangle([0.14 * k, 0.415 * k, 0.70 * k, 0.455 * k], radius=0.02 * k, fill=255)
        cv.put(cv.draw(wurst), paint("#8a2a16"))
        def mus(d, k):
            pts = [((0.17 + 0.03 * i) * k, (0.435 + 0.01 * (-1) ** i) * k) for i in range(18)]
            d.line(pts, fill=255, width=int(0.008 * k))
        cv.put(cv.draw(mus), paint("#f2c21a"))
    face("FoodCartMenu", 1.5, 0.52, 1536, "#c2261e", menu, rough=0.35, age=1.6, top_fade=0.4)

    # crate stencil 0.66 x 0.44 (black, sprayed, alpha = paint)
    def sten(cv, rng):
        m = np.zeros((cv.H, cv.W), np.float32)
        a, _, _ = cv.text("FRAGILE", "heavy", 0.09, 0.33, 0.075, cond=0.8)
        b, _, _ = cv.text("HANDLE WITH CARE", "bold", 0.038, 0.33, 0.17, max_w=0.6)
        c, _, _ = cv.text("LOT 0214 · QNS", "bold", 0.036, 0.33, 0.235, max_w=0.6)
        m = np.maximum.reduce([a, b, c])
        def ar(d, k):
            d.polygon([(0.33 * k, 0.27 * k), (0.27 * k, 0.33 * k), (0.31 * k, 0.33 * k), (0.31 * k, 0.43 * k),
                       (0.35 * k, 0.43 * k), (0.35 * k, 0.33 * k), (0.39 * k, 0.33 * k)], fill=255)
        m = np.maximum(m, cv.draw(ar))
        bridges = ((np.abs((cv.x * 1000) % 40 - 20) < 1.5) & (cv.y < 0.1)).astype(np.float32)
        m = m * (1 - bridges)
        over = tp.blur(m, cv.k * 0.004) * 0.35
        n = S.vnoise(rng, cv.H, cv.W, cv.k * 0.02)
        cov = np.clip(np.maximum(m * (0.75 + 0.35 * n), over * n), 0, 1)
        cv.c[:] = paint("#161310")
        cv.a = cov
    face("CrateStencil", 0.66, 0.44, 768, (0.08, 0.07, 0.06), sten, rough=0.7, age=0, grime_amt=0, alpha=True,
         meta=dict(note="decal card: BC alpha = paint (masked or translucent decal)"))

    # vulture crew stencil 0.5 x 0.4: a hunched vulture on a wire, bone white, sprayed
    def vul(cv, rng):
        def f(d, k):
            P = lambda pts: [(x * k, y * k) for x, y in pts]
            d.polygon(P([(0.17, 0.30), (0.12, 0.22), (0.14, 0.13), (0.22, 0.08), (0.30, 0.09), (0.36, 0.14), (0.40, 0.22),
                         (0.43, 0.31), (0.39, 0.32), (0.33, 0.28), (0.28, 0.31), (0.23, 0.32)]), fill=255)      # hunched wings
            d.polygon(P([(0.22, 0.09), (0.19, 0.04), (0.155, 0.03), (0.125, 0.05), (0.105, 0.075), (0.13, 0.07), (0.16, 0.06),
                         (0.18, 0.08)]), fill=255)                                                                   # neck and hooked beak
            d.ellipse(P([(0.145, 0.025), (0.19, 0.06)]), fill=255)
            d.polygon(P([(0.40, 0.25), (0.47, 0.33), (0.44, 0.34), (0.38, 0.29)]), fill=255)                     # tail
            for x in (0.24, 0.30):
                d.line(P([(x, 0.30), (x - 0.01, 0.345)]), fill=255, width=int(0.012 * k))                       # legs
            d.line(P([(0.0, 0.35), (0.5, 0.34)]), fill=255, width=int(0.008 * k))                               # the wire
        m = cv.draw(f)
        eye = cv.draw(lambda d, k: d.ellipse([0.150 * k, 0.038 * k, 0.162 * k, 0.050 * k], fill=255))
        m = np.clip(m - eye, 0, 1)
        feathers = ((np.sin((cv.x * 0.7 + cv.y) * 160) > 0.7) & (cv.y > 0.15) & (cv.y < 0.3)).astype(np.float32)
        m = m * (1 - 0.8 * feathers)
        n = S.vnoise(rng, cv.H, cv.W, cv.k * 0.015)
        over = tp.blur(m, cv.k * 0.006) * 0.4
        cv.c[:] = paint("#e9e4d6")
        cv.a = np.clip(np.maximum(m * (0.6 + 0.5 * n), over * n) * sstep(0.15, 0.4, n + 0.2), 0, 1)
    face("VultureStencil", 0.5, 0.4, 768, (0.9, 0.88, 0.84), vul, rough=0.6, age=0, grime_amt=0, alpha=True,
         meta=dict(note="crew stencil, sprayed and worn; decal card, BC alpha = paint"))

    # carton print 0.34 x 0.22: THIS SIDE UP, two arrows (alpha decal)
    def cprint(cv, rng):
        a, _, _ = cv.text("THIS SIDE UP", "bold", 0.03, 0.17, 0.035)
        def ar(d, k):
            for cx in (0.09, 0.25):
                d.polygon([(cx * k, 0.07 * k), ((cx - 0.04) * k, 0.12 * k), ((cx - 0.015) * k, 0.12 * k), ((cx - 0.015) * k, 0.2 * k),
                           ((cx + 0.015) * k, 0.2 * k), ((cx + 0.015) * k, 0.12 * k), ((cx + 0.04) * k, 0.12 * k)], fill=255)
        m = np.maximum(a, cv.draw(ar))
        n = S.vnoise(rng, cv.H, cv.W, cv.k * 0.01)
        cv.c[:] = paint("#1d1a18")
        cv.a = np.clip(m * (0.75 + 0.3 * n), 0, 1)
    face("CartonPrint", 0.34, 0.22, 512, (0.1, 0.1, 0.1), cprint, rough=0.8, age=0, grime_amt=0, alpha=True)

    # shipping label 0.15 x 0.10 with a barcode
    def label(cv, rng):
        rect(cv, 0.0, 0.0, 0.15, 0.10, "#f1efe6")
        txt(cv, "SHIP TO:", 0.005, 0.008, 0.01, "#16161a", "bold", align="l")
        greek(cv, 0.008, 0.018, 0.09, 0.045, line=0.004, gap=0.003, seed=9)
        rect(cv, 0.1, 0.008, 0.142, 0.045, "#16161a", outline=0.0015)
        txt(cv, "2", 0.025, 0.121, 0.027, "#16161a", "heavy")
        barcode(cv, 0.01, 0.055, 0.14, 0.085, 5)
        txt(cv, "1Z 4X7 019 03 5521 0846", 0.0035, 0.075, 0.093, "#16161a", "semi")
    face("CartonLabel", 0.15, 0.10, 384, "#f1efe6", label, rough=0.55, age=0.8)

    # barber pole: red, white and blue helix on 0..1 (u around, v up), glass-cylinder print; scrolls in engine
    def pole(cv, rng):
        u = cv.x / cv.wm
        v = 1 - cv.y / cv.hm
        ph = (u + v * 2.0) % 1.0
        red = (ph < 0.25).astype(np.float32)
        blue = ((ph >= 0.5) & (ph < 0.75)).astype(np.float32)
        aa = lambda m: tp.blur(m, 1.2)
        cv.c[:] = paint("#e9e7df")
        cv.put(aa(red), paint("#c2261e"))
        cv.put(aa(blue), paint("#1c2f5a"))
    face("BarberPole", 0.6, 0.6, 512, "#e9e7df", pole, rough=0.3, age=0.6, grime_amt=0.3, top_fade=0.0,
         meta=dict(note="u around the inner cylinder, v up: two turns of each colour; pan V at -0.25/s in engine to turn it"))


def draw_all(force=False):
    draw_sets(force)
    furniture_faces()
    new_faces()
