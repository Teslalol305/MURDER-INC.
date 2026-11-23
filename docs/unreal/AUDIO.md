# Audio: the voice lines and the game's sound in Unreal

What exists, how it is wired, how to add a line or a sound, the recording brief, what is placeholder and what was
generated. The web game's sound is specified in `spec/07-ui-audio.md` (cited as "spec 07"); this page records what
the Unreal code does. Code: `unreal/MurderInc/Source/MurderInc/Audio/`; data: `Content/Data/voice.json`,
`audio.json`, `audio_sounds.json`; files: `Content/Audio/`; tests: `Tests/MIAudioTests.cpp`,
`Tests/MIAudioVoiceTests.cpp`, `Tests/MIAudioEngineTests.cpp`; tools: `tools/audio/` (placeholders, effects,
`voice_ingest.py` for real recordings, `render_report.py` to measure a render). State and evidence: `PROGRESS.md`,
section Audio.

## 1. Layers

| Layer | Class | Holds | Never |
|---|---|---|---|
| Rules (plain C++, seeded) | `FMIVoiceTriggers` (bus events to voice triggers), `FMIVoiceRules` (which line, which take, when), `FMIAudioDirector` (every event to play / set / stop commands and a mix state) | every decision | touch an actor, an audio component or the engine's audio device |
| Engine host | `UMIAudioSubsystem` (a world subsystem of game and PIE worlds) | binds the director to the world's bus, turns commands into audio components on imported Sound Waves, applies the mix each frame, attenuation, occlusion, reverb zones, the subtitle | decide what plays |
| Offline host | `FMIOfflineMix` | renders the same commands and mix into a WAV with no audio device (the tests' mix-down) | |
| Recording | `FMIAudioEventLog` | records a live bus to JSON (`MIAudio.Record start`, `MIAudio.Record stop <name>`), replays it into a bus | |

The voice is driven only by the event bus (`Core/MIEvents.h`): enemy kills with their kind, the flow's lines,
the player's hits and death. It reads no rule state. The sound host also reads the public player state the HUD
reads (`FMIPlayerRules::Health / MaxHealth`, for the heartbeat and the low-health filter), the camera (the listener)
and the enemy actors' positions (`AMIGoon`, `AMIBuzzard`: rotor loops follow their Buzzard; Goon footsteps are strided
from their movement because the bus has no enemy step event).

Nothing in another package had to change: the subsystem creates itself in every game world and listens. The hooks
the rest of the game can call (all optional, **none wired yet**: until they are, every crew member speaks with Rule's
set and the "RULE" subtitle, and the options keep their voice.json defaults):

| Who | Call | When |
|---|---|---|
| Options screen | `UMIAudioSubsystem::Get(this)->SetOptions(FMIAudioOptions)` | a slider or toggle changes (master, effects, ambience, music, UI, voice volume, subtitles, how often, clean language) |
| Loadout / crew (LOADOUT.md 3.4) | `SetCharacter(crewId)` | the run's crew member is applied |
| Loadout / attachments | `SetSuppressed(weaponId, true)` | a gun carries the silencer: its shots use `<weapon>_shot_silenced` and quieter tails. When `FMIShotFiredEvent` gains `bSuppressed` (LOADOUT.md 1.2), one line in `FMIAudioDirector::OnWeaponFire` reads it instead |
| Atmosphere | `SetNight(bool)` | time of day: the day and night beds crossfade |

Until the options screen calls it, the console drives the same options: `MIAudio.Volume <master|effects|ambience|music|ui|voice> <0..1>`,
`MIVoice frequency <off|rare|normal|often>`, `MIVoice subtitles 0|1`, `MIVoice clean 0|1`, `MIVoice character <id>`.

**A decision for the user: clean language is off by default** (voice.json `settings.options.cleanLanguage: false`),
so "What's my motherf\*\*\*in' name?!" plays uncensored until a player turns clean language on, and today only the
console can (no options screen calls `SetOptions` yet). Set it to `true` in voice.json to ship clean by default.

## 2. The voice lines

### 2.1 How a line is chosen

1. `FMIVoiceTriggers` turns bus events into triggers (voice.json `triggers` lists them all):

