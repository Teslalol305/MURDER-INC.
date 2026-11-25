export const meta = {
  name: 'mi-v3b-sound',
  description: 'MURDER INC. version 3b: version 3a plus sound (audio assets into the package, guards against a silent build, sound proven through the stream), reviewed, packaged, gated, uploaded, independently checked',
  phases: [
    { title: 'Sound', detail: 'audio assets where packages are made, guards and tests, every kind of sound measured through the stream' },
    { title: 'Package', detail: 'package, release gate, stream proof with sound, upload, docs' },
    { title: 'Review', detail: 'two adversarial reviews, while the package is made' },
    { title: 'Check', detail: 'independent release check with its own way of hearing the sound' },
    { title: 'Fix', detail: 'only if the check found a must-fix: fix, package again, check again' },
  ],
}

const SP = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad'
const BASE = '48be79e'

const CONTEXT = `
PROJECT: MURDER INC., a first-person shooter rebuilt in Unreal Engine 5.9 (C++ project unreal/MurderInc), packaged for Linux with Pixel Streaming 2 and streamed by Eagle 3D Streaming (E3DS) into the owner's website. Repo /home/user/MURDER-INC. (branch claude/tender-albattani-5q78qr: commit and push there, small commits, each ending with the attribution trailers given in your session rules; git pull --no-rebase before every push; never force-push; no pull request). Read first: docs/unreal/BOX.md (the box loop and its pitfalls), docs/unreal/RESUME.md (sections 8 and 9), the top three entries of docs/unreal/PROGRESS.md, docs/unreal/PREFLIGHT.md item V3-14, docs/unreal/AUDIO.md, docs/LAUNCH.md section 9, tools/box/cloud/package-cloud.sh, tools/box/cloud/lag-test.sh and lag-gate.txt.

WHERE WE ARE (2026-11-25, 09:30 UTC):
- Version 2 is what E3DS serves today. It starts and streams, but the owner cannot play it: the game stalls for seconds when the player turns.
- Version 3a (zip sha256 de41a7089a3e..., game and launcher from commit 6c4d810, game code last changed at 906dfdf) ends that stall (a pacer, dynamic resolution, a frame-rate target of 60, 45 or 30), adds exact mouse speed, clickable cards and a complete controller path. It passed the release gate on the zip (no frame over 50 ms in play at any load; version 2 as the control froze for 1.3 s under the same load), was played through a real stream, is in the owner's storage in nine parts and passed an independent check. The owner has not uploaded it yet.
- That check found that THE GAME HAS NO SOUND IN ANY PACKAGE SO FAR (PREFLIGHT.md V3-14): the game plays Sound Wave assets under /Game/Audio, the import that makes them (tools/box/audio-import.sh) was only ever run in the audio work's own clone (/project/ue/repo-audio), and the gameplay clone that every package is made from has the WAV files and no asset. Sound through the stream has therefore never been tested at all.
YOU ARE BUILDING VERSION 3b = version 3a plus sound. It is the build the owner will upload and launch. Nothing else in the game changes unless an item below says so: release B (PREFLIGHT V3-2, V3-4, V3-6, V3-7, V3-12, V3-13) is a later job.

E3DS FACTS (from its documentation; text copies of about 40 pages in ${SP}/e3ds-docs/*.txt, the page list in ${SP}/e3ds-docs/sitemap.xml; https://docs.eagle3dstreaming.com/wiki/<page>/ is readable with curl from this machine, not from the box): it starts the app's .sh with, always: -PixelStreamingURL=<ws url> -PixelStreamingID=<id> -AudioMixer -log -Unattended -StdOut -FullStdOutLogOutput -ABSLOG=<file>, plus -AllowPixelStreamingCommands -Windowed -ForceRes, -ResX/-ResY, codec, bitrate and QP options and the configuration's launch options. Every Linux session starts on a cold machine with a fresh copy of the zip; the machine has no display and should be assumed to have no sound card. Its player page starts a stream muted when the browser refuses autoplay (a speaker button unmutes).

GPU BOX: Higgsfield rental, session id in BOXDIR=${SP}/box/session (now ec087d85-b777-4ece-be42-ccc063d225cf, RTX PRO 6000 Blackwell 96 GB, 16 CPUs). Tool: mcp__Higgsfield__gpu_rental_exec (load its schema with ToolSearch "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__gpu_rental"), at most 90 s per call (it may report a timeout after 60 s: check before repeating), so start long work detached (setsid nohup ... &) and poll its log. If the box is gone follow the box-gone procedure of BOX.md exactly (same spec only: desktop kind, RTX-PRO-6000, cpu 16, memory_gib 64, max_credits_per_hour 114; never more than one box). /project is persistent: gameplay clone /project/ue/repo-gameplay, release copy /project/ue/repo-release, cloud dir /project/ue/cloud (build-Shipping, build-Development, src = the tools as pushed, MurderInc-E3DS.zip = version 3a, v2-ceaf828d.zip = version 2, lag/, chk/ = the last checker's scripts and runs, among them chk/rtcaudio.py, the viewer that reads the received sound). ONE GAME AT A TIME on the GPU: several games on one card produce the very stall the gate is about; lag-test.sh waits for the card and marks a run CLEAN or POLLUTED. Do not compile or cook while a gate run measures.
THE OWNER'S BROWSER: a Firefox window runs on the box's desktop (tools/box/cloud/owner-browser.sh, profile /tmp/e3ds-owner-browser). It is where the owner signs in to E3DS's control panel. Do not close it, do not read or copy anything from its profile, do not connect to its control port, do not take screenshots of the desktop. It draws in software, puts no load on the GPU and is not a game.

HOW TO LOOK AND LISTEN: to look at a received frame or keep a recording, PUT the file to the owner's Higgsfield storage (mcp__Higgsfield__media_upload gives a presigned address; PUT from the box with the headers Content-Type and If-None-Match: *; mcp__Higgsfield__media_confirm), download it to a folder under ${SP} on this machine, look at it with the Read tool, delete the local copy (BOX.md describes how a long address reaches the box). Nobody here has ears: sound is proven by measurement (what was received, when, how loud, and that it is the game's own sample), never by a packet count.

RULES: the gameplay rules must not change: tools/box/test.sh MurderInc must pass every test (golden replays included) before anything is packaged; new behaviour gets new automation tests; never weaken, skip or re-record a test to get there. Sound: use only the WAV files already under Content/Audio; do not add, replace, generate or re-record audio; never clone or imitate a real voice and never sample a released recording. Never commit pack, Epic or likeness content, any download link or storage address, the owner's email, an E3DS account or user name, or any person's name (public repository). Do not touch the web game src/ (read it as the reference). Never ask for or handle passwords. Write plain English in docs and commit messages. Be honest in your report: say what was measured, what was only read in source, and what is unproven.`

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
    sound: { type: 'string' },
    package_urls: { type: 'array', items: { type: 'string' } },
    part_sha256: { type: 'array', items: { type: 'string' } },
    sha256: { type: 'string' },
    size_bytes: { type: 'number' },
    owner_settings: { type: 'array', items: { type: 'string' } },
    unproven: { type: 'array', items: { type: 'string' } },
    head_commit: { type: 'string' },
  },
  required: ['summary', 'tests', 'runs', 'stream', 'sound', 'package_urls', 'part_sha256', 'sha256', 'owner_settings', 'unproven', 'head_commit'],
}

