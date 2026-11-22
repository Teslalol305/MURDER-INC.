# 03 — Enemies: the Goon and the Buzzard

Port spec for the Unreal Engine 5 rebuild of MURDER INC. The web game is the ground truth. Everything below was read
from the source files listed in 2.1. Values marked **(measured)** are not typed anywhere in the source: they were
obtained by running the game's own code headless in Node (the model builders, the pose solver, and the complete
enemies module on the real level geometry, with stand-in props) and reading the results back. Values marked
(derived) are arithmetic on source values.

How to read this document:

- Web units are metres, seconds and radians. +Y is up, north is −Z, east is +X. Yaw 0 faces −Z and grows
  counter-clockwise seen from above (turning left); forward = (−sin yaw, 0, −cos yaw) (`docs/CONTRACT.md:20`).
  Section 4 gives the Unreal values (cm, cm/s, degrees).
- `[a, b]` is a uniform random range. Every random draw of the enemies comes from their own seeded stream
  (mulberry32, default seed 9001, URL parameter `eseed`): `src/config/enemies.js:9`, `src/enemies.js:52`,
  `src/core/rng.js:22`.
- `damp(x, target, rate, dt)` = `target + (x − target) · e^(−rate · dt)`: an exponential approach that covers 90 % of
  the way in 2.3 / rate seconds (`src/core/util.js:25`). `moveToward(x, target, step)` is a linear approach that never
  overshoots (`src/core/util.js:57`). `smoothstep(a, b, x)` is the cubic 0…1 step (`src/core/util.js:35`).
- A Goon's position is his feet. A Buzzard's position is the centre of its airframe (`docs/CONTRACT.md:462`).
- Neighbouring specs in this directory, as named at the time of writing: `02-weapons-combat.md` (the player's guns,
  hitscan, melee, explosions), `04-flow.md` (who spawns what and when), `07-ui-audio.md` (how enemy events are shown
  and heard). Where this document touches their ground it says so and only gives what the enemies need.

---------------------------------------------------------------------------------------------------

## 1. Overview

The enemies are the Vultures, the crew holding the block, and they are the whole fight. **Goons** are masked gunmen
on foot and the majority type: they notice the player by sight or sound, run to a firing position 8 to 18 m away
(preferring authored cover that still has a shot), warn with a growing weapon-light flare for half a second, fire a
4 to 6 round SMG burst, kneel behind their cover while the gun cools, relocate after one or two bursts, and inside 3 m
drop everything for a telegraphed dash with a steel pipe. **Buzzards** are armed quadcopters: they orbit the player
13 to 23 m out and about 5 to 7 m up, steady themselves, flare a red eye, and fire three slow red tracer bolts that the
player can side-step. Both get more accurate the longer they keep line of sight, both lose that accuracy within about
two seconds of the player breaking it, and a shared pool of attack tokens caps how many of them may shoot at the same
moment, so the pressure rises with difficulty but stays readable. For the player this subsystem provides the threat,
the reason to use cover, the audio-visual warnings to react to, and the feedback of a kill: a Goon folds onto the
street and stays there as a body, a Buzzard spins down trailing smoke and bursts where it lands.

---------------------------------------------------------------------------------------------------

## 2. Facts

### 2.1 Source map

| File | Lines | What it holds |
|---|---|---|
| `src/config/enemies.js` | 258 | All tuning: pools, day / night look, `buzzard`, `goon`, `ai`, the three difficulty overlays |
| `src/enemies.js` | 658 | Shared part: pools, public API, mode machine, sight and hearing, accuracy ramp, attack tokens, hit tests, damage, bodies, per-frame budgets |
| `src/enemies/logic.js` | 767 | Pure rules: tokens, perception, spread, fire-position cost, ray tests, bolt sweep, lead, flight planning (El deck, climbing, push-out, doorways) |
| `src/enemies/goon.js` | 1127 | The Goon in the world: spawning, path following, fire positions, the engage state machine, the rush, death, body |
| `src/enemies/goon-anim.js` | 900 | The Goon's procedural pose solver: gait, stances, gun holds, pipe swing, recoil and flinch springs, the collapse |
| `src/enemies/goon-model.js` | 256 | The Goon mesh: bones, joints, three outfits, the SMG, the pipe, colours |
| `src/enemies/rig.js` | 520 | Rigid skinning, the shared enemy material (self-lit parts, lamp, hit flash, rim light, dither fade), two-bone IK |
| `src/enemies/buzzard.js` | 912 | The Buzzard in the world: flight, feelers, orbit, attack, damage, the fall and the burst |
| `src/enemies/buzzard-model.js` | 191 | The Buzzard mesh: hull, arms, rotors, gimbal, eye, gun, strobes; rotor and gimbal pose |
| `src/enemies/bolts.js` | 190 | The Buzzard's projectiles: pool, sweep against world and player, streak drawing |
| `src/enemies/glow.js` | 300 | One instanced additive batch for every flare, strobe and bolt streak; one for the rotor blur discs |
| `src/stubs/enemies.js` | 465 | A stand-in with the same API (dummies that never move). Not to be ported: see 3.14 |

Related code this subsystem depends on: `src/combat.js` (hitscan, melee, explosions), `src/physics.js` (box world, nav
grid), `src/config/flow.js` and `src/game.js` (who spawns what and when), `src/audio/sfx-enemies.js` and
`src/audio/react.js` (sounds), `src/config/weapons.js` (head multiplier).

### 2.2 Values that change with difficulty (effective)

The module boots on Boss (`src/enemies.js:113`). `setDifficulty(table)` first restores every base value and then lays
the table over it (`src/enemies.js:42`, `src/enemies.js:620`); the game calls it on every reset
(`src/game.js:176`). Hit points are fixed when a unit spawns; everything else is read live (`src/enemies.js:300`).
Only the rows below differ between difficulties; every other number in this document is the same on all three.

| Value | Hustler | Boss (default) | Kingpin | Source |
|---|---|---|---|---|
| Goon hit points | 90 | 110 | 130 | `src/config/enemies.js:245`, `:250`, `:255` |
| Goon SMG damage per round | 4 | 6 | 8 | same lines |
| Goon rounds per burst | 4 | 5 | 6 | same lines |
| Goon burst length, first to last round (derived: (n − 1) × 0.11 s) | 0.33 s | 0.44 s | 0.55 s | `src/config/enemies.js:167` |
| Goon cooldown after a burst | [1.8, 3.0] s | [1.4, 2.4] s | [1.0, 1.9] s | `src/config/enemies.js:245`, `:250`, `:255` |
| Goon spread at exposure 0 → 1 (rad per axis) | 0.12 → 0.045 | 0.095 → 0.038 | 0.08 → 0.032 | same lines |
| Goon pipe damage | 15 | 22 | 30 | same lines |
| Goon run speed | 4.5 m/s | 5.0 m/s | 5.4 m/s | same lines |
| Buzzard hit points | 45 | 55 | 60 | `src/config/enemies.js:244`, `:249`, `:254` |
| Buzzard bolt damage | 7 | 10 | 13 | same lines |
| Buzzard telegraph | 0.55 s | 0.46 s | 0.38 s | same lines |
| Buzzard cooldown after a volley | [1.9, 3.3] s | [1.4, 2.5] s | [1.0, 1.9] s | same lines |
| Buzzard spread at exposure 0 → 1 (rad per axis) | 0.065 → 0.018 | 0.052 → 0.016 | 0.042 → 0.014 | same lines |
| Attack tokens: normal / crowd | 2 / 3 | 3 / 4 | 4 / 5 | `src/config/enemies.js:246`, `:251`, `:256` |
| Minimum gap between two token grants | 1.25 s | 0.85 s | 0.6 s | same lines |
| Exposure gain per second in sight | 0.10 | 0.14 | 0.18 | same lines |
| Time in sight to full accuracy (derived: 1 / gain) | 10.0 s | 7.14 s | 5.56 s | `src/enemies/logic.js:97` |

Often assumed to vary but constant: the Goon telegraph (0.5 s), the Goon burst gap (0.11 s), the Buzzard volley (3
bolts, 0.12 s apart), bolt speed (70 m/s), reaction times, sight range, every rush timing, pool sizes.

How many enemies exist is the game flow's business (`src/config/flow.js:101`), listed here for context only:

| | Hustler | Boss | Kingpin | Source |
|---|---|---|---|---|
| Starting patrol, Buzzard + Goon, unaware | 1 + 3 | 2 + 4 | 2 + 5 | `src/config/flow.js:104`, `:116`, `:128` |
| Waves after reel 1 / 2 / 3, Buzzard + Goon, arrive alerted | 2+3 / 2+4 / 3+5 | 2+5 / 3+6 / 4+7 | 3+6 / 4+7 / 5+8 | `src/config/flow.js:105`, `:117`, `:129` |
| Alive cap (both types together) | 9 | 11 | 13 | `src/config/flow.js:110`, `:122`, `:134` |

Hold the Block multiplies through `enemies.setScale({hp, damage, cooldown})` (`src/enemies.js:627`,
`src/config/flow.js:153`): wave n gives hp × min(2.5, 1 + 0.07 (n − 1)), damage × min(2, 1 + 0.05 (n − 1)),
cooldown × max(0.6, 1 − 0.03 (n − 1)). `hp` applies to units spawned from then on (`src/enemies.js:300`); `damage`
applies at once to SMG rounds (`src/enemies/goon.js:624`), the pipe (`src/enemies/goon.js:894`) and bolts
(`src/enemies/buzzard.js:633`); `cooldown` applies to the cooldown drawn after each burst
(`src/enemies/goon.js:862`, `src/enemies/buzzard.js:673`). Not scaled: the Buzzard's crash burst, the first cooldown,
telegraphs, the rush cooldown.

### 2.3 Shared AI constants (perception, alerting, pacing)

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `sightRange` | 45 m | Largest distance from the sensor to the player's eye (3D) | `src/config/enemies.js:201` |
| `fov` | 200° total (100° either side), horizontal only | Cone centred on the facing; ignored once engaged and inside `closeRange` | `src/config/enemies.js:202` |
| `closeRange` | 3.5 m | Inside this the cone is ignored | `src/config/enemies.js:203` |
| `senseEvery` | [0.11, 0.19] s | Interval between sight checks, redrawn at every check; the first check comes U(0, 0.19) s after spawn | `src/config/enemies.js:204`, `src/enemies.js:228`, `src/enemies.js:305` |
| `reaction` | Goon 0.55 s, Buzzard 0.40 s | Accumulated sight needed to engage from patrol | `src/config/enemies.js:118`, `src/config/enemies.js:30` |
| `investigateReaction` | × 0.45 (Goon 0.2475 s, Buzzard 0.18 s) | The same once investigating or searching | `src/config/enemies.js:205` |
| `seenDecay` | 0.6 | Out of view, the accumulator loses 0.6 × the tick length per tick | `src/config/enemies.js:206` |
| `loseSightAfter` | 4 s | Engaged without sight this long: go searching | `src/config/enemies.js:207` |
| `searchTime` | [8, 11] s | How long a search lasts | `src/config/enemies.js:208` |
| `noiseTime` | [9, 13] s | How long a noise or a rally keeps a unit investigating | `src/config/enemies.js:209` |
| `provokedTime` | 10 s | The same after being hit | `src/config/enemies.js:210` |
| `spawnAlertTime` | Goon 10 s, Buzzard 8 s | How long a reinforcement hunts before giving up | `src/config/enemies.js:119`, `src/config/enemies.js:31` |
| `rallyOnSight` | 18 m | Allies this close to a unit that engages come to look | `src/config/enemies.js:211` |
| `rallyOnHit` | 20 m | Allies this close to a unit that was hit come to look | `src/config/enemies.js:212` |
| `exposureUp` | 0.10 / 0.14 / 0.18 per s | Accuracy ramp while in sight (2.2) | `src/config/enemies.js:215` |
| `exposureDown` | 0.45 per s | Accuracy lost out of sight: full to zero in 2.2 s | `src/config/enemies.js:216` |
| `tokens`, `tokensCrowd` | 2 / 3, 3 / 4, 4 / 5 | Simultaneous ranged attackers (2.2) | `src/config/enemies.js:219` |
| `crowdAbove` | 5 | More than this many alive unlocks the crowd limit | `src/config/enemies.js:221` |
| `tokenGap` | 1.25 / 0.85 / 0.6 s | Minimum time between two grants | `src/config/enemies.js:222` |
| `tokenFairness` | `refusedWithin` 0.5 s, `gapFactor` 2.2 | Types alternate when both want to fire (3.6) | `src/config/enemies.js:223` |
| `hear.gunfire` | 45 m | Alert radius of a player shot | `src/config/enemies.js:227`, `src/enemies.js:488` |
| `gunfireEvery` | 0.3 s | Player gunfire alerts at most this often | `src/config/enemies.js:234`, `src/enemies.js:486` |
| `hear.explosion` | 30 m | Alert radius of any blast | `src/config/enemies.js:228`, `src/enemies.js:491` |
| `hear.explosive` | 60 m | Alert radius of a propane tank or welding rack going up | `src/config/enemies.js:229`, `src/enemies.js:494`, `src/explosives.js:28` |
| `alertDefaultRadius` | 40 m | Radius of `alert()` / `hear()` when none is given | `src/config/enemies.js:233` |
| Reinforcement arrival | 60 m around the player | The flow re-alerts at each arrival | `src/config/flow.js:82`, `src/game.js:508` |
| Pursuit re-alert | 90 m around the player, every 4 s | After the last reel | `src/config/flow.js:93`, `src/game.js:642` |
| Holdout re-alert | 90 m around the player, every 5 s | Once a wave is all out | `src/config/flow.js:147`, `src/game.js:720` |
| `pathsPerFrame`, `picksPerFrame` | 2, 1 | Nav queries and fire-position choices per frame over all Goons | `src/config/enemies.js:237` |

### 2.4 Goon constants

Body and hit volumes:

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `radius`, `height` | 0.3 m, 1.8 m | Movement capsule (also `enemy.radius`, `enemy.height`) | `src/config/enemies.js:108`, `src/enemies/goon.js:384` |
| `eyeHeight` | 1.6 m above the feet, on the body axis | Where he sees from; does not drop when he kneels | `src/config/enemies.js:113`, `src/enemies/goon.js:1060` |
| `gunHeight` | 1.46 m above the feet, on the body axis | Where his rounds start (not the drawn muzzle) | `src/config/enemies.js:114`, `src/enemies/goon.js:602` |
| Head hit sphere | radius 0.155 m, centred 0.12 m above the neck joint of the animated head | The weak point; follows the pose | `src/config/enemies.js:111`, `src/enemies/goon-model.js:60`, `src/enemies/goon-anim.js:634`, `src/enemies.js:373` |
| Body hit capsule | radius 0.27 m; from 0.62 m under the hip joint (never lower than 0.27 m) to 0.13 m under the neck joint | Follows the pose | `src/config/enemies.js:112`, `src/enemies/goon-anim.js:640`, `src/enemies.js:385` |
| Head damage multiplier | × 2.2, player guns only | Melee and blasts always count as body | `src/config/weapons.js:173`, `src/combat.js:192` |

Where those volumes sit in each stance **(measured** with `poseGoon`, heights above the feet):

| Stance | Head sphere centre | Body capsule, low end → high end | Muzzle |
|---|---|---|---|
| Standing, gun at low ready | 1.61 m | 0.33 m → 1.36 m | 0.89 m |
| Standing, aiming | 1.57 m | 0.29 m → 1.32 m | 1.37 m, 0.73 m ahead, 0.13 m to his right |
| Kneeling behind cover | 1.12 m | 0.27 m → 0.88 m | 0.47 m |
| Walking (patrol, 1.5 m/s) | 1.55 to 1.60 m | 0.32 m → 1.34 m | 0.85 m |
| Stalking (2 m/s, gun up) | 1.45 to 1.50 m | 0.27 m → 1.24 m | 1.21 m |
| Running (4.5 to 5.4 m/s) | 1.48 to 1.54 m, 0.16 m ahead of the feet | 0.27 m → 1.24 to 1.29 m | 1.20 to 1.25 m |

