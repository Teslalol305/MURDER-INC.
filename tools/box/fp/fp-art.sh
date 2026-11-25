#!/bin/bash
# The first-person and enemy art the game project needs from art/out/ (git-ignored: the arms and Goons are skinned
# on Epic's skeleton), carried to the box through the user's Higgsfield storage, never through git.
# It never touches /project/ue/art-in (the level's art, receive-art.sh): everything lands in /project/ue/fp-in.
#
#   local:  tools/box/fp/fp-art.sh pack                 -> art/out/fp-chars.tar (arms, bracelet, watch, three Goons)
#                                                          art/out/fp-guns.tar  (NINE, its magazine, the Goon SMG, Buzzard)
#           (agent: mcp__Higgsfield__media_upload with one filename per tar -> upload_url, url, media_id)
#   local:  tools/box/fp/fp-art.sh put <upload_url> <tar>   (PUT with If-None-Match: *, as send-art.sh)
#           (agent: mcp__Higgsfield__media_confirm, type file)
#   box:    bash tools/box/fp/fp-art.sh unpack <url> [url ...]   -> /project/ue/fp-in/{glb,textures,goons_ue.json}
#   box:    bash tools/box/fp/import-chars.sh [arms|goons|guns|all]   (the game project's editor stopped)
#
# Re-run all four steps whenever the character agents re-export SK_RuleArms or the Goons: the import replaces the
# assets in place, so the game picks the new versions up with no data change.
#
# Weapons round 4 (the five own guns, their magazines and the parts kit):
#   local:  tools/box/fp/fp-art.sh packr4 [guns] [rattler] [parts]
#                -> art/out/fp-weapons-r4-guns.tar    (SK_Chopper, SK_Nine, SK_Shorty, SK_Stretch, their magazines and sets, the brass,
#                                                      the tiling detail sets TS_GunDetail_Steel and TS_GunDetail_Polymer)
#                   art/out/fp-weapons-r4-rattler.tar (SK_Rattler, its magazine and sets: re-carried alone when its final bake lands)
#                   art/out/fp-weapons-r4-parts.tar   (SM_Part_* with their sockets, the part and magazine sets, manifest.json,
#                                                      weapons_r4.json and the icons when they exist)
#   box:    FP_IN=/project/ue/fp-in-guns bash tools/box/fp/fp-art.sh unpack <url> [url ...]
#           (a folder of its own: /project/ue/fp-in is read by other clones; the importer reads the same variable, MI_FP_IN)
#   box:    MI_FP_IN=/project/ue/fp-in-guns bash tools/box/fp/import-chars.sh r4
set -u
case "${1:-}" in
  pack)
    cd "$(dirname "${BASH_SOURCE[0]}")/../../.." || exit 1
    O=art/out; S=$O/fp-stage; rm -rf $S; mkdir -p $S/glb $S/textures
    cp_set() { mkdir -p $S/textures/$1; for k in BC N ORM E A; do [ -f $O/textures/$1/T_$1_$k.png ] && cp $O/textures/$1/T_$1_$k.png $S/textures/$1/; done; return 0; }
    # characters
    cp $O/glb/SK_RuleArms.glb $O/glb/SK_RuleArms.sockets.json $O/glb/SM_Character_RuleBracelet.glb $O/glb/SM_Character_RuleWatch.glb $S/glb/
    cp_set RuleArms_Skin; cp $O/textures/RuleArms_Skin/T_RuleArms_SkinDetail_N.png $S/textures/RuleArms_Skin/ 2>/dev/null
    for g in Hoodie Puffer Tracksuit; do cp $O/glb/SK_Goon_$g.glb $S/glb/; cp_set Goon${g}_Cloth; cp_set Goon${g}_Head; done
    cp_set GoonFabric_Detail; cp $O/goons/goons_ue.json $S/ 2>/dev/null
    tar -cf $O/fp-chars.tar -C $S . && ls -la $O/fp-chars.tar
    rm -rf $S; mkdir -p $S/glb $S/textures
    # guns and the drone
    cp $O/glb/SK_Nine.glb $O/glb/SM_Weapon_NineMagazine.glb $O/glb/SM_Weapon_NineMagazine_TopRound.glb $O/glb/SM_Weapon_GoonSMG.glb \
       $O/glb/SM_Weapon_GoonSMG_Magazine.glb $O/glb/SK_Buzzard.glb $S/glb/
    for s in Nine Weapon_NineMagazine Weapon_GoonSMG Buzzard; do cp_set $s; done
    tar -cf $O/fp-guns.tar -C $S . && ls -la $O/fp-guns.tar
    rm -rf $S ;;
  packr4)
    # packr4 [guns] [rattler] [parts]   (default: all three); each group is one tar under 240 MB, so a group that the
    # modelers re-export later is carried again alone: art/out/fp-weapons-r4-<group>.tar
    cd "$(dirname "${BASH_SOURCE[0]}")/../../.." || exit 1
    O=art/out; S=$O/fp-stage-r4; shift; groups=${*:-guns rattler parts}
    cp_set() { mkdir -p $S/textures/$1; for k in BC N ORM E A; do [ -f $O/textures/$1/T_$1_$k.png ] && cp $O/textures/$1/T_$1_$k.png $S/textures/$1/; done
               [ -f $O/textures/$1/set.json ] && cp $O/textures/$1/set.json $S/textures/$1/; return 0; }
    cp_mag() { cp $O/glb/SM_Weapon_${1}Magazine.glb $O/glb/SM_Weapon_${1}Magazine_TopRound.glb $S/glb/ 2>/dev/null; cp_set Weapon_${1}Magazine; }
    for g in $groups; do
      rm -rf $S; mkdir -p $S/glb $S/textures $S/ui
      case $g in
        guns)    # the four finished guns (the CHOPPER has three sets), their magazines and the brass
          for n in Chopper Nine Shorty Stretch; do cp $O/glb/SK_$n.glb $S/glb/; cp_mag $n; done
          for s in Chopper Chopper_Front Chopper_Furniture Nine Shorty Stretch; do cp_set $s; done
          cp_set TS_GunDetail_Steel; cp_set TS_GunDetail_Polymer     # the tiling detail (manifest detail_set*), 1024 px each
          cp $O/glb/SM_Weapon_CasingRifle.glb $O/glb/SM_Weapon_CasingPistol.glb $S/glb/ 2>/dev/null; cp_set Weapon_CasingRifle; cp_set Weapon_CasingPistol ;;
        rattler) cp $O/glb/SK_Rattler.glb $S/glb/; cp_mag Rattler; cp_set Rattler; cp_set TS_GunDetail_Steel ;;
        parts)   # the parts kit with its sockets, the contract and the icons
          cp $O/glb/SM_Part_*.glb $O/glb/SM_Part_*.sockets.json $S/glb/ 2>/dev/null
          cp_set Weapon_Parts; cp_set Weapon_PartsMags
          cp $O/manifest.json $S/manifest.json 2>/dev/null; cp $O/weapons_r4.json $S/weapons_r4.json 2>/dev/null
          cp $O/ui/T_UI_Gun_*.png $O/ui/T_UI_Att_*.png $S/ui/ 2>/dev/null ;;
        *) echo "packr4: unknown group $g"; exit 2 ;;
      esac
      rmdir $S/ui 2>/dev/null
      tar -cf $O/fp-weapons-r4-$g.tar -C $S . && ls -la $O/fp-weapons-r4-$g.tar
    done
    rm -rf $S ;;
  put)
    url=$2; tar=$3
    for i in 1 2 3; do
      code=$(curl -sS -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/octet-stream' -H 'If-None-Match: *' --data-binary @"$tar" "$url")
      [ "$code" = 200 ] && { echo "PUT OK $tar"; exit 0; }
      echo "PUT $code, retry"; sleep 3
    done
    exit 1 ;;
  unpack)
    shift; D=${FP_IN:-/project/ue/fp-in}; mkdir -p $D
    for url in "$@"; do
      tmp=$(mktemp /tmp/fp-XXXXXX.tar)
      code=$(curl -sSL -o "$tmp" -w '%{http_code}' "$url"); [ "$code" = 200 ] || { echo "UNPACK FAILED: HTTP $code"; exit 1; }
      tar -xf "$tmp" -C $D || { echo "UNPACK FAILED: tar"; exit 1; }
      rm -f "$tmp"
    done
    chown -R ue4 $D 2>/dev/null
    echo "UNPACK OK $D: $(ls $D/glb | wc -l) files in glb, $(ls $D/textures | wc -l) texture sets, $(du -sm $D | cut -f1) MB" ;;
  *) echo "usage: fp-art.sh pack | packr4 | put <upload_url> <tar> | unpack <url> [url ...]  (unpack: FP_IN=<folder> to change /project/ue/fp-in)"; exit 2 ;;
esac
