#!/bin/bash
# The animation-pack scratch project's own headless editor, MCP on port 8003 (never the game clones' editors).
# Usage: editor.sh start [map] | stop | status.  The process id is kept in /project/ue/logs/animpack/editor.pid and
# stop kills exactly that process (never pkill: other agents' editors run on the same box).
P=/project/ue/animpack; L=/project/ue/logs/animpack; PORT=8003
if [ "$(id -un)" != ue4 ]; then mkdir -p $L; chown ue4 $L; exec su ue4 -c "$(printf '%q ' bash "$0" "$@")"; fi
mkdir -p $L
pid() { local p; p=$(cat $L/editor.pid 2>/dev/null); [ -n "$p" ] && [ -d /proc/$p ] && tr '\0' ' ' < /proc/$p/cmdline | grep -q AnimPack.uproject && echo $p; }
ping() { MI_MCP_URL=http://127.0.0.1:$PORT/mcp timeout 20 python3 $P/scripts/mi_mcp.py py - <<< '1+1' 2>/dev/null | grep -q 2; }
case "${1:-status}" in
  start)
    [ -n "$(pid)" ] && { echo "EDITOR already running pid $(pid)"; exit 0; }
    ini=$P/Saved/Config/LinuxEditor/EditorPerProjectUserSettings.ini; mkdir -p "$(dirname $ini)"
    grep -q ModelContextProtocolSettings $ini 2>/dev/null || printf '\n[/Script/ModelContextProtocol.ModelContextProtocolSettings]\nbAutoStartServer=True\n' >> $ini
    shift
    setsid nohup /project/ue/bin/run-editor.sh $P/AnimPack.uproject "$@" '-ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1' \
      -ModelContextProtocolPort=$PORT -RenderOffscreen -unattended -nosplash -NoSound > $L/editor.log 2>&1 < /dev/null &
    echo $! > $L/editor.pid; echo "EDITOR STARTED pid $!" ;;
  stop)
    p=$(pid); [ -z "$p" ] && { echo "EDITOR not running"; exit 0; }
    kill -TERM $p; for i in $(seq 1 20); do [ -d /proc/$p ] || break; sleep 1; done
    [ -d /proc/$p ] && kill -KILL $p; echo "EDITOR STOPPED pid $p" ;;
  status)
    p=$(pid); [ -z "$p" ] && { echo "EDITOR not running"; tail -3 $L/editor.log 2>/dev/null | cut -c1-200; exit 1; }
    if ping; then echo "EDITOR UP pid $p (MCP $PORT)"; else echo "EDITOR STARTING pid $p"; tail -1 $L/editor.log | cut -c1-200; fi ;;
esac
