# 02 — Weapons and combat: the CHOPPER, the NINE, melee, hit resolution, explosives

Port spec for the Unreal Engine 5 rebuild of MURDER INC. The web game is the ground truth. Everything below was read
from the source files listed in 2.1. Values marked **(derived)** are computed from typed constants. Values marked
**(measured)** are not typed anywhere: they were obtained by running the game's own code headless (the rule module
`src/weapon/logic.js`, the model builders, the real level with the real explosives module) or by rendering the
viewmodel with the project's harness, and reading the results back.

How to read this document:

- Web units are metres, seconds and radians. +Y is up, north is −Z, east is +X (`docs/CONTRACT.md:20`). Section 4
  gives the Unreal values (cm, cm/s, degrees).
- **View space** is camera space: +X right, +Y up, −Z forward. The viewmodel rig is a child of the camera
  (`src/weapon/viewmodel.js:57-60`).
- **Gun space** (both guns): the origin sits on the bore axis at the back end of the receiver (CHOPPER) or the back
  face of the slide (NINE). `s` is the distance forward along the bore (web −Z), `x` is to the shooter's right, `y` is
  up (`src/weapon/chopper.js:6-7`, `src/weapon/nine.js:4-5`). Blender weapon space is (X, Y, Z) = (s, −x, y); Unreal
  weapon space is (X, Y, Z) = (s, x, y) × 100 cm.
- **Gun rotations** are pitch / yaw / roll applied in three.js order `YXZ` (yaw first, then pitch, then roll):
  pitch + lifts the muzzle, yaw + turns the muzzle to the shooter's **left**, roll + tips the top of the gun to the
  shooter's **left** (`src/weapon/handling.js:15-21`).
- `damp(x, target, rate, dt)` = `target + (x − target) · e^(−rate · dt)` (`src/core/util.js:25`).
  `moveToward(x, target, step)` is linear and never overshoots (`src/core/util.js:57`). `ease(t)` and
  `smootherstep` are the quintic `t³(6t² − 15t + 10)` on a clamped 0…1 input (`src/weapon/springs.js:46`,
  `src/core/util.js:41`). `lerp(a, b, t)` = `a + (b − a) t`.
- A **spring** `[w, z]` is a second-order system `x'' = −w² (x − target) − 2 z w x'` with angular frequency `w` in
  rad/s and damping ratio `z`, advanced with its exact solution so it is frame-rate independent
  (`src/weapon/springs.js:13-33`). An *impulse* adds to the spring's velocity.
- Random draws that decide gameplay (spread, recoil) come from the seeded stream `G.rng.fork('weapon')`
  (`src/weapon/logic.js:53`); the explosives use `G.rng.fork('explosives')` (`src/explosives.js:42`). Cosmetic
  variation in the viewmodel uses `Math.random()` (`src/weapon/viewmodel.js:649`).
- Neighbouring specs in this folder: `01-player.md` (the camera, how a recoil kick and shake are applied, the sprint
  rule, the aim field of view, bindings), `03-enemies.md` (enemy hit points, what a hit does to an enemy, hearing),
  `07-ui-audio.md` (crosshair, hit markers, ammunition display, sounds). Where this document repeats one of their
  numbers it says so.

---------------------------------------------------------------------------------------------------

## 1. Overview

This subsystem is everything Rule does to the Vultures and everything that blows up. The player carries two guns and
a quick strike. The **CHOPPER** is a compact full-automatic carbine (30 rounds, 720 rounds a minute, 26 damage, a
finite reserve) whose recoil climbs hard for the first nine rounds, starts weaving side to side from the fourth and
then flattens to about a third of the climb; the **NINE**
is a semi-automatic pistol (15 rounds, 34 damage, a reserve that never runs out) that snaps hard per shot and fires
as fast as the player can click up to 420 rounds a minute. Both are hitscan from the eye, one ray per round, with no
damage falloff and no penetration, so the crosshair (or the iron sights, which line up for real when aiming) is where
the round goes, inside a cone that widens with movement, jumping and sustained fire and tightens when aiming or
crouching. A Goon's head takes ×2.2. The **melee** strike (rifle butt or pistol whip) lands 0.16 s after the press
for 60 damage on the nearest enemy within 2.3 m in a 50° cone. **Propane tanks** and **welding racks** are solid
cover that a round turns into a timed bomb: the first hit lights a fuse with a roaring jet of flame, more hits or a
neighbouring blast shorten it, and the blast damages enemies in full and the player at half, falling off linearly
with distance and blocked by walls. Around the rules sits the first-person presentation: a large detailed gun held in
black-gloved hands with a gold watch and a gold chain, animated entirely in code (sway, bob, spring recoil, staged
reloads, strike, holster and draw), plus tracers on every round, muzzle flash, ejected brass, camera kick and gamepad
rumble.

---------------------------------------------------------------------------------------------------

## 2. Facts

### 2.1 Source map

| File | Lines | What it holds |
|---|---|---|
| `src/config/weapons.js` | 210 | All tuning: `chopper`, `nine`, `melee`, `common` (shared rules, viewmodel light) |
| `src/weapon.js` | 48 | The module: glues rules and viewmodel, applies the `view` setting, exposes `inspect` (a test hook) |
| `src/weapon/logic.js` | 661 | The rules: ammo, trigger, spread, recoil, aim, reload, switching, melee, public state. Runs without a renderer |
| `src/weapon/viewmodel.js` | 830 | What the player sees: pose layers, springs, muzzle flash, viewmodel lights, the dropped gun |
| `src/weapon/chopper.js` | 331 | The CHOPPER mesh (every part with dimensions), its poses, hand positions and reload choreography |
| `src/weapon/nine.js` | 266 | The NINE mesh, poses, hand positions and reload choreography |
| `src/weapon/arms.js` | 777 | Rule's forearms, gloves, watch, bracelet; bones, CPU skinning, finger poses |
| `src/weapon/handling.js` | 112 | Gun poses, hand keys, track sampling, the 13 named finger poses |
| `src/weapon/springs.js` | 64 | The exact spring step, `ease`, `easeOutBack`, `softLimit` |
| `src/weapon/build.js` | 402 | Modelling kit (prism, loft, lathe, sweep), vertex paint, baked ambient shading |
| `src/weapon/material.js` | 270 | The viewmodel surface shader (procedural finishes), its reflection boxes, the muzzle-flash shader |
| `src/combat.js` | 377 | `G.combat`: hitscan, melee, explosion resolution, run statistics |
| `src/explosives.js` | 504 | `G.explosives`: propane tanks and welding racks (hit points, fuse, chain, reset, drawing) |
| `src/stubs/weapon.js`, `src/stubs/explosives.js` | 204, 206 | Simplified stand-ins with the same API. Not to be ported: see 3.19 |

Related code this subsystem leans on: `src/player.js` and `src/config/player.js` (how a kick reaches the camera, aim
field of view, sprint rule), `src/physics.js` (the ray world), `src/enemies.js` (enemy hit shapes), `src/fx.js` and
`src/fx/*` (tracers, brass, flashes), `src/props/gameplay.js` (the explosive props), `src/level/data.js` (where the
explosives stand), `src/game.js` and `src/config/flow.js` (reset and resupply), `src/audio/react.js` (sounds).

### 2.2 The two guns (gameplay numbers)

| Property | CHOPPER | NINE | Source |
|---|---|---|---|
| id / HUD name / slot | `chopper` / `CHOPPER` / 1 | `nine` / `NINE` / 2 | `src/config/weapons.js:5-7`, `src/config/weapons.js:87-89` |
| Fire mode | full-automatic only | semi-automatic only (one round per press) | `src/config/weapons.js:8`, `src/config/weapons.js:90` |
| Damage per round | 26 | 34 | `src/config/weapons.js:9`, `src/config/weapons.js:91` |
| Head multiplier (Goon head only) | × 2.2 = 57.2 | × 2.2 = 74.8 | `src/config/weapons.js:173`, `src/combat.js:192` |
| Damage falloff, penetration, pellets | none, none, one ray per round | same | `src/config/weapons.js:1` |
| Rate of fire | 720 rpm, interval 0.08333 s | cap 420 rpm, minimum interval 0.14286 s | `src/config/weapons.js:10`, `src/config/weapons.js:92` |
| Magazine | 30 | 15 | `src/config/weapons.js:11`, `src/config/weapons.js:93` |
| Reserve at the start of a run | 150 | infinite | `src/config/weapons.js:12`, `src/config/weapons.js:94` |
| Range | 300 m | 120 m | `src/config/weapons.js:13`, `src/config/weapons.js:95` |
| Aim time (linear ramp 0 → 1, then eased) | 0.18 s | 0.14 s | `src/config/weapons.js:14`, `src/config/weapons.js:96` |
| Buffered fire press | none (a held trigger is read every frame) | 0.13 s | `src/config/weapons.js:97`, `src/weapon/logic.js:536` |
| Cooldown after a dry click | none | 0.12 s | `src/config/weapons.js:98`, `src/weapon/logic.js:505` |
| Dry pull schedules a reload after | 0.32 s | 0.28 s | `src/config/weapons.js:15`, `src/config/weapons.js:99` |
| Reload, magazine not empty ("tactical") | 2.24 s | 1.50 s | `src/config/weapons.js:18`, `src/config/weapons.js:101` |
| Reload, magazine empty | 2.72 s | 1.90 s | `src/config/weapons.js:19`, `src/config/weapons.js:102` |
| Rounds move into the gun at | 1.44 s | 1.13 s | `src/config/weapons.js:23`, `src/config/weapons.js:106` |
| HUD "low" cue when magazine ≤ | 9 (= ceil(30 × 0.27)) | 5 (= ceil(15 × 0.27)) | `src/config/weapons.js:195`, `src/weapon/logic.js:171` |
| Camera shake added per round (trauma) | 0.12 | 0.14 | `src/config/weapons.js:51`, `src/config/weapons.js:125` |
| Gamepad rumble per round (strong, weak, ms) | 0.18, 0.5, 55 | 0.35, 0.6, 55 | `src/config/weapons.js:73`, `src/config/weapons.js:146` |
| World muzzle light (colour, intensity, range, life) | `#ffb020`, 45, 9 m, 0.05 s | `#ffb020`, 30, 9 m, 0.05 s | `src/config/weapons.js:72`, `src/config/weapons.js:145` |
| Muzzle flash scale handed to fx | 1.0 | 0.55 | `src/config/weapons.js:72`, `src/config/weapons.js:145` |
| Ejected casing kind | `rifle` | `pistol` | `src/weapon/logic.js:475` |
| Barrel smoke after long bursts | yes | no | `src/config/weapons.js:76`, `src/config/weapons.js:148` |
| Wall pull-back starts / is full at | 1.05 m / 0.42 m | 0.80 m / 0.32 m | `src/config/weapons.js:74`, `src/config/weapons.js:147` |

Derived from the above (not typed in the code):

| | CHOPPER | NINE |
|---|---|---|
| Time to empty a full magazine | 29 × 0.08333 = 2.417 s **(measured: 2.4167 s)** | 14 × 0.14286 = 2.000 s at the cap |
| Body damage per second while firing | 312 | 238 at the cap |
| Rounds at the start of a run | 30 + 150 | 15 + infinite |
| Rounds to kill a Goon (90 / 110 / 130 HP on Hustler / Boss / Kingpin), body | 4 / 5 / 5 | 3 / 4 / 4 |
| Rounds to kill a Goon, head | 2 / 2 / 3 | 2 / 2 / 2 |
| Rounds to kill a Buzzard (45 / 55 / 60 HP, no weak point) | 2 / 3 / 3 | 2 / 2 / 2 |
| Melee strikes (60) to kill a Goon / a Buzzard | 2 / 2 / 3 and 1 / 1 / 1 | same |

Enemy hit points are per difficulty (`src/config/enemies.js:244-255`) and are scaled up to × 2.5 in Hold the Block
(`src/config/flow.js:153`); see spec 03.

### 2.3 Reload timelines

Seconds from the reload's start. The marks in bold are gameplay events (the `magout`, `magin`, `bolt` and `done`
phases of `weapon:reload`); the others only drive the animation (`src/weapon/logic.js:61-75`).

| Mark | CHOPPER | NINE | Meaning | Source |
|---|---|---|---|---|
| **`magOut`** | 0.40 | 0.18 | magazine released (event `magout`) | `src/config/weapons.js:20`, `src/config/weapons.js:103` |
| `magShow` | 0.80 | 0.48 | a fresh magazine is in the left hand and visible | `src/config/weapons.js:21`, `src/config/weapons.js:104` |
| `magInsert` | 1.15 | 0.90 | the fresh magazine touches the gun | `src/config/weapons.js:22`, `src/config/weapons.js:105` |
| **`magIn`** | 1.44 | 1.13 | magazine seated: **ammunition is transferred here** (event `magin`) | `src/config/weapons.js:23`, `src/config/weapons.js:106` |
| `tug` | 1.565 | — | the left hand tugs the seated magazine | `src/config/weapons.js:24` |
| **`bolt`**, tactical | 1.89 (`pressCheck[0]`; the check ends at 1.93) | no bolt event | press check of the charging handle | `src/config/weapons.js:25`, `src/weapon/logic.js:69` |
| **`bolt`**, empty | 1.96 (`boltBack`) | 1.61 (`slideRelease`) | charging handle racked / slide released | `src/config/weapons.js:26`, `src/config/weapons.js:107` |
| `boltRelease`, empty | 2.155 | — | the racked handle is let go | `src/config/weapons.js:27` |
| **`done`**, tactical | 2.24 | 1.50 | reload over, the gun can fire | `src/config/weapons.js:18`, `src/config/weapons.js:101` |
| **`done`**, empty | 2.72 | 1.90 | reload over, the gun can fire | `src/config/weapons.js:19`, `src/config/weapons.js:102` |

### 2.4 Spread (cone half-angles)

| Term | CHOPPER rad (deg) | NINE rad (deg) | Source |
|---|---|---|---|
| `hip` base, standing still | 0.0125 (0.716°) | 0.0105 (0.602°) | `src/config/weapons.js:30`, `src/config/weapons.js:110` |
| `ads` base, fully aimed | 0.0012 (0.069°) | 0.0017 (0.097°) | `src/config/weapons.js:31`, `src/config/weapons.js:111` |
| `moveHip` added at full movement | 0.013 (0.745°) | 0.0065 (0.372°) | `src/config/weapons.js:32`, `src/config/weapons.js:112` |
| `moveAds` added at full movement, aimed | 0.004 (0.229°) | 0.003 (0.172°) | `src/config/weapons.js:33`, `src/config/weapons.js:113` |
| `bloomHip` added at bloom 1 | 0.0065 (0.372°) | 0.0085 (0.487°) | `src/config/weapons.js:34`, `src/config/weapons.js:114` |
| `bloomAds` added at bloom 1, aimed | 0.0022 (0.126°) | 0.003 (0.172°) | `src/config/weapons.js:35`, `src/config/weapons.js:115` |
| `air` added while airborne (not reduced by aiming) | 0.022 (1.261°) | 0.018 (1.031°) | `src/config/weapons.js:36`, `src/config/weapons.js:116` |
| `crouch` subtracted while crouching, × (1 − aim) | 0.002 (0.115°) | 0.002 (0.115°) | `src/config/weapons.js:37`, `src/config/weapons.js:117` |
| `shot`: bloom added per round (bloom is 0…1) | 0.17 | 0.30 | `src/config/weapons.js:38`, `src/config/weapons.js:118` |
| `decay`: bloom lost per second | 1.5 | 2.8 | `src/config/weapons.js:39`, `src/config/weapons.js:119` |
| Bloom starts to drain this long after a round | 0.15 s | 0.15 s | `src/config/weapons.js:179` |
| Player speed that gives the full movement term | 6 m/s | 6 m/s | `src/config/weapons.js:180` |
| Approach rate of the cone actually used (`damp`) | 18 per s | 18 per s | `src/config/weapons.js:178` |

A cone of 0.0125 rad is a disc of radius 12.5 cm at 10 m and 37.5 cm at 30 m.

### 2.5 Recoil into the camera

Per round, before scaling (`src/weapon/logic.js:481-496`):

| Term | CHOPPER | NINE | Source |
|---|---|---|---|
| Pitch kick (up) | 0.0068 rad (0.390°) | 0.0092 rad (0.527°) | `src/config/weapons.js:42`, `src/config/weapons.js:122` |
| Random factor on the pitch kick | uniform 0.85…1.15 | uniform 0.90…1.10 | `src/config/weapons.js:43`, `src/config/weapons.js:123` |
| Late-burst flattening | from round 10 of a burst the pitch kick × 0.38 | — | `src/config/weapons.js:44-45` |
| Yaw, rounds 1–3 of a burst | uniform ± 0.0011 rad (0.063°) | uniform ± 0.0025 rad (0.143°) on every round | `src/config/weapons.js:46`, `src/config/weapons.js:124` |
| Yaw, from round 4 | `sin(n · 0.57 + phase) · 0.0042` ± 0.001 rad (weave amplitude 0.241°) | — | `src/config/weapons.js:47-50` |
| Weave period | 2π / 0.57 = 11.0 rounds = 0.92 s **(derived)**; `phase` is re-rolled for every burst | — | `src/weapon/logic.js:616-619` |
| Burst counter clears after | 0.24 s without a round | 0.24 s | `src/config/weapons.js:176` |
| Scale while fully aimed | × 0.55 (blended by the aim amount) | × 0.55 | `src/config/weapons.js:181` |
| Scale while crouching | × 0.85 | × 0.85 | `src/config/weapons.js:182` |

