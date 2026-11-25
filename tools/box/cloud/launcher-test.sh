#!/bin/bash
# The launcher MurderInc.sh against a fake game: no GPU, no Unreal, a few seconds a case. It proves what the launcher
# does with a game process, so that a change to it (release 3c: it now gives the game its own process id) keeps every
# behaviour of version 4's launcher (docs/unreal/DECISIONS.md, 2026-11-25: the stop signal goes on to the game at once,
# a watchdog stops the game when the launcher is killed, the exit code passes through, the host's own log file is
# written, a second game of the package is stopped as a leftover).
#
#   launcher-test.sh [path to MurderInc.sh]      default: the one beside this file; run as an ordinary user (as root the
#                                                launcher runs the game as the folder's owner, which needs a user for it)
# Each case prints "ok" or "FAILED <what>"; the last line says LAUNCHER-TEST OK or FAILED.
L=${1:-$(dirname "$(readlink -f "$0")")/MurderInc.sh}
[ "$(id -u)" = 0 ] && { echo "run as an ordinary user"; exit 2; }
W=$(mktemp -d "${TMPDIR:-/tmp}/launcher-test.XXXXXX")
trap 'pkill -f "$W/" 2>/dev/null; rm -rf "$W"' EXIT
FAILS=0
ok() { echo "ok      $*"; }
bad() { echo "FAILED  $*"; FAILS=$((FAILS + 1)); }
check() { # check <description> <command...>
  local d=$1; shift
  if "$@"; then ok "$d"; else bad "$d"; fi
}

mkpkg() {  # mkpkg <name>: a package folder with the launcher and a fake Shipping game
  local P=$W/$1
  mkdir -p "$P/MurderInc/Binaries/Linux"
  cp "$L" "$P/MurderInc.sh"; chmod +x "$P/MurderInc.sh"
  cat > "$P/MurderInc/Binaries/Linux/MurderInc-Linux-Shipping" <<'EOF'
#!/bin/bash
# A fake game: says its arguments and its parent, ends on TERM, or by itself with the exit code a case asks for.
echo "FAKE-GAME pid $$ parent $PPID args: $*"
echo "$$ $PPID" > "${FAKE_PID_FILE:-/dev/null}"
trap 'echo FAKE-GAME-GOT-TERM; exit 0' TERM
for a in "$@"; do case "$a" in -fake-exit=*) exit "${a#*=}" ;; esac; done
while :; do sleep 0.2; done
EOF
  chmod +x "$P/MurderInc/Binaries/Linux/MurderInc-Linux-Shipping"
  echo "$P"
}
alive() { [ -d "/proc/$1" ] && [ "$(awk '{print $3}' "/proc/$1/stat" 2>/dev/null | tr -d ' ')" != Z ]; }
waitfor() { local f=$1 i; for i in $(seq 1 100); do [ -s "$f" ] && return 0; sleep 0.1; done; return 1; }
gone() { local pid=$1 secs=$2 i; for i in $(seq 1 $((secs * 10))); do alive "$pid" || return 0; sleep 0.1; done; return 1; }

# 1. The game is given the launcher's own process id, as the first of the host's arguments; its parent is the launcher;
#    the exit code passes through.
P=$(mkpkg one); FAKE_PID_FILE=$W/one.pid bash "$P/MurderInc.sh" -fake-exit=3 -PixelStreamingURL=ws://127.0.0.1:1 > "$W/one.out" 2>&1; RC=$?
LP=$(grep -o 'launcher, [^,]*, pid [0-9]*' "$W/one.out" | head -1 | grep -o '[0-9]*$')
GAMEARGS=$(grep 'FAKE-GAME' "$W/one.out" | head -1)
check "the launcher prints its own pid ($LP)" [ -n "$LP" ]
check "the game's arguments name that pid: -MILauncherPid=$LP" grep -q -- "-MILauncherPid=$LP " <<< "$GAMEARGS"
check "-MILauncherPid comes before the host's own arguments" bash -c '[[ "$1" == *"-MILauncherPid="*"-PixelStreamingURL="* ]]' _ "$GAMEARGS"
check "the game's parent is the launcher" grep -q "parent $LP " <<< "$GAMEARGS"
check "the game's exit code 3 is the launcher's" [ "$RC" = 3 ]

