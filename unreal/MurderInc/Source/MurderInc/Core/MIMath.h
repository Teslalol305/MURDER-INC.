#pragma once

#include "CoreMinimal.h"

/**
 * The web game's small math helpers (src/core/util.js, src/weapon/springs.js), in double precision so that the
 * golden vectors of tools/ue-export/golden.mjs are met to about 1e-9.
 */
namespace MI
{
	inline double Clamp01(double X) { return X < 0.0 ? 0.0 : (X > 1.0 ? 1.0 : X); }
	inline double Lerp(double A, double B, double T) { return A + (B - A) * T; }

	/** Frame-rate independent exponential approach: target + (x - target) * e^(-rate * dt). */
	inline double Damp(double Current, double Target, double Rate, double Dt)
	{
		return Target + (Current - Target) * FMath::Exp(-Rate * Dt);
	}

	/** x * e^(-rate * dt). */
	inline double ExpDecay(double Value, double Rate, double Dt) { return Value * FMath::Exp(-Rate * Dt); }

	/** Linear approach that never overshoots. */
	inline double MoveToward(double Current, double Target, double MaxDelta)
	{
		const double D = Target - Current;
		if (FMath::Abs(D) <= MaxDelta)
		{
			return Target;
		}
		return Current + FMath::Sign(D) * MaxDelta;
	}

	/** Cubic step 3t^2 - 2t^3 of x between e0 and e1, clamped. */
	inline double SmoothStep(double E0, double E1, double X)
	{
		const double T = Clamp01(E0 == E1 ? 0.0 : (X - E0) / (E1 - E0));
		return T * T * (3.0 - 2.0 * T);
	}

	/** Quintic step t^3 (6t^2 - 15t + 10) of x between e0 and e1, clamped. */
	inline double SmootherStep(double E0, double E1, double X)
	{
		const double T = Clamp01(E0 == E1 ? 0.0 : (X - E0) / (E1 - E0));
		return T * T * T * (T * (T * 6.0 - 15.0) + 10.0);
	}

	/** Wraps degrees to (-180, 180]. */
	inline double WrapDegrees(double A)
	{
		A = FMath::Fmod(A + 180.0, 360.0);
		if (A <= 0.0)
		{
			A += 360.0;
		}
		return A - 180.0;
	}

	inline double DegToRad(double D) { return D * (UE_DOUBLE_PI / 180.0); }
	inline double RadToDeg(double R) { return R * (180.0 / UE_DOUBLE_PI); }
}

/**
 * Second-order spring stepped with the exact solution of x'' = -w^2 (x - target) - 2 z w x' (src/weapon/springs.js):
 * the motion does not depend on the frame rate.
 */
struct FMIExactSpring
{
	double X = 0.0;
	double V = 0.0;

	void Reset(double At = 0.0)
	{
		X = At;
		V = 0.0;
	}

	double Step(double Target, double W, double Z, double Dt)
	{
		if (!(Dt > 0.0))
		{
			return X;
		}
		const double Y0 = X - Target;
		const double V0 = V;
		if (Z >= 0.999)
		{
			const double E = FMath::Exp(-W * Dt);
			const double K = V0 + W * Y0;
			X = Target + E * (Y0 + K * Dt);
			V = E * (V0 - W * K * Dt);
		}
		else
		{
			const double Wd = W * FMath::Sqrt(1.0 - Z * Z);
			const double E = FMath::Exp(-Z * W * Dt);
			const double C = FMath::Cos(Wd * Dt);
			const double S = FMath::Sin(Wd * Dt);
			const double B = (V0 + Z * W * Y0) / Wd;
			const double Y = E * (Y0 * C + B * S);
			X = Target + Y;
			V = -Z * W * Y + E * Wd * (B * C - Y0 * S);
		}
		return X;
	}
};

/** Seeded random numbers: the web game's mulberry32 with FNV-1a labelled forks (src/core/rng.js), bit for bit. */
struct FMIRng
{
	uint32 State = 1994;
	uint32 Seed = 1994;

	FMIRng() = default;
	explicit FMIRng(uint32 InSeed) : State(InSeed), Seed(InSeed) {}

	/** Uniform in [0, 1). */
	double Next()
	{
		State = State + 0x6d2b79f5u;
		uint32 T = (State ^ (State >> 15)) * (1u | State);
		T = (T + ((T ^ (T >> 7)) * (61u | T))) ^ T;
		return static_cast<double>(T ^ (T >> 14)) / 4294967296.0;
	}

	double Range(double A, double B) { return A + (B - A) * Next(); }

	static uint32 HashString(const FString& Text)
	{
		uint32 H = 0x811c9dc5u;
		for (const TCHAR Char : Text)
		{
			H ^= static_cast<uint32>(Char);
			H *= 0x01000193u;
		}
		return H;
	}

	/** A child stream that depends only on the root seed and the label (rng.fork('weapon')). */
	FMIRng Fork(const FString& Label) const
	{
		return FMIRng(HashString(FString::Printf(TEXT("%u:%s"), Seed, *Label)));
	}
};
