"""Characters on the UE5 mannequin skeleton: the player's first-person arms SK_RuleArms (briefs character_rule_arms,
character_rule_watch, character_rule_bracelet in docs/unreal/spec/assets/weapons.json; web source src/weapon/arms.js).

Pipeline (docs/unreal/CHARACTERS.md, art/blender/README.md "Characters"):
  1. import Epic's mannequin (art/out/epic, never committed) and read the right arm's bones in the rest pose;
  2. model the right arm as signed distance fields placed on those bones (anatomy in ArmRig, hand in hand_sdf):
     bare skin from the shoulder to inside the glove cuff, the glove as a separate surface over the hand, and the
     moulded rubber pieces (knuckle bar, wrist strap, fingertip pads) as separate pieces;
  3. surface nets -> projection onto the exact surface -> relaxation; UVs (the glove is cut like a real glove
     pattern: back and palm panels), panel labels, skin weights transferred from the mannequin's own arm and hand
     (per finger, so a finger never takes a neighbour's weights), mirrored to the left arm;
  4. textures computed per texel from the baked rest position (characters_tex.py): skin and glove 4K sets;
  5. one skinned GLB on the full skeleton (char.export_character), the watch and the bracelet as static meshes.

`--only roundtrip` re-runs the Blender half of the round-trip proof (art/out/epic/RT_Manny.glb).
"""
import json
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import char, geo, paths, scene, sdf

FAMILY = {"name": "characters", "description": "First-person arms on the UE5 mannequin skeleton, watch, bracelet"}

SKIN_H = 0.0026          # surface nets spacing of the skin (metres)
GLOVE_H = 0.00135        # of the glove
PIECE_H = 0.0006         # of the rubber pieces
GLOVE_T = 0.0012         # glove material over the hand
CUFF_TOP = 0.042         # padded cuff from 4 to 42 mm above the wrist (brief)
SKIN_CUT = 0.024         # the skin mesh starts inside the cuff (hidden overlap 18 mm)

# forearm sections, distance above the wrist (m) -> full width x height (mm); brief character_rule_arms, eased
# toward the mannequin's own forearm near the elbow (muscle masses add 3-5 mm on top)
FOREARM = [(-0.03, 56, 38), (0.00, 60, 42), (0.04, 64, 48), (0.09, 74, 60), (0.13, 83, 69), (0.16, 88, 75),
           (0.20, 92, 80), (0.24, 94, 82), (0.28, 90, 84), (0.31, 86, 84)]
# upper arm, distance above the elbow joint (m) -> width (medial-lateral) x depth (front-back) mm
UPPER = [(-0.02, 80, 74), (0.00, 80, 72), (0.06, 82, 78), (0.13, 90, 88), (0.20, 98, 94), (0.25, 106, 98),
         (0.29, 100, 96)]
# finger radii at the base (brief, mm) and the taper to the tip
FINGER_R = {"index": 9.3, "middle": 9.7, "ring": 9.1, "pinky": 8.0, "thumb": 12.2}
FINGERS = ("index", "middle", "ring", "pinky", "thumb")


def _n(v):
    v = np.asarray(v, dtype=np.float64)
    return v / max(np.linalg.norm(v), 1e-12)


def _perp(v, axis):
    v = np.asarray(v, dtype=np.float64)
    return _n(v - (v @ axis) * axis)


def _rot(v, axis, ang):
    """Rodrigues rotation of vectors v (N, 3) or (3,) about unit axis by angles ang (N,) or scalar."""
    v = np.asarray(v, dtype=np.float64)
    c, s = np.cos(ang), np.sin(ang)
    if v.ndim == 1:
        return v * c + np.cross(axis, v) * s + axis * (axis @ v) * (1 - c)
    c, s = np.asarray(c)[..., None], np.asarray(s)[..., None]
    return v * c + np.cross(axis, v) * s + axis[None] * (v @ axis)[:, None] * (1 - c)


def _interp(table, s, col):
    xs = np.array([t[0] for t in table])
    ys = np.array([t[col] for t in table]) * 0.001
    return np.interp(s, xs, ys)


def ellipse_d(x, y, a, b):
    """Distance bound to an ellipse of semi-axes a, b (Quilez's ellipsoid bound in 2D)."""
    k0 = np.sqrt((x / a) ** 2 + (y / b) ** 2)
    k1 = np.sqrt((x / (a * a)) ** 2 + (y / (b * b)) ** 2)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-12)