Movement on the nav grid:

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `runSpeed` | 4.5 / 5.0 / 5.4 m/s | To a fire position; to a distant last known position | `src/config/enemies.js:122` |
| `stalkSpeed` | 2.0 m/s | The last 8 m of an investigation, gun up | `src/config/enemies.js:123` |
| `patrolSpeed` | 1.5 m/s | Wandering | `src/config/enemies.js:124` |
| `accel`, `decel` | 7 m/s², 9.8 m/s² | Linear change of speed | `src/config/enemies.js:125` |
| `turnRate` | 2.5 rad/s | Standing: turning to face a target | `src/config/enemies.js:127` |
| `pathTurnRate` | 5 rad/s | Walking: steering along a path | `src/config/enemies.js:128` |
| `aimRate` | 4.5 rad/s | How fast the gun's aim yaw follows the bearing | `src/config/enemies.js:129` |
| `turnInPlace` | 1.1 rad | Heading error above this: stop and turn | `src/config/enemies.js:133` |
| `replan` | [0.6, 0.75] s | Period of the "is the next waypoint still straight ahead" check | `src/config/enemies.js:130` |
| `waypointReach`, `goalReach` | 0.55 m, 0.45 m | A waypoint counts as passed, the goal as reached | `src/config/enemies.js:131` |
| `separation.goon` | 1.7 m, push up to 2.2 m/s | Kept apart from other living Goons | `src/config/enemies.js:134`, `src/enemies/goon.js:39` |
| `separation.player` | 1.25 m, push up to 3 m/s | Kept off the player (not during the dash) | `src/config/enemies.js:134`, `src/enemies/goon.js:40` |
| `stuckTime` | 0.5 s | Trying to move and getting nowhere this long: new plan | `src/config/enemies.js:136` |
| Gravity, step-up | 20 m/s², 0.42 m | When he walks off a kerb; ledges he walks up | `src/enemies/goon.js:36`, `src/physics.js:21` |
| `patrol` | radius 7 m, wait [1.5, 4.5] s | Wander radius around home; pause at each point | `src/config/enemies.js:137` |
| Footstep range | 45 m | `enemy:step` is only emitted this close to the player | `src/enemies/goon.js:38` |

Investigating and searching (`src/config/enemies.js:142`):

| Constant | Value | Meaning |
|---|---|---|
| `stalkWithin` | 8 m | Inside this distance of the spot he slows to `stalkSpeed`, gun up, half crouched |
| `stopWithin` | 2.2 m | He stops this short of the spot and sweeps |
| `sweep` | ± 0.9 rad at 1.3 rad/s phase rate (period 4.8 s) | The gun sweeps left and right of the way he came in |
| `elevated` | 1.2 m | A spot this far above his feet is "up on something" (the scaffold deck, the mezzanine office) |
| `restand` | 1.5 m | The elevated spot moved this far (sum of the three axis differences): choose a new stand-off point |
| `restandAfter` | 2.5 s | A stand-off point that turned out blind: choose again after this much sweeping |
| `standFallback` | 4.5 m | With no stand-off point yet, stop this far short |

Fire positions:

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `rangeMin`, `rangeMax` | 8 m, 18 m | The band around the player he fights from (horizontal distance) | `src/config/enemies.js:145` |
| `repick.playerMoved` | 7 m | The player moved this far from where he was at the last choice: choose again | `src/config/enemies.js:147` |
| `repick.randomPoints` | 7 | Random candidates in the band | `src/config/enemies.js:147` |
| `repick.arcPoints`, `arc`, `arcRange` | 5, ± 1.3 rad, [9, 17] m | Candidates on his own side of the player | `src/config/enemies.js:147` |
| `repick.minMove` | 3 m | A relocation goes at least this far | `src/config/enemies.js:147` |
| `positionCost.travel` | 0.9 per metre | Distance from where he stands | `src/config/enemies.js:149` |
| `positionCost.authored` / `random` / `arc` | −2 / 0 / +1 | Bias by kind of candidate | `src/config/enemies.js:150` |
| `positionCost.jitter` | 3 × U(0, 1) | Noise | `src/config/enemies.js:153` |
| `positionCost.sameBearing` | up to +14 | Within 30° of another engaged Goon's bearing from the player | `src/config/enemies.js:154`, `src/enemies/logic.js:108` |
| `positionCost.crowded` | +16 | Within 3 m of another Goon's position or destination | `src/config/enemies.js:155`, `src/enemies/logic.js:109` |
| `positionCost.noSight` | +22 | No shot from there | `src/config/enemies.js:156` |
| `positionCost.cover` | −4 | An authored cover point that still sees the player | `src/config/enemies.js:157` |
| `cover.crouchBetweenBursts` | true | He kneels at such a point while the gun cools | `src/config/enemies.js:159` |
| `cover.maxStep` | 1 m | Cover points more than this above or below him are ignored | `src/config/enemies.js:159` |
| `move.aimEarlyAfter`, `aimEarlyRange`, `aimEarlyChance` | 1.4 s, [7, 20] m, 0.7 per second | On the way, with sight, he may stop and shoot from where he is | `src/config/enemies.js:160` |
| `move.giveUp` | 7 s | Still not there: shoot from here | `src/config/enemies.js:160` |
| `hold.tooClose`, `tooCloseTime` | 5 m, 0.8 s | The player this close this long: relocate | `src/config/enemies.js:161` |
| `hold.noSightTime` | 1.1 s | No sight from the position this long: relocate | `src/config/enemies.js:161` |
| `hold.maxWait` | 3 s | Ready but no token (or not lined up) this long: relocate | `src/config/enemies.js:161` |
| `hold.aimTolerance` | 0.14 rad | The gun must be this close to the bearing before a burst | `src/config/enemies.js:161` |
| `burstsBeforeMove.one` | 0.6 | Chance to relocate after one burst, otherwise after two | `src/config/enemies.js:162` |
| Candidate cap | 96 | Per choice | `src/enemies/goon.js:37` |

The SMG burst:

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `shotDamage`, `burst`, `cooldown` | see 2.2 | | `src/config/enemies.js:165` |
| `burstGap` | 0.11 s (545 rounds per minute) | Between rounds of a burst | `src/config/enemies.js:167` |
| `telegraph` | 0.5 s | Warning before every burst | `src/config/enemies.js:168` |
| `firstCooldown` | [0.6, 1.6] s | Drawn at spawn; counts down in every mode | `src/config/enemies.js:170`, `src/enemies/goon.js:217` |
| `shotRange` | 200 m | Hitscan range | `src/config/enemies.js:171` |
| `aimHeight` | 1.0 m above the player's feet (0.8 m when he crouches) | The point aimed at | `src/config/enemies.js:172`, `src/enemies/goon.js:603` |
| `spreadPerSpeed` | 0.3 | Spread × (1 + player speed × this) | `src/config/enemies.js:175` |
| `overCover` | `below` 0.25 m, `spreadY` 0.3 | Shooting up at a player whose chest is hidden (3.7.6) | `src/config/enemies.js:117` |
| Player target | upright cylinder, radius 0.38 m, 1.8 m tall (1.15 m crouched) | What an enemy round has to hit | `src/combat.js:21` |
| Tracer | colour `#ff3a22`, from the drawn muzzle to the hit point | | `src/config/look.js:121`, `src/enemies/goon.js:628` |
| Muzzle light | colour `#ff7a3c`, intensity 14, range 7 m, 0.05 s, every other round | Pooled point light | `src/enemies/goon.js:630`, `src/enemies.js:106` |
| Round against an explosive | 9 damage, whatever the round's own damage | | `src/config/weapons.js:198`, `src/combat.js:216` |

The rush (`src/config/enemies.js:180`):

| Constant | Value | Meaning |
|---|---|---|
| `rushDamage` | 15 / 22 / 30 | One blow, damage kind `melee` |
| `rush.range` | 3 m | Starts inside this horizontal distance |
| `rush.windup` | 0.28 s | He stops, draws the pipe, turns on the player |
| `rush.speed`, `rush.time` | 9.5 m/s for at most 0.36 s (3.42 m) | The dash |
| `rush.reach` | 1.35 m | The blow lands inside this distance during the dash |
| `rush.recovery` | 0.55 s | Standing still afterwards |
| `rush.cooldown` | 3.5 s | Before the next rush |
| Height tolerance | 1.4 m to start, 1.3 m to land | `src/enemies/goon.js:753`, `src/enemies/goon.js:890` |

Death and body (`src/config/enemies.js:192`): `collapse` 0.9 s, `bodyFade` 3.2 s, `bodyStay` 45 s, `staggerMax` 1.6.

### 2.5 Buzzard constants

Body: hit volume one ellipsoid of revolution, horizontal `radius` 0.5 m, `halfHeight` 0.22 m, no weak point
(`src/config/enemies.js:28`, `src/enemies.js:362`). `enemy.radius` 0.5, `enemy.height` 0.44. It sees from its eye lens
(`src/enemies/buzzard.js:828`).

Flight:

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `maxSpeed` | 8 m/s | Speed cap while engaged | `src/config/enemies.js:34` |
| `investigateSpeed`, `patrolSpeed` | 5.5 m/s, 3 m/s | Speed caps of the other modes | `src/config/enemies.js:35` |
| `accel` | 11 m/s² | Cap on the steering acceleration | `src/config/enemies.js:37` |
| `yawRate` | 3.2 rad/s | Turning the nose | `src/config/enemies.js:38` |
| `pull.horizontal` | [2.2, 2.4] | Acceleration = 2.2 × offset − 2.4 × velocity (per s², per s) | `src/config/enemies.js:39` |
| `pull.vertical` | [5, 3.6] | The same, vertical | `src/config/enemies.js:39` |
| `minHeight` | 2.2 m | Lowest wanted height above the ground under it; also the clearance over an obstacle it climbs | `src/config/enemies.js:40` |
| `floorClearance` | 1.1 m | Hard floor above the ground under it | `src/config/enemies.js:41` |
| `ceilingClearance` | 1.3 m | Kept under a ceiling it has felt | `src/config/enemies.js:42` |
| `feelers` | forward 2.2 m + 0.5 s × speed, down 2.4 m, up 4 m, bounce −0.25 | One probe ray per frame, in rotation | `src/config/enemies.js:43` |
| `patrol` | radius [4, 9] m, 0.28 rad/s | Circle around home | `src/config/enemies.js:44` |
| `investigate` | radius 4.5 m, 0.5 rad/s, at most 5.5 m up | Circle over the last known position | `src/config/enemies.js:45` |
| `maxAltitude`, `overshoot` | 15 m, 0.5 m | Ceiling of the block; hard clamp at 15.5 m | `src/config/enemies.js:46` |
| `climbLook` | 6 m | Length of the leg ahead checked for things to climb over | `src/config/enemies.js:48` |
| `boundsMargin` | 1.2 m | Kept this far inside the play bounds | `src/config/enemies.js:49` |
| `deck` | under 1.5, over 3.6, thickness 1, margin 1.5, hold 2.5, slide 5 (m) | Flight plan around the El's track deck (3.8.3) | `src/config/enemies.js:54` |
| `detour` | far 2.5 m, moved 0.5 m, after 2.5 s, distance 4 m, up 1.5 m, time 1.5 s | Last resort when wedged | `src/config/enemies.js:57` |
| Bank | 0.034 rad per m/s², at most 0.5 rad | Tilt into the acceleration | `src/enemies/buzzard.js:55` |
| Pole rule | narrower than 1 m both ways; step off at 2 m/s | Lamp posts and columns are gone around, never over | `src/enemies/logic.js:434`, `src/enemies/buzzard.js:60` |
| Doorways | at least 2 m wide, clear at 2.4 m and 3.2 m | How it finds its way into the shop | `src/enemies/buzzard.js:193` |

Orbit while engaged (`src/config/enemies.js:58`):

| Constant | Value | Meaning |
|---|---|---|
| `orbit.radius` | [14, 22] m | Personal orbit radius, drawn at spawn |
| `orbit.radiusClamp`, `radiusDrift` | [13, 23] m, ± 3 m | It drifts inside this band at every rethink |
| `orbit.altitude` | [4.8, 7.2] m above the player's feet | Personal height, drawn at spawn |
| `orbit.speed`, `speedFiring` | 3.6 m/s, 0.9 m/s | Tangential speed; while telegraphing or firing |
| `orbit.rethink` | [3, 8] s | Between changes of direction and radius |
| `orbit.reverseChance` | 0.6 | Chance to reverse at a rethink |
| `orbit.lostAfter` | 1.5 s | Without sight this long it flies to the last known position instead |

Attack:

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `boltDamage`, `telegraph`, `cooldown` | see 2.2 | | `src/config/enemies.js:71` |
| `boltSpeed`, `boltLife` | 70 m/s, 1.3 s (91 m) | A bolt flies straight, no gravity | `src/config/enemies.js:72` |
| `burst`, `burstGap` | 3 bolts, 0.12 s apart (0.24 s first to last) | One volley | `src/config/enemies.js:74` |
| `firstCooldown` | [1, 2.5] s | Drawn at spawn; counts down in every mode | `src/config/enemies.js:78` |
| `fireRange` | 42 m | Distance (3D) inside which it may start a volley | `src/config/enemies.js:79` |
| `aimTolerance` | 0.35 rad | The nose must be this close to the bearing | `src/config/enemies.js:80` |
| `lead` | [0.2, 0.85] of perfect lead | Rolled once per volley | `src/config/enemies.js:81` |
| `aimHeight` | 1.05 m above the player's feet (0.75 m when he crouches) | The point aimed at | `src/config/enemies.js:82`, `src/enemies/buzzard.js:622` |
| `recoilPush` | 0.35 m/s per bolt, against the shot | | `src/config/enemies.js:83` |
| `spreadPerSpeed` | 0.45 | Spread × (1 + player speed × this) | `src/config/enemies.js:86` |
| `boltTarget` | upright capsule, radius 0.36 m, from 0.35 m to 1.5 m above the feet (to 1.0 m crouched) | What a bolt has to touch | `src/config/enemies.js:88`, `src/enemies/bolts.js:99` |
| Bolt against an explosive | 9 damage | | `src/enemies/bolts.js:116` |
| Bolt look | streak 2.4 m long, 0.11 m wide; head flare 0.34 m; colour `#ff3a22` × 9 (HDR), streak at 0.6 of that | | `src/enemies/bolts.js:8` |
| Muzzle light | colour `#ff3a22`, intensity 10, range 6 m, 0.05 s, every bolt | | `src/enemies/buzzard.js:638` |
| Bolt pool | 32; when full the oldest bolt is replaced | | `src/config/enemies.js:12`, `src/enemies/bolts.js:50` |

Damage and death:

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `damagedBelow` | 0.5 of max HP | Below this: wobble, smoke, sparks, worse aim | `src/config/enemies.js:91` |
| `damagedSpread` | × 1.5 | Spread multiplier when damaged | `src/config/enemies.js:92` |
| `damagedJitter` | 1.6 m/s² | Sinusoidal steering noise when damaged | `src/config/enemies.js:93` |
| `smokeEvery` | [0.1, 0.22] s | Between smoke puffs when damaged | `src/config/enemies.js:94` |
| `hitKick` | ± 0.5 rad | Random pitch and roll offset per hit, decaying at rate 5 | `src/config/enemies.js:95`, `src/enemies/buzzard.js:752` |
| `knockback` | 0.09 m/s per point of damage, at most 3 m/s | Along the shot | `src/config/enemies.js:96` |
| `deathKick` | up 1.5 m/s, along the shot 2.5 m/s | Impulse when killed | `src/config/enemies.js:97` |
| `fallGravity` | 9.5 m/s² | The fall | `src/config/enemies.js:98` |
| `fallMaxTime` | 5 s | It bursts in the air if it has not landed by then | `src/config/enemies.js:99` |
| `burstRadius`, `burstDamage`, `burstPlayerScale` | 3 m, 30, 0.5 (15 at most to the player) | The crash; linear falloff, needs line of sight | `src/config/enemies.js:100` |

### 2.6 Pools, caps and budgets

| What | Value | Rule | Source |
|---|---|---|---|
| Goons | 12 slots | Living, dying and bodies share them | `src/config/enemies.js:12`, `src/enemies/goon.js:179` |
| Buzzards | 8 slots | Living and falling | `src/config/enemies.js:12`, `src/enemies/buzzard.js:177` |
| Bodies | 6 kept | A seventh makes the oldest dissolve | `src/config/enemies.js:12`, `src/enemies.js:579` |
| Bolts | 32 | Oldest replaced when full | `src/config/enemies.js:12` |
| Glow sprites, rotor discs | 160, 32 | Draw budget of the web version, not a rule | `src/enemies.js:121` |
| Alive cap | 9 / 11 / 13 (+ up to 5 in Hold the Block) | Enforced by the game flow, not by the pools | `src/config/flow.js:110`, `src/config/flow.js:156`, `src/game.js:497` |

### 2.7 Public interface

`G.enemies` (`src/enemies.js:601`, `docs/CONTRACT.md:460`): `list` (living and dying units), `aliveCount()`,
`countByType(type)`, `spawn(type, pos, {alerted, target, yaw, variant, passive, show})` → enemy or null when no slot
is free, `clear()`, `raycast(origin, dir, maxDist = 500)` → `{enemy, dist, point, normal, part: 'head' | 'body'}`,
`damage(enemy, amount, {point, dir, part, from, weapon})` → `{killed}`, `alert(pos, radius = 40)`,
`hear(pos, radius = 40)`, `setDifficulty(table)`, `setScale({hp, damage, cooldown})`, `nearestDistance()`,
`aimTarget(origin, dir, maxDist = 60)` → is an unoccluded enemy under the ray (gamepad aim slow-down), `update(dt)`.

An enemy object exposes `id`, `type`, `pos`, `alive`, `hp`, `maxHp`, `radius`, `height`, `state` and, beyond the
contract, `mode`, `sub` (Goon), `yaw`, `vel`, `sees`, `exposure`, `variant` (Goon outfit 0 to 2).
`state` is one of `patrol`, `investigate`, `search`, `engage`, `dying`, `dead` (a Goon body), `idle` (a free slot).
`passive: true` makes a unit that never senses or acts and `show` poses such a Goon; both exist for showcase and
screenshot scenes only and need no port.

