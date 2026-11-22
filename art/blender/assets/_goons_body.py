"""The Goons' shared body on the mannequin skeleton: region labels of the mannequin surface, sections measured
from it (the garments are cut to them), the landmarks every outfit uses (joints, hem heights, wrist and ankle
rings), the head under the mask, the gloves and the sneakers.

All positions are read from the imported mannequin (rest pose, metres, facing -Y); nothing is typed in except
ease, lengths and the brief's sizes.
"""
import numpy as np
from mathutils import Vector

from mi import char, rig

REGIONS = ("torso", "arm_l", "arm_r", "leg_l", "leg_r", "head", "hand_l", "hand_r", "foot_l", "foot_r")


def region_of(bone):
    if bone == "head":
        return "head"
    for side in ("l", "r"):
        if bone.endswith("_" + side):
            b = bone[:-2]
            if b in ("hand",) or any(b.startswith(f) for f in ("index", "middle", "ring", "pinky", "thumb")):
                return "hand_" + side
            if b.startswith(("upperarm", "lowerarm")):
                return "arm_" + side
            if b.startswith(("thigh", "calf")):
                return "leg_" + side
            if b in ("foot", "ball"):
                return "foot_" + side
            if b.startswith("clavicle"):
                return "torso"
    return "torso"


class Body:
    """Measured mannequin: `arm` (armature), `body` (mesh), `co` (n, 3) rest positions, `label` (n,) region
    index into REGIONS, joints J[name] (3,) and the section tables used to cut the garments."""

    def __init__(self, arm, body):
        self.arm, self.body = arm, body
        me = body.data
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        M = np.array(body.matrix_world)
        self.co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        names, W = rig.weight_table(body)
        dom = np.array(names)[np.argmax(W, axis=1)]
        self.bone = dom
        self.label = np.array([REGIONS.index(region_of(b)) for b in dom])
        self.J = {b.name: np.array(char.bone_frame(arm, b.name)[0]) for b in arm.data.bones}
        self.T = {b.name: np.array(char.bone_frame(arm, b.name)[1]) for b in arm.data.bones}
        self._torso()

    def pts(self, *regions):
        m = np.isin(self.label, [REGIONS.index(r) for r in regions])
        return self.co[m]

    # ------------------------------------------------------------------ torso sections by height
    def _torso(self):
        P = self.pts("torso")
        zs = np.arange(0.80, 1.56, 0.02)
        rows = []
        for z in zs:
            s = P[np.abs(P[:, 2] - z) < 0.012]
            if len(s) < 8:
                continue
            # the clavicle/shoulder region spreads into the arm root: keep the core within the shoulder joints
            xs = np.abs(s[:, 0])
            lim = abs(self.J["upperarm_l"][0]) + 0.02
            s = s[xs < lim]
            rows.append((z, np.abs(s[:, 0]).max(), s[:, 1].min(), s[:, 1].max()))
        self.torso = np.array(rows)        # z, half width, front y (min), back y (max)

    def torso_at(self, z):
        t = self.torso
        return (np.interp(z, t[:, 0], t[:, 1]), np.interp(z, t[:, 0], t[:, 2]), np.interp(z, t[:, 0], t[:, 3]))

    # ------------------------------------------------------------------ limb sections along a chain
    def limb_sections(self, side, kind, stations):
        """Measured half extents of an arm or leg around its axis. kind 'arm': shoulder -> elbow -> wrist;
        'leg': hip -> knee -> ankle. stations: fractions along the chain 0..2 (0 = top joint, 1 = middle joint,
        2 = end joint). Returns list of (centre, u, v, a, b) with u across (lateral) and v front-back."""
        if kind == "arm":
            j = [self.J["upperarm_" + side], self.J["lowerarm_" + side], self.J["hand_" + side]]
            P = self.pts("arm_" + side)
        else:
            j = [self.J["thigh_" + side], self.J["calf_" + side], self.J["foot_" + side]]
            P = self.pts("leg_" + side)
        out = []
        for s0 in stations:
            s = float(np.clip(s0, 0.08, 1.92))          # measured inside the chain, placed where asked
            k = min(int(s), 1)
            t = s - k
            A, B = j[k], j[k + 1]
            c = A + (B - A) * t
            w = (B - A) / np.linalg.norm(B - A)
            k0 = 0 if s0 < 1 else 1
            c_real = j[k0] + (j[k0 + 1] - j[k0]) * (s0 - k0)
            # section axes: v = front-back (world -Y projected), u = w x v
            fwd = np.array([0, -1.0, 0])
            if kind == "arm":
                # across the arm: the elbow hinge axis is roughly the world Y projected; v = "up" side
                v = np.array([0, 0, 1.0]) - w * w[2]
                v /= np.linalg.norm(v)
            else:
                v = fwd - w * (fwd @ w)
                v /= np.linalg.norm(v)
            u = np.cross(v, w)
            r = P - c
            ax = r @ w
            sel = np.abs(ax) < 0.015
            if sel.sum() < 6:
                sel = np.abs(ax) < 0.03
            q = r[sel] - np.outer(r[sel] @ w, w)
            x, y = q @ u, q @ v
            # robust extents (95th percentile of |x| and |y|) and the section centre offset
            cx, cy = 0.5 * (np.percentile(x, 98) + np.percentile(x, 2)), 0.5 * (np.percentile(y, 98) + np.percentile(y, 2))
            a = 0.5 * (np.percentile(x, 98) - np.percentile(x, 2))
            b = 0.5 * (np.percentile(y, 98) - np.percentile(y, 2))
            out.append((c_real + u * cx + v * cy, u, v, a, b))
        return out
