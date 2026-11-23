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
        add("bore ray stops at the closed breech face (was: the hammer)", 0.0 <= m["bore_ray_hit_x"] <= 0.006,
            {"was": base["bore_ray_hit_x"], "now": m["bore_ray_hit_x"]})
    gun = next(o for o in meshes if o.name.startswith("SK_"))
    bvh, _V = R.bvh_of([gun])
    for s in ("Palm_R", "Palm_L"):
        p = m["bones"][s]
        dd = surface_distance(bvh, p)
        if name == "Nine" and s == "Palm_L":       # the support hand wraps over the firing hand's fingers (brief)
            add("Palm_L ahead of the front strap, over the fingers (not on the gun)", 0.002 <= dd <= 0.025,
                {"distance_mm": round(dd * 1000, 2)})
            continue
        add("%s within 1.5 mm of the surface" % s, dd <= 0.0015, {"distance_mm": round(dd * 1000, 2)})
    if name == "Nine":
        z = -0.0815
        f = bvh.ray_cast(Vector((0.2, 0, z)), Vector((-1, 0, 0)), 1)[0]
        b = bvh.ray_cast(Vector((-0.2, 0, z)), Vector((1, 0, 0)), 1)[0]
        w = bvh.ray_cast(Vector((0.005, 0.2, z)), Vector((0, -1, 0)), 1)[0]
        w2 = bvh.ray_cast(Vector((0.005, -0.2, z)), Vector((0, 1, 0)), 1)[0]
        depth = (f.x - b.x) * 1000
        add("NINE grip at mid height ~52 mm deep across the rake, ~30 mm wide",
            50 <= depth * 0.968 <= 55 and 28 <= (w.y - w2.y) * 1000 <= 32,
            {"horizontal_mm": round(depth, 1), "across_rake_mm": round(depth * 0.968, 1),
             "width_mm": round((w.y - w2.y) * 1000, 1), "was_horizontal_mm": 72})
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
