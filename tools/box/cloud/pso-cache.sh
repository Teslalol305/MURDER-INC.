#!/bin/bash
# The bundled pipeline cache (docs/unreal/SMOOTH.md H3, H4), recorded from a package and turned into the file the next
# cook bundles. Run as root on the box.
#
#   pso-cache.sh record <build folder> <runs folder> [script ...]   detached: one -logPSO run of the Development game per
#                     recording script (default: pso/rec-*.txt beside this file) under the
#                     hitch lane's conditions (lag-test.sh: l20 load, cpus=0-7, -sm5, a fresh user, a clean Saved, a
#                     viewer), one at a time under the GPU claim; each run's recording lands in <runs folder>/<run>/
#   pso-cache.sh status <runs folder>                     how far the recording got
#   pso-cache.sh expand <release copy> <keys folder> <out.spc> <recording> ...
#                     the engine's ShaderPipelineCacheTools: recordings + the cook's stable shader keys -> a stable cache
#                     (MurderInc_SF_VULKAN_SM5.spc). The keys must be from the cook of the package that was recorded
#                     (package-cloud.sh keeps them in <cloud>/pso-keys); the release copy is the project the
#                     commandlet loads (its editor module built)
#   pso-cache.sh dump <file>                                the commandlet's dump of a recording or a cache (counts)
#
# The steps, end to end (each checked against Unreal 5.9's ShaderPipelineCache.cpp, PipelineFileCache.cpp,
# ShaderLibraryCooking.cpp and CopyBuildToStagingDirectory.Automation.cs):
#  1. package the commit (package-cloud.sh): Config/DefaultEngine.ini has [DevOptions.Shaders] NeedsShaderStableKeys, so
#     the cook writes its stable shader keys, and r.Vulkan.EnablePSOFileCacheWhenPrecachingActive=1, without which
#     Vulkan has no pipeline file cache at all while PSO precaching is on ("PipelineFileCache = 0" in the game log)
#  2. record: pso-cache.sh record (the game's -logPSO writes Saved/CollectedPSOs/*.rec.upipelinecache on every
#     "r.ShaderPipelineCache.Save" of the scripts and at the end). r.ShaderPipelineCache.IncludeAllPrecachedPSOs=1: without
#     it a recording holds only the PSOs the precacher did not have (117 in a whole Story run, rec-a of 2026-11-26), not
#     the ones it compiled late, which are the cold start's misses
#  3. expand the recordings with that cook's keys into unreal/MurderInc/Build/Linux/PipelineCaches/MurderInc_SF_VULKAN_SM5.spc
#     and commit it
#  4. package again: the cook finds the .spc and writes Content/PipelineCaches/Linux/MurderInc_SF_VULKAN_SM5.stable.upipelinecache,
#     the stage puts it in the pak; package-cloud.sh checks the pak list (PSO CACHE OK) and refuses a zip without it
#  5. the game opens it at start and compiles every PSO in it (r.ShaderPipelineCache.PSOPrecacheIncludeMode=0) on the
#     precaching threads in its Fast mode, while the title waits for the viewer; the probe line's psoLeft counts down to 0
# Record again whenever materials, shaders or the engine change: a PSO whose shaders are no longer in the cook is skipped
# (the cache degrades, it does not break), new ones are not in it.
T=$(dirname "$(readlink -f "$0")")
ME=$(readlink -f "$0")
ENGINE=/project/ue/UnrealEngine
CLAIM=pso-claim

others() {  # MURDER INC. games or another lane's claim on the GPU (the suite's -nullrhi editors do not count)
  local p c
  for p in $(pgrep -x MurderInc; pgrep -x MurderInc-Linux); do
    c=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)
    case "$c" in *"$CLAIM"*|*-nullrhi*|*-NullRHI*) ;; ?*) return 0 ;; esac
  done
  return 1
}

