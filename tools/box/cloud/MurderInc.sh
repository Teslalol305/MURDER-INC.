#!/bin/bash
# MURDER INC. on Eagle 3D Streaming (E3DS): the launcher at the root of the cloud zip. E3DS runs this file (the app
# name MurderInc is the name of this script). tools/box/cloud/package-cloud.sh puts it in the zip in place of the
# engine's own launcher; docs/LAUNCH.md sections 9 and 13 say how to read what it writes.
#
# It starts the Shipping game the way the engine's launcher does (MurderInc-Linux-Shipping MurderInc ... "$@"), with:
#   -MICloud              the cloud profile and the click-to-play card (Source/MurderInc/Cloud/MICloud.h)
#   -RenderOffScreen      no window: no X server or display is needed (Pixel Streaming captures the frames itself)
#   -UserDir=<here>/MurderInc   Saved/ (logs, crash reports, settings) next to the game, where a Development build
#                         keeps it, when this folder is writable (else under $HOME, else /tmp)
#   -stdout -FullStdOutLogOutput   everything the game prints goes to the log below
# and the host's own arguments last ("$@": the Pixel Streaming connection, resolution, launch options). The game's
# environment gets SDL_AUDIODRIVER=dummy: the sound device that needs no sound card (the sound goes out with the stream).
#
# The log: MurderInc/Saved/Logs/MurderInc.log (the run before is kept as MurderInc-backup-<time>.log). It holds the
# build (BUILD.txt), who and where the game runs, the GPU and driver, the Vulkan check Unreal 5.9 needs, the free
# graphics memory, the arguments, every line the game prints, how the game ended (exit code or the signal that killed
# it) and, after a crash, the engine's crash report (Saved/Crashes/crashinfo-*/Diagnostics.txt: the call stack).
# Shipping builds have no engine log of their own (the installed engine cannot turn bUseLoggingInShipping on); the
# game prints its own report lines ("[MICloud] ...") and fatal errors still reach stdout.
#
# The host's own log file: E3DS starts every app with -ABSLOG=<file> (its documentation: "These are always sent:
# -PixelStreamingURL=, -PixelStreamingID=, -AudioMixer, -log, -Unattended, -StdOut, -FullStdOutLogOutput and
# -ABSLOG=") and takes its crash-log email from that file. A Shipping game writes nothing there ("no crashlog was
# found"), so this launcher writes it: everything that goes to the log above also goes to that file and to this
# launcher's own output. The argument itself is not passed on to the game (one writer per file).
#
# Stop signals (TERM, INT, HUP) are passed on to the game at once (and the game is killed if it is still there 8 s
# later); if this launcher itself is killed, a watchdog ends the game. Before the game starts, every other game of
# this package that is still running on the machine is stopped: see "leftovers" below.
# The game also looks after itself (release 3c, Source/MurderInc/Cloud/MISession.h): this launcher gives it its own
# process id (-MILauncherPid=<pid>), and a game whose launcher has been gone for 5 s quits (the watchdog below does the
# same from outside); with no viewer for 2 s the game idles, and 20 s after the last viewer left it quits, so that the
# game of an ended session does not go on drawing on the machine. -MIKeepAlive (a launch option, passed on) turns that
# off for a game that is held with no viewer on purpose (the box's test scripts).
# Started as root (Unreal refuses to run as root), the game runs as the folder's owner, or "nobody", with HOME in /tmp.
#
# Launch options (E3DS: the stream configuration's launch options arrive as arguments, and so does whatever a visitor
# writes after ?exeLaunchArgs= on the stream link):
#   -MIDev=<key>  run the Development game in the zip instead (the full engine log in MurderInc/Saved/Logs, with call
#                 stacks): for a crash the Shipping log does not explain. The key is the word in the file MIDEV.key
#                 beside this launcher (package-cloud.sh makes a new one for every zip; it is never printed). Without
#                 the right key the Shipping game runs: the Development game has the developer console, -ExecCmds and
#                 the debug switches the Shipping game was built without (-MICrashTest=, -MICloudLog=), and a visitor
#                 must not be able to start it from a link. A folder without MIDEV.key (a test folder on the box) takes
#                 the plain -MIDev.
#   -MIForceSM6   skip Unreal's Vulkan SM6 check (-SkipVulkanProfileCheck) on a driver that fails it; the game otherwise
#                 falls back to its SM5 shaders by itself (no Nanite, no Lumen)
#   -MIKeepOthers do not stop other games of this package that are running on the machine (see "leftovers" below)
#   -MIReapOthers stop every other game of this package, also off E3DS (the default there; elsewhere only those whose
#                 launcher is gone)
# Not passed on to the game: Pixel Streaming's debug dumps (-PixelStreaming...DumpDebug...), which write every frame or
# the sound to files on the server for as long as the game runs.