# ------------------------------------------------------------------------------------------------ anatomy frame


class ArmRig:
    """The right arm's landmarks and frames, read from the mannequin in its rest pose (Blender world metres)."""

    def __init__(self, arm, body, side="r"):
        self.side = side
        B = arm.data.bones
        h = lambda n: np.array(B[n + "_" + side].head_local, dtype=np.float64)
        self.h = h
        self.S, self.E, self.W = h("upperarm"), h("lowerarm"), h("hand")
        self.L = float(np.linalg.norm(self.W - self.E))                 # forearm length (elbow -> wrist joint)
        self.Lu = float(np.linalg.norm(self.E - self.S))
        self.af = _n(self.W - self.E)                                    # forearm axis, toward the wrist
        self.bu = _n(self.S - self.E)                                    # upper-arm axis, toward the shoulder
        mcp = {f: h(f + "_01") for f in FINGERS[:4]}
        self.mcp = mcp
        self.fwd = _n(np.mean(list(mcp.values()), axis=0) - self.W)
        self.lat = _perp(mcp["pinky"] - mcp["index"], self.fwd)          # toward the little finger (ulnar)
        curl = np.zeros(3)
        for f in FINGERS[:4]:
            d1 = _n(h(f + "_02") - h(f + "_01"))
            d3 = _n(h(f + "_03") - h(f + "_02"))
            curl += d3 - d1
        dors = _n(np.cross(self.fwd, self.lat))
        if dors @ curl > 0:                                              # the fingers curl toward the palm
            dors = -dors
        self.dors = dors
        self.lat = _n(np.cross(self.dors, self.fwd))                     # re-orthonormalise (sign kept: ulnar)
        if self.lat @ (mcp["pinky"] - mcp["index"]) < 0:
            self.lat = -self.lat
        # forearm section frame: width axis u (ulnar), height axis v (dorsal); twisted toward the elbow hinge
        self.u0 = _perp(self.lat, self.af)
        self.v0 = _n(np.cross(self.af, self.u0))
        if self.v0 @ self.dors < 0:
            self.v0 = -self.v0
        hinge = _n(np.cross(self.bu, self.af))
        ue = _perp(hinge, self.af)
        if ue @ self.u0 < 0:
            ue = -ue
        self.twist = float(math.atan2(np.cross(self.u0, ue) @ self.af, self.u0 @ ue))
        # upper arm frame: anterior (biceps side) = where the forearm points
        self.ant = _perp(self.af, self.bu)
        self.latu = _n(np.cross(self.bu, self.ant))
        if self.latu[0] * (1 if side == "l" else -1) < 0:               # away from the body
            self.latu = -self.latu
        # fingers: joint chain P1..P4 (P4 = the tip's sphere centre) and radii from the brief
        self.chain = {}
        for f in FINGERS:
            p1, p2, p3 = h(f + "_01"), h(f + "_02"), h(f + "_03")
            d3 = _n(p3 - p2)
            tip = self._tip_extent(arm, body, f + "_03_" + side, p3, d3)
            r0 = FINGER_R[f] * 0.001 + GLOVE_T * 0
            radii = np.array([1.0, 0.93, 0.88, 0.80]) * r0
            p4 = p3 + d3 * max(tip - radii[3], 0.008)
            dors_f = _perp(self.dors, _n(p3 - p1)) if f != "thumb" else self._thumb_dorsal(p1, p2, p3)
            self.chain[f] = dict(P=np.array([p1, p2, p3, p4]), r=radii, dors=dors_f)
        self.cmc = h("thumb_01")

    def _tip_extent(self, arm, body, bone, p3, d3):
        names = [g.name for g in body.vertex_groups]
        if bone not in names:
            return 0.024
        gi = names.index(bone)
        co = np.array([v.co for v in body.data.vertices if any(g.group == gi and g.weight > 0.6 for g in v.groups)])
        if not len(co):
            return 0.024
        return float(((co - p3) @ d3).max())

    def _thumb_dorsal(self, p1, p2, p3):
        ax = _n(p3 - p1)
        # the thumb nail faces away from the palm and toward the radial side
        d = _perp(self.dors * 0.55 - self.lat * 0.85, ax)
        return d

    # --- forearm ---------------------------------------------------------------------------------------------
    def fore_coords(self, p):
        """(s above the wrist, x along the (twisted) width axis, y along the height axis) for points p."""
        q = p - self.W
        s = q @ (-self.af)
        rad = q + np.outer(s, self.af)
        t = np.clip(s / self.L, 0, 1)
        ang = self.twist * (t * t * (3 - 2 * t))
        u = _rot(np.broadcast_to(self.u0, rad.shape), self.af, ang)
        v = np.cross(self.af, u)
        if (np.cross(self.af, self.u0) @ self.v0) < 0:
            v = -v
        return s, np.einsum("ij,ij->i", rad, u), np.einsum("ij,ij->i", rad, v)

    def fore_frame(self, s):
        t = min(max(s / self.L, 0), 1)
        u = _rot(self.u0, self.af, self.twist * (t * t * (3 - 2 * t)))
        v = np.cross(self.af, u)
        if (np.cross(self.af, self.u0) @ self.v0) < 0:
            v = -v
        return self.W - self.af * s, u, v

    def forearm_section(self, p, grow=0.0):
        s, x, y = self.fore_coords(p)
        a = _interp(FOREARM, s, 1) / 2 + grow
        b = _interp(FOREARM, s, 2) / 2 + grow
        return s, ellipse_d(x, y, a, b)

    # --- upper arm --------------------------------------------------------------------------------------------
    def upper_coords(self, p):
        q = p - self.E
        s = q @ self.bu
        rad = q - np.outer(s, self.bu)
        return s, rad @ self.latu, rad @ self.ant


