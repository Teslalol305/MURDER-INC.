#!/bin/bash
# Launch the packaged cloud build the way a Pixel Streaming host (Eagle 3D Streaming) most likely does, one variant
# per call, with a time limit, and record how it ended (still running at the limit, exit code, signal, core).
# Diagnostic only (the E3DS "crashed, no crashlog" report of 2026-11-24); nothing here changes the game.
#
#   e3ds-repro.sh run <name> <secs> [game args...]   detached; result in /project/ue/cloud/repro/<name>/result.txt
#   e3ds-repro.sh status [name]                       results so far
#   e3ds-repro.sh ss start|stop                       a signalling server (Epic's infrastructure, as stream-test.sh)
#   e3ds-repro.sh stopall                             stop every game binary of the cloud builds
#
# Variant knobs, as environment variables of the `run` call:
#   CFG=Shipping|Development (default Shipping)   BUILD=<dir with MurderInc.sh> (overrides CFG)
#   RUNAS=ue4|fresh|root  (fresh: user e3dsfresh with a new empty HOME each run)
#   HOMEDIR=<path>|unset  (HOME for the game; "unset" removes it; default the user's own)
#   NODISPLAY=1           (DISPLAY, WAYLAND_DISPLAY, XAUTHORITY removed)
#   ENVS="A=b C=d"        (more variables for the launcher's environment, which is otherwise built from nothing: what a
#                          host's service environment might hold, for example SDL_AUDIODRIVER=alsa on a machine with
#                          no sound card)
#   CWD=<dir>             (working directory; default the build folder)
#   STDOUT=1              (adds -stdout -FullStdOutLogOutput, default 1)
#   WSURL=<url>           (default none: give it as an argument)
#   VIEWER=<secs on>,<secs off>,<cycles>[,delay]  (a fake viewer joins and leaves through the signalling server)
#   STOPSIG=INT|TERM|HUP  (sent to the game binary when it is still alive at <secs>; default INT), GRACE=<secs> (30)
#   STOPTO=game|launcher  (who gets STOPSIG: the game binary (default) or the launcher MurderInc.sh, which passes it on)
#   CRASHAT=<secs>        (SIGSEGV to the game binary after that long: a crash from outside, for the Shipping game,
#                          which has no -MICrashTest; the run must then report ENDED BY ITSELF with signal 11)
#   CPUS=<list>           (the launcher and the game run on these CPUs only, a taskset list such as 0-5: a server
#                          with few CPUs. Unreal counts the CPUs it may run on, and with 6 or fewer task workers its
#                          Vulkan RHI has no interrupt thread: completed GPU work is then noticed only when the RHI
#                          thread submits or somebody waits for it on the render thread)
# result.txt: "ENDED BY ITSELF: ..." is a crash or exit before the limit; "ALIVE at limit; after <sig>: ..." says how
# the shutdown went (a clean shutdown ends with EXIT 0 or the signal's 128+n code; SIGNAL 11 is a crash on the way out).
C=/project/ue/cloud
R=$C/repro
TOOLS=$(dirname "$(readlink -f "$0")")
export PATH=$C/node/bin:$PATH
mkdir -p "$R"

run() {
  local name=$1 secs=$2; shift 2
  local d=$R/$name; rm -rf "$d"; mkdir -p "$d"; chmod 777 "$d"
  local B=${BUILD:-$C/build-${CFG:-Shipping}/Linux}
  [ -x "$B/MurderInc.sh" ] || { echo "no $B/MurderInc.sh"; return 1; }
  local user=ue4 home=/home/ue4
  case "${RUNAS:-ue4}" in
    root) user=root; home=/root ;;
    fresh) id e3dsfresh >/dev/null 2>&1 || useradd -M -s /bin/bash e3dsfresh
           home=/tmp/e3dsfresh-$name; rm -rf "$home"; mkdir -p "$home"; chown e3dsfresh "$home"; user=e3dsfresh ;;
  esac
  [ -n "$HOMEDIR" ] && home=$HOMEDIR
  local cwd=${CWD:-$B}
  local args=("$@")
  [ "${STDOUT:-1}" = 1 ] && args+=(-stdout -FullStdOutLogOutput)
  {
    echo "name=$name build=$B user=$user home=$home cwd=$cwd nodisplay=${NODISPLAY:-0} secs=$secs cpus=${CPUS:-all} envs=${ENVS:-}"
    echo "args=${args[*]}"
  } > "$d/info.txt"
  # A packaged build starts its Development game only with the key of its own MIDEV.key (MurderInc.sh): the tests
  # write -MIDev, and the key is put in here (not into info.txt).
  if [ -f "$B/MIDEV.key" ]; then
    local i key; key=$(tr -d ' \t\r\n' < "$B/MIDEV.key")
    for i in "${!args[@]}"; do [ "${args[$i]}" = -MIDev ] && args[$i]="-MIDev=$key"; done
  fi
  # The runner: env built from scratch like a service manager would, then the game under timeout.
  local envs="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin LANG=C.UTF-8 USER=$user"
  [ "$home" != unset ] && envs="$envs HOME=$home"
  [ -z "$NODISPLAY" ] && [ -n "$DISPLAY" ] && envs="$envs DISPLAY=$DISPLAY"
  [ -n "$ENVS" ] && envs="$envs $ENVS"
  local pin=; [ -n "$CPUS" ] && pin="taskset -c $(printf %q "$CPUS") "
  local q; q=$(printf '%q ' "${args[@]}")
  cat > "$d/runner.sh" <<EOF
