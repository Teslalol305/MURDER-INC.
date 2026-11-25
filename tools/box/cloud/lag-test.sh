#!/bin/bash
# The lag test: one game at a time on the box's GPU, streamed to a viewer that turns, under a chosen GPU load, with
# one summary line per run. It is how the lag of version 2 on E3DS ("when the player turns it slows down") was
# reproduced and explained, and it is the release gate of version 3 (docs/unreal/PREFLIGHT.md section 2,
# docs/unreal/PROGRESS.md "Version 3, release A"). Run as root on the box.
#
#   lag-test.sh run <name> [key=value ...] [-- game arguments]   start one run, detached (about 2 minutes)
#   lag-test.sh queue <file>                                      one run per line of the file (the words after
#                                                                 "run"), one after another, detached; "# ..." skipped
#   lag-test.sh wait <name> [seconds]                             wait for it (at most 45 s a call: the box's limit)
#   lag-test.sh sum [-v] <name> ...                               the summary line(s) (lag_sum.py; -v: every probe line)
#   lag-test.sh csv <name> [limit ms]                             where the long frames went (lag_csv.py; csv=1 runs)
#   lag-test.sh calib <name> <load> <load> ...                    the GPU's time per frame under each load, one game
#   lag-test.sh hogs <n>[:<work ms>[:<idle ms>[:<size>]]] | stop  the load by hand
#   lag-test.sh list                                              every run so far, one line each
#
# Keys of run:
#   game=dev|ship     the Development game (launch option -MIDev: its own script starts a Story run with god mode;
#                     csv profile; the engine's log with Pixel Streaming's capture lines) or the Shipping game (the
#                     viewer clicks through the set-up screens). Default dev.
#   build=<folder>    the folder with MurderInc.sh: the unpacked zip (both games are in it). Default
#                     /project/ue/cloud/build-Shipping/Linux, or $LAG_BUILD.
#   load=<n>[:<work ms>[:<idle ms>[:<size>]]]   n second processes that keep the GPU busy (gpu_hog.py), each
#                     working in bursts of <work ms> (4) with <idle ms> (0) between them on matrices of <size>
#                     (2048). This is a load the game's own dynamic resolution cannot undo: a GPU that is slower
#                     for the game whatever it draws. Calibrated loads: see "calib" and PROGRESS.md. Default 0.
#   sp=<percent>      r.ScreenPercentage through the Development game's script: the simple load. It is not what a slow
#                     GPU does (400 % is sixteen times the pixels), and dynamic resolution replaces it. Default none.
#   res=<W>x<H>       the output size. Default 1920x1080.
#   view=<file>       the viewer's script (rtcinput.py), a path or the name of one beside this file. Default
#                     lag-turn.txt (dev) or lag-story.txt (ship); lag-commands.txt, lag-leave.txt, lag-rise.txt,
#                     lag-input.txt and lag-pad.txt are the others (each says at its top what it is for);
#                     lag-stops.txt is lag-story.txt with faster turns that stop dead (the release check's viewer).
#   view2=<file>      a second viewer who joins 3 s after the first has left (its log: view2.log): what the next
#                     viewer finds (lag-input2.txt).
#   cvars=<a=b,c=d>   passed as the launch option -MICVars= (the game's own tuning switch).
#   profile=1         for a test folder whose pak is older than the branch: version 3's additions to the cloud
#                     profile (the r.DynamicRes., MI.Cloud. and PixelStreaming2. lines of [MICloud] in the branch's
#                     DefaultGame.ini) are passed as -MICVars, and the input device mapping policy of the branch's
#                     DefaultInput.ini is written into the folder's Saved config (without it the engine raises an
#                     ensure when a controller connects), and so is the quality ladder's table (the QualitySteps= lines
#                     of the branch's DefaultGame.ini, release 3c, read through -MIQualityTable=). Not needed for a packaged build.
#   csv=1             a CSV profile of the Development game from the start of the run.
#   secs=<n>          how long the game runs. Default 110 (dev) or 125 (ship).
#   probe=<seconds>   the probe line's period. Default 1.
#   minbit=<bits/s>   the stream's lowest and first bitrate. Default 12000000: the Python viewer's congestion feedback
#                     is basic and the sender would otherwise drop most frames to fit a bitrate of a megabit or less;
#                     0 leaves the bitrate as E3DS starts it.
#   decode=0          the viewer does not decode the video (rtcinput.py --nodecode): it only counts the frames, and
#                     saves none. For the question whether the decoding beside the game slows the game's encoder.
#   env=<A=b,C=d>     more variables in the launcher's environment (e3ds-repro.sh ENVS), which is otherwise built
#                     from nothing: what a host's own environment might hold (SDL_AUDIODRIVER=alsa, for the sound).
#   demo=<file>       the Development game plays this script of its demo director instead of the built-in run (a path,
#                     or the name of one beside this file: sound-demo.txt, sound-dead.txt); the viewer then joins as
#                     for the Shipping game, join= seconds after the game's first probe line, so it is there from the
#                     script's first seconds. Give the script's length with secs=.
#   audio=1           the viewer is rtcaudio.py: the same script, and the sound it receives is recorded to sound.wav
#                     (sound.wav.json: when every sound packet came, when every script line was sent) and measured per
#                     half second; the summary line gets what was heard (loudness, peak, clipped samples, drop-outs).
#                     audio_find.py then says which of the game's samples are in the recording and how long after a
#                     fire input the gun's sound came.
#   cpus=<list>       the game runs on these CPUs only (a taskset list such as 0-5): a server with few CPUs. With 6 or
#                     fewer task workers (8 hyper-threaded CPUs or fewer; 7 or fewer on this box, which shows no
#                     hyper-threads) Unreal's Vulkan RHI runs without its interrupt and submission threads. The load
#                     and the viewer keep all CPUs. Default: all.
#   runas=ue4|fresh|root   who starts the launcher (e3ds-repro.sh RUNAS): fresh is a user with a new, empty home for
#                     every run, as on a host that starts each session on a machine that never ran the game. Default
#                     ue4, or $LAG_RUNAS.
#   join=<seconds>    the Shipping game's viewer joins this long after the game's first probe line (about 8 s after
#                     the start). Default 55, or $LAG_JOIN: the home screen has warmed up by then. join=3 is a player
#                     who is there at once and reaches the run about 20 s after the game started: with runas=fresh
#                     clean=1 that is the coldest start a host can give.
#   clean=1           the build folder's Saved (settings, logs, shader and pipeline caches of earlier runs) is removed
#                     before the run: a fresh copy of the zip, which is what a host unpacks for a session. Default 0,
#                     or $LAG_CLEAN. The release gate on a package is run with both: unzip the zip as the user
#                     e3dsfresh, then LAG_BUILD=<that folder> LAG_RUNAS=fresh LAG_CLEAN=1 lag-test.sh queue lag-gate.txt
#   qp=<min>:<max>    the encoder's -PixelStreamingEncoderMinQP and MaxQP (default 18:36). E3DS's Medium is 34:34, its
#                     High 16:16 (docs/unreal/DECISIONS.md, 2026-11-25); the game takes them as the centre of a range
#                     (release 3c, MI.Cloud.QpBelow / QpAbove), -MIQpExact after "--" turns that off.
#   vopts=<a,b,...>   more options for the viewer (rtcinput.py), the words joined by commas (a queue file's line has no
#                     spaces to give): --delay-ms,N  --link-kbps,N  --link-queue-ms,N  --remb-kbps,N make the viewer's
#                     link (the box has no tc: rtcinput.py's header says how), --player,WxH.
#   viewer=0          no viewer at all: the game runs alone until its limit (secs) or until it quits by itself, which a
#                     streamed game without -MIKeepAlive does 600 s after its start when nobody came (MI.Cloud.
#                     ExitIfNoViewer; -- -MIExitIfNoViewer=40 shortens it). The idle game's and the unwatched game's runs.
#   keepalive=0       the game is NOT given -MIKeepAlive (default 1). Since release 3c a streamed game idles when no
#                     viewer watches and quits 60 s after the last viewer left (MI.Cloud.IdleFps, ExitAfterEmpty,
#                     ExitIfNoViewer: docs/LAUNCH.md section 9): every run of this tool holds a game with no viewer on
#                     purpose (the Development game plays its script before the viewer joins, a run goes on after its
#                     viewer left, the calibration has no viewer at all), so each is started with -MIKeepAlive and
#                     measures the game as before. keepalive=0 is for a run of the session's own behaviour (the idle
#                     game, the quit after the last viewer, a viewer that comes back): the game then does what a
#                     package does on E3DS, and a result of "ENDED BY ITSELF: EXIT 0" is the game quitting as designed.
# Anything after -- goes to the game as it is (for example -PixelStreamingDecoupleFramerate).
#
# One game at a time: a run waits (up to 10 minutes) until no other MURDER INC. game runs on the box, and a watcher
# notes once a second whether one appeared and how busy the GPU was; the summary says CLEAN or POLLUTED. Runs that
# shared the GPU are thrown away (several games on one card produce the very stall this test is about).
# Each run keeps its files in /project/ue/cloud/lag/<name>/: info.txt, game.log, view.log, others.log, the frames the
# viewer saved, the CSV profile, summary.txt.
C=/project/ue/cloud
T=$(dirname "$(readlink -f "$0")")
OUT=${LAG_OUT:-$C/lag}
PY=/tmp/fps/venv/bin/python
ME=$(readlink -f "$0")
mkdir -p "$OUT"

