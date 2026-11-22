#!/bin/bash
# LOCAL side of the art transfer (runs in the local checkout, not on the box).
# The Blender outputs (art/out/, git-ignored) reach the box through the user's Higgsfield storage, not through git:
#   1. send-art.sh pack [pattern ...]     tar of the GLBs whose names match (default: the El, the street kit and the
#                                         hydrant), every texture set their slots use (BC, N, ORM; no height maps),
#                                         the grey-box sets below and art/out/manifest.json -> art/out/mi-art.tar
#   2. the agent calls mcp__Higgsfield__media_upload with filename mi-art-<date>.tar: it returns upload_url, url
#      and the content type it expects (application/x-tar)
#   3. send-art.sh put <upload_url> [content_type]     PUT the tar (retries with If-None-Match: * on 403)
#   4. the agent calls mcp__Higgsfield__media_confirm with the media_id and type "file"
#   5. on the box: tools/box/receive-art.sh <url>   (downloads and unpacks under /project/ue/art-in/)
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1
TAR=art/out/mi-art.tar
# Sets the level needs although no mesh slot names them: the grey-box massing of build_block.py.
EXTRA_SETS="TS_Brick_ScanRedCommon TS_Concrete_ScanWeathered"

case "${1:-}" in
  pack)
    shift
    [ $# -gt 0 ] || set -- 'SM_El_*' 'SM_Street_*' 'SM_Prop_Hydrant'
    python3 - "$TAR" "$EXTRA_SETS" "$@" <<'PY' || exit 1
import fnmatch, json, os, sys, tarfile
out, extra, patterns = sys.argv[1], sys.argv[2].split(), sys.argv[3:]
root = "art/out"
manifest = json.load(open(os.path.join(root, "manifest.json")))
files, sets, missing = ["manifest.json"], set(extra), []
for name, asset in sorted(manifest["assets"].items()):
    if not any(fnmatch.fnmatch(name, p) for p in patterns) or not asset.get("glb"):
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
with tarfile.open(out, "w") as tar:
    for f in files:
        tar.add(os.path.join(root, f), arcname=f)
print("PACK OK %s: %d files, %d GLBs, %d texture sets, %.1f MB" % (
    out, len(files), sum(f.endswith(".glb") for f in files), len(sets), os.path.getsize(out) / 1e6))
for m in missing:
    print("  missing: " + m)
PY
    ;;
  put)
    url=${2:-}; ct=${3:-application/x-tar}
    [ -n "$url" ] && [ -f "$TAR" ] || { echo "usage: send-art.sh put <upload_url> [content_type] (after pack)"; exit 2; }
    code=$(curl -sS -o /tmp/mi-art-put.out -w '%{http_code}' -X PUT -H "Content-Type: $ct" --data-binary @"$TAR" "$url")
    if [ "$code" = 403 ]; then
      code=$(curl -sS -o /tmp/mi-art-put.out -w '%{http_code}' -X PUT -H "Content-Type: $ct" -H 'If-None-Match: *' --data-binary @"$TAR" "$url")
    fi
    echo "PUT $code $(stat -c %s "$TAR") bytes $TAR"
    [ "$code" = 200 ] || { head -c 300 /tmp/mi-art-put.out; echo; exit 1; }
    ;;
  *)
    echo "usage: send-art.sh pack [mesh name pattern ...] | put <upload_url> [content_type]"; exit 2 ;;
esac
