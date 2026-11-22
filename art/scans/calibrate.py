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


def line_counts(img, top=4):
    """Repeat counts of what lies along single lines: bricks along a course, boards across a deck.

    A running bond shifts every course by half a brick, so the column profile of repeat_counts() sees nothing;
    but each row on its own is periodic with the brick length. The autocorrelation is therefore taken line by
    line and averaged, and its peaks are reported as counts per tile (not whole numbers when the units are
    irregular, as hand-laid bricks are). Returns {"x": [[count, correlation], ...], "y": [...]}.
    """
    out = {}
    for name, axis in (("x", 1), ("y", 0)):
        a = img - img.mean(axis=axis, keepdims=True)
        spec = np.fft.rfft(a, axis=axis)
        power = (spec.real ** 2 + spec.imag ** 2).mean(axis=1 - axis)
        acf = np.fft.irfft(power, n=img.shape[axis])
        acf = acf / (acf[0] or 1.0)
        n = len(acf)
        peaks = []
        for lag in range(8, n // 2 + 1):
            w = max(2, lag // 16)
            lo, hi = max(1, lag - w), min(n // 2, lag + w)
            if acf[lag] >= acf[lo:hi + 1].max() and acf[lag] > 0.03:
                # refine the peak position with a parabola through its neighbours
                y0, y1, y2 = acf[lag - 1], acf[lag], acf[min(lag + 1, n - 1)]
                den = y0 - 2 * y1 + y2
                pos = lag + (0.5 * (y0 - y2) / den if den else 0.0)
                peaks.append([round(float(n / pos), 2), round(float(acf[lag]), 3)])
        peaks.sort(key=lambda p: -p[1])
        out[name] = peaks[:top]
    return out


def grain_px(lum):
    """Typical grain diameter in pixels, from the correlation length of the base colour.

    Variation broader than about 100 px is removed first (stains, shading). The radially averaged
    autocorrelation of what is left falls to one half at r_half; for a surface made of round grains of diameter
    D lying at random, that happens at 0.404 D (the overlap of two discs), so D = r_half / 0.404.
    Good for aggregate, grit and weave; meaningless on a surface whose detail is joints or boards.
    """
    h, w = lum.shape
    spec = np.fft.rfft2(lum - lum.mean())
    spec *= 1.0 - gaussian_fft(lum.shape, 24.0)
    power = (spec.real ** 2 + spec.imag ** 2)
    acf = np.fft.irfft2(power, s=lum.shape)
    acf /= acf[0, 0] or 1.0
    # radial average out to 64 px: sample along rows, columns and both diagonals of the wrapped correlation
    radii = np.arange(0, 65)
    prof = np.zeros(len(radii))
    for i, r in enumerate(radii):
        d = int(round(r / math.sqrt(2)))
        vals = [acf[0, r % w], acf[r % h, 0], acf[d % h, d % w], acf[d % h, -d % w]] if r else [1.0]
        prof[i] = float(np.mean(vals))
    below = np.nonzero(prof < 0.5)[0]
    if not len(below):
        return 2.0 * 64 / 0.404, [round(float(v), 3) for v in prof[:16]]
    i = int(below[0])
    r_half = (i - 1) + (prof[i - 1] - 0.5) / (prof[i - 1] - prof[i]) if i > 0 else 0.5
    return r_half / 0.404, [round(float(v), 3) for v in prof[:16]]


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
    """How the wrapped edge compares with ordinary neighbours, per axis and at three scales.

    At each scale (full size, 1/4, 1/16, box-filtered) the mean absolute difference between the last and the
    first column (row) is divided by the median of the same difference between adjacent interior columns
    (rows); "rank" is the share of interior pairs that differ less than the wrapped pair (1.0 = the seam is the
    worst line in the picture). The coarse scales catch a soft seam: a tone step that was feathered over a few
    pixels and so passes at pixel scale.
    """
    a = img if img.ndim == 3 else img[..., None]
    out = {}
    for name, axis in (("x", 1), ("y", 0)):
        m = np.moveaxis(a, axis, 0)
        res = {}
        for label, f in (("px1", 1), ("px4", 4), ("px16", 16)):
            n = (m.shape[0] // f) * f
            mm = m[:n].reshape(n // f, f, *m.shape[1:]).mean(axis=1) if f > 1 else m
            d = np.abs(np.roll(mm, -1, axis=0) - mm).mean(axis=(1, 2))  # d[-1] is the wrapped pair
            wrap, inner = float(d[-1]), d[:-1]
            med = float(np.median(inner)) or 1e-9
            res[label] = [round(wrap / med, 2), round(float((inner < wrap).mean()), 3)]
        out[name] = res
    return out


def seam_verdict(seams):
    """"ok", or a short description of what shows."""
    notes = []
    for mapname, s in seams.items():
        for axis in ("x", "y"):
            v = s[axis]
            if v["px1"][0] > 1.6 and v["px1"][1] > 0.995:
                notes.append(f"{mapname} {axis}: hard seam ({v['px1'][0]}x a normal neighbour)")
            elif v["px4"][0] > 1.6 and v["px4"][1] > 0.995:
                notes.append(f"{mapname} {axis}: soft seam ({v['px4'][0]}x at 1/4 size)")
            elif v["px16"][0] > 2.0 and v["px16"][1] > 0.995:
                notes.append(f"{mapname} {axis}: tone step across the wrap ({v['px16'][0]}x at 1/16 size)")
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
    m["repeat"] = {"base_colour": repeat_counts(luminance(bc)), "base_colour_lines": line_counts(luminance(bc))}
    if height is not None:
        m["repeat"]["height"] = repeat_counts(height)
        m["repeat"]["height_lines"] = line_counts(height)
    g, _ = grain_px(luminance(bc))
    m["grain_px"] = round(g, 1)
    if tile:
        m["grain_mm"] = round(g / w * tile[0] * 1000.0, 1)
        m["px_per_m"] = round(w / tile[0])
    if height is not None and "N" in files:
        nrm = load_rgb(files["N"])
        frac, corr = relief_fraction(height, nrm)
        lo, hi = np.percentile(height, [1, 99])
        m["height_range"] = [round(float(height.min()), 4), round(float(lo), 4), round(float(hi), 4), round(float(height.max()), 4)]
        m["height_mid"] = round(float(np.median(height)), 4)
        m["relief_fit"] = round(corr, 2)
        m["height_scale_frac"] = round(frac, 6)  # metres of height per unit of map value, per metre of tile width
        if tile:
            m["height_scale_mm"] = round(frac * tile[0] * 1000.0, 1)
            m["relief_mm"] = round(frac * tile[0] * 1000.0 * float(hi - lo), 1)
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

# Hollis, Queens (40.71 N, 73.76 W), 15 July, 4:15 PM daylight time: solar time 15:14, declination 21.5 deg.
# Elevation 45 deg, bearing 260 deg (10 deg south of due west). In project axes (east = +X, north = +Y) the sun
# stands at 190 deg counter-clockwise from +X: it shines down Jamaica Avenue from the west end.
DESIGN_SUN = {"elevation_deg": 45.0, "bearing_deg": 260.0, "azimuth_deg": 190.0}

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
    share = e_sun / e_total if e_total else 0.0
    image_azimuth = (360.0 * (0.5 - u)) % 360.0  # Cycles: column u = 0.5 of an unrotated equirect faces +X, u = 0.25 faces +Y
    return {
        "px": [w, h],
        # the brightest source: the sun by day, the moon or a lamp at night
        "sun_uv": [round(u, 4), round((y + 0.5) / h, 4)],
        "sun_elevation_deg": round(elev, 1),
        "sun_share_of_irradiance": round(share, 3),
        "has_sun": bool(share >= 0.3 and peak >= 1000.0),
        "peak_radiance": round(peak, 1),
        "sky_mean_radiance": round(float((lum[: h // 2] * solid[: h // 2]).sum() / solid[: h // 2].sum()), 3),
        "ground_mean_radiance": round(float((lum[h // 2:] * solid[h // 2:]).sum() / solid[h // 2:].sum()), 3),
        "horizontal_irradiance": round(e_total, 3),
        # exposure shift (stops) at which an 18 % grey card lying flat under this sky renders at 18 %
        "ev_for_grey_card": round(math.log2(math.pi / e_total), 2) if e_total > 0 else 0.0,
        # where the source stands in an unrotated Blender world (degrees counter-clockwise from +X = east)
        "sun_azimuth_unrotated_deg": round(image_azimuth, 1),
        # Z rotation of the Mapping node in front of the Environment Texture that puts it where the design wants
        # the 4:15 PM sun (see DESIGN_SUN): world azimuth = unrotated azimuth - rotation
        "rotation_z_for_design_sun_deg": round((image_azimuth - DESIGN_SUN["azimuth_deg"]) % 360.0, 1),
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
            # Blender axes: x = x, y = -z, z = y
            parts.append({"name": node.get("name", mesh.get("name", "")),
                          "size_m": [round(float(phi[0] - plo[0]), 3), round(float(phi[2] - plo[2]), 3), round(float(phi[1] - plo[1]), 3)],
                          "centre_m": [round(float((plo[0] + phi[0]) / 2), 3), round(float(-(plo[2] + phi[2]) / 2), 3), round(float((plo[1] + phi[1]) / 2), 3)]})
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
        "nodes": parts if len(parts) > 1 else [],
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
    ap.add_argument("--kind", choices=("texture", "hdri", "model"), help="only entries of this kind")
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
        if args.kind and entry["kind"] != args.kind:
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
                    if "height_scale_frac" in m:
                        m["height_scale_mm"] = round(m["height_scale_frac"] * tile[0] * 1000.0, 1)
                        m["relief_mm"] = round(m["height_scale_mm"] * (m["height_range"][2] - m["height_range"][1]), 1)
                entry["measured"] = m
                if args.cards and entry.get("tile_m"):
                    Path(args.cards).mkdir(parents=True, exist_ok=True)
                    card(entry, Path(args.cards) / f"card_{entry['set']}.jpg")
                rep = m["repeat"].get("height", m["repeat"]["base_colour"])
                print(f"{entry['set']:32s} {m['px'][0]}x{m['px'][1]}  tile {entry.get('tile_m')}  "
                      f"repeat x{rep['x'][:2]} y{rep['y'][:2]} lines x{m['repeat']['base_colour_lines']['x'][:3]}  grain {m.get('grain_mm')} mm  relief {m.get('relief_mm')} mm "
                      f"(scale {m.get('height_scale_mm')} mm, fit {m.get('relief_fit')})  albedo {m['albedo']['luminance']}  "
                      f"R {m['roughness']} M {m['metallic']}  seam {m['seam_verdict']}")
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
        text = json.dumps(cat, indent=1, ensure_ascii=False) + "\n"  # encode first: a failure must not truncate the file
        tmp = CATALOGUE.with_suffix(".tmp")
        tmp.write_text(text)
        tmp.replace(CATALOGUE)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
