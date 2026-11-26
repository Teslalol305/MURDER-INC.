"""Tune the first-person data offline against the reconstruction (HANDS_R4.md 13): a reload pose that brings the magazine
and the support hand into the picture, and a `shoulders` anchor from which both arms reach. No rendering; the numbers
are the game's maths (fp_math) on the meshes the game draws. What it finds is checked with fp_offline renders.

    /home/user/mi-venv/bin/python tools/box/fp/offline/tune.py pose GUN [--shoulders X,Y,Z] [--target U,V]
    /home/user/mi-venv/bin/python tools/box/fp/offline/tune.py shoulders GUN[,GUN...] [--around X,Y,Z]
    /home/user/mi-venv/bin/python tools/box/fp/offline/tune.py elbow GUN [--shoulders X,Y,Z]

pose: a local search over `poses.reload` (web: x, y, z m; pitch, yaw, roll rad) from the data's value. Cost: the
magazine (its vertices, at 0.5 and 1.1 s) inside the picture and its centre near the target (frame fractions from the
top left) at 0.5 s; its left face (the face the hand leaves free) turned toward the eye; both hands reaching; no part of
the gun nearer the eye than 15 cm; the pose near the data's.
shoulders: the anchor (camera cm) nearest the data's from which both arms reach in every state (hip, aimed, reload
0.5 / 1.1 s) with the firing elbow bent at least 35 degrees and the support arm unstretched.
elbow: supportElbowOut / supportElbowOutAim that give the support forearm the slope the 9.3 tuning settled on (hip 52,
aimed 60 degrees on the screen) from the anchor given.
"""
import argparse
import itertools
import json
import math
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_math as fm  # noqa: E402
import fp_offline as fo  # noqa: E402

STATES = ("hip", "aim", ("reload", 0.5), ("reload", 1.1))


class Rig:
    """One gun's scene (meshes imported once), posed by fp_math for any data the caller sets on .gun."""

    def __init__(self, gid):
        args = argparse.Namespace(samples=1, threads=4, res=320, tex_set=None, finish="textured", hdri=None)
        fo.OUT_TEX = os.path.join(fm.ROOT, "art", "out", "fp-offline", "tex")
        os.makedirs(fo.OUT_TEX, exist_ok=True)
        self.S = fo.Scene(gid, args)
        self.gun = self.S.gun
        self.clip = fo.fm.ClipModel(0.0, fo.CLIP_DEFAULT["pole_l"], fo.CLIP_DEFAULT["pole_r"], 0.0,
                                    None if gid == "nine" else fo.CLIP_DEFAULT["shoulder_l"])
        self.ref = fm.Gun("chopper").gun_matrix("hip")[:3, :3]
        self.mag_v = self._verts(self.S.mag_meshes, self.S.mag_root)
        self.gun_v = self._verts(self.S.gun_meshes, self.S.gun_root)
        self.mag_c = (self.mag_v.min(0) + self.mag_v.max(0)) * 0.5

    def _verts(self, objs, root):
        """Vertices in the root's own frame (the gun's / the magazine's mesh space), Unreal cm, every 7th."""
        import bpy
        root.matrix_world = fo.to_mat(np.eye(4))
        bpy.context.view_layer.update()
        out = []
        for o in objs:
            co = np.empty(len(o.data.vertices) * 3)
            o.data.vertices.foreach_get("co", co)
            co = np.c_[co.reshape(-1, 3), np.ones(len(o.data.vertices))]
            out.append(((np.array(o.matrix_world) @ co.T).T[:, :3] @ fo.D) * 100.0)
        v = np.vstack(out) if out else np.zeros((1, 3))
        return v[::7]

    def frame(self, state):
        return fm.frame(self.gun, state, self.S.sk, self.S.sockets, self.clip, ref_hip_rot=self.ref if self.gun.id != "nine" else None)


