// Story guidance (docs/unreal/PLAY.md, guide lane).
//   MurderInc.Guide.Data       guide.json loads: a hint line for every step of the level, the ways down stand on the grid
//   MurderInc.Guide.Routes     every step of the story from the start and from the step before: a route on the grid the
//                              Goons use, through no wall, inside the block, ending where the grab or the truck answers;
//                              the chevrons on the floor; the upper floors go down their stair first
//   MurderInc.Guide.Hint       the hint after 45 s of play without progress (combat does not count), gone on progress
//   MurderInc.Guide.Stable     chevrons stay put while the player walks the route; no flip between equal routes
//   MurderInc.Guide.Combat     the guide sees a fight from the enemy field's slots (its list holds slot indexes, not the
//                              units' ids): one engaging Goon dims the path, none brings it back
//   MurderInc.Guide.EndToEnd   the whole story walked with the real movement on the block's collision, by a bot that only
//                              follows the drawn route: Reel 1, Reel 2, Reel 3, the truck; the guide's cost per frame

#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Components/StaticMeshComponent.h"
#include "Flow/MIGameSubsystem.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/WorldSettings.h"
#include "Player/MIPlayerCharacter.h"
#include "Tests/MITestUtil.h"
#include "World/MIGuide.h"
#include "World/MILevelData.h"

#if WITH_AUTOMATION_TESTS

namespace MIGuideTestsPrivate
{
	double Flat(const FVector& A, const FVector& B) { return MI::Web::Hypot(A.X - B.X, A.Z - B.Z); }

	struct FBlock
	{
		const FMILevelData* Level = nullptr;
		FMIBoxWorld Nav;
		FMIGuideTune Tune;

		bool Init(FAutomationTestBase& T)
		{
			Level = FMILevelData::Get();
			if (!T.TestNotNull(TEXT("level.json loads"), Level))
			{
				return false;
			}
			Level->FillWorld(Nav, FMIRng(1994));
			FString Error;
			return T.TestTrue(TEXT("guide.json loads: ") + Error, FMIGuideTune::Load(Tune, Error));
		}

		/** The plan run on the box world from Feet with these reels taken until it has a route (a few frames). */
		void Route(FMIGuidePlan& Plan, const FVector& Feet, const TArray<bool>& Secured)
		{
			FMIGuideInput In;
			In.bStory = true;
			In.bClock = true;
			In.Feet = Feet;
			In.Secured = Secured;
			for (int32 I = 0; I < 30 && !Plan.HasRoute(); ++I)
			{
				Plan.Update(1.0 / 30.0, In, Nav);
			}
			Plan.Update(1.0 / 30.0, In, Nav);
		}

		FVector GoalOf(int32 Step) const
		{
			return Step == FMIGuidePlan::ExtractionStep ? Level->Extraction.Pos : Level->Objectives[Step].Pos;
		}
	};

