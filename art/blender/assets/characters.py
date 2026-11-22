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
PIECE_H = 0.0008         # of the rubber pieces
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
        ring = np.sqrt((s - (CUFF_TOP - 0.0016)) ** 2 + (de - 0.0042) ** 2) - 0.0026
        d = sdf.smin(d, ring, 0.0012)
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
    lo = np.minimum.reduce([R.S, R.E, R.W, R.S + R.bu * 0.07]) - 0.075
    hi = np.maximum.reduce([R.S, R.E, R.W, R.S + R.bu * 0.07]) + 0.075
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


TRI_BUDGET = {"skin": 12000, "glove": 34000, "KnuckleBar_R": 3000, "Strap_R": 1600, "pads": 3600}
SLOTS = {"skin": "M_RuleArms_Skin", "leather": "M_RuleArms_GloveLeather", "suede": "M_RuleArms_GloveSuede",
         "rubber": "M_RuleArms_Rubber"}


def decimate(ob, tris):
    n = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if n <= tris:
        return ob
    md = ob.modifiers.new("dec", "DECIMATE")
    md.decimate_type = "COLLAPSE"
    md.ratio = tris / n
    md.use_collapse_triangulate = True
    geo._apply_modifier(ob, md)
    return ob


def verts(ob):
    co = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def finger_frame_coords(R, n, p):
    """Nearest point on finger n's chain: (distance from the axis, dorsal cosine, t along the chain in metres)."""
    P = R.chain[n]["P"]
    best = None
    t0 = 0.0
    for i in range(3):
        a, b = P[i], P[i + 1]
        ab = b - a
        L = np.linalg.norm(ab)
        t = np.clip(((p - a) @ ab) / (L * L), 0, 1)
        q = a + t[:, None] * ab
        d = np.linalg.norm(p - q, axis=1)
        tt = t0 + t * L
        if best is None:
            best = [d, q, tt]
        else:
            m = d < best[0]
            best[0][m], best[1][m], best[2][m] = d[m], q[m], tt[m]
        t0 += L
    r = p - best[1]
    cosd = (r @ R.chain[n]["dors"]) / np.maximum(np.linalg.norm(r, axis=1), 1e-9)
    return best[0], cosd, best[2]


def glove_regions(R, p):
    """Per point: label (0 hand/cuff, 1..5 finger), dorsal (bool), cuff (bool)."""
    palm = palm_sdf(R, GLOVE_T)(p)
    lab = np.zeros(len(p), dtype=np.int64)
    best = palm - 0.0015
    dors = ((p - R.W) @ R.dors) > -0.0035
    for i, n in enumerate(FINGERS):
        fd = finger_sdf(R, n, GLOVE_T)(p)
        m = fd < best
        lab[m] = i + 1
        best = np.where(m, fd, best)
        _, cosd, _ = finger_frame_coords(R, n, p[m])
        dors[m] = cosd > 0
    s, x, y = R.fore_coords(p)
    cuff = s > 0.004
    dors[cuff] = y[cuff] > 0
    return lab, dors, cuff


def source_labels(body, side="r"):
    """Mannequin vertices: 1..5 dominated by a finger's bones, 0 by another bone of the arm, -1 elsewhere."""
    names, W = char.weight_matrix(body)
    dom = np.array(names)[W.argmax(axis=1)]
    lab = -np.ones(len(dom), dtype=np.int64)
    lab[np.isin(dom, char.ARM_BONES[side])] = 0
    for i, n in enumerate(FINGERS):
        bones = ["%s_%s_%s" % (n, k, side) for k in ("01", "02", "03")]
        lab[np.isin(dom, bones)] = i + 1
    return lab


def skin_seams(R, ob):
    """Cut the arm tube along the ulnar border (forearm) and the medial side (upper arm), and around the
    shoulder cap."""
    p = verts(ob)
    s, x, y = R.fore_coords(p)
    su, xu, yu = R.upper_coords(p)
    up = s > R.L + 0.01
    ang = np.where(up, np.arctan2(yu, -xu), np.arctan2(y, x))      # branch cut at +u (ulnar) / -latu (medial)
    cap = su > R.Lu - 0.035
    me = ob.data
    e = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    jump = np.abs(ang[e[:, 0]] - ang[e[:, 1]]) > np.pi
    near = np.minimum(np.abs(ang[e[:, 0]]), np.abs(ang[e[:, 1]])) > np.pi / 2
    ring = cap[e[:, 0]] != cap[e[:, 1]]
    return (jump & near & ~cap[e[:, 0]]) | ring


