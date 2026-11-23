# Audio: the voice lines and the game's sound in Unreal

What exists, how it is wired, how to add a line or a sound, the recording brief, what is placeholder and what was
generated. The web game's sound is specified in `spec/07-ui-audio.md` (cited as "spec 07"); this page records what
the Unreal code does. Code: `unreal/MurderInc/Source/MurderInc/Audio/`; data: `Content/Data/voice.json`,
`audio.json`, `audio_sounds.json`; files: `Content/Audio/`; tests: `Tests/MIAudioTests.cpp`,
`Tests/MIAudioEngineTests.cpp`. State and evidence: `PROGRESS.md`, section Audio.

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
the rest of the game can call (all optional, none wired yet):

| Who | Call | When |
|---|---|---|
| Options screen | `UMIAudioSubsystem::Get(this)->SetOptions(FMIAudioOptions)` | a slider or toggle changes (master, effects, ambience, music, UI, voice volume, subtitles, how often, clean language) |
| Loadout / crew (LOADOUT.md 3.4) | `SetCharacter(crewId)` | the run's crew member is applied |
| Loadout / attachments | `SetSuppressed(weaponId, true)` | a gun carries the silencer: its shots use `<weapon>_shot_silenced` and quieter tails. When `FMIShotFiredEvent` gains `bSuppressed` (LOADOUT.md 1.2), one line in `FMIAudioDirector::OnWeaponFire` reads it instead |
| Atmosphere | `SetNight(bool)` | time of day: the day and night beds crossfade |

Until the options screen calls it, the console drives the same options: `MIAudio.Volume <master|effects|ambience|music|ui|voice> <0..1>`,
`MIVoice frequency <off|rare|normal|often>`, `MIVoice subtitles 0|1`, `MIVoice clean 0|1`, `MIVoice character <id>`.

## 2. The voice lines

### 2.1 How a line is chosen

1. `FMIVoiceTriggers` turns bus events into triggers (voice.json `triggers` lists them all):

| Trigger | From the bus |
|---|---|
| `kill.ordinary`, `kill.headshot`, `kill.melee`, `kill.explosive`, `kill.buzzard` | `Enemy` killed with `bByPlayer`: Buzzard; else weapon `melee`; weapon `blast`; part `head`; else ordinary |
| `kill.multi` (value: how many) | a kill within `multiKill.window` (1.5 s) of the last |
| `kill.streak` (value: the streak) | the streak reaches a threshold (6, 12, 20, 30); a hit of `streak.breakDamage` or a gap over `streak.gap` (25 s) breaks it |
| `kill.lastOfWave` | a kill no more than `lastOfWaveWindow` (0.5 s) before `objective:done wave` |
| `run.start` | `game:state intro`, or `playing` from the title, a death or a debrief |
| `reel.collected`, `wave.cleared` | `objective:done` (an objective id / `wave`) |
| `objective.update` | `hud:objective` during play, more than 2 s into the run |
| `health.lowSurvived` | a hit left health under `lowHealth.below` (30) and `lowHealth.survive` (6 s) passed with no hit, alive |
| `extraction.called`, `run.win` | `objective:all`, `extraction:reached` |
| `results.complete`, `results.holdout`, `results.dead` | `menus:card complete`; `menus:card dead` after a Hold the Block run / a Story run (no line listens to the last) |

2. `FMIVoiceRules` collects the triggers of the last `coalesceWindow` (0.3 s) and judges them together, the most
   important line first (a trigger may carry its own priority: `kill.lastOfWave` lifts "It's Murda!" to 75). Each
   candidate that is not cooling down rolls its chance (seeded `FRandomStream`); the first that wins speaks. Lines that
   can wait (`queueable`, seconds) queue behind it, the rest are dropped.
3. A line may start when nothing is speaking, `afterLineGap` (0.8 s) has passed since the last line, and the
   `globalCooldown` (6 s) has passed since the last start. A line `interruptMargin` (30) above the last one skips the
   gap and the global cooldown, and cuts a playing line that is `interruptible`. An answer (the crowd after
   "What's my name") plays on time, `answer.delay` after the take ends, and is never cut.
4. The take: at random among the line's takes, never the one it played last time.
5. The death, a reset or the title silence the voice (nothing pending survives).

While a line plays the other categories duck (voice.json `settings.duck`: music 0.5, ambience 0.55, world 0.65,
near 0.75, gun 0.8, tail 0.7; attack 0.06 s, release 0.45 s). The subtitle (speaker in gold `#f6c21a`, the line in
ink `#f4f2ec`, on a plate) is drawn under the crosshair through `AHUD::OnHUDPostRender`, for the take's length + 0.6 s.

