#include "Enemies/MIGoonMesh.h"

#include "Engine/SkeletalMesh.h"
#include "ReferenceSkeleton.h"
#include "TwoBoneIK.h"

void UMIGoonMeshComponent::FinalizeBoneTransform()
{
	const USkeletalMesh* Mesh = Cast<USkeletalMesh>(GetSkinnedAsset());
	TArray<FTransform>& CS = GetEditableComponentSpaceTransforms();
	if (bHaveGrip && SupportWeight > 0.001f && Mesh && CS.Num() == Mesh->GetRefSkeleton().GetNum())
	{
		const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
		const int32 U = Ref.FindBoneIndex(TEXT("upperarm_l"));
		const int32 L = Ref.FindBoneIndex(TEXT("lowerarm_l"));
		const int32 E = Ref.FindBoneIndex(TEXT("hand_l"));
		const int32 R = Ref.FindBoneIndex(HandBone);
		const int32 Palm = Ref.FindBoneIndex(TEXT("middle_metacarpal_l"));
		if (U != INDEX_NONE && L != INDEX_NONE && E != INDEX_NONE && R != INDEX_NONE)
		{
			const TArray<FTransform> Old = CS;
			FTransform UT = CS[U], LT = CS[L], ET = CS[E];
			const FVector Grip = (GripInHand * CS[R]).GetLocation();
			// The palm's centre (the middle metacarpal) lands on the grip, not the wrist.
			const FVector PalmOffset = Palm != INDEX_NONE ? CS[Palm].GetLocation() - ET.GetLocation() : FVector::ZeroVector;
			const FVector Effector = FMath::Lerp(ET.GetLocation(), Grip - PalmOffset, static_cast<double>(SupportWeight));
			const FVector Pole = LT.GetLocation() + (LT.GetLocation() - (UT.GetLocation() + ET.GetLocation()) * 0.5) * 2.0;
			AnimationCore::SolveTwoBoneIK(UT, LT, ET, Pole, Effector, false, 1.0, 1.0);
			CS[U] = UT;
			CS[L] = LT;
			CS[E] = ET;
			// Every descendant of the three follows its parent (children come after their parents in the array).
			TBitArray<> Moved(false, CS.Num());
			Moved[U] = Moved[L] = Moved[E] = true;
			for (int32 I = U + 1; I < CS.Num(); ++I)
			{
				if (I == L || I == E)
				{
					continue;
				}
				const int32 P = Ref.GetParentIndex(I);
				if (P != INDEX_NONE && Moved[P])
				{
					CS[I] = Old[I].GetRelativeTransform(Old[P]) * CS[P];
					Moved[I] = true;
				}
			}
			LastGrip = Grip;
			LastPalm = Palm != INDEX_NONE ? CS[Palm].GetLocation() : CS[E].GetLocation();
		}
	}
	Super::FinalizeBoneTransform();
}
