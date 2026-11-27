#include "UI/SMIFrontEnd.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

#include "Brushes/SlateColorBrush.h"
#include "Brushes/SlateImageBrush.h"
#include "Engine/Texture2D.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "Cloud/MICloud.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Flow/MIGameSubsystem.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/SlateTypes.h"
#include "UI/MIFrontEnd.h"
#include "UI/MIShowroom.h"
#include "UI/MIStyle.h"
#include "UI/SMIMark.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace MIFrontEndUI
{
	using namespace MIStyle;

	/** The smallest text on the set-up screens (LOADOUT.md 2.2: read on a television from a sofa). */
	constexpr float MinText = 14.f;
	/** The controls column: the left 40 % of the screen, under the veil (2.2). Nothing is drawn right of it but the
	 *  stage, so no panel can cover the gun at any aspect ratio. */
	constexpr float Column = 0.40f;

	/** The veil's soft edge as one horizontal gradient (review 2026-11-24: eight stacked translucent strips showed as
	 *  hard vertical bands across the sky): a transient 512 x 1 texture, the background colour with alpha falling from
	 *  0.88 to 0 by a smooth step, kept for the life of the process. */
	const FSlateBrush* FadeBrush()
	{
		static TSharedPtr<FSlateBrush> Brush;
		if (Brush.IsValid())
		{
			return Brush.Get();
		}
		constexpr int32 N = 512;
		UTexture2D* Tex = UTexture2D::CreateTransient(N, 1, PF_B8G8R8A8);
		if (!Tex)
		{
			Brush = MakeShared<FSlateColorBrush>(WithAlpha(Bg(), 0.44f));
			return Brush.Get();
		}
		Tex->SRGB = true;
		Tex->Filter = TF_Bilinear;
		Tex->AddressX = TA_Clamp;
		Tex->AddressY = TA_Clamp;
		Tex->AddToRoot();
		const FColor C = Bg().ToFColor(true);
		FTexture2DMipMap& Mip = Tex->GetPlatformData()->Mips[0];
		FColor* Px = static_cast<FColor*>(Mip.BulkData.Lock(LOCK_READ_WRITE));
		for (int32 I = 0; I < N; ++I)
		{
			const float T = (I + 0.5f) / N;
			const float A = 0.88f * (1.f - FMath::SmoothStep(0.f, 1.f, T));
			Px[I] = FColor(C.R, C.G, C.B, static_cast<uint8>(FMath::Clamp(FMath::RoundToInt32(A * 255.f), 0, 255)));
		}
		Mip.BulkData.Unlock();
		Tex->UpdateResource();
		Brush = MakeShared<FSlateImageBrush>(Tex, FVector2D(N, 1));
		return Brush.Get();
	}

	/** Brushes live as long as the process (Slate holds raw pointers to them). */
	const FSlateBrush* Box(const FLinearColor& Fill, float Radius = 6.f, const FLinearColor& Edge = FLinearColor::Transparent, float EdgeWidth = 0.f)
	{
		static TMap<FString, TSharedPtr<FSlateBrush>> Cache;
		const FString Key = FString::Printf(TEXT("%s|%.1f|%s|%.1f"), *Fill.ToString(), Radius, *Edge.ToString(), EdgeWidth);
		if (const TSharedPtr<FSlateBrush>* Have = Cache.Find(Key))
		{
			return Have->Get();
		}
		TSharedPtr<FSlateBrush> B;
		if (Radius > 0.f || EdgeWidth > 0.f)
		{
			B = MakeShared<FSlateRoundedBoxBrush>(Fill, Radius, Edge, EdgeWidth);
		}
		else
		{
			B = MakeShared<FSlateColorBrush>(Fill);
		}
		Cache.Add(Key, B);
		return B.Get();
	}

	// Every button of the screens clicks on the press (EButtonClickMethod::MouseDown): a screen rebuilt between the press
	// and the release (the pointer leaving a Workbench option ends its preview on the way to DONE) replaced the pressed
	// button, and the release on its successor clicked nothing (menu fixer's stream run mf2-after: DONE took two clicks).
	enum class EBtn : uint8 { Primary, Quiet, Card, Link, Chip };

	/** Styles live as long as the process, each in its own allocation: SButton keeps a raw pointer to its style, and a
	 *  pointer into a growing TMap of values went stale when the map reallocated (the first screen, built before the
	 *  game thread's first rebuild, was painted with freed styles: the menu fixer's run mf2-after3 crashed in
	 *  SButton::OnPaint on frame 0). */
	const FButtonStyle* ButtonStyle(EBtn Kind, bool bSelected = false)
	{
		static TMap<int32, TUniquePtr<FButtonStyle>> Cache;
		const int32 Key = static_cast<int32>(Kind) * 2 + (bSelected ? 1 : 0);
		if (const TUniquePtr<FButtonStyle>* Have = Cache.Find(Key))
		{
			return Have->Get();
		}
		FButtonStyle S;
		FLinearColor Normal, Hover, Press, Edge = FLinearColor::Transparent;
		float Radius = 6.f, EdgeW = 0.f;
		switch (Kind)
		{
		case EBtn::Primary: Normal = Gold(); Hover = FLinearColor(1.f, 0.85f, 0.3f); Press = FLinearColor(0.8f, 0.6f, 0.05f); break;
		case EBtn::Quiet: Normal = WithAlpha(Plate(), 0.85f); Hover = WithAlpha(PlateEdge(), 0.95f); Press = WithAlpha(Bg(), 0.95f); Edge = PlateEdge(); EdgeW = 1.f; break;
		case EBtn::Card: Normal = WithAlpha(Plate(), 0.9f); Hover = FLinearColor(0.035f, 0.038f, 0.045f, 0.95f); Press = WithAlpha(Bg(), 0.95f); Edge = bSelected ? Gold() : PlateEdge(); EdgeW = bSelected ? 2.f : 1.f; Radius = 8.f; break;
		case EBtn::Link: Normal = FLinearColor::Transparent; Hover = WithAlpha(PlateEdge(), 0.6f); Press = WithAlpha(PlateEdge(), 0.9f); Radius = 4.f; break;
		case EBtn::Chip: Normal = bSelected ? WithAlpha(Gold(), 0.95f) : WithAlpha(Plate(), 0.85f); Hover = bSelected ? Gold() : WithAlpha(PlateEdge(), 0.95f); Press = Hover; Edge = bSelected ? Gold() : PlateEdge(); EdgeW = 1.f; Radius = 16.f; break;
		}
		S.SetNormal(*Box(Normal, Radius, Edge, EdgeW));
		S.SetHovered(*Box(Hover, Radius, Kind == EBtn::Card ? Gold() : Edge, Kind == EBtn::Card ? 2.f : EdgeW));
		S.SetPressed(*Box(Press, Radius, Edge, EdgeW));
		// A disabled primary (NEXT with nothing to go on with) keeps a readable button: a faint gold fill and a gold edge, its label in
		// the dim ink (POLISH.md 3: the label was the page colour on a 40 % plate and could not be seen).
		if (Kind == EBtn::Primary)
		{
			S.SetDisabled(*Box(WithAlpha(Gold(), 0.22f), Radius, WithAlpha(Gold(), 0.55f), 1.f));
		}
		else
		{
			S.SetDisabled(*Box(WithAlpha(Plate(), 0.4f), Radius, WithAlpha(PlateEdge(), 0.4f), EdgeW));
		}
		S.SetNormalPadding(FMargin(0));
		S.SetPressedPadding(FMargin(0));
		return Cache.Add(Key, MakeUnique<FButtonStyle>(S)).Get();
	}

	/** Text: wrapped to the space it gets, or cut with an ellipsis; never below MinText. */
	TSharedRef<STextBlock> Txt(const FString& T, FSlateFontInfo Font, const FLinearColor& Colour, bool bWrap = false)
	{
		Font.Size = FMath::Max(Font.Size, MinText);
		return SNew(STextBlock).Text(FText::FromString(T)).Font(Font).ColorAndOpacity(FSlateColor(Colour)).AutoWrapText(bWrap)
			.OverflowPolicy(bWrap ? ETextOverflowPolicy::Clip : ETextOverflowPolicy::Ellipsis);
	}

	FSlateFontInfo Spaced(FSlateFontInfo F, int32 Spacing)
	{
		F.LetterSpacing = Spacing;
		return F;
	}

	/** A key or button name in a small plate (frontend.glyphs.*); nothing when the device has none. */
	TSharedRef<SWidget> Key(const FString& Glyph, const FLinearColor& Ink1, const FLinearColor& Plate1)
	{
		if (Glyph.IsEmpty())
		{
			return SNullWidget::NullWidget;
		}
		return SNew(SBorder).BorderImage(Box(Plate1, 4.f)).Padding(FMargin(6.f, 1.f)).VAlign(VAlign_Center)[Txt(Glyph.ToUpper(), Body(MinText, true), Ink1)];
	}

	/** A focus ring around a control (keyboard and pad focus), gold. The content sits inside the ring's padding, so the
	 *  ring never crosses a label. */
	TSharedRef<SWidget> Ring(TSharedRef<SWidget> Inner, bool bFocused, float Radius = 8.f, float Pad = 6.f)
	{
		return SNew(SBorder)
			.BorderImage(bFocused ? Box(FLinearColor::Transparent, Radius + Pad, Gold(), 2.f) : Box(FLinearColor::Transparent, 0.f))
			.Padding(Pad)
			[Inner];
	}

	/** A 0..1 bar with an optional ghost (the value before a change on the Workbench). */
	TSharedRef<SWidget> Bar(double Value, double Ghost, float Width)
	{
		const double V = FMath::Clamp(Value, 0.0, 1.0);
		const double G = Ghost < 0.0 ? V : FMath::Clamp(Ghost, 0.0, 1.0);
		const FLinearColor Fill = Ghost < 0.0 || FMath::IsNearlyEqual(V, G) ? Ink() : (V > G ? FLinearColor(0.35f, 0.85f, 0.45f) : FLinearColor(0.95f, 0.35f, 0.3f));
		return SNew(SBox).WidthOverride(Width).HeightOverride(7.f)
			[
				SNew(SOverlay)
				+ SOverlay::Slot()[SNew(SImage).Image(Box(WithAlpha(PlateEdge(), 0.9f), 3.f))]
				+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).WidthOverride(Width * static_cast<float>(FMath::Max(V, G)))[SNew(SImage).Image(Box(WithAlpha(Ink(), 0.28f), 3.f))]]
				+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).WidthOverride(Width * static_cast<float>(V))[SNew(SImage).Image(Box(Fill, 3.f))]]
			];
	}

	/** n gold pips: the parts fitted beyond the factory build (shapes, not characters). */
	TSharedRef<SWidget> Pips(int32 N, float Size = 10.f)
	{
		TSharedRef<SHorizontalBox> Row = SNew(SHorizontalBox);
		for (int32 P = 0; P < N; ++P)
		{
			Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0.f, 0.f, 3.f, 0.f)[SNew(SMIMark).Kind(SMIMark::EKind::Pip).Colour(Gold()).Size(Size)];
		}
		return Row;
	}

	int32 CountPips(const FMIFrontEndRules& R, FName Gun)
	{
		int32 N = 0;
		if (const FMIGunBuild* B = R.GetSetup().BuildOf(Gun))
		{
			for (const TPair<FName, FName>& P : B->Parts)
			{
				const FMIAttachmentDef* D = R.GetData().FindPart(P.Value);
				N += D && !D->bBaseline ? 1 : 0;
			}
		}
		return N;
	}

	/** The width of the controls column in Slate units (the viewport's width x Column, less the column's padding), from
	 *  the last frame the screens were given. */
	float ColumnWidth = 690.f;

	/** A wrap box that wraps at the room it gets. Until its first paint a wrap box wraps at its preferred size (100 units
	 *  by default): a rebuilt screen was laid out once with every chip and card on a line of its own (taller, the rest
	 *  pushed down) and then once right, a one-frame jump in the stream. Less is the room the box loses inside the column
	 *  (labels, ring and card padding), so the first layout is already the right one. */
	TSharedRef<SWrapBox> Wrap(float Gap = 8.f, float Less = 0.f)
	{
		return SNew(SWrapBox).UseAllottedSize(true).PreferredSize(FMath::Max(100.f, ColumnWidth - Less)).InnerSlotPadding(FVector2D(Gap, Gap));
	}

	/** An effect line's text without its leading mark character (the mark is drawn as a shape beside it). */
	FString WithoutMark(const FString& Line)
	{
		static const FString Marks = TEXT("▲▼•");
		int32 I = 0;
		while (I < Line.Len() && (Marks.Contains(FString::Chr(Line[I])) || Line[I] == TEXT(' ')))
		{
			++I;
		}
		return Line.Mid(I);
	}
}

