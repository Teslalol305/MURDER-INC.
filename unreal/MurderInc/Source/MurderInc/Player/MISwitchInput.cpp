#include "Player/MISwitchInput.h"

void FMISwitchInput::Reset()
{
	Pending = FMISwitchFrame();
	bSwapHeld = false;
	bViewHeld = bViewInspected = false;
	CloseWheel();
}

void FMISwitchInput::SwapDown(double Now)
{
	if (!UsesWheel())
	{
		Pending.bSwap = true;  // the web game: on press, whether it is held or not
		return;
	}
	bSwapHeld = true;
	SwapAt = Now;
}

void FMISwitchInput::SwapUp(double Now)
{
	if (!UsesWheel() || !bSwapHeld)
	{
		return;
	}
	bSwapHeld = false;
	if (bWheelOpen)
	{
		Pending.WheelPick = GetSelection();  // the dead zone picks nothing
		CloseWheel();
	}
	else if (Now - SwapAt < Config.WheelHold)
	{
		Pending.bSwap = true;  // a tap: the quick swap, on release
	}
}

void FMISwitchInput::WheelStep(int32 Direction, double Now)
{
	if (Direction == 0 || Now - LastWheel < Config.WheelDebounce)
	{
		return;
	}
	LastWheel = Now;
	(Direction > 0 ? Pending.bNext : Pending.bPrevious) = true;
}

void FMISwitchInput::PadStep(int32 Direction)
{
	if (Direction != 0)
	{
		(Direction > 0 ? Pending.bNext : Pending.bPrevious) = true;
	}
}

void FMISwitchInput::ViewDown(double Now)
{
	bViewHeld = true;
	bViewInspected = false;
	ViewAt = Now;
}

void FMISwitchInput::ViewUp(double Now)
{
	if (bViewHeld && !bViewInspected)
	{
		Pending.bFireMode = true;  // a tap of View is the selector
	}
	bViewHeld = false;
}

void FMISwitchInput::Tick(double Now)
{
	if (bSwapHeld && !bWheelOpen && UsesWheel() && Now - SwapAt >= Config.WheelHold)
	{
		bWheelOpen = true;
		Travel = StickValue = FVector2D::ZeroVector;
	}
	if (bViewHeld && !bViewInspected && Now - ViewAt >= Config.InspectHold)
	{
		bViewInspected = true;
		Pending.bInspect = true;
	}
}

FMISwitchFrame FMISwitchInput::Consume()
{
	const FMISwitchFrame Out = Pending;
	Pending = FMISwitchFrame();
	return Out;
}

int32 FMISwitchInput::GetSelection() const
{
	if (!bWheelOpen || Guns <= 0)
	{
		return INDEX_NONE;
	}
	// The stick wins when it is pushed; otherwise the mouse travel as a share of its radius.
	FVector2D V = StickValue.Size() >= Config.Deadzone ? StickValue : Travel / FMath::Max(1.0, Config.MouseRadius);
	if (V.Size() < Config.Deadzone)
	{
		return INDEX_NONE;
	}
	// Slot 1 at the top, clockwise: the angle from straight up toward the right.
	double Angle = FMath::RadiansToDegrees(FMath::Atan2(V.X, V.Y));
	if (Angle < 0.0)
	{
		Angle += 360.0;
	}
	const double Sector = 360.0 / Guns;
	return FMath::FloorToInt32(FMath::Fmod(Angle + Sector * 0.5, 360.0) / Sector) % Guns;
}
