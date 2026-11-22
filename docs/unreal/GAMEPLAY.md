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
