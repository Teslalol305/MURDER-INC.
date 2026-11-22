"""Texture authoring in UV space with numpy, for unique sets of hero assets (guns, close-up props).

Instead of baking procedural shaders, bake the GEOMETRY once (object-space position and normal, a per-face part
id, ambient occlusion at two distances and a rounded-edge mask) into float images through the object's UV map,
then compute every channel (base colour, roughness, metallic, a detail height turned into a tangent-space normal
map, emissive) with numpy from those maps. Everything is a function of the 3D position, so UV seams never show
and the masks are physically placed (wear on the convex edges that hands and holsters reach, dust in the
recesses that the short-range occlusion finds, scratches along the direction of handling).

    from mi import texpaint as tp
    G = tp.geometry_maps(ob, res=4096, attr="mid")      # dict of (h, w[, 3]) arrays, row 0 at the bottom (v = 0)
    N = tp.Noise(seed=3)
    m = G["mask"]; p = G["pos"][m]                       # work on covered texels only (flat arrays)
    rough = tp.scatter(m, 0.4 + 0.1 * N.fbm(p, 400, 4))
    height = tp.scatter(m, 2e-5 * N.fbm(p, 3000, 2))
    normal = tp.tangent_normal(height, G)                 # OpenGL (+Y up), encoded 0..1
    bake.write_set("Chopper", {"bc": ..., "rough": ..., "metal": ..., "normal": normal, "ao": G["ao"]}, meta=...)

Maps returned by geometry_maps (row 0 = v 0, column 0 = u 0; texels outside the islands carry the margin):
    mask   bool, covered (islands + margin)        id     int, the face attribute `attr` (-1 outside)
    pos    object-space position (m)               nrm    object-space shading normal (unit)
    ao     occlusion within ao_far (1 = open)      cav    occlusion within ao_near (crevices, seams)
    edge   rounded-edge mask from a Bevel node (0 flat .. 1 sharp corner, convex and concave alike)
    convex edge * (cav high)                       m_u, m_v  metres per texel along u and v (local)
"""
import time

import bpy
import numpy as np

from . import bake as _bake
from . import mat as _mat
from . import scene as _scene


# --------------------------------------------------------------------------------------------- geometry bakes

