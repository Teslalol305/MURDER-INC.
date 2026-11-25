#!/bin/bash
# Import the arms, the Goons, the NINE, the Goon SMG, the Buzzard, the CHOPPER's finish and the effect materials into
# THIS clone's game project, headless (tools/box/fp/mi_fp_import.py; inputs from fp-art.sh unpack in /project/ue/fp-in).
# Usage (root or ue4; this clone's editor stopped): import-chars.sh [arms|goons|guns|fx|all] ...
#        import-chars.sh r4 [probe|guns|rattler|parts|sockets|all]   the weapons of round 4 (our own five guns, their
#                           magazines and the parts kit: tools/box/fp/mi_guns_r4.py; inputs from MI_FP_IN, default
#                           /project/ue/fp-in-guns)
# Detached; log $MI_LOGS/fp-import.log, its last line is MI-DONE; `import-chars.sh status` prints the result lines
# (`import-chars.sh probe-lines` prints the MI-PROBE lines of the last probe).
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"
  mi_become_ue4 "$@"
  local log=$MI_LOGS/fp-import.log
  if [ "${1:-}" = status ]; then
    grep -E "MI-FP |MI-R4 |MI-DONE|Error: .*Python|Traceback" "$log" | cut -c1-300 | tail -8
    [ -n "$(mi_pids_of UnrealEditor-Cm)" ] && echo "RUNNING pid $(mi_pids_of UnrealEditor-Cm | head -1)"
    return 0
  fi
  if [ "${1:-}" = probe-lines ]; then grep -a "MI-PROBE" "$log" | sed 's/^.*MI-PROBE/MI-PROBE/' | cut -c1-400; return 0; fi
  local script=mi_fp_import.py
  if [ "${1:-}" = r4 ]; then script=mi_guns_r4.py; shift; fi
  [ -z "$(mi_editor_pid)" ] || mi_die "IMPORT FAILED: this clone's editor is running (editor.sh stop)"
  mi_engine_env
  cd "$MI_ENGINE" || exit 1
  setsid nohup env 'UE-LocalDataCachePath=/project/ue/ddc' ./Engine/Binaries/Linux/UnrealEditor-Cmd "$MI_UPROJECT" \
    -run=pythonscript "-script=$MI_BOX_DIR/fp/$script ${*:-all}" -unattended -nosplash -NoSound -stdout \
    -FullStdOutLogOutput -RenderOffscreen -AllowCommandletRendering "${MI_CACHE_ARGS[@]}" "${MI_EDITOR_ARGS[@]}" \
    > "$log" 2>&1 < /dev/null &
  echo "IMPORT STARTED pid $! (import-chars.sh status; MI-DONE at the end of $log)"
}
main "$@"
