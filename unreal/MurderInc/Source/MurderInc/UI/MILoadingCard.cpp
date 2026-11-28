#include "UI/MILoadingCard.h"

#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "UI/MIStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"
#include "Brushes/SlateColorBrush.h"

namespace
{
	TSharedPtr<SWidget> GCard;

	TSharedRef<SWidget> Text(const FString& S, const FSlateFontInfo& Font, const FLinearColor& C)
	{
		return SNew(STextBlock).Text(FText::FromString(S)).Font(Font).ColorAndOpacity(C).Justification(ETextJustify::Center).AutoWrapText(true);
	}
}

void MILoadingCard::Show(const FString& Kicker, const FString& Title, const FString& Line)
{
	Hide();
	UGameViewportClient* VC = GEngine ? GEngine->GameViewport : nullptr;
	if (!VC)
	{
		return;
	}
	static const FSlateColorBrush Black(FLinearColor(0.02f, 0.02f, 0.025f, 1.f));
	GCard = SNew(SOverlay)
		+ SOverlay::Slot()[SNew(SImage).Image(&Black)]
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
			[
				SNew(SBox).WidthOverride(1280.f).HeightOverride(720.f)
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().FillHeight(1.f)
					+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[Text(Kicker.ToUpper(), MIStyle::Body(22.f, true), MIStyle::Gold())]
					+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 8.f)[Text(Title.ToUpper(), MIStyle::Display(96.f), MIStyle::Ink())]
					+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(120.f, 6.f)[Text(Line, MIStyle::Body(24.f), MIStyle::InkDim())]
					+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 36.f)[Text(TEXT("LOADING"), MIStyle::Body(18.f, true), MIStyle::InkFaint())]
					+ SVerticalBox::Slot().FillHeight(1.f)
				]
			]
		];
	VC->AddViewportWidgetContent(GCard.ToSharedRef(), 20000);
}

void MILoadingCard::Hide()
{
	if (GCard.IsValid())
	{
		if (GEngine && GEngine->GameViewport)
		{
			GEngine->GameViewport->RemoveViewportWidgetContent(GCard.ToSharedRef());
		}
		GCard.Reset();
	}
}

bool MILoadingCard::IsUp() { return GCard.IsValid(); }
