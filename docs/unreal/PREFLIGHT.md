# MURDER INC. on E3DS: launch pre-flight and decisions

Written 2026-11-25, about 00:05 UTC, by the release lead. It merges four reviews of version 2 against E3DS's own
documentation (hosting contract, play through the stream, GPU performance, website and launch). Each review was
re-checked by a verifier. Fresh checks were added for this page: the Unreal 5.9 engine source on the GPU box, the box
logs, E3DS's live Linux player script (version 1.0.146, read on the box without saving it) and E3DS's public iframe
demo. Refuted points are left out (they are listed at the end).

Sections 1 and 4 are for the owner. Sections 2, 3, 5, 6 and 7 are for the next engineer and for Cursor.

## Where we are

- **Version 2 streams on E3DS.** The zip with sha256 `ceaf828d…` (game `e989cb8`, launcher `f827e1b`) loaded and
  streamed on 2026-11-24 (`docs/unreal/DECISIONS.md`, 23:10 UTC). The start-up crash of version 1 is fixed.
  (The zip `82ed886a…` named in some notes was never uploaded. It is the same game with an older launcher.)
- **Play is the problem now.** The owner's words: "sticky", "not fluid", "lag", and later "very laggy; when the
  player turns it slows down; it is not a viable experience".
- **The mechanism is now reproduced on the box** (DECISIONS.md, 23:39 UTC, logs in
  `/project/ue/cloud/lag-2026-11-24/`): when the GPU cannot finish frames in time, Pixel Streaming 2's capture waits
  for the GPU (up to 100 ms per captured frame) and one game frame can last seconds (worst frames 1.8 to 7.2 s).
  Turning costs more GPU time, so turning is what tips it over. With GPU head-room the same build is steady (60 frames
  a second at 1280 x 720, or a steady 30 with a 30 cap). `-PixelStreamingDecoupleFramerate` neither causes nor cures
  it. What we still do not know is how much head-room E3DS's machine lacks: its GPU, the game's frame rate there,
  the stream's frame rate and the round trip were not collected.
- **Version 3 is being built.** Input work is committed (`05f5e8b` to `b25b888`, 23:59 UTC), not yet packaged. The
  rendering work has not started. Section 2 changes what version 3 must contain.
- **The owner's binding decision** (DECISIONS.md, 23:10 UTC): fluid, responsive play comes first and the look
  second; version 3 must adapt to whatever GPU E3DS gives it; the delay must be measured and cut; a PS5 or Xbox
  controller must work from the first screen to the end of a run.

## The short version

1. Version 2 works. The lag has a known mechanism: the server's graphics card runs out of time, and the streaming
   plugin then stalls the game. Version 3 must never let the card run full.
2. Before version 3 is packaged, run three short test sessions (section 1, about 20 of your 300 monthly minutes) and
   send back what 1.5 lists. Two of them try the fixes that need no new build: a smaller picture (1280 x 720) and a
   30 frames-a-second cap. If one plays smoothly, keep it until version 3.
3. Fix one setting now: **Log Out Countdown Timer Length is counted in minutes.** Put 1, not 30.
4. Send E3DS support the message in 1.6. Which graphics card your Linux sessions get decides how far version 3 must
   lower the picture.
5. Version 3 will lower its own picture quality when the server's card is slow, keep about 60 frames a second, show
   its own numbers on the pause screen, fix the mouse speed and make a controller work everywhere.
6. Do not make the page public before section 4 is done. 300 minutes is only about 20 to 30 player sessions a month.

---

## 1. For the version 2 test (now)

### 1.1 What we still need, and why

