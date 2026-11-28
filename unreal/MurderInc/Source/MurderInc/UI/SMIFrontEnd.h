#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"

class UMIFrontEnd;

/**
 * The set-up screens in Slate (docs/unreal/LOADOUT.md 2.2 - 2.8): Home, Crew, Loadout (the rack and the four slots),
 * Workbench (attachments), Block & Style and the Briefing, in the shared frame (letterbox, the left-to-right veil,
 * the step strip, kicker and title, Back and Next). The widget only draws UMIFrontEnd's rules and sends every click
 * and key back to it; it rebuilds when the rules' version changes. Sizes are 1080p units: the viewport's DPI scale
 * keeps it legible at 4K.
 */
class MURDERINC_API SMIFrontEnd : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SMIFrontEnd) {}
		SLATE_ARGUMENT(UMIFrontEnd*, Owner)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	virtual bool SupportsKeyboardFocus() const override { return true; }
	virtual FReply OnKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent) override;
	virtual FReply OnKeyUp(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent) override;
	virtual FReply OnMouseButtonDown(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent) override;
	virtual FReply OnMouseButtonUp(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent) override;
	virtual FReply OnMouseMove(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent) override;
	virtual FReply OnMouseWheel(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent) override;
	virtual FReply OnAnalogValueChanged(const FGeometry& MyGeometry, const FAnalogInputEvent& InAnalogInputEvent) override;
	virtual void Tick(const FGeometry& AllottedGeometry, const double InCurrentTime, const float InDeltaTime) override;

	/** The pointer entered or left a Workbench option (Arg: a part id or "factory"; Gen: the build the button belongs
	 *  to). A rebuild replaces the button under a resting pointer: the replaced button's leave is ignored and a second
	 *  look at the part already previewed changes nothing (docs/unreal/READY.md M1, the 20 Hz strobe). */
	void OptionHovered(const FString& Arg, int32 Gen);
	void OptionUnhovered(const FString& Arg, int32 Gen);
	/** Rebuilds the screen when the owner's rules changed. UMIFrontEnd::Tick calls it on the game thread, before Slate's
	 *  frame, so Slate measures the new screen before it draws it. True when it rebuilt. */
	bool Sync();
	/** Rebuilds so far (a test reads it: a pointer resting on an option must not rebuild the screen). */
	int32 GetBuildCount() const { return BuildGen; }

private:
	void Rebuild();
	/** Remembers the focused control of the screen being built (the scroll box brings it into view) and returns it. */
	TSharedRef<SWidget> Focusable(TSharedRef<SWidget> W, bool bFocused);
	/** A stopped hover: the preview of that part ends (and only that part's). */
	void EndHover();
	TSharedRef<SWidget> Frame(TSharedRef<SWidget> Body, bool bWideRight);
	TSharedRef<SWidget> StepStrip();
	TSharedRef<SWidget> Heading(const FString& Kicker, const FString& Title, float Width = 0.f);
	TSharedRef<SWidget> BottomBar();
	TSharedRef<SWidget> Home();
	TSharedRef<SWidget> Crew();
	TSharedRef<SWidget> Loadout();
	TSharedRef<SWidget> Workbench();
	/** The Loadout's parts panel: the focused gun's slots and their options, beside the rack (LOADOUT.md 2.6a). */
	TSharedRef<SWidget> PartsPanel();
	/** The share of the width the controls column takes on the screen being built (the Loadout's is wider). */
	float ColumnNow() const;
	/** The pointer rests on the button of this key, by where its last layout put it. A screen built again replaces the button under the
	 *  pointer, and Slate gives the new one its hover a frame or two after its first paint: a card or chip built meanwhile is given
	 *  the hover look at once, so it does not flip plain and back at every fit (the blink of the stream, DECISIONS.md 2026-11-28). */
	bool PointerOver(const FString& Key) const;
	void TrackHover(const FString& Key, const TSharedRef<SWidget>& W);
	TSharedRef<SWidget> Where();
	TSharedRef<SWidget> Briefing();
	TSharedRef<SWidget> GunCard(FName Gun, bool bFocused);
	TSharedRef<SWidget> Bars(FName Gun, const struct FMIGunBuild* Build, const struct FMIGunBuild* Ghost);
	TSharedRef<SWidget> ControlsGlance();
	/** True in the stream (Cloud/MICloud.h): the strip names P, not Esc, for Pause. */
	bool IsStreamed() const;

	TWeakObjectPtr<UMIFrontEnd> Owner;
	int32 Built = -1;
	int32 BuildGen = 0;
	/** The scroll box of the screen built last (the column, or the rack's) and the control that has the focus there. */
	TSharedPtr<class SScrollBox> Scroller;
	TSharedPtr<SWidget> FocusedWidget;
	/** The parts panel's scroll box and its focused option (the panel scrolls on its own, the rack's scroll box is Scroller). */
	TSharedPtr<class SScrollBox> PartsScroller;
	TSharedPtr<SWidget> PartsFocused;
	/** Screen, pane and focus of the last build: the focused control is scrolled into view only when it changes. */
	FString FocusKey;
	/** The pointer rests on a Workbench option: its part, the option button of the current build, ticks since the
	 *  build and ticks the pointer has been outside the button. */
	bool bHoverOn = false;
	FString HoverArg;
	TMap<FString, TWeakPtr<SWidget>> OptionButtons;
	/** The buttons of this build that can rest under the pointer, and where each stood after its layout. */
	TMap<FString, TWeakPtr<SWidget>> HoverWidgets;
	TMap<FString, FGeometry> HoverGeo;
	/** The rack's gun cards by gun: a card is built again only when what it shows changed (its signature), not on every
	 *  rebuild of the screen (a Loadout rebuild built six cards of about 40 widgets each for every key press). */
	TMap<FName, TPair<FString, TSharedPtr<SWidget>>> CardCache;
	int32 TicksSinceBuild = 0;
	int32 HoverOutside = 0;
	bool bDragging = false;
	FVector2D LastMouse = FVector2D::ZeroVector;
	FVector2D Stick = FVector2D::ZeroVector;
	float Triggers = 0.f;
};
