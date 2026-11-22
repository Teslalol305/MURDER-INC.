#!/bin/bash
# Bring the box mirror (/project/ue/repo) to the tip of the branch.
# Tracked files are overwritten; untracked files survive (Binaries, Intermediate, Saved, DerivedDataCache and the
# generated .uasset/.umap content are ignored by git and there is no "git clean" here, on purpose).
# Usage: sync.sh
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
    return 0
  fi
  local files code
  files=$(git diff --name-only "$old" "$new" | wc -l)
  code=$(git diff --name-only "$old" "$new" | grep -cE '^unreal/MurderInc/(Source/|MurderInc\.uproject$)')
  echo "SYNC OK ${old:0:7} -> ${new:0:7}, $files files changed, $code of them C++ or project files ($(git log -1 --format=%s | cut -c1-70))"
  if [ "$code" -gt 0 ]; then echo "next: build.sh"; fi
}
main "$@"; exit $?
