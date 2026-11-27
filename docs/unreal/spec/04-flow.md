# 04 — Game flow, modes, waves, scoring and copy

Port spec for the Unreal Engine 5 rebuild of MURDER INC. The web game is the ground truth. Everything below was read
from the source files listed in 2.1. Statements marked **(verified)** were also observed by driving the shipped build
(`dist/index.html`) headless in fixed 1/30 s steps while logging every call and event of the flow; values marked
**(derived)** are typed nowhere in the source and were computed with the game's own functions. Verified times are
quantised to that step: a 1.5 s delay shows up as the first frame at or after 1.5 s.

How to read this document:

- Web units are metres, seconds and radians. +Y is up, north is −Z, east is +X. Yaw 0 faces −Z and grows
  counter-clockwise seen from above; forward = (−sin yaw, 0, −cos yaw) (`docs/CONTRACT.md:20`). Section 4 gives the
  Unreal values (cm, cm/s, degrees).
- "The flow" is the module `G.game` (`src/game.js`). A "run" is one attempt, from a reset to a death or debrief card.
  "B + G" means Buzzards + Goons.
- `damp(x, target, rate, dt)` = `target + (x − target) · e^(−rate · dt)`: 90 % of the way in 2.3 / rate seconds
  (`src/core/util.js:25`). `smoothstep(a, b, x)` is the cubic 0…1 step (`src/core/util.js:35`).
- Citations are `path:line`. Inside a table, `:NN` alone means the same file as the citation before it.
- Copy is quoted verbatim in code font. `—` is U+2014 (em dash), `·` is U+00B7 (middle dot), apostrophes are plain
  ASCII. `{name}` marks a value that is inserted at run time.
- The enemies themselves (senses, attacks, pools) are in `03-enemies.md`. This document only says who is spawned,
  where, when, and what the game does around the fight.

---------------------------------------------------------------------------------------------------

## 1. Overview

The flow is the director: it owns the state of the game and everything that happens around the shooting. The game
opens on a title screen laid over a slow camera flight through the living block. *Hit the block* fades up from black
at the foot of the El stairs, with a location card and a first radio line from the IPX dispatcher. In **Story** a small
patrol holds the block and does not know the player is there; the player finds three master reels (world markers,
minimap pins, a boombox leaking a loop), holds Interact for 2.4 s at each, and every reel taken back brings a banner
with the compass direction of a reinforcement wave that arrives already hunting, one member every 0.85 s. After the
third reel the objective becomes the IPX truck and a finite pursuit trickles in until the player steps into the zone
behind the truck: the doors open, a debrief card shows time, accuracy, kills, retries and a certification from Demo to
Diamond. In **Hold the Block** there are no reels: waves that grow in size and toughness arrive, each cleared wave
pays a bonus and a resupply, nine seconds of breathing space follow with a "Wave N in 3 … 2 … 1" countdown, and the run
ends only with death; the card shows waves cleared, kills, score and the locally saved best. Death shows a card after
1.5 s and every retry restarts the whole run: there are no checkpoints. Around all this the flow types out the
objective line, queues the radio subtitles, shows the interaction prompt, sets the music intensity (calm, alert, hot),
fades and desaturates the screen at the end, pauses when asked or when the game loses focus, and applies the chosen
difficulty (Hustler, Boss, Kingpin) at once.

---------------------------------------------------------------------------------------------------

## 2. Facts

### 2.1 Source map

| File | Lines | What it holds |
|---|---|---|
| `src/game.js` | 957 | The flow: state machine, run reset, interaction, spawn queue and pump, pursuit, extraction, the holdout loop, cards, music driver, event wiring |
| `src/game/waves.js` | 78 | Arrival orders, the record of a holdout wave, kill score, pursuit type |
| `src/game/spawn.js` | 66 | Compass sector, spawn-point score, spawn-point pick |
| `src/game/music.js` | 23 | Intensity rule and the "wave is over" rule |
| `src/game/radio.js` | 55 | Timing of the radio queue |
| `src/game/stats.js` | 35 | Accuracy and the data object of the cards |
| `src/game/titlecam.js` | 62 | Title fly-through camera |
| `src/game/intro.js` | 18 | Intro copy per mode |
| `src/config/flow.js` | 225 | Every flow number and formula |
| `src/config/text.js` | 222 | Player-facing copy |
| `src/config/quality.js` | 78 | Quality presets, auto-detection, dynamic resolution |
| `src/core/events.js` | 44 | The event bus |
| `src/core/settings.js` | 126 | Persisted settings and the best score |
| `src/core/contract.js` | 236 | Event names and payload keys as data (checked in dev builds) |
| `src/main.js`, `src/modules.js` | 390, 98 | Boot order, main loop, update groups |
| `src/hud.js`, `src/menus.js`, `src/ui/logic.js`, `src/ui/copy.js`, `src/ui/panel.js` | 814, 413, 437, 151, 305 | How the flow's calls are shown; copy that only the interface uses |
| `src/stubs/game.js` | 705 | A simplified stand-in flow. Not to be ported: see 3.21 |
| `test/flow-logic.test.js` | 372 | Unit tests of the pure rules: use its cases as test vectors |

### 2.2 Modes, keys and the public shape

| Thing | Value | Source |
|---|---|---|
| Modes (internal key → name on screen) | `mission` → `Story`, `holdout` → `Hold the Block` | `src/config/flow.js:6`, `src/config/text.js:47` |
| Difficulties | `hustler`, `boss`, `kingpin`; default `boss` | `src/config/flow.js:4`, `:5` |
| States | `title`, `intro`, `playing`, `paused`, `dead`, `complete` | `src/game.js:3`, `docs/CONTRACT.md:124` |
| `game.run` | `{time, reels, total, retries, wave, score, kills, shots, hits}`; `total` = number of objectives in the level (3) | `src/game.js:37`, `:214` |
| `game.holdout` | `{active, breakLeft, countdown, cleared, realertIn}` | `src/game.js:39` |
| `game.flow` (read-only view for tests) | `{queue, clock, maxAlive, pursuitLeft, pursuitTimer, music, lastWave: {order, from, at}, grabbing, progress}` | `src/game.js:41` |
| Calls | `start({mode, skipIntro, quick})`, `pause()`, `resume()`, `restart()`, `retry()`, `redeploy()`, `toTitle()`, `setDifficulty(name)`, `debugGrab()` (secures the next reel at once), `update(dt)` → live | `src/game.js:43` |
| Random numbers | `G.rng.fork('game')`: mulberry32 seeded with the FNV-1a hash of `"<seed>:game"`; seed 1994 unless URL `seed` | `src/game.js:32`, `src/core/rng.js:22`, `:52` |

### 2.3 State timings

All from `src/config/flow.js` (`timing`) unless another file is named.

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `intro` | 2.4 s | Intro of a start from the title (the "full" intro) | `src/config/flow.js:10` |
| `introQuick` | 1.1 s | Intro of retry / restart / redeploy | `:11` |
| `introFade` | [0.05, 1.3] s | Black to clear between these times; the end is capped by the intro length (so 0.05 → 1.1 s on a quick intro) | `:12` |
| `locationCardAt` | 0.25 s | Location card appears (full intro only) | `:13` |
| `introRadioAt` | 0.9 s | First radio line is queued (full intro only) | `:14` |
| `pauseDebounce` | 0.35 s | The pause key cannot resume before this much time on the pause card | `:15` |
| `deathCard` | 1.5 s | Death card appears this long after death | `:16` |
| `debriefCard` | 3.3 s | Debrief card appears this long after the truck is reached | `:17` |
| `lookHintEvery` / `lookHintSecs` | 6 s / 2.6 s | Browser-only mouse-capture hint (3.13) | `:18`, `:19` |
| Location card wipe | 1.1 s in 28 steps | The place line is revealed left to right | `src/menus.js:23`, `:24` |
| Menu focus delay | 30 ms | Primary button takes focus after a screen is shown | `src/menus.js:22` |
| Card veil / screen-in | 0.5 s / 0.45 s | CSS fades of the dim layer and of a card | `src/ui.css:983`, `:1029` |
| Boot screen fade | 700 ms | After `boot:done` | `src/main.js:37` |
| Frame step clamp | 0.05 s | `dt = min(real, 0.05)`: below 20 fps the game slows down | `src/main.js:34` |

### 2.4 Screen treatment at the end of a run

`render.post.fade` is the share of black over the picture (0 clear … 1 black); `render.post.saturation` is 1 for normal
colour. In the two end states the flow eases both with `damp` every frame (`src/game.js:757`).

| State | Saturation target, rate | Fade target, rate | 90 % reached after (derived) | Source |
|---|---|---|---|---|
| `dead` | 0.12, 2.2 /s | 0.55, 1.4 /s | 1.05 s, 1.64 s | `src/config/flow.js:24` |
| `complete` | 0.7, 1.4 /s | 0.72, 1.2 /s | 1.64 s, 1.92 s | `src/config/flow.js:25` |

**(verified)** one second after death: fade 0.414, saturation 0.218. The dead targets are written a second time in
`src/config/player.js:155` and `:156`, and the title camera's angle (2.5) in `src/config/player.js:80`; no code reads
those copies.

### 2.5 Title fly-through camera

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `minLoop` | 26 s | Loop length = max(26, path length / speed) | `src/config/flow.js:30` |
| `speed` | 1.15 m/s | Mean speed along the path | `:31` |
| `fov` | 50° (vertical) | Camera field of view on the title | `:32` |
| `fadeIn` / `fadeOut` | 1.8 s / 1.6 s | From black at the loop start, to black at its end | `:33`, `:34` |
| `ease` | 0.25 | Progress = 0.25 × smoothstep + 0.75 × linear | `:35` |
| `sway` | rate 0.42 rad/s, side 0.07 m, lift 0.04 m, roll 0.005 rad | "A hand-held breath" | `:36` |
| Path | 14 authored keys `{pos, look}` | Start → reel 1 → shop → alley → avenue → cage → lot → truck | `src/level/data.js:153` |
| Path length **(derived)** | 155.54 m | Centripetal Catmull-Rom through the 14 positions | `src/game/titlecam.js:16` |
| Loop length **(derived)** | 135.25 s | 155.54 / 1.15 | `src/game/titlecam.js:20` |
| Camera speed **(derived)** | 0.84 … 1.42 m/s | Ease and sway included | |

### 2.6 Interaction: holding Interact on a master reel

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `range` | 2.2 m | Horizontal distance, player feet to reel | `src/config/flow.js:41` |
| `vertical` | 2.5 m | Largest height difference, feet to reel base | `:42` |
| `facingDot` | 0.45 | Horizontal facing must be within acos(0.45) = 63.3° of the reel… | `:43` |
| `freeRange` | 0.9 m | …unless the player is this close | `:44` |
| `hold` | 2.4 s | Time to fill the bar | `:45` |
| `decay` | 1.6 /s | Bar lost per second while not holding (a full bar drains in 0.625 s) | `:46` |
| `shake` | 0.18 | Camera trauma added when a reel is secured | `:47` |

### 2.7 Extraction

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `radius` | 2.5 m | Horizontal radius of the zone; copied into `level.extraction.radius` | `src/config/flow.js:51`, `src/level.js:106` |
| `vertical` | 3.5 m | Largest height difference, feet to zone | `src/config/flow.js:52` |
| `refuseSecs` | 3.5 s | How long the refusal message stays | `:53` |
| `refuseEvery` | 8 s | Shortest time between two refusal messages | `:54` |

### 2.8 Spawn selection and the arrival pump

All from `src/config/flow.js` (`spawn`).

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `firstDelay` | 1.6 s | First member of a story wave arrives this long after the reel is secured | `src/config/flow.js:59` |
| `stagger` | 0.85 s | Then one member every this long | `:60` |
| `far` | 18 m | Preferred minimum distance from the player for reinforcements | `:61` |
| `patrolMinDistance` | 32 m | Same for the starting patrol (strict) | `:62` |
| `score.random` | 1.5 | Score: + uniform 0 … 1.5 | `:64` |
| `score.far` | 2 | + 2 when at least the minimum distance away… | `:65` |
| `score.farExtra`, `farExtraOver` | 0.5, 30 m | …plus up to 0.5 more, linear over the next 30 m | `:66`, `:67` |
| `score.nearDivisor` | 4 | Closer than the minimum: − (shortfall in metres) / 4 | `:68` |
| `score.hidden` | 2.5 | + 2.5 when the player cannot see the point | `:69` |
| `score.recent`, `recentSecs` | −3, 6 s | − 3 when the point was picked in the last 6 s | `:70`, `:71` |
| `jitter` | 1.2 m | Uniform ± on x and z after the pick | `:73` |
| `airMinHeight`, `airLift` | 2.5 m, [6, 9] m | An air position lower than 2.5 m is lifted to a random 6 … 9 m | `:74`, `:75` |
| `eyeHeight`, `probeHeight` | 1.6 m, 1.2 m | Sight check runs from this high above the player's feet to this high above a ground point | `:76`, `:77` |
| `tooClose` | 9 m | A queued ground position this near the player at arrival time is picked again | `:78` |
| `capRetry` | 1 s | A due arrival waits this long while the alive cap is reached | `:79` |
| `poolRetry`, `poolTries` | 1.5 s, 6 | Wait after the enemy pool refused a spawn; dropped after 6 refusals | `:80`, `:81` |
| `alertRadius` | 60 m | Each arrival alerts every enemy within this distance of the player | `:82` |
| `fallbackRing` | 26 m | Ring around the player used only when the level has no authored points | `:83` |
| `bannerSecs` | 3.4 s | "Contact — {DIRECTION}" banner | `:84` |

### 2.9 Pursuit (Story, after the third reel)

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `firstDelay` | 12 s | First pursuit check this long after the third reel | `src/config/flow.js:89` |
| `minAlive` | 4 | One more arrives only while fewer than this are alive and nothing is queued | `:90` |
| `spawnDelay` | 0.5 s | Delay of a pursuit arrival after it is queued | `:91` |
| `buzzardShare` | 0.35 | Each arrival is a Buzzard with probability 0.35, else a Goon | `:92` |
| `realertEvery`, `realertRadius` | 4 s, 90 m | Otherwise: everyone within 90 m of the player is sent after him, and the check repeats in 4 s | `:93`, `:94` |
| Interval and budget | per difficulty | 2.10 | `src/config/flow.js:111`, `:112` |

### 2.10 Difficulty tiers

Display names: `Hustler`, `Boss`, `Kingpin` (`src/config/text.js:59`). Flow side (`src/config/flow.js:101`):

| Value | Hustler | Boss (default) | Kingpin | Source |
|---|---|---|---|---|
| Player health regeneration: delay after the last hit / rate | 4 s / 25 HP/s | 5.5 s / 16 HP/s | 7 s / 10 HP/s | `src/config/flow.js:103`, `:115`, `:127` |
| Starting patrol B + G (unaware) | 1 + 3 | 2 + 4 | 2 + 5 | `:104`, `:116`, `:128` |
| Wave after reel 1, B + G | 2 + 3 | 2 + 5 | 3 + 6 | `:106`, `:118`, `:130` |
| Wave after reel 2, B + G | 2 + 4 | 3 + 6 | 4 + 7 | `:107`, `:119`, `:131` |
| Wave after reel 3, B + G | 3 + 5 | 4 + 7 | 5 + 8 | `:108`, `:120`, `:132` |
| Alive cap (both types together) | 9 | 11 | 13 | `:110`, `:122`, `:134` |
| Pursuit: seconds between arrivals | 7 | 5.5 | 4.5 | `:111`, `:123`, `:135` |
| Pursuit: budget (arrivals in total) | 5 | 8 | 12 | `:112`, `:124`, `:136` |
| Enemies in a whole Story run without / with the full pursuit **(derived)** | 23 / 28 | 33 / 41 | 40 / 52 | |
| Last member of wave 1 / 2 / 3 arrives after **(derived)** | 5.0 / 5.85 / 7.55 s | 6.7 / 8.4 / 10.1 s | 8.4 / 10.1 / 11.8 s | 1.6 + (count − 1) × 0.85 |

Enemy side, applied by the same call (`src/game.js:176`; authoritative table and meaning in `03-enemies.md` 2.2):

