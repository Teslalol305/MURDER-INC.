// Replays the golden vectors of tools/ue-export/golden.mjs (Content/Data/golden/*.json: the web game's own modules,
// run in Node) against the C++ rules. Every scenario is the same script, frame by frame; every recorded number must
// match. Web units in the files (metres, radians, +Y up, yaw + = left) are converted here:
// Unreal (X, Y, Z) = (x, z, y) * 100; yaw = -web yaw - 90 degrees; pitch = web pitch; roll = -web roll.

#include "Core/Data/MIDataSubsystem.h"
#include "Core/MIMath.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Misc/AutomationTest.h"
#include "Player/MIPlayerRules.h"
#include "Weapons/MIExplosiveRules.h"
#include "Weapons/MIWeaponRules.h"
#include "Weapons/MILoadoutResolver.h"

#if WITH_AUTOMATION_TESTS

namespace MIGoldenPrivate
{
	/** The parity set-up (frontend.json parity) through FMILoadoutResolver. */
	bool ResolveParity(FAutomationTestBase& Test, FMIResolvedRun& Out)
	{
		FMILoadoutData D;
		TSharedPtr<FJsonObject> Config, Presentation;
		FString Error;
		if (!FMILoadoutData::Load(D, Error) || !FMILoadoutResolver::LoadRoots(Config, Presentation, Error)
			|| !FMILoadoutResolver(D, Config, Presentation).Resolve(D.ParitySetup(TEXT("mission"), TEXT("boss"), TEXT("day")), nullptr, Out, Error))
		{
			Test.AddError(TEXT("parity set-up: ") + Error);
			return false;
		}
		return true;
	}
}

namespace MIGoldenPrivate
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;
	using FJsonArray = TArray<TSharedPtr<FJsonValue>>;

	TSharedPtr<FJsonObject> Load(FAutomationTestBase& Test, const TCHAR* Name)
	{
		TSharedPtr<FJsonObject> Root;
		FString Error;
		if (!UMIDataSubsystem::LoadJsonFile(FString::Printf(TEXT("golden/%s"), Name), Root, Error))
		{
			Test.AddError(FString::Printf(TEXT("golden/%s: %s (run node tools/ue-export/golden.mjs)"), Name, *Error));
			return nullptr;
		}
		return Root;
	}

	bool LoadConfig(FAutomationTestBase& Test, FMIConfigData& Out)
	{
		FString Error;
		if (!UMIDataSubsystem::LoadConfig(Out, Error))
		{
			Test.AddError(FString::Printf(TEXT("config.json: %s"), *Error));
			return false;
		}
		return true;
	}

	const FJsonArray& Arr(const TSharedPtr<FJsonValue>& V) { return V->AsArray(); }
	const FJsonArray& Arr(const TSharedPtr<FJsonObject>& O, const TCHAR* Field) { return O->GetArrayField(Field); }
	double Num(const FJsonArray& A, int32 I) { return A[I]->AsNumber(); }
	bool IsNull(const TSharedPtr<FJsonValue>& V) { return !V.IsValid() || V->IsNull(); }

	/**
	 * The step the scenario ran with. The files hold 1/60 as 0.016666666666666666, and the engine's number parser
	 * can land one unit in the last place away from the double that JavaScript's 1 / 60 is; nine such steps then
	 * cross a 0.15 s hold one frame early. A step within 1e-12 of 1/n is taken as exactly 1.0 / n.
	 */
	double StepOf(const TSharedPtr<FJsonObject>& O)
	{
		const double Dt = O->GetNumberField(TEXT("dt"));
		const double N = FMath::RoundToDouble(1.0 / Dt);
		return N > 0.0 && FMath::Abs(Dt - 1.0 / N) < 1e-12 ? 1.0 / N : Dt;
	}

	/** Web metres (x, y, z) to Unreal centimetres. */
	FVector ToUE(double X, double Y, double Z) { return FVector(X, Z, Y) * 100.0; }
	FVector ToUE(const FJsonArray& A) { return ToUE(Num(A, 0), Num(A, 1), Num(A, 2)); }
	double YawToUE(double WebYaw) { return MI::WrapDegrees(-MI::RadToDeg(WebYaw) - 90.0); }

	/** Counts mismatches and reports the first few of each label. */
	struct FChecker
	{
		FAutomationTestBase& Test;
		FString Context;
		int32 Failures = 0;
		TMap<FString, int32> PerLabel;

		explicit FChecker(FAutomationTestBase& InTest) : Test(InTest) {}

		bool Fail(const FString& Label, const FString& Message)
		{
			++Failures;
			int32& Count = PerLabel.FindOrAdd(Context + TEXT(" ") + Label);
			if (++Count <= 3)
			{
				Test.AddError(FString::Printf(TEXT("%s %s: %s"), *Context, *Label, *Message));
			}
			return false;
		}

		bool Near(const FString& Label, double Actual, double Expected, double Tolerance = 1e-6)
		{
			if (FMath::Abs(Actual - Expected) <= Tolerance * FMath::Max(1.0, FMath::Abs(Expected)))
			{
				return true;
			}
			return Fail(Label, FString::Printf(TEXT("expected %.10g, got %.10g"), Expected, Actual));
		}

		bool NearAngle(const FString& Label, double Actual, double Expected, double Tolerance = 1e-6)
		{
			const double D = MI::WrapDegrees(Actual - Expected);
			if (FMath::Abs(D) <= Tolerance * FMath::Max(1.0, FMath::Abs(Expected)))
			{
				return true;
			}
			return Fail(Label, FString::Printf(TEXT("expected %.10g, got %.10g"), Expected, Actual));
		}

		bool Same(const FString& Label, const FString& Actual, const FString& Expected)
		{
			return Actual == Expected || Fail(Label, FString::Printf(TEXT("expected '%s', got '%s'"), *Expected, *Actual));
		}

		bool Same(const FString& Label, int64 Actual, int64 Expected)
		{
			return Actual == Expected || Fail(Label, FString::Printf(TEXT("expected %lld, got %lld"), Expected, Actual));
		}
	};

	/** A logged event, as golden.mjs writes them: [frame, name, payload]. */
	struct FLogged
	{
		int32 Frame = 0;
		FString Name;
		TMap<FString, FString> Text;
		TMap<FString, double> Numbers;
	};

	FLogged ReadLogged(const TSharedPtr<FJsonValue>& V)
	{
		const FJsonArray& A = V->AsArray();
		FLogged L;
		L.Frame = static_cast<int32>(A[0]->AsNumber());
		L.Name = A[1]->AsString();
		for (const auto& Pair : A[2]->AsObject()->Values)
		{
			const TPair<FString, TSharedPtr<FJsonValue>> Field(FString(*Pair.Key), Pair.Value);
			if (Field.Value->Type == EJson::Number)
			{
				L.Numbers.Add(Field.Key, Field.Value->AsNumber());
			}
			else if (Field.Value->Type == EJson::Boolean)
			{
				L.Numbers.Add(Field.Key, Field.Value->AsBool() ? 1.0 : 0.0);
			}
			else if (Field.Value->Type == EJson::String)
			{
				L.Text.Add(Field.Key, Field.Value->AsString());
			}
		}
		return L;
	}

	void CompareLogs(FChecker& C, const TArray<FLogged>& Actual, const TArray<FLogged>& Expected, TFunctionRef<double(const FString&, double)> ConvertNumber)
	{
		C.Same(TEXT("event count"), Actual.Num(), Expected.Num());
		for (int32 I = 0; I < FMath::Min(Actual.Num(), Expected.Num()); ++I)
		{
			const FLogged& A = Actual[I];
			const FLogged& E = Expected[I];
			const FString Label = FString::Printf(TEXT("event %d (%s at frame %d)"), I, *E.Name, E.Frame);
			if (!C.Same(Label + TEXT(" name"), A.Name, E.Name))
			{
				return;  // out of step: the rest would only repeat the first difference
			}
			C.Same(Label + TEXT(" frame"), A.Frame, E.Frame);
			for (const TPair<FString, FString>& Field : E.Text)
			{
				C.Same(Label + TEXT(" ") + Field.Key, A.Text.FindRef(Field.Key), Field.Value);
			}
			for (const TPair<FString, double>& Field : E.Numbers)
			{
				const double* Got = A.Numbers.Find(Field.Key);
				if (!Got)
				{
					C.Fail(Label + TEXT(" ") + Field.Key, TEXT("missing"));
					continue;
				}
				C.Near(Label + TEXT(" ") + Field.Key, *Got, ConvertNumber(Field.Key, Field.Value));
			}
		}
	}
}

