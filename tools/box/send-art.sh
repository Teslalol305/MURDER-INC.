#!/bin/bash
# LOCAL side of the art transfer (runs in the local checkout, not on the box).
# The Blender outputs (art/out/, git-ignored) reach the box through the user's Higgsfield storage, not through git:
#   1. send-art.sh pack [pattern ...]     tar of the GLBs whose names match (default: every SM_* the level uses: the
#                                         El, the street kit, the facade kit, the props, the furniture), every texture set their
#                                         slots use (BC, N, ORM; no height maps), the grey-box sets below,
#                                         art/out/manifest.json and art/out/placements/*.json (art/blender/
#                                         place_buildings.py) -> art/out/mi-art-<k>.tar
#   2. the agent calls mcp__Higgsfield__media_upload with filename mi-art-<date>.tar: it returns upload_url, url
#      and the content type it expects (application/x-tar)
#   3. send-art.sh put <upload_url> [content_type] [part]   PUT one part (art/out/mi-art-<k>.tar, at most 240 MB:
#                                         the storage refuses bodies over about 500 MB); one media_upload per part
#   4. the agent calls mcp__Higgsfield__media_confirm with the media_id and type "file"
#   5. on the box: tools/box/receive-art.sh <url>   (downloads and unpacks under /project/ue/art-in/)
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1
TAR=art/out/mi-art.tar
# Sets the level needs although no mesh slot names them: the grey-box massing of build_block.py.
EXTRA_SETS="TS_Brick_ScanRedCommon TS_Concrete_ScanWeathered TS_Concrete_ScanRough TS_Asphalt_ScanWorn"

case "${1:-}" in
  pack)
    shift
    # The new levels' art (families chinatown and midtown: SM_*_CT_*, SM_Roof_*, SM_Scaf_*, SM_Sign_LEDWall_*,
    # SM_Sign_Ticker_4m, SM_Sign_TowerStack, their atlases and placements) is left out unless `--maps` comes first:
    # the default patterns SM_Facade_*, SM_Prop_* and SM_Sign_* would otherwise carry it into a release's art pack
    # (MAPS.md lane B; the release in progress must not change). A maps pack: send-art.sh pack --maps 'SM_*_CT_*' ...
    MAPS=0
    if [ "${1:-}" = "--maps" ]; then MAPS=1; shift; fi
    [ $# -gt 0 ] || set -- 'SM_El_*' 'SM_Street_*' 'SM_Facade_*' 'SM_Prop_*' 'SM_Gameplay_*' 'SM_Furn_*' 'SM_Struct_*' 'SM_Sign_*' 'SM_Vehicle_*'
    python3 - "$TAR" "$EXTRA_SETS" "$MAPS" "$@" <<'PY' || exit 1
import fnmatch, json, os, sys, tarfile
out, extra, maps, patterns = sys.argv[1], sys.argv[2].split(), sys.argv[3] == "1", sys.argv[4:]
MAP_FAMILIES = {"chinatown", "midtown"}
root = "art/out"
manifest = json.load(open(os.path.join(root, "manifest.json")))
files, sets, missing = ["manifest.json"], set(extra), []
if os.path.isdir(os.path.join(root, "placements")):
    files += [os.path.join("placements", f) for f in sorted(os.listdir(os.path.join(root, "placements")))
              if f.endswith(".json") and (maps or not any(f == "placements_%s.json" % m for m in MAP_FAMILIES))]
for name, asset in sorted(manifest["assets"].items()):
    if not any(fnmatch.fnmatch(name, p) for p in patterns) or not asset.get("glb"):
        continue
    if asset.get("family") in MAP_FAMILIES and not maps:
        continue
    if not os.path.exists(os.path.join(root, asset["glb"])):
        missing.append(asset["glb"]); continue
    files.append(asset["glb"])
    for slot in asset.get("material_slots", []):
        sets.update(s for s in (slot.get("set"), slot.get("blend_set_G")) if s)
for name in sorted(sets):
    folder = os.path.join("textures", name)
    if not os.path.isdir(os.path.join(root, folder)):
        missing.append(folder + "/ (no texture set: the importer gives the slot a flat stand-in)"); continue
    for f in sorted(os.listdir(os.path.join(root, folder))):
        if "_H." in f:
            continue
        files.append(os.path.join(folder, f))
# The storage's upload front refuses bodies over about 500 MB (HTTP 413 at 611 MB): parts of at most 240 MB.
LIMIT = 240e6
parts, size = [[]], 0
for f in files:
    s = os.path.getsize(os.path.join(root, f))
    if parts[-1] and size + s > LIMIT:
        parts.append([]); size = 0
    parts[-1].append(f); size += s
for old in os.listdir(root):
    if old.startswith("mi-art") and old.endswith(".tar"):
        os.remove(os.path.join(root, old))
for k, part in enumerate(parts, 1):
    path = out.replace(".tar", "-%d.tar" % k)
    with tarfile.open(path, "w") as tar:
        for f in part:
            tar.add(os.path.join(root, f), arcname=f)
    print("PART %s: %d files, %.1f MB" % (path, len(part), os.path.getsize(path) / 1e6))
print("PACK OK %d parts: %d files, %d GLBs, %d texture sets" % (
    len(parts), len(files), sum(f.endswith(".glb") for f in files), len(sets)))
for m in missing:
    print("  missing: " + m)
PY
    ;;
  put)
    url=${2:-}; ct=${3:-application/x-tar}; TAR=${4:-art/out/mi-art-1.tar}
    [ -n "$url" ] && [ -f "$TAR" ] || { echo "usage: send-art.sh put <upload_url> [content_type] [part tar] (after pack)"; exit 2; }
    code=$(curl -sS -o /tmp/mi-art-put.out -w '%{http_code}' -X PUT -H "Content-Type: $ct" --data-binary @"$TAR" "$url")
    if [ "$code" = 403 ]; then
      code=$(curl -sS -o /tmp/mi-art-put.out -w '%{http_code}' -X PUT -H "Content-Type: $ct" -H 'If-None-Match: *' --data-binary @"$TAR" "$url")
    fi
    echo "PUT $code $(stat -c %s "$TAR") bytes $TAR"
    [ "$code" = 200 ] || { head -c 300 /tmp/mi-art-put.out; echo; exit 1; }
    ;;
  *)
    echo "usage: send-art.sh pack [mesh name pattern ...] | put <upload_url> [content_type] [part tar]"; exit 2 ;;
esac
