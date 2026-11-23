#!/bin/bash
# The demo's sound: the event bus recorded in the capture run (<logs>/demo/<name>.json, MIAudio.Record) played
# through the engine's own audio mixer on the imported Sound Waves (MurderInc.Audio.EngineRender with
# -MIAudioStream, AUDIO.md 7), on the SDL dummy driver, placed on the device's clock so it lines up with the frames.
# The live director's seed (7) and the capture's voice options (frequency often, clean language) are used, so the
# same lines are chosen as in the run (the subtitles in the picture).
# Usage: audio.sh start [name] | status    Output: <logs>/demo/<name>.wav (6 channels, 48 kHz; front left/right)
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"
  mi_become_ue4 "$@"
  local dir=$MI_LOGS/demo name=${2:-demo}
  case "$1" in
    --run)
      local log=$dir/$name-audio.log
      [ -s "$dir/$name.json" ] || { echo "no stream $dir/$name.json" > "$log"; exit 1; }
      mi_engine_env
      rm -f "$MI_PROJECT_DIR/Saved/Audio/${name}_audio.wav"
      cd "$MI_ENGINE" || exit 1
      env "UE-LocalDataCachePath=$MI_DDC" SDL_AUDIODRIVER=dummy ./Engine/Binaries/Linux/UnrealEditor-Cmd "$MI_UPROJECT" \
        "-ExecCmds=Automation RunTests MurderInc.Audio.EngineRender;Quit" "-TestExit=Automation Test Queue Empty" \
        "-MIAudioStream=$dir/$name.json" "-MIAudioOut=${name}_audio" -MIAudioSeed=7 -MIAudioFrequency=often -MIAudioClean \
        -unattended -nosplash -NullRHI -nopause -stdout -FullStdOutLogOutput -AudioMixer \
        -ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False \
        "${MI_CACHE_ARGS[@]}" "${MI_EDITOR_ARGS[@]}" > "$log" 2>&1
      echo "exit code $?" >> "$log"
      cp -f "$MI_PROJECT_DIR/Saved/Audio/${name}_audio.wav" "$dir/$name.wav" 2>/dev/null
      exit 0 ;;
    start) setsid nohup bash "$0" --run "$name" > /dev/null 2>&1 & echo "AUDIO started: poll audio.sh status $name" ;;
    status) grep -aE "demo stream|engine render|recording:|Test Completed|exit code|Error" "$dir/$name-audio.log" 2>/dev/null | cut -c1-400 | tail -8; ls -la "$dir/$name.wav" 2>/dev/null ;;
    *) echo "usage: audio.sh start [name] | status [name]" ;;
  esac
}
main "$@"
