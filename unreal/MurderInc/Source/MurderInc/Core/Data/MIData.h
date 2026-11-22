#pragma once

#include "CoreMinimal.h"

/**
 * Tuning tables read from Content/Data/config.json by UMIDataSubsystem.
 * Everything here is already in Unreal units: centimetres, degrees, seconds (the file holds metres and radians).
 * Rates (1/s), times (s), shares and trauma are unit-free and unchanged. The web names are kept so that every number
 * can be diffed against src/config/*.js; the comment gives the unit after conversion.
 */

/** config.json "player.body" */
struct FMIPlayerBodyData
{
	double Radius = 0.0;          // cm, capsule radius
	double Height = 0.0;          // cm, standing collision height
	double CrouchHeight = 0.0;    // cm, crouched collision height
	double Eye = 0.0;             // cm above the feet, standing
	double CrouchEye = 0.0;       // cm above the feet, crouched
	double EyeRate = 0.0;         // 1/s, damp rate of the eye height between stances
	double StepHeight = 0.0;      // cm, highest step taken without jumping
	double AirStepHeight = 0.0;   // cm, ledge tolerance while airborne
	double BoundsMargin = 0.0;    // cm
	double StandClearance = 0.0;  // cm
	double Footprint = 0.0;       // x radius, headroom test radius
	double HeadClearance = 0.0;   // cm, the eye never comes closer than this to the top of the body
};

/** config.json "player.speed" */
struct FMIPlayerSpeedData
{
	double Walk = 0.0;       // cm/s
	double Sprint = 0.0;     // cm/s
	double Crouch = 0.0;     // cm/s
	double Ads = 0.0;        // cm/s cap at full aim
	double Backpedal = 0.0;  // factor at full backward input
	double Moving = 0.0;     // cm/s, below this the player stands still (stride)
};

/** config.json "player.accel": rates of the straight move toward the wish velocity. */
struct FMIPlayerAccelData
{
	double Ground = 0.0;      // cm/s^2, grounded with input
	double GroundStop = 0.0;  // cm/s^2, grounded without input
	double Air = 0.0;         // cm/s^2
	double AirStop = 0.0;     // cm/s^2
};

/** config.json "player.jump" */
struct FMIPlayerJumpData
{
	double Gravity = 0.0;   // cm/s^2, positive
	double Apex = 0.0;      // cm
	double Coyote = 0.0;    // s
	double Buffer = 0.0;    // s
	double Terminal = 0.0;  // cm/s

	/** Take-off speed that reaches Apex under Gravity, cm/s. */
	double LaunchSpeed() const { return FMath::Sqrt(2.0 * Gravity * Apex); }
};

/** config.json "player.sprint" */
struct FMIPlayerSprintData
{
	double MinForward = 0.0;
	double MaxStrafe = 0.0;
	double MaxAds = 0.0;
	double MinSpeedFrac = 0.0;  // of walk speed
};

/** config.json "player.stride" */
struct FMIPlayerStrideData
{
	double Walk = 0.0;    // cm per footstep
	double Sprint = 0.0;  // cm
	double Crouch = 0.0;  // cm
	double SettleRate = 0.0;
	double AfterLanding = 0.0;  // stride phase set on landing
};

/** config.json "player.fov": vertical degrees, as in the web game. */
struct FMIPlayerFovData
{
	double Base = 0.0;
	double Min = 0.0;
	double Max = 0.0;
	double SprintAdd = 0.0;
	double Ads = 0.0;
	double Rate = 0.0;
	double RateAds = 0.0;
	double AdsBandLow = 0.0;
	double AdsBandHigh = 0.0;
	double Viewmodel = 0.0;
};

/** config.json "player.look" and "player.input" */
struct FMIPlayerLookData
{
	double PitchLimit = 0.0;            // degrees up and down
	double ViewPitchLimit = 0.0;        // degrees, aim + recoil offset
	double AdsScale = 0.0;              // look-rate factor at full aim
	double MouseDegreesPerCount = 0.0;  // degrees per mouse count at sensitivity 1
	double MouseGlitch = 0.0;           // counts: a larger single event is discarded
};

