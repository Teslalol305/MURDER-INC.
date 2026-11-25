# Deployment readiness (release v6)

One section per lane of the readiness pass. Every finding names the evidence it rests on (a picture, a log line, a number).

## Menu audit (box lane, 2026-11-25, 19:50 to 21:00 UTC)

**What was looked at.** The newest package on the box: the trial zip `/project/ue/cloud/v6trial.zip` (commit `fd8ce12`, no newer
package in `/project/ue/cloud/v6`), unpacked privately to `/project/ue/ready/menu/zip`. The front end's C++ (`Source/MurderInc/UI`)
and `Content/Data/frontend*.json` have not changed between `fd8ce12` and the branch head, so every menu finding below is
also true of the head unless it says otherwise. Pictures were taken two ways:

- **MIShot** (the Development game, driven by a demo-director script of `MIMenu fe ...` and real key events through Slate,
  `MIKey`): the screens read back losslessly. Runs `rm-full-1080` (1920 x 1080, 145 pictures), `rm-full-2160` (3840 x 2160,
  145), `rm-pad-1080` (the simulated pad: `MIKey Gamepad_*`, 57), `rm-nine-1080` (the known NINE + suppressor state, 27).
  Every Home row, Crew, every rack card and slot, the five rack filters, the Workbench of all six guns with nothing fitted and
  with every option of every slot fitted (and everything fitted at once on the SHORTY and STICK), Block & Style rows,
  Briefing rows, the intro, the HUD with each gun drawn, fired, reloaded and aimed, the pause card and every Settings row.
- **The stream** (the Shipping game through Pixel Streaming 2, the Python viewer `rtcinput.py` with a new `burst` verb that
  keeps N consecutive decoded frames): run `rm-st-1080`, mouse, keyboard and pad as a browser sends them, 31 single frames and
  21 bursts (750 frames). The pictures a player actually receives.

Scripts and runs: `/project/ue/ready/menu` on the box (`gen.py` makes the demo scripts, `go.sh`, `goship.sh`, `stream.txt`,
`runs/`, `shots/`). The release's own picture set below is `docs/unreal/shots/ready-menu-*.jpg`.

### Findings, most severe first

