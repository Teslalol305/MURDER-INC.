#pragma once

#include "CoreMinimal.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "MICharacterMovement.generated.h"

/**
 * The stock walking and falling moves (collision, steps, floor, gravity) with the web game's velocity rule: the
 * horizontal velocity is not computed here from acceleration and friction but handed in every frame by
 * FMIPlayerRules (a straight move toward the wish velocity at constant rates, spec 01 3.5).
 */
UCLASS()
class MURDERINC_API UMICharacterMovement : public UCharacterMovementComponent
{
	GENERATED_BODY()

public:
	/** When true, CalcVelocity takes the horizontal velocity from RuleVelocity. */
	bool bRuleDriven = false;
	FVector RuleVelocity = FVector::ZeroVector;

	virtual void CalcVelocity(float DeltaTime, float Friction, bool bFluid, float BrakingDeceleration) override;
	virtual float GetMaxSpeed() const override;
};
