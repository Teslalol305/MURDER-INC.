#!/bin/bash
# The cloud (Pixel Streaming 2) package of MURDER INC., for Eagle 3D Streaming (docs/LAUNCH.md), in one command:
#
#   bash /project/ue/cloud/src/tools/box/cloud/package-cloud.sh all     (as root on the box; detached, poll status)
#
# Steps (each can be run alone):
#   src        fetch the branch into /project/ue/cloud/src (sparse clone: unreal/MurderInc, tools/box)
#   refresh    copy the branch's Source, Config and .uproject into the release copy /project/ue/repo-release
#   content    copy the gameplay clone's Content into the release copy, only if no editor has that clone open
#              (else the release copy keeps the Content of its last copy, and the step says so). It fails when a
#              sound of the gameplay clone has no Sound Wave asset or an older one than its WAV: the assets are
#              generated content (tools/box/audio-import.sh there), and a package without them is silent
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
#              (cloud/pak_sounds.py), with its .uasset, .uexp and .ubulk, and does the cook's own output hold the audio
#              (a .ubulk of more than 100 bytes) from an asset at least as new as the release copy's? "package" and
#              "zip" ask the same and stop when one is missing: versions 1, 2 and 3a were packaged without a single
#              sound and nothing said so, and a wave whose audio failed to encode passed by its name
#   zip        /project/ue/cloud/MurderInc-E3DS.zip from build-Shipping: the launcher cloud/MurderInc.sh at the root
#              (E3DS app name = script name = MurderInc; it logs to MurderInc/Saved/Logs), BUILD.txt (the commit), the
#              Development game beside the Shipping one (launch option -MIDev=<key>; the key is a new random word
#              in MIDEV.key at the zip's root, copied to /project/ue/cloud/MurderInc-E3DS.devkey for the release
#              report: a visitor can add launch options to a stream link and must not be able to start the Development
#              game, which has the debug switches; never commit the key), no *.debug / *.sym (kept on the box in
#              /project/ue/cloud/symbols/<commit>/ to read crash call stacks), plus its sha256
#   parts      the zip in parts of 240 MiB (the storage takes at most about 250 MB a file) in /project/ue/cloud/parts,
#              named MurderInc-E3DS-part<k>-of-<n>.zip, with parts.sha256 (MI_TAG=v3a in the environment names them
#              MurderInc-E3DS-v3a-part<k>-of-<n>.zip: the names the owner sees in the storage)
#   all        src, refresh, content, overlay, usage, package Development, package Shipping, zip, parts (detached;
#              log in /project/ue/cloud/package.log)
#   status     the step running or the result, and the last log lines
#
# MI_COMMIT=<40 hex digits> in the environment packages that commit of the branch instead of its head (src fetches
# it; BUILD.txt names it). For a release while other work is pushed to the same branch: the head may by then hold
# game code that is not tested or gated yet. The commit must be on the pushed branch.
#
# The package holds pack, Epic and likeness content: it stays on the box and goes only to the owner's private
# Higgsfield storage (docs/LAUNCH.md); it is never committed.

C=${MI_CLOUD:-/project/ue/cloud}   # (another folder only to try a step on a copy)
REL=/project/ue/repo-release/unreal/MurderInc
GP=/project/ue/repo-gameplay/unreal/MurderInc
ENGINE=/project/ue/UnrealEngine
BRANCH=${MI_BRANCH:-claude/tender-albattani-5q78qr}
COMMIT=${MI_COMMIT:-}              # this commit of the branch instead of its head
LOG=$C/package.log
ST=$C/package.status
ME=$(readlink -f "$0")
say() { echo "[$(date +%H:%M:%S)] $*"; }

as_ue4() { su ue4 -c "$(printf '%q ' "$@")"; }

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
  chown -R ue4 "$REL/Source" "$REL/Config" "$REL/MurderInc.uproject" "$REL/Content/Data" "$REL/Content/Python"
  say "REFRESH OK: Source, Config, Data from the branch"
}

# Sound Waves without an asset, and assets older than their WAV, under a Content folder: "<missing> <stale>".
audio_stale() {
  local w a missing=0 stale=0
  while IFS= read -r w; do
    a=${w%.wav}.uasset
    if [ ! -f "$a" ]; then missing=$((missing + 1)); elif [ "$w" -nt "$a" ]; then stale=$((stale + 1)); fi
  done < <(find "$1/Audio" -name '*.wav' ! -name 'IR_*' 2>/dev/null)
  echo "$missing $stale"
}

