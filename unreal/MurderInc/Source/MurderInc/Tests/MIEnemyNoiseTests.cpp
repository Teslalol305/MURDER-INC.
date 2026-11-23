// MurderInc.Enemies.GunfireRadius: the gunfire throttle with per-gun noise radii (LOADOUT.md 4.5). The web alerts at
// most once per ai.gunfireEvery; a round heard further than the last alert in that window still alerts, a quieter one
// (a silenced gun after a bare one) does not.

#include "Enemies/MIEnemies.h"
#include "Tests/MITestUtil.h"
#include "Core/MIMath.h"
#include "Enemies/MIEnemyTune.h"
#include "World/MIBoxWorld.h"
#include "World/MILevelData.h"

#if WITH_AUTOMATION_TESTS

namespace MIEnemyNoisePrivate
{
	struct FQuietHost : public IMIEnemyHost
	{
		virtual FVector Hitscan(int32, const FVector& Origin, const FVector&, double, double) override { return Origin; }
		virtual void DamagePlayer(double, const FVector&, FName) override {}
		virtual void Explode(int32, const FVector&, double, double, double) override {}
	};

	/** A field on the block with two Goons facing away, 30 m and 15 m from the shot. */
	struct FScene
	{
		FMIBoxWorld World;
		FMIEnemyField Field;
		FQuietHost Host;
		FVector Shot;
		int32 FarId = INDEX_NONE, NearId = INDEX_NONE;

		bool Init(FAutomationTestBase& T, const FMIEnemyTune& Tune, const FMILevelData* Level)
		{
			Level->FillWorld(World, FMIRng(1));
			Field.Init(Tune, Level, &World, &Host);
			Shot = Level->PlayerStart.Pos;
			FMIEnemySpawnOptions Away;
			Away.Yaw = 0.0;
			const FMIEnemy* Far = Field.Spawn(MIEnemy::EType::Goon, Shot + FVector(30.0, 0.0, 0.0), Away);
			const FMIEnemy* Near = Field.Spawn(MIEnemy::EType::Goon, Shot + FVector(0.0, 0.0, 15.0), Away);
			FarId = Far ? Far->Id : INDEX_NONE;
			NearId = Near ? Near->Id : INDEX_NONE;
			return T.TestTrue(TEXT("two Goons"), Far && Near);
		}

		bool Heard(int32 Id) { const FMIEnemy* E = Field.Find(Id); return E && E->Mode == EMIEnemyMode::Investigate; }
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIEnemyGunfireRadiusTest, "MurderInc.Enemies.GunfireRadius", MITest::Flags)

bool FMIEnemyGunfireRadiusTest::RunTest(const FString& Parameters)
{
	using namespace MIEnemyNoisePrivate;
	FMIEnemyTune Tune;
	FString Error;
	const FMILevelData* Level = FMILevelData::Get();
	if (!FMIEnemyTune::Load(TEXT("boss"), Tune, Error) || !Level)
	{
		AddError(Error.IsEmpty() ? FString(TEXT("no level data")) : Error);
		return false;
	}
	const double Bare = Tune.Ai.HearGunfire;
	TestEqual(TEXT("a bare round is heard 45 m out (config.json ai.hearGunfire)"), Bare, 45.0);
	TestTrue(TEXT("the throttle window is open"), Tune.Ai.GunfireEvery > 0.0);
	{
		FScene S;
		if (S.Init(*this, Tune, Level))
		{
			S.Field.Gunfire(S.Shot);
			TestTrue(TEXT("bare: heard at 15 m"), S.Heard(S.NearId));
			TestTrue(TEXT("bare: heard at 30 m"), S.Heard(S.FarId));
		}
	}
	{
		FScene S;
		if (S.Init(*this, Tune, Level))
		{
			S.Field.Gunfire(S.Shot, 18.0);
			TestTrue(TEXT("silenced: heard at 15 m"), S.Heard(S.NearId));
			TestFalse(TEXT("silenced: not heard at 30 m"), S.Heard(S.FarId));
		}
	}
	{
		// Inside the window: a bare round far away (nobody near it), then a silenced one here alerts nobody; a louder one
		// than the last alert does.
		FScene S;
		if (S.Init(*this, Tune, Level))
		{
			S.Field.Gunfire(S.Shot + FVector(500.0, 0.0, 500.0), Bare);
			TestFalse(TEXT("the far round reaches neither"), S.Heard(S.NearId) || S.Heard(S.FarId));
			S.Field.Gunfire(S.Shot, 18.0);
			TestFalse(TEXT("a radius-18 round after a radius-45 alert inside the window: not heard"), S.Heard(S.NearId));
			S.Field.Gunfire(S.Shot, 60.0);
			TestTrue(TEXT("a radius-60 round inside the window: heard at 15 m"), S.Heard(S.NearId));
			TestTrue(TEXT("... and at 30 m"), S.Heard(S.FarId));
		}
	}
	{
		// The other way round: a silenced alert, then a bare round inside the window is louder, so it alerts.
		FScene S;
		if (S.Init(*this, Tune, Level))
		{
			S.Field.Gunfire(S.Shot, 18.0);
			TestFalse(TEXT("silenced first: not heard at 30 m"), S.Heard(S.FarId));
			S.Field.Gunfire(S.Shot);
			TestTrue(TEXT("then a bare round inside the window: heard at 30 m"), S.Heard(S.FarId));
		}
	}
	{
		// Equal radii keep the web's throttle: the second round inside the window is ignored.
		FScene S;
		if (S.Init(*this, Tune, Level))
		{
			S.Field.Gunfire(S.Shot + FVector(500.0, 0.0, 500.0));
			S.Field.Gunfire(S.Shot);
			TestFalse(TEXT("equal radius inside the window: ignored"), S.Heard(S.NearId) || S.Heard(S.FarId));
		}
	}
	return !HasAnyErrors();
}

#endif
