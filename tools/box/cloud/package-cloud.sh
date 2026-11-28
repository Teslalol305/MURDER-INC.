#!/bin/bash
# The cloud (Pixel Streaming 2) package of MURDER INC., for Eagle 3D Streaming (docs/LAUNCH.md), in one command:
#
#   bash /project/ue/cloud/src/tools/box/cloud/package-cloud.sh all     (as root on the box; detached, poll status)
#
# Steps (each can be run alone):
#   src        fetch the branch into /project/ue/cloud/src (sparse clone: unreal/MurderInc, tools/box)
#   refresh    copy the branch's Source, Config and .uproject into the release copy /project/ue/repo-release, and its
#              tools/box (so build.sh, test.sh and the importers run there against the release copy itself)
#   editor     build the release copy's editor target (MurderIncEditor) from that Source, nice 19, at most MI_JOBS (6)
#              compile jobs. The cooker is the editor: it must load a game module built from the same commit as the
#              packaged games (cooked packages are written with the cooker's class layouts). Until version 3b the
#              release copy took the gameplay clone's editor module instead, which was right only while that clone
#              stood at the packaged commit
#   content    copy the gameplay clone's Content into the release copy, only if no editor has that clone open
#              (else the release copy keeps the Content of its last copy, and the step says so). It fails when a
#              sound of the gameplay clone has no Sound Wave asset or an older one than its WAV: the assets are
#              generated content (tools/box/audio-import.sh there), and a package without them is silent. The folders
#              the weapons import owns (Content/Weapons/Chopper, Nine, Shorty, Stretch, Rattler, Parts, Casings) are
#              only filled where the release copy lacks a file (cp --update=none): never over its own import
#   fx         the effect materials (Content/FX: flash, smoke, tracer, the decal material MD_FX_Mark with the blood pool
#              of the death pass, brass, debris) made again in the release copy by the commit's
#              tools/box/fp/mi_fp_import.py fx, headless, as import-chars.sh fx does in a clone. content copies the
#              gameplay clone's Content/FX, whose MD_FX_Mark may be older than the commit (a material made before the
#              death pass draws the pool under a body as a spatter), so it runs after content every time; it fails
#              when MD_FX_Mark has no pool branch afterwards
#   weapons    the weapons of round 4 (the five own guns, their magazines, the brass, the parts kit) imported into
#              the release copy by the commit's tools/box/fp/mi_guns_r4.py from the art in MI_FP_IN
#              (/project/ue/fp-in-guns: fp-art.sh unpack; read only), headless, as import-chars.sh r4 does in a clone.
#              Skipped when the script, its helpers and the art are the same as at the last import into the release
#              copy (Content/Weapons/.r4-import; MI_WEAPONS_FORCE=1 imports anyway). A commit without the script
#              skips the step
#   overlay    the packaging settings, on the release copy only (start map L_Block, folders loaded by path, fonts,
#              no Zen store): the same as tools/box/demo/package.sh
#              Also for the stream only: the SM5 shaders as well as SM6 (a server whose driver fails Unreal 5.9's SM6
#              Vulkan check falls back to SM5 instead of quitting at start), and the engine's crash handler writes
#              Saved/Crashes/<crash>/ (call stack) even without a display (no crash reporter is packaged: nothing is
#              sent anywhere)
#   usage      the release copy's asset step (cloud/cloud_assets.py): the material usage flags the cooked game needs
#              (demo/fix_usage.py: without them the cooked game draws the CHOPPER pack rifle, the Goons' guns, Rule's
#              silver, the Buzzard's tracer material and the art masters on instanced meshes with the default grey
#              material; the editor sets the flags on the fly, so play in editor never shows it), and the six interior
#              cube maps stored as BC6H (384 MB of graphics memory down to 48 MB)
#   package <Development|Shipping>   BuildCookRun Linux into /project/ue/cloud/build-<config> (Shipping skips the
#              cook when a cook exists)
#   sounds     is every Sound Wave the game's data names in the pak list of build-Shipping and build-Development
#              (cloud/pak_sounds.py)? "package" and "zip" ask the same and stop when one is missing: versions 1, 2
#              and 3a were packaged without a single sound and nothing said so
#   guns       the same for the guns: is every asset under /Game/Weapons that the game's data names (the guns, their
#              magazines, the brass, the parts) in the pak list of both builds (cloud/pak_weapons.py)? "package" and
#              "zip" ask it too and stop when one is missing
#   zip        /project/ue/cloud/MurderInc-E3DS.zip (or MI_ZIP) from build-Shipping: the launcher cloud/MurderInc.sh at
#              the root (E3DS app name = script name = MurderInc; it logs to MurderInc/Saved/Logs), BUILD.txt (the
#              commit), the Development game beside the Shipping one (launch option -MIDev=<key>; the key is a new
#              random word in MIDEV.key at the zip's root, copied to /project/ue/cloud/MurderInc-E3DS.devkey (the zip's
#              name with .devkey) for the release report: a visitor can add launch options to a stream link and must
#              not be able to start the Development game, which has the debug switches; never commit the key), no
#              *.debug / *.sym (kept on the box in /project/ue/cloud/symbols/<commit>/ to read crash call stacks),
#              plus its sha256
#   parts      the zip in parts of 240 MiB (the storage takes at most about 250 MB a file) in /project/ue/cloud/parts,
#              named MurderInc-E3DS-part<k>-of-<n>.zip, with parts.sha256 (MI_TAG=v3a in the environment names them
#              MurderInc-E3DS-v3a-part<k>-of-<n>.zip: the names the owner sees in the storage)
#   all        src, refresh, editor, content, weapons, overlay, usage, package Development, package Shipping, zip,
#              parts (detached; log in /project/ue/cloud/package.log)
#   status     the step running or the result, and the last log lines
#
# MI_COMMIT=<40 hex digits> in the environment packages that commit of the branch instead of its head (src fetches
# it; BUILD.txt names it). For a release while other work is pushed to the same branch: the head may by then hold
# game code that is not tested or gated yet. The commit must be on the pushed branch.
# MI_ZIP=<file> writes the zip there instead of /project/ue/cloud/MurderInc-E3DS.zip, and MI_PARTS=0 leaves out the
# parts: a trial package that must not take the release's names (MI_ZIP=/project/ue/cloud/v6trial.zip MI_PARTS=0).
# MI_JOBS: the most compile jobs at once (default 6: the box is shared). Start it with nice -n 19 on a shared box.
# MI_REL=<folder> and MI_GP=<folder>: the release copy and the clone whose generated Content it takes, instead of
# /project/ue/repo-release and /project/ue/repo-gameplay (a lane's own package beside the release engineer's).
# The pipeline cache (docs/unreal/SMOOTH.md H3, H4): a commit with unreal/MurderInc/Build/Linux/PipelineCaches/*.spc
# (tools/box/cloud/pso-cache.sh) has it cooked into both games; "package" and "zip" stop when it is not in the pak
# list. "package Development" keeps the cook's stable shader keys in $C/pso-keys (what pso-cache.sh expand reads).
#
# The package holds pack, Epic and likeness content: it stays on the box and goes only to the owner's private
# Higgsfield storage (docs/LAUNCH.md); it is never committed.