What reaches the player, as damage kinds of `player.damage(amount, from, kind)`: SMG rounds `bullet` (through
`combat.hitscan`), bolts `bolt`, the pipe `melee`, a Buzzard's crash `blast` (`docs/CONTRACT.md:487`).

Events emitted (payloads in `docs/CONTRACT.md:146`):

| Event | When | Source |
|---|---|---|
| `enemy:spawn {enemy}` | A unit is placed | `src/enemies.js:321` |
| `enemy:alert {enemy, pos}` | A unit starts engaging; or an unaware unit is sent to look by a noise or a hit | `src/enemies.js:196`, `src/enemies.js:212` |
| `enemy:telegraph {enemy, type, duration, pos}` | Once before every burst or volley | `src/enemies/goon.js:816`, `src/enemies/buzzard.js:687` |
| `enemy:fire {enemy, type, pos, dir}` | Once per round or bolt; `pos` is the drawn muzzle | `src/enemies/goon.js:631`, `src/enemies/buzzard.js:639` |
| `enemy:melee {enemy, phase, pos}` | `windup` when the rush starts, `strike` when the pipe swings | `src/enemies/goon.js:642`, `src/enemies/goon.js:649` |
| `enemy:hit {enemy, part, damage, point}` | Every damaging hit | `src/enemies.js:429` |
| `enemy:killed {enemy, type, pos, part, byPlayer, weapon}` | `byPlayer` is true for player shots and for every blast | `src/enemies.js:451` |
| `enemy:step {enemy, pos, surface}` | Every Goon footfall within 45 m of the player | `src/enemies/goon.js:994` |

Consumers: audio (every event, 5.7), the HUD kill feed ("Goon down", "Buzzard down", tag "Headshot":
`src/hud.js:315`), the minimap (a red pip for every unit in `engage` or that fired in the last 2 s:
`src/ui/logic.js:291`, `src/ui/minimap.js:14`), the flow (first `enemy:alert` triggers the "They made you" radio line
and every one holds the music at alert intensity for 10 s: `src/game.js:899`, `src/config/flow.js:212`; holdout score
per kill: `src/game.js:906`).

### 2.8 Config values that are defined but never read

These exist in `src/config/enemies.js` and no code uses them. Do not port them as rules.

| Value | Line | What actually happens instead |
|---|---|---|
| `goon.crouchHeight: 1.25` | 110 | Nothing changes size when he kneels; only the posed hit volumes drop (2.4) |
| `goon.head.height: 1.62` | 111 | The head sphere follows the animated head (1.61 m standing, 1.12 m kneeling) |
| `goon.blockedRay` | 135 | There is no forward ray; stuck detection (3.7.4) does that job |
| `goon.cover.snap: 1.6` | 159 | Cover points are candidates themselves; nothing snaps to them |
| `goon.shotTarget` | 177 | Rounds go through `combat.hitscan` against the player cylinder (`src/combat.js:21`) |
| `goon.score: 150`, `buzzard.score: 100` | 196, 103 | The flow uses its own copy with the same numbers (`src/config/flow.js:157`) |
| `ai.hear.reinforcement: 60`, `ai.hear.escape: 90` | 230, 231 | The flow uses its own copy with the same numbers (`src/config/flow.js:82`, `:94`) |

`enemies.hear()` exists and works but nothing calls it. Audio reads `enemy.voice` for the pitch of a Goon's grunts
(`src/audio/react.js:214`) but no code sets it, so every Goon has the same voice.

### 2.9 Where docs/DESIGN.md and the code differ (the code wins)

| DESIGN.md | Code |
|---|---|
| "hoodie or puffer jacket" (`docs/DESIGN.md:24`) | Three outfits: hoodie, puffer, tracksuit, chosen at random per spawn (`src/enemies/goon-model.js:109`, `src/enemies/goon.js:218`) |
| Goons "prefer fire positions next to a `level.coverPoints` entry" (`docs/DESIGN.md:140`) | The cover points are the candidates; he stands on the point itself (`src/enemies/goon.js:459`) |
| Bodies: "max 6 kept, oldest fades" (`docs/DESIGN.md:142`) | Also: a body dissolves by itself after 45 s, and a new Goon may take the oldest body's slot at once when all 12 slots are in use (`src/config/enemies.js:194`, `src/enemies.js:291`) |
| The difficulty table in 3.1 | Matches the code exactly |
| Night is the look of sections 1 and 5; day is the default per section 8 | The enemy materials follow the time of day: self-lit trim and rim light at 0.12 by day, 1.0 and 0.8 by night; flares 1.35 × larger by day and covering 60 % of what is behind them (`src/config/enemies.js:21`) |

---------------------------------------------------------------------------------------------------

## 3. Behaviour

### 3.1 Order within a frame

The main loop runs `input → game → player → weapon → enemies → explosives → fx …` with one clamped time step,
dt ≤ 0.05 s (`docs/CONTRACT.md:81`). Inside `enemies.update(dt)` (`src/enemies.js:548`):

1. Follow the time of day (materials only). Advance the module clock.
2. Read the player: feet, eye, alive, crouching, velocity. `player.speed` = horizontal speed smoothed with
   `damp(rate 6)`; 0 when dead (`src/enemies.js:500`).
3. Reset the per-frame budgets (2 path queries, 1 position choice). Count the living: that number sets the token limit.
4. For every unit, newest first: a living, non-passive unit **thinks** (sight check if one is due, exposure step, mode
   timers: 3.2 to 3.5) and then runs its own update (movement, attack, pose). A dying unit advances its collapse or
   fall. A Goon that has come to rest leaves the list and becomes a body. A Buzzard that has landed is retired first
   and bursts second, so its own burst cannot touch it (`src/enemies.js:570`).
5. Spend the budgets round robin over the Goon slots: fire-position choices, then stand-off choices (same budget), then
   path queries (`src/enemies.js:520`).
6. Bodies: dissolve the ones that are fading, free the ones that are gone.
7. Bolts: move and test every bolt in flight.
8. Refill the glow batch (flares, strobes, streaks, rotor discs).

So: an SMG round is resolved in the frame it is fired (hitscan); a bolt makes its first step in the frame it is fired;
the player has already moved when enemy damage lands; the enemies see the weapon's shot of the same frame.

### 3.2 The mode machine (both types)

One machine for Goons and Buzzards (`src/enemies.js:171` to `src/enemies.js:268`). `enemy.state` equals the mode while
alive. Timers per unit: `seen` (accumulated sight), `sinceSeen` (time since the last sight check that saw the player),
`modeTime` (time left in investigate or search).

| From | When | To | What else happens |
|---|---|---|---|
| (spawn) | `alerted: false` | `patrol` | Home = spawn point |
| (spawn) | `alerted: true` | `investigate` | Last known = the given target, else the player; `modeTime` = 10 s (Goon) / 8 s (Buzzard); no `enemy:alert` |
| `patrol` | `seen` ≥ reaction (0.55 s Goon, 0.40 s Buzzard) | `engage` | `enemy:alert`; allies within 18 m come to look (3.4) |
| `patrol` | A noise in range, a rally, or a hit that did not kill | `investigate` | Last known = ground under the noise, or the player's feet for a rally or a hit; `modeTime` = [9, 13] s (noise, rally) or 10 s (hit); `enemy:alert` for a noise or a hit |
| `investigate`, `search` | `seen` ≥ 0.45 × reaction | `engage` | As above |
| `investigate`, `search` | Another noise, rally or hit | stays (`search` stays `search`) | New last known position, timer restarted |
| `investigate`, `search` | `modeTime` runs out | `patrol` | Home = where it gave up (it does not go back); `seen` = 0 |
| `engage` | `sinceSeen` ≥ 4 s, or the player is dead | `search` | `modeTime` = [8, 11] s; telegraph or burst dropped, token returned; last known = where the player was last seen (his current position if he just died) |
| any living | Hit points reach 0 | `dying` | Token returned; `enemy:killed`; no more sight, no more hits taken |
| `dying` (Goon) | The collapse has run 0.9 s | `dead` | Leaves `enemies.list`; a body (3.7.10) |
| `dying` (Buzzard) | It touches anything, or after 5 s | `idle` | Retired, then the crash burst (3.8.9) |
| `dead` | The dissolve has finished | `idle` | Slot free |

Only sight leads into `engage`. Noise, rallies and hits only send a unit to look, with a shorter reaction time once it
is looking. Engaged units ignore alerts and rallies altogether.

### 3.3 Sight

Every unit checks sight on its own clock (`src/enemies.js:224`, `src/enemies/logic.js:74` to `:94`):

```
every tick (tick = a new draw from [0.11, 0.19] s):
  sensor  = Goon: feet + 1.6 m on the body axis          Buzzard: its eye lens
  facing  = Goon: body yaw + animated head yaw            Buzzard: body yaw
  d       = distance(sensor, player eye)                   // 3D
  visible = player alive
            and d < 45
            and (mode == engage or d <= 3.5 or the horizontal bearing to the player is within 100° of facing)
            and lineOfSight(sensor, player eye)             // bullet-solid boxes block; glass and chain-link do not
  sees    = visible
  seen    = visible ? seen + tick : max(0, seen − 0.6 · tick)
  if visible:
      lastKnown = player feet ; sinceSeen = 0
      if mode != engage and seen >= (mode == patrol ? reaction : 0.45 · reaction): engage
```

- The player is seen exactly when his **eye point** is visible: 1.68 m above his feet standing, 1.05 m crouched
  (`src/config/player.js:9`). Crouching behind anything taller than that hides him.
- Short peeks add up, because `seen` drains slower (0.6 per second) than it fills (1 per second).
- With ticks of 0.11 to 0.19 s, a patrolling Goon engages about 0.4 to 0.7 s after the player first comes into
  view, a patrolling Buzzard 0.2 to 0.6 s; a unit that is already looking needs one to three checks (under 0.45 s).
- A patrolling Goon turns his head ± 0.9 rad on a sine with an 11.4 s period (`src/enemies/goon.js:656`), and the cone
  follows the head, so the 160° blind wedge behind him swings from side to side.
- A unit that was just hit has `seen` raised to at least 1 and checks sight at its very next update
  (`src/enemies.js:436`): if it can see the player it engages at once.
- While engaged the cone no longer matters: only range and line of sight.

### 3.4 Hearing and alert propagation

`alert(pos, radius)`: every living, non-engaged unit within `radius` of `pos` (straight 3D distance from the unit's
position, no walls considered) goes to investigate. Its last known position becomes the **ground under** `pos` (the
highest walkable top below `pos.y + 0.3`), the timer is [9, 13] s, and a unit that was unaware emits `enemy:alert`
(`src/enemies.js:465`, `src/enemies.js:204`). `hear()` is the same for unaware units only.

| Cause | Centre | Radius | Source |
|---|---|---|---|
| A player shot (at most one alert per 0.3 s) | The muzzle | 45 m | `src/enemies.js:485` |
| Any explosion, a Buzzard's crash included | The blast | 30 m | `src/enemies.js:490` |
| A propane tank or welding rack going up | The prop | 60 m | `src/enemies.js:493`, `src/explosives.js:424` |
| Each reinforcement arriving | The player | 60 m | `src/game.js:508` |
| Pursuit after the last reel, every 4 s | The player | 90 m | `src/game.js:642` |
| Hold the Block, every 5 s once the wave is all out | The player | 90 m | `src/game.js:720` |

Rallies (`src/enemies.js:183`), measured from the unit, not from the player:

- When a unit **engages**, every non-engaged ally within 18 m of it goes to investigate the player's position
  ([9, 13] s, silently).
- When a non-engaged unit is **hit and survives**, it investigates the player's position for 10 s (with
  `enemy:alert`) and every non-engaged ally within 20 m of it does the same for [9, 13] s (`src/enemies.js:434`).

### 3.5 Exposure and accuracy

Each unit carries `exposure` 0…1, stepped every frame from the result of its last sight check, in every mode
(`src/enemies.js:255`, `src/enemies/logic.js:97` to `:104`):

```
exposure = clamp01(exposure + (sees ? exposureUp : −0.45) · dt)
spread   = (spreadFar + (spreadNear − spreadFar) · exposure) · (1 + playerSpeed · spreadPerSpeed) · extra
dir      = normalize(aimPoint − origin)
dir.x   += U(−1, 1) · spread
dir.y   += U(−1, 1) · spread · spreadY          // spreadY = 1, or 0.3 for a Goon shooting up over cover
dir.z   += U(−1, 1) · spread
dir      = normalize(dir)
```

- `spread` is therefore the half-width, in radians for small angles, of a **uniform box** around the aim direction, not
  the half-angle of a cone: each world axis gets its own independent offset.
- `extra` is 1.5 for a Buzzard under half its hit points, otherwise 1.
- `playerSpeed` is the smoothed horizontal speed. With the player's speeds (`src/config/player.js:21`) the
  multiplier is:

| Player | Speed | Goon spread × | Buzzard spread × |
|---|---|---|---|
| Standing | 0 | 1.00 | 1.00 |
| Crouch-walking | 1.9 m/s | 1.57 | 1.86 |
| Aiming down sights | 2.4 m/s | 1.72 | 2.08 |
| Walking | 3.8 m/s | 2.14 | 2.71 |
| Sprinting | 6.4 m/s | 2.92 | 3.88 |

- Exposure starts at 0 at spawn, rises from the first sight check that sees the player (before the unit engages) and
  reaches 1 after 10 / 7.1 / 5.6 s of unbroken sight. Out of sight it is gone in 2.2 s.

### 3.6 Attack tokens

One global counter limits how many units may run a **ranged** attack at once (`src/enemies/logic.js:29`,
`src/enemies.js:149`):

```
limit = (living units of both types > 5) ? tokensCrowd : tokens
request(type, now):
    ok = held < limit and (now − lastGrantAt) >= tokenGap
    if ok and lastGrantType == type:
        other = the other type
        if (now − refusedAt[other]) <= 0.5 and (now − lastGrantAt) < 2.2 · tokenGap: ok = false
    if not ok: refusedAt[type] = now ; return false
    held += 1 ; lastGrantAt = now ; lastGrantType = type ; return true
release(): held = max(0, held − 1)
```

- A unit asks when its telegraph is about to start (every frame while it is ready and refused) and holds the token
  through the telegraph and the burst. It gives it back when the burst ends, when it leaves `engage`, when it dies,
  and when a Goon drops the attack for a rush.
- The fairness rule makes Goons and Buzzards alternate when both are asking: a type that got the last token is
  refused while the other type was refused within the last 0.5 s, until 2.2 gaps have passed.
- The rush needs no token. Tokens are reset by `clear()`.

### 3.7 The Goon

#### 3.7.1 Spawning

`spawn('goon', pos, opts)` (`src/enemies/goon.js:204`): a position that is not walkable is moved to the nearest
walkable cell within 4 m; the feet go to the ground height there; home = that point; yaw = `opts.yaw` or random;
outfit = `opts.variant` or a random one of three; the first cooldown is drawn from [0.6, 1.6] s; the first patrol
pause from [0, 1.5] s. There is no spawn effect: he is simply there (the flow picks points the player cannot see, 3.9).

#### 3.7.2 Patrol (`src/enemies/goon.js:654`)

He wanders. After a pause he asks the nav grid for a random walkable point within 7 m of home, in the same connected
area, and walks there at 1.5 m/s with the gun at low ready, head scanning. On arrival, or when two path queries in a
row fail, he pauses [1.5, 4.5] s and picks again. When stuck he drops the goal and waits 0.5 s.

#### 3.7.3 Investigate and search (`src/enemies/goon.js:673`)

Both modes run the same routine toward `lastKnown`:

1. Further than 2.2 m from the spot: go there. More than 8 m away he **runs** (`runSpeed`); inside 8 m he **stalks**
   at 2 m/s with the gun shouldered (aim weight 0.85) and half crouched (crouch weight 0.4). His head faces the spot.
2. There (or when the path failed twice, or after three stuck events): he stands and **sweeps**. The gun yaw follows
   `base + 0.9 · sin(1.3 · t)` where `base` is the bearing he came in on, the body follows the gun at 0.6 × `turnRate`
   (1.5 rad/s), the gun stays up.
3. When the timer runs out he goes back to patrol where he stands.

Elevated spots: if the last known position is more than 1.2 m above his feet (the player was on the scaffold deck or
in the mezzanine office), walking to it would park him under the floor, the one place with no sightline. Instead he
asks for a **stand-off point** (`src/enemies/goon.js:507`): the fire-position candidates and cost of 3.7.5 (with 14
random points instead of 7) built around that spot instead of around the player, minus every candidate that lies
under a floor higher than his feet + 1.2 m, with "sight" meaning a line from gun height at the candidate to 1.6 m
above the spot. He walks to the best one (stopping within 0.7 m) and sweeps there, looking up. Until the choice is
made he stops 4.5 m short of the spot, or does not move at all if he is already under that floor. He chooses again
when the spot moves more than 1.5 m, or after 2.5 s of sweeping at a point that turned out not to see the spot.