# Started by sh (dash) instead of bash: run again under bash; with no bash at all, start the game the engine's way.
if [ -z "$BASH_VERSION" ]; then
  command -v bash >/dev/null 2>&1 && exec bash "$0" "$@"
  chmod +x "$(dirname "$0")/MurderInc/Binaries/Linux/MurderInc-Linux-Shipping" 2>/dev/null
  SDL_AUDIODRIVER=dummy SDL_AUDIO_DRIVER=dummy exec "$(dirname "$0")/MurderInc/Binaries/Linux/MurderInc-Linux-Shipping" MurderInc -MICloud -RenderOffScreen "$@"
fi

# Started as a background job of a non-interactive shell, this launcher would ignore SIGINT and could not trap it:
# run again once with SIGINT and SIGQUIT back to default (coreutils env), so a stop by SIGINT reaches the trap below.
if [ -z "$MI_LAUNCHER_SIGRESET" ] && env --default-signal=INT true 2>/dev/null; then
  export MI_LAUNCHER_SIGRESET=1
  exec env --default-signal=INT,QUIT bash "$0" "$@"
fi

ROOT=$(dirname "$(readlink -f "$0")")
PROJ=$ROOT/MurderInc
STAMP=$(date -u +%Y%m%d-%H%M%S)

# The host stops reading this launcher's output: writes fail instead of killing the launcher (Unreal ignores SIGPIPE
# itself).
trap '' PIPE

DEV=0; DEVASKED=; FORCESM6=0; ABS=; PASS=(); DROPPED=; KEEPOTHERS=0; REAPALL=0
# The key of the Development game: one word in MIDEV.key (absent in a test folder: the plain -MIDev then works).
DEVKEY=$(head -c 200 "$ROOT/MIDEV.key" 2>/dev/null | tr -d ' \t\r\n')
shopt -s nocasematch   # Unreal's arguments are case-insensitive
for a in "$@"; do
  case "$a" in
    -MIDev) DEVASKED=1; [ -z "$DEVKEY" ] && DEV=1 ;;
    -MIDev=*) DEVASKED=1; v=${a#*=}; v=${v#\"}; v=${v%\"}; { [ -z "$DEVKEY" ] || [ "$v" = "$DEVKEY" ]; } && DEV=1 ;;
    -MIForceSM6) FORCESM6=1 ;;
    -MIKeepOthers) KEEPOTHERS=1 ;;
    -MIReapOthers) REAPALL=1 ;;
    -ABSLOG=*) ABS=${a#*=}; ABS=${ABS#\"}; ABS=${ABS%\"} ;;   # the host's log file: written below, not passed on
    -PixelStreaming*DumpDebug*) DROPPED="$DROPPED ${a%%=*}" ;;   # files written on the server: not from a link
    *) PASS+=("$a") ;;
  esac
done
shopt -u nocasematch
BIN=$PROJ/Binaries/Linux/MurderInc-Linux-Shipping
[ "$DEV" = 1 ] && [ -f "$PROJ/Binaries/Linux/MurderInc" ] && BIN=$PROJ/Binaries/Linux/MurderInc
chmod +x "$BIN" 2>/dev/null

