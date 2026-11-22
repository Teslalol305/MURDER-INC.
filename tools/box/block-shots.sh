#!/bin/bash
# The four reference views of L_Block (docs/unreal/shots/block-v0-*.jpg), taken in the running editor with the
# block map open (block.sh start level, or editor.sh start /Game/Maps/L_Block).
# Usage: block-shots.sh [out_dir] [frames]     default /project/ue/logs/shots, 60 warm-up redraws per view
# About 12 s per view: run it detached (setsid nohup ... &) when a call is limited to 45 s.
out=${1:-/project/ue/logs/shots}; frames=${2:-60}
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
# 1 eye level at the player start (level.json playerStart: feet Z 15 + 165 cm eye), looking east along the avenue
bash shot.sh "$out/block-v0-1.jpg" cam=-3740,815,180,0,-4.6,0 fov=90 frames="$frames" | tail -1
# 2 a south-row column and its pedestal from the south-west, on its sunlit faces
bash shot.sh "$out/block-v0-2.jpg" cam=3200,790,150,-5,-47.7,0 fov=70 frames="$frames" | tail -1
# 3 under the deck, looking up and west at the bent at X -1500
bash shot.sh "$out/block-v0-3.jpg" cam=-1250,250,160,24,170,0 fov=85 frames="$frames" | tail -1
# 4 high overview of the whole block from the south-west, the sun behind the camera
bash shot.sh "$out/block-v0-4.jpg" cam=-7200,6200,5200,-28.7,-40.7,0 fov=70 frames="$frames" | tail -1
