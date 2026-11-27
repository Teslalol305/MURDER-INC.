#include "Core/MIPreload.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "Misc/AutomationTest.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "MurderInc.h"

namespace MIPreloadPrivate
{
	int32 GPreload = 1;
	FAutoConsoleVariableRef CVarPreload(TEXT("MI.Preload"), GPreload,
		TEXT("1 (default): load every asset the data files name in the background once the title screen is up, so set-up screens and gun switches do not load on the game thread (docs/unreal/SMOOTH.md C2); 0: do not."));

	// The data files that name the assets a run, a set-up screen or a gun switch may ask for.
	const TCHAR* Files[] = {TEXT("presentation.json"), TEXT("attachments.json"), TEXT("guns.json"), TEXT("crew.json")};
}

TArray<FSoftObjectPath> UMIPreloadSubsystem::CollectPaths(const TArray<FString>& JsonTexts)
{
	TArray<FSoftObjectPath> Out;
	TSet<FString> Seen;
	for (const FString& Text : JsonTexts)
	{
		int32 From = 0;
		while (true)
		{
			const int32 At = Text.Find(TEXT("\"/Game/"), ESearchCase::CaseSensitive, ESearchDir::FromStart, From);
			if (At == INDEX_NONE)
			{
				break;
			}
			const int32 End = Text.Find(TEXT("\""), ESearchCase::CaseSensitive, ESearchDir::FromStart, At + 1);
			if (End == INDEX_NONE)
			{
				break;
			}
			const FString Path = Text.Mid(At + 1, End - At - 1);
			From = End + 1;
			// An asset path: /Game/Folder/Name.Name, no spaces, no escapes (a JSON string with a backslash is not one).
			if (Path.Contains(TEXT(" ")) || Path.Contains(TEXT("\\")) || !Path.Contains(TEXT(".")))
			{
				continue;
			}
			if (!Seen.Contains(Path))
			{
				Seen.Add(Path);
				Out.Emplace(Path);
			}
		}
	}
	return Out;
}

void UMIPreloadSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	if (GIsAutomationTesting || IsRunningDedicatedServer() || IsRunningCommandlet() || !FApp::CanEverRender()
		|| FParse::Param(FCommandLine::Get(), TEXT("MINoPreload")))
	{
		return;
	}
	TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UMIPreloadSubsystem::Tick), 0.25f);
}

void UMIPreloadSubsystem::Deinitialize()
{
	if (TickHandle.IsValid())
	{
		FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
		TickHandle.Reset();
	}
	if (Handle.IsValid())
	{
		Handle->CancelHandle();
		Handle.Reset();
	}
	Streamable.Reset();
	Super::Deinitialize();
}

bool UMIPreloadSubsystem::Tick(float DeltaTime)
{
	TRACE_CPUPROFILER_EVENT_SCOPE_STR("MI/UMIPreloadSubsystem::Tick");
	if (!bStarted)
	{
		const UGameInstance* GI = GetGameInstance();
		const UWorld* World = GI ? GI->GetWorld() : nullptr;
		if (!World || !World->HasBegunPlay())
		{
			return true;  // the map is still loading: wait for the title screen
		}
		bStarted = true;
		Start();
		if (!Handle.IsValid())
		{
			TickHandle.Reset();
			return false;
		}
	}
	if (Handle.IsValid() && Handle->HasLoadCompleted() && !bDone)
	{
		bDone = true;
		TArray<UObject*> Loaded;
		Handle->GetLoadedAssets(Loaded);
		UE_LOG(LogMI, Log, TEXT("Preload: %d of %d assets named by the data files are in memory, %.1f s after the title screen came up"),
			Loaded.Num(), Requested, FPlatformTime::Seconds() - StartedAt);
		TickHandle.Reset();
		return false;
	}
	return true;
}

void UMIPreloadSubsystem::Start()
{
	if (MIPreloadPrivate::GPreload == 0)
	{
		UE_LOG(LogMI, Log, TEXT("Preload: off (MI.Preload 0)"));
		return;
	}
	TArray<FString> Texts;
	const FString Dir = UMIDataSubsystem::GetDataDir();
	for (const TCHAR* File : MIPreloadPrivate::Files)
	{
		FString Text;
		if (FFileHelper::LoadFileToString(Text, *FPaths::Combine(Dir, File)))
		{
			Texts.Add(MoveTemp(Text));
		}
	}
	TArray<FSoftObjectPath> Paths = CollectPaths(Texts);
	int32 Missing = 0;
	Paths.RemoveAll([&Missing](const FSoftObjectPath& P)
	{
		// A clean checkout lacks the pack and our own guns (generated content): asking for them would only log failures.
		const bool bThere = FPackageName::DoesPackageExist(P.GetLongPackageName());
		Missing += bThere ? 0 : 1;
		return !bThere;
	});
	Requested = Paths.Num();
	if (Requested == 0)
	{
		UE_LOG(LogMI, Log, TEXT("Preload: nothing to load (%d paths named, none of them in this build)"), Missing);
		return;
	}
	StartedAt = FPlatformTime::Seconds();
	Streamable = MakeUnique<FStreamableManager>();
	// Below the default priority: what a screen asks for now goes first. The handle keeps everything it loaded referenced.
	Handle = Streamable->RequestAsyncLoad(MoveTemp(Paths), FStreamableDelegateWithHandle(), FStreamableManager::DefaultAsyncLoadPriority - 1, true, false, TEXT("MIPreload"));
	UE_LOG(LogMI, Log, TEXT("Preload: %d assets named by the data files are being loaded in the background (%d not in this build)"), Requested, Missing);
}
