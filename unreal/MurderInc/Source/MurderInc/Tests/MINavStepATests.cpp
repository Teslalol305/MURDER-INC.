// Nav step A (MAPS.md lane N, midtown.md 17.3 and 17.4, chinatown.md 4.4), headless: the maps' level files on the box
// world with a field of Goons and a player who stands still. No window, no GPU, no actors.
//   MurderInc.Levels.Midtown.NavStepA  the roof grids exist; a Goon spawned on each roof layer stays on it, walks to a firing
//                                      cell when the player is in the street and fires from it; a street Goon never leaves
//                                      the street plane when the player is on a roof; a Goon with no way to fight is
//                                      returned to the pool after strandedAfter seconds; spawn reach is the table
//   MurderInc.Levels.Chinatown.RoofHold  roof Goons and street Goons fight a player on the roof and a player in the street:
//                                      both sides fire, nobody is stranded
//   MurderInc.Levels.Block.OneLayer    the Block has one plane layer: no layers, layer 0 everywhere
// The level files are read from tools/levels/data (or Content/Data/level_<id>.json once the loader has moved them); the
// reader here is a small one of its own for the layer data and the points, which the level loader folds in later.

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Enemies/MIEnemies.h"
#include "Enemies/MIEnemyTune.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Tests/MITestUtil.h"
#include "World/MILevelData.h"
#include "World/MINavLayers.h"

#if WITH_AUTOMATION_TESTS

namespace MINavStepAPrivate
{
	constexpr double Dt = 1.0 / 30.0;

	FVector Vec(const TSharedPtr<FJsonObject>& O)
	{
		return FVector(O->GetNumberField(TEXT("x")), O->GetNumberField(TEXT("y")), O->GetNumberField(TEXT("z")));
	}

	/** One level file: what the box world, the spawns and the field need. */
	struct FMap
	{
		FMILevelData Level;
		FMINavSpec Spec;
		TArray<FName> SpawnLayer;  // per Level.Spawns entry
		FMIBoxWorld World;