| Trigger | From the bus |
|---|---|
| `kill.ordinary`, `kill.headshot`, `kill.melee`, `kill.explosive`, `kill.buzzard` | `Enemy` killed with `bByPlayer`: Buzzard; else weapon `melee`; weapon `blast`; part `head`; else ordinary |
| `kill.multi` (value: how many) | a kill within `multiKill.window` (1.5 s) of the last |
| `kill.streak` (value: the streak) | the streak reaches a threshold (6, 12, 20, 30); a hit of `streak.breakDamage` or a gap over `streak.gap` (25 s) breaks it |
| `kill.lastOfWave` | a kill no more than `lastOfWaveWindow` (0.5 s) before `objective:done wave` |
| `run.start` | `game:state intro`, or `playing` from the title, a death or a debrief (a restart also silences the old run first) |
| `reel.collected`, `wave.cleared` | `objective:done` (an objective id / `wave`) |
| `wave.milestone` (value: the wave) | every `waveMilestone`-th wave cleared (5, 10, 15 ...) |
| `score.newBest` (value: the score) | `score:best` from the flow (not sent yet: hand-off in PROGRESS.md); until then a Hold the Block card above every earlier card of the session |
| `objective.update` | `hud:objective` during play, more than 2 s into the run |
| `health.lowSurvived` | a hit left health under `lowHealth.below` (30) and `lowHealth.survive` (6 s) passed with no hit, alive |
| `extraction.called`, `run.win` | `objective:all`, `extraction:reached` |
| `results.complete`, `results.holdout`, `results.dead` | `menus:card complete`; `menus:card dead` after a Hold the Block run / a Story run (no line listens to the last) |

2. `FMIVoiceRules` collects the triggers of the last `coalesceWindow` (0.3 s) and judges them together, the most
   important line first (a trigger may carry its own priority: `kill.lastOfWave` lifts "It's Murda!" to 75). Each
   candidate that is not cooling down rolls its chance (seeded `FRandomStream`) times the **repeat decay**
   (`repeatDecay` 0.8 to the power of the line's plays in this run: the third "It's Murda!" of a run is half as likely
   as the first); the first that wins speaks. Lines that can wait (`queueable`, seconds) queue behind it, the rest are
   dropped; a trigger marked `onlyIfSilent` speaks only when nothing else of the same moment did (a wave's
   "Rule Baby!" after a wave whose last kill did not already say "It's Murda!").
3. A line may start when nothing is speaking, `afterLineGap` (0.8 s) has passed since the last line, and the
   `globalCooldown` (6 s) has passed since the last start. A line `interruptMargin` (30) above the last one skips the
   gap and the global cooldown, and cuts a playing line that is `interruptible`, **except between two kill barks**
   (`barkTriggers`: ordinary, headshot, melee, explosive, Buzzard and multi kills): a burst of ten kills is one clean
   line, never "Holla, ho- It's Murda!"; streaks, the last kill of a wave and every progress beat still cut. A trigger
   marked `always` (the win, the wave milestone, a new best) ignores the line's cooldown, the global cooldown and the
   decay, and waits (`queueable`) behind a line it may not cut. An answer (the crowd after "What's my name") plays on
   time, `answer.delay` after the take ends, and is never cut.
4. The take: among the takes of the **intensity the trigger asks for** (`intensity`: the win and the milestones
   `shout`, a close call survived `breath` or `spoken`, the run start and the debrief `shout` or `spoken`), at random,
   never the one the line played last time; any take when none matches.
5. The death, `player:reset` (restart from the pause menu, "Run it back"), an intro that does not come from the title
   and the title silence the voice: the playing line stops (at once while the world is paused), and nothing queued or
   answered survives. A run start resets the repeat decay.

While a line plays the other categories duck (voice.json `settings.duck`: music 0.5, ambience 0.55, world 0.65,
near 0.75, gun 0.8, tail 0.7; attack 0.06 s, release 0.45 s). The subtitle (speaker in gold `#f6c21a`, the line in
ink `#f4f2ec`, on a plate) is drawn under the crosshair through `AHUD::OnHUDPostRender`, for the take's length + 0.6 s.

### 2.2 The lines and what triggers them

