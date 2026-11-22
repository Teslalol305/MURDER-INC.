#include "Player/MICharacterMovement.h"

void UMICharacterMovement::CalcVelocity(float DeltaTime, float Friction, bool bFluid, float BrakingDeceleration)
{
	if (!bRuleDriven)
	{
		Super::CalcVelocity(DeltaTime, Friction, bFluid, BrakingDeceleration);
		return;
	}
	Velocity.X = RuleVelocity.X;
	Velocity.Y = RuleVelocity.Y;
}

float UMICharacterMovement::GetMaxSpeed() const
{
	// Nothing may clamp the rules' velocity (the stock walking code scales a velocity above the maximum back).
	return bRuleDriven ? FMath::Max(Super::GetMaxSpeed(), static_cast<float>(RuleVelocity.Size2D()) + 1.f) : Super::GetMaxSpeed();
}
