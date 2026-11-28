#pragma once

#include "CoreMinimal.h"

class UWorld;

/**
 * The level travel's card (progression.md 3.7): full screen over the viewport while the next map loads. It is a
 * viewport widget, so it outlives the old world and shows on the stream until the new world's game mode takes it away.
 */
namespace MILoadingCard
{
	MURDERINC_API void Show(const FString& Kicker, const FString& Title, const FString& Line);
	MURDERINC_API void Hide();
	MURDERINC_API bool IsUp();
}
