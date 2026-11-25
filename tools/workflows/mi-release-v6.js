export const meta = {
  name: 'mi-release-v6',
  description: 'Release v6: package the head of the branch (sound fixes, 3c game fixes, the new guns and parts), prove sound and play through a stream, gate it, review it independently, fix what must be fixed; the lead uploads it to E3DS',
  phases: [
    { title: 'Merge', detail: 'one head, one test run, the weapons content imported in the packaging clone' },
    { title: 'Package', detail: 'package, sound guard, gate, stream proof (reviewers read meanwhile)' },
    { title: 'Check', detail: 'independent check of the zip' },
    { title: 'Fix', detail: 'only what must be fixed, then package again' },
  ],
}

const BRANCH = 'claude/tender-albattani-5q78qr'
const SP = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad'
const REPORTS = args || {}

const CONTEXT = `
PROJECT: MURDER INC., a first-person shooter in Unreal Engine 5.9 (C++ project unreal/MurderInc), packaged for Linux with Pixel Streaming 2 and streamed by Eagle 3D Streaming (E3DS) into the owner's website. Repo /home/user/MURDER-INC. (branch ${BRANCH}: commit and push there, small commits, each ending with exactly these two lines:
Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4
git pull --no-rebase before every push, git add with explicit paths only, never force-push, no pull request; no link, storage address, email, E3DS account or host user name, or person's name in any commit; no model name anywhere else).

WHAT THIS RELEASE IS: three lines of work end up in ONE package, release v6. (1) Sound fixes (the music kept its voices through a burst, the Goons' footsteps in 3D, the mono upmix, stereo, the package guards): docs/unreal/sound_review_3b.json says what was wrong. (2) Release 3c: the game ends with its session and idles when nobody watches, the encoder gets a quality range, quality steps for a slow card, the round trip reading (docs/unreal/DECISIONS.md, PROGRESS.md). (3) The weapons: the CHOPPER and NINE with their own art and mounts, SHORTY and STRETCH as new guns, the RATTLER as the sixth, our parts kit on every gun (docs/unreal/WEAPONS_R4.md, WEAPONS_R4_UNREAL.md, LOADOUT.md section 6). The reports of the three lines (JSON, may be partly empty): ${JSON.stringify(REPORTS)}.
The owner's priorities, in order: smooth and responsive play on E3DS (an RTX A4000 shared with nothing else once the leftover games are gone, 8 CPU threads, SM5, no Nanite), a controller that works, the guns with attachments, sound. Facts that matter: tools/box/cloud/lag-test.sh and its gate (docs/unreal/PREFLIGHT.md, tools/box/cloud/release-gate.txt, lag-gate.txt); the numbers of version 3b's gate on the box are in docs/unreal/DECISIONS.md (free GPU 60 fps worst frame 31 ms; load 20 ms 34.9 fps; load 35 ms 28.9 fps; the same limited to six CPUs 30.4 and 29.3): this release must be no worse. E3DS's own test of an upload failed to finish for over an hour on 2026-11-25 (their test server): the lead handles E3DS.

BOX AND ETIQUETTE (important): GPU box = Higgsfield rental, session id in ${SP}/box/session (now ec087d85-b777-4ece-be42-ccc063d225cf, RTX PRO 6000 Blackwell, 16 CPUs, 64 GB). Tool: mcp__Higgsfield__gpu_rental_exec (load its schema with ToolSearch "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__gpu_rental"), at most 90 s per call (it may time out at 60 s: check before repeating), so start long work detached (setsid nohup ... &) and poll. If the box is gone follow BOX.md's box-gone procedure exactly (same spec only; never more than one box). THE OTHER JOBS HAVE FINISHED (the sound fixes, the 3c code, the weapons integration; their engineers' clones /project/ue/repo-audio, repo-3c and repo-guns are idle) but the owner's browser runs on the box's desktop (pinned to CPUs 13 to 15) and the lead may run a short stream session from it. Therefore: (1) NEVER touch the browser (owner-browser, /tmp/e3ds-owner-browser, Firefox) or the files of version 3a and 4 in /project/ue/cloud (v3a-*.zip, v2-*.zip, old-*.zip, e3ds-upload-3a, e3ds-upload-3b); the packaging folders (/project/ue/repo-release, /project/ue/cloud/build-*, MurderInc-E3DS.zip, e3ds-upload/) are YOURS. (2) Work in the packaging clone /project/ue/repo-release (the 3b release engineer's; look at its git status and log first, commit nothing of anyone else's unfinished work, git pull --no-rebase the branch, and bring its generated content (the art and map copies, the audio import, and the weapons import of docs/unreal/WEAPONS_R4_UNREAL.md or WEAPONS_R4.md) up to date; copy generated content from another clone with cp --reflink=auto only, never move it). (3) Run every compile with nice -n 19 and at most 6 parallel jobs (UBT: -MaxParallelActions=6), and start no compile, cook or test suite while a gate run is active (pgrep -f lag-test.sh or a game process of another job: wait and re-check); lag-test.sh already serialises games on the GPU: use it. (4) Several games on one GPU produce the very stall you measure: one game at a time, throw away polluted runs. (5) Do not upload anything to E3DS (the lead does, from the box's browser), do not touch the owner's Higgsfield storage except for looking at pictures (BOX.md says how).



RULES: the gameplay rules must not change: the full automation suite (tools/box/test.sh MurderInc) must pass on the head you package, golden replays included, with no test weakened, skipped or re-recorded; the web game src/ is never touched; no pack, Epic or likeness content, link or account name is ever committed; plain English in docs and commit messages. Be honest in every report: say what was measured, what was only read, what is unproven. Never package a build that is silent, stalls, or crashes: report exactly what failed instead.`