| Line (id) | Text | Triggers (chance) | Cooldown | Priority |
|---|---|---|---|---|
| `holla` | Holla, holla! | kill.ordinary 0.14, kill.melee 0.5, kill.explosive 0.4, kill.buzzard 0.3 | 25 s | 20 |
| `murda` | It's Murda! | kill.headshot 0.25, kill.multi 0.6 (shout or spoken), kill.lastOfWave 0.5 (priority 75, shout) | 40 s | 50 |
| `rulebaby` | Rule Baby! | reel.collected 0.9, wave.cleared 0.9 (only if the wave's kill did not speak), extraction.called 1.0 (shout), health.lowSurvived 0.4 (breath or spoken), objective.update 0.15; queues up to 2.5 s | 12 s | 60 |
| `inc` | I-N-C! | run.start 0.8, results.complete 1.0, results.holdout 1.0 (shout or spoken); queues up to 3 s | 20 s | 70 |
| `name` | What's my motherf\*\*\*in' name?! | run.win 1.0 (always, priority 100, queues 6 s, shout), wave.milestone 1.0 (always, queues 4 s, shout), score.newBest 1.0 (always, shout), kill.streak at 20 or more 1.0 | 60 s | 90, not interruptible |
| `rule_chant` (CROWD) | R-U-L-E! | only as the answer of `name`, 0.35 s after it | | 95 |

How often, by the options' **How often**: `off` silences every line; `rare` halves the chances and doubles the
cooldowns (1.6 x); `often` multiplies the chances by 1.6 and the cooldowns by 0.6, the global cooldown by 0.5.

**Measured rates (normal), real take lengths.** `MurderInc.Audio.VoiceRate` plays a Story run on Boss as spec 04
2.10 and config.json have it (the patrol of 4 Goons and 2 Buzzards, a wave after each reel of 5+2, 6+3 and 7+4, the 8
pursuit arrivals, intro then playing, the objective line after each reel, the player hit every 1.5 to 5 s in every
fight, the truck, the debrief), 20 seeds: **4.6 minutes, 41 kills, 2.56 lines a minute** (11.7 a run), **13 % of the
kills speak**; per run Holla 2.75, It's Murda 2.70, Rule Baby 2.55, I-N-C 1.65, What's my name and its crowd answer
1.0 each (the win, every run). It fails outside 1 to 3 lines a minute, at a quarter of the kills, or when a run's win
is not called and answered. `MurderInc.Audio.VoiceRateHoldout` plays Hold the Block as spec 04 2.11 has it (waves of
min(5 + 2n, 30), a third Buzzards, 9 s breathers, enemy damage up to x 2, hits every 1.5 to 5 s so no streak
survives, dead after wave 12): **10.6 minutes, 2.61 lines a minute, "It's Murda!" 0.73 a minute (the worst run
0.89)**, What's my name 2 a run (waves 5 and 10, every run, each answered). It fails above one "It's Murda!" a minute
in any run, without "What's my name" by wave 10, or above 3 lines a minute. `MurderInc.Audio.VoiceWin` proves the win
after a 20-kill streak 25 s earlier is still called (shouted, then the crowd), that it cuts "I-N-C!" and waits behind
the uninterruptible streak line; `VoiceBurst` that ten kills 0.3 s apart are at most one line with no cut (40 seeds:
every burst spoke once); `VoiceDirector` the same through the whole director plus a pause in the middle of a line
(nothing new, no close call on the frozen clock, the crowd after resuming), a restart (the line stops, no answer, no
queued line) and a progress beat cutting a kill bark.

### 2.3 Clean language

`name` is flagged `profane`. With **clean language** on: mode `swap` (the default) plays the clean takes
`name_clean_*` ("What's my name?!") and shows that text; mode `bleep` plays the normal take, mutes it over each take's
`bleep` range (seconds) and plays a 1 kHz tone (`Gen/bleep_1k.wav`) there. The placeholder takes carry empty ranges
([0, 0]): `MurderInc.Audio.VoiceData` fails if the mode is switched to `bleep` while a profane take has an empty range
(the word would play unbleeped). Real takes get their ranges from `voice_ingest.py --bleep` (section 5).

### 2.4 Per-character sets

`voice.json characters.<crew id>` holds each crew member's own lines (crew.json ids: `rule`, `deuce`, `smoke`,
`keys`). A member with no lines is silent: there is no fallback to Rule's voice. `SetCharacter` switches the set and
restarts the cooldowns. Files: `Content/Audio/Voice/<crew id>/`.

### 2.5 Adding or retuning a line

