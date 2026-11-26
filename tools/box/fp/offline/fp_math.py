"""The first-person view of a hand-IK gun as the game computes it, offline (HANDS_R4.md 12).

Pure Python + numpy (no Blender, no engine). Mirrors, line for line where it matters:

  - MIViewmodel.cpp   FMIViewmodelRig: the gun's pose in camera space from the gun's views (hip = views[0]), the aimed
                      pose (the rear sight on the axis, `relief` in front of the eye), the reload pose (poses.reload,
                      weighted by min(Ease(t / in), Ease((total - t) / out))), the magazine bone's drop (out / show / in
                      marks), WebToUE, EulerYXZ, MeshOffset * GunTransform;
  - MIWeaponComponent.cpp PoseView: the arms carried so that their shoulders' midpoint sits on the anim set's
                      `shoulders` (camera space), GripShoulderTranslation;
  - MIFirstPersonRig.cpp UpdateHands: the IK targets (Palm_L / Palm_R sockets), the solved grips (grips.json guns, hip and
                      aimed blended by smoothstep(aim) for the hands `grip.aimSides` names), the reload hold (the support
                      shape taken from grips.json magazines.<mesh>.l, carried by the magazine's bone), the support elbow
                      push (supportElbowOut, camera space, let go while the hand holds the magazine);
  - MIFirstPersonAnim.cpp SolveHand / ShapeHand / ShapeFingers: two-bone IK with the pole L + (L - (U + E) / 2) * 2 +
                      PoleShift, the hand turned so its frame of points (wrist, middle_01, index_01, pinky_01) matches the
                      shape's, every finger bone swung onto its child's point (the _03 bone along its parent segment's
                      reference direction).

Units and frames: everything here is Unreal (cm; X forward, Y right, Z up). The camera is the eye at the origin. The
Blender side (fp_offline.py) maps a point with (x, y, z) -> (x, -y, z) / 100 (BOX.md 5: Blender -> glTF -> Unreal is
(x, y, z) -> (x, -y, z) x 100), and a rotation R with D R D, D = diag(1, -1, 1).

What is NOT the game's: the arms' pre-IK pose. The game plays the pack's rifle idle (A_TFA_FP_AR_Idle_Loop_Standing),
which is not in this repository. Its part in the result is small and named (see `ClipModel`): the shoulder line's turn
(the clip's hand rotation sets the arms component's rotation, PoseView `Hand.Inverse() * Grip`) and the elbow pole the
IK starts from. Both are calibrated against the game's own development log (HANDS_R4.md 9.3: the support elbow's bend
and the forearm's slope on the screen, with and without the elbow push).
"""
import json
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DATA = os.path.join(ROOT, "unreal", "MurderInc", "Content", "Data")
GLB = os.path.join(ROOT, "art", "out", "glb")


# ------------------------------------------------------------------------------------------------ quaternions (FQuat)
def q_axis(axis, angle):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    s = math.sin(angle * 0.5)
    return np.array([a[0] * s, a[1] * s, a[2] * s, math.cos(angle * 0.5)])