record_fg() {
  local build=$1 out=$2; shift 2
  local scripts=("$@") s n ids= claim w=0
  [ ${#scripts[@]} -gt 0 ] || scripts=("$T"/pso/rec-*.txt)
  mkdir -p "$out"
  for s in "${scripts[@]}"; do n=rec-$(basename "$s" .txt | sed 's/^rec-//'); ids="$ids -PixelStreamingID=lag$(echo "$n" | tr -cd 'a-zA-Z0-9')"; done
  # The GPU claim (as the lanes' gated.sh): wait until no other game or claim draws, then hold a placeholder named
  # MurderInc whose command line carries this queue's streamer ids, so lag-test.sh in other lanes waits for it.
  until ! others; do sleep 1; w=$((w + 1)); [ $w -gt 7200 ] && { echo "$(date -u +%T) gave up waiting for the GPU"; return 1; }; done
  printf '#!/bin/bash\nsleep "$1"\n' > "$out/MurderInc"; chmod 755 "$out/MurderInc"
  setsid "$out/MurderInc" 5400 $CLAIM $ids < /dev/null > /dev/null 2>&1 &
  claim=$!
  echo "$(date -u +%T) GPU claimed after $w s (pid $claim)"
  for s in "${scripts[@]}"; do
    n=rec-$(basename "$s" .txt | sed 's/^rec-//')
    # Long enough for the script: about 0.9 s of game per line, at least 4 minutes, at most 14 (the GPU-run limit).
    local secs; secs=$(( $(grep -c . "$s") * 9 / 10 + 60 )); [ $secs -lt 240 ] && secs=240; [ $secs -gt 840 ] && secs=840
    # A script may name its viewer and its length ("# view: guns-keys.txt", "# secs: 170"): rec-d.txt is driven by the
    # viewer's keys, as a player drives the game, and only saves the recording itself.
    local view; view=$(sed -n 's/^# view: *//p' "$s" | head -1); [ -n "$view" ] || view=sound-watch.txt
    local own; own=$(sed -n 's/^# secs: *//p' "$s" | head -1); [ -n "$own" ] && secs=$own
    echo "$(date -u +%T) start $n ($s, secs=$secs)"
    (cd "$T" && LAG_OUT=$out LAG_RUNAS=fresh LAG_CLEAN=1 bash lag-test.sh run-fg "$n" game=dev "build=$build" "demo=$s" "view=$view" \
      join=3 "secs=$secs" load=1:0.05:0:1024 cpus=0-7 -- -sm5 -logPSO "-ini:Engine:[ConsoleVariables]:r.ShaderPipelineCache.IncludeAllPrecachedPSOs=1" \
      < /dev/null > "$out/$n.out" 2>&1)
    echo "$(date -u +%T) done $n: $(ls "$out/$n"/*.upipelinecache 2>/dev/null | wc -l) recording(s), $(du -ch "$out/$n"/*.upipelinecache 2>/dev/null | tail -1 | cut -f1); $(tail -1 "$out/$n/summary.txt" 2>/dev/null | cut -c1-160)"
  done
  kill $claim 2>/dev/null; pkill -x sleep -P $claim 2>/dev/null
  echo "$(date -u +%T) GPU released; RECORD-DONE"
}

expand() {
  local rel=$1 keys=$2 outf=$3; shift 3
  [ -f "$rel/unreal/MurderInc/MurderInc.uproject" ] || { echo "no release copy at $rel"; return 1; }
  local k; k=$(ls "$keys"/*SF_VULKAN_SM5* 2>/dev/null | grep -v upipelinecache | tr '\n' ' ')
  [ -n "$k" ] || { echo "no SM5 stable keys in $keys"; return 1; }
  mkdir -p "$(dirname "$outf")"; chown ue4 "$(dirname "$outf")"
  local log=${outf%.spc}.expand.log
  # The cache arguments of package-cloud.sh: without them the editor looks for a Zen server and crashes at start.
  su ue4 -c "cd $ENGINE && env HOME=/home/ue4 UE-LocalDataCachePath=/project/ue/ddc ./Engine/Binaries/Linux/UnrealEditor-Cmd $rel/unreal/MurderInc/MurderInc.uproject \
    -run=ShaderPipelineCacheTools expand $* $k $outf -unattended -nosplash -NullRHI -nopause -stdout -FullStdOutLogOutput -NoDDCCleanup \
    '-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal)' \
    -ini:Engine:[Zen]:AutoLaunch=false -ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1" > "$log" 2>&1 < /dev/null
  grep -a -E 'LogShaderPipelineCacheTools: (Display|Warning|Error)' "$log" | tail -12 | cut -c1-240
  [ -s "$outf" ] && echo "EXPAND OK: $outf $(stat -c %s "$outf") bytes (log $log)" || { echo "EXPAND FAILED (log $log)"; return 1; }
}

[ "$(id -u)" = 0 ] || { echo "run as root"; exit 1; }
case "$1" in
  record) shift; mkdir -p "$2"; setsid nohup bash "$ME" record-fg "$@" < /dev/null > "$2/record.log" 2>&1 & echo "started: watch $2/record.log" ;;
  record-fg) shift; record_fg "$@" ;;
  status) cat "$2/record.log" 2>/dev/null; for d in "$2"/rec-*/; do [ -d "$d" ] && echo "$(basename "$d"): $(tail -1 "$d/view.log" 2>/dev/null | cut -c1-100)"; done ;;
  expand) shift; expand "$@" ;;
  dump) su ue4 -c "cd $ENGINE && env UE-LocalDataCachePath=/project/ue/ddc ./Engine/Binaries/Linux/UnrealEditor-Cmd -run=ShaderPipelineCacheTools dump $2 -unattended -nosplash -NullRHI -stdout \
          '-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal)' -ini:Engine:[Zen]:AutoLaunch=false" 2>&1 | grep -a -E 'LogShaderPipelineCacheTools' | tail -15 ;;
  *) sed -n 2,40p "$0"; exit 2 ;;
esac
