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

**E3DS's control panel, worked from the box (2026-11-25, 02:25 UTC; state at 09:35 UTC).** The owner asked for a
browser to sign in to, so that E3DS's settings are changed for them instead of by them. This cloud session cannot open
a browser on the owner's computer (the computer is seen, but it offers none of its Remote Control folders to cloud
sessions), and creating a desktop in another service was refused by the session's safety setting. The rented box
already has a desktop the owner can open in a browser tab ("Open desktop" on the rental), so that is used:
`tools/box/cloud/owner-browser.sh plain` starts Firefox there on E3DS's sign-in page as a plain browser (a sign-in with
Google refuses a browser under remote control), and `owner-browser.sh control` restarts it under remote control with
the same profile once the owner says they are signed in; `owner-browser.py` then reads the page's controls and works
them (`inv`, `click`, `fill`, `file`, `eval`). The password is never asked for, read, typed or saved (saving passwords
is off; password fields are left out and refused); the profile is under `/tmp` and is wiped when the work is done
(`owner-browser.sh wipe`). What it is for, in this order:
1. Upload the new build from the box's own disk (`/project/ue/cloud/e3ds-upload/MurderInc.zip`) with "Upload a new
   version of MurderInc": the owner no longer downloads, joins and uploads 2.25 GB.
2. E3DS's settings for the build (LAUNCH.md 9.1), among them **"Unreal console commands to run at start"** (Developer
   tab; several commands separated by a semicolon): E3DS's own way to tune a running app without a new build.
   Version 2 runs any command a page sends (it has no allowlist); from version 3a on the game admits the tuning
   prefixes only (`t.MaxFPS` among them).
3. One short test session from that browser with "Print UE log in browser console" on (the browser's log receives
   the page's console): the game's probe lines name the graphics card E3DS gives a Linux session and its time per
   frame. That is the fact every setting so far has been chosen without.
State: the browser has been waiting on the sign-in page since 02:25 UTC; the owner has not opened the desktop yet
(`deskctl idle`: no human input since the box started). Version 3a was finished at 06:36 UTC and checked at about
09:20 UTC; the check found that no package so far has sound, and version 3b (3a plus sound,
`tools/workflows/mi-v3b-sound-wf_314f60ad-a65.js`) was started at 09:33 UTC.

**What E3DS's machines really are, measured from the box's browser (2026-11-25, 11:00 to 11:30 UTC).** The owner signed
in to E3DS's control panel in the box's desktop browser (`tools/box/cloud/owner-browser.sh`); version 3a was uploaded
from the box's disk (24 s up, E3DS's test launch 76 s, everything on the streaming machines 4 min 40 s) and three stream
sessions were opened from that browser with the stream configuration's "Show the Unreal log in the browser console" on:
the game's own lines (launcher, `[MICloud]`, probe) arrive in the page's console, which the browser writes to its log.
1. **The machine.** NVIDIA RTX A4000 (GA104GL), driver 550.90.07, 16 GB; AMD EPYC 7402P, 8 usable threads; 20 GB of memory;
   9 to 12 GB of disk free; Ubuntu 22.04.4, kernel 6.5; no display; the streamer in the United States (Region: Global).
   It is **not** the RTX 4080 or 5070 of E3DS's own hardware page. The card is about a quarter of the test box's in
   speed.
2. **SM5, not SM6.** This driver fails Unreal 5.9's Vulkan SM6 check, so the game runs its SM5 shaders there: no Nanite,
   Lumen in software. (Version 2 did the same: what the owner saw is this look.)
3. **What E3DS starts the game with** (Medium quality, Custom 1920 x 1080): `-PixelStreamingEncoderCodec=H264 -AudioMixer
   -AllowPixelStreamingCommands -PixelStreamingURL=ws://127.0.0.1:3000 -PixelStreamingWebRTCMinBitrate=100000
   -PixelStreamingWebRTCMaxBitrate=20000000 -PixelStreamingEncoderMinQP=34 -PixelStreamingEncoderMaxQP=34 -Windowed
   -ForceRes -ResX=1920 -ResY=1080 -PixelStreamingID=...`, and `-PixelStreamingEncoderMaxQP=31` once more at the end.
   So "Medium" is a **constant quantiser of 34** (the picture's quality is fixed and the bitrate follows the motion, up
   to 20 Mbit/s: fast turns make big frames); E3DS's own page prints "Picture compression: 34 (good)". The signalling
   server is at port 3000 of the machine in every session: one session per machine.
4. **Menus, a free card, 1920 x 1080:** 60 frames a second, 11 ms of GPU time at 75 % render scale, encoder 4 ms, 0.15
   Mbit/s; E3DS's info panel: 60 fps, response delay 91 ms from the test box (in Europe) to the US machine.
5. **A session takes about two minutes to start** the first time (queue, "Acquiring App", "Preparing App", the game's
   own start); the next one on the same machine started in 34 s.
6. **THE FINDING: E3DS does not stop the game of a session that has ended.** The launcher's "GPU processes" line of the
   second session listed the first session's game (pid, same program, 3,405 MiB) still holding the card, 61 s after that
   session ended; the third session's listed two (6,732 MiB in all), and the first one was still there 4 minutes after its
   session ended. Each leftover game goes on drawing the menu at full speed, so the card is shared: the second session
   measured **gpuMs 33 to 37 at the smallest picture (render scale 0.50) and 27 frames a second** (first session: 11 ms
   at 0.75, 60 frames), the third **gpuMs 52 to 57 and 18 frames a second**. The pacer of version 3a held the game
   steady (frames of 40 and 62 ms, owed 2) but the picture was slow. **This is very probably most of what the owner
   met on E3DS**: a test session started within minutes of the last one lands on the same machine with the last game
   still on the card; version 2 had no pacer, so every such overload became a freeze. (The two mechanisms add up:
   the unpaced pile of frames explains why a turn stalled, the leftovers explain why it was slow at all.)
