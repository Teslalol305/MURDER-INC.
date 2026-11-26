#!/usr/bin/env python3
"""The support hand's reload grip round each magazine (HANDS_R4.md 8.1 step 2, section 10), written into grips.json.

In a reload the first-person rig carries the support hand from the handguard onto the magazine it drops and seats
(UMIFirstPersonRig::UpdateHands). Turning the handguard's solved grip round the magazine (magazine.turn) read as an open,
spread hand in every frame (HANDS_R4.md 9.4): that grip wraps a 5 to 6 cm round handguard, a magazine is a 2.6 to 3.3 cm
plank. This solves a grip round each magazine's own body instead, by rule, from the magazine's mesh:

  - the palm flat on the magazine's left face (the palm bones 1.5 cm off it), the fingers forward with their knuckle line
    along the magazine's front edge (a curved magazine's edge leans: the hand leans with it), tilted `tilt` degrees
    further up, the middle knuckle `height` of the way up from the base;
  - each finger closed joint by joint (knuckle, middle joint, end joint) until that phalanx touches the magazine (its
    cross-section at that height, grown by the finger's radius) or reaches its largest bend: the fingers wrap the front
    edge and lie on the right face, the pinky closes into the fist under a short magazine;
  - the thumb along the left face toward the magazine's top (it pushes the magazine into the well).

The bone lengths and the hand's own knuckle arc come from the solved hip grip of the CHOPPER (grips.json, made by
art/blender/assets/_rule_grips.py on SK_RuleArms). The magazine meshes are read from the GLBs the importer brings in
(art/out/glb, git-ignored: the Blender outputs), in Unreal's convention (glTF (x, y, z) -> Unreal (x, z, y) x 100 cm,
docs/unreal/BOX.md 5), in the magazine mesh's own frame, which is the frame the game reads them in. Output:
grips.json "magazines": {<static mesh name>: {"l": {bone: [x, y, z] cm}, "rule": {...}}}.

Pure Python (no Blender, no numpy). Run: python3 tools/data/reload_grips.py [--glb art/out/glb] [--check]
--check writes nothing: it re-solves and prints the largest difference from what grips.json holds (cm).
"""
import argparse
import json
import math
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GRIPS = os.path.join(ROOT, "unreal", "MurderInc", "Content", "Data", "grips.json")

# every magazine a hand-IK gun can hold: its own (presentation.json animSets.*.magazine.full) and the fitted parts
MAGAZINES = {
    "SM_Weapon_ChopperMagazine": {},
    "SM_Weapon_ShortyMagazine": {},
    "SM_Weapon_StretchMagazine": {},
    "SM_Weapon_RattlerMagazine": {},
    "SM_Weapon_NineMagazine": {},
    "SM_Part_MagRifleExt": {},
    "SM_Part_MagSmgExt": {},
    "SM_Part_MagPistolExt": {},
}
# "base" (HANDS_R4.md 13, the default): palm under the base plate, fingers up the front face, thumb up the left face.
# "side" (HANDS_R4.md 10): palm flat on the left face, the face the eye looks at in a reload: it hid the magazine (11, 12.4).
DEFAULTS = {
    "base": {"style": "base", "palm_off": 1.5, "knuckle_ahead": 1.0, "finger_r": 0.8, "thumb_off": 0.9, "thumb_rise_deg": 70.0,
             "max_sum": 150.0, "axis_lo": 3.0, "axis_hi": 9.0, "base_band": 2.0, "index_in": 0.6, "yaw": 0.0},
    "side": {"style": "side", "height": 0.40, "tilt": 0.0, "thumb_rise_deg": 35.0, "palm_off": 1.5, "knuckle_ahead": 0.9,
             "finger_r": 0.8, "thumb_off": 0.9, "max_sum": 150.0},
}
FINGERS = ("index", "middle", "ring", "pinky")
MAX_BEND = (90.0, 105.0, 80.0)   # knuckle, middle joint, end joint (degrees)


# ------------------------------------------------------------------------------------------------ small vector maths
def add(a, b): return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
def sub(a, b): return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
def mul(a, s): return [a[0] * s, a[1] * s, a[2] * s]
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
def norm(a):
    n = math.sqrt(dot(a, a))
    return [a[0] / n, a[1] / n, a[2] / n]


