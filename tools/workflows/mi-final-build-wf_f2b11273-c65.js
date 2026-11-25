export const meta = {
  name: 'mi-final-build',
  description: 'MURDER INC. version 3, release A: input fixes plus the end of the lag (GPU head-room, capture settings), reviewed, packaged, stream-tested under load, uploaded',
  phases: [
    { title: 'Input', detail: 'mouse scale, gamepad look, clickable cards, quality row, viewer console allowlist' },
    { title: 'Fluid', detail: 'never GPU-bound: dynamic resolution, frame-rate target, capture settings by measurement, numbers on the pause card, tuning without a rebuild' },
    { title: 'Review', detail: 'two adversarial reviews of the whole diff' },
    { title: 'Fix', detail: 'apply confirmed review findings, full tests' },
    { title: 'Package', detail: 'package, release gate under GPU load, stream test with input, upload, docs' },
    { title: 'Check', detail: 'independent release check' },
  ],
}

const SP = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad'
const TR = '/root/.claude/projects/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/tool-results'
const BASE = '0f99e0e'

const CONTEXT = `
PROJECT: MURDER INC., a first-person shooter rebuilt in Unreal Engine 5.9 (C++ project unreal/MurderInc), packaged for Linux with Pixel Streaming 2 (PS2) and streamed by Eagle 3D Streaming (E3DS) into the owner's website. Repo /home/user/MURDER-INC. (branch claude/tender-albattani-5q78qr: commit and push there, small commits, each ending with the attribution trailers given in your session rules; git pull --no-rebase before every push; never force-push; no pull request). Read first: docs/unreal/BOX.md (the box loop and pitfalls), docs/unreal/RESUME.md (sections 8 and 9), the top three entries of docs/unreal/PROGRESS.md, docs/LAUNCH.md, tools/box/cloud/package-cloud.sh, tools/box/cloud/MurderInc.sh, unreal/MurderInc/Source/MurderInc/Cloud/MICloud.cpp.

WHERE WE ARE (2026-11-24): version 1 on E3DS died at every session start with no log. Version 2 (zip sha256 ceaf828d..., game e989cb8, launcher f827e1b) adds: -RenderOffScreen always (E3DS does not add it; without it and without a display version 1 exits after 2.4 s), a logging launcher that also writes the file E3DS names with -ABSLOG= (E3DS always passes it and takes its crash-log email from it), SM5 fallback shaders, less video memory. The owner is uploading and testing version 2 on E3DS now. On the box a real WebRTC viewer (Python aiortc) received 1080p H.264 and sound from version 2: about 40 frames a second as E3DS starts it, about 55 with -PixelStreamingDecoupleFramerate. A launch pre-flight (four reviews against E3DS's own documentation) found the problems this workflow fixes. YOU ARE BUILDING VERSION 3, THE FINAL BUILD the owner will launch publicly: it must play well through the stream, not just start.

INPUTS TO READ: the pre-flight findings with file:line evidence and proposed fixes: ${TR}/b6h2x27u7.txt (E3DS hosting contract) and ${TR}/bn8o4k1re.txt (player experience through the stream, then GPU performance). If docs/unreal/PREFLIGHT.md exists, it is the verified and merged version: where it corrects or drops an item, follow it. If docs/unreal/DECISIONS.md has an entry about the owner's E3DS test of version 2 (GPU model, driver, frame rate, how the mouse felt, any crash log), use those facts. E3DS's documentation: https://docs.eagle3dstreaming.com/wiki/<page>/ is readable with curl from this machine (not from the box); text copies of about 30 pages are in ${SP}/e3ds-docs/*.txt, the page list in ${SP}/e3ds-docs/sitemap.xml. E3DS's connector hosts (their player page) are NOT reachable from here.

E3DS FACTS (from its documentation): it starts the app's .sh with, always: -PixelStreamingURL=<ws url> -PixelStreamingID=<id> -AudioMixer -log -Unattended -StdOut -FullStdOutLogOutput -ABSLOG=<file>, plus -AllowPixelStreamingCommands -Windowed -ForceRes, -ResX/-ResY (Browser Resolution Custom), -PixelStreamingEncoderCodec=, -PixelStreamingWebRTCMaxBitrate=, -PixelStreamingEncoderMinQP=/MaxQP= and the configuration's launch options. Machines: RTX 4080 or RTX 5070, 12 to 16 GB video memory, 32 GB RAM, one app per machine; an app should use 4 to 6 GB video memory and 50 to 70 % GPU. Linux uploads are not stream-tested by E3DS; every Linux session starts on a cold machine with a fresh copy of the zip. Browser Resolution Dynamic (their default) makes the page ask the app to render at the viewer's frame size (r.SetRes through PS2); Custom fixes it.

GPU BOX: Higgsfield rental, session id in BOXDIR=${SP}/box/session (now ec087d85-b777-4ece-be42-ccc063d225cf, RTX PRO 6000 Blackwell 96 GB, driver 620.70; it stops by itself after 10 idle minutes). Tool: mcp__Higgsfield__gpu_rental_exec (load its schema with ToolSearch "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__gpu_rental"), at most 90 s per call (it may report a timeout after 60 s: check before repeating), so start long work detached (setsid nohup ... &) and poll its log. If the box is gone follow the box-gone procedure of BOX.md exactly (next unused key from BOXDIR/keys that is not in BOXDIR/used, append it to used, rent the SAME spec: desktop kind, RTX-PRO-6000, cpu 16, memory_gib 64, max_credits_per_hour 114; write the new id to BOXDIR/session; run ensure-setup.sh until SETUP-DONE; if no unused key is left, generate one with uuidgen, append it to keys and used). Never rent anything else, never more than one box. /project is persistent: gameplay clone /project/ue/repo-gameplay (build.sh, tools/box/test.sh MurderInc: 105 tests with golden replays, about 20 minutes), release copy /project/ue/repo-release, cloud dir /project/ue/cloud (build-Shipping, build-Development, src = the tools as pushed, MurderInc-E3DS.zip, parts, repro/, verify-v2/). Other agents may be reading the box at the same time: run long scans with timeout, use your own streamer ids and run names, do not stop processes you did not start.

STREAM TEST TOOLS ON THE BOX: tools/box/cloud/e3ds-repro.sh (run <name> <secs> with RUNAS=fresh|ue4|root NODISPLAY=1 STOPSIG STOPTO BUILD=<dir> STDOUT=0; ss start|stop = Epic's signalling server, streamer port 8888, player port 8090), tools/box/cloud/e3ds-verify.sh, /project/ue/cloud/verify-v2/rtcview.py (a WebRTC viewer in Python: python rtcview.py <streamerId> <seconds> <outdir>; counts video and audio frames, saves frames 60, 600, 1500 as JPEG; its signalling socket closes after about 60 s, probably a missing keep-alive answer: fix that if you need longer sessions; needs a venv with aiortc websockets pillow: /tmp/fps/venv if it still exists, else python3 -m venv and pip install). A browser cannot be the viewer on the box (Chrome gathers no ICE candidates there). To LOOK at a frame: PUT it to the owner's Higgsfield storage (mcp__Higgsfield__media_upload gives a presigned URL; PUT from the box with headers Content-Type and If-None-Match: *; mcp__Higgsfield__media_confirm), download it to a folder under ${SP} on this machine, look at it with the Read tool, delete the local copy. To pass a long presigned URL to the box without retyping it: extract it from the session transcript with a script and stage it in a small text file in the storage that the box fetches by its short URL (PROGRESS.md and BOX.md describe both). Never commit a link.

RULES: the gameplay rules must not change: tools/box/test.sh MurderInc must pass every test (golden replays included) before anything is packaged; new behaviour gets new automation tests. Desktop (non-streamed) behaviour stays as it is unless an item says otherwise. Never commit pack, Epic or likeness content, any download link, the owner's email, an E3DS account or user name, or any person's name (public repository). Do not touch the web game src/. Never ask for or handle passwords. Write plain English in docs and commit messages. Be honest in your report: say what was measured, what was only read in source, and what is unproven.`