#!/bin/bash
cd $(printf %q "$cwd") || { echo "EXIT cd-failed" > $d/result.txt; exit; }
start=\$(date +%s.%N)
env -i $envs $pin$(printf %q "$B/MurderInc.sh") $q > $d/game.log 2>&1 &
sh=\$!
el() { python3 -c "print(round(\$(date +%s.%N)-\$start,1))"; }
how() { local rc=\$1; if [ \$rc -gt 128 ]; then echo "SIGNAL \$((rc-128)) (\$(kill -l \$((rc-128)) 2>/dev/null))"; else echo "EXIT \$rc"; fi; }
# Wait up to the limit; the launcher (sh) returns the game's status (128+n when a signal ended it).
for i in \$(seq 1 $secs); do
  kill -0 \$sh 2>/dev/null || break
  if [ "\$i" = "${CRASHAT:-0}" ]; then
    game=\$(pgrep -P \$sh -x MurderInc-Linux | head -1); [ -n "\$game" ] || game=\$(pgrep -P \$sh -x MurderInc | head -1)
    echo "at \$(el)s: SIGSEGV to the game \$game (CRASHAT)" > $d/crash.txt; kill -SEGV \$game
  fi
  sleep 1
done
if ! kill -0 \$sh 2>/dev/null; then wait \$sh; rc=\$?; echo "ENDED BY ITSELF: \$(how \$rc) after \$(el)s" > $d/result.txt; exit; fi
# Alive at the limit: stop it the way a host would (STOPSIG to the game binary, the launcher's child), then KILL.
# The game is the launcher's child named after the binary (the logging launcher also runs tee); setpriv execs it.
game=\$(pgrep -P \$sh -x MurderInc-Linux | head -1); [ -n "\$game" ] || game=\$(pgrep -P \$sh -x MurderInc | head -1)
[ -n "\$game" ] || game=\$(pgrep -P \$sh | head -1)
target=\$game; [ "${STOPTO:-game}" = launcher ] && target=\$sh
echo "alive at \$(el)s; sending ${STOPSIG:-INT} to ${STOPTO:-game} \$target (game \$game)" > $d/stop.txt
kill -${STOPSIG:-INT} \$target
for i in \$(seq 1 ${GRACE:-30}); do kill -0 \$sh 2>/dev/null || break; sleep 1; done
if kill -0 \$sh 2>/dev/null; then kill -9 \$game; wait \$sh; echo "ALIVE at limit; ${STOPSIG:-INT} did not end it in ${GRACE:-30}s (HUNG in shutdown), KILLed" > $d/result.txt
else wait \$sh; rc=\$?; echo "ALIVE at limit; after ${STOPSIG:-INT}: \$(how \$rc) at \$(el)s" > $d/result.txt; fi
EOF
  chmod 755 "$d/runner.sh"
  if [ "$user" = root ]; then setsid nohup bash "$d/runner.sh" </dev/null >/dev/null 2>&1 &
  else setsid nohup su "$user" -s /bin/bash -c "bash $d/runner.sh" </dev/null >/dev/null 2>&1 & fi
  echo "started $name ($user, ${secs}s): $d"
  if [ -n "$VIEWER" ]; then
    local v=$VIEWER vd=30; [ "$(echo "$v" | tr -cd , | wc -c)" = 3 ] && { vd=${v##*,}; v=${v%,*}; }
    setsid nohup node "$TOOLS/fake_viewer.cjs" "$v" "$vd" > "$d/viewer.log" 2>&1 </dev/null &
  fi
}

status() {
  for d in "$R"/${1:-*}/; do
    [ -d "$d" ] || continue
    local n; n=$(basename "$d")
    printf '%-22s %s\n' "$n" "$(cat "$d/result.txt" 2>/dev/null || echo 'RUNNING')"
  done
}

case "$1" in
  run) shift; run "$@" ;;
  status) status "$2" ;;
  ss)
    if [ "$2" = start ]; then
      (cd "$C/infra/SignallingWebServer" && setsid nohup node --require "$TOOLS/localhost.cjs" dist/index.js --no_config \
        --serve --http_root www --homepage player.html --player_port 8090 --streamer_port 8888 --streamer_host 127.0.0.1 \
        --log_folder "$R/sslogs" --console_messages verbose </dev/null > "$R/ss.log" 2>&1 & echo $! > "$R/ss.pid")
      echo "signalling started $(cat "$R/ss.pid")"
    else
      for p in $(pgrep -x node); do
        tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q 'localhost.cjs' && kill "$p" && echo "stopped signalling $p"
      done
    fi ;;
  stopall)
    for p in $(pgrep -x MurderInc-Linux; pgrep -x MurderInc); do
      tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q "cloud/" && kill -9 "$p" && echo "killed $p"
    done ;;
  *) sed -n 2,22p "$0"; exit 2 ;;
esac
