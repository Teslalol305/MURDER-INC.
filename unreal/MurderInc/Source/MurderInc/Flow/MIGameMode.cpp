#include "Flow/MIGameMode.h"

#include "Flow/MIGameSubsystem.h"
#include "Kismet/GameplayStatics.h"
#include "Player/MIPlayerCharacter.h"
#include "Player/MIPlayerController.h"
#include "UI/MIHUD.h"

AMIGameMode::AMIGameMode()
{
	DefaultPawnClass = AMIPlayerCharacter::StaticClass();
	PlayerControllerClass = AMIPlayerController::StaticClass();
	HUDClass = AMIHUD::StaticClass();
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
	if (!BlockMaps.Contains(Map) && Block != TEXT("1"))
	{
		return;
	}
	FMIBootOptions Options;
	Options.Mode = FName(UGameplayStatics::ParseOption(OptionsString, TEXT("mode")));
	Options.Difficulty = FName(UGameplayStatics::ParseOption(OptionsString, TEXT("difficulty")));
	if (UGameplayStatics::HasOption(OptionsString, TEXT("autostart")))
	{
		Options.bTitle = false;
		Options.bSkipIntro = true;
	}
	Game->Boot(Options);
}