# ------------------------------------------------------------------------------------------------ fields


def skin_sdf(R):
    """Bare arm from the shoulder to below the glove cuff: forearm (twisting section, muscle masses), elbow,
    upper arm (biceps, triceps, deltoid), closed at the shoulder."""
    def f(p):
        s, d_fore = R.forearm_section(p)
        d_fore = np.maximum(d_fore, s - (R.L + 0.035))
        d_fore = np.maximum(d_fore, -s - 0.035)
        su, xu, yu = R.upper_coords(p)
        a = _interp(UPPER, su, 1) / 2
        b = _interp(UPPER, su, 2) / 2
        d_up = ellipse_d(xu, yu, a, b)
        d_up = np.maximum(d_up, su - (R.Lu + 0.005))
        d_up = np.maximum(d_up, -su - 0.03)
        d = sdf.smin(d_fore, d_up, 0.028)
        # forearm muscle masses (frame at their centre)
        for s0, off, rad, k in (
            (0.205, (-0.020, 0.012), (0.080, 0.020, 0.020), 0.016),     # brachioradialis / radial extensors
            (0.195, (0.010, -0.017), (0.085, 0.024, 0.019), 0.016),     # flexor mass
            (0.150, (0.012, 0.016), (0.070, 0.016, 0.015), 0.014),      # ulnar extensors
        ):
            c0, u, v = R.fore_frame(s0)
            c = c0 + u * off[0] + v * off[1]
            d = sdf.smin(d, sdf.ellipsoid(p, c, np.array([R.af, u, v]), rad), k)
        # elbow: olecranon and epicondyles
        d = sdf.smin(d, sdf.sphere(p, R.E - R.ant * 0.030 + R.bu * 0.004, 0.0165), 0.012)
        d = sdf.smin(d, sdf.sphere(p, R.E + R.latu * 0.034 + R.bu * 0.012, 0.012), 0.012)
        d = sdf.smin(d, sdf.sphere(p, R.E - R.latu * 0.037 + R.bu * 0.014, 0.012), 0.012)
        # upper arm muscles
        fr = np.array([R.bu, R.latu, R.ant])
        d = sdf.smin(d, sdf.ellipsoid(p, R.E + R.bu * 0.125 + R.ant * 0.020, fr, (0.085, 0.028, 0.028)), 0.018)  # biceps
        d = sdf.smin(d, sdf.ellipsoid(p, R.E + R.bu * 0.165 - R.ant * 0.018, fr, (0.095, 0.034, 0.030)), 0.018)  # triceps
        d = sdf.smin(d, sdf.ellipsoid(p, R.S - R.bu * 0.045 + R.latu * 0.012, fr, (0.075, 0.048, 0.050)), 0.020)  # deltoid
        d = sdf.smin(d, sdf.sphere(p, R.S + R.latu * 0.004 - R.bu * 0.004, 0.047), 0.02)                         # shoulder cap
        return d
    return f