def q_mul(a, b):
    """FQuat a * b: b applied first, then a (Hamilton product)."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw * bx + bw * ax + ay * bz - az * by,
                     aw * by + bw * ay + az * bx - ax * bz,
                     aw * bz + bw * az + ax * by - ay * bx,
                     aw * bw - ax * bx - ay * by - az * bz])


def q_mat(q):
    x, y, z, w = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def q_slerp(a, b, t):
    d = float(np.dot(a, b))
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        r = a + (b - a) * t
        return r / np.linalg.norm(r)
    th = math.acos(d)
    return (math.sin((1 - t) * th) * a + math.sin(t * th) * b) / math.sin(th)


def euler_yxz(pitch, yaw, roll):
    """FMIViewmodelRig::EulerYXZ (three.js order YXZ, web space)."""
    return q_mul(q_mul(q_axis((0, 1, 0), yaw), q_axis((1, 0, 0), pitch)), q_axis((0, 0, 1), roll))


def web_to_ue_q(q):
    return np.array([q[2], -q[0], -q[1], q[3]])


def web_to_ue(v):
    """Web (x right, y up, z back; metres) -> Unreal cm."""
    return np.array([-v[2], v[0], v[1]]) * 100.0


def tf(q=None, t=(0, 0, 0)):
    M = np.eye(4)
    if q is not None:
        M[:3, :3] = q_mat(q)
    M[:3, 3] = t
    return M


def ue_mul(A, B):
    """FTransform A * B (A applied first, then B) as 4x4 column matrices."""
    return B @ A


def xp(M, p):
    return (M @ np.append(np.asarray(p, float), 1.0))[:3]


def xv(M, v):
    return M[:3, :3] @ np.asarray(v, float)


def find_between(a, b):
    """FQuat::FindBetweenVectors as a 3x3 matrix (the shortest swing taking a onto b)."""
    a = np.asarray(a, float) / np.linalg.norm(a)
    b = np.asarray(b, float) / np.linalg.norm(b)
    c = np.cross(a, b)
    d = float(np.dot(a, b))
    if d < -0.999999:
        axis = np.cross(a, [1, 0, 0])
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(a, [0, 1, 0])
        return q_mat(q_axis(axis, math.pi))
    K = np.array([[0, -c[2], c[1]], [c[2], 0, -c[0]], [-c[1], c[0], 0]])
    return np.eye(3) + K + K @ K * (1.0 / (1.0 + d))


def ease(t):
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return t * t * t * (t * (t * 6 - 15) + 10)


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------------------------------------ the data, resolved
def _load(name):
    return json.load(open(os.path.join(DATA, name)))


def _ref(doc_by_file, ref):
    f, path = ref.split("#")
    o = doc_by_file[f]
    for k in path.split("."):
        o = o[k]
    return o


class Gun:
    """One gun as the loadout resolver hands it to the rig (MILoadoutResolver: `$ref`s followed, the `real` block merged
    over the presentation when the real mesh is drawn), plus its anim set, grips and magazine solve."""

    def __init__(self, gid):
        docs = {"presentation.json": _load("presentation.json"), "config.json": _load("config.json"),
                "guns.json": _load("guns.json")}
        self.docs = docs
        g = docs["guns.json"]["guns"][gid]
        pres = g["presentation"]
        pres = dict(_ref(docs, pres["$ref"])) if "$ref" in pres else dict(pres)
        rules = g["rules"]
        rules = _ref(docs, rules["$ref"]) if "$ref" in rules else rules
        if pres.get("realMesh") and isinstance(pres.get("real"), dict):
            for k, v in pres["real"].items():
                pres[k] = v
        self.id = gid
        self.pres = pres
        self.rules = rules
        fp = docs["presentation.json"]["firstPerson"]
        self.fp = fp
        self.set = fp["animSets"][pres["animSet"]]
        self.config = docs["config.json"]
        self.feel = docs["presentation.json"]["feel"]
        mesh = pres.get("realMesh") or pres["mesh"]
        if isinstance(mesh, dict):   # {"$variant": ...}: the base mesh of the build's variant (only `open` exists)
            vs = {k: v for k, v in g.get("variants", {}).items() if isinstance(v, dict) and "mesh" in v}
            mesh = (vs.get("open") or next(iter(vs.values())))["mesh"]
        self.mesh_name = mesh.split(".")[-1]
        self.glb = os.path.join(GLB, self.mesh_name + ".glb")
        mag = self.set.get("magazine", {}).get("full")
        self.mag_name = mag.split(".")[-1] if mag else None
        self.mag_glb = os.path.join(GLB, self.mag_name + ".glb") if mag else None
        grips = _load("grips.json")
        gk = self.set["grip"]["gun"]
        self.grip_pose = self.set["grip"].get("pose", "hip")
        self.grip_aim_pose = self.set["grip"].get("aimPose", "aim")
        self.aim_sides = self.set["grip"].get("aimSides", "l")
        G = grips["guns"][gk]
        self.grip_hip = {s: {k: np.array(v, float) for k, v in G[self.grip_pose][s].items()} for s in ("l", "r")}
        self.grip_aim = {}
        if self.grip_aim_pose != self.grip_pose and self.grip_aim_pose in G:
            for s in ("l", "r"):
                if s in self.aim_sides and s in G[self.grip_aim_pose]:
                    self.grip_aim[s] = {k: np.array(v, float) for k, v in G[self.grip_aim_pose][s].items()}
        self.reload_points = {}
        if self.mag_name and self.mag_name in grips.get("magazines", {}):
            self.reload_points = {k: np.array(v, float) for k, v in grips["magazines"][self.mag_name]["l"].items()}
        # MIViewmodel: the views (hip = views[0]), poses, markers, relief
        self.views = rules["views"]
        self.reload = rules["reload"]
        self.markers = pres["markers"]
        self.relief = pres["relief"]
        self.poses = pres["poses"]
        mo = pres["meshOffset"]
        self.mesh_offset = tf(web_to_ue_q(euler_yxz(*mo["rot"])), web_to_ue(mo["pos"]))
        self.mag_part = pres["parts"]["magazine"]
        self.shoulders = np.array(self.set["shoulders"], float) if "shoulders" in self.set else None
        self.elbow_out = np.array(self.set.get("supportElbowOut", [0, 0, 0]), float)
        self.elbow_out_aim = np.array(self.set.get("supportElbowOutAim", self.set.get("supportElbowOut", [0, 0, 0])), float)
        self.arm_stretch = min(1.3, max(1.0, self.set.get("armStretch", 1.0)))
        self.mag_blend = min(0.6, max(0.05, self.set.get("magazine", {}).get("blend", 0.25)))
        self.optic = False

    # -------------------------------------------------------------------------------------------- MIViewmodel poses
    def view_pose(self, state):
        """(pos web m, quat web) of FMIViewmodelRig::Pose for a frozen state: 'hip', 'aim' or ('reload', t)."""
        def pose_of(a):
            return np.array(a[:3], float), euler_yxz(a[3], a[4], a[5])
        pos, rot = pose_of(self.views[0])
        if isinstance(state, tuple) and state[0] == "reload":
            t = state[1]
            total = self.reload["tactical"]
            fb = self.feel["reloadBlend"]
            w = min(ease(t / fb["in"]), ease((total - t) / fb["out"]))
            rp, rr = pose_of(self.poses["reload"])
            pos, rot = pos + (rp - pos) * w, q_slerp(rot, rr, w)
        if state == "aim":
            s = self.markers["sightRear"]
            ap = np.array([-s[0], -s[1], -self.relief - s[2]])
            pos, rot = ap, np.array([0, 0, 0, 1.0])
        return pos, rot

    def ads(self, state):
        return 1.0 if state == "aim" else 0.0

    def fov_v(self, state):
        """Vertical first-person field of view (UMIFirstPersonRig::FirstPersonFovV over config player.fov.viewmodel)."""
        hip = self.config["player"]["fov"]["viewmodel"]
        to = self.fp["recipe"]["fovOptic"] if self.optic else self.fp["recipe"]["fovIrons"]
        return hip + (to - hip) * self.ads(state)

    def gun_matrix(self, state):
        """The gun mesh's frame in camera space (UMIWeaponComponent::PoseView: MeshOffset * Rig.GetGunTransform())."""
        pos, rot = self.view_pose(state)
        G = tf(web_to_ue_q(rot), web_to_ue(pos))
        return ue_mul(self.mesh_offset, G)

    def magazine_drop(self, state):
        """FMIViewmodelRig::UpdateParts Parts.Magazine (0..1) and the bone's translation in mesh space (cm)."""
        m = 0.0
        if isinstance(state, tuple) and state[0] == "reload":
            t = state[1]
            out, show, inn = (self.reload.get(self.mag_part[k]) for k in ("out", "show", "in"))
            if out is not None and show is not None and inn is not None:
                if out <= t < show:
                    k = min(1.0, max(0.0, (t - out) / max(1e-3, (show - out) * 0.5)))
                    m = ease(k)
                elif show <= t < inn:
                    m = 1.0 - ease((t - show) / max(1e-3, inn - show))
        d = np.array(self.mag_part.get("drop", [0, 0, 0]), float)
        d_ue = np.array([-d[2], d[0], d[1]])           # WebToUE(web) / 100
        d_mesh = self.mesh_offset[:3, :3].T @ d_ue     # MeshOffset.InverseTransformVectorNoScale
        return m, d_mesh * 100.0 * m

    def mag_hold(self, state):
        """MagK of UpdateHands (the hold moved at most 1 / magazine.blend a second, smoothstepped)."""
        if not (isinstance(state, tuple) and state[0] == "reload") or not self.mag_name:
            return 0.0
        t = state[1]
        left = self.reload["tactical"] - t
        # the state chases min(t, left) / blend at 1 / blend a second from 0 at t = 0: it equals the target while rising
        return smooth(min(1.0, max(0.0, min(t, left) / self.mag_blend)))