| # | Severity | Finding | Evidence | Fix (proposed, not made) |
|---|---|---|---|---|
| M1 | **blocker** | **The set-up screens flicker in the stream.** Every rebuild of the front end is painted once with all its controls piled at the top of the column (zero-size layout: kicker, title, tabs, stat lines, BACK/ESC and DONE/ENTER drawn over each other). One such frame on every screen change; and while the mouse rests on a Workbench option the screen alternates garbled / clean / clean continuously (about 20 garbled frames a second) until the mouse moves. This is the "NINE + suppressor" frame of the trial, and it is not a NINE fault: the trial's SHORTY bench frame is the same. | Run `rm-st-1080`, consecutive stream frames: mouse resting on "Pistol suppressor" 29 of 90 frames garbled, after clicking it 20 of 60; screen changes Crew, Loadout, Workbench, back to Loadout, Block & Style, Briefing: exactly 1 garbled frame each; the bursts after keyboard moves inside a screen (rack Right and Down, Workbench tab, Down, Enter) showed none, but a stream frame taken at random during set-up changes inside the Loadout did (run `rm-full-1080`, `v007`, no mouse near the column). Trial `t-guns/g-bench-nine-fit.jpg` and `g-bench-shorty.jpg`. MIShot never shows it (it lays the widget out again before reading it back), which is why the editor and MIShot pictures were always clean. The same one-frame flash at 2560 x 1440 (`rm-st-1440`: 1 garbled frame in each of the Crew, Loadout and Workbench openings). Pictures `ready-menu-bench-hover-flicker.jpg`, `ready-menu-rack-garbled-stream.jpg`, `ready-menu-bench-garbled-stream.jpg`. | Cause in code: `SMIFrontEnd::Tick` calls `Rebuild()` (`UI/SMIFrontEnd.cpp` 226-257), which swaps `ChildSlot` during Slate's paint pass, after the frame's prepass, so the new widgets are arranged with no desired size for one frame. The Workbench option's `OnHovered` runs `Act("preview")` and `OnUnhovered` runs `StopPreview` + `Changed()` (lines 824-825): each rebuild replaces the hovered button, the new one is hovered again, so it rebuilds again. Fix: prepass the new body at once (`Body->SlatePrepass(AllottedGeometry.Scale)` right after `ChildSlot[Body]`), or rebuild from `UMIFrontEnd::Changed()` on the game thread instead of in `Tick`; and make preview idempotent (no `Changed()` when the same part is already previewed; `OnUnhovered` stops only its own preview). Prove with the stream burst (`/project/ue/ready/menu/stream.txt`): 0 garbled frames in every burst. |
| M2 | **blocker** | **At 3840 x 2160 the stream stops.** The game draws at 60 a second, but the viewer gets a few dozen frames at the start and then nothing (sound keeps coming); the game's own line says `stream 0 a second (lowest 0)`. | Run `rm-st-2160` (the Shipping game, **CLEAN**: no other game on the GPU in any of its samples): the viewer received 24 frames, then none; 146 of 148 probe lines `encFps=0 txFps=0` with `outW=3840`, `fps=60`. Run `rm-full-2160` (Development, shared the GPU for 178 of 412 s): 143 frames then none for seven minutes, `LogPixelCapture: WaitForGPU: Timed out waiting for fence`, `LogAVCodecs: Failed to lock output bitstream [NVENC 8]`, then 21,010 `CUDA 700` errors from 20:17:12; the pause card line in picture `ready-menu-hud-4k.jpg`. The same package at 1920 x 1080 streams 60 a second, QP 18, 5.5 Mbit/s (`rm-st-1080` pause line). BOX.md row 36 saw 46 encoded frames a second at 4K on an earlier build: this is new. At 2560 x 1440 (`rm-st-1440`, the Shipping game, another lane's game on the GPU) the encoder made 58 to 61 frames a second (`encFps` in the probe lines); its viewer's connection ended after 45 s (`track ended video MediaStreamError`) while the game went on encoding for a viewer, which looks like the Python viewer, not the game. The game's own start line says a viewer's size request is drawn within 1920 x 1080 (`[MICloud] Viewer input: a size request is taken from 640 x 360 up and drawn within 1920 x 1080`), so on E3DS a 4K browser gets 1080 scaled up; only a 4K launch size reaches this fault. | Until a 4K run alone on the GPU streams, cap the output at 2560 x 1440 (PREFLIGHT V3-6 already says test at 1080 until the game limits its own size) and say so to E3DS's resolution setting. The stream lane owns the cause. |
| M3 | must-fix | **Crew screen looks broken.** The stage shows a large brown sphere (a fist seen end-on) and the CHOPPER cut at the eye; the crew card's portrait is the word RULE in a grey box. It is the first screen a first-time visitor sees after Hit the block. | `rm-full-1080/011-crew`, `rm-full-2160/011-crew`, stream `rm-st-1080/s-crew.jpg`; picture `ready-menu-crew.jpg`. | Frame the Crew stage on the gun alone (as the Briefing does) until the arms read well there, and give the card a real portrait or no portrait box. The hands data in the branch (`8d0d6ac`, `7c0bc1a`) removes the ball in play; whether it does on this stage is not seen (not yet packaged). |
| M4 | must-fix | **Carried guns show "..." on their rack card** instead of "Carried · slot n", at every size ("C..." at 4K). Looks like placeholder text. | `rm-full-1080/014-rack`, `021`; `rm-full-2160/014-rack`; stream `s-rack-row2.jpg`; picture `ready-menu-rack.jpg`. | `SMIFrontEnd.cpp` 624/648: the tag shares a 176-unit row with the "E Attachments" button and is ellipsized to nothing. Put the tag on its own line (or a short "SLOT n" chip). |
| M5 | must-fix | **Focused controls scroll out of sight, worst at 16:10.** The rack shows the second row of cards cut at "Kill speed"; keyboard or pad focus on STICK, STRETCH or RATTLER leaves the focused card half hidden. On Block & Style the focused Difficulty row is cut by the bottom bar (its note is a half line at 4K). At 1280 x 800 the Difficulty chips are entirely below the fold while the row has the focus, the rack's second row shows only the names, and the stat labels are cut ("Kill spe..."). | `rm-st-1080/s-rack-row2.jpg` (stream, focus on STRETCH), `rm-pad-1080/014-pad-rack-d`, `rm-full-1080/106-where-row3`, `rm-full-2160/106-where-row3`, `rm-full-800/014-rack`, `106-where-row3`; pictures `ready-menu-where.jpg`, `ready-menu-1280x800.jpg`. | Scroll the focused widget into view (`SScrollBox::ScrollDescendantIntoView`) on every focus move, or fit the page (shorter Where title, less padding). |
| M6 | should-fix | **Home: SETTINGS and CONTROLS cannot be reached by keyboard or pad** (focus walks 8 rows and wraps). A pad player cannot open Settings (Graphics quality) before a run. | `rm-full-1080/002`-`010`, `rm-pad-1080/002`-`009`; `UMIFrontEnd::NumFocusable` returns 8 for Home (`UI/MIFrontEnd.cpp` 202); picture `ready-menu-home-keys.jpg`. Mouse works (stream `s-settings-mouse.jpg`). | Add the two buttons to Home's focus order. |
| M7 | should-fix | **Pad trapped in the Loadout slots pane.** After RB (rack to slots), LB/RB reorder slots instead of switching back and the D-pad cannot leave the pane; Y on an empty slot does nothing ("MIKey Gamepad_FaceButton_Top: not handled"). Only B (leaves the screen) or Next get out. | `rm-pad-1080/016`-`021` and its log; `UMIFrontEnd::Key` handles LB/RB in pane 1 as swaps before the pane switch (`UI/MIFrontEnd.cpp` ~640-660). LOADOUT.md 2.5 gives LB/RB to both. | Pane switch on a free button (or D-pad up from slot 1 returns to the rack). |
| M8 | should-fix | **The pause card shows a diagnostics line** in the Shipping stream: the server's GPU name, frame rate, GPU ms, drawn and sent size, stream rate, QP, round trip and the build hash. An executive will read it as debug text. | `rm-st-1080/s-pause.jpg` (Shipping), `rm-full-1080/125-pause`; drawn by `MICloud.cpp` (~547, `GetNumbersLine`). | Show it only with a launch option (or `-MIDev`), keep the "P to resume" line. |
| M9 | should-fix | **HUD objective label does not scale at 4K**: "TAKE BACK THE THREE MASTER REELS" is about half the size it is at 1080 while "0 / 3" and the weapon strip scale. | `rm-full-1080/117-hud-play` vs `rm-full-2160/117-hud-play`; picture `ready-menu-hud-4k.jpg`. | Scale that text with the HUD scale like its neighbours. |
| M10 | should-fix | Block & Style title wraps to a lone "STYLE" (two lines at 1080 and 4K); "Best 0" on Hold the Block for a first-time player. | `rm-full-1080/103-where`, `rm-full-2160/103-where`. | Shorter title text or smaller display size on that page; hide Best when 0. |
| M11 | nit | The NEW rack filter with nothing new is an empty grid (no message); a Workbench opened on a gun that is not carried shows the carried strip with no gun highlighted (STICK, STRETCH); "Kill speed" touches its bar and "DIFFICULTY" touches its first chip on Home; the controls glance lists Q twice (Swap, Last gun); the Settings row "Controller" is English text in code (`MIMenus.cpp` 90); "Weapon position: Close" sits above the CLOSE button. | `rm-full-1080/030-rack-filter-4`, `063`/`082` benches, `bench-left` crop of `rm-nine-1080/011`, `108-briefing`, `129-settings`. | Small text and layout touches. |