Goons never climb: the nav grid is one flat layer, and the stairs to the scaffold deck and to the mezzanine are
obstacles in it. **(measured)**: with the player on the scaffold deck for 60 s, four Goons stayed on the street
(highest feet 0.15 m, a kerb) and fought from 8 to 13 m away.

#### 3.7.4 Locomotion (`src/enemies/goon.js:296`)

The nav grid (`src/physics.js:33`): 0.5 m cells over the play bounds (92 × 68 m, 184 × 136 cells); a cell is blocked
when its centre lies inside a collider grown by 0.5 m; only colliders that reach above 0.47 m and start below 1.5 m
count (lower ones are stepped over, higher ones walked under); player-only, bullet-only and `noNav` boxes do not
count (`src/physics.js:91`). Paths are A* on that grid, 8-connected without corner cutting, then string-pulled; a
blocked start or goal snaps to the nearest free cell within 6 m and the goal must be in the start's connected area
(`src/physics.js:907`).

Per frame, for a Goon with a goal, a path and a wanted speed:

```
skip waypoints closer than 0.55 m (not the last one); the goal is reached within 0.45 m of the last waypoint
wantYaw   = bearing to the current waypoint
error     = abs(shortest angle from yaw to wantYaw)
remaining = distance to the waypoint (+ 2 m if it is not the last one)
target    = error > 1.1 ? 0 : min(wantSpeed · (1 − 0.5 · error), 0.4 + 2.6 · remaining)     // logic.js:147
yaw      += clamp(angle to wantYaw, ± rate · dt)     rate = 5 rad/s while moving (speed > 0.3 or target > 0), else 2.5
speed     = moveToward(speed, target, (target > speed ? 7 : 9.8) · dt)
velocity  = forward(yaw) · speed                     // he moves where he faces, not straight at the waypoint
```

- So he stops to turn when more than 63° off, slows in corners (half speed at 1 rad off), eases in over the last
  1.6 to 1.9 m of a run, and his turning circle at a run is about 1 m (speed / 5 rad/s).
- **Separation** is added to the velocity: from every other living Goon within 1.7 m (and within 1.5 m of his
  height) a push of `(1 − d / 1.7) · 2.2` m/s straight away from him; from the player within 1.25 m a push of
  `(1 − d / 1.25) · 3` m/s, except during the dash. Two Goons on the same spot step apart by slot number.
- The result is moved with the same capsule mover as the player (radius 0.3, height 1.8, 0.42 m step-up, wall slide,
  gravity 20 m/s² off a ledge). His animation is driven by the distance he actually covered.
- **Re-planning**: every [0.6, 0.75] s he checks that the straight line to his next waypoint is still walkable on the
  grid and asks for a new path if not. Path queries are served two per frame over all Goons.
- **Stuck**: wanting more than 0.6 m/s but covering less than 30 % of it adds up; after 0.5 s: engaged and moving →
  choose another fire position; patrolling → drop the goal, wait 0.5 s; investigating → ask for a new path, and after
  the third time count the spot as reached (`src/enemies/goon.js:962`).
- Enemies do not collide with each other or with the player: separation is the only thing keeping them apart.

#### 3.7.5 Engage: the state machine

`enemy.sub` holds the step (`src/enemies/goon.js:740`). On entering `engage` he starts in `move` and asks for a fire
position. In `move`, `aim` and `cool` (the "free" steps) two checks come first every frame:

- **Rush** (3.7.8): the player is alive, the rush is off cooldown, the horizontal distance is under 3 m, the height
  difference under 1.4 m, there is line of sight from 1.2 m above his feet to 1 m above the player's, and nothing
  that blocks a body lies between them at 1 m (so not through the Cage's chain-link). Then: `windup`.
- **Re-pick**: no fire position yet, or the player has moved more than 7 m from where he stood at the last choice.

| Step | What he does | Leaves when → to |
|---|---|---|
| `move` | Runs (`runSpeed`) along his path to the fire position, gun at port arms | Arrived → `aim`. 7 s without arriving → `aim`. After 1.4 s, with sight, 7 to 20 m from the player: chance 0.7 per second → `aim` where he is. Path failed twice → `aim` and relocate. Stuck 0.5 s → relocate |
| `aim` (on arrival), `cool` (after a burst): identical | Stands, body turns to the player at 2.5 rad/s, gun yaw follows at 4.5 rad/s, gun shouldered. At an authored cover point with a shot, within 1.2 m of it and with more than 0.4 s of cooldown left: **kneels**, gun lowered (aim weight 0.3) | With sight, cooldown over, not waiting for a new position, gun within 0.14 rad of the bearing, token granted → `telegraph`. Ready but refused for 3 s → relocate. Sight and the player closer than 5 m for 0.8 s → relocate. No sight for 1.1 s → relocate |
| `telegraph` | Stands, keeps tracking, the weapon light flares up for 0.5 s: brightness 1.5 + 14 k² with k from 0 to 1 | 0.5 s → `burst`. Sight is not needed any more |
| `burst` | Fires `burst` rounds, one every 0.11 s, the first at once; weapon light at 6 | Last round → `cool`: token returned, cooldown = `cooldown` × scale, burst count + 1; if the count has reached 1 (chance 0.6, decided at the last choice) or 2 → relocate |
| `windup` | 0.28 s: stops, turns on the player at 7.5 rad/s, draws and raises the pipe. `enemy:melee windup` | 0.28 s → `lunge`, snapping to face the player |
| `lunge` | Dashes at 9.5 m/s straight at the player, steering at 5 rad/s | Player within 1.35 m (height within 1.3 m, body path clear) → the blow lands, `recover`. 0.36 s, or blocked (slower than 2.85 m/s after 0.08 s) → swings at the air, `recover` |
| `recover` | 0.55 s: stands, brakes at 40 m/s², puts the pipe back | → `aim` with the rush on a 3.5 s cooldown, and relocates |

"Relocate" = ask for a new fire position at least 3 m from where he stands. The cooldown keeps running during every
step except `telegraph` and `burst` (`src/enemies/goon.js:934`), so a Goon that relocates usually arrives ready.

**Choosing a fire position** (`src/enemies/goon.js:453`, one choice per frame over all Goons):

```
candidates:
  every level.coverPoints entry within 1 m of his height                         kind authored (cover = true)
  7 random points: angle U(0, 2π), distance 8 + 10 · sqrt(U) from the player      kind random
  5 points on an arc ± 1.3 rad around his own bearing from the player,
      each jittered ± 0.15 rad, at U(9, 17) m                                     kind arc
keep a candidate if it is 8 to 18 m from the player (horizontal) and walkable,
  and, when relocating, at least 3 m from where he stands
sight(c) = lineOfSight(c at his feet height + 1.46 m → player eye)

cost(c) = 0.9 · distance(c, self) + bias(kind: −2 / 0 / +1) + 3 · U(0, 1)
        + for every other engaged Goon o (its destination = its fire position, else where it stands):
              a = angle between the bearings of c and of o's destination, seen from the player
              if a < 30°: + 14 · (1 − a / 30°)
              if c is within 3 m of o or of o's destination: + 16
        + (sight(c) ? (cover ? −4 : 0) : + 22)
lowest cost wins; atCover = winner is authored and has sight
```

The level provides 100 cover points (`src/level/data.js:84`): 45 on the avenue, 37 in the lot and the Cage, 15 in the
shop, 3 at the west end; 3 of them are up on the scaffold deck and the mezzanine, out of every Goon's reach
**(measured)**. If no candidate survives: within 18 m of the player he shoots from where he is; further away he heads
for the point on the line to the player that is 13 m short of him (`src/enemies/goon.js:556`). A goal closer than
0.7 m counts as reached.

The effect: Goons spread around the player (no two on the same line of fire, never shoulder to shoulder), prefer
cover they can shoot from, and keep moving. And a player who breaks line of sight gets flanked: every position is
scored against where he really is, so a Goon that has stood 1.1 s without a shot heads for a spot that can see him
again; only after 4 s without any sight does he fall back to searching the place the player was last seen (3.2).

#### 3.7.6 One round (`src/enemies/goon.js:600`)

```
origin = his feet + 1.46 m (on the body axis, whatever the pose)
aim    = player feet + 1.0 m (0.8 m if the player crouches)
if the player's feet are more than 1.2 m above his and the line origin → aim is blocked:    // behind the parapet
    aim.y = player eye − 0.25 m ; if that is blocked too: aim.y = player eye ; spreadY = 0.3
dir    = spread applied to (aim − origin)                       // 3.5, perSpeed 0.3
result = hitscan(origin, dir, 200 m, shotDamage · scale)        // world, explosives, the player; never other enemies
tracer from the drawn muzzle to the hit point; muzzle flash; point light on every other round; recoil kick
```

A round is aimed at where the player is, with no lead. The first round of a burst leaves the moment the telegraph
ends. Rounds stop on cover: the world hit comes first (`src/combat.js:155`).

#### 3.7.7 Cover use

Cover is not a special state. A fire position that is an authored cover point with a shot sets `atCover`; while he
stands on it between bursts (cooldown above 0.4 s) the pose solver gets crouch weight 1 and aim weight 0.3, so he
kneels with the gun lowered, and stands up again about 0.4 s before the gun is ready (the crouch blend reaches 96 %
in 0.4 s). He always stands for the telegraph and the burst. Kneeling lowers his head sphere from 1.57 m to 1.12 m
and the top of his body capsule from 1.59 m to 1.15 m; his eyes (1.6 m) and his shot origin (1.46 m) do not move. A
kneeling Goon tops out at about 1.28 m: seen level, he is hidden behind a sedan roof (1.45 m) or a dumpster (1.35 m)
and shows his head over the lower kinds of cover (a bonnet or a barrel at 1.0 m, a jersey barrier at 0.81 m; heights
from `docs/DESIGN.md:211`).

#### 3.7.8 The rush (`src/enemies/goon.js:636`, `:871`)

Timeline from the moment the conditions of 3.7.5 are met:

| t | What |
|---|---|
| 0 | Any telegraph or burst is dropped and its token returned. `enemy:melee windup` (a growl and the pipe scraping). He stops |
| 0 → 0.28 s | Wind-up: turns on the player at up to 7.5 rad/s; the right hand leaves the gun, takes the pipe from his back (first 40 %) and cocks it over the right shoulder (last 60 %) |
| 0.28 s | Snaps to face the player; the dash starts at full speed (9.5 m/s, no acceleration), steering at 5 rad/s |
| during the dash | As soon as the player is within 1.35 m (and within 1.3 m of height, and a body could pass between them): `rushDamage` to the player (kind `melee`, direction from his chest), the pipe swings (0.14 s), `enemy:melee strike` |
| 0.28 + 0.216 s | No contact yet: the pipe swings anyway (60 % of the dash) |
| 0.28 + 0.36 s at the latest | The dash ends (also when it runs into something) |
| + 0.55 s | Recovery: he stands, the pipe goes back on his back, the hand returns to the gun |
| after | Rush cooldown 3.5 s; he relocates to a fire position and goes back to shooting |

The dash covers at most 3.42 m. Arithmetic at constant speeds (derived): against a player backing straight off at
walking speed (3.8 m/s × 0.82 backwards = 3.1 m/s, `src/config/player.js:21`) the dash closes 2.3 m and has to bring
him within 1.35 m, so it connects when the rush began inside about 2.8 m and just misses from the full 3 m.
Side-stepping after the snap, or sprinting away (6.4 m/s), gets clear. The blow lands at the start of the swing
animation, not at its end.

#### 3.7.9 Being hit

A hit that does not kill is cosmetic for the body (`src/enemies/goon.js:999`): a spring shoves hips, spine and head
along the shot (strength = min(1.6, damage / 28), × 1.5 for a head hit) and the whole model flashes warm white for
about 0.15 s. It does not interrupt movement, the telegraph or the burst. What it does change is the mode: 3.4.

#### 3.7.10 Death and the body

On the killing hit (`src/enemies/goon.js:1014`, `src/enemies/goon-anim.js:746`): any attack is dropped, the token
returned, `enemy:killed` is emitted, and a 0.9 s collapse starts from the pose he was in:

- Direction: along the horizontal direction of the killing shot. Shot from the front half, he goes over backwards and
  ends on his back; shot from behind (the shot direction within about 75° of his facing), he pitches forward onto his
  face. A killing blast pushes him away from the blast. Every Goon has a handedness (odd or even id) that mirrors the
  final pose.
- 0 to 0.70 s: the knees give during the first 0.28 s (the hips sink toward 0.62 m) while the body starts to topple,
  accelerating, sliding 0.5 m (back) or 0.4 m (front) along the shot until the hips lie at 0.12 m; arms fly up and
  trail; the head lags, then drops and rolls.
- The SMG leaves his hands at once, falls under gravity, skids about 0.46 m over half a second and stops on its
  side. The pipe stays strapped to his back.
- 0.63 s: a dust puff at his feet. 0.70 to 0.90 s: a small bounce (4.5 cm) and the limbs settle.

From 0.9 s he is a **body**: not in `enemies.list`, not hit by rays, not an obstacle, still casting a shadow. At most 6
bodies stay; a seventh makes the oldest dissolve over 3.2 s (a screen-door dither, its shadow off at once); any body
dissolves by itself after 45 s (`src/enemies/goon.js:1043`). If a Goon has to spawn while all 12 slots are in use, the
oldest body gives up its slot at once, without a dissolve; with no body, a Goon that is still collapsing does
(`src/enemies.js:288`).

### 3.8 The Buzzard

A free-flying body with a velocity, steered toward a wanted point. No pathfinding at all.

#### 3.8.1 Spawning (`src/enemies/buzzard.js:263`)

The given position is used, with these corrections: lower than 2.2 m above the ground under it → 5 to 5.6 m above
that ground; inside the El deck's footprint and between 1.5 m under its underside and 2 m above it → 1.5 m under the
underside; overlapping anything solid → pushed out into free air. Home = that point. Drawn once per spawn: yaw
(unless given), first cooldown [1, 2.5] s, personal orbit altitude [4.8, 7.2] m, orbit radius [14, 22] m, orbit
direction (either), patrol radius [4, 9] m, strobe phase. No spawn effect; the rotor loop starts on `enemy:spawn`.

#### 3.8.2 The wanted point per mode (`src/enemies/buzzard.js:318`)

| Mode | Wanted point | Speed cap |
|---|---|---|
| `patrol` | Home + patrol radius × (cos a, 0, sin a), at home height; a advances 0.28 rad/s in its direction | 3 m/s |
| `investigate`, `search` | Last known + 4.5 m × (cos a, 0, sin a), at last known height + min(altitude, 5.5 m); a advances 0.5 rad/s | 5.5 m/s |
| `engage`, sight within the last 1.5 s | Player feet + orbit radius × (cos a, 0, sin a) + altitude. a advances by direction × speed / radius per second, speed 3.6 m/s, or 0.9 m/s while telegraphing or firing. Every [3, 8] s: reverse with chance 0.6, and radius += U(−3, 3) m, kept in [13, 23] m. If drone and player are inside the same interior box, x and z are kept 1.5 m inside its walls | 8 m/s |
| `engage`, no sight for 1.5 s | Last known + (altitude + 1 m) straight up | 8 m/s |

On entering a mode the angle a is set to the drone's current bearing from that mode's centre, so it joins its circle
where it is instead of cutting across (`src/enemies/buzzard.js:898`). One orbit at 18 m takes 31 s (derived).

Hover heights at a glance: on patrol, the height it spawned at (authored air points are 8.6 to 16.2 m up; a spawn
asked for at street level comes in 5 to 5.6 m above the ground); curious, at most 5.5 m above the spot; engaged, 4.8
to 7.2 m above the player's feet; anywhere under the El, at most 5.0 m; never less than 2.2 m above the ground under
it by choice and never less than 1.1 m at all; never above 15.5 m.

#### 3.8.3 Corrections to the wanted point, in this order (`src/enemies/buzzard.js:468`)

1. **Into the shop through a doorway** (`src/enemies/logic.js:742`). If the wanted point is inside an interior box
   and the drone is not: head for the point 2.5 m outside the doorway that gives the shortest way, at the doorway's
   flight height; once inside the doorway's corridor (between its outside and inside points, within 1 m of its centre
   line and 0.35 m of its height) go through to the point 2.5 m inside. Doorways are found once, by probing every
   wall of `level.interiorBoxes` from outside with a pair of horizontal rays (2.4 m and 3.2 m up) every 0.5 m: a run
   at least 2 m wide where both pass is a doorway, and its flight height is 0.6 m under its lintel, at least 2.4 m
   (`src/enemies/buzzard.js:203`). **(measured**, headless build with stand-in props): two doorways, both in the
   shop's south wall (z = −11): x = −12.15 at 3.6 m and x = −1.4 at 2.8 m.
