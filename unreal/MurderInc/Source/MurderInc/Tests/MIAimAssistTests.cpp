// The aim assist (docs/unreal/DECISIONS.md 2026-11-27 ~22:20: "lock onto the targets as they shoot"):
//   MurderInc.Assist.Data     the numbers come from config.json player.input.assist (pad 0.45 / mouse 0.8 slow-down, cones 6 / 3 degrees,
//                             snaps 10 / 5 degrees over 0.12 s); the setting is on by default with Normal strength and is saved.
//   MurderInc.Assist.Math     the pure assist: the slow-down, the capped magnetism that gives way to the player's own turn, the ADS snap,
//                             the strengths, and nothing at all when it is off.
//   MurderInc.Assist.World    in a played world with the real controller: it engages on a visible Goon (slow-down, pull, snap), does
//                             nothing through a wall, and does nothing when switched off.

#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Core/MIMath.h"
#include "Engine/Engine.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Enemies/MIEnemies.h"
#include "Enemies/MIEnemyActors.h"
#include "Flow/MIGameSubsystem.h"
#include "Flow/MISettings.h"
#include "GameFramework/WorldSettings.h"
#include "Player/MIAimAssist.h"
#include "Player/MIPlayerCharacter.h"
#include "Player/MIPlayerController.h"
#include "Tests/MITestUtil.h"
#include "Weapons/MICombatSubsystem.h"

#if WITH_AUTOMATION_TESTS

namespace MIAssistTestsPrivate
{
	constexpr double Dt = 1.0 / 30.0;

	bool LoadAssist(FAutomationTestBase& T, FMIAimAssist& Out)
	{
		FMIConfigData Config;
		FString Error;
		if (!T.TestTrue(TEXT("config.json loads"), UMIDataSubsystem::LoadConfig(Config, Error)))
		{
			return false;
		}
		Out.Data = Config.Player.Look.Assist;
		return true;
	}

