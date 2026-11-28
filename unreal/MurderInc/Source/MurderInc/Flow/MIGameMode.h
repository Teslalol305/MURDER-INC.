#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "MIGameMode.generated.h"

/**
 * The game mode of every MURDER INC. level: spawns the player character with its controller, and in the block maps
 * (BlockMaps in DefaultGame.ini, or the URL option ?block=1) boots the game (UMIGameSubsystem). URL options:
 * ?level=<id> (a map level on the grey map), ?travelled (a level travel: the set-up goes on, the run starts), ?mode=mission|holdout, ?difficulty=hustler|boss|kingpin, ?autostart (straight into a run, no intro).
 */
UCLASS(Config = Game)
class MURDERINC_API AMIGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AMIGameMode();
	virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;
	virtual void StartPlay() override;
	/** The level a map belongs to: levels.json `map` or `greyMap` of an entry (the Block's L_Block, a map level's art map or the grey map). */
	static FName LevelOfMap(const FString& Map);

	UPROPERTY(Config)
	TArray<FString> BlockMaps;
};
