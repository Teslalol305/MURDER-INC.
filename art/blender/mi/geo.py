"""Modelling helpers. Every function works in metres and returns a mesh object linked to the scene.

Primitives are bevelled by default: hard edges must catch light (2-10 mm on props, 5-20 mm on architecture).

    from mi import geo
    a = geo.box((0.4, 0.2, 0.1), bevel=0.004)                         # bevelled box, centred, sitting on z = 0
    b = geo.revolve([(0, 0), (0.1, 0), (0.1, 0.3), (0, 0.3)], 48)     # lathe a (radius, z) profile around Z
    c = geo.sweep(geo.rect_profile(0.05, 0.02), path, bevel=0.003)    # profile along a 3D polyline
    d = geo.pipe([(0, 0, 0), (0, 0, 1), (1, 0, 1)], radius=0.02, bend_radius=0.08)
    e = geo.plate((0.3, 0.2), 0.012, holes=[(0.05, 0.05, 0.011)], bevel=0.002)
    f = geo.instances(geo.hex_bolt(0.02), geo.ring_matrices(8, 0.12), "Bolts")   # instance then realise
    g = geo.join([a, b, c, d, e, f], "SM_Prop_Thing")
    geo.smooth_by_angle(g, 35); geo.weighted_normals(g)
    geo.uv_world_box(g, tile_m=2.0)        # tiling sets: 1 UV unit = one tile (2 m), any texel density you bake
    geo.uv_unwrap(g, res=2048)             # unique sets: smart unwrap + pack, returns px per metre
    geo.wear_from_geometry(g)              # paint the 'Wear' colour attribute (R dirt, G edges, B leaks, A splash)
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, geometry
from mathutils.bvhtree import BVHTree

from . import scene as _scene

WEAR = "Wear"          # colour attribute: R cavity dirt, G edge wear, B leak streaks, A splash-back / wetness
UV = "UVMap"


# ----------------------------------------------------------------------------------------------------- mesh plumbing

def new(name, bm, col=None, smooth=35.0, uv=True):
    """Turn a bmesh into a linked object (the bmesh is freed)."""
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = _scene.new_object(name, me, col)
    if uv and not me.uv_layers:
        me.uv_layers.new(name=UV)
    if smooth is not None:
        smooth_by_angle(ob, smooth)
    return ob


def from_arrays(name, verts, faces, col=None, smooth=35.0):
    """Object from numpy arrays: verts (n, 3) and faces (k, 3 or 4) or a list of index lists."""
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, dtype=np.float32)
    if isinstance(faces, np.ndarray) and faces.ndim == 2:
        k, m = faces.shape
        me.vertices.add(len(verts))
        me.vertices.foreach_set("co", verts.ravel())
        me.loops.add(k * m)
        me.loops.foreach_set("vertex_index", faces.astype(np.int32).ravel())
        me.polygons.add(k)
        me.polygons.foreach_set("loop_start", np.arange(0, k * m, m, dtype=np.int32))
        me.update(calc_edges=True)
    else:
        me.from_pydata([tuple(v) for v in verts], [], [list(f) for f in faces])
        me.update()
    me.validate(clean_customdata=False)
    ob = _scene.new_object(name, me, col)
    me.uv_layers.new(name=UV)
    if smooth is not None:
        smooth_by_angle(ob, smooth)
    return ob


def arrays(ob):
    """(verts (n,3) float64, normals (n,3)) of a mesh object, object space."""
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    no = np.empty(n * 3, dtype=np.float32)
    me.vertices.foreach_get("normal", no)
    return co.reshape(-1, 3).astype(np.float64), no.reshape(-1, 3).astype(np.float64)


def set_verts(ob, co):
    ob.data.vertices.foreach_set("co", np.asarray(co, dtype=np.float32).ravel())
    ob.data.update()


def bm_of(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    return bm


def bm_to(ob, bm):
    bm.normal_update()
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def join(objs, name=None, col=None):
    """Join objects into the first one (material slots and attributes are merged). Returns it."""
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    if len(objs) > 1:
        _scene.select_only(*objs)
        with bpy.context.temp_override(active_object=objs[0], object=objs[0], selected_objects=objs,
                                       selected_editable_objects=objs):
            bpy.ops.object.join()
    ob = objs[0]
    if name:
        ob.name = name
        ob.data.name = name
    if col:
        _scene.move_to(ob, col)
    return ob


def transform(ob, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), degrees=True):
    """Bake a transform straight into the mesh (rot is XYZ euler). Chainable."""
    r = [math.radians(a) for a in rot] if degrees else list(rot)
    from mathutils import Euler
    m = Matrix.Translation(loc) @ Euler(r, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal((*scale, 1.0))
    ob.data.transform(m)
    if m.determinant() < 0:
        ob.data.flip_normals()
    ob.data.update()
    return ob


def assign(ob, material, where=None):
    """Give ob a material. where=None: every face; otherwise a bool array per polygon or a function of the
    polygon centre (x, y, z) -> bool. Returns the slot index."""
    me = ob.data
    names = [m.name if m else None for m in me.materials]
    if material.name in names:
        idx = names.index(material.name)
    else:
        me.materials.append(material)
        idx = len(me.materials) - 1
    k = len(me.polygons)
    cur = np.zeros(k, dtype=np.int32)
    me.polygons.foreach_get("material_index", cur)
    if where is None:
        cur[:] = idx
    else:
        if callable(where):
            c = np.empty(k * 3, dtype=np.float32)
            me.polygons.foreach_get("center", c)
            c = c.reshape(-1, 3)
            where = where(c[:, 0], c[:, 1], c[:, 2])
        cur[np.asarray(where, dtype=bool)] = idx
    me.polygons.foreach_set("material_index", cur)
    me.update()
    return idx


# --------------------------------------------------------------------------------------------------------- shading

def smooth_by_angle(ob, angle=35.0):
    """Blender 5.x way: smooth faces + 'sharp_edge' attribute from the angle (there is no use_auto_smooth)."""
    me = ob.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(angle))
    return ob


def weighted_normals(ob, weight=50, keep_sharp=True):
    """Face-area weighted custom normals so bevels shade flat faces flat (apply once, after all modelling)."""
    md = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
    md.keep_sharp = keep_sharp
    md.mode = "FACE_AREA"
    md.weight = weight
    _apply_modifier(ob, md)
    return ob


def _apply_modifier(ob, md):
    _scene.select_only(ob)
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=md.name)


def bevel_edges(ob, width=0.003, segments=2, angle=40.0, harden=True):
    """Bevel every edge sharper than angle (modifier, applied). Use after booleans and joins."""
    md = ob.modifiers.new("bevel", "BEVEL")
    md.width = width
    md.segments = segments
    md.limit_method = "ANGLE"
    md.angle_limit = math.radians(angle)
    md.harden_normals = harden
    md.miter_outer = "MITER_ARC"
    md.use_clamp_overlap = True
    _apply_modifier(ob, md)
    return ob


def boolean(target, cutter, op="DIFFERENCE", solver="EXACT", keep_cutter=False):
    """target = target (op) cutter. Solvers in 5.3: FLOAT, EXACT, MANIFOLD."""
    md = target.modifiers.new("bool", "BOOLEAN")
    md.operation = op
    md.solver = solver
    md.object = cutter
    _apply_modifier(target, md)
    if not keep_cutter:
        bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def densify(ob, max_edge=0.03, passes=6):
    """Split edges longer than max_edge so per-vertex wear masks have somewhere to live."""
    bm = bm_of(ob)
    for _ in range(passes):
        long_edges = [e for e in bm.edges if e.calc_length() > max_edge]
        if not long_edges:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    return bm_to(ob, bm)


def displace(ob, amount=0.002, scale=3.0, seed=0, along_normal=True, mask=None):
    """Low-frequency noise displacement: nothing man-made is perfectly straight. amount in metres."""
    from mathutils import noise
    co, no = arrays(ob)
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    d = np.array([noise.noise(Vector(p) * scale + off) for p in co])
    if mask is not None:
        d = d * (mask(co[:, 0], co[:, 1], co[:, 2]) if callable(mask) else mask)
    if along_normal:
        co += no * (d * amount)[:, None]
    else:
        dv = np.array([tuple(noise.noise_vector(Vector(p) * scale + off)) for p in co])
        co += dv * amount
    set_verts(ob, co)
    return ob


# ------------------------------------------------------------------------------------------------------ primitives

def box(size=(1, 1, 1), bevel=0.005, segments=2, name="Box", base=True):
    """Bevelled box. base=True: sits on z = 0, centred in x and y; otherwise centred."""
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    if base:
        bmesh.ops.translate(bm, vec=(0, 0, sz / 2), verts=bm.verts)
    if bevel > 0:
        b = min(bevel, 0.49 * min(sx, sy, sz))
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=b, offset_type="OFFSET", segments=segments,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    return new(name, bm)


def cylinder(radius=0.5, depth=1.0, segments=32, bevel=0.0, bevel_segments=2, name="Cylinder", base=True, axis="Z"):
    """Capped cylinder with bevelled rims (a revolve underneath, so the caps are clean)."""
    b = min(bevel, 0.45 * depth, 0.45 * radius)
    prof = [(0.0, 0.0), (radius, 0.0), (radius, depth), (0.0, depth)]
    if b > 0:
        prof = fillet(prof, b, bevel_segments)
    ob = revolve(prof, segments, name=name)
    if not base:
        transform(ob, loc=(0, 0, -depth / 2))
    return _axis(ob, axis)


def tube(r_outer=0.5, r_inner=0.4, depth=1.0, segments=32, bevel=0.0, bevel_segments=2, name="Tube", axis="Z"):
    """Hollow cylinder (ring cross-section), bevelled, base on z = 0."""
    prof = [(r_inner, 0.0), (r_outer, 0.0), (r_outer, depth), (r_inner, depth)]
    b = min(bevel, 0.45 * depth, 0.45 * (r_outer - r_inner))
    if b > 0:
        prof = fillet(prof, b, bevel_segments, closed=True)
    return _axis(revolve(prof, segments, closed=True, name=name), axis)


def sphere(radius=0.5, segments=32, rings=16, name="Sphere"):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    return new(name, bm, smooth=80)


def torus(major=0.1, minor=0.02, seg_major=32, seg_minor=12, name="Torus", stretch=0.0):
    """Torus in the XY plane. stretch > 0 lengthens it along X into a chain-link shape (total extra length)."""
    a = np.linspace(0, 2 * np.pi, seg_major, endpoint=False)
    b = np.linspace(0, 2 * np.pi, seg_minor, endpoint=False)
    A, B = np.meshgrid(a, b, indexing="ij")
    cx, cy = np.cos(A), np.sin(A)
    x = (major + minor * np.cos(B)) * cx + np.sign(cx) * stretch / 2 * (np.abs(cx) > 1e-9)
    y = (major + minor * np.cos(B)) * cy
    z = minor * np.sin(B)
    verts = np.stack([x, y, z], axis=-1).reshape(-1, 3)
    i = np.arange(seg_major)[:, None]
    j = np.arange(seg_minor)[None, :]
    i1, j1 = (i + 1) % seg_major, (j + 1) % seg_minor
    f = np.stack([i * seg_minor + j, i1 * seg_minor + j, i1 * seg_minor + j1, i * seg_minor + j1], axis=-1)
    return from_arrays(name, verts, f.reshape(-1, 4), smooth=80)


def _axis(ob, axis):
    if axis == "X":
        transform(ob, rot=(0, 90, 0))
    elif axis == "Y":
        transform(ob, rot=(-90, 0, 0))
    return ob


def fillet(points, radius, segments=3, closed=False):
    """Round the corners of a 2D or 3D polyline. radius is clamped by the neighbouring segment lengths.
    Use it on lathe profiles, sweep profiles and pipe paths: it is how hard edges get their bevel."""
    pts = [np.asarray(p, dtype=np.float64) for p in points]
    n = len(pts)
    if n < 3 or radius <= 0:
        return [tuple(p) for p in pts]
    out = []
    rng_ = range(n) if closed else range(1, n - 1)
    if not closed:
        out.append(tuple(pts[0]))
    for i in rng_:
        p0, p1, p2 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        a, b = p0 - p1, p2 - p1
        la, lb = np.linalg.norm(a), np.linalg.norm(b)
        if la < 1e-9 or lb < 1e-9:
            out.append(tuple(p1))
            continue
        a, b = a / la, b / lb
        cosang = float(np.clip(np.dot(a, b), -1, 1))
        ang = math.acos(cosang)                      # interior angle at the corner
        if ang > math.pi - 1e-3 or ang < 1e-3:
            out.append(tuple(p1))
            continue
        t = radius / math.tan(ang / 2)               # distance from the corner to the tangent points
        t = min(t, 0.45 * la, 0.45 * lb)
        r = t * math.tan(ang / 2)
        bis = a + b
        bis /= np.linalg.norm(bis)
        centre = p1 + bis * (r / math.sin(ang / 2))
        s, e = p1 + a * t, p1 + b * t
        v0, v1 = s - centre, e - centre
        sweep_ang = math.pi - ang
        for k in range(segments + 1):
            f = k / segments
            # slerp between the two radius vectors
            w0 = math.sin((1 - f) * sweep_ang) / math.sin(sweep_ang)
            w1 = math.sin(f * sweep_ang) / math.sin(sweep_ang)
            out.append(tuple(centre + v0 * w0 + v1 * w1))
    if not closed:
        out.append(tuple(pts[-1]))
    return out


def rect_profile(w, h, centre=True):
    """Closed rectangular profile for sweep(), counter-clockwise."""
    if centre:
        return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    return [(0, 0), (w, 0), (w, h), (0, h)]


def circle_profile(r, segments=16):
    return [(r * math.cos(2 * math.pi * i / segments), r * math.sin(2 * math.pi * i / segments)) for i in range(segments)]


def revolve(profile, segments=48, closed=False, name="Revolve", angle=360.0, uv_v_scale=1.0):
    """Lathe a (radius, z) profile around Z. Points with radius 0 become poles. closed=True joins the last
    profile point back to the first (rings, tubes). Normals point outward when the profile runs bottom -> top
    on the outside (counter-clockwise in the (r, z) plane)."""
    prof = [(float(r), float(z)) for r, z in profile]
    m = len(prof)
    full = abs(angle - 360.0) < 1e-6
    ns = segments if full else segments + 1
    ang = np.linspace(0, math.radians(angle), segments, endpoint=False) if full else np.linspace(0, math.radians(angle), ns)
    verts, ring_start, is_pole = [], [], []
    for (r, z) in prof:
        ring_start.append(len(verts))
        if abs(r) < 1e-9:
            verts.append((0.0, 0.0, z))
            is_pole.append(True)
        else:
            for a in ang:
                verts.append((r * math.cos(a), r * math.sin(a), z))
            is_pole.append(False)
    faces = []
    pairs = list(range(m - 1)) + ([m - 1] if closed else [])
    for i in pairs:
        j = (i + 1) % m
        if is_pole[i] and is_pole[j]:
            continue
        for s in range(segments):
            s1 = (s + 1) % ns if full else s + 1
            if is_pole[i]:
                faces.append((ring_start[i], ring_start[j] + s1, ring_start[j] + s))
            elif is_pole[j]:
                faces.append((ring_start[i] + s, ring_start[i] + s1, ring_start[j]))
            else:
                faces.append((ring_start[i] + s, ring_start[i] + s1, ring_start[j] + s1, ring_start[j] + s))
    ob = from_arrays(name, np.array(verts), faces)
    return ob


def sweep(profile, path, closed_path=False, closed_profile=True, cap=True, name="Sweep", up=(0, 0, 1), bevel=0.0,
          bevel_segments=2, scale=None):
    """Sweep a 2D profile [(x, y)] along a 3D polyline. Profile x maps to the frame's side vector, y to its
    up vector (as close to `up` as the path allows). Corners are mitred. scale: optional per-path-point factor."""
    prof = list(profile)
    if bevel > 0:
        prof = fillet(prof, bevel, bevel_segments, closed=closed_profile)
    P = np.array(path, dtype=np.float64)
    n, m = len(P), len(prof)
    prof = np.array(prof, dtype=np.float64)
    upv = np.array(up, dtype=np.float64)

    def unit(v):
        ln = np.linalg.norm(v)
        return v / ln if ln > 1e-12 else v

    # tangent (bisector of the two neighbouring segments), bend direction and mitre stretch at every point
    T = np.zeros_like(P)
    bend = np.zeros_like(P)
    mitre = np.ones(n)
    for i in range(n):
        if closed_path:
            a, b = unit(P[i] - P[(i - 1) % n]), unit(P[(i + 1) % n] - P[i])
        else:
            a = unit(P[i] - P[i - 1]) if i > 0 else unit(P[1] - P[0])
            b = unit(P[i + 1] - P[i]) if i < n - 1 else unit(P[-1] - P[-2])
        t = a + b
        T[i] = unit(t) if np.linalg.norm(t) > 1e-9 else b
        d = b - a
        if np.linalg.norm(d) > 1e-9:
            bend[i] = unit(d)
            mitre[i] = 1.0 / max(0.3, float(np.dot(T[i], b)))
    # rotation-minimising frames: start from `up`, then carry the frame along the path (no twist at bends)
    side = np.cross(T[0], upv)
    if np.linalg.norm(side) < 1e-6:
        side = np.cross(T[0], np.array([0.0, 1.0, 0.0]))
    side = unit(side)
    u = unit(np.cross(side, T[0]))
    verts = np.zeros((n, m, 3))
    for i in range(n):
        if i > 0:
            q = Vector(T[i - 1]).rotation_difference(Vector(T[i]))
            side = np.array(q @ Vector(side))
            u = np.array(q @ Vector(u))
        s_ = (scale[i] if scale is not None else 1.0)
        off = (prof[:, 0:1] * s_) * side + (prof[:, 1:2] * s_) * u            # (m, 3) offsets in the cross-section
        if mitre[i] != 1.0:
            off = off + (mitre[i] - 1.0) * (off @ bend[i])[:, None] * bend[i]  # stretch along the bend direction
        verts[i] = P[i] + off
    faces = []
    rows = n if closed_path else n - 1
    cols = m if closed_profile else m - 1
    for i in range(rows):
        i1 = (i + 1) % n
        for j in range(cols):
            j1 = (j + 1) % m
            faces.append((i * m + j, i * m + j1, i1 * m + j1, i1 * m + j))
    if cap and closed_profile and not closed_path:
        faces.append(tuple(range(m - 1, -1, -1)))
        faces.append(tuple((n - 1) * m + j for j in range(m)))
    ob = from_arrays(name, verts.reshape(-1, 3), faces)
    bm = bm_of(ob)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm_to(ob, bm)
    smooth_by_angle(ob, 35)
    return ob


def pipe(path, radius=0.02, segments=16, bend_radius=0.0, bend_segments=6, cap=True, name="Pipe"):
    """Round pipe or conduit along a polyline, with filleted bends."""
    pts = fillet(path, bend_radius, bend_segments) if bend_radius > 0 else path
    return sweep(circle_profile(radius, segments), pts, cap=cap, name=name)


def plate(size=(0.3, 0.2), thickness=0.01, holes=(), bevel=0.002, hole_segments=20, name="Plate", outline=None):
    """Flat plate in XY (centred, z from 0 to thickness) with round holes [(x, y, radius)].
    outline: optional closed polygon [(x, y)] instead of the rectangle. Triangulated by constrained Delaunay,
    so there are no boolean leftovers."""
    w, h = size
    poly = list(outline) if outline is not None else [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    coords = [Vector(p) for p in poly]
    faces_in = [list(range(len(poly)))]
    for (hx, hy, hr) in holes:
        start = len(coords)
        for k in range(hole_segments):
            a = -2 * math.pi * k / hole_segments
            coords.append(Vector((hx + hr * math.cos(a), hy + hr * math.sin(a))))
        faces_in.append(list(range(start, start + hole_segments)))
    vc, _e, tris, *_ = geometry.delaunay_2d_cdt(coords, [], faces_in, 3, 1e-7)
    bm = bmesh.new()
    top = [bm.verts.new((v.x, v.y, thickness)) for v in vc]
    bot = [bm.verts.new((v.x, v.y, 0.0)) for v in vc]
    edge_count = {}
    for t in tris:
        bm.faces.new([top[i] for i in t])
        bm.faces.new([bot[i] for i in reversed(t)])
        for a, b in zip(t, list(t[1:]) + [t[0]]):
            edge_count[(a, b)] = edge_count.get((a, b), 0) + 1
    for (a, b) in edge_count:
        if (b, a) not in edge_count:                 # boundary edge: wall
            bm.faces.new([top[b], top[a], bot[a], bot[b]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # merge coplanar triangles back into n-gons so the bevel sees only real edges
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=bm.verts, edges=bm.edges)
    ob = new(name, bm)
    if bevel > 0:
        bevel_edges(ob, min(bevel, thickness * 0.45), 2, 40)
    return ob


def heightfield(xs, ys, z, name="Ground", tile_m=2.0):
    """Tensor-grid surface: xs (nx), ys (ny), z as an (ny, nx) array or a function z(X, Y). World-scale UVs
    (u = x / tile_m, v = y / tile_m). Faces are quads with +Z normals."""
    xs = np.asarray(xs, dtype=np.float64)
    ys = np.asarray(ys, dtype=np.float64)
    X, Y = np.meshgrid(xs, ys)
    Z = z(X, Y) if callable(z) else np.asarray(z, dtype=np.float64)
    nx, ny = len(xs), len(ys)
    verts = np.stack([X, Y, Z], axis=-1).reshape(-1, 3)
    i = np.arange(ny - 1)[:, None] * nx
    j = np.arange(nx - 1)[None, :]
    f = np.stack([i + j, i + j + 1, i + j + 1 + nx, i + j + nx], axis=-1).reshape(-1, 4)
    ob = from_arrays(name, verts, f, smooth=60)
    uv_world_box(ob, tile_m)
    return ob


def cut_hole(ob, polygon, z=None, pad=None, name_attr=None):
    """Cut a hole with a clean outline into a grid/heightfield mesh. polygon: [(x, y)] in object space (convex or
    star-shaped). Faces touching the polygon are removed and the gap between the jagged remainder and the exact
    outline is re-triangulated (constrained Delaunay). z: height of the outline vertices (number, function of
    (x, y), or None to take the nearest removed vertex). Returns the indices of the new outline vertices."""
    poly = [Vector(p[:2]) for p in polygon]
    cx = sum(p.x for p in poly) / len(poly)
    cy = sum(p.y for p in poly) / len(poly)
    bm = bm_of(ob)
    bm.verts.ensure_lookup_table()
    if pad is None:
        e = next(iter(bm.edges))
        pad = e.calc_length() * 0.35
    px = np.array([p.x for p in poly])
    py = np.array([p.y for p in poly])

    def inside(x, y, grow=0.0):
        # point in polygon (even-odd), optionally grown outwards from the centre
        if grow:
            d = math.hypot(x - cx, y - cy)
            if d > 1e-9:
                x, y = x - (x - cx) / d * grow, y - (y - cy) / d * grow
        c = False
        n = len(px)
        j = n - 1
        for i in range(n):
            if ((py[i] > y) != (py[j] > y)) and (x < (px[j] - px[i]) * (y - py[i]) / (py[j] - py[i] + 1e-30) + px[i]):
                c = not c
            j = i
        return c

    rad = max(math.hypot(p.x - cx, p.y - cy) for p in poly) + pad * 3
    near = [v for v in bm.verts if abs(v.co.x - cx) <= rad and abs(v.co.y - cy) <= rad]
    kill_v = set(v for v in near if inside(v.co.x, v.co.y, pad))
    kill_f = set(f for v in kill_v for f in v.link_faces)
    removed = [(v.co.x, v.co.y, v.co.z) for v in kill_v]
    ring = set(v for f in kill_f for v in f.verts if v not in kill_v)
    bmesh.ops.delete(bm, geom=list(kill_f), context="FACES")
    ring = [v for v in ring if v.is_valid]
    ring.sort(key=lambda v: math.atan2(v.co.y - cy, v.co.x - cx))
    # outline vertices
    removed_np = np.array(removed) if removed else np.zeros((1, 3))

    def z_at(x, y):
        if z is None:
            d = (removed_np[:, 0] - x) ** 2 + (removed_np[:, 1] - y) ** 2
            return float(removed_np[int(np.argmin(d)), 2])
        return float(z(x, y)) if callable(z) else float(z)

    order = sorted(range(len(poly)), key=lambda i: math.atan2(poly[i].y - cy, poly[i].x - cx))
    new_v = [bm.verts.new((poly[i].x, poly[i].y, z_at(poly[i].x, poly[i].y))) for i in order]
    coords = [Vector((v.co.x, v.co.y)) for v in ring] + [Vector((v.co.x, v.co.y)) for v in new_v]
    nr = len(ring)
    faces_in = [list(range(nr)), list(range(nr, nr + len(new_v)))]
    vc, _e, tris, ov, *_ = geometry.delaunay_2d_cdt(coords, [], faces_in, 3, 1e-7)
    allv = ring + new_v
    lut = []
    for k, v2 in enumerate(vc):
        src = ov[k]
        lut.append(allv[src[0]] if src else bm.verts.new((v2.x, v2.y, z_at(v2.x, v2.y))))
    for t in tris:
        try:
            f = bm.faces.new([lut[i] for i in t])
            f.smooth = True
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.verts.index_update()
    idx = [v.index for v in new_v]
    bm_to(ob, bm)
    return idx


def ribbon(path, width=0.04, z=0.0, lift=0.0015, name="Ribbon", width_jitter=0.3, wander=0.0, seed=0, profile="dome",
           crown=0.001, taper=0.15, step=None, tile_m=2.0):
    """Thin strip draped over the ground along a 2D polyline: tar bands, cracks, painted stripes.
    z: number or function z(x, y) of the ground. profile: 'flat', 'dome' (raised centre: crown metres) or
    'vee' (sunk centre). width_jitter: relative width noise, wander: sideways noise in metres. The strip tapers to
    a point over the first and last `taper` fraction. UVs: u along the length (metres / tile_m), v across."""
    from mathutils import noise
    P = np.array([p[:2] for p in path], dtype=np.float64)
    if step:                                               # resample at a fixed spacing
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(seg)])
        t = np.arange(0, s[-1] + step * 0.5, step)
        t[-1] = s[-1]
        P = np.stack([np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])], axis=1)
    n = len(P)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    N = np.stack([-T[:, 1], T[:, 0]], axis=1)
    rows = []
    cols = 3 if profile in ("dome", "vee") else 2
    verts = []
    for i in range(n):
        f = s[i] / max(s[-1], 1e-9)
        tp = min(1.0, f / taper, (1 - f) / taper) if taper > 0 else 1.0
        tp = max(tp, 0.02) ** 0.6
        wj = 1.0 + width_jitter * noise.noise(Vector((s[i] * 9.0, seed * 3.7, 0.0)))
        wn = wander * noise.noise(Vector((s[i] * 2.2, 11.0 + seed * 5.1, 0.0)))
        w = width * wj * tp
        c = P[i] + N[i] * wn
        for k in range(cols):
            off = (k / (cols - 1) - 0.5) * w
            p = c + N[i] * off
            zz = (z(p[0], p[1]) if callable(z) else z) + lift
            if cols == 3 and k == 1:
                zz += crown * tp if profile == "dome" else -crown * tp
            verts.append((p[0], p[1], zz))
    faces = []
    for i in range(n - 1):
        for k in range(cols - 1):
            a = i * cols + k
            faces.append((a, a + 1, a + cols + 1, a + cols))
    ob = from_arrays(name, np.array(verts), np.array(faces), smooth=80)
    bm = bm_of(ob)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bm.faces and sum(f.normal.z for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm_to(ob, bm)
    smooth_by_angle(ob, 80)
    uv = ob.data.uv_layers[0].data
    me = ob.data
    lv = np.zeros(len(me.loops), dtype=np.int32)
    me.loops.foreach_get("vertex_index", lv)
    row, col = lv // cols, lv % cols
    uvs = np.stack([s[row] / tile_m, col / (cols - 1) * (width / tile_m)], axis=1)
    uv.foreach_set("uv", uvs.astype(np.float32).ravel())
    return ob


def text(body, size=0.05, depth=0.003, bevel=0.0005, name="Text", align="CENTER", spacing=1.0, resolution=4):
    """Extruded lettering lying in XY, reading left to right along +X, raised from z = 0 to z = depth.
    Uses Blender's built-in font (Bfont, a DejaVu-like sans). Use for cast or stamped lettering and plates."""
    cu = bpy.data.curves.new(name + "_curve", "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = depth / 2
    cu.bevel_depth = bevel
    cu.bevel_resolution = 1
    cu.resolution_u = resolution
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_character = spacing
    tmp = bpy.data.objects.new(name + "_tmp", cu)
    bpy.context.scene.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(cu)
    ob = _scene.new_object(name, me)
    bm = bm_of(ob)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.translate(bm, vec=(0, 0, depth / 2), verts=bm.verts)
    bm_to(ob, bm)
    if not me.uv_layers:
        me.uv_layers.new(name=UV)
    smooth_by_angle(ob, 35)
    return ob


def text_on_arc(body, radius, size=0.05, depth=0.003, bevel=0.0005, centre_deg=90.0, name="ArcText", inside=False,
                tracking=1.0):
    """Lettering bent around a circle of the given radius in XY (manhole covers, medallions). centre_deg: where
    the middle of the text sits (90 = top). inside=False: letters stand upright at the top of the circle and read
    clockwise; inside=True: readable along the bottom, baseline toward the centre."""
    letters = []
    widths = []
    for ch in body:
        if ch == " ":
            letters.append(None)
            widths.append(size * 0.45)
            continue
        o = text(ch, size, depth, bevel, name="chr", align="CENTER")
        lo, hi = _scene.bounds(o)
        letters.append(o)
        widths.append(max(hi[0] - lo[0], size * 0.25) + size * 0.16 * tracking)
    total = sum(widths)
    ang_total = total / radius
    a0 = math.radians(centre_deg) + (ang_total / 2 if not inside else -ang_total / 2)
    out = []
    run = 0.0
    for o, w in zip(letters, widths):
        mid = run + w / 2
        run += w
        if o is None:
            continue
        a = a0 - mid / radius if not inside else a0 + mid / radius
        rot = math.degrees(a) - 90 if not inside else math.degrees(a) + 90
        transform(o, loc=(radius * math.cos(a), radius * math.sin(a), 0), rot=(0, 0, rot))
        out.append(o)
    return join(out, name)


def recalc_normals(ob, inside=False):
    """Make face winding consistent and outward (closed shapes). inside=True flips the result."""
    bm = bm_of(ob)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if inside:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm_to(ob, bm)


def face_toward(ob, point, away=False):
    """Flip the whole mesh if its faces do not look toward `point` (open shells: basin walls, skins)."""
    me = ob.data
    n = len(me.polygons)
    c = np.empty(n * 3, dtype=np.float32)
    nrm = np.empty(n * 3, dtype=np.float32)
    me.polygons.foreach_get("center", c)
    me.polygons.foreach_get("normal", nrm)
    d = np.asarray(point, dtype=np.float32)[None, :] - c.reshape(-1, 3)
    s_ = float(np.einsum("ij,ij->i", d, nrm.reshape(-1, 3)).sum())
    if (s_ < 0) != bool(away):
        me.flip_normals()
        me.update()
    return ob


# ------------------------------------------------------------------------------------------- fasteners and instances

def hex_bolt(d=0.016, head_h=None, washer=True, name="Bolt", chamfer=True):
    """Hex bolt head (d = thread diameter; across flats 1.5 d) on an optional washer, sitting on z = 0."""
    af = 1.5 * d
    h = head_h or 0.65 * d
    r = af / math.sqrt(3)                # circumradius
    z0 = 0.0
    parts = []
    if washer:
        parts.append(cylinder(1.05 * d, 0.14 * d, 20, bevel=0.03 * d, name="washer"))
        z0 = 0.14 * d
    c = 0.12 * d if chamfer else 0.0
    prof = [(0.0, z0), (r, z0), (r, z0 + h - c), (r - c * 1.6, z0 + h), (0.0, z0 + h)]
    parts.append(revolve(prof, 6, name="head"))
    smooth_by_angle(parts[-1], 20)
    return join(parts, name)


def rivet(d=0.022, height=None, segments=12, rings=4, name="Rivet"):
    """Round (button) rivet head sitting on z = 0: d = head diameter. Structural steel uses 22-38 mm heads."""
    h = height or 0.32 * d
    r = d / 2
    R = (r * r + h * h) / (2 * h)        # sphere radius of the cap
    prof = []
    a_max = math.asin(min(1.0, r / R))
    for k in range(rings + 1):
        a = a_max * (1 - k / rings)
        prof.append((R * math.sin(a), R * math.cos(a) - (R - h)))
    prof[-1] = (0.0, h)
    prof.insert(0, (r * 1.04, 0.0))
    return revolve(prof, segments, name=name)


def nut(d=0.016, name="Nut"):
    """Hex nut with the bolt end poking through, sitting on z = 0."""
    n = hex_bolt(d, head_h=0.8 * d, washer=True, name=name)
    stud = cylinder(d / 2, 1.25 * d, 16, bevel=0.06 * d, name="stud")
    return join([n, stud], name)


def ring_matrices(count, radius, z=0.0, start_deg=0.0, face_out=False, axis="Z"):
    """Matrices for a bolt circle. face_out=True turns local +Z to point away from the axis."""
    mats = []
    for i in range(count):
        a = math.radians(start_deg) + 2 * math.pi * i / count
        m = Matrix.Translation((radius * math.cos(a), radius * math.sin(a), z)) @ Matrix.Rotation(a, 4, "Z")
        if face_out:
            m = m @ Matrix.Rotation(math.radians(90), 4, "Y")
        mats.append(m)
    return mats


def line_matrices(count, start, step, rot=None):
    """Matrices for a row of fasteners: start + i * step. rot: optional 4x4 applied to each instance."""
    s, d = Vector(start), Vector(step)
    r = rot or Matrix.Identity(4)
    return [Matrix.Translation(s + d * i) @ r for i in range(count)]


def grid_matrices(nx, ny, start, dx, dy, rot=None):
    s, a, b = Vector(start), Vector(dx), Vector(dy)
    r = rot or Matrix.Identity(4)
    return [Matrix.Translation(s + a * i + b * j) @ r for j in range(ny) for i in range(nx)]


def instances(proto, matrices, name="Instances", keep_proto=False, col=None):
    """Instance-then-realise: one mesh holding a copy of proto at every matrix (rivets, bolt heads, studs).
    Thousands of copies are fine: it is plain numpy."""
    me = proto.data
    nv = len(me.vertices)
    co = np.empty(nv * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = np.concatenate([co.reshape(-1, 3), np.ones((nv, 1), dtype=np.float32)], axis=1)
    nl = len(me.loops)
    lv = np.empty(nl, dtype=np.int32)
    me.loops.foreach_get("vertex_index", lv)
    npoly = len(me.polygons)
    ls = np.empty(npoly, dtype=np.int32)
    me.polygons.foreach_get("loop_start", ls)
    mi_ = np.empty(npoly, dtype=np.int32)
    me.polygons.foreach_get("material_index", mi_)
    M = np.array([np.array(m) for m in matrices], dtype=np.float32)       # (k, 4, 4)
    k = len(M)
    allco = np.einsum("kij,nj->kni", M, co)[:, :, :3].reshape(-1, 3)
    alllv = (lv[None, :] + (np.arange(k) * nv)[:, None]).ravel()
    allls = (ls[None, :] + (np.arange(k) * nl)[:, None]).ravel()
    out = bpy.data.meshes.new(name)
    out.vertices.add(k * nv)
    out.vertices.foreach_set("co", allco.astype(np.float32).ravel())
    out.loops.add(k * nl)
    out.loops.foreach_set("vertex_index", alllv.astype(np.int32))
    out.polygons.add(k * npoly)
    out.polygons.foreach_set("loop_start", allls.astype(np.int32))
    out.polygons.foreach_set("material_index", np.tile(mi_, k))
    out.update(calc_edges=True)
    for m in me.materials:
        out.materials.append(m)
    ob = _scene.new_object(name, out, col)
    out.uv_layers.new(name=UV)
    smooth_by_angle(ob, 35)
    if not keep_proto:
        bpy.data.objects.remove(proto, do_unlink=True)
    return ob


def array_linear(ob, count, offset, name=None):
    """count copies of ob, each shifted by offset, realised into one mesh (ob is consumed)."""
    return instances(ob, line_matrices(count, (0, 0, 0), offset), name or ob.name)


def array_radial(ob, count, axis="Z", name=None, start_deg=0.0):
    """count copies of ob rotated around the world axis through the origin (ob is consumed)."""
    mats = [Matrix.Rotation(math.radians(start_deg) + 2 * math.pi * i / count, 4, axis) for i in range(count)]
    return instances(ob, mats, name or ob.name)


def chain(points, link_len=0.03, wire=0.004, name="Chain", sag=0.0, seg=(12, 6)):
    """Welded-link chain along a polyline (or between two points with a catenary-like sag in metres).
    Links alternate by 90 degrees, as real chain does."""
    pts = [Vector(p) for p in points]
    if len(pts) == 2 and sag > 0:
        a, b = pts
        pts = []
        for i in range(25):
            f = i / 24
            p = a.lerp(b, f)
            p.z -= sag * 4 * f * (1 - f)
            pts.append(p)
    # resample at the link pitch
    pitch = link_len - 2 * wire * 1.1
    seglen = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seglen)
    count = max(2, int(total / pitch))
    mats = []
    proto = torus(major=(link_len * 0.34), minor=wire, seg_major=seg[0], seg_minor=seg[1], stretch=link_len * 0.32, name="link")

    def at(d):
        for i, L in enumerate(seglen):
            if d <= L or i == len(seglen) - 1:
                f = min(1.0, d / max(L, 1e-9))
                return pts[i].lerp(pts[i + 1], f), (pts[i + 1] - pts[i]).normalized()
            d -= L
    for i in range(count):
        p, t = at((i + 0.5) * total / count)
        q = t.to_track_quat("X", "Z").to_matrix().to_4x4()
        twist = Matrix.Rotation(math.radians(90 if i % 2 else 0), 4, "X")
        mats.append(Matrix.Translation(p) @ q @ twist)
    return instances(proto, mats, name)


# -------------------------------------------------------------------------------------------------------------- UVs

def uv_world_box(ob, tile_m=2.0, offset=(0.0, 0.0), rotate90=False, layer=UV):
    """World-scale box projection for TILING sets: each face is projected along its dominant axis and
    1 UV unit = tile_m metres (tile_m may be (u_metres, v_metres) for non-square tiles such as brick).
    Texel density = bake resolution / tile_m (2048 px over 2 m = 1024 px/m). Uses world coordinates, so call it
    after the object sits where its texture should be anchored, or at the origin for modular pieces.
    rotate90=True swaps u and v (timber: u must run along the grain)."""
    me = ob.data
    tu, tv = (tile_m, tile_m) if np.isscalar(tile_m) else tile_m
    uvl = me.uv_layers.get(layer) or me.uv_layers.new(name=layer)
    nl = len(me.loops)
    lv = np.empty(nl, dtype=np.int32)
    me.loops.foreach_get("vertex_index", lv)
    co, _ = arrays(ob)
    M = np.array(ob.matrix_world)
    co = co @ M[:3, :3].T + M[:3, 3]
    npoly = len(me.polygons)
    pn = np.empty(npoly * 3, dtype=np.float32)
    me.polygons.foreach_get("normal", pn)
    pn = pn.reshape(-1, 3) @ M[:3, :3].T
    ls = np.empty(npoly, dtype=np.int32)
    lt = np.empty(npoly, dtype=np.int32)
    me.polygons.foreach_get("loop_start", ls)
    me.polygons.foreach_get("loop_total", lt)
    lp = np.repeat(np.arange(npoly), lt)                      # polygon of each loop (loops are stored in order)
    axis = np.argmax(np.abs(pn), axis=1)[lp]
    sign = np.sign(pn[np.arange(npoly), np.argmax(np.abs(pn), axis=1)])[lp]
    p = co[lv]
    u = np.where(axis == 2, p[:, 0], np.where(axis == 1, -p[:, 0] * sign, p[:, 1] * sign))
    v = np.where(axis == 2, p[:, 1] * sign, p[:, 2])
    if rotate90:
        u, v = v, -u
    uv = np.stack([u / tu + offset[0], v / tv + offset[1]], axis=1).astype(np.float32)
    uvl.data.foreach_set("uv", uv.ravel())
    me.update()
    return ob


def uv_unwrap(ob, res=2048, angle=66.0, margin_px=8, method="SMART", pack="AABB", weights=None):
    """Unique-set UVs: smart project (or 'ANGLE' unwrap along sharp edges), then pack with a pixel margin.
    pack: 'AABB' (instant), 'CONVEX' or 'CONCAVE' (tighter, but minutes on meshes with many islands).
    weights: optional per-polygon UV scale (array, or function of the face centre (x, y, z)): give hidden or
    unimportant faces 0.3 and the visible ones get the texels. Returns the median texel density in px per metre."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name=UV)
    _scene.select_only(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    margin = margin_px / float(res)
    if method == "SMART":
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle), margin_method="FRACTION", island_margin=margin,
                                 area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    else:
        bpy.ops.mesh.mark_seam(clear=True)
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(angle))
        bpy.ops.mesh.mark_seam(clear=False)
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=margin)
    if weights is not None:
        bpy.ops.object.mode_set(mode="OBJECT")
        npoly = len(me.polygons)
        if callable(weights):
            c = np.empty(npoly * 3, dtype=np.float32)
            me.polygons.foreach_get("center", c)
            c = c.reshape(-1, 3)
            weights = weights(c[:, 0], c[:, 1], c[:, 2])
        lt = np.empty(npoly, dtype=np.int32)
        me.polygons.foreach_get("loop_total", lt)
        wl = np.repeat(np.asarray(weights, dtype=np.float32), lt)
        uv = np.empty(len(me.loops) * 2, dtype=np.float32)
        me.uv_layers.active.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2) * wl[:, None]
        me.uv_layers.active.data.foreach_set("uv", uv.ravel())
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin_method="FRACTION", margin=margin, shape_method=pack)
    bpy.ops.object.mode_set(mode="OBJECT")
    return uv_texel_density(ob, res)


def uv_texel_density(ob, res=2048, layer=None):
    """Median texel density (px per metre) of the active UV layer at a texture resolution."""
    me = ob.data
    uvl = me.uv_layers.get(layer) if layer else me.uv_layers.active
    if uvl is None or len(me.polygons) == 0:
        return 0.0
    nl = len(me.loops)
    uv = np.empty(nl * 2, dtype=np.float32)
    uvl.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(np.float64)
    lv = np.empty(nl, dtype=np.int32)
    me.loops.foreach_get("vertex_index", lv)
    co, _ = arrays(ob)
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    tl = np.empty(nt * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("loops", tl)
    tl = tl.reshape(-1, 3)
    p = co[lv[tl]]
    a3 = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
    q = uv[tl]
    a2 = 0.5 * np.abs((q[:, 1, 0] - q[:, 0, 0]) * (q[:, 2, 1] - q[:, 0, 1]) - (q[:, 2, 0] - q[:, 0, 0]) * (q[:, 1, 1] - q[:, 0, 1]))
    ok = (a3 > 1e-12) & (a2 > 1e-14)
    if not ok.any():
        return 0.0
    dens = np.sqrt(a2[ok] / a3[ok]) * res
    order = np.argsort(dens)
    w = np.cumsum(a3[ok][order])
    return float(dens[order][np.searchsorted(w, w[-1] / 2)])


# ------------------------------------------------------------------------------------------------- wear mask painting

def ensure_wear(ob, fill=(0.0, 0.0, 0.0, 0.0)):
    """Make sure the mesh has the 'Wear' colour attribute (float, per corner), active for render and export.
    A missing attribute reads as alpha = 1 in shaders (everything soaking wet), so every mesh gets one."""
    me = ob.data
    ca = me.color_attributes.get(WEAR)
    if ca is None or ca.domain != "CORNER" or ca.data_type != "FLOAT_COLOR":
        if ca is not None:
            me.color_attributes.remove(ca)
        ca = me.color_attributes.new(WEAR, "FLOAT_COLOR", "CORNER")
        ca.data.foreach_set("color", np.tile(np.array(fill, dtype=np.float32), len(me.loops)))
    me.color_attributes.active_color = ca
    try:
        me.color_attributes.render_color_index = list(me.color_attributes).index(ca)
    except Exception:
        pass
    return ca


def get_wear(ob, per="vertex"):
    """Wear mask as a numpy array (n, 4): per='vertex' (mean of the corners) or per='corner'."""
    ca = ensure_wear(ob)
    me = ob.data
    nl = len(me.loops)
    c = np.empty(nl * 4, dtype=np.float32)
    ca.data.foreach_get("color", c)
    c = c.reshape(-1, 4)
    if per == "corner":
        return c
    lv = np.empty(nl, dtype=np.int32)
    me.loops.foreach_get("vertex_index", lv)
    out = np.zeros((len(me.vertices), 4), dtype=np.float64)
    cnt = np.zeros(len(me.vertices))
    np.add.at(out, lv, c)
    np.add.at(cnt, lv, 1)
    return out / np.maximum(cnt, 1)[:, None]


def set_wear(ob, values, per="vertex"):
    """Write the whole wear mask from an (n_vertices, 4) or (n_corners, 4) array."""
    ca = ensure_wear(ob)
    me = ob.data
    v = np.clip(np.asarray(values, dtype=np.float32), 0.0, 1.0)
    if per == "vertex":
        lv = np.empty(len(me.loops), dtype=np.int32)
        me.loops.foreach_get("vertex_index", lv)
        v = v[lv]
    ca.data.foreach_set("color", np.ascontiguousarray(v).ravel())
    me.update()
    return ob


CH = {"R": 0, "G": 1, "B": 2, "A": 3, "dirt": 0, "edge": 1, "leak": 2, "splash": 3, "wet": 3}


def paint(ob, channel, value, mode="max", faces=None):
    """Paint one wear channel. value: number, per-vertex array, or function (x, y, z) -> array in OBJECT space.
    mode: 'set', 'max', 'add', 'mul'. faces: optional bool array per polygon (or material slot index) to
    restrict the paint to the corners of those faces: neighbouring faces keep their own value at shared
    vertices, which is why the attribute lives on corners."""
    me = ob.data
    ch = CH[channel]
    c = get_wear(ob, per="corner").copy()
    nl = len(me.loops)
    lv = np.empty(nl, dtype=np.int32)
    me.loops.foreach_get("vertex_index", lv)
    co, _ = arrays(ob)
    if callable(value):
        val = np.asarray(value(co[:, 0], co[:, 1], co[:, 2]), dtype=np.float64)
    else:
        val = np.asarray(value, dtype=np.float64)
    val = np.broadcast_to(val, (len(co),))[lv] if val.ndim <= 1 and val.size in (1, len(co)) else val
    sel = np.ones(nl, dtype=bool)
    if faces is not None:
        npoly = len(me.polygons)
        lt = np.empty(npoly, dtype=np.int32)
        me.polygons.foreach_get("loop_total", lt)
        if np.isscalar(faces):
            mi_ = np.empty(npoly, dtype=np.int32)
            me.polygons.foreach_get("material_index", mi_)
            faces = mi_ == int(faces)
        sel = np.repeat(np.asarray(faces, dtype=bool), lt)
    old = c[:, ch]
    if mode == "set":
        new_ = val
    elif mode == "add":
        new_ = old + val
    elif mode == "mul":
        new_ = old * val
    else:
        new_ = np.maximum(old, val)
    c[:, ch] = np.where(sel, np.clip(new_, 0, 1), old)
    set_wear(ob, c, per="corner")
    return ob


def _adjacency(me):
    ne = len(me.edges)
    ev = np.empty(ne * 2, dtype=np.int32)
    me.edges.foreach_get("vertices", ev)
    return ev.reshape(-1, 2)


def _blur(values, ev, n, iters=2):
    v = values.astype(np.float64).copy()
    for _ in range(iters):
        acc = v.copy()
        cnt = np.ones(n)
        np.add.at(acc, ev[:, 0], v[ev[:, 1]])
        np.add.at(acc, ev[:, 1], v[ev[:, 0]])
        np.add.at(cnt, ev[:, 0], 1)
        np.add.at(cnt, ev[:, 1], 1)
        v = acc / cnt
    return v


def curvature(ob):
    """Per-vertex signed curvature proxy in about [-1, 1]: > 0 concave (cavity), < 0 convex (exposed edge)."""
    me = ob.data
    co, no = arrays(ob)
    ev = _adjacency(me)
    d = co[ev[:, 1]] - co[ev[:, 0]]
    ln = np.maximum(np.linalg.norm(d, axis=1), 1e-12)
    d /= ln[:, None]
    n = len(co)
    acc = np.zeros(n)
    cnt = np.zeros(n)
    np.add.at(acc, ev[:, 0], np.einsum("ij,ij->i", no[ev[:, 0]], d))
    np.add.at(acc, ev[:, 1], np.einsum("ij,ij->i", no[ev[:, 1]], -d))
    np.add.at(cnt, ev[:, 0], 1)
    np.add.at(cnt, ev[:, 1], 1)
    return acc / np.maximum(cnt, 1)


def occlusion(ob, distance=0.15, rays=16, seed=1, others=()):
    """Per-vertex ambient occlusion in [0, 1] (1 = fully enclosed) by BVH ray casts over the normal hemisphere.
    others: extra objects that shadow this one (the ground, neighbouring parts)."""
    co, no = arrays(ob)
    M = np.array(ob.matrix_world)
    cw = co @ M[:3, :3].T + M[:3, 3]
    nw = no @ np.linalg.inv(M[:3, :3])
    nw /= np.maximum(np.linalg.norm(nw, axis=1, keepdims=True), 1e-12)
    dg = bpy.context.evaluated_depsgraph_get()
    r = np.random.default_rng(seed)
    dirs = r.normal(size=(rays, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    # per vertex: flip each direction into the normal hemisphere, bias toward the normal
    D = dirs[None, :, :] * np.sign(np.einsum("rj,nj->nr", dirs, nw))[:, :, None]
    D = D * 0.75 + nw[:, None, :] * 0.25
    D /= np.linalg.norm(D, axis=2, keepdims=True)
    P0 = cw + nw * 2e-4
    occ = np.zeros(len(co))
    hit_any = np.zeros((len(co), rays), dtype=bool)
    for o in (ob, *others):
        tree = BVHTree.FromObject(o, dg)
        Mi = np.array(o.matrix_world.inverted())
        Pl = (P0 @ Mi[:3, :3].T + Mi[:3, 3]).tolist()
        Dl = (D @ Mi[:3, :3].T).tolist()
        cast = tree.ray_cast
        for i in range(len(co)):
            p = Pl[i]
            di = Dl[i]
            acc = 0.0
            for k in range(rays):
                if hit_any[i, k]:
                    continue
                h = cast(p, di[k], distance)
                if h[0] is not None:
                    hit_any[i, k] = True
                    acc += 1.0 - 0.5 * h[3] / distance
            occ[i] += acc
    return np.clip(occ / rays, 0, 1)


def wear_from_geometry(ob, cavity=1.0, edge=1.0, leak=1.0, splash=1.0, ao_distance=0.12, ao_rays=12,
                       leak_sources=None, leak_auto=True, leak_length=0.35, leak_width=0.02, ground_z=None,
                       splash_height=0.18, others=(), seed=0, blur=1):
    """Paint the Wear attribute from the shape itself. Physical causes only:

    R  cavity dirt    concave creases and occluded pockets (ambient occlusion + curvature) hold grime
    G  edge wear      convex, exposed edges get knocked and rubbed: paint chips there first
    B  leak streaks   water runs down from crevices, fasteners and ledges: pass leak_sources=[(x, y, z)] (object
                      space) for bolt heads and seams, leak_auto adds the deepest crevices
    A  splash-back    rain throws dirt up the first ~0.2 m above the ground (ground_z, default: lowest vertex)

    The mesh needs enough vertices for the masks to live on: geo.densify() flat panels first.
    Each factor scales its channel (0 switches it off). Returns the (n, 4) per-vertex array."""
    from mathutils import noise
    me = ob.data
    co, no = arrays(ob)
    n = len(co)
    ev = _adjacency(me)
    r = np.random.default_rng(seed + 17)
    curv = curvature(ob)
    out = np.zeros((n, 4))
    occ = occlusion(ob, ao_distance, ao_rays, seed, others) if (cavity > 0 or leak_auto) and ao_rays > 0 else np.zeros(n)
    if cavity > 0:
        conc = _blur(np.clip(curv * 4.0, 0, 1), ev, n, blur)
        out[:, 0] = np.clip((occ * 1.25 + conc * 0.6) * cavity, 0, 1)
    if edge > 0:
        conv = np.clip(-curv * 5.0, 0, 1)
        conv = np.maximum(conv, _blur(conv, ev, n, blur) * 0.9)
        expo = 1.0 - occ
        out[:, 1] = np.clip(conv * (0.45 + 0.55 * expo) * edge, 0, 1)
    if leak > 0:
        src = [np.asarray(p, dtype=np.float64) for p in (leak_sources or [])]
        if leak_auto:
            # deep, sideways-facing crevices hold water and bleed rust
            cand = np.nonzero((occ > 0.55) & (np.abs(no[:, 2]) < 0.75))[0]
            if len(cand) > 160:
                cand = r.choice(cand, 160, replace=False)
            src += [co[i] for i in cand]
        b = np.zeros(n)
        vert = np.clip(1.0 - np.abs(no[:, 2]) * 1.2, 0, 1)        # only on steep faces
        for k, s in enumerate(src):
            L = leak_length * (0.35 + 0.65 * r.random())
            w = leak_width * (0.6 + 0.9 * r.random())
            dz = s[2] - co[:, 2]
            dh = np.hypot(co[:, 0] - s[0], co[:, 1] - s[1])
            m = (dz > -0.004) & (dz < L) & (dh < 3 * w + 0.5 * dz * 0.15)
            if not m.any():
                continue
            fall = np.exp(-(dh[m] / (w * (1 + dz[m] / L))) ** 2) * (1 - dz[m] / L) ** 0.7
            b[m] = np.maximum(b[m], fall)
        out[:, 2] = np.clip(b * vert * leak, 0, 1)
    if splash > 0:
        M = np.array(ob.matrix_world)
        zw = (co @ M[:3, :3].T + M[:3, 3])[:, 2]
        g = float(zw.min()) if ground_z is None else ground_z
        h = np.clip((zw - g) / splash_height, 0, None)
        nz = np.array([noise.noise(Vector(p) * 14.0) for p in co]) * 0.25
        out[:, 3] = np.clip((np.exp(-h * 2.2) * (1.0 - 0.5 * np.clip(no[:, 2], 0, 1)) + nz * np.exp(-h)) * splash, 0, 1)
    set_wear(ob, out)
    return out


# ------------------------------------------------------------------------------------------------------- inspection

def stats(ob):
    """Triangle and vertex counts of the mesh as exported (n-gons triangulated)."""
    me = ob.data
    me.calc_loop_triangles()
    return {"triangles": len(me.loop_triangles), "vertices": len(me.vertices)}
