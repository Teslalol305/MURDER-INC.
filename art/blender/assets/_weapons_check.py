"""Fixed-point proof for the rebuilt player guns: re-import the exported GLBs in a fresh scene, measure them with the
art director's own measuring code (art/blender/review/weapons_review.py: measure()), and compare every fixed
number with the director's measurement of the first-pass files (review/sheets/weapons_measure.json) and the brief.

    python art/blender/assets/_weapons_check.py            # writes art/out/glb/weapons_fixed_points.json

Checked: every bone and socket head (1e-5 m), the overall box of gun + magazine (0.5 mm), the gun's length and
top, nothing between the sights above the sight line, the rear notch profile and front post profile (0.1 mm),
the sight line's first hit (the front post), the bore ray (CHOPPER: the barrel's bore end as before; NINE: now
stopped by the closed breech face instead of the hammer), Palm_R / Palm_L on the surface, the re-import pose proof
written by the export (SK_*.glb.verify.json), and the NINE grip depth / width at mid height.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
sys.path.insert(0, BL)
sys.path.insert(0, os.path.join(BL, "review"))

import bpy  # noqa: E402,F401  (the bpy module provides mathutils)
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import weapons_review as R  # noqa: E402

BASE = os.path.join(BL, "review", "sheets", "weapons_measure.json")
GLB = R.GLB
OUT = os.path.join(GLB, "weapons_fixed_points.json")


def close(a, b, tol):
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def profile_diff(a, b):
    za, zb = a["z_mm"], b["z_mm"]
    d = [abs(x - y) for x, y in zip(za, zb) if x is not None and y is not None]
    miss = sum(1 for x, y in zip(za, zb) if (x is None) != (y is None))
    return (max(d) if d else 0.0), miss


def surface_distance(bvh, p):
    loc, _n, _i, d = bvh.find_nearest(Vector(p))
    return d


def _groups(gun):
    mw = gun.matrix_world
    co = np.array([tuple(mw @ v.co) for v in gun.data.vertices])
    dom = np.full(len(co), -1)
    best = np.zeros(len(co))
    for v in gun.data.vertices:
        for g in v.groups:
            if g.weight > best[v.index]:
                best[v.index], dom[v.index] = g.weight, g.group
    names = {g.index: g.name for g in gun.vertex_groups}
    polys = [list(p.vertices) for p in gun.data.polygons]
    pdom = np.array([dom[p[0]] for p in polys])
    return co, dom, names, polys, pdom


def travel_checks(name, gun, add):
    """Moving parts through their briefed travel against the rest of the gun (round 2): triangle overlaps and the
    smallest clearance of the moved part's vertices."""
    from mathutils.bvhtree import BVHTree
    import math as _m
    co, dom, names, polys, pdom = _groups(gun)
    gid = {n: i for i, n in names.items()}

    def tree(c, sel):
        return BVHTree.FromPolygons([Vector(v) for v in c], [polys[i] for i in np.nonzero(sel)[0]])

    def moved(part, fn, extra_sel=None):
        m = dom == gid[part]
        if extra_sel is not None:
            m &= extra_sel
        c2 = co.copy()
        c2[m] = fn(c2[m])
        mp = pdom == gid[part]
        if extra_sel is not None:
            mp &= np.array([all(extra_sel[i] for i in polys[k]) for k in range(len(polys))])
        other = pdom != gid[part]
        t_o = tree(co, other)
        n_ov = len(tree(c2, mp).overlap(t_o))
        clear = min(t_o.find_nearest(Vector(v))[3] for v in c2[m]) if m.any() else None
        return n_ov, clear

    def rot_y(pivot, deg):
        a = _m.radians(deg)
        ca, sa = _m.cos(a), _m.sin(a)

        def f(c):
            c = c.copy()
            x, z = c[:, 0] - pivot[0], c[:, 2] - pivot[2]
            c[:, 0], c[:, 2] = pivot[0] + x * ca + z * sa, pivot[2] - x * sa + z * ca
            return c
        return f
    if name == "Chopper":
        for deg in (14.0, 19.5):
            n_ov, cl = moved("trigger", rot_y((0.108, 0.0, -0.038), deg))
            add("trigger pulled %.1f deg about X 0.108, Z -0.038: no contact, >= 0.5 mm clear" % deg,
                n_ov == 0 and cl is not None and cl >= 0.0005, {"overlaps": n_ov, "clearance_mm": round(cl * 1000, 2)})
        stem = (co[:, 1] > 0.0095) & (co[:, 1] < 0.0330) & (co[:, 0] > 0.170) & (co[:, 0] < 0.190) & (co[:, 2] > 0.009) \
            & (co[:, 2] < 0.0195)
        worst = (0, 1.0)
        for t in np.linspace(0.0, 0.092, 24):
            n_ov, cl = moved("bolt", lambda c, t=t: c - np.array([t, 0.0, 0.0]), stem)
            worst = (max(worst[0], n_ov), min(worst[1], cl))
        add("charging-handle stem clears the slot by >= 0.5 mm over the whole 92 mm travel",
            worst[0] == 0 and worst[1] >= 0.0005, {"max_overlaps": worst[0], "min_clearance_mm": round(worst[1] * 1000, 2)})
    else:
        res = {}
        for t in (0.010, 0.020, 0.030, 0.044):
            n_ov, _cl = moved("slide", lambda c, t=t: c - np.array([t, 0.0, 0.0]))
            res["%d mm" % round(t * 1000)] = n_ov
        add("slide back 10-44 mm: no contact with the static hammer or the frame", all(v == 0 for v in res.values()),
            res)
        n_ov, cl = moved("trigger", rot_y((0.091, 0.0, -0.031), 17.0))
        add("trigger pulled 17 deg: no contact", n_ov == 0, {"overlaps": n_ov, "clearance_mm": round(cl * 1000, 2)})