content() {
  local busy
  busy=$(ps -eo args | grep -E '^[^ ]*UnrealEditor[^ ]* .*repo-gameplay/' | grep -v grep | head -1)
  if [ -n "$busy" ]; then
    # The release copy keeps its last Content: it must be one that sounds (an editor open on the gameplay clone, a test
    # run included, used to return here before any look at the sounds: a copy whose audio had been replaced since, or
    # that had none, was packaged all the same).
    local n; n=$(audio_stale "$REL/Content")
    if [ "${n% *}" != 0 ] || [ "${n#* }" != 0 ] || [ ! -d "$REL/Content/Audio/Web" ]; then
      say "CONTENT FAILED: an editor has the gameplay clone open, so the release copy keeps its last Content, and that has ${n% *} sound(s) without a Sound Wave asset and ${n#* } with an asset older than its WAV$([ -d "$REL/Content/Audio/Web" ] || echo ' (no Content/Audio/Web at all)'): the package would be silent there. Close the editor (or finish the audio import in the gameplay clone) and run this step again"
      return 1
    fi
    say "CONTENT KEPT: an editor has the gameplay clone open; the release copy keeps its last Content ($(du -sh "$REL/Content" 2>/dev/null | cut -f1)); its $(find "$REL/Content/Audio" -name '*.wav' ! -name 'IR_*' | wc -l) sounds all have an asset not older than their WAV"
    return 0
  fi
  [ -d "$GP/Content" ] || { say "no gameplay clone Content"; return 1; }
  # The sounds: every WAV of the gameplay clone needs its Sound Wave asset, not older than the WAV.
  local n missing stale; n=$(audio_stale "$GP/Content"); missing=${n% *}; stale=${n#* }
  if [ "$missing" != 0 ] || [ "$stale" != 0 ] || [ ! -d "$GP/Content/Audio" ] || [ ! -d "$GP/Content/Audio/Web" ]; then
    say "CONTENT FAILED: the gameplay clone has $missing sound(s) without a Sound Wave asset and $stale with an asset older than its WAV$([ -d "$GP/Content/Audio" ] || echo ' (no Content/Audio at all)')$([ -d "$GP/Content/Audio/Web" ] || echo ' (no Content/Audio/Web: the web game'"'"'s sounds are not in git, node tools/ue-export/audio.mjs makes them)'): the package would be silent there. Run 'bash tools/box/audio-import.sh' in /project/ue/repo-gameplay (its editor stopped), poll 'audio-import.sh status' until AUDIO-IMPORT-DONE failed=0, then package again"
    return 1
  fi
  # Content (not Data or Python: those come from the branch) and the editor module the cooker loads.
  (cd "$GP" && tar -cf - --exclude=Content/Data --exclude=Content/Python Content Binaries) \
    | tar --no-same-owner -C "$REL" -xf - || return 1
  chown -R ue4 "$REL/Content" "$REL/Binaries"
  say "CONTENT OK: $(du -sh "$REL/Content" | cut -f1) from the gameplay clone"
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

# The cook is current when nothing it cooks from is newer than the end of the Development package (whose cook it is):
# "package Shipping" used to skip the cook whenever a cooked folder existed, so content, package Shipping and zip shipped
# the audio of an older cook with "SOUNDS OK" (which read the pak list's names only).
cook_current() {
  local mark=$C/build-Development.commit
  [ -d "$REL/Saved/Cooked/Linux" ] && [ -f "$mark" ] || return 1
  [ -z "$(find "$REL/Content" \( -path "$REL/Content/Data" -o -path "$REL/Content/Python" \) -prune -o -type f -newer "$mark" -print -quit 2>/dev/null)" ]
}

package() {
  local cfg=${1:-Shipping} cook="-cook -IgnoreCookErrors"
  if [ "$cfg" = Shipping ]; then
    if cook_current; then cook="-skipcook"; else say "COOK: the Development package's cook is missing or older than the release copy's Content: cooking again for Shipping"; fi
  fi
  export HOME=/home/ue4
  mkdir -p /home/ue4/.config; [ -L /home/ue4/.config/Epic ] || ln -sfn /project/ue/home/Epic /home/ue4/.config/Epic
  chown -h ue4 /home/ue4/.config/Epic 2>/dev/null
  rm -rf "$C/build-$cfg"; mkdir -p "$C/build-$cfg"; chown ue4 "$C/build-$cfg"
  # -NoDDCCleanup: no cache maintainer. On a fresh box it scans the whole file-system cache on the 9p volume at 100 %
  # of a core and the cooker's own cache reads crawl meanwhile ("is very slow (0.00 MiB/s)"; 2026-11-24, box ec087d85).
  say "PACKAGE $cfg ($cook)"
  su ue4 -c "cd $ENGINE && env HOME=/home/ue4 UE-LocalDataCachePath=/project/ue/ddc ./Engine/Build/BatchFiles/RunUAT.sh BuildCookRun \
    -project=$REL/MurderInc.uproject -noP4 -utf8output -unattended -platform=Linux -clientconfig=$cfg -target=MurderInc \
    -build -nocompileeditor '-UbtArgs=-NoUBA -WaitMutex' $cook -map=/Game/Maps/L_Block -stage -pak -iostore \
    -archive -archivedirectory=$C/build-$cfg -prereqs \
    '-AdditionalCookerOptions=-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal) -NoDDCCleanup -ini:Engine:[Zen]:AutoLaunch=false -ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1'" \
    || { say "PACKAGE $cfg FAILED"; return 1; }
  cp "$C/src.commit" "$C/build-$cfg.commit"  # the commit the game binaries were built from (BUILD.txt)
  local snd; snd=$(python3 "$C/src/tools/box/cloud/pak_sounds.py" "$C/build-$cfg/Linux" --cooked "$REL/Saved/Cooked/Linux/MurderInc" --source "$REL/Content") || { say "PACKAGE $cfg FAILED: $snd"; return 1; }
  say "PACKAGE $cfg OK: $(du -sh "$C/build-$cfg/Linux" | cut -f1); $snd"
}

sounds() {  # every Sound Wave the game's data names must be in the pak list of both builds
  local cfg out rc=0
  for cfg in Shipping Development; do
    out=$(python3 "$C/src/tools/box/cloud/pak_sounds.py" "$C/build-$cfg/Linux" --cooked "$REL/Saved/Cooked/Linux/MurderInc" --source "$REL/Content") || rc=1
    say "$out"
  done
  return $rc
}

zipit() {
  local L=$C/build-Shipping/Linux z=$C/MurderInc-E3DS.zip B=$C/build-Shipping/Linux/MurderInc/Binaries/Linux
  local D=$C/build-Development/Linux/MurderInc/Binaries/Linux launcher=$C/src/tools/box/cloud/MurderInc.sh
  [ -f "$L/MurderInc.sh" ] || { say "no $L/MurderInc.sh"; return 1; }
  [ -f "$launcher" ] && [ -f "$C/src.commit" ] || { say "run src first (no $launcher or src.commit)"; return 1; }
  # No zip of a game that cannot make a sound: the pak list of both games must hold every Sound Wave the data names.
  sounds || { say "ZIP REFUSED: a sound the game plays is not in the package (lines above). No zip was made."; rm -f "$z" "$z.sha256"; return 1; }
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
  echo "$key" > "$L/MIDEV.key" && chmod 644 "$L/MIDEV.key" && echo "$key" > "$C/MurderInc-E3DS.devkey" || return 1
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
  say "ZIP OK: $z $(du -h "$z" | cut -f1) sha256 $(cat "$z.sha256") (game ${gsha:0:7}, launcher ${sha:0:7}; symbols in $S; the Development game's key is in $C/MurderInc-E3DS.devkey: give it to the owner with the release report, never commit it)"
}

parts() {
  local z=$C/MurderInc-E3DS.zip P=$C/parts
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
    src && refresh && content && overlay && usage && package Development && package Shipping && zipit && parts
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
  src|refresh|content|overlay|usage|sounds) "$1" ;;
  zip) zipit ;;
  parts) parts ;;
  package) package "$2" ;;
  all) mkdir -p "$C"; setsid nohup bash "$ME" all-fg </dev/null >"$LOG" 2>&1 & echo "started: poll package-cloud.sh status" ;;
  all-fg) all ;;
  status) status ;;
  *) sed -n 2,41p "$0"; exit 2 ;;
esac
