export const meta = {
  name: 'mi-e3ds-crash',
  description: 'Find why the game crashes on Eagle 3D Streaming, fix it, repackage with logs, upload, verify',
  phases: [
    { title: 'Diagnose', detail: 'E3DS docs research + reproduce E3DS launch conditions on the box' },
    { title: 'Fix', detail: 'fix, logging-enabled package, upload parts' },
    { title: 'Verify', detail: 'independent check of fix and package' },
  ],
}

const CONTEXT = `
Repo /home/user/MURDER-INC. (branch claude/tender-albattani-5q78qr; commit and push there with the attribution trailers from the session rules; pull --no-rebase before push). Read docs/unreal/RESUME.md (sections 8 and 9), docs/LAUNCH.md, docs/unreal/BOX.md and tools/box/cloud/package-cloud.sh first.

SITUATION: the owner uploaded the 2026-11-24 zip (sha256 8378eedd...e570a, Linux, Pixel Streaming 2, Unreal 5.9 Preview, Shipping, MurderInc.sh runs "MurderInc-Linux-Shipping MurderInc -MICloud \"$@\"") to Eagle 3D Streaming (E3DS). E3DS's upload step "Test" (they start the app once to check it streams) PASSED and the dashboard said "Your app is ready to stream". The owner then opened the share link in Chrome: it showed "In Queue 1" and E3DS emailed: "MurderInc (v-1 Dev-chemistree) Crashed At: Tue Nov 24 2026 09:46:05 GMT-0800 (17:46:05 UTC) But no crashlog was found". Project settings the owner set: Locked Mouse, browser cursor off, browser resolution fixed 1920x1080, video quality High, codec H264, region Global, 15 min session, 5 min idle, password on, "Show the Unreal log in the browser console" on, crash-log email on, no launch options, no console commands. E3DS machines: RTX 4080/5070-class, 8 or 16 GB VRAM, Linux. We have no log from E3DS. Shipping builds write no log by default, which is probably why "no crashlog was found".

GPU BOX: Higgsfield GPU rental per RESUME/BOX.md. Shared state in BOXDIR=/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/box/{session,keys,used}. Last box 8b816116-3377-4331-9a05-d201df758d97; it has probably auto-stopped. If it is gone, follow the box-gone procedure exactly (next unused key from keys not in used, append to used, rent the SAME spec: desktop kind, RTX-PRO-6000, cpu 16, memory_gib 64, max_credits_per_hour 114, write the new id to session, run ensure-setup.sh until SETUP-DONE). Never rent anything else, never more than one box. /project is persistent; release copy /project/ue/repo-release, cloud dir /project/ue/cloud (build-Shipping, build-Development).

RULES: never commit pack/Epic/likeness content or any download link (public repo); never put the owner's email or E3DS account name anywhere committed except what is already there; do not touch the web game src/. Give file paths, commands and evidence in your report. Be concrete and honest about what was and was not proven.`

const DIAG_SCHEMA = { type: 'object', properties: {
  findings: { type: 'string' }, likely_causes: { type: 'array', items: { type: 'string' } },
  e3ds_launch_args: { type: 'string' }, recommended_fixes: { type: 'array', items: { type: 'string' } } },
  required: ['findings', 'likely_causes', 'recommended_fixes'] }

phase('Diagnose')
const [docs, repro] = await parallel([
  () => agent(`${CONTEXT}

YOUR JOB (research only, no box): from Eagle 3D Streaming's CURRENT public documentation (docs.eagle3dstreaming.com, their knowledge base, blog, forum, GitHub, and any public Q&A), find out precisely:
1. How E3DS launches a Linux Unreal Pixel Streaming build: the exact command line / arguments / environment they pass (e.g. -RenderOffScreen, -PixelStreamingURL or -PixelStreamingConnectionURL, -AllowPixelStreamingCommands, -ResX/-ResY, -ForceRes, audio, -vulkan, display/X server or headless), which user runs it, file permissions they expect (exec bit on MurderInc.sh and the binary), working directory, and whether they expect the launch .sh at the zip root.
2. Which Unreal versions and which Pixel Streaming plugin (PixelStreaming vs PixelStreaming2) they support for Linux, and any known problems with Pixel Streaming 2 or with UE 5.5+ on their Linux machines.
3. How to get the app log or crash log from E3DS (dashboard location, "Download log", support), and what makes them report "no crashlog was found".
4. Known causes of "Crashed ... no crashlog was found" and of "In Queue" that never starts, and what the upload "Test" actually checks.
5. Their Linux machines' GPU/driver/Vulkan details if published (ray tracing support, driver version).
Cite URLs for every claim and mark anything you could not confirm. Return structured results.`, { label: 'research:e3ds-linux', phase: 'Diagnose', schema: DIAG_SCHEMA }),
  () => agent(`${CONTEXT}

YOUR JOB (on the GPU box): reproduce the crash under the conditions E3DS most likely uses, and find its cause.
- Get a box (see rules). Use the packaged Shipping build in /project/ue/cloud/build-Shipping/Linux (the zip's contents; if it is missing, unzip /project/ue/cloud/MurderInc-E3DS.zip to a scratch dir) and build-Development for logs.
- Launch it the way a Pixel Streaming host does, several variants, each with a timeout and a captured log (Development has logs; for Shipping add -stdout -FullStdOutLogOutput and check exit code / signal / core): ./MurderInc.sh -RenderOffScreen -PixelStreamingConnectionURL=ws://127.0.0.1:8888 (and the older -PixelStreamingURL=), with and without a running signalling server (tools/box/cloud/stream-test.sh starts one), with DISPLAY unset, with no audio device, as a non-root user with a fresh HOME, with the working directory elsewhere, with -ResX=1920 -ResY=1080 -ForceRes, and with -vulkan. Also try the cases where the signalling server goes away or a "viewer" connects and disconnects (the game pauses on viewer leave via MICloud; check that path does not crash), and run long enough (5+ minutes) to catch crashes after start (the owner waited in the queue, so the crash may have been at start of a second session or after the Test's session ended).
- Also check robustness issues that could only appear on E3DS hardware: hardware ray tracing / Lumen HWRT required but unavailable, Nanite, VRAM 8 GB (try r.Streaming limits / -forcevramMB style emulation if possible), a Vulkan feature or driver extension the RTX PRO 6000 has but an RTX 4080/5070 Linux driver might not. Read the Shipping binary's startup code paths in Source/MurderInc (MICloud etc.) for anything that asserts or crashes when a value is missing (e.g. no viewer, no audio, no display, no gamepad, a missing file, a cloud-setting).
- Read /project/ue/cloud package logs for anything suspicious (cook errors that were ignored, e.g. the known ABP_FP_Pistol errors: could a missing cooked asset crash at runtime in a run?).
Report the exact commands, outcomes, log excerpts and the most likely causes ranked, and concrete fixes. Do not change game code yet; small diagnostic scripts in tools/box/cloud/ are fine (commit them).`, { label: 'diagnose:box-repro', phase: 'Diagnose', schema: DIAG_SCHEMA }),
])

