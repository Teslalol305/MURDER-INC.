"""Adapt the Tactical FPS Animation Pack's assault-rifle clips to the CHOPPER (run inside the editor of the scratch
project, or of the game project after ue_import_pack.py; see docs/unreal/ANIMATION.md).

The pack is authored on SK_Mannequin with the rifle hanging from ik_hand_gun (identity). Every clip is read with
AnimPose (component space), changed with our own transform maths and written as a new AnimSequence on the same
skeleton (no retargeting):

- gun: ik_hand_gun becomes the CHOPPER's origin (forward +X, right +Y, up +Z, cm) at M = (CHOP_IN_PACK) in the pack
  gun's space, so SK_Chopper attaches to ik_hand_gun with an identity transform. M puts the pack's right palm on our
  pistol grip at the socket Palm_R (the right hand is never moved).
- aimed clips: a fixed gun-space correction Dg lines our sights (SightRear, SightFront) up on the pack's sight line,
  i.e. on the first-person eye (EYE_CS); both hands follow by two-bone IK.
- left hand: two-bone IK to targets in our gun space: on the handguard at Palm_L's station; in the reloads it works
  our magazine (rock out and in about MagHinge, 24 deg), carries it, brings the fresh one, and works the LEFT-side
  charging handle (press check, rack), on the rules' marks (spec 02 2.3, 3.17), retimed piecewise from the pack.
- weapon parts: a matching SK_Chopper clip (bolt, trigger, selector, magazine bone) and float curves on the
  character clip (Chopper_Bolt, Chopper_MagVisible, Chopper_MagInHand, Chopper_MagRock).

Transforms here are (t, q): t a 3-tuple in cm, q a unit quaternion (x, y, z, w) with Unreal's rotate formula;
compose(parent, local) is the world of a child, like FTransform local * parent.
"""
import json
import math
import os

import unreal

PACK = "/Game/ThirdParty/InfimaTFA"
OUT = PACK + "/Adapted"
SKELETON = "/Game/Characters/Mannequins/Meshes/SK_Mannequin"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
CHOPPER = "/Game/Weapons/Chopper/SK_Chopper"
ASSETS = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
WS = unreal.AnimPoseSpaces.WORLD
LS = unreal.AnimPoseSpaces.LOCAL
FPS = 30

# ---------------------------------------------------------------- the CHOPPER (docs/unreal/spec/assets/weapons.json)
# Unreal cm in the gun's space: X forward (muzzle), Y right, Z up; origin on the bore at the back of the receiver.
CH = {
    "Palm_R": (4.0, 1.55, -8.5), "Palm_L": (31.5, 0.0, -6.15), "MagHinge": (22.2, 0.0, -4.0),
    "SightRear": (2.35, 0.0, 5.55), "SightFront": (40.9, 0.0, 5.55), "Knob": (18.0, -3.8, 1.45),
    "Trigger": (10.8, 0.0, -3.8), "Muzzle": (49.75, 0.0, 0.0), "Eject": (15.0, 1.9, 1.8),
    "bolt_travel": 9.2, "mag_deg": 24.0, "trigger_deg": 19.5,
}
# Where the palm centre (mean of the hand's metacarpal and knuckle joints) goes, in the CHOPPER's space:
PALM_R_TARGET = (4.0, 3.55, -8.5)          # Palm_R, 2 cm out of the grip's right face (the palm's flesh)
PALM_L_TARGET = (31.5, -3.6, -3.4)         # Palm_L's station; the pack's C-grip wrap of the lower left handguard
# The pack's rifle (its own skeleton, cm, in ik_hand_gun space: forward +Y, left +X, up +Z)
PK = {"palm_l": (3.43, 28.38, 0.62), "palm_r": (-3.48, -4.16, -6.2), "Magazine": (0.0, 12.27, -7.02),
      "Bolt_Catch": (1.64, 7.55, 1.91), "Sight_Rear": (0.0, 1.94, 6.74), "Sight_Front": (0.0, 39.68, 6.74)}
