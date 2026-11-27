#include "Player/MIAimAssist.h"

#include "Core/MIMath.h"

namespace
{
	int32 Nearest(const TArray<FVector2D>& Errors, double Within)
	{
		int32 Best = INDEX_NONE;
		double BestLen = Within;
		for (int32 I = 0; I < Errors.Num(); ++I)
		{
			const double L = Errors[I].Size();
			if (L <= BestLen)
			{
				BestLen = L;
				Best = I;
			}
		}
		return Best;
	}
}

double FMIAimAssist::Reach(bool bPad, double Strength) const
{
	const FMIAssistSideData& S = SideOf(bPad);
	// The snap tracks its target a little beyond where it began, so the controller keeps that one in view too.
	return FMath::Max3(S.SlowRadius, S.MagCone, S.SnapAngle * 1.5) * FMath::Max(Strength, 0.0);
}

double FMIAimAssist::SlowAt(bool bPad, double Strength) const
{
	const double Depth = (1.0 - SideOf(bPad).Slow) * FMath::Max(Strength, 0.0);
	return FMath::Clamp(1.0 - Depth, FMath::Min(Data.MinSlow, 1.0), 1.0);
}

void FMIAimAssist::Reset()
{
	SlowValue = 1.0;
	bWasAds = false;
	bSnapping = false;
	SnapLeft = 0.0;
}

FMIAssistResult FMIAimAssist::Step(const FMIAssistFrame& F, const TArray<FVector2D>& Errors)
{
	FMIAssistResult Out;
	if (!F.bOn || F.Dt <= 0.0)
	{
		Reset();
		return Out;
	}
	const FMIAssistSideData& S = SideOf(F.bPad);
	const double K = FMath::Max(F.Strength, 0.0);

	// 1. Slow-down: eased in and out so the view never jerks.
	const bool bOver = Nearest(Errors, S.SlowRadius * K) != INDEX_NONE;
	SlowValue = MI::Damp(SlowValue, bOver ? SlowAt(F.bPad, K) : 1.0, Data.SlowRate, F.Dt);
	Out.Slow = SlowValue;

	// 3. ADS snap: begins on the press, over the target nearest the crosshair inside the angle.
	if (F.bAds && !bWasAds)
	{
		if (Nearest(Errors, S.SnapAngle * K) != INDEX_NONE)
		{
			bSnapping = true;
			SnapLeft = S.SnapTime;
		}
	}
	bWasAds = F.bAds;
	if (!F.bAds)
	{
		bSnapping = false;
	}
	if (bSnapping)
	{
		// Follows its target a little beyond the angle it began in (the crosshair or the target may move meanwhile).
		const int32 I = Nearest(Errors, S.SnapAngle * K * 1.5);
		if (I == INDEX_NONE)
		{
			bSnapping = false;
		}
		else
		{
			const double Share = SnapLeft <= F.Dt ? 1.0 : F.Dt / SnapLeft;
			Out.Turn = Errors[I] * Share;
			SnapLeft -= F.Dt;
			Out.bSnapping = true;
			if (SnapLeft <= 0.0)
			{
				bSnapping = false;
			}
			return Out;
		}
	}

	// 2. Magnetism while firing: toward the nearest target inside the cone, capped, and never against the player's turn.
	if (F.bFire)
	{
		const int32 I = Nearest(Errors, S.MagCone * K);
		if (I != INDEX_NONE)
		{
			const FVector2D& E = Errors[I];
			const double Len = E.Size();
			if (Len > UE_KINDA_SMALL_NUMBER)
			{
				const FVector2D Dir = E / Len;
				const double Fade = Data.MagFalloff > 0.0 ? FMath::Min(1.0, Len / Data.MagFalloff) : 1.0;
				double Step = FMath::Min(Len, S.MagRate * K * F.Dt * Fade);
				const double TurnLen = F.PlayerTurn.Size();
				if (TurnLen > UE_KINDA_SMALL_NUMBER)
				{
					const double Cos = FVector2D::DotProduct(F.PlayerTurn, Dir) / TurnLen;
					if (Cos < 0.0)
					{
						Step *= FMath::Clamp(1.0 + 2.0 * Cos, 0.0, 1.0);  // fully gone once the player turns 120 degrees away from it
					}
				}
				Out.Turn = Dir * Step;
			}
		}
	}
	return Out;
}