# Who runs the game: Unreal aborts when started as root ("Refusing to run with the root privileges").
RUNAS=(); RUNUSER=$(id -un 2>/dev/null || id -u)
if [ "$(id -u)" = 0 ]; then
  RUNUSER=$(stat -c %U "$ROOT" 2>/dev/null)
  { [ -z "$RUNUSER" ] || [ "$RUNUSER" = root ] || [ "$RUNUSER" = UNKNOWN ]; } && RUNUSER=nobody
  RUNUID=$(id -u "$RUNUSER" 2>/dev/null); RUNGID=$(id -g "$RUNUSER" 2>/dev/null)
  RUNHOME=/tmp/MurderInc-home-$RUNUSER
  mkdir -p "$RUNHOME" && chown "$RUNUID:$RUNGID" "$RUNHOME" 2>/dev/null
  if command -v setpriv >/dev/null 2>&1; then
    RUNAS=(setpriv "--reuid=$RUNUID" "--regid=$RUNGID" --init-groups env "HOME=$RUNHOME" "USER=$RUNUSER" "LOGNAME=$RUNUSER")
  elif command -v runuser >/dev/null 2>&1; then
    RUNAS=(runuser -u "$RUNUSER" -- env "HOME=$RUNHOME" "USER=$RUNUSER" "LOGNAME=$RUNUSER")
  else
    RUNAS=(su -s /bin/sh "$RUNUSER" -c "HOME=$RUNHOME USER=$RUNUSER LOGNAME=$RUNUSER exec \"\$0\" \"\$@\"")
  fi
fi

