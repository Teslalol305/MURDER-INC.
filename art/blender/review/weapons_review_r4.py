"""Independent review renders and measurements of the exported player guns (critique round 4).

Reuses the round-3 harness (weapons_review_r3.py, itself on top of weapons_review.py) unchanged: fresh scene per view,
GLBs as exported, texture sets wired from the material names, studio HDRI, first-person camera from
docs/unreal/spec/02-weapons-combat.md 2.13 (vertical FOV 54 deg, hip view 1 and the derived aim pose), fixed-point
measurements. Only the output folder differs.

    python art/blender/review/weapons_review_r4.py [--only Chopper|Nine] [--views left,...] [--samples 32]

Outputs: art/blender/review/sheets/r4/weapons_<Gun>_<view>.jpg (1280 x 720), weapons_measure.json beside them.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import weapons_review as wr  # noqa: E402
import weapons_review_r3  # noqa: E402,F401  (installs the round-3 loader and measurements)

wr.OUT = os.path.join(HERE, "sheets", "r4")

if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--samples" not in argv:
        argv += ["--samples", "32"]
    sys.argv = [sys.argv[0]] + argv
    wr.main()