		bool Load(FAutomationTestBase& T, const FString& Id)
		{
			const FString Name = FString::Printf(TEXT("level_%s.json"), *Id);
			FString Path = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Data"), Name);
			if (!IFileManager::Get().FileExists(*Path))
			{
				Path = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT("../../tools/levels/data"), Name));
			}
			FString Text;
			TSharedPtr<FJsonObject> Root;
			if (!FFileHelper::LoadFileToString(Text, *Path) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid())
			{
				T.AddError(FString::Printf(TEXT("cannot read %s"), *Path));
				return false;
			}
			const TSharedPtr<FJsonObject> B = Root->GetObjectField(TEXT("bounds"))->GetObjectField(TEXT("web"));
			Level.Bounds.MinX = B->GetNumberField(TEXT("minX"));
			Level.Bounds.MaxX = B->GetNumberField(TEXT("maxX"));
			Level.Bounds.MinZ = B->GetNumberField(TEXT("minZ"));
			Level.Bounds.MaxZ = B->GetNumberField(TEXT("maxZ"));
			for (const TSharedPtr<FJsonValue>& V : Root->GetObjectField(TEXT("colliders"))->GetArrayField(TEXT("boxes")))
			{
				const TSharedPtr<FJsonObject> C = V->AsObject();
				if (C->GetObjectField(TEXT("owner"))->GetStringField(TEXT("kind")) == TEXT("truck"))
				{
					continue;
				}
				FMIBox Box;
				Box.Min = Vec(C->GetObjectField(TEXT("web"))->GetObjectField(TEXT("min")));
				Box.Max = Vec(C->GetObjectField(TEXT("web"))->GetObjectField(TEXT("max")));
				Box.Tag = FName(C->GetStringField(TEXT("tag")));
				Box.Surface = FName(C->GetStringField(TEXT("surface")));
				const TSharedPtr<FJsonObject> F = C->GetObjectField(TEXT("flags"));
				Box.bBulletOnly = F->GetBoolField(TEXT("bulletOnly"));
				Box.bPlayerOnly = F->GetBoolField(TEXT("playerOnly"));
				Box.bNoNav = F->GetBoolField(TEXT("noNav"));
				Box.Id = static_cast<int32>(C->GetNumberField(TEXT("index")));
				Level.Colliders.Add(Box);
			}
			auto Points = [&](const TCHAR* Section, TArray<FMILevelPoint>& Out, TArray<FName>* Layers)
			{
				for (const TSharedPtr<FJsonValue>& V : Root->GetObjectField(Section)->GetArrayField(TEXT("points")))
				{
					const TSharedPtr<FJsonObject> O = V->AsObject();
					bool bEnabled = true;
					O->TryGetBoolField(TEXT("enabled"), bEnabled);
					if (!bEnabled)
					{
						continue;
					}
					FMILevelPoint P;
					P.Index = static_cast<int32>(O->GetNumberField(TEXT("index")));
					P.Pos = Vec(O->GetObjectField(TEXT("web"))->GetObjectField(TEXT("pos")));
					P.Zone = FName(O->GetStringField(TEXT("zone")));
					P.Type = FName(TEXT("ground"));
					Out.Add(P);
					if (Layers)
					{
						Layers->Add(FName(O->GetStringField(TEXT("layer"))));
					}
				}
			};
			Points(TEXT("enemySpawns"), Level.Spawns, &SpawnLayer);
			Points(TEXT("coverPoints"), Level.Cover, nullptr);
			Level.PlayerStart.Pos = Vec(Root->GetObjectField(TEXT("playerStart"))->GetObjectField(TEXT("web"))->GetObjectField(TEXT("pos")));
			Level.FillWorld(World, FMIRng(7));
			if (!FMINavSpec::Parse(Root->GetObjectField(TEXT("nav")), Spec))
			{
				T.AddError(TEXT("the level file has no nav layers"));
				return false;
			}
			World.SetNavSpec(Spec);
			return true;
		}

		int32 CountWalkable(int32 Layer)
		{
			int32 N = 0;
			for (int32 J = 0; J < World.NavRows(); ++J)
			{
				for (int32 I = 0; I < World.NavCols(); ++I)
				{
					N += World.NavBlocked(I, J, Layer) ? 0 : 1;
				}
			}
			return N;
		}
		/** Spawns of one layer, as indices into Level.Spawns. */
		TArray<int32> SpawnsOn(FName Layer) const
		{
			TArray<int32> Out;
			for (int32 I = 0; I < SpawnLayer.Num(); ++I)
			{
				if (SpawnLayer[I] == Layer)
				{
					Out.Add(I);
				}
			}
			return Out;
		}
	};

	/**
	 * Where a player could stand in the street (layer 0) so that a Goon on `Layer` has somewhere to fight him from: the street cell
	 * (6 to 26 m from the Goon) that the most roof cells of the Goon's area (within 30 m) can shoot at. False when none can.
	 */
	bool SpotSeenFrom(FMap& M, const FVector& GoonPos, int32 Layer, int32 TargetLayer, FVector& Out, int32& OutSightCells)
	{
		OutSightCells = 0;
		FMIBoxWorld& W = M.World;
		for (double X = GoonPos.X - 40.0; X <= GoonPos.X + 40.0; X += 3.0)
		{
			for (double Z = GoonPos.Z - 40.0; Z <= GoonPos.Z + 40.0; Z += 3.0)
			{
				const double D = FVector::Dist2D(FVector(X, 0, Z), GoonPos);
				if (D < 6.0 || D > 40.0 || !W.IsWalkable(X, Z, TargetLayer))
				{
					continue;
				}
				const FVector Eye(X, M.Spec.Layers[TargetLayer].Y + 1.6, Z);
				int32 Count = 0;
				for (double Cx = GoonPos.X - 30.0; Cx <= GoonPos.X + 30.0; Cx += 1.0)
				{
					for (double Cz = GoonPos.Z - 30.0; Cz <= GoonPos.Z + 30.0; Cz += 1.0)
					{
						if (W.IsWalkable(Cx, Cz, Layer) && W.LineOfSight(FVector(Cx, M.Spec.Layers[Layer].Y + 1.4, Cz), Eye) && W.SameRegion(Layer, GoonPos, FVector(Cx, GoonPos.Y, Cz)))
						{
							++Count;
						}
					}
				}
				if (Count > OutSightCells)
				{
					OutSightCells = Count;
					Out = FVector(X, M.Spec.Layers[TargetLayer].Y, Z);
				}
			}
		}
		return OutSightCells > 0;
	}

	/** Records every round; nobody is hurt. */
	struct FHost : public IMIEnemyHost
	{
		TMap<int32, int32> Rounds;
		virtual FVector Hitscan(int32 EnemyId, const FVector& Origin, const FVector& Dir, double, double) override
		{
			Rounds.FindOrAdd(EnemyId)++;
			return Origin;
		}
		virtual void DamagePlayer(double, const FVector&, FName) override {}
		virtual void Explode(int32, const FVector&, double, double, double) override {}
	};

	struct FFight
	{
		FMap& Map;
		FMIEnemyTune Tune;
		FMIEnemyField Field;
		FHost Host;
		FMIEnemyPlayer Player;
		int32 Recycled = 0;
		bool bLoaded = false;
		/** Per Goon id: the largest distance of his feet from the layer's y (a Goon who fell or was snapped to the street shows here). */
		TMap<int32, double> Drift;
		TMap<int32, int32> LayerOf;

		FFight(FMap& InMap, FAutomationTestBase& T, const FVector& PlayerPos) : Map(InMap)
		{
			FString Error;
			bLoaded = FMIEnemyTune::Load(TEXT("boss"), Tune, Error);
			if (!bLoaded)
			{
				T.AddError(Error);
				return;
			}
			Field.Init(Tune, &Map.Level, &Map.World, &Host);
			Player.Pos = PlayerPos;
			Player.Eye = PlayerPos + FVector(0, 1.6, 0);
			Player.bAlive = true;
		}
		const FMIEnemy* Add(const FVector& At, bool bAlerted = true)
		{
			FMIEnemySpawnOptions O;
			O.bAlerted = bAlerted;
			O.Target = Player.Pos;
			Field.SetLivePlayerPos(Player.Pos);
			const FMIEnemy* E = Field.Spawn(MIEnemy::EType::Goon, At, O);
			if (E)
			{
				LayerOf.Add(E->Id, E->Layer);
			}
			return E;
		}
		void Run(double Seconds)
		{
			for (double T = 0; T < Seconds; T += Dt)
			{
				Field.Update(Dt, Player);
				Field.Events().Reset();
				Recycled += Field.TakeRecycled();
				for (const FMIEnemy& E : Field.GetSlots())
				{
					if (E.bAlive && E.IsGoon() && Map.World.HasLayers())
					{
						double& D = Drift.FindOrAdd(E.Id);
						D = FMath::Max(D, FMath::Abs(E.Pos.Y - Map.Spec.Layers[E.Layer].Y));
					}
				}
			}
		}
		int32 RoundsBy(int32 Id) const { const int32* N = Host.Rounds.Find(Id); return N ? *N : 0; }
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMINavMidtownTest, "MurderInc.Levels.Midtown.NavStepA", MITest::Flags)