const CHECK = {
  type: 'object',
  properties: {
    ok: { type: 'boolean' },
    must_fix: { type: 'array', items: { type: 'object', properties: { title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['title', 'evidence', 'fix'] } },
    problems: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['ok', 'must_fix', 'problems', 'notes'],
}

phase('Sound')
const sound = await agent(`${CONTEXT}

YOU ARE THE SOUND ENGINEER OF VERSION 3b. Work in /project/ue/repo-gameplay on the box and in the repo. In this order:

1. THE ASSETS. With the gameplay clone's editor stopped, run tools/box/audio-import.sh there until its status ends with AUDIO-IMPORT-DONE and failed=0. The clone has 291 WAV files and the audio clone made 289 Sound Waves: find out what the difference is and whether a sound the game plays is among it. Then make sure the release copy and the package step really take the assets (read package-cloud.sh: where does Content come from, is anything under Content/Audio filtered out, are the assets cooked when nothing references them by a hard reference: the game loads them by path, so check the cook rules, for example DirectoriesToAlwaysCook, and fix what is missing).
2. NEVER SILENT AGAIN. (a) package-cloud.sh must refuse, with a plain message and a non-zero exit, to make a zip whose pak list (Manifest_UFSFiles_Linux.txt) does not hold every Sound Wave the game's data names; say how many it found. (b) The automation test MurderInc.Audio.Assets must FAIL, not warn, when an asset is missing, and a test must check that every sound id the game's audio data can play resolves to a Sound Wave that loads. (c) Bringing a clone up to date (sync.sh or ensure-setup.sh, whichever BOX.md says a clone is made usable with) must import the audio when assets are missing or older than their WAV files, so a new box or a new clone cannot package without sound. (d) A sound whose asset is missing is logged today at Verbose only: make it a warning, once per sound, and count missing and played sounds in the probe line (new fields at the end of the line; check tools/box/cloud/lag_sum.py still reads old and new lines).
3. THE LISTENING TOOL. Move /project/ue/cloud/chk/rtcaudio.py into the repo as tools/box/cloud/rtcaudio.py (read it first; keep what works) and make it a real instrument: it records what the viewer receives to a WAV file, prints loudness and peak per half second, counts clipped samples and gaps (silence inside a passage that should be continuous), can run the same viewer scripts as rtcinput.py and notes the time of each action it sends, so that the delay from a fire input to the start of the gun's sound can be measured; and a second tool (or mode) that takes the recording and a source WAV from Content/Audio and says whether, where and how strongly that sample is in the recording (correlation or a spectral fingerprint: choose what survives Opus). Check the instrument itself first with a known tone and a known sample through the same path.
4. PROVE THE SOUND, in the Development game and then in the Shipping game of a package (package-cloud.sh all once the suite passes), started with E3DS's argument list (it includes -AudioMixer), no display, as a fresh user. Read AUDIO.md and the audio data for the full list of what the game plays; for every KIND of sound (music per screen or state, interface sounds, each gun's shot, reload and dry fire, footsteps, enemy voices, hits and deaths, pickups, ambience, the briefing and debrief voices, anything else in the data) trigger it with a viewer script and report one table row: kind, how it was triggered, heard or not, which sample matched, level, delay after the input where there is one. Then the mix: nothing clips, the music does not drown the guns and the voices (compare the measured levels with the volumes the audio data and the web game's audio code give; src/ is the reference, read only), the volume rows of the Settings card work through the stream, what plays while paused and on the click card is what the web game does. If a sound never plays or plays at the wrong time or level because of a defect in the port, fix it with a test; do not redesign the mix.
5. WHAT THE SERVER GIVES. Read the game's log for the audio device it opened on the box (LogAudio, LogAudioMixer and the platform's lines) and find out what happens on a machine with no sound card and no sound service at all, which is what a cloud server is: does the mixer still run, does Pixel Streaming still get the sound? Make that condition on the box (for example a user and environment with no PulseAudio or ALSA device, or SDL's dummy driver) and measure it. If the launcher (tools/box/cloud/MurderInc.sh) should set something so that sound is certain there, add it, with a comment that says why, and prove both conditions.
6. SOUND UNDER LOAD AND ITS COST. With the GPU loaded as the gate does (lag-test.sh loads of about 20 and 34 ms a frame, where the game runs at 45 or 30 frames a second): the music has no gaps and the gun's sound still follows the input; the worst frame stays under 100 ms. With a free GPU the game still holds 60. Report the game's memory and the zip's size against version 3a.
7. Build if code changed, run the full suite on the box until every test passes with no audio warning, commit and push (repo and the box clone at the same commit), and write the entry "Version 3b: sound" at the top of docs/unreal/PROGRESS.md with the tables; update PREFLIGHT.md V3-14 and AUDIO.md with what is now true.

Report every item under done or not_done with evidence, the exact test result line, the head commit, and notes for the release engineer (the exact commands that prove sound in a package, what the gate must repeat, anything half-done).`, { label: 'impl:sound', phase: 'Sound', schema: WORK })

const LENSES = [
  { key: 'sound-as-played', prompt: `YOUR LENS: the sound a player gets. Prove or disprove with evidence: (1) every event of the web game's audio (src/, read only, and unreal/MurderInc/Content/Data for the exported data) has its counterpart in the Unreal game and plays the right sample at the right moment and level; list any sound that the data names and nothing ever triggers, and any trigger with no asset; (2) the tables in the sound engineer's report hold up: was each kind of sound really measured in the Shipping game of a package, is "heard" backed by a match against the game's own sample and not by a packet count, are the levels plausible, does anything clip, is the delay from input to sound acceptable for a shooter (say what it is made of); (3) the guards really make a silent build impossible: read package-cloud.sh, the tests and the clone set-up path and try to defeat each on paper (an empty asset, a WAV newer than its asset, a sound added to the data later, a cook that leaves the assets out); (4) no gameplay rule, no golden replay and no test was changed to make this pass.` },
  { key: 'server-and-stream', prompt: `YOUR LENS: sound on a cloud server and through the stream. Check against the Unreal 5.9 source on the box (/project/ue/UnrealEngine) and E3DS's documentation (find its pages about audio, autoplay, the speaker button and the microphone; curl them from this machine): (1) which audio device the Linux game opens with E3DS's arguments on a machine with no sound card and no sound service, whether the mixer then runs on a clock, and where Pixel Streaming 2 takes the sound from: can the stream be silent on E3DS although it is not on the box, and is the engineer's answer to that proven or assumed; (2) the stream's audio settings (sample rate, channels, Opus bitrate, any Pixel Streaming 2 audio cvar or E3DS argument that changes them) and the buffer sizes that make up the delay; (3) what the browser does: autoplay refused, E3DS's page muted at the start, the click card's text, a controller-only player who never clicks: does such a player get sound, and what must the owner's page do; (4) cost and risk: memory, load time, the size of the zip, a hitch when a sound is first played (a synchronous load on the game thread during play is a stall: check how and when the Sound Waves are loaded and whether the first shot or the first voice line loads from disk in the middle of a fight), and anything in the audio path that can block a frame.` },
]

const releasePrompt = (tag, extra) => `${CONTEXT}

YOU ARE THE RELEASE ENGINEER of version ${tag}. The sound engineer reported (JSON): ${JSON.stringify(sound)}${extra}

1. Confirm the full test suite passed on the head you package (run it if the head moved; no audio warning may remain). Then tools/box/cloud/package-cloud.sh all with MI_TAG=${tag} for the parts' names, and tools/box/cloud/e3ds-verify.sh on the zip.
2. THE PACKAGE HAS SOUND: the pak's list holds the Sound Waves (say how many under /Content/Audio/), and from the zip unpacked as a fresh user into an empty folder, started with E3DS's argument list and no display, a viewer hears the Shipping game: music on the home screen, the gun when it fires (matched against the game's own sample, with the delay after the input), a voice line, nothing clipped. Repeat it on the condition a cloud server gives (no sound card, no sound service). If the package is silent in either, do not upload: report exactly what failed.
3. THE RELEASE GATE ON THE ZIP as docs and lag-gate.txt describe it (unpacked by a new user, a new empty home for every run, E3DS's argument list): free GPU and the three loads, the Shipping game's Story run and the Development game under the heaviest load, the console-command check; use the viewer whose turns stop dead (lag-stops.txt) for at least the loaded runs. It passes when every run is CLEAN, no frame in play is over 100 ms, never more than 2 frames are owed, the game holds 60 on a free GPU, memory stays flat and every game stops with exit code 0. Report the table next to version 3a's numbers. If it fails, do not upload: report exactly what failed.
4. Prove play through the stream once more with proof-keys.txt and proof-pad.txt (mouse and keyboard, then a controller only), this time with the sound recorded; look at two received frames with the Read tool.
5. Split the zip into parts of at most 240 MiB, upload them to the owner's Higgsfield storage (file names MurderInc-E3DS-${tag}-part<k>-of-<n>.zip), confirm, download every part back, join, compare sha256, unzip -t, check that MurderInc.sh in the zip is byte-identical to the repository's, that BUILD.txt names the pushed commit, and that the zip holds no Saved/, symbols or logs. KEEP the final zip on the box twice: as /project/ue/cloud/MurderInc-E3DS.zip and as /project/ue/cloud/e3ds-upload/MurderInc.zip (E3DS needs exactly that file name; the lead may upload it to E3DS from the box's own browser), with a .sha256 file beside each. Keep version 3a's zip as /project/ue/cloud/v3a-de41a708.zip.
6. Docs for an owner who is not technical: docs/LAUNCH.md section 9 rewritten for version ${tag} (it replaces 3a there: parts with fingerprints and sizes, the join and upload steps, the E3DS settings, and a short paragraph about sound: what the player hears, that E3DS's page may start muted and where the speaker button is, what a controller-only player must do); take out the warning that the build is silent; PROGRESS.md and RESUME.md section 9; PREFLIGHT.md V3-14 closed with the evidence. No link, storage address, email, account name or person's name in any commit.
Return: summary, the test result line, the runs with results (the gate table), the stream proof in plain words, the sound proof in plain words (what was heard, how it was matched, levels, delay, the no-sound-card condition), package_urls in part order (only in this report), the parts' sha256 in order, the joined sha256 and size, the exact E3DS settings the owner should use, everything still unproven, and the head commit.`

const reviewPrompt = (l) => `${CONTEXT}

YOU ARE AN ADVERSARIAL REVIEWER of version 3b's changes: the diff from commit ${BASE} to the pushed head (git diff ${BASE}..HEAD -- unreal tools; read whole files where the diff is not enough) and the claims in the sound engineer's report (JSON): ${JSON.stringify(sound)}
Do not edit, commit, build, package or start a game: the release engineer is packaging and running the gate on the box right now, and a second game or a compile would spoil its measurements. Short read-only commands on the box are fine (reading logs, recordings, source and the files of finished runs).

${l.prompt}

Report only real defects with evidence (file and line, an engine source line, a recording or log with what it shows), the concrete failure each causes for a player on E3DS or for the release, and the exact fix. must-fix = the build may be silent, wrong or stalling for players on E3DS, a rule changed, or a release hazard; should-fix = real but minor; nit = cosmetic. List what you checked and found correct.`

const checkPrompt = (tag, rel, findings) => `${CONTEXT}

YOU ARE THE INDEPENDENT RELEASE CHECKER of version ${tag}. Trust nothing in the reports below; verify. RELEASE (JSON): ${JSON.stringify(rel)} SOUND ENGINEER (JSON): ${JSON.stringify(sound)}
REVIEW FINDINGS written while the package was being made (JSON; reviewers can be wrong): ${JSON.stringify(findings)}

On the box: download every package_url, check sizes and sha256 against the report and docs/LAUNCH.md section 9, run the owner's own join commands from LAUNCH.md, unzip -t, unpack as a brand-new non-root user into an empty folder and run it with E3DS's documented argument list and an -ABSLOG file, no display, with the signalling server.
SOUND, by a way of your own: do not reuse the engineer's verdicts and, where you can, not its decoder either (for example save the received Opus and decode it with ffmpeg or opusdec, or write your own short reader). In the Shipping game from that zip: the home screen's music, the gun's shot after a fire input (the game's own sample, found in the recording; say the delay), a voice line, footsteps while walking; nothing clipped; no gaps in the music under the gate's heaviest load. Then the same on a machine condition with no sound card and no sound service. A build whose sound you cannot prove is not ok.
THE GATE, yourself: free GPU and loaded (make sure no other game runs), a Story run with fast turns that stop dead: no game frame over 100 ms once the run is under way, never more than 2 frames owed, 60 frames a second on a free GPU, memory flat, clean stop (exit 0). Confirm mouse, keyboard and controller input still reach the game through a stream, and the full test suite's result for the packaged commit (no audio warning left).
THE REVIEW FINDINGS: for each must-fix and should-fix decide with evidence from the package whether it is real. Check the commits since ${BASE} contain no link, storage address, email, account name, person's name, licensed content or src/ change. Fix small doc errors yourself (commit, push); report everything else as a problem with its fix.
ok is true only if this build has sound that is proven as above, still passes the gate, and the owner can upload it as it is. Put every confirmed defect that must be fixed before the owner launches this build under must_fix (a real must-fix makes ok false); everything else under problems.`

const both = await parallel([
  () => agent(releasePrompt('v3b', ''), { label: 'release:v3b', phase: 'Package', schema: RELEASE }),
  () => parallel(LENSES.map(l => () =>
    agent(reviewPrompt(l), { label: `review:${l.key}`, phase: 'Review', schema: REVIEW })
      .then(r => r ? { lens: l.key, ...r } : null)
  )).then(a => a.filter(Boolean)),
])
let release = both[0]
const reviews = both[1] || []
const open = reviews.flatMap(r => r.findings.filter(f => f.severity !== 'nit').map(f => ({ lens: r.lens, ...f })))
log(`review: ${open.length} findings above nit (${open.filter(f => f.severity === 'must-fix').length} must-fix) from ${reviews.length} of ${LENSES.length} reviewers; package ${release ? 'made: ' + release.sha256 : 'NOT made'}`)

phase('Check')
const releases = [{ tag: 'v3b', release }]
const checks = []
let check = release ? await agent(checkPrompt('v3b', release, open), { label: 'check:v3b', phase: 'Check', schema: CHECK }) : null
checks.push({ tag: 'v3b', check })
let fixed = null

if (!release || !check || !check.ok) {
  phase('Fix')
  log(`version 3b is not releasable as it is (${!release ? 'no package' : !check ? 'no check result' : check.must_fix.length + ' must-fix'}): fixing and packaging version 3c`)
  fixed = await agent(`${CONTEXT}

YOU FIX WHAT STOPPED VERSION 3b. Sound engineer's report (JSON): ${JSON.stringify(sound)}
Release engineer's report (JSON, null if it made no package): ${JSON.stringify(release)}
Independent check (JSON, null if none): ${JSON.stringify(check)}
Review findings (JSON): ${JSON.stringify(open)}

For each must-fix of the check, each problem that stopped the package, and each review finding marked must-fix: check it yourself first; fix it if it is real, with a test where one is possible; if you reject it, say why with evidence. Nothing that makes the build silent, stalling or wrong for players on E3DS may be left open. Then build, run the full test suite on the box until every test passes, commit and push, and add the outcome to the PROGRESS.md entry. Do not package: the release engineer does that next. Report done / not_done per finding, the test result line, the head commit, and notes for the release engineer.`, { label: 'fix:v3b', phase: 'Fix', schema: WORK })
  release = await agent(releasePrompt('v3c', `
A FIRST PACKAGE (version 3b) was not released. Its release report (JSON, null if none): ${JSON.stringify(releases[0].release)} The check's verdict (JSON): ${JSON.stringify(check)} What was fixed since (JSON): ${JSON.stringify(fixed)} Version 3c replaces 3b everywhere (docs, part names); delete version 3b's parts from nothing: leave the storage as it is and say in your report which files there are stale.`), { label: 'release:v3c', phase: 'Fix', schema: RELEASE })
  releases.push({ tag: 'v3c', release })
  check = release ? await agent(checkPrompt('v3c', release, []), { label: 'check:v3c', phase: 'Fix', schema: CHECK }) : null
  checks.push({ tag: 'v3c', check })
}

const last = releases[releases.length - 1]
return { final_tag: last.tag, ok: !!(check && check.ok), sound, reviews, open, releases, checks, fixed }
