"""Bake materials to texture sets: T_<Set>_BC / _N / _ORM (+ _H, _E) under art/out/textures/<Set>/.

    from mi import bake
    bake.bake_object(hydrant, "Prop_Hydrant", res=2048)                       # UNIQUE set from the mesh's own UVs
    bake.bake_tiling_set("TS_Asphalt_Aged", "asphalt", tile_m=2.0, Cracks=0.3)   # SEAMLESS tiling set
    bake.tiled_preview("TS_Asphalt_Aged", "art/previews/tiling_asphalt_2x2.jpg")

Conventions: BC is sRGB; N is tangent space, OpenGL (+Y up) as Blender bakes it; ORM is linear with
R = ambient occlusion, G = roughness, B = metallic; H is 16-bit height (range in set.json, metres).

How it bakes (Blender 5.3 notes in the README): base colour, roughness, metallic and height are baked as
EMISSION of the socket that feeds the Principled BSDF. That is exact and fast, and it avoids the classic trap that
a DIFFUSE colour bake is black wherever metallic = 1. Normals of unique sets use the Cycles NORMAL pass; ambient
occlusion uses the AO pass with a plain white override material (the AO pass evaluates the whole shader once per
sample otherwise). Tiling sets get their normal and micro-occlusion from the baked height with wrap-around
filters, so they tile as exactly as the height does.
"""
import hashlib
import inspect
import json
import os
import time

import bpy
import numpy as np

from . import mat as _mat
from . import paths
from . import scene as _scene

H_ENC = 40.0        # height is baked as h * H_ENC + 0.5 so that +-12 mm stays inside 0..1


# ---------------------------------------------------------------------------------------------------- image helpers

def srgb_encode(lin):
    a = np.clip(lin, 0.0, 1.0)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * np.power(a, 1 / 2.4) - 0.055)


def srgb_decode(s):
    a = np.clip(s, 0.0, 1.0)
    return np.where(a <= 0.04045, a / 12.92, np.power((a + 0.055) / 1.055, 2.4))


