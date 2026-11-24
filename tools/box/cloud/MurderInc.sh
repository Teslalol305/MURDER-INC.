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
# and the host's own arguments last ("$@": the Pixel Streaming connection, resolution, launch options).
#
# The log: MurderInc/Saved/Logs/MurderInc.log (the run before is kept as MurderInc-backup-<time>.log). It holds the
# build (BUILD.txt), who and where the game runs, the GPU and driver, the Vulkan check Unreal 5.9 needs, the free
# graphics memory, the arguments, every line the game prints, how the game ended (exit code or the signal that killed
# it) and, after a crash, the engine's crash report (Saved/Crashes/crashinfo-*/Diagnostics.txt: the call stack).
# Shipping builds have no engine log of their own (the installed engine cannot turn bUseLoggingInShipping on); the
# game prints its own report lines ("[MICloud] ...") and fatal errors still reach stdout.
#
# Stop signals (TERM, INT, HUP) are passed on to the game, which then quits normally (exit code 0).
# Started as root (Unreal refuses to run as root), the game runs as the folder's owner, or "nobody", with HOME in /tmp.
#
# Launch options (E3DS: the stream configuration's launch options arrive as arguments):
#   -MIDev        run the Development game in the zip instead (the full engine log in MurderInc/Saved/Logs, with call
#                 stacks): for a crash the Shipping log does not explain
#   -MIForceSM6   skip Unreal's Vulkan SM6 check (-SkipVulkanProfileCheck) on a driver that fails it; the game otherwise
#                 falls back to its SM5 shaders by itself (no Nanite, no Lumen)

# Started by sh (dash) instead of bash: run again under bash; with no bash at all, start the game the engine's way.
if [ -z "$BASH_VERSION" ]; then
  command -v bash >/dev/null 2>&1 && exec bash "$0" "$@"
  exec "$(dirname "$0")/MurderInc/Binaries/Linux/MurderInc-Linux-Shipping" MurderInc -MICloud -RenderOffScreen "$@"
fi

ROOT=$(dirname "$(readlink -f "$0")")
PROJ=$ROOT/MurderInc
STAMP=$(date -u +%Y%m%d-%H%M%S)

DEV=0; FORCESM6=0; PASS=()
for a in "$@"; do
  case "$a" in
    -MIDev|-midev) DEV=1 ;;
    -MIForceSM6|-miforcesm6) FORCESM6=1 ;;
    *) PASS+=("$a") ;;
  esac
done
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
note() { echo "[MurderInc.sh] $*" >> "$LOG"; }
section() { echo "[MurderInc.sh] ---- $1" >> "$LOG"; shift; "$@" >> "$LOG" 2>&1; }

# ---- before the game: where it runs ----
note "MURDER INC. launcher, $(date -u '+%Y-%m-%d %H:%M:%S UTC'), pid $$"
note "build: $(tr '\n' ' ' < "$ROOT/BUILD.txt" 2>/dev/null || echo 'no BUILD.txt')"
note "folder $ROOT; game $BIN; log $LOG; saved ${USERDIR:-(none writable: the engine default)}/Saved"
note "launcher user $(id 2>/dev/null); game user $RUNUSER; HOME=${HOME:-unset} PWD=$PWD"
note "DISPLAY=${DISPLAY:-unset} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset} XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-unset}"
note "system: $(uname -srm 2>/dev/null); $(grep -m1 PRETTY_NAME /etc/os-release 2>/dev/null)"
note "memory: $(free -m 2>/dev/null | awk '/^Mem:/{print $2" MB total, "$7" MB available"}'); disk here: $(df -Pm "$ROOT" 2>/dev/null | awk 'NR==2{print $4" MB free"}'); core dumps: $(ulimit -c)"
if command -v nvidia-smi >/dev/null 2>&1; then
  section "GPU (nvidia-smi): name, driver, memory total / used / free" timeout 10 nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free --format=csv,noheader
  section "GPU processes (anything else holding graphics memory)" timeout 10 nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
else
  note "no nvidia-smi"
fi
# Libraries the game cannot start without (the Vulkan loader and the NVIDIA Vulkan driver come from the server).
MISSINGLIB=$(ldd "$BIN" 2>/dev/null | grep "not found" | tr -s ' \t' ' ')
note "libraries: ${MISSINGLIB:+MISSING$MISSINGLIB}${MISSINGLIB:-all found (ldd)}; Vulkan loader: $( (ldconfig -p 2>/dev/null | grep -m1 -o 'libvulkan.so.1 .*') || echo 'not in ldconfig')"
note "Vulkan drivers (ICD files): $(ls /usr/share/vulkan/icd.d/ /etc/vulkan/icd.d/ 2>/dev/null | grep -i json | tr '\n' ' ')${VK_ICD_FILENAMES:+ VK_ICD_FILENAMES=$VK_ICD_FILENAMES}"
# Unreal 5.9 runs its full renderer (SM6: Nanite, Lumen) only when the driver passes this check (the profile in
# Engine/Source/ThirdParty/Vulkan/profiles/include/vulkan_profiles_ue.h); else it falls back to SM5.
SM6EXT="VK_EXT_calibrated_timestamps VK_EXT_descriptor_buffer VK_EXT_descriptor_indexing VK_EXT_mesh_shader VK_EXT_mutable_descriptor_type VK_EXT_scalar_block_layout VK_EXT_shader_image_atomic_int64 VK_KHR_buffer_device_address VK_KHR_compute_shader_derivatives VK_KHR_maintenance4 VK_KHR_pipeline_library VK_KHR_push_descriptor VK_KHR_separate_depth_stencil_layouts VK_KHR_shader_atomic_int64 VK_KHR_synchronization2 VK_KHR_timeline_semaphore"
if command -v vulkaninfo >/dev/null 2>&1; then
  VI=$(timeout 15 vulkaninfo 2>/dev/null)
  note "Vulkan: $(echo "$VI" | grep -m1 -E 'apiVersion' | tr -s ' ') $(echo "$VI" | grep -m1 -E 'driverInfo|driverVersion' | tr -s ' ')"
  MISSING=; for e in $SM6EXT; do echo "$VI" | grep -q "$e" || MISSING="$MISSING $e"; done
  if [ -n "$MISSING" ]; then note "Vulkan SM6 check: MISSING$MISSING (the game will use its SM5 fallback: no Nanite, no Lumen)"
  else note "Vulkan SM6 check: all $(echo $SM6EXT | wc -w) extensions present"; fi
  RT=; for e in VK_KHR_ray_tracing_pipeline VK_KHR_acceleration_structure VK_KHR_ray_query; do echo "$VI" | grep -q "$e" || RT="$RT $e"; done
  note "Vulkan ray tracing: ${RT:+MISSING$RT (software Lumen)}${RT:-present}"