def finger_sdf(R, name, grow=0.0):
    c = R.chain[name]
    P, r, dv = c["P"], c["r"] + grow, c["dors"]
    flat = 0.90 if name != "thumb" else 0.92

    def f(p):
        # flatten the section front to back: scale the dorsal component about the chain
        off = ((p - P[0]) @ dv)
        q = p + ((1.0 / flat) - 1.0) * off[:, None] * dv[None]
        Pq = P
        d = sdf.round_cone(q, Pq[0], Pq[1], r[0], r[1])
        d = np.minimum(d, sdf.round_cone(q, Pq[1], Pq[2], r[1], r[2]))
        d = np.minimum(d, sdf.round_cone(q, Pq[2], Pq[3], r[2], r[3]))
        # knuckles over the joints (dorsal) and the pulp of the fingertip (palmar)
        for j in (1, 2):
            d = sdf.smin(d, sdf.sphere(q, Pq[j] + dv * r[j] * 0.42, r[j] * 0.62), r[j] * 0.35)
        ax = _n(Pq[3] - Pq[2])
        frame = np.array([ax, np.cross(dv, ax), dv])
        d = sdf.smin(d, sdf.ellipsoid(q, Pq[2] + (Pq[3] - Pq[2]) * 0.62 - dv * r[3] * 0.32, frame,
                                       (np.linalg.norm(Pq[3] - Pq[2]) * 0.55 + r[3] * 0.4, r[3] * 0.80, r[3] * 0.62)),
                     r[3] * 0.4)
        return d
    return f


def palm_sdf(R, grow=0.0):
    W, fwd, lat, dors = R.W, R.fwd, R.lat, R.dors
    hf = np.array([fwd, lat, dors])
    mcp = R.mcp
    knuck = np.mean(list(mcp.values()), axis=0)
    span = float(np.linalg.norm(knuck - W))
    bases = {f: R.h(f + "_metacarpal") for f in FINGERS[:4]}

    def f(p):
        d = None
        for name in FINGERS[:4]:
            a = bases[name] + (W - bases[name]) * 0.25 - dors * 0.002
            b = mcp[name] + dors * 0.0015
            e = sdf.round_cone(p, a, b, 0.0098 + grow, 0.0105 + grow)
            d = e if d is None else sdf.smin(d, e, 0.009)
        slab_c = W + fwd * (span * 0.50) - dors * 0.0045
        d = sdf.smin(d, sdf.round_box(p, slab_c, hf, (span * 0.47, 0.0355 + grow, 0.0105 + grow), 0.0085), 0.008)
        # distal palmar pad along the knuckles, thenar and hypothenar eminences
        kl = _n(mcp["pinky"] - mcp["index"])
        kf = np.array([np.cross(kl, dors), kl, dors])
        d = sdf.smin(d, sdf.ellipsoid(p, knuck - fwd * 0.010 - dors * 0.0085, kf, (0.011 + grow, 0.043 + grow, 0.0085 + grow)), 0.008)
        t1, t2 = R.h("thumb_01"), R.h("thumb_02")
        ta = _n(t2 - t1)
        tf = np.array([ta, _n(np.cross(dors, ta)), _n(np.cross(ta, np.cross(dors, ta)))])
        d = sdf.smin(d, sdf.ellipsoid(p, t1 + (t2 - t1) * 0.45 - dors * 0.010 + lat * 0.010, tf, (0.031 + grow, 0.018 + grow, 0.0145 + grow)), 0.010)
        d = sdf.smin(d, sdf.ellipsoid(p, W + fwd * 0.040 + lat * 0.026 - dors * 0.008, hf, (0.032 + grow, 0.0125 + grow, 0.0125 + grow)), 0.010)
        # heel of the hand into the wrist
        s, dw = R.forearm_section(p, grow)
        dw = np.maximum(dw, -s - 0.022)
        dw = np.maximum(dw, s - 0.03)
        d = sdf.smin(d, dw, 0.014)
        return d
    return f


def hand_sdf(R, grow=0.0):
    palm = palm_sdf(R, grow)
    fingers = {n: finger_sdf(R, n, grow) for n in FINGERS}

    def f(p):
        d = palm(p)
        fd = None
        for n in FINGERS:
            k = 0.0075 if n != "thumb" else 0.011
            e = sdf.smin(d, fingers[n](p), k)
            fd = e if fd is None else np.minimum(fd, e)
        return fd
    return f