C=${MI_CLOUD:-/project/ue/cloud}   # (another folder only to try a step on a copy)
RELROOT=${MI_REL:-/project/ue/repo-release}   # (MI_REL / MI_GP: a lane's own release copy and content clone)
REL=$RELROOT/unreal/MurderInc
GP=${MI_GP:-/project/ue/repo-gameplay}/unreal/MurderInc
ENGINE=/project/ue/UnrealEngine
BRANCH=${MI_BRANCH:-claude/tender-albattani-5q78qr}
COMMIT=${MI_COMMIT:-}              # this commit of the branch instead of its head
ZIP=${MI_ZIP:-$C/MurderInc-E3DS.zip}
FPIN=${MI_FP_IN:-/project/ue/fp-in-guns}
JOBS=${MI_JOBS:-6}
# The folders under Content/Weapons that the weapons import of round 4 writes (mi_guns_r4.py).
R4_FOLDERS="Chopper Nine Shorty Stretch Rattler Parts Casings"
LOG=$C/package.log
ST=$C/package.status
ME=$(readlink -f "$0")
say() { echo "[$(date +%H:%M:%S)] $*"; }
CACHE_ARGS="'-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal)' -ini:Engine:[Zen]:AutoLaunch=false -ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1"

as_ue4() { su ue4 -c "$(printf '%q ' "$@")"; }

ue4_home() {  # the engine's user, its home and its Epic settings folder on persistent storage (as lib.sh does)
  export HOME=/home/ue4
  mkdir -p /home/ue4/.config; [ -L /home/ue4/.config/Epic ] || ln -sfn /project/ue/home/Epic /home/ue4/.config/Epic
  chown -h ue4 /home/ue4/.config/Epic 2>/dev/null
}

src() {
  local url; url=$(as_ue4 git -C /project/ue/repo remote get-url origin 2>/dev/null)
  [ -n "$url" ] || { say "no origin url in /project/ue/repo"; return 1; }
  if [ -n "$COMMIT" ] && ! [[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]]; then say "SRC FAILED: MI_COMMIT must be the 40 hex digits of a commit, not '$COMMIT'"; return 1; fi
  if [ ! -d "$C/src/.git" ]; then
    rm -rf "$C/src" && mkdir -p "$C" && chown ue4 "$C"
    as_ue4 git clone -q --depth 1 --filter=blob:none --sparse -b "$BRANCH" "$url" "$C/src" || return 1
    as_ue4 git -C "$C/src" sparse-checkout set unreal/MurderInc tools/box || return 1
  fi
  # The branch's head, or the one commit asked for (MI_COMMIT).
  as_ue4 git -C "$C/src" fetch -q --depth 1 origin "${COMMIT:-$BRANCH}" && as_ue4 git -C "$C/src" reset -q --hard FETCH_HEAD || return 1
  # git refuses a repository owned by another user (ue4) when run as root: read it as ue4.
  as_ue4 git -C "$C/src" rev-parse HEAD > "$C/src.commit" || return 1
  if [ -n "$COMMIT" ] && [ "$(cat "$C/src.commit")" != "$COMMIT" ]; then say "SRC FAILED: asked for commit $COMMIT, the clone is at $(cat "$C/src.commit")"; return 1; fi
  say "SRC OK at $(as_ue4 git -C "$C/src" log --oneline -1)${COMMIT:+ (MI_COMMIT: this commit, not the head of the branch)}"
}

