#!/bin/bash
# The offline first-person reconstruction, end to end (HANDS_R4.md 12). One heavy job at a time: every step below
# runs Blender as a Python module on the CPU (4 threads); about 10 minutes in all on 4 CPUs.
#   bash tools/box/fp/offline/run-all.sh [OUT]      (OUT defaults to art/out/fp-offline, git-ignored)
# Needs: the venv with bpy (art/blender/README.md; /home/user/mi-venv here), art/out/glb and art/out/textures.
set -euo pipefail
cd "$(dirname "$0")/../../../.."
PY=${MI_BPY:-/home/user/mi-venv/bin/python}
OUT=${1:-art/out/fp-offline}
SHOTS=docs/unreal/shots
O=tools/box/fp/offline
mkdir -p "$OUT"
q() { grep -v "INFO\|^Info\|Fra:\|Saved:" || true; }
# 1. the clip model's fit to the game's development log, and the firing arm's reach from the log alone
$PY $O/calibrate.py 2>&1 | q | tee "$OUT/calibrate.txt"
$PY $O/calibrate.py --reach 2>&1 | q | tee "$OUT/reach.txt"
$PY $O/calibrate.py --scan 2>&1 | q | tee "$OUT/scan.txt"
# 2. every gun, hip / aimed / reload 0.5 s / 1.1 s, from the eye, the right and above left, with the ID renders
$PY $O/fp_offline.py --out "$OUT" --threads 4 2>&1 | grep FRAME | cut -c1-160
# 3. what-ifs (data changed in the run only): the shoulders anchor both arms reach from; the SHORTY's eye relief;
#    every gun texture read as 0, under a street HDRI
$PY $O/fp_offline.py --guns chopper,stretch,rattler --shoulders=2,0,-16 --tag=-sh2 --cams eye,side --out "$OUT" --threads 4 2>&1 | grep FRAME | cut -c1-120
$PY $O/fp_offline.py --guns shorty --states aim --relief 0.12 --tag=-relief12 --cams eye,side --out "$OUT" --threads 4 2>&1 | grep FRAME | cut -c1-120
for f in textured zero; do
  $PY $O/fp_offline.py --guns shorty,stretch --states aim,r1.1 --cams eye --no-id --finish $f --hdri art/out/hdri/canary_wharf_2k.hdr --tag=-fin-$f --out "$OUT" --threads 4 2>&1 | grep FRAME | cut -c1-120
done
# 4. the sheets in the docs
python3 $O/sheets.py "$OUT" $SHOTS
python3 $O/figures.py "$OUT" $SHOTS
# 5. HANDS_R4.md 13, before and after the fix: the data of 12 (commit f861e43, unpacked into OUT-before/data) against
#    this tree's data; the tuning that chose the fix (tune.py; numbers only, no renders)
BEFORE=$OUT-before
mkdir -p "$BEFORE/data"
for f in presentation.json guns.json grips.json config.json; do git show f861e43:unreal/MurderInc/Content/Data/$f > "$BEFORE/data/$f"; done
MI_FP_DATA=$PWD/$BEFORE/data $PY $O/fp_offline.py --out "$BEFORE" --threads 4 --cams eye,side,grip 2>&1 | grep FRAME | cut -c1-120
$PY $O/fp_offline.py --out "$OUT-fix" --threads 4 --cams eye,side,left,grip 2>&1 | grep FRAME | cut -c1-120
$PY $O/tune.py report chopper,stretch,rattler,shorty,nine 2>&1 | grep REPORT | tee "$OUT-fix/tune-report.txt"
$PY $O/tune.py robust chopper,stretch,rattler 2>&1 | grep ROBUST | tee "$OUT-fix/tune-robust.txt"
python3 $O/fixsheets.py "$BEFORE" "$OUT-fix" $SHOTS
