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

# First person and the enemies as drawn (the pack clips, the real arms, the Goons, the effects)

## 15. The viewmodel

`UMIFirstPersonRig` (`Weapons/MIFirstPersonRig`) owns how the arms and the gun in hand are drawn; `UMIWeaponComponent`
steps it after the rules and the procedural rig every frame. A gun is drawn one of three ways, chosen when it is
equipped from its resolved presentation's `animSet` (presentation.json `firstPerson.animSets`):

| Mode | When | Arms | Gun |
|---|---|---|---|
| Pack | set `rifle` (`mode: pack`): the CHOPPER (when its `realMesh`, the pack's Short rifle, exists), SHORTY, STICK, STRETCH | `SK_RuleArms` on the camera by the recipe of ANIMATION.md 9 (component (-0.66, 0, -162), yaw -90), playing the pack's FP clips | the pack rifle (`USkeletalMeshComponent`) on the arms' `ik_hand_gun`, identity, playing the pack's weapon clips; parts by `UMIGunAssembly` on it |
| HandIK | set `pistol` (`mode: ik`): the NINE when `SK_Nine` exists | `SK_RuleArms` placed so the template body's `HandGrip_R` socket (read from `SKM_Manny_Simple`, same skeleton) holds the gun's grip, playing the template `MF_Pistol_Idle_ADS` with `MM_Pistol_Fire` added per round; both palms pulled onto `SK_Nine`'s `Palm_L` / `Palm_R` by two-bone IK (the `middle_metacarpal` point lands on the socket); the support hand's fingers (the bones below `hand_l`) take the pack idle's wrap (`fingerCurl`, a finger-only layer: `FMIFPLayer::Branch`; without the pack the template fingers stay) | the procedural rig poses `SK_Nine`, its slide, barrel, trigger and magazine bones as before; `SM_Weapon_NineMagazine` rides the `magazine` bone **at the inverse of that bone's reference pose** (`UMIFirstPersonRig::MeshSpacePartOnBone`: the magazine is modelled in the pistol's space, so snapped to the bone's frame it floated 10 to 20 cm beside the gun, turned 90 degrees; `FirstPerson.NineMagazine`) |
| Template | nothing above exists (a clean checkout) | the template body, as before | the template rifle or pistol, as before |

Every choice falls back: a missing arms mesh, clip, gun mesh or a clip on another skeleton keeps the template way and
logs why. `UMIFPAnimInstance` (`Weapons/MIFirstPersonAnim`) has no graph: the game thread hands it a stack of clips at
times (`FMIFPPose`: override layers blended in order, additive layers relative to the clip's own first frame) and hand
IK targets, and its proxy samples and blends them on the worker thread. It never decides timing.

**The pack state mapping** (ANIMATION.md 4, roles in `animSets.rifle.arms` / `.gun`):

| Rules state / event | Arms | Gun |
|---|---|---|
| Ready | `idle` (crouched: `crouch`) looped; `walkF/B/L/R` by the velocity's direction in the view, weight by speed / `walkSpeed`; `sprint` by `SprintBlend`; `fall` while airborne; `jumpStart` on `PlayerJump`, `jumpEnd` on `PlayerLand` (weight by fall speed) | `base` (the reference pose) |
| Aim (`Ads`) | `aim` (`Aim_Pose`; `aimGripVertical` / `aimGripAngled` with that grip) blended by smoothstep(Ads): the pack's aim transitions are too slow for the rules' aim time | |
| Each round (`WeaponFire`) | `fire` (hip) / `fireAimed` restarted, additive, weight `fireWeight` | `fire` restarted at `fireRate` |
| Reloading | `reloadTactical` (Reload_Quick) or `reloadEmpty` (Reload_Empty), clip time = a piecewise-linear map of the rule's activity time through the marks: (0, 0), (magOut, 0.40 / 0.333), (magIn, 1.467 / 1.333), empty only (boltRelease or slideRelease, 2.15), (the rule's total, the clip's length). Every pack mark lands on the gun's own stage time (config / guns.json `reload`) | the same clip of the gun at the same time |
| Holstering, Drawing | `holster` over the activity; `draw` (Equip_Quick, 0..0.53 s) over the activity; the rig's holster / draw offset stays on top | |
| Striking | `melee` (Melee_Swing_L, 0..1.0 s) over the strike | |
| Selector | `modeSwitch` (FireModeSwitch) at its own rate | |
| Inspect key (T, View held; `MIInput inspect 1`) | `inspect`, or `magCheck` when the magazine is not full; also the idle flourish after `inspectAfter` (24 s) of calm; any activity, aim, sprint or shot ends it. Presentation only: the rules have no inspect | `inspect` / `magCheck` |

Actions blend in over 0.08 s and out over 0.18 s; gun clips snap (their last frame is the reference pose).

**Magazines (ANIMATION.md 9.1).** The seated magazine is the build's magazine part (`UMIGunAssembly::PartMesh`) or the
rig's own `SM_TFA_AR_Magazine_Full` on `MagHinge`; a reserve one rides `Magazine_Reserve` with the hinge socket's frame.
In a reload the reserve shows from `reserve` to the end; at `out` the seated one hides. **The tactical reload stows
it** (`reloads.tactical.stow`: hidden, kept, no body: a partly used magazine is never thrown away); the empty reload
drops a physics `_Empty` copy where it appears on screen with the bone's velocity (`UMIEffects::SpawnBody`, 8 s).
Outside a reload the seated one shows and the reserve hides.

**Drawn at the first-person depth.** The first-person pass draws the arms and gun with their own field of view and
the camera's `FirstPersonScale` (0.6): a world object at the gun's world point sits behind the gun. The muzzle flash,
the casings and the dropped magazine therefore go through `UMIWeaponComponent::FirstPersonToNearWorld`: location
(s x, s k y, s k z) in camera space, scale s k (s = FirstPersonScale, k = tan(world fov / 2) / tan(first-person fov /
2)). They land on exactly the pixels of the muzzle, port or well, in front of the world as the gun is. The player's
flash uses the effects' own world cards (`UMIEffects::WorldFlash`, the cards the Goons' flashes use) at that point:
cards attached to the camera (first-person primitives in the first pass, plain primitives in this one) were read back
visible, placed and sized right in play and still never drew in a picture.

**Aimed.** The irons are zeroed: once the gun is fully up, the front sight's direction from the eye in the clip's
own pose (the rig's layers taken off) is measured and the arms are turned about the eye by that angle, by
smoothstep(Ads), kept per gun (`GetIronZeroDeg`), so the post sits on the screen centre where the rounds go. The
support elbow drops (`animSets.rifle.supportElbowDrop` (0, 0, -45) cm on the left arm's IK pole, the hand kept where
the clip has it): the forearm leaves the sight picture. The HUD crosshair fades out with smoothstep(0.05, 0.55, Ads).
The pack optics get daylight values (`firstPerson.opticMaterials`: the reticle's `Brightness` 25,000 nits, the
glass `Opacity` 0.05) on dynamic instances.

**The procedural layers stay on top.** In Pack mode `FMIViewmodelRig::SetClipDriven(true, bobScale)` drops the rig's
own sprint, reload, aim and strike poses; `GetLayerTransform()` (hip view to the final pose, camera space) carries the
wall pull, holster and draw offsets, footstep bob (x `bobScale` 0.45: the walk loops bob too), breathing, look lag,
inertia, jump and landing, bumps, the aim arc and the six recoil springs, and is applied to the arms' rest transform.

**Camera.** First-person field of view: config `player.fov.viewmodel` (54 vertical) blended by Ads to `recipe.fovIrons`
38 or, with any optic, `recipe.fovOptic` 32 (`UMIWeaponComponent::GetFirstPersonFov`; `FirstPersonToWorld` uses the
current value). Near plane `recipe.nearClip` 1 cm (`GNearClippingPlane`, game worlds only). With an optic the arms move
by minus the scope's `SightEye` offset from `SightRear` across the bore, times smoothstep(Ads), so the eye sits on the
optic's axis. An optic other than the irons switches the base mesh to `variants.<v>.opticMesh` (the irons-folded twin:
`FMIReadiness::BaseMesh`).

**The CHOPPER's stand-in** (DECISIONS.md 2026-11-23): presentation.json `guns.chopper.realMesh` is the pack's Short
rifle; `guns.chopper.real` (and `guns.nine.real` for `SK_Nine`) is merged over the gun's presentation by the resolver
only when that mesh is the one drawn: its sockets, mesh frame, `animSet` and `materials` (slot -> material: the dark-earth
`MI_Chopper_DarkEarth_01` / `_03` of `tools/box/fp/mi_fp_import.py paint_master`, a worn cerakote over the pack's own
albedo that keeps the bright edges bare). The rules are never touched (`FirstPerson.RealArt`).

**Arms.** presentation.json `firstPerson.arms` (`SK_RuleArms`) replaces the template body when it exists; its jewels
(`firstPerson.jewels`: the silver bracelet; the watch is not worn on these arms) are placed from their Blender rest
placement made relative to the bone's reference pose at run time.

## 16. The enemies as drawn

presentation.json `enemies.goon`: `variants` are `SK_Goon_Hoodie`, `_Puffer`, `_Tracksuit` (cycled by the rules'
outfit index across the slots) at `meshScale` 0.98; when any is missing the `variantsFallback` mannequins at scale 1.
The weapon is `SM_Weapon_GoonSMG` (a static mesh, origin at the grip) on bone `hand_r` at `weaponOffset` (CHARACTERS.md;
socket names cannot be set from Python in 5.9), its muzzle at `muzzleOffset` (39, 0, 4.2) cm (weapons.py: bore 4.2 cm
over the grip, muzzle device ends at 0.39 m); without it the template rifle on `HandGrip_R`. Animation as before
(`ABP_TP_Rifle`), with two presentation fixes on top:

- **The support hand holds the SMG.** The Goon's mesh is `UMIGoonMeshComponent` (`Enemies/MIGoonMesh`): after the
  animation blueprint's pose, in `FinalizeBoneTransform`, the left arm is solved by two-bone IK in component space so
  the palm's centre (`middle_metacarpal_l`) lands on `supportGrip` (17, 0, -3) cm in the SMG's frame (weapons.py's
  `SupportHand` socket, 1.8 cm under it), every descendant of the arm following. Weight 1 while alive, fading out
  over 0.25 s in the death clip.
- **The body turns onto the aim.** The template set aims along the body; the drawn mesh turns by the rules' aim yaw
  (`AimYawRel` x the aim weight, eased, at most 75 degrees). The hit volumes stay the rules'.

**The Buzzard** is `SK_Buzzard` when it is in the project (`enemies.buzzard.mesh`): a `UPoseableMeshComponent`, the
four props spun about their hubs by the rules' rotor angle (fl and rr counter-clockwise from above), a lost rotor
scaled to nothing, the gimbal turned to the rules' eye yaw and pitch, the lens lit through `eyeMaterial` (the
additive tracer material, `Intensity` = lamp x `eyeNits`); the placeholder shapes only in a clean checkout.

