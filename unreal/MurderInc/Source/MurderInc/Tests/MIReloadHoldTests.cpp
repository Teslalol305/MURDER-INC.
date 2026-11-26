// The support hand in a reload, in a played world (HANDS_R4.md 8.1 and 10): the real player with the four hand-IK rifles,
// each fired and reloaded through the keys, and the first-person rig read while it pulls the hands:
//   MurderInc.FirstPerson.ReloadHold   the support hand gets onto the magazine (the rig's hold reaches 1 mid-reload), its
//                                      palm target is the magazine's palm point, the grip laid on it is the one solved round
//                                      that magazine (every joint), the elbow push is let go there and back after, the
//                                      magazine stays drawn in the hand (magazine.inHand), and the hold never moves faster
//                                      than magazine.blend allows (no jump in one frame).
// The test reads only presentation: no gameplay number is set or checked here.

#include "Engine/Engine.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "EnhancedInputSubsystems.h"
#include "Flow/MIGameSubsystem.h"
#include "GameFramework/WorldSettings.h"
#include "InputCoreTypes.h"
#include "InputKeyEventArgs.h"
#include "Player/MIPlayerCharacter.h"
#include "Player/MIPlayerController.h"
#include "Tests/MITestUtil.h"
#include "UI/MIFrontEnd.h"
#include "Weapons/MIWeaponComponent.h"
#include "Weapons/MIFirstPersonAnim.h"
#include "Weapons/MIFirstPersonRig.h"

#if WITH_AUTOMATION_TESTS

namespace MIReloadHoldPrivate
{
	constexpr float Dt = 1.f / 30.f;

	/** The run's world (as MISwitchPlayTests' FWorld): the block booted from level.json with the real player character. */
	struct FWorld
	{
		UWorld* World = nullptr;
		AMIPlayerCharacter* Player = nullptr;
		UMIGameSubsystem* Game = nullptr;

		FWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("MIReloadHoldWorld"));
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
		~FWorld()
		{
			World->EndPlay(EEndPlayReason::Quit);
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
		void Step()
		{
			World->Tick(LEVELTICK_All, Dt);
			GFrameCounter++;  // tick functions run once per engine frame
		}
		EMIGameState State() const { return Game->GetRules().GetState(); }

		bool Start(FAutomationTestBase& T, const TArray<FName>& Guns)
		{
			FMIBootOptions O;
			O.bPersist = false;
			O.bDrawGrey = false;
			if (!T.TestTrue(TEXT("the game boots"), Player && Game && Game->Boot(O)))
			{
				return false;
			}
			Step();
			UMIFrontEnd* F = Game->GetFrontEnd();
			if (!T.TestNotNull(TEXT("the set-up screens"), F))
			{
				return false;
			}
			F->GetRules().EditReadinessForTest().AssetExists = [](const FString&) { return true; };
			FMIRunSetup& S = F->GetRules().EditSetup();
			S.Guns = Guns;
			S.bPlayed = true;
			F->Act(TEXT("hit"));
			for (int32 I = 0; I < 30 * 4 && State() != EMIGameState::Playing; ++I) Step();
			for (int32 I = 0; I < 60; ++I) Step();
			return T.TestEqual(TEXT("playing"), (int32)State(), (int32)EMIGameState::Playing);
		}
	};

	/** A real local player and AMIPlayerController on the run's player. */
	struct FPad
	{
		FWorld& W;
		ULocalPlayer* LP = nullptr;
		AMIPlayerController* PC = nullptr;

		explicit FPad(FWorld& InW) : W(InW)
		{
			LP = NewObject<ULocalPlayer>(GEngine);
			LP->PlayerAdded(nullptr, INVALID_CONTROLLERID);
			PC = W.World->SpawnActor<AMIPlayerController>();
			if (PC)
			{
				PC->SetPlayer(LP);
				PC->Possess(W.Player);
				if (UEnhancedInputLocalPlayerSubsystem* Sub = LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
				{
					FModifyContextOptions Now;
					Now.bForceImmediately = true;
					Sub->RequestRebuildControlMappings(Now);
				}
			}
		}
		~FPad()
		{
			if (PC) PC->UnPossess();
			LP->PlayerRemoved();
		}
		void Key(const FKey& K, EInputEvent E) const
		{
			PC->InputKey(FInputKeyEventArgs(nullptr, FInputDeviceId::CreateFromInternalId(0), K, E, E == IE_Released ? 0.f : 1.f, false, FPlatformTime::Cycles64()));
		}
		void Tap(const FKey& K, int32 Frames = 2) const
		{
			Key(K, IE_Pressed);
			for (int32 I = 0; I < Frames; ++I) W.Step();
			Key(K, IE_Released);
			W.Step();
		}
	};