2. **Height band.** Wanted height = clamp(wanted, ground under the drone + 2.2 m, min(15 m, felt ceiling − 1.3 m)).
3. **The El deck plan** (`src/enemies/logic.js:371`). The track deck is a slab over the whole avenue; `level.el`
   **(measured)**: underside y = 6.5 m, top 6.83 m, x −46 … 46, z −5.4 … 5.4. With the config that gives a pass-under
   height of 5.0 m (underside − 1.5), a pass-over height of 11.1 m (underside + 1 + 3.6) and a footprint grown by
   1.5 m. A drone never steers through the slab:

   | Drone is | And | Rewrite of the wanted point |
   |---|---|---|
   | Inside the footprint, under the deck | | Height capped at 5.0 m |
   | Inside the footprint, over the deck | Wanted height ≥ 11.1 m | None |
   | Inside the footprint, over the deck | Wanted point lower | Leave sideways first: z = 5 m beyond the deck's edge (the wanted point's side if it lies outside, else the nearer side), height = max(own, 11.1 m) |
   | Outside, straight line crosses the footprint | Own height ≥ 10.6 m and wanted ≥ 11.1 m | None (crossing over) |
   | Outside, line crosses | Own height ≤ 5.6 m | Height capped at 5.0 m: go in under |
   | Outside, line crosses | Still higher | Height capped at 5.0 m and the point pulled back to 2.5 m before the footprint: come down there first |

4. **Climbing over what is ahead** (`src/enemies/logic.js:511`), skipped under the deck and while passing a doorway.
   Along the next 6 m of the flat line to the wanted point, widened by the airframe radius, every solid box it
   crosses raises the wanted height: to its top + 2.2 m when the top is above the airframe's underside (an obstacle:
   climb over it), to its top + 1.32 m when the airframe is already above it (a roof: stay over it, free to come down
   to it). Not counted: poles (under 1 m across both ways: lamp posts, columns), boxes inside the El's footprint,
   boxes with tops above 15 m, and overhangs whose underside is above both the drone and the wanted height.
5. **At the deck's edge** (`src/enemies/logic.js:714`): when the plan says "go under" but the climb found something
   tall in the way within 3.5 m of the footprint, aim straight across the nearest edge instead of diagonally; if that
   is still blocked, slide 5 m along the deck, away from the blocking box, until there is room to come down.
6. Cap the wanted height at the ceiling of step 2 again.
7. **Detour** (`src/enemies/buzzard.js:431`), the last resort: wanting to be more than 2.5 m away (sum of the axis
   differences) but not having moved 0.5 m in 2.5 s, it picks a random horizontal direction with a clear body path
   (six tries) and flies 4 m that way and up to 1.5 m higher for 1.5 s.

#### 3.8.4 Steering and collision, per frame (`src/enemies/buzzard.js:512`)

```
a    = Kp · (want − pos) − Kd · vel + push            Kp, Kd = 2.2, 2.4 horizontally and 5, 3.6 vertically
if under half hit points: a += 1.6 · (sin 5.3w, 0.7 · sin(7.1w + 1), cos 4.7w)       // w = seconds spent damaged
a    = clampLength(a, 11)
vel += a · dt ;  vel = clampLength(vel, speed cap of the mode)
push = push · e^(−6 · dt)
one feeler ray (in rotation: ahead, down, up)
move along X, then Z: stop 0.6 m short of any surface; a stopped axis keeps −0.25 × its speed (a soft bounce)
move along Y: stop 0.42 m short; if it came down onto a pole, step off sideways at 2 m/s
pos.y >= ground + 1.1 ;  pos.y <= 15.5 ;  stay 1.2 m inside the play bounds
push-out: an airframe (upright cylinder, radius 0.5 m, ± 0.22 m) that overlaps a solid box is moved the shortest
          way out (up, down, or sideways; off a pole always sideways) and loses the velocity pointing back in
```

Feelers (`src/enemies/buzzard.js:366`), one per frame:

- **Ahead** (only above 0.3 m/s), along the velocity, reach 2.2 m + 0.5 s × speed. On a hit at distance d:
  k = (1 − d / reach) × 17.6; `push` += surface normal × k, plus 0.5 k upward. If d is under half the reach and the
  last flip was more than 1.2 s ago, the orbit direction reverses.
- **Down**, 2.4 m: `push.y` += (1 − d / 2.4) × 16.5.
- **Up**, 4 m: remembers the ceiling height (step 2 of 3.8.3); forgotten when an up-ray finds nothing and the last
  find is more than 0.5 s old.

What counts as solid: the collision and feeler rays use the bullet world (everything except player-only boxes). The
overlap tests (ground, climbing, push-out) use every movement-blocking box except the player-only ones, but treat the
hoist netting (tag `hoist`) and the office glass (tag `office-glass`) as solid (`src/enemies/logic.js:432`). A Buzzard
therefore flies through the Cage's fence collider, railings and the invisible seals of the block, and is kept in the
block by the bounds clamp alone.

Buzzards do not avoid each other, the Goons or the player. Their personal radius, altitude and orbit angle are what
spreads them out.

#### 3.8.5 Attitude, facing, gimbal and eye (`src/enemies/buzzard.js:600`, `:693`)

- **Yaw** turns at 3.2 rad/s toward: the player (engaged, sight within 1.5 s); the last known position (investigating,
  searching, engaged without sight); its own direction of travel (patrol).
- **Bank**: the nose dips toward the acceleration: pitch and roll = 0.034 rad per m/s² of forward and sideways
  acceleration, each capped at 0.5 rad, plus hit kicks, plus a wobble when damaged (0.1 and 0.13 rad at 9.1 and
  7.7 rad/s), smoothed with `damp(rate 7)`.
- **Rotors**: power = 0.75 + 0.25 × (acceleration / 11); the blades turn at 41 rad/s × power, neighbours in opposite
  directions; power follows with `damp(rate 6)` up and 1.6 down (`src/enemies/buzzard-model.js:132`).
- **Gimbal** (eye and gun together): yaw toward the target relative to the nose, within ± 1.5 rad; pitch toward the
  target relative to the airframe's pitch, within −1.35 … +0.5 rad; `damp(rate 14)`. It looks at the player's chest
  (feet + 1.05 m) when engaged, 1 m above the last known position when curious, 3 m below its own height on patrol.
- **Eye brightness** (the lamp follows with `damp(rate 30)` rising, 10 falling): patrol 0.7; investigate and search
  1.3 + 0.6 sin(6t); engage 2.5; telegraph 2.5 + 16 k²; volley 7; every bolt sets it to 12 at once.

#### 3.8.6 Attack (`src/enemies/buzzard.js:644`)

The cooldown counts down in every mode; a volley can only start while engaged.

| Step | What | Leaves when |
|---|---|---|
| Ready | Orbiting; cooldown running | Engaged, sees the player, cooldown over, closer than 42 m (3D), nose within 0.35 rad of the bearing, token granted → telegraph, `enemy:telegraph` |
| Telegraph | `telegraph` seconds (0.55 / 0.46 / 0.38): the eye flares up, the orbit slows to 0.9 m/s | Time up → volley, with a lead share drawn from [0.2, 0.85]. (No longer engaged: token back, nothing fired) |
| Volley | 3 bolts, 0.12 s apart, the first at once | Last bolt → token back, cooldown = `cooldown` × scale |

One bolt (`src/enemies/buzzard.js:620`):

```
chest  = player feet + 1.05 m (0.75 m if he crouches)
flight = distance(gun muzzle, chest) / 70
aim    = chest + player velocity (all three axes) · flight · lead
dir    = spread applied to (aim − gun muzzle)              // 3.5, perSpeed 0.45, × 1.5 when damaged
bolt starts at (drone x, gun muzzle height, drone z)       // on the centre line, never inside what the gun pokes into
drone velocity −= dir · 0.35 m/s ; pitch kick 0.06 rad ; eye = 12 ; muzzle flash ; point light ; `enemy:fire`
```

#### 3.8.7 Bolts (`src/enemies/bolts.js:82`)

Simulated projectiles, straight flight, no gravity. Per frame and bolt:

```
step  = 70 · dt
world = raycast(pos, dir, step)                            // bullet world
reach = world ? distance to it : step
if the player is alive and within reach + 1 m (horizontally):
    if the segment pos → pos + dir · reach passes within 0.36 m of the upright segment
       from player feet + 0.35 m to player feet + 1.5 m (1.0 m if he crouches):
        player.damage(damage, from = where the bolt was fired, kind 'bolt') ; the bolt is gone
if world: an explosive there takes 9 ; `impact` event (from 'enemy', the surface hit) ; the bolt is gone
else:     pos += dir · step ; the bolt is gone after 1.3 s
```

Bolts pass through enemies. What makes them dodgeable (derived): the warning (0.38 to 0.55 s) plus the flight time
(0.20 s from 13 m, 0.34 s from 23 m, 0.60 s from the 42 m limit); the lead is partial and fixed for the volley, so a
change of direction after the first bolt takes the player out of the line; crouching lowers the top of the target
from 1.86 m to 1.36 m (capsule end plus radius).

#### 3.8.8 Being hit (`src/enemies/buzzard.js:749`)

Every hit: velocity += shot direction × min(3, 0.09 × damage) m/s; a random offset of up to ± 0.5 rad on pitch and on
roll that decays at rate 5; a flash. Under half its hit points, for good: steering jitter, attitude wobble, a smoke
puff every [0.1, 0.22] s, five sparks every [0.5, 1.7] s, spread × 1.5.

#### 3.8.9 Death: the spin-down and the burst (`src/enemies/buzzard.js:757`, `:775`, `:816`)

On the kill: velocity += 1.5 m/s up + 2.5 m/s along the shot; one random rotor comes off (ten sparks and four debris
chips at its hub, a smoke puff); the remaining rotors drop to quarter power; it starts to spin at 3 rad/s either way.

Per frame while falling: gravity 9.5 m/s²; horizontal velocity × e^(−0.4 dt); the spin gains 9 rad/s every second and
turns the yaw; the nose pitches toward 0.5 rad (rate 2); roll += 0.25 × spin × dt; smoke every 0.05 s, four sparks
every 0.16 s; the eye flickers (1.5 × |sin 40t|) for 0.5 s, then goes dark.

It lands when a ray along its velocity finds anything within this frame's travel + 0.25 m, or after 5 s in the air.
From orbit height that is about 1.1 to 1.4 s (derived). On landing it is removed and then bursts:
`combat.explode` with radius 3 m, damage 30, linear falloff, line of sight required. Goons and other Buzzards in the
radius take up to 30, the player up to 15 (kind `blast`), explosive props nearby are chained, and the `explosion`
event draws a small "drone" explosion (more electric sparks, less fire: `src/fx/recipes.js:649`) and alerts 30 m.

### 3.9 Spawn-in and pooling

`spawn(type, pos, opts)` (`src/enemies.js:284`) takes, in this order: a free slot of that type; for a Goon, the slot
of the oldest body; the slot of a unit of that type that is still dying; otherwise it returns null. It then resets the
unit (hit points = `hp` × holdout scale, mode `patrol`, first sight check within 0.19 s), runs the type's own spawn
(3.7.1, 3.8.1), and with `alerted` sends it to investigate `opts.target` (else the player) for 10 s (Goon) or 8 s
(Buzzard). `clear()` retires every unit and body, resets the tokens and removes all bolts.

What the game flow adds around it, for context (`src/game.js:405` to `:514`, `src/config/flow.js:58`):

- The level offers 46 authored points (`src/level/data.js:24`, `:60`): 29 on the ground (12 avenue, 10 lot, 7 shop)
  and 17 in the air (6 avenue, 7 lot, 4 shop; 8.6 to 16.2 m up); none in the west zone **(measured)**.
- The starting patrol spawns unaware, at least 32 m from the player's start, out of its sight where possible.
- A reinforcement gets its point when its wave is queued: at least 18 m from the player preferred, hidden from his
  eye, not used in the last 6 s, jittered ± 1.2 m. In Story the first arrives 1.6 s after the reel is grabbed, then
  one every 0.85 s; one arrival per frame at most. An arrival waits 1 s while the alive cap is reached; a ground
  point the player has walked within 9 m of is swapped for a fresh one; a spawn the pool refuses is retried every
  1.5 s, six times. Air points under 2.5 m are lifted to [6, 9] m.
- After every arrival the flow calls `alert(player position, 60)`.

The result for the player: reinforcements appear where he is not looking, already hunting. A Goon runs toward where
the player was when he spawned, is re-pointed at the player's current position by every later arrival's alert, stalks
the last 8 m with the gun up, and engages after a quarter of a second of sight.

### 3.10 Taking damage (`src/enemies.js:337` to `:460`)

- **Hit test for the player's rounds** (`enemies.raycast`): the nearest of every living Buzzard's ellipsoid, every
  living Goon's head sphere (`part: 'head'`) and body capsule (`part: 'body'`). The world is combat's business: a
  body only counts in front of the nearest world hit (`src/combat.js:158`).
- **Sources**: the player's guns (head × 2.2 on Goons); the player's melee (60 damage to the nearest unit whose body
  surface is within 2.3 m, inside a 50° cone, in line of sight; always `body`: `src/combat.js:246`,
  `src/config/weapons.js:158`); blasts (linear falloff to the radius, line of sight to the unit's centre, which is the
  feet + 0.9 m for a Goon; always `body`: `src/combat.js:321`).
- `damage(enemy, amount, info)`: hit points down, `enemy:hit`, the type's reaction (3.7.9, 3.8.8). Survived and not
  engaged: provoked (3.4). Dead: 3.2.
- Enemy rounds and bolts never hurt enemies. Blasts do, the crash of a Buzzard included, and every blast kill is
  credited to the player.
- Impact surface: `flesh` for a Goon, `drone` for a Buzzard (`src/combat.js:70`). The effect for a body hit is a
  dusty cloth puff (`#9a6a64`), never blood; for a drone, grey chips and sparks (`src/fx/recipes.js:29`).

### 3.11 Readability cues

| Cue | Rule | Source |
|---|---|---|
| Goon weapon light: the telegraph | Lamp target 1.5 + 14 k² through the telegraph (k from 0 to 1), 6 during the burst, 0 otherwise; the lamp follows with `damp(rate 30)` rising and 9 falling. A flare sprite at the lens, diameter 0.12 + 0.62 · sqrt(min(1, lamp / 15)) m: 0.32 m when the telegraph starts, 0.74 m when it ends, 0.51 m during the burst. Colour linear (1, 0.74, 0.42) × 0.9 × lamp. "A cue the player must catch at 15 m" | `src/enemies/goon.js:839`, `src/enemies/goon.js:1065`, `src/enemies/goon-anim.js:367` |
| Buzzard eye | Flare diameter 0.16 + 0.75 · sqrt(min(1, lamp / 18)) m: 0.31 m on patrol, 0.31 to 0.40 m pulsing when curious, 0.44 m engaged, 0.91 m at the end of the telegraph, 0.77 m at each bolt. Colour linear (1, 0.09, 0.05) × lamp | `src/enemies/buzzard.js:719`, `src/enemies/buzzard.js:849` |
| Buzzard strobes | 1.3 s cycle: port red and starboard green flash at 0 to 0.05 s and 0.16 to 0.21 s, the white tail light at 0.65 to 0.71 s; flares of 0.22, 0.22 and 0.26 m; living units only | `src/enemies/buzzard.js:57`, `src/enemies/buzzard.js:862` |
| Rotor blur | A translucent disc of radius 0.185 m just above each hub, brightness with rotor power; the blades under it turn slowly enough to read (6.5 turns per second) | `src/enemies/buzzard.js:838`, `src/enemies/glow.js:48`, `src/enemies/buzzard-model.js:132` |
| Hit flash | The whole model adds warm white, linear (1, 0.82, 0.62) × 0.55 × flash; a hit adds 0.55 + 0.25 × strength (Goon) or 0.7 (Buzzard), capped at 1; it decays at 7 per second | `src/enemies/rig.js:165`, `src/enemies/goon-anim.js:192`, `src/enemies/buzzard.js:754` |
| Self-lit trim | Share of its own colour a part emits: mask 0.2, oxblood accents 0.3, sneakers 0.05, pipe 0.03; the Buzzard's oxblood panels 0.3. Scaled by the time of day: × 0.12 by day, × 1 by night | `src/enemies/goon-model.js:97`, `src/enemies/buzzard-model.js:55`, `src/config/enemies.js:21` |
| Rim light | A cool view-dependent rim: Goon `#9db8ff` × 0.55, power 2.4; Buzzard `#a8bcff` × 0.5, power 2.2. × 0.12 by day, × 0.8 by night | `src/enemies/goon-model.js:252`, `src/enemies/buzzard-model.js:94` |
| Flares by day | 1.35 × larger, and they cover 60 % of the bright background behind their core instead of only adding to it, so red stays red on a sunlit wall | `src/config/enemies.js:22`, `src/enemies/glow.js:96` |
| Tracers | Enemy rounds and bolts are red (`#ff3a22`); the player's are warm white-gold (`#ffe2a8`) | `src/config/look.js:120` |

### 3.12 What the enemies do not do

So that nobody adds it by assumption: no friendly fire from guns; no collision between units or with the player; Goons
do not jump, climb stairs, vault, open doors, throw anything, retreat or surrender; there is no morale, healing or
reloading; SMG rounds are not led; a dropped SMG cannot be picked up; Buzzards do not land, perch or avoid each other;
nothing communicates beyond the rally and alert radii of 3.4.

### 3.13 Reference traces (measured)

The real enemies module on the real level, stepped headless at 60 Hz, Boss, one enemy, the player standing still in
the open. Use them to check a port end to end.

