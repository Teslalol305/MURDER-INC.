# Gameplay slice 1: the contracts that exist in code

The player and the two guns in Unreal, as built (`unreal/MurderInc/Source/MurderInc`). The specs are
`spec/01-player.md` and `spec/02-weapons-combat.md`; this page records what the code actually does and what other
packages may rely on. State and evidence: `PROGRESS.md`, section Gameplay.

## 1. Layers

| Layer | Class | Holds | Never |
|---|---|---|---|
| Rules | `FMIPlayerRules` (`Player/MIPlayerRules`), `FMIWeaponRules` (`Weapons/MIWeaponRules`), `FMIExplosiveField` (`Weapons/MIExplosiveRules`) | every decision of `src/player.js`, `src/weapon/logic.js`, `src/explosives.js`, frame by frame, in plain C++ (cm, degrees, s) | touch an actor, a mesh or the renderer |
| Hosts | `AMIPlayerCharacter`, `UMIWeaponComponent`, `UMICombatSubsystem` | answer the rules' questions with the engine (traces on the `Bullet` channel, overlaps, the capsule move) | decide gameplay |
| Presentation | `FMIViewmodelRig` (`Weapons/MIViewmodel`), the first-person meshes, `AMIHUD` | the gun pose, the moving parts, tracers, the HUD | write rule state |

