"""Scene plumbing: empty metric scene, collections, seeded RNG, transforms and pivots.

    from mi import scene
    scene.reset()                              # empty file, metres, Cycles on CPU with 3 threads
    col = scene.collection("Street")           # get or create, linked to the scene
    rng = scene.rng("street", 3)               # numpy Generator, stable for the same key
    ob = scene.new_object("SM_Prop_Thing", mesh, col)
    scene.apply_transforms(ob)                 # bake location/rotation/scale into the mesh
    scene.set_pivot(ob, (0, 0, 0))             # move the origin, geometry stays where it is
"""
import hashlib
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

THREADS = 3  # the build machines are shared: never take every core


def reset(threads=THREADS, samples=96):
    """Factory-empty file, metric units, Cycles on CPU with a fixed thread count. Returns the scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 1.0
    s.unit_settings.length_unit = "METERS"
    setup_cycles(s, threads=threads, samples=samples)
    return s


def setup_cycles(s=None, threads=THREADS, samples=96, denoise=True, bounces=6):
    """Cycles, CPU, fixed threads, OpenImageDenoise. Safe to call again to change samples."""
    s = s or bpy.context.scene
    s.render.engine = "CYCLES"          # 'CYCLES' is valid even though bl_rna lists only EEVEE (dynamic enum)
    c = s.cycles
    c.device = "CPU"
    s.render.threads_mode = "FIXED"
    s.render.threads = int(threads)
    c.samples = int(samples)
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.use_denoising = bool(denoise)
    if denoise:
        c.denoiser = "OPENIMAGEDENOISE"  # the only denoiser in the CPU build
        c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        c.denoising_prefilter = "ACCURATE"
    c.max_bounces = bounces
    c.diffuse_bounces = min(3, bounces)
    c.glossy_bounces = min(4, bounces)
    c.transmission_bounces = min(6, bounces)
    c.transparent_max_bounces = 8
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.sample_clamp_indirect = 8.0
    return s


def rng(*key):
    """A numpy Generator seeded from any hashable key, e.g. rng('street', 'road', 2). Same key, same numbers."""
    h = hashlib.sha256(repr(key).encode("utf8")).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


def collection(name, parent=None):
    """Get or create a collection and make sure it is linked under parent (default: the scene root)."""
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
    root = parent or bpy.context.scene.collection
    if col.name not in [c.name for c in root.children]:
        try:
            root.children.link(col)
        except RuntimeError:
            pass
    return col


def new_object(name, mesh, col=None, location=(0, 0, 0)):
    """Wrap a mesh in an object and link it."""
    ob = bpy.data.objects.new(name, mesh)
    mesh.name = name
    ob.location = location
    link(ob, col)
    return ob


def link(ob, col=None):
    col = col or bpy.context.scene.collection
    if ob.name not in col.objects:
        col.objects.link(ob)
    return ob


def move_to(ob, col):
    """Make col the only collection of ob."""
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    col.objects.link(ob)
    return ob


def select_only(*obs):
    """Deselect everything, select obs, make the first active. Operators (bake, export, uv) rely on this."""
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    for o in obs:
        o.hide_set(False)
        o.select_set(True)
    if obs:
        vl.objects.active = obs[0]
    return obs[0] if obs else None


def apply_transforms(ob, location=True, rotation=True, scale=True):
    """Bake the object transform into the mesh data (no operator, works on linked data too if single user)."""
    loc, rot, scl = ob.matrix_basis.decompose()
    m = Matrix.Identity(4)
    keep = Matrix.Identity(4)
    T = Matrix.Translation(loc)
    R = rot.to_matrix().to_4x4()
    S = Matrix.Diagonal((*scl, 1.0))
    m = (T if location else Matrix.Identity(4)) @ (R if rotation else Matrix.Identity(4)) @ (S if scale else Matrix.Identity(4))
    keep = (Matrix.Identity(4) if location else T) @ (Matrix.Identity(4) if rotation else R) @ (Matrix.Identity(4) if scale else S)
    ob.data.transform(m)
    if m.determinant() < 0:
        ob.data.flip_normals()
    ob.matrix_basis = keep
    ob.data.update()
    return ob


def set_pivot(ob, point, world=True):
    """Move the object origin to point (world space by default) without moving the geometry."""
    p = Vector(point)
    local = ob.matrix_world.inverted() @ p if world else p
    ob.data.transform(Matrix.Translation(-local))
    ob.matrix_world = ob.matrix_world @ Matrix.Translation(local)
    ob.data.update()
    return ob


def pivot_ground_centre(ob):
    """Prop convention: origin at the centre of the footprint, on the ground (lowest z)."""
    lo, hi = bounds(ob, world=True)
    return set_pivot(ob, ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))


def bounds(ob, world=False):
    """(min, max) corners of the mesh as numpy arrays; object space unless world=True."""
    n = len(ob.data.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    ob.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    if world:
        m = np.array(ob.matrix_world, dtype=np.float64)
        co = co @ m[:3, :3].T + m[:3, 3]
    return co.min(axis=0), co.max(axis=0)


def duplicate(ob, name=None, linked=True, col=None):
    """Copy an object. linked=True shares the mesh (an instance: use for repeated modules)."""
    cp = ob.copy()
    if not linked:
        cp.data = ob.data.copy()
    if name:
        cp.name = name
    link(cp, col or (ob.users_collection[0] if ob.users_collection else None))
    return cp


def place(ob, location=(0, 0, 0), rot_z_deg=0.0):
    ob.location = location
    ob.rotation_euler = (0.0, 0.0, math.radians(rot_z_deg))
    return ob


def save_blend(path):
    """Save the current file (compressed). Works from the bpy module: there is no 'current file' until this runs."""
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True, copy=True, check_existing=False)
    return path


def purge_orphans():
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


# Coordinate conventions -------------------------------------------------------------------------------------------

def web_to_blender(x, y, z):
    """three.js game (metres, +Y up, north = -Z) -> Blender (Z up, north = +Y)."""
    return (x, -z, y)


def blender_to_unreal(x, y, z):
    """Blender metres -> Unreal centimetres (X east, Y south, Z up)."""
    return (x * 100.0, -y * 100.0, z * 100.0)
