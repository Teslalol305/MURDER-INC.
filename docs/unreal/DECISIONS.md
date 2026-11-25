# Decisions from the user

Decisions the owner made during the rebuild. Each one wins over any older design text that says otherwise.

## 2026-11-23: the pack rifle stands in for the CHOPPER; the NINE stays

**Asked:** after three rebuild rounds, an independent critic still graded the game's own guns 2.5/5 (CHOPPER) and
2/5 (NINE). The rifle from the purchased Infima pack looked clearly better in the game. The user was offered four ways
forward: buy gun packs, generate source models, keep hand-building, or use the pack rifle.

**Answer:** "Use the pack rifle". The pack's rifle stands in as the main gun, and the NINE stays as it is for now.

**What this means for the build:**

- **The CHOPPER's rules stay the web game's.** Its id, slot 1, its fire rate, damage, magazine, reload stage times,
  recoil and everything else the golden tests replay are unchanged. Only its presentation changes.
- **Its mesh and clips become the pack rifle's.** The CHOPPER is drawn with the pack rifle in the **Short handguard**
  length, the closest to the CHOPPER's compact build. It uses the pack's own first-person and third-person clips
  natively, with no hand IK and no adaptation. The adapted `A_FP_Chopper_*` and `A_TP_Chopper_*` clips and
  `SK_Chopper` are retired from the game (kept on the box and in `art/` for reference).
- **It must still read apart from SHORTY.** SHORTY is the same Short-handguard rifle in the loadout. The CHOPPER gets
  its own material instance: a worn dark-earth or bronze-tinted finish on the receiver and handguard, plus the gold
  accent of the web game's palette where a small part allows it. Its loadout card and HUD keep the name CHOPPER.
- **Reload timing.** The web game's reload stage times stay the rule. The pack's Reload_Quick and Reload_Empty clips
  are played at the rate that lands their magazine-out, magazine-in and bolt marks on the rule's stage times, as
  `ANIMATION.md` describes for the pack rifles.
- **Attachments.** The CHOPPER may now take the pack attachments its Short variant supports. The default set-up still
  carries none, so parity holds.
- **The NINE** keeps `SK_Nine` as it is now (critic 2/5) and the template pistol clips. Better pistol art and
  first-person pistol clips remain an open item: a matching pistol pack is the recommended route.
- **Licence:** unchanged. Nothing from the pack is committed; the stand-in works on the box and falls back to the
  template rifle in a clean checkout.

## 2026-11-23: the game lives on the IPX.exchange Game OS website, streamed

**Owner:** "this game will live on the IPX.exchange Game OS website". Asked how, since Unreal Engine 5 cannot run
inside a web page, the owner chose **"Stream Unreal"**: the full Unreal build runs on cloud GPUs and is streamed into
the IPX.exchange page (Pixel Streaming), playable with keyboard, mouse or gamepad.

**What this means for the build:**

- The delivery target is a **Linux server build with Pixel Streaming 2**, not a desktop package. Everything else
  (art, gameplay, menus) stays as it is.
- The website embeds the Pixel Streaming player (a web component or iframe) in a Game OS page. The site's own code is
  not in this repository; the build provides the player front end, the signalling server and a matchmaker that hands
  each visitor a free game instance, plus the instructions for the site to embed it.
- Each concurrent player needs one GPU game instance (or a share of a large GPU). Hosting cost scales with players:
  measure instances per GPU and cost per player-hour, and write them down.
- Input and UI must work in a browser tab: pointer lock for mouse look, keyboard, gamepad through the browser, a
  click-to-start overlay, audio started on the first click, and graceful handling of a lost connection.
- Latency budget for a shooter: aim for under 80 ms from input to picture on a good connection; measure it.
- The demo playable route (`docs/DEMO.md`) is the first step of this: the same Pixel Streaming set-up, on the box.

## 2026-11-23: hosting the streamed game: a managed Pixel Streaming service

**Asked:** the rented GPU box cannot serve the public (it exposes only its own private desktop page and forbids
tunnels or extra servers), so where should the website version be hosted? **Answer:** "Managed streaming": a
Pixel Streaming service that hosts Unreal games and gives an embed link and auto-scaling (for example Arcware Cloud
or PureWeb). The owner creates the account and uploads the build we package; pricing is per streaming minute.

**Open technical point:** several managed services take only Windows builds, and Unreal cannot package for Windows
from Linux. The next job must check, from each candidate's current documentation, which ones accept a Linux build,
and say plainly if a Windows packaging machine is needed.

