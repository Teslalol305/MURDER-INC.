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

private:
	void Rebuild();
	TSharedRef<SWidget> Frame(TSharedRef<SWidget> Body, bool bWideRight);
	TSharedRef<SWidget> StepStrip();
	TSharedRef<SWidget> Heading(const FString& Kicker, const FString& Title);
	TSharedRef<SWidget> BottomBar();
	TSharedRef<SWidget> Home();
	TSharedRef<SWidget> Crew();
	TSharedRef<SWidget> Loadout();
	TSharedRef<SWidget> Workbench();
	TSharedRef<SWidget> Where();
	TSharedRef<SWidget> Briefing();
	TSharedRef<SWidget> GunCard(FName Gun, bool bFocused);
	TSharedRef<SWidget> Bars(FName Gun, const struct FMIGunBuild* Build, const struct FMIGunBuild* Ghost);
	TSharedRef<SWidget> ControlsGlance();

	TWeakObjectPtr<UMIFrontEnd> Owner;
	int32 Built = -1;
	bool bDragging = false;
	bool bShowControls = false;
	FVector2D LastMouse = FVector2D::ZeroVector;
	FVector2D Stick = FVector2D::ZeroVector;
	float Triggers = 0.f;
};
