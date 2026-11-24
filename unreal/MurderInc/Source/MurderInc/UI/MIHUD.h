#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "UI/MIMenus.h"
#include "MIHUD.generated.h"

class UFont;
class UMIGameSubsystem;

/**
 * The heads-up display and the menus, drawn on the canvas (functional and legible; the real HUD of spec 07 and its
 * styling come later): the crosshair whose gap is the weapon's spread cone, the hit marker, ammunition and health;
 * the flow's lines (objective, tally, reels, the hold prompt with its fill, messages, the wave banner, the radio
 * strip, the location card, objective markers); and the cards and menus of UMIGameSubsystem's FMIMenu. It reads
 * only public state, with one exception: it tells the menu where it drew a card's rows (FMIMenu::Layout) and which
 * row the moving cursor is over, so the cards take the mouse.
 */
UCLASS()
class MURDERINC_API AMIHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;

private:
	void DrawPlay(UFont* Font);
	/** LOADOUT.md 4.7: one slot per carried gun, then melee; the bag once; AUTO / SEMI; attachment pips. */
	void DrawWeaponBar(const class AMIPlayerCharacter& Player, UMIGameSubsystem* Game);
	/** LOADOUT.md 4.6: the weapon wheel, while Q / Y is held with three or more guns. */
	void DrawWheel(const class AMIPlayerCharacter& Player);
	void DrawPlate(double X, double Y, double W, double H, const FLinearColor& Fill, const FLinearColor& Edge, float EdgeWidth = 1.f);
	void DrawFlow(UMIGameSubsystem& Game, UFont* Font);
	void DrawMenu(UMIGameSubsystem& Game, UFont* Font);
	void Centered(const FString& Text, double Y, const FLinearColor& Colour, UFont* Font, float Scale);
	/** Damage at the edges (a red vignette, at most 15 % in the centre) and a marker toward where the hit came from. */
	void DrawHurt(const class AMIPlayerCharacter& Player, double Hurt);

	FDelegateHandle HitHandle;
	TOptional<FVector> HitFrom;  // world (cm)
	double HitTime = -1.0;        // world seconds of the last hit
	/** The card the cursor was last seen on and where: the cursor selects a row only once it has moved on that card. */
	EMIMenuScreen HoverScreen = EMIMenuScreen::None;
	FVector2D HoverCursor = FVector2D::ZeroVector;
};
