#!/bin/bash
# Import every WAV under Content/Audio as Sound Wave assets (Content/Python/mi_audio_import.py), headless.
# Usage: audio-import.sh          start (detached; the editor of this clone must be stopped), then poll:
#        audio-import.sh status   last lines of the import status
# Files: <logs>/audio-import.log, <project>/Saved/AudioImport/status.txt (ends with AUDIO-IMPORT-DONE).
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
  mi_become_ue4 "$@"
  local log=$MI_LOGS/audio-import.log status=$MI_PROJECT_DIR/Saved/AudioImport/status.txt
  if [ "$1" = --run ]; then
    mi_engine_env
    rm -f "$status"
    cd "$MI_ENGINE" || exit 1
    env "UE-LocalDataCachePath=$MI_DDC" ./Engine/Binaries/Linux/UnrealEditor-Cmd "$MI_UPROJECT" -run=pythonscript \
      "-script=$MI_PROJECT_DIR/Content/Python/mi_audio_import.py" -unattended -nosplash -NoSound -NullRHI -nopause -stdout \
      "${MI_CACHE_ARGS[@]}" "${MI_EDITOR_ARGS[@]}" > "$log" 2>&1
    echo "exit code $?" >> "$log"
    exit 0
  fi
  if [ "$1" = status ]; then
    if [ -f "$status" ]; then tail -1 "$status"; grep -c '^OK' "$status" | sed 's/^/ok lines: /'; grep '^FAILED' "$status" | head -5
    else echo "AUDIO-IMPORT RUNNING or not started: $(tail -c 300 "$log" 2>/dev/null | tr '\n' ' ')"; fi
    return 0
  fi
  [ -n "$(mi_editor_pid)" ] && mi_die "AUDIO-IMPORT FAILED: this clone's editor is running (editor.sh stop)"
  setsid nohup bash "$0" --run > /dev/null 2>&1 &
  echo "AUDIO-IMPORT started: poll audio-import.sh status"
}
main "$@"; exit $?
