#include "Weapons/MIGunAssembly.h"

#include "AnimationRuntime.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "MurderInc.h"
#include "Weapons/MIViewmodel.h"
#include "Dom/JsonObject.h"
#include "Materials/MaterialInterface.h"

namespace MIGunAssemblyPrivate
{
	/** Where a part sits when its mount has no socket on the base mesh: the viewmodel marker of its slot. */
	FName FallbackMarker(FName Slot)
	{
		if (Slot == TEXT("optic")) return TEXT("sightRear");
		if (Slot == TEXT("muzzle")) return TEXT("muzzle");
		if (Slot == TEXT("underbarrel") || Slot == TEXT("laser")) return TEXT("support");
		return NAME_None;
	}

	/** A bone of the gun that a part replaces is hidden. The first-person gun is a poseable mesh: its bone is shrunk to
	 *  a point (every vertex weighted to it, and to its children, collapses onto the bone's origin), which does not
	 *  depend on how the renderer treats hidden bones of a poseable component. A skeletal mesh (the stage) hides it. */
	void HideGunBone(USkinnedMeshComponent* Base, FName Bone)
	{
		if (UPoseableMeshComponent* Poseable = Cast<UPoseableMeshComponent>(Base))
		{
			Poseable->SetBoneScaleByName(Bone, FVector(1e-3), EBoneSpaces::ComponentSpace);
		}
		else
		{
			Base->HideBoneByName(Bone, EPhysBodyOp::PBO_None);
		}
	}

	void ShowGunBone(USkinnedMeshComponent* Base, FName Bone)
	{
		if (UPoseableMeshComponent* Poseable = Cast<UPoseableMeshComponent>(Base))
		{
			Poseable->ResetBoneTransformByName(Bone);
		}
		else
		{
			Base->UnHideBoneByName(Bone);
		}
	}

	/** The gun's own static part made like a fitted one: movable, no collision, the base's first-person flags. */
	UStaticMeshComponent* MakePartComponent(UObject* Outer, USkinnedMeshComponent* Base, UStaticMesh* Mesh)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(Outer, NAME_None, RF_Transient);
		C->SetStaticMesh(Mesh);
		C->SetMobility(EComponentMobility::Movable);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(Base->CastShadow);
		C->bOnlyOwnerSee = Base->bOnlyOwnerSee;
		C->SetFirstPersonPrimitiveType(Base->FirstPersonPrimitiveType);
		C->RegisterComponent();
		return C;
	}
}

bool UMIGunAssembly::BoneRestInMesh(const USkinnedMeshComponent* InBase, FName Bone, FTransform& Out)
{
	const USkeletalMesh* Mesh = InBase ? Cast<USkeletalMesh>(InBase->GetSkinnedAsset()) : nullptr;
	const int32 Index = Mesh && !Bone.IsNone() ? Mesh->GetRefSkeleton().FindBoneIndex(Bone) : INDEX_NONE;
	if (Index == INDEX_NONE)
	{
		return false;
	}
	Out = FAnimationRuntime::GetComponentSpaceTransformRefPose(Mesh->GetRefSkeleton(), Index);
	return true;
}

bool UMIGunAssembly::IsBoneSocket(const USkinnedMeshComponent* InBase, FName Name)
{
	const USkeletalMesh* Mesh = InBase ? Cast<USkeletalMesh>(InBase->GetSkinnedAsset()) : nullptr;
	return Mesh && !Name.IsNone() && Mesh->FindSocket(Name) == nullptr && Mesh->GetRefSkeleton().FindBoneIndex(Name) != INDEX_NONE;
}

UMIGunAssembly::UMIGunAssembly()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
	PrimaryComponentTick.bTickEvenWhenPaused = true;
}

void UMIGunAssembly::Clear()
{
	for (UStaticMeshComponent* C : Owned)
	{
		if (C)
		{
			C->DestroyComponent();
		}
	}
	Owned.Reset();
	Parts.Reset();
	if (Base)
	{
		for (const FName Bone : Hidden)
		{
			MIGunAssemblyPrivate::ShowGunBone(Base, Bone);
		}
	}
	Hidden.Reset();
	FactoryMagazine.Reset();
	LaserSlot = NAME_None;
}