Goon, 15 m away, unaware, facing the player:

| t | Event |
|---|---|
| 0.63 s | Engages (`enemy:alert`), runs to a fire position 0.9 m away |
| 1.80 s | Arrives, aims |
| 2.12 s | Telegraph |
| 2.65 to 3.08 s | Burst of 5, rounds 0.10 to 0.12 s apart; exposure 0.35 to 0.41; 1 hit |
| 3.18 to 4.92 s | Kneels at the cover point, stands 0.3 s before the next telegraph |
| 5.23 s, 5.77 to 6.20 s | Telegraph, burst of 5; exposure 0.78 to 0.85; 3 hits |
| 6.20 to 7.87 s | Relocates: 5.6 m in 1.7 s |
| 7.88 s, 8.42 to 8.85 s | Telegraph on arrival (cooldown already over), burst of 5; exposure 1.0; 5 hits |
| 8.95 to 10.87 s, 11.18 s, 11.72 s | Kneels; telegraph; burst; then relocates again |

Buzzard, 23 m away and 9 m up, unaware: engages at 0.52 s; first telegraph at 1.80 s (the first cooldown); bolts at
2.28, 2.40, 2.52 s; then a volley every 2.8 to 2.9 s (telegraphs at 4.68, 7.48, 10.42 s). In the first five seconds it
comes down from 9 m to 5 m (the pass-under height, the player being under the El) and closes from 23 m to 14 m.

Rush, Goon 2.6 m away, unaware: engages and starts the wind-up at 0.63 s; dash at 0.92 s; the blow lands at 1.03 s
(22 damage); recovers until 1.58 s; relocates 7.4 m in 2.7 s; telegraph at 4.95 s; burst at 5.48 s.

### 3.14 The stub (`src/stubs/enemies.js`)

A stand-in for builds without the real module: capsules and spheres that never move, turn to the player, notice him
after 0.55 s and fire one weak telegraphed hitscan shot every 2.5 to 4 s. Its shapes and numbers (Goon radius 0.35 m,
head radius 0.17 m at 1.63 m, a spherical Buzzard of 0.45 m, bodies gone after 2.5 s, `hear` = `alert`) are not the
game's. Nothing in it is to be ported; it only shows the API surface, which is the same as in 2.7.

---------------------------------------------------------------------------------------------------

## 4. Unreal mapping

### 4.1 Units, axes and angles

- Positions: Unreal (X, Y, Z) = (x_web, z_web, y_web) × 100 cm. Speeds × 100 (cm/s), accelerations × 100 (cm/s²),
  angles × 57.2958 (degrees). Rates per second and unit-free gains (the `damp` rates, the Buzzard's pull gains,
  exposure rates, cost weights) keep their numbers.
- **Yaw**: Unreal yaw = −(web yaw in degrees) − 90, wrapped to (−180, 180]. Web yaw 0 looks north (−Z), which is
  Unreal yaw −90 (north is −Y). Web yaw grows turning left, Unreal yaw grows turning right; turn rates keep their size.
- The Buzzard's circle angle `a` (centre + r (cos a, sin a) in web x, z) is the same number in Unreal's X, Y plane.
- A Goon's position in this document is his feet. An `ACharacter` location is the capsule centre: add 90 cm.
- Mesh spaces follow the shared conventions: the Goon faces +Y in Unreal mesh space (−Y in Blender), like the
  mannequin. **The Buzzard, the SMG and the pipe are authored like vehicles and weapons: nose, barrel and striking end
  toward +X** (Blender and Unreal), so the Buzzard pawn needs no mesh yaw offset. Model-space conversions from the
  web models (which face −Z with +X to their right): for the Goon, Unreal mesh (X, Y, Z) = (−x, −z, y) × 100; for
  the Buzzard and the SMG, Unreal mesh (X, Y, Z) = (−z, x, y) × 100. In Blender the same points are
  (−x, z, y) for the Goon and (−z, −x, y) for the Buzzard and the SMG, in metres.

### 4.2 Converted values

Shared:

| Value | Web | Unreal |
|---|---|---|
| Sight range; close range | 45 m; 3.5 m | 4500 cm; 350 cm |
| Vision cone | 200° total | 100° half-angle (peripheral vision angle) |
| Rally radius on sight / on hit | 18 m / 20 m | 1800 cm / 2000 cm |
| Noise radii: gunfire / blast / explosive prop / arrival / pursuit and holdout / default | 45 / 30 / 60 / 60 / 90 / 40 m | 4500 / 3000 / 6000 / 6000 / 9000 / 4000 cm |
| Player eye, standing / crouched | 1.68 m / 1.05 m | 168 cm / 105 cm above the feet |

Goon:

| Value | Web | Unreal |
|---|---|---|
| Movement capsule | radius 0.3 m, height 1.8 m | radius 30 cm, half-height 90 cm |
| Eye; shot origin (above the feet, on the capsule axis) | 1.6 m; 1.46 m | 160 cm; 146 cm |
| Head hit sphere | r 0.155 m, 0.12 m above the neck joint | r 15.5 cm, 12 cm above the neck joint |
| Body hit capsule | r 0.27 m, hip − 0.62 m (at least 0.27 m up) to neck − 0.13 m | r 27 cm, hip − 62 cm (at least 27 cm up) to neck − 13 cm |
| Run speed H / B / K | 4.5 / 5.0 / 5.4 m/s | 450 / 500 / 540 cm/s |
| Stalk; patrol; dash | 2.0; 1.5; 9.5 m/s | 200; 150; 950 cm/s |
| Acceleration; braking; brake after the dash | 7; 9.8; 40 m/s² | 700; 980; 4000 cm/s² |
| Turn rate standing / on a path / gun aim | 2.5 / 5 / 4.5 rad/s | 143.2 / 286.5 / 257.8 °/s |
| Turn rate in the wind-up / in the dash / sweeping | 7.5 / 5 / 1.5 rad/s | 429.7 / 286.5 / 85.9 °/s |
| Stop-and-turn threshold; aim tolerance | 1.1 rad; 0.14 rad | 63.0°; 8.0° |
| Waypoint passed; goal reached; fire position reached | 0.55; 0.45; 0.7 m | 55; 45; 70 cm |
| Separation from Goons; from the player | 1.7 m, 2.2 m/s; 1.25 m, 3 m/s | 170 cm, 220 cm/s; 125 cm, 300 cm/s |
| Gravity; step-up | 20 m/s²; 0.42 m | 2000 cm/s² (gravity scale 2.04); 42 cm |
| Patrol radius | 7 m | 700 cm |
| Investigate: stalk within; stop within; sweep | 8 m; 2.2 m; ± 0.9 rad | 800 cm; 220 cm; ± 51.6° |
| Elevated spot; re-stand; fallback stop | 1.2 m; 1.5 m; 4.5 m | 120 cm; 150 cm; 450 cm |
| Fire band | 8 to 18 m | 800 to 1800 cm |
| Re-pick when the player moved; minimum relocation | 7 m; 3 m | 700 cm; 300 cm |
| Arc candidates | ± 1.3 rad, 9 to 17 m | ± 74.5°, 900 to 1700 cm |
| Same-bearing window; crowd radius | 30°; 3 m | 30°; 300 cm |
| Travel cost | 0.9 per m | 0.009 per cm |
| Cover: height window; kneel within | 1 m; 1.2 m | 100 cm; 120 cm |
| Too close; aim-early range | 5 m; 7 to 20 m | 500 cm; 700 to 2000 cm |
| Shot range; aim point on the player (crouched) | 200 m; 1.0 m (0.8 m) | 20000 cm; 100 cm (80 cm) above his feet |
| Spread far → near, H / B / K (half-width of a box) | 0.12 → 0.045 / 0.095 → 0.038 / 0.08 → 0.032 rad | 6.88° → 2.58° / 5.44° → 2.18° / 4.58° → 1.83° |
| Over-cover aim | eye − 0.25 m, vertical spread × 0.3 | eye − 25 cm, vertical spread × 0.3 |
| Player target for rounds | cylinder r 0.38 m, 1.8 m (1.15 m crouched) | r 38 cm, 180 cm (115 cm) |
| Rush: start range; height window start / hit; reach | 3 m; 1.4 / 1.3 m; 1.35 m | 300 cm; 140 / 130 cm; 135 cm |
| Rush: longest dash | 3.42 m in 0.36 s | 342 cm in 0.36 s |
| Collapse slide back / front; gun skid | 0.5 / 0.4 m; 0.46 m | 50 / 40 cm; 46 cm |
| Footstep event range | 45 m | 4500 cm |

Buzzard:

| Value | Web | Unreal |
|---|---|---|
| Hit ellipsoid | radius 0.5 m, half-height 0.22 m | semi-axes 50 × 50 × 22 cm |
| Speed cap engaged / investigating / patrol | 8 / 5.5 / 3 m/s | 800 / 550 / 300 cm/s |
| Steering acceleration cap | 11 m/s² | 1100 cm/s² |
| Pull gains horizontal; vertical | 2.2 and 2.4; 5 and 3.6 | unchanged (per s² on the offset, per s on the velocity) |
| Yaw rate | 3.2 rad/s | 183.3 °/s |
| Bank | 0.034 rad per m/s², at most 0.5 rad | 1.95° per m/s² (0.0195° per cm/s²), at most 28.6°; 21.4° at full acceleration |
| Lowest wanted height; hard floor; under a ceiling | 2.2 m; 1.1 m; 1.3 m | 220 cm; 110 cm; 130 cm |
| Top of the block | 15 m (clamp 15.5 m) | 1500 cm (clamp 1550 cm) |
| Bounds margin | 1.2 m | 120 cm |
| Feelers ahead / down / up | 2.2 m + 0.5 s × speed / 2.4 m / 4 m | 220 cm + 0.5 s × speed / 240 cm / 400 cm |
| Feeler push at contact, ahead / down | 17.6 / 16.5 m/s² | 1760 / 1650 cm/s² |
| Stop short of surfaces, sideways / vertically | 0.6 m / 0.42 m | 60 cm / 42 cm |
| Climb: look ahead; clear an obstacle by; stay over a roof by | 6 m; 2.2 m; 1.32 m | 600 cm; 220 cm; 132 cm |
| Patrol circle | 4 to 9 m at 0.28 rad/s | 400 to 900 cm at 16.0 °/s |
| Investigate circle | 4.5 m at 0.5 rad/s, up to 5.5 m above the spot | 450 cm at 28.6 °/s, up to 550 cm |
| Orbit radius (band, drift) | 14 to 22 m (13 to 23 m, ± 3 m) | 1400 to 2200 cm (1300 to 2300 cm, ± 300 cm) |
| Orbit altitude above the player's feet | 4.8 to 7.2 m | 480 to 720 cm |
| Orbit speed; while firing | 3.6; 0.9 m/s | 360; 90 cm/s |
| El deck slab (level) | y 6.5 to 6.83 m, x ± 46 m, z ± 5.4 m | Z 650 to 683, X ± 4600, Y ± 540 cm |
| Pass under at most; pass over at least | 5.0 m; 11.1 m | Z 500; Z 1110 cm |
| Deck margin; hold; leave-over offset; slide | 1.5; 2.5; 5; 5 m | 150; 250; 500; 500 cm |
| Detour | 2.5 m away, 0.5 m in 2.5 s; 4 m, + 1.5 m, 1.5 s | 250 cm, 50 cm in 2.5 s; 400 cm, + 150 cm, 1.5 s |
| Doorway: width; probe heights; flight height; approach points | ≥ 2 m; 2.4 and 3.2 m; lintel − 0.6 m (≥ 2.4 m); 2.5 m either side | ≥ 200 cm; 240 and 320 cm; lintel − 60 cm (≥ 240 cm); 250 cm |
| Shop interior box (level) | x −24 to 6, y 0 to 6.3, z −31 to −11 m | X −2400 to 600, Y −3100 to −1100, Z 0 to 630 cm |
| Doorways found (stand-in props) | (−12.15, 3.6, −11) and (−1.4, 2.8, −11) m | (−1215, −1100, 360) and (−140, −1100, 280) cm |
| Gimbal limits | yaw ± 1.5 rad; pitch −1.35 to +0.5 rad | yaw ± 85.9°; pitch −77.3° (down) to +28.6° (up) |
| Bolt speed; life; reach | 70 m/s; 1.3 s; 91 m | 7000 cm/s; 1.3 s; 9100 cm |
| Fire range; nose tolerance | 42 m; 0.35 rad | 4200 cm; 20.1° |
| Aim point on the player (crouched) | 1.05 m (0.75 m) | 105 cm (75 cm) above his feet |
| Spread far → near, H / B / K | 0.065 → 0.018 / 0.052 → 0.016 / 0.042 → 0.014 rad | 3.72° → 1.03° / 2.98° → 0.92° / 2.41° → 0.80° |
| Bolt target on the player | capsule r 0.36 m, axis 0.35 to 1.5 m (1.0 m crouched) | r 36 cm, axis 35 to 150 cm (100 cm): half-height 93.5 cm centred 92.5 cm up (68.5 cm centred 67.5 cm) |
| Recoil per bolt; pitch kick | 0.35 m/s; 0.06 rad | 35 cm/s; 3.4° |
| Knockback | 0.09 m/s per damage point, at most 3 m/s | 9 cm/s per point, at most 300 cm/s |
| Hit kick; damaged wobble | ± 0.5 rad; 0.1 and 0.13 rad | ± 28.6°; 5.7° and 7.4° |
| Death kick up / along the shot; fall gravity | 1.5 / 2.5 m/s; 9.5 m/s² | 150 / 250 cm/s; 950 cm/s² |
| Death spin; nose | 3 rad/s + 9 rad/s²; toward 0.5 rad | 171.9 °/s + 515.7 °/s²; toward 28.6° |
| Crash burst | radius 3 m, 30 damage, player × 0.5 | radius 300 cm, 30, × 0.5 |
| Bolt streak; head | 2.4 m × 0.11 m; 0.34 m | 240 × 11 cm; 34 cm |
| Rotor (visual only) | 41 rad/s at full power | 391.5 rpm; a real 15 inch prop turns about ten times faster: use a blur disc |

### 4.3 Which Unreal feature carries which mechanic