using namespace MIFrontEndUI;

void SMIFrontEnd::Construct(const FArguments& InArgs)
{
	Owner = InArgs._Owner;
	SetCanTick(true);
	Rebuild();
}

void SMIFrontEnd::Tick(const FGeometry& AllottedGeometry, const double InCurrentTime, const float InDeltaTime)
{
	TRACE_CPUPROFILER_EVENT_SCOPE_STR("MI/SMIFrontEnd::Tick");
	SCompoundWidget::Tick(AllottedGeometry, InCurrentTime, InDeltaTime);
	++TicksSinceBuild;
	// A pointer that left a Workbench option while the screen was being rebuilt never sends a leave (the button it
	// left was replaced): once the new buttons have been painted, a pointer outside the hovered option ends its
	// preview.
	if (bHoverOn && TicksSinceBuild > 2 && FSlateApplication::IsInitialized())
	{
		const TWeakPtr<SWidget>* Btn = OptionButtons.Find(HoverArg);
		const TSharedPtr<SWidget> B = Btn ? Btn->Pin() : nullptr;
		const FVector2D Cursor = FSlateApplication::Get().GetCursorPos();
		const bool bInside = B.IsValid() && (B->IsHovered() || B->GetTickSpaceGeometry().IsUnderLocation(Cursor));
		HoverOutside = bInside ? 0 : HoverOutside + 1;
		if (HoverOutside >= 2)
		{
			EndHover();
		}
	}
	// The screens are rebuilt in Sync, on the game thread before Slate's frame, never here: Slate ticks a widget while
	// it paints it, after that frame's layout pass, and a screen rebuilt here was drawn once with every control at zero
	// size, piled at the top of the column (the flash on every screen change in the stream, READY.md M1). Measuring the
	// new screen here instead left its wrap boxes measured at their default width and its layout stale until the next
	// rebuild (menu fixer's stream run mf2-after).
	ColumnWidth = FMath::Max(100.f, static_cast<float>(AllottedGeometry.GetLocalSize().X) * Column - (56.f + 22.f));
	if (Owner.IsValid() && Owner->GetShowroom() && (Stick.SizeSquared() > 0.0 || Triggers != 0.f))
	{
		Owner->GetShowroom()->Stick(Stick, Triggers);
	}
}

bool SMIFrontEnd::Sync()
{
	if (!Owner.IsValid() || Owner->GetVersion() == Built)
	{
		return false;
	}
	Rebuild();
	return true;
}

void SMIFrontEnd::Rebuild()
{
	if (!Owner.IsValid())
	{
		return;
	}
	Built = Owner->GetVersion();
	++BuildGen;
	TicksSinceBuild = 0;
	HoverOutside = 0;
	OptionButtons.Reset();
	// Every build makes new scroll boxes: the new one starts where the old one was on the same screen, and scrolls the
	// focused control into view when the focus moved (keyboard and pad focus never sits under the bottom bar, M5).
	const EMIFrontScreen Screen = Owner->GetRules().GetScreen();
	const FString Key = FString::Printf(TEXT("%s|%d|%d|%d"), *FMIFrontEndRules::ScreenName(Screen), Owner->Pane, Owner->FocusShown(), Owner->bOnNext ? 1 : 0);
	const FString ScreenWas = FocusKey.Left(FocusKey.Find(TEXT("|")));
	const float Offset = Scroller.IsValid() && ScreenWas == FMIFrontEndRules::ScreenName(Screen) ? Scroller->GetScrollOffset() : 0.f;
	const bool bFocusMoved = Key != FocusKey;
	FocusKey = Key;
	Scroller.Reset();
	FocusedWidget.Reset();
	TSharedRef<SWidget> Body = SNullWidget::NullWidget;
	switch (Screen)
	{
	case EMIFrontScreen::Home: Body = Home(); break;
	case EMIFrontScreen::Crew: Body = Crew(); break;
	case EMIFrontScreen::Loadout: Body = Loadout(); break;
	case EMIFrontScreen::Workbench: Body = Workbench(); break;
	case EMIFrontScreen::Where: Body = Where(); break;
	case EMIFrontScreen::Briefing: Body = Briefing(); break;
	}
	ChildSlot[Body];
	if (Scroller.IsValid())
	{
		Scroller->SetScrollOffset(Offset);
		if (bFocusMoved && FocusedWidget.IsValid())
		{
			Scroller->ScrollDescendantIntoView(FocusedWidget, false, EDescendantScrollDestination::IntoView, 12.f);
		}
	}
}