Tuning: `Content/Data/config.json` (the web game's tables; `UMIDataSubsystem` converts to Unreal units).
Web literals the exporter does not reach: `Content/Data/rules.json`. Presentation only (meshes, markers, poses, feel):
`Content/Data/presentation.json`. No tuning number is in code.

## 2. A frame

1. `AMIPlayerCharacter::Tick` (pre-physics): `FMIPlayerRules::BeginFrame` (look, crouch, jump with coyote and
   buffer, sprint rule, the straight move toward the wish velocity) hands the velocity to `UMICharacterMovement`
   (stock walking and falling, `CalcVelocity` replaced; gravity scale = config gravity / world gravity, step 42 cm,
   perch radius from the footprint, crouch through `bWantsToCrouch`, take-off by setting Z and falling).
2. The movement component moves the capsule.
3. `FMIPlayerLateTick` (post-physics, after the movement tick): `EndFrame` (landing, stride, health and regeneration,
   eye height, field of view, recoil, shake, the view), then `UMIWeaponComponent::Step` (rules, viewmodel, parts,
   tracers), then the camera is put at `Rules.Eye` / `Rules.CameraRotation`.
4. `UMICombatSubsystem::Tick`: the explosive fuses; a fuse that runs out blows (`Explode`).

## 3. What the rest of the game may read and listen to

The world's event bus: `UMIEventSubsystem::Get(World)` returns `FMIGameEvents` (`Core/MIEvents.h`), native multicast
delegates named after the web events: `WeaponFire` (one per round: weapon, eye, direction, aim, the camera kick of
that round in degrees, the spread it was drawn from, the round's place in the burst, rounds left), `WeaponDry`,
`WeaponReload` (start, magout, magin, bolt, done, cancel), `WeaponSwitch` (holster, draw), `WeaponSwing`,
`WeaponMelee`, `Impact`, `PlayerHitEnemy`, `Explosion`, `ExplosiveLit`, `ExplosiveBlast`, `PlayerStep`, `PlayerJump`,
`PlayerLand` (fall speed), `PlayerHit` (amount, from, health, kind), `PlayerDead`.

For an animation layer (nothing of it may reach into the rules):

| Need | Read |
|---|---|
| weapon id and state | `UMIWeaponComponent::GetView()` → `FMIWeaponView`: `Weapon`, `Activity` (Ready, Reloading, Holstering, Drawing, Striking, Dropped), `ActivityTime` / `ActivityLength` (progress), `ReloadStage` (last mark passed), `bReloadEmpty`, `bTrigger`, `Mag`, `MagSize`, `Ads`, `SprintBlend`, `Wall`, `Spread`, `SinceShot`, `Burst` |
| one event per shot with its impulse | `WeaponFire` (`KickPitch`, `KickYaw`, `Spread`, `Burst`, `MagLeft`) |
| aim alpha, speed, stance, airborne | `AMIPlayerCharacter::GetAimAlpha`, `GetGroundSpeed`, `GetStance` (stand, crouch, sprint, dead), `IsAirborne`; landing and take-off: `PlayerLand`, `PlayerJump` |
| damage direction | `AMIPlayerCharacter::GetLastDamageDirection`, `PlayerHit.From` |
| the gun's pose and parts | `UMIWeaponComponent::GetRig()` → `FMIViewmodelRig::GetGunTransform()` (camera space), `GetParts()` (bolt or slide 0..1, slide locked, trigger 0..1, barrel tilt 0..1, magazine 0..1 and visible) |

Damage: anything hurtable implements `IMIDamageable` (`Core/MIDamageable.h`) and registers with
`UMICombatSubsystem` (the player, `AMITargetDummy`, `AMIExplosive`; enemies later). A round is one line trace on
`ECC_GameTraceChannel1` "Bullet" (`Config/DefaultEngine.ini`) from the eye; a component tagged `head` (or a bone
whose name contains `head`) takes `weapons.common.headMultiplier`. Blasts: `UMICombatSubsystem::Explode` (event,
chain, then enemies, the player at `rules.json` height × `explosives.rules.playerDamageScale`, explosives; linear
falloff; world geometry blocks).

## 4. First person (the engine's template way, 5.9)

The camera has `bEnableFirstPersonFieldOfView` and `bEnableFirstPersonScale`; its world field of view is the rules'
vertical value converted to horizontal for the viewport's aspect, the first-person one is config
`player.fov.viewmodel` (54° vertical) converted the same way; the scale is `presentation.json firstPerson.scale`.
The gun (`UPoseableMeshComponent`) and the arms (`USkeletalMeshComponent`, the mannequin body playing the gun's idle
sequence) are `EFirstPersonPrimitiveType::FirstPerson`, owner-only, attached to the camera. Each frame:

- gun = `meshOffset` (mesh space → gun space) × the rig's gun transform (gun space → camera space);
- arms = the body placed so that its `bodyHandSocket` (`HandGrip_R`) sits on the gun's `grip` marker;
- parts: the bones named in `presentation.json guns.<id>.parts` (bolt or slide along its axis, trigger and barrel
  about the gun's right axis, magazine along its drop vector and hidden while off screen), relative to the reference
  pose; a bone the mesh does not have is skipped;
- markers: a socket of the real mesh with the name in `sockets` (Muzzle, Eject, SightRear, RecoilPivot, Palm_R ...)
  replaces the web value, so the sight alignment and the recoil pivot follow the real art;
- tracers start where the muzzle appears on screen (camera-space point re-projected by the ratio of the two
  fields of view' tangents, spec 02 3.16).

Placeholders: the template mannequin (`SKM_Manny_Simple`), `SKM_Rifle` (CHOPPER) and `SKM_Pistol` (NINE), installed
by `tools/box/seed-content.sh`. The real SK_Chopper, SK_Nine and arms replace them by changing the paths and
`meshOffset` in `presentation.json`; no code changes.

## 5. Tests

`tools/box/test.sh` runs every `MurderInc.*` test headless. The golden tests replay
`Content/Data/golden/*.json`, written by `node tools/ue-export/golden.mjs` from the web game's own modules
(player, weapon, explosives, combat, rng); every recorded number must match. `MurderInc.Weapons.ViewmodelRig` checks
the rig against its own data; `MurderInc.Weapons.HitscanDummyBlast` fires real traces in a world at the dummy and a
propane tank and checks body and head damage and the blast falloff.

# Gameplay slice 2: the enemies and the game itself

The specs are `spec/03-enemies.md` and `spec/04-flow.md`. As for slice 1, this records what the code does and what
other packages may rely on; evidence is in `PROGRESS.md`.

## 6. Layers

| Layer | Class | Holds |
|---|---|---|
| Rules (web units: metres, +Y up, radians) | `FMIBoxWorld` (`World/MIBoxWorld`, `src/physics.js`), `FMIEnemyField` (`Enemies/MIEnemies`, `src/enemies.js` with `goon.js`, `buzzard.js`, `bolts.js`, `logic.js`), `FMIGameRules` (`Flow/MIGameRules`, `src/game.js`), `MIFlow::*` and `FMIRadio` (`Flow/MIFlowRules`, `src/game/spawn.js`, `waves.js`, `stats.js`, `music.js`, `radio.js`) | every decision of the web modules, frame by frame |
| Host | `UMIGameSubsystem` (`Flow/MIGameSubsystem`) | boots the block, owns the rules, answers their questions with the engine (`IMIGameHost`, `IMIEnemyHost`), statistics, settings, save game, menus |
| Presentation | `AMIGoon`, `AMIBuzzard` (`Enemies/MIEnemyActors`), `AMIReelCase`, `AMITruck` (`World/MIObjectiveActors`), `AMIBlockGeometry`, `AMIHUD`, `FMIMenu` (`UI/MIMenus`) | follow the rule state; never write it |

**Navigation: the web game's own nav grid, ported, not the engine's navigation mesh.** `FMIBoxWorld` is
`src/physics.js` line for line (0.5 m cells inflated 0.5 m, A* with string pulling, regions, random points, the
re-plan line test) over level.json's 777 colliders. Why: (1) the Goon's whole engage logic (fire-position costs,
repicks, stuck rules, the rush) is written against this grid's answers, and with the grid ported the C++ replays the
web game's fights exactly (`MurderInc.Golden.World`, `.Enemies`, `.Directors`: 0 mismatches over 100,000 checks),
which a Recast mesh cannot; (2) it needs no build step and no navigation volume, so it runs headless from a clean
checkout and is identical in both maps, because both maps' collision is the same level.json box list; (3) it is
cheap (184 x 136 cells). The engine's navigation mesh is not used by gameplay; nothing stops an art pass from
building one for other uses.

## 7. The game in a world

`AMIGameMode::StartPlay` boots `UMIGameSubsystem` in the maps listed as `BlockMaps` in `Config/DefaultGame.ini`
(`L_Block`, `L_GreyBlock`) or with the URL option `?block=1`; `?mode=`, `?difficulty=`, `?autostart` as in the web
game's URL. Boot, in order:

1. `FMILevelData` (level.json) fills the box world; config.json, text.json (`text` and `interface`), rules.json, the
   three enemy tables (`enemiesResolved`), presentation.json and the save game load.
2. `AMIBlockGeometry`: every collider no explosive owns becomes a box component (bullet-only boxes ignore pawns,
   player-only seal walls block only pawns), plus the ground slab. In a map with art (any actor tagged
   `presentation.json block.artTag`, `MIBlock`, which `build_block.py` puts on everything it places) the boxes stay
   invisible and the art map's own collision is switched off, so the data's boxes are the only collision; in a map
   without art they are drawn as grey boxes. Same collision, same box world, same play in both maps.
3. The 21 explosives (`AMIExplosive`) in level order: combat item i is level explosive i is box-world owner i. A blown
   one removes its boxes from the box world (they come back on a run reset) and shows its wreck mesh.
4. Both enemy pools, pre-spawned and hidden: field slot i is actor i (12 `AMIGoon`, then 8 `AMIBuzzard`).
5. A reel case per objective, the IPX truck, a title camera.
6. `FMIGameRules::Init` (title) or straight into a run.

Frame (spec 04 3.1): `UMIGameSubsystem` flow tick (pre-physics; the player's early tick waits for it; ticks while
paused) → the player and his weapon (slice 1) → the enemy tick (post-update work: `FMIEnemyField::Update`, the
events, the actors follow). The delta is clamped to 0.05 s. A kill by the player's round is reacted to in the same
frame (`DamageEnemy` drains the field's events at once).

What the host answers (web ↔ Unreal: `MI::Web::ToUnreal` / `FromUnreal`):

| Rule question | Engine answer |
|---|---|
| A Goon round (`Hitscan`) | a line trace on `Bullet` from the rules' muzzle ignoring every enemy and the player, then `src/combat.js rayPlayer` against the player's shot cylinder (rules.json `player.shotTarget`: r 0.38 m, 1.8 / 1.15 m) inside that distance; a hit explosive takes the enemy amount; `Impact` event otherwise |
| Bolts, the pipe (`DamagePlayer`) | `AMIPlayerCharacter::ApplyMIDamage` (kind `bolt` / `melee`, source Enemy) |
| A Buzzard's crash (`Explode`) | `UMICombatSubsystem::Explode` with the Buzzard's player scale |
| The player's hits on a unit | `AMIGoon` / `AMIBuzzard::ApplyMIDamage` → `DamageEnemy`: part head only for rounds, every blast credited to the player, enemy sources ignored |
| Hearing | `WeaponFire` → `Gunfire` (45 m, every 0.3 s at most), `Explosion` → `Explosion` (30 m), `ExplosiveBlast` → `Alert` (60 m) |
| Reset, heal, resupply, regeneration, invulnerability | `AMIPlayerCharacter::ResetAt`, `FMIPlayerRules`, `UMIWeaponComponent::AddReserve`, `UMICombatSubsystem::ResetExplosives` |
| Statistics | shots: `WeaponFire`; hits: `PlayerHitEnemy` of rounds; kills and headshots: the field's `killed` events with `byPlayer` |
| Best score, settings | `FMISettings` (src/core/settings.js validation; defaults config.json, ranges rules.json) in one save slot `murderinc.settings.v1` (`UMISaveGame`) |

State → world (spec 04 3.2): the simulation (player, weapon, enemies) runs except on the title and in a pause;
gameplay input, HUD and viewmodel only in intro and playing; the player is disabled on the title and after the
truck; a pause pauses the world (`SetGamePaused`); the title shows the fly-through camera on the level's cinematic
keys; fade and saturation go to the camera manager and the player camera's post process.

## 8. What the rest of the game may read and listen to

Event bus additions (`Core/MIEvents.h`): `Enemy` (every `FMIEnemyEvent`: spawn, alert, telegraph, fire, melee, hit,
killed; web units), `Flow` (every `FMIFlowEvent`: `game:state`, `objective:done`, `objective:all`, `holdout:wave`,
`extraction:reached`, `hud:*`, `audio:sting`, `player:heal`, `weapon:reserve` ...), `MusicIntensity` (0..1 every
frame). Effects and sound hang on these and on the slice 1 events.

For an animation layer, per enemy (`AMIGoon::GetView()` / `AMIBuzzard::GetView()` → `FMIEnemyView`, Unreal units):
mode, Goon step (`EMIGoonSub`), alive, velocity, speed, yaw rate, crouch and aim weights, aim yaw and pitch, look yaw
and pitch, rush phase and progress, lamp, hit flash, outfit, death direction; Buzzard rotor speed and angle, eye yaw
and pitch, lost rotor; the last rule event and its age. The Goon is an `ACharacter` whose movement component reports
the rules' velocity and acceleration (it never moves the actor), so an animation blueprint wired like the template
shooter NPC's (presentation.json `enemies.goon.animClass`, now `ABP_TP_Rifle`) plays locomotion; aim pitch is the
pawn's remote view pitch; a death clip by the shot's direction (`enemies.goon.death`). Hit volumes are never the
mesh: a head sphere (tag `head`) at the rules' head point and a body capsule from the shin to the head, config.json
sizes, on `Bullet` only, off once dead. The Buzzard is a placeholder (presentation.json `enemies.buzzard`) with a box
hit volume 0.8 r x 0.8 r x h of the ellipsoid. Bone and socket names the real meshes keep: `head`, `pelvis`,
`spine_05`, `hand_r`, `HandGrip_R` (weapon), `Muzzle` (the SMG's lamp and tracer), mannequin skeleton; the
Buzzard's rotor points and eye come from rules.json `buzzardModel`.

Reel case: `AMIReelCase::GetState()` (Live, Grabbing, Taken) and `GetProgress()`; truck: `AMITruck::GetState()`
(Idle, Open).

## 9. Menus and input

`FMIMenu` holds the screen (title, pause, settings, death card, debrief) with its lines and items from text.json;
`AMIHUD` draws it and the flow's lines on the canvas (final styling later). Input (Enhanced Input, in code):
Interact E / gamepad X (held), Pause Esc / P / Start, menu Up / Down / Left / Right / Enter / Space / A /
Backspace / B (these also act while paused). The mouse wheel swaps at most once per `player.input.wheelDebounce`.
Console: `MIStart [mission|holdout] [skip]`, `MIPauseKey`, `MIMenu <up|down|left|right|confirm|back>`,
`MIInteract <0|1>`.

## 10. Slice 1 leftovers closed here

The 8 cm air step (airborne, blocked, free once lifted by `body.airStepHeight`, a floor within it ahead: the body is
put on the ledge), the play-bounds clamp (`body.boundsMargin` inside level.json's bounds), the fall-out return (feet
below rules.json `player.fallOut.below` or not finite: back to the last ground), the wheel debounce, explosive wrecks
and their reset.

## 11. Tests (slice 2)

`MurderInc.Golden.World`, `.EnemyLogic`, `.Enemies`, `.FlowRules`, `.Directors` replay the web game's own modules
(`tools/ue-export/golden-ai.mjs`). `MurderInc.Run.*` play whole runs in a world with collision, headless:
`StoryComplete` (a bot that follows the objective data, aims and fires the real weapon at enemies it can see, takes the
three reels and reaches the truck; it is patched up every frame, so the enemies' hits land and are counted but do not
end the run), `StoryDeath` (a bot that does not fight dies; the death card; Run it back), `HoldTheBlock` (three waves
at the start, score, resupply, the card and the best), `Menus` (settings validation, title, start, pause, settings,
resume).

# The set-up flow and four guns (LOADOUT.md, as built)

## 12. The set-up screens

`UMIFrontEnd` (rules `FMIFrontEndRules`, Slate widget `SMIFrontEnd`, stage `AMIShowroom`) replaces the canvas title:
Home, Crew, Loadout, Workbench, Block & Style, Briefing. Every control sits in the left 40 % column under the veil; the
smallest text is 14 pt; marks, arrows and pips are shapes (`SMIMark`), never characters; every string comes from
frontend_text.json or text.json, the key names from `frontend.glyphs.<kbm|pad>` for the device used last. The fonts fall
back to a symbol face (`MIStyle::SymbolFontFile`), and the front end logs any character no face has.

Input on the screens (Slate key events, the same path in play and in the tests): Enter / Space / A activate the focused
control; Start is Next on every set-up screen and Hit the block on Home and the Briefing; Ctrl+Enter or View+Start
jumps to the Briefing; Tab cycles the panes and Next (Loadout: rack, slots, Next), Down past the last row lands on
Next; Esc / B go back. Console twins: `MIMenu fe <action> [args]` (the rules' actions), `MIKey <key> [down|up] [ctrl]
[shift]` (a real key event through `FSlateApplication`; in the run it goes to the game viewport), `MIViewSize <w> <h>`
(the window around the game viewport, for pictures at other sizes), `MISetup dump`. `MISetup overlay`,
`MIKey`, `MIViewSize` and `UMIDataSubsystem::EditLoadoutForDev` are not in shipping builds.

The stage: the turntable frames the shown gun from its mesh bounds inside the free 60 % of the screen at the viewport's
aspect ratio; on the Workbench it aims at the slot's mount socket, turns that side to the camera, stops spinning and
lights the mount. Crew shows the member's own arms at the eye, or the turntable while those arms are not in the
project. The Briefing is the player's first-person view with the arms hidden while they are the template body.

## 13. Four guns in play

`FMIWeaponRules` carries one to four guns (1-4, Q / Y last gun, next / previous, the wheel from three guns), per-gun
holster and draw, one bag, fire modes with the Selector, falloff and noise radius per round. The run takes the
set-up through `UMIGameSubsystem::BeginWithSetup` → `FMILoadoutResolver` → `UMIWeaponComponent::ApplyRun`. The enemy
field hears a round at the gun's noise radius (`FMIShotFiredEvent::NoiseRadius`, cm, converted to metres by the
game subsystem); the web's gunfire throttle stays, except that a louder round than the last alert in the window still
alerts. The HUD bar shows the four slots and the bag; the world's objective markers hide while the wheel is open.

## 14. Tests (set-up and four guns)

`Loadout.*` (DataLoads, ParityResolve, ParityGolden, ParityNextPrevious, ParityPIE, BuildPIE, MountsExist),
`Attachments.*`, `Weapons.FourGuns`, `Player.ControllerSwitching` (the input layer), `Player.ControllerKeys` (a local
player and the controller's own mappings through `InputKey`), `Frontend.Walk` (rules), `Frontend.WalkWorld` and
`Frontend.WalkPad` (Home to the run with Slate key events only), `Frontend.Glyphs` (the fonts' character maps),
`Enemies.GunfireRadius`, `Save.SetupRoundTrip`, `Save.SetupValidation`.