# ------------------------------------------------------------------------------------------------ the arms' clip model
class ClipModel:
    """What the pack's idle clip gives the rig and this file cannot read (the clip is not in the repository).

    blade_deg: the shoulder line's turn about the camera's Z at the hip (positive brings the left shoulder forward);
    roll_deg: then its turn about the camera's X (positive lifts the left shoulder: Unreal's left-handed sense, Y to Z);
    shoulder_l: or, instead of a rigid turn, where the clip puts the left shoulder (upperarm_l's head) from the shoulders'
    midpoint, camera space cm at the CHOPPER's hip (the right one mirrored through the midpoint; both turn with the gun
    as the arms component does). The clip protracts the clavicles, which a rigid turn of the rest skeleton cannot.
    pole_l / pole_r: where the clip's elbow lies from the middle of the shoulder-hand line, camera space, cm (the pole
    the IK starts from is that point times three: L + (L - mid) * 2 with L = mid + offset).
    Calibrated by calibrate.py against the support-arm log of HANDS_R4.md 9.3."""

    def __init__(self, blade_deg=0.0, pole_l=(0.0, -6.0, -10.0), pole_r=(0.0, 6.0, -10.0), roll_deg=0.0, shoulder_l=None):
        self.blade_deg = blade_deg
        self.roll_deg = roll_deg
        self.shoulder_l = None if shoulder_l is None else np.array(shoulder_l, float)
        self.pole_l = np.array(pole_l, float)
        self.pole_r = np.array(pole_r, float)


