"""Calibrate fp_math.ClipModel (the pack idle's part in the arms: the shoulder line's turn, the elbow pole) against the
game's own development log (HANDS_R4.md 9.3, runs t1 / t2: the support elbow's bend and the forearm's slope on the
screen, hip / aimed, with no elbow push and with the data's push).

    /home/user/mi-venv/bin/python tools/box/fp/offline/calibrate.py           # the fit
    /home/user/mi-venv/bin/python tools/box/fp/offline/calibrate.py --reach   # the firing arm's reach, from the log alone
    /home/user/mi-venv/bin/python tools/box/fp/offline/calibrate.py --scan    # a shoulders anchor both arms reach from

Prints the best fit and its residuals. The fit is two stages: the shoulder line (blade about the camera's Z, roll
about its X) from the eight elbow bends (the bend depends only on where the shoulder is), then the pole offset from
the slopes. No rendering.
"""
import itertools
import math
import os
import sys
import warnings

import bpy
import numpy as np

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_math as fm  # noqa: E402
import fp_offline as fo  # noqa: E402

# HANDS_R4.md 9.3: (gun, state) -> (bend with no push, slope with no push, slope with the data's push)
LOG = {
    ("chopper", "hip"): (103, 98, 52), ("chopper", "aim"): (114, 120, 60),
    ("rattler", "hip"): (87, 95, 52), ("rattler", "aim"): (118, 118, 57),
    ("stretch", "hip"): (99, 96, None), ("stretch", "aim"): (125, 117, None),
    ("shorty", "hip"): (116, 104, None), ("shorty", "aim"): (62, 121, None),
}
# the SHORTY was tuned with [-10, -40, -20] (its data value): 57 / 90
SHORTY_PUSH = {"hip": 57, "aim": 90}


def skeleton():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    root, objs = fo.import_glb(os.path.join(fm.GLB, "SK_RuleArms.glb"), "Arms")
    arm = [o for o in objs if o.type == "ARMATURE"][0]
    names, parents, rest = [], {}, {}
    for b in arm.data.bones:
        names.append(b.name)
        parents[b.name] = b.parent.name if b.parent else None
        rest[b.name] = fo.ue_from_bl_matrix(np.array(b.matrix_local))
    return fm.Skeleton(names, parents, rest)


class TurnedClip(fm.ClipModel):
    pass


def run(sk, guns, clip, roll, push=True):
    out = {}
    ref = guns["chopper"].gun_matrix("hip")[:3, :3]
    for (gid, st), want in LOG.items():
        g = guns[gid]
        save = g.elbow_out.copy(), g.elbow_out_aim.copy()
        if not push:
            g.elbow_out[:] = 0
            g.elbow_out_aim[:] = 0
        # the roll of the shoulder line about the camera's X, applied with the blade (fm.frame reads clip.blade_deg only)
        F = fm.frame(g, st, sk, {"Palm_L": np.zeros(3), "Palm_R": np.zeros(3)}, clip, ref_hip_rot=ref)
        g.elbow_out[:], g.elbow_out_aim[:] = save
        out[(gid, st)] = (F["reports"]["l"]["bend_deg"], F["reports"]["l"]["slope_deg"], F["reports"]["l"]["reached"])
    return out


def main():
    sk = skeleton()
    guns = {g: fm.Gun(g) for g in ("chopper", "rattler", "stretch", "shorty")}
    def bend_err(v):
        clip = fm.ClipModel(0.0, (0, -6, -10), (0, 6, -10), 0.0, v)
        r = run(sk, guns, clip, None, push=False)
        return sum((r[k][0] - LOG[k][0]) ** 2 for k in LOG), r
    # coarse grid, then a pattern search (cm)
    best = None
    for x, y, z in itertools.product(range(0, 31, 6), range(-24, 1, 6), range(-12, 13, 6)):
        e, r = bend_err(np.array([x, y, z], float))
        if best is None or e < best[0]:
            best = (e, np.array([x, y, z], float), r)
    step = 3.0
    while step > 0.4:
        moved = False
        for d in np.vstack([np.eye(3), -np.eye(3)]):
            v = best[1] + d * step
            e, r = bend_err(v)
            if e < best[0]:
                best, moved = (e, v, r), True
        if not moved:
            step /= 2
    err, sh, r = best
    blade, roll_deg = 0.0, 0.0
    print("SHOULDERS left shoulder from the midpoint %s cm (camera space at the CHOPPER's hip): rms bend error %.1f deg" % (np.round(sh, 1).tolist(), math.sqrt(err / len(LOG))))
    for k in LOG:
        print("  %-8s %-4s bend %5.1f (log %d)  reached %s" % (k[0], k[1], r[k][0], LOG[k][0], r[k][2]))
    roll = None
    bestp = None
    for py, pz, mag in itertools.product(range(-10, 11, 2), range(-10, 11, 2), (4, 8, 12, 16, 22, 30)):
        v = np.array([0, py, pz], float)
        if np.linalg.norm(v) < 1e-6:
            continue
        v = v / np.linalg.norm(v) * mag
        clip = fm.ClipModel(0.0, v, (0, 6, -10), 0.0, sh)
        a = run(sk, guns, clip, roll, push=False)
        b = run(sk, guns, clip, roll, push=True)
        e = 0.0
        n = 0
        for k, (bend, s0, s1) in LOG.items():
            e += (a[k][1] - s0) ** 2
            n += 1
            want1 = s1 if s1 is not None else (SHORTY_PUSH[k[1]] if k[0] == "shorty" else None)
            if want1 is not None:
                e += (b[k][1] - want1) ** 2
                n += 1
        if bestp is None or e < bestp[0]:
            bestp = (e / n, v, a, b)
    e, v, a, b = bestp
    print("POLE_L offset %s cm: rms slope error %.1f deg" % (np.round(v, 2).tolist(), math.sqrt(e)))
    for k, (bend, s0, s1) in LOG.items():
        want1 = s1 if s1 is not None else (SHORTY_PUSH[k[1]] if k[0] == "shorty" else None)
        print("  %-8s %-4s slope none %6.1f (log %d)   pushed %6.1f (log %s)" % (k[0], k[1], a[k][1], s0, b[k][1], want1))


