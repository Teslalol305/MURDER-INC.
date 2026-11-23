#include "UI/MIHUD.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Flow/MIGameSubsystem.h"
#include "Player/MIPlayerController.h"
#include "UI/MIFrontEnd.h"
#include "UI/MIStyle.h"
#include "Player/MIPlayerCharacter.h"
#include "Weapons/MIWeaponComponent.h"
#include "World/MIBoxWorld.h"
#include "Core/MIEvents.h"
#include "Camera/PlayerCameraManager.h"

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
	// The set-up flow (Slate) replaces the canvas title while it is up (LOADOUT.md 2).
	const bool bFrontEnd = Game->GetFrontEnd() && Game->GetFrontEnd()->IsShown();
	if (Game->GetMenu().Screen != EMIMenuScreen::None && !(bFrontEnd && Game->GetMenu().Screen == EMIMenuScreen::Title))
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
		// Gone while aiming: the sights or the optic's reticle are the point of aim (review 2026-11-23).
		const float Alpha = static_cast<float>(1.0 - FMath::SmoothStep(0.05, 0.55, View.Ads));
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

	DrawWeaponBar(*Player, UMIGameSubsystem::Get(this));
	const FName Cue = Weapon->GetRules().GetCue();
	float TW = 0.f, TH = 0.f;
	if (!Cue.IsNone())
	{
		const FString C = Cue.ToString().ToUpper();
		GetTextSize(C, TW, TH, MIStyle::CanvasDisplay(), 1.f);
		DrawText(C, MIStyle::Gold(), CX - TW * 0.5, CY + H * 0.06, MIStyle::CanvasDisplay(), static_cast<float>(H / 1080.0 * 0.9));
	}
	DrawWheel(*Player);
	const FString Health = FString::Printf(TEXT("HEALTH %d"), FMath::CeilToInt32(Rules.Health));
	DrawText(Health, Rules.Health < Rules.MaxHealth * 0.3 ? Red : White, W * 0.03, H - TH - H * 0.04, Font, 1.5f);
	DrawHurt(*Player, Rules.Hurt);
}

