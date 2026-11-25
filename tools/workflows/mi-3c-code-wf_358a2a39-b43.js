export const meta = {
  name: 'mi-3c-code',
  description: 'MURDER INC. release 3c, game code only: the game ends with its session and idles when nobody watches (E3DS leaves it running), the encoder gets a quality range, a quality ladder for slow shared cards, the round trip reading; reviewed; no packaging',
  phases: [
    { title: 'Session', detail: 'idle throttle, exit after the last viewer, parent watch, encoder quality range, round trip' },
    { title: 'Ladder', detail: 'quality steps for a slow card after resolution and frame rate are used up' },
    { title: 'Review', detail: 'two adversarial reviews' },
    { title: 'Fix', detail: 'what the review found, full tests' },
  ],
}

const SP = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad'
const BRANCH = 'claude/tender-albattani-5q78qr'

const CONTEXT = `
PROJECT: MURDER INC., a first-person shooter in Unreal Engine 5.9 (C++ project unreal/MurderInc), packaged for Linux with Pixel Streaming 2 (PS2) and streamed by Eagle 3D Streaming (E3DS) into the owner's website. Repo /home/user/MURDER-INC. (branch ${BRANCH}: commit and push there, small commits, each ending with exactly these two lines:
Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4
git pull --no-rebase before every push; never force-push; no pull request; no link, storage address, email, E3DS account or host user name, or person's name in any commit; do not put a model name anywhere else). Read first: docs/unreal/BOX.md (the box loop and its pitfalls), docs/unreal/RESUME.md section 9, the newest entries of docs/unreal/DECISIONS.md (the two of 2026-11-25 about E3DS's machines and version 4: READ THEM, they are the facts this work rests on), the top entries of docs/unreal/PROGRESS.md (version 3a and "Version 3b: sound"), docs/unreal/PREFLIGHT.md (V3-2, V3-4, V3-6, V3-15 if present), unreal/MurderInc/Source/MurderInc/Cloud/MICloud.cpp and .h, tools/box/cloud/MurderInc.sh (the launcher), tools/box/cloud/lag-test.sh (the lag test: its header says how to run it), rtcinput.py.

WHAT WE KNOW (measured on E3DS from the box's browser, 2026-11-25; details in DECISIONS.md):
- E3DS's Linux machine: NVIDIA RTX A4000 (16 GB, about a quarter of the test box's speed), driver 550.90, 8 AMD EPYC threads, 20 GB RAM, no display. The driver fails Unreal's Vulkan SM6 check, so the game runs SM5 (no Nanite, software Lumen). E3DS starts the app with -PixelStreamingEncoderMinQP and MaxQP equal (Medium: 34 and 34; High: 16 and 16: a constant quantiser) and its page sends PixelStreaming.Encoder.MinQP / MaxQP console commands at the start of every session; -PixelStreamingWebRTCMinBitrate=100000 -PixelStreamingWebRTCMaxBitrate=20000000. At QP 16 a fast turn needs up to 14.5 Mbit/s.
- On a clean machine version 4 (3a + launcher cleanup) plays a Story run at 60 fps with a worst frame of 18 ms and 10 to 13 ms of GPU time at render scale 0.50 to 0.63: the card has about 4 ms in hand at the smallest picture.
- THE BIG ONE: E3DS does NOT stop the game of a session that has ended. The next session on that machine finds the old game still on the card drawing at full speed: session 2 ran at 27 fps (GPU 36 ms), session 3 at 18 fps (55 ms). Version 4's launcher now stops other games of the package at its start and forwards a stop signal at once, but the GAME ITSELF should (1) stop drawing when no viewer is connected, (2) quit by itself a short time after the last viewer left, and (3) quit if nobody ever connects. E3DS's documentation says an ended session "frees the machine" but does not say it kills the app.
- The pause card's numbers line and the probe line (-MICloudProbe=N seconds; default 30) exist (version 3a); the round trip reads 0 ms on E3DS (a reading that does not work).

BOX AND ETIQUETTE (important): GPU box = Higgsfield rental, session id in ${SP}/box/session (now ec087d85-b777-4ece-be42-ccc063d225cf, RTX PRO 6000 Blackwell, 16 CPUs, 64 GB). Tool: mcp__Higgsfield__gpu_rental_exec (load its schema with ToolSearch "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__gpu_rental"), at most 90 s per call (it may time out at 60 s: check before repeating), so start long work detached (setsid nohup ... &) and poll. If the box is gone follow BOX.md's box-gone procedure exactly (same spec only; never more than one box). TWO OTHER JOBS USE THIS BOX NOW: the version 3b release (its engineers package from /project/ue/repo-release and test in /project/ue/repo-gameplay, and run the release gate on the GPU) and the owner's browser on the box's desktop. Therefore: (1) NEVER touch /project/ue/repo-gameplay, /project/ue/repo-release, /project/ue/cloud/e3ds-upload*, /project/ue/cloud/MurderInc-E3DS.zip, /project/ue/cloud/build-*, the v3a/v3b files in /project/ue/cloud, or the browser (owner-browser, /tmp/e3ds-owner-browser, Firefox). (2) Work in YOUR OWN clone /project/ue/repo-3c: make it as BOX.md section 7 describes (git clone of the public repository's branch, seed-content.sh, the art and map copies the gameplay clone needs to play a Story run, the audio import if tools/box/audio-import.sh applies, the first build about 12 minutes); if the repository's branch already has what you need use it, and copy generated content (never committed) from the gameplay clone with cp --reflink=auto only, never move it. (3) Run every compile with nice -n 19 and at most 6 parallel jobs (UBT: -MaxParallelActions=6), and start no compile, cook or test suite while a gate run is active (pgrep -f lag-test.sh or a game process of another job: wait and re-check); lag-test.sh already serialises games on the GPU: use it. (4) Several games on one GPU produce the very stall you measure: one game at a time, throw away polluted runs. (5) Do not package, do not upload anything to E3DS, do not touch the owner's Higgsfield storage except for looking at pictures (BOX.md says how).

RULES: the gameplay rules must not change: the full automation suite (tools/box/test.sh MurderInc in your clone) must pass, golden replays included, with no test weakened, skipped or re-recorded; new behaviour gets new tests; the web game src/ is never touched; no pack, Epic or likeness content, link or account name is ever committed; plain English in docs and commit messages. Be honest in every report: say what was measured, what was only read, what is unproven.`

