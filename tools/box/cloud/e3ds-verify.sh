#!/bin/bash
# Re-verify a cloud package against the E3DS crash causes (docs/unreal/PROGRESS.md, "E3DS crash fix"), as root on
# the box, detached:
#
#   e3ds-verify.sh start [Shipping|<build dir>]   runs everything below (about 20 minutes); log in repro/verify.log
#   e3ds-verify.sh status                         one line per run (e3ds-repro.sh status) and the log's tail
#
# Every run goes through the zip's own launcher (MurderInc.sh) with a clean environment (e3ds-repro.sh); the launcher
# adds -RenderOffScreen and the log. The runs, two at a time:
#   v-long        7 minutes, a fresh user with no display, a signalling server and a fake viewer joining and
#                 leaving 12 times, -ForceRes 1920x1080, then TERM to the game
#   v-sm5         -sm5: the shader platform a driver failing Unreal's SM6 check gets (it used to exit 1 after 7 s)
#   v-root        started as root (Unreal refuses root): the launcher runs the game as the folder's owner; TERM to
#                 the launcher, which passes it on
#   v-crash       the Shipping game crashed from outside after 30 s (SIGSEGV from the harness: version 3 has no
#                 -MICrashTest in Shipping, so no visitor can cause a crash email); the log must say CRASH and carry
#                 the engine's crash report
#   v-crash-dev   -MIDev -MICrashTest=30: the Development game crashes on purpose; the same, with a full call stack
#   v-nort        hardware ray tracing off (a GPU or driver without it): software Lumen; INT to the launcher
#   v-dev-quit    the Development game (-MIDev) quits by itself: exit code 0 (it used to segfault on every exit)
# then one at a time, with tools/box/cloud/vram_hog.py holding graphics memory:
#   v-vram5000    start-up with 5.0 GB of the card free (the old package segfaulted 6 s after the start)
#   v-vram6000    the Development game plays a Story run with 6.0 GB free
#   v-e3ds-7600   E3DS-style arguments with 7.6 GB free (an 8 GB card), signalling server and viewer
C=/project/ue/cloud
R=$C/repro
T=$(dirname "$(readlink -f "$0")")
LOG=$R/verify.log
B=${2:-Shipping}

one() {  # name secs [env...] -- args...
  local name=$1 secs=$2; shift 2
  local envs=()
  while [ "$1" != -- ]; do envs+=("$1"); shift; done; shift
  env "${envs[@]}" STDOUT=0 bash "$T/e3ds-repro.sh" run "$name" "$secs" "$@" >> "$LOG" 2>&1
  local i; for i in $(seq 1 $((secs + 120))); do [ -f "$R/$name/result.txt" ] && break; sleep 1; done
  echo "[$(date +%H:%M:%S)] $name: $(cat "$R/$name/result.txt" 2>/dev/null || echo 'NO RESULT')" >> "$LOG"
}

hog() {  # free MiB, or stop
  [ -f "$R/hog.pid" ] && kill "$(cat "$R/hog.pid")" 2>/dev/null && sleep 5
  rm -f "$R/hog.pid"
  [ "$1" = stop ] && return
  setsid nohup /opt/venv/bin/python3 -I "$T/vram_hog.py" "$1" > "$R/hog.log" 2>&1 < /dev/null & echo $! > "$R/hog.pid"
  local i; for i in $(seq 1 60); do grep -q held "$R/hog.log" && break; sleep 1; done
  echo "[$(date +%H:%M:%S)] hog: $(cat "$R/hog.log")" >> "$LOG"
}

run_all() {
  local cfg=(CFG=Shipping); [ -d "$B" ] && cfg=(BUILD="$B")
  echo "[$(date +%H:%M:%S)] verify start (${cfg[*]})" > "$LOG"
  bash "$T/e3ds-repro.sh" ss start >> "$LOG" 2>&1
  sleep 3
  local ps="-PixelStreamingConnectionURL=ws://127.0.0.1:8888" none="-PixelStreamingConnectionURL=ws://127.0.0.1:8899"
  # The long run with the viewer, beside the short ones one after another.
  one v-long 420 "${cfg[@]}" RUNAS=fresh NODISPLAY=1 STOPSIG=TERM VIEWER=25,10,12,40 -- \
    "$ps" -ResX=1920 -ResY=1080 -ForceRes -MICloudProbe=30 &
  one v-sm5 120 "${cfg[@]}" NODISPLAY=1 STOPSIG=TERM -- "$none" -sm5 -MICloudProbe=30
  one v-root 90 "${cfg[@]}" RUNAS=root NODISPLAY=1 STOPSIG=TERM STOPTO=launcher -- "$none"
  one v-crash 90 "${cfg[@]}" NODISPLAY=1 CRASHAT=30 -- "$none"
  one v-crash-dev 90 "${cfg[@]}" NODISPLAY=1 -- -MIDev "$none" -MICrashTest=30
  one v-nort 90 "${cfg[@]}" NODISPLAY=1 STOPSIG=INT STOPTO=launcher -- "$none" \
    "-ini:Engine:[/Script/Engine.RendererSettings]:r.RayTracing=False"
  one v-dev-quit 150 "${cfg[@]}" NODISPLAY=1 -- -MIDev "$none" "-ExecCmds=MIDemo.Run $T/e3ds-quit.txt"
  wait
  # Graphics memory, one run at a time.
  hog 5000
  one v-vram5000 120 "${cfg[@]}" NODISPLAY=1 STOPSIG=TERM -- "$none" -ResX=1920 -ResY=1080 -ForceRes -MICloudProbe=15
  hog 6000
  one v-vram6000 220 "${cfg[@]}" NODISPLAY=1 STOPSIG=TERM -- -MIDev "$none" -ResX=1920 -ResY=1080 -ForceRes \
    "-ExecCmds=MIDemo.Run $T/e3ds-play.txt" -MICloudProbe=15
  hog 7600
  one v-e3ds-7600 220 "${cfg[@]}" RUNAS=fresh NODISPLAY=1 STOPSIG=TERM VIEWER=25,10,5,40 -- -AudioMixer \
    -PixelStreamingURL=ws://127.0.0.1:8888 -PixelStreamingIP=127.0.0.1 -PixelStreamingPort=8888 \
    -AllowPixelStreamingCommands -PixelStreamingEncoderCodec=H264 -PixelStreamingHideCursor -Windowed -ForceRes \
    -ResX=1920 -ResY=1080 -MICloudProbe=20
  hog stop
  bash "$T/e3ds-repro.sh" ss stop >> "$LOG" 2>&1
  echo "[$(date +%H:%M:%S)] verify done" >> "$LOG"
}

[ "$(id -u)" = 0 ] || { echo "run as root"; exit 1; }
case "$1" in
  start) mkdir -p "$R"; setsid nohup bash "$0" run "$B" < /dev/null > /dev/null 2>&1 & echo "started: poll e3ds-verify.sh status" ;;
  run) run_all ;;
  status) bash "$T/e3ds-repro.sh" status 'v-*'; tail -3 "$LOG" ;;
  *) sed -n 2,26p "$0"; exit 2 ;;
esac