refresh() {
  local S=$C/src/unreal/MurderInc
  [ -f "$S/MurderInc.uproject" ] || { say "run src first"; return 1; }
  mkdir -p "$REL"
  rm -rf "$REL/Source" "$REL/Config"
  cp -a "$S/Source" "$S/Config" "$S/MurderInc.uproject" "$REL/" || return 1
  # The data the game reads by path comes from the branch too.
  mkdir -p "$REL/Content" && cp -a "$S/Content/Data" "$S/Content/Python" "$REL/Content/" || return 1
  # The recorded pipeline cache (Build/Linux/PipelineCaches/*.spc, tools/box/cloud/pso-cache.sh): the cook turns it into
  # the package's Content/PipelineCaches/Linux/MurderInc_SF_VULKAN_SM5.stable.upipelinecache (SMOOTH.md H3, H4).
  rm -rf "$REL/Build/Linux/PipelineCaches"
  if [ -d "$S/Build/Linux/PipelineCaches" ]; then
    mkdir -p "$REL/Build/Linux" && cp -a "$S/Build/Linux/PipelineCaches" "$REL/Build/Linux/" && chown -R ue4 "$REL/Build" || return 1
  fi
  chown -R ue4 "$REL/Source" "$REL/Config" "$REL/MurderInc.uproject" "$REL/Content/Data" "$REL/Content/Python"
  # The box scripts of the same commit, so that build.sh, test.sh and the importers can be run in the release copy
  # (lib.sh takes the clone from the script's own place: /project/ue/repo-release, logs in /project/ue/logs/repo-release).
  rm -rf "$RELROOT/tools/box" && mkdir -p "$RELROOT/tools" && cp -a "$C/src/tools/box" "$RELROOT/tools/" || return 1
  chown -R ue4 "$RELROOT/tools"
  say "REFRESH OK: Source, Config, Data and tools/box from the branch"
}

editor() {  # the release copy's editor target from its own Source: the module the cooker and the importers load
  [ -f "$REL/MurderInc.uproject" ] && [ -d "$REL/Source" ] || { say "run refresh first"; return 1; }
  ue4_home
  say "EDITOR build of the release copy (MurderIncEditor, nice 19, at most $JOBS jobs)"
  if su ue4 -c "cd $ENGINE && env HOME=/home/ue4 nice -n 19 ./Engine/Build/BatchFiles/Linux/Build.sh MurderIncEditor Linux Development \
      -project=$REL/MurderInc.uproject -WaitMutex -NoUBA -MaxParallelActions=$JOBS" > "$C/editor-build.log" 2>&1; then
    say "EDITOR OK: $(grep -a -E 'Total execution time|Result: ' "$C/editor-build.log" | tail -1 | cut -c1-120) (log $C/editor-build.log)"
  else
    say "EDITOR FAILED (log $C/editor-build.log): $(grep -a -E ' error[ :]|Error:' "$C/editor-build.log" | head -3 | cut -c1-240 | tr '\n' ' ')"
    return 1
  fi
}