TSharedRef<SWidget> SMIFrontEnd::Focusable(TSharedRef<SWidget> W, bool bFocused)
{
	if (bFocused)
	{
		FocusedWidget = W;
	}
	return W;
}

void SMIFrontEnd::OptionHovered(const FString& Arg, int32 Gen)
{
	if (Owner.IsValid() && Owner->HoverBlocked())
	{
		return;  // the rebuild after a fit re-announces the hover of a pointer that has not moved (PLAY.md E7)
	}
	bHoverOn = true;
	HoverArg = Arg;
	HoverOutside = 0;
	if (Owner.IsValid())
	{
		Owner->Act(TEXT("preview"), Arg);  // the part already previewed: nothing changes, no rebuild, no sound
	}
}

void SMIFrontEnd::OptionUnhovered(const FString& Arg, int32 Gen)
{
	if (Gen != BuildGen || !bHoverOn || Arg != HoverArg)
	{
		return;  // a button the last rebuild replaced (its successor takes the hover), or not the hovered one
	}
	EndHover();
}

void SMIFrontEnd::EndHover()
{
	bHoverOn = false;
	HoverOutside = 0;
	if (!Owner.IsValid())
	{
		return;
	}
	FMIFrontEndRules& R = Owner->GetRules();
	const FName Part = HoverArg == TEXT("factory") ? NAME_None : FName(*HoverArg);
	if (R.IsPreviewing() && R.GetPreviewed() == Part)
	{
		R.StopPreview();  // only its own preview: a part the keyboard moved to stays shown
		Owner->Changed();
	}
}

// ------------------------------------------------------------------------------------------------ the frame

TSharedRef<SWidget> SMIFrontEnd::Frame(TSharedRef<SWidget> Body, bool bScroll)
{
	// The veil: the left 40 % holds the controls, the rest shows the stage; a soft edge as one smooth gradient.
	TSharedRef<SHorizontalBox> Veil = SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().FillWidth(Column)[SNew(SImage).Image(Box(WithAlpha(Bg(), 0.88f), 0.f))];
	Veil->AddSlot().FillWidth(0.16f)[SNew(SImage).Image(FadeBrush())];
	Veil->AddSlot().FillWidth(1.f - Column - 0.16f)[SNullWidget::NullWidget];
	TSharedRef<SWidget> Content = Body;
	if (bScroll)
	{
		TSharedRef<SScrollBox> Box1 = SNew(SScrollBox) + SScrollBox::Slot()[Body];
		Scroller = Box1;
		Content = Box1;
	}
	return SNew(SOverlay)
		+ SOverlay::Slot()[Veil]
		// Letterbox bars.
		+ SOverlay::Slot().VAlign(VAlign_Top)[SNew(SBox).HeightOverride(46.f)[SNew(SImage).Image(Box(FLinearColor::Black, 0.f))]]
		+ SOverlay::Slot().VAlign(VAlign_Bottom)[SNew(SBox).HeightOverride(46.f)[SNew(SImage).Image(Box(FLinearColor::Black, 0.f))]]
		// Every control lives in the column: the step strip, the screen, the bottom bar.
		+ SOverlay::Slot()
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(Column).Padding(FMargin(56.f, 62.f, 22.f, 58.f))
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()[StepStrip()]
				+ SVerticalBox::Slot().FillHeight(1.f).Padding(0.f, 16.f, 0.f, 12.f)[Content]
				+ SVerticalBox::Slot().AutoHeight()[BottomBar()]
			]
			+ SHorizontalBox::Slot().FillWidth(1.f - Column)[SNullWidget::NullWidget]
		];
}

TSharedRef<SWidget> SMIFrontEnd::StepStrip()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	const TArray<FString> Labels = R.GetData().TextList(TEXT("frontend.steps.labels"));
	const int32 Current = FMIFrontEndRules::StepOf(R.GetScreen());
	if (Current == 0)
	{
		return SNew(SBox).HeightOverride(24.f);
	}
	TSharedRef<SWrapBox> Row = Wrap(4.f);
	for (int32 I = 0; I < Labels.Num(); ++I)
	{
		const int32 Step = I + 1;
		const bool bDone = Step < Current;
		const bool bNow = Step == Current;
		const FLinearColor C = Line(FMath::Min(I, 3));
		TWeakObjectPtr<UMIFrontEnd> O = Owner;
		Row->AddSlot()
		[
			SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Link)).IsEnabled(R.IsStepReachable(Step)).ContentPadding(FMargin(2.f, 2.f, 10.f, 2.f))
			.OnClicked_Lambda([O, Step]() { if (O.IsValid()) O->Act(TEXT("step"), FString::FromInt(Step)); return FReply::Handled(); })
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(2.f)
				[
					SNew(SBox).WidthOverride(14.f).HeightOverride(14.f)
					[SNew(SImage).Image(Box(bDone || bNow ? C : FLinearColor::Transparent, 7.f, bNow ? Ink() : C, 2.f))]
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6.f, 0.f, 0.f, 0.f)
				[Txt(Labels[I].ToUpper(), Spaced(Body(MinText, true), 140), bNow ? Ink() : InkDim())]
			]
		];
	}
	return Row;
}

TSharedRef<SWidget> SMIFrontEnd::Heading(const FString& Kicker, const FString& Title)
{
	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Txt(Kicker.ToUpper(), Spaced(Body(MinText, true), 220), InkDim())]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 2.f, 0.f, 0.f)[Txt(Title.ToUpper(), Display(50.f), Ink(), true)];
}

TSharedRef<SWidget> SMIFrontEnd::BottomBar()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	const EMIFrontScreen S = R.GetScreen();
	if (S == EMIFrontScreen::Home)
	{
		return SNullWidget::NullWidget;
	}
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	const FString Blocked = R.NextBlocked();
	FString NextLabel = R.Text(R.IsEditMode() || S == EMIFrontScreen::Workbench ? TEXT("frontend.steps.done") : TEXT("frontend.steps.next"));
	if (S == EMIFrontScreen::Briefing)
	{
		NextLabel = R.Text(TEXT("frontend.briefing.go"));
	}
	const bool bNextFocused = Owner->bOnNext || (S == EMIFrontScreen::Briefing && Owner->Focus == 4);
	const FString Note = Blocked.IsEmpty() ? R.LastMessage : Blocked;
	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, Note.IsEmpty() ? 0.f : 8.f)
		[Txt(Note, Body(MinText), Blocked.IsEmpty() ? InkDim() : Red(), true)]
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				Ring(SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(18.f, 10.f))
				.OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("back")); return FReply::Handled(); })
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Txt(R.Text(TEXT("frontend.steps.back")).ToUpper(), Spaced(Body(16.f, true), 140), Ink())]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(10.f, 0.f, 0.f, 0.f)[Key(Owner->Glyph(TEXT("back")), InkDim(), WithAlpha(PlateEdge(), 0.9f))]
				], false, 6.f, 3.f)
			]
			+ SHorizontalBox::Slot().FillWidth(1.f)[SNullWidget::NullWidget]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
			[
				Ring(SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Primary)).ContentPadding(FMargin(24.f, 10.f)).IsEnabled(Blocked.IsEmpty())
				.OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("next")); return FReply::Handled(); })
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Txt(NextLabel.ToUpper(), Display(24.f), Blocked.IsEmpty() ? Bg() : InkDim())]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(12.f, 0.f, 0.f, 0.f)[Key(Owner->Glyph(TEXT("next")), Blocked.IsEmpty() ? Bg() : InkDim(), WithAlpha(Blocked.IsEmpty() ? Bg() : InkDim(), 0.16f))]
				], bNextFocused, 6.f, 3.f)
			]
		];
}

// ------------------------------------------------------------------------------------------------ Home

