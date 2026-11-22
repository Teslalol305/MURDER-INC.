# MURDER INC. in Unreal Engine 5.9: gameplay architecture

The design that the gameplay engineers implement in parallel, one work package each. The web game (`src/`) is the
ground truth for behaviour; the port specs in `docs/unreal/spec/` say what each rule is; this document says where each
rule lives in the Unreal project, which declarations everybody shares, in what order things run, and who owns which
file. Where this document and a spec disagree about *behaviour*, the spec (and behind it the web code) wins. Where
they disagree about *Unreal structure*, this document wins; section 6 lists every such deviation as a decision.

Scope: gameplay code and the grey-box. Photoreal art, lighting and sound assets plug into the hooks described here
but are specified in `docs/unreal/ART_BIBLE.md` and specs 05, 05b, 06, 07.

## 0. Status and how to read this

### 0.1 What was read

| Input | State |
|---|---|
| `docs/DESIGN.md` (section 8 wins: daylight default) | read |
| `docs/unreal/spec/01-player.md`, `02-weapons-combat.md`, `03-enemies.md`, `04-flow.md` | read completely |
| `00-unreal-scout.md` (written for 5.8 without an engine), `08-data-export.md`, `05-level.md`, `05b-props.md`, `06-look-fx.md`, `07-ui-audio.md` | facts, behaviour, Unreal mapping and open questions read; the long art tables only skimmed |
| `unreal/MurderInc/Content/Data/{config,text,level,props,atmos}.json` | key structure of every file read; every field named in section 3.9 was checked against the file |
| The engine on the box: Unreal Engine 5.9.0, changelist 60738873, branch `++UE5+Release-5.9` | `Templates/TP_FirstPerson` (base and `Variant_Shooter`) read; engine headers and sources grepped for the classes of sections 2 to 4 |

**The box stopped answering part of the way through** (`This GPU box is not running`). Everything tagged **[B]** or
**[T]** below was read on the box before that. The engine facts that could not be checked any more are tagged **[S]**
or **[M]** and collected in Appendix B: confirm them at the first compile. Nothing was built, started or stopped on
the box.

### 0.2 Evidence tags

| Tag | Meaning |
|---|---|
| **[B]** | Read in the 5.9 engine source on the box (header path or source line given). |
| **[T]** | Used that way in the 5.9 `TP_FirstPerson` template source on the box. |
| **[S]** | From `00-unreal-scout.md`: verified there against Epic's 5.8 Python reference, or memory. |
| **[M]** | Memory only. Compile before relying on it. |

### 0.3 Words used here

- **Rule core**: a plain C++ struct or namespace with no `UObject`, no `UWorld` and no engine tick, holding the rules
  of one subsystem. It is what the automation tests exercise. The web game has the same split
  (`src/weapon/logic.js`, `src/enemies/logic.js`, `src/game/*.js`, the pure helpers of `src/player.js`).
- **Shell**: the `UObject` (actor, component, subsystem) that owns a rule core, feeds it world facts and turns its
  outputs into events, movement, pictures and sound.
- **Service**: one of the interfaces of section 3.6, reached through `UMIServices`. It is the Unreal form of the web
  game's shared object `G` (`docs/CONTRACT.md` 4); the stubs of `Core/Stubs` are the Unreal form of `src/stubs/*`.
- **Web units**: metres, seconds, radians, +Y up. **Unreal units**: centimetres, seconds, degrees, +Z up.
  Unreal (X, Y, Z) = (x, z, y) × 100; yaw 0 faces +X (east), +90 faces +Y (south).

---------------------------------------------------------------------------------------------------

## 1. Principles

### 1.1 The ten rules

1. **C++ plus data.** Every tuning number comes from `Content/Data/*.json`, loaded once by `UMIDataSubsystem` into
   the structs of section 3.9 and converted to Unreal units there. No tuning constant in code; a constant that the
   web game keeps private in a source file goes into `Content/Data/port.json` with a citation (3.9.8). No gameplay
   logic in Blueprints, no gameplay state in assets.
2. **Rule cores plus shells.** Every rule that has a number in a spec lives in a rule core that compiles and runs
   without a world. Shells are thin. A reviewer should be able to put the rule core next to the web file it ports.
3. **Parity first.** The first complete build reproduces the web game's rules exactly, including the quirks the specs
   call "as built". Every deliberate difference is listed in 1.3 or section 6 and nowhere else.