else
  note "no vulkaninfo on this server: the Vulkan check is in the game's own lines below ([MICloud] GPU / Features)"
fi

ARGS=(MurderInc -MICloud -RenderOffScreen)
[ -n "$USERDIR" ] && ARGS+=("-UserDir=$USERDIR")
ARGS+=(-stdout -FullStdOutLogOutput)
[ "$FORCESM6" = 1 ] && ARGS+=(-SkipVulkanProfileCheck)
note "start: ${RUNAS[*]} $BIN ${ARGS[*]} ${PASS[*]}"
note "---- the game"

# ---- the game: its output goes to the log (and to this launcher's own output, which the host may read) ----
FIFO=
command -v tee >/dev/null 2>&1 && FIFO=$(mktemp -u "${TMPDIR:-/tmp}/MurderInc-out.XXXXXX") && { mkfifo "$FIFO" || FIFO=; }
TEE=
if [ -n "$FIFO" ]; then
  # tee ignores stop signals (a host that signals the whole process group must not kill it: the game would then die
  # of SIGPIPE on its next line); it ends when the game closes its output. -p: keep writing the file if the host
  # stops reading this launcher's output.
  TOPT=-a; tee --version 2>/dev/null | grep -q GNU && TOPT=-ap
  ( trap '' TERM INT HUP PIPE; exec tee $TOPT "$LOG" ) < "$FIFO" & TEE=$!
  START=$(date +%s)
  "${RUNAS[@]}" "$BIN" "${ARGS[@]}" "${PASS[@]}" > "$FIFO" 2>&1 &
else
  START=$(date +%s)
  "${RUNAS[@]}" "$BIN" "${ARGS[@]}" "${PASS[@]}" >> "$LOG" 2>&1 &
fi
GAME=$!
# A stop signal for this launcher goes on to the game, once, and only if the game did not get it too: a host that
# signals the whole process group reaches the game directly, and Unreal treats a second signal during its shutdown as
# "quit now" (no clean exit). So: wait up to 5 s for the game to end by itself, then pass the signal on.
STOPPED=; FWD=
alive() { local st=; read -r _ _ st _ 2>/dev/null < "/proc/$GAME/stat"; [ -n "$st" ] && [ "$st" != Z ]; }
trap 'STOPPED=TERM' TERM
trap 'STOPPED=INT' INT
trap 'STOPPED=HUP' HUP
while :; do
  wait "$GAME"; RC=$?
  alive || break
  if [ -n "$STOPPED" ] && [ -z "$FWD" ]; then
    for i in 1 2 3 4 5 6 7 8 9 10; do alive || break; sleep 0.5; done
    if alive; then kill -s "$STOPPED" "$GAME" 2>/dev/null; FWD=1; note "passed SIG$STOPPED on to the game"; fi
  fi
done
# The game may have been reaped by the wait that the trap interrupted: its status is then the last wait's.
wait "$GAME" 2>/dev/null; R2=$?; [ "$R2" != 127 ] && RC=$R2
[ -n "$TEE" ] && wait "$TEE" 2>/dev/null
[ -n "$FIFO" ] && rm -f "$FIFO"

# ---- after the game ----
SECS=$(( $(date +%s) - START ))
if [ "$RC" -gt 128 ] && [ "$RC" -lt 160 ]; then
  SIG=$(kill -l $((RC - 128)) 2>/dev/null)
  if [ -n "$STOPPED" ] && [ "$SIG" = "$STOPPED" ]; then
    note "the game was stopped by SIG$SIG (sent by the host) after ${SECS}s"
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
    for f in "$d"/Diagnostics.txt; do [ -f "$f" ] && head -c 60000 "$f" >> "$LOG"; done
  done
done
note "end: exit code $RC; log $LOG"
# A stop the host asked for is a normal quit.
if [ -n "$STOPPED" ] && [ "$RC" -gt 128 ] && [ "$RC" -lt 160 ] && [ "$(kill -l $((RC - 128)) 2>/dev/null)" = "$STOPPED" ]; then
  exit 0
fi
exit "$RC"
