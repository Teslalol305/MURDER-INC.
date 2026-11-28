#include "Flow/MIGameMode.h"

#include "Flow/MIGameSubsystem.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Kismet/GameplayStatics.h"
#include "World/MILevelData.h"
#include "Player/MIPlayerCharacter.h"
#include "Player/MIPlayerController.h"
#include "UI/MIHUD.h"
#include "UI/MILoadingCard.h"

AMIGameMode::AMIGameMode()
{
	DefaultPawnClass = AMIPlayerCharacter::StaticClass();
	PlayerControllerClass = AMIPlayerController::StaticClass();
	HUDClass = AMIHUD::StaticClass();
}

FName AMIGameMode::LevelOfMap(const FString& Map)
{
	TSharedPtr<FJsonObject> Root;
	FString Error;
	const TSharedPtr<FJsonObject>* Levels = nullptr;
	if (!UMIDataSubsystem::LoadJsonFile(TEXT("levels.json"), Root, Error) || !Root->TryGetObjectField(TEXT("levels"), Levels))
	{
		return NAME_None;
	}
	for (const TPair<FString, TSharedPtr<FJsonValue>>& L : (*Levels)->Values)
	{
		const TSharedPtr<FJsonObject> E = L.Value->AsObject();
		FString A, B;
		E->TryGetStringField(TEXT("map"), A);
		E->TryGetStringField(TEXT("greyMap"), B);
		if (FPackageName::GetShortName(A) == Map || (!B.IsEmpty() && FPackageName::GetShortName(B) == Map && L.Key == TEXT("block")))
		{
			return FName(L.Key);
		}
	}
	return NAME_None;
}

void AMIGameMode::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
	Super::InitGame(MapName, Options, ErrorMessage);
	// The level the world plays is known before any actor begins (the guide reads it in BeginPlay).
	FName Id = FName(UGameplayStatics::ParseOption(Options, TEXT("level")));
	if (Id.IsNone())
	{
		Id = LevelOfMap(FPackageName::GetShortName(MapName));
	}
	FMILevelData::SetActive(Id.IsNone() ? FName(TEXT("block")) : Id);
}

void AMIGameMode::StartPlay()
{
	Super::StartPlay();
	UWorld* World = GetWorld();
	UMIGameSubsystem* Game = UMIGameSubsystem::Get(this);
	if (!World || !Game)
	{
		return;
	}
	FString Map = World->GetMapName();
	Map.RemoveFromStart(World->StreamingLevelsPrefix);
	const FString Block = UGameplayStatics::ParseOption(OptionsString, TEXT("block"));
	const FName MapLevel = LevelOfMap(Map);
	if (!BlockMaps.Contains(Map) && Block != TEXT("1") && MapLevel.IsNone())
	{
		return;
	}
	FMIBootOptions Options;
	Options.Level = FMILevelData::ActiveId();
	Options.bCampaign = true;
	Options.Mode = FName(UGameplayStatics::ParseOption(OptionsString, TEXT("mode")));
	Options.Difficulty = FName(UGameplayStatics::ParseOption(OptionsString, TEXT("difficulty")));
	if (UGameplayStatics::HasOption(OptionsString, TEXT("autostart")))
	{
		Options.bTitle = false;
		Options.bSkipIntro = true;
	}
	if (UGameplayStatics::HasOption(OptionsString, TEXT("travelled")))
	{
		Options.bTitle = false;
		Options.bSkipIntro = false;
		Options.bTravelled = true;
	}
	const bool bBooted = Game->Boot(Options);
	if (bBooted && Options.bTravelled)
	{
		MILoadingCard::Hide();
	}
}