games() {  # MURDER INC. game processes other than those of streamer id $1
  local n=0 p c
  for p in $(pgrep -x MurderInc-Linux; pgrep -x MurderInc); do
    c=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)
    [ -n "$c" ] || continue   # a process on its way out has no command line left: not a game that draws
    case "$c" in *"-PixelStreamingID=$1 "*) ;; *) n=$((n + 1)) ;; esac
  done
  echo $n
}

venv() {  # the viewer's Python (aiortc); /tmp is lost when the box restarts
  [ -x "$PY" ] && "$PY" -c 'import aiortc, websockets, PIL' 2>/dev/null && return 0
  python3 -m venv /tmp/fps/venv && /tmp/fps/venv/bin/pip -q install aiortc websockets pillow
}

hogs() {  # <n>[:<work ms>[:<idle ms>[:<size>]]] <pid file> <log prefix> | stop <pid file>
  if [ "$1" = stop ]; then
    local p; for p in $(cat "$2" 2>/dev/null); do kill "$p" 2>/dev/null; done; rm -f "$2"; return
  fi
  local n=${1%%:*} rest= i
  [ "${1#*:}" != "$1" ] && rest=${1#*:}
  for i in $(seq 1 "$n"); do
    # shellcheck disable=SC2086  (work, idle and size are separate arguments)
    setsid nohup /opt/venv/bin/python3 -I "$T/gpu_hog.py" ${rest//:/ } > "$3$i.log" 2>&1 < /dev/null &
    echo $! >> "$2"
  done
  [ "$n" -gt 0 ] && for i in $(seq 1 40); do [ "$(cat "$3"*.log 2>/dev/null | grep -c 'hog running')" -ge "$n" ] && break; sleep 0.5; done
}

run_fg() {
  local name=$1; shift
  local O=$OUT/$name game=dev build= load=0 sp= res=1920x1080 view= view2= cvars= csv= secs= probe=1 minbit=12000000 profile= cpus= decode=1 audio=0 demo= envs= extra=()
  local runas=${LAG_RUNAS:-ue4} clean=${LAG_CLEAN:-0} join=${LAG_JOIN:-55} keepalive=1 qp=18:36 vopts= withviewer=1
  while [ $# -gt 0 ]; do
    case "$1" in
      --) shift; extra=("$@"); break ;;
      game=*) game=${1#*=} ;; build=*) build=${1#*=} ;; load=*) load=${1#*=} ;; sp=*) sp=${1#*=} ;;
      res=*) res=${1#*=} ;; view=*) view=${1#*=} ;; cvars=*) cvars=${1#*=} ;; csv=*) csv=${1#*=} ;;
      secs=*) secs=${1#*=} ;; probe=*) probe=${1#*=} ;; minbit=*) minbit=${1#*=} ;; profile=*) profile=${1#*=} ;;
      cpus=*) cpus=${1#*=} ;; decode=*) decode=${1#*=} ;; view2=*) view2=${1#*=} ;;
      runas=*) runas=${1#*=} ;; clean=*) clean=${1#*=} ;; join=*) join=${1#*=} ;; audio=*) audio=${1#*=} ;; demo=*) demo=${1#*=} ;; env=*) envs=${1#*=} ;;
      keepalive=*) keepalive=${1#*=} ;; qp=*) qp=${1#*=} ;; vopts=*) vopts=${1#*=} ;; viewer=*) withviewer=${1#*=} ;;
      *) echo "unknown key $1"; return 2 ;;
    esac; shift
  done
  [ -n "$build" ] || build=${LAG_BUILD:-$C/build-Shipping/Linux}
  [ -n "$view" ] || { view=lag-turn.txt; [ "$game" = ship ] && view=lag-story.txt; }
  case "$view" in   # a bare name is one of the scripts beside this file; the viewer runs in the run's own folder
    /*) ;;
    *) if [ -f "$T/$view" ]; then view=$T/$view; else view=$(readlink -f "$view"); fi ;;
  esac
  case "$view2" in ''|/*) ;; *) if [ -f "$T/$view2" ]; then view2=$T/$view2; else view2=$(readlink -f "$view2"); fi ;; esac
  case "$demo" in ''|/*) ;; *) if [ -f "$T/$demo" ]; then demo=$T/$demo; else demo=$(readlink -f "$demo"); fi ;; esac
  # A fresh copy of the zip: nothing an earlier run left (the launcher makes Saved again, as the game's user).
  [ "$clean" = 1 ] && rm -rf "$build/MurderInc/Saved"
  if [ "$profile" = 1 ]; then
    # A folder whose pak is older than the branch: version 3's additions to the cloud profile ([MICloud] of
    # DefaultGame.ini: dynamic resolution, the game's pacing, Pixel Streaming's settings) as -MICVars, this run's own
    # cvars after them.
    local add; add=$(sed -n '/^\[MICloud\]/,/^\[/p' "$T/../../../unreal/MurderInc/Config/DefaultGame.ini" \
      | grep -E '^\+(CVars|StreamCVars)=(r\.DynamicRes\.|MI\.Cloud\.|PixelStreaming2\.)' | sed -E 's/^\+(CVars|StreamCVars)=//' | tr '\n' ',' | sed 's/,$//')
    cvars=${add}${cvars:+,$cvars}
    # The pak's DefaultInput.ini is older too: the mapping policy for controllers, before every run (the game deletes
    # a Saved ini it did not write when it exits).
    mkdir -p "$build/MurderInc/Saved/Config/Linux"
    printf '[InputPlatformSettings_Linux InputPlatformSettings]\ninput.DeviceMappingPolicy=3\n' > "$build/MurderInc/Saved/Config/Linux/Input.ini"
    # The pak's DefaultGame.ini is older too: the quality ladder's steps (release 3c, the [MICloud] QualitySteps= lines) go to a file the
    # game is told to read (-MIQualityTable=, below; not in the Shipping game). A Saved Game.ini does not do it: a packaged game does not
    # merge one (box run probe3: a +CVars line in it was not applied).
    sed -n '/^\[MICloud\]/,/^\[/p' "$T/../../../unreal/MurderInc/Config/DefaultGame.ini" | grep -E '^\+QualitySteps=' > "$build/MurderInc/Saved/qtable.txt" || true
    chmod 644 "$build/MurderInc/Saved/qtable.txt"
    chown -R ue4 "$build/MurderInc/Saved/Config" 2>/dev/null
  fi
  [ -n "$secs" ] || { secs=110; [ "$game" = ship ] && secs=125; }
  local id=lag$(echo "$name" | tr -cd 'a-zA-Z0-9')
  rm -rf "$O"; mkdir -p "$O"; chmod 777 "$O"
  printf 'name=%s\ngame=%s\nbuild=%s\nload=%s\nsp=%s\nres=%s\nview=%s\ncvars=%s\ncsv=%s\nsecs=%s\nminbit=%s\ncpus=%s\nid=%s\nextra=%s\nstarted=%s\nrunas=%s\nclean=%s\nprobe=%s\njoin=%s\naudio=%s\nkeepalive=%s\nqp=%s\nvopts=%s\n' \
    "$name" "$game" "$build" "$load" "$sp" "$res" "$view" "$cvars" "$csv" "$secs" "$minbit" "${cpus:-all}" "$id" "${extra[*]}" "$(date -u +%FT%TZ)" "$runas" "$clean" "$probe" "$join" "$audio" "$keepalive" "$qp" "$vopts" > "$O/info.txt"
  venv || { echo "FAILED: no Python with aiortc" > "$O/done"; return 1; }
  # One game at a time.
  local i
  for i in $(seq 1 120); do [ "$(games "$id")" = 0 ] && break; sleep 5; done
  echo "waited $((i - 1)) x 5 s for the GPU; other games now: $(games "$id")" >> "$O/info.txt"
  # A signalling server (Epic's; streamers on 8888, players on 8090): the one that runs, or ours.
  (exec 3<>/dev/tcp/127.0.0.1/8888) 2>/dev/null || { bash "$T/e3ds-repro.sh" ss start >> "$O/info.txt" 2>&1; sleep 4; }
  # The load.
  [ "${load%%:*}" -gt 0 ] 2>/dev/null && hogs "$load" "$O/hog.pids" "$O/hog"
  # The game, with the arguments E3DS passes (its documentation: FAQ, command-line parameters).
  local args=(-PixelStreamingURL=ws://127.0.0.1:8888 "-PixelStreamingID=$id" -AudioMixer -log -Unattended -StdOut -FullStdOutLogOutput
    "-ABSLOG=$O/abs.log" -AllowPixelStreamingCommands -Windowed -ForceRes "-ResX=${res%x*}" "-ResY=${res#*x}"
    -PixelStreamingEncoderCodec=H264 -PixelStreamingWebRTCMaxBitrate=20000000 "-PixelStreamingEncoderMinQP=${qp%%:*}"
    "-PixelStreamingEncoderMaxQP=${qp##*:}" "-MICloudProbe=$probe")
  # The Python viewer's congestion feedback is basic: the sender thinks the connection carries a quarter of a megabit,
  # then a few, and WebRTC drops most frames to fit (run x1: 60 captured, 2 to 58 encoded a second). minbit=<bits a
  # second> (default 12 Mbit/s; 0: as E3DS starts it) keeps the bitrate up, so the frames received say something
  # about the game and the capture.
  [ "$minbit" -gt 0 ] && args+=("-PixelStreamingWebRTCMinBitrate=$minbit" "-PixelStreamingWebRTCStartBitrate=$minbit")
  [ -n "$cvars" ] && args+=("-MICVars=$cvars")
  [ "$profile" = 1 ] && args+=("-MIQualityTable=$build/MurderInc/Saved/qtable.txt")   # the ladder's steps for a folder whose pak is older
  [ "$keepalive" = 1 ] && args+=(-MIKeepAlive)   # the game is held with no viewer on purpose (see the header)
  if [ "$game" = dev ]; then
    if [ -n "$demo" ]; then
      { grep -v '^[[:space:]]*#' "$demo"; echo "wait 900"; } > "$O/play.txt"   # the game's user must be able to read it
    else
    {
      echo "wait 4"; echo "con MIStart mission skip"; echo "waitstate playing 40"; echo "god 1"
      [ -n "$sp" ] && echo "con r.ScreenPercentage $sp"
      [ "$csv" = 1 ] && echo "con csvprofile start"
      echo "wait $((secs - 25))"
      [ "$csv" = 1 ] && echo "con csvprofile stop"
      echo "wait 900"
    } > "$O/play.txt"
    fi
    args+=(-MIDev "-ExecCmds=MIDemo.Run $O/play.txt")
    rm -rf "$build/MurderInc/Saved/Profiling/CSV"
  fi
  rm -rf "$build/MurderInc/Saved/SaveGames"   # a setting changed in one run (Look sensitivity) must not reach the next
  # The watcher: other games, the GPU, (cpu=) how busy all of the box's CPUs were in the last second, and (build=)
  # how many compiler, cook or editor processes ran (another job's on a shared box: they take CPUs, not the GPU, so
  # "CLEAN" does not see them). cpu= is for the sound first: a box whose CPUs are all busy in the half minute of a
  # cold start puts holes into the stream's sound that are not the package's (sound-gate.txt), so a run says what
  # the box was doing.
  ( ptot=; pidl=; while [ ! -f "$O/done" ]; do
      read -r _ cu cn cs ci cw cq csq cst _ < /proc/stat; tot=$((cu + cn + cs + ci + cw + cq + csq + cst)); idl=$((ci + cw)); busy=
      [ -n "$ptot" ] && [ $((tot - ptot)) -gt 0 ] && busy=$(( 100 * ((tot - ptot) - (idl - pidl)) / (tot - ptot) ))
      ptot=$tot; pidl=$idl
      echo "$(date -u +%T) others=$(games "$id") util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ') mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ') cpu=$busy build=$(pgrep -c -x 'clang\+\+|UnrealEditor|UnrealEditor-Cm|ShaderCompileWo|UnrealPak')"
      sleep 1
    done > "$O/others.log" 2>&1 ) &
  (cd "$T" && RUNAS="$runas" NODISPLAY=1 STOPSIG=TERM STOPTO=launcher STDOUT=0 CPUS="$cpus" BUILD="$build" ENVS="${envs//,/ }" bash e3ds-repro.sh run "lag-$name" "$secs" "${args[@]}" "${extra[@]}") >> "$O/info.txt" 2>&1
  local R=$C/repro/lag-$name
  if [ "$withviewer" = 0 ]; then   # no viewer: the game runs alone until its limit or until it quits by itself
    for i in $(seq 1 $((secs + 60))); do [ -f "$R/result.txt" ] && break; sleep 1; done
    hogs stop "$O/hog.pids"
    cp "$R/game.log" "$O/game.log" 2>/dev/null; cp "$R/result.txt" "$O/result.txt" 2>/dev/null
    echo DONE > "$O/done"; wait
    python3 "$T/lag_sum.py" "$O" > "$O/summary.txt" 2>&1
    cat "$O/summary.txt"
    return 0
  fi
  # The viewer joins when the game streams: in a run already (dev), or on its home screen (ship), join= seconds after
  # the game's first probe line. (Until 2026-11-25 the Shipping game's wait looked for a line that never comes and
  # ran its full 60 s, so the viewer of every earlier run found a home screen that had been drawn for about 55 s.
  # That stays the default, to keep the runs comparable; join=3 is a viewer who is there as soon as the game is.)
  # How long the game takes to its first line is noted (firstline=): 9 to 14 s for a cold start on a quiet box. Once
  # it took over a minute (version 3b's release, the first run of a queue, another job's compile beside it): the wait
  # used to end after 60 s, the viewer then came before the game had reached the signalling server, found no streamer
  # and left. It now waits up to three minutes, which is also as long as E3DS waits for an app.
  local t0; t0=$(date +%s)
  if [ "$game" = ship ] || [ -n "$demo" ]; then
    for i in $(seq 1 180); do grep -a -q "MICloudProbe fps=" "$R/game.log" 2>/dev/null && break; sleep 1; done
    echo "firstline=$(( $(date +%s) - t0 ))" >> "$O/info.txt"
    sleep "$join"
  else
    for i in $(seq 1 180); do grep -a -q "MICloudProbe fps=" "$R/game.log" 2>/dev/null && break; sleep 1; done
    echo "firstline=$(( $(date +%s) - t0 ))" >> "$O/info.txt"
    for i in $(seq 1 60); do grep -a -q "MICloudProbe.*state=2" "$R/game.log" 2>/dev/null && break; sleep 1; done
    sleep 3
  fi
  date -u +%T > "$O/view.start"
  local vopt=() viewer=rtcinput.py; [ "$decode" = 0 ] && vopt=(--nodecode)
  # shellcheck disable=SC2206  (the viewer's options are separate words)
  [ -n "$vopts" ] && vopt+=(${vopts//,/ })
  [ "$audio" = 1 ] && viewer=rtcaudio.py   # the same viewer with a recorder on the sound (sound.wav in the run's folder)
  (cd "$O" && timeout $((secs)) "$PY" "$T/$viewer" "$id" "$view" --out "$O" "${vopt[@]}" > "$O/view.log" 2>&1) || echo "VIEWER FAILED: $(tail -1 "$O/view.log")" >> "$O/info.txt"
  if [ -n "$view2" ]; then   # the next viewer, once the game has noticed that the first one left
    sleep 3; date -u +%T > "$O/view2.start"
    vopt=(); [ "$audio" = 1 ] && vopt=(--wav "$O/sound2.wav")
    (cd "$O" && timeout $((secs)) "$PY" "$T/$viewer" "$id" "$view2" --out "$O" "${vopt[@]}" > "$O/view2.log" 2>&1) || echo "SECOND VIEWER FAILED: $(tail -1 "$O/view2.log")" >> "$O/info.txt"
  fi
  for i in $(seq 1 $((secs + 60))); do [ -f "$R/result.txt" ] && break; sleep 1; done
  hogs stop "$O/hog.pids"
  cp "$R/game.log" "$O/game.log" 2>/dev/null; cp "$R/result.txt" "$O/result.txt" 2>/dev/null
  cp "$build"/MurderInc/Saved/Profiling/CSV/*.csv "$O/" 2>/dev/null
  echo DONE > "$O/done"; wait
  python3 "$T/lag_sum.py" "$O" > "$O/summary.txt" 2>&1
  cat "$O/summary.txt"
}

calib_fg() {  # <name> <load> ...: one Development game standing in a Story run at full quality; each load for 20 s
  local name=$1; shift
  local O=$OUT/$name id=lag$(echo "$name" | tr -cd 'a-zA-Z0-9') build=${LAG_BUILD:-$C/build-Shipping/Linux} i l
  rm -rf "$O"; mkdir -p "$O"; chmod 777 "$O"
  for i in $(seq 1 120); do [ "$(games "$id")" = 0 ] && break; sleep 5; done
  printf 'wait 4\ncon MIStart mission skip\nwaitstate playing 40\ngod 1\nwait 900\n' > "$O/play.txt"
  local secs=$((45 + 22 * $#))
  # Full quality: no dynamic resolution, the target fixed at 60; the pacer stays on, so frames do not pile up.
  (cd "$T" && RUNAS=ue4 NODISPLAY=1 STOPSIG=TERM STOPTO=launcher STDOUT=0 BUILD="$build" bash e3ds-repro.sh run "lag-$name" "$secs" \
    -PixelStreamingURL=ws://127.0.0.1:8888 "-PixelStreamingID=$id" -AudioMixer -log -Unattended -StdOut -FullStdOutLogOutput \
    -Windowed -ForceRes -ResX=1920 -ResY=1080 -MICloudProbe=1 -MICloudNoCard -MIKeepAlive -MIDev "-ExecCmds=MIDemo.Run $O/play.txt" \
    "-MICVars=r.DynamicRes.OperationMode=0,MI.Cloud.FpsTarget=60") > "$O/info.txt" 2>&1
  local R=$C/repro/lag-$name
  for i in $(seq 1 60); do grep -a -q "MICloudProbe.*state=2" "$R/game.log" 2>/dev/null && break; sleep 1; done
  sleep 8
  for l in "$@"; do
    rm -f "$O/hog.pids"; [ "${l%%:*}" -gt 0 ] 2>/dev/null && hogs "$l" "$O/hog.pids" "$O/hog-$l-"
    sleep 6; local from; from=$(grep -a -c MICloudProbe "$R/game.log")
    sleep 12
    grep -a MICloudProbe "$R/game.log" | tail -n +$((from + 1)) | python3 -c "
import re, sys
p = [dict(re.findall(r'(\w+)=(-?[\d.]+)', l)) for l in sys.stdin]
a = lambda k: sum(float(x[k]) for x in p) / max(len(p), 1)
print(f'load $l: GPU {a(\"gpuMs\"):5.1f} ms a frame, {a(\"fps\"):5.1f} frames a second, worst frame {max(float(x[\"worstMs\"]) for x in p):.0f} ms, other games $(games "$id") ({len(p)} s)')" | tee -a "$O/summary.txt"
    hogs stop "$O/hog.pids"; sleep 3
  done
  for i in $(seq 1 $((secs + 60))); do [ -f "$R/result.txt" ] && break; sleep 1; done
  cp "$R/game.log" "$O/game.log" 2>/dev/null
  echo DONE > "$O/done"
}

[ "$(id -u)" = 0 ] || { echo "run as root"; exit 1; }
case "$1" in
  run) shift; setsid nohup bash "$ME" run-fg "$@" < /dev/null > "$OUT/$1.out" 2>&1 & echo "started $1: poll lag-test.sh wait $1" ;;
  run-fg) shift; run_fg "$@" ;;
  calib) shift; setsid nohup bash "$ME" calib-fg "$@" < /dev/null > "$OUT/$1.out" 2>&1 & echo "started $1: poll lag-test.sh wait $1" ;;
  calib-fg) shift; calib_fg "$@" ;;
  queue) setsid nohup bash "$ME" queue-fg "$2" < /dev/null > "$OUT/queue.out" 2>&1 & echo "started the queue $2: watch $OUT/queue.out" ;;
  queue-fg) while read -r line; do
              case "$line" in ''|'#'*) continue ;; esac
              # shellcheck disable=SC2086  (the line is the run's words)
              run_fg $line < /dev/null
            done < "$2"; echo QUEUE-DONE ;;
  wait) for i in $(seq 1 "${3:-45}"); do [ -f "$OUT/$2/done" ] && break; sleep 1; done
        if [ -f "$OUT/$2/done" ]; then cat "$OUT/$2/summary.txt" 2>/dev/null || cat "$OUT/$2/done"; else echo "RUNNING $2: $(tail -1 "$OUT/$2/view.log" 2>/dev/null | cut -c1-100)"; fi ;;
  sum) shift; v=; [ "$1" = -v ] && { v=-v; shift; }; for n in "$@"; do python3 "$T/lag_sum.py" $v "$OUT/$n"; done ;;
  csv) python3 "$T/lag_csv.py" "$(ls "$OUT/$2"/*.csv | head -1)" "${3:-50}" ;;
  hogs) if [ "$2" = stop ]; then hogs stop "$OUT/hand.pids"; else hogs "$2" "$OUT/hand.pids" "$OUT/hand-hog"; cat "$OUT"/hand-hog*.log; fi ;;
  list) for d in "$OUT"/*/; do [ -f "$d/summary.txt" ] && cat "$d/summary.txt"; done ;;
  *) sed -n 2,41p "$0"; exit 2 ;;
esac