void AMIHUD::DrawHurt(const AMIPlayerCharacter& Player, double Hurt)
{
	UWorld* World = GetWorld();
	if (World && !HitHandle.IsValid())
	{
		if (FMIGameEvents* Events = UMIEventSubsystem::Get(this))
		{
			HitHandle = Events->PlayerHit.AddWeakLambda(this, [this](const FMIPlayerHitEvent& E)
			{
				HitFrom = E.From;
				HitTime = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
			});
		}
	}
	if (Hurt <= 0.0)
	{
		return;
	}
	const double W = Canvas->ClipX;
	const double H = Canvas->ClipY;
	const float K = static_cast<float>(FMath::Clamp(Hurt, 0.0, 1.0));
	// A faint wash (at most 15 % in the centre) and a vignette: bands thickening to the frame's edge.
	DrawRect(FLinearColor(0.55f, 0.f, 0.f, 0.15f * K * 0.6f), 0.f, 0.f, W, H);
	constexpr int32 Bands = 12;
	const double Depth = FMath::Min(W, H) * 0.16;
	for (int32 I = 0; I < Bands; ++I)
	{
		const double T = Depth * (1.0 - static_cast<double>(I) / Bands);  // outer bands first, each one inside the last
		const float A = 0.075f * K;
		const FLinearColor C(0.5f, 0.f, 0.f, A);
		DrawRect(C, 0.f, 0.f, W, T);
		DrawRect(C, 0.f, H - T, W, T);
		DrawRect(C, 0.f, T, T, H - 2.0 * T);
		DrawRect(C, W - T, T, T, H - 2.0 * T);
	}
	// Where it came from: a red wedge on a ring round the crosshair, for 1.5 s after the hit.
	const APlayerController* PC = GetOwningPlayerController();
	if (!HitFrom.IsSet() || !PC || !PC->PlayerCameraManager || !World || World->GetTimeSeconds() - HitTime > 1.5)
	{
		return;
	}
	const FVector To = (HitFrom.GetValue() - PC->PlayerCameraManager->GetCameraLocation()).GetSafeNormal2D();
	const FRotator View = PC->PlayerCameraManager->GetCameraRotation();
	const double Rel = FMath::DegreesToRadians(FRotator::NormalizeAxis(To.Rotation().Yaw - View.Yaw));
	const float Fade = static_cast<float>(1.0 - FMath::Clamp((World->GetTimeSeconds() - HitTime) / 1.5, 0.0, 1.0));
	const double R = H * 0.16;
	const FVector2D C(W * 0.5, H * 0.5);
	const FVector2D Dir(FMath::Sin(Rel), -FMath::Cos(Rel));  // 0 = ahead = up the screen, +90 = right
	const FVector2D Side(-Dir.Y, Dir.X);
	const FVector2D Tip = C + Dir * (R + H * 0.035);
	const FLinearColor Mark(0.85f, 0.06f, 0.04f, 0.9f * Fade);
	for (int32 I = -6; I <= 6; ++I)
	{
		const FVector2D Base = C + Dir * R + Side * (H * 0.006 * I);
		DrawLine(Base.X, Base.Y, Tip.X, Tip.Y, Mark, 2.f);
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
		// Objective and tally, top left, on a soft dark band (fix pass: over brick, sky or a water tank the thin counter
		// did not read). The counter is in the display face, larger, under the title.
		{
			const double K = H / 1080.0;
			const FString Title = V.Objective.ToUpper();
			const FString Tally = Rules.GetMode() == TEXT("mission") ? FString::Printf(TEXT("%d / %d"), V.Reels, V.ReelsTotal) : V.Tally;
			UFont* Big = MIStyle::CanvasDisplay();
			const float TallyScale = static_cast<float>(K * 1.15);
			float TW = 0.f, TH = 0.f, CW = 0.f, CH = 0.f;
			GetTextSize(Title, TW, TH, Font, 1.3f);
			GetTextSize(Tally, CW, CH, Big, TallyScale);
			const double X0 = W * 0.03, Y0 = H * 0.04;
			const double Pad = 12.0 * K;
			if (!Title.IsEmpty() || !Tally.IsEmpty())
			{
				DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.42f), X0 - Pad, Y0 - Pad * 0.6, FMath::Max(TW, CW) + Pad * 2.0, TH + CH + 4.0 * K + Pad * 1.4);
			}
			DrawText(Title, White, X0, Y0, Font, 1.3f);
			DrawText(Tally, Amber, X0, Y0 + TH + 4.0 * K, Big, TallyScale);
		}
		// Markers: objective codes where they are, with the distance. Hidden while the weapon wheel is open, so its
		// labels never collide with them.
		const AMIPlayerCharacter* P = Cast<AMIPlayerCharacter>(GetOwningPawn());
		const AMIPlayerController* WheelPC = Cast<AMIPlayerController>(GetOwningPlayerController());
		const bool bWheel = WheelPC && WheelPC->GetSwitch().IsWheelOpen();
		for (const FMIFlowView::FMarker& M : bWheel ? TArray<FMIFlowView::FMarker>() : V.Markers)
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
			GetTextSize(Label, TW, TH, Font, 1.1f);
			// Never on the crosshair (fix pass: "[1] 24m" sat on the point of aim): a marker inside the centre ring is
			// pushed out along its own direction (straight up when it is dead centre).
			FVector2D C(Screen.X, Screen.Y);
			const FVector2D Mid(W * 0.5, H * 0.5);
			const double Ring = H * 0.075;
			const FVector2D Off = C - Mid;
			if (Off.Size() < Ring)
			{
				const FVector2D Dir = Off.Size() > 1.0 ? Off / Off.Size() : FVector2D(0.0, -1.0);
				C = Mid + Dir * Ring;
			}
			// On a dark backing, so it reads over the truck, the sky or sunlit brick.
			const double Pad = 5.0;
			DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.5f), C.X - TW * 0.5 - Pad, C.Y - TH * 0.5 - Pad * 0.5, TW + Pad * 2.0, TH + Pad);
			DrawText(Label, M.bExit ? FLinearColor(0.5f, 1.f, 0.6f, 1.f) : Amber, C.X - TW * 0.5, C.Y - TH * 0.5, Font, 1.1f);
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
		const FString Speaker = Game.GetCopy().Get(TEXT("radio.speaker")) + TEXT("  ");
		// A soft dark band behind the whole line (polish pass): the strip sits over the forearm and the gun at the
		// hip, where light text on sunlit skin did not read. Placed and sized by the full line, so it neither grows
		// nor slides as the line types.
		float TW = 0.f, TH = 0.f;
		GetTextSize(Speaker + Radio.Current, TW, TH, Font, 1.1f);
		const double X0 = Canvas->ClipX * 0.5 - TW * 0.5;
		// At 0.815 of the height (fix pass: at 0.84 its band touched the weapon strip's band, which now has a tag row).
		const double RY = H * 0.815;
		DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.42f), X0 - 14.0, RY - 6.0, TW + 28.0, TH + 12.0);
		DrawText(Speaker + Radio.Current.Left(Shown), FLinearColor(0.75f, 0.9f, 1.f, 1.f), X0, RY, Font, 1.1f);
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

