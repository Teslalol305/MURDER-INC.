#include "Player/MILookInput.h"

double MILook::Deadzone(double Value, double Zone)
{
	const double V = FMath::IsFinite(Value) ? Value : 0.0;
	const double M = FMath::Abs(V);
	if (M <= Zone || Zone >= 1.0)
	{
		return 0.0;
	}
	return FMath::Sign(V) * FMath::Min(1.0, (M - Zone) / (1.0 - Zone));
}

FVector2D FMIPadLook::Step(const FVector2D& Stick, double Dt, double Sensitivity, double AimSlow, bool bInvertY)
{
	const FMIPadLookData& P = Config;
	if (!(Dt > 0.0))
	{
		Dt = 0.0;
	}
	// Unreal's stick is +Y up; the browser's, and the look, are +Y down.
	const double X = MILook::Deadzone(Stick.X, P.Deadzone);
	const double Y = MILook::Deadzone(-Stick.Y, P.Deadzone);
	const double Length = FMath::Sqrt(X * X + Y * Y);
	const double M = FMath::Min(1.0, Length);
	FVector2D Share = FVector2D::ZeroVector;
	if (M > 0.0)
	{
		// The curve acts on the magnitude, so a diagonal push behaves like a straight one; a square gate reaches 1.41
		// in the corners and is capped at the full rate.
		const double K = (P.CurveLinear * M + P.CurveCubic * M * M * M) / M;
		const double Over = FMath::Max(1.0, Length);
		Share = FVector2D(X / Over * K, Y / Over * K);
	}
	// The boost builds while the stick is held at the rim.
	if (M > P.BoostFrom)
	{
		BoostValue = P.BoostTime > 0.0 ? FMath::Min(1.0, BoostValue + Dt / P.BoostTime) : 1.0;
	}
	else
	{
		BoostValue = P.BoostDecay > 0.0 ? FMath::Max(0.0, BoostValue - Dt / P.BoostDecay) : 0.0;
	}
	const double Fast = 1.0 + (P.Boost - 1.0) * BoostValue;
	const double Rate = P.YawRate * Sensitivity * AimSlow * Dt;
	return FVector2D(Share.X * Fast * Rate, Share.Y * Fast * Rate * P.PitchScale * (bInvertY ? -1.0 : 1.0));
}

bool FMIStreamMouse::Event(const FVector2D& Counts, FVector2D& OutPixels) const
{
	const auto Axis = [this](double C)
	{
		return C == 0.0 || !FMath::IsFinite(C) ? 0.0 : (C + FMath::Sign(C) * Truncation) * Scale;
	};
	OutPixels = FVector2D(Axis(Counts.X), Axis(Counts.Y));
	return !(Glitch > 0.0 && (FMath::Abs(OutPixels.X) > Glitch || FMath::Abs(OutPixels.Y) > Glitch));
}
