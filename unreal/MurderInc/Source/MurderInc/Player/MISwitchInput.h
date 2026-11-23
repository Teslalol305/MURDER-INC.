#pragma once

#include "CoreMinimal.h"

/**
 * The input layer of four-gun switching (docs/unreal/LOADOUT.md 4.2, 4.6), without the engine: AMIPlayerController
 * feeds it key presses and releases with their times, the tests feed it synthetic ones. With fewer than
 * wheel.minGuns guns Q / Y swap on press exactly as the web game; with more, a tap swaps on release and a hold of
 * wheel.hold opens the weapon wheel (no swap starts until the player has chosen). View on a pad: a tap is the fire
 * selector, a hold of inspectHold inspects. The mouse wheel steps next / previous at most once per wheelDebounce.
 */
struct FMISwitchConfig
{
	int32 WheelMinGuns = 3;
	double WheelHold = 0.25;
	double InspectHold = 0.4;
	double WheelDebounce = 0.28;
	double Deadzone = 0.5;      // share of MouseRadius or of the stick
	double MouseRadius = 60.0;  // px of mouse travel since the wheel opened
};

/** What one frame of input asks of the rules (the edges are consumed). */
struct FMISwitchFrame
{
	bool bSwap = false;
	bool bNext = false;
	bool bPrevious = false;
	int32 WheelPick = INDEX_NONE;
	bool bFireMode = false;
	bool bInspect = false;
};

class MURDERINC_API FMISwitchInput
{
public:
	FMISwitchConfig Config;

	void SetGuns(int32 InGuns) { Guns = InGuns; if (!UsesWheel()) CloseWheel(); }
	int32 GetGuns() const { return Guns; }
	bool UsesWheel() const { return Guns >= Config.WheelMinGuns; }

	void SwapDown(double Now);
	void SwapUp(double Now);
	/** Mouse wheel: +1 next (wheel down), -1 previous (wheel up), debounced. */
	void WheelStep(int32 Direction, double Now);
	/** D-pad up (next) / down (previous): one step per press. */
	void PadStep(int32 Direction);
	void FireModeKey() { Pending.bFireMode = true; }
	void InspectKey() { Pending.bInspect = true; }
	void ViewDown(double Now);
	void ViewUp(double Now);
	/** Mouse travel (px, X right, Y up) and the right stick (-1..1) while the wheel is open. */
	void MouseMove(const FVector2D& Delta) { if (bWheelOpen) Travel += Delta; }
	void Stick(const FVector2D& Value) { if (bWheelOpen) StickValue = Value; }
	/** Opens the wheel or starts the inspect once a hold is long enough. */
	void Tick(double Now);
	FMISwitchFrame Consume();
	void Reset();

	bool IsWheelOpen() const { return bWheelOpen; }
	/** The sector under the mouse or stick (slot 1 at the top, clockwise), or INDEX_NONE inside the dead zone. */
	int32 GetSelection() const;
	/** Look and fire are blocked while the wheel is open. */
	bool BlocksLook() const { return bWheelOpen; }

private:
	void CloseWheel() { bWheelOpen = false; Travel = StickValue = FVector2D::ZeroVector; }

	int32 Guns = 2;
	FMISwitchFrame Pending;
	bool bSwapHeld = false;
	double SwapAt = 0.0;
	bool bWheelOpen = false;
	FVector2D Travel = FVector2D::ZeroVector;
	FVector2D StickValue = FVector2D::ZeroVector;
	double LastWheel = -1e9;
	bool bViewHeld = false;
	bool bViewInspected = false;
	double ViewAt = 0.0;
};
