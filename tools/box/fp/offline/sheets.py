"""Contact sheets of fp_offline.py's renders for the docs (docs/unreal/shots/hands-offline-*.jpg, each under 300 KB).

    python3 tools/box/fp/offline/sheets.py OUT_DIR DEST_DIR [--guns chopper,shorty,stretch,rattler,nine]
        [--states hip,aim,r0.5,r1.1] [--cams eye,side,left] [--cell 400] [--suffix ""] [--name hands-offline-%s.jpg]

One sheet per gun: a row per state, a column per camera, each cell labelled (gun, state, camera) in a black strip.
JPEG quality is lowered until the sheet is under 300 KB.
"""
import argparse
import io
import os

from PIL import Image, ImageDraw, ImageFont

LABEL = {"hip": "hip", "aim": "aimed (irons)", "r0.5": "reload 0.5 s", "r1.1": "reload 1.1 s"}
CAM = {"eye": "from the eye", "side": "from the right", "left": "from above left", "id": "ID: gun blue, magazine red, support green, firing yellow"}


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def save_small(im, path, limit=300 * 1024):
    for q in (85, 80, 75, 70, 65, 60, 55, 50):
        b = io.BytesIO()
        im.save(b, "JPEG", quality=q)
        if b.tell() < limit:
            break
    open(path, "wb").write(b.getvalue())
    return b.tell(), q


def sheet(out_dir, gun, states, cams, cell, suffix=""):
    w, h = cell, cell * 9 // 16
    strip = 22
    im = Image.new("RGB", (w * len(cams), (h + strip) * len(states)), (18, 18, 18))
    d = ImageDraw.Draw(im)
    f = font(14)
    for r, st in enumerate(states):
        for c, cam in enumerate(cams):
            name = "%s-%s%s-%s.%s" % (gun, st.replace(".", ""), suffix, cam, "png" if cam == "id" else "jpg")
            p = os.path.join(out_dir, name)
            x, y = c * w, r * (h + strip)
            if os.path.exists(p):
                im.paste(Image.open(p).convert("RGB").resize((w, h)), (x, y + strip))
            d.text((x + 5, y + 3), "%s %s, %s" % (gun.upper(), LABEL.get(st, st), CAM.get(cam, cam)), fill=(235, 235, 235), font=f)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("dest")
    ap.add_argument("--guns", default="chopper,shorty,stretch,rattler,nine")
    ap.add_argument("--states", default="hip,aim,r0.5,r1.1")
    ap.add_argument("--cams", default="eye,side,left")
    ap.add_argument("--cell", type=int, default=400)
    ap.add_argument("--suffix", default="")
    ap.add_argument("--name", default="hands-offline-%s.jpg")
    a = ap.parse_args()
    for g in a.guns.split(","):
        im = sheet(a.out_dir, g, a.states.split(","), a.cams.split(","), a.cell, a.suffix)
        path = os.path.join(a.dest, a.name % g)
        n, q = save_small(im, path)
        print("SHEET %s %dx%d %d KB (quality %d)" % (path, im.size[0], im.size[1], n // 1024, q))


if __name__ == "__main__":
    main()
