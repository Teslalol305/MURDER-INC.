#include "UI/MIMenus.h"

namespace MIMenusPrivate
{
	FString Clock(double Seconds)
	{
		const int32 S = FMath::Max(0, FMath::FloorToInt32(Seconds));
		return FString::Printf(TEXT("%d:%02d"), S / 60, S % 60);
	}

	FMIMenuItem Item(FName Id, const FString& Label, const FString& Value = FString(), bool bAdjust = false)
	{
		FMIMenuItem I;
		I.Id = Id;
		I.Label = Label;
		I.Value = Value;
		I.bAdjust = bAdjust;
		return I;
	}
}

FMIMenuHit FMIMenuLayout::HitTest(const FVector2D& Point) const
{
	FMIMenuHit Hit;
	if (Screen == EMIMenuScreen::None || !(Width > 0.0) || !(RowHeight > 0.0) || Adjust.Num() == 0
		|| Point.X < X || Point.X >= X + Width || Point.Y < Top)
	{
		return Hit;
	}
	const double Pitch = RowHeight + FMath::Max(0.0, RowGap);
	const int32 Row = FMath::FloorToInt32((Point.Y - Top) / Pitch);
	if (Row < 0 || Row >= Adjust.Num() || Point.Y - Top - Row * Pitch >= RowHeight)
	{
		return Hit;  // below the last row, or in the gap under a row
	}
	Hit.Row = Row;
	Hit.Side = Adjust[Row] ? (Point.X < X + Width * 0.5 ? -1 : 1) : 0;
	return Hit;
}

FMIMenuHit FMIMenu::HitTest(const FVector2D& Point) const
{
	return Layout.Screen == Screen && Layout.Adjust.Num() == Items.Num() ? Layout.HitTest(Point) : FMIMenuHit();
}