| Mechanic | Unreal Engine 5 |
|---|---|
| Pools, caps, the list, `spawn` returning "no slot", bodies, `alert` / `hear`, difficulty and holdout scale | One `UWorldSubsystem` that owns both actor pools (12 Goons, 8 Buzzards, pre-spawned and hidden) and the body queue. Keep the slot rules of 3.9: the flow's retry logic depends on a refused spawn |
| Attack tokens | Plain C++ in that subsystem, exactly 3.6. Not Gameplay Abilities, not a behaviour-tree service |
| Mode machine and the Goon's engage steps | A small hand-written state machine per pawn (or a State Tree with the same states and timers). A generic behaviour tree is not needed: the transitions of 3.2 and 3.7.5 are the whole logic |
| Sight | A component ticking on its own [0.11, 0.19] s timer with one `LineTraceTestByChannel` from the sensor to the player's eye point, plus the `seen` and `exposure` accumulators. `UAIPerceptionComponent` (sight radius 4500, peripheral half-angle 100°) can supply the raw stimulus, but it has no accumulator, no "cone off while engaged" and no eye-point target, so the direct trace is simpler and exact |
| What blocks sight and bullets vs. what blocks bodies | The channels of `01-player.md` 4.4. Weapon and sight traces (the channel `02-weapons-combat.md` calls `Bullet`): blocked by world geometry and bullet-only blockers, not by chain-link, glass, railings or invisible walls. The pawn channel: blocked by everything that blocks pawns, those included. The web's `lineOfSight(a, b)` is the first (it stops 5 cm short of the far point), `lineOfSight(a, b, {movement: true})` the second |
| Hearing | Direct calls into the subsystem (`Alert(Location, Radius)`), as in the web game. `UAISense_Hearing` adds nothing: the rule is a plain 3D radius with no occlusion |
| Goon body and movement | `ACharacter` + `UCharacterMovementComponent`: capsule 30 / 90, `MaxStepHeight` 42, `MaxAcceleration` 700, `BrakingDecelerationWalking` 980, `MaxWalkSpeed` set per gait. Do **not** use `bOrientRotationToMovement`: turn the actor yourself at 143 / 286 °/s and feed input along the actor's forward vector, with the speed rule of 3.7.4 (stop above 63° of error, slow in corners, ease in) |
| Nav grid | Recast nav mesh, kept to one ground-level layer (see 6, item 1). Use a supported agent of **radius 50 cm**, step height 42 cm, so paths keep the web's 0.5 m distance from obstacles while the capsule stays 30 cm. `FindPathToLocationSynchronously` (or async) for paths, `GetRandomReachablePointInRadius(home, 700)` for patrol, `ProjectPointToNavigation` for "walkable" and the 4 m spawn snap, `NavigationRaycast` for the re-plan check. The per-frame budgets of the web version are not needed |
| Keeping Goons apart | Detour crowd (`UCrowdFollowingComponent`) or RVO on the movement component with a 170 cm radius; or the web's own push (3.7.4), which is ten lines. Decide what Goons and the player do on contact (see 6) |
| Fire positions | The cost function of 3.7.5 in C++ over three candidate sets: the level's cover points (import them from the exported level data), 7 random nav points in the 800 to 1800 cm ring, 5 on the arc. EQS (a ring generator plus distance, trace and dot tests) can express it and gives a debugger, but the "other Goons' bearings" term needs a custom test either way |
| SMG rounds | A line trace on the shot channel from the capsule axis 146 cm above the feet (not from the muzzle socket), 20000 cm, with the box spread of 3.5. Draw the tracer from the muzzle socket to the hit. Target on the player: a dedicated collision cylinder or capsule of radius 38 cm, 180 / 115 cm tall |
| Head and body hit volumes | Two bodies that follow the skeleton: a sphere on the head bone and a capsule from pelvis to upper spine (a two-body physics asset, or two primitive components on sockets), queried by the player's weapon trace. Head = × 2.2. Do not use the full ragdoll physics asset for hits unless the weapon tuning is redone (see 6) |
| Rush | The same state machine. During the dash set `MaxWalkSpeed` to 950 and the velocity directly (full speed at once, no acceleration) for at most 0.36 s; check the distance to the player every tick; apply the damage through the normal damage path with kind `melee` |
| Goon animation | An Animation Blueprint driven by the same parameters the web solver gets: speed, yaw rate, crouch weight, aim weight, aim yaw and pitch, look yaw and pitch, rush phase, lamp. Locomotion blend space (0 to 540 cm/s), aim offset (yaw ± 63°, pitch ± 40°), upper-body hold states, look-at, two-bone IK for the support hand, montages for wind-up / swing / recover, additive hit reactions. Details in 5.3 |
| Goon death and body | A 0.9 s death montage per direction (back, front; mirrored) blending into ragdoll, or ragdoll at once with an impulse along the shot. The body ignores the weapon and pawn channels. Dissolve: a dither-masked material parameter 0 → 1 over 3.2 s, shadow off at the start |
| Buzzard body and flight | `APawn` with a hand-written movement update (3.8.4): the PD pull, the acceleration and speed caps, then one sphere sweep per axis (radius 50 cm; or one swept move with slide) in place of the web's centre rays and push-out. `UFloatingPawnMovement` has neither the pull nor the per-axis stop. Run the three feelers at a fixed rate (for example 20 Hz each), not "one per frame" |
| Buzzard route rules | The El deck plan and the climb-over as written (3.8.3): they are arithmetic on boxes. Give the drone its own collision channel that ignores fences, railings and invisible walls but blocks on the hoist netting and the office glass. Author the shop's doorway portals by hand instead of probing for them |
| Buzzard hit volume | One convex body approximating the 50 × 50 × 22 cm ellipsoid on the shot channel. No weak point |
| Bolts | A pooled manager (32) ticking every bolt: one line trace on the shot channel per step and one segment-to-segment distance test against the player's bolt capsule (`FMath::SegmentDistToSegmentSafe`). `UProjectileMovementComponent` (speed 7000, no gravity, 1.3 s life) works too but is heavier and needs the same custom player test |
| Crash burst and blast damage | A custom radial query: linear falloff to the radius, a line trace from the blast to each target's centre (a Goon is measured at feet + 90 cm), player × 0.5, kill credit to the player. `UGameplayStatics::ApplyRadialDamageWithFalloff` (inner radius 0, falloff exponent 1, a damage-prevention channel) comes close but measures to the nearest point of the component and knows nothing of the last three rules |
| Telegraph cues | Weapon light: a spot or point light on the SMG's light socket plus a flare (Niagara sprite or lens-flare card) whose intensity and size follow 1.5 + 14 k². Buzzard eye: emissive lens + red point light + flare following 3.11. Both must read in full sun (3.11, "flares by day") |
| Tracers, muzzle flashes, bolt streaks, strobes, smoke, sparks, debris, dust | Niagara systems (5.6). Muzzle lights: pooled point lights, 0.05 s |
| Rotors | Rotating prop meshes (`URotatingMovementComponent` or the animation blueprint) swapped or cross-faded to a blur disc at speed; one prop hidden on death |
| Hit flash, self-lit trim, rim light | Per-instance material parameters (custom primitive data): `HitFlash` 0 to 1, `Readability` (emissive trim) and `Rim`, the last two driven by time of day through a material parameter collection |
| Random numbers | One `FRandomStream` (seed 9001) owned by the subsystem for every gameplay draw. The sequence will not match the web's mulberry32; parity is statistical |
| Tuning | A data asset or the exported JSON under `unreal/MurderInc/Content/Data/`, loaded as "base values + per-difficulty overlay" (2.2). Section 2 is the cross-check |

### 4.4 What must stay exact and what may change

Keep exact: every number in 2.2 to 2.6; the mode transitions and timers (3.2); the accumulators and the spread formula
(3.3, 3.5); the token rules (3.6); telegraph lengths and the fact that every ranged attack is announced by light and
sound; burst and volley rhythm; bolt speed and target; the rush timeline; pool sizes, slot rules and body rules.

Free to change: how it looks; how the Goon is animated (clips and IK instead of a solver); the nav representation;
how the Buzzard senses obstacles (sweeps instead of rays), as long as the height rules around the El and the roofs
hold; all per-frame budgets and instancing tricks of the web version (2.6, last rows).

---------------------------------------------------------------------------------------------------

## 5. Art and audio implications

The web models are low-poly stand-ins (1 304 to 1 552 triangles per Goon, 716 for the Buzzard **(measured)**). The
rebuild models the real things they stand for, at the same sizes, with the same silhouettes and colours. One
requirement carries over unchanged (`docs/DESIGN.md:287`): enemies must read at a glance in full sun. A Goon is a
black figure with oxblood accents and a pale mask; a Buzzard is a dark machine with a red eye.

The asset briefs for Blender are in `docs/unreal/spec/assets/characters.json`.

### 5.1 The Goon

Proportions, from the bind pose (`src/enemies/goon-model.js:37` to `:60`; heights above the ground, standing):

| Landmark | Height | Across / length |
|---|---|---|
| Top of the head: hood / beanie / cap | 1.78 / 1.77 / 1.76 m **(measured)** | |
| Centre of the head | 1.62 m | Head 0.20 m wide, 0.24 m tall, 0.22 m deep under the mask |
| Base of the neck | 1.50 m | Neck 0.11 m thick |
| Shoulder joints | 1.42 m | 0.40 m apart; 0.53 to 0.55 m over the sleeves |
| Chest | | 0.42 m wide, 0.25 m deep (puffer: up to 0.47 m × 0.30 m) |
| Waist joint; pelvis joint | 1.05 m; 0.96 m | Pelvis 0.36 m wide, 0.24 m deep |
| Hip joints | 0.93 m | 0.19 m apart |
| Elbows; wrists; fingertips (arms hanging) | 1.14 m; 0.87 m; 0.76 m | Upper arm 0.28 m, forearm 0.27 m, hand 0.105 m |
| Knees; ankles | 0.50 m; 0.085 m | Thigh 0.43 m, shin 0.415 m |
| Feet | | Sneaker 0.29 m long, 0.10 m wide |

That is a lean adult man of about 1.75 m in sneakers; the hood, beanie or cap adds 1 to 4 cm. All three outfits
share the body, the black gloves (`#0d0d0f`), the pale sneakers (upper `#d6d1c4`, sole `#efece4`, an oxblood heel
tab) and the crew mark on the back: an oxblood **V** made of two bars 0.20 m long and 0.03 m wide, each leaning 24°
outward, centred 1.29 m up (`src/enemies/goon-model.js:179`). No skin shows anywhere: mask, gloves, long sleeves,
collar or hood. That is a rule of the fiction ("faces are always covered", no real people: `docs/DESIGN.md:24`).

| Outfit (`variant`) | What he wears | Head | Legs | Source |
|---|---|---|---|---|
| 0 Hoodie | Black pullover hoodie (`#232328`), front pouch pocket (`#0e0e11`), oxblood drawstrings, dark oxblood waistband and cuffs (`#4d0d13`) | Hood up over a pale full-face ski mask (`#dcd5c5`) with two narrow, slanted eye slits (0.046 × 0.017 m) and a mouth seam (`#b5ad9c`); the hood gathers on the shoulders | Dark denim (`#262a36`) | `src/enemies/goon-model.js:168`, `:210` |
| 1 Puffer | Charcoal quilted puffer jacket (`#28282e`): four horizontal quilt rings, an oxblood shoulder yoke and shoulder caps (`#7c151d`), a tall collar, an oxblood zip; arms 16 % thicker; dark oxblood belt line | Black beanie with an oxblood cuff, dark wrap-around glasses, a pale bandana over the lower face coming to a point at the chest; under them the same pale mask fabric, no skin | Charcoal trousers (`#30323b`) | `src/enemies/goon-model.js:151`, `:215` |
| 2 Tracksuit | Black track jacket with a stand-up collar and an oxblood zip; oxblood stripes down the outside of both sleeves | Black fitted cap worn backwards (oxblood brim to the rear) over a pale full-face ski mask tucked into the collar | Black track trousers with oxblood side stripes | `src/enemies/goon-model.js:137`, `:174`, `:194`, `:221` |

Materials to author: cotton fleece, quilted nylon, polyester tricot, rib knit (mask, beanie, cuffs), denim, leather or
synthetic gloves, sneaker leather and rubber. The black cloth is not pure black (`#232328` and `#28282e`): the folds
must read in sunlight. The web version lets the mask, the oxblood trim and the sneakers emit a little of their own
colour at night (3.11); in Unreal expose that as one "readability" scalar and leave it near zero by day.

### 5.2 The SMG and the pipe

The SMG (`src/enemies/goon-model.js:229`), in weapon space: origin where the right hand holds the pistol grip, barrel
toward +X, up +Z. Overall 0.64 m long (0.39 m ahead of the origin, 0.25 m behind), 0.27 m tall with the magazine,
0.046 m wide **(measured)**.

| Part | Size | Where |
|---|---|---|
| Receiver | 0.27 m long, 0.072 m tall, 0.046 m wide | From 0.08 m behind the origin to 0.19 m ahead, its underside at the origin's height |
| Handguard | 0.15 m long, 0.046 m tall, 0.036 m wide | 0.19 to 0.34 m ahead |
| Barrel end / muzzle device | 0.024 m across, 0.06 m long | 0.33 to 0.39 m ahead; bore axis 0.042 m above the origin |
| Pistol grip | 0.10 m long, set at 15° to the receiver | Below the origin |
| Magazine | 0.17 m long, 0.042 m × 0.03 m, a straight box set at 6° | 0.085 m ahead of the grip, reaching 0.18 m below the origin |
| Stock and butt plate | Strut 0.19 m long; plate 0.085 m tall | Ends 0.25 m behind the origin |
| Sight rail | 0.07 m long | On top, 0.09 m above the origin |
| Weapon light | 0.036 m across, 0.075 m long; lens 0.032 m | Under the handguard, lens 0.32 m ahead, on the origin's height |

Sockets (weapon space, cm): `Muzzle` (38.5, 0, 4.2), `Light` (31.8, 0, −0.2), `SupportHand` (17, 0, −1.2), `Butt`
(−23.5, 0, 3) (`src/enemies/goon-model.js:66`). The boxes above are the envelope: model a generic compact
pistol-calibre submachine gun with a fixed stock, a straight stick magazine ahead of the trigger and a weapon light
under the barrel; dark worn steel and polymer (`#24262c`, lighter parts `#34373f`). No maker's marks and no copy of a
specific make (`docs/DESIGN.md:27`). The light's lens is the telegraph: warm white, linear (1, 0.74, 0.42), about
`#ffdfad`. Calibre, magazine capacity and action are not in the code and do not matter to the game: Goons never reload.

The pipe (`src/enemies/goon-model.js:242`): a length of 1 inch galvanised steel pipe, 0.70 m long and 0.034 m across
(`#8f949c`), with a threaded coupling at the striking end (0.05 m across, 0.05 m long) and 0.15 m of black tape
(`#18181a`) for a grip at the other. The fist closes 0.14 m from the grip end; 0.56 m of pipe is ahead of it. It rides
diagonally across his back, grip at the right shoulder blade (0.15 m right of and 0.15 m behind the middle of the
shoulder line, 0.06 m above it), striking end toward the left hip (`src/enemies/goon-anim.js:99`). The web model has
no strap: give it a sling or a loop it can be drawn from over the right shoulder.

### 5.3 The Goon's rig and animation

**Skeleton.** The web rig has 17 rigid bones (`src/enemies/goon-model.js:13`): hips, spine (the whole torso), head,
upper arm / forearm / hand and thigh / shin / foot on each side, plus one bone for the gun and one for the pipe. Use
the UE5 mannequin skeleton so the animations can be retargeted; map hips → `pelvis`, spine → `spine_01` to `spine_05`,
head → `neck_01` and `head`, the gun to a weapon bone or a hand socket, the pipe to a prop bone that switches between
`hand_r` and a socket on the upper spine. Sockets on the character (Unreal mesh space, cm, +Y forward): eye and sight
origin (0, 0, 160), shot origin (0, 0, 146), head centre (0, −0.5, 162), `PipeBack` (−15, −15, 148).

**No clips exist in the web game.** `poseGoon` solves every frame from what the AI wants
(`src/enemies/goon-anim.js:348`). The list below is that solver written out as clips and layers, with the lengths it
produces, so they can be authored or retargeted. Speeds are rules of the game: animation must follow the capsule (no
root motion that changes speed).

The four ways he holds the SMG (`src/enemies/goon-anim.js:65`), grip position relative to the middle of the shoulder
line in the torso's frame:

| Hold | When | Grip (right, up, forward) | Barrel |
|---|---|---|---|
| Low ready | Standing, walking | 10 cm, −27 cm, 21 cm | 43° down, 32° across to his left |
| Port arms | Running | 12 cm, −20 cm, 20 cm | 32° up, 43° to his left |
| Shouldered | Aiming, stalking, sweeping | 12.5 cm, −4 cm, 30.5 cm, in the frame of the aim direction | Along the aim; butt in the right shoulder |
| One-hand carry | The rush (left hand only) | −4 cm, −33 cm, 17 cm | 57° down, 52° to his left |

The animations:

| # | Animation | Kind | Length | What happens |
|---|---|---|---|---|
| 1 | Idle, gun at low ready | Loop | One breath 3.7 s; weight shift 10.3 s | Feet 0.23 m apart, 6 cm staggered. SMG held low in both hands, muzzle down and across to his left (43° down). Breathing moves the hips 3 mm and the spine 0.5°; the hips sway 6 mm |
| 2 | Look around (patrol) | Procedural head look | 11.4 s per sweep | Head yaw ± 52° on a sine. It is also where he sees (3.3), so it must stay a driven look-at, not baked into a clip |
| 3 | Walk (patrol), 1.5 m/s | Loop | 0.89 s per cycle (two steps), stride 1.34 m | Heel-to-toe; a foot is on the ground 62 % of the cycle and lifts 7 cm; pelvis turns ± 9° and rolls ± 2°; gun at low ready |
| 4 | Stalk, 2.0 m/s | Loop | 0.67 s per cycle, stride 1.35 m | Half crouch (hips 12 cm lower than standing), torso 14° forward, gun shouldered and steady (aim offset on top) |
| 5 | Run, 4.5 / 5.0 / 5.4 m/s | Loop | 0.56 / 0.54 / 0.53 s per cycle, stride 2.5 / 2.7 / 2.9 m | A real run: each foot on the ground 36 % of the cycle, lifting 27 cm; torso 16° forward, hips 8 cm lower; SMG at port arms across the chest, muzzle up to his left. Author at 5.0 m/s and scale the play rate ± 10 % |
| 6 | Dash, 9.5 m/s | Loop, at most 0.36 s seen | 0.47 s per cycle | A sprint with the pipe cocked over the right shoulder and the gun carried low in the left hand |
| 7 | Turn on the spot | Stepping | 0.22 cycles per radian turned (at 143 °/s: one step every 0.9 s), feet lift 5 cm | Standing turns at 143 °/s; during a sweep the body follows the gun at 86 °/s |
| 8 | Aim stance | Pose + aim offset | Blends in 0.2 s | Bladed 18° with the left shoulder leading; left foot 17 cm forward, right 15 cm back, 27 cm apart; hips 3.5 cm lower; butt in the right shoulder, head tilted 6° onto the stock. Aim offset: yaw ± 63°, pitch ± 40° |
| 9 | Kneel behind cover | Pose | Down or up in 0.3 s | Right knee on the ground (right foot 0.30 m back, on its toes), left foot 0.20 m forward and flat; hips 0.45 m lower; torso 18° forward; gun lowered in front (aim weight 0.3); head still tracks the player |
| 10 | Telegraph | 0.5 s | 0.5 s | No body motion of its own in the web version: he stands in the aim stance while the weapon light flares. An authored "settle into the stock" is welcome if the light and the muzzle stay on the player for the last 0.2 s |
| 11 | Fire, per round | Additive | Rounds 0.11 s apart; settles 0.27 s after the last | Per round: muzzle climbs 2°, gun 1.5 cm back, shoulders rock 1.4° (a spring: 22.8 rad/s, damping ratio 0.66; the rounds of a burst stack) |
| 12 | Hit reaction | Additive | 0.6 s | A shove along the shot: hips up to 2 cm, spine up to 11° (3 cm and 17° for a head hit), head against it. Scale = min(1.6, damage / 28), × 1.5 on the head (spring: 12.2 rad/s, damping ratio 0.53) |
| 13 | Rush wind-up | One-shot | 0.28 s | 0 to 0.11 s: the right hand leaves the grip and reaches over the right shoulder. 0.11 to 0.28 s: it draws the pipe and cocks it up and back (29° past vertical); hips drop 7 cm, torso coils 26° to the right; the left hand takes the gun down to the left hip |
| 14 | Pipe swing | One-shot | 0.14 s | A diagonal down-stroke: the right hand travels from 30 cm right, 20 cm above and 10 cm behind the middle of the shoulder line to 10 cm left, 22 cm below and 42 cm ahead of it; the pipe goes from 29° back to 109° forward-down; the torso uncoils to 29° left and folds 23° forward |
| 15 | Rush recovery | One-shot | 0.55 s | 0.14 to 0.39 s: the pipe goes back into its sling over the shoulder. 0.40 to 0.55 s: the right hand returns to the grip |
| 16 | Death, onto the back | One-shot, plus its mirror image | 0.9 s (0.70 s fall, 0.20 s settle) | Shot from the front: knees give in the first 0.28 s, then he topples backwards and slides 0.5 m. Ends on his back, one arm flung out, the other across the hip, head rolled 32° to the side |
| 17 | Death, onto the front | One-shot, plus its mirror image | 0.9 s | Shot from behind: pitches forward, slides 0.4 m. Ends face down, one arm thrown up beside the head, head turned 66° |
| 18 | Head look | Procedural | 90 % in 0.33 s | Follows the player or the spot being investigated: yaw ± 80° from the body (± 72° from the chest), pitch ± 34° |

