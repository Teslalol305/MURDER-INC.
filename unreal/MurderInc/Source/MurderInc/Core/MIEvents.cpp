#include "Core/MIEvents.h"

#include "Engine/World.h"

FMIGameEvents* UMIEventSubsystem::Get(const UObject* WorldContextObject)
{
	const UWorld* World = WorldContextObject ? WorldContextObject->GetWorld() : nullptr;
	UMIEventSubsystem* Subsystem = World ? World->GetSubsystem<UMIEventSubsystem>() : nullptr;
	return Subsystem ? &Subsystem->Events : nullptr;
}
