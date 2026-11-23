// LOADOUT.md 8: the loadout data, the resolver's parity and the attachments.

#include "Core/Data/MIDataSubsystem.h"
#include "Core/Data/MILoadoutData.h"
#include "Misc/AutomationTest.h"
#include "World/MILevelData.h"

#if WITH_AUTOMATION_TESTS

namespace MILoadoutTestsPrivate
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;

	bool LoadData(FAutomationTestBase& Test, FMILoadoutData& Out)
	{
		FString Error;
		if (!FMILoadoutData::Load(Out, Error))
		{
			Test.AddError(FString::Printf(TEXT("loadout data: %s"), *Error));
			return false;
		}
		return true;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutDataLoadsTest, "MurderInc.Loadout.DataLoads", MILoadoutTestsPrivate::Flags)

bool FMILoadoutDataLoadsTest::RunTest(const FString& Parameters)
{
	FMILoadoutData D;
	if (!MILoadoutTestsPrivate::LoadData(*this, D))
	{
		return false;
	}
	TArray<FString> Problems;
	D.ValidateData(Problems);
	for (const FString& P : Problems)
	{
		AddError(P);
	}
	TestEqual(TEXT("roster"), D.Roster.Num(), 6);
	TestEqual(TEXT("parts"), D.Attachments.Num(), 10);
	TestEqual(TEXT("slots"), D.Slots.Num(), 6);
	TestEqual(TEXT("crew"), D.CrewOrder.Num(), 4);
	TestEqual(TEXT("parity guns"), D.ParityGuns, TArray<FName>{TEXT("chopper"), TEXT("nine")});
	// The CHOPPER's rules are the very config.json object (one source of truth).
	FMIConfigData Config;
	FString Error;
	TSharedPtr<FJsonObject> ConfigRoot;
	if (UMIDataSubsystem::LoadJsonFile(TEXT("config.json"), ConfigRoot, Error))
	{
		const TSharedPtr<FJsonValue> Chopper = MIJson::Get(ConfigRoot, TEXT("weapons.chopper"));
		TestTrue(TEXT("chopper rules = config.json weapons.chopper"), Chopper.IsValid() && MIJson::Print(Chopper->AsObject()) == MIJson::Print(D.FindGun(TEXT("chopper"))->Rules));
		double Holster = 0.0, Common = 0.0;
		TestTrue(TEXT("extraDefaults.holster is a number"), MIJson::Number(D.ExtraDefaults->TryGetField(TEXT("holster")), Holster));
		MIJson::Number(MIJson::Get(ConfigRoot, TEXT("weapons.common.holster")), Common);
		TestEqual(TEXT("extraDefaults.holster = weapons.common.holster"), Holster, Common);
	}

	// levels.json provides against the level file (the block: 3 reels, 29 / 17 spawns, 21 explosives, 14 title keys).
	const FMILevelData* Level = FMILevelData::Get();
	const FMILevelEntry* Block = D.Levels.Find(TEXT("block"));
	if (TestNotNull(TEXT("level.json"), Level) && TestNotNull(TEXT("levels.json block"), Block))
	{
		int32 Ground = 0, Air = 0;
		for (const FMILevelPoint& S : Level->Spawns)
		{
			(S.Type == TEXT("air") ? Air : Ground)++;
		}
		const FMILevelProvides& P = Block->Provides;
		TestEqual(TEXT("objectives"), P.Objectives, Level->Objectives.Num());
		TestEqual(TEXT("ground spawns"), P.Ground, Ground);
		TestEqual(TEXT("air spawns"), P.Air, Air);
		TestEqual(TEXT("explosives"), P.bExplosives, Level->Explosives.Num() > 0);
		TestEqual(TEXT("title path"), P.bTitlePath, Level->CinematicPos.Num() >= 2);
		TestEqual(TEXT("21 explosives"), Level->Explosives.Num(), 21);
		TestEqual(TEXT("14 title keys"), Level->CinematicPos.Num(), 14);
		TestEqual(TEXT("3 reels"), Level->Objectives.Num(), 3);
	}
	return Problems.Num() == 0;
}

#endif