Everything is data (`voice.json`): add an entry under the character's `lines` with `text`, `priority`, `cooldown`,
`triggers` (trigger: chance, or `{chance, atLeast, priority, intensity, always, queueable, onlyIfSilent}`; voice.json
`meta.triggerRules` explains each), `takes` (files), and optional `queueable`,
`interruptible`, `answer`, `profane` + `clean`, `speaker`, `volume`. Put the WAV files in
`Content/Audio/Voice/<character>/`, run `tools/box/audio-import.sh` on the box. `MurderInc.Audio.VoiceData` checks
that the files exist (48 kHz mono), that every take is under 2.5 s (the crowd chant under 2.2 s) with no silence over
0.5 s inside and at most 0.45 s at its end, that every trigger is a known one, and warns with the count of placeholder
takes (21 of 21 today). New trigger kinds need a line in
`FMIVoiceTriggers` and in voice.json `triggers`.

## 3. The game's sound

### 3.1 Sources

| Tree | What | Committed |
|---|---|---|
| `Content/Audio/Web/` | the web game's 104 sounds, 190 variants, rendered by `node tools/ue-export/audio.mjs` from `src/audio/library.js` (the browser's own synthesis, seeded: identical files on every machine) + the two reverb responses | no (27 MB; regenerate, or copy as `mi-audio-web.tar` through the storage, BOX.md 4) |
| `Content/Audio/Gen/` | generated replacement and layer material (section 6) | yes |
| `Content/Audio/Voice/` | the voice takes (placeholders, section 5) | yes |

`audio_sounds.json` (generated by the same script) holds every web definition: bus, variants, lengths, peak,
volume, jitter, priority, voices, gap, reference distance and roll-off, loop and stereo flags. `audio.json` holds the
rest by hand. The import (`tools/box/audio-import.sh`, `Content/Python/mi_audio_import.py`, headless, about 90 s)
makes `/Game/Audio/<same path>` Sound Waves next to the files, loops flagged; a file replaced under the same name is
re-imported in place, so real material needs no code or data change.

### 3.2 The event table

`audio.json events` has an entry for every key the bus can produce (`FMIAudioDirector::BusEventKeys()`, plus every
`Note(TEXT("..."))` flow line the gameplay source emits, which `MurderInc.Audio.EventTable` scans so a new flow line
fails the test until it gets an entry): 61 keys, 21 that play a list of sounds, 24 that name a code rule, 17 explicit
`silent` with the reason. The rules: `gunshot` (spec 07 3.20: dry shot, layers, street and garage tails split by the
interior zone, the burst rule, the casing on the ground 0.45 to 0.65 s later by the surface underfoot, the gunfire
duck), `impact` (surface table, ricochet roll, the 22 ms impact gap), `explosion` (near layer + a far layer, the duck,
the distance muffle), `step` and `land` (surface table), `hurt`, `dead`, `rotor` (one loop per Buzzard following its
actor, the six nearest within 90 m heard), `telegraph` (charge pitched to the telegraph), `enemyShot` (at the muzzle,
the enemy-fire duck, the near-miss whizz of spec 07 3.21 with an occlusion trace), `grunt` (no hit grunt on the
killing hit), `fuse` (hiss rising with the burnt fraction), `reelSecured`, `sting`, `radio`, `grab`, `state`,
`reset`, `music`.

### 3.3 The mix (spec 07 2.11, 3.19, 4.5, 4.6)

| Category | Volume | Option slider | Muffled | Plays paused | Reverb send |
|---|---|---|---|---|---|
| gun | 1.0 | effects | yes | no | 0.10 |
| tail | 0.85 | effects | yes | no | 0 |
| near | 0.95 | effects | yes | no | 0.14 |
| world (3D) | 1.05 | effects | yes | no | 0.5 |
| ambience | 0.7 | ambience | yes | no | 0 |
| ui | 0.95 | ui | no | yes | 0 |
| music | 0.5 (x 0.9 stem trim = spec 07's 0.45) | music | no | yes (thinned) | 0 |
| voice | 1.0 | voice | no | no | 0 |

Every frame the director computes each category's gain: volume x slider x master trim (1.0) x the ducks (gunfire 0.45,
NINE 0.55, 85 ms hold; enemy fire 0.85 on the ambience; blasts 0.4 / 0.6 with the music dip) x the voice duck x
states (ambience 0.6 title, 1 run, 0.7 dead, 0.8 debrief; x (1 - 0.55 x interior); the train duck) and the low-pass
cut-offs: the muffle `20000 x 0.03^m` (hits, blasts within 20 m, death settling at 0.85), the **low-health** state
(new: under 35 % health the muffled categories close toward 3.2 kHz, the music thins to 75 % and the ambience to
70 %, with the heartbeat loop of spec 07 3.22), and the **pause** state (world refused, music at 45 % behind 1.3 kHz).
The ambience also closes by the interior factor, `20000 x 0.08^i` (20 kHz on the street, 1.6 kHz inside the shop,
spec 07 3.19). The host applies them to every live component (`SetVolumeMultiplier`, `SetLowPassFilterFrequency`).

