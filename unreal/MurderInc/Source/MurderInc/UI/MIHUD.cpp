#include "UI/MIHUD.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Flow/MIGameSubsystem.h"
#include "Player/MIPlayerCharacter.h"
#include "Weapons/MIWeaponComponent.h"
#include "World/MIBoxWorld.h"

namespace MIHUDPrivate
{
	const FLinearColor White(1.f, 1.f, 1.f, 0.92f);
	const FLinearColor Dim(1.f, 1.f, 1.f, 0.6f);
	const FLinearColor Amber(1.f, 0.72f, 0.28f, 1.f);
	const FLinearColor Red(1.f, 0.3f, 0.25f, 1.f);
}

void AMIHUD::Centered(const FString& Text, double Y, const FLinearColor& Colour, UFont* Font, float Scale)
{
	float TW = 0.f, TH = 0.f;
	GetTextSize(Text, TW, TH, Font, Scale);
	DrawText(Text, Colour, Canvas->ClipX * 0.5 - TW * 0.5, Y, Font, Scale);
}

void AMIHUD::DrawHUD()
{
	Super::DrawHUD();
	if (!Canvas)
	{
		return;
	}
	UFont* Font = GEngine ? GEngine->GetLargeFont() : nullptr;
	UMIGameSubsystem* Game = UMIGameSubsystem::Get(this);
	if (!Game || !Game->IsBooted())
	{
		DrawPlay(Font);  // a map without the game flow (L_GameplayTest)
		return;
	}
	const EMIGameState S = Game->GetRules().GetState();
	if (S == EMIGameState::Intro || S == EMIGameState::Playing)
	{
		DrawPlay(Font);
	}
	DrawFlow(*Game, Font);
	if (Game->GetMenu().Screen != EMIMenuScreen::None)
	{
		DrawMenu(*Game, Font);
	}
}

void AMIHUD::DrawPlay(UFont* Font)
{
	using namespace MIHUDPrivate;
	const AMIPlayerCharacter* Player = Cast<AMIPlayerCharacter>(GetOwningPawn());
	if (!Player || !Player->GetWeapon() || !Player->GetWeapon()->IsReady())
	{
		return;
	}
	const FMIPlayerRules& Rules = Player->GetPlayerRules();
	const UMIWeaponComponent* Weapon = Player->GetWeapon();
	const FMIWeaponView View = Weapon->GetView();
	const double W = Canvas->ClipX;
	const double H = Canvas->ClipY;
	const double CX = W * 0.5;
	const double CY = H * 0.5;

	// Crosshair: the gap is where the spread cone meets the screen (vertical field of view, pixels from the centre).
	if (Rules.bAlive && View.Activity != EMIWeaponActivity::Dropped)
	{
		const double Half = FMath::Tan(FMath::DegreesToRadians(Rules.ViewFov) * 0.5);
		const double Gap = Half > 0.0 ? FMath::Tan(FMath::DegreesToRadians(View.Spread)) / Half * CY : 0.0;
		const double Arm = FMath::Max(6.0, H * 0.012);
		const float Alpha = static_cast<float>(1.0 - 0.85 * View.Ads);
		const FLinearColor Hair(1.f, 1.f, 1.f, 0.85f * Alpha);
		DrawLine(CX + Gap, CY, CX + Gap + Arm, CY, Hair, 2.f);
		DrawLine(CX - Gap, CY, CX - Gap - Arm, CY, Hair, 2.f);
		DrawLine(CX, CY + Gap, CX, CY + Gap + Arm, Hair, 2.f);
		DrawLine(CX, CY - Gap, CX, CY - Gap - Arm, Hair, 2.f);
	}

	// Hit marker for a quarter of a second.
	if (Weapon->GetSinceHit() < 0.25)
	{
		const FLinearColor Mark = Weapon->WasLastHitKill() ? FLinearColor(1.f, 0.2f, 0.15f, 1.f) : White;
		const double A = H * 0.008, B = H * 0.02;
		DrawLine(CX - B, CY - B, CX - A, CY - A, Mark, 2.f);
		DrawLine(CX + B, CY - B, CX + A, CY - A, Mark, 2.f);
		DrawLine(CX - B, CY + B, CX - A, CY + A, Mark, 2.f);
		DrawLine(CX + B, CY + B, CX + A, CY + A, Mark, 2.f);
	}

	const double Reserve = Weapon->GetRules().GetReserve();
	const FString Ammo = FMath::IsFinite(Reserve)
		? FString::Printf(TEXT("%s  %d / %d"), *View.Weapon.ToString().ToUpper(), View.Mag, static_cast<int32>(Reserve))
		: FString::Printf(TEXT("%s  %d / -"), *View.Weapon.ToString().ToUpper(), View.Mag);
	const FName Cue = Weapon->GetRules().GetCue();
	float TW = 0.f, TH = 0.f;
	GetTextSize(Ammo, TW, TH, Font, 1.5f);
	DrawText(Ammo, White, W - TW - W * 0.03, H - TH - H * 0.04, Font, 1.5f);
	if (!Cue.IsNone())
	{
		DrawText(Cue.ToString().ToUpper(), Amber, W - TW - W * 0.03, H - 2.2 * TH - H * 0.04, Font, 1.2f);
	}
	const FString Health = FString::Printf(TEXT("HEALTH %d"), FMath::CeilToInt32(Rules.Health));
	DrawText(Health, Rules.Health < Rules.MaxHealth * 0.3 ? Red : White, W * 0.03, H - TH - H * 0.04, Font, 1.5f);
	if (Rules.Hurt > 0.0)
	{
		DrawRect(FLinearColor(0.6f, 0.f, 0.f, static_cast<float>(0.25 * Rules.Hurt)), 0.f, 0.f, W, H);
	}
}