def rot(v, axis, deg):
    """v turned by deg about the unit axis (Rodrigues; the sense is the same as the cross product's)."""
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return add(add(mul(v, c), mul(cross(axis, v), s)), mul(axis, dot(axis, v) * (1 - c)))


def frame(x, a):
    """The hand's frame as MIFirstPersonAnim.cpp HandFrame builds it: X, Z = X x across, Y = Z x X."""
    x = norm(x)
    z = norm(cross(x, a))
    return x, cross(z, x), z


# ------------------------------------------------------------------------------------------------ the magazine
def glb_triangles(path):
    """Every triangle of a GLB's meshes (node transforms applied), as three vertices each, Unreal cm."""
    b = open(path, "rb").read()
    if b[:4] != b"glTF":
        raise ValueError(path + " is not a GLB")
    off, js, bin_ = 12, None, None
    while off < len(b):
        ln, typ = struct.unpack_from("<II", b, off)
        off += 8
        if typ == 0x4E4F534A:
            js = json.loads(b[off:off + ln])
        else:
            bin_ = b[off:off + ln]
        off += ln

    def mat(n):
        if "matrix" in n:
            m = n["matrix"]
            return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
        t, (x, y, z, w), s = n.get("translation", [0, 0, 0]), n.get("rotation", [0, 0, 0, 1]), n.get("scale", [1, 1, 1])
        R = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
             [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
             [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
        return [[R[i][0] * s[0], R[i][1] * s[1], R[i][2] * s[2], t[i]] for i in range(3)] + [[0, 0, 0, 1]]

    def mm(a, c):
        return [[sum(a[i][k] * c[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
    out = []

    def walk(ni, M):
        n = js["nodes"][ni]
        M2 = mm(M, mat(n))
        if "mesh" in n:
            for p in js["meshes"][n["mesh"]]["primitives"]:
                a = js["accessors"][p["attributes"]["POSITION"]]
                bv = js["bufferViews"][a["bufferView"]]
                o, st = bv.get("byteOffset", 0) + a.get("byteOffset", 0), bv.get("byteStride", 12)
                vs = []
                for i in range(a["count"]):
                    q = struct.unpack_from("<fff", bin_, o + i * st) + (1.0,)
                    v = [sum(M2[r][c] * q[c] for c in range(4)) for r in range(3)]
                    vs.append((v[0] * 100.0, v[2] * 100.0, v[1] * 100.0))
                if "indices" in p:
                    ia = js["accessors"][p["indices"]]
                    ib = js["bufferViews"][ia["bufferView"]]
                    fmt, size = {5121: ("<B", 1), 5123: ("<H", 2), 5125: ("<I", 4)}[ia["componentType"]]
                    io = ib.get("byteOffset", 0) + ia.get("byteOffset", 0)
                    idx = [struct.unpack_from(fmt, bin_, io + k * size)[0] for k in range(ia["count"])]
                else:
                    idx = list(range(len(vs)))
                out.extend((vs[idx[k]], vs[idx[k + 1]], vs[idx[k + 2]]) for k in range(0, len(idx) - 2, 3))
        for c in n.get("children", []):
            walk(c, M2)
    for ni in js["scenes"][js.get("scene", 0)]["nodes"]:
        walk(ni, [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)])
    return out


def hull(pts):
    """2D convex hull (monotone chain), counter-clockwise."""
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def turn(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and turn(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and turn(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


class Magazine:
    """The magazine as a stack of convex cross-sections (X, Y) every 0.5 cm up its height."""

    def __init__(self, tris):
        verts = [v for t in tris for v in t]
        self.verts = verts
        self.z0 = min(v[2] for v in verts)
        self.z1 = max(v[2] for v in verts)
        self.ymin = min(v[1] for v in verts)
        self.slabs = []
        z = self.z0 + 0.05
        while z <= self.z1 - 0.05 + 1e-6:
            s = []
            for t in tris:   # the triangles cut by the plane at this height: the cross-section's outline
                for i in range(3):
                    a, b = t[i], t[(i + 1) % 3]
                    if (a[2] - z) * (b[2] - z) < 0:
                        k = (z - a[2]) / (b[2] - a[2])
                        s.append((round(a[0] + k * (b[0] - a[0]), 3), round(a[1] + k * (b[1] - a[1]), 3)))
            self.slabs.append((z, hull(s) if len(s) >= 3 else []))
            z += 0.5

    def section(self, z):
        i = min(range(len(self.slabs)), key=lambda k: abs(self.slabs[k][0] - z))
        return self.slabs[i][1]

    def front(self, z):
        s = self.section(min(max(z, self.z0), self.z1))
        return max(p[0] for p in s) if s else None

    def depth(self, p):
        """How far p is inside the magazine (cm, > 0 inside, < 0 outside), by its cross-section at p's height."""
        s = self.section(min(max(p[2], self.z0), self.z1))
        if len(s) < 3:
            return -99.0
        inside, best = True, 1e9
        for i in range(len(s)):
            a, b = s[i], s[(i + 1) % len(s)]
            ex, ey = b[0] - a[0], b[1] - a[1]
            px, py = p[0] - a[0], p[1] - a[1]
            if ex * py - ey * px < 0:
                inside = False
            L2 = ex * ex + ey * ey
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, (px * ex + py * ey) / L2))
            best = min(best, math.hypot(px - t * ex, py - t * ey))
        dz = max(self.z0 - p[2], p[2] - self.z1, 0.0)
        if inside and dz == 0.0:
            return best
        return -math.hypot(0.0 if inside else best, dz)


def touches(mag, a, b, r):
    """A phalanx from a to b (radius r) touches or sinks into the magazine."""
    for k in range(9):
        p = add(a, mul(sub(b, a), k / 8.0))
        if mag.depth(p) > -r:
            return True
    return False


# ------------------------------------------------------------------------------------------------ the hand
def template(grips):
    L = grips["guns"]["chopper"]["hip"]["l"]
    return {k: list(v) for k, v in L.items()}


def solve(mag, T, rule):
    W, M1, I1, P1 = T["hand_l"], T["middle_01_l"], T["index_01_l"], T["pinky_01_l"]
    xs, ys, zs = frame(sub(M1, W), sub(I1, P1))
    # the side the fingers close to (the palm) in the template's frame
    curl = [sum(T[f + "_tip_l"][i] - T[f + "_01_l"][i] for f in FINGERS) for i in range(3)]
    s = 1.0 if dot(curl, zs) > 0 else -1.0
    # where the middle knuckle goes: `height` up the magazine, just ahead of its front edge, palm bones off the left face
    zk = mag.z0 + rule["height"] * (mag.z1 - mag.z0)
    zk = min(zk, mag.z1 - 3.5)
    fz = mag.front(zk)
    e = sub([mag.front(zk + 2.5), 0, zk + 2.5], [mag.front(zk - 2.5), 0, zk - 2.5])   # the front edge, upward
    e = norm(e)
    xt = norm([e[2], 0.0, -e[0]])                    # forward, square to the edge
    xt = norm(rot(xt, [0.0, 1.0, 0.0], -rule["tilt"]))  # tilted further up (about Y a positive turn takes X toward -Z)
    palm_n = [0.0, 1.0, 0.0]                          # the palm faces right, onto the left face
    zt = mul(palm_n, s)
    yt = cross(zt, xt)
    knuckle = [fz + rule["knuckle_ahead"], mag.ymin - rule["palm_off"], zk]

    def place(p, flat):
        d = sub(p, M1)
        loc = [dot(d, xs), dot(d, ys), 0.0 if flat else dot(d, zs)]
        return add(knuckle, add(add(mul(xt, loc[0]), mul(yt, loc[1])), mul(zt, loc[2])))
    # the palm laid flat on the flat face (the template's palm is cupped round a round handguard)
    palm = {"hand_l", "thumb_01_l"} | {f + "_metacarpal_l" for f in FINGERS} | {f + "_01_l" for f in FINGERS}
    out = {k: place(v, k in palm) for k, v in T.items()}
    # each finger, straight from its metacarpal, then closed joint by joint until it touches
    report = {}
    for f in FINGERS:
        names = ["%s_%02d_l" % (f, k) for k in (1, 2, 3)] + [f + "_tip_l"]
        lens = [math.dist(T[names[i]], T[names[i + 1]]) for i in range(3)]
        base = out[names[0]]
        d0 = norm(sub(base, out[f + "_metacarpal_l"]))
        hinge = norm(cross(d0, palm_n))
        # the sense that brings the finger toward the palm
        if dot(rot(d0, hinge, 10.0), palm_n) < dot(d0, palm_n):
            hinge = mul(hinge, -1.0)
        angles = [0.0, 0.0, 0.0]

        def chain(ang):
            pts, d = [base], d0
            for i in range(3):
                d = rot(d, hinge, ang[i])
                pts.append(add(pts[-1], mul(d, lens[i])))
            return pts
        for j in range(3):
            step = 2.0
            while angles[j] + step <= MAX_BEND[j] and sum(angles) + step <= rule.get("max_sum", 999.0):
                trial = list(angles)
                trial[j] += step
                pts = chain(trial)
                if any(touches(mag, pts[i], pts[i + 1], rule["finger_r"]) for i in range(j, 3)):
                    break
                angles = trial
        pts = chain(angles)
        for n, p in zip(names, pts):
            out[n] = p
        report[f] = [round(a) for a in angles]
    # the thumb on the left face, rising thumb_rise_deg from its base toward the front, gently bent (its tip 88 % of its length
    # from its base; 2 cm under the magazine's top at most: above it is the gun's well), searched: the first segment's
    # direction and the even bend at its two joints that put the tip there
    tn = ["thumb_01_l", "thumb_02_l", "thumb_03_l", "thumb_tip_l"]
    tl = [math.dist(T[tn[i]], T[tn[i + 1]]) for i in range(3)]
    y_face = mag.ymin - rule["thumb_off"]
    base = out["thumb_01_l"]
    reach = 0.88 * sum(tl)            # a thumb laid along a flat face, gently bent
    rise = math.radians(rule["thumb_rise_deg"])
    tz = min(base[2] + reach * math.sin(rise), mag.z1 - 2.0)
    tx = base[0] + math.sqrt(max(reach * reach - (tz - base[2]) ** 2, 0.0))
    target = [tx, y_face, tz]
    best = None
    for a10 in range(-900, 901, 15):          # the first segment's direction in the face's plane (degrees from +X, toward +Z)
        for c10 in range(0, 451, 15):         # the bend at each of the two joints (toward -Z: the thumb curls down onto the face)
            a, c = math.radians(a10 / 10.0), math.radians(c10 / 10.0)
            p, ang, pts = base, a, []
            for i in range(3):
                d = [math.cos(ang), 0.0, math.sin(ang)]
                q = add(p, mul(d, tl[i]))
                q[1] = p[1] + (y_face - p[1]) * (0.5 if i == 0 else 1.0)
                q = add(p, mul(norm(sub(q, p)), tl[i]))
                pts.append(q)
                p = q
                ang -= c
            miss = math.dist(pts[-1], target)
            if best is None or miss < best[0]:
                best = (miss, pts, a10 / 10.0, c10 / 10.0)
    for n, q in zip(tn[1:], best[1]):
        out[n] = q
    report["thumb"] = {"tip_miss_cm": round(best[0], 2), "first_deg": best[2], "bend_deg": best[3]}
    report["thumb_base_off_face_cm"] = round(mag.ymin - out["thumb_01_l"][1], 2)
    report["wrist"] = [round(v, 2) for v in out["hand_l"]]
    report["knuckle"] = [round(v, 2) for v in knuckle]
    # nothing may sink into the magazine
    worst = max(mag.depth(v) for v in out.values())
    report["deepest_point_cm"] = round(worst, 2)
    return {k: [round(v[0], 3), round(v[1], 3), round(v[2], 3)] for k, v in out.items()}, report


def solve_base(mag, T, rule):
    """The base hold (HANDS_R4.md 13): the magazine held from below, as a shooter seats one. The palm flat under the base
    plate (the palm bones `palm_off` under it), the fingers forward with their knuckle line just ahead of the front edge
    (`knuckle_ahead`), each closed joint by joint until it lies on the front face (no finger bent more than `max_sum`
    degrees in all: a finger with nothing to hold curls, it does not fold through the palm), the thumb up the magazine's
    left face, the side toward the eye. From the eye (behind, above and left of the magazine in a reload) the magazine's
    rear and left faces stay in sight: the hand is under and in front of it. A curved magazine is held square to its own
    axis near the base (the midline of its sections `axis_lo` to `axis_hi` cm above its lowest point)."""
    W, M1, I1, P1 = T["hand_l"], T["middle_01_l"], T["index_01_l"], T["pinky_01_l"]
    xs, ys, zs = frame(sub(M1, W), sub(I1, P1))
    curl = [sum(T[f + "_tip_l"][i] - T[f + "_01_l"][i] for f in FINGERS) for i in range(3)]
    s = 1.0 if dot(curl, zs) > 0 else -1.0

    def mid(z):
        sec = mag.section(min(max(z, mag.z0), mag.z1))
        return (min(p[0] for p in sec) + max(p[0] for p in sec)) * 0.5
    za = min(mag.z0 + rule["axis_lo"], mag.z1 - 1.0)
    zb = min(mag.z0 + rule["axis_hi"], mag.z1 - 0.5)
    u = norm([mid(za) - mid(zb), 0.0, za - zb])            # down the magazine's axis at its base
    f = [-u[2], 0.0, u[0]]                                  # forward, square to it (both in the X-Z plane)
    b = max(dot(v, u) for v in mag.verts)                   # the base plate, along u
    low = [v for v in mag.verts if dot(v, u) > b - rule["base_band"]]
    fmax = max(dot(v, f) for v in low)
    ymin = min(v[1] for v in low)
    palm_n = mul(u, -1.0)                                   # the palm faces up the magazine, onto its base
    xt = norm(rot(f, palm_n, rule.get("yaw", 0.0)))        # the fingers forward, turned `yaw` about the axis
    zt = mul(palm_n, s)
    yt = cross(zt, xt)
    knuckle = add(add(mul(u, b + rule["palm_off"]), mul(f, fmax + rule["knuckle_ahead"])), [0.0, 0.0, 0.0])

    palm = {"hand_l", "thumb_01_l"} | {g + "_metacarpal_l" for g in FINGERS} | {g + "_01_l" for g in FINGERS}

    def place(p, flat, at):
        d = sub(p, M1)
        loc = [dot(d, xs), dot(d, ys), 0.0 if flat else dot(d, zs)]
        return add(at, add(add(mul(xt, loc[0]), mul(yt, loc[1])), mul(zt, loc[2])))
    out = {k: place(v, k in palm, knuckle) for k, v in T.items()}
    # across the magazine: the index knuckle `index_in` cm inside the left face, so the index takes the front-left corner and
    # the others the front and the right (a hand is wider than a magazine)
    shift = (ymin + rule["index_in"]) - out["index_01_l"][1]
    knuckle = add(knuckle, [0.0, shift, 0.0])
    out = {k: add(v, [0.0, shift, 0.0]) for k, v in out.items()}
    report = {"axis_down": [round(x, 3) for x in u]}
    for g in FINGERS:
        report[g] = close_finger(mag, T, out, g, palm_n, rule)
    # the thumb up the left face (toward the eye), from its base under the plate: its tip 88 % of its length away, `thumb_rise_deg`
    # from the forward direction toward the magazine's top, 2 cm under the top at most
    up = palm_n
    tn = ["thumb_01_l", "thumb_02_l", "thumb_03_l", "thumb_tip_l"]
    tl = [math.dist(T[tn[i]], T[tn[i + 1]]) for i in range(3)]
    y_face = ymin - rule["thumb_off"]
    base = out["thumb_01_l"]
    reach = 0.88 * sum(tl)
    rise = math.radians(rule["thumb_rise_deg"])
    target = add(base, add(mul(f, reach * math.cos(rise)), mul(up, reach * math.sin(rise))))
    target[1] = y_face
    best = None
    for a10 in range(-300, 1201, 15):          # the first segment's direction in the face's plane (degrees from forward toward up)
        for c10 in range(0, 451, 15):          # the even bend at each of its two joints (toward forward: the thumb curls to the fingers)
            a, c = math.radians(a10 / 10.0), math.radians(c10 / 10.0)
            p, ang, pts = base, a, []
            for i in range(3):
                d = add(mul(f, math.cos(ang)), mul(up, math.sin(ang)))
                q = add(p, mul(d, tl[i]))
                q[1] = p[1] + (y_face - p[1]) * (0.5 if i == 0 else 1.0)
                q = add(p, mul(norm(sub(q, p)), tl[i]))
                pts.append(q)
                p = q
                ang -= c
            if pts[-1][2] > mag.z1 - 2.0 or any(mag.depth(q) > -0.7 for q in pts):
                continue
            miss = math.dist(pts[-1], target)
            if best is None or miss < best[0]:
                best = (miss, pts, a10 / 10.0, c10 / 10.0)
    if best is not None:
        for n, q in zip(tn[1:], best[1]):
            out[n] = q
        report["thumb"] = {"tip_miss_cm": round(best[0], 2), "first_deg": best[2], "bend_deg": best[3]}
    report["wrist"] = [round(v, 2) for v in out["hand_l"]]
    report["knuckle"] = [round(v, 2) for v in knuckle]
    report["deepest_point_cm"] = round(max(mag.depth(v) for v in out.values()), 2)
    return {k: [round(v[0], 3), round(v[1], 3), round(v[2], 3)] for k, v in out.items()}, report


def close_finger(mag, T, out, f, palm_n, rule):
    """One finger, straight on from its metacarpal, closed joint by joint toward the palm until a phalanx touches the
    magazine, a joint reaches its largest bend (MAX_BEND) or the finger's summed bend reaches `max_sum`."""
    names = ["%s_%02d_l" % (f, k) for k in (1, 2, 3)] + [f + "_tip_l"]
    lens = [math.dist(T[names[i]], T[names[i + 1]]) for i in range(3)]
    base = out[names[0]]
    d0 = norm(sub(base, out[f + "_metacarpal_l"]))
    hinge = norm(cross(d0, palm_n))
    if dot(rot(d0, hinge, 10.0), palm_n) < dot(d0, palm_n):
        hinge = mul(hinge, -1.0)
    angles = [0.0, 0.0, 0.0]

    def chain(ang):
        pts, d = [base], d0
        for i in range(3):
            d = rot(d, hinge, ang[i])
            pts.append(add(pts[-1], mul(d, lens[i])))
        return pts
    for j in range(3):
        step = 2.0
        while angles[j] + step <= MAX_BEND[j] and sum(angles) + step <= rule.get("max_sum", 999.0):
            trial = list(angles)
            trial[j] += step
            pts = chain(trial)
            if any(touches(mag, pts[i], pts[i + 1], rule["finger_r"]) for i in range(j, 3)):
                break
            angles = trial
    pts = chain(angles)
    for n, p in zip(names, pts):
        out[n] = p
    return [round(a) for a in angles]


SOLVERS = {"side": solve, "base": solve_base}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", default=os.path.join(ROOT, "art", "out", "glb"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--set", action="append", default=[], help="name=value overrides of the rule for every magazine (tuning)")
    a = ap.parse_args()
    grips = json.load(open(GRIPS))
    T = template(grips)
    def val(x):
        try:
            return float(x)
        except ValueError:
            return x
    over = {kv.split("=")[0]: val(kv.split("=")[1]) for kv in a.set}
    mags = grips.get("magazines", {})
    worst = 0.0
    for name, own in MAGAZINES.items():
        path = os.path.join(a.glb, name + ".glb")
        if not os.path.exists(path):
            print("skip %s: no %s" % (name, path))
            continue
        style = over.get("style", own.get("style", "base"))
        rule = dict(DEFAULTS[style], **own, **over)
        pts, rep = SOLVERS[style](Magazine(glb_triangles(path)), T, rule)
        print("%-28s %s" % (name, json.dumps(rep)))
        if a.check:
            old = mags.get(name, {}).get("l", {})
            d = max((math.dist(pts[k], old[k]) for k in pts if k in old), default=1e9)
            worst = max(worst, d)
            continue
        mags[name] = {"rule": rule, "l": pts}
    if a.check:
        print("largest difference from grips.json: %.3f cm" % worst)
        return 0 if worst < 0.01 else 1
    grips["magazines"] = mags
    with open(GRIPS, "w") as f:
        json.dump(grips, f, indent=1)
        f.write("\n")
    print("wrote", GRIPS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