def _to_u8(a):
    return (np.clip(a, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def save_png(arr, path, bits=8):
    """arr: (h, w) or (h, w, 3) floats in 0..1, row 0 at the BOTTOM (Blender / UV orientation)."""
    from PIL import Image
    os.makedirs(os.path.dirname(path), exist_ok=True)
    a = np.flipud(arr)
    if bits == 16:
        Image.fromarray((np.clip(a, 0, 1) * 65535.0 + 0.5).astype(np.uint16)).save(path, "PNG", compress_level=6)
    else:
        Image.fromarray(_to_u8(a)).save(path, "PNG", compress_level=6)
    return path


def load_image(path):
    """Image file -> float array (h, w, c) in 0..1, row 0 at the bottom."""
    from PIL import Image
    im = Image.open(path)
    a = np.asarray(im)
    scale = 65535.0 if a.dtype == np.uint16 or im.mode.startswith("I") else 255.0
    return np.flipud(a.astype(np.float32) / scale)


# -------------------------------------------------------------------------------------------------- low level bake

def _pixels(img):
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)


def _bake_pass(ob, kind, res, samples=1, margin=0, pass_filter=None, margin_type="EXTEND"):
    """One Cycles bake of `kind` into a fresh float image; returns (h, w, 4) float32, scene-linear."""
    s = bpy.context.scene
    w, h = (res, res) if isinstance(res, int) else res
    img = bpy.data.images.new("__mi_bake", w, h, alpha=False, float_buffer=True, is_data=True)
    nodes = []
    for slot in ob.material_slots:
        m = slot.material
        if m is None:
            continue
        nt = m.node_tree
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = img
        for n in nt.nodes:
            n.select = False
        tn.select = True
        nt.nodes.active = tn                      # the bake target is the ACTIVE image node of every material
        nodes.append((nt, tn))
    _scene.select_only(ob)
    old = s.cycles.samples, s.cycles.use_denoising, s.cycles.use_adaptive_sampling
    s.cycles.samples = int(samples)
    s.cycles.use_denoising = False
    s.cycles.use_adaptive_sampling = False
    kw = {"pass_filter": set(pass_filter)} if pass_filter else {}
    try:
        bpy.ops.object.bake(type=kind, margin=int(margin), margin_type=margin_type, use_clear=True,
                            target="IMAGE_TEXTURES", save_mode="INTERNAL", **kw)
        px = _pixels(img).copy()
    finally:
        s.cycles.samples, s.cycles.use_denoising, s.cycles.use_adaptive_sampling = old
        for nt, tn in nodes:
            nt.nodes.remove(tn)
        bpy.data.images.remove(img)
    return px


class _Emit:
    """Temporarily replace every material's surface by an Emission shader fed from per-material sources.
    get(material) -> a socket, a colour/number, or a tuple of three scalars to pack into R, G, B."""

    def __init__(self, ob, get):
        self.ob, self.get, self.undo = ob, get, []

    def __enter__(self):
        for slot in self.ob.material_slots:
            m = slot.material
            if m is None or any(m is u[0] for u in self.undo):
                continue
            nt = m.node_tree
            g = _mat.G(nt)
            out = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial" and n.is_active_output), None)
            if out is None:
                continue
            before = set(nt.nodes)
            orig = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].is_linked else None
            src = self.get(m)
            if isinstance(src, tuple) and len(src) == 3 and any(_mat._is_sock(x) for x in src):
                src = g.comb(*src)
            em = g.node("ShaderNodeEmission")
            g.put(em.inputs["Color"], src)
            em.inputs["Strength"].default_value = 1.0
            nt.links.new(em.outputs[0], out.inputs["Surface"])
            self.undo.append((m, out, orig, [n for n in nt.nodes if n not in before]))
        return self

    def __exit__(self, *exc):
        for m, out, orig, new_nodes in self.undo:
            nt = m.node_tree
            for n in new_nodes:
                nt.nodes.remove(n)
            if orig is not None:
                nt.links.new(orig, out.inputs["Surface"])
        return False


def _input(bsdf, name, default):
    if bsdf is None:
        return default
    s = bsdf.inputs[name]
    if s.is_linked:
        return s.links[0].from_socket
    v = s.default_value
    return float(v) if isinstance(v, (int, float)) else tuple(v)[:3]


def _is_const(x, value=None):
    if _mat._is_sock(x):
        return False
    return True if value is None else (x == value)