phase('Fix')
const fix = await agent(`${CONTEXT}

Two diagnosis reports (JSON):
RESEARCH: ${JSON.stringify(docs)}
REPRO: ${JSON.stringify(repro)}

YOUR JOB: make the next E3DS upload start and stream reliably, and make sure that if it ever crashes again we get a log.
1. Fix every crash cause the reports found or rank as likely (game code, config, launch script, packaging), in /project/ue/repo-gameplay and the repo, so the Shipping build is robust to the E3DS launch conditions (headless/-RenderOffScreen, no audio device, no gamepad, no viewer yet, viewer leaves, 8 GB VRAM, GPUs without the same RT/driver features: fall back gracefully, e.g. software Lumen if hardware RT is unavailable). Keep the gameplay rules unchanged: tools/box/test.sh MurderInc must pass 105 of 105 (golden replays) before packaging.
2. Logging: make the Shipping build write a log file and crash reports (bUseLoggingInShipping in the Target.cs, crash reporter/minidump output in Saved), and have MurderInc.sh also tee stdout/stderr to a log file under the app folder, plus print a build stamp (commit) at start. Put a BUILD.txt with the commit at the zip root. Fix package-cloud.sh src() provenance (as_ue4 git) as the release check asked. Leave *.debug and *.sym out of the zip (keep them on the box). Also change the home screen controls row to show "P Pause" in cloud mode (-MICloud).
3. Re-run the repro launches from the REPRO report against the new Shipping package and show they no longer crash (5+ minutes, connect/disconnect a viewer if possible).
4. Package with tools/box/cloud/package-cloud.sh all, split into parts below 250 MB, upload each to the owner's Higgsfield storage the same way the previous release did (see PROGRESS "Repackage for the website"), download all back, join, sha256 and unzip -t. Delete local copies afterwards.
5. Update docs/LAUNCH.md section 9 (new parts table, sizes, sha256, date; a note on uploading it in E3DS as a NEW VERSION of the existing build "MurderInc" and where the log now is), a new section on getting the log from E3DS if it crashes again (from the RESEARCH report), PROGRESS.md and RESUME.md section 9. Do NOT commit the download links.
Return: summary, root cause (or the best-supported hypothesis, clearly labelled), what changed, test result, package_urls in part order, per-part sizes, joined sha256, size, and anything still unproven.`, { label: 'fix:package', phase: 'Fix', schema: { type: 'object', properties: {
  summary: { type: 'string' }, root_cause: { type: 'string' }, changes: { type: 'array', items: { type: 'string' } },
  tests: { type: 'string' }, package_urls: { type: 'array', items: { type: 'string' } }, sha256: { type: 'string' },
  size_bytes: { type: 'number' }, unproven: { type: 'array', items: { type: 'string' } } },
  required: ['summary', 'root_cause', 'changes', 'tests', 'package_urls', 'sha256', 'unproven'] } })

phase('Verify')
const check = await agent(`${CONTEXT}

The fixer reports (JSON): ${JSON.stringify(fix)}
Diagnosis: RESEARCH ${JSON.stringify(docs)} REPRO ${JSON.stringify(repro)}

YOUR JOB: independently and skeptically verify. On the box: download every package_url, check sizes/sha256 against LAUNCH.md, join in order, unzip -t, confirm BUILD.txt matches the pushed commit, MurderInc.sh is executable and logs to a file, no .debug/.sym, Pixel Streaming 2 present. Unzip to a fresh dir as a fresh non-root user and run the E3DS-style launches from the REPRO report (including -RenderOffScreen with a signalling server, viewer connect/disconnect if the scripts allow, 5+ minutes): no crash, and a log file is written. Confirm the claimed root cause is supported by evidence or say it is not. Check the commits contain no download link or licensed content and the web game src/ is untouched. Fix small doc errors yourself (commit, push). Return ok plus problems (each with a fix).`, { label: 'verify:release', phase: 'Verify', schema: { type: 'object', properties: {
  ok: { type: 'boolean' }, problems: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['ok', 'problems'] } })

return { docs, repro, fix, check }