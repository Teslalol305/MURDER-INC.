// MurderInc.Golden.FlowRules: Flow/MIFlowRules against golden/flow_rules.json (compass sectors, spawn scores, pickSpawn
// over the level's points, wave orders, the holdout formulas for waves 1 to 30, kill scores, pursuit types, cards).
// MurderInc.Golden.Directors: FMIGameRules (src/game.js) with FMIEnemyField on the box world against
// golden/directors.json: a whole Story run to the IPX truck, a Story run that dies, four waves of Hold the Block (Boss),
// a Story run on Hustler and Hold the Block on Kingpin.

#include "Enemies/MIEnemyTune.h"
#include "Flow/MIGameRules.h"
#include "Tests/MITestUtil.h"

#if WITH_AUTOMATION_TESTS

using namespace MITest;

namespace MIGoldenFlowPrivate
{
	bool LoadAll(FAutomationTestBase& T, FMIFlowTune& Flow, FMIText& Text)
	{
		TSharedPtr<FJsonObject> Config;
		FString Error;
		if (!UMIDataSubsystem::LoadJsonFile(TEXT("config.json"), Config, Error) || !FMIFlowTune::Parse(Config, Flow, Error) || !FMIText::Load(Text, Error))
		{
			T.AddError(Error);
			return false;
		}
		return true;
	}