def bake_channels(ob, res=2048, samples=4, margin=12, normal=True, ao=True, ao_samples=16, ao_distance=None,
                  ground=False, verbose=True):
    """Bake every channel of the object's materials. Returns a dict of float arrays (row 0 at the bottom):
    'bc' (h, w, 3) linear, 'rough', 'metal', 'height' (metres), 'ao', 'normal' (h, w, 3 encoded 0..1), 'emit'."""
    t0 = time.time()
    mats = [s.material for s in ob.material_slots if s.material]
    pr = {m.name: _mat.principled(m) for m in mats}
    out = {}

    def log(msg):
        if verbose:
            print("    bake %-8s %6.1fs" % (msg, time.time() - t0), flush=True)

    # base colour
    with _Emit(ob, lambda m: _input(pr[m.name], "Base Color", (0.5, 0.5, 0.5))):
        out["bc"] = _bake_pass(ob, "EMIT", res, samples, margin)[..., :3]
    log("BC")

    # roughness, metallic, height packed into one emission bake
    def pack(m):
        b = pr[m.name]
        sn = _mat.surface_node(m)
        hsock = sn.outputs["Height"] if sn is not None and "Height" in sn.outputs else None
        g = _mat.G(m.node_tree)
        henc = g.add(g.mul(hsock, H_ENC), 0.5) if hsock is not None else 0.5
        return (_input(b, "Roughness", 0.5), _input(b, "Metallic", 0.0), henc)
    with _Emit(ob, pack):
        p = _bake_pass(ob, "EMIT", res, samples, margin)
    out["rough"], out["metal"] = p[..., 0], p[..., 1]
    out["height"] = (p[..., 2] - 0.5) / H_ENC
    log("R/M/H")

    # standing water (coat) folds into roughness: engines without a clear-coat channel still read it as wet
    if any(pr[m.name] is not None and pr[m.name].inputs["Coat Weight"].is_linked and _has_water(m) for m in mats):
        with _Emit(ob, lambda m: _input(pr[m.name], "Coat Weight", 0.0)):
            coat = _bake_pass(ob, "EMIT", res, samples, margin)[..., 0]
        out["rough"] = out["rough"] * (1 - coat) + 0.05 * coat
        out["coat"] = coat
        log("coat")

    # emission
    def emis(m):
        b = pr[m.name]
        if b is None:
            return (0.0, 0.0, 0.0)
        c, st = _input(b, "Emission Color", (0, 0, 0)), _input(b, "Emission Strength", 0.0)
        if _is_const(st) and st == 0.0:
            return (0.0, 0.0, 0.0)
        return c
    if any(not (_is_const(emis(m)) and max(emis(m)) == 0.0) for m in mats):
        with _Emit(ob, emis):
            out["emit"] = _bake_pass(ob, "EMIT", res, samples, margin)[..., :3]
        log("E")

    if normal:
        n = _bake_pass(ob, "NORMAL", res, max(1, samples // 2), margin)[..., :3]
        out["normal"] = n
        log("N")
    if ao:
        out["ao"] = _bake_ao(ob, res, ao_samples, margin, ao_distance, ground)
        log("AO")
    return out


def _has_water(m):
    sn = _mat.surface_node(m)
    if sn is None:
        return True
    try:
        gt = sn.node_tree
        go = next(n for n in gt.nodes if n.bl_idname == "NodeGroupOutput")
        return go.inputs["Coat Weight"].is_linked
    except Exception:
        return True


def _bake_ao(ob, res, samples, margin, distance, ground):
    """Ambient occlusion with a plain override material; other objects are hidden so only the asset (and an
    optional ground plane under props) occludes."""
    s = bpy.context.scene
    hidden = []
    for o in s.objects:
        if o is not ob and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    plane = None
    if ground:
        import bmesh
        lo, hi = _scene.bounds(ob, world=True)
        me = bpy.data.meshes.new("__mi_ao_ground")
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=float(max(hi[0] - lo[0], hi[1] - lo[1]) * 4 + 2))
        bmesh.ops.translate(bm, vec=((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] if ground is True else float(ground)), verts=bm.verts)
        bm.to_mesh(me)
        bm.free()
        plane = bpy.data.objects.new("__mi_ao_ground", me)
        s.collection.objects.link(plane)
    white = _mat.flat("__mi_ao_white", (0.8, 0.8, 0.8), 1.0)
    orig = [sl.material for sl in ob.material_slots]
    for sl in ob.material_slots:
        sl.material = white
    w = s.world
    old_world = None
    if w is not None and distance:
        old_world = w.light_settings.distance
        w.light_settings.distance = distance
    try:
        a = _bake_pass(ob, "AO", res, samples, margin)[..., 0]
    finally:
        for sl, m in zip(ob.material_slots, orig):
            sl.material = m
        for o in hidden:
            o.hide_render = False
        if plane is not None:
            bpy.data.objects.remove(plane, do_unlink=True)
        if old_world is not None:
            w.light_settings.distance = old_world
        bpy.data.materials.remove(white)
    return a


# ----------------------------------------------------------------------------------------- periodic image filters

def _gauss_wrap(a, sigma):
    """Gaussian blur with wrap-around (FFT): keeps tiling exact."""
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    k = np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))
    return np.fft.irfft2(np.fft.rfft2(a) * k, s=a.shape).astype(np.float32)