# A Saved folder the game's user can write (the launcher itself may be root).
writable() {
  mkdir -p "$1/Saved/Logs" 2>/dev/null || return 1
  if [ ${#RUNAS[@]} -gt 0 ]; then
    chown -R "$RUNUID:$RUNGID" "$1/Saved" 2>/dev/null
    "${RUNAS[@]}" test -w "$1/Saved" && "${RUNAS[@]}" test -w "$1/Saved/Logs"
  else
    test -w "$1/Saved" && test -w "$1/Saved/Logs"
  fi
}
USERDIR=
for d in "$PROJ" "${HOME:-/nonexistent}/MurderInc-cloud" "${TMPDIR:-/tmp}/MurderInc-cloud-$RUNUSER"; do
  case "$d" in *" "*) continue ;; esac   # the engine reads -UserDir= up to the first space
  if writable "$d"; then USERDIR=$d; break; fi
done
if [ -n "$USERDIR" ]; then
  LOGDIR=$USERDIR/Saved/Logs
else
  LOGDIR=${TMPDIR:-/tmp}/MurderInc-logs-$$; mkdir -p "$LOGDIR"
fi
# Shipping writes no log file of its own, so this log is MurderInc.log; the Development game writes MurderInc.log
# itself, so then this one is MurderInc-stdout.log.
NAME=MurderInc.log; [ "$BIN" != "${BIN%/MurderInc}" ] && NAME=MurderInc-stdout.log
LOG=$LOGDIR/$NAME
if [ -f "$LOG" ]; then mv -f "$LOG" "$LOGDIR/${NAME%.log}-backup-$STAMP.log" 2>/dev/null; fi
ls -1t "$LOGDIR"/MurderInc*-backup-*.log 2>/dev/null | tail -n +11 | while read -r f; do rm -f "$f"; done
: > "$LOG" 2>/dev/null || { LOGDIR=${TMPDIR:-/tmp}; LOG=$LOGDIR/MurderInc-$STAMP-$$.log; : > "$LOG"; }
chmod 644 "$LOG" 2>/dev/null
# The host's log file (-ABSLOG=). ABSLATE: the Development game writes that very file itself (it is its own default
# log), so this launcher only adds its closing lines to it, after the game has ended.
OUTS=("$LOG"); ABSNOTE=; ABSLATE=
if [ -n "$ABS" ]; then
  mkdir -p "$(dirname "$ABS")" 2>/dev/null
  if [ "$(readlink -f "$ABS" 2>/dev/null)" = "$(readlink -f "$LOG")" ]; then
    ABSNOTE="the host's log file (-ABSLOG=) is this log"
  elif [ "$NAME" = MurderInc-stdout.log ] && [ "$(readlink -f "$ABS" 2>/dev/null)" = "$(readlink -f "$LOGDIR/MurderInc.log")" ]; then
    ABSLATE=$ABS; ABSNOTE="the host's log file (-ABSLOG=) is the Development game's own log $ABS"
  else
    if [ -s "$ABS" ]; then mv -f "$ABS" "${ABS%.*}-backup-$STAMP.${ABS##*.}" 2>/dev/null; fi
    if : > "$ABS" 2>/dev/null; then
      chmod 644 "$ABS" 2>/dev/null; OUTS+=("$ABS"); ABSNOTE="also written to the host's log file (-ABSLOG=) $ABS"
    else
      ABSNOTE="CANNOT WRITE the host's log file (-ABSLOG=) $ABS as $(id -un 2>/dev/null): the host will find no log there"
    fi
  fi
fi
# Every line of this launcher goes to the log, to the host's log file and to this launcher's own output.
out() {
  local line f
  while IFS= read -r line || [ -n "$line" ]; do
    printf '%s\n' "$line" 2>/dev/null
    for f in "${OUTS[@]}"; do printf '%s\n' "$line" >> "$f" 2>/dev/null; done
  done
}
note() { echo "[MurderInc.sh] $*" | out; }
section() { { echo "[MurderInc.sh] ---- $1"; shift; "$@" 2>&1; } | out; }

# ---- before the game: where it runs ----
note "MURDER INC. launcher, $(date -u '+%Y-%m-%d %H:%M:%S UTC'), pid $$"
note "build: $(tr '\n' ' ' < "$ROOT/BUILD.txt" 2>/dev/null || echo 'no BUILD.txt')"
note "folder $ROOT; game $BIN; log $LOG; saved ${USERDIR:-(none writable: the engine default)}/Saved"
note "host log: ${ABSNOTE:-no -ABSLOG= argument (the host named no log file)}"
note "launcher user $(id 2>/dev/null); game user $RUNUSER; HOME=${HOME:-unset} PWD=$PWD"
note "DISPLAY=${DISPLAY:-unset} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset} XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-unset}"
note "system: $(uname -srm 2>/dev/null); $(grep -m1 PRETTY_NAME /etc/os-release 2>/dev/null)"
note "memory: $(free -m 2>/dev/null | awk '/^Mem:/{print $2" MB total, "$7" MB available"}'); disk here: $(df -Pm "$ROOT" 2>/dev/null | awk 'NR==2{print $4" MB free"}'); core dumps: $(ulimit -c)"
# The CPUs the game may use. With 8 hyper-threaded CPUs or fewer Unreal starts 6 task workers or fewer, and its Vulkan
# RHI then runs without its interrupt and submission threads (the game's own "CPUs:" line below says which it is).
note "CPUs: $(nproc 2>/dev/null || echo '?') usable, $(grep -c '^processor' /proc/cpuinfo 2>/dev/null || echo '?') in the machine;$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2- | tr -s ' ')"
[ -n "$DEVASKED" ] && [ "$DEV" = 0 ] && note "launch option -MIDev NOT taken: this package starts its Development game only with -MIDev=<key> (the word in the file MIDEV.key beside this launcher; it is not printed anywhere). The Shipping game runs."
[ -n "$DROPPED" ] && note "launch option(s) not passed on to the game (they write files on the server):$DROPPED"
if command -v nvidia-smi >/dev/null 2>&1; then
  section "GPU (nvidia-smi): name, driver, memory total / used / free" timeout 10 nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free --format=csv,noheader
  section "GPU processes (anything else holding graphics memory)" timeout 10 nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
else
  note "no nvidia-smi"
fi

# ---- leftovers: games of earlier sessions that are still running ----
# E3DS gives a machine to one session at a time (its documentation: a dedicated session has its own machine) but does
# not always end the game of the session before. Measured on E3DS (docs/unreal/DECISIONS.md, 2026-11-25): the game of a
# session that had ended minutes before was still running, holding 3.4 GB of the card and drawing at full speed; the
# next session on that machine ran at a third of the speed, the one after that at a fifth. So before this game starts,
# the other games of this package on the machine (the Shipping or the Development binary, any folder) are stopped: always
# those that nobody started and nothing waits for (their launcher is gone: the parent is init), and on an E3DS machine
# (the folder is .../0.apps/<account>/<app>/<version>) every other one, whatever its parent. TERM first, KILL 4 s later.
#   -MIKeepOthers  leave them alone (two games of this package on one machine, on purpose)
#   -MIReapOthers  stop every other game, also off E3DS (a test machine)
pstate() { local s; s=$(< "/proc/$1/stat") 2>/dev/null || return 1; s=${s##*) }; echo "${s%% *}"; }
pppid() { local s; s=$(< "/proc/$1/stat") 2>/dev/null || return 1; s=${s##*) }; set -- $s; echo "$2"; }
reap_leftovers() {
  [ "$KEEPOTHERS" = 1 ] && { note "leftovers: not looked for (-MIKeepOthers)"; return 0; }
  local anc=" " p d pid cmd ppid st age rss mode=orphans victims=() v n=0
  # This launcher and everything above it are never touched.
  p=$$; while [ -n "$p" ] && [ "$p" -gt 1 ] 2>/dev/null; do anc="$anc$p "; p=$(pppid "$p"); done
  case "$ROOT" in */0.apps/*) mode=all ;; esac
  [ "$REAPALL" = 1 ] && mode=all
  for d in /proc/[0-9]*; do
    pid=${d#/proc/}
    case "$anc" in *" $pid "*) continue ;; esac
    cmd=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null) || continue
    case "$cmd" in
      */Binaries/Linux/MurderInc-Linux-Shipping\ *|*/Binaries/Linux/MurderInc\ MurderInc\ *) ;;
      *) continue ;;
    esac
    st=$(pstate "$pid") || continue
    [ "$st" = Z ] || [ "$st" = X ] && continue   # already dead, only not collected yet
    ppid=$(pppid "$pid")
    age=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' '); rss=$(awk '/^VmRSS/{printf "%d", $2/1024}' "$d/status" 2>/dev/null)
    if [ "$mode" = all ] || [ "$ppid" = 1 ]; then
      victims+=("$pid"); note "leftover game: pid $pid (parent $ppid, state $st, running ${age:-?} s, ${rss:-?} MB): stopping it"
    else
      note "other game: pid $pid (parent $ppid, state $st, running ${age:-?} s, ${rss:-?} MB): left alone (it has a launcher; -MIReapOthers stops it)"
    fi
  done
  [ ${#victims[@]} -gt 0 ] || { note "leftovers: no other game of this package is running"; return 0; }
  for v in "${victims[@]}"; do kill -s TERM "$v" 2>/dev/null; done
  for n in 1 2 3 4 5 6 7 8; do
    p=0; for v in "${victims[@]}"; do [ -d "/proc/$v" ] && st=$(pstate "$v") && [ "$st" != Z ] && p=1; done
    [ "$p" = 0 ] && break; sleep 0.5
  done
  for v in "${victims[@]}"; do
    if [ -d "/proc/$v" ] && st=$(pstate "$v") && [ "$st" != Z ] && [ "$st" != X ]; then kill -s KILL "$v" 2>/dev/null; note "leftover game $v did not stop in 4 s: killed"; fi
  done
  sleep 1
  note "leftovers: ${#victims[@]} stopped"
  command -v nvidia-smi >/dev/null 2>&1 && section "GPU after the leftovers were stopped: name, driver, memory total / used / free" timeout 10 nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free --format=csv,noheader
}
reap_leftovers

# Libraries the game cannot start without (the Vulkan loader and the NVIDIA Vulkan driver come from the server).
MISSINGLIB=$(ldd "$BIN" 2>/dev/null | grep "not found" | tr -s ' \t' ' ')
note "libraries: ${MISSINGLIB:+MISSING$MISSINGLIB}${MISSINGLIB:-all found (ldd)}; Vulkan loader: $( (ldconfig -p 2>/dev/null | grep -m1 -o 'libvulkan.so.1 .*') || echo 'not in ldconfig')"
note "Vulkan drivers (ICD files): $(ls /usr/share/vulkan/icd.d/ /etc/vulkan/icd.d/ 2>/dev/null | grep -i json | tr '\n' ' ')${VK_ICD_FILENAMES:+ VK_ICD_FILENAMES=$VK_ICD_FILENAMES}"
# Unreal 5.9 runs its full renderer (SM6: Nanite, Lumen) only when the driver passes this check (the profile in
# Engine/Source/ThirdParty/Vulkan/profiles/include/vulkan_profiles_ue.h); else it falls back to SM5.
SM6EXT="VK_EXT_calibrated_timestamps VK_EXT_descriptor_buffer VK_EXT_descriptor_indexing VK_EXT_mesh_shader VK_EXT_mutable_descriptor_type VK_EXT_scalar_block_layout VK_EXT_shader_image_atomic_int64 VK_KHR_buffer_device_address VK_KHR_compute_shader_derivatives VK_KHR_maintenance4 VK_KHR_pipeline_library VK_KHR_push_descriptor VK_KHR_separate_depth_stencil_layouts VK_KHR_shader_atomic_int64 VK_KHR_synchronization2 VK_KHR_timeline_semaphore"
if command -v vulkaninfo >/dev/null 2>&1; then
  VI=$(timeout 15 vulkaninfo 2>/dev/null)
  # Here-strings, not pipes: with SIGPIPE ignored (above) an early-exiting grep would make echo report a write error.
  note "Vulkan: $(grep -m1 -E 'apiVersion' <<< "$VI" | tr -s ' ') $(grep -m1 -E 'driverInfo|driverVersion' <<< "$VI" | tr -s ' ')"
  MISSING=; for e in $SM6EXT; do grep -q "$e" <<< "$VI" || MISSING="$MISSING $e"; done
  if [ -n "$MISSING" ]; then note "Vulkan SM6 check: MISSING$MISSING (the game will use its SM5 fallback: no Nanite, no Lumen)"
  else note "Vulkan SM6 check: all $(echo $SM6EXT | wc -w) extensions present"; fi
  RT=; for e in VK_KHR_ray_tracing_pipeline VK_KHR_acceleration_structure VK_KHR_ray_query; do grep -q "$e" <<< "$VI" || RT="$RT $e"; done
  note "Vulkan ray tracing: ${RT:+MISSING$RT (software Lumen)}${RT:-present}"
else
  note "no vulkaninfo on this server: the Vulkan check is in the game's own lines below ([MICloud] GPU / Features)"
fi

# ---- the sound: the same on every server, whatever its environment says ----
# The game's sound needs no sound card: Unreal mixes it and Pixel Streaming sends it to the browser. But Unreal's mixer
# only runs on an audio device that SDL can open. With -RenderOffScreen Unreal asks SDL for its "dummy" device, which
# needs nothing from the machine (LinuxPlatformApplicationMisc.cpp, ApplySDLAudioDriverHint) -- unless the environment
# already names a driver, which SDL then obeys: started with SDL_AUDIODRIVER=alsa on a machine without a sound card,
# the game logs "ALSA: Couldn't open audio device", "Main audio device could not be initialized", starts no sound at
# all and sends a stream without any (measured on the GPU box, docs/unreal/PROGRESS.md "Version 3b: sound"). So the
# launcher names the dummy device itself, under both names SDL reads.
# The dummy device keeps its own size of buffer (1,024 samples): it then takes sound a little faster than real time
# (1.011 s a second on the GPU box; a browser's player absorbs that, and no packet is ever short). Asked for 960 samples
# (SDL_AUDIO_DEVICE_SAMPLE_FRAMES) it takes sound a little slower than real time, and the stream then has holes: 20
# drop-outs of up to 40 ms in a minute (box run snd-env-960). So that setting is cleared as well.
SNDNOTE="SDL_AUDIODRIVER=${SDL_AUDIODRIVER:-unset} SDL_AUDIO_DRIVER=${SDL_AUDIO_DRIVER:-unset} SDL_AUDIO_DEVICE_SAMPLE_FRAMES=${SDL_AUDIO_DEVICE_SAMPLE_FRAMES:-unset} as the host set them"
export SDL_AUDIODRIVER=dummy SDL_AUDIO_DRIVER=dummy
unset SDL_AUDIO_DEVICE_SAMPLE_FRAMES
note "sound: $SNDNOTE; the game gets SDL's dummy audio device (no sound card or sound service is needed: the sound goes out with the stream)"

# -MILauncherPid=: this launcher's own id (the game is its child, started below). Before the host's arguments: the first
# one counts, so a link cannot name another process for the game to watch.
ARGS=(MurderInc -MICloud -RenderOffScreen "-MILauncherPid=$$")
[ -n "$USERDIR" ] && ARGS+=("-UserDir=$USERDIR")
ARGS+=(-stdout -FullStdOutLogOutput)
[ "$FORCESM6" = 1 ] && ARGS+=(-SkipVulkanProfileCheck)
note "start: ${RUNAS[*]} $BIN ${ARGS[*]} ${PASS[*]}"
note "---- the game"

# A background job of a non-interactive shell starts with SIGINT and SIGQUIT ignored, and Unreal keeps an ignored
# SIGINT ignored: give the game the default back (coreutils env), so a host's Ctrl+C-style stop reaches it.
DEFSIG=(); env --default-signal=INT,QUIT true 2>/dev/null && DEFSIG=(env --default-signal=INT,QUIT)

# ---- the game: its output goes to the log (and to this launcher's own output, which the host may read) ----
FIFO=
command -v tee >/dev/null 2>&1 && FIFO=$(mktemp -u "${TMPDIR:-/tmp}/MurderInc-out.XXXXXX") && { mkfifo "$FIFO" || FIFO=; }
TEE=
if [ -n "$FIFO" ]; then
  # tee ignores stop signals (a host that signals the whole process group must not kill it: the game would then die
  # of SIGPIPE on its next line); it ends when the game closes its output. -p: keep writing the file if the host
  # stops reading this launcher's output.
  TOPT=-a; tee --version 2>/dev/null | grep -q GNU && TOPT=-ap
  ( trap '' TERM INT HUP PIPE; exec tee $TOPT "${OUTS[@]}" ) < "$FIFO" & TEE=$!
  START=$(date +%s)
  "${RUNAS[@]}" "${DEFSIG[@]}" "$BIN" "${ARGS[@]}" "${PASS[@]}" > "$FIFO" 2>&1 &
else
  START=$(date +%s)
  "${RUNAS[@]}" "${DEFSIG[@]}" "$BIN" "${ARGS[@]}" "${PASS[@]}" >> "$LOG" 2>&1 &
fi
GAME=$!
NOTEE=; [ -z "$FIFO" ] && NOTEE=1
# A stop signal for this launcher goes on to the game AT ONCE, once, as SIGTERM (the game may still ignore SIGINT, see
# DEFSIG, never SIGTERM), and the game is killed if it is still there 8 s later. This used to wait 5 s for the game to
# end by itself (a host that signals the whole process group reaches the game directly, and Unreal takes a second
# signal during its shutdown as "quit now": no clean exit); but a host that stops only this launcher and kills it a
# moment later then left the game running with nobody to stop it, which is what E3DS did: the game of an ended session
# went on drawing on the card for minutes (docs/unreal/DECISIONS.md, 2026-11-25). A game that quits at once instead of
# cleanly is the lesser harm.
STOPPED=; FWD=
alive() { local st; st=$(pstate "$GAME") && [ "$st" != Z ] && [ "$st" != X ]; }
trap 'STOPPED=TERM' TERM
trap 'STOPPED=INT' INT
trap 'STOPPED=HUP' HUP
# If this launcher is killed (SIGKILL cannot be trapped), a watchdog outlives it, sees it gone and stops the game: TERM
# after 3 s (a host that signals the whole group stops the game itself in that time), KILL 8 s after that. It holds
# none of the launcher's pipes (the host would otherwise wait for it) and ends with the game.
LAUNCHER=$$
(
  trap '' TERM INT HUP PIPE
  while :; do l=$(pstate "$LAUNCHER") || break; [ "$l" = Z ] || [ "$l" = X ] && break; sleep 2; done
  sleep 3
  if g=$(pstate "$GAME") && [ "$g" != Z ] && [ "$g" != X ]; then
    kill -s TERM "$GAME" 2>/dev/null; sleep 8
    if g=$(pstate "$GAME") && [ "$g" != Z ] && [ "$g" != X ]; then kill -s KILL "$GAME" 2>/dev/null; fi
  fi
) > /dev/null 2>&1 < /dev/null &
while :; do
  wait "$GAME"; RC=$?
  alive || break
  if [ -n "$STOPPED" ] && [ -z "$FWD" ]; then
    kill -s TERM "$GAME" 2>/dev/null; FWD=1; note "got SIG$STOPPED: passed it on to the game as SIGTERM"
    ( sleep 8; kill -s KILL "$GAME" 2>/dev/null ) > /dev/null 2>&1 < /dev/null &
  fi
done
# The game may have been reaped by the wait that the trap interrupted: its status is then the last wait's.
wait "$GAME" 2>/dev/null; R2=$?; [ "$R2" != 127 ] && RC=$R2
[ -n "$TEE" ] && wait "$TEE" 2>/dev/null
[ -n "$FIFO" ] && rm -f "$FIFO"

# ---- after the game ----
SECS=$(( $(date +%s) - START ))
# Without tee the game's lines are only in the log: copy them to the host's file now. The Development game's own
# log (ABSLATE) is closed now: the closing lines below go there too.
if [ -n "$NOTEE" ] && [ ${#OUTS[@]} -gt 1 ]; then cat "$LOG" > "${OUTS[1]}" 2>/dev/null; fi
[ -n "$ABSLATE" ] && OUTS+=("$ABSLATE")
# A stop the host asked for: the game ended by (or with the code of) a stop signal while one was pending.
HOSTSTOP=
if [ -n "$STOPPED" ] && { [ "$RC" = 130 ] || [ "$RC" = 143 ] || [ "$RC" = 129 ]; }; then HOSTSTOP=1; fi
if [ "$RC" -gt 128 ] && [ "$RC" -lt 160 ]; then
  SIG=$(kill -l $((RC - 128)) 2>/dev/null)
  if [ -n "$HOSTSTOP" ]; then
    note "the game was stopped by SIG$SIG after the host's SIG$STOPPED, after ${SECS}s"
  else
    note "CRASH: the game was killed by signal $((RC - 128)) (SIG$SIG) after ${SECS}s"
  fi
elif [ "$RC" = 0 ]; then
  note "the game quit normally after ${SECS}s${STOPPED:+ (stop asked by SIG$STOPPED)}"
else
  note "the game ENDED with exit code $RC after ${SECS}s${STOPPED:+ (stop asked by SIG$STOPPED)} (1 within seconds of the start: usually a missing shader platform, see the Vulkan check above)"
fi
# The engine's crash report (written by its crash handler into Saved/Crashes, also in Shipping).
SEEN=
for c in "${USERDIR:-/nonexistent}/Saved/Crashes" "$PROJ/Saved/Crashes" "${HOME:-/nonexistent}/.config/Epic/MurderInc/Saved/Crashes"; do
  [ -d "$c" ] || continue
  case " $SEEN " in *" $(readlink -f "$c") "*) continue ;; esac   # USERDIR is usually $PROJ: read each folder once
  SEEN="$SEEN $(readlink -f "$c")"
  find "$c" -mindepth 1 -maxdepth 1 -type d -newermt "@$START" 2>/dev/null | while read -r d; do
    note "---- crash report $d"
    for f in "$d"/Diagnostics.txt; do [ -f "$f" ] && head -c 60000 "$f" | out; done
  done
done
note "end: exit code $RC; log $LOG"
# A stop the host asked for is a normal quit.
[ -n "$HOSTSTOP" ] && exit 0
exit "$RC"