if __name__ == "__main__" and "--reach" not in sys.argv and "--scan" not in sys.argv:
    main()


def reach_bound():
    """The firing arm's reach, bounded from the log alone (no clip model): the code puts the shoulders' midpoint M on the
    anim set's `shoulders`; the logged support bend fixes |L - Wl| (L the left shoulder, Wl the support wrist the shape
    asks for); the right shoulder is R = 2M - L. The nearest R can come to the firing wrist Wr is |Wl - (2M - Wr)| - |L - Wl|.
    If that exceeds the arm (upper + fore arm, the firing arm never stretches), the firing hand cannot reach the grip
    whatever the clip does."""
    sk = skeleton()
    up = np.linalg.norm(sk.rest_world["lowerarm_l"][:3, 3] - sk.rest_world["upperarm_l"][:3, 3])
    fo_ = np.linalg.norm(sk.rest_world["hand_l"][:3, 3] - sk.rest_world["lowerarm_l"][:3, 3])
    upr = np.linalg.norm(sk.rest_world["lowerarm_r"][:3, 3] - sk.rest_world["upperarm_r"][:3, 3])
    for_ = np.linalg.norm(sk.rest_world["hand_r"][:3, 3] - sk.rest_world["lowerarm_r"][:3, 3])
    print("ARM upper %.2f fore %.2f (left), %.2f %.2f (right) cm: the firing arm reaches %.1f cm" % (up, fo_, upr, for_, upr + for_))
    for (gid, st), (bend, _, _) in LOG.items():
        g = fm.Gun(gid)
        G = g.gun_matrix(st)
        k = fm.smooth(g.ads(st))
        def pt(side, n):
            p = g.grip_hip[side][n]
            a = g.grip_aim.get(side, {})
            return fm.xp(G, p + (a[n] - p) * k if n in a else p)
        Wl, Wr = pt("l", "hand_l"), pt("r", "hand_r")
        interior = math.radians(180 - bend)
        dl = math.sqrt(up * up + fo_ * fo_ - 2 * up * fo_ * math.cos(interior))
        M = g.shoulders
        nearest = np.linalg.norm(Wl - (2 * M - Wr)) - dl
        print("  %-8s %-4s support shoulder-wrist %.1f cm (bend %d); firing shoulder at least %.1f cm from the firing wrist: %s by %.1f cm"
              % (gid, st, dl, bend, nearest, "SHORT" if nearest > upr + for_ else "can reach", nearest - (upr + for_)))


if __name__ == "__main__" and "--reach" in sys.argv:
    reach_bound()


def scan_shoulders():
    """A `shoulders` anchor for the four rifles that lets both arms reach in every state (hip, aimed, reload 0.5 / 1.1 s),
    with the calibrated clip: the smallest move from the data's [-10, -14, -7]. Offline numbers only; a starting value
    to be seen on the box (the upper arms in the picture are not checked here)."""
    import fp_offline as fo_
    sk = skeleton()
    clip = fm.ClipModel(0.0, fo_.CLIP_DEFAULT["pole_l"], fo_.CLIP_DEFAULT["pole_r"], 0.0, fo_.CLIP_DEFAULT["shoulder_l"])
    guns = {g: fm.Gun(g) for g in ("chopper", "stretch", "rattler", "shorty")}
    ref = guns["chopper"].gun_matrix("hip")[:3, :3]
    states = ("hip", "aim", ("reload", 0.5), ("reload", 1.1))
    socks = {"Palm_L": np.zeros(3), "Palm_R": np.zeros(3)}
    base = np.array([-10.0, -14.0, -7.0])
    rows = []
    for x, y, z in itertools.product(range(-14, 3, 2), range(-14, 9, 2), range(-30, -3, 2)):
        a = np.array([x, y, z], float)
        worst, bend_r = 0.0, 180.0
        for gid in ("chopper", "stretch", "rattler"):
            g = guns[gid]
            g.shoulders = a
            for st in states:
                F = fm.frame(g, st, sk, socks, clip, ref_hip_rot=ref)
                R = F["reports"]
                worst = max(worst, R["r"]["gap_cm"], R["l"]["gap_cm"])
                bend_r = min(bend_r, R["r"]["bend_deg"])
        rows.append((worst, -min(bend_r, 25.0), float(np.linalg.norm(a - base)), a, bend_r))
    rows.sort(key=lambda r: (round(r[0], 1), r[1], r[2]))
    print("SCAN the shoulders anchor (camera cm) for CHOPPER, STRETCH, RATTLER, every state: worst hand gap, least firing bend")
    for worst, _, dist, a, bend_r in rows[:8]:
        print("  %s  worst gap %.1f cm  firing elbow bent at least %.0f deg  (%.1f cm from the data's)" % (a.tolist(), worst, bend_r, dist))


if __name__ == "__main__" and "--scan" in sys.argv:
    scan_shoulders()