def normal_from_height(height_m, pixel_m, wrap=True, strength=1.0):
    """Tangent-space normal map (OpenGL, +Y up) from a height field in metres. pixel_m: metres per pixel
    (number or (x, y)). With wrap=True the derivative wraps, so a tiling height gives a tiling normal map."""
    px, py = (pixel_m, pixel_m) if np.isscalar(pixel_m) else pixel_m
    h = height_m.astype(np.float64)
    if wrap:
        l, r = np.roll(h, 1, axis=1), np.roll(h, -1, axis=1)
        d, u = np.roll(h, 1, axis=0), np.roll(h, -1, axis=0)
    else:
        hp = np.pad(h, 1, mode="edge")
        l, r, d, u = hp[1:-1, :-2], hp[1:-1, 2:], hp[:-2, 1:-1], hp[2:, 1:-1]
    dx = (r - l) / (2 * px) * strength
    dy = (u - d) / (2 * py) * strength
    n = np.stack([-dx, -dy, np.ones_like(h)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return (n * 0.5 + 0.5).astype(np.float32)


def ao_from_height(height_m, pixel_m, relief=0.001):
    """Micro-occlusion for a flat tiling surface: pits and the foot of bumps darken (two scales, wrap-around)."""
    px = pixel_m if np.isscalar(pixel_m) else pixel_m[0]
    h = height_m.astype(np.float32)
    occ = np.zeros_like(h)
    for radius_m, weight in ((0.004, 0.6), (0.016, 0.4)):
        b = _gauss_wrap(h, max(1.0, radius_m / px))
        occ += weight * np.clip((b - h) / max(relief, 1e-6), 0.0, 1.5)
    return np.clip(1.0 - 0.75 * occ, 0.25, 1.0).astype(np.float32)


def seam_report(arr):
    """How well does an image tile? The step across each wrapped edge (last column -> first column, last row ->
    first row) is compared with the steps between interior neighbours. Every interior column pair gives one mean
    absolute difference; a seamless edge is one whose step sits inside that population (at most its 99.9th
    percentile, or 1.25 x its mean), i.e. the wrap is no more visible than any other pixel boundary.
    Returns wrap_x/y, interior_x/y (population mean), limit_x/y, ratio (worst wrap / interior mean) and ok."""
    a = arr.astype(np.float64)
    if a.ndim == 2:
        a = a[..., None]
    px = np.abs(np.diff(a, axis=1)).mean(axis=(0, 2))          # one value per interior column pair
    py = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))
    wx = float(np.abs(a[:, 0] - a[:, -1]).mean())
    wy = float(np.abs(a[0, :] - a[-1, :]).mean())
    ix, iy = float(px.mean()), float(py.mean())
    lx = max(float(np.percentile(px, 99.9)), ix * 1.25) + 1e-6
    ly = max(float(np.percentile(py, 99.9)), iy * 1.25) + 1e-6
    ratio = max(wx / max(ix, 1e-9), wy / max(iy, 1e-9))
    return {"wrap_x": wx, "interior_x": ix, "limit_x": lx, "wrap_y": wy, "interior_y": iy, "limit_y": ly,
            "ratio": ratio, "ok": bool(wx <= lx and wy <= ly)}


# ------------------------------------------------------------------------------------------------------ set output

