"""Signed distance modelling for organic forms (characters): numpy primitives and blends, surface nets meshing on a
(rotatable) grid, projection of the vertices onto the exact zero level, tangential relaxation, Blender mesh.

    from mi import sdf
    f = lambda p: sdf.smin(sdf.round_cone(p, a, b, 0.03, 0.02), sdf.sphere(p, c, 0.025), 0.01)
    v, q = sdf.surface_nets(f, lo, hi, 0.002)          # quads, outward winding
    v = sdf.project(f, v)                              # onto f = 0
    v = sdf.relax(f, v, q, 4)                          # even quads, still on the surface
    ob = sdf.to_mesh("Name", v, q, col)

Every primitive takes p as an (N, 3) array and returns (N,) distances (metres, negative inside). They are exact or
close to exact (ellipsoids and blends are bounds); surface nets only need the sign and a sane gradient near zero.
"""
import bpy
import numpy as np

# ------------------------------------------------------------------------------------------------ primitives


def _v(a):
    return np.asarray(a, dtype=np.float64)


def sphere(p, c, r):
    return np.linalg.norm(p - _v(c), axis=1) - r


def round_cone(p, a, b, ra, rb):
    """Capsule from a (radius ra) to b (radius rb), exact (Inigo Quilez's round cone)."""
    a, b = _v(a), _v(b)
    ba = b - a
    l2 = float(ba @ ba)
    rr = ra - rb
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = p - a
    y = pa @ ba
    z = y - l2
    w = pa * l2 - np.outer(y, ba)
    x2 = np.einsum("ij,ij->i", w, w)
    y2 = y * y * l2
    z2 = z * z * l2
    k = np.sign(rr) * rr * rr * x2
    d3 = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - ra
    d1 = np.sqrt(x2 + z2) * il2 - rb
    d2 = np.sqrt(x2 + y2) * il2 - ra
    return np.where(np.sign(z) * a2 * z2 > k, d1, np.where(np.sign(y) * a2 * y2 < k, d2, d3))


def capsule(p, a, b, r):
    return round_cone(p, a, b, r, r)


def local(p, c, frame):
    """Points in a local frame: frame rows are the local X, Y, Z axes (orthonormal) in world space."""
    return (p - _v(c)) @ _v(frame).T


def ellipsoid(p, c, frame, radii):
    """Ellipsoid (bound, Quilez) with semi-axes `radii` along the rows of `frame`."""
    q = local(p, c, frame)
    r = _v(radii)
    k0 = np.linalg.norm(q / r, axis=1)
    k1 = np.linalg.norm(q / (r * r), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-12)


def round_box(p, c, frame, half, r):
    q = np.abs(local(p, c, frame)) - _v(half) + r
    return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(axis=1), 0) - r


def torus(p, c, frame, R, r):
    """Torus around the local Z axis of `frame`."""
    q = local(p, c, frame)
    a = np.linalg.norm(q[:, :2], axis=1) - R
    return np.sqrt(a * a + q[:, 2] ** 2) - r


def rect2(x, y, hx, hy, r):
    """2D rounded rectangle distance (for footprints)."""
    qx = np.abs(x) - hx + r
    qy = np.abs(y) - hy + r
    return np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - r


# ------------------------------------------------------------------------------------------------ blends


