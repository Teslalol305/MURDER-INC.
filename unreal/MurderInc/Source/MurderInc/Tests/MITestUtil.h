#pragma once

// Shared helpers of the slice 2 golden tests (MIGoldenWorldTests, MIGoldenEnemyTests, MIGoldenFlowTests).

#include "CoreMinimal.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Misc/AutomationTest.h"

#if WITH_AUTOMATION_TESTS

namespace MITest
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;
	using FJsonArray = TArray<TSharedPtr<FJsonValue>>;

	inline TSharedPtr<FJsonObject> LoadGolden(FAutomationTestBase& Test, const TCHAR* Name)
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

	inline double Num(const FJsonArray& A, int32 I) { return A[I]->AsNumber(); }
	inline bool IsNull(const TSharedPtr<FJsonValue>& V) { return !V.IsValid() || V->IsNull(); }
	inline FVector Vec3(const FJsonArray& A) { return FVector(Num(A, 0), Num(A, 1), Num(A, 2)); }
	inline FVector Vec3(const TSharedPtr<FJsonValue>& V) { return Vec3(V->AsArray()); }
	inline FVector Vec3(const TSharedPtr<FJsonObject>& O)
	{
		return FVector(O->GetNumberField(TEXT("x")), O->GetNumberField(TEXT("y")), O->GetNumberField(TEXT("z")));
	}

	/** 1/60 as JavaScript computes it (the engine's parser can land one unit in the last place away). */
	inline double StepOf(const TSharedPtr<FJsonObject>& O)
	{
		const double Dt = O->GetNumberField(TEXT("dt"));
		const double N = FMath::RoundToDouble(1.0 / Dt);
		return N > 0.0 && FMath::Abs(Dt - 1.0 / N) < 1e-12 ? 1.0 / N : Dt;
	}

	/** Counts mismatches and reports the first few of each label. */
	struct FChecker
	{
		FAutomationTestBase& Test;
		int32 Checks = 0;
		int32 Failures = 0;
		TMap<FString, int32> PerLabel;

		explicit FChecker(FAutomationTestBase& InTest) : Test(InTest) {}

		bool Fail(const FString& Label, const FString& Message)
		{
			++Failures;
			int32& Count = PerLabel.FindOrAdd(Label.Left(40));
			if (++Count <= 3)
			{
				Test.AddError(FString::Printf(TEXT("%s: %s"), *Label, *Message));
			}
			return false;
		}

		bool Near(const FString& Label, double Actual, double Expected, double Tolerance = 1e-6)
		{
			++Checks;
			if (FMath::Abs(Actual - Expected) <= Tolerance * FMath::Max(1.0, FMath::Abs(Expected)))
			{
				return true;
			}
			return Fail(Label, FString::Printf(TEXT("expected %.12g, got %.12g"), Expected, Actual));
		}

		bool True(const FString& Label, bool bOk)
		{
			++Checks;
			return bOk || Fail(Label, TEXT("does not match the web game"));
		}

		bool Same(const FString& Label, const FString& Actual, const FString& Expected)
		{
			++Checks;
			return Actual == Expected || Fail(Label, FString::Printf(TEXT("expected '%s', got '%s'"), *Expected, *Actual));
		}

		void Report(const TCHAR* What)
		{
			Test.AddInfo(FString::Printf(TEXT("%s: %d checks, %d mismatches"), What, Checks, Failures));
		}
	};
}

#endif
