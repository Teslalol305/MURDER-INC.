#!/bin/bash
# Repeat the animation pack's import, and bring in the CHOPPER adaptation, in any Unreal project on the box
# (the game project later; docs/unreal/ANIMATION.md). Nothing it touches may be committed: Fab licence.
#
# Usage (as root or ue4, the project's editor STOPPED):
#   import-animpack.sh <Project.uproject> pack      the pack's 109 character clips on SK_Mannequin (no retargeting),
#                                                   its rifle, magazine and 30 weapon clips as reference
#                                                   -> /Game/ThirdParty/InfimaTFA/{Character,Weapon}
#   import-animpack.sh <Project.uproject> adapted   the adapted clips as built on the box (same engine version):
#                                                   copies /project/ue/packs/tactical-rifle/adapted/uasset/* into
#                                                   Content/ -> /Game/ThirdParty/InfimaTFA/Adapted/{FP,TP} (on
#                                                   /Game/Characters/Mannequins/Meshes/SK_Mannequin) and
#                                                   /Game/Weapons/Chopper/Anims (on /Game/Weapons/Chopper/
#                                                   SK_Chopper_Skeleton: the CHOPPER must be imported there)
#   import-animpack.sh <Project.uproject> adapt     rebuild the adaptation inside the project instead (needs `pack`
#                                                   first and SK_Chopper at /Game/Weapons/Chopper/SK_Chopper):
#                                                   tools/box/anim/mi_run.py adapt_all + parts_all, headless
# ONLY=<substring> limits `pack` to the matching clips (a quick test). Logs: /project/ue/logs/animpack/import-<mode>.log; the last line is MI-DONE (or a Python error).
set -e
UP=$1; MODE=${2:-pack}
PACK=${PACK:-/project/ue/packs/tactical-rifle/FBX_Files_TacticalAssaultRifle}
ADAPTED=${ADAPTED:-/project/ue/packs/tactical-rifle/adapted}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$UP" ] || { echo "usage: import-animpack.sh <Project.uproject> pack|adapted|adapt"; exit 2; }
if [ "$(id -un)" != ue4 ]; then exec su ue4 -c "$(printf '%q ' bash "$0" "$@")"; fi
PROJ=$(dirname "$UP"); LOG=/project/ue/logs/animpack; mkdir -p $LOG
for p in $(pgrep -x UnrealEditor) $(pgrep -x UnrealEditor-Cm); do  # pgrep -x sees 15 characters
  tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -qF "$UP" && { echo "the editor of $UP is running (pid $p): stop it first"; exit 3; }
done
run() {  # run a Python file headless in the project
  cd /project/ue/UnrealEngine
  env HOME=/home/ue4 'UE-LocalDataCachePath=/project/ue/ddc' ./Engine/Binaries/Linux/UnrealEditor-Cmd "$UP" \
    -run=pythonscript "-script=$1" -unattended -nosplash -NoSound -stdout -FullStdOutLogOutput -NullRHI \
    '-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal)' \
    '-ini:Engine:[Zen]:AutoLaunch=false' '-ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1' \
    > "$LOG/import-$MODE.log" 2>&1
  grep -E "MI-ANIMPACK|MI-ADAPT|MI-DONE|Error: .*Python|Traceback" "$LOG/import-$MODE.log" | tail -5
}
case $MODE in
  pack)
    run "$HERE/ue_import_pack.py --pack $PACK --dest /Game/ThirdParty/InfimaTFA${ONLY:+ --only $ONLY}" ;;
  adapted)
    [ -d "$ADAPTED/uasset" ] || { echo "no $ADAPTED/uasset"; exit 4; }
    cp -r "$ADAPTED/uasset/." "$PROJ/Content/"
    echo "copied $(find "$ADAPTED/uasset" -name '*.uasset' | wc -l) assets into $PROJ/Content (manifest: $ADAPTED/manifest.json)" ;;
  adapt)
    cat > /tmp/mi-adapt-cmdlet.py <<PY
import sys, json
sys.path.insert(0, "$HERE")
import mi_run
a = mi_run.adapt_all()
p = mi_run.parts_all()
print("MI-ADAPT", json.dumps({"generic": len(a["generic"]), "reloads": len(a["reloads"]), "failed": a["failed"],
                               "parts": len(p["clips"])}))
print("MI-DONE")
PY
    run /tmp/mi-adapt-cmdlet.py ;;
  *) echo "mode: pack | adapted | adapt"; exit 2 ;;
esac
