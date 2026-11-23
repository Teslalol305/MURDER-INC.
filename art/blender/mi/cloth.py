"""Garments for characters: pattern-like start shapes as signed distance lofts, meshing with open edges, Blender
cloth simulation onto a collider in the rest pose (drape), and the finishing a real garment needs (turned hems
with thickness, ribbed bands, quilt loft).

    from mi import cloth, sdf
    torso = cloth.Loft([(c, u, v, a, b, n), ...])           # sections along a polyline axis
    f = lambda p: sdf.smin(torso(p), sleeve(p), 0.04)
    ob = cloth.garment_mesh("Hoodie", f, lo, hi, 0.01, cuts=[(point, normal), ...])   # open where cut
    cloth.drape(ob, [collider], frames=60, pin=pin_weights, shrink=grow_weights)        # folds by simulation
    cloth.hem_facing(ob, depth=0.02, thickness=0.003)        # the edge turned in: thickness at hems and cuffs

Everything is metres, Z up, the character at the origin facing -Y (the mannequin's rest pose).
"""
import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import scene as _scene
from . import sdf as _sdf


# ------------------------------------------------------------------------------------------------ lofts


class Loft:
    """Tube along a polyline with superelliptic sections: stations (centre (3,), u (3,), v (3,), a, b, n),
    u and v the section axes (unit, roughly perpendicular to the axis), a and b the half extents along them,
    n the superellipse exponent (2 = ellipse, larger = boxier). Distance is approximate (exact for circles):
    enough for surface nets and projection. Ends are open-ended caps (axial overshoot)."""

    def __init__(self, stations, cap=True):
        self.c = np.array([s[0] for s in stations], dtype=np.float64)
        self.u = np.array([s[1] for s in stations], dtype=np.float64)
        self.v = np.array([s[2] for s in stations], dtype=np.float64)
        self.a = np.array([s[3] for s in stations], dtype=np.float64)
        self.b = np.array([s[4] for s in stations], dtype=np.float64)
        self.n = np.array([s[5] if len(s) > 5 else 2.0 for s in stations], dtype=np.float64)
        self.cap = cap

    def params(self, p):
        """(segment index, t in 0..1 unclamped at the ends, local x, y, axial overshoot) of points p."""
        best = None
        K = len(self.c) - 1
        for k in range(K):
            A, B = self.c[k], self.c[k + 1]
            ab = B - A
            L2 = float(ab @ ab)
            t = ((p - A) @ ab) / L2
            tc = np.clip(t, 0.0, 1.0)
            q = A + tc[:, None] * ab
            d = np.linalg.norm(p - q, axis=1)
            if k == 0:
                d = np.where(t < 0, np.linalg.norm(p - A, axis=1) * 0 + d, d)
            if best is None:
                best = (d, np.full(len(p), k), t)
            else:
                m = d < best[0]
                best = (np.where(m, d, best[0]), np.where(m, k, best[1]), np.where(m, t, best[2]))
        _, k, t = best
        tt = np.clip(t, 0.0, 1.0)
        lerp = lambda X: X[k] + (X[k + 1] - X[k]) * tt[:, None] if X.ndim == 2 else X[k] + (X[k + 1] - X[k]) * tt
        c, u, v = lerp(self.c), lerp(self.u), lerp(self.v)
        w = self.c[k + 1] - self.c[k]
        L = np.linalg.norm(w, axis=1)
        w = w / L[:, None]
        r = p - c
        r = r - np.einsum("ij,ij->i", r, w)[:, None] * w
        x = np.einsum("ij,ij->i", r, u)
        y = np.einsum("ij,ij->i", r, v)
        over = np.where(t < 0, -t * L, 0.0) * (k == 0) + np.where(t > 1, (t - 1) * L, 0.0) * (k == K - 1)
        return k, tt, x, y, over, lerp

    def __call__(self, p):
        k, tt, x, y, over, lerp = self.params(p)
        a, b, n = lerp(self.a), lerp(self.b), lerp(self.n)
        ax, ay = np.abs(x) / a, np.abs(y) / b
        r = (ax ** n + ay ** n) ** (1.0 / n)
        rho = np.sqrt(x * x + y * y)
        reff = rho / np.maximum(r, 1e-9)
        reff = np.where(r < 1e-6, np.minimum(a, b), reff)
        d = (r - 1.0) * reff
        if self.cap:
            d = np.where(over > 0, np.where(d > 0, np.sqrt(np.maximum(d, 0) ** 2 + over ** 2), np.maximum(d, over)), d)
        return d


