# Smooth play: the lanes' findings

The owner played version 4 on E3DS: "It is very laggy and buggy" (stutter or freezes, a low frame rate; bugs in menus,
weapons and gameplay). DECISIONS.md (2026-11-25, ~21:00) makes this file's verdict a release criterion. One section per
lane; every number names the run it comes from. Severities: blocker (a freeze, a crash, a stuck state, or under 50 fps
sustained on E3DS-class limits), must-fix (a player would feel or see it), should-fix, nit.

## v6 prover verdict (2026-11-26, runs 19:29 to 21:05 UTC; supersedes the 02:50 section below)

**Verdict: NOT-YET.** There is no freeze left in play and no crash, and 60 is held for 15 minutes. But "every number better
than or equal to version 4's" is not met on two counts, so DECISIONS.md criterion 4 (21:00) is not closed:

1. **Viewer-driven play of the front end and all four guns has more missed refreshes than version 4**:
   **14.0 and 7.9** frames over 25 ms a minute against version 4's **4.3 and 4.8** (30 and 17 frames against 9 and 10).
2. **The engine takes 3.4 to 4.1 s longer to its first frame** (6.0 and 6.7 s against 2.8 and 2.6 s). The pipeline cache
   removed the shader freezes at the price of a longer start.

What is better: version 4 crashed at 126 s of Hold the Block (SIGSEGV; its third crash in three sessions); the head ran
**15.9 minutes** with 0 frames over 50 ms. The Story to the extraction has 0 frames over 25 ms. The front end's worst frames
are 2 to 3 times shorter. The target never left 60 in any run.

### The package measured, and why it is not rebuilt for the newest head

| What | Value |
|---|---|
| Package | `MurderInc-v6p.zip` (box `/project/ue/smooth/v6p/cloud`, built by `package-cloud.sh` of `b665160`, Shipping and Development games, pipeline cache in: the logs show `FPipelineCacheFile ... with 405 entries` and `PipelineFileCache = 1`). Version 4 is `6c4d810` (`/project/ue/cloud/v3a-fix/out/MurderInc.zip`) |
| Against the head (`675e5c2`) | `git diff b665160 675e5c2 -- unreal` is three data files: `grips.json` (hand anchors, from the offline hands lane), `guns.json` (8 lines), `presentation.json` (blood colour). No C++, no art, no shader, no asset. The hands data changes only where a solve puts the hand, not what is drawn or loaded, so it cannot move a frame time by a refresh. I did not rebuild: a rebuild would cost a cook and a zip, and every run below would need repeating for the same result. **A package of the final head needs one run of `n-menus` and `n-story` after the fixes below, not a new proof** |
| Conditions (every run) | `lag-test.sh` with `load=1:0.05:0:1024` (l20), `cpus=0-7`, `-sm5`, 1920 x 1080, cold user (`fresh`, fresh `Saved`), package copied to the box's local disk (`/tmp/v6p`), the GPU claim held (`gated.sh` queue), CSV profile of every frame. Viewer through Pixel Streaming (join after 3 s) unless the run is marked `nv`. **Every run CLEAN**: `others=0` and `build=0` in every watcher line (263 to 1,060 lines a run), no other game or compiler. GPU 11.8 to 12.3 ms a frame at picture 0.50 to 0.75 (E3DS read 10.6 to 13.2 ms) |
| Why version 4's Story and holdout have no viewer | Version 4's Development game was run with `viewer=0`; the new package has both with and without. Compare `nv` with `nv` |
| Numbers | `scripts/v6sum.py`, `over25.py`, `tgt.py` in `/project/ue/smooth/v6p/scripts` (every CSV frame; never one-second averages). Runs in `/project/ue/smooth/v6p/runs` |

### Per-frame numbers

| Run | Frames, length | fps | Frames over 25 / 50 / 100 ms a minute | Worst frame | 1 % low | Steady (median 10-s) | Target |
|---|---|---|---|---|---|---|---|
| **Front end by script, 0 to 33 s** | | | | | | | |
| new, viewer (`n-story`) | 1,975, 33.0 s | 59.84 | 3.6 / 1.8 / 0.0 | 84.2 ms (the first Crew draw, 6.06 s) | 47.8 | 59.9 | 60 |
| new, no viewer (`n-story-nv`) | 1,971, 33.0 s | 59.71 | 9.1 / 3.6 / 0.0 | 68.9 ms (6.05 s) | 41.0 | 60.0 | 60 |
| **version 4**, no viewer (`v4-story-nv`) | 1,951, 33.0 s | 59.11 | 12.7 / 5.5 / **3.6** | **190.8 ms** (0.82 s); 151.9 ms at the Crew draw | 24.4 | 60.0 | 60 |
| **Story run, 35.5 to 87 s (the demo director to the truck, four guns, reloads, blast)** | | | | | | | |
| new, viewer | 3,090, 51.5 s | 59.99 | 0 / 0 / 0 | 19.3 ms | 59.5 | 60.0 | 60 |
| new, no viewer | 3,089, 51.5 s | 59.99 | 0 / 0 / 0 | 18.5 ms | 59.5 | 60.0 | 60 |
| version 4, no viewer | 3,090, 51.5 s | 59.99 | 0 / 0 / 0 | 16.8 ms | 59.9 | 60.0 | 60 |
| **Viewer-driven front end and all guns through the stream (Shipping, `guns-keys.txt`, 8 s to the end, about 128 s)** | | | | | | | |
| new `n-menus` | 7,706 | 59.89 | **14.0** / 1.4 / 0.0 | 76.3 ms | 38.7 | 60.0 | 60 |
| new `n-menus2` | 7,752 | 59.93 | **7.9** / 0.9 / 0.5 | 100.9 ms | 43.4 | 60.0 | 60 |
| version 4 `v4-menus` | 7,582 | 59.84 | **4.3** / 1.4 / 0.9 | 158.1 ms | 41.1 | 60.0 | 60 |
| version 4 `v4-menus2` | 7,568 | 59.92 | **4.8** / 0.5 / 0.5 | 149.4 ms | 44.7 | 60.0 | 60 |
| **15-minute holdout (Hold the Block, `sm-long15.txt`, viewer, 8 s to the end)** | | | | | | | |
| new `n-long15` | 57,352, 956 s | 59.98 | 0.4 / **0.0** / 0.0 (7 frames over 25 ms) | 36.0 ms (797 s) | 58.6 | 60.0; slowest 10 s: 59.9; seconds under 57 fps: 0 | 60 all run |
| new `n-long` (earlier, shorter script) | 45,495, 759 s | 59.94 | 1.4 / 0.6 / 0.0 (8 over 50 ms: 70.2 at 190 s, 87.4 at 366 s, 94.1 at 765 s, five of 50 to 53) | 94.1 ms | 55.4 | 60.0; seconds under 57: 3 | 60 all run |
| version 4 `v4-long-nv` | **crashed at 126.4 s**: `SIGSEGV`, `Unhandled Exception`, exit 139 | | | | | | |

Other facts, from the same runs:
- **Crashes**: none in the head's 8 runs (about 40 minutes of play). Version 4: 1 of 1 today, 2 of 2 in the hitch lane.
- **Target drops**: none in any run. No spell under 60 (`tgt.py`: 0 seconds at 45 or 30 in about 3,000 probe lines of the head). So there
  was nothing to recover from; the drop and recovery rules were not exercised by these loads.
- **Synchronous loads** (`FlushAsyncLoading` events in play): 0 in the head's runs, 40 in version 4's Story.
- **PSO creation hitch frames**: version 4 5 in its 99-s Story run and 10 to 12 in the menus runs; the head 0 in the Story and 4
  in the menus runs, 3 of them inside the first 8 s.
- **Graphics quality press** (`n-q`, new only): 1 frame of 99.3 ms at 9.8 s, 2.9 / 1.5 / 0.0 a minute over 41 s.
- **Garbage collections** in the holdout: 15 (CSV events), no frame over 36 ms in the run.

### What is left (all for the game's owner; no game code was edited here)

1. **Frames at 27 ms in viewer-driven play with all four guns.** A frame in these runs has a median 27 ms: one refresh missed,
   with the game thread 3.7 ms, the render thread 6.9, the RHI 2.4 and the GPU 12.1: the same figures as version 4's
   (3.1 / 7.3 / 2.6 / 12.1), so the lateness is in how the shared card hands the frame over, not in a thread. They cluster:
   13 of `n-menus`'s 30 are between 70 and 90 s (guns being drawn). The stream carries twice the data (17.4 and 13.6 Mbit/s
   against version 4's 7.8 and 6.6), so the new guns and screens are heavier to encode and to draw. **The cause is not
   proven**; a GPU trace of the guns phase on this load would show it. The Story, where the same guns are used, has none; one
   reading is the first draw of a gun after a switch, but that is a guess.
2. **The start is 3.4 to 4.1 s longer.** From `Opened FPipelineCacheFile` to `Game Engine Initialized` the log spans 4.4 s in the
   head (20:40:02.176 to 20:40:06.601) against 0.5 s in version 4 (the engine's cache open and the save of the device
   pipeline cache sit in that span). The 405 PSOs compile in 0.12 s, so the time is the cache's own set-up. It happens
   before any picture, so it is a longer black wait on a cold start, not a hitch in play; still it is a number that is worse.
   Moving it behind CLICK TO PLAY (the first title frame) or into the launcher's preload would remove it.
3. **Isolated frames of 50 to 100 ms remain** (8 in 12.6 minutes of Hold the Block; the first Crew draw at 6 s with 84 ms; the
   Graphics press). One of them is the RHI thread (56.4 ms at 190 s). None reached 100 ms in the Story or the holdout.
   They are much fewer than version 4's, but "no freezes" is read as none over 50 ms, which is not yet true.
4. **Not measured**: E3DS's own A4000 (this emulation shares the card in time slices and is harsher than E3DS's sample of
   version 4, whose worst frame averaged 16.8 ms); a package of the final head; B5's pause when the viewer leaves was run
   (`n-away`: worst 42 ms, no freeze) but its pause state was not read here, so the bug lane's check stands; B3 on version 4.

To close: fix items 1 and 2 in the game, build the head's package (`package-cloud.sh`), and run `n-menus`, `n-menus2`, `v4-menus`
and `n-story` once more from `/project/ue/smooth/v6p/queue.txt` (the queue and `gated.sh` are kept there). A verdict of "smooth"
then needs frames over 25 ms a minute at or under version 4's (4.3 and 4.8) in the menus runs, a start no longer than
version 4's, and no frame over 50 ms in the holdout.

## Earlier independent verdict (superseded by the section above) (prover lane, 2026-11-26, 02:50 to 03:33 UTC)

**Verdict: NOT SMOOTH, and the proof is incomplete.** DECISIONS.md criterion 4 (21:00) is **not met**:

- **60 fps is not held frame by frame** under the E3DS-class load. On a package of the head:
  - Story play: 57.1 fps, 30 frames over 25 ms a minute, 1 % low 30.2 fps.
  - Playing all four guns through the stream: 82 frames over 25 ms a minute, 1 % low 26.0 fps.
- **The cold-start freezes are still there**: 260.7 ms on the title, 163.8 ms at the first Crew draw and 145.0 ms in the
  streamed front end. This is H3, which is not fixed.
- **"Better than version 4 under the same conditions" is not shown.** The version 4 control runs and the 15-minute
  holdout never ran, because **the box ended at 03:33:22 UTC with `credits_exhausted`** (`gpu_rental`: status `ended`,
  1,105.84 credits spent). That happened 10 minutes into the holdout run and before any version 4 run. No lane can
  measure on the box until the owner adds credits and a box runs again. This lane may not rent one.

What the fixes did deliver is real, and it is listed below.

### The package measured