def write_set(set_name, ch, out_dir=None, meta=None, height_range=None):
    """Write T_<Set>_BC/N/ORM (+H, +E) PNG files and set.json from a channel dict. Returns the meta dict."""
    out_dir = out_dir or paths.texture_set(set_name)
    os.makedirs(out_dir, exist_ok=True)
    files = {}
    h, w = ch["rough"].shape
    bc = srgb_encode(ch["bc"])
    files["BC"] = os.path.basename(save_png(bc, os.path.join(out_dir, "T_%s_BC.png" % set_name)))
    n = ch.get("normal")
    if n is None:
        n = np.zeros((h, w, 3), dtype=np.float32) + np.array([0.5, 0.5, 1.0], dtype=np.float32)
    files["N"] = os.path.basename(save_png(n, os.path.join(out_dir, "T_%s_N.png" % set_name)))
    ao = ch.get("ao")
    if ao is None:
        ao = np.ones((h, w), dtype=np.float32)
    orm = np.stack([ao, ch["rough"], ch["metal"]], axis=-1)           # packed with numpy: R = AO, G = rough, B = metal
    files["ORM"] = os.path.basename(save_png(orm, os.path.join(out_dir, "T_%s_ORM.png" % set_name)))
    info = dict(meta or {})
    hh = ch.get("height")
    if hh is not None and float(hh.max() - hh.min()) > 1e-6:
        lo, hi = (float(np.percentile(hh, 0.5)), float(np.percentile(hh, 99.95))) if height_range is None else height_range
        files["H"] = os.path.basename(save_png((hh - lo) / max(hi - lo, 1e-9), os.path.join(out_dir, "T_%s_H.png" % set_name), bits=16))
        info["height_range_m"] = [lo, hi]
    if ch.get("emit") is not None and float(ch["emit"].max()) > 1e-4:
        files["E"] = os.path.basename(save_png(srgb_encode(ch["emit"]), os.path.join(out_dir, "T_%s_E.png" % set_name)))
    lum = ch["bc"] @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    info.update({
        "set": set_name, "resolution": [int(w), int(h)], "files": files,
        "convention": {"BC": "sRGB base colour", "N": "tangent-space normal, OpenGL (+Y up, as Blender bakes it)",
                       "ORM": "linear: R = ambient occlusion, G = roughness, B = metallic",
                       "H": "16-bit height, 0..1 over height_range_m (metres)", "E": "sRGB emissive"},
        "albedo_mean": [round(float(v), 4) for v in ch["bc"].reshape(-1, 3).mean(axis=0)],
        "albedo_luminance_p01_p50_p99": [round(float(np.percentile(lum, q)), 4) for q in (1, 50, 99)],
        "roughness_mean": round(float(ch["rough"].mean()), 4), "metallic_mean": round(float(ch["metal"].mean()), 4),
    })
    with open(os.path.join(out_dir, "set.json"), "w") as f:
        json.dump(info, f, indent=1, sort_keys=True)
    return info


