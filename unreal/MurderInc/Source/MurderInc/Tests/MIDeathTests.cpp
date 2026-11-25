// The death pass (docs/unreal/PLAY.md, death lane): a killed Goon falls to the floor as a ragdoll and never gets in the
// way of the game. In a world with collision (no window, no GPU), booted from level.json like the run tests:
//   MurderInc.Death.Ragdoll   one round kills a Goon: its body becomes a ragdoll on the mannequin physics asset that
//                             answers to nothing but the world's geometry (not the player, rounds, sight lines, the
//                             camera), it comes to rest on the ground (not under it, not standing), is frozen, and a
//                             round fired through where it lies is not stopped by it. The rules' unit is the same as
//                             with the ragdoll switched off (mi.Goon.Ragdoll 0).

#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SphereComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Enemies/MIEnemies.h"
#include "Enemies/MIEnemyActors.h"
#include "Flow/MIGameSubsystem.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/IConsoleManager.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "Player/MIPlayerCharacter.h"
#include "Tests/MITestUtil.h"
#include "Weapons/MICombatSubsystem.h"

#if WITH_AUTOMATION_TESTS

namespace MIDeathTestsPrivate
{
	constexpr float Dt = 1.f / 30.f;

	struct FDeathWorld
	{
		UWorld* World = nullptr;
		AMIPlayerCharacter* Player = nullptr;
		UMIGameSubsystem* Game = nullptr;

		FDeathWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("MIDeathWorld"));
			FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
			Context.SetCurrentWorld(World);
			World->InitializeActorsForPlay(FURL());
			World->BeginPlay();
			if (!World->GetBegunPlay())
			{
				World->GetWorldSettings()->NotifyBeginPlay();
			}
			Player = World->SpawnActor<AMIPlayerCharacter>(FVector(0, 0, 200), FRotator::ZeroRotator);
			Game = UMIGameSubsystem::Get(World);
		}
		~FDeathWorld()
		{
			World->EndPlay(EEndPlayReason::Quit);
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
		bool Boot(FAutomationTestBase& T)
		{
			FMIBootOptions O;
			O.bTitle = false;
			O.Mode = TEXT("mission");
			O.Difficulty = TEXT("boss");
			O.bPersist = false;
			O.bDrawGrey = false;
			return T.TestTrue(TEXT("the game boots from level.json"), Player && Game && Game->Boot(O));
		}
		void Step()
		{
			World->Tick(LEVELTICK_All, Dt);
			GFrameCounter++;
		}
		/** The first living Goon's slot, or INDEX_NONE. */
		int32 LiveGoon() const
		{
			const TArray<FMIEnemy>& Slots = Game->GetEnemies().GetSlots();
			for (int32 I = 0; I < Slots.Num(); ++I)
			{
				if (Slots[I].bAlive && Slots[I].IsGoon() && Cast<AMIGoon>(Game->GetEnemyActor(I)))
				{
					return I;
				}
			}
			return INDEX_NONE;
		}
		/** One player's round into the Goon's body from 6 m in front of it (the weapon's damage path). */
		FMIDamageResult Shoot(AMIGoon* G) const
		{
			const FVector Chest = G->GetBodyHit()->GetComponentLocation();
			const FVector From = Chest + G->GetActorForwardVector() * 600.0;
			FMIDamage D;
			D.Amount = 100000.0;
			D.Kind = EMIDamageKind::Bullet;
			D.Source = EMIDamageSource::Player;
			D.From = From;
			D.Direction = (Chest - From).GetSafeNormal();
			D.Point = Chest - D.Direction * G->GetBodyHit()->GetScaledCapsuleRadius();
			D.Part = TEXT("body");
			D.Weapon = TEXT("chopper");
			return G->ApplyMIDamage(D);
		}
	};

	/** The rules' record of a unit, as far as the death touches it. */
	FString UnitLine(const FMIEnemy& E)
	{
		return FString::Printf(TEXT("alive %d active %d mode %d pos %s yaw %.6f deathDir %s hp %.3f"), E.bAlive ? 1 : 0, E.bActive ? 1 : 0, (int32)E.Mode,
			*E.Pos.ToString(), E.Yaw, *E.DeathDir.ToString(), E.Hp);
	}

	/** Kill the first living Goon, step Seconds; the unit's record each second and the actor. */
	TArray<FString> KillAndWatch(FAutomationTestBase& T, FDeathWorld& W, double Seconds, AMIGoon*& OutGoon, int32& OutSlot)
	{
		TArray<FString> Lines;
		for (int32 I = 0; I < 30; ++I) W.Step();
		OutSlot = W.LiveGoon();
		OutGoon = OutSlot != INDEX_NONE ? Cast<AMIGoon>(W.Game->GetEnemyActor(OutSlot)) : nullptr;
		if (!T.TestNotNull(TEXT("a living Goon to kill"), OutGoon))
		{
			return Lines;
		}
		T.TestTrue(TEXT("one round kills it"), W.Shoot(OutGoon).bKilled);
		const int32 Frames = FMath::RoundToInt32(Seconds / Dt);
		for (int32 F = 1; F <= Frames; ++F)
		{
			W.Step();
			if (F % 30 == 0)
			{
				Lines.Add(UnitLine(W.Game->GetEnemies().GetSlots()[OutSlot]));
				T.AddInfo(FString::Printf(TEXT("%.0f s: pelvis %s, ragdoll %d, settled %d"), F * Dt,
					*OutGoon->GetMesh()->GetBoneLocation(TEXT("pelvis")).ToCompactString(), OutGoon->IsRagdoll() ? 1 : 0, OutGoon->IsBodySettled() ? 1 : 0));
			}
		}
		return Lines;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIDeathRagdollTest, "MurderInc.Death.Ragdoll", MITest::Flags)