	void Settle(FWorld& W)
	{
		for (int32 I = 0; I < 90 && W.Player->GetWeapon()->GetRules().GetActivity() != EMIWeaponActivity::Ready; ++I) W.Step();
		W.Step();
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIReloadHoldTest, "MurderInc.FirstPerson.ReloadHold", MITest::Flags)

bool FMIReloadHoldTest::RunTest(const FString& Parameters)
{
	using namespace MIReloadHoldPrivate;
	FWorld W;
	if (!W.Start(*this, {TEXT("chopper"), TEXT("shorty"), TEXT("stretch"), TEXT("rattler")}))
	{
		return false;
	}
	FPad P(W);
	if (!TestNotNull(TEXT("controller"), P.PC))
	{
		return false;
	}
	W.Player->GetPlayerRules().bInvulnerable = true;
	const UMIWeaponComponent& Weapon = *W.Player->GetWeapon();
	const UMIFirstPersonRig* Rig = Weapon.GetFirstPersonRig();
	if (!TestNotNull(TEXT("the first-person rig"), Rig))
	{
		return false;
	}
	const FKey Digits[] = {EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four};
	int32 Checked = 0;
	for (int32 Slot = 0; Slot < 4; ++Slot)
	{
		P.Tap(Digits[Slot]);
		Settle(W);
		const FMIWeaponRules& R = Weapon.GetRules();
		const FString Gun = R.GetCurrentId().ToString();
		if (Rig->GetMode() != EMIFPMode::HandIK)
		{
			AddInfo(FString::Printf(TEXT("%s is not drawn with hand IK here (its art is not installed): not checked"), *Gun));
			continue;
		}
		++Checked;
		TestTrue(Gun + TEXT(": a grip is solved round its magazine (grips.json magazines)"), Rig->HasReloadSolve());
		// at the hip, before the reload: the hand on the handguard, the elbow pushed out (supportElbowOut)
		TestEqual(Gun + TEXT(": on the handguard before the reload"), Rig->GetMagazineHold(), 0.0);
		const FMIFPPose& Hip = Rig->GetHandPose();
		TestTrue(Gun + TEXT(": the support elbow is pushed out at the hip"), Hip.Hands.Num() > 0 && !Hip.Hands[0].PoleShift.IsNearlyZero());
		// HANDS_R4.md 13: the firing hand closes round the pistol grip (its palm where the solved grip puts it)
		double FiringGap = -1.0;
		const bool bFiringGap = Rig->FiringPalmGap(FiringGap);
		TestTrue(FString::Printf(TEXT("%s: the firing hand is on the pistol grip at the hip (palm %.1f cm off)"), *Gun, FiringGap),
			bFiringGap && FiringGap < 1.5);
		// a few rounds, then the reload
		P.Key(EKeys::LeftMouseButton, IE_Pressed);
		for (int32 I = 0; I < 6; ++I) W.Step();
		P.Key(EKeys::LeftMouseButton, IE_Released);
		for (int32 I = 0; I < 10; ++I) W.Step();
		if (!TestTrue(Gun + TEXT(": rounds spent"), R.GetMag() < R.GetDef().MagSize))
		{
			continue;
		}
		P.Tap(EKeys::R);
		TestEqual(Gun + TEXT(": reloading"), (int32)R.GetActivity(), (int32)EMIWeaponActivity::Reloading);
		double Most = 0.0, Prev = Rig->GetMagazineHold(), Fastest = 0.0, WorstPalm = 0.0, WorstFiring = 0.0;
		int32 Held = 0, ShapePoints = 0, InHand = 0;
		bool bPoleLetGo = true;
		for (int32 I = 0; I < 30 * 6 && R.GetActivity() == EMIWeaponActivity::Reloading; ++I)
		{
			W.Step();
			const double K = Rig->GetMagazineHold();
			Fastest = FMath::Max(Fastest, FMath::Abs(K - Prev));
			Prev = K;
			Most = FMath::Max(Most, K);
			if (K > 0.999)
			{
				++Held;
				FVector Want, Got;
				if (Rig->MagazinePalmTarget(Want) && Rig->SupportPalmTarget(Got))
				{
					WorstPalm = FMath::Max(WorstPalm, FVector::Dist(Want, Got));
				}
				const FMIFPPose& Pose = Rig->GetHandPose();
				ShapePoints = Pose.Hands.Num() > 0 ? Pose.Hands[0].Shape.Num() : 0;
				bPoleLetGo &= Pose.Hands.Num() > 0 && Pose.Hands[0].PoleShift.IsNearlyZero(0.01);
				InHand += Rig->KeepsMagazineInHand() ? 1 : 0;
				double Gap = 0.0;
				WorstFiring = Rig->FiringPalmGap(Gap) ? FMath::Max(WorstFiring, Gap) : 99.0;
			}
		}
		TestTrue(FString::Printf(TEXT("%s: the firing hand stays on the pistol grip through the reload (worst %.1f cm)"), *Gun, WorstFiring), WorstFiring < 1.5);
		TestTrue(FString::Printf(TEXT("%s: the support hand gets onto the magazine (most %.3f)"), *Gun, Most), Most > 0.999);
		TestTrue(FString::Printf(TEXT("%s: and holds it for a while (%d frames)"), *Gun, Held), Held >= 10);
		TestTrue(FString::Printf(TEXT("%s: its palm goes to the magazine's palm point (worst %.2f cm)"), *Gun, WorstPalm), WorstPalm < 0.5);
		TestTrue(FString::Printf(TEXT("%s: the grip laid on it has every joint (%d points)"), *Gun, ShapePoints), ShapePoints >= 24);
		TestTrue(Gun + TEXT(": the elbow push is let go while the hand is on the magazine"), bPoleLetGo);
		TestEqual(Gun + TEXT(": the magazine stays drawn while the hand holds it (magazine.inHand)"), InHand, Held);
		// the hold is moved at most 1 / magazine.blend (0.25 s) a second, smoothstepped: at most 1.5 x that a frame
		TestTrue(FString::Printf(TEXT("%s: the hold never jumps (largest step %.3f a frame)"), *Gun, Fastest), Fastest <= 1.5 * Dt / 0.25 + 1e-6);
		for (int32 I = 0; I < 30; ++I) W.Step();
		TestEqual(Gun + TEXT(": back on the handguard after the reload"), Rig->GetMagazineHold(), 0.0);
		const FMIFPPose& After = Rig->GetHandPose();
		TestTrue(Gun + TEXT(": the elbow is pushed out again"), After.Hands.Num() > 0 && !After.Hands[0].PoleShift.IsNearlyZero());
	}
	if (Checked == 0)
	{
		AddInfo(TEXT("No gun drawn with hand IK (the art is not installed): nothing checked."));
	}
	return !HasAnyErrors();
}

#endif