def read_set(set_name, out_dir=None):
    p = os.path.join(out_dir or paths.texture_set(set_name), "set.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def _source_hash(kind, extra):
    sf = _mat.SURFACES.get(kind)
    src = inspect.getsource(sf.fn) if sf else ""
    if kind == "road_paint":
        src += inspect.getsource(_mat.SURFACES["asphalt"].fn)
    for fn in (_mat._rust, _mat._grime, _mat._dust, _mat.group, _mat.Ctx, _mat.Co):
        src += inspect.getsource(fn)
    return hashlib.sha1((src + repr(extra)).encode()).hexdigest()[:16]


# ------------------------------------------------------------------------------------------------------ public API

def bake_object(ob, set_name=None, res=2048, samples=4, margin=12, ao_samples=16, ground=False, out_dir=None,
                meta=None, verbose=True):
    """UNIQUE set: bake every material on the object through its UV map into one texture set named after the
    asset (SM_Prop_Hydrant -> 'Prop_Hydrant', used through slot M_Prop_Hydrant). The object needs a packed,
    non-overlapping UV map (geo.uv_unwrap). ground=True adds a ground plane under props for the AO pass."""
    set_name = set_name or ob.name.replace("SM_", "", 1)
    t = time.time()
    if verbose:
        print("  bake unique set %s  %dpx  %d tris" % (set_name, res, len(ob.data.loop_triangles) or 0), flush=True)
    ch = bake_channels(ob, res, samples, margin, True, True, ao_samples, None, ground, verbose)
    from . import geo as _geo
    info = {"kind": "unique", "asset": ob.name, "texel_density_px_per_m": round(_geo.uv_texel_density(ob, res), 1),
            "seconds": None}
    info.update(meta or {})
    info = write_set(set_name, ch, out_dir, info)
    info["seconds"] = round(time.time() - t, 1)
    with open(os.path.join(out_dir or paths.texture_set(set_name), "set.json"), "w") as f:
        json.dump(info, f, indent=1, sort_keys=True)
    return info


def bake_tiling_set(set_name, kind, tile_m=2.0, res=2048, samples=4, force=False, out_dir=None, verbose=True,
                    **params):
    """SEAMLESS tiling set from a library surface: bakes `kind` with `params` over one tile of tile_m metres
    (a number, or (u, v) for non-square tiles such as brick). All noise lives on a 4D torus, so the edges wrap
    exactly; the normal map and micro-occlusion are derived from the height with wrap-around filters. The result
    is checked numerically (seam_report) and recorded in set.json. Cached: nothing is re-baked unless the surface
    code, the parameters or the resolution changed (force=True overrides)."""
    out_dir = out_dir or paths.texture_set(set_name)
    tu, tv = (float(tile_m), float(tile_m)) if np.isscalar(tile_m) else (float(tile_m[0]), float(tile_m[1]))
    key = _source_hash(kind, (sorted((k, repr(v)) for k, v in params.items()), tu, tv, res, samples))
    old = read_set(set_name, out_dir)
    if old and old.get("hash") == key and not force and all(os.path.exists(os.path.join(out_dir, f)) for f in old["files"].values()):
        if verbose:
            print("  tiling set %s up to date" % set_name, flush=True)
        return old
    t = time.time()
    if verbose:
        print("  bake tiling set %s  (%s, %.2f x %.2f m, %d px, %d spp)" % (set_name, kind, tu, tv, res, samples), flush=True)
    import bmesh
    me = bpy.data.meshes.new("__mi_tile")
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(p) for p in ((0, 0, 0), (tu, 0, 0), (tu, tv, 0), (0, tv, 0))]
    f = bm.faces.new(vs)
    for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        lp[uvl].uv = uv
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("__mi_tile", me)
    bpy.context.scene.collection.objects.link(ob)
    m = _mat.make("__mi_tile_" + set_name, kind, tile=(tu, tv), **params)
    me.materials.append(m)
    try:
        ch = bake_channels(ob, res, samples, 0, normal=False, ao=False, verbose=verbose)
    finally:
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(me)
        bpy.data.materials.remove(m)
    pix = (tu / res, tv / res)
    ch["normal"] = normal_from_height(ch["height"], pix, wrap=True)
    ch["ao"] = ao_from_height(ch["height"], pix, _mat.SURFACES[kind].relief)
    info = {"kind": "tiling", "surface": kind, "params": {k: (v if isinstance(v, (int, float)) else list(v)) for k, v in params.items()},
            "tile_m": [tu, tv], "texel_density_px_per_m": round(res / tu, 1), "hash": key}
    info = write_set(set_name, ch, out_dir, info)
    # numeric proof of seamlessness, on the files as written
    seams = {}
    for role in ("BC", "N", "ORM", "H"):
        if role in info["files"]:
            seams[role] = seam_report(load_image(os.path.join(out_dir, info["files"][role])))
    info["seam"] = {r: {k: (round(v, 6) if isinstance(v, float) else v) for k, v in s.items()} for r, s in seams.items()}
    info["seamless"] = all(s["ok"] for s in seams.values())
    info["seconds"] = round(time.time() - t, 1)
    with open(os.path.join(out_dir, "set.json"), "w") as fjs:
        json.dump(info, fjs, indent=1, sort_keys=True)
    if verbose:
        print("    seam check: " + ", ".join("%s %.2f" % (r, s["ratio"]) for r, s in seams.items())
              + ("  -> seamless" if info["seamless"] else "  -> SEAM VISIBLE") + "   (%.0f s)" % info["seconds"], flush=True)
    if not info["seamless"]:
        raise RuntimeError("tiling set %s is not seamless: %s" % (set_name, info["seam"]))
    return info