const WORK = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    done: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, what: { type: 'string' }, evidence: { type: 'string' } }, required: ['item', 'what', 'evidence'] } },
    not_done: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, why: { type: 'string' } }, required: ['item', 'why'] } },
    tests: { type: 'string' },
    head_commit: { type: 'string' },
    notes_for_next: { type: 'string' },
  },
  required: ['summary', 'done', 'not_done', 'tests', 'head_commit', 'notes_for_next'],
}

const REVIEW = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
          file: { type: 'string' },
          evidence: { type: 'string' },
          failure: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['title', 'severity', 'file', 'evidence', 'failure', 'fix'],
      },
    },
    checked_ok: { type: 'array', items: { type: 'string' } },
  },
  required: ['findings', 'checked_ok'],
}

const RELEASE = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    tests: { type: 'string' },
    runs: { type: 'array', items: { type: 'string' } },
    stream: { type: 'string' },
    package_urls: { type: 'array', items: { type: 'string' } },
    part_sha256: { type: 'array', items: { type: 'string' } },
    sha256: { type: 'string' },
    size_bytes: { type: 'number' },
    owner_settings: { type: 'array', items: { type: 'string' } },
    unproven: { type: 'array', items: { type: 'string' } },
    head_commit: { type: 'string' },
  },
  required: ['summary', 'tests', 'runs', 'stream', 'package_urls', 'part_sha256', 'sha256', 'owner_settings', 'unproven', 'head_commit'],
}