content() {
  local busy
  busy=$(ps -eo args | grep -F -- "${GP%/unreal/MurderInc}/" | grep -E '^[^ ]*UnrealEditor' | head -1)
  if [ -n "$busy" ]; then
    say "CONTENT KEPT: an editor has the gameplay clone open; the release copy keeps its last Content ($(du -sh "$REL/Content" 2>/dev/null | cut -f1))"
    return 0
  fi
  [ -d "$GP/Content" ] || { say "no gameplay clone Content"; return 1; }
  # The sounds: every WAV of the gameplay clone needs its Sound Wave asset, not older than the WAV.
  local w a missing=0 stale=0
  while IFS= read -r w; do
    a=${w%.wav}.uasset
    if [ ! -f "$a" ]; then missing=$((missing + 1)); elif [ "$w" -nt "$a" ]; then stale=$((stale + 1)); fi
  done < <(find "$GP/Content/Audio" -name '*.wav' ! -name 'IR_*' 2>/dev/null)
  if [ "$missing" != 0 ] || [ "$stale" != 0 ] || [ ! -d "$GP/Content/Audio" ]; then
    say "CONTENT FAILED: the gameplay clone has $missing sound(s) without a Sound Wave asset and $stale with an asset older than its WAV$([ -d "$GP/Content/Audio" ] || echo ' (no Content/Audio at all)'): the package would be silent there. Run 'bash tools/box/audio-import.sh' in /project/ue/repo-gameplay (its editor stopped), poll 'audio-import.sh status' until AUDIO-IMPORT-DONE failed=0, then package again"
    return 1
  fi
  # Content (not Data or Python: those come from the branch). Not the editor module (Binaries): the release copy builds
  # its own (editor). Not over the weapons import either: the folders it owns only get the files the release copy lacks.
  local own=() d
  for d in $R4_FOLDERS; do own+=("--exclude=Content/Weapons/$d"); done
  (cd "$GP" && tar -cf - --exclude=Content/Data --exclude=Content/Python "${own[@]}" Content) \
    | tar --no-same-owner -C "$REL" -xf - || return 1
  for d in $R4_FOLDERS; do
    [ -d "$GP/Content/Weapons/$d" ] || continue
    mkdir -p "$REL/Content/Weapons/$d" && cp -a --reflink=auto --update=none "$GP/Content/Weapons/$d/." "$REL/Content/Weapons/$d/" || return 1
  done
  chown -R ue4 "$REL/Content"
  say "CONTENT OK: $(du -sh "$REL/Content" | cut -f1) from the gameplay clone (Content/Weapons/{${R4_FOLDERS// /,}}: only what the release copy lacked)"
}

fx() {  # the effect materials of this commit into the release copy, as import-chars.sh fx does in a clone
  local script=$C/src/tools/box/fp/mi_fp_import.py fl=$C/fx.log mark=$REL/Content/FX/MD_FX_Mark.uasset
  if [ ! -f "$script" ]; then say "FX SKIPPED: this commit has no tools/box/fp/mi_fp_import.py"; return 0; fi
  [ -f "$REL/Binaries/Linux/libUnrealEditor-MurderInc.so" ] || { say "FX FAILED: the release copy has no editor module (run editor first)"; return 1; }
  ue4_home
  say "FX import of the effect materials (Content/FX) from $script"
  su ue4 -c "cd $ENGINE && env HOME=/home/ue4 UE-LocalDataCachePath=/project/ue/ddc nice -n 19 ./Engine/Binaries/Linux/UnrealEditor-Cmd \
    $REL/MurderInc.uproject -run=pythonscript '-script=$script fx' -unattended -nosplash -NoSound -stdout -FullStdOutLogOutput \
    -RenderOffscreen -AllowCommandletRendering -NoDDCCleanup $CACHE_ARGS" > "$fl" 2>&1 < /dev/null
  if ! grep -a -q 'MI-DONE' "$fl" || ! grep -a -q 'MI-FP fx ok' "$fl"; then
    say "FX FAILED (log $fl: $(grep -a -E 'MI-FP fx|Traceback|Error: ' "$fl" | head -2 | cut -c1-200 | tr '\n' ' '))"
    return 1
  fi
  # The pool branch's own words are in the material's custom expression (stored as plain text in the asset).
  if ! grep -a -q 'a pool under a body' "$mark" 2>/dev/null; then
    say "FX FAILED: $mark has no pool branch after the import (pools under bodies would draw as spatters)"
    return 1
  fi
  chown -R ue4 "$REL/Content/FX"
  say "FX OK: MD_FX_Mark.uasset $(stat -c '%s bytes, %y' "$mark" | cut -c1-36) with the pool branch (log $fl)"
}

