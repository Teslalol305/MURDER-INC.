#!/bin/bash
# Round-4 vehicle review: one Blender process per render, sequential, waits for >= 4 GB free before each.
PY=${PY:-/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python}
S=art/blender/review/vehicles_review_r4.py
cd "$(dirname "$0")/../../.." || exit 1
waitmem() { while [ "$(free -g | awk '/Mem:/{print $7}')" -lt 4 ]; do sleep 20; done; }
run() { waitmem; echo "== $*"; "$PY" "$S" "$@" 2>&1 | grep -E "VIEW|SHEET|CLOSE|Error|Traceback|^\{" | cut -c1-400; }
ALL="Sedan Taxi SUV Pickup Van Van_Vulture BoxTruck IPXTruck Motorbike BurnedCar StrippedCar"
STEP=${1:-all}
if [ "$STEP" = measure ] || [ "$STEP" = all ]; then for v in $ALL; do run --measure $v; done; fi
if [ "$STEP" = sheets ] || [ "$STEP" = all ]; then
  for v in $ALL; do for i in 0 1 2 3; do run --view $v $i; done; run --compose $v; done; fi
if [ "$STEP" = close ] || [ "$STEP" = all ]; then
  for v in Sedan SUV Pickup Van BoxTruck IPXTruck BurnedCar StrippedCar; do
    for t in wheel lamp door interior; do run --close $v $t; done; done
  run --close Motorbike wheel; run --close Motorbike lamp
fi
echo DONE