const WORK = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    done: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, what: { type: 'string' }, evidence: { type: 'string' } }, required: ['item', 'what', 'evidence'] } },
    not_done: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, why: { type: 'string' } }, required: ['item', 'why'] } },
    tests: { type: 'string' },
    head_commit: { type: 'string' },
    notes_for_release: { type: 'string' },
  },
  required: ['summary', 'done', 'not_done', 'tests', 'head_commit', 'notes_for_release'],
}

const REVIEW = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
      file: { type: 'string' }, evidence: { type: 'string' }, failure: { type: 'string' }, fix: { type: 'string' },
    }, required: ['title', 'severity', 'file', 'evidence', 'failure', 'fix'] } },
    checked_ok: { type: 'array', items: { type: 'string' } },
  },
  required: ['findings', 'checked_ok'],
}

phase('Session')
const session = await agent(`${CONTEXT}

YOU ARE THE SESSION ENGINEER. Implement, in your own clone, with tests, in this order (each item: read the code, change it, test it, measure it through a stream where it says so):

S1. NOBODY WATCHING = NO DRAWING. In UMICloudSubsystem (it already counts viewers: FMICloudViewers), when the viewer count has been 0 for 2 s (and the card/pause logic has run), cap the frame rate hard (t.MaxFPS about 2) and keep the resolution minimal so that an idle game costs the card almost nothing; restore the previous caps at once when a viewer joins (the click card still shows). Make the numbers cvars (MI.Cloud.IdleFps, default 2) with launch options. Prove it on the box: a game with no viewer for 30 s uses a small fraction of the GPU (nvidia-smi dmon or the probe's gpuMs and fps) compared with one that has a viewer on the menu.
S2. THE GAME ENDS WITH ITS SESSION. (a) When the last viewer has gone for MI.Cloud.ExitAfterEmpty seconds (default 20; a page reload reconnects within a few seconds: choose the default so that a reload does not end the game, and say how you decided), the game logs one clear line and quits cleanly (FPlatformMisc::RequestExit(false) from the game thread; exit code 0). (b) If no viewer ever connected within MI.Cloud.ExitIfNoViewer seconds of the game's start (default 600), it quits the same way (a machine given to a session whose viewer never came). (c) If the launcher that started it is gone, it quits: the launcher passes its own pid as -MILauncherPid=<pid> (change tools/box/cloud/MurderInc.sh: it already forwards stop signals and has a watchdog; keep every behaviour of version 4's launcher and its tests), the game polls that pid every 2 s on Linux and quits after it is gone for 5 s; with no -MILauncherPid (a game started by a test script) nothing is watched. (d) Launch option -MIKeepAlive turns (a) to (c) off; the box's test scripts that hold a game with no viewer on purpose (lag-test.sh, e3ds-repro.sh, stream-test.sh, memory-runs.sh and any script of tools/box/cloud) must keep working: find every place that starts a game and give the ones that need it -MIKeepAlive, saying in each script's header why. The EXIT must never happen during a live session: prove with a test that the countdown is cancelled by a join and that a viewer present keeps the game alive for as long as you like; unit-test the decision logic (pure function: viewers, seconds since the last change, options -> keep, idle, exit) in the automation suite.
S3. THE ENCODER GETS A RANGE. E3DS's page sends PixelStreaming.Encoder.MinQP and MaxQP console commands at the start of every session (equal values: a constant quantiser). In the cloud, take those two numbers as the CENTRE of a range instead: effective MinQP = value - MI.Cloud.QpBelow (default 10, floor 8), MaxQP = value + MI.Cloud.QpAbove (default 8, ceiling 48), so that the sender can pick the quality the connection carries (Medium 34 gives 24 to 42; High 16 gives 8 to 24). Find where the game handles viewer console commands (MICloud.cpp) and PS2's own handling of the launch-option QPs (the command line carries them too: check which one wins and when, in the engine source /project/ue/UnrealEngine/Engine/Plugins/Media/PixelStreaming2), apply the range to both, log the mapping once per change, and keep a pin (launch option -MIQpExact turns it off). Prove on the box with rtcinput.py (cmd PixelStreaming.Encoder.MinQP 34 / MaxQP 34, then 16 / 16) and E3DS's argument list: the probe's qp field and bitrate in a standing scene and in fast turns; then limit the viewer's link (tc netem on loopback, or the Python viewer's own bandwidth feedback: lag-test.sh's minbit key and BOX.md's notes) to about 4 Mbit/s and show that with High the exact QP stalls or drops frames while the range adapts (the sender's frames a second, the received frames, the QP actually used).
S4. THE ROUND TRIP. The probe and the pause card's line show a round trip of 0 ms on E3DS. Find where it is read (PS2's stats: the active outbound video stats' currentRoundTripTime / the transport's), make it read the real value, and show on the box that it does under a viewer on a link with a known delay (tc netem delay 40ms).
S5. Build, run the full suite in your clone until every test passes (no audio or other warnings that your change causes), commit and push in working steps, and write the entry "Release 3c: the session" at the top of docs/unreal/PROGRESS.md (what changed, how each item was verified, the numbers). Add the new launch options and cvars to docs/LAUNCH.md section 9 or 13 where the others are listed (short, plain English), and to MICloud.h's header comment.
Report each item under done or not_done with evidence, the exact test result line, the head commit, and notes for the release engineer (the exact commands that prove each item on a package; which test scripts now pass -MIKeepAlive).`, { label: 'impl:session', phase: 'Session', schema: WORK })