void AMIHUD::DrawPlate(double X, double Y, double W, double H, const FLinearColor& Fill, const FLinearColor& Edge, float EdgeWidth)
{
	DrawRect(Fill, X, Y, W, H);
	DrawLine(X, Y, X + W, Y, Edge, EdgeWidth);
	DrawLine(X, Y + H, X + W, Y + H, Edge, EdgeWidth);
	DrawLine(X, Y, X, Y + H, Edge, EdgeWidth);
	DrawLine(X + W, Y, X + W, Y + H, Edge, EdgeWidth);
}

void AMIHUD::DrawWeaponBar(const AMIPlayerCharacter& Player, UMIGameSubsystem* Game)
{
	using namespace MIStyle;
	const UMIWeaponComponent* Weapon = Player.GetWeapon();
	const FMIWeaponRules& R = Weapon->GetRules();
	const double K = Canvas->ClipY / 1080.0;  // legible at 1080p and 4K alike
	UFont* Big = CanvasDisplay();
	UFont* Small = CanvasBody();
	const UMIDataSubsystem* Data = UMIDataSubsystem::Get(this);
	const FMILoadoutData* Loadout = Data && Data->IsLoadoutLoaded() ? &Data->GetLoadout() : nullptr;
	const int32 N = R.NumGuns();
	const double SW = 168.0 * K, SH = 74.0 * K, Gap = 8.0 * K, MeleeW = 118.0 * K, BagW = 104.0 * K;
	const double Total = N * (SW + Gap) + MeleeW + Gap + BagW;
	double X = Canvas->ClipX - Total - 40.0 * K;
	const double Y = Canvas->ClipY - SH - 40.0 * K;
	const double TagH = 26.0 * K;  // the row above the slots: the mode badges
	// The fire-mode prompt on a two-mode gun (the selector works without its clip): the key as a key cap, then what it
	// does ("[B] SWITCH TO SEMI"), left of the slots on the tag row, so it never reads as a second mode beside the
	// badge (fix pass: "B SEMI" next to "AUTO" read as two modes, and the aimed gun covered the "B").
	FString Prompt;
	double PromptW = 0.0;
	const float PS = static_cast<float>(K * 0.75);
	const double Cap = TagH - 4.0 * K;
	if (R.HasTwoModes(R.GetCurrentIndex()))
	{
		const bool bSemi = R.IsSemi(R.GetCurrentIndex());
		FString To = Loadout ? Loadout->Text(bSemi ? TEXT("frontend.hud.modes.auto") : TEXT("frontend.hud.modes.semi")) : FString();
		if (To.IsEmpty()) To = bSemi ? TEXT("AUTO") : TEXT("SEMI");
		FString Verb = Loadout ? Loadout->Text(TEXT("frontend.hud.modes.switchTo")) : FString();
		if (Verb.IsEmpty()) Verb = TEXT("SWITCH TO");
		Prompt = Verb + TEXT(" ") + To;
		float PW = 0.f, PH = 0.f;
		GetTextSize(Prompt, PW, PH, Small, PS);
		PromptW = Cap + 8.0 * K + PW;
	}
	const double PromptX = X - (PromptW > 0.0 ? PromptW + 16.0 * K : 0.0);
	// The whole strip on a soft dark band (fix pass: the tags floated over the gun's receiver and stock).
	DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.4f), PromptX - 12.0 * K, Y - TagH - 12.0 * K, X - PromptX + Total + 24.0 * K, SH + TagH + 24.0 * K);
	if (!Prompt.IsEmpty())
	{
		float TW = 0.f, TH = 0.f;
		GetTextSize(TEXT("B"), TW, TH, Small, PS);
		const double PY = Y - TagH;
		DrawPlate(PromptX, PY, Cap, Cap, WithAlpha(Plate(), 0.9f), Ink(), 1.5f);
		DrawText(TEXT("B"), Ink(), PromptX + (Cap - TW) * 0.5, PY + (Cap - TH) * 0.5, Small, PS);
		GetTextSize(Prompt, TW, TH, Small, PS);
		DrawText(Prompt, InkDim(), PromptX + Cap + 8.0 * K, PY + (Cap - TH) * 0.5, Small, PS);
	}
	static const TCHAR* Glyphs[] = {TEXT("1"), TEXT("2"), TEXT("3"), TEXT("4")};
	for (int32 I = 0; I < N; ++I)
	{
		const FMIWeaponDef& D = R.GetData().Guns[I];
		const bool bCurrent = I == R.GetCurrentIndex();
		DrawPlate(X, Y, SW, SH, WithAlpha(Plate(), bCurrent ? 0.86f : 0.6f), bCurrent ? Gold() : WithAlpha(PlateEdge(), 0.9f), bCurrent ? 2.f : 1.f);
		if (bCurrent)
		{
			DrawRect(Gold(), X, Y, 4.0 * K, SH);
		}
		DrawText(Glyphs[FMath::Clamp(I, 0, 3)], bCurrent ? Gold() : InkFaint(), X + 10.0 * K, Y + 6.0 * K, Small, static_cast<float>(K * 0.85));
		DrawText(D.Name, bCurrent ? Ink() : InkDim(), X + 24.0 * K, Y + 4.0 * K, Big, static_cast<float>(K * 0.78));
		// Magazine pips (one per round, up to 30 shown) and the count.
		const int32 Mag = R.GetMagOf(I);
		const int32 Shown = FMath::Min(D.MagSize, 30);
		const double PipW = (SW - 70.0 * K) / FMath::Max(1, Shown);
		for (int32 P = 0; P < Shown; ++P)
		{
			const bool bFull = P < FMath::CeilToInt32(static_cast<double>(Mag) * Shown / FMath::Max(1, D.MagSize));
			DrawRect(bFull ? WithAlpha(Ink(), bCurrent ? 0.9f : 0.55f) : WithAlpha(PlateEdge(), 0.8f), X + 12.0 * K + P * PipW, Y + SH - 14.0 * K, FMath::Max(1.0, PipW - 1.5 * K), 6.0 * K);
		}
		const FString Count = FString::Printf(TEXT("%d"), Mag);
		float TW = 0.f, TH = 0.f;
		GetTextSize(Count, TW, TH, Big, static_cast<float>(K * 0.9));
		DrawText(Count, Mag == 0 ? Red() : (bCurrent ? Ink() : InkDim()), X + SW - TW - 10.0 * K, Y + SH - TH - 2.0 * K, Big, static_cast<float>(K * 0.9));
		// The gun's mode (AUTO / SEMI) as one badge over its slot: filled on the gun in hand, outlined on the others.
		if (R.HasTwoModes(I))
		{
			FString Mode = Loadout ? Loadout->Text(R.IsSemi(I) ? TEXT("frontend.hud.modes.semi") : TEXT("frontend.hud.modes.auto")) : FString();
			if (Mode.IsEmpty()) Mode = R.IsSemi(I) ? TEXT("SEMI") : TEXT("AUTO");
			const float MS = static_cast<float>(K * 0.75);
			GetTextSize(Mode, TW, TH, Small, MS);
			const double BW = TW + 12.0 * K, BH = TagH - 4.0 * K;
			const double BX = X + SW - BW, BY = Y - TagH;
			if (bCurrent)
			{
				DrawPlate(BX, BY, BW, BH, WithAlpha(Cyan(), 0.9f), Cyan());
				DrawText(Mode, Bg(), BX + 6.0 * K, BY + (BH - TH) * 0.5, Small, MS);
			}
			else
			{
				DrawPlate(BX, BY, BW, BH, WithAlpha(Plate(), 0.85f), WithAlpha(Cyan(), 0.6f));
				DrawText(Mode, WithAlpha(Cyan(), 0.8f), BX + 6.0 * K, BY + (BH - TH) * 0.5, Small, MS);
			}
		}
		// One pip per fitted non-baseline attachment.
		int32 Pips = 0;
		for (const TPair<FName, FName>& Fit : D.Fitted)
		{
			const FMIAttachmentDef* Part = Loadout ? Loadout->FindPart(Fit.Value) : nullptr;
			if (Part && !Part->bBaseline)
			{
				DrawRect(Gold(), X + 28.0 * K + Pips * 9.0 * K, Y + SH - 26.0 * K, 6.0 * K, 6.0 * K);
				++Pips;
			}
		}
		X += SW + Gap;
	}
	// Melee comes with you: the slot-1 gun's strike.
	{
		FString Melee;
		if (Game && N > 0)
		{
			const FName First = R.GetData().Guns[0].Id;
			const FMIGunEntry* G = Loadout ? Loadout->FindGun(First) : nullptr;
			Melee = G && G->MeleeKey.StartsWith(TEXT("frontend.")) ? Loadout->Text(G->MeleeKey) : Game->GetCopy().Get(TEXT("weapons.melee.") + First.ToString());
		}
		DrawPlate(X, Y, MeleeW, SH, WithAlpha(Plate(), 0.6f), WithAlpha(PlateEdge(), 0.9f));
		DrawText(TEXT("F"), InkFaint(), X + 10.0 * K, Y + 6.0 * K, Small, static_cast<float>(K * 0.85));
		DrawText(Melee.ToUpper(), InkDim(), X + 10.0 * K, Y + SH * 0.45, Small, static_cast<float>(K * 0.8));
		X += MeleeW + Gap;
	}
	// The shared bag once, or the infinite reserve of a bag-less set-up.
	{
		const double Bag = R.GetBag();
		const FString Label = Loadout ? Loadout->Text(TEXT("frontend.hud.bag")) : FString(TEXT("BAG"));
		const FString Value = Bag >= 0.0 ? FString::Printf(TEXT("%d"), static_cast<int32>(Bag)) : FString(TEXT("\u221e"));
		DrawPlate(X, Y, BagW, SH, WithAlpha(Plate(), 0.6f), WithAlpha(PlateEdge(), 0.9f));
		DrawText(Label, InkFaint(), X + 10.0 * K, Y + 6.0 * K, Small, static_cast<float>(K * 0.8));
		float TW = 0.f, TH = 0.f;
		GetTextSize(Value, TW, TH, Big, static_cast<float>(K * 1.05));
		DrawText(Value, Bag == 0.0 ? Red() : Ink(), X + BagW - TW - 10.0 * K, Y + SH - TH - 2.0 * K, Big, static_cast<float>(K * 1.05));
	}
}