| Value | Hustler | Boss | Kingpin | Source |
|---|---|---|---|---|
| Buzzard HP / bolt damage / telegraph s / cooldown s | 45 / 7 / 0.55 / 1.9–3.3 | 55 / 10 / 0.46 / 1.4–2.5 | 60 / 13 / 0.38 / 1.0–1.9 | `src/config/enemies.js:244`, `:249`, `:254` |
| Buzzard spread far → near, rad | 0.065 → 0.018 | 0.052 → 0.016 | 0.042 → 0.014 | same lines |
| Goon HP / round damage / rounds per burst / cooldown s | 90 / 4 / 4 / 1.8–3.0 | 110 / 6 / 5 / 1.4–2.4 | 130 / 8 / 6 / 1.0–1.9 | `src/config/enemies.js:245`, `:250`, `:255` |
| Goon spread far → near, rad | 0.12 → 0.045 | 0.095 → 0.038 | 0.08 → 0.032 | same lines |
| Goon pipe damage / run speed | 15 / 4.5 m/s | 22 / 5.0 m/s | 30 / 5.4 m/s | same lines |
| Attack tokens normal / crowd, gap | 2 / 3, 1.25 s | 3 / 4, 0.85 s | 4 / 5, 0.6 s | `src/config/enemies.js:246`, `:251`, `:256` |
| Accuracy gain per second in sight | 0.10 | 0.14 | 0.18 | same lines |

Hard caps that the flow runs into: 12 Goon slots (living, dying and bodies share them) and 8 Buzzard slots
(`src/config/enemies.js:12`).

### 2.11 Hold the Block

All from `src/config/flow.js` (`holdout`); n is the wave number, starting at 1.

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `firstDelay` | 3.5 s | Run clock at which wave 1 starts (the intro counts) | `src/config/flow.js:142` |
| `breather` | 9 s | Pause between a cleared wave and the next | `:143` |
| `countdownFrom` | 3 | "Wave {n} in 3 / 2 / 1" during the last three seconds of a breather | `:144` |
| `firstSpawn` | 1.2 s | First member arrives this long after the wave starts | `:145` |
| `bannerSecs` | 3.6 s | "Wave {n} — {DIRECTION}" banner | `:146` |
| `realertEvery`, `realertRadius` | 5 s, 90 m | Once the whole wave is out, everyone within 90 m is sent after the player this often | `:147`, `:148` |
| `total(n)` | min(5 + 2n, 30) | Members of wave n | `:149` |
| `buzzardShare(n)` | max(0.25, 0.45 − 0.02n) | Buzzards = min(total, round(total × share)), halves round up | `:150`, `src/game/waves.js:58` |
| `stagger(n)` | max(0.35, 0.9 − 0.04n) s | One member every this long | `src/config/flow.js:151` |
| `hpScale(n)` | min(2.5, 1 + 0.07 (n − 1)) | × enemy HP, for units spawned from then on | `:153` |
| `damageScale(n)` | min(2, 1 + 0.05 (n − 1)) | × enemy damage, at once | `:154` |
| `cooldownScale(n)` | max(0.6, 1 − 0.03 (n − 1)) | × enemy cooldown, at once | `:155` |
| `extraAlive(n)` | min(5, floor(n / 2)) | Added to the difficulty's alive cap | `:156` |
| `score.buzzard`, `score.goon` | 100, 150 | Base points per kill | `:158`, `:159` |
| `score.killScale(wave)` | 1 + 0.1 (wave − 1) | Kill points = round(base × this) | `:160`, `src/game/waves.js:72` |
| `score.waveClear(wave)` | 500 × wave | Bonus for clearing a wave | `src/config/flow.js:161` |
| `resupply.reserve`, `reserveCap` | 90, 240 | Chopper reserve rounds added per cleared wave, up to 240 (a run starts with 150: `src/config/weapons.js:12`) | `src/config/flow.js:164`, `:165` |
| `resupply.heal` | 35 HP | Healed per cleared wave | `:166` |
| `resupply.explosivesEvery` | 2 | Every propane tank and welding rack comes back after each even wave | `:167` |

Worked values **(derived with `holdoutWave`, `killScore`; rows 1, 5, 10 and the caps are also unit-tested in
`test/flow-logic.test.js:60`)**. "Last arrival" is seconds after the wave starts, with no cap delays. "Best total" is
the score after clearing wave n having killed everything.

| n | Total | B | G | Stagger s | Last arrival s | HP × | Damage × | Cooldown × | Cap + | Kill B / G | Clear bonus | Best total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 7 | 3 | 4 | 0.86 | 6.36 | 1.00 | 1.00 | 1.00 | 0 | 100 / 150 | 500 | 1,400 |
| 2 | 9 | 4 | 5 | 0.82 | 7.76 | 1.07 | 1.05 | 0.97 | 1 | 110 / 165 | 1,000 | 3,665 |
| 3 | 11 | 4 | 7 | 0.78 | 9.00 | 1.14 | 1.10 | 0.94 | 1 | 120 / 180 | 1,500 | 6,905 |
| 4 | 13 | 5 | 8 | 0.74 | 10.08 | 1.21 | 1.15 | 0.91 | 2 | 130 / 195 | 2,000 | 11,115 |
| 5 | 15 | 5 | 10 | 0.70 | 11.00 | 1.28 | 1.20 | 0.88 | 2 | 140 / 210 | 2,500 | 16,415 |
| 6 | 17 | 6 | 11 | 0.66 | 11.76 | 1.35 | 1.25 | 0.85 | 3 | 150 / 225 | 3,000 | 22,790 |
| 7 | 19 | 6 | 13 | 0.62 | 12.36 | 1.42 | 1.30 | 0.82 | 3 | 160 / 240 | 3,500 | 30,370 |
| 8 | 21 | 6 | 15 | 0.58 | 12.80 | 1.49 | 1.35 | 0.79 | 4 | 170 / 255 | 4,000 | 39,215 |
| 9 | 23 | 6 | 17 | 0.54 | 13.08 | 1.56 | 1.40 | 0.76 | 4 | 180 / 270 | 4,500 | 49,385 |
| 10 | 25 | 6 | 19 | 0.50 | 13.20 | 1.63 | 1.45 | 0.73 | 5 | 190 / 285 | 5,000 | 60,940 |
| 11 | 27 | 7 | 20 | 0.46 | 13.16 | 1.70 | 1.50 | 0.70 | 5 | 200 / 300 | 5,500 | 73,840 |
| 12 | 29 | 7 | 22 | 0.42 | 12.96 | 1.77 | 1.55 | 0.67 | 5 | 210 / 315 | 6,000 | 88,240 |
| 13 | 30 | 8 | 22 | 0.38 | 12.22 | 1.84 | 1.60 | 0.64 | 5 | 220 / 330 | 6,500 | 103,760 |
| 14 | 30 | 8 | 22 | 0.35 | 11.35 | 1.91 | 1.65 | 0.61 | 5 | 230 / 345 | 7,000 | 120,190 |
| 15 | 30 | 8 | 22 | 0.35 | 11.35 | 1.98 | 1.70 | 0.60 | 5 | 240 / 360 | 7,500 | 137,530 |

Caps are reached at: total 30 from n = 13; Buzzard share 0.25 from n = 10; stagger 0.35 from n = 14; cooldown 0.6 from
n = 15; damage 2.0 from n = 21; HP 2.5 from n = 23; extra alive 5 from n = 10. Kill points keep growing by 10 / 15 per
wave without a cap.

### 2.12 Rating (debrief certification)

| Rule | Points | Source |
|---|---|---|
| `run.time` under 270 s | 2 | `src/config/flow.js:174` |
| else `run.time` under 400 s | 1 | `:175` |
| accuracy (hits / shots) at least 0.5 | 2 | `:178` |
| else accuracy at least 0.3 | 1 | `:179` |
| no shot fired | 0 for accuracy | `:196` |
| `run.retries` is 0 | 1 | `:181`, `:203` |

Sum 0 … 5 → name: 0 `Demo`, 1 `Mixtape`, 2 `Single`, 3 `Gold`, 4 `Platinum`, 5 `Diamond`
(`src/config/text.js:188`, `src/config/flow.js:188`). Test vectors: `test/flow-logic.test.js:205`.

### 2.13 Music-intensity driver

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `calm` | 0.15 | Also title, death card, debrief card | `src/config/flow.js:209` |
| `alert` | 0.6 | | `:210` |
| `hot` | 1 | | `:211` |
| `alertHold` | 10 s | Alert for this long after any `enemy:alert` | `:212` |
| `hitHold` | 8 s | …or after the player was hit | `:213` |
| `nearDistance` | 26 m | …or while a living enemy is closer than this | `:214` |
| `waveHot` | 30 s | Hot for this long after a wave was queued, while anything is alive | `:215` |
| `waveMinOut` | 6 s | That window ends once the wave is at least this old and nothing is alive or queued | `:216` |

### 2.14 Text pacing and HUD timers the flow relies on

| What | Value | Source |
|---|---|---|
| Radio typewriter | 58 characters/s | `src/config/flow.js:221`, `src/hud.js:42` |
| Silence between two radio lines | 0.3 s | `src/config/flow.js:224` |
| Objective typewriter | 46 characters/s | `src/config/flow.js:222`, `src/hud.js:41` |
| Objective change flash | 900 ms: the rule and the badge edge go from white to gold | `src/hud.js:714` |
| Countdown message | 1 s each | `src/config/flow.js:223` |
| Banner | at least 3.4 s; fades up over the first 8 %, one flicker down to 35 % opacity at 14 %, solid from 20 % to 82 %, then out; the letters start 22 % wider and close up over the first 20 % | `src/hud.js:46`, `:765`, `:598`, `src/ui/logic.js:131` |
| Centre message | stays the given time, 3 s when none is given; a new one replaces the old | `src/hud.js:769` |
| Kill feed | 4 lines at most, 4.2 s each, fading over the last 0.6 s | `src/hud.js:176`, `src/ui/logic.js:364` |
| World markers | 5 at most; hidden within 3 m; anchored 1.9 m above a reel and 1.2 m above the exit point; hidden while aiming down sights | `src/hud.js:45`, `:461`, `:473`, `:421` |

### 2.15 Authored level data the flow consumes

Positions are (x, y, z) in web space. Ground heights come from `floorAt`: 0 on the road, 0.15 on a sidewalk
(`src/level/layout.js:187`, `:23`).

| What | Value | Source |
|---|---|---|
| Player start | (−37.4, 0.15, 8.15), yaw −π/2 + 0.08 rad: facing east, 4.6° toward north | `src/level/data.js:7`, `src/level.js:186` |
| Reel 1: id `reel1`, code `1`, label `Reel 1 — The Avenue`, zone `avenue` | (−4, 0, 1) | `src/level/data.js:11`, `src/config/text.js:75` |
| Reel 2: id `reel2`, code `2`, label `Reel 2 — Chop Shop`, zone `shop` | (−9.5, 0, −21.5) | `src/level/data.js:12`, `src/config/text.js:76` |
| Reel 3: id `reel3`, code `3`, label `Reel 3 — The Cage`, zone `lot` | (35.25, 0, −22.5) | `src/level/data.js:13`, `src/config/text.js:77` |
| Extraction zone: label `IPX truck`, code `IPX` | centre (35.9, 0, 29.7), radius 2.5 m | `src/level/data.js:18`, `src/level.js:104`, `src/config/text.js:81` |
| IPX truck | centre (41.3, 0, 29.7), nose east; 6.8 × 3.0 × 2.5 m (length, height, width). The zone centre is 2.0 m behind its rear doors | `src/level/data.js:17`, `src/config/catalog.js:77` |
| Enemy spawn points, ground | 29: 7 in zone `shop`, 12 in `avenue`, 10 in `lot`, none in `west` **(derived)**; 23 of them are at least 32 m from the start | `src/level/data.js:24`, `src/level.js:135` |
| Enemy spawn points, air | 17: 4 `shop`, 6 `avenue`, 7 `lot`; 8.6 … 16.2 m high **(derived)**; 14 are at least 32 m from the start | `src/level/data.js:60`, `src/level.js:136` |
| Title path | 14 keys `[x, y, z, lookX, lookY, lookZ]` (4.3 lists them) | `src/level/data.js:153` |
| Play bounds | x −46 … 46, z −34 … 34 | `src/level/layout.js:21` |
| Zones | `west` x −46 … −30; `shop` x −30 … 22, z −34 … −11; `avenue` x −30 … 22, z −11 … 34; `lot` x 22 … 46 | `src/level/layout.js:158` |
| Distances **(derived)** | start → reel 1: 34.2 m; reel 3 → extraction: 52.2 m | |

Ground spawn points and cover points that end up inside an obstacle's margin are moved to the nearest walkable nav cell
when the level is built (`src/level.js:176`), so the exported positions, not the table in `data.js`, are the ones to use.

### 2.16 User settings and what is stored

Stored as one JSON object in `localStorage['murderinc.settings.v1']` (`src/core/settings.js:4`, `:99`). On load every
key is validated on its own and an unusable value falls back to the default (`:75`). `settings.set(key, value)`
validates and clamps, saves, and emits `settings:change {key, value}` only when the value really changed; it returns
false and changes nothing for a value that cannot be used (`:92`). **(verified)**: `fov` 200 is stored as 95, `fov`
74.6 as 75, `sens` 0.01 as 0.2, `volume` 2 as 1, `view` `'2'` as 2, and `quality` `'test'` is rejected.

| Key | Default | Accepted | Control (label, options, display) | Applied by, when | Source |
|---|---|---|---|---|---|
| `mode` | `mission` | `mission`, `holdout` | Title picker `Mode`: `Story` / `Hold the Block`. Title screen only | The flow reads it at the next start from the title; `game.mode` follows at once while on the title | `src/core/settings.js:14`, `:35`, `src/menus.js:107`, `src/game.js:267`, `:914` |
| `difficulty` | `boss` | `hustler`, `boss`, `kingpin` | Title picker `Difficulty` and drawer row `Difficulty`: `Hustler` / `Boss` / `Kingpin` | The flow, at once, also in the middle of a run (3.18) | `src/core/settings.js:13`, `:34`, `src/menus.js:108`, `src/ui/panel.js:135`, `src/game.js:913` |
| `time` | `day` | `day`, `night` | Title picker `Time`: `Day` / `Night`. Title screen only | At once while on the title; otherwise at the next run reset | `src/core/settings.js:16`, `:37`, `src/menus.js:109`, `src/game.js:188`, `:915`, `src/atmos.js:311` |
| `quality` | `auto` | `auto`, `low`, `medium`, `high`, `ultra` | Drawer `Graphics quality`: `Auto` / `Low` / `Medium` / `High` / `Ultra`; with Auto the tier that was picked shows pressed too | Renderer, at once (2.17) | `src/core/settings.js:8`, `:29`, `src/ui/panel.js:137`, `src/render.js:793` |
| `sens` | 1 | number, clamped to 0.2 … 3 | Drawer slider `Look sensitivity`, step 0.05 (gamepad 0.1), shown as `1.00×` | Input, at once | `src/core/settings.js:9`, `:30`, `src/ui/panel.js:12`, `src/input.js:1168` |
| `invertY` | false | boolean | Drawer toggle `Invert Y`: `On` / `Off` | Input, at once | `src/core/settings.js:10`, `:31`, `src/ui/panel.js:139`, `src/input.js:1169` |
| `volume` | 0.8 | number, clamped to 0 … 1 | Drawer slider `Master volume`, 0 … 100 in steps of 1 (gamepad 5), shown as `80%` | Audio master gain, at once | `src/core/settings.js:11`, `:32`, `src/ui/panel.js:13`, `src/audio.js:866` |
| `fov` | 74 | number, clamped to 60 … 95 and rounded to a whole degree | Drawer slider `Field of view`, step 1, shown as `74°` | Player camera, at once. This is the **vertical** field of view | `src/core/settings.js:12`, `:33`, `src/ui/panel.js:14`, `src/player.js:684` |
| `view` | 1 | 1, 2, 3 | Drawer `Weapon position`: `Close` / `Three-quarter` / `Compact` | Weapon viewmodel, at once | `src/core/settings.js:15`, `:36`, `src/ui/panel.js:136`, `src/weapon.js:43` |

Best Hold the Block score: `localStorage['murderinc.holdout.best']`, an integer as text (`src/core/settings.js:5`).
`settings.best()` = the larger of the stored value and the best of this session (so a record still counts when storage
is blocked) (`:111`); `settings.setBest(n)` rounds n, stores it only when it beats the best, and returns true for a new
record (`:117`). It is one number for all three difficulties and both times of day.

The drawer also has a `Display` row with `Enter fullscreen` / `Exit fullscreen` (not a stored setting,
`src/ui/panel.js:115`). Debug switches that are URL parameters, not settings: `autostart`, `mode`, `shot`, `q`, `seed`,
`eseed`, `god`, `noaudio`, `nohud`, `cam`, `fov`, `exposure`, `post`, `bloom`, `dynres`, `step`, `dt`
(`docs/DEV.md:112`).

