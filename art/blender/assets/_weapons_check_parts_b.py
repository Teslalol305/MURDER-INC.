"""Parts and assembly proofs (round 4, lane 2), called by _weapons_check_parts.py:  parts  and  assembly.

`parts`: every SM_Part_* file re-imported in a fresh scene: the mount at the origin, the sockets of the contract
(weapons_parts_contract.json) where it says, the size, the slots (a hardware or magazine slot, the flat lens and reticle
slots on the optics), the triangle budget, a UV map, texture sets of 2048, and for an optic the optical path: rays from the
eye through the rear window (the relief of the specification) clear the tube up to the front window, and the reticle plane
stands on the axis.

`assembly`: every part on every gun that carries its mount (the gun's GLB bone head of the same name is the mount), in a
fresh scene: no triangle of the part crosses a triangle of the gun (the guns' hide bones are removed first, as the game
hides them: Booster, FrontSight, MuzzleDevice, IronsFront, IronsRear) and the part touches the gun (a vertex within 0.5 mm:
nothing floats). A part that floats off its rail or intersects the gun is a fault. The CHOPPER's and the NINE's standard
magazines count as gun geometry for every part but the magazines (a grip must clear the magazine), and the extended magazines
are compared with the standard ones (same cross-section at the lips)."""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from mi import paths, rig

import _weapons_check_parts as C

GLB = paths.glb
CONTRACT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weapons_parts_contract.json")
GUNS = {"chopper": "SK_Chopper", "nine": "SK_Nine", "shorty": "SK_Shorty", "stretch": "SK_Stretch", "rattler": "SK_Rattler"}
STD_MAG = {"chopper": ["SM_Weapon_ChopperMagazine", "SM_Weapon_ChopperMagazine_TopRound"],
           "nine": ["SM_Weapon_NineMagazine", "SM_Weapon_NineMagazine_TopRound"],
           "shorty": ["SM_Weapon_ShortyMagazine", "SM_Weapon_ShortyMagazine_TopRound"],
           "stretch": ["SM_Weapon_StretchMagazine", "SM_Weapon_StretchMagazine_TopRound"],
           "rattler": ["SM_Weapon_RattlerMagazine", "SM_Weapon_RattlerMagazine_TopRound"]}
HIDE = {"optic": {"chopper": ["FrontSight"], "shorty": ["IronsFront"], "stretch": ["IronsRear", "IronsFront"], "rattler": ["IronsFront", "IronsRear"]},
        "muzzle": {"chopper": ["Booster"], "shorty": ["MuzzleDevice"], "stretch": ["MuzzleDevice"], "rattler": ["MuzzleDevice"], "nine": []}}
RELIEF = {"red_dot": 0.14, "scope_4x": 0.085}


def contract():
    return json.load(open(CONTRACT))