4. **Headless from a clean checkout.** The project builds, runs its automation tests and plays a grey-box run with
   zero binary assets: no `.umap`, no `.uasset`. The world is assembled at run time from JSON by code (2.6); visuals
   fall back to engine basic shapes; every art, sound and effect asset is a soft path in data that may be missing.
5. **One explicit frame order.** Simulation code never depends on the engine's tick order by accident. The order of
   section 4 is written in two places only: tick prerequisites set by `AMIGameMode`, and the slot order of
   `UMIFrameSubsystem`.
6. **Explicit clocks.** Gameplay countdowns are floats stepped inside `Step(Dt)`. No `FTimerHandle`, no latent
   actions and no wall clock in gameplay, because the flow's clocks advance only in certain states (4.2).
7. **Contract and stubs.** A work package includes only `Core/` headers and its own headers, never another
   package's. Other packages are reached through services, interfaces, events and class paths (3.6, 3.12). Every
   service has a stub that is installed first, so each package runs and is tested alone.
8. **Synchronous events.** The event bus calls handlers at once, inside the emitter's step, as the web bus does.
   Handlers must not depend on the order in which other handlers run.
9. **Seeded randomness.** Every gameplay draw comes from a seeded `FRandomStream` owned by the subsystem that the web
   stream belongs to (`game`, `weapon`, `explosives`, `enemies`). Cosmetic variation may use `FMath::FRand`. The
   sequences differ from the web's mulberry32, so parity is statistical: tests compare timings and distributions.
10. **Feet, not centres; vertical, not horizontal.** Positions in data and in every service are feet positions for
    the player and the Goon and airframe centre for the Buzzard. Fields of view in data and in every service are
    vertical degrees. The two conversions (capsule half height, horizontal field of view) happen in exactly one
    function each (3.1).

### 1.2 Where an Unreal system replaces hand-rolled web code, and how parity is kept

| Web code | Unreal system that replaces it | How parity is kept | Test that proves it |
|---|---|---|---|
| `physics.moveCapsule` for the player (flat-ended cylinder, step 0.42 m, wall slide) | `UCharacterMovementComponent` in `MOVE_Walking` / `MOVE_Falling` | Capsule 32 / 90 cm, `MaxStepHeight` 42, `bUseFlatBaseForFloorChecks` true **[B]**, `PerchRadiusThreshold` 9.6 (overhang 22.4 cm), crouched half height 57.5 with `bCrouchMaintainsBaseLocation` true **[B]** | `MurderInc.Player.Step42`, `.Ledge43`, `.CrouchClearance` |
| The velocity rule (straight move-toward in velocity space, four rates) | Override of `UCharacterMovementComponent::CalcVelocity` **[B]**: the stock friction and braking model is bypassed for walking and falling | `MIPlayerRules::ApproachVelocity` is the web function line for line; `GetMaxSpeed` returns the rule's target speed | `.Accel` (0 to 380 cm/s in 0.112 s, stop in 0.146 s over 27.8 cm) |
| Gravity in two half steps round the move | Stock `PhysFalling`: it moves by `0.5 * (OldVelocity + Velocity) * timeTick` (`CharacterMovementComponent.cpp:5037`) **[B]**, which is the same midpoint rule | `GravityScale` = 2100 / 980, `JumpZVelocity` 648.07; one jump height: the jump is applied by the rule, not by `ACharacter::Jump` hold logic | `.JumpApex` (100 cm, 0.617 s at 30, 60, 144 Hz) |
| Coyote time, jump buffer, sprint rule, crouch rule | No engine equivalent: `MIPlayerRules`, run in `UpdateCharacterStateBeforeMovement` **[B]** | Ported as written | `.Coyote`, `.JumpBuffer`, `.SprintRule` |
| Camera placement (`camera.position`, YXZ rotation, vertical FOV) | `UCameraComponent` on the capsule, written once per frame from `FMIViewRig`; first-person primitives for the gun **[T]** | The rig composes the layers of spec 01 3.11 in web order; shake, lean and landing pitch stay out of the aim; FOV conversion in one function (3.1) | `.ViewLayers`, `.RecoilKick`, `.FovTimeline` |
| Screen feedback uniforms (`render.post.*`) | Post-process settings on the camera component and `APlayerCameraManager::SetManualCameraFade` **[B]** | Same six scalars, same easing | `.Feedback` |
| `input.js` (keys, mouse, pad, edges) | Enhanced Input, actions and mapping context built in C++ from `config.json player.keys / mouseButtons / padButtons` **[T][S]** | The router turns engine callbacks into one `FMIInputFrame` per frame with the web's `down / pressed / released` semantics; every rule reads only that struct | `MurderInc.Input.Edges`, `.PadCurve` |
| Goon body movement (`moveCapsule`, 20 m/s² gravity) | `UCharacterMovementComponent` with direct velocity (override of `CalcVelocity`), `bRunPhysicsWithNoController` true **[B]** | Speed, turn and separation rules stay in `MIGoonRules`; the component only resolves collision, steps and gravity | `MurderInc.Goon.Locomotion` |
| DOM and CSS interface | Slate, built in C++ (2.7) | Layout numbers and timings from spec 07; all formatting and timers in `MIUiRules` / `UMIHudPresenter` | `MurderInc.UI.*` |
| WebAudio graph | Unreal audio components, submixes and Quartz behind `IMIAudio` (2.8) | Event → sound table and mix state machine ported; assets are soft paths | `MurderInc.Audio.EventTable` |
| three.js renderer, generated textures, sprite batches | Lumen, Nanite, virtual shadow maps, Niagara | Not a parity item: gameplay never reads the renderer | none |
| Web debris, casings, dropped gun (hand-rolled bounces) | Chaos rigid bodies or Niagara collision | Cosmetic; counts and lifetimes from data | none |
| `localStorage` settings | `UGameUserSettings` subclass and one `USaveGame` (2.9) | Same nine keys, same clamps, same change event | `MurderInc.Settings.Clamp` |

