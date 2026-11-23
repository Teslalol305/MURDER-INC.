#include "UI/SMIMark.h"

#include "Brushes/SlateRoundedBoxBrush.h"
#include "Rendering/DrawElements.h"

void SMIMark::Construct(const FArguments& InArgs)
{
	Kind = InArgs._Kind;
	Colour = InArgs._Colour;
	Size = InArgs._Size;
}

int32 SMIMark::OnPaint(const FPaintArgs& Args, const FGeometry& G, const FSlateRect& MyCullingRect, FSlateWindowElementList& Out, int32 LayerId,
	const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	const FLinearColor C = Colour * InWidgetStyle.GetColorAndOpacityTint();
	const float S = Size;
	if (Kind == EKind::Dot || Kind == EKind::Pip)
	{
		static const FSlateRoundedBoxBrush Round(FLinearColor::White, 99.f);
		static const FSlateRoundedBoxBrush Square(FLinearColor::White, 1.5f);
		const float D = Kind == EKind::Dot ? S * 0.42f : S * 0.8f;
		const FVector2f At((S - D) * 0.5f, (S - D) * 0.5f);
		FSlateDrawElement::MakeBox(Out, LayerId, G.ToPaintGeometry(FVector2f(D, D), FSlateLayoutTransform(At)), Kind == EKind::Dot ? &Round : &Square, ESlateDrawEffect::None, C);
		return LayerId;
	}
	// A filled triangle from one-unit scan lines (Slate has no polygon fill without a brush resource).
	const float Pad = S * 0.12f;
	const float Span = S - Pad * 2.f;
	const int32 Rows = FMath::Max(4, FMath::CeilToInt32(Span * 1.5f));
	TArray<FVector2f> Line;
	Line.SetNum(2);
	for (int32 I = 0; I < Rows; ++I)
	{
		const float T = (I + 0.5f) / Rows;      // 0 at the tip, 1 at the base
		const float Along = Pad + Span * T;     // distance from the tip side
		const float Half = Span * 0.5f * T;     // half width at this row
		const float Mid = S * 0.5f;
		switch (Kind)
		{
		case EKind::Up: Line[0] = FVector2f(Mid - Half, Along); Line[1] = FVector2f(Mid + Half, Along); break;
		case EKind::Down: Line[0] = FVector2f(Mid - Half, S - Along); Line[1] = FVector2f(Mid + Half, S - Along); break;
		case EKind::Left: Line[0] = FVector2f(Along, Mid - Half); Line[1] = FVector2f(Along, Mid + Half); break;
		default: Line[0] = FVector2f(S - Along, Mid - Half); Line[1] = FVector2f(S - Along, Mid + Half); break;
		}
		if (Half > 0.05f)
		{
			FSlateDrawElement::MakeLines(Out, LayerId, G.ToPaintGeometry(), Line, ESlateDrawEffect::None, C, true, Span * 1.2f / Rows + 0.4f);
		}
	}
	return LayerId;
}
