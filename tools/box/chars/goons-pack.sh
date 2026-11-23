#!/bin/bash
# Local: pack the three Goons for the scratch project (art/out/goons-ue.tar: SK_Goon_*.glb, tex/T_Goon*_{BC,N,ORM}.png,
#        tex/T_GoonFabric_Detail_N.png and goons_ue.json: the detail normal's tiling per set).
# Box:   receive with  goons-pack.sh unpack <url>   (into /project/ue/chars/in/goons, then mi_chars.setup_goons()).
set -e
case "${1:-pack}" in
  pack)
    cd "$(dirname "$0")/../../.."
    S=art/out/goons_ue; rm -rf $S; mkdir -p $S/tex
    cp art/out/glb/SK_Goon_Hoodie.glb art/out/glb/SK_Goon_Puffer.glb art/out/glb/SK_Goon_Tracksuit.glb $S/
    for d in art/out/textures/Goon*_Cloth art/out/textures/Goon*_Head; do cp $d/T_*_BC.png $d/T_*_N.png $d/T_*_ORM.png $S/tex/; done
    cp art/out/textures/GoonFabric_Detail/T_GoonFabric_Detail_N.png $S/tex/
    cp art/out/goons/goons_ue.json $S/
    tar -cf art/out/goons-ue.tar -C $S . && ls -la art/out/goons-ue.tar ;;
  unpack)
    D=/project/ue/chars/in/goons; mkdir -p $D; cd $D
    curl -sSfL -o /tmp/goons-ue.tar "$2" && rm -rf tex *.glb && tar -xf /tmp/goons-ue.tar && chown -R ue4 $D && ls -la $D $D/tex | head -30 ;;
esac
