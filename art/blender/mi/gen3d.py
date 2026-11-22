"""Generated meshes (image-to-3D GLB files from art/out/gen/) brought into the pipeline.

    from mi import gen3d
    ob, tex = gen3d.load("art/out/gen/vehicles/sedan_hunyuan.glb", "Gen_Sedan")   # one joined mesh + its maps
    gen3d.orient(ob, length_axis="Y", nose_sign=-1)        # length on X, nose at +X, centred, wheels on z = 0
    gen3d.fit_box(ob, (4.61, 1.85, 1.45))                  # non-uniform scale to the brief's box
    gen3d.warp_x(ob, [(-2.2, -2.305), (x_rear, -1.38), (x_front, 1.42), (2.2, 2.305)])   # piecewise-linear in x
    rgb, mr = gen3d.face_samples(ob, tex)                  # per-face base colour and (rough, metal) from the maps
    gen3d.delete_faces(ob, mask)

tex is a dict of numpy float32 arrays read from the GLB's images: 'bc' (linear RGB, h x w x 3), 'rough', 'metal'
(h x w) and 'normal' (h x w x 3, 0..1 OpenGL), plus 'size'. Everything is metres, Z up (Blender's glTF importer
already converts from +Y up).
"""
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

from . import scene as _scene
from . import bake as _bake


def _image_array(img, srgb, cache_dir=None):
    """The image as float32 numpy (h, w, 3), top row first; srgb images are decoded to linear. The pixels are
    read through a PNG written next to the GLB (8-bit, much lighter than Image.pixels)."""
    from PIL import Image
    cache_dir = cache_dir or bpy.app.tempdir
    os.makedirs(cache_dir, exist_ok=True)
    p = os.path.join(cache_dir, bpy.path.clean_name(img.name) + ".png")
    if not os.path.exists(p):
        img.filepath_raw = p
        img.file_format = "PNG"
        img.save()
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0
    return _bake.srgb_decode(a) if srgb else a


