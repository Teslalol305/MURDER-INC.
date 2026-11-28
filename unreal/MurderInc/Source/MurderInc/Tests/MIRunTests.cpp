// Whole runs in a world with collision (no window, no GPU): the game subsystem boots the block from level.json, the
// player character plays it with his real weapon, the enemies fight back through their actors' hit volumes and the
// engine's traces, the flow decides.
//   MurderInc.Run.StoryComplete  a bot follows the objective data: fights, takes the three reels, reaches the truck
//   MurderInc.Run.StoryDeath     a bot that does not fight dies; the death card; Run it back starts the run again
//   MurderInc.Run.HoldTheBlock   a bot holds the start through three waves; scores, resupply, the card and the best
//   MurderInc.Run.Menus          title, settings validation, pause and resume through the menu model
//   MurderInc.Player.PadReloadOrGrab   the pad's X: a reload, or the grab when a reel is in reach, never both
//   MurderInc.Cloud.ViewerLeaves       a stream's last viewer leaves: the run pauses (in its intro too) and what the
//                                      viewer held is let go

#include "Cloud/MICloud.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Enemies/MIEnemyActors.h"
#include "Flow/MIGameSubsystem.h"
#include "GameFramework/WorldSettings.h"
#include "Player/MIPlayerCharacter.h"
#include "Tests/MITestUtil.h"
#include "Weapons/MICombatSubsystem.h"
#include "Weapons/MIWeaponComponent.h"
#include "World/MILevelData.h"
#include "World/MIObjectiveActors.h"
#include "Player/MISwitchInput.h"
#include "UI/MIFrontEnd.h"
#include "Weapons/MILoadoutResolver.h"
#include "Flow/MIRunSetupSubsystem.h"
#include "InputCoreTypes.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "InputKeyEventArgs.h"
#include "Player/MIPlayerController.h"
#include "Enemies/MIEnemies.h"
#include "Weapons/MIGunAssembly.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Framework/Application/SlateApplication.h"
#include "UI/SMIFrontEnd.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"

#if WITH_AUTOMATION_TESTS

namespace MIRunTestsPrivate
{
	constexpr float Dt = 1.f / 30.f;

	struct FRunWorld
	{
		UWorld* World = nullptr;
		AMIPlayerCharacter* Player = nullptr;
		UMIGameSubsystem* Game = nullptr;
		int32 PlayerHits = 0;
		int32 EnemyShots = 0;
		int32 Frames = 0;

		FRunWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("MIRunWorld"));
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
			if (FMIGameEvents* Events = UMIEventSubsystem::Get(World))
			{
				Events->PlayerHit.AddLambda([this](const FMIPlayerHitEvent&) { PlayerHits++; });
				Events->Enemy.AddLambda([this](const FMIEnemyEvent& E) { if (E.Kind == FMIEnemyEvent::EKind::Fire) EnemyShots++; });
			}
		}
		~FRunWorld()
		{
			World->EndPlay(EEndPlayReason::Quit);
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
		bool Boot(FAutomationTestBase& T, FName Mode, FName Difficulty)
		{
			FMIBootOptions O;
			O.bTitle = false;
			O.Mode = Mode;
			O.Difficulty = Difficulty;
			O.bPersist = false;
			O.bDrawGrey = false;
			return T.TestTrue(TEXT("the game boots from level.json"), Player && Game && Game->Boot(O));
		}
		void Step()
		{
			World->Tick(LEVELTICK_All, Dt);
			// Tick functions run once per engine frame (GFrameCounter): advance it as the engine's FTestWorldWrapper does.
			GFrameCounter++;
			Frames++;
		}
		EMIGameState State() const { return Game->GetRules().GetState(); }
	};

	/** The bot's eyes and trigger finger: aims the player's view at a point and fires with the real weapon. */
	struct FBot
	{
		FRunWorld& W;
		int32 Target = INDEX_NONE;
		int32 Blind = 0;
		bool bFiring = false;

		explicit FBot(FRunWorld& InW) : W(InW) {}

		FVector AimPoint(int32 Slot) const
		{
			AActor* A = W.Game->GetEnemyActor(Slot);
			if (const AMIGoon* G = Cast<AMIGoon>(A))
			{
				return G->GetBodyHit()->GetComponentLocation();
			}
			return A ? A->GetActorLocation() : FVector::ZeroVector;
		}

		bool Sees(int32 Slot) const
		{
			AActor* A = W.Game->GetEnemyActor(Slot);
			FHitResult Hit;
			FCollisionQueryParams Params(SCENE_QUERY_STAT(MIBot), false, W.Player);
			const FVector Eye = W.Player->GetPlayerRules().Eye;
			return A && W.World->LineTraceSingleByChannel(Hit, Eye, AimPoint(Slot), MIBulletChannel, Params) && Hit.GetActor() == A;
		}

		void Look(const FVector& At)
		{
			FMIPlayerRules& R = W.Player->GetPlayerRules();
			const FVector D = At - R.Eye;
			R.Yaw = FMath::RadiansToDegrees(FMath::Atan2(D.Y, D.X));
			R.Pitch = FMath::RadiansToDegrees(FMath::Atan2(D.Z, D.Size2D()));
		}

		void Release()
		{
			FMIPlayerInputState& In = W.Player->GetInput();
			In.bFire = false;
			In.bAds = false;
			bFiring = false;
		}

		/** One frame of fighting: the nearest living enemy in sight, aimed and shot. Returns false when none is in sight. */
		bool Fight()
		{
			const TArray<FMIEnemy>& Slots = W.Game->GetEnemies().GetSlots();
			const FVector Eye = W.Player->GetPlayerRules().Eye;
			int32 Best = INDEX_NONE;
			double BestD = TNumericLimits<double>::Max();
			for (int32 I = 0; I < Slots.Num(); ++I)
			{
				if (!Slots[I].bAlive || !Sees(I))
				{
					continue;
				}
				const double D = FVector::Dist(Eye, AimPoint(I));
				if (D < BestD)
				{
					Best = I;
					BestD = D;
				}
			}
			FMIPlayerInputState& In = W.Player->GetInput();
			if (Best == INDEX_NONE)
			{
				Release();
				return false;
			}
			Look(AimPoint(Best));
			In.bAds = true;
			const UMIWeaponComponent* Weapon = W.Player->GetWeapon();
			if (Weapon->GetRules().GetMag() == 0)
			{
				In.bFire = false;
				if (Weapon->GetRules().GetReserve() > 0.0)
				{
					In.bReloadPressed = true;
				}
				else
				{
					In.bWeapon2Pressed = true;  // the NINE never runs dry
				}
				bFiring = false;
				return true;
			}
			// The NINE fires per press: press again every few frames.
			if (!bFiring || W.Frames % 4 == 0)
			{
				In.bFirePressed = true;
			}
			In.bFire = true;
			bFiring = true;
			return true;
		}

		/** Goes to a place near the nearest living enemy (on walkable ground, in the open) when nothing is in sight. */
		void Hunt()
		{
			const TArray<FMIEnemy>& Slots = W.Game->GetEnemies().GetSlots();
			const FVector Me = W.Game->PlayerFeetWeb();
			const FMIEnemy* Near = nullptr;
			for (const FMIEnemy& E : Slots)
			{
				if (E.bAlive && (!Near || FVector::Dist(E.Pos, Me) < FVector::Dist(Near->Pos, Me)))
				{
					Near = &E;
				}
			}
			if (!Near)
			{
				return;
			}
			FMIBoxWorld& Box = W.Game->GetBoxWorld();
			const FVector Toward = (Me - Near->Pos).GetSafeNormal2D();
			FVector Spot;
			if (Box.NearestWalkable(Near->Pos.X + Toward.X * 5.0, Near->Pos.Z + Toward.Z * 5.0, 4.0, Spot))
			{
				W.Game->TeleportPlayerWeb(FVector(Spot.X, Box.GroundHeight(Spot.X, Spot.Z, 1.0), Spot.Z));
			}
		}

		/** The fight for one frame with a hunt when nothing has been in sight for two seconds. */
		void Engage()
		{
			if (Fight())
			{
				Blind = 0;
			}
			else if (++Blind > 60 && W.Game->GetEnemies().AliveCount() > 0)
			{
				Hunt();
				Blind = 0;
			}
		}
	};

	/** Horizontal distance in web space (x, z). */
	double HDist(const FVector& A, const FVector& B) { return MI::Web::Hypot(A.X - B.X, A.Z - B.Z); }

	void PatchUp(FRunWorld& W)
	{
		FMIPlayerRules& R = W.Player->GetPlayerRules();
		if (R.bAlive)
		{
			R.Health = R.MaxHealth;
		}
	}

	void StandAt(FRunWorld& W, const FVector& Web)
	{
		FMIBoxWorld& Box = W.Game->GetBoxWorld();
		W.Game->TeleportPlayerWeb(FVector(Web.X, Box.GroundHeight(Web.X, Web.Z, Web.Y + 0.6), Web.Z));
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIRunStoryCompleteTest, "MurderInc.Run.StoryComplete", MITest::Flags)

bool FMIRunStoryCompleteTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	if (!W.Boot(*this, TEXT("mission"), TEXT("boss")))
	{
		return false;
	}
	const FMILevelData* Level = W.Game->GetLevel();
	FBot Bot(W);
	TestEqual(TEXT("the intro runs first"), (int32)W.State(), (int32)EMIGameState::Intro);
	TestTrue(TEXT("the starting patrol is out"), W.Game->GetEnemies().AliveCount() > 0);
	int32 Step = 0;      // 0, 2, 4: take reel Step / 2; 1, 3, 5: fight; 6: to the truck
	int32 Waited = 0;
	const int32 Limit = 30 * 60 * 8;
	for (int32 F = 0; F < Limit && W.State() != EMIGameState::Complete; ++F)
	{
		PatchUp(W);  // the bot is patched up every frame: the enemies' hits still land (counted below)
		if (W.State() == EMIGameState::Playing)
		{
			FMIGameRules& R = W.Game->GetRules();
			if (Step < 6 && Step % 2 == 0)
			{
				const FMILevelObjective& O = Level->Objectives[Step / 2];
				Bot.Release();
				if (HDist(W.Game->PlayerFeetWeb(), O.Pos) > 0.6)
				{
					StandAt(W, O.Pos + FVector(0.4, 0, 0));
				}
				Bot.Look(MI::Web::ToUnreal(O.Pos) + FVector(0, 0, 80.0));
				W.Game->SetInteractHeld(true);
				if (R.GetRun().Reels > Step / 2)
				{
					W.Game->SetInteractHeld(false);
					Step++;
					Waited = 0;
				}
			}
			else if (Step < 6)
			{
				Bot.Engage();
				++Waited;
				const bool bQuiet = W.Game->GetEnemies().AliveCount() == 0 && R.QueueLength() == 0;
				if ((Waited > 30 * 8 && bQuiet) || Waited > 30 * 45)
				{
					Bot.Release();
					Step++;
				}
			}
			else
			{
				Bot.Engage();
				StandAt(W, Level->Extraction.Pos);
			}
		}
		W.Step();
	}
	const FMIGameRules& R = W.Game->GetRules();
	const FMIRunStats& S = W.Game->GetStats();
	AddInfo(FString::Printf(TEXT("story: %d frames (%.1f s game time), reels %d, kills %d, headshots %d, shots %d, hits %d, enemy rounds %d, hits on the player %d"),
		W.Frames, W.Frames * Dt, R.GetRun().Reels, S.Kills, S.Headshots, S.Shots, S.Hits, W.EnemyShots, W.PlayerHits));
	TestEqual(TEXT("the run is complete (at the truck with every reel)"), (int32)W.State(), (int32)EMIGameState::Complete);
	TestEqual(TEXT("three reels"), R.GetRun().Reels, 3);
	TestTrue(TEXT("the bot fought: kills through the weapon"), S.Kills > 0 && S.Shots > 0 && S.Hits > 0);
	TestTrue(TEXT("the enemies fought back: rounds fired and hits on the player"), W.EnemyShots > 0 && W.PlayerHits > 0);
	for (int32 I = 0; I < Level->Objectives.Num(); ++I)
	{
		const AMIReelCase* Case = W.Game->GetCase(I);
		TestTrue(FString::Printf(TEXT("case %d taken"), I), Case && Case->GetState() == EMIReelCaseState::Taken);
	}
	for (int32 I = 0; I < 30 * 4; ++I)
	{
		W.Step();
	}
	TestTrue(TEXT("the truck's doors are open"), W.Game->GetTruck() && W.Game->GetTruck()->GetState() == EMITruckState::Open);
	TestTrue(TEXT("the debrief card is up"), R.Card().IsSet() && R.Card()->Screen == TEXT("complete"));
	TestEqual(TEXT("the menu shows the debrief"), (int32)W.Game->GetMenu().Screen, (int32)EMIMenuScreen::Debrief);
	if (R.Card().IsSet())
	{
		const FMIRunCard& C = R.Card().GetValue();
		AddInfo(FString::Printf(TEXT("debrief: %s (%d), time %.1f s, accuracy %.2f, kills %d, retries %d"), *C.RatingName, C.Rating, C.Time, C.Accuracy, C.Kills, C.Retries));
		TestEqual(TEXT("card kills = the statistics"), C.Kills, S.Kills);
		TestFalse(TEXT("a rating name"), C.RatingName.IsEmpty());
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIRunStoryDeathTest, "MurderInc.Run.StoryDeath", MITest::Flags)

bool FMIRunStoryDeathTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	if (!W.Boot(*this, TEXT("mission"), TEXT("kingpin")))
	{
		return false;
	}
	const FMILevelData* Level = W.Game->GetLevel();
	// The bot takes the first reel and then stands in the open without fighting back.
	const int32 Limit = 30 * 60 * 4;
	for (int32 F = 0; F < Limit && W.State() != EMIGameState::Dead; ++F)
	{
		if (W.State() == EMIGameState::Playing)
		{
			StandAt(W, Level->Objectives[0].Pos + FVector(0.4, 0, 0));
			W.Game->SetInteractHeld(W.Game->GetRules().GetRun().Reels == 0);
		}
		W.Step();
	}
	AddInfo(FString::Printf(TEXT("death after %.1f s: %d enemy rounds, %d hits on the player"), W.Frames * Dt, W.EnemyShots, W.PlayerHits));
	TestEqual(TEXT("the player died"), (int32)W.State(), (int32)EMIGameState::Dead);
	TestTrue(TEXT("killed by enemy fire"), W.PlayerHits > 0 && !W.Player->GetPlayerRules().bAlive);
	for (int32 I = 0; I < 30 * 2; ++I)
	{
		W.Step();
	}
	const FMIGameRules& R = W.Game->GetRules();
	TestTrue(TEXT("the death card is up"), R.Card().IsSet() && R.Card()->Screen == TEXT("dead"));
	TestEqual(TEXT("the menu shows it"), (int32)W.Game->GetMenu().Screen, (int32)EMIMenuScreen::Dead);
	TestEqual(TEXT("its first item is Run it back"), W.Game->GetMenu().Current() ? W.Game->GetMenu().Current()->Id : NAME_None, FName(TEXT("retry")));
	W.Game->MenuConfirm();
	TestEqual(TEXT("Run it back: the intro again"), (int32)W.State(), (int32)EMIGameState::Intro);
	TestEqual(TEXT("one retry counted"), R.GetRun().Retries, 1);
	W.Step();
	TestTrue(TEXT("the player stands again with full health"), W.Player->GetPlayerRules().bAlive && W.Player->GetPlayerRules().Health == W.Player->GetPlayerRules().MaxHealth);
	TestEqual(TEXT("no reel"), R.GetRun().Reels, 0);
	TestTrue(TEXT("at the start"), HDist(W.Game->PlayerFeetWeb(), Level->PlayerStart.Pos) < 0.5);
	TestEqual(TEXT("the menu is gone"), (int32)W.Game->GetMenu().Screen, (int32)EMIMenuScreen::None);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIRunHoldTheBlockTest, "MurderInc.Run.HoldTheBlock", MITest::Flags)

bool FMIRunHoldTheBlockTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	if (!W.Boot(*this, TEXT("holdout"), TEXT("boss")))
	{
		return false;
	}
	FBot Bot(W);
	int32 Reserves = 0, Heals = 0, Waves = 0;
	if (FMIGameEvents* Events = UMIEventSubsystem::Get(W.World))
	{
		Events->Flow.AddLambda([&](const FMIFlowEvent& E)
		{
			if (E.Name == TEXT("holdout:wave")) Waves++;
		});
	}
	FMIGameRules& R = W.Game->GetRules();
	double ReserveBefore = -1.0;
	const int32 Limit = 30 * 60 * 8;
	for (int32 F = 0; F < Limit && R.WavesCleared() < 3; ++F)
	{
		PatchUp(W);
		if (W.State() == EMIGameState::Playing)
		{
			Bot.Engage();
		}
		const double Reserve = W.Player->GetWeapon()->GetRules().GetReserveOf(0);
		if (ReserveBefore >= 0.0 && Reserve > ReserveBefore)
		{
			Reserves++;
		}
		ReserveBefore = Reserve;
		W.Step();
	}
	const FMIRunStats& S = W.Game->GetStats();
	AddInfo(FString::Printf(TEXT("hold the block: %.1f s, waves cleared %d, score %.0f, kills %d, shots %d, hits %d, enemy rounds %d, hits on the player %d, resupplies %d"),
		W.Frames * Dt, R.WavesCleared(), R.GetRun().Score, S.Kills, S.Shots, S.Hits, W.EnemyShots, W.PlayerHits, Reserves));
	TestTrue(TEXT("three waves cleared"), R.WavesCleared() >= 3);
	TestTrue(TEXT("wave banners"), Waves >= 3);
	TestTrue(TEXT("a score from kills"), R.GetRun().Score > 0 && S.Kills > 0);
	TestTrue(TEXT("resupply between waves"), Reserves > 0);
	TestTrue(TEXT("the enemies fought back"), W.EnemyShots > 0 && W.PlayerHits > 0);
	// The end: the player goes down; the card holds the score and the best.
	FMIDamage Kill;
	Kill.Amount = 1e6;
	Kill.Source = EMIDamageSource::World;
	Kill.Kind = EMIDamageKind::Fall;
	W.Player->ApplyMIDamage(Kill);
	for (int32 I = 0; I < 30 * 2; ++I)
	{
		W.Step();
	}
	TestEqual(TEXT("dead"), (int32)W.State(), (int32)EMIGameState::Dead);
	if (TestTrue(TEXT("the death card"), R.Card().IsSet()))
	{
		const FMIRunCard& C = R.Card().GetValue();
		AddInfo(FString::Printf(TEXT("card: wave %d, score %d, best %d, new best %d"), C.Wave, C.Score, C.Best, C.bNewBest));
		TestTrue(TEXT("score on the card"), C.Score > 0 && C.Best >= C.Score && C.bNewBest);
		TestEqual(TEXT("best kept by the settings"), W.Game->GetSettings().GetBest(), C.Score);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIRunMenusTest, "MurderInc.Run.Menus", MITest::Flags)

bool FMIRunMenusTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	// The web game's validation (spec 04 2.16, verified there): fov 200 -> 120, 90.6 -> 91 (the slider is horizontal degrees at 16:9 since the v6 finish, DECISIONS.md 2026-11-26), sens 0.01 -> 0.2, volume 2 -> 1, quality 'test' rejected.
	FMISettings S;
	FString Error;
	if (!TestTrue(TEXT("settings defaults load: ") + Error, FMISettings::LoadDefaults(S, Error)))
	{
		return false;
	}
	TestEqual(TEXT("default mode"), S.Mode, FName(TEXT("mission")));
	TestEqual(TEXT("default fov"), S.Fov, 90.0);
	S.SetFov(200);
	TestEqual(TEXT("fov 200 -> 120"), S.Fov, 120.0);
	S.SetFov(90.6);
	TestEqual(TEXT("fov 90.6 -> 91"), S.Fov, 91.0);
	S.SetSens(0.01);
	TestEqual(TEXT("sens 0.01 -> 0.2"), S.Sens, 0.2);
	S.SetVolume(2);
	TestEqual(TEXT("volume 2 -> 1"), S.Volume, 1.0);
	TestFalse(TEXT("quality 'test' rejected"), S.SetQuality(TEXT("test")));
	TestFalse(TEXT("view 4 rejected"), S.SetView(4));
	TestTrue(TEXT("a first best is a record"), S.SetBest(1234.4) && S.GetBest() == 1234);
	TestFalse(TEXT("a lower score is not"), S.SetBest(1000));

	// The game on the title: the menu, a pick, the start, the pause card and back.
	FRunWorld W;
	FMIBootOptions O;
	O.bPersist = false;
	O.bDrawGrey = false;
	if (!TestTrue(TEXT("boots on the title"), W.Game && W.Game->Boot(O)))
	{
		return false;
	}
	W.Step();
	TestEqual(TEXT("title"), (int32)W.State(), (int32)EMIGameState::Title);
	FMIMenu& M = W.Game->GetMenu();
	TestEqual(TEXT("the title menu"), (int32)M.Screen, (int32)EMIMenuScreen::Title);
	TestFalse(TEXT("the simulation is off on the title"), W.Game->IsSimulationLive());
	M.Selected = M.IndexOf(TEXT("mode"));
	W.Game->MenuAdjust(1);
	TestEqual(TEXT("mode picker: Hold the Block"), W.Game->GetSettings().Mode, FName(TEXT("holdout")));
	W.Game->MenuAdjust(1);
	TestEqual(TEXT("and back to Story"), W.Game->GetSettings().Mode, FName(TEXT("mission")));
	M.Selected = M.IndexOf(TEXT("start"));
	W.Game->MenuConfirm();
	TestEqual(TEXT("Hit the block: the intro"), (int32)W.State(), (int32)EMIGameState::Intro);
	for (int32 I = 0; I < 30 * 3; ++I)
	{
		W.Step();
	}
	TestEqual(TEXT("playing after the intro"), (int32)W.State(), (int32)EMIGameState::Playing);
	TestTrue(TEXT("the simulation runs"), W.Game->IsSimulationLive());
	W.Game->PauseKey();
	TestEqual(TEXT("paused"), (int32)W.State(), (int32)EMIGameState::Paused);
	TestEqual(TEXT("the pause card"), (int32)M.Screen, (int32)EMIMenuScreen::Pause);
	W.Game->PauseKey();
	TestEqual(TEXT("the pause key within the debounce does nothing"), (int32)W.State(), (int32)EMIGameState::Paused);
	M.Selected = M.IndexOf(TEXT("settings"));
	W.Game->MenuConfirm();
	TestEqual(TEXT("settings from the pause card"), (int32)M.Screen, (int32)EMIMenuScreen::Settings);
	M.Selected = M.IndexOf(TEXT("fov"));
	W.Game->MenuAdjust(1);
	TestEqual(TEXT("field of view one degree up"), W.Game->GetSettings().Fov, 91.0);
	W.Game->MenuBack();
	TestEqual(TEXT("back to the pause card"), (int32)M.Screen, (int32)EMIMenuScreen::Pause);
	M.Selected = M.IndexOf(TEXT("resume"));
	W.Game->MenuConfirm();
	TestEqual(TEXT("resumed"), (int32)W.State(), (int32)EMIGameState::Playing);
	TestEqual(TEXT("no menu in play"), (int32)M.Screen, (int32)EMIMenuScreen::None);
	return true;
}

namespace MIRunTestsPrivate
{
	/** A booted title with the set-up screens up (a fresh player: played is false). */
	UMIFrontEnd* BootTitle(FAutomationTestBase& T, FRunWorld& W)
	{
		FMIBootOptions O;
		O.bPersist = false;
		O.bDrawGrey = false;
		if (!T.TestTrue(TEXT("boots on the title"), W.Game && W.Game->Boot(O)))
		{
			return nullptr;
		}
		W.Step();
		UMIFrontEnd* F = W.Game->GetFrontEnd();
		if (!T.TestNotNull(TEXT("the set-up flow replaces the canvas title"), F))
		{
			return nullptr;
		}
		T.TestTrue(TEXT("shown on the title"), F->IsShown());
		T.TestEqual(TEXT("Home"), F->GetRules().GetScreen(), EMIFrontScreen::Home);
		return F;
	}

	/** One real key press through Slate (FSlateApplication::ProcessKeyDownEvent / ProcessKeyUpEvent), then a frame. */
	void Press(FAutomationTestBase& T, FRunWorld& W, UMIFrontEnd* F, const FKey& K, bool bCtrl = false)
	{
		T.TestTrue(FString::Printf(TEXT("%s%s is handled by the set-up screens"), bCtrl ? TEXT("Ctrl+") : TEXT(""), *K.ToString()), F->PressKey(K, bCtrl));
		W.Step();
	}

	void Expect(FAutomationTestBase& T, UMIFrontEnd* F, EMIFrontScreen S, const TCHAR* What)
	{
		T.TestEqual(What, FMIFrontEndRules::ScreenName(F->GetRules().GetScreen()), FMIFrontEndRules::ScreenName(S));
	}
}

// LOADOUT.md 8.5: the whole set-up flow in a world, Home to the run, with the keyboard only: every step is a real key
// event routed by Slate to the screens (no MIMenu verbs).
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFrontendWalkWorldTest, "MurderInc.Frontend.WalkWorld", MITest::Flags)

bool FMIFrontendWalkWorldTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	UMIFrontEnd* F = BootTitle(*this, W);
	if (!F)
	{
		return false;
	}
	// Enter on Home: the first Hit the block opens Crew.
	Press(*this, W, F, EKeys::Enter);
	Expect(*this, F, EMIFrontScreen::Crew, TEXT("first time: Enter opens Crew"));
	// Down past the last row reaches Next; Enter on Next advances.
	Press(*this, W, F, EKeys::Down);
	TestTrue(TEXT("Crew: Down past the cards focuses Next"), F->bOnNext);
	Press(*this, W, F, EKeys::Enter);
	Expect(*this, F, EMIFrontScreen::Loadout, TEXT("Enter on Next: Loadout"));
	TestEqual(TEXT("the parity guns"), F->GetRules().GetSetup().Guns, TArray<FName>{TEXT("chopper"), TEXT("nine")});
	// The NEW tags: the card focused on arrival and every card focused later lose it, and the save keeps that.
	TestFalse(TEXT("the CHOPPER, focused on arrival, is no longer NEW"), F->GetRules().IsNew(TEXT("chopper")));
	TestTrue(TEXT("the NINE is NEW until focused"), F->GetRules().IsNew(TEXT("nine")));
	Press(*this, W, F, EKeys::Right);
	TestFalse(TEXT("Right onto the NINE: not NEW"), F->GetRules().IsNew(TEXT("nine")));
	Press(*this, W, F, EKeys::Left);
	TestEqual(TEXT("Left: back on the CHOPPER"), F->GetRules().GetFocusGun(), FName(TEXT("chopper")));
	TestFalse(TEXT("the CHOPPER stays seen"), F->GetRules().IsNew(TEXT("chopper")));
	{
		FMISetupSave Save;
		FMIRunSetup Back;
		UMIRunSetupSubsystem::ToSave(F->GetRules().GetSetup(), Save);
		UMIRunSetupSubsystem::FromSave(Save, Back);
		TestTrue(TEXT("seen survives a save round trip"), Back.Seen.Contains(TEXT("chopper")) && Back.Seen.Contains(TEXT("nine")));
	}
	// Tab cycles the rack, the slots and Next; Enter on Next goes to Block & Style (never straight to the Briefing).
	Press(*this, W, F, EKeys::Tab);
	TestEqual(TEXT("Tab: the slots"), F->Pane, 1);
	Press(*this, W, F, EKeys::Tab);
	TestTrue(TEXT("Tab again: Next"), F->bOnNext);
	Press(*this, W, F, EKeys::Enter);
	Expect(*this, F, EMIFrontScreen::Where, TEXT("Enter on Next: Block & Style"));
	// Block & Style: four rows, then Next.
	for (int32 I = 0; I < 3; ++I) Press(*this, W, F, EKeys::Down);
	TestFalse(TEXT("the difficulty row is not Next"), F->bOnNext);
	// Up walks back (READY.md W3: the keyboard's Up arrow), Down returns to the difficulty row.
	Press(*this, W, F, EKeys::Up);
	TestEqual(TEXT("Up: the mode row"), F->Focus, 2);
	Press(*this, W, F, EKeys::Down);
	TestEqual(TEXT("Down: the difficulty row again"), F->Focus, 3);
	Press(*this, W, F, EKeys::Down);
	TestTrue(TEXT("Down past the difficulty row: Next"), F->bOnNext);
	Press(*this, W, F, EKeys::Enter);
	Expect(*this, F, EMIFrontScreen::Briefing, TEXT("Enter on Next: the Briefing"));
	// Esc twice goes back to Loadout; Ctrl+Enter jumps to the Briefing.
	Press(*this, W, F, EKeys::Escape);
	Expect(*this, F, EMIFrontScreen::Where, TEXT("Esc: Block & Style"));
	Press(*this, W, F, EKeys::Escape);
	Expect(*this, F, EMIFrontScreen::Loadout, TEXT("Esc: Loadout"));
	Press(*this, W, F, EKeys::Enter, true);
	Expect(*this, F, EMIFrontScreen::Briefing, TEXT("Ctrl+Enter: the Briefing"));
	for (int32 I = 0; I < 3; ++I) W.Step();
	// Enter on the Briefing (Hit the block is focused) starts the run.
	Press(*this, W, F, EKeys::Enter);
	TestEqual(TEXT("Hit the block: the intro"), (int32)W.State(), (int32)EMIGameState::Intro);
	TestFalse(TEXT("the front end is down in the run"), F->IsShown());

	// Loadout.ParityPIE's first half: after the run reset from the front end, the weapon's data is the resolver's
	// parity output, which is config.json's.
	const FMIWeaponRules& Rules = W.Player->GetWeapon()->GetRules();
	FMIConfigData Config;
	FString Error;
	if (UMIDataSubsystem::LoadConfig(Config, Error) && TestEqual(TEXT("two guns"), Rules.NumGuns(), 2))
	{
		for (int32 I = 0; I < 2; ++I)
		{
			const FMIWeaponDef& A = Rules.GetData().Guns[I];
			const FMIWeaponDef& B = Config.Weapons.Guns[I];
			TestTrue(FString::Printf(TEXT("gun %d is config.json's"), I), A.Id == B.Id && A.Damage == B.Damage && A.Rpm == B.Rpm && A.AdsTime == B.AdsTime
				&& A.Spread.Hip == B.Spread.Hip && A.Recoil.Pitch == B.Recoil.Pitch && A.Holster == B.Holster && A.Draw == B.Draw && A.NoiseRadius == B.NoiseRadius
				&& A.Reload.Tactical == B.Reload.Tactical && A.WallStart == B.WallStart && A.FalloffStart == B.FalloffStart);
		}
		TestEqual(TEXT("the bag is the CHOPPER's reserve"), Rules.GetBag(), 150.0);
	}
	return !HasAnyErrors();
}

