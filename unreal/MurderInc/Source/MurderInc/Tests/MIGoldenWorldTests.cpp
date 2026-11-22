// MurderInc.Golden.World: the box world (World/MIBoxWorld, the port of src/physics.js) filled with level.json's
// colliders against golden/world.json, which the web game's own physics produced from the same list: rays, sight
// lines, floors, a capsule walking over the block, the nav grid cell for cell, paths, straight lines, random points.

#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Misc/AutomationTest.h"
#include "Tests/MITestUtil.h"
#include "World/MIBoxWorld.h"
#include "World/MILevelData.h"

#if WITH_AUTOMATION_TESTS

using namespace MITest;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGoldenWorldTest, "MurderInc.Golden.World", MITest::Flags)

bool FMIGoldenWorldTest::RunTest(const FString& Parameters)
{
	const TSharedPtr<FJsonObject> G = LoadGolden(*this, TEXT("world.json"));
	const FMILevelData* Level = FMILevelData::Get();
	TestNotNull(TEXT("level.json"), Level);
	if (!G || !Level)
	{
		return false;
	}
	FChecker C(*this);
	FMIBoxWorld W;
	Level->FillWorld(W, FMIRng(static_cast<uint32>(G->GetNumberField(TEXT("seed")))));

	// The grid equals level.json nav (the web game's, exported).
	{
		TSharedPtr<FJsonObject> Root;
		FString Error;
		if (UMIDataSubsystem::LoadJsonFile(TEXT("level.json"), Root, Error))
		{
			const TSharedPtr<FJsonObject>& Nav = Root->GetObjectField(TEXT("nav"));
			const FJsonArray& Rows = Nav->GetObjectField(TEXT("grid"))->GetArrayField(TEXT("cells"));
			TestEqual(TEXT("nav cols"), W.NavCols(), static_cast<int32>(Nav->GetNumberField(TEXT("cols"))));
			TestEqual(TEXT("nav rows"), W.NavRows(), Rows.Num());
			int32 Diff = 0;
			for (int32 J = 0; J < FMath::Min(Rows.Num(), W.NavRows()); ++J)
			{
				const FString Row = Rows[J]->AsString();
				for (int32 I = 0; I < FMath::Min(Row.Len(), W.NavCols()); ++I)
				{
					Diff += (Row[I] == TEXT('#')) != W.NavBlocked(I, J) ? 1 : 0;
				}
			}
			TestEqual(TEXT("nav cells that differ from level.json"), Diff, 0);
		}
	}

	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("rays")))
	{
		const FJsonArray& A = V->AsArray();
		FMIRayHit Hit;
		const bool bHit = W.Raycast(Vec3(A[0]), Vec3(A[1]), 40.0, Hit);
		const bool bWant = !IsNull(A[2]);
		C.True(TEXT("ray hits"), bHit == bWant);
		if (bHit && bWant)
		{
			const FJsonArray& H = A[2]->AsArray();
			C.Near(TEXT("ray dist"), Hit.Dist, Num(H, 0), 1e-7);
			C.Near(TEXT("ray normal"), (Hit.Normal - FVector(Num(H, 1), Num(H, 2), Num(H, 3))).Size(), 0.0, 1e-9);
			C.True(TEXT("ray box"), Hit.Box == static_cast<int32>(Num(H, 4)));
		}
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("sight")))
	{
		const FJsonArray& A = V->AsArray();
		C.True(TEXT("sight"), W.LineOfSight(Vec3(A[0]), Vec3(A[1])) == A[2]->AsBool());
		C.True(TEXT("sight movement"), W.LineOfSight(Vec3(A[0]), Vec3(A[1]), true) == A[3]->AsBool());
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("ground")))
	{
		const FJsonArray& A = V->AsArray();
		C.Near(TEXT("ground"), W.GroundHeight(Num(A, 0), Num(A, 1), Num(A, 2)), Num(A, 3), 1e-9);
		C.True(TEXT("overlaps"), W.OverlapsCylinder(Num(A, 0), Num(A, 1), 0.3, 0.1, 1.8) == A[4]->AsBool());
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("walks")))
	{
		const TSharedPtr<FJsonObject>& O = V->AsObject();
		const FString Name = O->GetStringField(TEXT("name"));
		FVector Pos = Vec3(O->GetField<EJson::Array>(TEXT("start")));
		Pos.Y = W.GroundHeight(Pos.X, Pos.Z, Pos.Y + 0.6);
		FVector Vel = FVector::ZeroVector;
		bool bOnGround = true;
		const double Dt = StepOf(O);
		const double Gravity = O->GetNumberField(TEXT("gravity"));
		int32 Frame = 0;
		for (const TSharedPtr<FJsonValue>& R : O->GetArrayField(TEXT("out")))
		{
			const FJsonArray& A = R->AsArray();
			Vel.X = Num(A, 0);
			Vel.Z = Num(A, 1);
			Vel.Y = bOnGround ? 0.0 : Vel.Y - Gravity * Dt;
			const FMIMoveResult M = W.MoveCapsule(Pos, Vel, Dt, O->GetNumberField(TEXT("radius")), O->GetNumberField(TEXT("height")), bOnGround);
			bOnGround = M.bOnGround;
			const FString F = FString::Printf(TEXT("walk %s frame %d "), *Name, Frame++);
			C.Near(F + TEXT("pos"), (Pos - FVector(Num(A, 2), Num(A, 3), Num(A, 4))).Size(), 0.0, 1e-7);
			C.Near(F + TEXT("vel"), (Vel - FVector(Num(A, 5), Num(A, 6), Num(A, 7))).Size(), 0.0, 1e-7);
			C.True(F + TEXT("ground"), M.bOnGround == (Num(A, 8) != 0.0));
			C.True(F + TEXT("wall"), M.bHitWall == (Num(A, 9) != 0.0));
		}
	}
	TArray<FVector> Path;
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("paths")))
	{
		const FJsonArray& A = V->AsArray();
		const bool bFound = W.FindPath(Vec3(A[0]), Vec3(A[1]), Path);
		C.True(TEXT("path found"), bFound == !IsNull(A[2]));
		if (bFound && !IsNull(A[2]))
		{
			const FJsonArray& P = A[2]->AsArray();
			C.True(FString::Printf(TEXT("path length %d vs %d"), Path.Num(), P.Num()), Path.Num() == P.Num());
			for (int32 I = 0; I < FMath::Min(Path.Num(), P.Num()); ++I)
			{
				C.Near(TEXT("path point x"), Path[I].X, Num(P[I]->AsArray(), 0), 1e-9);
				C.Near(TEXT("path point z"), Path[I].Z, Num(P[I]->AsArray(), 1), 1e-9);
			}
		}
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("lines")))
	{
		const FJsonArray& A = V->AsArray();
		C.True(TEXT("clear line"), W.ClearLine(Vec3(A[0]), Vec3(A[1])) == A[2]->AsBool());
		C.True(TEXT("walkable"), W.IsWalkable(Vec3(A[0]).X, Vec3(A[0]).Z) == A[3]->AsBool());
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("randoms")))
	{
		const FJsonArray& A = V->AsArray();
		FVector P;
		const bool bGot = W.RandomPoint(Vec3(A[0]), Num(A, 1), P);
		C.True(TEXT("random point found"), bGot == !IsNull(A[2]));
		if (bGot && !IsNull(A[2]))
		{
			C.Near(TEXT("random x"), P.X, Num(A[2]->AsArray(), 0), 1e-9);
			C.Near(TEXT("random z"), P.Z, Num(A[2]->AsArray(), 1), 1e-9);
		}
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("snaps")))
	{
		const FJsonArray& A = V->AsArray();
		FVector P;
		const bool bGot = W.NearestWalkable(Num(A, 0), Num(A, 1), Num(A, 2), P);
		C.True(TEXT("snap found"), bGot == !IsNull(A[3]));
		if (bGot && !IsNull(A[3]))
		{
			C.Near(TEXT("snap x"), P.X, Num(A[3]->AsArray(), 0), 1e-9);
			C.Near(TEXT("snap z"), P.Z, Num(A[3]->AsArray(), 1), 1e-9);
		}
	}
	C.Report(TEXT("world"));
	return true;
}

#endif
