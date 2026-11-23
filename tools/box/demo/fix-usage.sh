#!/bin/bash
# Sets the material usage flags a standalone game needs (fix_usage.py) in this clone's content. Editor stopped.
. "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"
mi_become_ue4 "$@"
mi_engine_env
cd "$MI_ENGINE" || exit 1
env "UE-LocalDataCachePath=$MI_DDC" ./Engine/Binaries/Linux/UnrealEditor-Cmd "$MI_UPROJECT" -run=pythonscript "-script=$MI_BOX_DIR/demo/fix_usage.py" \
  -unattended -nosplash -NullRHI -nopause -stdout -FullStdOutLogOutput "${MI_CACHE_ARGS[@]}" "${MI_EDITOR_ARGS[@]}" > "$MI_LOGS/demo/fix-usage.log" 2>&1
echo "exit code $?" >> "$MI_LOGS/demo/fix-usage.log"
grep -a "fix_usage\|exit code" "$MI_LOGS/demo/fix-usage.log" | cut -c1-200
