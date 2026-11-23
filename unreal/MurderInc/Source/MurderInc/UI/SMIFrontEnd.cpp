#include "UI/SMIFrontEnd.h"

#include "Brushes/SlateColorBrush.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "Flow/MIGameSubsystem.h"
#include "Styling/SlateTypes.h"
#include "UI/MIFrontEnd.h"
#include "UI/MIShowroom.h"
#include "UI/MIStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace MIFrontEndUI
{
	using namespace MIStyle;

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

	enum class EBtn : uint8 { Primary, Quiet, Card, Link, Chip };

	const FButtonStyle* ButtonStyle(EBtn Kind, bool bSelected = false)
	{
		static TMap<int32, FButtonStyle> Cache;
		const int32 Key = static_cast<int32>(Kind) * 2 + (bSelected ? 1 : 0);
		if (const FButtonStyle* Have = Cache.Find(Key))
		{
			return Have;
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
		S.SetDisabled(*Box(WithAlpha(Plate(), 0.4f), Radius, WithAlpha(PlateEdge(), 0.4f), EdgeW));
		S.SetNormalPadding(FMargin(0));
		S.SetPressedPadding(FMargin(0));
		return &Cache.Add(Key, S);
	}

	TSharedRef<STextBlock> Txt(const FString& T, const FSlateFontInfo& Font, const FLinearColor& Colour, bool bWrap = false, float WrapAt = 0.f)
	{
		return SNew(STextBlock).Text(FText::FromString(T)).Font(Font).ColorAndOpacity(FSlateColor(Colour)).AutoWrapText(bWrap).WrapTextAt(WrapAt);
	}

	FSlateFontInfo Spaced(FSlateFontInfo F, int32 Spacing)
	{
		F.LetterSpacing = Spacing;
		return F;
	}

	/** A focus ring around a control (keyboard and pad focus), gold. */
	TSharedRef<SWidget> Ring(TSharedRef<SWidget> Inner, bool bFocused, float Radius = 8.f)
	{
		return SNew(SBorder)
			.BorderImage(bFocused ? Box(FLinearColor::Transparent, Radius + 3.f, Gold(), 2.f) : Box(FLinearColor::Transparent, 0.f))
			.Padding(3.f)
			[Inner];
	}

	/** A 0..1 bar with an optional ghost (the value before a change on the Workbench). */
	TSharedRef<SWidget> Bar(double Value, double Ghost, float Width)
	{
		const double V = FMath::Clamp(Value, 0.0, 1.0);
		const double G = Ghost < 0.0 ? V : FMath::Clamp(Ghost, 0.0, 1.0);
		const FLinearColor Fill = Ghost < 0.0 || FMath::IsNearlyEqual(V, G) ? Ink() : (V > G ? FLinearColor(0.35f, 0.85f, 0.45f) : FLinearColor(0.95f, 0.35f, 0.3f));
		return SNew(SBox).WidthOverride(Width).HeightOverride(6.f)
			[
				SNew(SOverlay)
				+ SOverlay::Slot()[SNew(SImage).Image(Box(WithAlpha(PlateEdge(), 0.9f), 3.f))]
				+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).WidthOverride(Width * static_cast<float>(FMath::Max(V, G)))[SNew(SImage).Image(Box(WithAlpha(Ink(), 0.28f), 3.f))]]
				+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).WidthOverride(Width * static_cast<float>(V))[SNew(SImage).Image(Box(Fill, 3.f))]]
			];
	}
}

using namespace MIFrontEndUI;

void SMIFrontEnd::Construct(const FArguments& InArgs)
{
	Owner = InArgs._Owner;
	SetCanTick(true);
	Rebuild();
}

void SMIFrontEnd::Tick(const FAllottedGeometry& AllottedGeometry, const double InCurrentTime, const float InDeltaTime)
{
	SCompoundWidget::Tick(AllottedGeometry, InCurrentTime, InDeltaTime);
	if (Owner.IsValid() && Owner->GetVersion() != Built)
	{
		Rebuild();
	}
	if (Owner.IsValid() && Owner->GetShowroom() && (Stick.SizeSquared() > 0.0 || Triggers != 0.f))
	{
		Owner->GetShowroom()->Stick(Stick, Triggers);
	}
}

void SMIFrontEnd::Rebuild()
{
	if (!Owner.IsValid())
	{
		return;
	}
	Built = Owner->GetVersion();
	TSharedRef<SWidget> Body = SNullWidget::NullWidget;
	switch (Owner->GetRules().GetScreen())
	{
	case EMIFrontScreen::Home: Body = Home(); break;
	case EMIFrontScreen::Crew: Body = Crew(); break;
	case EMIFrontScreen::Loadout: Body = Loadout(); break;
	case EMIFrontScreen::Workbench: Body = Workbench(); break;
	case EMIFrontScreen::Where: Body = Where(); break;
	case EMIFrontScreen::Briefing: Body = Briefing(); break;
	}
	ChildSlot[Body];
}

// ------------------------------------------------------------------------------------------------ the frame

