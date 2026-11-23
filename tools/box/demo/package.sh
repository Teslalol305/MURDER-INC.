#!/bin/bash
# Package the game for the demo: a Linux Development build of the most complete project on the box.
# Runs on the box (as root through gpu_rental_exec; the engine part re-runs itself as user ue4).
#
#   package.sh snapshot   copy the gameplay clone's project (Source, Config, Content with the imported art, the
#                         editor module in Binaries) to /project/ue/repo-demo and apply the demo settings
#   package.sh start      BuildCookRun (build the game target, cook L_Block, stage, pak, archive) detached
#   package.sh status     RUNNING / OK / FAILED, the minutes so far and the last log lines
#   package.sh stop       stop a package run (its process group)
#
# The archive lands in /project/ue/demo/build/Linux (MurderInc.sh starts it). It holds pack and Epic content:
# it stays on the box and is never committed or published (docs/DEMO.md, docs/unreal/RESUME.md section 2).
# Measured 2026-11-23: snapshot about 40 s (1.7 GB of Content); see docs/unreal/PROGRESS.md for the package time.

SRC=${MI_DEMO_SRC:-/project/ue/repo-gameplay/unreal/MurderInc}
DEMO=/project/ue/repo-demo/unreal/MurderInc
WORK=/project/ue/demo
OUT=$WORK/build
LOG=$WORK/package.log
ST=$WORK/package.status
ENGINE=/project/ue/UnrealEngine

snapshot() {
  [ "$(id -u)" = 0 ] || { echo "snapshot runs as root (the gameplay clone has files ue4 cannot read)"; exit 1; }
  [ -f "$SRC/MurderInc.uproject" ] || { echo "no project at $SRC"; exit 1; }
  mkdir -p "$(dirname "$DEMO")" "$WORK"
  rm -rf "$DEMO"
  # Intermediate, Saved and the cache are rebuilt; Binaries carries the editor module the cooker loads.
  (cd "$(dirname "$SRC")" && tar -cf - --exclude=MurderInc/Intermediate --exclude=MurderInc/Saved \
      --exclude=MurderInc/DerivedDataCache MurderInc) | tar --no-same-owner -C "$(dirname "$DEMO")" -xf - || exit 1
  overlay
  chown -R ue4 /project/ue/repo-demo "$WORK" && chmod -R u+rwX /project/ue/repo-demo
  echo "SNAPSHOT OK: $DEMO ($(du -sh "$DEMO/Content" | cut -f1) of Content)"
}

# The demo settings, written into the snapshot only (the committed project keeps L_Bootstrap: L_Block is
# generated content and is missing from a clean checkout).
overlay() {
  local ini=$DEMO/Config/DefaultEngine.ini game=$DEMO/Config/DefaultGame.ini
  sed -i 's#^GameDefaultMap=.*#GameDefaultMap=/Game/Maps/L_Block.L_Block#' "$ini"
  cat >> "$game" <<'EOF'

; ---- demo overlay (tools/box/demo/package.sh) ----
[/Script/UnrealEd.ProjectPackagingSettings]
BuildConfiguration=PPBC_Development
+MapsToCook=(FilePath="/Game/Maps/L_Block")
bUseIoStore=True
bShareMaterialShaderCode=True
; The cooker writes into Zen storage by default in 5.9, and the box cannot reach a Zen server (BOX.md section 1):
; "Failed to delete oplog on the ZenServer" (ZenStoreWriter.cpp) ends the cook. Loose cooked files instead.
bUseZenStore=False
EOF
}

start() {
  [ "$(id -un)" = ue4 ] || exec su ue4 -c "bash $(printf '%q' "$0") start"
  [ -f "$DEMO/MurderInc.uproject" ] || { echo "run package.sh snapshot first"; exit 1; }
  if [ "$(cat "$ST" 2>/dev/null)" = RUNNING ] && kill -0 "$(cat "$WORK/package.pid" 2>/dev/null)" 2>/dev/null; then
    echo "already RUNNING"; exit 0
  fi
  export HOME=/home/ue4
  mkdir -p /home/ue4/.config; [ -L /home/ue4/.config/Epic ] || ln -sfn /project/ue/home/Epic /home/ue4/.config/Epic
  echo RUNNING > "$ST"; date +%s > "$WORK/package.start"
  setsid nohup bash -c '
    echo $$ > '"$WORK"'/package.pid
    cd '"$ENGINE"' && env UE-LocalDataCachePath=/project/ue/ddc ./Engine/Build/BatchFiles/RunUAT.sh BuildCookRun -project='"$DEMO"'/MurderInc.uproject \
      -noP4 -utf8output -unattended -platform=Linux -clientconfig=Development -target=MurderInc \
      -build -nocompileeditor -UbtArgs=-NoUBA -cook -map=/Game/Maps/L_Block -stage -pak -iostore \
      -archive -archivedirectory='"$OUT"' -prereqs \
      "-AdditionalCookerOptions=-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal) -ini:Engine:[Zen]:AutoLaunch=false -ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1"
    rc=$?; date +%s > '"$WORK"'/package.end
    if [ $rc -eq 0 ]; then echo OK > '"$ST"'; else echo FAILED > '"$ST"'; fi' </dev/null >"$LOG" 2>&1 &
  echo "PACKAGE started: poll package.sh status (log $LOG)"
}

stop() {
  local p; p=$(cat "$WORK/package.pid" 2>/dev/null)
  [ -n "$p" ] && kill -- -"$p" 2>/dev/null; echo STOPPED > "$ST"; echo "package run $p stopped"
}

status() {
  local s; s=$(cat "$ST" 2>/dev/null || echo NONE)
  local t0; t0=$(cat "$WORK/package.start" 2>/dev/null || date +%s)
  local t1; t1=$(cat "$WORK/package.end" 2>/dev/null || date +%s)
  echo "PACKAGE $s after $(( (t1 - t0) / 60 )) min"
  grep -E 'BUILD (SUCCESSFUL|FAILED)|Error:|ERROR:|Cook.*(Done|complete)|Packages Cooked|AutomationTool exiting' "$LOG" 2>/dev/null | tail -8 | cut -c1-300
  tail -3 "$LOG" 2>/dev/null | cut -c1-300
}

case "$1" in
  snapshot) snapshot ;;
  start) start ;;
  status) status ;;
  stop) stop ;;
  *) sed -n 2,12p "$0"; exit 2 ;;
esac
