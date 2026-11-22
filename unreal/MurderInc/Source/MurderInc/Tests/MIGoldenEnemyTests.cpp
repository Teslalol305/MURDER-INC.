// MurderInc.Golden.Enemies: six fights of the web game's own src/enemies.js (golden/enemies.json, written by
// tools/ue-export/golden-ai.mjs) replayed against FMIEnemyField on the box world, frame by frame: every unit's mode,
// engage step, position, heading, health, exposure and sight accumulator, and every event in order (spawns, alerts,
// telegraphs, rounds and bolts with their directions, melee phases, hits, kills, the player's damage, crash bursts).

#include "Enemies/MIEnemies.h"
#include "Tests/MITestUtil.h"

#if WITH_AUTOMATION_TESTS

using namespace MITest;

namespace MIGoldenEnemyPrivate
{
	struct FLogEntry
	{
		FString Name;
		int32 Id = 0;
		FVector Dir = FVector::ZeroVector;
		bool bHasDir = false;
		double Amount = 0;
		FString Text;  // phase, part, kind
	};

	/** Records what the field asks of the world, interleaved with the field's own events, in call order. */
	struct FRecorder : public IMIEnemyHost
	{
		FMIEnemyField* Field = nullptr;
		TArray<FLogEntry> Log;

		void Drain()
		{
			for (const FMIEnemyEvent& Ev : Field->Events())
			{
				FLogEntry& L = Log.AddDefaulted_GetRef();
				static const TCHAR* Names[] = {TEXT("enemy:spawn"), TEXT("enemy:alert"), TEXT("enemy:telegraph"), TEXT("enemy:fire"), TEXT("enemy:melee"), TEXT("enemy:hit"), TEXT("enemy:killed")};
				L.Name = Names[static_cast<int32>(Ev.Kind)];
				L.Id = Ev.Id;
				if (Ev.Kind == FMIEnemyEvent::EKind::Fire)
				{
					L.Dir = Ev.Dir;
					L.bHasDir = true;
				}
				L.Amount = Ev.Kind == FMIEnemyEvent::EKind::Hit ? Ev.Damage : (Ev.Kind == FMIEnemyEvent::EKind::Telegraph ? Ev.Duration : 0.0);
				L.Text = Ev.Kind == FMIEnemyEvent::EKind::Melee ? Ev.Phase.ToString() : (Ev.Kind == FMIEnemyEvent::EKind::Hit || Ev.Kind == FMIEnemyEvent::EKind::Killed ? Ev.Part.ToString() : FString());
			}
			Field->Events().Reset();
		}
		virtual FVector Hitscan(int32 EnemyId, const FVector& Origin, const FVector& Dir, double Range, double Damage) override
		{
			Drain();
			FLogEntry& L = Log.AddDefaulted_GetRef();
			L.Name = TEXT("hitscan");
			L.Dir = Dir;
			L.bHasDir = true;
			L.Amount = Damage;
			return Origin + Dir * 10.0;
		}
		virtual void DamagePlayer(double Amount, const FVector& From, FName Kind) override
		{
			Drain();
			FLogEntry& L = Log.AddDefaulted_GetRef();
			L.Name = TEXT("player:damage");
			L.Amount = Amount;
			L.Text = Kind.ToString();
		}
		virtual void Explode(int32 EnemyId, const FVector& Pos, double Radius, double Damage, double PlayerScale) override
		{
			Drain();
			FLogEntry& L = Log.AddDefaulted_GetRef();
			L.Name = TEXT("explode");
			L.Amount = Damage;
		}
	};

	FString ModeName(EMIEnemyMode M)
	{
		switch (M)
		{
		case EMIEnemyMode::Patrol: return TEXT("patrol");
		case EMIEnemyMode::Investigate: return TEXT("investigate");
		case EMIEnemyMode::Search: return TEXT("search");
		case EMIEnemyMode::Engage: return TEXT("engage");
		case EMIEnemyMode::Dying: return TEXT("dying");
		default: return TEXT("other");
		}
	}