weapons() {  # the weapons of round 4 into the release copy, as import-chars.sh r4 does in a clone
  local script=$C/src/tools/box/fp/mi_guns_r4.py stamp=$REL/Content/Weapons/.r4-import key wl=$C/weapons.log
  if [ ! -f "$script" ]; then say "WEAPONS SKIPPED: this commit has no tools/box/fp/mi_guns_r4.py"; return 0; fi
  [ -d "$FPIN/glb" ] || { say "WEAPONS FAILED: no art in $FPIN/glb (tools/box/fp/fp-art.sh unpack with FP_IN=$FPIN)"; return 1; }
  [ -f "$REL/Binaries/Linux/libUnrealEditor-MurderInc.so" ] || { say "WEAPONS FAILED: the release copy has no editor module (run editor first)"; return 1; }
  # What the import depends on: the script and its two helpers, and the art (every file's name, size and time).
  key="script $(cat "$script" "$C/src/tools/box/fp/mi_fp_import.py" "$C/src/tools/box/chars/mi_chars.py" 2>/dev/null | sha256sum | cut -c1-16) art $(cd "$FPIN" && find . -type f -printf '%p %s %T@\n' | sort | sha256sum | cut -c1-16)"
  if [ -z "$MI_WEAPONS_FORCE" ] && [ "$(cat "$stamp" 2>/dev/null)" = "$key" ] && [ -d "$REL/Content/Weapons/Parts" ]; then
    say "WEAPONS KEPT: the release copy's import is of the same script and art ($key)"
    return 0
  fi
  ue4_home
  say "WEAPONS import from $FPIN ($(ls "$FPIN/glb" | wc -l) files in glb, $(ls "$FPIN/textures" 2>/dev/null | wc -l) texture sets)"
  su ue4 -c "cd $ENGINE && env HOME=/home/ue4 UE-LocalDataCachePath=/project/ue/ddc MI_FP_IN=$FPIN nice -n 19 ./Engine/Binaries/Linux/UnrealEditor-Cmd \
    $REL/MurderInc.uproject -run=pythonscript '-script=$script all' -unattended -nosplash -NoSound -stdout -FullStdOutLogOutput \
    -RenderOffscreen -AllowCommandletRendering -NoDDCCleanup $CACHE_ARGS" > "$wl" 2>&1 < /dev/null
  local steps failed absent
  steps=$(grep -a -o 'MI-FP [a-z]* \(ok\|FAILED\)' "$wl" | sed 's/MI-FP //' | tr '\n' ',' | sed 's/,$//')
  failed=$(grep -a -c 'MI-FP [a-z]* FAILED' "$wl")
  # What the art did not hold (the importer reports "no <file>" and goes on): a gun without its mesh is a missing gun.
  absent=$(grep -a 'MI-FP-REPORT' "$wl" | grep -o '"no [^"]*"' | sed 's#"no [^ ]*/##; s#"##' | tr '\n' ' ')
  if ! grep -a -q 'MI-DONE' "$wl" || [ "$failed" != 0 ]; then
    say "WEAPONS FAILED: steps $steps$( [ -n "$absent" ] && echo "; not in the art: $absent") (log $wl: $(grep -a -E 'Traceback|Error: ' "$wl" | head -2 | cut -c1-200 | tr '\n' ' '))"
    return 1
  fi
  chown -R ue4 "$REL/Content/Weapons"
  echo "$key" > "$stamp"
  say "WEAPONS OK: steps $steps$( [ -n "$absent" ] && echo "; NOT in the art (those assets keep what the release copy had, or are missing): $absent") (log $wl)"
}

overlay() {
  local ini=$REL/Config/DefaultEngine.ini game=$REL/Config/DefaultGame.ini
  sed -i 's#^GameDefaultMap=.*#GameDefaultMap=/Game/Maps/L_Block.L_Block#' "$ini"
  # Pixel Streaming 2 for every target of the release copy: the cooker is the editor, and only a cooker that loads
  # the plugin cooks the global shaders it brings (else the game stops at start: "Missing global shader
  # FXRCubemapPS"). The committed project keeps it to the game target, away from the editor and the tests.
  python3 - "$REL/MurderInc.uproject" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
for pl in d['Plugins']:
    if pl['Name'] == 'PixelStreaming2':
        pl.pop('TargetAllowList', None)
json.dump(d, open(p, 'w'), indent='\t')
PY
  chown ue4 "$REL/MurderInc.uproject"
  # The SM5 shaders too (the base engine targets SM5 and SM6; the project drops SM5): Unreal picks SM6 when the
  # server's driver passes its Vulkan profile check, else SM5. Without them a failed check ends the game 7 s after
  # the start ("Failed to initialize ShaderCodeLibrary", exit 1), with no log in Shipping.
  sed -i '/^-TargetedRHIs=SF_VULKAN_SM5$/d' "$ini"
  cat >> "$ini" <<'EOF'

; ---- cloud package overlay (tools/box/cloud/package-cloud.sh) ----
; The engine's crash handler skips its report when no display is set (headless servers count as unattended) unless
; crash upload is agreed. No crash reporter is packaged, so nothing is uploaded: the report stays in
; Saved/Crashes/crashinfo-*/ (Diagnostics.txt has the call stack), and the launcher copies it into the log.
[CrashReportClient]
bAgreeToCrashUpload=true
bStartCRCFromEngineHandler=false
EOF
  cat >> "$game" <<'EOF'

; ---- cloud package overlay (tools/box/cloud/package-cloud.sh; same as tools/box/demo/package.sh) ----
[/Script/UnrealEd.ProjectPackagingSettings]
+MapsToCook=(FilePath="/Game/Maps/L_Block")
+MapsToCook=(FilePath="/Game/Maps/L_Chinatown")
+MapsToCook=(FilePath="/Game/Maps/L_Midtown")
+DirectoriesToAlwaysCook=(Path="/Game/Art")
+DirectoriesToAlwaysCook=(Path="/Game/Audio")
+DirectoriesToAlwaysCook=(Path="/Game/Characters")
+DirectoriesToAlwaysCook=(Path="/Game/FX")
+DirectoriesToAlwaysCook=(Path="/Game/FirstPerson")
+DirectoriesToAlwaysCook=(Path="/Game/ThirdParty")
+DirectoriesToAlwaysCook=(Path="/Game/Weapons")
+DirectoriesToAlwaysCook=(Path="/Game/Input")
+DirectoriesToAlwaysCook=(Path="/Game/Variant_Shooter")
+DirectoriesToAlwaysStageAsNonUFS=(Path="Fonts")
bUseIoStore=True
bShareMaterialShaderCode=True
bUseZenStore=False
EOF
  chown ue4 "$ini" "$game"
  say "OVERLAY OK"
}

