#!/bin/bash
# Stop the MURDER INC. demo game on the box (started by start.sh). Only that process: it is matched by its process
# id and by its command line naming the demo build, never by a bare process name (other agents' editors share the
# box). Does not stop the box itself; the box stops on its own after 10 idle minutes.
#
#   bash /project/ue/demo/tools/stop.sh

WORK=/project/ue/demo
GAME=$WORK/build/Linux
p=$(cat "$WORK/game.pid" 2>/dev/null)
if [ -z "$p" ] || ! kill -0 "$p" 2>/dev/null || ! tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -q "$GAME"; then
  echo "DEMO-NOT-RUNNING"; rm -f "$WORK/game.pid"; exit 0
fi
kill "$p"
for _ in $(seq 1 20); do kill -0 "$p" 2>/dev/null || break; sleep 0.5; done
kill -0 "$p" 2>/dev/null && kill -9 "$p"
rm -f "$WORK/game.pid"
echo "DEMO-STOPPED $p"