| What | Why it matters |
|---|---|
| The GPU model, driver and memory of the Linux machine | E3DS's FAQ: apps run on "RTX 4080 and 5070 in the E3DS datacentre, and typically T4 or A10 on cloud providers" (https://docs.eagle3dstreaming.com/wiki/faq-frequently-asked-questions/). A Linux machine "is being allocated and started" for each session (https://docs.eagle3dstreaming.com/wiki/linux-upload-and-stream/). A T4 would run the game as packaged at roughly 15 to 25 frames a second (estimate: the box's card is many times faster). That would feel exactly "sticky". |
| The game's own frame rate and GPU time there | They show how far over its budget the card is, so version 3 knows how much to cut. |
| The stream's frame rate, resolution, bitrate and round trip | E3DS's Info panel shows them ("the network round trip, data received, resolution, frame rate, codec and bitrate", https://docs.eagle3dstreaming.com/wiki/features-api-live-connection-state/). They separate a slow card from a slow network. |
| Whether a smaller picture or a 30 cap is enough there | Both need no new build. On the box, 1280 x 720 gave 59.6 frames a second with no stalls, and a 30 cap gave a steady 30 (DECISIONS.md, 23:39 UTC). E3DS itself suggests `t.MaxFPS 30` in its console-commands field to save GPU (https://docs.eagle3dstreaming.com/wiki/command-line-parameters/). |
| Whether `-PixelStreamingDecoupleFramerate` should stay | The first test used it. It neither causes nor cures the stall (box, 23:39 UTC), and for an app that draws under 60 E3DS measured repeats and a slower app (https://docs.eagle3dstreaming.com/wiki/app-draws-60-viewer-gets-15/). So the sessions below leave it out. |

### 1.2 Settings, in Control Panel order

Path (E3DS's names, https://docs.eagle3dstreaming.com/wiki/project-settings/): **Your Projects → Project_MurderInc →
Settings (the gear)**. The tabs are Project Setting, Builds, Viewer Experience, and Sharing & live access. In
Viewer Experience, the **Search settings** box finds any setting by a word (for example "mouse"). Nothing is kept
until you press **Save changes**, and changes apply to new sessions only.

| Where | Setting | Value | Why |
|---|---|---|---|
| Builds | Running build, Run a fixed version | `MurderInc`, **Latest** | the version that streamed |
| Builds | version list | **Delete** beside version 1 (never the build's trash icon) | version 1 never worked; this frees 2.2 GB of the 10 GB for version 3 |
| Viewer Experience, Common | Browser Resolution | **Custom**, both boxes filled: **1920 and 1080**, or **1280 and 720** for session B (1.3) | a fixed size; empty boxes mean Dynamic (https://docs.eagle3dstreaming.com/wiki/resolution/) |
| Common | Max Session Time (minutes) | **15** | E3DS's default ("If the field is left empty, 15 minutes applies too", https://docs.eagle3dstreaming.com/wiki/session-and-access/); a test needs under 10 |
| Common | Log Out Automatically After Inactivity | **On** | ends forgotten sessions |
| Common | Minutes Until Log Out Countdown Starts | **3** | |
| Common | Log Out Countdown Timer Length | **1** | this field is in minutes too: E3DS's player multiplies both values by 60 (player 1.0.146: `afkCloseTimeout=60*r`, default 1). 30 would mean a 30-minute countdown |
| Common | Password Protect Stream | **On while testing**, a password only testers know | never put it in the website, never give it to Cursor |
| Common | Anonymize URL | **Off for now** | turn it on before going public (section 4); it changes the link |
| Search "mouse" | the mouse mode | **Locked**, not Hovering; any browser-cursor switch off | E3DS's player reads this as `MouseControlScheme` ("1" means Hovering). Hovering stops the view turning at the picture's edge |
| Viewer Experience | Advanced Options | **On** | shows the UI, Branding, Developer and Microphone tabs |
| UI | Settings Control Bar, Quality Control Menu | **On** | the gear, and the Info panel with the readings |
| UI | Draggable Settings Button | **On** | the gear sits bottom right, over the game's weapon strip |
| UI (or search "autoplay") | Autoplay | **On** (default) | |
| UI (or search "touch") | Fake Mouse With Touch | **Off** | |
| Developer | Platform | **Linux** | "The Platform field offers Streaming App, Windows and Linux" (linux-upload-and-stream) |
| Developer | Select Region | **Global** (default) | "the nearest free machine" (https://docs.eagle3dstreaming.com/wiki/select-region/) |
| Developer | Video Quality | **Medium** (default) for these sessions | a higher level "can cost smoothness on the way" (https://docs.eagle3dstreaming.com/wiki/features-api-video-quality/); fix smoothness first |
| Developer | Codec | **H264** (default) | |
| Developer | Print UE log in browser console | **On** (test sessions only) | the only way you can see the game's own lines |
| Developer | Email To Send Log Upon App Crash | **On**, your own address | "the only one of the three that works when the crash happens to somebody else" (https://docs.eagle3dstreaming.com/wiki/developer-options/) |
| Developer | Launch options (Parameters To Pass To App on older panels) | **per session, see 1.3** | |
| Developer | Console Cmds To Pass To Unreal App (newer panels: "Unreal console commands to run at start") | **empty**, except in session C | "runs Unreal console commands as the session starts" (developer-options) |
| Microphone | Use Browser side Microphone | **Off** | |

Then **Save changes**, and open the link from the project (Open Stream or Copy Link).

### 1.3 Three short sessions (and two optional)

Use a new **Chrome Incognito** window for each (no extensions, no saved session). **Before** opening the link,
press F12 (Cmd+Option+J on a Mac), choose **Console**, and type `MICloud` in its filter box. Change only what the
table says between sessions, and Save changes each time.

| Session | Browser Resolution (Common) | Launch options (Developer) | Console Cmds To Pass To Unreal App (Developer) | What it tells us | Minutes |
|---|---|---|---|---|---|
| A | Custom 1920 x 1080 | `-MICloudProbe=5` | empty | the game as E3DS starts it, without decoupling: GPU, game frame rate, GPU time, stream frame rate | about 7 |
| B | **Custom 1280 x 720** | `-MICloudProbe=5` | empty | is a smaller picture enough head-room on E3DS's card? | about 7 |
| C | Custom 1920 x 1080 | `-MICloudProbe=5` | **`t.MaxFPS 30`** | is a 30 cap enough head-room? It also shows whether E3DS's console field reaches the game: the probe lines then say `fps=30.0` | about 7 |
| D, only if session A's console showed no `[MICloud]` lines | as A | `-MIDev -MICloudProbe=5` | empty | the Development game. In play, press the key left of 1 (`` ` `` or `~`) to open its console, type `stat unit`, press Enter: Frame, Game, Draw and GPU times appear on the picture. Screenshot them in a fight. Remove `-MIDev` afterwards | about 5 |
| E, optional, last | as A | `-MICrashTest=45` | empty | the game crashes on purpose 45 seconds after the start (version 2 only; version 3 removes this switch). Check E3DS's crash email: is a log attached, and does it end with `CRASH: ... SIGSEGV`? | about 1 |

**After the sessions:** if B or C played smoothly, keep that setting until version 3 (B first: 60 frames a second
matter more in a shooter than sharpness). Empty the console field again if you keep B. In session B the mouse turns
slower than in A (version 2 scales the mouse by the render width); that is expected, and Look sensitivity can make
up for it.

`-MICloudProbe=5` prints one line every 5 seconds: frame rate, worst frame, GPU time, memory, game state
(`Source/MurderInc/Cloud/MICloud.cpp`, probe). The launcher passes unknown options on to the game
(`tools/box/cloud/MurderInc.sh:65` at `f827e1b`). Version 2 runs a viewer's console command without a filter
(Pixel Streaming 2's default handler, `PixelStreaming2RTC/Private/RTCInputHandler.cpp:714-722`), so session C's
command works if E3DS delivers it.

### 1.4 What to do in each session, and what to watch

1. Note the time you open the link, and how long until the picture appears.
2. At **CLICK TO PLAY**, click once. No sound? Press the **speaker button at the bottom right** of the picture.
3. Stay on the home screen for 30 seconds without touching anything. Open the gear, then **Info**. Screenshot it.
4. **Gear Up** → crew → loadout → block → briefing → a **Story** run. Play 3 minutes: walk, turn left and right
   fast, shoot, fight. During a fight, screenshot **Info** again.
5. The turn test: move the mouse slowly to the right by a hand's width, then fast by the same width. Does the view
   turn the same amount both times? Does it stop the moment your hand stops?
6. Session A only, at the end: turn Wi-Fi off for 10 seconds, then on. Does the game come back, or does the session
   end?
7. Close the tab. That ends the session. In the console, right-click and choose **Save as...**.

What you see tells us the cause:

| You see | Most likely cause | Version 3 answer (section 2) |
|---|---|---|
| The game slows down or freezes for a moment when you turn, and catches up | the server's card has no head-room: the streaming plugin's capture then waits for the card and stalls the game (reproduced on the box) | now: session B or C's setting; version 3: V3-1, V3-2, V3-3 |
| Choppy even when standing still; Info frame rate under about 40 | the card is too slow for the full picture, or frames are lost between the game and the video encoder | V3-1, V3-2, V3-3 |
| The picture is smooth, but the view answers late and keeps moving after your hand stops | delay. Info round trip over about 80 ms: distance or network. Under about 50 ms: the game or the encoder queues frames | V3-4; region |
| The view turns much too fast, or slow moves feel sticky while fast ones jump | mouse scaling through the stream (about 2 to 3 times too fast in version 2; slow moves lose counts) | V3-6. For now: Look sensitivity about 0.35 to 0.5 (press P, Settings; arrow keys and Enter) |
| The view stops turning at the edge of the picture, and a cursor shows | the mouse is in Hovering mode | set the mouse mode to Locked (1.2) |
| A short freeze every 15 to 30 seconds | the small hitches also seen on the box | profiled later; not a version 3 blocker |
| Blocky or smeared picture while moving | bitrate: E3DS calls under about 4,000 kbps at 1920 x 1080 in a moving scene poor | Video Quality, after smoothness is fixed |

E3DS's own scale for the round trip: "Under 100 feels instant. Over 250 is noticeably slow to respond" (live
connection state page). For a shooter, aim for under 50 ms.

### 1.5 What to send back

- For each session: its launch options, the time it started, how long until the picture, both Info screenshots,
  and the saved console file. If the file is large, screenshots of the lines that start with `[MICloud] GPU:`,
  `[MICloud] Features:`, `[MICloud] Command line:` and `MICloudProbe` are enough.
- Your answers: choppy or smooth? Did turning slow the game down? Late or immediate? Mouse too fast, too slow or
  uneven? Which of A, B and C felt best? Did the session survive the Wi-Fi drop? Was there sound after the click, or
  only after the speaker button?
- Session D: the `stat unit` screenshot from a fight. Session E: the crash email (is a log attached, what is in it).
- E3DS support's answers to 1.6.

### 1.6 A message to E3DS support (by email or Discord, as their pages list)

> My Linux app MurderInc (project Project_MurderInc, Unreal 5.9 with Pixel Streaming 2) streams but feels laggy.
> Please tell me: (1) which GPU model, NVIDIA driver version and graphics memory my Linux sessions run on, and in
> which region; (2) whether my Linux sessions can run on your RTX 4080 or 5070 machines rather than T4 cloud
> machines, and what that costs; (3) which file your crash email attaches for a Linux app, and which `-ABSLOG=` path
> you pass; (4) the file `MurderInc/Saved/Logs/MurderInc.log` from my session at <time, UTC>, if that machine still
> has it; (5) how many Linux sessions can run at once on my plan in the US and in Europe, and whether warm Linux
> capacity can be arranged for a launch date.

---

## 2. Version 3: the must-fix list

> **Release A measured (2026-11-25; `docs/unreal/PROGRESS.md`, "Version 3, release A: the lag").** The cause is
> not the capture: a game that renders off screen never waits for the GPU, and the unfinished frames pile up while
> the view turns (up to 79 were counted; the pile is the frame of seconds). Where the items below say "the capture
> stalls the game" or "a full GPU stalls", read that. What changed against this list: **V3-1** gained a third part,
> a pacer that holds the game back while the GPU still owes it more than one frame (`MI.Cloud.GpuFramesInFlight`);
> it alone passes the release gate, dynamic resolution and the frame-rate target keep the picture and the pacing
> good on top of it. The target does **not** drop at 70 % of the frame time: it drops only while a run is being
> played and only when the game falls short of the rate because it waits for the GPU (at 70, 85 and 90 % a rate
> that was being held was lowered; DECISIONS, "Decisions of release A").
> **V3-3**: no capture setting changes the stall or the frames delivered; Pixel Streaming's defaults stay,
> decoupling stays off, there are no `-MIDecouple` switches (Pixel Streaming's own
> `-PixelStreamingDecoupleFramerate=true` works). **V3-4, first bullet**: run `gp-in5`'s memory and slow exit are
> the same pile (about 11 MB for every unfinished frame), not version 3's code. **V3-5**: the pause card's line
> has no quality level yet (V3-2 is release B). **V3-6**: 3840 x 2160 output misbehaved in one run (the encoder at
> 46 frames a second, a viewer's leaving missed, no shutdown within 30 s): limit the size before allowing Dynamic.
> **The gate's "no fence time-out line"** can only be read in the Development game (Shipping has no engine log);
> the Shipping game is judged by its probe lines (`owed=`, `worstMs=`). The gate as a queue of runs:
> `tools/box/cloud/lag-gate.txt`.
>
> **Release A reviewed (2026-11-25; PROGRESS.md, "Version 3, release A: the review's findings").** Ten faults,
> all real, all fixed. What changes in this list: **V3-1**: the pacer waits on the render thread (on a server with
> 8 hyper-threaded CPUs or fewer the first form froze for 250 ms a frame), the gate has runs on 6 CPUs, the target
> rises by the next rate's frame time, and dynamic resolution turned out a weak lever (an eighth of the GPU's time
> follows the picture's size): **V3-2's quality steps matter more than this list assumed**. **V3-6**: the size cap
> (640 x 360 to 1920 x 1080) and the mouse scale for a size that was cut down are in; the rest is release B.
> **V3-7**: a controller's first press now counts, X reloads or grabs, a trigger pulled when the viewer leaves is
> let go. **V3-9**: the fog's variables and the quality groups have ranges, the stream's debug dumps are refused,
> the Development game needs a key (`-MIDev=<key>`). **New for the owner's next test**: a double click no longer
> leaves the fire button held; the pause card's stream number runs a few frames below the game's by itself.

> **Release A delivered as version 3a (2026-11-25; PROGRESS.md, "Version 3a: packaged, gated and delivered").** Zip
> sha256 `de41a708…58e4`, game and launcher `6c4d810`. The gate was run on the zip itself, unpacked as a new user
> with an empty home into a fresh folder and started with E3DS's arguments, and passes: no frame over 50 ms in play
> at any load, on 16 CPUs and on 6 (38 ms in the Shipping game's Story runs). **New for V3-12:** such a cold start
> has numbers now: the game's first frame takes 3 to 4.5 s (before anybody is connected) and the first set-up
> screen (Crew) costs one frame of about 0.85 s, both gone with a warm graphics-driver cache, which a host that
> starts every session on a new machine never has. **New for V3-7:** after the press that hides the click card, the
> home screen lists the keyboard's keys until the next controller press. The owner's settings for version 3a are in
> LAUNCH.md 9.1 (Browser Resolution Custom 1920 x 1080, launch options empty); section 1.2's table is from the
> version 2 test.

Everything below ships in **one** version 3 build. The build itself costs about an hour of box time (package, the
full test suite, the E3DS-style runs, a stream test with input) and about an hour of the owner's time (download,
join and upload 2.25 GB). The cost given per item is the extra engineering work. "Status" is the state at commit
`b25b888` (23:59 UTC). The plan items A1 to A7 and B1 to B8 are those of `tools/workflows/mi-final-build-wf_f2b11273-c65.js`.
**Where this list and that plan differ, this list wins** (the plan itself says so). Game-source line numbers are
those of commit `202f020` (the working tree is being edited).

Order of work if time is short: V3-1, V3-3 (the two that end the stall), V3-5, V3-6, V3-2, V3-7, V3-4, V3-9's
allowlist fix, V3-10, V3-11, then the rest.

**The release gate for all of it** (DECISIONS.md, 23:39 UTC: "nothing may block a frame for more than a few
milliseconds while a run is being played"): on the box, with the GPU loaded the way the lag was reproduced
(`r.ScreenPercentage 200`, or two copies of the game on one card, `/project/ue/cloud/lag-2026-11-24/`), a Story run
with fast turning has no game frame over 100 ms and no "Timed out waiting for fence" line.

### V3-1. Never run the GPU full: a head-room controller (plan B3, now the first must-fix)

- **Change, part 1: dynamic resolution.** `unreal/MurderInc/Config/DefaultGame.ini`, section `[MICloud]`, add:
  `+CVars=r.DynamicRes.OperationMode=2`, `+CVars=r.DynamicRes.FrameTimeBudget=16.67`,
  `+CVars=r.DynamicRes.TargetedGPUHeadRoomPercentage=30`, `+CVars=r.DynamicRes.MinScreenPercentage=50`,
  `+CVars=r.DynamicRes.MaxScreenPercentage=75` (V3-6 raises the maximum for small frames).
- **Change, part 2: the frame-rate target.** `Source/MurderInc/Cloud/MICloud.cpp`, in `UMICloudSubsystem::Tick`: if
  dynamic resolution is at its minimum and the GPU time over the last second is still above 70 % of the frame time,
  lower the target at once: 60 → 45 → 30 (`t.MaxFPS`, set with the cloud profile's priority, and
  `PixelStreaming2.WebRTC.Fps` to the same value). This lever needs no new shaders, so it is safe in the middle of a
  fight. Raise the target again only at a safe moment (V3-2), after 10 s well under budget. Log each change; show the
  target on the pause card (V3-5); `-MIFps=60|45|30` pins it.
- **Evidence.** The stall happens only when the GPU is full (box runs s0, s1, q0, q1 against s3 and s4,
  DECISIONS.md 23:39 UTC). Mode 2 means "Enable regardless of the game user settings"
  (`Engine/Private/UnrealEngine.cpp:523-530`). The default budget is 33.3 ms (`DynamicResolution.cpp:37`) and the
  default headroom 10 % (`DynamicResolution.cpp:47-51`). A 30 % headroom aims at about 70 % of the GPU, E3DS's own
  limit ("GPU RTX 4080 / 5070, 50-70% utilisation", https://docs.eagle3dstreaming.com/wiki/system-requirements/).
  Linux Vulkan supports dynamic resolution (`VulkanGenericPlatform.h:106`, GPU review). 75 % keeps the internal
  picture at version 2's size (73 % at 1080p). `PixelStreaming2.WebRTC.Fps` defaults to 60 and can change while
  running (`PixelStreaming2PluginSettings.cpp:506-508`). E3DS's own advice for an app that cannot draw 60: "a fixed or
  smoothed frame rate set to 30" (app-draws-60-viewer-gets-15).
- **Accept only** after the release-gate runs above: no pumping, no hitch when the size or the target changes.
- **Cost.** About a day with the box runs.
- **Player gains** a game that never freezes on a turn, at 60 frames a second wherever the card allows. **Loses**
  some sharpness, and on slow cards 45 or 30 frames a second, which is still far better than multi-second freezes.

### V3-2. Step the quality down by measured GPU time (new; overrides plan B3's "Do NOT lower Lumen, Nanite or shadow quality")

- **Change.** `Source/MurderInc/Cloud/MICloud.cpp` and `.h`: a governor in `UMICloudSubsystem::Tick`, next to
  V3-1. Every 5 s it averages the GPU time (`RHIGetGPUFrameCycles`, already read by the probe). If V3-1 had to lower
  the frame-rate target, or dynamic resolution sat at its minimum for 10 s, it steps the quality down one level at the
  next **safe moment** (home screen, set-up screens, pause, between waves, before a run starts: quality changes can
  compile shaders and re-light the scene, so never in a fight), and then lets V3-1 try 60 again. Order: Lumen at
  Epic's 60-fps level
  (`sg.GlobalIlluminationQuality=2`, keeping `r.Lumen.TraceMeshSDFs.Allow=1` for the no-ray-tracing fallback) and
  volumetric fog at High (`r.VolumetricFog.GridPixelSize=16`, `r.VolumetricFog.GridSizeZ=64`); then shadows,
  reflections and effects at 2; then Lumen off (`sg.GlobalIlluminationQuality=1`) and post-processing at 1 (the
  frame-rate target stays V3-1's lever). It steps back up only on the home screen, when the GPU stays under 8 ms. Apply groups through the
  existing `UMICloudSubsystem::ApplyStreamedQuality`. Log each step, show the level on the pause card (V3-5), and
  add a launch option `-MIQuality=0..3` that pins a level. The exact cvars per step come from `BaseScalability.ini`,
  checked on the box.
- **Why.** The owner's decision of 23:10 UTC. A T4-class card would otherwise give 15 to 25 frames a second.
- **Cost.** About a day with box tests on a slowed GPU (DECISIONS.md item 2 asks for the same set-up).
- **Player gains** about 60 frames a second on T4- or A10-class cards. **Loses**, on such cards only: flatter
  bounce light, softer shadows and reflections, at worst 30 frames a second. On an RTX 4080 nothing changes.

### V3-3. Capture settings chosen by measurement under load (replaces plan B7's fixed decouple default)

- **Measure first,** on the box with the GPU loaded as in the release gate, one change at a time, and keep what removes
  the multi-second frames without tearing or a worse received picture: `PixelStreaming2.CaptureUseFence` (default on;
  "non-fenced is faster but less safe", `PixelStreaming2PluginSettings.cpp:376-378`), `PixelStreaming2.UseMediaCapture`
  (default on, `:330-332`; the stall's wait is `UPixelStreaming2MediaIOCapture::WaitForGPU`, which spins up to 0.1 s
  twice per frame), `PixelStreaming2.WebRTC.DisableFrameDropper` (`:963`), and `PixelStreaming2.WebRTC.Fps` equal to
  the frame-rate target (V3-1). Use `-PixelStreamingLogStats` (Development game) for the sender's own figures; the
  Python viewer's received rates are only a rough check (DECISIONS.md, 23:39 UTC).
- **Decoupling:** off by default. `Source/MurderInc/Cloud/MICloud.cpp` turns `PixelStreaming2.DecoupleFramerate` on
  only while the game holds 57 frames a second or more, and off below 50 (at most one change per 10 s); keep this only
  if the measurement above shows a gain. Launch options `-MIDecouple` and `-MINoDecouple` pin it. Do **not** add
  `-PixelStreamingDecoupleFramerate` to the launcher's fixed arguments (`tools/box/cloud/MurderInc.sh:182`).
- **Evidence.** All these settings can change while the game runs: their changes are broadcast
  (`PixelStreaming2PluginSettings.cpp:293-303` for decoupling) and the frame thread is switched on or off
  (`PixelStreaming2/Private/VideoSourceGroup.cpp:206-219`). With a free GPU, decoupling raised the received rate from
  about 40 to about 55 (`/project/ue/cloud/verify-v2/fps-ab/`); under load it neither caused nor cured the stall. E3DS:
  decoupled with an app that draws about 25 gives "60 a second but most were repeats" and slowed the app to 19.
- **Cost.** Half a day of box runs.
- **Player gains** the most real frames on fast cards, and no capture stall on slow ones. **Loses** nothing if the
  measurement is followed.

### V3-4. Measure the delay and cut it (DECISIONS.md item 2)

- **Also explain one test run.** Box run `/project/ue/cloud/repro/gp-in5` (a version 3 test build, 23:34 UTC)
  logged 511 lines "UPixelCaptureMediaCapture::WaitForGPU: Timed out waiting for fence to be written!" (the same
  stall: `Engine/Plugins/Media/PixelCapture/Source/PixelCapture/Private/PixelCaptureCapturerMediaCapture.cpp`,
  `WaitForGPU`), but also reached 14.5 GB of memory and hung when stopped ("HUNG in shutdown, KILLed"). The memory
  and the hang are not explained by a busy GPU. Find out whether version 3's code causes them before packaging. (The
  runs `gp-in1`, `gp-in3` and `gp-in6` logged no time-out.)
- **Measure.** `tools/box/cloud/rtcinput.py` (`cbb41f4`) already sends input over the data channel. Add a
  time-stamped turn and measure the time to the first received frame that changed, at 60 frames a second and with
  the GPU slowed.
- **Then try**, in `[MICloud]`: `+CVars=r.GTSyncType=1` (the game thread waits for the RHI thread's previous frame
  instead of letting two frames queue: `RenderCore/Private/FrameEndSync.cpp:12-21`) and
  `+CVars=r.OneFrameThreadLag=0` (`FrameEndSync.cpp:6-10`). Keep each only if it lowers the measured delay and still
  holds 60.
- **Cost.** Half a day to a day.
- **Player gains** a shooter that answers the hand. **Loses** possibly a few frames a second (measured first).

### V3-5. The game shows its own numbers (the owner cannot read the server's log)

- **Change.** `Source/MurderInc/Cloud/MICloud.cpp`, the overlay's pause branch (`SMICloudOverlay::OnPaint`): one dim
  line at the bottom of the pause card when streamed: GPU name, game frames a second and the frame-rate target
  (V3-1), GPU ms, internal size → output size, quality level (V3-2), decoupled yes or no, build commit. Plus plan B5
  (a probe line every 30 s by default).
- **Cost.** An hour.
- **Player gains** nothing directly; the owner's screenshot answers what no log can. **Loses** one small line on the
  pause card.

### V3-6. The right mouse speed at every frame size: Dynamic resolution with the game's own limit (extends A1 and B2)

- **Change.** `Source/MurderInc/Cloud/MICloud.cpp`: replace Pixel Streaming 2's `Resolution.Width` command handler
  through `IPixelStreaming2InputHandler::SetCommandHandler` (the same call already replaces `ConsoleCommand`,
  `MICloud.cpp:677`). Today that handler runs `r.SetRes WxH` for any size of 1 or more
  (`PixelStreaming2RTC/Private/RTCInputHandler.cpp:724-741`). The new one keeps the aspect, caps at 1920 x 1080,
  ignores sizes under 640 x 360, runs `r.SetRes`, gives the mouse code the browser's width (so
  `FMIStreamMouse` scale = browser width / (2 x render width) is exact, `Player/MILookInput.h`), and sets
  `r.DynamicRes.MaxScreenPercentage` so the internal picture never has more pixels than version 2's 1400 x 788
  (100 % at 1280 x 720, 75 % at 1920 x 1080).
- **Then** the owner uses Browser Resolution **Dynamic** (E3DS's default). E3DS's player then sends a size request
  whenever the frame changes (it sets `MatchViewportRes` when the resolution type is Dynamic, player 1.0.146).
  `-MIMouseScale` stays as a fine-tuning switch.
- **Test on the box** (plan B2): resize while running; full-screen sizes 2560 x 1440 and 3840 x 2160 and a phone's
  1170 x 2532 (all clamped); memory and GPU time at each; the HUD (plan B6) at 1280 x 720, 1920 x 1080, 1440 x 900.
- **Fallback** if the run-time resize misbehaves on Linux: stay on a Custom size and set `-MIMouseScale` to
  frame width / (2 x render width) (0.333 for 1920 x 1080 shown 1280 wide, LAUNCH.md section 7's rule; 0.5 for
  1280 x 720 shown 1280 wide). The speed is then only right at that one frame width.
- **Cost.** Half a day plus the B2 box tests.
- **Player gains** the same mouse feel in the page, in full screen and on any monitor; no 4K load; a smaller frame
  costs less GPU. **Loses** native 1440p or 4K in full screen (a 1080p picture scaled by the browser).

### V3-7. A complete controller path (A2 plus DECISIONS.md item 3)

- **Status.** In code, not yet built: right-stick look with the web game's numbers (`05f5e8b`, `5835d9f`, `202f020`),
  menus with a controller, one action per tap, button names while a controller is in use, and a Settings row that
  chooses Xbox or PlayStation names (`b25b888`). That choice is right: Pixel Streaming 2 does not tell the game which
  controller it is (`RTCInputHandler.cpp`, `HandleOnControllerConnected` reads no payload).
- **Still to do.** The screens a player meets before reaching Settings must name both families ("✕ / A",
  "○ / B"): above all the CLICK TO PLAY card ("click, or press ✕ / A"). The card also says "Press a button on your
  controller once": browsers show a controller to a page only after a button press. Then every screen without
  keyboard or mouse: set-up screens, cards, Dead and Debrief, and back to home.
- **Test.** A whole Story run and a Hold the Block run with the pad only, through a real stream (`rtcinput.py`'s
  gamepad messages), as the plan's release step 3 and DECISIONS.md item 4 require.
- **Cost.** About a day.
- **Player gains** a PS5 or Xbox controller plays end to end. **Loses** nothing.

### V3-8. Clickable cards and the capture click (A3)

- **Status.** In progress (`2c346ed`, `5835d9f`, `c109303`: "the click that takes the mouse capture counts as input").
  Finish it and test it through the stream.
- **Player gains** a mouse click on RETRY or PLAY AGAIN works. **Loses** nothing.

### V3-9. Already in code: verify, and widen the console allowlist (A4 to A7)

- Graphics quality in a stream moves the scalability groups only (A4); a guest joining does not bring back the card
  (A5); the viewers' console allowlist (A6, `MICloud.cpp:380` and `:677`); debug commands out of Shipping (A6); the
  card's sound line (A7).
- **Keep the prefixes `PixelStreaming2.` and `PixelStreaming.`, and do not force
  `PixelStreaming2.AllowPixelStreamingCommands` off:** E3DS's player sends its own quality changes as console
  commands (player 1.0.146 sends `PixelStreaming.Encoder.MinQP ...`).
- **Must-fix in A6: also allow the tuning prefixes of V3-11** (`sg.`, `r.DynamicRes.`, `r.ScreenPercentage`,
  `t.MaxFPS`, `r.Streaming.PoolSize`, `r.GTSyncType`, `r.OneFrameThreadLag`, `r.VolumetricFog.`). E3DS's documented
  tuning field "Console Cmds To Pass To Unreal App" ("This is where per-app engine tuning belongs",
  https://docs.eagle3dstreaming.com/wiki/developer-options/; E3DS itself suggests `t.MaxFPS 30` there) most likely
  arrives as a viewer console command, so version 3's allowlist, as committed, would refuse it without a word.
  These cvars change only the viewer's own session.

### V3-10. Box tests that version 3 broke (release hazard; plan B8)

- `tools/box/cloud/e3ds-verify.sh:57` runs `v-crash` on the **Shipping** game with `-MICrashTest=30`. Version 3
  compiled that switch out of Shipping (`MICloud.cpp:436`, `#if !UE_BUILD_SHIPPING`), so the run no longer crashes.
  Run it as `-MIDev -MICrashTest=30`, and add a Shipping crash by sending SIGSEGV to the game's process from the
  harness (`kill -SEGV <pid>`), so the Shipping crash report keeps its proof.
- `tools/box/cloud/stream-test.sh:48` passes `-MICloudLog=`, which Shipping now ignores (`MICloud.cpp:77`). Read the
  `[MICloud]` lines from the game's own output (`game.log`) instead.
- **Cost.** An hour. **Player gains** nothing directly; keeps the crash-log proof honest.

### V3-11. Tuning without a new build (new)

- **Change.** `Source/MurderInc/Cloud/MICloud.cpp`: a launch option `-MICVars="name=value;name=value"`, accepted only
  for the prefixes `sg.`, `r.DynamicRes.`, `r.ScreenPercentage`, `t.MaxFPS`, `r.Streaming.PoolSize`, `r.GTSyncType`,
  `r.OneFrameThreadLag`, `r.VolumetricFog.` and `PixelStreaming2.`, set with `ECVF_SetByCommandline` (above the cloud
  profile's priority), each one printed in the log. A value set this way also pins V3-2 for that group.
- **Why.** Shipping compiles `-ExecCmds` and `-ini:` overrides out (`UnrealEngine.cpp:2542-2551`,
  `ConfigCacheIni.h:57`). E3DS's console-commands field is the other no-rebuild path (V3-9), but it arrives only once
  the stream is up and its delivery on Linux is unproven (session C tests it). Without one of the two, every tuning
  step is a 2.25 GB upload, and E3DS's pak patches do not cover code and are untested on Linux
  (https://docs.eagle3dstreaming.com/wiki/patches/).
- **Cost.** An hour.
- **Player gains** faster fixes. **Loses** nothing; a visitor who adds it to a link changes only their own session.

### V3-12. A smoother cold start (plan B4, corrected)

- **Drop** "load the enemies at boot": they are already pre-spawned at boot (`Flow/MIGameSubsystem.cpp:253`, "Both
  pools, pre-spawned and hidden").
- **Instead:** in `AMIGoon::Setup` give each pooled Goon its own outfit, `Variants[Slot % Variants.Num()]`, instead of
  `Variants[0]` (`Enemies/MIEnemyActors.cpp:231-233`), so all outfits' shaders compile on the home screen. Or add
  `r.PSOPrecache.Resources=1` under `[SystemSettings]` in `DefaultEngine.ini` (read-only, so it cannot go in
  `[MICloud]`: `Engine/Private/PSOPrecache.cpp:26-32`). Measure one cold run (new user, empty HOME) through the
  first fight.
- **Cost.** An hour and one cold run. **Player gains** fewer late-appearing Goons and hitches in the first minute.
  **Loses** nothing.

### V3-13. Smaller items (include if ready; do not hold the build for them)

- **Texture pool** (B1): `r.Streaming.PoolSize=1000` in `[MICloud]`; fix the comments ("8 GB" → 12 to 16 GB; shadow
  pages are 128 KB, not 64 KB). Check that committed memory stays under about 4.8 GB in a Story run.
  Gains: sharper surfaces. Loses: nothing on 12 GB or larger cards.
- **Launcher** (B7, without the fixed decouple default): signal 9 reported as "killed from outside"; the SM5 line
  says software Lumen stays; an `nvidia-smi` line every 30 s that ends with the game. Re-zip only.
- **HUD scale** (B6): needed once Dynamic sizes are used (V3-6).

### Not in version 3 (not worth a rebuild now)

A recorded PSO cache; the 20 to 70 ms hitches every 15 to 30 s (profile first, PROGRESS.md "steady hitches"); pak
patching (`-createreleaseversion`, only after E3DS confirms Linux patches work); a smaller zip; ending the session
from a Quit item in the game.

---

## 3. The website (Cursor): replacement text

Replace the whole section **"## Prompt to paste into Cursor (in the IPX website repository)"** of
`docs/CURSOR_HANDOFF.md` (today lines 21 to 149, from that heading to the end of the quoted prompt) with the text
between the two marker lines. It keeps the prompt of `ce1e944` and adds what the verifiers and the live checks found:
the queue and progress events must never be merged; E3DS's demo's event names; the events today's Linux player never
sends; the hidden-tab rule counts only from the picture; the forwarding case of a framed Game OS; a frame-src that
does not break other embeds; the leave warning; the speaker button; the locked mouse; the controller text; the iPad
check; "Look sensitivity".

----- replacement starts -----

~~~~markdown
## Prompt to paste into Cursor (in the IPX website repository)

The same text is what the owner receives as a file. It was written from E3DS's own documentation, E3DS's live Linux
player and E3DS's public iframe demo by the launch pre-flight (`docs/unreal/PREFLIGHT.md` explains each point).

> We are adding the game MURDER INC. to the IPX.exchange Game OS website. The game is an Unreal Engine 5.9 Linux build that runs on Eagle 3D Streaming (E3DS) servers and is streamed into our page in an iframe. Your job is only the website: the MURDER INC. page, its headers, its tests and its deployment. Do not download, join, upload or change the game build. Do not use any E3DS API, API key, login or Control Panel: I do all E3DS work myself, and whatever version I upload, nothing on the page changes. Never ask me for a password or a key.
>
> I will give you three things:
> (a) The Public Stream Link of the E3DS project, copied from the project itself (Copy Link). For this Linux build it starts with https://connector_linux.eagle3dstreaming.com/ or https://stream.eagle3dstreaming.com/. If I later turn on E3DS's Anonymize URL, the link changes and I will give you the new one.
> (b) The session limit in minutes that I set in E3DS.
> (c) Whether a test password is on.
> Until then, develop against E3DS's public Linux demo link, published on https://docs.eagle3dstreaming.com/wiki/linux-upload-and-stream/. It runs on E3DS's demo account, not on my minutes.
>
> 1. Where it lives
> - Add MURDER INC. to the Game OS game list with its own route. Follow the site's existing patterns for routing, layout, styling and the game list.
> - The E3DS iframe must be in the top-level document of that route. E3DS's Linux player sends every event with window.top.postMessage, so a page that is itself inside an iframe receives none of them. Prefer opening MURDER INC. as a full page. If the Game OS can only show a game inside its own iframe or window frame: give that outer frame allow="autoplay; fullscreen; gamepad" and allowfullscreen, and no sandbox. If that outer frame has the same origin as the Game OS page, the game page adds its message listener to window.top (same-origin access allows it). If not, the Game OS page forwards each E3DS message to the game page wrapped as {source: 'e3ds', data: <the message>}, and the game page accepts that wrapper only from the Game OS page's own origin. Tell me which case applies.
> - Read these settings from the site's config or environment, never hard-coded. Use public variables, for example NEXT_PUBLIC_... in Next.js.
>   - MURDERINC_STREAM_URL: the stream link.
>   - MURDERINC_SESSION_MINUTES: default 15.
>   - MURDERINC_ENABLED: when false, the page says 'MURDER INC. is offline right now' and shows no Play button.
>   - MURDERINC_GAMEPAD: default false. When true, the controls text also shows the Controller line and the phone message mentions controllers (full controller play arrives with the next game build; I will tell you when to switch it on).
>   - MURDERINC_LISTED: when false, the page can be reached only by its address, is left out of the game list and carries <meta name="robots" content="noindex">.
> - Accept the stream URL only if it is https and its host ends with .eagle3dstreaming.com. Otherwise show 'not configured' and log why.
> - Tell me how to change each setting.
>
> 2. Headers
> Check every place the site sets headers: framework config (for example next.config headers() or middleware), vercel.json, netlify.toml or _headers, server or CDN rules, and <meta http-equiv="Content-Security-Policy"> tags.
> - Content-Security-Policy: add frame-src https://*.eagle3dstreaming.com and keep the existing sources. Do not list only connector.eagle3dstreaming.com. Do not write the connector_linux host itself: a CSP host may not contain an underscore, so that entry is ignored and the frame is blocked. The wildcard matches both the connector_linux. and the stream. hosts.
> - Frames fall back to child-src, then to default-src. If the policy has no frame-src yet, the new frame-src must repeat the sources that child-src (or default-src) allows today, plus the wildcard, or be set on this route only. Otherwise other embeds on the site stop working.
> - Permissions-Policy, if the site sends one: on this route, fullscreen, autoplay and gamepad must not be () or (self). Use (self "https://*.eagle3dstreaming.com") or leave them out.
> - No Cross-Origin-Embedder-Policy (require-corp or credentialless) on this route. E3DS's pages send no CORP or COEP headers, so the browser would refuse the frame.
> - No sandbox attribute on the iframe. A sandbox blocks the mouse lock and scripts.
>
> 3. The Play button and the iframe
> - Before Play, the 16:9 stage shows a poster and a Play button. The poster is an image I approve, or the title on black.
> - Never render the iframe on page load, on hover, during route prefetch or on the server. Every iframe load starts a session that reserves a server, and once the video runs it spends my minutes.
> - In the Play click handler, do this synchronously:
>   - Create the iframe.
>   - Set id="iframe_1", title="MURDER INC. game stream", allow="autoplay; fullscreen; gamepad" and allowfullscreen before you set src. The browser reads allow when the frame starts loading.
>   - Set border 0 and width and height 100%.
>   - Set src to MURDERINC_STREAM_URL, append the iframe and call frame.focus().
> - Do not add pointer-lock: it is not a real permission, and the mouse lock works in any frame without a sandbox. Do not add clipboard-read, clipboard-write, camera or microphone either.
> - The Play click and allow="autoplay" let most browsers start the stream with sound. When a browser refuses, E3DS starts the stream muted and shows a speaker button at the bottom right of the picture; the text beside the player says so.
> - In React or similar, create the iframe from state set in that click handler and give it a stable key. Make sure no later state change re-creates it: every re-creation is a new paid session. Double-mounting in development must not create two.
> - The stage: aspect-ratio 16/9, width min(100%, 1920px), centred, black. On Play, scroll it fully into view.
> - While a session runs, the page must not scroll: set overflow: hidden on html and body and restore it at the end. That way the mouse wheel (weapon switch) and Space (jump) never move the page.
> - While a session runs, ask before the page is left: window.addEventListener('beforeunload', e => { e.preventDefault(); e.returnValue = ''; }), removed when the session ends. A slip on Ctrl+W, the back button or a reload otherwise ends the game at once.
>
> 4. Messages from the stream (window 'message' events)
> - Use a message only if new URL(event.origin).hostname matches /(^|\.)eagle3dstreaming\.com$/, or if it is the wrapper of section 1 from the Game OS page's own origin. event.data is usually an object. If it is a string, JSON.parse it inside try/catch. Ignore anything else.
> - What we send to the frame must be a JSON string: frame.contentWindow.postMessage(JSON.stringify({...}), '*').
> - E3DS's Linux player sends only the older event names (checked in its live code). The dotted names in E3DS's documentation and in its demo may never arrive. Handle every name below; each line is one moment. Treat a repeat of the same moment within 3 seconds as one event, except the three moments marked "repeats": each copy carries a new value and must be shown. Each line reads: moment: old Linux names / documented names.
>   - waiting in line (repeats): stage1_inqueued (positionInQueue), QueueNumberUpdated (queuePosition) / session.queued, session.queuePositionChanged (queuePosition)
>   - server found: stage2_deQueued, stage3_slotOccupied / session.hostFound, session.hostReserved, session.machineAssigned, session.machineReserved
>   - copying the game to the server (repeats): stage3_1_AppAcquiringProgress (percent) / build.acquiring, app.downloadProgress (percent)
>   - unpacking (repeats): stage3_2_AppPreparationProgress (percent) / build.preparing, app.prepareProgress (percent)
>   - starting: build.started
>   - ready, may wait for a click: stage4_playBtnShowedUp / stream.ready
>   - playing: stage5_playBtnPressed / stream.playing
>   - the game's data channel is open: bidirectionalChannelBetweenUnrealAndIframeReady / stream.channelOpen
>   - the game stopped: handleStreamerDisconnected / build.stopped, app.stopped
>   - time limit reached: sessionExpired / session.expired
>   - the video failed: videoStreamFailed / stream.failed
>   - error: Error_Redirect / session.error
>   - ended, always last: redirectingWithMessage and sessionEnding (message; the Linux player sends both, the second with legacyType 'redirectingWithMessage') / session.ending (message)
>   - password box: passwordRequested, passwordAccepted
>   - keyboard focus: streamFocusLost, streamFocusGained
>   - if they arrive: notice (show its message as a small note beside the stage), _focus (focus the frame), isIframe (reply JSON.stringify({cmd: 'isIframe', value: true})), connection.stats (keep the last one for ?debug=1).
> - Today's Linux player never sends Error_Redirect, videoStreamFailed, isIframe, _focus or connection.stats. Keep their handlers, but the ending moment and the watchdog of section 5 must cover every failure.
> - Once, when the stream is ready or playing, send JSON.stringify({cmd: 'switchMouseControlSchemeTo', value: 'LockedMouse'}) to the frame. The game needs the locked mouse; it takes hold at the player's next click.
> - Show a status line beside or under the stage, never over it, with aria-live="polite":
>   - 'Waiting for a free game server: you are number N in line'
>   - 'Server found, starting'
>   - 'Copying the game to the server: N %' (Linux servers copy the whole game for every session; 1 to 3 minutes is normal)
>   - 'Unpacking: N %'
>   - 'Ready: click the picture'
>   - nothing while playing.
> - Nothing may cover the iframe while it is on the page. E3DS draws its own password box, queue screen, play button and inactivity countdown inside it, and the player must see and click them. If you want a loading layer over the frame, it needs pointer-events: none. It must go away on the ready, playing, password or error moments, and after 10 seconds in any case.
> - On passwordRequested, focus the frame so that typing goes into E3DS's password box.
> - If the stream becomes ready while the tab is hidden, set document.title to 'Ready: MURDER INC.' until the tab is visible again.
>
> 5. Ending sessions (this is what protects my minutes)
> - A 'Quit game' button beside the stage removes the iframe and shows the end screen. When the frame goes away, E3DS ends the session and frees the server.
> - Remove the iframe, never just hide it, when the visitor leaves the route or the page, or when the Game OS window is closed or minimised. Never keep it mounted with display: none or off-screen: it would keep running, spend minutes and hide the inactivity countdown.
> - If the tab stays hidden for 3 minutes after the stream became ready or started playing, remove the iframe and show 'We stopped the game while you were away, to free the server. Press Play to start again.' Do not stop a session that is still waiting in line, copying or unpacking: E3DS counts minutes from the moment the video starts.
> - On the 'game stopped' moment, remove the iframe at once and show the 'stopped unexpectedly' text. Otherwise E3DS's player reloads itself after 3 seconds and starts another session.
> - On the ending moment, and in all the cases above, remove the iframe and show our own end screen in the stage, with a 'Play again' button. Choose the words from the moments you saw, never from the message text. Write E3DS's message only to console.info, never on the page: it can contain the account name or billing words.
>   - A password was asked and the game never played: 'The game did not start (a wrong or cancelled password ends it). Press Play to try again.'
>   - The game never played, for any other reason: 'MURDER INC. could not start right now (all game servers are busy, or the game is being updated). Please try again in a few minutes.'
>   - After the time-limit moment: 'Your session reached its N-minute limit. Press Play again for a new game.'
>   - After the 'game stopped' moment: 'The game stopped unexpectedly. Press Play again to start a new game.'
>   - After the 'video failed' moment: 'The video could not reach your browser. A school or office network can block it; try another network, then press Play again.'
>   - Otherwise: 'Your session has ended (for example after a few minutes without input, or a dropped connection). Press Play again for a new game.'
> - Never start a new session automatically. Do not copy E3DS's demo, which reloads on sessionExpired and stream.failed. 'Play again' creates a new iframe from its own click.
> - Watchdog: if a server was found but the stream is not playing 6 minutes after Play, and the password box is not showing, remove the iframe and show the 'could not start' text.
> - Allow one running game per browser, using BroadcastChannel or a localStorage lock. A second tab says 'MURDER INC. is already running in another tab.'
> - If the site has analytics, record Play clicks and which ending happened, by moment name only.
>
> 6. Focus, keys, controllers and full screen
> - Focus the frame:
>   - on its load event, with setTimeout(() => frame.focus(), 0)
>   - on mouseenter
>   - when playing starts
>   - on _focus and streamFocusLost
>   - right after any page control is used (full screen, help, quit).
>   Never take focus from an input, select or textarea the visitor is typing in.
> - No page or Game OS shortcut may close, hide or minimise the game on Esc or another single key. In the stream, Esc only gives the mouse back to the browser.
> - Add a 'Full screen' button (E3DS's own full-screen button does not work yet). In its click handler, call requestFullscreen() (or webkitRequestFullscreen()) on the stage element, then focus the frame. Hide the button where full screen is not available (iPhone).
> - Controllers: a browser shows a controller to a page only after one of its buttons is pressed, and only to the frame that has focus. The Play click focuses the frame; the text asks the player to press a controller button once when the game appears.
>
> 7. Text beside the player
> - 'Press Play. Starting takes 1 to 3 minutes. When CLICK TO PLAY shows, click the picture once: that locks the mouse to the game. No sound? Click the speaker button at the bottom right of the picture.'
> - Keyboard and mouse: Move W A S D · Look mouse · Fire left click · Aim right click · Reload R · Swap weapon Q, mouse wheel or 1 to 4 · Weapon wheel hold Q · Grab a reel hold E · Jump Space · Sprint Shift · Crouch C (not Ctrl: Ctrl+W closes the tab) · Melee F · Fire mode B · Inspect T · Pause P. Esc gives the mouse back to the browser; click the game to take it again. In the game's menus: arrow keys and Enter.
> - Only when MURDERINC_GAMEPAD is true: Controller (PlayStation 5 or Xbox, in Chrome or Edge; connect it before Play and press one of its buttons when the game appears): Move and look with the sticks · Fire R2 / RT · Aim L2 / LT · Reload Square / X (hold it at a reel to grab it) · Swap Triangle / Y or the D-pad · Jump Cross / A · Crouch Circle / B or L1 / LB · Sprint: click the left stick · Melee R1 / RB or click the right stick · Pause Options / Start.
> - 'A session lasts up to N minutes', with N from MURDERINC_SESSION_MINUTES.
> - 'After a few minutes without input a countdown appears in the picture: move the mouse, press a key or a controller button to stay.'
> - 'If your connection drops, the game ends: press Play again (a new game starts).'
> - 'If aiming feels too fast or too slow, change Look sensitivity in the game's settings (press P, then Settings; in the game's menus use the arrow keys and Enter).'
> - 'Best in Chrome or Edge on a computer; Safari and Firefox should work. When all game servers are busy you wait in line and see your place.'
> - An age note: 'Mature: strong violence and language. 17+.' I may change the wording.
>
> 8. Phones and tablets
> - Treat a device as touch-only if window.matchMedia('(any-pointer: fine)').matches is false, or if it is an iPad that reports itself as a Mac (navigator.maxTouchPoints > 1 and 'Macintosh' in navigator.userAgent): Safari on iPad has no mouse lock. On a touch-only device show 'MURDER INC. needs a computer with a keyboard and mouse' (when MURDERINC_GAMEPAD is true: 'a computer with a keyboard and mouse, or a controller') in place of the Play button, with a small 'Play anyway' link. An iPhone has no mouse lock and no full screen in a frame.
>
> 9. Test, deploy, report
> - Test with the demo link first and check all of these:
>   - The console shows no 'Refused to frame' or Permissions-Policy errors.
>   - The messages arrive and the status follows them, including every queue and progress update. When the page is opened with ?debug=1, log each message with console.debug.
>   - Quit, leaving the route, a tab hidden for 3 minutes after the picture appears, and a second tab behave as described. A tab hidden while the game is copied does not end the session.
>   - The leave warning shows only while a session runs.
>   - Nothing covers the frame. The page never scrolls during play.
>   - The deployed site sends the right response headers, not only the local one.
> - Then put my link in and make one short test: under 5 minutes, then Quit. Every minute counts against my 300 a month. Mouse lock, sound and controllers need a person: I test them myself in Chrome, Edge, Safari and Firefox.
> - Deploy with MURDERINC_LISTED=false first. When my tests pass, I will ask you to set it to true.
> - Report the files and headers you changed, the live URL, how I switch the game off (MURDERINC_ENABLED=false) and how I change the link.
~~~~

----- replacement ends -----

Evidence for the additions: E3DS's demo (GitHub `e3ds/E3DS-Iframe-Demo`, `js/iframe-events.js`, read 23:43 UTC)
maps `stage2_deQueued` to `session.machineAssigned`, `stage3_1_AppAcquiringProgress` to `app.downloadProgress`,
`bidirectionalChannelBetweenUnrealAndIframeReady` to `stream.channelOpen`, and never merges
`session.queuePositionChanged`, `app.downloadProgress` and `app.prepareProgress` ("swallowing one freezes a progress
bar or a queue position"). E3DS's live Linux player (1.0.146) contains no `connection.stats`, `stream.playing` or
`session.ending`, and on pointer-lock loss it sends a key-up for every held key. Minutes: "Duration: How long the
video ran. These are the minutes the session used" (https://docs.eagle3dstreaming.com/wiki/minutes/). The mouse
mode command and "Locked only takes hold on the viewer's next click":
https://docs.eagle3dstreaming.com/wiki/features-api-mouse-mode/. "Look sensitivity" is the game's label
(`Content/Data/text.json:455`). Controller bindings: `Source/MurderInc/Player/MIPlayerController.cpp:86-119`.

---

## 4. Before going public

### 4.1 Plan and minutes

- **Core:** $29 a month, 300 minutes (unused minutes expire), 10 players at once, $0.10 a minute beyond that. Going
  over is never charged: "When they are used up, streaming stops" (FAQ). Extra minutes are bought "in steps of 50"
  ($5) on the monthly plan and are then "added, and charged, every month until you lower them or cancel"
  (https://docs.eagle3dstreaming.com/wiki/plans-and-billing/).
- **What 300 minutes buys.** A session costs at most the Max Session Time (15 minutes). An idle one ends after about
  4 minutes (3 plus a 1-minute countdown); a hidden tab after 3 minutes (the page's rule). A real player (Gear Up
  plus a Story run of "about five minutes", DESIGN.md:42) uses 8 to 12 minutes. So 300 minutes is roughly 20 to 30
  player sessions a month, and your own tests come out of the same minutes.
- **Decide before announcing:** either a soft launch (page unlisted, password on, invited players only), or a budget:
  for example 500 extra minutes a month is $50 a month, and stays on your bill until you lower it.
- **Watch** Control Panel → Minutes after each day (the Duration and "how it ended" columns). On E3DS's 75 % and 90 %
  emails, switch the page off (`MURDERINC_ENABLED=false`) or set the project's Streaming status to Disabled, so
  visitors see our "offline" text instead of a failing stream.

### 4.2 Capacity

- At most 10 at once on Core. The 11th waits in E3DS's queue ("CCU Limit Reached. Trying Again in 10 sec",
  https://docs.eagle3dstreaming.com/wiki/capacity-and-regions/); the page shows the place in line.
- Linux machines "are not kept warm", every session copies the whole 2.25 GB zip, and "Support can arrange things,
  but not at short notice" (https://docs.eagle3dstreaming.com/wiki/linux-pixel-streaming/). Send question 5 of 1.6
  well before the launch date.
- **Pin the version** once version 3 has proven itself on the live page: Builds → Run a fixed version of this
  build… → that version → Save changes. Test each later upload in a private window with the project link plus
  `?appVersion=<number>` before moving the pin back to Latest (project-settings,
  https://docs.eagle3dstreaming.com/wiki/apps-and-versions/). Delete a version only after the next one has proven
  itself.

### 4.3 Settings for the public project (what changes from section 1.2)

| Setting | Public value |
|---|---|
| Password Protect Stream | Off (only at launch; keep it on until then) |
| Anonymize URL | On, then Copy Link again and give Cursor the new link. It only encodes the names; it is not secret (https://docs.eagle3dstreaming.com/wiki/session-and-access/) |
| Print UE log in browser console | Off (it shows the game's internals to every visitor) |
| Launch options | only what the version 3 release notes say; never `-MIDev`, never `-MICrashTest` |
| Browser Resolution | Dynamic if version 3 ships its size limit (V3-6); otherwise Custom 1920 x 1080, or 1280 x 720 if the tests showed the card needs it, with the `-MIMouseScale` the release notes give. E3DS's own advice for an unknown public audience is "1280 × 720 fixed" (resolution page) |
| Video Quality | what the tests showed: Medium, or High if it stayed smooth on an ordinary home connection |
| Keyboard Focus Notice (UI) | Off (the page returns focus itself) |
| Max Session Time; inactivity | 15; 3 and 1 |
| Email To Send Log Upon App Crash | On |
| Select Region; Fake Mouse With Touch; microphone | Global; Off; Off |
| Draggable Settings Button | On |
| Loading screen (Branding) | your own 1920 x 1080 key art as Queue background and Loading background, and a transparent logo. By default "it carries Eagle 3D Streaming's branding" (https://docs.eagle3dstreaming.com/wiki/loading-screen/) |

### 4.4 Notes for the page (Cursor's prompt covers them)

Starting takes 1 to 3 minutes; a dropped connection ends the game; keyboard and mouse (a controller from version 3);
Chrome or Edge best; no sound means the speaker button; an age note. Read E3DS's terms for a violent shooter (their
legal page did not load for us).

### 4.5 Final check before announcing

- [ ] Version 3 on E3DS: Info frame rate at 55 or more in a fight, round trip under 80 ms from your home.
- [ ] A full Story run and a few Hold the Block waves, with mouse and keyboard and with a PS5 controller.
- [ ] The live page in Chrome, Edge, Safari and Firefox on a computer; a phone gets the "needs a computer" text.
- [ ] Quit, a hidden tab and a second tab behave as the prompt says; nothing covers the frame.
- [ ] The minute plan is decided (4.1), the version is pinned (4.2), the public settings are set (4.3).

---

## 5. Corrections our docs need

Another agent is editing `docs/LAUNCH.md`, `docs/unreal/PROGRESS.md` and `docs/unreal/RESUME.md`; these are for that
agent. Line numbers are those of the current files and may move.

### docs/LAUNCH.md

| Where | It says | It should say | Evidence |
|---|---|---|---|
| Opening (lines 7-10) | "So the free trial is the real test: do steps 1 to 6 on the trial before paying for anything." | The account is on Core. Version 2 has streamed; the open problem is smooth play, not starting. | DECISIONS.md, 2026-11-24 entries |
| What you need (line 21) | "Google Chrome or Microsoft Edge (Safari cannot lock the mouse and keyboard to the game)." | "Chrome or Edge recommended. Safari and Firefox on a computer should work (not yet tested). Phones and tablets cannot play." | MDN: pointer lock in Safari 10.1 and later; WebKit refuses it only without a click or in a sandbox |
| Section 1 (lines 24-29) | the free trial steps | mark as history: the account is on Core | DECISIONS.md "E3DS Core plan" |
| Section 3, step 1 (line 43) | "open **Configurations** (or **Stream settings**) for the app, on the **Development** tab" | "Your Projects → Project_MurderInc → Viewer Experience. Turn Advanced Options on for the UI, Branding, Developer and Microphone tabs." | project-settings page |
| Section 3, step 3 (line 45) | "set **Platform** to **"Linux UE Build for PS"**" | "Developer tab: **Platform: Linux**" | linux-upload-and-stream: "The Platform field offers Streaming App, Windows and Linux" |
| Section 3, step 4 (lines 47-48) | the mouse mode, with no place named | "Search settings: mouse → **Locked**" | E3DS's player reads `MouseControlScheme` (1.2) |
| Section 3, step 5 (line 49) | "Resolution: **1920 x 1080** (or "match the browser window"; see the note in section 7)." | "Common tab, **Browser Resolution: Custom, width 1920, height 1080**, both boxes filled (version 2; 1280 x 720 if it plays more smoothly, PREFLIGHT.md session B). Version 3: as its release notes say (Dynamic once the game limits the size itself)." | resolution page; V3-6 |
| Section 3, step 6 (lines 50-51) | "for example 30 minutes and 5 minutes" | "**Max Session Time (minutes): 15** (E3DS's default, also when empty). **Log Out Automatically After Inactivity** on: Minutes Until Log Out Countdown Starts **3**, Log Out Countdown Timer Length **1** (also minutes)." | session-and-access; E3DS's player multiplies both by 60 |
| Section 4, step 1 (line 57) | "E3DS gives up after 3 minutes" | "Every Linux session copies the whole 2.25 GB zip to a cold machine: expect 1 to 3 minutes. E3DS sets no limit on copying and unpacking. Once the game connects, the picture must appear within 3 minutes, and E3DS's own play button, if shown, waits 3 minutes for a click." | FAQ ("There is no time limit for downloading or preparing an app"); session-end-messages #13 |
| Section 4, step 3 (line 67) | "a gamepad plugged into your computer moves and aims" | "Version 2: a gamepad moves, fires and pauses but cannot turn or aim. Version 3 adds that." | `MIPlayerController.cpp:73` and `:103` at `e989cb8` |
| Section 4, step 4 (line 68) | "Close the tab. The game pauses by itself when the last viewer leaves." | "Close the tab: that ends the session, and E3DS stops the game." | reconnect-after-connection-drop: closing or reloading "the session ends immediately" |
| Section 5 (lines 75-101) | a static iframe set at page load, with `pointer-lock; clipboard-read; clipboard-write`, `max-width:1280px`, and "`fullscreen` lets E3DS's full-screen button work" | A pointer to `docs/CURSOR_HANDOFF.md`: the page creates the iframe in the Play click, with `allow="autoplay; fullscreen; gamepad"` plus `allowfullscreen`; no pointer-lock (not a permission), no clipboard. E3DS's Fullscreen Button "does not take effect yet": the page has its own. | streaming-interface page; W3C permissions-policy feature list |
| Section 6 (lines 103-108) | "If the player's network drops or the tab is closed, the game **pauses itself**." and "reload the page to play again" | "When the connection breaks or the tab closes, E3DS ends the session (only Omniverse apps reconnect). Press Play again for a new game." | reconnect-after-connection-drop: "For other apps the session still ends as soon as the connection breaks" |
| Section 7 (lines 114 and 120-124) | "Sound plays after the first click; a gamepad works"; "Players can also change **Sensitivity**" | "Sound after the first click, or after the speaker button; a gamepad from version 3"; "**Look sensitivity**". Say that the 0.333 rule holds only for Custom 1920 x 1080 shown 1280 wide. | text.json:455 |
| Section 8, step 2 (line 133) | "platform is "Linux UE Build for PS"" | "Linux" | as above |
| Section 10 (lines 242-243) | "E3DS's servers have 8 or 16 GB of graphics memory (RTX 4080 or 5070 class)" | "E3DS's own machines are RTX 4080 or 5070 with 12 to 16 GB; its cloud machines are typically T4 or A10. Which one a Linux session gets is not published; the log's GPU line shows it. E3DS asks apps to use 4 to 6 GB; version 2 uses 3.6 GB on the home screen and 3.8 GB in a Story run (Vulkan count; the card's own counter shows more)." | system-requirements; FAQ |
| Section 10 (line 289) | "Lighting itself (Lumen with hardware ray tracing), Nanite, the art and the resolution are unchanged." | From version 3 the game lowers its resolution, and on slower cards its lighting quality, by itself to keep about 60 frames a second. | V3-1, V3-2 |
| Section 11 (line 297) | "Extra minutes \| $0.10 a minute, bought 100 at a time" | "$0.10 a minute, in steps of 50 ($5) on the monthly plan or 1,000 on the yearly; once added, billed again every month until you lower them; lowering applies from the next month" | plans-and-billing |
| Section 11 (lines 300-302) | "E3DS never bills automatically: when the minutes run out, streaming stops." | "Core renews every month until you cancel it. Going over is never charged: when the minutes run out, running streams end and none start until the billing day or until you add minutes. Extra storage is $1 per GB a month; lower it with Adjust Storage on the subscription." Remove or mark the Trial row. | plans-and-billing |
| Section 12 (line 309) | "the box cannot test an actual stream" | "the box receives the stream with a non-browser WebRTC viewer and can send input (`rtcinput.py`), but cannot run a browser" | PROGRESS.md top entry; `cbb41f4` |
| Section 13, item 1 (line 331) | "Show the Unreal log in the browser console" | "**Print UE log in browser console**" | developer-options |
| Section 13, item 2 (lines 335-336) | "E3DS's "Auto Download UE Crash Log" ... only works with Development builds" | "**Auto-Download UE Crash Log** is "not working at present"; use **Email To Send Log Upon App Crash**." Keep the `-MIDev` paragraph. | developer-options |

### Other files

- `docs/CURSOR_HANDOFF.md`, lines 11-12 (outside the prompt): add "If the owner has pinned a fixed version, the owner
  moves the pin after testing a new version; the website still does not change." Lines 5-7 send the owner to
  LAUNCH.md sections 2 to 4, which still carry the wrong names above.
- `docs/unreal/DECISIONS.md`, line 82: "RTX 4080 or RTX 5070 class, 8 or 16 GB of graphics memory" → "12 to 16 GB"
  (system-requirements). Add it as a correction note under the entry rather than rewriting the record.
- `docs/unreal/PROGRESS.md`, lines 29-30: "the next package makes it the launcher's default if E3DS shows the same" →
  version 3 switches decoupling by the game's own frame rate (V3-3). Lines 77-81: version 2 has streamed
  (DECISIONS.md 23:10).
- `docs/unreal/RESUME.md`, section 9 "Next:": version 2 streamed; next are the measurement sessions (section 1) and
  version 3.
- `unreal/MurderInc/Config/DefaultGame.ini`, comments at lines 17-19 and 28 (version 3, V3-13).

---

## 6. What we cannot know until the E3DS test, and how the test will tell us

| Unknown | How the test tells us | What we do with the answer |
|---|---|---|
| The GPU, driver and memory of E3DS's Linux machine | the log's `[MICloud] GPU:` line and the launcher's `nvidia-smi` lines (browser console, crash email, or support); support's answer (1.6) | sets how far V3-2 must step down; on a T4, ask support for RTX machines |
| The game's frame rate and GPU time there | `MICloudProbe` lines; session C's `stat unit` | V3-1 and V3-2 thresholds |
| The stream's frame rate, round trip, bitrate and region | Info screenshots | V3-3, V3-4; region choice |
| Whether a smaller picture or a 30 cap gives enough head-room on that machine | sessions B and C against A (feel, Info, probe lines) | the setting to keep until version 3; V3-1's starting point |
| Whether E3DS's console-commands field reaches a Pixel Streaming 2 Linux app | session C's probe lines say `fps=30.0` | whether V3-9's allowlist fix is the owner's tuning path, or only V3-11's launch option |
| Whether decoupling helps there | the first test (decoupled) against session A | V3-3 (decoupling off by default) |
| Whether the delay is the network or the game | Info round trip against the felt delay | V3-4 or region |
| Whether E3DS's browser log carries the game's lines for Linux | the console shows `[MICloud]` lines, or nothing | if nothing: rely on V3-5 and on support |
| Which file E3DS's crash email attaches for Linux | session D | how we triage crashes after launch |
| The arguments E3DS really passes (the Video Quality numbers, `-ResX`/`-ResY`, the `-ABSLOG=` path) | the log's `Command line:` line | Video Quality choice; V3-6's start size |
| Whether a 10-second connection drop ends the session (E3DS's pages disagree: "more than 30 seconds" against "as soon as the connection breaks") | session A's Wi-Fi test | the page text (it already says the game ends) |
| Whether the mouse mode comes out Locked | the cursor is hidden in play and the view keeps turning | the configuration |
| Whether sound starts with the click or needs the speaker | the session | card and page text |
| The start-up wait for our 2.25 GB zip | the owner times it | page text; whether a smaller zip is worth it later |
| Whether E3DS's in-session Quality menu changes the picture for a Pixel Streaming 2 app | gear → Quality → High while watching Info's bitrate | the Video Quality advice |
| Linux capacity at once, warm machines | support's answer (1.6, question 5) | the launch plan (4.2) |
| **After version 3:** whether dynamic resolution, the quality steps, the size limit and decoupling behave on E3DS's card | the pause card's line (V3-5) and Info, in a fight | final thresholds, set by launch option (V3-11) without a rebuild |

---

## 7. Checked and fine

- E3DS's arguments map to Pixel Streaming 2 in 5.9: `-PixelStreamingURL=`, `-PixelStreamingID=`, codec, bitrate, MinQP/MaxQP (`PixelStreaming2PluginSettings.cpp:93-104, 170-193, 244, 1393-1414`; box run x3-dev).
- `-AllowPixelStreamingCommands` still works in 5.9 (`:246`); version 3's allowlist limits it.
- `-Unattended` and no display still write the engine's crash report (`UnixPlatformCrashContext.cpp:763-813`; runs v-crash, w-crash).
- `-log` adds no duplicate lines next to `-stdout` (`LinuxConsoleOutputDevice.cpp:63`).
- `-Windowed -ForceRes -ResX -ResY` with `-RenderOffScreen` run (box runs v-e3ds-7600, x1-ship).
- The zip: `MurderInc.sh` (mode 755) at the top, 64 files, no `Saved/` or symbols; the box's copy is sha256 `ceaf828d…`, as in LAUNCH.md section 9.
- The launcher writes E3DS's `-ABSLOG=` file, `Saved/Logs` and its own output (`f827e1b`; runs x1 to x4).
- Exit codes: the game's own code for a crash, 0 for a stop the host asked for; E3DS follows the process it starts and its children (FAQ).
- Started as root, the game runs as the folder's owner or `nobody` (runs v-root, x4-root).
- The game has no Quit item, so quitting cannot look like a crash.
- Memory: 3.6 GB (home) and 3.8 GB (Story) of Vulkan memory against E3DS's 4 to 6 GB guidance.
- The game is up about 8 seconds after it starts; E3DS's 3-minute rule counts from the stream connecting.
- A new version keeps the project link; projects run Latest unless pinned (project-settings).
- Sound leaves the game: Opus received on the box (PROGRESS.md top entry).
- Gamepad buttons and sticks reach Unreal (`RTCInputHandler.cpp:145-159`); E3DS's player counts gamepad messages as activity for its idle timer (player 1.0.146).
- P pauses in a stream (`MIPlayerController.cpp:119`); E3DS's player sends a key-up for every held key when the pointer lock ends, so no key sticks.
- Mouse smoothing is off (`Config/DefaultInput.ini:4`).
- Minutes count from the moment the video starts (minutes page).
- E3DS's pages allow any site to embed the player (no X-Frame-Options or frame-ancestors, fetched from the box).
- `https://*.eagle3dstreaming.com` matches both Linux hosts in Chrome, Firefox and Safari's CSP parsers.
- Pointer lock in a frame needs no allow token; a sandbox is the only thing that blocks it.
- Max Session Time defaults to 15 minutes (session-and-access).
- H.264 is encoded by every card E3DS runs (codec page); AV1 is not needed.
- Version 2 streams on E3DS: the start-up crash fix works (DECISIONS.md, 23:10 UTC).
- Pixel Streaming 2 in 5.9 can switch decoupling while the game runs (`VideoSourceGroup.cpp:206-219`), which V3-3 relies on.
- **Fixed since the reviews:** CURSOR_HANDOFF.md was rewritten for the owner-uploads flow (`ce1e944`); LAUNCH.md section 9 joins into `MurderInc.zip` and uses E3DS's upload names (`474ce9e`); the launcher writes the `-ABSLOG` file (`036ee74`, `f827e1b`).

---

## Appendix A. Where the reviews disagreed, and the decision

| Question | Decision | Why |
|---|---|---|
| Browser Resolution: Custom 1920 x 1080 or Dynamic | Custom for the version 2 sessions (1920 x 1080, and 1280 x 720 as the head-room test); Dynamic for launch once version 3 limits the size itself (V3-6); otherwise Custom | Only Dynamic makes the mouse speed exact at every frame size and in full screen. The game's own limit removes the 1440p and 4K load. A smaller frame costs less GPU, which is what the stall needs. |
| Max Session Time: 15 or 30 | 15 | A Story run is about five minutes (DESIGN.md:42). On 300 minutes a month, 15 halves the worst case of an abandoned session. It is also E3DS's default. |
| Inactivity: 3 and 30 seconds, 5 and 60, or 10 and 60 | 3 and **1** | E3DS's player multiplies both fields by 60, so "30" would be 30 minutes. Gamepad input resets the timer (player code), so active pad players are safe. |
| `-PixelStreamingDecoupleFramerate`: launcher default or launch option | neither: off by default; version 3 turns it on only while the game holds 60, and only if the loaded-GPU measurement shows a gain (V3-3) | Under load it neither causes nor cures the stall (box, 23:39 UTC); E3DS measured that it hurts an app drawing under 60. |
| The root cause of "sticky": GPU, capture or network | GPU head-room first (V3-1, V3-2), capture settings second (V3-3), delay work third (V3-4) | The stall was reproduced only with a full GPU and disappeared with head-room. The round trip from E3DS's Info panel will say whether the network adds to it. |
| Version 3's console allowlist: PixelStreaming commands only, or also tuning cvars | also the tuning prefixes (V3-9) | Otherwise version 3 silently refuses E3DS's own tuning field, the one E3DS documents for `t.MaxFPS 30`. |
| Video Quality: High now, or Medium | Medium until play is smooth; then try High | The owner reports lag; E3DS says a higher level can cost smoothness. |
| Viewers' console commands: force off, or allowlist | allowlist (`A6`, done) | E3DS's own quality changes arrive as console commands. |
| `-MICrashTest` and `-MICloudLog`: keep in Shipping behind a variable, or remove | removed from Shipping (as committed), and the box tests changed (V3-10) | No visitor can trigger a crash email; the tests use `-MIDev` and an outside SIGSEGV. |
| "Do not lower Lumen, Nanite or shadow quality" (plan B3) | overruled | The owner's decision of 23:10 UTC: fluid play first. |
| Texture pool to 1000 MB | kept, lowest priority | Memory, not GPU time; E3DS's cards have 12 GB or more. |
| Pad look severity (high or medium) | must-fix | The owner asked for a working PS5 controller path. |
| The mouse mode: a Control Panel field or only a page command | a configuration field (the player reads `MouseControlScheme`), and the page also sends the command once | Belt and braces; the command is harmless when the field is right. |

## Appendix B. Refuted or no longer true (left out above)

- **e3ds-abslog** (crash email reads the `-ABSLOG` file the launcher never writes): the uploaded zip `ceaf828d…` has launcher `f827e1b`, which writes that file; `82ed886a…` was never uploaded.
- **upload-build-name** (the joined file name breaks the build name): LAUNCH.md section 9 already joins into `MurderInc.zip` and uses "Upload a new version of MurderInc".
- **v1-no-display-cause** (the docs omit the `-RenderOffScreen` cause): PROGRESS.md and LAUNCH.md section 9 already name it.
- **cursor-handoff-stale** and **cursor-handoff-v1** (the handoff still describes version 1): rewritten in `ce1e944`.
- **web-cursor-prompt** (replace the prompt): its text is already in CURSOR_HANDOFF.md; only the edits of section 3 remain.
- Parts of confirmed findings that did not hold: enemies do not load at spawn (pre-spawned at boot); "software Lumen costs the same" compared a 1280 x 720 run with 1080p runs; the 16 to 35 s transfer estimate used customer upload speeds; E3DS's Share button has no switch of its own; Graphics quality does not resize the picture at a Custom size; storage can be lowered (Adjust Storage); `-PixelStreamingCaptureUseFence` is already on in Pixel Streaming 2; a full pad deflection for one second turns about 263 degrees, not 166; at the player limit the page shows "CCU Limit Reached", not an account message.
