#!/usr/bin/env python3
"""Measure what is in art/out and write the numbers back into art/scans/sets.json.

    python3 art/scans/calibrate.py [--only set ...] [--cards DIR] [--check]

For every tiling set (reads the convention files that fetch.py wrote):
  * px                real pixel size of the maps;
  * repeat            how many times the pattern repeats along x and along y, from the power spectrum of the
                      row and column profiles of the height map and of the base colour (courses, slats, ribs,
                      boards: the texture wraps, so a regular pattern must repeat a whole number of times);
  * tile_m            recomputed from the catalogue's own recipe ("basis": count x unit, or the publisher's
                      stated size checked against a feature of known size) and compared with what is written;
  * grain_mm          dominant blob size of the base colour (difference-of-Gaussians scale space), in
                      millimetres at the stated tile size: aggregate, grit, weave;
  * relief_mm         height-map amplitude in millimetres that agrees with the slopes stored in the normal
                      map at the stated tile size (least squares on the band-limited gradients);
  * seam              wrapped edge difference against interior neighbour differences, base colour and
                      height, both axes, at pixel scale and at band scale (1/32 of the tile);
  * albedo, roughness, metallic, ao   linear means, for a plausibility check against measured materials.
For every sky: sun direction, peak and mean radiance, the share of the light that comes from the sun disc.
For every model: bounding box in metres (Blender axes), triangle count, texture list, pivot offset.

--cards DIR writes one picture per tiling set (whole tile with a ruler in the recipe's unit, and a 1:1 crop
with a millimetre scale) for checking the scale by eye. --check changes nothing and exits non-zero when the
catalogue and the files disagree. Standard library, pillow and numpy only.
"""
import argparse
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch  # noqa: E402  (same folder: paths, the .hdr reader, the 16-bit PNG reader)

Image.MAX_IMAGE_PIXELS = None
OUT = fetch.OUT
CATALOGUE = fetch.CATALOGUE


# ------------------------------------------------------------------------------------------------ image helpers

def load_rgb(path):
    return np.asarray(Image.open(path).convert("RGB"), np.float32) / 255.0


def load_height(path):
    """Height map as float32 in 0..1, whatever the PNG's depth."""
    with open(path, "rb") as f:
        head = f.read(33)
    depth, ctype = head[24], head[25]
    if depth == 16 and ctype == 0:
        return np.asarray(Image.open(path), np.float32) / 65535.0
    if depth == 16:
        return fetch.read_png(path)[..., 0].astype(np.float32) / 65535.0
    return np.asarray(Image.open(path).convert("L"), np.float32) / 255.0


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def luminance(rgb_linear):
    return rgb_linear @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def gaussian_fft(shape, sigma):
    """Transfer function of a Gaussian blur with periodic boundaries (exactly what a tiling texture needs)."""
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.rfftfreq(shape[1])[None, :]
    return np.exp(-2.0 * (math.pi * sigma) ** 2 * (fx * fx + fy * fy)).astype(np.float32)


# ---------------------------------------------------------------------------------------------------- measures

