// Whole runs in a world with collision (no window, no GPU): the game subsystem boots the block from level.json, the
// player character plays it with his real weapon, the enemies fight back through their actors' hit volumes and the
// engine's traces, the flow decides.
//   MurderInc.Run.StoryComplete  a bot follows the objective data: fights, takes the three reels, reaches the truck
//   MurderInc.Run.StoryDeath     a bot that does not fight dies; the death card; Run it back starts the run again
//   MurderInc.Run.HoldTheBlock   a bot holds the start through three waves; scores, resupply, the card and the best
//   MurderInc.Run.Menus          title, settings validation, pause and resume through the menu model

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
			// A bare world's persistent level is not marked visible: the tick task manager skips invisible levels.
			World->PersistentLevel->bIsVisible = true;
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
	// The web game's validation (spec 04 2.16, verified there): fov 200 -> 95, 74.6 -> 75, sens 0.01 -> 0.2, volume 2 -> 1, quality 'test' rejected.
	FMISettings S;
	FString Error;
	if (!TestTrue(TEXT("settings defaults load: ") + Error, FMISettings::LoadDefaults(S, Error)))
	{
		return false;
	}
	TestEqual(TEXT("default mode"), S.Mode, FName(TEXT("mission")));
	TestEqual(TEXT("default fov"), S.Fov, 74.0);
	S.SetFov(200);
	TestEqual(TEXT("fov 200 -> 95"), S.Fov, 95.0);
	S.SetFov(74.6);
	TestEqual(TEXT("fov 74.6 -> 75"), S.Fov, 75.0);
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
	TestEqual(TEXT("field of view one degree up"), W.Game->GetSettings().Fov, 75.0);
	W.Game->MenuBack();
	TestEqual(TEXT("back to the pause card"), (int32)M.Screen, (int32)EMIMenuScreen::Pause);
	M.Selected = M.IndexOf(TEXT("resume"));
	W.Game->MenuConfirm();
	TestEqual(TEXT("resumed"), (int32)W.State(), (int32)EMIGameState::Playing);
	TestEqual(TEXT("no menu in play"), (int32)M.Screen, (int32)EMIMenuScreen::None);
	return true;
}

#endif
