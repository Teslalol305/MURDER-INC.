#!/bin/bash
# The six reference views of L_Block (docs/unreal/shots/block-v1-*.jpg), taken in the running editor with the
# block map open (block.sh start level, or editor.sh start /Game/Maps/L_Block).
# Usage: block-shots.sh [out_dir] [frames] [prefix]   default /project/ue/logs/shots, 60 warm-up redraws, block-v1
# About 12 s per view: run it detached (setsid nohup ... &) when a call is limited to 45 s.
out=${1:-/project/ue/logs/shots}; frames=${2:-60}; p=${3:-block-v1}
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
# 1 eye level at the player start (level.json playerStart: feet Z 15 + 165 cm eye), looking east along the avenue
bash shot.sh "$out/$p-1.jpg" cam=-3740,815,180,0,-4.6,0 fov=90 frames="$frames" | tail -1
# 2 the south block face (s1, s2) from the north sidewalk, between the kiosk and the parked van
bash shot.sh "$out/$p-2.jpg" cam=-2500,-980,170,8,100,0 fov=80 frames="$frames" | tail -1
# 3 the pizza shop front (s1) up close, from beside the phone booth
bash shot.sh "$out/$p-3.jpg" cam=-3050,900,165,2,140,0 fov=70 frames="$frames" | tail -1
# 4 under the deck, looking up and west at the bent at X -1500
bash shot.sh "$out/$p-4.jpg" cam=-1250,250,160,24,170,0 fov=85 frames="$frames" | tail -1
# 5 the avenue from mid-block, looking west under the El
bash shot.sh "$out/$p-5.jpg" cam=600,-300,170,0,180,0 fov=85 frames="$frames" | tail -1
# 6 high overview of the whole block from the south-west, the sun behind the camera
bash shot.sh "$out/$p-6.jpg" cam=-7200,6200,5200,-28.7,-40.7,0 fov=70 frames="$frames" | tail -1
