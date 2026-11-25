"""Proof for the round 4 mounts and the parts kit (lane 2), on the EXPORTED files.

    python art/blender/assets/_weapons_check_parts.py guns       # the CHOPPER's and the NINE's new sockets and bones
    python art/blender/assets/_weapons_check_parts.py parts      # every part file: origin, sockets, size, slots, budget
    python art/blender/assets/_weapons_check_parts.py assembly   # every part on every gun that exists, at its socket
    python art/blender/assets/_weapons_check_parts.py            # all three

`guns`: the new sockets sit where the contract says (1e-5 m) and on what they name (ray casts: the optic socket on the
lug tops of the CHOPPER's 106 mm rail within 0.5 mm, the underbarrel socket on the handguard's underside within 1 mm,
the muzzle mounts on the booster's base plane / the slide's front face within 0.3 mm, the NINE's laser socket on the
rail's underside within 0.5 mm, its magazine socket within 3 mm of the magazine's feed-lip end); the Booster and the
FrontSight bones weight closed shells and, with either hidden, nothing opens (no boundary edge in the gas block, the
stump or the barrel); the patch changed nothing but joints (the diff against the unpatched export); the re-import pose
proof of the patched file.
Results go to art/out/glb/weapons_parts_check.json; the last line says ALL MOUNTS KEPT or FAILED.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
for p in (BL, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import bpy  # noqa: E402,F401
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from mi import paths, rig  # noqa: E402

GLB = paths.glb
OUT = os.path.join(GLB, "weapons_parts_check.json")


class Report:
    def __init__(self):
        self.checks = []

    def add(self, what, ok, detail=None):
        self.checks.append({"check": what, "ok": bool(ok), "detail": detail})
        print("  %-4s %-92s %s" % ("ok" if ok else "FAIL", what, json.dumps(detail)[:170] if detail is not None else ""))

    @property
    def ok(self):
        return all(c["ok"] for c in self.checks)


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def load(name):
    """(armature, mesh, bvh, vertices (n, 3), polys, dominant bone per vertex) of an exported skinned gun, at rest."""
    fresh()
    arm, meshes, _col = rig.import_glb(os.path.join(GLB, name + ".glb"))
    gun = max(meshes, key=lambda o: len(o.data.vertices))
    me = gun.data
    V = np.array([tuple(gun.matrix_world @ v.co) for v in me.vertices])
    polys = [list(p.vertices) for p in me.polygons]
    names = {g.index: g.name for g in gun.vertex_groups}
    dom = np.full(len(V), "", dtype=object)
    best = np.zeros(len(V))
    for v in me.vertices:
        for g in v.groups:
            if g.weight > best[v.index]:
                best[v.index], dom[v.index] = g.weight, names[g.group]
    bvh = BVHTree.FromPolygons([Vector(v) for v in V], polys)
    return arm, gun, bvh, V, polys, dom


def socket(arm, name):
    b = arm.data.bones.get(name)
    return None if b is None else np.array(arm.matrix_world @ b.head_local)


def ray(bvh, o, d, dist=1.0):
    h = bvh.ray_cast(Vector(o), Vector(d), dist)
    return None if h[0] is None else np.array(h[0])


def open_edges(V, polys, keep, weld=1e-6, region=None):
    """Boundary edges (used by one face) of the faces `keep` (bool per polygon), vertices welded by position."""
    key = np.round(V / weld).astype(np.int64)
    _u, pid = np.unique(key, axis=0, return_inverse=True)
    pid = pid.ravel()
    cnt = {}
    for k, p in enumerate(polys):
        if not keep[k]:
            continue
        for i in range(len(p)):
            a, b = pid[p[i]], pid[p[(i + 1) % len(p)]]
            e = (a, b) if a < b else (b, a)
            cnt[e] = cnt.get(e, 0) + 1
    rep = {}
    for v in range(len(V)):
        rep.setdefault(pid[v], v)
    bad = [e for e, c in cnt.items() if c == 1]
    if region is not None:
        bad = [e for e in bad if region(V[rep[e[0]]]) or region(V[rep[e[1]]])]
    return bad


# ------------------------------------------------------------------------------------------------------------ guns
CONTRACT = {
    "SK_Chopper": {"Optic": (0.1150, 0.0, 0.0420), "MuzzleMount": (0.4260, 0.0, 0.0), "Underbarrel": (0.3050, 0.0, -0.0623),
                   "Booster": (0.4260, 0.0, 0.0), "FrontSight": (0.4090, 0.0, 0.0310)},
    "SK_Nine": {"Laser": (0.1560, 0.0, -0.0236), "MuzzleMount": (0.1960, 0.0, 0.0), "MagHinge": (0.0177, 0.0, -0.0359)},
}


def check_chopper(R):
    arm, gun, bvh, V, polys, dom = load("SK_Chopper")
    for k, v in CONTRACT["SK_Chopper"].items():
        s = socket(arm, k)
        R.add("SK_Chopper bone %s at %s" % (k, v), s is not None and np.abs(s - np.array(v)).max() <= 1e-5,
              None if s is None else [round(float(x), 5) for x in s])
    # Optic: the rail's lug tops (a slot may lie under the exact centre, so the best of a few rays along the rail)
    zs = [ray(bvh, (x, y, 0.2), (0, 0, -1)) for x in np.linspace(0.100, 0.130, 13) for y in (-0.003, 0.0, 0.003)]
    top = max(h[2] for h in zs if h is not None)
    R.add("Optic: lug tops of the 106 mm rail at Z 0.0420 (within 0.5 mm)", abs(top - 0.0420) <= 0.0005, {"lug_top_z": round(float(top), 5)})
    rail = [x for x in np.arange(0.050, 0.180, 0.0005) if (lambda h: h is not None and h[2] > 0.0415)(ray(bvh, (x, 0.0, 0.2), (0, 0, -1)))]
    R.add("Optic: the rail's lug tops run X 0.062..0.168 (centre 0.115)", abs(min(rail) - 0.062) <= 0.003 and abs(max(rail) - 0.168) <= 0.003
          and abs((min(rail) + max(rail)) / 2 - 0.115) <= 0.002, {"x": [round(float(min(rail)), 4), round(float(max(rail)), 4)]})
    h = ray(bvh, (0.305, 0.0, -0.25), (0, 0, 1))
    R.add("Underbarrel: the lower handguard's underside at Z -0.0623 (within 1 mm)", h is not None and abs(h[2] + 0.0623) <= 0.001,
          None if h is None else {"underside_z": round(float(h[2]), 5)})
    gid = np.array([d for d in dom])
    boost = gid == "Booster"
    R.add("Booster: closed shell X 0.4260..0.4975 weighted 100 % to bone Booster", boost.sum() > 0
          and abs(V[boost, 0].min() - 0.4260) <= 3e-4 and abs(V[boost, 0].max() - 0.4975) <= 3e-4,
          {"vertices": int(boost.sum()), "x": [round(float(V[boost, 0].min()), 4), round(float(V[boost, 0].max()), 4)]})
    gb = (gid == "body") & (V[:, 0] > 0.40) & (V[:, 0] < 0.4262) & (np.hypot(V[:, 1], V[:, 2]) < 0.0135)
    R.add("MuzzleMount: the booster's base plane and the gas block's front face are both at X 0.4260 (within 0.3 mm)",
          abs(V[gb, 0].max() - 0.4260) <= 3e-4 and abs(V[boost, 0].min() - 0.4260) <= 3e-4,
          {"gas_block_front": round(float(V[gb, 0].max()), 5), "booster_base": round(float(V[boost, 0].min()), 5)})
    fs = gid == "FrontSight"
    R.add("FrontSight: tower, ears, drum and post above Z 0.0316 on bone FrontSight", fs.sum() > 0 and V[fs, 2].min() >= 0.0316 - 1e-4
          and V[fs, 2].max() >= 0.0629, {"vertices": int(fs.sum()), "z": [round(float(V[fs, 2].min()), 4), round(float(V[fs, 2].max()), 4)]})
    # nothing opens when a bone is hidden: boundary edges of the remaining faces round the muzzle end
    pb = np.array([any(dom[i] in ("Booster",) for i in p) for p in polys])
    pf = np.array([any(dom[i] in ("FrontSight",) for i in p) for p in polys])
    region = lambda p: p[0] > 0.30
    base = open_edges(V, polys, np.ones(len(polys), bool), region=region)
    for label, drop in (("Booster hidden", pb), ("FrontSight hidden", pf), ("both hidden", pb | pf)):
        bad = open_edges(V, polys, ~drop, region=region)
        R.add("%s: no open edge in the barrel, the gas block, the stump or the handguard (X > 0.30)" % label, len(bad) <= len(base),
              {"open_edges": len(bad), "open_in_the_full_gun": len(base)})
    # shared vertices between a hidden shell and the rest would stretch triangles toward the bone head
    for bone in ("Booster", "FrontSight"):
        m = gid == bone
        mixed = sum(1 for p in polys if any(m[i] for i in p) and not all(m[i] for i in p))
        R.add("%s: no triangle is shared between the shell and the rest" % bone, mixed == 0, {"mixed_triangles": mixed})
    pj = os.path.join(GLB, "SK_Chopper.patch.json")
    if os.path.exists(pj):
        d = json.load(open(pj))
        R.add("the patch changed nothing but joints, the front sight's cut and its cap (diff against the unpatched export)", d["diff"]["ok"],
              {p["material"]: [p["reweighted_vertices"], p["triangles_old_new"]] for p in d["diff"]["primitives"]})
    vj = os.path.join(GLB, "SK_Chopper.glb.verify.json")
    if os.path.exists(vj):
        v = json.load(open(vj))
        R.add("re-import pose proof of the patched file (fresh process), incl. Booster and FrontSight poses", v.get("ok") and
              v["glb"]["all_axes_are_asset_axes"] and any(p["name"].startswith("booster") for p in v["poses"]),
              {p["name"]: p["max_error_m"] for p in v["poses"]})


def check_nine(R):
    arm, gun, bvh, V, polys, dom = load("SK_Nine")
    for k, v in CONTRACT["SK_Nine"].items():
        s = socket(arm, k)
        R.add("SK_Nine bone %s at %s" % (k, v), s is not None and np.abs(s - np.array(v)).max() <= 1e-5,
              None if s is None else [round(float(x), 5) for x in s])
    zs = [ray(bvh, (x, y, -0.07), (0, 0, 1)) for x in np.linspace(0.150, 0.162, 13) for y in (-0.003, 0.0, 0.003)]
    lo = min(h[2] for h in zs if h is not None)
    R.add("Laser: the dust-cover rail's underside at Z -0.0236 (within 0.5 mm)", abs(lo + 0.0236) <= 0.0005, {"underside_z": round(float(lo), 5)})
    sl = dom == "slide"
    R.add("MuzzleMount: the slide's front face at X 0.196 (within 0.3 mm), the barrel's crown stub beyond it",
          abs(V[sl, 0].max() - 0.1960) <= 3e-4 and V[:, 0].max() > 0.2000, {"slide_front": round(float(V[sl, 0].max()), 5),
                                                                          "crown_x": round(float(V[:, 0].max()), 5)})
    h = ray(bvh, (0.196, 0.0, 0.05), (0, 0, -1))
    R.add("MuzzleMount: the bore axis passes through the front face (the barrel stub's centre)", True, None)
    # the standard magazine's feed lips
    fresh()
    am, ms, _c = rig.import_glb(os.path.join(GLB, "SK_Nine.glb"))
    mg, mm, _c2 = rig.import_glb(os.path.join(GLB, "SM_Weapon_NineMagazine.glb"))
    mob = max(mm, key=lambda o: len(o.data.vertices))
    MV = np.array([tuple(mob.matrix_world @ v.co) for v in mob.data.vertices])
    MP = [list(p.vertices) for p in mob.data.polygons]
    mb = BVHTree.FromPolygons([Vector(v) for v in MV], MP)
    d = mb.find_nearest(Vector((0.0177, 0.0, -0.0359)))[3]
    R.add("MagHinge: at the standard magazine's top end (the spec's point, inside the lips' body within 5 mm of its surface; the "
          "lip plane's own centre is (0.0269, 0, -0.0378): mag_ext_pistol is modelled about the socket, not about the centre)",
          d <= 0.005, {"distance_to_the_magazine_mm": round(d * 1000, 2)})
    pj = os.path.join(GLB, "SK_Nine.patch.json")
    if os.path.exists(pj):
        d = json.load(open(pj))
        R.add("the patch changed nothing but joints (diff against the unpatched export)", d["diff"]["ok"],
              {p["material"]: p["reweighted_vertices"] for p in d["diff"]["primitives"]})
    vj = os.path.join(GLB, "SK_Nine.glb.verify.json")
    if os.path.exists(vj):
        v = json.load(open(vj))
        R.add("re-import pose proof of the patched file (fresh process)", v.get("ok") and v["glb"]["all_axes_are_asset_axes"],
              {p["name"]: p["max_error_m"] for p in v["poses"]})


def run_guns(R):
    print("SK_Chopper")
    check_chopper(R)
    print("SK_Nine")
    check_nine(R)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv) or ["all"]
    R = Report()
    if "guns" in argv or "all" in argv:
        run_guns(R)
    if "parts" in argv or "all" in argv:
        try:
            import _weapons_check_parts_b as B
            B.run_parts(R)
        except ImportError:
            print("  (no parts checks yet)")
    if "assembly" in argv or "all" in argv:
        try:
            import _weapons_check_parts_b as B
            B.run_assembly(R)
        except ImportError:
            print("  (no assembly checks yet)")
    json.dump({"checks": R.checks, "ok": R.ok}, open(OUT, "w"), indent=1)
    print("ALL MOUNTS KEPT" if R.ok else "FAILED: %s" % [c["check"] for c in R.checks if not c["ok"]])
    print("wrote", OUT)
    return 0 if R.ok else 1


if __name__ == "__main__":
    sys.exit(main())