## 17. Effects

`UMIEffects` (`Weapons/MIEffects`, a tickable world subsystem, game worlds only) on the /Game/FX materials of
`tools/box/fp/mi_fp_import.py fx`; tuning in presentation.json `fx`. Built in code on pooled components (no Niagara
asset: the effect materials are procedural HLSL, the motion is the subsystem's).

Two things the fix pass (2026-11-23) found by measuring in play, not by reading the code:

- **Long frames ate the short effects.** The headless editor plays at 10 to 20 frames a second; one step of 0.05 to
  0.1 s aged a 0.045 s flash, a 0.05 s light or a 0.09 s tracer past its life before it was ever drawn (the cards
  existed, placed and sized right, but hidden: read back from Python). Flashes, lights and tracers now advance at
  most 1/60 s per frame, so each is drawn for its life's worth of frames at any frame rate.
- **Dark translucent puffs drew nothing.** A bright card on M_FX_Smoke showed (`tools/box/fp/fx_diag.py`, in the
  editor and in play), 53 smoke-coloured cards at opacity 0.5, facing the camera at 7 to 9 m, left the street behind
  them untouched. M_FX_Smoke is now a **lit, masked** card whose coverage is dithered per pixel (`DitherTemporalAA`,
  resolved by TSR into a soft edge): it takes the sun, the sky and Lumen like any surface; the fireball's glow stays
  emissive. The parameters (Color, Opacity, Seed, Erode, Fire) are unchanged.


| Hook | Effect |
|---|---|
| Player round (`OnRoundFired`) | three world flash cards (`WorldFlash`) on the muzzle at the first-person depth (the star across the bore, two crossed jets along it; `flash.life` 0.045 s, nearly three frames at 60 fps) and a 0.05 s point light in the world (none at all with a silencer); a brass casing from `Eject` along its +X with the body's velocity, at the first-person depth and size (`SM_TFA_AR_Bullet_Casing` on the pack rifles, else a brass cylinder); the tracer as a moving streak from 1 m past the muzzle (more when the rules hide the first stretch), 1 cm radius, 60,000 nits (the old line tracer when the materials are absent); every streak starts one frame in flight |
| Enemy `Fire` (`AMIGoon::OnRuleEvent`) | a world flash at the SMG's muzzle with its light, the tracer to the first thing the round meets |
| `Impact` on the world | two dust puffs in the surface's colour (`fx.surfaces`), a strike mark (deferred decal, 30 s), a spark card on metal |
| `Impact` on an enemy | a short blood mist both ways and a spatter on the wall behind within 2.6 m |
| `PlayerHit` (HUD, `AMIHUD::DrawHurt`) | the rules' `Hurt` drawn at the frame's edges: twelve bands thickening to the edge (at most about 0.6 alpha at the very edge), a 9 % wash in the centre (the old full-frame 25 % tint flattened the picture), and for 1.5 s a red wedge on a ring round the crosshair pointing at `PlayerHit.From` |
| `Explosion` | a 0.45 s light, a fireball (seven emissive puffs), twelve smoke puffs rising for 5 to 8 s, a dust ring, ten debris bodies, a scorch mark |

## 18. Dev console (not in shipping builds)

`MIStart [mode] [skip]` resolves the saved set-up (or the parity one) through the loadout resolver before the run,
like the set-up screens (`UMIGameSubsystem::StartRunWithSetup`), so a console run draws the real arms and guns too.
`MIFaceEnemy <m>` stands the player on a walkable spot the asked distance (within 0.75 m) from the nearest Goon with a
clear line to its chest, the bearings fanned out 15 degrees at a time from the line Goon -> player.
`MIPose <x> <y> <feet z> <yaw> <pitch>`, `MIFreezeAfter <s>` (world time dilation 0.0001 after that much game time),
`MIFreezeOn <fire|reload|explosion|enemyfire> [delay]` (enemyfire: a Goon in sight within 16 m, the view turned onto
it), `MIBlowNearest`, `MIInput inspect 1`, `MIFaceEnemy -1` (turn only). `tools/box/fp/fp-shots.sh` uses them for the
pictures `docs/unreal/shots/fp-*.jpg`.

## 19. Tests (first person)

`FirstPerson.NineMagazine` (on the box: `SM_Weapon_NineMagazine` on SK_Nine's `magazine` bone sits inside the gun's
bounds, below the bore, centred in the grip, upright), `FirstPerson.RealArt` (the CHOPPER and NINE resolve the real mesh, anim set, sockets and finish only when the art
exists; the CHOPPER's rules JSON stays config.json's and its stage times 2.24 / 2.72), `FirstPerson.OpticTwin` (the
three pack rifles take the irons-folded twin with the scope), `FirstPerson.Clips` (on the box: every clip of every anim
set loads on the right skeleton, the reload marks rise; a clean checkout says so and passes).