7. **Why the leftover survives** (read in the launcher): it passed a stop signal on to the game only after waiting 5 s
   for the game to end by itself; a host that stops just the launcher and kills it a moment later leaves the game
   running with nothing to stop it. What E3DS really sends is not known: the fix does not depend on it.
8. **The fix, in the launcher (commit 2322f3c; tested with a fake game, then on the box):** a stop signal goes on to the game
   at once (KILL 8 s later if needed: the game stops with a signal 0.35 s after the launcher's); a watchdog stops the game
   if the launcher is killed (4.5 s in the test); and before it starts, the launcher stops every other game of the package
   on the machine (all of them on an E3DS machine, whose folder is `.../0.apps/<account>/<app>/<version>`; elsewhere only
   those whose launcher is gone; `-MIKeepOthers`, `-MIReapOthers`). It prints each one it finds (pid, parent, age, memory)
   and the card's memory before and after, so the next session's log shows what E3DS leaves behind. **Still to do in the
   game (release 3c):** the game itself should stop drawing when no viewer is connected and quit a little after the last
   one left (E3DS's own documentation says an ended session "frees the machine"; it does not stop the app), and the quality
   steps of PREFLIGHT V3-2 matter more than thought: a card this slow, shared or not, has little room.
9. **Stream settings now** (set from the box's browser): Browser Resolution Custom 1920 x 1080, Video Quality Medium,
   "Show the Unreal log in the browser console" on, launch option `-MICloudProbe=1` (a log line every second: for the
   tests only), crash-log email on (the owner's own), session limit 15 minutes, idle log-out as before, password
   **off** (the owner chooses a password themselves: nothing here types one), mouse Locked.
10. **E3DS's storage is 10 GB:** versions 1 (2.2 GB), 2 (2.1) and 3 (2.1) fill 6.4; one more build fits (3.6 GB free),
    the next does not: older versions have to be deleted (the owner's decision).

**E3DS, the verification runs on version 4 (version 3a + the launcher fix), 2026-11-25 11:36 to 11:47 UTC.**
Version 4 was uploaded from the box's disk (24 s up, E3DS's test 75 s, on the streaming machines after 4 min 38 s) and
two more sessions were played from the box's browser with the game's log at one line a second (`-MICloudProbe=1`).
Both landed on a clean machine (the launcher printed "leftovers: no other game of this package is running", the card at
2 MiB), so **the cleanup itself has not yet been seen to stop a leftover**; it ran without error.
1. **A Story run on a clean E3DS card is smooth.** Home screen to run by keyboard (Enter on Home and Crew, Tab Tab Enter on
   the Loadout, Tab Enter on Block & Style, Enter on the Briefing), then walking, fast turns (yaw swings of 100 to 270
   degrees a second) and two shots: **60 frames a second in every second of the log, the worst frame 16.7 ms (18.4 ms in the
   worst second), GPU 10.2 to 13.3 ms at render scale 0.50 to 0.63** (the smallest picture is 0.50: the card has about 4 ms
   in hand), owed 1 or 2, held 0 to 4, the encoder 4.4 to 7.3 ms. The pause card on E3DS reads (E3DS's real page): "NVIDIA RTX
   A4000 - 60 frames a second (lowest 60, target 60) - GPU 10.7 ms - drawn 1183 x 665, sent 1920 x 1080 - stream 60 a second
   (lowest 59), 0.3 Mbit/s, QP 34, round trip 0 ms - build 6c4d810". (The round trip reads 0 ms on E3DS too: the game's
   reading of it is not working; E3DS's own info panel says 91 ms from the test box.) What was not tried: a fight (enemies,
   explosions) and a long run: the first room of the Story run has no enemies in sight.
2. **E3DS's Video Quality is a constant quantiser, not a bitrate**: Medium = QP 34 for both the minimum and the maximum
   (0.1 Mbit/s standing, up to 1.6 Mbit/s in fast turns, soft and blocky in the dark parts of the picture), High = **QP 16** for both
   (6 Mbit/s standing, **up to 14.5 Mbit/s in fast turns**, 60 fps held, the street scene crisp: the taxi, the lettering on the
   truck). With the minimum equal to the maximum the encoder cannot lower the quality to fit a thin connection: the extra
   bits queue in the sender, and a viewer whose connection cannot carry them sees a turn stall: another way for the owner's
   "it slows down when I turn" to arise, and the owner had High set when they tested version 2 (the author advised it from a
   free-card measurement: wrong advice, withdrawn). **Medium is set again. Release 3c should give the encoder a RANGE** (the
   game takes E3DS's `PixelStreaming.Encoder.MinQP` / `MaxQP` commands, which the page sends at the start of every session, as
   the middle of a range, for example 8 below to 8 above, so the sender picks the quality the connection can carry: this is
   what E3DS's own page calls "automatic quality, planned").
3. **Input from the box's browser**: the CLICK TO PLAY click makes the page lock the mouse. Marionette's own pointer moves do
   not turn a locked view; `owner-browser.sh ff act '[["jsmove",12,0,50,16]]'` (mouse-move events carrying their movement,
   dispatched in the page) does. Absolute clicks work only until the lock: use the keyboard for the set-up screens. Ctrl+Enter
   ("jump to the Briefing") arrives as a plain Enter through the page: the page does not pass Ctrl on.
4. **Storage and minutes**: 1.5 GB of the 10 GB left (versions 1 to 4); 259 of the 300 minutes left (the tests used 21; a
   session counts from the moment it starts, the machine's first start takes about two minutes of it). The next upload needs
   an older version deleted: the owner's decision (version 3 is the same game as version 4; version 1 never worked).

**E3DS in the hour before the owner's 9 am (2026-11-25, 13:00 to 13:40 UTC; the owner's calendar is US Eastern, so 9 am is 14:00 UTC).**
The owner asked for a game that is "playable and perfect by 9 am" and then said the guns with attachments are the
priority. What was done on E3DS from the box's browser, and what was measured:
1. **The link was pinned to version 4** (Builds tab, "Run a fixed version": Version 4), so that an upload does not change
   what the owner's link streams until the new version is chosen. **Version 1 was deleted** (2.2 GB; it never worked; the
   other versions stay): 6.3 of 10 GB used. Deleting a version: Storage page, open the build, "Delete version N".
2. **Two project settings would have cut a demo short**: "Longest a session can last" was **15 minutes** (a hard cap, even
   for an active viewer) and the idle logout started after 5 minutes (countdown 1 minute). Set to **45 minutes** and **10 + 2
   minutes**. They cost E3DS minutes only when a viewer stays (250 of 300 minutes were left at 13:35).
3. **Version 4 on a real E3DS machine, Hold the Block** (session `v4a`, 13:23 to 13:28): picture after 112 s (cold start), the
   set-up screens by keyboard (on Home, Down twice reaches the Mode row and Right switches it), the run began, the player
   died after 24 s without a kill (the scripted fight does not aim): over the 130 probe lines of the session **60.0 frames
   a second on average (lowest 59.7), worst frame 16.7 ms on average (21.1 ms at most), GPU 10.6 to 13.2 ms at render scale
   0.50 to 0.75, QP 34, 0.5 Mbit/s on average (8 at most, in a turn), encoder 3.8 to 8.0 ms**. A short sample, not a long
   fight, and the first one on E3DS. The street, the HUD, the CHOPPER in the hands and the tattooed arm read well in the
   picture. **The stream carries no sound** (every sample: "stream has no audio track"): version 4 has none.
4. **The launcher found a clean machine again** four minutes after the last session ended (`leftovers: no other game of this
   package is running`): E3DS now stops the game with its session (the stop signal that version 4's launcher forwards at
   once works on the real path). The reaping of a game that survived has still not been seen; the game quitting by itself
   (release 3c) is the second layer.
5. **Version 3b (sound) is uploaded, but E3DS's own test did not finish.** Upload 25 s at 89 MB/s; E3DS's test machine took
   the build at 13:10:47 and stayed at "Download, unpack, virus scan" ("Unpacking on our build-testing server: 70 %") for
   more than 25 minutes, where versions 3a and 4 took 75 s. A second upload (13:29:57) then waited "for a free test machine".
   Nothing in the build is involved before the app starts: the test server is stuck or slow. No version 5 exists, and the
   link streams version 4. When it passes: pin version 5 ("Run a fixed version"), run `e3ds-session.sh`, read the sound
   level (`e3ds-snd.js`: rms and peak must be above zero in the menu and in the run), then make it the latest.
6. **Tools (committed):** `owner-browser.py file` now types into E3DS's file input even when the page clips it to nothing
   (class `sr-only`: it was refused as "not reachable by keyboard"); the dialogs are duplicated, so the file goes to the
   LAST input, "Yes, Linux" is clicked twice (both copies) and then the last "Upload". `e3ds-snd.js` (the stream's audio
   level in the page), `e3ds-probesum.py` (the probe lines summarised), `e3ds-session.sh` (a whole scripted session).
   A browser on the box that plays a stream takes CPU from a measuring run: pin it (`taskset -a -cp 13-15`) when one runs.

**A PS5 controller through E3DS's own player page, tested with a simulated DualSense (2026-11-25, 13:52 to 13:59 UTC, version 4).**
The owner asked whether the build takes a PS5 controller. Version 3a/4's controller path had been played only with
the test client's gamepad messages sent straight into the stream (`rtcinput.py`), never through E3DS's player page.
`e3ds-padinject.js` puts a standard-mapping DualSense into the PAGE's world (a script element: the Marionette sandbox's
own changes to `navigator` are invisible to the page) by replacing `navigator.getGamepads` and sending a
`gamepadconnected` event; the page's gamepad code then reads and forwards it as for a real pad (`e3ds-padseq.js` plays
button and stick sequences). Measured on a real E3DS machine:
1. A button press hides the CLICK TO PLAY card (`click=0`); Options on Home starts the run with the saved set-up and
   pauses and resumes it afterwards (`state` 2, 3, 2, 3, 2); Cross accepts; R2 fired, the left stick moved, a run ended
   in the player's death after a few seconds.
2. **The right stick turns exactly as the web game's numbers say**: full deflection for 300 ms gave 67.2 degrees, for
   600 ms 152.3 and 147.5, for 1000 ms 263.8 (the probe's yaw is wrapped to plus or minus 180: a change of minus 96.2
   is 263.8; the first reading of it as 96 degrees was this wrap, not a slow stick). The web game's own function gives
   263.775 for exactly 60 frames. So the browser, E3DS's page, the data channel and the game together add nothing.
3. Not covered: a real DualSense in a real browser (Chrome or Edge), the Dead and Debrief cards by pad in a stream, a
   whole Story run by pad, the delay from hand to picture, and the pad's button names (the game cannot tell which pad it
   is: Settings, Controller row). The owner plays it next.

**The version 3b release gate was stopped at 29 of its lines (2026-11-25, 14:00 UTC), and why.** The release engineer of the
3b workflow died on the owner's monthly spend limit for the older model, but its queue of measuring runs
(`tools/box/cloud/lag-test.sh queue-fg`, files `/project/ue/cloud/v3b/*-queue.txt`, results in
`/project/ue/cloud/lag-v3b/queue.out`) went on by itself and kept the box busy for an hour, which blocks every compile and
test of the other jobs by their etiquette. The package it measured (zip c274d3b8, game 5c1b6be) is not going to be released:
a review found two must-fix sound faults in it (`docs/unreal/sound_review_3b.json`), so the next release is a new package.
The queue and its load generator (`gpu_hog.py`) were stopped by hand. What the 29 lines showed, on the test box: free GPU
60.0 frames a second (lowest 59.0), worst frame 31 ms; loads of 8, 12 ms: 60 and 59.9; load 20 ms: 34.9 (version 3a's zip
under the same load: 35.3, so no change); load 35 ms: 28.9; the same with the process limited to six CPUs: 30.4 and 29.3; the
Development game's Story run under the 35 ms load: 30.0; the pad-only proof 60.0 with a worst frame of 25 ms; the input and
console-command checks ran. Nothing showed a stall or a rule change. These are the numbers the next gate compares with.

**Sound work paused until the guns release is out (2026-11-25, 14:18 UTC), at the owner's request.** The owner said: "dont let
the sound build delay, we can work on the sound after the other part is finished". The sound-fix job (workflow
`tools/workflows/mi-sound-fixes.js`, the review's findings in `docs/unreal/sound_review_3b.json`) was stopped and its
half-finished edits were taken OUT of the branch head so that nothing of them can break or delay the weapons and 3c
builds that others make from it: they are kept in history as `17da1c7` and `9b0b3a1` (the engineer's two work-in-progress
states) and taken out again by the revert commits `c8801f7` and `fe9dafe`. **To resume the sound work:** `git revert c8801f7
fe9dafe` brings those edits back (the audio director's voice limit, the Goons' footsteps, the mixer pace in the probe
line, the package guard, sync.sh), then run the workflow again (it re-reads the findings). The measuring tools it added
before (`rtcaudio.py`, `rtcinput.py` stereo answer, `music_phase.py`) stay in the branch; they change no game file. Release
v6 therefore carries the version 3b sound as it stands (two known faults, listed in the findings), is NOT gated on it, and
the lead can silence it from E3DS's launch options with `-nosound` if the owner prefers silence; the release workflow
`tools/workflows/mi-release-v6.js` says so to its engineer. E3DS's own test server was stuck on the 3b upload at the
same time (see the entry above): the new package is uploaded once, and only the weapons package.

## 2026-11-25 (14:40 UTC): the guns come first, and they must read apart: the CHOPPER is SK_Chopper again

**Asked.** After the owner's test of the streamed game: "all the guns look the same and no attachments are able to be added to the guns", then
"the guns need to be priority with attachments", and for the day's work: "make sure the game is ready with guns and accesories and smooth turns".

**What this reverses.** The mesh part of the decision of 2026-11-23, "Use the pack rifle". That decision made the CHOPPER the pack's Short
rifle in a dark-earth finish and retired `SK_Chopper`. Together with the pack's other two handguard lengths (the SHORTY, the STICK, the
STRETCH) it left four of the five offered guns as one M4 in three lengths, and none of the three of ours could take a part. The owner saw
exactly that. The rest of the 2026-11-23 decision stands: the NINE stays, the CHOPPER's rules stay the web game's, nothing from the pack is
ever committed.