bool FMINavMidtownTest::RunTest(const FString& Parameters)
{
	using namespace MINavStepAPrivate;
	FMap M;
	if (!M.Load(*this, TEXT("midtown")))
	{
		return false;
	}
	TestEqual(TEXT("four layers"), M.Spec.Layers.Num(), 4);
	TestTrue(TEXT("the world has layers"), M.World.HasLayers());
	// The grids: the street is as walkable as the plane's rule makes it, every roof layer has floor and is smaller than the street.
	const int32 Street = M.CountWalkable(0);
	TestTrue(TEXT("the street grid has cells"), Street > 2000);
	for (int32 L = 1; L < 4; ++L)
	{
		const int32 N = M.CountWalkable(L);
		AddInfo(FString::Printf(TEXT("layer %s: %d walkable cells (street %d)"), *M.Spec.Layers[L].Id.ToString(), N, Street));
		TestTrue(FString::Printf(TEXT("layer %s has walkable roof"), *M.Spec.Layers[L].Id.ToString()), N > 300);
		TestTrue(FString::Printf(TEXT("layer %s stays inside its rect"), *M.Spec.Layers[L].Id.ToString()), N < Street);
	}
	// Every enabled ground spawn of a layer is on a walkable cell of that layer (within the 4 m snap) and LayerForY agrees with the file.
	int32 Off = 0;
	for (int32 I = 0; I < M.Level.Spawns.Num(); ++I)
	{
		const int32 L = M.World.LayerForY(M.Level.Spawns[I].Pos.Y);
		FVector Near;
		if (M.Spec.Layers[L].Id != M.SpawnLayer[I] || !M.World.NearestWalkable(M.Level.Spawns[I].Pos.X, M.Level.Spawns[I].Pos.Z, 4.0, Near, L))
		{
			++Off;
			AddError(FString::Printf(TEXT("spawn %d (%s) is not on a walkable cell of its layer"), M.Level.Spawns[I].Index, *M.SpawnLayer[I].ToString()));
		}
	}
	TestEqual(TEXT("every spawn is on its layer's grid"), Off, 0);

	// Spawn reach (midtown.md 7.2).
	{
		const TCHAR* Names[4] = {TEXT("street"), TEXT("r1"), TEXT("r2"), TEXT("r3")};
		const FString Want[4] = {TEXT("street r1"), TEXT("r1 r2 street"), TEXT("r1 r2 r3"), TEXT("r2 r3")};
		for (int32 P = 0; P < 4; ++P)
		{
			const int32 PlayerIdx = M.Spec.IndexOf(FName(Names[P]));
			FString Got;
			TArray<FString> Allowed;
			for (int32 S = 0; S < 4; ++S)
			{
				if (M.Spec.Allows(PlayerIdx, M.Spec.IndexOf(FName(Names[S]))))
				{
					Allowed.Add(Names[S]);
				}
			}
			Allowed.Sort();
			TArray<FString> Expected;
			Want[P].ParseIntoArray(Expected, TEXT(" "));
			Expected.Sort();
			TestEqual(FString::Printf(TEXT("spawns allowed while the player is on %s"), Names[P]), FString::Join(Allowed, TEXT(" ")), FString::Join(Expected, TEXT(" ")));
		}
	}

	// A player one layer below, a Goon on each roof layer: he stays on his layer, walks to a firing cell and fires.
	// r1 over the street, r2 over r1, r3 over r2 (a street player is out of the r2 and r3 Goons' reach: the parapets hide him
	// and the nearest sight cell is beyond the firing range, which midtown.md 7.2's spawn reach already keeps them out of).
	struct FPair { const TCHAR* Goon; const TCHAR* Target; };
	const FPair Pairs[3] = {{TEXT("r1"), TEXT("street")}, {TEXT("r2"), TEXT("r1")}, {TEXT("r3"), TEXT("r2")}};
	const TArray<int32> Streets = M.SpawnsOn(FName(TEXT("street")));
	for (const FPair& Pair : Pairs)
	{
		const FName Roof(Pair.Goon);
		const int32 GoonLayer = M.Spec.IndexOf(Roof), TargetLayer = M.Spec.IndexOf(FName(Pair.Target));
		bool bGot = false;
		FVector PlayerPos = FVector::ZeroVector;
		int32 Sight = 0, SpawnIdx = INDEX_NONE;
		for (const int32 R : M.SpawnsOn(Roof))
		{
			int32 Count = 0;
			FVector Spot;
			if (SpotSeenFrom(M, M.Level.Spawns[R].Pos, GoonLayer, TargetLayer, Spot, Count) && Count > Sight)
			{
				Sight = Count;
				PlayerPos = Spot;
				SpawnIdx = R;
				bGot = true;
			}
		}
		if (!TestTrue(FString::Printf(TEXT("%s: a spot on %s that %s cells can shoot at"), Pair.Goon, Pair.Target, Pair.Goon), bGot))
		{
			continue;
		}
		const double BestD = FVector::Dist2D(PlayerPos, M.Level.Spawns[SpawnIdx].Pos);
		AddInfo(FString::Printf(TEXT("%s over %s: the player stands at (%.0f, %.1f, %.0f), %.1f m from the Goon, %d cells see him"), Pair.Goon, Pair.Target, PlayerPos.X, PlayerPos.Y, PlayerPos.Z, BestD, Sight));
		FFight F(M, *this, PlayerPos);
		if (!F.bLoaded)
		{
			return false;
		}
		const FMIEnemy* G = F.Add(M.Level.Spawns[SpawnIdx].Pos);
		if (!TestNotNull(TEXT("the roof Goon spawned"), G))
		{
			continue;
		}
		const int32 Id = G->Id;
		TestEqual(FString::Printf(TEXT("%s Goon's layer"), Pair.Goon), F.Map.Spec.Layers[G->Layer].Id, Roof);
		for (int32 Step = 0; Step < 9; ++Step)
		{
			F.Run(5.0);
			if (const FMIEnemy* S = F.Field.Find(Id))
			{
				FString Path;
				for (const FVector& P : S->Path)
				{
					Path += FString::Printf(TEXT("(%.1f,%.1f) "), P.X, P.Z);
				}
				AddInfo(FString::Printf(TEXT("  %s t=%d: (%.1f, %.1f) mode %d sub %d goal %d (%.1f, %.1f) hasPath %d idx %d fails %d stuck %.1f/%d sees %d rounds %d path %s"), Pair.Goon, (Step + 1) * 5, S->Pos.X, S->Pos.Z, static_cast<int32>(S->Mode), static_cast<int32>(S->Sub),
					S->bHasGoal, S->GoalX, S->GoalZ, S->bHasPath, S->PathIndex, S->PathFails, S->Stuck, S->StuckCount, S->bSees, F.RoundsBy(Id), *Path));
			}
		}
		const FMIEnemy* After = F.Field.Find(Id);
		AddInfo(FString::Printf(TEXT("%s: %d rounds, drift %.2f m, recycled %d; end: (%.1f, %.1f, %.1f) mode %d sub %d firePos %d (%.1f, %.1f) sees %d pathFails %d"), Pair.Goon, F.RoundsBy(Id), F.Drift.FindRef(Id), F.Recycled,
			After ? After->Pos.X : 0.0, After ? After->Pos.Y : 0.0, After ? After->Pos.Z : 0.0, After ? static_cast<int32>(After->Mode) : -1, After ? static_cast<int32>(After->Sub) : -1,
			After ? After->bHasFirePos : 0, After ? After->GoalFireX : 0.0, After ? After->GoalFireZ : 0.0, After ? After->bSees : 0, After ? After->PathFails : 0));
		TestTrue(FString::Printf(TEXT("%s Goon stayed on his layer's floor"), Pair.Goon), F.Drift.FindRef(Id) < 0.6);
		TestTrue(FString::Printf(TEXT("%s Goon fires at the player on %s (a firing cell)"), Pair.Goon, Pair.Target), F.RoundsBy(Id) > 0);
		TestEqual(FString::Printf(TEXT("%s Goon was not stranded"), Pair.Goon), F.Recycled, 0);
	}

	// A player on r1, a street Goon: he stays on the plane and in free street cells.
	{
		const TArray<int32> R1 = M.SpawnsOn(FName(TEXT("r1")));
		if (TestTrue(TEXT("r1 has spawns"), R1.Num() > 0 && Streets.Num() > 0))
		{
			FVector PlayerPos = M.Level.Spawns[R1[0]].Pos;
			int32 Near = Streets[0];
			for (const int32 S : Streets)
			{
				if (FVector::Dist2D(M.Level.Spawns[S].Pos, PlayerPos) < FVector::Dist2D(M.Level.Spawns[Near].Pos, PlayerPos))
				{
					Near = S;
				}
			}
			FFight F(M, *this, PlayerPos);
			const FMIEnemy* G = F.Add(M.Level.Spawns[Near].Pos);
			if (TestNotNull(TEXT("the street Goon spawned"), G))
			{
				const int32 Id = G->Id;
				bool bUnderRoof = false;
				for (double T = 0; T < 40.0; T += Dt)
				{
					F.Run(Dt);
					const FMIEnemy* E = F.Field.Find(Id);
					if (E && E->bAlive && !M.World.IsWalkable(E->Pos.X, E->Pos.Z, 0))
					{
						bUnderRoof = true;
					}
				}
				TestEqual(TEXT("the street Goon is on the street layer"), F.LayerOf.FindRef(Id), 0);
				TestTrue(TEXT("the street Goon never leaves the street plane"), F.Drift.FindRef(Id) < 0.6);
				TestFalse(TEXT("the street Goon never stands on a street cell that is blocked (a building footprint)"), bUnderRoof);
			}
		}
	}

	// Stranded: a player far from every roof cell (the plaza's far end): a roof Goon has no firing cell, holds, and is returned.
	{
		const TArray<int32> R3 = M.SpawnsOn(FName(TEXT("r3")));
		FVector Far = M.Level.Spawns[Streets[0]].Pos;
		for (const int32 S : Streets)
		{
			if (FVector::Dist2D(M.Level.Spawns[S].Pos, M.Level.Spawns[R3[0]].Pos) > FVector::Dist2D(Far, M.Level.Spawns[R3[0]].Pos))
			{
				Far = M.Level.Spawns[S].Pos;
			}
		}
		Far.Y = 0.0;
		FFight F(M, *this, Far);
		const FMIEnemy* G = F.Add(M.Level.Spawns[R3[0]].Pos);
		if (TestNotNull(TEXT("the stranded Goon spawned"), G))
		{
			F.Run(5.0);
			TestEqual(TEXT("not returned after 5 s"), F.Recycled, 0);
			F.Run(25.0);
			AddInfo(FString::Printf(TEXT("stranded: player %.0f m from the Goon: recycled %d"), FVector::Dist2D(Far, M.Level.Spawns[R3[0]].Pos), F.Recycled));
			TestEqual(TEXT("returned to the pool within 30 s, once"), F.Recycled, 1);
			TestEqual(TEXT("no Goon is left alive"), F.Field.AliveCount(), 0);
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMINavChinatownTest, "MurderInc.Levels.Chinatown.RoofHold", MITest::Flags)

bool FMINavChinatownTest::RunTest(const FString& Parameters)
{
	using namespace MINavStepAPrivate;
	FMap M;
	if (!M.Load(*this, TEXT("chinatown")))
	{
		return false;
	}
	TestEqual(TEXT("two layers"), M.Spec.Layers.Num(), 2);
	const int32 Street = M.CountWalkable(0), Roof = M.CountWalkable(1);
	AddInfo(FString::Printf(TEXT("chinatown: street %d walkable cells, roof %d"), Street, Roof));
	TestTrue(TEXT("the roof has floor"), Roof > 300);
	// The roof spawns are switched off in the file until step A lands (enabled false): switch them on for this test.
	TArray<FVector> RoofSpots = {FVector(-21.4, 5.7, 8.0), FVector(-4.0, 5.7, -12.4), FVector(-24.0, 5.7, -5.0)};
	TArray<FVector> StreetSpots;
	for (int32 I = 0; I < M.Level.Spawns.Num(); ++I)
	{
		if (M.SpawnLayer[I] == FName(TEXT("street")) && StreetSpots.Num() < 4 && FVector::Dist2D(M.Level.Spawns[I].Pos, RoofSpots[0]) < 30.0 && FVector::Dist2D(M.Level.Spawns[I].Pos, RoofSpots[0]) > 8.0)
		{
			StreetSpots.Add(M.Level.Spawns[I].Pos);
		}
	}
	if (!TestTrue(TEXT("street spawns near the market"), StreetSpots.Num() >= 2))
	{
		return false;
	}
	for (const FVector& Spot : RoofSpots)
	{
		FVector Cell;
		TestTrue(TEXT("a roof spawn is on a walkable roof cell"), M.World.NearestWalkable(Spot.X, Spot.Z, 4.0, Cell, 1));
	}
	struct FCase { const TCHAR* Name; FVector Player; };
	// The roof player stands at the roof cell nearest the first street spot (the parapet over the street), so the street can see him.
	FVector RoofEdge = FVector(-15.0, 5.7, -4.0);
	{
		FVector Cell;
		if (M.World.NearestWalkable(StreetSpots[0].X, StreetSpots[0].Z, 40.0, Cell, 1))
		{
			RoofEdge = FVector(Cell.X, 5.7, Cell.Z);
		}
	}
	const FCase Cases[2] = {{TEXT("player on the roof"), RoofEdge}, {TEXT("player in the street"), StreetSpots[0]}};
	for (const FCase& C : Cases)
	{
		FVector P = C.Player;
		FFight F(M, *this, P);
		if (!F.bLoaded)
		{
			return false;
		}
		TArray<int32> Ids;
		for (const FVector& R : RoofSpots)
		{
			if (const FMIEnemy* E = F.Add(R))
			{
				Ids.Add(E->Id);
			}
		}
		const int32 RoofCount = Ids.Num();
		for (int32 I = 0; I < StreetSpots.Num(); ++I)
		{
			if (const FMIEnemy* E = F.Add(StreetSpots[I]))
			{
				Ids.Add(E->Id);
			}
		}
		F.Run(50.0);
		int32 RoofRounds = 0, StreetRounds = 0, Drifted = 0;
		for (int32 I = 0; I < Ids.Num(); ++I)
		{
			(I < RoofCount ? RoofRounds : StreetRounds) += F.RoundsBy(Ids[I]);
			Drifted += F.Drift.FindRef(Ids[I]) > 0.6 ? 1 : 0;
		}
		AddInfo(FString::Printf(TEXT("%s: roof Goons %d rounds, street Goons %d rounds, recycled %d, drifted %d"), C.Name, RoofRounds, StreetRounds, F.Recycled, Drifted));
		TestTrue(FString::Printf(TEXT("%s: the roof Goons fire"), C.Name), RoofRounds > 0);
		TestTrue(FString::Printf(TEXT("%s: the street Goons fire"), C.Name), StreetRounds > 0);
		TestEqual(FString::Printf(TEXT("%s: nobody is stranded"), C.Name), F.Recycled, 0);
		TestEqual(FString::Printf(TEXT("%s: nobody left his layer"), C.Name), Drifted, 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMINavBlockTest, "MurderInc.Levels.Block.OneLayer", MITest::Flags)

bool FMINavBlockTest::RunTest(const FString& Parameters)
{
	const FMILevelData* Level = FMILevelData::Get();
	if (!TestNotNull(TEXT("the Block's level data"), Level))
	{
		return false;
	}
	FMIBoxWorld World;
	Level->FillWorld(World, FMIRng(1));
	TestFalse(TEXT("the Block has no nav layers"), World.HasLayers());
	TestEqual(TEXT("one layer"), World.NumLayers(), 1);
	TestEqual(TEXT("a spawn is on layer 0"), World.LayerForY(Level->Spawns[0].Pos.Y), 0);
	TestEqual(TEXT("the player is on layer 0"), World.LayerAt(Level->PlayerStart.Pos), 0);
	return true;
}

#endif