TSharedRef<SWidget> SMIFrontEnd::Frame(TSharedRef<SWidget> Body, bool bWideRight)
{
	// The veil: the left 40 % holds the controls, the rest shows the stage; a soft edge in eight strips.
	TSharedRef<SHorizontalBox> Veil = SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().FillWidth(0.40f)[SNew(SImage).Image(Box(WithAlpha(Bg(), 0.86f), 0.f))];
	for (int32 I = 0; I < 8; ++I)
	{
		Veil->AddSlot().FillWidth(0.02f)[SNew(SImage).Image(Box(WithAlpha(Bg(), 0.86f * (1.f - (I + 1) / 9.f)), 0.f))];
	}
	Veil->AddSlot().FillWidth(0.44f)[SNullWidget::NullWidget];
	return SNew(SOverlay)
		+ SOverlay::Slot()[Veil]
		// Letterbox bars.
		+ SOverlay::Slot().VAlign(VAlign_Top)[SNew(SBox).HeightOverride(46.f)[SNew(SImage).Image(Box(FLinearColor::Black, 0.f))]]
		+ SOverlay::Slot().VAlign(VAlign_Bottom)[SNew(SBox).HeightOverride(46.f)[SNew(SImage).Image(Box(FLinearColor::Black, 0.f))]]
		+ SOverlay::Slot().Padding(FMargin(72.f, 70.f, 72.f, 64.f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[StepStrip()]
			+ SVerticalBox::Slot().FillHeight(1.f).Padding(0.f, 22.f, 0.f, 14.f)[Body]
			+ SVerticalBox::Slot().AutoHeight()[BottomBar()]
		];
}

TSharedRef<SWidget> SMIFrontEnd::StepStrip()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	const TArray<FString> Labels = R.GetData().TextList(TEXT("frontend.steps.labels"));
	const int32 Current = FMIFrontEndRules::StepOf(R.GetScreen());
	TSharedRef<SHorizontalBox> Row = SNew(SHorizontalBox);
	for (int32 I = 0; I < Labels.Num(); ++I)
	{
		const int32 Step = I + 1;
		const bool bDone = Step < Current;
		const bool bNow = Step == Current;
		const FLinearColor C = Line(FMath::Min(I, 3));
		TWeakObjectPtr<UMIFrontEnd> O = Owner;
		Row->AddSlot().AutoWidth().Padding(0.f, 0.f, 26.f, 0.f)
		[
			SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Link)).IsEnabled(R.IsStepReachable(Step))
			.OnClicked_Lambda([O, Step]() { if (O.IsValid()) O->Act(TEXT("step"), FString::FromInt(Step)); return FReply::Handled(); })
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(4.f)
				[
					SNew(SBox).WidthOverride(16.f).HeightOverride(16.f)
					[SNew(SImage).Image(Box(bDone || bNow ? C : FLinearColor::Transparent, 8.f, bNow ? Ink() : C, bNow ? 2.f : 2.f))]
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6.f, 0.f, 4.f, 0.f)
				[Txt(Labels[I].ToUpper(), Spaced(Body(13.f, true), 180), bNow ? Ink() : InkDim())]
			]
		];
	}
	if (Current == 0)
	{
		return SNew(SBox).HeightOverride(30.f);
	}
	return Row;
}

TSharedRef<SWidget> SMIFrontEnd::Heading(const FString& Kicker, const FString& Title)
{
	return SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Txt(Kicker.ToUpper(), Spaced(Body(14.f, true), 240), InkDim())]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Txt(Title.ToUpper(), Display(58.f), Ink())];
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
	return SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth()
		[
			SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(22.f, 12.f))
			.OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("back")); return FReply::Handled(); })
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Txt(R.Text(TEXT("frontend.steps.back")).ToUpper(), Spaced(Body(15.f, true), 160), Ink())]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(12.f, 0.f, 0.f, 0.f)[Txt(TEXT("ESC / B"), Body(11.f), InkFaint())]
			]
		]
		+ SHorizontalBox::Slot().FillWidth(0.4f).VAlign(VAlign_Center).Padding(24.f, 0.f)
		[Txt(Blocked.IsEmpty() ? R.LastMessage : Blocked, Body(14.f), Blocked.IsEmpty() ? InkDim() : Red(), true, 420.f)]
		+ SHorizontalBox::Slot().FillWidth(0.6f)[SNullWidget::NullWidget]
		+ SHorizontalBox::Slot().AutoWidth()
		[
			SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Primary)).ContentPadding(FMargin(30.f, 12.f)).IsEnabled(Blocked.IsEmpty())
			.OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("next")); return FReply::Handled(); })
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Txt(NextLabel.ToUpper(), Display(24.f), Bg())]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(14.f, 0.f, 0.f, 0.f)[Txt(TEXT("ENTER / START"), Body(11.f, true), WithAlpha(Bg(), 0.7f))]
			]
		];
}

// ------------------------------------------------------------------------------------------------ Home