**The master chain** (spec 07 2.11 / 4.5, audio.json `master`): SUM -> compressor (threshold -6 dB, knee 8 dB,
2.5 : 1, attack 6 ms, release 140 ms) -> x 1.15 -> soft clip. In the engine `FMIMasterChain` (Audio/MIAudioMaster)
puts two Submix Effect Dynamics Processors on the device's master submix when a game world begins play: the
compressor with the make-up as its output gain (+1.2 dB), then a soft-knee limiter (threshold -0.3 dB, knee 8.2 dB,
look-ahead 3 ms) standing in for the web curve, whose knee starts at -4.4 dB (0.6). The offline mix runs the same
compressor (`FMIMasterCompressor`, stereo-linked, soft knee) and the web game's exact curve. The game's volume setting
(default 0.8) is not in these gains: `UMIGameSubsystem::ApplySettings` sets it as the device's primary volume, after
the chain, where the browser has it; audio.json `options.master` is only a trim before the chain and stays 1.0 (it was
0.8 before the fix pass, which with the device volume played the game at 0.64).

### 3.4 Space

- **Distance**: a custom attenuation curve sampled from spec 07's inverse model `ref / (ref + roll (d - ref))` (per
  sound's ref and roll, 48 points, out to the 160 m cull), built in code per (category, ref, roll).
- **Air absorption**: the attenuation's low-pass by distance with log-frequency scaling, 20 kHz at 0 to 2.5 kHz at
  100 m (= `20 kHz x e^(-d/48 m)`, a straight line in log frequency).
- **Occlusion**: the engine's occlusion trace (Visibility channel): an occluded source loses 0.45 of its level and
  closes to 1.4 kHz over 0.12 s.
- **Reverb**: `UReverbEffect` presets activated by zone: `street` (1.4 s, dark, early slaps), `underEl` (under the
  El's deck, x -46..46 m, z -5.4..5.4 m, 3 m fade: shorter, steel ring), `shop` (the interior box of level.json:
  0.8 s, bright, dense). The interior factor also splits the gun tails (street tail outside, garage tail inside).
- **Panning**: the engine's default panning (no HRTF), as the web game.

### 3.5 Ambience and music

Day and night beds, the wind near the El, the far one-shots on the timers of spec 07 2.14 placed around the
listener, the El train every 40 to 70 s with rumble and clack loops riding the point of the train nearest the listener,
the squeal in 70 % of passes and the train duck; neon and steam emitters are not placed yet (open issue). The score's
seven stems loop together and their gains follow the bus's music intensity with the layer formula of spec 07 3.24
(meter, tiers, the dead mode); stings duck the stems. The riser and impact on the bar grid (Quartz) are not yet built.

## 4. The host in the engine

