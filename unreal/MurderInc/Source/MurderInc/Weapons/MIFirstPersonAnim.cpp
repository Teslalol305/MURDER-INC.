#include "Weapons/MIFirstPersonAnim.h"

#include "Animation/AnimNodeBase.h"
#include "Animation/AnimSequenceBase.h"
#include "AnimationRuntime.h"
#include "BonePose.h"
#include "TwoBoneIK.h"
#include "HAL/IConsoleManager.h"

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
	/** How far an arm may stretch to reach its target (1 = never). The mannequin's arm is 58.5 cm from the upper arm to the
	 *  palm and the support palm of a rifle is up to 64 cm from the shoulder under the eye: without a little stretch the
	 *  hand stops short of the handguard. Console mi.FP.ArmStretch. */
	static TAutoConsoleVariable<float> CVarArmStretch(TEXT("mi.FP.ArmStretch"), 0.f,
		TEXT("Largest stretch of every hand-IK arm to reach its target (1 = none); 0 = each arm's own (the anim set's armStretch on the support arm of a rifle)"), ECVF_Default);

	void Sample(const FMIFPLayer& L, float Time, FPoseContext& Out)
	{
		FAnimationPoseData Data(Out);
		const float T = FMath::Clamp(Time, 0.f, L.Clip->GetPlayLength());
		L.Clip->GetAnimationPose(Data, FAnimExtractContext(static_cast<double>(T), false));
	}

	FCompactPoseBoneIndex BoneIndex(const FBoneContainer& Bones, FName Name)
	{
		const int32 Ref = Bones.GetPoseBoneIndexForBoneName(Name);
		return Ref == INDEX_NONE ? FCompactPoseBoneIndex(INDEX_NONE) : Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Ref));
	}

	/** The hand's own frame from points: X wrist -> middle knuckle, Z across the knuckles (index -> pinky) x X. */
	bool HandFrame(const FVector& Wrist, const FVector& Middle, const FVector& Index, const FVector& Pinky, FQuat& Out)
	{
		const FVector X = (Middle - Wrist).GetSafeNormal();
		const FVector Across = Index - Pinky;
		FVector Z = FVector::CrossProduct(X, Across).GetSafeNormal();
		if (X.IsNearlyZero() || Z.IsNearlyZero())
		{
			return false;
		}
		const FVector Y = FVector::CrossProduct(Z, X);
		Out = FMatrix(X, Y, Z, FVector::ZeroVector).ToQuat();
		return true;
	}

	/** The rotation and wrist point of a hand shape for the current pose (the hand turned so its frame of points
	 *  matches the shape's). */
	bool ShapeHand(FCSPose<FCompactPose>& CS, const FMIFPHandIK& H, FTransform& Out)
	{
		const FBoneContainer& Bones = CS.GetPose().GetBoneContainer();
		const FString Side = H.Hand.ToString().Right(2);  // "_r" / "_l"
		const FName Names[4] = {H.Hand, FName(TEXT("middle_01") + Side), FName(TEXT("index_01") + Side), FName(TEXT("pinky_01") + Side)};
		FVector Cur[4], Tgt[4];
		for (int32 I = 0; I < 4; ++I)
		{
			const FCompactPoseBoneIndex B = BoneIndex(Bones, Names[I]);
			const FVector* T = H.Shape.Find(Names[I]);
			if (!B.IsValid() || !T)
			{
				return false;
			}
			Cur[I] = CS.GetComponentSpaceTransform(B).GetLocation();
			Tgt[I] = *T;
		}
		FQuat Qc, Qt;
		if (!HandFrame(Cur[0], Cur[1], Cur[2], Cur[3], Qc) || !HandFrame(Tgt[0], Tgt[1], Tgt[2], Tgt[3], Qt))
		{
			return false;
		}
		const FTransform E = CS.GetComponentSpaceTransform(BoneIndex(Bones, H.Hand));
		Out = FTransform((Qt * Qc.Inverse() * E.GetRotation()).GetNormalized(), Tgt[0]);
		return true;
	}

	/** Every finger bone of a shaped hand aimed at its child's point (swing only), parents first. */
	void ShapeFingers(FCSPose<FCompactPose>& CS, const FMIFPHandIK& H)
	{
		const FBoneContainer& Bones = CS.GetPose().GetBoneContainer();
		const FString Side = H.Hand.ToString().Right(2);
		static const TCHAR* Fingers[5] = {TEXT("thumb"), TEXT("index"), TEXT("middle"), TEXT("ring"), TEXT("pinky")};
		const float W = FMath::Clamp(H.ShapeWeight, 0.f, 1.f);
		for (const TCHAR* F : Fingers)
		{
			TArray<FName> Chain;
			if (FCString::Strcmp(F, TEXT("thumb")) != 0)
			{
				Chain.Add(FName(FString::Printf(TEXT("%s_metacarpal%s"), F, *Side)));
			}
			for (int32 K = 1; K <= 3; ++K)
			{
				Chain.Add(FName(FString::Printf(TEXT("%s_%02d%s"), F, K, *Side)));
			}
			const FName Tip(FString::Printf(TEXT("%s_tip%s"), F, *Side));
			for (int32 I = 0; I < Chain.Num(); ++I)
			{
				const FCompactPoseBoneIndex B = BoneIndex(Bones, Chain[I]);
				const FVector* PB = H.Shape.Find(Chain[I]);
				const FName ChildName = I + 1 < Chain.Num() ? Chain[I + 1] : Tip;
				const FVector* PC = H.Shape.Find(ChildName);
				if (!B.IsValid() || !PB || !PC)
				{
					continue;
				}
				const FTransform T = CS.GetComponentSpaceTransform(B);
				FVector Cur;
				if (I + 1 < Chain.Num())
				{
					const FCompactPoseBoneIndex C = BoneIndex(Bones, Chain[I + 1]);
					if (!C.IsValid())
					{
						continue;
					}
					Cur = CS.GetComponentSpaceTransform(C).GetLocation() - T.GetLocation();
				}
				else
				{
					// the last segment has no child bone: its direction is the line from its parent's head in the
					// reference pose, carried in its own frame
					const FTransform& Ref = Bones.GetRefPoseTransform(B);
					Cur = T.GetRotation().RotateVector(Ref.GetRotation().UnrotateVector(Ref.GetTranslation()));
				}
				const FVector Want = *PC - *PB;
				if (Cur.IsNearlyZero() || Want.IsNearlyZero())
				{
					continue;
				}
				const FQuat D = FQuat::Slerp(FQuat::Identity, FQuat::FindBetweenVectors(Cur, Want), W);
				FTransform N = T;
				N.SetRotation((D * T.GetRotation()).GetNormalized());
				TArray<FBoneTransform> Out;
				Out.Add(FBoneTransform(B, N));
				CS.SafeSetCSBoneTransforms(Out);
			}
		}
	}

	/** The per-gun finger curls (FMIFPFingerCurl), in component space, parents first: each joint turned about its own
	 *  pivot, the joints below it following. */
	void ApplyCurls(FCSPose<FCompactPose>& CS, const TArray<FMIFPFingerCurl>& Curls)
	{
		const FBoneContainer& Bones = CS.GetPose().GetBoneContainer();
		static const TCHAR* Fingers[4] = {TEXT("index"), TEXT("middle"), TEXT("ring"), TEXT("pinky")};
		const auto At = [&](FName Name, FVector& Out)
		{
			const FCompactPoseBoneIndex B = BoneIndex(Bones, Name);
			if (!B.IsValid()) return false;
			Out = CS.GetComponentSpaceTransform(B).GetLocation();
			return true;
		};
		for (int32 S = 0; S < 2; ++S)
		{
			const bool bLeft = S == 0;
			if (!Curls.ContainsByPredicate([bLeft](const FMIFPFingerCurl& C) { return C.bLeft == bLeft && FMath::Abs(C.Deg) > 0.05f; }))
			{
				continue;
			}
			FVector Hand, Base[4], Tip[4];
			bool bOk = At(bLeft ? FName(TEXT("hand_l")) : FName(TEXT("hand_r")), Hand);
			for (int32 I = 0; I < 4 && bOk; ++I)
			{
				bOk = At(MIFingerCurl::Bone(Fingers[I], 1, bLeft), Base[I]) && At(MIFingerCurl::Bone(Fingers[I], 3, bLeft), Tip[I]);
			}
			if (!bOk)
			{
				continue;
			}
			const FVector N = MIFingerCurl::PalmNormal(Hand, Base[1], Base[0], Base[3], Base, Tip);
			for (const FMIFPFingerCurl& C : Curls)
			{
				if (C.bLeft != bLeft || FMath::Abs(C.Deg) <= 0.05f)
				{
					continue;
				}
				FCompactPoseBoneIndex Idx[3];
				for (int32 J = 0; J < 3; ++J)
				{
					Idx[J] = BoneIndex(Bones, MIFingerCurl::Bone(*C.Finger.ToString(), J + 1, bLeft));
				}
				if (!Idx[0].IsValid() || !Idx[1].IsValid() || !Idx[2].IsValid())
				{
					continue;
				}
				for (int32 J = 0; J < 3; ++J)
				{
					FVector P[3];
					for (int32 K = 0; K < 3; ++K) P[K] = CS.GetComponentSpaceTransform(Idx[K]).GetLocation();
					FTransform T = CS.GetComponentSpaceTransform(Idx[J]);
					T.SetRotation((MIFingerCurl::JointTurn(P, J, N, C.Deg) * T.GetRotation()).GetNormalized());
					TArray<FBoneTransform> Out;
					Out.Add(FBoneTransform(Idx[J], T));
					CS.SafeSetCSBoneTransforms(Out);
				}
			}
		}
	}

	/** Two-bone IK of one arm in component space, the hand's rotation blended to the target's. */
	void SolveHand(FCSPose<FCompactPose>& CS, const FMIFPHandIK& H)
	{
		const FBoneContainer& Bones = CS.GetPose().GetBoneContainer();
		const auto Index = [&Bones](FName Name) { return BoneIndex(Bones, Name); };
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
		FVector Effector = H.bKeepHand ? ET.GetLocation() : FMath::Lerp(ET.GetLocation(), H.Target.GetLocation() - PalmOffset, H.Weight);
		FQuat ShapeRot = FQuat::Identity;
		const bool bShape = H.ShapeWeight > 0.f && !H.bKeepHand && !H.Shape.IsEmpty();
		FTransform Shaped;
		const bool bShaped = bShape && ShapeHand(CS, H, Shaped);
		if (bShaped)
		{
			Effector = FMath::Lerp(Effector, Shaped.GetLocation(), FMath::Clamp(H.ShapeWeight, 0.f, 1.f));
			ShapeRot = Shaped.GetRotation();
		}
		// The elbow keeps bending the way the clip bends it (moved by PoleShift x Weight when asked).
		const FVector Pole = LT.GetLocation() + (LT.GetLocation() - (UT.GetLocation() + ET.GetLocation()) * 0.5) * 2.0 + H.PoleShift * H.Weight;
		const double Forced = static_cast<double>(CVarArmStretch.GetValueOnAnyThread());
		const double Stretch = FMath::Clamp(Forced > 0.0 ? Forced : static_cast<double>(H.Stretch), 1.0, 1.3);
		AnimationCore::SolveTwoBoneIK(UT, LT, ET, Pole, Effector, Stretch > 1.0, 1.0, Stretch);
		if (H.bRotation && !H.bKeepHand)
		{
			ET.SetRotation(FQuat::Slerp(E0.GetRotation(), H.Target.GetRotation(), H.Weight).GetNormalized());
		}
		if (bShaped)
		{
			ET.SetRotation(FQuat::Slerp(ET.GetRotation(), ShapeRot, FMath::Clamp(H.ShapeWeight, 0.f, 1.f)).GetNormalized());
		}
		TArray<FBoneTransform> Out;
		Out.Add(FBoneTransform(U, UT));
		Out.Add(FBoneTransform(L, LT));
		Out.Add(FBoneTransform(E, ET));
		CS.SafeSetCSBoneTransforms(Out);
		if (bShaped)
		{
			ShapeFingers(CS, H);
		}
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
		if (!L.Branch.IsNone())
		{
			// Only the bones below Branch (the fingers under hand_l), blended in local space.
			const FBoneContainer& Bones = Output.Pose.GetBoneContainer();
			const int32 RootRef = Bones.GetPoseBoneIndexForBoneName(L.Branch);
			if (RootRef == INDEX_NONE)
			{
				continue;
			}
			const FCompactPoseBoneIndex Root = Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(RootRef));
			FPoseContext T(Output);
			Sample(L, L.Time, T);
			for (const FCompactPoseBoneIndex I : Output.Pose.ForEachBoneIndex())
			{
				bool bBelow = false;
				for (FCompactPoseBoneIndex P = Output.Pose.GetParentBoneIndex(I); P.IsValid(); P = Output.Pose.GetParentBoneIndex(P))
				{
					if (P == Root) { bBelow = true; break; }
				}
				if (bBelow)
				{
					Output.Pose[I].BlendWith(T.Pose[I], L.Weight);
				}
			}
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
	if (Pose.Curls.Num() > 0 || Pose.Hands.ContainsByPredicate([](const FMIFPHandIK& H) { return H.Weight > 0.f; }))
	{
		FCSPose<FCompactPose> CS;
		CS.InitPose(Output.Pose);
		ApplyCurls(CS, Pose.Curls);
		for (int32 S = 0; S < 2; ++S)
		{
			const FCompactPoseBoneIndex B = BoneIndex(Output.Pose.GetBoneContainer(), S == 0 ? FName(TEXT("hand_l")) : FName(TEXT("hand_r")));
			bPreIK[S] = B.IsValid();
			if (B.IsValid())
			{
				PreIKHand[S] = CS.GetComponentSpaceTransform(B);
			}
		}
		for (const FMIFPHandIK& H : Pose.Hands)
		{
			SolveHand(CS, H);
		}
		FCSPose<FCompactPose>::ConvertComponentPosesToLocalPoses(MoveTemp(CS), Output.Pose);
	}
	return true;
}

bool UMIFPAnimInstance::GetPreIKHand(FName Hand, FTransform& Out) const
{
	const FMIFPAnimProxy& P = GetProxyOnAnyThread<FMIFPAnimProxy>();
	const int32 S = Hand == TEXT("hand_l") ? 0 : Hand == TEXT("hand_r") ? 1 : INDEX_NONE;
	if (S == INDEX_NONE || !P.bPreIK[S])
	{
		return false;
	}
	Out = P.PreIKHand[S];
	return true;
}
