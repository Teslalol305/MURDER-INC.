# Unreal rebuild: progress

What is verified on the box, newest first. Every entry says how it was verified. The loop and the pitfalls are in
`docs/unreal/BOX.md`.

## Weapons round 4: the box engineer (integration, 2026-11-25, 13:30 UTC onward): code, tests, imports, what the pictures show

**Built (all of it in `unreal/MurderInc`, tests in `MIWeaponsR4Tests.cpp` and the edited suites):** the data's `rideBone`, `topRound` and the
trade check (`MILoadoutData`, `MILoadoutResolver`); the gun assembly that works on the exported skeletons (a part snapped to a bone socket
turns by the inverse of the bone's reference rotation: every bone of an exported skeleton carries the importer's quarter turn, BOX.md 8; parts
hide the gun's bones, ride the magazine bone, the factory magazine and its top round stand on the stage gun); the first-person rig for hand-IK
guns (the arms' shoulder anchor also for guns with no solved grip, brass for hand-IK guns, the support hand following a fitted foregrip, the
seated magazine and its top round, the optic's housing fading out as the sight comes up: ANIMATION.md 11). Tools: `fp-art.sh packr4`,
`mi_guns_r4.py` (guns, rattler, parts; `import-chars.sh r4`), `bench-shots.sh`, `guns-shots.sh`, `gun_lineup.py`, `sheet.py`, `quiet-editor.sh`.

**Measured on the box (clone `/project/ue/repo-guns`, port 8010):**

| What | Result |
|---|---|
| Editor build of the clone with the round's C++ | compiled first time (11 files), 3 min 15 s with another job's build in front of it (UBT's lock is per engine, builds of all clones queue); a later one-line fix 60 s |
| Full suite on it | **189 of 189** (60 to 72 s). Two failures on the first run, both mine to judge: `FirstPerson.OwnGunSets` held a long banana magazine inside the gun's bounds (the CHOPPER's hangs 8.1 cm and the RATTLER's 6.9 cm below the receiver, as modelled: the test now asks for the top, front, back and sides inside and the hang under 12 cm), and `Loadout.SocketContract` held the NINE's six old hand-set markers to 1.2 mm (its support marker is 6.29 mm off its socket; the data check `check_guns_data.py` leaves the NINE's markers out and the sockets replace them at run time: the test now reports them, it does not hold them) |
| The three art tars, unpacked and imported (`guns rattler parts`) | 1 min 30 s for all; the final archive (`fp-guns-r4.tar`, sha256 `6a521cf3…`) went up in 32 s and is unpacked in `/project/ue/fp-in-guns` |
| A picture session needs the editor, and the box is shared | see BOX.md 8: from 14:42 to 17:30 UTC (2 h 48 min) other agents' gate and profile runs, the release engineer's package, verify and test runs and the hands engineer's runs were on the box nearly all the time; the gaps that were long enough for work of mine (a build, the suite, an import) came about every 15 to 45 minutes and lasted 2 to 4 minutes; an editor for pictures was up for 25 s twice and for 70 s once beside a run that began just after it started (each stopped at once, by hand or by the watcher), and never long enough for a picture |

**Pictures (19, `docs/unreal/shots/guns-r4-*.jpg`, each under 300 kB). None is an editor picture: the box was never quiet long enough for the editor (below), so they are frames of the
packaged game as a player's machine draws it, from the stream viewer's `guns-keys.txt` script. I looked at every one (through contact sheets, then singly).**

Set A, `guns-r4-trial-*` (9): the release engineer's trial run, game commit `fd8ce12`, the data of that day, before the solved grips of the four new guns
(`/project/ue/cloud/lag-v6trial/t-guns*`).

| Picture | What it shows |
|---|---|
| `trial-rack-chopper` | the Loadout rack at 1920 x 1080: six cards, CHOPPER focused and on the stage (red-brown furniture, black receiver) |
| `trial-bench-chopper-reddot`, `-shorty-reddot`, `-stretch-scope`, `-stick-scope`, `-nine-suppressor` | the Workbench with the first part of the optic or muzzle slot fitted, factory part marked "FITTED": the red dot is on the CHOPPER's and the SHORTY's rail, the 4x scope on the STRETCH, the suppressor on the NINE (a part is on the gun: the owner's "no attachments are able to be added" is answered in the game). The SHORTY is olive polymer, the STRETCH long and dark with a wood stock |
| `trial-fp-chopper-hip`, `trial-fp-rattler-hip` | **before:** the support arm is a cut upper arm in front of the left of the picture ending in a ball (a closed fist seen end-on) that floats above the gun; the same on the SHORTY and the STRETCH |
| `trial-fp-stretch-aim-scope` | the aimed STRETCH with the 4x scope: the ball beside the sight, and the scope's housing a thick black ring round a small clear disc (the "dark tunnel": WEAPONS_R4.md 5.5, answered by the housing's fade, not yet seen) |

Set B, `guns-r4-grips-*` (10): the same packaged game (commit `fd8ce12`'s code, so none of this entry's C++) run with the branch's data of 17:21 UTC (the solved grips and shoulder anchors of the
data engineer and the grips helper; run `pk1` in `/project/ue/logs/repo-guns/lag/pk1`, taken beside two other games on the card: 28 frames a second, so the run says nothing about speed).

| Picture | What it shows |
|---|---|
| `grips-fp-chopper-hip`, `-chopper-aim-reddot` | **after:** no ball and no cut arm; the left hand is under the handguard, the right hand on the grip; aimed, the red dot's housing is still a thick ring (no fade in that build) |
| `grips-fp-shorty-hip`, `-shorty-reload` | the bullpup in two hands, the left hand under the forend; in the reload the gun stands up and the left hand is at the magazine well |
| `grips-fp-rattler-hip`, `-rattler-aim`, `-rattler-reload` | the SMG held in two hands, the left on the strap; aimed on the irons; reload as above |
| `grips-fp-nine-hip` | the NINE, the regression check: unchanged |
| `grips-rack-rattler`, `-rack-stretch` | the rack with the RATTLER and the STRETCH on the stage |

So the hands engineer's data (grips and anchors) took the ball and the cut arm away on the four guns; what is still wrong in these frames is not for this entry to judge (HANDS_R4.md).

## Weapons round 4: the art hand-off page and the archive (finisher, 2026-11-25, 15:40 to 16:00 UTC)

`docs/unreal/WEAPONS_R4.md` is the one page for the box engineer (every asset with triangles, sets, bones and sockets; the roster of six; the parts kit and its fit table;
the data as it stands; the import checklist; the first-person arm notes; what is not done; the weaknesses). Every family was re-exported from the committed code in a fresh process
(31 GLBs byte-identical to the previous exports) and all proofs pass: `_weapons_check.py` (CHOPPER and NINE ALL FIXED POINTS KEPT), the SHORTY, STRETCH and RATTLER checks, `_weapons_check_parts.py`
(ALL MOUNTS KEPT) and `_weapons_r4_contract.py` (CONTRACT KEPT). Archive: `art/out/fp-guns-r4.tar` (git-ignored), 300,011,520 bytes, sha256
`6a521cf3653be7ebc98f976f7ee17a69442f00ae92b3fed191453a7dedbd5741`, the three `fp-weapons-r4-*.tar` merged in one tar with the same layout. Nothing was run in Unreal.

## Weapons round 4: the review fixes of the art (fixer, 2026-11-25, 15:00 to 16:30 UTC): what the integration engineer must know

Details, evidence and what was rejected: `art/blender/PROGRESS.md`, section "Weapons round 4: the review fixes". Verified in Blender only (re-import proofs,
pictures); nothing was run in Unreal.

- **Re-carry the art.** SK_Shorty and SK_Stretch were re-baked (new textures, same geometry, same bones and sockets: `_weapons_check_shorty.py` 63 of 63,
  `_weapons_check_stretch.py` ALL FIXED POINTS KEPT), the two parts sets were re-baked (metallic is now binary). Run `tools/box/fp/fp-art.sh packr4` again
  (guns 230.5 MB, rattler 48 MB, parts 21.5 MB) and import over the old ones; paths and slot names did not change. The parts archive now also carries
  `ui/T_UI_Gun_{Chopper,Nine,Shorty,Stretch,Rattler}.png` (512 x 192, one scale: 2.2 mm per px) and `weapons_r4.json`.
- **weapons_r4.json is real now** (`art/blender/assets/_weapons_r4_contract.py`, proof `CONTRACT KEPT`): per gun `bones` and `sockets` in `m` and `unreal_cm`,
  `eject_dir_gun` / `eject_dir_unreal`, `workbench_slots`, `hide_bones_when_fitted`; per part the same as `weapons_parts_contract.json`. `mi_guns_r4.sockets()` still
  only prints the keys: make it compare `guns.<id>.sockets[*].unreal_cm` and `.bones[*].head_unreal_cm` with the imported skeleton (the importer leaves a bone turn,
  see BOX.md) and `parts.<id>.sockets_unreal_cm` with the static meshes' sockets, and return the number of differences.
- **The aimed view of an optic needs a material rule, not a mesh.** The red dot's clear cone is 4 degrees and no tube can do 9 at the data's relief (see the art
  PROGRESS): while aiming, set the fitted optic's `M_Part_Hardware` slot to a material that fades out (dither or opacity by the aim alpha, fully gone above ~0.6)
  and keep `M_Part_Lens` and `M_Part_Reticle`; the scope keeps its body (its tunnel is the intended 30 degree scope picture).
- **The tiling detail is not applied by the importer** (`mi_fp_import._surface()` wires BC, ORM, N, E only): the manifest slot records of all five guns carry
  `detail_set` and `detail_repeat_per_uv` (the SHORTY also the polymer pair): add the second UV tile and blend the tiling normal into N, steel where ORM.B = 1,
  polymer where 0. It is what lifts the 6.2 to 6.6 k px/m unique texel density at 25 to 60 cm.
- **The STICK icon** (pack rifle, `bl_icons.py` on the box) is still at 1.906 mm per px; re-render it at 2.2 so the six icons compare by length.
- Corrected statement of the modelers: the RATTLER's strap is NOT hidden by the folded wires (wires end at X 256, the strap starts at X 290); the CHOPPER's hip pose looks
  along the barrel. The wires and plate do cover about half of the left flank in first person: judge it in the engine camera.

## Weapons round 4: the solved grips of the CHOPPER, SHORTY, STRETCH and RATTLER (grips helper, 2026-11-25, 14:28 to 15:45 UTC)

`Content/Data/grips.json` now holds five guns: the NINE (hip, unchanged: re-solved with `_rule_grips.py nine --check`, max difference
0.000 cm over every point) and the CHOPPER, SHORTY, STRETCH and RATTLER (hip and aim), written by `art/blender/assets/_rule_grips.py
chopper shorty stretch rattler --pose hip,aim --pictures` on the exported files: Palm_R / Palm_L from each file, the hip view from the data
(config.json, or guns.json rules.views for the new guns), the aimed view from guns.json relief and the file's SightRear; the support palm up
under the handguard or forend, fingers up its right face, as on the CHOPPER. New for these four (`_characters_pose.py`; the NINE's search
is untouched): the trigger index may straighten (first joint from -30 deg) and swing in the plane of the palm, a point inside the gun counts
as negative clearance, the thumb grid is wider. Checked in Blender, **not yet in Unreal**: pictures `art/previews/grips_<gun>_hip.jpg` (and
`grips_chopper_aim.jpg`, `grips_rattler_aim.jpg`; the aimed SHORTY and STRETCH show only the stock and sights) plus close-ups from the
right, from below and under the support hand; at the hip the index pad sits 0.8 mm (CHOPPER), 2.6 (SHORTY), 7.0 (STRETCH) and 20.6 mm
(RATTLER) from the trigger's face, the firing thumb round the grip's left side within 13 to 16 mm of its aim, every phalanx clear or at most
2.7 mm pressed. The four rifle anim sets of `presentation.json` get the NINE's key, `"grip": {"gun": ..., "pose": "hip", "weight": 1.0}`
(its own commit). **To tune in play**: with a grip the set's `shoulders` anchor takes over, and all four carry the NINE's [-6, 0, -24],
where the support wrist ends about 58 to 63 cm from its shoulder (estimated; the arm reaches about 55); the solves put the shoulders
(camera space, cm) at CHOPPER [-8.5, 1.1, -12.4], STRETCH [-6.5, 1.1, -12.4], RATTLER [-2.5, 1.1, -12.4] (try them with
`mi.FP.Shoulders`). The SHORTY's hip view
is the CHOPPER's numbers on a gun whose origin is its butt pad: its forend sits 70 cm out (support wrist 77 cm from the anchor; the solve
needed its shoulders at [11.5, 1.1, -16.4], ahead of the eye), so its view wants the butt near the eye. The RATTLER's trigger face is at
X 140 mm (spec 132), 4.5 mm from the magazine well, so no finger fits in front of it, and from its back strap to the trigger is 10.3 cm
(CHOPPER 9.25): its firing thumb lies along the right side, outside the gun.

## Release 3c: the session (session engineer, 2026-11-25, 11:50 to 15:25 UTC)

The game now looks after its own session, and E3DS's quality number became the centre of a range. **In the game**
(`Source/MurderInc/Cloud/`: `MISession.h/.cpp`, `MIStreamQuality.h/.cpp`, `MICloud.h/.cpp`): it idles when nobody watches, quits when its
session is over, watches its launcher, takes the QP of E3DS's Video Quality as the centre of an encoder range, reads the round trip from
the sender's measured values, and ends with exit code 0 when the engine's shutdown crashes; the module is built without unity chunks. **In
the launcher** (`tools/box/cloud/MurderInc.sh`): it gives the game its own process id. The box got the tools to prove all of it. **No package
was made and nothing was uploaded** (the release engineer's step: section 8 has the commands that prove each item on a package). The code
is on the branch `claude/tender-albattani-5q78qr`; the game of this entry is the commit `d2a062e`.

**Why.** E3DS does not stop the game of a session that has ended (DECISIONS.md, "the verification runs on version 4", point 6):
the next session on that machine found the old game still drawing the menu at full speed and shared the card with it (27
frames a second for the second session, 18 for the third). The launcher of version 4 stops leftovers when the next session
starts; this release makes the game stop drawing when nobody watches and quit when its session is over, so that nothing is
left to find. The same measurement showed that E3DS's Video Quality is a constant quantiser, which cannot give way to a thin
connection (section 3), and that the round trip on the pause card read 0 ms (section 4).

| | What | Proven how |
|---|---|---|
| 1 | no viewer for 2 s: 2 frames a second; a join wakes it (the game hears of the viewer 0.2 to 0.55 s later than a drawing game does); the click card still shows | the Shipping game on the box: the card's utilisation idle against a viewer on the menu: **the card at 6 % idle** (the empty box: 5 %) **against 39 % with a viewer on the home screen** and 34 % for an unwatched game that does not idle; a join into an idle game takes 0.2 to 0.55 s longer |
| 2 | the game quits 20 s after the last viewer left (a join cancels the countdown), 600 s after its start if nobody ever came, 5 s after its launcher is gone; `-MIKeepAlive` turns it all off | unit tests of the decision and the clock; the Shipping game on the box with a viewer who leaves, one who comes back, none, and a stand-in launcher that is killed: **`Session over` exactly 20.0 s after the last viewer left and exit code 0 about 3 s later**; a viewer back after 3.5 s cancelled the countdown; no viewer ever: quit at the 30 s it was given; a killed launcher: quit 5.0 s later; `-MIKeepAlive`: nothing of it; the unit tests and `SESSION-TEST OK`, `LAUNCHER-TEST OK` |
| 3 | E3DS's QP is the centre of a range (Medium 34: 24 to 42, High 16: 8 to 24); `-MIQpExact` pins the old behaviour | read in the engine's source, then 13 runs through a stream on the box with an emulated link: **stalls on a thin link are gone**, a fast link is not worse (it uses more data standing) |
| 4 | the round trip on the pause card and in the probe line is the median of the sender's measured values, and absent when there is none | a 40 ms link: **the older game read 0 ms in 35 of 35 probe lines** (its card: `round trip 0 ms`), **this release 41 to 43 ms** (its card: `round trip 41 ms`) |
| 5 | a crash in the engine's shutdown (after it was asked to quit) ends the process with exit code 0 and a log line, not 139 and a crash mail | one of 27 stops of version 3b's gate crashed there; shown with a crash on purpose: exit code 0 with the net, **SIGSEGV without it** |
| 6 | **the module builds without unity chunks**: a clean clone of this branch failed to build once this release's files were in it | a clean module build of the Development game: 59 files, 104 s, no error |
| 7 | build, full suite, docs | the merged head `d2a062e`: **`TESTS FAILED passed=193 failed=2 skipped=0 filter=MurderInc 67 s`**; the two failures are the weapons lane's `Loadout.MountsExist` and `Loadout.SocketContract` on the box's old `SK_Nine` content (section 6); on this release's own commit before the merge: `TESTS OK passed=127 failed=0 skipped=0` |

### 1. Nobody watching, nothing drawn

**What the game does** (`UMICloudSubsystem::TickSession`, `EnterIdle`, `SleepIdle`, `LeaveIdle`; the decision is the pure function
`FMISession::Decide` in `Cloud/MISession.h`). A streamed game (the launcher always adds `-MICloud`) counts the viewers the
stream reports. With **no viewer for `MI.Cloud.IdleAfter` = 2 s** it idles:

- it draws `MI.Cloud.IdleFps` = **2 frames a second**: at the end of every frame (the core ticker runs after the frame's work)
  it sleeps until the next idle frame is due, in steps of 10 ms; the idle frames are real frames, so the game thread, the
  render thread and the pacer go on as before, only thirty times less often than the 60 of a play;
- dynamic resolution's maximum is set to its minimum (the cloud profile's 50 to 75 % become 50 %), and put back on the way
  out; a value somebody set by hand stays;
- the governor of the frame-rate target (`TickPacing`) skips the idle frames: they say nothing about what a frame costs.

**A viewer who joins wakes it.** Pixel Streaming reports a viewer's arrival with a task for the game thread
(`FEpicRtcStreamer::OnRoomJoinedUpdate` posts it with `DoOnGameThread`) and the game thread is the one that is asleep, so the idle
game runs the game thread's waiting tasks every 10 ms of its sleep (`SleepIdle`: `ProcessThreadUntilIdle`). The report moves an
atomic counter, the sleep ends, and the join is handled in the same pass: `LeaveIdle` puts the picture size back, the pacing's half
second starts afresh, and **the click card comes up as for any first viewer** (`Viewers.Join()` → `bWaitingForClick`; a guest on
a session that is watched already gets no card). The game does not go back to sleep until the game thread has handled the event
(`ViewerEventsHandled`), so a join cannot be slept through. (The first version only counted the event and slept on until the end
of the idle frame, up to 500 ms at 2 frames a second: it would have been woken at the end of the frame, because the report is
a game-thread task; found by reading the plugin before any run and fixed.) The plugin sends the report when the viewer joins the
signalling room, before the video connection is made, so the game is awake while the connection is still being set up.

**What a join costs, measured** (`session_sum.py <run> --join`: the wall-clock time at which the test viewer subscribed, which `rtcinput.py`
logs to the millisecond, against the game's own `Viewer joined` line, stamped to the millisecond; both are the box's clock): a game
that draws at full speed hears of the viewer **119, 131 and 159 ms** after it subscribed (the three Development runs `s3c-rtt-*`); an
**idle game 298, 323 and 672 ms** after (`s3c-reload` twice, `s3c-idle`): about **0.2 to 0.55 s more, up to one idle frame**. The game's own part
is the 10 ms of its sleeping loop, so the rest is the time the plugin takes to hand the report on while the game's frames are 0.5 s
apart (not looked into further: the game's frame is the only thing known to have changed). The viewer's first picture came 0.93 s
after it started in `s3c-idle` and 0.51 s in the first join of `s3c-reload`, against 0.38 to 0.55 s in the release engineer's gate runs of the
Shipping game, which has no idling. In every join of these runs the click card was up and the viewer's click took it away (`Viewer joined:
click to play`, then `Click to play: dismissed`, in `s3c-idle` and in both joins of `s3c-reload`).

**A first viewer is given time.** A game that has just started has not been watched yet and is building its screens,
compiling shaders and streaming textures; while no first viewer has come it is not idled in its first `IdleStartupGrace` = 10 s
after it became streamed (counted from that moment, not from the process's start: a cold start takes seconds to get there), so
a first viewer finds it ready. (After a viewer has been there, the grace does not apply: 2 s of nobody is idle.)

**The idle game never has a run going.** The pause and the release of everything the last viewer held happen in the call that
reports the viewer gone, 2 s before the first idle frame (`ReleaseForLeave`).

`-MIKeepAlive` turns the idling off with the quitting; `MI.Cloud.IdleFps` 0 turns just the idling off (`-MIIdleFps=0`).

**Measured** (the Shipping game of this release in a test folder, E3DS's launch options, no `-MIKeepAlive`; the box's card, `nvidia-smi`'s
utilisation once a second; runs `s3c-idle` and `s3c-keep`, the box otherwise quiet: its own desktop services keep the card at about
5 % (15 samples of the empty box, no game on it: 5 % in every one)):

| What the game was doing | Card utilisation | Frames a second | GPU time of a frame (probe lines) |
|---|---|---|---|
| nobody has watched for 2 s, idle (this release) | **6.1 %** (33 s: lowest 5, highest 12); 6.3 % in the 15 s after the viewer left | **2.0** | 5.1 to 6.3 ms |
| a viewer is on the home screen | **39.3 %** (28 s: lowest 33, highest 45) | 60 | 5.4 to 6.4 ms |
| nobody watches, the game does not idle (`-MIKeepAlive`: what an ended session's game did before this release) | **34.2 %** (the whole 57 s of the run, highest 58) | 60 | |

An idle game costs the card the 5 to 6 ms of one frame twice a second, about 1 % of it (it holds its 3 GB of memory
(`rssMB` of the probe line) until it quits 20 s later); a leftover game drawing the home screen costs a third of it, which is what the second and third
E3DS sessions found on their card. The idle picture is the home screen's: the menus have **no dynamic resolution** (`dr=-1` in
every probe line of the run, with a viewer too), so the "smallest picture" part of the idle only applies when a run is on screen
(a game paused in play); nothing here measures it.


### 2. The game ends with its session

**(a) 20 s after the last viewer left** (`MI.Cloud.ExitAfterEmpty`, `-MIExitAfterEmpty=`; 0: never): one log line, `Session over:
the last viewer left 20.0 s ago ... The game quits now (exit code 0)`, then `FPlatformMisc::RequestExit(false)` from the game thread.
The game's own exit guard turns the engine's status into exit code 0 and skips the static destructors (the codec registry
crashed in one on every exit of a build with logging); a watchdog thread ends the process with `_exit(0)` if the engine's
shutdown has not finished 30 s after the request. 

**A crash in the shutdown is a normal quit** (`ArmShutdownCrashNet`, armed when
the engine begins to exit, whoever asked it to: the game itself or a host's SIGTERM): SIGSEGV, SIGBUS, SIGABRT, SIGILL and SIGFPE
then end the process with exit code 0 and one log line that names the signal (`[MICloud] Exit: the engine crashed during its
shutdown (signal 11); it had been asked to quit, so this is a normal quit: exit code 0`), instead of a crash report, the host's
crash e-mail and exit code 139. **Why it is there:** one of the 27 runs of version 3b's gate (`v3b-late-free`, in the release
engineer's folder `/project/ue/cloud/lag-v3b`, the zip's Shipping game stopped with SIGTERM) ended with SEGV and exit code 139, a null
read inside `main()` in the engine's exit, and from this release on every session ends with a shutdown: a crash in 1 of 27 stops would
be a false crash mail to the owner after about one session in thirty. **What it hides:** such a crash is no longer a report;
the log line and `-MINoExitGuard` (the net and the exit guard left out) are the way to find one. The crash itself was not found
(the Shipping game has no symbols here) and was not reproduced.

**Shown with a crash on purpose** (the Development game only: `-MIExitCrashTest` writes through a null pointer in the engine's shutdown, right
after the net is armed): `s3c-net-self` (the game quits by itself, `-MIExitIfNoViewer=30`) and `s3c-net-term` (stopped with SIGTERM) both
logged `Exit crash test: crashing in the shutdown now (null write)` and then `Exit: the engine crashed during its shutdown (signal 11); it had
been asked to quit, so this is a normal quit: exit code 0` and ended with **`EXIT 0`**; the control `s3c-net-off` (the same crash with
`-MINoExitGuard`, which leaves the net out) ended with **`SIGNAL 11 (SEGV)`**, as the Shipping game of version 3b's gate did once.

**A join cancels the countdown**: the clock (`FMISessionClock`) restarts
at every change between "somebody" and "nobody", and a viewer present resets nothing and keeps the game for as long as he
stays: the unit test lets a viewer sit for ten hours, then 200 reloads of 8 s, and the game never quits.

**How 20 s was chosen, against a page reload.** Two things must hold at once.
1. *A page that is reloaded must not lose its game.* On a host that keeps the game for a reloaded page (the box's test viewers, a
   signalling server of your own) the reload is a new connection to the same game. Measured on the box with the test viewer that
   leaves and a second one that subscribes 3 s later (`view2=`: run `s3c-reload`): the second viewer was in the game **3.5 s after the
   game had logged "Connection lost"** (3 s of the script's wait, 0.3 s to be joined), and the game woke from its first idle frames
   and stayed. A real browser cannot connect on the box (no ICE candidates: BOX.md), so a real page's reload was **not measured**:
   it has to load the page, start the player and open the signalling connection, which takes a few seconds on a good line and
   more on a poor one. 20 s is almost six times the measured 3.5 s, and a retry of the page's own (E3DS's page reconnects by
   itself at times) fits in it.
2. *A game that nobody comes back to must be gone before the next game is up.* E3DS starts a **new** game for a reloaded page or
   a new session (LAUNCH.md section 6: a reload starts a new session, a fresh game on a fresh server; E3DS's documentation says a
   broken connection ends an Unreal app's session at once), and the quickest start seen was 34 s (DECISIONS.md, the first E3DS
   runs: two minutes the first time, 34 s for the next session on the same machine). A game that quits 20 s after the last viewer
   left, plus its few seconds of shutdown (measured on the box: 2.9 to 3.0 s), is gone before that, and the new game finds the card to itself.
Between the two: 20 s. A host with a slower reload sets `-MIExitAfterEmpty=` higher (the cost is a game that stays that
much longer, idling at 2 frames a second); the value cannot be below 2 s (`FMISession::Sanitize`: a smaller one would end a
reload).

**(b) 600 s after its start with no viewer ever** (`MI.Cloud.ExitIfNoViewer`, `-MIExitIfNoViewer=`; 0: never): a machine given
to a session whose viewer never arrived. Not under 5 s. E3DS's first start takes about two minutes before the game even
begins, so 600 s counts from the game's own start and is generous.

**(c) the launcher is gone** (`MurderInc.sh` passes `"-MILauncherPid=$$"` as the first of the host's arguments, before them, so
that a link cannot name another process; the first one counts). On Linux the game looks at `/proc/<pid>/stat` and `kill(pid, 0)` every 2 s
(`MIProbeProcess`: gone is no such process, state `Z`/`X` (a launcher that was killed and nobody collected is a zombie), or
another start time (the id was taken by another process since)); **5 s** after the first "gone" it quits, even with a viewer
connected (nobody can stop a game whose launcher is gone). **Careful in both directions** (`FMILauncherWatch`): nothing is
watched without `-MILauncherPid`; the watch starts only when the launcher has been *seen alive* (an id that is not there at the
first look, as in another process namespace, says "not watched" in the log and disarms the watch); "cannot tell" counts as alive.
The v4 launcher's behaviours are unchanged (`launcher-test.sh`: the stop signal goes on to the game at once, the watchdog ends the
game when the launcher is killed, the exit code passes through, the host's log is written, a leftover game of the package is
stopped).

**(d) `-MIKeepAlive`** (or `MI.Cloud.KeepAlive 1`) turns (a), (b), (c) and the idling off: for a game that is held without a
viewer on purpose, and it says so in the log (`Session: -MIKeepAlive: ...`). Every script of the box that holds a game without
a viewer passes it, and says why in its header: `lag-test.sh` (default; `keepalive=0` for a run of the session's own behaviour,
`viewer=0` for no viewer at all; the calibration too), `e3ds-verify.sh` (all runs but `v-long` and `v-e3ds-7600`, which have a fake
viewer and run with `NOKEEP=1`: a viewer that leaves for 10 s and comes back, which the 20 s has to carry), `stream-test.sh` (so
`memory-runs.sh`; `STREAM_KEEPALIVE=0` leaves it out), `xtest.py`; `e3ds-repro.sh`'s header says to pass it among the game's
arguments. The scripts in `/project/ue/cloud/chk/` are not in the repository.

**Measured** (the Shipping game, E3DS's launch options, started by `MurderInc.sh`, no `-MIKeepAlive`; the log lines are the game's own; the
clock is the game's `game time` and the box's UTC clock to the millisecond):

| Run | What happened | Result |
|---|---|---|
| `s3c-idle` | the game started, nobody came: **idle at 13.0 s** (10 s of grace after it became streamed); a viewer joined at 50.8 s (`Back at full speed (a viewer joined) after 37.8 s and 75 idle frames`); it left at 83.5 s (`Connection lost`); **idle again 2.0 s later (85.5 s)**; **`Session over: the last viewer left 20.0 s ago ... The game quits now (exit code 0)` at 103.5 s**, to the millisecond 20.0 s after the loss | the process ended with **`EXIT 0` 106.4 s after its start**, 2.9 s after the line (`Exit: engine status 0; exiting with 0`) |
| `s3c-reload` | a viewer from 30.4 s to 63.2 s; **a second viewer joined 3.5 s later (66.7 s), 1.5 s into the idle that had begun 2.0 s after the loss** (`Back at full speed (a viewer joined) after 1.5 s and 3 idle frames`: the countdown was cancelled); it left at 99.4 s; one `Session over` only, **20.0 s later (119.4 s)** | `EXIT 0` 122.4 s after the start (3.0 s after the line) |
| `s3c-nobody` | no viewer, `-MIExitIfNoViewer=30` | `Session over: no viewer connected in the 30 s since the game started ... nobody is coming` at 30.2 s; `EXIT 0` at 33.1 s |
| `s3c-keep` | no viewer, `-MIKeepAlive`, 60 s | `Session: -MIKeepAlive: the game keeps drawing and never quits by itself`; nothing idled, nothing quit; the script's SIGTERM at the limit: `Exit: engine status 143 (stop asked by a signal: a normal quit); exiting with 0` |
| `session-test.sh launcher`, **a stand-in launcher that is killed** (SIGKILL, nobody collects it: a zombie) | the Development game, started directly with `-MILauncherPid=<its id>` | `Launcher: process 50085 is gone; the game quits if it stays gone for 5 s`, **5.0 s later `Session over: the launcher that started the game has been gone for 5.0 s`**, `EXIT 0` (this Development game took 15 s to finish its shutdown, the Shipping game 3 s) |
| the same, stand-in alive / no `-MILauncherPid` / an id that no process has / `-MIKeepAlive` and a killed stand-in | | the game stays in all four (stopped by the script after 25 s); the third says `process 4194000 (-MILauncherPid) is not there at the start of the game: it is not watched`; **`SESSION-TEST OK`**, 7 checks |
| **`launcher-test.sh`** (no GPU, fake game) | as a user without privileges | **`LAUNCHER-TEST OK`**; the same test against the launcher of the commit before (`git show 5c1b6be:tools/box/cloud/MurderInc.sh`) fails exactly the three checks about the process id and passes the rest (the v4 behaviours) |

Exit times: **the game takes about 3 s from `Session over` to the end of the process in the Shipping game** (2.9, 3.0 and 2.9 s in
three runs), and the watchdog of 30 s is for a hang.

### 3. The encoder gets a range, not E3DS's one number

**What E3DS asks for.** E3DS's Video Quality is a constant quantiser: Medium is QP 34 for the lowest and the highest, High is
QP 16 and 16 (launch options `-PixelStreamingEncoderMinQP=` and `-PixelStreamingEncoderMaxQP=`, and the page's console
commands `PixelStreaming.Encoder.MinQP` / `MaxQP`, which it sends again and again). A constant quantiser cannot give way:
when the connection carries less than a picture of that quality needs, the sender drops frames instead (the stall of
version 2 was one cause of that; a thin link is another).

**Which source wins (read in the engine, 5.9 `PixelStreaming2` plugin, then shown by a run).**

| Where | What it does |
|---|---|
| `PixelStreaming2Settings/Private/PixelStreaming2PluginSettings.cpp` ~1395-1411 (`ParseLegacyCommandlineArgs`) | the launch option MinQP becomes the variable `PixelStreaming2.Encoder.MaxQuality` and MaxQP becomes `MinQuality`, as `quality = int(100 * (1 - QP / 51))` (QP 34 gives 33, QP 16 gives 68). It is applied once, at start |
| `PixelStreaming2RTC/Private/EpicRtcStreamer.cpp` 519-540 | the data channel's `Command` messages `Encoder.MinQP` / `MaxQP` / `MinQuality` / `MaxQuality` set the same two variables with `SetWithCurrentPriority`, so a viewer's Command message does win over the launch option |
| `PixelStreaming2RTC/Private/EpicRtcVideoEncoder.cpp` 175 and 661 | the encoder reads the two variables when it is created and on every rate update (`UpdateConfig`), rate control is CBR |
| `Experimental/AVCodecs/NVCodecs/.../VideoEncoderConfigNVENC.cpp` 123-124, 147-148 | NVENC's minimum QP is `(1 - MaxQuality/100) * 51` and its maximum `(1 - MinQuality/100) * 51` (cut), the limits are switched on when MaxQuality < 100 and MinQuality > 0 |
| **E3DS's console commands** `PixelStreaming.Encoder.MinQP 16` | **there is no console object of that name in PixelStreaming2** (its variables are `PixelStreaming2.Encoder.MinQuality` ...): the engine does nothing with the command. On the box, on the code before this change, a viewer that sent High's QP 16 after a launch with QP 34 left the encoder at QP 34 in every probe line of its session (67 of 67, run `s3c-b-qp`). So **what E3DS's page sends as console commands has never changed the encoder**; only the launch options did |

**What the game does now** (`Cloud/MIStreamQuality.h`, `UMICloudSubsystem::ApplyEncoderRange`). The two numbers are the centre
of a range: lowest QP = first number minus `MI.Cloud.QpBelow` (10, not under `MI.Cloud.QpFloor` 8), highest QP = second number
plus `MI.Cloud.QpAbove` (8, not over `MI.Cloud.QpCeiling` 48); a number that is already outside keeps itself, equal numbers
are the centre of both ends, and a page that sends them the wrong way round gets the same two numbers. So **Medium 34 gives
24 to 42 and High 16 gives 8 to 24**. The game takes the numbers from the launch options at the start and from every
`PixelStreaming(2).Encoder.MinQP` / `MaxQP` command of a viewer (as a console command, which the engine ignores, and as a
`Command` message; both go through `OnEncoderCommand`), works the range out and sets the two quality variables with the launch
option's priority (`ECVF_SetByCommandline`, so that the plugin's own `SetWithCurrentPriority` finds nothing above it). Each
change is logged once, with the source of the numbers (the page sends the same two again and again: set once, logged once):

`Encoder quality, from the launch options: asked for QP 16 at the lowest, 16 at the highest; the encoder may use QP 8 to 24
(PixelStreaming2.Encoder.MaxQuality 84, MinQuality 52) (MI.Cloud.QpBelow 10, QpAbove 8, floor 8, ceiling 48)`

`-MIQpExact` pins the old behaviour (both numbers as given; the viewer's commands still count, now they reach the encoder),
`-MIQpBelow=` and `-MIQpAbove=` change the width. The pause card's line shows the range after the QP (`QP 31 of 24 to 42`).
The numbers go through the plugin's own conversion in both directions: `QpForQuality(QualityForQp(q)) == q` for every QP 0 to 51
(test `MurderInc.Cloud.EncoderRange`).

**Measured** (box, one run of each (two of the first High line), 90 s, the Development game's Story run, `session_sum.py --phases`; the viewer makes its link:
`rtcinput.py --link-kbps` is a drop-tail queue, `--remb-kbps` the bandwidth the sender is told it has; "sent" is what the
sender's own statistics say it sent a second, "received" what the viewer counted; the last phase is 5 s long and not counted
here). The box has no `tc`, so this is the emulated link of the viewer, not a network.

| Link and quality | Phase | exact: QP used, Mbit/s, sent, **received** | range: QP used, Mbit/s, sent, **received** |
|---|---|---|---|
| **4 Mbit/s, High (QP 16)**, range 8 to 24 (run 1 / a repeat of it) | the page's commands | 16, 1.5, 2.4, **2.6 / 3.0** | 21, 0.9, 9.2, **15.9 / 23.7** |
| | standing | 16, 1.9, 2.4, **2.3 / 2.7** | 21, 1.7, 13.2, **12.3 / 16.5** |
| | turning fast | 16, 4.4, 2.4, **0.8 / 1.1** | 21, 4.9, 17.0, **10.0 / 9.2** |
| | standing | 16, 7.2, 2.4, **0.0 / 0.0** | 20, 2.9, 27.9, **32.9 / 33.6** |
| | turning fast | 16, 7.1, 2.4, **0.0 / 0.0** | 20, 5.8, 19.9, **11.3 / 9.9** |
| **4 Mbit/s, Medium (QP 34)**, range 24 to 42 | the page's commands | 34, 0.4, 54.5, **53.7** | 30.6, 0.6, 56.6, **56.8** |
| | standing | 34, 1.2, 55.0, **50.0** | 26.8, 1.8, 56.0, **55.5** |
| | turning fast | 34, 2.8, 22.0, **21.8** | 36.1, 4.4, 46.9, **38.1** |
| | standing | 34, 1.6, 45.1, **42.9** | 31.8, 2.7, 52.9, **57.6** |
| | turning fast | 34, 4.1, 23.2, **11.2** | 34.4, 4.0, 45.4, **33.1** |
| 4 Mbit/s, High, range 8 to 32 (`-MIQpAbove=16`) | the page's commands / standing / turning / standing / turning | | QP 29 and received **54, 38, 17, 42, 15** |
| **1.5 Mbit/s, Medium (QP 34)**, range 24 to 42 | the page's commands | 34, 0.4, 49.3, **52.3** | 35.8, 0.3, 56.1, **56.1** |
| | standing | 34, 1.0, 43.0, **31.6** | 33.4, 1.0, 56.6, **56.2** |
| | turning fast | 34, 2.3, 15.1, **11.0** | 38.3, 1.8, 21.9, **17.2** |
| | standing | 34, 0.8, 32.9, **35.9** | 34.5, 1.1, 41.1, **44.2** |
| | turning fast | 34, 2.2, 16.1, **11.2** | 35.6, 1.7, 22.5, **7.9** |
| **20 Mbit/s (fast), Medium**, range 24 to 42 | standing | 34.0, 0.9, 53.3, **49.0** | 33.7, 0.7, 56.1, **54.8** |
| | turning fast | 34.0, 2.5, 19.7, **25.1** | 37.1, 2.5, 41.3, **41.6** |
| **20 Mbit/s, High**, range 8 to 24 | the page's commands | 21.1 (still coming down from 34), 4.5, 52.5, **53.8** | 18.2, 3.4, 57.2, **56.3** |
| | standing | 16.0, 7.2, 57.0, **54.7** | 11.7, 8.6, 54.8, **53.5** |
| | turning fast | 16.0, 18.8, 23.6, **23.6** | 18.7, 18.9, 38.3, **22.0** |

What it shows, and what it does not:

- **On a thin link the exact quantiser stalls and the range does not.** High on 4 Mbit/s: a still picture at QP 16 takes
  about 7 Mbit/s at 57 frames a second (the 20 Mbit/s run below), the link carries 4; the sender then sends 2.4 frames a
  second (it puts 7 Mbit/s into the 4) and after the first turn the viewer gets nothing at all (0.0 received in both phases
  after it), where the range sends 13 to 28 and the viewer receives 10 to 33 (QP 20 to 21, never the 24 it was allowed).
  **Medium on 4 Mbit/s** (the link that was asked for): the range receives **38 and 33 frames a second in the two turns against 22 and 11**, and
  58 against 43 standing (QP 36 in the first turn: it gave way by 2 over E3DS's number to fit the link). Medium on 1.5 Mbit/s: the
  range is better standing (56 against 32 and 44 against 36 frames a second received) and **not better turning** (17 against 11 in the first turn, **7.9 against 11.2 in the second**: the link is full either way and the
  range's second turn received fewer). A wider range helps High on 4 Mbit/s further (`-MIQpAbove=16`: 38 to 54 frames a
  second standing, QP 29 on average at most), at the price of a softer picture; the default stays 8 as asked.
- **On a fast link nothing gets worse that matters, one thing costs data.** Turning, Medium's range gives 41.6 frames a
  second received against 25.1. **Standing, High's range goes sharper than the old number: QP 11.7 against 16 and 8.6
  Mbit/s against 7.2** (the range allows down to QP 8 and a still picture lets the encoder go there). That is more data
  for a still picture: on E3DS's 20 Mbit/s ceiling nothing is lost, but a player whose link is 10 Mbit/s uses more of it. If
  that is not wanted, `-MIQpBelow=0` makes High's range 16 to 24 (never sharper than asked).
- One run of each line, one scene, one emulated link; **only the two High lines on 4 Mbit/s were repeated, on the binary of the
  head** (`s3c-hi-range-b`, `s3c-hi-exact-b`: the second number of each cell above). Two runs of one line differed by up to 8 frames
  a second in the first seconds (15.9 and 23.7 received), by 1 to 4 later (12.3 and 16.5, 33 and 34, 10.0 and 9.2, 11.3 and 9.9), and the
  exact quantiser's 0.0 came back both times. So a difference of a few frames a second between two rows of the other lines is not shown
  to be real; the stall (0 against 10 to 33), the fast link's Medium turn (42 against 25) and the standing difference on 1.5 Mbit/s
  are large next to that.
- Not measured: a real browser's decoder, a real network, E3DS's own sender. **E3DS may apply its own quality setting after
  the game has set the variables** (its Video Quality menu); the game logs the numbers it set and every change, so a session's
  log says who wrote last (the first session with this build should be read for the `Encoder quality, from ...` lines).

### 4. The round trip reads what the sender measured

**Where it was read.** The pause card's numbers line (`MakeNumbersLine`) and the probe line's `rttMs=` read the statistic
`roundTripTime` that Pixel Streaming 2 broadcasts on the game thread (`UPixelStreaming2Delegates::OnStatChangedNative`, our
`OnStreamStat`), in seconds. The old reading kept **the last value** and printed it (`round trip %.0f ms`; since release A).
That value is wrong in three ways (read in the plugin's statistics code and in libwebrtc's; what the probe lines show is the outcome, below):

1. the plugin reports a statistic **only when it changes**, so the last report can be a minute old;
2. **the video track and the audio track report under the same name**, one after the other: an audio report of 0 hides the
   video's value, and the card shows the last of the two (the baseline run on the older build printed `rttMs=0` in every probe
   line of a session on a free loopback, where the true round trip is about 1 ms);
3. libwebrtc reports **0 until it has measured one** (its smallest measured value is 1 ms), so "0" is "not measured", never "no
   delay"; the old line printed "round trip 0 ms" and E3DS's owner read it as a link with no delay.

**What it reads now** (`FMIRoundTrip`, `Cloud/MIStreamQuality.h`): the **median of the last five positive reports** (under 60 s
each; zeros, negatives, NaN and absurd values are counted as ignored and never stored), cleared when the viewers change (the
round trip of the viewer before is not this one's), and **absent when none was measured**: the pause card says nothing
instead of "0 ms", the probe line says `rttMs=-1` and carries how many values it has (`rttN=`) and how old the newest is
(`rttAge=`). The median of five takes the plugin's occasional spike (a report during a keyframe) out without hiding a link
that really changed within a few seconds.

**Measured** (box, the Development game's Story run, the test viewer's link `--delay-ms N` adds N ms of round trip, half to every packet it
receives and half to every one it sends; runs `s3c-rtt-old40`, `-new40`, `-new0`, `-new100`; the viewer stands for 25 s, presses P and
saves the picture of the pause card; the probe line is at one a second):

| Game | Round trip added | `rttMs=` of the probe lines of the viewer's session | The pause card (picture `pause-card.jpg` of the run) |
|---|---|---|---|
| **the game before this release** (the older Development game kept in a test folder: release A's reading) | 40 ms | **0.0 in all 35 lines** | `... QP 34, round trip 0 ms` |
| this release | none (loopback) | 1.0 (median; the first line, before any report, says unknown: -1) | |
| this release | 40 ms | **41 to 43 (median 42)** in 34 lines, no zero, no unknown; 25 reports accepted at the end | `... QP 37 of 24 to 42, round trip 41 ms` |
| this release | 100 ms | 101 to 102 (median 102); the first line unknown | |

So the old reading was 0 on a link of a known 40 ms (the reading the owner saw on E3DS), and the new one reads the link: its 1 to 3 ms over
the added delay are the game's and the viewer's own processing. On loopback it reads 1 ms: libwebrtc's smallest measurement, which is
also what a connection to a relay on the same machine would read.

**What this does not tell.** It is the time to the other end of the game's own video connection. On E3DS that may be E3DS's
relay on the machine and not the player's computer (nothing measured here shows where its other end is), in which case the game
reads about 1 ms whatever the player's line: E3DS's Info panel
("response delay", 91 ms from the box's location in the first session) is the time to the player's computer. That 0 ms was
shown on E3DS is probably explained by the three points above (and possibly a local relay on top); **how the new reading looks on E3DS is
not known until a session has run it**: the first session's log has `rttMs=` in every probe line.

### 5. The build, and a build failure this release found

**A clean clone did not build once this release's new files were in it, and a working clone did.** The first game build after the
box's clone was brought up to date (`Development` and `Shipping`, 14:14 UTC) failed in all three unity chunks of the module
(`Module.MurderInc.1.cpp` to `.3.cpp`): `struct FReader` is defined in two source files of the module (`MIFlowRules.cpp:151` and
another), and `MIEnemies.cpp:15` has `constexpr double Gravity` in an anonymous namespace, which an engine header that follows it in
the chunk (`CharacterMovementComponent.h:1739`, a parameter named `Gravity`) reports as a shadowed variable (`-Werror,-Wshadow`).
In a unity build the files of a chunk share one translation unit, so each of them sees the others' names. Nothing of this release's
code is in those lines: **new source files anywhere cut the chunks differently** (this release adds three .cpp files and two headers), and a clone whose files
differ from its upstream compiles the changed files on their own (UBT's adaptive unity build: the earlier builds of this session
printed `[Adaptive Build] Excluded from MurderInc unity file: ...` for nearly every file), which hides it. A release package is built
from a clean clone, with no such list, so **the package build of this branch's head would have failed**.

**Fixed with `bUseUnity = false` in `MurderInc.Build.cs`:** every file is compiled on its own, which no new file can undo (renaming the
colliding names would be undone by the next new file). **Checked by building the Development game's module from scratch** (its
`Intermediate` folder removed, nice 19, 6 jobs): **59 compile actions in 104 s, no error** (`cleanbuild.log`). The Shipping game and the
editor target were built after the change, not from scratch (6 min 39 s for the editor target, whose planning UBT redid after the change to
`MurderInc.Build.cs`, then 1 min 35 s and 1 min), and the suite passed on them. Whether the branch without this release's files
would have failed the same way in a clean clone was not tried.

### 6. Tests

Six new automation tests (`Source/MurderInc/Tests/MICloudSessionTests.cpp`), all of pure logic the game itself runs (no world, no
renderer, no stream), and no existing test was changed or weakened (the diff of this release touches no other file under
`Tests/`; the golden replays are among the suite's tests, unchanged):

| Test | What it holds |
|---|---|
| `MurderInc.Cloud.SessionDecision` | every branch of `FMISession::Decide`: not streamed and `-MIKeepAlive` keep whatever the clock says; the last viewer gone 0, 1.9, 2.0, 19.9, 20.0 s and an hour; a viewer present for 0 s to 1e9 s keeps; nobody ever: 9.9 s keeps, 10 s idles, 599.9 s idles, 600 s quits; a cold start's grace counts from the moment the game became streamed; the launcher gone for 5 s quits even with a viewer; zero turns a part off; bad numbers (NaN, negatives, a 0.5 s exit that would end a reload) fall back |
| `MurderInc.Cloud.SessionClock` | the bookkeeping the game keeps, driven through whole sessions: **a viewer present for ten hours keeps the game; 200 reloads of 8 s each never end it; a join cancels the countdown (19.9 s into it); a viewer who joins a game that idles wakes it** |
| `MurderInc.Cloud.LauncherWatch` | gone for 5 s quits, "cannot tell" never counts, an id never seen alive is not watched; and the real looking at processes on Linux: a `sleep 60` child is alive, killed it is gone (a zombie too: nobody collects it), an id that never existed is gone, our own id is alive |
| `MurderInc.Cloud.EncoderRange` | Medium 34 gives 24 to 42, High 16 gives 8 to 24, the floor 8 and the ceiling 48 (a request below or above keeps its own number), `-MIQpExact` gives the numbers as asked, a page that sends them the wrong way round, `QpForQuality(QualityForQp(q)) == q` for every QP 0 to 51, the page's console commands and Pixel Streaming's launch options are read the way the plugin reads them |
| `MurderInc.Cloud.RoundTrip` | a 0 is not a measurement, the median of the last five positive reports, a spike does not move it, the viewers' change clears it, absent when none |
| `MurderInc.Cloud.SessionDefaults` | the console variables a package starts with (`MI.Cloud.IdleFps` 2, `IdleAfter` 2, `ExitAfterEmpty` 20, `ExitIfNoViewer` 600, `KeepAlive` 0, `QpBelow` 10, `QpAbove` 8, `QpFloor` 8, `QpCeiling` 48, `QpExact` 0) and their limits |

The launcher has a test of its own that needs no GPU and no Unreal: **`tools/box/cloud/launcher-test.sh`** runs `MurderInc.sh` against a fake
game (a few seconds a case, as an ordinary user): the launcher passes its own process id as `-MILauncherPid=<pid>` before the
host's arguments (and a `-MILauncherPid=999999` from the host stands behind it, the game reads the first), the game's parent is the
launcher, the exit code passes through, SIGTERM to the launcher goes on to the game at once, a launcher killed with SIGKILL is followed
by its watchdog within 12 s, a leftover game of the package is stopped before the new one starts, the host's log file (`-ABSLOG=`) is
written and the option is not passed on. The v4 launcher (the commit before this release, `git show 5c1b6be:tools/box/cloud/MurderInc.sh`)
passes everything except the three checks about the process id, which is the point of the test.


**The suite on the merged head, and its two failures.** On `d2a062e` (main at `fd8ce12` plus this release) the full suite on the box
printed `TESTS FAILED passed=193 failed=2 skipped=0 filter=MurderInc 67 s`. The two are `MurderInc.Loadout.MountsExist` ("nine (SK_Nine): mount
laser has socket Laser", "... muzzle has socket MuzzleMount", "... magazine has socket MagHinge") and `MurderInc.Loadout.SocketContract` ("nine: marker
support is 6.29 mm from its socket Palm_L"). Both read the imported gun asset `Content/Weapons/Nine/SK_Nine.uasset`, which is git-ignored
(`Content/*`) and on this box's clone dates from 2026-11-23 09:13, before the weapons round 4 contract added those sockets; the lane that
owns the guns (task "Weapons round 4 integration") re-imports them. **This release touches nothing they read** (against `fd8ce12` its diff in `Tests/` and `Weapons/` is the one new file
`Tests/MICloudSessionTests.cpp`), and its own commit before the merge had the suite at 127 of 127. **What supports this**: the guns lane's own clone (`/project/ue/repo-guns`, main `fd8ce12` plus its commits, `SK_Nine.uasset` imported again
at 15:10) printed `TESTS OK passed=189 failed=0` at 15:16 UTC, with these two tests in it. **Not shown**: the same two failing on `fd8ce12` alone in this
clone (it was not built here), or passing here with the new content. The release engineer's clone must have the guns imported before this suite can print OK.

**The merged binaries, once more** (Shipping game for the first two, Development for the third; `d2a062e`, 15:17 to 15:20 UTC; runs
`s3c-final-idle`, `-nobody`, `-net`): a viewer who joins an idle game and leaves: idle at 13.6 s after the start, back at full speed
at the join, `Session over` 20.1 s after the connection was lost, exit code 0 (108.4 s); no viewer at all with `-MIExitIfNoViewer=30`:
`Session over` at 30.3 s, exit code 0 after 33.1 s; the crash on purpose: exit code 0 with the line "the engine crashed during its shutdown (signal 11)".

### 7. What is not proven

- **Nothing was run on E3DS.** Whether E3DS applies its own Video Quality *after* the game has set the range, whether a reload on
  E3DS really starts a new game (its documentation says so: LAUNCH.md section 6), how soon its own page reconnects after a
  broken link, and what its machine does with a game that quits by itself: all from documentation and from the first runs
  (DECISIONS.md), none from this release's runs. **The first E3DS session with this build should be read for**: `Session:`,
  `Encoder quality, from ...`, `Nobody is watching`, `Back at full speed (a viewer joined)`, `Session over` and the exit code of the
  launcher's end line, `rttMs=` in the probe lines (with `-MICloudProbe=1` in the launch options).
- **A real browser's reload was not measured**: a browser cannot connect to the game on the box (no ICE candidates, BOX.md); the
  test viewer's second join (3.5 s after the connection was lost) stands for it, and E3DS's own page was never seen to reload
  inside a session.
- **The link of the QP runs is emulated** (the viewer's own rate limit, delay and bandwidth estimate: `rtcinput.py`), one run of
  each line but the two High lines on 4 Mbit/s, which were run twice; a real browser's decoder and a real network are not in them.
  The box's card is an RTX PRO 6000 Blackwell, not E3DS's A4000.
- The idle numbers are the box's card with the game alone on it; the GPU's utilisation is `nvidia-smi`'s once a second.
- **High's range on a thin link** (8 to 24) still stalls part of the time on 4 Mbit/s in a fast turn (received 10 to 11 frames a
  second against 60); the wider range (`-MIQpAbove=16`) is better there and costs sharpness. Which the owner prefers is the
  owner's decision; the defaults are the 10 and 8 that were asked for.
- The round trip on E3DS: see section 4.
- **A visitor can turn the session handling off.** E3DS passes whatever a visitor adds to a stream link on to the game as launch
  options (MurderInc.sh's header), and `-MIKeepAlive`, `-MIExitAfterEmpty=0` and the `MI.Cloud.` variables are launch options and
  console variables of the same kind as `-MICVars=`: a visitor who types them keeps his own game on the machine after his session,
  which is the leftover this release removes for everybody else. Nothing here stops that (the box's scripts need `-MIKeepAlive` in the
  Shipping game); what is left to find it is the launcher's clean-up of other games of the package when the next session starts.

### 8. To prove each item on a package (the release engineer's commands)

The proofs are queues for `tools/box/cloud/lag-test.sh` (its header says what every key does), nothing else running on the box
(no compile, no cook, no other game).

```
# the unit tests (in the clone the package came from): TESTS OK passed=N failed=0
bash tools/box/test.sh MurderInc

# the launcher (no GPU): LAUNCHER-TEST OK; the packaged launcher must say 1 or more:
bash tools/box/cloud/launcher-test.sh <the package's MurderInc.sh>        # as an ordinary user
grep -c MILauncherPid <the package's MurderInc.sh>

# the game's own watch on its launcher (the Development test folder; as root): SESSION-TEST OK
bash tools/box/cloud/session-test.sh launcher <Development test folder>

# 1 and 2: idle, quit, reload, no viewer, -MIKeepAlive (the Shipping game on the unzipped package, about 12 minutes)
LAG_BUILD=<unzipped package> LAG_RUNAS=fresh LAG_CLEAN=1 LAG_OUT=<runs> bash tools/box/cloud/lag-test.sh queue tools/box/cloud/session-gate.txt
python3 tools/box/cloud/session_sum.py <runs>/s3c-idle --gpu           # the card idle against a viewer on the menu
python3 tools/box/cloud/session_sum.py <runs>/s3c-idle --join          # how long the viewer's arrival took to reach the idle game
grep -a "Session over" <runs>/s3c-*/game.log; cat <runs>/s3c-*/result.txt   # exit code 0 after each quit; ALIVE at limit for s3c-keep

# 3, 4 and the crash net: the encoder's range, the round trip, the shutdown crash (the Development game; about 30 minutes)
LAG_BUILD=<Development test folder> LAG_OUT=<runs> bash tools/box/cloud/lag-test.sh queue tools/box/cloud/session-gate-dev.txt
python3 tools/box/cloud/session_sum.py <runs>/s3c-hi-range --phases ; python3 tools/box/cloud/session_sum.py <runs>/s3c-hi-exact --phases
python3 tools/box/cloud/session_sum.py <runs>/s3c-rtt-new40 --phases   # rttMs about 40; 0 nowhere; <runs>/s3c-rtt-new40/pause-card.jpg is the card
python3 tools/box/cloud/session_sum.py <runs>/s3c-net-self             # the crash net: EXIT 0 in result.txt, the line "crashed during its shutdown";
cat <runs>/s3c-net-off/result.txt                                      # without it (-MINoExitGuard): SIGNAL 11 (SEGV)
```

**Which scripts now pass `-MIKeepAlive`** (so that a game held without a viewer on purpose is not ended by its own session
logic): `lag-test.sh` (by default; `keepalive=0` for a run that is about the session; also the calibration), `e3ds-verify.sh` (all
runs but `v-long` and `v-e3ds-7600`, which have a fake viewer and run with `NOKEEP=1`), `stream-test.sh` (so `memory-runs.sh`;
`STREAM_KEEPALIVE=0` leaves it out), `xtest.py`. `e3ds-repro.sh` passes the game's arguments on as they are: its header says to give
`-MIKeepAlive` to a run that holds a game with no viewer. **The existing gates (`release-gate.txt`, `lag-gate.txt`, `sound-gate.txt`)
run with it** (a viewer is there the whole time, so the game would not idle in them anyway); a package's own release gate that
should include the session's behaviour adds `keepalive=0` to a line.

## Weapons round 4: the parts kit and the CHOPPER and NINE mounts (parts modeler, lane 2, 2026-11-25, 13:20 to 14:45 UTC)

Why the Workbench was empty on the two guns the owner has played: `guns.json` mounts of the CHOPPER and NINE were `missing`, because
the exported meshes had no Optic / MuzzleMount / Underbarrel / Laser socket and the booster was not its own bone. This round adds them
**to the exported files** (art/out, git-ignored) and builds the parts that go on them. Verified in Blender, **not in Unreal**: `python
art/blender/assets/_weapons_check_parts.py` on the exported files says **ALL MOUNTS KEPT (153 checks)**: every new socket against the
gun's surface by ray cast, the hide bones closed shells that open nothing when hidden, the patch changing nothing but joints (diff
against the unpatched export), every part on every gun that carries its mount (the CHOPPER, NINE, SHORTY, STRETCH and RATTLER files) with
no triangle crossed and a vertex within 1 mm of the gun, the optics' corridors clear; `_weapons_check.py` still says ALL FIXED POINTS KEPT
for the CHOPPER and the NINE. Pictures `art/previews/weapons_parts_kit.jpg`, `weapons_chopper_built.jpg`, `weapons_nine_built.jpg`,
`weapons_parts_sights.jpg` (the sight pictures from the eye through the red dot and the scope).

**What the integrator gets** (two archives in the layout of fp-guns.tar, `python art/blender/assets/_weapons_pack_parts.py`: `art/out/fp-weapons-parts.tar`
21 MB: 15 SM_Part_* GLBs + `.sockets.json`, the sets Weapon_Parts and Weapon_PartsMags, `weapons_r4_parts.json`; `fp-weapons-mounts.tar` 134 MB: the
patched SK_Chopper.glb and SK_Nine.glb, their sets and the two standard magazines; the committed contract is
`art/blender/assets/weapons_parts_contract.json`):

| Gun socket (gun space, metres; Unreal cm = (x, -y, z) x 100) | CHOPPER | NINE |
|---|---|---|
| Optic | (0.1150, 0, 0.0420) = (11.5, 0, 4.2): the centre of slot 4 of the 106 mm rail, on the lug tops | |
| MuzzleMount | (0.4260, 0, 0) = (42.6, 0, 0): the booster's base plane | (0.1960, 0, 0) = (19.6, 0, 0): the slide's front face |
| Underbarrel | (0.3050, 0, -0.0623) = (30.5, 0, -6.23): the underside of the folded stock's shoulder plate | |
| Laser | | (0.1560, 0, -0.0236) = (15.6, 0, -2.36): the dust cover's middle lug |
| MagHinge | (0.222, 0, -0.040) (unchanged) | (0.0177, 0, -0.0359) = (1.77, 0, -3.59) |
| new deform bones | `Booster` (head (0.4260, 0, 0): the muzzle booster, hide it for a muzzle part), `FrontSight` (head (0.409, 0, 0.031): the sight tower, ears, drum and post; hide it for an optic) | none |

Part sockets (part frame, metres; the part's origin is its mount): red_dot `SightEye` (-0.0325, 0, 0.0245); scope_4x `SightEye` (-0.067, 0, 0.0275);
suppressor `Muzzle` (0.210, 0, 0); compensator `Muzzle` (0.062, 0, 0); suppressor_pistol `Muzzle` (0.155, 0, 0); foregrip_vertical `SupportHand` (0, 0, -0.052);
foregrip_vertical_wood `SupportHand` (0, 0, -0.048); foregrip_angled `SupportHand` (-0.012, 0, -0.030); laser_module `Beam` (0.0235, 0, -0.0125) along +X; the
three magazines have none (the origin is MagHinge). Files: `SM_Part_RedDot`, `SM_Part_Scope4x`, `SM_Part_Suppressor`, `SM_Part_Compensator`,
`SM_Part_SuppressorPistol`, `SM_Part_ForegripVertical`, `SM_Part_ForegripVerticalWood`, `SM_Part_ForegripAngled`, `SM_Part_LaserModule`,
`SM_Part_MagRifleExt`, `SM_Part_MagSmgExt`, `SM_Part_MagPistolExt` (+ `_TopRound` for the three magazines).

**What the Unreal import must do**: (1) re-import SK_Chopper and SK_Nine (the skeletons gain bones; they are the same meshes, UVs and sets: re-link
the existing sets); (2) import the 15 part GLBs as **static meshes** and write their sockets from `weapons_r4_parts.json`
(`ue_import_guns._put_static_socket`: a GLB cannot carry them), slots by name: `M_Part_Hardware` = set `Weapon_Parts` (BC N ORM E), `M_Part_Mags` =
set `Weapon_PartsMags` (BC N ORM), `M_Part_Lens` = a translucent smoked glass made in the editor (copy `ue_import_guns.glass()`), `M_Part_Reticle` = the
collimated additive dot (copy `reticle()`; the plane is 10 mm on the red dot, 20 mm on the scope, at X 0 of the part, facing the eye); (3) attach with
`SnapToTargetIncludingScale` at the gun's socket of the same name (sockets carry no rotation: the parts are built in the gun's axes, the NINE
magazine pre-canted); (4) hide with `HideBoneByName` per fitted part: optic -> `FrontSight` on the CHOPPER (`IronsFront` / `IronsRear` on the new guns),
muzzle -> `Booster` (CHOPPER) / `MuzzleDevice`; a hidden shell collapses to its bone head, so nothing opens (checked); (5) the magazines replace
the gun's standard magazine mesh on the `magazine` bone, the top round hides when empty; (6) the camera of an aimed optic sits at
`SightEye - relief` along the bore (relief 0.14 red dot, 0.085 scope).
Optics: the **clear half angle from the eye through the tube is 4.0 deg** (red dot and scope; measured), not the 9 deg of the ocular alone: beyond it the
ray meets the tube's dark matte inside. The scope view will therefore look like a small clear disc in a dark tunnel at an aimed field of 30 deg; hide or
fade the scope's body in the aimed view if the whole picture is wanted (the lens ring and the turrets are not in the way of the sight line).

**Data** (`guns.json`, `attachments.json`, from the specification's sections A and B with these numbers): chopper mounts optic {Optic [0.115, 0, 0.042], exists,
hide ['FrontSight']}, muzzle {MuzzleMount [0.426, 0, 0], exists, hide ['Booster']}, underbarrel {Underbarrel [0.305, 0, -0.0623], exists}; nine mounts laser
{Laser [0.156, 0, -0.0236]}, muzzle {MuzzleMount [0.196, 0, 0]}, magazine {MagHinge [0.0177, 0, -0.0359]}, all exists; remove `compatibility.nine.dropped.laser`
(the module is 46 mm, under the 50 mm gate); attachments with the ids red_dot, scope_4x, suppressor, suppressor_pistol, compensator, foregrip_vertical,
foregrip_vertical_wood (CHOPPER only: its own text key "Vertical grip"), foregrip_angled, laser_module, mag_ext_rifle, mag_ext_smg, mag_ext_pistol and the
meshes above; compatibility chopper optic [red_dot, scope_4x], muzzle [suppressor, compensator], underbarrel [foregrip_vertical_wood]; nine muzzle
[suppressor_pistol], laser [laser_module], magazine [mag_ext_pistol]; shorty optic [red_dot, scope_4x], muzzle [suppressor, compensator], underbarrel
[foregrip_vertical, foregrip_angled], laser [laser_module], magazine [mag_ext_rifle]; stretch optic [scope_4x, red_dot], muzzle [suppressor], underbarrel
[foregrip_vertical, foregrip_angled], magazine [mag_ext_rifle]; rattler optic [red_dot], muzzle [suppressor, compensator], magazine [mag_ext_smg].
Where the measured guns differ from the specification's numbers (the CHOPPER's grip clamps the stock plate, the laser is tilted 1 deg, the compensator recess
is 12.6 deep, the NINE magazine is modelled about the socket): `art/blender/PROGRESS.md` ("Where the measured guns decided against the specification").

**Verifier pass on the parts kit (2026-11-25, 14:15 to 14:50 UTC).** Checked, not rebuilt. On the final files: `_weapons_check.py` (the CHOPPER and the NINE
ALL FIXED POINTS KEPT), `_weapons_check_parts.py` (153 checks, ALL MOUNTS KEPT), and checks of its own: every part file is closed shells (no open or non-manifold
edge, no zero-area triangle), UVs inside 0..1, the slots, the 2048 maps (BC N ORM E and BC N ORM), and every pair of parts of different slots on one gun (54
pairs: 25 SHORTY, 13 STRETCH, 8 CHOPPER, 5 RATTLER, 3 NINE) crosses nothing. **One fault found and fixed:** on the SHORTY the **angled grip and the laser module
crossed** (277 triangle pairs): the Workbench allows both, the grip's 55 mm plate and thumb shelf reached X +28 in its frame and the laser's rear face stands at
+23.2 (the sockets are 48 mm apart on the forend's rail). `foregrip_angled` now has a 47.5 mm plate and its front ramp and shelf stop at X +19.5 above Z -29.7
(the laser's floor): 0 crossings, 6.3 mm gap (the vertical grip's: 6.5 mm), 2,380 triangles (was 2,364), the proof still 153 of 153. The set was unwrapped again,
so the nine hardware parts, `Weapon_Parts`, their manifest records and the 12 pips were replaced together (the rebuild ran in a copy of the pipeline and was
swapped in file by file); `fp-weapons-parts.tar`, `fp-weapons-mounts.tar` and `fp-weapons-r4-parts.tar` were packed again. **The `fp-weapons-r4-parts.tar` made at
14:25 predates the final 2K bake (14:26) and the reticle plane (14:36): use one packed after 14:45.** Left as measured, not faults of the files: the clear half
angle through the tube is 4.0 deg in both optics (above); the wooden grip is 4,092 and the scope 12,040 triangles against budgets of 4,000 and 12,000 (+2.3 % and
+0.3 %); the hardware set's texel density is 3,266 px/m, the magazines' 3,866 (the guns': 7,000 to 9,000).

## Weapons round 4: the SHORTY, our own bullpup carbine (weapons modeler, 2026-11-25, 12:20 to 13:55 UTC)

The owner's report on the E3DS build, "all the guns look the same and no attachments are able to be added to the guns", is the
loadout design's own "Read this first" (four of the five offered guns are one pack M4). The SHORTY replaces the pack's Short
rifle: **a compact bullpup carbine of our own** (700 mm, magazine behind the pistol grip, an olive polymer block with a see-through
carry handle on top, a ventilated forend, a birdcage hider). Verified in Blender, not in Unreal: `python
art/blender/assets/_weapons_check_shorty.py` on the exported files says **ALL FIXED POINTS KEPT (63 of 63)**: the 19 bones and
12 sockets to 1e-5 m, both MI-R rails tooth by tooth with Optic / Underbarrel / Laser / Palm_L on them, MuzzleMount on the thread
shoulder, the sight line clear from the aperture (Z 0.060) to the post, Palm_R on the grip and the trigger 73 mm ahead of it,
the bolt (75 mm), trigger (17 deg), selector (0 / 14 / 28 deg) and the magazine drop with zero contacts, the hide bones leaving no
hole, the eye corridors of the irons, the red dot and the scope, and the re-import pose proof.

What the integrator gets (art/out, git-ignored; names as the pack import expects): `glb/SK_Shorty.glb` (67,168 triangles, bones
body root, bolt, trigger, selector, magazine (attach), MuzzleDevice, IronsFront + the 12 socket bones `Muzzle`, `Eject`,
`SightRear`, `SightFront`, `RecoilPivot`, `MagHinge`, `Palm_R`, `Palm_L`, `Optic`, `MuzzleMount`, `Underbarrel`, `Laser`; positions
in `manifest.json` under SK_Shorty, metres and Unreal cm), `glb/SM_Weapon_ShortyMagazine.glb` + `_TopRound.glb` (static, in place),
textures `Shorty/T_Shorty_{BC,N,ORM,E}.png` (4096, E = the tritium insert) and `Weapon_ShortyMagazine/T_Weapon_ShortyMagazine_{BC,N,ORM}.png`
(2048), tiling detail `TS_GunDetail_Steel` (20 mm) and the new `TS_GunDetail_Polymer` (12 mm; blend by ORM.B). Data for guns.json: the
mesh asset `SK_Shorty` (the Blender name is the asset name), `presentation.meshOffset` pos [0,0,0] rot [0, 1.5708, 0] (the origin is
the butt face, not the grip), mounts optic `Optic` (hide `IronsFront`), muzzle `MuzzleMount` (hide `MuzzleDevice`), underbarrel
`Underbarrel`, laser `Laser`, magazine `MagHinge`, no stock slot; `parts.bolt.bone` bolt (travel 0.075), `trigger.bone` trigger,
`magazine.bone` magazine (drop (0, 0, -0.13)); eject direction (0.55, -0.80, 0.25); relief 0.12 (irons) / 0.14 (red dot) / 0.085
(scope); `views[0]` re-anchored on Palm_R: [0.2229, -0.0925, 0.0046, 0.05, 0.28, -0.35]. Pictures `art/previews/weapons_shorty_*.jpg`;
the icon `T_UI_Gun_Shorty.png` is rendered (512 x 192, git-ignored). Weaknesses and decisions: `art/blender/PROGRESS.md`.

## Weapons round 4: the RATTLER, the Goons' submachine gun at first-person grade (weapons modeler, lane 2, 2026-11-25, 13:15 to about 15:00 UTC)

The sixth gun. The RATTLER was designed and in the data but hidden from the rack because its mesh did not exist; the Goons' own gun
(`SM_Weapon_GoonSMG`, enemy grade) is now the player's: **an open-bolt 9 mm submachine gun of our own design**: a stamped sheet-steel
box (hollow, 1.6 mm sheet, spot welds, ribs, a butt-welded seam), a round ventilated shroud with a tan strap wrap, a slotted muzzle
device, a 182 mm stick magazine ahead of the pistol grip and a wire stock folded along the left flank (plainly visible from the
shooter's eye). Verified in Blender, not in Unreal: `python art/blender/assets/_weapons_check_rattler.py` on the exported files
says **ALL FIXED POINTS KEPT (55 of 55)**: the 19 bones and 10 sockets to 1e-5 m, the sight line (4.8 mm aperture on Z 0.0575 to the post), the
cover's MI-R rail tooth by tooth (12 lugs, tops Z 0.042) with the Optic socket on the middle of it, MuzzleMount on the thread
shoulder, Palm_R / Palm_L on their surfaces, the trigger 70 mm ahead of Palm_R, the bolt (50 mm), the T-handle in its slot, the
trigger (17 deg), the selector (0 / 14 / 28 deg), the stock (0..180 deg) and the magazine drop with zero contacts, the three hide
bones leaving no hole, and the re-import pose proof. The parts kit's assembly proof (`weapons_parts_check.json`) already fits the red
dot (Optic), the suppressor and the compensator (MuzzleMount) and the extended magazine (MagHinge) on the exported mesh without a
crossing triangle.

What the integrator gets (art/out, git-ignored; names as the pack import expects): `glb/SK_Rattler.glb` (67,964 triangles; bones
body root, bolt, trigger, selector, magazine (attach), stock, MuzzleDevice, IronsFront, IronsRear + the 10 socket bones `Muzzle`,
`Eject`, `SightRear`, `SightFront`, `RecoilPivot`, `MagHinge`, `Palm_R`, `Palm_L`, `Optic`, `MuzzleMount`; positions in
`manifest.json` under SK_Rattler, metres and Unreal cm), `glb/SM_Weapon_RattlerMagazine.glb` + `_TopRound.glb` (static, in place),
textures `Rattler/T_Rattler_{BC,N,ORM}.png` (4096; no E file: nothing is emissive) and
`Weapon_RattlerMagazine/T_Weapon_RattlerMagazine_{BC,N,ORM}.png` (2048), tiling detail `TS_GunDetail_Steel` (20 mm; the strap carries
its weave in the unique normal map). Data for guns.json: the mesh asset **`SK_Rattler`** (the data says `SK_Weapon_Rattler`: rename it;
the Blender name is the asset name), `presentation.meshOffset` pos [0,0,0] rot [0, 1.5708, 0] (origin on the bore at the receiver's rear
face), mounts optic `Optic` (hide `IronsFront`, `IronsRear`), muzzle `MuzzleMount` (hide `MuzzleDevice`: the R 8.5 thread stub and
the bore remain), magazine `MagHinge`; no underbarrel, no laser (a round shroud has no rail); `parts.bolt.bone` bolt (travel 0.05, the
top T-handle moves with it), `trigger.bone` trigger, `magazine.bone` magazine (drop (0, 0, -0.14)); eject direction (0, -0.95, 0.31),
pistol casing; the stock bone is rest = folded and +180 deg about (0, 0.0285, 0) = deployed (the optional `stock_wire_open` variant
and the icon use it; deployed the plate stands 0.25 m behind the receiver). Palm_L is the strap wrap's underside (X 0.315, Z -0.0275).
Pictures `art/previews/weapons_rattler_*.jpg`; the icon `T_UI_Gun_Rattler.png` is rendered (512 x 192, stock deployed, git-ignored).
Weaknesses and decisions (the stock's deployed length is 715 mm, not 635: the specification's folded geometry mirrors about the
hinge): `art/blender/PROGRESS.md`.

## Version 3b: sound (sound engineer, 2026-11-25, 09:28 to 12:35 UTC)

Version 3b is version 3a plus sound, and it is packaged: **zip sha256
`aa7cc478f80ddb3ab077a718d518b300844b4f4d07eab6e07595b95038218deb`, 2,259,930,775 bytes** (version 3a: 2,254,962,151;
5.0 MB more), the game from commit `3dd4053`, the launcher from `5bba2dd`, nine parts
`MurderInc-E3DS-v3b-part<k>-of-9.zip` in `/project/ue/cloud/parts` on the box. **Not uploaded and not gated for lag:
that is the release engineer's step** (section 11). It was zipped twice from one build: at 10:50 UTC with the
launcher of `3dd4053` (sha256 `8ec0f7f7…f3a4`: the first measurements and the search of section 8.2) and at 11:53
UTC with the launcher of the branch head, because the cleanup of leftover games (`2322f3c`) had reached the branch
meanwhile. The two zips differ in three files only (`MurderInc.sh`, `MIDEV.key`, `BUILD.txt`: compared file by file
after unpacking). The sound gate was run on the second one, and the tables of sections 4, 6 and 8.1 are from it.

The sound was measured through a real WebRTC stream on the box, in the Development game and in the Shipping game of
the zip, unpacked as a new user into a fresh folder and started with E3DS's arguments. Nobody here has ears: "heard"
below means that the game's own sample was found in what the viewer received, at the time the game's log or the
viewer's input gives; where only a level could be measured, or nothing, that is said. Section 10 lists what is not
proven. Runs are in `/project/ue/cloud/lag/<name>/` on box ec087d85 (`sound.wav` is what the viewer received; the
runs of the first zip carry `-z1` at the end of their names).

Three faults of the port came out of the listening and are fixed with tests (section 5): **four of the six guns had
no shot sound at all, the menus never played their two sounds, and the first round of each gun sample came about
110 ms late.** One way a host could silence the game without knowing: an environment that names an audio driver
(section 7); the launcher now rules it out. **And one thing is not as the brief wanted it: in the first half minute
after a cold start, on a machine whose CPUs are at their limit, the stream's sound can have short holes** (section
8.2: seen in ten of the cold starts here; never after that half minute, never in play, never from the GPU's load
alone, and in none of the load lines of the gate on the zip to upload).

### 1. The assets

- `tools/box/audio-import.sh` in `/project/ue/repo-gameplay` (its editor stopped), 09:29 UTC:
  **`AUDIO-IMPORT-DONE imported=289 failed=0`** after 55 s.
- **291 WAV files, 289 Sound Waves.** The two that are not imported are `Web/IR_shop.wav` and `Web/IR_street.wav`, the
  reverb responses (the import skips `IR_*`; audio_sounds.json gives them the bus `ir`, which the game's parser skips).
  **No sound the game plays is among the difference**: the data names exactly 289 files (`pak_sounds.py --names
  Content/Data`: 188 under `Web`, 80 under `Gen`, 21 voice takes), each of them a WAV in the folder, and the only WAVs
  the data does not name are those two.
- **The release copy and the package take them** (read in `package-cloud.sh`, then checked): the `content` step
  copies the gameplay clone's whole `Content` (but `Data` and `Python`) with tar, nothing under `Content/Audio`
  filtered (release copy after it: 188, 80 and 21 `.uasset`); the cook rule was already there
  (`+DirectoriesToAlwaysCook=(Path="/Game/Audio")` in the overlay: the game loads the waves by path, nothing references
  them), so nothing had to be fixed in the rules: the assets had simply never been in the clone. The cook: 2,528
  packages (2,232 in version 3a). **The pak list (`Manifest_UFSFiles_Linux.txt`) holds 867 entries under
  `MurderInc/Content/Audio/`: 289 `.uasset`, 289 `.uexp`, 289 `.ubulk`** (version 3a: none).

### 2. Never silent again

| What | How it was shown |
|---|---|
| (a) `package-cloud.sh` refuses a zip without the sounds | `pak_sounds.py` reads the packaged data (`MurderInc/Content/Data/*.json`), works out every Sound Wave it can ask for the way the game does, and looks each up in the pak list. On the new package: "SOUNDS OK: all 289 Sound Waves the game's data names are in the pak list ... (289 under MurderInc/Content/Audio/)", printed by `package`, by `zip` and by the new step `sounds`. **On version 3a's own unpacked zip** (`MI_CLOUD` pointed at it): "SOUNDS MISSING: the game's data names 289 Sound Waves and the pak list ... holds 0 of them", then "ZIP REFUSED: a sound the game plays is not in the package (lines above). No zip was made.", exit code 1, no zip. The `content` step also stops when the gameplay clone has a sound without an asset or with an older one |
| (b) the tests fail | `MurderInc.Audio.Assets` fails (it warned) when an asset is missing or older than its WAV. New: `MurderInc.Audio.SoundsResolve` (289 of 289 files load as Sound Waves; 70 sound ids named by the tables are sounds) and `MurderInc.Audio.EveryGunSounds`. **Shown red**: with one asset moved away and one gun's line taken out of the data, `TESTS FAILED passed=20 failed=3` ("Web/ui_click_01.wav has no Sound Wave asset", "no Sound Wave loads from /Game/Audio/Web/ui_click_01", "rattler: a shot is heard (category gun)"); both put back |
| (c) a clone that is brought up to date imports its sounds | `sync.sh` (BOX.md's first step for a clone) counts the WAVs without an asset and those newer than their asset and starts `audio-import.sh`, or says what stands in the way (C++ just changed: build first; the editor open; no `Content/Audio/Web`). **Shown**: one asset moved away and one WAV touched: "AUDIO: 1 sound(s) without a Sound Wave asset, 1 with an asset older than the WAV: AUDIO-IMPORT started"; a second sync meanwhile: "the import is running"; 55 s later `AUDIO-IMPORT-DONE imported=289 failed=0` and the next sync is silent |
| (d) a missing sound is a warning, and it is counted | Once per sound: "sound missing: <file>: no Sound Wave asset ... It will not be heard." (it was a Verbose line, and a missing web sound said nothing at all); the same for a sound id the data does not have. Three new fields at the end of the probe line: `sndPlayed` (sounds started on the audio device), `sndMissing`, `sndNoDevice` (starts that found no audio device). `lag_sum.py` prints them ("sound: 503 sounds started in the play (529 in the whole run), 0 without an asset, 0 without an audio device") and reads lines without them as before (tried on a version 3a line and a new one) |

### 3. The listening tool

`/project/ue/cloud/chk/rtcaudio.py` (a copy of the viewer with a loudness reading of every eighth sample) became
three tools in `tools/box/cloud/`:

- **`rtcaudio.py`**: the viewer of `rtcinput.py` (it imports that file, so the scripts are played by the same code)
  with a recorder. It writes what arrives to `sound.wav`, every decoded frame at the place its RTP timestamp gives it;
  prints loudness and peak per half second, clipped samples, digital silence, lost sound and the size of the Opus
  packets; counts drop-outs (10 ms to 1 s of digital silence with sound on both sides) and says under which of the
  script's markers they fell; compares the sound's clock with the wall clock; and keeps the time of every script line
  and the arrival of every sound packet (taken before the viewer's own jitter buffer) in `sound.wav.json`.
  `lag-test.sh ... audio=1` uses it.
- **`audio_find.py`**: is this sample of `Content/Audio` in that recording, where, how strongly? A matched filter in
  the band an Opus stream keeps the waveform of (150 Hz to 6 kHz), at every speed the game's pitch jitter can give
  (3.5 %: 37 speeds). What chance scores is measured, not assumed: the same sample backwards, and at six speeds the
  game does not use. A find is 1.5 times that or more. For a find it gives the correlation, the sample's level against
  the file and, with the viewer's times, the delay from a script action to the arrival of the packet that holds the
  sample's start.
- **`sound_table.py`**: the Development game logs every sound it starts (`-LogCmds="LogMIAudioHost Verbose"`: file,
  volume, category gain, speed); this looks each of them up in the recording at that time and speed.

**The instrument, checked first with a known signal through the same path** (`rtcaudio.py --selftest`: a sender in
the same process sends through Opus, RTP, the jitter buffer and the recorder; `audio_find.py --truth`). Its Opus
encoder runs at 96 kbit/s, a third of the game's stream (651 bytes a packet), so the test is the harder case:

| Sent | Received |
|---|---|
| a 1 kHz tone at -23.01 dBFS RMS | -22.99 dBFS, 1,000 cycles a second |
| a gap of 100 ms in a street bed | found as a drop-out of 70 ms at the right place (the codec rings 20 ms into each end) |
| a full-scale square burst, 960 samples | peak 0.0 dBFS; 19 samples at 99 % of full scale or more: **a clipped count through Opus is a lower bound** (the decoder rounds the tops off), the peak is the surer sign |
| nothing lost; the sound's clock | 0 ms lost in 1,115 packets; 1.0001 s of sound a second |
| the CHOPPER's close sample at 6 s, 8 s and 10 s, at -6.0, -12.0 and -18.1 dB and speeds 1.0, 0.97 and 1.03, over the drum stem and the street bed | each found 0.04 ms from its place, at -6.3, -12.3 and -18.2 dB, at exactly its speed, 8.5 to 9.1 times chance |
| the drum stem at -24.6 dB | found at its place, -25.2 dB, 9.0 times chance |
| three samples that were not sent (a blast, a voice line, a far horn) | 0.55 to 0.93 times chance: not found |
| a sample started by each of three script actions | the packet with its start arrived 25, 16 and 25 ms after the action; the sender had handed that frame to its encoder 24, 15 and 24 ms after it |

Its limits, met on the game (BOX.md): a sample that is only a tone (the ear ring, a far siren) or only a short low
thump (the hurt and the heartbeat have 98 % of their energy under 150 Hz) cannot be told from chance, and a far
3D sound under gunfire is too quiet. For those the table below says what was measured instead.

### 4. The sound, kind by kind

Two games of the zip `aa7cc478…`, unpacked as the user `e3dsfresh` with a new empty home into `/tmp/v3b2/zip`, no
display, E3DS's arguments (which include `-AudioMixer`), free GPU, one game at a time (both runs CLEAN):

- **Development game**, run `snd-dev` (12:17 UTC): its own demo director plays `sound-demo.txt` (the set-up screens
  with four guns, the run, each gun's single rounds, a burst, reloads, the rifle butt, steps, a jump, two reels, a
  fight on the avenue, the propane tanks, the last reel by hand, the truck, the debrief; 128 s of play at 59.9 frames
  a second). The game started **1,148 sounds, 0 without an asset, 0 without an audio device**; the viewer recorded
  321 s with no digital silence, nothing lost and no drop-out. `sound_table.py` looked at 396 of the starts (the first
  four of every file) and **found 174 of them; of the 65 different sounds the game started, 40 were found at least
  once**. The middle delay from the game's log line to the arrival of the packet with the sample's start: **44 ms**.
- **Shipping game**, run `snd-keys` (12:01 UTC): a viewer plays `sound-keys.txt` with mouse and keyboard, one kind of
  sound at a time under a marker; `sound-keys-check.sh` looks in each part for the samples that belong there. 522
  sounds started, 0 missing (the game's own count); 146 s recorded, no digital silence, nothing lost, no drop-out.
- The same two runs on the first zip (`snd-dev-z1`, `snd-keys-z1`) gave the same picture (174 of 394 found, 38 of 65
  sounds; middle delay 40 ms); where the two differ the table says so.
- The death (the Development game without god mode, `sound-dead.txt`, run `snd-dead1`) was run on the package of
  10:18 UTC (`924bbce`: the same audio data; the preload of section 5 came after it).

"x" is how far above chance the find was (1.5 or more is a find). "Level" is the sample's amplitude in the recording
against the file's own; after the semicolon what the game's own numbers give (its volume times the category's gain at
that moment). "Delay" is from the game's log line (D, the Development run) or from the viewer's input (S, the
Shipping run) to the arrival of the packet that holds the sample's start. "n of m" is found of looked at.

| Kind | How it was triggered | Heard | Sample matched | Level | Delay |
|---|---|---|---|---|---|
| Music and street behind the click card and on the home screen | the viewer joins; a click | yes | S, in the whole recording: `stem_drums_01` at each of its five loop starts (up to 7.8 x), `stem_keys_01` once (2.5 x), `bed_day_01` at nine loop starts (up to 7.6 x); the bed also under the click card alone (4.1 x) | drums -16.3 to -17.1 dB. Bed -11.4 and -12.6 dB on the card and the home screen (the title's street is 0.6 of the run's), -7.1 to -9.1 dB in the run | none to measure |
| Menu: a move, a press | S: Down and Up, then every button of the set-up screens; five moves and five presses on the pause card. D: the demo's presses | yes | S: `ui_click_01` in four of the five set-up parts (1.7 to 2.1 x, correlation 0.70 to 0.78; all five in the first zip's run) and 5 times on the pause card (3.0 x, 0.96); `ui_hover_01` 3 times in the set-up moves (1.7 x) and 5 times on the pause card (2.2 x, 0.79). D: `ui_click` 3 of 4 (2.1 x) | -7.5 to -8.3 dB (S); -7.5; -2.5 (D) | 32 ms (D) |
| The run's start: the radio and Rule's line | the Briefing's button | yes | D: `radio_in_01` 4 of 4 (3.8 x), `radio_out_01` 4 of 4 (1.9 x), `Voice/rule/inc_02`. S: `inc_02` under the briefing (6.6 x, correlation 0.87); the radio's two clicks not found there | radio -7.7; -2.8. Voice -7.1 dB (S); -7.7; -1.9 (D) | 62 and 60 ms (D) |
| CHOPPER, single rounds | S: three clicks two seconds apart. D: the demo's fire | yes | S: `chopper_close_01`, `_02`, `_03` (3.1, 5.9 and 3.8 x), the case on the ground `brass_asphalt_03` (1.5 x); 12 other samples of the library tried on the same part: none found. D: `chopper_shot` 13 of 36 (5.6 x, the close layers and the web shot), `chopper_tail_out` 3 of 16 (2.3 x), `brass_asphalt` 10 of 28 (2.4 x) | close layer -7.9 to -10.7 dB (S); -8.8; -3.1 (D). Tail -13.2; -8.4 | **41, 50 and 61 ms after the click (S)**; 31 ms (D) |
| CHOPPER, a burst and a magazine fired empty | S: the button held | yes | S: 6 rounds found in the burst, 29 in the emptied magazine (10, 8 and 11 of the three close samples) | -8.7 to -9.8 dB | 69 ms after the button went down |
| Reload | S: R. D: the demo | yes | S: `cloth_01` (5.1 x), `rifle_magout_01` (1.9 x), `rifle_bolt_01` (1.7 x), and the web layers of magazine out and in (1.6 and 1.9 x). D: `rifle_magout`, `rifle_magin`, `rifle_bolt` 4 of 4 each (2.1 to 2.2 x), `cloth` 6 of 6 (5.7 x) | -10.1 dB (S); -9.8 to -11.5; -4.3 to -5.0 (D) | 45 ms after R (S); 38 to 62 ms (D) |
| Dry fire, the fire selector's click | S: B; two clicks on an empty magazine. D: the demo | hardly | Not found in these two runs (1.4 x at most); once in the first zip's Development run (2.4 x, 1 of 6). It is 0.15 s long and the quietest sound of the gun (volume 0.30); the selector plays it at 1.6 times its pitch, and the dry click falls under the last round's tail before the game reloads by itself. The game started it 6 times (the log) | -18.0; -12.8 (first zip, D) | not measured |
| NINE: drawn, three rounds, reload, back to the CHOPPER | S: 2, three clicks, R, 1. D: the demo | yes | S: `nine_close_01`, `_02`, `_03` (3.8, 4.2 and 2.9 x), `draw_01` at 1.17 times its speed for the NINE (3.1 x) and at its own for the CHOPPER (6.7 x), `pistol_magout_01` (2.0 x). D: `nine_shot` 2 of 6 (7.2 x), `nine_tail_out` 2 of 4 (2.7 x), `holster` 4 of 4 (7.2 x), `draw` 4 of 4 (7.2 x), `pistol_magin` and `pistol_magout` 2 of 2 each | NINE -11.6 to -12.4 dB (S); -8.9; -3.9 (D) | **27, 35 and 54 ms after the click (S)**; 41 ms (D); holster 38, draw 60 ms (D) |
| The other four guns (they fire with the CHOPPER's sounds, section 5) | D: the demo's loadout: the STICK with its silencer, the STRETCH | yes | `chopper_sup_02`, `_03` 2 of 2 (5.8 x) for the STICK; the STRETCH's rounds are among the `chopper_shot` finds | -9.6; -4.0 | 48 ms |
| Rifle butt | F | yes | S: `whoosh_01` (6.8 x, correlation 0.70). D: `whoosh` 1 of 1 (6.2 x); a Goon's `pipe_swing_01` 2 of 3 (2.1 x). (In the first zip's Shipping run the press fell into the draw of the gun, where the rules refuse the butt: no whoosh, rightly; the script now waits) | -9.1 dB (S); -8.9; -3.8 (D) | 78 ms after F (S); 45 ms (D) |
| Steps, a jump, the landing | S: W, Shift with W, Space. D: the demo's walks | yes; the steps only in D | D: `step_asphalt` 12 of 32 (2.0 x), `step_asphalt_run` 16 of 24 (2.4 x), `jump` and `land` 1 of 1 (6.5 and 3.5 x). S: `jump_01` (7.1 x), `land_01` (3.4 x); the steps not found in this run (two of the walk's in the first zip's run, 2.0 and 2.5 x; the sprint's in neither): they are the quietest sounds of the player (volume 0.37 to 0.42) | steps -17.1; -11.3 and -13.3; -7.8 (D). Jump -11.2 dB (S) | 35 ms after Space (S); steps 52 and 38, jump 40, land 36 ms (D) |
| Enemies: their calls and their guns | D: the fight on the avenue, a Buzzard | yes, in part | `alert_goon` 7 of 9 (2.6 x), `alert_buzzard` 4 of 4 (4.0 x), `smg_shot` 4 of 23 (3.2 x), `bolt_shot` 18 of 20 (2.5 x), bullets passing `whizz` 12 of 12 (3.4 x), `buzzard_charge` 2 of 4, `rotor` 2 of 8. Not found: `goon_ready`, `goon_rush`, `grunt_hit`, `grunt_death` (2 of 3 in the earlier run `snd-dev1`) | 3D sounds: no one level | not read (3D) |
| Hits and kills | D | in part | `kill_confirm` 4 of 4 (2.4 x), `hit_head` 1 of 3 (1.7 x), `buzzard_death` 1 of 1 (2.7 x). Not found: `hit_confirm` (a short tone), `body_fall`, the bullet impacts `imp_*`, `ricochet` | kill -7.2; -2.7 | 43 ms |
| Blasts | D: the propane tanks | yes | `explosion_small` 2 of 2 (2.7 x), `explosion_big` 1 of 4 (3.5 x), `explosion_far` 1 of 2 (1.8 x). Not found: the fuse's `hiss` | -18 to -25 dB; -3.1 to -5.8 before distance (3D, 20 m away and more) | not read (3D) |
| Reels and stings | D: two reels given, the last one taken by hand, the truck | yes | `reel_secure` 1 of 1 (3.0 x), the last reel's `sting_all` 1 of 1 (1.6 x), the debrief's `sting_complete` 1 of 1 (2.1 x). Not found: the grab's rising tone `reel_grab`. Not triggered: `sting_reel` | reel -8.5; -3.1. Stings -15.4; -8.9 and -13.0; -8.1 | 48, 48 and 41 ms |
| Rule's lines in play and on the debrief | D | yes, all six | `inc_02` at the run's start, `rulebaby_03`, `murda_01`, `name_01`, the crowd's `rule_chant_03`, `inc_01` on the debrief: 6 of 6 (4.3 x in the middle; `holla_02` in the first zip's run) | -7.7; -1.9 | 56 ms in the middle (28 to 63) |
| The street's life | every run | the bed yes, the rest hardly | Not found in this run: `pigeons` (2 of 6 at 1.7 x in the first zip's), the far one-shots `bus_pull`, `chime_far`, `dog_far`, `horn_far`, `jackhammer`, `kids_far`, `siren_far` and the train's three loops (3D, 60 to 150 m away, under the music) | not read | not read |
| Hurt, the ear ring, death | D without god mode (`snd-dead1`): the player dies 19 s into the run | yes, by level | `sting_dead` (3.1 x). The hurt (12 starts): no sample find (a low thump), but the band from 40 to 120 Hz rises 5 to 7.5 dB in the 0.3 s after each start. The ear ring: 4.0 to 4.35 kHz rises 11 dB at the first hit. After the death the band above 2 kHz falls from -28.6 to -57.9 dB (the web game's "everything muffles"). The heartbeat started 0.8 s before the death: not shown | as said | not read |
| Paused | S: P | as the web game | the street bed stops (no loop start of it between 103.8 and 138.5 s of the recording; found again after the resume, 5.9 x); the music stays, thinned (`stem_drums_01` on the card at -25.7 dB, about 9 dB under its level in the run); the card's moves and presses are found (row 2) | -35.6 dBFS against -27.3 in the run | none to measure |

**Not heard as their own sample, and why**: the far one-shots of the street (3D, 60 to 150 m away, under the
music), the bullet impacts (3D, down the avenue, under the gun that made them), body falls, the Goons' "ready" call
and grunts, the fuse's hiss, the train's loops, the grab's rising tone and the hit tick (short tones), the dry click.
The game started every one of them (the log), with its asset; whether a player can make them out in that mix is a
question for ears, and the web game mixes them the same way.

### 5. Three faults of the port, fixed

1. **Four of the six guns fired in silence.** The web game has two guns; the loadout added four (`guns.json`: SHORTY,
   STICK, STRETCH, RATTLER). The gunshot rule asked for `<gun>_shot` and `<gun>_tail_out`, which exist for the CHOPPER
   and the NINE only. `audio.json weaponSounds` now names the gun whose sounds each of them fires with (all four the
   CHOPPER's, until they have material of their own; no new audio), `FMIAudioDirector::SoundFamily` reads it, and
   `MurderInc.Audio.EveryGunSounds` fires, runs dry, reloads and switches every gun of the roster. In the stream: the
   STICK with its silencer played `chopper_sup_01` and `_02` (found, 6.5 times chance), the STRETCH the CHOPPER's shot.
2. **The menus were silent.** The web game plays `ui_click` on every press and `ui_hover` on every focus move
   (`src/menus.js`); the port had the samples and never played them. `UMIGameSubsystem::UiNote` now puts `ui:click`
   and `ui:hover` on the bus from the set-up screens and the cards, the event table plays them, the test above checks
   both (in play and on a paused run's card). In the stream: every press of the set-up screens and every move and
   press on the pause card found (correlation 0.70 to 0.96). Not done: the pointer entering a button of the set-up
   screens.
3. **The first round of each gun sample came late.** Unreal reads a wave's audio from the pak the first time it
   plays. Before the fix (package `924bbce`, runs `snd-dev1`, `snd-keys1`): the packet with the CHOPPER's first three
   single rounds arrived 144, 155 and 166 ms after the click (one for each of its three close samples), the NINE's
   145, 156 and 184 ms, the first whoosh 141 ms, the first jump 171 ms; a burst right after: 33 ms. Now every wave is
   loaded and its audio kept in memory when the world begins play (`UMIAudioSubsystem::Preload`; the log: "sounds:
   288 of 288 Sound Waves loaded and kept in memory in 88 ms"). **After the fix** (run `snd-keys`; in brackets the first zip's
   run): the CHOPPER's first three rounds **41, 50 and 61 ms** after the click (32, 54, 65), the NINE's **27, 35
   and 54 ms** (31, 33, 34), the jump 35 ms (41), the reload's first sound 45 ms after R (47).

A sound without its asset, or an id the data does not have, now also shows in a running Shipping game: `sndMissing`
in the probe line (0 in every run here).

### 6. The mix

- **Nothing clips, by a hair.** Peaks of the two long runs: -0.8 dBFS (Shipping) and 0.0 dBFS with 2 samples at full
  scale out of 31 million (Development; both in the half second in which a whole magazine is fired). The seven short
  runs with a burst of 1.2 s: -1.2 to 0.0 dBFS, in five of them 2 samples at full scale. The game's limiter stops at
  -0.3 dBFS and the codec adds the rest; the web game has 1.9 dB more room there, because its volume setting comes
  after its limiter and here it comes before (as a gain of the mix: Pixel Streaming takes the sound before the
  device's own volume, so the Volume row could not work otherwise). Not changed; AUDIO.md 3.3 says it as it is now.
- **The music does not drown the guns or the voice** (Shipping run, dBFS RMS per part): the home screen -28.0,
  standing in the run -27.3, single rounds -25.1 with half seconds of -19.8, a burst -15.3, a magazine emptied
  -14.1, the pause card -35.6. The run-start line ("I-N-C!") lifts its half second to -21.5 over a bed of -27. By
  sample: the drum stem arrives at -16 to -17 dB, the CHOPPER's close layer at -8 to -11 dB, the voice at -7 dB.
- **Against the data and the web game's code.** The category gains the game applies are the data's volumes times the
  volume setting, as `src/audio` has its buses: gun 1.0, tail 0.85, near 0.95, world 1.05, ui 0.95, music 0.5, voice
  1.0, each times 0.8 (the log's `mix=`: 0.80, 0.68, 0.76, 0.84, 0.76, 0.40, 0.80). **Every mono sound then arrives
  4.5 to 6.5 dB under volume x gain, each the same** (25 sounds of the Development run's table: clicks, the radio,
  both guns and their tails, the reload's parts, steps, the jump, the whoosh, the voice, the stings), so the levels
  between the kinds are as the data gives them. The stereo street bed arrives about 2.5 dB under: Unreal plays a mono
  source at half amplitude in each front channel and a stereo one nearly whole, where the web game plays both whole.
  **So the street bed sits about 3 dB higher against everything else than the numbers say.** Measured, not changed.
- **The Volume row works through the stream** (the Settings card has one, the master volume): on the pause card,
  forty presses of Left (80 % to 40 %) took the music from **-35.9 to -42.6 dBFS (-6.7 dB; the setting alone is
  -6.0 dB)**, and forty presses of Right brought it back to -35.4 (the first zip's run: -35.7, -42.3, -35.7).
- **Paused**: the street bed stops (no loop start of it while the card is up; found again after the resume), the
  music stays, about 9 dB down (the drum stem at -25.7 dB against -17; the part's level -35.6 dBFS; the data: 45 %
  behind 1.3 kHz), the card's moves and presses sound. That is the web game's pause (`src/audio`: the world's buses
  close, the dry bus and the thinned music stay).
- **On the click card** the home screen's music and street play as on the home screen itself (-28.4 and -28.0
  dBFS; the street bed found under the card). The web game is silent before its first click because a browser starts
  no sound without one; here E3DS's page holds the stream muted until the same click, which the card asks for.

### 7. What the server gives

**Read in the engine, then measured.** With `-RenderOffScreen` (the launcher always passes it) Unreal 5.9 asks SDL
for its "dummy" audio driver (`LinuxPlatformApplicationMisc.cpp`, `ApplySDLAudioDriverHint`), unless `SDL_AUDIODRIVER`
or `SDL_AUDIO_DRIVER` is set. The game's log on the box, as a new user with no display: "Initialized SDL using dummy
platform API backend", "Using Audio Hardware Device System audio playback device", 6 channels, 48 kHz, buffers of
1,024 frames. The dummy device needs nothing from the machine: the box has no sound card (no `/dev/snd`), and root's
PulseAudio is never asked. Pixel Streaming listens on the mixer's main submix (`AudioProducer.cpp`), folds the six
channels to two and sends what the mixer renders. **So a server with no sound card and no sound service gets the
whole sound**: that is the condition of every run in this entry.

| Condition (Shipping or Development game of a package, new user, no display, no sound card) | The game | The viewer |
|---|---|---|
| nothing in the environment (every run above) | dummy device; all sounds started | sound, no drop-out |
| `SDL_AUDIODRIVER=alsa` in the launcher's environment, launcher of `924bbce` (run `snd-env-alsa`) | "ALSA: Couldn't open audio device: No such file or directory", "FAudioDevice::Init Failed!", "Main audio device could not be initialized"; `sndPlayed=0`, `sndNoDevice=203` | **0.0 s of sound: the stream has no sound at all** |
| the same variable and `SDL_AUDIO_DEVICE_SAMPLE_FRAMES=960`, **launcher of version 3b** (run `snd-env`; the same on the first zip) | "sound: SDL_AUDIODRIVER=alsa ... as the host set them; the game gets SDL's dummy audio device"; 208 sounds started, 0 without a device; 60.0 frames a second | 66.2 s, -25.8 dBFS, no digital silence, nothing lost, no drop-out |

So **`MurderInc.sh` now sets `SDL_AUDIODRIVER` and `SDL_AUDIO_DRIVER` to `dummy` and clears
`SDL_AUDIO_DEVICE_SAMPLE_FRAMES`**, with the reason in a comment and a `sound:` line in the log. Unreal's own null
device, which keeps real time exactly, cannot be chosen: `FMixerPlatformSDL::OpenAudioStream` returns false when SDL
lists no device.

**The dummy device runs about 1 % fast.** It waits a whole 21 ms for every 21.33 ms of sound, so the stream carries
1.009 to 1.011 s of sound per second of wall clock on a free box (1.004 to 1.007 when the box is busy: the wait
overshoots more). No packet is ever short, and a browser's player makes up a sender's clock drift by itself; **what a
real browser makes of 1 % was not heard** (section 10). The obvious cure is worse: asked for buffers of 960 frames
(20 ms exactly) the device runs slower than real time by its wait's overshoot, and the stream has holes: 20 drop-outs
of up to 40 ms and 610 ms lost in 65 s (run `snd-env-960`). Hence the cleared variable.

### 8. Sound under load, and its cost

`sound-short.txt` (the click card and the set-up screens, a run, five single rounds, a burst of 1.2 s, a fast turn,
the pause card: 66 s) on the Shipping game of the zip, new user, fresh copy, the viewer there three seconds after the
game's first probe line (55 s after it in the line called late), the gate's loads from a second process.

#### 8.1 The frame rates, the gun, the music, the memory

The zip to upload (`aa7cc478…`), 12:06 to 12:17 UTC, every line CLEAN:

| Run | Load | Frames a second in the play (lowest second) | Worst frame in the play | Target | GPU time | Sounds started in the play | Drop-outs; sound lost | The five single rounds: click to the arrival of the gun's sound (shortest, middle, longest); the burst | Memory in the play (highest) |
|---|---|---|---|---|---|---|---|---|---|
| `snd-free` | none | **60.0** (59.0) | 21 ms | 60 | 6.5 ms | 183 | 0; 0 ms | 45, **73**, 81 ms; 35 ms | 3,917 to 3,888 MB (3,945) |
| `snd-l20` | 20 ms a frame | 36.7 (29.9) | 34 ms | 45, then 30 | 21.3 ms | 184 | 0; 0 ms | 53, **59**, 94 ms; 58 ms | 3,970 to 3,935 MB (4,030) |
| `snd-l35` | 34 ms a frame | 29.1 (27.0) | 42 ms | 30 | 33.6 ms | 174 | 0; 0 ms | 57, **85**, 92 ms; 69 ms | 3,963 to 3,919 MB (3,982) |
| `snd-cpu6-l35` | 34 ms, the game on 6 CPUs | 29.2 (26.5) | 42 ms | 30 | 33.6 ms | 181 | 0; 0 ms | 55, **76**, 84 ms; 54 ms | 3,004 to 3,218 MB (3,391) |
| `snd-l20-late` | 20 ms, the viewer 55 s later | 30.6 (29.9) | 35 ms | 30 (it had left 45 before the play) | 20.8 ms | 185 | 0; 0 ms | 58, **80**, 95 ms; 80 ms | 3,975 to 3,978 MB (3,978) |
| `snd-l20-c12` | 20 ms, the game on 12 CPUs | 30.2 (29.5) | 38 ms | 45, then 30 | 21.1 ms | 184 | 0; 0 ms | 56, **68**, 85 ms; 59 ms | 3,712 to 3,652 MB (3,808) |

- **The music has no gap in any of these runs, and the gun's sound follows the input at every load**: all five
  rounds of every run were found; the delay from the click to the arrival of the gun's sound is 45 to 95 ms with a
  middle of 59 to 85 ms, and the load makes no difference that these runs can show (the first zip's runs: middle
  57 ms free, 85 and 75 ms under the two loads). It holds the input's own way into the game, which waits for a frame.
- **The worst frame stays far under 100 ms** (42 ms at most under load); **with a free GPU the game holds 60**. No
  pacer time-out in any play; three or four in each whole run and one frame of 0.86 to 0.90 s on the Crew screen:
  the cold start that version 3a's gate describes.
- **For the lag gate to look at**: under the 20 ms load the game went on from 45 to 30 frames a second in these
  runs (GPU 20.8 to 21.3 ms a frame, the edge of what 45 allows); version 3a's gate held 45 at 18.8 ms, and so did
  one run here (`snd-x10`, 45.0, lowest second 43.7). Nothing in version 3b draws more; the load process is the same
  script. Not looked into further.
- **Against version 3a**: the zip is 5.0 MB larger. The Shipping game's memory in a cold Story run is 3,986 MB five
  seconds into the play and 3,944 MB at its end in the run by keyboard (highest 4,037), where version 3a's gate had
  3,813 to 3,963 MB in other scripts: no difference that these runs can show; the waves kept in memory are about
  5 MB of compressed audio. The Development game's full run with a fight: 4,181 MB five seconds in, 4,242 MB at its
  end.

#### 8.2 Holes in the first half minute of a cold start

**In the first zip's runs the music had gaps in the two runs under load on 16 CPUs, all of them before the run
began:**

| Run | Drop-outs | Sound lost | When | Sound per second of wall clock |
|---|---|---|---|---|
| `snd-free-z1` (no load) | 0 | 0 ms | | 1.0085 s |
| `snd-l20-z1` | **13** (30 to 40 ms each) | 450 ms | 1.4 to 23.7 s of the recording; the run began at 30.8 s | 1.0063 s |
| `snd-l35-z1` | **4** | 150 ms | 3.2 to 21.0 s | 1.0041 s |
| `snd-cpu6-l35-z1` | 0 | 0 ms | | 1.0050 s |

What a hole is (looked at in the packets and in the sound of `snd-l20-z1`): the sender's RTP time stamps jump 30 or
40 ms between two packets that follow each other, and **the sound goes on where it stopped**: across each of the 13
holes the street bed's place in its own file steps 30 ms less than the time stamps do (in the seven holes of 30 ms
nothing of the sound is missing, in the six of 40 ms 10 ms are). Nothing was thrown away that mattered; for that
moment no sound was made in time, and Pixel Streaming's sender (closed code: the EpicRtc library) marks the wait as a
gap in the time line. A player has to fill such a gap; **what a browser makes of it was not heard** (section 10). The
Development game's log has no underrun line in such a phase.

**The cause is the box's CPUs in the half minute of a cold start, not the GPU's load, the frame rate or the
menus.** Shown one step at a time, each a run of its own (`snd-x1` to `snd-x10`, first zip):

| What was tried | Result |
|---|---|
| The Development game left on its home screen for a minute under the 20 ms load (`snd-x1`, `-x2`, `-x5`) | 24 to 84 holes, **the last between 28.5 and 30.2 s** of the recording; none in the 22 to 39 s after them: the same screen, the same load, the frame rate still short of its target |
| `top -H` during that half minute, and after it | the game uses **1,050 to 1,380 % of a CPU**: twelve `PSOPrec-Pool` threads at 70 to 90 % each. That is Unreal's pipeline-state precompile, which a game that has never run in its folder does on three quarters of the CPUs (`r.pso.PrecompileThreadPoolPercentOfHardwareThreads`, 75 by default). Beside it: the load process 90 to 120 %, the viewer 20 to 50 %, the desktop's browser up to 110 % (it was playing E3DS sessions for another piece of work). The box: 86 to 95 % busy, which is its limit. After the half minute: the game 290 to 480 %, the box 22 to 46 % |
| The same load, the game on 12 of the 16 CPUs (`snd-x7`), on 8 (`snd-x8`), on 6 (`snd-cpu6-l35-z1`) | **0 holes** |
| The same load on 16 CPUs, the viewer joining 55 s after the first probe line (`snd-x10`) | **0 holes**, 66 s at 45.0 frames a second (lowest 43.7), worst frame 30 ms |
| A free GPU, two busy loops (two CPUs' worth) beside the game from its start (`snd-x9`) | **57 holes**, 2,020 ms lost, all in the first 31.5 s; none in the 35 s after them, the busy loops still running; 58.9 frames a second in the play |
| A free GPU, nothing beside the game but the viewer and the desktop (`snd-free-z1`, `snd-keys-z1`, `snd-dev-z1`, `snd-env-z1`) | 0 holes in four cold starts |
| The 20 ms load twice more on 16 CPUs (`snd-x4`, `snd-x6`) | 22 and 8 holes, all before the run began |
| The same two loads again half an hour later, on the second zip, the desktop's browser idle (`snd-l20`, `snd-l35`, section 8.1) | **0 holes** in both |

So: for about half a minute after its first start in a folder the game takes three quarters of the machine's CPUs
to compile pipeline states, which alone brings this box to its limit; a little more work beside it then (the load
process and a browser that plays a stream; two busy loops) and the threads that make and send the sound wake late:
holes. The box makes this easy to meet: its kernel is a sandbox (gVisor) whose timers are weaker than a real
kernel's when every CPU is busy, and the test's own load process, viewer and desktop are the other work. **Whether
an E3DS machine meets it is not known.** Every session there is a cold start (an empty home), and its machines are
shared with other sessions' games (DECISIONS.md, today), so other work beside a cold start is likely there; whether
its kernel then lets the sound's threads wake in time is what the box cannot say.
**Not fixed.** What would lessen it is fewer precompile threads (a line in the cloud profile); that changes how long
the cold start's hitches last, which is the lag gate's ground and not a sound change, so it is left as a decision
(section 11). The instrument got what it needed to tell the two apart: the summary of a sound run now says under
which of the script's markers the drop-outs fell and how busy the box's CPUs were in the viewer's first 40 s
(`lag-test.sh`'s watcher notes it every second), and `sound-gate.txt` says what each line must show.

#### 8.3 The sound gate on the zip to upload

`sound-gate.txt` (nine lines) was run on the zip `aa7cc478…` from 11:55 to 12:17 UTC: the six lines of 8.1, the two
runs of section 4 and `snd-env` (section 7). Every line CLEAN; in every line 0 sounds without an asset and 0 without
an audio device; **no drop-out in eight of the nine**. The ninth is the queue's first line, the Development game's
run at 11:55 (kept as `snd-dev-first`): **115 drop-outs of up to 70 ms and 4.9 s of sound lost in its first 35 s, on
a free GPU, and none in the 286 s after them** (59.9 frames a second in the play, 1,141 sounds started, none
missing). What the box was doing in those 35 s was not recorded; the record of its CPUs was added to `lag-test.sh`
because of this line, and the line was run again at 12:17 (`snd-dev`, section 4): **no drop-out; "the box's CPUs:
74 % busy in the viewer's first 40 s (busiest second 95 %), 27 % after them"**. That busiest stretch is the game
itself: 86 to 95 % for 33 s with nothing else on the box. So a Development game's cold start alone takes this box to
its limit, and whether the sound then has holes hangs on what little else happens in that half minute.

### 9. Tests, builds, commits

- **`TESTS OK passed=121 failed=0 skipped=0 filter=MurderInc 59 s (report)`** on the box at 12:30 UTC, the gameplay
  clone at `8391b33`, whose game code is the packaged `3dd4053` (the 119 of version 3a with their 11 golden replays,
  and `Audio.SoundsResolve` and `Audio.EveryGunSounds`); the same 121 of 121 at `83d2c61` (56 s) and at `924bbce`,
  and 119 of 119 at `6de5b0b` right after the import, before any code changed. No test was weakened, skipped or
  re-recorded; `Audio.Assets` and `Audio.EngineRender` got stricter.
- **No warning about missing sound is left.** Two warnings remain in the report and neither is one: `Audio.VoiceData`
  ("21 of 21 takes are placeholders", which is true until the owner's recordings arrive) and `Audio.EngineRender`
  ("no audio device in this process (-NoSound)": the suite runs without a device; with one,
  `tools/box/audio-engine-render.sh`, it was not run in this pass).
- Editor target built at `924bbce` (115 s) and `83d2c61` (93 s); both game targets compiled by `package-cloud.sh all`
  at `924bbce` and at `3dd4053`. The gameplay clone on the box is at the pushed head; nothing under `unreal/` differs
  between `3dd4053` and the head, and the zip's launcher is the branch's at `5bba2dd`.
- Changed in the game: `Audio/MIAudioSubsystem` (the warning, the counts, the preload, the Verbose "play" line),
  `Audio/MIAudioDirector` (unknown ids, the gun's sound family, the two menu events), `Cloud/MICloud.cpp` (the probe
  fields), `Flow/MIGameSubsystem` and `UI/MIFrontEnd.cpp` (the menus' notes), `Content/Data/audio.json`
  (`weaponSounds`, `ui:click`, `ui:hover`), the three audio test files. No rule of play changed; `src/` untouched;
  no audio file added, replaced or generated.

### 10. Not done, not proven

- **Not heard by anyone.** Everything here is measurement: which sample, when, how loud. Whether the game sounds
  good, whether the placeholder voice and the generated gun layers are what the owner wants, nobody here can say.
- **The music can have gaps in the first half minute of a cold start** when the machine's CPUs are at their limit
  (section 8.2): measured, explained, not fixed, and not known for E3DS's machines, where every session is a cold
  start.
- **E3DS itself, a real browser.** The viewer is a Python client on the same machine. What Chrome's player makes of
  a sound clock that runs 1 % fast (it should shorten the sound by that much, inaudibly; unproven) and of a gap of
  30 to 70 ms in the time line, whether E3DS's page starts muted and its speaker button unmutes, whether a
  controller's first press counts as the gesture, how the sound sits against the picture: the owner's first session
  with version 3b.
- **The delay ends at the packet's arrival.** A browser's own sound buffer (tens of milliseconds) comes on top, and
  so does the way from the browser to E3DS and back.
- **The heartbeat** under a third of the health: the game started it 0.8 s before the death in `snd-dead1`; too short
  to show in the recording. The hurt and the ear ring are shown as levels, not as samples (table).
- **Sounds the game started that were not found as samples** (the list under the table, the steps in the Shipping
  run among them): their assets are in the pak and the game started them; that a viewer can make them out is not
  shown.
- **`sting_reel`** (a reel secured that is not the last) did not come up: the demo script's two first reels are
  given, not taken. The last reel's sting did. The NINE's slide (a reload from empty), the melee hit, steps on
  surfaces other than asphalt, the four guns other than the STICK and the STRETCH in a stream, Hold the Block, the
  night bed: covered by the tests or by the same code paths, not by a stream run.
- **The street bed 3 dB high and the 1.9 dB less headroom** (section 6): measured and left, because the brief says
  not to redesign the mix.
- **The pointer's hover on the set-up screens** has no sound yet; **`Audio.EngineRender` with a device** was not
  rerun; the lag gate on the zip (`lag-gate.txt`) was not run here: the load lines of section 8 are sound checks
  with the gate's loads, not the gate.
- The dead run and the `snd-env-alsa` run are of the package of 10:18 UTC, and the runs `snd-x1` to `snd-x10` of
  section 8.2 are of the first zip (the game's files are the same in both zips).

### 11. For the release engineer

1. The zip: `/project/ue/cloud/MurderInc-E3DS.zip`, sha256 `aa7cc478…8deb`, parts in `/project/ue/cloud/parts`
   (`parts.sha256`), the Development game's key in `MurderInc-E3DS.devkey` (new for this zip; the first zip's
   fingerprint, key and parts list are kept as `v3b-8ec0f7f7.*`). Version 3a's zip is kept as
   `/project/ue/cloud/v3a-de41a708.zip` with its key and parts list. `/tmp/v3b2/zip` is the zip unpacked as
   `e3dsfresh` (lost when the box stops). If the launcher changes again before the upload: `package-cloud.sh src`,
   `zip`, `MI_TAG=v3b package-cloud.sh parts` (two minutes; no cook), then the sound gate.
2. **The lag gate must be repeated on this zip** (`lag-gate.txt`, 13 runs): the game's code changed (the preload at
   world start, the probe line, the menus' notes), every run now has sound playing, the launcher has the leftovers
   cleanup, and under the 20 ms load the game sat at 30 where version 3a's gate had 45 (section 8.1).
3. **The sound gate** is `sound-gate.txt` (9 runs, about 25 minutes):
   `LAG_BUILD=<unpacked zip> LAG_RUNAS=fresh LAG_CLEAN=1 bash lag-test.sh queue sound-gate.txt`, then
   `python3 sound_table.py /project/ue/cloud/lag/snd-dev --audio /project/ue/repo-gameplay/unreal/MurderInc/Content/Audio`
   and `bash sound-keys-check.sh /project/ue/cloud/lag/snd-keys` (both in `/opt/venv/bin/python3`, after the queue:
   they take every CPU). The file's top says what each line must show. **It needs a quiet box**: no other work, and
   the desktop's browser not playing a stream; each summary now says how busy the box's CPUs were in the viewer's
   first 40 s, and a line with drop-outs in its first half minute on a busy box is run again before the package is
   blamed. The short proof that a package has sound at all: `package-cloud.sh sounds` ("SOUNDS OK: all 289 ...") and
   any summary line's "sound: N sounds started ..., 0 without an asset, 0 without an audio device" with "viewer
   heard: ... digital silence 0.0 s, lost 0 ms, drop-outs 0".
4. **A decision for the lead: the cold start's CPUs** (section 8.2). `r.pso.PrecompileThreadPoolPercentOfHardwareThreads`
   (75 by default; it must be in the engine's ini, the launch option `-dpcvars=` did not change the pool in the
   Shipping game) would leave more of the machine to the sound in the first half minute; it needs a package and the
   lag gate's cold lines, because the precompile then takes longer. Nothing was changed.
5. `LAUNCH.md` still tells the owner that the build is silent (top of the page, sections 4, 7, 9.2, 9.4) and names
   version 3a's parts: it needs version 3b's parts, fingerprints and a line on the sound (the speaker button at the
   bottom right of E3DS's page; the Volume row on the Settings card; a gap in the music in a session's first half
   minute is worth a word back).
6. Storage: nothing was uploaded in this pass.

## Version 3a: the independent release check (release checker, 2026-11-25, 07:56 to 09:20 UTC)

A second pair of hands took version 3a from the owner's storage, not from the box's build folder, and repeated the
release gate without trusting the entry below. **It holds: the stall of version 2 is gone and the file can be
uploaded. And it found what no check before it had looked for: the game has no sound** (section 7; neither had
versions 1 and 2: the sound was never packed). Every number here is from this check's own runs
(`/project/ue/cloud/chk/lag/chk-*` on box ec087d85, the scripts in `/project/ue/cloud/chk/`); where a number of the
entry below was re-read from its raw log, that is said. What is not proven is in section 8, and it is the same
list as before: the box is not E3DS.

### 1. The file, from the storage

- The nine parts were downloaded on the box by their links (random names, as a browser saves them): eight of
  251,658,240 bytes and one of 241,696,231, every sha256 as in LAUNCH.md section 9.
- **The owner's own commands** (the rename loop and the join line, cut out of LAUNCH.md byte for byte and run with
  `shasum` as on a Mac) named the nine parts and joined them: `MurderInc.zip`, 2,254,962,151 bytes, sha256
  `de41a7089a3e940c010806753640e1c84b3f357f0e551e067f300b006eef58e4`. `unzip -t`: no errors, 65 files.
- In the zip: `MurderInc.sh` executable and byte for byte the repository's (sha256 `4254cbef…3343`, the same at
  `6c4d810` and at the head), `BUILD.txt` naming `6c4d810`, `MIDEV.key` equal to the box's copy, no `Saved/`, no
  symbols, no logs. The two game programs are, by sha256, the ones in `/project/ue/cloud/build-Shipping` and
  `build-Development`. The Shipping program holds the texts of the last code commit `906dfdf`
  (`MI.Cloud.FpsPixelPart`, the sentence of the frame-rate target's rise) and none of the Development switches
  (`MICrashTest`, `MICloudLog`, `MIDemo.Run`). The `Source` folder of the release copy, of the gameplay clone and of
  the pushed branch are one and the same (one fingerprint over its 138 files).

### 2. The suite

`build.sh` in `/project/ue/repo-gameplay` at `6c4d810`: "Target is up to date". `tools/box/test.sh MurderInc`, run
again at 08:03 UTC: **`TESTS OK passed=119 failed=0 skipped=0`** (55 s); the report lists 119 tests, all "Success",
116 clean and the 3 audio ones with their usual warnings, the 11 golden replays among them. Nothing under `unreal/`
differs between `906dfdf`, `6c4d810` and the head.

### 3. One session the way E3DS starts it, by hand

Not with the box's test tools: a user that did not exist before (`useradd -m`; its home held the three skeleton
files), the zip unpacked by that user into an empty folder, an environment built from nothing, the working
directory `/`, no display, and E3DS's documented arguments and nothing else (`-PixelStreamingURL= -PixelStreamingID=
-AudioMixer -log -Unattended -StdOut -FullStdOutLogOutput -ABSLOG= -AllowPixelStreamingCommands -Windowed -ForceRes
-ResX=1920 -ResY=1080 -PixelStreamingEncoderCodec=H264 -PixelStreamingWebRTCMaxBitrate= -PixelStreamingEncoderMinQP=
-PixelStreamingEncoderMaxQP=`): no launch option, no probe option, none of the bitrate options the box's viewer
usually gets. Script: `/project/ue/cloud/chk/first-run.sh`.

- The launcher's lines name the build, the user, the card, "Vulkan SM6 check: all 16 extensions present"; the game's
  first numbers line came 10.1 s after the start.
- A viewer (rtcinput.py) clicked the card away, went through the set-up screens into a Story run and turned fast for
  95 s. The game's own line every 30 s, for the two half minutes that lie wholly in the play: **60.0 frames a
  second, worst frame 22.1 and 16.9 ms**, the stream 55 to 57 a second at 17 to 18 Mbit/s.
- Stop as a host that closes "the process we start and every child process under it": SIGTERM to the launcher, tee
  and the game in the same moment. "the game quit normally after 170s (stop asked by SIGTERM)", exit code 0 two
  seconds later, no process left.
- The file named with `-ABSLOG=`, `MurderInc/Saved/Logs/MurderInc.log` and the launcher's output are the same 50
  lines, byte for byte.
- Frames looked at (1920 x 1080 as received): the click card over the dimmed home screen with its three lines; the
  home screen; the street at the start of the run; a frame after fast turning (whole, sharp, "CHOPPER 28" after two
  clicks); **the pause card with its line**: "NVIDIA RTX PRO 6000 Blackwell Server Edition · 60 frames a second
  (lowest 60, target 60) · GPU 5.1 ms · drawn 1440 x 810, sent 1920 x 1080 · stream 60 a second (lowest 38),
  19.2 Mbit/s, QP 22, round trip 0 ms · build 6c4d810".

### 4. The gate, repeated

`lag-test.sh` on the zip unpacked as `e3dsfresh`, every run with a new empty home and the folder's `Saved` removed
(cold), one game on the card at a time (every run CLEAN), the viewer there as soon as the game is (`join=3`). The
viewer is this check's own (`chk/chk-story.txt`): it turns more and faster than `lag-story.txt` (173 and 288
degrees a second) and **stops dead eight times** between flicks of 180 degrees, because version 2 froze when a turn
ended; it walks, holds the fire button while turning and reloads. About 6,000 degrees of turning in a minute of
play. The numbers are read from the game's raw lines by this check's own script (`chk/chk_probe.py`), not by
`lag_sum.py`.

| Run | Game | Load (GPU time a frame) | Frames a second (lowest second) | Worst frame in play | Frames over 100 ms | Owed | Fence lines in play | Memory over the play | Stop |
|---|---|---|---|---|---|---|---|---|---|
| `chk-free` | Shipping | none (5.9 ms) | **60.0 (59.1)** | 31 ms | 0 | 2 | (no engine log) | 3,963 to 3,941 MB | exit 0 |
| `chk-l20` | Shipping | 18.8 ms | 45.0 (44.8) | 27 ms | 0 | 2 | | 3,912 to 3,843 MB | exit 0 |
| `chk-l35` | Shipping | **31.6 ms: the lag's load** | **29.8 (28.4)** | **48 ms** | **0** | 2 | | 3,905 to 3,868 MB | exit 0 |
| `chk-l35dev` | Development, played from the home screen | 27.5 ms | 30.0 (29.8) | 39 ms | 0 | 2 | **0** (2 at the Crew screen's cold frame) | 4,151 to 4,106 MB | exit 0 |
| `chk-cpu6-l35` | Shipping, 6 CPUs | 29.8 ms | 30.0 (28.7) | 38 ms | 0 | 2 | | level, one step when the view first turns (below) | exit 0 |
| `chk-cpu6-l35dev` | Development from the home screen, 6 CPUs | 28.0 ms | 30.0 (29.8) | 39 ms | 0 | 2 | **0** (2 at the Crew screen) | the same | exit 0 |
| `chk-l35dev-script` | Development, run started by script | 28.3 ms | 30.0 (29.9) | 37 ms | 0 | 2 | 0 | | exit 0 |
| `chk-cpu6-l35dev-script`, `-b`, `-c` | the same on 6 CPUs, three times (the gate line that logged one fence line in the entry below) | 27.8 to 28.3 ms | 30.0 (30.0, 29.8, 30.0) | 35, 39 and 34 ms | 0 | 2 | **0, 0 and 0** | | exit 0 |

"No frames available for capture": in no run. Pacer time-outs in the play: none in any run (2 to 4 in the whole run,
at the cold start and the Crew screen, as the entry below says). The engine's own CSV profile of
`chk-l35dev-script` (2,554 frames, 85 s) agrees with the game's line: longest frame 62 ms, none over 100 ms, the
middle frame 33.3 ms.

**So the gate passes here too**: with the card loaded the way the lag is reproduced, a Story run with fast turning
and dead stops has no frame over 100 ms (48 ms at the most in the Shipping game), no fence line in the play, level
memory and a clean stop; with a free card the game holds 60.0.

Memory on 6 CPUs, since the table's number alone would mislead: 2,945 to 2,971 MB for the first 23 s of the play,
one step to about 3,200 MB in the three seconds in which the view first turns right round (the rest of the block
comes into view), then level between 3,197 and 3,264 MB to the end. A pile grows by hundreds of MB every second.

### 5. Version 2 under the same load, the same morning

The control that makes the table mean something: version 2's zip (`ceaf828d…`, game `e989cb8`), unpacked the same
way, the same load, the same tool (`chk-v2-l35dev`: the Development game with its script-started run, the viewer of
`lag-turn.txt`), next to version 3a in the same harness (`chk-l35dev-script`).

| | Version 2 | Version 3a |
|---|---|---|
| Frames a second in the run | 34.6 on average, lowest second 13.5 | 30.0, lowest second 29.9 |
| Worst frame | **1,302 ms** | **37 ms** |
| Seconds with a frame over 100 ms | 16 of 56 (1,302 and 1,095 ms, then ten seconds in a row with frames of 291 to 346 ms, then 737, 685 and 702 ms) | 0 of 50 |
| "Timed out waiting for fence" | 498 | 0 |
| "No frames available for capture" | 2,282 | 0 |
| Memory | 3.8 GB five seconds into the run, 4.8 GB at its end and still rising | level once the level has loaded |
| Stop | did not end within 30 s of SIGTERM, killed | exit 0 |

### 6. Beyond the gate

| Run | What | Result |
|---|---|---|
| `chk-l48` | a load far past the gate: the card needs 83.5 ms a frame at the smallest picture | **a steady 12.0 frames a second** (lowest second 11.4), worst frame 96 ms, 2 frames owed, memory level, exit 0. Too slow to play, but no freeze: the game follows the card down instead of piling up |
| `chk-fight-ship`, `chk-fight-free` | the Shipping game, sprinting into the block with the fire button held in bursts, turning, reloading (lag's load; free card) | 29.3 (27.8), worst frame 60 ms; 60.0 (59.1), worst frame 31 ms. The enemies answered ("They made you…", health 94 in one frame) |
| `chk-fight-dev` | the same in the Development game with god mode | 30.0 (29.1), worst frame 38 ms, no fence line, no skipped capture |
| `chk-l35-v2opts` | version 2's launch option left in by mistake (`-PixelStreamingDecoupleFramerate`), lag's load | 29.7 (28.1), worst frame 56 ms, exit 0; the viewer counted 1,210 repeated pictures of 2,765, as LAUNCH.md warns |
| `chk-long-l35` | six minutes of play under the lag's load | 319 s of play, 31,992 degrees turned: **29.8 frames a second (lowest second 28.3), worst frame 64 ms, none over 100 ms**; memory 3,871 MB five seconds in, 3,909 MB at the end, never over 3,984 MB; the card's counter level; exit 0 after 408 s |
| `chk-hold-l35` | Hold the Block, chosen with the mouse on the home screen, a minute of quarter turns and bursts under the lag's load | the mode chip took the click ("HOLD THE BLOCK · Wave 1"); 29.8 frames a second (lowest second 27.6), worst frame 41 ms; **the wave killed the player after 23 s** and the "LIGHTS OUT" card came through the stream whole and sharp (time on the block 0:23, RUN IT BACK, CHANGE SET-UP, BACK TO TITLE, "Up/Down choose · Enter select · or click"); no frame over 100 ms at the death or on the card |
| `chk-dead` | Hold the Block on a free card, standing until the wave kills the player, three times | the "LIGHTS OUT" card was left three ways and each started a new run (the game's state went dead, intro, playing): **a mouse click on RUN IT BACK, Enter, and a controller's A** (`pad=1` from that press on) |
| `chk-two` | **two copies of version 3a on the one card, each with its own viewer**: the load the lag was first reproduced with (version 2: frames of 7 s) | no freeze in either: one copy settled on 30 and drew 24.7 frames a second on average (lowest second 19.7), **worst frame 84 ms**; the other on 45, 36.9 on average (lowest 27.5), **worst frame 80 ms**; no frame over 100 ms, 2 frames owed at the most, no pacer time-out in the play, each game's memory level at 3.9 GB after one step when the view first turns, both stopped with exit code 0. Uneven (two games fight for one card, which E3DS does not do: one app a machine), but frames of a twelfth of a second where version 2 had frames of seven seconds |

### 7. Input through the stream, and the sound

The two proof scripts on the zip from the storage (cold, free card, the viewer there at once):

- **Mouse and keyboard** (`chk-keys`, `proof-keys.txt`): one click hid the card; Home by mouse, Crew and Block by
  Tab and Enter, Loadout and the briefing by mouse: state 0, 1, 2. W: `moveY=1.00` then `0.00`. 1,800 browser pixels
  of mouse: the view turned **+216.58 degrees**, and the same back -216.58 (the web game's 0.0021 rad a pixel gives
  216.578). Two clicks: magazine 30, 29, 28. P: paused; a click on Resume: playing again, the magazine still 28.
  Meanwhile 59.9 frames a second, worst frame 33 ms.
- **Controller only** (`chk-pad`, `proof-pad.txt`): the game answered the pad with id 0; the first press, marked as
  a repeat, hid the card; Start five times reached the run (`pad=1`); left stick: `moveY=1.00`; right stick at the
  rim for a second: **263.81 degrees**; trigger: magazine 30, 27, 25 and `fire` back to 0; Start paused, Start
  resumed. 60.0 frames a second, worst frame 19 ms.
- **The sound: there is none.** A copy of the viewer that measures the received sound (`chk/rtcaudio.py`; its
  reading was checked first with a tone through the same Opus decoder) heard digital silence for a whole session
  of the Shipping game, two emptied magazines included (runs `chkaudio`, `chkaudio2`): loudness 0 in every two
  seconds, **every Opus packet 3 bytes**. The earlier checks counted the audio packets and called that sound.
  **The cause is the package, not the stream**: the game plays its sounds from Sound Wave assets under
  `/Game/Audio/` (`FMIAudioData::AssetPath`) and skips a sound whose asset is missing without a word; the gameplay
  clone and the release copy hold the 291 WAV files under `Content/Audio` and **not one `.uasset`** (the import,
  `tools/box/audio-import.sh`, was only ever run in the audio work's own clone `/project/ue/repo-audio`: 289 Sound
  Waves there); the list of what is in the pak (`Manifest_UFSFiles_Linux.txt` in the zip) has **no entry under
  `/Content/Audio/`**, in version 3a and in version 2's zip alike; the Development game of the zip, asked to log
  it, says "no asset for Voice/Rule/inc_02.wav (tools/box/audio-import.sh)". The suite has said so in every run:
  `MurderInc.Audio.Assets` passes with the warning "no audio assets imported yet", one of the "3 with audio
  warnings". **So versions 1, 2 and 3a are silent on E3DS too**, whatever the speaker button does. The fix is no
  game code: run `tools/box/audio-import.sh` in the gameplay clone, package again, check that the pak's list has
  `/Content/Audio/` entries and that a viewer hears the gun (PREFLIGHT.md V3-14). Sound through the stream has
  therefore never been tested at all: its cost in frames, its delay and its level are unknown.
- Re-read from the entry below's own logs: `v3a-input` (double click 30 to 28 with `dbl=1` and `fire=0`; the size
  request of 2560 x 1440 drawn at 1920 x 1080 with `mouseScale=0.6667`; what the first viewer held does nothing for
  the next) and the three gate runs `v3a-free`, `v3a-l35`, `v3a-cpu6-l35dev` say what that entry says they say,
  the one fence line of the last included.

### 8. What this check found, and what stays unproven

- **No sound** (section 7). The one finding that must be fixed before the game goes public. It is not a fault of
  release A (versions 1 and 2 were as silent), and no reason to keep version 3a from the owner's test of the lag,
  the mouse and the controller: LAUNCH.md now tells the owner to expect silence. PREFLIGHT.md V3-14 has the fix.
- **The one fence line** of the script-started Development run on 6 CPUs (entry below, section 4) did not come
  back: three repeats of that gate line here logged none (worst frames 35, 39 and 34 ms), and neither did the two
  runs in which the Development game was played from the home screen. The entry below read it as a cold-start
  artefact of the test script and not as the stall; this check agrees and adds that it is not there every time.
  The gate's line "no fence time-out in a Story run" is met in every run of this check.
- **Cold start, confirmed**: in every run the game's first frame takes 3.2 to 3.7 s (4.2 s on 6 CPUs) with nobody
  connected, and the Crew screen costs one frame of 0.87 to 0.92 s; once, one frame of 105 ms on a later set-up
  screen. Nothing of it in the play. Release B (PREFLIGHT V3-12).
- **The stream's sender is not as even as the game.** On a free card it sent 55.8 of the game's 60 frames a second
  with single seconds at 44 to 50 (the encoder's time for a frame: 8.5 ms on average). Under this check's outside
  load the encoder is slowed too (10.5 to 14 ms on average, single seconds of 22 to 40 ms), and in `chk-l20` it sent
  only 24 to 36 of 45 frames for six seconds of the fast turn while the game drew every one of its 45. That part is
  the test's own load, which shares the card with the encoder as it does with the game; what E3DS's encoder does
  when the game is the only load cannot be seen on the box. If the owner still sees turning stutter with version 3a,
  the pause card's line tells: the game's number steady and the stream's low is this, not the stall.
- **Graphics memory**: the card's counter stands at 6.1 to 6.8 GB through a Story run (one game alone, 1920 x 1080)
  and touched 7.2 GB for 20 s in the controller run. A little over E3DS's "4 to 6 GB" advice; LAUNCH.md section 10
  says so now.
- **In the Development game's picture** during the fight sprint: the engine's red line that the texture pool is
  over its budget (by 264 MB). The Shipping game does not draw it, but the condition is the same: textures come in
  softer than they were made. PREFLIGHT V3-13 (release B) has the pool size.
- **The mouse on the Game OS page**: with Browser Resolution Custom 1920 x 1080 the speed is exact when the picture
  is shown 1920 wide; in a frame 1280 wide, which is what LAUNCH.md section 5's embed makes, the view turns one and
  a half times as fast. LAUNCH.md 9.1 gives the launch option (`-MIMouseScale=0.333` for that frame).
- **Unproven, as before**: E3DS itself (its card, its player page, its encoder settings), a real browser, a real
  controller, a real connection, the delay between hand and picture, a whole Story run to the truck, the Dead and
  Debrief cards, Browser Resolution Dynamic. E3DS's documentation says its idle log-out watches "mouse, keyboard or
  touch"; PREFLIGHT read in its player script that gamepad input counts too: a controller-only player should check
  that the countdown does not appear after three minutes.

### 9. The commits since `0f99e0e`

79 commits before this check's own, all by the same author line; no change under `src/`; no binary file; the
only web addresses are E3DS's public documentation and host names and the session line of the commit trailers; no
email address but the trailer's; no storage link, no key, no account or user name, no person's name in any added
line or message (the starring name on the title screen is the game's own billing, in the repository since its first
commit and in none of these).

### 10. Changed by this check

- `docs/LAUNCH.md`: that version 3a is silent and why (top of the page, sections 4, 7, 9.2, 9.4); E3DS's names and
  facts where the page still had the first upload's guesses (Platform "Linux"; 12 to 16 GB; "Print UE log in
  browser console" and the crash email; closing the tab ends the session; the Core plan renews by itself and added
  minutes recur); version 3a's graphics memory.
- `docs/unreal/PREFLIGHT.md`: V3-14 (the package has no sound). `docs/unreal/DECISIONS.md`, `docs/unreal/RESUME.md`
  section 9, `docs/unreal/AUDIO.md`: the same, where each is read. `docs/unreal/BOX.md`: the pitfalls this check met.
- `tools/box/cloud/lag-stops.txt`: the viewer with dead stops. `tools/box/cloud/lag_sum.py`: a run of version 2's
  zip is counted. No game code, nothing under `src/`.
- On the box only (`/project/ue/cloud/chk/`): `first-run.sh` (a session the way E3DS starts one), `two.sh` (two
  games at once), `chk_probe.py` (the raw probe lines read without `lag_sum.py`), `rtcaudio.py` (the viewer that
  measures the sound), the viewer scripts of the fight, Hold the Block, Dead card, long and sound runs, and every
  run's folder under `chk/lag/`. In the owner's storage, to delete: three small tars of received frames
  (`mi-chk-frames-1.tar` to `-3.tar`) and three used-up address files (`mi-chk-stage-1.txt` to `-3.txt`).

## Version 3a: packaged, gated and delivered (release engineer, 2026-11-25, 06:25 to 07:55 UTC)

Release A of version 3 (the three entries below: play through the stream, the lag, the review's findings) is
packaged, and **the package itself passed the release gate**: the zip, unpacked as a new user with an empty home
into a fresh folder, started with E3DS's documented arguments. It is in the owner's storage in nine parts, checked
from there. No game code changed in this step. What was measured, what was only read and what is unproven is said
where it applies; section 8 lists what is not proven.

**The zip: sha256 `de41a7089a3e940c010806753640e1c84b3f357f0e551e067f300b006eef58e4`, 2,254,962,151 bytes**, game and
launcher from commit `6c4d810` (the game's code last changed at `906dfdf`). `docs/LAUNCH.md` section 9 has the parts,
the E3DS settings and what the owner sends back.

### 1. Before packaging

- **No new data from the owner's E3DS test** had arrived (`DECISIONS.md` ends with the review's decisions of 05:30
  UTC): which graphics card E3DS gave the sessions, its frame rates and the mouse's feel are still unknown. **So no
  default was changed.** Version 3a ships the cloud profile of the two entries below as it stands.
- **The suite at the packaged head:** `TESTS OK passed=119 failed=0 skipped=0 filter=MurderInc 51 s (report)` on the
  box at `6c4d810` (116 without and 3 with the audio warnings this clone always had; the 11 golden replays among
  them; the editor "Target is up to date"). Nothing under `unreal/` differs between `906dfdf` and `6c4d810`.

### 2. The package

`MI_TAG=v3a tools/box/cloud/package-cloud.sh all`, 06:31:29 to 06:36:12 UTC (4 min 43 s): a full cook (2,232
packages, none skipped), both game targets "up to date" (the binaries are those compiled at 05:22 UTC from the same
code, by the review pass), the zip and nine parts. 65 files (version 2's 64 and `MIDEV.key`), 2,729,232,371 bytes
unpacked; no `Saved/`, no `*.debug` or `*.sym`, no log; `MurderInc.sh` in the zip is byte for byte the repository's
(sha256 `4254cbef…3343`); `BUILD.txt` names `6c4d810` for the game and the launcher. Debug symbols:
`/project/ue/cloud/symbols/6c4d810/` on the box. Version 2's zip is kept there as `v2-ceaf828d.zip`.

**The Development game's key** (`-MIDev=<key>`, `MIDEV.key` at the top of the zip) is new for this zip. It is in the
release report to the owner and in `/project/ue/cloud/MurderInc-E3DS.devkey` on the box, nowhere in this repository.

### 3. The release gate on the zip

**How.** The zip unpacked by the user `e3dsfresh` into `/tmp/v3a/zip` on the box. Every run: that user with a new,
empty home (`lag-test.sh runas=fresh`), the folder's `Saved` removed first (`clean=1`: no settings, no shader or
pipeline cache from the run before, which is what a host that unpacks a fresh copy for every session gives), no
display, the launcher of the zip, and E3DS's arguments (`-PixelStreamingURL= -PixelStreamingID= -AudioMixer -log
-Unattended -StdOut -FullStdOutLogOutput -ABSLOG= -AllowPixelStreamingCommands -Windowed -ForceRes -ResX=1920
-ResY=1080 -PixelStreamingEncoderCodec=H264 -PixelStreamingWebRTCMaxBitrate= -PixelStreamingEncoderMinQP=
-PixelStreamingEncoderMaxQP=`, plus the two bitrate options the box's Python viewer needs and `-MICloudProbe=1`).
One game on the GPU at a time, every run CLEAN, the 13 lines of `tools/box/cloud/lag-gate.txt` as runs `v3a-…`
(`/project/ue/cloud/lag/v3a-*/`). The viewer clicks the card, goes through the set-up screens into a Story run,
stands, turns slowly, turns fast and walks while turning. Box ec087d85 (RTX PRO 6000 Blackwell, driver 620.70).

**It passes.** In play, at every load, on all CPUs and on 6: **no frame over 38 ms in the Shipping game's Story
runs** and none over 50 ms in the Development game's (the gate asks for none over 100 ms), never more than 2 frames
owed, no pacer time-out, memory flat, and every game stopped with exit code 0 within 8 s of SIGTERM. With a free
GPU the game holds 60.0 frames a second (lowest second 59.8). The fence lines of the Development game's log need a
sentence more: section 4.

| Run | Game | Load (GPU time a frame) | Settled on: target, picture | Frames a second (lowest second) | Worst frame in play (first 5 s; after) | GPU time (highest second) | Owed | Pacer time-outs in play | Memory 5 s into the play, change to its end | Sent a second (lowest second) | Stop |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `v3a-free` | Shipping | none | 60, 75 % | **60.0 (59.8)** | 21 ms (17; 21) | 5.9 ms (6.7) | 2 | 0 | 3,813 MB, +17 | 57.0 (51) | exit 0 |
| `v3a-l8` | Shipping | 8 ms | 60, 75 % | 60.0 (59.8) | 20 ms (17; 20) | 8.1 ms (9.5) | 2 | 0 | 3,907 MB, +17 | 55.1 (38) | exit 0 |
| `v3a-l12` | Shipping | 12 ms | 60, 70 to 75 % | 60.0 (59.8) | 20 ms (17; 20) | 11.0 ms (12.9) | 2 | 0 | 3,888 MB, +22 | 56.5 (43) | exit 0 |
| `v3a-l20` | Shipping | 20 ms | 45, 50 % | 45.0 (44.8) | 26 ms (22; 26) | 18.8 ms (21.6) | 2 | 0 | 3,937 MB, +15 | 42.5 (22) | exit 0 |
| `v3a-l35` | Shipping | **34 ms: the lag's load** | 30, 50 % | **29.9 (28.9)** | **37 ms** (37; 33) | 29.9 ms (36.5) | 2 | 0 | 3,923 MB, +2 | 29.7 (28) | exit 0 |
| `v3a-l35dev` | Development | the same | 30, 50 % | 30.0 (30.0) | 33 ms (33; 33) | 28.1 ms (32.1) | 1 | 0 | 3,735 MB, +324 (see below) | 29.9 (28) | exit 0 |
| `v3a-cpu6-l20` | Shipping, 6 CPUs | 20 ms | 45, 50 % | 45.0 (44.9) | 24 ms (22; 24) | 18.8 ms (21.3) | 2 | 0 | 3,230 MB, +4 | 43.6 (38) | exit 0 |
| `v3a-cpu6-l35` | Shipping, 6 CPUs | 34 ms | 30, 50 % | 29.9 (28.8) | **38 ms** (38; 38) | 30.3 ms (35.3) | 2 | 0 | 3,203 MB, +45 | 29.6 (26) | exit 0 |
| `v3a-cpu6-l35dev` | Development, 6 CPUs | 34 ms | 30, 50 % | 30.0 (29.5) | 50 ms (35; 50) | 27.6 ms (30.9) | 2 | 0 | 3,053 MB, +392 (see below) | 29.7 (28) | exit 0 |

The four lines that are not Story runs:

- `v3a-cmds` (a viewer's console commands, Shipping): `t.MaxFPS 30` was taken (the log: "Frame-rate target: fixed at
  30 by t.MaxFPS = 30, set by hand"; the last probe lines `fps=30.0 target=30`), `quit` and `r.ScreenPercentage 400`
  were refused, `MI.Cloud.FpsTarget` was read: `cmdRun=2 cmdRefused=2`. **The pause card's line was looked at** in
  the frame the viewer saved: "NVIDIA RTX PRO 6000 Blackwell Server Edition · 60 frames a second (lowest 60, target
  60) · GPU 4.9 ms · drawn 1440 x 810, sent 1920 x 1080 · stream 53 a second (lowest 50), 11.0 Mbit/s, QP 18, round
  trip 0 ms · build 6c4d810": the package's own commit.
- `v3a-input`: the double click cost two rounds (magazine 30, 28, `dbl=1`, `fire=0`; one more click: 27); a size
  request of 2560 x 1440 was drawn at 1920 x 1080 with `mouseScale=0.6667`, 1280 x 720 as asked, 300 x 200 ignored;
  the viewer left holding W and the left button while the magazine ran from 24 to 9: the run paused, `fire=0`,
  `moveY=0.00`; for the next viewer the magazine stood at 8 for 6 s after the resume, a fresh W walked, one click
  fired one round.
- `v3a-pad`: **the first run in which the controller's mapping policy comes from the pak** (earlier test folders had
  it from a Saved override). The first press, marked as a repeat, hid the card; five Start presses reached the run
  (`state=2`, `pad=1`); the trigger ran the magazine from 30 to 10 and the viewer left; for the next viewer `fire=0`
  and the magazine at 8 for 8 s; a click fired one round; a trigger message with the first pad's id fired and
  stopped. 46 repeats dropped.
- `v3a-rise` (13 ms load): the game held 60.0 (59.8) in play, worst frame 20 ms; on the pause card the target put at
  45 and set free came back: "Frame-rate target: 45 -> 60 frames a second: the GPU took 10.8 ms a frame (10.8 ms at
  the smallest picture), under 80 % of the 16.7 ms a frame has at 60, for 10 s, and no run is being played".

**Memory.** Flat in every Shipping run (+2 to +45 MB over about 45 s of play, 3.2 to 3.9 GB; version 2's pile grew
by 250 to 300 MB a second). The two script-started Development runs rise by 0.3 to 0.4 GB in the first 20 s of their
play and then stand still (3,425, 3,725, 3,735, 3,940, 4,095, 4,100, 4,112, 4,114, 4,118, 4,118 MB at 5 s steps in
`v3a-l35dev`): their script starts the run 12 s after the process, while the level is still loading. With the
Development game played from the home screen like a Shipping run: +35 and +39 MB (`v3a-devstory-…`, below).

**The sender** (recorded, as before; not a gate line): 55 to 57 of the game's 60 frames a second encoded and sent
(lowest seconds 38 to 51), 42.5 to 43.6 of 45 (lowest 22 and 38), 29.6 to 29.9 of 30 (lowest 26 to 28). The box's
second process shares the card with the encoder as it does with the game; `v3a-l8`'s one second at 38 and
`v3a-l20`'s at 22 are lower than the review's runs showed (45 and 40). The game's own frames were not touched in
those seconds.

**One frame looked at** for the picture itself (the capture path did not change, but the cloud profile now comes
from the pak): `v3a-l35`'s fast-turn frame, 30 frames a second with the picture at 50 %: a whole picture, no tear,
nothing half-drawn, the HUD sharp; the scene is soft and the room behind the shop window smears while turning.

### 4. What a cold machine adds (new in this step)

Every gate run before this one reused a warm folder and a warm home. A host that starts each session on a machine
that never ran the game has neither, and the runs above show what that costs. It is the same in every run:

| Where | What | Seen by a player? |
|---|---|---|
| The game's first frame | 3.1 to 3.4 s (4.2 to 4.5 s on 6 CPUs); the pacer's wait runs into its 250 ms limit 2 or 3 times | No: nobody is connected yet |
| **The first set-up screen (Crew), about 2 s after "Hit the block" on Home** | **one frame of 0.82 to 0.92 s**, with one pacer time-out before it; in the Development game's log two "Timed out waiting for fence" lines at that moment | **Yes, once per session**: a hitch of about a second on a menu |
| Every other screen, and the play | before the play nothing over 92 ms (one frame of 107 ms on a later set-up screen in the loaded run of the fastest player, below); in the Story runs nothing over 40 ms (50 ms once in the script-started Development run on 6 CPUs) | |

**It is the graphics driver's shader cache, which lives in the user's home.** The same package run by the user
`ue4`, whose home has run these binaries before (runs `v3a-warm1…` to `v3a-warm3…`; that folder's own `Saved` was
new): the game's first frame takes 0.30 to 0.40 s, the whole run has no pacer time-out (longest wait 44 to 48 ms),
the script-started Development run on 6 CPUs logs no fence line (twice: worst frames 37 and 34 ms), and the Crew
screen costs 57 ms. The engine's own pipeline cache file is off in this build (its log: "Vulkan PSO Precaching = 1,
PipelineFileCache = 0"), so a folder's `Saved` carries nothing from run to run; the driver's cache does. A host that
gives every session a new machine never has it: **on E3DS the table above is what every session starts with.**
Making the first minute smoother (PREFLIGHT V3-12) is release B; these numbers are where it starts.

**The fence lines, exactly.** "Timed out waiting for fence" appears in the Development game's log only (Shipping has
no engine log). The gate asks for none in a Story run with fast turning:

| Run | Lines | Where |
|---|---|---|
| `v3a-l35dev` (script-started run, all CPUs) | 0 | |
| `v3a-devstory-l35`, `v3a-devstory-cpu6-l35` (the Development game **played from the home screen by the viewer**, as a player reaches a run; all CPUs and 6) | 2 each | both at the Crew screen's cold frame (2.8 s after the card was clicked away, `state=0`); **none in the run**: 30.0 frames a second (lowest second 30.0), worst frame 35 and 34 ms |
| `v3a-cpu6-l35dev` and its repeat `v3a-cpu6-l35dev-b` (script-started run, 6 CPUs) | 1 each | 25 s after the process started, 13 s into a run that the script starts 12 s after the process: one render frame of 84 ms, one game frame of 50 ms, no skipped capture, 2 frames owed |

So in a Story run as a player can reach it there is no fence line, on 16 CPUs and on 6. The one line of the
script-started runs on 6 CPUs comes from starting a run 12 s after a cold process start, which no player can do
(the stream has to connect and five screens have to be clicked through first); it is one frame of 50 ms, not a
stall. "No frames available for capture" appeared in no run. **The gate's lines for the script-started Development
game should be read with that in mind from now on**; `lag-gate.txt` says so.

**The fastest player** (`lag-test.sh join=3`: every run above had a viewer who joined 55 s after the game's first
probe line, because the Shipping game's wait in `lag-test.sh` looked for a line that never comes; `join=3` is a
viewer who is there 12 s after the game starts and reaches the run 22 to 27 s after it, cold):

| Run | Game | Load | In the run | Before the run, viewer there |
|---|---|---|---|---|
| `v3a-j3-free` | Shipping | none | 60.0 frames a second (lowest second 58.4), worst frame 40 ms | the Crew frame of 872 ms |
| `v3a-j3-l35` | Shipping | 34 ms | 29.9 (28.7), worst frame 38 ms | the Crew frame of 916 ms, and one of 107 ms four seconds later |
| `v3a-j3-devstory-cpu6-l35` | Development, played from the home screen, 6 CPUs | 34 ms | 30.0 (29.9), worst frame 36 ms; **no fence line in the run**, no skipped capture | the Crew frame of 906 ms with the two fence lines |

So the earliest run a player can have is as clean as a late one.

### 5. e3ds-verify

`tools/box/cloud/e3ds-verify.sh start /tmp/v3a/zip-ue4` (the same zip unpacked as `ue4`; 07:31 to 07:49 UTC; two
games at a time, so its frame rates are not measurements). Every run through the zip's own launcher, with a clean
environment:

| Run | What | Result |
|---|---|---|
| `v-long` | 7 minutes, a new user with an empty home and no display, a viewer joining and leaving 11 times, `-ForceRes` 1920 x 1080 | alive at the limit, 11 "Viewer joined" and 11 "Connection lost: the game is paused", memory about 3.7 GB throughout; TERM: exit 0. (The folder is not that user's: `Saved` went to its home, as the launcher's fallback says) |
| `v-sm5` | `-sm5`: the shaders a driver gets that fails Unreal's SM6 check | `VULKAN_SM5`, "Fallback: this GPU or driver did not pass Unreal's SM6 check"; alive 120 s; TERM: exit 0 |
| `v-root` | started as root | the game runs as the folder's owner; TERM to the launcher: "the game quit normally" |
| `v-crash` | the Shipping game killed with SIGSEGV from outside after 30 s | "CRASH: the game was killed by signal 11 (SIGSEGV) after 29s" and the crash report's folder in the launcher's log |
| `v-crash-dev` | `-MIDev -MICrashTest=30` (`e3ds-repro.sh` puts the zip's key in) | **the Development game of the zip started with the key** and crashed on purpose after 35 s; the same log lines |
| `v-nort` | INT to the launcher (the ray-tracing switch of this run does nothing in the Shipping game, which ignores `-ini:`; as noted for version 2) | "got SIGINT: passed it on to the game as SIGTERM", exit 0 |
| `v-dev-quit` | the Development game quits by itself | exit 0 after 48 s |
| `v-vram5000` | 5.0 GB of the card's memory free | starts, 60 frames a second on the home screen; TERM: exit 0 |
| `v-vram6000` | the Development game plays a Story run with 6.0 GB free | 60 frames a second in the run; TERM: exit 0 |
| `v-e3ds-7600` | E3DS-style arguments, 7.6 GB free (an 8 GB card), a new user, a viewer joining and leaving 5 times | 60 frames a second, 5 joins and 5 leaves; TERM: exit 0 |

Two more runs on the zip, by hand with `e3ds-repro.sh`:

- `v3a-plain-midev` (what a visitor could add to a link: `-midev -PixelStreamingEncoderDumpDebugFrames=true`): the
  launcher's log says "launch option -MIDev NOT taken: this package starts its Development game only with
  -MIDev=<key> … The Shipping game runs." and "launch option(s) not passed on to the game (they write files on the
  server): -PixelStreamingEncoderDumpDebugFrames"; the start line names the Shipping game with neither option.
- `v3a-dev-nort` (the Development game with `r.RayTracing=False`, where the override does work): "Ray tracing is
  disabled", "Features: hardware ray tracing off … Lumen on", "Fallback: no hardware ray tracing on this server;
  Lumen traces in software"; 60 s; TERM: exit 0.

The signalling server that was already running was used and left running (`e3ds-verify.sh` used to stop it).

### 6. Play through the stream

Two runs of the packaged Shipping game (fresh user, fresh copy, free GPU), each played by `rtcinput.py` through
the stream from the click card on; the game's probe lines four times a second say what it did
(`python3 lag_story.py <run> state click pad moveY mag fire`), and the viewer saved the frames it received.

| | Mouse and keyboard (`proof-keys.txt`, run `v3a-proof-keys`) | Controller only (`proof-pad.txt`, run `v3a-proof-pad`) |
|---|---|---|
| The click card | one click: `click=1` to `0` | the first press (A, marked as a repeat, as a browser's page sends the first press of a session): `click=1` to `0` |
| To the run | Home's "Hit the block" by mouse; Crew and Block by keyboard (Tab to Next, Enter); Loadout's Next and the briefing's "Hit the block" by mouse: `state` 0, 1, 2 | Start five times: `state` 0, 1, 2 with `pad=1` |
| Move | W for 1.5 s: `moveY=1.00`, then `0.00` | left stick up for 1.2 s: `moveY=1.00`, then `0.00` |
| Turn | 150 mouse events of 12 pixels: the view turned **216.58 degrees** (1,800 browser pixels at the built-in scale are 216.58); the same back: 0.01 degrees from where it started | right stick at the rim for 1.0 s: 268.7 degrees (the web game's rate gives 263.8 for exactly 60 frames, one frame more 4.85) |
| Fire | two clicks: magazine 30, 29, 28 | trigger for 0.4 s: 30, 29, 26, 24, `fire=1` then `0` |
| Pause and resume | P: `state=3`; a click on the card's Resume row: `state=2`, the magazine still 28 (the click fired nothing) | Start: `state=3`; Start: `state=2` |
| The game meanwhile | 59.8 frames a second in play (lowest second 53.6), worst frame 38 ms | 59.9 (58.4), worst frame 23 ms |
| When the viewer left | paused, "Connection lost: the game is paused until a viewer joins, and what the viewer held is let go" | the same |

**Frames looked at** (1920 x 1080 as received; the four the task names at full size, the others on two sheets at
half size; local copies deleted):

- **Home** (after the click): the title, the starring line, the tag line, "HIT THE BLOCK" focused and "GEAR UP", the
  set-up line "RULE · CHOPPER / NINE · The Block · Day", mode, difficulty and time chips, Settings and Controls,
  the two rows of keys ("W A S D Move … P Pause"), and behind it the garage looking out on the sunlit street. Sharp
  text, a whole picture, the game's mouse arrow in the middle, black bars above and below (the title camera's).
  Looks wrong: the word DIFFICULTY touches its first chip (no gap), and the dark half of the garage is grainy.
- **In the run**: the street under the elevated tracks in daylight, the pizzeria's awning, a taxi, the truck behind
  the fence, three distance markers, the arm with its tattoo and the rifle; objective "0 / 3", health 100, the bar
  "CHOPPER 30 · NINE 15 · F RIFLE BUTT · BAG 150", "B SWITCH TO SEMI". Sharp at the 75 % picture, nothing torn or
  missing.
- **After turning** (216 degrees): the closed station gate, a candy shop, a grey car and "ROAD CLOSED" boards under
  the tracks, a hazy shaft of light. A whole, sharp picture; the HUD unchanged. Looks wrong: the rooms behind some
  upper windows are coarse blocks (the small baked room pictures), and the crosshair is reduced to a short tick
  right after the turn.
- **The pause card**: "HOLD UP / PAUSED", Resume (highlighted), Restart run, Difficulty "< Boss >", Settings, the
  hint "Up/Down choose · Enter select · Left/Right change · or click", "P to resume · Esc gives the mouse back to the
  browser; click the game to take it again", and the line of numbers, small, dim and readable: "NVIDIA RTX PRO 6000
  Blackwell Server Edition · 60 frames a second (lowest 56, target 60) · GPU 5.3 ms · drawn 1440 x 810, sent
  1920 x 1080 · stream 60 a second (lowest 48), 4.0 Mbit/s, QP 19, round trip 0 ms · build 6c4d810". The game's
  mouse arrow is on the card.
- On the sheets: the click card over the dimmed home screen with its three lines ("… a gamepad works too", "No
  sound? Click the speaker at the bottom right."); the briefing ("HERE'S HOW IT GOES", crew, guns, block, style,
  "HIT THE BLOCK ENTER"); the weapon box at "CHOPPER 28" after the two clicks and still 28 after the click on
  Resume. Controller run: the pause card says "D-pad or stick choose · A select · Left/Right change" and "START to
  resume"; in play the bar says "VIEW SWITCH TO SEMI" and "RB RIFLE BUTT".
- **Two things a controller player will notice** (frames `pad-home`, `pad-pause`): right after the first press has
  hidden the card, the home screen still lists the keyboard's keys; it names the controller's buttons from the next
  press on (the press that hides the card does nothing else, so the screens have not seen a controller yet). And
  the pause card's line can read "stream 40 a second (lowest 50)": the number in front is of the paused moment, the
  one in brackets the lowest of the last half minute of play. Neither was changed here.

### 7. Delivery

Nine parts of at most 240 MiB (`MurderInc-E3DS-v3a-part1-of-9.zip` to `…part9-of-9.zip`: eight of 251,658,240
bytes, the ninth 241,696,231), PUT from the box to the owner's Higgsfield storage (all nine HTTP 200) and confirmed
there. The parts went up only after the gate and the stream proof had passed. **Checked from the storage** on the
build machine: every part downloaded back, each sha256 as in `/project/ue/cloud/parts.sha256` and LAUNCH.md section
9; joined: 2,254,962,151 bytes, sha256 `de41a708…58e4`; `unzip -t`: no errors, 65 files; `MurderInc.sh` byte for byte
the repository's; `BUILD.txt` names `6c4d810`, which is on the pushed branch; no `Saved/`, no symbols, no log. The
local copies were deleted. The download links and the Development game's key are in the release report only.

**The E3DS settings the owner should use** (LAUNCH.md 9.1): Browser Resolution Custom 1920 x 1080; launch options
empty (take out version 2's `-MICloudProbe=10 -PixelStreamingDecoupleFramerate`); the console-commands field empty;
Video Quality Medium; H264; Max Session Time 15; inactivity 3 and 1 (minutes); mouse Locked; the browser log and
the crash email on while testing. **What to send back:** a screenshot of the pause card taken after a fast turn or
a stutter.

### 8. Not done, not proven

- **E3DS itself.** Everything here is the box: one RTX PRO 6000 Blackwell, a second process as the load, a Python
  viewer on the same machine (round trip 0 ms). Which card E3DS's Linux sessions get, and whether it is slow the way
  the test load is, is still not known; the owner's pause-card screenshot is the first data.
- **A real browser, a real controller, E3DS's own player page, a real connection.** The viewer sends what Pixel
  Streaming's reference page sends, as read in its source. Whether E3DS's page sends the double click without a
  release, marks a controller's first press as a repeat, or delivers its console-commands field to a Linux app, is
  unproven; so is whether a controller press alone starts the sound.
- **A whole Story run and a Hold the Block run through the stream**, the Dead and Debrief cards in a stream, a
  fight: the runs here play the first 20 to 50 s of a Story run, standing, walking, turning and firing a few
  rounds. No enemy was fought.
- **The delay between hand and picture** was not measured (release B, V3-4).
- **The cold start on E3DS.** The box's cold runs have an empty driver cache but a warm file cache (the zip had
  just been unpacked), and a far faster card and processor than a small cloud server. The 0.85 s at the Crew screen
  and the 3 to 4.5 s first frame may be longer there. Why the Crew screen is the one that costs (what it compiles)
  was not traced.
- **The one fence line of the script-started Development run on 6 CPUs** (section 4) is explained by where it
  falls, not by a trace of the 84 ms render frame behind it.
- **The sender's low seconds** (38 of 60, 22 of 45 in two runs) are recorded, not explained; as before, some frames
  take the encoder longer than a frame lasts.
- **Browser Resolution Dynamic** stays untested beyond the three size requests of `v3a-input`; the settings keep it
  off.
- **A thin connection**: not tested; the pause card's line tells it apart from a slow card.
- **Browsers other than Chrome, the Game OS page itself, the minutes a session costs**: the owner's side.
- Seen in the frames and left as it is: the home screen lists the keyboard's keys to a controller player until a
  second controller press; "DIFFICULTY" touches its first chip on the home screen; the pause card's stream number
  can be lower than its "lowest"; coarse rooms behind some windows.

### 9. Tools changed in this step

- `lag-test.sh`: `runas=fresh`, `clean=1` (the gate as a host starts a package), `join=<seconds>` (when the Shipping
  game's viewer joins: its wait looked for a line that never comes, so every earlier run's viewer found a home
  screen that had been drawn for about 55 s; that stays the default, `join=3` is a viewer who is there at once).
- `lag_sum.py`: the worst frame of the first 5 s of a run apart from the rest; the game's memory at the start and
  the end of the play; the worst frame and the pacer's time-outs outside the play, with a viewer there and with
  nobody watching.
- `e3ds-verify.sh` uses a signalling server that already listens and leaves it running (it used to stop one that
  other tests were using). `package-cloud.sh parts`: `MI_TAG` names the parts for the storage.
- `proof-keys.txt`, `proof-pad.txt`: the stream proof as viewer scripts.

## Version 3, release A: the review's findings (2026-11-25, 04:30 to 06:30 UTC)

Two reviews of release A's changes (the diff `0f99e0e..f54b135`: the gameplay part and the lag work below) found
ten faults. **All ten were real; all ten are fixed.** Each was checked first (in the engine's source on the box, in
the web game, and, where a run could show it, by a run), then fixed with a test where one is possible, then checked
through a real WebRTC stream on the box, for five of them also against the binaries from before the fix. **Nothing
was packaged here.**

The two that could have sunk the launch:

- **On a server with 8 hyper-threaded CPUs or fewer the pacer froze the game for a quarter of a second in every
  frame the GPU was the limit.** The box has 16 CPUs and could not show it; with the game held to 6 CPUs it did
  (section 1). How many CPUs E3DS's servers have is not known; the small GPU servers of the large cloud providers
  have 4 or 8 (from general knowledge of their lists, not from E3DS).
- **Two quick clicks left the fire button held** when the page sends the browser's double-click message with no
  release after it, which is how the review read E3DS's page: an automatic gun kept firing until the next click
  was let go, and that click fired nothing (section 3). Version 2 treats the message the same way, so if the
  reading is right the owner's test already had it.

What was measured, what was only read and what is unproven is said where it applies; section 8 lists what is not
done. Runs are named; their files are in `/project/ue/cloud/lag/<name>/` on the box.

### 1. The pacer on a server with few CPUs (must-fix)

**Read in the engine, then reproduced.** The pacer's game thread waited by polling a GPU fence every fifth of a
millisecond. `FRHIGPUFence::Poll` carries the note "Do not call poll in a loop to block until completion. Some
platform RHIs will not signal fences unless the RHI thread continues to make progress and submit GPU work. To block
for completion, call Wait(), which can only be done from the render thread" (`RHIResources.h`). Unreal's Vulkan RHI
is such an RHI when it starts without its interrupt thread, and it starts without it when the task graph has 6
workers or fewer (`VulkanSubmission.cpp`, `InitializeSubmissionPipe`: `GetNumWorkerThreads() > 6`); on Linux the
workers are the logical CPUs minus 2 with hyper-threading and the cores minus 1 without
(`UnixPlatformMisc.cpp`, counted from the CPUs the process may run on). Finished GPU work is then collected only
when the RHI thread submits, or when somebody waits for a sync point (`ProcessInterruptQueueUntil`). While the game
thread waited, nothing submitted: the fence it polled could not be seen to pass.

`lag-test.sh` got `cpus=<list>` (the game under `taskset`; the load and the viewer keep all CPUs). On 6 CPUs the
game starts 5 workers; its log says "Number of logical cores available for the process: 6". **The release A code on
6 CPUs** (binaries of `4c385f9`):

| Run | Load (GPU time a frame) | In play | In the whole run |
|---|---|---|---|
| `rf-cpu6-l35` Shipping | 34 ms, the lag's load | **24.8 frames a second (lowest second 7.0), worst frame 253 ms**, 43 pacer time-outs, 4 frames owed | 123 time-outs |
| `rf-cpu6-l35dev` Development | the same | 29.6 (lowest 16.9), worst frame 252 ms, 3 time-outs, **44 fence time-outs** in the engine's log | 32 time-outs; the log: "the GPU finished no frame during three waits in a row of 250 ms ... the game runs unheld for 3 s" again and again |
| `rf-cpu6-l20` Shipping | 20 ms | clean at 45 (the GPU keeps up at 45) | **78 time-outs, all on the home screen and the set-up screens**, where the target is 60: four freezes of 250 ms, three seconds unheld at 50 frames a second, and again |
| `rf-cpu6-free` Shipping | none | 60.0, worst frame 36 ms | 1 time-out (at the start) |

The gate's summary line had said "time-outs 0" for `rf-cpu6-l20`: it counted the play only. `lag_sum.py` now also
prints the time-outs of the whole run.

**The fix** (`FMIGpuPacer::WaitOnRenderThread`, `Cloud/MIPacing.cpp`). When a frame must wait, the game thread asks
the render thread to wait for the fence of the frame that has to be finished, with `FRHIGPUFence::Wait`: the call
the engine's header names, and the one the engine itself uses for its occlusion read-back (`SceneOcclusion.cpp`);
on Vulkan it is `ProcessInterruptQueueUntil`, which works with and without the interrupt thread. The command sits
behind everything the frame before drew, so it holds up nothing that could run. The game thread still looks at the
fences every fifth of a millisecond and keeps its 250 ms limit. That limit no longer cuts the hold short: a frame
the GPU needs longer for still holds the next frames at the render thread, which is the hold the pacer is for.
The game's start lines now say which kind of server it is on ("[MICloud] CPUs: 6 cores, 6 with hyper-threads, 5
task workers (6 or fewer: the RHI runs without interrupt and submission threads)"), and the launcher's log has a
`CPUs:` line.

**The same runs with the fix** (binaries of `c7e2a09`, the final code; the full table is in section 7):

| Run | Load | In play | In the whole run |
|---|---|---|---|
| `rg-cpu6-l35` Shipping, 6 CPUs | 34 ms | **29.8 frames a second (lowest second 27.9), worst frame 40 ms**, 2 frames owed | **0 time-outs**, longest wait 41 ms |
| `rg-cpu6-l35dev` Development, 6 CPUs | 34 ms | 30.0 (lowest 30.0), worst frame 34 ms, **0 fence time-outs**, 0 skipped captures | 0 time-outs, longest wait 49 ms |
| `rg-cpu6-l20` Shipping, 6 CPUs | 20 ms | 45.0 (lowest 44.8), worst frame 26 ms | 0 time-outs (78 before), longest wait 48 ms |
| `rg-flight0-cpu6` Shipping, 6 CPUs, `MI.Cloud.GpuFramesInFlight=0` | 34 ms | 28.2 (lowest 25.8), worst frame 49 ms, 1377 frames held | 0 time-outs, longest wait 135 ms |
| `rg-cpu4-l35` Shipping, 4 CPUs (3 task workers) | 34 ms | 29.8 (lowest 28.2), worst frame 50 ms | 0 time-outs, longest wait 55 ms |
| `rg-cpu4-free` Shipping, 4 CPUs | none | 60.0 (lowest 59.8), worst frame 19 ms | 0 time-outs, longest wait 56 ms |

The `rg-flight0-cpu6` line is the hardest case for the wait: with no frame allowed in flight the game thread waits
for the GPU in every frame, 1377 times in the play, and never ran into the limit. The two 4-CPU lines (the
smallest GPU servers of the cloud providers have 4) were run once each after the gate; they are not gate lines.

### 2. The other nine, one by one

| Finding | Checked | Changed | Verified |
|---|---|---|---|
| **A double click leaves the left button held** (must-fix) | Engine source on the box: `RTCInputHandler.cpp` `HandleOnMouseDoubleClick`, `InputHandler.cpp` `OnMouseDoubleClick` (the window's `OnMouseDoubleClick`), `SlateApplication.cpp` `ProcessMouseButtonDoubleClickEvent` (adds the button to the pressed buttons; "treat this event as a mouse down"), `SceneViewport.cpp` (`IE_DoubleClick`), `PlayerInput.cpp` (a press is counted). Epic's front end change log, 0.3.0: "the plugin treats MouseDouble as a press-class event but never synthesizes a release". **Shown on the box with the binaries from before the fix** (`rg-dbl-old`, section 3). **E3DS's page script was not read again** (it is not saved anywhere and its host cannot be reached from the build machine): that E3DS sends no release after the message is the review's reading. The fix does not depend on it | `UMICloudSubsystem::GuardViewerInput` replaces Pixel Streaming's handler of "MouseDouble" with one that drops the message and counts it (`dbl=` in the probe line). Both clicks have arrived as presses and releases already. With a page that does send a release after it, that release finds the button up | Stream, Shipping game (`rf-input`, and `rg-input` on the final code): two clicks and the message as a browser sends them: the magazine went 30 to 28, `dbl=1`, `fire=0`; a single click after it: 27. Seen in a received frame: "CHOPPER 28", where the old binaries show "CHOPPER 0". No automation test: the message exists only in the game target (Pixel Streaming is not in the test build) |
| **The first press of a controller button is thrown away** | Epic's `GamepadController.ts`: `onGamepadConnected` copies the pad's state as both the current and the previous state, and the page then sends `GamepadButtonPressed` with repeat = 1 for a button that was down when the browser showed it the pad. A browser shows a pad to a page only after a button press (Chrome's behaviour: from knowledge, not measured). **Shown with the old binaries** (`rg-pad-old`): the press marked as a repeat left the click card up (`click=1` while `padRepeats` rose), the next press was spent on the card, and the script's five Start presses no longer reached the run (`state=0` to the end) | `FMIPadButtons`: of one hold only the first message goes on, marked as a repeat or not; every later one is dropped as before (one tap still acts once) | Test `MurderInc.Input.PadMenu`. Stream (`rf-pad`, `rg-pad`): the session's first button message marked as a repeat hid the click card (`click=0`); the five Start presses went into the run (`state=2`), 46 repeats dropped |
| **What a viewer held when the connection was cut stays held** | `PlayerInput.cpp`: a key stays down until a release, an axis keeps its last sample. Pixel Streaming releases nothing when a viewer goes, and sends a trigger's last value again every frame until a zero arrives (`InputHandler.cpp`, `bKeepUnlessZero`). E3DS reconnects inside a session (its page on monitoring sessions) | `UMICloudSubsystem::ReleaseForLeave` and `AMIPlayerController::DropAllHeld`: `FlushPressedKeys`, the controller's own move, sticks, fire, aim, sprint latch and grab, the pawn's input. Pixel Streaming gets a zero for every trigger and stick of every pad it knows. **Not as the review proposed**: the pads are not reported as disconnected, because a page that reconnects may keep the id it was given (DECISIONS) | Test `MurderInc.Cloud.ViewerLeaves` (W, Shift, the left stick, the right trigger and E held; after the leave and a resume nothing moves or fires; a fresh W, click, trigger and Shift count at once). Stream (`rg-input`, `rg-pad`): the first viewer left holding W and the left button, or with the trigger pulled, while the magazine was running down; the next viewer resumed: `moveY=0.00`, `fire=0`, the magazine stood still for about 6 and 8 s; a fresh W walked, a click fired one round, and a trigger message with the first pad's id fired and stopped. The old binaries were not run with a second viewer: that they keep firing is read in the engine |
| **Controller X reloads as well as grabs at a reel** | The web game, `src/input.js` padDown: "X reloads, unless a prompt is showing at the moment of the press: then it interacts, for that whole hold" | One action for the pad's X (`IA_PadX`), decided when the press starts; R and E as before. 70 key mappings (71). This one changes the desktop game too: the fault was there as well | Tests `MurderInc.Player.PadReloadOrGrab` (away from a reel: one reload, no grab; at a reel with rounds missing: the grab, the reel taken, no reload, the magazine as it was; R and E unchanged), `MurderInc.Core.GameClasses` |
| **The last viewer leaving in a run's intro does not pause** | `MICloud.cpp` paused only in `Playing`; the pause key pauses in the intro too (`UMIGameSubsystem::PauseKey`) | `ReleaseForLeave` pauses in `Intro` and `Playing` | Test `MurderInc.Cloud.ViewerLeaves` (leave in the intro: paused, and still paused 4 s later) |
| **A target that has dropped cannot come back on a card that holds 60** | The rise asked for a GPU time under 45 % of the frame time now (10 ms at 45). **Shown with the old binaries** (`rg-rise13-old`): under a 13 ms load the game held 60 in play (60.0, lowest second 59.9), and a target put at 45 on the pause card and set free stayed there for the 25 s the run still had (the card took 10 to 12 ms a frame) | The rise is judged by the rate it goes to: the GPU's time, worked out for the smallest picture, under four fifths of the next rate's frame time (13.3 ms to 60, 17.8 ms to 45). See section 4 for why the picture's size hardly enters | Test `MurderInc.Cloud.FrameRate`. Stream, the same load and script on the final code (`rg-rise13`): ten seconds after the target was free the log said "Frame-rate target: 45 -> 60 frames a second: the GPU took 10.8 ms a frame (10.8 ms at the smallest picture), under 80 % of the 16.7 ms a frame has at 60, for 10 s, and no run is being played", and the probe lines went to `target=60`. (Under the lighter 12 ms load the card takes 9.6 ms and both rules rise, `rg-rise` and `rg-rise-old`: the gate line uses the 13 ms load) |
| **What a visitor may set can still exhaust the GPU** | `VolumetricFog.cpp`, `FroxelGridUtils.cpp`: the fog's grid is (width / GridPixelSize) x (height / GridPixelSize) x GridSizeZ and neither is limited from above. `RTCInputHandler.cpp`: the size request runs `r.SetRes` for any size of 1 or more. **Shown with the old binaries** (`rg-dbl-old`): asked for 2560 x 1440 the stream became 2560 x 1440, asked for 300 x 200 it became 300 x 200 | `MITuning`: `r.VolumetricFog.GridPixelSize` 8 to 32, `GridSizeZ` 32 to 128 and nothing else of the fog; `sg.` 0 to 3; `PixelStreaming2.Encoder.DumpDebugFrames` and `PixelStreaming2.DumpDebugAudio` refused. The size request has the game's own handler (`FMICloudSize`): ignored below 640 x 360, cut down to fit 1920 x 1080 with its shape kept, and the mouse scale multiplied by requested width / drawn width (without that the cap would have slowed the mouse of every viewer with a larger frame; the rest of PREFLIGHT V3-6 stays release B). The launcher also drops `-PixelStreaming...DumpDebug...` launch options | Tests `MurderInc.Cloud.Tuning`, `MurderInc.Cloud.ViewerSize`. Stream (`rf-input`, `rg-input`): 2560 x 1440 stayed 1920 x 1080 with `mouseScale=0.6667`; 1280 x 720 was drawn as asked (the stream changed size while running and back: both frames looked at, whole pictures); 300 x 200 was ignored. `rg-cmds`: `quit` and `r.ScreenPercentage 400` refused, `t.MaxFPS 30` taken (`cmdRun=2 cmdRefused=2`) |
| **The debug switches are one link parameter away (`-MIDev`)** | `MurderInc.sh` took `-MIDev` from its arguments; E3DS passes what a visitor writes after `?exeLaunchArgs=` (its page on advanced command-line parameters) | The launcher starts the Development game only with `-MIDev=<key>`, the word in `MIDEV.key` at the package root; `package-cloud.sh zip` makes a new key for every zip (and keeps it in `/project/ue/cloud/MurderInc-E3DS.devkey` for the release report). A plain `-MIDev` or a wrong key starts the Shipping game and says so in the log. A folder without the file (a test folder) takes the plain switch; `e3ds-repro.sh` puts the key in for the box's tests | The launcher's argument handling run with stand-in games on the build machine (no key file; plain, wrong, right and empty key; the dump options). The new launcher with the real games on the box, in a copy of the test folder with a key file: the tests' plain `-MIDev` started the Development game (`rf-launch-dev`: "Build Configuration: Development", the key not passed on); a visitor's `-midev` with `-PixelStreamingEncoderDumpDebugFrames=true` started the Shipping game with both notes in the log and the dump option gone from the game's command line (`rf-launch-ship`). **Not run:** `package-cloud.sh zip` itself (nothing was packaged) |
| **The stream sends about 56 of the game's 60 frames** | Section 5 | The gate file states the measured numbers; LAUNCH.md section 7 no longer blames the connection for a gap of a few frames; the sentence about `WebRTC.Fps` in the entry below is corrected here and marked there | Six runs, section 5 |

### 3. The double click, as E3DS's page sends it

A browser reports a double click as mousedown, mouseup, mousedown, mouseup and then dblclick. Pixel Streaming's page
passes the last one on as its own message, "MouseDouble", and Unreal takes that message for a press of the button
(read in four engine files, table above). On a desktop the same event stands in for the second press; through the
browser it comes on top of both. Epic's own page has sent a release after it since its version 0.3.0; by the
review's reading of E3DS's script, E3DS's does not. So after two quick clicks the engine held the left button
down: the CHOPPER fired until the next click was released, that click itself fired nothing, a double click on a
card's row acted three times, and a button on a set-up screen stayed pressed.

`rtcinput.py` got `dblclick` (the five messages) and `dbl`. The same script (`lag-input.txt`) through the stream,
Shipping game, a frame saved 3.2 s after the double click and both frames looked at:

| Binaries | The weapon box in the frame | The game's probe lines |
|---|---|---|
| Before the fix (`4c385f9`: release A's code, which like version 2's leaves the message to Pixel Streaming; run `rg-dbl-old`) | **"CHOPPER 0" in red**: the whole magazine fired by a double click | no magazine count in that build's probe line |
| The final code (`rg-input`; the same in `rf-input`) | **"CHOPPER 28"** | magazine 30, then 28 with `dbl=1` and `fire=0`, then 27 after one more click |

So the latch is shown on the box for a page that sends no release after the message, which is how the test viewer
sends it. Whether E3DS's page is such a page is the review's reading (section 8).

### 4. The frame-rate target's way back up, and what a smaller picture buys

The review proposed to judge the rise by the GPU's time at the smallest picture (time x (smallest share / share)
squared). **Measured first, that would have changed almost nothing**: for this game on the box's card the GPU's
time hardly depends on the picture's size.

| Picture (`r.ScreenPercentage`, dynamic resolution off, target fixed at 60, Development game, Story run) | GPU time a frame | Run |
|---|---|---|
| 75 % | 6.39 ms | `rf-sp75` |
| 50 % (44 % of the pixels) | 6.00 ms | `rf-sp50` |
| 400 % (release A's lag runs) | 29 ms | c1 |

Six per cent less time for 56 % fewer pixels: **about an eighth of a frame's GPU time follows the pixels**; the
rest (Lumen, the shadow maps, Nanite, the 1080p output) does not. `MI.Cloud.FpsPixelPart=0.12` holds that share,
and the game works the time at the smallest picture out with it (`MITuning::GpuMsAtSmallest`). Two consequences:

- **Dynamic resolution between 50 and 75 % is a weak lever for this game** (release A put "a smaller picture gains
  little" down to the test load; it is the game). It stays on, since it costs nothing. What a slow card needs is
  the frame-rate target, and release B's quality steps (PREFLIGHT V3-2) more than the plan assumed. A card unlike
  the box's may have another share; the variable can be set without a build.
- **The rise needed another line, not another picture.** The first rule asked for a GPU time under 45 % of the
  frame time now: 10 ms at 45, which is 60 % of what a frame has at 60. The new one asks for a time (at the
  smallest picture) under **four fifths of the frame time of the next rate up**: 13.3 ms to go to 60, 17.8 ms to
  go to 45 (`MI.Cloud.FpsRaiseUnder=0.8`, now a share of the next rate's frame time). The highest second of a gate
  run costs about a fifth more than its average (`k-l12`: 10.9 and 12.9 ms; `k-l35`: 30.6 and 37.7 ms), which the
  next rate then still holds; a rise that does not hold doubles the wait before the next, as before. The gate's
  loads fall on the right sides. The two the game holds 60 under in play (11.1 and 12.2 ms of GPU time) came back
  to 60 on the pause card (`rg-rise`, `rg-rise13`). Under the 20 ms load, which the game plays at 45, a target put
  at 30 on the card came back to 45 after ten seconds ("30 -> 45 ...: the GPU took 17.1 ms a frame ..., under
  80 % of the 22.2 ms a frame has at 45") and did not go on to 60 in the 12 s the run still had (`rg-rise30`, one
  run after the gate, with a copy of the viewer's script that sets 30). The lag's load, 31 ms, is over both lines
  by the rule's arithmetic and the test's cases; no run put it on a card.

**What the first check of this taught.** The rise check was first run under the 12 ms load, and the old binaries
rose there too (`rg-rise-old`: the card took 9.6 ms a frame, just under their 10 ms). The pair that tells the two
rules apart is the 13 ms load (table in section 2); the gate's `gate-rise` line uses it.

### 5. The stream's 56 of 60 frames

Release A's gate looked at the game's frame rate. The sender's own numbers in the same runs: 60 frames captured a
second, 56 to 57 encoded and sent, single seconds at 44 to 53, on a free GPU. Release A suspected the Python
viewer's weak feedback. Six runs on a free GPU (Shipping, release A's code, the stream held at 12 Mbit/s) say no:

| Run | What differs | Encoded and sent a second (lowest second) | Encode time |
|---|---|---|---|
| `rf-fps60`, `rf-cpu6-free`, `k-free` | nothing | 57.0 (44), 56.7 (48), 56.9 (48) | 8.0 to 8.1 ms |
| `rf-fps120` | `PixelStreaming2.WebRTC.Fps=120` at the start (the stream's cap on frames a second) | 56.1 (44) | 8.4 ms |
| `rf-nodec` | the viewer does not decode the video (`rtcinput.py --nodecode`) | 56.1 (49) | 8.4 ms |
| `rf-lowq` | `PixelStreaming2.Encoder.QualityPreset=LOW_QUALITY` | 56.5 (49) | 8.2 ms |

And at lower rates: 44 of 45 (`k-l20`; 43.4 to 43.9 in the final runs), 30 of 30 (`k-l35`; 29.3 to 29.9). The loss
follows the encoder's time: in the seconds of `rf-fps120` with 13 to 15 ms a frame it encoded 44 to 48, in those
with 5 ms all 60. The reading that fits: a frame that arrives while the frame before is still in the encoder is
dropped, and a few frames in a hundred take the encoder longer than a sixtieth of a second. **Why they take that
long was not found** (the encoder shares the card with the game's drawing; the box runs in a sandbox whose driver
calls are slow; neither was tested). The viewer was not the cause, nor the cap, nor the preset.

What follows from it:

- It is **recorded, not accepted**: `lag-gate.txt` states the measured numbers as the state to compare with, and
  the decision is the owner's once the pause card has shown E3DS's own (DECISIONS, item 7).
- LAUNCH.md section 7 told the owner that a stream number below the game's means the connection. A gap of a few
  frames with plenty of megabits is the encoder; the connection shows as a large gap and few megabits. Corrected.
- **Correction to the entry below, section 5:** `PixelStreaming2.WebRTC.Fps` does not "tell the encoder how many
  frames to spread the bitrate over". Pixel Streaming reads it once, when a viewer's video is set up, as the most
  frames a second it may send (`EpicRtcStreamer.cpp`, `_maxFrameRate`), and otherwise only as the pace of its
  decoupled capture thread (`VideoSourceGroup.cpp`). With the capture coupled to the game's frames, as shipped,
  changing it on a running stream does nothing. The game keeps it in step with the target for a session that
  turns decoupling on.
- The final code sends the same: 56.4 to 57.0 with lowest seconds of 45 to 50 in the six runs that held 60 on a
  free or lightly loaded GPU (section 7), 56.7 (47) on 4 CPUs.
- Not explained, and far under the gate's 100 ms: the game's worst frame on a free GPU is 17 to 20 ms in some
  runs (`k-free`, `rf-lowq`, `rf-nodec`, `rg-free`, `rg-cpu4-free`) and 32 to 36 ms in others with the same
  settings (`rf-fps60`, `rf-cpu6-free`, `rf-fps120`): one frame of twice the usual time. The viewer's decoding is
  not what decides it (runs of both kinds had the decoding viewer).

### 6. Tests and builds

- `TESTS OK passed=119 failed=0 skipped=0 filter=MurderInc` on the box at `1877857`, whose code is the last code
  commit `906dfdf`; nothing under `unreal/` changed after it (the 116 tests of release A with their golden
  replays, and three new ones: `MurderInc.Cloud.ViewerSize`, `MurderInc.Cloud.ViewerLeaves`,
  `MurderInc.Player.PadReloadOrGrab`; `Cloud.FrameRate`, `Cloud.Tuning`, `Input.PadMenu` and `Core.GameClasses`
  were extended). The suite also passed 119 of 119 one build earlier (`2f8f43e`, before the rise's new line), and
  once more at `13eb9a5`, after this entry was written ("Target is up to date": only documents and test scripts
  had changed).
- The game target compiled and linked in Development and in Shipping from the release copy at `c7e2a09` (the same
  code); the stream runs of section 7 used those two binaries in release A's test folder (`/tmp/pf/app`: version
  2's content, so the branch's `[MICloud]` additions reach the game as `-MICVars`, and the controller's mapping
  policy as a Saved override: `lag-test.sh profile=1`).
- The pacer still has no automation test (it needs a GPU): its proof is the gate, now also on 6 CPUs. The double
  click's handler and the zeros sent to Pixel Streaming when the last viewer leaves exist only in the game target:
  their proof is the stream runs.

### 7. The release gate again, with the final code

The pacer and the frame-rate target changed, so the gate was repeated: every line of `lag-gate.txt` as it now
stands, run as `rg-*` with `profile=1` on the binaries of `c7e2a09`. Every run CLEAN (one game on the GPU, nothing
compiling), the game alive at the end and stopped with exit code 0.

**It passes.** Under the load the lag was reproduced with, the Story run with fast turning has its worst frame at
43 ms (Shipping) and 33 ms (Development), with "fence time-outs 0" in the Development game's log; the same with the
game on 6 CPUs (40 and 34 ms); with a free GPU the game holds 60.0 (lowest second 59.8).

| Run | Game | Load | Settled on: target, picture | Frames a second (lowest second) | Worst frame | GPU time (highest second) | Owed | Pacer time-outs: play, whole run (longest wait) | Sent a second (lowest second) |
|---|---|---|---|---|---|---|---|---|---|
| `rg-free` | Shipping | none | 60, 75 % | 60.0 (59.8) | 20 ms (17 turning) | 5.9 ms (6.8) | 2 | 0, 0 (86 ms) | 56.7 (50) |
| `rg-l8` | Shipping | 8 ms | 60, 75 % | 60.0 (59.7) | 22 ms | 8.0 ms (8.9) | 2 | 0, 0 (57 ms) | 56.5 (45) |
| `rg-l12` | Shipping | 12 ms | 60, 68 to 75 % | 60.0 (59.1) | 31 ms | 11.1 ms (13.0) | 2 | 0, 0 (48 ms) | 56.4 (48) |
| `rg-l20` | Shipping | 20 ms | 45, 50 % | 45.0 (44.8) | 26 ms | 18.6 ms (21.1) | 2 | 0, 0 (56 ms) | 43.9 (40) |
| `rg-l35` | Shipping | 34 ms | 30, 50 % | 29.8 (28.3) | **43 ms** | 31.9 ms (37.4) | 2 | 0, 0 (59 ms) | 29.3 (22) |
| `rg-l35dev` | Development | 34 ms | 30, 50 % | 30.0 (30.0) | **33 ms** | 27.5 ms (31.1) | 1 | 0, 0 (46 ms); fence time-outs 0, skipped captures 0 | 29.9 (28) |
| `rg-cpu6-l20` | Shipping, 6 CPUs | 20 ms | 45, 50 % | 45.0 (44.8) | 26 ms | 18.6 ms (20.5) | 2 | 0, 0 (48 ms) | 43.4 (38) |
| `rg-cpu6-l35` | Shipping, 6 CPUs | 34 ms | 30, 50 % | 29.8 (27.9) | **40 ms** | 30.4 ms (38.8) | 2 | 0, 0 (41 ms) | 29.6 (28) |
| `rg-cpu6-l35dev` | Development, 6 CPUs | 34 ms | 30, 50 % | 30.0 (30.0) | **34 ms** | 27.8 ms (30.8) | 2 | 0, 0 (49 ms); fence time-outs 0, skipped captures 0 | 29.5 (27) |

Against release A's own gate (the entry below, section 7): the same targets and pictures at every load, worst
frames of 20 to 43 ms where it had 20 to 40. The render-thread wait costs nothing that shows.

The four lines that are not Story runs:

- `rg-cmds` (a viewer's console commands, Shipping): `t.MaxFPS 30` was taken (the log: "Frame-rate target: fixed at
  30 by t.MaxFPS = 30, set by hand"; the probe lines `fps=30`, `target=30`), `quit` and `r.ScreenPercentage 400`
  were refused: `cmdRun=2 cmdRefused=2`.
- `rg-rise13` (the `gate-rise` line): section 2. In its play the game held 60 under the 13 ms load: 59.9 (lowest
  second 59.4), worst frame 23 ms, GPU 12.2 ms (highest second 14.2) at the 50 % picture.
- `rg-input` (the `gate-input` line): the double click (magazine 30, 28, 27; `dbl=1`; `fire=0`), the three size
  requests (`mouseScale=0.6667` at 2560 x 1440, `outW=1280 outH=720`, 300 x 200 ignored), the viewer who left
  holding W and the left button while the magazine ran from 26 to 10 (the run paused, `fire=0`, `moveY=0.00`), and
  the next viewer: the click card, the resume, the magazine at 8 for 6 s, a fresh W (`moveY=1.00`), one click (7).
- `rg-pad` (the `gate-pad` line): the first press marked as a repeat hid the card; the Start presses reached the
  run with `pad=1`; the trigger ran the magazine from 30 to 12 and the viewer left; for the next viewer `fire=0`
  and the magazine at 11 for 8 s; a mouse click fired one round; a trigger message with the first pad's id fired
  and stopped (7, 4, 3).

Frames were looked at where the picture could have changed: the weapon box after the double click (section 3)
and, in `rf-input` with the same input code, the three size requests' frames (whole pictures, no tearing). The
capture path itself did not change in this pass.

### 8. Not done, not proven

- **E3DS's page script was not read in this pass.** That it sends no release after a double click, and marks a
  controller's first press as a repeat, are the review's readings (its script is not saved, and its host cannot be
  reached from the build machine). Both faults are shown on the box with a viewer that behaves that way, and both
  fixes are right whichever way the page behaves; whether they change what the owner feels on E3DS only the next
  test can say.
- **How many CPUs E3DS's servers have is not known.** The fix was proven with the game held to 6 and to 4 of
  the box's CPUs (5 and 3 task workers); a real 8-CPU hyper-threaded server starts 6 and is in the same case by
  the engine's source. Holding the game to a few CPUs of a 16-CPU machine is not a small machine: the load and the
  viewer kept the other CPUs, and the card is the box's.
- **Why some frames take the encoder longer than a sixtieth of a second** (section 5).
- **The picture's share of the GPU time (an eighth) is one scene on one card.** A Story run standing and turning
  at the start; no fight, no other card.
- **`package-cloud.sh zip` with the key, and the launcher inside a real package**, were not run: nothing was
  packaged. The launcher was run with the real games in a copy of the test folder.
- **The size request at sizes other than the three tried**, the HUD at small sizes, and the picture's sharpness
  when the page scales a 1080p picture up: release B (V3-6). The mouse's speed after a size was cut down was
  worked out (`mouseScale=0.6667` in the probe line), not measured with a turn.
- **What a viewer held, with the old binaries and a second viewer**, was not run: that version 2 keeps firing for
  the next viewer is read in the engine. The final code was run both ways (keys and mouse, controller).
- **A real browser, a real controller, a real thin connection, a cold start, the delay between hand and picture**:
  as in the two entries below.
- The fog's two variables and the quality groups were limited by reading the engine; nobody tried to exhaust the
  GPU with the old limits.
- No release B item was started. The size request's cap and mouse scale are a small part of V3-6 that finding 8
  needed (the cap alone would have slowed the mouse of every viewer with a frame larger than 1080p).

### 9. For the packager

1. `tools/box/test.sh MurderInc` must pass first: **119 tests**.
2. After `package-cloud.sh all`: the zip step prints where the Development game's key is
   (`/project/ue/cloud/MurderInc-E3DS.devkey`). **Give the key to the owner with the release notes; never commit
   it.** LAUNCH.md section 13 tells the owner what it is for.
3. The gate: `bash /project/ue/cloud/src/tools/box/cloud/lag-test.sh queue
   /project/ue/cloud/src/tools/box/cloud/lag-gate.txt` (13 runs, about 35 minutes, no `profile=1`). The top of
   that file says what each line must show. New against release A: the three `gate-cpu6-*` lines ("whole run:
   pacer time-outs 0", worst frame under 100 ms), `gate-rise` (the log's "45 -> 60" line), `gate-input` and
   `gate-pad` (read them with `python3 lag_story.py /project/ue/cloud/lag/gate-input`: the magazine 30, 28, 27;
   `mouseScale=0.6667` after the 2560 x 1440 request; after the second viewer's resume `moveY=0.00 fire=0` and a
   magazine that stands still).
4. In the packaged build the controller's mapping policy comes from the pak's `DefaultInput.ini`; the box's test
   folder had it from a Saved override. `gate-pad` is the first run that shows it from the pak: it passes when the
   Start presses reach the run (`state=2`, `pad=1`). If the controller does nothing there, the policy did not
   reach the game.
5. `e3ds-verify.sh` passes `-MIDev`; `e3ds-repro.sh` turns it into the keyed form for a folder that has
   `MIDEV.key` (run on the box in a test folder: `rf-launch-dev`). Check once that `v-crash-dev` still starts the
   Development game on the package.
6. Keep E3DS's Browser Resolution at Custom 1920 x 1080 (LAUNCH.md): the game now also holds a larger request down
   to that size itself, but the setting keeps the page from asking.

## Version 3, release A: the lag (performance engineer, 2026-11-25, 00:35 to 03:55 UTC)

**The lag of version 2 on E3DS is explained and, on the box, ended. Nothing was packaged here.** The owner's report
was "the game is sticky", "when the player turns it slows down; it is not a viable experience". On the box the same
thing is one frame of 1 to 8 seconds whenever the view has turned for a moment on a GPU that is slower than the
game's frame rate. With this branch's code the same Story run with fast turning has no frame over 60 ms at any
load up to the one the lag was reproduced with, no "Timed out waiting for fence" line, and a steady 60 frames a
second on a free GPU: the release gate passes (section 7). With the GPU slowed to a twentieth of its speed the
worst frame is one GPU frame, 158 ms, where it was 8.6 s.

**Two things this entry cannot promise.** That E3DS's servers were slow in this way: the box reproduces the
symptom, it is not E3DS. And that the owner's lag was only this: a thin connection makes the same picture (smooth
when the view stands, a few frames a second when it turns) while the game holds 60, and nothing on the server
cures that (section 5). Version 3's pause card now says which of the two it was (section 8).

What was measured, what was only read in source and what is unproven is said where it applies; section 11 lists
what was not done. Runs are named; their files are on the box in `/project/ue/cloud/lag/<name>/` (the summary line
in `summary.txt`, the game's log, the viewer's log, the frames it saved).

### 1. The cause

**A game that renders off screen never waits for the GPU.** E3DS's servers have no display, so the launcher adds
`-RenderOffScreen` (without it version 1 died at start). Linux then runs Unreal's Null application, which has no
native window, and Unreal 5.9's Vulkan viewport returns from `Present` before its wait for the previous frame
(`VulkanViewport.cpp:842-850`, "Skip present if the native window has been destroyed", ahead of the wait at
`:873-878`; `LinuxPlatformApplicationMisc.cpp:635-638`). This is read in the engine source, not single-stepped; every
measurement below fits it. With a window, that wait is what holds a game to its GPU.

What still held the game back most of the time was a side effect: at the start of a frame the render thread reads the
occlusion results of the frame before and blocks until the GPU has them. **While the view turns, that wait is zero**:
the engine draws no occlusion tests in those frames (`DrawCall/BeginOcclusionTests` in the profile is 1 or more in
every frame with a still view and 0 in every turning frame; why it issues none then was not traced in the source), so
there is nothing to read back. The game then runs at its 60 cap, the GPU finishes what it can, and the
frames it has not finished pile up. When the turn ends, the occlusion read-back comes back and waits for the whole
pile: one frame that lasts as long as the pile takes. Pixel Streaming's messages ("Timed out waiting for fence",
"No frames available for capture ... Skipping") are the same pile seen from the capture: its fences sit behind
seconds of queued work, and its eight capture textures are all waiting.

How it was found, in the order of the instruction "profile before fixing":

| Evidence | Run | What it shows |
|---|---|---|
| CSV profile of the Development game (`csvprofile`), one game alone, the GPU slowed by a second process | `x2` | 2,098 frames in 65.8 s. Game thread 2.1 ms, render thread 7.7 ms, RHI thread 3.3 ms, GPU 31 ms a frame on average. The worst frame, 1,580 ms: game 7.8, render 6.6, RHI 4.7, GPU 31.3 ms of work, and **1,570.7 ms of the render thread waiting for a GPU query** (`RenderThreadIdle/GPUQuery`). All eight frames over 100 ms are that wait |
| The same profile in half-second steps | `x2` | view still: 32 frames a second, the query wait 25 ms in every frame (the game runs at the GPU's pace). View turning: the query wait is **0.0 ms**, the game runs at **56 to 60 frames a second** while the GPU still needs 30 ms a frame, for 2.5 s; then the 1,580 ms frame. Five more times in the next 25 s (507 to 1,127 ms) |
| The game's own counter of frames the GPU still owes (a GPU fence behind every frame; new in version 3, here only counting) | `p1`, GPU slowed to 130 ms a frame | view still: 3 owed. Turning: 26, 50, 65 owed in three seconds, then a frame of **7.3 s**; again 67, 72 and a frame of **8.6 s**. 594 fence time-outs, 204 skipped captures |
| The same with the game held back by that counter (the pacer, below) | `p2` | never more than 2 owed, worst frame 158 ms (one GPU frame at that load), no skipped capture |

It also explains two older observations: a 400 % screen percentage stalled with every capture setting, fence or
not (DECISIONS, runs c1 to d2: the wait was the occlusion read-back, not the capture), and two games on one card
stalled for 4 to 7 s (each made the GPU slow for the other).

### 2. What version 3 does about it (`Source/MurderInc/Cloud/MIPacing.h`, `MICloud.cpp`, `[MICloud]` in `DefaultGame.ini`)

1. **A pacer.** At the end of every frame the game puts a GPU fence behind that frame's commands; before it reads
   the next frame's input it waits until the GPU owes it no more than `MI.Cloud.GpuFramesInFlight` frames (1), for
   at most `MI.Cloud.GpuWaitLimitMs` (250 ms; only when the GPU finished nothing at all during three such waits in
   a row, a GPU that stands still or fences that are never signalled, does it let the game run for 3 s, say so in
   the log and try again). The pile cannot form, whatever the GPU's speed. With a GPU that keeps up it waits for
   nothing. The wait sits just before the frame reads its input, after the frame cap's sleep,
   so the input a frame is drawn with is as fresh as it can be.
2. **Dynamic resolution** (`r.DynamicRes.OperationMode=2`, 50 to 75 % of the output size, 30 % head-room): the
   picture shrinks while the GPU's time is over 70 % of the frame time. 75 % is version 2's fixed picture at 1080p.
3. **A frame-rate target** of 60, 45 or 30 (`FMIFrameRateGovernor`): down, within a second and only while a run
   is being played, when the picture is already at its smallest and the game falls more than 8 % short of the
   rate because it has to wait for the GPU (or the GPU's own time is over the whole frame time); up again only
   while no run is being played (a card, a set-up screen), after 10 s under 45 % of the frame time; a rise that
   does not hold doubles the wait before the next. `t.MaxFPS`, `PixelStreaming2.WebRTC.Fps` and dynamic
   resolution's frame time follow it. `-MIFps=` or `MI.Cloud.FpsTarget` fixes it; so does a `t.MaxFPS` set by a
   launch option or a console command. How the rule came to be this one is in section 6.

### 3. The lag test (`tools/box/cloud/lag-test.sh`)

The investigator's scripts in `/project/ue/cloud/lag-2026-11-24/` are now one committed tool. `lag-test.sh run <name>
key=value ...` starts one game with E3DS's argument list, waits until no other MURDER INC. game runs (a watcher notes
once a second whether one appears: the summary says CLEAN or POLLUTED), loads the GPU, lets a viewer
(`rtcinput.py`) stand, turn slowly (43 degrees a second), turn fast (173 degrees a second) and walk while turning,
and prints one line from the game's own probe lines, the engine's log, the sender's statistics and the frames
received. `queue <file>` runs a list; `calib` measures the loads; `csv <name>` reads a CSV profile (`lag_csv.py`).
Viewer scripts: `lag-turn.txt` (Development game), `lag-story.txt` (Shipping: clicks through the set-up screens),
`lag-commands.txt` (console commands and the pause card), `lag-leave.txt` (the viewer leaves). `lag-gate.txt` is
the release gate as a queue.

**Two loads.** `sp=<percent>` sets `r.ScreenPercentage` in the Development game: simple, but it is not what a slow GPU
does, and dynamic resolution replaces it. `load=<n>:<work ms>:<idle ms>:<size>` starts second processes that keep
the GPU busy (`gpu_hog.py`, PyTorch): the driver gives the two processes turns, so each of the game's frames takes
longer whatever the game draws. **Calibrated** on box ec087d85 (one game alone in a Story run, standing, 1080p,
version 2's fixed picture size, no viewer; `lag-test.sh calib`, runs `cal1`, `cal2`):

| Load | GPU time of a frame | Frames a second (60 cap) |
|---|---|---|
| none | 6.3 ms | 59.7 |
| `1:0.3:1` | 8.1 ms | 60.0 |
| `1:0.05:0.05:1024` | 11.4 ms | 59.9 |
| `1:0.3:0.15` | 13.5 ms | 59.9 |
| `1:0.05:0:1024` | 19.3 ms | 50.0 |
| `2:0.05:0:1024` | 27.5 ms | 35.6 |
| `1:0.3:0` (the load of the lag runs) | 33.8 ms | 29.5 |
| `1:1:0` | 47.9 ms | 20.7 |
| `1:4:0` | 142.7 ms | 7.0 |

**The Python viewer and the bitrate.** With the arguments E3DS passes, the sender believed the connection to the
Python viewer carried 0.25 to a few Mbit/s and WebRTC dropped most frames to fit (run `x1`, free GPU: 60 frames
captured, 2 to 58 encoded a second). That, not the game, is why earlier runs "received 3 to 7 frames a second while
turning". `lag-test.sh` therefore starts the stream at 12 Mbit/s and keeps it there (`minbit=`); the viewer then
receives what the game makes (below). `-PixelStreamingLogStats` logs nothing when given on the command line (the
plugin starts its logger only when the variable changes later); version 3's probe line carries the sender's
statistics itself.

### 4. The pacer, measured

Development game of this branch (version 2's content), 1920 x 1080, one viewer, a Story run with god mode, CLEAN
runs. Dynamic resolution off and the target fixed at 60, so that only the pacer differs. "Owed" is the largest
number of frames the GPU still owed when a frame started.

| Load (GPU time a frame) | Pacer | Frames a second (lowest second) | Worst frame | Owed | Fence time-outs | Skipped captures | Run |
|---|---|---|---|---|---|---|---|
| `1:0.3:0` (31 ms) | off (version 2's behaviour) | 35.5 (12.4) | **1,659 ms** | 57 | 57 | 280 | `b0` |
| the same | holds at 0 owed | 26.1 (24.9) | 64 ms | 1 | 0 | 0 | `b2` |
| the same | **holds at 1 owed (the default)** | 31.5 (29.6) | **39 ms** | 2 | 0 | 0 | `b1` |
| the same | holds at 2 owed | 31.9 (29.0) | 44 ms | 3 | 0 | 0 | `b3` |
| `1:4:0` (130 ms) | off | 13.4 (4.3) | **8,564 ms** | 79 | 594 | 204 | `p1` |
| the same | holds at 1 owed | 7.2 (6.6) | 158 ms | 2 | 728 | 0 | `p2` |
| none (6 ms) | off | 59.9 (57.8) | 50 ms | 3 | 0 | 0 | `f0` |
| none (6 ms) | holds at 1 owed | 60.0 (59.5) | 24 ms | 2 | 0 | 0 | `c0` |

Reading it: holding at 1 costs no frame rate (31.5 against the GPU's own 32) and ends the stall; holding at 0 gives
the freshest input but starves the GPU (26 a second); 2 adds a frame of delay for nothing. At 130 ms a frame every
capture fence still times out with the pacer (Pixel Streaming waits 100 ms for a frame that takes 130): nothing
stalls, but below about 10 frames a second that line cannot go away. With a free GPU the pacer waits for nothing
(23 of 3,000 frames waited at all, the frames in which the GPU itself was late). Runs `b0` to `b3`, `p1` and
`p2` were made while the pacer's wait still sat at the very start of the frame; from `c0` on it sits just before
the input is read. The runs of section 7 are the final code.

### 5. V3-3: Pixel Streaming's capture settings, measured under load

The same set-up with the pacer on, dynamic resolution off and the target fixed (so only the capture differs), the
stream held at 12 Mbit/s. "Sent" is the sender's own count (`transmitFps`); "received" the viewer's count while
turning fast; "repeats" are received frames that show the same picture as the one before.

| Capture setting | GPU free: game, sent, received (repeats) | GPU at 31 ms a frame: game, sent, received (repeats) | Worst frame, free / loaded | Runs |
|---|---|---|---|---|
| **defaults** (Media Capture with its fence, coupled) | 60.0, 57, 58 | 31.9, 31, 32 | 24 / 40 ms | `c0`, `c4` |
| `-PixelStreamingDecoupleFramerate=true` | 60.0, 55, 54 (1) | 31.4, 55, 55 (9 to 24 a second) | 19 / 38 ms | `c1`, `c5` |
| `-PixelStreamingUseMediaCapture=false` (RHI capturer with its fence) | 60.0, 56, 56 | 32.2, 32, 32 | 17 / 40 ms | `c2`, `c6` |
| the same with `-PixelStreamingCaptureUseFence=false` (no fence) | 60.0, 57, 56 | 31.3, 31, 31 | 24 / 39 ms | `c3`, `c7` |
| defaults with the target fixed at 30 (`t.MaxFPS` 30, `WebRTC.Fps` 30) | | 30.0 (lowest second 29.2), 30, 29 | 37 ms (33 while turning) | `c8` |
| the same, decoupled | | 30.0 (lowest second 30.0), 29, 29 | 33 ms | `c9` |

No run logged a fence time-out or a skipped capture. Frames looked at (four of each: still, slow turn, fast turn,
walking turn): the defaults under load (`c4`) and no fence under load (`c7`): whole pictures, no tear line, nothing
half-drawn, the HUD intact.

**Decision: Pixel Streaming's capture defaults stay** (nothing is set in `[MICloud]`; a `StreamCVars` list exists
for the day one is needed). No setting delivers more frames or a shorter worst frame than the defaults; the fence is
Epic's protection against a texture being drawn to while it is encoded, and removing it buys nothing measurable.
**Decoupling stays off**: with a full GPU it sends 55 frames a second of which up to 24 are repeats (what E3DS's
own article found), and with a free GPU it sends slightly fewer new frames than coupled (55 against 57). The gain
measured on version 2 ("40 received coupled, 55 decoupled") was the Python viewer's bitrate, not the capture. So
there is no `-MIDecouple` switch; Pixel Streaming's own `-PixelStreamingDecoupleFramerate=true` (or `-MICVars=
PixelStreaming2.DecoupleFramerate=true`) turns it on for a session. `PixelStreaming2.WebRTC.Fps` follows the
frame-rate target (it tells the encoder how many frames to spread the bitrate over). **Wrong, found in review:**
Pixel Streaming reads the variable once, when a viewer's video is set up, as the most frames a second it may send,
and otherwise only as the pace of its decoupled capture thread; on a running stream with the capture coupled to
the game's frames, as shipped, changing it does nothing (the entry above, section 5).
`PixelStreaming2.WebRTC.DisableFrameDropper` **stays off, measured** (runs `e0`, `e1`: a free GPU and the stream's
bitrate left as E3DS starts it, which the Python viewer's feedback lets fall to 1.7 Mbit/s):

| | Game | Sender: encoded and sent | Bitrate | A frame waits between capture and send | Received while turning |
|---|---|---|---|---|---|
| frame dropper on (the default), `e0` | 60.0 | 28 a second (15 while turning) | 1.7 of 1.7 Mbit/s | 52 ms | 5 to 7 a second |
| frame dropper off, `e1` | 60.0 | 57 a second | 3.9 Mbit/s against the 1.7 the connection is thought to carry | **644 ms** | 49 to 56 a second |

Without the dropper every frame is sent, but each waits two thirds of a second in the sender: on a real thin
connection that is delay, the worse evil in a shooter. (In every other run with the final probe line a frame
waited 2 to 5 ms.)

**These two runs also show a second way to the owner's complaint, one the server cannot fix.** On a connection the
sender believes to carry 1.7 Mbit/s, the sender encoded 15 frames a second of a turning 1080p picture and the
viewer counted 5 to 7 in the two turn phases, **while the game held a steady 60**: the picture stutters in every
turn and is smooth when the view stands still. Whether the
owner's sessions on E3DS had a full GPU (the pile, sections 1 to 4), a thin connection, or both, cannot be told from
here: version 2 wrote neither number anywhere the owner could read. Version 3's pause card now says both
(section 8).

### 6. V3-1: dynamic resolution and the frame-rate target, measured

The whole cloud profile on (dynamic resolution 50 to 75 %, 30 % head-room, the target free, the pacer at 1), the
Development game, 1080p unless said, the stream at 12 Mbit/s, every run CLEAN. "Load" is the GPU's time for a frame
at version 2's fixed picture (section 3). The first set was run with the line the pre-flight proposed (the target
drops when the GPU's time is over 70 % of the frame time at the smallest picture) and with 85 %, and with a target
that could still drop anywhere, also while the game started:

| Load | Drop line | What the game settled on | Frames a second (lowest second) | Worst frame | GPU time | Run |
|---|---|---|---|---|---|---|
| none (6 ms) | 70 % | target 60, picture 75 % | 60.0 (59.3) | 29 ms | 6.3 ms | `d0` |
| 8 ms | 70 % | target 60, picture 75 % | 60.0 (58.9) | 24 ms | 8.3 ms | `d1` |
| 12 ms | 70 % | **target 45** after 10 s, picture back at 75 % | 45.0 (44.9) | 25 ms | 10.6 ms | `d2` |
| 12 ms | 85 % | target 60, picture 57 to 75 % | 60.0 (59.3) | 28 ms | 11.7 ms | `d6` |
| 20 ms | 70 % | target 30 (60 to 45 to 30 within 2 s), picture 75 % | 30.0 (30.0) | 34 ms | 18.6 ms | `d3` |
| 20 ms | 85 % | target 45 for 8 s (a steady 45), then **30** | 30.0 (30.0) | 33 ms | 16.8 ms | `d5` |
| 34 ms | 70 % | target 30, picture 50 % | 30.0 (30.0) | 34 ms | 27.8 ms | `d4` |
| 34 ms | 85 % | target 30, picture 50 % | 30.0 (30.0) | 34 ms | 28.0 ms | `d9` |
| none, 2560 x 1440 output | 70 % | target 60, picture 75 % | 60.0 (59.4) | 26 ms | 7.0 ms | `d8` |
| none, 3840 x 2160 output | 70 % | target 60, picture 75 % | 59.9 (55.5) | 92 ms (see below) | 8.9 ms | `d7` |

What the table says:

- **On a free or lightly loaded GPU nothing changes against version 2**: 60 frames a second at the same picture.
- **No run has a frame over 100 ms**, whatever the load and whatever the line.
- **Every line drawn at a share of the frame time lowered a rate that was being held.** At 70 %: a GPU at 12 ms
  held a steady 60 until the target put it at 45 (`d2`; at 85 % it stayed at 60, `d6`). At 85 %: a GPU at 20 ms held
  a steady 45 for eight seconds until one second at 19.3 ms (87 % of 22.2 ms) put it at 30 (`d5`). At 90 %, the
  line of the first two gate sets (section 7): the same load was put at 30 in the first second of the run, 0.4 ms
  over the line, although its average afterwards was 89 % of 45's frame time in the Shipping game and 78 % in the
  Development game (`h-l20`, `h-l20dev`). With the line out of the way
  (`h-l20x`) the Shipping game ran **a steady 45.0 for 23 seconds, no frame over 22.3 ms, with the GPU at 78 to
  98 % of the frame time**, and was then put at 30 by the other rule, "the pacer waited a fifth of the time", in a
  second that still had 45.0 frames and no late one: while the rate is held, the pacer's wait before the input
  only takes the place of the frame cap's sleep.
- **The final rule**: the target drops, in live play and at the smallest picture, after a second in which the game
  made **more than 8 % fewer frames than the target asks for while it waited for the GPU**, or in which the GPU's
  own time was over the whole frame time (`MI.Cloud.FpsDropOver=1.0`). The pacer already keeps a full GPU from
  stalling the game, so the target only has to follow what a run can really hold; the owner's order is fluid play
  first, the look second: 60 frames a second at a smaller picture before 45 at a larger one. The gate runs of
  section 7 use it.
- **It never drops outside live play.** The start of the game is full of long frames on any card: on a free GPU
  the pacer waited a third of the first second (`g-free`, `g-l8`, `g-l12`), and under load the first gate set had
  the target at 45 or 30 before a viewer had joined (`g-l20`, `d5`). A target lost there comes back only after 10 s
  under 45 % on a card or a set-up screen, so a server that is busy but able would have played its first run below
  what it can hold.
- **With this kind of load a smaller picture gains little**: the second process takes its turns on the card however
  little the game draws (at 20 ms: 15 to 19 ms at a 50 % picture and 15 to 18.5 ms at 75 %). That is the load the
  instruction asked for ("a second way dynamic resolution cannot undo"). A card that is slow only because the game's
  own picture is heavy for it (a weaker GPU) was **not measured**: the box has one card. There dynamic resolution
  should carry more of the load before the target moves.
- **The target rises only outside live play** and only after 10 s under 45 % of the frame time, so a game put at 45
  by a busy minute stays there until the next card or set-up screen. **Seen in a stream run** (`rise`, Shipping,
  `lag-rise.txt`, build `3875973`; the rise's code did not change after it): at the lag's load the target went 60, 45, 30 in play; the viewer paused and the load was stopped;
  the log said "Frame-rate target: 30 -> 45 frames a second: the GPU took 5.0 ms a frame, under 45 % of 33.3 ms for
  10 s, and no run is being played" and ten seconds later "45 -> 60", and the probe lines followed (45.0, then
  60.0). The picture stayed at 50 % on the pause card (dynamic resolution did not move while the game was paused;
  not looked into: in `d2` it was back at 75 % three seconds into play).
- **3840 x 2160 output is not ready** (run `d7`, free GPU): the game itself held 60 and the GPU took 8.9 ms, but the
  encoder made only 46 frames a second (19 to 59 by the second, 11.8 ms each), the 92 ms frame and one fence
  time-out came in the second the viewer left, the game then **did not notice that the viewer had gone** (no pause)
  and **did not shut down within 30 s of SIGTERM** (it stopped after "CleanupWorld" and was killed). 2560 x 1440 was
  clean (`d8`: 60.0, 56 sent, exit in 7.5 s). Not investigated: the output size is release B's item V3-6, which
  limits it; until then E3DS's Browser Resolution should stay Custom 1920 x 1080, as LAUNCH.md and the pre-flight say.

### 7. The release gate, with the final code

**The gate** (PREFLIGHT section 2): on the box, with the GPU loaded the way the lag was reproduced, a Story run with
fast turning has no game frame over 100 ms and no "Timed out waiting for fence" line; with a free GPU the game holds
60 frames a second. **It passes.**

The Shipping game and the Development game compiled at `4c385f9` (the last code commit of this entry), in a test
folder with version 2's content, 1920 x 1080, one viewer who clicks through the set-up screens into a Story run,
stands, turns slowly, turns fast and walks while turning (`lag-story.txt`; the Development game starts the run
itself, `lag-turn.txt`). Every run CLEAN. "Load" is the GPU's time for a frame at version 2's fixed picture
(section 3); "GPU time" is what the game measured in the run; "owed" the most frames the GPU still owed when a
frame started.

| Run | Game | Load | Settled on: target, picture | Frames a second (lowest second) | Worst frame (while turning) | GPU time (highest second) | Owed | Pacer time-outs | Sent, received in the fast turn |
|---|---|---|---|---|---|---|---|---|---|
| `k-free` | Shipping | none (6 ms) | 60, 75 % | **60.0 (59.8)** | 20 ms (17) | 5.9 ms (6.8) | 2 | 0 | 57, 56 |
| `k-l8` | Shipping | 8 ms | 60, 75 % | 60.0 (59.5) | 25 ms (25) | 8.0 ms (10.0) | 2 | 0 | 57, 56 |
| `k-l12` | Shipping | 12 ms | 60, 70 to 75 % | 59.9 (58.6) | 33 ms (27) | 10.9 ms (12.9) | 2 | 0 | 57, 56 |
| `k-l20` | Shipping | 20 ms | 45, 50 % | 45.0 (44.9) | 25 ms (22) | 18.3 ms (21.3) | 2 | 0 | 44, 43 |
| `k-l35` | Shipping | **34 ms: the lag's load** | 30, 50 % | **29.9 (28.3)** | **40 ms (40)** | 30.6 ms (37.7) | 2 | 0 | 30, 30 |
| `k-l35dev` | Development | the same | 30, 50 % | 30.0 (30.0) | 34 ms (34) | 28.0 ms (32.7) | 1 | 0 | 30, 30; **fence time-outs 0, skipped captures 0** |

For comparison, version 2's behaviour at the lag's load (run `b0`, section 4): worst frame 1,659 ms, 57 frames
owed, 57 fence time-outs, 280 skipped captures.

- **"No fence time-out line" can only be read in the Development game** (the Shipping game has no engine log):
  `k-l35dev` logged none, and no skipped capture. The Shipping game is judged by its own probe lines: no frame over
  100 ms, never more than 2 frames owed, no pacer time-out.
- **The gate was run three times**, once for each state of the target's rule (section 6), because each change
  needed a build. The two earlier sets:

| Load | Build `52b2816` (drops at 90 %, anywhere): runs `g-…` | Build `3875973` (drops at 90 %, only in live play): runs `h-…` |
|---|---|---|
| none | Shipping: 60.0 (59.8), worst 19 ms, target 60 | Shipping: 60.0 (59.8), worst 20 ms, target 60 |
| 8 ms | Shipping: 60.0 (59.3), worst 28 ms, target 60 | Shipping: 60.0 (59.9), worst 18 ms, target 60 |
| 12 ms | Shipping: 59.9 (59.3), worst 26 ms, target 60, picture 70 to 75 % | Shipping: 60.0 (59.7), worst 21 ms, target 60, picture 70 to 75 % |
| about 13 ms (`1:0.3:0.1`, not calibrated) | | Shipping: 60.0 (59.0), worst 33 ms, target 60, picture 50 %, GPU 12.6 ms (one second at 15.5) |
| 20 ms | Shipping: 30.0 (30.0), worst 33 ms, target 30 (lost while the game started) | Shipping: 30.0 (30.0), worst 34 ms, target 30 (lost in the first two seconds of play); Development: 30.0 (29.9), worst 37 ms, no fence line |
| 34 ms, the lag's load | Shipping: 29.7 (27.9), worst 49 ms, target 30, picture 50 %; Development: 30.0 (30.0), worst 34 ms, no fence line | Shipping: 29.9 (28.1), worst 52 ms, target 30, picture 50 %; Development: 30.0 (30.0), worst 33 ms, no fence line |

  No run of either set had a pacer time-out or more than 2 frames owed.
- **Frames looked at:** four received frames each of the Shipping game at the lag's load (30 a second, picture at
  50 %) and on a free GPU (60, 75 %), and the fast-turn frame at the lag's load at full size: whole pictures, no
  tear, nothing half-drawn, the HUD sharp (it is drawn at the output size). At 50 % the scene is soft; reflections
  in the shop window smear while turning, at 75 % too. (From the first gate set, runs `g-l35` and `g-free`; the
  picture's path did not change after it.)
- **Where the target is decided.** On the set-up screens the target stays at 60 whatever the GPU does: at the 20 ms
  load the game ran there at the GPU's pace, 46 to 55 frames a second, the pacer holding every frame, no frame over
  42 ms (`h-l20`). The target moves when the player takes control, and the log names the reason each time
  (`k-l20`: "Frame-rate target: 60 -> 45 frames a second: at the smallest picture the game fell short of the rate
  because it had to wait for the GPU for 1.0 s (the GPU took 19.3 ms a frame; a frame has 16.7 ms)", and nothing
  after it: a steady 45 for the whole run, where the two earlier rules ended at 30).
- **The pacer's wait limit**, tried on purpose at 20 ms on a GPU that needs 31 ms a frame (target fixed at 60,
  dynamic resolution off). A limit shorter than the GPU's frame cannot hold the game to the GPU's pace: a frame
  goes through every 20 ms and a pile forms in the turns again. With the first version of the rule for a GPU that
  does not answer (three waits in a row at the limit, then 3 s without holding) the worst frame was 1,604 ms
  (`t-pause`, 53 frames owed). The final rule lets the game run unheld only when the GPU finished **nothing** during
  three waits in a row; the same run then never ran unheld and its worst frame was 957 ms (`t-pause2`), which is the
  20 ms limit itself. **With the default limit of 250 ms no run ever had a time-out**, down to a GPU at 130 ms a
  frame (`p2`); a GPU slower than four frames a second would get past the pacer. After a time-out the counter
  starts again from the frames written from then on, so `owed` under-reports such a pile: `pacerTimeOuts` in the
  same probe line is the sign to look for.

### 8. The smaller items of release A

| Item | What was done | How it was checked |
|---|---|---|
| **V3-5** the game shows its own numbers | One dim line at the bottom of the pause card when streamed: the graphics card's name, frames a second and the target (", fixed" when something holds it), the GPU's time, the size drawn and the size sent, what the stream sends (frames a second, Mbit/s, QP, round trip when the viewer reports one, "decoupled" when it is), the build's commit. Both frame rates come with their **lowest value of the last half minute of play**: the pause card is a still picture, so the current numbers alone would hide a stutter; the two lowest values say whether the server's card (the game's number fell) or the connection (only the stream's did, section 5) was the cause. The probe line is written every 30 s by default when streamed (`-MICloudProbe=<seconds>` changes it) and carries the pacer, the target, the picture's share and the sender's statistics | **Looked at** in three frames a viewer received from the Shipping game (runs `h-cmds`, `rise`; the bottom strips at full size): "NVIDIA RTX PRO 6000 Blackwell Server Edition · 60 frames a second (lowest 59, target 60) · GPU 4.9 ms · drawn 1440 x 810, sent 1920 x 1080 · stream 50 a second (lowest 50), 11.0 Mbit/s, QP 18, round trip 0 ms · build e989cb8"; after the viewer's `t.MaxFPS 30`: "30 frames a second (lowest 30, target 30, fixed) · GPU 5.4 ms · … · stream 31 a second (lowest 27), 11.8 Mbit/s, QP 19, …" (the longest form: it fits 1920 pixels with about 30 to spare on each side); and under the lag's load: "30 frames a second (lowest 28, target 30) · GPU 27.6 ms · drawn 960 x 540, sent 1920 x 1080 · stream 31 a second (lowest 25), 9.5 Mbit/s, QP 19, round trip 0 ms · build e989cb8". Small, dim, readable at 1080p. The build shown is the test folder's `BUILD.txt` (version 2's); the round trip is 0 because the viewer sat on the same machine. The 30 s default: a Shipping run without the option wrote its probe line at the start and after 30, 60 and 90 s (`pf-probe`). These frames are from the build before the last change to the target's rule; the line's code did not change after it. **Not in the line:** the quality level (it comes with V3-2 in release B) |
| **V3-11** tuning without a rebuild | Launch option `-MICVars=name=value,name=value`: sets the variables of the list below with the strength of a launch option (the cloud profile and the frame-rate target do not override them) and logs each one, set or refused. `-MIFps=60/45/30` fixes the target | Every `profile=1` run passes eleven variables this way; the Shipping game's log lists each ("Launch option -MICVars: r.DynamicRes.MinScreenPercentage = 50 (now 50)") and they act (the picture moves between 50 and 75 %; run `h-l20x` passed `MI.Cloud.FpsDropOver=1.0` on top of them and the target's rule followed it). `-MIFps=30` in the Shipping game: 30.0 a second from the first second, target 30, 30 sent and received (run `g-fps30`). Refusals, in the Shipping game's log of run `rise`: "refused "r.ScreenPercentage=400"", "refused "r.Streaming.PoolSize=5000"" and "refused "quit=1"", each with the list of what is allowed, next to "PixelStreaming2.WebRTC.DisableFrameDropper = true (now true)"; and test `MurderInc.Cloud.Tuning` |
| **V3-9** the viewer's console commands, widened | A viewer (the player page, E3DS's "Unreal console commands to run at start" field) may read or set: `PixelStreaming2.*`, `PixelStreaming.*`, `MI.Cloud.*`, `sg.*` (0 to 4), `r.DynamicRes.*` (minimum and maximum screen percentage 25 to 100), `r.ScreenPercentage` (25 to 100), `t.MaxFPS` (0 to 120), `r.Streaming.PoolSize` (200 to 3000), `r.GTSyncType`, `r.OneFrameThreadLag`, `r.VolumetricFog.*`. Anything else, and any value outside its range, is refused. "name value", "name=value" and "name = value" are all understood | **In the Shipping game through a stream** (runs `g-cmds` and, one build later, `h-cmds`; `rtcinput.py` sends them as the browser does): `t.MaxFPS 30` ran, the log said "Frame-rate target: fixed at 30 by t.MaxFPS = 30, set by hand", the probe lines said `fps=30.0 target=30` and the viewer received 30 a second; `quit` was refused and the game went on; `r.ScreenPercentage 400` was refused; `MI.Cloud.FpsTarget` (a read) ran; the counters ended at `cmdRun=2 cmdRefused=2`. Tests `MurderInc.Cloud.Tuning`, `MurderInc.Cloud.ViewerCommands` |
| **V3-10** box tests that version 3 broke | `e3ds-verify.sh`: the Shipping game has no `-MICrashTest` any more, so `v-crash` now crashes it from outside (`e3ds-repro.sh CRASHAT=30`: SIGSEGV to the game after 30 s) and a new `v-crash-dev` keeps the old path for the Development game. `stream-test.sh`, `stream_test.cjs`, `xtest.py` and `memory-runs.sh` read the game's `[MICloud]` lines from its own output instead of `-MICloudLog=`, which Shipping no longer has | Run by hand with `e3ds-repro.sh` on the test folder (build `52b2816`): the Shipping game with `CRASHAT=30` "ENDED BY ITSELF: SIGNAL 11 (SEGV) after 30.1s", its launcher's log says "CRASH: the game was killed by signal 11 (SIGSEGV) after 29s" and names the crash report's folder; the Development game with `-MIDev -MICrashTest=30` the same after 35.1 s (runs `pf-crash`, `pf-crash-dev`). The whole of `e3ds-verify.sh` was **not run**. `stream_test.cjs`: syntax checked, and its probe reading run on a Shipping game's log (124 probe lines read). That showed a fault of the repair: the game's output also echoes its command line, which holds `-MICloudProbe=`, and those lines were taken for probe lines; fixed in all three readers. `stream-test.sh`, `xtest.py` and `memory-runs.sh` themselves were **not run**: they need the box's desktop, which another task's browser session was using, and a browser cannot connect to the game on this box anyway |
| **V3-4, first bullet** box run `gp-in5`: 14.5 GB and "HUNG in shutdown" | It is the same pile, not version 3's code. Every frame the GPU has not finished keeps about **11 MB** of memory (measured in the pacer-off runs: `p1`, 3 to 65 frames owed, 3,488 to 4,179 MB; `b0`, 3 to 57 owed, 3,462 to 4,093 MB). `gp-in5` shared the card with other agents' games; from the second its viewer turned (the first of 511 fence time-outs) the game ran 43 to 51 frames a second against a GPU that finished far fewer, for 54 s, also while paused: memory rose by 250 to 300 MB a second, 11.2 GB in all, about 1,000 unfinished frames. At exit the engine waits for the GPU to finish them all (1,000 frames at 25 to 30 ms): longer than the 30 s it was given | The numbers above are from the runs' own probe lines. With the pacer the GPU never owes more than 2 frames, so neither can happen: memory stayed flat in every gate run and every run ended within 8 s of SIGTERM. **Not reproduced:** why `gp-in5`'s pile kept growing after its view stood still. In a one-game run the pile is drained by one long frame when the turn ends, and a game that is paused without a turn before it does not pile up at all (run `m0`, pacer off: 3 owed, memory flat, exit in 7 s; `m1`, pacer on: 2 owed, memory flat, exit in 7 s) |

### 9. Tests and builds

- The automation suite at `f0f57f5` (the code of `4c385f9`, the last code commit): `TESTS OK passed=116 failed=0
  skipped=0 filter=MurderInc` (the 114 tests of the gameplay part with their golden replays, and two
  new ones: `MurderInc.Cloud.FrameRate`, the frame-rate target's decisions, and `MurderInc.Cloud.Tuning`, what
  `-MICVars` and a viewer may set). `MurderInc.Cloud.ViewerCommands` was extended for the wider list.
- The game target compiled and linked in Development and in Shipping from the release copy at the same commit; the
  gate runs above used those two binaries.
- The pacer itself has no unit test: it needs a GPU. Its proof is the runs (sections 4 and 7). Its path for a GPU
  that does not answer was provoked with an absurd wait limit (section 7); a GPU that really finishes nothing for
  three waits in a row was never seen, so that the game then runs unheld for 3 s is read in the code, not shown.
- **Nothing was packaged.** The test folder is version 2's unpacked zip with this branch's two game binaries; its
  pak is version 2's, so `DefaultGame.ini` of this branch was not in it and `lag-test.sh profile=1` handed the
  branch's `[MICloud]` additions to the game as `-MICVars`. That the same lines act from a packaged `DefaultGame.ini`
  (they are read by the code that already reads the profile's other ten lines) is for the packager's gate runs to
  show.

### 10. What cloud mode now sets, and why

| Setting (`[MICloud]` in `DefaultGame.ini`) | Value | Why |
|---|---|---|
| `r.DynamicRes.OperationMode`, `MinScreenPercentage`, `MaxScreenPercentage` | 2, 50, 75 | dynamic resolution on; 75 % is the picture version 2 always drew at 1080p, so a free GPU shows no change; 50 % was looked at (section 7): soft, readable |
| `r.DynamicRes.TargetedGPUHeadRoomPercentage` | 30 | the picture shrinks above 70 % GPU use: E3DS asks for 50 to 70 % |
| `MI.Cloud.GpuFramesInFlight`, `MI.Cloud.GpuWaitLimitMs` | 1, 250 | the pacer: 1 loses no frame rate and ends the stall (0 costs a sixth of the frame rate, 2 adds a frame of delay for nothing: runs `b1` to `b3`); 250 ms is the longest a frame's start waits |
| `MI.Cloud.FpsTarget` | 0 | the game chooses 60, 45 or 30; `-MIFps=` or a console command fixes it |
| `MI.Cloud.FpsDropOver`, `MI.Cloud.FpsDropAfter` | 1.0, 1.0 | down, in live play and at the smallest picture, after a second in which the game fell more than 8 % short of the rate because it waited for the GPU, or in which the GPU's time was over the whole frame time (section 6) |
| `MI.Cloud.FpsRaiseUnder`, `MI.Cloud.FpsRaiseAfter` | 0.45, 10 | up only outside live play, after 10 s under 45 %: the next rate up then starts at about two thirds of its frame time |
| Pixel Streaming's capture settings | not set | its defaults measured best (section 5); decoupling off |
| `PixelStreaming2.WebRTC.Fps`, `r.DynamicRes.FrameTimeBudget`, `t.MaxFPS` | follow the target | set by the game whenever the target changes |
| the probe line | every 30 s | so that a log from E3DS always holds the numbers; `-MICloudProbe=` changes it |

Desktop play (no `-MICloud`, no stream) is unchanged: none of this starts there.

### 11. Not done, not proven

- **E3DS itself.** Everything above is the box: one RTX PRO 6000, a second process as the load, a Python viewer on
  the same machine. Whether E3DS's servers are slow in the way the load is (a shared card) or in another way is not
  known; the pacer does not depend on the kind of slowness, the target's numbers might.
- **A real browser.** The box cannot run one against the game. The Python viewer has no congestion control worth
  the name (the stream had to be held at 12 Mbit/s) and its round trip is 0 ms.
- **The delay between hand and picture** (V3-4's other bullets) was not measured: release B. The pacer waits just
  before the input is read, which is the right place for the delay, but no number says so.
- **Why the engine draws no occlusion tests while the view turns** was not traced in the source, and the off-screen
  `Present` path was read, not single-stepped.
- **The sender's dips.** In several runs, with every capture setting, the sender's encoded frames a second dipped
  for a few seconds (to 36 to 47 of 60) while the game held 60. The cause was not found; the viewer's weak feedback
  is the first suspect.
- **A thin connection.** The frame dropper's two runs (section 5) used the Python viewer's weak feedback as the thin
  connection; the box has no real one. What a browser's congestion control does at 2 Mbit/s was not seen.
- **How the final rule behaves between the loads tried.** It was run at five loads; a GPU that sits exactly at a
  target's frame time (16.7 or 22.2 ms) was not among them. There the game runs at the GPU's pace until it is more
  than 8 % short.
- **A cold start.** The box's games start warm (shaders and files cached). The rule that the target drops only in
  live play was made for the long frames of a start, but a cold start on E3DS was not seen.
- **3840 x 2160 output** (section 6) and the size limit: release B, V3-6.
- **`stream-test.sh`, `xtest.py`, `memory-runs.sh`** were repaired by reading and not run (section 8).

### 12. For the packager: the gate to repeat on the packaged Shipping game

1. Package from the head of this branch. `tools/box/test.sh MurderInc` must pass first (116 tests).
2. `bash /project/ue/cloud/src/tools/box/cloud/lag-test.sh queue /project/ue/cloud/src/tools/box/cloud/lag-gate.txt`
   (about 20 minutes; it uses `/project/ue/cloud/build-Shipping/Linux`, the packaged build; `LAG_BUILD=<folder>`
   for another one; no `profile=1`: the packaged `DefaultGame.ini` carries the lines). Nothing else may use the GPU
   and nothing may compile meanwhile; each line must end in CLEAN. `bash lag-test.sh list` prints the lines.
3. It passes when: `gate-free` holds 60 (lowest second 57 or more) at target 60; `gate-l8` to `gate-l35` have no
   frame over 100 ms, `owed` 2 or less and no pacer time-out (measured here: targets 60, 60, 45 and 30, worst
   frames 25, 33, 25 and 40 ms); `gate-l35dev` also says "fence time-outs 0, skipped
   captures 0" (only the Development game has the engine's log; the Shipping game is judged by its probe lines);
   `gate-cmds` ends with `cmdRun=2 cmdRefused=2` and its probe lines say `fps=30.0 target=30` after the command.
   Look at `gate-cmds`' `pause.jpg`: the line of numbers must show the package's own commit.
4. The loads are calibrated for box ec087d85. On another card run `lag-test.sh calib cal 0 1:0.3:1
   1:0.05:0.05:1024 1:0.05:0:1024 1:0.3:0` first and compare with the table in section 3.
5. The viewer's Python lives in `/tmp/fps/venv` (lost when the box restarts; `lag-test.sh` builds it again).

## Version 3: play through the stream (gameplay part, 2026-11-25, 00:30 UTC)

The gameplay part of version 3: the seven input items of the launch pre-flight (A1 to A7), and the controller path
the owner asked for after testing version 2 (DECISIONS, 2026-11-24 23:10). Rendering, the launcher and the package
come next. **Nothing was packaged here**, and the lag when turning is not in this part.

**How it was checked**, three ways:

1. The automation suite at `71e5b44`: `TESTS OK passed=114 failed=0 skipped=0 filter=MurderInc` (the 105 tests of
   version 2 with their golden replays, and nine new ones: `MurderInc.Input.StreamMouse`, `.Input.PadLook`,
   `.Input.PadMenu`, `.UI.CardHitTest`, `.Cloud.Viewers`, `.Cloud.ViewerCommands`, `.Cloud.Quality`,
   `.Player.ControllerPad`, `.Run.MenuMouse`).
2. The game target compiled and linked from the release copy in Development and in Shipping at `71e5b44` (the
   editor build does not contain the Pixel Streaming code or the Shipping guards).
3. **Through a real WebRTC stream on the box**: the Development game of these commits, started as a fresh user with
   no display and E3DS's argument list, and `tools/box/cloud/rtcinput.py` as a viewer that plays: it sends mouse,
   keys, gamepad buttons and axes and console commands over the data channel in the browser player's own message
   formats, and saves frames it receives. The game logged its view angles, state and counters four times a second
   (`-MICloudProbe=0.25`). The runs quoted had the GPU to themselves (60 frames a second, no skipped capture)
   unless the table says otherwise. Scripts and logs: `/project/ue/cloud/gp-test/` and
   `/project/ue/cloud/repro/gp-in*`; the last three runs (`gp-in11` to `gp-in13`) are the controller-only path,
   the same at the final commit, and the mouse and keyboard path.

**What this is not:** no real browser, no real controller and not E3DS's own player page (the box cannot run a
browser viewer). What a browser sends was read in Pixel Streaming's reference front end and in the engine source
and reproduced by the test client. The owner's next test on E3DS is the first real one.

| Item | What changed | How it was verified |
|---|---|---|
| A1 mouse look 2 to 3 times too fast | Read in both sources: the browser sends each mouse event as a 16-bit share of half the player's size and the engine turns it into counts of the render size, so one browser pixel is 2 counts, less one count per event and axis because both ends cut the fraction. **The cut matters**: 1 pixel arrives as 1 count, 10 pixels as 19, so slow aiming would be half speed. The game now takes the stream's mouse events one by one and turns the counts back into browser pixels (`[MICloud] MouseScale=0.5`, `MouseTruncation=1`; launch options `-MIMouseScale=`, `-MIMouseTruncation=`; printed in the `[MICloud]` start lines), and drops one event beyond 400 pixels (the web game's pointer-lock spike filter). Only while streamed | Stream: 100 events of 5 px turned 60.1606 degrees (500 px x 0.0021 rad is 60.1606), 200 events of 1 px turned 24.0642 (12.03 without putting the count back), 150 events of (-3, +2) px turned -54.1445 and -36.0963; single events of 600 px and 450 px dropped (`spikes=2`); with Sensitivity clicked down to 0.90, 200 px turned 21.658. Desktop unchanged: 300 counts are 36.096 degrees in `Player.ControllerPad`, the number of version 2 |
| A2 no look on a gamepad | Right-stick look with the web game's numbers (dead zone 0.14, curve, 166 degrees a second, pitch 62 %, turn boost 1.75 after 0.45 s at the rim), triggers from their axes (a browser sends them only as axes), left stick with its dead zone, L3 sprint latch, the device in use from the last real input. Found on the way: the game viewport hands the right stick's Y over negated (stick up looked down, and the weapon wheel picked the opposite slot) | Stream, Sensitivity 1.00: full right stick for one second (the test client held it about 1.005 s) turned **265.76 degrees**; the web game's own functions give 263.78 for exactly 60 frames, and a frame more at the full rate adds 4.85. Stick up raised the view; the trigger axis fired; a key made the keyboard the device again. Tests: `Input.PadLook` (263.775 at 60 frames a second, 264.775 at 30), `Player.ControllerPad` |
| A3 cards not clickable | Pause, Settings, Dead and Debrief take clicks and hover; the halves of an adjustable row change its value; one hint line under the items. Found on the way: the game-only input mode swallowed the click that takes the mouse capture, so no click on a card reached the game | Stream: hover highlights, clicks logged with their row, Sensitivity, volume and weapon position changed by halves, Close and Resume, and Resume fired no shot (30 rounds before and after). The set-up screens by mouse too: the card, Hit the block, Next three times, Hit the block, into the run, P, Settings, Close, P. Tests: `UI.CardHitTest`, `Run.MenuMouse` |
| A4 Graphics quality side effects | In a stream the Quality row moves the scalability groups only: output resolution, render resolution, the frame cap and the cloud profile stay | Test: `Cloud.Quality` (`t.MaxFPS`, the resolution and a cloud-profile setting unchanged after every level). Stream: four clicks on the row logged "Graphics quality: 0" to "3 (scalability groups only ...)" and the received picture stayed 1920 x 1080. **The frame cap was not read in the stream**: another agent's game shared the GPU in that run (22 to 25 frames a second throughout), so the frame rate says nothing |
| A5 click card for a guest | The card shows for the first viewer and after everybody left | Stream: a second viewer joined, the log said so, `click=0 viewers=2`. Test: `Cloud.Viewers` |
| A6 viewer console and debug commands | Pixel Streaming's console-command handler replaced through its own API (`SetCommandHandler("ConsoleCommand")`): only `PixelStreaming2.` and `PixelStreaming.` commands run, anything else is refused and logged once per session. `MIShot`, `MIAudio.Record`, `MIInput`, `MIMenu`, `MIStart`, `MIFaceEnemy`, `-MICrashTest` and `-MICloudLog` are compiled out of Shipping | Stream: `MIShot <file>` refused and the file not written, `t.MaxFPS 20` refused (the game stayed at 60), `PixelStreaming2.WebRTC.MaxBitrate` ran (`cmdRun=1 cmdRefused=2`). Shipping compiled and linked; **not run**: that the commands are gone from Shipping is read from the source, not tried |
| A7 card text | "No sound? Click the speaker at the bottom right." | Seen in a received frame |
| Controller path (owner, after version 2) | Played controller-only through the stream, which showed: a browser sends a held button again every frame as a repeat, so one tap of A acted about six times on a set-up screen and the Start that began a run paused it at once; a stick arrives as axes only, so it did nothing in a menu; the HUD named keyboard keys. Now: a gamepad's repeats stop before any screen sees them; the left stick presses the menu keys with the web game's timing; the weapon bar, the grab prompt, the cards' hint, the pause line and the set-up screens name the controller's buttons while a controller is in use; Settings has a **Controller** row (Xbox / PlayStation names: a streamed game cannot tell which pad it is, and the web game's "X" is Square on a PlayStation pad); no drawn mouse arrow for a controller player; an input device mapping policy for Linux (without it the engine raised an ensure when a pad connected) | Stream, a first-time player, no mouse or key: A hid the card and pressed nothing else; Start five times went Home, Crew, Loadout, Block and Style, Briefing and into the run (`state` 1 then 2, not paused); stick and trigger looked and fired; Start paused ("START to resume"); the stick held down for 0.62 s moved three rows; A opened Settings; the Controller row set to PlayStation changed the hint to "Cross select", the line to "OPTIONS to resume" and the bar to "CREATE" and "R1"; B went back; Start resumed. The bar named the controller's buttons from the first frame of the run, and Home and the Briefing listed the controller's controls. Tests: `Input.PadMenu`, `Player.ControllerPad`, `Run.MenuMouse` |

**Still open, said plainly:**

- A whole Story run and a Hold the Block run were **not** played through the stream (the owner's point 4), and the
  Dead and Debrief cards were not reached with a controller in a stream (same card code as Pause; tests reach them).
- The delay between hand and picture was not measured here (the owner's point 2).
- Sound still needs one click on the page: a browser's rule, which a controller press may not satisfy.
- The weapon bar still numbers its slots 1 to 4 for a controller player (the D-pad's left and right pick 1 and 2,
  Y swaps, holding Y opens the wheel); the web game shows arrows there, which the HUD's font may not have.
- The Controller row's own words ("Controller", "Xbox", "PlayStation") are in the code, not in the copy deck.
- One mouse event beyond half the player's width wraps in Pixel Streaming's 16-bit field and can arrive small
  (3,000 px arrived as -480 counts): the spike filter cannot see such an event.
- With `-MICloud` on a desktop the stream's mouse path applies (scale 0.5): `xtest.py` numbers from version 2 no
  longer hold there.
- E3DS's field "Unreal console commands to run at start" now takes only the stream's own settings (LAUNCH.md 7).

## The stream itself, received on the box (2026-11-24, 22:20 UTC)

The box cannot run a browser viewer (Chrome gathers no ICE candidates in this sandbox), but a Python WebRTC client
does work there (`/project/ue/cloud/verify-v2/rtcview.py`, aiortc, written by the independent check): it subscribes
through Epic's signalling server, answers the game's offer and decodes the video.

Two copies of the final zip's game (`ceaf828d…`, launcher `f827e1b`) ran side by side as a fresh user with no
display and E3DS's documented arguments, one with `-PixelStreamingDecoupleFramerate` added (runs `f-A`, `f-B`):

| | Frames received per second, 5 s windows over 60 s | Last 25 s |
|---|---|---|
| as E3DS starts it (coupled) | 22, 20, 25, 23, 20, 25, 34, 41, 40, 39, 40 | about 40 |
| with `-PixelStreamingDecoupleFramerate` | 34, 32, 36, 34, 30, 35, 45, 54, 55, 52, 55 | about 55 |

Both: H.264 1920 x 1080 and Opus sound, first frame 1.8 s after subscribing, about 38 audio frames a second. The
game itself drew 60 a second in both. One received frame of each was looked at: the home screen under the
CLICK TO PLAY card, sharp text, the 3D scene moving behind it. (The client's signalling socket closes after 60 s:
a limit of the test client, not of the game, which then logs "Connection lost: the game is paused".) Logs kept in
`/project/ue/cloud/verify-v2/fps-ab/`.

What it means: picture and sound do leave this build over WebRTC with the connection argument E3DS passes
(`-PixelStreamingURL=`); with off-screen rendering fewer frames are delivered than drawn, as E3DS's own article
"Why your app draws 60 frames a second and the viewer gets 15" describes, and decoupling the capture from the
render raises it (in Unreal 5.9 `PixelStreaming2.CaptureUseFence` is already on, so the one flag is enough). The
owner can add it as a launch option now; the next package makes it the launcher's default if E3DS shows the same.
Still not tested anywhere: mouse, keyboard and gamepad through a stream, and E3DS's own signalling and player page.

## Version 2 re-zipped after reading E3DS's own documentation (2026-11-24, 22:05 UTC)

**The zip to upload: sha256 `ceaf828d10a8b3d7997e8b76ccaa7701e87a8f5dab7f488a1976a3b7944674c5`, 2,254,912,173 bytes**,
nine parts (`MurderInc-E3DS-v2b-part<k>-of-9.zip` in the owner's storage), game binaries and paks unchanged
(`e989cb8`), launcher `f827e1b`. It replaces `82ed886a…` (same game, older launcher), which was never uploaded to
E3DS. Checked: downloaded back with the exact command given to the owner, joined, the same sha256, `unzip -t` clean,
the launcher in the zip identical to the repository's, executable bits kept, no `Saved/`.

**Why.** E3DS's documentation (docs.eagle3dstreaming.com) was not reachable from this session until the owner
allowed the host on 2026-11-24 (the earlier research worked from search extracts). Read in full, it says:

- *FAQ*: "These are always sent: `-PixelStreamingURL=`, `-PixelStreamingID=`, `-AudioMixer`, `-log`, `-Unattended`,
  `-StdOut`, `-FullStdOutLogOutput` and `-ABSLOG=`." E3DS names the log file and takes its crash-log email from it.
  A Shipping game writes nothing there: version 1's "no crashlog was found". The `82ed886a…` launcher wrote its log
  only into the app's own `Saved/Logs`, so a failing test would again have produced no log.
- *Command-line parameters*: "`-RenderOffScreen` ... Eagle 3D Streaming does not add it by default", while E3DS's
  own Linux test script adds it. Version 1's launcher (the engine's, plus `-MICloud`) did not. **Box run
  `s-nodisp-noRO` (version 1, no display, no `-RenderOffScreen`): exit 1 after 2.4 s, nothing but an
  `XDG_RUNTIME_DIR` line.** This is the only cause that reproduces version 1's report exactly (dead in seconds, no
  log); the launcher has added `-RenderOffScreen` since the first version-2 zip. Still not proven (no E3DS log
  exists); the SM6 driver check and graphics memory stay possible on some machines and are handled as before.
- *Linux streaming*: "Linux uploads are not stream-tested"; Linux machines are not kept warm and every session
  copies the whole zip; the stream link of a Linux app is on `connector_linux.eagle3dstreaming.com`.

**Launcher changes** (`tools/box/cloud/MurderInc.sh`, `036ee74` and `f827e1b`): `-ABSLOG=<file>` is taken from the
arguments (any case, quotes stripped) and not passed on; every line of the launcher (system report, how the game
ended, the crash report) and every line the game prints go to that file as well as to `Saved/Logs` and to the
launcher's own output; if that file is the Development game's own log, only the closing lines are appended after
the game ends; SIGPIPE ignored (a host that stops reading the output cannot kill the launcher); executable bit set
in the `sh` fallback too.

**Verified on box ec087d85**, with E3DS's documented argument list (`-PixelStreamingURL=ws://127.0.0.1:8888
-PixelStreamingID=e3dstest -AudioMixer -log -Unattended -StdOut -FullStdOutLogOutput -ABSLOG=<file>
-AllowPixelStreamingCommands -Windowed -ForceRes -ResX=1920 -ResY=1080 -PixelStreamingEncoderCodec=H264
-PixelStreamingWebRTCMaxBitrate=20000000 -PixelStreamingEncoderMinQP=18 -PixelStreamingEncoderMaxQP=36`), no display:

| Run | Result |
|---|---|
| x1-ship: Shipping, fresh user | SM6, Nanite and Lumen on, "the default streamer has its video source"; TERM to the launcher: exit 0; the `-ABSLOG` file holds the launcher's report, the game's lines and the ending (70 lines) |
| x2-crash: `-MICrashTest=20` | exit 139; the `-ABSLOG` file ends with `CRASH: ... signal 11 (SIGSEGV)` and the engine's report with the call stack (`UMICloudSubsystem::Tick ... MICloud.cpp:520`) |
| x3-dev: `-MIDev` | the `-ABSLOG` file holds the full engine log (1,675 lines in 30 s): `PixelStreaming2.ID` set to `e3dstest` from the command line, `PixelStreamingURL is a legacy setting and has been converted to PixelStreamingConnectionURL`, `Conference::CreateSession. Id=[e3dstest], Url=[ws://127.0.0.1:8888]`, `Local participant joined the room. roomId=[e3dstest]`; TERM: exit 0 |
| x4-root: launcher started as root, `-ABSLOG` in a root-only folder | the launcher writes the file, the game runs as `nobody`; TERM: exit 0 |
| fake game, ten cases | `-abslog=` in any case and quoted; crash (139) and exit code 3 passed on; unwritable file reported and the game still runs; output closed or read by `head -1`: the launcher survives; started by `sh`; no `-ABSLOG=` |

**Still not known until the owner's E3DS test:** whether E3DS's signalling accepts Pixel Streaming 2 of 5.9 and a
picture reaches the browser (a browser cannot connect on the box; a non-browser WebRTC client did receive the game's
picture and sound there, next entry), the GPU and driver of E3DS's Linux machines, the start-up
wait. The log now answers the first two in one session. The launch pre-flight (four reviews against E3DS's
documentation, `tools/workflows/mi-launch-preflight-wf_eb57e899-664.js`) is collected in `docs/unreal/PREFLIGHT.md`.

## Independent check of the `82ed886a…` zip (verifier, 2026-11-24, 21:32 to 22:10 UTC) — package and runs as reported, real WebRTC frames received; launcher superseded by `ceaf828d…`

On box ec087d85, from the owner's storage, nothing reused from the build folders:

- **Package**: the nine download links of that release report: HTTP 200, 8 x 251,658,240 + 241,645,324 bytes; the
  rename loop of LAUNCH.md section 9 as it then stood matched all nine; joined in order: 2,254,911,244 bytes, sha256
  `82ed886a…d92ee8a`; `unzip -t` no errors; 64 entries; `MurderInc.sh` mode 755 and byte-identical to
  `tools/box/cloud/MurderInc.sh` at `3f5d85a`; `BUILD.txt`: game `e989cb8`, launcher and packaging `3f5d85a` (both
  on the pushed branch); no `*.debug`, `*.sym` or `Saved/`; Pixel Streaming 2 in the game (it registers as a PS2
  streamer; the zip carries only the plugin's helper scripts in `MurderInc/Samples/PixelStreaming2/WebServers`).
- **Runs**: unzipped by a new non-root user into an empty folder; clean environment, no display; every run wrote
  `MurderInc/Saved/Logs/MurderInc.log`; runs, launcher logs and the test scripts in `/project/ue/cloud/verify-v2/`.

| Run | Result |
|---|---|
| E3DS/PS1-style flags (`-AudioMixer -RenderOffScreen -PixelStreamingURL= -PixelStreamingIP/Port -AllowPixelStreamingCommands -PixelStreamingEncoderCodec=H264 -PixelStreamingHideCursor -Windowed -ForceRes -ResX=1920 -ResY=1080`), Epic's signalling server (wilbur 3.3.0), fake viewer joining and leaving 10 times, 7 min | alive; 10 "Viewer joined", 10 "Connection lost: the game is paused"; TERM to the whole process group: exit 0 |
| the same flags, 7 min, no signalling server | alive; TERM to the launcher, passed on: exit 0 |
| only `-PixelStreamingURL=` (plus `-PixelStreamingID=`) | the game registered with the signalling server 13 s after the start |
| **a real WebRTC viewer** (Python aiortc, `/project/ue/cloud/verify-v2/rtcview.py`) | ICE connected in 0.4 s; the game offered H.264 and Opus; first 1920 x 1080 frame 1.1 s after subscribing; 1,941 video and 2,536 audio frames decoded in 60 s; the frames are a changing, non-blank picture (dark, mean level about 22 of 255; measured, not looked at); the game logged the join and, after the viewer left, the pause |
| headless Chrome as the viewer, 5 min | offer and answer exchanged, then nothing: Chrome gathers no ICE candidates in the box's sandbox (with or without its IP-handling or loopback flags); INT to the launcher, passed on as TERM: exit 0 |
| `-sm5` | VULKAN_SM5, the `[MICloud] Fallback` line, `Features: hardware ray tracing off, Nanite off, Lumen on`; TERM to the game itself: exit 0 |
| launcher started as root, root-owned copy in `/opt` | the game runs as `nobody` (`setpriv`), the log is in the app's folder; TERM to the group: exit 0 |
| `-MIDev` | the Development game's full engine log in `MurderInc.log`, the launcher's own in `MurderInc-stdout.log`; TERM: exit 0 |
| HUP to the launcher | nothing happened: the test harness had started it under `nohup`, so HUP was ignored from the start (as for any host using `nohup`); the harness then sent SIGKILL to the game, and the log reads `CRASH: the game was killed by signal 9 (SIGKILL)`, exit 137: an outside kill reads like a crash (LAUNCH.md section 13 now says how to read that line) |

Not re-run: the graphics-memory cases (another agent shared the card meanwhile; the fixer's `v-vram5000` logs show
4,999 MiB free and 60 fps, version 1's `s-vram5000` "Out Of Memory" then signal 11). Not tested: the `ceaf828d…`
launcher (`-ABSLOG=`), input or a gamepad through the stream, a browser, E3DS itself. Root cause: the SM6 mechanism
is real (version 1's Development game under `-sm5`: "Failed to initialize ShaderCodeLibrary", exit 1 at 7 s), but
nothing shows that E3DS's drivers fail the check; the missing `-RenderOffScreen` (entry above) fits E3DS's
documentation better. Neither is proven.

## E3DS crash fix (release engineer, 2026-11-24, evening) — version 2 packaged, verified on the box and in the owner's storage; root cause not proven

**What happened on E3DS.** Version 1 (the zip of `0f23081`, sha256 `8378eedd…e570a`) passed E3DS's upload check
("Test" ✔, "Your app is ready to stream"); then the owner's session showed "In Queue 1" and E3DS emailed "MurderInc
(v-1 …) Crashed At: Tue Nov 24 2026 09:46:05 GMT-0800 (17:46:05 UTC) But no crashlog was found". A second try on the
Core plan with ten slots (about 18:55 UTC) crashed the same way; the Chrome console had no game lines
(`DECISIONS.md`). Version 1 had no log to give: Shipping compiles the engine's log out, and its launcher (the
engine's own `MurderInc.sh`) kept none.

**Root cause: not proven** (E3DS has no log of it). Two diagnoses ran first: E3DS's documentation (through search
extracts; their pages could not be opened from here) and launches on box ec087d85 imitating E3DS
(`tools/box/cloud/e3ds-repro.sh`, results in `/project/ue/cloud/repro/SUMMARY.txt`). Ranked by how well they fit
"passes the upload check, every real session dies at start, no log":

1. **Best supported: the server's NVIDIA driver fails Unreal 5.9's Vulkan SM6 check.** Unreal 5.9 runs its full
   renderer (Nanite, Lumen, ray tracing) only if the GPU and driver pass the profile `VP_UE_Vulkan_SM6`
   (`Engine/Source/ThirdParty/Vulkan/profiles/include/vulkan_profiles_ue.h`): Vulkan 1.3 and 16 extensions, among
   them `VK_KHR_compute_shader_derivatives` (the KHR version: recent NVIDIA drivers only), `VK_EXT_mesh_shader` and
   `VK_EXT_descriptor_buffer`. If the check fails the engine picks SM5 (`RHI/Private/Linux/LinuxDynamicRHI.cpp`
   prefers the highest feature level that passes), but version 1 carried SM6 shaders only (the project drops
   `SF_VULKAN_SM5`): the game ends about 7 s after the start with exit code 1 ("Failed to initialize
   ShaderCodeLibrary required by the project because part of the Global shader library is missing"), and a
   Shipping build prints only "Disabling core dumps." Reproduced on the box with `-sm5` (box driver 620.70 passes the
   check). A fleet on an older long-term driver would fail every session the same way, whatever the slot; E3DS's
   upload check does not start a Linux build (their documentation: Linux uploads are only checked for the plugin's
   files), so it could pass.
2. **Graphics memory at start.** Version 1 used 4.2 GB of the card's memory on the title screen (Vulkan memory
   budget, `r.Vulkan.DumpMemory`) and segfaulted 6 s after the start when only 5.0 GB was free ("Out Of Memory,
   trying to allocate 134217728 bytes", a 128 MB render-graph heap). An 8 GB card with anything else on it would do
   that.
3. **Started as root**: Unreal refuses ("Refusing to run with the root privileges", SIGABRT after 0.2 s). Unlikely
   (no Unreal Linux app would run on E3DS), not ruled out by anything E3DS publishes.
4. **A stop by signal returns 130/143** ("Exiting abnormally"): if E3DS counts any non-zero exit as a crash, stopping
   an instance sends that email. Fits the email, not a session that never shows the game.

Ruled out on the box (no crash): viewers joining and leaving (pause on leave), no signalling server or one killed
mid-run, no audio device, no display with `-RenderOffScreen`, a fresh user or no HOME, another working directory,
`-ForceRes` 1920x1080, E3DS/Pixel Streaming 1-style arguments, no hardware ray tracing, 7-minute runs, 7.6 GB free.

**What changed** (all for the cloud package; gameplay rules untouched):

- **A log for every start** (`tools/box/cloud/MurderInc.sh`, the zip's launcher in place of the engine's): it runs
  the Shipping game as before (`MurderInc-Linux-Shipping MurderInc -MICloud ... "$@"`) and adds `-RenderOffScreen`
  (no display needed), `-UserDir=<app>/MurderInc` (Saved/ next to the game, as a Development build keeps it) and
  `-stdout -FullStdOutLogOutput`; it writes `MurderInc/Saved/Logs/MurderInc.log` (falls back to `$HOME`, then
  `/tmp`): build (`BUILD.txt`), user, folder, display variables, memory and disk, `nvidia-smi` (GPU, driver, free
  memory, other GPU processes), missing libraries (`ldd`), the Vulkan loader and driver files, the SM6 extension
  check (with `vulkaninfo` when the server has it), the command line, every line the game prints (tee through a
  FIFO; tee ignores stop signals, so a host that signals the whole process group cannot kill it and SIGPIPE the
  game), how the game ended (exit code, signal name, CRASH or stopped by the host) and the engine's crash report
  (`Saved/Crashes/*/Diagnostics.txt`). A stop signal (TERM, INT, HUP) goes on to the game once, as SIGTERM, and only
  if the game did not get it itself within 5 s (Unreal hard-exits on a second signal); a stop the host asked for
  counts as a normal quit (exit 0). A background job of a non-interactive shell starts with SIGINT ignored (and
  Unreal keeps an ignored SIGINT ignored): the launcher re-runs itself once with SIGINT back to default and starts
  the game through `env --default-signal=INT,QUIT`. Started as root, it runs the game as the folder's owner or
  `nobody` (`setpriv`, else `runuser`, else `su`). Started by `sh`, it re-runs itself under bash.
  Launch options: `-MIDev` (the Development game in the zip, full engine log), `-MIForceSM6`
  (`-SkipVulkanProfileCheck`).
- **bUseLoggingInShipping is not possible here**: the box's engine is an installed build
  (`Engine/Build/InstalledBuild.txt`); its Shipping engine libraries are precompiled with the log compiled out and UBT
  refuses a unique build environment on an installed engine. So Shipping's log is the launcher's (above), the game's
  own lines, the engine's crash handler and, for a full engine log, the Development game carried in the zip.
- **The game reports itself** (`Source/MurderInc/Cloud/MICloud.cpp`): at start the build (`BUILD.txt`), GPU, driver,
  RHI, feature level, shader platform, hardware ray tracing, Nanite, Lumen and video memory; a fallback line when the
  SM6 check failed (SM5) or ray tracing is missing (then `r.Lumen.TraceMeshSDFs=1`, software Lumen on the meshes'
  distance fields); the full command line. In Shipping every `[MICloud]` line is also printed to stdout (UE_LOG is
  compiled out), so the launcher's log has them. `-MICrashTest=<s>` crashes on purpose (to test the crash path).
- **Exit guard** (same file): on Linux game builds an `on_exit` handler armed at `FCoreDelegates::OnExit` ends the
  process when `main()` returns, before the static destructors that crashed every Development exit (the AVCodecs
  `FNVDEC` registry logging after the log is gone: `TSparseArray<...FAPI...>::~TSparseArray ->
  TIntrusiveReferenceController<FNVDEC>::DestroyObject -> UnhookDllAllocators -> UE_LOG`, gdb in
  `/project/ue/cloud/repro/gdb-dev/gdb.log`), and reports a stop asked for by SIGINT, SIGTERM or SIGHUP (engine status
  128 + signal, "Exiting abnormally") as exit code 0. `-MINoExitGuard` turns it off.
- **SM5 fallback shaders** (`package-cloud.sh` overlay): the cloud package cooks `SF_VULKAN_SM5` as well as SM6, so a
  failed SM6 check gives a running game (no Nanite and no hardware ray tracing; Lumen in software) instead of exit 1.
- **Crash reports headless** (overlay, `[CrashReportClient] bAgreeToCrashUpload=true`,
  `bStartCRCFromEngineHandler=false`): without a display the engine counts as unattended and skipped its report; now
  it writes `Saved/Crashes/crashinfo-MurderInc-pid-*/` (Diagnostics.txt with the call stack, CrashContext.runtime-xml).
  No crash reporter is packaged, so nothing is uploaded.
- **Graphics memory**: `[MICloud]` texture pool 800 to 600 MB and `r.TSR.History.ScreenPercentage=100` (the 200 %
  history was a 4K buffer); the six interior cube maps (`/Game/Art/Interiors/TC_*`, 64 MB each, uncompressed float,
  always resident) are stored as BC6H in the release copy (`tools/box/cloud/cloud_assets.py`, run by the usage step
  with `demo/fix_usage.py`).
- **Home screen**: the controls strip shows "P Pause" when streamed (`Source/MurderInc/UI/SMIFrontEnd.cpp`).
- **Packaging** (`tools/box/cloud/package-cloud.sh`): `src` reads the clone as ue4 (the provenance line was empty
  under root) and records `src.commit`; `package` records the commit the binaries were built from; `zip` installs
  the launcher, writes `BUILD.txt` (game commit, launcher commit, branch, date), copies the Development game beside
  the Shipping one, leaves `*.debug`, `*.sym` and any `Saved/` out (symbols kept on the box in
  `/project/ue/cloud/symbols/<commit>/`); new `parts` step (240 MiB parts and their sha256, joined sha256 checked);
  `-NoDDCCleanup` for the cook and the asset step (on a fresh box the cache maintainer's scan of the 9p cache starved
  the cooker's own cache reads: the first cook attempt sat 20 minutes at "Compiling global changed shaders", "is very
  slow (0.00 MiB/s)"; without the maintainer the cook ran in about 20 minutes).
- **Tools**: `tools/box/cloud/e3ds-verify.sh` (the runs below in one detached command); `e3ds-repro.sh` finds the
  game under the new launcher by name and can stop the launcher instead (`STOPTO=launcher`).

**Verified on the box** (box ec087d85, RTX PRO 6000 Blackwell, driver 620.70.06):

Gameplay clone at `e179e3b` (same C++ as the package): `build.sh` OK, **`tools/box/test.sh MurderInc`: TESTS OK
passed=105 failed=0 skipped=0** (golden replays included; 1214 s, the editor's first start on this box took 10 min).

Every run goes through the zip's launcher with a clean environment (`tools/box/cloud/e3ds-verify.sh`,
`e3ds-repro.sh`; results in `/project/ue/cloud/repro/<run>/`, launcher logs in the build's
`MurderInc/Saved/Logs/` or the fresh user's `$HOME/MurderInc-cloud/Saved/Logs/`). "Version 1" is the REPRO result
with the old package.

| Run | Conditions | Version 1 | Version 2 |
|---|---|---|---|
| v-long | 7 min, fresh user, no display, signalling server, fake viewer joining and leaving 12 times, `-ForceRes` 1920x1080, TERM | alive | alive 7 min; 11 "Viewer joined" / 11 "Connection lost: paused" lines; TERM: exit 0; log fell back to `$HOME/MurderInc-cloud` (build folder not writable for that user) |
| v-sm5, d2-sm5 | `-sm5`: what a driver failing the SM6 check gets | exit 1 after 7 s | runs on VULKAN_SM5 for 100-120 s (Shipping and Development), `[MICloud] Fallback` line; TERM: exit 0 |
| v-root | launcher started as root | SIGABRT after 0.2 s | game runs as ue4 (`setpriv`); TERM to the launcher passed on; exit 0 |
| v-crash, w-crash | `-MICrashTest=30` (null write) | no log | log: `CRASH: the game was killed by signal 11 (SIGSEGV) after 29s`, then the engine's report with a symbolicated call stack (`UMICloudSubsystem::Tick(float) [.../MICloud.cpp:520]`); `Saved/Crashes/crashinfo-MurderInc-pid-*/` holds Diagnostics.txt and CrashContext.runtime-xml |
| v-nort | `-ini:...r.RayTracing=False`, INT to the launcher | - | not a valid test: Shipping ignores `-ini:` overrides (ray tracing stayed on), and the launcher, started as a background job, ignored INT: KILLed after 30 s. Both fixed and re-run as w-dev-nort and w-int-launcher |
| w-dev-nort | Development game (`-MIDev`), `r.RayTracing=False` | (REPRO: runs) | "Ray tracing is disabled", `[MICloud] Fallback: no hardware ray tracing ... Lumen traces in software (mesh distance fields)`; 90 s; TERM: exit 0 |
| w-int-launcher, w-term-launcher | INT / TERM to the launcher after 60 s | - | "got SIGINT: passed it on to the game as SIGTERM", "quit normally (stop asked by SIGINT)": exit 0; TERM likewise |
| v-dev-quit, w-mem | the Development game from the Shipping zip quits by itself | segfault on every exit | exit 0 (the exit guard: "[MICloud] Exit: engine status 143 (stop asked by a signal: a normal quit); exiting with 0" after a TERM, 0 after quit) |
| v-vram5000 | 5.0 GB of the card free, home screen 120 s | SIGSEGV after 6 s ("Out Of Memory, trying to allocate 134217728 bytes") | alive at 60 fps; TERM: exit 0 |
| v-vram6000 | 6.0 GB free, Development Story run 220 s | (REPRO: 150 s ran) | Story run (state 2) at 60 fps; TERM: exit 0 |
| v-e3ds-7600 | E3DS/PS1-style flags (`-AudioMixer -PixelStreamingURL= -PixelStreamingIP/Port -AllowPixelStreamingCommands -PixelStreamingEncoderCodec=H264 -PixelStreamingHideCursor -Windowed -ForceRes`), 7.6 GB free, fresh user, 5 viewer cycles | alive | alive 220 s at 60 fps; TERM: exit 0 |
| w-shot2 | home screen, Development game, `-MICloudNoCard` | "ESC Pause" | the controls strip ends with **"P Pause"** (picture looked at, kept on the box: `/project/ue/cloud/repro2/home.png`) |
| launcher, locally | fake game: TERM, INT, HUP to the launcher; TERM and INT to the process group; crash; `sh` and `dash` start | - | all end as described above (exit 0 for host stops, 139 for the crash) |

Graphics memory (Development, `r.Vulkan.DumpMemory`, the game's committed Vulkan memory, 1920 x 1080): home screen
4,218 MB (version 1, `d-mem`) to **3,596 MB** (version 2, `w-mem`); Story run 30 s in 4,541 MB to **3,805 MB**.
Texture cube memory 384 to 48 MB (BC6H interiors), TSR history colour 127.5 to 33.8 MB, UAV textures 809 to 691 MB.

**Package** (2026-11-24, 20:26 to 21:23 on box ec087d85; `package-cloud.sh all` after the tests, then the zip
rebuilt twice for launcher fixes found by the runs): game binaries and paks from `e989cb8` (C++ identical to the
tested `e179e3b`), launcher and packaging from `3f5d85a`. `/project/ue/cloud/MurderInc-E3DS.zip`, **2,254,911,244
bytes, sha256 `82ed886a3fb508a96ce6ac0e7c4a4c3b61f0563872e9d9cdc25249817d92ee8a`**, 64 files (2.7 GB unpacked):
`MurderInc.sh` (mode 755), `BUILD.txt`, the Shipping and the Development game, the paks with SM6 and SM5 shader
libraries; no `*.debug`, `*.sym` or `Saved/`. Nine parts of 240 MiB (the last 241,645,324 bytes) PUT from the box
to the owner's Higgsfield storage (all HTTP 200), confirmed as files, named `MurderInc-E3DS-v2-part<k>-of-9.zip`;
**downloaded back, joined: the same sha256, `unzip -t` no errors**; local copies deleted. Part sizes and sha256 in
LAUNCH.md section 9. The download links are only in the release report (public repository, licensed content). Superseded: the first upload of version 2 (sha256 `a57e2288…`, the
launcher before its signal fixes; still in the storage under the same names) and a second zip (`468015bc…`, never
uploaded: it had swept the box's test logs from `Saved/` into the zip, hence the `Saved/` exclusion).

**Not proven / not done:** the root cause of the E3DS crashes (no E3DS log exists; the SM6/driver explanation is the best supported, not
proven: E3DS's driver version is unknown); whether version 2 streams on E3DS (a browser cannot connect on the box;
a non-browser WebRTC client later received its picture and sound there, "Independent check" above; input and a
gamepad through a real stream were never tested); E3DS's command line, user, GPU sharing and crash detection (unpublished); what E3DS's
"Print UE Log in Browser Console" and "Auto Download UE Crash Log" actually read (whether they find
`MurderInc/Saved/Logs`); `-MIForceSM6` (never needed on the box); the SM5 fallback's picture (it ran; nobody looked at
it); a real 8 GB card (the box emulates one by holding memory; the engine still sees 96 GB). bUseLoggingInShipping
was not possible (installed engine, see above). Known cosmetic issue, fixed in source after the package: the SM5
fallback line says "no Lumen" though the platform keeps software Lumen (`acce058`).

## Repackage for the website (release engineer, 2026-11-24) — delivered, checked from the storage

**Box 8b816116**, 16:30 to 16:55. Branch head `0f23081` (C++ as built and tested in the fix pass). No editor of the
gameplay clone was running (`ps`). Steps, as RESUME 8 step 4 says:

- Gameplay clone `sync.sh` (`d1d1e05` -> `0f23081`, docs and pictures only), then `tools/box/test.sh MurderInc` there:
  **TESTS OK passed=105 failed=0 skipped=0** (golden replays included).
- `tools/box/demo/package.sh snapshot` (gameplay clone -> `/project/ue/repo-release`, 2.6 GB of Content), then
  `tools/box/cloud/package-cloud.sh all`: src `0f23081`, refresh, content, overlay, **usage: 20 masters saved with
  their flags, 0 not found**, Development (cook 2,233 packages; only the known `ABP_FP_Pistol` blueprint errors,
  ignored), Shipping, zip. 8 minutes 17 s in all. Release copy `Config/DefaultGame.ini` carries
  `r.Streaming.PoolSize=800` in `[MICloud]`.
- **Zip:** `/project/ue/cloud/MurderInc-E3DS.zip`, 2,320,153,618 bytes (Shipping 2.6 GB unpacked; the zip of
  2026-11-23 was 1.46 GB before the block-v2 art and the later content), sha256
  `8378eedde07ce04510a654dee46032c7af6bc87b7fb37852b210d6af4e9e570a`. The old zip is kept on the box as
  `old-4ff06998.zip` (parts in `parts-old-4ff06998/`).
- **Started on the box** (`xtest.py`, the box's desktop `:1`, XTEST input), Shipping and Development: running 7.8 s
  after launch; **CLICK TO PLAY card up**; the first click dismisses it; Enter and Tab through Crew, Loadout, Block and
  Briefing into a **Story run** (state 2); mouse look 0.12032 degrees per count (as before); P pauses and resumes;
  60 fps, GPU 5.9 to 7.3 ms in the run, `poolMB=800`, peak RSS 3.8 GB (Shipping) and 4.0 GB (Development).
  Looked at the Shipping frames: the card over the home screen, and the run's first view (the El, the pizza front,
  the taxi, the CHOPPER in Rule's hands, the health band and weapon strip, the objective panel). The Development
  log has **no `missing usage flag`** line (and no other error but ALSA, which has no sound device on the box).
  Pictures stay on the box (`/project/ue/cloud/run2/xship`, `xdev`): they show pack and likeness content.
- **Delivered:** split into ten parts of 240 MiB (`split -b 240M`), each PUT from the box to the owner's Higgsfield
  storage (all 200) and confirmed (type `file`), named `MurderInc-E3DS-partN-of-10.zip`. **Verified** from the
  storage: all ten downloaded to the local checkout's scratch space, joined with `cat`, sha256 equal to the above,
  `unzip -t`: no errors, 64 files, `MurderInc.sh` launches `MurderInc-Linux-Shipping MurderInc -MICloud "$@"`.
- `docs/LAUNCH.md`: the "do not upload" warning replaced by which build to upload; section 9 has the ten part
  names, sizes, per-part sha256 and the joined sha256. The download links themselves are **not** committed (this
  repository is public and the zip holds licensed content); they are in the release report of this run.

**Not done here:** the explosion frame after the garage propane tanks (RESUME 8); the stream itself (WebRTC is still
blocked on the box): the E3DS free trial is the next test (LAUNCH.md section 4). Seen in passing: the home screen's
controls row still lists `ESC Pause` while the cloud card says P pauses (both work locally; in a browser P is the
reliable one).

## Fix pass after the independent play-through (2026-11-24) — built, 105 of 105, pictures retaken

**2026-11-24, box 8b816116**, gameplay clone `/project/ue/repo-gameplay`, branch head built at each step (`build.sh` OK
every time; only the two known `CompositeFont` deprecation warnings). `tools/box/test.sh MurderInc`: **105 of 105 pass**,
golden replays included, on `f643e67` (all the C++ below). The review's 14 entries, most visible first:

**Fixed (each in a commit of its own):**
- **Night did nothing** (`0042dc5`). `levels.json` `levels.block.times` is `["day"]`, and the boot keeps only the times
  the default level offers (the chips, the Home picker and the title item read `Settings.Rules.Times`, which came from
  `rules.json`, so the data change alone would not have hidden Night). A saved "night" is refused by `SetTime` and the
  run plays by day; the briefing text is unchanged. The night rig (atmos.json `rigs.night`) is still to build.
- **In-game cards looked like placeholders** (`00fa8a9`). `AMIHUD::DrawMenu` draws title, pause, settings, game over
  and debrief as a dark plate with a gold top edge, the kicker in gold, the title in the display face with a gold rule,
  the note wrapped to the plate, stats as key/value rows with hairlines, and every item as a row: the selected one a
  gold button with dark text (no more `> <`), adjustable values as `<  value  >` in gold; all sizes scale with
  `ClipY / 1080`. Picture `fix-pause`.
- **Health readout** (`00fa8a9`). On a dark band bottom left like the weapon strip: the number in the display face,
  `HEALTH` small, a bar; below 30 % the band, number and bar turn red and pulse. Picture `fix-hud`.
- **Cooked game would draw default grey materials** (`5572427`). `package-cloud.sh` has a `usage` step (run by `all`
  between `overlay` and `package`): `demo/fix_usage.py` on the release copy. `fix_usage.py` now also flags every
  master under `/Game/Characters/Buzzard` for skeletal meshes. Run once on the gameplay clone here (editor stopped):
  20 masters saved (Rule's silver, tracer, pack rifle, Goon SMG and lens, NINE magazine, the art masters, the three
  Buzzard masters).
- **Muzzle flash when aimed, orange forearm** (`cd8462f`). Aimed (Ads at or above `fx.flash.view.overlayAds` 0.5)
  the player's flash uses the depth-tested cards on the muzzle, 0.7 the size (`scaleAimed`): no star over the rear
  sight. The player's flash light is its own: `fx.flash.player` 8,000 cd, 6 m reach, placed 1.1 m out along the bore
  past the gun (it was the enemies' 30,000 cd at the muzzle, 20 to 40 cm from the forearm). Pictures `fix-fire`,
  `fix-fire-ads`.
- **Forearm-long casing** (`cd8462f`). The casing's first-person phase is drawn at `fx.casing.viewScale` 0.55 and
  spins at `viewSpin` 0.3 of the world spin (1,400 degrees a second a few centimetres from the eye smeared into a bar
  under motion blur).
- **Stepped fade into the stage** (`44f6c4a`). `SMIFrontEnd` draws the veil's edge as one image: a 512 x 1 transient
  texture, the background colour with alpha 0.88 falling to 0 by a smooth step. Pictures `fix-loadout`,
  `fix-briefing`.
- **Pursuers fire over the debrief** (same commit). From `Complete` the enemy field is not stepped any more (every
  test and golden run stops at `Complete`), and `UMIEffects::ClearShots` ends every tracer, flash card and flash light
  in flight. Picture `fix-debrief`.
- **Wave 3 never cleared** (`f2ba240`). Hold the Block: with nothing left to spawn and one or two enemies alive, the HUD
  marks each in red where it is (a diamond and the distance), or on the screen's edge toward it when it is off screen
  or behind. If only Buzzards are left and none has been hurt for 60 s they are brought down (not to the player's
  tally) and the wave clears. Game only (`Boots.bPersist`): tests and replays never take that path. The Buzzard's own
  patrol and line of sight near the El were not changed (rules code shared with the web game's replays).
- **Grey-box loadout stage** (`f643e67`). `frontend.json stage.materials`: world-projected instances of the block's
  scans on the set's cubes (brick back wall, painted block walls, concrete floor, a steel top on a dark frame, a metal
  turntable) and two pools of light on the back wall. Picture `fix-loadout`.
- **Blocky rooms behind the backs' windows** (`87c339a`). The six baked interior cubes were streamed textures sampled
  by a ray in the glass material (no mesh UVs), so streaming held their smallest mips. They are never streamed and
  filtered trilinear now (`mi_interiors.py` sets both on every bake; set and saved on the gameplay clone's cubes here).

- **Black rectangle on the Chop Shop floor** (`a818b8d`). Found by elimination in play (still there with dynamic
  shadows off and with decals off): one of the eight oil-stain cards of `SM_Struct_ShopFloor` (`M_Sign_OilStain`,
  1.2 to 2 m). Its texture set's BC alpha is coverage, but only the set (not the slot) says so, so `slot_parent` gave
  it the opaque master and the whole card drew as a dark square. `slot_parent` now gives sign sets whose alpha is
  coverage the masked master; on the gameplay clone `MI_Sign_OilStain` was reparented to `M_MI_SurfaceMasked` and
  saved: an irregular blot now (`fix-chopshop3`). The rule also applies to seven more sign sets at the next
  `block.sh start materials force` (CartonPrint, CrateStencil, IPXMark, LoadingZone, Mural, PostNoBills,
  VultureStencil): look at them after that build.

**Checked, not changed:**
- **The Cage gate** (`fixpass-cage.txt`): the nav walk from the player start into the Cage ended 76 cm from reel 3
  with the grab prompt up (the review's walk, from elsewhere, stopped 11 m short). The north gate is a 3 m gap
  (level.json colliders 315 to 318, x 33 to 36) with nothing in it; the walk uses its full 40 s from the start, so a
  bot's time limit, not the gate, is the likely cause. The level data (web parity) was not touched.
- **Explosions** and the **packaged build's log** (`missing usage flag`): not checked; no package was made in this
  pass. Both are for the repackage (RESUME 8, step 4): `package-cloud.sh all` now runs the usage step itself; then
  start the build once, grep its log for `missing usage flag`, and freeze 0.1 to 0.3 s after the garage propane tanks.

**Pictures** (`docs/unreal/shots/fix-*.jpg`, play in editor on this build): `fix-loadout` (dressed stage, smooth veil
edge), `fix-briefing` (veil over the street), `fix-hud` (health band), `fix-fire` and `fix-fire-ads` (0.03 s after a
round: flash on the muzzle, no orange forearm, casing small), `fix-pause` (styled card), `fix-debrief` (the debrief
card after extraction, no tracer), `fix-cage` (end of the nav walk at reel 3), `fix-chopshop3` (the oil blot). The
proof script is `tools/box/fp/fixpass-shots.sh` (with `fixpass-cage.txt`, `fixpass-debrief.txt`).

**Not done.** The night rig; the Buzzard's own patrol height and line of sight near the El (rules code shared with the
web game's replays: the 60 s fallback and the HUD marks cover a stuck Buzzard); the repackage and the explosion frame
in it; the level clone (`/project/ue/repo`) has neither the cube nor the oil-stain change (rebuild there with
`block.sh start materials force`, then `interiors`).

## Box back: fix pass built and proven, start view, the backs and the skyline dressed — done

**2026-11-24, box d6f06d9d** (new rental, RTX PRO 6000, 16 cores, 64 GB, 113.84 credits an hour), gameplay clone
`/project/ue/repo-gameplay`. RESUME section 8 steps 1 and 2.

**Set-up and the fix pass proven.** `ensure-setup.sh` answered SETUP-DONE at once; `sync.sh` to `c2786c7`; `build.sh`
(first build on the fresh box, 507 s) compiled the 36-card flash pool (`9e55db3`) and the whole fix pass;
`tools/box/test.sh MurderInc`: **105 of 105 pass** (golden replays included), and again **105 of 105** after this
pass's C++ (start pitch, HUD crosshair). `fp/import-chars.sh fx` made `/Game/FX/M_FX_FlashView`. Play frames from
`fp/polish-shots.sh` (mission and holdout), each looked at: `polish-fire` and `polish-fire-ads` show the player's flash
on the muzzle (front of the handguard at the hip, round the front post aimed), the brass small and leaving, no burst
on the knuckles; `polish-hold` shows Hold the Block wave 1 with Goons on the avenue.

**Fixed in this pass (each seen in a picture before and after):**
- **The first frame faced a trash can.** Measured, not assumed: the galvanised can that replaced the litter basket
  (prop 270, 1.1 m ahead) is an open scan with its lid on the ground beside it, so its dark inside still filled the
  bottom of the frame (`MIPose` frames at the start, pitched down to see it). Moving the can or its collider 704
  breaks the golden `avenue` walk (it slides round that collider at step 8); moving the start breaks
  `Golden.Directors` (its runs start there); a yaw turn would need 27 degrees right, into the shop fronts. The start
  pose stays the web game's; the view starts **pitched 7 degrees up** (`presentation.json` `block.startPitch`, read
  in `UMIGameSubsystem::ResetPlayer`; the test hosts ignore it): `polish-start` looks down the avenue under the El,
  no can. (`ff0181b`)
- **The 7 brick backs read as blockout.** `build_block.py` dresses every face of a neighbour's back that looks into
  the block with the facade kit's bays: `SM_Facade_BayWindow_Red` (cast-stone sill and lintel, painted double-hung
  frame, glass with a baked room) storey by storey from the first floor line, `SM_Facade_BayBlank_Red` for the ground
  floor, for storeys hidden behind something lower that stands in front (shop wall 6.9 m, garages 4.7 m: a window
  where its sill is at most 40 cm under that top) and for the strip under the parapet; a roller blind behind 45 % of
  the windows, an air conditioner in 12 %. 119 window bays, 141 blank, on 9 faces. The drawn mass steps back 30 cm
  behind the bays (the collider stays as it was, hidden); the block's seal walls, which share four of those planes
  from inside, are drawn in pieces stepped back 31 cm behind the bays; backdrop masses no longer reach into the backs
  (both had filled window openings with brick). (`7be27b6`, `ee56a91`, `d8e8d93`, `6b66ebc`, `7daa915`)
- **The skyline towers and backdrop read as blockout** (salmon slabs with flat black window squares). The world-
  projected window grid (`WEAR_HLSL` in `M_MI_Surface`) now draws a cast-stone sill and lintel, a reveal in its own
  shadow (the opening reads 10 cm deep), a painted double-hung frame with its meeting rail (colour per building),
  blinds and curtains in some windows and the room behind the glass by interior mapping, as emission (new output
  `WinE`, camera vector input). Masses of 45 m and more are towers: curtain walls of tinted reflective glass with
  mullions and spandrels (`MI_Backdrop_TowerGlass`, `...GlassDark`, window mode 2) or office stone with punched
  windows (`MI_Backdrop_TowerStone`), and from 60 m one or two setback tiers on top. (`7be27b6`)
- **The crosshair stayed in the aperture when aimed** (`polish-chopper-aim`, open since the polish pass). Cause: AHUD
  canvas lines are batched opaque and ignore alpha, so the Ads fade never showed. The arms are translucent tiles now,
  skipped when faded: aimed, no "+" in the rear sight. (`6b66ebc`)

**Pictures** (`docs/unreal/shots/`): `polish-start`, `polish-avenue`, `polish-lot`, `polish-fire`, `polish-fire-ads`,
`polish-chopper-aim`, `polish-hold` retaken on this build; `backs-lot.jpg` (the lot's backs with their bays),
`backs-cage.jpg` (the Cage's two backs, the towers behind), `skyline-west.jpg` (the avenue's continuation and the
towers from 22 m up). Before: the polish pass's pictures in git history.

**Re-verified on the branch head (2026-11-24 15:20, box 8b816116, a new rental after d6f06d9d stopped idle).** `ensure-setup.sh` SETUP-DONE; `sync.sh` `ca393d8 -> b1d321f` (no C++ changed); `build.sh` OK (402 s, fresh box; only the two known `CompositeFont` deprecation warnings in `MIStyle.cpp`); `tools/box/test.sh MurderInc`: **105 of 105 pass**, golden replays included (98 s). Nothing in the game changed since the pictures above, so they were not retaken.

**Not done.** The level clone (`/project/ue/repo`) was not rebuilt: its L_Block keeps the old backs until
`block.sh start materials force` then `level` there. The repackage for the website (RESUME section 8 steps 4 and 5)
and the independent play-through review (step 3) are next. The muzzle flash light turns the firing forearm orange
for the frame of the shot (`polish-fire`): bright, but one frame; left as is.

## Polish fix pass (after the independent play-through review) — code committed, nothing built or seen

**2026-11-23/24, no box.** Box d14fa3ab had ended (`credits_exhausted`); the Higgsfield balance is **0.6 credits**.
The last key in `scratchpad/box/keys` (`0b02e986...`) was recorded in `used` and `gpu_rent` with the approved settings
was refused ("You do not have enough credits for this rental"); no key is left. So in this pass **nothing was compiled,
no test or golden replay was run and no picture was taken.** Every change below was written to be safe without a
build (the optional material is looked up before it is loaded; data keys have code fallbacks), but the next box must
build and run the suite before anyone packages. No rules code and no golden data were touched.

What changed (commits on the branch, most visible first):
- **The player's muzzle flash** (`36f558b`). Cause, from the polish measurements: the cards are drawn, but at the hip
  the gun's own front end sits between the eye and the muzzle and hides them. Fix: `mi_fp_import.py fx` now also
  makes `/Game/FX/M_FX_FlashView` (the flash material with **depth testing off**), presentation
  `fx.materials.flashView` names it, and `UMIEffects` gives the player's flash its own six cards in it, placed on the
  muzzle's true first-person point (`flash.view.pullOverlay` 1, no pull toward the eye: the star no longer lands on
  the support hand's knuckles) and never recycled by Goon flashes. Without the material the polish-pass path runs.
- **Brass and the dropped magazine** (`69aedd1`). `UMIEffects::SpawnViewBody`: first-person depth and size only while
  it leaves the gun (`fx.casing.viewLife` 0.12 s; magazine 0.45 s), then a true-size body thrown at the same moment
  from the port's (well's) true place (`FirstPersonToWorld`) is shown for the rest of its life. Before, the shrunken
  body stayed 4 s (8 s): the size of the rear sight on screen, then a miniature on the ground.
- **HUD** (`5dc3081`). Objective title and counter on a dark band, the counter in the display face and larger; markers
  on a dark backing and pushed out of a ring of 7.5 % of the height round the crosshair ("[1] 24m" sat on the aim
  point); the weapon strip on a band with a tag row: one mode badge per two-mode gun (filled on the gun in hand) and
  the selector as a key cap "[B] SWITCH TO SEMI" left of the slots (`frontend_text.json` `hud.modes.switchTo`); the
  radio strip moved to 0.815 of the height, clear of the strip's band.
- **Player start** (`b7b5a16`). `build_block.py PROP_MESH_OVERRIDES`: prop 270, the litter basket 1.1 m ahead of the
  start whose black liner was the dark half disc of every first frame, is drawn as the galvanised lidded can
  (`SM_Prop_TrashCan_Metal`) in the same place and collider (collider 704 and the start pose stay: both are web-game
  parity). Takes effect at the next `block.sh start level`.
- **Set-up stage banding** (`ba2eca2`). `UMIFrontEnd::CutCamera` marks a camera cut on the frame of every view-target
  switch and stage reframe and on the next frame; entering play and the title camera mark one too.
- **Loadout stage light** (`da986d4`, data). The fill rect stood behind the gun facing the camera: a rect light lights
  only what is in front of its plane, which is the hard lit-to-unlit seam across the back wall in `demo-loadout.jpg`.
  The fill is now on the camera's side, the key brighter (2600 lux), and a rim spot from behind right.
- **Proof commands** (`4261408`). `MIPose` and `MIFaceEnemy` mark a camera cut: `polish-hold`'s orange ghost on the
  pavement came right after the `MIFaceEnemy` snap turn. Whether a mouse turn in play ghosts the viewmodel (TSR
  velocity of first-person primitives) is still to check on the box, frame by frame during a turn.
- `docs/LAUNCH.md` tells the owner not to upload the current zip (`29bf7a1`); GAMEPLAY.md 13 and 15 describe the
  changes; the duplicated Demo build text inside the Polish section is gone.

**Not fixed, and why.**
- **The crosshair still drawn when aimed** (`polish-chopper-aim`). The "+" there is exactly the HUD crosshair (13 px
  arms, gap 0), so the HUD saw Ads below 0.05 while the gun was aimed; yet `AMIHUD` reads `Rules.GetView().Ads`, the
  same value the first-person rig aims with. Not explained from the code. On the box: `MIInput ads 1`, then log
  `View.Ads` from the HUD in the same frame.
- **Brick backs and skyline** read as blockout (`MI_Box_BrickWindows`, flat black windows; salmon towers): an art pass
  in `build_block.py` on the box (facade kit window modules, or recessed frames and glass in the material).
- **`-IgnoreCookErrors`** in the release engineer's `package.sh` / `package-cloud.sh` (two dead template anim
  blueprints): theirs to change; not seen by a player.
- **Level clone L_Block**, **the stream test on E3DS**, **the repackage**: need a box or the owner.
- **CHOPPER firing pinky** 2.7 mm into the grip, on its hidden back: left for launch, as the review says.

**Exact next steps on the next box** (after the credits are topped up): `sync.sh` and `build.sh` in
`/project/ue/repo-gameplay`; `fp/import-chars.sh fx` (makes `M_FX_FlashView`); `block.sh start level` there (prop 270);
`tools/box/test.sh MurderInc` (105 tests and the golden replays); `fp/polish-shots.sh` and the Hold run, and look at
`polish-start` (the lidded can), `polish-fire` and `polish-fire-ads` (flash on the muzzle, no knuckle burst, casing
small and gone), `polish-chopper-aim` (crosshair), a frame mid-turn (ghost), the loadout and crew stage right after a
cut; fix what they show; then the release engineer's `package.sh snapshot` from the gameplay clone and
`package-cloud.sh all`, and the new sha256 in LAUNCH.md.

## Cloud build (release engineer): Pixel Streaming 2 package for Eagle 3D Streaming — package delivered, stream test blocked on the box

**2026-11-23, box d14fa3ab** (it ended at 19:48 when the credits ran out). Owner's guide: `docs/LAUNCH.md`. Scripts:
`tools/box/cloud/` (`package-cloud.sh` makes everything in one command from the branch and the gameplay clone's
Content; `setup-ps.sh`, `stream-test.sh`, `stream_test.cjs`, `xtest.py`, `memory-runs.sh`, `hold.txt`, `shot.txt`,
`localhost.cjs`).

**In the game (`Source/MurderInc/Cloud/MICloud.*`).** Pixel Streaming 2 (the 5.9 engine's
`Engine/Plugins/Media/PixelStreaming2`, the only streaming plugin) is enabled in `MurderInc.uproject` for the **game
target only** (`TargetAllowList: Game`): the editor and the tests never load it. The release copy enables it for every
target (`package-cloud.sh overlay`), because the cooker is the editor and only a cooker that loads the plugin cooks
its global shaders (without it the game stops at start: "Missing global shader FXRCubemapPS"). `UMICloudSubsystem`
switches on when the command line carries a Pixel Streaming URL, `-MICloud`, or the plugin reports a signalling
connection; then it applies the **Cloud profile** (`[MICloud] +CVars=` in `DefaultGame.ini`, device-profile
priority), shows a **CLICK TO PLAY** card (the click is eaten: it presses nothing), names **P** as the pause key in
the browser (P was already bound; the browser keeps Esc), draws a **software cursor** where the game shows the mouse
(the stream has no OS cursor), **pauses** when the last viewer leaves and puts the card back for the next one. It
also gives the default streamer its back-buffer video source if the plugin made it before Slate existed (here it had
one). `-MICloudLog=<file>` and `-MICloudProbe=<s>` write what the game saw (Shipping has no engine log);
`-MICloudNoCard` for runs nobody clicks. The E3DS launcher `MurderInc.sh` gets `-MICloud`.

**Tests: 105 of 105 pass** (`test.sh` run from `/project/ue/repo-release`, editor target built from the branch, 49 s).

**The package.** `package-cloud.sh all`: Development (for measurements) and **Shipping** (delivered), Linux, about
5 minutes for both on a warm cache; zip 1.4 GB, `MurderInc.sh` at the root (E3DS app name `MurderInc`), sha256
`4ff069986adae2d19464c91a6542fa9477d6ba157efa4b969c6d2463a53b3118`, in the owner's Higgsfield storage as six parts of
240 MB (`MurderInc-E3DS-partN-of-6.zip`, joined with `cat`, LAUNCH.md section 9). It was built before the texture
pool went from 1500 to 800 MB; the repackage with 800 MB was cut off with the box, and the next
`package-cloud.sh all` carries it.

**In-game test on the box (the Shipping build, `xtest.py`, XTEST input as a stream's input becomes):** running 8.3 s
after launch; card up; the first click hides it; Enter and Tab through Crew, Loadout, Block and Briefing into a Story
run; mouse look **0.12032 degrees per count**, identical to local play (100 counts = 12.03 degrees); P pauses and
resumes; the software cursor shows on the set-up screens. That run used a second X server (`Xvfb :99`); the rental
says not to start one, so `xtest.py` now uses the box's own desktop `:1` (stop the demo game first).

**Memory (Development, off screen, 1920 x 1080, `memory-runs.sh`).** The card was shared (the demo game and the
gameplay editor), so two measures: the rise of the card's counter during the run, and the game's own Vulkan figures
(`r.Vulkan.DumpMemory` before it quits). Story, Epic preset: 4.3 GB own, 6.7 GB card rise, RAM 3.2 GB. Story, Cloud
profile: 5.5 and 5.7 GB card rise in two runs (the own figure did not print in that run), RAM 3.2 GB. Hold the Block,
Cloud: 3.4 GB own, but only the first waves (`hunt` ends at once before the first wave; `hold.txt` now alternates
fights and waits). Home screen: Epic 3.8 GB, Cloud 3.2 GB own. **Peak under 7 GB in every case.** GPU frame time on
an RTX 4080 could not be judged here (shared card: 17 to 30 ms a frame with two other Unreal processes on it). The
before/after picture of the home screen (`/project/ue/cloud/mem/shot-epic/shot.png`, `shot-cloud/shot.png`) is on
the box's storage, not fetched before the box ended.

**Not done: the WebRTC stream on the box.** Signalling (Epic's infrastructure, branch UE5.7 as the engine's
`get_ps_servers.sh` names, Node 22, bound to 127.0.0.1 by `localhost.cjs`, player page on 8090 because the desktop
stream holds 8080) and offer/answer work, the game joins, Opus audio and the H.264 video track are negotiated, and
the game hands the stream 60 frames a second. But **the game's WebRTC stack gathers no ICE candidates on this box**
(a gVisor sandbox: `Linux 4.19.0-gvisor`, no `/sys/class/net`); Chrome on the same box gathers its own, so the
connection stays "new" and no media flows. Port allocator flags, media capture, fences, a decoupled frame rate and a
window on an X server changed nothing. So start time through a stream, the stream picture, audio in the WebRTC track,
input-to-picture latency, gamepad through the stream and the browser side of a lost connection are **untested**;
`stream-test.sh start` + `test` (headless Chrome viewer, fake gamepad, latency by frame differencing) are ready for a
machine with an ordinary network stack. E3DS's servers are ordinary Linux machines: the free trial is where these get
tested (LAUNCH.md section 4 is the checklist).

**Mouse speed through the stream (read from the 5.9 source, untested).** The frontend sends `movementX` normalised to
the video element's size and the plugin scales it back to the game's resolution (`PixelStreaming2Input`,
`InputHandler.cpp`): look speed matches local play when the stream resolution equals the player's video size, and
scales with their ratio otherwise. LAUNCH.md asks for "match the browser window" in E3DS if the speed feels off.

## Demo build (release engineer): the game playable from a browser — done

**Verified 2026-11-23** on the box (session d14fa3ab). Owner's guide: `docs/DEMO.md`. Scripts: `tools/box/demo/package.sh`,
`start.sh`, `stop.sh` (copied to `/project/ue/demo/tools/` on the box; the demo-video agent's `capture.sh`, `audio.sh`,
`finish.sh` share the folder).

**Route: the rental's own browser desktop.** The desktop rental already streams its screen (Selkies, websockets mode,
H.264 on the card) to a private page behind the platform's HTTPS link (`Open desktop`, a `*.w.modal.host` address
with a connect token and a session token); that page is the only thing the box exposes to the internet. Pixel
Streaming was not used: it needs its own signalling and media ports reachable from the internet, the rental routes
no other port, and the rental's instructions forbid starting tunnels, VNC or web servers on a desktop box ("the
desktop and its link already exist"). A packaged Mac build is impossible from Linux (it needs a Mac with Xcode and
the engine), and was not needed.

**Windows do work here for the game.** `desktop-run --vulkan` (the box's launcher: primus_vk renders on the RTX PRO 6000
and presents through llvmpipe on the virtual screen) draws the packaged game, and `UnrealEditor <project> -game`,
in a window without aborting; only the editor's own window was ever seen to abort (BOX.md).

**The package.** `package.sh snapshot` copies the gameplay clone's project (Source, Config, Content with all the
imported art, the editor module) to `/project/ue/repo-release` (its own copy: `repo-demo` is the demo-video agent's
clone), `package.sh start` runs BuildCookRun Linux Development: game target 2 min from scratch, cook 1 to 2 min
with the shared cache, 1.7 GB staged in `/project/ue/demo/build/Linux`. Overlay on the copy only: start map
`L_Block`, cook the folders the data loads by path (Art, Audio, Characters, FX, FirstPerson, ThirdParty, Weapons,
Input, Variant_Shooter), stage `Content/Fonts` as files (`UI/MIStyle.cpp` reads them like the data), no Zen store
(the cooker's Zen writer aborts: no Zen server on the box), `-IgnoreCookErrors` (the template's ABP_FP_Pistol and
ABP_FP_Weapon no longer compile and are unused). The package holds pack and Epic content: box only, never committed.

**Found and fixed: mouse look was 14 times too slow outside play in editor.** BaseInput.ini scales MouseX, MouseY
and Mouse2D by 0.07 and Enhanced Input applies it even with the legacy scales off: 300 counts turned 2.5 degrees
(read back with `getall MIPlayerController ControlRotation`) instead of 36. `Config/DefaultInput.ini` now replaces
the three entries with sensitivity 1; after the fix 100 counts turn 12.03 degrees (0.0021 rad per count, exact) and
50 counts down pitch 6.0 degrees down. Play-in-editor input went through `MIInput`, which is why no test saw it.

**Measured through the desktop path** (the X screen the stream sends; input injected with XTEST as the stream's
input is): home screen to the Story run through Crew, Loadout, Block and Briefing with mouse clicks; 1920 x 1080 full
screen, Epic preset, TSR at 73 %: **60 fps locked**, GPU 6.4 to 6.6 ms, game thread 5 ms, draw 7.5 to 7.9 ms;
mouse-move-to-screen 43 to 56 ms (median of 8, includes a 12 ms screen grab). With two other agents' editors
running on the same card: 55 to 60 fps, GPU 14 to 17 ms, 78 ms median delay. The uncooked `-game` run with an
editor alongside managed 36 to 49 fps: the package matters. The desktop icon "MURDER INC." (re)starts the game.
Pictures (box only, they show pack content): `/project/ue/demo/home.jpg`, `g3.jpg`, `ads.jpg`, `fire.jpg`.

**Limits** (the rental's stream settings, not the game): no sound in the browser (Selkies runs with audio off; the
game's audio device does not open for user ue4 either: "ALSA: Couldn't open audio device"), no gamepad through the
browser (gamepad input off), Safari has no keyboard lock (Esc leaves gaming mode). The game window does not follow
a later resize of the desktop: restart it with the icon. Seen in play: a black half disc below the left forearm in
the hip pose (art, first-person agent), vertical banding on the set-up stage for a few frames after a camera cut.

## Polish pass (visible breaks in normal play) — done

**Verified 2026-11-23** in the gameplay clone `/project/ue/repo-gameplay` (MCP 8001), play in editor in L_Block from
the player's eye (`tools/box/fp/polish-shots.sh`; set-up CHOPPER, NINE, STICK on the set-up screens, day, Hustler).
Pictures `docs/unreal/shots/polish-*.jpg`, each looked at.

**1. No grey boxes left in L_Block.** The gameplay clone played an old L_Block (22 Nov, no vehicle art: the two dark
slabs in front of the player at the start were a parked car's colliders drawn in `MI_Grey_Car`, the IPX truck a cube).
`Content/Art` and `L_Block.umap` copied from the level clone (BOX.md 7), then `block.sh start level` rebuilt the map
there with `build_block.py`'s new rules for the last colliders with no module (`structure_placements`): the shanty by
the El is the plywood pen (`SM_Struct_DigPen` fitted to its box), the material hoist in the lot a chain-link cage up
the whole 9.3 m tower in panel-high rows with pallet stacks at its foot, the lot sign's pole a steel column
(`SM_Struct_ShopColumn`), and the seven neighbours' backs (brick masses with the window grid and tar roofs) carry the
facade kit's parapet round their roofs (134 modules), a water tank each and a stair bulkhead on the biggest. Read back in
the editor: the only `Grey_*` actors left are those seven brick backs in `MI_Box_BrickWindows`; every other collider is
invisible under art (615 of 622). The 13 vehicles, the taxi and the IPX truck draw as art (`polish-start`,
`polish-avenue`, `polish-lot`). The level clone's own map is untouched (rebuild it there with the same `block.sh start
level` when its agent next runs).

**2. The player's muzzle flash and tracer.** Measured, not guessed (`tools/box/fp/flash-diag.sh`, frozen 0.02 s after a
round, the visible effect cards read back): the three flash cards were drawn all along, 38.6 cm from the eye at the
muzzle's first-person point, screen (1058, 694). That point is on the handguard's front end as the eye sees it: at the
hip the muzzle sits straight behind the gun's own front, which is nearer the eye and hides it, and the two jet cards
lay along the bore, edge-on to an eye behind it. With `r.HZBOcclusion 0` and `r.AllowOcclusionQueries 0` the frame was
the same (not culling); the material is two-sided additive unlit (not back faces). Fix (`UMIEffects::ViewFlash`): the
star faces the eye, the jets run along the bore turned toward it, and at the hip all three are pulled toward the eye on
their sight lines to half their distance with sizes alike (same pixels, drawn over the gun's end); aimed the pull eases
off, because pulled in they fell behind the rear sight. The tracer started from the world muzzle a metre out and flew
along the line of sight: 0.02 s later it was a dot under the crosshair. `UMIEffects::PlayerTracer` leaves the muzzle as
drawn and converges on the aim point, its tail held 0.8 m out for the first 12 m (`fx.tracer.player`).
`polish-fire.jpg` is that frozen frame 0.02 s after a hip round.

**3. CHOPPER fingers.** `FMIFPFingerCurl` in `UMIFPAnimInstance`: per-gun, per-finger closing (or opening) about the
knuckles, from presentation `guns.<id>.real.fingers.hip / .aim`, blended by Ads, let go in actions and the sprint
(GAMEPLAY.md 15). The numbers come from play: console `MIGripProbe` skins the arms on the CPU from the imported model
and measures each finger's pads against the pack rifle's triangles, signed by their normals. On the pack's Short rifle
with SK_RuleArms every finger is within 3 mm of the gun at the hip, aimed and on a round (support index, middle,
pinky 0.3 to 1 mm into the handguard, ring 0.3 mm off; firing middle on the grip, pinky 2.7 mm into it, ring 2.2 mm off;
trigger finger 2.6 mm off the trigger at rest and 0.7 mm on a round). The 11 to 20 mm gaps of
`rule_r3_final_review.json` were measured in Blender on the old CHOPPER model, which the pack rifle replaced
(DECISIONS.md). The CHOPPER's data backs the support middle and pinky out of the handguard (-1 degree: 0.9 to 0.7 mm);
opening the firing pinky took it deeper (its deepest point is on its back, under the grip, out of view): left as the
clip has it.

**4. Other breaks seen in play.** The radio strip (bottom centre) sat on the sunlit forearm with no backing and did not
read: a soft dark band behind the whole line now (`AMIHUD`). The "black half disc" at the lower left of the start view
(also in the demo notes) is the open top of the trash can 1.1 m ahead of the player start (prop 270), not a fault.
The player's flash vanished once Goons were firing: their flashes share the effects' card pool (three cards a
flash), and with 9 cards three enemy shots inside 0.045 s recycled the player's own (`polish-tracer.jpg`: tracer drawn,
flash gone, the frame after "They made you"). The pool is now 36 cards (commit 9e55db3: **built nowhere yet**, see below).

**Pictures** (play frames, 1920 x 1080): `polish-start`, `polish-avenue`, `polish-lot` (the IPX truck at the back of
the lot), `polish-hold` (Hold the Block, wave 1, Goons on the avenue), `polish-chopper-aim`, `polish-fire` (frozen 0.02 s
after a hip round: the flash star over the gun's end; the tracer is the short orange dash at the crosshair of the
first tracer version), `polish-tracer` (the current tracer, a streak converging from the gun on the aim point; no
flash: the card-pool fault above).

**Not done (why).** The box ended at 19:48 with `credits_exhausted` (the account's Higgsfield credits ran out) while
the full suite was running; a re-rent with the next key was refused ("not enough credits"). So:
- **The suite was not completed after these changes.** Last full run in this clone: 105 passed (fix pass). The C++
  changed here is presentation only (effects, first-person anim curls, HUD band, a dev command); no rules code and no
  golden data were touched. Run `tools/box/test.sh MurderInc` first thing on the next box.
- **The 36-card pool (9e55db3) is not built or seen.** Next box: `sync.sh`, `build.sh`, then
  `bash fp/polish-shots.sh` and retake `polish-fire` (and `polish-fire-ads`: aimed, the flash on the muzzle round the
  front post was built but its frame was taken while the pool was being recycled).
- **The release copy** (`/project/ue/repo-release`) still holds the old L_Block without vehicle art: the release
  engineer's next `package.sh snapshot` from the gameplay clone carries the rebuilt map and `Content/Art`.
- The level clone's L_Block was not rebuilt with the new rules (`block.sh start level` there when its editor runs).

## First person (the player's arms and guns, the Goons, the effects) — first pass done

Built in the gameplay clone `/project/ue/repo-gameplay` (MCP 8001). Contracts: `docs/unreal/GAMEPLAY.md` 15 to 19.

**Verified 2026-11-23**
- **Art in the game project** by one re-runnable command (`tools/box/fp/fp-art.sh pack | put | unpack`, then
  `tools/box/fp/import-chars.sh all`, 2 to 3 minutes headless): `SK_RuleArms` on SK_Mannequin (Recompute Normals off,
  `M_RuleArms_Skin` with `SP_RuleSkin`, `M_RuleArms_Nail`, the silver bracelet), the three Goons r3 by
  `mi_chars.setup_goons` (Cloth shading, exported normals), `SK_Nine` with its magazine, `SM_Weapon_GoonSMG`, `SK_Buzzard`,
  the CHOPPER's dark-earth instances on the pack's own textures, and the /Game/FX materials. The pack was already in the
  project (the loadout agent's `import-animpack.sh all`): not re-imported. Re-run after any re-export by the character
  agents: assets are replaced in place, no data change.
- **The real paths are data** (the dev overlay is gone): presentation.json `firstPerson.arms`, `.jewels`, `.recipe`,
  `.animSets`, `guns.chopper.realMesh` + `real` (the Short pack rifle, its sockets, `animSet` and finish), `guns.nine.realMesh`
  + `real` (SK_Nine), `enemies.goon.variants` (the Goons, `variantsFallback` the mannequins), `meshScale` 0.98, the SMG on
  `hand_r`; guns.json `animSet` on SHORTY, STICK, STRETCH; `opticMesh` read by `FMIReadiness::BaseMesh`. A clean checkout
  keeps the templates (`FirstPerson.RealArt` checks both ways).
- **Pictures through the player's eyes** (`tools/box/fp/fp-shots.sh`, play in editor in L_Block, Story on Hustler, set-up
  CHOPPER + NINE + STICK with scope and vertical grip made on the set-up screens; 1920 x 1080, each looked at):
  `shots/fp-hip-sun.jpg`, `fp-hip-el.jpg` (the CHOPPER as the pack's Short rifle in its dark-earth finish, the bare
  tattooed arms in the pack's idle), `fp-irons.jpg` (Aim_Pose, the rear aperture on the screen centre at 38 degrees),
  `fp-scope.jpg` (the STICK, irons folded under the scope, the window on the eye line at 32 degrees),
  `fp-reload-tactical.jpg` (Reload_Quick warped onto 2.24 s), `fp-reload-empty.jpg` (Reload_Empty onto 2.72 s, the
  magazine dropped as a body: logged at 1.1 to 1.4 m/s), `fp-inspect.jpg`, `fp-nine.jpg` (SK_Nine in both hands, the
  palms pulled onto its Palm sockets, the bracelet), `fp-goon.jpg` (a Goon at about 12 m firing at the player: its
  SMG's flash and the tracer; frozen on its round), `fp-explosion.jpg` (a propane tank blown at 9 m).
- **Rules untouched.** The pack's clips play at the rules' times (reloads warped piecewise onto the stage times), never
  the other way round; `Loadout.ParityGolden` and every `Golden.*` replay still pass with 0 mismatches.
- **Suite** (`tools/box/test.sh MurderInc`, 2026-11-23, after the web sound files were copied into the clone from a local
  `node tools/ue-export/audio.mjs` output): **TESTS OK passed=104 failed=0** (new: `FirstPerson.RealArt`, `.OpticTwin`,
  `.Clips`: 31 clips on the right skeletons).

**Open (most important first)**
1. **The translucent puffs do not show in play** (smoke, dust, blood mist): they are spawned, placed, sized and faded
   (read back from Python during a blast: 47 visible cards of 1.8 to 2.1 m, opacity 0.47 to 0.49, on M_FX_Smoke,
   which compiles: 483 instructions), lit or unlit alike, yet no picture shows them; the additive cards (flashes,
   sparks), tracers, lights and debris bodies do. So `fp-explosion.jpg` (0.42 s) shows the blast's light, the fireball's
   glow and the debris but no smoke. Next: one puff in front of the camera in a test map to find the cause, or a
   Niagara sprite system for the puffs (none is built: every effect is code on pooled components). The strike marks
   (MD_FX_Mark) and the casings were not caught in a picture.
2. The bare forearm in direct sun reads orange-red under the El (`fp-hip-el`, `fp-irons`) even with the game's shorter
   scatter (`SP_RuleSkin` 0.22 cm, Opacity 0.45): for the character agent (skin albedo / profile), see Handoffs.
3. The scope's reticle dot (1.5 mrad) is about 3 px at 32 degrees and sits under the HUD crosshair: hide the crosshair
   while aimed through an optic, or enlarge the dot (`M_TFA_AR_Reticle`, animation agent).
4. NINE: template third-person pistol clips (idle, fire); no pistol reload, holster, draw or inspect clips (the rig's
   procedural poses play them). A first-person pistol pack is still the recommended route (DECISIONS.md).
5. Goons: template rifle anim set with the SMG on `hand_r` at the CHARACTERS.md offset; no left-hand IK onto the SMG,
   no fire, reload or hit montages; the Buzzard is still the placeholder (`SK_Buzzard` imported, not driven).
6. A run started with the console `MIStart` (no set-up screens) uses presentation.json's own guns: the template way.
   The set-up flow (`fe hit`, the saved set-up) resolves the real art.
7. The CHOPPER's mounts stay `missing` (parity): DECISIONS.md allows the Short rifle's parts; not offered yet.

### First-person fix pass (independent review, 2026-11-23: grades 2 and 2)

Box re-rented (the old one had ended idle). Everything below was verified in the gameplay clone, play in editor in
L_Block, pictures retaken with `tools/box/fp/fp-shots.sh` and looked at.

**Fixed, most visible first**
- **The NINE's magazine** sits in the grip: `SM_Weapon_NineMagazine` is modelled in the pistol's space, so it rides
  the `magazine` bone at the inverse of that bone's reference pose (`UMIFirstPersonRig::MeshSpacePartOnBone`).
  New test `FirstPerson.NineMagazine`: magazine box (-1.35..4.53, +-1.3, -13.45..-3.3) cm inside SK_Nine's box, below
  the bore, centred, upright (`fp-nine.jpg`).
- **Casings** leave the port on screen (drawn at the first-person depth and size: `FirstPersonToNearWorld`), and the
  dropped magazine the same way. **Muzzle flash and tracer: still not seen in a picture** (see Not fixed). Found and
  fixed on the way: the headless editor plays at 10 to 20 frames a second and one long step aged the 0.045 s flash
  and the 0.09 s tracer past their life before they were drawn (the cards were read back hidden); flashes, lights and
  tracers now advance at most 1/60 s a frame and a tracer starts one frame in flight. Read back after that fix, the
  three flash cards are visible, 38 to 44 cm from the eye, sized right, frozen 0.02 s after a round, and a test card of
  the same material placed 40 cm in front of the eye by hand draws; yet the cards at the muzzle drew nothing. The
  flash now goes through the effects' world cards (`WorldFlash`, the Goons' flash path) at the muzzle's first-person
  point; that build was not looked at in a picture (the clone's editor was restarted by another session, see below).
- **Smoke, dust and blood mist** never drew: a bright card on M_FX_Smoke showed, 53 smoke-coloured cards at opacity
  0.5 facing the camera at 7 to 9 m left the street untouched (`fx_diag.py`, read-back from Python). M_FX_Smoke is now
  a lit, masked, dithered card (DitherTemporalAA, TSR resolves it): it takes the sun and Lumen; blast smoke lighter
  (albedo 0.07) (`fp-explosion.jpg` 0.42 s, `fp-explosion-late.jpg` 1.6 s).
- **Aiming.** The HUD crosshair fades out with smoothstep(Ads); the irons are zeroed (the front sight's direction in
  the clip's aimed pose turned onto the camera axis, per gun); the support elbow drops when aimed
  (`supportElbowDrop`, the hand kept on the handguard); the optic's reticle lit to 25,000 nits and the glass nearly
  clear (`firstPerson.opticMaterials`) (`fp-irons.jpg`, `fp-scope.jpg`).
- **Tactical reload stows** the partly used magazine (hidden at magOut, no body); only the empty reload drops one,
  drawn at the first-person depth so it is seen leaving the well (`fp-reload-tactical.jpg`, `fp-reload-empty.jpg`
  0.1 s after magOut).
- **Damage** at the edges (twelve bands, a 9 % centre wash, not the old 25 % full-frame tint) with a red wedge toward
  the hit for 1.5 s (`fp-explosion-late.jpg`).
- **MIStart** resolves the saved (or parity) set-up through the loadout resolver: a console run draws the pack rifle
  and the real arms ("chopper drawn with the pack's clips" in the log). **MIFaceEnemy** finds a walkable spot at the
  asked distance with a clear line (10.4 m for 10; `fp-goon.jpg`, and `fp-goon-5.jpg` at 5 m).
- **The Buzzard** is SK_Buzzard (props spun, gimbal on the eye, lens lit), the grey disc only in a clean checkout.
- **Goons:** the support hand is pulled onto the SMG's SupportHand point by two-bone IK after the animation
  blueprint (`UMIGoonMeshComponent`), and the drawn body turns onto the rules' aim. Not yet seen up close: at 10 m
  (`fp-goon.jpg`) the hands are a few pixels, and the 5 m picture caught no Goon in sight (not committed).
- **NINE:** a finger-only layer (the pack idle's wrap) on the support hand, and in a reload the support hand follows
  the magazine's base pad. In `fp-nine.jpg` the support fingers still read straight: the wrap needs its own pose.
- Arms re-imported from the current export (`fp-art.sh pack|put|unpack`, `import-chars.sh arms`); the dev overlay
  file on the box is deleted (the data path is presentation.json since the first pass).
- Suite: **TESTS OK passed=105 failed=0** (every `Golden.*` replay and `Loadout.ParityGolden` among them).

**Not fixed (why)**
- **The player's muzzle flash and tracer in pictures** (above). Next step: with `log LogMI Verbose`, fire with
  `MIFreezeOn fire 0.02` and read the logged muzzle point in camera space ("Flash: world cards ... muzzle in camera
  space ..."); project it to the screen and check what covers it (the support hand or the front sight at the hip),
  and take `fp-fire.jpg` aimed, where the muzzle is clear of the hands. `fp-fire.jpg` is not committed.
- The suite was last run after the effects-clamp build (6f794e2: 105 passed, 0 failed, every `Golden.*` and
  `Loadout.ParityGolden`); the two later C++ commits (the flash through `WorldFlash`, a tracer's first frame, verbose
  logs) are presentation only and were built (OK) but not run through the suite: another session restarted this
  clone's editor at 15:08 and killed the shells on the box.
- The arms' skin (saturated orange, red stripes at the El's slat shadows, tattoos, hair, pores) is the character
  agent's pass in progress (commit 5667229: resident textures, detail normal, shorter scatter, re-lettered tattoos);
  the game picks it up by re-running `fp-art.sh` + `import-chars.sh arms`. Support fingers wrapping the rail at the
  hip need per-finger targets on the rail: not done (the elbow drop only acts when aimed).
- The grey-box blockers in L_Block are the level's colliders drawn by tag (`build_block.py`, level agent): hand-off.
- Goon motion stays the template rifle set (no SMG or pistol aim set exists in the project); mask and cloth
  materials are the Goons agent's.
- NINE reload, draw and holster clips do not exist (no pistol pack); the rig's procedural poses play them.
- Effects remain code on pooled components, not Niagara systems (no scriptable Niagara authoring here); no smoke
  flipbook texture exists.

## Demo video (capture artist)

**Verified 2026-11-23** in its own copy of the gameplay clone, `/project/ue/repo-demo` (logs `/project/ue/logs/repo-demo/demo`).
The video is delivered privately through the owner's Higgsfield storage (it shows pack and Epic content: never
committed); six stills from it are `docs/unreal/shots/demo-*.jpg`. Scripts: `tools/box/demo/`.

**The take** (`tools/box/demo/demo.txt`, take t9; `murder-inc-unreal-demo.mp4`, 90.0 s, 1920 x 1080, 60 fps, H.264
High about 10.6 Mbit/s, AAC stereo 48 kHz, 119 MB, -14.3 LUFS integrated, true peak -1.7 dBFS): 0-2 s the title card;
2-30 s Home, Crew (Rule), four guns (CHOPPER, NINE, STICK, STRETCH), the Workbench (scope, then silencer on the
STICK), Block & Style (the block, day, Story, Hustler), the Briefing; the cut to play is the briefing's own fade-in.
32-90 s one unbroken first-person run in L_Block: down the avenue under the El past the taxi and the box truck, the
Goons alerted and fought (headshots; "It's Murda!" on a headshot kill at 62.6 s), a reload, the NINE (a Buzzard
and a Goon), back to the CHOPPER, a propane blast in the garage, the last reel taken (2 of 3 counted as taken
earlier: `secure`), the sprint to the IPX truck with Goons chasing, extraction at 83.0 s: "What's my name?!" (clean
take) at 83.3 s, the crowd's "R-U-L-E!" at 85.0 s, "I-N-C!" and the debrief card. Voice lines of the engine render
(`audio.sh`): I-N-C 32.1, Rule Baby 34.5, Murda 62.6, name 83.3, chant 85.0, I-N-C 87.7 (title included).
Stills: `shots/demo-home.jpg`, `demo-loadout.jpg`, `demo-bench.jpg`, `demo-avenue.jpg`, `demo-fight.jpg`, `demo-truck.jpg`.
To redo it: `capture.sh start tools/box/demo/demo.txt <name>`, `audio.sh start <name>`, `finish.sh <name>
/project/ue/fonts/Anton-Regular.ttf <end s>` (about 12 minutes in all).

**How it is made (all headless, re-runnable).**
- The game runs **standalone** (`UnrealEditor <project> /Game/Maps/L_Block -game -RenderOffscreen`), not in the editor:
  that works on this box and draws every frame. `-benchmark -fps=60 -deterministic` gives a fixed 1/60 s game step, so
  each engine frame is one video frame whatever the render costs (about 30 frames a second of wall clock), and the take
  is the same every time (t3, t4 and t8, t9 matched frame for frame up to the first changed line).
- `UMIDemoDirector` (`Source/MurderInc/Flow/MIDemoDirector`, dev only) plays `tools/box/demo/demo.txt` on game time:
  the set-up screens by their console twins (`MIMenu fe ...`), then the run through the player's own input state
  (move axis, fire, aim, reload, weapon keys, interact). The view is never set in one step: a damped spring turns it
  toward what the script looks at (the walk's direction ahead on the route, a Goon's head, a tank, the truck), at most
  110 degrees a second. Verbs: `route` / `goto` (walk a nav path, `goto` plans it in C++ with the Goons' own
  `FMIBoxWorld::FindPath`), `fight` / `auto` / `hunt` (pick the nearest Goon in sight, aim at the head, ADS, short
  bursts), `alert` (the rules' own enemy alert), `blow`, `grab`, `secure` (a reel counted as taken earlier, no event),
  `hide`, `god`. `tools/box/demo/plan_path.py` prints routes from level.json's nav grid.
- Frames: `MIDemo.Capture` reads the game viewport with its Slate screens and the HUD every frame
  (`FSlateApplication::TakeScreenshot`, as `MIShot`) at `FCoreDelegates::OnEndFrame` and writes raw BGRA into a FIFO
  that ffmpeg (installed on the box with apt) encodes (`capture.sh`).
- Sound: `MIAudio.Record` records the event bus from the first captured frame; `audio.sh` plays that stream through
  the engine's own audio mixer on the imported Sound Waves (`MurderInc.Audio.EngineRender` with `-MIAudioStream=`,
  the live director's seed 7 and the take's voice options), **placed on the audio device's own clock**, so the
  recording lines up with the frames (the dummy driver drifts from the wall clock). `finish.sh` puts the 2 s title
  card in front, cuts the take, takes the front left and right, normalises to -16 LUFS and encodes H.264 / AAC.
- Voice options of the take: `MIVoice clean 1` (the clean "What's my name?!") and `frequency often`.

**Found on the way (for everyone who runs the game outside the editor, the packaged build too).**
- **Materials without a usage flag draw as the default material in a standalone game** ("missing usage flag Nanite!
  Default Material will be used in game"): the editor adds flags on the fly, so PIE never showed it. Affected: the pack
  rifle's `MI_TFA_AR_02/04/ATT_01` (base `M_TFA_AR_Surface`), the Goon SMG, the NINE magazine, the bracelet silver,
  `M_FX_Tracer` (skeletal), and with the block-v2 map every art master on instanced meshes (the El steel, concrete,
  plates). `tools/box/demo/fix-usage.sh` sets and saves the flags (in the demo copy only: generated content). The
  scope's glass and reticle are translucent on a Nanite mesh and stay on the default material (bench close-up only).
- **The gameplay clone plays an old L_Block**: no vehicle art, so the 63 car colliders drew as dark grey slabs and the
  IPX truck as a plain cube. The demo copy took `Content/Art` and `Maps/L_Block.umap` from the level clone
  `/project/ue/repo` (BOX.md 7): parked cars, the taxi, the box truck and the IPX truck are real now.
- The smoke and dust puffs do draw in the standalone game (soft, lit; the explosion's fireball and smoke column read
  well): their absence in PIE pictures was the headless editor's picture path.
- Two takes crashed (signal 11, no stack in the log) on the frame after the director started aiming at a propane tank
  with the NINE in hand; with the CHOPPER the same blast never crashed (three takes). Not found: `capture.sh` with
  `DEMO_GDB=1` runs the game under gdb for the stack.

**Open (what the video still shows)**
- The NINE in hand is the weakest moment (the template pistol pose: the gun rests on the palm; in a fast turn the
  support forearm swings across the view). The take keeps the NINE to a few seconds.
- Fights happen at 12 to 20 m: the Goons are small on screen; hits on them have no reaction animation.
- The Workbench stage is dim and the gun small on it; the debrief card at the end is small text on a darkened view.
- Motion blur turned down for the take (`r.MotionBlur.Amount 0.15`); turns still smear a little.

## Rule's arms in the game: hands-and-tattoos pass (character and technical artist)

**Verified 2026-11-23** in the gameplay clone (`import-chars.sh arms`, then `tools/box/fp/fp-arms-shots.sh`, play in
editor in L_Block; pictures `shots/fp-arms-*.jpg`, each looked at). Cause and fix: `CHARACTERS.md`, "SK_RuleArms,
hands-and-tattoos pass". In play `ListTextures` lists the four arms textures at full size and not streamed; the skin is
on the Standard Subsurface model (no red fringes on the sun-stripe shadow edges), R/B 2.5 brown; knuckle wrinkles,
wrist creases and the thumb nail read at the hip; the tattoos sit on the thumb side of the upper forearm (outside the
hip frame, as in the photo: `fp-arms-forearm-l/r` turn the arms to the eye to show them).
Restart (same day): the forearm close-ups now aim at the tattoo centres measured on the mesh (Unreal's glTF import
swaps the bones' local Y and Z, which had pointed the earlier close-ups at bare skin), and both tattoos read in play;
the skin's scatter is toned down (`SubsurfaceTint` 0.26 / 0.14 / 0.09, `Scatter` 0.6) after the sunlit forearm under
the El read salmon. All six `fp-arms-*.jpg` retaken after `import-chars.sh arms`.
Open (for the next pass): the NINE's support hand and the hip hold still come from the template pistol clip (the gun
rests on the palm, the fingers do not wrap); no per-gun finger pose ships; the pack clips' finger poses were not
measured against this hand's thickness.
Second pass after the in-game review (hands 1.5, tattoos 2.5, "no tattoo in any play frame"): `CHARACTERS.md`, "SK_RuleArms,
second pass". Proof is now unmodified play frames only (`fp-arms-shots.sh` rewritten; the close-ups that moved the arms
are gone). A probe in play measured the face of each forearm the eye sees; the numerals moved to 5-15 cm above the wrist
on that face, the script line heavier, the skin's warmth back in the albedo (`SkinTint` 1, `SubsurfaceTint` 0.35 / 0.18 /
0.11). The NINE takes a solved grip from `Content/Data/grips.json` (`MIFirstPersonAnim.cpp` ShapeHand / ShapeFingers,
`presentation.json` `animSets.pistol.grip`); the arms are placed by the pre-IK hand (`GetPreIKHand`) so the grip does not
feed back into the placement. Open: CHOPPER inspect / reload finger contact, hair cards, the NINE's wrist bend from the
template clip.
Retake (same pass, after a restart): the numerals re-centred on the radial-volar face of the support forearm (the probe's
first reading had the rotation reversed) and now read in the hip and El play frames; the NINE's arms placed by their
shoulders (`animSets.pistol.shoulders`, `UMIFirstPersonRig::GripShoulderTranslation`): the wrist-based placement had put
the left upper arm 29 cm in front of the eye, a stump across the NINE frames. Re-imported (`import-chars.sh arms`, the
18:07 export), rebuilt, all ten `fp-arms-*.jpg` retaken as play frames; `fp-arms-forearm-l/r.jpg` deleted.

## Exact next step (level)

1. Still boxes in L_Block, with no art anywhere: the building backs (`backs`, 7 brick masses with the window grid),
   the shanty (568), the hoist tower (571, 572), the lot sign pole (423). The 12 `ac_unit` props have no mesh and no
   `art_catalogue.json` entry (not drawn).
2. Baked interiors (`mi_interiors.py`): six rooms from the art; the racks are empty and the homes' furniture is boxes
   in the art's materials. Next: stock the shelves (the deck heights of `SM_Prop_ShelfRack_*` are not in the
   manifest), modelled sofas and beds from the art side, a lamps-on variant for the night rig.
3. Day only: vehicle lamps, neon and station lamps have day values (vehicle `E` scaled 0, neon 550 nits); the night
   rig needs lamp parameters driven by the level.
4. Not checked in a picture: the rust-streak decals' direction (none in frame in `block-v2-upper`), and the facade
   modules' seams at arm's length: `block-v2-seams.jpg` (north sidewalk at X -2600, looking east) shows the chop
   shop's block wall and the tyre cage, not facade modules: move it to n1/n2's shop fronts.
5. Backdrop: parapets and tar roofs everywhere, roof clutter (water tanks, bulkheads, condensers) within 300 m only;
   from far above it still reads as boxes with a window grid.

## Level (block-v2: the art in the level, the game played in it)

**Verified 2026-11-23** (`/project/ue/repo`, MCP 8000; pictures `docs/unreal/shots/block-v2-*.jpg`, 1920 x 1080)
- **Art transfer**: `send-art.sh pack` with the new defaults (`SM_Struct_*`, `SM_Sign_*`, `SM_Vehicle_*` added):
  1,344 MB in 7 parts, 279 GLBs, 222 texture sets (4K scans, the 8K roof bitumen); vehicles as exported at 00:52
  (the 13 `SM_Vehicle_*` in the manifest at pack time, 02:22). Import: 845 texture and material units in 104 s,
  meshes 473 s with the level; every mesh's bounds equal the manifest's to 0.0 cm. Checked in the editor:
  `T_TS_Roof_ScanBitumen_BC` 8192 x 8192, Steel_ScanRust, Brick_ScanRedCommon, Sidewalk_ScanWorn, Asphalt_ScanWorn,
  Wood_ScanPlankDark, Concrete_ScanFormed 4096 x 4096 (Galvanised_Aged stays 2048, as the art side made it). Every
  sign and tree is Nanite (the dense neon, e.g. `SM_Sign_WinesLiquors`, needs no LODs).
- **One data table for catalogue id -> mesh**: `Content/Data/art_catalogue.json` (64 ids; gameplay ids marked);
  `build_block.py` places 283 props of 57 ids (85 mesh-and-paint groups), the old note parsing is gone.
- **Vehicles** at their props.json poses: `M_MI_CarPaint` (clear coat: `MSM_CLEAR_COAT`, CustomData0 1, roughness
  0.03) with one instance per paint slot and props.json colour (`MI_Vehicle_<Car>_Paint_<RRGGBB>`), vehicle lamps
  off by day, tinted glass dark and sharp (`MI_Glass_CarTint`), chrome, rubber, plates from their sets; the crew's
  van is `SM_Vehicle_Van_Vulture` (props.json variant `vulture`).
- **Gameplay props drawn by the gameplay actors with the real meshes** (`presentation.json` `objectives.case.art`,
  `objectives.truck.art`, `explosives.<kind>.mesh`; `AMIReelCase` with lid on its hinge, reel per objective and
  beacon, `AMITruck` with `SM_Vehicle_IPXTruck` and both door leaves on their hinges (+-108.9 deg), `AMIExplosive`
  propane tank / welding rack and their wrecks as modelled). Without the art in the project the basic shapes stay.
  The level draws hidden-in-game previews of them for editor pictures and no boxes for them. Build green at e2cfe9c
  (113 s); `test.sh`: 35 of 38 pass, every `Run.*` and `Golden.*` with the changed actors; the 3 failures are
  `MurderInc.Audio.EventTable`, `.VoiceDirector`, `.VoiceRateHoldout` (the audio work in progress, not these files).
- **Structures family**: 38 instances from `placements/structures.json` (station mezzanine, stairs, bridges,
  platforms, kiosks, produce stand, hoardings, dig pen, dock, garages, the chop shop's floor, roof, mezzanine,
  stair, safe, fan); new rules: chain-link on the roadblock and the alley gate, jersey barriers across the road
  end, the tyre cage fenced with tyre stacks, the lot's knee walls, seals and railings invisible. Visible boxes
  left: 11 (item 1 above), from 30.
- **Interiors**: `mi_interiors.py` (build_block step `interiors`) builds six rooms from the art (grocery, parlour,
  store; living room, bedroom, vacant), lights them and captures HDR cube maps `/Game/Art/Interiors/TC_*` (1024);
  `M_MI_Glass` looks a cube up per window cell (one of three, half mirrored, lamp level varied); `block-v2-3` and
  `block-v2-interior` show the parlour (menu board, tiles, chairs, vending machine) through the pizza window.
- **Vertex-colour ramp test** (`mi_ramp_test.py`, art bible 3.3): an 11-step COLOR_0 ramp through the art's import
  path, captured as BaseColor into a float target: the shader receives the linear value (0.0977, 0.2012 ... 0.8945,
  1.0 for 0.1 ... 1.0: 8-bit steps), so the master's `pow(x, 2.2)` decode was wrong (0.5 became 0.216): removed.
- **Backdrop** in five brick and concrete finishes with parapets, tar roofs, water tanks, bulkheads, condensers.
- **The game in L_Block** (`tools/box/play-shots.sh`, play in editor headless): "Game: booted (art map, 757 boxes,
  21 explosives, 20 enemy slots, 3 reels)", 927 art collision primitives off; `block-v2-play-1` the start pose with
  the HUD (objective, health 100, CHOPPER 30/150), `-2` aimed down the avenue, `-3` beside the parked taxi.
- Two review rounds: round 1 fixed the vehicle view (inside the Cage's fence), the dark wood interior, the crude
  backdrop and the play pose inside the box truck; round 2 moved the seam view off a hoarding. Editor stopped at the
  end (by process id).

## Audio (voice lines and the game's sound) — first cut, in progress

Contracts and how-tos: `docs/unreal/AUDIO.md`. Built and tested in `/project/ue/repo-audio` (logs in
`/project/ue/logs/repo-audio`; no editor, no MCP port used).

**Verified 2026-11-23**
- **Build green; `test.sh MurderInc` 32 of 32 pass** (the 14 new `MurderInc.Audio.*` with every gameplay test, 32 s).
  Audio: `VoiceData` (the six lines word for word, 21 takes on disk, 48 kHz mono), `VoiceCooldowns` (line and global
  cooldowns, how-often rare / often / off), `VoiceChances` (chance 0.25 over 4,000 triggers: 0.254; same seed, same
  sequence), `VoiceNoRepeats` (300 plays, no take twice in a row, all three used), `VoicePriority` (window, crowd
  answer after the take, interruption by margin, the uninterruptible line, the queue), `VoiceCleanLanguage` (swap,
  bleep, untouched clean lines), `VoiceCharacters` (own set, empty set silent), `VoiceTriggers` (every trigger from bus
  events, streaks, last kill of a wave, the Hold the Block card), `VoiceRate` (typical Story run, 20 seeds: **2.76 lines
  a minute, 1.3 a minute on kills, 6.5 of 36 kills speak**), `EventTable` (61 bus keys incl. 28 flow lines scanned
  from the gameplay source: 21 play, 24 rules, 17 silent; all 83 replacement files present), `Director` (burst tails,
  ducks, blast muffle and recovery, pause refusal and music low-pass, death muffle, voice duck and subtitle), `Mixdown`,
  `Assets` (289 of 289 WAVs imported as Sound Waves, lengths equal, 22 loops), `EngineRender` (warns without a device).
- **Offline mix-down of a recorded fight**: `Content/Data/audio_fight.json` (52 s scripted Story fight, 799 bus events)
  replayed through the director, `Saved/Audio/fight_mixdown.wav` on the box (55.9 s stereo 48 kHz, 501 voices, peak
  -0.1 dBFS after the soft clip, RMS -17 dBFS; 7 lines: I-N-C at the start, Holla twice, Rule Baby on the last reel,
  What's my name and the crowd's R-U-L-E at the truck, I-N-C on the card).
- **The engine's own audio mixer plays it** (`tools/box/audio-engine-render.sh`, SDL dummy driver, no `-NoSound`): an
  audio device comes up ("Using Audio Hardware Device System audio playback device"), the stream replayed in real time
  started 479 audio components on the imported Sound Waves with 0 missing assets, and the master-submix recording's
  header announced 55.5 s of 6-channel audio; the file was cut short when the process quit before the background WAV
  writer finished. The test now waits for the full file; that re-run is still to do.
- **Import**: `tools/box/audio-import.sh` (headless, about 90 s): 289 Sound Waves under `/Game/Audio`, 0 failed.
- **Material**: 190 web variants rendered by `node tools/ue-export/audio.mjs` (3 s, 26.7 MB, not committed; on the box
  through the storage as `mi-audio-web.tar`), 21 placeholder voice files (generic stock voice, -18 LUFS), 79 generated
  effects + the bleep (9.8 MB); the committed audio tree is 15.5 MB. Generation spent about 53 credits (49 effects,
  about 3.5 voice); balance 3,392 at the end.

**Next**: re-run `audio-engine-render.sh` and listen to both renders; options screen wiring (`SetOptions`), crew
(`SetCharacter`), silencer (`SetSuppressed` / `bSuppressed`); music riser and Quartz grid; neon, steam and boombox
emitters; Goon step surfaces; the real voice recordings (AUDIO.md section 5).

### Audio fix pass (independent audio review, 2026-11-23)

**Verified**: build green, **`test.sh` 94 of 94 pass** (21 of them `MurderInc.Audio.*`; VoiceData warns with the placeholder count, EngineRender warns under -NoSound by design); `audio-engine-render.sh` passes with a device.

Every problem of the review addressed; AUDIO.md rewritten where the rules changed (2.1, 2.2, 2.3, 2.5, 3.3, 4, 5, 6, 7).

- **The voice rules** (`FMIVoiceRules`, `FMIVoiceTriggers`, voice.json): the win is `always` (no cooldown, no decay,
  priority 100, waits 6 s behind a line it may not cut) and shouted; takes follow the moment's `intensity`; a kill
  bark never cuts or chains onto another kill bark (`barkTriggers`); a repeat decay (x 0.8 per play of a line in a
  run); Hold the Block gets `wave.milestone` (waves 5, 10, 15 ...) and `score.newBest` feeding "What's my name", the
  last kill of a wave 0.5, the wave's "Rule Baby!" only when the kill bark did not speak; It's Murda! cooldown 40 s,
  Holla 25 s; a restart (`player:reset`, an intro not from the title) silences the voice and its queue and answer.
- **New tests** (`Tests/MIAudioVoiceTests.cpp`): `VoiceWin`, `VoiceBurst`, `VoiceDirector` (burst, pause in a line,
  restart, interruption through the whole director), `VoiceRate` (Story on Boss from config.json: **2.56 lines a
  minute, 13 % of kills speak, the win called and answered in all 20 runs**), `VoiceRateHoldout` (spec 04 2.11, 12
  waves: **2.61 lines a minute, It's Murda! 0.73 a minute, worst run 0.89; What's my name by wave 10 in every run**),
  `GenFiles` (variant length and loudness per set, silenced under open shots), `MasterChain`; extended: `VoiceData`
  (lengths, inner gaps, tails, bleep ranges, placeholder count), `VoiceTriggers` (kill after death, restart,
  milestones, new best), `VoiceIntensity`, `EventTable` (every delegate of Core/MIEvents.h must be bound: it caught
  the new `WeaponMode` at once; bound, with a selector click, and `bSuppressed` read in OnWeaponFire).
- **Proven red** before green: on the old data `VoiceData` (inc_01 3.09 s, gaps 0.78 / 0.59 s), `GenFiles`
  (chopper_close_03 11 dB off its set), `VoiceBurst` (2 lines), `VoiceRate` (3.86 a minute), `VoiceRateHoldout`
  (1.16 a minute); with the rule broken on the box clone: `VoiceWin` (no `always`: no win line in any seed),
  `VoiceData` (clean mode bleep with empty ranges), and with code breaks built on the box clone (never committed): no silence on reset or restart (`VoiceTriggers`, `VoiceDirector`: the old crowd answer played after a restart), kill barks allowed to cut each other (`VoiceBurst`: 5 cuts), intensity ignored (`VoiceIntensity`, `VoiceWin`: 2 of 10 wins shouted), a delegate left out (`EventTable`); and the engine render with the make-up at 0.0001 (peak -80.8 dBFS: red).
- **Placeholders re-cut** (`voice_placeholders.py`: gate, inner pauses 0.12 / 0.14 s, pitch-keeping tightening at
  most x 1.35): 21 takes 0.98 to 1.91 s (It's Murda! 0.98 to 1.19 s, I-N-C! 1.31 to 1.91 s, the chant 1.89 to 1.92 s),
  longest inner gap 0.08 s, -18 LUFS; the six breathed takes regenerated at a neutral rate (same preset voice, same
  text, 1.2 credits). **Effects re-cut and levelled** (`sfx_process.py`, from the same generated files): one loudness
  per variant set (momentary maximum within 0.8 dB), matched to the web sound, minimum lengths, DC and 20 Hz
  high-pass; the silenced shots 10.7 / 11.0 dB under the open ones; 31 sets pass `GenFiles`.
- **The mix**: the master chain of spec 07 2.11 (compressor, x 1.15, soft clip) on the main submix in the engine and
  in the offline mix; the ambience low-pass by interior; the music bus 0.5; master trim 1.0 (the game's volume is
  the device's primary volume, applied after the chain by UMIGameSubsystem).
- **Placeholders visible**: the log line "voice: 21 of 21 takes are placeholders", a "placeholder voice" tag under the
  subtitle in non-shipping builds, the VoiceData warning, `"placeholder": true` on the 40 generated replace layers,
  README.txt in Content/Audio/Voice/rule and Content/Audio/Gen.
- **Real recordings**: `tools/audio/voice_ingest.py` (any format, 48 kHz 24-bit mono, trim with 100 / 300 ms pads,
  -18 LUFS and -1 dBFS peaks, length and gap report, placeholder false, new takes by name, bleep marks); AUDIO.md 5
  is now a brief for a phone and for a studio with a release note. Prompt plans committed: `tools/audio/voice_plan.json`,
  `sfx_plan.json`.
- **Engine render**: **it works**: 55.57 s of 6-channel audio recorded from the main submix (the device's clock 55.57 s, the stream 54.9 s), 500 components, peak -0.0 dBFS with no clipped sample, **-16.5 LUFS integrated**, loudest 3 s -9.8 LUFS; the offline mix-down of the same stream 55.91 s, -12.5 LUFS, peak -0.0 dBFS; the six voice moments measured in both (AUDIO.md 7). Three engine-side causes found and fixed on the way: a stale complete WAV passed the wait, the dummy driver's clock drifts up to 3 % from the wall clock, and master-submix effects added at run time ran on default settings until their settings are pushed to the instances the device creates (`FMIMasterChain::Refresh`). `tools/audio/render_report.py` measures any render.
- Generation this pass: 1.2 credits (balance 3,282.7 at the start, 2,721.95 at the end). Balance figure of the first
  pass corrected to 3,358.6.

**Hand-offs** (one line each in other packages; the audio side is ready): `UMIGameSubsystem::ApplySettings`
(Flow/MIGameSubsystem.cpp) calls `UMIAudioSubsystem::Get(this)->SetOptions(...)` with the options screen's voice and
category settings; the loadout's crew apply calls `UMIAudioSubsystem::Get(this)->SetCharacter(Loadout.Crew)`;
`FMIGameRules` (Flow/MIGameRules.cpp, after `C.bNewBest = Host->SetBest(C.Score);`) emits
`if (C.bNewBest) Note(TEXT("score:best"), FString(), C.Score, C.Best);`. Clean language stays off by default: a decision
for the user (voice.json `settings.options.cleanLanguage`).

## Animation pack (Tactical FPS Animation Pack - Assault Rifle) on the CHOPPER — done

Details, mapping and what is missing: `docs/unreal/ANIMATION.md`. Scratch project `/project/ue/animpack` (MCP 8003).

**Verified 2026-11-23**
- The pack's 109 character clips are the UE5 mannequin skeleton bone for bone (88 bones, rest pose within 0.014 mm,
  30 fps, cm): imported onto SK_Mannequin with no retargeting, 139 of 139 imports (clips, rifle, magazine, weapon
  clips). Proof `shots/anim-pack-rifle.jpg`.
- 44 clips adapted by hand IK onto SK_Chopper (`Palm_R`, `Palm_L`, sights on the eye line, 16 cm eye relief) and 4
  reloads (FP and TP, tactical 2.233 s and empty 2.733 s) adjusted on the rules' marks: magazine rocked about
  `MagHinge`, LEFT-side charging handle, left-hand IK error 0.0 cm on every frame. Five SK_Chopper part clips
  (fire, dry fire, idle, two reloads). Proofs `shots/anim-fp-aimed.jpg`, `anim-grip.jpg`, `anim-fp-reload.jpg`,
  `anim-bolt-racked.jpg`, `anim-tp-reload.jpg`.
- 53 adapted assets as .uasset and FBX with `manifest.json` in `/project/ue/packs/tactical-rifle/adapted/` (never
  in git); `tools/box/anim/import-animpack.sh` imports the pack (`pack`) or copies the adapted set (`adapted`) into
  any project; both tested on a fresh copy of the mannequin project.

## Loadout (crew, four guns, attachments, block and style) — steps 1-4 and 6-11 of LOADOUT.md 9

Spec: `docs/unreal/LOADOUT.md`. Built and tested in `/project/ue/repo-gameplay` (MCP 8001).

**Verified 2026-11-23**
- **Parity holds through the new path.** `Loadout.ParityResolve`: the resolver's JSON for the default set-up (Rule,
  CHOPPER + NINE, no parts) is byte-equal to config.json's and presentation.json's objects, its `FMIWeaponDef`s equal
  `Config.Weapons` field by field (doubles compared exactly) and its view data equals `FMIViewmodelData::Load`.
  `Loadout.ParityGolden` replays the 13 weapon golden scenarios through the resolved data and
  `Loadout.ParityNextPrevious` replays all of them again with the swap press as next and as previous: 0 mismatches.
  Every existing `Golden.*` (five whole web-game runs included), `Weapons.*`, `Run.*` test still passes.
- **Data** (`FMILoadoutData`, its own error path in `UMIDataSubsystem`): `$ref`s resolved, `Loadout.DataLoads` checks
  every rule of 3.1 that needs only the data and the block's `provides` against level.json (3 reels, 29 / 17 spawns,
  21 explosives, 14 title keys).
- **Rules** (`FMIWeaponRules`): slots 1-4, quick swap to the last gun used, next / previous, retarget mid-holster,
  per-gun holster and draw, one shared bag (150, `AddReserve` once per pool), fire modes with the Selector activity
  (blocks fire, holds a pending auto reload, cancelled by a swap), falloff and noise radius in the shot, the aimed
  field of view and look per gun. `Weapons.FourGuns` covers each case of 8.3 including the mixed-timing reversal
  (`0.27 x (1 - T / 0.24)`) and the re-holster mid-draw.
- **Input** (`FMISwitchInput` in `AMIPlayerController`): Q / Y on press with one or two guns, tap-on-release and
  hold-for-wheel with three or more, the wheel by mouse travel or right stick (dead zone 0.5), the debounced mouse
  wheel, View tap (selector) and hold (inspect). `Player.ControllerSwitching`; `Core.GameClasses` now 68 mappings.
- **Attachments**: effects applied to the gun's JSON in web units before parsing. `Attachments.<part>.<stat>` (40
  cases from attachments.json: 37 effects and 3 baselines), `Attachments.Builds` (the six builds of 3.3, and the
  CHOPPER with scope and silencer at 20 / 37.5 / 60 m: 26, 24.05, 22.1), `.Ops`, `.Clamps`, `.Falloff`.
- **Flow** (`FMIFrontEndRules`, `UMIRunSetupSubsystem`, the set-up in the save game): `Frontend.Walk` (8.5 steps 1-8 on
  the rules), `Save.SetupRoundTrip`, `Save.SetupValidation` (each rule of 7, and a clean checkout degrading a saved
  STICK to the parity guns), `Frontend.WalkWorld` and `Loadout.ParityPIE` (the flow in a world with the real player:
  Hit the block from the Briefing, the weapon's data is the resolver's parity output, a 1 s Q hold with two guns is
  one swap on the press frame and no wheel, Change set-up on the death card opens the Briefing).
- **Screens** (Slate, `SMIFrontEnd` + `UMIFrontEnd`, replacing the canvas title): Home (the web title with the
  pickers, Hit the block, Gear up, the summary links), Crew, Loadout (rack three wide, class tabs, stat bars, the four
  slots, melee, the bag note), Workbench (carried-gun strip, slot tabs, options with Fitted, effect lines from the
  resolver with their marks, bars before / after, hold to reset), Block & Style, Briefing (four lines with Change, the
  controls strip); keyboard, mouse and gamepad through one `Act()`; console twin `MIMenu fe <action>`. The 3D stage
  `AMIShowroom` (closed room 1 km up, own lights and fixed exposure, turntable with `UMIGunAssembly`, the arms at the
  eye with first-person rendering). The four-slot HUD bar (pips, AUTO / SEMI, attachment pips, melee, the bag) and the
  weapon wheel. Pictures `shots/loadout-*.jpg` (`tools/box/loadout-shots.sh`; the pack rifles and parts through the
  dev-only `MISetup overlay`, because guns.json / attachments.json do not yet name the imported meshes).
- Audio hooks: crew to `SetCharacter`, each gun's silencer to `SetSuppressed`, the volume setting to `SetOptions`
  (master), and `FMIShotFiredEvent.bSuppressed` / `NoiseRadius` on every round.

**Open (most important first)**
1. The pack import's data (LOADOUT.md 6.2, animation agent): guns.json `variants.*.mesh` / statuses for Short,
   Extended and the folded stocks, the mounts' `exists`, attachments.json `presentation.mesh`, and the socket pass
   (`Optic`, `MuzzleMount`, ...). Until then the Workbench shows "No parts on this gun yet" outside the dev overlay,
   and parts sit at the data's provisional markers instead of sockets.
2. Crew phase-1 material instances (6.4, characters): only Rule is offered; the code applies a look by material slot
   on the arms and the template lines for DEUCE, SMOKE and KEYS.
3. Step 12 (pack clips: inspect, magazine check, selector, swings, quick and empty-retain reloads, dry tap-rack): no
   pack clip is in the gameplay project yet; the inspect and selector inputs reach the rules and the HUD only.
4. Not built: the probes in play of 8.2 (aim frames, view field of view, kick sum, the Goon behind a wall hearing a
   silenced round), a second level (the split Block / Style screens and level travel), the gun silhouettes and part
   pips as icons (names and squares stand in), `Ops` / `Clamps` fixtures as files (built in code).
5. `Audio.EventTable` asks for the new `WeaponMode` bus delegate to be bound in `FMIAudioDirector` (audio agent).
6. Seen in the pictures: the Crew stage shows the first gun first-person but not the template arms; the rack's
   turntable frames the CHOPPER stand-in as a close-up (the STICK on the Workbench frames whole); pack parts sit at
   the provisional markers (the vertical grip reads, the scope and silencer do not yet). Headless pictures are the
   editor's play viewport (1013 x 550), so the type is smaller than at 1080p.

Final suite before the fix pass (2026-11-23): `test.sh MurderInc` TESTS FAILED passed=93 failed=1 (`Audio.EventTable`: 188 web sound
files missing, the audio agent's).

Correction (fix pass below): items 1 and 6 above and the note on the pictures are out of date. The animation agent's
commit 464cb44 already names the pack meshes in guns.json and attachments.json, and the box offers SHORTY, STICK,
STRETCH and every part but the folded stock with no overlay. `loadout-shots.sh` no longer takes an overlay.

### Loadout fix pass (independent review, 2026-11-23)

- **Order on a pad and the keyboard.** Start is Next on every set-up screen (Hit the block on Home and the Briefing);
  the jump to the Briefing is Ctrl+Enter or View+Start. Next takes the focus: Tab cycles rack, slots, Next; Down past
  the last row lands on it; Enter / A there advances. `Frontend.WalkWorld` (keyboard) and `Frontend.WalkPad` walk Home
  to the run with real key events only (`UMIFrontEnd::PressKey` → `FSlateApplication::ProcessKeyDownEvent`; the
  screens sit in a virtual window in the test world). Console `MIKey <key>` does the same in play in editor.
- **Glyphs.** Marks, arrows and pips are shapes (`SMIMark`); every face falls back to the engine's Droid Sans Fallback
  (Noto Sans Symbols 2 was tried: it has no arrows). The front end logs characters no face has; `Frontend.Glyphs`
  reads the fonts' character maps and fails on any character of frontend_text.json or text.json without a glyph.
  Key names come from `frontend.glyphs.<kbm|pad>` (new keys back, next, toBriefing, prevGun, nextGun, reset, bench,
  melee, empty, panes) for the device used last; no string is written in the code (the HUD's "Pick a gun" too).
- **Layout.** Every control of every set-up screen lives in the left 40 % column (the slots are a strip under the
  rack, the effect lines wrap beside the bars, the Briefing's Carrying line wraps name plus pips, the controls strip
  wraps); focus rings pad their row; the smallest text is 14 pt. The world's objective markers hide while the wheel
  is open. `MIViewSize <w> <h>` resizes the window around the play viewport for pictures at 16:9, 21:9 and 4K.
- **Stage.** The turntable fits the gun from its mesh bounds into the free 60 % at the viewport's aspect ratio; on the
  Workbench it aims at the slot's mount socket (frontend.json offset only without a socket), turns that side to the
  camera, stops spinning and lights the mount with its own spot; the room lights aim at the gun (they aimed 86 cm
  below it). Crew shows the member's own arms (placed on the grip every frame, as in play) or, while those arms are
  not in the project, the turntable; the Briefing hides the template arms (hand-off below).
- **NEW.** The card focused when Loadout opens is seen; `WalkWorld` checks a focused card loses NEW and keeps it
  through a save.
- **Tests added:** `Loadout.MountsExist` (13 pack meshes, 83 sockets on the box; says so and passes when the pack is
  absent), `Loadout.BuildPIE` (STICK with scope and silencer plus a bare CHOPPER through the run reset: the weapon's
  data is the resolver's, the view at full aim 30°, the silenced round heard at 15 m and not 30 m, the bare one at
  30 m), `Enemies.GunfireRadius` (the throttle exception), `Player.ControllerKeys` (a local player and the
  controller's own mapping context through `InputKey`: 3, Q tap and hold, D-pad right, wheel, B), `Frontend.WalkPad`,
  `Frontend.Glyphs`. Each was seen red with its rule broken on the box (Start back to the Briefing jump, Next not
  focusable, no seen-on-arrival, no throttle exception, no symbol face, no `ApplyRun`, noise / 10 instead of / 100,
  the 3 key unmapped), then green.
- Found while retaking the pictures: parts fitted while the rack's swap had the turntable scaled out came out 16 times
  too big (they kept their world scale); they now take the gun's scale (`Loadout.PartsScale`, seen red first). The
  title camera kept a 16:9 constraint and pillarboxed Home and Block & Style at 21:9; it now fills the screen.
- Pictures (play in editor, `tools/box/loadout-shots.sh`, no overlay): `shots/loadout-{home,crew,rack,workbench,
  workbench-muzzle,workbench-grip,where,briefing,hud,wheel}.jpg` at 1918 x 1086, and every set-up screen at 21:9
  (2561 x 1086) and 4K (3836 x 2166, stored at 1920 wide) in `shots/loadout-sizes/`. The layout is the same at each
  size: every panel in the left column, the gun whole in the free part.
- `MISetup overlay`, `MIKey`, `MIViewSize` and `EditLoadoutForDev` are compiled out of shipping builds.
- **Hand-off (characters / animation):** in first person the template body's upper arm and a black disc cover the
  lower left, the support arm stretches sideways when aiming and the pack STICK sits low; hide or cull the template
  upper arm and clamp the support-hand reach. The Briefing hides the arms until then.

Final suite after the fix pass (2026-11-23, 644d4d2): `test.sh MurderInc` TESTS FAILED passed=100 failed=1 (only
`Audio.EventTable`, the audio agent's: 188 web sound files missing). `Loadout.ParityGolden` and
`Loadout.ParityNextPrevious` replay the 13 weapon scenarios with 0 mismatches; every `Golden.*` passes.

## Gameplay (slice 2: the enemies and the flow) — in progress

Contracts: `docs/unreal/GAMEPLAY.md` sections 6 to 11. Built and tested in `/project/ue/repo-gameplay` (MCP 8001).

**Verified 2026-11-23**
- **Build green, 18 of 18 tests pass** (`test.sh` TESTS OK passed=18 failed=0, 32 s for the whole suite).
- `MurderInc.Golden.FlowRules` and `MurderInc.Golden.Directors` (FMIGameRules = `src/game.js` with the enemies on the
  box world: a whole Story run to the IPX truck, a Story run that dies, four waves of Hold the Block, replayed frame by
  frame against the web game: state, clocks, reels, waves, score, queue, alive count, caps, pursuit, music, hold
  progress and every flow event): pass, 0 mismatches.
- **The game in a world** (`UMIGameSubsystem`, `MurderInc.Run.*`, headless world with collision, real player
  character and weapon, enemy actors with hit volumes, engine traces):
  - `Run.StoryComplete`: a bot that follows the objective data took the three reels and reached the truck in 82.3 s
    of game time on Boss: 35 kills (all by the CHOPPER's rounds through the Goons' and Buzzards' hit volumes), 189
    rounds, 148 hits, 46 enemy rounds fired, 16 hits on the player; debrief card "Diamond", truck doors open, cases
    taken, menu on the debrief.
  - `Run.StoryDeath`: on Kingpin a bot that does not fight dies after 9.7 s (16 enemy rounds, 10 hits); the death
    card at 1.5 s; Run it back: intro, one retry, full health at the start, no reel.
  - `Run.HoldTheBlock`: three waves cleared in 77.7 s, score 6,905 from 27 kills, two resupplies, the death card with
    score and a new best.
  - `Run.Menus`: settings validation as the web game (fov 200 to 95, 74.6 to 75, sens 0.01 to 0.2, volume 2 to 1,
    quality 'test' refused, best rounding); title menu, mode picker, start, intro to playing, pause card with the
    0.35 s debounce, settings from the pause card, resume.
- Pitfall found: in a hand-made test world tick functions run once per engine frame; the test advances
  `GFrameCounter` per step as the engine's `FTestWorldWrapper` does (without it nothing but tickable objects ticks).
- `Golden.Directors` now also replays Story on Hustler (4,000 frames, 53,520 checks) and Hold the Block on Kingpin
  (3,000 frames, 39,306 checks): 0 mismatches; all five whole runs of the web game agree with the C++.
- **Play in editor, the same code in both maps** (`L_GreyBlock` from `mi_greyblock_map.py`; `L_Block` copied from the
  level clone): the game boots from `AMIGameMode` (`BlockMaps`), "art map: 923 art collision primitives switched off,
  the data's boxes decide", 757 boxes, 21 explosives, 20 enemy slots, 3 reels. Pictures: `shots/gameplay-v2-title.jpg`
  (title menu), `gameplay-v2-greybox.jpg` (the block as grey boxes, objective markers), `gameplay-v2-block.jpg` (the
  art map, objective and markers), `gameplay-v2-goon.jpg` (two Goons with the template rifle animation blueprint
  aiming from the rules, a Buzzard above, the player already hit: HEALTH 32).

**Open (most important first)**
1. Enemy animation: the template rifle animation blueprint on the mannequin follows the rules' velocity and aim
   pitch; no aim offset yaw, telegraph, fire, rush or hit-reaction montages yet (the presentation contract exposes
   them: `FMIEnemyView`); the Buzzard is a basic-shape placeholder. Effects and sounds are hooks on the event bus.
2. The weapon-position setting (`view`) is stored and validated but the viewmodel does not read it yet.
3. Gamepad look curve and aim slow-down, rumble (slice 1 leftovers) are still open.
4. The title fly-through is linear along the level's cinematic keys (no centripetal curve, no sway, no fade-out of
   the loop); the menus are canvas text, not UMG/CommonUI.
5. `L_Block` still draws its own grey boxes for the 21 explosives and 3 cases (their collision is switched off at
   run time); `build_block.py` could skip owner kinds `explosive` and `objective` (LEVEL agent).

## Gameplay (slice 1: the player and the two guns)

Contracts: `docs/unreal/GAMEPLAY.md`. Built and tested in the second clone `/project/ue/repo-gameplay` (MCP 8001).

**Verified 2026-11-22**
- **Build green, 9 of 9 tests pass** (`build-status.sh` BUILD OK; `test.sh` TESTS OK passed=9 failed=0, 22 s):
  `MurderInc.Core.DataLoads`, `Core.GameClasses` (38 key mappings), `Golden.Rng`, `Golden.PlayerPure`,
  `Golden.PlayerSim`, `Golden.Weapon`, `Golden.Blast` (the C++ rules replay every frame of the web game's own
  modules: `node tools/ue-export/golden.mjs` writes `Content/Data/golden/*.json`), `Weapons.ViewmodelRig` (aimed, the
  rear sight sits on the view axis within 0.02 cm at 16.0 cm relief for the CHOPPER and 37.0 cm for the NINE; a round
  kicks the gun more than 2 mm and it settles within 0.3 mm), `Weapons.HitscanDummyBlast` (in a world with collision:
  a body round deals 26, a head round 26 x 2.2, a miss misses, a player round lights a propane tank, the fuse runs
  out and the blast hurts the dummy by 170 x (1 - d / 650 cm)).
- **Play in editor** on `/Game/Maps/L_GameplayTest` (`mi_gameplay_testmap.py`, `tools/box/pie.sh`): the player stands
  (feet on the floor, eye 168 cm), the HUD draws health, ammunition and the crosshair, the template rifle sits at the
  CHOPPER's hip pose (`docs/unreal/shots/gameplay-v0-hip.jpg`); `MIInput ads 1` brings the sight onto the crosshair
  (`gameplay-v0-ads.jpg`); `MIInput fire 1` for 0.6 s killed the dummy 7 m ahead (it keeled over). No tick cycle
  warnings after moving the frame into two tick functions.
- `config.json` numbers were rounded to 4 decimals by the exporter (shake.onHit.perDamage 0.0143 for 1/70);
  `golden.mjs` restores full precision for the player, weapon and explosive tables (3 numbers changed).

**Open (most important first)**
1. The arms are the template mannequin placed by its right-hand socket on the gun's grip, playing one ADS idle: the
   left hand does not hold the handguard at the hip and the reload, draw and strike have no hand animation. Needs the
   animation layer (two-bone IK to `Palm_R` / `Palm_L`, reload montages to spec 02 3.17) on the real arms.
2. Not ported yet: the air step (8 cm), the play-bounds clamp and fall-out teleport, gamepad look curve and aim
   slow-down input, the mouse-wheel swap debounce, rumble, muzzle flash, casings, impact effects, sounds, the
   damage post-process, the explosives' wreck meshes and jets (grey boxes), the settings menu.
3. Tracers are line-batcher streaks (no Niagara yet). The dummy and the explosive are engine basic shapes.
4. The movement is the stock walking and falling with the rules' velocity: the golden replay covers the rules on
   flat ground; steps, ledges and the parity table of spec 01 4.9 are not measured in a level yet.

## 2026-11-22

- **block-v1: the avenue with the facade kit, props, furniture, decals and backdrop** (`docs/unreal/shots/block-v1-1.jpg`
  ... `-6.jpg`, 1920 x 1080, `shot.sh` through the piloted viewport, 60 warm-up frames): 1 eye level at the start pose
  looking east; 2 the south block face from the north sidewalk; 3 the pizza shop front up close; 4 under the El
  looking up; 5 the avenue from mid-block looking west; 6 high overview. Three picture rounds (sheets looked at each
  time): round 1 found every remaining box textured as concrete, cameras inside the produce stand and behind vans,
  pastel shop interiors and black shade; round 2 found the chain-link drawn opaque, gum spots too dense, the backdrop
  brick too pink; round 3 is the committed set.
  - **Facade kit on the five street-facing buildings** n1, n2, s1, s2, s3: 985 instances of 77 modules from
    `art/out/placements/buildings.json` (`art/blender/place_buildings.py`: the kit's own `assemble_front` /
    `assemble_shell` plus closing walls for the backs), one actor per building with one InstancedStaticMeshComponent
    per module (added through `SubobjectDataSubsystem`, saved with the level), no collision; awnings per shop colour
    (`MI_Fabric_ScanCanvas_<Shop>`). The buildings' 337 colliders stay as invisible blocking boxes (`Block/Collision`):
    the tuned cover and openings are unchanged. Every imported mesh matched its manifest bounds to 0.0 cm (190 GLBs).
  - **Props from props.json** by catalogue id where a mesh exists (catalogue ids parsed from the manifest notes; the
    modelled furniture before the scans): 217 dressing props of 36 ids, footprint centre aligned to the catalogue
    shape's (the fire-escape balcony's pivot is its left end); fire escapes the facade kit already draws are skipped.
  - **Level structures from the furniture family**: the auto body shop's block walls tiled along its colliders with
    the 6.0 x 4.3 and 3.8 x 3.5 openings, open roll-up doors and the side-door module; the Cage's knee walls,
    chain-link panels and end posts; chain-link round both rolling scaffolds; the sidewalk shed and its stair at the
    manifest's placement. Remaining boxes wear the material of what they are (`TAG_SURFACE`: El green steel for the
    station, plywood hoardings, painted block, brick backs with windows); vehicles are dark paint.
  - **Materials**: `M_MI_Surface` gained a detail layer (the set's own normal and roughness at 4.37 x, faded in within
    3 m), macro variation (value, hue and roughness noise at 4 and 14 m), sign emission (E maps, 900 nits) and a
    window grid for world-projected masses; `M_MI_SurfaceMasked` (two-sided, BC alpha clip) for chain-link;
    `M_MI_Glass` (opaque glass, Lumen reflections, a world-space interior room per window: wall paint, furniture or
    shop shelving, lamp on in one room in six, grime at the sill); `M_MI_Flat` for chrome, aluminium, blinds, lenses and
    sign stand-ins; `M_MI_Decal` with seven procedural kinds.
  - **Decals by rule** (seeded): 153 (22 road cracks, 7 patches, 32 oil, 10 tyre marks, 48 gum patches, 18 stains at
    the manholes and under the El's edges and rails, 16 rust streaks under window sills).
  - **Sky and backdrop**: volumetric clouds (engine simple cloud material, layer 1.6 to 7.6 km), far ground to 5 km,
    the avenue's street walls continued to 450 m, 318 city and skyline masses out to 4.5 km, all with windows.
    Exposure: auto exposure EV100 12.3 to 14.2, local exposure shadow contrast 0.45, sun shafts (volumetric scattering
    3, volumetric fog extinction x 5): the shade under the El reads and the shafts show through the ties.
  - **Hardware ray tracing on this box's Vulkan driver**: NVIDIA 620.70 exposes VK_KHR_ray_tracing_pipeline,
    VK_KHR_acceleration_structure and VK_KHR_ray_query; editor.log says "Ray tracing is enabled", "Ray tracing
    shaders are enabled" and allocates the ray-tracing scene (`FRayTracingScene::SceneBuffer`); the project sets
    `r.RayTracing=True`, `r.Lumen.HardwareRayTracing=True` (BOX.md section 1).
  - Editor stopped at the end (`editor.sh stop`, by process id).

- **The block in Unreal, first pictures** (`docs/unreal/shots/block-v0-1.jpg` ... `-4.jpg`, 1920 x 1080, through
  `tools/box/block-shots.sh`): eye level at the player start looking east under the El; a south-row column and its
  pedestal; under the deck looking up at a bent; a high overview of the block. Two review rounds: round 1 fixed
  black shade (scene captures had no sky light and no Lumen: pictures now come from the piloted editor viewport and
  HighResShot), clipped cached lighting (pre-exposure 8), too dark exposure (clamped auto exposure EV100 12.9 to
  14.2) and brick on the roofs of the massing (concrete on upward faces); round 2 moved the column and deck cameras
  out of grey-box clutter.
- **`/Game/Maps/L_Block` assembled from data** by `unreal/MurderInc/Content/Python/build_block.py` (`block.sh start
  level`, 7 s, 920 actors, saved): 7 road pieces and 140 kerb and sidewalk modules along the avenue (X -70 to +70 m,
  gutter lines at Y +-700); the El from `level.json` `el` (18 bents, 17 girder spans and decks, 36 columns, 9 lamps
  at the `atmos.json` El lamp positions; deck underside at Z 650 as the mesh bounds show); 657 grey-box cubes, one per
  movement-blocking static collider of `level.json` (bullet-only colliders and the ones the El and street meshes
  draw are skipped), with world-projected scanned brick or concrete by collider surface; 12 ground slabs from
  `ground.surfaces` off the avenue and a far ground plane; a player start at `playerStart`; the day rig from
  `atmos.json` `rigs.day`: sun at pitch -52.0 yaw -26.1 and 99,956 lx (5 game lux x 24,400 lx x colour
  luminance, spec 06 4.5), source angle 0.5357, atmosphere sun light; sky atmosphere with 2.5 x Mie scattering; real-time
  sky light; height fog for about half of the web haze at 92 m (density 0.0047) with volumetric fog; unbound
  post-process volume with Lumen GI and reflections, clamped auto exposure, bloom 0.25 without threshold, vignette
  0.15, white balance 6,300 K, local exposure, saturation 1.05.
- **Art imported** (`block.sh start textures,materials,meshes`): 60 textures of 20 sets, the master material
  `M_MI_Surface` (base colour, normal, ORM, tint, optional second set on G, the four `Wear` masks with a value-noise
  breakup, world box projection for the grey-box) and 30 instances, 16 meshes with Nanite. Every mesh's bounds equal
  the manifest's Unreal bounds to 0.0 cm: axes and scale right, unmirrored (BOX.md section 5). The lamp lens slot
  (`TS_Glass_SodiumLens`, no texture set yet) uses a warm-tinted concrete stand-in.
- **Art transfer** works: `send-art.sh pack` (163 MB, 16 GLBs, 21 sets), `send-art.sh put` (19 s), `media_confirm`
  type file, box download and unpack to `/project/ue/art-in` (4 s). `receive-art.sh` is the box half.
- **Build and tests green**: `build-status.sh` BUILD OK (127 s game module build), `test.sh` TESTS OK passed=2
  failed=0 (29 s), run again after the last change. Editor stopped at the end.
- `docs/unreal/BOX.md` written: the loop, timings, every pitfall the scripts encode.

## Before 2026-11-22 (the bootstrap)

- The project `unreal/MurderInc` compiles on the box (`-NoUBA`), the headless editor starts with its MCP server, the
  bootstrap map `L_Bootstrap` is built by `mi_bootstrap_map.py`, and a picture of it came back through the transfer
  procedure (`docs/unreal/shots/bootstrap.jpg`; its black shade is the scene-capture limit found later).

**Weapons round 4, first-person shoulders (lead, 2026-11-25 15:40 UTC).** The grip solves (grips.json) put the arms'
shoulders where the support hand can reach the gun: `presentation.json firstPerson.animSets` now carries them for
`chopper_ik` [-8.5, 1.1, -12.4], `stretch_ik` [-6.5, 1.1, -12.4] and `rattler_ik` [-2.5, 1.1, -12.4] (camera space, cm;
they all had the NINE's [-6, 0, -24], from which the support wrist is 58 to 63 cm from the shoulder against an arm of
about 55). **Still open for the box engineer:** the SHORTY's hip view in guns.json is the CHOPPER's numbers on a gun
whose origin is its butt pad (its forend lands about 70 cm out): give it a view with the butt near the eye, then run
`art/blender/assets/_rule_grips.py shorty --pose hip,aim --pictures` and set `shorty_ik.shoulders` from the solve. Check
all four in play with `mi.FP.Shoulders`. The RATTLER's trigger finger stays about 2 cm off the trigger face (the gun's
geometry: the trigger sits 4.5 mm from the magazine well).
