#!/bin/bash
# Start the MURDER INC. demo on the box's desktop (the browser desktop the owner opens with "Open desktop").
# One command, run on the box as root (through gpu_rental_exec) or by double-clicking the desktop icon:
#
#   bash /project/ue/demo/tools/start.sh
#
# It starts the packaged game (package.sh) full screen at the desktop's current size, drawn on the GPU through the
# desktop's Vulkan bridge (primus_vk, the same set-up as `deskctl run --vulkan`), straight into the home screen.
# It also puts a "MURDER INC." icon on the desktop that runs this script again, so the owner can restart the game
# from the browser. Prints DEMO-STARTED <pid> or why it could not. Stop with stop.sh.
#
# Nothing here opens a port: the only way in is the box's own desktop link.

WORK=/project/ue/demo
GAME=$WORK/build/Linux
BIN=$GAME/MurderInc/Binaries/Linux/MurderInc
PIDF=$WORK/game.pid
LOG=$WORK/game.log
export DISPLAY=:1

if [ "$(id -un)" != ue4 ]; then
  # Root part: the desktop icon, then the game as user ue4 (the engine refuses root).
  [ -x "$BIN" ] || { echo "NO-BUILD: $BIN is missing (run package.sh snapshot, package.sh start)"; exit 1; }
  old=$(cat "$PIDF" 2>/dev/null)
  if [ -n "$old" ] && kill -0 "$old" 2>/dev/null && tr '\0' ' ' < "/proc/$old/cmdline" | grep -q "$GAME"; then
    echo "DEMO-ALREADY-RUNNING $old (stop.sh first to restart it)"; exit 0
  fi
  for d in /root/Desktop; do
    mkdir -p "$d"
    cat > "$d/murder-inc.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=MURDER INC.
Comment=Start the game (restarts it if it is already running)
Exec=bash -c 'bash $WORK/tools/stop.sh; bash $WORK/tools/start.sh'
Icon=applications-games
Terminal=false
EOF
    chmod +x "$d/murder-inc.desktop"
  done
  touch "$WORK/game.log" && chown ue4 "$WORK" "$WORK/game.log" 2>/dev/null
  exec su ue4 -c "bash $(printf '%q' "$0")"
fi

# ue4 part.
export HOME=/home/ue4 XDG_RUNTIME_DIR=/tmp/studio/xdg
# Vulkan on the NVIDIA card, shown on the virtual screen through the software device by the primus_vk layer:
# the box's own launcher `desktop-run --vulkan` (what `deskctl run --vulkan` uses) picks the two devices.
command -v desktop-run >/dev/null || { echo "NO-DESKTOP-RUN: this box has no desktop launcher (not a desktop rental?)"; exit 1; }

# The desktop's current size (the stream follows the viewer's browser window when it connects).
size=$(xdpyinfo 2>/dev/null | awk '/dimensions:/{print $2}')
W=${size%x*}; H=${size#*x}
[ -n "$W" ] && [ -n "$H" ] || { W=1920; H=1080; }

# Demo settings (docs/DEMO.md): full screen at the desktop size, the Epic preset with TSR, frame rate capped at
# 60 so the stream stays even, sound on (the box's sound device; the browser stream carries no sound, see
# DEMO.md), no console or stats on screen.
setsid nohup desktop-run --vulkan "$BIN" -vulkan -ResX="$W" -ResY="$H" -WINDOWED \
  -ExecCmds="r.SetRes ${W}x${H}wf,t.MaxFPS 60,r.VSync 0" \
  -nosplash -stdout -FullStdOutLogOutput </dev/null >"$LOG" 2>&1 &
echo $! > "$PIDF"
sleep 1
if kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "DEMO-STARTED $(cat "$PIDF") at ${W}x${H} (log $LOG); the home screen shows in about 20 to 40 s"
else
  echo "DEMO-FAILED: the game ended at once; last log lines:"; tail -5 "$LOG"; exit 1
fi