using namespace MIGoldenPrivate;

// ------------------------------------------------------------------------------------------------------ rng

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGoldenRngTest, "MurderInc.Golden.Rng", MIGoldenPrivate::Flags)

bool FMIGoldenRngTest::RunTest(const FString& Parameters)
{
	const TSharedPtr<FJsonObject> Root = Load(*this, TEXT("rng.json"));
	if (!Root)
	{
		return false;
	}
	FChecker C(*this);
	const uint32 Seed = static_cast<uint32>(Root->GetNumberField(TEXT("seed")));
	FMIRng Rng(Seed);
	const FJsonArray& Next = Arr(Root, TEXT("next"));
	for (int32 I = 0; I < Next.Num(); ++I)
	{
		C.Near(FString::Printf(TEXT("next %d"), I), Rng.Next(), Num(Next, I), 1e-11);
	}
	for (const auto& Pair : Root->GetObjectField(TEXT("forks"))->Values)
	{
		const TPair<FString, TSharedPtr<FJsonValue>> Fork(FString(*Pair.Key), Pair.Value);
		FMIRng Child = FMIRng(Seed).Fork(Fork.Key);
		const TSharedPtr<FJsonObject> F = Fork.Value->AsObject();
		C.Same(Fork.Key + TEXT(" seed"), Child.Seed, static_cast<int64>(F->GetNumberField(TEXT("seed"))));
		const FJsonArray& Values = Arr(F, TEXT("next"));
		for (int32 I = 0; I < Values.Num(); ++I)
		{
			C.Near(FString::Printf(TEXT("%s next %d"), *Fork.Key, I), Child.Next(), Num(Values, I), 1e-11);
		}
	}
	return C.Failures == 0;
}

// ------------------------------------------------------------------------------------------------ player: pure

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGoldenPlayerPureTest, "MurderInc.Golden.PlayerPure", MIGoldenPrivate::Flags)