const CHECK = {
  type: 'object',
  properties: { ok: { type: 'boolean' }, problems: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } },
  required: ['ok', 'problems', 'notes'],
}

phase('Input')
const input = await agent(`${CONTEXT}

YOU ARE THE GAMEPLAY ENGINEER (first of two implementers; the second does rendering, the launcher and packaging after you). Work in /project/ue/repo-gameplay on the box and in the repo; build and run the tests on the box. Implement these items, each with an automation test where one is possible, then run the full suite. Evidence and proposed fixes for each are in ${TR}/bn8o4k1re.txt and ${TR}/b6h2x27u7.txt (search for the ids in brackets); verify each claim in the code before changing it.

A1 [mouse-scale-through-stream, mouse-glitch-filter-not-ported] Mouse look through the stream is 2 to 3 times too fast. PS2's reference player sends 2 counts per CSS pixel when render and player size are equal (check the maths in the engine source and the reference front end at /project/ue/cloud/infra/Frontend on the box, and say whether Shipping truncation matters). Add a cloud look scale: [MICloud] MouseScale in unreal/MurderInc/Config/DefaultGame.ini (default 0.5), overridable with a launch option -MIMouseScale=<number> (so the owner can tune it on E3DS without a rebuild), applied to the mouse look factor only while UMICloudSubsystem says the game is streamed; print it in the [MICloud] start lines. Port the web game's pointer-lock spike filter (config.json player.input.mouseGlitch; src/input.js is the reference; read only, never edit src/). Desktop mouse feel must not change.
A2 [pad-look-missing] A gamepad cannot turn or aim. Add right-stick look with the web game's numbers (Content/Data/config.json player.input.pad: dead zone, curve, yaw rate, pitch scale, boost; src/input.js is the reference), set FMIPlayerInputState::bPad from the last-used device so the pad aim slow-down works, keep the weapon wheel on the stick while the wheel is open. Test: full stick for one second turns the documented angle.
A3 [cards-not-clickable] The Pause, Settings, Dead and Debrief cards ignore the mouse although a cursor is drawn. Make their rows clickable and hover-selectable (left and right halves of adjustable rows change the value), and draw one hint line under the items ("Up/Down choose, Enter select, Left/Right change"). Keyboard and pad behaviour unchanged. Test the hit-testing function.
A4 [quality-setting-side-effects] In cloud mode, changing Graphics quality on the Settings card must not change the output resolution, the 60 fps cap or the cloud profile (see the finding for the engine calls involved). Test that t.MaxFPS and the resolution are unchanged after each quality level while streamed.
A5 [guest-join-reshows-card] A second viewer joining must not put the CLICK TO PLAY card over a running game: show the card for the first viewer and after all viewers have left (when the game is paused), not on additional joins.
A6 [viewer-console-and-link-args] E3DS passes -AllowPixelStreamingCommands, so any viewer can run console commands. In cloud mode replace PS2's console-command handling with an allowlist (commands that start with PixelStreaming2. or PixelStreaming. only; anything else is refused and logged once per session); find the right PS2 5.9 API in the engine source on the box (the input handler's command handlers). If PS2 offers no way to do that, set its allow-commands setting to false by code when streamed and write down which E3DS feature that may switch off. Take the game's debug console commands and switches (MIShot, MIAudio.Record, MIInput, MIMenu, MIStart, MIFaceEnemy, -MICrashTest, -MICloudLog) out of Shipping builds; they stay in Development (the zip carries the Development game as -MIDev, and the box tests use it).
A7 Text on the click card (Cloud/MICloud.cpp): replace "Sound starts with your click." with "No sound? Click the speaker at the bottom right." (E3DS starts a stream muted when the browser refuses autoplay). "a gamepad works too" stays, now that A2 makes it true.

Then: build, run tools/box/test.sh MurderInc on the box until every test passes (do not weaken or skip a test to get there), commit and push (repo and the box clone at the same commit), and add a short entry at the top of docs/unreal/PROGRESS.md ("Version 3: play through the stream") with what changed and how each item was verified. Report every item under done or not_done, the exact test result line, the head commit, and notes for the next implementer (anything half-done, any pitfall of the box today).`, { label: 'impl:input', phase: 'Input', schema: WORK })