### 1.3 What is ported as written instead of being replaced, and why

| Web code | Decision | Why |
|---|---|---|
| The box world's queries: `raycast`, `lineOfSight`, `groundHeight`, `overlapsCylinder` | Ported as math over the collider list in `FMIBoxWorld` (World). Engine collision components exist too, generated from the same list, but only character movement and physical debris use them | Exact semantics that the engine's traces do not have (a box that contains the ray origin is ignored; the 3 cm explosive tie; the 5 cm line-of-sight slack); works in a pure unit test; does not depend on collision settings in `Config/` that another owner writes. One entry point (`IMIBlockWorld`), so switching to engine traces later is local. Decision D2 |
| The nav grid and A* | Ported in `FMINavGrid` (World): 0.5 m cells, 0.5 m inflation, 8 neighbours without corner cutting, string pull. Recast is not used | The web grid is exported cell for cell (`level.json nav.grid.cells`) and can be rebuilt and compared exactly; it is one ground layer by construction, which the stand-off logic of spec 03 3.7.3 depends on; it needs no nav-bounds volume, no build wait and no map. Decision D1 gives the Recast route and what was verified for it |
| Enemy hit tests (`enemies.raycast`: head sphere, body capsule, Buzzard ellipsoid) and the player as a target (cylinder, bolt capsule) | Ported as ray-versus-shape math in `MICombatRules`, with shape positions read from the pawn (sockets once art exists) | At most 20 units; exact shapes including the ellipsoid; "head keeps the hit unless the body is strictly nearer" is one line of code instead of a collision-priority puzzle |
| Enemy AI (mode machine, engage steps, tokens, fire positions, flight) | Hand-written state machines in C++, no `AAIController`, no behaviour tree, no State Tree, no EQS, no `UAIPerceptionComponent` | The template's State Tree needs binary assets; the transitions of spec 03 3.2 and 3.7.5 are the whole logic; the accumulators (`seen`, `exposure`) have no engine twin. Decision D5 |
| Damage | Own `IMIDamageable` and `FMIDamageInfo`, not `AActor::TakeDamage` / `UDamageType` | Typed kind, part, origin and credit in one struct; no engine side effects (radial impulse, knockback). Decision D6 |
| Weapon fire control, reload timelines, switch, melee | Ported as `FMIWeaponLogic` with accumulators, never anim notifies or timers | Spec 02 4.4 and its risk 13 |
| Springs of the viewmodel | Exact analytic step (`FMISpring`), never per-frame Euler | Spec 02 4.4 |
| Landing spring and stair glide | Semi-implicit Euler in sub-steps of at most 1/120 s, as the web does | The measured dips of spec 01 3.9 depend on it |

---------------------------------------------------------------------------------------------------

## 2. Module and folder map