bool FMIGoldenPlayerPureTest::RunTest(const FString& Parameters)
{
	FMIConfigData Config;
	const TSharedPtr<FJsonObject> Root = Load(*this, TEXT("player_pure.json"));
	if (!Root || !LoadConfig(*this, Config))
	{
		return false;
	}
	const FMIPlayerData& P = Config.Player;
	FChecker C(*this);

	C.Context = TEXT("targetSpeed");
	for (const TSharedPtr<FJsonValue>& V : Arr(Root->GetObjectField(TEXT("targetSpeed")), TEXT("cases")))
	{
		const FJsonArray& A = V->AsArray();
		const double Got = MIPlayerRules::TargetSpeed(P.Speed, A[0]->AsBool(), A[1]->AsBool(), Num(A, 2), Num(A, 3));
		C.Near(FString::Printf(TEXT("(%d %d %.2f %.2f)"), A[0]->AsBool(), A[1]->AsBool(), Num(A, 2), Num(A, 3)), Got, Num(A, 4) * 100.0);
	}

	C.Context = TEXT("sprintWanted");
	for (const TSharedPtr<FJsonValue>& V : Arr(Root->GetObjectField(TEXT("sprintWanted")), TEXT("cases")))
	{
		const FJsonArray& A = V->AsArray();
		const bool Got = MIPlayerRules::SprintWanted(P.Sprint, A[0]->AsBool(), Num(A, 1), Num(A, 2), A[3]->AsBool(), Num(A, 4), A[5]->AsBool());
		C.Same(FString::Printf(TEXT("(%.3f %.3f ads %.2f)"), Num(A, 1), Num(A, 2), Num(A, 4)), Got ? 1 : 0, A[6]->AsBool() ? 1 : 0);
	}

	// Velocity space is the horizontal plane: web (x, z) is Unreal (X, Y).
	C.Context = TEXT("approach");
	int32 Case = 0;
	for (const TSharedPtr<FJsonValue>& V : Arr(Root, TEXT("approach")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		const FJsonArray& Vel = Arr(O, TEXT("vel"));
		const FJsonArray& Wish = Arr(O, TEXT("wish"));
		double X = Num(Vel, 0) * 100.0, Y = Num(Vel, 1) * 100.0;
		const double Rate = O->GetNumberField(TEXT("rate")) * 100.0;
		const double Dt = StepOf(O);
		const bool bSnap = O->GetBoolField(TEXT("snap"));
		const FJsonArray& Out = Arr(O, TEXT("out"));
		for (int32 I = 0; I < Out.Num(); ++I)
		{
			MIPlayerRules::ApproachVelocity(X, Y, Num(Wish, 0) * 100.0, Num(Wish, 1) * 100.0, Rate, Dt, bSnap);
			C.Near(FString::Printf(TEXT("case %d step %d x"), Case, I), X, Num(Arr(Out[I]), 0) * 100.0);
			C.Near(FString::Printf(TEXT("case %d step %d y"), Case, I), Y, Num(Arr(Out[I]), 1) * 100.0);
		}
		++Case;
	}

	C.Context = TEXT("recoil");
	{
		FMIRecoil Recoil;
		int32 Step = 0;
		for (const TSharedPtr<FJsonValue>& V : Arr(Root, TEXT("recoil")))
		{
			const TSharedPtr<FJsonObject> O = V->AsObject();
			const TSharedPtr<FJsonValue> Kick = O->TryGetField(TEXT("kick"));
			if (!IsNull(Kick))
			{
				Recoil.Kick(P.Recoil, MI::RadToDeg(Num(Arr(Kick), 0)), -MI::RadToDeg(Num(Arr(Kick), 1)));
			}
			Recoil.Update(P.Recoil, O->GetNumberField(TEXT("dt")));
			const FJsonArray& Out = Arr(O, TEXT("out"));
			C.Near(FString::Printf(TEXT("step %d pitch"), Step), Recoil.Pitch, MI::RadToDeg(Num(Out, 0)));
			C.Near(FString::Printf(TEXT("step %d yaw"), Step), Recoil.Yaw, -MI::RadToDeg(Num(Out, 1)));
			C.Near(FString::Printf(TEXT("step %d targetPitch"), Step), Recoil.TargetPitch, MI::RadToDeg(Num(Out, 2)));
			C.Near(FString::Printf(TEXT("step %d targetYaw"), Step), Recoil.TargetYaw, -MI::RadToDeg(Num(Out, 3)));
			++Step;
		}
	}

	C.Context = TEXT("shake");
	{
		FMIShake Shake;
		int32 Step = 0;
		for (const TSharedPtr<FJsonValue>& V : Arr(Root, TEXT("shake")))
		{
			const TSharedPtr<FJsonObject> O = V->AsObject();
			for (const TSharedPtr<FJsonValue>& Op : Arr(O, TEXT("ops")))
			{
				const FJsonArray& A = Op->AsArray();
				if (A[0]->AsString() == TEXT("add"))
				{
					Shake.Add(P.Shake, Num(A, 1));
				}
				else
				{
					Shake.AtLeast(Num(A, 1));
				}
			}
			Shake.Update(P.Shake, O->GetNumberField(TEXT("dt")));
			const FJsonArray& Out = Arr(O, TEXT("out"));
			C.Near(FString::Printf(TEXT("step %d trauma"), Step), Shake.Trauma, Num(Out, 0));
			C.Near(FString::Printf(TEXT("step %d pitch"), Step), Shake.Pitch, MI::RadToDeg(Num(Out, 1)));
			C.Near(FString::Printf(TEXT("step %d yaw"), Step), Shake.Yaw, -MI::RadToDeg(Num(Out, 2)));
			C.Near(FString::Printf(TEXT("step %d roll"), Step), Shake.Roll, -MI::RadToDeg(Num(Out, 3)));
			++Step;
		}
	}

	C.Context = TEXT("springs");
	for (const TSharedPtr<FJsonValue>& V : Arr(Root, TEXT("springs")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		const FString Name = O->GetStringField(TEXT("name"));
		const TSharedPtr<FJsonObject> Tune = O->GetObjectField(TEXT("tune"));
		const double Stiffness = Tune->GetNumberField(TEXT("stiffness"));
		const double Damping = Tune->GetNumberField(TEXT("damping"));
		const double Min = Tune->GetNumberField(TEXT("min")) * 100.0;
		const double Max = Tune->GetNumberField(TEXT("max")) * 100.0;
		const double Dt = StepOf(O);
		const TSharedPtr<FJsonObject> Kicks = O->GetObjectField(TEXT("kicks"));
		FMIClampedSpring Spring;
		Spring.Offset = O->GetNumberField(TEXT("start")) * 100.0;
		const FJsonArray& Out = Arr(O, TEXT("out"));
		for (int32 I = 0; I < Out.Num(); ++I)
		{
			double Kick = 0.0;
			if (Kicks->TryGetNumberField(FString::FromInt(I), Kick))
			{
				Spring.Kick(Kick * 100.0);
			}
			Spring.Update(Dt, Stiffness, Damping, Min, Max);
			C.Near(FString::Printf(TEXT("%s step %d offset"), *Name, I), Spring.Offset, Num(Arr(Out[I]), 0) * 100.0, 1e-6);
			C.Near(FString::Printf(TEXT("%s step %d velocity"), *Name, I), Spring.Velocity, Num(Arr(Out[I]), 1) * 100.0, 1e-6);
		}
	}
	return C.Failures == 0;
}

// --------------------------------------------------------------------------------------------- player: the whole

namespace MIGoldenPrivate
{
	/**
	 * The web game's moveCapsule on an empty world: the ground plane only (src/physics.js), with the player's two
	 * gravity halves around it (src/player.js update). The character movement component takes this place in the game.
	 */
	FMIBodyResult FlatGroundMove(const FMIPlayerRules& Rules, const FMIBodyMove& Move, double Dt)
	{
		const FMIPlayerData& T = Rules.GetTuning();
		FMIBodyResult Out;
		Out.Feet = Rules.Feet;
		Out.Velocity = Move.Velocity;
		Out.bOnGround = Rules.bOnGround;
		if (!Move.bMove)
		{
			return Out;
		}
		FVector& V = Out.Velocity;
		if (!Move.bDead)
		{
			V.Z = FMath::Max(V.Z - T.Jump.Gravity * Dt * 0.5, -T.Jump.Terminal);
		}
		Out.Feet.X += V.X * Dt;
		Out.Feet.Y += V.Y * Dt;
		const double Floor = 0.0;
		double Z = Out.Feet.Z + V.Z * Dt;
		bool bOnGround = false;
		if (Z <= Floor)
		{
			Z = Floor;
			if (V.Z < 0.0)
			{
				V.Z = 0.0;
			}
			bOnGround = true;
		}
		else if (Move.bAllowStep && V.Z <= 0.0 && Z - Floor <= T.Body.StepHeight)
		{
			Z = Floor;
			V.Z = 0.0;
			bOnGround = true;
		}
		Out.Feet.Z = Z;
		Out.bOnGround = bOnGround;
		if (!Move.bDead && !bOnGround)
		{
			V.Z = FMath::Max(V.Z - T.Jump.Gravity * Dt * 0.5, -T.Jump.Terminal);
		}
		return Out;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGoldenPlayerSimTest, "MurderInc.Golden.PlayerSim", MIGoldenPrivate::Flags)

bool FMIGoldenPlayerSimTest::RunTest(const FString& Parameters)
{
	FMIConfigData Config;
	const TSharedPtr<FJsonObject> Root = Load(*this, TEXT("player_sim.json"));
	if (!Root || !LoadConfig(*this, Config))
	{
		return false;
	}
	FChecker C(*this);
	for (const TSharedPtr<FJsonValue>& SV : Arr(Root, TEXT("scenarios")))
	{
		const TSharedPtr<FJsonObject> S = SV->AsObject();
		C.Context = S->GetStringField(TEXT("name"));
		const double Dt = StepOf(S);

		FMIGameEvents Events;
		TArray<FLogged> Log;
		int32 Frame = 0;
		Events.PlayerStep.AddLambda([&](const FMIPlayerStepEvent& E) { FLogged L{Frame, TEXT("player:step")}; L.Numbers.Add(TEXT("sprint"), E.bSprint ? 1.0 : 0.0); Log.Add(L); });
		Events.PlayerJump.AddLambda([&]() { Log.Add({Frame, TEXT("player:jump")}); });
		Events.PlayerLand.AddLambda([&](const FMIPlayerLandEvent& E) { FLogged L{Frame, TEXT("player:land")}; L.Numbers.Add(TEXT("speed"), E.Speed); Log.Add(L); });
		Events.PlayerHit.AddLambda([&](const FMIPlayerHitEvent& E)
		{
			static const TCHAR* Kinds[] = {TEXT("bullet"), TEXT("bolt"), TEXT("melee"), TEXT("blast"), TEXT("fall")};
			FLogged L{Frame, TEXT("player:hit")};
			L.Numbers.Add(TEXT("amount"), E.Amount);
			L.Numbers.Add(TEXT("health"), E.Health);
			L.Text.Add(TEXT("kind"), Kinds[static_cast<int32>(E.Kind)]);
			Log.Add(L);
		});
		Events.PlayerDead.AddLambda([&](const TOptional<FVector>&) { Log.Add({Frame, TEXT("player:dead")}); });

		FMIPlayerRules Rules;
		Rules.Init(Config.Player, &Events);
		Rules.Reset(ToUE(Arr(S, TEXT("start"))), YawToUE(S->GetNumberField(TEXT("startYaw"))));
		const TSharedPtr<FJsonObject> Regen = S->GetObjectField(TEXT("regen"));
		Rules.RegenDelay = Regen->GetNumberField(TEXT("delay"));
		Rules.RegenRate = Regen->GetNumberField(TEXT("rate"));

		TSet<FString> Held;
		FVector2D Move = FVector2D::ZeroVector;
		const FJsonArray& Inputs = Arr(S, TEXT("inputs"));
		const FJsonArray& Rows = Arr(S, TEXT("rows"));
		for (Frame = 0; Frame < Rows.Num(); ++Frame)
		{
			const TSharedPtr<FJsonObject> In = Inputs[Frame]->AsObject();
			FMIPlayerInputFrame Input;
			bool bJumpEdge = false;
			if (!IsNull(In->TryGetField(TEXT("move"))))
			{
				const FJsonArray& M = Arr(In, TEXT("move"));
				Move = FVector2D(Num(M, 0), Num(M, 1));
			}
			if (!IsNull(In->TryGetField(TEXT("look"))))
			{
				const FJsonArray& L = Arr(In, TEXT("look"));
				Input.LookDegrees = FVector2D(MI::RadToDeg(Num(L, 0)), MI::RadToDeg(Num(L, 1)));
			}
			for (const TSharedPtr<FJsonValue>& H : Arr(In, TEXT("held")))
			{
				const FString Action = H->AsString();
				if (Action.StartsWith(TEXT("-")))
				{
					Held.Remove(Action.Mid(1));
				}
				else
				{
					Held.Add(Action);
					bJumpEdge |= Action == TEXT("jump");
				}
			}
			for (const TSharedPtr<FJsonValue>& Tap : Arr(In, TEXT("taps")))
			{
				bJumpEdge |= Tap->AsString() == TEXT("jump");
			}
			if (!IsNull(In->TryGetField(TEXT("ads"))))
			{
				Rules.Ads = In->GetNumberField(TEXT("ads"));
			}
			if (!IsNull(In->TryGetField(TEXT("damage"))))
			{
				const FJsonArray& D = Arr(In, TEXT("damage"));
				TOptional<FVector> From;
				if (!IsNull(D[1]))
				{
					From = ToUE(Arr(D[1]));
				}
				const FString Kind = D[2]->AsString();
				Rules.Damage(Num(D, 0), From, Kind == TEXT("melee") ? EMIDamageKind::Melee : (Kind == TEXT("fall") ? EMIDamageKind::Fall : EMIDamageKind::Bullet));
			}
			Input.Move = Move;
			Input.bSprintHeld = Held.Contains(TEXT("sprint"));
			Input.bCrouchHeld = Held.Contains(TEXT("crouch"));
			Input.bFireHeld = Held.Contains(TEXT("fire"));
			Input.bJumpPressed = bJumpEdge;

			const FMIBodyMove BodyMove = Rules.BeginFrame(Dt, Input, [] { return true; });
			Rules.EndFrame(Dt, FlatGroundMove(Rules, BodyMove, Dt));
			if (!IsNull(In->TryGetField(TEXT("recoilAfter"))))
			{
				const FJsonArray& K = Arr(In, TEXT("recoilAfter"));
				Rules.AddRecoil(MI::RadToDeg(Num(K, 0)), -MI::RadToDeg(Num(K, 1)));
			}

			const FJsonArray& R = Arr(Rows[Frame]);
			const FString F = FString::Printf(TEXT("frame %d "), Frame);
			const FVector Feet = ToUE(Num(R, 0), Num(R, 1), Num(R, 2));
			const FVector Vel = ToUE(Num(R, 3), Num(R, 4), Num(R, 5));
			const FVector EyeAt = ToUE(Num(R, 13), Num(R, 14), Num(R, 15));
			C.Near(F + TEXT("X"), Rules.Feet.X, Feet.X);
			C.Near(F + TEXT("Y"), Rules.Feet.Y, Feet.Y);
			C.Near(F + TEXT("Z"), Rules.Feet.Z, Feet.Z);
			C.Near(F + TEXT("VX"), Rules.Velocity.X, Vel.X);
			C.Near(F + TEXT("VY"), Rules.Velocity.Y, Vel.Y);
			C.Near(F + TEXT("VZ"), Rules.Velocity.Z, Vel.Z);
			C.Same(F + TEXT("onGround"), Rules.bOnGround ? 1 : 0, static_cast<int64>(Num(R, 6)));
			C.Same(F + TEXT("crouching"), Rules.bCrouching ? 1 : 0, static_cast<int64>(Num(R, 7)));
			C.Same(F + TEXT("sprinting"), Rules.bSprinting ? 1 : 0, static_cast<int64>(Num(R, 8)));
			C.Near(F + TEXT("eyeHeight"), Rules.EyeHeight, Num(R, 9) * 100.0);
			C.Near(F + TEXT("fov"), Rules.ViewFov, Num(R, 10));
			C.Near(F + TEXT("health"), Rules.Health, Num(R, 11));
			C.Near(F + TEXT("stridePhase"), Rules.StridePhase, Num(R, 12));
			C.Near(F + TEXT("eyeX"), Rules.Eye.X, EyeAt.X);
			C.Near(F + TEXT("eyeY"), Rules.Eye.Y, EyeAt.Y);
			C.Near(F + TEXT("eyeZ"), Rules.Eye.Z, EyeAt.Z);
			C.NearAngle(F + TEXT("yaw"), Rules.Yaw, YawToUE(Num(R, 16)));
			C.Near(F + TEXT("pitch"), Rules.Pitch, MI::RadToDeg(Num(R, 17)));
			C.Near(F + TEXT("camPitch"), Rules.CameraRotation.Pitch, MI::RadToDeg(Num(R, 18)));
			C.NearAngle(F + TEXT("camYaw"), Rules.CameraRotation.Yaw, YawToUE(Num(R, 19)));
			C.Near(F + TEXT("camRoll"), Rules.CameraRotation.Roll, -MI::RadToDeg(Num(R, 20)));
			C.Same(F + TEXT("alive"), Rules.bAlive ? 1 : 0, static_cast<int64>(Num(R, 21)));
			C.Near(F + TEXT("hurt"), Rules.Hurt, Num(R, 22));
			C.Near(F + TEXT("lowHealth"), Rules.LowHealth, Num(R, 23));
			C.Near(F + TEXT("trauma"), Rules.GetTrauma(), Num(R, 24));
		}

		TArray<FLogged> Expected;
		for (const TSharedPtr<FJsonValue>& E : Arr(S, TEXT("events")))
		{
			Expected.Add(ReadLogged(E));
		}
		CompareLogs(C, Log, Expected, [](const FString& Key, double V) { return Key == TEXT("speed") ? V * 100.0 : V; });
	}
	return C.Failures == 0;
}

// ----------------------------------------------------------------------------------------------------- weapon

namespace MIGoldenPrivate
{
	/** The scripted player and recording combat of test/weapon-logic.test.js. */
	struct FWeaponHarness : public IMIWeaponHost
	{
		FMIWeaponPlayerState Player;
		double Ads = 0.0;
		bool bStrikeLands = false;
		int32 Frame = 0;
		struct FShot
		{
			int32 Frame = 0;
			double Spread = 0.0;
			double Side = 0.0;
			double Lift = 0.0;
			double Range = 0.0;
			double Damage = 0.0;
			double KickPitch = 0.0;
			double KickYaw = 0.0;
			double Shake = -1.0;
		};
		TArray<FShot> Shots;
		TArray<TPair<int32, double>> Shakes;
		TArray<int32> Strikes;
		const FMIWeaponRules* Rules = nullptr;

		virtual FMIWeaponPlayerState GetPlayerState() const override { return Player; }
		virtual void SetPlayerAds(double InAds) override { Ads = InAds; }
		virtual void AddRecoil(double PitchDeg, double YawDeg) override
		{
			if (Shots.Num() > 0)
			{
				Shots.Last().KickPitch = PitchDeg;
				Shots.Last().KickYaw = YawDeg;
			}
		}
		virtual void AddShake(double Trauma) override
		{
			if (Shots.Num() > 0 && Shots.Last().Frame == Frame && Shots.Last().Shake < 0.0)
			{
				Shots.Last().Shake = Trauma;
			}
			else
			{
				Shakes.Add({Frame, Trauma});
			}
		}
		virtual FMIShotResult Hitscan(const FMIShotRequest& Shot) override
		{
			const FVector Right = FVector::CrossProduct(FVector::UpVector, Player.Forward).GetSafeNormal();
			const FVector Up = FVector::CrossProduct(Player.Forward, Right);
			FShot S;
			S.Frame = Frame;
			S.Spread = Rules->Spread;
			S.Side = FVector::DotProduct(Shot.Direction, Right);
			S.Lift = FVector::DotProduct(Shot.Direction, Up);
			S.Range = Shot.Range;
			S.Damage = Shot.Damage;
			Shots.Add(S);
			FMIShotResult R;
			R.bHit = true;
			R.Distance = 2000.0;
			R.Point = Shot.Origin + Shot.Direction * 2000.0;
			return R;
		}
		virtual EMIStrikeResult Melee(const FMIStrikeRequest& Strike) override
		{
			Strikes.Add(Frame);
			return bStrikeLands ? EMIStrikeResult::Enemy : EMIStrikeResult::None;
		}
		virtual double ProbeWall(const FVector&, const FVector&, double) override { return -1.0; }
		virtual bool AimTarget(const FVector&, const FVector&, double) override { return false; }
	};
}

namespace MIGoldenPrivate
{
/**
 * The 13 weapon scenarios of golden/weapon.json. Weapons: the guns to run (null: config.json's); SwapAs: the web's
 * swap press goes in as bSwapPressed (0), bNextPressed (1) or bPreviousPressed (2) (LOADOUT.md 8.1).
 */
bool ReplayWeaponGolden(FAutomationTestBase& Test, const FMIWeaponsData* Weapons, int32 SwapAs)
{
	FMIConfigData Config;
	const TSharedPtr<FJsonObject> Root = Load(Test, TEXT("weapon.json"));
	if (!Root || !LoadConfig(Test, Config))
	{
		return false;
	}
	FChecker C(Test);
	const uint32 Seed = static_cast<uint32>(Root->GetNumberField(TEXT("seed")));
	for (const TSharedPtr<FJsonValue>& SV : Arr(Root, TEXT("scenarios")))
	{
		const TSharedPtr<FJsonObject> S = SV->AsObject();
		C.Context = S->GetStringField(TEXT("name"));
		const double Dt = StepOf(S);

		FMIGameEvents Events;
		TArray<FLogged> Log;
		FWeaponHarness Host;
		Host.bStrikeLands = S->GetBoolField(TEXT("strikeLands"));
		Host.Player.Eye = ToUE(0.0, 1.68, 0.0);
		Host.Player.Forward = FVector(0.0, -1.0, 0.0);  // web (0, 0, -1): north
		const auto Add = [&](const TCHAR* Name, TFunctionRef<void(FLogged&)> Fill) { FLogged L{Host.Frame, Name}; Fill(L); Log.Add(L); };
		Events.WeaponFire.AddLambda([&](const FMIShotFiredEvent& E) { Add(TEXT("weapon:fire"), [&](FLogged& L) { L.Text.Add(TEXT("weapon"), E.Weapon.ToString()); L.Numbers.Add(TEXT("ads"), E.Ads); }); });
		Events.WeaponDry.AddLambda([&](FName W) { Add(TEXT("weapon:dry"), [&](FLogged& L) { L.Text.Add(TEXT("weapon"), W.ToString()); }); });
		Events.WeaponReload.AddLambda([&](const FMIReloadEvent& E) { Add(TEXT("weapon:reload"), [&](FLogged& L) { L.Text.Add(TEXT("weapon"), E.Weapon.ToString()); L.Text.Add(TEXT("phase"), E.Phase.ToString()); L.Numbers.Add(TEXT("empty"), E.bEmpty ? 1.0 : 0.0); }); });
		Events.WeaponSwitch.AddLambda([&](const FMISwitchEvent& E) { Add(TEXT("weapon:switch"), [&](FLogged& L) { L.Text.Add(TEXT("from"), E.From.ToString()); L.Text.Add(TEXT("to"), E.To.ToString()); L.Text.Add(TEXT("phase"), E.Phase.ToString()); }); });
		Events.WeaponSwing.AddLambda([&](FName W) { Add(TEXT("weapon:swing"), [&](FLogged& L) { L.Text.Add(TEXT("weapon"), W.ToString()); }); });
		Events.WeaponMelee.AddLambda([&](bool bHit) { Add(TEXT("weapon:melee"), [&](FLogged& L) { L.Numbers.Add(TEXT("hit"), bHit ? 1.0 : 0.0); }); });

		FMIWeaponRules Rules;
		Rules.Init(Weapons ? *Weapons : Config.Weapons, Seed, &Events);
		Host.Rules = &Rules;

		TSet<FString> Held;
		const FJsonArray& Inputs = Arr(S, TEXT("inputs"));
		const FJsonArray& Rows = Arr(S, TEXT("rows"));
		for (Host.Frame = 0; Host.Frame < Rows.Num(); ++Host.Frame)
		{
			const TSharedPtr<FJsonObject> In = Inputs[Host.Frame]->AsObject();
			TSet<FString> Edges;
			TSet<FString> Taps;
			for (const TSharedPtr<FJsonValue>& H : Arr(In, TEXT("held")))
			{
				const FString Action = H->AsString();
				if (Action.StartsWith(TEXT("-")))
				{
					Held.Remove(Action.Mid(1));
				}
				else
				{
					if (!Held.Contains(Action))
					{
						Edges.Add(Action);
					}
					Held.Add(Action);
				}
			}
			for (const TSharedPtr<FJsonValue>& T : Arr(In, TEXT("taps")))
			{
				const FString Action = T->AsString();
				if (!Held.Contains(Action))
				{
					Edges.Add(Action);
				}
				Held.Add(Action);
				Taps.Add(Action);
			}
			const TSharedPtr<FJsonValue> PlayerFields = In->TryGetField(TEXT("player"));
			if (!IsNull(PlayerFields))
			{
				const TSharedPtr<FJsonObject> P = PlayerFields->AsObject();
				bool B = false;
				double N = 0.0;
				if (P->TryGetBoolField(TEXT("alive"), B)) Host.Player.bAlive = B;
				if (P->TryGetBoolField(TEXT("sprinting"), B)) Host.Player.bSprinting = B;
				if (P->TryGetBoolField(TEXT("crouching"), B)) Host.Player.bCrouching = B;
				if (P->TryGetBoolField(TEXT("onGround"), B)) Host.Player.bOnGround = B;
				if (P->TryGetNumberField(TEXT("speed"), N)) Host.Player.Speed = N * 100.0;
			}
			// death_drop: the script resets the weapon when the player is alive again.
			if (C.Context == TEXT("death_drop") && Host.Frame == 50)
			{
				Rules.Reset();
			}
			FMIWeaponInput Input;
			Input.bFireDown = Held.Contains(TEXT("fire"));
			Input.bFirePressed = Edges.Contains(TEXT("fire"));
			Input.bAdsDown = Held.Contains(TEXT("ads"));
			Input.bSwapPressed = SwapAs == 0 && Edges.Contains(TEXT("swap"));
			Input.bNextPressed = SwapAs == 1 && Edges.Contains(TEXT("swap"));
			Input.bPreviousPressed = SwapAs == 2 && Edges.Contains(TEXT("swap"));
			Input.bWeapon1Pressed = Edges.Contains(TEXT("weapon1"));
			Input.bWeapon2Pressed = Edges.Contains(TEXT("weapon2"));
			Input.bMeleePressed = Edges.Contains(TEXT("melee"));
			Input.bReloadPressed = Edges.Contains(TEXT("reload"));
			Rules.Update(Dt, Input, Host);
			for (const FString& T : Taps)
			{
				Held.Remove(T);
			}

			const FJsonArray& R = Arr(Rows[Host.Frame]);
			const FString F = FString::Printf(TEXT("frame %d "), Host.Frame);
			C.Same(F + TEXT("current"), Rules.GetCurrentId().ToString(), R[0]->AsString());
			C.Same(F + TEXT("state"), Rules.GetState().ToString(), R[1]->AsString());
			C.Same(F + TEXT("cue"), Rules.GetCue().IsNone() ? FString() : Rules.GetCue().ToString(), R[2]->AsString());
			C.Same(F + TEXT("mag"), Rules.GetMag(), static_cast<int64>(Num(R, 3)));
			C.Same(F + TEXT("reserve"), FMath::IsFinite(Rules.GetReserve()) ? static_cast<int64>(Rules.GetReserve()) : -1, static_cast<int64>(Num(R, 4)));
			C.Near(F + TEXT("spread"), Rules.Spread, MI::RadToDeg(Num(R, 5)));
			C.Near(F + TEXT("ads"), Host.Ads, Num(R, 6));
			C.Near(F + TEXT("adsLinear"), Rules.GetAdsLinear(), Num(R, 7));
			C.Near(F + TEXT("sprint"), Rules.GetSprintBlend(), Num(R, 8));
			C.Same(F + TEXT("otherMag"), Rules.GetMagOf(Rules.GetOtherIndex()), static_cast<int64>(Num(R, 9)));
		}

		const FJsonArray& Shots = Arr(S, TEXT("shots"));
		C.Same(TEXT("rounds"), Host.Shots.Num(), Shots.Num());
		for (int32 I = 0; I < FMath::Min(Shots.Num(), Host.Shots.Num()); ++I)
		{
			const TSharedPtr<FJsonObject> E = Shots[I]->AsObject();
			const FWeaponHarness::FShot& A = Host.Shots[I];
			const FString L = FString::Printf(TEXT("round %d "), I);
			C.Same(L + TEXT("frame"), A.Frame, static_cast<int64>(E->GetNumberField(TEXT("frame"))));
			C.Near(L + TEXT("spread"), A.Spread, MI::RadToDeg(E->GetNumberField(TEXT("spread"))));
			C.Near(L + TEXT("side"), A.Side, E->GetNumberField(TEXT("side")), 1e-7);
			C.Near(L + TEXT("lift"), A.Lift, E->GetNumberField(TEXT("lift")), 1e-7);
			C.Near(L + TEXT("range"), A.Range, E->GetNumberField(TEXT("range")) * 100.0);
			C.Near(L + TEXT("damage"), A.Damage, E->GetNumberField(TEXT("damage")));
			const FJsonArray& Kick = Arr(E, TEXT("kick"));
			C.Near(L + TEXT("kick pitch"), A.KickPitch, MI::RadToDeg(Num(Kick, 0)));
			C.Near(L + TEXT("kick yaw"), A.KickYaw, -MI::RadToDeg(Num(Kick, 1)));
			C.Near(L + TEXT("shake"), A.Shake, E->GetNumberField(TEXT("shake")));
		}
		const FJsonArray& Shakes = Arr(S, TEXT("shakes"));
		C.Same(TEXT("other shakes"), Host.Shakes.Num(), Shakes.Num());
		for (int32 I = 0; I < FMath::Min(Shakes.Num(), Host.Shakes.Num()); ++I)
		{
			C.Same(FString::Printf(TEXT("shake %d frame"), I), Host.Shakes[I].Key, static_cast<int64>(Num(Arr(Shakes[I]), 0)));
			C.Near(FString::Printf(TEXT("shake %d"), I), Host.Shakes[I].Value, Num(Arr(Shakes[I]), 1));
		}
		const FJsonArray& Strikes = Arr(S, TEXT("strikes"));
		C.Same(TEXT("strikes"), Host.Strikes.Num(), Strikes.Num());
		for (int32 I = 0; I < FMath::Min(Strikes.Num(), Host.Strikes.Num()); ++I)
		{
			C.Same(FString::Printf(TEXT("strike %d frame"), I), Host.Strikes[I], static_cast<int64>(Num(Arr(Strikes[I]), 0)));
		}

		TArray<FLogged> Expected;
		for (const TSharedPtr<FJsonValue>& E : Arr(S, TEXT("events")))
		{
			Expected.Add(ReadLogged(E));
		}
		CompareLogs(C, Log, Expected, [](const FString&, double V) { return V; });
	}
	Test.AddInfo(FString::Printf(TEXT("weapon scenarios: %d mismatches"), C.Failures));
	return C.Failures == 0;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGoldenWeaponTest, "MurderInc.Golden.Weapon", MIGoldenPrivate::Flags)

bool FMIGoldenWeaponTest::RunTest(const FString& Parameters)
{
	return MIGoldenPrivate::ReplayWeaponGolden(*this, nullptr, 0);
}

// LOADOUT.md 8.1: the default set-up, through the resolver, replays the web game's weapon scenarios.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutParityGoldenTest, "MurderInc.Loadout.ParityGolden", MIGoldenPrivate::Flags)

bool FMILoadoutParityGoldenTest::RunTest(const FString& Parameters)
{
	FMIResolvedRun Run;
	if (!MIGoldenPrivate::ResolveParity(*this, Run))
	{
		return false;
	}
	return MIGoldenPrivate::ReplayWeaponGolden(*this, &Run.Weapons, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutParityNextPreviousTest, "MurderInc.Loadout.ParityNextPrevious", MIGoldenPrivate::Flags)

bool FMILoadoutParityNextPreviousTest::RunTest(const FString& Parameters)
{
	FMIResolvedRun Run;
	if (!MIGoldenPrivate::ResolveParity(*this, Run))
	{
		return false;
	}
	// Every scenario (switch_reverse and nine_presses among them) with the swap press as next, then as previous.
	const bool bNext = MIGoldenPrivate::ReplayWeaponGolden(*this, &Run.Weapons, 1);
	const bool bPrevious = MIGoldenPrivate::ReplayWeaponGolden(*this, &Run.Weapons, 2);
	return bNext && bPrevious;
}

// ----------------------------------------------------------------------------------------------- explosives, blast

namespace MIGoldenPrivate
{
	struct FBox3
	{
		FVector Min;
		FVector Max;
	};

	/** Segment against boxes (src/physics.js lineOfSight: stops 5 cm short; a box holding the start is ignored). */
	bool LineOfSight(const FVector& A, const FVector& B, const TArray<FBox3>& Boxes)
	{
		const FVector D = B - A;
		const double Length = D.Size();
		if (Length < 1e-6)
		{
			return true;
		}
		const double Reach = Length - 5.0;
		const FVector Dir = D / Length;
		for (const FBox3& Box : Boxes)
		{
			const bool bInside = A.X >= Box.Min.X && A.X <= Box.Max.X && A.Y >= Box.Min.Y && A.Y <= Box.Max.Y && A.Z >= Box.Min.Z && A.Z <= Box.Max.Z;
			if (bInside)
			{
				continue;
			}
			double T0 = 0.0, T1 = Reach;
			bool bHit = true;
			for (int32 Axis = 0; Axis < 3 && bHit; ++Axis)
			{
				if (FMath::Abs(Dir[Axis]) < 1e-12)
				{
					bHit = A[Axis] >= Box.Min[Axis] && A[Axis] <= Box.Max[Axis];
					continue;
				}
				double Ta = (Box.Min[Axis] - A[Axis]) / Dir[Axis];
				double Tb = (Box.Max[Axis] - A[Axis]) / Dir[Axis];
				if (Ta > Tb)
				{
					Swap(Ta, Tb);
				}
				T0 = FMath::Max(T0, Ta);
				T1 = FMath::Min(T1, Tb);
				bHit = T0 <= T1;
			}
			if (bHit)
			{
				return false;
			}
		}
		return true;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGoldenBlastTest, "MurderInc.Golden.Blast", MIGoldenPrivate::Flags)

bool FMIGoldenBlastTest::RunTest(const FString& Parameters)
{
	FMIConfigData Config;
	const TSharedPtr<FJsonObject> Root = Load(*this, TEXT("blast.json"));
	if (!Root || !LoadConfig(*this, Config))
	{
		return false;
	}
	FChecker C(*this);
	const uint32 Seed = static_cast<uint32>(Root->GetNumberField(TEXT("seed")));
	const FMIExplosiveRulesData& Rules = Config.Explosives.Rules;
	// src/combat.js: the player is measured 1.0 m above the feet (0.6 m crouched); a blast of 5 m or more is "big".
	constexpr double PlayerTargetStand = 100.0, PlayerTargetCrouch = 60.0, BigRadius = 500.0;

	for (const TSharedPtr<FJsonValue>& SV : Arr(Root, TEXT("scenarios")))
	{
		const TSharedPtr<FJsonObject> S = SV->AsObject();
		C.Context = S->GetStringField(TEXT("name"));
		const double Dt = StepOf(S);
		int32 Frame = 0;
		TArray<FLogged> Log;
		FMIGameEvents Events;
		Events.ExplosiveLit.AddLambda([&](int32 Index, const FVector&, double Fuse) { FLogged L{Frame, TEXT("explosive:lit")}; L.Numbers.Add(TEXT("item"), Index); L.Numbers.Add(TEXT("fuse"), Fuse); Log.Add(L); });
		Events.ExplosiveBlast.AddLambda([&](int32 Index, const FVector&) { FLogged L{Frame, TEXT("explosive:blast")}; L.Numbers.Add(TEXT("item"), Index); Log.Add(L); });

		FMIExplosiveField Field;
		Field.Init(Config.Explosives, Seed, &Events);
		TArray<FBox3> ItemBoxes;
		for (const TSharedPtr<FJsonValue>& E : Arr(S, TEXT("entries")))
		{
			const FJsonArray& A = E->AsArray();
			const FName Kind(*A[0]->AsString());
			const FVector Foot = ToUE(Num(A, 1), Num(A, 2), Num(A, 3));
			Field.Add(Kind, Foot);
			const FMIExplosiveKindData* K = Config.Explosives.FindKind(Kind);
			FVector Half(K->Box.X * 0.5, K->Box.Y * 0.5, 0.0);
			if (FMath::Abs(FMath::Sin(Num(A, 4))) > 0.7)
			{
				Swap(Half.X, Half.Y);
			}
			ItemBoxes.Add({Foot - Half, Foot + Half + FVector(0.0, 0.0, K->Box.Z)});
		}
		TArray<FBox3> Walls;
		for (const TSharedPtr<FJsonValue>& W : Arr(S, TEXT("walls")))
		{
			const FVector A = ToUE(Arr(Arr(W)[0])), B = ToUE(Arr(Arr(W)[1]));
			Walls.Add({A.ComponentMin(B), A.ComponentMax(B)});
		}
		const TSharedPtr<FJsonObject> PlayerJson = S->GetObjectField(TEXT("player"));
		const FVector PlayerPos = ToUE(Arr(PlayerJson, TEXT("pos")));
		bool bCrouching = false;
		PlayerJson->TryGetBoolField(TEXT("crouching"), bCrouching);
		struct FEnemy
		{
			FVector Pos;
			double Height;
			bool bBuzzard;
		};
		TArray<FEnemy> Enemies;
		for (const TSharedPtr<FJsonValue>& E : Arr(S, TEXT("enemies")))
		{
			const FJsonArray& A = E->AsArray();
			Enemies.Add({ToUE(Num(A, 0), Num(A, 1), Num(A, 2)), Num(A, 3) * 100.0, A.Num() > 4 && A[4]->AsString() == TEXT("buzzard")});
		}

		/** Blockers for a sight line: the walls and every live explosive except the one being reached. */
		const auto Blockers = [&](int32 Except)
		{
			TArray<FBox3> Out = Walls;
			for (int32 I = 0; I < ItemBoxes.Num(); ++I)
			{
				if (I != Except && Field.GetItems()[I].State != EMIExplosiveState::Gone)
				{
					Out.Add(ItemBoxes[I]);
				}
			}
			return Out;
		};
		const auto Explode = [&](const FVector& Centre, double Radius, double Damage, double PlayerScale, int32 Source)
		{
			FLogged E{Frame, TEXT("explosion")};
			E.Numbers.Add(TEXT("radius"), Radius);
			E.Text.Add(TEXT("size"), Radius >= BigRadius ? TEXT("big") : TEXT("small"));
			Log.Add(E);
			Field.OnExplosion(Centre, Radius, Source);
			const TArray<FBox3> Sight = Blockers(INDEX_NONE);
			for (int32 I = Enemies.Num() - 1; I >= 0; --I)
			{
				const FVector Target = Enemies[I].bBuzzard ? Enemies[I].Pos : Enemies[I].Pos + FVector(0.0, 0.0, Enemies[I].Height * 0.5);
				const double Dist = FVector::Dist(Target, Centre);
				if (Dist >= Radius || !LineOfSight(Centre, Target, Sight))
				{
					continue;
				}
				FLogged L{Frame, TEXT("enemy:damage")};
				L.Numbers.Add(TEXT("enemy"), I);
				L.Numbers.Add(TEXT("amount"), Damage * MIBlast::Falloff(Dist, Radius));
				Log.Add(L);
			}
			const FVector PlayerTarget = PlayerPos + FVector(0.0, 0.0, bCrouching ? PlayerTargetCrouch : PlayerTargetStand);
			const double PlayerDist = FVector::Dist(PlayerTarget, Centre);
			if (PlayerDist < Radius && LineOfSight(Centre, PlayerTarget, Sight))
			{
				FLogged L{Frame, TEXT("player:damage")};
				L.Numbers.Add(TEXT("amount"), Damage * PlayerScale * MIBlast::Falloff(PlayerDist, Radius));
				L.Text.Add(TEXT("kind"), TEXT("blast"));
				Log.Add(L);
			}
			for (int32 I = Field.GetItems().Num() - 1; I >= 0; --I)
			{
				const FMIExplosiveItem& Item = Field.GetItems()[I];
				if (I == Source || Item.State == EMIExplosiveState::Gone)
				{
					continue;
				}
				const double Dist = FVector::Dist(Item.Centre(), Centre);
				if (Dist >= Radius || !LineOfSight(Centre, Item.Centre(), Blockers(I)))
				{
					continue;
				}
				Field.Damage(I, Damage * MIBlast::Falloff(Dist, Radius), EMIDamageSource::Blast);
			}
		};

		const FJsonArray& Actions = Arr(S, TEXT("actions"));
		int32 Next = 0;
		const int32 Frames = static_cast<int32>(S->GetNumberField(TEXT("frames")));
		for (Frame = 0; Frame < Frames; ++Frame)
		{
			while (Next < Actions.Num() && static_cast<int32>(Num(Arr(Actions[Next]), 0)) == Frame)
			{
				const FJsonArray& A = Arr(Actions[Next++]);
				if (A[1]->AsString() == TEXT("shoot"))
				{
					Field.Damage(static_cast<int32>(Num(A, 2)), Num(A, 3), A[4]->AsString() == TEXT("player") ? EMIDamageSource::Player : EMIDamageSource::Enemy, true);
				}
				else
				{
					Explode(ToUE(Arr(A[2])), Num(A, 3) * 100.0, Num(A, 4), Rules.PlayerDamageScale, INDEX_NONE);
				}
			}
			Field.Update(Dt, [&](int32 Index)
			{
				const FVector Centre = Field.Blow(Index);
				const FMIExplosiveKindData* K = Field.KindOf(Index);
				Explode(Centre, K->Radius, K->Damage, Rules.PlayerDamageScale, Index);
				const double G = 1.0 - FVector::Dist(PlayerPos, Centre) / Rules.ShakeReach;
				if (G > 0.0)
				{
					FLogged L{Frame, TEXT("player:shake")};
					L.Numbers.Add(TEXT("x"), Config.Player.Shake.BlastBase + Config.Player.Shake.BlastScale * G * G);
					Log.Add(L);
				}
			});
		}

		TArray<FLogged> Expected;
		for (const TSharedPtr<FJsonValue>& E : Arr(S, TEXT("events")))
		{
			Expected.Add(ReadLogged(E));
		}
		CompareLogs(C, Log, Expected, [](const FString& Key, double V) { return Key == TEXT("radius") ? V * 100.0 : V; });
		const FJsonArray& Final = Arr(S, TEXT("final"));
		for (int32 I = 0; I < Final.Num() && I < Field.GetItems().Num(); ++I)
		{
			static const TCHAR* States[] = {TEXT("idle"), TEXT("lit"), TEXT("gone")};
			C.Same(FString::Printf(TEXT("item %d state"), I), States[static_cast<int32>(Field.GetItems()[I].State)], Arr(Final[I])[0]->AsString());
			C.Near(FString::Printf(TEXT("item %d hp"), I), Field.GetItems()[I].Hp, Num(Arr(Final[I]), 1));
		}
	}
	return C.Failures == 0;
}

#endif // WITH_AUTOMATION_TESTS