# Corresponding grip frames on the two magazines (where the left hand holds a seated magazine), gun space
PACK_MAG_FRAME = ((0.0, 12.27, -7.02), "yaw90")
OUR_MAG_FRAME = ((22.5, 0.0, -11.0), 8.0)          # position, pitch (deg): the curved body leans forward there
PACK_BC_FRAME = ((1.64, 7.55, 1.91), "yaw90")
OUR_KNOB_FRAME = ((18.0, -3.8, 1.45), 0.0)
EYE_CS = (-5.06, 0.66, 157.55)     # first-person eye, component space: the pack's sight line at the head joint's depth
EYE_RELIEF = 16.0                   # cm from the eye to SightRear when aimed (spec 02 2.13)


# ---------------------------------------------------------------- small transform maths
def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vmul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def vlen(a):
    return math.sqrt(dot(a, a))


def vnorm(a):
    n = vlen(a)
    return vmul(a, 1.0 / n) if n > 1e-9 else (0.0, 0.0, 0.0)


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qconj(q):
    return (-q[0], -q[1], -q[2], q[3])


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q))
    return tuple(c / n for c in q)


def qrot(q, v):
    u = (q[0], q[1], q[2])
    w = q[3]
    t = vmul(cross(u, v), 2.0)
    return vadd(vadd(v, vmul(t, w)), cross(u, t))


def qaxis(axis, deg):
    a = math.radians(deg) * 0.5
    ax = vnorm(axis)
    s = math.sin(a)
    return (ax[0] * s, ax[1] * s, ax[2] * s, math.cos(a))


def qbetween(a, b):
    a, b = vnorm(a), vnorm(b)
    c = cross(a, b)
    d = dot(a, b)
    if d < -0.999999:
        perp = cross(a, (1, 0, 0)) if abs(a[0]) < 0.9 else cross(a, (0, 1, 0))
        return qaxis(perp, 180.0)
    return qnorm((c[0], c[1], c[2], 1.0 + d))


def qslerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b = tuple(-x for x in b)
        d = -d
    if d > 0.9995:
        return qnorm(tuple(x + (y - x) * t for x, y in zip(a, b)))
    th = math.acos(min(1.0, d))
    s = math.sin(th)
    wa, wb = math.sin((1 - t) * th) / s, math.sin(t * th) / s
    return tuple(wa * x + wb * y for x, y in zip(a, b))


ID = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))


def compose(parent, local):
    pt, pq = parent
    lt, lq = local
    return (vadd(pt, qrot(pq, lt)), qnorm(qmul(pq, lq)))


def inv(tr):
    t, q = tr
    qi = qconj(q)
    return (vmul(qrot(qi, t), -1.0), qi)


def rel(parent, world):
    """local such that compose(parent, local) == world"""
    return compose(inv(parent), world)


def point(tr, p):
    return vadd(tr[0], qrot(tr[1], p))


def tblend(a, b, w):
    if w <= 0.0:
        return a
    if w >= 1.0:
        return b
    return (vadd(a[0], vmul(vsub(b[0], a[0]), w)), qslerp(a[1], b[1], w))


def from_ue(t):
    return ((t.translation.x, t.translation.y, t.translation.z),
            (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w))


def to_ue(tr):
    t, q = tr
    return unreal.Transform(unreal.Vector(*t), unreal.Quat(q[0], q[1], q[2], q[3]).rotator(), unreal.Vector(1, 1, 1))


def yaw90():
    return qaxis((0, 0, 1), 90.0)


def pitch(deg):
    """Unreal pitch (nose up) as a rotation about the gun's Y axis: X toward +Z."""
    return qaxis((0, -1, 0), deg)


def frame(spec):
    pos, r = spec
    q = yaw90() if r == "yaw90" else pitch(r)
    return (tuple(float(x) for x in pos), q)


# M: the CHOPPER's frame in the pack gun's space; palm_r of the pack on PALM_R_TARGET
def chop_in_pack():
    q = yaw90()
    p = vsub(PK["palm_r"], qrot(q, PALM_R_TARGET))
    return (p, q)


M = chop_in_pack()