def repeat_counts(img, top=3):
    """Strongest whole-number repeat counts of the pattern along x and along y.

    The profile along an axis (the image averaged across the other axis) of a regular pattern that wraps is a
    periodic signal with a whole number of periods, so its power spectrum has a peak at that number.
    Returns {"x": [[count, share], ...], "y": [...]}, share = that peak's part of the profile's variance.
    """
    out = {}
    for name, axis in (("x", 0), ("y", 1)):
        prof = img.mean(axis=axis).astype(np.float64)
        prof -= prof.mean()
        power = np.abs(np.fft.rfft(prof)) ** 2
        power[0] = 0.0
        total = power.sum() or 1.0
        hi = min(len(power) - 1, len(prof) // 6)  # a feature narrower than 6 px is not a repeat we can trust
        order = np.argsort(power[2:hi + 1])[::-1][:top] + 2
        out[name] = [[int(k), round(float(power[k] / total), 3)] for k in order]
    return out


def grain_px(lum):
    """Dominant blob diameter in pixels: the scale where the difference-of-Gaussians energy peaks."""
    spec = np.fft.rfft2(lum - lum.mean())
    sigmas = [1.0 * 2 ** (i / 2.0) for i in range(0, 13)]  # 1 .. 64 px
    blur = [gaussian_fft(lum.shape, s) for s in sigmas]
    n = lum.size
    energy = []
    for a, b in zip(blur[:-1], blur[1:]):
        band = spec * (a - b)
        # Parseval for the half spectrum: every bin but the first and last column counts twice
        p = np.abs(band) ** 2
        e = (2 * p.sum() - p[:, 0].sum() - (p[:, -1].sum() if lum.shape[1] % 2 == 0 else 0)) / (n * n)
        energy.append(float(e))
    i = int(np.argmax(energy))
    if 0 < i < len(energy) - 1:  # parabolic refinement in log scale
        a, b, c = energy[i - 1], energy[i], energy[i + 1]
        shift = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
    else:
        shift = 0.0
    sigma = sigmas[0] * 2 ** ((i + shift) / 2.0) * 2 ** 0.25  # centre of the band between sigma and sigma*sqrt2
    return 2.0 * math.sqrt(2.0) * sigma, [round(e / max(energy), 3) for e in energy]


def relief_fraction(height, normal):
    """Height amplitude, as a fraction of the tile width, at which the height map's slopes match the normal map.

    The normal map stores slopes: dz/dx = -nx/nz, dz/dy = -ny/nz (OpenGL convention, +Y up in the image).
    If z = A * h with h in 0..1 and x in pixels, then A [px] is the least-squares factor between the two
    gradient fields. Both are band-limited (2 px blur) so that sharp detail present in only one of them does
    not decide the answer. Returns (A / width, correlation).
    """
    n = normal * 2.0 - 1.0
    nz = np.clip(n[..., 2], 0.05, None)
    sx = -n[..., 0] / nz
    sy = n[..., 1] / nz  # image rows run downwards, the green channel points up
    g = gaussian_fft(height.shape, 2.0)
    hs = np.fft.irfft2(np.fft.rfft2(height) * g, s=height.shape)
    hx = (np.roll(hs, -1, axis=1) - np.roll(hs, 1, axis=1)) * 0.5
    hy = (np.roll(hs, -1, axis=0) - np.roll(hs, 1, axis=0)) * 0.5
    sx = np.fft.irfft2(np.fft.rfft2(sx) * g, s=height.shape)
    sy = np.fft.irfft2(np.fft.rfft2(sy) * g, s=height.shape)
    num = float((hx * sx).sum() + (hy * sy).sum())
    den = float((hx * hx).sum() + (hy * hy).sum())
    if den <= 0:
        return 0.0, 0.0
    amp_px = num / den
    corr = num / math.sqrt(den * float((sx * sx).sum() + (sy * sy).sum()) + 1e-30)
    return amp_px / height.shape[1], corr


def seam_measure(img):
    """How the wrapped edge compares with ordinary neighbours, per axis.

    pixel: mean absolute difference between the last and the first column (row) divided by the median of the
           same difference between adjacent interior columns (rows); "rank" is the share of interior pairs that
           differ less than the wrapped pair (1.0 = the seam is the worst line in the image).
    band:  the same with the image averaged into 32 bands, which catches a brightness step or gradient that a
           pixel-level blend hides.
    """
    a = img if img.ndim == 3 else img[..., None]
    out = {}
    for name, axis in (("x", 1), ("y", 0)):
        m = np.moveaxis(a, axis, 0)
        d = np.abs(np.roll(m, -1, axis=0) - m).mean(axis=(1, 2))  # d[-1] is the wrapped pair
        wrap, inner = float(d[-1]), d[:-1]
        med = float(np.median(inner)) or 1e-9
        bands = m.reshape(32, m.shape[0] // 32, *m.shape[1:]).mean(axis=1) if m.shape[0] % 32 == 0 else \
            np.stack([c.mean(axis=0) for c in np.array_split(m, 32, axis=0)])
        bd = np.abs(np.roll(bands, -1, axis=0) - bands).mean(axis=(1, 2))
        bmed = float(np.median(bd[:-1])) or 1e-9
        out[name] = {"pixel": round(wrap / med, 2), "rank": round(float((inner < wrap).mean()), 3),
                     "band": round(float(bd[-1]) / bmed, 2), "band_rank": round(float((bd[:-1] < bd[-1]).mean()), 3)}
    return out


def seam_verdict(seams):
    """"ok", or a short description of what shows."""
    notes = []
    for mapname, s in seams.items():
        for axis in ("x", "y"):
            v = s[axis]
            if v["pixel"] > 1.6 and v["rank"] > 0.995:
                notes.append(f"{mapname} {axis}: hard seam ({v['pixel']}x a normal neighbour)")
            elif v["band"] > 3.0 and v["band_rank"] >= 0.97:
                notes.append(f"{mapname} {axis}: tone step across the wrap ({v['band']}x a normal band step)")
    return "ok" if not notes else "; ".join(notes)


# ------------------------------------------------------------------------------------------------ texture sets

def tile_from_basis(entry, px):
    """Tile size in metres from the catalogue's own recipe. Returns ([x, y], text) or (None, why)."""
    basis = entry.get("basis") or {}
    w, h = px
    if basis.get("kind") == "count":
        size = {}
        for axis in ("x", "y"):
            b = basis.get(axis)
            if b:
                size[axis] = b["count"] * b["unit_mm"] / 1000.0
        if not size:
            return None, "count basis without an axis"
        # an axis without its own count keeps the pixels square
        if "x" not in size:
            size["x"] = size["y"] * w / h
        if "y" not in size:
            size["y"] = size["x"] * h / w
        return [round(size["x"], 3), round(size["y"], 3)], "count"
    if basis.get("kind") == "stated":
        m = basis["stated_m"]
        return [round(m, 3), round(m * h / w, 3)], "stated"
    return None, "no basis"


def measure_texture(entry):
    files = {role: OUT / spec["out"] for role, spec in entry["files"].items()}
    bc = load_rgb(files["BC"])
    h, w = bc.shape[:2]
    lin = srgb_to_linear(bc)
    lum = luminance(lin)
    m = {"px": [w, h]}
    height = load_height(files["H"]) if "H" in files and files["H"].is_file() else None
    with open(files["H"], "rb") as f:
        head = f.read(33)
    m["height_bits"] = head[24]
    tile, _ = tile_from_basis(entry, (w, h))
    tile = tile or entry.get("tile_m")
    m["repeat"] = {"base_colour": repeat_counts(luminance(bc))}
    if height is not None:
        m["repeat"]["height"] = repeat_counts(height)
    g, curve = grain_px(luminance(bc))
    m["grain_px"] = round(g, 1)
    if tile:
        m["grain_mm"] = round(g / w * tile[0] * 1000.0, 1)
        m["px_per_m"] = round(w / tile[0])
    if height is not None and "N" in files:
        nrm = load_rgb(files["N"])
        frac, corr = relief_fraction(height, nrm)
        m["relief_fit"] = round(corr, 2)
        if tile:
            m["relief_mm"] = round(frac * tile[0] * 1000.0, 1)
        nz = nrm[..., 2].mean()
        m["normal_mean"] = [round(float(v), 3) for v in nrm.reshape(-1, 3).mean(axis=0)]
    seams = {"base_colour": seam_measure(bc)}
    if height is not None:
        seams["height"] = seam_measure(height)
    m["seam"] = seams
    m["seam_verdict"] = seam_verdict(seams)
    orm = load_rgb(files["ORM"])
    mean_lin = lin.reshape(-1, 3).mean(axis=0)
    p5, p95 = np.percentile(lum, [5, 95])
    m["albedo"] = {"linear_rgb": [round(float(v), 3) for v in mean_lin], "luminance": round(float(lum.mean()), 3),
                   "p5": round(float(p5), 3), "p95": round(float(p95), 3)}
    m["ao"] = round(float(orm[..., 0].mean()), 3)
    m["roughness"] = round(float(orm[..., 1].mean()), 3)
    m["metallic"] = round(float(orm[..., 2].mean()), 3)
    return m


# -------------------------------------------------------------------------------------------------------- skies

def measure_hdri(entry, res="2k"):
    path = OUT / fetch.remote(entry["files"]["HDR"]["out"], res)
    img = fetch.read_hdr(path)
    h, w = img.shape[:2]
    lum = luminance(img)
    theta = (np.arange(h) + 0.5) / h * math.pi  # 0 at the zenith
    solid = (2 * math.pi / w) * (math.pi / h) * np.sin(theta)[:, None] * np.ones((1, w))
    y, x = np.unravel_index(int(np.argmax(lum)), lum.shape)
    peak = float(lum[y, x])
    # the sun: everything within 3 degrees of the brightest pixel, weighted by luminance
    phi = (np.arange(w) + 0.5) / w * 2 * math.pi
    dirs = np.stack([np.sin(theta)[:, None] * np.cos(phi)[None, :], np.sin(theta)[:, None] * np.sin(phi)[None, :],
                     np.cos(theta)[:, None] * np.ones((1, w))], axis=-1)
    d0 = dirs[y, x]
    near = (dirs @ d0) > math.cos(math.radians(3.0))
    wgt = (lum * solid)[near]
    centre = (dirs[near] * wgt[:, None]).sum(axis=0)
    centre /= np.linalg.norm(centre)
    elev = math.degrees(math.asin(float(centre[2])))
    # equirect u = 0.5 is Blender's -Y for an unrotated Environment Texture; u grows towards... see README
    u = (math.atan2(float(centre[1]), float(centre[0])) / (2 * math.pi)) % 1.0
    cosz = np.clip(np.cos(theta), 0, None)[:, None]
    e_total = float((lum * solid * cosz).sum())
    e_sun = float(((lum * solid * cosz))[near].sum())
    upper = lum[: h // 2]
    return {
        "px": [w, h],
        "sun_uv": [round(u, 4), round((y + 0.5) / h, 4)],
        "sun_elevation_deg": round(elev, 1),
        "peak_radiance": round(peak, 1),
        "sky_mean_radiance": round(float((upper * solid[: h // 2]).sum() / solid[: h // 2].sum()), 3),
        "ground_mean_radiance": round(float((lum[h // 2:] * solid[h // 2:]).sum() / solid[h // 2:].sum()), 3),
        "horizontal_irradiance": round(e_total, 2),
        "sun_share_of_irradiance": round(e_sun / e_total, 3) if e_total else 0.0,
        "mean_rgb": [round(float(v), 3) for v in (img * solid[..., None]).sum(axis=(0, 1)) / solid.sum()],
    }


# ------------------------------------------------------------------------------------------------------- models

COMPONENT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def gltf_accessor(doc, buffers, index):
    acc = doc["accessors"][index]
    view = doc["bufferViews"][acc["bufferView"]]
    dtype = np.dtype(COMPONENT[acc["componentType"]])
    n = WIDTH[acc["type"]]
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = view.get("byteStride") or dtype.itemsize * n
    raw = buffers[view["buffer"]]
    if stride == dtype.itemsize * n:
        arr = np.frombuffer(raw, dtype, acc["count"] * n, start).reshape(acc["count"], n)
    else:
        arr = np.ndarray((acc["count"], n), dtype, raw, start, (stride, dtype.itemsize))
    return arr


def node_matrix(node):
    if "matrix" in node:
        return np.array(node["matrix"], np.float64).reshape(4, 4).T
    t = np.array(node.get("translation", [0, 0, 0]), np.float64)
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    s = np.array(node.get("scale", [1, 1, 1]), np.float64)
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r * s[None, :]
    m[:3, 3] = t
    return m


def measure_model(entry, res="2k"):
    folder = OUT / fetch.remote(entry["files"]["GLTF"]["out"], res)
    gltf = folder / Path(fetch.remote(entry["files"]["GLTF"]["src"], res)).name
    doc = json.loads(gltf.read_text())
    buffers = [(folder / b["uri"]).read_bytes() for b in doc["buffers"]]
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    tris = verts = 0
    parts = []

    def walk(index, parent):
        nonlocal lo, hi, tris, verts
        node = doc["nodes"][index]
        world = parent @ node_matrix(node)
        if "mesh" in node:
            mesh = doc["meshes"][node["mesh"]]
            plo, phi = np.full(3, np.inf), np.full(3, -np.inf)
            for prim in mesh["primitives"]:
                pos = gltf_accessor(doc, buffers, prim["attributes"]["POSITION"]).astype(np.float64)
                p = pos @ world[:3, :3].T + world[:3, 3]
                plo, phi = np.minimum(plo, p.min(axis=0)), np.maximum(phi, p.max(axis=0))
                verts += len(pos)
                if prim.get("mode", 4) == 4:
                    tris += (doc["accessors"][prim["indices"]]["count"] if "indices" in prim else len(pos)) // 3
            lo, hi = np.minimum(lo, plo), np.maximum(hi, phi)
            parts.append(node.get("name", mesh.get("name", "")))
        for child in node.get("children", []):
            walk(child, world)

    scene = doc["scenes"][doc.get("scene", 0)]
    for root in scene["nodes"]:
        walk(root, np.eye(4))
    # glTF is +Y up, -Z forward... in Blender axes: x = x, y = -z, z = y
    blo = np.array([lo[0], -hi[2], lo[1]])
    bhi = np.array([hi[0], -lo[2], hi[1]])
    size = bhi - blo
    centre = (blo + bhi) / 2
    images = [i["uri"] for i in doc.get("images", [])]
    tex_px = sorted({max(Image.open(folder / u).size) for u in images})
    return {
        "size_m": [round(float(v), 3) for v in size],
        "bbox_min_m": [round(float(v), 3) for v in blo],
        "bbox_max_m": [round(float(v), 3) for v in bhi],
        "pivot_to_footprint_centre_m": [round(float(centre[0]), 3), round(float(centre[1]), 3), round(float(blo[2]), 3)],
        "triangles": int(tris),
        "vertices": int(verts),
        "mesh_nodes": len(parts),
        "materials": len(doc.get("materials", [])),
        "textures": images,
        "texture_px": tex_px,
        "generator": doc.get("asset", {}).get("generator", ""),
    }


# -------------------------------------------------------------------------------------------------------- cards

def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def card(entry, dest):
    """A 1280x720 picture for checking one set's scale by eye."""
    bc = Image.open(OUT / entry["files"]["BC"]["out"]).convert("RGB")
    w, h = bc.size
    tile = entry["tile_m"]
    basis = entry.get("basis", {})
    sheet = Image.new("RGB", (1280, 720), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    side = 640
    ox, oy = 40, 56
    sheet.paste(bc.resize((side, round(side * h / w)), Image.LANCZOS), (ox, oy))
    th = round(side * h / w)
    # rulers in the recipe's unit: alternating bands just outside the image
    for axis in ("x", "y"):
        b = basis.get(axis) if basis.get("kind") == "count" else None
        n = b["count"] if b else None
        length = side if axis == "x" else th
        if n:
            for i in range(int(math.ceil(n))):
                a0, a1 = i * length / n, min(length, (i + 1) * length / n)
                col = (255, 220, 0) if i % 2 == 0 else (30, 30, 30)
                if axis == "x":
                    d.rectangle((ox + a0, oy - 14, ox + a1, oy - 4), fill=col)
                    d.rectangle((ox + a0, oy + th + 4, ox + a1, oy + th + 14), fill=col)
                else:
                    d.rectangle((ox - 14, oy + a0, ox - 4, oy + a1), fill=col)
                    d.rectangle((ox + side + 4, oy + a0, ox + side + 14, oy + a1), fill=col)
        else:  # decimetres
            n10 = tile[0 if axis == "x" else 1] * 10
            for i in range(int(math.ceil(n10))):
                a0, a1 = i * length / n10, min(length, (i + 1) * length / n10)
                col = (0, 200, 255) if i % 2 == 0 else (30, 30, 30)
                if axis == "x":
                    d.rectangle((ox + a0, oy - 14, ox + a1, oy - 4), fill=col)
                else:
                    d.rectangle((ox - 14, oy + a0, ox - 4, oy + a1), fill=col)
    # 1:1 crop with a millimetre scale
    cs = 520
    cx, cy = 730, 56
    crop = bc.crop((w // 2 - cs // 2, h // 2 - cs // 2, w // 2 + cs // 2, h // 2 + cs // 2))
    sheet.paste(crop, (cx, cy))
    mm_per_px = tile[0] * 1000.0 / w
    for length_mm, yoff, colour in ((100, 24, (255, 220, 0)), (10, 44, (0, 200, 255))):
        px = length_mm / mm_per_px
        k = 0
        while (k + 1) * px <= cs and k < 60:
            if k % 2 == 0:
                d.rectangle((cx + k * px, cy + cs + yoff - 14, cx + (k + 1) * px, cy + cs + yoff - 4), fill=colour)
            k += 1
        d.text((cx + cs + 6, cy + cs + yoff - 18), f"{length_mm} mm", fill=colour, font=font(14))
    f = font(18)
    d.text((40, 8), f"{entry['set']}  ({entry['slug']})   tile {tile[0]:.3f} x {tile[1]:.3f} m   "
                    f"{mm_per_px:.2f} mm/px", fill=(255, 255, 255), font=f)
    text = entry.get("tile_method", "")
    words, lines, line = text.split(), [], ""
    for wd in words:
        if len(line) + len(wd) > 62:
            lines.append(line)
            line = ""
        line += wd + " "
    lines.append(line)
    for i, ln in enumerate(lines[:6]):
        d.text((730, 640 + i * 13 - 8), ln, fill=(200, 200, 200), font=font(12))
    b = [f"{a}: {basis[a]['count']} x {basis[a]['unit_mm']} mm {basis[a].get('feature', '')}" for a in ("x", "y")
         if basis.get(a)] if basis.get("kind") == "count" else [f"stated {basis.get('stated_m')} m"]
    d.text((40, oy + th + 20), "ruler: " + "; ".join(b) + ("" if basis.get("kind") == "count" else "  (ruler: 100 mm)"),
           fill=(255, 220, 0), font=font(14))
    sheet.save(dest, quality=88)


# --------------------------------------------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", nargs="+", metavar="SET")
    ap.add_argument("--cards", metavar="DIR", help="write a scale-check picture per tiling set into DIR")
    ap.add_argument("--check", action="store_true", help="do not write; fail if the catalogue disagrees with the files")
    ap.add_argument("--fast", action="store_true", help="recompute tile sizes and cards only (skip the image analysis)")
    args = ap.parse_args(argv)
    cat = json.loads(CATALOGUE.read_text())
    names = set(args.only or [])
    problems = []
    for entry in cat["sets"]:
        if names and entry["set"] not in names and entry["slug"] not in names:
            continue
        try:
            if entry["kind"] == "texture":
                old = entry.get("measured", {})
                m = old if args.fast and old else measure_texture(entry)
                tile, how = tile_from_basis(entry, m["px"])
                if tile is None:
                    problems.append(f"{entry['set']}: {how}")
                elif entry.get("tile_m") != tile:
                    if args.check:
                        problems.append(f"{entry['set']}: tile_m {entry.get('tile_m')} but the recipe gives {tile}")
                    entry["tile_m"] = tile
                if entry.get("px") != m["px"]:
                    if args.check:
                        problems.append(f"{entry['set']}: px {entry.get('px')} but the files are {m['px']}")
                    entry["px"] = m["px"]
                if tile:
                    m["px_per_m"] = round(m["px"][0] / tile[0])
                    m["grain_mm"] = round(m["grain_px"] / m["px"][0] * tile[0] * 1000.0, 1)
                    if "relief_mm" in m and old.get("px_per_m") and args.fast:
                        m["relief_mm"] = round(m["relief_mm"] * old["px_per_m"] / m["px_per_m"], 1)
                entry["measured"] = m
                if args.cards and entry.get("tile_m"):
                    Path(args.cards).mkdir(parents=True, exist_ok=True)
                    card(entry, Path(args.cards) / f"card_{entry['set']}.jpg")
                rep = m["repeat"].get("height", m["repeat"]["base_colour"])
                print(f"{entry['set']:32s} {m['px'][0]}x{m['px'][1]}  tile {entry.get('tile_m')}  "
                      f"repeat x{rep['x'][:2]} y{rep['y'][:2]}  grain {m.get('grain_mm')} mm  relief {m.get('relief_mm')} mm "
                      f"(fit {m.get('relief_fit')})  albedo {m['albedo']['luminance']}  R {m['roughness']} M {m['metallic']}  "
                      f"seam {m['seam_verdict']}")
            elif entry["kind"] == "hdri" and not args.fast:
                entry["measured"] = measure_hdri(entry)
                m = entry["measured"]
                print(f"{entry['set']:32s} sun el {m['sun_elevation_deg']} u {m['sun_uv'][0]} peak {m['peak_radiance']} "
                      f"E {m['horizontal_irradiance']} sun share {m['sun_share_of_irradiance']}")
            elif entry["kind"] == "model" and not args.fast:
                entry["measured"] = measure_model(entry)
                m = entry["measured"]
                print(f"{entry['set']:32s} {m['size_m']} m  {m['triangles']} tris  pivot off {m['pivot_to_footprint_centre_m']}  "
                      f"{len(m['textures'])} tex")
        except FileNotFoundError as e:
            problems.append(f"{entry['set']}: {e}")
    for p in problems:
        print("PROBLEM", p)
    if not args.check:
        CATALOGUE.write_text(json.dumps(cat, indent=1, ensure_ascii=False) + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