# 2. A link cannot name another process: a -MILauncherPid of the host's comes after the launcher's, and the game reads the first.
P=$(mkpkg two); FAKE_PID_FILE=$W/two.pid bash "$P/MurderInc.sh" -fake-exit=0 -MILauncherPid=999999 > "$W/two.out" 2>&1
LP2=$(grep -o 'launcher, [^,]*, pid [0-9]*' "$W/two.out" | head -1 | grep -o '[0-9]*$')
check "a host's -MILauncherPid=999999 stands behind the launcher's own" bash -c 'l=$(grep FAKE-GAME "$1" | head -1); a=${l#*-MILauncherPid=}; [ "${a%% *}" = "$2" ]' _ "$W/two.out" "$LP2"
check "-MIKeepAlive and the other options reach the game" bash -c 'FAKE_PID_FILE=/dev/null bash "$1/MurderInc.sh" -fake-exit=0 -MIKeepAlive -MIExitAfterEmpty=8 2>&1 | grep FAKE-GAME | grep -q -- "-MIKeepAlive -MIExitAfterEmpty=8"' _ "$P"

# 3. A stop signal for the launcher goes on to the game at once, and the launcher ends with it (exit code 0: a host's stop).
P=$(mkpkg three); FAKE_PID_FILE=$W/three.pid bash "$P/MurderInc.sh" -PixelStreamingURL=ws://127.0.0.1:1 > "$W/three.out" 2>&1 &
LPID=$!
if waitfor "$W/three.pid"; then
  GPID=$(cut -d' ' -f1 "$W/three.pid")
  kill -TERM "$LPID"
  check "SIGTERM to the launcher: the game ends within 2 s" gone "$GPID" 2
  check "... and so does the launcher" gone "$LPID" 3
  check "... the game was told with SIGTERM" grep -q FAKE-GAME-GOT-TERM "$W/three.out"
  wait "$LPID"; check "... the launcher's exit code is 0 (a stop the host asked for)" [ "$?" = 0 ]
else bad "the fake game did not start"; kill "$LPID" 2>/dev/null; fi

# 4. A launcher that is killed outright (SIGKILL cannot be trapped): its watchdog stops the game (TERM after 3 s).
P=$(mkpkg four); FAKE_PID_FILE=$W/four.pid bash "$P/MurderInc.sh" > "$W/four.out" 2>&1 &
LPID=$!
if waitfor "$W/four.pid"; then
  GPID=$(cut -d' ' -f1 "$W/four.pid")
  kill -KILL "$LPID"
  sleep 1
  check "the launcher is gone, the game still runs for the moment" alive "$GPID"
  check "the watchdog stops the game within 12 s of the launcher's death" gone "$GPID" 12
else bad "the fake game did not start"; kill "$LPID" 2>/dev/null; fi

# 5. Another game of the package that nobody waits for (its launcher is gone) is stopped when the next launcher starts.
P=$(mkpkg five)
(setsid "$P/MurderInc/Binaries/Linux/MurderInc-Linux-Shipping" MurderInc -leftover > "$W/leftover.out" 2>&1 < /dev/null &)
sleep 0.5
OLD=$(pgrep -f "$P/MurderInc/Binaries/Linux/MurderInc-Linux-Shipping MurderInc -leftover" | head -1)
if [ -n "$OLD" ]; then
  # -MIReapOthers: stop every other game of the package, whoever its parent is (off E3DS the default only stops orphans).
  FAKE_PID_FILE=$W/five.pid bash "$P/MurderInc.sh" -MIReapOthers -fake-exit=0 > "$W/five.out" 2>&1
  check "a leftover game of the package is stopped before the new game starts" gone "$OLD" 8
  check "the log names it" grep -q "leftover game" "$W/five.out"
else ok "(case 5 skipped: the leftover could not be told from the shell script that starts it)"; fi

# 6. The host's log file is written.
P=$(mkpkg six); FAKE_PID_FILE=/dev/null bash "$P/MurderInc.sh" -fake-exit=0 "-ABSLOG=$W/host.log" > "$W/six.out" 2>&1
check "the host's log (-ABSLOG=) holds the game's lines and the launcher's" bash -c 'grep -q FAKE-GAME "$1" && grep -q "MurderInc.sh" "$1"' _ "$W/host.log"
check "the host's own -ABSLOG= is not passed on to the game" bash -c '! grep FAKE-GAME "$1" | grep -qi -- "-ABSLOG"' _ "$W/six.out"

if [ "$FAILS" = 0 ]; then echo "LAUNCHER-TEST OK"; else echo "LAUNCHER-TEST FAILED ($FAILS)"; exit 1; fi