def project(gun, state, P):
    """Camera-space points (cm) to frame fractions (u from the left, v from the top) for the state's field of view."""
    tv = math.tan(math.radians(gun.fov_v(state)) * 0.5)
    th = tv * 16.0 / 9.0
    X = np.maximum(P[:, 0], 1e-3)
    return np.c_[0.5 + P[:, 1] / X / (2 * th), 0.5 - P[:, 2] / X / (2 * tv)], P[:, 0] > 1.0


def mag_in_view(rig, F, state):
    P = (F["MagW"][:3, :3] @ rig.mag_v.T).T + F["MagW"][:3, 3]
    uv, front = project(rig.gun, state, P)
    inside = front & (uv[:, 0] > 0.03) & (uv[:, 0] < 0.97) & (uv[:, 1] > 0.03) & (uv[:, 1] < 0.95)
    c = fm.xp(F["MagW"], rig.mag_c)
    cuv, _ = project(rig.gun, state, c[None, :])
    eye = F["MagW"][:3, :3].T @ (-c)
    eye /= np.linalg.norm(eye)
    return float(inside.mean()), cuv[0], eye


def pose_cost(rig, p, p0, target, verbose=False):
    g = rig.gun
    g.poses = dict(g.poses, reload=list(p))
    cost = 0.0
    rows = {}
    for t in (0.5, 1.1):
        st = ("reload", t)
        F = rig.frame(st)
        inside, cuv, eye = mag_in_view(rig, F, st)
        G = F["G"]
        gv = (G[:3, :3] @ rig.gun_v.T).T + G[:3, 3]
        near = float(np.linalg.norm(gv, axis=1).min())
        R = F["reports"]
        cost += 12.0 * (1.0 - inside)
        if t == 0.5:
            cost += 8.0 * float(np.sum((cuv - target) ** 2)) * 10
        cost += 2.0 * max(0.0, eye[1] + 0.45)                    # the left face toward the eye
        cost += 3.0 * max(0.0, 15.0 - near)
        cost += 1.5 * (R["l"]["gap_cm"] + R["r"]["gap_cm"])
        rows[t] = {"mag_inside": round(inside, 3), "mag_centre_uv": cuv.round(3).tolist(), "eye_in_mag": eye.round(2).tolist(),
                   "gun_nearest_cm": round(near, 1), "gap_l": round(R["l"]["gap_cm"], 1), "gap_r": round(R["r"]["gap_cm"], 1)}
    d = (np.array(p) - p0) / np.array([0.05, 0.05, 0.05, 0.4, 0.4, 0.5])
    cost += 0.3 * float(np.sum(d ** 2))
    if verbose:
        return cost, rows
    return cost


def tune_pose(gid, shoulders, target):
    rig = Rig(gid)
    if shoulders is not None:
        rig.gun.shoulders = np.array(shoulders, float)
    p0 = np.array(rig.gun.poses["reload"], float)
    lo = np.array([-0.05, -0.25, -0.40, -0.3, -0.4, -1.4])
    hi = np.array([0.20, 0.05, -0.15, 0.9, 0.9, 0.3])
    best = (pose_cost(rig, p0, p0, target), p0.copy())
    print("START", p0.round(3).tolist(), round(best[0], 3), json.dumps(pose_cost(rig, p0, p0, target, True)[1]))
    steps = np.array([0.02, 0.02, 0.02, 0.1, 0.1, 0.1])
    while steps[0] > 0.002:
        moved = False
        for i in range(6):
            for sgn in (1, -1):
                q = best[1].copy()
                q[i] = min(hi[i], max(lo[i], q[i] + sgn * steps[i]))
                c = pose_cost(rig, q, p0, target)
                if c < best[0] - 1e-6:
                    best, moved = (c, q), True
        if not moved:
            steps *= 0.5
    p = [round(float(x), 3) for x in best[1]]
    c, rows = pose_cost(rig, np.array(p), p0, target, True)
    print("BEST", p, round(c, 3), json.dumps(rows))
    return p