	FString SubName(const FMIEnemy& E)
	{
		if (!E.IsGoon())
		{
			return E.Telegraph > 0 ? TEXT("telegraph") : (E.BurstLeft > 0 ? TEXT("burst") : TEXT("-"));
		}
		static const TCHAR* Names[] = {TEXT("move"), TEXT("aim"), TEXT("cool"), TEXT("telegraph"), TEXT("burst"), TEXT("windup"), TEXT("lunge"), TEXT("recover")};
		return Names[static_cast<int32>(E.Sub)];
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGoldenEnemiesTest, "MurderInc.Golden.Enemies", MITest::Flags)

bool FMIGoldenEnemiesTest::RunTest(const FString& Parameters)
{
	using namespace MIGoldenEnemyPrivate;
	const TSharedPtr<FJsonObject> G = LoadGolden(*this, TEXT("enemies.json"));
	const FMILevelData* Level = FMILevelData::Get();
	FMIEnemyTune Tune;
	FString Error;
	if (!FMIEnemyTune::Load(TEXT("boss"), Tune, Error))
	{
		AddError(Error);
		return false;
	}
	if (!G || !Level)
	{
		return false;
	}
	const uint32 NavSeed = static_cast<uint32>(G->GetNumberField(TEXT("navSeed")));
	TestEqual(TEXT("enemy seed"), Tune.Seed, static_cast<uint32>(G->GetNumberField(TEXT("seed"))));

	for (const TSharedPtr<FJsonValue>& SV : G->GetArrayField(TEXT("scenarios")))
	{
		const TSharedPtr<FJsonObject>& S = SV->AsObject();
		const FString Name = S->GetStringField(TEXT("name"));
		FChecker C(*this);
		FMIBoxWorld World;
		Level->FillWorld(World, FMIRng(NavSeed));
		FMIEnemyField Field;
		FRecorder Rec;
		Rec.Field = &Field;
		Field.Init(Tune, Level, &World, &Rec);
		const double Dt = StepOf(S);

		const FJsonArray& Players = S->GetArrayField(TEXT("players"));
		Field.SetLivePlayerPos(Vec3(S->GetObjectField(TEXT("player"))->GetArrayField(TEXT("pos"))));
		auto DoSpawn = [&](const FJsonArray& A)
		{
			FMIEnemySpawnOptions O;
			if (!IsNull(A[3]))
			{
				O.Yaw = Num(A, 3);
			}
			O.bAlerted = A[4]->AsBool();
			if (!IsNull(A[5]))
			{
				O.Target = Vec3(A[5]);
			}
			const FMIEnemy* E = Field.Spawn(A[1]->AsString() == TEXT("goon") ? MIEnemy::EType::Goon : MIEnemy::EType::Buzzard, Vec3(A[2]), O);
			C.True(Name + TEXT(" spawn id"), E && E->Id == static_cast<int32>(Num(A, 6)));
		};
		for (const TSharedPtr<FJsonValue>& V : S->GetArrayField(TEXT("spawns")))
		{
			if (Num(V->AsArray(), 0) < 0)
			{
				DoSpawn(V->AsArray());
			}
		}
		Rec.Drain();

		// Expected events per frame, pokes apart.
		TMap<int32, TArray<TSharedPtr<FJsonValue>>> Expected, Pokes;
		for (const TSharedPtr<FJsonValue>& V : S->GetArrayField(TEXT("events")))
		{
			const FJsonArray& A = V->AsArray();
			const FString N = A[1]->AsString();
			(N.StartsWith(TEXT("poke:")) ? Pokes : Expected).FindOrAdd(static_cast<int32>(Num(A, 0))).Add(V);
		}
		TArray<FLogEntry> SetupLog = Rec.Log;
		Rec.Log.Reset();
		if (const TArray<TSharedPtr<FJsonValue>>* Setup = Expected.Find(-1))
		{
			C.True(Name + TEXT(" setup events"), Setup->Num() == SetupLog.Num());
		}

		const FJsonArray& Rows = S->GetArrayField(TEXT("rows"));
		int32 FirstBad = -1;
		for (int32 F = 0; F < Rows.Num(); ++F)
		{
			const int32 Before = C.Failures;
			if (const TArray<TSharedPtr<FJsonValue>>* P = Pokes.Find(F))
			{
				for (const TSharedPtr<FJsonValue>& V : *P)
				{
					const FJsonArray& A = V->AsArray();
					const FString N = A[1]->AsString();
					const TSharedPtr<FJsonObject>& O = A[2]->AsObject();
					if (N == TEXT("poke:damage"))
					{
						if (FMIEnemy* E = Field.Find(static_cast<int32>(O->GetNumberField(TEXT("id")))))
						{
							TOptional<FVector> Dir;
							const TArray<TSharedPtr<FJsonValue>>* D;
							if (O->TryGetArrayField(TEXT("dir"), D))
							{
								Dir = Vec3(*D).GetSafeNormal();
							}
							Field.Damage(*E, O->GetNumberField(TEXT("amount")), FName(O->GetStringField(TEXT("part"))), Dir, true, TEXT("chopper"));
						}
					}
					else if (N == TEXT("poke:alert"))
					{
						Field.Alert(Vec3(O->GetArrayField(TEXT("pos"))), O->GetNumberField(TEXT("radius")));
					}
					else if (N == TEXT("poke:hear"))
					{
						Field.Hear(Vec3(O->GetArrayField(TEXT("pos"))), O->GetNumberField(TEXT("radius")));
					}
					else if (N == TEXT("poke:gunfire"))
					{
						Field.Gunfire(Vec3(O->GetArrayField(TEXT("pos"))));
					}
					Rec.Drain();
				}
			}
			const FJsonArray& Pl = Players[F]->AsArray();
			FMIEnemyPlayer Player;
			Player.Pos = FVector(Num(Pl, 0), Num(Pl, 1), Num(Pl, 2));
			Player.Vel = FVector(Num(Pl, 3), Num(Pl, 4), Num(Pl, 5));
			Player.bCrouching = Num(Pl, 6) != 0;
			Player.bAlive = Num(Pl, 7) != 0;
			Player.Eye = FVector(Num(Pl, 8), Num(Pl, 9), Num(Pl, 10));
			Field.Update(Dt, Player);
			Rec.Drain();

			// The units, by id.
			TArray<const FMIEnemy*> Units;
			for (const int32 I : Field.GetList())
			{
				Units.Add(&Field.GetSlots()[I]);
			}
			Units.Sort([](const FMIEnemy& A, const FMIEnemy& B) { return A.Id < B.Id; });
			const FJsonArray& Row = Rows[F]->AsArray();
			const FString At = FString::Printf(TEXT("%s frame %d "), *Name, F);
			C.True(At + TEXT("unit count"), Units.Num() == Row.Num());
			for (int32 K = 0; K < FMath::Min(Units.Num(), Row.Num()); ++K)
			{
				const FJsonArray& U = Row[K]->AsArray();
				const FMIEnemy& E = *Units[K];
				const FString Who = At + FString::Printf(TEXT("unit %d "), E.Id);
				C.True(Who + TEXT("id"), E.Id == static_cast<int32>(Num(U, 0)));
				C.Same(Who + TEXT("mode"), ModeName(E.Mode), U[2]->AsString());
				C.Same(Who + TEXT("sub"), SubName(E), U[3]->AsString());
				C.Near(Who + TEXT("x"), E.Pos.X, Num(U, 4), 1e-5);
				C.Near(Who + TEXT("y"), E.Pos.Y, Num(U, 5), 1e-5);
				C.Near(Who + TEXT("z"), E.Pos.Z, Num(U, 6), 1e-5);
				C.Near(Who + TEXT("yaw"), MI::Web::AngleDelta(Num(U, 7), E.Yaw), 0.0, 1e-5);
				C.Near(Who + TEXT("hp"), E.Hp, Num(U, 8), 1e-9);
				C.Near(Who + TEXT("exposure"), E.Exposure, Num(U, 9), 1e-6);
				C.Near(Who + TEXT("seen"), E.Seen, Num(U, 10), 1e-6);
			}
			// The events of this frame.
			const TArray<TSharedPtr<FJsonValue>>* Want = Expected.Find(F);
			const int32 WantN = Want ? Want->Num() : 0;
			C.True(At + FString::Printf(TEXT("event count %d vs %d"), Rec.Log.Num(), WantN), Rec.Log.Num() == WantN);
			for (int32 K = 0; K < FMath::Min(WantN, Rec.Log.Num()); ++K)
			{
				const FJsonArray& A = (*Want)[K]->AsArray();
				const FLogEntry& L = Rec.Log[K];
				const FString N = A[1]->AsString();
				C.Same(At + TEXT("event"), L.Name, N);
				const TSharedPtr<FJsonObject>& O = A[2]->AsObject();
				double Id;
				if (O->TryGetNumberField(TEXT("id"), Id) && L.Name.StartsWith(TEXT("enemy:")))
				{
					C.True(At + N + TEXT(" id"), L.Id == static_cast<int32>(Id));
				}
				const TArray<TSharedPtr<FJsonValue>>* D;
				if (L.bHasDir && O->TryGetArrayField(TEXT("dir"), D))
				{
					C.Near(At + N + TEXT(" dir"), (L.Dir - Vec3(*D)).Size(), 0.0, 1e-6);
				}
				double Amount;
				if ((O->TryGetNumberField(TEXT("amount"), Amount) || O->TryGetNumberField(TEXT("damage"), Amount) || O->TryGetNumberField(TEXT("duration"), Amount)))
				{
					C.Near(At + N + TEXT(" amount"), L.Amount, Amount, 1e-9);
				}
				FString Text;
				if (O->TryGetStringField(TEXT("phase"), Text) || O->TryGetStringField(TEXT("kind"), Text) || O->TryGetStringField(TEXT("part"), Text))
				{
					C.Same(At + N + TEXT(" text"), L.Text, Text);
				}
			}
			Rec.Log.Reset();
			if (FirstBad < 0 && C.Failures > Before)
			{
				FirstBad = F;
			}
		}
		const TSharedPtr<FJsonObject>& Final = S->GetObjectField(TEXT("final"));
		C.True(Name + TEXT(" final bodies"), Field.GetBodies().Num() == static_cast<int32>(Final->GetNumberField(TEXT("bodies"))));
		C.True(Name + TEXT(" final tokens"), Field.TokensHeld() == static_cast<int32>(Final->GetNumberField(TEXT("tokens"))));
		AddInfo(FString::Printf(TEXT("%s: %d frames, %d checks, %d mismatches, first at frame %d"), *Name, Rows.Num(), C.Checks, C.Failures, FirstBad));
	}
	return true;
}

#endif
