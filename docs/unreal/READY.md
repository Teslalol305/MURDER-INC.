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
| M1 | **blocker** | **The set-up screens flicker in the stream.** Every rebuild of the front end is painted once with all its controls piled at the top of the column (zero-size layout: kicker, title, tabs, stat lines, BACK/ESC and DONE/ENTER drawn over each other). One such frame on every screen change; and while the mouse rests on a Workbench option the screen alternates garbled / clean / clean continuously (about 20 garbled frames a second) until the mouse moves. This is the "NINE + suppressor" frame of the trial, and it is not a NINE fault: the trial's SHORTY bench frame is the same. | Run `rm-st-1080`, consecutive stream frames: mouse resting on "Pistol suppressor" 29 of 90 frames garbled, after clicking it 20 of 60; screen changes Crew, Loadout, Workbench, back to Loadout, Block & Style, Briefing: exactly 1 garbled frame each; keyboard moves inside a screen 0. Run `rm-full-1080` stream frame `v007` (Loadout, keyboard only). Trial `t-guns/g-bench-nine-fit.jpg` and `g-bench-shorty.jpg`. MIShot never shows it (it lays the widget out again before reading it back), which is why the editor and MIShot pictures were always clean. Pictures `ready-menu-bench-hover-flicker.jpg`, `ready-menu-rack-garbled-stream.jpg`, `ready-menu-bench-garbled-stream.jpg`. | Cause in code: `SMIFrontEnd::Tick` calls `Rebuild()` (`UI/SMIFrontEnd.cpp` 226-257), which swaps `ChildSlot` during Slate's paint pass, after the frame's prepass, so the new widgets are arranged with no desired size for one frame. The Workbench option's `OnHovered` runs `Act("preview")` and `OnUnhovered` runs `StopPreview` + `Changed()` (lines 824-825): each rebuild replaces the hovered button, the new one is hovered again, so it rebuilds again. Fix: prepass the new body at once (`Body->SlatePrepass(AllottedGeometry.Scale)` right after `ChildSlot[Body]`), or rebuild from `UMIFrontEnd::Changed()` on the game thread instead of in `Tick`; and make preview idempotent (no `Changed()` when the same part is already previewed; `OnUnhovered` stops only its own preview). Prove with the stream burst (`/project/ue/ready/menu/stream.txt`): 0 garbled frames in every burst. |
| M2 | **blocker** (to confirm alone on the GPU) | **At 3840 x 2160 the stream stops.** The game drew and the viewer got 143 frames in its first seconds, then nothing for seven minutes while sound kept coming; the game's own line says `stream 0 a second (lowest 0)`. | Run `rm-full-2160`: probe lines `encFps=0 txFps=0` with `outW=3840` throughout; `LogPixelCapture: WaitForGPU: Timed out waiting for fence`, then `LogAVCodecs: Error Locking: Failed to lock output bitstream [NVENC 8]` and 21,010 `CUDA 700` errors from 20:17:12; the pause card line (picture `ready-menu-hud-4k.jpg`). The run shared the GPU with another lane's game for 178 of 412 seconds (POLLUTED), so it is not yet proof on its own; the same package at 1920 x 1080 streamed 60 a second, QP 18, 5.5 Mbit/s (`rm-st-1080` pause line). See the 4K stream run below. | Until a 4K run alone on the GPU streams, cap the output at 2560 x 1440 (PREFLIGHT V3-6 already says test at 1080 until the game limits its own size) and say so to E3DS's resolution setting. The stream lane owns the cause. |
| M3 | must-fix | **Crew screen looks broken.** The stage shows a large brown sphere (a fist seen end-on) and the CHOPPER cut at the eye; the crew card's portrait is the word RULE in a grey box. It is the first screen a first-time visitor sees after Hit the block. | `rm-full-1080/011-crew`, `rm-full-2160/011-crew`, stream `rm-st-1080/s-crew.jpg`; picture `ready-menu-crew.jpg`. | Frame the Crew stage on the gun alone (as the Briefing does) until the arms read well there, and give the card a real portrait or no portrait box. The hands data in the branch (`8d0d6ac`, `7c0bc1a`) removes the ball in play; whether it does on this stage is not seen (not yet packaged). |
| M4 | must-fix | **Carried guns show "..." on their rack card** instead of "Carried · slot n", at every size ("C..." at 4K). Looks like placeholder text. | `rm-full-1080/014-rack`, `021`; `rm-full-2160/014-rack`; stream `s-rack-row2.jpg`; picture `ready-menu-rack.jpg`. | `SMIFrontEnd.cpp` 624/648: the tag shares a 176-unit row with the "E Attachments" button and is ellipsized to nothing. Put the tag on its own line (or a short "SLOT n" chip). |
| M5 | must-fix | **Focused controls scroll out of sight.** The rack shows the second row of cards cut at "Kill speed"; keyboard or pad focus on STICK, STRETCH or RATTLER leaves the focused card half hidden. On Block & Style the focused Difficulty row is cut by the bottom bar (its note is a half line at 4K). | `rm-st-1080/s-rack-row2.jpg` (stream, focus on STRETCH), `rm-pad-1080/014-pad-rack-d`, `rm-full-1080/106-where-row3`, `rm-full-2160/106-where-row3`; picture `ready-menu-where.jpg`. | Scroll the focused widget into view (`SScrollBox::ScrollDescendantIntoView`) on every focus move, or fit the page (shorter Where title, less padding). |
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

**Not reached:** the death card and the debrief (a Development script mistake kept the run paused; in the Shipping stream the
player stood in the street 80 s and was not attacked), the Hold the Block results. 2560 x 1440 and 1280 x 800 MIShot runs and a
4K stream run were queued behind other lanes' games when this was written: see the addendum below if present.

**Seen on the way, other lanes' items** (evidence only, not menu): in the trial package the support hand is still a brown
sphere in play and the aimed red dot a thick black ring (`rm-full-1080/117`, `124`): fixed in the branch's hands data and
`7e120ac`/`a88dcdc`, not yet packaged. The Development game prints "TEXTURE STREAMING POOL OVER 49.578 MiB BUDGET" (1080) and
"OVER 302 MiB" (4K) in red at the top left (`117-hud-play`); the Shipping game does not show the message, but the pool is over
budget. `LogMaterial: M_Weapon_CasingPistol missing usage flag Nanite! Default Material will be used` and the red dot's lens and
reticle materials invalid on a Nanite mesh (SM6 path; E3DS runs SM5).
