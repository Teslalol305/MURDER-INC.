# 01 — Player: movement, camera, input, health

Port spec for the Unreal Engine 5 rebuild of MURDER INC. The web game is the ground truth. Everything below was read
from the source files listed in 2.1. Values marked **(measured)** are not typed anywhere in the source: they were
obtained by running the game's own `src/player.js` and `src/physics.js` headless in node (the same harness shape as
`test/input-player-player.test.js`, 60 steps per second unless stated), and, where the level is involved, on the 777
colliders of the real build (`G.physics.boxes` after boot).

How to read this document:

- Web units are metres, seconds and radians. +Y is up, north is −Z, east is +X. Yaw 0 looks toward −Z and grows
  turning **left** (counter-clockwise seen from above); pitch grows looking **up**; the camera uses rotation order
  YXZ (yaw, then pitch, then roll); forward = (−sin yaw, 0, −cos yaw) (`docs/CONTRACT.md:20`, `src/player.js:15`).
  A positive camera roll tilts the head to the **left**. Section 4 gives the Unreal values (cm, cm/s, degrees).
- The player's position `pos` is the point between his feet. `eye` is the camera position.
- `damp(x, target, rate, dt)` = `target + (x − target) · e^(−rate · dt)`: an exponential approach that covers 90 % of
  the way in 2.3 / rate seconds (`src/core/util.js:25`). `expDecay(x, rate, dt)` = `x · e^(−rate · dt)`
  (`src/core/util.js:32`). `moveToward(x, target, step)` is a linear approach that never overshoots
  (`src/core/util.js:57`). `smoothstep(a, b, x)` is the cubic 0…1 step `3t² − 2t³` (`src/core/util.js:35`),
  `smootherstep` the quintic one (`src/core/util.js:41`). `lerp(a, b, t)` = `a + (b − a) · t`.
- "ads" is the aim amount 0…1 (0 = hip, 1 = fully aimed down the sights). The weapon module writes it every frame.
- Neighbouring specs in this folder: `02-weapons-combat.md` (who produces the aim amount and the recoil kicks, the
  first-person weapon), `03-enemies.md` (what shoots at the player, how the nav grid is used), `07-ui-audio.md` (HUD
  and sound). "The level spec" and "the flow spec" below mean the documents that cover the block and the game flow.

---------------------------------------------------------------------------------------------------

## 1. Overview

The player is Ja Rule ("Rule"), seen only in first person and never heard. This subsystem is his body, his eyes and
his hands on the controls. The body is an upright cylinder 0.64 m across and 1.80 m tall (1.15 m crouched) that walks
at 3.8 m/s, sprints at 6.4 m/s, crouch-walks at 1.9 m/s, jumps exactly one metre high, steps up kerbs and stairs of up
to 0.42 m without leaving the ground, slides along walls, and cannot climb, mantle, lean, slide or go prone. Speed
changes are quick and linear (no friction, no momentum games): full walk speed in 0.11 s, a dead stop in 0.15 s. The
camera sits at 1.68 m (1.05 m crouched) and carries a stack of small procedural motions: a stride bob timed to the
footsteps, a lean into strafes, a spring dip on landing, a glide over stair steps, weapon recoil that kicks the view
and partly recovers, a trauma-based shake for hits, blasts and the train overhead, a field of view that widens 6° in a
sprint and narrows to 52° when aiming, and a 0.85 s collapse onto the pavement on death. Health is 100 points with no
armour; it comes back by itself after a quiet spell whose length and rate depend on the difficulty, the screen edges
flash red on every hit and the picture drains and pulses when health is low. Input is one set of twelve actions fed by
keyboard and mouse, a gamepad or touch controls, with the active device switching on use; the gamepad gets a response
curve, a turn boost and a mild aim slow-down over enemies, and the browser version has a fallback for when the mouse
cannot be captured. Underneath sits a deliberately simple collision world: axis-aligned boxes over a flat ground
plane, which also answers every bullet ray and builds the enemies' navigation grid.

---------------------------------------------------------------------------------------------------

## 2. Facts

### 2.1 Source map

| File | Lines | What it holds |
|---|---|---|
| `src/config/player.js` | 376 | All player and input tuning: body, speeds, acceleration, jump, sprint, stride, look, field of view, health, fall, bob, recoil, shake, death, device look rates, gamepad, rumble, key / button maps, glyphs, touch buttons, hint copy |
| `src/player.js` | 699 | The controller: movement decisions, health, every camera layer, events; pure helpers `targetSpeed`, `sprintWanted`, `approachVelocity`, `createRecoil`, `createShake`, `createSpring` |
| `src/physics.js` | 1046 | The collision world: box list, rays, line of sight, `moveCapsule`, ground and overlap queries, the nav grid and A* |
| `src/input.js` | 1259 | Devices → actions: keyboard, mouse, pointer lock and its fallback, touch controls, gamepad (curve, boost, aim slow-down, rumble, menu navigation) |
| `src/core/settings.js` | 126 | Persisted user settings: sensitivity, invert Y, field of view (and others) |
| `src/stubs/player.js`, `src/stubs/input.js` | 316, 245 | The smallest correct implementations of the two contracts (see 3.19) |
| `src/config/flow.js`, `src/game.js` | 225, 957 | Regeneration per difficulty, when the player is enabled / invulnerable, death and pause flow |
| `src/combat.js`, `src/config/enemies.js`, `src/enemies/bolts.js`, `src/enemies/goon.js`, `src/explosives.js` | — | How damage reaches the player (hit volumes and amounts) |
| `src/weapon/logic.js`, `src/config/weapons.js` | 661, 210 | Who writes the aim amount, calls `addRecoil` / `addShake`, and the gamepad aim slow-down |
| `src/render.js`, `src/config/look.js` | 1032, 377 | Camera objects, narrow-screen zoom, the screen feedback driven by `render.post.damage / lowHealth / ads` |
| `test/input-player-player.test.js`, `test/input-player-input.test.js` | 861, 1383 | Executable statements of most numbers below |

The player reads its tuning as `{...config group}` once at creation (`src/player.js:202-217`); nothing overrides the
file at run time except the values in 2.2.

### 2.2 Values that are overridden at run time (effective values)

| Value | Config default | Effective value | Where |
|---|---|---|---|
| `player.regen.delay`, `player.regen.rate` | 5.5 s, 16 HP/s (`src/config/player.js:85-86`) | per difficulty, table 2.10; written on every run reset and difficulty change | `src/game.js:178-179`, `src/config/flow.js:103,115,127` |
| base field of view | 74° (`src/config/player.js:71`) | the user setting `fov` (60…95, integer, default 74), then clamped to 55…100 by `setFov` | `src/core/settings.js:12,33`, `src/player.js:394-396,681-685` |
| `input.sensitivity`, `input.invertY` | 1, false | user settings `sens` (0.2…3, default 1) and `invertY` | `src/core/settings.js:9-10,30-31`, `src/input.js:1167-1174` |
| `player.invulnerable` | false | true from reaching the truck until the next reset; true every frame with URL `?god=1` | `src/game.js:664`, `src/main.js:279`, `src/player.js:223,350` |
| `player.enabled` | true | false on the title screen and after mission complete; true in intro, playing, paused, dead | `src/game.js:143-148` |

### 2.3 Body and stances (`src/config/player.js`, line in the last column)

| Constant | Value | Unit | Meaning | Line |
|---|---|---|---|---|
| `body.radius` | 0.32 | m | radius of the collision cylinder (diameter 0.64) | :6 |
| `body.height` | 1.80 | m | standing collision height, feet to top | :7 |
| `body.crouchHeight` | 1.15 | m | crouched collision height (the top comes down, the feet stay) | :8 |
| `body.eye` | 1.68 | m | standing eye height above the feet | :9 |
| `body.crouchEye` | 1.05 | m | crouched eye height | :10 |
| `body.eyeRate` | 11 | 1/s | `damp` rate of the eye height between stances (90 % in 0.21 s) | :11 |
| `body.boundsMargin` | 0.4 | m | the body centre is kept this far inside the play bounds | :14 |
| `body.standClearance` | 0.05 | m | the headroom test for standing up starts this far under the crouched top | :15 |
| `body.footprint` | 0.9 | × radius | radius used by that headroom test (0.288 m) | :16 |
| `body.headClearance` | 0.07 | m | bob and landing spring may never lift the eye closer than this to the top of the body | :17 |
| death capsule | 0.6 | m | collision height of the body once dead (`death.capsuleHeight`) | :154 |

There are two stances, standing and crouching. There is no prone, lean, slide, mantle, ladder or swim.

| | Standing | Crouching |
|---|---|---|
| Collision height / eye height | 1.80 m / 1.68 m | 1.15 m / 1.05 m |
| Top speed | 3.8 m/s walk, 6.4 m/s sprint | 1.9 m/s, no sprint |
| Stride per footstep | 1.55 m walk, 2.1 m sprint | 1.05 m |
| View bob scale | 1 (× 1.9 sprinting) | 0.7 |
| Bullet hit cylinder (2.14) | r 0.38 m × 1.80 m | r 0.38 m × 1.15 m |
| Passes under an obstacle whose underside is at least **(measured)** | 1.80 m above the feet | 1.15 m above the feet |

### 2.4 Speeds, acceleration, jump, sprint (`src/config/player.js`)