TSharedRef<SWidget> SMIFrontEnd::Home()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	const FMIRunSetup& S = R.GetSetup();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	const int32 F = Owner->FocusShown();
	const auto Picker = [&](int32 Index, const FString& Label, const TCHAR* Which, const TArray<FName>& Values, FName Now)
	{
		TSharedRef<SWrapBox> Chips = Wrap(6.f, 124.f + 2.f * 14.f);  // beside the 124-unit label, inside the ring
		for (const FName V : Values)
		{
			const FString Name = Which == FString(TEXT("mode")) ? R.Text(TEXT("text.modes.") + V.ToString() + TEXT(".name"))
				: Which == FString(TEXT("difficulty")) ? R.Text(TEXT("text.difficulties.") + V.ToString()) : R.Text(TEXT("frontend.level.times.") + V.ToString());
			const FString W(Which);
			Chips->AddSlot()
			[
				SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Chip, V == Now)).ContentPadding(FMargin(14.f, 5.f))
				.OnClicked_Lambda([O, W, V]() { if (O.IsValid()) O->Act(W, V.ToString()); return FReply::Handled(); })
				[Txt(Name.ToUpper(), Spaced(Body(MinText, true), 100), V == Now ? Bg() : InkDim())]
			];
		}
		return Focusable(Ring(SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).WidthOverride(124.f)[Txt(Label.ToUpper(), Spaced(Body(MinText, true), 160), InkFaint())]]
			+ SHorizontalBox::Slot().FillWidth(1.f)[Chips], F == Index, 14.f), F == Index);
	};
	const FMISettings::FRules& SR = Owner->GetGame()->GetSettings().Rules;
	// The summary line: each part is a link that opens its screen in edit mode.
	TArray<FString> Guns;
	for (const FName G : S.Guns) Guns.Add(R.GunName(G));
	const auto Link = [&](int32 Index, const FString& Label, const TCHAR* Screen)
	{
		const FString Sc(Screen);
		return Ring(SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Link)).ContentPadding(FMargin(6.f, 3.f))
			.OnClicked_Lambda([O, Sc]() { if (O.IsValid()) O->Act(TEXT("edit"), Sc); return FReply::Handled(); })
			[Txt(Label, Body(16.f, true), Ink())], F == Index, 4.f, 3.f);
	};
	const FMILevelEntry* Level = R.GetData().Levels.Find(S.Level);
	const FString Dot = TEXT("·");
	TSharedRef<SWrapBox> Summary = Wrap(4.f);
	Summary->AddSlot()[Link(5, R.CrewName(S.Crew), TEXT("crew"))];
	Summary->AddSlot().VAlign(VAlign_Center)[Txt(Dot, Body(16.f), InkFaint())];
	Summary->AddSlot()[Link(6, FString::Join(Guns, TEXT(" / ")), TEXT("loadout"))];
	Summary->AddSlot().VAlign(VAlign_Center)[Txt(Dot, Body(16.f), InkFaint())];
	Summary->AddSlot()[Link(7, (Level ? R.Text(Level->TextKey + TEXT(".name")) : FString()) + TEXT("  ") + Dot + TEXT("  ") + R.Text(TEXT("frontend.level.times.") + S.Time.ToString()), TEXT("where"))];

	TSharedRef<SVerticalBox> Col = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(TEXT("text.title.eyebrow")), Spaced(Body(15.f, true), 240), Gold(), true)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Txt(R.Text(TEXT("text.title.wordmark")), Display(96.f), Ink(), true)]
		+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(TEXT("text.title.star")), Spaced(Body(16.f, true), 280), InkDim(), true)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 14.f, 0.f, 20.f)[Txt(R.Text(TEXT("text.title.premise")), Body(18.f), Ink(), true)]
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				Ring(SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Primary)).ContentPadding(FMargin(30.f, 12.f))
				.OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("hit")); return FReply::Handled(); })
				[Txt(R.Text(TEXT("frontend.home.start")).ToUpper(), Display(32.f), Bg())], F == 0, 8.f)
			]
			+ SHorizontalBox::Slot().AutoWidth().Padding(10.f, 0.f, 0.f, 0.f).VAlign(VAlign_Center)
			[
				Ring(SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(20.f, 12.f))
				.OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("gearup")); return FReply::Handled(); })
				[Txt(R.Text(TEXT("frontend.home.setup")).ToUpper(), Spaced(Body(16.f, true), 140), Ink())], F == 1, 8.f)
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 8.f, 0.f, 0.f)[Summary]
		+ SVerticalBox::Slot().AutoHeight().Padding(6.f, 2.f, 0.f, 0.f)
		[Txt(S.bPlayed ? FString() : R.Text(TEXT("frontend.home.firstTime")), Body(MinText), Gold(), true)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 18.f, 0.f, 0.f)[Picker(2, R.Text(TEXT("text.interface.title.modeLabel")), TEXT("mode"), SR.Modes, S.Mode)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Picker(3, R.Text(TEXT("text.interface.title.difficultyLabel")), TEXT("difficulty"), SR.Difficulties, S.Difficulty)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Picker(4, R.Text(TEXT("text.interface.title.timeLabel")), TEXT("time"), SR.Times, S.Time)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 18.f, 0.f, 0.f)
		[
			SNew(SHorizontalBox)
			// Focus 8 and 9: the keyboard and the pad reach them too (READY.md M6).
			+ SHorizontalBox::Slot().AutoWidth()
			[
				Focusable(Ring(SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(16.f, 8.f))
				.OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("settings")); return FReply::Handled(); })
				[Txt(R.Text(TEXT("text.title.settings")).ToUpper(), Spaced(Body(MinText, true), 140), F == 8 ? Ink() : InkDim())], F == 8, 8.f, 3.f), F == 8)
			]
			+ SHorizontalBox::Slot().AutoWidth().Padding(10.f, 0.f, 0.f, 0.f)
			[
				Focusable(Ring(SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(16.f, 8.f))
				.OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("controls")); return FReply::Handled(); })
				[Txt(R.Text(TEXT("text.title.controls")).ToUpper(), Spaced(Body(MinText, true), 140), F == 9 ? Ink() : InkDim())], F == 9, 8.f, 3.f), F == 9)
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 14.f, 0.f, 0.f)[ControlsGlance()];
	return Frame(Col, true);
}

bool SMIFrontEnd::IsStreamed() const
{
	const UMIGameSubsystem* G = Owner.IsValid() ? Owner->GetGame() : nullptr;
	const UWorld* World = G ? G->GetWorld() : nullptr;
	const UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
	if (const UMICloudSubsystem* Cloud = GI ? GI->GetSubsystem<UMICloudSubsystem>() : nullptr)
	{
		return Cloud->IsStreamed();
	}
	return UMICloudSubsystem::IsStreamedByCommandLine();
}

TSharedRef<SWidget> SMIFrontEnd::ControlsGlance()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	// interface.glance (the web title's strip), then frontend.controls.<kbm|pad> (the new rows) when expanded.
	TArray<TPair<FString, FString>> Rows;
	const auto Read = [&Rows](const TSharedPtr<FJsonValue>& V)
	{
		if (!V.IsValid() || V->Type != EJson::Array) return;
		for (const TSharedPtr<FJsonValue>& Row : V->AsArray())
		{
			const TArray<TSharedPtr<FJsonValue>>& A = Row->AsArray();
			if (A.Num() < 2) continue;
			TArray<FString> Keys;
			for (const TSharedPtr<FJsonValue>& K : A[1]->AsArray()) Keys.Add(K->AsString());
			Rows.Add({A[0]->AsString(), FString::Join(Keys, TEXT(" "))});
		}
	};
	// With a controller in the hand the strip is the controller's list (interface.controls.pad: the web game's
	// Controls drawer), in the names chosen in Settings; the keyboard's strip told a controller player nothing.
	const bool bPad = Owner->IsPad();
	Read(MIJson::Get(R.TextJson, bPad ? TEXT("interface.controls.pad.rows") : TEXT("interface.glance")));
	if (bPad)
	{
		Rows.Add({TEXT("Grab"), TEXT("Hold X")});  // the drawer has it as a note on Reload
	}
	if (Owner->bShowControls || R.GetSetup().Guns.Num() >= R.GetData().WheelMinGuns)
	{
		Read(MIJson::Get(R.GetData().TextJson, bPad ? TEXT("frontend.controls.pad") : TEXT("frontend.controls.kbm")));
	}
	if (bPad)
	{
		for (TPair<FString, FString>& Row : Rows)
		{
			Row.Value = Owner->PadName(Row.Value);
		}
	}
	// In the stream (-MICloud, Cloud/MICloud.h) the browser keeps Esc to free the mouse: the keyboard's pause key
	// there is P, as the click-to-play card and the pause card say.
	if (!Owner->IsPad() && IsStreamed())
	{
		for (TPair<FString, FString>& Row : Rows)
		{
			if (Row.Key.Equals(TEXT("Pause"), ESearchCase::IgnoreCase))
			{
				Row.Value = TEXT("P");
			}
		}
	}
	// Wraps to the column: every row shows, none is cut.
	TSharedRef<SWrapBox> Strip = Wrap(6.f);
	int32 N = 0;
	for (const TPair<FString, FString>& Row : Rows)
	{
		if (!Owner->bShowControls && N++ >= 12) break;
		Strip->AddSlot()
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()[Key(Row.Value, Ink(), WithAlpha(PlateEdge(), 0.9f))]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6.f, 0.f, 8.f, 0.f)[Txt(Row.Key, Body(MinText), InkDim())]
		];
	}
	return Strip;
}