**Research result (2026-11-23, `docs/unreal/hosting_research.json`, independently checked):** Eagle 3D Streaming
(E3DS) is the only managed Pixel Streaming host whose own docs accept a Linux Unreal build, so no Windows machine is
needed. Free 60-minute trial with no card; Core $29/month with 300 minutes and 10 concurrent players; extra minutes
$0.10 (about $6 per player-hour); US and EU. Fallback: Amazon GameLift Streams on its Ubuntu runtime (needs an AWS
account and a small session backend; gamepads may not work there). Risks: our engine is Unreal 5.9 Preview 2, which no
host lists; E3DS does not test Linux uploads, so the first upload on the free trial is the real test; budget the cloud
build for 8 GB of video memory; read E3DS's terms for a violent shooter before publishing.

## 2026-11-24: E3DS Core plan

**Owner:** upgraded the E3DS account from the trial to **Core** (dashboard: 300 minutes a month, 10 GB storage
included, 10 players at once). Build `MurderInc` version 1 (the zip of 2026-11-24, sha256 `8378eedd…e570a`, 2.2 GB)
is stored and used by `Project_MurderInc`; 7.8 GB is free, so the fixed build fits beside it as version 2 with no paid
storage. Once version 2 streams, delete version 1 from inside the build (open the build's versions), **not** the
build row's trash icon, which deletes the whole build.

**Still true on Core:** as far as E3DS publishes, Core streams on the same server pool as the trial (RTX 4080 or
RTX 5070 class, 8 or 16 GB of graphics memory), so the game must still fit an 8 GB card with headroom. The owner was
advised to ask E3DS support whether the app can be kept on 16 GB machines.

**Retry on Core (2026-11-24, about 18:55 UTC):** the owner opened the link again on Core, with ten slots, so no
leftover instance could hold the only slot. It **crashed again**. The Chrome console showed only errors from the
owner's crypto-wallet browser extensions (MetaMask, Backpack and others competing for `window.ethereum`), which have
nothing to do with the game, plus E3DS's `SessionIDFound {savedSessionId: …}`. There were no game lines: version 1
writes no log. So the crash is consistent, not caused by one blocked slot. That points to start-up on E3DS's
servers: graphics memory, the driver failing Unreal 5.9's Vulkan SM6 check, or the way E3DS launches the app. Test
version 2 in a fresh **Incognito** window: no extensions and no saved session.

## 2026-11-24 (23:10 UTC): the owner's E3DS test of version 2, and what version 3 must do

**What happened.** Version 2 (zip `ceaf828d…`, launch options `-MICloudProbe=10 -PixelStreamingDecoupleFramerate`,
Browser Resolution Custom 1920 x 1080) **loaded and streamed on E3DS**: the start-up crash is fixed. The owner's
words: "the game is sticky i cant play it", "it loaded and the game was streamed from e3ds but it is not fluid",
"as of now the game looks much better but the playability and lag is a problem", and "make sure there is a path for
someone to connect a PS5 controller and play".

**Not known yet** (asked for; add below when it arrives): which GPU and driver the E3DS Linux machine has, the game's
own frame rate and GPU time there (the `[MICloud]` lines of the session log), the stream's frame rate and the region
in E3DS's Info panel. E3DS's documentation says its own datacentre has RTX 4080 and 5070, and its cloud machines are
"typically T4 or A10"; Linux machines are allocated on demand. A T4 is roughly a seventh of the box's GPU: the game as
packaged (Lumen with hardware ray tracing, Nanite, virtual shadow maps, 6 ms a frame on the box) would run there at
about 15 to 20 frames a second with several frames of queueing: that is what "sticky" and "lag" would feel like.

**What the owner decided, in effect (binding for version 3):**

1. **Fluid, responsive play comes first; the look comes second.** The earlier instruction "do not lower Lumen, Nanite
   or shadow quality" no longer holds when the machine cannot keep 60 frames a second: version 3 must adapt by
   itself to whatever GPU E3DS gives it (a T4, an A10, an RTX 5070 or 4080) and keep the game near 60 frames a
   second with low delay, at the best look that GPU can afford. On a fast GPU it keeps the full look.
2. **Delay between the hand and the picture is a defect to measure and reduce**, not a given: measure it through a
   real stream on the box (input sent, first changed frame received), with a fast and with a slowed-down GPU, and
   remove what the game and the engine add.
3. **A complete controller path**: a player with a PS5 (DualSense) or Xbox controller plugged into the computer must
   be able to do everything, from the CLICK TO PLAY card to the end of a run and back, without a keyboard or mouse,
   with the right labels on screen.
4. **A gameplay review through the stream**: somebody (an agent) plays a whole Story run and a Hold the Block run
   through a real stream on the box, with a mouse and keyboard and then with a controller, and fixes what does not
   work or feel right.

**Reproduced on the box, 23:25 to 23:40 UTC** (version 2's own zip unpacked to a scratch folder, the Development game
from it with a MIDemo script into a Story run, one viewer that turns the camera through the stream:
`tools/box/cloud/rtcinput.py`; logs and scripts kept in `/project/ue/cloud/lag-2026-11-24/`). The owner later added:
"the gameplay is very laggy; when the player turns it slows down; it is not a viable experience; we need to fix this
now."

| Run | Load on the GPU | The game's own frame rate, worst frame | Pixel Streaming capture | Frames received while turning |
|---|---|---|---|---|
| s0: 1080p, the owner's options (decoupled) | made GPU-bound with `r.ScreenPercentage 200` (GPU time about 38 ms) | 32 a second, **worst frame 4.2 s** | 1,056 "No frames available for capture ... Skipping", 264 "WaitForGPU: Timed out waiting for fence to be written!" | 22, then 10 a second |
| s1: the same without `-PixelStreamingDecoupleFramerate` | the same | 33, worst frame 1.8 s | 1,088 skipped, 256 fence time-outs | 16 to 18 |
| s3: the same as s0 with `t.MaxFPS 30` | not GPU-bound (GPU time 11 ms of 33) | a steady 30, worst frame while turning 33 ms | none | (4 to 7: see below) |
| s4: 1280x720 output, otherwise as s0 | not GPU-bound (GPU time 8 ms) | 59.6, worst frame while turning 65 ms | none | 30, then 44 to 49 |
| q0, q1: two copies of the game at once at 1080p | each GPU-bound (about 26 ms) | about 40, **worst frame 7.1 s and 7.2 s** | 654 skipped, 132 fence time-outs (q0) | 13 to 15 in the worst turns |

What this shows: **when the GPU cannot finish frames in time, Pixel Streaming 2's capture stalls the game**: each
captured frame waits up to 100 ms for a GPU fence (`UPixelStreaming2MediaIOCapture::WaitForGPU`, the same code in
`PixelCaptureCapturerMediaCapture.cpp`; `PixelStreaming2.CaptureUseFence` is on by default in 5.9), the capture
runs out of frames, and one game frame can last seconds. Turning costs more GPU time than standing still, so it is
what pushes a loaded GPU over. With head-room the same build is steady. `-PixelStreamingDecoupleFramerate` does
not cause it and does not cure it (it was this session's advice, from a measurement with a free GPU). The numbers
in the last column come from a Python client whose congestion feedback is basic: trust the game-side columns; get
sender-side figures with `-PixelStreamingLogStats` before drawing conclusions from received frame rates.

**Consequence for version 3:** the game must always leave the GPU head-room (adapt quality and resolution, and
lower its frame-rate target to 45 or 30 when it has to, rather than run GPU-bound), the capture settings must be
chosen by measurement under load (`CaptureUseFence`, `UseMediaCapture`, `DecoupleFramerate`, `WebRTC.Fps` equal to
the frame-rate target, `WebRTC.DisableFrameDropper`), and nothing may block a frame for more than a few
milliseconds while a run is being played.

**Correction, 00:20 UTC (2026-11-25): which runs were clean.** The gameplay engineer's stream tests ran on the same
GPU at the same time as runs s0, s1, q0 and q1 above, so those four were two games on one card, not one game at a
200 % screen percentage. Repeated with a guard that no other game runs
(`/project/ue/cloud/lag-2026-11-24/out3`, `out4`):

| Run | GPU time a frame | The game | Capture |
|---|---|---|---|
| a1: one game alone, `r.ScreenPercentage 200`, 60 fps cap | 11 ms | a steady 60, worst frame while turning 26 ms | no fence time-out, no skipped frame |
| b1: the same with `-PixelStreamingCaptureUseFence=false` | 11 ms | the same (worst 18 ms) | the same |
| c1: one game alone, `r.ScreenPercentage 400` (truly GPU-bound) | 29 ms | 33 a second, **worst frame while turning 1.0 s** | 239 fence time-outs, 1,145 skipped frames |
| c2: the same with `-PixelStreamingCaptureUseFence=false` | 29 ms | the same (worst 1.1 s) | 240 time-outs, 1,181 skipped: the option changed nothing |

So: a 200 % screen percentage alone does not load this GPU enough (11 ms of 16.7); the stall needs a GPU that is
really full: one game at 400 % (29 ms), or two games on one card (the worst case: frames of 4 to 7 s). The earlier
conclusion stands (a full GPU makes Pixel Streaming 2's capture stall the game), with one addition from the engine
source: with `PixelStreaming2.UseMediaCapture` on (the default) the capturer is `FPixelCaptureCapturerMediaCapture`,
which always waits on its fence; `PixelStreaming2.CaptureUseFence` is only read when `UseMediaCapture` is off
(`PixelStreaming2/Private/VideoCapturer.cpp:189-203`: `FPixelCaptureCapturerRHI` with the fence,
`FPixelCaptureCapturerRHIRDG` without). Epic's own note there (`PixelStreaming2Module.cpp:86-88`): without a fence
"we get frequent and intermittent stuttering as textures are rendered to while being encoded"; with NVENC "acceptable
without a fence in most cases". Runs with `-PixelStreamingUseMediaCapture=false` (d1, d2), decoupled under load (c3)
and version 2's Shipping game steered by a viewer's console commands next to a second game (t1) follow below.
For the release gate use a load the game's own dynamic resolution cannot undo (a second process on the GPU), and
check that nothing else runs.

**The remaining lag runs, 00:20 to 00:31 UTC** (`/project/ue/cloud/lag-2026-11-24/out4`, `out5`, `out6`; the gameplay
engineer's report lists when its own games and compiles ran: 23:46:08-23:47:49, 23:51:15-23:53:06, 00:05:01-00:06:36,
00:07:32-00:09:12, 00:22:15-00:23:55, 00:24:08-00:25:49; compiles on all cores about 00:01-00:04, 00:13-00:17,
00:19-00:21):

| Run | What | Result |
|---|---|---|
| c3: one game, 400 %, `-PixelStreamingDecoupleFramerate` | GPU-bound, decoupled | the same as c1 on the game's side (33 a second, worst frame while turning 1.07 s, 241 fence time-outs, 1,168 skipped frames) |
| d1: one game, 400 %, `-PixelStreamingUseMediaCapture=false` | the RHI capturer with its fence | **not clean** (another game on the card for most of it): ignore the numbers; no capture error lines |
| d2: one game, 400 %, `-PixelStreamingUseMediaCapture=false -PixelStreamingCaptureUseFence=false` (clean) | the RDG capturer, no fence | no fence time-out, no skipped frame, **but still one frame of 1.1 s while turning** and 33 a second |
| t1: version 2's **Shipping** game next to a second game that keeps the GPU busy; the viewer sends console commands | `r.DynamicRes.OperationMode 2`, `FrameTimeBudget 16.67`, min 50, max 75, then `t.MaxFPS 30` | the game logged every one as set: **a viewer's console commands work in version 2's Shipping game**. `MIStart mission skip` did not start a run there (the game stayed on the home screen), so nothing was played; frame rate and GPU time did not change (28 a second, about 35 ms: with a second process on the card the game's measured GPU time includes the other process's share) |

What to take from them: (1) the capturer decides whether frames are skipped and fence lines are logged, but the
second-long frame at 400 % is there without any fence, so the capture is not the whole story: **find where the long
frames go (game thread, render thread, RHI, waiting for the GPU, capture) with a profile before choosing fixes**;
(2) a 400 % screen percentage is not a slow GPU: it is sixteen times the pixels (shadow pages, Lumen caches, a 600 MB
texture pool), and its one-second frame comes at about the same moment of the turn in every run; a slow GPU does
the same work more slowly. The closest thing to the owner's report so far is two games on one card (q0, q1: frames of
4 to 7 s, the frame counter standing still while a fence time-out is logged every 100 ms); build the load for the
release gate that way (a second process), and check what dynamic resolution does when the measured GPU time
includes another process's share; (3) E3DS's "Unreal console commands to run at start" field can steer version 2
without a build if E3DS delivers the commands the way a viewer does (unproven); version 3's allowlist must let the
tuning commands through (PREFLIGHT V3-9).

**State at 00:30 UTC:** the session's container restarted at about 00:29. The gameplay engineer had just reported
(all seven input items and the controller path, 114 tests passing at `71e5b44`, head `6116a2a`); nothing was lost.
The final-build workflow was resumed as **release A** (the lag: PREFLIGHT V3-1, V3-3, V3-5, V3-11, V3-9's widening,
V3-10), with the rest of version 3 as release B afterwards.