void FMIMenu::Build(EMIMenuScreen InScreen, const FMISettings& S, const FMIText& Copy, const FMIText& Ui, const TOptional<FMIRunCard>& Card, FName Mode)
{
	using namespace MIMenusPrivate;
	const FName Keep = Current() && InScreen == Screen ? Current()->Id : NAME_None;
	Screen = InScreen;
	Kicker.Reset();
	Title.Reset();
	Note.Reset();
	Stats.Reset();
	Items.Reset();
	const FString OnOff = S.bInvertY ? Ui.Get(TEXT("panel.on")) : Ui.Get(TEXT("panel.off"));
	switch (Screen)
	{
	case EMIMenuScreen::Title:
		Kicker = Copy.Get(TEXT("title.eyebrow"));
		Title = Copy.Get(TEXT("title.wordmark"));
		Note = Copy.Get(TEXT("title.premise"));
		Items.Add(Item(TEXT("start"), Copy.Get(TEXT("title.start"))));
		Items.Add(Item(TEXT("mode"), Ui.Get(TEXT("title.modeLabel")), Copy.Get(FString::Printf(TEXT("modes.%s.name"), *S.Mode.ToString())), true));
		Items.Add(Item(TEXT("difficulty"), Ui.Get(TEXT("title.difficultyLabel")), Copy.Get(FString::Printf(TEXT("difficulties.%s"), *S.Difficulty.ToString())), true));
		Items.Add(Item(TEXT("time"), Ui.Get(TEXT("title.timeLabel")), Ui.Get(FString::Printf(TEXT("title.times.%s"), *S.Time.ToString())), true));
		Items.Add(Item(TEXT("settings"), Copy.Get(TEXT("title.settings"))));
		Stats.Add({Copy.Get(FString::Printf(TEXT("modes.%s.name"), *S.Mode.ToString())), Copy.Get(FString::Printf(TEXT("modes.%s.note"), *S.Mode.ToString()))});
		break;
	case EMIMenuScreen::Pause:
		Kicker = Copy.Get(TEXT("cards.pause.kicker"));
		Title = Copy.Get(TEXT("cards.pause.title"));
		Items.Add(Item(TEXT("resume"), Copy.Get(TEXT("cards.pause.resume"))));
		Items.Add(Item(TEXT("restart"), Copy.Get(TEXT("cards.pause.restart"))));
		Items.Add(Item(TEXT("difficulty"), Ui.Get(TEXT("panel.difficulty")), Copy.Get(FString::Printf(TEXT("difficulties.%s"), *S.Difficulty.ToString())), true));
		Items.Add(Item(TEXT("settings"), Copy.Get(TEXT("cards.pause.settings"))));
		Note = Copy.Get(TEXT("notes.difficulty"));
		break;
	case EMIMenuScreen::Settings:
		Kicker = Ui.Get(TEXT("panel.label"));
		Title = Ui.Get(TEXT("panel.tabs.settings"));
		Items.Add(Item(TEXT("sens"), Ui.Get(TEXT("panel.sens")), FString::Printf(TEXT("%.2fx"), S.Sens), true));
		Items.Add(Item(TEXT("invert"), Ui.Get(TEXT("panel.invertY")), OnOff, true));
		Items.Add(Item(TEXT("volume"), Ui.Get(TEXT("panel.volume")), FString::Printf(TEXT("%d%%"), FMath::RoundToInt32(S.Volume * 100.0)), true));
		Items.Add(Item(TEXT("fov"), Ui.Get(TEXT("panel.fov")), FString::Printf(TEXT("%d°"), FMath::RoundToInt32(S.Fov)), true));
		Items.Add(Item(TEXT("view"), Ui.Get(TEXT("panel.view")), Ui.Get(FString::Printf(TEXT("panel.views.%d"), S.View)), true));
		Items.Add(Item(TEXT("quality"), Ui.Get(TEXT("panel.quality")), S.Quality == TEXT("auto") ? Ui.Get(TEXT("panel.auto")) : Ui.Get(FString::Printf(TEXT("panel.qualities.%s"), *S.Quality.ToString())), true));
		Items.Add(Item(TEXT("difficulty"), Ui.Get(TEXT("panel.difficulty")), Copy.Get(FString::Printf(TEXT("difficulties.%s"), *S.Difficulty.ToString())), true));
		// The Unreal build's own row (the copy deck has no words for it): which names a controller's buttons get.
		Items.Add(Item(TEXT("padnames"), TEXT("Controller"), S.bPadPlayStation ? TEXT("PlayStation") : TEXT("Xbox"), true));
		// The Unreal build's own row too: the story's ground path and objective markers (docs/unreal/PLAY.md, guide lane).
		Items.Add(Item(TEXT("guide"), TEXT("Path and markers"), S.bGuide ? Ui.Get(TEXT("panel.on")) : Ui.Get(TEXT("panel.off")), true));
		Items.Add(Item(TEXT("back"), Ui.Get(TEXT("panel.close"))));
		break;
	case EMIMenuScreen::Dead:
		Kicker = Copy.Get(TEXT("cards.dead.kicker"));
		Title = Copy.Get(TEXT("cards.dead.title"));
		if (Card.IsSet())
		{
			const FMIRunCard& C = Card.GetValue();
			Stats.Add({Copy.Get(TEXT("cards.dead.stats.time")), Clock(C.Time)});
			if (C.Mode == TEXT("holdout"))
			{
				Stats.Add({Copy.Get(TEXT("cards.dead.stats.waves")), FString::FromInt(C.Wave)});  // cardData: wave = waves cleared
				Stats.Add({Copy.Get(TEXT("cards.dead.stats.kills")), FString::FromInt(C.Kills)});
				Stats.Add({Copy.Get(TEXT("cards.dead.stats.score")), FMIText::Grouped(C.Score)});
				Stats.Add({Copy.Get(TEXT("cards.dead.stats.best")), FMIText::Grouped(C.Best) + (C.bNewBest ? TEXT("  ") + Ui.Get(TEXT("cards.newBest")) : FString())});
			}
			else
			{
				Stats.Add({Copy.Get(TEXT("cards.dead.stats.reels")), FString::Printf(TEXT("%d / %d"), C.Reels, C.Total)});
				Stats.Add({Copy.Get(TEXT("cards.dead.stats.kills")), FString::FromInt(C.Kills)});
			}
		}
		Items.Add(Item(TEXT("retry"), Copy.Get(TEXT("cards.dead.retry"))));
		Items.Add(Item(TEXT("totitle"), Ui.Get(TEXT("cards.toTitle"))));
		break;
	case EMIMenuScreen::Debrief:
		Kicker = Copy.Get(TEXT("cards.debrief.kicker"));
		Title = Copy.Get(TEXT("cards.debrief.title"));
		if (Card.IsSet())
		{
			const FMIRunCard& C = Card.GetValue();
			Stats.Add({Copy.Get(TEXT("cards.debrief.stats.rating")), C.RatingName});
			Stats.Add({Copy.Get(TEXT("cards.debrief.stats.time")), Clock(C.Time)});
			Stats.Add({Copy.Get(TEXT("cards.debrief.stats.accuracy")), C.Accuracy < 0.0 ? FString(TEXT("—")) : FString::Printf(TEXT("%d%%"), FMath::RoundToInt32(C.Accuracy * 100.0))});
			Stats.Add({Copy.Get(TEXT("cards.debrief.stats.kills")), FString::FromInt(C.Kills)});
			Stats.Add({Copy.Get(TEXT("cards.debrief.stats.retries")), FString::FromInt(C.Retries)});
		}
		Items.Add(Item(TEXT("again"), Copy.Get(TEXT("cards.debrief.again"))));
		Items.Add(Item(TEXT("totitle"), Ui.Get(TEXT("cards.toTitle"))));
		break;
	default:
		break;
	}
	const int32 K = IndexOf(Keep);
	Selected = K != INDEX_NONE ? K : 0;
}