// ------------------------------------------------------------------------------------------------ Crew

TSharedRef<SWidget> SMIFrontEnd::Crew()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	TSharedRef<SWrapBox> Cards = Wrap(10.f);
	const TArray<FName> Offered = R.OfferedCrew();
	for (int32 I = 0; I < Offered.Num(); ++I)
	{
		const FName Id = Offered[I];
		const bool bSel = R.GetSetup().Crew == Id;
		Cards->AddSlot()
		[
			Focusable(Ring(SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Card, bSel)).ContentPadding(FMargin(16.f))
			.OnClicked_Lambda([O, Id]() { if (O.IsValid()) O->Act(TEXT("crew"), Id.ToString()); return FReply::Handled(); })
			[
				SNew(SBox).WidthOverride(200.f)
				[
					SNew(SVerticalBox)
					// The portrait: a card of the arms on the bench, never a face (T_UI_Crew_* missing: the name stands in).
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(SBox).HeightOverride(140.f)
						[
							SNew(SBorder).BorderImage(Box(FLinearColor(0.025f, 0.026f, 0.03f), 6.f, WithAlpha(PlateEdge(), 0.8f), 1.f)).HAlign(HAlign_Center).VAlign(VAlign_Center)
							[Txt(R.CrewName(Id), Display(56.f), bSel ? Gold() : WithAlpha(Ink(), 0.85f))]
						]
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 10.f, 0.f, 0.f)[Txt(R.CrewName(Id), Display(28.f), Ink())]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Txt(R.CrewTagline(Id), Body(MinText), InkDim(), true)]
				]
			], Owner->FocusShown() == I), Owner->FocusShown() == I)
		];
	}
	return Frame(SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Heading(R.Text(TEXT("frontend.crew.kicker")), R.Text(TEXT("frontend.crew.title")))]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 8.f, 0.f, 22.f)[Txt(R.Text(TEXT("frontend.crew.note")), Body(16.f), InkDim(), true)]
		+ SVerticalBox::Slot().AutoHeight()[Cards], true);
}

// ------------------------------------------------------------------------------------------------ Loadout

TSharedRef<SWidget> SMIFrontEnd::Bars(FName Gun, const FMIGunBuild* Build, const FMIGunBuild* Ghost)
{
	const FMIFrontEndRules& R = Owner->GetRules();
	const FMIGunBars B = R.Bars(Gun, Build);
	const FMIGunBars G = Ghost ? R.Bars(Gun, Ghost) : FMIGunBars();
	const TCHAR* Keys[] = {TEXT("damage"), TEXT("kill"), TEXT("control"), TEXT("handling"), TEXT("accuracy"), TEXT("hip")};
	const double Values[] = {B.Damage, B.Kill, B.Control, B.Handling, B.Aimed, B.Hip};
	const double Ghosts[] = {G.Damage, G.Kill, G.Control, G.Handling, G.Aimed, G.Hip};
	TSharedRef<SVerticalBox> Col = SNew(SVerticalBox);
	for (int32 I = 0; I < 6; ++I)
	{
		Col->AddSlot().AutoHeight().Padding(0.f, 1.f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).WidthOverride(88.f)[Txt(R.Text(FString(TEXT("frontend.loadout.stats.")) + Keys[I]), Body(MinText), InkFaint())]]
			+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)[Bar(Values[I], Ghost ? Ghosts[I] : -1.0, 84.f)]
		];
	}
	return Col;
}

TSharedRef<SWidget> SMIFrontEnd::GunCard(FName Gun, bool bFocused)
{
	const FMIFrontEndRules& R = Owner->GetRules();
	const FMIGunEntry* G = R.GetData().FindGun(Gun);
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	const int32 Slot = R.SlotOf(Gun);
	const FMIGunBuild* Build = R.GetSetup().BuildOf(Gun);
	const int32 Mag = G ? static_cast<int32>(MIJson::NumberOr(G->Rules, TEXT("magSize"), 0)) : 0;
	const bool bInfinite = G && !FMath::IsFinite(MIJson::NumberOr(G->Rules, TEXT("reserve"), 0));
	const TArray<FName> Slots = R.GetReadiness().OfferedSlots(Gun);
	const bool bSemiOnly = G && MIJson::Names(G->Extra, TEXT("fireModes")) == TArray<FName>{TEXT("semi")};
	const FString Tags = Slot != INDEX_NONE ? R.GetData().Format(TEXT("frontend.loadout.carried"), {{TEXT("n"), FString::FromInt(Slot + 1)}}) : FString();
	FString Info = R.Text(TEXT("frontend.loadout.stats.mag")).ToUpper() + TEXT(" ") + FString::FromInt(Mag);
	if (bInfinite) Info += TEXT(" / ") + R.Text(TEXT("frontend.loadout.stats.infinite"));
	if (bSemiOnly) Info += TEXT("  ") + R.Text(TEXT("frontend.loadout.stats.semi"));
	const FString SlotsLine = Slots.Num() > 0 ? R.GetData().Format(TEXT("frontend.loadout.slots"), {{TEXT("n"), FString::FromInt(Slots.Num())}}) : R.Text(TEXT("frontend.loadout.noSlots"));
	const bool bDev = !R.GetReadiness().IsGunReady(Gun);
	return Ring(SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Card, Slot != INDEX_NONE)).ContentPadding(FMargin(12.f, 10.f))
		.OnClicked_Lambda([O, Gun]() { if (O.IsValid()) O->Act(TEXT("carry"), Gun.ToString()); return FReply::Handled(); })
		[
			SNew(SBox).WidthOverride(176.f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().FillWidth(1.f)[Txt(R.GunName(Gun), Display(26.f), Ink())]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Top)
					[Txt(bDev ? R.Text(TEXT("frontend.loadout.devTag")) : R.IsNew(Gun) ? R.Text(TEXT("frontend.loadout.new")) : FString(), Body(MinText, true), bDev ? Red() : Gold())]
				]
				+ SVerticalBox::Slot().AutoHeight()[Txt(G ? R.Text(TEXT("frontend.loadout.classes.") + G->Class.ToString()).ToUpper() : FString(), Spaced(Body(MinText, true), 120), InkFaint())]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f)[Bars(Gun, Build, nullptr)]
				+ SVerticalBox::Slot().AutoHeight()[Txt(Info, Body(MinText), InkDim(), true)]
				+ SVerticalBox::Slot().AutoHeight()[Txt(SlotsLine, Body(MinText), InkDim(), true)]
				// The carried tag on a line of its own: beside the Attachments button the 176-unit row cut it to "..."
				// (READY.md M4). Every card keeps the line, so the cards of a row end level.
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 0.f)[Txt(Tags.IsEmpty() ? FString(TEXT(" ")) : Tags, Body(MinText, true), Gold())]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().FillWidth(1.f)[SNullWidget::NullWidget]
					+ SHorizontalBox::Slot().AutoWidth()
					[
						SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(6.f, 3.f)).Visibility(Slots.Num() > 0 ? EVisibility::Visible : EVisibility::Collapsed)
						.ToolTipText(FText::FromString(R.Text(TEXT("frontend.loadout.attachments"))))
						.OnClicked_Lambda([O, Gun]() { if (O.IsValid()) O->Act(TEXT("bench"), Gun.ToString()); return FReply::Handled(); })
						[
							SNew(SHorizontalBox)
							+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Key(Owner->Glyph(TEXT("bench")), Ink(), WithAlpha(PlateEdge(), 0.9f))]
							+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(4.f, 0.f, 0.f, 0.f)[Txt(R.Text(TEXT("frontend.loadout.attachments")), Body(MinText, true), Ink())]
						]
					]
				]
			]
		], bFocused);
}

