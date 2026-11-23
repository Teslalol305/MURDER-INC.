"""Review round 5 of the exported vehicle GLBs: the round-4 loader, rig, cameras and measuring
(vehicles_review_r4.py, on r3 and vehicles_review.py), outputs redirected to sheets/vehicles_r5/.
Change from round 4: the car glass is reviewed at the opacity the fix pass reports building (0.55).

    python art/blender/review/vehicles_review_r5.py --measure Sedan
    python art/blender/review/vehicles_review_r5.py --view Sedan 0
    python art/blender/review/vehicles_review_r5.py --compose Sedan
    python art/blender/review/vehicles_review_r5.py --close Sedan wheel      # wheel | lamp | door | interior
    python art/blender/review/vehicles_review_r5.py --close Sedan custom --cam x,y,z --target x,y,z --lens 35

One render per process (memory). run_vehicles_r5.sh drives the whole round sequentially.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import vehicles_review_r4 as R4  # noqa: E402

R3 = R4.R3
R3.OUT = os.path.join(HERE, "sheets", "vehicles_r5")
R3.TMP = os.path.join(R3.OUT, "_tmp")
R3.MEAS = os.path.join(R3.OUT, "measure.json")
R4.GLASS_OPACITY["MI_Glass_CarTint"] = 0.55

if __name__ == "__main__":
    R3.main()
