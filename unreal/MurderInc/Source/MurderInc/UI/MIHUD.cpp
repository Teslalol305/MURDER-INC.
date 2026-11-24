#include "UI/MIHUD.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Flow/MIGameSubsystem.h"
#include "Enemies/MIEnemies.h"
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
	else
	{
		Game->GetMenu().Layout.Reset();  // no card on screen: nothing for a click to hit
		HoverScreen = EMIMenuScreen::None;
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
		// Gone while aiming: the sights or the optic's reticle are the point of aim (review 2026-11-23). Drawn as
		// tiles: canvas lines are batched opaque and ignore alpha, which is why the fade never showed and the "+"
		// stayed in the aperture when aimed (polish-chopper-aim).
		const float Alpha = static_cast<float>(1.0 - FMath::SmoothStep(0.05, 0.55, View.Ads));
		if (Alpha > 0.01f)
		{
			const FLinearColor Hair(1.f, 1.f, 1.f, 0.85f * Alpha);
			const float T = 2.f, A = static_cast<float>(Arm), G = static_cast<float>(Gap);
			const float X = static_cast<float>(CX), Y = static_cast<float>(CY);
			DrawRect(Hair, X + G, Y - T * 0.5f, A, T);
			DrawRect(Hair, X - G - A, Y - T * 0.5f, A, T);
			DrawRect(Hair, X - T * 0.5f, Y + G, T, A);
			DrawRect(Hair, X - T * 0.5f, Y - G - A, T, A);
		}
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
	// Health on the same dark band as the weapon strip, bottom left (review 2026-11-24: plain "HEALTH 100" vanished
	// over bright surfaces): the label small, the number in the display face, a bar; red and pulsing when low.
	{
		using namespace MIStyle;
		const double K = H / 1080.0;
		const double Frac = Rules.MaxHealth > 0.0 ? FMath::Clamp(Rules.Health / Rules.MaxHealth, 0.0, 1.0) : 0.0;
		const bool bLow = Frac < 0.3;
		const double T = GetWorld() ? GetWorld()->GetRealTimeSeconds() : 0.0;
		const float Pulse = bLow ? static_cast<float>(0.55 + 0.45 * FMath::Abs(FMath::Sin(T * 5.0))) : 1.f;
		const FLinearColor Tint = bLow ? WithAlpha(MIStyle::Red(), Pulse) : Ink();
		const FString Num = FString::Printf(TEXT("%d"), FMath::CeilToInt32(Rules.Health));
		UFont* Big = CanvasDisplay();
		UFont* Small = CanvasBody();
		const float NumS = static_cast<float>(K * 1.5), LabS = static_cast<float>(K * 0.75);
		float NW = 0.f, NH = 0.f, LW = 0.f, LH = 0.f;
		GetTextSize(TEXT("100"), NW, NH, Big, NumS);
		GetTextSize(TEXT("HEALTH"), LW, LH, Small, LabS);
		const double BarW = 200.0 * K, BarH = 8.0 * K, Pad = 12.0 * K;
		const double BandW = NW + 14.0 * K + BarW + Pad * 2.0;
		const double BandH = NH + Pad * 2.0;
		const double X0 = 40.0 * K, Y0 = H - 40.0 * K - BandH;
		DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.4f), X0, Y0, BandW, BandH);
		if (bLow)
		{
			DrawRect(WithAlpha(MIStyle::Red(), 0.25f * Pulse), X0, Y0, BandW, BandH);
		}
		DrawRect(bLow ? Tint : Gold(), X0, Y0, 4.0 * K, BandH);
		DrawText(Num, Tint, X0 + Pad, Y0 + Pad, Big, NumS);
		const double BX = X0 + Pad + NW + 14.0 * K;
		DrawText(TEXT("HEALTH"), InkDim(), BX, Y0 + Pad, Small, LabS);
		const double BY = Y0 + BandH - Pad - BarH;
		DrawRect(FLinearColor(1.f, 1.f, 1.f, 0.14f), BX, BY, BarW, BarH);
		DrawRect(bLow ? Tint : Ink(), BX, BY, BarW * Frac, BarH);
	}
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
		// Hold the Block: the wave's last one or two enemies, marked in red where they are, or as an arrow on the
		// screen's edge when they are off it (review 2026-11-24: nothing showed where the last enemy was).
		for (const int32 Id : bWheel ? TArray<int32>() : Game.GetLastEnemies())
		{
			const FMIEnemy* E = Game.GetEnemies().Find(Id);
			if (!E || !E->bAlive)
			{
				continue;
			}
			const double K = H / 1080.0;
			const FVector At = MI::Web::ToUnreal(E->Pos) + FVector(0, 0, E->IsGoon() ? 200.0 : 40.0);
			FVector Screen = Project(At, true);
			const FVector2D Mid(W * 0.5, H * 0.5);
			FVector2D C(Screen.X, Screen.Y);
			const double Margin = 48.0 * K;
			bool bEdge = Screen.Z <= 0.0 || C.X < Margin || C.X > W - Margin || C.Y < Margin || C.Y > H - Margin;
			if (bEdge)
			{
				// Behind or off the screen: the direction from the centre, clamped to the edge.
				FVector2D Dir = C - Mid;
				if (Screen.Z <= 0.0) Dir = -Dir;
				if (Dir.IsNearlyZero()) Dir = FVector2D(0.0, -1.0);
				Dir.Normalize();
				const double SX = Dir.X != 0.0 ? (W * 0.5 - Margin) / FMath::Abs(Dir.X) : 1e9;
				const double SY = Dir.Y != 0.0 ? (H * 0.5 - Margin) / FMath::Abs(Dir.Y) : 1e9;
				C = Mid + Dir * FMath::Min(SX, SY);
			}
			const double R = 11.0 * K;
			const FLinearColor Mark = MIStyle::Red();
			// A diamond outline on a dark backing.
			DrawRect(FLinearColor(0.f, 0.f, 0.f, 0.45f), C.X - R - 3.0 * K, C.Y - R - 3.0 * K, (R + 3.0 * K) * 2.0, (R + 3.0 * K) * 2.0);
			const float LW = static_cast<float>(FMath::Max(2.0, 2.5 * K));
			DrawLine(C.X, C.Y - R, C.X + R, C.Y, Mark, LW);
			DrawLine(C.X + R, C.Y, C.X, C.Y + R, Mark, LW);
			DrawLine(C.X, C.Y + R, C.X - R, C.Y, Mark, LW);
			DrawLine(C.X - R, C.Y, C.X, C.Y - R, Mark, LW);
			const double Metres = P ? FVector::Dist(P->GetActorLocation(), At) / 100.0 : 0.0;
			const FString Label = FString::Printf(TEXT("%dm"), FMath::RoundToInt32(Metres));
			float TW = 0.f, TH = 0.f;
			GetTextSize(Label, TW, TH, MIStyle::CanvasBody(), static_cast<float>(K * 0.8));
			DrawText(Label, Mark, C.X - TW * 0.5, C.Y + R + 6.0 * K, MIStyle::CanvasBody(), static_cast<float>(K * 0.8));
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
	// The in-game cards (title, pause, settings, game over, debrief) in the front end's look (review 2026-11-24: small
	// default-font text centred over a dimmed frame read as a placeholder next to the styled set-up screens): a dark
	// plate with a gold rule, the kicker in gold, the title in the display face, the selected item as a gold button with
	// dark text, every size and offset scaled with the canvas height (1080p reference).
	using namespace MIStyle;
	const FMIMenu& M = Game.GetMenu();
	const double W = Canvas->ClipX;
	const double H = Canvas->ClipY;
	const double K = H / 1080.0;
	const bool bTitle = M.Screen == EMIMenuScreen::Title;
	UFont* Big = CanvasDisplay();
	UFont* Body = CanvasBody();
	if (!Big) Big = Font;
	if (!Body) Body = Font;
	DrawRect(FLinearColor(0.f, 0.f, 0.f, bTitle ? 0.35f : 0.55f), 0.f, 0.f, W, H);

	const float KickerS = static_cast<float>(K * 0.95);
	const float TitleS = static_cast<float>(K * (bTitle ? 2.7 : 2.1));
	const float NoteS = static_cast<float>(K * 0.95);
	const float StatS = static_cast<float>(K * 1.0);
	const float ItemS = static_cast<float>(K * 1.1);
	const double CardW = FMath::Min(W - 48.0 * K, 620.0 * K);
	const double Pad = 36.0 * K;
	const double Inner = CardW - Pad * 2.0;
	const double RowH = 46.0 * K, RowGap = 8.0 * K;

	// The note, wrapped to the card by words.
	TArray<FString> NoteLines;
	if (!M.Note.IsEmpty())
	{
		TArray<FString> Words;
		M.Note.ParseIntoArray(Words, TEXT(" "), true);
		FString Line;
		for (const FString& Word : Words)
		{
			const FString Try = Line.IsEmpty() ? Word : Line + TEXT(" ") + Word;
			float TW = 0.f, TH = 0.f;
			GetTextSize(Try, TW, TH, Body, NoteS);
			if (TW > Inner && !Line.IsEmpty())
			{
				NoteLines.Add(Line);
				Line = Word;
			}
			else
			{
				Line = Try;
			}
		}
		if (!Line.IsEmpty()) NoteLines.Add(Line);
	}
	float KW = 0.f, KH = 0.f, TW = 0.f, TH = 0.f, NW = 0.f, NH = 0.f, SW = 0.f, SH = 0.f, IW = 0.f, IH = 0.f;
	GetTextSize(TEXT("Ag"), KW, KH, Body, KickerS);
	GetTextSize(M.Title.IsEmpty() ? FString(TEXT("Ag")) : M.Title, TW, TH, Big, TitleS);
	GetTextSize(TEXT("Ag"), NW, NH, Body, NoteS);
	GetTextSize(TEXT("Ag"), SW, SH, Body, StatS);
	GetTextSize(TEXT("Ag"), IW, IH, Body, ItemS);
	// One line under the items says how the card is worked (launch pre-flight 2026-11-24: nothing on the cards named
	// a key, and a click did nothing): for the device in use.
	const AMIPlayerController* Controller = Cast<AMIPlayerController>(GetOwningPlayerController());
	const bool bPad = Controller && Controller->IsPadActive();
	FString Hint = bPad ? TEXT("D-pad choose  ·  A select") : TEXT("Up/Down choose  ·  Enter select");
	if (M.Items.ContainsByPredicate([](const FMIMenuItem& I) { return I.bAdjust; }))
	{
		Hint += TEXT("  ·  Left/Right change");
	}
	if (!bPad)
	{
		Hint += TEXT("  ·  or click");
	}
	float HintS = static_cast<float>(K * 0.8), HW = 0.f, HH = 0.f;
	GetTextSize(Hint, HW, HH, Body, HintS);
	if (HW > Inner)
	{
		HintS *= static_cast<float>(Inner / HW);
		GetTextSize(Hint, HW, HH, Body, HintS);
	}
	const double HintGap = 12.0 * K;
	double CardH = Pad;
	if (!M.Kicker.IsEmpty()) CardH += KH + 10.0 * K;
	CardH += TH + 14.0 * K;  // the title and the gold rule under it
	if (NoteLines.Num() > 0) CardH += NoteLines.Num() * (NH + 2.0 * K) + 12.0 * K;
	if (M.Stats.Num() > 0) CardH += M.Stats.Num() * (SH + 10.0 * K) + 8.0 * K;
	CardH += 12.0 * K + M.Items.Num() * (RowH + RowGap) + Pad - RowGap;
	if (M.Items.Num() > 0) CardH += HintGap + HH;
	const double CX = (W - CardW) * 0.5;
	const double CY = FMath::Max(24.0 * K, (H - CardH) * (bTitle ? 0.62 : 0.5));
	DrawPlate(CX, CY, CardW, CardH, WithAlpha(Plate(), 0.9f), WithAlpha(PlateEdge(), 1.f), static_cast<float>(FMath::Max(1.0, K)));
	DrawRect(Gold(), CX, CY, CardW, 4.0 * K);  // the gold top edge, as on the set-up plates

	const double X0 = CX + Pad;
	double Y = CY + Pad;
	if (!M.Kicker.IsEmpty())
	{
		DrawText(M.Kicker.ToUpper(), Gold(), X0, Y, Body, KickerS);
		Y += KH + 10.0 * K;
	}
	DrawText(bTitle ? M.Title : M.Title.ToUpper(), Ink(), X0, Y, Big, TitleS);
	Y += TH + 4.0 * K;
	DrawRect(Gold(), X0, Y, 56.0 * K, 3.0 * K);
	Y += 10.0 * K;
	for (const FString& L : NoteLines)
	{
		DrawText(L, InkDim(), X0, Y, Body, NoteS);
		Y += NH + 2.0 * K;
	}
	if (NoteLines.Num() > 0) Y += 12.0 * K;
	for (const TPair<FString, FString>& Stat : M.Stats)
	{
		// Key left in the dim ink, value right in the ink, a hairline under each row.
		float VW = 0.f, VH = 0.f;
		GetTextSize(Stat.Value, VW, VH, Body, StatS);
		DrawText(Stat.Key.ToUpper(), InkDim(), X0, Y, Body, StatS);
		DrawText(Stat.Value, Ink(), X0 + Inner - VW, Y, Body, StatS);
		DrawRect(WithAlpha(PlateEdge(), 0.9f), X0, Y + SH + 4.0 * K, Inner, FMath::Max(1.0, K));
		Y += SH + 10.0 * K;
	}
	if (M.Stats.Num() > 0) Y += 8.0 * K;
	Y += 12.0 * K;
	// Where the rows are, for the mouse: a click acts on the row under it (AMIPlayerController, IA_MenuClick), and the
	// cursor selects the row it moves over. A cursor that rests where a card opens selects nothing: Enter still takes
	// the card's first item.
	{
		FMIMenuLayout& L = Game.GetMenu().Layout;
		L.Screen = M.Screen;
		L.X = X0;
		L.Width = Inner;
		L.Top = Y;
		L.RowHeight = RowH;
		L.RowGap = RowGap;
		L.Adjust.Reset(M.Items.Num());
		for (const FMIMenuItem& Item : M.Items)
		{
			L.Adjust.Add(Item.bAdjust);
		}
		float MX = 0.f, MY = 0.f;
		const APlayerController* PC = GetOwningPlayerController();
		if (PC && PC->ShouldShowMouseCursor() && PC->GetMousePosition(MX, MY))
		{
			const FVector2D Cursor(MX, MY);
			if (HoverScreen != M.Screen)
			{
				HoverScreen = M.Screen;
				HoverCursor = Cursor;
			}
			else if (!Cursor.Equals(HoverCursor, 0.5))
			{
				HoverCursor = Cursor;
				Game.MenuHover(Cursor);
			}
		}
	}
	for (int32 I = 0; I < M.Items.Num(); ++I)
	{
		const FMIMenuItem& Item = M.Items[I];
		const bool bSel = I == M.Selected;
		// The selected item is the gold button with dark text; the others sit on a faint plate with a hairline edge.
		if (bSel)
		{
			DrawRect(Gold(), X0, Y, Inner, RowH);
		}
		else
		{
			DrawPlate(X0, Y, Inner, RowH, WithAlpha(Bg(), 0.55f), WithAlpha(PlateEdge(), 1.f), static_cast<float>(FMath::Max(1.0, K)));
		}
		const FLinearColor TextC = bSel ? Bg() : Ink();
		const double TY = Y + (RowH - IH) * 0.5;
		DrawText(Item.Label.ToUpper(), TextC, X0 + 18.0 * K, TY, Body, ItemS);
		if (!Item.Value.IsEmpty())
		{
			const FString V = Item.bAdjust ? TEXT("<  ") + Item.Value + TEXT("  >") : Item.Value;
			float VW = 0.f, VH = 0.f;
			GetTextSize(V, VW, VH, Body, ItemS);
			DrawText(V, bSel ? Bg() : Gold(), X0 + Inner - 18.0 * K - VW, TY, Body, ItemS);
		}
		Y += RowH + RowGap;
	}
	if (M.Items.Num() > 0)
	{
		DrawText(Hint, InkDim(), X0 + (Inner - HW) * 0.5, Y - RowGap + HintGap, Body, HintS);
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