def hinge(deg, down=0.0):
    """The magazine bone's transform (gun space) rocked `deg` forward about MagHinge, then moved `down` cm."""
    q = pitch(deg)
    h = CH["MagHinge"]
    t = vsub(h, qrot(q, h))
    return ((t[0], t[1], t[2] - down), q)


def smooth(e0, e1, x):
    if e0 == e1:
        return 1.0 if x >= e1 else 0.0
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def window(t, a, b, c, d):
    """0 before a, ramps to 1 at b, 1 until c, ramps to 0 at d."""
    return smooth(a, b, t) * (1.0 - smooth(c, d, t))


# ---------------------------------------------------------------- the skeleton
_SK = {}


def skeleton():
    if _SK:
        return _SK
    a = ACTORS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, -10000))
    c = a.skeletal_mesh_component
    c.set_skinned_asset_and_update(unreal.load_asset(MANNY))
    names = [str(c.get_bone_name(i)) for i in range(c.get_num_bones())]
    parents = {n: (str(c.get_parent_bone(n)) if str(c.get_parent_bone(n)) not in ("None", "") else None) for n in names}
    ACTORS.destroy_actor(a)
    _SK.update(names=names, parents=parents)
    return _SK


def _opts():
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("evaluation_type", unreal.AnimDataEvalType.RAW)
    o.set_editor_property("should_retarget", False)
    o.set_editor_property("extract_root_motion", False)
    return o


def locals_at(anim, t):
    p = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, float(t), _opts())
    return {n: from_ue(unreal.AnimPoseExtensions.get_bone_pose(p, n, LS)) for n in skeleton()["names"]}


def worlds(loc):
    sk = skeleton()
    w = {}
    for n in sk["names"]:
        p = sk["parents"][n]
        w[n] = compose(w[p], loc[n]) if p else loc[n]
    return w


def blend_locals(a, b, wgt, bones=None):
    if wgt <= 0:
        return a
    out = dict(a)
    for n in (bones or a.keys()):
        out[n] = tblend(a[n], b[n], wgt)
    return out


PALM = ("hand_{s}", "index_metacarpal_{s}", "middle_metacarpal_{s}", "ring_metacarpal_{s}", "pinky_metacarpal_{s}",
        "index_01_{s}", "middle_01_{s}", "ring_01_{s}", "pinky_01_{s}")
FINGERS = [f + "_%02d_{s}" % i for f in ("index", "middle", "ring", "pinky", "thumb") for i in (1, 2, 3)] + \
          [f + "_metacarpal_{s}" for f in ("index", "middle", "ring", "pinky")]


def palm(w, s):
    pts = [w[b.format(s=s)][0] for b in PALM]
    return vmul(tuple(sum(p[i] for p in pts) for i in range(3)), 1.0 / len(pts))


def palm_offset(w, s):
    """palm centre in the hand bone's frame"""
    return rel(w["hand_" + s], (palm(w, s), (0, 0, 0, 1)))[0]


# ---------------------------------------------------------------- two-bone IK
def two_bone(loc, w, side, target):
    """Set upperarm, lowerarm and hand locals so the hand reaches `target` (world), keeping the elbow's plane."""
    up, lo, ha = "upperarm_" + side, "lowerarm_" + side, "hand_" + side
    A, B, C = w[up][0], w[lo][0], w[ha][0]
    P = target[0]
    l1, l2 = vlen(vsub(B, A)), vlen(vsub(C, B))
    D = vsub(P, A)
    d = max(abs(l1 - l2) + 1e-3, min(l1 + l2 - 1e-3, vlen(D)))
    u = vnorm(D)
    n = vsub(vsub(B, A), vmul(u, dot(vsub(B, A), u)))
    v = vnorm(n) if vlen(n) > 1e-4 else vnorm(cross(u, (0, 0, 1)))
    ca = max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)))
    sa = math.sqrt(max(0.0, 1 - ca * ca))
    B2 = vadd(A, vmul(vadd(vmul(u, ca), vmul(v, sa)), l1))
    P2 = vadd(A, vmul(u, d))
    q1 = qbetween(vsub(B, A), vsub(B2, A))
    up_w = (A, qnorm(qmul(q1, w[up][1])))
    lo_rot = qnorm(qmul(q1, w[lo][1]))
    q2 = qbetween(qrot(q1, vsub(C, B)), vsub(P2, B2))
    lo_w = (B2, qnorm(qmul(q2, lo_rot)))
    ha_w = (P2, target[1])
    parent = skeleton()["parents"][up]
    loc[up] = rel(w[parent], up_w)
    loc[lo] = rel(up_w, lo_w)
    loc[ha] = rel(lo_w, ha_w)
    return vlen(vsub(P2, P))