/** config.json "player.health" */
struct FMIPlayerHealthData
{
	double Max = 0.0;
	double RegenDelay = 0.0;  // s (default; the difficulty overrides)
	double RegenRate = 0.0;   // HP/s
	double LowWarning = 0.0;
	double HurtBase = 0.0;
	double HurtPerDamage = 0.0;
	double HurtDecay = 0.0;   // 1/s
	double LowFrom = 0.0;     // health fraction where the low-health value starts
	double LowTo = 0.0;       // fraction where it is full
	double LowRate = 0.0;
};

/** config.json "player.fall" */
struct FMIPlayerFallData
{
	double LandMinAir = 0.0;      // s
	double DamageFrom = 0.0;      // cm/s
	double DamagePerSpeed = 0.0;  // HP per cm/s
	double ShakeFrom = 0.0;       // cm/s
	double ShakePerSpeed = 0.0;   // trauma per cm/s
	double ShakeMax = 0.0;
	double DipPerSpeed = 0.0;     // spring impulse per landing speed (unit-free)
	double DipMax = 0.0;          // cm/s
};

/** config.json "player.bob" */
struct FMIPlayerBobData
{
	double Rate = 0.0;
	double Vertical = 0.0;         // cm
	double Lateral = 0.0;          // cm
	double RollFromLateral = 0.0;  // degrees per cm
	double SprintScale = 0.0;
	double CrouchScale = 0.0;
	double AdsScale = 0.0;
	double StrafeRoll = 0.0;       // degrees at sprint speed sideways
	double StrafeRollRate = 0.0;
	double StrafeRollAds = 0.0;
	double SpringStiffness = 0.0;  // 1/s^2
	double SpringDamping = 0.0;    // 1/s
	double SpringMin = 0.0;        // cm
	double SpringMax = 0.0;        // cm
	double SpringPitch = 0.0;      // degrees per cm (a dip looks down)
	double StepFrequency = 0.0;    // rad/s
	double StepMax = 0.0;          // cm
};

/** config.json "player.recoil" */
struct FMIPlayerRecoilData
{
	double Keep = 0.0;
	double MaxPitch = 0.0;  // degrees
	double MaxYaw = 0.0;    // degrees
	double Chase = 0.0;
	double Hold = 0.0;      // s
	double Recover = 0.0;
};

/** config.json "player.shake" */
struct FMIPlayerShakeData
{
	double Decay = 0.0;
	double Pitch = 0.0;  // degrees per sine at trauma 1
	double Yaw = 0.0;
	double Roll = 0.0;
	double FreqPitch[2] = {0.0, 0.0};  // rad/s
	double FreqYaw[2] = {0.0, 0.0};
	double FreqRoll[2] = {0.0, 0.0};
	double OnHitBase = 0.0;
	double OnHitPerDamage = 0.0;
	double BlastRange = 0.0;  // cm
	double BlastBase = 0.0;
	double BlastScale = 0.0;
	double BlastSmall = 0.0;
	double SustainBelow = 0.0;
	double SustainMax = 0.0;
	double SustainRate = 0.0;
};

/** config.json "player.death" */
struct FMIPlayerDeathData
{
	double Collapse = 0.0;       // s
	double Eye = 0.0;            // cm
	double EyeRate = 0.0;
	double Roll = 0.0;           // degrees
	double Pitch = 0.0;          // degrees (negative: looks down)
	double PitchBounce = 0.0;    // degrees
	double Slide = 0.0;          // 1/s
	double CapsuleHeight = 0.0;  // cm
};

struct FMIPlayerData
{
	FMIPlayerBodyData Body;
	FMIPlayerSpeedData Speed;
	FMIPlayerAccelData Accel;
	FMIPlayerJumpData Jump;
	FMIPlayerSprintData Sprint;
	FMIPlayerStrideData Stride;
	FMIPlayerFovData Fov;
	FMIPlayerLookData Look;
	FMIPlayerHealthData Health;
	FMIPlayerFallData Fall;
	FMIPlayerBobData Bob;
	FMIPlayerRecoilData Recoil;
	FMIPlayerShakeData Shake;
	FMIPlayerDeathData Death;
};

