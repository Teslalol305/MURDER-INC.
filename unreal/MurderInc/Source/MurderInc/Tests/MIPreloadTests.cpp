// The background preload of the assets the data files name (docs/unreal/SMOOTH.md C2). No world, no renderer.
//   MurderInc.Preload.Paths   every distinct /Game/ asset path of the JSON texts, once, in order; strings that are not
//                             asset paths are left out; the real data files name the guns, the parts and the crew's arms

#include "Core/Data/MIDataSubsystem.h"
#include "Core/MIPreload.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Tests/MITestUtil.h"

#if WITH_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIPreloadPathsTest, "MurderInc.Preload.Paths", MITest::Flags)

bool FMIPreloadPathsTest::RunTest(const FString& Parameters)
{
	{
		TArray<FString> Texts;
		Texts.Add(TEXT("{\"a\":\"/Game/Weapons/X/SK_X.SK_X\",\"b\":[\"/Game/Weapons/X/SK_X.SK_X\",\"/Game/P/SM_P.SM_P\"],\"c\":\"/Game/no dot or space\",\"d\":\"Game/SM_Q.SM_Q\",\"e\":\"/Engine/BasicShapes/Cube.Cube\"}"));
		Texts.Add(TEXT("{\"f\":\"/Game/P/SM_P.SM_P\",\"g\":\"/Game/Folder\"}"));
		const TArray<FSoftObjectPath> Paths = UMIPreloadSubsystem::CollectPaths(Texts);
		TestEqual(TEXT("two distinct asset paths"), Paths.Num(), 2);
		if (Paths.Num() == 2)
		{
			TestEqual(TEXT("the first in order"), Paths[0].ToString(), FString(TEXT("/Game/Weapons/X/SK_X.SK_X")));
			TestEqual(TEXT("the second, once"), Paths[1].ToString(), FString(TEXT("/Game/P/SM_P.SM_P")));
		}
		TestEqual(TEXT("nothing in an empty text"), UMIPreloadSubsystem::CollectPaths({FString()}).Num(), 0);
		TestEqual(TEXT("an unterminated string is not read past the end"), UMIPreloadSubsystem::CollectPaths({FString(TEXT("{\"a\":\"/Game/X.X"))}).Num(), 0);
	}
	{
		// The game's own data: the guns, their parts and the crew's arms are named, so a set-up screen finds them loaded.
		TArray<FString> Texts;
		for (const TCHAR* File : {TEXT("presentation.json"), TEXT("attachments.json"), TEXT("guns.json"), TEXT("crew.json")})
		{
			FString Text;
			TestTrue(FString::Printf(TEXT("%s is there"), File), FFileHelper::LoadFileToString(Text, *FPaths::Combine(UMIDataSubsystem::GetDataDir(), File)));
			Texts.Add(Text);
		}
		const TArray<FSoftObjectPath> Paths = UMIPreloadSubsystem::CollectPaths(Texts);
		AddInfo(FString::Printf(TEXT("%d asset paths named by the data files"), Paths.Num()));
		TestTrue(TEXT("more than a hundred asset paths"), Paths.Num() > 100);
		const auto Has = [&Paths](const TCHAR* Part) { return Paths.ContainsByPredicate([Part](const FSoftObjectPath& P) { return P.ToString().Contains(Part); }); };
		TestTrue(TEXT("a gun"), Has(TEXT("/Game/Weapons/Shorty/SK_Shorty")));
		TestTrue(TEXT("a part"), Has(TEXT("/Game/Weapons/Parts/")));
		TestTrue(TEXT("the crew's arms"), Has(TEXT("/Game/Characters/")));
	}
	return !HasAnyErrors();
}

#endif
