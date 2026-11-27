#include "Enemies/MIEnemyTune.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

namespace
{
	/** Reads dotted paths from one table and remembers the first one that is missing. */
	struct FReader
	{
		TSharedPtr<FJsonObject> Root;
		FString Missing;

		TSharedPtr<FJsonValue> Find(const FString& Path)
		{
			TArray<FString> Parts;
			Path.ParseIntoArray(Parts, TEXT("."));
			TSharedPtr<FJsonObject> O = Root;
			for (int32 I = 0; I + 1 < Parts.Num() && O.IsValid(); ++I)
			{
				const TSharedPtr<FJsonObject>* Next;
				O = O->TryGetObjectField(Parts[I], Next) ? *Next : nullptr;
			}
			TSharedPtr<FJsonValue> V = O.IsValid() ? O->TryGetField(Parts.Last()) : nullptr;
			if (!V.IsValid() && Missing.IsEmpty())
			{
				Missing = Path;
			}
			return V;
		}
		void Num(const TCHAR* Path, double& Out)
		{
			if (TSharedPtr<FJsonValue> V = Find(Path))
			{
				Out = V->AsNumber();
			}
		}
		void Num(const TCHAR* Path, int32& Out)
		{
			if (TSharedPtr<FJsonValue> V = Find(Path))
			{
				Out = static_cast<int32>(V->AsNumber());
			}
		}
		void Bool(const TCHAR* Path, bool& Out)
		{
			if (TSharedPtr<FJsonValue> V = Find(Path))
			{
				Out = V->AsBool();
			}
		}
		void Range(const TCHAR* Path, FMIRange& Out)
		{
			if (TSharedPtr<FJsonValue> V = Find(Path))
			{
				const TArray<TSharedPtr<FJsonValue>>& A = V->AsArray();
				if (A.Num() >= 2)
				{
					Out.A = A[0]->AsNumber();
					Out.B = A[1]->AsNumber();
				}
			}
		}
	};
}

FMIFlightK FMIEnemyTune::Flight() const
{
	const FMIBuzzardTune& T = Buzzard;
	FMIFlightK K;
	K.Radius = T.Radius;
	K.HalfHeight = T.HalfHeight;
	K.MinHeight = T.MinHeight;
	K.FloorClearance = T.FloorClearance;
	K.MaxAltitude = T.MaxAltitude;
	K.ClimbLook = T.ClimbLook;
	K.BoundsMargin = T.BoundsMargin;
	K.Under = T.DeckUnder;
	K.Over = T.DeckOver;
	K.Thickness = T.DeckThickness;
	K.Margin = T.DeckMargin;
	K.Hold = T.DeckHold;
	K.Slide = T.DeckSlide;
	return K;
}

namespace MIEnemy
{
	static int32 GDronesOverride = -1;  // -1: the data decides
	bool DronesOn(const TSharedPtr<FJsonObject>& Config)
	{
		if (GDronesOverride >= 0)
		{
			return GDronesOverride == 1;
		}
		const TSharedPtr<FJsonObject>* Flow;
		bool bOn = true;
		if (Config.IsValid() && Config->TryGetObjectField(TEXT("flow"), Flow))
		{
			(*Flow)->TryGetBoolField(TEXT("drones"), bOn);
		}
		return bOn;
	}
	FMIDronesScope::FMIDronesScope(bool bOn) : Saved(GDronesOverride) { GDronesOverride = bOn ? 1 : 0; }
	FMIDronesScope::~FMIDronesScope() { GDronesOverride = Saved; }
}