TSharedRef<SWidget> SMIFrontEnd::Home()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	const FMIRunSetup& S = R.GetSetup();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	const int32 F = Owner->Focus;
	const auto Picker = [&](int32 Index, const FString& Label, const FString& Value, const TCHAR* Which, const TArray<FName>& Values, FName Now)
	{
		TSharedRef<SHorizontalBox> Chips = SNew(SHorizontalBox);
		for (const FName V : Values)
		{
			const FString Name = Which == FString(TEXT("mode")) ? R.Text(TEXT("text.modes.") + V.ToString() + TEXT(".name"))
				: Which == FString(TEXT("difficulty")) ? R.Text(TEXT("text.difficulties.") + V.ToString()) : R.Text(TEXT("frontend.level.times.") + V.ToString());
			const FString W(Which);
			Chips->AddSlot().AutoWidth().Padding(0.f, 0.f, 8.f, 0.f)
			[
				SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Chip, V == Now)).ContentPadding(FMargin(16.f, 7.f))
				.OnClicked_Lambda([O, W, V]() { if (O.IsValid()) O->Act(W, V.ToString()); return FReply::Handled(); })
				[Txt(Name.ToUpper(), Spaced(Body(13.f, true), 120), V == Now ? Bg() : InkDim())]
			];
		}
		return Ring(SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).WidthOverride(130.f)[Txt(Label.ToUpper(), Spaced(Body(13.f, true), 200), InkFaint())]]
			+ SHorizontalBox::Slot().AutoWidth()[Chips], F == Index, 18.f);
	};
	const FMISettings::FRules& SR = Owner->GetGame()->GetSettings().Rules;
	// The summary line: each part is a link that opens its screen in edit mode.
	TArray<FString> Guns;
	for (const FName G : S.Guns) Guns.Add(R.GunName(G));
	const auto Link = [&](int32 Index, const FString& Label, const TCHAR* Screen)
	{
		const FString Sc(Screen);
		return Ring(SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Link)).ContentPadding(FMargin(6.f, 3.f))
			.OnClicked_Lambda([O, Sc]() { if (O.IsValid()) O->Act(TEXT("edit"), Sc); return FReply::Handled(); })
			[Txt(Label, Body(16.f, true), Ink())], F == Index, 4.f);
	};
	const FMILevelEntry* Level = R.GetData().Levels.Find(S.Level);
	const FString Dot = TEXT("  ·  ");
	TSharedRef<SWidget> Summary = SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth()[Link(5, R.CrewName(S.Crew), TEXT("crew"))]
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Txt(Dot, Body(16.f), InkFaint())]
		+ SHorizontalBox::Slot().AutoWidth()[Link(6, FString::Join(Guns, TEXT(" / ")), TEXT("loadout"))]
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Txt(Dot, Body(16.f), InkFaint())]
		+ SHorizontalBox::Slot().AutoWidth()[Link(7, (Level ? R.Text(Level->TextKey + TEXT(".name")) : FString()) + Dot + R.Text(TEXT("frontend.level.times.") + S.Time.ToString()), TEXT("where"))];

	TSharedRef<SVerticalBox> Col = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(TEXT("text.title.eyebrow")), Spaced(Body(15.f, true), 260), Gold())]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 0.f)[Txt(R.Text(TEXT("text.title.wordmark")), Display(150.f), Ink())]
		+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(TEXT("text.title.star")), Spaced(Body(16.f, true), 320), InkDim())]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 18.f, 0.f, 26.f)[Txt(R.Text(TEXT("text.title.premise")), Body(19.f), Ink(), true, 620.f)]
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				Ring(SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Primary)).ContentPadding(FMargin(36.f, 14.f))
				.OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("hit")); return FReply::Handled(); })
				[Txt(R.Text(TEXT("frontend.home.start")).ToUpper(), Display(34.f), Bg())], F == 0, 8.f)
			]
			+ SHorizontalBox::Slot().AutoWidth().Padding(16.f, 0.f, 0.f, 0.f).VAlign(VAlign_Center)
			[
				Ring(SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(24.f, 14.f))
				.OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("gearup")); return FReply::Handled(); })
				[Txt(R.Text(TEXT("frontend.home.setup")).ToUpper(), Spaced(Body(16.f, true), 160), Ink())], F == 1, 8.f)
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 12.f, 0.f, 0.f)[Summary]
		+ SVerticalBox::Slot().AutoHeight().Padding(6.f, 2.f, 0.f, 0.f)
		[Txt(S.bPlayed ? FString() : R.Text(TEXT("frontend.home.firstTime")), Body(14.f), Gold())]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 26.f, 0.f, 0.f)[Picker(2, R.Text(TEXT("text.interface.title.modeLabel")), FString(), TEXT("mode"), SR.Modes, S.Mode)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 8.f, 0.f, 0.f)[Picker(3, R.Text(TEXT("text.interface.title.difficultyLabel")), FString(), TEXT("difficulty"), SR.Difficulties, S.Difficulty)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 8.f, 0.f, 0.f)[Picker(4, R.Text(TEXT("text.interface.title.timeLabel")), FString(), TEXT("time"), SR.Times, S.Time)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 26.f, 0.f, 0.f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()
			[
				SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(18.f, 9.f))
				.OnClicked_Lambda([O]() { if (O.IsValid() && O->GetGame()) O->GetGame()->OpenSettingsFromFrontEnd(); return FReply::Handled(); })
				[Txt(R.Text(TEXT("text.title.settings")).ToUpper(), Spaced(Body(13.f, true), 160), InkDim())]
			]
			+ SHorizontalBox::Slot().AutoWidth().Padding(10.f, 0.f, 0.f, 0.f)
			[
				SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(18.f, 9.f))
				.OnClicked_Lambda([this]() { bShowControls = !bShowControls; Rebuild(); return FReply::Handled(); })
				[Txt(R.Text(TEXT("text.title.controls")).ToUpper(), Spaced(Body(13.f, true), 160), InkDim())]
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 18.f, 0.f, 0.f)[ControlsGlance()];
	return Frame(SNew(SScrollBox) + SScrollBox::Slot()[Col], false);
}

TSharedRef<SWidget> SMIFrontEnd::ControlsGlance()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	TSharedRef<SVerticalBox> Box1 = SNew(SVerticalBox);
	// interface.glance (the web title's strip), then frontend.controls.kbm (the new rows) when expanded.
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
	Read(MIJson::Get(R.TextJson, TEXT("interface.glance")));
	if (bShowControls || R.GetSetup().Guns.Num() >= R.GetData().WheelMinGuns)
	{
		Read(MIJson::Get(R.GetData().TextJson, TEXT("frontend.controls.kbm")));
	}
	TSharedRef<SHorizontalBox> Line1 = SNew(SHorizontalBox);
	int32 N = 0;
	for (const TPair<FString, FString>& Row : Rows)
	{
		if (!bShowControls && N++ >= 10) break;
		Line1->AddSlot().AutoWidth().Padding(0.f, 0.f, 18.f, 6.f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth()[SNew(SBorder).BorderImage(Box(WithAlpha(PlateEdge(), 0.9f), 4.f)).Padding(FMargin(6.f, 2.f))[Txt(Row.Value, Body(12.f, true), Ink())]]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6.f, 0.f, 0.f, 0.f)[Txt(Row.Key, Body(12.f), InkDim())]
		];
		if (bShowControls && (N % 5) == 0)
		{
			Box1->AddSlot().AutoHeight()[Line1];
			Line1 = SNew(SHorizontalBox);
		}
	}
	Box1->AddSlot().AutoHeight()[Line1];
	return SNew(SBox).MaxDesiredWidth(1300.f)[Box1];
}

