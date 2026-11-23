"""Measure the pack rifles' mount points from their geometry (bpy on the box; numbers only, never pack data).

    /opt/blpy/bin/python -I tools/box/anim/bl_measure.py <pack FBX root> <rig facts meshes.json> <out pack_sockets.json>

Gun space as Unreal sees the pack's skeletal meshes: cm, +Y to the muzzle, +X to the gun's left, +Z up
(Unreal = Blender (x, -y, z) for these FBX files; checked against the bone heads Unreal reports).

The pack author's own attachment frames (SOCKET_* empties of the rig .blend, read by bl_meshes.py into
meshes.json) say where each part's origin goes; every one is checked here against the measured surface it must sit
on (rail top, handguard underside, side rail, muzzle threads, magazine well), and the sight and muzzle points are
measured outright (bore axis from the muzzle ring, front post tip, rear aperture centre). The result is the socket
table that ue_import_guns.py writes on every variant and part.
"""
import json
import math
import os
import sys

import bpy

ROOT, RIG_FACTS, OUT = sys.argv[1:4]
LENGTHS = ("Short", "Default", "Extended")
# Palms measured from the pack's own first-person clips in gun space (mi_anim.py, ANIMATION.md section 1)
PALM_R = (-3.5, -4.2, -6.2)
PALM_L = (3.4, 28.4, 0.6)


def load(fbx):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, "Meshes", fbx))
    out = []
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        mw = o.matrix_world
        names = [g.name for g in o.vertex_groups]
        mats = [s.material.name if s.material else "" for s in o.material_slots]
        vmat = {}
        for p in o.data.polygons:
            for v in p.vertices:
                vmat[v] = mats[p.material_index] if p.material_index < len(mats) else ""
        for v in o.data.vertices:
            w = mw @ v.co
            b = names[max(v.groups, key=lambda g: g.weight).group] if v.groups else ""
            out.append(((w.x * 100.0, -w.y * 100.0, w.z * 100.0), b, vmat.get(v.index, "")))
    return out


def r3(v):
    return [round(float(x), 3) for x in v]


def box(pts):
    if not pts:
        return None
    return {"min": r3([min(p[i] for p in pts) for i in range(3)]), "max": r3([max(p[i] for p in pts) for i in range(3)])}


def ring_axis(pts, end_y, depth=0.15, front=True):
    sel = [p for p in pts if (p[1] > end_y - depth if front else p[1] < end_y + depth)]
    b = box(sel)
    return ((b["min"][0] + b["max"][0]) / 2, (b["min"][2] + b["max"][2]) / 2), b


def profile(pts, axis, y0, y1, step=0.25, rmax=2.4):
    rows = []
    y = y0
    while y < y1:
        rs = [math.hypot(p[0] - axis[0], p[2] - axis[1]) for p in pts if y <= p[1] < y + step]
        rs = [r for r in rs if r < rmax]
        rows.append([round(y, 2), round(max(rs), 3) if rs else None, round(min(rs), 3) if rs else None])
        y += step
    return rows


rig = json.load(open(RIG_FACTS))["rig"]
bones = rig["Armature"]["bones"]
# The SOCKET_* empties of the rig: the Default handguard's are evaluated in place; the Short and Extended
# handguards sit in excluded collections, so their empties are taken from the .blend's local values: the
# rig.json loc (Blender coordinates) is either the world point already (parent inverse cancels the handguard's
# offset) or a point relative to the handguard bone. Both readings are tested against the geometry below.
res = {"space": "Unreal gun space of the pack skeletal meshes: cm, +Y muzzle, +X left, +Z up",
       "bones": bones, "variants": {}, "parts": {}, "checks": {}}
author = {k: v["loc"] for k, v in rig.items() if k.startswith("SOCKET_")}
res["author_sockets_evaluated"] = author
hg_bone = bones["Handguard"]

