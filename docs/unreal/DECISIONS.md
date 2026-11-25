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

**The cause, 01:10 UTC (2026-11-25; performance engineer, release A; runs, tables and what was changed are in
`docs/unreal/PROGRESS.md`, "Version 3, release A: the lag").** It is not Pixel Streaming's capture that stalls the
game, and a full GPU alone does not either. **A game that renders off screen never waits for the GPU**: with no
window to present to, Unreal 5.9's Vulkan viewport returns before its wait for the previous frame (read in the
engine source, not single-stepped: `VulkanViewport.cpp:842-850`, "Skip present if the native window has been
destroyed", comes before the wait at `:873-878`, and with `-RenderOffScreen` Linux runs the Null application,
`LinuxPlatformApplicationMisc.cpp:635-638`, which has no native window). The only thing that still held the game to the GPU's pace was a side
effect: the render thread reads last frame's occlusion results at the start of a frame and blocks until the GPU has
them. While the view turns that wait is zero (CSV profiles of runs x2 and b0: 25 ms a frame with a still view, 0.0 ms
in every turning frame, in which the engine draws no occlusion tests at all), the game runs at its 60 cap, the GPU
finishes half of that, and the unfinished frames pile up. The
game's new counter shows it directly (run p1, the GPU slowed to 130 ms a frame): 3 frames owed with a still view,
then 26, 50, 65 while turning, then one frame of 7.3 s; again 67, 72 and a frame of 8.6 s. When the turn ends the
occlusion read-back waits for the whole pile: that is "when the player turns it slows down". The capture's fence
time-outs and skipped frames are the same pile seen from Pixel Streaming, and so are the 14.5 GB of memory and the
slow shutdown of run `gp-in5`: every unfinished frame keeps about 11 MB (measured in runs p1 and b0), `gp-in5`
gathered about a thousand of them, and at exit the engine waits for the GPU to finish them all.
Version 3 holds the game back itself (a pacer: no frame starts while the GPU still owes more than one), which ends
the stall at every load tried; dynamic resolution and a frame-rate target of 60, 45 or 30 then keep the GPU from being
the limit at all. The earlier entries above keep their measurements; their explanation ("the capture stalls the
game") is replaced by this one.

**Decisions of release A, 03:00 UTC (2026-11-25; performance engineer; measurements in PROGRESS.md, "Version 3,
release A: the lag").**

1. **The pacer allows one unfinished frame** (`MI.Cloud.GpuFramesInFlight=1`). None costs a sixth of the frame rate
   on a full GPU, two add a frame of delay and gain nothing.
2. **Pixel Streaming's capture settings stay at Epic's defaults; decoupling stays off; there are no `-MIDecouple`
   switches.** With the pile gone no capture setting delivered more frames or a shorter worst frame, with a free
   GPU or a full one. Decoupled, a full GPU sends 55 frames a second of which up to 24 repeat the one before. The
   gain measured on version 2 was the Python viewer's bitrate. Pixel Streaming's own launch options and
   `-MICVars=PixelStreaming2...` remain for a session that wants to try.
3. **The frame-rate target drops only when a run cannot hold the rate**, not at 70 % of the frame time as
   PREFLIGHT V3-1 proposed: in live play, at the smallest picture, after a second in which the game made more than
   8 % fewer frames than the target asks for while it waited for the GPU, or in which the GPU's own time was over
   the whole frame time. Lines at 70, 85 and 90 % were each tried and each lowered a rate that was being held
   without one late frame (a GPU that held 60 was put at 45; one that held 45 was put at 30), and so did "the
   pacer waited a fifth of the time" on its own: while the rate is held, that wait only takes the place of the
   frame cap's sleep. And it never drops outside live play: the start of the game is full of long frames on any
   card (the pacer waited a third of the first second on a free GPU), and a target lost there would have stayed
   lost for the first run on a card that is busy but able. The pacer keeps a full GPU from stalling whatever the
   target is, so the target only has to follow what a run can really hold. The owner's order decides the rest:
   fluid play first, so 60 at a smaller picture before 45 at a larger one.
4. **3840 x 2160 output waits for release B (V3-6).** On a free GPU the game held 60 but the encoder made 46 frames
   a second, the game missed that its viewer had left and did not shut down within 30 s (run d7). 2560 x 1440 was
   clean. Until the game limits its own size, E3DS's Browser Resolution stays Custom 1920 x 1080.
5. **The Python viewers of the box need the stream held at 12 Mbit/s** (`lag-test.sh minbit=`): with E3DS's
   arguments alone the sender believes their connection carries a megabit or less and drops most frames. Received
   frame rates from earlier runs without it say nothing about the game.

**Decisions of the review of release A, 05:30 UTC (2026-11-25; two reviews of release A's changes found ten
faults; what was checked, changed and measured is in PROGRESS.md, "Version 3, release A: the review's findings").**

1. **The pacer's wait belongs to the render thread.** The game thread polled a GPU fence in a loop, which Unreal's
   own header forbids: some RHIs notice finished GPU work only while the RHI thread submits. Unreal's Vulkan RHI is
   one of them when it has 6 task workers or fewer (8 hyper-threaded CPUs: the usual small cloud GPU server), and
   the box's 16 CPUs had hidden it. On 6 CPUs every frame the GPU was the limit froze for the pacer's 250 ms
   (runs `rf-cpu6-l20`, `rf-cpu6-l35`). The render thread now waits with `FRHIGPUFence::Wait`, the call the engine
   uses itself; the game thread only watches. The release gate has three runs on 6 CPUs from now on.
2. **A double click is two clicks.** Pixel Streaming's "MouseDouble" message is dropped: Unreal takes it for a
   third press, and by the review's reading of its script E3DS's page never sends its release (shown on the box
   with a viewer that sends it so: the old binaries emptied the magazine after one double click, run
   `rg-dbl-old`). This is the one finding that fits the owner's word "sticky" for version 2 (two quick clicks left
   an automatic gun firing); that link is an inference.
3. **When the last viewer leaves, everything he held is let go, and the controllers stay known.** The review
   proposed to tell Pixel Streaming that every pad had disconnected. A page that reconnects inside one session may
   go on using the id it was given, and its pad would then be dead; the game instead hands Pixel Streaming a zero
   for every trigger and stick, which ends the repeat of a pulled trigger and keeps the ids (checked through the
   stream: the next viewer's trigger message with the old id fires and stops).
4. **The Development game in the zip needs a key** (`-MIDev=<key>`, the word in `MIDEV.key`, new for every zip).
   A visitor can add launch options to a stream link, and the Development game has the switches the Shipping game
   was built without. One zip stays enough for the owner; the key travels with the release report, never in the
   repository.
5. **A viewer's size request is drawn between 640 x 360 and 1920 x 1080, and the mouse scale follows a size that
   was cut down.** The cap alone would have slowed the mouse of every viewer with a larger frame, so the scale half
   of PREFLIGHT V3-6 came with it (five lines); the rest of V3-6 (sharpness and HUD at small sizes, Dynamic as the
   advised setting) stays release B. Browser Resolution stays Custom 1920 x 1080 until then.
6. **The frame-rate target rises when the next rate up would leave a fifth of its frame time free** (13.3 ms to go
   to 60, 17.8 ms to go to 45), judged at the smallest picture. The first rule (45 % of the frame time now) could
   not give 60 back to a card that holds it. **And a smaller picture buys little for this game**: measured on the
   box, 6.39 ms a frame at a 75 % picture and 6.00 ms at 50 %: an eighth of the GPU's time follows the pixels.
   Dynamic resolution stays on (it costs nothing), but the frame-rate target, and in release B the quality steps,
   are what a slow card needs.
7. **The stream sends 56 to 57 of the game's 60 frames a second on a free GPU on the box, and nothing tried
   changes it** (a frame cap of 120, a viewer that does not decode, a faster encoder preset, every capture
   setting): some frames take the encoder longer than a sixtieth of a second and the frame behind is dropped. It
   is recorded as the measured state, not accepted as good: **the owner decides** after the pause card on E3DS has
   shown what its servers do (the line reads "stream 56 a second (lowest 50)"). A gap of a few frames with plenty
   of megabits is the encoder, not the connection (LAUNCH.md section 7 says so now); `-MIFps=45` is the setting to
   try if the gap is larger there.
8. **The pad's X (Square) reloads or grabs, never both** (the web game's rule: the press decides).

**Version 3a delivered, 07:50 UTC (2026-11-25; release engineer; PROGRESS.md, "Version 3a: packaged, gated and
delivered").** What was decided on the way, for the owner to overrule:

1. **No default was changed before packaging**: nothing new had arrived from the owner's E3DS test (the card, the
   frame rates and the mouse's feel there are still unknown). Version 3a is release A as reviewed.
2. **The gate was run on the zip itself, cold**: unpacked as a new user with an empty home into a fresh folder,
   every run. That is stricter than the earlier gates (warm folder, warm home) and showed what a new machine costs:
   one frame of about 0.85 s when the first set-up screen appears, and a first frame of 3 to 4.5 s before anybody
   is connected. **It was not fixed here**: the play is not touched by it, the fix is release B's (PREFLIGHT V3-12),
   and holding release A for it would have kept the lag fix from the owner.
3. **"No fence time-out line" is read for a Story run as a player reaches it.** In such runs the Development
   game's log has none, on 16 CPUs and on 6, also for a player who clicks through at once. It has two at the cold
   frame of the first set-up screen, and one when a test script starts a run 12 s after a cold process start on 6
   CPUs (one frame of 50 ms). Read to the letter for every run, the gate's Development lines on 6 CPUs would have
   failed on that one line; it is reported, not hidden.
4. **The owner's settings for version 3a**: Browser Resolution Custom 1920 x 1080 and no launch options (version
   2's `-PixelStreamingDecoupleFramerate` comes out: decoupled, a slow server repeats pictures). The mouse is then
   exact when the picture is shown 1920 wide and faster by the same factor when it is shown smaller; Dynamic, which
   would make it exact at every size, waits for release B as decided in the review.
5. **What comes back from the owner decides release B's order**: a screenshot of the pause card. A slow card (the
   game's own number low, "target 45" or "target 30") puts the quality steps (V3-2) first.

**The release check of version 3a, 09:20 UTC (2026-11-25; release checker; PROGRESS.md, "Version 3a: the
independent release check").** What it decided, for the owner to overrule:

1. **Version 3a is fit for the owner's test of the lag**: the gate passed again from the storage's own file, with
   a harder viewer, and version 2 under the same load on the same morning showed the stall the owner described
   (frames of 0.3 to 1.3 s where version 3a's longest is 48 ms).
2. **The game has no sound, in no package so far, and this does not hold version 3a back.** Versions 1 and 2 were
   as silent (the same missing import), so nothing is lost against what the owner has already streamed, and the lag
   is what the owner asked to have fixed first. But the owner is told before the upload (LAUNCH.md, top of the
   page), and **the build after 3a starts with the sound** (PREFLIGHT.md V3-14): about an hour and a half, no game
   code. If the owner would rather wait for a build with sound than upload 2.25 GB twice, that is the owner's call.
3. **"No fence time-out line" is read as the release engineer read it**, and the one line of the script-started
   Development run on 6 CPUs did not appear in three repeats.
4. **The stream's sender stays the open question for E3DS**: on the box it sends 56 of 60 frames a second with
   single seconds at 44 to 50, and under an outside load the encoder itself slows down. Only the owner's pause-card
   line can say what E3DS's encoder does.