usage() {
  local script=$C/src/tools/box/cloud/cloud_assets.py fix=$C/src/tools/box/demo/fix_usage.py
  [ -f "$script" ] && [ -f "$fix" ] || { say "run src first (no $script)"; return 1; }
  [ -f "$REL/MurderInc.uproject" ] || { say "run refresh and content first"; return 1; }
  export HOME=/home/ue4
  su ue4 -c "cd $ENGINE && env HOME=/home/ue4 UE-LocalDataCachePath=/project/ue/ddc MI_FIX_USAGE=$fix ./Engine/Binaries/Linux/UnrealEditor-Cmd $REL/MurderInc.uproject \
    -run=pythonscript -script=$script -unattended -nosplash -NullRHI -nopause -stdout -FullStdOutLogOutput -NoDDCCleanup \
    '-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal)' -ini:Engine:[Zen]:AutoLaunch=false \
    -ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1" > "$C/usage.log" 2>&1
  local saved missing
  saved=$(grep -ac 'fix_usage: .* saved True' "$C/usage.log")
  missing=$(grep -ac 'fix_usage: missing' "$C/usage.log")
  [ "$saved" -gt 0 ] || { say "USAGE FAILED: nothing saved (log $C/usage.log)"; return 1; }
  local cubes; cubes=$(grep -a 'cloud_assets: [0-9]* interior cube' "$C/usage.log" | tail -1 | sed 's/.*cloud_assets: //')
  [ -n "$cubes" ] || { say "USAGE FAILED: the cube map step did not finish (log $C/usage.log)"; return 1; }
  say "USAGE OK: $saved material(s) saved with their flags, $missing not found; $cubes (log $C/usage.log)"
}

