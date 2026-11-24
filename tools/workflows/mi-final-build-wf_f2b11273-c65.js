export const meta = {
  name: 'mi-final-build',
  description: 'MURDER INC. version 3 (the final build): fix play through the stream, tune for E3DS, review, package, test the stream with input, upload, verify',
  phases: [
    { title: 'Input', detail: 'mouse scale, gamepad look, clickable cards, quality row, viewer console allowlist' },
    { title: 'Render', detail: 'texture pool, resolution cap, dynamic resolution, shader warm-up, probe, HUD scale, launcher' },
    { title: 'Review', detail: 'three adversarial reviews of the whole diff' },
    { title: 'Fix', detail: 'apply confirmed review findings, full tests' },
    { title: 'Package', detail: 'package, E3DS-style runs, stream test with input, upload, docs' },
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

phase('Render')
const render = await agent(`${CONTEXT}

YOU ARE THE RENDERING AND RELEASE-TOOLS ENGINEER (second implementer). The gameplay engineer before you reported (JSON): ${JSON.stringify(input)}

Start from the pushed head. Implement these items; measure before and after on the box and report the numbers (use the Development game for engine statistics: r.Vulkan.DumpMemory, rhi.DumpResourceMemory, -MICloudProbe=<seconds>; tools/box/cloud/e3ds-repro.sh and the MIDemo scripts e3ds-play.txt and hold.txt drive runs; make a demo script that turns the camera and fights if none does). Evidence and proposed fixes are in ${TR}/bn8o4k1re.txt (GPU performance section) and ${TR}/b6h2x27u7.txt.

B1 [texture-pool-full] E3DS's cards have 12 to 16 GB, not 8: set r.Streaming.PoolSize in [MICloud] (unreal/MurderInc/Config/DefaultGame.ini) to 1000, keep LimitPoolSizeToVRAM=1, correct the comments there. The committed Vulkan memory at 1920x1080 must stay under about 4.8 GB in a Story run; if it does not, choose the largest pool that does.
B2 [dynamic-resolution-4k, dynamic-resolution-untested] With E3DS's Dynamic resolution a viewer in full screen on a 1440p or 4K monitor makes the game render at that output size. Cap the internal render size in cloud mode (r.ScreenPercentage.MaxResolution=1080 if that cvar exists and works in 5.9: verify in the engine source and by measurement), then run the game at -ResX=2560 -ResY=1440 and at 3840x2160 and also change the size at run time the way PS2 does (r.SetRes) and report GPU time and video memory for each. The game must be safe at any size a browser asks for, including odd and portrait sizes (no crash, no runaway memory): clamp what is unreasonable.
B3 [gpu-5070-headroom] Frame time was measured only on a GPU 2 to 4 times faster than E3DS's. Check that dynamic resolution engages on Linux Vulkan with off-screen rendering and TSR (r.DynamicRes.OperationMode=2, r.DynamicRes.FrameTimeBudget=16.67, min 50, max 75), by forcing GPU load on the box. Turn it on in [MICloud] only if it works without artefacts or hitches; otherwise leave it off and say exactly what you saw. Do NOT lower Lumen, Nanite or shadow quality: the owner wants the next-gen look; quality may drop only under load, through resolution.
B4 [cold-shader-caches, cold-machine-shader-hitches] Every E3DS session starts with cold shader caches. Add what makes the first run smooth, cheapest first: r.PSOPrecache.Resources=1 if valid in 5.9, and loading at boot (asynchronously, kept referenced) every asset the spawn code loads later (Goons, the drone, guns and attachments, effects, wrecks: find them in the spawn code and the data files), so their shaders compile during the home and loadout screens. Measure a cold start (fresh user, empty HOME, NVIDIA and Vulkan caches removed) through the first minute of a Story run with -MICloudProbe=1 before and after; report worst frame times and any late-appearing models.
B5 [no-session-gpu-telemetry] In cloud mode log one probe line every 30 s by default (frame rate, worst frame, GPU time, memory, game state); -MICloudProbe=0 turns it off, other values change the period.
B6 [hud-scaling-at-other-sizes] Scale the HUD texts that use fixed font scales with the resolution factor, bind the wide strips to min(height, width) scale, give the crosshair a thin dark outline. Check the HUD at 1280x720, 1920x1080, 2560x1440 and 3840x2160 (save pictures on the box and look at two of them).
B7 Launcher tools/box/cloud/MurderInc.sh: report a game killed by signal 9 as "killed from outside (the host or the out-of-memory killer)", not as a crash; fix the SM5 text (the SM5 fallback keeps software Lumen and loses Nanite); add -PixelStreamingDecoupleFramerate to the game's arguments by default with -MINoDecouple to leave it out (measured on the box: about 55 instead of 40 frames a second received; in 5.9 PixelStreaming2.CaptureUseFence is already on); every 30 s while the game runs append one line of nvidia-smi (memory.used, utilization.gpu, utilization.encoder) to the log, from a child that ends with the launcher and never outlives the game (E3DS shuts down processes it does not know). Keep everything the launcher does today (the -ABSLOG file, stop signals, root handling); re-run the fake-game cases and the E3DS-argument runs that PROGRESS.md lists.
B8 tools/box/cloud/e3ds-verify.sh: add the runs with E3DS's documented argument list and an -ABSLOG file (Shipping, crash test with the Development game, -MIDev, started as root), and a stream check with rtcview.py that fails when no video frame arrives. package-cloud.sh: add -createreleaseversion only if the package then builds and runs exactly as before (it makes later pak patches possible); if it complicates anything, leave it out and say so.

Then build, run the full test suite until every test passes, commit and push, extend the PROGRESS.md entry "Version 3" with measurements (a table: item, before, after). Report done / not_done, the test result line, the head commit, and notes for the packager.`, { label: 'impl:render', phase: 'Render', schema: WORK })

phase('Review')
const LENSES = [
  { key: 'rules-and-input', prompt: `YOUR LENS: gameplay rules and input. Prove or disprove: (1) nothing in the rule code or data changed (golden replays still exercise the same paths; no test was weakened, skipped or re-recorded to pass); (2) the new mouse scale, glitch filter and gamepad look match the web game's numbers and behaviour (src/input.js and unreal/MurderInc/Content/Data/config.json are the reference) and desktop mouse feel is unchanged; (3) the clickable cards cannot fire twice, cannot click through to the game, and keyboard and pad still work; (4) the click-to-play card and pause-on-leave logic have no state in which the game runs under a card or stays paused with a viewer present.` },
  { key: 'engine-and-shipping', prompt: `YOUR LENS: engine use and Shipping-build safety. Check every engine API, cvar and Pixel Streaming 2 call the diff uses against the Unreal 5.9 source on the box (/project/ue/UnrealEngine): does it exist, is it used on the right thread and at the right time in start-up, does it behave in Shipping, on Linux, with the null platform application (-RenderOffScreen)? Check the console-command allowlist really blocks what it should and still lets E3DS's own PixelStreaming commands through. Check the asset preloading for memory growth, start-up time and garbage-collection safety. Check each [MICloud] and engine ini value is read where the author thinks (priority against the command line and E3DS's arguments).` },
  { key: 'launcher-and-release', prompt: `YOUR LENS: the launcher and packaging. Read tools/box/cloud/MurderInc.sh, package-cloud.sh, e3ds-verify.sh as changed. Try to break the launcher on paper and with a fake game on the box (a scratch folder under /tmp on the box): the -ABSLOG file in every mode, the sampler child (does it end when the game ends, when the launcher is killed, when the host kills the process group; can it outlive the session), stop signals, exit codes (the game's own code for a crash, 0 for a stop the host asked for), started by sh, started as root, a closed output, spaces in paths, missing tools (no nvidia-smi, no tee, no setpriv). Check that -PixelStreamingDecoupleFramerate reaches the game and -MINoDecouple removes it. Check nothing in the zip step can ship Saved/, symbols, logs, links or the box's own files.` },
]
const reviews = (await parallel(LENSES.map(l => () =>
  agent(`${CONTEXT}

YOU ARE AN ADVERSARIAL REVIEWER of version 3's changes. Review the diff from commit ${BASE} to the pushed head (git diff ${BASE}..HEAD -- unreal tools docs; read whole files where the diff is not enough). Do not edit, commit or run long jobs; short read-only commands on the box are fine (and, for the launcher lens only, fake-game runs in a scratch folder under /tmp on the box). The two implementers reported (JSON): INPUT ${JSON.stringify(input)} RENDER ${JSON.stringify(render)}

${l.prompt}

Report only real defects with evidence (file and line, an engine source line, or a command and its output), the concrete failure each causes, and the exact fix. must-fix = wrong behaviour for players on E3DS, a crash, a rule change, or a release hazard; should-fix = real but minor; nit = cosmetic. List what you checked and found correct.`, { label: `review:${l.key}`, phase: 'Review', schema: REVIEW })
    .then(r => r ? { lens: l.key, ...r } : null)
))).filter(Boolean)

const open = reviews.flatMap(r => r.findings.filter(f => f.severity !== 'nit').map(f => ({ lens: r.lens, ...f })))
log(`review: ${open.length} findings to fix (${open.filter(f => f.severity === 'must-fix').length} must-fix) from ${reviews.length} of ${LENSES.length} reviewers`)

phase('Fix')
const fixed = open.length === 0
  ? { summary: 'no review findings above nit', done: [], not_done: [], tests: render ? render.tests : '', head_commit: render ? render.head_commit : '', notes_for_next: '' }
  : await agent(`${CONTEXT}

YOU FIX WHAT THE REVIEW FOUND in version 3's changes (the diff ${BASE}..HEAD). Implementers' reports (JSON): INPUT ${JSON.stringify(input)} RENDER ${JSON.stringify(render)}

Review findings (JSON): ${JSON.stringify(open)}

For each finding: check it yourself first (reviewers can be wrong); fix it if it is real, with a test where one is possible; if you reject it, say why with evidence. must-fix items may not be left open. Then build and run the full test suite on the box until every test passes, commit and push, and add the outcome to the PROGRESS.md "Version 3" entry. Report done / not_done per finding, the test result line, the head commit, and notes for the packager.`, { label: 'fix:review-findings', phase: 'Fix', schema: WORK })

phase('Package')
const release = await agent(`${CONTEXT}

YOU ARE THE RELEASE ENGINEER for version 3. Reports so far (JSON): INPUT ${JSON.stringify(input)} RENDER ${JSON.stringify(render)} FIXES ${JSON.stringify(fixed)}

1. Read the newest entries of docs/unreal/DECISIONS.md and docs/unreal/PREFLIGHT.md again: if the owner's E3DS test of version 2 is recorded (GPU, driver, frame rate, mouse feel, a crash log), apply what it implies to the defaults (for example MouseScale, the decouple default) before packaging and say what you changed and why. If it is not recorded yet, package with the defaults and list which defaults the E3DS result may still change.
2. Confirm the full test suite passed on the head you package (run it if the head moved). Then tools/box/cloud/package-cloud.sh all (as PROGRESS.md "E3DS crash fix" describes; watch package.status), and e3ds-verify.sh.
3. Prove version 3 through a real stream on the box, with input: extend rtcview.py (or write a sibling tool, committed under tools/box/cloud/) so the viewer also sends Pixel Streaming input over the data channel the way the reference front end does (read /project/ue/cloud/infra/Frontend on the box for the message formats): click the CLICK TO PLAY card, start a Story run from the home screen, move, turn with the mouse, fire, open the pause card with P and click Resume with the mouse, turn with a gamepad stick. Verify from the game's log (probe lines, state changes) and from received frames that each input did what it should; measure how many degrees a known mouse travel turns the camera with the default MouseScale; look at four received frames (home, in the run, the pause card, after turning) with the Read tool and describe them honestly. Measure received frames per second with and without -MINoDecouple, and video memory and GPU time in the run. If a step cannot be automated, say exactly which and why.
4. Zip, split into parts of at most 240 MiB, upload to the owner's Higgsfield storage (file names MurderInc-E3DS-v3-part<k>-of-<n>.zip), confirm, download every part back on this machine, join, compare sha256, unzip -t, check that MurderInc.sh in the zip is byte-identical to the repository's, that BUILD.txt names the pushed commits, and that the zip holds no Saved/, symbols or logs. Delete local copies.
5. Docs, for an owner who is not technical: rewrite docs/LAUNCH.md so every E3DS step uses E3DS's own names (Your Projects, the project's Builds tab, "Upload a new version of MurderInc", Viewer Experience tabs Common / UI / Developer, Browser Resolution, Max Session Time, Email To Send Log Upon App Crash, Print UE log in browser console, Launch options; check each against ${SP}/e3ds-docs or the live documentation), section 9 with version 3's parts (fingerprints, sizes, the joined file must be called MurderInc.zip), the settings to use and why, what the game does on weaker servers, how to read the log, costs (extra minutes are billed monthly until lowered), and the corrections listed in PREFLIGHT.md. Rewrite docs/CURSOR_HANDOFF.md from PREFLIGHT.md's website section (the page: Play button that creates the iframe on click, the Linux connector host and the frame-src wildcard, keyboard-and-mouse gate for touch devices, own waiting and ending screens from the frame's messages, leave guard, controls text); it must not mention download links, and the owner uploads the build, not Cursor. Update PROGRESS.md and RESUME.md section 9. No links, emails, account names or person names in any of them.
Return: summary, the test result line, the runs with results, the stream proof in plain words, package_urls in part order (only in this report), the parts' sha256 in order, the joined sha256 and size, the exact E3DS settings and launch options the owner should use with version 3, everything still unproven, and the head commit.`, { label: 'release:package', phase: 'Package', schema: RELEASE })

phase('Check')
const check = await agent(`${CONTEXT}

YOU ARE THE INDEPENDENT RELEASE CHECKER for version 3. Trust nothing in the reports below; verify. Reports (JSON): RELEASE ${JSON.stringify(release)} FIXES ${JSON.stringify(fixed)}

On the box: download every package_url, check sizes and sha256 against the report and docs/LAUNCH.md section 9, run the owner's own join commands from LAUNCH.md, unzip -t, unpack as a brand-new non-root user into an empty folder and run it with E3DS's documented argument list and an -ABSLOG file: no display, with the signalling server, 5 minutes; confirm the log file, a received video stream (rtcview.py or the release engineer's tool), that mouse and keyboard input through the stream reach the game, a clean stop (exit 0) and that a forced crash of the Development game (-MIDev) leaves the crash report in the -ABSLOG file. Confirm the full test suite's result for the packaged commit. Read LAUNCH.md and CURSOR_HANDOFF.md as the owner would: every E3DS name must exist in E3DS's documentation (${SP}/e3ds-docs or the live pages), every command must work as written, nothing may contradict the package. Check the commits since ${BASE} contain no link, email, account name, person's name, licensed content or src/ change. Fix small doc errors yourself (commit, push); report everything else as a problem with its fix. ok is true only if the owner can upload this build and launch.`, { label: 'check:release', phase: 'Check', schema: CHECK })

return { input, render, reviews, fixed, release, check }
