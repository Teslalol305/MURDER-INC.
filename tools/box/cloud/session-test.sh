#!/bin/bash
# The game's own watch on its launcher (release 3c, Source/MurderInc/Cloud/MISession.h), shown with a stand-in launcher: a
# plain process whose id the game is given as -MILauncherPid=<pid>. The game is started directly (not through
# MurderInc.sh: the launcher's own watchdog would end it after 3 s and hide what the game does by itself).
#
#   session-test.sh launcher [<build dir>]    five runs, one game at a time, about 4 minutes; as root on the box
#       gone        the stand-in is killed (SIGKILL, nobody collects it: a zombie): the game must log it and quit,
#                   exit code 0, 5 to 7 s later
#       alive       the stand-in lives for 40 s: the game keeps running (and is then stopped by the script)
#       none        no -MILauncherPid (a game a test script starts): the script kills a bystander, nothing happens
#       unknown     an id that no process has (the launcher is in another process namespace): the game says it does not
#                   watch it, and keeps running
#       keepalive   -MIKeepAlive and a killed stand-in: the game keeps running
#   Each run keeps its files in /project/ue/cloud/lag-3c/session-<name>/ (game.log, result.txt); the last lines say
#   SESSION-TEST OK or FAILED.
# <build dir>: a folder with MurderInc/Binaries/Linux/MurderInc (the Development game; default /tmp/3c/app).
C=/project/ue/cloud
OUT=${SESSION_OUT:-$C/lag-3c}
B=${2:-/tmp/3c/app}
GAME=$B/MurderInc/Binaries/Linux/MurderInc
mkdir -p "$OUT"

games() {  # MURDER INC. game processes on the box
  local n=0 p
  for p in $(pgrep -x MurderInc-Linux; pgrep -x MurderInc); do [ -n "$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)" ] && n=$((n + 1)); done
  echo $n
}
state() { awk '{print $3}' "/proc/$1/stat" 2>/dev/null; }

one() {  # name, wait before the event (s), the event (kill | none), the game's extra arguments (@PID@ = the stand-in's id)
  local name=$1 wait=$2 event=$3; shift 3
  local d=$OUT/session-$name; rm -rf "$d"; mkdir -p "$d"; chmod 777 "$d"
  local i; for i in $(seq 1 120); do [ "$(games)" = 0 ] && break; sleep 5; done
  # The stand-in launcher: a sleeper that is the child of a process which never collects it, as the launcher E3DS killed
  # (a killed child nobody waits for stays a zombie, state Z).
  cat > "$d/standin.py" <<EOF
import os, time
pid = os.spawnvp(os.P_NOWAIT, 'sleep', ['sleep', '900'])
open('$d/standin.pid', 'w').write(str(pid))
time.sleep(900)
EOF
  chmod 644 "$d/standin.py"
  su ue4 -c "setsid nohup python3 $d/standin.py > /dev/null 2>&1 < /dev/null &"
  for i in $(seq 1 30); do [ -s "$d/standin.pid" ] && break; sleep 0.2; done
  local stand; stand=$(cat "$d/standin.pid")
  local args=("$@") k
  for k in "${!args[@]}"; do args[$k]=${args[$k]//@PID@/$stand}; done
  echo "name=$name stand-in pid=$stand event=$event after ${wait}s args=${args[*]}" > "$d/info.txt"
  cat > "$d/run.sh" <<EOF
#!/bin/bash
cd $B/MurderInc/Binaries/Linux
start=\$(date +%s.%N)
HOME=/home/ue4 ./MurderInc MurderInc -MICloud -RenderOffScreen -stdout -FullStdOutLogOutput -log -AudioMixer -Unattended \
  -AllowPixelStreamingCommands -PixelStreamingURL=ws://127.0.0.1:8888 -PixelStreamingID=sess$name -ResX=1920 -ResY=1080 \
  -ForceRes -Windowed -MICloudProbe=1 ${args[*]} > $d/game.log 2>&1 &
echo \$! > $d/game.pid
wait \$!
rc=\$?
echo "EXIT \$rc after \$(python3 -c "import time; print(round(time.time()-\$start, 1))")s" > $d/result.txt
EOF
  chmod 755 "$d/run.sh"
  su ue4 -c "setsid nohup bash $d/run.sh > /dev/null 2>&1 < /dev/null &"
  sleep "$wait"
  local t0; t0=$(date +%s.%N)
  if [ "$event" = kill ]; then
    kill -KILL "$stand"; sleep 0.3
    echo "killed the stand-in $stand (state: $(state "$stand"))" >> "$d/info.txt"
  fi
  # The game ends by itself within 25 s of the event, or it is stopped.
  for i in $(seq 1 25); do [ -f "$d/result.txt" ] && break; sleep 1; done
  local t1; t1=$(date +%s.%N)
  local waited; waited=$(python3 -c "print(round($t1-$t0,1))")
  if [ ! -f "$d/result.txt" ]; then
    kill -TERM "$(cat "$d/game.pid" 2>/dev/null)" 2>/dev/null; for i in $(seq 1 30); do [ -f "$d/result.txt" ] && break; sleep 1; done
    echo "STILL RUNNING $waited s after the event; stopped by the script: $(cat "$d/result.txt" 2>/dev/null)" >> "$d/info.txt"
    echo running > "$d/outcome"
  else
    echo "ENDED BY ITSELF $waited s after the event: $(cat "$d/result.txt")" >> "$d/info.txt"
    echo ended > "$d/outcome"
  fi
  kill -KILL "$stand" 2>/dev/null; pkill -f "$d/standin.py" 2>/dev/null
  echo "== $name: $(tail -1 "$d/info.txt")"
  grep -a "Launcher:\|Session over\|Session:" "$d/game.log" | cut -c1-260 | sed 's/^/     /'
}

verdict() {  # name, expected outcome (ended|running), what the run is about
  local d=$OUT/session-$1 got; got=$(cat "$d/outcome" 2>/dev/null)
  if [ "$got" = "$2" ]; then echo "ok      $3"; else echo "FAILED  $3 (expected the game to be $2, it was ${got:-not run})"; FAILS=$((FAILS + 1)); fi
}

[ "$(id -u)" = 0 ] || { echo "run as root"; exit 1; }
case "$1" in
  launcher)
    FAILS=0
    one gone 15 kill -MILauncherPid=@PID@
    one alive 15 none -MILauncherPid=@PID@
    one none 15 kill
    one unknown 15 none -MILauncherPid=4194000
    one keepalive 15 kill -MILauncherPid=@PID@ -MIKeepAlive
    verdict gone ended "a killed launcher: the game quits by itself"
    grep -q "EXIT 0" "$OUT/session-gone/result.txt" && echo "ok      ... with exit code 0" || { echo "FAILED  ... with exit code 0"; FAILS=$((FAILS + 1)); }
    verdict alive running "a launcher that lives: the game stays"
    verdict none running "no -MILauncherPid: nothing is watched, the game stays"
    verdict unknown running "an id nobody has: not watched, the game stays"
    grep -aq "is not there at the start of the game: it is not watched" "$OUT/session-unknown/game.log" && echo "ok      ... and it says so" || { echo "FAILED  ... and it says so"; FAILS=$((FAILS + 1)); }
    verdict keepalive running "-MIKeepAlive: a killed launcher does not end the game"
    if [ "$FAILS" = 0 ]; then echo "SESSION-TEST OK"; else echo "SESSION-TEST FAILED ($FAILS)"; exit 1; fi ;;
  *) sed -n 2,19p "$0"; exit 2 ;;
esac
