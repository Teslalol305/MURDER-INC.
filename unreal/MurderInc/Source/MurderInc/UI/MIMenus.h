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

struct MURDERINC_API FMIMenu
{
	EMIMenuScreen Screen = EMIMenuScreen::None;
	EMIMenuScreen Return = EMIMenuScreen::None;  // where Settings goes back to
	FString Kicker, Title, Note;
	TArray<TPair<FString, FString>> Stats;
	TArray<FMIMenuItem> Items;
	int32 Selected = 0;

	/** Rebuilds the lines of Screen from the settings and the run card (the selection is kept when it still fits). */
	void Build(EMIMenuScreen InScreen, const FMISettings& Settings, const FMIText& Copy, const FMIText& Ui, const TOptional<FMIRunCard>& Card, FName Mode);
	const FMIMenuItem* Current() const { return Items.IsValidIndex(Selected) ? &Items[Selected] : nullptr; }
	void Move(int32 Dy) { if (Items.Num() > 0) Selected = (Selected + Dy + Items.Num()) % Items.Num(); }
	int32 IndexOf(FName Id) const { return Items.IndexOfByPredicate([Id](const FMIMenuItem& I) { return I.Id == Id; }); }
};
