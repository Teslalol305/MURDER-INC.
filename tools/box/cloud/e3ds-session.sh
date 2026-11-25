#!/bin/bash
# One real E3DS stream session driven from the box's browser (owner-browser.sh, the browser the owner signed in with):
# start, the set-up screens by keyboard, a run (story or holdout), a minute or two of fighting, the stream's sound
# level (e3ds-snd.js), the pause card, then back to the control panel (the page is left: the session ends).
#   e3ds-session.sh <label> [story|holdout] [fight-seconds]
# It lives in the browser's tool folder on the box (/tmp/e3ds-owner-browser/tool, with owner-browser.sh, owner-browser.py,
# vid.js, snd.js = e3ds-snd.js) and reads the stream's address from /tmp/e3ds-owner-browser/stream.url (never committed:
# it holds the account's name). Output: <label>.out (what happened), <label>_*.png (pictures), the console log's probe
# lines for e3ds-probesum.py. Start it detached (setsid nohup) and poll <label>.out: a session takes 3 to 5 minutes.
# Measured on version 4 (2026-11-25 13:24 UTC): the picture was up after 112 s; in the holdout run the player died after
# 24 s without a kill (the fight loop does not aim): the numbers of the fight are a sample, not a long run.
cd /tmp/e3ds-owner-browser/tool || exit 1
O=/tmp/e3ds-owner-browser; LBL=${1:-s}; MODE=${2:-story}; FIGHT=${3:-90}
ff() { timeout 90 bash owner-browser.sh ff "$@" 2>&1 | grep -v "^\s*at \|receiveMessage\|^\s*$"; }
say() { echo "$(date -u +%T) $*" | tee -a $O/$LBL.out; }
: > $O/$LBL.out
URL=$(cat $O/stream.url); L=$(cat $O/log.path)
say "session $LBL ($MODE) start; console log $(basename $L)"
ff goto "$URL" > /dev/null
T0=$(date +%s)
for i in $(seq 1 80); do ff eval vid.js | tail -1 | grep -q 'video 1920x1080' && break; sleep 3; done
say "video up after $(( $(date +%s) - T0 )) s"
grep -a '\[MurderInc.sh\]' "$L" | grep -a -E 'build:|leftover|GPU after|CPUs' | sed 's/\\n/ /g; s/console.log: //' | cut -c1-230 | head -6 | tee -a $O/$LBL.out
sleep 4
ff act '[["pclick",0.5,0.5],["wait",2.5]]' > /dev/null
ff shot $O/${LBL}_0.png > /dev/null
if [ "$MODE" = holdout ]; then
  # Home: Down twice = the Mode row, Right = the next mode (Hold the Block), Up twice = back on "Hit the block".
  ff act '[["key","Down"],["wait",0.4],["key","Down"],["wait",0.4],["key","Right"],["wait",0.8],["key","Up"],["wait",0.4],["key","Up"],["wait",0.4]]' > /dev/null
  ff shot $O/${LBL}_home.png > /dev/null
fi
# Enter on Home and Crew, Tab Tab Enter on the Loadout, Tab Enter on Block & Style, Enter on the Briefing.
ff act '[["key","Enter"],["wait",3],["key","Enter"],["wait",3],["key","Tab"],["wait",0.5],["key","Tab"],["wait",0.5],["key","Enter"],["wait",3],["key","Tab"],["wait",0.5],["key","Enter"],["wait",3],["key","Enter"],["wait",9]]' > /dev/null
say "run started?  $(grep -a MICloudProbe "$L" | tail -1 | grep -o 'state=[0-9]* click=[0-9]*' | head -1)"
ff shot $O/${LBL}_run.png > /dev/null
say "sound (4 s): $(ff eval snd.js '[4]' | tail -1)"
# the fight: hold fire, sweep the view, reload, walk
END=$(( $(date +%s) + FIGHT )); N=0
while [ $(date +%s) -lt $END ]; do
  N=$((N+1))
  ff act '[["down"],["jsmove",18,0,30,16],["wait",0.8],["jsmove",-36,0,60,16],["wait",0.8],["jsmove",18,0,30,16],["up"],["key","r"],["wait",1.2],["keydown","w"],["wait",0.8],["keyup","w"]]' > /dev/null
  [ $((N % 3)) = 0 ] && say "sound (3 s): $(ff eval snd.js '[3]' | tail -1)"
done
ff shot $O/${LBL}_fight.png > /dev/null
ff act '[["key","p"],["wait",1.5]]' > /dev/null
ff shot $O/${LBL}_pause.png > /dev/null
say "sound (4 s, paused): $(ff eval snd.js '[4]' | tail -1)"
ff act '[["key","p"],["wait",0.5]]' > /dev/null
ff goto "https://controlpanel.eagle3dstreaming.com/projects?edit=Project_MurderInc" > /dev/null
say "session ended (page left); log lines kept in $(basename $L)"
cp "$L" $O/$LBL.console.log 2>/dev/null