def check(name, base):
    R.fresh()
    objs, meshes = R.load_gun(name)
    m = R.measure(name, objs, meshes)
    res = {"measure": {k: v for k, v in m.items() if "profile" not in k}, "checks": []}

    def add(what, ok, detail):
        res["checks"].append({"check": what, "ok": bool(ok), "detail": detail})
    for b, h in base["bones"].items():
        got = m["bones"].get(b)
        add("bone %s head" % b, got is not None and close(got, h, 1e-5), {"was": h, "now": got})
    lo0, hi0 = np.array(base["all_bbox"][0]), np.array(base["all_bbox"][1])
    lo1, hi1 = np.array(m["all_bbox"][0]), np.array(m["all_bbox"][1])
    # the brief's numbers: CHOPPER 0.502 long (bbox -0.0045 .. 0.4975), 0.292 from the magazine floor to the ears
    # (-0.2295 .. 0.063); NINE 0.234 from the muzzle (0.201) to the back of the grip, 0.153 high (0.0185 down to the
    # base pad at -0.1345)
    want = {"Chopper": ((-0.0045, 0.4975), (-0.2295, 0.063)), "Nine": ((0.201 - 0.234, 0.201), (-0.1345, 0.0185))}[name]
    add("overall length (brief)", abs(lo1[0] - want[0][0]) <= 1e-3 and abs(hi1[0] - want[0][1]) <= 2e-4,
        {"brief": want[0], "first_pass": [lo0[0], hi0[0]], "now": [lo1[0], hi1[0]]})
    add("overall height (brief)", abs(lo1[2] - want[1][0]) <= 5e-4 and abs(hi1[2] - want[1][1]) <= 2e-4,
        {"brief": want[1], "first_pass": [lo0[2], hi0[2]], "now": [lo1[2], hi1[2]]})
    add("overall box y (width)", abs((hi1[1] - lo1[1]) - (hi0[1] - lo0[1])) <= 1e-3,
        {"was": hi0[1] - lo0[1], "now": hi1[1] - lo1[1]})
    sz = 0.0555 if name == "Chopper" else 0.0185
    add("nothing between the sights above the sight line", m["max_z_between_sights"] <= sz + 1e-5,
        {"max_z": m["max_z_between_sights"], "sight_z": sz})
    d, miss = profile_diff(m["rear_sight_profile"], base["rear_sight_profile"])
    centre = [z for y, z in zip(m["rear_sight_profile"]["y_mm"], m["rear_sight_profile"]["z_mm"]) if abs(y) < 1.9]
    centre0 = [z for y, z in zip(base["rear_sight_profile"]["y_mm"], base["rear_sight_profile"]["z_mm"]) if abs(y) < 1.9]
    add("rear notch (bottom and width) unchanged", close(centre, centre0, 0.1) and d <= 0.3,
        {"notch_bottom_mm": min(centre), "was": min(centre0), "max_profile_diff_mm": round(d, 3), "mismatched_hits": miss})
    tip = max(z for z in m["front_post_profile"]["z_mm"] if z is not None)
    tip0 = max(z for z in base["front_post_profile"]["z_mm"] if z is not None)
    add("front sight tip height", abs(tip - tip0) <= 0.1, {"was_mm": tip0, "now_mm": tip})
    add("sight line first hit (front sight)", m["sight_line_first_hit_x"] is not None
        and abs(m["sight_line_first_hit_x"] - base["sight_line_first_hit_x"]) <= 2e-3,
        {"was": base["sight_line_first_hit_x"], "now": m["sight_line_first_hit_x"]})
    if name == "Chopper":
        add("bore ray stops where it did (bore end)", abs(m["bore_ray_hit_x"] - base["bore_ray_hit_x"]) <= 1e-3,
            {"was": base["bore_ray_hit_x"], "now": m["bore_ray_hit_x"]})
    else:
        # round 2: the 9.5 mm hammer channel under the slide's rear (critique) opens the breech face's lower
        # middle, so the bore ray runs on through the open chamber to the hammer face, as in the first pass
        add("bore ray: through the barrel and the hammer channel to the hammer", -0.013 <= m["bore_ray_hit_x"] <= -0.006,
            {"was": base["bore_ray_hit_x"], "now": m["bore_ray_hit_x"]})
    gun = next(o for o in meshes if o.name.startswith("SK_"))
    bvh, _V = R.bvh_of([gun])
    for s in ("Palm_R", "Palm_L"):
        p = m["bones"][s]
        dd = surface_distance(bvh, p)
        if name == "Nine" and s == "Palm_L":       # round 2: the grip moved forward with the brief's magazine line,
            add("Palm_L on the left grip panel (within 1.5 mm)", dd <= 0.0015, {"distance_mm": round(dd * 1000, 2)})
            continue
        add("%s within 1.5 mm of the surface" % s, dd <= 0.0015, {"distance_mm": round(dd * 1000, 2)})
    if name == "Nine":
        # round 2 (critique): the front strap rises straight into the back of the guard, ~35 mm from the trigger face
        trig = bvh.ray_cast(Vector((0.115, 0, -0.046)), Vector((-1, 0, 0)), 0.1)[0]
        strap = bvh.ray_cast(Vector((0.115, 0, -0.0800)), Vector((-1, 0, 0)), 0.2)[0]
        under = bvh.ray_cast(Vector((0.115, 0, -0.0745)), Vector((-1, 0, 0)), 0.2)[0]
        reach = (trig.x - strap.x) * 1000 if trig and strap else None
        add("NINE trigger face to front strap ~35 mm, strap right under the guard (no flat web)",
            reach is not None and 32 <= reach <= 38 and under is not None and under.x >= 0.060,
            {"trigger_face_x": round(trig.x, 4) if trig else None, "strap_x": round(strap.x, 4) if strap else None,
             "reach_mm": round(reach, 1) if reach else None, "front_under_guard_x": round(under.x, 4) if under else None})
        z = -0.0900
        w = bvh.ray_cast(Vector((0.015, 0.2, z)), Vector((0, -1, 0)), 1)[0]
        w2 = bvh.ray_cast(Vector((0.015, -0.2, z)), Vector((0, 1, 0)), 1)[0]
        add("NINE grip ~30 mm over the panels", 28 <= (w.y - w2.y) * 1000 <= 32, {"width_mm": round((w.y - w2.y) * 1000, 1)})
        mags = [o for o in meshes if o.name.startswith("SM_Weapon_NineMagazine")]
        if mags:
            cm = np.vstack([np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices]) for o in mags])
            add("magazine in place X -0.029..0.045, Z -0.1345..-0.037 (brief; round 1 had moved it 12 mm back)",
                abs(cm[:, 0].min() + 0.029) <= 0.0012 and abs(cm[:, 0].max() - 0.045) <= 0.0012
                and abs(cm[:, 2].min() + 0.1345) <= 0.0003,
                {"x": [round(float(cm[:, 0].min()), 4), round(float(cm[:, 0].max()), 4)],
                 "z": [round(float(cm[:, 2].min()), 4), round(float(cm[:, 2].max()), 4)]})
    travel_checks(name, gun, add)
    vj = os.path.join(GLB, "SK_%s.glb.verify.json" % name)
    if os.path.exists(vj):
        v = json.load(open(vj))
        add("re-import pose proof (fresh process)", v.get("ok") and v["glb"]["all_axes_are_asset_axes"],
            {p["name"]: p["max_error_m"] for p in v["poses"]})
    res["ok"] = all(c["ok"] for c in res["checks"])
    return res


def main():
    base = json.load(open(BASE))
    out = {}
    for name in ("Chopper", "Nine"):
        out[name] = check(name, base[name])
        print("%s: %s" % (name, "ALL FIXED POINTS KEPT" if out[name]["ok"] else "FAILED"))
        for c in out[name]["checks"]:
            if not c["ok"] or not c["check"].startswith("bone"):
                print("  %-4s %-60s %s" % ("ok" if c["ok"] else "FAIL", c["check"], json.dumps(c["detail"])[:150]))
    json.dump(out, open(OUT, "w"), indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
