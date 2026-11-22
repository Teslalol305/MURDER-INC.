#include "UI/MIHUD.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Player/MIPlayerCharacter.h"
#include "Weapons/MIWeaponComponent.h"

void AMIHUD::DrawHUD()
{
	Super::DrawHUD();
	const AMIPlayerCharacter* Player = Cast<AMIPlayerCharacter>(GetOwningPawn());
	if (!Canvas || !Player || !Player->GetWeapon() || !Player->GetWeapon()->IsReady())
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
	const FLinearColor White(1.f, 1.f, 1.f, 0.9f);

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

	UFont* Font = GEngine ? GEngine->GetLargeFont() : nullptr;
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
		DrawText(Cue.ToString().ToUpper(), FLinearColor(1.f, 0.8f, 0.3f, 1.f), W - TW - W * 0.03, H - 2.2 * TH - H * 0.04, Font, 1.2f);
	}
	const FString Health = FString::Printf(TEXT("HEALTH %d"), FMath::CeilToInt32(Rules.Health));
	DrawText(Health, Rules.Health < Rules.MaxHealth * 0.3 ? FLinearColor(1.f, 0.3f, 0.25f, 1.f) : White, W * 0.03, H - TH - H * 0.04, Font, 1.5f);
	if (Rules.Hurt > 0.0)
	{
		DrawRect(FLinearColor(0.6f, 0.f, 0.f, static_cast<float>(0.25 * Rules.Hurt)), 0.f, 0.f, W, H);
	}
}
