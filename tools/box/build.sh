#!/bin/bash
# Build the editor target (MurderIncEditor Linux Development) on the box.
# Stops a running editor or test run first: they hold the module library that the build replaces.
# The build runs detached and this script returns at once; poll with build-status.sh.
# Usage: build.sh [clean] [extra UnrealBuildTool arguments, for example -NoUBA or -MaxParallelActions=8]
#   clean   delete the project's Binaries and Intermediate/Build first (full rebuild of the game module)
# Files in /project/ue/logs: build.log (full output), build.status (one word: RUNNING, OK or FAILED),
# build.start / build.end (epoch seconds), build.pid (the runner).
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
  mi_become_ue4 "$@"
  local st=$MI_LOGS/build.status

  if [ "$1" = --run ]; then
    shift
    echo $$ > "$MI_LOGS/build.pid"
    echo RUNNING > "$st"; date +%s > "$MI_LOGS/build.start"; rm -f "$MI_LOGS/build.end"
    cd "$MI_ENGINE" || exit 1
    ./Engine/Build/BatchFiles/Linux/Build.sh MurderIncEditor Linux Development "-project=$MI_UPROJECT" -waitmutex "$@" > "$MI_LOGS/build.log" 2>&1
    local rc=$?
    date +%s > "$MI_LOGS/build.end"
    echo "build exit code $rc" >> "$MI_LOGS/build.log"
    if [ $rc -eq 0 ]; then echo OK > "$st"; else echo FAILED > "$st"; fi
    exit $rc
  fi

  [ -f "$MI_UPROJECT" ] || mi_die "BUILD FAILED: $MI_UPROJECT is missing (run sync.sh)"
  if [ "$(cat "$st" 2>/dev/null)" = RUNNING ] && kill -0 "$(cat "$MI_LOGS/build.pid" 2>/dev/null)" 2>/dev/null; then
    echo "BUILD already RUNNING for $(( $(date +%s) - $(cat "$MI_LOGS/build.start") )) s: poll build-status.sh"
    return 0
  fi

  "$MI_BOX_DIR/editor.sh" stop >/dev/null 2>&1
  pkill -x UnrealEditor-Cm 2>/dev/null

  if [ "$1" = clean ]; then
    shift
    rm -rf "$MI_PROJECT_DIR/Binaries" "$MI_PROJECT_DIR/Intermediate/Build"
    echo "cleaned Binaries and Intermediate/Build"
  fi

  mkdir -p "$MI_LOGS"
  echo RUNNING > "$st"; date +%s > "$MI_LOGS/build.start"; rm -f "$MI_LOGS/build.end"
  setsid nohup bash "$0" --run "$@" > /dev/null 2>&1 &
  echo "BUILD started at $(git -C "$MI_REPO" rev-parse --short HEAD 2>/dev/null): poll build-status.sh"
}
main "$@"; exit $?