bool FMIDeathRagdollTest::RunTest(const FString& Parameters)
{
	using namespace MIDeathTestsPrivate;
	IConsoleVariable* Switch = IConsoleManager::Get().FindConsoleVariable(TEXT("mi.Goon.Ragdoll"));
	if (!TestNotNull(TEXT("mi.Goon.Ragdoll exists"), Switch))
	{
		return false;
	}
	const int32 Was = Switch->GetInt();

	// With the ragdoll switched off: the rules' record of the killed unit, second by second.
	TArray<FString> Off;
	{
		Switch->Set(0, ECVF_SetByCode);
		FDeathWorld W;
		if (!W.Boot(*this))
		{
			Switch->Set(Was, ECVF_SetByCode);
			return false;
		}
		AMIGoon* G = nullptr;
		int32 Slot = INDEX_NONE;
		Off = KillAndWatch(*this, W, 6.0, G, Slot);
		TestFalse(TEXT("switched off, the body is no ragdoll"), G && G->IsRagdoll());
	}

	Switch->Set(1, ECVF_SetByCode);
	FDeathWorld W;
	if (!W.Boot(*this))
	{
		Switch->Set(Was, ECVF_SetByCode);
		return false;
	}
	AMIGoon* G = nullptr;
	int32 Slot = INDEX_NONE;
	const TArray<FString> On = KillAndWatch(*this, W, 6.0, G, Slot);
	Switch->Set(Was, ECVF_SetByCode);
	if (!G)
	{
		return false;
	}
	// The rules never see the ragdoll: the unit's record is the same either way.
	TestEqual(TEXT("the rules' record of the killed unit is the same with and without the ragdoll"), FString::Join(On, TEXT("\n")), FString::Join(Off, TEXT("\n")));

	USkeletalMeshComponent* M = G->GetMesh();
	if (!M->GetPhysicsAsset())
	{
		AddWarning(TEXT("no physics asset in this project (a clean checkout): the death clip plays instead, the ragdoll is not checked"));
		return true;
	}
	AddInfo(FString::Printf(TEXT("actor %s, mesh %s, pelvis %s, bodies %d, simulating %d, settled %d"), *G->GetActorLocation().ToCompactString(),
		*M->GetComponentLocation().ToCompactString(), *M->GetBoneLocation(TEXT("pelvis")).ToCompactString(), M->Bodies.Num(), M->IsSimulatingPhysics() ? 1 : 0, G->IsBodySettled() ? 1 : 0));
	TestTrue(TEXT("the killed Goon fell as a ragdoll"), G->IsRagdoll());
	TestTrue(TEXT("its body came to rest and was frozen within 6 s"), G->IsBodySettled());
	// What the body answers to: the world's geometry only.
	TestEqual(TEXT("bodies ignore the player (Pawn)"), (int32)M->GetCollisionResponseToChannel(ECC_Pawn), (int32)ECR_Ignore);
	TestEqual(TEXT("bodies ignore rounds (Bullet)"), (int32)M->GetCollisionResponseToChannel(MIBulletChannel), (int32)ECR_Ignore);
	TestEqual(TEXT("bodies ignore sight lines (Visibility)"), (int32)M->GetCollisionResponseToChannel(ECC_Visibility), (int32)ECR_Ignore);
	TestEqual(TEXT("bodies ignore the camera"), (int32)M->GetCollisionResponseToChannel(ECC_Camera), (int32)ECR_Ignore);
	TestEqual(TEXT("bodies ignore other bodies"), (int32)M->GetCollisionResponseToChannel(ECC_PhysicsBody), (int32)ECR_Ignore);
	TestEqual(TEXT("bodies rest on world geometry"), (int32)M->GetCollisionResponseToChannel(ECC_WorldStatic), (int32)ECR_Block);
	TestEqual(TEXT("a frozen body has no collision left"), (int32)M->GetCollisionEnabled(), (int32)ECollisionEnabled::NoCollision);
	TestFalse(TEXT("the hit volumes are off"), G->GetBodyHit()->IsCollisionEnabled() || G->GetHeadHit()->IsCollisionEnabled());

	// On the floor: the hips low over the ground under them, never under it; the head no higher than a sitting man's.
	const FVector Pelvis = M->GetBoneLocation(TEXT("pelvis"));
	const FVector Head = M->GetBoneLocation(TEXT("head"));
	FHitResult Floor;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(MIDeathTest), false, G);
	Q.AddIgnoredActor(W.Player);
	const bool bFloor = W.World->LineTraceSingleByChannel(Floor, Pelvis + FVector(0, 0, 60), Pelvis - FVector(0, 0, 400), ECC_Visibility, Q);
	if (TestTrue(TEXT("ground under the body"), bFloor))
	{
		const double Over = Pelvis.Z - Floor.ImpactPoint.Z;
		AddInfo(FString::Printf(TEXT("pelvis %.1f cm over the ground, head %.1f cm"), Over, Head.Z - Floor.ImpactPoint.Z));
		TestTrue(TEXT("the hips are not under the ground"), Over > -2.0);
		TestTrue(TEXT("the hips are on the ground (under 45 cm: lying, not crouched or standing)"), Over < 45.0);
		TestTrue(TEXT("the head is down (under 70 cm)"), Head.Z - Floor.ImpactPoint.Z < 70.0);
	}
	// A round through where the body lies is not stopped by it.
	FHitResult Through;
	FCollisionQueryParams R(SCENE_QUERY_STAT(MIDeathTestRound), false, W.Player);
	const FVector A = Pelvis + FVector(-300, 0, 15), B = Pelvis + FVector(300, 0, 15);
	const bool bHit = W.World->LineTraceSingleByChannel(Through, A, B, MIBulletChannel, R);
	TestFalse(TEXT("a round through the body does not hit it"), bHit && Through.GetActor() == G);
	return true;
}

#endif