phase('Ladder')
const ladder = await agent(`${CONTEXT}

YOU ARE THE QUALITY-LADDER ENGINEER. The session engineer before you reported (JSON): ${JSON.stringify(session)}
Start from the pushed head in YOUR clone (/project/ue/repo-3c): pull it, build, make sure its tests pass first.

THE PROBLEM. Version 3a keeps the GPU from being the limit by lowering the render scale (50 % to 75 % of the output) and then the frame-rate target (60, 45, 30). E3DS's card is about four times slower than the box's and may be shared with another game. When the render scale is at its minimum and the target is 30 and the GPU is still the limit (or a frame still takes 35 ms or more), the game has nothing left to give: that is the case PREFLIGHT.md V3-2 ("quality steps") is for and that this task implements. It must also make the 60 fps case more robust: a card that holds 60 at render scale 0.5 with 4 ms in hand has no room for a fight (explosions, many enemies): a fight costs more GPU than the first room of a Story run.

DO, in order:
L1. MEASURE what each step buys, on the box, with the lag test tool and its calibrated loads (lag-test.sh calib; the loads that make the box's card as slow as E3DS's: about 4 times slower is the "1:0.3:0" load and heavier ones; read lag-gate.txt): for the Story run's scenes (and, if you can drive one, a fight), the GPU time at render scale 0.5 with each of: sg.ShadowQuality 3/2/1, sg.GlobalIlluminationQuality 3/2/1, sg.ReflectionQuality 3/2/1, sg.PostProcessQuality 3/2/1, sg.EffectsQuality, r.Lumen.* (software Lumen: screen-probe resolution, trace distance, reflections off), r.VolumetricFog off, r.TSR.* cheaper settings, r.Shadow.Virtual.* (pages, resolution scale), r.MotionBlur, r.DepthOfField. Put the table in PROGRESS.md. LOOK at received frames (rtcinput.py frame lines) for each candidate step: say what each costs in looks and choose the order of steps by (GPU time saved) / (what the picture loses), cheapest-looking first.
L2. IMPLEMENT the ladder in the head-room controller (UMICloudSubsystem / the pacer code): a small state machine with steps 0 (full) to N, going down when the GPU time has stayed above its limit for a few seconds AT the smallest render scale and the lowest target the controller allows, going up only after a long calm period (hysteresis, so that it never oscillates; each change at most once per 10 s), applying the steps as cvars from the table (data in DefaultGame.ini [MICloud], not code constants), with launch options to pin a step (-MIQuality=<n>) or turn the ladder off, a log line per change and the current step on the pause card's numbers line and the probe line. The scalability groups are in the viewer-command allowlist: keep that as it is. Changing a quality group at run time can hitch (shader permutations, Lumen rebuilds): measure the longest frame of every step change and choose the steps and the way of applying them so that a change never makes a frame over 100 ms in play; if a step cannot be changed live without a hitch, apply it only at a calm moment (a pause card, a loading moment) or drop it from the ladder and say so. Unit-test the decision logic (a pure function over a recorded series of GPU times), with the oscillation case.
L3. THE GATE. Repeat the release gate (tools/box/cloud/lag-gate.txt and the lag-stops.txt viewer, on the Shipping game of a package: you cannot package; use the Development game built in your clone with the cloud profile exactly as the cloud has it, the way PROGRESS.md "Version 3a" says the gate was first run, and say plainly that it is not the packaged game) at the loads of the gate AND at two heavier loads (the box slowed to E3DS's speed and to a shared card: two games' worth): in play no frame over 100 ms, never more than 2 frames owed, the game ends at the step you report and holds at least 30 fps at the heaviest load, a free GPU still gives 60 fps and step 0. Report the table next to version 3a's.
L4. Build, run the full suite until every test passes, commit and push in working steps, write "Release 3c: the quality ladder" in PROGRESS.md with the tables, update PREFLIGHT.md V3-2 (done, and what is left), docs/LAUNCH.md (the new launch options and what the numbers line shows).
Report done / not_done per item with evidence, the exact test result line, the head commit, and notes for the release engineer.`, { label: 'impl:ladder', phase: 'Ladder', schema: WORK })

