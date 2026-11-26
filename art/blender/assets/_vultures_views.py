"""Split a 4-view turnaround sheet (front, left, back, right in one row) into four square views at one common
scale, for Tripo multiview (docs/unreal/maps/characters.md 3.2). Needs only PIL and numpy:

    venv/bin/python -I art/blender/assets/_vultures_views.py art/out/characters/maps/<id>/src/sheet_v1.png \
        art/out/characters/maps/<id>/src/view

writes view_front.png, view_left.png, view_back.png, view_right.png (2048 x 2048). Figures are found as runs of
columns that differ from the background (the median of the top and bottom rows); the A-pose front figure is wider
than a quarter of the sheet, so the sheet is never cut in equal quarters.
"""
import sys

import numpy as np
from PIL import Image

def main(src, out_prefix):
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    bg = np.median(np.concatenate([a[:20].reshape(-1, 3), a[-20:].reshape(-1, 3)]), axis=0)
    diff = np.abs(a - bg).max(axis=2)
    mask = diff > 18
    col = mask.sum(axis=0) > 3
    runs, start = [], None
    for x, v in enumerate(col):
        if v and start is None:
            start = x
        if not v and start is not None:
            runs.append((start, x)); start = None
    if start is not None:
        runs.append((start, len(col)))
    runs = [r for r in runs if r[1] - r[0] > 40]
    # merge runs separated by small gaps (fingers, straps)
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < 25:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    print("runs", merged)
    assert len(merged) == 4, merged
    rows = mask.sum(axis=1) > 3
    y0, y1 = np.nonzero(rows)[0][[0, -1]]
    H = y1 - y0
    side = int(H * 1.12)
    names = ["front", "left", "back", "right"]
    for n, (x0, x1) in zip(names, merged):
        cx = (x0 + x1) // 2
        canvas = Image.new("RGB", (side, side), tuple(int(v) for v in bg))
        crop = im.crop((x0 - 10, y0, x1 + 10, y1 + 1))
        canvas.paste(crop, (side // 2 - (cx - x0 + 10), (side - H) // 2))
        canvas = canvas.resize((2048, 2048), Image.LANCZOS)
        canvas.save("%s_%s.png" % (out_prefix, n))
        print(n, x0, x1, "width", x1 - x0)
    print("height px", H)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