// The same walk on a pad: Start is Next on every set-up screen, so crew, loadout, block and style and the Briefing come
// in order; D-pad down past the last row then A also advances; View+Start jumps to the Briefing.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFrontendWalkPadTest, "MurderInc.Frontend.WalkPad", MITest::Flags)

bool FMIFrontendWalkPadTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	UMIFrontEnd* F = BootTitle(*this, W);
	if (!F)
	{
		return false;
	}
	Press(*this, W, F, EKeys::Gamepad_Special_Right);
	Expect(*this, F, EMIFrontScreen::Crew, TEXT("Start on Home, first time: Crew"));
	TestTrue(TEXT("a pad key switches the glyphs to the pad's"), F->IsPad());
	Press(*this, W, F, EKeys::Gamepad_Special_Right);
	Expect(*this, F, EMIFrontScreen::Loadout, TEXT("Start on Crew: Loadout"));
	Press(*this, W, F, EKeys::Gamepad_Special_Right);
	Expect(*this, F, EMIFrontScreen::Where, TEXT("Start on Loadout: Block & Style, not the Briefing"));
	Press(*this, W, F, EKeys::Gamepad_Special_Right);
	Expect(*this, F, EMIFrontScreen::Briefing, TEXT("Start on Block & Style: the Briefing"));
	Press(*this, W, F, EKeys::Gamepad_FaceButton_Right);
	Expect(*this, F, EMIFrontScreen::Where, TEXT("B: Block & Style"));
	Press(*this, W, F, EKeys::Gamepad_FaceButton_Right);
	Expect(*this, F, EMIFrontScreen::Loadout, TEXT("B: Loadout"));
	// D-pad down past the rack's last row lands on Next; A there advances.
	for (int32 I = 0; I < 4 && !F->bOnNext; ++I) Press(*this, W, F, EKeys::Gamepad_DPad_Down);
	TestTrue(TEXT("D-pad down reaches Next"), F->bOnNext);
	Press(*this, W, F, EKeys::Gamepad_FaceButton_Bottom);
	Expect(*this, F, EMIFrontScreen::Where, TEXT("A on Next: Block & Style"));
	Press(*this, W, F, EKeys::Gamepad_FaceButton_Right);
	Expect(*this, F, EMIFrontScreen::Loadout, TEXT("B: Loadout again"));
	// The chord: hold View, press Start.
	TestTrue(TEXT("View down"), F->SendKey(EKeys::Gamepad_Special_Left, true));
	Press(*this, W, F, EKeys::Gamepad_Special_Right);
	F->SendKey(EKeys::Gamepad_Special_Left, false);
	Expect(*this, F, EMIFrontScreen::Briefing, TEXT("View+Start: the Briefing"));
	for (int32 I = 0; I < 3; ++I) W.Step();
	Press(*this, W, F, EKeys::Gamepad_Special_Right);
	TestEqual(TEXT("Start on the Briefing: the intro"), (int32)W.State(), (int32)EMIGameState::Intro);
	return !HasAnyErrors();
}

namespace MIRunTestsPrivate
{
	/** The widget of the current build whose tag is Tag (the Workbench's options are tagged MIOption.<part>). */
	TSharedPtr<SWidget> FindTagged(const TSharedRef<SWidget>& Root, FName Tag)
	{
		if (Root->GetTag() == Tag)
		{
			return Root;
		}
		FChildren* Children = Root->GetChildren();
		for (int32 I = 0; Children && I < Children->Num(); ++I)
		{
			if (TSharedPtr<SWidget> Found = FindTagged(Children->GetChildAt(I), Tag))
			{
				return Found;
			}
		}
		return nullptr;
	}

	/** Slate's paint of the set-up widget: Slate ticks a widget while it paints it, after the frame's layout pass. */
	void SlatePaint(SMIFrontEnd& Widget)
	{
		const FGeometry Geo = FGeometry::MakeRoot(FVector2f(1920.f, 1080.f), FSlateLayoutTransform());
		Widget.Tick(Geo, FSlateApplication::Get().GetCurrentTime(), 1.f / 60.f);
	}

	/** One engine frame: the game thread (the front end's tick), then Slate's layout pass and paint. */
	void SlateFrame(UMIFrontEnd* F, SMIFrontEnd& Widget)
	{
		F->Tick(1.0 / 60.0);
		Widget.SlatePrepass(1.f);
		SlatePaint(Widget);
	}
}

// READY.md M1: the set-up screens flickered in the stream. (1) A screen must never be rebuilt while Slate paints (after
// the frame's layout pass: its controls were drawn piled at the top for one frame): it is rebuilt on the game thread,
// before Slate's layout pass. (2) A pointer resting on a Workbench
// option is told it is hovered again after each rebuild: that must not rebuild the screen again (it strobed at 20 Hz
// with 20 hover sounds a second); a leave from a replaced button is ignored; a pointer that left while the screen was
// rebuilt still ends its preview.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFrontendSteadyTest, "MurderInc.Frontend.Steady", MITest::Flags)

bool FMIFrontendSteadyTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	UMIFrontEnd* F = BootTitle(*this, W);
	if (!F || !TestTrue(TEXT("Slate is up"), FSlateApplication::IsInitialized()) || !TestNotNull(TEXT("a renderer measures text"), FSlateApplication::Get().GetRenderer()))
	{
		return false;
	}
	TSharedPtr<SMIFrontEnd> Widget = F->GetWidget();
	if (!TestTrue(TEXT("the set-up widget"), Widget.IsValid()))
	{
		return false;
	}
	SlateFrame(F, *Widget);
	// (1) A screen change: the paint does not rebuild; the game thread does, and Slate's layout pass then measures it.
	F->Act(TEXT("gearup"));
	const int32 BuildsBefore = Widget->GetBuildCount();
	SlatePaint(*Widget);
	TestEqual(TEXT("Slate's paint never rebuilds the screen"), Widget->GetBuildCount(), BuildsBefore);
	F->Tick(1.0 / 60.0);
	TestEqual(TEXT("the game thread's tick rebuilds it, before Slate's frame"), Widget->GetBuildCount(), BuildsBefore + 1);
	Widget->SlatePrepass(1.f);
	const FVector2D Desired = Widget->GetChildren()->GetChildAt(0)->GetDesiredSize();
	TestTrue(FString::Printf(TEXT("Crew is measured before it is drawn (desired %.0f x %.0f)"), Desired.X, Desired.Y), Desired.X > 100.0 && Desired.Y > 100.0);
	SlatePaint(*Widget);
	// (2) The Workbench: the first carried gun with options.
	F->Act(TEXT("next"));
	FName Gun;
	for (const FName G : F->GetRules().GetSetup().Guns)
	{
		F->Act(TEXT("bench"), G.ToString());
		if (F->GetRules().BenchOptions(F->GetRules().GetBenchSlot()).Num() > 1)
		{
			Gun = G;
			break;
		}
	}
	if (!TestFalse(TEXT("a carried gun has Workbench options"), Gun.IsNone()))
	{
		return false;
	}
	SlateFrame(F, *Widget);
	const TArray<FName> Options = F->GetRules().BenchOptions(F->GetRules().GetBenchSlot());
	const FName Part = Options.Last();
	const FString Arg = Part.IsNone() ? FString(TEXT("factory")) : Part.ToString();
	const FName Tag(*(TEXT("MIOption.") + Arg));
	const FPointerEvent Pointer;
	const FGeometry Geo = FGeometry::MakeRoot(FVector2f(1920.f, 1080.f), FSlateLayoutTransform());
	TSharedPtr<SWidget> Btn = FindTagged(Widget.ToSharedRef(), Tag);
	if (!TestTrue(TEXT("the option's button"), Btn.IsValid()))
	{
		return false;
	}
	// The pointer comes to rest on the option: one preview, one rebuild. Then Slate does what it does after each
	// rebuild: the replaced button is left, the new one under the pointer is entered.
	Btn->OnMouseEnter(Geo, Pointer);
	TestTrue(TEXT("the hover previews the part"), F->GetRules().IsPreviewing() && F->GetRules().GetPreviewed() == Part);
	const int32 Builds0 = Widget->GetBuildCount();
	for (int32 Frame = 0; Frame < 40; ++Frame)
	{
		SlateFrame(F, *Widget);
		const TSharedPtr<SWidget> Now = FindTagged(Widget.ToSharedRef(), Tag);
		if (Now.IsValid() && Now != Btn)
		{
			Btn->OnMouseLeave(Pointer);
			Now->OnMouseEnter(Geo, Pointer);
			Btn = Now;
		}
	}
	TestEqual(TEXT("a pointer resting on an option for 40 frames rebuilds the Workbench once"), Widget->GetBuildCount() - Builds0, 1);
	TestTrue(TEXT("and the part stays previewed"), F->GetRules().IsPreviewing() && F->GetRules().GetPreviewed() == Part);
	const int32 V0 = F->GetVersion();
	F->Act(TEXT("preview"), Arg);
	TestEqual(TEXT("previewing the part already previewed changes nothing (no rebuild, no hover sound)"), F->GetVersion(), V0);
	// The pointer leaves: the preview ends, the screen rebuilds once.
	Btn->OnMouseLeave(Pointer);
	TestFalse(TEXT("leaving the option ends its preview"), F->GetRules().IsPreviewing());
	SlateFrame(F, *Widget);
	// A leave from a replaced button does not end the preview of the new one.
	Btn = FindTagged(Widget.ToSharedRef(), Tag);
	Btn->OnMouseEnter(Geo, Pointer);
	SlateFrame(F, *Widget);
	Btn->OnMouseLeave(Pointer);  // the button before this rebuild
	TestTrue(TEXT("a replaced button's leave is ignored"), F->GetRules().IsPreviewing() && F->GetRules().GetPreviewed() == Part);
	// The new button was never entered (the pointer left during the rebuild): a few frames later the preview ends.
	for (int32 Frame = 0; Frame < 6; ++Frame) SlateFrame(F, *Widget);
	TestFalse(TEXT("a pointer gone during a rebuild still ends the preview"), F->GetRules().IsPreviewing());
	return !HasAnyErrors();
}

// LOADOUT.md 2.6a: a picked gun's parts are on the Loadout itself, beside the rack, and work by mouse, keyboard and pad:
// nothing is behind E, the screen never changes. The options are in the widget tree of the Loadout, the keys act on them
// (Right from the last card or E enters the panel, Up and Down look at a part, Enter fits, Backspace takes it off, Esc
// leaves the panel and only then the screen), and so do the pad's Y, D-pad, A, X and B.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFrontendLoadoutPartsWorldTest, "MurderInc.Frontend.LoadoutPartsWorld", MITest::Flags)

bool FMIFrontendLoadoutPartsWorldTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	UMIFrontEnd* F = BootTitle(*this, W);
	if (!F || !TestTrue(TEXT("Slate is up"), FSlateApplication::IsInitialized()) || !TestNotNull(TEXT("a renderer measures text"), FSlateApplication::Get().GetRenderer()))
	{
		return false;
	}
	TSharedPtr<SMIFrontEnd> Widget = F->GetWidget();
	if (!TestTrue(TEXT("the set-up widget"), Widget.IsValid()))
	{
		return false;
	}
	F->Act(TEXT("gearup"));
	F->Act(TEXT("next"));
	Expect(*this, F, EMIFrontScreen::Loadout, TEXT("Loadout"));
	FMIFrontEndRules& R = F->GetRules();
	// A gun with parts to choose from.
	FName Gun;
	for (const FName G : R.GetSetup().Guns)
	{
		F->Act(TEXT("carry"), G.ToString());
		if (R.GetBenchSlot() != NAME_None && R.BenchOptions(R.GetBenchSlot()).Num() > 1)
		{
			Gun = G;
			break;
		}
	}
	if (Gun.IsNone())
	{
		AddInfo(TEXT("No carried gun has parts to choose from here (no gun art installed): nothing to check."));
		return true;
	}
	// (1) The parts are on the Loadout, not behind a screen: the first option's button is in the widget tree.
	SlateFrame(F, *Widget);
	Expect(*this, F, EMIFrontScreen::Loadout, TEXT("picking a gun keeps the Loadout"));
	TestEqual(TEXT("the picked gun's parts are the panel's"), R.GetBenchGun(), Gun);
	const TArray<FName> Options = R.BenchOptions(R.GetBenchSlot());
	const auto TagOf = [](FName Part) { return FName(*(TEXT("MIOption.") + (Part.IsNone() ? FString(TEXT("factory")) : Part.ToString()))); };
	TestTrue(TEXT("the first option is on the Loadout"), FindTagged(Widget.ToSharedRef(), TagOf(Options[0])).IsValid());
	TestTrue(TEXT("and the last"), FindTagged(Widget.ToSharedRef(), TagOf(Options.Last())).IsValid());
	// (2) The keyboard: E (or Right from the last card) enters the panel, Down looks, Enter fits, Esc leaves it.
	F->Act(TEXT("carry"), Gun.ToString());
	TestEqual(TEXT("a picked card has the rack's keys"), F->Pane, 0);
	Press(*this, W, F, EKeys::E);
	TestEqual(TEXT("E: the parts panel"), F->Pane, 2);
	Expect(*this, F, EMIFrontScreen::Loadout, TEXT("E does not open another screen"));
	const FName Slot = R.GetBenchSlot();
	Press(*this, W, F, EKeys::Down);
	const FName Looked = R.BenchOptions(Slot)[FMath::Min(F->Focus, R.BenchOptions(Slot).Num() - 1)];
	TestTrue(TEXT("Down: a look at the next option"), R.IsPreviewing() && R.GetPreviewed() == Looked);
	TestTrue(TEXT("the look is on the stage's build"), R.ShownBuild().Parts.FindRef(Slot) == Looked);
	Press(*this, W, F, EKeys::Enter);
	TestEqual(TEXT("Enter: fitted"), R.FittedIn(Slot), Looked);
	TestFalse(TEXT("a fit ends the look"), R.IsPreviewing());
	if (R.BenchOptions(Slot).Contains(NAME_None))
	{
		Press(*this, W, F, EKeys::BackSpace);
		TestEqual(TEXT("Backspace: the factory part"), R.FittedIn(Slot), FName(NAME_None));
	}
	Press(*this, W, F, EKeys::Escape);
	Expect(*this, F, EMIFrontScreen::Loadout, TEXT("Esc in the panel stays on the Loadout"));
	TestEqual(TEXT("Esc: back on the card"), F->Pane, 0);
	// Right from the last card of the rack reaches the panel too.
	{
		const TArray<FName> Rack = R.Rack(F->RackFilter);
		F->Act(TEXT("carry"), Rack.Last().ToString());
		if (R.BenchSlots().Num() > 0)
		{
			Press(*this, W, F, EKeys::Right);
			TestEqual(TEXT("Right from the last card: the parts panel"), F->Pane, 2);
			Press(*this, W, F, EKeys::Left);
			TestEqual(TEXT("Left from the first slot: the card"), F->Pane, 0);
		}
		F->Act(TEXT("carry"), Gun.ToString());
	}
	// (3) The mouse: a slot chip and an option, no pane to enter.
	{
		const TArray<FName> Slots = R.BenchSlots();
		const FName Next = Slots.IsValidIndex(1) ? Slots[1] : Slots[0];
		F->Act(TEXT("benchslot"), Next.ToString());
		TestEqual(TEXT("the slot chip chooses the slot"), R.GetBenchSlot(), Next);
		const TArray<FName> Opts = R.BenchOptions(Next);
		const FName Pick = Opts.Last();
		F->Act(TEXT("fit"), Pick.IsNone() ? TEXT("factory") : Pick.ToString());
		TestEqual(TEXT("a click on an option fits it"), R.FittedIn(Next), Pick);
		Expect(*this, F, EMIFrontScreen::Loadout, TEXT("the mouse stays on the Loadout"));
	}
	// (4) The pad: Y to the panel, D-pad Down looks, A fits, B back to the card, B again leaves the screen.
	F->Act(TEXT("carry"), Gun.ToString());
	R.ChooseBenchSlot(R.BenchSlots()[0]);  // the first slot, with its first option fitted: Down has an option to look at
	R.Fit(R.BenchOptions(R.GetBenchSlot())[0]);
	Press(*this, W, F, EKeys::Gamepad_FaceButton_Top);
	TestEqual(TEXT("Y: the parts panel"), F->Pane, 2);
	Press(*this, W, F, EKeys::Gamepad_DPad_Down);
	TestTrue(TEXT("D-pad down: a look"), R.IsPreviewing());
	const FName PadSlot = R.GetBenchSlot();
	const FName PadLook = R.GetPreviewed();
	Press(*this, W, F, EKeys::Gamepad_FaceButton_Bottom);
	TestEqual(TEXT("A: fitted"), R.FittedIn(PadSlot), PadLook);
	Press(*this, W, F, EKeys::Gamepad_FaceButton_Right);
	TestEqual(TEXT("B: back on the card"), F->Pane, 0);
	Expect(*this, F, EMIFrontScreen::Loadout, TEXT("B in the panel stays on the Loadout"));
	Press(*this, W, F, EKeys::Gamepad_FaceButton_Right);
	Expect(*this, F, EMIFrontScreen::Crew, TEXT("B on the card: the step before"));
	return !HasAnyErrors();
}

// The stream's flicker when parts are fitted (docs/unreal/DECISIONS.md 2026-11-28): every fit and every look at a part rebuilds the
// Loadout, and for ONE frame the new option cards were drawn with their wrapped text on one line, clipped, the effect lines and the
// bars missing (a thumbnail of that single frame in the stream shows it: Red dot's blurb cut to "Gets on target fast, a little").
// An auto-wrapping text block (STextBlock AutoWrapText: the engine's own header warns "the wrapped size will be computed at least
// one frame late") measures itself at the width of its last paint, and a new one has none. A text that wraps at a width it is
// given measures right in the layout pass before its first paint. A headless test never paints, so it cannot see the frame: it
// asks the widget tree instead. No text of the Loadout (or of its parts panel) may be an auto-wrapping one.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFrontendFirstLayoutTest, "MurderInc.Frontend.FirstLayout", MITest::Flags)

namespace MIRunTestsPrivate
{
	/** Texts under Root that wrap by themselves (AutoWrapText), and how many texts there are. */
	void CountAutoWrap(const TSharedRef<SWidget>& Root, int32& AutoWrapped, int32& Texts, FString& First)
	{
		if (Root->GetType() == FName(TEXT("STextBlock")))
		{
			++Texts;
			const STextBlock& T = static_cast<const STextBlock&>(Root.Get());
			if (T.GetAutoWrapText())
			{
				++AutoWrapped;
				if (First.IsEmpty()) First = T.GetText().ToString().Left(40);
			}
		}
		FChildren* Children = Root->GetChildren();
		for (int32 I = 0; Children && I < Children->Num(); ++I)
		{
			CountAutoWrap(Children->GetChildAt(I), AutoWrapped, Texts, First);
		}
	}
}

bool FMIFrontendFirstLayoutTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	UMIFrontEnd* F = BootTitle(*this, W);
	if (!F || !TestTrue(TEXT("Slate is up"), FSlateApplication::IsInitialized()))
	{
		return false;
	}
	TSharedPtr<SMIFrontEnd> Widget = F->GetWidget();
	if (!TestTrue(TEXT("the set-up widget"), Widget.IsValid()))
	{
		return false;
	}
	F->Act(TEXT("gearup"));
	F->Act(TEXT("next"));
	FMIFrontEndRules& R = F->GetRules();
	// A gun with parts: its options, the effect lines of a part looked at, the keys line.
	for (const FName G : R.GetSetup().Guns)
	{
		F->Act(TEXT("carry"), G.ToString());
		if (R.GetBenchSlot() != NAME_None && R.BenchOptions(R.GetBenchSlot()).Num() > 1)
		{
			break;
		}
	}
	if (R.GetBenchSlot() != NAME_None)
	{
		F->Act(TEXT("preview"), R.BenchOptions(R.GetBenchSlot()).Last().IsNone() ? FString(TEXT("factory")) : R.BenchOptions(R.GetBenchSlot()).Last().ToString());
	}
	SlateFrame(F, *Widget);
	int32 Wrapped = 0, Texts = 0;
	FString First;
	CountAutoWrap(Widget.ToSharedRef(), Wrapped, Texts, First);
	TestTrue(TEXT("the Loadout draws texts"), Texts > 20);
	TestEqual(FString::Printf(TEXT("no text of the Loadout wraps by itself (first: '%s'): it would be drawn on one line in the first frame after each rebuild"), *First), Wrapped, 0);
	return !HasAnyErrors();
}

// READY.md M6, M7 and W3: the keyboard's Up, Home's Settings and Controls by keys, and a pad that can always leave the
// Loadout's slots.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFrontendKeysReachTest, "MurderInc.Frontend.KeysReach", MITest::Flags)

bool FMIFrontendKeysReachTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	UMIFrontEnd* F = BootTitle(*this, W);
	if (!F)
	{
		return false;
	}
	TestEqual(TEXT("Home has ten controls"), F->NumFocusable(), 10);
	for (int32 I = 0; I < 8; ++I) Press(*this, W, F, EKeys::Down);
	TestEqual(TEXT("Down x8: SETTINGS"), F->Focus, 8);
	Press(*this, W, F, EKeys::Down);
	TestEqual(TEXT("Down: CONTROLS"), F->Focus, 9);
	Press(*this, W, F, EKeys::Up);
	TestEqual(TEXT("Up: back on SETTINGS"), F->Focus, 8);
	Press(*this, W, F, EKeys::Down);
	const bool bWas = F->bShowControls;
	Press(*this, W, F, EKeys::Enter);
	TestEqual(TEXT("Enter on CONTROLS opens the controls list"), F->bShowControls, !bWas);
	TestEqual(TEXT("still Home"), F->GetRules().GetScreen(), EMIFrontScreen::Home);
	Press(*this, W, F, EKeys::Down);
	TestEqual(TEXT("Down from CONTROLS wraps to Hit the block"), F->Focus, 0);
	Press(*this, W, F, EKeys::Up);
	TestEqual(TEXT("Up from Hit the block wraps to CONTROLS"), F->Focus, 9);
	// The pad on Loadout: RB to the slots, D-pad up from the first slot back to the rack; Y on an empty slot too.
	F->Act(TEXT("gearup"));
	F->Act(TEXT("next"));
	Expect(*this, F, EMIFrontScreen::Loadout, TEXT("Loadout"));
	Press(*this, W, F, EKeys::Gamepad_RightShoulder);
	TestEqual(TEXT("RB: the slots"), F->Pane, 1);
	Press(*this, W, F, EKeys::Gamepad_DPad_Up);
	TestEqual(TEXT("D-pad up from slot 1: the rack"), F->Pane, 0);
	Press(*this, W, F, EKeys::Gamepad_RightShoulder);
	const int32 Empty = F->GetRules().GetSetup().Guns.Num();
	for (int32 I = 0; I < Empty; ++I) Press(*this, W, F, EKeys::Gamepad_DPad_Right);
	TestEqual(TEXT("D-pad right walks the slots to the first empty one"), F->Focus, Empty);
	Press(*this, W, F, EKeys::Gamepad_FaceButton_Top);
	TestEqual(TEXT("Y on an empty slot: the rack"), F->Pane, 0);
	// The keyboard's Up on a set-up screen (Block & Style): Down, Down, Up.
	F->Act(TEXT("next"));
	Expect(*this, F, EMIFrontScreen::Where, TEXT("Block & Style"));
	Press(*this, W, F, EKeys::Down);
	Press(*this, W, F, EKeys::Down);
	Press(*this, W, F, EKeys::Up);
	TestEqual(TEXT("Up on Block & Style moves the focus up"), F->Focus, 1);
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutParityPIETest, "MurderInc.Loadout.ParityPIE", MITest::Flags)

bool FMILoadoutParityPIETest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	FMIBootOptions O;
	O.bPersist = false;
	O.bDrawGrey = false;
	if (!TestTrue(TEXT("boots on the title"), W.Game && W.Game->Boot(O)) || !TestNotNull(TEXT("front end"), W.Game->GetFrontEnd()))
	{
		return false;
	}
	W.Step();
	UMIFrontEnd* F = W.Game->GetFrontEnd();
	F->GetRules().EditSetup().bPlayed = true;
	F->Act(TEXT("hit"));  // played: Hit the block starts at once with the remembered (default) set-up
	TestEqual(TEXT("a returning player starts in one press"), (int32)W.State(), (int32)EMIGameState::Intro);
	for (int32 I = 0; I < 30 * 3; ++I) W.Step();
	TestEqual(TEXT("playing"), (int32)W.State(), (int32)EMIGameState::Playing);
	// The resolver's parity output in the weapon component.
	FMILoadoutData D;
	TSharedPtr<FJsonObject> Config, Presentation;
	FMIResolvedRun Run;
	FString Error;
	if (FMILoadoutData::Load(D, Error) && FMILoadoutResolver::LoadRoots(Config, Presentation, Error)
		&& FMILoadoutResolver(D, Config, Presentation).Resolve(D.ParitySetup(TEXT("mission"), TEXT("boss"), TEXT("day")), nullptr, Run, Error))
	{
		const FMIWeaponRules& Rules = W.Player->GetWeapon()->GetRules();
		for (int32 I = 0; I < FMath::Min(2, Rules.NumGuns()); ++I)
		{
			const FMIWeaponDef& A = Rules.GetData().Guns[I];
			const FMIWeaponDef& B = Run.Weapons.Guns[I];
			TestTrue(FString::Printf(TEXT("gun %d = the resolver's parity output"), I), A.Id == B.Id && A.Damage == B.Damage && A.Interval() == B.Interval()
				&& A.Spread.Ads == B.Spread.Ads && A.Recoil.WeaveAmp == B.Recoil.WeaveAmp && A.FireModes == B.FireModes && A.AdsFov == B.AdsFov);
		}
	}
	// Holding Q for 1 s with two guns opens no wheel and gives exactly one swap, on the press frame.
	FMISwitchInput Q;
	Q.SetGuns(W.Player->GetWeapon()->GetRules().NumGuns());
	int32 Switches = 0;
	FDelegateHandle H;
	if (FMIGameEvents* Events = UMIEventSubsystem::Get(W.World))
	{
		H = Events->WeaponSwitch.AddLambda([&Switches](const FMISwitchEvent& E) { if (E.Phase == TEXT("holster")) ++Switches; });
	}
	const double T0 = 100.0;
	for (int32 I = 0; I <= 30; ++I)
	{
		if (I == 0) Q.SwapDown(T0);
		Q.Tick(T0 + I * Dt);
		const FMISwitchFrame Frame = Q.Consume();
		FMIPlayerInputState& In = W.Player->GetInput();
		In.bSwapPressed |= Frame.bSwap;
		TestFalse(TEXT("no wheel with two guns"), Q.IsWheelOpen());
		W.Step();
		if (I == 0) TestEqual(TEXT("the swap starts on the press frame"), Switches, 1);
	}
	Q.SwapUp(T0 + 1.0);
	W.Player->GetInput().bSwapPressed |= Q.Consume().bSwap;
	W.Step();
	TestEqual(TEXT("exactly one swap for a 1 s hold"), Switches, 1);
	if (FMIGameEvents* Events = UMIEventSubsystem::Get(W.World))
	{
		Events->WeaponSwitch.Remove(H);
	}
	// After a death: Change set-up opens the Briefing on the title; Back to title opens Home.
	W.Game->DamagePlayer(1000.0, W.Player->GetActorLocation() + FVector(100, 0, 0), TEXT("bullet"));
	for (int32 I = 0; I < 30 * 3 && W.Game->GetMenu().Screen != EMIMenuScreen::Dead; ++I) W.Step();
	FMIMenu& M = W.Game->GetMenu();
	if (TestEqual(TEXT("the death card"), (int32)M.Screen, (int32)EMIMenuScreen::Dead))
	{
		const int32 Change = M.IndexOf(TEXT("changesetup"));
		TestTrue(TEXT("Change set-up between Run it back and Back to title"), Change > M.IndexOf(TEXT("retry")) && Change < M.IndexOf(TEXT("totitle")));
		M.Selected = Change;
		W.Game->MenuConfirm();
		TestEqual(TEXT("Change set-up: the title"), (int32)W.State(), (int32)EMIGameState::Title);
		TestEqual(TEXT("... on the Briefing"), F->GetRules().GetScreen(), EMIFrontScreen::Briefing);
		TestTrue(TEXT("the front end is up"), F->IsShown());
	}
	return !HasAnyErrors();
}