void AMIHUD::DrawFlow(UMIGameSubsystem& Game, UFont* Font)
{
	using namespace MIHUDPrivate;
	const FMIGameRules& Rules = Game.GetRules();
	const FMIFlowView& V = Rules.View();
	const EMIGameState S = Rules.GetState();
	const double W = Canvas->ClipX;
	const double H = Canvas->ClipY;
	if (S == EMIGameState::Intro || S == EMIGameState::Playing)
	{
		// Objective and tally, top left.
		DrawText(V.Objective.ToUpper(), White, W * 0.03, H * 0.04, Font, 1.3f);
		const FString Tally = Rules.GetMode() == TEXT("mission") ? FString::Printf(TEXT("%d / %d"), V.Reels, V.ReelsTotal) : V.Tally;
		DrawText(Tally, Amber, W * 0.03, H * 0.04 + 30.0, Font, 1.2f);
		// Markers: objective codes where they are, with the distance.
		const AMIPlayerCharacter* P = Cast<AMIPlayerCharacter>(GetOwningPawn());
		for (const FMIFlowView::FMarker& M : V.Markers)
		{
			const FVector At = MI::Web::ToUnreal(M.Pos) + FVector(0, 0, 150.0);
			const FVector Screen = Project(At, true);
			if (Screen.Z <= 0.0)
			{
				continue;
			}
			const double Metres = P ? FVector::Dist(P->GetActorLocation(), At) / 100.0 : 0.0;
			const FString Label = FString::Printf(TEXT("[%s] %dm"), *M.Code, FMath::RoundToInt32(Metres));
			float TW = 0.f, TH = 0.f;
			GetTextSize(Label, TW, TH, Font, 1.0f);
			DrawText(Label, M.bExit ? FLinearColor(0.5f, 1.f, 0.6f, 1.f) : Amber, Screen.X - TW * 0.5, Screen.Y - TH * 0.5, Font, 1.0f);
		}
		// The hold prompt with its fill.
		if (!V.Prompt.IsEmpty())
		{
			Centered(V.Prompt, H * 0.66, White, Font, 1.3f);
			if (V.PromptProgress > 0.0)
			{
				const double BW = W * 0.18;
				DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.5f), W * 0.5 - BW * 0.5, H * 0.66 + 34.0, BW, 6.0);
				DrawRect(Amber, W * 0.5 - BW * 0.5, H * 0.66 + 34.0, BW * FMath::Clamp(V.PromptProgress, 0.0, 1.0), 6.0);
			}
		}
		if (V.WarnLeft > 0.0 && !V.Warn.IsEmpty())
		{
			Centered(V.Warn.ToUpper(), H * 0.16, Red, Font, 1.6f);
		}
		if (V.MessageLeft > 0.0 && !V.Message.IsEmpty())
		{
			Centered(V.Message, H * 0.22, White, Font, 1.2f);
		}
		if (V.bLocationCard)
		{
			Centered(Game.GetCopy().Get(TEXT("location.place")).ToUpper(), H * 0.40, White, Font, 1.6f);
			Centered(Game.GetCopy().Get(Rules.GetMode() == TEXT("mission") ? TEXT("location.tagline") : TEXT("location.taglineHoldout")), H * 0.40 + 40.0, Dim, Font, 1.2f);
		}
	}
	// The radio strip stays in every state but the title and the pause card; typed at the radio's rate.
	const FMIRadio& Radio = Rules.GetRadio();
	if (S != EMIGameState::Title && S != EMIGameState::Paused && !Radio.Current.IsEmpty())
	{
		const int32 Shown = FMath::Clamp(FMath::FloorToInt32(Radio.CurrentAge * Radio.CharsPerSec), 0, Radio.Current.Len());
		const FString Line = Game.GetCopy().Get(TEXT("radio.speaker")) + TEXT("  ") + Radio.Current.Left(Shown);
		Centered(Line, H * 0.84, FLinearColor(0.75f, 0.9f, 1.f, 1.f), Font, 1.1f);
	}
}

