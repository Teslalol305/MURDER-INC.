#!/bin/bash
# Send a result file from the box to a presigned upload address (the picture transfer of docs/unreal/BOX.md).
# Usage: put.sh <file> <upload_url> [content_type]      content type defaults to image/jpeg
f=$1; url=$2; ct=${3:-image/jpeg}
[ -f "$f" ] && [ -n "$url" ] || { echo "usage: put.sh <file> <upload_url> [content_type]"; exit 2; }
code=$(curl -sS -o /tmp/put.out -w '%{http_code}' -X PUT -H "Content-Type: $ct" --data-binary @"$f" "$url")
if [ "$code" = 403 ]; then
  code=$(curl -sS -o /tmp/put.out -w '%{http_code}' -X PUT -H "Content-Type: $ct" -H 'If-None-Match: *' --data-binary @"$f" "$url")
fi
echo "PUT $code $(stat -c %s "$f") bytes $f"
[ "$code" = 200 ] || { head -c 300 /tmp/put.out; echo; exit 1; }
