"""Per-texel texture authoring for unique sets (characters): bake what the mesh knows into UV space once (rest
position, normal, material slot, face attributes, coverage), then compute colour, roughness and height for every
texel in numpy from analytic fields of the 3D position (seams, stitches, wrinkles, veins, pores), and derive the
tangent-space normal map from the height through the UV layout itself.

    maps = texel.bake_maps(ob, 4096, face_attrs=["mi_label"])   # dict of (H, W[, 3]) arrays, row 0 at the bottom
    idx = np.nonzero(maps["mask"].ravel())[0]                     # covered texels
    for sl in texel.chunks(idx):  P = maps["pos"].reshape(-1, 3)[sl] ...
    n = texel.normal_from_height(height, maps["pos"], maps["mask"])
    texel.dilate(img, maps["mask"])                               # fill the gutters for mip-mapping

Noise: texel.noise(p, freq, seed) is 3D gradient noise in -1..1 (quintic fade), fbm(...) sums octaves.
"""
import numpy as np
import bpy

from . import bake as _bake
from . import scene as _scene

POS_OFFSET = 8.0


# ------------------------------------------------------------------------------------------------ baking


def _emit_material(name, kind, value=None):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    if kind == "pos":
        g = nt.nodes.new("ShaderNodeNewGeometry")
        add = nt.nodes.new("ShaderNodeVectorMath")
        add.operation = "ADD"
        add.inputs[1].default_value = (POS_OFFSET,) * 3
        nt.links.new(g.outputs["Position"], add.inputs[0])
        nt.links.new(add.outputs[0], em.inputs["Color"])
    elif kind == "normal":
        g = nt.nodes.new("ShaderNodeNewGeometry")
        mad = nt.nodes.new("ShaderNodeVectorMath")
        mad.operation = "MULTIPLY_ADD"
        mad.inputs[1].default_value = (0.5, 0.5, 0.5)
        mad.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(g.outputs["Normal"], mad.inputs[0])
        nt.links.new(mad.outputs[0], em.inputs["Color"])
    elif kind == "attr":
        a = nt.nodes.new("ShaderNodeAttribute")
        a.attribute_type = "GEOMETRY"
        a.attribute_name = value
        nt.links.new(a.outputs["Fac"], em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = (*value, 1.0)
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


class _Override:
    """Temporarily give every slot of ob its own emission material (per slot so the slot index can be baked)."""

    def __init__(self, ob, make):
        self.ob, self.make, self.saved, self.temp = ob, make, [], []

    def __enter__(self):
        for i, slot in enumerate(self.ob.material_slots):
            self.saved.append(slot.material)
            m = self.make(i)
            self.temp.append(m)
            slot.material = m
        return self

    def __exit__(self, *a):
        for slot, m in zip(self.ob.material_slots, self.saved):
            slot.material = m
        for m in self.temp:
            bpy.data.materials.remove(m)
        return False


def bake_maps(ob, res, face_attrs=(), samples=1):
    """Rest-space maps through ob's active UV layer: pos (H, W, 3) metres in object space (ob at identity),
    normal (H, W, 3) unit, slot (H, W) int, mask (H, W) bool, and each face attribute (H, W) float."""
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    out = {}
    with _Override(ob, lambda i: _emit_material("__tx_pos", "pos")):
        px = _bake._bake_pass(ob, "EMIT", res, samples, 0)
    cov = px[..., :3].sum(axis=-1) > 1.0                      # uncovered texels stay 0 (positions are offset)
    out["pos"] = (px[..., :3] - POS_OFFSET).astype(np.float32)
    out["mask"] = cov
    with _Override(ob, lambda i: _emit_material("__tx_n", "normal")):
        px = _bake._bake_pass(ob, "EMIT", res, samples, 0)
    n = px[..., :3] * 2 - 1
    out["normal"] = (n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)).astype(np.float32)
    with _Override(ob, lambda i: _emit_material("__tx_slot", "const", ((i + 0.5) / 16.0, 0, 0))):
        px = _bake._bake_pass(ob, "EMIT", res, samples, 0)
    out["slot"] = np.floor(px[..., 0] * 16.0).astype(np.int16)
    for a in face_attrs:
        with _Override(ob, lambda i: _emit_material("__tx_a", "attr", a)):
            px = _bake._bake_pass(ob, "EMIT", res, samples, 0)
        out[a] = px[..., 0].astype(np.float32)
    return out


def chunks(idx, size=1_500_000):
    for s in range(0, len(idx), size):
        yield idx[s:s + size]


# ------------------------------------------------------------------------------------------------ noise

_PERM = np.random.default_rng(1234).permutation(256).astype(np.int64)
_PERM = np.concatenate([_PERM, _PERM])
_G = np.array([[1, 1, 0], [-1, 1, 0], [1, -1, 0], [-1, -1, 0], [1, 0, 1], [-1, 0, 1], [1, 0, -1], [-1, 0, -1],
               [0, 1, 1], [0, -1, 1], [0, 1, -1], [0, -1, -1], [1, 1, 0], [0, -1, 1], [-1, 1, 0], [0, -1, -1]],
              dtype=np.float32)