const UPDATE = `

UPDATE (2026-11-25, after the owner's E3DS test; this block and docs/unreal/PREFLIGHT.md win over anything older in this prompt):
The owner uploaded version 2 to E3DS. It loads and streams (the start-up crash is fixed). The owner's verdict: "the game is sticky i cant play it", "the gameplay is very laggy; when the player turns it slows down; it is not a viable experience; we need to fix this now", and "make sure there is a path for someone to connect a PS5 controller and play". Read docs/unreal/DECISIONS.md, the entries of 2026-11-24 23:10 UTC and after: the lag is reproduced on the box and explained (Pixel Streaming 2's capture stalls the game when frames take the GPU too long; logs, scripts and summaries in /project/ue/cloud/lag-2026-11-24/ on the box), and the owner's priorities are binding: FLUID, RESPONSIVE PLAY FIRST, the look second.
docs/unreal/PREFLIGHT.md now exists. Its section 2 (items V3-1 to V3-13, the release gate, the order of work) is the specification of version 3. The work is split into two releases so the owner gets a playable build as early as possible:
RELEASE A (this workflow): what the gameplay engineer already built (mouse scale, gamepad look and menus, clickable cards, console allowlist), plus V3-1 (never run the GPU full: dynamic resolution and a frame-rate target), V3-3 (capture settings chosen by measurement under load), V3-5 (the game shows its own numbers on the pause card, a probe line by default), V3-11 (tuning without a rebuild: -MICVars), V3-9's allowlist widening, V3-10 (the box tests version 3 broke), and the first bullet of V3-4 (explain the 14.5 GB of memory and the hang at stop in box run gp-in5).
RELEASE B (a later workflow, not yours): V3-2 (quality steps), the rest of V3-4 (delay), V3-6 (Dynamic resolution handler and exact mouse scale), V3-7's remaining controller work, V3-12, V3-13. Do not start release B items unless one is needed to pass the release gate; if so, say which and why.
THE RELEASE GATE (PREFLIGHT.md section 2): on the box, with the GPU loaded the way the lag was reproduced, a Story run with fast turning has no game frame over 100 ms and no "Timed out waiting for fence" line; and with a free GPU the game holds 60 frames a second.
MEASURING ON THE BOX: several games on one GPU slow each other down and produce the very stall being fixed. Before each measurement run check (ps, nvidia-smi) that no other game is running, watch for one starting during the run, and throw away polluted runs. The Python viewers (rtcview.py, rtcinput.py) count received frames, but their congestion feedback and decoding are basic: under fast motion at 1080p their received frame rate collapses even when the game is healthy (runs s6 and s2 in /project/ue/cloud/lag-2026-11-24/SUMMARY.txt). Judge the game by its own probe lines (-MICloudProbe=1: fps, worstMs, gpuMs), the engine log (fence time-outs, "No frames available for capture") and the sender's own statistics (-PixelStreamingLogStats in the Development game); use received frame rates only as a rough check, and look at received frames with your own eyes when a capture setting changes (a torn, stale or half-drawn frame is a defect).`