`UMIAudioSubsystem` (tickable, also while paused): on begin play it binds the director to `UMIEventSubsystem`; each
frame it observes the listener (first player's camera), the player's health, the enemy actors, ticks the director with
real seconds, executes the commands (`CreateSound2D` then spatialisation, attenuation override and location for 3D,
`bIsUISound` for UI and music, fades on stop, a plain stop while the world is paused because a paused world does not
advance fades), applies the mix, switches the reverb zone, and draws the subtitle. It installs the master chain on
begin play and removes it when the world goes. It logs once per world `voice: N of M takes are placeholders`, and
in every build but Shipping draws a small dim "placeholder voice" tag under a subtitle whose take is a placeholder.
A file with no asset is skipped (logged once, Verbose); a missing replacement layer falls back to the web sound.

## 5. The recording brief (for the real voice)

Today every take is a **placeholder in a generic stock synthetic voice** (Higgsfield `seed_audio` on built-in preset
voices, the prompt being only the line's text: `tools/audio/voice_plan.json`). No voice was cloned or imitated, no
released recording was sampled. The real recordings replace them **file for file, with no code change**.

### 5.1 What to record

Seven lines. For each, **three intensities**, and at least **three takes of each intensity** (nine or more per line;
the best three go in the game, the rest are spares). Each take is the line once, alone: no count-in, no second try in
the same file.

| Line | Say | Intensity and where the game uses it |
|---|---|---|
| `holla` | "Holla, holla!" | ordinary kills, melee, blasts, a Buzzard down: all three intensities, mostly **spoken** |
| `murda` | "It's Murda!" | headshots, quick doubles (**shout** or **spoken**), the last kill of a wave (**shout**). Keep it short: about 1 s |
| `rulebaby` | "Rule Baby!" | a reel secured (**shout**, **spoken**), the truck called (**shout**), a close call survived (**breath**: raspy, to himself) |
| `name` | "What's my motherf\*\*\*in' name?!" | the win, every fifth wave, a new best (**shout**, full voice, the big moment); a long kill streak (**shout** or **spoken**). Leave a short beat at the end: the crowd answers |
| `name_clean` | "What's my name?!" | the same moments with clean language on; same energy as `name` |
| `inc` | "I-N-C!" | the run starting and the debrief (**shout** or **spoken**): three letters, punchy, even spacing, the whole thing 1.5 to 2 s |
| `rule_chant` | "R-U-L-E!" | the crowd answering `name`: several people together (four or more if you can; one person recorded four times also works), the four letters on an even beat, about **0.4 s apart, 1.6 to 2 s in all, under 2.2 s**. Three takes, each a different group or mix |

**Shout** = full voice, as if across a street. **Spoken** = confident, to someone next to you. **Breath** = low,
raspy, close, under the breath. Every take must be **under 2.5 s** (the chant under 2.2 s) with **no pause over half
a second inside it**: the game checks this (`MurderInc.Audio.VoiceData`) because a long take keeps the voice "speaking",
blocks other lines and holds the rest of the mix down.

**Name the files** `<line>_<NN>[_<intensity>]`, NN two digits: `murda_01_shout`, `murda_02_spoken`,
`murda_03_breath`, `murda_04_shout` ... The first three of each line replace the placeholders 01 to 03 (01 shout,
02 spoken, 03 breath, as now); 04 and up are added as new takes with the intensity the name says. Spares you do not
want in the game: name them `spare_murda_07` (anything not matching the pattern is skipped). Keep the extension the
app gives (.m4a, .wav ...).

**The word to bleep**: for each `name_*` take, note where "motherf\*\*\*in'" starts and ends (seconds into the
file, two decimals, from any audio editor or by ear). Only needed if the game ships with clean mode `bleep` instead
of the clean takes; write them in the notes sheet.

### 5.2 With a phone

- **App**: iPhone Voice Memos (set Settings > Voice Memos > Audio Quality to **Lossless**; the default "Compressed"
  .m4a also works), or on Android a recorder with a WAV or "high quality" setting (Samsung Voice Recorder, Easy Voice
  Recorder, RecForge). Use the phone's own microphone, no Bluetooth headset.
- **Turn off what "helps"**: in Voice Memos turn off **Enhance Recording** and **Reduce Background Noise** if the
  phone offers them; on Android turn off **noise suppression / speech enhancement** and any "voice focus". No filters,
  no auto-level tricks we can avoid: the phone's automatic gain cannot always be turned off, so **keep the same
  distance and do not hold back on the shouts** (the gain settles; a shout that clips is worse than a quiet one, see
  below).
- **Distance**: phone at **about 30 cm (a forearm) for spoken and breath**, **about 60 cm for shouts**, microphone
  (the bottom edge) pointing at your mouth from slightly below, so your breath goes past it. Hold it still or lay it on
  a pile of clothes; do not touch it during a take.
- **Room**: the deadest room you have. Best: **a walk-in closet or wardrobe full of clothes**, or standing between a
  bed and a sofa with duvets or coats hung around you. Avoid kitchens, bathrooms, stairwells, empty rooms, cars on a
  street. Turn off fans, fridge hum and air conditioning if you can; no TV or music.
- **Level check**: record a shout and play it back. If it sounds crushed or crackles, step back 20 cm. If the breath
  takes are lost in hiss, come 10 cm closer for those only.
- **Takes**: one take per recording is easiest (name each one as above right away). Several takes in one long
  recording also work: say the slate before each ("murda, shout, one") and leave two seconds between takes; then cut
  them in any editor, or send the long file with the notes sheet and we cut it.
- **Send** the files **as they are** (no conversion, no editing, no "enhance"): AirDrop or share them into a shared
  folder (Google Drive, Dropbox, iCloud), or a zip by a file-transfer link. Messaging apps (WhatsApp, iMessage audio)
  recompress the sound: share them as **files** ("Save to Files" / "Share as file"), not as voice messages.

### 5.3 In a studio

- **Format**: WAV, **48 kHz, 24-bit, mono**, dry: no reverb, no music, no compression or limiting, at most a gentle
  high-pass (80 Hz). Large-diaphragm condenser or a dynamic for the shouts, **15 to 30 cm** with a pop filter
  (spoken and breath), **40 to 60 cm** or a step off-axis for shouts. A treated booth or a dead room.
- **Level**: set the gain on the loudest shout so it peaks around **-6 dBFS**; peaks must stay under **-3 dBFS**.
  Reference: spoken takes land around -20 to -24 dBFS RMS at that gain; do not re-trim the gain between takes of one
  intensity (the pipeline levels them; it cannot undo clipping).
- **Slate** each take ("murda, shout, take four") on the talkback track or in the session, not on the take itself;
  **100 ms of silence before, 300 ms after** each take when exporting, one take per file, named as in 5.1.
- **Take sheet** (one row per take): file name, line, intensity, take number, circled or not, notes (energy, a
  word that tripped, noise), and for `name_*` the **bleep marks** (start and end of the profane word in seconds of the
  exported file). A spreadsheet or a text file next to the WAVs.
- **The crowd chant**: record four or more voices together on one mic (or each voice separately, same distance) to
  a click at **150 BPM** (a letter every 0.4 s): R on the beat, U, L, E, the E held a little longer; 1.6 to 2 s in all.
  Three different groupings or mixes.
- Deliver the WAVs, the take sheet and the session notes (mic, room) in one folder, as for the phone.

### 5.4 What happens to the files

`python3 tools/audio/voice_ingest.py <the folder>` (on any machine with ffmpeg and Python with numpy) converts every
file (any format: .m4a, .wav, .aiff, .flac, .mp3 ...) to 48 kHz 24-bit mono, trims it to the line with 100 ms before
and 300 ms after, levels it to **-18 LUFS with peaks under -1 dBFS**, writes it under
`Content/Audio/Voice/rule/<line>_<NN>.wav`, sets `"placeholder": false` on that take in voice.json (adds the take for
04 and up, with the intensity from the name), takes the bleep marks with `--bleep name_01=0.62:0.98` and shifts them
with the trim, and reports each take's length, its longest inner pause and its loudness, flagging what the game check
would refuse. `--dry-run` only reports. Then commit, and on the box `sync.sh`, `audio-import.sh`,
`test.sh MurderInc.Audio`. The take count of the placeholder warning drops as real takes arrive.

### 5.5 Voice use release (a short note to sign)

Before recording, the speaker and the user sign a short release, for example: "I, [speaker], agree that my recorded
performance of the lines 'It's Murda!', 'Holla, holla!', 'Rule Baby!', 'What's my motherf\*\*\*in' name?!', 'What's
my name?!', 'I-N-C!' and the chant 'R-U-L-E!' may be used, edited and distributed in the game MURDER INC. and its
trailers and promotion, in every medium, worldwide, without time limit [for the fee of ...]. The recordings are new
performances made for the game and use no released recording." Crowd voices sign the same, one line each. The rights
in the recordings are the user's to secure; this project only ever uses recordings made for it.

## 6. Generated material (Higgsfield) and what it cost

| What | Model | Files | Credits |
|---|---|---|---|
| Placeholder voice takes: 6 lines x 3 intensities + 3 clean takes + 6 stock voices for the crowd | `seed_audio` (preset voices, text to speech) | 18 takes + 3 crowd mixes (`tools/audio/voice_placeholders.py`: mono, 48 kHz, a gate that drops generator blips and shortens inner pauses to 0.12 s (0.14 s between spelled letters), a pitch-keeping tightening of at most x 1.35 where the stock read is slow, -18 LUFS; the crowd assembled on one chant grid with a short room) | about 3.5 (0.1 to 0.3 a take, two test takes included) |
| Fix pass: the six breathed takes again at a neutral speaking rate (they had `speech_rate` -15: up to 5.7 s) | `seed_audio`, same preset voice, same text | `holla_03`, `murda_03`, `rulebaby_03`, `name_03`, `name_clean_03`, `inc_03` | 1.2 (6 x 0.2) |
| Gun layers (CHOPPER and NINE close, mechanical, distant tails, silenced shots), dry fire, reload stages, casings on asphalt and concrete, impacts per surface, the Goon SMG at 30 m, the Buzzard's rotor loop and gun, explosions near and far, footsteps (asphalt, concrete, metal; walk and run), the El train, the hot-afternoon room tone | `mirelo_text_to_audio` | 79 files (`tools/audio/sfx_plan.json`; `tools/audio/sfx_process.py`: DC out and a 20 Hz high-pass, oneshot / tail / loop cuts with a minimum length per kind (casings 0.3 s, steps 0.25 s, far blast 2.5 s, near blast 1.5 s), every variant set levelled to one loudness (the loudest 400 ms, K-weighted) matched to the web sound it plays over, the silenced shots 11 dB under the open ones once the layer volumes count, 48 kHz 24-bit), 10.4 MB with the bleep. Re-cut in the fix pass from the same generated files (no new generation) | 49.0 (0.25 a second) |

In all about 54 credits of generation. Balance: 4,015.6 at the start of the first pass, **3,358.6** at its end (the
3,392.8 this page gave before was read before the last generations of that pass); 3,282.7 at the start of the fix
pass (the GPU box and other packages' work on the same account in between). The difference beyond the generations is
the GPU box and the other packages.

**The prompts are in the repository**, so anyone can check them: `tools/audio/voice_plan.json` (every voice request:
the line's text, the model, the preset voice id, the loudness, speed and pitch settings; no names, no reference
audio, no cloning) and `tools/audio/sfx_plan.json` (every effect prompt, length and cut).

All of it is placeholder: synthetic material to give the mix weight now, to be replaced by recorded or licensed
sound (guns first: a recorded carbine and 9 mm with separate close, mechanical and tail layers). `audio.json replace`
keeps the web sound under each layer (`web` gain) so the timing and character of the original stay audible; a layer
whose files are missing falls back to the web sound.

## 7. Proof: the mix-down of a recorded fight

- `Content/Data/audio_fight.json`: a 52 s scripted Story fight as a bus event stream (`tools/audio/fight.py`): run
  start, the radio, Goons and a Buzzard arriving, enemy bursts with near misses, CHOPPER bursts with hits and a kill,
  a reload, a bolt hit, the switch to the NINE, a Buzzard and a headshot, a propane blast, a close call, the reel
  grab and the reel, a melee kill, the last reel, two bursts, a dry fire, a jump, the truck, the debrief. The format is
  what `MIAudio.Record` writes from a live session (Saved/Audio/<name>.json; `recorded.json` is used by the test when
  present), so a real play session can be rendered the same way.
- `MurderInc.Audio.Mixdown` replays it through the director at 100 Hz and renders `Saved/Audio/fight_mixdown.wav`
  (stereo 48 kHz 16-bit) with `FMIOfflineMix`: the same commands and mix state, the spec's distance model, air
  absorption, equal-power panning, a small Schroeder reverb on the sends, the web game's soft clip. It proves the
  decisions and the mix; it is not the engine's spatialiser.
- `MurderInc.Audio.EngineRender` (`tools/box/audio-engine-render.sh`) plays the same stream through the engine's
  own audio mixer on the imported Sound Waves and records the master submix (`Saved/Audio/engine_render.wav`) when the
  process has an audio device. On the box the SDL dummy driver gives one: 479 components started on the imported
  assets and the recording announced 55.5 s of 6-channel output, but the first runs quit before the background WAV
  writer finished; the test now waits for the whole file (re-run pending, PROGRESS.md). The default `test.sh` run has
  `-NoSound`, so there the test warns and passes.
- Measured mix-down (offline): 55.9 s, 501 voices, peak -0.1 dBFS after the soft clip, RMS -17 dBFS, 7 voice lines.

## 8. Open issues

- The riser and impact of the music conductor (Quartz bar grid), the boombox at the reels, neon and steam emitters
  (the level's lamp and vent positions), the night far one-shot schedule (the day one plays at night too).
- Goon footsteps use one surface (asphalt) until the enemies' step event carries their surface.
- The engine's convolution reverb with `IR_street` / `IR_shop` instead of the algorithmic presets (needs Impulse
  Response assets).
- The options screen does not call `SetOptions` yet, and the options are not saved (FMISettings belongs to the
  gameplay package).
