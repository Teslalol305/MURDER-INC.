"""A contact sheet of pictures, for looking at many at once (and for sending many back as one file).

  python3 sheet.py out.jpg [--cols 3] [--cell 800] [--quality 80] picture1.jpg picture2.jpg ...

Each picture is shrunk to a cell (the longest side `cell` pixels) with its file name under it. The result is a JPEG.
Nothing is added to the pictures themselves: the sheet is for the eye, the single pictures stay the evidence.
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("pictures", nargs="+")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--cell", type=int, default=800)
    ap.add_argument("--quality", type=int, default=80)
    a = ap.parse_args()
    try:
        font = ImageFont.load_default(size=18)
    except TypeError:
        font = ImageFont.load_default()
    cells = []
    for p in a.pictures:
        im = Image.open(p).convert("RGB")
        im.thumbnail((a.cell, a.cell))
        cells.append((os.path.basename(p), im))
    cw = a.cell
    ch = max(im.size[1] for _, im in cells) + 26
    rows = (len(cells) + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (a.cols * cw, rows * ch), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(cells):
        x, y = (i % a.cols) * cw, (i // a.cols) * ch
        sheet.paste(im, (x, y))
        draw.text((x + 4, y + im.size[1] + 3), name, fill=(235, 235, 235), font=font)
    sheet.save(a.out, "JPEG", quality=a.quality)
    print("SHEET %s %dx%d %d pictures" % (a.out, sheet.size[0], sheet.size[1], len(cells)))


if __name__ == "__main__":
    main()
