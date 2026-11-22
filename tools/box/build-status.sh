#!/bin/bash
# State of the last build: one status line, then compiler errors only (file:line: message), at most 40.
# Usage: build-status.sh [-w]     -w also lists warnings from the project's own files (at most 20)
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
  local log=$MI_LOGS/build.log st t0 t1 el
  st=$(cat "$MI_LOGS/build.status" 2>/dev/null)
  [ -n "$st" ] || mi_die "BUILD NONE: no build has been started (build.sh)"
  t0=$(cat "$MI_LOGS/build.start" 2>/dev/null || date +%s)
  t1=$(cat "$MI_LOGS/build.end" 2>/dev/null || date +%s)
  el=$(( t1 - t0 ))

  if [ "$st" = RUNNING ]; then
    local pid; pid=$(cat "$MI_LOGS/build.pid" 2>/dev/null)
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null && [ ! -e "$MI_LOGS/build.end" ] && [ "$el" -gt 10 ]; then
      echo "BUILD FAILED after ${el} s: the build process is gone without a result (box restarted or killed). Last lines:"
      tail -5 "$log" 2>/dev/null | cut -c1-240
      return 1
    fi
    echo "BUILD RUNNING ${el} s $(grep -oE '^\[[0-9]+/[0-9]+\]' "$log" 2>/dev/null | tail -1)"
    tail -1 "$log" 2>/dev/null | cut -c1-200
  elif [ "$st" = OK ]; then
    echo "BUILD OK ${el} s $(grep -E 'Total execution time|Target is up to date' "$log" | tail -1 | cut -c1-120)"
  else
    echo "BUILD FAILED ${el} s"
  fi

  # Errors: clang (file:line:col: error: text), UnrealHeaderTool (file(line): Error: text), the C# rules
  # compiler (file(line,col): error CSxxxx: text), the linker and UnrealBuildTool itself.
  # Paths are shortened to start at the project or at Engine/.
  local short='s#[^ :(]*/unreal/MurderInc/##g; s#[^ :(]*/UnrealEngine/Engine/#Engine/#g'
  local errors
  errors=$(grep -aE '(^|[^a-zA-Z])(fatal error|error)( [A-Z]+[0-9]+)?: |\): Error: |^ERROR: |^Unhandled exception|ld\.lld: error|clang\+\+: error|error: linker command failed|UnrealBuildTool.*Exception' "$log" 2>/dev/null \
    | sed -E "$short" | sed -E 's/^(.*):([0-9]+):[0-9]+: (fatal error|error): /\1:\2: /' | awk '!seen[$0]++' | cut -c1-300)
  if [ -n "$errors" ]; then
    echo "errors: $(echo "$errors" | wc -l)"
    echo "$errors" | head -40
  elif [ "$st" = FAILED ]; then
    echo "no compiler error line found; last lines of build.log:"
    tail -15 "$log" | sed -E "$short" | cut -c1-240
  fi

  if [ "$1" = -w ]; then
    local warnings
    warnings=$(grep -aE 'unreal/MurderInc/.*: warning: |unreal/MurderInc/.*\): Warning: ' "$log" 2>/dev/null | sed -E "$short" | awk '!seen[$0]++' | cut -c1-300)
    [ -n "$warnings" ] && { echo "warnings: $(echo "$warnings" | wc -l)"; echo "$warnings" | head -20; }
  fi
  [ "$st" = FAILED ] && return 1
  return 0
}
main "$@"; exit $?