def reach_rows(rig, anchor, states=STATES):
    g = rig.gun
    g.shoulders = np.array(anchor, float)
    rows = []
    for st in states:
        F = rig.frame(st)
        R = F["reports"]
        rows.append((st, R["l"]["gap_cm"], R["r"]["gap_cm"], R["r"]["bend_deg"], R["l"]["bend_deg"], R["l"]["slope_deg"]))
    return rows


def scan_shoulders(gids, around):
    rigs = [Rig(g) for g in gids]
    base = np.array(around, float)
    found = []
    for x, y, z in itertools.product(range(-10, 15, 2), range(-14, 13, 2), range(-34, -3, 2)):
        a = np.array([x, y, z], float)
        worst, bend_r, bend_l = 0.0, 180.0, 180.0
        for rig in rigs:
            for st, gl, gr, br, bl, _ in reach_rows(rig, a):
                worst = max(worst, gl, gr)
                bend_r = min(bend_r, br)
                bend_l = min(bend_l, bl)
        if worst < 0.05 and bend_r >= 35.0:
            found.append((float(np.linalg.norm(a - base)), a, bend_r, bend_l))
    found.sort(key=lambda r: r[0])
    print("SHOULDERS for %s: both arms reach in every state, the firing elbow bent 35 degrees or more, nearest %s first" % (",".join(gids), base.tolist()))
    for d, a, br, bl in found[:10]:
        print("  %s  %.1f cm away  firing bend >= %.0f  support bend >= %.0f" % (a.tolist(), d, br, bl))
    return found[0][1].tolist() if found else None


def tune_elbow(gid, shoulders, want=(52.0, 60.0)):
    rig = Rig(gid)
    if shoulders is not None:
        rig.gun.shoulders = np.array(shoulders, float)
    g = rig.gun
    out = {}
    for st, key, w in (("hip", "elbow_out", want[0]), ("aim", "elbow_out_aim", want[1])):
        best = None
        for s in np.arange(0.0, 1.61, 0.05):
            v = np.array([-10.0, -60.0, -30.0]) * s
            setattr(g, key, v)
            if key == "elbow_out":
                g.elbow_out_aim = g.elbow_out_aim if "aim" in out else v
            F = rig.frame(st)
            sl = F["reports"]["l"]["slope_deg"]
            c = abs(sl - w)
            if best is None or c < best[0]:
                best = (c, v.round(1).tolist(), sl, F["reports"]["l"]["bend_deg"])
        setattr(g, key, np.array(best[1]))
        out[st] = best
        print("ELBOW %s %s: push %s gives the forearm %.1f deg on the screen (want %.0f), elbow bent %.0f" % (gid, st, best[1], best[2], w, best[3]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("pose", "shoulders", "elbow", "report"))
    ap.add_argument("guns")
    ap.add_argument("--shoulders", default=None)
    ap.add_argument("--around", default="-10,-14,-7")
    ap.add_argument("--target", default="0.42,0.68")
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    sh = [float(x) for x in a.shoulders.split(",")] if a.shoulders else None
    if a.what == "pose":
        tune_pose(a.guns, sh, np.array([float(x) for x in a.target.split(",")]))
    elif a.what == "shoulders":
        scan_shoulders(a.guns.split(","), [float(x) for x in a.around.split(",")])
    elif a.what == "elbow":
        tune_elbow(a.guns, sh)
    else:
        for gid in a.guns.split(","):
            rig = Rig(gid)
            if sh:
                rig.gun.shoulders = np.array(sh, float)
            for st in STATES:
                F = rig.frame(st)
                inside, cuv, eye = mag_in_view(rig, F, st)
                R = F["reports"]
                print("REPORT %-8s %-14s mag in picture %.2f centre %s | gap l %.1f r %.1f | bend l %.0f r %.0f | slope l %.0f"
                      % (gid, st, inside, cuv.round(2).tolist(), R["l"]["gap_cm"], R["r"]["gap_cm"], R["l"]["bend_deg"], R["r"]["bend_deg"], R["l"]["slope_deg"]))


if __name__ == "__main__":
    main()
