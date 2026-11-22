#!/bin/bash
# The headless editor on this clone's MurderInc project, with its MCP server on http://127.0.0.1:<port>/mcp
# (8000 for /project/ue/repo, 8001 for other clones: MI_MCP_PORT in lib.sh).
# Usage: editor.sh start [extra editor arguments, for example /Game/Maps/L_Bootstrap]
#        editor.sh stop | restart | status
# Windows do not work on this box (the editor aborts when it opens one), so it always runs with -RenderOffscreen.
# Log: /project/ue/logs/editor.log (the previous one is kept as editor.prev.log).
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
  mi_become_ue4 "$@"
  local cmd=${1:-status}; shift
  case "$cmd" in
    start)   editor_start "$@" ;;
    stop)    editor_stop ;;
    restart) editor_stop; editor_start "$@" ;;
    status)  editor_status ;;
    *)       mi_die "usage: editor.sh start [editor args] | stop | restart | status" ;;
  esac
}

# The MCP server starts on its own only when the per-user editor settings say so. That file lives in Saved/
# (not committed), so it is written here. run-editor.sh also passes -ModelContextProtocolStartServer.
ensure_mcp_autostart() {
  local ini=$MI_PROJECT_DIR/Saved/Config/LinuxEditor/EditorPerProjectUserSettings.ini
  mkdir -p "$(dirname "$ini")"
  if ! grep -q '^\[/Script/ModelContextProtocol.ModelContextProtocolSettings\]' "$ini" 2>/dev/null; then
    printf '\n[/Script/ModelContextProtocol.ModelContextProtocolSettings]\nbAutoStartServer=True\n' >> "$ini"
  fi
}

editor_start() {
  local pid; pid=$(mi_editor_pid)
  if [ -n "$pid" ]; then echo "EDITOR already running, pid $pid"; editor_status; return 0; fi
  [ -f "$MI_UPROJECT" ] || mi_die "EDITOR FAILED: $MI_UPROJECT is missing (run sync.sh)"
  [ -x "$MI_RUN_EDITOR" ] || mi_die "EDITOR FAILED: $MI_RUN_EDITOR is missing"
  if [ ! -f "$MI_PROJECT_DIR/Binaries/Linux/libUnrealEditor-MurderInc.so" ]; then
    mi_die "EDITOR FAILED: the game module is not built (run build.sh and wait for build-status.sh to say OK)"
  fi
  if [ "$(cat "$MI_LOGS/build.status" 2>/dev/null)" = RUNNING ]; then mi_die "EDITOR FAILED: a build is running (build-status.sh)"; fi
  ensure_mcp_autostart
  [ -f "$MI_LOGS/editor.log" ] && mv -f "$MI_LOGS/editor.log" "$MI_LOGS/editor.prev.log"
  date +%s > "$MI_LOGS/editor.start"
  setsid nohup "$MI_RUN_EDITOR" "$MI_UPROJECT" "$@" "${MI_EDITOR_ARGS[@]}" "-ModelContextProtocolPort=$MI_MCP_PORT" -RenderOffscreen -unattended -nosplash -NoSound > "$MI_LOGS/editor.log" 2>&1 &
  local i
  for i in $(seq 1 17); do
    sleep 2
    if [ -z "$(mi_editor_pid)" ]; then
      echo "EDITOR FAILED: the process exited during start. Last lines of editor.log:"
      editor_fatal; tail -6 "$MI_LOGS/editor.log" | cut -c1-240
      return 1
    fi
    if mi_mcp ping >/dev/null 2>&1; then
      echo "EDITOR UP pid $(mi_editor_pid), MCP answering after $(( $(date +%s) - $(cat "$MI_LOGS/editor.start") )) s"
      return 0
    fi
  done
  echo "EDITOR STARTING pid $(mi_editor_pid): MCP is not answering yet (a first start compiles shaders); poll editor.sh status"
  tail -1 "$MI_LOGS/editor.log" | cut -c1-200
}

editor_stop() {
  local pid; pid=$(mi_editor_pid)
  if [ -z "$pid" ]; then echo "EDITOR not running"; return 0; fi
  # Only this clone's editor: another clone's editor may be running on the same box.
  kill -TERM $(mi_pids_of UnrealEditor) 2>/dev/null
  local i
  for i in $(seq 1 15); do [ -z "$(mi_editor_pid)" ] && break; sleep 1; done
  if [ -n "$(mi_editor_pid)" ]; then kill -KILL $(mi_pids_of UnrealEditor) 2>/dev/null; sleep 1; fi
  [ -z "$(pgrep -x UnrealEditor)" ] && pkill -x CrashReportClie 2>/dev/null
  echo "EDITOR STOPPED (was pid $pid)"
}

editor_fatal() {
  grep -aE 'Fatal error|Assertion failed|Unhandled Exception|Segmentation fault|LogCore: Error: appError|=== Critical error' "$MI_LOGS/editor.log" 2>/dev/null | head -5 | cut -c1-240
}

editor_status() {
  local pid; pid=$(mi_editor_pid)
  if [ -z "$pid" ]; then
    echo "EDITOR STOPPED"
    editor_fatal
    return 1
  fi
  local up=$(( $(date +%s) - $(cat "$MI_LOGS/editor.start" 2>/dev/null || date +%s) ))
  if mi_mcp ping >/dev/null 2>&1; then
    echo "EDITOR RUNNING pid $pid, up ${up} s, MCP ok, level $(mi_mcp level 2>/dev/null | head -1)"
  else
    echo "EDITOR RUNNING pid $pid, up ${up} s, MCP not answering"
    tail -1 "$MI_LOGS/editor.log" | cut -c1-200
  fi
  echo "log: $(grep -ac 'Error: ' "$MI_LOGS/editor.log") error lines, $(grep -ac 'Warning: ' "$MI_LOGS/editor.log") warning lines, shader jobs: $(grep -aoE 'Shaders left to compile [0-9]+|[0-9,]+ jobs? remaining' "$MI_LOGS/editor.log" | tail -1)"
}

main "$@"; exit $?