### 2.2 The lines and what triggers them

| Line (id) | Text | Triggers (chance) | Cooldown | Priority |
|---|---|---|---|---|
| `holla` | Holla, holla! | kill.ordinary 0.14, kill.melee 0.5, kill.explosive 0.4, kill.buzzard 0.3 | 20 s | 20 |
| `murda` | It's Murda! | kill.headshot 0.3, kill.multi 0.6, kill.lastOfWave 1.0 (priority 75) | 25 s | 50 |
| `rulebaby` | Rule Baby! | reel.collected 0.9, wave.cleared 0.9, extraction.called 1.0, health.lowSurvived 0.4, objective.update 0.15; queues up to 2.5 s | 12 s | 60 |
| `inc` | I-N-C! | run.start 0.8, results.complete 1.0, results.holdout 1.0; queues up to 3 s | 20 s | 70 |
| `name` | What's my motherf\*\*\*in' name?! | run.win 1.0, kill.streak at 20 or more 1.0 | 60 s | 90, not interruptible |
| `rule_chant` (CROWD) | R-U-L-E! | only as the answer of `name`, 0.35 s after it | | 95 |

How often, by the options' **How often**: `off` silences every line; `rare` halves the chances and doubles the
cooldowns (1.6 x); `often` multiplies the chances by 1.6 and the cooldowns by 0.6, the global cooldown by 0.5.

**Expected rate in a typical Story run (normal).** Spec 04 2.10 gives 33 to 41 enemies on Boss in "about five
minutes", about 7 kills a minute in fights of a few kills. `MurderInc.Audio.VoiceRate` plays that run 20 times with
the real voice.json (36 kills over 300 s in twelve fights, a quarter headshots, five Buzzards, one melee and one blast
kill, three reels, two close calls, the truck, the debrief) and measures **2.6 lines a minute**, of which **1.3 a
minute on kills** (6.5 of 36 kills speak, 18 %); per run: Holla 3.6, Rule Baby 3.6, It's Murda 3.0, What's my name
and its crowd 1.0 each, I-N-C 0.8 at the start (and the outro when the debrief comes after the crowd's answer). The
progress beats (start, three reels, the truck, the win, the card) are about half of it and always land; the kill
barks stay under one kill in five, so they remain a reward. The test fails outside 1 to 3.5 lines a minute or if a
third of kills speak.

### 2.3 Clean language

`name` is flagged `profane`. With **clean language** on: mode `swap` (the default) plays the clean takes
`name_clean_*` ("What's my name?!") and shows that text; mode `bleep` plays the normal take, mutes it over each take's
`bleep` range (seconds) and plays a 1 kHz tone (`Gen/bleep_1k.wav`) there. Set the ranges once the real takes exist.

### 2.4 Per-character sets

`voice.json characters.<crew id>` holds each crew member's own lines (crew.json ids: `rule`, `deuce`, `smoke`,
`keys`). A member with no lines is silent: there is no fallback to Rule's voice. `SetCharacter` switches the set and
restarts the cooldowns. Files: `Content/Audio/Voice/<crew id>/`.

### 2.5 Adding or retuning a line

Everything is data (`voice.json`): add an entry under the character's `lines` with `text`, `priority`, `cooldown`,
`triggers` (trigger: chance, or `{chance, atLeast, priority}`), `takes` (files), and optional `queueable`,
`interruptible`, `answer`, `profane` + `clean`, `speaker`, `volume`. Put the WAV files in
`Content/Audio/Voice/<character>/`, run `tools/box/audio-import.sh` on the box. `MurderInc.Audio.VoiceData` checks
that the files exist (48 kHz mono) and that every trigger is a known one. New trigger kinds need a line in
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
| music | 0.45 | music | no | yes (thinned) | 0 |
| voice | 1.0 | voice | no | no | 0 |

Every frame the director computes each category's gain: volume x slider x master (0.8) x the ducks (gunfire 0.45,
NINE 0.55, 85 ms hold; enemy fire 0.85 on the ambience; blasts 0.4 / 0.6 with the music dip) x the voice duck x
states (ambience 0.6 title, 1 run, 0.7 dead, 0.8 debrief; x (1 - 0.55 x interior); the train duck) and the low-pass
cut-offs: the muffle `20000 x 0.03^m` (hits, blasts within 20 m, death settling at 0.85), the **low-health** state
(new: under 35 % health the muffled categories close toward 3.2 kHz, the music thins to 75 % and the ambience to
70 %, with the heartbeat loop of spec 07 3.22), and the **pause** state (world refused, music at 45 % behind 1.3 kHz).
The host applies them to every live component (`SetVolumeMultiplier`, `SetLowPassFilterFrequency`).

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
`bIsUISound` for UI and music, fades on stop), applies the mix, switches the reverb zone, and draws the subtitle.
A file with no asset is skipped (logged once, Verbose); a missing replacement layer falls back to the web sound.

