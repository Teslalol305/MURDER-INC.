#pragma once

#include "CoreMinimal.h"

class FJsonObject;

namespace MIEnemy
{
	/** Whether the drones (Buzzards) are in the game: config.json `flow.drones` (false in the shipped game, DECISIONS.md 2026-11-27 ~22:15).
	 *  Off: no Buzzard is pooled, patrolled, waved or pursued. The code stays; flip the data (or a test's MIDronesScope) to bring them back. */
	bool DronesOn(const TSharedPtr<FJsonObject>& Config);
	/** Tests that pin the drones' behaviour: while one lives, DronesOn answers bOn whatever config.json says. */
	struct MURDERINC_API FMIDronesScope
	{
		explicit FMIDronesScope(bool bOn = true);
		~FMIDronesScope();
		int32 Saved;
	};
}

/**
 * The enemies' tuning as the AI reads it: config.json `enemiesResolved.<difficulty>` (the base tables of
 * src/config/enemies.js with that difficulty's overlay laid over them), plus `enemies.pool` and `enemies.seed`.
 * Web units (metres, seconds, radians): the enemy rules run in the web game's space (World/MIBoxWorld.h).
 * Field names are the web names.
 */
struct FMIRange
{
	double A = 0.0, B = 0.0;
};

struct FMIAiTune
{
	double SightRange = 0, Fov = 0, CloseRange = 0;
	FMIRange SenseEvery;
	double InvestigateReaction = 0, SeenDecay = 0, LoseSightAfter = 0;
	FMIRange SearchTime, NoiseTime;
	double ProvokedTime = 0, RallyOnSight = 0, RallyOnHit = 0, ExposureUp = 0, ExposureDown = 0;
	int32 Tokens = 0, TokensCrowd = 0, CrowdAbove = 0;
	double TokenGap = 0, FairRefusedWithin = 0, FairGapFactor = 0;
	double HearGunfire = 0, HearExplosion = 0, HearExplosive = 0, HearReinforcement = 0, HearEscape = 0;
	double AlertDefaultRadius = 0, GunfireEvery = 0;
	int32 PathsPerFrame = 0, PicksPerFrame = 0;
};

struct FMIGoonTune
{
	double Hp = 0, Radius = 0, Height = 0, CrouchHeight = 0, HeadRadius = 0, HeadHeight = 0, BodyRadius = 0;
	double EyeHeight = 0, GunHeight = 0, OverCoverBelow = 0, OverCoverSpreadY = 0;
	double Reaction = 0, SpawnAlertTime = 0, RunSpeed = 0, StalkSpeed = 0, PatrolSpeed = 0, Accel = 0, Decel = 0;
	double TurnRate = 0, PathTurnRate = 0, AimRate = 0;
	FMIRange Replan;
	double WaypointReach = 0, GoalReach = 0, TurnInPlace = 0, SeparationGoon = 0, SeparationPlayer = 0, StuckTime = 0;
	double PatrolRadius = 0;
	FMIRange PatrolWait;
	double InvStalkWithin = 0, InvStopWithin = 0, InvSweep = 0, InvElevated = 0, InvRestand = 0, InvRestandAfter = 0, InvStandFallback = 0;
	double RangeMin = 0, RangeMax = 0;
	double RepickPlayerMoved = 0;
	int32 RepickRandomPoints = 0, RepickArcPoints = 0;
	double RepickArc = 0;
	FMIRange RepickArcRange;
	double RepickMinMove = 0;
	double CostTravel = 0, CostAuthored = 0, CostRandom = 0, CostArc = 0, CostJitter = 0, CostSameBearing = 0, CostCrowded = 0, CostNoSight = 0, CostCover = 0;
	bool bCoverCrouchBetweenBursts = true;
	double CoverMaxStep = 0;
	double MoveAimEarlyAfter = 0;
	FMIRange MoveAimEarlyRange;
	double MoveAimEarlyChance = 0, MoveGiveUp = 0;
	double HoldTooClose = 0, HoldTooCloseTime = 0, HoldNoSightTime = 0, HoldMaxWait = 0, HoldAimTolerance = 0;
	double BurstsBeforeMoveOne = 0;
	double ShotDamage = 0;
	int32 Burst = 0;
	double BurstGap = 0, Telegraph = 0;
	FMIRange Cooldown, FirstCooldown;
	double ShotRange = 0, AimHeight = 0, SpreadFar = 0, SpreadNear = 0, SpreadPerSpeed = 0;
	double RushDamage = 0, RushRange = 0, RushWindup = 0, RushSpeed = 0, RushTime = 0, RushReach = 0, RushRecovery = 0, RushCooldown = 0;
	double Collapse = 0, BodyFade = 0, BodyStay = 0, StaggerMax = 0, Score = 0;
};