def glove_sdf(R):
    """The glove's outer surface: the hand grown by the material, the glove body up the wrist, the padded cuff
    from 4 to 42 mm with a rolled top edge, and the raised stitched panel on the back of the hand."""
    hand = hand_sdf(R, GLOVE_T)
    W, fwd, lat, dors = R.W, R.fwd, R.lat, R.dors
    hf = np.array([fwd, lat, dors])

    def f(p):
        d = hand(p)
        s, de = R.forearm_section(p)
        body = np.maximum(de - 0.0026, np.maximum(-s - 0.02, s - 0.031))
        d = sdf.smin(d, body, 0.006)
        cuff = de - 0.0050
        cuff = sdf.smax(cuff, 0.004 - s, 0.0025)
        cuff = sdf.smax(cuff, s - CUFF_TOP, 0.0025)
        d = np.minimum(d, cuff)
        ring = np.sqrt((s - (CUFF_TOP - 0.0012)) ** 2 + (de - 0.0040) ** 2) - 0.0040
        d = np.minimum(d, ring)
        # raised back panel (wrist to 64 mm ahead of it, about 58 % of the hand's width), 1 mm proud
        q = sdf.local(p, W + fwd * 0.034, hf)
        foot = sdf.rect2(q[:, 0], q[:, 1] - 0.003, 0.033, 0.0235, 0.012)
        d = sdf.smin(d, np.maximum(hand(p) - 0.0010, foot), 0.0015)
        return d
    return f


# rubber pieces ----------------------------------------------------------------------------------------------


def knuckle_bar_sdf(R, glove):
    mcp = R.mcp
    dors = R.dors
    kl = _n(mcp["pinky"] - mcp["index"])
    mid = np.mean(list(mcp.values()), axis=0)
    kf = np.array([_n(np.cross(kl, dors)), kl, dors])

    def f(p):
        g = glove(p)
        layer = np.maximum(g - 0.0042, -g - 0.002)
        q = sdf.local(p, mid, kf)
        foot = sdf.rect2(q[:, 0] + 0.002, q[:, 1], 0.010, 0.043, 0.008)
        up = -q[:, 2] - 0.0                                       # dorsal half only
        d = sdf.smax(layer, foot, 0.0016)
        d = sdf.smax(d, up, 0.002)
        for n in FINGERS[:4]:
            c = mcp[n] + dors * (R.chain[n]["r"][0] + GLOVE_T + 0.004) - kf[0] * 0.001
            d = sdf.smin(d, sdf.ellipsoid(p, c, kf, (0.0068, 0.0078, 0.0042)), 0.0028)
        return d
    return f


def strap_sdf(R, glove):
    c0, u, v = R.fore_frame(0.020)
    fr = np.array([-R.af, u, v])

    def f(p):
        g = glove(p)
        layer = np.maximum(g - 0.0028, -g - 0.0015)
        q = sdf.local(p, c0, fr)
        foot = sdf.rect2(q[:, 0], q[:, 1] + 0.004, 0.012, 0.020, 0.0045)     # 24 along x 40 across
        d = sdf.smax(layer, foot, 0.0012)
        d = sdf.smax(d, -q[:, 2], 0.002)                                       # back of the wrist only
        # pull tab on the thumb side
        tab = sdf.rect2(q[:, 0], q[:, 1] + 0.027, 0.007, 0.006, 0.004)
        d = np.minimum(d, sdf.smax(np.maximum(g - 0.0036, -g - 0.0015), np.maximum(tab, -q[:, 2]), 0.0012))
        return d
    return f


def pad_sdf(R, glove, n):
    def f(p):
        d = None
        g = glove(p)
        layer = np.maximum(g - 0.0016, -g - 0.0015)
        for n_ in (n,):
            c = R.chain[n]
            P, dv = c["P"], c["dors"]
            ax = _n(P[3] - P[2])
            side = _n(np.cross(dv, ax))
            ctr = P[2] + (P[3] - P[2]) * 0.55
            q = sdf.local(p, ctr, np.array([ax, side, dv]))
            L = np.linalg.norm(P[3] - P[2])
            foot = sdf.rect2(q[:, 0], q[:, 1], L * 0.5 + c["r"][3] * 0.55, c["r"][3] * 0.78, c["r"][3] * 0.7)
            e = sdf.smax(sdf.smax(layer, foot, 0.0008), q[:, 2] + c["r"][3] * 0.15, 0.0015)
            d = e if d is None else np.minimum(d, e)
        return d
    return f


# ------------------------------------------------------------------------------------------------ meshing