	/** Secured flags for "the first N objectives taken". */
	TArray<bool> Taken(int32 Num, int32 Count)
	{
		TArray<bool> S;
		S.Init(false, Num);
		for (int32 I = 0; I < FMath::Min(Count, Num); ++I)
		{
			S[I] = true;
		}
		return S;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGuideDataTest, "MurderInc.Guide.Data", MITest::Flags)

bool FMIGuideDataTest::RunTest(const FString& Parameters)
{
	using namespace MIGuideTestsPrivate;
	FBlock B;
	if (!B.Init(*this))
	{
		return false;
	}
	for (const FMILevelObjective& O : B.Level->Objectives)
	{
		const FString* H = B.Tune.Hints.Find(O.Id);
		TestTrue(FString::Printf(TEXT("a hint line for %s"), *O.Id.ToString()), H && !H->IsEmpty() && H->Len() <= 90);
	}
	const FString* X = B.Tune.Hints.Find(TEXT("extraction"));
	TestTrue(TEXT("a hint line for the truck"), X && !X->IsEmpty() && X->Len() <= 90);
	TestEqual(TEXT("the pool is a multiple of the light's phases"), B.Tune.MaxChevrons % B.Tune.Phases, 0);
	TestTrue(TEXT("the pool holds every slot the reach shows"), B.Tune.MaxChevrons >= FMath::CeilToInt32(B.Tune.Reach / B.Tune.Spacing) + 2);
	TestTrue(TEXT("the hint waits about 45 s"), B.Tune.HintAfter >= 30.0 && B.Tune.HintAfter <= 60.0);
	TestTrue(TEXT("at least one way down"), B.Tune.WaysDown.Num() > 0);
	for (const FMIGuideTune::FWayDown& W : B.Tune.WaysDown)
	{
		FVector Free;
		TestTrue(FString::Printf(TEXT("%s: its foot is on the grid (within 0.6 m)"), *W.Name), B.Nav.NearestWalkable(W.Foot.X, W.Foot.Z, 0.6, Free));
		const double Floor = B.Nav.GroundHeight(W.Top.X, W.Top.Z, W.Top.Y + 0.2);
		TestTrue(FString::Printf(TEXT("%s: its top stands on a floor at its height (%.2f, floor %.2f)"), *W.Name, W.Top.Y, Floor), FMath::Abs(Floor - W.Top.Y) < 0.25);
		TestTrue(FString::Printf(TEXT("%s: its top is an upper floor"), *W.Name), W.Top.Y - B.Nav.GroundHeight(W.Top.X, W.Top.Z, B.Tune.StepUp) > B.Tune.Elevated);
	}
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGuideRoutesTest, "MurderInc.Guide.Routes", MITest::Flags)

bool FMIGuideRoutesTest::RunTest(const FString& Parameters)
{
	using namespace MIGuideTestsPrivate;
	FBlock B;
	if (!B.Init(*this))
	{
		return false;
	}
	const int32 N = B.Level->Objectives.Num();
	TestEqual(TEXT("three reels"), N, 3);
	const FMIBounds& Bounds = B.Nav.GetBounds();
	double Total = 0.0;
	// Each step from the start of the run and from the step before it (where the player stands after the grab).
	for (int32 Step = 0; Step <= N; ++Step)
	{
		const int32 Want = Step < N ? Step : FMIGuidePlan::ExtractionStep;
		const FVector Goal = B.GoalOf(Want);
		TArray<FVector> Froms = {B.Level->PlayerStart.Pos};
		if (Step > 0)
		{
			Froms.Add(B.Level->Objectives[Step - 1].Pos + FVector(0.8, 0.0, 0.0));
		}
		for (int32 F = 0; F < Froms.Num(); ++F)
		{
			const FString What = FString::Printf(TEXT("step %d from %s"), Step, F == 0 ? TEXT("the start") : TEXT("the step before"));
			FMIGuidePlan Plan;
			Plan.Init(B.Tune, B.Level);
			B.Route(Plan, Froms[F], Taken(N, Step));
			if (!TestTrue(What + TEXT(": a route"), Plan.HasRoute()))
			{
				continue;
			}
			TestEqual(What + TEXT(": the step"), Plan.GetStep(), Want);
			const TArray<FVector>& P = Plan.GetPath();
			double Len = 0.0;
			for (int32 I = 0; I < P.Num(); ++I)
			{
				TestTrue(What + FString::Printf(TEXT(": point %d inside the block"), I), P[I].X > Bounds.MinX && P[I].X < Bounds.MaxX && P[I].Z > Bounds.MinZ && P[I].Z < Bounds.MaxZ);
				TestTrue(What + FString::Printf(TEXT(": point %d on the ground floor (%.2f m)"), I, P[I].Y), P[I].Y >= -0.01 && P[I].Y <= B.Tune.StepUp + 0.01);
				if (I > 0)
				{
					Len += FVector::Dist(P[I - 1], P[I]);
					TestTrue(What + FString::Printf(TEXT(": leg %d through no wall (%.1f, %.1f) to (%.1f, %.1f)"), I, P[I - 1].X, P[I - 1].Z, P[I].X, P[I].Z), B.Nav.ClearLine(P[I - 1], P[I]));
				}
			}
			const double Straight = Flat(Froms[F], Goal);
			TestTrue(What + FString::Printf(TEXT(": no long way round (%.1f m for %.1f m straight)"), Len, Straight), Len < Straight * 1.8 + 6.0);
			if (Step == 0 && F == 0)
			{
				// the avenue's sidewalk between the white van (z 5.0 to 6.9) and the DANGER STEAM hoarding (z 8.6 to 11.0) is a
				// 1.7 m gap of grid and less in the engine (the art is wider than the colliders): a player led into it stopped
				// there (PLAY.md, v6 independent play, finding 1). No leg of the route may run through it.
				for (int32 I = 1; I < P.Num(); ++I)
				{
					for (int32 K = 0; K <= 10; ++K)
					{
						const FVector Q = FMath::Lerp(P[I - 1], P[I], K / 10.0);
						TestFalse(What + FString::Printf(TEXT(": leg %d stays out of the van gap (%.1f, %.1f)"), I, Q.X, Q.Z), Q.X > -21.0 && Q.X < -14.0 && Q.Z > 7.2 && Q.Z < 8.4);
					}
				}
			}
			const double Reach = Want == FMIGuidePlan::ExtractionStep ? B.Level->ExtractionRadius : 2.2;
			TestTrue(What + FString::Printf(TEXT(": ends where the game answers (%.2f m from the goal)"), Flat(P.Last(), Goal)), Flat(P.Last(), Goal) < Reach - 0.2);
			// The chevrons: on the floor under them, pointing along the route, never more than the pool.
			const TArray<FMIGuideChevron>& C = Plan.GetChevrons();
			TestTrue(What + TEXT(": chevrons drawn"), C.Num() > 3);
			TestTrue(What + TEXT(": no more chevrons than the pool"), C.Num() < B.Tune.MaxChevrons);
			for (const FMIGuideChevron& V : C)
			{
				const double Floor = B.Nav.GroundHeight(V.Tip.X, V.Tip.Z, B.Tune.StepUp);
				TestTrue(What + FString::Printf(TEXT(": chevron %d on the floor"), V.Slot), FMath::Abs(V.Tip.Y - Floor) < 0.02);
				TestTrue(What + FString::Printf(TEXT(": chevron %d on walkable ground"), V.Slot), B.Nav.IsWalkable(V.Tip.X, V.Tip.Z));
				TestTrue(What + FString::Printf(TEXT(": chevron %d within the reach"), V.Slot), Flat(V.Tip, Froms[F]) < B.Tune.Reach + 1.0);
			}
			if (F == (Step > 0 ? 1 : 0))
			{
				Total += Len;
				AddInfo(FString::Printf(TEXT("%s: %.1f m of route (%.1f m straight), %d points, %d chevrons, %d under a roof"), *What, Len, Straight, P.Num(), C.Num(),
					C.FilterByPredicate([](const FMIGuideChevron& V) { return V.bShade; }).Num()));
			}
		}
	}
	AddInfo(FString::Printf(TEXT("the story's route: %.1f m"), Total));
	TestTrue(TEXT("the whole route is about 195 m"), Total > 150.0 && Total < 260.0);

	// An upper floor: down its own stair first, never through the parapet to the street under it.
	for (const FMIGuideTune::FWayDown& W : B.Tune.WaysDown)
	{
		FMIGuidePlan Plan;
		Plan.Init(B.Tune, B.Level);
		B.Route(Plan, W.Top, Taken(N, 0));
		if (!TestTrue(W.Name + TEXT(": a route"), Plan.HasRoute()))
		{
			continue;
		}
		const TArray<FVector>& P = Plan.GetPath();
		TestTrue(W.Name + TEXT(": by its stair"), P.Num() >= 3 && Flat(P[1], W.Top) < 0.01 && Flat(P[2], W.Foot) < 0.01);
		TestTrue(W.Name + TEXT(": the first chevrons on the upper floor or the stair"), Plan.GetChevrons().Num() > 0);
	}
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGuideHintTest, "MurderInc.Guide.Hint", MITest::Flags)

bool FMIGuideHintTest::RunTest(const FString& Parameters)
{
	using namespace MIGuideTestsPrivate;
	FBlock B;
	if (!B.Init(*this))
	{
		return false;
	}
	const int32 N = B.Level->Objectives.Num();
	FMIGuidePlan Plan;
	Plan.Init(B.Tune, B.Level);
	FMIGuideInput In;
	In.bStory = true;
	In.bClock = false;  // the intro: the clock does not run
	In.Feet = B.Level->PlayerStart.Pos;
	In.Secured = Taken(N, 0);
	const double Dt = 1.0 / 30.0;
	for (int32 I = 0; I < 30 * 60; ++I)
	{
		Plan.Update(Dt, In, B.Nav);
	}
	TestFalse(TEXT("no hint during the intro"), Plan.ShowsHint());
	In.bClock = true;
	In.bCombat = true;
	for (int32 I = 0; I < 30 * 60; ++I)
	{
		Plan.Update(Dt, In, B.Nav);
	}
	TestFalse(TEXT("a minute of fighting on the spot is not 'lost'"), Plan.ShowsHint());
	In.bCombat = false;
	for (int32 I = 0; I < 30 * 44; ++I)
	{
		Plan.Update(Dt, In, B.Nav);
	}
	TestFalse(TEXT("no hint at 44 s"), Plan.ShowsHint());
	for (int32 I = 0; I < 30 * 2; ++I)
	{
		Plan.Update(Dt, In, B.Nav);
	}
	TestTrue(TEXT("the hint at 46 s without progress"), Plan.ShowsHint());
	TestEqual(TEXT("Reel 1's line"), Plan.GetHint(), *B.Tune.Hints.Find(TEXT("reel1")));
	// Five metres along the route: progress.
	const TArray<FVector> Path = Plan.GetPath();
	FVector At = Path[0];
	double Left = 5.0;
	for (int32 I = 1; I < Path.Num() && Left > 0.0; ++I)
	{
		const double L = FVector::Dist(Path[I - 1], Path[I]);
		At = FMath::Lerp(Path[I - 1], Path[I], FMath::Min(1.0, Left / FMath::Max(L, 1e-6)));
		Left -= L;
	}
	In.Feet = At;
	Plan.Update(Dt, In, B.Nav);
	TestFalse(TEXT("gone once the player moves on along the route"), Plan.ShowsHint());
	TestEqual(TEXT("the clock starts again"), Plan.GetNoProgress(), 0.0);
	// Back at the start: further than the best so far, no progress.
	In.Feet = B.Level->PlayerStart.Pos;
	for (int32 I = 0; I < 30 * 46; ++I)
	{
		Plan.Update(Dt, In, B.Nav);
	}
	TestTrue(TEXT("walking back to the start brings the hint back"), Plan.ShowsHint());
	// The next step: the clock and the line start again.
	In.Secured = Taken(N, 1);
	Plan.Update(Dt, In, B.Nav);
	TestFalse(TEXT("a new step: no hint"), Plan.ShowsHint());
	TestEqual(TEXT("a new step: Reel 2"), Plan.GetStep(), 1);
	TestEqual(TEXT("Reel 2's line"), Plan.GetHint(), *B.Tune.Hints.Find(TEXT("reel2")));
	In.Secured = Taken(N, N);
	Plan.Update(Dt, In, B.Nav);
	TestEqual(TEXT("all reels: the truck"), Plan.GetStep(), FMIGuidePlan::ExtractionStep);
	In.bStory = false;
	Plan.Update(Dt, In, B.Nav);
	TestFalse(TEXT("no story (Hold the Block, the title, a card): nothing"), Plan.IsActive());
	TestEqual(TEXT("and no chevrons"), Plan.GetChevrons().Num(), 0);
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGuideStableTest, "MurderInc.Guide.Stable", MITest::Flags)

bool FMIGuideStableTest::RunTest(const FString& Parameters)
{
	using namespace MIGuideTestsPrivate;
	FBlock B;
	if (!B.Init(*this))
	{
		return false;
	}
	const int32 N = B.Level->Objectives.Num();
	FMIGuidePlan Plan;
	Plan.Init(B.Tune, B.Level);
	FMIGuideInput In;
	In.bStory = true;
	In.bClock = true;
	In.Secured = Taken(N, 2);  // the long leg: Reel 2 to the cage
	In.Feet = B.Level->Objectives[1].Pos + FVector(0.8, 0.0, 0.0);
	B.Route(Plan, In.Feet, In.Secured);
	const TArray<FVector> Route = Plan.GetPath();
	if (!TestTrue(TEXT("a route"), Route.Num() >= 2))
	{
		return false;
	}
	TMap<int32, FVector> Seen;
	for (const FMIGuideChevron& V : Plan.GetChevrons())
	{
		Seen.Add(V.Slot, V.Tip);
	}
	// Walk the route at 6 m/s for 6 s: the chevrons that stay in view stay where they were; the route is not replaced.
	const double Dt = 1.0 / 30.0;
	double S = 0.0;
	int32 Moved = 0, Kept = 0;
	const int32 Searches = Plan.GetSearches();
	for (int32 F = 0; F < 180; ++F)
	{
		S += 6.0 * Dt;
		double Left = S;
		FVector At = Route[0];
		for (int32 I = 1; I < Route.Num(); ++I)
		{
			const double L = FVector::Dist(Route[I - 1], Route[I]);
			if (Left <= L)
			{
				At = FMath::Lerp(Route[I - 1], Route[I], Left / FMath::Max(L, 1e-6));
				break;
			}
			Left -= L;
			At = Route[I];
		}
		In.Feet = At;
		Plan.Update(Dt, In, B.Nav);
		for (const FMIGuideChevron& V : Plan.GetChevrons())
		{
			if (const FVector* Was = Seen.Find(V.Slot))
			{
				(Was->Equals(V.Tip, 1e-6) ? Kept : Moved)++;
			}
			Seen.FindOrAdd(V.Slot) = V.Tip;
		}
	}
	TestTrue(TEXT("searched again while walking (every second)"), Plan.GetSearches() >= Searches + 5);
	TestEqual(TEXT("no chevron jumped while the player walked the route"), Moved, 0);
	TestTrue(TEXT("chevrons were seen again"), Kept > 100);
	TestTrue(TEXT("the drawn route is the first one (no flip)"), Plan.GetPath().Num() == Route.Num() && Plan.GetPath()[1].Equals(Route[1], 1e-6));
	// A stray of 4 m (to walkable ground) asks for a new route at once.
	FVector Off4 = FVector::ZeroVector;
	bool bFound = false;
	for (int32 A = 0; A < 64 && !bFound; ++A)
	{
		const double Ang = (A % 16) * UE_DOUBLE_PI / 8.0;
		const double Radius = 4.0 + (A / 16) * 1.0;
		Off4 = In.Feet + FVector(FMath::Cos(Ang) * Radius, 0.0, FMath::Sin(Ang) * Radius);
		double Near = 1e9;
		for (int32 I = 0; I + 1 < Route.Num(); ++I)
		{
			const FVector2D P0(Route[I].X, Route[I].Z), P1(Route[I + 1].X, Route[I + 1].Z), Q(Off4.X, Off4.Z);
			const double L2 = (P1 - P0).SizeSquared();
			const double T = L2 > 1e-12 ? FMath::Clamp(FVector2D::DotProduct(Q - P0, P1 - P0) / L2, 0.0, 1.0) : 0.0;
			Near = FMath::Min(Near, FVector2D::Distance(Q, P0 + (P1 - P0) * T));
		}
		bFound = Near > B.Tune.Stray + 0.3 && B.Nav.IsWalkable(Off4.X, Off4.Z);
	}
	if (!TestTrue(FString::Printf(TEXT("walkable ground 4 to 7 m from the route near (%.1f, %.1f)"), In.Feet.X, In.Feet.Z), bFound))
	{
		return false;
	}
	In.Feet = FVector(Off4.X, B.Nav.GroundHeight(Off4.X, Off4.Z, B.Tune.StepUp), Off4.Z);
	const int32 Before = Plan.GetSearches();
	for (int32 F = 0; F < 12; ++F)
	{
		Plan.Update(Dt, In, B.Nav);
	}
	TestTrue(TEXT("a stray: a new search within 0.4 s"), Plan.GetSearches() > Before);
	TestTrue(FString::Printf(TEXT("and the route starts at the player again (%.2f m off)"), Plan.GetOffRoute()), Plan.GetOffRoute() < 0.3);
	return !HasAnyErrors();
}

namespace MIGuideTestsPrivate
{
	constexpr float Dt = 1.f / 30.f;

