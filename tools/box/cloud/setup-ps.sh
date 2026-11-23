#!/bin/bash
# Install, on the box, what the Pixel Streaming 2 test needs (idempotent; everything under /project/ue/cloud so it
# survives a box restart, except the system libraries Chromium needs, which this re-installs):
#   - Node.js 22 (tarball from nodejs.org)
#   - Epic's Pixel Streaming infrastructure, the branch the engine's own get_ps_servers.sh names for this engine
#     (UE5.7: signalling server + web frontend), built with npm
#   - Google Chrome, headless, as the viewer on the box itself (through Playwright)
# Run as root, detached:  setsid nohup bash setup-ps.sh > /project/ue/cloud/setup.log 2>&1 &
# Ends with the line SETUP-PS-DONE (or SETUP-PS-FAILED <step>).
set -u
C=/project/ue/cloud
NODE_V=v22.11.0
BRANCH=${MI_PS_BRANCH:-UE5.7}
mkdir -p "$C" && cd "$C" || exit 1
fail() { echo "SETUP-PS-FAILED $1"; exit 1; }

if [ ! -x "$C/node/bin/node" ]; then
  curl -fsSL "https://nodejs.org/dist/$NODE_V/node-$NODE_V-linux-x64.tar.xz" -o node.tar.xz || fail node-download
  rm -rf node && mkdir node && tar -xJf node.tar.xz -C node --strip-components=1 && rm node.tar.xz || fail node-unpack
fi
export PATH=$C/node/bin:$PATH
echo "node $(node -v)"

if [ ! -f "$C/infra/.mi-built" ]; then
  rm -rf infra && mkdir infra
  curl -fsSL "https://github.com/EpicGamesExt/PixelStreamingInfrastructure/archive/refs/heads/$BRANCH.tar.gz" \
    | tar -xz -C infra --strip-components=1 || fail infra-download
  # Only the parts the test needs (the SFU's mediasoup worker has no prebuilt binary here and compiles for minutes).
  WS="-w Common -w Signalling -w SignallingWebServer -w Frontend/library -w Frontend/ui-library -w Frontend/implementations/typescript"
  (cd infra && npm install --no-audit --no-fund $WS && npm run build:all:cjs) || fail infra-build
  echo "$BRANCH" > infra/.mi-built
fi
echo "infra $(cat infra/.mi-built)"

mkdir -p "$C/pw"
if [ ! -f "$C/pw/node_modules/playwright/package.json" ]; then
  (cd pw && npm init -y >/dev/null && npm install --no-audit --no-fund playwright@1.49.1) || fail playwright
fi
export PLAYWRIGHT_BROWSERS_PATH=$C/pw/browsers
(cd pw && npx playwright install --with-deps chromium) || fail chromium
# Google Chrome as the viewer: the open-source Chromium build cannot decode the H.264 the game streams.
command -v google-chrome >/dev/null || (cd pw && npx playwright install chrome) || fail chrome
echo SETUP-PS-DONE
