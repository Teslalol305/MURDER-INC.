#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "MIHUD.generated.h"

/**
 * The minimal heads-up display of slice 1, drawn on the canvas: the crosshair whose gap is the weapon's spread
 * cone projected with the current field of view, the hit marker (white, red on a kill), ammunition and health.
 * The real HUD (spec 07) replaces it; it reads only public state of the player and the weapon.
 */
UCLASS()
class MURDERINC_API AMIHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;
};