How the player module applies a kick (owned by the player spec; repeated here because the weapon's feel depends on it):

| Constant | Value | Source |
|---|---|---|
| Share of a kick that stays in the aim for good | 35 % | `src/config/player.js:124`, `src/player.js:380-388` |
| Share that becomes a recoverable view offset | 65 % | `src/player.js:86-88` |
| Clamp of the recoverable offset | ± 0.30 rad pitch, ± 0.20 rad yaw | `src/config/player.js:125-126` |
| The view chases the offset target with `damp` rate | 34 per s | `src/config/player.js:127` |
| Hold after the last round before recentring | 0.09 s | `src/config/player.js:128` |
| Recentring: exponential decay of the offset target | 6.5 per s | `src/config/player.js:129` |
| Shake: trauma decay; camera moves by trauma² | 1.7 per s | `src/config/player.js:133` |

**(measured)** A full 30-round CHOPPER burst from the hip, standing, averaged over 200 seeds: total pitch 0.1155 rad
(6.62°), of which 35 % (0.0404 rad, 2.3°) stays in the aim; the summed yaw wanders at most about 0.65° to either
side. In the run with the default seed the kicks summed to 6.41°, the view peaked 6.40° above where the burst
started about 0.08 s after the last round, and settled 2.24° above it. Aimed, every figure is × 0.55.

### 2.6 Rules shared by both guns (`common`)

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `order` | `chopper`, `nine` | slot order; the run starts on the CHOPPER | `src/config/weapons.js:172` |
| `headMultiplier` | 2.2 | passed to every player hitscan | `src/config/weapons.js:173` |
| `holster` | 0.28 s | putting a gun away | `src/config/weapons.js:174` |
| `draw` | 0.32 s | bringing the other gun up | `src/config/weapons.js:175` |
| `burstReset` | 0.24 s | time without a round before the burst counter clears | `src/config/weapons.js:176` |
| `maxCatchUpShots` | 3 | most rounds the CHOPPER may fire in one frame | `src/config/weapons.js:177` |
| `spreadRate` | 18 per s | `damp` rate of `weapon.spread` | `src/config/weapons.js:178` |
| `bloomHold` | 0.15 s | bloom does not drain until this long after a round | `src/config/weapons.js:179` |
| `spreadSpeedRef` | 6 m/s | full movement penalty at this speed | `src/config/weapons.js:180` |
| `adsRecoilScale`, `crouchRecoilScale` | 0.55, 0.85 | camera recoil multipliers | `src/config/weapons.js:181-182` |
| `sprintRate` | 17 rad/s | critically damped spring of the sprint-lowered blend | `src/config/weapons.js:183` |
| `sprintHurry` | × 1.5 | that rate while the player wants the gun | `src/config/weapons.js:184` |
| `sprintFireGate` | 0.45 | the blend must be below this to fire | `src/config/weapons.js:185` |
| `sprintAdsGate` | 0.35 | the blend must be below this to aim | `src/config/weapons.js:186` |
| `firingHold` | 0.14 s | `weapon.state` reads `firing` this long after a round | `src/config/weapons.js:187` |
| `wallEvery`, `wallRate`, `wallAdsScale` | 0.08 s, 12 per s, 0.15 | wall probe interval, blend rate, share kept when aimed | `src/config/weapons.js:188-190` |
| `heat` | + 0.05 per round, max 1.3, − 0.2 per s | drives the barrel smoke only | `src/config/weapons.js:191` |
| `tracer` | colour `#ffe2a8`, 260 m/s | every player tracer | `src/config/weapons.js:193` |
| `lowAmmoFraction` | 0.27 | HUD "low" cue | `src/config/weapons.js:195` |
| `flashSeconds` | 0.036…0.056 s | life of the first-person muzzle flash | `src/config/weapons.js:196` |
| `adsFlashScale` | 0.62 | flash size at full aim | `src/config/weapons.js:197` |
| `explosiveHitFromEnemy` | 9 | damage of any enemy round or bolt to an explosive | `src/config/weapons.js:198` |
| `CREDIT` | 0.001 s | most time an idle gun may bank toward its next round | `src/weapon/logic.js:17` |
| `SHORT_TRACER` | 0.9 m | no tracer when the hit is closer than this | `src/weapon/logic.js:18` |
| Gamepad aim slow-down | × 0.55 look rate, range 60 m, checked every 0.05 s, `damp` rate 14 | pad only | `src/config/player.js:192-195`, `src/weapon/logic.js:46-51` |

### 2.7 Melee

| Constant | Value | Source |
|---|---|---|
| Whole strike | 0.55 s | `src/config/weapons.js:159` |
| The blow lands at | 0.16 s | `src/config/weapons.js:160` |
| Reach (measured to the surface of the enemy's body) | 2.3 m | `src/config/weapons.js:161`, `src/combat.js:259-260` |
| Cone, full apex angle (measured to the nearest edge of the body) | 50° (0.8727 rad), so 25° to either side | `src/config/weapons.js:162`, `src/combat.js:263-264` |
| Damage | 60, always `body`, no head multiplier | `src/config/weapons.js:163`, `src/combat.js:296` |
| Time between the starts of two strikes | 0.75 s | `src/config/weapons.js:164` |
| Cancels a reload | yes | `src/config/weapons.js:165` |
| Blocked while switching guns | yes | `src/config/weapons.js:166` |
| Camera shake when the blow lands | 0.22 on an enemy, 0.11 on a wall, none in thin air | `src/config/weapons.js:167`, `src/weapon/logic.js:407` |
| Rumble on an enemy | strong 0.6, weak 0.4, 90 ms | `src/weapon/logic.js:410` |
| HUD names | "Rifle butt" (CHOPPER), "Pistol whip" (NINE) | `src/config/text.js:68` |

### 2.8 Hit resolution constants

| Constant | Value | Source |
|---|---|---|
| Ray origin of a player round | the eye (camera position), never the muzzle | `src/weapon/logic.js:458-467` |
| What a ray hits in the world | every collision box except `playerOnly` ones, and the ground plane y = 0 | `src/physics.js:305-339`, `src/physics.js:287-294` |
| Boxes a ray ignores | `playerOnly` boxes (invisible walls, shoot-through glass, the Cage's chain-link, railings) and any box that contains the ray's origin | `src/physics.js:8-9`, `src/physics.js:324`, `docs/DEV.md:132` |
| Goon head | sphere, radius 0.155 m, centred 1.62 m above the feet in the rest pose and following the animated head | `src/config/enemies.js:111`, `src/enemies.js:373-374` |
| Goon body | capsule, radius 0.27 m, shin to shoulder, following the animated body | `src/config/enemies.js:112`, `src/enemies.js:383-385` |
| Buzzard | one ellipsoid, horizontal radius 0.5 m, half height 0.22 m, no weak point | `src/config/enemies.js:28-29`, `src/enemies.js:361-362` |
| Player, as a target of enemy rounds | upright cylinder, radius 0.38 m, height 1.8 m standing or 1.15 m crouching | `src/combat.js:21-23` |
| Tie distance in favour of an explosive over its own collider | 0.03 m | `src/combat.js:27` |
| Impact surface names | `asphalt concrete metal wood rubber glass dirt brick car cloth`, plus `flesh` (a Goon) and `drone` (a Buzzard) | `docs/CONTRACT.md:166-167`, `src/combat.js:70` |
| Tracer: colour, speed | `#ffe2a8` (warm white-gold), 260 m/s | `src/config/weapons.js:193`, `src/config/look.js:120` |
| Tracer: streak length | speed × 0.022 clamped to 2…7 m = 5.72 m **(derived)** | `src/fx/tracers.js:12-14` |
| Tracer: width, brightness | 0.035 m, colour × 8 (HDR), × 2.2 to 2.4 hotter by day | `src/fx.js:43-44`, `docs/CONTRACT.md:565` |
| Tracer: not drawn when | hit closer than 0.9 m (weapon) or path shorter than 0.5 m (fx) | `src/weapon/logic.js:473`, `src/fx.js:366` |
| Tracer: first stretch hidden | 1.1 m, when the path is longer than 3.3 m | `src/fx.js:42`, `src/fx.js:371` |
| Tracer pool | 48 | `src/fx.js:32` |
| Casing pool; drawn sizes (length, radius) | 60; rifle 0.058 m × 0.0085 m, pistol 0.027 m × 0.0085 m ("a third larger than life") | `src/fx.js:34`, `src/fx/bits.js:116-117` |
| Casing ejection velocity, camera space | right 2.0…3.2 m/s, up 1.2…2.0 m/s, along the view ± 0.5 m/s, plus the player's velocity | `src/weapon/viewmodel.js:757-763` |
| Casing physics | gravity 9.81 m/s², restitution 0.32…0.48, keeps 60 % of its horizontal speed per bounce, at most 4 bounces | `src/fx/bits.js:12-14`, `src/fx/bits.js:204-206` |
| Enemies hear gunfire | within 45 m of the muzzle, at most once every 0.3 s | `src/config/enemies.js:227`, `src/config/enemies.js:234`, `src/enemies.js:485-489` |

### 2.9 Explosives

| | Propane tank (`propane`) | Welding rack (`rack`) | Source |
|---|---|---|---|
| Hit points | 50 | 70 | `src/explosives.js:20-21` |
| Fuse lit by the first round | 1.6 s | 1.1 s | `src/explosives.js:20-21` |
| Blast radius | 6.5 m | 7.5 m | `src/explosives.js:20-21` |
| Blast damage at the centre | 170 | 210 | `src/explosives.js:20-21` |
| Damage to the player at the centre (× 0.5) | 85 | 105 | `src/explosives.js:25` |
| Chain "size" | 1.9 | 2.3 | `src/explosives.js:20-21` |
| Chain range = 2.2 + 1.6 × size | 5.24 m | 5.88 m | `src/explosives.js:33` |
| Jet-of-flame emitter scale | 0.9 | 1.2 | `src/explosives.js:20-21` |
| Collider (length × height × width; the footprint turns with the prop and is boxed axis-aligned) | 0.32 × 0.6 × 0.32 m | 0.9 × 1.6 × 0.5 m | `src/config/catalog.js:142-143`, `src/explosives.js:176-199` |
| Blast centre | the foot + half the collider height: 0.30 m up | 0.80 m up | `src/explosives.js:414` |
| Announced size (radius ≥ 5 m is `big`) | `big` | `big` | `src/combat.js:28`, `src/combat.js:326` |
| Player rounds that take its hit points to zero (it then pops 0.06 s later): CHOPPER / NINE | 2 / 2 | 3 / 3 | **(derived)**, `test/fx-explosives.test.js:191` |
| Enemy rounds or bolts (9 each) that take its hit points to zero | 6 | 8 | **(derived)** |
| Placed on the block | 14 | 7 | `src/level/data.js:119-141` |

| Rule constant | Value | Source |
|---|---|---|
| Fuse once the hit points reach 0 | 0.06 s | `src/explosives.js:24` |
| Player share of blast damage | 0.5 | `src/explosives.js:25` |
| Damage of an enemy round or a Buzzard bolt to an explosive | 9, whatever the round does to a person | `src/explosives.js:26`, `src/explosives.js:368-371`, `src/enemies/bolts.js:113-117` |
| Fuse of an explosive caught by another blast | 0.14 + [0, 0.3) + 0.03 × distance s | `src/explosives.js:36` |
| "Size" of a blast that is not one of these props | 0.47 + 0.244 × radius, clamped 0.6…2.6 (a Buzzard's 3 m burst: 1.20, chain range 4.12 m) | `src/explosives.js:39` |
| Camera shake of a prop blast | 0.15 + 0.9 g², g = 1 − distance / 28 m (none beyond 28 m) | `src/explosives.js:27`, `src/explosives.js:419-423` |
| Enemies alerted by a prop blast | everyone within 60 m | `src/explosives.js:28`, `src/explosives.js:424` |
| Rattle of a lit prop | ± 0.035 rad × (0.3 + 0.7 × build) about two axes at 71 and 83 rad/s | `src/explosives.js:29`, `src/explosives.js:440-444` |
| Hiss loop volume while lit | 0.25 + 0.75 × build², build = 1 − fuse left / fuse lit | `src/explosives.js:30`, `src/explosives.js:440-441` |
| Jet emitter life | fuse + 0.15 s | `src/explosives.js:346` |
| Restored in Hold the Block | after every even wave cleared (2, 4, 6 …): every explosive, whatever its state | `src/config/flow.js:167`, `src/game.js:701` |
| Restored in every mode | at every run reset | `src/game.js:224` |

### 2.10 Where the explosives stand **(measured: real level built headless)**

Positions are the foot of the prop. Web yaw is about +Y, counter-clockwise seen from above; Unreal yaw = −web yaw.
Unreal (X, Y, Z) = (x, z, y) × 100. Source of every row: `src/level/data.js:120-140`; heights come from the level's
floor (`src/level.js:143`): 0.15 m on a kerbed sidewalk, 2.95 m on the scaffold deck.

| # | Type | Web x, y, z (m) | Web yaw (rad) | Unreal X, Y, Z (cm) | Unreal yaw | Where |
|---|---|---|---|---|---|---|
| 1 | propane | −4.20, 0.15, −7.85 | 0 | −420, −785, 15 | 0° | the food cart |
| 2 | propane | −4.20, 0.15, −8.70 | 0 | −420, −870, 15 | 0° | the food cart |
| 3 | rack | −22.60, 0.15, −10.62 | 0 | −2260, −1062, 15 | 0° | outside the shop, beside the tyre cage |
| 4 | rack | −20.40, 0, −13.60 | π/2 | −2040, −1360, 0 | −90° | the welding corner inside the shop |
| 5 | rack | 3.40, 0, −17.60 | π/2 | 340, −1760, 0 | −90° | by the east lift |
| 6 | rack | −14.30, 0, −23.40 | 0.3 | −1430, −2340, 0 | −17.2° | the foot of the mezzanine stair |
| 7 | propane | −3.40, 0, −30.10 | 0 | −340, −3010, 0 | 0° | the north bench |
| 8 | rack | 6.55, 0, −19.60 | π/2 | 655, −1960, 0 | −90° | the alley, beside the shop's side door |
| 9 | propane | 0.35, 0.15, 7.80 | 0 | 35, 780, 15 | 0° | the foot of the scaffold shed |
| 10 | propane | 9.30, 2.95, 10.35 | 0 | 930, 1035, 295 | 0° | on the shed deck (the vantage) |
| 11 | propane | 17.60, 0.15, 10.45 | 0 | 1760, 1045, 15 | 0° | the east end of the shed |
| 12 | propane | 25.90, 0, 12.90 | 0 | 2590, 1290, 0 | 0° | the lot booth |
| 13 | propane | 28.80, 0, 13.70 | 0 | 2880, 1370, 0 | 0° | the lot booth |
| 14 | propane | −12.90, 0, 16.30 | 0 | −1290, 1630, 0 | 0° | the vacant lot, by the burned car |
| 15 | rack | 5.90, 0, 30.55 | 0 | 590, 3055, 0 | 0° | the rear lane, between two garage doors |
| 16 | propane | 18.30, 0, 26.50 | 0 | 1830, 2650, 0 | 0° | the rear lane, east end |
| 17 | propane | 43.30, 0, −30.50 | 0 | 4330, −3050, 0 | 0° | the Cage, by the bleachers |
| 18 | rack | 32.60, 0, 33.55 | 0 | 3260, 3355, 0 | 0° | the lot's south wall, short of the truck |
| 19 | propane | 39.60, 0, 20.90 | 0 | 3960, 2090, 0 | 0° | the lot's east aisle |
| 20 | propane | 39.80, 0, −6.40 | 0 | 3980, −640, 0 | 0° | the roadblock |
| 21 | propane | 8.90, 0, −1.50 | 0 | 890, −150, 0 | 0° | the avenue, at the barrier chicane |

Layout rule checked by `test/level-layout.test.js`: none within 7 m of the start or 2.2 m of a reel
(`src/level/data.js:115-118`). Pairs inside each other's chain range **(measured)**: 1 ↔ 2 (0.85 m, clear line),
3 ↔ 4 (3.71 m, the shop's wall between them), 5 ↔ 8 (3.73 m, a shelf rack and the shop's wall between them),
12 ↔ 13 (3.01 m, the lot booth between them). All four pairs ripple, because the chain rule needs no line of
sight (3.14); only in the first pair does one blast also reach the other with its damage test. Every other
explosive goes off alone.

### 2.11 Events this subsystem emits

| Event | Payload | When | Source |
|---|---|---|---|
| `weapon:fire` | `{weapon, pos, dir, ads}`; `pos` is the muzzle in world space, `dir` the round's direction, `ads` the aim amount | once per round | `src/weapon/logic.js:479` |
| `weapon:dry` | `{weapon}` | a trigger pull on an empty magazine | `src/weapon/logic.js:507` |
| `weapon:reload` | `{weapon, phase, empty}`; phase is `start`, `magout`, `magin`, `bolt`, `done` or `cancel` | at the marks of 2.3 | `src/weapon/logic.js:284-287` |
| `weapon:switch` | `{from, to, phase}`; phase is `holster` or `draw` | at the start of each phase, and on a reversal | `src/weapon/logic.js:330-333` |
| `weapon:swing` | `{weapon}` | a strike starts | `src/weapon/logic.js:390` |
| `weapon:melee` | `{hit}` (true when an enemy was struck) | the blow lands, 0.16 s in | `src/weapon/logic.js:408` |
| `impact` | `{point, normal, surface, dir, from, enemy}`; `from` is `player` or `enemy` | every round or strike that lands on the world, an enemy or an explosive. Not when the player is hit, not for a melee miss on a wall | `src/combat.js:204`, `src/combat.js:217`, `src/combat.js:227`, `src/combat.js:300` |
| `player:hitEnemy` | `{enemy, part, killed, damage, weapon}`; `weapon` is `chopper`, `nine` or `melee` | a player round or strike lands on an enemy (drives hit markers, hit sounds, accuracy) | `src/combat.js:205`, `src/combat.js:301` |
| `explosion` | `{pos, radius, size, source}`; size is `small` or `big` | every blast, **before** its damage is applied | `src/combat.js:323-328` |
| `explosive:lit` | `{item, pos, fuse}` | a fuse is lit (by a round or by a neighbouring blast) | `src/explosives.js:355` |
| `explosive:blast` | `{item, pos}`; `pos` is the blast centre | the prop goes, just before `explosion` | `src/explosives.js:416` |
| `shell:bounce` | `{pos, surface}` | a casing touches the ground (emitted by fx) | `src/fx.js:303-305` |

### 2.12 Public interface

| Member | Meaning | Source |
|---|---|---|
| `weapon.current`, `weapon.def` | id of the gun in hand and its config row | `src/weapon/logic.js:185-186` |
| `weapon.state` | `idle`, `firing`, `reloading`, `switching`, `melee` or `lowered` (3.2) | `src/weapon/logic.js:174-181` |
| `weapon.mag`, `weapon.reserve`, `weapon.magSize` | of the gun in hand; reserve is `Infinity` for the NINE | `src/weapon/logic.js:187-189` |
| `weapon.other` | `{id, name, mag, reserve}` of the gun not in hand (HUD) | `src/weapon/logic.js:192-196` |
| `weapon.spread` | the cone half-angle in use, radians (HUD crosshair gap) | `src/weapon/logic.js:651` |
| `weapon.cue` | empty, `reloading`, `low`, `reload` (magazine empty, reserve left) or `empty` (nothing left) | `src/weapon/logic.js:166-172` |
| `weapon.reset()` | full magazines, 150 reserve, CHOPPER in hand, every timer cleared | `src/weapon/logic.js:236-256` |
| `weapon.addReserve(n, cap)` | adds to every finite reserve (the CHOPPER) up to `cap` | `src/weapon/logic.js:259-266` |
| `weapon.drop()` | the gun leaves Rule's hands (death) | `src/weapon/logic.js:269-278` |
| `weapon.setVisible(on)`, `weapon.setView(1, 2 or 3)` | show the viewmodel; choose one of three hip poses | `src/weapon.js:29-34`, `src/weapon/viewmodel.js:764-772` |
| `weapon.update(dt)` | one step of the rules, then of the viewmodel | `src/weapon.js:25-28` |
| `combat.hitscan({origin, dir, range, damage, from, weapon, headMult})` | one instant round; returns `{type, point, normal, dist, surface, enemy, part, killed, box, item}` with type `none`, `world`, `enemy`, `explosive` or `player` | `src/combat.js:150-230` |
| `combat.melee({origin, dir, reach, cone, damage})` | one strike; same result shape | `src/combat.js:246-303` |
| `combat.explode({pos, radius, damage, playerScale, source, size})` | one blast | `src/combat.js:321-374` |
| `combat.stats` | `{shots, hits, kills, headshots, damageTaken}` for the run | `src/combat.js:34` |
| `explosives.items` | `[{type, pos, hp, state, box}]`, state `idle`, `lit` or `gone` | `src/explosives.js:179-203` |
| `explosives.reset()`, `.raycast(origin, dir, maxDist)`, `.damage(item, amount, from)`, `.update(dt)` | restore all; nearest live item on a ray; apply a hit; run the fuses | `src/explosives.js:291`, `src/explosives.js:454`, `src/explosives.js:362`, `src/explosives.js:427` |

### 2.13 Viewmodel numbers

The viewmodel is drawn by its own camera: vertical field of view 54°, near plane 0.01 m, far 10 m, drawn after the
world with the depth buffer cleared, so the gun never clips into walls (`src/render.js:423`,
`src/config/player.js:79`, `docs/CONTRACT.md:221-222`). Every pose below is the place of the gun-space origin in view
space at that field of view.

**Base poses** (position in metres as x right, y up, z toward the viewer; rotation in radians as pitch, yaw, roll):

| Pose | CHOPPER position | CHOPPER rotation | NINE position | NINE rotation | Source |
|---|---|---|---|---|---|
| Hip, view 1 "Close" (default) | 0.15, −0.09, −0.24 | 0.05, 0.28, −0.35 | 0.105, −0.056, −0.36 | 0.07, 0.11, −0.18 | `src/config/weapons.js:80`, `src/config/weapons.js:151` |
| Hip, view 2 "Three-quarter" | 0.17, −0.12, −0.30 | 0.04, 0.22, −0.30 | 0.10, −0.075, −0.44 | 0.06, 0.11, −0.20 | `src/config/weapons.js:81`, `src/config/weapons.js:152` |
| Hip, view 3 "Compact" | 0.12, −0.085, −0.25 | 0.05, 0.24, −0.30 | 0.075, −0.055, −0.33 | 0.07, 0.15, −0.16 | `src/config/weapons.js:82`, `src/config/weapons.js:153` |
| Sprint (lowered across the body) | 0.05, −0.20, −0.27 | −0.32, 0.80, −0.30 | 0.05, −0.20, −0.30 | −0.60, 0.60, −0.20 | `src/weapon/chopper.js:281`, `src/weapon/nine.js:200` |
| Reload (brought to the centre, magazine well presented) | 0.05, −0.105, −0.31 | 0.40, 0.34, −0.55 | 0.03, −0.085, −0.33 | 0.50, 0.32, −0.50 | `src/weapon/chopper.js:282`, `src/weapon/nine.js:201` |
| Wall (muzzle tipped up, pulled in) | 0.09, −0.15, −0.14 | 0.62, 0.12, −0.10 | 0.07, −0.13, −0.24 | 0.75, 0.10, 0 | `src/weapon/chopper.js:283`, `src/weapon/nine.js:202` |
| Holster (down and away, out of frame) | 0.20, −0.46, −0.20 | −0.55, 0.25, −0.45 | 0.17, −0.44, −0.24 | −0.60, 0.20, −0.40 | `src/weapon/chopper.js:284`, `src/weapon/nine.js:203` |
| Aim **(derived)**: rear sight on the view axis | 0, −0.0555, −0.1365 | 0, 0, 0 | 0, −0.0185, −0.3575 | 0, 0, 0 | `src/weapon/viewmodel.js:257-259` |

The names of the three views are the "Weapon position" setting (`src/ui/copy.js:50-51`, default 1:
`src/core/settings.js:15`).

**Markers on the guns** (gun space, mm: s forward, x right, y up):

| Marker | CHOPPER | NINE | Source |
|---|---|---|---|
| Muzzle | s 497.5, 0, 0 | s 201, 0, 0 | `src/weapon/chopper.js:271`, `src/weapon/nine.js:191` |
| Ejection port (casings start here) | s 150, x 19, y 18 | s 105, x 12, y 14 | `src/weapon/chopper.js:272`, `src/weapon/nine.js:192` |
| Rear sight (the point put on the view axis) | s 23.5, y 55.5 | s 12.5, y 18.5 | `src/weapon/chopper.js:273`, `src/weapon/nine.js:193` |
| Front sight tip | s 409, y 55.5 | s 183.5…188.5, y 18.5 | `src/weapon/chopper.js:115`, `src/weapon/nine.js:100` |
| Sight radius **(derived)** | 385.5 mm | about 173.5 mm | |
| Eye relief: eye to rear sight when aimed | 160 mm | 370 mm | `src/weapon/chopper.js:275`, `src/weapon/nine.js:194` |
| Recoil pivot (kicks turn the gun about it) | s −20, y −30: the back of the receiver, in the firing hand | s −30, y −85: the wrist | `src/weapon/chopper.js:277`, `src/weapon/nine.js:196` |
| Bolt / slide travel | 92 mm back | 44 mm back | `src/weapon/chopper.js:18`, `src/weapon/nine.js:14` |
| Trigger pivot; trigger turn when pulled | s 108, y −38; 0.34 rad | s 91, y −31; 0.30 rad | `src/weapon/chopper.js:215`, `src/weapon/chopper.js:303`, `src/weapon/nine.js:148`, `src/weapon/nine.js:218` |
| Magazine hinge / axis | hinge at the front lip of the well, s 222, y −40 | slides along (s 0.250, y 0.968), base to lips | `src/weapon/chopper.js:224`, `src/weapon/nine.js:17` |
| Barrel tilt when the slide unlocks | — | 0.04 rad about the lug at s 70, y −8 | `src/weapon/nine.js:145`, `src/weapon/nine.js:260` |
| First-person flash size (star, jet) | 0.20 m, 0.34 m | 0.12 m, 0.13 m | `src/weapon/chopper.js:278`, `src/weapon/nine.js:197` |
| Elbow targets in view space (right; left) | 0.34, −0.40, 0.02; −0.22, −0.44, −0.24 | 0.24, −0.38, −0.08; −0.15, −0.40, −0.15 | `src/weapon/chopper.js:294`, `src/weapon/nine.js:213` |
| Triangles as built **(measured)** | 3 928 | 2 200 (both arms: 6 024) | `src/weapon/viewmodel.js:680-682` |

**Fire kick** (visual only: velocity impulses into six springs; `src/weapon/viewmodel.js:651-664`):

| Channel | CHOPPER impulse | CHOPPER spring [w, z] | NINE impulse | NINE spring [w, z] | Source |
|---|---|---|---|---|---|
| Back along the bore | 0.82 m/s | [44, 0.55] | 0.55 m/s | [56, 0.55] | `src/config/weapons.js:55`, `src/config/weapons.js:128`, `src/config/weapons.js:66`, `src/config/weapons.js:139` |
| Pitch (muzzle rise) | 1.5 rad/s | [36, 0.5] | 6.4 rad/s | [50, 0.5] | `src/config/weapons.js:56`, `src/config/weapons.js:129` |
| Yaw, random sign | ± 0.475 rad/s | [30, 0.45] | ± 0.65 rad/s | [38, 0.48] | `src/config/weapons.js:57`, `src/config/weapons.js:130` |
| Roll, random sign | ± 0.85 rad/s | [31, 0.42] | ± 1.15 rad/s | [38, 0.45] | `src/config/weapons.js:58`, `src/config/weapons.js:131` |
| Up | 0.11 m/s | [40, 0.5] | 0.20 m/s | [46, 0.5] | `src/config/weapons.js:59`, `src/config/weapons.js:132` |
| Side, random sign | ± 0.09 m/s | [40, 0.5] | ± 0.10 m/s | [46, 0.5] | `src/config/weapons.js:60`, `src/config/weapons.js:133` |
| First / second round of a burst (back and pitch only) | × 1.4 / × 1.2 | | × 1 / × 1 | | `src/config/weapons.js:61-62`, `src/config/weapons.js:134-135` |
| Random spread of every impulse | × (1 ± 0.12) | | × (1 ± 0.10) | | `src/config/weapons.js:63`, `src/config/weapons.js:136` |
| Crouching | × 0.88 | | × 0.90 | | `src/config/weapons.js:64`, `src/config/weapons.js:137` |
| Fully aimed: back, rotations, shifts | × 0.75, × 0.10, × 0.90 | | × 0.80, × 0.42, × 0.80 | | `src/config/weapons.js:65`, `src/config/weapons.js:138` |

Peak of one hip-fire impulse **(derived from the spring equation)**: CHOPPER 9.7 mm back at 27 ms, 1.30° of muzzle
rise at 34 ms, settled (2 %) in about 0.17 to 0.31 s depending on the channel; NINE 5.1 mm back at 21 ms, 4.0° of
muzzle rise at 24 ms, settled in about 0.13 to 0.23 s.

**Other springs and additive motion** (`src/weapon/viewmodel.js:20-31` unless noted):

| Constant | Value |
|---|---|
| Aim spring [w, z] | CHOPPER [23, 0.75], NINE [29.5, 0.75] (`src/config/weapons.js:69`, `src/config/weapons.js:142`) |
| Look-lag spring [w, z]; soft limit | CHOPPER [13.5, 0.64], 0.07 rad; NINE [19, 0.6], 0.085 rad (`src/config/weapons.js:70-71`, `src/config/weapons.js:143-144`) |
| Look lag | gain 0.5 of the frame's look delta, roll 0.55 × the yaw lag, sideways shift 0.018 m per rad, × 0.22 when aimed |
| Breathing | 0.25 Hz: 1.3 mm up and down, 0.0032 rad pitch (phase + 1.1 rad), 0.0016 rad roll at half the frequency; × 0.18 when aimed |
| Footstep bob, walk → sprint | vertical 3.6 → 10.5 mm, sideways 3.4 → 7.5 mm, roll 0.008 → 0.032 rad, pitch 0.004 → 0.014 rad |
| Bob while aimed; while crouching | positions × 0.14, rotations × 0.05; amplitude × 0.72 |
| Movement inertia | rate 7.7; strafe push 4.5 mm, surge push 3.5 mm (per 40 m/s² of acceleration), lean 0.045 rad at 6.4 m/s sideways, fall 3.5 mm and 0.012 rad per m/s of vertical speed; × 0.25 when aimed |
| Jump | impulse + 0.85 m/s into the land spring |
| Landing | impulse − 0.075 × landing speed (speed capped at 14 m/s); land spring [15, 0.45]; roll 0.5 × the spring, alternating side |
| Bump spring (dry click, magazine events) | [26, 0.5] on pitch, roll and height |
| Aim arc | at the middle of the aim transition the gun dips 12 mm and cants 0.07 rad |
| Trigger finger | `damp` rate 38 toward "trigger held and allowed to fire" |
| Reload pose weight | in over the first 0.24 s, out over the last 0.30 s, both eased (`src/weapon/viewmodel.js:464`) |

### 2.14 Config values that are defined but never read

| Value | Where | Note |
|---|---|---|
| `chopper.inspectAfter: 24` | `src/config/weapons.js:75` | No idle-inspect animation exists. `weapon.inspect(spec)` is a screenshot hook that freezes the gun in a given pose (`src/weapon.js:35-38`, `src/weapon/viewmodel.js:773-793`) |
| `kick.arm: [0.55, 0.35]` and `[0.8, 0.6]` | `src/config/weapons.js:67`, `src/config/weapons.js:140` | Never read: the arms simply follow the gun |
| `common.noise: {radius: 45, every: 0.3}` | `src/config/weapons.js:192` | The enemies use their own copy with the same numbers (`src/config/enemies.js:227`, `src/config/enemies.js:234`) |
| `common.shake.decay: 1.7` | `src/config/weapons.js:194` | The player uses `src/config/player.js:133` (same number) |
| `KINDS.*.box` | `src/explosives.js:20-21` | Only a fallback: the collider takes the catalogue size, which is identical |

### 2.15 Where the documents and the code differ (the code wins)

| Document | Code |
|---|---|
| `docs/CONTRACT.md:458`: "Rule's forearms: bare, brown skin, a gold watch" | Black gloves, a gold watch on the left forearm and a gold curb chain on the right (`src/weapon/arms.js:1-2`), as `docs/DESIGN.md:295-297` asks |
| `src/weapon/material.js:221` comment: flash jet strength "0.25" for the NINE | The value set is 0.3 (`src/weapon/viewmodel.js:256`) |
| `src/weapon/viewmodel.js:494` comment: the draw comes "up with a little overshoot" | The overshoot never shows: a blend weight at or below zero is ignored, so the gun reaches its hip pose 0.14 s into the 0.32 s draw and stays there (3.17) |
| `docs/DESIGN.md:145-146` explosive numbers; `docs/DESIGN.md:111-112` melee numbers; `docs/DESIGN.md:138-139` resupply | All match the code |
| `docs/DESIGN.md:214`: "about 18–22 explosives" | 21 (14 tanks, 7 racks) |

---------------------------------------------------------------------------------------------------

## 3. Behaviour

### 3.1 Order within a frame

The main loop calls, while the game is live: `player.update`, `weapon.update`, `enemies.update`, `explosives.update`
(`docs/CONTRACT.md:83-85`). So the weapon sees this frame's eye position and aim, and an explosive hit by a round
has its fuse run by `explosives.update` afterwards: even a popped one (0.06 s fuse) blows on a later frame, never
inside the weapon's own step.

One `weapon.update(dt)` (`src/weapon/logic.js:591-657`), in order:

1. Player dead: `drop()`, aim ramps out, stop. A dropped gun with a living player is picked up again.
2. Timers: `cooldown −= dt`, `sinceShot += dt`, `strikeWait −= dt`, `fireBuffer −= dt`. Bloom drains if the last round
   is more than 0.15 s old. Heat cools. The burst counter clears after 0.24 s (and the weave phase is re-rolled).
3. Weapon select: `swap` pressed, else `weapon1`, else `weapon2`.
4. Melee press.
5. Reload press, then the auto-reload timer.
6. Advance the switch, the reload and the strike timelines (a strike resolves its blow here).
7. Sprint-lowered blend.
8. Aim ramp; writes `player.ads` and `render.post.ads`.
9. Spread: compute the target cone, `damp` `weapon.spread` toward it.
10. Trigger: fire, dry-fire, buffering.
11. Wall probe, gamepad aim slow-down.
12. Publish `state`, `cue`, ammunition and the animation inputs; then the viewmodel poses itself from them
    (`src/weapon.js:25-28`).

Consequences of the order: a swap and a strike pressed on the same frame gives the swap (the strike is then blocked);
a strike and a reload pressed on the same frame gives the strike; the spread used by a round is the value damped on
that same frame, before the round's own bloom is added.

### 3.2 The weapon state machine

The rules hold one **activity** at a time plus a few continuous values. `busy` means the activity is Reloading,
Switching or Striking (`src/weapon/logic.js:160`).

| State | Timer | Left by |
|---|---|---|
| **Ready** | — | the triggers below |
| **Reloading** `{t, empty}` | counts up to 2.24 / 2.72 s (CHOPPER) or 1.50 / 1.90 s (NINE) | its `done` mark; a strike; a switch request; death |
| **Holstering** `{t, to}` | 0.28 s | the timer (the other gun is equipped and Drawing starts with the leftover time); a request for the gun being put away |
| **Drawing** `{t, to}` | 0.32 s | the timer; a request for the other gun |
| **Striking** `{t, landed}` | 0.55 s; the blow at 0.16 s | the timer; death |
| **Dropped** | — | `reset()`, or the player being alive again |

| From | Trigger and guard | To | Actions |
|---|---|---|---|
| Ready | reload pressed, or the auto-reload timer runs out; magazine not full and reserve > 0 | Reloading | `empty` = magazine is 0; clear the auto-reload timer and the fire buffer; event `start` (`src/weapon/logic.js:289-298`) |
| Reloading | each mark of 2.3 is passed | Reloading, then Ready at `done` | events `magout`, `magin` (ammunition moves), `bolt`, `done` (`src/weapon/logic.js:308-324`) |
| Ready or Reloading | melee pressed; no strike running, 0.75 s since the last strike began, not switching | Striking | a running reload is cancelled (event `cancel`); clear auto-reload and fire buffer; event `weapon:swing` (`src/weapon/logic.js:381-392`, `src/weapon/logic.js:625`) |
| Striking | t ≥ 0.16 s, once | Striking | `combat.melee`; event `weapon:melee`; shake; rumble (`src/weapon/logic.js:394-411`) |
| Striking | t ≥ 0.55 s | Ready, then at once Holstering if a swap was queued | (`src/weapon/logic.js:412-419`) |
| Striking | swap / weapon key | Striking | the request is queued (the latest one wins) (`src/weapon/logic.js:337-340`) |
| Ready or Reloading | swap, or the key of the gun not in hand | Holstering | a running reload is cancelled; clear auto-reload and fire buffer; event `switch {phase: 'holster'}` (`src/weapon/logic.js:341-347`) |
| Holstering | t ≥ 0.28 s | Drawing | the other gun becomes `current`; cooldown, burst, bloom, heat, fire buffer, dry latch and auto-reload are cleared; t keeps the overshoot; event `switch {phase: 'draw'}` (`src/weapon/logic.js:365-373`, `src/weapon/logic.js:217-234`) |
| Holstering | a request for the gun being put away (swap again, or its key) | Drawing the same gun | t = 0.32 × (1 − t / 0.28): it comes back up from where it got to; event `switch {phase: 'draw'}` (`src/weapon/logic.js:348-355`) |
| Drawing | t ≥ 0.32 s | Ready | (`src/weapon/logic.js:374`) |
| Drawing | a request for the other gun | Holstering | t = 0.28 × (1 − t / 0.32); event `switch {phase: 'holster'}` (`src/weapon/logic.js:356-362`) |
| any | the player is dead | Dropped | a running reload is cancelled (event `cancel`); switch, strike and queued swap are discarded (`src/weapon/logic.js:269-278`) |
| Dropped | `weapon.reset()` at the next run | Ready | full ammunition, CHOPPER in hand |

Firing is not an activity: a round may leave whenever the activity is Ready and the sprint-lowered blend is below
0.45 (`src/weapon/logic.js:514`).

The public `weapon.state` is derived, first match wins (`src/weapon/logic.js:174-181`): Dropped → `lowered`;
Holstering or Drawing → `switching`; Striking → `melee`; Reloading → `reloading`; sprint-lowered blend above 0.5 →
`lowered`; a round in the last 0.14 s → `firing`; else `idle`. The HUD hides the crosshair while the state is
`lowered`, while the aim amount is above 0.6 and when the player is dead (`src/hud.js:375`).

The HUD cue (`src/weapon/logic.js:166-172`): none while Dropped or switching; `reloading` while Reloading; with an
empty magazine `reload` if any reserve is left, else `empty`; `low` at 9 rounds or fewer (CHOPPER) or 5 or fewer
(NINE). Copy: "Reloading", "Low ammo", "R — Reload", "Empty — Q swaps" (`src/ui/copy.js:28-34`).

### 3.3 Trigger logic and input buffering

Pseudo-code of `pullTrigger` (`src/weapon/logic.js:511-549`), run once per frame after `cooldown −= dt`:

```
held    = fire is down
canFire = activity is Ready and sprintBlend < 0.45
if not held: dryLatch = false

CHOPPER (automatic)
  firing = held and canFire and mag > 0
  if not (firing and firedLastFrame) and cooldown < −0.001: cooldown = −0.001     # nothing banked
  firedLastFrame = firing
  if firing:
      repeat at most 3 times while cooldown ≤ 0 and mag > 0:
          shoot(); cooldown += 60 / 720
  else if held and canFire and not dryLatch and cooldown ≤ 0:                      # magazine is empty
      dryFire()

NINE (semi-automatic)
  if fire was pressed this frame: fireBuffer = 0.13
  if fireBuffer > 0 and canFire and cooldown ≤ 0:
      fireBuffer = 0
      if mag > 0: shoot(); cooldown = 60 / 420
      else: dryFire()

cooldown = max(cooldown, −0.001)

dryFire():  dryLatch = true
            NINE only: cooldown = 0.12
            if reserve > 0: autoReload = 0.32 (CHOPPER) or 0.28 (NINE)
            event weapon:dry; the viewmodel nods (bump pitch + 0.35 rad/s, height − 0.04 m/s)
```

What this means for the player:

- **Frame-rate independence.** While the CHOPPER keeps firing, the unused part of each interval carries over, and a
  slow frame fires up to three rounds at once, so 720 rpm holds at any frame rate. A fresh pull starts from "ready"
  and banks nothing (at most 1 ms).
- **CHOPPER buffering.** The trigger is a level, not an edge: holding fire through a reload, a switch, a strike or the
  sprint-lowered pose starts the burst on the first frame firing is allowed.
- **NINE buffering.** A press is remembered for 0.13 s. A click up to 0.13 s before the end of the 0.143 s cooldown, of
  a draw, of a reload or of a strike still fires. Holding the button never repeats.
- **Dry fire.** One click per trigger pull on the CHOPPER (the latch), one per press on the NINE with a 0.12 s
  cooldown. A dry pull schedules a reload 0.32 / 0.28 s later when there is reserve; emptying the magazine without
  pulling again does **not** reload (`test/weapon-logic.test.js:426`). On the CHOPPER, holding the trigger through
  the last round clicks one interval later, so the reload starts 0.083 + 0.32 = 0.40 s after the last round
  **(derived)**. Starting a strike or a switch, or a manual reload, clears the scheduled reload.
- **Not buffered:** reload presses and melee presses are ignored when their guard fails. A weapon key during a strike
  is queued until the strike ends.

Bindings (owned by the input spec): fire = left mouse, Enter, right trigger, touch FIRE; aim = right mouse or left
trigger held, or the touch AIM button, which latches on and off (`src/input.js:48`); reload = R / X; swap = Q / Y /
D-pad up or down / mouse wheel (0.28 s debounce); direct select = 1, 2 / D-pad left, right; melee = F, V, middle
mouse / RB, R3 (`src/config/player.js:207-259`, `src/input.js:508-517`).

### 3.4 What one round does

`shoot()` (`src/weapon/logic.js:441-501`), in order:

1. Magazine − 1; burst counter + 1; `sinceShot` = 0; heat + 0.05 (max 1.3); `combat.stats.shots` + 1.
2. Direction: a uniformly random point of the disc of radius `tan(weapon.spread)` one metre ahead:
   `dir = normalize(forward + right · r cos a + up · r sin a)`, `r = tan(spread) · sqrt(u1)`, `a = 2π · u2`.
   `forward` is the player's aim vector, which already carries the recoil offset of earlier rounds but never the
   camera shake (`docs/CONTRACT.md:432-435`).
3. `combat.hitscan` from the eye along `dir` with the gun's range and damage and the head multiplier 2.2 (3.12).
4. The muzzle and the ejection port in world space, as the player sees them on screen (3.16). Without a viewmodel the
   muzzle is guessed 0.6 m ahead, 0.16 m right and 0.13 m below the eye (`src/weapon/logic.js:427-429`).
5. Effects: a tracer from the muzzle to the hit point (or to the end of the range on a miss) unless the hit is
   closer than 0.9 m; the muzzle flash, scaled by `lerp(1, 0.62, aim)`; one casing from the ejection port.
6. A world light at the muzzle: `#ffb020`, intensity 45 (CHOPPER) or 30 (NINE), range 9 m, fading linearly to zero
   in 0.05 s (`src/render.js:514-546`).
7. Event `weapon:fire`.
8. Camera recoil and shake (3.6).
9. Bloom + 0.17 (CHOPPER) or + 0.30 (NINE), capped at 1.
10. The viewmodel kick (2.13), told the round's index in the burst, whether it emptied the magazine, the aim amount
    and the crouch flag.
11. Gamepad rumble.

Every round draws a tracer; there is no "every n-th round" rule.

### 3.5 Spread

Target cone, recomputed every frame (`src/weapon/logic.js:644-651`):

```
cone = lerp(hip, ads, aim)
     + clamp01(playerSpeed / 6) · lerp(moveHip, moveAds, aim)
     + bloom · lerp(bloomHip, bloomAds, aim)
     + (airborne ? air : 0)
     − (crouching ? crouch · (1 − aim) : 0)
weapon.spread = damp(weapon.spread, max(0, cone), 18, dt)
```

- `aim` is the eased aim amount 0…1 (3.7). `playerSpeed` is horizontal speed in m/s; walking is 3.8, sprinting 6.4,
  crouching 1.9, fully aimed at most 2.4 (`src/config/player.js:21-28`), so walking from the hip adds 63 % of the
  movement term and moving while aimed 40 %.
- **Bloom** is 0…1. Each round adds `shot`; it only drains (at `decay` per second) once the last round is more than
  0.15 s old (`src/weapon/logic.js:613-614`). Both guns at their full rate fire faster than that, so bloom never
  drains inside a burst: the CHOPPER saturates on its 6th round, the NINE on its 4th. Recovery from full bloom takes
  0.15 + 0.67 s (CHOPPER) or 0.15 + 0.36 s (NINE) **(derived)**.
- Because the cone in use is damped at 18 per second, it trails the target. **(measured)** CHOPPER, hip, standing,
  held trigger at 60 frames a second, cone used by round 1…10: 0.01250, 0.01336, 0.01441, 0.01550, 0.01660, 0.01771,
  0.01871, 0.01894, 0.01899, 0.01900 rad. Aimed: 0.00120 rising to 0.00340 by round 9. NINE, hip, one round every
  0.15 s: 0.0105, 0.0129, 0.0154, 0.0180, 0.0189, then 0.0190.
- Switching guns clears the bloom of the gun in hand but not `weapon.spread`, which glides to the new gun's cone
  during the draw.
- The HUD crosshair gap is the cone projected on the screen: `tan(cone) / tan(fov / 2) · viewportHeight / 2 + 4 px`,
  plus 10 px while sprinting, clamped 4…70 px (`src/ui/logic.js:99-104`).

### 3.6 Recoil: from the round to the camera

Per round (`src/weapon/logic.js:481-496`):

```
scale = lerp(1, 0.55, aim) · (crouching ? 0.85 : 1)
CHOPPER  pitch = 0.0068 · scale · uniform(0.85, 1.15);  if burst ≥ 10: pitch · 0.38
         yaw   = burst < 4 ? uniform(−1, 1) · 0.0011 · scale
                           : (sin(burst · 0.57 + weavePhase) · 0.0042 + uniform(−1, 1) · 0.001) · scale
NINE     pitch = 0.0092 · scale · uniform(0.90, 1.10)
         yaw   = uniform(−1, 1) · 0.0025 · scale
player.addRecoil(pitch, yaw)            # radians; pitch up, yaw to the left
player.addShake(shake · scale)          # 0.12 CHOPPER, 0.14 NINE
```

`burst` is the 1-based index of the round in the current burst. The CHOPPER's pattern is therefore: nine rounds of
full climb, with almost no sideways drift for the first three and a sine weave of about 11 rounds per cycle from
the fourth; from the tenth round the climb drops to 38 % while the weave goes on. The weave's starting phase
differs from burst to burst.

In the player (`src/player.js:380-388`, `src/player.js:77-108`, `src/player.js:408-426`):

1. 35 % of the kick is added to the player's own pitch and yaw at once and for good.
2. 65 % is added to a recoverable offset target, clamped to ± 0.30 rad pitch and ± 0.20 rad yaw.
3. Every frame the offset on screen chases its target (`damp`, rate 34). Once 0.09 s have passed since the last kick,
   the target decays toward zero at 6.5 per second.
4. The aim vector and the camera are both `player rotation + offset`, so rounds follow the kicked view. The camera
   alone adds shake (trauma², two sines per axis) and view roll.

With the CHOPPER's 0.083 s interval the 0.09 s hold never elapses inside a burst, so the recoverable part only comes
back after the trigger is released; with the NINE at its cap about 29 % of the recoverable offset is shed between
rounds **(derived)**.

### 3.7 Aiming down the sights

- The rules read the aim input as a level: they want the aim while it is down, the activity is Ready and the
  sprint-lowered blend is below 0.35 (`src/weapon/logic.js:642`). Mouse and gamepad hold it; only the touch button
  latches, and that happens in the input module.
- `adsLinear` moves linearly toward 1 or 0 over the gun's aim time (0.18 / 0.14 s); the aim amount is
  `smootherstep(adsLinear)` (`src/weapon/logic.js:584-589`). It is written to `player.ads` every frame.
- Starting a reload, a strike or a switch therefore ramps the aim out; if the button is still held when the activity
  ends, the aim ramps back in.
- Effects of the aim amount elsewhere: spread and recoil as above; look rate × `lerp(1, 0.6, aim)`
  (`src/config/player.js:66`, `src/player.js:466`); field of view toward 52° vertical, with `damp` rate 30 while the
  amount is strictly between 0.02 and 0.98 (`src/config/player.js:75-78`, `src/player.js:543-546`); speed capped
  toward 2.4 m/s (`src/config/player.js:25`); sprint refused from 0.35 (`src/config/player.js:50`); a vignette of
  0.22 × aim (`src/config/look.js:33`, `src/render.js:132`); the crosshair hidden above 0.6.
- The viewmodel does not follow the aim amount directly. A spring (CHOPPER [23, 0.75], NINE [29.5, 0.75]) leaves for
  1 when the ramp starts rising and for 0 when it starts falling, and the pose blends to the aim pose by the spring's
  value clamped to 0…1 (`src/weapon/viewmodel.js:452-458`, `src/weapon/viewmodel.js:493`). It first reaches the aim
  pose after about 0.16 s (CHOPPER) or 0.12 s (NINE) and is settled by about 0.23 / 0.18 s **(derived)**.
- **Sight alignment.** The aim pose puts the rear sight on the view axis, `relief` in front of the eye, with the
  bore parallel to the view axis and no cant (`src/weapon/viewmodel.js:257-259`). The front sight tip is at the same
  height over the bore as the rear notch, so notch and post sit exactly on the screen centre, which is where the
  ray leaves from (verified by rendering both guns). The bore runs 55.5 mm (CHOPPER) or 18.5 mm (NINE) below the
  line of sight; no parallax is modelled because rounds leave the eye.

### 3.8 Sprint lowering, wall pull-back, gamepad aim slow-down

**Sprint lowering** (`src/weapon/logic.js:637-640`): a critically damped spring (z = 1) drives a blend 0…1 toward 1
while the player is sprinting and does not want the gun, else toward 0. "Wants the gun" = busy, or fire held, or aim
held; then the spring runs at 17 × 1.5 = 25.5 rad/s instead of 17. The player's own sprint rule already drops the
sprint while fire is held or the aim amount is 0.35 or more (`src/player.js:48-50`). Timings from rest
**(derived)**: lowering crosses 0.5 (state `lowered`) after 0.10 s; raising to fire (below 0.45) takes 0.072 s; to
aim (below 0.35) 0.087 s. The blend moves the viewmodel toward the sprint pose and switches the bob to its sprint
amplitudes.

**Wall pull-back** (`src/weapon/logic.js:556-565`): every 0.08 s a ray from the eye along the aim, as long as the
gun's start distance (1.05 / 0.80 m). `target = clamp01((start − hit distance) / (start − full))`, full at 0.42 /
0.32 m; `wall = damp(wall, target · lerp(1, 0.15, aim), 12, dt)`. Purely visual: the viewmodel blends toward the
wall pose; firing is never blocked.

**Gamepad aim slow-down** (`src/weapon/logic.js:568-582`): only while the gamepad is the active device. Every 0.05 s:
is an unoccluded enemy under the ray from the eye along the aim within 60 m (`src/enemies.js:416-420`)? The look-rate
multiplier `input.aimSlow` damps (rate 14) toward 0.55 if so, else toward 1. It never turns the view.

### 3.9 Reloading

- Starts on the reload press or the auto-reload timer when the activity is Ready, the magazine is not full and the
  reserve is above zero (`src/weapon/logic.js:289-298`). `empty` is decided at the start.
- **Ammunition moves at `magIn`**, not at the end: `n = min(magazine size − magazine, reserve)`, magazine + n,
  reserve − n (`src/weapon/logic.js:313-318`). There is no extra round in the chamber: a tactical reload tops up to
  30 / 15 and the rounds left in the old magazine are not lost. The NINE's reserve stays infinite.
- Nothing can be fired until `done`. Aiming is released for the whole reload. Sprinting does not cancel it (the gun
  is raised while reloading).
- **Cancel** (strike, switch request, death): event `cancel`. Rounds stay where they are: in the gun if `magIn` had
  passed, otherwise nothing changed (`src/weapon/logic.js:300-306`, `test/weapon-logic.test.js:389`).
- The CHOPPER with no reserve and an empty magazine cannot reload: the cue is `empty` and the trigger only clicks.

### 3.10 Switching guns

- Total 0.28 + 0.32 = 0.60 s. The gun in hand changes at the end of the holster phase; each gun keeps its own
  magazine and reserve (`src/weapon/logic.js:81-82`).
- `swap` asks for the other gun; while Holstering it asks for the gun being put away again, which reverses the
  switch (`src/weapon/logic.js:621`). `weapon1` / `weapon2` ask for that gun; asking for the gun already in hand or
  already on its way does nothing.
- A reversal keeps its place: the new phase starts as far along as the old one was short of finishing (table in 3.2).
- A switch cancels a reload and the scheduled auto-reload. No round can be fired, no aim taken and no strike started
  until the draw is over.
- Equipping clears the cooldown, burst counter, bloom and heat. The gun that was put away keeps nothing but its
  ammunition.

### 3.11 Melee

- Press → Striking for 0.55 s; another strike may start 0.75 s after this one began (so 0.20 s after it ended).
- At 0.16 s the blow is resolved with the eye position and aim **of that frame** (`src/weapon/logic.js:396-404`).
- `combat.melee` (`src/combat.js:246-303`): among living enemies, take the point on each body nearest to the eye's
  height (a Goon: his axis, clamped between 0.2 m above his feet and 0.15 m below his top; a Buzzard: its centre).
  An enemy qualifies when the distance to its surface (centre distance minus its radius, 0.3 m Goon, 0.5 m Buzzard)
  is at most 2.3 m, the angle between the aim and the nearest edge of its body is at most 25°, and
  `physics.lineOfSight(eye, point)` holds. The nearest by surface distance takes 60 damage as a `body` hit with
  weapon `melee`. Events `impact` (surface `flesh` or `drone`) and `player:hitEnemy`.
- No enemy: a world ray of 2.3 m along the aim. A wall within reach is reported (no `impact` event, no damage); the
  camera shakes 0.11 and the viewmodel bounces off it. An explosive in the way counts as a wall: a strike never
  damages an explosive.
- Statistics: a melee kill counts as a kill; a strike is neither a shot nor a hit (`src/combat.js:240-244`).
- The line-of-sight test is the bullet one: `playerOnly` boxes (chain-link, glass, railings) do not block a strike.

### 3.12 Hitscan resolution

`combat.hitscan` (`src/combat.js:150-230`), for one ray of length `range`:

1. World: `physics.raycast(origin, dir, range)`. `limit` = its distance, or the range when nothing is hit.
2. Enemies (player rounds only): `enemies.raycast(origin, dir, limit)`: the nearest of every living enemy's shapes;
   a Goon's head sphere is tested before his body capsule and keeps the hit unless the body is strictly nearer.
3. Explosives: `explosives.raycast(origin, dir, limit + 0.03)`, a slab test against each live item's collider.
4. The player (enemy rounds only): the cylinder of 2.8, entered through its side or its caps; a ray that starts
   inside it hits at distance 0.
5. The nearest wins. An explosive wins over its own collider in the world list; a ray that stops on a collider owned
   by a live explosive is a hit on that explosive whatever step 3 said; an enemy at the same distance as an explosive
   wins; the player wins a tie.
6. Outcome:

| Result | Damage | Events |
|---|---|---|
| `enemy` | `damage × 2.2` on a Goon's head, else `damage`, through `enemies.damage(enemy, amount, {point, dir, part, from, weapon})` | `impact` with surface `flesh` or `drone` and the enemy; `player:hitEnemy`; `stats.hits + 1`; a kill adds `stats.kills` and, when the final blow was a head hit, `stats.headshots` |
| `explosive` | the round's damage from the player, 9 from an enemy, through `explosives.damage` | `impact` with the collider's surface (`metal`) |
| `player` | the round's damage through `player.damage(amount, origin, 'bullet')` | none here: `player:hit` is the cue |
| `world` | none | `impact` with the surface and normal of the box or the ground |
| `none` | none | none; the result's point is the end of the range (the tracer still flies there) |

Rules that follow: nothing is shot through cover (bodies only count in front of the world hit); there is no
penetration, no ricochet (the ricochet is only a sound: `src/audio/react.js:14`, `src/audio/react.js:157-158`) and no
falloff; rounds pass through `playerOnly` geometry; enemy rounds never hit other enemies
(`docs/CONTRACT.md:205-206`); a player round never hits the player.

What `enemies.damage` does with a hit (events `enemy:hit`, `enemy:killed`, provocation) is in spec 03
(`src/enemies.js:424-460`). `enemy:killed.byPlayer` is true for the player's rounds, strikes and for **any** blast.

### 3.13 Explosions

`combat.explode({pos, radius, damage, playerScale = 0.5, source, size})` (`src/combat.js:321-374`):

1. Event `explosion` first (fx, audio, the player's shake, enemy hearing at 30 m and the explosive chain all hang
   off it).
2. Every living enemy except `source`: target point = a Buzzard's centre, or a Goon's feet + half his height. If
   the distance is below the radius and `physics.lineOfSight(centre, target)` holds: damage × (1 − distance /
   radius), as a `body` hit from `blast`. Kills are counted.
3. The player: target = feet + 1.0 m (0.6 m crouching). Same test; damage × `playerScale` × (1 − distance / radius),
   kind `blast`.
4. Every explosive except `source` and those already gone: target = the centre of its collider; the ray may stop on
   that explosive's own collider. If in range and reached: `explosives.damage(item, amount, 'blast')`, which costs
   no hit points and only applies the chain rule of 3.14.

Falloff is linear to zero at the radius, there is no inner full-damage core, and cover blocks a blast completely.
Blast damage is not a hit for accuracy.

Other blasts that use this function: a Buzzard that crashes (radius 3 m, 30 damage, `small`; spec 03).

### 3.14 Explosives: fuse, chain, restoration

Each item is `idle`, `lit` or `gone` and owns one solid collider (surface `metal`, tag `explosive`) that is cover
for everyone until it blows (`src/explosives.js:265-283`).

```
damage(item, amount, from):                                  # src/explosives.js:362-375
    ignore when gone or amount ≤ 0
    from 'blast':         chain(item); return                # never costs hit points
    from an enemy object: amount = 9
    hp = max(0, hp − amount)
    if idle: ignite(fuse = 1.6 or 1.1)
    if hp ≤ 0: fuse = min(fuse, 0.06)

ignite(item, fuse):                                          # src/explosives.js:349-356
    state = lit; show the heated shell; start the jet of flame; start the hiss; event explosive:lit

on every `explosion` event (any source, any cause):         # src/explosives.js:392-404
    range = 2.2 + 1.6 × size        (size 1.9 / 2.3 for these props, else from the blast radius)
    for every item except the source and the gone ones:
        d = distance from the blast to the item's centre (its foot + half its height)
        if d ≤ range:  f = 0.14 + uniform[0, 0.3) + 0.03 × d
                       idle → ignite(f);   lit → fuse = min(fuse, f)
    line of sight is NOT required: the shock carries around corners and through walls

update(dt):                                                  # src/explosives.js:427-447
    for every lit item: fuse −= dt; at 0 → blow(item); else rattle and raise the hiss

blow(item):                                                  # src/explosives.js:406-425
    stop jet and hiss; state = gone; remove the collider (before the blast, so it shields nothing)
    show the wreck; event explosive:blast
    combat.explode(centre, 6.5 or 7.5 m, 170 or 210, player × 0.5, source = item)
    camera shake by distance; enemies.alert(centre, 60 m)
```

- A lit prop cannot be put out. More rounds only shorten the fuse by taking the hit points to zero.
- **The jet of flame** starts at the bullet hole when the fuse was lit by a ray on that same frame: 2 cm off the
  surface, pointing along the surface normal tilted upward (normal + 0.55 up). Lit by a blast, it comes out of the
  valve at 94 % of the prop's height in a random upward direction (`src/explosives.js:332-347`).
- While lit the shell glows (the same paint with emissive `#b8400f` at 0.6: `src/props/materials.js:122-131`), the
  prop rattles and the hiss rises (2.9).
- The chain makes a ripple: a neighbour goes 0.14 to about 0.6 s after the blast that caught it.
- `reset()` re-arms every item: full hit points, `idle`, collider back, jet and hiss stopped
  (`src/explosives.js:291-325`). The game calls it at every run reset and, in Hold the Block, when an even-numbered
  wave is cleared (`src/game.js:224`, `src/game.js:701`).

### 3.15 Death, reset, resupply

- **Death.** While the player is dead the weapon is Dropped every frame, the aim ramps out and the gun model is
  handed to the world: it leaves the hands with a velocity of 0.7 right, 1.1 up, 1.3 forward m/s (camera space) plus
  the player's, spins at 5.5 rad/s, falls at 13.5 m/s², bounces up to three times (vertical speed × −0.3, horizontal
  × 0.6, spin × 0.55) and comes to rest on its side 3.5 cm above the floor; the empty hands sink 0.64 m in 0.4 s and
  vanish (`src/weapon/viewmodel.js:713-730`, `src/weapon/viewmodel.js:409-435`, `src/weapon/viewmodel.js:631-638`).
  The dropped gun stays on the ground until the run is over.
- **Run reset** (`src/game.js:223-224`): `weapon.reset()` and `explosives.reset()`.
- **Hold the Block resupply**, on every cleared wave (`src/game.js:699-701`, `src/config/flow.js:163-168`):
  CHOPPER reserve + 90 up to a cap of 240 (a reserve already at or above the cap is left alone); + 35 health;
  explosives restored after even waves.
- The viewmodel is shown in the `playing` and `intro` states only (`src/game.js:146`).

### 3.16 Viewmodel: how a frame is posed

Each frame the gun's place in view space is built in four layers, then the parts and hands are placed on it
(`src/weapon/viewmodel.js:441-643`).

**Layer 1, base pose.** Start from the hip pose of the chosen view, then blend (position lerp, rotation slerp) in
this order: toward Sprint by the sprint-lowered blend; toward Reload by the reload weight; toward Wall by the wall
value; toward Aim by the aim spring; toward Holster by `ease(k)` while holstering and by `1 − easeOutBack(k)` while
drawing (k = progress of the phase 0…1), or by `ease(t / 0.3)` after a death drop
(`src/weapon/viewmodel.js:483-499`).

**Layer 2, strike.** While Striking, keyed offsets are added: a translation in view space and a rotation about the
gun's recoil pivot (3.17).

**Layer 3, additive motion** (constants in 2.13; `src/weapon/viewmodel.js:510-586`):

- *Footstep bob.* A phase advances by `speed · dt / stride` (stride = metres per footstep: 1.55 walking, 2.1
  sprinting, 1.05 crouching) while on the ground and faster than 0.3 m/s, and snaps to a whole number on every
  `player:step` event so it stays in step with the footfalls. Amplitude = `(speed / 3.8)^0.8`, × 0.72 crouching, 0 in
  the air, smoothed with `damp` rate 9. With `step = sin(phase · π)` (one swing per two steps) and
  `bounce = cos(phase · 2π)` (one dip per step): sideways = step × (3.4 → 7.5 mm), vertical = −bounce × (3.6 →
  10.5 mm), pitch = bounce × (0.004 → 0.014 rad), roll = step × (0.008 → 0.032 rad), the ranges blended by the
  sprint-lowered blend.
- *Breathing.* A 4 s cycle: height sin(b) × 1.3 mm, pitch sin(b + 1.1) × 0.0032 rad, roll sin(b / 2 + 0.4) ×
  0.0016 rad.
- *Look lag.* Each frame the look delta × 0.5 is added to two springs (yaw, pitch) through a soft limit
  `limit · x / (limit + |x|)`; the springs pull back to zero. The gun trails the view by the spring values, rolls
  0.55 × the yaw lag and shifts 18 mm per radian against the turn.
- *Inertia.* Sideways and forward acceleration (clamped to ± 40 m/s²) push the gun the other way; sideways speed
  leans it into the strafe; vertical speed in the air (clamped −12…8 m/s) floats it up and dips the muzzle when
  falling, and the reverse when rising.
- *Jump and landing.* One spring: a jump kicks it up, a landing kicks it down by the landing speed; it moves the
  gun's height, 1.6 × as pitch, and half as roll with alternating sign.
- *Bump spring.* Small impulses from the dry click and the reload marks (3.17).
- *Aim arc.* `sin(aim spring · π)`: a dip and a cant at mid-transition.

Each of these is scaled down while aimed (factors in 2.13).

**Layer 4, recoil springs.** The six springs of 2.13: pitch, yaw and roll turn the gun about its recoil pivot, side
and up shift it, and the back spring moves it straight back along its own bore
(`src/weapon/viewmodel.js:588-606`).

**Parts and hands.** The gun reports where its parts are and where each palm goes (a hand key: the middle of the
palm at a point, pressing along one direction, fingers running along another, plus a named finger pose;
`src/weapon/handling.js:23-31`). Keys in gun space ride with the gun; keys in view space ("rig") stay with the
camera (reaching for a magazine). Between keys the hand moves with an eased blend of position, rotation and finger
pose (`src/weapon/handling.js:50-72`). Each forearm simply points from the wrist at a fixed elbow target and rolls
with the back of the hand; there is no upper arm (`src/weapon/arms.js:595-615`).

**Muzzle and port in world space.** A view-space point seen by the 54° viewmodel camera is turned into the world
point that lands on the same pixel of the main camera: `world = cameraPosition + cameraRotation · (x · k, y · k, z)`,
`k = tan(worldFov / 2) / tan(viewmodelFov / 2)` (`src/weapon/viewmodel.js:234-239`). Tracers, casings, the muzzle
light and `weapon:fire.pos` use it.

**Light.** The gun is lit to sit in the street's light: by day one hard key from the sun's direction and colour at
0.85 × the sun's intensity plus a neutral sky / warm pavement ambient and a reflection box of the sunlit avenue; by
night a rim light coloured by the street lamps around the player and a darker reflection box; a cool fill from the
camera side in both (`src/config/weapons.js:199-209`, `src/weapon/viewmodel.js:316-381`,
`src/weapon/material.js:115-204`). In Unreal the real scene lights the gun; keep only the intent.

### 3.17 Viewmodel: choreography timelines

**CHOPPER reload** (`src/weapon/chopper.js:223-264`, `src/weapon/chopper.js:301-329`,
`src/weapon/viewmodel.js:460-480`, `src/weapon/viewmodel.js:689-704`). The right hand stays on the grip throughout.

| t (s) | Left hand | Gun and parts | Spring impulses | Sound |
|---|---|---|---|---|
| 0.00 | leaves the handguard | pose starts blending to Reload (0.24 s) | — | `cloth` |
| 0.27 | wraps the magazine (palm on its left face, fingers across the front, thumb toward the catch) | | | |
| **0.40** | magazine comes free; from here it rides in the hand | | bump: height + 0.1 m/s, roll + 0.5 rad/s | `rifle_magout` |
| 0.53 | rocks it forward 0.42 rad about the front lip of the well, 3 cm down | | | |
| 0.68 | carries it down and left (4 cm left, 12 cm down, 3 cm back) | | | |
| 0.74 – 0.80 | at the pouch, off screen (view space −0.20, −0.46, −0.20) | magazine hidden from 0.70 to 0.80 | | |
| 0.80 | fresh magazine in the hand, top round showing | magazine visible again | | |
| 1.06 | back at the "away" position | | | |
| 1.15 | front lip hooked in the well | | bump: height + 0.12 m/s | |
| **1.44** | rocked home; magazine belongs to the gun again | **ammunition moves** | bump: height + 0.3 m/s, pitch + 0.7 rad/s | `rifle_magin` |
| 1.565 | tugs the magazine | | bump: height − 0.2 m/s, pitch − 0.5 rad/s | |
| 1.625 | lets go | | | |
| *Tactical* **1.89** | two fingers hooked over the charging handle (from 1.88) | handle pulled back to 32 % of its travel (29 mm) by 1.93, forward again by 1.98 | recoil back + 0.2 m/s | `rifle_bolt` |
| 1.99 – 2.22 | returns to the handguard | pose blends back to hip over the last 0.30 s | | |
| **2.24** | | reload over | | `cloth` (quieter) |
| *Empty* **1.96** | hooks the charging handle | handle pulled fully back (92 mm) by 2.07, held | recoil back + 0.5 m/s | `rifle_bolt` |
| 2.155 | lets the handle go | handle flies forward in 0.03 s | recoil back − 0.5 m/s, bump pitch − 0.9 rad/s | |
| 2.275 | hand off the handle, relaxed | | | |
| 2.66 | back on the handguard | pose blends back over the last 0.30 s | | |
| **2.72** | | reload over | | `cloth` (quieter) |

**NINE reload** (`src/weapon/nine.js:155-184`, `src/weapon/nine.js:216-264`).

| t (s) | Left hand | Right hand, gun and parts | Spring impulses | Sound |
|---|---|---|---|---|
| 0.00 | leaves the grip | pose starts blending to Reload | — | `cloth` |
| 0.06 – 0.30 | | right thumb reaches down for the magazine button (pose weight peaks at 0.18) | | |
| 0.15 | out of the way, low left (view space −0.10, −0.33, −0.30) | | | |
| **0.18** | | the old magazine drops free along the grip: 4.5 t² + 0.25 t metres, tumbling at 1.4 rad/s, hidden 0.4 m away or at 0.48 | bump: height + 0.1 m/s, roll + 0.5 rad/s | `pistol_magout` |
| 0.38 – 0.48 | at the pouch, off screen (−0.17, −0.52, −0.20) | | | |
| 0.48 | fresh magazine pinched in the hand, top round showing | | | |
| 0.80 | lined up under the grip (13 cm below, 5 cm back) | | | |
| 0.90 | lips entering the well (5 cm short along the grip axis) | | bump: height + 0.12 m/s | |
| **1.13** | open palm drives the base home | **ammunition moves** | bump: height + 0.3 m/s, pitch + 0.7 rad/s | `pistol_magin` |
| 1.20 | palm still on the base | | | |
| *Tactical* 1.47 | wrapped over the firing hand again | pose blends back over the last 0.30 s | | |
| **1.50** | | reload over | | `cloth` (quieter) |
| *Empty* 1.43 | out of the way again | the slide has been locked back since the last round | | |
| **1.61** | | right thumb up on the slide stop (pose weight peaks here, ± 0.1 s); the slide closes in 0.03 s | recoil pitch + 2.4 rad/s, back − 0.25 m/s | `pistol_slide` |
| 1.86 | wrapped over the firing hand again | | | |
| **1.90** | | reload over | | `cloth` (quieter) |

A cancelled reload has no animation of its own: the left hand and the magazine jump back to their rest places and
the pose weight decays at `damp` rate 16.

**Firing** (per round; `src/weapon/chopper.js:263-264`, `src/weapon/nine.js:183-184`, `src/weapon/nine.js:257-260`).

| | CHOPPER | NINE |
|---|---|---|
| Bolt carrier and charging handle / slide | back 92 mm in 0.020 s, forward in 0.045 s | back 44 mm in 0.018 s, forward in 0.042 s |
| Barrel | fixed | tilts up to 0.04 rad during the first third of the slide travel |
| After the last round | bolt closes as usual | the slide stays back until the slide stop is thumbed in the empty reload |
| Trigger and trigger finger | follow the held trigger at `damp` rate 38; trigger turns 0.34 rad; finger pose `rifleGrip` → `rifleTrigger` | 0.30 rad; `pistolGrip` → `pistolTrigger` |
| First-person flash (`src/weapon/viewmodel.js:666-676`, `src/weapon/material.js:262-264`) | star 0.20 m and jet 0.34 m, each × (0.8…1.3) × `lerp(1, 0.62, aim)`, rolled ± 0.6 rad, life 0.036…0.056 s, brightness `sqrt(life left / life)`, from a hot core (linear RGB 1.0, 0.93, 0.74) to an orange edge (1.0, 0.42, 0.08), a point light on the gun and hands for the same time | star 0.12 m, jet 0.13 m at 0.3 strength |
| Barrel smoke | when a round is fired with heat above 0.4 (about the 12th round of a burst **(derived)**): thin wisps from the muzzle every 0.085 s for 1.6 s, starting 0.11 s after the last round (`src/weapon/viewmodel.js:394-406`) | none |
| Dry click | bump: pitch + 0.35 rad/s, height − 0.04 m/s (`src/weapon/viewmodel.js:685-688`) | same |

**Switching** (`src/weapon/viewmodel.js:494-499`). Holster, 0.28 s: the gun eases (quintic) from wherever it is to
the Holster pose, down and to the right out of frame; the model is swapped at the bottom. Draw, 0.32 s: the new gun
rises along `1 − easeOutBack(k)` and is at its hip pose from k = 0.44 (0.14 s); it cannot fire until 0.32 s. Sounds:
`holster` at the start, `draw` at the change-over (`src/audio/react.js:89-93`).

**Melee** (`src/weapon/chopper.js:286-293`, `src/weapon/nine.js:205-212`). Offsets from the current base pose:
translation in view space (m), rotation about the recoil pivot (rad), eased between keys
(`src/weapon/viewmodel.js:280-289`).

| t (s) | CHOPPER "rifle butt": x, y, z; pitch, yaw, roll | NINE "pistol whip": x, y, z; pitch, yaw, roll |
|---|---|---|
| 0 | 0, 0, 0; 0, 0, 0 | 0, 0, 0; 0, 0, 0 |
| 0.08 wind-up | 0.05, −0.02, 0.07; 0.08, −0.30, 0.15 | 0.04, 0.05, 0.06; 0.55, −0.25, 0.35 |
| 0.16 contact | −0.13, 0.05, −0.20; −0.18, 1.20, −0.50 | −0.10, 0.02, −0.15; 1.05, 0.35, −0.60 |
| 0.27 follow-through | −0.14, 0.03, −0.16; −0.24, 1.30, −0.55 | −0.11, 0, −0.13; 1.10, 0.40, −0.65 |
| 0.55 back at rest | 0, 0, 0; 0, 0, 0 | 0, 0, 0; 0, 0, 0 |

The CHOPPER is swung flat across the front, muzzle to the left, receiver and butt leading; both hands stay on it.
The NINE is thrown one-handed, butt first with the muzzle up: the support hand lets go for the strike (weight
`min(ease(t / 0.08), ease((0.55 − t) / 0.16))`, `src/weapon/nine.js:253-256`). On contact with an enemy or a wall:
recoil back + 1.4 m/s (enemy) or + 0.9 m/s (wall), bump roll + 0.8 rad/s (`src/weapon/viewmodel.js:707-712`).
Sounds: `whoosh` at the start, `melee_thud` on an enemy (`src/audio/react.js:95-98`).

**Named finger poses** (`src/weapon/handling.js:87-112`): `relaxed`, `fist`, `rifleGrip` (index straight along the
frame), `rifleTrigger`, `rifleSupport` (cupping the handguard from below), `magHold` (around a rifle magazine),
`hook` (two fingers over the charging handle), `pistolGrip`, `pistolTrigger`, `pistolThumbDown` (thumb on the
magazine button or slide stop), `pistolSupport` (wrapped over the firing hand), `magPinch` (a pistol magazine
between thumb and fingers), `palm` (open hand, heel forward). Each is four fingers × [knuckle curl, middle curl, tip
curl, spread] plus the thumb [toward the palm, down, twist, curl, tip curl], in radians.

**Hand positions at rest** (gun space, mm: s forward, x right, y up; palm centre, press direction, finger direction):

| Hand | CHOPPER | NINE |
|---|---|---|
| Right (firing) | palm at s 40, x 14.5, y −85 on the right face of the pistol grip, pressing left, fingers running forward and down (`src/weapon/chopper.js:226`) | palm at s 14, x 13.5, y −78, pressing left, fingers forward (`src/weapon/nine.js:156`) |
| Left (support) | palm at s 315, x −10, y −61.5 under the handguard, pressing up, fingers wrapping to the right (`src/weapon/chopper.js:228`) | palm at s 24, x −16.5, y −90 over the firing hand's fingers, pressing right (`src/weapon/nine.js:160`) |

### 3.18 Edge cases worth keeping, or changing on purpose

- A reload cancelled after `magIn` keeps the rounds. A strike right after `magIn` therefore skips the rest of the
  reload: the gun fires again at 1.44 + 0.55 = 1.99 s instead of 2.24 / 2.72 s (CHOPPER), and at 1.68 s instead of
  1.90 s on the NINE's empty reload **(derived)**.
- The player can strike through `playerOnly` geometry (the Cage's chain-link) while a Goon's pipe cannot
  (`docs/CONTRACT.md:503-504`).
- The chain rule ignores walls; blast damage does not.
- An explosive's collider (1.6 m for the rack) is taller than its model (1.52 m); rounds that pass just over the
  cylinders still hit it.
- A melee strike resolves against the aim 0.16 s after the press, not at the press.
- The air spread penalty is not reduced by aiming; the crouch bonus disappears when fully aimed.
- The barrel-smoke trigger tests "a round was fired less than 0.02 s ago" once per frame, so it only fires above
  about 50 frames a second (`src/weapon/viewmodel.js:396`). Port it as "on a round, if heat > 0.4".
- Rays ignore a box that contains their origin, so a player pressed into geometry can shoot out of it.
- `weapon.spread` is never reset, only damped. During a switch it follows the old gun's cone while holstering and
  the new gun's (with zero bloom) while drawing, and has converged by the time the new gun may fire.

### 3.19 Stubs

`src/stubs/weapon.js` and `src/stubs/explosives.js` are the fallbacks the build uses when the real module is missing
or throws. They differ on purpose (CHOPPER only, the strike resolves at the press, ammunition moves at the end of
the reload, a dry pull reloads at once, no bloom, no recoil; chain fuse 0.14…0.44 s without the distance term, blast
damage costs hit points). **Do not port them.**

---------------------------------------------------------------------------------------------------

## 4. Unreal mapping

### 4.1 Axes, units, rotations

| Web | Unreal |
|---|---|
| World (x, y, z) m | (X, Y, Z) = (x, z, y) × 100 cm |
| View space (x right, y up, z toward the viewer) m | camera space (X forward, Y right, Z up) = (−z, x, y) × 100 cm |
| Gun space (s forward, x right, y up) | mesh space (X, Y, Z) = (s, x, y) × 100 cm; Blender (s, −x, y) m |
| Gun pitch, yaw, roll (rad, order yaw → pitch → roll) | `FRotator(Pitch, Yaw, Roll)` = (pitch, −yaw, −roll) in degrees: same order, pitch up is positive in both, yaw and roll change sign |
| World yaw about +Y | Unreal yaw = −web yaw in degrees |
| Speeds m/s, accelerations m/s² | × 100 |
| Spring `[w, z]`, `damp` rates, times | unchanged |

### 4.2 Converted gameplay values

| Value | Web | Unreal |
|---|---|---|
| Range, CHOPPER / NINE | 300 / 120 m | 30 000 / 12 000 cm |
| Spread, CHOPPER hip / aimed / move hip / move aimed / bloom hip / bloom aimed / air / crouch | 0.0125 / 0.0012 / 0.013 / 0.004 / 0.0065 / 0.0022 / 0.022 / 0.002 rad | 0.716° / 0.069° / 0.745° / 0.229° / 0.372° / 0.126° / 1.261° / 0.115° |
| Spread, NINE, same order | 0.0105 / 0.0017 / 0.0065 / 0.003 / 0.0085 / 0.003 / 0.018 / 0.002 rad | 0.602° / 0.097° / 0.372° / 0.172° / 0.487° / 0.172° / 1.031° / 0.115° |
| Movement speed for the full penalty | 6 m/s | 600 cm/s |
| Camera kick, CHOPPER: pitch; early yaw; weave; weave noise | 0.0068; ± 0.0011; 0.0042; ± 0.001 rad | 0.390°; ± 0.063°; 0.241°; ± 0.057° |
| Camera kick, NINE: pitch; yaw | 0.0092; ± 0.0025 rad | 0.527°; ± 0.143° |
| Recoverable offset clamp | 0.30 / 0.20 rad | 17.19° pitch / 11.46° yaw |
| Melee reach; cone | 2.3 m; 0.8727 rad | 230 cm; 50° (25° half-angle) |
| Wall pull-back, CHOPPER / NINE | 1.05 → 0.42 m / 0.80 → 0.32 m | 105 → 42 cm / 80 → 32 cm |
| Aim-assist range | 60 m | 6 000 cm |
| Gunfire heard within | 45 m | 4 500 cm |
| Tracer: speed; streak; width; no tracer under; hidden start | 260 m/s; 5.72 m; 0.035 m; 0.9 m; 1.1 m (paths over 3.3 m) | 26 000 cm/s; 572 cm; 3.5 cm; 90 cm; 110 cm (paths over 330 cm) |
| Casing ejection, camera space | right 2.0…3.2, up 1.2…2.0, forward ± 0.5 m/s | Y 200…320, Z 120…200, X ± 50 cm/s |
| Player target cylinder | r 0.38 m, h 1.8 / 1.15 m | r 38 cm, h 180 / 115 cm |
| Goon head; body; Buzzard | r 0.155 m at 1.62 m; r 0.27 m; 0.5 × 0.22 m | r 15.5 cm at 162 cm; r 27 cm; 50 × 22 cm half extents |
| Propane tank: radius; chain range; collider | 6.5 m; 5.24 m; 0.32 × 0.6 × 0.32 m | 650 cm; 524 cm; 32 × 32 × 60 cm (X × Y × Z) |
| Welding rack: radius; chain range; collider | 7.5 m; 5.88 m; 0.9 × 1.6 × 0.5 m | 750 cm; 588 cm; 90 × 50 × 160 cm (X × Y × Z) |
| Chain fuse | 0.14 + [0, 0.3) + 0.03 s per m | 0.14 + [0, 0.3) + 0.0003 s per cm |
| Blast shake reach; blast alert | 28 m; 60 m | 2 800 cm; 6 000 cm |
| Dropped gun: velocity (camera space); spin; gravity | 0.7 right, 1.1 up, 1.3 forward m/s; 5.5 rad/s; 13.5 m/s² | Y 70, Z 110, X 130 cm/s; 315°/s; 1 350 cm/s² |
| Field of view, vertical → horizontal at 16:9 | 74° default, 52° aimed, 54° viewmodel, + 6° sprinting | 106.5°, 81.9°, 84.3°, 112.3° **(derived)** |

### 4.3 Converted viewmodel poses

Position of the mesh origin in camera space (X forward, Y right, Z up, cm) and `FRotator` (Pitch, Yaw, Roll,
degrees), valid for a viewmodel drawn at 84.3° horizontal (54° vertical) field of view.

| Pose | CHOPPER location | CHOPPER rotator | NINE location | NINE rotator |
|---|---|---|---|---|
| Hip 1 "Close" | 24, 15, −9 | 2.86, −16.04, 20.05 | 36, 10.5, −5.6 | 4.01, −6.30, 10.31 |
| Hip 2 "Three-quarter" | 30, 17, −12 | 2.29, −12.61, 17.19 | 44, 10, −7.5 | 3.44, −6.30, 11.46 |
| Hip 3 "Compact" | 25, 12, −8.5 | 2.86, −13.75, 17.19 | 33, 7.5, −5.5 | 4.01, −8.59, 9.17 |
| Sprint | 27, 5, −20 | −18.33, −45.84, 17.19 | 30, 5, −20 | −34.38, −34.38, 11.46 |
| Reload | 31, 5, −10.5 | 22.92, −19.48, 31.51 | 33, 3, −8.5 | 28.65, −18.33, 28.65 |
| Wall | 14, 9, −15 | 35.52, −6.88, 5.73 | 24, 7, −13 | 42.97, −5.73, 0 |
| Holster | 20, 20, −46 | −31.51, −14.32, 25.78 | 24, 17, −44 | −34.38, −11.46, 22.92 |
| Aim | 13.65, 0, −5.55 | 0, 0, 0 | 35.75, 0, −1.85 | 0, 0, 0 |

Strike keys in the same convention (location offset cm; rotator offset degrees about the recoil pivot):

| t (s) | CHOPPER | NINE |
|---|---|---|
| 0.08 | −7, 5, −2; 4.58, 17.19, −8.59 | −6, 4, 5; 31.51, 14.32, −20.05 |
| 0.16 | 20, −13, 5; −10.31, −68.75, 28.65 | 15, −10, 2; 60.16, −20.05, 34.38 |
| 0.27 | 16, −14, 3; −13.75, −74.48, 31.51 | 13, −11, 0; 63.03, −22.92, 37.24 |

Sockets (mesh space, cm): CHOPPER `Muzzle` 49.75, 0, 0; `Eject` 15, 1.9, 1.8; `SightRear` 2.35, 0, 5.55;
`RecoilPivot` −2, 0, −3; `MagHinge` 22.2, 0, −4. NINE `Muzzle` 20.1, 0, 0; `Eject` 10.5, 1.2, 1.4; `SightRear`
1.25, 0, 1.85; `RecoilPivot` −3, 0, −8.5. Kick impulses: m/s × 100 for the three translations, rad/s × 57.296 for
the three rotations (CHOPPER: back 82 cm/s, rise 85.9°/s, yaw ± 27.2°/s, roll ± 48.7°/s, up 11 cm/s, side ± 9 cm/s;
NINE: 55 cm/s, 366.7°/s, ± 37.2°/s, ± 65.9°/s, 20 cm/s, ± 10 cm/s).

### 4.4 Mechanic → Unreal feature

| Mechanic | Natural Unreal Engine 5 home | Notes |
|---|---|---|
| Tuning tables | One data asset per gun plus one for the shared rules, or a data table filled from the config dump that `tools/ue-export` writes into `unreal/MurderInc/Content/Data/` | Keep the web names so the numbers can be diffed against `src/config/weapons.js`. The NINE's infinite reserve travels in that dump as the string `Infinity` (`tools/ue-export/lib/collect.cjs:16-17`): read it as "unlimited" |
| The rules (3.1–3.11) | A weapon component on the player character, ticked after the character's movement and camera update | Port `logic.js` as written: a tick with accumulators, not timers. The 3-rounds-per-frame catch-up and the 1 ms credit are what make 720 rpm exact |
| Input | Enhanced Input actions Fire, Aim, Reload, Swap, Weapon1, Weapon2, Melee | Fire needs both "is down" and "pressed this frame"; a press and release inside one frame must still read as down for one frame (`docs/CONTRACT.md:419`) |
| Hitscan | A line trace on a dedicated weapon trace channel (called `Bullet` below; the "weapon traces" of spec 01, 4.4) from the camera location | World geometry blocks it; "player-only" blockers (invisible walls, chain-link, shoot-through glass, railings) block the pawn but ignore `Bullet`; bullet-only blockers do the reverse. No penetration, one trace per round |
| Enemy hit shapes | Collision bodies on the enemy that answer only to `Bullet`: a head sphere and a body capsule on the Goon's skeleton, one flattened body on the Buzzard | Read the head from the hit body or bone name; multiply by 2.2 |
| Surfaces | Physical materials on the hit result, one per web surface name (2.8) | Drives impact effects, decals and sounds |
| Damage and events | A damage interface on enemies, player and explosives, plus multicast delegates named after the web events | The HUD, audio and score listen to the delegates exactly as the web modules listen to the events |
| Spread | A random unit vector in a cone around the aim from a seeded random stream | The web version is uniform over the disc `tan(spread)`; `VRandCone` differs by less than 0.1 % at these angles |
| Camera recoil | The permanent 35 % goes into the control rotation; the recoverable 65 % is an offset held by the camera manager (or a camera modifier) and **also** added to the aim used for the trace | Shake must stay out of the aim |
| Camera shake | A trauma-driven camera shake pattern | Owned by the player spec |
| Aim | The aim amount 0…1 lives on the weapon component; the camera manager reads it for field of view and look rate | |
| Viewmodel | Skeletal meshes for the two guns and the arms on a first-person camera, with the first-person rendering primitives of recent UE 5 releases (own field of view, no clipping into walls), or a separate viewmodel pass | The poses of 4.3 assume 84.3° horizontal. The wall pull-back pose stays even if clipping is solved by the renderer |
| Procedural layers | An Animation Blueprint: base poses as pose assets blended by the weapon component's values; sway, bob, inertia, landing and recoil as an additive transform on the weapon / hand IK root computed in native code with the exact spring step of `src/weapon/springs.js` | Keep springs analytic; a per-frame Euler spring will change the feel with frame rate |
| Reload, strike, holster, draw | Montages authored to the timelines of 3.17 and started by the rules | Gameplay moments (`magin`, the blow at 0.16 s, `done`) are fired by the rules' own timers, never by anim notifies; notifies are for sound and for attaching the magazine to the hand |
| Hands | Two-bone IK from the shoulders to hand targets that are sockets on the gun (grip, support) or camera-space points (pouch) | The web game has no upper arm; build real arms |
| Muzzle flash | A Niagara system on the `Muzzle` socket (first-person only) plus a short point light | Re-tune intensity by eye: three.js units do not transfer |
| Tracer | A Niagara beam or ribbon from the on-screen muzzle to the trace end, head speed 26 000 cm/s, length 572 cm | Start it at the muzzle as seen through the viewmodel's field of view (3.16) |
| Casings | Niagara mesh particles with collision, or pooled rigid bodies | Emit a bounce event per surface for the sound |
| Melee | An overlap around the camera filtered by reach, cone and a `Bullet` line-of-sight trace | 3.11 |
| Explosives | An actor per prop: intact mesh, wreck mesh, a box collider that blocks pawn and `Bullet`, hit points, a fuse, a Niagara jet at the hit point, an audio component for the hiss | 21 actors need no instancing |
| Blast | A native loop over enemies, the player and explosives as in 3.13 | `ApplyRadialDamageWithFalloff` is close but uses other target points and has no player share |
| Chain | A global explosion delegate; each explosive within range sets its fuse | No line of sight |
| Dropped gun on death | Detach the gun mesh and let it simulate as a rigid body | |
| Gamepad rumble | Force-feedback effects per round and per strike | Strong = large motors, weak = small |
| Gunfire noise | Report a noise event at the muzzle, at most one per 0.3 s | Owned by the AI spec |
| Aim slow-down | Scale look input in the player controller | Pad only |

**First-person rendering requirements** (this spec owns them; spec 01 only fixes the camera). Whatever route the
engine version allows, the result must match the web game on four points: (1) the guns and arms are projected with
a 54° vertical field of view (84.3° horizontal at 16:9) while the world uses the player's setting, and the vertical
value is the one kept when the aspect ratio changes (the web game only zooms both cameras out below 4:3:
`docs/CONTRACT.md:799-801`); (2) they are drawn over the world and never intersect it; (3)
they are lit by the place the player stands in, sun and shade included, with reflections that show sky, street and
the El; (4) anything spawned in the world from a point on the gun (tracer start, casing, muzzle light, the
`weapon:fire` position) starts where that point appears on screen, which means re-projecting it with the factor
`tan(worldFov / 2) / tan(viewmodelFov / 2)` on the two screen axes (3.16).

### 4.5 Animation set to author

Suggested set, lengths fixed by the rules (first-person arms and gun together; names are suggestions):

| Clip | Length | Marks |
|---|---|---|
| `A_FP_Chopper_ReloadTactical` | 2.24 s | 0.40 magazine out, 0.80 fresh magazine, 1.15 touch, 1.44 seated, 1.565 tug, 1.89–1.98 press check |
| `A_FP_Chopper_ReloadEmpty` | 2.72 s | as above to 1.565, then 1.96–2.07 rack, 2.155 release |
| `A_FP_Nine_ReloadTactical` | 1.50 s | 0.18 magazine drops, 0.48 fresh magazine, 0.90 touch, 1.13 seated |
| `A_FP_Nine_ReloadEmpty` | 1.90 s | as above, slide locked back from the start, 1.61 slide release |
| `A_FP_<Gun>_Holster`, `A_FP_<Gun>_Draw` | 0.28 s, 0.32 s | the gun must be out of frame at the change-over |
| `A_FP_Chopper_Melee`, `A_FP_Nine_Melee` | 0.55 s | 0.08 wound up, 0.16 contact, 0.27 end of follow-through |
| `A_FP_<Gun>_Fire` (or springs only) | about 0.2–0.3 s | bolt 0.020 + 0.045 s, slide 0.018 + 0.042 s |
| `A_FP_Nine_SlideLock` pose, `A_FP_<Gun>_DryFire` | pose, about 0.3 s | |
| Pose assets per gun | — | Hip × 3, Sprint, Reload (only if the reload is kept procedural), Wall, Aim, Holster |

### 4.6 Parity checks for the rebuilt rules

The web game's own unit tests state the behaviour to reproduce (`test/weapon-logic.test.js`, `test/combat.test.js`,
`test/fx-explosives.test.js`; 42 tests, all passing on this checkout). The ones worth porting as automated tests:

- Holding fire empties the CHOPPER's 30 rounds in 2.4167 s at 30, 60 and 144 frames a second alike; a single frame
  never fires more than 3 rounds.
- The NINE fires one round per press, never on a hold, at most one every 0.1429 s; a press 0.1 s before the cooldown
  ends still fires.
- A tactical CHOPPER reload emits `start`, `magout` at 0.40, `magin` at 1.44, `bolt` at 1.89, `done` at 2.24; the
  magazine count changes at `magin`. Empty: `bolt` at 1.96, `done` at 2.72. NINE: 0.18, 1.13, no `bolt`, 1.50; empty
  `bolt` at 1.61, `done` at 1.90.
- A strike before `magin` leaves the ammunition unchanged; after it, the rounds are in the gun.
- A dry pull clicks once and the reload starts 0.32 s (CHOPPER) or 0.28 s (NINE) later; an emptied magazine alone
  never reloads.
- A switch takes 0.28 + 0.32 s, keeps both magazines, and reverses in proportion when asked back mid-way.
- The strike resolves at 0.16 s, ends at 0.55 s, and a second one is refused until 0.75 s after the first began.
- Spread at rest, moving at 6 m/s, in the air, crouched, aimed, and after 1 to 10 rounds matches 3.5.
- An enemy behind cover is never hit; a Goon's head takes × 2.2; an enemy round never hits another enemy.
- A propane tank lit by one round blows after 1.6 s; two CHOPPER rounds pop it 0.06 s after the second; a welding
  rack takes three; an enemy round always does 9.
- A blast does `damage × (1 − distance / radius)` to an enemy in the open, nothing behind a wall, half of that to
  the player; an explosive 3 m away is lit with a fuse between 0.23 and 0.53 s even behind a wall.
- After wave 2, 4, 6 … of Hold the Block every explosive is back; after odd waves none are.

---------------------------------------------------------------------------------------------------

## 5. Art and audio implications

### 5.1 What must be built

The asset briefs of this spec are in `docs/unreal/spec/assets/weapons.json` (10 briefs): the CHOPPER and its
magazine, the NINE and its magazine, the two casings, Rule's arms with gloves, the watch, the bracelet, and the
muzzle-flash cards. The propane tank, the welding rack and their two wrecks are briefed once only, in
`docs/unreal/spec/assets/props.json` (ids `gameplay_propane_tank`, `gameplay_propane_tank_wreck`,
`gameplay_welding_rack`, `gameplay_welding_rack_wreck`), because the props spec owns every catalogue prop; 5.7 says
what the explosive rules need from those four meshes. The originals are low-polygon stand-ins painted per vertex;
the rebuild models the real object each one stands for, at the dimensions below, with no maker's marks (the game
shows no real brands: `docs/DESIGN.md:27`).

All dimensions in 5.2 and 5.3 are gun space in millimetres: `s` forward from the origin, `y` up from the bore axis,
widths across the gun (centred unless a side is named).

### 5.2 The CHOPPER (`src/weapon/chopper.js:1-4`)

A compact wood-and-steel automatic carbine of the Kalashnikov pattern in its shortest form: stamped receiver with a
ribbed top cover, laminated-wood handguard and pistol grip, a curved 30-round magazine, a stubby flared muzzle
booster, and an under-folding stock tucked along the receiver. Overall **(measured)**: 502 mm long (stock folded),
292 mm high (magazine floor to front-sight ears), 46 mm wide at the body and 65 mm with the charging handle.
Two details are deliberately not like the real pattern and matter to the animation: the **charging handle and the
selector are on the left side**, "where the shooter can see it", with the ejection port on the right.

| Part | Along the bore (s) | Height (y) | Width | Surface | Notes | Source |
|---|---|---|---|---|---|---|
| Receiver | −4 … 256 | −40 … 12 | 32 | blued steel | stamped box, lower front corner cut from (238, −40) to (256, −27), 1.2 mm worn chamfers | `src/weapon/chopper.js:56-59` |
| Rivets and pins | 7 places | | r 2.2 | dark steel | at (s, y) 12, 1; 30, −30; 84, −13; 112, −21; 226, −6; 242, −16; 228, −27 | `src/weapon/chopper.js:61-63` |
| Top cover | 2 … 186 | 12 … 34 | 29 → 32.5 | blued steel, slightly darker | half-round stamping; three raised ribs at s 56, 102, 148 (8 mm long, 0.8 mm proud) | `src/weapon/chopper.js:66-70` |
| Accessory rail on the cover | 62 … 168 | 32.5 … 41.8 | 16.4 base, 20.8 lugs | dark steel | 10 lugs, 5.6 mm long at 10.5 mm pitch; stays under the sight line | `src/weapon/chopper.js:72-73` |
| Stamped panel over the magazine well | 168 … 236 | −36 … −12 | 1.4 proud, both sides | blued steel | rounded rectangle; three trunnion rivets r 1.9 beside it | `src/weapon/chopper.js:75-77` |
| Charging-handle slot (left) | 78 … 192 | 12 … 17 | on the left face | black | | `src/weapon/chopper.js:80` |
| Ejection port (right) | 112 … 190 | 12.2 … 23.5 | on the right face | black, bolt carrier inside | | `src/weapon/chopper.js:81` |
| Sight block (rear trunnion) | 186 … 256 | 12 … 32 | 30 | blued steel | rounded top corners, cross pin r 3 at (222, 22) | `src/weapon/chopper.js:84-85` |
| Rear sight | 10 … 36 base; leaf at 21.5 … 25.5 | base 33 … 39.8; leaf to 51.3; ears to 55.5 | base 16, leaf 16.4 | dark steel | square notch 4.4 wide × 4.2 deep; two white dots 2.4 mm at x ± 4.4 on the rear face | `src/weapon/chopper.js:88-94` |
| Lower handguard | 250 … 385 | −42 … −4 | 40 → 46 → 41 | varnished laminate | three dark cooling slots per side at s 283, 318, 353 (22 × 6.4) | `src/weapon/chopper.js:97-98`, `src/weapon/chopper.js:102-103` |
| Upper handguard | 262 … 372 | 4 … 33 | 31 → 34 | varnished laminate | two round vents per side at s 295, 340 (r 3.6) | `src/weapon/chopper.js:99-100`, `src/weapon/chopper.js:104` |
| Retaining band | 385 … 392.5 | −43.5 … 34 | 45 | blued steel | | `src/weapon/chopper.js:107` |
| Barrel | 250 … 432 | | r 8.5, r 7.5 from 392.5 | dark steel | shows between the handguard halves | `src/weapon/chopper.js:110` |
| Gas tube | 255 … 396 | axis at 19 | r 6.5 | dark steel | | `src/weapon/chopper.js:111` |
| Gas block and front-sight base | 392.5 … 426 | −14 … 30 | 22 | blued steel | | `src/weapon/chopper.js:112` |
| Front-sight ears | 398 … 420 | 30 … 63 | two plates 2 mm thick at x ± 9.8 | dark steel | rounded tops | `src/weapon/chopper.js:113-114` |
| Front post | at 409 | 30 … 55.5 | r 1.4 → 1.2 | dark steel | white strip 1.6 wide on its rear face, y 47.5 … 55.3 | `src/weapon/chopper.js:115-116` |
| Muzzle booster | 426 … 497.5 | | r 9.5 neck, r 12.8 body with a groove at 468 … 473, flaring to r 16.2 at the mouth | blued steel, black inside | bore r 7 … 7.8 | `src/weapon/chopper.js:119-128` |
| Pistol grip | 70 → 27 (raked back) | −34 … −148 | 27.5 … 30.5, 40 → 47 deep | varnished laminate | grip screw r 2.8 at the bottom | `src/weapon/chopper.js:131-141` |
| Trigger guard | 88 … 156 | −40 … −79 | 14 | blued steel | a bent strip about 2.5 thick; opening s 90.5 … 153 × y −76.5 … −40 | `src/weapon/chopper.js:144-147` |
| Magazine catch | 150 … 157 | −63 … −40 | 12 | dark steel | paddle between the guard and the magazine | `src/weapon/chopper.js:148` |
| Selector lever (left) | 72 … 110 | −31 … −18 | 2.4 thick on the left face | dark steel | pivot boss r 3.6 at (78, −22.5) | `src/weapon/chopper.js:149-150` |
| Folding stock arms | 14 … 236 | −14 falling to −55.5 | two flat arms 3 thick at x ± 18.8 | blued steel | pivot r 6.2 at (22, −22), front pin r 4.2 at (236, −49.5) | `src/weapon/chopper.js:153-156` |
| Butt plate (folded under the handguard) | 234 … 337 | −60.5 … −52.5 | 34 | blued steel | small hook at the front end | `src/weapon/chopper.js:157` |
| **Bolt carrier** (moves 92 back) | 118 … 188 | 12.5 … 22.5 | seen through the port | bare brushed steel | | `src/weapon/chopper.js:165` |
| **Charging handle** (moves with the carrier) | at 180 | axis at 14.5 | stem r 4.2 from x −15 to −30; knob r 6 from x −28 to −42 | dark steel, two bright rings | on the left | `src/weapon/chopper.js:166-169` |
| **Trigger** | pivot at 108 | pivot at −38, 30 long | 6 | dark steel | turns 0.34 rad | `src/weapon/chopper.js:172-176`, `src/weapon/chopper.js:215` |
| **Magazine** (separate, rides in the hand) | 160 … 312 | −229 … −21 | 25.5 body, 27.8 floor plate | blued steel, darker floor plate | follows an arc of radius 260 over 0.8 rad; body 62 → 59 deep; side rib, spine, four stamped cross ribs | `src/weapon/chopper.js:20-26`, `src/weapon/chopper.js:179-190` |
| **Top round** (child of the magazine) | 172 … 222 | axis at −19.5 | r 5.6 case, 50 long | brass case, copper bullet | shown when the magazine holds rounds | `src/weapon/chopper.js:193-195` |

Surface colours as painted in the original (base colour, roughness, metalness; `src/weapon/chopper.js:36-48`): blued
steel `#5a5e65` 0.36 / 0.9 with edges worn to `#9aa0a8`; cover `#53565c`; dark steel `#3c3e43`; bare steel
`#b1b6bd` brushed; laminate `#55301c` 0.36 / 0 (red-brown, a soft gloss); magazine `#45484e`; black `#050506`; brass
`#caa23d`; copper `#b5683a`; sight dots `#f2f0e4`, self-lit at 0.55.

### 5.3 The NINE (`src/weapon/nine.js:1-2`)

A full-size, hammer-fired 9 mm service pistol in two tones: brushed stainless slide over a black frame, black
checkered grip panels, an exposed hammer, three-dot sights, a railed dust cover, and gold on the trigger and the
magazine base. Overall **(measured)**: 234 mm long (muzzle to the back of the grip), 153 mm high, 31 mm wide.

| Part | Along the bore (s) | Height (y) | Width | Surface | Notes | Source |
|---|---|---|---|---|---|---|
| Frame | −33 … 196 | −128 … −13.5 | 24.5, 2.2 mm bevels | blued black steel | dust cover to s 196 (lower edge −30), trigger guard down to −71.5 with an opening s 73 … 123.5 × y −66 … −40, front strap raked from (66, −60) to (41, −128), butt at −128, beavertail at (−18, −24.5) | `src/weapon/nine.js:38-58` |
| Accessory rail | three lugs at 142, 156, 170 (6 long) | −33.5 … −30 | 17 | as the frame | | `src/weapon/nine.js:60` |
| Recoil-spring guide | 120 … 198.5 | axis at −8.8 | r 3.6 | brushed steel | shows under the barrel at the muzzle | `src/weapon/nine.js:62` |
| Grip panels | −27 … 57 | −122 … −40 | 3.4 thick at x ± 13.4 | black checkered | two screws per side at (4, −52), (12, −112) | `src/weapon/nine.js:65-70` |
| Hammer, cocked | −15.5 … −3 | −12 … 10.5 | 7.5 | dark steel | spur up and back | `src/weapon/nine.js:73` |
| Slide stop (left) | 58 … 100 | −16.5 … −10.5 | 2.2 thick | dark steel | thumbed in the empty reload | `src/weapon/nine.js:74` |
| Thumb safety (left) | 4 … 30 | −12.5 … −4.5 | 3 thick | dark steel | | `src/weapon/nine.js:75` |
| Magazine button (left) | at 62.5 | at −40.5 | r 4.2 | dark steel | thumbed at the start of every reload | `src/weapon/nine.js:76` |
| **Slide** (moves 44 back) | 0 … 196 | −13.5 … 12.5 | 27, 2.6 mm bevels | brushed stainless | rounded top edges, chamfered nose | `src/weapon/nine.js:82-86` |
| Cocking serrations | 7 … 38 | −10.5 … 7.5 | both sides | cut into the slide | 7 grooves 2 wide at 4.8 pitch | `src/weapon/nine.js:88-91` |
| Ejection port | 86 … 126 | 4.5 … 12.7 | top right | black, barrel hood inside (89 … 123, polished) | | `src/weapon/nine.js:93-94` |
| Rear sight | 7 … 18 | 12.4 … 18.5 | 17 | dark steel | notch 4.2 wide × 3.9 deep; two white dots 2.2 mm at x ± 5.2 | `src/weapon/nine.js:96-99` |
| Front sight | 178 … 190 at the base, 183.5 … 188.5 at the top | 12.4 … 18.5 | 3.4 | dark steel | one white dot 2.2 wide on its rear face | `src/weapon/nine.js:100-101` |
| **Barrel** (tilts) | 50 … 201 | | r 6.8, bore r 4.4 … 4.6 | polished steel, black inside | stands 5 mm proud of the slide's nose | `src/weapon/nine.js:103-105` |
| **Trigger** | pivot at 91 | pivot at −31, 29 long | 6.8 | gold | turns 0.30 rad | `src/weapon/nine.js:108-112`, `src/weapon/nine.js:148` |
| **Magazine** (separate) | −18 … 40 body | −127.5 … −37 | 19.5 | brushed steel | raked with the grip; three witness holes per side at y −60, −78, −96 | `src/weapon/nine.js:115-119` |
| Magazine base pad | −30 … 46 | −134.5 … −127.5 | 26.2 | gold | rounded | `src/weapon/nine.js:120` |
| **Top round** (child of the magazine) | 4 … 34 | axis at −33.5 | r 4.8 case, 30 long | brass, copper | | `src/weapon/nine.js:121-123` |

Surface colours (`src/weapon/nine.js:20-32`): slide `#aeb1b6` brushed, 0.4 / 1; frame `#34363b` 0.42 / 0.85 with
edges worn to `#8a9098`; grips `#1c1c1f` 0.72 / 0; dark parts `#3c3e43`; barrel `#bbbec4` 0.22 / 1; gold `#e7b53a`
0.24 / 1 (the catalogue's gold, `src/config/catalog.js:33`); steel `#9da1a7`; black `#040405`; sight dots `#f2f0e4`
self-lit at 0.5.

### 5.4 Rule's arms, gloves, watch, bracelet (`src/weapon/arms.js`)

Two bare, brown forearms and two gloved hands. The original stops at the elbow end of the forearm; the rebuild
should model the arm past the elbow so no cut end can show. Right-hand bind pose: wrist at the origin, fingers
forward, back of the hand up, thumb on the inner side; the left arm is the mirror image (`src/weapon/arms.js:5-6`).
Dimensions in mm.

| Part | Dimensions | Surface | Source |
|---|---|---|---|
| Forearm | drawn 370 long from the wrist; oval sections 100 × 92 at the elbow end, 99 × 89 at 240, 90 × 77 at 160, 72 × 58 at 90, 61 × 46 at 45, 58 × 40 at the wrist | bare skin, effective colour `#684029` **(derived)** from the catalogue skin `#7a4a2e` mixed 35 % toward `#5b3b2b` and darkened × 0.85; roughness 0.56–0.62, slightly lighter on the inside | `src/weapon/arms.js:258-272`, `src/weapon/arms.js:706`, `src/weapon/arms.js:291` |
| Hand | 205 from the wrist to the middle fingertip; 74 wide at the heel, 88 at the knuckles | glove | `src/weapon/arms.js:20-34`, `src/weapon/arms.js:267-271` |
| Fingers (knuckle, middle, tip segment lengths; radius) | index 44, 26, 22, r 9.3; middle 49, 30, 23, r 9.7; ring 45, 28, 22, r 9.1; little 35, 20, 19, r 8.0; each tapers to 82 % | glove, creased at the joints | `src/weapon/arms.js:23-24`, `src/weapon/arms.js:389-443` |
| Thumb | segments 44, 34, 28; r 13.2 tapering to 82 %; root 27 inside, 11 below and 27 ahead of the wrist | glove | `src/weapon/arms.js:25-31`, `src/weapon/arms.js:443` |
| Glove body | covers the hand to 30 above the wrist; black synthetic leather `#1e1f22`, roughness 0.68; palm side in synthetic suede `#2a2724`, roughness up to 0.80 | | `src/weapon/arms.js:274`, `src/weapon/arms.js:292`, `src/weapon/arms.js:707-708` |
| Cuff | a padded band from 4 to 42 above the wrist, 1.6–3.6 proud, with a rolled edge (37–42.5, up to 4.2 proud) in the seam colour `#3c3e43` | | `src/weapon/arms.js:330-333` |
| Wrist strap | across the back of the wrist at 22: 40 long × 24 wide × 3.4 thick, moulded rubber `#18181b`, on a stitched plate 43 × 26.5 | | `src/weapon/arms.js:334-350` |
| Back-of-hand panel | a raised stitched panel from the wrist to 64 ahead of it, 52 % (at the wrist) to 66 % of the hand's width, 4.2 high, a shade lighter than the glove, with a seam-coloured rim 3.6 wider | | `src/weapon/arms.js:353-364` |
| Knuckle guard | a moulded bar across the knuckles (84 ahead of the wrist): 86 long, 20 wide (14 at the ends), 4.8 high, rubber `#18181b`, roughness 0.42, with one dome per knuckle (radius 1.2 × the finger's, flattened) | | `src/weapon/arms.js:367-386` |
| Fingertip pads | a grip pad on the inside of every last segment, rubber, roughness 0.7 | | `src/weapon/arms.js:429-436` |
| **Watch**, left forearm | centred 72 above the wrist, clear of the cuff. Bracelet-style band 19 wide, 3.4 proud of the skin, brushed gold with three darker link lines. Round case on the back of the forearm: 39 across, 8.5 high; bezel 42.4 across; black gloss dial 34.4 across; four gold batons at 12, 3, 6, 9; two gold hands (12 and 9 long); crown r 2.8 | gold `#e7b53a`, metalness 1, roughness 0.2–0.3; dial `#0a0a0c`, roughness 0.1 | `src/weapon/arms.js:448-471`, `src/weapon/arms.js:716` |
| **Bracelet**, right forearm | a heavy curb chain 70 above the wrist: 26 overlapping links of 5.6 mm wire, hanging loose 3.6 clear of the arm and sagging 2.8 underneath; alternate links raised and a shade darker | gold `#e7b53a` and `#cfa233` | `src/weapon/arms.js:472-489`, `src/weapon/arms.js:715` |

Skeleton of the original, per arm: forearm, hand, three bones per finger and thumb (17 bones); pose = 21 angles
(`src/weapon/arms.js:36-43`). The jewellery is rigid on the forearm bone.

### 5.5 Sight alignment

The aim pose is defined by the sights, so the rebuilt meshes must keep these relations exactly or the aim pose must
be recomputed from the new sockets: the rear-sight socket goes to the camera axis at the relief distance (16 cm
CHOPPER, 37 cm NINE), the bore parallel to the view axis, the front-sight tip at the same height over the bore as
the rear notch (55.5 mm and 18.5 mm). Nothing may rise above the sight line between the two sights (the CHOPPER's
rail tops out at 41.8 mm, 13.7 mm below it). The white dots face the shooter and are faintly self-lit so the sight
picture reads at night.

### 5.6 Surfaces and textures

The original uses one vertex-painted material with procedural finishes (`src/weapon/material.js:37-78`). They say
what the texture artist should deliver:

| Finish | Look |
|---|---|
| Blued steel | a slow mottle in tone and gloss with faint machining lines along the bore; chamfered edges worn to bright steel |
| Brushed steel | streaks running the length of the part |
| Laminated wood | long grain along the bore with darker late-wood lines and a few pores, under a soft varnish |
| Grip checkering | a diagonal diamond grid, about 2.4 mm across flats, pressed in |
| Glove | synthetic leather with a faint weave and a slow sheen variation; suede palm; rubber pads |
| Skin | soft mottling so large areas are not one flat tone |

Undersides are baked darker and tops lighter in the original (`src/weapon/build.js:127-135`); bake real ambient
occlusion instead. Texture sets by the shared naming: `T_Chopper_*`, `T_Nine_*`, `T_RuleArms_*` (`_BC`, `_N`, `_ORM`,
and `_E` for the sight dots), material slots `M_Chopper`, `M_Nine`, `M_RuleArms`. The gun is seen from 15 to 60 cm:
budget texel density for that distance.

### 5.7 Explosive props (`src/props/gameplay.js:316-403`)

**Propane tank**: a refillable steel LPG cylinder of the barbecue kind. Modelled extent 304 mm across and 585 mm
high; collider 320 × 320 × 600. Parts: dark steel foot ring (r 105–125, 45 high); white body (r 152 from 110 to 330
high, domed bottom); red shoulder (330 to 470); a white collar guard (r 100, 450 to 585 high) open at two hand
holes; a brass valve with a side outlet and a red hand wheel (r 40) inside the collar; a flammable-gas diamond
(130 × 130: red diamond, white flame, the class number 2) on the front and the back at 215 high
(`src/props/atlas.js:702-731`). Colours: white `#e6e4dc`, red `#b3261e`, brass `#b58a3a`, steel `#2a2d31`, soot
`#0c0b0a` (`src/props/gameplay.js:255-261`). Wreck: only a scorched, tilted foot ring and a bent plate remain.

**Welding rack**: an oxy-acetylene bottle cart. Collider 900 × 500 × 1600 (the model reaches 1518 at the top of the
regulator gauges, the cylinder caps 1502). Parts: a
steel base plate 900 × 500 × 40; a back frame of two 40 mm posts 1300 high and three cross rails at 500, 1000 and
1320; a retaining chain across the front at 820; two green oxygen cylinders (230 across, 1420 high, `#2f6b4f`) and
one maroon acetylene cylinder (280 across, 1120 high, `#7a1a1a`), each with a rounded shoulder, a brass valve and a
steel cap; a brass regulator with two white-faced gauges on the middle oxygen cylinder and on the acetylene one;
twin hoses (red and green, 22 mm) looped over the frame and down the back; a brass torch hung on the frame; a white
placard 380 × 270 at 500 high on the front reading DANGER / FLAMMABLE GAS / NO SMOKING / NO OPEN FLAME under a red
header (`src/props/atlas.js:733-740`). Wreck: the scorched base plate and two bent posts.

What the rules need from these meshes: three states, intact, lit (the same mesh with the shell glowing with heat,
emissive `#b8400f`, so the material needs a heat mask or parameter) and gone (the wreck mesh, no collision); a
simple box collider of exactly the size above, pivot at the centre of the footprint on the ground, the long side of
the rack along the local X of the web prop; and a surface a jet of flame can start from anywhere. The wrecks must
stay low and inside the footprint: once the collider is gone, players and Goons walk through that spot.

### 5.8 Effects to author

| Effect | Brief |
|---|---|
| First-person muzzle flash | a star seen from behind plus a forward jet; 0.036–0.056 s; CHOPPER 20 cm star and 34 cm jet, NINE 12 cm and a faint 13 cm jet; smaller when aimed; must read against sunlit walls |
| Muzzle sparks and world light | a few sparks ahead of the muzzle; a warm light for 0.05 s |
| Tracer | warm white-gold `#ffe2a8`, hot white head, 5.7 m streak at 260 m/s, on every round; a faint smoke thread on the first metres now and then (`src/fx.js:388-413`) |
| Casings | rifle and pistol brass (`#c9a24a`), tumbling, up to 4 bounces, staying on the ground (pool of 60) |
| Barrel smoke | thin pale wisps for 1.6 s after a long CHOPPER burst |
| Jet of flame | a roaring gas jet for the length of the fuse, at the bullet hole or the valve |
| Explosion | scaled by radius (6.5 m = 1): fireball, smoke column, scorch mark, smouldering site, screen flash when close (`src/fx.js:618-627`, `docs/CONTRACT.md:553-555`) |
| Impacts and decals | one set per surface name; owned by the effects spec |

### 5.9 Audio to record or design

Triggered by this subsystem (`src/audio/react.js:35-110`, `src/audio/react.js:139-159`,
`src/audio/react.js:238-248`):

| Cue | When | Notes |
|---|---|---|
| `chopper_shot`, `nine_shot` | every round | non-spatial |
| `chopper_tail_out` / `_in`, `nine_tail_out` / `_in` | every round | street and interior tails, cross-faded by how far inside the shop the player is; in a burst only the last tail rings out fully |
| `dry_fire` | dry click | pitched × 1.2 for the NINE |
| `cloth` | reload start and end | |
| `rifle_magout`, `rifle_magin`, `rifle_bolt` | CHOPPER reload marks | the bolt cue serves both the press check and the full rack |
| `pistol_magout`, `pistol_magin`, `pistol_slide` | NINE reload marks | |
| `holster`, `draw` | switch phases | pitched up for the NINE |
| `whoosh`, `melee_thud` | strike start; blow on an enemy | |
| `brass_asphalt`, `brass_metal` | casing bounce | pitched × 1.22 for pistol brass, quieter on soft ground |
| `hit_confirm`, `hit_head`, `kill_confirm` | `player:hitEnemy` | non-spatial feedback |
| `imp_concrete`, `imp_brick`, `imp_metal`, `imp_car`, `imp_glass`, `imp_wood`, `imp_dirt`, `imp_flesh`, `imp_drone`, `ricochet` | `impact` | ricochet chance by surface: metal 24 %, car 12 %, concrete 7 %, brick 5 %, asphalt 5 % |
| `hiss` (loop) | a lit explosive | volume 0.25 → 1 over the fuse |
| `explosion_big`, `explosion_small` | `explosion` | also muffles the mix when close and dips the music |

Shots duck the music and the mix briefly; these behaviours belong to the audio spec.

---------------------------------------------------------------------------------------------------

## 6. Open questions and risks

1. **Left-side charging handle and selector on the CHOPPER.** The original puts both on the left so the player sees
   them and the left hand can rack the handle. The real pattern has them on the right. Keep the fiction (and the
   reload choreography of 3.17) or model the real layout and re-choreograph the rack?
2. **No idle inspect exists.** `inspectAfter: 24` is the only trace of one. Should the rebuild add an inspect after
   24 s of idling, or leave it out as the web game does?
3. **Reload cancel shortcut** (3.18): a strike after `magIn` skips up to 0.73 s of the CHOPPER's empty reload. Keep
   as a skill move or close it?
4. **Draw timing.** The gun is visually up after 0.14 s but cannot fire until 0.32 s. Author the draw to fill the
   whole 0.32 s (the comment's intent, with a small overshoot), or keep the early arrival?
5. **Viewmodel field of view and pass.** All poses assume a 54° vertical viewmodel drawn over the world. The Unreal
   route (first-person rendering primitives or a separate pass) depends on the engine version chosen for the
   project; with any other field of view the poses of 4.3 must be re-tuned on screen
   (`docs/DESIGN.md:292-295` gives the framing: about 40–45 % of the width, 40 % of the height).
6. **Strike through chain-link.** The player's strike ignores `playerOnly` geometry; the Goon's pipe does not.
   Intended, or should both use the movement test?
7. **Chain through walls** and the rack collider being 8 cm taller than its model: keep both as they are, or fit
   the collider to the new mesh and give the chain a line-of-sight test? A line-of-sight test would stop three of
   the four pairs of 2.10 from rippling.
8. **Tracers on every round** read as arcade in daylight, but that is what the web game does and the design asks
   that tracers stay visible against bright walls (`docs/DESIGN.md:287-288`). Confirm.
9. **Effective range.** 300 m and 120 m both exceed the block (92 × 68 m) with no falloff: range is never felt.
   Confirm that no falloff is wanted in the rebuild.
10. **Light and effect intensities** (muzzle light 45 / 30, flash brightness, emissive values) are three.js numbers
    and must be re-tuned by eye in Unreal.
11. **Three gravities.** The dropped gun falls at 13.5 m/s², casings at 9.81, the player at 21. A physics-driven
    port will use one unless overridden; the difference is cosmetic.
12. **Determinism.** Spread and recoil draw from a seeded stream so runs repeat under the test harness. Decide
    whether the Unreal build needs that (a seeded `FRandomStream`) or not.
13. **Timing ownership.** If reload or strike moments are ever driven by animation notifies instead of the rules'
    timers, blending and frame drops will move gameplay. Keep the rules authoritative.
14. **Real-pattern fidelity versus "no real brands".** The modellers need real reference for a photoreal carbine
    and pistol, yet the result must carry no maker's marks or trade dress that identifies a product.
