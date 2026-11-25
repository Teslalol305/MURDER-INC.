# Smooth play: the lanes' findings

The owner played version 4 on E3DS: "It is very laggy and buggy" (stutter or freezes, a low frame rate; bugs in menus,
weapons and gameplay). DECISIONS.md (2026-11-25, ~21:00) makes this file's verdict a release criterion. One section per
lane; every number names the run it comes from. Severities: blocker (a freeze, a crash, a stuck state, or under 50 fps
sustained on E3DS-class limits), must-fix (a player would feel or see it), should-fix, nit.

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