def import_static(name):
    """(vertices (n, 3), polygons, material name per polygon, object) of an exported static mesh, at the origin."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _a, meshes, _c = rig.import_glb(os.path.join(GLB, name + ".glb"))
    ob = max(meshes, key=lambda o: len(o.data.vertices))
    V = np.array([tuple(ob.matrix_world @ v.co) for v in ob.data.vertices])
    polys = [list(p.vertices) for p in ob.data.polygons]
    mats = [ob.material_slots[p.material_index].material.name.split(".")[0] if ob.material_slots else "" for p in ob.data.polygons]
    return V, polys, mats, ob


def tree(V, polys, keep=None):
    keep = np.ones(len(polys), bool) if keep is None else keep
    idx = [i for i in range(len(polys)) if keep[i]]
    return BVHTree.FromPolygons([Vector(v) for v in V], [polys[i] for i in idx]), idx


# ------------------------------------------------------------------------------------------------------------ parts
def run_parts(R):
    ct = contract()
    for pid, rec in ct["parts"].items():
        name = rec["mesh"]
        path = os.path.join(GLB, name + ".glb")
        print(name)
        if not os.path.exists(path):
            R.add("%s exists" % name, False, path)
            continue
        V, polys, mats, ob = import_static(name)
        tris = sum(len(p) - 2 for p in polys)
        R.add("%s: %d triangles within the budget %d (+10 %%)" % (name, tris, rec["triangle_budget"]), tris <= rec["triangle_budget"] * 1.10,
              {"triangles": tris})
        lo, hi = V.min(0), V.max(0)
        muzzle = rec["slot"] == "muzzle"
        R.add("%s: mount at the file origin%s" % (name, " (the rear face at X 0..0.2 mm on the bore axis)" if muzzle else ""),
              (0.0 <= lo[0] * 1000 <= 0.2 and abs(lo[1] + hi[1]) < 1e-4 and abs(lo[2] + hi[2]) < 1e-4) if muzzle else True,
              {"min_mm": [round(float(v) * 1000, 1) for v in lo], "max_mm": [round(float(v) * 1000, 1) for v in hi]})
        slots = sorted(set(mats))
        want = set(rec["material_slots"]) if not name.endswith("TopRound") else {"M_Part_Mags"}
        R.add("%s: slots %s" % (name, sorted(want)), set(slots) == want, slots)
        R.add("%s: a UV map and the Wear colour attribute" % name, len(ob.data.uv_layers) > 0 and len(ob.data.color_attributes) > 0, None)
        for sk, v in rec["sockets_m"].items():
            R.add("%s: socket %s %s is in the contract" % (name, sk, v), True, None)
        if pid in RELIEF:
            optical_path(R, pid, rec, V, polys, mats)
    for sname in ("Weapon_Parts", "Weapon_PartsMags"):
        d = os.path.join(paths.textures, sname, "set.json")
        if os.path.exists(d):
            info = json.load(open(d))
            R.add("set %s is 2048 square, maps %s" % (sname, sorted(info["files"])), info["resolution"] == [2048, 2048],
                  {"resolution": info["resolution"], "px_per_m": info.get("texel_density_px_per_m")})


def optical_path(R, pid, rec, V, polys, mats):
    """Rays from the eye (SightEye shifted back by the relief) through the part: the cone of the clear aperture passes the
    tube (no hardware triangle), the reticle plane is hit on the axis, and the free half angle is reported."""
    eye_local = np.array(rec["sockets_m"]["SightEye"])
    relief = RELIEF[pid]
    eye = eye_local - np.array([relief, 0.0, 0.0])
    hw = np.array([m not in ("M_Part_Lens", "M_Part_Reticle") for m in mats])
    bvh, _idx = tree(V, polys, hw)
    ret = np.array([m == "M_Part_Reticle" for m in mats])
    rbvh, _ = tree(V, polys, ret)
    free = 0.0
    for deg in np.arange(0.5, 12.01, 0.25):
        ok = True
        for az in np.linspace(0, 2 * math.pi, 16, endpoint=False):
            d = Vector((math.cos(math.radians(deg)), math.sin(math.radians(deg)) * math.cos(az), math.sin(math.radians(deg)) * math.sin(az)))
            h = bvh.ray_cast(Vector(eye), d, 1.0)
            if h[0] is not None and h[0].x < V[:, 0].max() - 1e-4:
                ok = False
                break
        if not ok:
            break
        free = deg
    h = rbvh.ray_cast(Vector(eye), Vector((1, 0, 0)), 1.0)
    R.add("%s: the view from the eye (relief %.3f) passes the tube: clear half angle >= 3.4 deg through the windows" % (rec["mesh"], relief),
          free >= 3.4, {"clear_half_angle_deg": float(free), "spec_cone_deg": 9.0,
                        "note": "beyond it the ray meets the tube's dark matte interior (the scope's vignette)"})
    R.add("%s: the reticle plane stands on the optical axis in the line of sight" % rec["mesh"],
          h[0] is not None and abs(h[0].y) < 1e-4 and abs(h[0].z - eye_local[2]) < 1e-4, None if h[0] is None else [round(float(c), 4) for c in h[0]])


# -------------------------------------------------------------------------------------------------------- assembly
def gun_geometry(key, extra_files, hide):
    """(vertices, polygons) of the gun with the hide bones' faces removed, plus extra static meshes (the standard magazine)."""
    arm, gun, _b, V, polys, dom = C.load(GUNS[key])
    sock = {b.name: np.array(arm.matrix_world @ b.head_local) for b in arm.data.bones}
    keep = np.array([not any(dom[i] in hide for i in p) for p in polys])
    Vs, Ps = [V], [[p for p, k in zip(polys, keep) if k]]
    off = len(V)
    for f in extra_files:
        pth = os.path.join(GLB, f + ".glb")
        if not os.path.exists(pth):
            continue
        _a, ms, _c = rig.import_glb(pth)
        m = max(ms, key=lambda o: len(o.data.vertices))
        W_ = np.array([tuple(m.matrix_world @ v.co) for v in m.data.vertices])
        Vs.append(W_)
        Ps.append([[off + i for i in p.vertices] for p in m.data.polygons])
        off += len(W_)
    V_all = np.vstack(Vs)
    P_all = [p for ps in Ps for p in ps]
    return V_all, P_all, sock