// ------------------------------------------------------------------------------------------------ Crew

TSharedRef<SWidget> SMIFrontEnd::Crew()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	TSharedRef<SHorizontalBox> Cards = SNew(SHorizontalBox);
	const TArray<FName> Offered = R.OfferedCrew();
	for (int32 I = 0; I < Offered.Num(); ++I)
	{
		const FName Id = Offered[I];
		const bool bSel = R.GetSetup().Crew == Id;
		Cards->AddSlot().AutoWidth().Padding(0.f, 0.f, 14.f, 0.f)
		[
			Ring(SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Card, bSel)).ContentPadding(FMargin(18.f))
			.OnClicked_Lambda([O, Id]() { if (O.IsValid()) O->Act(TEXT("crew"), Id.ToString()); return FReply::Handled(); })
			[
				SNew(SBox).WidthOverride(230.f)
				[
					SNew(SVerticalBox)
					// The portrait: a card of the arms on the bench, never a face (T_UI_Crew_* missing: the name stands in).
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(SBox).HeightOverride(170.f)
						[
							SNew(SBorder).BorderImage(Box(FLinearColor(0.025f, 0.026f, 0.03f), 6.f, WithAlpha(PlateEdge(), 0.8f), 1.f)).HAlign(HAlign_Center).VAlign(VAlign_Center)
							[Txt(R.CrewName(Id), Display(64.f), bSel ? Gold() : WithAlpha(Ink(), 0.85f))]
						]
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 12.f, 0.f, 0.f)[Txt(R.CrewName(Id), Display(30.f), Ink())]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Txt(R.CrewTagline(Id), Body(14.f), InkDim(), true, 220.f)]
				]
			], Owner->Focus == I)
		];
	}
	return Frame(SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Heading(R.Text(TEXT("frontend.crew.kicker")), R.Text(TEXT("frontend.crew.title")))]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 8.f, 0.f, 28.f)[Txt(R.Text(TEXT("frontend.crew.note")), Body(16.f), InkDim())]
		+ SVerticalBox::Slot().AutoHeight()[Cards]
		+ SVerticalBox::Slot().FillHeight(1.f)[SNullWidget::NullWidget], false);
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
		Col->AddSlot().AutoHeight().Padding(0.f, 2.f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).WidthOverride(84.f)[Txt(R.Text(FString(TEXT("frontend.loadout.stats.")) + Keys[I]).ToUpper(), Spaced(Body(10.f, true), 100), InkFaint())]]
			+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Bar(Values[I], Ghost ? Ghosts[I] : -1.0, 118.f)]
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
	FString Tags = Slot != INDEX_NONE ? R.GetData().Format(TEXT("frontend.loadout.carried"), {{TEXT("n"), FString::FromInt(Slot + 1)}}) : FString();
	const FString Info = FString::Printf(TEXT("%s %s%s   %s"), *R.Text(TEXT("frontend.loadout.stats.mag")).ToUpper(), bInfinite ? TEXT("") : *FString::FromInt(Mag),
		bInfinite ? *(FString::FromInt(Mag) + TEXT(" / ") + R.Text(TEXT("frontend.loadout.stats.infinite"))) : (bSemiOnly ? *(TEXT("  ") + R.Text(TEXT("frontend.loadout.stats.semi"))) : TEXT("")),
		Slots.Num() > 0 ? *R.GetData().Format(TEXT("frontend.loadout.slots"), {{TEXT("n"), FString::FromInt(Slots.Num())}}) : *R.Text(TEXT("frontend.loadout.noSlots")));
	const bool bDev = !R.GetReadiness().IsGunReady(Gun);
	return Ring(SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Card, Slot != INDEX_NONE)).ContentPadding(FMargin(14.f, 12.f))
		.OnClicked_Lambda([O, Gun]() { if (O.IsValid()) O->Act(TEXT("carry"), Gun.ToString()); return FReply::Handled(); })
		[
			SNew(SBox).WidthOverride(222.f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().FillWidth(1.f)[Txt(R.GunName(Gun), Display(30.f), Ink())]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Top)
					[Txt(bDev ? R.Text(TEXT("frontend.loadout.devTag")) : R.IsNew(Gun) ? R.Text(TEXT("frontend.loadout.new")) : FString(), Body(11.f, true), bDev ? Red() : Gold())]
				]
				+ SVerticalBox::Slot().AutoHeight()[Txt(G ? R.Text(TEXT("frontend.loadout.classes.") + G->Class.ToString()).ToUpper() : FString(), Spaced(Body(11.f, true), 160), InkFaint())]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 8.f)[Bars(Gun, Build, nullptr)]
				+ SVerticalBox::Slot().AutoHeight()[Txt(Info, Body(11.f), InkDim())]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 0.f)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)[Txt(Tags, Body(11.f, true), Gold())]
					+ SHorizontalBox::Slot().AutoWidth()
					[
						SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(10.f, 4.f))
						.OnClicked_Lambda([O, Gun]() { if (O.IsValid()) O->Act(TEXT("bench"), Gun.ToString()); return FReply::Handled(); })
						[Txt(TEXT("⚒ ") + R.Text(TEXT("frontend.loadout.attachments")), Body(11.f, true), Ink())]
					]
				]
			]
		], bFocused);
}