| Constant | Value | Unit | Meaning | Line |
|---|---|---|---|---|
| `speed.walk` | 3.8 | m/s | standing, any direction (no strafe penalty) | :22 |
| `speed.sprint` | 6.4 | m/s | sprinting; unlimited (no stamina) | :23 |
| `speed.crouch` | 1.9 | m/s | crouching | :24 |
| `speed.ads` | 2.4 | m/s | cap at full aim; blended by the aim amount | :25 |
| `speed.backpedal` | 0.82 | × | multiplier at full backward input, blended by how far back the input points | :26 |
| `speed.moving` | 0.3 | m/s | below this the player counts as standing still (stride, footsteps) | :27 |
| `accel.ground` | 34 | m/s² | rate the velocity moves toward the wish velocity, grounded with input | :32 |
| `accel.groundStop` | 26 | m/s² | grounded without input (the only "friction") | :33 |
| `accel.air` | 9 | m/s² | airborne with input | :34 |
| `accel.airStop` | 0.6 | m/s² | airborne without input (momentum is kept) | :35 |
| `jump.gravity` | 21 | m/s² | gravity for the player (2.14 × Earth's) | :39 |
| `jump.apex` | 1.0 | m | jump height; take-off speed = √(2 · 21 · 1.0) = 6.4807 m/s (`src/player.js:34,220`) | :40 |
| `jump.coyote` | 0.12 | s | a jump is still allowed this long after leaving the ground without jumping | :41 |
| `jump.buffer` | 0.13 | s | a jump press is remembered this long | :42 |
| `jump.terminal` | 40 | m/s | fall speed cap | :43 |
| `sprint.minForward` | 0.55 | — | forward input must exceed this | :48 |
| `sprint.maxStrafe` | 0.6 | — | absolute strafe input must be below this | :49 |
| `sprint.maxAds` | 0.35 | — | aim amount must be below this | :50 |
| `sprint.minSpeedFrac` | 0.6 | × walk | the `sprinting` flag turns on above 2.28 m/s | :51 |
| `stride.walk / sprint / crouch` | 1.55 / 2.1 / 1.05 | m | distance per footstep | :56-58 |
| `stride.settleRate` | 10 | 1/s | standing still, the stride phase eases to the nearest footfall | :59 |
| `stride.afterLanding` | 0.72 | stride | phase set on landing: the next footstep comes 0.28 stride later | :60 |

Derived: 0 → walk 0.112 s, 0 → sprint 0.188 s, walk → stop 0.146 s (0.28 m), sprint → stop 0.246 s (0.79 m),
full reverse at walk speed 0.224 s, 0 → walk in the air 0.42 s. Jump air time on flat ground 0.617 s. Footstep cadence
2.45 /s walking, 3.05 /s sprinting, 1.81 /s crouching, 1.55 /s walking while aimed.

### 2.5 Look and field of view (`src/config/player.js`)

| Constant | Value | Unit | Meaning | Line |
|---|---|---|---|---|
| `look.pitchLimit` | 1.5 | rad (85.94°) | clamp of the aim pitch, up and down | :64 |
| `look.viewPitchLimit` | 1.55 | rad (88.81°) | clamp of aim pitch + recoil offset | :65 |
| `look.adsScale` | 0.6 | × | look-rate multiplier at full aim, every device, both weapons | :66 |
| `fov.base` | 74 | ° vertical | default of the user setting | :71 |
| `fov.min / max` | 55 / 100 | ° | clamp inside `setFov` (the settings UI offers 60…95, step 1: `src/ui/panel.js:14`) | :72-73 |
| `fov.sprintAdd` | 6 | ° | added while the `sprinting` flag is on | :74 |
| `fov.ads` | 52 | ° vertical | field of view at full aim, same for both weapons and any base setting | :75 |
| `fov.rate` | 7 | 1/s | `damp` rate of the field of view normally | :76 |
| `fov.rateAds` | 30 | 1/s | `damp` rate while the aim amount is strictly between 0.02 and 0.98 | :77-78 |
| `fov.viewmodel` | 54 | ° vertical | fixed field of view of the first-person weapon camera (`src/render.js:423`) | :79 |
| world camera | near 0.08, far 700 | m | clip planes (`src/render.js:417`) | — |
| weapon camera | near 0.01, far 10 | m | (`src/render.js:423`) | — |

All fields of view are **vertical** (three.js convention). Below a 4:3 aspect both cameras zoom out so the horizontal
view never drops under what 4:3 shows, up to a vertical field of view of 105° (`src/render.js:43-44,342-346,826`).
Aim times belong to the weapon: 0.18 s Chopper, 0.14 s Nine (`src/config/weapons.js:14,96`).

### 2.6 View bob, lean, landing spring, stair glide (`src/config/player.js`)

| Constant | Value | Unit | Meaning | Line |
|---|---|---|---|---|
| `bob.rate` | 9 | 1/s | `damp` rate of the bob amplitude | :105 |
| `bob.vertical` | 0.024 | m | vertical bob amplitude at walk speed (one cycle per footstep) | :106 |
| `bob.lateral` | 0.013 | m | sideways bob amplitude (one cycle per two footsteps) | :107 |
| `bob.rollFromLateral` | 0.35 | rad/m | camera roll per metre of sideways bob | :108 |
| `bob.sprintScale / crouchScale / adsScale` | 1.9 / 0.7 / 0.22 | × | amplitude multipliers (aim blends 1 → 0.22) | :109-111 |
| `bob.strafeRoll` | 0.02 | rad (1.15°) | lean at a sideways speed of 6.4 m/s (0.68° at walk speed) | :112 |
| `bob.strafeRollRate` | 8 | 1/s | `damp` rate of the lean | :113 |
| `bob.strafeRollAds` | 0.4 | × | lean multiplier at full aim | :114 |
| `bob.spring.stiffness / damping` | 150 / 17 | 1/s², 1/s | landing spring on a vertical eye offset (ω 12.25 rad/s, damping ratio 0.69) | :115 |
| `bob.spring.min / max` | −0.2 / +0.05 | m | hard stops of that offset | :115 |
| `bob.spring.pitch` | 0.12 | rad/m | camera pitch per metre of spring offset (a dip looks down) | :115 |
| `bob.step.frequency` | 24 | rad/s | critically damped spring that glides the eye over steps (0 = off) | :119 |
| `bob.step.max` | 0.5 | m | the eye never lags further than this behind a step | :119 |
| `fall.landMinAir` | 0.12 | s | shorter air time than this is not a landing | :93 |
| `fall.dipPerSpeed / dipMax` | 0.36 / 3.2 | —, m/s | landing impulse into the spring = −min(speed · 0.36, 3.2) m/s | :99-100 |
| spring integration step | 1/120 | s | longest sub-step of both springs (`src/player.js:27`) | — |

### 2.7 Camera recoil (`src/config/player.js`)

| Constant | Value | Unit | Meaning | Line |
|---|---|---|---|---|
| `recoil.keep` | 0.35 | share | of every kick added permanently to the aim (yaw / pitch) | :124 |
| `recoil.maxPitch` | 0.3 | rad (17.19°) | clamp of the recoverable offset | :125 |
| `recoil.maxYaw` | 0.2 | rad (11.46°) | same, sideways | :126 |
| `recoil.chase` | 34 | 1/s | `damp` rate at which the view snaps onto the offset (90 % in 0.068 s) | :127 |
| `recoil.hold` | 0.09 | s | after the last shot before the offset starts to recentre | :128 |
| `recoil.recover` | 6.5 | 1/s | exponential decay of the offset after the hold (half-life 0.107 s) | :129 |

Kick sizes are the weapon's (`src/config/weapons.js:41-52,121-126`): per round the Chopper asks for 0.0068 rad of
pitch × a random 0.85…1.15, the Nine for 0.0092 rad × 0.9…1.1, each × `lerp(1, 0.55, ads)` and × 0.85 when crouched
(`src/weapon/logic.js:482-495`, `src/config/weapons.js:181-182`). Details are in the weapons spec.

### 2.8 Screen shake (`src/config/player.js`)

| Constant | Value | Unit | Meaning | Line |
|---|---|---|---|---|
| `shake.decay` | 1.7 | trauma/s | linear decay of the trauma value (0…1) | :133 |
| `shake.pitch / yaw / roll` | 0.03 / 0.03 / 0.045 | rad | amplitude per sine at trauma 1 (two sines per axis: peaks 3.44°, 3.44°, 5.16°) | :134-136 |
| `shake.freq.pitch` | 43, 72 | rad/s | 6.84 Hz and 11.46 Hz | :138 |
| `shake.freq.yaw` | 37, 84 | rad/s | 5.89 Hz and 13.37 Hz | :138 |
| `shake.freq.roll` | 30, 61 | rad/s | 4.77 Hz and 9.71 Hz | :138 |
| `shake.onHit` | 0.22 + damage / 70 | trauma | added per hit taken | :139 |
| `shake.onBlast` | range 28 m, 0.15 + 0.9 · near², × 0.6 for a `small` blast | trauma | per `explosion` event, near = 1 − distance / 28 | :140 |
| `shake.sustain.below` | 0.03 | trauma | an `addShake` call smaller than this is a trickle (a rate, not an impulse) | :143 |
| `shake.sustain.max / rate` | 0.6 / 6 | trauma, 1/s | cap and ease rate of the level a trickle holds | :143 |
| `fall.shakeFrom / shakePerSpeed / shakeMax` | 7.5 / 0.06 / 0.5 | m/s, per m/s, trauma | landing shake = min(0.5, (speed − 7.5) · 0.06) | :96-98 |

Every source of shake (all go through `player.addShake` or the two internal paths):

| Source | Trauma | Where |
|---|---|---|
| Damage taken | 0.22 + amount / 70 (a 6-point round 0.31, a 22-point pipe 0.53, 55 or more = 1) | `src/player.js:355` |
| Hard landing | min(0.5, (landing speed − 7.5) · 0.06); a flat jump (6.5 m/s) gives none | `src/player.js:598` |
| Any explosion (event) | at least (0.15 + 0.9 · (1 − d / 28)²) × (0.6 if small), d from the eye; raises, never stacks | `src/player.js:689-694,433-436` |
| Propane tank / welding rack | adds 0.15 + 0.9 · (1 − d / 28)² itself; does not stack with the row above | `src/explosives.js:27,419-423` |
| Own shot | Chopper 0.12, Nine 0.14 per round × `lerp(1, 0.55, ads)` × (0.85 crouched) | `src/weapon/logic.js:496`, `src/config/weapons.js:51,125` |
| Melee strike landing | 0.22 on a body, 0.11 on a wall | `src/weapon/logic.js:407`, `src/config/weapons.js:167` |
| Reel secured | 0.18 | `src/game.js:606`, `src/config/flow.js:47` |
| El train overhead | a trickle of 0.42 trauma/s × proximity (holds trauma ≈ 0.25 right under it) | `src/atmos/train.js:366-371`, `src/config/look.js:270-271` |

### 2.9 Health, feedback, fall, death (`src/config/player.js`)

| Constant | Value | Unit | Meaning | Line |
|---|---|---|---|---|
| `health.max` | 100 | HP | maximum and starting health; no armour, no shields | :84 |
| `health.lowWarning` | 30 | HP | first time below this in a run: the radio line "You're hit bad…" (`src/game.js:864-867`) | :87 |
| `health.hurtPulse` | 0.35 + damage / 40, decay 1.9 /s | 0…1 | red flash value written to `render.post.damage` | :88 |
| `health.lowHealth` | from 0.55 to 0.12, rate 4 | fraction, 1/s | health fraction → `render.post.lowHealth` (0 at 55 % or more, 1 at 12 % or less, smoothstep between) | :89 |
| `fall.damageFrom` | 13 | m/s | landing speed above which a fall hurts (a drop of about 4.0 m) | :94 |
| `fall.damagePerSpeed` | 7 | HP per m/s | damage = (speed − 13) · 7 | :95 |
| `death.collapse` | 0.85 | s | time for the camera to reach the floor | :147 |
| `death.eye` | 0.22 | m | final eye height | :148 |
| `death.eyeRate` | 18 | 1/s | `damp` rate of the eye toward its falling target | :149 |
| `death.roll` | 1.15 | rad (65.89°) | final roll, onto the shoulder away from the shot | :150 |
| `death.pitch / pitchBounce` | −0.25 / 0.12 | rad (−14.32° / 6.88°) | final downward pitch and the nod on the way | :151-152 |
| `death.slide` | 5 | 1/s | exponential decay of the body's horizontal speed | :153 |
| fall-out limit | −30 | m | feet below this (or a non-finite position): back to the last ground stood on (`src/player.js:29,587-592`) | — |

Screen feedback strengths, applied by the grade pass from the two values above (`src/config/look.js:25-35`,
`src/render.js:122-139`): hit flash = red tint (linear RGB 0.30, 0.008, 0.006) on the screen border up to 85 % opacity
plus 50 % desaturation at `post.damage` 1; low health = up to 65 % desaturation, + 0.55 vignette and a red border rim
of up to 55 % that pulses at 5 rad/s (0.8 Hz) between half and full strength; aiming adds 0.22 vignette × ads. Death
drives saturation to 0.12 and a 55 % darkening (`src/config/flow.js:24`, eased at rates 2.2 and 1.4 by the game).
Audio: a heartbeat loop below 35 % health, louder and up to 35 % faster down to 10 % (`src/audio/react.js:350-365`).

### 2.10 Regeneration per difficulty (effective; `src/config/flow.js:101-138`)

| Difficulty (display name) | Delay after the last damage | Rate | 1 HP → 100 HP takes |
|---|---|---|---|
| `hustler` (Hustler) | 4 s | 25 HP/s | 4 + 3.96 s |
| `boss` (Boss, the default: `src/config/flow.js:4`) | 5.5 s | 16 HP/s | 5.5 + 6.19 s |
| `kingpin` (Kingpin) | 7 s | 10 HP/s | 7 + 9.9 s |

Hold the Block also heals 35 HP when a wave is cleared (`src/config/flow.js:166`, `src/game.js:700`).

### 2.11 Device look rates and gamepad handling (`src/config/player.js`)

| Constant | Value | Unit | Meaning | Line |
|---|---|---|---|---|
| `input.mouse` | 0.0021 | rad per pixel (0.1203°) | × sensitivity; 2 992 pixels per full turn at sensitivity 1 | :161 |
| `input.mouseGlitch` | 400 | pixels | a single mouse event larger than this on either axis is discarded | :162 |
| `input.mouseWake` | 4 | pixels per frame | mouse travel that makes keyboard + mouse the active device again | :163 |
| `input.touch` | 0.0052 | rad per CSS pixel (0.2979°) | × sensitivity, look finger and FIRE-button finger | :164 |
| `input.keyYaw / keyPitch` | 2.1 / 1.26 | rad/s (120.3 / 72.2 °/s) | arrow keys and I J K L; not scaled by sensitivity or invert | :172-173 |
| `input.edgeYaw / edgePitch` | 2.4 / 1.2 | rad/s (137.5 / 68.8 °/s) | fallback edge turning, × sensitivity | :174-175 |
| `input.edgeZoneX / edgeZoneY` | 0.12 / 0.10 | of the width / height | edge zones of that fallback | :176-177 |
| `input.lockTimeout` | 1.2 | s | wait for a pointer-lock grant before falling back | :178 |
| `input.lockRetries` | 3 | clicks | refused clicks after which the fallback stops asking for the lock | :179 |
| `input.wheelDebounce` | 0.28 | s | at most one weapon swap per this long from the wheel | :180 |
| `pad.deadzone` | 0.14 | — | **axial** dead zone on each stick axis, rescaled to 0…1 beyond it (`src/input.js:56-61`) | :182 |
| `pad.trigger` | 0.35 | — | a trigger (any analog button) counts as pressed above this | :183 |
| `pad.yaw` | 2.9 | rad/s (166.2 °/s) | full yaw rate of the right stick at sensitivity 1 | :184 |
| `pad.pitchScale` | 0.62 | × | pitch rate relative to yaw (103.0 °/s) | :185 |
| `pad.curve` | 0.25, 0.75 | — | rate share = 0.25 · m + 0.75 · m³ of the stick magnitude m | :186 |
| `pad.boost` | 1.75 | × | extra turn rate that builds while the stick is at the rim (290.8 °/s) | :187 |
| `pad.boostFrom / boostTime / boostDecay` | 0.92 / 0.45 / 0.17 | —, s, s | magnitude that counts as "at the rim", build time 0 → 1, decay time 1 → 0 | :188-190 |
| `pad.sprintForward` | 0.55 | — | the sprint latch lets go when the stick's forward value drops below this | :191 |
| `pad.aimSlow` | 0.55 | × | look-rate multiplier with an enemy under the crosshair | :192 |
| `pad.aimRange / aimEvery / aimRate` | 60 / 0.05 / 14 | m, s, 1/s | reach of that test, how often it runs, `damp` rate of the multiplier | :193-195 |
| `pad.nav` | stick 0.6, first 0.38, repeat 0.17 | —, s, s | menu navigation threshold and key repeat | :197 |
| `rumble.hit` | strong min(1, 0.45 + damage / 30), weak 0.3, 160 ms | — | dual-rumble on every hit taken | :201 |
| `rumble.blast` | range 22 m, size small 1 / big 1.2, weak × 0.8, 240 ms + 200 ms × strength | — | dual-rumble for explosions by distance | :202 |

### 2.12 Actions and default bindings

Twelve public actions (`docs/CONTRACT.md:385`) plus the internal movement and key-turn ones. Sources:
`src/config/player.js:226-256` (keys), `:259` (mouse), `:207-223` (gamepad, W3C standard mapping indices),
`:316-327` (touch buttons); wheel `src/input.js:508-517`; L3 and X `src/input.js:918-932`.

| Action | Keyboard + mouse | Gamepad | Touch | Kind |
|---|---|---|---|---|
| move | W / S / A / D | left stick (axes 0, 1) | floating stick on the left 45 % of the screen | analog; half deflection = half speed |
| look | mouse; arrows or I / J / K / L at a fixed rate | right stick (axes 2, 3) | drag anywhere else; dragging on FIRE also looks | — |
| `fire` | left mouse (0); Enter, Numpad Enter | RT (7) | FIRE, and a second smaller FIRE on the left | hold |
| `ads` | right mouse (2) | LT (6) | AIM | hold; **toggle** on touch |
| `jump` | Space | A (0) | JUMP | press (buffered 0.13 s, never repeats while held) |
| `sprint` | Left Shift, Right Shift | L3 (10), **latched** | stick pushed fully forward; sprint-lock arrow | hold; latch on gamepad |
| `crouch` | C | B (1), LB (4) | DUCK | hold; **toggle** on touch |
| `reload` | R | X (2) while no prompt shows | RLD | press |
| `interact` | E | X (2) while an interaction prompt shows | USE (only visible with a prompt) | hold (2.4 s grab, flow spec) |
| `swap` | Q; mouse wheel either way | Y (3), D-pad up (12), D-pad down (13) | SWAP | press |
| `weapon1` | 1, Numpad 1 | D-pad left (14) | tap on the HUD's weapon slot | press |
| `weapon2` | 2, Numpad 2 | D-pad right (15) | tap on the HUD's weapon slot | press |
| `melee` | F, V; middle mouse (1) | RB (5), R3 (11) | HIT | press |
| `pause` | Esc, P | Start (9) | pause disc (or the HUD's own) | press; the only action that works in menus |

Not bound: gamepad Back / View (8) and Guide (16), mouse buttons above 2 (swallowed so "back" cannot leave the page).
Ctrl is deliberately not crouch (Ctrl + W closes a browser tab: `src/config/player.js:234`). Tab is swallowed during
play. Glyphs shown in prompts per device are data (`src/config/player.js:265-309`): keyboard `LMB RMB SPACE SHIFT C R E
Q 1 2 F ESC`, gamepad `RT LT A L3 B X X Y ← → RB START`, touch `FIRE AIM JUMP STICK DUCK RLD USE SWAP SWAP SWAP HIT II`;
keyboard letters follow the printed layout where the browser can tell (AZERTY shows A for swap).

### 2.13 Physics constants (`src/physics.js`)

| Constant | Value | Unit | Meaning | Line |
|---|---|---|---|---|
| `STEP_HEIGHT` | 0.42 | m | tallest ledge a grounded body walks up, and the furthest it snaps down | :21 |
| `AIR_STEP` | 0.08 | m | ledge tolerance while airborne | :22 |
| `SUBSTEP` | 0.6 | × radius | longest horizontal sub-step (0.192 m for the player) | :23 |
| `PUSH_ITERATIONS` | 3 | — | push-out passes per sub-step | :24 |
| `FOOTPRINT` | 0.7 | × radius | half-size of the square under the body that finds its floor (0.224 m) | :25 |
| `LOS_SLACK` | 0.05 | m | `lineOfSight` stops this short of the far point | :26 |
| ground surface default | `asphalt` | — | when the level has no opinion (`level.groundSurfaceAt` decides otherwise) | :27 |
| `SLICE_THRESHOLD / SLICE_MAX / SLICE_SHRINK` | 0.2 / 10 / 0.86 | — | rotated boxes: sliced when abs(sin 2·yaw) > 0.2, into at most 10 pieces, each AABB shrunk to 86 % | :29-31 |
| default play bounds | x −46…46, z −34…34 | m | set again by the level (`src/level/layout.js:21`, `src/level.js:172`) | :62 |
| ray reach default | 500 | m | `raycast(origin, dir, maxDist = 500)` | :305 |
| `NAV_CELL` | 0.5 | m | nav grid cell | :33 |
| `NAV_INFLATE` | 0.5 | m | obstacles grow by this before stamping (body radius + clearance) | :34 |
| `NAV_BAND_MIN / MAX` | 0.47 / 1.5 | m | a box blocks the grid only if its top is at least 0.47 m and its underside at most 1.5 m | :35-36 |
| `NAV_SNAP_RINGS` | 12 | cells | how far a blocked start or goal looks for a free cell (6 m) | :37 |
| `NAV_MIN_EXPANSIONS` | 9000 | cells | A* budget (or half the grid if larger) | :38 |
| `NAV_RANDOM_TRIES` | 24 | — | tries of `randomPoint` | :39 |

Box flags (`src/physics.js:8-10,42-43,91-92`): `bulletOnly` = hit by rays, ignored by movement and nav;
`playerOnly` = blocks body movement, ignored by rays and nav; `noNav` = not stamped into the nav grid. Each box also
carries a `surface` name (default `concrete`), a `tag` and an optional `owner`. The ground is the implicit plane
y = 0, infinite, hit by rays, surface from the level (`src/level/layout.js:196-203`: shop and Cage concrete, vacant lot
dirt, the sidewalk strips concrete, everything else asphalt).

### 2.14 How damage reaches the player (hit volumes and amounts)

`player.damage(amount, from, kind)` is the only entry (`src/player.js:349-358`). There is no damage reduction,
no difficulty scaling on the player's side (difficulty changes what enemies deal), no invulnerability frames, and
**no knockback, stagger or slow**: nothing but the player module ever writes his position or velocity.

| Kind | Source | Player volume it is tested against | Amount (Hustler / Boss / Kingpin where three) | Where |
|---|---|---|---|---|
| `bullet` | Goon SMG round (hitscan) | upright cylinder, radius 0.38 m, height 1.80 m (1.15 m crouched), from the feet | 4 / 6 / 8 | `src/combat.js:21-23,101-143,218-222`, `src/config/enemies.js:245,250,255` |
| `bolt` | Buzzard tracer bolt (70 m/s projectile) | upright capsule, radius 0.36 m, from 0.35 m to 1.5 m above the feet (to 1.0 m crouched) | 7 / 10 / 13 | `src/config/enemies.js:88,244,249,254`, `src/enemies/bolts.js:93-108` |
| `melee` | Goon pipe during his dash | within 1.35 m horizontally, feet within 1.3 m vertically, and a clear way for a body | 15 / 22 / 30 | `src/config/enemies.js:180-186`, `src/enemies/goon.js:890-894` |
| `blast` | any explosion | the point 1.0 m above the feet (0.6 m crouched); needs line of sight; linear falloff to the radius | `damage × playerScale × (1 − d / radius)`: propane tank ≤ 85 (r 6.5 m), welding rack ≤ 105 (r 7.5 m), Buzzard crash ≤ 15 (r 3 m) | `src/combat.js:353-361`, `src/explosives.js:20-25`, `src/config/enemies.js:100-102` |
| `fall` | landing faster than 13 m/s | — | (speed − 13) · 7 | `src/player.js:601` |

In Hold the Block the enemy amounts are also multiplied by the wave's damage scale, min(2, 1 + 0.05 · (wave − 1))
(`src/config/flow.js:154`). `from` is the muzzle, the bolt's origin, the Goon's chest, the blast centre, or `null` for
a fall; it drives the HUD damage arc and which way the death camera falls.

### 2.15 Collider census of the shipped block (measured on the real build)

777 boxes: 696 solid, 27 `playerOnly`, 54 `bulletOnly`.

- `playerOnly` (27): the 8 m high seal walls just outside the play bounds and across the two street closures and the
  alley's north end (`src/level.js:31-32,85-92`, `src/level/street.js:401,436`, `src/level/yards.js:66`); the Cage's
  chain-link above its 0.5 m plinth, up to 8 m (`src/level/yards.js:108-110`); stair and deck railings
  (`src/level/shop.js:218,235`, `src/level/street.js:529`); the mezzanine office glass (`src/level/shop.js:186`); the
  hoist netting (`src/level/street.js:362`); boxes on the three master-reel cases.
- `bulletOnly` (54): 44 facade recesses and details, the lot's sign board, the burned cars' cabins, the food cart's
  canopy, boxes on the master-reel cases.
- Things a walking body meets as steps: kerbs 0.15 m (`src/level/layout.js:23`); two flights of stairs with 0.233 m
  risers, 2.8 m in 12 (the scaffold stair and the shop's mezzanine stair: `src/level/layout.js:65,113`); the loading
  dock's four 0.25 m steps (`src/level/yards.js:355-359`); bleacher rows at 0.42 / 0.78 / 1.14 / 1.50 m. The El
  station's stairs at the west end are scenery behind a shut gate (`src/level/el.js:206,237`).
- Highest floors the player can reach on foot: the scaffold deck at 2.95 m and the shop mezzanine at 2.8 m.

### 2.16 Public state and events

State other systems read (`docs/CONTRACT.md:422-448`, `src/player.js:268-304`): `pos`, `vel`, `yaw`, `pitch`, `eye`,
`forward` (unit aim vector: aim + recoil offset, never shake), `health`, `maxHealth`, `alive`, `onGround`,
`sprinting`, `crouching`, `speed` (horizontal, m/s), `ads`, `enabled`, `invulnerable`, `regen {delay, rate}`,
`surface` (surface name underfoot); extras `stridePhase`, `eyeHeight`, `trauma`. Methods: `reset({pos, yaw})`,
`damage`, `heal`, `addRecoil(pitch, yaw)`, `addShake(trauma)`, `setFov(deg)`, `update(dt)`.

| Event | Payload | Emitted when | Where |
|---|---|---|---|
| `player:step` | `{pos, surface, sprint}` | every footfall (stride phase crosses a whole number) | `src/player.js:611-613` |
| `player:jump` | `{}` | a jump starts | `src/player.js:490` |
| `player:land` | `{speed, surface}` | touching down after more than 0.12 s in the air; `speed` = fastest descent of that fall | `src/player.js:522,596` |
| `player:hit` | `{amount, from, health, kind}` | every accepted `damage()` call, before `player:dead` | `src/player.js:356` |
| `player:dead` | `{from}` | health reaches 0 | `src/player.js:372` |
| `input:lock` | `{locked, mode}` | mouse capture gained, lost, or the look mode changed (`lock` / `drag`) | `src/input.js:364` |
| `input:device` | `{device}` | the active device changed (`kbm` / `pad` / `touch`) | `src/input.js:286` |

Surface names: `asphalt, concrete, metal, wood, rubber, glass, dirt, brick, car, cloth, flesh, drone`
(`docs/CONTRACT.md:166-167`).

### 2.17 Config values that are defined but never read

| Field | Value | What is used instead |
|---|---|---|
| `body.stepHeight`, `body.airStepHeight` (`src/config/player.js:12-13`) | 0.42, 0.08 | the physics constants of the same value (`src/physics.js:21-22`) |
| `fov.title` (`src/config/player.js:80`) | 50 | `titleCamera.fov` 50 (`src/config/flow.js:32`) |
| `death.saturation`, `death.fade` (`src/config/player.js:155-156`) | 0.12, 0.55 | `post.dead` with the same targets and its own rates (`src/config/flow.js:24`) |
| `input.touchStickRadius` (`src/config/player.js:165`) | 58 px | only a fallback: the ring's real half-width is measured (`src/input.js:756,825`) |

### 2.18 Where the documents and the code differ (the code wins)

| Document says | Code does |
|---|---|
| Start "near (−40, 0, 8), facing east" (`docs/DESIGN.md:179`) | (−37.4, 0.15, 8.15), on the south sidewalk, yaw −π/2 + 0.08: east, 4.6° toward the avenue (`src/level/data.js:7`, `src/level.js:186`) |
| Cover heights "car bonnets 1.0 … milk-crate stacks 1.0 … mailboxes 1.25, dumpsters 1.35" (`docs/DESIGN.md:211-212`) | the colliders are a little lower or higher than those round numbers: car bodies 1.08, milk crates 0.90, barrels 0.98, newspaper boxes 1.08, mailboxes 1.20, dumpsters 1.30, trash bags 0.62 (measured, 3.7); a car body at 1.08 m cannot be jumped onto from the road |
| Settings field of view "fov: 74" (`docs/CONTRACT.md:113`) | the setting is limited to 60…95; `player.setFov` itself accepts 55…100 |
| `input.aimSlow` is "set by weapon" (`docs/CONTRACT.md:387`) | both the weapon and the input module compute the same slow-down from the same constants; the weapon's value wins while it keeps writing (3.17) |
| "Player … use the reference numbers unchanged" (`docs/DESIGN.md:109`) | cannot be checked: the reference notes no longer exist on this machine. The code is the only source |

---------------------------------------------------------------------------------------------------

## 3. Behaviour

### 3.1 Order within a frame

Variable timestep, `dt = min(real frame time, 0.05 s)`: below 20 fps the game slows down instead of taking bigger
steps (`src/main.js:34,321`). One frame (`src/main.js:270-295`, `src/modules.js:91-98`):

1. `input.update(dt)`: polls the gamepad, builds `input.move` and `input.look` for this frame.
2. `game.update(dt)`: flow, interaction (it sees the player where the previous frame left him).
3. If the run is live (state not `title` / `paused`): `player.update`, then `weapon.update`, `enemies.update`,
   `explosives.update`.
4. World effects, audio, HUD, menus; then the picture is drawn; then `input.endFrame()` clears the press / release edges.

Two consequences matter for feel. The player reads the aim amount the weapon wrote in the **previous** frame (one
frame of latency on the aim-dependent look scale, speed cap and field of view). And because the weapon fires after
the player has placed the camera, `addRecoil` re-places the view at once, so the picture of that same frame and a
second catch-up round already carry the kick (`src/player.js:385-387`).

### 3.2 Order inside `player.update(dt)` (`src/player.js:430-561`)

1. Decay the red hit flash; apply the shake owed for explosions since the last update.
2. If `enabled` is false: only the shake, the low-health ease and the screen values keep settling; return.
3. If dead: run the death view (3.13); return.
4. Read `input.move`; if its length exceeds 1, scale it back to 1.
5. Look: `yaw −= look.dx · k`, `pitch = clamp(pitch − look.dy · k, ±1.5)`, with `k = lerp(1, 0.6, ads)`.
6. Crouch: held → crouching; released → stand as soon as there is headroom (3.3).
7. Jump: coyote and buffer timers; maybe take off (3.4).
8. Sprint rule, target speed, wish velocity, velocity step (3.5).
9. Half a step of gravity; remember the fastest descent; move the body (3.6); second half of gravity if still airborne;
   keep the body 0.4 m inside the bounds.
10. Publish `onGround`, `surface`, `speed`, `sprinting`. On touch-down after more than 0.12 s in the air: landing (3.9).
11. Stair glide, stride and footsteps, bob (3.8, 3.9).
12. Health: regeneration, low-health value, screen values (3.12).
13. Eye height toward the stance's value (rate 11); field of view (3.10).
14. Advance recoil, shake, landing spring; compute lean and view pitch / roll; place the camera (3.11).

### 3.3 Stance state machine

```
STANDING --[crouch held]--------------------------------------------> CROUCHING
CROUCHING --[crouch not held AND room to stand]----------------------> STANDING
CROUCHING --[jump accepted (needs room to stand)]--------------------> STANDING (then airborne)
```

- The collision height switches at once (1.80 ↔ 1.15 m); only the eye eases (rate 11, 90 % in 0.21 s).
- Room to stand = no movement-blocking box overlaps the cylinder of radius 0.288 m from 1.10 m to 1.80 m above the
  feet (`src/player.js:311-315`). Without it the player stays crouched after letting go, and cannot jump.
- Crouch works in the air: holding it through a jump re-crouches on the next frame. The body shrinks from the top
  (the feet do not rise), so there is **no crouch-jump height gain**, and the target speed drops to 1.9 m/s.
- Crouching never changes how the body is pushed by walls; it only lowers the top (what it can pass under, what
  bullets and bolts can hit) and the eye.

### 3.4 Ground, air and the jump

```
GROUNDED --[jump accepted]--> AIRBORNE (vel.y = 6.4807 m/s, event player:jump)
GROUNDED --[walks off a ledge higher than 0.42 m]--> AIRBORNE (coyote timer 0.12 s running)
AIRBORNE --[jump accepted within the coyote time]--> AIRBORNE (vel.y = 6.4807 m/s, whatever the fall speed was)
AIRBORNE --[feet reach a floor]--> GROUNDED (if air time > 0.12 s: landing, 3.9)
any --[health reaches 0]--> DEAD (3.13)        any --[enabled = false]--> frozen (no movement, no look, camera not touched)
```

Timers, each frame (`src/player.js:480-491`):

```
coyote     = wasGrounded ? 0.12 : coyote − dt
jumpBuffer = jump pressed this frame ? 0.13 : jumpBuffer − dt
if jumpBuffer > 0 and coyote > 0 and (not crouching or room to stand):
    crouching = false; vel.y = 6.4807; jumpBuffer = coyote = 0; emit player:jump
```

- One jump height only: holding the button longer does nothing, and a held button never jumps again.
- No double jump, no air jump after the coyote time, no wall jump.
- A press up to 0.13 s before touching down jumps on the frame after landing.
- `wasGrounded` is the grounded state at the end of the previous frame; it also selects the acceleration row (3.5) and
  whether the body may step (3.6).

### 3.5 Horizontal velocity

Sprint is wanted when all of these hold (`src/player.js:48-50,494`): sprint held, forward input > 0.55, absolute
strafe input < 0.6, not crouching, aim amount < 0.35, fire not held. On a keyboard W + A or W + D gives a strafe share
of 0.707, so **diagonal keyboard movement cannot sprint**; an analog stick can sprint within the cone the two limits
allow. Firing or aiming drops a sprint at once.

```
target = crouching ? 1.9 : (sprint wanted ? 6.4 : 3.8)
target = lerp(target, min(target, 2.4), ads)                    // aiming caps the speed
if forward < 0: target *= lerp(1, 0.82, min(1, −forward))       // backing up
ahead  = (−sin yaw, −cos yaw);  right = (cos yaw, −sin yaw)     // (x, z) components
wish   = (right · move.x + ahead · move.y) · target             // zero without input
rate   = wasGrounded ? (input ? 34 : 26) : (input ? 9 : 0.6)    // m/s²
velocity.xz moves straight toward wish by at most rate · dt     // lands exactly on it when closer than one step,
                                                                // except in the air without input (left as it is)
```

(`src/player.js:40-45,57-71,494-504`.) This is a move-toward in velocity space, not a friction model: the path of the
velocity is a straight line at constant rate, identical at any frame rate. The move input is analog: its length scales
the wish speed. Steady speeds **(measured)**: forward and strafe 3.8, diagonal forward 3.8, back 3.116, diagonal back
3.316, sprint 6.4, crouch 1.9, aimed 2.4, aimed backward 1.968, crouched and aimed 1.9 m/s. Changing from sprint to
walk with input held takes 0.076 s (rate 34). The `sprinting` flag is `sprint wanted AND (grounded ? speed > 2.28 m/s :
its previous value)` (`src/player.js:519`); the target speed itself follows "sprint wanted", also in the air.

### 3.6 Gravity and the body move

Gravity is applied in two halves around the move, which makes the jump arc exact at any frame rate
(`src/player.js:506-512`):

```
vel.y = max(vel.y − 21 · dt / 2, −40)
moveCapsule(pos, vel, dt, radius 0.32, height (1.80 or 1.15), allowStep = wasGrounded and not jumped this frame)
if not on ground: vel.y = max(vel.y − 21 · dt / 2, −40)
```

`moveCapsule` (`src/physics.js:478-596`) moves an upright, flat-ended **cylinder** (not a rounded capsule) whose
origin is at the feet. With `stepTop = feet + (allowStep ? 0.42 : 0.08)` and `head = feet + height`, every box that is
not `bulletOnly` is one of three things for this body: a **floor** candidate if its top ≤ stepTop, a **ceiling**
candidate if its underside ≥ head, otherwise a **wall**.

1. Horizontal: the travel `speed · dt` is cut into sub-steps of at most 0.192 m. After each sub-step, up to three
   passes: clamp to the play bounds (centre no closer than one radius; they are walls of unlimited height), then for
   every wall whose footprint is closer to the body's axis than the radius, push the body straight out to exactly one
   radius and remove the velocity component pointing into it. That removal is the wall slide. A body whose axis is
   inside a box leaves through the nearest face.
2. Floor and ceiling at the new spot (`src/physics.js:410-441`): the floor is the highest floor-candidate top under a
   **square** of half-size 0.224 m around the axis (the ground plane y = 0 otherwise); the ceiling is the lowest
   ceiling-candidate underside over the full circle.
3. A floor higher than the feet with less than the body's height of room above it is a wall after all: the horizontal
   move of this frame is undone and the horizontal velocity zeroed.
4. Vertical: `y = feet + vel.y · dt`. Rising into the ceiling: stop under it, `vel.y = 0`. If `y ≤ floor`: stand on
   it (this is both landing and stepping **up**, instantly). Else if `allowStep` and not rising and the floor is at
   most 0.42 m below: snap **down** onto it (walking down stairs and kerbs never goes airborne). Otherwise airborne.
5. Result: `{onGround, hitWall, hitCeil, surface}`; `surface` is the floor box's surface or the ground's.

Consequences: a step up or down is an instant pop of the feet (the eye glides, 3.9). The body can hang over an edge
until its axis is 0.224 m beyond it. There are **no slopes**: every walkable surface is a horizontal box top or the
ground plane, and speed never depends on gradient. The visual ramps of the level (the flares of dropped kerbs,
`src/level/ground.js:73-78`) have no sloped collision; the sidewalk slab's 0.15 m edge is simply stepped. Stairs are
rows of boxes, each reaching down to the flight's foot (`src/level/kit.js:543-563`): walls from the side, low steps
from the front. The player does not collide with enemies or their bodies (only boxes are tested); Goons keep their own
distance.

After the move the player module keeps the body 0.4 m inside the bounds (`src/player.js:564-586`) and, should the
position ever be non-finite or more than 30 m under the ground, puts the body back on the last spot it stood on with
zero velocity.

### 3.7 What the player can walk, step, jump and climb

Rules, with the limits **measured** on the real modules:

| Obstacle, relative to the floor the player stands on | Result |
|---|---|
| Top up to 0.42 m (0.4201 m fails) | walked onto without leaving the ground, if the body's height fits above it |
| Drop of up to 0.42 m | walked down, stays grounded, no landing event (0.43 m: airborne for 0.2 s, landing event) |
| Top up to about 1.02 m | reached by a jump from a standstill pressed against it (1.04 m at 30 fps) |
| Top up to about 1.075 m | reached with a run-up of a few metres, walking or sprinting (1.0775 m passes, 1.08 m fails) |
| Top of 1.08 m or more | cannot be reached from that floor. There is no mantle, climb, vault or ladder |
| Underside at least 1.80 m above the feet | walked under standing (1.79 m blocks) |
| Underside at least 1.15 m above the feet | walked under crouched (1.14 m blocks) |
| Gap narrower than 0.64 m between two walls | impassable |
| Gap between two tops of equal height | crossed up to 3.15 m walking, 5.1 m sprinting (jump at the end of the coyote time, 0.224 m of overhang at each edge) |
| Jump length on flat ground | 2.35…2.41 m walking, 3.96…4.05 m sprinting (the spread is landing detection at 30…144 fps) |

Why the jump limit is 1.075 m and not 1.0 m: in the air a ledge whose top is within 0.08 m above the feet still counts
as a floor, and the feet peak at 1.0 m. Why a standing jump reaches less: pressed against the wall the body starts
from zero forward speed and gains it at only 9 m/s² in the air, so it has to travel the 0.096 m between "one radius
from the wall" and "footprint over the edge" inside the short window in which the feet are high enough.

The shipped block, by collider height above the prop's own base **(measured)**:

| Class | Props (collider top, m) |
|---|---|
| Walked onto (≤ 0.42) | kerbs 0.15; stair risers 0.233; dock steps 0.25; first bleacher row 0.42, the next rows 0.36 each; pallet 0.144; engine-hoist base 0.16; a sedan's or taxi's roof from its own body (1.08 → 1.45: 0.37) |
| Jumped onto from the same floor | bench seat 0.47; trash bags 0.62; master-reel case 0.66; cardboard boxes 0.72; hydrant 0.74; lot wall 0.77; planter 0.80; workbench 0.80; jersey barrier 0.81; milk crates, oil drum, sandbags, compressor 0.90; motorbike, shopping cart, trash can 0.95; burned car 0.96; traffic barrel, tyre stack 0.98; barricade, wood crate, bollard, loading dock 1.00 |
| Not from the same floor | sedan and taxi body 1.08; newspaper box 1.08; tool chest 1.09; lot gate 1.10; pallet stack 1.15; mailbox 1.20; generator 1.22; SUV body 1.24; food cart 1.25; pickup body 1.27; dumpster, parking meter 1.30; welding rack 1.50; vending machine 1.85; van 2.14; box-truck cab 2.28; lot booth 2.37; box truck 3.30 |
| Never stood on | the Cage plinth (0.5 m, but the player-only fence box sits on it); anything behind a seal wall |

Heights chain. A car parked at a kerb is 0.93 m above the 0.15 m sidewalk, so it **can** be mounted from the sidewalk
side but **not** from the road side (confirmed on the real colliders); from a car body the roof is a walk-up step, and
from a 1.45 m roof anything up to about 2.5 m above the road is one jump away. Nothing reachable leads out of the
block: seal walls and the Cage fence are 8 m high and the play bounds are walls of unlimited height.

### 3.8 Stride, footsteps and view bob (`src/player.js:605-631`)

```
walking = on ground and speed > 0.3
if walking:  stridePhase += speed · dt / (crouching ? 1.05 : sprinting ? 2.1 : 1.55)
             every time floor(stridePhase) increases: emit player:step {pos, surface, sprint}
else if on ground: stridePhase eases to the nearest whole number (rate 10; snaps within 0.02)
stridePhase wraps at 2                                    // 0…1 one foot, 1…2 the other
amp    = on ground ? clamp01(speed / 3.8) · (sprinting ? 1.9 : 1) · lerp(1, 0.22, ads) · (crouching ? 0.7 : 1) : 0
bobAmp = damp(bobAmp, amp, 9, dt)
bobY   = −cos(2π · stridePhase) · 0.024 · bobAmp          // lowest at each footfall, one cycle per step
bobX   =  sin(π · stridePhase)  · 0.013 · bobAmp          // right on one step, left on the next
```

`bobX` moves the eye along the camera's right vector and rolls the view by `bobX · 0.35` rad; `bobY` moves it up and
down. Walking: ± 2.4 cm vertical, ± 1.3 cm sideways. Sprinting: ± 4.6 cm and ± 2.5 cm. No footsteps and no bob in the
air. The first-person weapon keeps its own bob phase from the same speed and stride lengths (weapons spec).

### 3.9 Landing, the landing dip and the stair glide

Landing (`src/player.js:521-528,595-602`), when the body touches down after more than 0.12 s in the air, with `speed`
= the fastest descent of that fall:

1. emit `player:land {speed, surface}` (audio plays the thud, fx a puff of dust);
2. kick the landing spring by −min(speed · 0.36, 3.2) m/s;
3. if speed > 7.5: add shake min(0.5, (speed − 7.5) · 0.06);
4. set the stride phase so the next footstep follows after 0.28 stride;
5. if speed > 13: `damage((speed − 13) · 7, null, 'fall')`.

The landing spring is a damped spring on a vertical eye offset, integrated in steps of at most 1/120 s
(`src/player.js:168-197`): `velocity += (−150 · offset − 17 · velocity) · h; offset += velocity · h`, with the offset
held inside −0.20…+0.05 m (hitting a stop zeroes the velocity in that direction). The view also pitches by `offset ·
0.12` rad. Deepest dips **(measured)**: 5.6 cm after a 0.5 m drop, 7.9 cm after a flat jump, 10.5 cm (0.72° of
pitch) after any drop of 2 m or more (the impulse is capped).

Fall numbers **(measured, 60 fps)**: 2.95 m (the scaffold deck) lands at 11.0 m/s, no damage; a jump off the deck
(3.95 m) 12.8 m/s, no damage; 4.0 m: 13.1 m/s, 1 HP; 5 m: 11 HP; 8 m: 38 HP; 12 m: 67 HP; 17.8 m or more kills. The
reported speed is sampled once per frame, so it is up to half a frame of gravity below the analytic value.

Stair glide (`src/player.js:235-243,530-537`): whenever the body was grounded before and after the move, did not
jump, and its feet popped by Δ, the eye offset `stepLag` is reduced by Δ (clamped to ± 0.5 m) and then pulled back to
zero by a critically damped spring of angular frequency 24 rad/s (stiffness 576, damping 48). A flight of stairs reads
as a ramp: the largest frame-to-frame eye move on 0.25 m risers stays under 7.5 cm
(`test/input-player-player.test.js:510`).

### 3.10 Field of view and aiming

```
ads      = clamp01(player.ads)                                   // written by the weapon
target   = lerp(baseFov + (sprinting ? 6 : 0), 52, ads)
inFlight = ads > 0.02 and ads < 0.98
viewFov  = damp(viewFov, target, inFlight ? 30 : 7, dt)          // degrees, vertical
```

(`src/player.js:543-546`.) The weapon produces `ads` as a linear ramp over its aim time (0.18 s Chopper, 0.14 s
Nine), eased with the quintic `smootherstep`, the same out as in (`src/weapon/logic.js:584-589`). It only lets the aim
start when no reload, switch or melee is running and the sprint-lowered blend of the gun has fallen under 0.35
(`src/weapon/logic.js:642`, `src/config/weapons.js:186`).

Zoom factor at full aim = tan(base / 2) / tan(26°): 1.18× at 60°, **1.55× at the default 74°**, 2.24× at 95°.

Timing **(measured, Chopper, base 74°)**: 73.2° at 0.05 s, 67.1° at 0.10 s, 58.1° at 0.15 s, 55.6° at 0.20 s, 53.8° at
0.30 s, 52.9° at 0.40 s. The field of view is within 1° of 52° only after 0.39 s: once the aim amount passes 0.98 the
rate falls from 30 to 7, so the last 3 to 4 degrees creep in. Aiming out mirrors it (70.4° at 0.20 s, 73° at 0.39 s).
The Nine reaches 57.1° at 0.15 s and the same tail. Sprint widening and its release use rate 7 (90 % in 0.33 s).

What the aim amount scales, all blended linearly by `ads`: look rate × 1 → 0.6; speed cap → 2.4 m/s; bob × 1 → 0.22;
strafe lean × 1 → 0.4; field of view → 52°; screen vignette + 0.22; and in the weapon, recoil and shot shake × 1 →
0.55. A sprint cannot start at ads ≥ 0.35.

### 3.11 The view: layers and what follows them (`src/player.js:408-426,548-559`)

```
aimYaw   = yaw + recoil.yaw
aimPitch = clamp(pitch + recoil.pitch, ±1.55)
forward  = (−sin aimYaw · cos aimPitch,  sin aimPitch,  −cos aimYaw · cos aimPitch)

headroom = (crouching ? 1.15 − 1.05 : 1.80 − 1.68) − 0.07          // 0.03 m or 0.05 m
eye      = pos + right(aimYaw) · bobX + up · (eyeHeight + min(bobY + spring.offset, headroom) + stepLag.offset)

lean      = damp(lean, −(sideways speed / 6.4) · 0.02 · lerp(1, 0.4, ads), 8, dt)   // moving right leans right
viewPitch = spring.offset · 0.12
viewRoll  = lean + bobX · 0.35

camera.position = eye
camera.rotation (order yaw, pitch, roll) = (aimYaw + shake.yaw,  aimPitch + viewPitch + shake.pitch,  viewRoll + shake.roll)
camera.fov      = viewFov
```

| Layer | Moves the eye point | Turns the picture | Turns the aim (`forward`, where rounds go) |
|---|---|---|---|
| Look input, permanent recoil share | — | yes | yes |
| Recoverable recoil offset | — | yes | **yes** |
| Stance eye height, stride bob, landing spring offset, stair glide | yes | — | — |
| Landing spring pitch, strafe lean, bob roll | — | yes | no |
| Shake | — | yes | **no** |
| Death collapse | yes (eye height) | yes | aim frozen |

Rounds leave from `eye` along `forward` (`src/weapon/logic.js:459-461`): the bobbing, dipping eye is the real origin of
every shot, the recoil-kicked view is its real direction, and shake never moves a bullet. The camera has no idle sway
and no breathing; the sway of the gun in the hands is the weapon's own (weapons spec).

### 3.12 Health

`damage(amount, from, kind)` (`src/player.js:349-358`): ignored when dead, invulnerable, `?god=1`, or the amount is not
a positive finite number. Otherwise, in this order: `health = max(0, health − amount)`; the regeneration clock restarts
(`sinceHit = 0`); hit flash `hurt = min(1, hurt + 0.35 + amount / 40)`; shake `+= 0.22 + amount / 70`; emit
`player:hit`; if health is 0, die (3.13). A fatal fall therefore emits `player:land`, `player:hit`, `player:dead` in
that order. `heal(n)` adds up to the maximum, only while alive.

Per live update (`src/player.js:633-647`):

```
hurt     = max(0, hurt − 1.9 · dt)                               // also while the player is disabled
sinceHit += dt
if alive and health < 100 and sinceHit ≥ regen.delay: health = min(100, health + regen.rate · dt)
lowTarget = alive ? 1 − smoothstep(0.12, 0.55, health / 100) : 1
lowHealth = damp(lowHealth, lowTarget, 4, dt)
render.post.damage = hurt;  render.post.lowHealth = lowHealth
```

Any damage of any kind restarts the delay. Regeneration does not run while the game is paused or the player is
disabled. Low-health value by health: 0 at 55 HP and above, 0.04 at 50, 0.28 at 40, 0.62 at 30, 0.91 at 20, 1 at 12
and below. Hit flash by damage: 0.50 for a 6-point round, 0.60 for a 10-point bolt, 0.90 for a 22-point pipe, 1.0 from
26 points up; it fades in at most 0.53 s. The audio module also plays a hit thud, an ear ring for hits of 8 or more
(at most every 1.8 s) and muffles the mix by damage (`src/audio/react.js:124-135`).

### 3.13 Death (`src/player.js:360-373,650-677`)

On reaching 0 HP: `alive = false`, sprint off, `deadTime = 0`, remember the current eye height, choose the side
(`from` to the player's **left** → the camera falls onto its right shoulder; from the right, from nowhere or a fall →
onto its left), emit `player:dead {from}`. From then on each update:

```
vel.xz *= e^(−5 · dt);  vel.y = max(vel.y − 21 · dt, −40);  move the body as a 0.6 m high cylinder
s = smoothstep(0, 0.85, deadTime)
eyeHeight = damp(eyeHeight, lerp(eye height at death, 0.22, s²), 18, dt)
viewPitch = −0.25 · s + 0.12 · sin(π · s) + spring.offset · 0.12
viewRoll  = side · 1.15 · s² + lean                     // side = +1 left shoulder, −1 right shoulder
field of view → base at rate 7;  bob amplitude → 0;  lean → 0;  recoil, shake and springs keep settling
render.post.lowHealth = 1
```

Eye height over time **(measured)**: 1.68 m at 0.1 s, 1.60 at 0.3 s, 1.23 at 0.5 s, 0.60 at 0.7 s, 0.27 at 0.85 s,
0.22 from about 1.0 s. Look input is ignored, the body still falls and slides to rest, takes no more damage and does
not heal. Around it (`src/game.js:879-893,809-816`, `src/weapon/logic.js:596-602`): the weapon is dropped, gameplay
input is switched off and the mouse released, the picture eases to 12 % saturation and 55 % darkening, the audio mix
is muffled over 0.85 s and the death sting plays, and the death card appears 1.5 s after death
(`src/config/flow.js:16`). "Run it back" restarts the whole run: there are no checkpoints, and `reset()` puts the
player at the start with full health, zero velocity, pitch 0, and every camera layer cleared (`src/player.js:319-347`).

### 3.14 Recoil: application and recovery (`src/player.js:77-108,380-388`)

`addRecoil(pitch, yaw)` (radians; pitch up, yaw left):

```
pitch_aim = clamp(pitch_aim + pitch · 0.35, ±1.5);   yaw_aim += yaw · 0.35             // permanent: the player must pull down
target.pitch = clamp(target.pitch + pitch · 0.65, ±0.3);  target.yaw = clamp(target.yaw + yaw · 0.65, ±0.2)
sinceKick = 0;   re-place the view now
```

Each update:

```
sinceKick += dt
past = min(dt, sinceKick − 0.09)                       // only the part of the step that lies after the hold
if past > 0: target *= e^(−6.5 · past)                 // both axes
offset = damp(offset, target, 34, dt)                  // the view snaps onto the target, then follows it back
```

So a kick shows in full within about 0.07 s, holds for 0.09 s after the **last** shot, then 65 % of it flows back
(half gone 0.11 s later, 90 % after 0.35 s) while 35 % stays in the aim. Sustained fire restarts the hold with every
round, so the offset accumulates up to its clamps (17.2° up, 11.5° sideways) and only recovers when the trigger is
released. The offset is part of the aim: bullets follow the kicked view.

### 3.15 Shake (`src/player.js:119-165`)

One trauma value 0…1; the camera turns by trauma² (so half the trauma is a quarter of the motion):

```
add(x):  x < 0.03 → trickle += x          else impulse = min(1, impulse + x)
atLeast(x): impulse = max(impulse, min(1, x))                                  // explosions: raise, do not stack
update(dt):
    time += dt;  impulse = max(0, impulse − 1.7 · dt)
    level = min(0.6, trickle / dt / 1.7);  trickle = 0;  sustained = damp(sustained, level, 6, dt)
    trauma = max(impulse, sustained);  p = trauma²
    pitch = 0.03  · p · (sin(43 t)       + sin(72 t + 1.3))
    yaw   = 0.03  · p · (sin(37 t + 2.1) + sin(84 t + 0.4))
    roll  = 0.045 · p · (sin(30 t + 4.2) + sin(61 t + 3.3))
```

Deterministic sines, no noise. A full-trauma impulse is gone after 0.59 s. Sources are listed in 2.8.

### 3.16 Input: actions, edges and the gameplay gate (`src/input.js:135-238,318-342`)

- Every device keeps its own held sources (a key, a mouse button, a pad button, a touch button). An action is `down`
  while any source holds it, `pressed` on the frame the first one arrives, `released` on the frame the last one goes.
  A press that comes and goes between two frames still reads as `down` and `pressed` for one frame.
- Outside gameplay (title, pause, death and debrief cards) only `pause` gets through, and `move` / `look` are zero.
  Nothing pressed in a menu carries into play, with one exception: movement, sprint, crouch and key-turn keys that are
  still physically held when play resumes count again at once (`src/input.js:36,328`).
- Losing focus or hiding the tab drops every input, the press edges of that frame included. Losing the mouse capture
  drops the mouse buttons only.
- `input.tap(action)`: the UI may queue a one-frame press (the HUD's weapon slots); it is read at the next update.
- The active device (`kbm`, `pad`, `touch`) is whichever produced real input last: a key or mouse button, 4 pixels of
  mouse travel in one frame, any pad button or a stick beyond its dead zone, any touch. Prompt glyphs follow it.
- The game pauses on: the pause action, losing a mouse capture it had held, the tab going hidden, the window losing
  focus, a lost graphics context (`src/game.js:829-832,918-930`).

Look assembled once per frame (`src/input.js:1112-1141`), radians, `flip` = −1 with invert Y:

```
dx = (mousePixelsX · 0.0021 + touchPixelsX · 0.0052) · sens
dy = (mousePixelsY · 0.0021 + touchPixelsY · 0.0052) · sens · flip
dx += (turnRight − turnLeft) · 2.1 · dt;   dy += (turnDown − turnUp) · 1.26 · dt            // keys: no sens, no flip
dx += edgeX · 2.4 · sens · dt;             dy += edgeY · 1.2 · sens · flip · dt             // fallback only
dx += padLookX · 2.9 · sens · aimSlow · dt;  dy += padLookY · 2.9 · 0.62 · sens · aimSlow · flip · dt
```

`dx > 0` turns right, `dy > 0` looks down. The player then multiplies both by `lerp(1, 0.6, ads)` (3.2). There is no
smoothing and no acceleration on the mouse; the browser delivers pixels after the operating system's own pointer
settings. Move is `(right − left, forward − back)` from the keys plus the pad's left stick plus the touch stick, cut
back to length 1 (`src/input.js:1143-1150`): keyboard diagonals are not faster.

### 3.17 Gamepad (`src/input.js:56-82,889-1044`)

- Sticks: each axis through the axial dead zone 0.14 (rescaled to 0…1). Left stick → move, no curve, stick up is
  forward. Any button with `pressed` or an analog value above 0.35 is down.
- Right stick: with (x, y) the dead-zoned axes and `m = min(1, length)`, the look share is `(x, y) / max(1, length) ·
  (0.25 · m + 0.75 · m³) / m`: the curve acts on the magnitude, so a diagonal push behaves like a straight one and the
  corners of a square gate are capped at the full rate. Half deflection gives 21.9 % of the full rate.
- Turn boost: `boost` rises by `dt / 0.45` while `m > 0.92`, otherwise falls by `dt / 0.17`, clamped 0…1; the look
  share is multiplied by `lerp(1, 1.75, boost)`. Full rates at sensitivity 1: 166 °/s yaw, 103 °/s pitch; boosted
  291 °/s and 180 °/s; at full aim × 0.6; over an enemy × 0.55.
- Sprint latch: one click of L3 holds `sprint` down; it lets go on a second click, when the stick's forward value
  falls below 0.55, or when gameplay stops.
- X is `reload`, unless an interaction prompt is showing at the moment of the press: then it is `interact` for that
  whole hold, even if the prompt disappears meanwhile.
- Aim slow-down, the only aim assist in the game (`src/weapon/logic.js:568-582`, `src/input.js:1024-1044`): every 0.05 s
  one ray from the eye along `forward`, 60 m long, against the enemies' own hit shapes; if it meets an enemy and the
  world does not block the way to that point (`src/enemies.js:416-420`), the multiplier's target is 0.55, else 1; the
  multiplier follows with `damp` rate 14. It scales the right stick only. There is no magnetism, no rotation toward
  targets, no snap and no bullet bending, and mouse and touch are never slowed.
- Rumble (dual-rumble where the pad has it): hit taken, explosion by distance (2.11), each round fired (Chopper strong
  0.18 / weak 0.5 / 55 ms, Nine 0.35 / 0.6 / 55 ms: `src/config/weapons.js:73,146`), a melee hit (0.6 / 0.4 / 90 ms).
  A new effect is skipped while a stronger one is still playing (its level below 70 % of the running one, level =
  max(strong, weak / 2)); durations are capped at 2 s (`src/input.js:1046-1066`).
- Menus: D-pad or left stick past 0.6 moves the selection (repeat after 0.38 s, then every 0.17 s), left / right
  adjusts a slider once per push, A accepts, B goes back, Start is the screen's primary action
  (`src/input.js:994-1021`). The first pad with the standard mapping is used; a pad that disappears releases everything.

### 3.18 Mouse capture and its fallback (browser only; `src/input.js:354-429,472-501,1122-1135`)

Two look modes. `lock`: the browser's pointer lock hides the cursor and delivers raw movement. `drag`: the fallback
for browsers and embedded frames that refuse the lock.

```
start or resume of a run, or a click on the game view while not captured  → ask for the lock, start a 1.2 s timer
grant                 → locked; mode 'lock' for the rest of the session (a later refusal never demotes it)
refusal, error, missing API or timeout, and the lock has never worked     → mode 'drag' (announced once)
capture lost (Esc, alt-tab) after it had been held                         → the game pauses; mouse buttons are released
in 'drag' a click still asks again until 3 clicks have been refused
```

The click that captures the mouse also fires. In `drag` mode: moving the free cursor turns the view at the normal
mouse rate; resting it within 12 % of the left / right edge or 10 % of the top / bottom keeps turning at up to 2.4 and
1.2 rad/s × sensitivity (linear from the zone line to the edge, armed only after the cursor has been mid-screen, with
faint edge strips as a cue); the arrow keys and I J K L turn; Enter fires. A one-line hint explains the mode
(`src/config/player.js:369-376`), repeated every 6 s while the mouse is free on desktop (`src/game.js:363-378`).

### 3.19 The stubs: the smallest correct player and input

`src/stubs/player.js` keeps exactly: the speed rule, the velocity model, jump with coyote time and buffer, gravity,
crouch with the headroom test, fall damage, health with regeneration, the hit flash and low-health values, death with
a simplified collapse, the five events, eye-height and field-of-view easing, and only the permanent 35 % of a recoil
kick. It leaves out: view bob, strafe lean, landing spring, stair glide, shake, the recoverable recoil offset, the
bounds margin. `src/stubs/input.js` keeps: the action model and gameplay gate, WASD / mouse bindings, mouse look with
sensitivity and invert, pointer lock with the drag fallback; no gamepad, no touch, no key turning. These two files are
a sound first milestone for the port: everything in them is gameplay, everything they omit is feel.

### 3.20 Touch controls (summary; `src/input.js:527-866`, `src/input.css`)

Shown only while touch is the device in use and gameplay is active. Semi-transparent dark discs with white line
glyphs; pressed or latched controls turn taxi yellow.

| Control | Behaviour |
|---|---|
| Move stick | appears under a thumb anywhere on the left 45 % of the screen; ring 116 px across at full scale; output clamped to the unit circle |
| Auto-sprint | stick deflection above 0.93 with forward above 0.8 |
| Sprint lock | drag the thumb 1.45 ring radii straight up onto the arrow and let go, or tap the arrow: runs forward with no finger down until the stick is touched again |
| Look | any other finger drags the view at 0.0052 rad per pixel × sensitivity; a finger holding FIRE drags too |
| FIRE (84 px), second FIRE on the left (52 px) | hold |
| AIM (58 px), DUCK (50 px) | toggles |
| JUMP (52), RLD (48), SWAP (46), HIT (46) | press |
| USE (58 px) | only visible while an interaction prompt shows; hold |
| Pause (40 px, top right) | only when the HUD has no pause button of its own |

The set scales with the screen (one layout unit = 0.72…1.1 px), keeps the bottom-centre 40 % free and stands 104 px
higher in portrait. Phones start in this scheme; a real mouse or keyboard switches back.

### 3.21 The collision world's other services (`src/physics.js`)

- `raycast(origin, dir, maxDist)` (`:305-339`): slab test against every box that is not `playerOnly`, plus the ground
  plane; the nearest entry point wins. A box that contains the origin is ignored (rays only hit faces they enter).
  Result: distance, point, an axis-aligned normal, the surface name and the box (`null` for the ground).
- `lineOfSight(a, b)` (`:347-362`): true when nothing ray-solid lies between the points, stopping 0.05 m short of b.
  With `{movement: true}` it asks whether a body could pass instead: `playerOnly` boxes block, `bulletOnly` ones do not.
- `groundHeight(x, z, maxY)` (`:365-376`): highest top of an unflagged box under the point, 0 if none.
  `overlapsCylinder(x, z, r, y0, y1)` (`:379-390`): does anything that blocks movement overlap that cylinder.
- `addOriented` (`:118-154`): a rotated box becomes one axis-aligned box when it is within about 5.8° of a right
  angle, otherwise up to 10 shrunken axis-aligned slices along its long side. All collision is axis-aligned.
- Nav grid (`:598-1029`): 0.5 m cells over the play bounds (184 × 136), rebuilt lazily when a blocking box changes. A
  cell is blocked when its centre lies inside a blocking box grown by 0.5 m; the outer ring is always blocked; free
  cells are labelled by connected area. `findPath` is A* on 8 neighbours without corner cutting, octile heuristic,
  then string-pulled into straight legs; a blocked start or goal snaps to the nearest free cell within 12 cells. It is
  a single ground-level layer: waypoints have y = 0, stairs and decks are not part of it. The enemies spec covers its
  use.

---------------------------------------------------------------------------------------------------

## 4. Unreal mapping

Nothing here was compiled or run (there is no editor in this environment); engine behaviour described below is from
knowledge of Unreal Engine 5 and must be confirmed in the editor. Class names are suggestions.

Data: do not retype the tables of section 2 into code. The web exporter (`tools/ue-export/export.cjs`) writes them
to `unreal/MurderInc/Content/Data/`. As exported at the time of writing:

| File and key | Holds |
|---|---|
| `config.json` → `player` | every group of `src/config/player.js` unchanged, in web units (metres, seconds, radians) |
| `config.json` → `settings.defaults` | the default user settings (`sens` 1, `invertY` false, `fov` 74) |
| `config.json` → `flow.difficulty.<name>.regen` | regeneration delay and rate per difficulty (2.10) |
| `level.json` → `playerStart.ue` | feet position (−3740, 815, 15) cm and yaw −4.5837°; `bounds` holds the play bounds |
| `level.json` → `colliders.boxes` | the 777 boxes, each with `blocks {movement, shots, nav}`, its flags, surface, tag, and web and Unreal extents |
| `level.json` → `physics` | `STEP_HEIGHT`, `AIR_STEP` and the nav and slicing constants of `src/physics.js` (`SUBSTEP`, `PUSH_ITERATIONS`, `FOOTPRINT` and `LOS_SLACK` are only in 2.13 here) |
| `text.json` → `input` | the glyph, hint and touch-button tables |

Load the player's numbers from there and convert at load time with the rules of 4.1; this document says what each
number means and how it is used.

### 4.1 Unit and axis conversion

| Web | Unreal |
|---|---|
| position (x, y, z) m | (X, Y, Z) = (x, z, y) × 100 cm |
| velocity, speeds m/s | × 100 cm/s; accelerations × 100 cm/s² |
| yaw ψ (rad, 0 = north, + = left) | Yaw° = −degrees(ψ) − 90, wrapped to (−180, 180] (0 = east, + = right) |
| pitch (rad, + = up) | Pitch° = degrees(pitch) (+ = up) |
| roll (rad, + = head tilts left) | Roll° = −degrees(roll) (+ = clockwise) |
| look `dx > 0` turns right, `dy > 0` looks down | yaw input + = right; pitch input − = down |
| field of view, vertical degrees | see 4.5 |

Player start: web (−37.4, 0.15, 8.15), yaw −1.4908 rad → Unreal location of the **feet** (−3740, 815, 15) cm, yaw
−4.58°. Play bounds: X −4600…4600, Y −3400…3400 cm; the body centre stays 40 cm inside.

### 4.2 Body and movement component

A `Character` with a capsule and a `CharacterMovementComponent` subclass. Values:

| Web | Unreal property | Value |
|---|---|---|
| radius 0.32 m, height 1.80 m | capsule radius / half-height | 32 / 90 cm |
| crouch height 1.15 m | `CrouchedHalfHeight` | 57.5 cm (the feet stay; the top comes down) |
| eye 1.68 m / 1.05 m | camera height above the feet (own damped value, not `BaseEyeHeight` popping) | 168 / 105 cm, i.e. +78 cm above the standing capsule centre, +47.5 cm above the crouched one |
| eye rate 11 /s | exponential interpolation | 90 % in 0.21 s |
| walk 3.8 | `MaxWalkSpeed` | 380 cm/s |
| sprint 6.4 | `MaxWalkSpeed` while sprinting | 640 cm/s |
| crouch 1.9 | `MaxWalkSpeedCrouched` | 190 cm/s |
| aim cap 2.4, backpedal × 0.82 | computed max speed (override `GetMaxSpeed` or set per tick) | 240 cm/s; × 0.82 → 311.6 cm/s straight back |
| accel 34 / 26 / 9 / 0.6 | see 4.3 | 3400 / 2600 / 900 / 60 cm/s² |
| gravity 21 | `GravityScale` with world gravity −980 | 2.1429 (2100 cm/s²) |
| take-off 6.4807 | `JumpZVelocity` | 648.07 cm/s (apex 100 cm, air time 0.617 s) |
| terminal 40 | physics volume terminal velocity | 4000 cm/s (the engine default) |
| step 0.42 | `MaxStepHeight` | 42 cm |
| jump: one fixed height | `JumpMaxCount` 1, `JumpMaxHoldTime` 0 | — |
| footprint 0.224 m | `PerchRadiusThreshold` | about 9.6 cm (32 − 22.4), so the centre may overhang an edge by 22 cm |
| bounds margin 0.4 | blocking volumes 40 cm inside the bounds, or a clamp after the move | 40 cm |
| fall-out limit −30 m | `KillZ` handling that teleports to the last grounded location | −3000 cm |
| death capsule 0.6 m | shrink the capsule on death | half-height 32 cm (a 64 cm sphere is the smallest a 32 cm radius allows) |

No slopes exist in the source, so slope behaviour is free: keep the default walkable floor angle, make sure real ramps
in the new level art (kerb cuts) are well under it, and keep speed independent of gradient (the engine default).

### 4.3 Movement logic that needs custom code

1. **Velocity model.** The stock walking and falling code (friction-based turning, `MaxAcceleration`,
   `BrakingDecelerationWalking`, `AirControl`) does not reproduce a straight move-toward in velocity space. Override the
   component's velocity calculation for walking and falling with the rule of 3.5: wish velocity from the input vector ×
   target speed; step toward it by rate × dt with the four rates; snap when within one step except airborne without
   input. If stock behaviour must be used instead, the nearest settings are `MaxAcceleration` 3400,
   `BrakingDecelerationWalking` 2600 with ground and braking friction 0, `BrakingDecelerationFalling` 60, `AirControl`
   about 0.26; expect direction changes to feel different.
2. **Sprint rule** (3.5) evaluated every tick from the raw move input, the aim amount and the fire input; it is not a
   toggle, and "wanted" (drives speed) differs from the `sprinting` flag (drives field of view, bob, stride, the gun).
3. **Coyote time 0.12 s and jump buffer 0.13 s**: the engine has neither. Track time since leaving the ground without
   a jump and the time of the last jump press; a coyote jump sets the vertical speed to 648 cm/s regardless of the
   current fall speed.
4. **Crouch**: hold-to-crouch; stand only when the standing capsule fits (the engine's uncrouch test does this); allow
   crouching in the air with the feet fixed; a jump from a crouch stands first and is refused without headroom.
5. **Air step of 8 cm**: the engine does not step up while falling. Without it the highest ledge a jump mounts is
   about 100 cm instead of 107.5 cm. Either accept that (it keeps car bodies at 108 cm unreachable from the road, and
   loses only tops between 100 and 107 cm, e.g. a 90 cm prop standing on a 15 cm kerb seen from the road) or add a
   small assist: airborne, blocked by a ledge whose top is at most 8 cm above the feet, with room on top → place the
   body on it.
6. **Step-down snap**: the engine's floor check keeps a walking character on the floor for drops up to
   `MaxStepHeight`; confirm that walking off a 42 cm ledge does not enter falling and a 43 cm one does.
7. **Landing**: in the character's landed callback use the downward speed just before impact; require more than
   0.12 s of air time; then the five steps of 3.9.
8. **No pawn blocking**: the web player passes through enemies. Set the player capsule to ignore enemy pawns (or
   overlap) unless a deliberate change is wanted.

### 4.4 Collision channels

| Web flag | Unreal |
|---|---|
| solid (default) | blocks pawns, weapon traces, sight traces; affects navigation |
| `playerOnly` | blocks pawn movement only: ignored by weapon and sight traces and by navigation. Use for the seal walls (800 cm high, plus full-height blocking volumes at the play bounds), the Cage chain-link above its plinth, railings, the office glass, the hoist netting |
| `bulletOnly` | blocks weapon and sight traces only: no pawn collision, no navigation |
| surface name | a physical material per surface (12 names, 2.16) on every collider, returned by floor hits and traces |

Use simple box collision for gameplay props so cover heights stay exactly as measured (3.7); the web level's collider
list (777 boxes with their flags, 2.15) is the reference. `raycast` → a line trace on the weapon channel; `lineOfSight` → a sight trace that stops 5 cm short;
`lineOfSight({movement: true})` → a trace on the pawn channel; `groundHeight` → a downward trace; `overlapsCylinder` →
a capsule overlap. The nav grid → a Recast nav mesh with an agent radius of about 50 cm; it must stay a single
ground-level layer to match (exclude the scaffold stair and deck, the mezzanine and its stair, the dock and the
bleachers with nav modifiers), or Goons will climb where they never did.

### 4.5 Camera

One camera component on the character, driven every tick after movement by a small view-rig object (or a player
camera manager with camera modifiers) that reproduces 3.11 in this order: control rotation (aim) → recoil offset →
eye point (stance height, bob, landing spring, stair glide) → landing pitch, lean, bob roll → shake → death.

- The **aim rotation** used for shots is control rotation + recoil offset. Keep the recoil offset out of the control
  rotation (it recentres) but inside the shot direction. Keep shake, lean and landing pitch out of both.
- Pitch limits: camera manager view pitch min / max ± 85.94°; clamp aim + recoil at ± 88.81°.
- Shake: a custom modifier holding the trauma scalar and the six sines of 3.15. The stock Perlin and wave shake
  patterns do not give "trauma squared, linear decay, raise-not-stack, trickle hold" without custom code.
- Bob, lean, landing spring and stair glide are procedural; do not replace them with authored camera animation.
  The engine pops the capsule on steps and on crouch, so the stair glide and the damped eye height are required for a
  smooth picture.
- Near clip 8 cm (the web value); the eye never comes closer than 7 cm to the top of the capsule.
- Field of view. Web values are vertical. Either make the viewport keep the vertical field of view constant and feed
  the vertical numbers (confirm in the editor that the camera's value is then read as vertical), or keep the engine's
  default horizontal convention and convert: `horizontal = 2 · atan(tan(vertical / 2) · aspect)`.

| Vertical ° | Meaning | Horizontal ° at 16:9 | at 16:10 | at 21:9 |
|---|---|---|---|---|
| 52 | full aim | 81.86 | 75.93 | 97.39 |
| 54 | first-person weapon | 84.34 | 78.38 | 99.86 |
| 60 | lowest setting | 91.49 | 85.46 | 106.83 |
| 74 | default | 106.52 | 100.66 | 120.74 |
| 80 | default, sprinting | 112.33 | 106.64 | 125.89 |
| 95 | highest setting | 125.46 | 120.40 | 137.12 |
| 101 | highest setting, sprinting | 130.25 | 125.48 | 141.08 |

- The first-person weapon is drawn with its own 54° vertical field of view and never clips into walls: use the
  engine's first-person rendering path where the engine version has one (first-person primitives with their own field
  of view), otherwise a separate weapon field of view in the material. The weapons spec owns this.
- Screen feedback: a post-process material on the camera with three scalars (`damage`, `lowHealth`, `ads`) and the
  strengths of 2.9; death adds saturation 0.12 and 55 % darkening.

Camera and feel constants converted (rates in 1/s and times in s are unchanged; signs follow 4.1):

| Quantity | Unreal value |
|---|---|
| Stride per footstep: walk / sprint / crouch | 155 / 210 / 105 cm |
| "Standing still" below; `sprinting` flag above | 30 cm/s; 228 cm/s |
| Bob amplitude at walk speed: vertical / sideways | 2.4 / 1.3 cm (× 1.9 sprinting, × 0.7 crouched, × 0.22 at full aim) |
| Roll from sideways bob | 0.2005° per cm |
| Strafe lean | 1.146° at 640 cm/s sideways (0.68° at 380 cm/s), × 0.4 at full aim; leaning right is positive roll |
| Landing spring | stiffness 150 /s², damping 17 /s, offset limits −20 / +5 cm, impulse −min(speed · 0.36, 320) cm/s, pitch 0.0688° per cm (dip looks down) |
| Stair glide | critically damped, 24 rad/s, at most ± 50 cm behind |
| Landing: minimum air time; shake from; fall damage from | 0.12 s; 750 cm/s (+ 0.0006 trauma per cm/s, at most 0.5); 1300 cm/s (0.07 HP per cm/s above it) |
| Aim pitch clamp; aim + recoil clamp | ± 85.94°; ± 88.81° |
| Recoil: permanent share; offset clamps | 35 %; 17.19° pitch, 11.46° yaw (a kick "left" is negative yaw) |
| Shake amplitude per sine at trauma 1: pitch / yaw / roll | 1.719° / 1.719° / 2.578° (frequencies in rad/s as in 3.15) |
| Shake reach for explosions | 2800 cm from the eye |
| Death: final eye height; roll; pitch; nod | 22 cm; 65.89° (negative roll = onto the left shoulder); −14.32°; 6.88° |
| Mouse | 0.1203° per count × sensitivity |
| Key turning | 120.3 °/s yaw, 72.2 °/s pitch |
| Right stick at sensitivity 1 | 166.2 °/s yaw, 103.0 °/s pitch; boost × 1.75; aim × 0.6; over an enemy × 0.55 |
| Aim slow-down trace | 6000 cm, every 0.05 s |
| Touch look | 0.2979° per pixel × sensitivity |

### 4.6 Input (Enhanced Input)

One mapping context for gameplay; `pause` in a context that stays active in menus.

| Input action | Value | Keyboard + mouse | Gamepad | Notes |
|---|---|---|---|---|
| Move | Axis2D | W / S / A / D | left stick, axial dead zone 0.14 | normalise to length ≤ 1; analog speed |
| Look (mouse) | Axis2D | mouse XY | — | no smoothing, no acceleration; degrees = counts × 0.1203 × sensitivity; Y × −1 with invert |
| Look (stick) | Axis2D | — | right stick, axial dead zone 0.14 | curve, boost, pitch × 0.62, aim slow-down: a custom modifier or code in the controller; rate in °/s × dt |
| Look (keys) | Axis2D | arrows, I / J / K / L | — | 120.3 °/s yaw, 72.2 °/s pitch, ignores sensitivity and invert; optional (accessibility) |
| Fire | bool | left mouse, Enter | RT, pressed above 0.35 | hold |
| Aim | bool | right mouse | LT, pressed above 0.35 | hold |
| Jump | bool | Space | A | pressed edge only; feed the 0.13 s buffer |
| Sprint | bool | Left / Right Shift | L3 | hold on keyboard; latch in code on gamepad (release below 0.55 forward) |
| Crouch | bool | C | B, LB | hold |
| Reload | bool | R | X | on gamepad X routes to Interact for the whole hold when a prompt was showing at the press |
| Interact | bool | E | X (see above) | hold |
| Swap | bool | Q, mouse wheel (0.28 s debounce) | Y, D-pad up / down | |
| Weapon 1 / 2 | bool | 1, 2 (and numpad) | D-pad left / right | |
| Melee | bool | F, V, middle mouse | RB, R3 | |
| Pause | bool | Esc, P | Start | |

- Sensitivity: one user value 0.2…3 (step 0.05, default 1) multiplies mouse and stick; aiming multiplies every device
  by `lerp(1, 0.6, ads)`. At sensitivity 1 a full turn is 2 992 mouse counts at the hip (9.5 cm at 800 DPI) and 4 987
  at full aim. Make sure no legacy input scale (the player controller's old yaw and pitch scale factors) is applied on top.
- The mouse-capture fallback of 3.18 (drag mode, edge turning, Enter to fire) is not needed: a packaged game always
  captures the mouse. Keep "pause when the window loses focus".
- Device switching for glyphs: detect the last used device (keyboard / mouse versus gamepad) and broadcast it; the
  thresholds of 3.16 avoid flicker (stick drift inside the dead zone and tiny mouse nudges do not switch).
- Rumble: force-feedback effects with the strengths and durations of 2.11 and 3.17 and the "weaker never cuts
  stronger" rule.
- Touch controls only matter if a mobile build is planned (open question); 3.20 is the layout to rebuild then.

### 4.7 Health, damage and events

- A health component on the character: max 100; `regen.delay` and `regen.rate` set by the game mode from the
  difficulty table (2.10) on every run reset; the logic of 3.12.
- Damage arrives through the engine's damage events with one damage type per kind (`bullet`, `bolt`, `melee`,
  `blast`, `fall`) and the source location (`from`). Hit volumes on the player: a 38 cm × 180 / 115 cm cylinder for
  enemy hitscan (a dedicated collision shape on the weapon-trace channel, slightly fatter than the 32 cm movement
  capsule), a 36 cm capsule from 35 to 150 cm (100 cm crouched) for bolts, and a sample point 100 cm (60 cm crouched)
  above the feet for blasts with a line-of-sight check and linear falloff. No knockback, no stagger.
- Events → multicast delegates on the character for audio, effects, HUD and game flow: step (location, surface,
  sprint), jump, land (speed, surface), hit (amount, from, health, kind), dead (from).
- Death: stop reading input, tell the weapon to drop, run the collapse of 3.13 in the view rig, let the game mode
  show the death card after 1.5 s.
- `enabled = false` (title fly-through, debrief): detach the view from the character (another view target) while the
  hit flash keeps fading. `invulnerable`: a flag checked first in the damage path.

### 4.8 Settings

Sensitivity (0.2…3, default 1), invert Y (default off), field of view (60…95 vertical degrees, default 74), saved with
the user settings and applied live. The web keys are `sens`, `invertY`, `fov` in `localStorage['murderinc.settings.v1']`
(`src/core/settings.js:4-17`).

### 4.9 Parity checks for the rebuilt controller

| Check | Expected |
|---|---|
| Standstill to 380 cm/s, and back to rest | 0.112 s; 0.146 s over 27.8 cm |
| Sprint, straight back, crouch, full aim | 640 / 311.6 / 190 / 240 cm/s; W + D with Shift stays at 380 |
| Jump on flat ground | apex 100 cm, air time 0.617 s, same height however long the button is held |
| Jump 0.11 s after walking off a ledge / 0.14 s after | works, with a full 648 cm/s whatever the fall speed / refused |
| Jump pressed 0.1 s before landing | jumps on touchdown |
| Ledge of 42 cm / 43 cm | walked up without a landing event / blocked |
| Ledge of 100 cm, 107 cm, 108 cm with a run-up | mounted, mounted (if the air step is ported), blocked |
| Obstacle underside at 180 cm / 115 cm | passes standing / passes only crouched; cannot stand up beneath |
| Drop of 2.95 m, 4.0 m, 8 m, 17.8 m | no damage, about 1 HP, about 38 HP, dead |
| Regeneration on Boss after a 30-point hit | nothing for 5.5 s, then 16 HP/s; a second hit restarts the wait |
| Aim with the Chopper at 74° | 67° after 0.10 s, 55.6° after 0.20 s, within 1° of 52° after 0.39 s |
| One recoil kick | 35 % stays in the aim; the rest shows within 0.07 s, holds 0.09 s, 90 % back 0.35 s later |
| Death | eye at 22 cm and rolled 65.9° after about 1 s, onto the side away from the shot |

---------------------------------------------------------------------------------------------------

## 5. Art and audio implications

**What exists of the player.** In the web game Rule has no body in the world: no legs, no torso, no shadow, no
reflection, no voice. The only visible parts are the first-person forearms, gloves and weapon (weapons spec; the look
is fixed by `docs/DESIGN.md:292-297`: black gloves, bare brown forearms, gold watch on the left wrist, gold link
bracelet on the right). A photoreal build has to decide whether the player casts a shadow or shows legs (open
question); nothing in the source asks for it.

**Dimensions the level art must respect** (they are gameplay, not decoration):

| Rule | Dimension |
|---|---|
| Body clearance: any passage the player must use | wider than 64 cm; at least 180 cm high standing, 115 cm crouched |
| Steps the player walks | risers of at most 42 cm (the block uses 15 cm kerbs and 23.3 cm stair risers) |
| Low cover that hides a crouched player | top at or above about 108 cm (crouched eye 105 cm); he shoots over it standing (eye 168 cm) |
| Jumpable tops | up to 100 cm reliably, 107 cm at most; 108 cm (a car body) and higher is a wall from the same floor |
| Edges | the player can stand with his centre up to 22 cm past an edge |
| Camera | near plane 8 cm. Walls stay about 30 cm from the eye (body radius 32 cm less the sideways bob); a ceiling the head touches is 12 cm above the resting eye (10 cm crouched) and never closer than 7 cm; the death view lies 22 cm above the ground, rolled 66°, so pavement, kerb and road textures need close-up quality |
| Field of view | 60…95° vertical by setting, + 6° in a sprint, 52° aimed: skies, horizons and tall facades are in view at the wide end; nothing may rely on a narrow view to hide unfinished geometry |

Collision for cover props should be simple boxes at the measured heights (3.7), not the render mesh, or the cover
rules change.

**Animation.** No character animation is needed for the player's body. Every camera motion in this document is
procedural and must stay that way; the arms and weapon are animated in the weapons spec and take the stride phase,
speed, sprint and aim amount from here.

**Effects.** A dust puff at the feet on `player:land`. The post-process feedback of 2.9: red border flash on hits,
desaturation + vignette + pulsing red rim at low health, a light vignette when aiming, desaturation and darkening on
death.

**Audio to record or source** (the web game synthesises all of it: `src/audio/sfx-player.js`, `src/audio/react.js`):

| Sound | Variations in the web game | Trigger and mix |
|---|---|---|
| Footsteps: asphalt, concrete, metal (tread plate, stairs), wood (plywood deck), dirt | 4 walking + 3 running per surface | `player:step`; walk volume 0.55, run 0.8 and pitch + 4 %. Other surfaces reuse a set: brick, glass → concrete; rubber, cloth → dirt; car → metal (`src/audio/react.js:7`) |
| Jump (clothes and a push-off scuff) | 1 | `player:jump`, volume 0.8 |
| Landing thud + gear settle | 2 | `player:land`; volume clamp(0.35 + speed / 10, 0.35, 1), plus one running footstep of the surface at 60 % volume, pitch − 8 % |
| Hit taken (a punch in the chest) | 3 | `player:hit`; volume clamp(0.5 + damage / 40, 0.5, 1); pitch 0.85 for blasts |
| Ear ring (about 4.1 kHz, 2.4 s) | 1 | hits of 8 or more, at most every 1.8 s, volume clamp(damage / 28, 0.3, 1) |
| Heartbeat loop (0.86 s lub-dub) | 1 | below 35 % health while playing: volume 0.25 → 0.65 and rate 1 → 1.35 as health falls from 35 % to 10 % |
| Mix muffle | — | on every hit by damage (0.2…0.7), full over 0.85 s on death |

Cadence at full speed: 2.45 steps/s walking, 3.05 sprinting, 1.81 crouched. Rule does not speak, grunt or breathe
audibly anywhere in the source. Controller rumble needs four effect families: hit taken, blast by distance, round
fired per weapon, melee hit.

---------------------------------------------------------------------------------------------------

## 6. Open questions and risks

1. **Vertical versus horizontal field of view.** Every web number is vertical; the engine's camera value is
   horizontal by default. Decide the convention once (4.5) and check ultra-wide and narrow windows; the web game also
   zooms out below 4:3.
2. **Cylinder versus capsule.** The source body has flat ends, finds its floor under a 44.8 cm square, steps instantly
   and tolerates 8 cm in the air. A rounded engine capsule perches, slides off edges and mounts ledges differently.
   The mount limit (107.5 cm versus about 100 cm), the reachable-roof chains of 3.7 and the 5.1 m sprint gap will all
   move unless tuned; a reachability pass over the rebuilt level is needed either way.
3. **Is "cars cannot be mounted from the road" intended?** The 1.08 m car body sits a few millimetres above what a
   jump reaches; the config comment only says the height hides a crouched eye (`src/props/vehicles.js:83`). The port
   should keep the outcome on purpose or change it on purpose.
4. **Mouse sensitivity units.** The browser delivers pixels after the operating system's pointer speed and
   acceleration; the engine reads raw counts. "0.1203° per count × sensitivity" is the literal port and will feel
   faster or slower than the web build on machines with non-default pointer settings. A different default may be
   wanted; the slider range (0.2…3) covers it.
5. **Field-of-view tail when aiming.** The last 3 to 4 degrees of the zoom arrive at the slow rate (3.10). It is what
   the code does; the config describes the two rates, not the tail, so it may be an accident. Confirm it should be
   kept rather than tightened.
6. **Aim assist on gamepad** is only a 45 % slow-down on the exact crosshair ray. Console-style assistance (larger
   bubble, rotation) does not exist; adding it is a design change, not a port.
7. **Axial dead zone.** The sticks use a per-axis (cross-shaped) dead zone, which makes slow diagonal aiming snap to
   the axes. Keep for parity or switch to a radial one deliberately.
8. **Player body and shadow** in a photoreal first-person game: not in the source (section 5).
9. **Touch controls and a mobile build**: in scope or not? The whole of 3.20 and the phone-specific layout depend on it.
10. **Fall damage is nearly unreachable in the shipped block**: the highest floors reached on foot are 2.95 m, and a
    jump off the deck lands at 12.8 m/s against a 13 m/s threshold. Only roofs reached by the chains of 3.7 (a 3.3 m
    box truck) could hurt, and those were not audited. If the rebuilt level adds height, the rule starts to matter.
11. **Enemies do not block the player** in the source (4.3, item 8); engine defaults would make them solid.
12. **Frame-rate limits.** The web simulation clamps its step to 0.05 s and every formula here is written to be
    frame-rate independent; the engine port should use the exponential forms as given (not linear interpolation
    shortcuts) and sub-step movement at low frame rates.
13. **The reference notes** that the design documents point to for "details" (`docs/CONTRACT.md:7-10`) are gone; where
    this spec and those documents disagree, only the code could be consulted.
