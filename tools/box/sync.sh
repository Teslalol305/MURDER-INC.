#!/bin/bash
# Bring the box mirror (/project/ue/repo) to the tip of the branch.
# Tracked files are overwritten; untracked files survive (Binaries, Intermediate, Saved, DerivedDataCache and the
# generated .uasset/.umap content are ignored by git and there is no "git clean" here, on purpose).
# It also looks at the sounds: when a WAV under Content/Audio has no Sound Wave asset, or one older than itself (a new
# clone, a new box, a recording that replaced a placeholder), it starts the import (audio-import.sh), or says what
# stands in its way. A clone without the assets plays nothing and packages a silent game.
# Usage: sync.sh
audio() {  # $1: 1 when this sync brought C++ changes (the import runs the editor, which needs the module built first)
  local n missing stale
  n=$(mi_audio_stale); missing=${n% *}; stale=${n#* }
  [ "$missing" = 0 ] && [ "$stale" = 0 ] && return 0
  local what="$missing sound(s) without a Sound Wave asset, $stale with an asset older than the WAV" p
  for p in $(pgrep -x UnrealEditor-Cm); do   # an import that an earlier sync started (the name is cut to 15 characters)
    if tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -qF "$MI_PROJECT_DIR/Content/Python/mi_audio_import.py"; then
      echo "AUDIO: $what: the import is running (audio-import.sh status)"; return 0
    fi
  done
  if [ ! -d "$MI_PROJECT_DIR/Content/Audio/Web" ]; then
    echo "AUDIO: $what, and no Content/Audio/Web (the web game's sounds are not in git: node tools/ue-export/audio.mjs, or copy the folder from another clone); then audio-import.sh"
  elif [ "$1" = 1 ] || [ ! -f "$MI_PROJECT_DIR/Binaries/Linux/libUnrealEditor-MurderInc.so" ] || [ "$(cat "$MI_LOGS/build.status" 2>/dev/null)" = RUNNING ]; then
    echo "AUDIO: $what. next: build.sh, then audio-import.sh (poll audio-import.sh status until AUDIO-IMPORT-DONE failed=0)"
  elif [ -n "$(mi_editor_pid)" ]; then
    echo "AUDIO: $what. This clone's editor is running: editor.sh stop, then audio-import.sh"
  else
    echo "AUDIO: $what: $(bash "$MI_BOX_DIR/audio-import.sh")"
  fi
}

main() {
  . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
  mi_become_ue4 "$@"
  cd "$MI_REPO" || mi_die "SYNC FAILED: no mirror at $MI_REPO (git clone --branch $MI_BRANCH --single-branch <url> $MI_REPO as ue4)"
  local old new out
  old=$(git rev-parse HEAD)
  if ! out=$(timeout 40 git fetch --quiet origin "+refs/heads/$MI_BRANCH:refs/remotes/origin/$MI_BRANCH" 2>&1); then
    mi_die "SYNC FAILED fetch: $(echo "$out" | tail -2 | tr '\n' ' ')"
  fi
  if ! out=$(git reset --quiet --hard "origin/$MI_BRANCH" 2>&1); then
    mi_die "SYNC FAILED reset: $(echo "$out" | tail -2 | tr '\n' ' ')"
  fi
  new=$(git rev-parse HEAD)
  if [ "$old" = "$new" ]; then
    echo "SYNC OK already at ${new:0:7} ($(git log -1 --format=%s | cut -c1-70))"
    audio 0
    return 0
  fi
  local files code
  files=$(git diff --name-only "$old" "$new" | wc -l)
  code=$(git diff --name-only "$old" "$new" | grep -cE '^unreal/MurderInc/(Source/|MurderInc\.uproject$)')
  echo "SYNC OK ${old:0:7} -> ${new:0:7}, $files files changed, $code of them C++ or project files ($(git log -1 --format=%s | cut -c1-70))"
  if [ "$code" -gt 0 ]; then echo "next: build.sh"; fi
  audio "$([ "$code" -gt 0 ] && echo 1 || echo 0)"
}
main "$@"; exit $?