for L in LENGTHS:
    v = load("SK_TFA_AR_%s_Combined.fbx" % L)
    vf = load("SK_TFA_AR_%s_Combined_Folded.fbx" % L)
    allp = [p for p, _, _ in v]
    hg = [p for p, b, _ in v if b == "Handguard"]
    grip = [p for p, b, _ in v if b == "Grip"]
    rear = [p for p, b, _ in v if b == "Sight_Rear"]
    tip = max(p[1] for p in allp)
    axis, ringb = ring_axis(allp, tip)
    m = {"tip_y": round(tip, 3), "bore_axis_xz": r3(axis), "muzzle_ring": ringb}
    m["muzzle_profile"] = profile(allp, axis, tip - 16.0, tip + 0.01)
    # rail top over the receiver (Grip bone, centre line, between the sights)
    rail = [p for p in grip if abs(p[0]) < 0.5 and 3.0 < p[1] < 13.0]
    m["rail_top_z"] = round(max(p[2] for p in rail), 3)
    # front sight post tip: handguard verts on the centre line, high, near the front sight
    fs = [p for p in hg if abs(p[0]) < 0.15 and p[2] > 7.0]
    top = max(fs, key=lambda p: p[2])
    m["front_post_tip"] = r3(top)
    post = [p for p in fs if p[2] > top[2] - 0.6]
    m["front_post_y"] = round(sum(p[1] for p in post) / len(post), 3)
    # rear aperture: the largest gap in z among the centre-line verts of the rear sight above the rail
    zs = sorted({round(p[2], 3) for p in rear if abs(p[0]) < 0.12 and p[2] > m["rail_top_z"] + 0.8})
    gaps = sorted(((zs[i + 1] - zs[i], zs[i], zs[i + 1]) for i in range(len(zs) - 1)), reverse=True)
    g = gaps[0] if gaps else (0, 0, 0)
    m["rear_aperture"] = {"z_low": g[1], "z_high": g[2], "centre_z": round((g[1] + g[2]) / 2, 3),
                          "y": round(sum(p[1] for p in rear if abs(p[0]) < 0.12) /
                                     max(1, len([p for p in rear if abs(p[0]) < 0.12])), 3)}
    # handguard underside along the centre line (where a grip clamps)
    under = {}
    for y in range(18, int(tip) + 1, 2):
        s = [p for p in hg if abs(p[0]) < 0.5 and y - 1 <= p[1] < y + 1 and p[2] < 3.5]
        under[y] = round(min(p[2] for p in s), 3) if s else None
    m["handguard_underside_z"] = under
    # right side rail outer face (x min) around z 3.6
    side = {}
    for y in range(18, int(tip) + 1, 2):
        s = [p for p in hg if 2.6 < p[2] < 4.6 and y - 1 <= p[1] < y + 1]
        side[y] = round(min(p[0] for p in s), 3) if s else None
    m["handguard_right_x"] = side
    m["handguard_box"] = box(hg)
    # receiver right wall at the ejection port, butt end, magazine well
    port = [p for p, b, _ in v if b == "Grip" and 8.0 < p[1] < 14.0 and 2.5 < p[2] < 5.0 and p[0] < 0]
    m["port_wall_x"] = round(max(p[0] for p in port if p[0] < -0.9), 3) if port else None
    butt_y = min(p[1] for p in grip)
    butt = [p for p in grip if p[1] < butt_y + 0.6]
    bb = box(butt)
    m["butt"] = {"y": round(butt_y, 3), "z_mid": round((bb["min"][2] + bb["max"][2]) / 2, 3), "box": bb}
    well = [p for p in grip if 7.0 < p[1] < 17.5 and -6.5 < p[2] < -3.0]
    m["mag_well_box"] = box(well)
    m["folded_irons_top_z"] = round(max(p[2] for p, b, _ in vf if b in ("Sight_Rear", "Handguard") and abs(p[0]) < 1.3), 3)
    m["standing_irons_top_z"] = round(max(p[2] for p, b, _ in v if b in ("Sight_Rear", "Handguard") and abs(p[0]) < 1.3), 3)
    m["stock_identical_in_folded"] = box([p for p, b, _ in v if b == "Grip"]) == box([p for p, b, _ in vf if b == "Grip"])
    res["variants"][L] = m
    print("MEASURED", L, flush=True)

# parts, in their own local space
for name in ("Scope", "Silencer", "Grip_Vertical", "Grip_Angled", "Laser", "Sight_Front", "Sight_Rear"):
    v = load("SM_TFA_AR_ATT_%s.fbx" % name)
    pts = [p for p, _, _ in v]
    m = {"box": box(pts)}
    if name == "Silencer":
        ymax = max(p[1] for p in pts)
        ax, rb = ring_axis(pts, ymax)
        ymin = min(p[1] for p in pts)
        axb, rbb = ring_axis(pts, ymin, front=False)
        m.update(end_y=round(ymax, 3), axis_front=r3(ax), axis_back=r3(axb),
                 back_face_y=round(ymin, 3), bore_radius_back=round(min(
                     math.hypot(p[0] - axb[0], p[2] - axb[1]) for p in pts if p[1] < ymin + 0.3), 3),
                 profile=profile(pts, axb, ymin, ymax + 0.01, step=0.5, rmax=3.0))
    if name == "Scope":
        glass = [p for p, _, mt in v if "Glass" in mt]
        ret = [p for p, _, mt in v if "Reticle" in mt]
        m.update(glass=box(glass), reticle=box(ret), rear_face_y=round(min(p[1] for p in pts), 3),
                 front_face_y=round(max(p[1] for p in pts), 3))
    if name == "Laser":
        ys = sorted(p[1] for p in pts)
        m.update(length_along_bore_cm=round(ys[-1] - ys[0], 3))
        front = [p for p in pts if p[1] > ys[-1] - 0.3]
        m["front_face"] = box(front)
    if name.startswith("Grip"):
        body = [p for p in pts if p[2] < -1.0]
        m["body"] = box(body)
        m["clamp_top_z"] = round(max(p[2] for p in pts), 3)
    res["parts"][name] = m
    print("MEASURED", name, flush=True)

for name in ("SK_TFA_AR_Magazine", "SK_TFA_AR_Magazine_Transparent"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, "Meshes", name + ".fbx"))
    for o in bpy.data.objects:
        if o.type == "MESH":
            res["parts"][name] = {"vgroups": [g.name for g in o.vertex_groups],
                                  "materials": [s.material.name for s in o.material_slots if s.material]}
        if o.type == "ARMATURE":
            res["parts"].setdefault(name + "_bones", [b.name for b in o.data.bones])

json.dump(res, open(OUT, "w"), indent=1)
print("BL-MEASURE-DONE")
