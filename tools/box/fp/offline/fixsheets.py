"""Before / after sheets of HANDS_R4.md 13 (docs/unreal/shots/hands-offline-fix-*.jpg, each under 300 KB).

    python3 tools/box/fp/offline/fixsheets.py BEFORE_DIR AFTER_DIR DEST_DIR [--guns ...] [--cell 300]

BEFORE_DIR: fp_offline.py's output on the data before the fix (HANDS_R4.md 12's run, art/out/fp-offline); AFTER_DIR: the
same run on this commit's data (art/out/fp-offline-fix). One sheet per gun: a row per state (hip, aimed, reload 0.5 s,
1.1 s); columns: before from the eye, after from the eye, before from the right, after from the right, after from above
left. Each cell is labelled; the report's numbers (firing-hand gap, magazine in sight) are written under the label.
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheets import LABEL, font, save_small  # noqa: E402

COLS = (("before", "eye", "BEFORE, eye"), ("after", "eye", "AFTER, eye"), ("before", "side", "BEFORE, right"),
        ("after", "side", "AFTER, right"), ("after", "left", "AFTER, above left"))


def note(rep, key):
    e = rep.get(key)
    if not e:
        return ""
    s = "firing hand %.1f cm off" % e["r"]["wrist_gap_cm"]
    v = (e.get("id") or {}).get("mag_visible_frac")
    if v is not None:
        s += ", magazine %d %% in sight" % round(v * 100)
    return s


def sheet(before, after, gun, states, cell):
    w, h = cell, cell * 9 // 16
    strip = 34
    reps = {k: (json.load(open(os.path.join(d, "report.json"))) if os.path.exists(os.path.join(d, "report.json")) else {})
            for k, d in (("before", before), ("after", after))}
    im = Image.new("RGB", (w * len(COLS), (h + strip) * len(states)), (18, 18, 18))
    d = ImageDraw.Draw(im)
    f, f2 = font(13), font(12)
    for r, st in enumerate(states):
        for c, (which, cam, title) in enumerate(COLS):
            src = before if which == "before" else after
            p = os.path.join(src, "%s-%s-%s.jpg" % (gun, st.replace(".", ""), cam))
            x, y = c * w, r * (h + strip)
            if os.path.exists(p):
                im.paste(Image.open(p).convert("RGB").resize((w, h)), (x, y + strip))
            col = (255, 170, 150) if which == "before" else (160, 255, 170)
            d.text((x + 5, y + 2), "%s %s, %s" % (gun.upper(), LABEL.get(st, st), title), fill=col, font=f)
            if cam == "eye":
                d.text((x + 5, y + 18), note(reps[which], "%s-%s" % (gun, st)), fill=(220, 220, 220), font=f2)
    return im


def grip_sheet(before, after, guns, cell):
    """The firing hand from the gun's left, level with the pistol grip: before and after, at the hip and at reload 0.5 s."""
    w, h = cell, cell * 9 // 16
    strip = 20
    cols = (("before", "hip"), ("after", "hip"), ("before", "r05"), ("after", "r05"))
    im = Image.new("RGB", (w * len(cols), (h + strip) * len(guns)), (18, 18, 18))
    d = ImageDraw.Draw(im)
    f = font(13)
    for r, g in enumerate(guns):
        for c, (which, st) in enumerate(cols):
            p = os.path.join(before if which == "before" else after, "%s-%s-grip.jpg" % (g, st))
            x, y = c * w, r * (h + strip)
            if os.path.exists(p):
                im.paste(Image.open(p).convert("RGB").resize((w, h)), (x, y + strip))
            d.text((x + 5, y + 2), "%s %s, %s: firing hand from the gun's left" % (g.upper(), "hip" if st == "hip" else "reload 0.5 s",
                                                                                  which.upper()),
                   fill=(255, 170, 150) if which == "before" else (160, 255, 170), font=f)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("dest")
    ap.add_argument("--guns", default="chopper,shorty,stretch,rattler,nine")
    ap.add_argument("--states", default="hip,aim,r0.5,r1.1")
    ap.add_argument("--cell", type=int, default=300)
    a = ap.parse_args()
    for g in a.guns.split(","):
        im = sheet(a.before, a.after, g, a.states.split(","), a.cell)
        path = os.path.join(a.dest, "hands-offline-fix-%s.jpg" % g)
        n, q = save_small(im, path)
        print("SHEET %s %dx%d %d KB (quality %d)" % (path, im.size[0], im.size[1], n // 1024, q))
    im = grip_sheet(a.before, a.after, a.guns.split(","), a.cell)
    path = os.path.join(a.dest, "hands-offline-fix-grip.jpg")
    n, q = save_small(im, path)
    print("SHEET %s %dx%d %d KB (quality %d)" % (path, im.size[0], im.size[1], n // 1024, q))


if __name__ == "__main__":
    main()
