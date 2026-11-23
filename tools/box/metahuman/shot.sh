#!/bin/bash
# shot.sh <out.png> cam=X,Y,Z,pitch,yaw,roll [fov=] [size=] [frames=]: a picture from the MetaHuman scratch editor,
# retried while the editor answers "slow task" (shader compiles). Converts to <out>.jpg with Pillow.
o=$1; shift
for i in $(seq 1 ${MH_TRIES:-30}); do
  out=$(MI_MCP_URL=http://127.0.0.1:8006/mcp timeout 120 python3 /project/ue/metahuman/scripts/mi_mcp.py shot $o "$@" 2>&1)
  echo "$out" | grep -q "slow task" || break; sleep 15
done
echo "$out" | tail -2 | cut -c1-200
[ -f $o ] && /opt/venv/bin/python3 -c "from PIL import Image; Image.open('$o').convert('RGB').save('${o%.png}.jpg', quality=88)" && ls -la ${o%.png}.jpg
