#!/bin/bash
# Test the packaged cloud build through Epic's Pixel Streaming 2 infrastructure, entirely on the box:
# signalling and web server on 127.0.0.1 only, the game rendering off screen, a headless Chromium as the viewer.
#
#   stream-test.sh start [Development|Shipping] [extra game args...]   signalling server + game (detached)
#   stream-test.sh test <outdir> [viewport WxH] [MatchViewportRes]     the browser test (stream_test.cjs)
#   stream-test.sh run <script> [Development] [extra args]             the game alone (no stream) playing a MIDemo
#                                                                      script, for the memory runs (Development only)
#   stream-test.sh xtest <outdir> [config]                            the in-game half on a private screen, no WebRTC
#   stream-test.sh stop                                                stop what this script started (by pid)
#
# Needs setup-ps.sh (Node, the infrastructure, Chromium) and package-cloud.sh (the builds). Run as root.
C=/project/ue/cloud
RUN=$C/run
mkdir -p "$RUN" && chown ue4 "$RUN"
export PATH=$C/node/bin:$PATH PLAYWRIGHT_BROWSERS_PATH=$C/pw/browsers
TOOLS=$(dirname "$(readlink -f "$0")")

gpu_sampler() {  # the GPU's own counters, once a second, until the game ends
  local pid=$1
  ( while kill -0 "$pid" 2>/dev/null; do
      echo "$(date +%s.%N | cut -c1-14),$(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits)"
      sleep 1
    done ) > "$RUN/gpu.csv" 2>/dev/null &
  echo $! > "$RUN/sampler.pid"
}

listening() {  # the listening sockets of ports 8090 and 8888, from /proc (no ss or netstat on the box)
  python3 - <<'PY'
import socket, struct
for f in ('/proc/net/tcp', '/proc/net/tcp6'):
    for line in open(f).readlines()[1:]:
        p = line.split(); addr, port = p[1].split(':'); port = int(port, 16)
        if p[3] == '0A' and port in (8090, 8888):
            ip = socket.inet_ntop(socket.AF_INET, struct.pack('<I', int(addr, 16))) if len(addr) == 8 else addr
            print('LISTEN', ip, port)
PY
}

start_game() {  # $1 config, rest: args
  local cfg=${1:-Shipping}; shift
  local L=$C/build-$cfg/Linux
  [ -x "$L/MurderInc.sh" ] || { echo "no build in $L"; exit 1; }
  echo "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)" > "$RUN/gpu-baseline.txt"
  date +%s.%N | cut -c1-14 > "$RUN/launch.txt"
  rm -f "$RUN/cloud.log"
  su ue4 -c "cd $L && HOME=/home/ue4 setsid nohup ./MurderInc.sh -RenderOffScreen -vulkan -unattended -nosplash -ResX=1920 -ResY=1080 -ForceRes \
    -stdout -FullStdOutLogOutput -MICloudLog=$RUN/cloud.log $(printf '%q ' "$@") </dev/null > $RUN/game.log 2>&1 & echo \$! > $RUN/game.pid"
  sleep 2
  gpu_sampler "$(cat "$RUN/game.pid")"
  echo "GAME $cfg started pid $(cat "$RUN/game.pid") (log $RUN/game.log)"
}

case "$1" in
  start)
    shift
    if ! kill -0 "$(cat "$RUN/ss.pid" 2>/dev/null)" 2>/dev/null; then
      (cd "$C/infra/SignallingWebServer" && setsid nohup node --require "$TOOLS/localhost.cjs" dist/index.js --no_config \
        --serve --http_root www --homepage player.html --player_port 8090 --streamer_port 8888 --streamer_host 127.0.0.1 \
        --log_folder "$RUN/sslogs" --console_messages verbose </dev/null > "$RUN/ss.log" 2>&1 & echo $! > "$RUN/ss.pid")
      sleep 3
    fi
    listening
    cfg=${1:-Shipping}; shift
    start_game "$cfg" -PixelStreamingConnectionURL=ws://127.0.0.1:8888 "$@"
    ;;
  run)
    scr=$2; cfg=${3:-Development}; shift 3
    sed -e '/^capture /d' -e '/MIAudio.Record/d' -e "s#@OUT@#$RUN/shot.png#" "$scr" > "$RUN/script.txt"; chown ue4 "$RUN/script.txt"
    start_game "$cfg" "-ExecCmds=MIDemo.Run $RUN/script.txt" "$@"
    ;;
  test)
    out=$2; vp=${3:-1920x1080}; mkdir -p "$out"
    VW=${vp%x*} VH=${vp#*x} MATCH=${4:-false} node "$TOOLS/stream_test.cjs" "$out" "$RUN/cloud.log" "$RUN/launch.txt"
    ;;
  xtest)  # the in-game half without WebRTC: a window on Xvfb :99, XTEST input (xtest.py)
    /opt/venv/bin/python3 -I "$TOOLS/xtest.py" "$2" "${3:-Development}"
    ;;
  stop)
    for f in game ss sampler; do p=$(cat "$RUN/$f.pid" 2>/dev/null); [ -n "$p" ] && kill "$p" 2>/dev/null && echo "stopped $f $p"; done
    # setsid can fork: stop the signalling server by its command line too (our preload names it).
    for p in $(pgrep -x node); do
      tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q 'cloud/localhost.cjs' && kill "$p" && echo "stopped signalling $p"
    done
    # The game runs under its launcher script: stop the binary it started (only the one in our builds).
    for p in $(pgrep -x MurderInc-Linux; pgrep -x MurderInc); do
      tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q "cloud/build-" && kill "$p" && echo "stopped game binary $p"
    done
    ;;
  *) sed -n 2,12p "$0"; exit 2 ;;
esac