ARMS_REST = q_axis((0, 0, 1), math.radians(-90.0))   # recipe armsYaw: the mesh's +Y forward


# ------------------------------------------------------------------------------------------------ the skeleton and the IK
class Skeleton:
    """Bones with parent-relative matrices, Unreal cm in the arms mesh's space (built by fp_offline from the GLB)."""

    def __init__(self, names, parents, rest_world):
        self.names = list(names)
        self.parent = dict(parents)
        self.rest_world = {n: np.array(m, float) for n, m in rest_world.items()}
        self.children = {n: [] for n in self.names}
        for n in self.names:
            p = self.parent.get(n)
            if p:
                self.children[p].append(n)
        self.rest_local = {}
        for n in self.names:
            p = self.parent.get(n)
            self.rest_local[n] = np.linalg.inv(self.rest_world[p]) @ self.rest_world[n] if p else self.rest_world[n].copy()


class Pose:
    def __init__(self, sk, root_xf):
        self.sk = sk
        self.local = {n: m.copy() for n, m in sk.rest_local.items()}
        self.root_xf = root_xf
        self._w = None

    def world(self):
        if self._w is None:
            w = {}
            for n in self.sk.names:
                p = self.sk.parent.get(n)
                w[n] = (w[p] if p else self.root_xf) @ self.local[n]
            self._w = w
        return self._w

    def W(self, n):
        return self.world()[n]

    def P(self, n):
        return self.world()[n][:3, 3].copy()

    def set_world(self, n, M):
        """SafeSetCSBoneTransforms: the bone set in component space, its children following by their local transforms."""
        p = self.sk.parent.get(n)
        base = self.W(p) if p else self.root_xf
        self.local[n] = np.linalg.inv(base) @ M
        self._w = None


def _bone_m(R, p):
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = p
    return M


def hand_frame(wrist, middle, index, pinky):
    x = middle - wrist
    x = x / np.linalg.norm(x)
    z = np.cross(x, index - pinky)
    z = z / np.linalg.norm(z)
    y = np.cross(z, x)
    return np.column_stack([x, y, z])


