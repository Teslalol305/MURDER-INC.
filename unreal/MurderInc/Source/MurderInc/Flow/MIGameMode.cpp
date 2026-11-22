#include "Flow/MIGameMode.h"

#include "Player/MIPlayerCharacter.h"
#include "Player/MIPlayerController.h"

AMIGameMode::AMIGameMode()
{
	DefaultPawnClass = AMIPlayerCharacter::StaticClass();
	PlayerControllerClass = AMIPlayerController::StaticClass();
}
