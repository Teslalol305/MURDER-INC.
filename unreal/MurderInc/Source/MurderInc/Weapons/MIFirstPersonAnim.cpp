#include "Weapons/MIFirstPersonAnim.h"

#include "Animation/AnimNodeBase.h"
#include "Animation/AnimSequenceBase.h"
#include "AnimationRuntime.h"
#include "BonePose.h"
#include "TwoBoneIK.h"

void FMIFPAnimProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	if (const UMIFPAnimInstance* I = Cast<UMIFPAnimInstance>(InAnimInstance))
	{
		Pose = I->GetPending();
	}
}

namespace MIFirstPersonAnimPrivate
{
	void Sample(const FMIFPLayer& L, float Time, FPoseContext& Out)
	{
		FAnimationPoseData Data(Out);
		const float T = FMath::Clamp(Time, 0.f, L.Clip->GetPlayLength());
		L.Clip->GetAnimationPose(Data, FAnimExtractContext(static_cast<double>(T), false));
	}

	/** Two-bone IK of one arm in component space, the hand's rotation blended to the target's. */
	void SolveHand(FCSPose<FCompactPose>& CS, const FMIFPHandIK& H)
	{
		const FBoneContainer& Bones = CS.GetPose().GetBoneContainer();
		const auto Index = [&Bones](FName Name)
		{
			const int32 Ref = Bones.GetPoseBoneIndexForBoneName(Name);
			return Ref == INDEX_NONE ? FCompactPoseBoneIndex(INDEX_NONE) : Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Ref));
		};
		const FCompactPoseBoneIndex U = Index(H.Upper), L = Index(H.Lower), E = Index(H.Hand);
		if (!U.IsValid() || !L.IsValid() || !E.IsValid() || H.Weight <= 0.f)
		{
			return;
		}
		FTransform UT = CS.GetComponentSpaceTransform(U);
		FTransform LT = CS.GetComponentSpaceTransform(L);
		FTransform ET = CS.GetComponentSpaceTransform(E);
		const FTransform E0 = ET;
		const FCompactPoseBoneIndex PalmIdx = Index(H.Palm);
		const FVector PalmOffset = PalmIdx.IsValid() ? CS.GetComponentSpaceTransform(PalmIdx).GetLocation() - ET.GetLocation() : FVector::ZeroVector;
		const FVector Effector = FMath::Lerp(ET.GetLocation(), H.Target.GetLocation() - PalmOffset, H.Weight);
		// The elbow keeps bending the way the clip bends it.
		const FVector Pole = LT.GetLocation() + (LT.GetLocation() - (UT.GetLocation() + ET.GetLocation()) * 0.5) * 2.0;
		AnimationCore::SolveTwoBoneIK(UT, LT, ET, Pole, Effector, false, 1.0, 1.0);
		if (H.bRotation)
		{
			ET.SetRotation(FQuat::Slerp(E0.GetRotation(), H.Target.GetRotation(), H.Weight).GetNormalized());
		}
		TArray<FBoneTransform> Out;
		Out.Add(FBoneTransform(U, UT));
		Out.Add(FBoneTransform(L, LT));
		Out.Add(FBoneTransform(E, ET));
		CS.SafeSetCSBoneTransforms(Out);
	}
}

bool FMIFPAnimProxy::Evaluate(FPoseContext& Output)
{
	using namespace MIFirstPersonAnimPrivate;
	Output.ResetToRefPose();
	bool bFirst = true;
	for (const FMIFPLayer& L : Pose.Layers)
	{
		if (!L.Clip || L.Weight <= 0.001f)
		{
			continue;
		}
		if (L.bAdditive)
		{
			FPoseContext A(Output), B(Output);
			Sample(L, L.Time, A);
			Sample(L, L.RefTime, B);
			FAnimationRuntime::ConvertPoseToAdditive(A.Pose, B.Pose);
			A.Curve.ConvertToAdditive(B.Curve);
			FAnimationPoseData OutData(Output);
			const FAnimationPoseData AddData(A);
			FAnimationRuntime::AccumulateAdditivePose(OutData, AddData, L.Weight, AAT_LocalSpaceBase);
			Output.Pose.NormalizeRotations();
			continue;
		}
		if (bFirst || L.Weight >= 0.999f)
		{
			Sample(L, L.Time, Output);
			bFirst = false;
			continue;
		}
		FPoseContext T(Output);
		Sample(L, L.Time, T);
		FAnimationPoseData OutData(Output);
		const FAnimationPoseData TData(T);
		FAnimationRuntime::BlendTwoPosesTogetherInPlace(OutData, TData, 1.f - L.Weight);
	}
	if (Pose.Hands.ContainsByPredicate([](const FMIFPHandIK& H) { return H.Weight > 0.f; }))
	{
		FCSPose<FCompactPose> CS;
		CS.InitPose(Output.Pose);
		for (const FMIFPHandIK& H : Pose.Hands)
		{
			SolveHand(CS, H);
		}
		FCSPose<FCompactPose>::ConvertComponentPosesToLocalPoses(MoveTemp(CS), Output.Pose);
	}
	return true;
}
