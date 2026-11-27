// The v6 finish pass (docs/unreal/DECISIONS.md 2026-11-26 22:45 and 2026-11-27 00:10, docs/unreal/POLISH.md v6 shortlist):
//   MurderInc.V6.Settings     the field of view is horizontal degrees at 16:9 with the owner's default of 90 (the rules take its
//                             vertical equivalent), a pad press steps further than a key, a held key repeats (data)
//   MurderInc.V6.StretchSemi  the STRETCH is semi-automatic only (one round per trigger pull); the CHOPPER keeps both modes
//   MurderInc.V6.ScopeName    the optic the player read as "4x scope" reads "2x scope" (the part id keeps its name)
//   MurderInc.V6.LastDrone    a Buzzard sent at the player flies straight at it (Hold the Block's last unhurt drones)
//   MurderInc.V6.BlastTick    a blast that kills an enemy raises the hit event a round raises, once per victim

#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SphereComponent.h"
#include "Core/Data/MILoadoutData.h"
#include "Core/MIEvents.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Enemies/MIEnemies.h"
#include "Enemies/MIEnemyActors.h"
#include "Flow/MIGameSubsystem.h"
#include "Flow/MISettings.h"
#include "GameFramework/WorldSettings.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Player/MIPlayerCharacter.h"
#include "Tests/MITestUtil.h"
#include "Weapons/MICombatSubsystem.h"
#include "Weapons/MILoadoutResolver.h"
#include "World/MIBoxWorld.h"
#include "World/MITargetDummy.h"

#if WITH_AUTOMATION_TESTS

namespace MIV6Private
{
	constexpr float Dt = 1.f / 30.f;

	struct FWorld
	{
		UWorld* World = nullptr;
		AMIPlayerCharacter* Player = nullptr;
		UMIGameSubsystem* Game = nullptr;

		FWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("MIV6World"));
			FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
			Context.SetCurrentWorld(World);
			World->InitializeActorsForPlay(FURL());
			World->BeginPlay();
			if (!World->GetBegunPlay())
			{
				World->GetWorldSettings()->NotifyBeginPlay();
			}
			Player = World->SpawnActor<AMIPlayerCharacter>(FVector(0, 0, 200), FRotator::ZeroRotator);
			Game = UMIGameSubsystem::Get(World);
		}
		~FWorld()
		{
			World->EndPlay(EEndPlayReason::Quit);
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
		bool Boot(FAutomationTestBase& T)
		{
			FMIBootOptions O;
			O.bTitle = false;
			O.Mode = TEXT("mission");
			O.Difficulty = TEXT("boss");
			O.bPersist = false;
			O.bDrawGrey = false;
			return T.TestTrue(TEXT("the game boots from level.json"), Player && Game && Game->Boot(O));
		}
		void Step()
		{
			World->Tick(LEVELTICK_All, Dt);
			GFrameCounter++;
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIV6SettingsTest, "MurderInc.V6.Settings", MITest::Flags)

bool FMIV6SettingsTest::RunTest(const FString& Parameters)
{
	FMISettings S;
	FString Error;
	if (!TestTrue(TEXT("settings defaults load: ") + Error, FMISettings::LoadDefaults(S, Error)))
	{
		return false;
	}
	TestEqual(TEXT("the default field of view is 90 degrees (horizontal at 16:9)"), S.Fov, 90.0);
	TestNearlyEqual(TEXT("its vertical equivalent for the rules"), S.VerticalFov(), 58.7, 0.1);
	TestNearlyEqual(TEXT("the conversion of the old 106 degrees back to the old 74 vertical"), FMISettings::VerticalFromWide(106.5), 74.0, 0.2);
	S.SetFov(10);
	TestEqual(TEXT("field of view 10 -> the slider's lowest"), S.Fov, 70.0);
	S.SetFov(200);
	TestEqual(TEXT("field of view 200 -> the slider's highest"), S.Fov, 120.0);
	TestTrue(TEXT("a pad press steps further than a key (volume)"), S.Rules.PadVolumeStep > S.Rules.VolumeStep);
	TestTrue(TEXT("a pad press steps further than a key (sensitivity)"), S.Rules.PadSensStep > S.Rules.SensStep);
	TestTrue(TEXT("a pad press steps further than a key (field of view)"), S.Rules.PadFovStep > S.Rules.FovStep);
	TestTrue(TEXT("a held key repeats after a delay, then faster, then in larger steps"),
		S.Rules.RepeatAfter > S.Rules.RepeatEvery && S.Rules.RepeatEvery > 0.0 && S.Rules.FastAfter > S.Rules.RepeatAfter && S.Rules.FastMult > 1.0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIV6StretchSemiTest, "MurderInc.V6.StretchSemi", MITest::Flags)

bool FMIV6StretchSemiTest::RunTest(const FString& Parameters)
{
	FMILoadoutData Data;
	TSharedPtr<FJsonObject> Config, Presentation;
	FString Error;
	if (!TestTrue(TEXT("loadout data loads: ") + Error, FMILoadoutData::Load(Data, Error) && FMILoadoutResolver::LoadRoots(Config, Presentation, Error)))
	{
		return false;
	}
	FMIRunSetup Setup;
	Setup.Guns = {TEXT("stretch"), TEXT("chopper")};
	FMIResolvedRun Run;
	if (!TestTrue(TEXT("the STRETCH and the CHOPPER resolve: ") + Error, FMILoadoutResolver(Data, Config, Presentation).Resolve(Setup, nullptr, Run, Error)))
	{
		return false;
	}
	if (!TestEqual(TEXT("two guns"), Run.Weapons.Guns.Num(), 2))
	{
		return false;
	}
	TestTrue(TEXT("STRETCH fire modes: semi only (the owner's decision, DECISIONS.md 2026-11-26)"), Run.Weapons.Guns[0].FireModes == TArray<FName>{TEXT("semi")});
	TestFalse(TEXT("the STRETCH is not automatic"), Run.Weapons.Guns[0].bAuto);
	TestTrue(TEXT("CHOPPER fire modes auto, semi (unchanged)"), Run.Weapons.Guns[1].FireModes == TArray<FName>{TEXT("auto"), TEXT("semi")});
	TestTrue(TEXT("the CHOPPER stays automatic"), Run.Weapons.Guns[1].bAuto);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIV6ScopeNameTest, "MurderInc.V6.ScopeName", MITest::Flags)

bool FMIV6ScopeNameTest::RunTest(const FString& Parameters)
{
	FString Text;
	if (!TestTrue(TEXT("frontend_text.json reads"), FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Data/frontend_text.json")))))
	{
		return false;
	}
	TestTrue(TEXT("the optic is named 2x scope"), Text.Contains(TEXT("\"scope4x\": {\"name\": \"2x scope\"")));
	TestFalse(TEXT("no 4x scope left in the text the player reads"), Text.Contains(TEXT("4x scope")));
	TestFalse(TEXT("no 'four times' left in it either"), Text.Contains(TEXT("Four times")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIV6LastDroneTest, "MurderInc.V6.LastDrone", MITest::Flags)

bool FMIV6LastDroneTest::RunTest(const FString& Parameters)
{
	using namespace MIV6Private;
	FWorld W;
	if (!W.Boot(*this))
	{
		return false;
	}
	for (int32 I = 0; I < 30; ++I) W.Step();
	const FVector Me = MI::Web::FromUnreal(W.Player->GetPlayerRules().Feet);
	FMIEnemySpawnOptions Opts;
	Opts.bAlerted = true;
	FMIEnemy* Probe = W.Game->GetEnemies().Spawn(MIEnemy::EType::Buzzard, FVector(Me.X + 28.0, 6.0, Me.Z), Opts);
	if (!TestNotNull(TEXT("a Buzzard spawns"), Probe))
	{
		return false;
	}
	const int32 Id = Probe->Id;
	TestFalse(TEXT("it does not charge by itself"), Probe->bCharge);
	Probe->bCharge = true;
	double Nearest = 1e9;
	for (int32 F = 0; F < 30 * 25; ++F)
	{
		W.Step();
		const FMIEnemy* E = W.Game->GetEnemies().Find(Id);
		if (!E || !E->bAlive)
		{
			break;
		}
		const FVector P = MI::Web::FromUnreal(W.Player->GetPlayerRules().Feet);
		Nearest = FMath::Min(Nearest, FVector::Dist(E->Pos, P + FVector(0, 1.0, 0)));
	}
	TestTrue(FString::Printf(TEXT("a charging Buzzard comes within 8 m of the player (nearest %.1f m; its orbit keeps it 12 m or more away)"), Nearest), Nearest < 8.0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIV6BlastTickTest, "MurderInc.V6.BlastTick", MITest::Flags)

bool FMIV6BlastTickTest::RunTest(const FString& Parameters)
{
	using namespace MIV6Private;
	// A world with nothing but a target dummy (an "enemy" for the blast) and the combat subsystem.
	FWorld W;
	AMITargetDummy* Dummy = W.World->SpawnActor<AMITargetDummy>(FVector(1000, 0, 100), FRotator::ZeroRotator);
	if (!TestNotNull(TEXT("a target dummy"), Dummy))
	{
		return false;
	}
	for (int32 I = 0; I < 3; ++I) W.Step();
	int32 Ticks = 0, Kills = 0;
	FMIGameEvents* Events = UMIEventSubsystem::Get(W.World);
	UMICombatSubsystem* Combat = UMICombatSubsystem::Get(W.World);
	if (!TestNotNull(TEXT("the event bus"), Events) || !TestNotNull(TEXT("the combat subsystem"), Combat))
	{
		return false;
	}
	const FDelegateHandle Handle = Events->PlayerHitEnemy.AddLambda([&](const FMIHitEnemyEvent& E)
	{
		if (E.Weapon == TEXT("blast"))
		{
			Ticks++;
			Kills += E.bKilled ? 1 : 0;
		}
	});
	// A blast that hurts without killing raises the hit event (no kill), a second one that kills raises it with bKilled.
	Combat->Explode(Dummy->GetMIBlastTarget() + FVector(0, 0, 30), 500.0, 40.0, INDEX_NONE, true, nullptr, 0.0);
	const int32 TicksAfterHurt = Ticks;
	TestTrue(TEXT("a blast that hurts an enemy raises the hit event, without a kill"), TicksAfterHurt == 1 && Kills == 0 && Dummy->IsMIDamageableAlive());
	Combat->Explode(Dummy->GetMIBlastTarget() + FVector(0, 0, 30), 500.0, 100000.0, INDEX_NONE, true, nullptr, 0.0);
	Events->PlayerHitEnemy.Remove(Handle);
	AddInfo(FString::Printf(TEXT("blasts: %d hit events, %d kills, the dummy %s"), Ticks, Kills, Dummy->IsMIDamageableAlive() ? TEXT("alive") : TEXT("down")));
	TestFalse(TEXT("the second blast downed the dummy"), Dummy->IsMIDamageableAlive());
	TestTrue(TEXT("once per victim per blast: two blasts, two events, the second with the kill"), Ticks == 2 && Kills == 1);
	return true;
}

#endif