# ---------------------------------------------------------------- recipes
def _seg(s):
    return (s[0], s[1], s[2], s[3], s[4] if len(s) > 4 else 0.0)


def warp(segments, t):
    """segments: [(out0, out1, src0, src1[, xf])], piecewise linear time map out -> src (src may run backwards)."""
    for s in segments:
        o0, o1, s0, s1, _ = _seg(s)
        if t <= o1 + 1e-9:
            if o1 <= o0:
                return s0
            return s0 + (s1 - s0) * (max(t, o0) - o0) / (o1 - o0)
    return segments[-1][3]


def src_locals(src, segments, t, start=0.0):
    """The source pose at output time t: the segment's mapped frame, cross-faded over the segment's first xf seconds
    from the pose the previous segment ended on (the first segment fades from the source frame `start`), so a jump
    in source time is a blend, never a pop."""
    st = warp(segments, t)
    loc = locals_at(src, st)
    prev_end = start
    for i, s in enumerate(segments):
        o0, o1, s0, s1, xf = _seg(s)
        if t <= o1 + 1e-9 or i == len(segments) - 1:
            if xf > 0 and t < o0 + xf and abs(prev_end - s0) > 1e-6:
                loc = blend_locals(locals_at(src, prev_end), loc, smooth(o0, o0 + xf, t))
            break
        prev_end = s1
    return st, loc


# The pack strips no magazine before its fresh one (its quick and empty reloads drop the old magazine while the
# left hand goes to the pouch, the shoulder swinging 33 cm back, out of reach of our magazine; its retention reload
# fetches the fresh one first). Our rule takes the old magazine out first (0.27 to 0.68), so that phase plays the
# pack's own seating motion backwards (hand on a seated magazine rocking it out and down), then cross-fades to
# the pack's pouch frames and runs forward from there.
RELOAD_TACTICAL = {
    "name": "A_{fp}_Chopper_ReloadTactical", "src": "Reload_Quick", "length": 2.24,
    "segments": [(0.0, 0.27, 1.467, 1.467, 0.27), (0.27, 0.68, 1.467, 1.00), (0.68, 0.80, 0.70, 0.80, 0.08),
                 (0.80, 1.15, 0.80, 1.10), (1.15, 1.44, 1.10, 1.467),
                 (1.44, 1.625, 1.467, 1.80), (1.625, 2.22, 1.80, 2.067), (2.22, 2.24, 2.067, 2.10)],
    "knob": {"in": (1.80, 1.88), "out": (1.98, 2.08), "pull": [(1.89, 0.0), (1.93, 0.32), (1.98, 0.0)]},
    "marks": {"magOut": 0.40, "magShow": 0.80, "magInsert": 1.15, "magIn": 1.44, "tug": 1.565, "bolt": 1.89,
              "done": 2.24},
}
RELOAD_EMPTY = {
    "name": "A_{fp}_Chopper_ReloadEmpty", "src": "Reload_Empty", "length": 2.72,
    "segments": [(0.0, 0.27, 1.40, 1.40, 0.27), (0.27, 0.68, 1.40, 1.00), (0.68, 0.80, 0.70, 0.80, 0.08),
                 (0.80, 1.15, 0.80, 1.10), (1.15, 1.44, 1.10, 1.333),
                 (1.44, 1.625, 1.333, 1.533), (1.625, 1.96, 1.533, 1.80), (1.96, 2.155, 1.80, 2.467),
                 (2.155, 2.66, 2.467, 2.733), (2.66, 2.72, 2.733, 2.80)],
    "knob": {"in": (1.70, 1.96), "out": (2.155, 2.45), "pull": [(1.96, 0.0), (2.07, 1.0), (2.155, 1.0), (2.40, 0.0)]},
    "bolt": [(1.96, 0.0), (2.07, 1.0), (2.155, 1.0), (2.185, 0.0)],
    "marks": {"magOut": 0.40, "magShow": 0.80, "magInsert": 1.15, "magIn": 1.44, "tug": 1.565, "bolt": 1.96,
              "boltRelease": 2.155, "done": 2.72},
}


