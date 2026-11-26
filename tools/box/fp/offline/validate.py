"""Check the offline reconstruction's framing against a frame the game took (HANDS_R4.md 12.2).

    python3 tools/box/fp/offline/validate.py GAME.jpg OFFLINE_ID.png REPORT.json KEY OUT.jpg [--crop-hud]

GAME.jpg: a play-in-editor frame (any 16:9 size); OFFLINE_ID.png: fp_offline.py's flat ID render of the same gun and
state (gun blue, magazine red, support arm green, firing arm yellow); REPORT.json / KEY: fp_offline.py's report and its
entry ("chopper-hip"). Writes OUT.jpg: the game frame with the offline gun's outline (red) and arms' outlines (green /
yellow) drawn over it, and the projected sockets (SightFront, SightRear, Muzzle) as crosses; prints the outline's box
against the game gun's box measured by `--box x0,y0,x1,y1` (fractions of the frame) when given.
"""
import argparse
import json
import math

import numpy as np
from PIL import Image, ImageDraw


def project(p, vfov, w, h):
    f = (h / 2) / math.tan(math.radians(vfov) / 2)
    return (w / 2 + p[1] / p[0] * f, h / 2 - p[2] / p[0] * f)


def outline(mask):
    m = mask.astype(bool)
    e = m.copy()
    e[1:, :] &= m[:-1, :]
    e[:-1, :] &= m[1:, :]
    e[:, 1:] &= m[:, :-1]
    e[:, :-1] &= m[:, 1:]
    return m & ~e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("game")
    ap.add_argument("idpng")
    ap.add_argument("report")
    ap.add_argument("key")
    ap.add_argument("out")
    ap.add_argument("--box", default=None, help="the game gun's box x0,y0,x1,y1 as fractions, read off the frame")
    a = ap.parse_args()
    ids = np.asarray(Image.open(a.idpng).convert("RGB")).astype(int)
    h, w = ids.shape[:2]
    game = Image.open(a.game).convert("RGB").resize((w, h))
    r, g, b = ids[..., 0] > 128, ids[..., 1] > 128, ids[..., 2] > 128
    gun = (b & ~r & ~g) | (r & ~g & ~b)
    left = g & ~r & ~b
    right = r & g & ~b
    out = np.asarray(game).copy()
    for m, col in ((gun, (255, 30, 30)), (left, (40, 255, 40)), (right, (255, 230, 0))):
        o = outline(m)
        out[o] = col
    im = Image.fromarray(out)
    d = ImageDraw.Draw(im)
    rep = json.load(open(a.report))[a.key]
    for name, p in rep["sockets_cam_cm"].items():
        if name in ("SightFront", "SightRear", "Muzzle") and p[0] > 1:
            x, y = project(p, rep["fov_v"], w, h)
            d.line([(x - 6, y), (x + 6, y)], fill=(0, 255, 255), width=2)
            d.line([(x, y - 6), (x, y + 6)], fill=(0, 255, 255), width=2)
    ys, xs = np.nonzero(gun)
    box = (xs.min() / w, ys.min() / h, (xs.max() + 1) / w, (ys.max() + 1) / h)
    print("OFFLINE gun box (fractions) x %.3f..%.3f  y %.3f..%.3f" % (box[0], box[2], box[1], box[3]))
    if a.box:
        gb = [float(v) for v in a.box.split(",")]
        d.rectangle([gb[0] * w, gb[1] * h, gb[2] * w, gb[3] * h], outline=(0, 200, 255))
        print("GAME    gun box (fractions) x %.3f..%.3f  y %.3f..%.3f" % (gb[0], gb[2], gb[1], gb[3]))
        print("DIFF    left %+.3f right %+.3f top %+.3f bottom %+.3f (fractions of the frame)" % (box[0] - gb[0], box[2] - gb[2], box[1] - gb[1], box[3] - gb[3]))
    im.save(a.out, quality=88)


if __name__ == "__main__":
    main()