TSharedRef<SWidget> SMIFrontEnd::Loadout()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	// Class tabs.
	TSharedRef<SHorizontalBox> Tabs = SNew(SHorizontalBox);
	for (const TCHAR* F : {TEXT("all"), TEXT("rifle"), TEXT("smg"), TEXT("pistol"), TEXT("new")})
	{
		const FName Filter(F);
		const bool bOn = Owner->RackFilter == Filter;
		Tabs->AddSlot().AutoWidth().Padding(0.f, 0.f, 8.f, 0.f)
		[
			SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Chip, bOn)).ContentPadding(FMargin(14.f, 5.f))
			.OnClicked_Lambda([O, Filter]() { if (O.IsValid()) O->Act(TEXT("filter"), Filter.ToString()); return FReply::Handled(); })
			[Txt(R.Text(FString(TEXT("frontend.loadout.filters.")) + F).ToUpper(), Spaced(Body(12.f, true), 120), bOn ? Bg() : InkDim())]
		];
	}
	// The rack, three wide.
	const TArray<FName> Rack = R.Rack(Owner->RackFilter);
	TSharedRef<SVerticalBox> Grid = SNew(SVerticalBox);
	TSharedPtr<SHorizontalBox> Row;
	for (int32 I = 0; I < Rack.Num(); ++I)
	{
		if (I % 3 == 0)
		{
			Row = SNew(SHorizontalBox);
			Grid->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)[Row.ToSharedRef()];
		}
		Row->AddSlot().AutoWidth().Padding(0.f, 0.f, 10.f, 0.f)[GunCard(Rack[I], Owner->Pane == 0 && Owner->Focus == I)];
	}
	// The four slots, on the right.
	TSharedRef<SVerticalBox> Slots = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(TEXT("frontend.loadout.carry")), Body(14.f, true), Ink(), true, 320.f)]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 2.f, 0.f, 12.f)[Txt(R.Text(TEXT("frontend.loadout.bag")), Body(13.f), InkDim(), true, 320.f)];
	for (int32 I = 0; I < R.GetData().CarryMax; ++I)
	{
		const bool bHave = R.GetSetup().Guns.IsValidIndex(I);
		const FName Gun = bHave ? R.GetSetup().Guns[I] : NAME_None;
		int32 Pips = 0;
		if (const FMIGunBuild* B = bHave ? R.GetSetup().BuildOf(Gun) : nullptr)
		{
			for (const TPair<FName, FName>& P : B->Parts)
			{
				const FMIAttachmentDef* Part = R.GetData().FindPart(P.Value);
				Pips += Part && !Part->bBaseline ? 1 : 0;
			}
		}
		TSharedRef<SHorizontalBox> PipRow = SNew(SHorizontalBox);
		for (int32 P = 0; P < Pips; ++P) PipRow->AddSlot().AutoWidth().Padding(0.f, 0.f, 4.f, 0.f)[SNew(SBox).WidthOverride(8.f).HeightOverride(8.f)[SNew(SImage).Image(Box(Gold(), 2.f))]];
		const bool bSel = R.GetSelectedSlot() == I;
		const int32 SlotIndex = I;
		Slots->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
		[
			Ring(SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Card, bSel)).ContentPadding(FMargin(14.f, 10.f))
			.OnClicked_Lambda([O, SlotIndex]() { if (O.IsValid()) O->Act(TEXT("selectslot"), FString::FromInt(SlotIndex + 1)); return FReply::Handled(); })
			[
				SNew(SBox).WidthOverride(300.f)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0.f, 0.f, 12.f, 0.f)
					[SNew(SBorder).BorderImage(Box(WithAlpha(PlateEdge(), 0.9f), 4.f)).Padding(FMargin(8.f, 2.f))[Txt(FString::FromInt(I + 1), Body(13.f, true), Ink())]]
					+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
					[
						SNew(SVerticalBox)
						+ SVerticalBox::Slot().AutoHeight()[Txt(bHave ? R.GunName(Gun) : R.Text(TEXT("frontend.loadout.empty")).ToUpper(), bHave ? Display(26.f) : Body(15.f, true), bHave ? Ink() : InkFaint())]
						+ SVerticalBox::Slot().AutoHeight()[bHave ? StaticCastSharedRef<SWidget>(PipRow) : StaticCastSharedRef<SWidget>(Txt(R.Text(TEXT("frontend.loadout.emptyHint")), Body(12.f), InkFaint()))]
					]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
					[
						SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Link)).ContentPadding(FMargin(8.f, 4.f)).Visibility(bHave ? EVisibility::Visible : EVisibility::Collapsed)
						.OnClicked_Lambda([O, SlotIndex]() { if (O.IsValid()) O->Act(TEXT("empty"), FString::FromInt(SlotIndex + 1)); return FReply::Handled(); })
						[Txt(R.Text(TEXT("frontend.loadout.remove")), Body(11.f, true), InkDim())]
					]
				]
			], Owner->Pane == 1 && Owner->Focus == I)
		];
	}
	// Melee comes with you: the slot-1 gun's strike.
	if (R.GetSetup().Guns.Num() > 0)
	{
		const FMIGunEntry* First = R.GetData().FindGun(R.GetSetup().Guns[0]);
		Slots->AddSlot().AutoHeight().Padding(4.f, 6.f, 0.f, 0.f)
		[Txt(TEXT("F   ") + (First ? R.Text(First->MeleeKey) : FString()).ToUpper(), Spaced(Body(12.f, true), 140), InkDim())];
	}
	return Frame(SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth()
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[Heading(R.Text(TEXT("frontend.loadout.kicker")), R.Text(TEXT("frontend.loadout.title")))]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 12.f, 0.f, 14.f)[Tabs]
			+ SVerticalBox::Slot().FillHeight(1.f)[SNew(SScrollBox) + SScrollBox::Slot()[Grid]]
		]
		+ SHorizontalBox::Slot().FillWidth(1.f)[SNullWidget::NullWidget]
		+ SHorizontalBox::Slot().AutoWidth().Padding(0.f, 70.f, 0.f, 0.f)
		[SNew(SBorder).BorderImage(Box(WithAlpha(Bg(), 0.72f), 10.f)).Padding(16.f)[Slots]], true);
}

// ------------------------------------------------------------------------------------------------ Workbench