def curve(points, t):
    if t <= points[0][0]:
        return points[0][1]
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
            k = k * k * (3 - 2 * k)
            return v0 + (v1 - v0) * k
    return points[-1][1]


class Adapter:
    def __init__(self):
        self.pack_mag = frame(PACK_MAG_FRAME)
        self.our_mag = frame(OUR_MAG_FRAME)
        self.pack_bc = frame(PACK_BC_FRAME)
        self.our_knob = frame(OUR_KNOB_FRAME)
        self.dg = None

    # -- pack gun space -> our gun space
    def gun(self, w):
        return compose(w["ik_hand_gun"], M)

    def pack_in_ours(self, p):
        return point(inv(M), p)

    def aim_correction(self, aimed_clip):
        """Dg (our gun space) that puts our sight line on the pack's sight line through the eye."""
        w = worlds(locals_at(aimed_clip, 0.0))
        g = w["ik_hand_gun"]
        pr, pf = point(g, PK["Sight_Rear"]), point(g, PK["Sight_Front"])
        d = vnorm(vsub(pf, pr))
        gw = self.gun(w)
        r, f = point(gw, CH["SightRear"]), point(gw, CH["SightFront"])
        q = qbetween(vsub(f, r), d)
        # rotate about r, then move r onto the pack line through EYE_CS (perpendicular move)
        e = EYE_CS
        rr = vadd(e, vmul(d, EYE_RELIEF))          # rear sight on the line, the rules' eye relief ahead of the eye
        delta_q = q
        gw2 = (vadd(rr, qrot(delta_q, vsub(gw[0], r))), qnorm(qmul(delta_q, gw[1])))
        self.dg = rel(gw, gw2)
        return self.dg

    def adapt_frame(self, loc, t_out, recipe=None, src_t=None, aimed=False, extra=None):
        """Returns (new locals, parts dict) for one frame."""
        w = worlds(loc)
        gw = self.gun(w)
        gw2 = compose(gw, self.dg) if (aimed and self.dg) else gw
        loc = dict(loc)
        parts = {"bolt": 0.0, "mag": ID, "mag_visible": 1.0, "mag_in_hand": 0.0, "mag_rock": 0.0, "trigger": 0.0}
        # right hand rides with the gun (unchanged unless aimed correction)
        hr_rel = rel(gw, w["hand_r"])
        hr_t = compose(gw2, hr_rel)
        # left hand: start from the pack hand mapped rigidly with the gun
        hl_rel = rel(gw, w["hand_l"])
        pl_pack = point(inv(w["ik_hand_gun"]), palm(w, "l"))
        dist_hg = vlen(vsub(pl_pack, PK["palm_l"]))
        off_hl = palm_offset(w, "l")
        # handguard correction: move the palm centre onto PALM_L_TARGET while near the pack's rest
        palm_rest_ours = self.pack_in_ours(PK["palm_l"])
        d_hg = vsub(PALM_L_TARGET, palm_rest_ours)
        w_hg = smooth(10.0, 3.0, dist_hg)
        target = ((vadd(hl_rel[0], vmul(d_hg, w_hg))), hl_rel[1])
        if recipe is not None:
            target, parts = self.reload_left(w, hl_rel, target, t_out, recipe, src_t, extra, parts)
        hl_t = compose(gw2, target)
        if aimed and self.dg:
            two_bone(loc, w, "r", hr_t)
        two_bone(loc, w, "l", hl_t)
        if extra and extra.get("fingers") is not None:
            fw = extra["fingers_w"]
            for f in FINGERS:
                n = f.format(s="l")
                loc[n] = tblend(loc[n], extra["fingers"][n], fw)
        # ik bones: ik_hand_gun = our gun's origin; ik_hand_l / ik_hand_r on the hands
        par = skeleton()["parents"]
        w2 = worlds(loc)
        loc["ik_hand_gun"] = rel(w2[par["ik_hand_gun"]], gw2)
        w3 = worlds(loc)
        for b in ("ik_hand_l", "ik_hand_r"):
            loc[b] = rel(w3[par[b]], w2["hand_" + b[-1]])
        parts["_check"] = {"hand_l_err": vlen(vsub(w2["hand_l"][0], hl_t[0])),
                           "palm_l_gun": point(inv(gw2), palm(w2, "l")),
                           "palm_r_gun": point(inv(gw2), palm(w2, "r"))}
        return loc, parts

    def reload_left(self, w, hl_rel, target, t, rc, src_t, extra, parts):
        """Left-hand target (our gun space) and magazine/bolt parts on the rules' marks."""
        g_pack = w["ik_hand_gun"]
        hand_pack = rel(g_pack, w["hand_l"])                  # pack hand in pack gun space
        seat_map = compose(self.our_mag, rel(self.pack_mag, hand_pack))   # pack hand moved from pack mag to ours
        # magazine bone transform B(t) (our gun space) and the hand that holds it
        K_s = extra["K_strip"]
        grip = lambda B, K: compose(compose(B, self.our_mag), K)
        tgt = target
        if t < 0.80:
            if t <= 0.40:
                B = ID
            else:
                k = smooth(0.40, 0.53, t)
                B = hinge(CH["mag_deg"] * k, 3.0 * k)
            w_strip = window(t, 0.067, 0.27, 0.53, 0.68)
            held = grip(B, K_s)
            tgt = tblend(target, held, w_strip)
            if t > 0.40:
                parts["mag_in_hand"] = 1.0
                if t > 0.53:
                    # the magazine follows the hand toward the pouch
                    B = compose(tgt, inv(compose(self.our_mag, K_s)))
            parts["mag"] = B
            parts["mag_rock"] = CH["mag_deg"] * smooth(0.40, 0.53, t) if t <= 0.53 else CH["mag_deg"]
            parts["mag_visible"] = 0.0 if 0.70 <= t < 0.80 else 1.0
            extra["fingers_w"] = w_strip
        elif t < 1.44:
            # fresh magazine: the pack hand mapped from the pack's magazine to ours, then hooked and rocked in
            parts["mag_in_hand"] = 1.0
            g_p = compose(extra["pack_mag_now"], (ID[0], yaw90()))        # pack grip frame now (our axes)
            g_o = compose(self.our_mag, rel(self.pack_mag, g_p))          # the same motion about our well
            free = compose(g_o, inv(self.our_mag))                        # our magazine bone, following it
            Kp = rel(g_p, hand_pack)                                      # the pack hand on its magazine
            if t < 1.15:
                B = tblend(free, hinge(CH["mag_deg"]), smooth(0.95, 1.15, t))
                parts["mag_rock"] = CH["mag_deg"] * smooth(0.95, 1.15, t)
            else:
                k = smooth(1.15, 1.44, t)
                B = hinge(CH["mag_deg"] * (1 - k))
                parts["mag_rock"] = CH["mag_deg"] * (1 - k)
            parts["mag"] = B
            tgt = grip(B, Kp)
            extra["fingers_w"] = 0.0
        else:
            # seated: hold, let go, return (pack), with the charging-handle detour
            w_seat = 1.0 - smooth(1.625, 1.90, t)
            tgt = tblend(target, seat_map, w_seat)
            kn = rc["knob"]
            w_k = window(t, kn["in"][0], kn["in"][1], kn["out"][0], kn["out"][1])
            if w_k > 0:
                hk = extra["knob_hand"]                         # pack hand on its bolt catch (pack gun space)
                on_knob = compose(self.our_knob, rel(self.pack_bc, hk))
                pull = curve(kn["pull"], t) * CH["bolt_travel"]
                on_knob = (vsub(on_knob[0], (pull, 0.0, 0.0)), on_knob[1])
                tgt = tblend(tgt, on_knob, w_k)
                extra["fingers_w"] = w_k
                extra["fingers"] = extra["knob_fingers"]
            parts["bolt"] = curve(rc.get("bolt", rc["knob"]["pull"]), t) if "bolt" in rc else \
                curve(kn["pull"], t)
        return tgt, parts


