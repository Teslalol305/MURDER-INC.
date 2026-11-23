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
	FName Branch = NAME_None;  // when set: only the bones below this one take the clip (e.g. hand_l: the fingers)
};

/** A hand pulled onto a point of the gun (component space of the arms): two-bone IK of upper arm, forearm, hand. */
struct FMIFPHandIK
{
	FName Upper, Lower, Hand;
	FName Palm;          // a bone in the palm (middle_metacarpal_*): that point, not the wrist, lands on the target
	FTransform Target;   // the wanted component-space transform
	float Weight = 0.f;
	bool bRotation = true;
	bool bKeepHand = false;            // the hand stays where the clip put it; only the elbow moves (PoleShift)
	FVector PoleShift = FVector::ZeroVector;  // component space, added to the clip's own pole (elbow down: -Z)
	/** A solved grip (Content/Data/grips.json): when ShapeWeight > 0 the hand is placed by the shape's wrist point and
	 *  the rotation that turns the hand's own frame (wrist, index / middle / pinky knuckles) onto the shape's, blended
	 *  over the palm placement above by ShapeWeight; then every finger bone is aimed at its child's point. */
	TMap<FName, FVector> Shape;        // bone (or '<finger>_tip_<side>') -> point, component space of the arms
	float ShapeWeight = 0.f;
};

/**
 * A finger closed (or opened, negative) by Deg about its knuckles onto the gun (polish pass, per gun: presentation
 * fingers.hip / .aim, solved in play by MIGripProbe). The turn is shared over the three joints (MIFingerCurl::Share),
 * each about the axis square to its segment and the palm's normal, so it closes toward the palm whatever the bones'
 * local axes are. Applied after the clips, before the hand IK.
 */
struct FMIFPFingerCurl
{
	FName Finger;        // index, middle, ring, pinky
	bool bLeft = true;
	float Deg = 0.f;
};

namespace MIFingerCurl
{
	inline constexpr float Share[3] = {0.3f, 0.4f, 0.3f};
	inline const TCHAR* Side(bool bLeft) { return bLeft ? TEXT("_l") : TEXT("_r"); }
	inline FName Bone(const TCHAR* Finger, int32 Joint, bool bLeft) { return FName(FString::Printf(TEXT("%s_%02d%s"), Finger, Joint, Side(bLeft))); }
	/** The palm's normal, toward where the curled fingers go: hand -> middle knuckle crossed with the knuckle line,
	 *  its sign set by the four fingers' 01 -> 03 directions (they curl to the palm side in every hold). */
	inline FVector PalmNormal(const FVector& Hand, const FVector& Middle1, const FVector& Index1, const FVector& Pinky1, const FVector (&Base)[4], const FVector (&Tip)[4])
	{
		FVector N = FVector::CrossProduct(Middle1 - Hand, Index1 - Pinky1).GetSafeNormal();
		double S = 0.0;
		for (int32 I = 0; I < 4; ++I) S += FVector::DotProduct(N, Tip[I] - Base[I]);
		return S < 0.0 ? -N : N;
	}
	/** The turn of joint J (0..2) of a finger: about the axis square to the segment (P[J] -> P[J + 1], the last one
	 *  along P[1] -> P[2]) and the palm normal, by Share[J] x Deg; positive closes toward the palm. */
	inline FQuat JointTurn(const FVector (&P)[3], int32 J, const FVector& Normal, float Deg)
	{
		const FVector Seg = J < 2 ? P[J + 1] - P[J] : P[2] - P[1];
		const FVector Axis = FVector::CrossProduct(Seg, Normal).GetSafeNormal();
		return Axis.IsNearlyZero() ? FQuat::Identity : FQuat(Axis, FMath::DegreesToRadians(Share[J] * Deg));
	}
}

struct FMIFPPose
{
	TArray<FMIFPLayer> Layers;
	TArray<FMIFPHandIK> Hands;
	TArray<FMIFPFingerCurl> Curls;
};

/** Evaluates FMIFPPose on the worker thread: no graph, no Blueprint; the game thread decides everything. */
struct FMIFPAnimProxy : public FAnimInstanceProxy
{
	FMIFPAnimProxy() = default;
	explicit FMIFPAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;

	FMIFPPose Pose;
	/** Each hand's component-space transform as the clips left it, before the IK and the grip (hands-and-tattoos second
	 *  pass): the weapon component places the arms on the gun by this, so the solved grip does not feed back into the
	 *  placement. [0] hand_l, [1] hand_r. */
	FTransform PreIKHand[2];
	bool bPreIK[2] = {false, false};
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
	/** The hand (hand_l / hand_r) in component space as the clips posed it, before the IK (last evaluation). */
	bool GetPreIKHand(FName Hand, FTransform& Out) const;

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FMIFPAnimProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }

private:
	FMIFPPose Pending;
};