**Checked and clean** (MIShot at 1080 and 4K, and in the stream at 1080): the Workbench of all six guns with every option of
every slot fitted and with everything fitted at once (no overflow, every part named, FITTED marks right, effect lines and the
stat ghost bars inside the column); the rack with four carried guns and the five filters; the four slots; Briefing (four
Change rows and Hit the block); the HUD with each of the four guns drawn (names, rounds, AUTO/SEMI tags, slot numbers, melee,
BAG) and after a burst and a reload; the pause card and all nine Settings rows by keyboard and pad; the glyphs follow the device
(keyboard: ESC / ENTER / E; pad: B / START / Y / RB, and the pause hint becomes "D-pad or stick choose · A select"); mouse on
Home (Gear up, Controls, Settings), the rack (Attachments button), the Workbench (click fits) and Next; the CLICK TO PLAY
card; Esc from Settings returns to Home. The 4K layout of the set-up screens is the 1080 layout scaled (no text too small,
nothing off screen) apart from M4, M5 and M9.

**Other sizes.** 2560 x 1440 (`rm-full-1440`, 145 pictures, 14 looked at enlarged): the 1080 layout scaled, the same findings
(M3, M4 "C...", M5, M10), nothing new. 1280 x 800 (`rm-full-800`, 141 pictures, 54 looked at): everything fits except M5, which
is worse there (above); Home, Crew, the Workbench, Briefing, HUD, pause and Settings are clean.

**Not reached:** the death card and the debrief (a Development script mistake kept the run paused; in the Shipping stream the
player stood in the street 80 s and was not attacked), the Hold the Block results. The 1280 x 800 stream run was not made (the box was needed by other lanes).

**Seen on the way, other lanes' items** (evidence only, not menu): in the trial package the support hand is still a brown
sphere in play and the aimed red dot a thick black ring (`rm-full-1080/117`, `124`): fixed in the branch's hands data and
`7e120ac`/`a88dcdc`, not yet packaged. The Development game prints "TEXTURE STREAMING POOL OVER 49.578 MiB BUDGET" (1080) and
"OVER 302 MiB" (4K) in red at the top left (`117-hud-play`); the Shipping game does not show the message, but the pool is over
budget. `LogMaterial: M_Weapon_CasingPistol missing usage flag Nanite! Default Material will be used` and the red dot's lens and
reticle materials invalid on a Nanite mesh (SM6 path; E3DS runs SM5).

## Render and stream audit (box lane, 2026-11-25, 19:50 to 21:30 UTC)

**What was looked at.** The newest package on the box, the trial zip `/project/ue/cloud/v6trial.zip` (commit `fd8ce12`; nothing newer
in `/project/ue/cloud/v6`), unpacked privately to `/project/ue/ready/render/pkg`. Everything ran in E3DS's shader platform (`-sm5`:
no Nanite, Lumen in software), one game at a time on the GPU (the runs' watchers say CLEAN unless a line says otherwise).

- **Game frames** (lossless): the Development game with the demo director's `capture` (every frame of the game viewport,
  HUD included, as raw BGRA), `-benchmark -fps=60` so that one engine frame is one picture, `-MICloudNoCard`, standing in the
  Story run's first street (the El, the fire escapes, the fence cage, the pizza sign), 40 consecutive frames at render scale
  50 %, 75 % and 100 % and during a slow turn. Run `r-dev2`.