void UMIGunAssembly::Assemble(USkinnedMeshComponent* InBase, const FMIResolvedGun& Gun, bool bSetBase, double Slide)
{
	using namespace MIGunAssemblyPrivate;
	// Parts that stay fitted keep their place; new ones slide in.
	TSet<FName> Before;
	for (const FPart& P : Parts)
	{
		Before.Add(P.Data.Part);
	}
	Clear();
	Base = InBase;
	if (!Base)
	{
		return;
	}
	if (bSetBase && BaseMesh != Gun.BaseMesh)
	{
		USkeletalMesh* Mesh = Cast<USkeletalMesh>(FSoftObjectPath(Gun.BaseMesh).TryLoad());
		Base->SetSkinnedAssetAndUpdate(Mesh, true);
		Base->SetVisibility(Mesh != nullptr);
	}
	if (bSetBase)
	{
		// The gun's own finish over the mesh's slots (presentation "materials": the CHOPPER's dark earth on the pack rifle).
		Base->EmptyOverrideMaterials();
		const TSharedPtr<FJsonValue> Mats = Gun.Presentation.IsValid() ? Gun.Presentation->TryGetField(TEXT("materials")) : nullptr;
		if (Mats.IsValid() && Mats->Type == EJson::Object)
		{
			for (const auto& Pair : Mats->AsObject()->Values)
			{
				if (UMaterialInterface* M = Cast<UMaterialInterface>(FSoftObjectPath(Pair.Value->AsString()).TryLoad()))
				{
					Base->SetMaterialByName(FName(FString(*Pair.Key)), M);
				}
			}
		}
	}
	BaseMesh = Gun.BaseMesh;
	MarkerFallback.Reset();
	for (const TPair<FName, FVector>& M : Gun.View.Markers)
	{
		MarkerFallback.Add(M.Key, Gun.View.MeshOffset.InverseTransformPosition(FMIViewmodelRig::WebToUE(M.Value)));
	}
	for (const FMIResolvedPart& R : Gun.Parts)
	{
		for (const FName Bone : R.Hide)
		{
			if (Base->GetBoneIndex(Bone) != INDEX_NONE)
			{
				HideGunBone(Base, Bone);
				Hidden.Add(Bone);
			}
		}
		UStaticMesh* Mesh = R.Mesh.IsEmpty() ? nullptr : Cast<UStaticMesh>(FSoftObjectPath(R.Mesh).TryLoad());
		if (!Mesh)
		{
			UE_LOG(LogMI, Warning, TEXT("Gun assembly: %s has no mesh at '%s' (not offered until it exists)"), *R.Part.ToString(), *R.Mesh);
			continue;
		}
		UStaticMeshComponent* C = MakePartComponent(GetOwner(), Base, Mesh);
		FTransform Rest = FTransform::Identity;
		if (!R.Socket.IsNone() && Base->DoesSocketExist(R.Socket))
		{
			C->AttachToComponent(Base, FAttachmentTransformRules::SnapToTargetIncludingScale, R.Socket);  // the part takes the gun's scale (a swap can be mid scale-out)
			FTransform BoneRest;
			if (IsBoneSocket(Base, R.Socket) && BoneRestInMesh(Base, R.Socket, BoneRest))
			{
				// A socket that is a bone of the exported skeleton carries the importer's turn of the glTF axes; the part
				// was modelled in the gun's own frame (X along the bore, Z up), so it is turned back (position unchanged).
				C->SetRelativeRotation(BoneRest.GetRotation().Inverse());
				if (!R.RideBone.IsNone() && BoneRestInMesh(Base, R.RideBone, BoneRest))
				{
					// A part that moves with a gun part (a magazine: it drops and hides with the 'magazine' bone in a
					// reload) is carried by that bone from where it sits at rest.
					const FTransform At(FQuat::Identity, Base->GetSocketTransform(R.Socket, RTS_Component).GetLocation());
					C->AttachToComponent(Base, FAttachmentTransformRules::SnapToTargetIncludingScale, R.RideBone);
					C->SetRelativeTransform(At.GetRelativeTransform(BoneRest));
				}
			}
		}
		else
		{
			// No socket on the mesh yet: the slot's marker from the data (provisional until the socket pass).
			C->AttachToComponent(Base, FAttachmentTransformRules::SnapToTargetIncludingScale);
			const FVector* At = MarkerFallback.Find(FallbackMarker(R.Slot));
			Rest.SetLocation(At ? *At : FVector::ZeroVector);
			C->SetRelativeTransform(Rest);
		}
		Rest = C->GetRelativeTransform();
		Owned.Add(C);
		FPart& P = Parts.AddDefaulted_GetRef();
		P.Data = R;
		P.Mesh = C;
		P.Rest = Rest;
		P.Slide = Before.Contains(R.Part) ? 0.0 : Slide;
		P.Age = P.Slide > 0.0 ? 0.0 : 1e9;
		if (R.Markers.Contains(TEXT("beam")))
		{
			LaserSlot = R.Slot;
		}
	}
	// The factory magazine (the stage and the crew screen: the first-person rig draws its own): in the well whenever no
	// magazine part is fitted, so a longer one reads as a change. presentation.magazine {mesh, bone | socket}: authored in
	// the gun's own space (our guns, carried by their 'magazine' bone) or on a socket of the mesh (the pack's rifles).
	if (bSetBase && !PartMesh(TEXT("magazine")))
	{
		const FString MagPath = MIJson::StringOr(Gun.Presentation, TEXT("magazine.mesh"));
		UStaticMesh* Mag = MagPath.IsEmpty() ? nullptr : Cast<UStaticMesh>(FSoftObjectPath(MagPath).TryLoad());
		if (Mag)
		{
			UStaticMeshComponent* C = MakePartComponent(GetOwner(), Base, Mag);
			const FName Bone(*MIJson::StringOr(Gun.Presentation, TEXT("magazine.bone")));
			const FName Socket(*MIJson::StringOr(Gun.Presentation, TEXT("magazine.socket")));
			FTransform BoneRest;
			if (BoneRestInMesh(Base, Bone, BoneRest))
			{
				C->AttachToComponent(Base, FAttachmentTransformRules::SnapToTargetIncludingScale, Bone);
				C->SetRelativeTransform(FTransform::Identity.GetRelativeTransform(BoneRest));
			}
			else if (!Socket.IsNone() && Base->DoesSocketExist(Socket))
			{
				C->AttachToComponent(Base, FAttachmentTransformRules::SnapToTargetIncludingScale, Socket);
			}
			else
			{
				C->AttachToComponent(Base, FAttachmentTransformRules::SnapToTargetIncludingScale);
			}
			Owned.Add(C);
			FactoryMagazine = C;
		}
	}
	SetComponentTickEnabled(Parts.ContainsByPredicate([](const FPart& P) { return P.Age < P.Slide; }));
}

