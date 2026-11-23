#!/bin/bash
# MurderInc.Audio.EngineRender with an audio device: like test.sh, but without -NoSound and with SDL's dummy audio
# driver (the box has no sound card), so the engine's audio mixer runs and records its master output to
# <project>/Saved/Audio/engine_render.wav. Usage: audio-engine-render.sh [status]
# Files: <logs>/audio-render.log, <logs>/audio-render-report/index.json.
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
  mi_become_ue4 "$@"
  local log=$MI_LOGS/audio-render.log report=$MI_LOGS/audio-render-report
  if [ "$1" = --run ]; then
    mi_engine_env
    rm -rf "$report"
    cd "$MI_ENGINE" || exit 1
    env "UE-LocalDataCachePath=$MI_DDC" SDL_AUDIODRIVER=dummy ./Engine/Binaries/Linux/UnrealEditor-Cmd "$MI_UPROJECT" \
      "-ExecCmds=Automation RunTests MurderInc.Audio.EngineRender;Quit" "-TestExit=Automation Test Queue Empty" "-ReportExportPath=$report" \
      -unattended -nosplash -NullRHI -nopause -stdout -FullStdOutLogOutput -AudioMixer "${MI_CACHE_ARGS[@]}" "${MI_EDITOR_ARGS[@]}" > "$log" 2>&1
    echo "exit code $?" >> "$log"
    exit 0
  fi
  if [ "$1" = status ]; then
    grep -E "engine render|no audio device|Test Completed|exit code|LogAudioMixer.*(Error|Warning)|Audio Device|AudioMixerPlatformSDL" "$log" 2>/dev/null | cut -c1-300 | tail -12
    return 0
  fi
  setsid nohup bash "$0" --run > /dev/null 2>&1 &
  echo "AUDIO-RENDER started: poll audio-engine-render.sh status (about a minute)"
}
main "$@"; exit $?
