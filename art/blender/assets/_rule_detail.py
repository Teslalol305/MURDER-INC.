"""A tiling micro-detail normal map for the bare skin of SK_RuleArms (hands-and-tattoos pass).

The baked RuleArms_Skin normal map holds the forms (veins, tendons, knuckle wrinkles, creases) at about 1 mm per
texel on the forearm; the skin's own grain (pores, the criss-cross of skin lines, follicles) is finer than a texel and
read as a smooth tube at first-person distance (20-50 cm). This map is tiled over the UVs in Unreal
(M_RuleArms_Skin, DetailTiling) and blended onto the baked normal (DetailStrength), as the Goons' fabric detail.

    T_RuleArms_SkinDetail_N.png   1024 px, one tile = DETAIL_TILE_M of skin on the forearm (OpenGL, +Y up)

Every pattern is periodic over the tile (FFT-filtered noise, wrapped cell distances), so the tiling shows no seam.
"""
import os

import numpy as np

DETAIL_TILE_M = 0.024
RES = 1024


def _band_noise(rng, n, lo_px, hi_px):
    """Periodic noise with features between lo_px and hi_px (FFT band-pass of white noise), unit variance."""
    w = rng.standard_normal((n, n))
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    r = np.hypot(fx, fy) + 1e-9
    band = np.exp(-((np.log(r) - np.log(1.0 / np.sqrt(lo_px * hi_px))) / (0.5 * np.log(hi_px / lo_px) + 0.35)) ** 2)
    out = np.real(np.fft.ifft2(np.fft.fft2(w) * band))
    return (out - out.mean()) / (out.std() + 1e-9)


def _cells(rng, n, count):
    """Periodic Worley distances (F1, F2) to `count` random points over the tile, in pixels."""
    pts = rng.random((count, 2)) * n
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    f1 = np.full((n, n), 1e9, dtype=np.float32)
    f2 = np.full((n, n), 1e9, dtype=np.float32)
    for px, py in pts:
        dx = np.abs(x - px)
        dx = np.minimum(dx, n - dx)
        dy = np.abs(y - py)
        dy = np.minimum(dy, n - dy)
        d = np.sqrt(dx * dx + dy * dy)
        m = d < f1
        f2 = np.where(m, f1, np.minimum(f2, d))
        f1 = np.where(m, d, f1)
    return f1, f2


def height(seed=7, n=RES):
    """Height in metres over the tile: skin-line grooves (a 0.6-1.4 mm network), pores (0.10-0.18 mm pits) and a
    faint fine wrinkle grain. Depths are those of forearm skin: lines 10-20 um, pores about 25 um."""
    rng = np.random.default_rng(seed)
    px_m = DETAIL_TILE_M / n
    h = np.zeros((n, n), dtype=np.float64)
    # skin lines: the edges of a cell network about 1 mm across
    f1, f2 = _cells(rng, n, int((DETAIL_TILE_M / 0.0011) ** 2))
    edge = np.clip(1.0 - (f2 - f1) / 3.0, 0, 1) ** 2
    h -= 18e-6 * edge
    # a second, finer and shallower network (the triangles inside the large cells)
    g1, g2 = _cells(rng, n, int((DETAIL_TILE_M / 0.00045) ** 2))
    h -= 9e-6 * np.clip(1.0 - (g2 - g1) / 2.0, 0, 1) ** 2
    # pores: small pits at the cell nodes and scattered between, 0.10-0.18 mm
    p1, _ = _cells(rng, n, int((DETAIL_TILE_M / 0.00055) ** 2))
    r_px = 0.000065 / px_m
    h -= 26e-6 * np.exp(-(p1 / r_px) ** 2)
    # the skin's soft relief between the lines
    h += 6e-6 * _band_noise(rng, n, 8, 40)
    return h.astype(np.float32), px_m


def normal_map(h, px_m):
    """Tangent-space normal (OpenGL, +Y up) from a periodic height, as 8-bit RGB."""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) / (2 * px_m)
    dy = (np.roll(h, 1, axis=0) - np.roll(h, -1, axis=0)) / (2 * px_m)     # image rows run down, +Y is up
    nrm = np.stack([-dx, -dy, np.ones_like(h)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    return np.clip((nrm * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8)


def write(folder, seed=7):
    from PIL import Image
    os.makedirs(folder, exist_ok=True)
    h, px_m = height(seed)
    rgb = normal_map(h, px_m)
    p = os.path.join(folder, "T_RuleArms_SkinDetail_N.png")
    Image.fromarray(rgb, "RGB").save(p)
    return p, {"tile_m": DETAIL_TILE_M, "res": RES, "slope_p95": float(np.percentile(np.abs(rgb[..., 0].astype(int) - 128), 95))}


if __name__ == "__main__":
    import sys
    print(write(sys.argv[1] if len(sys.argv) > 1 else "."))