def smin(a, b, k):
    """Polynomial smooth minimum (blend radius k, metres). k <= 0: hard minimum."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def union(*ds, k=0.0):
    out = ds[0]
    for d in ds[1:]:
        out = smin(out, d, k)
    return out


def shell(d, inner, outer):
    """The layer between d = inner and d = outer (e.g. a glove skin: shell(hand, 0, 0.0015))."""
    return np.maximum(d - outer, inner - d)


# ------------------------------------------------------------------------------------------------ meshing


def surface_nets(f, lo, hi, h, frame=None, origin=(0, 0, 0), chunk=2_000_000):
    """Naive surface nets of f over the box lo..hi (local coordinates of `frame` at `origin`; default world).
    Returns (vertices (M, 3) world, quads (Q, 4)) with outward winding (normals toward f > 0)."""
    lo, hi = _v(lo), _v(hi)
    R = np.eye(3) if frame is None else _v(frame)
    O = _v(origin)
    n = np.maximum(np.ceil((hi - lo) / h).astype(int) + 1, 2)
    nx, ny, nz = (int(v) for v in n)
    ii, jj, kk = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
    idx = np.stack([ii.ravel(), jj.ravel(), kk.ravel()], axis=1).astype(np.float64)
    F = np.empty(len(idx))
    for s in range(0, len(idx), chunk):
        loc = lo + idx[s:s + chunk] * h
        F[s:s + chunk] = f(O + loc @ R)
    F = F.reshape(nx, ny, nz)
    F[F == 0] = 1e-12
    S = F < 0
    cnt = np.zeros((nx - 1, ny - 1, nz - 1), dtype=np.int32)
    acc = np.zeros((nx - 1, ny - 1, nz - 1, 3))

    def t_of(a, b):
        return a / (a - b)
    # x edges: (i,j,k)-(i+1,j,k), shape (nx-1, ny, nz)
    ex = S[:-1] != S[1:]
    tx = np.where(ex, t_of(F[:-1], F[1:]), 0.0)
    for dj in (0, 1):
        for dk in (0, 1):
            e = ex[:, dj:ny - 1 + dj, dk:nz - 1 + dk]
            cnt += e
            acc[..., 0] += np.where(e, tx[:, dj:ny - 1 + dj, dk:nz - 1 + dk], 0)
            acc[..., 1] += e * dj
            acc[..., 2] += e * dk
    ey = S[:, :-1] != S[:, 1:]
    ty = np.where(ey, t_of(F[:, :-1], F[:, 1:]), 0.0)
    for di in (0, 1):
        for dk in (0, 1):
            e = ey[di:nx - 1 + di, :, dk:nz - 1 + dk]
            cnt += e
            acc[..., 0] += e * di
            acc[..., 1] += np.where(e, ty[di:nx - 1 + di, :, dk:nz - 1 + dk], 0)
            acc[..., 2] += e * dk
    ez = S[:, :, :-1] != S[:, :, 1:]
    tz = np.where(ez, t_of(F[:, :, :-1], F[:, :, 1:]), 0.0)
    for di in (0, 1):
        for dj in (0, 1):
            e = ez[di:nx - 1 + di, dj:ny - 1 + dj, :]
            cnt += e
            acc[..., 0] += e * di
            acc[..., 1] += e * dj
            acc[..., 2] += np.where(e, tz[di:nx - 1 + di, dj:ny - 1 + dj, :], 0)
    active = cnt > 0
    vid = -np.ones(cnt.shape, dtype=np.int64)
    vid[active] = np.arange(int(active.sum()))
    ci = np.argwhere(active)
    loc = lo + (ci + acc[active] / cnt[active][:, None]) * h
    verts = O + loc @ R
    quads = []
    # x edges: cells (i, j-1..j, k-1..k)
    i, j, k = np.nonzero(ex[:, 1:-1, 1:-1])
    j, k = j + 1, k + 1
    q = np.stack([vid[i, j - 1, k - 1], vid[i, j, k - 1], vid[i, j, k], vid[i, j - 1, k]], axis=1)
    flip = ~S[i, j, k]
    q[flip] = q[flip][:, ::-1]
    quads.append(q)
    i, j, k = np.nonzero(ey[1:-1, :, 1:-1])
    i, k = i + 1, k + 1
    q = np.stack([vid[i - 1, j, k - 1], vid[i - 1, j, k], vid[i, j, k], vid[i, j, k - 1]], axis=1)
    flip = ~S[i, j, k]
    q[flip] = q[flip][:, ::-1]
    quads.append(q)
    i, j, k = np.nonzero(ez[1:-1, 1:-1, :])
    i, j = i + 1, j + 1
    q = np.stack([vid[i - 1, j - 1, k], vid[i, j - 1, k], vid[i, j, k], vid[i - 1, j, k]], axis=1)
    flip = ~S[i, j, k]
    q[flip] = q[flip][:, ::-1]
    quads.append(q)
    quads = np.concatenate(quads)
    if np.linalg.det(R) < 0:
        quads = quads[:, ::-1]
    return verts, quads


def gradient(f, p, e=2e-4):
    g = np.empty_like(p)
    for a in range(3):
        d = np.zeros(3)
        d[a] = e
        g[:, a] = (f(p + d) - f(p - d)) / (2 * e)
    return g


def project(f, v, iters=3, e=2e-4, max_step=None):
    """Newton steps onto f = 0 along the gradient."""
    v = v.copy()
    for _ in range(iters):
        d = f(v)
        g = gradient(f, v, e)
        gg = np.maximum(np.einsum("ij,ij->i", g, g), 1e-12)
        step = (d / gg)[:, None] * g
        if max_step:
            ln = np.linalg.norm(step, axis=1, keepdims=True)
            step *= np.minimum(1.0, max_step / np.maximum(ln, 1e-12))
        v -= step
    return v


def edges_of_quads(quads):
    e = np.concatenate([quads[:, [0, 1]], quads[:, [1, 2]], quads[:, [2, 3]], quads[:, [3, 0]]])
    e = np.sort(e, axis=1)
    return np.unique(e, axis=0)


def relax(f, v, quads, iters=4, lam=0.5, pin=None):
    """Tangential Laplacian smoothing, each pass re-projected onto f = 0 (keeps the shape, evens the quads).
    pin: boolean (M,) of vertices that must not move."""
    e = edges_of_quads(quads)
    n = len(v)
    deg = np.bincount(e.ravel(), minlength=n).astype(np.float64)
    for _ in range(iters):
        s = np.zeros_like(v)
        np.add.at(s, e[:, 0], v[e[:, 1]])
        np.add.at(s, e[:, 1], v[e[:, 0]])
        mean = s / np.maximum(deg, 1)[:, None]
        g = gradient(f, v)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)
        d = mean - v
        d -= np.einsum("ij,ij->i", d, g)[:, None] * g          # tangential part only
        step = lam * d
        if pin is not None:
            step[pin] = 0
        v = v + step
        v2 = project(f, v, 2)
        if pin is not None:
            v2[pin] = v[pin]
        v = v2
    return v


def keep_largest(v, quads):
    """Drop small disconnected pieces (stray bubbles of the grid)."""
    n = len(v)
    parent = np.arange(n)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in edges_of_quads(quads):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    roots = np.array([find(i) for i in range(n)])
    big = np.bincount(roots).argmax()
    keep = roots == big
    remap = -np.ones(n, dtype=np.int64)
    remap[keep] = np.arange(int(keep.sum()))
    q = quads[keep[quads].all(axis=1)]
    return v[keep], remap[q]


def to_mesh(name, v, quads, col=None):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set("co", np.asarray(v, dtype=np.float32).ravel())
    nq = len(quads)
    me.loops.add(nq * 4)
    me.loops.foreach_set("vertex_index", np.asarray(quads, dtype=np.int32).ravel())
    me.polygons.add(nq)
    me.polygons.foreach_set("loop_start", np.arange(0, nq * 4, 4, dtype=np.int32))
    me.update(calc_edges=True)
    me.validate(clean_customdata=False)
    ob = bpy.data.objects.new(name, me)
    (col or bpy.context.scene.collection).objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob
