// Weapon switching in play, from the key to the gun in the hands (docs/unreal/PLAY.md, the switch lane): a run in a
// world with the real player character, AMIPlayerController and its Enhanced Input mapping context; every key goes in
// through APlayerController::InputKey as the game viewport sends it (the mouse wheel as FSceneViewport::OnMouseWheel
// sends it: a press and its release in the same frame), and after each one the test reads the gun the rules hold AND
// the gun the weapon component shows. For one, two, three and four carried guns (the six guns between them):
//   MurderInc.Player.SwitchEveryWay   keys 1-4 and the number pad, the wheel, the D-pad, Q / Y; and, with four guns,
//                                     a switch while reloading, aimed, firing, sprinting, right after the rifle butt,
//                                     a press while paused (ignored) and after the resume, after a death and Run it back.
//   MurderInc.FirstPerson.SwitchSurvivesGC   switching between the pack gun (the STICK) and the hand-IK guns with the
//                                     garbage collector run after every switch: every clip an anim instance of the player
//                                     may still evaluate survives it (version 4 crashed here: SIGSEGV in the hidden pack
//                                     gun's animation about a minute into play, the first collection after a switch).

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
#include "Components/SkeletalMeshComponent.h"
#include "UObject/UObjectGlobals.h"

#if WITH_AUTOMATION_TESTS

namespace MISwitchPlayPrivate
{
	constexpr float Dt = 1.f / 30.f;

	/** The run's world (as MIRunTests' FRunWorld): the block booted from level.json with the real player character. */
	struct FWorld
	{
		UWorld* World = nullptr;
		AMIPlayerCharacter* Player = nullptr;
		UMIGameSubsystem* Game = nullptr;

		FWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("MISwitchWorld"));
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

		/** The title, then Hit the block with Guns carried (every pack mesh counted as present). */
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

	/** A real local player and AMIPlayerController on the run's player (as MIRunTests' FControllerRig). */
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
		/** A press held for Frames frames, then its release and one more frame. */
		void Tap(const FKey& K, int32 Frames = 2) const
		{
			Key(K, IE_Pressed);
			for (int32 I = 0; I < Frames; ++I) W.Step();
			Key(K, IE_Released);
			W.Step();
		}
		/** One notch of the mouse wheel as FSceneViewport::OnMouseWheel sends it: press and release in one frame. */
		void Notch(const FKey& K) const
		{
			Key(K, IE_Pressed);
			Key(K, IE_Released);
			W.Step();
		}
	};

	const UMIWeaponComponent& Weapon(const FWorld& W) { return *W.Player->GetWeapon(); }

	/** Frames until the gun is up and nothing is under way (a holster and draw of the slowest gun is under a second). */
	void Settle(FWorld& W)
	{
		for (int32 I = 0; I < 90 && Weapon(W).GetRules().GetActivity() != EMIWeaponActivity::Ready; ++I) W.Step();
		W.Step();
	}

	/** The rules hold slot Want and the hands show that gun. */
	void Expect(FAutomationTestBase& T, const FWorld& W, int32 Want, const FString& What)
	{
		const FMIWeaponRules& R = Weapon(W).GetRules();
		T.TestEqual(FString::Printf(TEXT("%s: slot %d in hand"), *What, Want + 1), R.GetCurrentIndex(), Want);
		T.TestEqual(FString::Printf(TEXT("%s: the hands show the gun the rules hold"), *What), Weapon(W).GetShownGun(), R.GetCurrentId());
		T.TestEqual(FString::Printf(TEXT("%s: ready"), *What), (int32)R.GetActivity(), (int32)EMIWeaponActivity::Ready);
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMISwitchEveryWayTest, "MurderInc.Player.SwitchEveryWay", MITest::Flags)

bool FMISwitchEveryWayTest::RunTest(const FString& Parameters)
{
	using namespace MISwitchPlayPrivate;
	const TArray<TArray<FName>> Sets = {
		{TEXT("stretch")},
		{TEXT("chopper"), TEXT("nine")},
		{TEXT("shorty"), TEXT("rattler"), TEXT("nine")},
		{TEXT("stick"), TEXT("chopper"), TEXT("rattler"), TEXT("stretch")},
	};
	const FKey Digits[] = {EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four};
	const FKey Pads[] = {EKeys::NumPadOne, EKeys::NumPadTwo, EKeys::NumPadThree, EKeys::NumPadFour};
	for (const TArray<FName>& Guns : Sets)
	{
		const int32 N = Guns.Num();
		const FString Tag = FString::Printf(TEXT("%d gun%s"), N, N == 1 ? TEXT("") : TEXT("s"));
		FWorld W;
		if (!W.Start(*this, Guns))
		{
			return false;
		}
		FPad P(W);
		if (!TestNotNull(TEXT("controller"), P.PC))
		{
			return false;
		}
		W.Player->GetPlayerRules().bInvulnerable = true;  // the Goons may shoot: nobody dies in an input test
		const FMIWeaponRules& R = Weapon(W).GetRules();
		if (!TestEqual(*FString::Printf(TEXT("%s: carried"), *Tag), R.NumGuns(), N))
		{
			continue;
		}
		Settle(W);
		Expect(*this, W, 0, Tag + TEXT(", the run starts"));
		for (int32 I = 0; I < N; ++I)
		{
			TestEqual(*FString::Printf(TEXT("%s: slot %d is the set-up's"), *Tag, I + 1), R.GetData().Guns[I].Id, Guns[I]);
		}

		// The number keys and the number pad: a slot that is carried is drawn; a slot past the last does nothing.
		int32 Have = 0;
		for (int32 K = 3; K >= 0; --K)
		{
			P.Tap(Digits[K]);
			Settle(W);
			Have = K < N ? K : Have;
			Expect(*this, W, Have, FString::Printf(TEXT("%s, key %d"), *Tag, K + 1));
		}
		for (int32 K = 0; K < 4; ++K)
		{
			P.Tap(Pads[K]);
			Settle(W);
			Have = K < N ? K : Have;
			Expect(*this, W, Have, FString::Printf(TEXT("%s, number pad %d"), *Tag, K + 1));
		}
		P.Tap(EKeys::One);
		Settle(W);
		Have = 0;

		// The mouse wheel: down is the next gun, up the previous one, round the ends.
		P.Notch(EKeys::MouseScrollDown);
		Settle(W);
		Have = N > 1 ? 1 : 0;
		Expect(*this, W, Have, Tag + TEXT(", wheel down"));
		P.Notch(EKeys::MouseScrollUp);
		Settle(W);
		Have = 0;
		Expect(*this, W, Have, Tag + TEXT(", wheel up"));
		P.Notch(EKeys::MouseScrollUp);
		Settle(W);
		Have = N - 1;
		Expect(*this, W, Have, Tag + TEXT(", wheel up from slot 1 goes round"));
		P.Notch(EKeys::MouseScrollDown);
		Settle(W);
		Have = 0;
		Expect(*this, W, Have, Tag + TEXT(", wheel down from the last goes round"));

		// The pad: D-pad left and right are slots 1 and 2, up and down next and previous, Y (a tap) the last gun.
		P.Tap(EKeys::Gamepad_DPad_Right);
		Settle(W);
		Have = N > 1 ? 1 : 0;
		Expect(*this, W, Have, Tag + TEXT(", D-pad right"));
		P.Tap(EKeys::Gamepad_DPad_Left);
		Settle(W);
		Have = 0;
		Expect(*this, W, Have, Tag + TEXT(", D-pad left"));
		P.Tap(EKeys::Gamepad_DPad_Up);
		Settle(W);
		Have = N > 1 ? 1 : 0;
		Expect(*this, W, Have, Tag + TEXT(", D-pad up"));
		P.Tap(EKeys::Gamepad_DPad_Down);
		Settle(W);
		Have = 0;
		Expect(*this, W, Have, Tag + TEXT(", D-pad down"));
		// Quick switch: Q and Y go back to the gun used last (slot 2 here, after the D-pad).
		P.Tap(EKeys::Q);
		Settle(W);
		Have = N > 1 ? 1 : 0;
		Expect(*this, W, Have, Tag + TEXT(", Q"));
		P.Tap(EKeys::Gamepad_FaceButton_Top);
		Settle(W);
		Have = 0;
		Expect(*this, W, Have, Tag + TEXT(", Y"));
		P.Tap(EKeys::Q, 1);
		P.Tap(EKeys::Q, 1);
		Settle(W);
		Expect(*this, W, 0, Tag + TEXT(", Q twice at once lands on the gun it started on"));
		if (N < 4)
		{
			continue;
		}

		// Four guns: a switch from every state a player can be in.
		{
			P.Key(EKeys::LeftMouseButton, IE_Pressed);
			for (int32 I = 0; I < 8; ++I) W.Step();
			P.Key(EKeys::LeftMouseButton, IE_Released);
			W.Step();
			TestTrue(TEXT("rounds spent"), R.GetMag() < R.GetDef().MagSize);
			P.Tap(EKeys::R);
			TestEqual(TEXT("reloading"), (int32)R.GetActivity(), (int32)EMIWeaponActivity::Reloading);
			P.Tap(EKeys::Two);
			Settle(W);
			Expect(*this, W, 1, TEXT("key 2 while reloading"));
		}
		{
			P.Key(EKeys::RightMouseButton, IE_Pressed);
			for (int32 I = 0; I < 20; ++I) W.Step();
			TestTrue(TEXT("aimed"), R.GetAds() > 0.5);
			P.Tap(EKeys::Three);
			Settle(W);
			Expect(*this, W, 2, TEXT("key 3 while aimed"));
			for (int32 I = 0; I < 20; ++I) W.Step();
			TestTrue(TEXT("the new gun comes up aimed while the button is held"), R.GetAds() > 0.5);
			P.Key(EKeys::RightMouseButton, IE_Released);
			W.Step();
		}
		{
			P.Key(EKeys::LeftMouseButton, IE_Pressed);
			for (int32 I = 0; I < 3; ++I) W.Step();
			P.Tap(EKeys::Four);
			TestTrue(TEXT("key 4 while firing: the holster starts at once"), R.GetActivity() == EMIWeaponActivity::Holstering || R.GetActivity() == EMIWeaponActivity::Drawing);
			P.Key(EKeys::LeftMouseButton, IE_Released);
			Settle(W);
			Expect(*this, W, 3, TEXT("key 4 while firing"));
		}
		{
			P.Key(EKeys::LeftShift, IE_Pressed);
			P.Key(EKeys::W, IE_Pressed);
			for (int32 I = 0; I < 20; ++I) W.Step();
			TestTrue(TEXT("sprinting"), W.Player->GetPlayerRules().bSprinting);
			P.Tap(EKeys::One);
			Settle(W);
			Expect(*this, W, 0, TEXT("key 1 while sprinting"));
			P.Key(EKeys::W, IE_Released);
			P.Key(EKeys::LeftShift, IE_Released);
			for (int32 I = 0; I < 10; ++I) W.Step();
		}
		{
			P.Tap(EKeys::F, 1);
			TestEqual(TEXT("the rifle butt"), (int32)R.GetActivity(), (int32)EMIWeaponActivity::Striking);
			P.Tap(EKeys::Two, 1);
			for (int32 I = 0; I < 60 && R.GetActivity() == EMIWeaponActivity::Striking; ++I) W.Step();
			Settle(W);
			Expect(*this, W, 1, TEXT("key 2 during the rifle butt (goes through when the strike is over)"));
		}
		{
			// The P key pauses and resumes, as a player does it. (A world made by a test has no game mode, so the engine's
			// own pause does not stop the input here as it does in the game: the presses below do reach the controller,
			// and the resume must still drop them.)
			P.Tap(EKeys::P);
			TestEqual(TEXT("paused"), (int32)W.State(), (int32)EMIGameState::Paused);
			P.Tap(EKeys::Three);
			P.Notch(EKeys::MouseScrollDown);
			TestEqual(TEXT("a press on the pause card changes no gun"), R.GetCurrentIndex(), 1);
			for (int32 I = 0; I < 40 && W.State() == EMIGameState::Paused; ++I)
			{
				P.Tap(EKeys::P);  // again, once the pause's debounce allows
				for (int32 J = 0; J < 4; ++J) W.Step();
			}
			TestEqual(TEXT("resumed"), (int32)W.State(), (int32)EMIGameState::Playing);
			Settle(W);
			Expect(*this, W, 1, TEXT("presses made while paused do nothing after the resume"));
			P.Tap(EKeys::Three);
			Settle(W);
			Expect(*this, W, 2, TEXT("key 3 after the resume"));
		}
		{
			W.Player->GetPlayerRules().bInvulnerable = false;
			W.Game->DamagePlayer(1000.0, W.Player->GetActorLocation() + FVector(100, 0, 0), TEXT("bullet"));
			FMIMenu& M = W.Game->GetMenu();
			for (int32 I = 0; I < 30 * 4 && M.Screen != EMIMenuScreen::Dead; ++I) W.Step();
			if (TestEqual(TEXT("the death card"), (int32)M.Screen, (int32)EMIMenuScreen::Dead))
			{
				P.Tap(EKeys::Four);  // on the card: no gun changes
				M.Selected = M.IndexOf(TEXT("retry"));
				W.Game->MenuConfirm();
				for (int32 I = 0; I < 30 * 5 && W.State() != EMIGameState::Playing; ++I) W.Step();
				TestEqual(TEXT("Run it back: playing"), (int32)W.State(), (int32)EMIGameState::Playing);
				W.Player->GetPlayerRules().bInvulnerable = true;
				Settle(W);
				Expect(*this, W, 0, TEXT("Run it back starts on slot 1"));
				P.Tap(EKeys::Four);
				Settle(W);
				Expect(*this, W, 3, TEXT("key 4 after Run it back"));
				P.Notch(EKeys::MouseScrollDown);
				Settle(W);
				Expect(*this, W, 0, TEXT("wheel down after Run it back"));
			}
		}
	}
	return !HasAnyErrors();
}

