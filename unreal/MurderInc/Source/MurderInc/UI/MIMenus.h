#pragma once

#include "CoreMinimal.h"
#include "Flow/MIGameRules.h"
#include "Flow/MISettings.h"

/**
 * The menus as a model (src/menus.js, src/ui/panel.js): which screen is up, its lines and the selected item. The
 * HUD draws it; UMIGameSubsystem acts on the items. Copy from text.json (`text` and `interface`).
 */
enum class EMIMenuScreen : uint8 { None, Title, Pause, Settings, Dead, Debrief };

struct FMIMenuItem
{
	FName Id;          // start, mode, difficulty, time, settings, resume, restart, retry, again, totitle, sens, invert, volume, fov, view, quality, back
	FString Label;
	FString Value;     // shown right of the label for settings and pickers
	bool bAdjust = false;  // left / right change it
};

/** What the mouse is over on a card. */
struct FMIMenuHit
{
	int32 Row = INDEX_NONE;
	/** On an adjustable row: -1 its left half (the value before), +1 its right half (the value after). 0 on a button. */
	int32 Side = 0;
};

/**
 * Where a card's rows are on the canvas (pixels), as AMIHUD drew them last: what a click or the cursor hits. The rows
 * are one under the other, all of one size; the gaps between them and everything outside hit nothing.
 */
struct MURDERINC_API FMIMenuLayout
{
	EMIMenuScreen Screen = EMIMenuScreen::None;  // None: no card is on screen
	double X = 0.0;          // the rows' left edge
	double Width = 0.0;
	double Top = 0.0;        // the first row's top
	double RowHeight = 0.0;
	double RowGap = 0.0;
	TArray<bool> Adjust;     // one per row: true when left / right change its value

	void Reset() { *this = FMIMenuLayout(); }
	FMIMenuHit HitTest(const FVector2D& Point) const;
};

struct MURDERINC_API FMIMenu
{
	EMIMenuScreen Screen = EMIMenuScreen::None;
	EMIMenuScreen Return = EMIMenuScreen::None;  // where Settings goes back to
	FString Kicker, Title, Note;
	TArray<TPair<FString, FString>> Stats;
	TArray<FMIMenuItem> Items;
	int32 Selected = 0;
	/** Written by the HUD each frame it draws the card (reset when it draws none). */
	FMIMenuLayout Layout;

	/** The row of this card under Point, if the layout is this card's (same screen, same number of rows). */
	FMIMenuHit HitTest(const FVector2D& Point) const;

	/** Rebuilds the lines of Screen from the settings and the run card (the selection is kept when it still fits). */
	void Build(EMIMenuScreen InScreen, const FMISettings& Settings, const FMIText& Copy, const FMIText& Ui, const TOptional<FMIRunCard>& Card, FName Mode);
	const FMIMenuItem* Current() const { return Items.IsValidIndex(Selected) ? &Items[Selected] : nullptr; }
	void Move(int32 Dy) { if (Items.Num() > 0) Selected = (Selected + Dy + Items.Num()) % Items.Num(); }
	int32 IndexOf(FName Id) const { return Items.IndexOfByPredicate([Id](const FMIMenuItem& I) { return I.Id == Id; }); }
};