const RELEASE = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    head_commit: { type: 'string' },
    tests: { type: 'string' },
    zip: { type: 'string' },
    sha256: { type: 'string' },
    size_bytes: { type: 'number' },
    gate_table: { type: 'string' },
    stream_proof: { type: 'string' },
    sound_proof: { type: 'string' },
    guns_proof: { type: 'string' },
    unproven: { type: 'array', items: { type: 'string' } },
    ok_to_upload: { type: 'boolean' },
    notes_for_lead: { type: 'string' },
  },
  required: ['summary', 'head_commit', 'tests', 'zip', 'sha256', 'size_bytes', 'gate_table', 'stream_proof', 'sound_proof', 'guns_proof', 'unproven', 'ok_to_upload', 'notes_for_lead'],
}

const REVIEW = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
      where: { type: 'string' }, evidence: { type: 'string' }, failure: { type: 'string' }, fix: { type: 'string' },
    }, required: ['title', 'severity', 'where', 'evidence', 'failure', 'fix'] } },
    checked_ok: { type: 'array', items: { type: 'string' } },
  },
  required: ['findings', 'checked_ok'],
}

const releasePrompt = (extra) => `${CONTEXT}

YOU ARE THE RELEASE ENGINEER of release v6.${extra}
1. ONE HEAD. git fetch and read git log for the three lines' final commits; make sure everything is on the branch and pushed; resolve conflicts if two lines touched the same file (small, explained commits). The head you package is the one you tested.
2. In the packaging clone bring the generated content up to date (the art and map copies, the audio import (tools/box/audio-import.sh), and the WEAPONS import: the weapons archive and the import script as docs/unreal/WEAPONS_R4_UNREAL.md or WEAPONS_R4.md says: the packager must run the same unpack and import there, because generated content is not committed). Build, then run the FULL automation suite until every test passes (no audio warning, golden replays untouched).
3. tools/box/cloud/package-cloud.sh all with MI_COMMIT=<head> and MI_TAG=v6, then tools/box/cloud/e3ds-verify.sh on the zip. The sound guard (pak_sounds.py) must say OK; say how many Sound Waves, and that the weapons' cooked assets (/Game/Weapons, the parts kit) are in the pak list.
4. THE RELEASE GATE on the zip, trimmed to what matters (unpacked by a new user, a new empty home for every run, E3DS's argument list, one game at a time; the box is yours): free GPU, load 8, 20 and 35 ms, the load-35 run limited to six CPUs (cpus=0-5), the Development game's Story run under load 35, the console-command check, and the pad and input proofs (lag-test.sh views proof-keys.txt and proof-pad.txt with audio=1). It passes when every run is CLEAN, no frame in play is over 100 ms, never more than 2 frames are owed, the game holds 60 on a free GPU, memory stays flat, every game stops with exit code 0, and no number is worse than version 3b's (see above). Add a run that exercises the guns: equip every gun, open the Workbench (E) on three guns and fit a part, fire, reload (extend a keys view script; the engineer of the weapons left notes in WEAPONS_R4_UNREAL.md); look at the received frames with the Read tool (at least 4) and say what you saw: do the guns look different, are the parts on the guns.
5. SOUND through the stream (rtcaudio.py, audio_find.py, sound_table.py, sound-keys.txt; the review's two faults especially): the music's stems keep their voices and their time through a long burst (hold the trigger through a magazine), a Goon far away is quiet and near is loud, nothing clipped, in Shipping, in the no-sound-card condition too.
6. Keep the final zip on the box twice: /project/ue/cloud/MurderInc-E3DS.zip and /project/ue/cloud/e3ds-upload/MurderInc.zip (a hard link is fine; E3DS needs exactly that file name), with a .sha256 file beside each; BUILD.txt names the pushed head; the zip holds no Saved/, symbols or logs; MurderInc.sh is byte-identical to the repository's.
7. Docs for a non-technical owner: docs/LAUNCH.md section 9 for release v6 (what changed for the player: sound, guns and accessories, anything not done, the E3DS settings including the session length and idle logout the lead set: 45 and 10 plus 2 minutes), PROGRESS.md, RESUME.md section 9, PREFLIGHT.md items closed with evidence.
Report through the schema; set ok_to_upload only if the gate passed, the tests passed, the sound and the guns were shown in the stream, and nothing in the zip is silent or stalling.`

