#include "Cloud/MIProgressBridge.h"
#include "Misc/AutomationTest.h"
#include "Tests/MITestUtil.h"

// docs/unreal/maps/progression.md 4.3 / 4.4: the codes of the document's table pass, every one-character change fails,
// and the page's message is read strictly. The same vectors run in tools/ipx-bridge/murderinc-progress-bridge.test.js.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIProgressBridgeTest, "MurderInc.Cloud.ProgressBridge", MITest::Flags)

bool FMIProgressBridgeTest::RunTest(const FString& Parameters)
{
	const TCHAR* Good[] = { TEXT("47YZ-MB30"), TEXT("4FMY-N7W6"), TEXT("4Y4W-PZ1F"), TEXT("4FG6-05EW"), TEXT("4W00-1D88") };
	const FString Alphabet = TEXT("0123456789ABCDEFGHJKMNPQRSTVWXYZ");
	for (const TCHAR* C : Good)
	{
		TestEqual(C, FMIProgressBridge::CheckCode(C), FString(C));
		const FString Plain = FString(C).Left(4) + FString(C).Mid(5);
		for (int32 I = 0; I < 8; ++I)
		{
			for (int32 A = 0; A < Alphabet.Len(); ++A)
			{
				if (Alphabet[A] == Plain[I])
				{
					continue;
				}
				FString T = Plain;
				T[I] = Alphabet[A];
				TestTrue(*FString::Printf(TEXT("%s with one change is refused"), C), FMIProgressBridge::CheckCode(T).IsEmpty());
			}
		}
	}
	TestTrue(TEXT("lower case"), FMIProgressBridge::CheckCode(TEXT("47yz-mb30")).IsEmpty());
	TestTrue(TEXT("short"), FMIProgressBridge::CheckCode(TEXT("47YZ-MB3")).IsEmpty());

	FMIProgressMessage M;
	TestTrue(TEXT("a good message"), FMIProgressBridge::ParseDescriptor(TEXT("{\"mi\":\"progress\",\"v\":1,\"code\":\"4FMY-N7W6\",\"hold\":{\"block\":12345,\"chinatown\":0,\"midtown\":0}}"), M));
	TestEqual(TEXT("code"), M.Code, FString(TEXT("4FMY-N7W6")));
	TestEqual(TEXT("hold"), M.Hold[0], 12345);
	FMIProgressMessage N;
	TestFalse(TEXT("wrong version"), FMIProgressBridge::ParseDescriptor(TEXT("{\"mi\":\"progress\",\"v\":2,\"code\":\"4FMY-N7W6\"}"), N));
	TestFalse(TEXT("bad code"), FMIProgressBridge::ParseDescriptor(TEXT("{\"mi\":\"progress\",\"v\":1,\"code\":\"4FMY-N7W7\"}"), N));
	TestFalse(TEXT("hold too big"), FMIProgressBridge::ParseDescriptor(TEXT("{\"mi\":\"progress\",\"v\":1,\"code\":\"4FMY-N7W6\",\"hold\":{\"block\":100000000}}"), N));
	TestFalse(TEXT("hold fraction"), FMIProgressBridge::ParseDescriptor(TEXT("{\"mi\":\"progress\",\"v\":1,\"code\":\"4FMY-N7W6\",\"hold\":{\"block\":1.5}}"), N));
	TestFalse(TEXT("the away word"), FMIProgressBridge::ParseDescriptor(TEXT("{\"murderinc\":\"away\"}"), N));
	TestFalse(TEXT("too long"), FMIProgressBridge::ParseDescriptor(FString(TEXT("{\"mi\":\"progress\",\"pad\":\"")) + FString::ChrN(300, TEXT('x')) + TEXT("\"}"), N));

	// The round trip through the bytes of a UIInteraction message and through the JSON the game sends.
	const FString Json = FMIProgressBridge::BuildJson(M);
	TArray<uint8> B;
	B.Add((uint8)(Json.Len() & 255));
	B.Add((uint8)((Json.Len() >> 8) & 255));
	for (int32 I = 0; I < Json.Len(); ++I)
	{
		B.Add((uint8)(Json[I] & 255));
		B.Add((uint8)((Json[I] >> 8) & 255));
	}
	FMIProgressMessage R;
	TestTrue(TEXT("round trip"), FMIProgressBridge::ParseUIBytes(B, R));
	TestEqual(TEXT("round trip code"), R.Code, M.Code);
	TestEqual(TEXT("round trip hold"), R.Hold[0], 12345);
	TArray<uint8> Cut = B;
	Cut.SetNum(Cut.Num() - 4);
	TestFalse(TEXT("cut short"), FMIProgressBridge::ParseUIBytes(Cut, R));
	return !HasAnyErrors();
}