def set_material_ids(ob, mats, ids):
    me = ob.data
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", np.asarray(ids, dtype=np.int32))


def flat_material(name, colour, rough, sheen=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = rough
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
    return m


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def materials():
    return {"skin": flat_material(SLOTS["skin"], srgb("#684029"), 0.48),
            "leather": flat_material(SLOTS["leather"], srgb("#1e1f22"), 0.42),
            "suede": flat_material(SLOTS["suede"], srgb("#2a2724"), 0.85, sheen=0.4),
            "rubber": flat_material(SLOTS["rubber"], srgb("#18181b"), 0.62)}


def assemble_right(R, arm, body, parts, col, log=print):
    """Decimate, label, UV, material ids and weights of the right arm's parts; returns (skin, glove) objects
    (the glove object carries the rubber pieces)."""
    mats = materials()
    for k, ob in parts.items():
        decimate(ob, TRI_BUDGET[k])
    skin, glove = parts["skin"], parts["glove"]
    pieces = [parts["KnuckleBar_R"], parts["Strap_R"], parts["pads"]]
    # skin
    char.uv_from_seams(skin, skin_seams(R, skin), method="ANGLE_BASED")
    set_material_ids(skin, [mats["skin"]], np.zeros(len(skin.data.polygons)))
    # glove: panels (dorsal = leather back, palmar = suede palm), the cuff in leather
    fc = face_centres(glove)
    lab, dors, cuff = glove_regions(R, fc)
    panel = np.where(dors, 0, 1)
    char.uv_from_seams(glove, char.seams_between(glove, panel), method="ANGLE_BASED", pack=False)
    set_material_ids(glove, [mats["leather"], mats["suede"], mats["rubber"]], np.where(dors | cuff, 0, 1))
    for pc in pieces:
        _smart_uv(pc)
        set_material_ids(pc, [mats["leather"], mats["suede"], mats["rubber"]], np.full(len(pc.data.polygons), 2))
    # weights: from the mannequin's own arm, per finger
    sl = source_labels(body, R.side)
    bones = char.ARM_BONES[R.side]
    for ob, labels in ((skin, np.zeros(len(skin.data.vertices), dtype=np.int64)),
                       (glove, glove_regions(R, verts(glove))[0]),
                       (parts["KnuckleBar_R"], np.zeros(len(parts["KnuckleBar_R"].data.vertices), dtype=np.int64)),
                       (parts["Strap_R"], np.zeros(len(parts["Strap_R"].data.vertices), dtype=np.int64)),
                       (parts["pads"], glove_regions(R, verts(parts["pads"]))[0])):
        names, W = char.transfer_weights(ob, body, bones, limit=6, target_labels=labels, source_labels=sl)
        char.smooth_weights(ob, iterations=3, strength=0.4, limit=6, names=names, W=W)
        log("weights %s: %d vertices" % (ob.name, len(ob.data.vertices)))
    # face attributes for the texel patterns: finger label, back/palm, piece
    for ob, piece in ((glove, 0), (parts["KnuckleBar_R"], 1), (parts["Strap_R"], 2), (parts["pads"], 3)):
        lab_f, dors_f, _cuff = glove_regions(R, face_centres(ob))
        for nm, val in (("mi_label", lab_f), ("mi_dors", dors_f), ("mi_piece", np.full(len(lab_f), piece))):
            a = ob.data.attributes.get(nm) or ob.data.attributes.new(nm, "FLOAT", "FACE")
            a.data.foreach_set("value", np.asarray(val, dtype=np.float32))
    glove = geo.join([glove] + pieces, "Glove_R", col)
    _pack_uv(glove)
    return skin, glove


TEX_DIR = lambda set_name: paths.texture_set(set_name)


def bake_sets(R, skin, glove, res=4096, log=print):
    """The two unique 4K sets: RuleArms_Skin (slot M_RuleArms_Skin) and RuleArms_Glove (leather, suede and
    rubber slots), computed per texel from the right arm's rest positions."""
    from assets import _characters_tex as X
    from mi import bake as _bake, texel
    out = {}
    for ob, set_name in ((skin, "RuleArms_Skin"), (glove, "RuleArms_Glove")):
        attrs = ["mi_label", "mi_dors", "mi_piece"] if ob is glove else []
        maps = texel.bake_maps(ob, res, face_attrs=attrs)
        log("  %s: maps baked, coverage %.1f %%" % (set_name, 100 * maps["mask"].mean()))
        H, W = maps["mask"].shape
        idx = np.nonzero(maps["mask"].ravel())[0]
        bc = np.zeros((H * W, 3), dtype=np.float32)
        ro = np.full(H * W, 0.5, dtype=np.float32)
        hh = np.zeros(H * W, dtype=np.float32)
        Pf, Nf = maps["pos"].reshape(-1, 3), maps["normal"].reshape(-1, 3)
        for sl in texel.chunks(idx, 1_000_000):
            P, N = Pf[sl].astype(np.float64), Nf[sl]
            if ob is skin:
                c, r, h = X.skin_texels(R, P, N)
            else:
                c, r, h = X.glove_texels(R, P, N, maps["slot"].ravel()[sl], np.rint(maps["mi_label"].ravel()[sl]).astype(int),
                                         maps["mi_dors"].ravel()[sl], np.rint(maps["mi_piece"].ravel()[sl]).astype(int))
            bc[sl], ro[sl], hh[sl] = c, r, h
        mask = maps["mask"]
        hh = hh.reshape(H, W)
        hd = texel.dilate(hh, mask, 4)
        nrm = texel.normal_from_height(hd, maps["pos"], mask)
        cav = np.clip(texel.blur(hd, 3) - hd, 0, None)
        ao = np.clip(1.0 - cav / 0.00025, 0.55, 1.0)
        aol = _bake._bake_ao(ob, 1024, 16, 0, 0.03, False)
        aol = np.kron(aol, np.ones((H // 1024, W // 1024), dtype=np.float32))
        ao = ao * (0.35 + 0.65 * aol)
        ch = {"bc": texel.dilate(bc.reshape(H, W, 3), mask, 24), "rough": texel.dilate(ro.reshape(H, W), mask, 24),
              "metal": np.zeros((H, W), dtype=np.float32), "normal": texel.dilate(nrm, mask, 24),
              "ao": texel.dilate(ao, mask, 24), "height": hd}
        info = _bake.write_set(set_name, ch, meta={"kind": "unique", "asset": "SK_RuleArms", "resolution_px": res})
        log("  %s written: %s" % (set_name, info["files"]))
        out[set_name] = info
        del maps, bc, ro, hh, ch
    return out


def textured_materials():
    """Preview materials on the baked sets (Unreal builds its own: skin with a subsurface profile)."""
    from mi import mat as _mat
    res = {}
    for key, set_name, sss, sheen in (("skin", "RuleArms_Skin", 0.35, 0.0), ("leather", "RuleArms_Glove", 0.0, 0.0),
                                      ("suede", "RuleArms_Glove", 0.0, 0.5), ("rubber", "RuleArms_Glove", 0.0, 0.0)):
        name = SLOTS[key]
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        nt = m.node_tree
        for nd in list(nt.nodes):
            nt.nodes.remove(nd)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(b.outputs[0], out.inputs["Surface"])
        d = paths.texture_set(set_name)
        def img(tag, data):
            t = nt.nodes.new("ShaderNodeTexImage")
            t.image = bpy.data.images.load(os.path.join(d, "T_%s_%s.png" % (set_name, tag)), check_existing=True)
            t.image.colorspace_settings.name = "Non-Color" if data else "sRGB"
            return t
        bc, nm, orm = img("BC", False), img("N", True), img("ORM", True)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs[0])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(bc.outputs["Color"], mix.inputs["A"])
        nt.links.new(sep.outputs["Red"], mix.inputs["B"])
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
        nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(nm.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], b.inputs["Normal"])
        if sss:
            b.inputs["Subsurface Weight"].default_value = sss
            b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.15)
            b.inputs["Subsurface Scale"].default_value = 0.004
        if sheen:
            b.inputs["Sheen Weight"].default_value = sheen
            b.inputs["Sheen Roughness"].default_value = 0.6
        res[key] = m
    return res


def _smart_uv(ob):
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    scene.select_only(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def _pack_uv(ob, margin=0.003):
    scene.select_only(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin_method="FRACTION", margin=margin, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")


def build(ctx):
    if ctx.args.only and "roundtrip" in ctx.args.only:
        return roundtrip(ctx)
    if ctx.args.only and "textures" in ctx.args.only:
        return textures_only(ctx)
    arm, body = char.import_mannequin()
    body.hide_render = True
    R = ArmRig(arm, body)
    ctx.log("arm: forearm %.3f m, upper arm %.3f m, twist %.1f deg" % (R.L, R.Lu, math.degrees(R.twist)))
    parts = build_right_arm(R, ctx.col)
    ctx.log("fields meshed")
    skin, glove = assemble_right(R, arm, body, parts, ctx.col, ctx.log)
    keep = scene.collection("Parts_R")
    for o in (skin, glove):
        c = o.copy()
        c.data = o.data.copy()
        c.name = o.name + "_Keep"
        keep.objects.link(c)
        c.hide_render = True
        c.hide_set(True)
    if ctx.args.bake:
        bake_sets(R, skin, glove, ctx.args.res, ctx.log)
    if os.path.exists(os.path.join(paths.texture_set("RuleArms_Glove"), "T_RuleArms_Glove_BC.png")):
        textured_materials()
    skin_l = char.mirror_x(skin, "Skin_L")
    glove_l = char.mirror_x(glove, "Glove_L")
    ob = geo.join([skin, glove, skin_l, glove_l], "SK_RuleArms", ctx.col)
    geo.weighted_normals(ob, weight=50, keep_sharp=False)
    from mi import rig
    rig.bind(ob, arm)
    ctx.log("SK_RuleArms: %d triangles" % sum(len(p.vertices) - 2 for p in ob.data.polygons))
    ctx.rule = dict(R=R, arm=arm, body=body, ob=ob)
    return [ob]


def on_export(ctx, objs):
    r = getattr(ctx, "rule", None)
    if not r:
        return
    p = char.export_character(r["ob"], r["arm"])
    ctx.log("exported %s" % p)


def textures_only(ctx):
    """Re-bake the two sets from the right-arm parts kept in art/out/blend/characters.blend (no remodelling)."""
    src = os.path.join(paths.blend, "characters.blend")
    with bpy.data.libraries.load(src, link=False) as (fr, to):
        to.objects = [n for n in fr.objects if n in ("Skin_R_Keep", "Glove_R_Keep", "Mannequin", "Mannequin_Body")]
    for o in to.objects:
        ctx.col.objects.link(o)
    arm, body = bpy.data.objects["Mannequin"], bpy.data.objects["Mannequin_Body"]
    R = ArmRig(arm, body)
    skin, glove = bpy.data.objects["Skin_R_Keep"], bpy.data.objects["Glove_R_Keep"]
    for o in (skin, glove):
        o.hide_render = False
        o.parent = None
        o.modifiers.clear()
    ctx.args.export = False
    bake_sets(R, skin, glove, ctx.args.res, ctx.log)
    ctx.args.preview = False
    import tempfile
    paths.blend = tempfile.mkdtemp()          # build.py saves the scene afterwards: keep characters.blend intact
    return []


def roundtrip(ctx):
    arm, body = char.import_mannequin()
    p = char.export_character(body, arm, name="RT_Manny", path=os.path.join(char.EPIC, "RT_Manny.glb"), stub_materials=False)
    rep = char.round_trip_report(char.MANNEQUIN, p)
    ctx.log("round trip: " + json.dumps(rep, default=str))
    return []


# ------------------------------------------------------------------------------------------------ watch, bracelet

GOLD = (1.0, 0.766, 0.336)                 # linear reflectance of yellow gold (#e7b53a reads as this under light)
GOLD_DARK = (0.80, 0.58, 0.20)


def jewel_materials():
    from mi import mat as _mat
    gold = _mat.flat("M_Character_RuleWatch_Gold", GOLD, 0.16, 1.0)
    brushed = _mat.flat("M_Character_RuleWatch_GoldBrushed", GOLD, 0.34, 1.0)
    dark = _mat.flat("M_Character_RuleWatch_GoldDark", GOLD_DARK, 0.42, 1.0)
    dial = _mat.flat("M_Character_RuleWatch_Dial", (0.003, 0.003, 0.0035), 0.07, 0.0)
    glass = _mat.flat("M_Character_RuleWatch_Glass", (1, 1, 1), 0.0, 0.0)
    b = glass.node_tree.nodes.get("Principled BSDF")
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.77
    chain = _mat.flat("M_Character_RuleBracelet_Gold", GOLD, 0.14, 1.0)
    chain2 = _mat.flat("M_Character_RuleBracelet_GoldAlt", (0.93, 0.70, 0.30), 0.18, 1.0)
    return dict(gold=gold, brushed=brushed, dark=dark, dial=dial, glass=glass, chain=chain, chain2=chain2)


def _mat_all(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


def _ellipse_path(a, b, n, sag=0.0):
    """Closed path around the forearm in the local frame (X across, Z outward on the back, Y along the arm):
    points on an ellipse x = a cos t, z = b sin t, sagging `sag` underneath (z < 0)."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x, z = a * np.cos(t), b * np.sin(t)
    z = z - sag * np.clip(-np.sin(t), 0, 1) ** 2
    return np.stack([x, np.zeros_like(x), z], axis=1), t


def watch(col, sec=(0.0352, 0.0279)):
    """SM_Character_RuleWatch in its attach frame: origin on the forearm axis, X across the arm, Y along it
    (toward the elbow), Z out of the back of the forearm. sec: semi-axes of the forearm section under it."""
    M = jewel_materials()
    a, b = sec[0] + 0.0010, sec[1] + 0.0010              # band inner surface 1 mm off the skin
    parts = []
    # band: three-piece links (outer pieces brushed, centre polished), 44 segments around the arm
    n = 44
    pts, t = _ellipse_path(a + 0.0012, b + 0.0012, n)
    case_half = 0.0205
    for i in range(n):
        p0, p1 = pts[i], pts[(i + 1) % n]
        mid = (p0 + p1) / 2
        if abs(mid[0]) < case_half and mid[2] > 0:
            continue                                         # under the case
        tang = p1 - p0
        L = float(np.linalg.norm(tang)) - 0.0004
        ang = math.degrees(math.atan2(tang[2], tang[0]))
        for y0, w, m in ((-0.0065, 0.0058, M["brushed"]), (0.0, 0.0064, M["gold"]), (0.0065, 0.0058, M["brushed"])):
            bx = geo.box((L, w, 0.0024), bevel=0.0005, segments=2, base=False, name="Link")
            geo.transform(bx, rot=(0, -ang, 0))
            geo.transform(bx, loc=(mid[0], y0, mid[2]))
            parts.append(_mat_all(bx, m))
    # case, bezel, dial, glass, hands, batons, crown (built with 12 o'clock at +Y, then turned so the crown at
    # 3 o'clock points toward the hand, -Y), lugs
    band = len(parts)
    z0 = b + 0.0018
    case = geo.revolve([(0.0, 0.0), (0.0185, 0.0), (0.0195, 0.0012), (0.0195, 0.0060), (0.0190, 0.0068), (0.0, 0.0068)],
                       segments=96, name="Case")
    geo.transform(case, loc=(0, 0, z0))
    parts.append(_mat_all(case, M["gold"]))
    bez_prof = [(0.0170, 0.0066), (0.0212, 0.0066), (0.0212, 0.0074), (0.0205, 0.0083), (0.0185, 0.0086),
                (0.0172, 0.0084), (0.0170, 0.0066)]
    bez = geo.revolve(bez_prof, segments=120, closed=True, name="Bezel")
    geo.transform(bez, loc=(0, 0, z0))
    parts.append(_mat_all(bez, M["gold"]))
    dial = geo.cylinder(0.0172, 0.0004, 96, name="Dial")
    geo.transform(dial, loc=(0, 0, z0 + 0.0062))
    parts.append(_mat_all(dial, M["dial"]))
    for k in range(4):
        ang = k * 90
        bt = geo.box((0.0012, 0.0048, 0.0005), bevel=0.0002, segments=1, base=True, name="Baton")
        geo.transform(bt, loc=(0, 0.0138 if k != 0 else 0.0136, z0 + 0.0066))
        if k == 0:
            bt2 = geo.box((0.0012, 0.0048, 0.0005), bevel=0.0002, segments=1, base=True, name="Baton")
            geo.transform(bt, loc=(-0.0011, 0, 0))
            geo.transform(bt2, loc=(0.0011, 0.0136, z0 + 0.0066))
            parts.append(_mat_all(bt2, M["gold"]))
        geo.transform(bt, rot=(0, 0, -ang))
        parts.append(_mat_all(bt, M["gold"]))
    for L, w, ang, dz in ((0.012, 0.0011, -62, 0.0074), (0.009, 0.0014, 118, 0.0071)):     # 10:10 like a catalogue
        hd = geo.box((w, L, 0.0003), bevel=0.0001, segments=1, base=True, name="Hand")
        geo.transform(hd, loc=(0, L / 2 - 0.0015, z0 + dz - 0.0004))
        geo.transform(hd, rot=(0, 0, ang))
        parts.append(_mat_all(hd, M["gold"]))
    pin = geo.cylinder(0.0009, 0.0011, 24, name="Pinion")
    geo.transform(pin, loc=(0, 0, z0 + 0.0066))
    parts.append(_mat_all(pin, M["gold"]))
    glass = geo.revolve([(0.0, 0.0), (0.0171, 0.0), (0.0171, 0.0010), (0.0120, 0.0016), (0.0, 0.0019)], segments=96,
                        name="Glass")
    geo.transform(glass, loc=(0, 0, z0 + 0.0074))
    parts.append(_mat_all(glass, M["glass"]))
    crown = geo.revolve([(0.0, 0.0), (0.0028, 0.0), (0.0028, 0.0030), (0.0024, 0.0035), (0.0, 0.0035)], segments=36,
                        name="Crown")
    geo.transform(crown, rot=(0, 90, 0))
    geo.transform(crown, loc=(0.0193, 0, z0 + 0.0034))
    parts.append(_mat_all(crown, M["gold"]))
    for pt in parts[band:]:
        geo.transform(pt, rot=(0, 0, -90))
    for sx in (-1, 1):
        for sy in (-1, 1):
            lug = geo.box((0.0045, 0.0060, 0.0040), bevel=0.0008, segments=2, base=False, name="Lug")
            geo.transform(lug, loc=(sx * 0.0068, sy * 0.0185, z0 + 0.0022))
            parts.append(_mat_all(lug, M["gold"]))
    ob = geo.join(parts, "SM_Character_RuleWatch", col)
    geo.smooth_by_angle(ob, 40)
    return ob


def bracelet(col, sec=(0.0335, 0.0265)):
    """SM_Character_RuleBracelet: 26 twisted curb links on a path 3.6 mm clear of the forearm, sagging 2.8 mm
    underneath; same attach frame convention as the watch."""
    M = jewel_materials()
    a, b = sec[0] + 0.0036 + 0.0019, sec[1] + 0.0036 + 0.0019
    n = 26
    pts, t = _ellipse_path(a, b, 400, sag=0.0028)
    seg = np.linalg.norm(np.roll(pts, -1, axis=0) - pts, axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    total = cum[-1]
    parts = []
    for i in range(n):
        d = (i + 0.5) / n * total
        k = int(np.searchsorted(cum, d) - 1) % len(pts)
        p0, p1 = pts[k], pts[(k + 1) % len(pts)]
        mid = p0 + (p1 - p0) * ((d - cum[k]) / max(seg[k], 1e-9))
        tang = (p1 - p0) / max(seg[k], 1e-9)
        lk = geo.torus(major=0.0024, minor=0.00092, seg_major=28, seg_minor=10, name="Link",
                       stretch=total / n * 1.45 - 0.0048)
        geo.transform(lk, scale=(1.0, 1.0, 0.72))                 # curb links are pressed flat
        geo.transform(lk, rot=(28 if i % 2 else -28, 0, 0))       # each twisted against the next
        ang = math.degrees(math.atan2(tang[2], tang[0]))
        geo.transform(lk, rot=(0, -ang, 0))
        geo.transform(lk, loc=tuple(mid))
        parts.append(_mat_all(lk, M["chain"] if i % 2 == 0 else M["chain2"]))
    ob = geo.join(parts, "SM_Character_RuleBracelet", col)
    return ob


def attach_frame(R, s):
    """World matrix of a jewel's attach frame at s above the wrist: origin on the forearm axis, X across the arm
    (ulnar), Y toward the elbow, Z out of the back of the forearm."""
    c, u, v = R.fore_frame(s)
    y = -R.af
    x = np.cross(y, v)
    M = Matrix.Identity(4)
    for i in range(3):
        M[i][0], M[i][1], M[i][2], M[i][3] = x[i], y[i], v[i], c[i]
    return M
