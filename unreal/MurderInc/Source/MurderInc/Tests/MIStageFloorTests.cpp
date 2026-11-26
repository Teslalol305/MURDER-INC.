// The Workbench's turntable and the parts that hang below a gun (docs/unreal/READY.md W4): the stage centred each gun on
// its mesh 14 cm above the turntable plate, so an extended magazine, longer than the factory one, went down into the
// plate and the fitted gun looked like the factory one. The stand now rises just enough for the lowest point of the
// gun and its parts to clear the plate.
//   MurderInc.Frontend.StageFloor   the real set-up screens in a booted world: every gun's Workbench, every option of
//                                   every slot that the art allows fitted in turn, then Factory; after each, the gun and
//                                   every part on it stay above the plate (PlateClearance), the stand is raised only
//                                   when the parts need it, and it settles back once the part is taken off.

#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Flow/MIGameSubsystem.h"
#include "Flow/MIFrontEndRules.h"
#include "Core/Data/MILoadoutData.h"
#include "GameFramework/WorldSettings.h"
#include "Player/MIPlayerCharacter.h"
#include "Tests/MITestUtil.h"
#include "UI/MIFrontEnd.h"
#include "UI/MIShowroom.h"

#if WITH_AUTOMATION_TESTS

namespace MIStageFloorPrivate
{
	constexpr float Dt = 1.f / 30.f;

	/** The title screen of a booted block (as MISwitchPlayTests' FWorld), the set-up screens shown. */
	struct FWorld
	{
		UWorld* World = nullptr;
		UMIGameSubsystem* Game = nullptr;

		FWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("MIStageFloorWorld"));
			FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
			Context.SetCurrentWorld(World);
			World->InitializeActorsForPlay(FURL());
			World->BeginPlay();
			if (!World->GetBegunPlay())
			{
				World->GetWorldSettings()->NotifyBeginPlay();
			}
			World->SpawnActor<AMIPlayerCharacter>(FVector(0, 0, 200), FRotator::ZeroRotator);
			Game = UMIGameSubsystem::Get(World);
		}
		~FWorld()
		{
			World->EndPlay(EEndPlayReason::Quit);
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
		void Step(int32 N = 1)
		{
			for (int32 I = 0; I < N; ++I)
			{
				World->Tick(LEVELTICK_All, Dt);
				GFrameCounter++;
			}
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIStageFloorTest, "MurderInc.Frontend.StageFloor", MITest::Flags)

bool FMIStageFloorTest::RunTest(const FString& Parameters)
{
	using namespace MIStageFloorPrivate;
	FWorld W;
	FMIBootOptions O;
	O.bPersist = false;
	O.bDrawGrey = false;
	if (!TestTrue(TEXT("the game boots"), W.Game && W.Game->Boot(O)))
	{
		return false;
	}
	W.Step();
	UMIFrontEnd* F = W.Game->GetFrontEnd();
	if (!TestNotNull(TEXT("the set-up screens"), F) || !TestNotNull(TEXT("the stage"), F->GetShowroom()))
	{
		return false;
	}
	F->Show();
	const AMIShowroom& Stage = *F->GetShowroom();
	const FMIFrontEndRules& R = F->GetRules();
	const FMILoadoutData& Data = R.GetData();
	F->Act(TEXT("gearup"));
	F->Act(TEXT("next"));
	W.Step(10);
	int32 Checked = 0, Raised = 0;
	// A part slides in over 0.25 s and the stand eases after it: a second is ample.
	const auto Settle = [&W]() { W.Step(30); };
	const auto Check = [&](const FString& What)
	{
		const double Gap = Stage.GetPlateGap(), Lift = Stage.GetStandLift();
		AddInfo(FString::Printf(TEXT("%s: %.2f cm above the plate, stand raised %.2f cm"), *What, Gap, Lift));
		TestTrue(FString::Printf(TEXT("%s: the gun and its parts clear the turntable plate (gap %.2f cm)"), *What, Gap), Gap >= AMIShowroom::PlateClearance - 0.05);
		if (Lift > 0.05)
		{
			// Raised only as far as needed: the lowest point then sits at the clearance.
			TestTrue(FString::Printf(TEXT("%s: raised %.2f cm, no more than the clearance needs (gap %.2f cm)"), *What, Lift, Gap), Gap <= AMIShowroom::PlateClearance + 0.1);
			++Raised;
		}
		++Checked;
	};
	for (const FName Gun : Data.Roster)
	{
		const FMIGunEntry* Entry = Data.FindGun(Gun);
		if (!Entry)
		{
			continue;
		}
		F->Act(TEXT("bench"), Gun.ToString());
		Settle();
		if (R.GetScreen() != EMIFrontScreen::Workbench || R.GetBenchGun() != Gun || !Stage.HasGunMesh())
		{
			AddInfo(FString::Printf(TEXT("%s: no Workbench here (the gun's art is not installed): skipped"), *Gun.ToString()));
			F->Act(TEXT("back"));
			W.Step(5);
			continue;
		}
		Check(Gun.ToString() + TEXT(" as built"));
		for (const FMICompatSlot& Slot : Entry->Compat)
		{
			const TArray<FName> Options = R.BenchOptions(Slot.Slot);
			if (Slot.bVariant || Options.Num() == 0)
			{
				continue;
			}
			F->Act(TEXT("benchslot"), Slot.Slot.ToString());
			const FName Was = R.FittedIn(Slot.Slot);
			const double LiftWas = Stage.GetStandLift();
			for (const FName Part : Options)
			{
				F->Act(TEXT("fit"), Part.IsNone() ? TEXT("factory") : Part.ToString());
				Settle();
				Check(FString::Printf(TEXT("%s %s %s"), *Gun.ToString(), *Slot.Slot.ToString(), Part.IsNone() ? TEXT("factory") : *Part.ToString()));
			}
			// Back to what the slot held, so the next slot starts from the build: the stand settles where it was.
			const FString WasName = Was.IsNone() ? TEXT("factory") : Was.ToString();
			F->Act(TEXT("fit"), WasName);
			Settle();
			Check(FString::Printf(TEXT("%s %s back to %s"), *Gun.ToString(), *Slot.Slot.ToString(), *WasName));
			TestEqual(*FString::Printf(TEXT("%s %s back to %s: the stand is where it was"), *Gun.ToString(), *Slot.Slot.ToString(), *WasName), Stage.GetStandLift(), LiftWas, 0.1);
		}
		F->Act(TEXT("back"));
		W.Step(5);
	}
	AddInfo(FString::Printf(TEXT("%d stage states checked, %d with the stand raised"), Checked, Raised));
	if (Checked == 0)
	{
		AddInfo(TEXT("No gun had a Workbench here (no gun art installed): nothing to check."));
	}
	return !HasAnyErrors();
}

#endif