/** config.json "weapons.<gun>.reload": marks in seconds from the start. A bolt mark below zero means none. */
struct FMIWeaponReloadData
{
	double Tactical = 0.0;
	double Empty = 0.0;
	double MagOut = 0.0;
	double MagIn = 0.0;
	double BoltTactical = -1.0;  // pressCheck[0] (CHOPPER only)
	double BoltEmpty = -1.0;     // boltBack (CHOPPER) or slideRelease (NINE)
};

/** config.json "weapons.<gun>.spread": cone half-angles in degrees; Shot and Decay are bloom units. */
struct FMIWeaponSpreadData
{
	double Hip = 0.0;
	double Ads = 0.0;
	double MoveHip = 0.0;
	double MoveAds = 0.0;
	double BloomHip = 0.0;
	double BloomAds = 0.0;
	double Air = 0.0;
	double Crouch = 0.0;
	double Shot = 0.0;
	double Decay = 0.0;
};

/** config.json "weapons.<gun>.recoil": camera kicks in degrees. bWeave = the CHOPPER's climb-then-weave pattern. */
struct FMIWeaponRecoilData
{
	double Pitch = 0.0;
	double PitchRandomMin = 1.0;
	double PitchRandomMax = 1.0;
	bool bWeave = false;
	int32 LateFrom = 0;
	double LateScale = 1.0;
	double YawEarly = 0.0;
	int32 WeaveFrom = 0;
	double WeaveAmp = 0.0;
	double WeaveFreq = 0.0;   // rad per round
	double WeaveRandom = 0.0;
	double Yaw = 0.0;         // the NINE's symmetric yaw
	double Shake = 0.0;       // trauma per round
};

/** config.json "weapons.chopper" / "weapons.nine" */
struct FMIWeaponDef
{
	FName Id;
	FString Name;
	int32 Slot = 0;
	bool bAuto = false;
	double Damage = 0.0;
	double Rpm = 0.0;
	int32 MagSize = 0;
	double Reserve = 0.0;          // rounds; infinite for the NINE (the file says "Infinity")
	double Range = 0.0;            // cm
	double AdsTime = 0.0;          // s
	double FireBuffer = 0.0;       // s, 0 = none
	double DryCooldown = 0.0;      // s
	double DryReloadDelay = 0.0;   // s
	FMIWeaponReloadData Reload;
	FMIWeaponSpreadData Spread;
	FMIWeaponRecoilData Recoil;
	double WallStart = 0.0;        // cm
	double WallFull = 0.0;         // cm
	double FlashScale = 0.0;
	double FlashLight = 0.0;
	FColor FlashColor = FColor::White;
	double FlashRange = 0.0;       // cm
	double FlashTtl = 0.0;
	double RumbleStrong = 0.0;
	double RumbleWeak = 0.0;
	double RumbleMs = 0.0;

	double Interval() const { return Rpm > 0.0 ? 60.0 / Rpm : 0.0; }
};

/** config.json "weapons.common" (and the pad aim slow-down of "player.input.pad") */
struct FMIWeaponCommonData
{
	double HeadMultiplier = 0.0;
	double Holster = 0.0;
	double Draw = 0.0;
	double BurstReset = 0.0;
	int32 MaxCatchUpShots = 0;
	double SpreadRate = 0.0;
	double BloomHold = 0.0;
	double SpreadSpeedRef = 0.0;  // cm/s
	double AdsRecoilScale = 0.0;
	double CrouchRecoilScale = 0.0;
	double SprintRate = 0.0;
	double SprintHurry = 0.0;
	double SprintFireGate = 0.0;
	double SprintAdsGate = 0.0;
	double FiringHold = 0.0;
	double WallEvery = 0.0;
	double WallRate = 0.0;
	double WallAdsScale = 0.0;
	double HeatPerShot = 0.0;
	double HeatMax = 0.0;
	double HeatCool = 0.0;
	FColor TracerColor = FColor::White;
	double TracerSpeed = 0.0;     // cm/s
	double LowAmmoFraction = 0.0;
	double AdsFlashScale = 0.0;
	double ExplosiveHitFromEnemy = 0.0;
	double AimSlow = 0.0;
	double AimRange = 0.0;        // cm
	double AimEvery = 0.0;
	double AimRate = 0.0;
};