TSharedRef<SWidget> SMIFrontEnd::Workbench()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	const FName Gun = R.GetBenchGun();
	// The carried guns, to move between them without leaving.
	TSharedRef<SHorizontalBox> Strip = SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth().Padding(0.f, 0.f, 8.f, 0.f)
		[SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(10.f, 5.f)).OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("benchnext"), TEXT("-1")); return FReply::Handled(); })[Txt(TEXT("◀  ["), Body(12.f, true), InkDim())]];
	for (const FName G : R.GetSetup().Guns)
	{
		const bool bOn = G == Gun;
		Strip->AddSlot().AutoWidth().Padding(0.f, 0.f, 8.f, 0.f)
		[
			SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Chip, bOn)).ContentPadding(FMargin(14.f, 5.f))
			.OnClicked_Lambda([O, G]() { if (O.IsValid()) O->Act(TEXT("bench"), G.ToString()); return FReply::Handled(); })
			[Txt(R.GunName(G), Body(12.f, true), bOn ? Bg() : InkDim())]
		];
	}
	Strip->AddSlot().AutoWidth()[SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(10.f, 5.f)).OnClicked_Lambda([O]() { if (O.IsValid()) O->Act(TEXT("benchnext"), TEXT("1")); return FReply::Handled(); })[Txt(TEXT("]  ▶"), Body(12.f, true), InkDim())]];

	TSharedRef<SVerticalBox> Col = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Heading(R.Text(TEXT("frontend.attachments.kicker")), R.GetData().Format(TEXT("frontend.attachments.title"), {{TEXT("gun"), R.GunName(Gun)}}))]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 10.f, 0.f, 16.f)[Strip];
	const TArray<FName> Slots = R.BenchSlots();
	if (Slots.Num() == 0)
	{
		Col->AddSlot().AutoHeight().Padding(0.f, 20.f, 0.f, 6.f)[Txt(R.Text(TEXT("frontend.attachments.noPartsYet")), Display(32.f), Ink())];
		Col->AddSlot().AutoHeight()[Txt(R.Text(TEXT("frontend.attachments.noPartsYetNote")), Body(16.f), InkDim(), true, 600.f)];
		Col->AddSlot().AutoHeight().Padding(0.f, 22.f, 0.f, 0.f)[Bars(Gun, R.GetSetup().BuildOf(Gun), nullptr)];
		return Frame(Col, false);
	}
	// Slot tabs.
	TSharedRef<SHorizontalBox> Tabs = SNew(SHorizontalBox);
	for (const FName S : Slots)
	{
		const bool bOn = S == R.GetBenchSlot();
		const FMISlotDef* Def = R.GetData().FindSlot(S);
		Tabs->AddSlot().AutoWidth().Padding(0.f, 0.f, 6.f, 0.f)
		[
			SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Chip, bOn)).ContentPadding(FMargin(12.f, 5.f))
			.OnClicked_Lambda([O, S]() { if (O.IsValid()) O->Act(TEXT("benchslot"), S.ToString()); return FReply::Handled(); })
			[Txt((Def ? R.Text(Def->Text) : S.ToString()).ToUpper(), Spaced(Body(12.f, true), 120), bOn ? Bg() : InkDim())]
		];
	}
	Col->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)[Tabs];
	// The options of the slot, with Fitted on the one in use; focus previews, a click fits.
	const TArray<FName> Options = R.BenchOptions(R.GetBenchSlot());
	const FName Fitted = R.FittedIn(R.GetBenchSlot());
	FName Focused = Options.IsValidIndex(Owner->Focus) ? Options[Owner->Focus] : Fitted;
	TSharedRef<SVerticalBox> List = SNew(SVerticalBox);
	for (int32 I = 0; I < Options.Num(); ++I)
	{
		const FName P = Options[I];
		const FMIAttachmentDef* Def = R.GetData().FindPart(P);
		const FString Blurb = P.IsNone() ? R.Text(TEXT("frontend.attachments.factoryNote")) : (Def ? R.Text(Def->Text + TEXT(".blurb")) : FString());
		List->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
		[
			Ring(SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Card, P == Fitted)).ContentPadding(FMargin(14.f, 9.f))
			.OnHovered_Lambda([O, P]() { if (O.IsValid()) O->Act(TEXT("preview"), P.IsNone() ? TEXT("factory") : P.ToString()); })
			.OnUnhovered_Lambda([O]() { if (O.IsValid()) { O->GetRules().StopPreview(); O->Changed(); } })
			.OnClicked_Lambda([O, P]() { if (O.IsValid()) O->Act(TEXT("fit"), P.IsNone() ? TEXT("factory") : P.ToString()); return FReply::Handled(); })
			[
				SNew(SBox).WidthOverride(560.f)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().FillWidth(1.f)
					[
						SNew(SVerticalBox)
						+ SVerticalBox::Slot().AutoHeight()[Txt(R.PartName(P), Display(22.f), Ink())]
						+ SVerticalBox::Slot().AutoHeight()[Txt(Blurb, Body(13.f), InkDim(), true, 440.f)]
					]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Txt(P == Fitted ? R.Text(TEXT("frontend.attachments.fitted")).ToUpper() : FString(), Spaced(Body(11.f, true), 160), Gold())]
				]
			], Owner->Focus == I)
		];
	}
	Col->AddSlot().AutoHeight()[List];
	// The focused option's effect lines and the six bars before (ghost) and after (fill).
	TSharedRef<SVerticalBox> Lines = SNew(SVerticalBox);
	if (!Focused.IsNone())
	{
		for (const FMIEffectLine& L : R.EffectLines(Gun, Focused))
		{
			Lines->AddSlot().AutoHeight().Padding(0.f, 1.f)[Txt(L.Text, Body(14.f, true), L.Sign > 0 ? FLinearColor(0.4f, 0.9f, 0.5f) : L.Sign < 0 ? FLinearColor(1.f, 0.42f, 0.36f) : InkDim())];
		}
	}
	else
	{
		Lines->AddSlot().AutoHeight()[Txt(R.Text(TEXT("frontend.attachments.noChange")), Body(14.f), InkDim())];
	}
	const FMIGunBuild Shown = R.ShownBuild();
	const FMIGunBuild* Have = R.GetSetup().BuildOf(Gun);
	Col->AddSlot().AutoHeight().Padding(0.f, 14.f, 0.f, 0.f)
	[
		SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth().Padding(0.f, 0.f, 28.f, 0.f)[SNew(SBox).WidthOverride(330.f)[Lines]]
		+ SHorizontalBox::Slot().AutoWidth()[Bars(Gun, &Shown, Have)]
	];
	// Hold to reset build (0.6 s): the fill shows the hold.
	const float Hold = static_cast<float>(FMath::Clamp(Owner->GetHoldReset() / FMath::Max(0.01, R.GetData().ResetHold), 0.0, 1.0));
	Col->AddSlot().AutoHeight().Padding(0.f, 14.f, 0.f, 0.f)
	[
		SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Txt(R.Text(TEXT("frontend.attachments.reset")).ToUpper() + TEXT("   R / Y"), Spaced(Body(12.f, true), 140), InkFaint())]
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(12.f, 0.f)[Bar(Hold, -1.0, 120.f)]
	];
	return Frame(SNew(SScrollBox) + SScrollBox::Slot()[Col], false);
}

