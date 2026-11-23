#!/bin/bash
# The demo capture (docs/unreal/PROGRESS.md, "Demo video"): the game runs standalone (-game, offscreen) on a fixed
# 1/60 s frame (-benchmark -fps=60 -deterministic) and plays a demo script with the MIDemo director
# (Source/MurderInc/Flow/MIDemoDirector): the set-up screens by their console twins, then a Story run through the
# player's eyes with scripted input. Every frame of the game viewport (Slate screens, HUD, world) goes as raw BGRA
# through a FIFO to ffmpeg; the event bus is recorded (MIAudio.Record) for the sound (audio.sh).
# Usage (on the box): capture.sh start [script] [name] | status | stop
#   script  default tools/box/demo/demo.txt; the line `capture @FIFO@` starts the frames
#   name    output name (default demo): <logs>/demo/<name>.mp4, <name>.json (the bus), <name>-game.log
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"
  mi_become_ue4 "$@"
  local dir=$MI_LOGS/demo
  mkdir -p "$dir"
  case "$1" in
    --run) shift; run "$@"; exit $? ;;
    start)
      shift
      command -v ffmpeg > /dev/null || mi_die "CAPTURE FAILED: no ffmpeg (as root: apt-get install -y ffmpeg)"
      if [ -f "$dir/capture.pid" ] && kill -0 "$(cat "$dir/capture.pid")" 2>/dev/null; then mi_die "CAPTURE already running"; fi
      setsid nohup bash "$0" --run "$@" > "$dir/capture.out" 2>&1 &
      echo "CAPTURE started: poll capture.sh status" ;;
    status)
      local n=$(cat "$dir/capture.name" 2>/dev/null)
      echo "state: $(cat "$dir/capture.state" 2>/dev/null)  name: $n  since $(( $(date +%s) - $(cat "$dir/capture.start" 2>/dev/null || date +%s) )) s"
      grep -aE "MIDemo: (frame [0-9]+ t [0-9.]+: (line|captured|script|capture|fight|blow|grab|walk|event (killed|objective|game:state|extraction|explosion|reload [a-z]+ start|switch))|capture size|capture closed)|Fatal|Assertion failed" "$dir/$n-game.log" 2>/dev/null | tail -${2:-12} | cut -c1-220
      tail -2 "$dir/$n-ffmpeg.log" 2>/dev/null ;;
    stop)
      local p; for p in $(mi_pids_of UnrealEditor); do kill "$p" 2>/dev/null; done; for p in $(pgrep -x ffmpeg); do tr '\0' ' ' < /proc/$p/cmdline | grep -q mi-demo- && kill "$p"; done; echo stopped ;;
    *) echo "usage: capture.sh start [script] [name] | status | stop" ;;
  esac
}

run() {
  local dir=$MI_LOGS/demo script=${1:-$MI_BOX_DIR/demo/demo.txt} name=${2:-demo}
  echo $$ > "$dir/capture.pid"; echo "$name" > "$dir/capture.name"; date +%s > "$dir/capture.start"; echo RUNNING > "$dir/capture.state"
  local fifo=/tmp/mi-demo-$name.fifo scr=/tmp/mi-demo-$name.txt
  rm -f "$fifo"; mkfifo "$fifo"
  sed -e "s|@FIFO@|$fifo|g" -e "s|@NAME@|$name|g" "$script" > "$scr"
  # The encoder waits on the FIFO until the game opens it (the script's capture line).
  ffmpeg -y -loglevel warning -f rawvideo -pix_fmt bgra -video_size 1920x1080 -framerate 60 -i "$fifo" \
    -c:v libx264 -preset fast -crf 12 -pix_fmt yuv420p "$dir/$name.mp4" > "$dir/$name-ffmpeg.log" 2>&1 &
  local enc=$!
  mi_engine_env
  rm -f "$MI_PROJECT_DIR/Saved/Audio/$name.json"
  cd "$MI_ENGINE" || exit 1
  # -RenderOffscreen: windows abort on this box (BOX.md 1). -NoSound: the sound is rendered from the recorded bus.
  timeout 3600 env "UE-LocalDataCachePath=$MI_DDC" ./Engine/Binaries/Linux/UnrealEditor "$MI_UPROJECT" /Game/Maps/L_Block -game \
    -RenderOffscreen -unattended -nosplash -NoSound -nopause -windowed -ResX=1920 -ResY=1080 -benchmark -fps=60 -deterministic \
    -stdout -FullStdOutLogOutput "-ExecCmds=MIDemo.Run $scr" "${MI_CACHE_ARGS[@]}" "${MI_EDITOR_ARGS[@]}" > "$dir/$name-game.log" 2>&1
  echo "game exit code $?" >> "$dir/$name-game.log"
  # A game that never opened the FIFO leaves the encoder waiting: open it once so it ends.
  if kill -0 "$enc" 2>/dev/null; then (exec 3>"$fifo"; sleep 1) & fi
  wait "$enc"
  rm -f "$fifo"
  cp -f "$MI_PROJECT_DIR/Saved/Audio/$name.json" "$dir/$name.json" 2>/dev/null
  if [ -s "$dir/$name.mp4" ]; then echo DONE > "$dir/capture.state"; else echo FAILED > "$dir/capture.state"; fi
}
main "$@"