- **Viewer frames** (what a player receives): the Shipping game streamed through Pixel Streaming 2 to the Python viewer
  (`rtcinput.py` with a `grab` verb: the decoded luma of N consecutive frames, and every frame's arrival time and key-frame
  flag), menus, the Workbench, a still view, a slow turn, the aimed CHOPPER, then the release check's fast turns and flicks.
  E3DS's encoder setting (Medium: QP 34 for minimum and maximum, `qp=34:34`), the game on 6 CPUs (`cpus=0-5`), at 1920 x 1080,
  2560 x 1440 and 3840 x 2160 (launcher `-ResX/-ResY`, which is what E3DS's Browser Resolution Custom passes), under two loads
  (below). Runs `s-1080`, `s-1440`, `s-2160`, `s-1080-l20`, `s-1440-l20`.
- **The flicker number** (`flicker.py`, 8-bit luma of consecutive frames of one view): `mad` the mean change per frame;
  `rev` the up-and-down part of it (sqrt of -d1*d2 for two consecutive changes of a pixel: steady motion gives little,
  shimmer and blinking give a lot); `rev8` the share of pixels that go up AND down by more than 8 levels in two frames (a
  visible blink); `tstd99` the 99th percentile of each pixel's temporal standard deviation; `mean` the picture's mean luma
  (exposure pumping, black frames).

**The load convention, and its limit.** `load=1:0.05:0.05:1024` is the release gate's "E3DS machine" line (`v6-e3ds-l12`):
under it the game at 1080p held render scale 0.75 with 8.1 ms of GPU time (run `s-1080`). E3DS's own A4000 needed 10.2 to
13.3 ms at render scale 0.50 to 0.63 for the same street (DECISIONS.md, version 4 on E3DS), so that load is **lighter** than
the real card. `load=1:0.05:0:1024` (the gate's `l20`) matches it: under it the game at 1080p ran at render scale 0.50 with
13.2 ms of GPU time (run `s-1080-l20`), which is E3DS's own reading. **`l20` is the E3DS-faithful load for this package.** A load process slows every frame by the same
time whatever its size, while a slower card slows the size-dependent part too, so both loads understate what a larger
picture costs on the A4000: read the 1440p and 4K rows as best cases.

### The answer: the highest resolution to stream at

**1920 x 1080, for the meeting and for release v6.** It is the only size proven on E3DS's own machine (version 4: 60 frames a
second, render scale 0.50 to 0.75, QP 34) and it streamed cleanly here. **2560 x 1440 does not hold 60 at the viewer under the E3DS-faithful load (fast turns at 51 to 54 a second, the GPU at
its floor of render scale 0.50 with 13.9 ms average and 16.6 ms peaks, the encoder down to 25 a second in its worst second);
3840 x 2160 does not stream at all (R1).**

| Output | Game (play, E3DS-like load) | Sender | Viewer (decoded frames) | Verdict |
|---|---|---|---|---|
| 1920 x 1080 (`s-1080`) | 59.7 fps (lowest second 36.9: one 340 ms game-thread frame, R5), GPU 8.1 ms, render scale 0.75 the whole run (0 changes) | QP 34 always, 4.5 Mbit/s average, 11.5 peak; encoded 58.4 a second (lowest second 42) | 58 to 61 frames a second in every phase, one key frame in the session (at the start); still view: `rev8` 0.029 %, `tstd99` 6.7, exposure steady (mean luma std 0.05) | **ship** |
| 1920 x 1080, E3DS-faithful load (`s-1080-l20`) | 59.3 fps (lowest second 31.8), worst frame 175 ms (in a fast turn; 132 ms standing), GPU 13.2 ms, render scale 0.50 the whole run (0 changes) | QP 34, 4.1 Mbit/s average, 13.5 peak; encoded 59.1 a second (lowest second 45) | 56.7 to 60 a second per phase, gaps up to 192 to 199 ms in the aim and fast-turn phases; still view `rev8` 0.005 %, exposure steady | **ship** (the hitches are R5) |
| 2560 x 1440 (`s-1440`) | 60.0 fps (lowest 55.3), worst frame 50 ms, GPU 8.3 ms, render scale 0.75 (0 changes) | QP 34, 6.4 Mbit/s average, **21.8 peak** (over the 20 Mbit/s cap), encoded 58.4 a second but **lowest second 24** | still views cleaner than 1080 (`rev8` 0.0085 %), but **fast turns and flicks arrive at 53 a second with gaps up to 120 ms** (1080: 60, 46 to 53 ms); picture `ready-render-stream-1440-still.jpg` (a received 1440p frame: the support-hand ball of R6 is this package's) | box yes; E3DS **not proven** |
| 2560 x 1440, E3DS-faithful load (`s-1440-l20`) | 59.3 fps (lowest second 42.2), worst frame 157 ms (in turns), **GPU 13.9 ms, max 16.6** at render scale 0.50 (the floor: nothing left to give before 16.7 ms on the box; the A4000 pays more per pixel than this load models) | QP 34, 6.3 Mbit/s average, 18.6 peak; encoded 57.1 a second, **lowest second 25**, encode 9.2 ms average (20.9 at worst; 1080p: 6.3) | fast turns, flicks and the walk-turn arrive at **51 to 54 a second, a gap of 249 ms**; still views clean | **no** for E3DS's A4000 |
| 3840 x 2160 (`s-2160`) | 60 fps drawn | **capture and encoder stop after 2 s** (`capFps` 57, then 0, then none; `encFps=0` in 208 of 212 lines) | 63 frames, then nothing for the rest of the run (sound kept coming) | **blocker** (R1) |

**What to set to stream at 1920 x 1080 (nothing to rebuild):**

- **E3DS, Viewer Experience, Common: Browser Resolution Custom, 1920 and 1080** (both boxes filled). Dynamic is also safe for
  size (the game draws a viewer's request at most 1920 x 1080, `FMICloudSize` in `Cloud/MICloud.h`) but keeps the
  set-up screens' small sizes untested (LAUNCH.md 7). **Never Custom 2560 x 1440 or larger for the meeting**: E3DS passes the
  custom size as `-ResX/-ResY` at start, and the game's size limit applies only to a viewer's later requests, not to the
  start size (R1).
- **Video Quality Medium** (QP 34, as version 4 ran): measured here, it holds the bitrate at 4.5 Mbit/s on average and 11.5 at
  peak at 1080p, sends one key frame per session (`PixelStreaming2.Encoder.KeyframeInterval` is -1: no periodic key frames,
  so no key-frame pulsing) and the QP never moves, so no quality swings.
- **Launch options**: none needed. Optional, R4: `-MICVars=r.Streaming.PoolSize=1000`.
- The game: nothing. Dynamic resolution stays 0.50 to 0.75 (`[MICloud]` of `DefaultGame.ini`); under the gate's E3DS load it
  sat at 0.75 without a single change in two runs (no resolution oscillation to flicker); the quality ladder is not in this
  package (the probe line has no `q=`) and is off by default in release v6 (`-MILadder` turns it on).

**To try 2560 x 1440 later** (only after R1 is fixed or the start size is clamped): one E3DS session at Custom 2560 x 1440
with `-MICloudProbe=1`, the pause card's numbers line read in a fight: it must say 60 frames a second, lowest 58, and
"stream 60 a second". On the box's card it held 60 under the light load, but the sender's lowest second was 24 frames and
the fast-turn viewer phases came at 53 a second with gaps up to 120 ms; peaks of 21.8 Mbit/s at QP 34 are over E3DS's 20
Mbit/s maximum, so a home connection will queue them.

### Findings, most severe first

| # | Severity | Finding | Evidence | Fix (proposed, not made) |
|---|---|---|---|---|
| R1 | **blocker** (for any size above 1440p) | **At 3840 x 2160 the stream dies two seconds after the viewer joins**: the game draws 60 a second, Pixel Streaming captures and encodes 57 frames in the first second, 6 in the next, then nothing (`capFps=0`, then no capture statistics at all; `encFps=0` in 208 of 212 probe lines). The viewer got 63 frames in 100 s; the sound went on. The same as the menu lane's M2, here in the Shipping game with E3DS's arguments and QP, no other game on the GPU while it streamed (the run is marked POLLUTED for one sample after the stream had died; another lane's editor used CPUs in 30 of 144 samples). | Run `s-2160` (`/project/ue/ready/render/lag/s-2160`, probe lines in `/project/ue/cloud/repro/lag-s-2160/game.log`, `view.log`: "frames 63" from 50 s to the end). BOX.md row 36 (an older build): 46 frames a second at 4K, then no shutdown. | Do not offer 4K. Clamp the **start** size the way a viewer's request is clamped: run `FMICloudSize::Fit` on the viewport size at start in cloud mode (`r.SetRes` to the fitted size), so a Custom 3840 x 2160 becomes 1920 x 1080 with the mouse scale worked out as for Dynamic. The capture or encoder failure at 4K itself is the engine's (Development log of M2: `Failed to lock output bitstream [NVENC 8]`, CUDA 700). |
| R2 | **blocker** (menu; the same fault as M1, measured independently) | **The Workbench strobes at 20 Hz while the mouse rests on an option**: every third received frame is the garbled layout (title, tabs, effect lines, BACK and DONE piled at the top left, no veil), the other two clean, for as long as the pointer stays; and the hover sound fires 20 times a second with it. | Viewer grabs `G-bench-nine-fit` of `s-1080` and `s-1440`: frames 1, 4, 7, 10 ... differ from frames 0, 2, 3, 5 ... by a mean of 9.9 luma levels and those are equal to each other to 0.0 (pattern A B A A B A ...: 13 of 40 frames garbled at both sizes); `G-bench-nine-open`: the same from the frame the Workbench opened. `sndPlayed` in the probe lines rises by 10 every half second while the pointer rests there (`s-1080`), and by 100 every 5 s for the whole of `s-2160`, whose viewer sat on the Workbench without video: 1,659 sounds in a run that never left the front end. Picture `ready-render-bench-strobe.jpg` (four consecutive viewer frames). | As M1: `SMIFrontEnd.cpp` 824-825 and `MIFrontEnd.cpp` 356/370: `Act("preview")` calls `Changed()` even when the part is already previewed, `Rebuild()` replaces the hovered button, the new button is hovered again: a rebuild loop of 3 frames. Make preview a no-op when nothing changes (no `Changed()`, no `UiNote`), let `OnUnhovered` stop only its own preview, and prepass the new body after `ChildSlot[Body]`. Not fixed at the branch head (no change under `Source/MurderInc/UI` since `fd8ce12`). |
| R3 | should-fix | **Thin geometry blinks at render scale 0.50, the scale E3DS's card runs at** (version 4 on E3DS: 0.50 to 0.63). On the fire escapes of the first street, 8 x 8 pixel blocks jump between about 5 and 75 luma levels from one frame to the next (light blotches appearing and vanishing on the railings); at 0.75 and 1.00 the same blocks are steady. Whole picture: still small. | Game frames `r-dev2` (lossless, still camera, 40 frames each): fire-escape region (x 62-78 %, y 0-42 %) `rev8` **0.44 %** at 0.50, 0.11 % at 0.75, 0.033 % at 1.00; `tstd99` 13.9 / 5.4 / 3.0; one block's luma over 8 frames at 0.50: 77 6 6 58 62 8 11 7, at 0.75: 32 32 31 31 31 31 32 32. Whole frame `rev8` 0.044 % / 0.035 % / 0.010 %. Pictures `ready-render-fire-escape-blink.jpg` (four consecutive frames at 0.50 and at 1.00), `ready-render-flicker-map-50.jpg` (frame, temporal std x 8, up-and-down map x 8: the bright spots top right are the fire escapes). At the viewer the encoder at QP 34 smooths most of it but not all: the fire escapes of the stream's still view (x 60-68 %, y 0-40 %) have `rev8` **0.018 %** at render scale 0.50 (`s-1080-l20`) against 0.003 % at 0.75 (`s-1080`), six times more, still small next to the strobe of R2. | `r.DynamicRes.MinScreenPercentage` 50 to 60 in `[MICloud]` (or `-MICVars=r.DynamicRes.MinScreenPercentage=60` on E3DS, allowed by the viewer-command list) costs a few per cent of the GPU on the box's card (BOX.md row 43: 6.00 ms at 50 %, 6.39 ms at 75 %; more on the A4000, where the ladder's steps can pay for it) for a steadier picture; the source (Lumen reflections, screen traces or TSR on the fire-escape material) is not yet narrowed (run `r-dev3`, below). |
| R4 | should-fix | **The texture streaming pool is over budget in the opening street at 1080p and 1440p**: the pool is 600 MB (`[MICloud]`), the wanted textures 717 to 865 MB (1080) and 721 to 876 MB (1440). The Development game prints "TEXTURE STREAMING POOL OVER 23.104 MiB BUDGET" in red over the objective panel; the Shipping game does not print it, but drops mips the same (softer textures, mip changes while turning). | Probe lines `texStreamMB` / `poolMB=600` of `s-1080`, `s-1440`; frame `dev2-still50-f10` of `r-dev2` (red line at the top left); the menu lane's note (49.6 MB over at 1080, 302 MB at 4K). | E3DS's A4000 has 16 GB and the game used 6 to 7 GB at 1080p (BOX.md row 54): raise `r.Streaming.PoolSize` to 1000 in `[MICloud]` for the next package, or `-MICVars=r.Streaming.PoolSize=1000` now (the variable is in the viewer allowlist, 200 to 3000). |
| R5 | should-fix | **One 340 ms freeze while standing still in play** (game thread: `gameMs=339.8`, the GPU and render thread normal), and viewer gaps of 233 ms (1080) and 126 to 132 ms (1440) in the still and aim phases. Not repeated in the 1440 run's game lines (worst 50 ms, at the start). | `s-1080` probe line 138 (`fps=36.9 worstMs=339.9 ... gameMs=339.8`, yaw unchanged, `state=2`); `analyze.py` viewer phases (`gap_max_ms`). | Run the Development game standing for two minutes with `stat hitches` / `-LogCmds="LogGarbage Log"`: a garbage collection is the first suspect (a 60 s rhythm). |
| R6 | must-fix (fixed in the branch, not yet packaged) | In every first-person frame of this package the support hand is a large brown ball over the crosshair, and the aimed red dot is a thick black ring round a small clear circle. | Stream frames `s-1080/s-still.jpg`, `s-aim-chopper.jpg` (and the same at 1440). | Fixed in `8d0d6ac`/`7c0bc1a` (hands data and C++) and `7e120ac`/`a88dcdc` (the optic housing fades), not yet packaged. **Watch on the v6 package:** `a88dcdc` fades the housing with a screen-door dither keyed to the pixel position (not temporal): during the aim-in, at render scale 0.50 under TSR, that is a classic shimmer source. `stream-grab.txt`'s `G-aim-chopper` grab measures it (it must stay near this run's `rev8` 0.009 %). |
| R7 | nit | On the Workbench the NINE's slide reads as flat silver with a plain white block in front of it, and an orange glow sits at the suppressor's muzzle. Not checked against the art: may be intended. | `s-1080/s-bench-nine.jpg`, `s-bench-nine-fit.jpg`. | For the weapons lane to confirm. |

**Checked and clean (numbers):** no black or pink surface and no default (grid) material in any frame looked at (street,
El, fences, shop fronts, the six-gun rack, the Workbench, the first-person guns) in the SM5 game; no start-up black frame
in play (the lowest mean luma of any grabbed play frame 43.7, a dark aimed view); **auto exposure steady**: the mean luma
of a still view varies by 0.01 to 0.07 levels (standard deviation) over 40 to 90 frames at every scale and size; **no
resolution oscillation** (render scale 0.75 in every probe line of `s-1080` and `s-1440`); **no key-frame pulsing** (one key
frame per session at the viewer); **QP fixed at 34**; the still view at the viewer: `mad` 0.04 to 0.11 levels a frame,
`rev8` 0.007 to 0.029 % (1080 and 1440), the aimed CHOPPER 0.009 %; the game's own frames at 0.75 and 1.00: whole-picture
`rev8` 0.035 % and 0.010 %. The slow turn (3 browser pixels every 16 ms) at the viewer: `mad` 5.2 (1080) and 6.0 (1440),
`rev8` 3.5 % and 4.4 %, smooth arrival (60 a second, gaps under 36 ms). The menus at 2560 x 1440 are the 1080 layout scaled.

**Not done:** the variant run `r-dev3` (which of Lumen reflections, screen traces, TSR or render scale removes R3's blink:
`/project/ue/ready/render/repo/tools/box/cloud/render-dev3.txt`, queue line in `/project/ue/ready/render/q4.txt`) waited
behind other lanes' games for 25 minutes and was withdrawn; run it before choosing R3's fix. A browser viewer (canvas grabs) cannot run on the
box (BOX.md row 27: headless Chrome gathers no ICE candidates); the Python viewer decodes the same H.264 the browser would.
No run on E3DS itself.

**Tools** (on the box, not in the repository: `/project/ue/ready/render`; the strobe's 40 consecutive 1080p viewer frames are kept in `evidence/G-bench-nine-fit.y`): `rtcgrab.py` (made from `rtcinput.py` by
`mkgrab.py`: the `grab <n> <name> [bg]` verb and `frames.json`), `stream-grab.txt` (the viewer script), `flicker.py` (the
numbers above, `--map` for the pictures), `analyze.py` (a run's probe lines and viewer phases), `render-dev.txt` /
`render-dev3.txt` (the demo-director captures), and `repo/tools/box/cloud/lag-test3.sh` (lag-test.sh with the viewer
choice and a GPU claim: a placeholder process named MurderInc, as `repo-guns/r4c/hold.sh` does, from the moment the GPU is
free until the run's own game exists).

## Config, code and E3DS audit (read-only lane, 2026-11-25, 21:30 to 22:30 UTC)

**What was read.** `unreal/MurderInc/Config/DefaultEngine.ini`, `DefaultGame.ini` (`[MICloud]`), `DefaultEditor.ini` (there is no Linux
override ini); the launcher `tools/box/cloud/MurderInc.sh` and `package-cloud.sh`; `Source/MurderInc/Cloud/` (`MICloud`, `MIPacing`,
`MIQuality`, `MISession`, `MIStreamQuality`) at the branch head; the engine's own source on the box (`/project/ue/UnrealEngine`, 5.9.0:
`PixelStreaming2PluginSettings.cpp`, `DynamicResolution.cpp`, `RenderUtils.cpp`, `BaseScalability.ini`, `VulkanPC/DataDrivenPlatformInfo.ini`);
the game logs of the render lane's runs (`/project/ue/ready/render/lag/r-dev2`, `s-1080-l20`) and of the E3DS sessions kept on the box
(`/project/ue/cloud/e3ds-session-1`). E3DS's documentation site could not be fetched from this session (its host is outside the session's
network); what it says is taken from PREFLIGHT.md's citations and from search-result extracts (Dynamic sizes the stream to the page or
iframe and "has a drawback regarding the quality of the video in mobile devices"; Custom is a fixed size). No game was run in this lane.

**The one fact that changes the earlier numbers.** The trial package (`fd8ce12`) has none of release 3c: `6a6b0ea` (the session, the
encoder range) and the ladder commits all come after it (`git merge-base --is-ancestor 6a6b0ea fd8ce12` is false; `git diff --stat
fd8ce12 HEAD -- Source/MurderInc/Cloud` is 2,404 lines). So every "QP fixed at 34" above (render audit, menu audit) and version 4's
E3DS numbers are the **exact quantiser**. The v6 package will by default give the encoder **QP 24 to 42** around E3DS's Medium 34
(`MIStreamQuality.h` 16-20, `MICloud.cpp` 152), and nothing about that path has been seen at the viewer through a real browser.

**What E3DS really starts the game with** (the game's own `Command line:` line in the E3DS session logs on the box): the launch options
of the stream configuration come **first** (`... -FullStdOutLogOutput -MICloudProbe=1 -PixelStreamingEncoderCodec=H264 ...`), then
`-PixelStreamingWebRTCMinBitrate=100000 -PixelStreamingWebRTCMaxBitrate=20000000 -PixelStreamingEncoderMinQP=34
-PixelStreamingEncoderMaxQP=34 -Windowed -ForceRes -ResX=1920 -ResY=1080 ... -PixelStreamingEncoderMaxQP=31`. No start bitrate is
passed, so Pixel Streaming 2's default applies: `PixelStreaming2.WebRTC.StartBitrate` **1,000,000** (MaxBitrate default 40,000,000,
E3DS caps it at 20,000,000; `KeyframeInterval` -1; rate control CBR). Because launch options precede E3DS's own arguments and the
engine takes the first occurrence, a launch option can set any of these.

### What to set for the meeting (E3DS panel only, no rebuild)

| Where (E3DS) | Value | Why |
|---|---|---|
| Common, Browser Resolution | **Custom 1920 x 1080** (both boxes) | the size proven on E3DS's A4000 (version 4: 60 fps, render scale 0.50 to 0.63); the start size never changes mid-session (Dynamic resizes on every page or window change, C6); larger Custom sizes bypass the game's 1080 clamp (R1) |
| Developer, Video Quality | **Medium** | QP 34. High is QP 16: 14.5 Mbit/s in fast turns on E3DS in version 4, and with v6's range (8 to 24) it received 22 frames a second in fast turns even on a 20 Mbit/s link (PROGRESS.md, release 3c, encoder table): High is not safe for a demo |
| Developer, Launch options | **`-sm5 -MIQpExact -MICVars=r.Streaming.PoolSize=1000`** | `-sm5`: C3; `-MIQpExact`: C1 (version 4's encoder, the one proven on E3DS); the pool: R4. All three are launch options the launcher passes on (only Pixel Streaming dumps and the session options are dropped, `MurderInc.sh`); each is printed in the game's log |
| Console commands field | **empty** (no `t.MaxFPS 30`) | E3DS's own suggestion of a 30 cap would pin the frame-rate target at 30 (`MICloud.cpp` ~1834-1856: a hand-set `t.MaxFPS` fixes it) |

Optional, after one session's pause-card line reads 60 a second with GPU under 14 ms: `r.DynamicRes.MinScreenPercentage=60` added to
the `-MICVars=` list (R3: the fire-escape blink at 0.50). Worked out from the measured split (an eighth of the GPU's time follows the
pixel count, `MI.Cloud.FpsPixelPart` 0.12; 0.60 is 1.44 times the pixels of 0.50): about +5 % of the GPU's time, 13.2 ms to about
13.9 ms under the E3DS-faithful load, inside a 16.7 ms frame. Not measured on E3DS.

### Findings, most severe first

| # | Severity | Finding | Evidence | Fix (exact value, file and line; proposed, not made) |
|---|---|---|---|---|
| C1 | should-fix (decide before the meeting) | **v6's encoder range trades a fixed picture for one that sharpens standing and softens moving.** With Medium the encoder may use QP 24 to 42; on the box's emulated links the QP swung by about 10 between standing and turning within seconds, where version 4's exact 34 never moved. That is the "picture breathes with motion" effect a viewer reads as instability; the range's gain (no stall on a thin link) is not needed on an office connection, where version 4's exact 34 held 60 frames a second on E3DS with 8 Mbit/s at its peak. | PROGRESS.md release 3c, encoder table: Medium, 4 Mbit/s link, standing QP 26.8 against turning 36.1; 20 Mbit/s link, standing 33.7 against turning 37.1 (exact: 34 in every phase). DECISIONS.md, version 4 on E3DS: QP 34, 0.5 Mbit/s average, 8 at most, 60.0 fps. `fd8ce12` has no range (above). | For the meeting: launch option `-MIQpExact`. For the public release keep the default only after one E3DS session read as LAUNCH.md section 13 says; if kept, a narrower range is the gentler compromise: `-MIQpBelow=4 -MIQpAbove=6` (QP 30 to 40), not measured. Code defaults are `MICloud.cpp` 152 (`GQpBelow = 10, GQpAbove = 8`). |
| C2 | should-fix (only with the range on) | **The first seconds of every session start from a 1 Mbit/s estimate.** With CBR and a QP range, the encoder fits the bitrate WebRTC gives it, and the sender starts at `StartBitrate` 1 Mbit/s (E3DS passes none): the click card, Home and the first Loadout screen can arrive at the top of the range (QP up to 42) until the estimate grows. With the exact quantiser (version 4) the start bitrate does not touch the picture. | `PixelStreaming2PluginSettings.cpp` (`CVarWebRTCStartBitrate`, default 1000000); the E3DS command line above (no `-PixelStreamingWebRTCStartBitrate`). Not measured: the box's viewer fixes its own estimate (BOX.md row 33). | If the range ships: launch option `-PixelStreamingWebRTCStartBitrate=6000000` (between E3DS's 0.1 and 20 Mbit/s; it is read before E3DS's arguments). Moot with `-MIQpExact`. |
| C3 | should-fix | **The look and the cost on E3DS depend on whether the machine's driver passes Unreal's SM6 check.** Every measured number, the ladder's table and version 4's E3DS sessions are SM5 (no Nanite, software Lumen, cascaded shadows). A Global-region machine with a newer driver would run SM6: Nanite, hardware-ray-traced Lumen and virtual shadow maps, a different picture never run on an A4000, with no ladder (`MI.Cloud.QualitySm6` 0). | `DefaultEngine.ini` 30-32 (SM6 is the targeted RHI), `package-cloud.sh` 220-223 (SM5 added as the fallback), the E3DS logs: `Fallback: this GPU or driver did not pass Unreal's SM6 check; running the SM5 shaders` (driver 550.90.07). `-sm5` forces SM5: the render lane's runs on the box's SM6-capable card logged `feature level SM5 | shader platform VULKAN_SM5`. | Launch option `-sm5` on E3DS for v6 (a no-op on today's machines, a guard on the next). |
| C4 | should-fix | **Software Lumen on E3DS never traces the meshes' distance fields, although the code says it does.** `MICloud.cpp` 412-425: the SM5 fallback branch (`!bNanite || !bLumen`) comes first, so the `else if (!bRT)` branch that sets `r.Lumen.TraceMeshSDFs 1` is never reached on SM5, and `DefaultEngine.ini` 25 (`r.Lumen.TraceMeshSDFs=0`) rules: Lumen traces only the coarse global distance field (blotchier bounce light and occlusion, blurrier reflections). | r-dev2 and s-1080-l20 game logs: `Set CVar [[r.Lumen.TraceMeshSDFs:0]]`, the SM5 fallback line, and 0 lines "Lumen traces in software (mesh distance fields)". | **Do not change for v6**: every E3DS and gate number was taken with 0, and the A4000 sits at 13.2 ms at the smallest picture. Add `r.Lumen.TraceMeshSDFs=1` as one variant of the r-dev3 run (it may also change R3's blink); then either move the `TraceMeshSDFs` branch ahead of the fallback branch (cost measured first) or correct the comment and the log line. |
| C5 | should-fix (before v6 is packaged) | **TSR keeps its history at the output size (100 %) while E3DS's card draws at 50 to 63 %**: half the history density Epic's preset uses (200 %), a likely contributor to R3's thin-geometry blink. The reason it was lowered (start with only 5 GB of the card free) predates the launcher's reaping and the game's own quit; the A4000 has 16 GB and the game used 6 to 7 GB. It cannot be tried on E3DS without a rebuild: `r.TSR.*` is not in the `-MICVars` allowlist. | `DefaultGame.ini` 45-47; r-dev2 log: `[AntiAliasingQuality@3] ... r.TSR.History.ScreenPercentage:200` then the cloud profile's 100; `MIPacing.cpp` 130-146 (the allowlist). | Run r-dev3 with `r.TSR.History.ScreenPercentage=200` as a variant. If it removes the blink, set `+CVars=r.TSR.History.ScreenPercentage=200` at `DefaultGame.ini` 47 for the package (about 130 MB more video memory at 1080p, per the comment there), and add `r.TSR.History.ScreenPercentage` (100 to 200) to `MITuningPrivate::Rules` so the next one is tunable from E3DS. |
| C6 | should-fix | **Browser Resolution Dynamic resizes the game on every request, with no wait and with odd sizes passed through.** `OnViewerSize` runs `r.SetRes` for each request whose size differs (`MICloud.cpp` 1347-1367); `FMICloudSize::Fit` rounds to even numbers only when it scales down (459-475), so a 1365 x 767 browser frame is drawn and encoded at an odd size. A window drag or a full-screen toggle mid-session gives a burst of resizes: new render targets, a TSR history reset (one soft frame each) and an encoder re-initialisation each time. | Code as cited; E3DS's player sends a size request whenever the frame changes in Dynamic (PREFLIGHT V3-6, player 1.0.146). | For the meeting: Custom 1920 x 1080 (above). In code: always round `Out` to even (`& ~1`) in `Fit`, and apply a size only after it has been the same for 300 ms. |
| C7 | nit | **The cloud profile's virtual-shadow-map setting does nothing on E3DS.** In Unreal 5.9 VSMs need Nanite (`RenderUtils.cpp` 1686-1693: `DoesPlatformSupportVirtualShadowMaps` returns `... && DoesPlatformSupportNanite`), and `VULKAN_SM5` has `bSupportsNanite = false`: E3DS draws cascaded shadow maps (`[ShadowQuality@3]`: 10 cascades, 2048). Shadow-shimmer checks on E3DS belong to the cascades, not to `r.Shadow.Virtual.MaxPhysicalPages=2048` (`DefaultGame.ini` 41). | Engine source and ini as cited. | Say so in the `[MICloud]` comment; nothing to change for v6. |
| C8 | nit (the ladder is off in v6) | **If the ladder is turned on later, its first three steps change the picture in play**: `clouds off`, `no bounce light`, `no Lumen reflections` are `live` steps (applied in a fight), and the shadow steps change the cascade count live. | `DefaultGame.ini` 105-109; `MI.Cloud.QualityLadder` 0 (`MICloud.cpp` 165). | Keep the ladder off for the meeting and v6 (it is). Before turning it on, mark the visible steps `calm` (applied at a card or set-up screen). |
| C9 | nit | **A viewer who joins while the frame-rate target is 45 or 30 keeps that cap for their stream.** `PixelStreaming2.WebRTC.Fps` follows the target, and Pixel Streaming reads it once, when a viewer's video is set up (the code's own comment). A reconnect after a drop stays at 45 even after the target rises. | `MICloud.cpp` 1741-1747. Not measured. | Leave `WebRTC.Fps` at 60 (only `t.MaxFPS` and the dynamic-resolution budget need to follow the target), unless decoupled capture is turned on. |
| C10 | nit | Stale text that misleads the reader of a log: `DefaultEngine.ini` 9-13 ("Vulkan SM5 has no Nanite and no Lumen, so SM5 is not targeted"), `MurderInc.sh`'s `-MIForceSM6` help and its "SM5 fallback: no Nanite, no Lumen" note (Lumen runs in software there), `DefaultGame.ini` 19 ("8 GB RTX 4080-class": E3DS's card is a 16 GB A4000); LAUNCH.md 317 still says "Try High once play is smooth" (see the table above). `r.DynamicRes.MaxScreenPercentage=75` (`DefaultGame.ini` 62) also means the Workbench, the screen that shows the guns and parts, is never drawn at full size even when the GPU has room (11 ms at 0.75 in version 4's menus): try 100 only with a measurement. | Files as cited. | Correct the comments; no behaviour change for v6. |

**Checked and fine:** frame-rate cap 60 (`t.MaxFPS`, `WebRTC.Fps`, the dynamic-resolution budget follow one target; `r.VSync` 0;
motion blur off); no periodic key frames (`KeyframeInterval` -1: no key-frame pulsing); H.264, `LatencyMode` ultra-low, `QualityPreset`
default, simulcast off, frame dropper on (measured by release A); dynamic resolution at the engine's own step rules
(`MinResolutionChangePeriod` 8 frames, increase amortisation), TSR on, flicker rejection on (`r.TSR.ShadingRejection.Flickering 1` from
`[AntiAliasingQuality@3]`), and the render lane saw no resolution oscillation; auto exposure: the extended luminance range and
`CachedLightingPreExposure` 8 (`DefaultEngine.ini` 27, 43), the Workbench and rack stage pin their exposure (`MIShowroom.cpp` 175-176),
and the render lane measured steady exposure; Graphics quality on the Settings card does not touch the resolution, the cap or the cloud
profile (`ApplyStreamedQuality`), and the cloud profile's device-profile priority keeps the scalability levels from undoing its pools;
the idle state clamps and then restores `r.DynamicRes.MaxScreenPercentage` and does not touch `WebRTC.Fps`; a viewer's size request is
drawn at most 1920 x 1080 (`FMICloudSize`, `MICloud.h` 67); the viewer allowlist keeps `MI.Cloud.QpExact` and the session options out
of a visitor's reach. The 4K stop (R1, M2) is not a setting: the only way a session reaches it is a Custom size above 1920 x 1080.
