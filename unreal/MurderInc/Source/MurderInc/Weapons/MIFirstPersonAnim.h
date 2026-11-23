#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "MIFirstPersonAnim.generated.h"

class UAnimSequenceBase;

/**
 * One clip in the first-person pose: sampled at Time and blended over what the layers before it built (Weight), or,
 * when additive, its motion relative to the same clip at RefTime added on top (the pack's fire clips, whose own
 * motion is under a centimetre, are used that way: ANIMATION.md 4).
 */
struct FMIFPLayer
{
	const UAnimSequenceBase* Clip = nullptr;
	float Time = 0.f;
	float Weight = 1.f;
	bool bAdditive = false;
	float RefTime = 0.f;
};

/** A hand pulled onto a point of the gun (component space of the arms): two-bone IK of upper arm, forearm, hand. */
struct FMIFPHandIK
{
	FName Upper, Lower, Hand;
	FName Palm;          // a bone in the palm (middle_metacarpal_*): that point, not the wrist, lands on the target
	FTransform Target;   // the wanted component-space transform
	float Weight = 0.f;
	bool bRotation = true;
};

struct FMIFPPose
{
	TArray<FMIFPLayer> Layers;
	TArray<FMIFPHandIK> Hands;
};

/** Evaluates FMIFPPose on the worker thread: no graph, no Blueprint; the game thread decides everything. */
struct FMIFPAnimProxy : public FAnimInstanceProxy
{
	FMIFPAnimProxy() = default;
	explicit FMIFPAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;

	FMIFPPose Pose;
};

/**
 * The anim instance of the first-person arms and of the pack rifle (docs/unreal/ANIMATION.md 4 and 9): a stack of
 * clips at times the weapon component computes from the rules (UMIFirstPersonRig), plus hand IK. It never decides
 * timing itself, so the reload marks land on the rules' stage times by construction.
 */
UCLASS(Transient, NotBlueprintable)
class MURDERINC_API UMIFPAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	/** The pose for the next evaluation (game thread). */
	void SetPose(const FMIFPPose& InPose) { Pending = InPose; }
	const FMIFPPose& GetPending() const { return Pending; }

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FMIFPAnimProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }

private:
	FMIFPPose Pending;
};
