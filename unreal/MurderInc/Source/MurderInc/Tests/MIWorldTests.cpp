// The slice in a world: the viewmodel rig against its own data (the sights come onto the view axis, a round kicks
// the gun and it settles), and the weapon host, the target dummy, the explosive and the blast in a real world with
// collision (no window, no GPU).

#include "Core/Data/MIDataSubsystem.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/WorldSettings.h"
#include "Misc/AutomationTest.h"
#include "Weapons/MICombatSubsystem.h"
#include "Weapons/MIViewmodel.h"
#include "Weapons/MIWeaponComponent.h"
#include "World/MIExplosive.h"
#include "World/MITargetDummy.h"

#if WITH_AUTOMATION_TESTS

namespace MIWorldTestsPrivate
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;

	/** A bare game world with collision, begun play; destroyed by the destructor. */
	struct FTestWorld
	{
		UWorld* World = nullptr;

		FTestWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("MITestWorld"));
			FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
			Context.SetCurrentWorld(World);
			World->InitializeActorsForPlay(FURL());
			World->BeginPlay();
			// No game mode in a bare world: begin play the way the world settings do it for a loaded level.
			if (!World->GetBegunPlay())
			{
				World->GetWorldSettings()->NotifyBeginPlay();
			}
		}
		~FTestWorld()
		{
			World->EndPlay(EEndPlayReason::Quit);
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
		void Step(int32 Frames = 1, float Dt = 1.f / 60.f)
		{
			for (int32 I = 0; I < Frames; ++I)
			{
				World->Tick(LEVELTICK_All, Dt);
			}
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIViewmodelRigTest, "MurderInc.Weapons.ViewmodelRig", MIWorldTestsPrivate::Flags)

bool FMIViewmodelRigTest::RunTest(const FString& Parameters)
{
	FMIViewmodelData Data;
	FString Error;
	if (!TestTrue(TEXT("presentation.json and config.json load: ") + Error, FMIViewmodelData::Load(Data, Error)))
	{
		return false;
	}
	TestEqual(TEXT("two guns"), Data.Guns.Num(), 2);
	for (const FMIGunViewData& Gun : Data.Guns)
	{
		FMIViewmodelRig Rig;
		Rig.Init(&Data);
		Rig.Equip(Gun.Id);
		FMIWeaponView View;
		View.Weapon = Gun.Id;
		FMIViewmodelPlayer Player;
		const double Dt = 1.0 / 60.0;

		// Hip: the gun sits at the configured view 1 (no motion, the breath aside).
		for (int32 I = 0; I < 30; ++I) Rig.Update(Dt, View, 0.0, false, Player);
		const FVector Hip = Rig.GetWebPose().Pos;
		TestTrue(Gun.Id.ToString() + TEXT(" at the hip pose (within 3 mm)"), FVector::Dist(Hip, Gun.Hip[0].Pos) < 0.003);

		// Aim: the rear sight comes onto the view axis, its relief in front of the eye.
		for (int32 I = 0; I < 120; ++I)
		{
			View.Ads = FMath::Min(1.0, (I + 1) / 20.0);
			Rig.Update(Dt, View, View.Ads, false, Player);
		}
		const FVector Sight = Rig.GunPointInCamera(Gun.Marker(TEXT("sightRear")));
		AddInfo(FString::Printf(TEXT("%s aimed: rear sight at %s cm in camera space"), *Gun.Id.ToString(), *Sight.ToString()));
		TestTrue(Gun.Id.ToString() + TEXT(" rear sight on the axis (within 0.1 cm)"), FMath::Abs(Sight.Y) < 0.1 && FMath::Abs(Sight.Z) < 0.1);
		TestTrue(Gun.Id.ToString() + TEXT(" eye relief"), FMath::IsNearlyEqual(Sight.X, Gun.Relief * 100.0, 0.2));

		// A round kicks the gun back about the pivot; the springs bring it home.
		const FTransform Before = Rig.GetGunTransform();
		Rig.OnFire(1, false, 1.0, false);
		double Peak = 0.0;
		for (int32 I = 0; I < 12; ++I)
		{
			Rig.Update(Dt, View, 1.0, false, Player);
			Peak = FMath::Max(Peak, FVector::Dist(Rig.GetGunTransform().GetLocation(), Before.GetLocation()));
		}
		TestTrue(Gun.Id.ToString() + TEXT(" kicks visibly (over 2 mm)"), Peak > 0.2);
		for (int32 I = 0; I < 90; ++I) Rig.Update(Dt, View, 1.0, false, Player);
		TestTrue(Gun.Id.ToString() + TEXT(" settles (within 0.3 mm)"), FVector::Dist(Rig.GetGunTransform().GetLocation(), Before.GetLocation()) < 0.03);
		TestTrue(Gun.Id.ToString() + TEXT(" bolt or slide went back"), Rig.GetParts().Bolt == 0.0 || Rig.GetParts().bSlideLocked == false);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIHitscanDummyTest, "MurderInc.Weapons.HitscanDummyBlast", MIWorldTestsPrivate::Flags)

bool FMIHitscanDummyTest::RunTest(const FString& Parameters)
{
	MIWorldTestsPrivate::FTestWorld W;
	UWorld* World = W.World;
	FMIConfigData Config;
	FString Error;
	if (!TestTrue(TEXT("config loads"), UMIDataSubsystem::LoadConfig(Config, Error)))
	{
		return false;
	}
	AActor* Shooter = World->SpawnActor<AActor>(FVector::ZeroVector, FRotator::ZeroRotator);
	UMIWeaponComponent* Gun = NewObject<UMIWeaponComponent>(Shooter);
	Gun->RegisterComponent();
	AMITargetDummy* Dummy = World->SpawnActor<AMITargetDummy>(FVector(1000, 0, 0), FRotator::ZeroRotator);
	if (!TestNotNull(TEXT("dummy"), Dummy))
	{
		return false;
	}
	W.Step(2);
	TestEqual(TEXT("dummy hit points = a Goon's"), Dummy->GetHealth(), 90.0);

	const FMIWeaponDef& Chopper = Config.Weapons.Guns[0];
	FMIShotRequest Shot;
	Shot.Origin = FVector(0, 0, 120);
	Shot.Direction = FVector(1, 0, 0);
	Shot.Range = Chopper.Range;
	Shot.Damage = Chopper.Damage;
	Shot.HeadMultiplier = Config.Weapons.Common.HeadMultiplier;
	Shot.Weapon = Chopper.Id;
	FMIShotResult Body = Gun->Hitscan(Shot);
	TestTrue(TEXT("body shot hits"), Body.bHit);
	TestEqual(TEXT("body shot: full damage"), Dummy->GetTotalDamage(), Chopper.Damage);

	Shot.Origin = FVector(0, 0, 162);  // the head sphere's centre height (enemies.goon.head.height)
	FMIShotResult Head = Gun->Hitscan(Shot);
	TestTrue(TEXT("head shot hits"), Head.bHit);
	TestEqual(TEXT("head hits counted"), Dummy->GetHeadHits(), 1);
	TestTrue(TEXT("head shot: x head multiplier"), FMath::IsNearlyEqual(Dummy->GetTotalDamage(), Chopper.Damage * (1.0 + Shot.HeadMultiplier), 1e-6));

	Shot.Origin = FVector(0, 300, 120);  // beside the dummy: nothing there
	TestFalse(TEXT("a miss"), Gun->Hitscan(Shot).bHit);

	// A propane tank 300 cm from the dummy, lit by player rounds, blows when the fuse runs out.
	AMIExplosive* Tank = World->SpawnActor<AMIExplosive>(FVector(1000, 300, 0), FRotator::ZeroRotator);
	W.Step(1);
	const FMIExplosiveKindData* Propane = Config.Explosives.FindKind(TEXT("propane"));
	if (!TestNotNull(TEXT("propane kind"), Propane) || !TestNotNull(TEXT("tank"), Tank))
	{
		return false;
	}
	const double Before = Dummy->GetTotalDamage();
	Shot.Origin = FVector(1000, 100, Propane->Box.Z * 0.5);  // clear of the dummy's capsule
	Shot.Direction = FVector(0, 1, 0);
	{
		const UBoxComponent* TankBox = Tank->GetBox();
		AddInfo(FString::Printf(TEXT("tank %d at %s, extent %s, collision %d, bullet response %d, body %d"), Tank->GetIndex(), *Tank->GetActorLocation().ToString(),
			*TankBox->GetScaledBoxExtent().ToString(), (int32)TankBox->GetCollisionEnabled(), (int32)TankBox->GetCollisionResponseToChannel(MIBulletChannel), TankBox->GetBodyInstance() && TankBox->GetBodyInstance()->IsValidBodyInstance()));
	}
	TestTrue(TEXT("round reaches the tank"), Gun->Hitscan(Shot).bHit);
	TestEqual(TEXT("tank lit"), (int32)Tank->GetState(), (int32)EMIExplosiveState::Lit);
	W.Step(FMath::CeilToInt(Propane->Fuse * 60.0) + 2);
	TestEqual(TEXT("tank gone"), (int32)Tank->GetState(), (int32)EMIExplosiveState::Gone);
	const double Dealt = Dummy->GetTotalDamage() - Before;
	const double Distance = FVector::Dist(Dummy->GetMIBlastTarget(), FVector(1000, 300, Propane->Box.Z * 0.5));
	const double Expected = Propane->Damage * MIBlast::Falloff(Distance, Propane->Radius);
	AddInfo(FString::Printf(TEXT("blast: %.2f damage at %.1f cm (expected %.2f)"), Dealt, Distance, Expected));
	TestTrue(TEXT("blast damage with linear falloff"), FMath::IsNearlyEqual(Dealt, Expected, 1e-6));
	return true;
}

#endif // WITH_AUTOMATION_TESTS