| What | Value |
|---|---|
| Source | The branch head `5566ee4`. Its `unreal/` tree is identical to `9032311`, where the perf lane's suite passed 220 of 220 with 0 skipped and the golden replays included (`git diff --quiet 9032311 5566ee4 -- unreal`). It contains every fixer's commit: `63d4862`, `3ac39ee`, `de28380`, `4b621b7`, `36da424`, `e618e90` and the `HeldClips` fix |
| How it was built | The branch's own `package-cloud.sh` at `5566ee4` (`MI_COMMIT` set, so `BUILD.txt` names that commit), in this lane's folders on the box: `/project/ue/smooth/prove/pkg.sh`, release copy `prove/rel`, cloud folder `prove/cloud`. The generated content is reflinked, read-only, from the bug lane's clone; nothing in the inputs of that content changed between `1119352` and `5566ee4`. The steps were src, refresh, editor, weapons (guns, rattler, parts and sockets ok), overlay, usage, the Development and Shipping cooks (289 of 289 Sound Waves and 35 of 35 weapon assets in both pak lists) and the zip: `MurderInc-prove.zip`, 2.3 GB, sha256 `ac778ef3...`, 02:54 to 03:10 UTC. It is a proof package, not a release |
| E3DS-class limits | The hitch lane's line: `lag-test.sh` with `load=1:0.05:0:1024` (`l20`, the load that reproduces E3DS's own GPU readings), `cpus=0-7` (the 7 task workers E3DS logs), `-sm5`, 1920 x 1080, `runas=fresh clean=1` (a cold user, a fresh `Saved`), the package unpacked on the box's local disk (C6), a viewer through Pixel Streaming, a CSV profile of every frame. The runs held the GPU claim (`prove/gated.sh`, a placeholder named `MurderInc`, `prove-claim`) |
| How close the emulation is | **GPU: close.** The probe read 12.9 ms (max 14.6) in the guns run and 12.9 ms (max 15.2) in the Story, at render scale 0.50 to 0.75. E3DS read 10.6 to 13.2 ms at 0.50 to 0.75. **CPU: the same kind** (7 workers, the RHI's extra threads), with faster cores. **Box:** CLEAN in both runs (`others=0`, no compiler, `build=0`); the box's CPUs were 65 to 67 % busy in each viewer's first 40 s and 24 to 42 % after that. **Not like E3DS:** the load shares the card in time slices. The game's frame is then late even when its own GPU work is 12 to 13 ms, and the load also slows the encoder (BOX.md) |

### Per-frame numbers (every CSV frame; `prove/scripts/prove_sum.py`)

| Run, scene | Frames, length | fps | Frames over 25 / 50 / 100 ms a minute | Worst frame | 1 % low | Steady (median of 10-s buckets) | Sync loads |
|---|---|---|---|---|---|---|---|
| `p-new-menus`, engine start before any viewer (0 to 8.4 s) | 183, 8.4 s | 21.8 | | 3,523.5 ms (engine init), 1,350 ms, 231.5 ms | | | (388 at engine init) |
| `p-new-menus`, the streamed front end (8.4 to 52.8 s): CLICK TO PLAY, Home, Crew, Loadout by keys and mouse, three Workbench visits, Block and Style, the Briefing | 2,643, 44.4 s | 59.50 | 47.3 / 4.1 / **1.4** | **145.0 ms** at 14.94 s (render thread 109 ms; Pixel Capture's `Timed out waiting for fence` in the same second) | 26.3 | 59.9 | **0** |
| `p-new-menus`, play (55 to 137 s): four guns drawn, aimed, fired and reloaded through the stream | 4,849, 82.0 s | 59.15 | **82.0** / 2.9 / 0 | 62.7 ms | **26.0** | 59.1 | 0 |
| `p-new-story`, the front end by script (0 to 32.1 s) | 1,862, 32.1 s | 58.08 | 50.5 / 9.4 / **3.7** | **260.7 ms** (the title, 1.13 s), **163.8 ms** (`MIMenu fe gearup`, 6.08 s) | 16.6 | 58.8 | **0** |
| `p-new-story`, the whole Story run to the truck (32.1 to 104.1 s), four guns, reloads | 4,116, 72.1 s | **57.11** | **30.0** / 1.7 / 0 | 53.0 ms | 30.2 | 59.1 (slowest bucket **47.8**) | 0 |
| `p-new-long`, Hold the Block, `sm-long.txt` | **lost**: the box ended about 10 minutes into the run. The CSV lived on the box's local disk, and the copy of the game log was not written. What I read from its probe and log lines while it ran is in the H2 and C1 rows below | | | | | | |

**What the frames over 25 ms are.** In the guns run's play the 112 frames over 25 ms have a median of 30.2 ms, which is
one display refresh missed. Their medians are: game thread 1.9 ms, render thread 18.0 ms, RHI 2.8 ms, GPU 12.4 ms. Only
5 of the 112 have a PSO miss (`prove/scripts/long25.py`). They come 2 to 13 times in every 5 s of play. So this is not
H4's shader stutter and not the game thread. It is the frame waiting for a card it shares with the load: in 1 to 2
frames a second the finished frame comes late. Whether E3DS's A4000 does the same, when the game is alone on it, can
only be measured there. The probe lines of our own E3DS sample of version 4 (DECISIONS.md 13:23) read a worst frame of
16.77 ms on average, so on that day the A4000 did not. This emulation is therefore harsher than that sample.

**Version 4 under the same conditions:** not measured today; the queued runs `p-v4-menus`, `p-v4-story` and `p-v4-long`
never started. The only matching numbers are the hitch lane's from 2026-11-25. They used the same `l20` load, the same
CPUs and a cold user, but they had **no viewer** (version 4's Development game pauses when a viewer leaves).
- `v4-story-l20`: 59.70 fps over the capture, 1 % low 40.1 fps, frames over 25 / 100 ms a minute 3.5 / 1.7, and 60 fps
  in every play second.
- Version 4 **crashed in 2 of 2** Hold the Block sessions (H1).
- On those numbers the head's Story under `l20` is **not better** than version 4's frame by frame. It has more 30 ms
  frames and a lower 1 % low; its own viewer's encoder shares the card, and version 4's runs had none. The holdout is
  better only in the sense that it no longer crashes.

### Every bug marked fixed, re-checked on this package

| Item | Re-check | Verdict |
|---|---|---|
| H1 / C1 / B1: the crash at the garbage collection after a gun switch | **No GPU** (`prove/nr.sh`, `-nullrhi`, CPUs 14 and 15): `cpu-nr-new`, the CPU lane's `full-csv.txt`. The switches came at 89.7, 98.3, 103.4 and 108.5 s, then `game:state complete` at 185.3 s, and the script played to its end at t 208.6 s. There was no `Signal 11` line. The run was stopped by its 330 s limit (exit 124). The v6 trial died at about 121 s on this script. **With the GPU:** `p-new-long` made 7 switches by 03:31:44 with no `Signal 11` line, until the box ended at 03:33. `n3-new`, the 15-minute no-GPU gate, was lost with the box | **Confirmed** for the CPU lane's script, past the second periodic collection. The long sessions on this package were cut short by the box. The bug lane's 14-minute `sb-long` and 12-minute `n3-fix` on its own package (`ab55e0d` plus its fixes, the same `HeldClips` code) still stand |
| H2: the frame-rate target never rises in play | Every drop on this package came back to 60 in play. `p-new-story`: `60 -> 45` at 03:19:39.671 (`the GPU took 13.2 ms a frame`), then `45 -> 60 ... for 10 s, in play` at 03:19:49.892 (10.2 s later). `p-new-long`: `60 -> 45` at 03:26:01.641, back at 03:26:15.452 (13.8 s). `60 -> 45` at 03:30:39.746; a second `60 -> 45` at 03:31:03.639 means the target had come back to 60 in between (that line was not read before the box ended). Back again at 03:31:24.121 (20.5 s). Probe lines over the holdout's first 135 play seconds: mean 59.2 fps, 12 seconds under 57 | **Confirmed fixed** (it rises in play). **But the drops still happen** under this load, three times in 9 minutes of holdout. Each one costs 10 to 20 s at 45 (the Story's slowest 10-s bucket: 47.8 fps). On a 60 Hz screen 45 judders |
| C2: synchronous loads | `Preload: 114 of 114 assets named by the data files are in memory, 0.2 s after the title screen came up` (`p-new-menus` game log, 03:15:49.658). `FlushAsyncLoading` events in the front end and play: **0** in both runs (the 388 in `p-new-menus` all fall in engine init, frame 0) | **Confirmed** |
| B4: the pause card cannot leave a run | `b4-new` (no GPU, the bug lane's `b4.txt`): `MIMenu changesetup` at t 20.419 s and `game:state title` in the same frame; `MIMenu totitle` at t 33.821 s and `game:state title` in the same frame. The next screens were `screen crew` and then `screen briefing`. Exit 0 | **Confirmed** |
| B3: Graphics quality press freezes | `p-new-q` was queued and never ran (box ended) | **Not re-checked** (the perf lane's before / after pair stands) |
| B5: pause when the viewer leaves | `p-new-away` was queued and never ran | **Not re-checked** (the bug lane's `sb-away-fix` stands). The page's half is still not done |
| C4: HUD trace scopes | Instrumentation only; no trace was taken | Not a smoothness fix; open as the perf lane says |
| C6: `lag-test.sh local=1` | Present in `5566ee4`'s `lag-test.sh`; every run here was from local disk anyway | Confirmed in the script |

### Still wrong (blocks the "smooth" verdict)

1. **Frames that miss a refresh in play under the E3DS-class load**: 30 a minute in the Story and 82 a minute with all
   four guns, a 1 % low of 26 to 30 fps, and 45 fps spells of 10 to 20 s after each target drop (H2's drop rule is
   unchanged; only the rise is fixed). It is not yet known whether this is E3DS's card or only this emulation: one
   E3DS session of this package with `-MICloudProbe=1` and the browser console's log would settle it (worst frame and
   target per second).
2. **H3, the cold-start PSO freezes**: 260.7 ms on the title, 163.8 ms at the first Crew draw (no synchronous load in
   it any more, so it is shaders), and 145.0 ms in the streamed front end. It needs the bundled pipeline cache (perf
   lane, "For the lead" 1). It is not done.
3. **H6, the front end's frame per key press**: not fixed (perf lane).
4. **B2, the long waits at the end of Hold the Block waves**: the owner's decision. **B6**, settings lost each session:
   the page bridge. **B5's page half**: the lead's.
5. **Not proven, because the box ended**: the 15-minute holdout on this package, version 4 under the same conditions,
   B3 and B5 on this package, and the no-GPU 15-minute gate (`n3`).

To finish this proof once a box runs again: unzip `/project/ue/smooth/prove/cloud/MurderInc-prove.zip` (the local
copies were lost with the box), then `bash /project/ue/smooth/prove/gated.sh /project/ue/smooth/prove/queue1.txt`. The
queue's first two lines are done and can be commented out. The `v4` line needs version 4's zip
(`/project/ue/cloud/v3a-fix/out/MurderInc.zip`) unpacked to `/tmp/smooth-prove/v4`. Kept on `/project`: the scripts
(`pkg.sh`, `package-cloud.sh`, `gated.sh`, `after.sh`, `nr.sh`, `queue1.txt`), this lane's copy of `lag-test.sh` (with the
perf lane's `spike=` key, the CSV kept for runs without a viewer, and its own claim ignored), `scripts/prove_sum.py`,
`scripts/long25.py`, and the runs `p-new-menus`, `p-new-story` (each with its CSV), `b4-new` and `cpu-nr-new`.

## CPU and game-thread cost (lane `cpu`, 2026-11-25, 21:20 to 22:40 UTC)

**Verdict of this lane: not smooth, because of one crash; the game thread itself is not the lag.** Run from a local disk,
the same package and script played the home screen, every set-up screen, a Story run with shots, bursts, reloads and all
four gun switches at **59.8 fps, no frame over 50 ms, the game thread at 2.1 ms a frame on average and 3.5 ms at the
99th percentile** (16.7 ms is the budget). But the game **crashed in all three measured sessions**, each time at the
engine's periodic garbage collection after a gun switch, about two minutes in (C1: blocker). The synchronous asset loads
of the set-up screens, the Briefing and the gun switches cost 7 to 18 ms of game thread each (C2). Casings, decals,
effects, the probe line, the JSON data and garbage collection were measured and are cheap. **The large freezes first
seen on the box (140 to 280 ms, one of almost a second) were the box's, not the game's** (C6): the same run from the
box's network volume had them, from its local disk it had none. That matters for every lane measuring on this box.

### How it was measured

| What | Value |
|---|---|
| Package | `v6trial.zip` (game `fd8ce12`, the guns trial; the newest package on the box), its Development game (`MurderInc`, the same code as the Shipping one, with stats, CSV profiler and trace) |
| Where | Unpacked privately twice: `/project/ue/smooth/cpu/v6t` (the box's network volume, where every lane's packages live) and `/tmp/smooth-cpu/v6t` (the box's local disk). Runs in `/project/ue/smooth/cpu/runs`, Insights exports in `/project/ue/smooth/cpu/ins` |
| E3DS emulation | `lag-test.sh` with `load=1:0.05:0.05:1024` (the gate's `v6-e3ds-l12` load) and `cpus=0-5` (6 CPUs, 5 task workers: Unreal's Vulkan RHI then runs without its interrupt and submission threads, as on E3DS's 8 hyper-threads), `-sm5`, 1920 x 1080, a viewer through Pixel Streaming, `-MICloudProbe=1` as on E3DS |
| How close | The GPU read **7.0 to 10.2 ms a frame at render scale 0.75** (probe `gpuMs`, `dr`); E3DS read 10.6 to 13.2 ms at 0.50 to 0.75 (DECISIONS.md, 13:23). This load is a little lighter than E3DS's card: right for game-thread costs, which do not depend on it; frame rates here are an upper bound for E3DS. The CPU side is harsher on threads (5 workers, not 6) and kinder on clock speed (the box's cores are faster than an A4000 server's) |
| Script | The Development game's demo director playing `tools/box/cloud/sound-demo.txt` (`full-csv.txt` / `full-trace.txt` in the lane folder): 20 s of home screen, the set-up screens (crew, four gun slots, the Workbench with a silencer previewed and fitted, level, mode, difficulty), a Story run: single shots, a burst, reloads, the dry press, switches to guns 2, 3, 4 and back to 1 with shots, melee, walking, sprinting, a jump, then the fight on the avenue (never reached: C1) |
| Runs | `cpu-full-tr` (network volume, Unreal Insights trace with `-trace=default,task -statnamedevents`: for attribution only, tracing slows the game thread), `cpu-full-csv` (network volume, CSV profile, no trace), `cpu-full-csv-local` (local disk, CSV profile, no trace). All CLEAN: no other game on the GPU in any second (`others=0` in every watcher line) |
| Tools | `UnrealInsights -OpenTraceFile=... -NoUI -AutoQuit -ExecOnAnalysisCompleteCmd="@=cmds.txt"` with `TimingInsights.ExportTimingEvents` / `ExportTimerStatistics` (`-threads=GameThread`; a thread id such as `2` selects the GPU queues, not the game thread), `lag_csv.py` and `csvsum.py` (frames over 25, 50, 100 ms a minute, 1 % low) |

![Per-frame times of the same script from the network volume and from the local disk](shots/smooth-cpu-frames.jpg)

**Per-frame numbers** (every frame of the CSV profiles, not one-second averages; network volume `cpu-full-csv` /
local disk `cpu-full-csv-local`):

| Phase | fps | frames over 25 / 50 / 100 ms a minute | worst frame | 1 % low | game thread avg / p99 |
|---|---|---|---|---|---|
| Home screen, 0 to 20 s | 58.4 / **59.8** | 33.0 / 9.0 / 3.0 vs **12.0 / 0 / 0** | 277.6 / **32.8** ms | 17.9 / **45.4** fps | 5.5 / 20.2 vs **1.8 / 3.4** ms |
| Set-up screens and Briefing, 20 to 49.5 s | 59.4 / **59.8** | 12.2 / 4.1 / 2.0 vs **10.2 / 0 / 0** | 140.3 / **42.6** ms | 30.8 / **45.6** fps | 2.4 / 12.4 vs **2.3 / 7.1** ms |
| Story run: shooting, reloads, gun 2, 49.5 to 98 s | 59.9 / **59.9** | 0 / 0 / 0 vs **7.4 / 0 / 0** | 23.7 / **48.4** ms | 54.8 / **48.9** fps | 4.7 / 14.8 vs **2.1 / 3.1** ms |
| Switch to gun 3 and its first shots, 98 to 104 s | 48.7 / **59.7** | 70 / 70 / 60 vs **20 / 0 / 0** | 277.3 / **29.3** ms | 4.1 / **41.8** fps | 7.8 / 178.7 vs **2.4 / 3.3** ms |
| Gun 4, gun 1, melee, walking, 104 to 119 s | 60.0 / **60.0** | 0 / 0 / 0 vs **0 / 0 / 0** | 22.0 / **20.0** ms | 56.5 / **58.2** fps | 2.7 / 4.2 vs **2.1 / 3.0** ms |
| Whole run | 59.0 / **59.8** | 12.1 / 6.0 / 4.0 vs **8.6 / 0 / 0** | 277.6 / **48.4** ms | 22.4 / **47.6** fps | 4.1 / 16.2 vs **2.1 / 3.5** ms |

From the local disk the frames over 25 ms are the render and RHI threads', not the game thread's (the worst, 48.4 ms at
89.75 s, is RHI 52 ms in the frame after gun 2's first draw; the game thread 2.7 ms): the render and stream lanes' ground.
The GPU was never the limit (GPUTime average 7.8 ms, worst 24.6 ms once).

### Findings

| # | Severity | Finding | Measured cost | Evidence |
|---|---|---|---|---|
| C1 | **blocker** | **The game crashes (SIGSEGV) at the first periodic garbage collection after a gun switch.** Stack (symbolised with `/project/ue/cloud/symbols/fd8ce12/MurderInc.debug`): `MIFirstPersonAnimPrivate::Sample` (`MIFirstPersonAnim.cpp:23`, `L.Clip->GetPlayLength()`) from `FMIFPAnimProxy::Evaluate` (`:300`). `UMIFPAnimInstance::SetPose` kept raw `UAnimSequenceBase*` in `FMIFPPose`; the rig lets go of the old gun's clips on `Equip`, the collector frees them, and an anim instance that still holds that pose evaluates freed memory | The process ends: exit code 139 | **3 of 3 sessions.** `cpu-full-tr`: switch back to gun 1 at 108.7 s, `CollectGarbageInternal` at 132.242 s (the periodic one; the one before at 71.13 s), the game thread's last frame starts at 132.262 s, "Signal 11 caught" at 21:53:51.88. `cpu-full-csv` and `cpu-full-csv-local`: the same stack, 13.7 and 13.9 s after the switch to gun 1, at the second periodic collection (the CSV's `GC` event at 60.7 to 60.8 s, the crash at about 122 s). The switch lane found the same crash in version 4 and fixed the source at `2a35906` (`HeldClips`, `MIFirstPersonAnim.h`); no package has that fix yet. To close it: a package of the fix through this same script past two collections (over 125 s, with switches), and a longer session |
| C2 | should-fix | **Synchronous loads on the game thread** in the set-up screens, the Briefing and gun switches: `LoadObject` / `FSoftObjectPath::TryLoad` from ticks and input in `AMIShowroom::Tick` (a gun swap: `UMIGunAssembly::Assemble` loads the gun mesh, every part mesh, top round, magazine and materials), `UMIWeaponComponent::EquipMesh` (gun mesh, idle clip), `UMIFirstPersonRig::Equip` (`LoadAs`: clips, part meshes, optics; it also parses `grips.json`, 62 KB, on every equip), `AMIPlayerCharacter` (arms, materials). Each asset not yet in memory is a `FlushAsyncLoading` that holds the frame | **Local disk: 7 to 18 ms of game thread** in the frame of each load (CSV events with the next frames' game-thread time: gun focus on the slot screen 10.4, 7.3, 9.4 ms; the Briefing 10.4 ms; switch to gun 2 11.7 ms; to gun 3 18.2 ms, its frame 18.6 ms). **Network volume: 202 ms** for the Briefing's load alone (trace 46.81 s: `FTickFunctionTask > MIShowroom > LoadObject > StaticLoadObjectInternal > FlushAsyncLoading`, 183.9 ms of it `MainThreadWaitingOnAsyncLoadingThread`) | Runs `cpu-full-csv-local` (CSV events column), `cpu-full-tr` (`ev_sel.csv`, `w_briefing.csv`). On a disk as fast as the box's local one these are one late frame each; on a slower or cold disk (E3DS's is not known; every E3DS session starts on a fresh copy, PROGRESS.md "What a cold machine adds") they grow towards the network-volume numbers. Fix without touching rules: load every offered gun, part and clip and the crew's arms once, asynchronously, on the home screen (six guns, 22 parts) and keep them referenced (a `UPROPERTY` array on a subsystem), so `TryLoad` finds them in memory; parse `grips.json` once |
| C3 | (withdrawn) | A freeze of almost a second around the switch to gun 3 in `cpu-full-csv` (five frames of 84 to 277 ms, 100.2 to 101.0 s) | none from the local disk: the same moment's worst frame 18.6 ms | It was the box (C6), not the game: `cpu-full-csv-local`, 98 to 104 s, game thread p99 3.3 ms |
| C4 | should-fix | **The HUD draw takes 15 to 22 ms in some traced frames** (`HUD Time`, i.e. `AMIHUD::DrawHUD` and what it calls: crosshair, weapon bar, health, objective, markers, subtitles); median 0.8 ms. No named scope inside, so which part is not known | Traced: 16 frames of 11 to 23 ms in 60 s of play (60.99, 67.83, 68.64, 76.15, 79.17 s ...), each the frame's whole excess (exclusive 15.5 to 22.0 ms, nothing under it but `DbgDraw_Canvas_TextItem_RuntimeCache` x30, 0.08 ms). Untraced from the local disk the whole game thread never passed 11.7 ms in play | Run `cpu-full-tr` (`ev_hud.csv`, `h_*.csv`). Not a hitch today; worth a named event round `DrawPlay`, `DrawFlow`, `DrawMenu`, `DrawWeaponBar`, `DrawWheel` and `UMIAudioSubsystem::DrawSubtitle` (new subtitle text is shaped and rasterised by the font cache the first time) before it becomes one |
| C5 | should-fix | **The set-up screens' Slate widget costs up to 47 ms in a traced frame** (`SMIFrontEnd [MIFrontEnd.cpp(86)]`), 13 frames over 10 ms between 30 and 57 s; 38 ms exclusive at the Workbench (40.36 s) | Traced 19 to 47 ms per event; untraced from the local disk the game thread's p99 on these screens is 7.1 ms, worst 18.3 ms | Run `cpu-full-tr`, `cpu-full-csv-local`. This is READY.md's "rebuild in the paint pass" (menu audit), here with its game-thread cost; nothing to add to its fix |
| C6 | **must-fix for the measurements** (not the game) | **Packages run from the box's network volume `/project` (9p) get freezes that the same package from the local disk does not.** Same package, script, load and CPUs: frames over 100 ms 4.0 a minute against 0, worst 277.6 against 48.4 ms, game thread p99 16.2 against 3.5 ms and even its average 4.1 against 2.1 ms. The traced run shows the form they take: seven frames of 73 to 181 ms inside scopes with no work in them (`Tick_PerformanceMonitoring` 125 to 181 ms at 34.9, 85.9, 88.9, 115.8 s; `Render_BeginFrame` 73 to 181 ms at 19.8, 22.9, 28.9 s): the thread was not running. Plain reads of the volume are not slow (300 random 64 KB reads of the `.ucas`: 0.53 ms median, 1.1 ms worst; the local disk 1.23 and 1.7 ms), so it is more likely page faults on the memory-mapped binary and paks in the box's sandbox than bandwidth. A second suspect is load from other jobs (some early stalls fell in seconds when the box was 92 to 99 % busy with other lanes' compiles), but the 1-second freeze of C3 came when the box was quiet (`cpu=36-52`, no compiler) | All long frames of `cpu-full-csv` and `cpu-full-tr` over 50 ms | Runs `cpu-full-csv` against `cpu-full-csv-local` (picture). **Every lane that measures frame times on this box should run its package from local disk** (`/tmp`, lost when the box stops; `unzip` there takes under a minute), or treat any long frame as the box's until it repeats from local disk. Earlier gates measured from `/project` too: their long frames may include this |
| C7 | nit | **Casings, magazines and debris are spawned physics actors, not pooled** (`UMIEffects::SpawnBody`: an `AStaticMeshActor` with CCD and shadows per casing, two per round; destroyed by life span) | `SpawnActor` 77 calls in the session, **0.086 ms average, 0.26 ms worst**; `RegisterComponent` worst 0.4 ms; `RecreatePhysicsState` / `DestroyPhysicsState` 0.001 to 0.002 ms; `Exclusive/Physics` 0.025 ms a frame | Runs `cpu-full-tr`, `cpu-full-csv`. At the CHOPPER's 720 rounds a minute that is about 2 ms a second spread over 24 frames: no hitch. Pooling them as the puffs are pooled is tidy work, not a lag fix. The 20-Goon fight was not reached (C1), so a full-auto fight with Goon fire is unmeasured |
| C8 | nit | **Garbage collection** (default settings: every 61.1 s, `gc.TimeBetweenPurgingPendingKillObjects`) | 3 collections, **2.4 to 3.2 ms** each (`CollectGarbageInternal`), plus 0.6 to 0.8 ms incremental; from the local disk the GC frame's game thread was 6.2 ms | Runs `cpu-full-tr`, `cpu-full-csv-local`. Not a hitch; only the crash's trigger (C1) |
| C9 | nit | **The probe line (`-MICloudProbe=1`, still set on E3DS)**: one line a second, built with ~40 `Printf` fields, `FPlatformMemory::GetStats` (reads `/proc`), and in the Shipping game `printf` + `fflush` to the launcher's pipe | The core ticker's scope rises from a median 0.004 ms to **0.15 to 0.24 ms once a second** (33 of 10,704 ticks over 0.15 ms in 60 s of play, 1.0 s apart; worst 0.52 ms): about 0.02 % of the frame time | Run `cpu-full-tr` (`STAT_FTicker_Tick` events). Nothing a player feels. The only risk is the pipe: if the reader of the game's stdout (the launcher's `tee`) stopped reading, `fflush` would hold the game thread; not seen |
| C10 | nit | **Per-frame scans and lookups**: `UMIAudioSubsystem::Observe` runs two `TActorIterator`s every frame; `UMIEffects` reads `MIJson::NumberOr(Fx, "a.b.c")` paths on every flash, tracer and casing; `UMIGameSubsystem::StartPitch` parses `presentation.json` (51 KB) on every run start; each `AMIExplosive` and objective actor parses it at boot | `UMIAudioSubsystem` tick 0.046 ms a frame on average (0.23 ms worst); the JSON parses have no named scope and were not timed alone: they run at boot, at a run's start and at a gun equip, inside C2's 7 to 18 ms frames at most | Run `cpu-full-tr`. Cache the JSON roots and the numbers once; no player sees these |
| C11 | nit | **AI, box world, timers, debug drawing.** The enemy logic senses on a randomised interval (`SenseEvery`), its line of sight is a loop over the 757 boxes of `FMIBoxWorld`, the nav grid is rebuilt only when a blocking box is removed (an explosive). No `DrawDebug*` in the game code; the only per-shot timer is the casing's show timer | Not measured in a fight (C1 ended every run first); `Exclusive/TickActors` 0.17 ms and `Ticks/MIGoonMovement` 12 ticks a frame with no Goon awake | Code review; a fight measurement is the next step once C1's fix is packaged |

### What this says about the owner's session

- **Stutter or freezes**: C1 ends a session about two minutes in once a gun has been switched (a frozen picture, then a
  lost stream); this is the one thing in this lane that a player of version 4 certainly met if they switched guns and
  played on (the switch lane found it in version 4). C2's loads are single late frames on a fast disk. The game thread
  does not explain a sustained stutter.
- **Low frame rate**: not the game thread: 2.1 ms of 16.7 on average with 5 task workers. A sustained low rate on E3DS has
  to come from the GPU, the render thread or the stream (the other lanes).
- **Our earlier E3DS measurement** (DECISIONS.md 13:23) was a 24-second holdout with no gun switch reported, so it could not
  meet C1. The probe's `worstMs` is the longest frame of each second, so one-second averages did not hide freezes there.

### Not done, not proven

- The fight (20 Goon slots, explosions, full-auto with casings): every run crashed before it (C1).
- A trace from the local disk (queued, dropped for GPU time): C4's and C5's traced numbers come from the network volume.
- Version 4 itself under this script: its demo director and menus differ; the hitch lane measures version 4.
- E3DS's disk speed and its first-session (cold) load times: C2's size on E3DS depends on them.
- No fix was written (this phase changes no game code).

### Files (on the box, not in the repository)

`/project/ue/smooth/cpu/`: `go.sh` (a queue of `lag-test.sh` runs that holds the GPU claim, a placeholder process named
`MurderInc`, from the moment the GPU is free until its last run ends), `full-csv.txt`, `full-trace.txt`, `csvsum.py`;
`runs/cpu-full-tr`, `runs/cpu-full-csv`, `runs/cpu-full-csv-local` (each CSV run with its `profile.csv`); `ins/` (the trace,
`tree.py`, `flat.py`, `evsum.py` and every export named above).

## Stutter and freeze hunt (lane `hitch`, 2026-11-25, 21:20 to 23:50 UTC)

**Verdict of this lane: not smooth, in either version.** Version 4 (the owner's) crashed in **2 of 2** Hold the Block
sessions (H1). The newest package (`v6trial.zip`, game `fd8ce12`) did not crash in this lane's four sessions, but it
**locks itself at 45 or 30 frames a second for the rest of a run after one heavy second**, because the frame-rate
target only rises on a menu screen (H2): with the GPU load that reproduces E3DS's own GPU readings (l20, below) Hold the
Block fell to 30 at the end of its first fight and stayed there; the Story held 60. On top of that both versions have
cold-start shader (PSO) hitches of 110 to 250 ms on the first screens (H3) and a train of 33 ms frames in the first
fight (H4). Away from those moments the play is clean: 60 frames a second, game thread 2.2 ms, render thread 5 to 6 ms, the GPU 8 to 9 ms at render scale 0.75 under `l12` and 12 to 13 ms at 0.50 under `l20`, and no garbage
collection over 4.4 ms in eleven minutes (H7).

**What the owner most likely met.** Not one-second averages hiding freezes: the probe's `worstMs` is the longest frame
of each second (`MICloud.cpp`, `ProbeWorst = Max(ProbeWorst, DeltaTime)`), so the 21.1 ms worst frame of our own E3DS
sample (DECISIONS.md, 13:23) was real for those 130 seconds. That sample was short, a first room or a 24-second holdout
without a gun switch. A longer session meets three things that sample could not: the crash after a gun switch (H1: a
frozen picture, then a dead stream), the governor's one-way drop (H2: 45 or 30 frames a second until the next menu,
which Hold the Block never shows), and the first-fight stutter (H4). E3DS's own logs show what a shared card does to
this game (H8): 17 to 27 frames a second with frames of 40 to 77 ms every second and single freezes of 0.36 to
1.88 s. That matches both halves of the owner's report, a low frame rate and freezes. The owner's own session log would settle which of these it was: with
"Show the Unreal log in the browser console" on and `-MICloudProbe=1` set, the owner's browser console held the probe
lines of that session.

### How it was measured

| What | Value |
|---|---|
| Packages | **Version 4**: `/project/ue/cloud/v3a-fix/out/MurderInc.zip` (sha256 `5d7f9238...`, the file uploaded at 11:36; game `6c4d810`, launcher `2322f3c`). **Newest**: `/project/ue/cloud/v6trial.zip` (game `fd8ce12`, the guns trial; no newer package exists). Both unzipped as `e3dsfresh`, then copied to the box's local disk (`/tmp/smooth-hitch/v4`, `/tmp/smooth-hitch/v6t`) after the CPU lane's C6 (the 9p volume makes freezes of its own). Debug symbols of both builds copied beside the binaries so a crash prints its stack (`/project/ue/cloud/symbols/<commit>/*.sym`) |
| E3DS-class limits | `lag-test.sh` with `load=1:0.05:0.05:1024` (the gate's `e3ds-l12`), **`cpus=0-7`**, `-sm5`, 1920 x 1080, `runas=fresh clean=1` (a new user with an empty home and a fresh `Saved` every run: no driver shader cache, as on a new E3DS machine), `-MICloudProbe=1`, the Development game of the same package (same code, CSV profiler). The gate's `l20` load (`1:0.05:0:1024`), and one run with no load |
| How close | **CPU: exact in kind.** E3DS's machine logs `CPUs: 8 cores, 8 with hyper-threads, 7 task workers (more than 6: the RHI has its interrupt and submission threads)` (its game log in the box's browser console, `/project/ue/cloud/e3ds-session-1/firefox-console-s5.log`); `cpus=0-7` here gives the same 7 workers and the same RHI threads (the box shows no hyper-threads). The box's cores are faster. **GPU: `l20` reproduces E3DS's card, `l12` is lighter.** In the Story's play `l20` reads 11.6 to 13.0 ms (30-s medians) at render scale 0.50 (`v6-story-l20`, `v4-story-l20`: 11.8 ms, 52 of 56 play seconds at 0.50); E3DS read 10.2 to 13.3 ms at 0.50 to 0.63 in the same Story room and 10.6 to 13.2 at 0.50 to 0.75 in Hold the Block (DECISIONS.md, 11:36 and 13:23). `l12` reads 7.8 to 8.8 ms at 0.75: an upper bound. **Disk: local**, as an E3DS session's unpacked copy is likely to be (not known) |
| Player | The Development game's demo director (it aims, fights, walks routes, switches guns): `sm-story.txt` (Home, Crew, four guns in the Loadout, a sight fitted on the Workbench, Block & Style, Briefing, then the whole Story run of `tools/box/demo/demo.txt` to the truck, with switches to all four guns and reloads), `sm-hold.txt` (Hold the Block, seven fights, switches, reloads, a propane blast, about 4 minutes), `sm-long.txt` (Hold the Block, planned as 15 minutes: 26 fights, 26 switches, 26 reloads, 5 blasts; waves 1 to 5, up to 15 enemies; the director got through it in 11.4 minutes of play). God mode on (the runs must last; no rule changes). Plus the Shipping launcher's path with the Development game and the stream viewer pressing keys and clicking through every set-up screen and all four guns (`guns-keys.txt`, `-csvCaptureFrames=7800`) |
| Per-frame data | CSV profile of every frame from the first second (`csvprofile start` in the script, or `-csvCaptureFrames`): FrameTime, game / render / RHI thread, GPU, the engine's `PSO/GraphicsPSOHitch`, `PSO/ComputePSOHitch`, `PSO/PSOMisses`, `FlushAsyncLoading` and `GC` events, exclusive timers. Read with `smooth_csv.py` (every frame over 25 ms with what the threads did and the events within 0.6 s) and `pso_frames.py` (the frames where a PSO was created at draw time, a GC or a synchronous load ran) |
| Runs | `/project/ue/smooth/hitch/runs/<name>` on the box (each with `game.log`, the CSV, `summary.txt`, `others.log`), scripts in `/project/ue/smooth/hitch/scripts`, the queue runner `gated.sh` (holds the GPU claim, a placeholder named `MurderInc`, between its runs). Two runs were thrown away: the first `v4-story` started while seven `clang++` compiles and an editor had the box's CPUs (game thread 160 to 2,200 ms a frame, 2 to 20 fps: the box, not the game), and in `v4-story-paused` the viewer of version 4's scripted game got one video frame and left, which paused the game at 44 s (version 4's dev game is therefore run without a viewer, `viewer=0`) |

![Every frame of four sessions under E3DS-class limits](shots/smooth-hitch-frames.jpg)

Black: each frame's time; blue: its GPU time; clipped at 120 ms, longer frames named in red. The panel titles' counts are
from times rounded down to 0.1 ms; the tables below use the exact values. In the third and fourth panels the GPU time falls
back (at 480 s and at 158 s) while the frame time stays at 22.2 and 33.3 ms: H2.

### Per-frame numbers

Every frame of the CSV profiles (not one-second averages). "Cold" lines include the game's first second and the first
set-up screen; the Story and Hold lines start with the title screen. E3DS-class load `l12` unless the line says otherwise.

| Run | Version | Session | Frames, length | fps | 1 % low | Worst frame | Frames over 25 / 100 ms a minute |
|---|---|---|---|---|---|---|---|
| `v4-story2` | 4 | front end + whole Story run to the truck, 4 guns | 6,371, 106.8 s | 59.66 | 38.4 | 169.6 ms (title) | 5.6 / 1.1 |
| `v6-story` | v6 trial | the same script | 5,819, 97.4 s | 59.74 | 42.1 | 192.0 ms (title) | 3.7 / 1.2 |
| `v4-hold` | 4 | Hold the Block | **crashed at 70 s** (H1) | 59.8 (probe, play) | | 45 ms (probe) | |
| `v4-long` | 4 | Hold the Block, 15 minutes planned | **crashed at 128 s** (H1) | 59.8 (probe, play) | | 77.5 ms (probe) | |
| `v6-hold` | v6 trial | Hold the Block, 3.6 minutes | 12,697, 214.2 s | 59.27 | **28.2** | 198.0 ms (title) | **31.7** / 0.6 |
| `v6-long` | v6 trial | Hold the Block, 11.4 minutes of play | 36,233, 684.6 s | **52.92** (60 for 6 min, then **45 to the end**) | 35.6 | 211.7 ms (title) | 7.1 / 0.5 |
| `v4-menus` | 4 | the Shipping path through the stream, all set-up screens by keys and mouse, 4 guns drawn, aimed, fired, reloaded | 7,800, 136.8 s (from the process start) | 57.0 | 9.1 | 4,283 ms (engine start, nobody connected) | 24.1 / 3.1 |
| `v6-menus` | v6 trial | the same | 7,800, 137.5 s | 56.7 | 8.3 | 5,194 ms (engine start, nobody connected) | 24.9 / 2.2 |
| `v4-story-l20` | 4 | the Story script, load **l20 (E3DS's GPU time)** | 6,197, 103.8 s | 59.70 (60 in every play second, render scale 0.50) | 40.1 | 194.4 ms (title) | 3.5 / 1.7 |
| `v6-story-l20` | v6 trial | the same, l20 | 6,395, 107.2 s | 59.64 (60 in every play second, render scale 0.50) | 37.5 | 221.1 ms (title) | 5.6 / 1.7 |
| `v6-hold-l20` | v6 trial | Hold the Block, load **l20 (E3DS's GPU time)** | 7,047, 191.0 s | **36.90** (60 for 42 s, then **30 to the end**, H2) | 25.5 | 190.4 ms (title) | 1,367.6 (the 33.3 ms frames of the 30 lock) / 0.6 |
| `v6-hold-l15` | v6 trial | Hold the Block, load `1:0.05:0.02:1024` (GPU 9.1 ms at 0.75: close to l12, not between) | probe lines, 215 s of play | 59.9 (lowest second 52.1), target 60 in all 219 play seconds | | 170 ms (probe) | |
| `v6-hold-free` | v6 trial | Hold the Block, no load | 10,497, 215.1 s | 48.79 (60 for 50 s, then 45 to the end: another lane's game took the card from 23:33:06 to 23:35:11, H2) | 35.6 | 188.2 ms (title) | 3.9 / 0.8 |

The two menu runs shared the box's CPUs with other lanes' compiles in 109 and 130 of their 133 samples (the summary
lines say so); their set-up-screen frames over 25 ms are an upper bound. Every other line ran with no compiler beside
it in most samples and no other game on the GPU, except `v6-long` (H2, H8).

**Every frame over 100 ms, and what it was** (CSV times from the capture's start):

| Run | Time | Frame | What the frame was |
|---|---|---|---|
| `v4-story2` | 0.93 s | 169.6 ms | the title's first drawn frames: 7 graphics and 17 compute PSOs created at draw time in the frame before (H3) |
| | 6.11 s | 160.5 ms | Crew, first draw (`MIMenu fe gearup`): 3 synchronous loads, then 4 graphics + 6 compute PSOs created at draw time, render thread 118.5 ms in the frame before (H3) |
| `v6-story` | 1.02 s | 192.0 ms | the title (7 graphics PSOs, 263 ms of compile; 17 compute, 738 ms; spread over threads) |
| | 6.08 s | 129.4 ms | Crew, first draw (16.1 ms of `FlushAsyncLoading`, 4 graphics + 6 compute PSOs, 212 + 521 ms of compile) |
| `v6-hold` | 0.98 s | 198.0 ms | the title, PSOs as above |
| | 49.73 s | 155.9 ms | wave 2, Goons spawning: every thread idle (game 2.3, render 5.5 ms, GPU 8.7 ms); the pacer waited 153 ms for the GPU (H5) |
| `v6-long` | 1.03 s | 211.7 ms | the title |
| | 136.8, 323.1, 353.0, 506.9, 663.7 s | 151.7, 148.2, 131.3, 145.2, 126.8 ms | all threads idle, GPU 7 to 10 ms, the pacer's wait (H5) |
| `v4-story-l20` | 40.03 s | 116.3 ms | in play, all threads idle, GPU 14.4 ms (H5) |
| `v6-story-l20` | 101.09 s | 137.9 ms | after the run's end, all threads idle (H5) |
| `v6-hold-free` | 1.02, 1.39 s | 188.2, 172.9 ms | the title |
| | 180.92 s | 146.3 ms | all threads idle, GPU 4.2 ms, **no load process and no other game on the card** (H5) |
| `v4-menus` | 0 to 5.8 s | 4,283, 1,381, 124 ms | engine start and the first frames, before any viewer (1,641 ms of graphics and 6,302 ms of compute PSO compiles in the second frame) |
| | 7.27, 9.02 s | 252.4, 204.1 ms | the home screen's first frames (7 graphics + 23 compute PSOs), the viewer joining |
| | 15.61 s | 116.5 ms | Crew (H3), with "WaitForGPU: Timed out waiting for fence" from Pixel Streaming's capture at that moment (`game.log` 22:55:15.296) |
| | 96.16 s | 157.9 ms | the viewer leaving (the game pauses): not play |
| `v6-menus` | 0 to 5.2 s, 7.97 s | 5,194, 1,351, 213 ms | engine start; the home screen |
| | 17.30 s | 152.7 ms | Crew (16 ms of loads, 12 PSO misses) |
| | 119.28 s | 164.9 ms | the viewer leaving |

Frames of 25 to 100 ms besides those: the PSO misses of the first fight (H4), the front end's rebuilds (H6, game
thread `UI` 11 to 16 ms, frames 28 to 34 ms, about one every 2 s on the Loadout and the Workbench), the intro's first frame
(`MIMenu fe hit`: 50 and 60 ms, 6 graphics PSOs), and in the holdout a few render- or RHI-thread frames of 30 to 55 ms
with PSO misses. Gun switches cost 8 to 18 ms of synchronous loading (`FlushAsyncLoading`, up to 35 loads in one
frame) but never made a frame over 25 ms from the local disk (CPU lane C2 has them from the network volume).

### Findings

| # | Severity | Finding | Evidence | Fix (proposed, not made) |
|---|---|---|---|---|
| H1 | **blocker** | **Version 4 crashes in Hold the Block after a gun switch.** SIGSEGV reading address 0 in the first-person pack gun's animation (`AnimationContext: SkeletalMeshComponent='FirstPersonPackGun' SkeletalMesh='SK_TFA_AR_Short_Combined' AnimInstance='MIFPAnimInstance_...'`), symbolised: `FMIFPAnimProxy::Evaluate` at `MIFirstPersonAnim.cpp:23`, from a parallel animation task. It is the CPU lane's C1 and the switch lane's crash (PLAY.md), here on the owner's version under E3DS-class limits: a player who switches guns and plays on for a minute or two loses the session (the picture freezes, then the stream ends) | `v4-hold`: switch to the NINE at 47 s, CSV `GC` event at frame 3,522, crash in the same second (`game.log` 22:49:23.954), 70 s into the process. `v4-long`: switch at 78 s, GC at 121 s, crash at 121.3 s (23:17:47.384), 128 s into the process: 2 of 2. The v6 trial did not crash in this lane's 4 sessions (`v6-story`, `v6-hold`, `v6-menus`, `v6-long`: 11 collections and 26 switches in the last), against 3 of 3 in the CPU lane: the freed clips are read, and whether the memory is still mapped decides | Fixed in the branch (`68ce52c`, `HeldClips`; test `SwitchSurvivesGC`), in no package yet. Prove it on the release package with `sm-long.txt` (11 minutes, 26 switches) and the CPU lane's script, both past several collections |
| H2 | **blocker** | **The frame-rate target only falls during play; it rises only on a card or a set-up screen** (`FMIFrameRateGovernor`, `MIPacing.h`: "Up, only at a safe moment ... not in live play"). One second in which the GPU cannot keep up at the smallest picture drops 60 to 45 (and 45 to 30) for the rest of the run, however fast the GPU is afterwards. Hold the Block never shows a set-up screen, so a run that drops stays down for its whole length; in the Story a player gets it back only by pausing. 45 frames a second on a 60 Hz display is also uneven (every third frame is shown twice): a judder on top of the low rate | `v6-long`: 60 for 6 min 13 s, then `Frame-rate target: 60 -> 45 ... the GPU took 20.6 ms a frame` (23:06:36.477) when another game appeared on the card for two minutes (`others.log` 23:06:23 to 23:08:26, card memory 5.9 to 12.0 GB). From 480 s the GPU was back at 6.9 to 9.4 ms at render scale 0.75 (probe lines), the target stayed 45 for the last 5.2 minutes: 52.9 fps for the session. `v6-hold-l20` (the load that gives E3DS's GPU time): 60 held through the first fight, then 60 -> 45 -> 30 two seconds after it (42 s into the play, 23:20:56 and 23:20:57), then **30 for 146 of 189 play seconds** at a GPU median of 19.1 ms (most seconds would have fitted a 45 target: 22.2 ms); after 150 s the GPU was down to 12.9 to 13.5 ms (30-s medians) and the frames stayed at 33.3 ms (chart, fourth panel). `v6-hold-free` (no load) repeated `v6-long` by accident: another lane's game on the card for two minutes, 60 -> 45 at 23:33:21, and after it left the GPU read 4.6 to 5.6 ms while the target stayed 45 to the end. Under l12 the holdout's own heaviest frame reached 24.4 ms of GPU (`v6-hold` CSV) without a full second over the line; with E3DS's GPU time (l20) the first fight's end is where it drops. **This is the most likely "low frame rate" of the owner's report** | Let the target rise during play with the same rule as on the menus (GPU at the smallest picture under four fifths of the next rate's frame time for `RaiseAfter` seconds, the doubling back-off kept), or at least between holdout waves and on the pause card. It changes pacing only, no gameplay rule. Prove with `v6-long` and `v6-hold-l20` again: the target back at 60 within a minute of the load going |
| H3 | **must-fix** | **Cold-start PSO hitches on the first screens**: the title's first frames 170 to 212 ms, the home screen through the stream 204 to 252 ms, the Crew screen's first draw 108 to 160 ms, the intro's first frame 50 to 60 ms. The engine's own counters show graphics and compute pipeline states created at draw time in exactly those frames (`PSO/GraphicsPSOHitch`, `PSO/ComputePSOHitch`): 4 to 9 graphics and 6 to 23 compute PSOs each, 200 to 1,000 ms of compile work spread over the worker threads. **No pipeline cache is packaged** ("Vulkan PSO Precaching = 1, PipelineFileCache = 0" in the game log; `Config/` has no `r.ShaderPipelineCache` setting), and every E3DS session starts on a machine with no driver cache. The 3a gate measured the same Crew frame at 0.82 to 0.92 s with its packages on the network volume (PROGRESS.md, "What a cold machine adds"); from local disk it is 110 to 160 ms | `pso_frames.py` on every CSV above (for example `v6-story`: frame 60, 7 graphics + 17 compute PSO hitches, then the 192 ms frame; frame 347, 4 + 6, then 129.4 ms). E3DS's own first frames of version 4 (browser console, sessions 3 and 4): 413 and 187 ms in the game's second second | Bundle a recorded pipeline cache (record with `-logPSO` through the front end, the Story and Hold the Block on SM5, cook it in with `r.ShaderPipelineCache.Enabled=1`), and/or precache the global compute shaders (5.9's PSO precaching covers materials, not the global and Lumen compute passes); draw the Crew stage once behind the CLICK TO PLAY card. Prove: `pso_frames.py` lists no PSO hitch after the title, the Crew frame under 50 ms on a cold user |
| H4 | **must-fix** | **The first fight stutters**: in the first 30 s of fighting in Hold the Block, **88 frames over 25 ms**, nearly all 33.3 ms (one display refresh lost each), almost every one with 1 to 8 PSO misses (draws waiting for a pipeline state that the precacher had not built: the Goons, the Buzzards, muzzle flashes, tracers, impacts, the first blast). 1 % low 28 fps for the run. After about 60 s of play it is gone | `v6-hold` per 30 s: 0 to 30 s 56.4 fps and 88 frames over 25 ms, 30 to 60 s 16, then 0 to 7. PSO misses in the runs: 1,687 (`v6-story`), 1,166 (`v4-story-paused`), 4,579 in 2,011 frames (`v6-long`) | The same cache as H3, recorded through fights; or warm the enemy and effect materials before play (spawn one of each, hidden, during the intro), which costs no rule |
| H5 | should-fix (or the box's) | **Single frames of 126 to 156 ms with every thread idle**, about one every two minutes in the holdout: game thread 2 to 3 ms, render 5 to 8 ms, the frame's GPU time 7 to 10 ms, and the pacer's wait 149 to 153 ms (`worst wait` in the summary lines). Something held the GPU for 150 ms that is not the game's own frame | `v6-hold` 49.73 s; `v6-long` 136.8, 323.1, 353.0, 506.9, 663.7 s | Not the outside load process: `v6-hold-free` had one (180.92 s, GPU 4.2 ms) with no load process and no other game on the card for 14 s before it. Could still be the box (a sandboxed kernel). Look at what waits on the GPU in those frames (Pixel Streaming's capture fence, an occlusion read-back) with a trace from local disk |
| H6 | should-fix | **The set-up screens' rebuilds cost a frame each**: game-thread `UI` 11 to 16 ms in frames of 28 to 34 ms, about one every two seconds on the Loadout and the Workbench (v6 trial; 14 frames over 25 ms in 30 s of set-up) | `v6-menus` 20 to 48 s (`GT: UI 16.3, 12.7, 11.6, 12.4, 13.4, 12.5`), `v4-menus` the same pattern at 11 to 12 ms | READY.md M1 and CPU lane C5: the rebuild in the paint pass. Their fix removes this too |
| H7 | nit | **Memory and garbage collection over 15 minutes are not a problem**: 11 collections in `v6-long`, none in a frame over 22.2 ms (the 45-fps frame); resident memory 3,239 MB a minute in, 3,402 to 3,509 MB from minute 8 (+200 to 270 MB, flat after that); texture streaming at 780 to 795 MB all session against its 600 MB pool (READY.md's "over budget": a sharpness question, not a hitch) | `v6-long` probe lines (`rssMB`, `texStreamMB`), `pso_frames.py` (GC frames) | None needed for smoothness |
| H8 | (evidence) | **What a shared card does, on E3DS itself**: the box's browser kept E3DS's game log of five sessions on 2026-11-25 (`/project/ue/cloud/e3ds-session-1/firefox-console-s5.log`). With version 3's game left on the card from an earlier session, the home screen ran at **26 to 27 fps with 40 to 45 ms frames every second** (GPU 33 to 41 ms at render scale 0.50), single frames of **660 ms**, then a session at **17 fps with frames of 55 to 77 ms and freezes of 357 ms and 1,881 ms**. On a clean card version 4 played at **60.0 fps, worst frame 19.3 to 20.3 ms** (199 and 102 play seconds). `v6-long` reproduced the shared card by accident on the box: the other game's two minutes cost 49.8 and 44.9 fps and frames of 55 to 82 ms, and H2 kept the cost after it left | probe lines split by the `[MICloud] Build` start line of each session | Version 4's launcher stops leftover games of the package; nothing stops another process on the card, and H2 makes any such episode last |

**Steady-state frame rate under E3DS-class limits** (the v6 trial). Under `l12`: 60.0 in every second of the Story's play
and in the holdout after the first minute, until H2 drops it; medians a frame: GPU 7.8 to 8.8 ms (render scale 0.75, which
dynamic resolution never had to lower), render thread 5.0 to 6.2 ms, RHI 2.4 to 3.2 ms, game thread 2.1 to 2.4 ms; the
heaviest holdout frame 24.4 ms of GPU. Under `l20` (E3DS's GPU time): the Story held 60 in every play second at render scale
0.50 (GPU 11.6 to 13.0 ms, 4 ms in hand), while Hold the Block's fights needed 19 to 23 ms of GPU at any render scale
(dynamic resolution 0.50 to 0.75 changes little, BOX.md row 43): it falls below 60 in fights, and H2 then keeps it at 30.
With H2 fixed the holdout would drop to 45 or 30 in a fight and come back to 60 between waves; to hold 60 through the fights
on the A4000, the quality ladder (release 3c, off by default) or cheaper fight effects would have to take 3 to 6 ms off the
GPU. A per-pass GPU breakdown was not taken here.

**Version 4 against the v6 trial** (criterion 4 of DECISIONS.md 21:00): same script, same limits. Story: 59.66 against
59.74 fps, 1 % low 38.4 against 42.1, frames over 25 ms 5.6 against 3.7 a minute, over 100 ms 1.1 against 1.2 a minute
(the cold-start frames, H3, in both); with E3DS's GPU time (`l20`) 59.70 against 59.64, both at 60 in every play second.
Hold the Block: version 4 crashed twice before 130 s; the v6 trial ran 3.6 and 11.4
minutes without a crash but with the first-fight stutter (H4) and the 45 lock (H2). So the v6 trial is not yet better
than version 4 on the per-frame numbers that matter, and nothing in it removes H2 to H4.

### Not done, not proven

- The release package (the branch with the crash fix, the hands, the 3c review fixes) was not measured: no package of it
  exists. Every line above should be run again on it (`/project/ue/smooth/hitch/queue*.txt` are the lines).
- No Unreal Insights trace from this lane (the CPU lane has one, from the network volume); "top stacks" here are the CSV's
  exclusive timers and the engine's PSO and loading counters, and the crash's symbolised stack.
- Pixel Streaming's encoder under the long session was not separated from the game (the summary lines carry the sender's
  numbers: `v6-long` encoded 52.3 a second with a lowest second of 0, which is the other game's two minutes).
- The owner's own session log: not available. A copy of that session's browser console (or a new session with the
  console open) would show `gpuMs` with `viewers=0` on the home screen (a shared card reads 30 ms or more) and any
  `Frame-rate target` and `Signal 11` lines.
- No game code was changed (this phase).

### Files (on the box, not in the repository)

`/project/ue/smooth/hitch/`: `scripts/` (`sm-story.txt`, `sm-hold.txt`, `sm-long.txt`, `smooth_csv.py`, `pso_frames.py`,
`dump_ft.py`, `plot_box.py`), `queue*.txt`, `gated.sh` (the queue runner with the GPU claim), `runs/<name>/` for every run
named above, the unzipped packages in `v4/`, `v6t/` and their local copies in `/tmp/smooth-hitch/` (lost when the box stops).
The lane's copy of `lag-test.sh` (`/project/ue/smooth/hitch/repo/tools/box/cloud/`) differs from the branch in two lines:
a run without a viewer keeps its CSV profile, and a `-nullrhi` game or this lane's own claim does not count as a game.

## Gameplay, menu and weapon bug hunt (lane `bugs`, 2026-11-25 22:35 to 2026-11-26 00:40 UTC)

**Verdict of this lane: not smooth yet.** The game's rules hold up. Every mode, death, Run it back, Restart, results card,
debrief, Back to title and new start played in both packages without a stuck state, a refused command or an error line.
On E3DS-faithful limits the newest package also played the same life cycle with no frame over 50 ms: front end, run start,
gun switches, pause, Settings, death, Run it back by a real key, a second run. Three things a player meets in normal play
are wrong:

- **B1, blocker in version 4:** version 4 crashes after a gun switch. This is the switch lane's crash. It reproduces here
  with no GPU at all, so any machine can check a package for it.
- **B2, must-fix:** every Hold the Block wave ends with 50 to 165 s of waiting for the last Buzzards. To a player the wave
  looks stuck.
- **B3, should-fix:** each press on the Graphics quality row freezes the picture for one frame of 62 to 377 ms.

B4 to B8 are smaller. Nothing in this lane explains a sustained low frame rate. Ultra graphics costs no more GPU time than
Auto on E3DS-class limits (B3), and the game thread's 99th percentile is 3.6 ms.

![Pause card, death card and results card of version 4 (top); pause card, the run after Run it back and Back to title of the newest package (bottom)](shots/smooth-bugs-cards.jpg)

### How it was played

| What | Value |
|---|---|
| Packages | **Version 4**: the zip of `6c4d810` (`/project/ue/cloud/v3a-fix/out/MurderInc.zip`, PLAY.md). **The newest**: `v6trial.zip` (`fd8ce12`). Both were unpacked privately to the box's local disk (`/tmp/smooth-bugs/v4`, `/tmp/smooth-bugs/v6t`), as C6 asks. The Development game of each package was used; its rules and flow code is the Shipping game's |
| Same code at the head? | Between `6c4d810` and `fd8ce12`, `Flow/`, `Player/`, `UI/` and `Weapons/MIWeaponRules.cpp` differ by 47 lines (`git diff --stat`). From `fd8ce12` to the head, `Flow/` and `MIWeaponRules.cpp` are unchanged. `UI/` and `MIPlayerController.cpp` carry the set-up screen fixes of `d072184` (READY.md M1 to M10). So every rules or flow finding below holds for version 4 and for the head; the Head column says so finding by finding |
| Logic runs (no GPU) | The Development game with `-nullrhi`, on CPUs 14 and 15 at `nice 19`, `t.MaxFPS 60` (`/project/ue/smooth/bugs/nr.sh`). The demo director plays a script: **n1** is the life cycle in the next row, **n2** plays Story twice to the debrief, **n3** is 12 minutes of Hold the Block. The probe line comes every 0.5 s (`state`, `fire`, `mag`). The director logs every flow event, reload phase, switch phase and kill. Rules and animation run as with a GPU: version 4's crash reproduced this way (B1). There are no pictures, and these runs need no GPU claim |
| What n1 plays (both packages) | The front end as a first-time player: Home, Gear up, Crew, Loadout, Block & Style (Story, Kingpin), Briefing, Hit the block. A reload while sprinting. A switch in the middle of a reload, and back. Aiming while switching, firing aimed on the new gun, switching back aimed. The pause key with the trigger held at full auto, then resume. Pause, Settings (look speed and field of view changed), back, resume. A walk to the avenue aimed and firing, until death. Run it back, death again, Back to title. Hold the Block from the front end, death, the results card, Run it back, Restart from the pause card, and a quit in the middle of the run |
| GPU runs | `lag-test.sh` (this lane's copy, `/project/ue/smooth/bugs/repo`) with `game=dev`, `load=1:0.05:0:1024`, `cpus=0-5`, `-sm5`, 1920 x 1080, a viewer through Pixel Streaming and a CSV profile. That load is the render lane's E3DS-faithful `l20`. **g1** is n1's script with 19 `MIShot` pictures; the death card is answered with a real `Enter` key event and the pause opened with a real `P`. **g2** steps Graphics quality from Auto through Low, Medium and High to Ultra during a run, fights on Ultra, then steps back to Auto. The runs held the GPU claim (`gq.sh`, queue `q/q1.txt`), one game at a time |
| How close to E3DS | `g1-v6t`, first 84 s: **GPU 11.1 to 13.7 ms at render scale 0.50, 60 frames a second**. Version 4 on E3DS's A4000 read 10.2 to 13.3 ms at 0.50 to 0.63 (DECISIONS.md, 2026-11-25). From t 84 s of `g1-v6t` another job took the card: video memory rose from 7.9 GB to 12 to 13 GB, `others=1` showed in 7 watcher samples, the GPU went to 20 to 27 ms and the target to 30. Only the first 84 s are used. `g1-v4` shared the box throughout: every CPU was 97 to 98 % busy with another lane's build, and the target stayed at 30. Its pictures and logic are used, its frame times are not. `g2-v4` and `g2-v6t` were clean (`others=0` in all 140 and 135 samples) |
| Instrument | An `MIShot` holds its frame for 200 to 340 ms while the viewport is read back (B8). Each such frame and the two after it are left out of the per-frame numbers (57 frames a run); the CSV's `Cmd: MIShot` events mark them |

**Per-frame numbers, the newest package, E3DS-faithful load** (`g1-v6t`, 0 to 84 s, CSV, `MIShot` frames left out): 4,596
frames, **58.3 fps, 7 frames over 25 ms, none over 50 ms, worst 46.3 ms, 1 % low 40.9 fps, game thread p99 3.6 ms.** This window
covers the front end, Hit the block, the reload while sprinting, four gun switches, two pauses, Settings, the walk, the
first death, the death card, Run it back by the `Enter` key and the second run.

### Findings

| # | Severity | Bug | Steps to reproduce | Evidence | Head |
|---|---|---|---|---|---|
| B1 | **blocker** (version 4) | **Version 4 crashes after a gun switch.** The crash is a SIGSEGV, a null read, at the next periodic garbage collection after the CHOPPER (the pack gun) is put away. This is the switch lane's crash (PLAY.md), found here a third way: with no GPU and no stream, so any machine can check a package for it in three minutes | Hold the Block or Story: press 2 (the NINE) and keep the NINE for a minute | `n3-v4`: `switch chopper -> Nine draw` at t 134.2 s, then `Signal 11 caught ... SIGSEGV: invalid attempt to read memory at address 0x0` at 22:57:01 (t about 183 s, the first collection after the switch), exit code 139. `n3-v6t` ran the same script with the trial's hand-IK CHOPPER, played on to t 715 s and exited 0. `n1-v4` did not crash: it switched back to the CHOPPER within 4 s each time | Fixed in the branch (`1f560d7` and the `HeldClips` commit, PLAY.md) and proven by `SwitchSurvivesGC`. Not yet in a package. **Gate for the v6 package:** `nr.sh <package> scripts/n3.txt` (no GPU) must exit 0 after 10 minutes of switches |
| B2 | must-fix (the owner decides: a timing rule) | **Every Hold the Block wave ends with 50 to 165 s of waiting for the last Buzzards.** The Goons are all dead 23 to 43 s into a wave. Then the player stands in an empty street while one to three drones circle out of reach. The wave goes on until they are shot, or until the game's own rule brings them down after 60 s without a hit. Waves 1 to 5 lasted 94, 98, 193, 120 and 151 s; the wait is 54 to 85 % of each. A player reads it as a stuck wave | Hold the Block on any difficulty: kill every Goon, then watch the wave banner and the tally | `n3-v6t`, summed up by `waves.py`: the seconds after the wave's start at which a Goon (g) or Buzzard (b) fell. Wave 1: `15g 16g 19g 23g 34b 53b 94b`. Wave 2: `16b 19g 21g 23g 26g 27g 41b 53b 98b`. Wave 3: `11g 17g 21g 21g 24g 26g 29g 42b 49b 133b AUTO 193b`. Wave 4: last Goon at 43 s, cleared at 120 s. Wave 5: last Goon at 41 s, `AUTO`, cleared at 151 s. `AUTO` is the log line `Hold: 1 Buzzard(s) unhurt for 60 s as the wave's last enemies: brought down, the wave counts as cleared`. `n3-v4`: wave 1's last Goon at 24 s, `AUTO`, cleared at 102 s. The shooter is the demo director (`auto 1 1`): it fires at whatever it can see from the start. A player who walks may find the drones sooner, but cannot make them come down | Same rules at the head: `UMIGameSubsystem::UpdateLastEnemies` (`MIGameSubsystem.cpp`, `const double Limit = 60.0`, waves with only Buzzards left). The 60 s rule exists only in the Unreal game and is off in tests and replays (`Boots.bPersist`). So it can change without touching the golden runs, for example to 15 s counted from the last Goon's death. It is still a timing rule, so it needs the owner's word under the release criteria |
| B3 | should-fix | **Each press on Settings, Graphics quality freezes the picture for one frame of 62 to 377 ms**, in the stream as on the box. **Ultra costs no more than Auto**: on the E3DS-faithful load both draw at render scale 0.50 with 11.9 to 14.7 ms of GPU time (single samples of 16.7 to 20.9 ms in both). So the setting brings a hitch and no visible gain on E3DS | Pause, Settings, Graphics quality, Right four times (Auto to Ultra), back, play; then Left four times | `g2-v4`, the frame after each `Cmd: MIMenu right` (CSV rows 760, 769, 788, 803): **377.3, 214.9, 276.6 and 70.9 ms**, with the render thread at 23 to 42 ms in those frames. `g2-v6t`: 74.7, 72.1, 75.9 and 73.7 ms going up; 71.2, 71.9, 62.3 and **167.8 ms** (render thread 125.5 ms) going back to Auto. The game logs `Graphics quality: 0` through `3 (scalability groups only; ...)`, one line a press. Probe `gpuMs`, `dr=0.50` and `target=60` throughout | Same at the head (`UMICloudSubsystem::ApplyStreamedQuality` on every `UMIGameSubsystem::MenuAdjust`). Fix idea: apply the level once, when Settings closes. Or hide the row in a stream, where the cloud profile and dynamic resolution already decide the picture |
| B4 | should-fix | **A run cannot be left for the menus.** The pause card offers Resume, Restart run, Difficulty and Settings. Only death or the debrief lead to Back to title or Change set-up. A first-time player who wants another gun, mode or crew has to get killed first | Start any run and press P or Esc | Picture (both pause cards). `MIMenus.cpp`, `EMIMenuScreen::Pause`: `resume`, `restart`, `difficulty`, `settings`. That is the web game's card (`src/menus.js`, `paused()`), but the web game has no set-up screens to go back to | Same at the head. Add `changesetup` and `totitle` to the pause card: `UMIGameSubsystem::MenuConfirm` already handles both ids, which the death card uses |
| B5 | must-fix, **not proven in a browser** | **The stream does not pause when the player leaves the page.** The web game pauses on `blur` and `visibilitychange` (`src/game.js` 923-928) and drops held keys when focus or the pointer lock goes (`src/input.js` 1196-1206). The Unreal game pauses only when the viewer's connection ends (`UMICloudSubsystem::ReleaseForLeave`, from `OnAllViewersLeft`). It has no handler for Pixel Streaming's `MouseLeave`. Its own cards tell the player "Esc gives the mouse back to the browser" (the click card, and the pause card's last line in the picture). So a player who presses Esc or switches tabs leaves the run going behind the page and is shot while away. A key held at that moment may stay down if the page sends no key-up | Through E3DS: start a run, press Esc (or Alt+Tab) for 10 s, come back | Code and the cards' text, as cited. The box cannot run a browser viewer (BOX.md row 27), and no E3DS session was spent | Same at the head. To check in one E3DS session from the box's browser (`owner-browser.sh`): press Esc in a run; the pause card must show. Fix idea: pause on `MouseLeave` and on a message the page sends on `blur` |
| B6 | should-fix | **Nothing a player chooses survives an E3DS visit.** Look speed, field of view, volume, quality, the four guns, the Workbench builds and the Hold the Block best all live in the save slot. E3DS starts a fresh machine for every session (PROGRESS.md, "What a cold machine adds"; C2). The box keeps its saves, so READY.md's "the choice survives" holds there and not on E3DS | Set up guns, play, close the page, open the link again | Every run here starts with `Saved/SaveGames` deleted, as on a fresh E3DS machine (`nr.sh`, `lag-test.sh`). Every first screen then shows the defaults (picture: Back to title shows CHOPPER / NINE and Story, the defaults) | Same at the head. The page bridge of `docs/unreal/maps/progression.md` is the place to keep these |
| B7 | nit | The set-up line in the log spells names as Unreal first met them: `"guns":["chopper","Nine"]`, `"level":"bLock"`, `"time":"Day"` | Any run from the front end | `n1-v6t` log: `Set-up: {"crew":"Rule","guns":["chopper","Nine"],...,"level":"bLock",...,"time":"Day"}` | Harmless today: an `FName` compares without case. The progression's page bridge will carry these strings, so write them lower-case |
| B8 | nit (instrument) | `MIShot` holds its frame for 200 to 340 ms, so a CSV or probe line from a run that takes pictures shows those frames as freezes | Any demo script with `MIShot` | All 11 frames over 100 ms in `g1-v6t` are `Cmd: MIShot` frames. In `g1-v4`, 19 of 20 are. The 20th, 112.2 ms (row 3499) in Hold the Block wave 1, came while every CPU of the box was busy | Not the game. Lanes that read frame times from picture runs should leave those frames out, as done above |

### Checked and right (both packages unless named)

- **Weapons in play** (`n1`: probe `mag`, the director's reload and switch lines):
  - A reload while sprinting runs to the end (`start`, `magout`, `magin` 22 to 30, `bolt`, `done` with `sprint 1` held).
  - A switch in the middle of a reload cancels it (`reload chopper cancel`, then `switch chopper -> Nine holster`) and
    keeps the magazine's count: 24 before, 24 after switching back.
  - Aiming survives a switch both ways, and the NINE fires aimed (15 to 14).
  - With the trigger held, the pause fires nothing (`mag` 20 through the pause). Firing goes on after resume, since the
    button is still held (20 to 15).
  - Pictures `05` to `07`: the right gun in the hands after each switch, aimed after an aimed switch.
- **Pause and Settings.** P opens the pause card from a real key event (picture `08` of both packages). Look speed and field
  of view change and apply at once (`09`, `10`: 1.05x and 76 degrees). Back returns to the pause card; Back again resumes.
- **Death and Run it back.** The death card comes 1.5 s after death (`menus:card dead`), with the run's time, reels and
  kills. A real `Enter` key event starts the run again (picture `13`: a full magazine, health 100). Run it back resets the
  reels, the explosives and the enemies (`explosives:reset`, `player:reset`, seven `enemy:spawn`). Aiming does not carry
  into the next run (`14`). Two deaths, then Back to title, give the Home screen with the set-up kept (`16`).
- **Hold the Block.** The results card shows waves cleared, kills, score and best (picture: 1, 8, 1,565, "New best"). Run it
  back and Restart from the pause card both restart wave 1 (`holdout:wave 1 7`).
- **Story to the end, twice** (`n2`). Three reels and the truck reach `game:state complete` and the debrief. Run it again
  resets everything, and the second run reaches the debrief too (t 68 and 133 s in v6t). Then Back to title and a new run.
- **Quit in the middle of a run.** The game exits with code 0 (`n1`, `n2`, `g1`, `g2`: `[MurderInc.sh] the game quit normally`).
- **Transitions on E3DS-faithful limits** (`g1-v6t`, first 84 s, above): no frame over 50 ms at the run's start, a switch,
  a pause, Settings, the death, the death card or Run it back.
- **Logs.** No `Error` or `Ensure` line in any logic run apart from B1's crash. The only warnings come from the box
  (`/proc/meminfo`, netlink), the first start's missing save, and a console-lookup note for `MIMenu`.

### What this lane says about the owner's session

- **Stutter or freezes:** B1 ends a version 4 session about a minute after any switch off the CHOPPER: the picture freezes,
  then the stream is lost. A player who touches Graphics quality gets a third of a second of freeze per press (B3).
- **Bugs in gameplay:** Hold the Block's long empty waits (B2) and a run that cannot be left (B4). If the owner pressed Esc
  or left the tab, the run went on without them (B5, unproven).
- **Low frame rate:** nothing in this lane. With the card to itself, the newest package held 58.3 fps through the whole
  life cycle at E3DS's GPU time. When another job shared the card, the game's target fell to 45 and then 30, as the pacer
  is built to do (`g1-v6t` from t 84 s). A busy E3DS machine would look the same: that is the render and stream lanes'
  ground.

### Not done, not proven

- B5 in a real browser: there is no browser viewer on the box, and no E3DS session was spent.
- The simulated pad on the death, results and pause cards in a stream. The menu lane's pad run covers the set-up screens,
  and `SwitchEveryWay` covers the pad in play. Under `-nullrhi` the game takes no key events (runs `t1` and `t2`: keys were
  "handled" but changed nothing), so the logic runs used the director's commands.
- A long Story session on a clean GPU with frame times: `g1-v4`'s frame times are not usable (above).
- The head itself: no package of it exists yet. The rules and flow findings were read in its code (the Head column).

### Files (on the box, not in the repository)

`/project/ue/smooth/bugs/` holds:

- `nr.sh` (the logic runs) and `scripts/` (`n1`, `n2`, `n3`, `g1`, `g2`).
- `runs/`: the logic runs (`game.log`, `result.txt`).
- `lag/`: the GPU runs (CSV, `game.log`, `others.log`, `seg.txt`).
- `ev.py`, `waves.py`, `seg.py` (per-segment frame numbers from a demo run's CSV) and `sheet.py`.
- `gq.sh`: this lane's GPU queue and claim.

The pictures are in `/tmp/smooth-bugs/shots/` (`g1-v4`, `g1-v6t`, `g2-v4`, `g2-v6t`), on the local disk, so they are lost
when the box stops.

## Bug fixes (lane `bug`, the fixer of the bug findings, 2026-11-26 00:35 to 03:00 UTC)

**Verdict of this lane: the crash is gone from a package of the branch** (the v6 trial crashed at 120.7 s in the CPU
lane's script without a GPU; this lane's package ran the same script with and without the GPU, an 11-minute and a
12-minute Hold the Block session with 13 and 4 switches, every one to its end); **B4 and B5 are fixed in the game, B5's
page half, B2 and B6 are not fixed** (the page, the owner's word, the next release's page bridge). Every claim below comes from a run on the box named in the tables (per-frame CSV
lines, probe lines every 0.25 to 1 s, the director's event log, the engine's crash handler).

| # | Finding | Status | Commit |
|---|---|---|---|
| H1, C1, B1 | The SIGSEGV at the garbage collection after a gun switch | **fixed** (the branch's `HeldClips`, now in a package and proven past many collections) | in the branch before this lane (`HeldClips`, test `SwitchSurvivesGC`) |
| B5 | The stream does not pause when the player leaves the page | **fixed in the game**; the page's half is for the lead (below) | `63d4862` |
| B4 | A run cannot be left for the menus | **fixed** | `3ac39ee` |
| B2 | Hold the Block waves end with long waits for the last Buzzards | **not fixed**: a timing rule, the owner's word (below) | |
| B6 | Settings, guns, builds and the best score lost on every E3DS session | **not fixed**: needs the page bridge of the next release (below) | |

### The package these proofs ran on

No package of the branch existed (the release engineer packages only at the GO of DECISIONS.md 20:40), so this lane made
its own with the branch's own `package-cloud.sh` steps, in its own folders (`/project/ue/smooth/bug/pkg/pkg.sh`: the
release copy `/project/ue/smooth/bug/rel-smoothbug`, the cloud folder `/project/ue/smooth/bug/cloud`; nothing of the
release engineer's was read or written but the shared art input). Source: the branch at `ab55e0d` plus this lane's two
fixes (the C++ of `63d4862` and `3ac39ee`); the copied `Source/` is identical file for file to that tree
(`diff -r` against a worktree of `ab55e0d` with the patch applied), `Config/` differs only by the section the editor writes
for its Android file server plugin (`bIncludeInShipping=False`). Every step passed: editor build, the round-4 weapons
import (guns, rattler, parts, sockets ok), overlay, usage (20 materials, 6 cube maps), Development and Shipping cooks,
289 of 289 Sound Waves and 35 of 35 weapon assets in both pak lists, zip `MurderInc-bug.zip` (2.3 GB, sha256
`94c8719c...`). It is a proof package, never to be uploaded: it lacks the commits pushed after `ab55e0d` by other lanes.
Unpacked on the box's local disk (`/tmp/smooth-bug/fix`, CPU lane C6). The "before" runs used the v6 trial (`fd8ce12`,
unpacked privately to `/tmp/smooth-bug/v6t`), whose code has the crash; version 4's crash is the earlier lanes' runs.

### H1 / C1 / B1: the crash after a gun switch

**Before and after on the same script, with no GPU** (`nr.sh`: the Development game, `-nullrhi`, two CPUs, the demo
director playing the CPU lane's whole `full-csv.txt`: home, every set-up screen, the Workbench, a Story run with shots,
reloads, switches to guns 2, 3, 4 and back to 1, then the fight):

| Run | Package | Switches (the director's `switch ... draw` events) | End |
|---|---|---|---|
| `cpu-nr-v6t` | v6 trial `fd8ce12` | CHOPPER to NINE 89.7 s, NINE to STICK 98.3 s, STICK to STRETCH 103.4 s, STRETCH to CHOPPER 108.3 s | **`Signal 11 caught ... SIGSEGV: invalid attempt to read memory at address 0x0` at t 120.7 s, exit code 139**; crash context `SkeletalMeshComponent='FirstPersonPackGun' SkeletalMesh='SK_TFA_AR_Default_Combined' AnimInstance='MIFPAnimInstance_...'` (the CPU lane's C1, here without a GPU) |
| `cpu-nr-fix` | this lane's package | the same four at 89.7, 98.3, 103.4 and 108.4 s | no signal; the script played to its end (t 208 s, into the fight on the avenue that C1 never let any earlier run reach), the process was stopped by the run's own time limit |
| `long-nr-fix` (the hitch lane's `sm-long.txt`: Hold the Block, 26 fights) | this lane's package | 13 switches between the CHOPPER and the NINE, from 77.7 s to 822.0 s | **exit code 0**, the director's `quit` at t 829 s after eight waves; no `Signal 11` line |
| `n3-fix` (the bugs lane's 12-minute Hold the Block gate, `scripts/n3.txt`) | this lane's package | CHOPPER to NINE at 134.2 s (version 4 crashed about 49 s after this switch, `n3-v4`), and back and forth every 120 s to 614.4 s | **exit code 0** at t 858 s after seven waves, the director's own `quit`; no `Signal 11` line |

The periodic collection runs every 61.1 s (CPU lane C8), so `n3-fix` and `long-nr-fix` each passed about 13 collections
after their first switch and `cpu-nr-fix` about two, the point where every earlier session died.

**With the GPU, under E3DS-class limits** (this lane's copy of `lag-test.sh`, the GPU claim held, local disk): the CPU
lane's line (`sb-cpu-full`) and the hitch lane's 11-minute holdout (`sb-long`) on this lane's package ran once the perf
lane's GPU queue had ended (02:17 UTC).

| Run | Package | What happened | Per-frame (every CSV frame) |
|---|---|---|---|
| `cpu-full-csv-local` (CPU lane) | v6 trial | switches at 89.4, 98.0, 103.1, 108.2 s; CSV `GC` at 60.8 s; **SIGSEGV at about 122 s**, at the second periodic collection | 0 to 119 s: 59.8 fps, frames over 25 / 50 / 100 ms a minute 8.6 / 0 / 0, worst 48.4 ms, 1 % low 47.6 fps |
| `sb-cpu-full` (the same line: `load=1:0.05:0.05:1024 cpus=0-5 -sm5`, viewer, `probe=1`; CLEAN) | this lane's package | the same four switches (`Cmd: MIInput weapon2` ... `weapon1` at 89.4, 98.0, 103.1, 108.2 s); CSV `GC` at 60.8, **121.9** and 183.0 s; no signal; alive at the 330 s limit, then `EXIT 0` on TERM | 0 to 121 s: 59.9 fps, 3.5 / 0.5 / 0 a minute, worst 92.7 ms, 1 % low 50.9 fps; 121 to 198 s (where no earlier run got): 59.9 fps, 0.8 / 0.8 / 0.8 a minute, worst 139.1 ms, 1 % low 50.8 fps. Play (the summary line): 60.0 fps, lowest second 59.3, GPU 8.1 ms (max 11.2) at render scale 0.75 |

The two long frames are not the crash's and not this lane's fixes: 92.7 ms at 34.8 s is a set-up screen's synchronous
loads (`FlushAsyncLoading` x2 in that frame, game thread 8.5 ms: the CPU lane's C2, which the perf lane's preload, pushed
after this package's commit, addresses), 139.1 ms at 182.5 s has every thread idle (game 2.3, render 2.8, RHI 2.7, GPU
7.3 ms: the hitch lane's H5).

`sb-long` (the hitch lane's `v6-long` / `v4-long` line: `sm-long.txt`, `l12`, `cpus=0-7`, a fresh user and a clean
`Saved`) on this lane's package: **ended by itself, exit code 0, after 838 s**, 818 s of play, eight waves, 13 switches
between the CHOPPER and the NINE (78.2 s to 823.8 s), about 12 periodic collections after the first switch, no
`Signal 11` line. Version 4 crashed in this script at 128 s (`v4-long`). The probe lines (one a second, not per frame:
this run's CSV was not kept, the fresh-user copy of the build took it with it) read 59.3 fps in play, lowest second 44.9,
worst frame 172 ms, GPU 8.5 ms (max 28.4), resident memory 3,114 MB five seconds in and 3,519 MB at the end, and the
frame-rate target 60 -> 45 at 02:42:33, two minutes before the end, where it stayed: the hitch lane's H2, the other fixer's
ground. The watcher counted `others=1` from 02:32:17 to 02:42:25: another lane's GPU-claim placeholder (a `sleep` named
`MurderInc`, `weaponsfix-claim`), not a game: the card's memory stayed at 5.5 to 5.6 GB, one game and the load.

### B5: a run pauses when the player stops looking

**What E3DS's player does** (its live script `e3dsCore.min_ns_dark.js`, fetched on the box 2026-11-26 00:39 UTC and read,
not kept): its mouse controller listens for `mouseenter` and `mouseleave` on the video's parent in every mouse mode and
sends Pixel Streaming's `MouseEnter` / `MouseLeave` (and releases the mouse buttons); its locked-mouse controller, when the
pointer lock ends (Esc, another window), only stops sending mouse moves and sends a `KeyUp` for every held key; it tells
the page around it `streamFocusLost` / `streamFocusGained` when `document.hasFocus()` changes; and a page command
`{cmd: 'sendToUe4', value: ...}` (also `sendDataToUE`, `sendMessageToStreamingBuild`) reaches the game as
`emitUIInteraction(value)`, Pixel Streaming's `UIInteraction` message. So after Esc nothing reaches the game until the
pointer leaves the picture, and a tab switch reaches it only through the page.

**The fix** (`63d4862`, `Cloud/MICloud.cpp`, `GuardViewerInput`): the plugin's `MouseLeave` and `UIInteraction`
handlers are wrapped (each still runs first, with the message as it came). A `MouseLeave` from the viewer who has the
input, or a `UIInteraction` descriptor `{"murderinc": "away"}`, calls `UMICloudSubsystem::PauseForAway`: a run in play or
in its intro pauses and everything the viewer held is let go (`ReleaseForLeave`, the same as when the connection ends);
on a menu, a card or a run already paused nothing changes. The `MouseLeave` Pixel Streaming sends itself when a
connection closes has no sender and is ignored (the connection's own end pauses already). A probe line now ends
`away=<signals> awayPaused=<runs paused>`, and the log says `Viewer away (<why>): the run is paused ...`. No rule of play
changes: the pause is the pause key's. Tests: `MurderInc.Cloud.ViewerAway` (the pause in the intro and in play, the held
W and mouse button let go and not acting after Resume, nothing on the pause card or the title, and the page's word read
from bytes laid out as Pixel Streaming hands them over: the word, other words, other keys, a plain string, a message cut
short, an empty one). `rtcinput.py` gained the verbs `leave`, `enter` and `ui <text>`.

**Through the stream, before and after** (the Development game's director starts a Story run; the viewer `away-view.txt`
sends a `MouseLeave` in play, presses P, sends the page's word in play, presses P, sends another word, pauses with P and
sends a `MouseLeave` on the pause card, presses P; no load, 8 CPUs, the GPU claim held; probe every 0.25 s; times are
the viewer's own seconds, the game's state from the probe lines: 2 play, 3 paused):

| Viewer's step | `sb-away-v6t` (v6 trial) | `sb-away-fix` (this lane's package) |
|---|---|---|
| `leave` in play (48.4 s) | nothing: `state=2` for the next 5 s | **paused at once**: `Viewer away (the pointer left the picture): the run is paused ...` (02:21:30.357), `state=3`, `away=1 awayPaused=1` |
| P (53.4 s) | pauses (the key) | resumes (`state=2`) |
| `ui {"murderinc": "away"}` in play (59.5 s) | (the old game was still paused by the P before, since its `leave` had paused nothing: this step says nothing there) | **paused at once**: `Viewer away (the page says the player is away)` (02:21:41.448), `away=2 awayPaused=2` |
| P (64.5 s) | resumes | resumes |
| `ui {"murderinc": "back"}` (70.6 s) | nothing | nothing (`away=2`: not the word) |
| P (75.6 s), then `leave` on the pause card (78.7 s) | paused; nothing more | paused by the key; the leave is counted and changes nothing (`away=3 awayPaused=2`) |
| P (82.7 s) | resumes | resumes |
| the viewer goes (the run's end) | paused by the connection's end | the same |

Both runs played at 59.8 and 59.9 frames a second (the summary lines): the wrapped handlers cost nothing a frame can show.
A third run, the page's word alone in play on the v6 trial (`sb-away-v6t-ui`), was stopped unplayed: `lag-test.sh` waited
for a free GPU behind another lane's claim placeholder, which was itself waiting for this lane's claim. The v6 trial has no
handler for the word in its code (the plugin's own `UIInteraction` handler only passes it to `UPixelStreaming2Input`
components, of which the game has none), so the after-run is the evidence that matters.

### B4: the pause card can leave the run

**The fix** (`3ac39ee`, `Flow/MIGameSubsystem.cpp`, `PatchCards`): the pause card gains **Change set-up** and **Back to
title** after its own four rows, with the death card's words (`frontend.cards.changeSetup`, `cards.toTitle`), also when
it is built again after Settings (`MenuBack`). `MenuConfirm` already ended a run for both ids, as the death card's rows
do. `src/menus.js` is untouched: the web game has no set-up screens to go back to. Test `MurderInc.Run.PauseCardLeave`
(the rows' order, the rows after Settings and after a difficulty change, Back to title to Home, a new run, Change set-up
to the Briefing).

**In the packages, before and after** (no GPU, `scripts/b4.txt`: a Story run, the pause key, `MIMenu changesetup`, Hit the
block again, the pause key, `MIMenu totitle`; the console command selects the row and confirms it only if the card has
it):

| Run | Package | `MIMenu changesetup` on the pause card (t 20.4 s) | `MIMenu totitle` on the pause card (t 33.8 s) |
|---|---|---|---|
| `b4-v6t` | v6 trial | nothing: no event, the run stays paused (probe `state=3`) | nothing: no event, still paused |
| `b4-fix` | this lane's package | `game:state title` in the same frame; the front end's next answer is `screen briefing` | `game:state title` in the same frame; the next set-up command answers `screen crew` from Home |

(The director's front-end commands act even behind a paused run, which is how `b4-v6t` went on at all; a player has no
such path.)

### B2: the long waits at the end of Hold the Block waves (not fixed: the owner decides)

Seen again on this lane's package (`n3-fix`): the waves began at 15.0, 101.8, 148.9, 224.4, 358.6, 532.9 and 715.7 s, so
waves 1 to 6 lasted 86.8, 47.1, 75.5, 134.2, 174.3 and 182.8 s, and three of them (4, 5, 6) ended only by the rule
`Hold: N Buzzard(s) unhurt for 60 s as the wave's last enemies: brought down`. It is a timing rule: under the release
criteria it changes only on the owner's word (below).

### B6: choices lost on every E3DS session (not fixed: the page bridge)

Nothing in the game can keep them: every E3DS session is a new machine. The keeper is the page bridge of
`docs/unreal/maps/progression.md` 4.4 (the next release). That plan's open question, "the exact E3DS iframe command that
forwards a page message to the game" (its line 521), is answered by the read above: `sendToUe4` (or `sendDataToUE`,
`sendMessageToStreamingBuild`) arrives in the game as a `UIInteraction` descriptor, the path B5's word uses and tests.
The other direction was seen in the same script only as far as the player (`HandleResponseFromUnreal` and its response
listeners); whether the player passes a game's response up to the page was not read.

### For the lead

1. **B5, the page's half** (PREFLIGHT.md section 3's prompt for the website and `docs/CURSOR_HANDOFF.md`, section 6 "Focus,
   keys, controllers and full screen"): add this item, so that a tab switch or a click on the page pauses the run, as the
   web game does:
   > - While the stream is playing, tell the game when the player looks away: on `streamFocusLost`, and when the tab becomes
   >   hidden (`visibilitychange` with `document.visibilityState === 'hidden'`), send
   >   `frame.contentWindow.postMessage(JSON.stringify({cmd: 'sendToUe4', value: {murderinc: 'away'}}), '*')` before anything
   >   else you do for that moment. The game pauses the run; the player resumes it with P or the pause card. Send nothing when
   >   the player comes back.
2. **B2, the owner's question** (a timing rule; DECISIONS.md 20:40, nothing waived): "In Hold the Block, when only drones
   are left and nobody has hit them, the game brings them down after 60 seconds. Shorten it to 15 seconds?" On a yes, the
   change is one number in `UMIGameSubsystem::UpdateLastEnemies` (`Flow/MIGameSubsystem.cpp`, `const double Limit = 60.0;`
   to `15.0`); the rule is off in tests and replays (`Boots.bPersist`), so the golden runs are untouched; re-run `n3` with
   `nr.sh` and read the wave lengths.
3. **The release package** must be gated on the crash as `cpu-nr-fix` and `n3-fix` were: `nr.sh <unpacked package>
   scripts/full-csv.txt <name> 330` and `nr.sh <unpacked package> scripts/n3.txt <name> 900` (no GPU, about 6 and 15
   minutes, CPUs of their own), each without a `Signal 11` line; the v6 trial fails the first in two minutes.
4. **Two lanes' GPU queues can wait for each other for ever**: a queue runner holds its claim (a `sleep` named `MurderInc`)
   between its runs, and `lag-test.sh`'s own wait for a free GPU counts any other lane's claim as a game. Here this
   lane's last run waited behind `weaponsfix-claim`, whose queue waited for this lane's claim (stopped by hand at 02:49).
   The watcher's count already skips the run's own claim; the wait before a run should skip every claim placeholder
   (a command line with `-claim` and no `-PixelStreamingID=` of a running game), or the runners should take one shared
   lock file instead of a process name.

### Suite

`tools/box/test.sh MurderInc` in this lane's clone (`/project/ue/smooth/bug/repo-smoothbug`, the guns imported with
`import-chars.sh r4 all` from `/project/ue/fp-in-guns` as the guns lane does, the Sound Waves re-imported, built with
`-MaxParallelActions=6`): **218 passed, 0 failed, 0 skipped** at `ab55e0d` plus the two fixes, **219 passed, 0 failed, 0
skipped** at `04c66c8` plus the two fixes (the commits as pushed) and **219 passed, 0 failed, 0 skipped** at the merge
`1119352`, the golden replays included (`Golden.*`, `Loadout.ParityGolden`, all Success). The three warnings are not this
lane's: `Audio.EngineRender` (no audio device under `-NoSound`), `Audio.VoiceData` (placeholder voice takes),
`Frontend.StageFloor` (a pack magazine mesh absent from the clone).

### Files (on the box, not in the repository)

`/project/ue/smooth/bug/`: `repo-smoothbug` (the clone), `pkg/` (`pkg.sh`, the private copy of `package-cloud.sh`),
`cloud/` (the package's build folders, zip, symbols), `nr.sh`, `nr2.sh` (`NR_CPUS=`), `gq.sh` and `q1.txt` (the GPU queue
and its claim), `lagtools/` (a copy of `tools/box` whose `lag-test.sh` does not count a `-nullrhi` game or this lane's
claim as another game, and whose `rtcinput.py` has the new verbs), `scripts/` (`b4.txt`, `away-demo.txt`,
`away-view.txt`, and copies of `full-csv.txt`, `n3.txt`, `sm-long.txt`), `runs/` (the no-GPU runs), `lag/` (the GPU runs),
`logs/`. The unpacked packages are in `/tmp/smooth-bug/` (lost when the box stops).

## Perf fixes (lane `perf`, 2026-11-26, 00:35 to 02:30 UTC)

**Verdict of this lane: the blocker is fixed and proven; two must-fix items are not closed.** The frame-rate target now
comes back in live play (H2): with the hitch lane's own load and script, a minute of a shared card left the old game at
30 frames a second for the rest of the run (60 of 60 play seconds after the load at 30), the fixed game was back at 60
28 s after the load ended (59 of the last 86 play seconds at 60, the rest on the way up). The same change also undoes a
drop this lane had not looked for: in two of this lane's four cold holdout runs the first seconds of play (render thread
25 to 40 ms, GPU 12 ms) held the game back for a second and dropped the target to 45; the old rule keeps such a 45 to
the end of the run, the new one had 60 back 10 s later. Graphics quality presses no longer freeze the picture (B3), the
data's assets are loaded in the background before a set-up screen asks for them (C2), the HUD has named trace scopes
(C4), and `lag-test.sh` says when a run comes from the box's network volume (C6). The cold-start pipeline-state hitches
(H3) and the first fight's stutter (H4) are **not** fixed: they need a recorded pipeline cache in the package, which is
the release engineer's packaging script (For the lead, below); the first-fight train did not come back in this lane's
cold runs, and limiting the precompile pool made things worse. The set-up screens' frame per key press (H6) is **not**
fixed either: READY.md's M1 moved the rebuild from the paint into the tick (measured), it costs the same frame. H5's single 126 to 156 ms frames are Pixel Streaming 2's
capture waiting 100 ms for its fence; one capture setting was measured against it (below). No gameplay rule changed: the
golden replays pass unchanged, and every change is pacing, loading, the moment a setting is written, or a trace name.

### How it was measured

| What | Value |
|---|---|
| Packages | The newest package on the box, `v6trial.zip` (game `fd8ce12`), unpacked to the box's local disk (`/tmp/smooth-perf/v6t-before`, copied from the hitch lane's local copy; C6 says why not from `/project`). **After** copies are the same folder with only the Development game binary replaced: `v6t-after` is `fd8ce12` plus this lane's pacing change (`MIPacing.*`, the cvar line of `MICloud.cpp`) and the Settings change (`MIGameSubsystem.*`), applied with `git apply -3` in a worktree of `fd8ce12` (`/project/ue/smooth/perf/fd8`, patches `p1-game.patch`, `p2-game.patch`) and built as `MurderInc Linux Development`; `v6t-c2` adds the preload (`Core/MIPreload.*`). Same cooked content, same Shipping binary, same launcher in all of them, so a before / after pair differs only in the code named |
| E3DS emulation | The hitch lane's conventions: `lag-test.sh` (this lane's copy, `/project/ue/smooth/perf/tools/box/cloud`), `cpus=0-7` (7 task workers and the RHI's interrupt and submission threads, as E3DS's game log reads), `load=1:0.05:0:1024` (`l20`, the load that reproduces E3DS's own GPU readings: here 12.5 to 13.2 ms at render scale 0.50 in the holdout's calm, E3DS 10.6 to 13.2 ms at 0.50 to 0.75) or `l12` where named, `-sm5`, 1920 x 1080, a viewer through Pixel Streaming, `runas=fresh clean=1` (a new user with no driver shader cache, a fresh `Saved`: E3DS's cold machine), `-MICloudProbe=1`. Every run had the card to itself (`others=0` in every watcher line). **Not** like E3DS: the box's CPUs were shared with other lanes' compiles in most runs (watcher `cpu=` median 51 to 79 %, p90 81 to 96 %; the two runs of a pair within 21 points of each other) |
| A shared card on purpose | `v6-long`'s stuck 45 came from another game on the card for two minutes, by accident. `spike=75:60:0.3:0` (this lane's copy of `lag-test.sh`) starts one more load process (`gpu_hog.py 0.3 0`, the `1:0.3:0` load: 33.8 ms a frame on the earlier box) 75 s after the run's load starts, for 60 s: in both runs 60 to 64 s into the play, while the holdout fights |
| Scripts | The hitch lane's `sm-hold.txt` (Hold the Block from the start, god mode, seven fights, switches, reloads, a blast, about 3.5 minutes), the bugs lane's `g2-v6t.txt` without its `MIShot` lines (`q2.txt`: pause, Settings, Graphics quality Auto to Ultra by four presses, play, Ultra back to Auto by four presses), the CPU lane's `full-csv.txt` (20 s of home screen, every set-up screen, four guns focused and slotted, the Workbench, a Story run with all four guns) |
| Per-frame data | Every frame of the CSV profile (`perf_sum.py`: fps, frames over 25 / 50 / 100 ms a minute, worst frame, 1 % low as `csvsum.py` defines it, per 30 s of play, and the game log's `Frame-rate target` lines; `b3frames.py`: the longest of the four frames after each menu press; `c2frames.py`: every frame with a `FlushAsyncLoading` event), all in `/project/ue/smooth/perf` |

### The findings, one by one

Each finding was checked again before anything changed. "Before" and "after" are the same package, script, load, CPUs and
cold user, run back to back.

| # | Finding | Checked | What was done | Before | After |
|---|---|---|---|---|---|
| H2 | **blocker**: the frame-rate target falls in play and rises only on a card, so Hold the Block keeps 45 or 30 to its end | **Right, reproduced on purpose.** `p-hs-before`: the extra load from 63 s of play drops 60, 45, 30 in two seconds (`at the smallest picture the game fell short ... the GPU took 26.8 ms`); the load ends at 123 s, the GPU is back at 12.9 ms (30-s medians), the target stays 30: **60 of the 60 play seconds after the load at 30, 30.0 fps**. Without the extra load (`p-hold-before`) the target held 60 all run: the drop needs a heavy second, as the hitch lane said | `FMIFrameRateGovernor` rises in live play too, with the rule it used on cards (GPU at the smallest picture under four fifths of the next rate's frame for 10 s, the doubling back-off when a rise does not hold for 30 s kept); a rise that held for 120 s gives the 10 s wait back; `MI.Cloud.FpsRiseInPlay 0` is the old rule. `MIPacing.h/.cpp`, `MICloud.cpp`, `DefaultGame.ini` (commit `de28380`), tests in `MurderInc.Cloud.FrameRate` (the holdout case, the shared-card case, the back-off and earn-back, the old rule) and `MurderInc.Cloud.QualityGuards` | `p-hs-before`: play 40.24 fps, last 60 s at 30.0 fps, 1 % low 18.4 | `p-hs-after`: the extra load from 64 s to 124 s drops 60, 45, 30 the same way; then `30 -> 45 ... for 10 s, in play` 10.8 s after the load ended and `45 -> 60` 28.2 s after it. **Play 47.61 fps, the last 60 s at 58.8 and 59.9 fps** (30-s buckets), 1 % low 24.3. Of the 86 play seconds after the load: 10 at 30, 17 at 45, 59 at 60 (probe lines) |
| H2 (second way in) | A **cold start** can drop the target too: in `p-hold-after` and `p-hs-after` the first seconds of play (render thread 25 to 40 ms a frame while the GPU took 12.4 to 13.7 ms) held the game back for a second and the target fell to 45. The drop rule is unchanged by this lane; the same can happen in the old build (it did not in this lane's two before runs) | Read in the probe lines: `held=33 waitMs=364`, `held=41 waitMs=434` in the two seconds before the drop, `gpuMs` 12.1 and 12.7 | The same change | (old rule: 45 kept to the end of the run, as in the hitch lane's `v6-long`) | `p-hold-after`: `45 -> 60 ... in play` 10.2 s after the drop; the run played **58.87 fps**, 1 % low 34.0, against **59.58 fps** in `p-hold-before` (no drop there); from 30 s of play to the end both runs held 59.4 to 60.0 fps in every 30-s bucket |
| B3 | should-fix: each Graphics quality press freezes the picture for 62 to 377 ms | **Right.** `p-q-before`, the longest of the 4 frames after each press: **359, 305, 339, 77 ms** going up, **88, 87, 51, 103 ms** going back (render thread 19 to 61 ms in them); the log writes `Graphics quality: 0, 1, 2, 3` and back, one line a press | In a stream the level waits while Settings is open and is written once when the card closes (`UMIGameSubsystem::ApplySettings`, `FlowFrame`; commit `4b621b7`). Not a rule: the card still shows the value at once, the picture changes when the card closes | 8 frames over 50 ms in the two Settings visits, worst 359.2 ms; capture 57.37 fps, 6.8 frames over 100 ms a minute | `p-q-after`: **no frame over 16.7 ms after any press or Back**; the log writes `Graphics quality: 3` once and `auto` once. Capture 59.03 fps, over 100 ms 2.2 a minute (the game's first second and one fight frame at 41 s); GPU medians 11.7 to 12.8 ms in each 15-s span (before 11.8 to 12.5) |
| C2 | should-fix: synchronous asset loads on the game thread (set-up screens, Briefing, gun switches) | **Right.** `p-c2-off` (the preload switched off): **53 synchronous loads in 8 frames**, game thread median 11.2 ms, worst 19.6 ms in those frames: Gear up 18.7 ms, gun focus 10.3 / 6.8 / 9.6 ms, the Briefing 11.2 ms, gun 2 11.4 ms, gun 3 (33 loads) 19.6 ms, the same as the CPU lane's run | `UMIPreloadSubsystem` (new, `Core/MIPreload.*`, commits `36da424`, `2fa5273`): once the title screen is up it loads every asset that `presentation.json`, `attachments.json`, `guns.json` and `crew.json` name, in the background, and keeps them; off with `MI.Preload 0` or `-MINoPreload`, and in tests; test `MurderInc.Preload.Paths` | `p-c2-off`: 20 to 118 s 59.6 fps, game thread p99 6.16 ms, 2.5 frames over 50 ms a minute, 1 % low 36.2; gun switches (88 to 104 s) game thread worst 19.6 ms | `p-c2-on`: `Preload: 114 of 114 assets ... in memory, 0.2 s after the title screen came up` (15 more named in the data are not in this package); **0 synchronous loads in 191 s**; 20 to 118 s 59.8 fps, game thread p99 3.80 ms, 0.6 frames over 50 ms a minute, 1 % low 47.5; gun switches game thread worst 7.1 ms. Resident memory at most 3,206 MB against 3,180 MB (+26 MB) |
| H3 | must-fix: cold-start pipeline-state (PSO) hitches of 110 to 250 ms on the title, home and Crew screens, no pipeline cache packaged | **Right.** The game log of every run: `Vulkan PSO Precaching = 1, PipelineFileCache = 0`; `LogPSOHitching: Encountered 150 PSO creation hitches so far (34 graphics, 116 compute). 0 of them were precached` in the first 7 s (`v6-hold`). The engine's precaching covers materials, not the global compute shaders (5.9's `r.ShaderPipelineCache.GlobalShadersOnlyWhenPSOPrecaching`: with precaching on, a bundled cache is what brings the global shaders) | **Not fixed here**: it needs a pipeline cache recorded from a package and cooked into the next one, which is the packaging script (For the lead, 1). The Crew screen's part that was loading (`FlushAsyncLoading` at Gear up, 18.7 ms) is gone with C2 | | |
| H4 | must-fix: the first fight stutters (a train of 33 ms frames, 1 to 8 PSO misses each) | **Right, but the cause is the cold start's background compile, not the misses.** `v6-hold` started the fight 3 s after the process: 21, 24, 42 frames over 25 ms in its first three 10-s spans with about 1,060 PSO misses each, then 14, 3, 0 as the misses ran out; only the first 10 s had blocking hitches (10), the rest had none. `v6-story` went through the front end first and began its run 35.3 s after the process (`game:state playing`): **0 frames over 25 ms from 10 s on**, with 736, 232, 169 and 265 misses in 10-s spans of its play. So the misses themselves do not make the long frames (the engine counts no blocking PSO creation in them: `GraphicsPSOHitch` 0); the 33 ms frames come while the boot's precompile pool (75 % of the CPUs by default, `r.pso.PrecompileThreadPoolPercentOfHardwareThreads`) still competes with the render and RHI threads, the first 30 to 40 s after the process starts (BOX.md row 62 saw the same pool at 70 to 90 % a thread). A player who goes through the front end mostly misses that window; the scripts that start a fight 3 s after the process do not. The Story's fight is lighter than the holdout's, so this is the likelier reading, not a proof | **Not fixed.** One cheap remedy measured and **rejected**: the pool limited to 3 threads (`-dpcvars=r.pso.PrecompileThreadPoolSizeMax=3`, logged as set). The fix is the bundled cache of H3 (For the lead, 1) | **The train did not come back today.** `p-h12-base` (the hitch lane's `v6-hold` line again, `l12`, cold): first 30 s of play 6 frames over 25 ms (the hitch lane's run: 88), 59.7 fps; misses 1,224, 1,168, 1,027 in the first three 10-s spans, then 20, 3, 7. With `l20`, cold, the first 30 s of play had 25, 37, 38 and 91 frames over 25 ms (`p-hold-before`, `p-hs-before`, `p-hold-after`, `p-hs-after`, the last with the cold drop of row 2): it varies run to run with the box's CPU load, not with the misses | `p-h12-pso3`: first 30 s 8 frames over 25 ms (no better); the misses no longer run out: 456 to 759 in every 10-s span to the end of the run (with the engine's default `r.PSOPrecache.ProxyCreationStrategy 1` a component whose PSOs are still compiling is not drawn yet, so a longer compile is a longer window of missing or late meshes). Kept at the default |
| H5 | should-fix: single 126 to 156 ms frames with every thread idle | **Explained.** 5 of the 7 frames over 120 ms in `v6-long`, `v6-hold` and `v6-hold-free` come in the same second as `UPixelCaptureMediaCapture::WaitForGPU: Timed out waiting for fence to be written!` (`v6-long` 23:02:40.8, 23:06:17.0, 23:11:27.7 against the frames logged at 23:02:41.2, 23:06:17.4, 23:11:28.4; `v6-hold` 22:50:26.7 against 155.9 ms at 22:50:26.8; `v6-hold-free` 23:35:24.9 against 146.3 ms). The engine's Pixel Capture polls its fence with `FRHIGPUFence::Poll` for up to 100 ms (`PixelCaptureCapturerMediaCapture.cpp:256-266`), the pattern the engine's own note warns against. The other two (`v6-long` 23:05:47 and 23:08:51) have no capture line: their cause is not known | **Not fixed.** The one switch the game can turn without changing the engine was measured and **rejected**: `-PixelStreamingUseMediaCapture=false` (Pixel Streaming's RHI capturer with its own fence) | `v6-long` (the hitch lane, default capturer, `sm-long.txt`, `l12`): play 681.6 s, **0.4 frames over 100 ms a minute**, 1.8 over 50 ms | `p-long-rhicap` (the same script and load, `v6t-after`, the RHI capturer): play 782.4 s at 59.50 fps (the target never moved), but **1.8 frames over 100 ms a minute** (worst 219.4 ms), 2.8 over 50 ms; the probe lines put them on the render thread (`renderMs=225.8`, `174.6` in seconds with a GPU of 8 ms). Four times as many freezes: the default stays |
| H6 / C5 | should-fix: each front-end rebuild costs a frame of 28 to 34 ms (11 to 16 ms of UI on the game thread) | **Right, and READY.md's M1 fix moved the cost, it did not remove it.** M1 (`7bc34df`) rebuilds the set-up screens on the game thread before Slate's frame instead of inside the paint: that ended the flicker (READY.md), and the menu fixer's binary of it (`fd8ce12` + M1, `/project/ue/ready/menufix/pkg-after4`) was measured here against the trial with the hitch lane's `v6-menus` line (`game=ship -MIDev`, the viewer's `guns-keys.txt`, `l12`), 20 to 48 s (Crew, Loadout, the Workbench). The frames over 25 ms are the ones after the viewer's key presses (one every 1 to 2.5 s in the script) | Nothing in this lane's code (the front end is the menu fixer's: For the lead, 8) | `p-menus-before`: 15 frames over 25 ms (27 to 42 ms, one 69 ms), in them the game thread's exclusive `UI` 8.9 ms on average; game thread p99 9.1 ms | `p-menus-m1`: **14 frames over 25 ms** (27 to 39 ms, one 70 ms), in them `UI` 2.0 ms and **`TickActors` 7.6 ms** on average (game thread 10 to 14 ms in those frames): the same rebuild, now in the tick. `UI` p99 6.9 to 1.5 ms. Not fixed |
| C4 | should-fix: HUD frames of 15 to 22 ms with nothing named inside | Not reproduced untraced (the CPU lane: the game thread never above 11.7 ms in play from local disk) | Named trace scopes in `AMIHUD::DrawHUD`, `DrawPlay`, `DrawHurt`, `DrawStepMarker`, `DrawFlow`, `DrawMenu`, `DrawWeaponBar`, `DrawWheel` and `UMIAudioSubsystem::DrawSubtitle` (commit `e618e90`). **No trace was taken with them** (the GPU time went to the runs above): the next traced run names the part | | |
| C6 | must-fix for the measurements: packages run from `/project` (9p) get 100 to 280 ms freezes | Right (the CPU lane's two runs); every run of this lane ran from `/tmp` | `lag-test.sh local=1` (or `LAG_LOCAL=1`) copies a build that sits on `/project` to `/tmp/lag-local` once and runs it there; a run from `/project` without it writes `volume=warning: ...` into its `info.txt` (commit `541ed6a`). Default behaviour unchanged. **Not exercised in a run here** (all of this lane's builds were on `/tmp` already) | | |

### For the lead

1. **A bundled pipeline cache for H3 and H4** (`tools/box/cloud/package-cloud.sh`, the release engineer's). The steps are
   Epic's recording workflow for bundled pipeline caches; the variables named were checked in 5.9's `ShaderPipelineCache.cpp`;
   **none of it was run in this lane**:
   - in `Config/DefaultGame.ini` `[/Script/UnrealEd.ProjectPackagingSettings]`: `bShareMaterialShaderCode=True` (the cook then
     writes the stable shader keys, `.shk`, under `Saved/Cooked/Linux/MurderInc/Metadata/PipelineCaches`);
   - record: run the packaged Development game with `-logPSO` on SM5 (`-sm5`, the E3DS path) through the front end, every
     set-up screen, a Story run and two Hold the Block waves, under `runas=fresh clean=1`; it writes
     `Saved/CollectedPSOs/*.rec.upipelinecache`;
   - expand: `UnrealEditor-Cmd MurderInc.uproject -run=ShaderPipelineCacheTools expand <recordings> <.shk files>
     MurderInc_SF_VULKAN_SM5.spc`, put the `.spc` in `unreal/MurderInc/Build/Linux/PipelineCaches/` and cook again;
   - in the game: `r.ShaderPipelineCache.Enabled=1` (with PSO precaching on, 5.9 then precompiles the global shaders from
     it, `r.ShaderPipelineCache.GlobalShadersOnlyWhenPSOPrecaching`), at start-up while the title waits for its viewer;
   - prove: `pso_frames.py` (the hitch lane's) on a cold `sm-story.txt` run lists no PSO creation hitch after the title, and a
     cold `sm-hold.txt` run (the fight 3 s after the process) has no train of 33 ms frames in its first 40 s.
2. **Draw the Crew stage once behind the CLICK TO PLAY card** (front end, `UI/MIShowroom.cpp` / `SMIFrontEnd.cpp`, the menu
   readiness fixer's): the Crew screen's first draw is a 108 to 160 ms frame of PSO creation (H3); C2's preload took its
   loads away, not its shaders. Spawning the stage and its arms hidden-but-rendered for one frame while the click card
   covers the picture moves that frame where nothing moves.
3. **`grips.json` is parsed on every equip** (`Weapons/MIFirstPersonRig.cpp`, the hands engineer's; the CPU lane's C2): keep
   the parsed `TSharedPtr<FJsonObject>` in a function-local static, filled on the first `Equip`, so a gun switch stops reading
   and parsing 62 KB. With C2's preload the switch's asset loads are already gone (`p-c2-on`: game thread worst 7.1 ms at
   the switches against 19.6 ms).
4. **Pixel Streaming's capture wait** (H5): keep `PixelStreaming2.UseMediaCapture` at its default (the other capturer had four
   times the frames over 100 ms, `p-long-rhicap`). What is left is in the engine's plugin: `UPixelCaptureMediaCapture::WaitForGPU`
   polls its fence for up to 100 ms (`Engine/Plugins/Media/PixelCapture/.../PixelCaptureCapturerMediaCapture.cpp:256-266`); a
   change there (flush to the RHI thread before polling, or a shorter wait) is an engine change and was not made. About one
   such frame every two to three minutes of play on the box; whether E3DS's machine has them is for its probe lines to say
   (`worstMs` over 100 with `gpuMs` under the frame).
5. **The release package**: run `p-hs-before` / `p-hs-after`'s line (`sm-hold.txt`, `l20`, `spike=75:60:0.3:0`) on it with
   this lane's copy of `lag-test.sh` (or add the `spike=` key to the branch's): the target must be back at 60 within
   30 s of the extra load's end. And `q2.txt` (Graphics quality presses): no frame over 50 ms after a press.
6. **Memory**: the preload keeps every gun, part and clip the data names in memory (at most 3,206 MB resident in `p-c2-on`
   against 3,180 MB in `p-c2-off`: +26 MB for the trial's 114 assets). `MI.Preload 0` in the cloud profile switches it off if E3DS's
   4 to 6 GB budget ever needs it.
7. **A side effect to know about**: in `p-c2-on` the trial's game did **not** crash after its gun switches (exit 0 at 191 s),
   where `p-c2-off`, the same binary with the preload off, crashed at the periodic collection after the switch to gun 1
   (`Signal 11 caught`, exit 139: C1 / H1). The preload keeps the old gun's clips referenced, so the collector cannot free
   what the anim instance still reads. One run each: not a proof, and not the fix (the fix is `HeldClips` in the branch).
8. **The set-up screens' rebuild still costs a frame per key press** (H6, `UI/SMIFrontEnd.cpp` / `MIFrontEnd.cpp`, the menu
   fixer's): after M1 the 8 to 12 ms are in `TickActors` instead of `UI` (`p-menus-m1`). A frame that has to fit a rebuild
   and the game in 16.7 ms misses and shows as 27 to 30 ms. Ways out that change no screen: rebuild only the column that
   changed (the focus moved within one list), or build the next screen's widgets in the frame after the key press and swap
   them in when built.

### The suite

The whole suite (`tools/box/test.sh MurderInc`, golden replays included) in this lane's clone
(`/project/ue/smooth/perf/repo-perf`: the branch, the twelve generated folders copied from `/project/ue/repo-guns` with the
guns imported, `audio-import.sh` run once), built with `-MaxParallelActions=6`:

| Commit | Result |
|---|---|
| `591ab43` (this lane's fixes merged with the branch at `04c66c8`) | `TESTS OK passed=218 failed=0 skipped=0`, 83 s |
| `cdd5be3` (merged with `6192b07`) | `TESTS OK passed=218 failed=0 skipped=0`, 77 s |
| `9032311` (merged with `1119352`: the bugs fixer's pause and focus changes in `MICloud.cpp` and `MIGameSubsystem.cpp`, merged without a conflict) | `TESTS OK passed=220 failed=0 skipped=0`, 78 s, 11 golden replays among them; pushed as `9248390` (the merge of two documentation commits on top) |

No test was skipped, weakened or re-recorded. One test line changed meaning because the rule changed:
`MurderInc.Cloud.FrameRate`'s "10 ms for a minute in live play: it does not rise in a fight" is now "it rises in play
after 10 s", and the old assertion is kept, word for word, under `bRiseInPlay = false`. In `MurderInc.Cloud.QualityGuards`
the case "the governor on its own drops to 45" runs with the old rule (with the new one the ladder's two steps bring 60
back, which a new case asserts).

### Files

`/project/ue/smooth/perf/` on the box: `runs/<name>/` for every run named above (`game.log`, the CSV profile,
`summary.txt`, `others.log`, `spike.log`), `q1.txt` (the queue), `gated.sh` (the queue runner and GPU claim, a copy of the
hitch lane's), `tools/box/cloud/lag-test.sh` (the hitch lane's copy plus `spike=` and this lane's claim name), `hscripts/`
(the scripts), `perf_sum.py`, `b3frames.py`, `c2frames.py`, `buckets.py`, `fd8/` (the worktree of `fd8ce12` with the
patches), `p1-game.patch`, `p2-game.patch`. The packages are in `/tmp/smooth-perf/` (local disk: lost when the box stops).

## Pipeline cache (lane `pso`, 2026-11-26, 16:20 to 19:00 UTC): H3, H4, H6

**Verdict of this lane: H4 is fixed and H3 is fixed on the title and home screens but not yet on the Crew screen, by a
bundled pipeline cache, measured on a package of the branch against the same package without it; H6 is not fixed
(measured again, cause narrowed).** H3's own proof line ("no PSO hitch after the title, the Crew frame under 50 ms on a
cold user") is met for the hitches in the Story run and not for the Crew frame: 79.8 ms there (no PSO in it), 84.7 ms
with one compute PSO on the Shipping path. Under the hitch lane's conditions (`l20`,
`cpus=0-7`, `-sm5`, a cold user, the package on the local disk, a viewer) the cache took every pipeline-state (PSO)
creation hitch out of the Story's title, home and Crew screens and out of the holdout's start and first minute of
fighting: the engine's own counters (`PSO/GraphicsPSOHitch`, `PSO/ComputePSOHitch`) read 0 in those runs, against 40 (Story) and
36 (holdout) without it. The title's 169 ms frame and the holdout's 180 ms first frames are gone (worst frames 22 ms and
17 ms). The Crew screen's first draw is better (116 to 80 ms) but still one long frame: what is left is a render-thread
stall with no PSO created in it (below). The price is paid before any viewer sees a frame: the game's first frame comes
about 3.5 s later (the cache's 405 PSOs are compiled while the engine starts). No gameplay rule changed: the game code
changed by one field of the probe line (`psoLeft`); the rest is configuration, the recorded cache and the box tools.

### What was wrong, from the engine's source (5.9, on the box)

- `VulkanRHI.cpp`: with PSO precaching on (`r.PSOPrecaching=1`, the default) Vulkan sets `GRHISupportsPipelineFileCache = 0`
  unless `r.Vulkan.EnablePSOFileCacheWhenPrecachingActive` is set (read only, default false). That is the "Vulkan PSO
  Precaching = 1, PipelineFileCache = 0" line every earlier lane quoted: no pipeline cache could be recorded or opened at
  all, whatever `r.ShaderPipelineCache.Enabled` said (it is already 1 in a packaged game: `PIPELINE_CACHE_DEFAULT_ENABLED`
  is `!WITH_EDITOR`).
- `ShaderLibraryCooking.cpp`: the cook writes the stable shader keys (`ShaderStableInfo-*.shk`) only with
  `[DevOptions.Shaders] NeedsShaderStableKeys=true`; without them a recording cannot be turned into a bundled cache
  (the prover's and the release copies' `Metadata/PipelineCaches` folders were empty). At the end of the cook it looks for
  `Build/Linux/PipelineCaches/*MurderInc_SF_VULKAN_SM5.spc` and builds `Content/PipelineCaches/Linux/MurderInc_SF_VULKAN_SM5.stable.upipelinecache`,
  which the stage puts in the pak (`CopyBuildToStagingDirectory.Automation.cs`).
- `PipelineFileCache.cpp`: a `-logPSO` run records only the PSOs the precacher did not have, unless
  `r.ShaderPipelineCache.IncludeAllPrecachedPSOs=1` (read only): the first recording of the whole Story held 117 PSOs.
  With it, and the bound-PSO save, a recording holds every PSO that was drawn (316 to 397 a run).
- `ShaderPipelineCache.cpp`: `r.ShaderPipelineCache.PSOPrecacheIncludeMode` (read only, default 2) compiles only the
  recorded PSOs the recording run had *not* precached in time; on a slower host the precacher is later, so this lane sets 0
  (compile every recorded PSO). `StartupMode` 1 (the default) compiles in the Fast mode from the start, on the PSO
  precaching thread pool (`UsePrecachingThreadPool` 1): that is the "precompile behind the CLICK TO PLAY card"; nothing
  in the game had to change for it.

### What changed

| Commit | Change |
|---|---|
| `7862e3e` | `Config/DefaultEngine.ini`: `[ConsoleVariables] r.Vulkan.EnablePSOFileCacheWhenPrecachingActive=1`, `r.ShaderPipelineCache.PSOPrecacheIncludeMode=0`; `[DevOptions.Shaders] NeedsShaderStableKeys=true`. The editor never opens a pipeline cache (it has no shader code library: `FShaderPipelineCache::Initialize` returns at once), so the editor and the suite are unchanged. `.gitignore` keeps `Build/Linux/PipelineCaches/`. The probe line ends with `psoLeft=` (`FShaderPipelineCache::NumPrecompilesRemaining()`: the cache's compile tasks still to run). `package-cloud.sh`: `MI_REL` / `MI_GP` (a lane's own release copy), the commit's `.spc` copied into the release copy, the cook's stable keys kept in `<cloud>/pso-keys`, and a `PSO CACHE` check after each package and before the zip (a commit with a `.spc` and a pak list without `MurderInc_SF_VULKAN_SM5.stable.upipelinecache` fails). `lag-test.sh` keeps a `-logPSO` run's recording |
| `9409cf9`, `e17401d` | `unreal/MurderInc/Build/Linux/PipelineCaches/MurderInc_SF_VULKAN_SM5.spc` (recordings A to C: 408 PSOs, 757 stable PSOs; the cook keeps 405: 192 graphics, 213 compute); `tools/box/cloud/pso-cache.sh` (record, expand, dump; its header has the whole procedure); `tools/box/cloud/pso/rec-a.txt` to `rec-c.txt`; `lag-test.sh` finds the CSV and the recording under a fresh user's home too |
| this commit | `pso/rec-d.txt` (recording D: the viewer-driven path; it added no PSO, so no `.spc` of its own), `pso-cache.sh` reads a script's `# view:` and `# secs:` lines; this section, BOX.md rows, READY.md's check, `docs/unreal/shots/pso-frames.jpg`, `pso-before-after-frames.jpg` |

### How it was recorded

The Development game of the package of `09d3343` (the branch with `7862e3e`, before any `.spc`), `lag-test.sh` with
`game=dev demo=<script> join=3 load=1:0.05:0:1024 cpus=0-7 runas=fresh clean=1 -- -sm5 -logPSO
-ini:Engine:[ConsoleVariables]:r.ShaderPipelineCache.IncludeAllPrecachedPSOs=1`, each run under this lane's GPU claim
(`pso-cache.sh record`). The game saves the bound-PSO recording on every `r.ShaderPipelineCache.Save` of the script.

| Run | Script | What it drew | PSOs recorded |
|---|---|---|---|
| A | `pso/rec-a.txt` | Home (and its controls list), Settings, Gear up, all four crew, the six guns on the rack, every slot of every gun with every part previewed on the Workbench (37 parts), a loadout (CHOPPER red dot + suppressor, NINE laser + suppressor, SHORTY 4x scope + laser + angled grip, STRETCH red dot + vertical grip) fitted, the Story: each gun drawn, fired from the hip, aimed and fired, reloaded, inspected; the route under the El with fights (kills, blood), aimed fights, the propane blast, a reel, the pause card, the truck, the results | 316 |
| B | `pso/rec-b.txt` | Hold the Block through the front end with CHOPPER 4x scope + compensator + wood grip, STICK scope + silencer + grip + laser + clear magazine + folded stock, STRETCH 4x scope + suppressor + angled grip + long magazine, RATTLER red dot + compensator + long magazine; each drawn, fired, aimed, reloaded; six waves of Goons and Buzzards with switches, aimed fights, a blast, the pause card | 318 |
| C | `pso/rec-c.txt` | The Story with SHORTY red dot + compensator + vertical grip + long magazine, NINE long magazine, STICK irons + standard magazine + open stock + angled grip, CHOPPER factory; Graphics quality Low, Medium, High and Ultra in play (a fight on each, `Graphics quality: 0` to `3` in the log), back to Auto, a fight, a blast | 397 |
| D | `pso/rec-d.txt` (on the after package, `game=dev view=guns-keys.txt`) | The Shipping path as a player drives it through the stream: the CLICK TO PLAY card, the home screen, every set-up screen by keys, the rack, the Workbench with parts, every gun drawn, aimed, fired and reloaded | 295, none new |

The union of A to C is 408 PSOs (A and B are nearly the same set, 319 together; C adds the quality levels'). The engine's
precacher compiled about 4,400 PSOs in each run (1,452 graphics and 2,887 compute in run A by the log's "Encountered a
new ... PSO" lines), of which only those 300 to 400 were ever drawn.

### How it was measured

The same package twice: **before** is the package of `09d3343` (no `.spc`), **after** the package of `e17401d`, whose
`unreal/` tree differs from it only by `Build/Linux/PipelineCaches/MurderInc_SF_VULKAN_SM5.spc` (`git diff --stat
09d3343 e17401d -- unreal/`). Both unzipped as the fresh user to the box's local disk (`/tmp/pso-pkg/before`, `after`).
The hitch lane's conditions: `lag-test.sh` with `load=1:0.05:0:1024` (`l20`), `cpus=0-7`, `-sm5`, `runas=fresh clean=1`,
`join=3`, a viewer through Pixel Streaming, a CSV profile of every frame. Runs under this lane's claim (`gated.sh`, which
also waits for any rendering editor), one game at a time. **Every run CLEAN**: `others=0` in every watcher line, `build=0`
(no compiler, cook or editor process) in every watcher line, the GPU to itself. Scripts: the hitch lane's `sm-story.txt`
(front end, then the Story) and `sm-hold.txt` (Hold the Block from the start, the fight 13 s after the process), and
the prover's `p-new-menus` line (the Shipping path driven by the viewer's `guns-keys.txt`, `-csvCaptureFrames` from the
process start). Numbers from every frame of the CSV (`pso_seg.py`, `pso_frames.py`, `frame_at.py` in this lane's folder).

### Per-frame numbers, before and after

**Story** (`m-before-story`, `m-after-story`; segments by the script's own events in the CSV):

| Segment | Before | After |
|---|---|---|
| Title, 0 to 3 s | worst **168.9 ms** (0.88 s), 4 frames over 25 ms, 2 over 50, 1 over 100; 1 % low 5.9 fps; PSO hitches 11 graphics + 18 compute | worst **22.2 ms**, **0** over 25 ms; 1 % low 45.1 fps; **0** PSO hitches |
| Home, 3 to 6 s | worst 16.7 ms, 0 over 25 ms, 0 hitches | worst 16.7 ms, 0 over 25 ms, 0 hitches |
| Crew, first draw (Gear up, 6 to 10 s) | worst **115.9 ms** (6.05 s), 1 frame over 25 ms; PSO hitches 5 graphics + 6 compute (in the frame before, render thread 92.8 ms) | worst **79.8 ms** (6.06 s), 1 frame over 25 ms; **0** PSO hitches; the frame before has `RenderThreadOther` 76.8 ms with no PSO created |
| The other set-up screens, 10 to 32 s | 0 over 25 ms, worst 17.3 ms | 0 over 25 ms, worst 19.7 ms |
| First 60 s of the run (intro, fights, switches, reloads) | 0 over 25 ms, worst 20.0 ms, 1 % low 58.7 fps, 0 hitches | 0 over 25 ms, worst 19.3 ms, 1 % low 59.0 fps, 0 hitches |

**Hold the Block** (`m-before-hold`, `m-after-hold`; the fight starts 10.4 s after `MIStart holdout`):

| Segment | Before | After |
|---|---|---|
| Start, 0 to 3 s | worst **179.5 ms** (0.87 s), 5 over 25 ms, 1 over 100; 1 % low 5.6 fps; 6 hitch frames, 14 graphics + 19 compute | worst **16.8 ms**, **0** over 25 ms; 1 % low 59.6 fps; **0** hitches |
| Intro to the fight, 3 to 13.4 s | worst 47.8 ms, 3 over 25 ms; 1 graphics + 2 compute hitches | worst 23.8 ms, **0** over 25 ms; 0 hitches |
| Fight, first 30 s | worst 29.1 ms, 1 over 25 ms; 1 % low 56.2 fps | worst 29.3 ms, 1 over 25 ms; 1 % low 55.5 fps |
| Fight, 30 to 60 s | worst 33.2 ms, 1 over 25 ms; 1 % low 55.6 fps | worst **18.0 ms**, **0** over 25 ms; 1 % low 59.1 fps |
| The rest of the run | worst 50.8 ms, 5 over 25 ms, 1 over 50 | worst 27.2 ms, 1 over 25 ms |
| Whole capture | 207 s: **15** over 25 ms, 2 over 50, 1 over 100, worst 179.5 ms, 1 % low **48.3** fps, **36** PSO hitches | 190 s: **2** over 25 ms, 0 over 50, 0 over 100, worst 29.3 ms, 1 % low **58.0** fps, **0** PSO hitches |

**The Shipping path through the stream** (`m-before-menus`, `m-after-menus`; times from the process start; the viewer
joins about 3 s after the first probe line):

| Moment | Before | After |
|---|---|---|
| Engine start, before any viewer (the stream does not run yet) | first frames 2,802.5 and 1,265.7 ms (29 graphics + 97 compute PSO hitches in the second), 93.3 ms at 4.20 s, **213.3 ms at 5.48 s** (11 + 19 hitches: the title's first frames) | first frames 5,869.4 and 637.5 ms (10 + 34 hitches), 54.4 ms at 7.17 s (6 graphics), 29.6 ms at 7.31 s (3 graphics); `LogPSOHitching` counts them at frame 41, before the cache's own log of new PSOs starts (see Still open) |
| Title and home with the viewer (8 to 14 s; 9 to 16 s after) | 0 frames over 25 ms, worst 20.2 ms | 1 frame over 25 ms (29.4 ms at 8.31 s, before the viewer's first key); 0 hitches |
| Crew, first draw | **124.8 ms** at 14.40 s, 3 graphics + 6 compute hitches | **84.7 ms** at 16.54 s, **1** compute hitch (76 ms) |
| Loadout, Workbench, every gun drawn, aimed, fired, reloaded (16 to 60 s) | 15 frames over 25 ms (H6, below), worst 31.1 ms, 0 hitches | 13 frames over 25 ms, worst 84.7 ms (the Crew frame above falls in this window after the 2 s later start), 0 other hitches |
| Whole capture (7,800 frames) | 35 over 25 ms, 7 over 50, 4 over 100; **176** PSO hitches (47 graphics, 129 compute) | 23 over 25 ms, 4 over 50, 2 over 100 (both the start, before any viewer); **54** PSO hitches (19 graphics, 35 compute), all but one before the viewer |

Recording D (`pso/rec-d.txt`, this path driven by the viewer's keys with `-logPSO`, on the after package) logged 295 PSOs,
all of them already among the 408 of A to C (`exp3/all.expand.log`: 408 PSOs, 757 stable PSOs, the same as without D), and
its game log reads `Encountered 50 PSO creation hitches so far (9 graphics, 41 compute). 0 of them were precached` at frame 0:
the remaining start-up hitches are PSOs created before the cache's logging starts, which a recording cannot catch.
The frames the viewer saved (`docs/unreal/shots/pso-before-after-frames.jpg`: the CLICK TO PLAY card, the rack, the
Workbench with the red dot, the NINE aimed; before above, after below; and 8 more frames of play looked at the same way)
are the same picture before and after: the cache changes when a PSO is compiled, not what is drawn.

The H4 train of 33 ms frames did not come back in the before runs on this box either (as the perf lane found: it needs the
box's CPUs busy), so H4 is proven here by its cause: the holdout's first minute had no PSO created at draw time after the
cache, and its frames over 25 ms went from 15 to 2. `PSO/PSOMisses` stays about the same (1,450 and 1,055 in the first 30 s
of the fight): it counts first look-ups in the runtime PSO cache (`PipelineStateCache.cpp`: `GraphicsPipelineCacheMisses++`
for every runtime state not from the file cache), not draws that waited, so it is not a stutter measure.

### What the cache costs

- **Start-up**: the first probe line comes 8 to 9 s after the launcher instead of 5 to 6 s (`firstline=` in the six
  runs' `info.txt`: before 5, 5, 6; after 9, 9, 8). The game log shows where: the 405 tasks are enqueued at once, then
  2.2 s to "Saved device pipeline cache file" and 1.7 s to "BeginNextPrecompileCacheTask() - Finished" before the first
  frame. A viewer never sees it (the stream starts after it); on E3DS it lengthens the loading page by about 3.5 s.
- **The engine's compile backlog**: `psoLeft` on the probe line counts down from 2,968 at 7 s to 0 at 29 s after the
  start (`m-after-story`): the precacher's own work is not smaller, it is no longer paid at draw time.
- Memory: not higher (highest resident 3,318 against 3,363 MB in the Story, 3,259 against 3,311 MB in the holdout;
  `summary.txt` of the four runs).

### H6: each set-up screen rebuild still costs a frame (not fixed)

Measured again (`m-before-menus`, 16 to 60 s, the viewer's key presses on Crew, Loadout, Workbench): 15 frames over 25 ms
(25 to 31 ms), in them the game thread 9 to 15 ms, of which `TickActors` 6.3 to 10.3 ms and `UI` 2.3 to 4.6 ms, the GPU
11 to 13 ms; the after run has the same pattern (13 frames over 25 ms). That is the rebuild in `UMIFrontEnd::Tick` (the
perf lane's `p-menus-m1`). It is not a shader cost, so the cache does not touch it. The fix is in the front end (rebuild
only the column that changed, or build the next screen in the frame after the key press): a change to the screens that
needs the menu fixer's tests and stream frames, not made here.

### Still open

- **The Crew screen's first draw**: 79.8 ms in `m-after-story` with no PSO created in it: the render thread's
  `RenderThreadOther` is 76.8 ms in the frame before. The perf lane's suggestion stands: draw the Crew stage once behind
  the CLICK TO PLAY card (front end, the menu fixer's).
- **Start-up 3.5 s longer** (above): the trade for no hitches; if E3DS's loading page has a limit, it is still far inside it.
- **Hitches at the engine's start** (before any viewer; 54 PSOs in `m-after-menus`, 50 counted by frame 41) and **one compute
  PSO at the Crew screen's first draw on the Shipping path** (76 ms): recording D did not catch them, so they are created
  before or outside the pipeline cache's logging. Not visible in a stream that starts after them; the Crew one is.
- **Record again** whenever materials, shaders, the guns or the engine change (`pso-cache.sh` header, steps 1 to 4): a PSO
  whose shaders left the cook is dropped (the cache degrades, it does not break), a new one is not in it. Levels 2 and 3
  need their own recordings.
- The release engineer's package: `package-cloud.sh` now prints `PSO CACHE OK` for both games and refuses the zip without
  it; READY.md "Before upload" has the check.

### The suite

`tools/box/test.sh MurderInc` in this lane's clone (`/project/ue/smooth/pso/repo`: the branch, the integration clone's
generated Content, `audio-import.sh` run once), golden replays included, nothing skipped, weakened or re-recorded:
`TESTS OK passed=222 failed=0 skipped=0` on `09d3343` (`HEAD:unreal` `038455c`, the config and probe change) in 71 s, and
again on `7444307` (`HEAD:unreal` `27fed6c`, the same tree as `e17401d`'s: the config and the `.spc`) in 67 s.

### Files

On the box, `/project/ue/smooth/pso/`: `repo` (this lane's clone, built, the suite), `rel` (the release copy), `cloud`
(the packages, `pso-keys`), `rec`, `rec2`, `rec3` (the recording runs A and B, C, D with their game logs and recordings),
`exp1`, `exp2`, `exp3` (the expanded caches and the commandlet's logs), `runs/m-before-*`, `runs/m-after-*` (CSV,
`game.log`, `others.log`, `summary.txt`), `q-before.txt`, `q-after.txt`, `gated.sh`, `chain.sh`, `pso_seg.py`,
`frame_at.py`, `plot_pso.py`, `rec0` (the first recording, without `IncludeAllPrecachedPSOs`). The unzipped packages are in `/tmp/pso-pkg/` (local disk: lost when the box stops). In the
repository: `docs/unreal/shots/pso-frames.jpg` (every frame of the Story and holdout runs, before and after).