void AMIHUD::DrawMenu(UMIGameSubsystem& Game, UFont* Font)
{
	using namespace MIHUDPrivate;
	const FMIMenu& M = Game.GetMenu();
	const double W = Canvas->ClipX;
	const double H = Canvas->ClipY;
	DrawRect(FLinearColor(0.f, 0.f, 0.f, M.Screen == EMIMenuScreen::Title ? 0.35f : 0.6f), 0.f, 0.f, W, H);
	double Y = H * 0.16;
	if (!M.Kicker.IsEmpty())
	{
		Centered(M.Kicker.ToUpper(), Y, Amber, Font, 1.1f);
		Y += 36.0;
	}
	const bool bTitle = M.Screen == EMIMenuScreen::Title;
	Centered(M.Title, Y, White, Font, bTitle ? 3.0f : 2.2f);
	Y += bTitle ? 80.0 : 64.0;
	if (!M.Note.IsEmpty())
	{
		Centered(M.Note, Y, Dim, Font, 1.0f);
		Y += 40.0;
	}
	for (const TPair<FString, FString>& Stat : M.Stats)
	{
		Centered(Stat.Key + TEXT("    ") + Stat.Value, Y, White, Font, 1.15f);
		Y += 32.0;
	}
	Y += 24.0;
	for (int32 I = 0; I < M.Items.Num(); ++I)
	{
		const FMIMenuItem& Item = M.Items[I];
		const bool bSel = I == M.Selected;
		FString Line = Item.Value.IsEmpty() ? Item.Label : Item.Label + TEXT("    ") + (Item.bAdjust ? TEXT("< ") + Item.Value + TEXT(" >") : Item.Value);
		if (bSel)
		{
			Line = TEXT("> ") + Line + TEXT(" <");
		}
		Centered(Line, Y, bSel ? Amber : White, Font, bSel ? 1.45f : 1.3f);
		Y += 40.0;
	}
}