	struct FHost : public IMIGameHost, public IMIEnemyHost
	{
		FVector* PlayerPos = nullptr;
		int32 Kills = 0;
		int32 BestScore = 0;
		TMap<FName, FMIEnemyTune> Tunes;
		virtual void ResetPlayer(const FVector& Pos, double Yaw) override { *PlayerPos = Pos; }
		virtual void HealPlayer(double Amount) override {}
		virtual void AddReserve(double Amount, double Cap) override {}
		virtual void ResetExplosives() override {}
		virtual void ResetCombat() override { Kills = 0; }
		virtual void SetRegen(double Delay, double Rate) override {}
		virtual void SetInvulnerable(bool bOn) override {}
		virtual void Stats(int32& OutKills, int32& Shots, int32& Hits, int32& Headshots) const override
		{
			OutKills = Kills;
			Shots = Hits = Headshots = 0;
		}
		virtual const FMIEnemyTune* EnemyTune(FName D) const override { return Tunes.Find(D); }
		virtual int32 Best() const override { return BestScore; }
		virtual bool SetBest(int32 Score) override
		{
			if (Score > BestScore)
			{
				BestScore = Score;
				return true;
			}
			return false;
		}
		// The enemies' world calls: recorded by nobody here (their own replay is MurderInc.Golden.Enemies).
		virtual FVector Hitscan(int32, const FVector& O, const FVector& D, double, double) override { return O + D * 10.0; }
		virtual void DamagePlayer(double, const FVector&, FName) override {}
		virtual void Explode(int32, const FVector&, double, double, double) override {}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGoldenFlowRulesTest, "MurderInc.Golden.FlowRules", MITest::Flags)

bool FMIGoldenFlowRulesTest::RunTest(const FString& Parameters)
{
	// Recorded with the drones in the game; the shipped data has them off (DECISIONS.md 2026-11-27 ~22:15).
	const MIEnemy::FMIDronesScope DronesOn(true);
	using namespace MIGoldenFlowPrivate;
	FMIFlowTune Flow;
	FMIText Text;
	const TSharedPtr<FJsonObject> G = LoadGolden(*this, TEXT("flow_rules.json"));
	const FMILevelData* Level = FMILevelData::Get();
	if (!LoadAll(*this, Flow, Text) || !G || !Level)
	{
		return false;
	}
	FChecker C(*this);
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("sectors")))
	{
		const FJsonArray& A = V->AsArray();
		C.True(TEXT("compassSector"), MIFlow::CompassSector(Num(A, 0), Num(A, 1)) == static_cast<int32>(Num(A, 2)));
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("scores")))
	{
		const FJsonArray& A = V->AsArray();
		FMISpawnCandidate S{Num(A, 0), A[1]->AsBool(), Num(A, 2) < 0 ? MIEnemy::Inf : Num(A, 2), Num(A, 3)};
		C.Near(TEXT("spawnScore"), MIFlow::SpawnScore(S, Flow, Flow.Far), Num(A, 4), 1e-10);
	}
	// pickSpawn with the recorded answers, in the order the web game asked for them.
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("picks")))
	{
		const TSharedPtr<FJsonObject>& P = V->AsObject();
		const TSharedPtr<FJsonObject>& Q = P->GetObjectField(TEXT("q"));
		const FName Wanted(P->GetStringField(TEXT("wanted")));
		const FJsonArray& Answers = P->GetArrayField(TEXT("answers"));
		const double Qx = Q->GetNumberField(TEXT("x")), Qz = Q->GetNumberField(TEXT("z")), MinD = Q->GetNumberField(TEXT("minDistance"));
		const bool bStrict = Q->GetBoolField(TEXT("strict"));
		int32 K = 0, Best = -1;
		double BestScore = -MIEnemy::Inf;
		bool bBestFar = false;
		for (const FMILevelPoint& Point : Level->Spawns)
		{
			if (Point.Type != Wanted)
			{
				continue;
			}
			const double D = MI::Web::Hypot(Point.Pos.X - Qx, Point.Pos.Z - Qz);
			const bool bFar = D >= MinD;
			if (bStrict && bBestFar && !bFar)
			{
				continue;
			}
			if (K + 2 >= Answers.Num())
			{
				C.True(TEXT("pickSpawn asked more than the web game"), false);
				break;
			}
			FMISpawnCandidate S;
			S.Distance = D;
			S.bHidden = Answers[K++]->AsArray()[2]->AsBool();
			const double U = Num(Answers[K++]->AsArray(), 2);
			S.UsedAgo = U < 0 ? MIEnemy::Inf : U;
			S.Random = Num(Answers[K++]->AsArray(), 2);
			const double Score = MIFlow::SpawnScore(S, Flow, MinD);
			if (Score > BestScore || (bStrict && bFar && !bBestFar))
			{
				Best = Point.Index;
				BestScore = Score;
				bBestFar = bFar;
			}
		}
		C.True(TEXT("pickSpawn answers used"), K == Answers.Num());
		C.True(TEXT("pickSpawn best"), Best == static_cast<int32>(P->GetNumberField(TEXT("best"))));
	}
	auto Names = [](const TArray<FName>& Order)
	{
		FString S;
		for (const FName N : Order)
		{
			S += N.ToString() + TEXT(",");
		}
		return S;
	};
	auto JsNames = [](const FJsonArray& A)
	{
		FString S;
		for (const TSharedPtr<FJsonValue>& N : A)
		{
			S += N->AsString() + TEXT(",");
		}
		return S;
	};
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("mission")))
	{
		const FJsonArray& A = V->AsArray();
		C.Same(TEXT("missionOrder"), Names(MIFlow::MissionOrder(static_cast<int32>(Num(A, 0)), static_cast<int32>(Num(A, 1)))), JsNames(A[2]->AsArray()));
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("orders")))
	{
		const FJsonArray& A = V->AsArray();
		C.Same(TEXT("holdoutOrder"), Names(MIFlow::HoldoutOrder(static_cast<int32>(Num(A, 0)), static_cast<int32>(Num(A, 1)))), JsNames(A[2]->AsArray()));
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("holdout")))
	{
		const TSharedPtr<FJsonObject>& W = V->AsObject();
		const int32 N = static_cast<int32>(W->GetNumberField(TEXT("wave")));
		const MIFlow::FHoldoutWave H = MIFlow::HoldoutWave(N, Flow);
		const FString L = FString::Printf(TEXT("holdout wave %d "), N);
		C.True(L + TEXT("total"), H.Total == static_cast<int32>(W->GetNumberField(TEXT("total"))));
		C.True(L + TEXT("buzzards"), H.Buzzards == static_cast<int32>(W->GetNumberField(TEXT("buzzards"))));
		C.Same(L + TEXT("order"), Names(H.Order), JsNames(W->GetArrayField(TEXT("order"))));
		C.Near(L + TEXT("stagger"), H.Stagger, W->GetNumberField(TEXT("stagger")), 1e-10);
		const TSharedPtr<FJsonObject>& S = W->GetObjectField(TEXT("scale"));
		C.Near(L + TEXT("hp"), H.Hp, S->GetNumberField(TEXT("hp")), 1e-10);
		C.Near(L + TEXT("damage"), H.Damage, S->GetNumberField(TEXT("damage")), 1e-10);
		C.Near(L + TEXT("cooldown"), H.Cooldown, S->GetNumberField(TEXT("cooldown")), 1e-10);
		C.True(L + TEXT("extraAlive"), H.ExtraAlive == static_cast<int32>(W->GetNumberField(TEXT("extraAlive"))));
		C.True(L + TEXT("killGoon"), MIFlow::KillScore(true, N, Flow) == static_cast<int32>(W->GetNumberField(TEXT("killGoon"))));
		C.True(L + TEXT("killBuzzard"), MIFlow::KillScore(false, N, Flow) == static_cast<int32>(W->GetNumberField(TEXT("killBuzzard"))));
		C.Near(L + TEXT("waveClear"), Flow.WaveClear.Eval(N), W->GetNumberField(TEXT("waveClear")), 1e-10);
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("pursuit")))
	{
		const FJsonArray& A = V->AsArray();
		C.Same(TEXT("pursuitType"), MIFlow::PursuitType(Num(A, 0), Flow.PursuitBuzzardShare).ToString(), A[1]->AsString());
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("cards")))
	{
		const TSharedPtr<FJsonObject>& O = V->AsObject();
		const TSharedPtr<FJsonObject>& R = O->GetObjectField(TEXT("run"));
		const TSharedPtr<FJsonObject>& Card = O->GetObjectField(TEXT("card"));
		const int32 Shots = static_cast<int32>(R->GetNumberField(TEXT("shots"))), Hits = static_cast<int32>(R->GetNumberField(TEXT("hits")));
		const int32 Rating = MIFlow::RatingPoints(R->GetNumberField(TEXT("time")), Shots, Hits, static_cast<int32>(R->GetNumberField(TEXT("retries"))), Flow);
		C.True(TEXT("rating"), Rating == static_cast<int32>(Card->GetNumberField(TEXT("rating"))));
		C.Same(TEXT("rating name"), Text.Get(FString::Printf(TEXT("ratings.%d"), Rating)), Card->GetStringField(TEXT("ratingName")));
		C.Near(TEXT("accuracy"), MIFlow::Accuracy(Shots, Hits), O->GetNumberField(TEXT("accuracy")), 1e-10);
		C.True(TEXT("score"), static_cast<int32>(FMath::FloorToDouble(R->GetNumberField(TEXT("score")) + 0.5)) == static_cast<int32>(Card->GetNumberField(TEXT("score"))));
	}
	C.Same(TEXT("grouped"), FMIText::Grouped(12345.4), TEXT("12,345"));
	C.Same(TEXT("tally"), Text.Format(TEXT("objectives.tally.wave"), {{TEXT("n"), TEXT("3")}, {TEXT("score"), FMIText::Grouped(12345)}}), FString(TEXT("Wave 3 · 12,345")));
	C.Report(TEXT("flow rules"));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGoldenDirectorsTest, "MurderInc.Golden.Directors", MITest::Flags)