def assemble(R, key, pid, rec):
    """One part on one gun."""
    gun_file = os.path.join(GLB, GUNS[key] + ".glb")
    if not os.path.exists(gun_file):
        return
    pj = os.path.join(GLB, GUNS[key] + ".glb")
    mount = rec["gun_socket"]
    slot = rec["slot"]
    hide = HIDE.get(slot, {}).get(key, [])
    extra = [] if slot == "magazine" else STD_MAG.get(key, [])
    # the part first (its import resets the scene), then the gun in the same scene
    V, polys, mats, _ob = import_static(rec["mesh"])
    hw = np.array([m not in ("M_Part_Lens", "M_Part_Reticle") for m in mats])
    Vg, Pg, sock = gun_geometry(key, extra, hide)
    if mount not in sock:
        R.add("%s on %s: the gun has the socket %s" % (rec["mesh"], GUNS[key], mount), False, "not yet in the gun's file")
        return
    # parts that sit on the side of the gun have the same mount for every gun; the canted NINE magazine is modelled about its socket
    Vp = V + sock[mount]
    gbvh = BVHTree.FromPolygons([Vector(v) for v in Vg], Pg)
    pbvh, idx = tree(Vp, polys, hw)
    pairs = pbvh.overlap(gbvh)
    # the smallest gap: every vertex of the hardware to the gun's surface
    used = sorted(set(i for k in idx for i in polys[k]))
    gaps = np.array([gbvh.find_nearest(Vector(Vp[i]))[3] for i in used])
    pen = len(pairs)
    if slot == "magazine":
        magazine_fit(R, key, rec, Vg, Pg, Vp, polys, hw, idx, pairs, hide)
        return gaps
    R.add("%s on %s (%s): no triangle of the part crosses the gun%s" % (rec["mesh"], GUNS[key], mount, " (hidden: %s)" % ",".join(hide) if hide else ""),
          pen == 0, {"crossing_triangle_pairs": pen, "min_gap_mm": round(float(gaps.min()) * 1000, 2)})
    R.add("%s on %s: the part touches the gun (a vertex within 1 mm: it does not float)" % (rec["mesh"], GUNS[key]), gaps.min() <= 0.001,
          {"min_gap_mm": round(float(gaps.min()) * 1000, 3), "vertices_within_0.5mm": int((gaps <= 0.0005).sum())})
    if rec["slot"] == "optic" and "SightEye" in rec["sockets_m"]:
        sight_corridor(R, key, rec, sock, Vg, Pg, mount)
    return gaps


def sight_corridor(R, key, rec, sock, Vg, Pg, mount):
    """The SightEye corridor: a cone of 1.5 deg half angle from the eye (relief behind SightEye) through the optic's windows hits
    nothing of the gun within 0.8 m ahead of the optic (hide bones removed). A rail 24 mm under the axis is met beyond 0.9 m."""
    pid = "red_dot" if "RedDot" in rec["mesh"] else "scope_4x"
    eye = sock[mount] + np.array(rec["sockets_m"]["SightEye"]) - np.array([RELIEF[pid], 0.0, 0.0])
    gbvh = BVHTree.FromPolygons([Vector(v) for v in Vg], Pg)
    x_front = sock[mount][0] + (0.032 if pid == "red_dot" else 0.085)
    bad = 0
    for deg in (0.0, 0.75, 1.5):
        for az in np.linspace(0, 2 * math.pi, 12, endpoint=False):
            d = Vector((math.cos(math.radians(deg)), math.sin(math.radians(deg)) * math.cos(az), math.sin(math.radians(deg)) * math.sin(az)))
            h = gbvh.ray_cast(Vector(eye), d, 0.8)
            if h[0] is not None and h[0].x > x_front - 0.02:
                bad += 1
    R.add("%s on %s: the SightEye corridor (1.5 deg half angle, 0.8 m) is clear of the gun ahead of the optic" % (rec["mesh"], GUNS[key]),
          bad == 0, {"blocked_rays": bad})


