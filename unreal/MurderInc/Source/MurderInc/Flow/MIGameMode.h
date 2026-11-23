#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "MIGameMode.generated.h"

/**
 * The game mode of every MURDER INC. level: spawns the player character with its controller, and in the block maps
 * (BlockMaps in DefaultGame.ini, or the URL option ?block=1) boots the game (UMIGameSubsystem). URL options:
 * ?mode=mission|holdout, ?difficulty=hustler|boss|kingpin, ?autostart (straight into a run, no intro).
 */
UCLASS(Config = Game)
class MURDERINC_API AMIGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AMIGameMode();
	virtual void StartPlay() override;

	UPROPERTY(Config)
	TArray<FString> BlockMaps;
};
