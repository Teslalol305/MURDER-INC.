# Unreal rebuild: progress

What is verified on the box, newest first. Every entry says how it was verified. The loop and the pitfalls are in
`docs/unreal/BOX.md`.

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
