#!/bin/bash
# The owner's browser on the box's desktop: a Firefox window the owner signs in to (E3DS's control panel), which this
# script can then put under remote control, so that settings are changed, a test session is watched and a build is
# uploaded from the box itself. The owner opens the desktop ("Open desktop" on the box's rental) and types the
# password there: it is never asked for, typed, read or saved by anything here. Run as root on the box.
#
#   owner-browser.sh plain [url]   a plain browser for the sign-in (not under remote control: a sign-in with Google
#                                  refuses a controlled browser). Default url: E3DS's control panel.
#   owner-browser.sh control       the same browser, restarted under remote control with the same profile (the
#                                  session is restored: still signed in)
#   owner-browser.sh stop          close it; the profile, and with it the sign-in, stays
#   owner-browser.sh wipe          close it and delete the profile (signed out everywhere, nothing left on the box)
#   owner-browser.sh ff ARGS       owner-browser.py: tabs | text [n] | inv | goto URL | eval FILE.js [json] | shot OUT.png
#   owner-browser.sh state         what runs now
#
# The profile is /tmp/e3ds-owner-browser/profile: /tmp is lost when the box stops. Saving passwords and form history
# is off. The browser draws in software (deskctl run --software, no hardware video decoding): it puts no load on the
# GPU a lag test measures. The page's console goes to the browser's log (devtools.console.stdout.content): that is
# where a stream page prints the game's log when E3DS's "Print UE log in browser console" is on.
B=/tmp/e3ds-owner-browser
T=$(dirname "$(readlink -f "$0")")
FF=/opt/firefox/firefox
URL=https://controlpanel.eagle3dstreaming.com/

pids() { pgrep -f "[/]opt/firefox/firefox --profile $B/profile"; }

setup() {
  mkdir -p "$B/profile" && chmod 700 "$B"
  cat > "$B/profile/user.js" <<'EOF'
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("startup.homepage_welcome_url", "");
user_pref("startup.homepage_welcome_url.additional", "");
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("datareporting.healthreport.uploadEnabled", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("browser.tabs.warnOnClose", false);
user_pref("browser.warnOnQuit", false);
user_pref("signon.rememberSignons", false);
user_pref("signon.autofillForms", false);
user_pref("browser.formfill.enable", false);
user_pref("browser.startup.page", 3);
user_pref("browser.sessionstore.resume_from_crash", true);
user_pref("layers.acceleration.disabled", true);
user_pref("gfx.webrender.software", true);
user_pref("media.hardware-video-decoding.enabled", false);
user_pref("devtools.console.stdout.content", true);
user_pref("browser.translations.automaticallyPopup", false);
user_pref("extensions.pocket.enabled", false);
user_pref("app.update.auto", false);
EOF
  [ -x "$B/venv/bin/python" ] && "$B/venv/bin/python" -c 'import marionette_driver' 2>/dev/null && return 0
  python3 -m venv "$B/venv" && "$B/venv/bin/pip" -q install marionette_driver
}

stop() {  # ask the window to close (a clean quit writes the session), then wait; TERM only if it stays
  local w i
  for w in $(wmctrl -l 2>/dev/null | grep 'Mozilla Firefox' | cut -d' ' -f1); do wmctrl -ic "$w"; done
  for i in $(seq 1 20); do [ -z "$(pids)" ] && return 0; sleep 0.5; done
  pids | xargs -r kill -TERM; sleep 2
}

start() {  # [--marionette] [url]
  local out; out=$(deskctl run --software "$FF" --profile "$B/profile" --no-remote --width 1480 --height 940 "$@" 2>&1)
  echo "$out" | sed -n 's/.*"log": "\([^"]*\)".*/\1/p' > "$B/log.path"
  local i; for i in $(seq 1 30); do deskctl windows 2>/dev/null | grep -q 'Mozilla Firefox' && break; sleep 0.5; done
}

case "$1" in
  plain)
    setup || exit 1; stop
    if [ -f "$B/profile/sessionstore.jsonlz4" ]; then start; else start "${2:-$URL}"; fi
    deskctl windows ;;
  control)
    setup || exit 1; stop; start --marionette
    for i in $(seq 1 30); do (exec 3<>/dev/tcp/127.0.0.1/2828) 2>/dev/null && break; sleep 0.5; done
    "$B/venv/bin/python" "$T/owner-browser.py" tabs ;;
  stop) stop; echo "running: $(pids | wc -l)" ;;
  wipe) stop; pids | xargs -r kill -KILL 2>/dev/null; rm -rf "$B"; echo "profile deleted" ;;
  ff) shift; "$B/venv/bin/python" "$T/owner-browser.py" "$@" ;;
  state)
    echo "browser processes: $(pids | wc -l); log: $(cat "$B/log.path" 2>/dev/null)"
    (exec 3<>/dev/tcp/127.0.0.1/2828) 2>/dev/null && echo "under remote control" || echo "plain (not under remote control)"
    deskctl windows ;;
  *) sed -n '2,17p' "$0" ;;
esac