## 5. The recording brief (for the real voice)

The placeholders are a **generic stock synthetic voice** (Higgsfield `seed_audio`, a preset voice; no cloning, no
reference audio, no released recording sampled). They exist so the system can be heard and tested; they are meant to
be replaced file for file.

**Deliver**: WAV, **48 kHz, 24-bit, mono**, clean and dry (no reverb, no music, no processing beyond a gentle
high-pass), close-miked (15 to 30 cm, pop filter), in a quiet treated room; 100 ms of silence before and 300 ms after
each take; peaks under -3 dBFS (the pipeline normalises loudness to -18 LUFS). **Three to five takes per line**, at
three intensities: **shouted** (full voice, across a street), **spoken** (confident, to someone close), **under the
breath** (low, raspy, to himself). Name the files exactly as below; take 01 shouted, 02 spoken, 03 under the breath,
04 and 05 free (add them to voice.json `takes`).

| File (Content/Audio/Voice/rule/) | Say | Notes |
|---|---|---|
| `holla_01.wav` ... `holla_05.wav` | "Holla, holla!" | the call-and-response chant; leave room for an answer |
| `murda_01.wav` ... `murda_05.wav` | "It's Murda!" | the signature, shouted at the start or end of a track |
| `rulebaby_01.wav` ... `rulebaby_05.wav` | "Rule Baby!" | the raspy self-hype ad-lib |
| `name_01.wav` ... `name_05.wav` | "What's my motherf\*\*\*in' name?!" | the full word as performed; mark where the word is (seconds) for the bleep mode |
| `name_clean_01.wav` ... `name_clean_03.wav` | "What's my name?!" | the clean-language version, same energy |
| `inc_01.wav` ... `inc_05.wav` | "I-N-C!" | the initials spelled, punchy, even spacing |
| `rule_chant_01.wav` ... `rule_chant_03.wav` | "R-U-L-E!" | a crowd or several background voices answering, about 1.6 to 2 s, a real group if possible (each take a different group mix) |

Then: copy the files over the placeholders, set `"placeholder": false` on those takes in voice.json (and the bleep
ranges), commit, and on the box `sync.sh`, `audio-import.sh`, `test.sh MurderInc.Audio` (VoiceData checks rate and
channels). The rights in the recordings are the user's to secure; nothing here samples or imitates any released
recording.

## 6. Generated material (Higgsfield) and what it cost

| What | Model | Files | Credits |
|---|---|---|---|
| Placeholder voice takes: 6 lines x 3 intensities + 3 clean takes + 6 stock voices for the crowd | `seed_audio` (preset voices, text to speech) | 18 takes + 3 crowd mixes (`tools/audio/voice_placeholders.py`: trim, mono, 48 kHz, -18 LUFS, crowd assembled on one chant grid with a short room) | 2.6 |
| Gun layers (CHOPPER and NINE close, mechanical, distant tails, silenced shots), dry fire, reload stages, casings on asphalt and concrete, impacts per surface, the Goon SMG at 30 m, the Buzzard's rotor loop and gun, explosions near and far, footsteps (asphalt, concrete, metal; walk and run), the El train, the hot-afternoon room tone | `mirelo_text_to_audio` | 79 files planned in `tools/audio/sfx_plan.json` (`tools/audio/sfx_process.py`: oneshot / tail / loop cuts, peak to the web sound's peak, 48 kHz 24-bit) | see PROGRESS.md |

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
  process has an audio device; result in PROGRESS.md.

## 8. Open issues

- The riser and impact of the music conductor (Quartz bar grid), the boombox at the reels, neon and steam emitters
  (the level's lamp and vent positions), the night far one-shot schedule (the day one plays at night too).
- Goon footsteps use one surface (asphalt) until the enemies' step event carries their surface.
- The engine's convolution reverb with `IR_street` / `IR_shop` instead of the algorithmic presets (needs Impulse
  Response assets).
- The options screen does not call `SetOptions` yet, and the options are not saved (FMISettings belongs to the
  gameplay package).