phase('Merge')
const rel = await agent(releasePrompt(''), { label: 'release:v6', phase: 'Package', schema: RELEASE })

phase('Check')
const LENSES = [
  { key: 'stream-and-gate', prompt: 'YOUR LENS: play and smoothness through the stream. Unpack the zip as a brand-new non-root user into an empty folder, start it with E3DS\'s argument list and no display, and join with the box viewer: free GPU and under load 20 ms and 35 ms, a Story run and a Hold the Block wave by keyboard and mouse and then by pad only; read the probe lines; look at received frames with the Read tool. Check that the numbers in the release report are the numbers on the box, that nothing stalls, and that a viewer who leaves does not leave the game running (release 3c).' },
  { key: 'guns-and-sound', prompt: 'YOUR LENS: the guns and the sound as a player gets them. From received frames of the stream and the sound recordings: do six guns read as different guns; does the Workbench offer slots and parts on every gun and do the parts sit on the gun in the picture; is the sound right (music through a burst, footsteps by distance, levels, stereo); is anything missing that the web game has. Repeat the measurements of docs/unreal/sound_review_3b.json.' },
]
const reviews = (await parallel(LENSES.map(l => () =>
  agent(`${CONTEXT}

YOU ARE AN INDEPENDENT CHECKER of release v6. Trust nothing in the report; verify. The release engineer reported (JSON): ${JSON.stringify(rel)}
Do not edit, commit or package. ${l.prompt}
Report only real defects with evidence (a command and its output, a received frame and what it shows), the concrete failure each causes for a player on E3DS, and the exact fix. must-fix = silent, stalling, crashing, a rule changed, a gun or part visibly broken, a release hazard; should-fix = real but minor; nit = cosmetic. List what you checked and found correct.`, { label: 'check:' + l.key, phase: 'Check', schema: REVIEW })
    .then(r => r ? { lens: l.key, ...r } : null)
))).filter(Boolean)

const open = reviews.flatMap(r => r.findings.filter(f => f.severity === 'must-fix').map(f => ({ lens: r.lens, ...f })))
log('check: ' + open.length + ' must-fix')

phase('Fix')
const fixed = open.length === 0 ? null : await agent(releasePrompt(` A first package was made and an independent check found MUST-FIX items: ${JSON.stringify(open)}. The first release report (JSON): ${JSON.stringify(rel)}. Check each yourself (a checker can be wrong: say so with evidence), fix the real ones in the game or the tools with tests, run the full suite, package again (new sha256; replace the two copies on the box), repeat the gate lines that the change can affect and the stream proofs, and report. The old zip is kept as /project/ue/cloud/v6-first-<sha8>.zip.`), { label: 'release:v6-fix', phase: 'Fix', schema: RELEASE })

return { rel, reviews, fixed }