void AMIHUD::DrawWheel(const AMIPlayerCharacter& Player)
{
	using namespace MIStyle;
	const AMIPlayerController* PC = Cast<AMIPlayerController>(GetOwningPlayerController());
	if (!PC || !PC->GetSwitch().IsWheelOpen())
	{
		return;
	}
	const FMIWeaponRules& R = Player.GetWeapon()->GetRules();
	const int32 N = R.NumGuns();
	const double K = Canvas->ClipY / 1080.0;
	const double CX = Canvas->ClipX * 0.5, CY = Canvas->ClipY * 0.5;
	const double Radius = 210.0 * K;
	const int32 Sel = PC->GetSwitch().GetSelection();
	UFont* Big = CanvasDisplay();
	UFont* Small = CanvasBody();
	const UMIDataSubsystem* Data = UMIDataSubsystem::Get(this);
	const FMILoadoutData* Loadout = Data && Data->IsLoadoutLoaded() ? &Data->GetLoadout() : nullptr;
	DrawRect(WithAlpha(Bg(), 0.45f), 0.f, 0.f, Canvas->ClipX, Canvas->ClipY);
	// The ring and the sector dividers (slot 1 at the top, clockwise).
	const int32 Segments = 96;
	for (int32 I = 0; I < Segments; ++I)
	{
		const double A0 = UE_DOUBLE_TWO_PI * I / Segments, A1 = UE_DOUBLE_TWO_PI * (I + 1) / Segments;
		for (const double Rr : {Radius * 0.42, Radius * 1.08})
		{
			DrawLine(CX + Rr * FMath::Sin(A0), CY - Rr * FMath::Cos(A0), CX + Rr * FMath::Sin(A1), CY - Rr * FMath::Cos(A1), WithAlpha(PlateEdge(), 0.9f), 2.f);
		}
	}
	for (int32 I = 0; I < N; ++I)
	{
		const double A = UE_DOUBLE_TWO_PI * (I + 0.5) / N;
		DrawLine(CX + Radius * 0.42 * FMath::Sin(A), CY - Radius * 0.42 * FMath::Cos(A), CX + Radius * 1.08 * FMath::Sin(A), CY - Radius * 1.08 * FMath::Cos(A), WithAlpha(PlateEdge(), 0.9f), 2.f);
	}
	for (int32 I = 0; I < N; ++I)
	{
		const FMIWeaponDef& D = R.GetData().Guns[I];
		const double A = UE_DOUBLE_TWO_PI * I / N;
		const double PX = CX + Radius * 0.76 * FMath::Sin(A), PY = CY - Radius * 0.76 * FMath::Cos(A);
		const bool bSel = I == Sel;
		const double PW = 150.0 * K, PH = 78.0 * K;
		DrawPlate(PX - PW * 0.5, PY - PH * 0.5, PW, PH, bSel ? WithAlpha(Gold(), 0.92f) : WithAlpha(Plate(), 0.9f), bSel ? Gold() : PlateEdge(), bSel ? 2.f : 1.f);
		const FLinearColor Ink1 = bSel ? Bg() : Ink();
		float TW = 0.f, TH = 0.f;
		GetTextSize(D.Name, TW, TH, Big, static_cast<float>(K * 0.95));
		DrawText(D.Name, Ink1, PX - TW * 0.5, PY - PH * 0.5 + 4.0 * K, Big, static_cast<float>(K * 0.95));
		const double Bag = R.GetReserveOf(I);
		FString Line = FString::Printf(TEXT("%d / %s"), R.GetMagOf(I), FMath::IsFinite(Bag) ? *FString::FromInt(static_cast<int32>(Bag)) : TEXT("\u221e"));
		if (R.HasTwoModes(I) && Loadout)
		{
			Line += TEXT("  ") + Loadout->Text(R.IsSemi(I) ? TEXT("frontend.hud.modes.semi") : TEXT("frontend.hud.modes.auto"));
		}
		GetTextSize(Line, TW, TH, Small, static_cast<float>(K * 0.8));
		DrawText(Line, bSel ? Bg() : InkDim(), PX - TW * 0.5, PY + PH * 0.5 - TH - 6.0 * K, Small, static_cast<float>(K * 0.8));
	}
	const FString Centre = Loadout ? Loadout->Text(TEXT("frontend.hud.wheel")) : FString();
	float TW = 0.f, TH = 0.f;
	GetTextSize(Centre.ToUpper(), TW, TH, Small, static_cast<float>(K * 0.9));
	DrawText(Centre.ToUpper(), InkDim(), CX - TW * 0.5, CY - TH * 0.5, Small, static_cast<float>(K * 0.9));
}
