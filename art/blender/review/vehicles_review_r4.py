"""Review round 4 of the exported vehicle GLBs: same loader, rig, cameras and measuring as round 3
(vehicles_review_r3.py, itself on vehicles_review.py), outputs redirected to sheets/vehicles_r4/.

    python art/blender/review/vehicles_review_r4.py --measure Sedan
    python art/blender/review/vehicles_review_r4.py --view Sedan 0
    python art/blender/review/vehicles_review_r4.py --compose Sedan
    python art/blender/review/vehicles_review_r4.py --close Sedan wheel      # wheel | lamp | door | interior
    python art/blender/review/vehicles_review_r4.py --close Sedan custom --cam x,y,z --target x,y,z --lens 35

One render per process (memory). run_vehicles_r4.sh drives the whole round sequentially.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import vehicles_review_r3 as R3  # noqa: E402

R3.OUT = os.path.join(HERE, "sheets", "vehicles_r4")
R3.TMP = os.path.join(R3.OUT, "_tmp")
R3.MEAS = os.path.join(R3.OUT, "measure.json")

import numpy as np  # noqa: E402

R = R3.R

# Translucency as the sets ask for it in Unreal (set.json notes); round 1-3 used 0.75 for every glass slot,
# which turned the car glass milky. Mirror glass is opaque silvered. A roughness_override (primer) wins over ORM.
GLASS_OPACITY = {"MI_Glass_CarTint": 0.45, "MI_Glass_LampClear": 0.25, "MI_Glass_LampAmber": 0.6,
                 "MI_Glass_LampRed": 0.6, "MI_Glass_Mirror": 1.0}
_build0 = R.build_material


def _build(rec, old):
    m = _build0(rec, old)
    nt = m.node_tree
    op = GLASS_OPACITY.get(rec.get("slot", ""))
    if op is not None:
        for n in nt.nodes:
            if n.type == "MIX_SHADER":
                n.inputs["Fac"].default_value = op
    if "roughness_override" in rec:
        bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        for lk in list(bs.inputs["Roughness"].links):
            nt.links.remove(lk)
        bs.inputs["Roughness"].default_value = float(rec["roughness_override"])
    return m


R.build_material = _build


def _slot(ob, arrs, *names):
    co, tris, pm, ls, lt, lv = arrs
    return R.slot_verts(ob, co, pm, ls, lt, lv, lambda n: any(k in n for k in names))


def _xclusters(p, gap=0.2, nmin=30):
    if not len(p):
        return []
    o = np.argsort(p[:, 0])
    out = []
    for g in np.split(o, np.where(np.diff(p[o, 0]) > gap)[0] + 1):
        q = p[g]
        if len(q) >= nmin:
            out.append(q)
    return out


def _tyre_islands(ob, arrs):
    """Vertices of the tyre-slot islands that are wheel shaped (x extent ~ z extent, touching the ground):
    the tyre material is also used for door and glass seals, which must not join the wheels."""
    co, tris, pm, ls, lt, lv = arrs
    idx = [i for i, ms in enumerate(ob.material_slots) if ms.material and "Tyre" in ms.material.name]
    sel = np.where(np.isin(pm, idx))[0]
    if not len(sel):
        return np.zeros((0, 3))
    par = {}

    def find(a):
        while par.setdefault(a, a) != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for p in sel:
        vs = lv[ls[p]:ls[p] + lt[p]]
        r0 = find(int(vs[0]))
        for v in vs[1:]:
            r = find(int(v))
            if r != r0:
                par[r] = r0
    groups = {}
    for v in list(par):
        groups.setdefault(find(v), []).append(v)
    keep = []
    zfloor = co[:, 2].min()
    for g in groups.values():
        q = co[g]
        ex = q.max(0) - q.min(0)
        if len(g) >= 20 and q[:, 2].min() < zfloor + 0.06 and 0.75 < ex[0] / max(ex[2], 1e-3) < 1.33:
            keep.extend(g)
    return co[keep] if keep else np.zeros((0, 3))


def wheels_r4(ob, arrs):
    """Wheels from the tyre slot alone (round-4 bodies put brakes, alloys and chrome trim on other slots), one
    cluster per axle on the -Y side; wrecks and the bike (no tyre slot) from their ground contacts."""
    co = arrs[0]
    t = _tyre_islands(ob, arrs)
    res = []
    if len(t):
        for q in _xclusters(t[t[:, 1] < 0]):
            res.append({"x": round(float((q[:, 0].min() + q[:, 0].max()) / 2), 3),
                        "dia_z": round(float(q[:, 2].max() - q[:, 2].min()), 3),
                        "len_x": round(float(q[:, 0].max() - q[:, 0].min()), 3),
                        "width_y": round(float(q[:, 1].max() - q[:, 1].min()), 3),
                        "zmin": round(float(q[:, 2].min()), 4), "src": "tyre"})
    else:
        low = co[co[:, 2] < co[:, 2].min() + 0.03]
        for q in _xclusters(low, gap=0.3, nmin=3):
            res.append({"x": round(float(np.median(q[:, 0])), 3), "zmin": round(float(q[:, 2].min()), 4),
                        "n": int(len(q)), "src": "ground contact"})
    return res


def anchors_r4(ob, arrs, wheels):
    co = arrs[0]
    lo, hi = co.min(0), co.max(0)
    a = {}
    tw = [w for w in wheels if w.get("src") == "tyre"]
    if tw:
        w = max(tw, key=lambda w: w["x"])
        a["wheel"] = [w["x"], float(lo[1]), w["zmin"] + w["dia_z"] / 2]
        a["wheel_dia"] = w["dia_z"]
    lp = _slot(ob, arrs, "MI_Glass_LampClear")
    if len(lp):
        f = lp[(lp[:, 0] > hi[0] - 0.9) & (lp[:, 1] < 0)]
        if len(f):
            a["lamp"] = [float(f[:, 0].max()), float(np.median(f[:, 1])), float(np.median(f[:, 2]))]
    mp = _slot(ob, arrs, "MI_Glass_Mirror")
    if len(mp):
        m = mp[mp[:, 1] < 0]
        if len(m):
            a["mirror"] = [float(np.median(m[:, 0])), float(m[:, 1].min()), float(np.median(m[:, 2]))]
    gp = _slot(ob, arrs, "MI_Glass_CarTint")
    if len(gp):
        g = gp[gp[:, 1] > 0.9 * gp[:, 1].max()]
        if len(g):
            xf = g[:, 0].max()
            gf = g[g[:, 0] > xf - 0.7]
            a["driver_glass"] = [float(np.median(gf[:, 0])), float(gf[:, 1].max()), float(np.median(gf[:, 2]))]
    return a


_measure0 = R.measure


def _measure(name, obs, man, brief):
    m = _measure0(name, obs, man, brief)
    arrs = R.mesh_arrays(obs[0])
    w = wheels_r4(obs[0], arrs)
    m["wheels_r4"] = w
    xs = sorted(x["x"] for x in w)
    if len(xs) >= 2:
        m["wheelbase_r4"] = round(xs[-1] - xs[0], 3)
    m["anchors_r4"] = anchors_r4(obs[0], arrs, w)
    return m


R.measure = _measure
_anchors0 = R3.anchors


def _anchors(ob):
    a = _anchors0(ob)
    arrs = R.mesh_arrays(ob)
    a.update(anchors_r4(ob, arrs, wheels_r4(ob, arrs)))
    return a


R3.anchors = _anchors

# round-4 hand anchors where the slot rules cannot see a part (filled after the measuring pass)
R3.ANCHOR_FIX = {
    "BurnedCar": {"wheel": [1.42, -0.86, 0.21], "lamp": [2.15, -0.58, 0.60], "driver_glass": [0.35, 0.86, 1.00]},
    "StrippedCar": {"wheel": [1.42, -0.86, 0.47], "lamp": [2.15, -0.58, 0.78], "driver_glass": [0.35, 0.86, 1.25]},
    "Motorbike": {"wheel": [0.69, -0.31, 0.31]},
}

if __name__ == "__main__":
    R3.main()
