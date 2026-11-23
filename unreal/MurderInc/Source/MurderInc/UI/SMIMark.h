#pragma once

#include "CoreMinimal.h"
#include "Widgets/SLeafWidget.h"

/**
 * A small mark drawn as a shape, never as a character, so it shows whatever the font (LOADOUT.md 2.6: an effect line
 * starts with up for better, down for worse, a dot for neutral; the Workbench's previous / next gun arrows; the
 * attachment pips). Size in Slate units.
 */
class MURDERINC_API SMIMark : public SLeafWidget
{
public:
	enum class EKind : uint8 { Up, Down, Dot, Left, Right, Pip };

	SLATE_BEGIN_ARGS(SMIMark) : _Kind(EKind::Dot), _Colour(FLinearColor::White), _Size(12.f) {}
		SLATE_ARGUMENT(EKind, Kind)
		SLATE_ARGUMENT(FLinearColor, Colour)
		SLATE_ARGUMENT(float, Size)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);
	virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(Size, Size); }
	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;

	/** The kind for an effect line's sign (+1 better, -1 worse, 0 neutral). */
	static EKind ForSign(int32 Sign) { return Sign > 0 ? EKind::Up : Sign < 0 ? EKind::Down : EKind::Dot; }

private:
	EKind Kind = EKind::Dot;
	FLinearColor Colour = FLinearColor::White;
	float Size = 12.f;
};