def tiled_preview(set_name, path, repeats=2, samples=48, out_dir=None, title=None, **mat_kw):
    """Render the set tiled repeats x repeats under the day rig, straight down: left the whole block (the seams
    would run through the white ticks), right a close view of the corner where four tiles meet."""
    from PIL import Image, ImageDraw
    from . import render as _render
    import bmesh
    import tempfile
    out_dir = out_dir or paths.texture_set(set_name)
    info = read_set(set_name, out_dir) or {}
    tu, tv = info.get("tile_m", [2.0, 2.0])
    s = bpy.context.scene
    keep_cam, keep_world = s.camera, s.world
    hidden = [o for o in s.objects if not o.hide_render]
    for o in hidden:
        o.hide_render = True
    me = bpy.data.meshes.new("__mi_tiled")
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    W, Hh = tu * repeats, tv * repeats
    n = 2
    vs = [bm.verts.new(p) for p in ((0, 0, 0), (W, 0, 0), (W, Hh, 0), (0, Hh, 0))]
    f = bm.faces.new(vs)
    for lp, uv in zip(f.loops, ((0, 0), (repeats, 0), (repeats, repeats), (0, repeats))):
        lp[uvl].uv = uv
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("__mi_tiled", me)
    s.collection.objects.link(ob)
    m = _mat.from_texture_set(out_dir, name="__mi_tiled_mat", masks=False, macro=0.0, **mat_kw)
    me.materials.append(m)
    s.world = bpy.data.worlds.new("__mi_tiled_world")
    _render.setup(samples=samples, res=(720, 720))
    _render.rig_day(sun_elevation=38.0, sun_azimuth=235.0)
    tmp = tempfile.gettempdir()
    try:
        cam = _render.cam_top(bounds=((0, 0), (W, Hh)), margin=1.0, aspect=1.0)
        cam.data.ortho_scale = max(W, Hh)
        a = _render.render_png(os.path.join(tmp, "mi_tile_a_%d.png" % os.getpid()), samples, (720, 720))
        cam2 = _render.cam_top(bounds=((W / 2 - 0.3, Hh / 2 - 0.39), (W / 2 + 0.3, Hh / 2 + 0.39)), margin=1.0, aspect=552 / 720)
        cam2.data.ortho_scale = 0.78
        b = _render.render_png(os.path.join(tmp, "mi_tile_b_%d.png" % os.getpid()), samples, (552, 720))
        ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        sheet = Image.new("RGB", (1280, 720), (16, 16, 16))
        sheet.paste(ia, (0, 0))
        sheet.paste(ib, (728, 0))
        d = ImageDraw.Draw(sheet)
        for i in range(1, repeats):                      # ticks where the tile borders are
            x = round(720 * i / repeats)
            y = round(720 * i / repeats)
            for (x0, y0, x1, y1) in ((x, 0, x, 14), (x, 706, x, 720), (0, y, 14, y), (706, y, 720, y)):
                d.line((x0, y0, x1, y1), fill=(255, 255, 255), width=2)
        for (x0, y0, x1, y1) in ((728 + 276, 0, 728 + 276, 14), (728 + 276, 706, 728 + 276, 720), (728, 360, 742, 360), (1266, 360, 1280, 360)):
            d.line((x0, y0, x1, y1), fill=(255, 255, 255), width=2)
        seam = info.get("seam", {})
        worst = max((v.get("ratio", 0) for v in seam.values()), default=0)
        sheet = _render.label(sheet, "%s  %dx%d tiles of %.2f m  (%d px, %d px/m)" % (
            title or set_name, repeats, repeats, tu, info.get("resolution", [0])[0], info.get("texel_density_px_per_m", 0)), (12, 10), 17)
        sheet = _render.label(sheet, "corner where four tiles meet, 0.60 x 0.78 m   wrap step / interior step = %.2f" % worst, (740, 10), 15)
        _render.save_jpeg(sheet, path, 300)
        for p in (a, b):
            os.remove(p)
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.objects.remove(cam2, do_unlink=True)
    finally:
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(me)
        bpy.data.materials.remove(m)
        w = s.world
        s.world = keep_world
        bpy.data.worlds.remove(w)
        s.camera = keep_cam
        for o in hidden:
            o.hide_render = False
    return path
