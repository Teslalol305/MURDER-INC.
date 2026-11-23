"""Clean trims for the Goons (rebuild pass r2): rib bands and hat bands as closed double-walled tubes (no cut edges
to tear), tidy open edges (no sawtooth from a plane cut through a surface net), holes cut on an ellipse with a
rolled hem, surface strips (tracksuit stripe tape laid on the cloth, constant width), the sling's buckle, and the
mesh clean-up before decimation (one subdivision + Taubin so folds shade smooth, degenerate triangles dissolved).
"""
import bmesh
import numpy as np
from mathutils import Matrix

from mi import cloth, geo, sdf
from assets._goons_cloth import unit, verts, set_verts


# ------------------------------------------------------------------------------------------------ mesh clean-up


def refine(ob, smooth_iters=4):
    """One Catmull-Clark level (no new folds, smoother ones: the drape's 10 mm facets become rounded) and a
    Taubin pass. Open edges stay where they are."""
    md = ob.modifiers.new("sub", "SUBSURF")
    md.levels = md.render_levels = 1
    md.boundary_smooth = "PRESERVE_CORNERS"
    md.use_limit_surface = True
    geo._apply_modifier(ob, md)
    if smooth_iters:
        cloth.smooth(ob, smooth_iters)
    return ob


def clean_degenerate(ob, dist=4e-5, min_area=2e-9):
    """Dissolve zero-length edges and zero-area faces (Unreal's Remove Degenerates would drop them anyway, and they
    give undefined normals and tangents)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n0 = len(bm.faces)
    bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges[:])
    bad = [f for f in bm.faces if f.calc_area() < min_area]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return n0 - len(ob.data.polygons)


def tidy_open_edges(ob, iters=12, ears=2, which=None):
    """Open edges of a surface-net mesh cut by a plane run in a staircase: drop the 'ear' faces (every corner on
    the edge), then smooth each open loop along itself (a planar loop stays in its plane)."""
    for _ in range(ears):
        bnd = cloth.boundary_vertices(ob)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        co = verts(ob)
        kill = []
        for f in bm.faces:
            ids = [v.index for v in f.verts]
            if bnd[ids].all() and (which is None or which(co[ids])):
                kill.append(f)
        if kill:
            bmesh.ops.delete(bm, geom=kill, context="FACES")
            loose = [v for v in bm.verts if not v.link_faces]
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
    co = verts(ob)
    for L in cloth.boundary_loops(ob):
        if len(L) < 6 or (which is not None and not which(co[L])):
            continue
        L = np.asarray(L)
        for _ in range(iters):
            P = co[L]
            co[L] = P + 0.5 * (0.5 * (np.roll(P, 1, axis=0) + np.roll(P, -1, axis=0)) - P)
    set_verts(ob, co)
    return ob


# ------------------------------------------------------------------------------------------------ tubes


def _frame(axis, ref=None):
    w = unit(axis)
    ref = np.array([0, -1.0, 0]) if ref is None else np.asarray(ref, dtype=np.float64)
    if abs(ref @ w) > 0.9:
        ref = np.array([1.0, 0, 0])
    u = unit(ref - w * (ref @ w))
    v = np.cross(w, u)
    return u, v, w


def radius_on(field, level, c, dirs, rmax=0.35, step=0.0015):
    """Per direction: the outermost radius where field(c + d r) crosses `level` going outward."""
    rs = np.arange(0.0, rmax, step)
    P = c[None, None, :] + dirs[:, None, :] * rs[None, :, None]
    f = field(P.reshape(-1, 3)).reshape(len(dirs), len(rs)) - level
    out = np.empty(len(dirs))
    for i in range(len(dirs)):
        inside = np.nonzero(f[i] <= 0)[0]
        k = inside.max() if len(inside) else 0
        k = min(k, len(rs) - 2)
        a, b = f[i, k], f[i, k + 1]
        t = 0.0 if b == a else np.clip(-a / (b - a), 0, 1)
        out[i] = rs[k] + t * step
    return out


def axis_band(name, field, level, c0, axis, s0, s1, thick, col, nu=96, ns=9, ref=None, lip=4, smooth=3,
              ease_top=0.0):
    """A rib band (cuff, waistband, hat band) as ONE closed double-walled tube: its outer wall on field = level
    between the stations s0..s1 along `axis` from c0, the inner wall `thick` inside, joined by rounded lips at both
    ends. All quads, no open edge, so nothing tears or spikes at the hems. ease_top: extra radius at s1 (a cuff
    flares a little where the sleeve goes in)."""
    u, v, w = _frame(axis, ref)
    c0 = np.asarray(c0, dtype=np.float64)
    th = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    dirs = np.cos(th)[:, None] * u + np.sin(th)[:, None] * v
    S = np.linspace(s0, s1, ns)
    R = np.stack([radius_on(field, level, c0 + w * s, dirs) for s in S], axis=0)        # (ns, nu)
    for _ in range(smooth):                                                              # round the knit's line
        R = 0.5 * R + 0.25 * (np.roll(R, 1, axis=1) + np.roll(R, -1, axis=1))
        R[1:-1] = 0.5 * R[1:-1] + 0.25 * (R[:-2] + R[2:])
    R += ease_top * ((S - s0) / max(s1 - s0, 1e-6))[:, None] ** 2
    rows = []
    for k in range(ns):                                                                  # inner wall, s0 -> s1
        rows.append((S[k], R[k] - thick))
    rs = []
    for k, sk in ((ns - 1, s1), (0, s0)):
        rs.append([(sk + (1 if sk == s1 else -1) * 0.5 * thick * np.sin(np.pi * t),
                    R[k] - 0.5 * thick + 0.5 * thick * -np.cos(np.pi * t)) for t in np.linspace(0, 1, lip + 2)[1:-1]])
    rows += rs[0]
    for k in range(ns - 1, -1, -1):                                                      # outer wall, s1 -> s0
        rows.append((S[k], R[k]))
    rows += rs[1]
    V = []
    for s, r in rows:
        V.append(c0 + w * s + dirs * np.asarray(r)[:, None])
    V = np.concatenate(V, axis=0)
    nr = len(rows)
    F = []
    for a in range(nr):
        b = (a + 1) % nr
        for i in range(nu):
            j = (i + 1) % nu
            F.append((a * nu + i, a * nu + j, b * nu + j, b * nu + i))
    ob = geo.from_arrays(name, V, F, col, smooth=None)
    for p in ob.data.polygons:
        p.use_smooth = True
    # outward normals: the outer wall must face away from the axis
    me = ob.data
    me.update()
    k = (ns + lip + ns // 2) * nu
    pn = np.array(me.polygons[min(k, len(me.polygons) - 1)].normal)
    pc = np.array(me.polygons[min(k, len(me.polygons) - 1)].center)
    radial = pc - c0 - w * ((pc - c0) @ w)
    if pn @ radial < 0:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
        me.update()
    return ob


# ------------------------------------------------------------------------------------------------ holes


def cut_ellipse_hole(ob, field, c, u, v, a, b, depth=0.03, hem_r=0.0021, col=None, name="Hem"):
    """Cut an elliptic opening (semi-axes a along u, b along v, centred at c) through the faces of `ob` within
    `depth` of c along u x v, put its open edge exactly on the ellipse (projected back onto field = 0), relax the
    ring next to it, and return a rolled hem (a closed tube of radius hem_r just inside the edge)."""
    u, v = unit(u), unit(v)
    w = unit(np.cross(u, v))
    co = verts(ob)
    d = co - c
    du, dv, dw = d @ u, d @ v, d @ w
    r = np.sqrt((du / a) ** 2 + (dv / b) ** 2)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    kill = [f for f in bm.faces if np.mean([r[x.index] for x in f.verts]) < 1.0
            and abs(np.mean([dw[x.index] for x in f.verts])) < depth]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    loose = [x for x in bm.verts if not x.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    co = verts(ob)
    d = co - c
    du, dv, dw = d @ u, d @ v, d @ w
    r = np.sqrt((du / a) ** 2 + (dv / b) ** 2)
    loops = [L for L in cloth.boundary_loops(ob) if r[L].mean() < 1.6 and np.abs(dw[L]).mean() < depth]
    if not loops:
        raise RuntimeError("%s: no hole edge found" % name)
    L = np.asarray(max(loops, key=len))
    # onto the ellipse in the (u, v) plane, then back onto the surface
    ang = np.arctan2(dv[L] / b, du[L] / a)
    order = np.argsort(np.unwrap(ang))
    P = c + np.outer(a * np.cos(ang), u) + np.outer(b * np.sin(ang), v) + np.outer(dw[L], w)
    P = cloth.safe_project(field, P, 4, 0.01)
    co[L] = P
    # relax the next two rings (no squashed triangles at the edge)
    idx_near = np.nonzero((r < 1.5) & (np.abs(dw) < depth))[0]
    keep = np.zeros(len(co), dtype=bool)
    keep[L] = True
    from mi import char as _char
    adj, ptr = _char.adjacency(ob)
    for _ in range(6):
        mean = np.add.reduceat(co[adj], ptr[:-1], axis=0) / np.maximum(np.diff(ptr), 1)[:, None]
        mv = idx_near[~keep[idx_near]]
        co[mv] += 0.5 * (mean[mv] - co[mv])
        co[mv] = cloth.safe_project(field, co[mv], 2, 0.01)
    set_verts(ob, co)
    # the rolled hem: the edge, ordered round the ellipse, pulled in by the fabric thickness
    Q = P[order]
    nrm = cloth.vertex_normals(ob)[L][order]
    Q = Q - nrm * hem_r * 0.7
    for _ in range(3):
        Q = 0.5 * Q + 0.25 * (np.roll(Q, 1, axis=0) + np.roll(Q, -1, axis=0))
    Q = np.vstack([Q, Q[:1]])
    hem = geo.pipe([tuple(x) for x in Q], radius=hem_r, segments=8, cap=False, name=name)
    if col is not None:
        from mi import scene as _scene
        _scene.move_to(hem, col)
    return hem


# ------------------------------------------------------------------------------------------------ strips, hardware


def surface_strip(S, path, out, width, col, name="Stripe", step=0.008, across=5, lift=0.0018, thick=0.0006,
                  reach=0.35, smooth=2):
    """A tape laid on the outermost cloth (Surface S) along the polyline `path` (joint to joint), on the side `out`
    points to: at stations along the path rays are cast inward from outside, across the tape's width and square to
    the path, so the tape keeps its width and follows the cloth over every fold (a texture stripe in body space
    broke into patches on a baggy sleeve). Stations whose rays do not all land within reach are left out."""
    path = [np.asarray(p, dtype=np.float64) for p in path]
    seg = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
    out0 = np.asarray(out, dtype=np.float64)
    st = []
    for a, b in seg:
        L = np.linalg.norm(b - a)
        for t in np.arange(0.0, L, step):
            st.append((a, b, t))
    st.append((seg[-1][0], seg[-1][1], np.linalg.norm(seg[-1][1] - seg[-1][0])))
    ks = np.linspace(-0.5, 0.5, across) * width
    rows, nrows = [], []
    for a, b, t in st:
        wv = unit(b - a)
        o = unit(out0 - wv * (out0 @ wv))
        side = np.cross(wv, o)
        c = a + wv * t
        R, Nr = [], []
        for k in ks:
            loc, n = S.ray(c + side * k + o * reach, -o, reach * 1.5)
            if loc is None or np.linalg.norm(loc - c) > reach * 0.6:
                break
            if n @ o < 0:
                n = -n
            R.append(loc)
            Nr.append(n)
        if len(R) == across:
            rows.append(R)
            nrows.append(Nr)
    G, Nn = np.array(rows), np.array(nrows)
    for _ in range(smooth):
        G[1:-1] = 0.5 * G[1:-1] + 0.25 * (G[:-2] + G[2:])
    for _ in range(3):                                          # clearance over the cloth after the smoothing
        flat = G.reshape(-1, 3)
        hit, hn = S.nearest(flat)
        d = ((flat - hit) * Nn.reshape(-1, 3)).sum(axis=1)
        flat += Nn.reshape(-1, 3) * np.maximum(0.0, lift - d)[:, None]
        G = flat.reshape(G.shape)
    V, F = [], []
    n_t = len(G)
    for i in range(n_t):
        for j in range(across):
            V.append(G[i, j])
    for i in range(n_t):
        for j in range(across):
            V.append(G[i, j] + Nn[i, j] * thick)
    off = n_t * across
    for i in range(n_t - 1):
        for j in range(across - 1):
            q = (i * across + j, (i + 1) * across + j, (i + 1) * across + j + 1, i * across + j + 1)
            F.append(q[::-1])
            F.append(tuple(x + off for x in q))
    for i in range(n_t - 1):                                    # the two long edges
        for j in (0, across - 1):
            q = (i * across + j, (i + 1) * across + j, (i + 1) * across + j + off, i * across + j + off)
            F.append(q if j == 0 else q[::-1])
    for i in (0, n_t - 1):                                      # the ends
        for j in range(across - 1):
            q = (i * across + j, i * across + j + 1, i * across + j + 1 + off, i * across + j + off)
            F.append(q if i == 0 else q[::-1])
    ob = geo.from_arrays(name, np.array(V), F, col, smooth=None)
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.data.update()
    return ob


def buckle(name, p, t, n, col, width=0.046, height=0.034, bar=0.0042, thick=0.0035):
    """A tri-glide sling buckle (stamped steel, black): a rounded rectangular frame with a centre bar, lying on
    the strap at p (t along the strap, n out of the body)."""
    t, n = unit(t), unit(n)
    s = unit(np.cross(t, n))
    w2, h2 = width / 2, height / 2
    outline = [(-w2, -h2), (w2, -h2), (w2, h2), (-w2, h2)]
    parts = []
    for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]):
        c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
        L = abs(x1 - x0) + abs(y1 - y0) + bar
        horiz = abs(x1 - x0) > 0
        bx = geo.box(size=(L if horiz else bar, bar if horiz else L, thick), bevel=0.0011, segments=2, name="BuckleBar",
                     base=False)
        bx.data.transform(Matrix.Translation((c[0], c[1], 0)))
        parts.append(bx)
    mid = geo.box(size=(bar * 0.9, height, thick * 1.15), bevel=0.0011, segments=2, name="BuckleMid", base=False)
    parts.append(mid)
    ob = geo.join(parts, name, col)
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = s, t, n, np.asarray(p) + n * (thick * 0.5 + 0.0015)
    # the frame's long side runs across the strap
    ob.data.transform(Matrix(M.tolist()))
    ob.data.update()
    return ob
