#!/bin/bash
# An editor of this clone that only exists while the box is quiet (the box is shared: a gate run or a game of anybody's is
# measured, and an editor beside it spoils the measurement; BOX.md section 8).
#
#   setsid nohup bash quiet-editor.sh [map] > $MI_LOGS/quiet-editor.log 2>&1 < /dev/null &      start the watcher
#   rm $MI_LOGS/WANT                                                                             stop it (and the editor)
#
# It waits for 90 quiet seconds (no lag-test.sh, package-cloud.sh, e3ds-repro.sh run, e3ds-verify.sh, gpu_hog.py and no
# process named MurderInc*: compiles, cooks and test suites of others do not count, only gate runs and games do), starts the
# editor (nice 19) and touches $MI_LOGS/EDITOR-READY. While the editor is up it looks every second: when a gate run or a game
# starts, it stops the editor at once, touches $MI_LOGS/PREEMPTED, removes EDITOR-READY and waits for the next quiet. A script
# that needs the editor checks EDITOR-READY before it starts and PREEMPTED after it ends (a picture run that was preempted is
# run again).
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
  local map=${1:-/Game/Maps/L_Block}
  local dir=$MI_LOGS box; box=$(dirname "${BASH_SOURCE[0]}")
  touch "$dir/WANT"
  while [ -f "$dir/WANT" ]; do
    rm -f "$dir/PREEMPTED" "$dir/EDITOR-READY"
    local quiet=0
    while [ $quiet -lt 90 ] && [ -f "$dir/WANT" ]; do
      if busy; then quiet=0; else quiet=$((quiet + 1)); fi
      sleep 1
    done
    [ -f "$dir/WANT" ] || break
    echo "[$(date +%T)] quiet for 90 s: starting the editor"
    nice -n 19 bash "$box/editor.sh" start "$map" 2>&1 | tail -1
    touch "$dir/EDITOR-READY"
    echo "[$(date +%T)] EDITOR-READY"
    while [ -f "$dir/EDITOR-READY" ] && [ -f "$dir/WANT" ]; do
      if busy; then
        bash "$box/editor.sh" stop 2>&1 | tail -1
        echo "[$(date +%T)] PREEMPTED: a gate run or a game started, the editor is stopped"
        touch "$dir/PREEMPTED"; rm -f "$dir/EDITOR-READY"
        break
      fi
      sleep 1
    done
  done
  bash "$box/editor.sh" stop 2>&1 | tail -1
  echo "[$(date +%T)] quiet-editor ends"
}

busy() {
  ps -eo comm,args | awk '
    $1 ~ /^MurderInc/ {f=1}
    /lag-test\.sh|package-cloud\.sh|e3ds-repro\.sh run|e3ds-verify\.sh|gpu_hog/ && !/awk/ && !/quiet-editor/ && !/quiet\.sh/ {f=1}
    END {exit !f}'
}

main "$@"