Blend logic for the animation blueprint (`src/enemies/goon-anim.js:350`, `:493`):

- Move weight = smoothstep(0.15, 0.9 m/s) of the real speed, `damp(rate 12)`. Run weight = smoothstep(2.4, 4 m/s),
  `damp(rate 8)`. Crouch weight (0, 0.4 or 1) `damp(rate 8)`. Aim weight (0, 0.3, 0.85 or 1) `damp(rate 11)`. Gun yaw
  and pitch `damp(rate 12)`. Rush hand weight `damp(rate 20)`.
- Upper-body hold weights: one-hand carry = rush weight; shouldered = aim × (1 − rush); port arms = run × (1 − aim) ×
  (1 − rush); low ready = the rest.
- Kneeling only happens standing still: kneel weight = crouch × (1 − move). Moving, the crouch lowers the hips by
  0.22 m × crouch instead of 0.45 m.
- Footfalls: the left foot lands when the cycle wraps, the right at its half; each emits `enemy:step` (while the move
  weight is above 0.5).
- The left hand stays on the handguard at all times (two-bone IK to the `SupportHand` socket); during the rush it
  carries the gun alone while the right hand works the pipe.

### 5.4 The Buzzard

A heavy quadcopter (`src/enemies/buzzard-model.js:48`). Author it **nose toward +X**. Overall 1.02 m long, 1.07 m
across the rotor discs, 0.35 m tall **(measured)**; the motors are 0.89 m apart on the diagonal and the props are
0.37 m (about 15 inches) across.

| Part | Size | Where (x forward, y right, z up from the centre) |
|---|---|---|
| Hull | Flat faceted lozenge 0.56 m long, 0.30 m wide, 0.11 m deep | Centred 2 cm aft |
| Top deck and spine panel | Deck 0.50 m × 0.26 m tapering upward, 0.06 m tall; oxblood spine stripe 0.34 m × 0.07 m | On the hull, top at +0.13 m |
| Beak | Four-sided pointed fairing 0.24 m long, 0.20 m wide at its base, drooping 11° | Nose, tip 0.48 m ahead |
| Brow | Oxblood plate 0.12 m × 0.10 m, tilted 17° | Over the beak |
| Tail boom and V tail | Boom 0.26 m × 0.05 m × 0.04 m; two oxblood fins 0.15 m tall, 0.11 m chord, canted 34° outward | Boom to 0.53 m aft; fins at 0.47 m aft |
| Four arms | Section 0.045 m × 0.03 m, 0.43 m (front) and 0.46 m (rear) from the centre | To the hubs |
| Motor pods | 0.09 m across, 0.085 m tall | Under each hub |
| Rotor hubs | | Front (0.27, ± 0.33, 0.075) m; rear (−0.30, ± 0.35, 0.075) m |
| Props | Two blades, 0.37 m tip to tip, 0.034 m chord | Disc plane 0.097 m above the centre; diagonal pairs turn the same way |
| Skids | Two rails 0.40 m long, 0.26 m apart, on four splayed struts | 0.16 m below the centre |
| Gimbal | Ball housing 0.124 m across on a short neck | Pivot (0.17, 0, −0.085) m, under the nose |
| Eye | Lens 0.072 m across in a 0.09 m ring | (0.255, 0, −0.10) m, looking forward |
| Slung gun | Body 0.20 m × 0.034 m × 0.03 m, barrel 0.02 m across; ammunition box 0.07 m × 0.05 m × 0.045 m | On the gimbal's right side; muzzle at (0.37, 0.062, −0.13) m |
| Strobes | | Port red (0.33, −0.36, 0.02), starboard green (0.33, 0.36, 0.02), tail white (−0.47, 0, 0.09) m |

The positions above use Unreal's axes (in metres): +y is the drone's right. In Blender, with the nose on +X, its right
is −Y, so every y changes sign there: the gun hangs on the −Y side, the red port light sits at +Y.

Colours (`src/enemies/buzzard-model.js:34`): hull `#1c1e24`, lighter panels and arms `#2b2e36`, oxblood panels
`#7c151d`, props and barrel `#30333a`, gun `#17181c`, skids `#22242a`, lens glass `#2a0806`. Finish: satin composite
and anodised metal (the web material is roughness 0.5, metalness 0.45). The eye emits linear (1, 0.09, 0.05), about
`#ff553f`, at the brightness levels of 3.8.5.

Rig: body; four prop bones (or four rotating components); one gimbal bone carrying eye, gun and ammunition box, yaw
± 86°, pitch 77° down to 29° up. Sockets: `Eye`, `GunMuzzle`, the three strobes, the four hubs. Each prop needs a
static two-blade mesh and a blur disc; one prop (any of the four) is hidden when the drone is killed. The gun is a
fiction: something a crew bolted on. Keep it small and generic, with no real make.

Motion to author or drive: the bank into acceleration (up to 29°, 21° at full thrust), the hit shake (up to 29°,
gone in about half a second), the damaged wobble (6° and 7° at 1.2 to 1.4 Hz) with smoke and sparks, the recoil nod
(3.4° per bolt), and the death spin (3.8.9).

### 5.5 Effects

| Effect | Trigger | Dimensions and timing | Source |
|---|---|---|---|
| Weapon-light flare (Goon) | Telegraph and burst | 3.11; must read at 15 m in sunlight | `src/enemies/goon.js:1065` |
| SMG muzzle flash + light | Every round | Flash scale 0.7 of the player's; light `#ff7a3c`, 7 m, 0.05 s, every other round | `src/enemies/goon.js:629` |
| SMG tracer | Every round | Red (`#ff3a22`), muzzle to hit point | `src/enemies/goon.js:628` |
| Goon hit puff | Every hit on a Goon | Dusty cloth puff, `#9a6a64`; never blood (`docs/DESIGN.md:28`) | `src/fx/recipes.js:29` |
| Hit flash | Every hit on either type | Whole model, 0.15 s | `src/enemies/rig.js:165` |
| Body dust | 0.63 s into a Goon's collapse | One dust puff at his feet, scale 0.8 | `src/enemies/goon.js:1035` |
| Body dissolve | A seventh body, or 45 s | Screen-door dither over 3.2 s | `src/enemies/rig.js:153` |
| Eye flare (Buzzard) | Always, by state | 3.11 | `src/enemies/buzzard.js:849` |
| Strobes | Living Buzzards | 3.11 | `src/enemies/buzzard.js:862` |
| Rotor blur | Always | Four discs of radius 0.185 m | `src/enemies/buzzard.js:839` |
| Bolt | Every bolt | Red streak up to 2.4 m × 0.11 m with a 0.34 m hot head, 70 m/s, at most 1.3 s; surface impact where it lands | `src/enemies/bolts.js:144` |
| Bolt muzzle flash + light | Every bolt | Flash scale 0.6; light `#ff3a22`, 6 m, 0.05 s | `src/enemies/buzzard.js:637` |
| Damage smoke and sparks | Buzzard under half hit points | Thin smoke puff (scale 0.45) every 0.1 to 0.22 s; five sparks downward every 0.5 to 1.7 s | `src/enemies/buzzard.js:730` |
| Rotor loss | Buzzard killed | Ten sparks up, four dark debris chips (`#30333a`) at 5 m/s, a smoke puff (scale 0.8), at the hub that came off | `src/enemies/buzzard.js:767` |
| Fall trail | Buzzard falling | Smoke (scale 0.7) every 0.05 s, four sparks every 0.16 s | `src/enemies/buzzard.js:798` |
| Crash burst | Buzzard lands | Small explosion, "drone" flavour: more electric sparks, less fire, no smoke column, a few fragments; drawn at 0.46 of a propane blast's size (radius 3 m against 6.5 m) | `src/enemies/buzzard.js:816`, `src/fx/recipes.js:649`, `docs/CONTRACT.md:553` |
| Drone hit | Every hit on a Buzzard | Grey chips and sparks, surface `drone` | `src/fx/recipes.js:30` |

### 5.6 Audio

Every enemy sound is positional. Source: `src/audio/sfx-enemies.js:239` (the table of sounds), `src/audio/react.js:176`
(the triggers). Lengths are those of the synthesised originals; record or design replacements to the same lengths,
because several are timed to gameplay.

| Sound | Trigger | Length, variants | Notes |
|---|---|---|---|
| Rotor loop | Every living Buzzard, from `enemy:spawn` | 1 s loop, 1 | Four motors a few hertz apart (187 to 209 Hz) under blade wash. Pitch × (0.94 + 0.3 × speed / 10 m/s), each drone detuned 0.96 to 1.06. Only the six nearest within 90 m are heard. Stops 0.12 s after the kill |
| Charge-up | `enemy:telegraph`, Buzzard | 0.5 s, 1 | A rising whine (420 Hz to 2.35 kHz) that ticks faster and ends on a blip. Played at pitch 0.5 / telegraph (0.91 / 1.09 / 1.32) so the blip lands when the first bolt leaves |
| Bolt shot | `enemy:fire`, Buzzard | 0.4 s, 3 | An electric crack with a falling tone |
| Buzzard alert | `enemy:alert`, Buzzard | 0.36 s, 1 | Two quick rising chirps |
| Buzzard death | `enemy:killed`, Buzzard | 1.6 s, 1 | Motors dying, sputtering, sparks; then the small explosion of the crash |
| SMG shot | `enemy:fire`, Goon | 0.55 s, 4 | Lighter than the player's Chopper, with one slap off the far wall |
| Ready cue | `enemy:telegraph`, Goon | 0.5 s, 1 | The gun coming up: sling rustle, then two metallic clicks at 0.30 and 0.375 s |
| Rush | `enemy:melee windup` | 0.6 s, 2 | A growl rising from the chest and the pipe scraping; it runs through the wind-up and the dash |
| Pipe swing | `enemy:melee strike` | 0.32 s, 1 | A whoosh with a faint ring |
| Goon alert | `enemy:alert`, Goon | 0.24 s, 3 | One sharp rising shout with no word in it |
| Hit grunt | `enemy:hit` on a living Goon | 0.15 to 0.2 s, 4 | Wordless, muffled by the mask |
| Death grunt | `enemy:killed`, Goon | 0.42 to 0.56 s, 3 | |
| Body fall | 0.42 s after `enemy:killed`, Goon | 0.5 s, 2 | Body and coat on pavement |
| Footsteps | `enemy:step` | Per surface | The player's footstep set at volume 0.75 and pitch 0.88 |
| Body hit / drone hit | `impact` on an enemy from the player | 3 / 2 | The hit confirmation; pitched up 25 % on a head hit |
| Near miss | `enemy:fire` whose line passes 0.25 to 3.2 m from the listener, unobstructed | | For a bolt, delayed by its flight time (distance / 70 m/s); at once for an SMG round |

Goons never speak words: every voice sound is a wordless grunt, growl or shout behind a mask
(`src/audio/sfx-enemies.js:115`). Every enemy shot ducks the rest of the mix slightly (to 0.85 for about 0.1 s:
`src/audio/react.js:185`).

---------------------------------------------------------------------------------------------------

## 6. Open questions and risks

1. **Stairs and the two perches.** The web nav grid is one flat layer: Goons can never reach the scaffold deck or the
   mezzanine office, and the stand-off logic of 3.7.3 exists because of that. A Recast nav mesh will happily route
   them up both stairs, which turns the level's vantage points into ordinary ground. Decide: keep parity (exclude the
   stairs for the Goon's nav agent) or let them climb and drop the stand-off rule. This spec assumes parity, and so
   does `01-player.md` 4.4.
2. **Contact between bodies.** In the web game enemies and the player never collide; a soft push keeps them apart
   (3.7.4). Unreal capsules block by default. Blocking changes doorways, the rush and crowding. Recommended: Goons
   block the player, ignore each other, and keep the push.
3. **Hit volumes.** The Goon is a head sphere and one fat capsule; arms and gun outside the capsule cannot be hit, and
   everything inside 0.27 m of his axis can. A photoreal model invites per-bone hit bodies, which would change the
   time to kill. Keep the two volumes until the weapon tuning is revisited on purpose.
4. **Shots start on the body axis, not at the muzzle** (1.46 m up), and the eyes stay at 1.6 m while he kneels. With
   a realistic model this can show: a tracer that starts at a muzzle 0.7 m ahead of the real ray, a Goon who "sees"
   over cover he is kneeling behind. Keep the rule (it prevents shots from inside geometry) and check it visually.
5. **The spread is a box, not a cone** (3.5). A cone of the same half-angle is tighter in the corners; hit rates
   would drift a little. Port the box.
6. **Frame-rate dependence.** The Buzzard runs one feeler per frame and the budgets are per frame (2.3). Everything
   else is time based. Pick fixed rates and check against the traces of 3.13.
7. **What a Buzzard may fly through.** It ignores every player-only collider, the Cage's chain-link included
   (`src/enemies/logic.js:432`), so in the web game it can pass through the drawn fence. In a photoreal game that will
   look wrong: give the fence a real blocking volume for the drone channel up to its drawn height, and check the Cage
   fight still works.
8. **Doorways into the shop** were measured in a headless build with stand-in props (two openings in the south wall).
   The full build may find others. Author the portals by hand in Unreal and confirm against the level spec.
9. **Blast kills are always credited to the player** (`src/enemies.js:456`), including a Goon killed by a falling
   Buzzard or by a tank an enemy round set off. Keep (simple, generous) or track the instigator?
10. **Engaged units know where the player is for 4 s after losing sight**: they keep facing, aiming and choosing
    positions around his true position (3.2, 3.7.5). It is what makes them press. Port as is; do not "fix" it without
    retuning.
11. **Readability in sunlight.** The web version leans on emissive trim and oversized additive flares. With physically
    based lighting the half-second weapon-light warning may not read at 15 m at 4 PM. Budget time to tune the flare,
    a real light, and the sound; the warning is a gameplay rule, not decoration.
12. **Animation method.** The solver has no start, stop or turn transitions and snaps the dash to full speed. Authored
    clips will need stride warping or distance matching to follow a capsule that accelerates at 7 m/s² and turns at
    286 °/s without sliding. The clip list in 5.3 is derived, not shipped data.
13. **Random streams.** Exact reproduction of a web run is not possible (different generator). Tests should compare
    distributions and the reference timings, not sequences.
14. **Three outfits, not two.** DESIGN.md names hoodie and puffer; the code also has the tracksuit. The briefs
    include all three.
15. **Dead config and unused hooks** (2.8): `hear()`, `enemy.voice`, `goon.blockedRay`, `goon.cover.snap`,
    `goon.shotTarget`, `goon.crouchHeight`. Per-Goon voice pitch looks intended and was never wired: a cheap win, but
    not parity.
16. **Rotor speed.** 6.5 turns per second is a stylisation so the blades read under the blur disc. A real prop of
    this size turns roughly ten times faster: use a blur disc and motion blur, not the web number.
17. **Player-only walls and Goons.** Those boxes stop a Goon's body (same mover as the player) but are not in the nav
    grid (`src/physics.js:91`), so a web Goon can be routed into one and relies on the stuck rule to give up. In
    Unreal make such blockers part of the nav data.
18. Not found in the code, so not specified here: any difference in behaviour between Story and Hold the Block beyond
    the three multipliers; any reaction of enemies to the El train; any use of the time of day by the AI (it only
    changes materials).

