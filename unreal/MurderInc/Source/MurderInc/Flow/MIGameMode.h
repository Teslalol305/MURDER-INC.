#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "MIGameMode.generated.h"

/** The game mode of every MURDER INC. level: spawns the player character with its controller. */
UCLASS()
class MURDERINC_API AMIGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AMIGameMode();
};
