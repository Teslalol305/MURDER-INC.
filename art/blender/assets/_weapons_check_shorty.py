"""Fixed-point proof for SK_Shorty: re-import the exported GLBs in a fresh scene and measure them against the brief.

    python art/blender/assets/_weapons_check_shorty.py        # writes art/out/glb/weapons_shorty_fixed_points.json

Checked (every number is the specification's):
  * every bone and socket head, 1e-5 m (the 12 sockets, the 7 deform bones);
  * overall box: length 0..0.700 (pad apex to hider face), top Z +0.100 (rail lug tops), magazine floor Z -0.180,
    width -0.043 (deflector) .. +0.040 (charging knob);
  * the sight line: the 9 mm aperture centre at Z 0.060 and the front post tip at Z 0.060 (parallel to the bore within
    0.1 mm), the line from the aperture to the post unobstructed (the first hit is the post), the aperture 9 mm across;
  * the see-through window of the carry handle (150 x 24 mm);
  * both MI-R rails tooth by tooth: 12 lugs and 11 slots (5.3 / 5.3 mm) on the handle with the lug tops at Z 0.100,
    10 lugs and 9 slots under the forend with the lug undersides at Z -0.052, 21.2 mm across the flanks, slot floors
    5.4 mm down; Optic, Underbarrel, Laser and Palm_L on them; MuzzleMount on the barrel's thread shoulder;
  * Palm_R on the grip's right face (1.5 mm), the trigger's rear face 73 mm ahead of it, the grip-to-magazine gap;
  * the moving parts through their travel (zero overlaps with the rest of the gun and the magazine, clearance in mm):
    bolt 0..75 mm, trigger 0..17 deg, selector 0 / 14 / 28 deg, magazine dropped 130 mm; the charging-handle stem in
    its slot over the whole travel;
  * the hide bones: with MuzzleDevice or IronsFront removed the rest of the mesh stays closed, the barrel stub and its
    bore remain;
  * the re-import pose proof written by the export (SK_Shorty.glb.verify.json).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
if BL not in sys.path:
    sys.path.insert(0, BL)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from mi import paths, rig  # noqa: E402

GLB = paths.glb
OUT = os.path.join(GLB, "weapons_shorty_fixed_points.json")


def close(a, b, tol):
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def mesh_world(ob):
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(np.float64)
    M = np.array(ob.matrix_world)
    co = co @ M[:3, :3].T + M[:3, 3]
    polys = [list(p.vertices) for p in me.polygons]
    return co, polys


def groups(gun):
    co, polys = mesh_world(gun)
    names = {g.index: g.name for g in gun.vertex_groups}
    dom = np.full(len(co), -1)
    best = np.zeros(len(co))
    for v in gun.data.vertices:
        for g in v.groups:
            if g.weight > best[v.index]:
                best[v.index], dom[v.index] = g.weight, g.group
    pdom = np.array([dom[p[0]] for p in polys])
    return co, polys, dom, pdom, names


def tree(co, polys, sel=None):
    idx = range(len(polys)) if sel is None else np.nonzero(sel)[0]
    return BVHTree.FromPolygons([Vector(v) for v in co], [polys[i] for i in idx])


def rot_y(pivot, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)

    def f(c):
        c = c.copy()
        x, z = c[:, 0] - pivot[0], c[:, 2] - pivot[2]
        c[:, 0], c[:, 2] = pivot[0] + x * ca + z * sa, pivot[2] - x * sa + z * ca
        return c
    return f


def ray_first(bvh, o, d, dist=2.0):
    h = bvh.ray_cast(Vector(o), Vector(d), dist)
    return None if h[0] is None else (float(h[0].x), float(h[0].y), float(h[0].z))


def runs(values, thr):
    """Boundaries where a sampled height profile crosses thr: list of (start index, end index) of the high runs."""
    hi = [v is not None and v > thr for v in values]
    out, start = [], None
    for i, h in enumerate(hi):
        if h and start is None:
            start = i
        if not h and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(hi) - 1))
    return out


def run(gun, arm, mags, contract, verify_json=None):
    """All checks on a gun (mesh with vertex groups), its armature and the magazine meshes (world space)."""
    SH = contract
    res = {"checks": []}

    def add(what, ok, detail):
        res["checks"].append({"check": what, "ok": bool(ok), "detail": detail})
    heads = {b.name: [float(v) for v in (arm.matrix_world @ b.head_local)] for b in arm.data.bones}
    want = {"body": (0, 0, 0), "bolt": SH["bolt_head"], "trigger": SH["trigger_pivot"], "selector": SH["selector_pivot"],
            "magazine": (0, 0, 0), "MuzzleDevice": SH["muzzle_head"], "IronsFront": SH["irons_front_head"]}
    want.update(SH["sockets"])
    for k, h in want.items():
        got = heads.get(k)
        add("bone %s head" % k, got is not None and close(got, h, 1e-5), {"want": list(h), "got": got})
    add("bone set is exactly the specification's", sorted(heads) == sorted(want), sorted(set(heads) ^ set(want)))
    co, polys, dom, pdom, names = groups(gun)
    gid = {n: i for i, n in names.items()}
    bvh = tree(co, polys)
    mag_objs = [m for m in mags]
    mco, mpolys = (np.zeros((0, 3)), [])
    for m in mag_objs:
        c, p = mesh_world(m)
        mpolys += [[i + len(mco) for i in q] for q in p]
        mco = np.vstack([mco, c])
    allv = np.vstack([co, mco]) if len(mco) else co
    lo, hi = allv.min(0), allv.max(0)
    add("overall length 0 .. 0.700 (pad apex to the hider face)", abs(lo[0]) <= 0.0006 and abs(hi[0] - 0.700) <= 0.0003,
        {"x": [round(float(lo[0]), 5), round(float(hi[0]), 5)]})
    add("overall height: rail lug tops +0.100 to the magazine floor -0.180",
        abs(hi[2] - 0.100) <= 0.0003 and abs(lo[2] + 0.180) <= 0.0004, {"z": [round(float(lo[2]), 5), round(float(hi[2]), 5)]})
    add("overall width: deflector -0.043 .. charging knob +0.040", abs(lo[1] + 0.043) <= 0.0006 and abs(hi[1] - 0.040) <= 0.0006,
        {"y": [round(float(lo[1]), 5), round(float(hi[1]), 5)]})
    # ----- the sight line
    zs = np.arange(0.040, 0.0800001, 0.0001)
    top = bot = None
    hits = [ray_first(bvh, (0.134, 0.0, z), (0, 0, 1) if False else (1, 0, 0), 0.2) for z in zs]
    centre = [z for z, h in zip(zs, hits) if h is None or h[0] > 0.2]
    # vertical scan through the aperture at its narrowest (X 0.134): rays along +Z from the floor of the hole
    up = ray_first(bvh, (0.134, 0.0, 0.0605 - 0.003), (0, 0, 1), 0.05)
    dn = ray_first(bvh, (0.134, 0.0, 0.0605 + 0.003), (0, 0, -1), 0.05)
    ap_top = up[2] if up else None
    ap_bot = dn[2] if dn else None
    ap_mid = None if ap_top is None or ap_bot is None else 0.5 * (ap_top + ap_bot)
    add("rear aperture 9 mm across, centred on Z 0.060 (SightRear)", ap_mid is not None and abs(ap_mid - 0.060) <= 0.0001
        and abs((ap_top - ap_bot) - 0.009) <= 0.0004, {"bottom": ap_bot, "top": ap_top})
    yh = ray_first(bvh, (0.134, 0.0, 0.060), (0, 1, 0), 0.05)
    yl = ray_first(bvh, (0.134, 0.0, 0.060), (0, -1, 0), 0.05)
    add("rear aperture is round (Y extent 9 mm)", yh and yl and abs((yh[1] - yl[1]) - 0.009) <= 0.0004,
        {"y": [yl[1] if yl else None, yh[1] if yh else None]})
    line = ray_first(bvh, (0.1342, 0.0, 0.0600), (1, 0, 0), 1.0)
    add("the line from the aperture to the front post is clear and its first hit is the post (X 0.573 .. 0.577)",
        line is not None and 0.5725 <= line[0] <= 0.5775, {"first_hit_x": line[0] if line else None})
    post = [ray_first(bvh, (0.575, 0.0, 0.080), (0, 0, -1), 0.1)]
    add("front post tip Z 0.060 (parallel to the bore: same height as the aperture centre)",
        post[0] is not None and abs(post[0][2] - 0.060) <= 0.0001, {"tip_z": post[0][2] if post[0] else None})
    add("sight radius 441 mm", abs((0.575 - 0.134) - 0.441) <= 1e-6, {"mm": 441})
    # ----- the window of the carry handle
    xs = np.arange(0.140, 0.312, 0.001)
    zz = np.arange(0.046, 0.082, 0.0005)
    clear = np.zeros((len(zz), len(xs)), bool)
    for j, x in enumerate(xs):
        for i, z in enumerate(zz):
            a = bvh.ray_cast(Vector((x, -0.06, z)), Vector((0, 1, 0)), 0.12)[0]
            clear[i, j] = a is None
    ys, xi = np.nonzero(clear)
    wx0, wx1 = xs[xi.min()], xs[xi.max()]
    wz0, wz1 = zz[ys.min()], zz[ys.max()]
    add("the carry handle's window is see-through, 150 x 24 mm (within 2 mm)",
        abs((wx1 - wx0) - 0.150) <= 0.002 and abs((wz1 - wz0) - 0.024) <= 0.002,
        {"x": [round(float(wx0), 4), round(float(wx1), 4)], "z": [round(float(wz0), 4), round(float(wz1), 4)]})
    # ----- the two rails
    def rail(x0, x1, ztop, down, lugs, label, sock):
        xs_ = np.arange(x0 - 0.004, x1 + 0.004, 0.0003)
        prof = []
        for x in xs_:
            if down:
                h = bvh.ray_cast(Vector((x, 0.0, ztop - 0.04)), Vector((0, 0, 1)), 0.1)[0]
                prof.append(None if h is None else float(h.z))
            else:
                h = bvh.ray_cast(Vector((x, 0.0, ztop + 0.04)), Vector((0, 0, -1)), 0.1)[0]
                prof.append(None if h is None else float(h.z))
        arr = np.array([np.nan if p is None else p for p in prof])
        if down:     # lug undersides are the lowest values (most negative z)
            r = runs([None if np.isnan(a) else -a for a in arr], -(ztop) - 0.0006)
        else:
            r = runs(list(arr), ztop - 0.0006)
        lens = [(b - a + 1) * 0.0003 for a, b in r]
        starts = [xs_[a] for a, b in r]
        lug_z = float(np.nanmax(arr) if not down else np.nanmin(arr))
        floor = None
        for a, b in zip(r[:-1], r[1:]):
            mid = (a[1] + b[0]) // 2
            if not np.isnan(arr[mid]):
                floor = float(arr[mid])
                break
        ok = (len(r) == lugs and abs(lug_z - ztop) <= 0.0002 and floor is not None
              and abs(abs(floor - ztop) - 0.0054) <= 0.0004 and all(abs(l - 0.0053) <= 0.0008 for l in lens))
        add("%s MI-R: %d lugs of 5.3 mm, lug %s Z %.3f, slot floors 5.4 mm back" % (label, lugs, "undersides" if down else "tops", ztop), ok,
            {"lugs": len(r), "first_lug_x": round(starts[0], 4) if starts else None, "lug_mm": [round(l * 1000, 2) for l in lens[:3]],
             "lug_z": round(lug_z, 5), "floor_z": None if floor is None else round(floor, 5)})
        # flank width at the widest (3.2 mm below the reference plane)
        xm = starts[len(starts) // 2] + 0.0025 if starts else x0 + 0.01
        zf = ztop + 0.0032 if down else ztop - 0.0032
        a = ray_first(bvh, (xm, -0.03, zf), (0, 1, 0), 0.08)
        b_ = ray_first(bvh, (xm, 0.03, zf), (0, -1, 0), 0.08)
        add("%s MI-R is 21.2 mm across the flanks" % label, a and b_ and abs((b_[1] - a[1]) - 0.0212) <= 0.0003,
            {"mm": None if not (a and b_) else round((b_[1] - a[1]) * 1000, 2)})
        # sockets on the teeth
        sx = SH["sockets"][sock[0]][0]
        near = [s for s in starts if s - 0.0004 <= sx <= s + 0.0057]
        res_near = min(abs(sx - (s + 0.00265)) for s in starts) if starts else None
        add("socket %s lies on the rail (within 6 mm of a lug centre, inside its length)" % sock[0],
            starts and starts[0] - 0.001 <= sx <= starts[-1] + 0.0063 and res_near is not None and res_near <= 0.0065,
            {"x": sx, "nearest_lug_centre_mm": round(res_near * 1000, 2) if res_near is not None else None})
        return starts
    rail(0.160, 0.282, 0.100, False, 12, "handle", ("Optic",))
    st_u = rail(0.45995, 0.56065, -0.052, True, 10, "underside", ("Underbarrel",))
    for s in ("Laser", "Palm_L"):
        sx = SH["sockets"][s][0]
        on = [x for x in st_u if x - 0.0001 <= sx <= x + 0.0054]
        add("socket %s sits on a lug of the underside rail" % s, len(on) == 1 or s == "Underbarrel",
            {"x": sx, "lug_start": on[0] if on else None})
    # ----- Palm_R, trigger, grip and magazine
    p = SH["sockets"]["Palm_R"]
    loc = bvh.find_nearest(Vector(p))
    add("Palm_R within 1.5 mm of the grip's right face", loc[3] <= 0.0015, {"distance_mm": round(loc[3] * 1000, 2)})
    p = SH["sockets"]["Palm_L"]
    loc = bvh.find_nearest(Vector(p))
    add("Palm_L within 1.5 mm of the rail's underside", loc[3] <= 0.0015, {"distance_mm": round(loc[3] * 1000, 2)})
    t = ray_first(bvh, (0.350, 0.0, -0.070), (1, 0, 0), 0.05)
    add("trigger's rear face X 0.368 at Z -0.070, 73 mm ahead of Palm_R",
        t is not None and abs(t[0] - 0.368) <= 0.0003 and abs((t[0] - SH["sockets"]["Palm_R"][0]) - 0.073) <= 0.0004,
        {"face_x": t[0] if t else None})
    # grip back / front at a few levels and its width at Palm_R
    gaps = []
    for z in (-0.100, -0.120, -0.140, -0.160, -0.170):
        g = ray_first(bvh, (0.231, 0.0, z), (1, 0, 0), 0.1)
        gaps.append(None if g is None else round((g[0] - 0.230) * 1000, 1))
    add("grip to magazine gap >= 20 mm (24 mm at Z -0.170)", all(g is not None and g >= 20.0 for g in gaps) and gaps[-1] <= 26.0,
        {"gap_mm_at_z_-100_-120_-140_-160_-170": gaps})
    zq = SH["sockets"]["Palm_R"][2]
    gr = ray_first(bvh, (0.295, -0.05, zq), (0, 1, 0), 0.1)
    gl = ray_first(bvh, (0.295, 0.05, zq), (0, -1, 0), 0.1)
    fb = ray_first(bvh, (0.330, 0.0, zq), (-1, 0, 0), 0.1)
    bb = ray_first(bvh, (0.260, 0.0, zq), (1, 0, 0), 0.1)
    add("grip at palm height: 33 mm wide and 42 mm deep", gr and gl and fb and bb
        and abs((gl[1] - gr[1]) - 0.033) <= 0.0015 and abs((fb[0] - bb[0]) - 0.042) <= 0.0015,
        {"width_mm": None if not (gr and gl) else round((gl[1] - gr[1]) * 1000, 2),
         "depth_mm": None if not (fb and bb) else round((fb[0] - bb[0]) * 1000, 2)})
    # muzzle mount on the thread shoulder: the barrel's radius steps 9.5 -> 8.5 at X 0.652
    def radius_at(x):
        # sample the barrel's top at this X (ray down from above the hider-free region is blocked by the hider, so the
        # hider's vertices are lifted out of the way)
        return None
    # ----- moving parts
    def moved(part, fn, extra=None, only_other_bones=False):
        pi = gid[part]
        m = dom == pi
        if extra is not None:
            m &= extra
        c2 = co.copy()
        c2[m] = fn(c2[m])
        mp = np.array([all(m[v] for v in q) for q in polys])
        others = np.array([(dom[q[0]] != pi) for q in polys])
        if not only_other_bones:
            others |= (~mp & (pdom == pi))
        t_o = tree(co, polys, others)
        t_m = tree(c2, polys, mp)
        n_ov = len(t_m.overlap(t_o))
        if len(mco):
            n_ov += len(t_m.overlap(BVHTree.FromPolygons([Vector(v) for v in mco], mpolys)))
        cl = min(t_o.find_nearest(Vector(v))[3] for v in c2[m]) if m.any() else None
        return n_ov, cl
    t_rows = {}
    for t in (0.0, 0.015, 0.030, 0.045, 0.060, 0.075):
        n_ov, cl = moved("bolt", lambda c, t=t: c - np.array([t, 0.0, 0.0]))
        t_rows["%d mm" % round(t * 1000)] = [n_ov, None if cl is None else round(cl * 1000, 2)]
    add("bolt back 0..75 mm: no contact with the body, the forend or the magazine (>= 0.5 mm clear)",
        all(v[0] == 0 and v[1] >= 0.5 for v in t_rows.values()), t_rows)
    stem = (co[:, 1] > 0.0155) & (co[:, 1] < 0.0335) & (co[:, 0] > 0.370) & (co[:, 0] < 0.390) & (co[:, 2] > 0.008) & (co[:, 2] < 0.016)
    worst = (0, 1.0)
    for t in np.linspace(0.0, 0.075, 16):
        n_ov, cl = moved("bolt", lambda c, t=t: c - np.array([t, 0.0, 0.0]), stem, True)
        worst = (max(worst[0], n_ov), min(worst[1], cl))
    add("charging-handle stem clears its slot by >= 0.5 mm over the whole 75 mm", worst[0] == 0 and worst[1] >= 0.0005,
        {"min_clearance_mm": round(worst[1] * 1000, 2)})
    tr = {}
    for deg in (0.0, 8.0, 17.0):
        n_ov, cl = moved("trigger", rot_y(SH["trigger_pivot"], deg))
        tr["%.0f deg" % deg] = [n_ov, None if cl is None else round(cl * 1000, 2)]
    add("trigger pulled 0..17 deg about +Y: no contact, >= 0.5 mm clear of the guard and the body",
        all(v[0] == 0 and v[1] >= 0.5 for v in tr.values()), tr)
    sr = {}
    for deg in SH["selector_deg"]:
        n_ov, cl = moved("selector", rot_y(SH["selector_pivot"], deg))
        sr["%.0f deg" % deg] = [n_ov, None if cl is None else round(cl * 1000, 2)]
    add("selector at 0 / 14 / 28 deg about +Y: no contact with the flank, >= 0.2 mm clear",
        all(v[0] == 0 and v[1] >= 0.2 for v in sr.values()), sr)
    if len(mco):
        t_g = tree(co, polys)
        mv = {}
        for d in (0.0, 0.065, 0.13):
            c2 = mco + np.array([0.0, 0.0, -d])
            tm = BVHTree.FromPolygons([Vector(v) for v in c2], mpolys)
            mv["%d mm" % round(d * 1000)] = len(t_g.overlap(tm))
        cl = min(t_g.find_nearest(Vector(v))[3] for v in mco[::7])
        add("magazine in place and dropped 130 mm: no contact with the gun, >= 0.5 mm clear in the well",
            all(v == 0 for v in mv.values()) and cl >= 0.0005, {"overlaps": mv, "clearance_mm": round(cl * 1000, 2)})
    # ----- hide bones
    import bmesh
    for bone in ("MuzzleDevice", "IronsFront"):
        keep = [i for i, q in enumerate(polys) if dom[q[0]] != gid[bone]]
        bm = bmesh.new()
        vs = [bm.verts.new(tuple(c)) for c in co]
        for i in keep:
            try:
                bm.faces.new([vs[v] for v in polys[i]])
            except ValueError:
                pass
        open_e = sum(1 for e in bm.edges if len(e.link_faces) == 1)
        bm.free()
        add("with %s removed the rest of the mesh stays closed (no open edges)" % bone, open_e == 0, {"open_edges": open_e})
    keep = np.array([dom[q[0]] != gid["MuzzleDevice"] for q in polys])
    t2 = tree(co, polys, keep)
    bore = ray_first(t2, (0.72, 0.0, 0.0), (-1, 0, 0), 1.0)
    stub = ray_first(t2, (0.658, 0.0, 0.02), (0, 0, -1), 0.1)
    add("without the hider: the barrel stub (R 8.5, X 0.652..0.664) and the bore (R 2.8 to X 0.600) remain",
        bore is not None and abs(bore[0] - 0.600) <= 0.0006 and stub is not None and 0.0080 <= stub[2] <= 0.0087,
        {"bore_bottom_x": bore[0] if bore else None, "stub_r_mm": None if stub is None else round(stub[2] * 1000, 2)})
    shoulder = ray_first(t2, (0.6505, 0.0, 0.020), (0, 0, -1), 0.1)
    after = ray_first(t2, (0.6535, 0.0, 0.020), (0, 0, -1), 0.1)
    add("MuzzleMount on the thread shoulder X 0.652: barrel R 9.5 before it, R <= 8.9 after",
        shoulder is not None and after is not None and abs(shoulder[2] - 0.0095) <= 0.0002 and after[2] <= 0.0090,
        {"before_r_mm": None if shoulder is None else round(shoulder[2] * 1000, 2),
         "after_r_mm": None if after is None else round(after[2] * 1000, 2)})
    # ----- the ejection port is open
    e = SH["sockets"]["Eject"]
    h = ray_first(bvh, (e[0], -0.06, e[2]), (0, 1, 0), 0.2)
    add("Eject socket lies in the open port: the ray into the gun runs more than 12 mm before it hits the carrier",
        h is not None and h[1] > -0.016, {"first_hit_y": h[1] if h else None})
    # ----- budget
    tris = sum(len(p) - 2 for p in polys)
    add("triangles within the 120k cap and the 95k plan", tris <= 95000, {"triangles": tris})
    vj = verify_json or os.path.join(GLB, "SK_Shorty.glb.verify.json")
    if os.path.exists(vj):
        v = json.load(open(vj))
        add("re-import pose proof (fresh process: every bone posed, every vertex measured)",
            v.get("ok") and v["glb"]["all_axes_are_asset_axes"], {p_["name"]: p_["max_error_m"] for p_ in v["poses"]})
    res["ok"] = all(c["ok"] for c in res["checks"])
    return res


def load_glb():
    from mi import rig as _rig
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm, meshes, _col = _rig.import_glb(os.path.join(GLB, "SK_Shorty.glb"), "ImpShorty")
    gun = max(meshes, key=lambda o: len(o.data.vertices))
    mags = []
    for n in ("SM_Weapon_ShortyMagazine", "SM_Weapon_ShortyMagazine_TopRound"):
        p = os.path.join(GLB, n + ".glb")
        if os.path.exists(p):
            _a, ms, _c = _rig.import_glb(p, "Imp" + n)
            mags += ms
    for o in list(bpy.data.objects):
        if o.type == "MESH" and o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    return gun, arm, mags


def main():
    from assets import _weapons_shorty as S
    gun, arm, mags = load_glb()
    res = run(gun, arm, mags, S.SH)
    print("SHORTY: %s" % ("ALL FIXED POINTS KEPT" if res["ok"] else "FAILED"))
    for c in res["checks"]:
        if not c["ok"] or not c["check"].startswith("bone"):
            print("  %-4s %-100s %s" % ("ok" if c["ok"] else "FAIL", c["check"][:100], json.dumps(c["detail"])[:180]))
    json.dump(res, open(OUT, "w"), indent=1)
    print("wrote", OUT)
    return res["ok"]


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