package() {
  local cfg=${1:-Shipping} cook="-cook -IgnoreCookErrors"
  [ "$cfg" = Shipping ] && [ -d "$REL/Saved/Cooked/Linux" ] && cook="-skipcook"
  ue4_home
  rm -rf "$C/build-$cfg"; mkdir -p "$C/build-$cfg"; chown ue4 "$C/build-$cfg"
  # -NoDDCCleanup: no cache maintainer. On a fresh box it scans the whole file-system cache on the 9p volume at 100 %
  # of a core and the cooker's own cache reads crawl meanwhile ("is very slow (0.00 MiB/s)"; 2026-11-24, box ec087d85).
  say "PACKAGE $cfg ($cook)"
  su ue4 -c "cd $ENGINE && env HOME=/home/ue4 UE-LocalDataCachePath=/project/ue/ddc ./Engine/Build/BatchFiles/RunUAT.sh BuildCookRun \
    -project=$REL/MurderInc.uproject -noP4 -utf8output -unattended -platform=Linux -clientconfig=$cfg -target=MurderInc \
    -build -nocompileeditor '-UbtArgs=-NoUBA -WaitMutex -MaxParallelActions=$JOBS' $cook -map=/Game/Maps/L_Block+/Game/Maps/L_Chinatown+/Game/Maps/L_Midtown -stage -pak -iostore \
    -archive -archivedirectory=$C/build-$cfg -prereqs \
    '-AdditionalCookerOptions=-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal) -NoDDCCleanup -ini:Engine:[Zen]:AutoLaunch=false -ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1'" \
    || { say "PACKAGE $cfg FAILED"; return 1; }
  cp "$C/src.commit" "$C/build-$cfg.commit"  # the commit the game binaries were built from (BUILD.txt)
  local snd gun pso; snd=$(python3 "$C/src/tools/box/cloud/pak_sounds.py" "$C/build-$cfg/Linux") || { say "PACKAGE $cfg FAILED: $snd"; return 1; }
  gun=$(guncheck "$cfg") || { say "PACKAGE $cfg FAILED: $gun"; return 1; }
  pso=$(psocheck "$cfg") || { say "PACKAGE $cfg FAILED: $pso"; return 1; }
  # The stable shader keys of this cook (NeedsShaderStableKeys, Config/DefaultEngine.ini): what turns a recording of
  # this package's pipeline states into a cache (pso-cache.sh expand). The next cook replaces them, so keep a copy.
  local K=$REL/Saved/Cooked/Linux/MurderInc/Metadata/PipelineCaches
  if [ "$cfg" = Development ] && ls "$K"/*SF_VULKAN_SM5* > /dev/null 2>&1; then
    rm -rf "$C/pso-keys" && mkdir -p "$C/pso-keys" && cp -a "$K/." "$C/pso-keys/" && cp "$C/src.commit" "$C/pso-keys/commit.txt"
  fi
  say "PACKAGE $cfg OK: $(du -sh "$C/build-$cfg/Linux" | cut -f1); $snd; $gun; $pso"
}

psocheck() {  # <config>: the recorded pipeline cache of the commit (if it has one) is in the build's pak list
  local spc n
  spc=$(ls "$REL"/Build/Linux/PipelineCaches/*.spc 2>/dev/null | head -1)
  if [ -z "$spc" ]; then echo "PSO CACHE: none in this commit (Build/Linux/PipelineCaches)"; return 0; fi
  n=$(grep -a -c 'PipelineCaches/Linux/MurderInc_SF_VULKAN_SM5.stable.upipelinecache' "$C/build-$1/Linux/Manifest_UFSFiles_Linux.txt" 2>/dev/null)
  if [ "${n:-0}" -lt 1 ]; then
    echo "PSO CACHE MISSING: the commit has $(basename "$spc") but the pak list of build-$1 has no MurderInc_SF_VULKAN_SM5.stable.upipelinecache (the cook did not turn it into a cache: see 'UShaderPipelineCacheToolsCommandlet' in the cook log)"
    return 1
  fi
  echo "PSO CACHE OK: $(basename "$spc") ($(stat -c %s "$spc") bytes) is in the pak list as MurderInc_SF_VULKAN_SM5.stable.upipelinecache"
}

sounds() {  # every Sound Wave the game's data names must be in the pak list of both builds
  local cfg out rc=0
  for cfg in Shipping Development; do
    out=$(python3 "$C/src/tools/box/cloud/pak_sounds.py" "$C/build-$cfg/Linux") || rc=1
    say "$out"
  done
  return $rc
}

guncheck() {  # <config>: every gun, magazine and part mesh the game's data names in the pak list of that build
  local g=$C/src/tools/box/cloud/pak_weapons.py
  [ -f "$g" ] || { echo "WEAPONS NOT CHECKED: this commit has no tools/box/cloud/pak_weapons.py"; return 0; }
  python3 "$g" "$C/build-$1/Linux"
}

guns() {
  local cfg out rc=0
  for cfg in Shipping Development; do
    out=$(guncheck "$cfg") || rc=1
    say "$out"
  done
  return $rc
}

zipit() {
  local L=$C/build-Shipping/Linux z=$ZIP B=$C/build-Shipping/Linux/MurderInc/Binaries/Linux
  local D=$C/build-Development/Linux/MurderInc/Binaries/Linux launcher=$C/src/tools/box/cloud/MurderInc.sh
  local kf=${ZIP%.zip}.devkey
  [ -f "$L/MurderInc.sh" ] || { say "no $L/MurderInc.sh"; return 1; }
  [ -f "$launcher" ] && [ -f "$C/src.commit" ] || { say "run src first (no $launcher or src.commit)"; return 1; }
  # No zip of a game that cannot make a sound: the pak list of both games must hold every Sound Wave the data names.
  sounds || { say "ZIP REFUSED: a sound the game plays is not in the package (lines above). No zip was made."; rm -f "$z" "$z.sha256"; return 1; }
  # Nor of a game whose guns or parts have no mesh.
  guns || { say "ZIP REFUSED: a gun, magazine or part the game's data names is not in the package (lines above). No zip was made."; rm -f "$z" "$z.sha256"; return 1; }
  # Nor of a game whose recorded pipeline cache was left out (the cold-start freezes of SMOOTH.md H3 come back).
  local pc; for pc in Shipping Development; do
    psocheck "$pc" > /dev/null || { say "ZIP REFUSED: $(psocheck "$pc"). No zip was made."; rm -f "$z" "$z.sha256"; return 1; }
  done
  local sha gsha; sha=$(cat "$C/src.commit"); gsha=$(cat "$C/build-Shipping.commit" 2>/dev/null || echo "$sha")
  # Our launcher in place of the engine's (which ran MurderInc-Linux-Shipping MurderInc -MICloud "$@" and kept no
  # log): it logs to MurderInc/Saved/Logs, passes stop signals on, never runs the game as root.
  cp "$launcher" "$L/MurderInc.sh" && chmod 755 "$L/MurderInc.sh" || return 1
  # The Development game beside the Shipping one (the same cooked content and paks): launch option -MIDev=<key>.
  # The key: 16 random hex digits, new for every zip. The launcher starts the Development game only with it, so a
  # visitor who adds -MIDev to a stream link gets the Shipping game. It goes to the owner with the release report;
  # the game never sees it (the launcher keeps the option to itself) and nothing prints it.
  if [ -f "$D/MurderInc" ]; then cp "$D/MurderInc" "$B/MurderInc" && chmod 755 "$B/MurderInc" || return 1; fi
  local key; key=$(head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')
  [ ${#key} = 16 ] || { say "no random key"; return 1; }
  echo "$key" > "$L/MIDEV.key" && chmod 644 "$L/MIDEV.key" && echo "$key" > "$kf" || return 1
  {
    echo "MURDER INC. cloud build for Eagle 3D Streaming (Linux, Unreal Engine 5.9, Pixel Streaming 2)"
    echo "commit $gsha (branch $BRANCH)$( [ "$gsha" != "$sha" ] && echo "; launcher and packaging from commit $sha")"
    echo "packaged $(date -u '+%Y-%m-%d %H:%M UTC') with tools/box/cloud/package-cloud.sh"
    echo "games: MurderInc/Binaries/Linux/MurderInc-Linux-Shipping (default), MurderInc/Binaries/Linux/MurderInc (Development: launch option -MIDev=<key>, the word in MIDEV.key)"
    echo "shaders: Vulkan SM6 (Nanite, Lumen, hardware ray tracing) and the SM5 fallback; log: MurderInc/Saved/Logs/MurderInc.log"
  } > "$L/BUILD.txt"
  # Debug symbols stay on the box, by commit, to turn a crash report's addresses into function names.
  local S=$C/symbols/${gsha:0:7}
  mkdir -p "$S" && cp -f "$B"/*.debug "$B"/*.sym "$D"/*.debug "$D"/*.sym "$S/" 2>/dev/null
  rm -f "$z"
  (cd "$L" && python3 - "$z" <<'EOF'
import os, sys, zipfile
out = sys.argv[1]
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for root, dirs, files in os.walk('.'):
        # Saved/ is what a run of the game writes (logs, crash reports, settings: the box's own test runs): never ship it.
        dirs[:] = sorted(d for d in dirs if d != 'Saved')
        for f in sorted(files):
            if f.endswith(('.debug', '.sym')):
                continue  # symbols: kept on the box (symbols/<commit>/), not shipped
            p = os.path.join(root, f)
            z.write(p, os.path.relpath(p, '.'))  # keeps the executable bits
EOF
  ) || return 1
  sha256sum "$z" | cut -d' ' -f1 > "$z.sha256"
  say "ZIP OK: $z $(du -h "$z" | cut -f1) sha256 $(cat "$z.sha256") (game ${gsha:0:7}, launcher ${sha:0:7}; symbols in $S; the Development game's key is in $kf: give it to the owner with the release report, never commit it)"
}

parts() {
  local z=$ZIP P=$C/parts
  [ -f "$z" ] && [ -f "$z.sha256" ] || { say "no $z"; return 1; }
  rm -rf "$P"; mkdir -p "$P"
  (cd "$P" && split -b 240M -d -a 2 "$z" tmp-part-) || return 1
  local n k=0 f stem=MurderInc-E3DS-${MI_TAG:+$MI_TAG-}part; n=$(ls "$P"/tmp-part-* | wc -l)
  for f in $(ls "$P"/tmp-part-* | sort); do k=$((k + 1)); mv "$f" "$P/$stem$k-of-$n.zip"; done
  (cd "$P" && for k in $(seq 1 "$n"); do sha256sum "$stem$k-of-$n.zip"; done) > "$C/parts.sha256"
  local joined; joined=$(for k in $(seq 1 "$n"); do cat "$P/$stem$k-of-$n.zip"; done | sha256sum | cut -d' ' -f1)
  [ "$joined" = "$(cat "$z.sha256")" ] || { say "PARTS FAILED: joined sha256 $joined differs from the zip's"; return 1; }
  say "PARTS OK: $n parts in $P (list $C/parts.sha256), joined sha256 = the zip's"
}

all() {
  echo RUNNING > "$ST"
  ( set -o pipefail
    src && refresh && editor && content && fx && weapons && overlay && usage && package Development && package Shipping && zipit \
      && if [ "${MI_PARTS:-1}" = 0 ]; then say "PARTS LEFT OUT (MI_PARTS=0)"; else parts; fi
  ) && echo OK > "$ST" || echo FAILED > "$ST"
  say "ALL $(cat "$ST")"
}

status() {
  echo "CLOUD PACKAGE $(cat "$ST" 2>/dev/null || echo NONE)"
  grep -E '^\[[0-9:]+\]|BUILD (SUCCESSFUL|FAILED)|Error:|ERROR:' "$LOG" 2>/dev/null | tail -10 | cut -c1-300
  tail -2 "$LOG" 2>/dev/null | cut -c1-300
}

[ "$(id -u)" = 0 ] || { echo "run as root (it switches to ue4 for the engine)"; exit 1; }
case "$1" in
  src|refresh|editor|content|fx|weapons|overlay|usage|sounds|guns) "$1" ;;
  zip) zipit ;;
  parts) parts ;;
  package) package "$2" ;;
  all) mkdir -p "$C"; setsid nohup bash "$ME" all-fg </dev/null >"$LOG" 2>&1 & echo "started: poll package-cloud.sh status" ;;
  all-fg) all ;;
  status) status ;;
  *) sed -n '2,/^$/p' "$0"; exit 2 ;;
esac
