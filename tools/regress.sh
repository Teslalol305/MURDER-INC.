#!/usr/bin/env bash
# Full-build regression: every module's scripted scenario against one build, one browser at a time.
#   node build.mjs --dev --out=dist/dev-all.html && tools/regress.sh [dist/dev-all.html] [name ...]
# Each full-build page needs about 3 GB in software GL, so the runs are strictly sequential.
# Logs land in shots/regress/<name>.log; the summary is printed at the end and the exit code is the number of failures.

set -u
cd "$(dirname "$0")/.."
BUILD="${1:-dist/dev-all.html}"
shift || true
ONLY=("$@")
OUT=shots/regress
mkdir -p "$OUT"

# name | size | params | env | scenario | timeout
RUNS=(
  "flow-story|960x540|q=test&noaudio=1|FLOW_NOSHOTS=1|flow-story|900"
  "story-bot|640x360|autostart=1&q=test&noaudio=1&nohud=1|BOT_DIFFICULTY=hustler BOT_LIMIT=400 BOT_MAX_DEATHS=0|story-bot|900"
  "flow-mission|960x540|q=test&noaudio=1&scenes=0|FLOW_NOSHOTS=1|flow-mission|900"
  "flow-death|960x540|q=test&autostart=1&noaudio=1||flow-death|600"
  "flow-pause|960x540|q=test&noaudio=1&scenes=0||flow-pause|500"
  "flow-holdout|960x540|q=test&autostart=1&mode=holdout&noaudio=1||flow-holdout|900"
  "flow-difficulty|960x540|q=test&autostart=1&noaudio=1||flow-difficulty|600"
  "enemies-fight|800x450|autostart=1&q=test&god=1&noaudio=1&nohud=1|ENEMIES_SOAK=2000|enemies-fight|900"
  "weapon-assist|960x540|autostart=1&q=test&god=1&noaudio=1|ASSIST_NOSHOTS=1|weapon-assist|300"
  "weapon-rocket|960x540|autostart=1&q=test&god=1&noaudio=1|ROCKET_NOSHOTS=1|weapon-rocket|300"
  "input-player-full|960x540|autostart=1&q=test&noaudio=1||input-player-full|700"
  "input-player-hud|844x390|autostart=1&q=test&noaudio=1&god=1||input-player-hud|700"
  "level-walk|960x540|autostart=1&q=test&god=1&noaudio=1||level-walk|900"
  "ui-nav|960x540|q=test&noaudio=1&god=1||ui-nav|500"
  "audio-full|640x360|autostart=1&q=test&god=1||audio-full|700"
  "atmos-check|960x540|shot=1&nohud=1||atmos-check|500"
  "flow-fixes|960x540|q=test&scenes=0|FLOW_NOSHOTS=1|flow-fixes|900"
  "ui-layout|1280x720|q=test&noaudio=1&god=1|UI_NOSHOTS=1|ui-layout|700"
  "ui-layout-touch|844x390|q=test&noaudio=1&god=1|UI_TOUCH=1 UI_NOSHOTS=1|ui-layout|700"
  "ui-layout-portrait|390x844|q=test&noaudio=1&god=1|UI_TOUCH=1 UI_NOSHOTS=1|ui-layout|700"
)

fails=0
summary=()
for run in "${RUNS[@]}"; do
  IFS='|' read -r name size params envs scenario timeout <<<"$run"
  if [ ${#ONLY[@]} -gt 0 ] && [[ ! " ${ONLY[*]} " =~ " ${name} " ]]; then continue; fi
  start=$(date +%s)
  env $envs node tools/shot.cjs "$BUILD" --size "$size" --params "$params" \
    --scenario "tools/scenarios/$scenario.cjs" --timeout "$timeout" >"$OUT/$name.log" 2>&1
  code=$?
  secs=$(( $(date +%s) - start ))
  if [ $code -eq 0 ]; then summary+=("ok    $name (${secs}s)"); else summary+=("FAIL  $name (exit $code, ${secs}s)"); fails=$((fails + 1)); fi
  echo "${summary[${#summary[@]}-1]}" # (not [-1]: macOS ships bash 3.2)
done
echo "---"
printf '%s\n' "${summary[@]}"
exit $fails