bool FMIGoldenDirectorsTest::RunTest(const FString& Parameters)
{
	// Recorded with the drones in the game; the shipped data has them off (DECISIONS.md 2026-11-27 ~22:15).
	const MIEnemy::FMIDronesScope DronesOn(true);
	using namespace MIGoldenFlowPrivate;
	FMIFlowTune Flow;
	FMIText Text;
	const TSharedPtr<FJsonObject> G = LoadGolden(*this, TEXT("directors.json"));
	const FMILevelData* Level = FMILevelData::Get();
	if (!LoadAll(*this, Flow, Text) || !G || !Level)
	{
		return false;
	}
	const uint32 Seed = static_cast<uint32>(G->GetNumberField(TEXT("seed")));
	static const TSet<FString> Compared = {TEXT("game:state"), TEXT("objective:done"), TEXT("objective:all"), TEXT("holdout:wave"), TEXT("extraction:reached"), TEXT("enemy:spawn"),
		TEXT("enemy:killed"), TEXT("hud:warn"), TEXT("hud:objective"), TEXT("hud:tally"), TEXT("hud:radio"), TEXT("hud:reels"), TEXT("hud:message"), TEXT("hud:prompt"), TEXT("menus:card"),
		TEXT("audio:sting"), TEXT("player:heal"), TEXT("weapon:reserve")};

	for (const TSharedPtr<FJsonValue>& SV : G->GetArrayField(TEXT("scenarios")))
	{
		const TSharedPtr<FJsonObject>& S = SV->AsObject();
		const FString Name = S->GetStringField(TEXT("name"));
		FChecker C(*this);
		FHost Host;
		FVector PlayerPos = FVector::ZeroVector;
		Host.PlayerPos = &PlayerPos;
		FString Error;
		for (const FName D : {FName(TEXT("hustler")), FName(TEXT("boss")), FName(TEXT("kingpin"))})
		{
			FMIEnemyTune& T = Host.Tunes.Add(D);
			if (!FMIEnemyTune::Load(D, T, Error))
			{
				AddError(Error);
				return false;
			}
		}
		const FMIRng Root(Seed);
		FMIBoxWorld World;
		Level->FillWorld(World, Root);
		FMIEnemyField Field;
		const FName Difficulty(S->GetStringField(TEXT("difficulty")));
		Field.Init(Host.Tunes[Difficulty], Level, &World, &Host);
		FMIGameRules Rules;
		Rules.Init(Flow, Text, Level, &World, &Field, &Host, Root);
		Rules.SetDifficulty(Difficulty);
		TArray<FMIEnemyEvent> Out;
		auto Drain = [&]()
		{
			Out.Reset();
			Rules.DrainEnemies(Out);
			for (const FMIEnemyEvent& Ev : Out)
			{
				if (Ev.Kind == FMIEnemyEvent::EKind::Killed && Ev.bByPlayer)
				{
					Host.Kills++;
				}
			}
		};
		Rules.Start(FName(S->GetStringField(TEXT("mode"))));
		Drain();

		TMap<int32, TArray<TSharedPtr<FJsonValue>>> Want, Actions;
		for (const TSharedPtr<FJsonValue>& V : S->GetArrayField(TEXT("events")))
		{
			if (Compared.Contains(V->AsArray()[1]->AsString()))
			{
				Want.FindOrAdd(static_cast<int32>(Num(V->AsArray(), 0))).Add(V);
			}
		}
		for (const TSharedPtr<FJsonValue>& V : S->GetArrayField(TEXT("actions")))
		{
			Actions.FindOrAdd(static_cast<int32>(Num(V->AsArray(), 0))).Add(V);
		}
		bool bHold = false;
		bool bAlive = true;
		const double Dt = StepOf(S);
		const FJsonArray& Rows = S->GetArrayField(TEXT("rows"));
		int32 FirstBad = -1;
		for (int32 F = -1; F < Rows.Num(); ++F)
		{
			const int32 Before = C.Failures;
			if (F >= 0)
			{
				if (const TArray<TSharedPtr<FJsonValue>>* A = Actions.Find(F))
				{
					for (const TSharedPtr<FJsonValue>& V : *A)
					{
						const FJsonArray& Act = V->AsArray();
						const FString Kind = Act[1]->AsString();
						if (Kind == TEXT("at"))
						{
							PlayerPos = Vec3(Act[2]);
						}
						else if (Kind == TEXT("hold"))
						{
							bHold = Act[2]->AsBool();
						}
						else if (Kind == TEXT("kill"))
						{
							if (FMIEnemy* E = Field.Find(static_cast<int32>(Num(Act, 2))))
							{
								Field.Damage(*E, 9999, TEXT("body"), TOptional<FVector>(), true, TEXT("chopper"));
							}
							Drain();
						}
						else if (Kind == TEXT("die"))
						{
							bAlive = false;
							Rules.OnPlayerDead();
						}
					}
				}
				FMIFlowPlayer P;
				P.Pos = PlayerPos;
				P.bAlive = bAlive;
				P.Health = bAlive ? 100 : 0;
				const bool bLive = Rules.Update(Dt, P, bHold);
				Drain();
				if (bLive && Rules.GetState() != EMIGameState::Title && Rules.GetState() != EMIGameState::Paused)
				{
					FMIEnemyPlayer EP;
					EP.Pos = PlayerPos;
					EP.Eye = PlayerPos + FVector(0, 1.68, 0);
					EP.bAlive = bAlive;
					Field.Update(Dt, EP);
					Drain();
				}
				const FJsonArray& R = Rows[F]->AsArray();
				static const TCHAR* States[] = {TEXT("title"), TEXT("intro"), TEXT("playing"), TEXT("paused"), TEXT("dead"), TEXT("complete")};
				const FString At = FString::Printf(TEXT("%s frame %d "), *Name, F);
				C.Same(At + TEXT("state"), States[static_cast<int32>(Rules.GetState())], R[0]->AsString());
				C.Near(At + TEXT("clock"), Rules.GetClock(), Num(R, 1), 1e-9);
				C.True(At + TEXT("reels"), Rules.GetRun().Reels == static_cast<int32>(Num(R, 2)));
				C.True(At + TEXT("wave"), Rules.GetRun().Wave == static_cast<int32>(Num(R, 3)));
				C.Near(At + TEXT("score"), Rules.GetRun().Score, Num(R, 4), 1e-9);
				C.True(At + FString::Printf(TEXT("queue %d"), Rules.QueueLength()), Rules.QueueLength() == static_cast<int32>(Num(R, 5)));
				C.True(At + FString::Printf(TEXT("alive %d"), Field.AliveCount()), Field.AliveCount() == static_cast<int32>(Num(R, 6)));
				C.True(At + TEXT("maxAlive"), Rules.MaxAliveNow() == static_cast<int32>(Num(R, 7)));
				C.True(At + TEXT("pursuitLeft"), Rules.PursuitLeftNow() == static_cast<int32>(Num(R, 8)));
				C.Near(At + TEXT("music"), Rules.View().Music, Num(R, 9), 1e-9);
				C.Near(At + TEXT("progress"), Rules.Progress(), Num(R, 10), 1e-9);
				C.Near(At + TEXT("run time"), Rules.GetRun().Time, Num(R, 11), 1e-9);
			}
			// The flow's events of this frame, in order.
			TArray<FMIFlowEvent> Got;
			for (const FMIFlowEvent& E : Rules.Events())
			{
				if (Compared.Contains(E.Name.ToString()))
				{
					Got.Add(E);
				}
			}
			Rules.Events().Reset();
			const TArray<TSharedPtr<FJsonValue>>* W = Want.Find(F);
			const int32 WantN = W ? W->Num() : 0;
			const FString At = FString::Printf(TEXT("%s frame %d "), *Name, F);
			C.True(At + FString::Printf(TEXT("event count %d vs %d"), Got.Num(), WantN), Got.Num() == WantN);
			for (int32 K = 0; K < FMath::Min(Got.Num(), WantN); ++K)
			{
				const FJsonArray& A = (*W)[K]->AsArray();
				const FString N = A[1]->AsString();
				const TSharedPtr<FJsonObject>& O = A[2]->AsObject();
				const FMIFlowEvent& E = Got[K];
				if (!C.Same(At + TEXT("event"), E.Name.ToString(), N))
				{
					break;
				}
				FString T;
				if (N == TEXT("game:state"))
				{
					C.Same(At + N, E.Text, O->GetStringField(TEXT("state")));
				}
				else if (N == TEXT("hud:prompt"))
				{
					const bool bNull = !O->HasTypedField<EJson::String>(TEXT("text"));
					C.Same(At + N, E.Text, bNull ? FString() : O->GetStringField(TEXT("text")));
					if (!bNull)
					{
						C.Near(At + N + TEXT(" progress"), E.A, O->GetNumberField(TEXT("progress")), 1e-9);
					}
				}
				else if (O->TryGetStringField(TEXT("text"), T))
				{
					C.Same(At + N, E.Text, T);
				}
				else if (N == TEXT("objective:done"))
				{
					C.Same(At + N, E.Text, O->GetStringField(TEXT("id")));
					C.True(At + N + TEXT(" index"), E.A == O->GetNumberField(TEXT("index")));
				}
				else if (N == TEXT("holdout:wave"))
				{
					C.True(At + N, E.A == O->GetNumberField(TEXT("wave")) && E.B == O->GetNumberField(TEXT("count")));
				}
				else if (N == TEXT("enemy:spawn") || N == TEXT("enemy:killed"))
				{
					C.True(At + N + TEXT(" id"), static_cast<int32>(E.A) == static_cast<int32>(O->GetNumberField(TEXT("id"))));
					C.Same(At + N + TEXT(" type"), E.Text, O->GetStringField(TEXT("type")));
				}
				else if (N == TEXT("hud:reels"))
				{
					C.True(At + N, E.A == O->GetNumberField(TEXT("n")) && E.B == O->GetNumberField(TEXT("t")));
				}
				else if (N == TEXT("menus:card") && Rules.Card().IsSet())
				{
					const FMIRunCard& Card = Rules.Card().GetValue();
					C.Same(At + N, Card.Screen.ToString(), O->GetStringField(TEXT("screen")));
					C.True(At + N + TEXT(" rating"), Card.Rating == static_cast<int32>(O->GetNumberField(TEXT("rating"))));
					C.Same(At + N + TEXT(" rating name"), Card.RatingName, O->GetStringField(TEXT("ratingName")));
					C.True(At + N + TEXT(" score"), Card.Score == static_cast<int32>(O->GetNumberField(TEXT("score"))));
					C.True(At + N + TEXT(" kills"), Card.Kills == static_cast<int32>(O->GetNumberField(TEXT("kills"))));
					C.True(At + N + TEXT(" reels"), Card.Reels == static_cast<int32>(O->GetNumberField(TEXT("reels"))));
					C.True(At + N + TEXT(" wave"), Card.Wave == static_cast<int32>(O->GetNumberField(TEXT("wave"))));
					C.Near(At + N + TEXT(" time"), Card.Time, O->GetNumberField(TEXT("time")), 1e-9);
				}
			}
			if (FirstBad < 0 && C.Failures > Before)
			{
				FirstBad = F;
			}
		}
		AddInfo(FString::Printf(TEXT("%s: %d frames, %d checks, %d mismatches, first at frame %d"), *Name, Rows.Num(), C.Checks, C.Failures, FirstBad));
	}
	return true;
}

#endif
