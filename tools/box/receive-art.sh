#!/bin/bash
# BOX side of the art transfer: download the tar that send-art.sh put into the user's Higgsfield storage and unpack
# it under /project/ue/art-in/ (manifest.json, glb/, textures/<Set>/). Replaces what was there.
# Usage: receive-art.sh <url>      the permanent url that media_upload returned
url=${1:-}
[ -n "$url" ] || { echo "usage: receive-art.sh <url>"; exit 2; }
dest=/project/ue/art-in
tmp=$(mktemp /tmp/mi-art-XXXXXX.tar)
code=$(curl -sSL -o "$tmp" -w '%{http_code}' "$url")
[ "$code" = 200 ] || { echo "RECEIVE FAILED: HTTP $code"; rm -f "$tmp"; exit 1; }
tar -tf "$tmp" >/dev/null 2>&1 || { echo "RECEIVE FAILED: not a tar ($(stat -c %s "$tmp") bytes)"; rm -f "$tmp"; exit 1; }
rm -rf "$dest.new" && mkdir -p "$dest.new" && tar -xf "$tmp" -C "$dest.new" || { echo "RECEIVE FAILED: unpack"; exit 1; }
rm -rf "$dest" && mv "$dest.new" "$dest"
chown -R ue4 "$dest" 2>/dev/null
rm -f "$tmp"
echo "RECEIVE OK $dest: $(ls "$dest/glb" | wc -l) GLBs, $(ls "$dest/textures" | wc -l) texture sets, $(du -sm "$dest" | cut -f1) MB"