// ------------------------------------------------------------------------------------------------ Block & Style

TSharedRef<SWidget> SMIFrontEnd::Where()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	const FMIRunSetup& S = R.GetSetup();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	const int32 F = Owner->Focus;
	const auto Row = [&](int32 Index, const FString& Label, TSharedRef<SWidget> Content)
	{
		return Ring(SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[Txt(Label.ToUpper(), Spaced(Body(13.f, true), 200), InkFaint())]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 0.f)[Content], F == Index, 10.f);
	};
	const auto Chip = [&](const TCHAR* Act, FName V, const FString& Label, bool bOn)
	{
		const FString A(Act);
		return SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Chip, bOn)).ContentPadding(FMargin(16.f, 7.f))
			.OnClicked_Lambda([O, A, V]() { if (O.IsValid()) O->Act(A, V.ToString()); return FReply::Handled(); })
			[Txt(Label.ToUpper(), Spaced(Body(13.f, true), 120), bOn ? Bg() : InkDim())];
	};
	// 1. Level cards.
	TSharedRef<SHorizontalBox> Levels = SNew(SHorizontalBox);
	for (const FName L : R.Levels())
	{
		const FMILevelEntry& E = R.GetData().Levels[L];
		TArray<FString> ModeNames;
		for (const FName M : R.GetReadiness().ModesOf(L)) ModeNames.Add(R.Text(TEXT("text.modes.") + M.ToString() + TEXT(".name")));
		const FString Place = E.Place.Contains(S.Time) ? R.Text(E.Place[S.Time]) : FString();
		Levels->AddSlot().AutoWidth()
		[
			SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Card, L == S.Level)).ContentPadding(FMargin(16.f, 12.f))
			.OnClicked_Lambda([O, L]() { if (O.IsValid()) O->Act(TEXT("level"), L.ToString()); return FReply::Handled(); })
			[
				SNew(SBox).WidthOverride(560.f)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(E.TextKey + TEXT(".name")), Display(32.f), Ink())]
					+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(E.TextKey + TEXT(".blurb")), Body(14.f), InkDim(), true, 540.f)]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Txt(Place, Body(12.f, true), Gold())]
					+ SVerticalBox::Slot().AutoHeight()[Txt(R.GetData().Format(TEXT("frontend.level.modes"), {{TEXT("modes"), FString::Join(ModeNames, TEXT(" · "))}}), Body(12.f), InkFaint())]
				]
			]
		];
	}
	// 2. Time.
	TSharedRef<SHorizontalBox> Times = SNew(SHorizontalBox);
	for (const FName T : Owner->GetGame()->GetSettings().Rules.Times)
	{
		Times->AddSlot().AutoWidth().Padding(0.f, 0.f, 8.f, 0.f)[Chip(TEXT("time"), T, R.Text(TEXT("frontend.level.times.") + T.ToString()), T == S.Time)];
	}
	// 3. Mode cards (Hold the Block shows the best).
	TSharedRef<SHorizontalBox> Modes = SNew(SHorizontalBox);
	for (const FName M : R.Modes())
	{
		const bool bOn = M == S.Mode;
		const FString Best = M == TEXT("holdout") ? R.GetData().Format(TEXT("frontend.mode.best"), {{TEXT("score"), FMIText::Grouped(Owner->GetGame()->GetSettings().GetBest())}}) : FString();
		Modes->AddSlot().AutoWidth().Padding(0.f, 0.f, 10.f, 0.f)
		[
			SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Card, bOn)).ContentPadding(FMargin(14.f, 10.f))
			.OnClicked_Lambda([O, M]() { if (O.IsValid()) O->Act(TEXT("mode"), M.ToString()); return FReply::Handled(); })
			[
				SNew(SBox).WidthOverride(275.f)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(TEXT("text.modes.") + M.ToString() + TEXT(".name")), Display(24.f), Ink())]
					+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(TEXT("text.modes.") + M.ToString() + TEXT(".note")), Body(12.f), InkDim(), true, 255.f)]
					+ SVerticalBox::Slot().AutoHeight()[Txt(Best, Body(12.f, true), Gold())]
				]
			]
		];
	}
	// 4. Difficulty.
	TSharedRef<SHorizontalBox> Diffs = SNew(SHorizontalBox);
	for (const FName D : Owner->GetGame()->GetSettings().Rules.Difficulties)
	{
		Diffs->AddSlot().AutoWidth().Padding(0.f, 0.f, 8.f, 0.f)[Chip(TEXT("difficulty"), D, R.Text(TEXT("text.difficulties.") + D.ToString()), D == S.Difficulty)];
	}
	return Frame(SNew(SScrollBox) + SScrollBox::Slot()
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[Heading(R.Text(TEXT("frontend.where.kicker")), R.Text(TEXT("frontend.where.title")))]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 18.f, 0.f, 0.f)[Row(0, R.Text(TEXT("frontend.level.title")), Levels)]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 14.f, 0.f, 0.f)[Row(1, R.Text(TEXT("frontend.level.time")),
				SNew(SVerticalBox) + SVerticalBox::Slot().AutoHeight()[Times]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Txt(R.Text(TEXT("text.interface.title.timeNotes.") + S.Time.ToString()), Body(12.f), InkDim())])]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 14.f, 0.f, 0.f)[Row(2, R.Text(TEXT("frontend.mode.title")), Modes)]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 14.f, 0.f, 0.f)[Row(3, R.Text(TEXT("frontend.mode.difficulty")),
				SNew(SVerticalBox) + SVerticalBox::Slot().AutoHeight()[Diffs]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)[Txt(R.Text(TEXT("frontend.mode.difficultyNotes.") + S.Difficulty.ToString()) + TEXT("  ") + R.Text(TEXT("text.notes.difficulty")), Body(12.f), InkDim(), true, 600.f)])]
		], false);
}

