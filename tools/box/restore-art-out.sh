#!/bin/bash
# Restore the git-ignored art outputs (art/out/) from the box's persistent backup at /project/backup/art-out/.
#
# The backup was made by tarring each art/out folder locally, splitting into 250 MB parts, sending the parts through
# the user's Higgsfield storage and extracting them on the box; /project/backup/art-out/MANIFEST.txt lists every
# folder with its byte size and sha256. This script is the reverse. The box cannot push to git or to this container,
# so the transfer again goes through Higgsfield storage, driven by the agent:
#
#   1. Box (the box has no checkout of this file: copy it there first, e.g. one gpu_rental_exec with
#      `cat > /project/backup/restore-art-out.sh <<'EOF' ... EOF`), then start the packing detached, since one exec
#      call must finish within about 45 s:
#        setsid nohup bash /project/backup/restore-art-out.sh box-pack [folder ...] \
#          > /project/ue/logs/backup-restore.log 2>&1 < /dev/null &
#      Without folders it packs everything under /project/backup/art-out (ref gen glb blend textures goons goons_ue
#      epic placements manifest.json weapons_partswire.png review packguns-* logs scans hdri). Poll the log: it ends
#      with "sha256 <hex>" and the list of parts in /project/backup/restore/ (250 MB each; the storage answers 413
#      above about 300 MB).
#   2. Agent: mcp__Higgsfield__media_upload with one filename per part, each ending in .tar (files[] takes up to 20),
#      gives upload_url, url and media_id per part.
#   3. Box: PUT each part (several in parallel, each call detached or under 45 s):
#        bash /project/backup/restore-art-out.sh box-put /project/backup/restore/art-out.tar.part-00 "<upload_url>"
#   4. Agent: mcp__Higgsfield__media_confirm with the media_ids and type "file".
#   5. Local (this checkout): download in part order, check the sha256 from step 1, extract into art/out/:
#        tools/box/restore-art-out.sh local-get <sha256> "<url part-00>" "<url part-01>" ...
#   6. Box: rm -rf /project/backup/restore once the local extract printed OK (the backup itself stays).
#
# Subcommands:
#   box-pack [folder ...]          (box)   tar + split -b 250M into /project/backup/restore/, print sha256
#   box-put <part> <upload_url>    (box)   PUT one part to Higgsfield storage, retrying
#   local-get <sha256> <url ...>   (local) download parts, verify, extract into art/out/
set -u
SRC=/project/backup/art-out
OUT=/project/backup/restore
PART_SIZE=250M

put() {  # put <file> <upload_url>: the upload address is signed for these two headers
  local f=$1 u=$2 code a
  for a in 1 2 3 4 5; do
    code=$(curl -sS -o /dev/null -w '%{http_code}' -X PUT -H "Content-Type: application/octet-stream" \
      -H "If-None-Match: *" --upload-file "$f" "$u")
    echo "$(basename "$f") try=$a http=$code"
    [ "$code" = 200 ] && return 0
    sleep 5
  done
  return 1
}

case "${1:-}" in
  box-pack)
    shift
    cd "$SRC" || { echo "no $SRC"; exit 1; }
    [ $# -gt 0 ] || set -- $(ls -A | grep -v '^MANIFEST.txt$')
    mkdir -p "$OUT" && rm -f "$OUT"/art-out.tar.part-*
    tar -cf - "$@" | tee >(sha256sum | cut -d' ' -f1 > "$OUT/art-out.sha256") \
      | split -b "$PART_SIZE" -d -a 2 - "$OUT/art-out.tar.part-" || exit 1
    for i in $(seq 50); do [ -s "$OUT/art-out.sha256" ] && break; sleep 0.2; done
    echo "folders: $*"
    ls -l "$OUT"/art-out.tar.part-*
    echo "sha256 $(cat "$OUT/art-out.sha256")"
    ;;
  box-put)
    [ $# -eq 3 ] || { echo "usage: $0 box-put <part> <upload_url>"; exit 2; }
    put "$2" "$3"
    ;;
  local-get)
    shift
    [ $# -ge 2 ] || { echo "usage: $0 local-get <sha256> <url-part-00> [<url-part-01> ...]"; exit 2; }
    want=$1; shift
    cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1
    tmp=$(mktemp -d "${TMPDIR:-/tmp}/art-restore.XXXX")
    i=0; files=()
    for u in "$@"; do
      f=$tmp/part-$(printf %02d $i); files+=("$f"); i=$((i + 1))
      for a in 1 2 3 4 5; do curl -sS -f -o "$f" "$u" && break; echo "retry $f"; sleep 5; done
    done
    got=$(cat "${files[@]}" | sha256sum | cut -d' ' -f1)
    if [ "$got" != "$want" ]; then echo "FAIL sha256 got=$got want=$want (parts kept in $tmp)"; exit 1; fi
    mkdir -p art/out
    cat "${files[@]}" | tar -xf - -C art/out || { echo "FAIL extract (parts kept in $tmp)"; exit 1; }
    rm -rf "$tmp"
    echo "OK restored into art/out (sha256 $got)"
    ;;
  *)
    sed -n '2,36p' "$0"; exit 2 ;;
esac
