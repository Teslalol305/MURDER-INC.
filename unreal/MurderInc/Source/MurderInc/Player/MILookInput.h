#pragma once

#include "CoreMinimal.h"
#include "Core/Data/MIData.h"

/**
 * Look input shaped before it reaches the rules, without the engine so the tests can drive it (src/input.js is the
 * reference; spec 01 3.16 and 3.17):
 *  - the gamepad's sticks: the axial dead zone, the right stick's response curve and its turn boost at the rim;
 *  - the mouse through a Pixel Streaming data channel: counts back to the browser's pixels, and the web game's
 *    pointer-lock spike filter.
 */
namespace MILook
{
	/** Axial dead zone (src/input.js deadzone): nothing inside it, the rest rescaled to 0..1. */
	MURDERINC_API double Deadzone(double Value, double Zone);
	inline FVector2D Deadzone(const FVector2D& Stick, double Zone) { return FVector2D(Deadzone(Stick.X, Zone), Deadzone(Stick.Y, Zone)); }
}

/** The right stick (src/input.js padLook, pollPad and update). */
struct MURDERINC_API FMIPadLook
{
	FMIPadLookData Config;

	/**
	 * One frame. Stick is the raw right stick with X right and Y up (the controller puts the Y the game viewport
	 * inverts back first). Returns the degrees to add to the look (X > 0 turns right, Y > 0 looks down): the share of
	 * the full rate after the dead zone, the curve and the boost, times yaw rate x Sensitivity x AimSlow x Dt; the
	 * pitch also times pitchScale and the invert setting.
	 */
	FVector2D Step(const FVector2D& Stick, double Dt, double Sensitivity, double AimSlow, bool bInvertY);
	/** The device changed or the pad went away: the boost starts over. */
	void Reset() { BoostValue = 0.0; }
	double GetBoost() const { return BoostValue; }

private:
	double BoostValue = 0.0;
};

/**
 * Mouse counts that came through Pixel Streaming 2 (Unreal 5.9), turned back into the browser's pixels, which is the
 * unit of player.input.mouse (0.0021 rad per pixel).
 *
 * What happens on the way (read in the engine source and in Epic's reference player, 2026-11-24):
 *  - the browser sends each mouse event's movement as a 16-bit integer, trunc(movement / (player width / 2) x 32767)
 *    (Frontend/library/src/Util/InputCoordTranslator.ts translateSigned, Inputs/MouseControllerLocked.ts, written
 *    with DataView.setInt16, which cuts the fraction and wraps beyond half the player's width);
 *  - the engine turns it into counts with (int32)(value / 32767 x viewport width)
 *    (PixelStreaming2RTC RTCInputHandler.cpp HandleOnMouseMove, PixelStreaming2Input InputHandler.cpp
 *    ConvertFromNormalizedScreenLocation) and hands them to Slate as a raw mouse move.
 * So with the picture rendered at the size the player shows it, one browser pixel is 2 counts, and both cuts are
 * toward zero: every event loses one count on each axis that moved (1 pixel arrives as 1 count, 10 pixels as 19).
 * Slow, precise movement would be half speed and fast movement nearly full speed: Truncation puts the count back.
 */
struct MURDERINC_API FMIStreamMouse
{
	/** Browser pixels per count: 0.5 when the game renders at the player's size, player width / (2 x render width) in general. */
	double Scale = 1.0;
	/** Counts each moved axis of one event lost on the way (1 for the pipeline above; 0 leaves the counts as they are). */
	double Truncation = 0.0;
	/** Browser pixels: one event beyond this on either axis is a pointer-lock spike (src/input.js onMouseMove). 0: no filter. */
	double Glitch = 0.0;

	/** One mouse event (any axis convention: each axis is treated alone). False: a spike, to be dropped whole. */
	bool Event(const FVector2D& Counts, FVector2D& OutPixels) const;
};
