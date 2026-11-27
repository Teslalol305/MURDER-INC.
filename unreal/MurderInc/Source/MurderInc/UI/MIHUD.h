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
	virtual void BeginPlay() override;
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
	/** The same on a dark band (optionally with the gold rule on its left edge): the in-run warnings and the location card. */
	void CenteredPlate(const FString& Text, double Y, const FLinearColor& Colour, UFont* Font, float Scale, bool bRule);
	/** Damage at the edges (a red vignette, at most 15 % in the centre) and a marker toward where the hit came from. */
	void DrawHurt(const class AMIPlayerCharacter& Player, double Hurt);

	/** The story's next step (guide lane, docs/unreal/PLAY.md): its marker where it is, faded as the player closes in, or
	 *  an arrow on the screen's edge when it is off the screen or behind, with the distance in metres. */
	void DrawStepMarker(const FVector& WebPos, const FString& Code, bool bExit, double Metres, double Fade);

	FDelegateHandle HitHandle;
	TWeakObjectPtr<class AMIGuide> Guide;
	/** A wedge on the damage ring: where the hit came from (world, cm) and the world second it landed. */
	struct FWedge
	{
		FVector From = FVector::ZeroVector;
		double Time = 0.0;
	};
	TArray<FWedge> Wedges;
	static constexpr double WedgeHold = 1.5;  // seconds a wedge stays (full for the first half, then fading)
	/** The card the cursor was last seen on and where: the cursor selects a row only once it has moved on that card. */
	EMIMenuScreen HoverScreen = EMIMenuScreen::None;
	FVector2D HoverCursor = FVector2D::ZeroVector;
};
