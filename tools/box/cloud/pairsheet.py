#!/usr/bin/env python3
"""Contact sheet of before/after pairs, for LOOKING at what a setting costs in looks (release 3c, the quality ladder).

  pairsheet.py <out.jpg> <dir> <label|base.jpg|variant.jpg> ... [--rows 4] [--cell 640] [--crop x0,y0,x1,y1]

One row per pair: the frame as received with the setting at its usual value, the frame with the setting changed, and the difference
(absolute, multiplied by 6, so that a change of a few levels shows). The frames are the viewer's saved video frames (the same
scene, the same pose, a few seconds apart: the Goons and the traffic move, so differences in those places are not the setting's).
--crop looks at part of the frame at full resolution first (coordinates of the 1920 x 1080 frame).
"""
import os
import sys

from PIL import Image, ImageChops, ImageDraw


def main(a):
    rows, cell, crop = 4, 640, None
    args = []
    i = 0
    while i < len(a):
        if a[i] == '--rows':
            rows = int(a[i + 1]); i += 2
        elif a[i] == '--cell':
            cell = int(a[i + 1]); i += 2
        elif a[i] == '--crop':
            crop = tuple(int(x) for x in a[i + 1].split(',')); i += 2
        else:
            args.append(a[i]); i += 1
    out, d, pairs = args[0], args[1], args[2:]
    sheets = [pairs[k:k + rows] for k in range(0, len(pairs), rows)]
    for n, group in enumerate(sheets):
        h = None
        tiles = []
        for p in group:
            label, b, v = p.split('|')
            ib, iv = Image.open(os.path.join(d, b)).convert('RGB'), Image.open(os.path.join(d, v)).convert('RGB')
            if crop:
                ib, iv = ib.crop(crop), iv.crop(crop)
            diff = ImageChops.difference(ib, iv).point(lambda x: min(255, x * 6))
            w = cell
            h = int(ib.height * w / ib.width)
            row = Image.new('RGB', (w * 3, h + 18), (20, 20, 20))
            for j, im in enumerate((ib, iv, diff)):
                row.paste(im.resize((w, h)), (j * w, 18))
            ImageDraw.Draw(row).text((6, 3), '%s   [base | changed | difference x6]   %s  %s' % (label, b, v), fill=(255, 255, 0))
            tiles.append(row)
        sheet = Image.new('RGB', (tiles[0].width, sum(t.height for t in tiles)))
        y = 0
        for t in tiles:
            sheet.paste(t, (0, y)); y += t.height
        name = out if len(sheets) == 1 else out.replace('.jpg', '-%d.jpg' % (n + 1))
        sheet.save(name, quality=82)
        print(name)


if __name__ == '__main__':
    main(sys.argv[1:])