namespace MIRunTestsPrivate
{
	/** Boots the title, makes every pack mesh count as present (so a clean checkout offers the pack guns and parts) and
	 *  starts a run with Setup through Hit the block; returns once the run plays and the first gun is up. */
	UMIFrontEnd* StartWith(FAutomationTestBase& T, FRunWorld& W, TFunction<void(FMIRunSetup&)> Edit)
	{
		UMIFrontEnd* F = BootTitle(T, W);
		if (!F)
		{
			return nullptr;
		}
		F->GetRules().EditReadinessForTest().AssetExists = [](const FString&) { return true; };
		FMIRunSetup& S = F->GetRules().EditSetup();
		Edit(S);
		S.bPlayed = true;
		F->Act(TEXT("hit"));
		for (int32 I = 0; I < 30 * 4 && W.State() != EMIGameState::Playing; ++I) W.Step();
		T.TestEqual(TEXT("playing"), (int32)W.State(), (int32)EMIGameState::Playing);
		for (int32 I = 0; I < 60; ++I) W.Step();
		return F;
	}

	/** One round from the current gun. */
	void FireOnce(FRunWorld& W)
	{
		FMIPlayerInputState& In = W.Player->GetInput();
		In.bFirePressed = true;
		In.bFire = true;
		W.Step();
		In.bFire = false;
		W.Step();
	}
}

// LOADOUT.md 8.2 probes in play: a set-up that is not the parity one (the STICK with the scope and the silencer, then a
// bare CHOPPER) reaches the weapon component through the run reset, the aimed view narrows to the scope's 30 degrees,
// and the silenced round is heard 18 m out where the bare one is heard 45 m out (the cm -> m step of the listener).
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutBuildPIETest, "MurderInc.Loadout.BuildPIE", MITest::Flags)

bool FMILoadoutBuildPIETest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	UMIFrontEnd* F = StartWith(*this, W, [](FMIRunSetup& S)
	{
		S.Guns = {TEXT("stick"), TEXT("chopper")};
		FMIGunBuild& B = S.Builds.FindOrAdd(TEXT("stick"));
		B.Parts.Add(TEXT("optic"), TEXT("scope"));
		B.Parts.Add(TEXT("muzzle"), TEXT("silencer"));
	});
	if (!F)
	{
		return false;
	}
	// The weapon component holds the resolver's output for this set-up, not config.json's.
	const FMIWeaponRules& Rules = W.Player->GetWeapon()->GetRules();
	FMIResolvedRun Run;
	FString Error;
	FMIRunSetup Expected = F->GetRules().GetSetup();
	F->GetReadiness().Validate(Expected);
	TSharedPtr<FJsonObject> Config, Presentation;
	if (!TestTrue(TEXT("the set-up resolves"), FMILoadoutResolver::LoadRoots(Config, Presentation, Error)
		&& FMILoadoutResolver(F->GetRules().GetData(), Config, Presentation).Resolve(Expected, &F->GetReadiness(), Run, Error)))
	{
		AddError(Error);
		return false;
	}
	if (!TestEqual(TEXT("two guns"), Rules.NumGuns(), 2))
	{
		return false;
	}
	for (int32 I = 0; I < 2; ++I)
	{
		const FMIWeaponDef& A = Rules.GetData().Guns[I];
		const FMIWeaponDef& B = Run.Weapons.Guns[I];
		TestTrue(FString::Printf(TEXT("gun %d = the resolver's output for the set-up"), I), A.Id == B.Id && A.Damage == B.Damage && A.Interval() == B.Interval()
			&& A.Spread.Ads == B.Spread.Ads && A.AdsTime == B.AdsTime && A.AdsFov == B.AdsFov && A.NoiseRadius == B.NoiseRadius && A.bSuppressed == B.bSuppressed);
	}
	const FMIWeaponDef& Stick = Rules.GetData().Guns[0];
	TestEqual(TEXT("slot 1 is the STICK"), Stick.Id, FName(TEXT("stick")));
	TestEqual(TEXT("the scope's aimed view"), Stick.AdsFov, 30.0);
	TestEqual(TEXT("the silencer's noise radius (cm)"), Stick.NoiseRadius, 1800.0);
	TestTrue(TEXT("suppressed"), Stick.bSuppressed);
	TestEqual(TEXT("the CHOPPER is bare: heard 45 m out"), Rules.GetData().Guns[1].NoiseRadius, 4500.0);

	// The aimed view at full aim: the scope's 30 degrees (vertical), not the bare gun's.
	FMIPlayerInputState& In = W.Player->GetInput();
	In.bAds = true;
	for (int32 I = 0; I < 30 * 3; ++I) W.Step();
	TestNearlyEqual(TEXT("the view at full aim is 30 degrees"), W.Player->GetPlayerRules().ViewFov, 30.0, 0.05);
	In.bAds = false;
	for (int32 I = 0; I < 30 * 2; ++I) W.Step();

	// Noise: two Goons facing away, 30 m and 15 m out. The silenced round reaches the near one only.
	FMIEnemyField& Field = W.Game->GetEnemies();
	const FVector Me = W.Game->PlayerFeetWeb();
	FMIEnemySpawnOptions Away;
	Away.Yaw = 0.0;
	const FMIEnemy* Far = Field.Spawn(MIEnemy::EType::Goon, Me + FVector(30.0, 0.0, 0.0), Away);
	const FMIEnemy* Near = Field.Spawn(MIEnemy::EType::Goon, Me + FVector(-15.0, 0.0, 0.0), Away);
	if (!TestTrue(TEXT("two listeners"), Far && Near))
	{
		return false;
	}
	const int32 FarId = Far->Id, NearId = Near->Id;
	const auto Heard = [&Field](int32 Id) { const FMIEnemy* E = Field.Find(Id); return E && E->Mode == EMIEnemyMode::Investigate; };
	TestFalse(TEXT("nobody listening yet"), Heard(FarId) || Heard(NearId));
	FireOnce(W);
	TestTrue(TEXT("silenced: heard at 15 m"), Heard(NearId));
	TestFalse(TEXT("silenced: not heard at 30 m"), Heard(FarId));
	// The bare CHOPPER: heard 45 m out, by a fresh listener 30 m out (the first one may have moved on meanwhile).
	In.bWeapon2Pressed = true;
	for (int32 I = 0; I < 30 * 2; ++I) W.Step();
	TestEqual(TEXT("the CHOPPER is up"), Rules.GetCurrentIndex(), 1);
	const FMIEnemy* Far2 = Field.Spawn(MIEnemy::EType::Goon, W.Game->PlayerFeetWeb() + FVector(0.0, 0.0, 30.0), Away);
	if (!TestNotNull(TEXT("a second listener"), Far2))
	{
		return false;
	}
	const int32 Far2Id = Far2->Id;
	TestFalse(TEXT("the second listener has heard nothing yet"), Heard(Far2Id));
	FireOnce(W);
	TestTrue(TEXT("bare: heard at 30 m"), Heard(Far2Id));
	return !HasAnyErrors();
}

// LOADOUT.md 8.4 through the controller's own key mappings: a real local player and AMIPlayerController with its
// Enhanced Input mapping context; keys go in through APlayerController::InputKey, as the viewport sends them.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIControllerKeysTest, "MurderInc.Player.ControllerKeys", MITest::Flags)

bool FMIControllerKeysTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	UMIFrontEnd* F = StartWith(*this, W, [](FMIRunSetup& S)
	{
		S.Guns = {TEXT("chopper"), TEXT("nine"), TEXT("stick"), TEXT("stretch")};
	});
	if (!F)
	{
		return false;
	}
	ULocalPlayer* LP = NewObject<ULocalPlayer>(GEngine);
	LP->PlayerAdded(nullptr, INVALID_CONTROLLERID);  // no controller id: no force feedback, which needs a game instance
	AMIPlayerController* PC = W.World->SpawnActor<AMIPlayerController>();
	if (!TestNotNull(TEXT("controller"), PC))
	{
		return false;
	}
	PC->SetPlayer(LP);
	PC->Possess(W.Player);
	UEnhancedInputLocalPlayerSubsystem* Sub = LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>();
	if (TestNotNull(TEXT("Enhanced Input on the local player"), Sub))
	{
		FModifyContextOptions Now;
		Now.bForceImmediately = true;
		Sub->RequestRebuildControlMappings(Now);
	}
	const FMIWeaponRules& Rules = W.Player->GetWeapon()->GetRules();
	TestEqual(TEXT("four guns"), Rules.NumGuns(), 4);
	const auto Key = [&](const FKey& K, EInputEvent E)
	{
		PC->InputKey(FInputKeyEventArgs(nullptr, FInputDeviceId::CreateFromInternalId(0), K, E, E == IE_Released ? 0.f : 1.f, false, FPlatformTime::Cycles64()));
	};
	const auto Tap = [&](const FKey& K, int32 HoldFrames = 2)
	{
		Key(K, IE_Pressed);
		for (int32 I = 0; I < HoldFrames; ++I) W.Step();
		Key(K, IE_Released);
		W.Step();
	};
	const auto Settle = [&]() { for (int32 I = 0; I < 45; ++I) W.Step(); };
	// 3: slot 3.
	Tap(EKeys::Three);
	Settle();
	TestEqual(TEXT("3 selects slot 3"), Rules.GetCurrentIndex(), 2);
	// A Q tap with four guns swaps on release, back to the last gun used.
	Tap(EKeys::Q, 2);
	Settle();
	TestEqual(TEXT("a Q tap goes back to the last gun"), Rules.GetCurrentIndex(), 0);
	// A Q hold opens the wheel after wheel.hold; release shuts it.
	Key(EKeys::Q, IE_Pressed);
	for (int32 I = 0; I < 12; ++I) W.Step();
	TestTrue(TEXT("holding Q opens the wheel"), PC->GetSwitch().IsWheelOpen());
	Key(EKeys::Q, IE_Released);
	W.Step();
	TestFalse(TEXT("releasing Q shuts the wheel"), PC->GetSwitch().IsWheelOpen());
	Settle();
	// The pad: D-pad right is slot 2.
	Tap(EKeys::Gamepad_DPad_Right);
	Settle();
	TestEqual(TEXT("D-pad right selects slot 2"), Rules.GetCurrentIndex(), 1);
	// The mouse wheel down is next.
	Tap(EKeys::MouseScrollDown, 1);
	Settle();
	TestEqual(TEXT("wheel down: the next gun"), Rules.GetCurrentIndex(), 2);
	// B flips the selector of a gun with two modes (the STICK).
	if (Rules.HasTwoModes(2))
	{
		const bool bSemi = Rules.IsSemi(2);
		Tap(EKeys::B);
		Settle();
		TestNotEqual(TEXT("B flips the fire mode"), Rules.IsSemi(2), bSemi);
	}
	PC->UnPossess();
	LP->PlayerRemoved();
	return !HasAnyErrors();
}

// The stage and the first-person gun build a gun with UMIGunAssembly: every fitted part takes the gun's scale, whatever
// the gun's scale is when the part is fitted (the rack's swap scales the turntable out and in, and parts fitted then
// came out 16 times too big). Needs the pack's STICK and scope (skipped without them).
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutPartsScaleTest, "MurderInc.Loadout.PartsScale", MITest::Flags)

bool FMILoadoutPartsScaleTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FMILoadoutData D;
	TSharedPtr<FJsonObject> Config, Presentation;
	FString Error;
	if (!TestTrue(TEXT("data"), FMILoadoutData::Load(D, Error) && FMILoadoutResolver::LoadRoots(Config, Presentation, Error)))
	{
		AddError(Error);
		return false;
	}
	FMIReadiness Ready;
	Ready.Data = &D;
	Ready.AssetExists = FMIReadiness::PackageExists();
	if (!Ready.OfferedParts(TEXT("stick"), TEXT("optic")).Contains(TEXT("scope")))
	{
		AddInfo(TEXT("The pack's STICK and scope are not installed here: nothing to check (LOADOUT.md 6.7)."));
		return true;
	}
	FMIGunBuild Build;
	Build.Parts.Add(TEXT("optic"), TEXT("scope"));
	Build.Parts.Add(TEXT("muzzle"), TEXT("silencer"));
	FMIResolvedGun G;
	if (!TestTrue(TEXT("the STICK resolves"), FMILoadoutResolver(D, Config, Presentation).ResolveGun(TEXT("stick"), &Build, &Ready, G, Error)))
	{
		AddError(Error);
		return false;
	}
	FRunWorld W;
	AActor* Holder = W.World->SpawnActor<AActor>();
	USkeletalMeshComponent* Base = NewObject<USkeletalMeshComponent>(Holder);
	Holder->SetRootComponent(Base);
	Base->RegisterComponent();
	UMIGunAssembly* Assembly = NewObject<UMIGunAssembly>(Holder);
	Assembly->RegisterComponent();
	Base->SetWorldScale3D(FVector(0.06));  // mid scale-out
	Assembly->Assemble(Base, G, true);
	Base->SetWorldScale3D(FVector(1.0));   // scaled back in
	int32 Parts = 0;
	for (USceneComponent* C : Base->GetAttachChildren())
	{
		if (const UStaticMeshComponent* P = Cast<UStaticMeshComponent>(C))
		{
			++Parts;
			TestTrue(FString::Printf(TEXT("%s has the gun's scale"), *GetNameSafe(P->GetStaticMesh())), P->GetComponentScale().Equals(FVector(1.0), 1e-4));
		}
	}
	TestTrue(TEXT("the scope and the silencer are fitted"), Parts >= 2);
	return !HasAnyErrors();
}

namespace MIRunTestsPrivate
{
	/** A real local player and AMIPlayerController on the run's player, as the game has them: keys and axes go in
	 *  through APlayerController::InputKey, as the viewport sends them. */
	struct FControllerRig
	{
		FRunWorld& W;
		ULocalPlayer* LP = nullptr;
		AMIPlayerController* PC = nullptr;

		explicit FControllerRig(FRunWorld& InW) : W(InW)
		{
			LP = NewObject<ULocalPlayer>(GEngine);
			LP->PlayerAdded(nullptr, INVALID_CONTROLLERID);  // no controller id: no force feedback, which needs a game instance
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
		~FControllerRig()
		{
			if (PC) PC->UnPossess();
			LP->PlayerRemoved();
		}
		void Key(const FKey& K, EInputEvent E) const
		{
			PC->InputKey(FInputKeyEventArgs(nullptr, FInputDeviceId::CreateFromInternalId(0), K, E, E == IE_Released ? 0.f : 1.f, false, FPlatformTime::Cycles64()));
		}
		void Axis(const FKey& K, float Value) const
		{
			PC->InputKey(FInputKeyEventArgs(nullptr, FInputDeviceId::CreateFromInternalId(0), K, Value, Dt, 1, FPlatformTime::Cycles64()));
		}
		/** Steps with an axis held: a browser's pad sends its axes every frame. */
		void Hold(const FKey& K, float Value, int32 Frames) const
		{
			for (int32 I = 0; I < Frames; ++I)
			{
				Axis(K, Value);
				W.Step();
			}
		}
		void Rest(const FKey& K) const
		{
			Hold(K, 0.f, 2);
		}
	};