struct FMIBuzzardTune
{
	double Hp = 0, Radius = 0, HalfHeight = 0, Reaction = 0, SpawnAlertTime = 0, MaxSpeed = 0, InvestigateSpeed = 0, PatrolSpeed = 0;
	double Accel = 0, YawRate = 0;
	FMIRange PullH, PullV;
	double MinHeight = 0, FloorClearance = 0, CeilingClearance = 0;
	double FeelForward = 0, FeelForwardPerSpeed = 0, FeelDown = 0, FeelUp = 0, FeelBounce = 0;
	FMIRange PatrolRadius;
	double PatrolTurn = 0, InvRadius = 0, InvTurn = 0, InvMaxHeight = 0;
	double MaxAltitude = 0, Overshoot = 0, ClimbLook = 0, BoundsMargin = 0;
	double DeckUnder = 0, DeckOver = 0, DeckThickness = 0, DeckMargin = 0, DeckHold = 0, DeckSlide = 0;
	double DetourFar = 0, DetourMoved = 0, DetourAfter = 0, DetourDistance = 0, DetourUp = 0, DetourTime = 0;
	FMIRange OrbitRadius, OrbitRadiusClamp;
	double OrbitRadiusDrift = 0;
	FMIRange OrbitAltitude;
	double OrbitSpeed = 0, OrbitSpeedFiring = 0;
	FMIRange OrbitRethink;
	double OrbitReverseChance = 0, OrbitLostAfter = 0;
	double BoltDamage = 0, BoltSpeed = 0, BoltLife = 0;
	int32 Burst = 0;
	double BurstGap = 0, Telegraph = 0;
	FMIRange Cooldown, FirstCooldown;
	double FireRange = 0, AimTolerance = 0;
	FMIRange Lead;
	double AimHeight = 0, RecoilPush = 0, SpreadFar = 0, SpreadNear = 0, SpreadPerSpeed = 0;
	double BoltRadius = 0, BoltBottom = 0, BoltTop = 0, BoltCrouchTop = 0;
	double DamagedBelow = 0, DamagedSpread = 0, DamagedJitter = 0;
	FMIRange SmokeEvery;
	double HitKick = 0, KnockbackPerDamage = 0, KnockbackMax = 0, DeathKickUp = 0, DeathKickAlong = 0;
	double FallGravity = 0, FallMaxTime = 0, BurstRadius = 0, BurstDamage = 0, BurstPlayerScale = 0, Score = 0;
};

/** What the climb, push-out and deck rules read (a subset of the Buzzard's table, logic.js K). */
struct FMIFlightK
{
	double Radius = 0, HalfHeight = 0, MinHeight = 0, FloorClearance = 0, MaxAltitude = 0, ClimbLook = 0, BoundsMargin = 0;
	double Under = 0, Over = 0, Thickness = 0, Margin = 0, Hold = 0, Slide = 0;
};

struct MURDERINC_API FMIEnemyTune
{
	FMIGoonTune Goon;
	FMIBuzzardTune Buzzard;
	FMIAiTune Ai;
	int32 PoolGoon = 12, PoolBuzzard = 8, PoolBodies = 6, PoolBolts = 32;
	uint32 Seed = 9001;
	double ExplosiveHitFromEnemy = 9;  // weapons.common.explosiveHitFromEnemy (a bolt that hits an explosive)

	FMIFlightK Flight() const;

	/** Reads enemiesResolved.<Difficulty> (hustler, boss, kingpin) from a parsed config.json. */
	static bool Parse(const TSharedPtr<FJsonObject>& Config, FName Difficulty, FMIEnemyTune& Out, FString& OutError);
	/** Loads config.json and parses; tests and tools. */
	static bool Load(FName Difficulty, FMIEnemyTune& Out, FString& OutError);
};