### 2.17 The quality presets behind the `quality` setting

| Preset | Render scale | MSAA | Shadow map | Shadow redraw every | Bloom | Real lamp lights | Particle budget × | Pixel cap | Max device pixel ratio | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| `test` (screenshots only, not selectable) | 1 | 0 | 1024 | 1 frame | on | 4 | 0.4 | 1.0 M | 1 | `src/config/quality.js:15` |
| `low` | 0.7 | 0 | 2048 | 2 frames | on | 4 | 0.5 | 1.0 M | 1.5 | `:16` |
| `medium` | 0.85 | 2 | 2048 | 2 frames | on | 6 | 0.8 | 1.5 M | 2 | `:17` |
| `high` | 1 | 4 | 4096 | 2 frames | on | 8 | 1 | 2.3 M | 2 | `:18` |
| `ultra` | 1 | 4 | 4096 | 1 frame | on | 12 | 1 | 3.7 M | 2 | `:19` |

- `auto` picks: `low` for a phone, a small touch screen (short side under 900 px) or a software rasteriser; `medium`
  for mobile-class GPUs (Mali, Adreno, PowerVR) and Intel graphics other than Arc; `high` otherwise; `ultra` is never
  picked automatically (`src/config/quality.js:37`). An unknown name falls back to `medium` (`:26`).
- Dynamic resolution (`src/config/quality.js:55`): the internal scale moves between 0.6 and 1 in steps of 0.1: down
  when the mean frame time of a window (45 frames or 900 ms) is above 21.5 ms (two steps above 30 ms, straight to 0.6
  above 45 ms), up again below 17.4 ms. With `auto`, two windows in a row above 26 ms at scale 0.6 drop one preset
  down the ladder low ← medium ← high ← ultra (`:23`) and emit `quality:auto {name}` (`src/render.js:705`). Frame times
  are only measured in `intro` and `playing` (`src/render.js:711`).

### 2.18 The event bus: every event

`G.events` is a synchronous publish / subscribe bus: `on(name, fn)` returns an unsubscribe function and
`emit(name, payload)` calls every handler at once, in subscription order, each one isolated by try / catch
(`src/core/events.js:9`, `:25`). The names and payload keys are fixed by `docs/CONTRACT.md:119` and exist as data in
`src/core/contract.js:133`; dev builds report any payload that lacks a documented key (`src/main.js:85`). "Flow" in
the last column says what the flow does with the event; a dash means it does not listen.

| Event | Payload | Emitted by | When | Flow |
|---|---|---|---|---|
| `boot:done` | `{}` | `src/main.js:366` | Every module exists and the level is ready | – |
| `settings:change` | `{key, value}` | `src/core/settings.js:100` | A setting changed value | Applies `difficulty`, `mode`, `time` (`src/game.js:912`) |
| `game:state` | `{state, prev}` | `src/game.js:153` | Every state change; `prev` is null for the first `title` | Emits |
| `game:reset` | `{mode}` | `src/game.js:242` | Last step of every run reset | Emits |
| `input:lock` | `{locked, mode}`, mode `lock` or `drag` | `src/input.js:364` | Mouse capture gained or lost, or the look mode changed | Pauses when a capture it once had is lost (`src/game.js:919`) |
| `input:device` | `{device}`: `kbm`, `pad`, `touch` | `src/input.js:286` | The active device changed | – (the prompt glyph is re-read every frame) |
| `ui:click` | `{}` | `src/menus.js:56`, `:81`, `src/hud.js:282`, `:286`, `:298`, `src/ui/panel.js:29`, `:94` | Any menu or HUD button press, a slider let go | – |
| `ui:hover` | `{}` | `src/menus.js:68`, `:341`, `:356`, `:367` | Pointer enters a button; gamepad moves the focus | – |
| `player:step` | `{pos, surface, sprint}` | `src/player.js:612` | Every footfall | – |
| `player:jump` | `{}` | `src/player.js:490` | Jump starts | – |
| `player:land` | `{speed, surface}` | `src/player.js:596` | Landing | – |
| `player:hit` | `{amount, from, health, kind}`, kind `bullet`, `bolt`, `melee`, `blast`, `fall` | `src/player.js:356` | Every damage the player takes | Restarts the 8 s "hit" hold of the music (`src/game.js:895`) |
| `player:dead` | `{from}` | `src/player.js:372` | Health reached 0 (always right after `player:hit`) | Goes to `dead` (`src/game.js:879`) |
| `player:hitEnemy` | `{enemy, part, killed, damage, weapon}` | `src/combat.js:205`, `:301` | A player round or melee strike hit an enemy | – |
| `weapon:fire` | `{weapon, pos, dir, ads}` | `src/weapon/logic.js:479` | Every round fired | – |
| `weapon:reload` | `{weapon, phase, empty}`, phase `start`, `magout`, `magin`, `bolt`, `done`, `cancel` | `src/weapon/logic.js:285` | Reload steps | – |
| `weapon:dry` | `{weapon}` | `src/weapon/logic.js:507` | Trigger on an empty magazine | – |
| `weapon:switch` | `{from, to, phase}`, phase `holster`, `draw` | `src/weapon/logic.js:331` | Weapon swap steps | – |
| `weapon:swing` | `{weapon}` | `src/weapon/logic.js:390` | A melee strike starts | – |
| `weapon:melee` | `{hit}` | `src/weapon/logic.js:408` | The blow lands, 0.16 s into the strike | – |
| `shell:bounce` | `{pos, surface}` | `src/fx.js:304` | An ejected case hits the ground | – |
| `impact` | `{point, normal, surface, dir, from, enemy}`, from `player` or `enemy` | `src/combat.js:204`, `:217`, `:227`, `:300`, `src/enemies/bolts.js:118` | A round, bolt or strike hits the world, an explosive or an enemy (never emitted for hits on the player) | – |
| `explosion` | `{pos, radius, size, source}`, size `small` or `big` | `src/combat.js:323` | Any blast | – |
| `explosive:lit` | `{item, pos}` (+ `fuse`, seconds) | `src/explosives.js:355` | A tank or rack starts to burn | – |
| `explosive:blast` | `{item, pos}` | `src/explosives.js:416` | It blows | – |
| `enemy:spawn` | `{enemy}` | `src/enemies.js:321` | A unit is placed | – |
| `enemy:alert` | `{enemy, pos}` | `src/enemies.js:196`, `:212` | A unit starts engaging, or an unaware unit is sent to look | Restarts the 10 s "alert" hold of the music; the first one while `playing` queues the contact radio line (`src/game.js:899`) |
| `enemy:telegraph` | `{enemy, type, duration, pos}` | `src/enemies/goon.js:816`, `src/enemies/buzzard.js:687` | Before every burst or volley | – |
| `enemy:fire` | `{enemy, type, pos, dir}` | `src/enemies/goon.js:631`, `src/enemies/buzzard.js:639` | Every enemy round or bolt | – |
| `enemy:melee` | `{enemy, phase, pos}`, phase `windup`, `strike` | `src/enemies/goon.js:642`, `:649` | A Goon's pipe rush | – |
| `enemy:hit` | `{enemy, part, damage, point}` | `src/enemies.js:429` | Every damaging hit on an enemy | – |
| `enemy:killed` | `{enemy, type, pos, part, byPlayer, weapon}` | `src/enemies.js:451` | An enemy dies; `byPlayer` is true for player rounds, melee and every blast | Adds the Hold the Block kill score (`src/game.js:906`) |
| `enemy:step` | `{enemy, pos, surface}` | `src/enemies/goon.js:994` | A Goon footfall near the player | – |
| `objective:progress` | `{id, t}`, t 0 … 1 | `src/game.js:547` | Every frame while a reel's bar is filling or draining (one reused object) | Emits |
| `objective:done` | `{id, index, total}` | `src/game.js:608`, `:704` | A reel is secured: `index` = reels secured so far. A holdout wave is cleared: `id` is `wave`, `index` = `total` = the wave number | Emits |
| `objective:all` | `{}` | `src/game.js:621` | The last reel is secured | Emits |
| `extraction:reached` | `{}` | `src/game.js:666` | The player reaches the truck with every reel | Emits |
| `holdout:wave` | `{wave, count}` | `src/game.js:688` | A holdout wave starts; `count` = its members | Emits |
| `radio:line` | `{speaker, text, secs}` | `src/game.js:119` | A radio line starts | Emits |
| `train:pass` | `{phase, duration}` (+ `dir`), phase `approach`, `over`, `gone` | `src/atmos/train.js:307` | The El train, three times per pass | – |
| `quality:auto` | `{name}` | `src/render.js:705` | The renderer dropped a preset by itself | – |
| `render:lost` | `{}` | `src/render.js:1004` | The graphics context is gone | Pauses (`src/game.js:930`) |
| `render:restored` | `{}` | `src/render.js:1022` | It is back | – |

### 2.19 Every user-facing string

One table for all copy. "Shown" says where and when; "not shown" means the string exists in the copy deck and no
screen displays it today. Lettering painted in the world (shop signs, stencils, graffiti, posters) is level art and is
listed with the level, except the storefront names, which come from the copy deck.