# ---------------------------------------------------------------- writing clips
def _controller(anim):
    return anim.get_editor_property("controller")


def write_clip(dest_path, frames, rate=FPS, skeleton_path=SKELETON, curves=None, source=None):
    """frames: list of {bone: (t, q)} locals at 1/rate spacing. Creates or replaces dest_path."""
    folder, name = dest_path.rsplit("/", 1)
    if ASSETS.does_asset_exist(dest_path):
        ASSETS.delete_asset(dest_path)
    if source is not None:
        anim = ASSETS.duplicate_asset(source.get_path_name().split(".")[0], dest_path)
    else:
        f = unreal.AnimSequenceFactory()
        f.set_editor_property("target_skeleton", unreal.load_asset(skeleton_path))
        anim = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.AnimSequence, f)
    c = _controller(anim)
    c.open_bracket(unreal.Text("MI adapt"), False)
    c.set_frame_rate(unreal.FrameRate(rate, 1), False)
    c.set_number_of_frames(unreal.FrameNumber(len(frames) - 1), False)
    bones = list(frames[0].keys())
    model = anim.get_editor_property("data_model_interface") if hasattr(anim, "data_model_interface") else None
    for b in bones:
        pos = [unreal.Vector(*fr[b][0]) for fr in frames]
        rot = [unreal.Quat(*fr[b][1]) for fr in frames]
        scl = [unreal.Vector(1, 1, 1) for _ in frames]
        # a new sequence has no bone tracks and set_bone_track_keys then returns False without raising
        ok = c.set_bone_track_keys(b, pos, rot, scl, False)
        if not ok:
            for fn in ("add_bone_curve", "add_bone_track"):
                if hasattr(c, fn):
                    getattr(c, fn)(b, False)
                    break
            ok = c.set_bone_track_keys(b, pos, rot, scl, False)
        if not ok:
            c.close_bracket(False)
            raise RuntimeError("%s: no bone track for %s" % (dest_path, b))
    c.close_bracket(False)
    # The compressor samples at the sequence's target frame rate (30 unless told): a clip whose length is not a
    # whole number of target frames trips an assertion in AnimCompressionTypes.cpp and takes the editor down.
    try:
        p = anim.get_editor_property("platform_target_frame_rate")
        p.set_editor_property("default", unreal.FrameRate(rate, 1))
        anim.set_editor_property("platform_target_frame_rate", p)
    except Exception:  # noqa: BLE001
        if abs((len(frames) - 1) / rate * 30.0 - round((len(frames) - 1) / rate * 30.0)) > 1e-6:
            ASSETS.delete_asset(dest_path)
            raise RuntimeError("%s: %d frames at %d fps is not a whole number of 30 fps frames" %
                               (dest_path, len(frames) - 1, rate))
    if curves:
        for cname, pts in curves.items():
            try:
                unreal.AnimationLibrary.remove_curve(anim, cname, False)
            except Exception:  # noqa: BLE001
                pass
            unreal.AnimationLibrary.add_curve(anim, cname, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
            unreal.AnimationLibrary.add_float_curve_keys(anim, cname, [p[0] for p in pts], [p[1] for p in pts])
    ASSETS.save_loaded_asset(anim)
    return anim


def pack_clip(rel_path):
    return unreal.load_asset(PACK + "/Character/" + rel_path)


def fingers_of(loc, s="l"):
    return {f.format(s=s): loc[f.format(s=s)] for f in FINGERS}


def adapt_generic(rel_path, dest=None, aimed=None, adapter=None):
    """Hand IK onto the CHOPPER for a clip that holds the gun normally (locomotion, poses, fire, transitions...)."""
    src = pack_clip(rel_path)
    base = rel_path.split("/")[-1]
    aimed = ("Aimed" in base or "Aim_Pose" in base) if aimed is None else aimed
    ad = adapter or default_adapter()
    n = int(round(src.get_play_length() * FPS)) + 1
    frames = []
    for i in range(n):
        t = min(i / FPS, src.get_play_length())
        loc, _ = ad.adapt_frame(locals_at(src, t), t, aimed=aimed)
        frames.append(loc)
    dest = dest or OUT + "/" + rel_path.rsplit("/", 1)[0] + "/" + base.replace("A_TFA_", "A_CH_")
    write_clip(dest, frames, source=src)
    return {"dest": dest, "frames": n, "length": round((n - 1) / FPS, 4), "aimed": aimed}


_AD = {}


def default_adapter():
    if "a" not in _AD:
        a = Adapter()
        a.aim_correction(pack_clip("FP/Locomotion/A_TFA_FP_AR_Idle_Loop_Aimed"))
        _AD["a"] = a
    return _AD["a"]


def adapt_reload(recipe, view="FP"):
    ad = default_adapter()
    pv = "FP" if view == "FP" else "TP"
    src = pack_clip("%s/Combat/A_TFA_%s_AR_%s" % (pv, pv, recipe["src"]))
    wep_name = "A_TFA_%s_WEP_AR_%s" % (pv, recipe["src"])
    wep = unreal.load_asset(PACK + "/Weapon/Anims/%s/%s" % (pv, wep_name))
    if wep is None:
        wep = unreal.load_asset(PACK + "/Weapon/Anims/FP/A_TFA_FP_WEP_AR_" + recipe["src"])
    # constant grips from the pack: the hand holding a seated magazine (Quick 1.467), the hand on the bolt catch
    q = pack_clip("%s/Combat/A_TFA_%s_AR_Reload_Quick" % (pv, pv))
    lq = locals_at(q, 1.467)
    wq = worlds(lq)
    hand_on_mag = rel(wq["ik_hand_gun"], wq["hand_l"])
    K_strip = rel(ad.pack_mag, hand_on_mag)
    e = pack_clip("%s/Combat/A_TFA_%s_AR_Reload_Empty" % (pv, pv))
    le = locals_at(e, 2.0)
    we = worlds(le)
    extra = {"K_strip": K_strip, "fingers": fingers_of(lq), "fingers_w": 0.0,
             "knob_hand": rel(we["ik_hand_gun"], we["hand_l"]), "knob_fingers": fingers_of(le)}
    L = recipe["length"]
    n = int(round(L * FPS)) + 1
    frames, parts_t = [], []
    for i in range(n):
        t = min(i / FPS, L)
        st, loc = src_locals(src, recipe["segments"], t)
        extra["fingers"] = fingers_of(lq)
        extra["fingers_w"] = 0.0
        extra["pack_mag_now"] = _pack_reserve(wep, st)
        out, parts = ad.adapt_frame(loc, t, recipe=recipe, src_t=st, extra=extra)
        frames.append(out)
        parts_t.append((t, parts))
    name = recipe["name"].format(fp=view)
    dest = OUT + "/%s/%s" % (view, name)
    curves = {
        "Chopper_Bolt": [(t, round(p["bolt"], 4)) for t, p in parts_t],
        "Chopper_MagVisible": [(t, p["mag_visible"]) for t, p in parts_t],
        "Chopper_MagInHand": [(t, p["mag_in_hand"]) for t, p in parts_t],
        "Chopper_MagRock": [(t, round(p["mag_rock"], 3)) for t, p in parts_t],
    }
    write_clip(dest, frames, source=src, curves=curves)
    return {"dest": dest, "frames": n, "length": L, "parts": parts_t}


def _pack_reserve(wep, t):
    """The pack's fresh magazine (Magazine_Reserve) in its gun space at time t."""
    p = unreal.AnimPoseExtensions.get_anim_pose_at_time(wep, float(t), _opts())
    return from_ue(unreal.AnimPoseExtensions.get_bone_pose(p, "Magazine_Reserve", WS))