const LENSES = [
  { key: 'session-lifecycle', prompt: `YOUR LENS: the session's life on E3DS. Prove or disprove with evidence (code, engine source, runs): (1) the game cannot quit during a live session (viewer count read at the right time and thread; a page reload; a second viewer joining; a viewer on a slow connection reconnecting; E3DS's own start sequence in which the game starts BEFORE any viewer and a cold machine takes minutes: ExitIfNoViewer is long enough and counts from the right moment); (2) the game really ends after the last viewer leaves, cleanly, exit code 0, and the launcher then ends too without leaving a process (the launcher's trap, the watchdog, the tee); (3) -MILauncherPid cannot kill a game that a test script started, and a launcher that is replaced (E3DS restarting the app) cannot kill the new game; (4) the idle throttle restores everything at a join (frame cap, resolution, DR state, the pacer, the click card), and the first frames after a join are not a stall; (5) every box test script that starts a game still works and passes the right options; (6) the encoder range: which of the command line and the viewer commands wins, that the range is applied once and not undone by a later E3DS command or by PS2's own re-read, that the sender's QP stays inside the range, that -MIQpExact restores the old behaviour; (7) the round trip now reads a real value on E3DS's kind of connection (WebRTC stats on a Linux server) and never divides by zero or shows a stale number.` },
  { key: 'ladder-and-shipping', prompt: `YOUR LENS: the quality ladder and Shipping safety. Check every engine API, cvar and scalability call the diff uses against the Unreal 5.9 source on the box (/project/ue/UnrealEngine): does the cvar exist in Shipping on Linux, is it changed on the right thread, does a live change work with SM5 and software Lumen (not just SM6), does it hitch. Read the measurement tables critically: clean runs only (one game on the GPU), the loads really the E3DS speed, received frames looked at; do the numbers support the order of the steps? Look for oscillation, a step that can never be undone, a ladder that fights the render-scale controller or the frame-rate target, anything that makes the picture pop in play, and any way the ladder could lower quality on a card that was fine (a hitch misread as a slow GPU, the first seconds of a cold start, the idle throttle's low frame rate read as a slow GPU, a pause). Check the golden tests still exercise the same rule paths and no test was weakened.` },
]