def solve_two_bone(U, L, E, pole, eff, stretch_max):
    """AnimationCore::SolveTwoBoneIK on positions: the new elbow and end positions (and whether it reached)."""
    upper = np.linalg.norm(L - U)
    lower = np.linalg.norm(E - L)
    d = eff - U
    dl = np.linalg.norm(d)
    ddir = d / max(dl, 1e-9)
    maxl = upper + lower
    if stretch_max > 1.0 and dl > maxl:
        s = min(dl / maxl, stretch_max)
        upper, lower, maxl = upper * s, lower * s, maxl * s
    jt = pole - U
    jn = jt - ddir * np.dot(jt, ddir)
    if np.linalg.norm(jn) < 1e-6:
        jn = np.cross(ddir, [0, 0, 1])
    jn = jn / np.linalg.norm(jn)
    if dl >= maxl:
        newL = U + ddir * upper
        newE = U + ddir * maxl
        reached = False
    else:
        a = (upper * upper - lower * lower + dl * dl) / (2 * dl)
        h = math.sqrt(max(upper * upper - a * a, 0.0))
        newL = U + ddir * a + jn * h
        newE = eff.copy()
        reached = True
    return newL, newE, reached


FINGERS = ("thumb", "index", "middle", "ring", "pinky")


def solve_hand(pose, side, shape, target_palm, pole_shift, stretch, clip, cam_ok=True):
    """MIFirstPersonAnim SolveHand for one arm (Weight 1, ShapeWeight 1 when a shape is given). Returns a report."""
    sk = pose.sk
    U_n, L_n, E_n = "upperarm_" + side, "lowerarm_" + side, "hand_" + side
    U, L, E = pose.P(U_n), pose.P(L_n), pose.P(E_n)
    palm_off = pose.P("middle_metacarpal_" + side) - E
    eff = target_palm - palm_off
    shaped_R = None
    if shape:
        names = [E_n, "middle_01_" + side, "index_01_" + side, "pinky_01_" + side]
        Qc = hand_frame(*[pose.P(n) for n in names])
        Qt = hand_frame(*[shape[n] for n in names])
        shaped_R = Qt @ Qc.T @ pose.W(E_n)[:3, :3]
        eff = shape[E_n].copy()
    # the clip's elbow (ClipModel) stands in for L; the pole as the game builds it
    mid = (U + E) * 0.5
    off = clip.pole_l if side == "l" else clip.pole_r
    Lc = (U + eff) * 0.5 + off
    pole = Lc + (Lc - (U + eff) * 0.5) * 2.0 + pole_shift
    newL, newE, reached = solve_two_bone(U, L, E, pole, eff, stretch)
    # rotations: the upper arm swung onto U->newL, the forearm onto newL->newE (children follow), the end placed
    WU = pose.W(U_n)
    pose.set_world(U_n, _bone_m(find_between(L - U, newL - U) @ WU[:3, :3], U))
    L2, E2 = pose.P(L_n), pose.P(E_n)
    WL = pose.W(L_n)
    pose.set_world(L_n, _bone_m(find_between(E2 - L2, newE - L2) @ WL[:3, :3], L2))
    WE = pose.W(E_n)
    R = shaped_R if shaped_R is not None else WE[:3, :3]
    pose.set_world(E_n, _bone_m(R, newE))
    if shape:
        shape_fingers(pose, side, shape)
    Lw = pose.P(L_n)
    bend = 180.0 - math.degrees(math.acos(np.clip(np.dot((U - Lw) / np.linalg.norm(U - Lw), (newE - Lw) / np.linalg.norm(newE - Lw)), -1, 1)))
    return {"reached": reached, "gap_cm": float(np.linalg.norm(newE - eff)), "elbow": Lw, "bend_deg": bend,
            "shoulder": U, "wrist": newE, "pole": pole}


