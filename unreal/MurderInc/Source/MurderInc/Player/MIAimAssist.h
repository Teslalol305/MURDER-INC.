#pragma once

#include "CoreMinimal.h"
#include "Core/Data/MIData.h"

/**
 * Aim assist (docs/unreal/DECISIONS.md 2026-11-27 ~22:20: "lock onto the targets as they shoot"), without the engine so
 * the tests can drive it. It changes how the aim feels, never the rules: the controller gathers the live, visible Goons
 * (a line of sight to the aim point, so nothing is helped through a wall or cover) as angular errors from the crosshair,
 * and this turns them into three things, all tuned by config.json player.input.assist:
 *  1. slow-down: the look rate is scaled down (pad 0.45, mouse 0.8) while the crosshair is within a small radius of a target;
 *  2. magnetism while firing: a gentle turn toward the nearest target inside a cone, capped per second, and faded out when
 *     the player's own turn is against it (the player's input direction always wins);
 *  3. ADS snap: on starting to aim down sights, a turn over about 0.12 s onto the nearest target inside a wider angle.
 * Errors are (yaw to the right, pitch up) in degrees from the crosshair to the aim point (the chest). The strength setting
 * scales every reach and depth (Low, Normal, High).
 */
struct FMIAssistFrame
{
	bool bOn = false;                           // the setting; off: nothing happens and the state is cleared
	bool bPad = false;                          // the gamepad is the device in use (else the mouse)
	double Strength = 1.0;                      // FMIAimAssistData::ScaleOf the setting
	bool bFire = false;                         // the fire button is held
	bool bAds = false;                          // aiming down sights
	FVector2D PlayerTurn = FVector2D::ZeroVector;  // the player's own turn this frame, degrees: X right, Y up
	double Dt = 0.0;
};

struct FMIAssistResult
{
	double Slow = 1.0;                          // multiply the look rate by this (1: none)
	FVector2D Turn = FVector2D::ZeroVector;     // degrees to add to the view: X right, Y up
	bool bSnapping = false;
};

struct MURDERINC_API FMIAimAssist
{
	FMIAimAssistData Data;

	/** The widest angle (degrees) at which any of the three parts looks at a target: the controller tests no one beyond it. */
	double Reach(bool bPad, double Strength) const;
	/** The slow-down factor a strength gives a device (never below Data.MinSlow). */
	double SlowAt(bool bPad, double Strength) const;

	/** One frame. Errors: every live, visible target as (yaw right, pitch up) degrees from the crosshair to its aim point. */
	FMIAssistResult Step(const FMIAssistFrame& Frame, const TArray<FVector2D>& Errors);
	/** Back to rest (the setting went off, play stopped, the player died). */
	void Reset();

	double GetSlow() const { return SlowValue; }
	bool IsSnapping() const { return bSnapping; }

private:
	const FMIAssistSideData& SideOf(bool bPad) const { return bPad ? Data.Pad : Data.Mouse; }

	double SlowValue = 1.0;
	bool bWasAds = false;
	bool bSnapping = false;
	double SnapLeft = 0.0;
};
