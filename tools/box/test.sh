#!/bin/bash
# Run the automation tests headless (no window, no GPU: -NullRHI) in a separate UnrealEditor-Cmd process.
# Usage: test.sh [filter]    start a run (default filter: MurderInc = every MurderInc.* test), wait up to 36 s
#        test.sh status      result of the last run (use this to poll a run that is still going)
# Prints one line: TESTS OK|FAILED|RUNNING passed=N failed=N ..., then every failed test with its first messages.
# Files in /project/ue/logs: test.log (full output), test-report/index.json (the engine's report), test.status.
main() {
  . "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
  mi_become_ue4 "$@"
  local st=$MI_LOGS/test.status log=$MI_LOGS/test.log report=$MI_LOGS/test-report

  if [ "$1" = --run ]; then
    local filter=$2
    mi_engine_env
    echo $$ > "$MI_LOGS/test.pid"
    rm -rf "$report"; rm -f "$MI_LOGS/test.end"
    cd "$MI_ENGINE" || exit 1
    env "UE-LocalDataCachePath=$MI_DDC" ./Engine/Binaries/Linux/UnrealEditor-Cmd "$MI_UPROJECT" \
      "-ExecCmds=Automation RunTests $filter;Quit" "-TestExit=Automation Test Queue Empty" "-ReportExportPath=$report" \
      -unattended -nosplash -NoSound -NullRHI -nopause -stdout -FullStdOutLogOutput "${MI_CACHE_ARGS[@]}" "${MI_EDITOR_ARGS[@]}" > "$log" 2>&1
    echo "exit code $?" >> "$log"
    date +%s > "$MI_LOGS/test.end"
    echo DONE > "$st"
    exit 0
  fi

  if [ "$1" != status ]; then
    local filter=${1:-MurderInc}
    [ -f "$MI_PROJECT_DIR/Binaries/Linux/libUnrealEditor-MurderInc.so" ] || mi_die "TESTS FAILED: the game module is not built (build.sh)"
    [ "$(cat "$MI_LOGS/build.status" 2>/dev/null)" = RUNNING ] && mi_die "TESTS FAILED: a build is running (build-status.sh)"
    if [ "$(cat "$st" 2>/dev/null)" = RUNNING ] && kill -0 "$(cat "$MI_LOGS/test.pid" 2>/dev/null)" 2>/dev/null; then
      echo "a test run is already going"
    else
      echo RUNNING > "$st"; date +%s > "$MI_LOGS/test.start"; echo "$filter" > "$MI_LOGS/test.filter"; rm -f "$MI_LOGS/test.end"
      setsid nohup bash "$0" --run "$filter" > /dev/null 2>&1 &
    fi
    local i
    for i in $(seq 1 18); do sleep 2; [ "$(cat "$st" 2>/dev/null)" = DONE ] && break; done
  fi

  local state t0 t1
  state=$(cat "$st" 2>/dev/null)
  [ -n "$state" ] || mi_die "TESTS NONE: no test run yet (test.sh)"
  t0=$(cat "$MI_LOGS/test.start" 2>/dev/null || date +%s); t1=$(cat "$MI_LOGS/test.end" 2>/dev/null || date +%s)
  if [ "$state" = RUNNING ]; then
    if ! kill -0 "$(cat "$MI_LOGS/test.pid" 2>/dev/null)" 2>/dev/null && [ $(( t1 - t0 )) -gt 10 ]; then
      echo "TESTS FAILED: the test process is gone without a result. Last lines of test.log:"; tail -5 "$log" | cut -c1-240; return 1
    fi
    echo "TESTS RUNNING $(( t1 - t0 )) s (filter $(cat "$MI_LOGS/test.filter" 2>/dev/null)): poll test.sh status"
    return 2
  fi
  "$(mi_python)" - "$report/index.json" "$log" "$(( t1 - t0 ))" "$(cat "$MI_LOGS/test.filter" 2>/dev/null)" <<'PY'
import json, re, sys
report, log, seconds, name = sys.argv[1:5]
passed = failed = skipped = 0
bad = []
try:
    data = json.load(open(report, encoding="utf-8-sig"))
    for test in data.get("tests", []):
        state = test.get("state", "")
        if state == "Success":
            passed += 1
        elif state in ("Skipped", "NotRun"):
            skipped += 1
        else:
            failed += 1
            notes = [e.get("event", {}).get("message", "") for e in test.get("entries", [])
                     if e.get("event", {}).get("type") in ("Error", "Warning")]
            bad.append((test.get("fullTestPath", "?"), state, notes[:3]))
    source = "report"
except (OSError, ValueError):
    text = open(log, encoding="utf-8", errors="replace").read()
    for result, path in re.findall(r"Test Completed\. Result=\{(\w+)\} Name=\{[^}]*\} Path=\{([^}]*)\}", text):
        if result in ("Success", "Passed"):
            passed += 1
        else:
            failed += 1
            bad.append((path, result, []))
    source = "log only, no report file"
fatal = ""
try:
    text = open(log, encoding="utf-8", errors="replace").read()
    hit = re.search(r"(Fatal error.*|Assertion failed.*|Unhandled Exception.*|=== Critical error.*)", text)
    fatal = hit.group(1)[:200] if hit else ""
except OSError:
    pass
ok = failed == 0 and passed > 0 and not fatal
print("TESTS %s passed=%d failed=%d skipped=%d filter=%s %s s (%s)" % ("OK" if ok else "FAILED", passed, failed, skipped, name, seconds, source))
if passed + failed == 0:
    print("no test ran: the filter matched nothing, or the editor did not start (see /project/ue/logs/test.log)")
if fatal:
    print("crash: " + fatal)
for path, state, notes in bad[:25]:
    print("  %s %s" % (state.upper(), path))
    for note in notes:
        print("      " + " ".join(note.split())[:260])
sys.exit(0 if ok else 1)
PY
}
main "$@"; exit $?