### 2.1 The module

One runtime module, `MurderInc`, in `unreal/MurderInc/Source/MurderInc/` (fixed convention). The project skeleton,
`MurderInc.Build.cs`, the targets, `Config/` and the `.uproject` belong to the bootstrap owner (`docs/unreal/BOX.md`).
What this design needs from them:

| Need | Value | Evidence |
|---|---|---|
| Targets | `DefaultBuildSettings = BuildSettingsVersion.V8;` `IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_9;` | **[T]** |
| Module macro | `IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, MurderInc, "MurderInc");` `DEFINE_LOG_CATEGORY(LogMI)` in `MurderInc.cpp`; `DECLARE_LOG_CATEGORY_EXTERN(LogMI, Log, All);` in `MurderInc.h` | **[T]** |
| Public dependencies | `Core`, `CoreUObject`, `Engine`, `InputCore`, `EnhancedInput`, `Slate`, `SlateCore`, `Json`, `Niagara`, `PhysicsCore`, `AudioMixer` | `EnhancedInput`, `Slate` **[T]**; the rest **[S]** |
| Not needed | `AIModule`, `NavigationSystem`, `GameplayTasks`, `StateTreeModule`, `GameplayStateTreeModule`, `UMG`, `GameplayTags` | section 1.3, 2.7, 3.10 |
| Include style | Paths from the module root: `#include "Core/MITypes.h"` | the template adds its sub-folders to `PublicIncludePaths` **[T]**; we do not |
| Unity build | Either setting. File-local helpers must live in a namespace named after the file (`namespace MIPlayerMovePrivate`) so that two packages never clash inside one unity blob | rule |
| `Config/DefaultEngine.ini` | The collision lines of 3.4, `GameUserSettingsClassName` (2.9), `GlobalDefaultGameMode=/Script/MurderInc.MIGameMode`, `GameDefaultMap` (2.6.4) | **[S]** |
| `Config/DefaultGame.ini` | `+DirectoriesToAlwaysStageAsNonUFS=(Path="Data")` | **[S]** |

### 2.2 Folders, files and owners

`Source/MurderInc/` relative paths. "WP" is the owning work package (section 5). A file has exactly one owner.