const CONTEXT2 = CONTEXT + UPDATE

phase('Fluid')
const fluid = await agent(`${CONTEXT2}

YOU ARE THE PERFORMANCE ENGINEER OF RELEASE A. The gameplay engineer before you reported (JSON): ${JSON.stringify(input)}

Start from the pushed head (the gameplay engineer's work must be built and its tests passing; if its report says something is unfinished, finish only what release A needs). Then, in this order, following PREFLIGHT.md section 2 item by item (each item there names files, lines, cvars and evidence; verify before you change):

1. The lag-test tool. Turn the scripts in /project/ue/cloud/lag-2026-11-24/ (drive.sh, drive2.sh, drive3.sh, turn2.txt, turn3.txt, sum.py, the play scripts) into one committed tool, tools/box/cloud/lag-test.sh, that runs one game at a time (waiting until no other game runs and recording whether one appeared), with a chosen GPU load (r.ScreenPercentage in the Development game is the simple way to make frames cost more GPU time; find a second way that the game's own dynamic resolution cannot undo, for example other GPU work in a separate process, and calibrate both), and FIRST find out where the long frames go under that load, before fixing anything: profile the Development game (csvprofile, stat unit, or your own timestamps around the capture and the end of the frame) to tell the game thread, the render thread, the RHI thread, waiting for the GPU and the capture apart. DECISIONS.md's last lag entries say why: without any capture fence the capture errors vanish but a one-second frame remains at a 400 % screen percentage, and that load is not what a slow GPU does; two games on one card gave the owner's symptom (frames of 4 to 7 s), a viewer that turns slowly, fast and while walking, and prints one summary line per run: the game's frame rate, worst frame, GPU time, fence time-outs, skipped captures, sender statistics, received frames. Read DECISIONS.md's newest lag entries first: they say which runs were clean and what the clean comparison of the capture fence showed.
2. V3-3: capture settings by measurement under load (CaptureUseFence, UseMediaCapture, DecoupleFramerate, WebRTC.Fps, WebRTC.DisableFrameDropper). For each candidate: the game side (frame rate, worst frame, fence time-outs), the sender's statistics, and received frames LOOKED AT (still, slow turn, fast turn). Set the winners in cloud mode from code or config, with launch options to pin each way. If turning the fence off removes the stall, prove the picture is intact before making it the default.
3. V3-1: dynamic resolution with head-room, and the frame-rate target 60, 45, 30 that drops at once when the GPU still cannot keep up and rises only at a safe moment; WebRTC.Fps follows the target. Unit-test the decision logic. Then the release gate at several loads (frames of about 8, 12, 20 and 35 ms of GPU time at full quality): report for each what the game settled on (resolution, target) and the worst frame.
4. V3-5: the numbers line on the pause card and the default probe line every 30 s. V3-11: -MICVars with the allowed prefixes. V3-9: widen the console allowlist to the tuning prefixes (and check with rtcinput.py that a viewer's "t.MaxFPS 30" works in the Shipping game and that "quit" is refused). V3-10: repair e3ds-verify.sh and stream-test.sh.
5. V3-4, first bullet: find out why box run /project/ue/cloud/repro/gp-in5 reached 14.5 GB of memory and hung at stop; if version 3 code or the capture stall causes it, fix it (a session that eats memory until the machine kills it is a crash on E3DS).
Then build, run the full test suite on the box until every test passes, commit and push, and write the PROGRESS.md entry "Version 3, release A: the lag" with the measurement tables. Report done and not_done per item with evidence, the test result line, the head commit, the cloud defaults you set and why, and notes for the packager (the exact gate runs to repeat on the packaged Shipping game).`, { label: 'impl:fluid', phase: 'Fluid', schema: WORK })