**The answer, in effect (binding):**

- **`SK_Chopper` is the CHOPPER's mesh again**, in slot 1, with its own first-person hands (hand IK on its `Palm_R` and `Palm_L`, as the
  NINE's). The pack rifle stays only as the STICK. Its rules, its numbers, its reload stage times and everything the golden tests replay are
  untouched: this is a presentation change. Going back is one data commit: `presentation.json guns.chopper.realMesh` and its `real` block as
  they were before commit 19265f1.
- **The SHORTY and the STRETCH are our own guns now** (a bullpup carbine, a marksman rifle with a folding bipod), one body each. The
  **RATTLER**, the Goons' SMG, gets its own mesh and is offered. The rack shows six guns that read apart by their silhouettes: CHOPPER, NINE,
  SHORTY, STICK, STRETCH, RATTLER.
- **Attachments on every gun**, twelve parts of our own on top of the pack's ten: a red dot, a 4x scope, a suppressor, a pistol suppressor, a
  compensator, a vertical grip (and a walnut one for the CHOPPER's handguard), an angled grip, a laser module and three extended magazines,
  with the compatibility of the specification. The Workbench offers 3 / 3 / 5 / 5 / 4 / 3 slots on CHOPPER / NINE / SHORTY / STICK / STRETCH /
  RATTLER. Every part still makes one thing better and one worse, inside the trade band of LOADOUT.md 3.3, and a new stat, rounds per magazine,
  is how the extended magazines pay off.
- **Priority inside the work:** the guns on the stage and the Workbench with their parts first (the owner sees them first), then the same in
  first person (hip, aimed through an optic, one reload, one burst), then polish (casings, the laser dot, solved grips). Attachments come before
  hand polish.
- **A clean checkout is unchanged in what it offers:** the CHOPPER and the NINE on the template meshes, no slot, everything else hidden,
  because none of our meshes or parts is committed (they live on the box, imported by `tools/box/fp/import-chars.sh r4`).

**Defaults taken, to be changed on the owner's word:**

1. **The wall pull of the new guns is the one they had** (SHORTY [0.95, 0.38], STRETCH [1.27, 0.51], RATTLER [0.85, 0.34]). The specification asked
   for a re-measure with the real meshes (the bullpup is 0.70 m long where the pack's Short rifle was longer); a rule number does not change
   without a reason a test can show, so it stays until someone measures it in play.
2. **The extended pistol magazine holds 24 rounds, not the 25 of the specification** (a factor of 1.6 on 15, where 1.67 gives 25.05: the
   parser would drop the fraction). The rifle and SMG ones are 45 and 48 (a factor of 1.5).
3. **The STRETCH's magazine looks like 10 rounds and its data says 30.** The data stays: nobody counts the rounds in the picture, and damage is
   not retuned for a drawing.

## 2026-11-25 ~18:10 UTC: no credit floor

The owner, asked about the balance (about 1,275 credits, under the 2,500 floor of RESUME 2 and 7): "use as many credits as needed i will
replensih them". The floor is gone: the box (603980d9, the same spec, rented 17:50 after ec087d85 expired at its 24 hours) runs on, and
agents may rent the same spec again when a rental ends. Unchanged: one box at a time, the same spec and price, nothing else rented.

## 2026-11-25 ~20:40 UTC: release v6 waits for the full checks ("no shortcuts we need this to be perfect")

The owner chose the fully checked release over uploading the trial package (fd8ce12) now, then said: "no shortcuts we need this to be
perfect". The lead creates /project/ue/cloud/RELEASE-V6-GO only when all of these hold on one commit:
1. The hands C++ pass (HANDS_R4.md 8) is built, its review's must-fix items are closed, and the support hand holds the magazine in
   every reload and the aimed optics show no black ring, in pictures someone other than the engineer looked at.
2. The readiness pass (docs/unreal/READY.md) says go: rendering faults fixed, flicker measured at the viewer and within limits at the
   chosen stream resolution, every menu screen clean at every tested size, every gun with every part fitting, showing and playing.
3. The full suite passes on that commit in a clone with the guns imported fresh (golden replays included, nothing skipped).
Then the release engineer packages exactly that commit and gates it; an independent check plays the package; only then is it uploaded,
and E3DS's copy is played through the E3DS page (every gun, every part, keyboard, mouse and pad) before the owner switches the pin.
Anything that fails any step goes back to its lane; nothing is waived for time.

## 2026-11-25 ~21:00 UTC: smooth play is a release criterion

The owner played version 4 on E3DS: "It is very laggy and buggy you need to ensure this is built for a smooth gaming experience"
(asked: stutter or freezes and a low frame rate; bugs in menus, weapons and gameplay). Added to the GO criteria of 20:40:
4. docs/unreal/SMOOTH.md's independent verdict is "smooth": no freezes, 60 fps held under E3DS-class limits on the front end, story and
   holdout, per-frame numbers (frames over 25 ms and 100 ms per minute, worst frame, 1 % low) better than version 4's under the same
   conditions, and every gameplay, menu and weapon bug found fixed and re-checked.

## 2026-11-25 ~21:20 UTC: deaths, weapon switching, story guidance and an end-to-end play are release criteria

The owner: "enemies when killed crouch over they should have blood splatter and then fall to the floor, switching between weapons
doesnt work ... make sure to do a full end to end play so the game is ready for deployment. also the story needs to have ques to tell a
player where to go and hints (highlighted walking paths on the ground to get to the next object)". Story mode today is one map (L_Block,
mode mission: Reel 1, Reel 2, Reel 3, then the extraction truck). Added to the GO criteria (20:40, 21:00):
5. docs/unreal/PLAY.md: killed enemies bleed and fall to the floor (no crouch, no sinking, no bodies blocking shots); weapon switching
   works by keys 1-4, the wheel and the pad in every state tested, with tests; story guidance (objective line, hint after no progress,
   on-screen marker, a highlighted walking path on the ground) leads from the start through all three reels to the extraction; an
   independent end-to-end play from the front end to the extraction and the holdout finds no blocker or must-fix left.

## 2026-11-25 ~21:40 UTC: three maps, three levels; the fixes release ships first

The owner: "we need 3 maps to start we can add more later but the player needs to progress to 3 levels each map is a different newyork
setting". Asked, the owner chose Level 1 = the Block (the street under the El, as now), Level 2 = Chinatown / Canal Street, Level 3 =
Midtown rooftops / Times Square, and "Ship fixes, then maps": the guns-and-fixes release (v6, the GO criteria of 20:40 to 21:20) goes
out as soon as it passes every check, with one map; the three-level story is the next release and meets the same bar. Design and
build plan: docs/unreal/MAPS.md and docs/unreal/maps/ (workflow mi-maps-design). Invented names only on signs and billboards.

## 2026-11-26 ~02:00 UTC: the owner's answers on the three-map plan (docs/unreal/MAPS.md)

1. Session limit 30 minutes (the whole three-level story in one sitting; at most 10 full sessions on 300 minutes a month).
2. Levels 2 and 3 locked in order: clearing a level's story on any difficulty opens the next.
3. Progress: the 8-character progress code on every results screen AND the browser save through a small message handler on the IPX page.
4. Canal Street signs in English only: no Chinese characters (no outside reader needed); Chinatown reads through architecture, lanterns,
   the market and English shop names (invented, as everywhere).
Not yet answered (defaults of MAPS.md stand until the owner says otherwise): the nine-masters story with an unnamed buyer, night for both
new maps, the invented sign and billboard names (to be shown to the owner before the sign art is final), the Hold mode names, the far
bridge silhouette behind Canal Street.
Readiness pass verdict (READY.md): go with caveats for v6 from 04c66c8 (suite 217/217), stream at 1920x1080 only (2560x1440 does not
hold 60 at the viewer; 3840x2160 kills the encoder, now clamped in code), E3DS settings in LAUNCH.md 9.5.

## 2026-11-26: the progress code is a checksum, not a secret (page bridge)

The code's salt and CRC are in the public page script and in the game, so a valid code for every level and the album can be made by anyone, and
Hold bests are accepted as sent. Accepted: progress is a single-player convenience and nothing is monetised (progression.md 4.3). Rule: no
leaderboard, prize or ranking may read the Hold bests, the album bit or the code from this path; a keyed signature would need a server and is out
of scope. The page script merges, never overwrites, stored progress; the game takes the page's message only from the controlling viewer.

## 2026-11-26 ~22:45 UTC: the owner's polish decisions (POLISH.md owner list)

1. **The "4x scope" is renamed "2x scope"** (it magnifies about 1.8x over the irons): its zoom stays as it is; every string, the
   Workbench text, the part name the player reads and the docs say 2x. The part id in data may stay if renaming it would touch saves.
2. **Default field of view 90 degrees** (was 106 horizontal at 16:9, 112 sprinting, which keeps its relative widening), with the
   Settings slider kept so players can widen it.
3. **The STRETCH is semi-automatic** (one shot per trigger pull), matching its marksman role and description. This is a deliberate
   gameplay change by the owner for a gun that is not in the web game: tests that read the STRETCH's fire mode are updated to the new
   value (that is not weakening a test); golden replays of the Block's original guns must stay byte for byte.
These go into v6 with the fixer's POLISH.md shortlist.

## 2026-11-27 ~00:10 UTC: the last unhurt drones come to the player (B2)

The owner, on Hold the Block's wait for the last enemies (up to 77 s for an unhurt Buzzard): "Drones come to the player". After
20 seconds with only unhurt Buzzards left in a wave, they fly straight at the player so the fight ends quickly; the marker on the last
enemies stays. This is a deliberate rule change by the owner for Hold the Block's wave end only: the director's behaviour for the last
drones changes, tests that read it get the new value, and every golden replay that does not reach that state stays byte for byte.

## 2026-11-27 ~16:00 UTC: keep r.Vulkan.PipelineCacheLoad=0 (the lead)

The performance lane traced the slow and erratic engine start (5.7 s to the first probe line, once 26 s) to the render thread saving
the Vulkan driver's pipeline cache while the game thread waited. With r.Vulkan.PipelineCacheLoad=0 the first probe line comes at 3.4
to 3.9 s (version 4: 3.2 to 3.5 s). The cost is version-4-like pipeline creation in the first 3 s of a process, before any viewer
joins on E3DS; after 10 s no run had a PSO hitch and the first fight stays clean. Kept. Setting it back to 1 restores the old behaviour.
The GPU box 8496fd8c ended at 09:40 UTC (runtime_failed, the provider's side); the replacement is 1e0f3eeb, same spec.

## 2026-11-27 ~21:00 UTC: the owner passes smoothness; the STICK's one-hand reload ships as is

1. Smoothness criterion 4 (21:00, 2026-11-25) is met on the numbers of SMOOTH.md v9: no crash (version 4 crashed in Hold the Block),
   fewer stalls over 100 ms, half the worst frame, the Loadout fix in; frames over 25 ms a minute not significantly different from
   version 4's (Mann-Whitney p = 0.60). The short stall episodes (the stream pacer holding frames, every thread idle) stay under
   investigation for the next release.
2. The STICK's reload shows one hand (the pack's own clip): shipped as is in v6, fixed in the next release.
Still required for the GO: the SHORTY reload hands, the Story ground path trap, a full-size look at the guide path and the HUD
changes, and an independent end-to-end play (Story to the truck, Hold the Block waves 1 to 3 with the last-drone rule, the pad, gun
switching).

## 2026-11-27 ~21:15 UTC: the release bar, trimmed to what protects players (the lead, at the owner's word)

The owner: "make sure your rules arent holding back the game unnecessarily". Version 4 is live and crashes in Hold the Block; v6
beats it on every measure that matters. From now on a v6 GO needs only:
1. **No blocker:** no crash, no stuck state (a player can always finish the Story and leave any place the guidance leads), weapon
   switching and every attachment working, the stream at 1920x1080 clean.
2. **The full suite passes on the commit packaged** (golden replays included: they protect the game's rules, and they are cheap).
3. **One end-to-end check** of that package covering Story to the truck and Hold the Block waves 1 to 3. A focused check that
   finishes counts; it does not have to be repeated after a small, safe fix the fixer re-checked on the package himself.
Dropped as GO gates (they become release notes and next-release items, still worked on): "every smoothness number better than or
equal to v4", a second independent review after every small fix, cosmetic hand poses on one gun (the SHORTY's and the STICK's reload
hands), faint guide path in some sun frames if the marker and step line still lead, and the trimmed polish nits.
The release gate after the GO is cut to one sanity run of the package under the E3DS-class load (the smoothness lanes measured it
at length already), then the upload and one session on E3DS's own page before the owner switches the pin.

## 2026-11-27 ~20:30 UTC: multiplayer waits until single player is shipped

The owner asked for a Multiplayer button for players signed in to the IPX website (a lobby, play together in one session), then:
"lets get single player pushed and finalized before working on multiplayer". The design workflow (mi-multiplayer-design) was stopped
at its research step; it resumes after v6 is live on E3DS. Order: v6 single player to E3DS, then multiplayer design, then the
three-map release as planned (or as the owner reorders it).

## 2026-11-27 ~22:15 UTC: the drones (Buzzards) are removed from the game

The owner: "Forget about the drones. Remove them from the game. They are inconsequential. I don't want us to waste time on drones."
The Buzzards no longer spawn in the Story or in Hold the Block; a wave ends when its Goons are down. The last-drone rule (2026-11-27
~00:10) is moot. Prefer a data switch that turns them off (spawn weights, wave tables, air spawn points unused) over deleting code, so
they can come back later. Golden replays and tests that pin the drones: keep them passing by running them with the drones switched
on in the test set-up where that is how they were recorded; where a test asserts the shipped game's behaviour, update it to "no
drones" (an owner-made rule change, not a weakened test). No HUD text, objective, voice line or menu may mention drones afterwards.

### How it was done (v6 closer, drones removal)
`config.json` `flow.drones` is `false`: `MIEnemy::DronesOn(Config)` reads it. Off, `FMIFlowTune::Parse` reads every Buzzard count as 0
(patrol, Story waves, the pursuit share) and `HoldoutWave` has no Buzzards, and `FMIEnemyTune::Parse` sets the Buzzard pool to 0, so no
Buzzard actor is pooled and `Spawn(Buzzard)` finds no slot. The air spawn points stay in the level data, unused. The rest of the Buzzard
code and its data stay: set `flow.drones` to `true` and they are back. Tests that pin the drones (Golden.FlowRules, Golden.Directors,
Golden.EnemyLogic, Golden.Enemies, V6.LastDrone, V6.LastDroneSweep) run inside `MIEnemy::FMIDronesScope`, which forces them on; the new
`MurderInc.V6.NoDrones` asserts the shipped data has none. The radio line "They made you" no longer names them ("Goons on foot, and more on
the way", the same length so the radio pacing of the recorded replays holds; the golden's text was updated, an owner-made rule change).

## 2026-11-27 ~22:20 UTC: the game's goal, in the owner's words

"The goal is for the player to have fun, lock onto the targets as they shoot, and progress from one level or map to the next."
Consequences for the plan:
1. **Aim assist ("lock onto the targets as they shoot")** is a v6 feature, right after the drone removal: soft target lock for
   mouse and pad (stronger on the pad): aim slow-down over a Goon, gentle pull toward the nearest Goon in a small cone while firing,
   and a snap to the nearest visible Goon when aiming down sights; a Settings toggle and strength; no lock through walls; tuned so it
   helps over the stream's latency without playing the game for the player. It changes how play feels, not the rules: the golden
   replays (scripted input) run with it off.
2. **Progression across maps** is the core of the game: after v6 ships, the three-map release (docs/unreal/MAPS.md) comes before
   multiplayer unless the owner says otherwise.

### How it was done (v6 closer, aim assist)
`Player/MIAimAssist.{h,cpp}` is the assist without the engine (`FMIAimAssist::Step`); `AMIPlayerController::UpdateAimAssist` gathers its
input each frame: every live `AMIGoon` within `assist.range` whose chest point (`chestFraction` of the body capsule's half height above its
centre) lies within the widest reach of the three parts, the nearest four by angle each tested with a line trace on the bullets' own channel
from the eye to the chest (a wall, cover or another body in the way means no help of any kind). The three parts, all numbers in
`config.json` `player.input.assist` (`pad` and `mouse` blocks, `strengths`, `range`, `slowRate`, `magFalloff`, `minSlow`):
1. Slow-down: inside `slowRadius` (pad 2.5 deg, mouse 2 deg) of a visible Goon the look rate is scaled by `slow` (pad 0.45, mouse 0.8), eased
   at `slowRate`. For the pad it replaces the weapon rules' older 0.55 ray test while the assist is on (the deeper of the two applies);
   the mouse's counts are scaled the same way. Off, the old pad behaviour is unchanged.
2. Magnetism: while the fire button is held, the nearest visible Goon inside `magCone` (pad 6, mouse 3 deg) pulls the view toward its chest,
   at most `magRate` deg/s (pad 22, mouse 10), fading to nothing over the last `magFalloff` degrees. The pull is cut by the cosine of the
   player's own turn against it (gone at 120 degrees away): his input direction always wins. The turn is added to the rules' yaw and pitch
   directly (`FMIPlayerInputState::AssistDegrees`), outside the look rate, and is zero with the assist off, so the rules and the golden
   replays are untouched.
3. ADS snap: on the press of aim (not while it is held), the nearest visible Goon within `snapAngle` (pad 10, mouse 5 deg) is turned onto
   over `snapTime` (0.12 s), landing exactly on the chest; it follows the target up to 1.5 x the angle and ends when aim is released.
Settings (`Settings` card, saved with the others): "Aim assist" On/Off (default On, `config.json` `settings.defaults.aimAssist`) and "Assist
strength" Low / Normal / High (`aimAssistStrength`; the factors 0.6 / 1 / 1.4 scale every radius, cone, angle, cap and the slow-down's depth).
Tests and replays: `Boot` with no save slot turns the assist off (`FMIBootOptions::bAimAssist` asks for it), and a bare controller starts with
it off until the game flow applies the settings. `MurderInc.Assist.Data`, `.Math` and `.World` pin the data, the arithmetic and the engagement
(slow-down, pull, snap, a wall in between, switched off).

## 2026-11-28 ~02:00 UTC: v6 GO, and E3DS storage

- **v6 is GO** under the trimmed bar. The packaged commit is 1095726 (aim assist), with zip sha256 `7bbb3f14e4fc555129c3d4225b91ccfc52c8a9fe742676fd700cf6a4938ae6df`.
  - The full suite passes 232 of 232.
  - The check passes: Story to the truck, Hold waves 1–3, the aim-assist settings toggle, and no lock through walls.
  - Aim assist raises hits per magazine (pad hip 73%→97%, mouse hip 53%→78%), but does not shorten the time to put the crosshair on a Goon. To make acquisition faster, tune the pad's slow-down radius or the snap angle in `player.input.assist`.
- **E3DS storage** (10 GB on the plan) held 4 versions of MurderInc at 2.1 GB each, leaving 1.6 GB free.
  - The owner chose to delete Versions 2 and 3 and keep 4 as the rollback and 5 as live.
  - Legacy links pinned to those versions break; the project link always streams the newest version.
  - Each upload adds about 2.1–2.4 GB, so delete an old version before every release.
- **Upload path:** the owner signs in (Google) in the plain owner browser on the box, and it is then driven with xdotool plus screenshots. Do not restart it under remote control: the Google sign-in does not survive a restart, which was tried twice on 2026-11-28.
- **02:15 UTC: v6 is live on E3DS.**
  - The upload took 33 s and Prepare 37 s. E3DS's test passed in 1 min 21 s, and the build went out to the USA and France machines.
  - MurderInc is now **Version 6**, which the project link streams. Versions 4 and 5 are kept.
  - Stream check from the box: the title menu, CLICK TO PLAY, the Crew screen and the Loadout screen (all five guns, attachments) render and take input.
  - Clicking through the stream from the box's software-rendered browser lands in the wrong place, so the in-mission play check is left to a person playing on a real browser.

## 2026-11-28: attachments are on the Loadout beside the rack; the flicker was the hover and the wrapped text of a screen built again (owner, v6 on E3DS)

**Owner:** "the screen flickers when adding attachments to weapons. It's also difficult to navigate to the attachment options. When
you click a gun the option for attachments should show up in the frame with it, so users can click weapon, add attachments, then
navigate to the game."

**Decided:** the Loadout is one screen: the rack and the four slots on the left, the focused gun's attachments in a panel beside them
(slot chips, the options of the slot, the effect lines and six bars of the part in focus, Reset, the keys of the device in use),
the 3D gun on the right showing every look and fit. The picked gun is marked `Selected`. Nothing is behind E: Right from the last
card, E, or Enter on a carried gun enter the panel by keyboard (D-pad right or Y on a pad), a click works it directly. The Workbench
screen stays for the console (`MIMenu fe bench <gun>`) and the tests; no control opens it. LOADOUT.md 2.6a.

**The flicker, found by measurement.** Reproduced in the Shipping game at 1920 x 1080 (-sm5) through the stream with the viewer script
`tools/box/cloud/loadout-flicker.txt` and `rtcinput.py --trace` (mean level of every received frame; the same script plays on the old and
the new screens): at every fit, every look at a part and every part taken off, the mean level drops by 1 to 1.5 (2 to 3 %) for one or two
frames and comes back (13 such blinks in the 65-second script; a blink is a level that jumps 0.5 or more and returns within three frames).
Thumbnails of the frames (`--thumbs-every 0.04`) show where: the stage is the same level in every frame (the right 40 % of the picture,
55.4 in all of them), the blink is in the controls, and in the first run one frame shows the options panel half laid out. Two causes, both
in how the screens are built again at every part change (`UMIFrontEnd::Tick` builds them on the game thread, before Slate's frame):

1. The button under the pointer is replaced by a new one, and Slate gives a new button its hover a frame or two after its first paint,
   so the card the pointer rests on (the player has just clicked it) is drawn plain for those frames and then hovered again: a flip at
   every rebuild. The viewer's pointer rests on the CHOPPER's card; the card's region is 37 then 33 then 37 in three frames. Fix:
   `SMIFrontEnd::PointerOver` (the last layout of the tracked buttons against the cursor) gives a card, slot, option or chip built under
   the pointer the hover look at once (`ButtonStyle(..., bHoverLook)`); its end (`OnUnhovered`) builds the screen again with the plain look.
2. Every text that wraps was `AutoWrapText`, which measures itself at the width of its last paint; a new one has none and was drawn once
   on one line, clipped (the first run's thumbnail: Red dot's blurb cut to "Gets on target fast, a little", the effect lines and bars
   missing). The engine's header says "the wrapped size will be computed at least one frame late". Fix: every wrapped text of the
   Loadout is given its width (`Txt(..., WrapAt)`). `MurderInc.Frontend.FirstLayout` fails on the old code (26 auto-wrapping texts).

Result, same script, same package otherwise: blinks 13 (v6 screens), 12 (inline panel, text fix only), 2 (both fixes), and the 2 left are on
Home, before the Loadout, none at a fit, a look or a removal.

**What was suspected and is NOT the cause** (measured, kept out of the change): the 3D stage. The same package run with the stage's old
behaviour on and off (a camera cut marked at every part change, the whole gun built again at every change, the jump to a mount's side)
gave 11 to 15 blinks each, all three on or all three off alike. Those three stage changes were taken out again.

**Also changed:** the stage room is 2000 x 2000 x 600 (was 1200): the Loadout column is 58 % wide, the gun is framed in the part
the column leaves, a long gun with parts put the camera outside the room's wall. The Loadout is wider only on the Loadout; the
free part of the stage eases between screens (`AMIShowroom::SetFreeLeft`).
