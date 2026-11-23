#!/bin/bash
# The cloud (Pixel Streaming 2) package of MURDER INC., for Eagle 3D Streaming (docs/LAUNCH.md), in one command:
#
#   bash /project/ue/cloud/src/tools/box/cloud/package-cloud.sh all     (as root on the box; detached, poll status)
#
# Steps (each can be run alone):
#   src        fetch the branch into /project/ue/cloud/src (sparse clone: unreal/MurderInc, tools/box)
#   refresh    copy the branch's Source, Config and .uproject into the release copy /project/ue/repo-release
#   content    copy the gameplay clone's Content into the release copy, only if no editor has that clone open
#              (else the release copy keeps the Content of its last copy, and the step says so)
#   overlay    the packaging settings, on the release copy only (start map L_Block, folders loaded by path, fonts,
#              no Zen store): the same as tools/box/demo/package.sh
#   package <Development|Shipping>   BuildCookRun Linux into /project/ue/cloud/build-<config> (Shipping skips the
#              cook when a cook exists)
#   zip        /project/ue/cloud/MurderInc-E3DS.zip from build-Shipping: MurderInc.sh at the root (E3DS app name =
#              script name = MurderInc), plus its sha256
#   all        src, refresh, content, overlay, package Development, package Shipping, zip (detached; log in
#              /project/ue/cloud/package.log)
#   status     the step running or the result, and the last log lines
#
# The package holds pack, Epic and likeness content: it stays on the box and goes only to the owner's private
# Higgsfield storage (docs/LAUNCH.md); it is never committed.

C=/project/ue/cloud
REL=/project/ue/repo-release/unreal/MurderInc
GP=/project/ue/repo-gameplay/unreal/MurderInc
ENGINE=/project/ue/UnrealEngine
BRANCH=${MI_BRANCH:-claude/tender-albattani-5q78qr}
LOG=$C/package.log
ST=$C/package.status
ME=$(readlink -f "$0")
say() { echo "[$(date +%H:%M:%S)] $*"; }

as_ue4() { su ue4 -c "$(printf '%q ' "$@")"; }

src() {
  local url; url=$(as_ue4 git -C /project/ue/repo remote get-url origin 2>/dev/null)
  [ -n "$url" ] || { say "no origin url in /project/ue/repo"; return 1; }
  if [ ! -d "$C/src/.git" ]; then
    rm -rf "$C/src" && mkdir -p "$C" && chown ue4 "$C"
    as_ue4 git clone -q --depth 1 --filter=blob:none --sparse -b "$BRANCH" "$url" "$C/src" || return 1
    as_ue4 git -C "$C/src" sparse-checkout set unreal/MurderInc tools/box || return 1
  else
    as_ue4 git -C "$C/src" fetch -q --depth 1 origin "$BRANCH" && as_ue4 git -C "$C/src" reset -q --hard FETCH_HEAD || return 1
  fi
  say "SRC OK at $(git -C "$C/src" log --oneline -1)"
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

content() {
  local busy
  busy=$(ps -eo args | grep -E '^[^ ]*UnrealEditor[^ ]* .*repo-gameplay/' | grep -v grep | head -1)
  if [ -n "$busy" ]; then
    say "CONTENT KEPT: an editor has the gameplay clone open; the release copy keeps its last Content ($(du -sh "$REL/Content" 2>/dev/null | cut -f1))"
    return 0
  fi
  [ -d "$GP/Content" ] || { say "no gameplay clone Content"; return 1; }
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

package() {
  local cfg=${1:-Shipping} cook="-cook -IgnoreCookErrors"
  [ "$cfg" = Shipping ] && [ -d "$REL/Saved/Cooked/Linux" ] && cook="-skipcook"
  export HOME=/home/ue4
  mkdir -p /home/ue4/.config; [ -L /home/ue4/.config/Epic ] || ln -sfn /project/ue/home/Epic /home/ue4/.config/Epic
  chown -h ue4 /home/ue4/.config/Epic 2>/dev/null
  rm -rf "$C/build-$cfg"; mkdir -p "$C/build-$cfg"; chown ue4 "$C/build-$cfg"
  say "PACKAGE $cfg ($cook)"
  su ue4 -c "cd $ENGINE && env HOME=/home/ue4 UE-LocalDataCachePath=/project/ue/ddc ./Engine/Build/BatchFiles/RunUAT.sh BuildCookRun \
    -project=$REL/MurderInc.uproject -noP4 -utf8output -unattended -platform=Linux -clientconfig=$cfg -target=MurderInc \
    -build -nocompileeditor '-UbtArgs=-NoUBA -WaitMutex' $cook -map=/Game/Maps/L_Block -stage -pak -iostore \
    -archive -archivedirectory=$C/build-$cfg -prereqs \
    '-AdditionalCookerOptions=-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal) -ini:Engine:[Zen]:AutoLaunch=false -ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1'" \
    || { say "PACKAGE $cfg FAILED"; return 1; }
  say "PACKAGE $cfg OK: $(du -sh "$C/build-$cfg/Linux" | cut -f1)"
}

zipit() {
  local L=$C/build-Shipping/Linux z=$C/MurderInc-E3DS.zip
  [ -f "$L/MurderInc.sh" ] || { say "no $L/MurderInc.sh"; return 1; }
  # The engine's launcher runs the Shipping binary with "$@" (what E3DS passes: the Pixel Streaming connection,
  # resolution, off-screen rendering). -MICloud makes sure the cloud profile is on even if their arguments change.
  grep -q -- '-MICloud' "$L/MurderInc.sh" || sed -i 's#"\$@"#-MICloud "$@"#' "$L/MurderInc.sh"
  chmod +x "$L/MurderInc.sh"
  rm -f "$z"
  (cd "$L" && python3 - "$z" <<'EOF'
import os, sys, zipfile
out = sys.argv[1]
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for root, dirs, files in os.walk('.'):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(root, f)
            z.write(p, os.path.relpath(p, '.'))  # keeps the executable bits
EOF
  ) || return 1
  sha256sum "$z" | cut -d' ' -f1 > "$z.sha256"
  say "ZIP OK: $z $(du -h "$z" | cut -f1) sha256 $(cat "$z.sha256")"
}

all() {
  echo RUNNING > "$ST"
  ( set -o pipefail
    src && refresh && content && overlay && package Development && package Shipping && zipit
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
  src|refresh|content|overlay) "$1" ;;
  zip) zipit ;;
  package) package "$2" ;;
  all) mkdir -p "$C"; setsid nohup bash "$ME" all-fg </dev/null >"$LOG" 2>&1 & echo "started: poll package-cloud.sh status" ;;
  all-fg) all ;;
  status) status ;;
  *) sed -n 2,24p "$0"; exit 2 ;;
esac