const reviews = (await parallel(LENSES.map(l => () =>
  agent(`${CONTEXT}

YOU ARE AN ADVERSARIAL REVIEWER of release 3c's game changes (git diff from the commit before the session engineer's first commit to the pushed head; read whole files where the diff is not enough; the code is in your read-only view of the repository and in /project/ue/repo-3c on the box). Do not edit, commit or run long jobs; short read-only commands on the box are fine. The engineers reported (JSON): SESSION ${JSON.stringify(session)} LADDER ${JSON.stringify(ladder)}

${l.prompt}

Report only real defects with evidence (file and line, an engine source line, or a command and its output), the concrete failure each causes for a player on E3DS, and the exact fix. must-fix = a live session can end, a stall, a crash, a rule change, a quality loss on a card that was fine, or a release hazard; should-fix = real but minor; nit = cosmetic. List what you checked and found correct.`, { label: 'review:' + l.key, phase: 'Review', schema: REVIEW })
    .then(r => r ? { lens: l.key, ...r } : null)
))).filter(Boolean)

const open = reviews.flatMap(r => r.findings.filter(f => f.severity !== 'nit').map(f => ({ lens: r.lens, ...f })))
log(`review: ${open.length} findings to fix (${open.filter(f => f.severity === 'must-fix').length} must-fix) from ${reviews.length} of ${LENSES.length} reviewers`)

phase('Fix')
const fixed = open.length === 0
  ? { summary: 'no review findings above nit', done: [], not_done: [], tests: ladder ? ladder.tests : '', head_commit: ladder ? ladder.head_commit : '', notes_for_release: '' }
  : await agent(`${CONTEXT}

YOU FIX WHAT THE REVIEW FOUND in release 3c's game changes. Engineers' reports (JSON): SESSION ${JSON.stringify(session)} LADDER ${JSON.stringify(ladder)}
Review findings (JSON): ${JSON.stringify(open)}
For each finding: check it yourself first (reviewers can be wrong); fix it if it is real, with a test where one is possible; if you reject it, say why with evidence. must-fix items may not be left open. Then build in your clone, run the full suite until every test passes, repeat the gate runs that your change touches, commit and push, and add the outcome to the PROGRESS.md entries. Report done / not_done per finding, the test result line, the head commit, and notes for the release engineer (a short checklist of what a package of this code must be proven to do).`, { label: 'fix:review', phase: 'Fix', schema: WORK })

return { session, ladder, reviews, fixed }