namespace MISwitchPlayPrivate
{
	/** Every clip that a first-person anim instance on the player holds in its pose, as weak pointers. */
	TArray<TWeakObjectPtr<UAnimSequenceBase>> PoseClips(const FWorld& W, int32& Instances)
	{
		TArray<TWeakObjectPtr<UAnimSequenceBase>> Out;
		TArray<USkeletalMeshComponent*> Meshes;
		W.Player->GetComponents<USkeletalMeshComponent>(Meshes);
		Instances = 0;
		for (const USkeletalMeshComponent* M : Meshes)
		{
			if (const UMIFPAnimInstance* A = Cast<UMIFPAnimInstance>(M->GetAnimInstance()))
			{
				++Instances;
				for (const FMIFPLayer& L : A->GetPending().Layers)
				{
					if (L.Clip) Out.AddUnique(const_cast<UAnimSequenceBase*>(L.Clip));
				}
			}
		}
		return Out;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMISwitchSurvivesGCTest, "MurderInc.FirstPerson.SwitchSurvivesGC", MITest::Flags)

bool FMISwitchSurvivesGCTest::RunTest(const FString& Parameters)
{
	using namespace MISwitchPlayPrivate;
	FWorld W;
	if (!W.Start(*this, {TEXT("stick"), TEXT("rattler"), TEXT("nine"), TEXT("chopper")}))
	{
		return false;
	}
	FPad P(W);
	if (!TestNotNull(TEXT("controller"), P.PC))
	{
		return false;
	}
	W.Player->GetPlayerRules().bInvulnerable = true;
	const UMIFirstPersonRig* Rig = Weapon(W).GetFirstPersonRig();
	Settle(W);
	if (!Rig || Rig->GetMode() != EMIFPMode::Pack)
	{
		AddInfo(TEXT("The STICK is not drawn in pack mode here (the pack's art is not installed): nothing to check."));
		return true;
	}
	const FKey Digits[] = {EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four};
	// Pack -> hand IK -> pack -> the pistol -> the CHOPPER -> pack -> hand IK, a collection after each.
	for (const int32 Slot : {1, 0, 2, 3, 0, 1, 0})
	{
		P.Tap(Digits[Slot]);
		Settle(W);
		const FString What = FString::Printf(TEXT("slot %d (%s, mode %d)"), Slot + 1, *Weapon(W).GetRules().GetCurrentId().ToString(), (int32)Rig->GetMode());
		Expect(*this, W, Slot, What);
		int32 Instances = 0;
		const TArray<TWeakObjectPtr<UAnimSequenceBase>> Before = PoseClips(W, Instances);
		// The editor keeps every asset it loaded (RF_Standalone); a packaged game does not, and there an asset nothing
		// references is freed by the next collection. The clips are made collectable as in the game, for this collection.
		for (const TWeakObjectPtr<UAnimSequenceBase>& C : Before)
		{
			if (C.IsValid()) C->ClearFlags(RF_Standalone);
		}
		CollectGarbage(GARBAGE_COLLECTION_KEEPFLAGS, true);
		int32 Lost = 0;
		for (const TWeakObjectPtr<UAnimSequenceBase>& C : Before)
		{
			if (C.IsValid()) C->SetFlags(RF_Standalone);
			else ++Lost;
		}
		if (!TestEqual(*FString::Printf(TEXT("%s: every clip of the %d first-person pose(s) survives a collection"), *What, Instances), Lost, 0))
		{
			return false;  // the next evaluation would read a freed clip (version 4's crash): stop here
		}
		for (int32 I = 0; I < 10; ++I) W.Step();  // the poses are evaluated again after the collection
	}
	// The cost of holding the clips: SetPose on the arms' instance with its own pose (the rig calls it once a frame on the
	// arms and once on the pack gun), timed.
	TArray<USkeletalMeshComponent*> Meshes;
	W.Player->GetComponents<USkeletalMeshComponent>(Meshes);
	for (USkeletalMeshComponent* M : Meshes)
	{
		if (UMIFPAnimInstance* A = Cast<UMIFPAnimInstance>(M->GetAnimInstance()))
		{
			const FMIFPPose Pose = A->GetPending();
			constexpr int32 N = 20000;
			const double T0 = FPlatformTime::Seconds();
			for (int32 I = 0; I < N; ++I) A->SetPose(Pose);
			const double Us = (FPlatformTime::Seconds() - T0) / N * 1e6;
			AddInfo(FString::Printf(TEXT("SetPose on %s (%d clips): %.3f us a call"), *M->GetName(), Pose.Layers.Num(), Us));
			break;
		}
	}
	return !HasAnyErrors();
}

#endif