// ------------------------------------------------------------------------------------------------ Briefing

TSharedRef<SWidget> SMIFrontEnd::Briefing()
{
	const FMIFrontEndRules& R = Owner->GetRules();
	const FMIRunSetup& S = R.GetSetup();
	TWeakObjectPtr<UMIFrontEnd> O = Owner;
	const FMILevelEntry* L = R.GetData().Levels.Find(S.Level);
	TArray<FString> Guns;
	for (int32 I = 0; I < S.Guns.Num(); ++I)
	{
		int32 Pips = 0;
		if (const FMIGunBuild* B = S.BuildOf(S.Guns[I]))
		{
			for (const TPair<FName, FName>& P : B->Parts) { const FMIAttachmentDef* D = R.GetData().FindPart(P.Value); Pips += D && !D->bBaseline ? 1 : 0; }
		}
		Guns.Add(FString::Printf(TEXT("%d %s%s"), I + 1, *R.GunName(S.Guns[I]), Pips > 0 ? *(TEXT(" ") + FString::ChrN(Pips, TEXT('▪'))) : TEXT("")));
	}
	const FString Tagline = R.Text(S.Mode == TEXT("holdout") ? TEXT("text.location.taglineHoldout") : TEXT("text.location.tagline"));
	const FString Style = R.Text(TEXT("text.modes.") + S.Mode.ToString() + TEXT(".name")) + TEXT(" · ") + R.Text(TEXT("text.difficulties.") + S.Difficulty.ToString());
	struct FLine { const TCHAR* Label; FString Value; FString Sub; const TCHAR* Screen; };
	const TArray<FLine> Lines = {
		{TEXT("frontend.briefing.crew"), R.CrewName(S.Crew), R.CrewTagline(S.Crew), TEXT("crew")},
		{TEXT("frontend.briefing.loadout"), FString::Join(Guns, TEXT("    ")), FString(), TEXT("loadout")},
		{TEXT("frontend.briefing.block"), L ? R.Text(L->TextKey + TEXT(".name")) : FString(), L && L->Place.Contains(S.Time) ? R.Text(L->Place[S.Time]) : FString(), TEXT("where")},
		{TEXT("frontend.briefing.style"), Style, Tagline, TEXT("where")},
	};
	TSharedRef<SVerticalBox> Card = SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()[Heading(R.Text(TEXT("frontend.briefing.kicker")), R.Text(TEXT("frontend.briefing.title")))];
	for (int32 I = 0; I < Lines.Num(); ++I)
	{
		const FString Sc(Lines[I].Screen);
		Card->AddSlot().AutoHeight().Padding(0.f, 14.f, 0.f, 0.f)
		[
			Ring(SNew(SBorder).BorderImage(Box(WithAlpha(Plate(), 0.9f), 8.f, PlateEdge(), 1.f)).Padding(FMargin(16.f, 10.f))
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).WidthOverride(4.f).HeightOverride(40.f)[SNew(SImage).Image(Box(Line(FMath::Min(I, 3)), 2.f))]]
				+ SHorizontalBox::Slot().FillWidth(1.f).Padding(14.f, 0.f)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()[Txt(R.Text(Lines[I].Label).ToUpper(), Spaced(Body(11.f, true), 200), InkFaint())]
					+ SVerticalBox::Slot().AutoHeight()[Txt(Lines[I].Value, Display(24.f), Ink())]
					+ SVerticalBox::Slot().AutoHeight()[Txt(Lines[I].Sub, Body(13.f), InkDim(), true, 560.f)]
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					SNew(SButton).ButtonStyle(ButtonStyle(EBtn::Quiet)).ContentPadding(FMargin(14.f, 6.f))
					.OnClicked_Lambda([O, Sc]() { if (O.IsValid()) O->Act(TEXT("edit"), Sc); return FReply::Handled(); })
					[Txt(R.Text(TEXT("frontend.briefing.change")).ToUpper(), Spaced(Body(12.f, true), 140), Ink())]
				]
			], Owner->Focus == I, 10.f)
		];
	}
	Card->AddSlot().AutoHeight().Padding(0.f, 18.f, 0.f, 0.f)[ControlsGlance()];
	return Frame(SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(700.f)[SNew(SScrollBox) + SScrollBox::Slot()[Card]]]
		+ SHorizontalBox::Slot().FillWidth(1.f)[SNullWidget::NullWidget], false);
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