	/** A world with collision and the game booted (as MurderInc.Run.*), plus the guide. */
	struct FGuideWorld
	{
		UWorld* World = nullptr;
		AMIPlayerCharacter* Player = nullptr;
		UMIGameSubsystem* Game = nullptr;
		AMIGuide* Guide = nullptr;

		FGuideWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("MIGuideWorld"));
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
		~FGuideWorld()
		{
			World->EndPlay(EEndPlayReason::Quit);
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
		void Step()
		{
			World->Tick(LEVELTICK_All, Dt);
			GFrameCounter++;
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGuideCombatTest, "MurderInc.Guide.Combat", MITest::Flags)

bool FMIGuideCombatTest::RunTest(const FString& Parameters)
{
	using namespace MIGuideTestsPrivate;
	FGuideWorld W;
	FMIBootOptions O;
	O.bTitle = false;
	O.Mode = TEXT("mission");
	O.Difficulty = TEXT("hustler");
	O.bPersist = false;
	O.bDrawGrey = false;
	if (!TestTrue(TEXT("the game boots"), W.Player && W.Game && W.Game->Boot(O)))
	{
		return false;
	}
	W.Guide = AMIGuide::Ensure(W.World);
	if (!TestNotNull(TEXT("the guide is in the world"), W.Guide))
	{
		return false;
	}
	for (int32 I = 0; I < 30; ++I)
	{
		W.Step();
	}
	// A living unit whose spawn id is not the index of any listed slot: read by id instead of by slot (the bug this test
	// was written for), the guide would never find it.
	FMIEnemyField& Field = W.Game->GetEnemies();
	int32 Pick = INDEX_NONE;
	for (const int32 I : Field.GetList())
	{
		const FMIEnemy& E = Field.GetSlots()[I];
		if (E.bAlive && !Field.GetList().Contains(E.Id))
		{
			Pick = I;
			break;
		}
	}
	if (!TestTrue(TEXT("a living unit whose id is no listed slot's index"), Pick != INDEX_NONE))
	{
		return false;
	}
	// The field set by hand (the rules are not stepped here): that one unit engaging, every other one calm.
	const auto SetModes = [&Field](int32 Engaging)
	{
		for (const int32 I : Field.GetList())
		{
			if (FMIEnemy* E = Field.Find(Field.GetSlots()[I].Id))
			{
				E->Mode = I == Engaging ? EMIEnemyMode::Engage : EMIEnemyMode::Patrol;
			}
		}
	};
	SetModes(Pick);
	for (int32 I = 0; I < 3; ++I)
	{
		W.Guide->Step(0.1);
	}
	TestTrue(FString::Printf(TEXT("one engaging Goon is a fight (combat %.2f)"), W.Guide->GetPlan().GetCombat()), W.Guide->GetPlan().GetCombat() > 0.3);
	SetModes(INDEX_NONE);
	for (int32 I = 0; I < 10; ++I)
	{
		W.Guide->Step(0.1);
	}
	TestEqual(TEXT("nobody engaging: no fight"), W.Guide->GetPlan().GetCombat(), 0.0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGuideEndToEndTest, "MurderInc.Guide.EndToEnd", MITest::Flags)

bool FMIGuideEndToEndTest::RunTest(const FString& Parameters)
{
	using namespace MIGuideTestsPrivate;
	FGuideWorld W;
	FMIBootOptions O;
	O.bTitle = false;
	O.Mode = TEXT("mission");
	O.Difficulty = TEXT("hustler");
	O.bPersist = false;
	O.bDrawGrey = false;
	if (!TestTrue(TEXT("the game boots"), W.Player && W.Game && W.Game->Boot(O)))
	{
		return false;
	}
	// No controller in a test world: the movement component runs on the rules' velocity anyway (as with a player).
	W.Player->GetCharacterMovement()->bRunPhysicsWithNoController = true;
	W.Guide = AMIGuide::Ensure(W.World);
	if (!TestNotNull(TEXT("the guide is in the world"), W.Guide))
	{
		return false;
	}
	TestTrue(TEXT("Ground path on by default"), W.Game->GetSettings().bGuide);
	const FMILevelData* Level = W.Game->GetLevel();
	const int32 Limit = 30 * 60 * 6;
	int32 Step = -2;
	double StepStart = 0.0, BestLeft = 1e9, SinceBetter = 0.0, WorstOff = 0.0;
	int32 Frames = 0, Grabbing = 0, ShownFrames = 0, StoryFrames = 0, MaxStrips = 0;
	bool bStuck = false;
	for (; Frames < Limit && W.Game->GetRules().GetState() != EMIGameState::Complete && !bStuck; ++Frames)
	{
		// Patched up every frame (the enemies' hits still land): the bot only walks where the guide points.
		FMIPlayerRules& R = W.Player->GetPlayerRules();
		if (R.bAlive)
		{
			R.Health = R.MaxHealth;
		}
		FMIPlayerInputState& In = W.Player->GetInput();
		In.Move = FVector2D::ZeroVector;
		In.bSprint = false;
		const FMIGuidePlan& Plan = W.Guide->GetPlan();
		if (W.Game->GetRules().GetState() == EMIGameState::Playing && Plan.IsActive())
		{
			StoryFrames++;
			ShownFrames += W.Guide->IsShown() ? 1 : 0;
			MaxStrips = FMath::Max(MaxStrips, W.Guide->VisibleStrips());
			const double Now = Frames * Dt;
			if (Plan.GetStep() != Step)
			{
				if (Step != -2)
				{
					AddInfo(FString::Printf(TEXT("step %d done in %.1f s"), Step, Now - StepStart));
				}
				Step = Plan.GetStep();
				StepStart = Now;
				BestLeft = 1e9;
				SinceBetter = 0.0;
			}
			const FVector Feet = W.Game->PlayerFeetWeb();
			const FVector Goal = Plan.GetGoal();
			const bool bReel = Step != FMIGuidePlan::ExtractionStep;
			if (bReel && Flat(Feet, Goal) < 1.5)
			{
				// At the case: look at it and hold the grab.
				const FVector Eye = R.Eye;
				const FVector D = MI::Web::ToUnreal(Goal) + FVector(0, 0, 50.0) - Eye;
				R.Yaw = FMath::RadiansToDegrees(FMath::Atan2(D.Y, D.X));
				R.Pitch = FMath::RadiansToDegrees(FMath::Atan2(D.Z, D.Size2D()));
				W.Game->SetInteractHeld(true);
				Grabbing++;
				SinceBetter = 0.0;
			}
			else if (Plan.HasRoute())
			{
				W.Game->SetInteractHeld(false);
				// Pure pursuit on the drawn route: the point 1.6 m on from the one nearest the feet.
				const TArray<FVector>& P = Plan.GetPath();
				double BestD = 1e18, BestS = 0.0, Run = 0.0;
				TArray<double> Cum;
				Cum.Add(0.0);
				for (int32 I = 1; I < P.Num(); ++I)
				{
					Cum.Add(Cum.Last() + FVector::Dist(P[I - 1], P[I]));
				}
				for (int32 I = 0; I + 1 < P.Num(); ++I)
				{
					const FVector2D A(P[I].X, P[I].Z), B(P[I + 1].X, P[I + 1].Z), Q(Feet.X, Feet.Z);
					const double L2 = (B - A).SizeSquared();
					const double T = L2 > 1e-12 ? FMath::Clamp(FVector2D::DotProduct(Q - A, B - A) / L2, 0.0, 1.0) : 0.0;
					const double Dd = FVector2D::Distance(Q, A + (B - A) * T);
					if (Dd < BestD)
					{
						BestD = Dd;
						BestS = Cum[I] + (Cum[I + 1] - Cum[I]) * T;
					}
				}
				WorstOff = FMath::Max(WorstOff, BestD);
				const double Want = FMath::Min(BestS + 1.6, Cum.Last());
				FVector Aim = P.Last();
				for (int32 I = 0; I + 1 < P.Num(); ++I)
				{
					if (Cum[I + 1] >= Want)
					{
						const double T = (Want - Cum[I]) / FMath::Max(Cum[I + 1] - Cum[I], 1e-9);
						Aim = FMath::Lerp(P[I], P[I + 1], T);
						break;
					}
				}
				if (Want >= Cum.Last() - 1e-6)
				{
					Aim = Goal;  // the last metres: straight at the goal (the truck's zone, the case)
				}
				const FVector D = MI::Web::ToUnreal(Aim) - MI::Web::ToUnreal(Feet);
				if (D.Size2D() > 1.0)
				{
					R.Yaw = FMath::RadiansToDegrees(FMath::Atan2(D.Y, D.X));
					R.Pitch = 0.0;
					In.Move = FVector2D(0.0, 1.0);
					In.bSprint = true;
				}
			}
			// Stuck: no metre gained along the route in 8 s (the grab excepted).
			if (Plan.GetRemaining() < BestLeft - 1.0)
			{
				BestLeft = Plan.GetRemaining();
				SinceBetter = 0.0;
			}
			else
			{
				SinceBetter += Dt;
			}
			if (SinceBetter > 8.0)
			{
				AddError(FString::Printf(TEXT("stuck on step %d at (%.1f, %.2f, %.1f), %.1f m left, %.1f m off the route"), Step, Feet.X, Feet.Y, Feet.Z,
					Plan.GetRemaining(), Plan.GetOffRoute()));
				bStuck = true;
			}
		}
		else
		{
			W.Game->SetInteractHeld(false);
		}
		W.Step();
	}
	const FMIGameRules& Rules = W.Game->GetRules();
	TestEqual(TEXT("the story is complete: three reels and the truck, by the drawn route alone"), (int32)Rules.GetState(), (int32)EMIGameState::Complete);
	TestEqual(TEXT("all three reels"), Rules.GetRun().Reels, Level->Objectives.Num());
	TestTrue(TEXT("the path was shown in every frame of the story"), StoryFrames > 0 && ShownFrames == StoryFrames);
	TestTrue(TEXT("the bot never left the route by more than 2.5 m"), WorstOff < 2.5);
	const bool bArt = W.Guide->GetStrips().Num() > 0;
	if (bArt)
	{
		TestTrue(TEXT("strips drawn"), MaxStrips >= 8);
		for (const UStaticMeshComponent* C : W.Guide->GetStrips())
		{
			TestEqual(TEXT("a strip has no collision"), (int32)C->GetCollisionEnabled(), (int32)ECollisionEnabled::NoCollision);
			TestFalse(TEXT("a strip casts no shadow"), C->CastShadow);
		}
	}
	else
	{
		AddWarning(TEXT("the tracer material is not in this project: the path's strips were not built (the plan was tested)"));
	}
	for (int32 I = 0; I < 3; ++I)
	{
		W.Step();
	}
	TestEqual(TEXT("after the truck: nothing drawn"), W.Guide->VisibleStrips(), 0);
	const AMIGuide::FCost& C = W.Guide->GetCost();
	AddInfo(FString::Printf(TEXT("story complete in %.1f s of game time (%d frames, %d holding the grab); worst distance from the route %.2f m"), Frames * Dt, Frames, Grabbing, WorstOff));
	AddInfo(FString::Printf(TEXT("guide cost: %d frames, %.4f ms a frame on average, worst %.3f ms; %d searches, %.3f ms on average, worst %.3f ms; %d strip moves; %d strips at most"),
		C.Frames, C.Frames ? C.TotalMs / C.Frames : 0.0, C.WorstMs, C.Searches, C.Searches ? C.SearchMs / C.Searches : 0.0, C.WorstSearchMs, C.Moves, MaxStrips));
	return !HasAnyErrors();
}

#endif