TSharedRef<SWidget> SMIFrontEnd::Loadout()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	const int32 F = Owner->FocusShown();
	// Class tabs.
	TSharedRef<SWrapBox> Tabs = Wrap(6.f);
	for (const TCHAR* Filt : {TEXT("all"), TEXT("rifle"), TEXT("smg"), TEXT("pistol"), TEXT("new")})
	{
		const FName Filter(Filt);
		const bool bOn = Owner->RackFilter == Filter;
		Tabs->AddSlot()
		[
			SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Chip, bOn)).ContentPadding(FMargin(12.f, 4.f))
			.OnClicked_Lambda([O, Filter]() { if (O.IsValid()) O->Act(TEXT("filter"), Filter.ToString()); return FReply::Handled(); })
			[Txt(R.Text(FString(TEXT("frontend.loadout.filters.")) + Filt).ToUpper(), Spaced(Body(MinText, true), 100), bOn ? Bg() : InkDim())]
		];
	}
	// The rack: as many cards a row as the column holds (three at 16:9).
	const TArray<FName> Rack = R.Rack(Owner->RackFilter);
	TSharedRef<SWrapBox> Grid = Wrap(4.f, 12.f);  // beside the scroll bar
	for (int32 I = 0; I < Rack.Num(); ++I)
	{
		Grid->AddSlot()[Focusable(GunCard(Rack[I], Owner->Pane == 0 && F == I), Owner->Pane == 0 && F == I)];
	}
	TSharedRef<SScrollBox> RackScroll = SNew(SScrollBox) + SScrollBox::Slot()[Grid];
	Scroller = RackScroll;  // the rack scrolls; the slots under it always show
	// The four slots, a strip under the rack.
	TSharedRef<SHorizontalBox> Slots = SNew(SHorizontalBox);
	for (int32 I = 0; I < R.GetData().CarryMax; ++I)
	{
		const bool bHave = R.GetSetup().Guns.IsValidIndex(I);
		const FName Gun = bHave ? R.GetSetup().Guns[I] : NAME_None;
		const bool bSel = R.GetSelectedSlot() == I;
		const int32 SlotIndex = I;
		Slots->AddSlot().FillWidth(1.f).Padding(0.f, 0.f, I + 1 < R.GetData().CarryMax ? 4.f : 0.f, 0.f)
		[
			Ring(SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Card, bSel)).ContentPadding(FMargin(10.f, 8.f))
			.OnClicked_Lambda([O, SlotIndex]() { if (O.IsValid()) O->Act(TEXT("selectslot"), FString::FromInt(SlotIndex + 1)); return FReply::Handled(); })
			[
				SNew(SBox).HeightOverride(76.f)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0.f, 0.f, 8.f, 0.f)[Key(FString::FromInt(I + 1), Ink(), WithAlpha(PlateEdge(), 0.9f))]
						+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)[Txt(bHave ? R.GunName(Gun) : R.Text(TEXT("frontend.loadout.empty")).ToUpper(), bHave ? Display(20.f) : Body(MinText, true), bHave ? Ink() : InkFaint())]
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)
					[bHave ? Pips(CountPips(R, Gun)) : StaticCastSharedRef<SWidget>(Txt(R.Text(TEXT("frontend.loadout.emptyHint")), Body(MinText), InkFaint(), true))]
					+ SVerticalBox::Slot().FillHeight(1.f).VAlign(VAlign_Bottom).HAlign(HAlign_Right)
					[
						SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Link)).ContentPadding(FMargin(4.f, 0.f)).Visibility(bHave ? EVisibility::Visible : EVisibility::Collapsed)
						.OnClicked_Lambda([O, SlotIndex]() { if (O.IsValid()) O->Act(TEXT("empty"), FString::FromInt(SlotIndex + 1)); return FReply::Handled(); })
						[Txt(R.Text(TEXT("frontend.loadout.remove")), Body(MinText), InkDim())]
					]
				]
			], Owner->Pane == 1 && F == I, 8.f, 3.f)
		];
	}
	// Melee comes with you: the slot-1 gun's strike.
	FString Melee;
	if (R.GetSetup().Guns.Num() > 0)
	{
		const FMIGunEntry* First = R.GetData().FindGun(R.GetSetup().Guns[0]);
		Melee = First ? R.Text(First->MeleeKey).ToUpper() : FString();
	}
	return Frame(SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Heading(R.Text(TEXT("frontend.loadout.kicker")), R.Text(TEXT("frontend.loadout.title")))]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 8.f, 0.f, 8.f)[Tabs]
		+ SVerticalBox::Slot().FillHeight(1.f)[RackScroll]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 10.f, 0.f, 4.f)
		[Txt(R.Text(TEXT("frontend.loadout.carry")) + TEXT(" ") + R.Text(TEXT("frontend.loadout.bag")), Body(MinText), InkDim(), true)]
		+ SVerticalBox::Slot().AutoHeight()[Slots]
		+ SVerticalBox::Slot().AutoHeight().Padding(4.f, 6.f, 0.f, 0.f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Key(Owner->Glyph(TEXT("melee")), InkDim(), WithAlpha(PlateEdge(), 0.9f))]
			+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center).Padding(8.f, 0.f, 0.f, 0.f)[Txt(Melee, Spaced(Body(MinText, true), 120), InkDim())]
		], false);
}

// ------------------------------------------------------------------------------------------------ Workbench

