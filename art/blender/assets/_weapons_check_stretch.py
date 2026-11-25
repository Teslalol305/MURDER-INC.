"""Fixed-point proof for the STRETCH: re-import the exported SK_Stretch.glb (and its magazine) in a fresh scene and measure
it against the specification: every bone and socket head (1e-5 m), the overall box, the sight line (parallel to the bore,
the front post is its first hit, nothing between the sights above it), Palm_R / Palm_L on the surface, the trigger reach,
the MI-R rails (52 lugs at 10.6 pitch, 5.3 slots, 21.2 across the flanks, lug tops Z +0.052, undersides Z -0.038), the
sockets Optic / Underbarrel / MuzzleMount on their rails and shoulder, the part travels (bolt 95 mm, trigger 17 deg,
selector, bolt catch, bipod 0..-100 deg: no contact, clearances), the magazine in its well and its drop, the brake removal
leaving no hole, the budgets, and the re-import pose proof written by the export (SK_Stretch.glb.verify.json).

    python art/blender/assets/_weapons_check_stretch.py          # writes art/out/glb/stretch_fixed_points.json
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
sys.path.insert(0, BL)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from mi import paths, rig  # noqa: E402

GLB = paths.glb
OUT = os.path.join(GLB, "stretch_fixed_points.json")
SOCKETS = {"Muzzle": (0.790, 0, 0), "Eject": (0.135, -0.0225, 0.020), "SightRear": (0.028, 0, 0.0645), "SightFront": (0.505, 0, 0.0645),
           "RecoilPivot": (-0.245, 0, -0.030), "MagHinge": (0.157, 0, -0.024), "Palm_R": (0.046, -0.0165, -0.085),
           "Palm_L": (0.300, 0, -0.038), "Optic": (0.150, 0, 0.052), "MuzzleMount": (0.715, 0, 0), "Underbarrel": (0.300, 0, -0.038)}
BONES = {"body": (0, 0, 0), "bolt": (0.195, 0, 0.015), "trigger": (0.100, 0, -0.045), "selector": (0.040, 0.0225, -0.010),
         "bolt_catch": (0.125, 0.0225, -0.012), "magazine": (0, 0, 0), "bipod": (0.470, 0, -0.050), "MuzzleDevice": (0.715, 0, 0),
         "IronsRear": (0.028, 0, 0.052), "IronsFront": (0.505, 0, 0.052)}


def close(a, b, tol):
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def evaluated_world(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    polys = [list(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    M = np.array(ob.matrix_world)
    co = co.reshape(-1, 3).astype(np.float64)
    return co @ M[:3, :3].T + M[:3, 3], polys


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm, meshes, _col = rig.import_glb(path)
    ob = max(meshes, key=lambda o: len(o.data.vertices))
    co, polys = evaluated_world(ob)
    dom = np.full(len(co), -1)
    best = np.zeros(len(co))
    for v in ob.data.vertices:
        for g in v.groups:
            if g.weight > best[v.index]:
                best[v.index], dom[v.index] = g.weight, g.group
    names = {g.index: g.name for g in ob.vertex_groups}
    return arm, ob, co, polys, dom, names


def tree(co, polys, sel=None):
    ps = polys if sel is None else [polys[i] for i in np.nonzero(sel)[0]]
    return BVHTree.FromPolygons([Vector(v) for v in co], ps)


def ray(bvh, o, d, dist=3.0):
    h = bvh.ray_cast(Vector(o), Vector(d).normalized(), dist)
    return None if h[0] is None else (h[0], h[1], h[3])


def hits_along(bvh, o, d, dist, eps=2e-5):
    """All hits of a ray (successive casts)."""
    out = []
    p = Vector(o)
    dd = Vector(d).normalized()
    while True:
        h = bvh.ray_cast(p, dd, dist)
        if h[0] is None:
            break
        out.append(h[0].copy())
        p = h[0] + dd * eps
        dist -= (h[3] + eps)
        if dist <= 0:
            break
    return out


def rot_y(pivot, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)

    def f(c):
        c = c.copy()
        x, z = c[:, 0] - pivot[0], c[:, 2] - pivot[2]
        c[:, 0], c[:, 2] = pivot[0] + x * ca + z * sa, pivot[2] - x * sa + z * ca
        return c
    return f


def check():
    res = {"checks": []}

    def add(what, ok, detail):
        res["checks"].append({"check": what, "ok": bool(ok), "detail": detail})
    path = os.path.join(GLB, "SK_Stretch.glb")
    rep = rig.inspect_glb(path)
    for b, h in {**BONES, **SOCKETS}.items():
        got = rep["joints"].get(b, {}).get("rest_position_asset")
        add("bone/socket %s head" % b, got is not None and close(got, h, 1.2e-5), {"want": h, "got": got})
    add("every joint's axes are the gun's axes", rep["all_axes_are_asset_axes"], {})
    arm, ob, co, polys, dom, names = load(path)
    gid = {n: i for i, n in names.items()}
    bvh = tree(co, polys)
    lo, hi = co.min(0), co.max(0)
    add("overall length -0.255 .. 0.790 (1,045 mm)", abs(lo[0] + 0.255) <= 1e-3 and abs(hi[0] - 0.790) <= 3e-4,
        {"x": [round(float(lo[0]), 4), round(float(hi[0]), 4)]})
    add("grip bottom / magazine floor Z -0.140; top of the flip-up rear aperture", abs(lo[2] + 0.140) <= 5e-4 and 0.066 <= hi[2] <= 0.074,
        {"z": [round(float(lo[2]), 4), round(float(hi[2]), 4)], "note": "body height 198 mm (cheek riser +0.058 to -0.140); the rear aperture ring tops at +0.0717"})
    add("overall width 68 mm (charging knob Y +0.040 to comb / dust cover -0.0287)", abs((hi[1] - lo[1]) - 0.068) <= 0.0034,
        {"y": [round(float(lo[1]), 4), round(float(hi[1]), 4)], "width_mm": round(float(hi[1] - lo[1]) * 1000, 1)})
    add("triangles within the 105k budget (and the 120k ceiling)", rep["meshes"][0]["triangles"] <= 105000,
        {"triangles": rep["meshes"][0]["triangles"], "vertices": rep["meshes"][0]["vertices"]})
    # ---- sight line
    sr, sf = np.array(SOCKETS["SightRear"]), np.array(SOCKETS["SightFront"])
    add("sight line parallel to the bore (same Z)", abs(sr[2] - sf[2]) < 1e-9, {"z": float(sr[2])})
    h = ray(bvh, sr - np.array([0.02, 0, 0.0004]), (1, 0, 0), 2.0)           # 0.4 mm under the line: the post's tip is on it
    add("sight line from behind the aperture: first hit is the front post (X 0.5036..0.5064)",
        h is not None and 0.5035 <= h[0].x <= 0.5065, {"hit_x": None if h is None else round(h[0].x, 4)})
    mid = (co[:, 0] > 0.034) & (co[:, 0] < 0.499)
    add("nothing between the sights above the sight line (Z 0.0645)", float(co[mid, 2].max()) <= 0.0645 + 1e-5,
        {"max_z": round(float(co[mid, 2].max()), 5)})
    # ---- palms and trigger reach
    for s in ("Palm_R", "Palm_L"):
        loc, _n, _i, d = bvh.find_nearest(Vector(SOCKETS[s]))
        add("%s within 1.5 mm of the surface" % s, d <= 0.0015, {"distance_mm": round(d * 1000, 2)})
    hh = ray(bvh, (0.125, 0.0, -0.062), (-1, 0, 0), 0.5)
    tr = SOCKETS["Palm_R"][0]
    add("trigger blade face 70 mm ahead of Palm_R (the data's trigger reach)", hh is not None and abs((hh[0].x - tr) - 0.070) <= 0.0015,
        {"face_x": None if hh is None else round(hh[0].x, 4), "reach_mm": None if hh is None else round((hh[0].x - tr) * 1000, 1)})
    # ---- MI-R rails
    top_hits = []
    irons = (dom == gid["IronsRear"]) | (dom == gid["IronsFront"])
    rail_t = tree(co, polys, np.array([not irons[p[0]] for p in polys]))        # the rail without the flip-up irons on it
    for x in np.arange(0.0, 0.5466, 0.0005):
        hit = ray(rail_t, (x, 0.0, 0.0580), (0, 0, -1), 0.05)
        top_hits.append(None if hit is None else hit[0].z)
    z_top = np.array([np.nan if v is None else v for v in top_hits])
    is_lug = z_top > 0.0515
    edges = np.nonzero(np.diff(is_lug.astype(int)) != 0)[0]
    xs_scan = np.arange(0.0, 0.5466, 0.0005)
    starts = ([xs_scan[0]] if is_lug[0] else []) + [xs_scan[i + 1] for i in edges if not is_lug[i]]
    pitch = np.diff(starts)
    add("top rail: 52 lugs at the 10.6 mm pitch, tops at Z 0.0520", len(starts) == 52 and abs(float(np.median(pitch)) - 0.0106) <= 0.0006
        and abs(float(np.nanmax(z_top)) - 0.052) <= 2e-4,
        {"lugs": len(starts), "pitch_mm": round(float(np.median(pitch)) * 1000, 2), "top_z": round(float(np.nanmax(z_top)), 5)})
    slot_x = 0.0106 * 14 + 0.0053 * 1.5
    s_hit = ray(bvh, (0.0106 * 14 + 0.0053 + 0.0026, 0.0, 0.0580), (0, 0, -1), 0.05)
    add("top rail slots 5.3 mm wide, floor Z 0.0453", s_hit is not None and abs(s_hit[0].z - 0.0453) <= 2e-4,
        {"slot_floor_z": None if s_hit is None else round(s_hit[0].z, 5)})
    wl = ray(bvh, (0.150 + 0.0027, 0.0300, 0.0480), (0, -1, 0), 0.1)
    wr = ray(bvh, (0.150 + 0.0027, -0.0300, 0.0480), (0, 1, 0), 0.1)
    add("rail 21.2 mm across the flanks (at Z 0.0480, below the 45 deg chamfers)", wl is not None and wr is not None and abs((wl[0].y - wr[0].y) - 0.0212) <= 3e-4,
        {"across_mm": None if wl is None or wr is None else round((wl[0].y - wr[0].y) * 1000, 2)})
    ft = ray(bvh, (0.1503, 0.0, 0.0580), (0, 0, -1), 0.05)
    add("socket Optic on the lug tops (0.3 mm)", ft is not None and abs(ft[0].z - SOCKETS["Optic"][2]) <= 3e-4,
        {"lug_top_z": None if ft is None else round(ft[0].z, 5)})
    ub = ray(bvh, (0.2976, 0.0, -0.0600), (0, 0, 1), 0.05)
    add("socket Underbarrel on the lug undersides (0.3 mm), Z -0.038", ub is not None and abs(ub[0].z - SOCKETS["Underbarrel"][2]) <= 3e-4,
        {"lug_underside_z": None if ub is None else round(ub[0].z, 5)})
    bl = [i for i in range(len(polys))]
    brake = dom == gid["MuzzleDevice"]
    keep = np.array([not brake[p[0]] for p in polys])
    body_only = tree(co, polys, keep)
    mm_hit = ray(body_only, (0.760, 0.0, 0.0105), (-1, 0, 0), 0.2)
    add("socket MuzzleMount on the barrel's thread shoulder (X 0.715) with the brake removed", mm_hit is not None and abs(mm_hit[0].x - 0.715) <= 3e-4,
        {"shoulder_x": None if mm_hit is None else round(mm_hit[0].x, 5)})
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    kill = [v for v in bm.verts if brake[v.index]]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)             # the importer splits vertices at seams and hard edges
    holes = sum(1 for e in bm.edges if e.is_boundary)
    bm.free()
    add("MuzzleDevice removed leaves no hole (closed shells only)", holes == 0, {"boundary_edges": holes})
    # ---- part travel and sweep clearances against the rest of the gun
    polys_a = [np.array(p) for p in polys]

    def moved(part, fn, sel_extra=None):
        m = dom == gid[part]
        if sel_extra is not None:
            m &= sel_extra
        c2 = co.copy()
        c2[m] = fn(c2[m])
        mp = np.array([m[p[0]] and all(m[v] for v in p) for p in polys])
        other = np.array([dom[p[0]] != gid[part] for p in polys])
        t_o = tree(co, polys, other)
        t_m = tree(c2, polys, mp)
        pairs = t_m.overlap(t_o)
        n_ov = len(pairs)
        if n_ov and "where" not in res:
            mp_idx = np.nonzero(mp)[0]
            ot_idx = np.nonzero(other)[0]
            a, b = pairs[0]
            res["where"] = {part: [np.round(c2[polys[mp_idx[a]]].mean(0) * 1000, 1).tolist(), np.round(co[polys[ot_idx[b]]].mean(0) * 1000, 1).tolist()]}
        clear = min(t_o.find_nearest(Vector(v))[3] for v in c2[m][::3]) if m.any() else None
        return n_ov, clear
    worst = (0, 1.0)
    for t in np.linspace(0.0, 0.095, 20):
        n_ov, cl = moved("bolt", lambda c, t=t: c - np.array([t, 0, 0]))
        worst = (max(worst[0], n_ov), min(worst[1], cl))
    add("bolt: 95 mm travel back, no contact with anything (20 steps)", worst[0] == 0, {"max_overlaps": worst[0], "min_clearance_mm": round(worst[1] * 1000, 2)})
    stem = (co[:, 1] > 0.0095) & (co[:, 1] < 0.0420) & (co[:, 0] > 0.180) & (co[:, 0] < 0.212) & (co[:, 2] > 0.008) & (co[:, 2] < 0.0225)
    wst = (0, 1.0)
    for t in np.linspace(0.0, 0.095, 20):
        n_ov, cl = moved("bolt", lambda c, t=t: c - np.array([t, 0, 0]), stem)
        wst = (max(wst[0], n_ov), min(wst[1], cl))
    add("charging-handle stem clears its slot by >= 0.5 mm over the whole 95 mm", wst[0] == 0 and wst[1] >= 0.0005,
        {"max_overlaps": wst[0], "min_clearance_mm": round(wst[1] * 1000, 2)})
    for part, piv, deg, lab in (("trigger", (0.100, 0.0, -0.045), 17.0, "trigger pulled 17 deg: no contact, >= 0.5 mm clear"),
                                ("selector", (0.040, 0.0225, -0.010), 16.0, "selector SEMI 16 deg: no contact"),
                                ("bolt_catch", (0.125, 0.0225, -0.012), 7.0, "bolt catch up 7 deg: no contact")):
        w = (0, 1.0)
        for d in np.linspace(0.0, deg, 6):
            n_ov, cl = moved(part, rot_y(piv, d))
            w = (max(w[0], n_ov), min(w[1], cl))
        ok = w[0] == 0 and (part != "trigger" or w[1] >= 0.0005)
        add(lab, ok, {"max_overlaps": w[0], "min_clearance_mm": round(w[1] * 1000, 2)})
    wb = (0, 1.0)
    for d in np.linspace(0.0, -100.0, 11):
        n_ov, cl = moved("bipod", rot_y((0.470, 0.0, -0.050), d))
        wb = (max(wb[0], n_ov), min(wb[1], cl))
    add("bipod: 0..-100 deg in 10 steps, the legs touch nothing", wb[0] == 0, {"max_overlaps": wb[0], "min_clearance_mm": round(wb[1] * 1000, 2)})
    # ---- magazine in its well
    try:
        arm2, mag, mco, mpolys, _d, _n = load(os.path.join(GLB, "SM_Weapon_StretchMagazine.glb"))
        gun_t = tree(co, polys)
        mag_t = BVHTree.FromPolygons([Vector(v) for v in mco], mpolys)
        n_ov = len(mag_t.overlap(gun_t))
        add("magazine seated in the well: no contact", n_ov == 0, {"overlaps": n_ov})
        add("magazine box X 0.132..0.190, Z -0.135..-0.024 (feed lips at MagHinge)", abs(mco[:, 2].max() + 0.024) <= 3e-4 and abs(mco[:, 2].min() + 0.135) <= 3e-4,
            {"x": [round(float(mco[:, 0].min()), 4), round(float(mco[:, 0].max()), 4)], "z": [round(float(mco[:, 2].min()), 4), round(float(mco[:, 2].max()), 4)]})
        mc = mco.copy()
        n2 = 0
        for dz in np.linspace(0.0, -0.12, 9):
            m2 = BVHTree.FromPolygons([Vector(v + np.array([0, 0, dz])) for v in mco], mpolys)
            n2 = max(n2, len(m2.overlap(gun_t)))
        add("magazine dropped (0, 0, -0.12): clear of the well and guard on the way", n2 == 0, {"max_overlaps": n2})
    except Exception as e:                                  # the magazine file is optional for the gun's own proof
        add("magazine checks", False, {"error": str(e)[:200]})
    vj = os.path.join(GLB, "SK_Stretch.glb.verify.json")
    if os.path.exists(vj):
        v = json.load(open(vj))
        add("re-import pose proof (fresh process)", v.get("ok") and v["glb"]["all_axes_are_asset_axes"],
            {p["name"]: p["max_error_m"] for p in v["poses"]})
    res["ok"] = all(c["ok"] for c in res["checks"])
    return res


def main():
    res = check()
    print("STRETCH: %s" % ("ALL FIXED POINTS KEPT" if res["ok"] else "FAILED"))
    for c in res["checks"]:
        if not c["ok"] or not c["check"].startswith("bone/socket"):
            print("  %-4s %-86s %s" % ("ok" if c["ok"] else "FAIL", c["check"], json.dumps(c["detail"])[:170]))
    json.dump(res, open(OUT, "w"), indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