	FMIAssistFrame Frame(bool bPad, bool bFire, bool bAds, FVector2D Turn = FVector2D::ZeroVector)
	{
		FMIAssistFrame F;
		F.bOn = true;
		F.bPad = bPad;
		F.bFire = bFire;
		F.bAds = bAds;
		F.PlayerTurn = Turn;
		F.Dt = Dt;
		return F;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAssistDataTest, "MurderInc.Assist.Data", MITest::Flags)

bool FMIAssistDataTest::RunTest(const FString& Parameters)
{
	using namespace MIAssistTestsPrivate;
	FMIAimAssist A;
	if (!LoadAssist(*this, A))
	{
		return false;
	}
	TestEqual(TEXT("pad slow-down"), A.Data.Pad.Slow, 0.45);
	TestEqual(TEXT("mouse slow-down"), A.Data.Mouse.Slow, 0.8);
	TestEqual(TEXT("pad cone"), A.Data.Pad.MagCone, 6.0);
	TestEqual(TEXT("mouse cone"), A.Data.Mouse.MagCone, 3.0);
	TestEqual(TEXT("pad snap angle"), A.Data.Pad.SnapAngle, 10.0);
	TestEqual(TEXT("mouse snap angle"), A.Data.Mouse.SnapAngle, 5.0);
	TestEqual(TEXT("pad snap time"), A.Data.Pad.SnapTime, 0.12);
	TestEqual(TEXT("the strengths, in cycling order"), A.Data.Strengths.Num(), 3);
	TestTrue(TEXT("Low is weaker than Normal, High stronger"), A.Data.ScaleOf(TEXT("low")) < A.Data.ScaleOf(TEXT("normal")) && A.Data.ScaleOf(TEXT("high")) > A.Data.ScaleOf(TEXT("normal")));

	FMISettings S;
	FString Error;
	if (!TestTrue(TEXT("settings defaults load"), FMISettings::LoadDefaults(S, Error)))
	{
		return false;
	}
	TestTrue(TEXT("the aim assist is on by default"), S.bAimAssist);
	TestEqual(TEXT("Normal by default"), S.AimAssistStrength, FName(TEXT("normal")));
	TestEqual(TEXT("three strengths to choose from"), S.Rules.AssistStrengths.Num(), 3);
	TestFalse(TEXT("an unknown strength changes nothing"), S.SetAimAssistStrength(TEXT("insane")));
	TestTrue(TEXT("High is accepted"), S.SetAimAssistStrength(TEXT("high")));
	TestTrue(TEXT("Off is accepted"), S.SetAimAssist(false));

	UMISaveGame* Save = NewObject<UMISaveGame>();
	S.ToSave(*Save);
	FMISettings Back;
	FMISettings::LoadDefaults(Back, Error);
	Back.FromSave(*Save);
	TestFalse(TEXT("the choice is stored: off"), Back.bAimAssist);
	TestEqual(TEXT("the choice is stored: strength"), Back.AimAssistStrength, FName(TEXT("high")));
	// A save from before the assist: the default (on, Normal).
	UMISaveGame* Old = NewObject<UMISaveGame>();
	FMISettings Legacy;
	FMISettings::LoadDefaults(Legacy, Error);
	Legacy.FromSave(*Old);
	TestTrue(TEXT("an older save gets the assist on"), Legacy.bAimAssist);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAssistMathTest, "MurderInc.Assist.Math", MITest::Flags)

bool FMIAssistMathTest::RunTest(const FString& Parameters)
{
	using namespace MIAssistTestsPrivate;
	FMIAimAssist A;
	if (!LoadAssist(*this, A))
	{
		return false;
	}

	// Slow-down: eases to the device's factor inside the radius, back to 1 outside, no turn from it.
	{
		FMIAimAssist P = A, M = A, Far = A;
		FMIAssistResult R;
		for (int32 I = 0; I < 30; ++I)
		{
			R = P.Step(Frame(true, false, false), {FVector2D(1.5, 0.5)});
			M.Step(Frame(false, false, false), {FVector2D(1.5, 0.5)});
			Far.Step(Frame(true, false, false), {FVector2D(9.0, 0.0)});
		}
		TestTrue(TEXT("pad: slowed to 0.45 over a target"), FMath::IsNearlyEqual(P.GetSlow(), 0.45, 0.01));
		TestTrue(TEXT("mouse: slowed to 0.8 over a target"), FMath::IsNearlyEqual(M.GetSlow(), 0.8, 0.01));
		TestEqual(TEXT("a target far off the crosshair does not slow"), Far.GetSlow(), 1.0);
		TestTrue(TEXT("the slow-down alone turns nothing"), R.Turn.IsZero());
		for (int32 I = 0; I < 30; ++I) P.Step(Frame(true, false, false), {});
		TestTrue(TEXT("the slow-down lets go when the target is gone"), P.GetSlow() > 0.99);
		TestTrue(TEXT("it eases, not a step"), FMath::Abs(1.0 - A.Data.Pad.Slow) > 0.0 && [&]() { FMIAimAssist Q = A; Q.Step(Frame(true, false, false), {FVector2D(1, 0)}); return Q.GetSlow() > 0.46 && Q.GetSlow() < 1.0; }());
	}

	// Magnetism: only while firing, inside the cone, capped per second, toward the target.
	{
		FMIAimAssist P = A;
		TestTrue(TEXT("not firing: no pull"), P.Step(Frame(true, false, false), {FVector2D(3, 1)}).Turn.IsZero());
		FMIAssistResult R = P.Step(Frame(true, true, false), {FVector2D(3, 1)});
		TestTrue(TEXT("firing: a pull toward the target (right and up)"), R.Turn.X > 0.0 && R.Turn.Y > 0.0);
		TestTrue(TEXT("the pull is at most the cap per second"), R.Turn.Size() <= A.Data.Pad.MagRate * Dt + 1e-9);
		TestTrue(TEXT("it points at the target"), FMath::IsNearlyEqual(R.Turn.Y / R.Turn.X, 1.0 / 3.0, 1e-6));
		TestTrue(TEXT("beyond the cone: none"), P.Step(Frame(true, true, false), {FVector2D(7.5, 0)}).Turn.IsZero());
		TestTrue(TEXT("the mouse cone is narrower (3 degrees): 4 degrees is outside"), FMIAimAssist(A).Step(Frame(false, true, false), {FVector2D(4, 0)}).Turn.IsZero());
		TestFalse(TEXT("the mouse inside its cone is pulled"), FMIAimAssist(A).Step(Frame(false, true, false), {FVector2D(2, 0)}).Turn.IsZero());
		// The pull never passes the target, and fades out as the crosshair arrives.
		const FMIAssistResult Close = P.Step(Frame(true, true, false), {FVector2D(0.05, 0)});
		TestTrue(TEXT("a crosshair almost on it is not pushed past it"), Close.Turn.X > 0.0 && Close.Turn.X <= 0.05 + 1e-12);
		// The player's own input wins: turning away removes the pull, turning toward or across keeps it.
		const double With = P.Step(Frame(true, true, false, FVector2D(1, 0)), {FVector2D(3, 0)}).Turn.X;
		const double Away = P.Step(Frame(true, true, false, FVector2D(-1, 0)), {FVector2D(3, 0)}).Turn.X;
		const double Across = P.Step(Frame(true, true, false, FVector2D(0, 1)), {FVector2D(3, 0)}).Turn.X;
		TestTrue(TEXT("turning toward the target keeps the pull"), With > 0.0);
		TestEqual(TEXT("turning straight away: no pull at all"), Away, 0.0);
		TestTrue(TEXT("turning across it keeps the pull"), Across > 0.0);
		// Of two targets, the nearest to the crosshair.
		const FMIAssistResult Two = P.Step(Frame(true, true, false), {FVector2D(5, 0), FVector2D(0, -2)});
		TestTrue(TEXT("the nearest of two (the one below)"), Two.Turn.Y < 0.0 && FMath::Abs(Two.Turn.X) < 1e-9);
	}

	// ADS snap: on the press, onto the nearest target in range, over about 0.12 s, exactly on it at the end.
	{
		FMIAimAssist P = A;
		const FVector2D Target(8.0, -2.0);
		FVector2D Sum = FVector2D::ZeroVector, Err = Target;
		int32 Frames = 0;
		for (int32 I = 0; I < 20; ++I)
		{
			const FMIAssistResult R = P.Step(Frame(true, false, true), {Err});
			Sum += R.Turn;
			Err = Target - Sum;
			if (R.bSnapping) ++Frames;
		}
		TestTrue(TEXT("the snap lands on the aim point"), Sum.Equals(Target, 1e-6));
		TestTrue(TEXT("and takes about 0.12 s (4 frames at 30 Hz)"), Frames >= 3 && Frames <= 5);
		// Just pressed with the target 12 degrees off (beyond the pad's 10): nothing.
		FMIAimAssist Q = A;
		TestTrue(TEXT("beyond the snap angle: no snap"), Q.Step(Frame(true, false, true), {FVector2D(12, 0)}).Turn.IsZero());
		// The mouse's snap is 5 degrees: 7 is out, 4 is in.
		TestTrue(TEXT("mouse: 7 degrees is beyond its snap"), FMIAimAssist(A).Step(Frame(false, false, true), {FVector2D(7, 0)}).Turn.IsZero());
		TestFalse(TEXT("mouse: 4 degrees snaps"), FMIAimAssist(A).Step(Frame(false, false, true), {FVector2D(4, 0)}).Turn.IsZero());
		// Holding ADS later does not snap again; releasing and aiming again does.
		FMIAimAssist H = A;
		for (int32 I = 0; I < 10; ++I) H.Step(Frame(true, false, true), {});
		TestTrue(TEXT("holding ADS, a target that comes into range later is not snapped to"), H.Step(Frame(true, false, true), {FVector2D(6, 0)}).Turn.IsZero());
		H.Step(Frame(true, false, false), {});
		TestFalse(TEXT("a fresh ADS press snaps"), H.Step(Frame(true, false, true), {FVector2D(6, 0)}).Turn.IsZero());
		// Letting go of ADS ends a snap at once.
		FMIAimAssist L = A;
		L.Step(Frame(true, false, true), {FVector2D(6, 0)});
		TestTrue(TEXT("ADS released mid-snap: no more turn"), L.Step(Frame(true, false, false), {FVector2D(5, 0)}).Turn.IsZero());
	}

	// Strength scales reach and depth.
	{
		const double Low = A.Data.ScaleOf(TEXT("low")), High = A.Data.ScaleOf(TEXT("high"));
		TestTrue(TEXT("Low: a pad cone of 6 degrees shrinks, 5 degrees is outside it"), [&]() { FMIAimAssist Q = A; FMIAssistFrame F = Frame(true, true, false); F.Strength = Low; return Q.Step(F, {FVector2D(5, 0)}).Turn.IsZero(); }());
		TestFalse(TEXT("High: the cone grows, 7 degrees is inside"), [&]() { FMIAimAssist Q = A; FMIAssistFrame F = Frame(true, true, false); F.Strength = High; return Q.Step(F, {FVector2D(7, 0)}).Turn.IsZero(); }());
		TestTrue(TEXT("the slow-down is deeper at High and shallower at Low"), A.SlowAt(true, High) < A.SlowAt(true, 1.0) && A.SlowAt(true, Low) > A.SlowAt(true, 1.0));
		TestTrue(TEXT("never slower than the data's floor"), A.SlowAt(true, 5.0) >= A.Data.MinSlow - 1e-12);
	}

	// Off: nothing, and no memory of before.
	{
		FMIAimAssist P = A;
		for (int32 I = 0; I < 30; ++I) P.Step(Frame(true, true, true), {FVector2D(1, 0)});
		FMIAssistFrame Off = Frame(true, true, true);
		Off.bOn = false;
		const FMIAssistResult R = P.Step(Off, {FVector2D(1, 0)});
		TestTrue(TEXT("off: no turn"), R.Turn.IsZero());
		TestEqual(TEXT("off: no slow-down"), R.Slow, 1.0);
		TestEqual(TEXT("off: the slow-down state is cleared"), P.GetSlow(), 1.0);
	}
	return true;
}

namespace MIAssistTestsPrivate
{
	/** The run's world with the real player, a real controller and, as the game boots it, the assist ON (a test asks for it). */
	struct FWorld
	{
		UWorld* World = nullptr;
		AMIPlayerCharacter* Player = nullptr;
		UMIGameSubsystem* Game = nullptr;
		ULocalPlayer* LP = nullptr;
		AMIPlayerController* PC = nullptr;
		AMIGoon* Goon = nullptr;

		FWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("MIAssistWorld"));
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
			if (PC) PC->UnPossess();
			if (LP) LP->PlayerRemoved();
			World->EndPlay(EEndPlayReason::Quit);
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
		void Step()
		{
			if (Player) Player->GetPlayerRules().bInvulnerable = true;
			World->Tick(LEVELTICK_All, (float)Dt);
			GFrameCounter++;
		}
		bool Boot(FAutomationTestBase& T)
		{
			FMIBootOptions O;
			O.bTitle = false;
			O.Mode = TEXT("mission");
			O.Difficulty = TEXT("boss");
			O.bPersist = false;
			O.bAimAssist = true;
			O.bDrawGrey = false;
			if (!T.TestTrue(TEXT("the game boots from level.json"), Player && Game && Game->Boot(O)))
			{
				return false;
			}
			LP = NewObject<ULocalPlayer>(GEngine);
			LP->PlayerAdded(nullptr, INVALID_CONTROLLERID);
			PC = World->SpawnActor<AMIPlayerController>();
			if (!T.TestNotNull(TEXT("a controller"), PC))
			{
				return false;
			}
			PC->SetPlayer(LP);
			PC->Possess(Player);
			PC->SetAimAssist(true, TEXT("normal"));  // what the game flow applies from the settings
			for (int32 I = 0; I < 30; ++I) Step();
			// The nearest living Goon, with the player 7 m from it and a clear line to its chest.
			for (int32 I = 0; I < 3 && !Goon; ++I)
			{
				if (!Game->FaceNearestEnemy(7.0)) { Step(); continue; }
				for (int32 S = 0; S < 2; ++S) Step();
				Goon = NearestGoon();
			}
			return T.TestNotNull(TEXT("a Goon to aim at"), Goon);
		}
		AMIGoon* NearestGoon() const
		{
			AMIGoon* Best = nullptr;
			double BestD = TNumericLimits<double>::Max();
			for (TActorIterator<AMIGoon> It(World); It; ++It)
			{
				if (It->IsMIDamageableAlive() && It->GetBodyHit())
				{
					const double D = FVector::DistSquared(It->GetActorLocation(), Player->GetActorLocation());
					if (D < BestD) { BestD = D; Best = *It; }
				}
			}
			return Best;
		}
		FVector Chest() const
		{
			return Goon->GetBodyHit()->GetComponentLocation() + FVector::UpVector * (Goon->GetBodyHit()->GetScaledCapsuleHalfHeight() * PC->GetAimAssist().Data.ChestFraction);
		}
		/** Degrees from the crosshair to the chest: X right, Y up. */
		FVector2D Error() const
		{
			const FMIPlayerRules& R = Player->GetPlayerRules();
			const FVector To = (Chest() - R.Eye).GetSafeNormal();
			const FVector F = R.Forward.GetSafeNormal();
			return FVector2D(MI::WrapDegrees(MI::RadToDeg(FMath::Atan2(To.Y, To.X) - FMath::Atan2(F.Y, F.X))),
				MI::RadToDeg(FMath::Asin(To.Z) - FMath::Asin(F.Z)));
		}
		/** Aims Yaw/Pitch degrees off the chest (right, up). */
		void AimOff(double Yaw, double Pitch)
		{
			FMIPlayerRules& R = Player->GetPlayerRules();
			const FVector To = (Chest() - R.Eye).GetSafeNormal();
			R.Yaw = MI::WrapDegrees(MI::RadToDeg(FMath::Atan2(To.Y, To.X)) + Yaw);
			R.Pitch = MI::RadToDeg(FMath::Asin(To.Z)) + Pitch;
			Step();
		}
		/** A box across the line to the Goon's chest that stops rounds (a wall). */
		AActor* Wall() const
		{
			AActor* A = World->SpawnActor<AActor>();
			UBoxComponent* B = NewObject<UBoxComponent>(A);
			B->SetBoxExtent(FVector(20, 400, 400));
			B->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
			B->SetCollisionResponseToAllChannels(ECR_Ignore);
			B->SetCollisionResponseToChannel(MIBulletChannel, ECR_Block);
			A->SetRootComponent(B);
			B->RegisterComponent();
			const FVector From = Player->GetPlayerRules().Eye, To = Chest();
			A->SetActorLocationAndRotation(From + (To - From) * 0.5, FRotator(0, FMath::RadiansToDegrees(FMath::Atan2((To - From).Y, (To - From).X)), 0));
			return A;
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAssistWorldTest, "MurderInc.Assist.World", MITest::Flags)

bool FMIAssistWorldTest::RunTest(const FString& Parameters)
{
	using namespace MIAssistTestsPrivate;
	FWorld W;
	if (!W.Boot(*this))
	{
		return false;
	}
	FMIPlayerInputState& In = W.Player->GetInput();
	AddInfo(FString::Printf(TEXT("Goon %.1f m away, error %s"), FVector::Dist(W.Goon->GetActorLocation(), W.Player->GetActorLocation()) / 100.0, *W.Error().ToString()));

	// Engages: the pad over a visible Goon is slowed to the data's 0.45.
	W.PC->SetDeviceFromMenu(true);
	W.AimOff(1.0, 0.0);
	for (int32 I = 0; I < 12; ++I) W.Step();
	TestTrue(TEXT("pad: slowed over a visible Goon"), W.PC->GetAssistSlow() < 0.5);
	// The mouse: 0.8.
	W.PC->SetDeviceFromMenu(false);
	W.AimOff(1.0, 0.0);
	for (int32 I = 0; I < 12; ++I) W.Step();
	TestTrue(TEXT("mouse: slowed to about 0.8"), FMath::IsNearlyEqual(W.PC->GetAssistSlow(), 0.8, 0.03));
	// Off the target by 20 degrees: nothing.
	W.AimOff(20.0, 0.0);
	for (int32 I = 0; I < 12; ++I) W.Step();
	TestEqual(TEXT("far off the Goon: no slow-down"), W.PC->GetAssistSlow(), 1.0);

	// Magnetism: firing 2 degrees off pulls the view toward the chest by about the capped step; not firing leaves it.
	W.PC->SetDeviceFromMenu(true);
	W.AimOff(4.0, 0.0);
	const double Before = FMath::Abs(W.Error().X);
	W.Step();
	TestTrue(TEXT("not firing: the view is not pulled"), FMath::Abs(FMath::Abs(W.Error().X) - Before) < 0.05);
	W.AimOff(4.0, 0.0);
	In.bFire = true;
	const double Start = FMath::Abs(W.Error().X);
	W.World->Tick(LEVELTICK_All, (float)Dt);
	GFrameCounter++;
	In.bFire = false;
	const double After = FMath::Abs(W.Error().X);
	AddInfo(FString::Printf(TEXT("pull: %.3f -> %.3f degrees"), Start, After));
	TestTrue(TEXT("firing: the view is pulled toward the Goon, and gently"), After < Start - 0.01 && Start - After < 1.0);

	// ADS snap: 7 degrees off with the pad (inside 10), the aim ends on the chest within a few frames.
	W.PC->SetDeviceFromMenu(true);
	W.AimOff(7.0, 1.0);
	In.bAds = true;
	for (int32 I = 0; I < 8; ++I) W.Step();
	AddInfo(FString::Printf(TEXT("snap: error now %s"), *W.Error().ToString()));
	TestTrue(TEXT("ADS: snapped onto the Goon"), W.Error().Size() < 0.6);
	In.bAds = false;
	for (int32 I = 0; I < 4; ++I) W.Step();

	// A wall between: no slow-down, no pull, no snap.
	AActor* Wall = W.Wall();
	W.AimOff(2.0, 0.0);
	for (int32 I = 0; I < 12; ++I) W.Step();
	TestEqual(TEXT("behind a wall: no slow-down"), W.PC->GetAssistSlow(), 1.0);
	W.AimOff(2.0, 0.0);
	In.bFire = true;
	const double WallStart = W.Error().X;
	W.World->Tick(LEVELTICK_All, (float)Dt);
	In.bFire = false;
	TestTrue(TEXT("behind a wall: no pull"), FMath::Abs(W.Error().X - WallStart) < 0.01);
	W.AimOff(7.0, 0.0);
	In.bAds = true;
	for (int32 I = 0; I < 8; ++I) W.Step();
	In.bAds = false;
	TestTrue(TEXT("behind a wall: no snap"), FMath::Abs(W.Error().X - 7.0) < 0.1);
	Wall->Destroy();
	W.AimOff(2.0, 0.0);
	for (int32 I = 0; I < 12; ++I) W.Step();
	TestTrue(TEXT("the wall gone: it engages again"), W.PC->GetAssistSlow() < 0.5);

	// Switched off (the Settings row): nothing of it.
	W.PC->SetAimAssist(false, TEXT("normal"));
	W.AimOff(2.0, 0.0);
	for (int32 I = 0; I < 12; ++I) W.Step();
	TestEqual(TEXT("off: no slow-down"), W.PC->GetAssistSlow(), 1.0);
	W.AimOff(7.0, 0.0);
	In.bAds = true;
	for (int32 I = 0; I < 8; ++I) W.Step();
	In.bAds = false;
	TestTrue(TEXT("off: no snap"), FMath::Abs(W.Error().X - 7.0) < 0.1);
	return true;
}

#endif