def _bake_material(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.node_tree.nodes.clear()
    return m


def geometry_maps(ob, res=2048, samples=16, ao_far=0.02, ao_near=0.004, bevel_radius=0.0012, attr="mid",
                  margin=16, verbose=True):
    """Bake the geometry maps of `ob` through its active UV map (see module doc). The object's materials are
    swapped for one bake material during the bakes and restored after."""
    t0 = time.time()
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    me = ob.data
    orig = [sl.material for sl in ob.material_slots]
    m = _bake_material("__tp_bake")
    nt = m.node_tree
    nd, ln = nt.nodes, nt.links
    out = nd.new("ShaderNodeOutputMaterial")
    em = nd.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    ln.new(em.outputs[0], out.inputs["Surface"])
    geo_n = nd.new("ShaderNodeNewGeometry")
    att = nd.new("ShaderNodeAttribute")
    att.attribute_type = "GEOMETRY"
    att.attribute_name = attr
    comb = nd.new("ShaderNodeCombineXYZ")
    add1 = nd.new("ShaderNodeMath")
    add1.operation = "ADD"
    add1.inputs[1].default_value = 1.0
    ln.new(att.outputs["Fac"], add1.inputs[0])
    ln.new(add1.outputs[0], comb.inputs[0])
    nmap = nd.new("ShaderNodeVectorMath")
    nmap.operation = "MULTIPLY_ADD"
    nmap.inputs[1].default_value = (0.5, 0.5, 0.5)
    nmap.inputs[2].default_value = (0.5, 0.5, 0.5)
    ln.new(geo_n.outputs["Normal"], nmap.inputs[0])
    aof = nd.new("ShaderNodeAmbientOcclusion")
    aof.inputs["Distance"].default_value = ao_far
    aof.only_local = True
    aof.samples = 16
    aon = nd.new("ShaderNodeAmbientOcclusion")
    aon.inputs["Distance"].default_value = ao_near
    aon.only_local = True
    aon.samples = 16
    bev = nd.new("ShaderNodeBevel")
    bev.samples = 16
    bev.inputs["Radius"].default_value = bevel_radius
    dot = nd.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    ln.new(bev.outputs["Normal"], dot.inputs[0])
    ln.new(geo_n.outputs["Normal"], dot.inputs[1])
    inv = nd.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    ln.new(dot.outputs["Value"], inv.inputs[1])
    comb2 = nd.new("ShaderNodeCombineXYZ")
    ln.new(aof.outputs["AO"], comb2.inputs[0])
    ln.new(aon.outputs["AO"], comb2.inputs[1])
    ln.new(inv.outputs[0], comb2.inputs[2])

    for sl in ob.material_slots:
        sl.material = m
    if not ob.material_slots:
        me.materials.append(m)
    hidden = []
    for o in s.objects:
        if o is not ob and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    res_ = {}

    def run(sock, spp, key):
        ln.new(sock, em.inputs["Color"])
        a = _bake._bake_pass(ob, "EMIT", res, spp, margin, margin_type="ADJACENT_FACES")[..., :3]
        res_[key] = a
        if verbose:
            print("    geometry map %-5s %6.1fs" % (key, time.time() - t0), flush=True)
    try:
        run(comb.outputs[0], 1, "id")
        run(geo_n.outputs["Position"], 1, "pos")
        run(nmap.outputs[0], 1, "nrm")
        run(comb2.outputs[0], samples, "occ")
    finally:
        for sl, mm in zip(ob.material_slots, orig):
            sl.material = mm
        for o in hidden:
            o.hide_render = False
        bpy.data.materials.remove(m)
    idf = res_["id"][..., 0]
    mask = idf > 0.5
    G = {"mask": mask, "id": np.where(mask, np.rint(idf - 1.0), -1).astype(np.int32), "pos": res_["pos"]}
    n = res_["nrm"] * 2.0 - 1.0
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    G["nrm"] = n
    G["ao"], G["cav"], G["edge"] = [np.clip(res_["occ"][..., i], 0.0, 1.0) for i in range(3)]
    G["edge"] = np.clip(G["edge"] * 4.0, 0.0, 1.0)
    G["convex"] = G["edge"] * np.clip((G["cav"] - 0.8) / 0.15, 0.0, 1.0)
    P = G["pos"]
    du = np.linalg.norm(np.diff(P, axis=1, append=P[:, -1:]), axis=-1)
    dv = np.linalg.norm(np.diff(P, axis=0, append=P[-1:]), axis=-1)
    med = float(np.median(du[mask])) if mask.any() else 1e-4
    G["m_u"] = np.where((du > 0) & (du < 4 * med), du, med).astype(np.float32)
    G["m_v"] = np.where((dv > 0) & (dv < 4 * med), dv, med).astype(np.float32)
    G["m_px"] = med
    G["res"] = res
    if verbose:
        print("    geometry maps %dpx: %.1f%% covered, %.3f mm per texel, %.1fs" % (
            res, 100.0 * mask.mean(), med * 1000, time.time() - t0), flush=True)
    return G


def scatter(mask, values, fill=0.0):
    """Flat per-texel values (for mask's True texels, row-major) back into an image."""
    v = np.asarray(values)
    out = np.full(mask.shape + v.shape[1:], fill, dtype=np.float32)
    out[mask] = v
    return out


# ------------------------------------------------------------------------------------------------------- noise

class Noise:
    """Value noise and fBm on 3D points (N, 3) in metres, vectorised. freq in cycles per metre (a number or
    (fx, fy, fz) for streaks: a low frequency along a direction stretches the features along it)."""

    def __init__(self, seed=0):
        r = np.random.default_rng(seed)
        self.perm = np.concatenate([r.permutation(256)] * 2).astype(np.int32)
        self.vals = r.random(256).astype(np.float32)
        self.off = r.random((64, 3)).astype(np.float32) * 256.0

    def _hash(self, i, j, k):
        p = self.perm
        return p[p[p[i & 255] + (j & 255)] + (k & 255)]

    def value(self, p, freq=1.0, octave=0):
        """Smooth value noise in -1..1."""
        q = np.asarray(p, dtype=np.float32) * np.asarray(freq, dtype=np.float32) + self.off[octave % 64]
        f = np.floor(q)
        t = q - f
        i = f.astype(np.int64)
        w = t * t * t * (t * (t * 6 - 15) + 10)
        x0, y0, z0 = i[:, 0], i[:, 1], i[:, 2]
        acc = 0.0
        for dx in (0, 1):
            wx = w[:, 0] if dx else 1 - w[:, 0]
            for dy in (0, 1):
                wy = w[:, 1] if dy else 1 - w[:, 1]
                for dz in (0, 1):
                    wz = w[:, 2] if dz else 1 - w[:, 2]
                    acc = acc + self.vals[self._hash(x0 + dx, y0 + dy, z0 + dz)] * (wx * wy * wz)
        return acc * 2.0 - 1.0

    def fbm(self, p, freq=1.0, octaves=4, gain=0.5, lac=2.03, octave0=0):
        """Fractal sum, roughly -1..1."""
        fr = np.asarray(freq, dtype=np.float32)
        tot, amp, norm = 0.0, 1.0, 0.0
        for o in range(octaves):
            tot = tot + amp * self.value(p, fr, octave0 + o)
            norm += amp
            amp *= gain
            fr = fr * lac
        return tot / norm

    def ridged(self, p, freq=1.0, octaves=3, octave0=0):
        """Thin ridges (0..1, 1 on the crest): scratches and cracks with a stretched freq."""
        return 1.0 - np.abs(self.fbm(p, freq, octaves, octave0=octave0))

    def cells(self, p, size, jitter=0.9, octave=0):
        """Per-point (cell id hash 0..1, distance to the cell's random point / size) on a cubic grid of `size` m."""
        q = np.asarray(p, dtype=np.float32) / size + self.off[octave % 64]
        f = np.floor(q).astype(np.int64)
        best = np.full(len(q), 9.0, dtype=np.float32)
        bid = np.zeros(len(q), dtype=np.float32)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    c = f + np.array([dx, dy, dz])
                    h = self._hash(c[:, 0], c[:, 1], c[:, 2])
                    h2 = self._hash(c[:, 0] + 17, c[:, 1] + 31, c[:, 2] + 7)
                    h3 = self._hash(c[:, 0] + 59, c[:, 1] + 3, c[:, 2] + 41)
                    jp = c + 0.5 + jitter * (np.stack([self.vals[h], self.vals[h2], self.vals[h3]], -1) - 0.5)
                    d = np.linalg.norm(q - jp, axis=1)
                    closer = d < best
                    best = np.where(closer, d, best)
                    bid = np.where(closer, self.vals[self._hash(h, h2, h3)], bid)
        return bid, best


def smooth(a, lo, hi):
    t = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------------------------- image filters

def blur(img, sigma_px, mask=None):
    """Gaussian blur (FFT, not wrapped: padded). With mask, a normalised blur that ignores uncovered texels."""
    if sigma_px <= 0.3:
        return img
    a = img.astype(np.float32)
    pad = int(3 * sigma_px) + 1

    def g(x):
        x = np.pad(x, [(pad, pad), (pad, pad)] + [(0, 0)] * (x.ndim - 2))
        h, w = x.shape[:2]
        fy = np.fft.fftfreq(h)[:, None]
        fx = np.fft.rfftfreq(w)[None, :]
        k = np.exp(-2 * (np.pi * sigma_px) ** 2 * (fx * fx + fy * fy)).astype(np.float32)
        if x.ndim == 3:
            r = np.stack([np.fft.irfft2(np.fft.rfft2(x[..., c]) * k, s=(h, w)) for c in range(x.shape[2])], -1)
        else:
            r = np.fft.irfft2(np.fft.rfft2(x) * k, s=(h, w))
        return r[pad:-pad, pad:-pad].astype(np.float32)
    if mask is None:
        return g(a)
    mw = mask.astype(np.float32)
    num = g(a * (mw[..., None] if a.ndim == 3 else mw))
    den = g(mw)
    den = den[..., None] if a.ndim == 3 else den
    return np.where(den > 1e-4, num / np.maximum(den, 1e-4), a)


def dilate(img, mask, iters=8):
    """Push covered values outward into uncovered texels (mip-safe padding beyond the bake margin)."""
    a = img.copy()
    m = mask.copy()
    for _ in range(iters):
        acc = np.zeros_like(a)
        cnt = np.zeros(m.shape, dtype=np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sm = np.roll(m, (dy, dx), axis=(0, 1))
            sa = np.roll(a, (dy, dx), axis=(0, 1))
            add = sm & ~m
            acc[add] += sa[add]
            cnt[add] += 1
        new = cnt > 0
        if not new.any():
            break
        a[new] = acc[new] / (cnt[new][..., None] if a.ndim == 3 else cnt[new])
        m = m | new
    return a


def tangent_normal(height, G, strength=1.0):
    """OpenGL tangent-space normal map (0..1 encoded) from a detail height image in metres over the UV layout.
    The tangent is +u and the bitangent +v (MikkTSpace on unmirrored islands); the slope is measured in metres
    per texel along u and v from the position map, so every island gets the right bump whatever its scale."""
    h = height.astype(np.float32)
    dhdx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dhdy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    nx = -dhdx / G["m_u"] * strength
    ny = -dhdy / G["m_v"] * strength
    lim = 3.0                                                   # at most ~72 deg tilt
    nx, ny = np.clip(nx, -lim, lim), np.clip(ny, -lim, lim)
    n = np.stack([nx, ny, np.ones_like(nx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n = n * 0.5 + 0.5
    n[~G["mask"]] = (0.5, 0.5, 1.0)
    return n.astype(np.float32)


def raster_plane(mask_img, pos, axes, origin, size_m):
    """Sample a 2D image (h, w) laid on a plane in object space at the texels' positions: axes = (i, j) indices of
    the position components that map to the image's x and y, origin = (x0, y0) metres of the image's lower-left
    corner, size_m = (width, height) metres. Returns per-texel values (0 outside the image)."""
    hgt, wid = mask_img.shape[:2]
    u = (pos[:, axes[0]] - origin[0]) / size_m[0]
    v = (pos[:, axes[1]] - origin[1]) / size_m[1]
    inside = (u >= 0) & (u < 1) & (v >= 0) & (v < 1)
    xi = np.clip((u * wid).astype(np.int64), 0, wid - 1)
    yi = np.clip(((1 - v) * hgt).astype(np.int64), 0, hgt - 1)
    out = np.where(inside, mask_img[yi, xi], 0.0)
    return out.astype(np.float32)


def text_image(lines, px=512, font=None, size=None):
    """White-on-black text image (float 0..1) for engraved or painted markings: lines = [(text, x, y, size_px)]
    in a px x px canvas (y down). Uses a DejaVu face."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("L", (px, px), 0)
    d = ImageDraw.Draw(im)
    for text, x, y, sz in lines:
        f = ImageFont.truetype(font or "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(sz))
        d.text((x, y), text, fill=255, font=f, anchor="mm")
    return np.asarray(im, dtype=np.float32) / 255.0


def finish(ch, G, pad=8):
    """Pad every channel outward beyond the islands and the bake margin (mip-safe) and clamp."""
    m = G["mask"]
    for k in ("bc", "rough", "metal", "ao", "emit"):
        if k in ch and ch[k] is not None:
            ch[k] = np.clip(dilate(ch[k], m, pad), 0.0, 1.0).astype(np.float32)
    return ch