def plane(p, point, normal):
    """Signed distance to a plane, positive on the side `normal` points to."""
    n = np.asarray(normal, dtype=np.float64)
    n = n / np.linalg.norm(n)
    return (p - np.asarray(point, dtype=np.float64)) @ n


# ------------------------------------------------------------------------------------------------ meshing


def garment_mesh(name, f, lo, hi, h, cuts=(), col=None, relax=4, keep_largest=True, frame=None, origin=(0, 0, 0)):
    """Mesh the surface f = 0 with surface nets, open along the cut planes: cuts is a list of (point, normal)
    (or (point, normal, radius): the cut only acts within `radius` of the point) with the normal pointing to
    the part that is REMOVED. The field is clipped by the planes (so the surface
    ends exactly on them), the cap faces on the planes are deleted, and the boundary vertices are put back onto
    their plane. Returns the object (quads, outward normals)."""
    cuts = [(np.asarray(c[0], dtype=np.float64), np.asarray(c[1], dtype=np.float64) / np.linalg.norm(c[1]),
             c[2] if len(c) > 2 else None) for c in cuts]

    def g(p):
        d = f(p)
        for c, n, rad in cuts:
            s = (p - c) @ n
            if rad is not None:
                s = np.where(np.linalg.norm(p - c, axis=1) < rad, s, -1.0)
            d = np.maximum(d, s)
        return d
    v, q = _sdf.surface_nets(g, lo, hi, h, frame=frame, origin=origin)
    if keep_largest:
        v, q = _sdf.keep_largest(v, q)
    v = safe_project(g, v, 3, h)
    # cap faces: every corner on a cut plane
    on = np.zeros(len(v), dtype=bool)
    which = -np.ones(len(v), dtype=np.int64)
    for i, (c, n, rad) in enumerate(cuts):
        s = (v - c) @ n
        m = np.abs(s) < h * 0.35
        if rad is not None:
            m &= np.linalg.norm(v - c, axis=1) < rad
        on |= m
        which[m] = i
    cap = on[q].all(axis=1)
    q = q[~cap]
    used = np.unique(q)
    remap = -np.ones(len(v), dtype=np.int64)
    remap[used] = np.arange(len(used))
    v, q, which = v[used], remap[q], which[used]
    # relax with the boundary pinned onto its plane
    ob = _sdf.to_mesh(name, v, q, col)
    bnd = boundary_vertices(ob)
    if relax:
        v = _relax_open(f, v, q, relax, bnd)
    for i, (c, n, rad) in enumerate(cuts):
        m = bnd & (which == i)
        v[m] -= (((v[m] - c) @ n)[:, None]) * n
    ob.data.vertices.foreach_set("co", v.astype(np.float32).ravel())
    ob.data.update()
    return ob


def _relax_open(f, v, quads, iters, bnd, lam=0.5):
    e = _sdf.edges_of_quads(quads)
    n = len(v)
    deg = np.bincount(e.ravel(), minlength=n).astype(np.float64)
    for _ in range(iters):
        s = np.zeros_like(v)
        np.add.at(s, e[:, 0], v[e[:, 1]])
        np.add.at(s, e[:, 1], v[e[:, 0]])
        mean = s / np.maximum(deg, 1)[:, None]
        g = _sdf.gradient(f, v)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)
        d = mean - v
        d -= np.einsum("ij,ij->i", d, g)[:, None] * g
        d[bnd] *= 0.0
        v = safe_project(f, v + lam * d, 2, 0.02)
    return v


def safe_project(f, v, iters, limit):
    """sdf.project, but a point that would move further than `limit` (a flat or clamped stretch of the field) keeps
    its start position."""
    w = _sdf.project(f, v, iters)
    bad = ~np.isfinite(w).all(axis=1) | (np.linalg.norm(w - v, axis=1) > limit)
    w[bad] = v[bad]
    return w