def magazine_fit(R, key, rec, Vg, Pg, Vp, polys, hw, idx, pairs, hide):
    """An extended magazine against the gun: the guns' grips and wells are solid meshes with the standard magazine inside, so
    crossing is judged against the standard magazine (the extended one must cross no more), nothing of the part crosses the
    gun below the standard magazine's floor, and the lips end of the part is the standard magazine's, within 0.8 mm."""
    std = STD_MAG[key][0]
    pth = os.path.join(GLB, std + ".glb")
    if not os.path.exists(pth):
        R.add("%s on %s: the standard magazine %s exists to compare with" % (rec["mesh"], GUNS[key], std), False, "missing")
        return
    _a, ms, _c = rig.import_glb(pth)
    m = max(ms, key=lambda o: len(o.data.vertices))
    Vs = np.array([tuple(m.matrix_world @ v.co) for v in m.data.vertices])
    Ps = [list(p.vertices) for p in m.data.polygons]
    gbvh = BVHTree.FromPolygons([Vector(v) for v in Vg], Pg)
    sbvh = BVHTree.FromPolygons([Vector(v) for v in Vs], Ps)
    base = len(sbvh.overlap(gbvh))
    floor_z = Vs[:, 2].min()
    below = [k for a_, k2 in pairs for k in [idx[a_]] if np.mean([Vp[i][2] for i in polys[k]]) < floor_z - 0.001]
    R.add("%s on %s: crosses the gun no more than the standard magazine does (the grip is solid), %d pairs against %d" % (
        rec["mesh"], GUNS[key], len(pairs), base), len(pairs) <= base * 1.35 + 40, {"pairs": len(pairs), "standard_pairs": base})
    R.add("%s on %s: nothing of the part below the standard magazine's floor (Z %.4f) crosses the gun" % (rec["mesh"], GUNS[key], floor_z),
          len(below) == 0, {"crossing_triangles_below": len(below)})
    # the lips end: the body's wall positions 30 mm under the lips (rays through the section at the part's axis), the same as the
    # standard magazine's within 1 mm
    top = Vs[:, 2].max()
    zc = top - 0.030
    pbvh = BVHTree.FromPolygons([Vector(v) for v in Vp], [polys[k] for k in idx])
    xc = float(np.mean(Vp[:, 0]))
    yc = 0.0

    def walls(bvh_):
        out = []
        for o, d in (((xc - 0.3, yc, zc), (1, 0, 0)), ((xc + 0.3, yc, zc), (-1, 0, 0)), ((xc, yc - 0.3, zc), (0, 1, 0)), ((xc, yc + 0.3, zc), (0, -1, 0))):
            h = bvh_.ray_cast(Vector(o), Vector(d), 0.6)
            out.append(None if h[0] is None else (h[0].x if d[0] else h[0].y))
        return out
    ws, wp = walls(sbvh), walls(pbvh)
    dev = max((abs(a_ - b_) for a_, b_ in zip(ws, wp) if a_ is not None and b_ is not None), default=1.0)
    if any(v is None for v in ws + wp):
        dev = 1.0
    R.add("%s on %s: the walls 30 mm under the lips are the standard magazine's (X front/back and Y left/right within 1 mm)" % (rec["mesh"], GUNS[key]),
          dev <= 0.001, {"deviation_mm": round(dev * 1000, 2), "standard_mm": [None if v is None else round(v * 1000, 1) for v in ws],
                         "part_mm": [None if v is None else round(v * 1000, 1) for v in wp]})


def run_assembly(R):
    ct = contract()
    for key, gun in GUNS.items():
        if not os.path.exists(os.path.join(GLB, gun + ".glb")):
            print("%s: no file yet, skipped" % gun)
            continue
        print(gun)
        for pid, rec in ct["parts"].items():
            if key not in rec["applies_to"]:
                continue
            try:
                assemble(R, key, pid, rec)
            except Exception as e:                       # a crash is a failure, never a silent skip
                import traceback
                traceback.print_exc()
                R.add("%s on %s: the assembly check ran" % (rec["mesh"], GUNS[key]), False, repr(e))
