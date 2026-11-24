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
	// The stick here is +Y up; the browser's, and the look, are +Y down.
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

FString MILook::PadName(const FString& Name, bool bPlayStation)
{
	if (!bPlayStation)
	{
		return Name;
	}
	static const TCHAR* const Names[][2] = {
		{TEXT("A"), TEXT("Cross")}, {TEXT("B"), TEXT("Circle")}, {TEXT("X"), TEXT("Square")}, {TEXT("Y"), TEXT("Triangle")},
		{TEXT("LB"), TEXT("L1")}, {TEXT("RB"), TEXT("R1")}, {TEXT("LT"), TEXT("L2")}, {TEXT("RT"), TEXT("R2")},
		{TEXT("START"), TEXT("OPTIONS")}, {TEXT("Start"), TEXT("Options")}, {TEXT("VIEW"), TEXT("CREATE")}, {TEXT("View"), TEXT("Create")},
	};
	FString Out;
	Out.Reserve(Name.Len() + 8);
	int32 I = 0;
	while (I < Name.Len())
	{
		if (!FChar::IsAlnum(Name[I]))
		{
			Out.AppendChar(Name[I++]);
			continue;
		}
		int32 End = I;
		while (End < Name.Len() && FChar::IsAlnum(Name[End]))
		{
			++End;
		}
		const FString Word = Name.Mid(I, End - I);
		const TCHAR* Replacement = nullptr;
		for (const auto& Pair : Names)
		{
			if (Word.Equals(Pair[0], ESearchCase::CaseSensitive))
			{
				Replacement = Pair[1];
				break;
			}
		}
		Out += Replacement ? FString(Replacement) : Word;
		I = End;
	}
	return Out;
}

FIntPoint FMIPadNav::Step(const FVector2D& Stick, double Dt)
{
	const double Zone = Config.NavStick > 0.0 ? Config.NavStick : 0.6;
	const auto Direction = [Zone](double V) { return FMath::IsFinite(V) ? (V > Zone ? 1 : 0) - (V < -Zone ? 1 : 0) : 0; };
	const int32 X = Direction(Stick.X);
	const int32 Y = -Direction(Stick.Y);  // the stick is +Y up, rows count downwards
	FIntPoint Out(0, 0);
	if (Y != HeldY)
	{
		HeldY = Y;
		Timer = Config.NavFirst;
		Out.Y = Y;
	}
	else if (Y != 0 && Config.NavRepeat > 0.0)
	{
		Timer -= FMath::Max(0.0, Dt);
		if (Timer <= 0.0)
		{
			Timer += Config.NavRepeat;
			Out.Y = Y;
		}
	}
	if (X != HeldX)
	{
		HeldX = X;
		Out.X = X;  // left and right adjust once per push
	}
	return Out;
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
