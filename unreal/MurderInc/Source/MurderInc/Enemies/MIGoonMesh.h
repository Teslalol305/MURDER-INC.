#pragma once

#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "MIGoonMesh.generated.h"

/**
 * The Goon's body mesh: after the animation blueprint's pose (the template rifle set) the left hand is pulled onto
 * the SMG's support-hand point by two-bone IK in component space, every child of the arm following, so the support
 * hand holds the gun instead of hanging open beside it (review 2026-11-23). Presentation only.
 */
UCLASS(ClassGroup = (MurderInc))
class MURDERINC_API UMIGoonMeshComponent : public USkeletalMeshComponent
{
	GENERATED_BODY()

public:
	/** The support point in the bone's space of HandBone (the SMG's SupportHand socket through the weapon offset). */
	void SetSupportGrip(FName InHandBone, const FTransform& InGripInHand) { HandBone = InHandBone; GripInHand = InGripInHand; bHaveGrip = true; }
	void SetSupportWeight(float W) { SupportWeight = FMath::Clamp(W, 0.f, 1.f); }
	float GetSupportWeight() const { return SupportWeight; }

	/** Where the left palm landed last frame, component space (tests and pictures). */
	FVector GetLastPalm() const { return LastPalm; }
	FVector GetLastGrip() const { return LastGrip; }

protected:
	virtual void FinalizeBoneTransform() override;

private:
	FName HandBone = TEXT("hand_r");
	FTransform GripInHand = FTransform::Identity;
	bool bHaveGrip = false;
	float SupportWeight = 0.f;
	FVector LastPalm = FVector::ZeroVector;
	FVector LastGrip = FVector::ZeroVector;
};