def mesh_field(name, f, centre, frame, half, h, col, relax=3):
    v, q = sdf.surface_nets(f, -np.asarray(half), np.asarray(half), h, frame=frame, origin=centre)
    v, q = sdf.keep_largest(v, q)
    v = sdf.project(f, v, 3)
    v = sdf.relax(f, v, q, relax, 0.45)
    return sdf.to_mesh(name, v, q, col)


def mesh_piece(name, f, pts, frame, pad, col, h=PIECE_H):
    pts = np.asarray(pts)
    loc = (pts - pts.mean(axis=0)) @ np.asarray(frame).T
    lo, hi = loc.min(axis=0) - pad, loc.max(axis=0) + pad
    ctr = pts.mean(axis=0) + ((lo + hi) / 2) @ np.asarray(frame)
    return mesh_field(name, f, ctr, frame, (hi - lo) / 2, h, col, relax=2)


def arm_box(R):
    """Oriented box around the whole arm (shoulder to fingertips): frame rows and half extents."""
    tips = np.array([R.chain[n]["P"][3] for n in FINGERS])
    pts = np.vstack([R.S, R.E, R.W, tips, R.S + R.latu * 0.06, R.S - R.latu * 0.06])
    return pts


def delete_faces(ob, mask):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(mask)[0]], context="FACES")
    bm.to_mesh(ob.data)
    bm.free()


def face_centres(ob):
    me = ob.data
    c = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get("center", c)
    return c.reshape(-1, 3)


def build_right_arm(R, col):
    """Skin, glove and rubber pieces of the right arm as separate objects (rest pose)."""
    out = {}
    fs = skin_sdf(R)
    lo = np.minimum.reduce([R.S, R.E, R.W]) - 0.075
    hi = np.maximum.reduce([R.S, R.E, R.W]) + 0.075
    c = (lo + hi) / 2
    out["skin"] = mesh_field("Skin_R", fs, c, np.eye(3), (hi - lo) / 2, SKIN_H, col)
    s, _ = R.forearm_section(face_centres(out["skin"]))
    delete_faces(out["skin"], s < SKIN_CUT)
    fg = glove_sdf(R)
    hf = np.array([R.fwd, R.lat, R.dors])
    tips = np.array([R.chain[n]["P"][3] for n in FINGERS])
    loc = (tips - R.W) @ hf.T
    lo = np.minimum(loc.min(axis=0), [-0.06, -0.06, -0.05]) - 0.02
    hi = np.maximum(loc.max(axis=0), [0.0, 0.05, 0.04]) + 0.02
    ctr = R.W + ((lo + hi) / 2) @ hf
    out["glove"] = mesh_field("Glove_R", fg, ctr, hf, (hi - lo) / 2, GLOVE_H, col)
    cen = face_centres(out["glove"])
    s, de = R.forearm_section(cen)
    delete_faces(out["glove"], (de < -0.0015) & (s > 0.0))           # the cuff's top face inside the skin
    for name, fn, pts, pad in (
            ("KnuckleBar_R", knuckle_bar_sdf, list(R.mcp.values()), 0.022),
            ("Strap_R", strap_sdf, [R.fore_frame(0.020)[0]], 0.042)):
        out[name] = mesh_piece(name, fn(R, fg), pts, hf, pad, col)
    pads = []
    for n in FINGERS:
        P = R.chain[n]["P"]
        pads.append(mesh_piece("Pad_%s_R" % n, pad_sdf(R, fg, n), [P[2], P[3]], hf, 0.018, col))
    out["pads"] = geo.join(pads, "Pads_R", col)
    return out


def build(ctx):
    if ctx.want("roundtrip") and ctx.args.only and "roundtrip" in ctx.args.only:
        return roundtrip(ctx)
    arm, body = char.import_mannequin()
    R = ArmRig(arm, body)
    ctx.log("arm: forearm %.3f m, upper arm %.3f m, twist %.1f deg" % (R.L, R.Lu, math.degrees(R.twist)))
    parts = build_right_arm(R, ctx.col)
    for k, ob in parts.items():
        if ob is not None:
            ctx.log("%s: %d faces" % (k, len(ob.data.polygons)))
    return [o for o in parts.values() if o is not None]


def roundtrip(ctx):
    arm, body = char.import_mannequin()
    p = char.export_character(body, arm, name="RT_Manny", path=os.path.join(char.EPIC, "RT_Manny.glb"), stub_materials=False)
    rep = char.round_trip_report(char.MANNEQUIN, p)
    ctx.log("round trip: " + json.dumps(rep, default=str))
    return []
