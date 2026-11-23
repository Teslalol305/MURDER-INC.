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
set -u
case "${1:-}" in
  pack)
    cd "$(dirname "${BASH_SOURCE[0]}")/../../.." || exit 1
    O=art/out; S=$O/fp-stage; rm -rf $S; mkdir -p $S/glb $S/textures
    cp_set() { mkdir -p $S/textures/$1; for k in BC N ORM E A; do [ -f $O/textures/$1/T_$1_$k.png ] && cp $O/textures/$1/T_$1_$k.png $S/textures/$1/; done; return 0; }
    # characters
    cp $O/glb/SK_RuleArms.glb $O/glb/SK_RuleArms.sockets.json $O/glb/SM_Character_RuleBracelet.glb $O/glb/SM_Character_RuleWatch.glb $S/glb/
    cp_set RuleArms_Skin
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
  put)
    url=$2; tar=$3
    for i in 1 2 3; do
      code=$(curl -sS -o /dev/null -w '%{http_code}' -X PUT -H 'Content-Type: application/octet-stream' -H 'If-None-Match: *' --data-binary @"$tar" "$url")
      [ "$code" = 200 ] && { echo "PUT OK $tar"; exit 0; }
      echo "PUT $code, retry"; sleep 3
    done
    exit 1 ;;
  unpack)
    shift; D=/project/ue/fp-in; mkdir -p $D
    for url in "$@"; do
      tmp=$(mktemp /tmp/fp-XXXXXX.tar)
      code=$(curl -sSL -o "$tmp" -w '%{http_code}' "$url"); [ "$code" = 200 ] || { echo "UNPACK FAILED: HTTP $code"; exit 1; }
      tar -xf "$tmp" -C $D || { echo "UNPACK FAILED: tar"; exit 1; }
      rm -f "$tmp"
    done
    chown -R ue4 $D 2>/dev/null
    echo "UNPACK OK $D: $(ls $D/glb | wc -l) files in glb, $(ls $D/textures | wc -l) texture sets, $(du -sm $D | cut -f1) MB" ;;
  *) echo "usage: fp-art.sh pack | put <upload_url> <tar> | unpack <url> [url ...]"; exit 2 ;;
esac
