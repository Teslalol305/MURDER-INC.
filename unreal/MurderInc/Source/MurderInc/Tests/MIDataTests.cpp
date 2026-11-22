#include "Core/Data/MIDataSubsystem.h"
#include "Flow/MIGameMode.h"
#include "InputMappingContext.h"
#include "Misc/AutomationTest.h"
#include "Player/MIPlayerCharacter.h"
#include "Player/MIPlayerController.h"

#if WITH_AUTOMATION_TESTS

namespace MIDataTestsPrivate
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;

	bool Near(FAutomationTestBase& Test, const TCHAR* What, double Actual, double Expected, double Tolerance = 0.01)
	{
		const bool bOk = FMath::IsNearlyEqual(Actual, Expected, Tolerance);
		if (!bOk)
		{
			Test.AddError(FString::Printf(TEXT("%s: expected %.4f, got %.4f"), What, Expected, Actual));
		}
		return bOk;
	}
}

/**
 * Content/Data/config.json loads from disk and its player table arrives in Unreal units.
 * The expected numbers are the web game's (src/config/player.js; docs/unreal/spec/01-player.md section 2).
 */
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIDataLoadsTest, "MurderInc.Core.DataLoads", MIDataTestsPrivate::Flags)

bool FMIDataLoadsTest::RunTest(const FString& Parameters)
{
	using namespace MIDataTestsPrivate;

	FMIConfigData Config;
	FString Error;
	if (!UMIDataSubsystem::LoadConfig(Config, Error))
	{
		AddError(FString::Printf(TEXT("config.json did not load: %s"), *Error));
		return false;
	}

	TestEqual(TEXT("meta.game"), Config.Game, FString(TEXT("MURDER INC.")));
	TestEqual(TEXT("meta.schema"), Config.Schema, 1);
	TestEqual(TEXT("meta.seed"), Config.Seed, 1994);

	const FMIPlayerData& P = Config.Player;
	Near(*this, TEXT("body.radius 0.32 m in cm"), P.Body.Radius, 32.0);
	Near(*this, TEXT("body.height 1.8 m in cm"), P.Body.Height, 180.0);
	Near(*this, TEXT("body.crouchHeight 1.15 m in cm"), P.Body.CrouchHeight, 115.0);
	Near(*this, TEXT("body.eye 1.68 m in cm"), P.Body.Eye, 168.0);
	Near(*this, TEXT("body.crouchEye 1.05 m in cm"), P.Body.CrouchEye, 105.0);
	Near(*this, TEXT("body.stepHeight 0.42 m in cm"), P.Body.StepHeight, 42.0);
	Near(*this, TEXT("speed.walk 3.8 m/s in cm/s"), P.Speed.Walk, 380.0);
	Near(*this, TEXT("speed.sprint 6.4 m/s in cm/s"), P.Speed.Sprint, 640.0);
	Near(*this, TEXT("speed.crouch 1.9 m/s in cm/s"), P.Speed.Crouch, 190.0);
	Near(*this, TEXT("accel.ground 34 m/s2 in cm/s2"), P.Accel.Ground, 3400.0);
	Near(*this, TEXT("accel.groundStop 26 m/s2 in cm/s2"), P.Accel.GroundStop, 2600.0);
	Near(*this, TEXT("jump.gravity 21 m/s2 in cm/s2"), P.Jump.Gravity, 2100.0);
	Near(*this, TEXT("jump.apex 1 m in cm"), P.Jump.Apex, 100.0);
	Near(*this, TEXT("jump launch speed sqrt(2 * 2100 * 100)"), P.Jump.LaunchSpeed(), 648.07, 0.05);
	Near(*this, TEXT("sprint.minForward"), P.Sprint.MinForward, 0.55);
	Near(*this, TEXT("fov.base (vertical degrees)"), P.Fov.Base, 74.0);
	Near(*this, TEXT("look.pitchLimit 1.5 rad in degrees"), P.Look.PitchLimit, 85.9437, 0.001);
	Near(*this, TEXT("input.mouse 0.0021 rad per count in degrees"), P.Look.MouseDegreesPerCount, 0.120321, 0.00001);

	// A document without the player table must be refused, with the missing fields named.
	TSharedPtr<FJsonObject> Root;
	if (TestTrue(TEXT("config.json parses"), UMIDataSubsystem::LoadJsonFile(TEXT("config.json"), Root, Error)))
	{
		Root->RemoveField(TEXT("player"));
		FMIConfigData Broken;
		FString BrokenError;
		TestFalse(TEXT("config without player is refused"), UMIDataSubsystem::ParseConfig(Root, Broken, BrokenError));
		TestTrue(TEXT("the error names a missing field"), BrokenError.Contains(TEXT("player.speed.walk")));
	}
	return true;
}

/** The game mode spawns our character and controller, and the controller builds its input mappings in code. */
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIGameClassesTest, "MurderInc.Core.GameClasses", MIDataTestsPrivate::Flags)

bool FMIGameClassesTest::RunTest(const FString& Parameters)
{
	const AMIGameMode* GameMode = GetDefault<AMIGameMode>();
	TestTrue(TEXT("default pawn is AMIPlayerCharacter"), GameMode->DefaultPawnClass == AMIPlayerCharacter::StaticClass());
	TestTrue(TEXT("player controller is AMIPlayerController"), GameMode->PlayerControllerClass == AMIPlayerController::StaticClass());

	AMIPlayerController* Controller = NewObject<AMIPlayerController>();
	Controller->BuildInputAssets();
	const UInputMappingContext* Context = Controller->GetMappingContext();
	if (TestNotNull(TEXT("mapping context"), Context))
	{
		// W A S D, left stick, mouse, jump x2, sprint x3, crouch x2
		TestEqual(TEXT("key mappings"), Context->GetMappings().Num(), 13);
	}
	return true;
}

#endif // WITH_AUTOMATION_TESTS