| Folder | Files | WP |
|---|---|---|
| `Core/` | `MITypes.h`, `MIMath.h/.cpp`, `MICollision.h/.cpp`, `MIInterfaces.h`, `MIEvents.h`, `MIEventBus.h/.cpp`, `MIServices.h/.cpp`, `MIFrameSubsystem.h/.cpp`, `MIClassPaths.h`, `MIConsole.h/.cpp` | 00 |
| `Core/Api/` | `MIWorldApi.h`, `MICombatApi.h`, `MIEnemyApi.h`, `MIPlayerApi.h`, `MIWeaponApi.h`, `MIExplosiveApi.h`, `MIObjectiveApi.h`, `MIFlowApi.h`, `MIHudApi.h`, `MIAudioApi.h`, `MIFxApi.h` | 00 |
| `Core/Data/` | `MIData.h`, `MILevelData.h`, `MIJson.h/.cpp`, `MIDataLoader.h/.cpp`, `MIDataSubsystem.h/.cpp` | 00 |
| `Core/Settings/` | `MIGameUserSettings.h/.cpp`, `MISaveGame.h/.cpp` | 00 |
| `Core/Stubs/` | `MIStubServices.h/.cpp`, `MIStubPawn.h/.cpp`, `MIStubHUD.h/.cpp` | 00 |
| `Player/` | `MIPlayerRules.h/.cpp`, `MIViewLayers.h/.cpp`, `MIViewRig.h/.cpp`, `MIPlayerMovementComponent.h/.cpp`, `MIHealthComponent.h/.cpp`, `MIPlayerCharacter.h/.cpp`, `MIInputRouter.h/.cpp`, `MIPlayerController.h/.cpp`, `MIPlayerCameraManager.h/.cpp` | 01 |
| `Weapons/` | `MIWeaponLogic.h/.cpp`, `MIWeaponComponent.h/.cpp`, `MIViewModelRules.h/.cpp`, `MIViewModelComponent.h/.cpp`, `MICombatRules.h/.cpp`, `MICombatSubsystem.h/.cpp` | 02 |
| `World/` (block) | `MIBoxWorld.h/.cpp`, `MINavGrid.h/.cpp`, `MILevelQueries.h/.cpp`, `MIColliderComponent.h/.cpp`, `MIBlock.h/.cpp`, `MILevelBuilder.h/.cpp`, `MIBlockWorld.h/.cpp`, `MIDaylightRig.h/.cpp` | 03 |
| `World/` (actors) | `MIReelCase.h/.cpp`, `MIExtractionTruck.h/.cpp`, `MIObjectiveSubsystem.h/.cpp`, `MIExplosiveRules.h/.cpp`, `MIExplosive.h/.cpp`, `MIExplosiveSubsystem.h/.cpp`, `MITrainRules.h/.cpp`, `MIElTrain.h/.cpp`, `MIFxSubsystem.h/.cpp` | 08 |
| `Enemies/` (core) | `MIEnemyRules.h/.cpp`, `MIEnemyCore.h/.cpp`, `MIEnemyPawn.h`, `MIEnemySubsystem.h/.cpp`, `MIEnemyDummy.h/.cpp` | 04 |
| `Enemies/` (Goon) | `MIGoonRules.h/.cpp`, `MIGoonBrain.h/.cpp`, `MIGoonMovementComponent.h/.cpp`, `MIGoonFigure.h/.cpp`, `MIGoon.h/.cpp` | 05 |
| `Enemies/` (Buzzard) | `MIBuzzardRules.h/.cpp`, `MIBuzzardFlight.h/.cpp`, `MIBoltPool.h/.cpp`, `MIBuzzardFigure.h/.cpp`, `MIBuzzard.h/.cpp` | 06 |
| `Flow/` | `MIFlowRules.h/.cpp`, `MITitleCamera.h/.cpp`, `MIRadioQueue.h/.cpp`, `MISpawnDirector.h/.cpp`, `MIStoryDirector.h/.cpp`, `MIHoldoutDirector.h/.cpp`, `MIFlowDirector.h/.cpp`, `MIGameState.h/.cpp`, `MIGameMode.h/.cpp`, `MIFlowCheats.cpp` | 07 |
| `UI/` | `MIUiRules.h/.cpp`, `MIHudModel.h`, `MIHudPresenter.h/.cpp`, `MIStyle.h/.cpp`, `SMIHud.h/.cpp`, `SMIHudParts.h/.cpp`, `SMIMenus.h/.cpp`, `SMISettingsPanel.h/.cpp`, `MIHUD.h/.cpp` | 09 |
| `Audio/` | `MIAudioRules.h/.cpp`, `MISoundBank.h/.cpp`, `MIMusicDirector.h/.cpp`, `MIAmbience.h/.cpp`, `MIAudioSubsystem.h/.cpp` | 10 |
| `Tests/` | `MITestWorld.h/.cpp`, `MITestInput.h`, `MIGolden.h`, `MICoreTests.cpp`, `MIDataTests.cpp` | 00 |
| `Tests/` | `MIPlayerTests.cpp` (01), `MIWeaponTests.cpp`, `MICombatTests.cpp` (02), `MIWorldTests.cpp`, `MINavTests.cpp` (03), `MIEnemyCoreTests.cpp` (04), `MIGoonTests.cpp` (05), `MIBuzzardTests.cpp` (06), `MIFlowTests.cpp` (07), `MIExplosiveTests.cpp`, `MITrainTests.cpp` (08), `MIUiTests.cpp` (09), `MIAudioTests.cpp` (10), `MIRunTests.cpp`, `MIParityTests.cpp` (11) | as marked |

Outside `Source/`:

| Path | What | WP |
|---|---|---|
| `Content/Data/port.json` | Constants the port needs that the exporter does not write (3.9.8) | 00 creates it; each package adds its own section |
| `Content/Data/art.json` | Soft paths of every art, effect and font asset by id (3.11) | 00 creates the empty schema; the art pipeline fills it |
| `Content/Data/audio.json` | Sound definitions, event table, mix constants, music tables (spec 07 4.8 lists what is missing) | 10 |
| `Content/Python/mi_build_map.py` | Creates `/Game/Maps/L_Block` on the box (2.6.4) | 03 |
| `Content/Python/mi_build_audio.py` | Imports WAVs and creates the audio assets named in `audio.json` on the box | 10 |
| `Content/Python/mi_smoke.py`, `docs/unreal/SMOKE.md` | The MCP smoke procedures of section 5 as one script and one page | 11 |

<!-- MI-APPEND-POINT -->