TSharedRef<SWidget> SMIFrontEnd::Workbench()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	const FName Gun = R.GetBenchGun();
	const int32 F = Owner->FocusShown();
	// The carried guns, to move between them without leaving: arrows are shapes, the keys come from the glyphs.
	TSharedRef<SWrapBox> Strip = Wrap(6.f);
	Strip->AddSlot()
	[
		SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(8.f, 4.f)).OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("benchnext"), TEXT("-1")); return FReply::Handled(); })
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SMIMark).Kind(SMIMark::EKind::Left).Colour(InkDim()).Size(14.f)]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6.f, 0.f, 0.f, 0.f)[Key(Owner->Glyph(TEXT("prevGun")), InkDim(), WithAlpha(PlateEdge(), 0.9f))]
		]
	];
	for (const FName G : R.GetSetup().Guns)
	{
		const bool bOn = G == Gun;
		Strip->AddSlot()
		[
			SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Chip, bOn)).ContentPadding(FMargin(12.f, 4.f))
			.OnClicked_Lambda([O, G]() { if (O.IsValid()) O->Act(TEXT("bench"), G.ToString()); return FReply::Handled(); })
			[Txt(R.GunName(G), Body(MinText, true), bOn ? Bg() : InkDim())]
		];
	}
	Strip->AddSlot()
	[
		SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(8.f, 4.f)).OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("benchnext"), TEXT("1")); return FReply::Handled(); })
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Key(Owner->Glyph(TEXT("nextGun")), InkDim(), WithAlpha(PlateEdge(), 0.9f))]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6.f, 0.f, 0.f, 0.f)[SNew(SMIMark).Kind(SMIMark::EKind::Right).Colour(InkDim()).Size(14.f)]
		]
	];

	TSharedRef<SVerticalBox> Col = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Heading(R.Text(TEXT("frontend.attachments.kicker")), R.GetData().Format(TEXT("frontend.attachments.title"), {{TEXT("gun"), R.GunName(Gun)}}))]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 8.f, 0.f, 10.f)[Strip];
	const TArray<FName> Slots = R.BenchSlots();
	if (Slots.Num() == 0)
	{
		Col->AddSlot().AutoHeight().Padding(0.f, 16.f, 0.f, 6.f)[Txt(R.Text(TEXT("frontend.attachments.noPartsYet")), Display(30.f), Ink(), true)];
		Col->AddSlot().AutoHeight()[Txt(R.Text(TEXT("frontend.attachments.noPartsYetNote")), Body(16.f), InkDim(), true)];
		Col->AddSlot().AutoHeight().Padding(0.f, 18.f, 0.f, 0.f)[Bars(Gun, R.GetSetup().BuildOf(Gun), nullptr)];
		return Frame(Col, true);
	}
	// Slot tabs.
	TSharedRef<SWrapBox> Tabs = Wrap(6.f);
	for (const FName S : Slots)
	{
		const bool bOn = S == R.GetBenchSlot();
		const FMISlotDef* Def = R.GetData().FindSlot(S);
		Tabs->AddSlot()
		[
			SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Chip, bOn)).ContentPadding(FMargin(12.f, 4.f))
			.OnClicked_Lambda([O, S]() { if (O.IsValid()) O->Act(TEXT("benchslot"), S.ToString()); return FReply::Handled(); })
			[Txt((Def ? R.Text(Def->Text) : S.ToString()).ToUpper(), Spaced(Body(MinText, true), 100), bOn ? Bg() : InkDim())]
		];
	}
	Col->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)[Tabs];
	// The options of the slot, with Fitted on the one in use; focus previews, a click fits.
	const TArray<FName> Options = R.BenchOptions(R.GetBenchSlot());
	const FName Fitted = R.FittedIn(R.GetBenchSlot());
	const FName Focused = R.IsPreviewing() ? R.GetPreviewed() : Options.IsValidIndex(Owner->Focus) ? Options[Owner->Focus] : Fitted;
	for (int32 I = 0; I < Options.Num(); ++I)
	{
		const FName P = Options[I];
		const FMIAttachmentDef* Def = R.GetData().FindPart(P);
		const FString Blurb = P.IsNone() ? R.Text(TEXT("frontend.attachments.factoryNote")) : (Def ? R.Text(Def->Text + TEXT(".blurb")) : FString());
		// The pointer over an option previews it (once: a rebuild under a resting pointer changes nothing), a click fits.
		const FString Arg = P.IsNone() ? FString(TEXT("factory")) : P.ToString();
		const int32 Gen = BuildGen;
		const TWeakPtr<SMIFrontEnd> Self = StaticCastSharedRef<SMIFrontEnd>(AsShared());
		TSharedRef<SButton> Option = SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Card, P == Fitted)).ContentPadding(FMargin(12.f, 7.f))
			.Tag(FName(*(TEXT("MIOption.") + Arg)))
			.OnHovered_Lambda([Self, Arg, Gen]() { if (const TSharedPtr<SMIFrontEnd> S = Self.Pin()) S->OptionHovered(Arg, Gen); })
			.OnUnhovered_Lambda([Self, Arg, Gen]() { if (const TSharedPtr<SMIFrontEnd> S = Self.Pin()) S->OptionUnhovered(Arg, Gen); })
			.OnClicked_Lambda([O, Arg]() { if (O.IsValid()) O->Act(TEXT("fit"), Arg); return FReply::Handled(); })
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1.f)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()[Txt(R.PartName(P), Display(22.f), Ink())]
					+ SVerticalBox::Slot().AutoHeight()[Txt(Blurb, Body(MinText), InkDim(), true)]
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8.f, 0.f, 0.f, 0.f)
				[Txt(P == Fitted ? R.Text(TEXT("frontend.attachments.fitted")).ToUpper() : FString(), Spaced(Body(MinText, true), 120), Gold())]
			];
		OptionButtons.Add(Arg, Option);
		Col->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 2.f)[Focusable(Ring(Option, F == I, 8.f, 4.f), F == I)];
	}
	// The focused option's effect lines (a shape for better, worse or neutral, then the words) and the six bars before
	// (ghost) and after (fill).
	TSharedRef<SVerticalBox> Lines = SNew(SVerticalBox);
	if (!Focused.IsNone())
	{
		for (const FMIEffectLine& L : R.EffectLines(Gun, Focused))
		{
			const FLinearColor C = L.Sign > 0 ? FLinearColor(0.4f, 0.9f, 0.5f) : L.Sign < 0 ? FLinearColor(1.f, 0.42f, 0.36f) : InkDim();
			Lines->AddSlot().AutoHeight().Padding(0.f, 1.f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Top).Padding(0.f, 3.f, 8.f, 0.f)[SNew(SMIMark).Kind(SMIMark::ForSign(L.Sign)).Colour(C).Size(14.f)]
				+ SHorizontalBox::Slot().FillWidth(1.f)[Txt(WithoutMark(L.Text), Body(15.f, true), C, true)]
			];
		}
	}
	else
	{
		Lines->AddSlot().AutoHeight()[Txt(R.Text(TEXT("frontend.attachments.noChange")), Body(15.f), InkDim(), true)];
	}
	const FMIGunBuild Shown = R.ShownBuild();
	const FMIGunBuild* Have = R.GetSetup().BuildOf(Gun);
	Col->AddSlot().AutoHeight().Padding(0.f, 10.f, 0.f, 0.f)
	[
		SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().FillWidth(1.f).Padding(0.f, 0.f, 16.f, 0.f)[Lines]
		+ SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(180.f)[Bars(Gun, &Shown, Have)]]
	];
	// Hold to reset build (0.6 s): the fill shows the hold.
	const float Hold = static_cast<float>(FMath::Clamp(Owner->GetHoldReset() / FMath::Max(0.01, R.GetData().ResetHold), 0.0, 1.0));
	Col->AddSlot().AutoHeight().Padding(0.f, 12.f, 0.f, 0.f)
	[
		SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Txt(R.Text(TEXT("frontend.attachments.reset")).ToUpper(), Spaced(Body(MinText, true), 120), InkFaint())]
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8.f, 0.f)[Key(Owner->Glyph(TEXT("reset")), InkDim(), WithAlpha(PlateEdge(), 0.9f))]
		+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)[Bar(Hold, -1.0, 110.f)]
	];
	return Frame(Col, true);
}

// ------------------------------------------------------------------------------------------------ Block & Style

TSharedRef<SWidget> SMIFrontEnd::Where()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	const FMIRunSetup& S = R.GetSetup();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	const int32 F = Owner->FocusShown();
	const auto Row = [&](int32 Index, const FString& Label, TSharedRef<SWidget> Content)
	{
		// The ring pads its row: the label and the cards sit inside it.
		return Focusable(Ring(SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[Txt(Label.ToUpper(), Spaced(Body(MinText, true), 160), InkFaint())]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 0.f)[Content], F == Index, 6.f, 10.f), F == Index);
	};
	const auto Chip = [&](const TCHAR* Act, FName V, const FString& Label, bool bOn)
	{
		const FString A(Act);
		return SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Chip, bOn)).ContentPadding(FMargin(14.f, 5.f))
			.OnClicked_Lambda([O, A, V]() { if (O.IsValid()) O->Act(A, V.ToString()); return FReply::Handled(); })
			[Txt(Label.ToUpper(), Spaced(Body(MinText, true), 100), bOn ? Bg() : InkDim())];
	};
	// 1. Level cards.
	TSharedRef<SVerticalBox> Levels = SNew(SVerticalBox);
	for (const FName L : R.Levels())
	{
		const FMILevelEntry& E = R.GetData().Levels[L];
		TArray<FString> ModeNames;
		for (const FName M : R.GetReadiness().ModesOf(L)) ModeNames.Add(R.Text(TEXT("text.modes.") + M.ToString() + TEXT(".name")));
		const FString Place = E.Place.Contains(S.Time) ? R.Text(E.Place[S.Time]) : FString();
		Levels->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
		[
			SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Card, L == S.Level)).ContentPadding(FMargin(14.f, 10.f))
			.OnClicked_Lambda([O, L]() { if (O.IsValid()) O->Act(TEXT("level"), L.ToString()); return FReply::Handled(); })
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(E.TextKey + TEXT(".name")), Display(30.f), Ink())]
				+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(E.TextKey + TEXT(".blurb")), Body(MinText), InkDim(), true)]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Txt(Place, Body(MinText, true), Gold(), true)]
				+ SVerticalBox::Slot().AutoHeight()[Txt(R.GetData().Format(TEXT("frontend.level.modes"), {{TEXT("modes"), FString::Join(ModeNames, TEXT(" · "))}}), Body(MinText), InkFaint(), true)]
			]
		];
	}
	// 2. Time.
	TSharedRef<SWrapBox> Times = Wrap(6.f, 2.f * 10.f);  // inside the row's ring
	for (const FName T : Owner->GetGame()->GetSettings().Rules.Times)
	{
		Times->AddSlot()[Chip(TEXT("time"), T, R.Text(TEXT("frontend.level.times.") + T.ToString()), T == S.Time)];
	}
	// 3. Mode cards (Hold the Block shows the best), two to a row.
	TSharedRef<SHorizontalBox> Modes = SNew(SHorizontalBox);
	const TArray<FName> ModeIds = R.Modes();
	for (int32 I = 0; I < ModeIds.Num(); ++I)
	{
		const FName M = ModeIds[I];
		const bool bOn = M == S.Mode;
		const FString Best = M == TEXT("holdout") && Owner->GetGame()->GetSettings().GetBest() > 0 ? R.GetData().Format(TEXT("frontend.mode.best"), {{TEXT("score"), FMIText::Grouped(Owner->GetGame()->GetSettings().GetBest())}}) : FString();
		Modes->AddSlot().FillWidth(1.f).Padding(0.f, 0.f, I + 1 < ModeIds.Num() ? 8.f : 0.f, 0.f)
		[
			SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Card, bOn)).ContentPadding(FMargin(12.f, 8.f))
			.OnClicked_Lambda([O, M]() { if (O.IsValid()) O->Act(TEXT("mode"), M.ToString()); return FReply::Handled(); })
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(TEXT("text.modes.") + M.ToString() + TEXT(".name")), Display(22.f), Ink())]
				+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(TEXT("text.modes.") + M.ToString() + TEXT(".note")), Body(MinText), InkDim(), true)]
				+ SVerticalBox::Slot().AutoHeight()[Txt(Best, Body(MinText, true), Gold())]
			]
		];
	}
	// 4. Difficulty.
	TSharedRef<SWrapBox> Diffs = Wrap(6.f, 2.f * 10.f);
	for (const FName D : Owner->GetGame()->GetSettings().Rules.Difficulties)
	{
		Diffs->AddSlot()[Chip(TEXT("difficulty"), D, R.Text(TEXT("text.difficulties.") + D.ToString()), D == S.Difficulty)];
	}
	return Frame(SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Heading(R.Text(TEXT("frontend.where.kicker")), R.Text(TEXT("frontend.where.title")))]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 10.f, 0.f, 0.f)[Row(0, R.Text(TEXT("frontend.level.title")), Levels)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 2.f, 0.f, 0.f)[Row(1, R.Text(TEXT("frontend.level.time")),
			SNew(SVerticalBox) + SVerticalBox::Slot().AutoHeight()[Times]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Txt(R.Text(TEXT("text.interface.title.timeNotes.") + S.Time.ToString()), Body(MinText), InkDim(), true)])]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 2.f, 0.f, 0.f)[Row(2, R.Text(TEXT("frontend.mode.title")), Modes)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 2.f, 0.f, 0.f)[Row(3, R.Text(TEXT("frontend.mode.difficulty")),
			SNew(SVerticalBox) + SVerticalBox::Slot().AutoHeight()[Diffs]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Txt(R.Text(TEXT("frontend.mode.difficultyNotes.") + S.Difficulty.ToString()) + TEXT("  ") + R.Text(TEXT("text.notes.difficulty")), Body(MinText), InkDim(), true)])], true);
}