/** config.json "weapons.melee" */
struct FMIMeleeData
{
	double Duration = 0.0;
	double HitAt = 0.0;
	double Reach = 0.0;    // cm
	double Cone = 0.0;     // degrees, full apex angle
	double Damage = 0.0;
	double Cooldown = 0.0;
	bool bCancelsReload = false;
	bool bBlockedWhileSwitching = false;
	double Shake = 0.0;
};

struct FMIWeaponsData
{
	TArray<FMIWeaponDef> Guns;  // in weapons.common.order: [0] is the gun a run starts with
	FMIWeaponCommonData Common;
	FMIMeleeData Melee;
};

/** config.json "explosives.kinds.<kind>" */
struct FMIExplosiveKindData
{
	FName Id;
	FString Prop;
	double Hp = 0.0;
	double Fuse = 0.0;    // s
	double Radius = 0.0;  // cm
	double Damage = 0.0;
	double Size = 0.0;    // chain "size"
	FVector Box = FVector::ZeroVector;  // cm: X length, Y width, Z height (web x, z, y)
	double Jet = 0.0;
};

/**
 * config.json "explosives.rules". The three formulas travel as source text; their coefficients are read from it at
 * load time and checked against the samples the running game answered.
 */
struct FMIExplosiveRulesData
{
	double PopFuse = 0.0;
	double PlayerDamageScale = 0.0;
	double DamageFromEnemyRound = 0.0;
	double ShakeReach = 0.0;   // cm
	double AlertRadius = 0.0;  // cm
	double ChainBase = 0.0, ChainPerSize = 0.0;                 // metres: range = base + perSize * size
	double FuseBase = 0.0, FuseRoll = 0.0, FusePerMetre = 0.0;  // s
	double SizeMax = 0.0, SizeMin = 0.0, SizeBase = 0.0, SizePerMetre = 0.0;

	double ChainRange(double Size) const { return (ChainBase + ChainPerSize * Size) * 100.0; }
	double ChainFuse(double DistanceCm, double Roll) const { return FuseBase + Roll * FuseRoll + FusePerMetre * DistanceCm / 100.0; }
	double SizeFromRadius(double RadiusCm) const
	{
		return FMath::Min(SizeMax, FMath::Max(SizeMin, SizeBase + SizePerMetre * RadiusCm / 100.0));
	}
};

struct FMIExplosivesData
{
	TArray<FMIExplosiveKindData> Kinds;
	FMIExplosiveRulesData Rules;

	const FMIExplosiveKindData* FindKind(FName Id) const
	{
		return Kinds.FindByPredicate([Id](const FMIExplosiveKindData& K) { return K.Id == Id; });
	}
};

/** config.json "flow.difficulty.<name>.regen" */
struct FMIDifficultyData
{
	FName Id;
	double RegenDelay = 0.0;
	double RegenRate = 0.0;
};

/** config.json "settings.defaults" */
struct FMISettingsData
{
	double Sensitivity = 0.0;
	bool bInvertY = false;
	double Fov = 0.0;
};

struct FMIConfigData
{
	FString Game;      // meta.game
	int32 Schema = 0;  // meta.schema
	int32 Seed = 0;    // meta.seed
	FMIPlayerData Player;
	FMIWeaponsData Weapons;
	FMIExplosivesData Explosives;
	TArray<FMIDifficultyData> Difficulties;
	FName DefaultDifficulty;
	FMISettingsData Settings;

	const FMIDifficultyData* FindDifficulty(FName Id) const
	{
		return Difficulties.FindByPredicate([Id](const FMIDifficultyData& D) { return D.Id == Id; });
	}
	const FMIWeaponDef* FindGun(FName Id) const
	{
		return Weapons.Guns.FindByPredicate([Id](const FMIWeaponDef& G) { return G.Id == Id; });
	}
};