def shape_fingers(pose, side, shape):
    sk = pose.sk
    for f in FINGERS:
        chain = ([] if f == "thumb" else ["%s_metacarpal_%s" % (f, side)]) + ["%s_%02d_%s" % (f, k, side) for k in (1, 2, 3)]
        tip = "%s_tip_%s" % (f, side)
        for i, b in enumerate(chain):
            if b not in sk.parent:
                continue
            child = chain[i + 1] if i + 1 < len(chain) else tip
            if b not in shape or child not in shape:
                continue
            Wb = pose.W(b)
            if i + 1 < len(chain):
                cur = pose.P(chain[i + 1]) - Wb[:3, 3]
            else:
                ref = sk.rest_local[b]
                cur = Wb[:3, :3] @ (ref[:3, :3].T @ ref[:3, 3])
            want = shape[child] - shape[b]
            if np.linalg.norm(cur) < 1e-9 or np.linalg.norm(want) < 1e-9:
                continue
            pose.set_world(b, _bone_m(find_between(cur, want) @ Wb[:3, :3], Wb[:3, 3]))


# ------------------------------------------------------------------------------------------------ one frame
def frame(gun, state, sk, sockets, clip, ref_hip_rot=None):
    """Everything the rig does for one frozen frame. sockets: gun mesh-space socket positions (cm). Returns a dict with
    the gun and magazine matrices (camera space), the arms' pose and the reports of both hands."""
    G = gun.gun_matrix(state)
    m, drop = gun.magazine_drop(state)
    MagW = ue_mul(tf(None, drop), G)          # Held->GetRelativeTransform() * Gun->GetSocketTransform(MagBone)
    aim_k = smooth(gun.ads(state))
    mag_k = gun.mag_hold(state)
    # the arms' rotation: Hand.Inverse() * Grip with the clip's hand constant (ClipModel), i.e. the arms turn with the gun
    Rg = G[:3, :3]
    Rref = ref_hip_rot if ref_hip_rot is not None else gun.gun_matrix("hip")[:3, :3]
    blade = q_mat(q_axis((1, 0, 0), math.radians(clip.roll_deg))) @ q_mat(q_axis((0, 0, 1), math.radians(clip.blade_deg)))
    Rarms = Rg @ Rref.T @ blade @ q_mat(ARMS_REST)
    mid = (sk.rest_world["upperarm_l"][:3, 3] + sk.rest_world["upperarm_r"][:3, 3]) * 0.5
    t = gun.shoulders - Rarms @ mid
    root = _bone_m(Rarms, t)
    pose = Pose(sk, root)
    if clip.shoulder_l is not None:
        half = Rg @ Rref.T @ clip.shoulder_l
        for n, p in (("upperarm_l", gun.shoulders + half), ("upperarm_r", gun.shoulders - half)):
            Wn = pose.W(n)
            pose.set_world(n, _bone_m(Wn[:3, :3], p))
    reports = {}
    for side, sock in (("l", "Palm_L"), ("r", "Palm_R")):
        pts = gun.grip_hip[side]
        aimed = gun.grip_aim.get(side, {})
        shape = {}
        for k, v in pts.items():
            p = v + (aimed[k] - v) * aim_k if k in aimed else v
            shape[k] = xp(G, p)
        target = xp(G, sockets[sock])
        carry = side == "l" and mag_k > 0.0
        if carry:
            solved = gun.reload_points
            for k in list(shape):
                if k in solved:
                    shape[k] = shape[k] + (xp(MagW, solved[k]) - shape[k]) * mag_k
            if "middle_metacarpal_l" in solved:
                target = target + (xp(MagW, solved["middle_metacarpal_l"]) - target) * mag_k
        shift = np.zeros(3)
        if side == "l":
            shift = (gun.elbow_out + (gun.elbow_out_aim - gun.elbow_out) * aim_k) * (1.0 - mag_k)
        reports[side] = solve_hand(pose, side, shape, target, shift, gun.arm_stretch if side == "l" else 1.0, clip)
        reports[side]["shape"] = shape
    # the support-arm log line (UpdateHands): the forearm's slope on the screen
    Lw, Hw = pose.P("lowerarm_l"), pose.P("hand_l")
    F = Hw - Lw
    reports["l"]["slope_deg"] = math.degrees(math.atan2(F[2], F[1]))
    return {"G": G, "MagW": MagW, "mag_drop": m, "mag_k": mag_k, "aim_k": aim_k, "pose": pose, "reports": reports}