phase('Review')
const LENSES = [
  { key: 'rules-and-input', prompt: `YOUR LENS: gameplay rules and input. Prove or disprove: (1) nothing in the rule code or data changed (golden replays still exercise the same paths; no test was weakened, skipped or re-recorded to pass); (2) the mouse scale, spike filter and gamepad look match the web game's numbers and behaviour (src/input.js and unreal/MurderInc/Content/Data/config.json are the reference) and desktop mouse feel is unchanged; (3) the clickable cards cannot fire twice, cannot click through to the game, and keyboard and pad still work; (4) the click-to-play card and pause-on-leave logic have no state in which the game runs under a card or stays paused with a viewer present; (5) a frame-rate target of 45 or 30 changes nothing in the rules (movement, fire rate, timers, enemy behaviour must be frame-rate independent: check the fixed-step code and say so with evidence).` },
  { key: 'engine-and-shipping', prompt: `YOUR LENS: engine use and Shipping-build safety. Check every engine API, cvar and Pixel Streaming 2 call the diff uses against the Unreal 5.9 source on the box (/project/ue/UnrealEngine): does it exist, is it used on the right thread and at the right time, does it behave in Shipping, on Linux, with the null platform application (-RenderOffScreen)? Check the head-room logic for oscillation, for a target that can never recover, and for any path that leaves the GPU full; check the capture settings chosen (is a picture without the fence safe: read the capture code); check the console allowlist and -MICVars really refuse what they should and still let E3DS's own PixelStreaming commands through; check each ini value is read where the author thinks (priority against the command line and E3DS's arguments). Read the measurement tables critically: were the runs clean (no second game on the GPU), do the numbers support the defaults chosen?` },
]
const reviews = (await parallel(LENSES.map(l => () =>
  agent(`${CONTEXT2}

YOU ARE AN ADVERSARIAL REVIEWER of release A's changes. Review the diff from commit ${BASE} to the pushed head (git diff ${BASE}..HEAD -- unreal tools; read whole files where the diff is not enough). Do not edit, commit or run long jobs; short read-only commands on the box are fine. The two engineers reported (JSON): INPUT ${JSON.stringify(input)} FLUID ${JSON.stringify(fluid)}

${l.prompt}

Report only real defects with evidence (file and line, an engine source line, or a command and its output), the concrete failure each causes, and the exact fix. must-fix = wrong behaviour for players on E3DS, a stall, a crash, a rule change, or a release hazard; should-fix = real but minor; nit = cosmetic. List what you checked and found correct.`, { label: `review:${l.key}`, phase: 'Review', schema: REVIEW })
    .then(r => r ? { lens: l.key, ...r } : null)
))).filter(Boolean)

const open = reviews.flatMap(r => r.findings.filter(f => f.severity !== 'nit').map(f => ({ lens: r.lens, ...f })))
log(`review: ${open.length} findings to fix (${open.filter(f => f.severity === 'must-fix').length} must-fix) from ${reviews.length} of ${LENSES.length} reviewers`)

phase('Fix')
const fixed = open.length === 0
  ? { summary: 'no review findings above nit', done: [], not_done: [], tests: fluid ? fluid.tests : '', head_commit: fluid ? fluid.head_commit : '', notes_for_next: '' }
  : await agent(`${CONTEXT2}

YOU FIX WHAT THE REVIEW FOUND in release A's changes (the diff ${BASE}..HEAD). Engineers' reports (JSON): INPUT ${JSON.stringify(input)} FLUID ${JSON.stringify(fluid)}

Review findings (JSON): ${JSON.stringify(open)}

For each finding: check it yourself first (reviewers can be wrong); fix it if it is real, with a test where one is possible; if you reject it, say why with evidence. must-fix items may not be left open. Then build and run the full test suite on the box until every test passes, repeat the release gate if you touched the head-room or capture code, commit and push, and add the outcome to the PROGRESS.md entry. Report done / not_done per finding, the test result line, the head commit, and notes for the packager.`, { label: 'fix:review-findings', phase: 'Fix', schema: WORK })