bool FMIEnemyTune::Parse(const TSharedPtr<FJsonObject>& Config, FName Difficulty, FMIEnemyTune& Out, FString& OutError)
{
	const TSharedPtr<FJsonObject>* Resolved;
	const TSharedPtr<FJsonObject>* Table;
	if (!Config.IsValid() || !Config->TryGetObjectField(TEXT("enemiesResolved"), Resolved) || !(*Resolved)->TryGetObjectField(Difficulty.ToString(), Table))
	{
		OutError = FString::Printf(TEXT("config.json has no enemiesResolved.%s"), *Difficulty.ToString());
		return false;
	}
	FReader R{*Table};
	FMIAiTune& A = Out.Ai;
	R.Num(TEXT("ai.sightRange"), A.SightRange);
	R.Num(TEXT("ai.fov"), A.Fov);
	R.Num(TEXT("ai.closeRange"), A.CloseRange);
	R.Range(TEXT("ai.senseEvery"), A.SenseEvery);
	R.Num(TEXT("ai.investigateReaction"), A.InvestigateReaction);
	R.Num(TEXT("ai.seenDecay"), A.SeenDecay);
	R.Num(TEXT("ai.loseSightAfter"), A.LoseSightAfter);
	R.Range(TEXT("ai.searchTime"), A.SearchTime);
	R.Range(TEXT("ai.noiseTime"), A.NoiseTime);
	R.Num(TEXT("ai.provokedTime"), A.ProvokedTime);
	R.Num(TEXT("ai.rallyOnSight"), A.RallyOnSight);
	R.Num(TEXT("ai.rallyOnHit"), A.RallyOnHit);
	R.Num(TEXT("ai.exposureUp"), A.ExposureUp);
	R.Num(TEXT("ai.exposureDown"), A.ExposureDown);
	R.Num(TEXT("ai.tokens"), A.Tokens);
	R.Num(TEXT("ai.tokensCrowd"), A.TokensCrowd);
	R.Num(TEXT("ai.crowdAbove"), A.CrowdAbove);
	R.Num(TEXT("ai.tokenGap"), A.TokenGap);
	R.Num(TEXT("ai.tokenFairness.refusedWithin"), A.FairRefusedWithin);
	R.Num(TEXT("ai.tokenFairness.gapFactor"), A.FairGapFactor);
	R.Num(TEXT("ai.hear.gunfire"), A.HearGunfire);
	R.Num(TEXT("ai.hear.explosion"), A.HearExplosion);
	R.Num(TEXT("ai.hear.explosive"), A.HearExplosive);
	R.Num(TEXT("ai.hear.reinforcement"), A.HearReinforcement);
	R.Num(TEXT("ai.hear.escape"), A.HearEscape);
	R.Num(TEXT("ai.alertDefaultRadius"), A.AlertDefaultRadius);
	R.Num(TEXT("ai.gunfireEvery"), A.GunfireEvery);
	R.Num(TEXT("ai.pathsPerFrame"), A.PathsPerFrame);
	R.Num(TEXT("ai.picksPerFrame"), A.PicksPerFrame);

	FMIGoonTune& G = Out.Goon;
	R.Num(TEXT("goon.hp"), G.Hp);
	R.Num(TEXT("goon.radius"), G.Radius);
	R.Num(TEXT("goon.height"), G.Height);
	R.Num(TEXT("goon.crouchHeight"), G.CrouchHeight);
	R.Num(TEXT("goon.head.radius"), G.HeadRadius);
	R.Num(TEXT("goon.head.height"), G.HeadHeight);
	R.Num(TEXT("goon.bodyRadius"), G.BodyRadius);
	R.Num(TEXT("goon.eyeHeight"), G.EyeHeight);
	R.Num(TEXT("goon.gunHeight"), G.GunHeight);
	R.Num(TEXT("goon.overCover.below"), G.OverCoverBelow);
	R.Num(TEXT("goon.overCover.spreadY"), G.OverCoverSpreadY);
	R.Num(TEXT("goon.reaction"), G.Reaction);
	R.Num(TEXT("goon.spawnAlertTime"), G.SpawnAlertTime);
	R.Num(TEXT("goon.runSpeed"), G.RunSpeed);
	R.Num(TEXT("goon.stalkSpeed"), G.StalkSpeed);
	R.Num(TEXT("goon.patrolSpeed"), G.PatrolSpeed);
	R.Num(TEXT("goon.accel"), G.Accel);
	R.Num(TEXT("goon.decel"), G.Decel);
	R.Num(TEXT("goon.turnRate"), G.TurnRate);
	R.Num(TEXT("goon.pathTurnRate"), G.PathTurnRate);
	R.Num(TEXT("goon.aimRate"), G.AimRate);
	R.Range(TEXT("goon.replan"), G.Replan);
	R.Num(TEXT("goon.waypointReach"), G.WaypointReach);
	R.Num(TEXT("goon.goalReach"), G.GoalReach);
	R.Num(TEXT("goon.turnInPlace"), G.TurnInPlace);
	R.Num(TEXT("goon.separation.goon"), G.SeparationGoon);
	R.Num(TEXT("goon.separation.player"), G.SeparationPlayer);
	R.Num(TEXT("goon.stuckTime"), G.StuckTime);
	R.Num(TEXT("goon.patrol.radius"), G.PatrolRadius);
	R.Range(TEXT("goon.patrol.wait"), G.PatrolWait);
	R.Num(TEXT("goon.investigate.stalkWithin"), G.InvStalkWithin);
	R.Num(TEXT("goon.investigate.stopWithin"), G.InvStopWithin);
	R.Num(TEXT("goon.investigate.sweep"), G.InvSweep);
	R.Num(TEXT("goon.investigate.elevated"), G.InvElevated);
	R.Num(TEXT("goon.investigate.restand"), G.InvRestand);
	R.Num(TEXT("goon.investigate.restandAfter"), G.InvRestandAfter);
	R.Num(TEXT("goon.investigate.standFallback"), G.InvStandFallback);
	R.Num(TEXT("goon.rangeMin"), G.RangeMin);
	R.Num(TEXT("goon.rangeMax"), G.RangeMax);
	R.Num(TEXT("goon.repick.playerMoved"), G.RepickPlayerMoved);
	R.Num(TEXT("goon.repick.randomPoints"), G.RepickRandomPoints);
	R.Num(TEXT("goon.repick.arcPoints"), G.RepickArcPoints);
	R.Num(TEXT("goon.repick.arc"), G.RepickArc);
	R.Range(TEXT("goon.repick.arcRange"), G.RepickArcRange);
	R.Num(TEXT("goon.repick.minMove"), G.RepickMinMove);
	R.Num(TEXT("goon.positionCost.travel"), G.CostTravel);
	R.Num(TEXT("goon.positionCost.authored"), G.CostAuthored);
	R.Num(TEXT("goon.positionCost.random"), G.CostRandom);
	R.Num(TEXT("goon.positionCost.arc"), G.CostArc);
	R.Num(TEXT("goon.positionCost.jitter"), G.CostJitter);
	R.Num(TEXT("goon.positionCost.sameBearing"), G.CostSameBearing);
	R.Num(TEXT("goon.positionCost.crowded"), G.CostCrowded);
	R.Num(TEXT("goon.positionCost.noSight"), G.CostNoSight);
	R.Num(TEXT("goon.positionCost.cover"), G.CostCover);
	R.Bool(TEXT("goon.cover.crouchBetweenBursts"), G.bCoverCrouchBetweenBursts);
	R.Num(TEXT("goon.cover.maxStep"), G.CoverMaxStep);
	R.Num(TEXT("goon.move.aimEarlyAfter"), G.MoveAimEarlyAfter);
	R.Range(TEXT("goon.move.aimEarlyRange"), G.MoveAimEarlyRange);
	R.Num(TEXT("goon.move.aimEarlyChance"), G.MoveAimEarlyChance);
	R.Num(TEXT("goon.move.giveUp"), G.MoveGiveUp);
	R.Num(TEXT("goon.hold.tooClose"), G.HoldTooClose);
	R.Num(TEXT("goon.hold.tooCloseTime"), G.HoldTooCloseTime);
	R.Num(TEXT("goon.hold.noSightTime"), G.HoldNoSightTime);
	R.Num(TEXT("goon.hold.maxWait"), G.HoldMaxWait);
	R.Num(TEXT("goon.hold.aimTolerance"), G.HoldAimTolerance);
	R.Num(TEXT("goon.burstsBeforeMove.one"), G.BurstsBeforeMoveOne);
	R.Num(TEXT("goon.shotDamage"), G.ShotDamage);
	R.Num(TEXT("goon.burst"), G.Burst);
	R.Num(TEXT("goon.burstGap"), G.BurstGap);
	R.Num(TEXT("goon.telegraph"), G.Telegraph);
	R.Range(TEXT("goon.cooldown"), G.Cooldown);
	R.Range(TEXT("goon.firstCooldown"), G.FirstCooldown);
	R.Num(TEXT("goon.shotRange"), G.ShotRange);
	R.Num(TEXT("goon.aimHeight"), G.AimHeight);
	R.Num(TEXT("goon.spreadFar"), G.SpreadFar);
	R.Num(TEXT("goon.spreadNear"), G.SpreadNear);
	R.Num(TEXT("goon.spreadPerSpeed"), G.SpreadPerSpeed);
	R.Num(TEXT("goon.rushDamage"), G.RushDamage);
	R.Num(TEXT("goon.rush.range"), G.RushRange);
	R.Num(TEXT("goon.rush.windup"), G.RushWindup);
	R.Num(TEXT("goon.rush.speed"), G.RushSpeed);
	R.Num(TEXT("goon.rush.time"), G.RushTime);
	R.Num(TEXT("goon.rush.reach"), G.RushReach);
	R.Num(TEXT("goon.rush.recovery"), G.RushRecovery);
	R.Num(TEXT("goon.rush.cooldown"), G.RushCooldown);
	R.Num(TEXT("goon.collapse"), G.Collapse);
	R.Num(TEXT("goon.bodyFade"), G.BodyFade);
	R.Num(TEXT("goon.bodyStay"), G.BodyStay);
	R.Num(TEXT("goon.staggerMax"), G.StaggerMax);
	R.Num(TEXT("goon.score"), G.Score);

	FMIBuzzardTune& B = Out.Buzzard;
	R.Num(TEXT("buzzard.hp"), B.Hp);
	R.Num(TEXT("buzzard.radius"), B.Radius);
	R.Num(TEXT("buzzard.halfHeight"), B.HalfHeight);
	R.Num(TEXT("buzzard.reaction"), B.Reaction);
	R.Num(TEXT("buzzard.spawnAlertTime"), B.SpawnAlertTime);
	R.Num(TEXT("buzzard.maxSpeed"), B.MaxSpeed);
	R.Num(TEXT("buzzard.investigateSpeed"), B.InvestigateSpeed);
	R.Num(TEXT("buzzard.patrolSpeed"), B.PatrolSpeed);
	R.Num(TEXT("buzzard.accel"), B.Accel);
	R.Num(TEXT("buzzard.yawRate"), B.YawRate);
	R.Range(TEXT("buzzard.pull.horizontal"), B.PullH);
	R.Range(TEXT("buzzard.pull.vertical"), B.PullV);
	R.Num(TEXT("buzzard.minHeight"), B.MinHeight);
	R.Num(TEXT("buzzard.floorClearance"), B.FloorClearance);
	R.Num(TEXT("buzzard.ceilingClearance"), B.CeilingClearance);
	R.Num(TEXT("buzzard.feelers.forward"), B.FeelForward);
	R.Num(TEXT("buzzard.feelers.forwardPerSpeed"), B.FeelForwardPerSpeed);
	R.Num(TEXT("buzzard.feelers.down"), B.FeelDown);
	R.Num(TEXT("buzzard.feelers.up"), B.FeelUp);
	R.Num(TEXT("buzzard.feelers.bounce"), B.FeelBounce);
	R.Range(TEXT("buzzard.patrol.radius"), B.PatrolRadius);
	R.Num(TEXT("buzzard.patrol.turn"), B.PatrolTurn);
	R.Num(TEXT("buzzard.investigate.radius"), B.InvRadius);
	R.Num(TEXT("buzzard.investigate.turn"), B.InvTurn);
	R.Num(TEXT("buzzard.investigate.maxHeight"), B.InvMaxHeight);
	R.Num(TEXT("buzzard.maxAltitude"), B.MaxAltitude);
	R.Num(TEXT("buzzard.overshoot"), B.Overshoot);
	R.Num(TEXT("buzzard.climbLook"), B.ClimbLook);
	R.Num(TEXT("buzzard.boundsMargin"), B.BoundsMargin);
	R.Num(TEXT("buzzard.deck.under"), B.DeckUnder);
	R.Num(TEXT("buzzard.deck.over"), B.DeckOver);
	R.Num(TEXT("buzzard.deck.thickness"), B.DeckThickness);
	R.Num(TEXT("buzzard.deck.margin"), B.DeckMargin);
	R.Num(TEXT("buzzard.deck.hold"), B.DeckHold);
	R.Num(TEXT("buzzard.deck.slide"), B.DeckSlide);
	R.Num(TEXT("buzzard.detour.far"), B.DetourFar);
	R.Num(TEXT("buzzard.detour.moved"), B.DetourMoved);
	R.Num(TEXT("buzzard.detour.after"), B.DetourAfter);
	R.Num(TEXT("buzzard.detour.distance"), B.DetourDistance);
	R.Num(TEXT("buzzard.detour.up"), B.DetourUp);
	R.Num(TEXT("buzzard.detour.time"), B.DetourTime);
	R.Range(TEXT("buzzard.orbit.radius"), B.OrbitRadius);
	R.Range(TEXT("buzzard.orbit.radiusClamp"), B.OrbitRadiusClamp);
	R.Num(TEXT("buzzard.orbit.radiusDrift"), B.OrbitRadiusDrift);
	R.Range(TEXT("buzzard.orbit.altitude"), B.OrbitAltitude);
	R.Num(TEXT("buzzard.orbit.speed"), B.OrbitSpeed);
	R.Num(TEXT("buzzard.orbit.speedFiring"), B.OrbitSpeedFiring);
	R.Range(TEXT("buzzard.orbit.rethink"), B.OrbitRethink);
	R.Num(TEXT("buzzard.orbit.reverseChance"), B.OrbitReverseChance);
	R.Num(TEXT("buzzard.orbit.lostAfter"), B.OrbitLostAfter);
	R.Num(TEXT("buzzard.boltDamage"), B.BoltDamage);
	R.Num(TEXT("buzzard.boltSpeed"), B.BoltSpeed);
	R.Num(TEXT("buzzard.boltLife"), B.BoltLife);
	R.Num(TEXT("buzzard.burst"), B.Burst);
	R.Num(TEXT("buzzard.burstGap"), B.BurstGap);
	R.Num(TEXT("buzzard.telegraph"), B.Telegraph);
	R.Range(TEXT("buzzard.cooldown"), B.Cooldown);
	R.Range(TEXT("buzzard.firstCooldown"), B.FirstCooldown);
	R.Num(TEXT("buzzard.fireRange"), B.FireRange);
	R.Num(TEXT("buzzard.aimTolerance"), B.AimTolerance);
	R.Range(TEXT("buzzard.lead"), B.Lead);
	R.Num(TEXT("buzzard.aimHeight"), B.AimHeight);
	R.Num(TEXT("buzzard.recoilPush"), B.RecoilPush);
	R.Num(TEXT("buzzard.spreadFar"), B.SpreadFar);
	R.Num(TEXT("buzzard.spreadNear"), B.SpreadNear);
	R.Num(TEXT("buzzard.spreadPerSpeed"), B.SpreadPerSpeed);
	R.Num(TEXT("buzzard.boltTarget.radius"), B.BoltRadius);
	R.Num(TEXT("buzzard.boltTarget.bottom"), B.BoltBottom);
	R.Num(TEXT("buzzard.boltTarget.top"), B.BoltTop);
	R.Num(TEXT("buzzard.boltTarget.crouchTop"), B.BoltCrouchTop);
	R.Num(TEXT("buzzard.damagedBelow"), B.DamagedBelow);
	R.Num(TEXT("buzzard.damagedSpread"), B.DamagedSpread);
	R.Num(TEXT("buzzard.damagedJitter"), B.DamagedJitter);
	R.Range(TEXT("buzzard.smokeEvery"), B.SmokeEvery);
	R.Num(TEXT("buzzard.hitKick"), B.HitKick);
	R.Num(TEXT("buzzard.knockback.perDamage"), B.KnockbackPerDamage);
	R.Num(TEXT("buzzard.knockback.max"), B.KnockbackMax);
	R.Num(TEXT("buzzard.deathKick.up"), B.DeathKickUp);
	R.Num(TEXT("buzzard.deathKick.along"), B.DeathKickAlong);
	R.Num(TEXT("buzzard.fallGravity"), B.FallGravity);
	R.Num(TEXT("buzzard.fallMaxTime"), B.FallMaxTime);
	R.Num(TEXT("buzzard.burstRadius"), B.BurstRadius);
	R.Num(TEXT("buzzard.burstDamage"), B.BurstDamage);
	R.Num(TEXT("buzzard.burstPlayerScale"), B.BurstPlayerScale);
	R.Num(TEXT("buzzard.score"), B.Score);
	if (!R.Missing.IsEmpty())
	{
		OutError = FString::Printf(TEXT("config.json enemiesResolved.%s.%s is missing"), *Difficulty.ToString(), *R.Missing);
		return false;
	}

	FReader E{Config};
	E.Num(TEXT("enemies.pool.goon"), Out.PoolGoon);
	E.Num(TEXT("enemies.pool.buzzard"), Out.PoolBuzzard);
	if (!MIEnemy::DronesOn(Config))
	{
		Out.PoolBuzzard = 0;  // no Buzzard actor, no slot: nothing can spawn one
	}
	E.Num(TEXT("enemies.pool.bodies"), Out.PoolBodies);
	E.Num(TEXT("enemies.pool.bolts"), Out.PoolBolts);
	double Seed = 9001;
	E.Num(TEXT("enemies.seed"), Seed);
	Out.Seed = static_cast<uint32>(Seed);
	E.Num(TEXT("weapons.common.explosiveHitFromEnemy"), Out.ExplosiveHitFromEnemy);
	if (!E.Missing.IsEmpty())
	{
		OutError = FString::Printf(TEXT("config.json %s is missing"), *E.Missing);
		return false;
	}
	return true;
}

bool FMIEnemyTune::Load(FName Difficulty, FMIEnemyTune& Out, FString& OutError)
{
	TSharedPtr<FJsonObject> Root;
	return UMIDataSubsystem::LoadJsonFile(TEXT("config.json"), Root, OutError) && Parse(Root, Difficulty, Out, OutError);
}