| Key | Text (verbatim) | Shown | Source |
|---|---|---|---|
| `title.eyebrow` | `IPX PRESENTS · HOLLIS, QUEENS` | Title: the IPX lozenge, then `PRESENTS · HOLLIS, QUEENS` | `src/config/text.js:7`, `src/menus.js:117` |
| `title.wordmark` | `MURDER INC.` | Title wordmark; boot screen | `src/config/text.js:8` |
| `title.star` | `STARRING JA RULE` | Title | `:9` |
| `title.premise` | `The Vultures jacked three master reels. Take the block back. Get them to the truck.` | Title | `:10` |
| `title.note` | `Every street, sound and beat is generated in your browser. No art or audio files.` | Title foot; boot screen | `:11` |
| `title.start` | `Hit the block` | Title, primary button | `:12` |
| `title.settings`, `title.controls` | `Settings`, `Controls` | Title buttons | `:13`, `:14` |
| `location.byTime.day` | `Hollis, Queens · Jamaica Ave · 4:15 PM` | Location card, line 1, by day (a no-break space is put before `PM`) | `:27`, `src/menus.js:311` |
| `location.byTime.night` | `Hollis, Queens · Jamaica Ave · 02:14 AM` | Location card, line 1, by night | `src/config/text.js:28` |
| `location.tagline` | `Three reels. One block. No backup.` | Location card, line 2, Story | `:23` |
| `location.taglineHoldout` | `One block. Endless Vultures.` | Location card, line 2, Hold the Block | `:25` |
| `zones.*` | `WEST END`, `THE AVENUE`, `CHOP SHOP`, `THE LOT`, `THE CAGE` | Band under the minimap (3.16) | `:37` |
| `modes.mission.name` | `Story` | Title mode picker | `:49` |
| `modes.mission.note` | `Take back three master reels and reach the IPX truck. About five minutes.` | Title, under the pickers while Story is selected | `:50` |
| `modes.holdout.name` | `Hold the Block` | Title mode picker | `:53` |
| `modes.holdout.note` | `Endless waves that keep growing. Resupply between waves. How long can you hold it down?` | Title, under the pickers while Hold the Block is selected | `:54` |
| `difficulties.*` | `Hustler`, `Boss`, `Kingpin` | Title picker, settings drawer | `:60` |
| `weapons.chopper.name`, `weapons.nine.name` | `CHOPPER`, `NINE` | HUD weapon slots | `:66`, `:67` |
| `weapons.*.blurb` | `Compact automatic carbine, 30 rounds`; `9 mm pistol, 15 rounds, never runs dry` | Not shown | `:66`, `:67` |
| `weapons.melee.*` | `Pistol whip` (with the Nine), `Rifle butt` (with the Chopper) | Not shown | `:68` |
| `reels.item` | `Master reel` | Not shown | `:73` |
| `reels.list[].label` | `Reel 1 — The Avenue`, `Reel 2 — Chop Shop`, `Reel 3 — The Cage` | Handed to the HUD with each marker; the HUD draws only the code | `:75` |
| `reels.list[].code` | `1`, `2`, `3` | Route bullets: badge, world markers, minimap | `:75` |
| `extraction.label`, `extraction.code` | `IPX truck`, `IPX` | Label handed over with the marker; the code is drawn | `:81` |
| `enemies.*.down` | `Goon down`, `Buzzard down` | Kill feed | `:84`, `:85` |
| `enemies.headshot` | `Headshot` | Kill-feed tag when the killing hit was on the head | `:86` |
| `enemies.*.name` | `Goon`, `Buzzard` | Not shown | `:84`, `:85` |
| `explosives.*` | `Propane tank`, `Welding rack` | Not shown | `:90` |
| `objectives.mission[0…3]` | `Take back the three master reels`; `Two reels left`; `Last reel`; `Get to the IPX truck` | Objective line with 0, 1, 2, 3 reels secured | `:96` |
| `objectives.holdout.inbound` | `Vultures inbound` | Objective line before wave 1 | `:98` |
| `objectives.holdout.hold` | `Hold the block` | Objective line during a wave | `:99` |
| `objectives.holdout.breather` | `Catch your breath` | Objective line between waves | `:100` |
| `objectives.tally.standby` | `Stand by` | Badge tally before wave 1 | `:103` |
| `objectives.tally.wave` | `Wave {n} · {score}`, score with thousands separators: `Wave 3 · 12,345` | Badge tally from wave 1 on | `:104` |
| `prompts.grab` | `Hold {glyph} — Grab reel {code}`: `Hold E — Grab reel 1` | Interaction prompt at a reel; glyph `E` (keyboard), `X` (gamepad), `USE` (touch) | `:110`, `src/config/player.js:273` |
| `prompts.refuse` | `Reels still out there — the truck won't roll without all three` | Centre message at the truck before all reels are back | `src/config/text.js:112` |
| `compass[0…7]` | `NORTH`, `NORTH-EAST`, `EAST`, `SOUTH-EAST`, `SOUTH`, `SOUTH-WEST`, `WEST`, `NORTH-WEST` | Inside the two banners | `:116` |
| `banners.contact` | `Contact — {DIRECTION}`: `Contact — NORTH-EAST` | Banner when a reel is secured | `:125` |
| `banners.wave` | `Wave {n} — {DIRECTION}`: `Wave 3 — EAST` | Banner when a holdout wave starts | `:126` |
| `banners.countdown` | `Wave {n} in {secs}`: `Wave 2 in 3` | Centre message, last 3 s of a breather | `:127` |
| `notes.difficulty` | `Difficulty changes take effect at once; Vultures already on the block keep their health.` | Settings drawer | `:120` |
| `notes.time` | `Time of day changes when the next run starts.` | Not shown | `:121` |
| `radio.speaker` | `IPX VAULT` | Label over every radio line | `:132` |
| `radio.intro` | `Rule, it's the Vault. Vultures stashed your three masters on this block — the avenue, the chop shop, the cage. Bring them home.` | 3.15 | `:134` |
| `radio.introHoldout` | `Rule, it's the Vault. The Vultures want the whole block back. Hold it down as long as you can.` | 3.15 | `:138` |
| `radio.contact` | `They made you. Goons on foot, and more on the way. Handle it.` | 3.15 | `:139` |
| `radio.reel[0]` | `One reel back in your hands. They felt that — more coming.` | 3.15 | `:142` |
| `radio.reel[1]` | `Two reels. They're throwing the whole crew at you now.` | 3.15 | `:143` |
| `radio.reel[2]` | `That's all three. The IPX truck is idling at the south end of the lot. Move.` | 3.15 | `:144` |
| `radio.lowHealth` | `You're hit bad. Get behind something solid and breathe.` | 3.15 | `:146` |
| `radio.done` | `Masters are in the vault. The block is yours, Rule.` | 3.15 | `:147` |
| `radio.waveClear` | `Wave {n} down. Resupply at your feet — 9 seconds.` | 3.15 | `:148` |
| `cards.pause.*` | kicker `Hold up`; title `Paused`; buttons `Resume`, `Settings`, `Controls`, `Restart run` | Pause card | `:153` |
| `cards.dead.*` | kicker `Rule down`; title `Lights out`; stat labels `Time on the block`, `Reels recovered`, `Waves cleared`, `Vultures dropped`, `Score`, `Best`; button `Run it back` | Death card (3.14) | `:161` |
| `cards.debrief.*` | kicker `Hollis, Queens · Debrief`; title `The block is yours`; `Certification`; stat labels `Time`, `Accuracy`, `Vultures dropped`, `Retries`; button `Run it back` | Debrief card (3.14) | `:174` |
| `ratings[0…5]` | `Demo`, `Mixtape`, `Single`, `Gold`, `Platinum`, `Diamond` | Debrief, under `Certification` | `:188` |
| `boot.first … boot.ready` | `Waking up the block`; `Warming up the renderer`; `Mixing brick, chrome and neon`; `Parking cars on the avenue`; `Raising the El`; `Lighting the block`; `Loading tracers and smoke`; `Racking the Chopper`; `Waking the Vultures`; `Waiting on the next train`; `Ready` | Boot screen status line, in this order (3.1) | `:192` |
| `boot.fatal` | `Murder Inc. could not start: {error}` | Boot screen when start-up fails | `:203` |
| `boot.contextLost` | `The graphics context was lost. Reload the page to continue.` | Over the game about 5 s after the graphics context was lost and did not return | `:204`, `src/render.js:995` |
| `world.shop` | `V&R AUTO BODY` | Signs on the chop shop | `src/config/text.js:209` |
| `world.storefronts` | `HOLLIS DELI & GROCERY`; `CROWN & FADE BARBER`; `PAWN & GOLD`; `TAPES · RECORDS · CDs`; `GOLDEN BIRD CHICKEN`; `WINES & LIQUORS`; `LUCKY NAILS`; `24 HR LAUNDROMAT`; `CHECKS CASHED`; `99¢ PIZZA` | Storefront signs and awnings | `:211` |
| brand | `MURDER INC.` (title), `Murder Inc.` (plain form), `IPX PRESENTS`, `STARRING JA RULE`, `IPX` (wordmark, the only IPX mark), `IPX.EXCHANGE` (address, world art only) | Wordmarks; posters and livery in the world | `src/config/brand.js:8` |
| page | browser title `Murder Inc.`; boot screen `IPX` + `presents`, `MURDER INC.`, `Starring Ja Rule`; canvas label `Murder Inc. game view` | Boot screen (the note line is `title.note`) | `src/page.html:1`, `:4`, `:8` |
| ui `title.*` | `Mode`, `Difficulty`, `Time`, `Day`, `Night`, `Controls at a glance` | Title: picker labels, time options, heading of the controls strip | `src/ui/copy.js:8` |
| ui `title.eyebrow`, `title.timeNotes` | `Presents · Hollis, Queens`; `4:15 PM. Sun through the El.`; `02:14 AM. Sodium and neon.` | Not shown | `:7`, `:12` |
| ui `hud.*` | `Objective`, `HP`, `Melee`; button names `Pause`, `Settings`; `Wave` (not shown) | HUD labels | `:22` |
| ui `hud.cue.*` | `Reloading`; `Low ammo`; `Reload`, shown as `{key} — Reload` (`R — Reload`) when the device has keys; `Empty — {key} swaps` (`Empty — Q swaps`); `Empty — swap` on touch | Cue line over the weapon bar | `:29`, `src/ui/logic.js:333` |
| ui `hud.zones.*` | `West End`, `The Avenue`, `Chop Shop`, `The Cage`, `The Lot` | Fallback only (the level's upper-case names win) | `src/ui/copy.js:36` |
| ui `cards.*` | `Back to title` (second button of the death and debrief cards); `New best` (flag beside `Best`); `An IPX production` (foot of the debrief, hidden when the view is under 520 px high) | Cards | `:40`, `src/ui.css:1944` |
| ui `panel.*` | `Settings and controls`; `Close`; tabs `Settings`, `Controls`; `Difficulty`; `Weapon position` with `Close`, `Three-quarter`, `Compact`; `Graphics quality` with `Auto`, `Low`, `Medium`, `High`, `Ultra`; `Look sensitivity`; `Invert Y` with `On`, `Off`; `Master volume`; `Field of view`; `Display` with `Enter fullscreen`, `Exit fullscreen`, `Fullscreen is not available here` | Settings drawer | `src/ui/copy.js:46` |
| ui `panel.note*` | `Quality was picked for this device ({tier}). Lower it if the frame rate struggles.`; `Changes apply at once. Shadows and reflections may take a moment to catch up.` | Settings drawer, under the rows: the first with Auto quality, the second otherwise | `:65`, `:66` |
| ui `controls.kbm` | title `Keyboard · Mouse`; rows `Move` W A S D; `Look` Mouse; `Fire` LMB; `Aim` RMB; `Reload` R; `Swap weapon` Q, Wheel, 1, 2; `Grab a reel` Hold E; `Jump` Space; `Sprint` Shift; `Crouch` C; `Melee` F; `Pause` Esc, P. Note: `If the browser won't lock the mouse, move it to look and rest it at a screen edge to keep turning. Arrows or I J K L turn too, and Enter fires.` | Controls tab | `:72` |
| ui `controls.touch` | title `Touch`; rows `Move` Left thumb; `Look` Drag right side; `Fire` (fire button) `hold; drag to track`; `Fire, left thumb` (fire button) `the small trigger on the left`; `Aim` (aim button) `toggles`; `Reload`; `Swap weapon` `or tap a weapon slot`; `Grab a reel` (button captioned `USE`) `hold it`; `Jump`; `Crouch` `toggles`; `Melee`; `Sprint` Stick `pushed all the way forward`; `Sprint lock` `tap the arrow above the stick to keep running`; `Pause` `beside the map` | Controls tab | `:92` |
| ui `controls.pad` | title `Controller`; rows `Move / look` L stick, R stick; `Fire` RT; `Aim` LT; `Reload` X `hold X at a reel to grab it`; `Swap weapon` Y, D-pad; `Jump` A; `Crouch` B, LB; `Sprint` L3; `Melee` RB, R3; `Pause` Start. Note: `In menus the D-pad or left stick moves the selection, A accepts, B goes back. Browsers only start sound after a click or a key press, so a controller-only start can be silent until one click.` | Controls tab | `:114` |
| ui `glance`, `glanceOther` | `Move` W A S D; `Fire` LMB; `Aim` RMB; `Reload` R; `Swap` Q; `Grab` Hold E; `Sprint` Shift; `Crouch` C; `Melee` F; `Pause` Esc. `Controller`: `Sticks · RT fire · LT aim · X reload · Y swap`. `Touch`: `Left thumb moves · right side looks · the bullet button fires` | Title, controls strip on wide screens | `:135`, `:148` |
| input glyphs | Keyboard: `LMB`, `RMB`, `SPACE`, `SHIFT`, `C`, `R`, `E`, `Q`, `1`, `2`, `F`, `ESC`. Gamepad: `RT`, `LT`, `A`, `L3`, `B`, `X`, `X`, `Y`, `←`, `→`, `RB`, `START`. Touch: `FIRE`, `AIM`, `JUMP`, `STICK`, `DUCK`, `RLD`, `USE`, `SWAP`, `SWAP`, `SWAP`, `HIT`, `II` (order: fire, aim, jump, sprint, crouch, reload, interact, swap, weapon 1, weapon 2, melee, pause) | Key caps in prompts, the weapon bar and cue lines | `src/config/player.js:266`, `:280`, `:294` |
| touch button names | `Fire`, `Fire (left thumb)`, `Aim`, `Jump`, `Crouch`, `Reload`, `Swap weapon`, `Melee strike`, `Use` (caption `USE`), `Pause`; `Sprint lock` | Spoken names of the on-screen buttons | `src/config/player.js:317`, `src/input.js:579` |
| look hints | `Mouse is locked in. Esc lets it go.`; `Click the street once to lock the mouse in.`; `Resume locks the mouse back in.`; `This browser won't lock the mouse: move it to look, rest it at a screen edge to keep turning. Click fires. Arrows or I J K L turn too.` | Pause card hint line and the browser look-mode message (3.13) | `src/config/player.js:370` |
| formats | time `m:ss` (`1:15`); score `12,346`; accuracy `42 %`, or `—` when no shot was fired; reels `1/3`; ammo `24 / 120` and `15 / ∞`; marker distance `42 m`; slider values `1.00×`, `80%`, `74°`; minimap north mark `N` | Cards, HUD, drawer | `src/ui/logic.js:13`, `:19`, `:24`, `:29`, `:34`, `src/hud.js:502`, `:91`, `src/ui/panel.js:12` |

---------------------------------------------------------------------------------------------------

## 3. Behaviour

### 3.1 Boot, frame order and clocks

**Boot.** Modules are created one after the other; some steps change the status line and the bar of the boot screen
(`src/modules.js:70`, `src/main.js:346`). The first line, `Waking up the block`, is in the page before any script runs
(`src/page.html:12`).

| Order | Module | Boot line from this step on | Bar |
|---|---|---|---|
| 1 | render | `Warming up the renderer` | 0.04 |
| 2, 3 | mats, physics | `Mixing brick, chrome and neon` | 0.12 |
| 4, 5 | props, input | `Parking cars on the avenue` | 0.24 |
| 6 | level | `Raising the El` | 0.36, creeping toward 0.52 while the level builds |
| 7 | atmos | `Lighting the block` | 0.52 |
| 8 – 12 | fx, audio, player, combat, explosives | `Loading tracers and smoke` | 0.64 |
| 13 | weapon | `Racking the Chopper` | 0.74 |
| 14 – 17 | enemies, hud, menus, game | `Waking the Vultures` | 0.82 |
| then | `render.onLevelReady()`: shadow pass, shader pre-compile | `Waiting on the next train` | 0.92 |
| then | `boot:done` is emitted; the boot screen fades over 700 ms | `Ready` | 1 |

When the game module is created it reads `mode` and `difficulty` from the settings, writes the place line for the
stored time of day, applies the difficulty, sets the fade to black and enters `title` (`src/game.js:45`, `:951`).
With the URL parameter `autostart` (or `shot`) the boot starts a run straight away without an intro
(`src/main.js:368`).

**Frame.** One variable step per rendered frame (`src/main.js:270`, `src/modules.js:91`):

```
dt = min(real frame time, 0.05)
time.t += dt                      always, on the title and while paused too
input.update(dt)
live = game.update(dt)            false on the title, while paused, and on the frame a pause starts
if live and state is not title or paused:   player, weapon, enemies, explosives  update
if state is not paused:                     fx, level, atmos, mats               update
always:                                     audio, hud, menus                    update
render.frame(dt);  input.endFrame()
```

What follows from this order:

- The flow runs before the player, the weapon and the enemies, so it works on the positions, health and kills of the
  previous frame. A holdout wave is cleared on the frame after its last member died **(verified)**; a reel in reach is
  noticed one frame after the player arrives.
- Event handlers run inside the update of whoever emits. `enemy:killed` adds the score on the frame of the kill;
  `player:dead` switches to `dead` in the middle of a frame and the modules after it still update once.
- In `dead` and `complete` the flow returns true: enemies, explosives and effects keep running behind the card.

**Clocks.**

| Clock | Advances | Used for | Source |
|---|---|---|---|
| `G.time.t` | Every frame, in every state | Nothing in the flow (the HUD and effects use it) | `src/main.js:273` |
| `stateTime` | Every frame; set to 0 by every state change | Intro timings, card delays, pause debounce, the title loop | `src/game.js:62`, `:141`, `:790` |
| `clock` (the run clock) | Only in `intro` and `playing` | Due times of queued arrivals, how recently a spawn point was used, the refusal message | `src/game.js:63`, `:833` |
| `run.time` | Only in `playing` | The time on the cards and in the rating | `src/game.js:850` |
| `waveAge`, `sinceAlert`, `sinceHit` | Only in `intro` and `playing` | The music driver (3.17) | `src/game.js:768` |

Timers that count down (`pursuitTimer`, `holdout.breakLeft`, `holdout.realertIn`, the radio queue) are only stepped in
the states that step them (3.9, 3.11, 3.15). Nothing in the flow uses wall-clock time, so a pause freezes all of it.

### 3.2 The state machine

```
title → intro → playing ⇄ paused
intro | playing → dead                    the player died
intro | playing → complete                Story only: at the truck with every reel
paused | dead | complete → intro          restart, retry, redeploy: always the whole run again
dead | complete → title
```

**What is on in each state** (`src/game.js:139`):

| State | Simulation (player, weapon, enemies, explosives) | World animation (effects, level, sky, train) | HUD and viewmodel | Gameplay input | Player | Menu layer | Pointer |
|---|---|---|---|---|---|---|---|
| `title` | off | on | hidden | off | disabled; the title camera owns the view | Title screen | free |
| `intro` | on | on | shown | on | enabled | none; location card in a full intro | captured |
| `playing` | on | on | shown | on | enabled | none | captured |
| `paused` | off | off | hidden | off | enabled but nothing updates | Pause card | free |
| `dead` | on | on | hidden | off | enabled: the death camera plays (0.85 s collapse) | none, then the death card at 1.5 s | free |
| `complete` | on | on | hidden | off | disabled and invulnerable: the view stays where the run ended | none, then the debrief card at 3.3 s | free |

Every state change does this, in this order (`src/game.js:139`): store the state; `stateTime` = 0; forget that a card
was shown; gameplay input, HUD and viewmodel on only for `intro` and `playing`; player enabled for `intro`, `playing`,
`dead`, `paused`; tell audio whether the game is paused; show the title screen or the pause card, or clear the menu
layer; hide the interaction prompt unless the state is `intro` or `playing`; emit `game:state {state, prev}`.
The radio strip is not part of the HUD: a line stays visible in every state except `title` and `paused`
(`src/hud.js:612`). Audio follows `game:state` on its own: music in its title mix on `title` and its play mix on
`intro` / `playing`; ambience level 0.6 on the title, 1 in play, 0.7 dead, 0.8 complete (`src/audio/react.js:278`).

**Transitions.**

| # | From → to | Trigger | What happens | Source |
|---|---|---|---|---|
| T1 | boot → `title` | The game module is created | Fade black, title screen | `src/game.js:953` |
| T2 | `title` → `intro` | `start()`: the title button `Hit the block`; Enter or keypad Enter (not while a button or field has the focus, not while the drawer is open); gamepad Start (not while the drawer is open) | `run.retries` = 0; mode = the argument or the `mode` setting; run reset (3.3); ask for the pointer; music calm; full intro: length 2.4 s, fade black | `src/game.js:263`, `:245`, `:939`, `:798`, `src/menus.js:92` |
| T3 | `title` → `playing` | `start({skipIntro: true})`: only the URL parameters `autostart` / `shot` | As T2, but fade 0 and no intro | `src/game.js:250`, `src/main.js:371` |
| T4 | `intro` → `playing` | `stateTime` ≥ intro length | Location card off, fade 0 | `src/game.js:848`, `:320` |
| T5 | `intro` / `playing` → `paused` | `pause()` (3.13) | From `intro` T4 happens first (two `game:state` events), then the pause; pointer released | `src/game.js:287` |
| T6 | `paused` → `playing` | `resume()`: button `Resume`; the pause key after 0.35 s on the card (not while the drawer is open); gamepad B | Ask for the pointer | `src/game.js:294`, `:805`, `src/menus.js:209`, `:379` |
| T7 | `paused` → `intro` | `restart()`: button `Restart run` | `run.retries` + 1; same mode; run reset; quick intro 1.1 s | `src/game.js:271`, `src/menus.js:220` |
| T8 | `intro` / `playing` → `dead` | Event `player:dead` | 3.12 | `src/game.js:879` |
| T9 | `intro` / `playing` → `complete` | Story: the living player is inside the extraction zone with every reel secured | 3.10 | `src/game.js:649`, `:662` |
| T10 | `dead` → `intro` | `retry()`: button `Run it back` on the death card; gamepad Start | As T7 | `src/game.js:277`, `src/menus.js:227`, `:382` |
| T11 | `complete` → `intro` | `redeploy()`: button `Run it back` on the debrief; gamepad Start | `run.retries` = 0; same mode; run reset; quick intro | `src/game.js:282`, `src/menus.js:240` |
| T12 | `dead` / `complete` → `title` | `toTitle()`: button `Back to title` | 3.4 | `src/game.js:300`, `src/menus.js:234`, `:254` |

Guards: `pause()` does nothing outside `intro` / `playing`; `resume()` does nothing outside `paused`; two start
requests in the same frame while a run is already starting count as one (`src/game.js:264`). There is no way back to
the title from the pause card.

### 3.3 Run reset

Every start, retry, restart and redeploy runs the same reset, in this order (`src/game.js:195`). `run.retries` is set
by the caller before it.

1. Empty the arrival queue, the "recently used" memory of the spawn points and the set of secured reels.
2. Run clock 0; no reel being held; refusal timer cleared; "contact said" and "low health said" cleared; pursuit off;
   the three music clocks set to "long ago".
3. Holdout: inactive, `breakLeft` = 3.5 s, countdown 0, waves cleared 0.
4. `run`: time 0, reels 0, total = number of objectives, wave 0, score 0, kills 0, shots 0, hits 0.
5. Radio queue and strip cleared.
6. Time of day applied from the `time` setting (the sky rig switches; the place line of the location card is chosen).
7. Enemies cleared (bodies too); difficulty applied (3.18); effects cleared; combat statistics zeroed; weapon reset
   (full magazines, Chopper reserve 150, Chopper in hand); explosives rebuilt; player reset to the start point (full
   health, not invulnerable); HUD reset (feed, banner, message, prompt, radio).
8. Location card off; saturation 1; screen flash 0.
9. Objective cases: `live` in Story, `taken` (closed, lights out) in Hold the Block. Truck: `idle` (doors shut).
10. Story: reel bullets 0 / 3 and the starting patrol is spawned (3.6.1). Hold the Block: tally `Stand by`.
11. Objective line and world markers refreshed (3.16).
12. Emit `game:reset {mode}`.

Then `begin()` asks for the pointer, sets the music to calm, sets the fade to black and enters `intro`
(`src/game.js:245`). **(verified)** order of calls and events.

### 3.4 Title screen and fly-through

The title screen (`src/menus.js:127`): the IPX lozenge with `PRESENTS · HOLLIS, QUEENS`; the wordmark; the star line;
the premise; three pickers (`Mode`, `Difficulty`, `Time`) that write the settings at once; the note of the selected
mode; the buttons `Hit the block` (primary), `Settings`, `Controls`; the foot note; on wide screens a strip headed
`Controls at a glance`. Letterbox bars slide in at the top and bottom and a dark gradient covers the left and the
lower part of the picture (`src/ui.css:990`, `:1021`). Behind it the block is alive (train, steam, traffic) but empty:
no enemies exist on the title. After `toTitle()` the three cases stand open and lit again.

Every frame on the title the flow places the camera, sets the fade from the camera's loop, keeps saturation at 1 and
the music at calm (`src/game.js:793`). The camera (`src/game/titlecam.js:36`):

```
D = max(26, pathLength / 1.15)                      135.25 s for the shipped path
t = stateTime mod D;   k = t / D
u = 0.25 * smoothstep(0, 1, k) + 0.75 * k           share of the path length travelled
s = parameter of the position spline at arc-length share u
position = posSpline(s);   target = lookSpline(s)   the same parameter s on both splines
w = stateTime * 0.42
position += side * sin(w) * 0.07                    side: horizontal unit vector at right angles to the view
position.y += sin(1.31 * w + 1.7) * 0.04
aim at target, then roll by sin(0.77 * w + 0.6) * 0.005 rad;   vertical FOV 50 degrees
fade = 1 - smoothstep(0, 1.8, t) + smoothstep(D - 1.6, D, t)
```

Both splines are open centripetal Catmull-Rom curves through the 14 keys (`src/game/titlecam.js:16`). Because the look
spline is read at the position spline's parameter, the camera at key i looks exactly at look target i. The sway runs on
the time since the title came up, so it does not restart with the loop. The keys are passed at 0, 7.9, 19.5, 27.0,
33.7, 38.9, 45.6, 54.0, 70.7, 87.9, 104.4, 106.5, 121.0 and 135.2 s **(derived)**. A level without a usable path
leaves the camera alone and only runs the fade on a 26 s loop.

`toTitle()` (`src/game.js:300`): empty the queue; reset the player to the start (alive, full health: no low-health
look on the title); clear radio, enemies, effects and the location card; apply the time of day; all cases `live`,
truck `idle`; no markers; saturation 1; fade black; music calm; enter `title`; release the pointer.

### 3.5 Intro

| | Full intro | Quick intro |
|---|---|---|
| Used by | A start from the title | Retry, restart, redeploy |
| Length | 2.4 s | 1.1 s |
| Fade (share of black) | 1 − smoothstep(0.05, 1.3, t) | 1 − smoothstep(0.05, 1.1, t) |
| Location card | Appears at 0.25 s, removed when the intro ends (2.15 s on screen) | none |
| Radio | At 0.9 s the mode's first line is queued | none |

(`src/game.js:255`, `:836`.) The location card (`src/menus.js:302`) sits low on the left: line 1 is the place for the
time of day, revealed left to right over 1.1 s; line 2 is the tagline: `Three reels. One block. No backup.` in Story,
`One block. Endless Vultures.` in Hold the Block (`src/game/intro.js:11`).

The intro is not a cutscene. The player has full control from its first frame and the simulation is live: the run
clock counts, enemies act, arrivals are pumped, a reel can be held, the holdout delay runs. Only `run.time` waits for
`playing` (`src/game.js:828`).

### 3.6 Story mode

#### 3.6.1 The starting patrol

At reset, after the player is back at the start: for each type, Buzzards first, as many as the difficulty row says,
pick a position with minimum distance 32 m in strict mode (3.7) and spawn the unit unaware (`src/game.js:450`).
**(verified)** on Boss: 2 Buzzards and 4 Goons, all 64 to 84 m from the start. The reset happens under the black of
the intro, so nobody is seen appearing.

#### 3.6.2 Which reel is in reach

Every frame while the player lives (`src/game.js:521`): of the reels not yet secured, the nearest one that passes

```
d = horizontal distance from the player's feet to the reel
d <= 2.2 m   and   |reel.y - feet.y| <= 2.5 m
and ( d <= 0.9 m   or   cos(angle between the horizontal facing and the direction to the reel) >= 0.45 )
```

Pitch does not matter: only the horizontal part of the view direction is used. No line-of-sight test is made.

#### 3.6.3 Holding

```
holding = a reel is in reach and Interact is down
if holding:
    if it is a different reel than the one with progress:  that one drops to 0 at once; progress = 0
    progress = min(1, progress + dt / 2.4);   case state 'grabbing';   emit objective:progress {id, t}
else if a reel has progress:
    progress = max(0, progress - 1.6 * dt);   case state 'live';       emit objective:progress {id, t}
if a reel is in reach:   show the prompt "Hold {glyph} — Grab reel {code}" with the ring at that reel's progress
else:                    hide the prompt
if holding and progress >= 1:   secure the reel
```

(`src/game.js:554`.) The player is never held in place and can be shot while holding. Letting go, turning away,
stepping out of reach or dying drains the bar at 1.6 per second; it keeps draining while the player walks away, and a
short interruption costs little. **(verified)**: 1.2 s of holding gives 0.50, 0.2 s of letting go leaves 0.18, and
the reel is secured 1.97 s later. The prompt shows whenever a reel is in reach, held or not; its glyph follows the
active device (`E`, `X`, `USE`).

#### 3.6.4 Securing a reel

In this order, all on the same frame (`src/game.js:596`):

1. Mark the reel secured; `run.reels` = number secured; case state `taken` (lid drops, reel and lights gone).
2. Progress cleared, prompt hidden, reel bullets updated, camera shake 0.18.
3. Objective line and markers refreshed: the reel's marker goes; after the last reel the `IPX` exit marker appears.
4. Emit `objective:done {id, index: run.reels, total}`.
5. Queue the reinforcement wave for this reel (row `waves[reels − 1]` of the difficulty, 2.10) with first delay 1.6 s
   and stagger 0.85 s. If at least one member was queued: banner `Contact — {DIRECTION}` for 3.4 s.
6. Queue the radio line for this reel (3.15).
7. Music sting: `reel`, or `all` for the last reel.
8. After the last reel only: pursuit budget loaded, first pursuit check in 12 s, emit `objective:all {}`.

`debugGrab()` does exactly this for the next open reel (`src/game.js:625`).

#### 3.6.5 Who arrives, in which order

A story wave alternates from a Buzzard and the rest follow (`src/game/waves.js:17`):

```
order = [];  while b > 0 or g > 0:  if b > 0: push BUZZARD, b -= 1;   if g > 0: push GOON, g -= 1
```

(2, 5) gives B G B G G G G; (4, 7) gives B G B G B G B G G G G. Member i (from 0) is due at
`clock + 1.6 + 0.85 × i`.

#### 3.6.6 Queueing a wave and naming its direction

`queueWave(order, firstDelay, stagger)` (`src/game.js:463`) is shared by story waves, pursuit arrivals and holdout
waves. For every member it picks a position **now** (3.7, minimum distance 18 m, not strict), adds the horizontal
offset from the player to that position to a running sum, and appends `{type, due time, position, tries: 0}` to the
queue. If at least one member was queued, the wave's age (for the music) is set to 0 and the direction is

```
sector = round( atan2(sum.x, -sum.z) / 45 degrees ) mod 8
         0 = NORTH (toward -Z), then clockwise: 1 = NORTH-EAST, 2 = EAST ... 7 = NORTH-WEST
```

(`src/game/spawn.js:11`.) So the banner names where the bulk of the wave will come from, as seen from the player at
the moment of queueing. A zero sum reads `NORTH`.

### 3.7 Spawn-point scoring and selection

Enemies appear at authored points: `ground` points for Goons, `air` points for Buzzards (2.15). Every time a position
is needed, every point of the right kind is scored and the best one wins (`src/game/spawn.js:23`, `:48`):

```
d       = horizontal distance from the player to the point
hidden  = no line of sight from (player feet + 1.6 m) to the point (ground points: + 1.2 m)
usedAgo = run-clock seconds since this point was last chosen (never: infinity)

score = uniform(0, 1) * 1.5
      + ( d >= minDistance ?  2 + 0.5 * min(1, (d - minDistance) / 30)  :  -(minDistance - d) / 4 )
      + ( hidden ? 2.5 : 0 )
      + ( usedAgo < 6 ? -3 : 0 )
```

- The line of sight is tested against static, bullet-stopping geometry only: enemies, the Cage's chain-link, glass,
  railings and invisible walls do not hide a point (`src/physics.js:347`).
- **Strict mode** (the starting patrol): any point at least `minDistance` away beats every nearer point, whatever the
  scores; nearer points are used only when no point is far enough.
- The winner is stamped with the current run clock, so the −3 spreads a wave over different points: all members of a
  wave are placed on the same frame, and a point just taken is 3 points down for the rest.
- What the weights mean: among far points that were not just used, a hidden one always beats a visible one (2.5
  against a random spread of 1.5 and a distance bonus of at most 0.5). A point that is too near but hidden can beat a
  far visible one only when it is less than 8 m short of the minimum distance, and on average only when it is less
  than 2 m short. A point 10 m too near loses 2.5 on top of the 2 it does not get.

The position is then finished (`src/game.js:405`):

```
air:     x += uniform(-1.2, 1.2);  z += uniform(-1.2, 1.2);   if y < 2.5: y = uniform(6, 9)
ground:  try x + jx, z + jz:  kept only if that spot is walkable and its floor is within 0.3 m of the point's floor
```

With no authored points at all (never the case on the shipped block) a point on a 26 m ring around the player is used,
moved to the nearest walkable cell for a Goon; if there is none the member is skipped.

| Use | Minimum distance | Strict | Spawned as | Source |
|---|---|---|---|---|
| Starting patrol | 32 m | yes | unaware | `src/game.js:454` |
| Members of a story wave, a pursuit arrival, a holdout wave (picked when queued) | 18 m | no | alerted, hunting toward the player | `src/game.js:469`, `:506` |
| A queued ground position that is within 9 m of the player when it comes due | 18 m | no | picked again on the spot | `src/game.js:503` |

### 3.8 The arrival pump

Every frame of `intro` and `playing`, before the mode logic (`src/game.js:486`):

```
next = the first queue entry, in queue order, whose due time has come;   none: return
if enemies alive >= aliveCap:            next.due = clock + 1;   return
if next is a Goon and the player is within 9 m (horizontal) of next.position:   pick a new position
if enemies.spawn(type, position, {alerted, target: player position}) succeeds:
        remove it from the queue;   enemies.alert(player position, 60 m)
else:   next.tries += 1;   if tries >= 6: drop it   else: next.due = clock + 1.5
```

- At most one arrival per frame, however many are due.
- `aliveCap` is the difficulty's `maxAlive`, plus `extraAlive(n)` in Hold the Block. It counts every living enemy:
  the patrol, earlier waves, both types.
- While the cap is reached the due entries are pushed back one second at a time, each in turn, so they keep their
  order and enter one by one as kills make room **(verified)**.
- An arrival is "alerted": it walks or flies toward the player's position at that moment and keeps hunting for 10 s
  (Goon) or 8 s (Buzzard) before it would give up (`src/config/enemies.js:119`, `:31`); the 60 m alert also sends
  every unaware enemy near the player to look. These unaware ones announce themselves with `enemy:alert` (this can
  be the first contact of a run); the arrival itself does not.
- A spawn fails only when all 12 Goon slots (or all 8 Buzzard slots) hold living units; the entry is then retried
  every 1.5 s and dropped for good after the sixth refusal. A dropped member is simply missing from the wave.

### 3.9 Pursuit

Once every reel is secured, every frame (`src/game.js:632`):

```
pursuitTimer -= dt
if pursuitTimer <= 0:
    if pursuitLeft > 0 and the queue is empty and enemies alive < 4:
        pursuitLeft -= 1
        queue one arrival: Buzzard if random() < 0.35 else Goon, due in 0.5 s        (no banner)
        pursuitTimer = pursuitEvery of the difficulty (7 / 5.5 / 4.5 s)
    else:
        pursuitTimer = 4;   enemies.alert(player position, 90 m)
```

The first check comes 12 s after the third reel. The pursuit is a trickle that keeps a few hunters on a player who has
thinned the last wave: nothing extra arrives while four or more are alive or the last wave is still queued; in that
case everyone within 90 m is pointed at the player again every 4 s. The budget (5 / 8 / 12) is the most that can ever
arrive; unused budget is lost when the run ends. **(verified)** on Boss with the block cleared: one arrival every
5.5 s.

### 3.10 Extraction and completion

Every Story frame, also before the reels are back (`src/game.js:649`):

```
inside = horizontal distance from the player's feet to the zone centre <= 2.5 m  and  |zone.y - feet.y| <= 3.5 m
if inside and every reel is secured and the player is alive:   complete
else if inside and more than 8 s (run clock) since the last refusal:
        centre message "Reels still out there — the truck won't roll without all three" for 3.5 s
```

Completion, in this order (`src/game.js:662`): copy the statistics; make the player invulnerable; truck state `open`
(rear doors swing over 1.1 s, the vault lights up); emit `extraction:reached {}`; music sting `complete`; enter
`complete` (HUD and weapon hidden, player disabled); clear the radio and queue the final line
(`Masters are in the vault. The block is yours, Rule.`); release the pointer. In `complete` the screen eases toward
72 % black and 0.7 saturation (2.4), the radio keeps running, and at 3.3 s the debrief card appears and the music is
set to calm (`src/game.js:818`). The last radio line is on screen for 3.28 s, so it ends as the card arrives. Enemies
still alive keep moving and shooting behind the card; they cannot hurt the player.

### 3.11 Hold the Block

No reels, no truck, no markers: the three cases stand closed and the extraction zone is never tested. Every frame of
`intro` and `playing`, after the pump (`src/game.js:708`):

```
if a wave is active:
    if the queue is not empty:   return                      members are still on their way
    if enemies alive == 0:       clear the wave;  return
    realertIn -= dt;  if realertIn <= 0:  realertIn = 5;  enemies.alert(player position, 90 m)
else:
    breakLeft -= dt
    if wave >= 1 and countdown > 0 and breakLeft <= countdown:
        centre message "Wave {wave + 1} in {countdown}" for 1 s;   countdown -= 1
    if breakLeft <= 0:   start the next wave
```

**Starting wave n** (`src/game.js:678`): n = wave + 1; wave active; `realertIn` = 5 s; the difficulty is applied again
with this wave's multipliers and alive allowance (2.11); the wave is queued with first delay 1.2 s and `stagger(n)`
(3.6.6); banner `Wave {n} — {DIRECTION}` for 3.6 s; objective `Hold the block`; tally `Wave {n} · {score}`; emit
`holdout:wave {wave: n, count: total}`.

**Order of a holdout wave** (`src/game/waves.js:39`): `total` slots, all Goons at first; Buzzard i (counting from 0)
takes slot `min(total − 1, 1 + floor(i × total / buzzards))`, or the next free slot after it. Wave 1 is
G B G B G B G; wave 5 is G B G G B G G B G G B G G B G; wave 10 is G B G G G B G G G B G G G B G G G B G G G B G G G.

**Clearing wave n** (`src/game.js:691`), in this order: wave inactive; `holdout.cleared` = n; `breakLeft` = 9 s;
countdown = 3; score + 500 n; Chopper reserve + 90, capped at 240; player healed by 35 (never above the maximum); when
n is even every propane tank and welding rack on the block is rebuilt; the wave-clear radio line is queued
(`Wave {n} down. Resupply at your feet — 9 seconds.`); objective `Catch your breath` and the tally with the new score;
emit `objective:done {id: 'wave', index: n, total: n}`; music sting `reel`. The resupply is not an object in the
world: the rounds and the health are simply added.

**Kill score** (`src/game.js:906`): on every `enemy:killed` while the mode is Hold the Block and the state is
`playing`: score + round(base × (1 + 0.1 (wave − 1))), base 150 for a Goon and 100 for a Buzzard (an unknown type
scores as a Buzzard); the tally is redrawn at once. `byPlayer` is not looked at; kills while `dead` or `paused` do not
score.

Timing **(verified)**: wave 1 starts when the run clock reaches 3.5 s (1.1 s after a full intro ends, 2.4 s after a
quick one); its first member arrives 1.2 s later and the rest 0.86 s apart; a wave is cleared on the frame after its
last member dies with the queue empty; the countdown messages come 3, 2 and 1 s before the next wave, which starts 9 s
after the clear. Wave 2 spawned Goons with 117.7 HP and Buzzards with 58.9 HP on Boss (110 and 55 × 1.07).

The run only ends with death. The death card's `Waves cleared` is `holdout.cleared`: waves fully cleared, not the
number of the wave the player died in.

### 3.12 Death

On `player:dead` while the state is `intro`, `playing` or `paused` (`src/game.js:879`), in this order: copy the
statistics; a reel bar that was filling drops to 0 (case back to `live`, `objective:progress` with 0); location card
off; music sting `dead`; enter `dead` (HUD and weapon hidden, gameplay input off, player still enabled so the death
camera plays); radio queue and strip cleared; pointer released.

In `dead` (`src/game.js:809`): the screen eases toward 55 % black and 0.12 saturation (2.4); at 1.5 s the death card is
shown and the music is set to calm. The simulation keeps running: enemies lose sight of a dead player and go
searching, explosives finish their fuses. The arrival queue is frozen as it was (nothing more arrives), and the
pursuit, the holdout loop, the radio and the music driver are not stepped.

### 3.13 Pause

`pause()` only acts in `intro` and `playing`. It is called by:

| Trigger | Source |
|---|---|
| The pause action: Esc or P, gamepad Start, the touch pause control | `src/game.js:829`, `src/config/player.js:246`, `:216` |
| The HUD's pause button; the HUD's settings button (which also opens the drawer over the pause card) | `src/hud.js:281`, `:285` |
| The mouse capture is lost after the run once had it (the browser took it back, usually on Esc) | `src/game.js:919` |
| The page becomes hidden | `src/game.js:923` |
| The window loses focus | `src/game.js:928` |
| The graphics context is lost | `src/game.js:930` |

While paused the flow returns false and does nothing else: the run clock, `run.time`, every flow timer, the radio
queue, the kill feed and the radio strip stand still (`src/game.js:803`, `src/hud.js:788`); the world is not animated;
effects and ambience go silent and the music drops to 45 % behind a 1.3 kHz low-pass (`src/audio.js:584`).
**(verified)** a 2 s pause in a breather delayed the next wave and the pending radio line by exactly 2 s.

The pause card: IPX lozenge, kicker `Hold up`, title `Paused`, one hint line about the mouse (browser only), buttons
`Resume` (primary), `Settings`, `Controls`, `Restart run` (`src/menus.js:207`). The pause key resumes after 0.35 s on
the card; while the settings drawer is open the key closes the drawer instead (`src/game.js:805`, `src/menus.js:387`).

Browser-only extra, not to be ported: on a desktop with keyboard and mouse, while the mouse is not captured, a centre
message explains how looking works for 2.6 s, first 1.5 s into a run and then every 6 s (`src/game.js:363`).

### 3.14 Statistics, rating and cards

| Statistic | What counts | Source |
|---|---|---|
| `shots` | Every round fired by the player's guns. A melee strike is not a shot | `src/weapon/logic.js:447` |
| `hits` | Every player round that hits an enemy, body or head. Rounds into explosives, melee strikes and blasts are not hits | `src/combat.js:202` |
| `kills` | Enemies killed by a player round, by a melee strike, or by any blast: a tank or rack (also when an enemy round set it off), a chain reaction, the burst of a crashing Buzzard | `src/combat.js:92`, `:203`, `:299`, `:350` |
| `headshots` | Kills whose final round hit a Goon's head | `src/combat.js:94` |
| `damageTaken` | Sum of all damage the player took | `src/combat.js:48` |
| `run.time` | Seconds spent in `playing` (intro, pause and the death camera do not count) | `src/game.js:850` |
| `run.retries` | + 1 for every `Restart run` and every `Run it back` on the death card; 0 after a start from the title or a `Run it back` on the debrief | `src/game.js:266`, `:272`, `:283` |
| accuracy | `shots > 0 ? min(1, hits / shots) : none` | `src/game/stats.js:4` |

The combat counters are zeroed at every run reset (`src/combat.js:53`, `src/game.js:222`); the flow copies kills, shots
and hits into `run` every frame of `intro` / `playing` and again when a card is built (`src/game.js:737`, `:853`).
`headshots` and `damageTaken` are collected but no card shows them.

**Rating**: 2.12, computed from `run.time`, hits / shots and `run.retries`. Only the debrief shows it, so in practice
it rates completed Story runs. Example **(verified)**: a 75 s run without a shot and without a retry is 2 + 0 + 1 =
`Gold`.

**Building a card** (`src/game.js:744`): copy the statistics; round the score; in Hold the Block
`newBest = settings.setBest(score)` then `best = settings.best()`; hand the data to the menus; music calm. The data
object is the same for both cards (`src/game/stats.js:14`): `mode, difficulty, time, reels, total, wave` (holdout
waves cleared), `kills, headshots, shots, hits, score, best, newBest, accuracy` (0 … 1, or none), `retries, rating`
(0 … 5), `ratingName`.

| Card | Head | Rows | Buttons | Source |
|---|---|---|---|---|
| Death, Story | kicker `Rule down`, title `Lights out` (red title, red top edge) | `Time on the block` m:ss; `Reels recovered` n/3; `Vultures dropped` | `Run it back` (primary: retry), `Back to title` | `src/menus.js:225`, `src/ui/logic.js:415`, `src/ui.css:1395` |
| Death, Hold the Block | same | `Time on the block`; `Waves cleared`; `Vultures dropped`; `Score` 12,345; `Best` 12,345 with the flag `New best` when this run set it | same | same |
| Debrief (Story only) | IPX lozenge, kicker `Hollis, Queens · Debrief`, title `The block is yours` (gold top edge); a gold-record glyph with `Certification` and the rating name | `Time` m:ss; `Accuracy` `42 %` or `—`; `Vultures dropped`; `Retries` | `Run it back` (primary: redeploy), `Back to title`; foot `An IPX production` | `src/menus.js:238`, `src/ui/logic.js:430` |
| Pause | IPX lozenge, kicker `Hold up`, title `Paused` | hint line | `Resume` (primary), `Settings`, `Controls`, `Restart run` | `src/menus.js:207` |

The cards as rendered in the test runs **(verified)**. Kickers, titles, buttons and the flag are set in capitals by
the style, not in the copy.

| Card | Text on the card, top to bottom |
|---|---|
| Death, Story | `RULE DOWN`; `LIGHTS OUT`; `Time on the block` `0:20`; `Reels recovered` `1/3`; `Vultures dropped` `0`; `RUN IT BACK`; `BACK TO TITLE` |
| Death, Hold the Block | `RULE DOWN`; `LIGHTS OUT`; `Time on the block` `0:40`; `Waves cleared` `2`; `Vultures dropped` `18`; `Score` `3,965`; `Best` `3,965` `NEW BEST`; `RUN IT BACK`; `BACK TO TITLE` |
| Debrief | `IPX`; `HOLLIS, QUEENS · DEBRIEF`; `THE BLOCK IS YOURS`; `CERTIFICATION` `GOLD`; `Time` `1:15`; `Accuracy` `—`; `Vultures dropped` `0`; `Retries` `0`; `RUN IT BACK`; `BACK TO TITLE` |
| Pause | `IPX`; `HOLD UP`; `PAUSED`; `Resume locks the mouse back in.`; `RESUME`; `SETTINGS`; `CONTROLS`; `RESTART RUN` |

### 3.15 Radio

One speaker, `IPX VAULT`. Lines are subtitles with a short squelch sound at their start; there is no recorded voice.

**The queue** (`src/game/radio.js:12`): lines wait in order. When nothing is up, the next line starts on the flow's
next update and occupies `characters / 58 + hold + 0.3` seconds: it types out at 58 characters per second, holds for
its own time, then 0.3 s of silence before the next. Starting a line calls `hud.radio(speaker, text, hold)` and emits
`radio:line {speaker, text, secs: hold}` (`src/game.js:114`). The queue is stepped in `intro`, `playing` and
`complete`, frozen while paused, and emptied (the line on screen included) at every run reset, at death, on the way to
the title, and at completion just before the final line (`src/game.js:130`).

| Line | Trigger | How often | Hold | Typing **(derived)** | On screen | Slot | Source |
|---|---|---|---|---|---|---|---|
| `radio.intro` | 0.9 s into a full intro, Story | Every start from the title | 4.4 s | 2.19 s | 6.59 s | 6.89 s | `src/game.js:843`, `src/config/text.js:133` |
| `radio.introHoldout` | 0.9 s into a full intro, Hold the Block | Every start from the title | 4.0 s | 1.62 s | 5.62 s | 5.92 s | `src/game/intro.js:16`, `src/config/text.js:138` |
| `radio.contact` | The first `enemy:alert` while the state is `playing` | Once per run | 3.2 s | 1.05 s | 4.25 s | 4.55 s | `src/game.js:899` |
| `radio.reel[0]` | First reel secured | Once per run | 3.6 s | 1.00 s | 4.60 s | 4.90 s | `src/game.js:614` |
| `radio.reel[1]` | Second reel secured | Once per run | 3.6 s | 0.93 s | 4.53 s | 4.83 s | same |
| `radio.reel[2]` | Last reel secured | Once per run | 4.5 s | 1.31 s | 5.81 s | 6.11 s | same |
| `radio.lowHealth` | First frame of `intro` / `playing` with the living player's health under 30 | Once per run | 3.0 s | 0.95 s | 3.95 s | 4.25 s | `src/game.js:864`, `src/config/player.js:87` |
| `radio.done` | The truck is reached (the queue is emptied first) | Once per run | 2.4 s | 0.88 s | 3.28 s | 3.58 s | `src/game.js:670` |
| `radio.waveClear` | Holdout wave n cleared | Every wave | 3.4 s | 0.81 s (0.83 s from wave 10) | 4.21 s | 4.51 s | `src/game.js:702` |

Lines are never dropped while a run goes on: they wait. **(verified)** a reel taken 3.8 s after the intro line started
got its line 3.1 s late, when the intro line's slot was over; a contact that happened during the reel 2 line was
announced when that line was done.

### 3.16 HUD lines the flow drives

| HUD element | Call | What the flow sends | Source |
|---|---|---|---|
| Objective line | `hud.setObjective(text)` | Story: `objectives.mission[reels secured]`. Hold the Block: `Vultures inbound` before wave 1, `Hold the block` during a wave, `Catch your breath` between waves. Typed at 46 characters/s; the same text again is ignored | `src/game.js:330`, `src/hud.js:707` |
| Reel bullets | `hud.setReels(done, total)` | Story: three route bullets `1` `2` `3`, the secured ones filled, and `n/3` | `src/game.js:236`, `:605` |
| Tally | `hud.setTally(text)` | Hold the Block: `Stand by`, then `Wave {n} · {score}` after every kill, wave start and wave clear | `src/game.js:350` |
| World markers and minimap pins | `hud.setMarkers(list)` | Story: one `{id, code, label, pos, kind: 'reel'}` per reel still out; once every reel is secured one `{id: 'extraction', code: 'IPX', label: 'IPX truck', pos, kind: 'exit'}`. Hold the Block and the title: none. The HUD draws the code and the distance in whole metres | `src/game.js:333` |
| Interaction prompt | `hud.prompt({text, glyph, code, progress})` or `hud.prompt(null)` | 3.6.3 | `src/game.js:356`, `:580` |
| Banner (top centre) | `hud.warn(text, secs)` | `Contact — {DIRECTION}` 3.4 s when a reel is secured; `Wave {n} — {DIRECTION}` 3.6 s when a holdout wave starts. A new banner replaces the one on screen | `src/game.js:613`, `:686` |
| Centre message (under the banner) | `hud.message(text, secs)` | The refusal at the truck, 3.5 s, at most every 8 s; `Wave {n} in 3 / 2 / 1`, 1 s each; the browser look hint. A new message replaces the old | `src/game.js:658`, `:727` |
| Radio strip | `hud.radio(speaker, text, secs)`, `hud.clearRadio()` | 3.15 | `src/game.js:118`, `:132` |

Not driven by the flow but part of its presentation:

- **Kill feed.** The HUD listens to `enemy:killed` itself: text `Goon down` or `Buzzard down`; tag `Headshot` when the
  killing hit was on the head; a small glyph of the weapon (`chopper`, `nine`, `melee`; none for a blast). Four lines
  at most, newest at the bottom, 4.2 s each with a 0.6 s fade; frozen while paused; emptied at every run reset
  (`src/hud.js:315`, `:569`).
- **Zone band** under the minimap: `level.zoneName(x, z)` of the player's position. West of x = −30: `WEST END`. x −30
  … 22: `CHOP SHOP` north of z = −11, else `THE AVENUE`. East of x = 22: `THE CAGE` north of z = −7, `THE LOT` south
  of z = 7, `THE AVENUE` on the roadway between (`src/level.js:127`, `src/level/layout.js:158`).

### 3.17 The music-intensity driver

Last but one step of the flow's update in `intro` and `playing` (`src/game.js:766`, `src/game/music.js:16`):

```
waveAge += dt;  sinceAlert += dt;  sinceHit += dt
if waveAge >= 6 and nothing is alive and nothing is queued:   waveAge = infinity
if every reel is secured  or  the queue is not empty  or  (waveAge < 30 and enemies alive > 0):   level = 1.0    hot
else if sinceAlert < 10  or  sinceHit < 8  or  nearest living enemy < 26 m:                       level = 0.6    alert
else:                                                                                             level = 0.15   calm
audio.setMusicIntensity(level)
```

- `waveAge` is set to 0 whenever something is queued: a story wave, each pursuit arrival, a holdout wave
  (`src/game.js:476`). `sinceAlert` is set to 0 by every `enemy:alert`, `sinceHit` by every `player:hit`. All three
  start a run at "long ago".
- Outside `intro` / `playing` the flow sends calm: every frame on the title, when a run begins, when a card is
  built, on the way to the title. Between death (or completion) and the card the last level simply stays.
- Result. Story: calm until the first contact; alert around fights with the patrol; hot from each reel for as long as
  that wave is arriving or alive, at most 30 s after it was queued, then back to alert or calm; hot without pause from
  the third reel to the end. Hold the Block: hot while a wave arrives and for 30 s after it started; a wave that
  takes longer falls back to alert while the fight is close; the breather is alert for as long as the last alert or
  hit is recent, then calm **(verified)**: the level was 0.6 right after wave 1 was cleared and 0.15 after wave 2.
- What audio does with the number (summary; the audio spec owns it): it eases toward it over about half a second
  and never lets the mix fall under its own short-lived combat meter; 0.15 is filtered drums, a sketch of the bass and
  vinyl crackle; 0.6 adds full drums, hats, bass and keys; 1.0 adds string stabs and a bell hook that enter with a
  two-bar riser landing on a bar line (`src/audio/conductor.js:23`, `:199`). The four stings (`reel`, `all`, `dead`,
  `complete`) are requested by the flow (`src/game.js:617`, `:667`, `:705`, `:889`); `reel` also marks every cleared
  holdout wave.

### 3.18 Settings that change the flow

- **Difficulty** (`src/game.js:173`, `:182`): applied at every run reset and at once whenever the setting changes,
  also in the middle of a run (the drawer is reachable from the pause card). It replaces the enemy tuning table,
  re-applies the holdout multipliers of the current wave, and writes the regeneration delay and rate to the player.
  An unknown name becomes `boss`. Enemies already alive keep their hit points; the alive cap follows at once; wave
  sizes are read when a reel is secured, the pursuit budget when the third reel is secured, the pursuit interval at
  each arrival, the patrol only at a reset.
- **Mode** (`src/game.js:267`, `:914`): chosen on the title. A run keeps its mode through retry, restart and redeploy.
- **Time of day** (`src/game.js:188`, `:915`): changes the look and the first line of the location card; applied at
  once on the title, otherwise at the next run reset.

### 3.19 Two runs, second by second (Boss)

Story, from the title button at run clock 0 **(verified)**:

| Run clock | What happens |
|---|---|
| 0 | Reset under black. Patrol of 2 Buzzards and 4 Goons placed 64 – 84 m away, unaware. Objective `Take back the three master reels`, three markers |
| 0.05 – 1.3 s | Fade from black. The player can already move |
| 0.25 s | Location card (until 2.4 s) |
| 0.9 s | Radio: the intro line (on screen until 7.5 s) |
| 2.4 s | `playing`: `run.time` starts |
| R1 (reel 1 secured, 34 m from the start) | Shake, bullet 1 filled, `Two reels left`, sting, banner `Contact — {DIRECTION}`, radio line; wave B G B G G G G queued; music hot at once |
| R1 + 1.6 … R1 + 6.7 s | Seven arrivals 0.85 s apart, as far as the cap of 11 alive allows |
| R2 | `Last reel`; wave of 3 + 6, last member due at + 8.4 s |
| R3 | `Get to the IPX truck`, the `IPX` marker, sting `all`, radio line; wave of 4 + 7, last member due at + 10.1 s |
| R3 + 12 s, then every 4 s | Pursuit check: one arrival (then 5.5 s to the next check) while fewer than 4 are alive, 8 in all; else everyone within 90 m is sent after the player |
| X (the zone, 52 m from reel 3) | Doors open, sting, final radio line; X + 3.3 s the debrief |

Hold the Block **(verified)**:

| Run clock | What happens |
|---|---|
| 0 | Reset. Cases closed. Objective `Vultures inbound`, tally `Stand by` |
| 0.25 s, 0.9 s | Location card with `One block. Endless Vultures.`; the holdout radio line |
| 3.5 s | Wave 1: banner `Wave 1 — {DIRECTION}`, `Hold the block`, `Wave 1 · 0`, music hot |
| 4.7 … 9.9 s | Seven arrivals G B G B G B G, 0.86 s apart |
| C (last one dies) | Next frame: + 500, + 90 rounds, + 35 HP, radio line, `Catch your breath`, sting |
| C + 6, + 7, + 8 s | `Wave 2 in 3`, `Wave 2 in 2`, `Wave 2 in 1` |
| C + 9 s | Wave 2: nine members, HP × 1.07, damage × 1.05, cooldown × 0.97, alive cap 12. After it (and every even wave) the explosives come back |

### 3.20 Edge cases

1. **Pause during the intro** ends the intro first (`intro` → `playing` → `paused`, fade cleared, card removed). If
   that happens before 0.9 s the first radio line is never said; before 0.25 s the location card never shows.
   **(verified)**
2. **Contact during the intro**: the contact line is only queued in `playing`; an alert in the intro does not use it
   up, so it comes with the next alert.
3. **The low-health line** is said once per run and is not re-armed by regenerating.
4. **Waves pile up.** Each reel appends its wave to the same queue; while the cap is reached they wait. A player who
   takes all three reels on Boss without a kill has 22 arrivals waiting behind 11 living enemies **(verified)**, and
   the pursuit cannot start until that queue is empty.
5. **Dropped arrivals.** With all 12 Goon slots alive and the cap not yet reached (possible on Kingpin in Story, cap
   13, and from holdout wave 7 on, when a wave has more than 12 Goons), a due Goon is refused, retried five more times
   1.5 s apart, then dropped. The wave is that much smaller; nothing compensates.
6. **A holdout wave is over only when the queue is empty and nobody lives.** Killing everyone on the block while
   members are still due does not clear it.
7. **The banner direction is fixed when the wave is queued.** A Goon whose point the player has walked up to is
   re-placed at arrival and may come from another side.
8. **Switching reels** while holding drops the first reel's bar to 0 at once; walking away only drains it.
9. **Death beats the truck.** The zone is tested at the start of a frame, before the player moves. A player who steps
   into it and is killed on that same frame is dead: the next frame no longer tests the zone.
10. **Holdout kills only score in `playing`.** A tank that goes off after the player died scores nothing.
11. **The best score is written only when a death card is built.** Closing the game in the middle of a Hold the
    Block run loses that run's score.
12. **Difficulty can be changed in a pause** and applies at once; the Hold the Block score is not weighted by
    difficulty and the best score is shared by all three.
13. **Copy assumes three reels.** `run.total` comes from the level, but the objective lines, the radio lines and the
    refusal say "three".
14. **Two start requests in one frame** (a click and Enter together) are one start.
15. **`complete` leaves the fight running.** Enemies that are alive keep shooting at an invulnerable player behind the
    debrief until a new run clears them.

### 3.21 Where the documents and the code differ (the code wins), and the stub

| Document | Code |
|---|---|
| Title eyebrow `IPX PRESENTS · HOLLIS, QUEENS · 02:14 AM` (`docs/DESIGN.md:53`) | `IPX PRESENTS · HOLLIS, QUEENS` (`src/config/text.js:7`), as `docs/DESIGN.md:286` already says |
| Location card `… · 02:14 AM` (`docs/DESIGN.md:41`) | By time of day: `… · 4:15 PM` by day (the default), `… · 02:14 AM` by night (`src/config/text.js:27`) |
| Boot line "Waiting on the 2 AM train" (`docs/DESIGN.md:88`) | `Waiting on the next train` (`src/config/text.js:201`); the code also has a context-lost line (`:204`) |
| Intro radio line "first start only" (`docs/DESIGN.md:70`) | Every start from the title; never on retry, restart or redeploy (`src/game.js:256`, `:843`) |
| No intro copy for Hold the Block | Its own tagline and first radio line (`src/config/text.js:25`, `:138`) |
| Story death card: "Time on the block", "Reels recovered n/3" (`docs/DESIGN.md:80`) | Also `Vultures dropped` (`src/ui/logic.js:424`) |
| Death and debrief cards have one button (`docs/DESIGN.md:81`, `:83`) | Both also have `Back to title`; `Best` carries a `New best` flag; the debrief has the foot `An IPX production` (`src/ui/copy.js:40`) |
| Start near (−40, 0, 8); reel 2 near (−9, 0, −21); reel 3 near (33, 0, −22); truck and extraction near (40, 0, 27) (`docs/DESIGN.md:179`, `:191`, `:201`, `:203`) | Start (−37.4, 0.15, 8.15); reels at (−9.5, 0, −21.5) and (35.25, 0, −22.5); truck at (41.3, 0, 29.7); the zone is a separate point 5.4 m behind the truck's centre, (35.9, 0, 29.7) (`src/level/data.js:7`) |
| "about 28 ground + 16 air" spawn points (`docs/DESIGN.md:216`) | 29 + 17 (`src/level/data.js:24`, `:60`) |
| Zone band `THE CAGE / THE LOT` (`docs/DESIGN.md:306`) | Three names in the east zone: the roadway between the court and the lot reads `THE AVENUE` (`src/level.js:127`) |
| `explosive:lit {item, pos}`, `train:pass {phase, duration}` (`docs/CONTRACT.md:144`, `:160`) | Each carries one more key: `fuse`, `dir` |
| Difficulty table, holdout formulas, score, resupply, music levels (`docs/DESIGN.md:119`, `:136`, `:261`) | Match the code exactly (`test/flow-logic.test.js:35`, `:60`) |

`src/stubs/game.js` is a simplified flow that the web build falls back to when the real module fails to load. Do not
port it. Where it differs from the real flow:

| Stub | Real flow |
|---|---|
| A new radio line replaces the one on screen (`src/stubs/game.js:220`) | Lines queue (3.15) |
| Story waves start with a Goon; holdout waves alternate Goon, Buzzard from the front (`src/stubs/game.js:305`) | Buzzard first; holdout Buzzards spread evenly (3.6.5, 3.11) |
| The pump only looks at the head of the queue and a refused spawn is lost (`src/stubs/game.js:321`) | First due entry, retries (3.8) |
| A reel's bar is lost as soon as the player leaves reach (`src/stubs/game.js:361`) | It drains at 1.6 per second |
| Spawn pick without strict mode or jitter, sight probe 1 m up (`src/stubs/game.js:256`) | 3.7 |
| Title camera on straight segments (`src/stubs/game.js:549`) | Catmull-Rom with ease and sway (3.4) |
| Music: hot while anything is queued, a holdout wave is active or every reel is secured (`src/stubs/game.js:645`) | 3.17 |
| No re-alert in Hold the Block, no pause on lost focus, no guard against a double start | Present |

---------------------------------------------------------------------------------------------------

## 4. Unreal mapping

### 4.1 Conversions that matter here

- Position: Unreal (X, Y, Z) = (x, z, y) of the web × 100. X is east, Y is south, Z is up. Every horizontal distance in
  section 3 is just × 100.
- Direction: a web offset (dx, dz) is (ΔX, ΔY) in Unreal. The compass sector of 3.6.6 becomes
  `round(atan2(ΔX, −ΔY) / 45°) mod 8`, 0 = `NORTH` = toward −Y.
- Yaw: Unreal yaw in degrees = −90 − (web yaw in degrees). Web yaw 0 (north) is Unreal −90; the start's web yaw of
  −85.42° is Unreal −4.58° (east, a touch toward north).
- Feet: web positions of the player are his feet. An Unreal character reports the centre of its capsule: subtract the
  half-height before applying the height tolerances (250 cm at a reel, 350 cm at the truck) and before adding the
  160 cm eye offset of the spawn sight test.
- Field of view: the web values are **vertical** angles. Unreal's camera FOV is horizontal by default:
  `hFOV = 2 · atan(tan(vFOV / 2) × aspect)`. At 16:9 the title's 50° is 79.3°, and the setting's 60 … 95° (default 74°)
  is 91.5 … 125.5° (default 106.5°). Either convert, or constrain the cameras to the vertical axis and keep the web
  numbers.
- Times, rates, scores, probabilities, character counts and typing speeds are unchanged.

### 4.2 Converted constants

| Constant | Web | Unreal |
|---|---|---|
| `interact.range`, `vertical`, `freeRange` | 2.2 m, 2.5 m, 0.9 m | 220 cm, 250 cm, 90 cm |
| `interact.facingDot` | 0.45 | keep the dot product; the half-cone is 63.3° |
| `extraction.radius`, `vertical` | 2.5 m, 3.5 m | 250 cm, 350 cm |
| `spawn.far`, `patrolMinDistance` | 18 m, 32 m | 1,800 cm, 3,200 cm |
| `spawn.score.farExtraOver` | 30 m | 3,000 cm |
| `spawn.score.nearDivisor` | 1 point per 4 m short | 1 point per 400 cm short |
| `spawn.jitter` | ± 1.2 m | ± 120 cm |
| Floor tolerance of a jittered ground position | 0.3 m | 30 cm |
| `spawn.airMinHeight`, `airLift` | 2.5 m, 6 … 9 m | 250 cm, 600 … 900 cm |
| `spawn.eyeHeight`, `probeHeight` | 1.6 m, 1.2 m | 160 cm, 120 cm |
| `spawn.tooClose` | 9 m | 900 cm |
| `spawn.alertRadius` | 60 m | 6,000 cm |
| `spawn.fallbackRing` | 26 m | 2,600 cm |
| `pursuit.realertRadius`, `holdout.realertRadius` | 90 m | 9,000 cm |
| `music.nearDistance` | 26 m | 2,600 cm |
| `titleCamera.speed` | 1.15 m/s | 115 cm/s |
| `titleCamera.sway` side, lift, roll | 0.07 m, 0.04 m, 0.005 rad | 7 cm, 4 cm, 0.29° |
| `titleCamera.sway.rate` | 0.42 rad/s: periods of 15.0 s (side), 11.4 s (lift), 19.4 s (roll) | unchanged |
| `titleCamera.fov` | 50° vertical | 79.3° horizontal at 16:9 |
| Title path length, loop | 155.54 m, 135.25 s | 15,554 cm, 135.25 s |
| World marker: hidden within, anchor above a reel / the exit | 3 m, 1.9 m / 1.2 m | 300 cm, 190 cm / 120 cm |
| Goon run speed per difficulty | 4.5 / 5.0 / 5.4 m/s | 450 / 500 / 540 cm/s |

### 4.3 The flow's authored points in Unreal space

| What | Web (x, y, z) | Unreal (X, Y, Z) cm |
|---|---|---|
| Player start | (−37.4, 0.15, 8.15), yaw −π/2 + 0.08 | (−3740, 815, 15), yaw −4.58° |
| Reel 1 | (−4, 0, 1) | (−400, 100, 0) |
| Reel 2 | (−9.5, 0, −21.5) | (−950, −2150, 0) |
| Reel 3 | (35.25, 0, −22.5) | (3525, −2250, 0) |
| Extraction zone centre | (35.9, 0, 29.7) | (3590, 2970, 0) |
| IPX truck | (41.3, 0, 29.7), nose east | (4130, 2970, 0), yaw 0 |
| Play bounds | x −46 … 46, z −34 … 34 | X −4600 … 4600, Y −3400 … 3400 |
| Zone `west` | x −46 … −30 | X −4600 … −3000 |
| Zone `shop` | x −30 … 22, z −34 … −11 | X −3000 … 2200, Y −3400 … −1100 |
| Zone `avenue` | x −30 … 22, z −11 … 34 | X −3000 … 2200, Y −1100 … 3400 |
| Zone `lot` | x 22 … 46 | X 2200 … 4600: `THE CAGE` for Y < −700, `THE LOT` for Y > 700, `THE AVENUE` between |

The 29 ground and 17 air spawn points belong to the level export; use the positions after the level has nudged them
(2.15).

Title path (`src/level/data.js:153`). The camera passes key i while looking at look target i.

| Key | Web position | Web look target | Unreal position cm | Unreal look target cm | Reached at **(derived)** |
|---|---|---|---|---|---|
| 1 | (−38.6, 4.4, −1.6) | (−5, 2, −0.5) | (−3860, −160, 440) | (−500, −50, 200) | 0 s |
| 2 | (−31.5, 4.2, −2.5) | (−12, 1.8, 0.5) | (−3150, −250, 420) | (−1200, 50, 180) | 7.9 s |
| 3 | (−21, 3.3, 2.6) | (−9, 1.4, 1.5) | (−2100, 260, 330) | (−900, 150, 140) | 19.5 s |
| 4 | (−13.4, 2.4, −0.4) | (−3, 1, −1.5) | (−1340, −40, 240) | (−300, −150, 100) | 27.0 s |
| 5 | (−6.6, 2.2, −4) | (−4, 0.8, 1) | (−660, −400, 220) | (−400, 100, 80) | 33.7 s |
| 6 | (−12.4, 2.3, −5.6) | (−11.6, 2, −14) | (−1240, −560, 230) | (−1160, −1400, 200) | 38.9 s |
| 7 | (−10.2, 2.1, −13.4) | (−9.5, 0.9, −21.5) | (−1020, −1340, 210) | (−950, −2150, 90) | 45.6 s |
| 8 | (−14.2, 4.2, −22.6) | (−4, 1.2, −19) | (−1420, −2260, 420) | (−400, −1900, 120) | 54.0 s |
| 9 | (6.4, 2, −22.1) | (8.8, 2.4, −10) | (640, −2210, 200) | (880, −1000, 240) | 70.7 s |
| 10 | (12, 3.6, −1.4) | (24, 2, 1) | (1200, −140, 360) | (2400, 100, 200) | 87.9 s |
| 11 | (31.5, 3.8, −3) | (35.25, 1, −22.5) | (3150, −300, 380) | (3525, −2250, 100) | 104.4 s |
| 12 | (30.5, 4.6, −1) | (40, 2.4, 22) | (3050, −100, 460) | (4000, 2200, 240) | 106.5 s |
| 13 | (32.2, 3.4, 14.6) | (40.5, 1.6, 28.5) | (3220, 1460, 340) | (4050, 2850, 160) | 121.0 s |
| 14 | (34.6, 1.8, 27.8) | (42, 1.7, 30.2) | (3460, 2780, 180) | (4200, 3020, 170) | 135.2 s |

### 4.4 Mechanic by mechanic

Class names are suggestions; the split is what matters: one flow object that ticks before the pawns, thin actors in
the level, widgets that only display.

| Mechanic | Natural Unreal feature | Notes |
|---|---|---|
| State machine and run record | A flow object owned by the game mode with an enum state and an explicit per-frame update; a game-state object mirrors `run`, `holdout` and the debug view for the UI and for tests | Give it a tick prerequisite so that it runs before the player character and the AI (3.1). One persistent level: the title is the same world with another view target, no level travel |
| Frame step | Clamp the delta time the flow uses to 0.05 s | Keeps "below 20 fps the game slows down" |
| Pause | `SetGamePaused(true)`: world time, AI, physics, effects and world sound stop; the menu widgets keep ticking | Triggers: the pause input action, application deactivation (window focus lost, console suspend), controller disconnect. Resume debounce 0.35 s. The web game keeps the music audible in a pause (45 %, low-passed): flag the music to play while paused and apply a pause mix |
| Run clock and countdowns | Accumulate the (clamped) delta in the flow update while the state is Intro or Playing | Engine timers also stop on pause, but explicit accumulators keep the order of 3.8 – 3.11 inside one frame |
| Title fly-through | A camera actor as view target, driven from baked keys (a level sequence or curve assets sampled from the web curve), with the sway added on top; the loop fades through `SetManualCameraFade` | Bake rather than rebuild: an Unreal spline is parameterised differently from a centripetal Catmull-Rom curve and the look target must be read at the same parameter as the position |
| Intro and end fades | `PlayerCameraManager->SetManualCameraFade(alpha, black)` | alpha is the web fade value |
| End desaturation | Colour saturation of a post-process blend on the camera (or an unbound volume) | Ease with `x = target + (x − target) · exp(−rate · dt)` |
| Hold to grab | An Enhanced Input action read as a plain "is down" value; the fill and drain live in the flow | Do not use the Hold trigger: it resets on release instead of draining at 1.6 per second |
| Reel in reach | A sphere overlap of 220 cm around each case to collect candidates, then the test of 3.6.2 | Horizontal distance and horizontal facing only |
| Reel case | An actor with the states Live, Grabbing(t), Taken that drives its lid, reel, beacon, light shaft, progress bar and boombox sound | 5 |
| Extraction | A trigger tested every frame while the player is inside (the refusal repeats every 8 s): radius 250 cm, ± 350 cm | The truck actor has Idle and Open |
| Spawn points | Placed actors or the exported list, each with a kind (ground or air) and a zone | |
| Spawn scoring | Plain code over the list with the formula of 3.7 and one line trace per point on a channel that only static, bullet-stopping geometry blocks | The Environment Query System (generator: actors of class; tests: distance, trace, a custom "recently used" test) is the engine's own tool for scored point picking and is an acceptable alternative, but plain code reproduces the numbers exactly. Cost: at most 30 picks × 29 points on the frame a full holdout wave is queued |
| Ground jitter | `ProjectPointToNavigation` with a small extent for "walkable", a short down trace for the floor height | |
| Arrival queue and pump | An array of {type, due, position, tries} handled in the flow update, one arrival per frame | |
| "Alert everyone within r" | One call on the enemy manager that walks the living units (or `UAISense_Hearing::ReportNoiseEvent` with range r and a tag the controllers treat as "the player is there") | It must also re-point units that are already searching, not only unaware ones |
| Difficulty | A data table with three rows holding the flow columns and the enemy columns of 2.10 | Applied at reset and at once on change |
| Holdout formulas | Plain functions, not curve assets: they must be exact. Unit tests from the table in 2.11 | `round` must round halves up (wave 13: 7.5 → 8 Buzzards) |
| Score and best | Game state; one save-game slot for the best | |
| Statistics | Counters fed where the facts happen: `shots` when a round leaves the gun, `hits` when a player round damages an enemy, `kills` and `headshots` in the enemy death path, by cause | Every blast counts as the player's (3.14) |
| Radio | A queue object with the timing of 3.15 feeding a subtitle widget; if voice is recorded the slot becomes max(typing + hold, clip length) + 0.3 s | |
| Banners, messages, objective, tally, prompt, feed, cards | UMG widgets; CommonUI for the menu stack, focus, and device-specific glyphs (`E` / `X`) | Typewriter: show `floor(t × rate)` characters |
| Music intensity | One float parameter on the music player (a MetaSound mixing the stems, or layered components on a Quartz clock); stings started quantised to the next beat with Quartz | The driver stays in the flow |
| Events | Native multicast delegates on a world subsystem, or the Gameplay Message Subsystem with one gameplay tag per row of 2.18 and a payload struct each | Deliver synchronously, as the web bus does |
| Settings | A `UGameUserSettings` subclass for quality, field of view, sensitivity, invert, volume and weapon position; a save game for difficulty, mode, time of day and the best score | Quality: overall scalability level 0 … 3 for low … ultra; Auto = the hardware benchmark, then engine dynamic resolution |
| Debug | Console commands or a cheat manager for "secure the next reel", god mode, "start in mode X without intro" | These replace `debugGrab`, `god`, `autostart`, `mode` and let automation tests replay 3.19 |
| Boot lines | The eleven lines as loading-screen status lines, in order | Cosmetic; they no longer map to real steps |

### 4.5 Data

The exporter (`tools/ue-export/export.cjs`) boots the web game and writes its real data to
`unreal/MurderInc/Content/Data/`; the schema belongs to `08-data-export.md`. Where the flow's data was when this was
written (the exporter was still being worked on: check the keys before wiring loaders):

| Need | File → key |
|---|---|
| Every number of 2.3 – 2.13 | `config.json` → `flow` (`timing`, `post`, `titleCamera`, `interact`, `extraction`, `spawn`, `pursuit`, `difficulty`, `holdout`, `rating`, `music`, `pacing`). A formula is `{"$function": {params, source, samples}}`: implement it from the source text and test it against the samples |
| Enemy side of the difficulty rows, pool caps | `config.json` → `enemies.difficulty`, `enemiesResolved`, `enemies.pool` |
| Settings defaults and the storage key; quality presets | `config.json` → `settings`, `quality` |
| The copy of 2.19 | `text.json` → `text` (the copy deck), `interface` (interface-only copy), `input` (glyphs, hints, touch button names), `page`, `brand`. A line with inserted values is `{"$template": {template, params, formats, example}}` and uses `{name}` placeholders as 2.19 does |
| Start, reels, extraction zone and truck, zones, bounds | `level.json` → `playerStart`, `objectives`, `extraction` (with `truck`), `zones`, `bounds`; each has `web` and `ue` values |
| Spawn points | `level.json` → `enemySpawns.points`: 46, after the nudge, with `type`, `zone` and `ue.pos`. The `facing` given there is derived by the exporter; the game spawns every enemy with a random yaw |
| Title path | `level.json` → `cinematicPath.points`: 14 keys with `ue.pos`, `ue.look` and a rotator. The curve is open: the loop restarts through black, it does not close on itself |

Numbers are best read into a data asset at cook time. Copy belongs in a string table keyed by the Key column of 2.19,
formatted with named arguments (`{glyph}`, `{code}`, `{n}`, `{score}`, `{secs}`, `{DIRECTION}`, `{error}`, `{tier}`,
`{key}`).

### 4.6 Browser-only behaviour that is not ported

The mouse-capture handling and the `input:lock` event; the drag-look fallback, its hint lines and the look-mode centre
message; pausing on `visibilitychange` and `blur` (application deactivation replaces them); `render:lost`,
`render:restored` and the context-lost line; `quality:auto` (engine scalability and dynamic resolution replace it); the
module boot order and the stub modules; URL parameters; "sound starts on the first click"; the notes about browsers in
the controls tables; and the title and boot note (`title.note` in 2.19), which is false for the Unreal build.

---------------------------------------------------------------------------------------------------

## 5. Art and audio implications

**Master reel case** (three identical hero props, the objective; `src/props/gameplay.js:24`,
`src/config/catalog.js:141`). A black road case with aluminium edging and ball corners, body 0.42 × 0.50 × 0.32 m
(width, height, depth) on a 3 cm toe plate with a 0.12 m lid hinged along its back, strapped to a two-wheel hand truck
whose handle tops out at 0.96 m; a boombox stands beside it; an IPX tag and a small tracker with a lit display are
clipped to its front; a beacon sits on a short mast at 1.22 m, so the whole prop reaches about 1.35 m and shows over
waist-high cover. Footprint to keep clear: 0.9 × 0.6 m, 1.05 m high. In the open case: foam and a gold tape reel 0.27 m
across leaning on its tape box. It needs three states and the moves between them:

| State | Look |
|---|---|
| Live | Lid open (95° back), reel on show, beacon and a 6 m shaft of light pulsing slowly (2.2 rad/s), boombox lit and playing |
| Grabbing(t) | The same with a fast pulse (9 rad/s) and a gold bar, 0.34 m long, growing from left to right inside the lid with t |
| Taken | Reel gone, lid drops shut in 0.3 s, every light out, boombox silent |

Build it as separate parts (body, lid, reel, beacon lens) with emissive materials driven by parameters. The open
design problem is daylight: the web version leans on the mast's silhouette and the beacon because a light shaft barely
reads in sun.

**IPX truck** (`src/config/catalog.js:77`, `docs/CONTRACT.md:367`). An armoured vault truck, 6.8 m long, 3.0 m high,
2.5 m wide, nose east, with the IPX livery, hazard lights and an exhaust. Two states: Idle (rear doors shut) and Open
(both rear doors swing open over 1.1 s and the vault interior lights up). The extraction zone is a disc of 2.5 m radius
centred 2.0 m behind the doors. Nothing marks it in the web game but the HUD marker; the photoreal version would
benefit from a readable cue (light spilling from the vault, a ramp, a painted bay), without changing the radius.

**Title fly-through.** Fourteen held compositions (4.3), camera 1.8 to 4.6 m above the street: the avenue under the El
from the station, past the Vultures' van to reel 1, in through the shop's roll door, across the shop floor, out the
side door and up the alley, down the avenue, through the Cage gate at reel 3, across to the lot and onto the truck.
Every one of them is a beauty shot held for seconds at a 79° horizontal field of view: these are the places where
modelling, texturing and lighting must be finished first. The block is alive (train, steam) and empty of enemies; the
three cases glow.

**Places where enemies appear.** Goons are simply placed at ground points (doorways, behind vans, the alley's dead
end, the rear lane); Buzzards at air points 8.6 to 16.2 m up over roofs and beside the El deck. The scoring prefers
points the player cannot see but does not guarantee it. In a photoreal game a figure popping in is far more visible
than in the stylised original: each ground point should be dressed as a believable way in (an open door, a gap, a
parked van's blind side) and kept free of clutter; see 6 for the decision this needs.

**Interface.** Cards with a red top edge and red title (death) or a gold top edge (debrief), a gold-record glyph for
the certification, six rating names, route bullets `1`, `2`, `3`, `IPX` in their line colours (#f2762e, #1fa463,
#3b82f0, #f6c21a: `src/config/brand.js:36`), the IPX lozenge, the location card with a gold rule on its left, a
top-centre banner with a flicker, a radio strip with a gold speaker label and dot, the typed objective line. Fonts:
Anton for the wordmark and card titles, Archivo for everything else (`src/config/brand.js:54`). The interface spec owns
the layout; this list is what the flow needs to exist.

**Screen treatments.** Death: saturation down to 12 %, 55 % black, under the death camera. Completion: 70 % saturation,
72 % black behind the debrief. Fades from black for the title loop and the intro.

**Two times of day.** The flow switches the whole look between runs and prints the matching clock on the location
card: both looks must exist.

**Music** (`src/audio/music.js:11`, `:16`, `:292`, `:420`). An original boom-bap beat in F minor at 92 BPM as seven
stems of exactly one eight-bar loop each (20.87 s): drums, hats, bass, keys, strings, bell, crackle, plus a two-bar
riser and an impact. Three intensity levels (3.17) and four mixes (title, play, dead, complete). Four stings: `reel`
(a reel secured, and every cleared holdout wave), `all` (the last reel; it also forces the riser), `dead`, `complete`.
Stings start on the next beat (a 0.65 s grid), except `dead`, which is immediate; `reel` and `all` duck the stems to
40 % for 3.4 s, `complete` to 12 % for 7 s (`src/audio/conductor.js:265`).

**Radio.** There is no recorded voice: nine lines of subtitle and a squelch at the start of each. A voiced dispatcher
is the obvious upgrade for this build: one speaker, dry and calm, nine lines (2.19), of which the wave-clear line
carries a number. The squelch in and out are two short one-shots.

**Reel sounds.** A loop while holding whose pitch rises with the bar (0.85 → 1.25 of normal), a latch and two-note
confirm when the reel is secured, and a muffled boombox loop in 3D at every live case, in phase with the score, that
stops when its reel is taken; none in Hold the Block (`src/audio/react.js:252`, `src/audio/ambience.js:211`).

**State mixes** (`src/audio/react.js:278`; details in `07-ui-audio.md`). Title: ambience at 60 %, the title music mix.
Play: full. Pause: effects and ambience silent, the music at 45 % behind a 1.3 kHz low-pass, interface sounds still
play (`src/audio.js:584`). Death: the world is low-passed at once (to about 600 Hz, settling near 1 kHz for as long as
the state lasts: `src/audio.js:745`, `:583`), ambience 70 %, the sparse dead mix. Completion: ambience 80 %. Interface:
a click and a hover sound for every button. A heartbeat loop fades in under 35 % health while playing
(`src/audio/react.js:350`).

---------------------------------------------------------------------------------------------------

## 6. Open questions and risks

**Open questions**

1. **Voice.** Should the IPX VAULT lines be recorded? If so, the wave-clear line needs either numbers ("Wave seven
   down") or a spoken line without the number.
2. **Title note.** `Every street, sound and beat is generated in your browser. No art or audio files.` cannot ship in
   the Unreal build. Drop it or replace it, and with what?
3. **Best score.** One number is shared by Hustler, Boss and Kingpin, and difficulty can be changed in a pause without
   touching the score. Keep that, or keep a best per difficulty and lock the difficulty during a Hold the Block run?
4. **Dropped arrivals.** The web game drops a queued Goon after six refusals when all 12 slots are alive (3.20 item
   5). Keep the caps and the drop, or let arrivals wait as they do at the alive cap?
5. **Enemies appearing in view.** Is "prefer hidden points" enough for a photoreal game, or should arrivals be limited
   to points out of sight, or enter through doors and from vans with an animation?
6. **Title camera.** Bake the web curve (exact) or re-author the fly-through as a sequence for the new art?
7. **Pause card.** It offers no way back to the title. Add one, and if so, what happens to a Hold the Block score?
8. **Platform events.** Which events pause the Unreal build (focus loss, controller disconnect, overlay), and is touch
   still a target device?
9. **Rating thresholds.** 270 s and 400 s were tuned to this block and these movement speeds. Re-tune if either
   changes?
10. **Resupply.** The line says "Resupply at your feet" but nothing is placed in the world. Add a pickup, or keep the
    instant top-up?
11. **Unused copy.** Reel labels, weapon blurbs, melee names, `Master reel`, explosive and enemy names and the time
    note are written but never shown. Should the new interface use them?
12. **Spawn facing.** The game gives every arrival a random yaw; the export adds a derived facing to each spawn point.
    Which one should the Unreal build use?

**Risks**

- **Order inside a frame.** The flow must update before the player and the enemies and must place at most one arrival
  per frame; if Unreal's tick order is left to chance, wave clears, kill scores and the contact line can shift by a
  frame or double up.
- **Feet against capsule centre, vertical against horizontal field of view** (4.1): both are silent off-by-a-lot errors.
- **What "hidden" means.** The spawn sight test must ignore enemies, chain-link, glass and invisible walls and must
  start 160 cm above the player's feet, not at the camera; a different trace channel changes where every wave comes
  from.
- **Kill attribution.** Every blast kill is the player's, including blasts started by an enemy round and by a crashing
  Buzzard. A stricter instigator rule in Unreal would lower kills and Hold the Block scores.
- **Rounding.** Buzzards per holdout wave rely on halves rounding up (7.5 → 8 from wave 13); scores rely on
  `round(base × scale)`. Test against 2.11.
- **Randomness.** The web flow draws from a seeded mulberry32 stream; Unreal's random stream is a different
  generator. Runs cannot be compared number for number unless that generator is ported; compare distributions instead.
- **Time.** `run.time` counts only `playing`; all flow timers stand still in a pause. Engine wall-clock timers would
  break both.
- **The radio's closing squelch** is scheduled in real time `hold` seconds after a line starts
  (`src/audio/react.js:268`): it sounds before the typed line is finished and ignores a pause. Port the intent (a
  squelch when the line leaves), not the behaviour.
- **Copy assumes three reels and a 9 s breather.** The numbers are written into the lines; changing `total` or
  `breather` needs new copy.
