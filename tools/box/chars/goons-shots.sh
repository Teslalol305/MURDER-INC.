#!/bin/bash
# Box: the three Unreal pictures of the Goons (docs/unreal/shots/chars-goons-1..3.jpg) from the chars editor (MCP 8002,
# editor.sh start first, setup_goons done). Writes /tmp/f1.jpg .. /tmp/f3.jpg; prints SHOTS-DONE.
#   1: hoodie in jog / reload / hit / death   2: puffer, hoodie, tracksuit aiming   3: hood and mask at about 1 m
M="python3 /project/ue/chars/scripts/mi_mcp.py"; export MI_MCP_URL=http://127.0.0.1:8002/mcp
stage() { cat > /tmp/st.py <<PY
import sys, importlib
sys.path.insert(0, "/project/ue/chars/scripts")
import mi_chars
importlib.reload(mi_chars)
str(mi_chars.goon_stage($1))
PY
for i in 1 2 3 4 5 6; do out=$(timeout 60 $M py /tmp/st.py 2>&1); echo "$out" | grep -q "slow task" || break; sleep 10; done; echo "$out" | tail -1; }
shot() { for i in 1 2 3 4 5 6; do out=$(timeout 90 $M shot $1 $2 fov=$3 size=1600x900 frames=60 2>&1); echo "$out" | grep -q "SHOT OK" && break; sleep 10; done; echo "$out" | tail -1 | cut -c1-120; }
stage '[("Hoodie", "jog", 0.35, -160, 0, 0), ("Hoodie", "reload", 1.3, -55, 0, 0), ("Hoodie", "hit", 0.22, 55, 0, 0), ("Hoodie", "death", 1.05, 170, -40, 0)]'
shot /tmp/f1.png cam=0,470,115,-6,-90,0 50
stage '[("Puffer", "aim", 2.0, -95, 0, 20), ("Hoodie", "aim", 2.0, 0, -30, 0), ("Tracksuit", "aim", 2.0, 95, 0, -20)]'
shot /tmp/f2.png cam=0,380,120,-6,-90,0 52
stage '[("Hoodie", "reload", 1.3, 0, 0, 0)]'
shot /tmp/f3.png cam=35,105,170,-14,-103,0 42
/opt/venv/bin/python3 -c "
from PIL import Image
for n in ('f1','f2','f3'): Image.open('/tmp/%s.png'%n).convert('RGB').save('/tmp/%s.jpg'%n, quality=86)"
ls -la /tmp/f1.jpg /tmp/f2.jpg /tmp/f3.jpg; echo SHOTS-DONE
