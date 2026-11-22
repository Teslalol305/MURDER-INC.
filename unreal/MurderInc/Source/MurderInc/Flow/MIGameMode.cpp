#include "Flow/MIGameMode.h"

#include "Player/MIPlayerCharacter.h"
#include "Player/MIPlayerController.h"
#include "UI/MIHUD.h"

AMIGameMode::AMIGameMode()
{
	DefaultPawnClass = AMIPlayerCharacter::StaticClass();
	PlayerControllerClass = AMIPlayerController::StaticClass();
	HUDClass = AMIHUD::StaticClass();
}
