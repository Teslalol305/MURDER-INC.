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
#   import-animpack.sh <Project.uproject> guns      the six rifles (3 lengths x irons up / folded), every part, the
#                                                   magazines, the pack's 4K materials, the scope reticle, the loadout
#                                                   sockets and the UI icons (needs `pack` first for the two skeletons):
#                                                   bl_measure.py + bl_icons.py (bpy at /opt/blpy; without it the
#                                                   committed pack_measure.json and any icons already rendered are
#                                                   used), then ue_import_guns.py headless -> /Game/ThirdParty/InfimaTFA/
#                                                   Weapon{,/Attachments,/Materials,/Textures}, /Game/UI/Icons
#   import-animpack.sh <Project.uproject> all       pack + guns
#   import-animpack.sh <Project.uproject> chopper   re-import a re-exported CHOPPER and rebuild its whole adaptation:
#                                                   CHOPPER_IN=<dir with glb/SK_Chopper.glb, glb/SM_Weapon_Chopper*.glb,
#                                                   textures/Chopper...> (default /project/ue/animpack/in) ->
#                                                   mi_stage.import_chopper, mi_run.adapt_all + parts_all, and in the
#                                                   scratch project export_all (adapted/ .uasset + FBX + manifest)
# ONLY=<substring> limits `pack` to the matching clips (a quick test). Logs: /project/ue/logs/animpack/import-<mode>.log; the last line is MI-DONE (or a Python error).
set -e
UP=$1; MODE=${2:-pack}
PACK=${PACK:-/project/ue/packs/tactical-rifle/FBX_Files_TacticalAssaultRifle}
ADAPTED=${ADAPTED:-/project/ue/packs/tactical-rifle/adapted}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$UP" ] || { echo "usage: import-animpack.sh <Project.uproject> pack|adapted|adapt|guns|all|chopper"; exit 2; }
if [ "$(id -un)" != ue4 ] && { [ "$MODE" = guns ] || [ "$MODE" = all ]; }; then
  # bpy lives in root's uv tree (/opt/blpy -> /root/.local/...): the Blender steps run here, before the switch to ue4
  BL=${BL:-/opt/blpy/bin/python}; FACTS=${FACTS:-/project/ue/animpack/facts}; ICONS=${MI_ICONS:-/project/ue/animpack/icons}
  BLEND=${BLEND:-/project/ue/packs/tactical-rifle/Blender_Source_Files_TacticalAssaultRifle/Rigs/RIG_InfimaGames_TFA_AssaultRifle.blend}
  LOG=/project/ue/logs/animpack; mkdir -p $LOG
  if [ -x "$BL" ]; then
    mkdir -p "$FACTS" "$ICONS"
    [ -f "$FACTS/meshes.json" ] || "$BL" -I "$HERE/bl_meshes.py" "$PACK" "$BLEND" "$FACTS/meshes.json" > $LOG/bl_meshes.log 2>&1
    [ -f "$FACTS/rig.json" ] || "$BL" -I "$HERE/bl_rig.py" "$BLEND" "$FACTS/rig.json" > $LOG/bl_rig.log 2>&1
    "$BL" -I "$HERE/bl_measure.py" "$PACK" "$FACTS/meshes.json" "$FACTS/pack_sockets.json" > $LOG/bl_measure.log 2>&1 && echo "measured: $FACTS/pack_measure.json"
    "$BL" -I "$HERE/bl_icons.py" "$PACK" "$ICONS" > $LOG/bl_icons.log 2>&1 && echo "icons: $(ls $ICONS | wc -l) in $ICONS"
    chmod -R a+rX "$FACTS" "$ICONS"
  else
    echo "no bpy at $BL (/project/ue/bl/install.sh makes it): the committed $HERE/pack_measure.json and the icons already in $ICONS are used"
  fi
fi
if [ "$(id -un)" != ue4 ]; then exec su ue4 -c "$(printf '%q ' env MI_ICONS="${MI_ICONS:-/project/ue/animpack/icons}" bash "$0" "$@")"; fi
PROJ=$(dirname "$UP"); LOG=/project/ue/logs/animpack; mkdir -p $LOG
for p in $(pgrep -x UnrealEditor) $(pgrep -x UnrealEditor-Cm); do  # pgrep -x sees 15 characters
  tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -qF "$UP" && { echo "the editor of $UP is running (pid $p): stop it first"; exit 3; }
done
RHI=-NullRHI
[ "$MODE" = guns ] || [ "$MODE" = all ] || [ "$MODE" = chopper ] && RHI="-RenderOffscreen -AllowCommandletRendering"   # materials compile
run() {  # run a Python file headless in the project
  cd /project/ue/UnrealEngine
  env HOME=/home/ue4 'UE-LocalDataCachePath=/project/ue/ddc' ./Engine/Binaries/Linux/UnrealEditor-Cmd "$UP" \
    -run=pythonscript "-script=$1" -unattended -nosplash -NoSound -stdout -FullStdOutLogOutput $RHI \
    '-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal)' \
    '-ini:Engine:[Zen]:AutoLaunch=false' '-ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1' \
    > "$LOG/import-$MODE.log" 2>&1
  grep -E "MI-ANIMPACK|MI-ADAPT|MI-GUNS|MI-DONE|Error: .*Python|Traceback" "$LOG/import-$MODE.log" | cut -c1-300 | tail -5
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
  chopper)
    CIN=${CHOPPER_IN:-/project/ue/animpack/in}
    cat > /tmp/mi-chopper-cmdlet.py <<PY
import sys, json
sys.path.insert(0, "$HERE")
import mi_stage, mi_run
c = mi_stage.import_chopper("$CIN")
a = mi_run.adapt_all()
p = mi_run.parts_all()
e = mi_run.export_all() if "$PROJ" == "/project/ue/animpack" else None
print("MI-ADAPT", json.dumps({"chopper": c.get("SK_Chopper"), "generic": len(a["generic"]), "reloads": len(a["reloads"]),
                              "failed": a["failed"], "parts": len(p["clips"]), "export": e and e.get("character")}))
print("MI-DONE")
PY
    chmod 644 /tmp/mi-chopper-cmdlet.py
    run /tmp/mi-chopper-cmdlet.py ;;
  guns|all)
    if [ "$MODE" = all ]; then MODE=pack; run "$HERE/ue_import_pack.py --pack $PACK --dest /Game/ThirdParty/InfimaTFA${ONLY:+ --only $ONLY}"; MODE=guns; fi
    ICONS=${MI_ICONS:-/project/ue/animpack/icons}
    export MI_ICONS=$ICONS; run "$HERE/ue_import_guns.py --sync"
    grep -E "MI-GUNS" "$LOG/import-guns.log" | tail -1 | cut -c1-600 ;;
  *) echo "mode: pack | adapted | adapt | guns | all | chopper"; exit 2 ;;
esac
