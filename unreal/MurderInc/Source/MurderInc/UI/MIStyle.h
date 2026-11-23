#pragma once

#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"

class UFont;

/**
 * The brand look shared by the HUD and the front end (config.json brand.colors, spec 07 type: Anton for display,
 * Archivo for the interface). The fonts are read from Content/Fonts (Anton-Regular.ttf, Archivo.ttf: open-licensed
 * Google Fonts, fetched on the box, not committed); without them the engine's Roboto stands in.
 */
namespace MIStyle
{
	// config.json brand.colors
	MURDERINC_API FLinearColor Bg();
	MURDERINC_API FLinearColor Plate();
	MURDERINC_API FLinearColor PlateEdge();
	MURDERINC_API FLinearColor Ink();
	MURDERINC_API FLinearColor InkDim();
	MURDERINC_API FLinearColor InkFaint();
	MURDERINC_API FLinearColor Gold();
	MURDERINC_API FLinearColor Red();
	MURDERINC_API FLinearColor Oxblood();
	MURDERINC_API FLinearColor Cyan();
	/** The route-line colours (line1, line2, line3, IPX): the step strip's bullets. */
	MURDERINC_API FLinearColor Line(int32 Index);
	MURDERINC_API FLinearColor WithAlpha(const FLinearColor& C, float A);

	/** Slate fonts. Size in Slate units (1080p reference; the front end scales with the viewport). */
	MURDERINC_API FSlateFontInfo Display(float Size);
	MURDERINC_API FSlateFontInfo Body(float Size, bool bBold = false);
	/** Canvas fonts (runtime composite fonts from the same files). */
	MURDERINC_API UFont* CanvasDisplay();
	MURDERINC_API UFont* CanvasBody();
}
