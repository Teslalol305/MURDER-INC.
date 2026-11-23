#!/bin/bash
PY=/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python
S=art/blender/review/vehicles_review_r5.py
cd /home/user/MURDER-INC. || exit 1
waitmem() { while [ "$(free -g | awk '/Mem:/{print $7}')" -lt 4 ]; do sleep 20; done; }
run() { waitmem; echo "== $*"; "$PY" "$S" "$@" 2>&1 | grep -E "VIEW|SHEET|CLOSE|Error|Traceback|^\{" | cut -c1-400; }
run --compose Van_Vulture
for t in door interior; do run --close SUV $t; done
for v in Pickup Van BoxTruck IPXTruck BurnedCar StrippedCar; do for t in wheel lamp door interior; do run --close $v $t; done; done
for t in wheel lamp; do run --close Motorbike $t; done
echo DONE
