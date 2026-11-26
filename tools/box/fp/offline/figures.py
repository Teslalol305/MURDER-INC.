"""The evidence sheets of HANDS_R4.md 12 from fp_offline.py's output (each under 300 KB, docs/unreal/shots/):

  hands-offline-validation.jpg  the game's own frames (vis-*.jpg panels) with the offline outlines drawn over them: gun
                                red, support arm green, firing arm yellow; the projected sights and muzzle as crosses
  hands-offline-reach.jpg       the rifles as the data has them against the what-if shoulders anchor [2, 0, -16]
                                (eye and right side, hip and reload 0.5 s)
  hands-offline-finish.jpg      the SHORTY with its own textures, with every texture read as 0, and the game's frames
  hands-offline-shorty-aim.jpg  the SHORTY aimed: relief 0.22 m (data) and 0.12 m, from the eye and from the right

    python3 tools/box/fp/offline/figures.py OUT_DIR DEST_DIR
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheets import font, save_small  # noqa: E402
from validate import outline, project  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
SHOTS = os.path.join(ROOT, "docs", "unreal", "shots")

# (game sheet, panel 0..3, offline key, label)
GAME = [
    ("hands-r4c-p1-chopper-hip.jpg", None, "chopper-hip", "CHOPPER hip (p1)"),
    ("vis-hands-hip-hudoff.jpg", 0, "stretch-hip", "STRETCH hip (h1b)"),
    ("vis-hands-rattler.jpg", 0, "rattler-hip", "RATTLER hip (h1c)"),
    ("vis-hands-reload-eye.jpg", 0, "stretch-r0.5", "STRETCH reload 0.5 s (h1b)"),
    ("vis-hands-rattler.jpg", 2, "rattler-r0.5", "RATTLER reload 0.5 s (h1c)"),
    ("vis-hands-rattler.jpg", 3, "rattler-r1.1", "RATTLER reload 1.1 s (h1c)"),
    ("vis-hands-reload-eye.jpg", 1, "shorty-r1.1", "SHORTY reload 1.1 s (h1b)"),
    ("vis-stick-scope-and-aims.jpg", 2, "shorty-aim", "SHORTY aimed, irons (h1b)"),
    ("vis-hands-reload-eye.jpg", 3, "nine-r0.5", "NINE reload 0.5 s (h3)"),
]


def game_panel(sheet, panel):
    im = Image.open(os.path.join(SHOTS, sheet)).convert("RGB")
    if panel is None:
        return im
    x, y = (panel % 2) * 800, (panel // 2) * 450
    return im.crop((x, y, x + 800, y + 450))


def overlay(out_dir, key, game, w=480):
    h = w * 9 // 16
    idp = os.path.join(out_dir, key.replace(".", "") + "-id.png")
    ids = np.asarray(Image.open(idp).convert("RGB").resize((w, h), Image.NEAREST)).astype(int)
    g = np.asarray(game.resize((w, h))).copy()
    r_, g_, b_ = ids[..., 0] > 128, ids[..., 1] > 128, ids[..., 2] > 128
    for m, col in (((b_ & ~r_ & ~g_) | (r_ & ~g_ & ~b_), (255, 30, 30)), (g_ & ~r_ & ~b_, (40, 255, 40)), (r_ & g_ & ~b_, (255, 230, 0))):
        g[outline(m)] = col
    im = Image.fromarray(g)
    d = ImageDraw.Draw(im)
    rep = json.load(open(os.path.join(out_dir, "report.json")))[key]
    for n, p in rep["sockets_cam_cm"].items():
        if n in ("SightFront", "SightRear", "Muzzle") and p[0] > 1:
            x, y = project(p, rep["fov_v"], w, h)
            d.line([(x - 5, y), (x + 5, y)], fill=(0, 255, 255), width=2)
            d.line([(x, y - 5), (x, y + 5)], fill=(0, 255, 255), width=2)
    return im


def grid(cells, cols, w=480, strip=20, title=None):
    h = w * 9 // 16
    rows = (len(cells) + cols - 1) // cols
    top = 26 if title else 0
    im = Image.new("RGB", (cols * w, top + rows * (h + strip)), (18, 18, 18))
    d = ImageDraw.Draw(im)
    if title:
        d.text((6, 5), title, fill=(255, 255, 255), font=font(15))
    for i, (pic, label) in enumerate(cells):
        x, y = (i % cols) * w, top + (i // cols) * (h + strip)
        if pic is not None:
            im.paste(pic.convert("RGB").resize((w, h)), (x, y + strip))
        d.text((x + 4, y + 3), label, fill=(235, 235, 235), font=font(13))
    return im


def load(out_dir, name):
    p = os.path.join(out_dir, name)
    return Image.open(p) if os.path.exists(p) else None


def main():
    out_dir, dest = sys.argv[1], sys.argv[2]
    rep = json.load(open(os.path.join(out_dir, "report.json")))
    # validation
    cells = []
    for sheet, panel, key, label in GAME:
        if key in rep:
            cells.append((overlay(out_dir, key, game_panel(sheet, panel)), label + ": offline outlines over the game"))
    im = grid(cells, 3, title="The game's frames with the offline reconstruction's outlines: gun red, support arm green, firing arm yellow, sights and muzzle cyan")
    print("SHEET validation", save_small(im, os.path.join(dest, "hands-offline-validation.jpg")))
    # reach what-if
    cells = []
    for g in ("chopper", "stretch", "rattler"):
        for st in ("hip", "r05"):
            for suf, lab in (("", "data [-10, -14, -7]"), ("-sh2", "what-if [2, 0, -16]")):
                for cam in ("eye", "side"):
                    k = "%s-%s" % (g, st.replace("r05", "r0.5")) + suf
                    gap = rep.get(k, {}).get("r", {}).get("wrist_gap_cm")
                    cells.append((load(out_dir, "%s-%s%s-%s.jpg" % (g, st, suf, cam)),
                                  "%s %s %s, %s: firing hand %s" % (g.upper(), "hip" if st == "hip" else "reload 0.5 s", lab, cam,
                                                                    "on the grip" if gap == 0 else "%.1f cm short" % gap if gap is not None else "")))
    im = grid(cells, 4, w=360, title="Shoulders anchor: as the data has it, and a what-if from which both arms reach (fp_math, calibrated clip)")
    print("SHEET reach", save_small(im, os.path.join(dest, "hands-offline-reach.jpg")))
    # finish
    cells = [(load(out_dir, "shorty-aim-fin-textured-eye.jpg"), "offline SHORTY aimed: its own textures"),
             (load(out_dir, "shorty-aim-fin-zero-eye.jpg"), "offline: every gun texture read as 0"),
             (game_panel("vis-stick-scope-and-aims.jpg", 2), "game h1b: SHORTY aimed"),
             (load(out_dir, "shorty-r11-fin-textured-eye.jpg"), "offline SHORTY reload 1.1 s: own textures"),
             (load(out_dir, "shorty-r11-fin-zero-eye.jpg"), "offline: every gun texture read as 0"),
             (game_panel("vis-hands-reload-eye.jpg", 1), "game h1b: SHORTY reload 1.1 s (the STRETCH right in this session)"),
             (load(out_dir, "stretch-r11-fin-textured-eye.jpg"), "offline STRETCH reload 1.1 s: own textures"),
             (load(out_dir, "stretch-r11-fin-zero-eye.jpg"), "offline: every gun texture read as 0"),
             (game_panel("vis-hands-reload-eye.jpg", 0), "game h1b: STRETCH reload 0.5 s, walnut and paint")]
    im = grid(cells, 3, w=420, title="The finish: the guns' own textures and wiring give paint and walnut; zero-valued texture reads give the game's black mirror")
    print("SHEET finish", save_small(im, os.path.join(dest, "hands-offline-finish.jpg")))
    # SHORTY aimed
    cells = [(load(out_dir, "shorty-aim-eye.jpg"), "SHORTY aimed, relief 0.22 m (data): from the eye"),
             (load(out_dir, "shorty-aim-side.jpg"), "relief 0.22 m from the right: the eye (red) 8.6 cm behind the butt"),
             (load(out_dir, "shorty-aim-relief12-eye.jpg"), "what-if relief 0.12 m: from the eye"),
             (load(out_dir, "shorty-aim-relief12-side.jpg"), "relief 0.12 m from the right: the eye over the receiver"),
             (game_panel("vis-stick-scope-and-aims.jpg", 2), "game h1b: SHORTY aimed through the irons"),
             (load(out_dir, "stretch-aim-side.jpg"), "STRETCH aimed from the right (relief 0.12 m): the eye over the comb")]
    im = grid(cells, 2, w=480, title="SHORTY aimed: the eye relief puts the eye behind the bullpup's butt; its sight line is 0.4 to 0.8 cm over the receiver")
    print("SHEET shorty-aim", save_small(im, os.path.join(dest, "hands-offline-shorty-aim.jpg")))


if __name__ == "__main__":
    main()