	/** The yaw turned over Frames steps of Do (degrees, right positive), whatever way it wraps. */
	double YawTurned(FRunWorld& W, int32 Frames, TFunctionRef<void()> Do)
	{
		double Sum = 0.0, Last = W.Player->GetPlayerRules().Yaw;
		for (int32 I = 0; I < Frames; ++I)
		{
			Do();
			const double Yaw = W.Player->GetPlayerRules().Yaw;
			Sum += FMath::FindDeltaAngleDegrees(Last, Yaw);
			Last = Yaw;
		}
		return Sum;
	}
}

// The gamepad through the controller's own mappings (spec 01 3.16, 3.17; version 3, play through the stream): the right
// stick turns the view at the web game's rate, the pad becomes the device in use (the aim slow-down's switch), the stick
// picks on the weapon wheel while that is open and turns nothing meanwhile, the left stick has its dead zone, the
// triggers fire and aim from their axes (a browser's pad sends nothing else for them), L3 latches the sprint.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIControllerPadTest, "MurderInc.Player.ControllerPad", MITest::Flags)

bool FMIControllerPadTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	UMIFrontEnd* F = StartWith(*this, W, [](FMIRunSetup& S)
	{
		S.Guns = {TEXT("chopper"), TEXT("nine"), TEXT("stick"), TEXT("stretch")};
	});
	if (!F)
	{
		return false;
	}
	FControllerRig Rig(W);
	if (!TestNotNull(TEXT("controller"), Rig.PC))
	{
		return false;
	}
	FMIPlayerRules& Rules = W.Player->GetPlayerRules();
	FMIPlayerInputState& In = W.Player->GetInput();
	Rules.bInvulnerable = true;  // the Goons of the run may shoot: nobody dies in an input test
	// Looking at the ground: no enemy can come under the crosshair, so the aim slow-down stays out of the turn rate.
	Rules.Pitch = -80.0;
	W.Step();
	TestFalse(TEXT("the keyboard and mouse are the device at the start"), Rig.PC->IsPadActive());

	// Full right stick for one second (30 frames here): the web game's functions give 264.775 degrees at 30 frames a
	// second (166 degrees a second, 291 once the boost is full after 0.45 s; MurderInc.Input.PadLook has the 60 fps
	// number too).
	int32 Frame = 0;
	const double Turned = YawTurned(W, 34, [&]() { Rig.Axis(EKeys::Gamepad_RightX, Frame++ < 30 ? 1.f : 0.f); W.Step(); });
	TestTrue(FString::Printf(TEXT("full right stick for one second turns 264.775 degrees to the right (turned %.3f)"), Turned), FMath::IsNearlyEqual(Turned, 264.77546849244663, 0.01));
	AddInfo(FString::Printf(TEXT("full right stick for one second (30 frames): %.4f degrees; the web game's functions give 264.7755"), Turned));
	TestTrue(TEXT("the pad is the device in use after stick input"), Rig.PC->IsPadActive());
	TestTrue(TEXT("and the weapon rules are told (the aim slow-down)"), In.bPad);
	TestEqual(TEXT("the stick at rest turns nothing"), YawTurned(W, 10, [&]() { Rig.Axis(EKeys::Gamepad_RightX, 0.05f); W.Step(); }), 0.0);

	// Stick up looks up, at 62 % of the yaw rate. The game viewport hands the controller the right stick's Y upside
	// down (FSceneViewport::OnAnalogValueChanged negates Gamepad_RightY): a stick pushed up arrives here as -1, and the
	// rig stands where the viewport stands. (The stream test found it: stick up looked down.)
	const float StickUp = -1.f;
	Rules.Pitch = -80.0;
	Rig.Hold(EKeys::Gamepad_RightY, StickUp, 15);
	Rig.Rest(EKeys::Gamepad_RightY);
	TestTrue(FString::Printf(TEXT("stick up for half a second looks up (pitch %.2f)"), Rules.Pitch), Rules.Pitch > -80.0 + 60.0 && Rules.Pitch < -80.0 + 80.0);
	Rig.Hold(EKeys::Gamepad_RightY, -StickUp, 15);
	Rig.Rest(EKeys::Gamepad_RightY);
	TestTrue(FString::Printf(TEXT("stick down for half a second looks back down (pitch %.2f)"), Rules.Pitch), Rules.Pitch < -80.0 + 10.0);
	Rules.Pitch = -80.0;

	// A key press takes the device back; so do four pixels of mouse travel in one frame, but not a nudge.
	Rig.Key(EKeys::LeftShift, IE_Pressed);
	W.Step();
	Rig.Key(EKeys::LeftShift, IE_Released);
	W.Step();
	TestFalse(TEXT("a key press makes the keyboard and mouse the device"), Rig.PC->IsPadActive());
	W.Step();
	TestFalse(TEXT("and the weapon rules are told"), In.bPad);
	Rig.Key(EKeys::Gamepad_FaceButton_Top, IE_Pressed);
	W.Step();
	Rig.Key(EKeys::Gamepad_FaceButton_Top, IE_Released);
	for (int32 I = 0; I < 60; ++I) W.Step();
	TestTrue(TEXT("a pad button makes the pad the device"), Rig.PC->IsPadActive());
	Rig.Axis(EKeys::MouseX, 2.f);
	W.Step();
	TestTrue(TEXT("a nudge of the mouse (2 counts) does not take the device back"), Rig.PC->IsPadActive());
	Rig.Axis(EKeys::MouseX, 4.f);
	W.Step();
	TestFalse(TEXT("4 counts of mouse travel in one frame do"), Rig.PC->IsPadActive());

	// The desktop mouse is what it was: counts x player.input.mouse (0.120321 degrees) x sensitivity.
	const double Mouse = YawTurned(W, 3, [&, N = 0]() mutable { if (N++ == 0) Rig.Axis(EKeys::MouseX, 300.f); W.Step(); });
	TestTrue(FString::Printf(TEXT("desktop: 300 mouse counts turn 36.096 degrees (turned %.4f)"), Mouse), FMath::IsNearlyEqual(Mouse, 300.0 * 0.12032113697747288, 1e-6));
	AddInfo(FString::Printf(TEXT("desktop mouse: 300 counts turned %.5f degrees (0.120321 a count, as before)"), Mouse));

	// The mouse through a stream: events one by one, 2 counts a pixel less the one lost on the way; the engine's own
	// mouse axis is ignored meanwhile; a spike is dropped and counted.
	FMIStreamMouse Shape;
	Shape.Scale = 0.5;
	Shape.Truncation = 1.0;
	Shape.Glitch = 400.0;
	Rig.PC->SetStreamMouse(Shape);
	const double Stream = YawTurned(W, 3, [&, N = 0]() mutable
	{
		if (N++ == 0)
		{
			TestTrue(TEXT("stream: a 10-pixel event is kept"), Rig.PC->StreamMouseEvent(FVector2D(19.0, 0.0)));   // 10 pixels
			TestTrue(TEXT("stream: a 1-pixel event is kept"), Rig.PC->StreamMouseEvent(FVector2D(1.0, 0.0)));     // 1 pixel
			TestTrue(TEXT("stream: a 5-pixel event is kept"), Rig.PC->StreamMouseEvent(FVector2D(9.0, 0.0)));     // 5 pixels
			TestFalse(TEXT("stream: a 2000-count event is a spike"), Rig.PC->StreamMouseEvent(FVector2D(-2000.0, 0.0)));
			Rig.Axis(EKeys::MouseX, 300.f);  // the engine's axis: not used in a stream
		}
		W.Step();
	});
	TestTrue(FString::Printf(TEXT("stream: 10 + 1 + 5 browser pixels turn 1.925 degrees (turned %.4f)"), Stream), FMath::IsNearlyEqual(Stream, 16.0 * 0.12032113697747288, 1e-6));
	AddInfo(FString::Printf(TEXT("stream mouse: events of 19, 1 and 9 counts (10, 1 and 5 browser pixels) turned %.5f degrees; 16 pixels are 1.92514"), Stream));
	TestEqual(TEXT("stream: one spike counted"), Rig.PC->GetMouseSpikes(), 1);
	Rig.PC->ClearStreamMouse();

	// The triggers' axes: beyond pad.trigger (0.35) the trigger is down. One pull is one press.
	In.bFirePressed = false;
	Rig.Hold(EKeys::Gamepad_RightTriggerAxis, 0.2f, 2);
	TestFalse(TEXT("a right trigger at 0.2 does not fire"), In.bFire);
	Rig.Axis(EKeys::Gamepad_RightTriggerAxis, 0.6f);
	W.Step();
	TestTrue(TEXT("a right trigger at 0.6 fires"), In.bFire);
	Rig.Hold(EKeys::Gamepad_RightTriggerAxis, 1.f, 3);
	TestTrue(TEXT("and holds the fire"), In.bFire);
	Rig.Rest(EKeys::Gamepad_RightTriggerAxis);
	TestFalse(TEXT("letting the trigger go ends the fire"), In.bFire);
	Rig.Hold(EKeys::Gamepad_LeftTriggerAxis, 0.9f, 3);
	TestTrue(TEXT("the left trigger's axis aims"), In.bAds);
	Rig.Rest(EKeys::Gamepad_LeftTriggerAxis);
	TestFalse(TEXT("letting it go ends the aim"), In.bAds);
	for (int32 I = 0; I < 45; ++I) W.Step();

	// The left stick: nothing inside the dead zone, the rest rescaled; on top of the keys.
	Rig.Hold(EKeys::Gamepad_LeftY, 0.1f, 2);
	TestEqual(TEXT("the left stick inside its dead zone moves nothing"), In.Move.Y, 0.0);
	Rig.Hold(EKeys::Gamepad_LeftY, 0.57f, 2);
	TestTrue(FString::Printf(TEXT("the left stick at 0.57 is half forward (%.4f)"), In.Move.Y), FMath::IsNearlyEqual(In.Move.Y, 0.5, 1e-4));
	// L3 latches the sprint while the stick is forward; easing off lets it go.
	Rig.Hold(EKeys::Gamepad_LeftY, 1.f, 2);
	Rig.Key(EKeys::Gamepad_LeftThumbstick, IE_Pressed);
	Rig.Hold(EKeys::Gamepad_LeftY, 1.f, 1);
	Rig.Key(EKeys::Gamepad_LeftThumbstick, IE_Released);
	Rig.Hold(EKeys::Gamepad_LeftY, 1.f, 5);
	TestTrue(TEXT("one click of L3 holds the sprint"), Rig.PC->IsSprintLatched() && In.bSprint);
	Rig.Hold(EKeys::Gamepad_LeftY, 0.3f, 2);
	TestFalse(TEXT("easing the stick off forward lets the sprint go"), Rig.PC->IsSprintLatched() || In.bSprint);
	Rig.Rest(EKeys::Gamepad_LeftY);
	TestEqual(TEXT("the stick at rest: no move"), In.Move.Y, 0.0);

	// The weapon wheel keeps the stick: holding Y (four guns) opens it, the stick picks, the view does not turn.
	Rig.Key(EKeys::Gamepad_FaceButton_Top, IE_Pressed);
	for (int32 I = 0; I < 12; ++I) W.Step();
	TestTrue(TEXT("holding Y opens the wheel"), Rig.PC->GetSwitch().IsWheelOpen());
	const double WheelTurn = YawTurned(W, 10, [&]() { Rig.Axis(EKeys::Gamepad_RightX, 1.f); W.Step(); });
	TestEqual(TEXT("the stick turns nothing while the wheel is open"), WheelTurn, 0.0);
	TestEqual(TEXT("the stick to the right picks slot 2 of four"), Rig.PC->GetSwitch().GetSelection(), 1);
	Rig.Rest(EKeys::Gamepad_RightX);
	Rig.Hold(EKeys::Gamepad_RightY, StickUp, 3);
	TestEqual(TEXT("the stick up picks slot 1, at the top of the wheel"), Rig.PC->GetSwitch().GetSelection(), 0);
	Rig.Hold(EKeys::Gamepad_RightY, -StickUp, 3);
	TestEqual(TEXT("the stick down picks slot 3, at the bottom"), Rig.PC->GetSwitch().GetSelection(), 2);
	Rig.Rest(EKeys::Gamepad_RightY);
	Rig.Hold(EKeys::Gamepad_RightX, 1.f, 3);
	Rig.Key(EKeys::Gamepad_FaceButton_Top, IE_Released);
	W.Step();
	TestFalse(TEXT("releasing Y shuts the wheel"), Rig.PC->GetSwitch().IsWheelOpen());
	Rig.Rest(EKeys::Gamepad_RightX);
	for (int32 I = 0; I < 45; ++I) W.Step();
	TestEqual(TEXT("the pick is in hand"), W.Player->GetWeapon()->GetRules().GetCurrentIndex(), 1);

	// What the controls are called follows the device in use, and a controller's buttons the names chosen in Settings.
	TestEqual(TEXT("the grab key on the keyboard"), W.Game->ControlName(TEXT("interact"), false), FString(TEXT("E")));
	TestEqual(TEXT("the grab button on a controller"), W.Game->ControlName(TEXT("interact"), true), FString(TEXT("X")));
	TestEqual(TEXT("the melee button on a controller"), W.Game->ControlName(TEXT("melee"), true), FString(TEXT("RB")));
	TestEqual(TEXT("a control the data does not name"), W.Game->ControlName(TEXT("nothing"), true), FString());
	TestTrue(TEXT("the controller is the device in use"), Rig.PC->IsPadActive());
	W.Step();
	TestEqual(TEXT("the grab prompt names the controller's button"), W.Game->GetRules().InteractGlyph, FString(TEXT("X")));
	TestTrue(TEXT("PlayStation names chosen"), W.Game->GetSettings().SetPadPlayStation(true));
	TestEqual(TEXT("the grab button in PlayStation names"), W.Game->ControlName(TEXT("interact"), true), FString(TEXT("Square")));
	TestEqual(TEXT("melee in PlayStation names"), W.Game->ControlName(TEXT("melee"), true), FString(TEXT("R1")));
	TestEqual(TEXT("pause in PlayStation names"), W.Game->ControlName(TEXT("pause"), true), FString(TEXT("OPTIONS")));
	TestEqual(TEXT("the keyboard's names do not change"), W.Game->ControlName(TEXT("interact"), false), FString(TEXT("E")));
	W.Step();
	TestEqual(TEXT("the grab prompt in PlayStation names"), W.Game->GetRules().InteractGlyph, FString(TEXT("Square")));
	Rig.Key(EKeys::W, IE_Pressed);
	W.Step();
	Rig.Key(EKeys::W, IE_Released);
	W.Step();
	TestFalse(TEXT("a key: the keyboard is the device again"), Rig.PC->IsPadActive());
	TestEqual(TEXT("and the grab prompt says E"), W.Game->GetRules().InteractGlyph, FString(TEXT("E")));
	W.Game->GetSettings().SetPadPlayStation(false);
	return !HasAnyErrors();
}

