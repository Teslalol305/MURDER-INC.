#!/bin/bash
# Capture a picture of the level that is open in the running headless editor and save it as a JPEG.
# Usage: shot.sh <out.jpg> [cam=X,Y,Z,pitch,yaw,roll] [fov=90] [size=1920x1080] [frames=24] [mode=Lit]
#                          [view=auto|editor|game] [wait=seconds] [exec="console command"]...
#   cam    camera in Unreal units (centimetres, degrees); without it: the editor viewport's camera, or the
#          player's view when play-in-editor is running
#   frames with cam: render the view for this many editor ticks and keep the last frame, so that Lumen, the sky
#          light and temporal anti-aliasing have settled (Content/Python/mi_shot.py; editor world only: while
#          play-in-editor runs the MCP capture is used). frames=0: one frame through
#          the MCP capture tool, without temporal history (black shadows), which also takes mode= (see ListModes)
#   wait   seconds to wait before capturing (use it after loading a level: Lumen and shaders need a few seconds)
# Prints: SHOT OK|BLACK <file> <width>x<height> <bytes> bytes mean=<0-255> near-black=<percent>. Exit code 4 = black.
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
  mi_become_ue4 "$@"
  local out=$1; shift
  [ -n "$out" ] || mi_die "usage: shot.sh <out.jpg> [cam=X,Y,Z,pitch,yaw,roll] [fov=90] [size=1920x1080] [mode=Lit] [wait=s] [exec=cmd]"
  [ -n "$(mi_editor_pid)" ] || mi_die "SHOT FAILED: the editor is not running (editor.sh start)"
  local png; png=$(mktemp /tmp/mi-shot-XXXXXX.png)
  local line rc
  line=$(mi_mcp shot "$png" "$@"); rc=$?
  if [ $rc -ne 0 ] && [ $rc -ne 4 ]; then rm -f "$png"; echo "SHOT FAILED: $line"; return 1; fi
  mkdir -p "$(dirname "$out")"
  "$(mi_python)" - "$png" "$out" <<'PY' || { echo "SHOT FAILED: cannot write the JPEG (Pillow missing? pip install pillow): $line"; rm -f "$png"; return 1; }
import os, sys
from PIL import Image, ImageStat
image = Image.open(sys.argv[1]).convert("RGB")
image.thumbnail((1920, 1080))
image.save(sys.argv[2], "JPEG", quality=88)
grey = image.convert("L")
histogram = grey.histogram()
mean = ImageStat.Stat(grey).mean[0]
dark = sum(histogram[:8]) / max(sum(histogram), 1)
verdict = "BLACK" if mean < 2.0 or dark > 0.995 else "OK"
print("SHOT %s %s %dx%d %d bytes mean=%.1f/255 near-black=%.1f%%" % (
    verdict, sys.argv[2], image.size[0], image.size[1], os.path.getsize(sys.argv[2]), mean, dark * 100.0))
sys.exit(0 if verdict == "OK" else 4)
PY
  rc=$?
  rm -f "$png"
  return $rc
}
main "$@"; exit $?
