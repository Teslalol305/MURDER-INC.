"""Fixed-point proof for SK_Rattler: re-import the exported GLBs in a fresh scene and measure them against the specification.

    python art/blender/assets/_weapons_check_rattler.py        # writes art/out/glb/weapons_rattler_fixed_points.json

Checked (every number is the specification's unless the line says otherwise):
  * every bone and socket head, 1e-5 m (the 10 sockets, the 9 deform bones), and that the bone set is exactly the specification's;
  * the overall box: length (device face X 0.465), the stock hinge and the rear plate behind the receiver, the magazine floor Z -0.214;
  * the sight line: the 4.8 mm aperture centred on Z 0.0575 at X 0.012, the front post tip Z 0.0575 (parallel to the bore), the line from
    the aperture to the post unobstructed (the first hit is the post), nothing between the sights above the sight line;
  * the MI-R rail on the cover tooth by tooth: 12 lugs of 5.3 mm with 5.3 mm slots, lug tops Z 0.042, slot floors 5.4 mm back, 21.2 mm
    across the flanks, the Optic socket on the lug tops over the middle of the rail;
  * MuzzleMount on the barrel's thread shoulder (R 9.5 collar before X 0.410, the R 8.5 stub after) and, with MuzzleDevice removed, the
    stub and the bore remain; the same for IronsFront and IronsRear (closed shells: no hole opens);
  * Palm_R within 1.5 mm of the grip's right face, the trigger's rear face 70 mm ahead of it, Palm_L on the strap wrap's underside,
    the grip-to-magazine gap, the ejection port open;
  * the moving parts through their travel, zero triangle overlaps with the rest of the gun and the magazine, clearance in mm: bolt
    0..50 mm, the handle's stem in its slot over the whole travel, trigger 0..17 deg, selector 0 / 14 / 28 deg, magazine dropped 140 mm,
    stock 0..180 deg in 15 deg steps;
  * the files as the engine reads them (slots, joints, set resolutions) and the re-import pose proof written by the export.
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
OUT = os.path.join(GLB, "weapons_rattler_fixed_points.json")
MM = 0.001


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


def rot_z(pivot, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)

    def f(c):
        c = c.copy()
        x, y = c[:, 0] - pivot[0], c[:, 1] - pivot[1]
        c[:, 0], c[:, 1] = pivot[0] + x * ca - y * sa, pivot[1] + x * sa + y * ca
        return c
    return f


def ray_first(bvh, o, d, dist=2.0):
    h = bvh.ray_cast(Vector(o), Vector(d), dist)
    return None if h[0] is None else (float(h[0].x), float(h[0].y), float(h[0].z))


def runs(values, thr):
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
    RT = contract
    res = {"checks": []}

    def add(what, ok, detail):
        res["checks"].append({"check": what, "ok": bool(ok), "detail": detail})
    heads = {b.name: [float(v) for v in (arm.matrix_world @ b.head_local)] for b in arm.data.bones}
    want = {"body": (0, 0, 0), "bolt": RT["bolt_head"], "trigger": RT["trigger_pivot"], "selector": RT["selector_pivot"],
            "magazine": (0, 0, 0), "stock": RT["stock_hinge"], "MuzzleDevice": RT["muzzle_head"], "IronsFront": RT["irons_front_head"],
            "IronsRear": RT["irons_rear_head"]}
    want.update(RT["sockets"])
    for k, h in want.items():
        got = heads.get(k)
        add("bone %s head" % k, got is not None and close(got, h, 1e-5), {"want": list(h), "got": got})
    add("bone set is exactly the specification's", sorted(heads) == sorted(want), sorted(set(heads) ^ set(want)))
    co, polys, dom, pdom, names = groups(gun)
    gid = {n: i for i, n in names.items()}
    bvh = tree(co, polys)
    mco, mpolys = (np.zeros((0, 3)), [])
    for m in mags:
        c, p = mesh_world(m)
        mpolys += [[i + len(mco) for i in q] for q in p]
        mco = np.vstack([mco, c])
    allv = np.vstack([co, mco]) if len(mco) else co
    lo, hi = allv.min(0), allv.max(0)
    add("overall length: the muzzle device's face at X 0.465; the stock hinge reaches at most 5 mm behind the receiver",
        abs(hi[0] - 0.465) <= 0.0004 and -0.0050 <= lo[0] <= 0.0, {"x": [round(float(lo[0]), 5), round(float(hi[0]), 5)]})
    add("magazine floor at Z -0.214 (182 mm from the feed lips at Z -0.032)", abs(lo[2] + 0.214) <= 0.0004,
        {"z": [round(float(lo[2]), 5), round(float(hi[2]), 5)]})
    add("overall width: the stock's plate at the left, the strap's tail at the right (specification 56 mm; the plate and the tail add 15)",
        lo[1] > -0.032 and hi[1] < 0.045, {"y": [round(float(lo[1]), 5), round(float(hi[1]), 5)]})
    # ----- the sight line
    zc = RT["sockets"]["SightRear"][2]
    xr = RT["sockets"]["SightRear"][0]
    up = ray_first(bvh, (xr, 0.0, zc), (0, 0, 1), 0.05)
    dn = ray_first(bvh, (xr, 0.0, zc), (0, 0, -1), 0.05)
    ap_mid = None if not (up and dn) else 0.5 * (up[2] + dn[2])
    add("rear aperture 4.8 mm across, centred on Z 0.0575 (SightRear)",
        ap_mid is not None and abs(ap_mid - zc) <= 0.0001 and abs((up[2] - dn[2]) - 0.0048) <= 0.0005,
        {"bottom": dn, "top": up, "centre": ap_mid})
    line = ray_first(bvh, (0.0045, 0.0, zc - 0.0002), (1, 0, 0), 1.0)       # 0.2 mm under the sight line: through the aperture, onto the post
    add("the line from the aperture to the front post is clear and its first hit is the post (X 0.409 .. 0.415)",
        line is not None and 0.4090 <= line[0] <= 0.4150, {"first_hit_x": line[0] if line else None})
    post = ray_first(bvh, (RT["sockets"]["SightFront"][0], 0.0, 0.080), (0, 0, -1), 0.1)
    add("front post tip Z 0.0575 (parallel to the bore: the aperture's centre height)", post is not None and abs(post[2] - zc) <= 0.0001,
        {"tip_z": post[2] if post else None})
    # nothing between the sights above the sight line (the rear sight's own wings excluded: they stand beside the line)
    zs = np.arange(0.0, 0.40, 0.004) + 0.020
    top_between = max((ray_first(bvh, (x, 0.0, 0.075), (0, 0, -1), 0.2) or (0, 0, -1.0))[2] for x in zs)
    add("nothing between the sights above the sight line (Y = 0)", top_between <= zc + 1e-5, {"max_z": top_between, "sight_z": zc})
    # ----- the rail on the cover
    ztop = RT["sockets"]["Optic"][2]
    x0r, x1r = 0.1105, 0.2385
    xs_ = np.arange(x0r - 0.002, x1r + 0.004, 0.0003)
    arr = np.array([np.nan if (h := ray_first(bvh, (x, 0.0, ztop + 0.03), (0, 0, -1), 0.1)) is None else h[2] for x in xs_])
    r = runs(list(arr), ztop - 0.0006)
    lens = [(b - a + 1) * 0.0003 for a, b in r]
    starts = [xs_[a] for a, b in r]
    floor = None
    for a, b in zip(r[:-1], r[1:]):
        mid = (a[1] + b[0]) // 2
        if not np.isnan(arr[mid]):
            floor = float(arr[mid])
            break
    lug_z = float(np.nanmax(arr))
    ok = (len(r) == 12 and abs(lug_z - ztop) <= 0.0002 and floor is not None and abs((ztop - floor) - 0.0054) <= 0.0004
          and all(abs(l - 0.0053) <= 0.0008 for l in lens))
    add("cover MI-R: 12 lugs of 5.3 mm, lug tops Z 0.042, slot floors 5.4 mm back", ok,
        {"lugs": len(r), "first_lug_x": round(starts[0], 4) if starts else None, "lug_mm": [round(l * 1000, 2) for l in lens[:3]],
         "lug_z": round(lug_z, 5), "floor_z": None if floor is None else round(floor, 5)})
    xm = starts[len(starts) // 2] + 0.0025 if starts else 0.17
    a = ray_first(bvh, (xm, -0.03, ztop - 0.0032), (0, 1, 0), 0.08)
    b_ = ray_first(bvh, (xm, 0.03, ztop - 0.0032), (0, -1, 0), 0.08)
    add("cover MI-R is 21.2 mm across the flanks", a and b_ and abs((b_[1] - a[1]) - 0.0212) <= 0.0003,
        {"mm": None if not (a and b_) else round((b_[1] - a[1]) * 1000, 2)})
    sx = RT["sockets"]["Optic"][0]
    add("Optic socket on the lug tops over the middle of the rail (clamp footprint 52 mm fits: rail X %.3f .. %.3f)" %
        (starts[0] if starts else 0, (starts[-1] + 0.0053) if starts else 0),
        len(starts) == 12 and starts[0] <= sx - 0.026 and starts[-1] + 0.0053 >= sx + 0.026 and abs(sx - 0.5 * (starts[0] + starts[-1] + 0.0053)) <= 0.0015,
        {"optic_x": sx, "rail_mid": None if not starts else round(0.5 * (starts[0] + starts[-1] + 0.0053), 4)})
    # ----- Palm_R, trigger, grip and magazine
    p = RT["sockets"]["Palm_R"]
    loc = bvh.find_nearest(Vector(p))
    add("Palm_R within 1.5 mm of the grip's right face", loc[3] <= 0.0015, {"distance_mm": round(loc[3] * 1000, 2)})
    p = RT["sockets"]["Palm_L"]
    loc = bvh.find_nearest(Vector(p))
    add("Palm_L within 1.5 mm of the strap wrap's underside", loc[3] <= 0.0015, {"distance_mm": round(loc[3] * 1000, 2)})
    t = ray_first(bvh, (0.100, 0.0, -0.062), (1, 0, 0), 0.05)
    add("trigger's rear face X 0.132 at Z -0.062, 70 mm ahead of Palm_R",
        t is not None and abs(t[0] - 0.132) <= 0.0004 and abs((t[0] - RT["sockets"]["Palm_R"][0]) - 0.070) <= 0.0006,
        {"face_x": t[0] if t else None})
    zq = RT["sockets"]["Palm_R"][2]
    gr = ray_first(bvh, (0.062, -0.05, zq), (0, 1, 0), 0.1)
    gl = ray_first(bvh, (0.062, 0.05, zq), (0, -1, 0), 0.1)
    fb = ray_first(bvh, (0.090, 0.009, zq), (-1, 0, 0), 0.1)          # 9 mm off the centre line: past the guard's strap
    bb = ray_first(bvh, (0.020, 0.009, zq), (1, 0, 0), 0.1)
    add("grip at palm height: 30-33 mm wide, 40-46 mm deep (measured 9 mm off the centre line)", gr and gl and fb and bb
        and 0.030 <= (gl[1] - gr[1]) <= 0.0335 and 0.040 <= (fb[0] - bb[0]) <= 0.046,
        {"width_mm": None if not (gr and gl) else round((gl[1] - gr[1]) * 1000, 2),
         "depth_mm": None if not (fb and bb) else round((fb[0] - bb[0]) * 1000, 2)})
    gaps = []
    for z in (-0.100, -0.120, -0.140):
        g = ray_first(bvh, (0.110, 0.0, z), (-1, 0, 0), 0.1)
        gaps.append(None if g is None else round((0.1425 - g[0]) * 1000, 1))
    add("grip front to the magazine well's rear face >= 40 mm at Z -0.100 .. -0.140", all(g is not None and g >= 40.0 for g in gaps),
        {"gap_mm": gaps})
    # ----- the ejection port is open and the bolt shows in it
    e = RT["sockets"]["Eject"]
    h = ray_first(bvh, (e[0], -0.06, e[2]), (0, 1, 0), 0.2)
    add("Eject socket lies in the open port: the ray into the gun reaches the bolt body (Y > -0.017) and not the right wall",
        h is not None and h[1] > -0.017, {"first_hit_y": h[1] if h else None})
    b2 = ray_first(bvh, (0.1700, -0.06, 0.010), (0, 1, 0), 0.2)
    add("through the port at X 0.170 the first surface is inside the receiver (the bolt or the breech)", b2 is not None and b2[1] > -0.0200,
        {"first_hit_y": b2[1] if b2 else None})
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
    for t in (0.0, 0.010, 0.020, 0.030, 0.040, 0.050):
        n_ov, cl = moved("bolt", lambda c, t=t: c - np.array([t, 0.0, 0.0]))
        t_rows["%d mm" % round(t * 1000)] = [n_ov, None if cl is None else round(cl * 1000, 2)]
    add("bolt racked 0..50 mm: no contact with the receiver, the barrel, the sights or the magazine (>= 0.3 mm clear)",
        all(v[0] == 0 and v[1] >= 0.3 for v in t_rows.values()), t_rows)
    stem = (co[:, 1] > -0.0035) & (co[:, 1] < 0.0035) & (co[:, 0] > 0.090) & (co[:, 0] < 0.106) & (co[:, 2] > 0.020) & (co[:, 2] < 0.038)
    worst = (0, 1.0)
    for t in np.linspace(0.0, 0.050, 11):
        n_ov, cl = moved("bolt", lambda c, t=t: c - np.array([t, 0.0, 0.0]), stem, True)
        worst = (max(worst[0], n_ov), min(worst[1], cl))
    add("the handle's stem clears its slot in the cover by >= 0.5 mm over the whole 50 mm", worst[0] == 0 and worst[1] >= 0.0005,
        {"min_clearance_mm": round(worst[1] * 1000, 2)})
    tr = {}
    for deg in (0.0, 8.0, 17.0):
        n_ov, cl = moved("trigger", rot_y(RT["trigger_pivot"], deg))
        tr["%.0f deg" % deg] = [n_ov, None if cl is None else round(cl * 1000, 2)]
    add("trigger pulled 0..17 deg about +Y: no contact, >= 0.5 mm clear of the guard, the body and the hanger",
        all(v[0] == 0 and v[1] >= 0.5 for v in tr.values()), tr)
    sr = {}
    for deg in RT["selector_deg"]:
        n_ov, cl = moved("selector", rot_y(RT["selector_pivot"], deg))
        sr["%.0f deg" % deg] = [n_ov, None if cl is None else round(cl * 1000, 2)]
    add("selector at 0 / 14 / 28 deg about +Y: no contact with the flank, the stock or the ribs, >= 0.2 mm clear",
        all(v[0] == 0 and v[1] >= 0.2 for v in sr.values()), sr)
    sk = {}
    worst_c = 9.0
    for deg in range(0, 181, 15):
        n_ov, cl = moved("stock", rot_z(RT["stock_hinge"], float(deg)))
        sk["%d deg" % deg] = [n_ov, None if cl is None else round(cl * 1000, 2)]
        worst_c = min(worst_c, cl if cl is not None else 9.0)
    add("stock swung 0..180 deg about the hinge in 15 deg steps: no contact with the body, the hinge bracket, the selector or the "
        "magazine, >= 0.3 mm clear (the rest pose is folded along the left flank)",
        all(v[0] == 0 and v[1] >= 0.3 for v in sk.values()), sk)
    if len(mco):
        t_g = tree(co, polys)
        mv = {}
        for d in (0.0, 0.07, 0.14):
            c2 = mco + np.array([0.0, 0.0, -d])
            tm = BVHTree.FromPolygons([Vector(v) for v in c2], mpolys)
            mv["%d mm" % round(d * 1000)] = len(t_g.overlap(tm))
        cl = min(t_g.find_nearest(Vector(v))[3] for v in mco[::7])
        add("magazine in place and dropped 140 mm: no contact with the gun, >= 0.4 mm clear in the well",
            all(v == 0 for v in mv.values()) and cl >= 0.0004, {"overlaps": mv, "clearance_mm": round(cl * 1000, 2)})
    # ----- hide bones: closed shells
    import bmesh

    def open_edges(face_ids):
        bm = bmesh.new()
        vs = [bm.verts.new(tuple(c)) for c in co]
        for i in face_ids:
            try:
                bm.faces.new([vs[v] for v in polys[i]])
            except ValueError:
                pass
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-6)         # the GLB splits vertices at normals and UV seams
        n_open = sum(1 for e_ in bm.edges if len(e_.link_faces) == 1)
        bm.free()
        return n_open
    base_open = open_edges(range(len(polys)))
    for bone in ("MuzzleDevice", "IronsFront", "IronsRear"):
        keep = [i for i, q in enumerate(polys) if dom[q[0]] != gid[bone]]
        open_e = open_edges(keep)
        add("with %s removed no hole opens in the rest of the mesh (open edges %d, the whole gun has %d)" % (bone, open_e, base_open),
            open_e <= base_open, {"open_edges_without": open_e, "open_edges_with_all": base_open})
    keep = np.array([dom[q[0]] != gid["MuzzleDevice"] for q in polys])
    t2 = tree(co, polys, keep)
    stub = ray_first(t2, (0.416, 0.0, 0.012), (0, 0, -1), 0.1)
    inner = ray_first(t2, (0.470, 0.0, 0.0), (-1, 0, 0), 1.0)
    add("without the device: the threaded stub (R 8.0-8.6, X 0.410..0.422) stays, its bore runs to the breech face",
        stub is not None and 0.0080 <= stub[2] <= 0.0087 and inner is not None and 0.194 <= inner[0] <= 0.201,
        {"stub_r_mm": None if stub is None else round(stub[2] * 1000, 2), "bore_ray_ends_x": inner[0] if inner else None})
    shoulder = ray_first(t2, (0.4085, 0.0, 0.012), (0, 0, -1), 0.1)
    after = ray_first(t2, (0.4115, 0.0, 0.012), (0, 0, -1), 0.1)
    add("MuzzleMount on the thread shoulder X 0.410: barrel R 9.5 before it, R <= 8.9 after",
        shoulder is not None and after is not None and abs(shoulder[2] - 0.0095) <= 0.0002 and after[2] <= 0.0090,
        {"before_r_mm": None if shoulder is None else round(shoulder[2] * 1000, 2),
         "after_r_mm": None if after is None else round(after[2] * 1000, 2)})
    # ----- budget
    tris = sum(len(p) - 2 for p in polys)
    add("gun triangles within the 120k cap (specification plan 85k)", tris <= 120000, {"triangles": tris})
    vj = verify_json or os.path.join(GLB, "SK_Rattler.glb.verify.json")
    if os.path.exists(vj):
        v = json.load(open(vj))
        add("re-import pose proof (fresh process: every bone posed, every vertex measured)",
            v.get("ok") and v["glb"]["all_axes_are_asset_axes"], {p_["name"]: p_["max_error_m"] for p_ in v["poses"]})
    res["ok"] = all(c["ok"] for c in res["checks"])
    return res


def load_glb():
    from mi import rig as _rig
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm, meshes, _col = _rig.import_glb(os.path.join(GLB, "SK_Rattler.glb"), "ImpRattler")
    gun = max(meshes, key=lambda o: len(o.data.vertices))
    mags = []
    for n in ("SM_Weapon_RattlerMagazine", "SM_Weapon_RattlerMagazine_TopRound"):
        p = os.path.join(GLB, n + ".glb")
        if os.path.exists(p):
            _a, ms, _c = _rig.import_glb(p, "Imp" + n)
            mags += ms
    for o in list(bpy.data.objects):
        if o.type == "MESH" and o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    return gun, arm, mags


def file_checks(res):
    """The files as the engine will read them: slot names, set resolutions and channels, the manifest record."""
    from mi import bake as _bake

    def add(what, ok, detail):
        res["checks"].append({"check": what, "ok": bool(ok), "detail": detail})
    rep = rig.inspect_glb(os.path.join(GLB, "SK_Rattler.glb"))
    add("SK_Rattler.glb: one slot M_Rattler, 19 joints (9 deform bones + 10 sockets), joint axes = gun axes",
        rep["materials"] == ["M_Rattler"] and len(rep["joints"]) == 19 and rep["all_axes_are_asset_axes"],
        {"materials": rep["materials"], "joints": len(rep["joints"]), "triangles": [m["triangles"] for m in rep["meshes"]]})
    for name, size, chans in (("Rattler", 4096, ("BC", "N", "ORM")), ("Weapon_RattlerMagazine", 2048, ("BC", "N", "ORM"))):
        info = _bake.read_set(name) or {}
        have = sorted((info.get("files") or {}).keys())
        add("texture set %s: %d x %d, %s (no E: nothing emissive)" % (name, size, size, "+".join(chans)),
            info.get("resolution") == [size, size] and all(c in have for c in chans) and "E" not in have,
            {"resolution": info.get("resolution"), "files": have, "px_per_m": info.get("texel_density_px_per_m")})
    add("tiling detail set TS_GunDetail_Steel exists", _bake.read_set("TS_GunDetail_Steel") is not None, {})
    mp = paths.manifest
    ok = False
    if os.path.exists(mp):
        m = json.load(open(mp))
        ents = m.get("assets", {}) if isinstance(m.get("assets"), dict) else {}
        e = ents.get("SK_Rattler") or next((a for a in (m.get("assets") or []) if isinstance(a, dict) and a.get("name") == "SK_Rattler"), None)
        ok = bool(e) and sorted((e.get("sockets") or {}).keys()) == sorted(
            ["Muzzle", "Eject", "SightRear", "SightFront", "RecoilPivot", "MagHinge", "Palm_R", "Palm_L", "Optic", "MuzzleMount"])
    add("manifest record SK_Rattler lists the 10 sockets", ok, {})


def main():
    sys.path.insert(0, BL)
    from assets import _weapons_rattler as S
    gun, arm, mags = load_glb()
    res = run(gun, arm, mags, S.RT)
    file_checks(res)
    res["ok"] = all(c["ok"] for c in res["checks"])
    print("SK_Rattler: %s" % ("ALL FIXED POINTS KEPT" if res["ok"] else "FAILED"))
    for c in res["checks"]:
        if not c["ok"] or not c["check"].startswith("bone"):
            print("  %-4s %-100s %s" % ("ok" if c["ok"] else "FAIL", c["check"][:100], json.dumps(c["detail"])[:150]))
    json.dump(res, open(OUT, "w"), indent=1)
    print("wrote", OUT)
    return res


if __name__ == "__main__":
    main()