// The cards take the mouse (version 3): a click acts on the row under it, the cursor selects, and the press that left
// a card does not carry into play (spec 01 3.16).
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIRunMenuMouseTest, "MurderInc.Run.MenuMouse", MITest::Flags)

bool FMIRunMenuMouseTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	if (!W.Boot(*this, TEXT("mission"), TEXT("boss")))
	{
		return false;
	}
	for (int32 I = 0; I < 30 * 4 && W.State() != EMIGameState::Playing; ++I) W.Step();
	if (!TestEqual(TEXT("playing"), (int32)W.State(), (int32)EMIGameState::Playing))
	{
		return false;
	}
	W.Player->GetPlayerRules().bInvulnerable = true;
	FMIMenu& M = W.Game->GetMenu();
	// What the HUD does each frame it draws a card: where the rows are (here 400 wide from x 100, 40 high, 10 apart).
	const auto Draw = [&M]()
	{
		FMIMenuLayout& L = M.Layout;
		L.Screen = M.Screen;
		L.X = 100.0;
		L.Width = 400.0;
		L.Top = 200.0;
		L.RowHeight = 40.0;
		L.RowGap = 10.0;
		L.Adjust.Reset();
		for (const FMIMenuItem& Item : M.Items) L.Adjust.Add(Item.bAdjust);
	};
	const auto At = [&M](FName Id, double Share) { return FVector2D(100.0 + 400.0 * Share, 200.0 + M.IndexOf(Id) * 50.0 + 20.0); };

	TestFalse(TEXT("no card in play: a click hits nothing"), W.Game->MenuClick(FVector2D(300.0, 220.0)));
	W.Game->PauseKey();
	TestEqual(TEXT("the pause card"), (int32)M.Screen, (int32)EMIMenuScreen::Pause);
	TestFalse(TEXT("the card is not drawn yet: a click hits nothing"), W.Game->MenuClick(FVector2D(300.0, 220.0)));
	Draw();
	// The cursor selects, and only selects.
	TestTrue(TEXT("the cursor over Restart"), W.Game->MenuHover(At(TEXT("restart"), 0.5)));
	TestEqual(TEXT("selects it"), M.Selected, M.IndexOf(TEXT("restart")));
	TestEqual(TEXT("and does nothing else"), (int32)W.State(), (int32)EMIGameState::Paused);
	TestFalse(TEXT("the cursor between two rows selects nothing"), W.Game->MenuHover(FVector2D(300.0, 245.0)));
	TestEqual(TEXT("the selection stays"), M.Selected, M.IndexOf(TEXT("restart")));
	TestFalse(TEXT("a click beside the card does nothing"), W.Game->MenuClick(FVector2D(50.0, 220.0)));
	TestEqual(TEXT("still paused"), (int32)W.State(), (int32)EMIGameState::Paused);
	// An adjustable row: the right half is the next value, the left half the one before.
	const FName Difficulty = W.Game->GetSettings().Difficulty;
	TestTrue(TEXT("a click on the right half of Difficulty"), W.Game->MenuClick(At(TEXT("difficulty"), 0.9)));
	const FName Harder = W.Game->GetSettings().Difficulty;
	TestNotEqual(TEXT("changes the difficulty"), Harder, Difficulty);
	Draw();
	TestTrue(TEXT("a click on its left half"), W.Game->MenuClick(At(TEXT("difficulty"), 0.1)));
	TestEqual(TEXT("goes back"), W.Game->GetSettings().Difficulty, Difficulty);
	// A button: Settings opens; the pause card's rows are no longer what a click hits.
	Draw();
	TestTrue(TEXT("a click on Settings"), W.Game->MenuClick(At(TEXT("settings"), 0.5)));
	TestEqual(TEXT("opens the settings card"), (int32)M.Screen, (int32)EMIMenuScreen::Settings);
	TestFalse(TEXT("before the settings card is drawn a click hits nothing"), W.Game->MenuClick(FVector2D(300.0, 220.0)));
	Draw();
	const double Sens = W.Game->GetSettings().Sens;
	TestTrue(TEXT("a click on the left half of Sensitivity"), W.Game->MenuClick(At(TEXT("sens"), 0.2)));
	TestTrue(TEXT("lowers it one step"), FMath::IsNearlyEqual(W.Game->GetSettings().Sens, Sens - 0.05, 1e-9));
	Draw();
	TestTrue(TEXT("a click on its right half"), W.Game->MenuClick(At(TEXT("sens"), 0.8)));
	TestTrue(TEXT("raises it again"), FMath::IsNearlyEqual(W.Game->GetSettings().Sens, Sens, 1e-9));
	Draw();
	// The names of a controller's buttons: the Xbox names unless the player chooses the PlayStation ones.
	TestFalse(TEXT("Xbox names at the start"), W.Game->GetSettings().bPadPlayStation);
	TestTrue(TEXT("a click on the Controller row"), W.Game->MenuClick(At(TEXT("padnames"), 0.8)));
	TestTrue(TEXT("chooses the PlayStation names"), W.Game->GetSettings().bPadPlayStation);
	Draw();
	TestTrue(TEXT("a second click"), W.Game->MenuClick(At(TEXT("padnames"), 0.2)));
	TestFalse(TEXT("goes back to the Xbox names"), W.Game->GetSettings().bPadPlayStation);
	Draw();
	TestTrue(TEXT("a click on Back"), W.Game->MenuClick(At(TEXT("back"), 0.5)));
	TestEqual(TEXT("returns to the pause card"), (int32)M.Screen, (int32)EMIMenuScreen::Pause);
	for (int32 I = 0; I < 12; ++I) W.Step();  // past the pause debounce
	Draw();
	TestTrue(TEXT("a click on Resume"), W.Game->MenuClick(At(TEXT("resume"), 0.5)));
	TestEqual(TEXT("resumes"), (int32)W.State(), (int32)EMIGameState::Playing);
	W.Step();

	// Nothing pressed on a card carries into play: Enter is confirm on a card and fire in play.
	FControllerRig Rig(W);
	if (!TestNotNull(TEXT("controller"), Rig.PC))
	{
		return false;
	}
	for (int32 I = 0; I < 30; ++I) W.Step();
	FMIPlayerInputState& In = W.Player->GetInput();
	Rig.Key(EKeys::P, IE_Pressed);
	W.Step();
	Rig.Key(EKeys::P, IE_Released);
	W.Step();
	TestEqual(TEXT("P pauses"), (int32)W.State(), (int32)EMIGameState::Paused);
	for (int32 I = 0; I < 12; ++I) W.Step();
	M.Selected = M.IndexOf(TEXT("resume"));
	Rig.Key(EKeys::Enter, IE_Pressed);
	W.Step();
	TestEqual(TEXT("Enter on Resume resumes"), (int32)W.State(), (int32)EMIGameState::Playing);
	bool bFired = In.bFire || In.bFirePressed;
	for (int32 I = 0; I < 10; ++I)
	{
		W.Step();
		bFired |= In.bFire || In.bFirePressed;
	}
	TestFalse(TEXT("the Enter that resumed does not fire while it is still down"), bFired);
	Rig.Key(EKeys::Enter, IE_Released);
	W.Step();
	W.Step();
	Rig.Key(EKeys::Enter, IE_Pressed);
	W.Step();
	TestTrue(TEXT("a fresh Enter in play fires"), In.bFire);
	Rig.Key(EKeys::Enter, IE_Released);
	W.Step();
	TestFalse(TEXT("and stops when released"), In.bFire);
	// Sprint is a hold that carries through a card (W, A, S, D, sprint and crouch do).
	Rig.Key(EKeys::LeftShift, IE_Pressed);
	W.Step();
	TestTrue(TEXT("Shift sprints"), In.bSprint);
	W.Game->PauseKey();
	for (int32 I = 0; I < 12; ++I) W.Step();
	M.Selected = M.IndexOf(TEXT("resume"));
	Rig.Key(EKeys::Enter, IE_Pressed);
	W.Step();
	Rig.Key(EKeys::Enter, IE_Released);
	W.Step();
	TestEqual(TEXT("resumed again"), (int32)W.State(), (int32)EMIGameState::Playing);
	TestTrue(TEXT("the Shift held through the card still sprints"), In.bSprint);
	Rig.Key(EKeys::LeftShift, IE_Released);
	W.Step();
	TestFalse(TEXT("until it is released"), In.bSprint);
	return !HasAnyErrors();
}

// The pad's X (Square) is one button with two meanings, as in the web game (src/input.js padDown): it reloads, unless a
// grab prompt is showing at the moment of the press: then that hold grabs, and reloads nothing. (Until version 3's
// review it did both at a reel: every grab under fire put the gun out of action for a reload.) R and E are what they
// were.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIPadReloadOrGrabTest, "MurderInc.Player.PadReloadOrGrab", MITest::Flags)

bool FMIPadReloadOrGrabTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	if (!W.Boot(*this, TEXT("mission"), TEXT("boss")))
	{
		return false;
	}
	for (int32 I = 0; I < 30 * 4 && W.State() != EMIGameState::Playing; ++I) W.Step();
	if (!TestEqual(TEXT("playing"), (int32)W.State(), (int32)EMIGameState::Playing))
	{
		return false;
	}
	FControllerRig Rig(W);
	if (!TestNotNull(TEXT("controller"), Rig.PC))
	{
		return false;
	}
	W.Player->GetPlayerRules().bInvulnerable = true;
	const FMIWeaponRules& Gun = W.Player->GetWeapon()->GetRules();
	int32 Reloads = 0;
	FDelegateHandle Handle;
	FMIGameEvents* Events = UMIEventSubsystem::Get(W.World);
	if (!TestNotNull(TEXT("events"), Events))
	{
		return false;
	}
	Handle = Events->WeaponReload.AddLambda([&Reloads](const FMIReloadEvent& E) { if (E.Phase == TEXT("start")) ++Reloads; });
	const auto Shoot = [&]()
	{
		Rig.Key(EKeys::LeftMouseButton, IE_Pressed);
		for (int32 I = 0; I < 8; ++I) W.Step();
		Rig.Key(EKeys::LeftMouseButton, IE_Released);
		for (int32 I = 0; I < 20; ++I) W.Step();
	};
	const auto Settle = [&]() { for (int32 I = 0; I < 30 * 4; ++I) W.Step(); };
	const int32 Full = Gun.GetMag();
	Shoot();
	TestTrue(FString::Printf(TEXT("a few rounds are gone (%d of %d left)"), Gun.GetMag(), Full), Gun.GetMag() < Full);

	// Away from every reel: X reloads and holds no grab.
	TestTrue(TEXT("no reel in reach: no prompt"), W.Game->GetRules().View().Prompt.IsEmpty());
	Rig.Key(EKeys::Gamepad_FaceButton_Left, IE_Pressed);
	W.Step();
	W.Step();
	TestEqual(TEXT("X away from a reel starts a reload"), Reloads, 1);
	TestFalse(TEXT("and holds no grab"), W.Game->IsInteractHeld());
	Rig.Key(EKeys::Gamepad_FaceButton_Left, IE_Released);
	Settle();
	TestEqual(TEXT("the magazine is full again"), Gun.GetMag(), Full);

	// At a reel, with rounds missing: X grabs, for that whole hold, and reloads nothing.
	Shoot();
	const int32 Left = Gun.GetMag();
	TestTrue(TEXT("rounds are missing again"), Left < Full);
	const FMILevelData* Level = W.Game->GetLevel();
	if (!TestTrue(TEXT("the level has a reel"), Level && Level->Objectives.Num() > 0))
	{
		Events->WeaponReload.Remove(Handle);
		return false;
	}
	StandAt(W, Level->Objectives[0].Pos + FVector(0.4, 0, 0));
	W.Step();
	W.Step();
	TestFalse(TEXT("at the reel the grab prompt shows"), W.Game->GetRules().View().Prompt.IsEmpty());
	Rig.Key(EKeys::Gamepad_FaceButton_Left, IE_Pressed);
	W.Step();
	W.Step();
	TestTrue(TEXT("X at a reel holds the grab"), W.Game->IsInteractHeld());
	TestEqual(TEXT("and starts no reload"), Reloads, 1);
	for (int32 I = 0; I < 30 * 3 && W.Game->GetRules().GetRun().Reels == 0; ++I)
	{
		StandAt(W, Level->Objectives[0].Pos + FVector(0.4, 0, 0));
		W.Step();
	}
	TestEqual(TEXT("held, X takes the reel"), W.Game->GetRules().GetRun().Reels, 1);
	TestEqual(TEXT("no reload during the whole hold (the prompt is gone once the reel is taken)"), Reloads, 1);
	TestEqual(TEXT("the magazine is as it was"), Gun.GetMag(), Left);
	Rig.Key(EKeys::Gamepad_FaceButton_Left, IE_Released);
	W.Step();
	W.Step();
	TestFalse(TEXT("letting X go lets the grab go"), W.Game->IsInteractHeld());

	// The keyboard is what it was: R reloads, E grabs.
	Rig.Key(EKeys::R, IE_Pressed);
	W.Step();
	W.Step();
	Rig.Key(EKeys::R, IE_Released);
	TestEqual(TEXT("R reloads"), Reloads, 2);
	Rig.Key(EKeys::E, IE_Pressed);
	W.Step();
	W.Step();
	TestTrue(TEXT("E holds the grab"), W.Game->IsInteractHeld());
	TestEqual(TEXT("and reloads nothing"), Reloads, 2);
	Rig.Key(EKeys::E, IE_Released);
	W.Step();
	W.Step();
	TestFalse(TEXT("until it is let go"), W.Game->IsInteractHeld());
	Events->WeaponReload.Remove(Handle);
	return !HasAnyErrors();
}

// A stream's last viewer leaves (UMICloudSubsystem::ReleaseForLeave, version 3's review). The run pauses, in its intro
// too (it paused only in play: a viewer lost in the 2.4 s of the intro left a live run behind). And everything the
// viewer held is let go: no release arrives from a viewer who is gone, and a key or trigger that still read as down
// walked, turned or fired for the next viewer (a trigger's axis held the fire for good: neither the trigger nor the
// mouse fired again). A key pressed afterwards counts at once.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudViewerLeavesTest, "MurderInc.Cloud.ViewerLeaves", MITest::Flags)

bool FMICloudViewerLeavesTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	if (!W.Boot(*this, TEXT("mission"), TEXT("boss")))
	{
		return false;
	}
	W.Step();
	// In the intro.
	TestEqual(TEXT("the run begins with its intro"), (int32)W.State(), (int32)EMIGameState::Intro);
	UMICloudSubsystem::ReleaseForLeave(W.Game, nullptr);
	TestEqual(TEXT("the last viewer leaves in the intro: paused"), (int32)W.State(), (int32)EMIGameState::Paused);
	for (int32 I = 0; I < 30 * 4; ++I) W.Step();
	TestEqual(TEXT("and it stays paused: no run goes live with nobody watching"), (int32)W.State(), (int32)EMIGameState::Paused);
	UMICloudSubsystem::ReleaseForLeave(W.Game, nullptr);
	TestEqual(TEXT("leaving again changes nothing"), (int32)W.State(), (int32)EMIGameState::Paused);
	UMICloudSubsystem::ReleaseForLeave(nullptr, nullptr);  // no game yet (the stream can lose its viewer before the map is up)
	W.Game->Resume();
	W.Step();
	TestEqual(TEXT("resumed: playing"), (int32)W.State(), (int32)EMIGameState::Playing);

	FControllerRig Rig(W);
	if (!TestNotNull(TEXT("controller"), Rig.PC))
	{
		return false;
	}
	FMIPlayerInputState& In = W.Player->GetInput();
	W.Player->GetPlayerRules().bInvulnerable = true;
	for (int32 I = 0; I < 10; ++I) W.Step();

	// The viewer holds W and Shift, pushes the left stick and pulls the right trigger; then the connection is cut.
	Rig.Key(EKeys::W, IE_Pressed);
	Rig.Key(EKeys::LeftShift, IE_Pressed);
	W.Step();
	TestTrue(TEXT("W walks forward"), In.Move.Y > 0.5);
	TestTrue(TEXT("Shift sprints"), In.bSprint);
	Rig.Hold(EKeys::Gamepad_LeftX, 1.f, 2);
	TestTrue(TEXT("the left stick moves to the right"), In.Move.X > 0.5);
	Rig.Hold(EKeys::Gamepad_RightTriggerAxis, 1.f, 2);
	TestTrue(TEXT("the right trigger fires"), In.bFire);
	Rig.Key(EKeys::E, IE_Pressed);
	W.Step();
	TestTrue(TEXT("E holds the grab"), W.Game->IsInteractHeld());

	UMICloudSubsystem::ReleaseForLeave(W.Game, Rig.PC);
	TestEqual(TEXT("the last viewer leaves in play: paused"), (int32)W.State(), (int32)EMIGameState::Paused);
	TestTrue(TEXT("at once: no move"), In.Move.IsZero());
	TestFalse(TEXT("at once: no fire"), In.bFire);
	TestFalse(TEXT("at once: no sprint"), In.bSprint);
	TestFalse(TEXT("at once: no grab"), W.Game->IsInteractHeld());
	for (int32 I = 0; I < 30; ++I) W.Step();

	// The next viewer resumes without touching anything: nothing moves, nothing fires.
	W.Game->Resume();
	bool bMoved = false, bFired = false, bSprinted = false;
	for (int32 I = 0; I < 30; ++I)
	{
		W.Step();
		bMoved |= !In.Move.IsZero();
		bFired |= In.bFire || In.bFirePressed;
		bSprinted |= In.bSprint;
	}
	TestEqual(TEXT("resumed"), (int32)W.State(), (int32)EMIGameState::Playing);
	TestFalse(TEXT("the W that was held when the viewer left does not walk for the next viewer"), bMoved);
	TestFalse(TEXT("the trigger that was pulled does not fire"), bFired);
	TestFalse(TEXT("the Shift that was held does not sprint"), bSprinted);
	TestFalse(TEXT("the E that was held does not grab"), W.Game->IsInteractHeld());

	// What the next viewer presses counts at once (the releases of the old holds never came).
	Rig.Key(EKeys::W, IE_Pressed);
	W.Step();
	W.Step();
	TestTrue(TEXT("a fresh W walks"), In.Move.Y > 0.5);
	Rig.Key(EKeys::W, IE_Released);
	W.Step();
	W.Step();
	TestTrue(TEXT("and stops when let go"), In.Move.IsZero());
	Rig.Key(EKeys::LeftMouseButton, IE_Pressed);
	W.Step();
	W.Step();
	TestTrue(TEXT("the left mouse button fires again (the old trigger pull no longer holds the fire)"), In.bFire);
	Rig.Key(EKeys::LeftMouseButton, IE_Released);
	W.Step();
	W.Step();
	TestFalse(TEXT("and stops"), In.bFire);
	Rig.Hold(EKeys::Gamepad_RightTriggerAxis, 1.f, 3);
	TestTrue(TEXT("a fresh pull of the trigger fires"), In.bFire);
	Rig.Rest(EKeys::Gamepad_RightTriggerAxis);
	TestFalse(TEXT("and stops"), In.bFire);
	Rig.Key(EKeys::LeftShift, IE_Pressed);
	W.Step();
	W.Step();
	TestTrue(TEXT("a fresh Shift sprints"), In.bSprint);
	Rig.Key(EKeys::LeftShift, IE_Released);
	W.Step();
	W.Step();
	TestFalse(TEXT("and stops"), In.bSprint);
	return !HasAnyErrors();
}

// SMOOTH.md B4: a run can be left for the menus from the pause card. Change set-up and Back to title follow the card's
// own rows (Resume, Restart run, Difficulty, Settings), stay after a visit to Settings, and do what the death card's
// rows do: Back to title opens Home, Change set-up opens the Briefing; a new run from there plays.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIRunPauseCardLeaveTest, "MurderInc.Run.PauseCardLeave", MITest::Flags)

bool FMIRunPauseCardLeaveTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	FRunWorld W;
	UMIFrontEnd* F = StartWith(*this, W, [](FMIRunSetup&) {});
	if (!F)
	{
		return false;
	}
	FMIMenu& M = W.Game->GetMenu();
	const auto CheckRows = [this, &M](const TCHAR* When)
	{
		const int32 Settings = M.IndexOf(TEXT("settings"));
		const int32 Change = M.IndexOf(TEXT("changesetup"));
		const int32 Title = M.IndexOf(TEXT("totitle"));
		TestTrue(FString::Printf(TEXT("%s: the card's own rows first"), When), M.IndexOf(TEXT("resume")) == 0 && M.IndexOf(TEXT("restart")) == 1 && Settings == 3);
		TestTrue(FString::Printf(TEXT("%s: Change set-up after Settings"), When), Change == Settings + 1);
		TestTrue(FString::Printf(TEXT("%s: Back to title last"), When), Title == Change + 1 && Title == M.Items.Num() - 1);
		TestTrue(FString::Printf(TEXT("%s: both have their words"), When), Change != INDEX_NONE && Title != INDEX_NONE && !M.Items[Change].Label.IsEmpty() && !M.Items[Title].Label.IsEmpty());
	};
	// Pause: the two rows are there, once, and again after Settings and Back.
	W.Game->PauseKey();
	if (!TestEqual(TEXT("the pause card"), (int32)M.Screen, (int32)EMIMenuScreen::Pause))
	{
		return false;
	}
	CheckRows(TEXT("on pausing"));
	M.Selected = M.IndexOf(TEXT("settings"));
	W.Game->MenuConfirm();
	TestEqual(TEXT("Settings from the pause card"), (int32)M.Screen, (int32)EMIMenuScreen::Settings);
	W.Game->MenuBack();
	TestEqual(TEXT("back on the pause card"), (int32)M.Screen, (int32)EMIMenuScreen::Pause);
	CheckRows(TEXT("after Settings"));
	M.Selected = M.IndexOf(TEXT("difficulty"));
	W.Game->MenuAdjust(1);
	W.Game->MenuAdjust(-1);
	CheckRows(TEXT("after a difficulty change"));
	// Back to title: the run ends, Home is up.
	M.Selected = M.IndexOf(TEXT("totitle"));
	W.Game->MenuConfirm();
	TestEqual(TEXT("Back to title: the title"), (int32)W.State(), (int32)EMIGameState::Title);
	TestTrue(TEXT("the front end is up"), F->IsShown());
	TestEqual(TEXT("... on Home"), F->GetRules().GetScreen(), EMIFrontScreen::Home);
	TestEqual(TEXT("no game card over it"), (int32)M.Screen, (int32)EMIMenuScreen::Title);
	// A new run, paused, Change set-up: the Briefing.
	F->Act(TEXT("hit"));
	for (int32 I = 0; I < 30 * 4 && W.State() != EMIGameState::Playing; ++I) W.Step();
	TestEqual(TEXT("a new run plays"), (int32)W.State(), (int32)EMIGameState::Playing);
	for (int32 I = 0; I < 12; ++I) W.Step();
	W.Game->PauseKey();
	CheckRows(TEXT("the second run"));
	M.Selected = M.IndexOf(TEXT("changesetup"));
	W.Game->MenuConfirm();
	TestEqual(TEXT("Change set-up: the title"), (int32)W.State(), (int32)EMIGameState::Title);
	TestEqual(TEXT("... on the Briefing"), F->GetRules().GetScreen(), EMIFrontScreen::Briefing);
	TestTrue(TEXT("the front end is up"), F->IsShown());
	return !HasAnyErrors();
}

// SMOOTH.md B5: a viewer who stops looking (the pointer left the picture, or the page's away word) pauses a run in play
// or in its intro and lets go of what was held; on a menu, a card or a run already paused it changes nothing. And the
// page's word is read from a UIInteraction message exactly as Pixel Streaming hands it over.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudViewerAwayTest, "MurderInc.Cloud.ViewerAway", MITest::Flags)

bool FMICloudViewerAwayTest::RunTest(const FString& Parameters)
{
	using namespace MIRunTestsPrivate;
	// The message: a 16-bit count of UTF-16 code units, then the units, little-endian (RTCInputHandler.cpp).
	const auto Message = [](const FString& Text, int32 Cut = 0)
	{
		TArray<uint8> B;
		const int32 N = Text.Len();
		B.Add((uint8)(N & 0xff));
		B.Add((uint8)((N >> 8) & 0xff));
		for (int32 I = 0; I < N; ++I)
		{
			const uint32 C = (uint32)Text[I];
			B.Add((uint8)(C & 0xff));
			B.Add((uint8)((C >> 8) & 0xff));
		}
		B.SetNum(FMath::Max(0, B.Num() - Cut));
		return B;
	};
	TestTrue(TEXT("{\"murderinc\":\"away\"} is the away word"), UMICloudSubsystem::IsAwayMessage(Message(TEXT("{\"murderinc\":\"away\"}"))));
	TestTrue(TEXT("with spaces and other fields too"), UMICloudSubsystem::IsAwayMessage(Message(TEXT("{ \"from\": \"page\", \"murderinc\": \"AWAY\" }"))));
	TestFalse(TEXT("another word is not"), UMICloudSubsystem::IsAwayMessage(Message(TEXT("{\"murderinc\":\"back\"}"))));
	TestFalse(TEXT("another key is not"), UMICloudSubsystem::IsAwayMessage(Message(TEXT("{\"game\":\"away\"}"))));
	TestFalse(TEXT("a plain string is not"), UMICloudSubsystem::IsAwayMessage(Message(TEXT("murderinc away"))));
	TestFalse(TEXT("a message cut short is not"), UMICloudSubsystem::IsAwayMessage(Message(TEXT("{\"murderinc\":\"away\"}"), 3)));
	TestFalse(TEXT("an empty message is not"), UMICloudSubsystem::IsAwayMessage(TArray<uint8>()));
	TestFalse(TEXT("nor a count with nothing after it"), UMICloudSubsystem::IsAwayMessage(Message(FString())));

	FRunWorld W;
	if (!W.Boot(*this, TEXT("mission"), TEXT("boss")))
	{
		return false;
	}
	W.Step();
	TestEqual(TEXT("the run begins with its intro"), (int32)W.State(), (int32)EMIGameState::Intro);
	TestTrue(TEXT("away in the intro: it pauses"), UMICloudSubsystem::PauseForAway(W.Game, nullptr));
	TestEqual(TEXT("paused"), (int32)W.State(), (int32)EMIGameState::Paused);
	for (int32 I = 0; I < 30 * 4; ++I) W.Step();
	TestEqual(TEXT("and stays paused: the intro does not end into a live run"), (int32)W.State(), (int32)EMIGameState::Paused);
	TestFalse(TEXT("away again on the pause card: nothing to do"), UMICloudSubsystem::PauseForAway(W.Game, nullptr));
	TestEqual(TEXT("still the pause card"), (int32)W.Game->GetMenu().Screen, (int32)EMIMenuScreen::Pause);
	TestFalse(TEXT("no game: nothing to do"), UMICloudSubsystem::PauseForAway(nullptr, nullptr));
	W.Game->Resume();
	W.Step();
	TestEqual(TEXT("resumed"), (int32)W.State(), (int32)EMIGameState::Playing);

	FControllerRig Rig(W);
	if (!TestNotNull(TEXT("controller"), Rig.PC))
	{
		return false;
	}
	FMIPlayerInputState& In = W.Player->GetInput();
	W.Player->GetPlayerRules().bInvulnerable = true;
	for (int32 I = 0; I < 10; ++I) W.Step();
	Rig.Key(EKeys::W, IE_Pressed);
	Rig.Key(EKeys::LeftMouseButton, IE_Pressed);
	W.Step();
	W.Step();
	TestTrue(TEXT("W walks"), In.Move.Y > 0.5);
	TestTrue(TEXT("the mouse button fires"), In.bFire);
	TestTrue(TEXT("away in play: it pauses"), UMICloudSubsystem::PauseForAway(W.Game, Rig.PC));
	TestEqual(TEXT("paused"), (int32)W.State(), (int32)EMIGameState::Paused);
	TestTrue(TEXT("at once: no move"), In.Move.IsZero());
	TestFalse(TEXT("at once: no fire"), In.bFire);
	for (int32 I = 0; I < 30; ++I) W.Step();
	// The player comes back and resumes without touching anything: the W and the button held when they left do nothing.
	W.Game->Resume();
	bool bMoved = false, bFired = false;
	for (int32 I = 0; I < 30; ++I)
	{
		W.Step();
		bMoved |= !In.Move.IsZero();
		bFired |= In.bFire || In.bFirePressed;
	}
	TestEqual(TEXT("resumed"), (int32)W.State(), (int32)EMIGameState::Playing);
	TestFalse(TEXT("the W held when the player went away does not walk"), bMoved);
	TestFalse(TEXT("the button held does not fire"), bFired);
	// On the title nothing changes.
	W.Game->ToTitle();
	W.Step();
	TestFalse(TEXT("away on the title: nothing to do"), UMICloudSubsystem::PauseForAway(W.Game, Rig.PC));
	TestEqual(TEXT("still the title"), (int32)W.State(), (int32)EMIGameState::Title);
	return !HasAnyErrors();
}

#endif