def load(path, name, col=None):
    """Import a generated GLB, join every mesh into one object (transforms applied) and read its PBR maps.
    Returns (object, tex). The imported material stays on the object (slot 0) until it is replaced."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    for o in new:
        if o.type != "MESH":
            pass
    for o in meshes:
        o.matrix_world = o.matrix_world.copy()
    _scene.select_only(*meshes)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    # unparent and apply the transform
    mw = ob.matrix_world.copy()
    ob.parent = None
    ob.data.transform(mw)
    ob.matrix_world = Matrix.Identity(4)
    for o in new:
        if o != ob and o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    ob.name = name
    ob.data.name = name
    if col is not None:
        _scene.move_to(ob, col)
    tex = {}
    cache = os.path.splitext(path)[0] + "_maps"
    m = ob.data.materials[0] if ob.data.materials else None
    if m is not None and m.node_tree:
        for n in m.node_tree.nodes:
            if n.type != "TEX_IMAGE" or n.image is None:
                continue
            nm = n.image.name.lower()
            if "normal" in nm:
                tex["normal"] = _image_array(n.image, False, cache)
            elif "rough" in nm or "metal" in nm:
                a = _image_array(n.image, False, cache)
                tex["rough"], tex["metal"] = a[..., 1].copy(), a[..., 2].copy()
            else:
                tex["bc"] = _image_array(n.image, True, cache)
        if "bc" in tex:
            tex["size"] = tex["bc"].shape[1], tex["bc"].shape[0]
    return ob, tex


def verts(ob):
    co = np.empty(len(ob.data.vertices) * 3, dtype=np.float64)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def set_verts(ob, co):
    ob.data.vertices.foreach_set("co", np.ascontiguousarray(co, dtype=np.float32).ravel())
    ob.data.update()


def orient(ob, length_axis="Y", nose_sign=1.0):
    """Turn the mesh so its length runs along X with the nose at +X, centre it in x and y and stand it on z = 0.
    length_axis: the axis the generated mesh is long in; nose_sign: +1 when the nose is at the positive end."""
    co = verts(ob)
    if length_axis.upper() == "Y":
        x, y = co[:, 1] * nose_sign, -co[:, 0] * nose_sign
    else:
        x, y = co[:, 0] * nose_sign, co[:, 1] * nose_sign
    co = np.stack([x, y, co[:, 2]], axis=1)
    lo, hi = co.min(0), co.max(0)
    co[:, 0] -= (lo[0] + hi[0]) / 2
    co[:, 1] -= (lo[1] + hi[1]) / 2
    co[:, 2] -= lo[2]
    set_verts(ob, co)
    return ob


def fit_box(ob, size):
    """Non-uniform scale so the bounding box is exactly size (x, y, z), centred in x and y, standing on z = 0."""
    co = verts(ob)
    lo, hi = co.min(0), co.max(0)
    s = np.array(size, dtype=np.float64) / np.maximum(hi - lo, 1e-9)
    c = (lo + hi) / 2
    co = (co - c) * s
    co[:, 2] -= co[:, 2].min()
    set_verts(ob, co)
    return s


def warp(ob, axis, knots):
    """Piecewise-linear remap of one coordinate: knots = [(old, new), ...] sorted by old (extrapolates linearly)."""
    k = sorted(knots)
    old = np.array([a for a, _ in k])
    new = np.array([b for _, b in k])
    co = verts(ob)
    v = co[:, axis]
    out = np.interp(v, old, new)
    lo_m = (new[1] - new[0]) / (old[1] - old[0])
    hi_m = (new[-1] - new[-2]) / (old[-1] - old[-2])
    out = np.where(v < old[0], new[0] + (v - old[0]) * lo_m, out)
    out = np.where(v > old[-1], new[-1] + (v - old[-1]) * hi_m, out)
    co[:, axis] = out
    set_verts(ob, co)


def face_arrays(ob):
    """(centres (n, 3), normals (n, 3), areas (n,)) of the polygons."""
    me = ob.data
    n = len(me.polygons)
    c = np.empty(n * 3)
    me.polygons.foreach_get("center", c)
    nn = np.empty(n * 3)
    me.polygons.foreach_get("normal", nn)
    a = np.empty(n)
    me.polygons.foreach_get("area", a)
    return c.reshape(-1, 3), nn.reshape(-1, 3), a


def face_uv(ob, layer=None):
    """UV centroid of every polygon (n, 2)."""
    me = ob.data
    uvl = me.uv_layers[layer] if layer else me.uv_layers.active
    uv = np.empty(len(me.loops) * 2)
    uvl.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    ls = np.empty(len(me.polygons), dtype=np.int64)
    lt = np.empty(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get("loop_start", ls)
    me.polygons.foreach_get("loop_total", lt)
    idx = np.repeat(np.arange(len(ls)), lt)
    s = np.zeros((len(ls), 2))
    np.add.at(s, idx, uv)
    return s / lt[:, None]


def sample(tex_arr, uv):
    """Nearest texel of an (h, w[, c]) array (top row first) at UVs (n, 2) (v up, wrapped)."""
    h, w = tex_arr.shape[:2]
    x = np.clip((np.mod(uv[:, 0], 1.0) * w).astype(np.int64), 0, w - 1)
    y = np.clip(((1.0 - np.mod(uv[:, 1], 1.0)) * h).astype(np.int64), 0, h - 1)
    return tex_arr[y, x]


def face_samples(ob, tex, blur=2):
    """Per-face base colour (n, 3), roughness and metallic, sampled at the face's UV centroid. blur: box radius in
    texels applied to the maps first (generated atlases are noisy at the texel level)."""
    uv = face_uv(ob)
    bc = tex["bc"]
    if blur:
        bc = _box(bc, blur)
    rgb = sample(bc, uv)
    rough = sample(tex["rough"], uv) if "rough" in tex else np.full(len(uv), 0.5)
    metal = sample(tex["metal"], uv) if "metal" in tex else np.zeros(len(uv))
    return rgb, rough, metal


def _box(a, r):
    from PIL import Image, ImageFilter
    if a.ndim == 2:
        im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
        return np.asarray(im.filter(ImageFilter.BoxBlur(r)), dtype=np.float32) / 255.0
    im = Image.fromarray(np.clip(_bake.srgb_encode(a) * 255, 0, 255).astype(np.uint8))
    return _bake.srgb_decode(np.asarray(im.filter(ImageFilter.BoxBlur(r)), dtype=np.float32) / 255.0)


def delete_faces(ob, mask):
    """Delete the polygons where mask is True (and the vertices left loose)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    kill = [bm.faces[i] for i in np.nonzero(mask)[0]]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def split_faces(ob, mask, name, col=None):
    """Move the polygons where mask is True into a new object (same UVs and materials). Returns it."""
    cp = ob.copy()
    cp.data = ob.data.copy()
    cp.name = name
    cp.data.name = name
    (col or ob.users_collection[0]).objects.link(cp)
    delete_faces(cp, ~mask)
    delete_faces(ob, mask)
    return cp


def set_face_materials(ob, index):
    """Assign material slot indices per polygon from an (n,) int array."""
    ob.data.polygons.foreach_set("material_index", np.ascontiguousarray(index, dtype=np.int32))
    ob.data.update()


def decimate(ob, ratio, triangulate=True):
    """Collapse decimation that keeps UV seams and the material borders."""
    md = ob.modifiers.new("Decimate", "DECIMATE")
    md.decimate_type = "COLLAPSE"
    md.ratio = ratio
    md.use_collapse_triangulate = triangulate
    md.delimit = {"UV", "MATERIAL", "SEAM"} if hasattr(md, "delimit") else set()
    _scene.select_only(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=md.name)
    return ob


def save_texture(arr, path, srgb=True):
    """Write a float array (linear when srgb) as an 8-bit PNG."""
    a = _bake.srgb_encode(arr) if srgb else arr
    return _bake.save_png(a, path)


def exists(path):
    return os.path.exists(path)
