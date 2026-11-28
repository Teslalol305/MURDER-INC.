#include "Flow/MIRunSetupSubsystem.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Engine/GameInstance.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "MurderInc.h"

namespace MIRunSetupPrivate
{
	TAutoConsoleVariable<int32> CVarShowUnready(TEXT("mi.Setup.ShowUnready"), 0,
		TEXT("1: the rack also shows guns that are not ready (their mesh or core clips are missing), tagged DEV (LOADOUT.md 3.2)."));
}

void UMIRunSetupSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Collection.InitializeDependency<UMIDataSubsystem>();
	Super::Initialize(Collection);
}

UMIRunSetupSubsystem* UMIRunSetupSubsystem::Get(const UObject* WorldContextObject)
{
	UGameInstance* GI = WorldContextObject ? UGameplayStatics::GetGameInstance(WorldContextObject) : nullptr;
	return GI ? GI->GetSubsystem<UMIRunSetupSubsystem>() : nullptr;
}

const FMILoadoutData* UMIRunSetupSubsystem::GetData() const
{
	const UMIDataSubsystem* D = GetGameInstance() ? GetGameInstance()->GetSubsystem<UMIDataSubsystem>() : nullptr;
	return D && D->IsLoadoutLoaded() ? &D->GetLoadout() : nullptr;
}

FMIReadiness UMIRunSetupSubsystem::MakeReadiness() const
{
	FMIReadiness R;
	R.Data = GetData();
	R.AssetExists = FMIReadiness::PackageExists();
	R.bShowUnready = MIRunSetupPrivate::CVarShowUnready.GetValueOnGameThread() != 0;
	return R;
}

bool UMIRunSetupSubsystem::UnlockAll() const
{
	static const bool bAll = FParse::Param(FCommandLine::Get(), TEXT("MIUnlockAll"));
	return bAll;
}

bool UMIRunSetupSubsystem::IsLevelOpen(FName Level) const
{
	const FMILoadoutData* Data = GetData();
	return UnlockAll() || !Data || Progress.IsOpen(Level, Data->LevelOrder);
}

FName UMIRunSetupSubsystem::OpenLevelFor(FName Level) const
{
	const FMILoadoutData* Data = GetData();
	if (!Data || IsLevelOpen(Level))
	{
		return Level;
	}
	return Progress.FurthestOpen(Data->LevelOrder);
}

void UMIRunSetupSubsystem::ProgressToSave(const FMIProgress& In, FMIProgressSave& Out)
{
	Out = FMIProgressSave();
	for (const TPair<FName, FMILevelRecord>& R : In.Levels)
	{
		FMILevelRecordSave& S = Out.Levels.AddDefaulted_GetRef();
		S.Id = R.Key;
		S.bCleared = R.Value.bCleared;
		S.Clears = R.Value.Clears;
		S.BestPoints = R.Value.BestPoints;
		S.BestDifficulty = R.Value.BestDifficulty;
		S.HoldBest = R.Value.HoldBest;
	}
	Out.bAlbumSeen = In.bAlbumSeen;
}

void UMIRunSetupSubsystem::ProgressFromSave(const FMIProgressSave& In, FMIProgress& Out)
{
	Out = FMIProgress();
	for (const FMILevelRecordSave& S : In.Levels)
	{
		FMILevelRecord& R = Out.Levels.Add(S.Id);
		R.bCleared = S.bCleared;
		R.Clears = S.Clears;
		R.BestPoints = S.BestPoints;
		R.BestDifficulty = S.BestDifficulty;
		R.HoldBest = S.HoldBest;
	}
	Out.bAlbumSeen = In.bAlbumSeen;
}

void UMIRunSetupSubsystem::SetSetup(const FMIRunSetup& In)
{
	Setup = In;
	MakeReadiness().Validate(Setup);
	Setup.Level = OpenLevelFor(Setup.Level);
	bHave = true;
}

void UMIRunSetupSubsystem::ToSave(const FMIRunSetup& In, FMISetupSave& Out)
{
	Out = FMISetupSave();
	Out.Crew = In.Crew;
	Out.Guns = In.Guns;
	for (const TPair<FName, FMIGunBuild>& B : In.Builds)
	{
		Out.Builds.Add(B.Key).Parts = B.Value.Parts;
	}
	Out.Level = In.Level;
	Out.Seen = In.Seen;
	Out.bPlayed = In.bPlayed;
}

void UMIRunSetupSubsystem::FromSave(const FMISetupSave& In, FMIRunSetup& Out)
{
	Out.Crew = In.Crew;
	Out.Guns = In.Guns;
	Out.Builds.Reset();
	for (const TPair<FName, FMIGunBuildSave>& B : In.Builds)
	{
		Out.Builds.Add(B.Key).Parts = B.Value.Parts;
	}
	Out.Level = In.Level;
	Out.Seen = In.Seen;
	Out.bPlayed = In.bPlayed;
}

void UMIRunSetupSubsystem::Load(const UMISaveGame* Save, const FMISettings& Settings)
{
	const FMILoadoutData* Data = GetData();
	if (!Data)
	{
		Setup = FMIRunSetup();
		bHave = false;
		return;
	}
	FMIRunSetup S = Data->ParitySetup(Settings.Mode, Settings.Difficulty, Settings.Time);
	if (Save && Save->Setup.Version == 1 && Save->Setup.Guns.Num() > 0)
	{
		FromSave(Save->Setup, S);
	}
	else if (Save)
	{
		S.bPlayed = Save->Setup.bPlayed;
	}
	S.Mode = Settings.Mode;
	S.Difficulty = Settings.Difficulty;
	S.Time = Settings.Time;
	const int32 Fixes = MakeReadiness().Validate(S);
	if (Fixes > 0)
	{
		UE_LOG(LogMI, Log, TEXT("Set-up: the saved set-up took %d correction(s) (a gun, part or crew member no longer offered)"), Fixes);
	}
	if (Save)
	{
		ProgressFromSave(Save->Progress, Progress);
	}
	S.Level = OpenLevelFor(S.Level);  // a remembered level that is not open (a fresh session, no code) falls back to the furthest open one
	Setup = S;
	bHave = true;
}

void UMIRunSetupSubsystem::Write(UMISaveGame& Save) const
{
	if (bHave)
	{
		ToSave(Setup, Save.Setup);
	}
	ProgressToSave(Progress, Save.Progress);
}