phase('Package')
const release = await agent(`${CONTEXT2}

YOU ARE THE RELEASE ENGINEER of release A (version 3a). Reports so far (JSON): INPUT ${JSON.stringify(input)} FLUID ${JSON.stringify(fluid)} FIXES ${JSON.stringify(fixed)}

1. Read the newest entries of docs/unreal/DECISIONS.md again: if the owner's E3DS data has arrived (GPU model, driver, the command line E3DS used, frame rates, a crash email with or without our log), apply what it implies to the defaults before packaging and say what you changed and why.
2. Confirm the full test suite passed on the head you package (run it if the head moved). Then tools/box/cloud/package-cloud.sh all (watch package.status), and e3ds-verify.sh.
3. THE RELEASE GATE ON THE PACKAGED SHIPPING GAME, from the zip unpacked as a fresh user, started with E3DS's documented argument list: with a free GPU, and with the GPU loaded to several levels (tools/box/cloud/lag-test.sh, the way that the game's own dynamic resolution cannot undo), a Story run with slow and fast turning and walking: no game frame over 100 ms once the run is under way, no "Timed out waiting for fence", no "No frames available for capture"; memory stays flat; the game stops cleanly. Report the table. If the gate fails, do not upload: report exactly what failed.
4. Prove play through a real stream with tools/box/cloud/rtcinput.py: click the CLICK TO PLAY card, start a Story run from the home screen with the keyboard and mouse, move, turn, fire, open the pause card with P and click Resume with the mouse; then the same start and a turn with a gamepad only. Verify from the game's log and from received frames; look at four received frames (home, in the run, the pause card with its numbers line, after turning) with the Read tool and describe them honestly, including anything that looks wrong.
5. Zip, split into parts of at most 240 MiB, upload to the owner's Higgsfield storage (file names MurderInc-E3DS-v3a-part<k>-of-<n>.zip), confirm, download every part back on this machine, join, compare sha256, unzip -t, check that MurderInc.sh in the zip is byte-identical to the repository's, that BUILD.txt names the pushed commits, and that the zip holds no Saved/, symbols or logs. Delete local copies.
6. Docs, short and for an owner who is not technical: docs/LAUNCH.md section 9 with version 3a's parts (fingerprints, sizes; the joined file must be called MurderInc.zip; upload with "Upload a new version of MurderInc" on the project's Builds tab), the E3DS settings and launch options to use with this build and why (resolution, quality, session time), what the numbers line on the pause card means and that a screenshot of it is what to send back, and what the game does on a slow server (lower resolution, then 45 or 30 frames a second) so that it never stalls. Update PROGRESS.md and RESUME.md section 9. No links, emails, account names or person names. Leave the larger LAUNCH.md and CURSOR_HANDOFF.md rewrites to release B.
Return: summary, the test result line, the runs with results (the gate table), the stream proof in plain words, package_urls in part order (only in this report), the parts' sha256 in order, the joined sha256 and size, the exact E3DS settings and launch options the owner should use, everything still unproven, and the head commit.`, { label: 'release:package', phase: 'Package', schema: RELEASE })

phase('Check')
const check = await agent(`${CONTEXT2}

YOU ARE THE INDEPENDENT RELEASE CHECKER of release A (version 3a). Trust nothing in the reports below; verify. Reports (JSON): RELEASE ${JSON.stringify(release)} FIXES ${JSON.stringify(fixed)}

On the box: download every package_url, check sizes and sha256 against the report and docs/LAUNCH.md section 9, run the owner's own join commands from LAUNCH.md, unzip -t, unpack as a brand-new non-root user into an empty folder and run it with E3DS's documented argument list and an -ABSLOG file, no display, with the signalling server. Repeat the release gate yourself with a free and with a loaded GPU (make sure no other game runs): a Story run with fast turning, no game frame over 100 ms once the run is under way, no fence time-out, memory flat, clean stop (exit 0). Confirm through a real stream that mouse, keyboard and gamepad input reach the game (rtcinput.py) and that the pause card shows the numbers line; look at two received frames. Confirm the full test suite's result for the packaged commit. Check the commits since ${BASE} contain no link, email, account name, person's name, licensed content or src/ change. Fix small doc errors yourself (commit, push); report everything else as a problem with its fix. ok is true only if this build removes the stall the owner reported and the owner can upload it.`, { label: 'check:release', phase: 'Check', schema: CHECK })

return { input, fluid, reviews, fixed, release, check }