// ------------------------------------------------------------------------------------------------ Briefing

TSharedRef<SWidget> SMIFrontEnd::Briefing()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	const FMIRunSetup& S = R.GetSetup();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	const FMILevelEntry* L = R.GetData().Levels.Find(S.Level);
	// Carrying: each gun as its slot number, its name and its pips, wrapping to the card's width.
	TSharedRef<SWrapBox> Guns = Wrap(10.f, 2.f * 3.f + 2.f * 14.f + 4.f + 2.f * 12.f + 110.f);  // inside the card, beside CHANGE
	for (int32 I = 0; I < S.Guns.Num(); ++I)
	{
		Guns->AddSlot()
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0.f, 0.f, 6.f, 0.f)[Key(FString::FromInt(I + 1), InkDim(), WithAlpha(PlateEdge(), 0.9f))]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Txt(R.GunName(S.Guns[I]), Display(22.f), Ink())]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6.f, 0.f, 0.f, 0.f)[Pips(CountPips(R, S.Guns[I]), 9.f)]
		];
	}
	const FString Tagline = R.Text(S.Mode == TEXT("holdout") ? TEXT("text.location.taglineHoldout") : TEXT("text.location.tagline"));
	const FString Style = R.Text(TEXT("text.modes.") + S.Mode.ToString() + TEXT(".name")) + TEXT(" · ") + R.Text(TEXT("text.difficulties.") + S.Difficulty.ToString());
	struct FLine { const TCHAR* Label; TSharedRef<SWidget> Value; FString Sub; const TCHAR* Screen; };
	const TArray<FLine> Lines = {
		{TEXT("frontend.briefing.crew"), Txt(R.CrewName(S.Crew), Display(22.f), Ink()), R.CrewTagline(S.Crew), TEXT("crew")},
		{TEXT("frontend.briefing.loadout"), Guns, FString(), TEXT("loadout")},
		{TEXT("frontend.briefing.block"), Txt(L ? R.Text(L->TextKey + TEXT(".name")) : FString(), Display(22.f), Ink()), L && L->Place.Contains(S.Time) ? R.Text(L->Place[S.Time]) : FString(), TEXT("where")},
		{TEXT("frontend.briefing.style"), Txt(Style, Display(22.f), Ink()), Tagline, TEXT("where")},
	};
	TSharedRef<SVerticalBox> Card = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Heading(R.Text(TEXT("frontend.briefing.kicker")), R.Text(TEXT("frontend.briefing.title")))];
	for (int32 I = 0; I < Lines.Num(); ++I)
	{
		const FString Sc(Lines[I].Screen);
		Card->AddSlot().AutoHeight().Padding(0.f, 6.f, 0.f, 0.f)
		[
			Focusable(Ring(SNew(SBorder).BorderImage(Box(WithAlpha(Plate(), 0.9f), 8.f, PlateEdge(), 1.f)).Padding(FMargin(14.f, 8.f))
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Fill)[SNew(SBox).WidthOverride(4.f)[SNew(SImage).Image(Box(Line(FMath::Min(I, 3)), 2.f))]]
				+ SHorizontalBox::Slot().FillWidth(1.f).Padding(12.f, 0.f)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(Lines[I].Label).ToUpper(), Spaced(Body(MinText, true), 160), InkFaint())]
					+ SVerticalBox::Slot().AutoHeight()[Lines[I].Value]
					+ SVerticalBox::Slot().AutoHeight()[Txt(Lines[I].Sub, Body(MinText), InkDim(), true)]
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					SNew(SButton).ClickMethod(EButtonClickMethod::MouseDown).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(12.f, 5.f))
					.OnClicked_Lambda([O, Sc]() { if (O.IsValid()) O->Act(TEXT("edit"), Sc); return FReply::Handled(); })
					[Txt(R.Text(TEXT("frontend.briefing.change")).ToUpper(), Spaced(Body(MinText, true), 120), Ink())]
				]
			], Owner->FocusShown() == I, 8.f, 3.f), Owner->FocusShown() == I)
		];
	}
	Card->AddSlot().AutoHeight().Padding(0.f, 12.f, 0.f, 0.f)[ControlsGlance()];
	return Frame(Card, true);
}

// ------------------------------------------------------------------------------------------------ input

FReply SMIFrontEnd::OnKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent)
{
	if (Owner.IsValid() && Owner->Key(InKeyEvent.GetKey(), true, InKeyEvent.IsRepeat(), InKeyEvent.IsControlDown(), InKeyEvent.IsShiftDown()))
	{
		return FReply::Handled();
	}
	return FReply::Unhandled();
}

FReply SMIFrontEnd::OnKeyUp(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent)
{
	if (Owner.IsValid() && Owner->Key(InKeyEvent.GetKey(), false, false, InKeyEvent.IsControlDown(), InKeyEvent.IsShiftDown()))
	{
		return FReply::Handled();
	}
	return FReply::Unhandled();
}

FReply SMIFrontEnd::OnMouseButtonDown(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent)
{
	// A drag on the stage turns the gun (the buttons take their own clicks first).
	if (Owner.IsValid())
	{
		Owner->UsePad(false);  // the glyphs follow the device in use
	}
	bDragging = true;
	LastMouse = MouseEvent.GetScreenSpacePosition();
	return FReply::Handled().CaptureMouse(SharedThis(this)).SetUserFocus(SharedThis(this));
}

FReply SMIFrontEnd::OnMouseButtonUp(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent)
{
	bDragging = false;
	return FReply::Handled().ReleaseMouseCapture();
}

FReply SMIFrontEnd::OnMouseMove(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent)
{
	if (bDragging && Owner.IsValid() && Owner->GetShowroom())
	{
		const FVector2D P = MouseEvent.GetScreenSpacePosition();
		Owner->GetShowroom()->Drag((P - LastMouse) / MyGeometry.Scale);
		LastMouse = P;
		return FReply::Handled();
	}
	return FReply::Unhandled();
}

FReply SMIFrontEnd::OnMouseWheel(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent)
{
	if (Owner.IsValid() && Owner->GetShowroom())
	{
		Owner->GetShowroom()->Zoom(MouseEvent.GetWheelDelta());
		return FReply::Handled();
	}
	return FReply::Unhandled();
}

FReply SMIFrontEnd::OnAnalogValueChanged(const FGeometry& MyGeometry, const FAnalogInputEvent& InAnalogInputEvent)
{
	const FKey K = InAnalogInputEvent.GetKey();
	const float V = InAnalogInputEvent.GetAnalogValue();
	if (K == EKeys::Gamepad_RightX) Stick.X = FMath::Abs(V) > 0.15f ? V : 0.f;
	else if (K == EKeys::Gamepad_RightY) Stick.Y = FMath::Abs(V) > 0.15f ? V : 0.f;
	else if (K == EKeys::Gamepad_RightTriggerAxis) Triggers = V;
	else if (K == EKeys::Gamepad_LeftTriggerAxis) Triggers = -V;
	else return FReply::Unhandled();
	return FReply::Handled();
}