void UMIGunAssembly::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	bool bAny = false;
	for (FPart& P : Parts)
	{
		if (P.Age >= P.Slide || !P.Mesh.IsValid())
		{
			continue;
		}
		P.Age += DeltaTime;
		const double K = FMath::Clamp(P.Age / P.Slide, 0.0, 1.0);
		const double Ease = 1.0 - FMath::Pow(1.0 - K, 3.0);
		// Slides along the gun's bore (the mesh's X) into its socket, from 8 cm out.
		FTransform T = P.Rest;
		T.AddToTranslation(P.Rest.GetRotation().RotateVector(FVector(8.0 * (1.0 - Ease), 0.0, 3.0 * (1.0 - Ease))));
		P.Mesh->SetRelativeTransform(T);
		bAny |= K < 1.0;
	}
	SetComponentTickEnabled(bAny);
}

UStaticMeshComponent* UMIGunAssembly::PartMesh(FName Slot) const
{
	for (const FPart& P : Parts)
	{
		if (P.Data.Slot == Slot && P.Mesh.IsValid())
		{
			return P.Mesh.Get();
		}
	}
	return nullptr;
}

TMap<FName, FVector> UMIGunAssembly::MarkerOverrides() const
{
	TMap<FName, FVector> Out;
	if (!Base)
	{
		return Out;
	}
	const FTransform BaseWorld = Base->GetComponentTransform();
	for (const FPart& P : Parts)
	{
		if (!P.Mesh.IsValid())
		{
			continue;
		}
		for (const TPair<FName, FName>& M : P.Data.Markers)
		{
			if (P.Mesh->DoesSocketExist(M.Value))
			{
				Out.Add(M.Key, BaseWorld.InverseTransformPosition(P.Mesh->GetSocketLocation(M.Value)));
			}
		}
	}
	return Out;
}

bool UMIGunAssembly::MarkerTransform(FName Marker, FTransform& Out) const
{
	for (const FPart& P : Parts)
	{
		const FName* Socket = P.Data.Markers.Find(Marker);
		if (Socket && P.Mesh.IsValid() && P.Mesh->DoesSocketExist(*Socket))
		{
			Out = P.Mesh->GetSocketTransform(*Socket);
			return true;
		}
	}
	return false;
}

bool UMIGunAssembly::BeamWorld(FVector& OutStart, FVector& OutDir) const
{
	if (LaserSlot.IsNone() || !Base)
	{
		return false;
	}
	for (const FPart& P : Parts)
	{
		if (P.Data.Slot != LaserSlot || !P.Mesh.IsValid())
		{
			continue;
		}
		const FName* Socket = P.Data.Markers.Find(TEXT("beam"));
		const FTransform T = Socket && P.Mesh->DoesSocketExist(*Socket) ? P.Mesh->GetSocketTransform(*Socket) : P.Mesh->GetComponentTransform();
		OutStart = T.GetLocation();
		OutDir = T.GetRotation().GetForwardVector();
		return true;
	}
	return false;
}