def noise(p, freq=1.0, seed=0):
    """3D gradient noise (Perlin, improved) at points p (N, 3) scaled by freq; about -1..1."""
    q = np.asarray(p, dtype=np.float64) * freq + seed * 17.31
    i = np.floor(q)
    f = (q - i).astype(np.float32)
    i = i.astype(np.int64) & 255
    u = f * f * f * (f * (f * 6 - 15) + 10)
    P = _PERM
    out = None
    acc = {}
    for dx in (0, 1):
        a = P[i[:, 0] + dx]
        for dy in (0, 1):
            b = P[a + i[:, 1] + dy]
            for dz in (0, 1):
                h = P[b + i[:, 2] + dz] & 15
                g = _G[h]
                d = f - np.array([dx, dy, dz], dtype=np.float32)
                acc[(dx, dy, dz)] = np.einsum("ij,ij->i", g, d)
    lerp = lambda a, b, t: a + (b - a) * t
    x00 = lerp(acc[(0, 0, 0)], acc[(1, 0, 0)], u[:, 0])
    x10 = lerp(acc[(0, 1, 0)], acc[(1, 1, 0)], u[:, 0])
    x01 = lerp(acc[(0, 0, 1)], acc[(1, 0, 1)], u[:, 0])
    x11 = lerp(acc[(0, 1, 1)], acc[(1, 1, 1)], u[:, 0])
    y0 = lerp(x00, x10, u[:, 1])
    y1 = lerp(x01, x11, u[:, 1])
    out = lerp(y0, y1, u[:, 2])
    return out * 1.1


def fbm(p, freq, octaves=4, gain=0.5, lac=2.03, seed=0):
    s = np.zeros(len(p), dtype=np.float32)
    a, f, norm = 1.0, freq, 0.0
    for o in range(octaves):
        s += a * noise(p, f, seed + o * 7)
        norm += a
        a *= gain
        f *= lac
    return s / norm


def ridged(p, freq, seed=0):
    """Sharp creases: 1 - |noise| sharpened (0..1, 1 on the crease lines)."""
    return (1.0 - np.abs(noise(p, freq, seed))) ** 6


def cells(p, freq, seed=0):
    """Pebble pattern (leather grain): distance to the nearest of jittered points, 0 at the centres, ~1 at the
    edges between cells (3D Worley, F2 - F1 style edges)."""
    q = np.asarray(p, dtype=np.float64) * freq
    i = np.floor(q).astype(np.int64)
    f1 = np.full(len(q), 9.0, dtype=np.float32)
    f2 = np.full(len(q), 9.0, dtype=np.float32)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = i + np.array([dx, dy, dz])
                h = (c[:, 0] * 73856093) ^ (c[:, 1] * 19349663) ^ (c[:, 2] * 83492791) ^ (seed * 2654435761)
                h = (h ^ (h >> 13)) * 1274126177
                j = np.stack([((h >> s) & 1023) / 1023.0 for s in (0, 10, 20)], axis=1)
                d = np.linalg.norm(c + j - q, axis=1).astype(np.float32)
                f2 = np.where(d < f1, f1, np.minimum(f2, d))
                f1 = np.minimum(f1, d)
    return f1, f2


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------------------------------------ images


def normal_from_height(h, pos, mask, strength=1.0):
    """Tangent-space normal (OpenGL, +Y up, encoded 0..1) from a height map (metres) laid out like the UVs:
    the slope along each image axis is divided by the world distance one texel covers along that axis (measured
    from the baked positions), so the relief has its true scale on every island whatever its UV scale."""
    H, W = h.shape
    m = mask

    def diff(a, axis):
        f = np.roll(a, -1, axis=axis)
        b = np.roll(a, 1, axis=axis)
        mf = np.roll(m, -1, axis=axis) & m
        mb = np.roll(m, 1, axis=axis) & m
        both = mf & mb
        d = np.where(both, (f - b) * 0.5, np.where(mf, f - a, np.where(mb, a - b, 0)))
        return d

    dhx, dhy = diff(h, 1), diff(h, 0)
    dpx = np.stack([diff(pos[..., k], 1) for k in range(3)], axis=-1)
    dpy = np.stack([diff(pos[..., k], 0) for k in range(3)], axis=-1)
    lx = np.maximum(np.linalg.norm(dpx, axis=-1), 1e-7)
    ly = np.maximum(np.linalg.norm(dpy, axis=-1), 1e-7)
    nx = -dhx / lx * strength
    ny = -dhy / ly * strength
    n = np.stack([nx, ny, np.ones_like(nx)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n = n * 0.5 + 0.5
    n[~m] = (0.5, 0.5, 1.0)
    return n.astype(np.float32)


def dilate(img, mask, iters=16):
    """Fill uncovered texels from covered neighbours (iterative, keeps covered texels)."""
    img = img.copy()
    m = mask.copy()
    for _ in range(iters):
        if m.all():
            break
        acc = np.zeros_like(img, dtype=np.float32)
        cnt = np.zeros(m.shape, dtype=np.float32)
        for ax, sh in ((0, 1), (0, -1), (1, 1), (1, -1)):
            mm = np.roll(m, sh, axis=ax)
            acc += np.where((mm[..., None] if img.ndim == 3 else mm), np.roll(img, sh, axis=ax), 0)
            cnt += mm
        new = (~m) & (cnt > 0)
        div = np.maximum(cnt, 1)
        img[new] = (acc / (div[..., None] if img.ndim == 3 else div))[new]
        m = m | new
    return img


def blur(a, r=1):
    """Box blur of radius r texels (separable, a few passes ~ gaussian)."""
    out = a.astype(np.float32)
    for _ in range(2):
        for ax in (0, 1):
            s = np.zeros_like(out)
            for k in range(-r, r + 1):
                s += np.roll(out, k, axis=ax)
            out = s / (2 * r + 1)
    return out