def boundary_vertices(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    out = np.zeros(len(bm.verts), dtype=bool)
    for e in bm.edges:
        if e.is_boundary:
            out[e.verts[0].index] = out[e.verts[1].index] = True
    bm.free()
    return out


def boundary_loops(ob):
    """Ordered vertex index loops of the open edges."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    nxt = {}
    for e in bm.edges:
        if e.is_boundary:
            a, b = e.verts[0].index, e.verts[1].index
            nxt.setdefault(a, []).append(b)
            nxt.setdefault(b, []).append(a)
    bm.free()
    seen, loops = set(), []
    for s in nxt:
        if s in seen:
            continue
        loop, prev, cur = [s], None, s
        seen.add(s)
        while True:
            cand = [x for x in nxt[cur] if x != prev and x not in seen]
            if not cand:
                break
            prev, cur = cur, cand[0]
            seen.add(cur)
            loop.append(cur)
        loops.append(loop)
    return loops


# ------------------------------------------------------------------------------------------------ simulation


def collider(src, name="Collider", ratio=0.25, inflate=0.0, col=None):
    """A decimated copy of `src` (evaluated) as a cloth collision object, optionally pushed out along normals."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
    me.transform(src.matrix_world)
    ob = bpy.data.objects.new(name, me)
    (col or bpy.context.scene.collection).objects.link(ob)
    if ratio < 1.0:
        md = ob.modifiers.new("dec", "DECIMATE")
        md.ratio = ratio
        _apply(ob, md)
    if inflate:
        me.update()
        n = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("normal", n)
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        me.vertices.foreach_set("co", (co + n * inflate).astype(np.float32))
        me.update()
    return ob


def _apply(ob, md):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.remove(md)
    ob.data = me
    bpy.data.meshes.remove(old)


def set_group(ob, name, weights):
    """Vertex group `name` from a (n,) array (0 weights are left out)."""
    g = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
    w = np.asarray(weights, dtype=np.float64)
    for i in np.nonzero(w > 1e-4)[0]:
        g.add([int(i)], float(min(w[i], 1.0)), "REPLACE")
    return g


def weld(ob, dist=2e-4):
    """Merge vertices closer than `dist` (coincident points give zero-length springs: the solver then returns the
    mesh unchanged). Instead of merging (which would renumber the vertices the caller's pins refer to), the
    second vertex of each such edge is moved toward its neighbours."""
    co = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    e = np.empty(len(ob.data.edges) * 2, dtype=np.int64)
    ob.data.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    co = co.reshape(-1, 3)
    short = np.linalg.norm(co[e[:, 0]] - co[e[:, 1]], axis=1) < dist
    if short.any():
        # nudge the second vertex of each short edge toward the mean of its neighbours (keeps every index)
        nb = np.zeros_like(co)
        cnt = np.zeros(len(co))
        np.add.at(nb, e[:, 0], co[e[:, 1]])
        np.add.at(nb, e[:, 1], co[e[:, 0]])
        np.add.at(cnt, e[:, 0], 1)
        np.add.at(cnt, e[:, 1], 1)
        mean = nb / np.maximum(cnt, 1)[:, None]
        for a, b in e[short]:
            co[b] = co[b] + 0.35 * (mean[b] - co[b])
        ob.data.vertices.foreach_set("co", co.astype(np.float32).ravel())
        ob.data.update()
        print("cloth.weld: %s: %d short edges nudged" % (ob.name, int(short.sum())))


def drape(ob, colliders, frames=50, pin=None, shrink=None, shrink_min=0.0, mass=0.25, tension=12.0,
          compression=12.0, shear=6.0, bending=0.6, quality=6, distance=0.004, thickness=0.004,
          friction=8.0, self_collision=False, gravity=(0, 0, -9.81), air=1.0, log=None, pressure=0.0,
          sewing=None, internal_springs=False):
    """Simulate `ob` as cloth for `frames` frames (25 fps) onto the colliders (objects; their pose is frozen) and
    write the final shape into the mesh. pin (n,) 0..1: goal weights (1 = held where it is). shrink (n,) 0..1
    scales `shrink_min` per vertex (negative shrink_min = the fabric grows: buckles into folds where it is held).
    Returns the per-frame largest vertex speed (m/frame) so the caller can see it settle."""
    s = bpy.context.scene
    weld(ob, 2e-4)
    for c in colliders:
        if not any(m.type == "COLLISION" for m in c.modifiers):
            c.modifiers.new("Collision", "COLLISION")
        c.collision.thickness_outer = thickness
        c.collision.thickness_inner = 0.02
        c.collision.cloth_friction = friction
        c.collision.damping = 0.5
    md = ob.modifiers.new("Cloth", "CLOTH")
    st = md.settings
    st.quality = quality
    st.mass = mass
    st.tension_stiffness = tension
    st.compression_stiffness = compression
    st.shear_stiffness = shear
    st.bending_stiffness = bending
    st.air_damping = air
    st.gravity = gravity
    st.time_scale = 1.0
    if pin is not None:
        set_group(ob, "_pin", pin)
        st.vertex_group_mass = "_pin"
        st.pin_stiffness = 1.0
    if shrink is not None:
        set_group(ob, "_shrink", shrink)
        st.vertex_group_shrink = "_shrink"
        st.shrink_min = shrink_min
    elif shrink_min:
        st.shrink_min = shrink_min
    if pressure:
        st.use_pressure = True
        st.uniform_pressure_force = pressure
    if internal_springs:
        st.use_internal_springs = True
    cs = md.collision_settings
    cs.use_collision = True
    cs.distance_min = distance
    cs.collision_quality = 3
    cs.impulse_clamp = 0.02
    cs.self_impulse_clamp = 0.02
    cs.use_self_collision = self_collision
    cs.self_distance_min = distance * 0.75
    md.point_cache.frame_start = 1
    md.point_cache.frame_end = frames
    s.frame_start, s.frame_end = 1, frames
    prev = None
    speeds = []
    dg = bpy.context.evaluated_depsgraph_get()
    for fr in range(1, frames + 1):
        s.frame_set(fr)
        ev = ob.evaluated_get(dg)
        n = len(ev.data.vertices)
        co = np.empty(n * 3)
        ev.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        if prev is not None:
            speeds.append(float(np.percentile(np.linalg.norm(co - prev, axis=1), 99)))
            if log and fr % 10 == 0:
                log("  cloth %s frame %d: p99 speed %.2f mm/frame" % (ob.name, fr, speeds[-1] * 1000))
        prev = co
    ob.modifiers.remove(md)
    ob.data.vertices.foreach_set("co", prev.astype(np.float32).ravel())
    ob.data.update()
    s.frame_set(1)
    for g in ("_pin", "_shrink"):
        if ob.vertex_groups.get(g):
            ob.vertex_groups.remove(ob.vertex_groups[g])
    return speeds


# ------------------------------------------------------------------------------------------------ finishing


def vertex_normals(ob):
    me = ob.data
    me.update()
    n = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("normal", n)
    return n.reshape(-1, 3)


def hem_facing(ob, depth=0.02, thickness=0.003, steps=2, loops=None):
    """Turn the open edges inward: from each boundary loop a rim `thickness` deep (against the surface normal)
    and a facing that runs back up inside the garment for `depth`, so hems, cuffs and openings show a real edge
    with thickness and an inner face. loops: vertex loops to treat (default every boundary loop).
    Returns the indices of the new faces (to tag them as the inside)."""
    me = ob.data
    n0 = len(me.vertices)
    co = np.empty(n0 * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    N = vertex_normals(ob)
    loops = loops if loops is not None else boundary_loops(ob)
    e = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    bnd = boundary_vertices(ob)
    D = np.zeros_like(co)
    ia = bnd[e[:, 0]] & ~bnd[e[:, 1]]
    ib = bnd[e[:, 1]] & ~bnd[e[:, 0]]
    np.add.at(D, e[ia, 0], co[e[ia, 1]] - co[e[ia, 0]])
    np.add.at(D, e[ib, 1], co[e[ib, 0]] - co[e[ib, 1]])
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    created = []
    for loop in loops:
        L = list(loop)
        m = len(L)
        if m < 3:
            continue
        bm.verts.ensure_lookup_table()
        # orientation: the existing face on edge (L0, L1) runs L0 -> L1 or L1 -> L0
        ed = bm.edges.get((bm.verts[L[0]], bm.verts[L[1]]))
        forward = True
        if ed is not None and ed.link_faces:
            fv = [v.index for v in ed.link_faces[0].verts]
            k = fv.index(L[0])
            forward = fv[(k + 1) % len(fv)] == L[1]
        closed = (bm.edges.get((bm.verts[L[0]], bm.verts[L[-1]])) is not None)
        P, Nn = co[L], N[L]
        Dd = D[L] - np.einsum("ij,ij->i", D[L], Nn)[:, None] * Nn
        Dd /= np.maximum(np.linalg.norm(Dd, axis=1, keepdims=True), 1e-9)
        rings = [[bm.verts[i] for i in L]]
        for j in range(1, steps + 2):
            R = P - Nn * thickness + (Dd * depth * (j - 1) / steps if j > 1 else 0)
            rings.append([bm.verts.new(Vector(p)) for p in R])
        for r0, r1 in zip(rings[:-1], rings[1:]):
            for i in range(m if closed else m - 1):
                k = (i + 1) % m
                quad = [r0[i], r0[k], r1[k], r1[i]] if not forward else [r0[k], r0[i], r1[i], r1[k]]
                try:
                    created.append(bm.faces.new(quad))
                except ValueError:
                    pass
    bm.faces.index_update()
    idx = [f.index for f in created]
    bm.to_mesh(me)
    bm.free()
    me.update()
    return idx


def ribbon(name, path, normals, width, thick, col=None, closed=False):
    """A flat strap (webbing, tape) of `width` x `thick` along `path` (n, 3), lying on the surface whose normals
    are `normals` (n, 3). Closed box section, quads."""
    P = np.asarray(path, dtype=np.float64)
    Nn = np.asarray(normals, dtype=np.float64)
    T = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    if not closed:
        T[0], T[-1] = P[1] - P[0], P[-1] - P[-2]
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    Nn = Nn - np.einsum("ij,ij->i", Nn, T)[:, None] * T
    Nn /= np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-9)
    S = np.cross(T, Nn)
    corners = [(-0.5, 0.0), (0.5, 0.0), (0.5, 1.0), (-0.5, 1.0)]
    V = []
    for a, b in corners:
        V.append(P + S * (a * width) + Nn * (b * thick))
    V = np.stack(V, axis=1).reshape(-1, 3)
    n = len(P)
    F = []
    for i in range(n if closed else n - 1):
        k = (i + 1) % n
        for c in range(4):
            c2 = (c + 1) % 4
            F.append((i * 4 + c, k * 4 + c, k * 4 + c2, i * 4 + c2))
    if not closed:
        F.append((3, 2, 1, 0))
        F.append(((n - 1) * 4 + 0, (n - 1) * 4 + 1, (n - 1) * 4 + 2, (n - 1) * 4 + 3))
    from . import geo as _geo
    ob = _geo.from_arrays(name, V, F, col, smooth=50)
    return ob


def smooth(ob, iters=4, pin=None, lam=0.5, mu=-0.53):
    """Taubin smoothing of the vertex positions (removes mesh-scale crinkles left by the solver, keeps folds and
    volume). pin (n,) bool: vertices that stay put (open edges are always kept)."""
    me = ob.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    e = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    keep = boundary_vertices(ob)
    if pin is not None:
        keep = keep | np.asarray(pin, dtype=bool)
    deg = np.bincount(e.ravel(), minlength=len(co)).astype(np.float64)
    for _ in range(iters):
        for f in (lam, mu):
            s = np.zeros_like(co)
            np.add.at(s, e[:, 0], co[e[:, 1]])
            np.add.at(s, e[:, 1], co[e[:, 0]])
            d = s / np.maximum(deg, 1)[:, None] - co
            d[keep] = 0
            co = co + f * d
    me.vertices.foreach_set("co", co.astype(np.float32).ravel())
    me.update()
