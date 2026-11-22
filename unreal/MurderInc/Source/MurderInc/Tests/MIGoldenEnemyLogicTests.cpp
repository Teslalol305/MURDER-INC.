// MurderInc.Golden.EnemyLogic: Enemies/MIEnemyLogic (the port of src/enemies/logic.js) against golden/enemy_logic.json.

#include "Enemies/MIEnemyLogic.h"
#include "Tests/MITestUtil.h"

#if WITH_AUTOMATION_TESTS

using namespace MITest;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGoldenEnemyLogicTest, "MurderInc.Golden.EnemyLogic", MITest::Flags)

bool FMIGoldenEnemyLogicTest::RunTest(const FString& Parameters)
{
	const TSharedPtr<FJsonObject> G = LoadGolden(*this, TEXT("enemy_logic.json"));
	FMIEnemyTune Tune;
	FString Error;
	if (!FMIEnemyTune::Load(TEXT("boss"), Tune, Error))
	{
		AddError(Error);
		return false;
	}
	if (!G)
	{
		return false;
	}
	FChecker C(*this);
	using namespace MIEnemy;
	const FMIAiTune& Ai = Tune.Ai;
	const FMIGoonTune& Goon = Tune.Goon;

	FTokens Tokens;
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("tokens")))
	{
		const FJsonArray& A = V->AsArray();
		const EType Type = A[1]->AsString() == TEXT("goon") ? EType::Goon : EType::Buzzard;
		if (A[0]->AsString() == TEXT("request"))
		{
			C.True(TEXT("token request"), Tokens.Request(Type, Num(A, 2), static_cast<int32>(Num(A, 3)), Ai) == A[4]->AsBool());
		}
		else
		{
			Tokens.Release();
		}
		C.True(TEXT("tokens held"), Tokens.Held == static_cast<int32>(Num(A, 5)));
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("sight")))
	{
		const FJsonArray& A = V->AsArray();
		C.True(TEXT("inSight"), InSight(Num(A, 0), Num(A, 1), Num(A, 2), Num(A, 3), A[4]->AsBool(), Ai) == A[5]->AsBool());
		C.True(TEXT("inFov"), InFov(Num(A, 3), Num(A, 1), Num(A, 2), Ai.Fov) == A[6]->AsBool());
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("accum")))
	{
		const FJsonArray& A = V->AsArray();
		C.Near(TEXT("seenStep"), SeenStep(Num(A, 0), A[1]->AsBool(), Num(A, 2), Ai), Num(A, 6), 1e-10);
		C.Near(TEXT("exposureStep"), ExposureStep(Num(A, 3), A[1]->AsBool(), Num(A, 4), Ai), Num(A, 7), 1e-10);
		C.Near(TEXT("reactionTime"), ReactionTime(Goon.Reaction, A[5]->AsString() == TEXT("patrol"), Ai), Num(A, 8), 1e-10);
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("spread")))
	{
		const FJsonArray& A = V->AsArray();
		C.Near(TEXT("aimSpread"), AimSpread(Num(A, 0), Num(A, 1), Num(A, 2), Num(A, 3), Num(A, 4), Num(A, 5)), Num(A, 6), 1e-10);
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("cost")))
	{
		const FJsonArray& A = V->AsArray();
		const TSharedPtr<FJsonObject>& Co = A[0]->AsObject();
		FCandidate Cand;
		Cand.X = Co->GetNumberField(TEXT("x"));
		Cand.Z = Co->GetNumberField(TEXT("z"));
		const FString Kind = Co->GetStringField(TEXT("kind"));
		Cand.Kind = Kind == TEXT("authored") ? ECandidate::Authored : (Kind == TEXT("random") ? ECandidate::Random : ECandidate::Arc);
		Cand.bSight = Co->GetBoolField(TEXT("sight"));
		Cand.bCover = Co->GetBoolField(TEXT("cover"));
		TArray<FOther> Others;
		for (const TSharedPtr<FJsonValue>& O : A[3]->AsArray())
		{
			const TSharedPtr<FJsonObject>& Oo = O->AsObject();
			Others.Add({Oo->GetNumberField(TEXT("x")), Oo->GetNumberField(TEXT("z")), Oo->GetNumberField(TEXT("destX")), Oo->GetNumberField(TEXT("destZ"))});
		}
		const TSharedPtr<FJsonObject>& S = A[1]->AsObject();
		const TSharedPtr<FJsonObject>& P = A[2]->AsObject();
		C.Near(TEXT("firePositionCost"), FirePositionCost(Cand, S->GetNumberField(TEXT("x")), S->GetNumberField(TEXT("z")), P->GetNumberField(TEXT("x")), P->GetNumberField(TEXT("z")), Others, Num(A, 4), Goon), Num(A, 5), 1e-10);
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("follow")))
	{
		const FJsonArray& A = V->AsArray();
		C.Near(TEXT("followSpeed"), FollowSpeed(Num(A, 0), Num(A, 1), Num(A, 2), Goon), Num(A, 3), 1e-10);
	}
	auto Hit = [](double T) { return T == Inf ? -1.0 : T; };
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("rays")))
	{
		const FJsonArray& A = V->AsArray();
		const FVector O = Vec3(A[0]), D = Vec3(A[1]);
		C.Near(TEXT("raySphere"), Hit(RaySphere(O, D, FVector(0, 1.6, 0), 0.155)), Num(A, 2), 1e-9);
		C.Near(TEXT("rayCapsule"), Hit(RayCapsule(O, D, FVector(0, 0.8, 0), FVector(0.1, 1.5, 0.05), 0.27)), Num(A, 3), 1e-9);
		C.Near(TEXT("rayEllipsoid"), Hit(RayEllipsoid(O, D, FVector(0, 1, 0), 0.5, 0.22)), Num(A, 4), 1e-9);
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("upright")))
	{
		const FJsonArray& A = V->AsArray();
		C.Near(TEXT("segmentHitsUpright"), SegmentHitsUpright(Vec3(A[0]), Vec3(A[1]), 0, 0.1, 1.75, 0, 0.42), Num(A, 2), 1e-9);
	}
	for (const TSharedPtr<FJsonValue>& V : G->GetArrayField(TEXT("lead")))
	{
		const FJsonArray& A = V->AsArray();
		const FVector P = LeadPoint(Vec3(A[0]), Vec3(A[1]), Vec3(A[2]), 70.0, Num(A, 3));
		const FVector Out = Vec3(A[4]);
		C.Near(TEXT("leadPoint"), (P - Out).Size(), 0.0, 1e-8);
	}
	C.Report(TEXT("enemy logic"));
	return true;
}

#endif
